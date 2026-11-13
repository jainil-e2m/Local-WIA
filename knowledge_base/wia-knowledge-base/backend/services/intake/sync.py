"""Durable stream scheduling, run coalescing, checkpoints and operator requests.

Lock order, shared with page execution (execution.py): work item -> sync run -> sync stream -> connector
account -> source scope. Nothing here locks an account or a scope, so scheduling can never wait on a page job
in a cycle; mapping commands (which lock scopes) queue collection in a later transaction, never their own.
"""
from collections import Counter
from datetime import timedelta
from uuid import uuid4

from sqlalchemy import String, and_, case, cast, exists, func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import aliased

from backend.config import get_settings
from backend.models.db import Business, ConnectorAccount, CoverageWindow, SourceRecord, SourceScope, SyncRun, SyncStream
from backend.models.db.base import utcnow
from backend.workers.queue import db_now, enqueue
from backend.services.intake.positions import enqueue_page
from backend.services.intake.scoping import is_live, live_scope

PAGE_JOB = "intake.backfill_page"
SWEEP_LOCK = 7_301_125  # pg advisory key: one sweeper at a time, however many workers run
# LeadLock has no change feed: every run re-reads the whole sub-account, so poll it far less often.
# shortcut: per-provider intervals live in code; move them to settings if WIA wants to tune them.
INCREMENTAL_SECONDS = {"leadlock": 6 * 3600}
# Runs a mapping decision stopped (unlink, archive): safe to continue from their checkpoint once live again.
STOPPED_BY_DECISION = ("client_archived", "scope_retired", "approval_revoked")


def sync_interval(provider: str) -> int:
    return INCREMENTAL_SECONDS.get(provider, get_settings().sync_interval_seconds)


def _stream_key(provider: str, scope) -> str:
    return "drive:account" if provider == "drive" else str(scope.id)


def ensure_stream(s, scope):
    """The scope's stream, created if missing, locked. Takes no account lock (see the lock order above)."""
    provider = s.get(ConnectorAccount, scope.connector_account_id).provider
    q = select(SyncStream).where(SyncStream.connector_account_id == scope.connector_account_id,
        SyncStream.stream_key == _stream_key(provider, scope)).with_for_update()
    stream = s.execute(q).scalar_one_or_none()
    if stream is None:
        # The unique key makes a concurrent creator's insert a no-op; both then lock the same row.
        s.execute(insert(SyncStream).values(id=uuid4(), connector_account_id=scope.connector_account_id,
            scope_id=scope.id, stream_key=_stream_key(provider, scope), generation=1, cursor={}, enabled=False)
            .on_conflict_do_nothing(index_elements=["connector_account_id", "stream_key"]))
        stream = s.execute(q).scalar_one()
    elif not is_live(s, s.get(SourceScope, stream.scope_id)):
        stream.scope_id = scope.id
    return stream


def request_run(s, scope_id, mode="incremental", *, days=None, target=None, full=False):
    """A backfill with no `days` uses the source's BACKFILL_DAYS window (unset = full history); `full` forces full history."""
    if mode not in ("backfill", "incremental", "reconcile", "refresh"):
        raise ValueError("unsupported sync mode")
    scope = s.get(SourceScope, scope_id)
    if scope is None or not is_live(s, scope):
        raise ValueError("source scope is not approved, or its client is archived")
    account = s.get(ConnectorAccount, scope.connector_account_id)
    if account.state != "active":
        raise ValueError("connector account is inactive")
    if mode == "backfill" and days is None and not full:
        days = get_settings().backfill_days.get(account.provider)
    stream = ensure_stream(s, scope)
    active = s.execute(select(SyncRun).where(SyncRun.stream_id == stream.id,
        SyncRun.state.in_(("queued", "running"))).order_by(SyncRun.started_at)).scalars().all()
    for run in active:
        if run.mode == mode and run.target_external_id == target:
            return run, True
    now = utcnow()
    run = SyncRun(id=uuid4(), connector_account_id=account.id, scope_id=scope.id,
        stream_id=stream.id, generation=stream.generation, mode=mode,
        state="queued" if active else "running", window_end=now,
        window_start=now - timedelta(days=days) if days else None, checkpoint={}, target_external_id=target)
    s.add(run)
    s.flush()
    s.add(CoverageWindow(id=uuid4(), scope_id=scope.id, run_id=run.id,
        window_start=run.window_start, window_end=now, contract_version="intake-coverage-v2"))
    s.flush()
    enqueue_page(s, run, "sync", "bulk" if mode in ("backfill", "reconcile") else "sync")
    return run, False


def request_refresh(s, record_id):
    record = s.get(SourceRecord, record_id)
    if record is None or record.admitted_at is None:
        raise ValueError("record is not admitted")
    return request_run(s, record.scope_id, "refresh", target=record.external_id)


def operator_stop(s, run_id):
    """Stop a copy on command. Its in-flight page is acknowledged without publishing (positions.validate), and
    `operator_stopped` is not a mapping decision, so only `resume` (an operator) continues it."""
    from backend.services.intake.execution import stop
    run = s.get(SyncRun, run_id, with_for_update=True)
    if run is None or run.state not in ("queued", "running"):
        raise ValueError("only a queued or running run can be stopped")
    stop(s, run, "operator_stopped")
    return run


def resume(s, run_id):
    run = s.get(SyncRun, run_id, with_for_update=True)
    if run is None or run.state not in ("failed", "partial"):
        raise ValueError("only failed or partial runs can resume")
    scope = s.get(SourceScope, run.scope_id)
    stream = s.get(SyncStream, run.stream_id, with_for_update=True)  # run -> stream: the page jobs' order
    account = s.get(ConnectorAccount, run.connector_account_id)
    if not is_live(s, scope) or account.state != "active":
        raise ValueError("source scope or connector is inactive, or its client is archived")
    if run.generation != stream.generation:
        raise ValueError("run superseded; start a new reconciliation")
    other = s.execute(select(SyncRun.id).where(SyncRun.stream_id == stream.id,
        SyncRun.state == "running", SyncRun.id != run.id)).first()
    run.state, run.finished_at, run.error_class = ("queued" if other else "running"), None, None
    if run.checkpoint.get("completed"):
        run.checkpoint, run.mode = {}, "reconcile"
    coverage = s.execute(select(CoverageWindow).where(CoverageWindow.run_id == run.id)).scalar_one()
    coverage.state = "open"
    # Retry the original durable work item when this page never published.
    from backend.models.db import WorkItem
    from backend.services.intake.positions import input_key
    key = input_key(run.id, run.scope_id, run.generation, run.checkpoint, "sync")
    item = s.execute(select(WorkItem).where(WorkItem.kind == PAGE_JOB,
        WorkItem.input_signature == f"page:{run.id}:{run.generation}:{key}").with_for_update()).scalar_one_or_none()
    # "succeeded" too: a page that found its run stopped (archive, unlink) completes its item without publishing,
    # and the run's checkpoint not having moved proves this page never published.
    if item is not None and item.state in ("failed", "blocked", "succeeded"):
        item.state, item.attempt, item.next_run_at = "pending", 0, utcnow()
        item.last_error_class = item.last_error = None
    else:
        enqueue_page(s, run, "sync")
    return run


def collect(s, scope_id, *, explicit=False) -> str:
    """Get a live source collecting, from wherever it is.

    No stream or no run yet: a full-history copy. Its last copy was stopped by a mapping decision: resume that
    copy from its checkpoint. Already kept up to date: nothing, unless `explicit` (a person just linked it),
    which asks for a full re-check, since changes made while it was unlinked were never read. A copy that
    failed for another reason is an operator's call, except when a person explicitly links it again."""
    scope = s.get(SourceScope, scope_id)
    provider = s.get(ConnectorAccount, scope.connector_account_id).provider
    stream = s.execute(select(SyncStream).where(SyncStream.connector_account_id == scope.connector_account_id,
        SyncStream.stream_key == _stream_key(provider, scope))).scalar_one_or_none()
    last = None if stream is None else s.execute(select(SyncRun).where(SyncRun.stream_id == stream.id)
        .order_by(SyncRun.started_at.desc()).limit(1)).scalar_one_or_none()
    if last is not None and last.state in ("queued", "running"):
        return "already_running"
    if (last is not None and last.state == "failed" and last.error_class in STOPPED_BY_DECISION
            and last.mode in ("backfill", "reconcile") and last.generation == stream.generation):
        resume(s, last.id)
        return "resumed"
    if stream is None or not stream.enabled:
        if last is None or explicit:
            request_run(s, scope_id, "backfill")
            return "started"
        return "needs_operator"
    if explicit:
        request_run(s, scope_id, "reconcile")
        return "started"
    return "up_to_date"


# Gaps that are recorded and need nothing more read: a file type we don't parse, an item the account can't see, or
# one deleted upstream. A `failed` gap (or a failed count) means items were missed and the copy is incomplete.
SETTLED_GAPS = frozenset({"unsupported", "inaccessible", "scope_denied", "not_found"})
COMPLETE = ("complete", "complete_with_gaps")


def coverage(s) -> list[dict]:
    """Is every live source's history copied? One row per live scope (approved, client active), judged on its
    stream's full copies (backfill or reconcile; a Drive account's folders share one stream).

    complete: a full copy succeeded (a later failed re-check doesn't remove what it copied). complete_with_gaps:
    it finished with only settled gaps. copying: under way. incomplete: stopped or partial, resume it.
    not_started: nothing collected yet. blocked: the connector lost access."""
    out = []
    scopes = s.execute(select(SourceScope, ConnectorAccount)
                       .join(ConnectorAccount, ConnectorAccount.id == SourceScope.connector_account_id)
                       .where(live_scope()).order_by(ConnectorAccount.provider, SourceScope.name)).all()
    for scope, account in scopes:
        stream_id = s.scalar(select(SyncStream.id).where(SyncStream.connector_account_id == account.id,
                                                          SyncStream.stream_key == _stream_key(account.provider, scope)))
        # Runs of its stream, plus legacy-path runs (local learning runs: no stream, filed under the scope).
        mine = or_(SyncRun.stream_id == stream_id, and_(SyncRun.stream_id.is_(None), SyncRun.scope_id == scope.id))
        runs = s.execute(
            select(SyncRun, CoverageWindow).join(CoverageWindow, CoverageWindow.run_id == SyncRun.id)
            .where(mine, SyncRun.mode.in_(("backfill", "reconcile")))
            .order_by(SyncRun.started_at.desc())).all()
        latest, cov = runs[0] if runs else (None, None)
        # A finished copy counts only if it reaches back as far as the newest copy asked for: a short 30-day test
        # copy must not mark a source complete while its full-history copy is still running or has failed.
        def covers(r):
            return r.window_start is None or (latest.window_start is not None and r.window_start <= latest.window_start)
        done = next((r for r, _ in runs if r.state == "succeeded" and covers(r)), None)
        gaps = Counter(g.get("reason", "unknown") for g in (cov.gaps if cov else []))
        if account.state != "active":
            verdict = "blocked"
        elif done is not None:
            verdict = "complete"
        elif latest is None:
            verdict = "not_started"
        elif latest.state in ("queued", "running"):
            verdict = "copying"
        elif latest.state == "partial" and set(gaps) <= SETTLED_GAPS and not cov.counts.get("failed"):
            verdict = "complete_with_gaps"
        else:
            verdict = "incomplete"
        shown = done or latest
        out.append({"provider": account.provider, "scope": scope.name,
                    "client": s.get(Business, scope.business_id).slug if scope.business_id else "shared",
                    "verdict": verdict, "run_id": str(latest.id) if latest else None,
                    "run_state": latest.state if latest else None, "error": latest.error_class if latest else None,
                    "gaps": dict(gaps), "window": ("full history" if shown.window_start is None
                                                   else f"from {shown.window_start:%Y-%m-%d}") if shown else ""})
    return out


def sweep(s) -> int:
    """Start whatever is due, in one short transaction. Costs 3 queries when nothing is.

    1. Live sources that nothing collects yet (just linked or reactivated, or a link whose queueing step was
       lost): `collect`. 2. Enabled streams that are due: a full re-check when its time has come or the
       client was reactivated since the last one, else an incremental read. Due streams are locked SKIP
       LOCKED, so a stream a page job holds is simply left for the next sweep."""
    if not get_settings().sync_scheduler_enabled:
        return 0
    if not s.scalar(select(func.pg_try_advisory_xact_lock(SWEEP_LOCK))):
        return 0  # another worker is sweeping
    settings, now, count = get_settings(), db_now(s), 0
    key = case((ConnectorAccount.provider == "drive", "drive:account"), else_=cast(SourceScope.id, String))
    idle = s.execute(select(SourceScope.id).join(ConnectorAccount, ConnectorAccount.id == SourceScope.connector_account_id)
        .outerjoin(SyncStream, and_(SyncStream.connector_account_id == SourceScope.connector_account_id,
                                    SyncStream.stream_key == key))
        .where(live_scope(), ConnectorAccount.state == "active", or_(SyncStream.id.is_(None), ~SyncStream.enabled))
        .order_by(SourceScope.id)).scalars().all()
    for scope_id in idle:
        if collect(s, scope_id) in ("started", "resumed"):
            count += 1
    # A client reactivated after the stream's last full re-check: re-read everything, so the paused weeks are
    # covered (Slack's incremental window is only 7 days). Drive streams are account-wide: any of its folders.
    member, client = aliased(SourceScope), aliased(Business)
    reactivated = exists().where(member.business_id == client.id, member.state == "approved",
        client.status == "active",
        client.status_changed_at > func.coalesce(SyncStream.last_reconciled_at, SyncStream.created_at),
        or_(member.id == SyncStream.scope_id,
            and_(SyncStream.stream_key == "drive:account",
                 member.connector_account_id == SyncStream.connector_account_id)))
    due = s.execute(select(SyncStream, ConnectorAccount.provider, reactivated.label("reactivated"))
        .join(SourceScope, SourceScope.id == SyncStream.scope_id)
        .join(ConnectorAccount, ConnectorAccount.id == SyncStream.connector_account_id)
        .where(SyncStream.enabled, live_scope(), ConnectorAccount.state == "active",
               ~exists().where(SyncRun.stream_id == SyncStream.id, SyncRun.state.in_(("queued", "running"))),
               or_(SyncStream.next_reconcile_at <= now, reactivated,
                   # Fathom has no change feed: only its daily full re-check.
                   and_(SyncStream.next_sync_at <= now, ConnectorAccount.provider != "fathom")))
        .order_by(SyncStream.id)
        .with_for_update(of=SyncStream, skip_locked=True)).all()
    for stream, provider, was_reactivated in due:
        if was_reactivated or stream.next_reconcile_at <= now:
            request_run(s, stream.scope_id, "reconcile")
            stream.next_reconcile_at = now + timedelta(seconds=settings.reconcile_interval_seconds)
        else:
            request_run(s, stream.scope_id, "incremental")
            stream.next_sync_at = now + timedelta(seconds=sync_interval(provider))
        count += 1
    return count
