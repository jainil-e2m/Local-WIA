"""S2–S8 orchestration for one page of one approved scope.

Order of operations per page (Ingestion design §1.3 invariants 1–3):
1. read scope/run/contacts in a short transaction;
2. call the provider adapter OUTSIDE any transaction;
3. in ONE transaction: check the lease, persist every record, update coverage,
   advance the cursor, then either enqueue the next page or finalise the run.
A crash before step 3 commits leaves nothing half-applied; the page is retried.
"""
import json
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.db import transaction
from backend.logging.config import get_logger
from backend.models.db import ConnectorAccount, Contact, CoverageWindow, SourceScope, SyncCursor, SyncRun
from backend.models.db.base import utcnow
from backend.models.domain.intake import ApprovedContact, ChangeBatch, IntakeContext
from backend.services.intake import positions
from backend.services.intake.scoping import is_live, live_contacts
from backend.services.intake.adapters import get_adapter
from backend.services.intake.persist import IdentityCache, PersistOutcome, persist_record
from backend.services.shared.errors import AuthInvalidError
from backend.workers import queue

log = get_logger(__name__)

PAGE_JOB = "intake.backfill_page"
COVERAGE_CONTRACT = "intake-coverage-v1"


def window_bounds(days: int | None, now: datetime | None = None) -> tuple[datetime | None, datetime]:
    """days=None is the production case: no lower bound, full obtainable history."""
    end = now or datetime.now(UTC)
    return (end - timedelta(days=days) if days else None), end


def start_backfill(session: Session, scope_ids: list[UUID], days: int | None) -> list[UUID]:
    # The legacy copy: restarts from the beginning when stopped. Production uses sync.request_run(..., "backfill").
    window_start, window_end = window_bounds(days)
    run_ids = []
    for scope_id in scope_ids:
        scope = session.get(SourceScope, scope_id)
        if scope is None or not is_live(session, scope):
            continue
        run = SyncRun(id=uuid4(), connector_account_id=scope.connector_account_id, scope_id=scope.id,
                      mode="backfill", window_start=window_start, window_end=window_end,
                      generation=1, checkpoint={"cursor": None})
        session.add(run)
        session.flush()  # no ORM relationships: make insert order explicit
        session.add(CoverageWindow(id=uuid4(), scope_id=scope.id, run_id=run.id, window_start=window_start,
                                   window_end=window_end, contract_version=COVERAGE_CONTRACT))
        session.flush()
        positions.enqueue_page(session, run, "legacy")
        run_ids.append(run.id)
    return run_ids


def _context(session: Session, scope: SourceScope, run: SyncRun) -> IntakeContext:
    from backend.services.intake.admission import lookup
    contacts = live_contacts(session)
    return IntakeContext(
        window_start=run.window_start, window_end=run.window_end, scope_external_id=scope.external_id,
        scope_kind=scope.kind, settings=get_settings(),
        contacts=[ApprovedContact(c.business_id, c.email, c.domain) for c in contacts],
        connector_account_id=scope.connector_account_id, scope_id=scope.id,
        association_mode=scope.association_mode, business_id=scope.business_id,
        lookup_records=lambda keys: lookup(scope.connector_account_id, keys),
    )


def run_backfill_page(work_id: UUID, lease_token: UUID, payload: dict) -> None:
    if payload.get("executor") == "sync":
        from backend.services.intake.execution import run_page
        return run_page(work_id, lease_token, payload, adapter_factory=get_adapter)
    scope_id, run_id = UUID(payload["scope_id"]), UUID(payload["run_id"])

    with transaction() as session:
        item = queue.assert_lease(session, work_id, lease_token)
        run = session.get(SyncRun, run_id, with_for_update=True)
        if not positions.validate(session, item, run, payload, "legacy"):
            return
        scope = session.get(SourceScope, scope_id)
        account = session.get(ConnectorAccount, scope.connector_account_id)
        if account.state != "active":
            raise AuthInvalidError(f"connector account blocked: {account.blocked_reason}")
        if not is_live(session, scope):
            fail_run(run_id, "scope_retired", session=session)
            queue.complete(session, work_id, lease_token)
            return
        ctx = _context(session, scope, run)
        provider = account.provider
        cursor = run.checkpoint["cursor"]

    adapter = get_adapter(provider)
    batch: ChangeBatch = adapter.backfill_page(ctx, cursor)

    with transaction() as session:
        item = queue.assert_lease(session, work_id, lease_token)
        run = session.get(SyncRun, run_id, with_for_update=True)
        if not positions.validate(session, item, run, payload, "legacy"):
            return
        scope = session.get(SourceScope, scope_id, with_for_update=True)
        account = session.get(ConnectorAccount, scope.connector_account_id)
        if not is_live(session, scope) or account.state != "active":
            fail_run(run_id, "source_inactive", session=session)
            queue.complete(session, work_id, lease_token)
            return
        coverage = session.execute(
            select(CoverageWindow).where(CoverageWindow.run_id == run_id).with_for_update()
        ).scalar_one()

        outcome = PersistOutcome()
        identities = IdentityCache(session, scope.connector_account_id)
        for rec in batch.records:
            target = membership_scope(session, scope, batch, rec)
            if target is None:
                batch.excluded += 1
                continue
            persist_record(session, target, ctx, rec, identities, adapter.parser_version, outcome)

        counts = dict(coverage.counts)
        counts["discovered"] += batch.discovered
        counts["excluded"] += batch.excluded
        counts["stored_content"] += outcome.stored_content
        counts["stored_metadata"] += outcome.stored_metadata
        counts["unchanged"] += outcome.unchanged
        for gap in batch.gaps:
            key = {"scope_denied": "inaccessible", "not_found": "inaccessible",
                   "unsupported": "unsupported"}.get(gap.reason, "failed")
            counts[key] += 1
        coverage.counts = counts
        coverage.gaps = coverage.gaps + [{"external_id": g.external_id, "reason": g.reason} for g in batch.gaps]
        run.pages += 1

        next_cursor = json.dumps(batch.checkpoint, sort_keys=True) if batch.checkpoint else batch.next_cursor
        _store_cursor(session, scope_id, next_cursor)
        run.checkpoint = {"cursor": next_cursor}
        if batch.terminal:
            _finalise(session, scope, run, coverage)
        else:
            if next_cursor is None or run.checkpoint == payload["checkpoint"]:
                raise positions.PageInvariantError("nonterminal page did not advance its checkpoint")
            positions.enqueue_page(session, run, "legacy")
        queue.complete(session, work_id, lease_token)
    log.info("page committed", extra={"scope_id": str(scope_id), "run_id": str(run_id), "page": run.pages,
                                      "records": len(batch.records), "gaps": len(batch.gaps),
                                      "terminal": batch.terminal})


def membership_scope(session: Session, scope: SourceScope, batch: ChangeBatch, rec) -> SourceScope | None:
    """The scope a record is stored and associated under.

    A reader that walks more than its own scope (Drive walks every approved folder on the account) says
    where each record really sits in `batch.memberships`. Storing it under the run's scope instead filed
    files under whichever client's run reached them first, e.g. one client's questionnaires under another.
    Mirrors execution.publish: the first live listed scope wins; only paused (archived) scopes → skip.
    """
    membership = next((m for m in batch.memberships
                       if m["kind"] == rec.record_kind and m["external_id"] == rec.external_id), None)
    if membership is None:
        return scope
    listed = [UUID(x) for x in membership["scope_ids"]]
    if not listed:
        return scope
    live = [s for s in session.execute(select(SourceScope).where(
        SourceScope.id.in_(listed), SourceScope.connector_account_id == scope.connector_account_id)).scalars()
        if is_live(session, s)]
    if scope.id in {s.id for s in live}:
        return scope
    return min(live, key=lambda s: listed.index(s.id)) if live else None


def _store_cursor(session: Session, scope_id: UUID, cursor: str | None) -> None:
    row = session.execute(
        select(SyncCursor).where(SyncCursor.scope_id == scope_id, SyncCursor.mode == "backfill")
    ).scalar_one_or_none()
    if row is None:
        session.add(SyncCursor(id=uuid4(), scope_id=scope_id, mode="backfill", cursor=cursor))
    else:
        row.cursor = cursor
        row.generation += 1


def _finalise(session: Session, scope: SourceScope, run: SyncRun, coverage: CoverageWindow) -> None:
    complete = coverage.counts["failed"] == 0 and coverage.counts["inaccessible"] == 0
    coverage.state = "complete" if complete else "partial"
    run.state = "succeeded" if complete else "partial"
    run.finished_at = utcnow()
    if complete:
        # Only a fully accounted run moves last-successful-sync (invariant 2).
        scope.last_successful_sync_at = run.window_end


def fail_run(run_id: UUID, error_class: str, *, session=None) -> None:
    if session is None:
        with transaction() as own_session:
            fail_run(run_id, error_class, session=own_session)
        return
    run = session.get(SyncRun, run_id, with_for_update=True)
    if run is None or run.state not in ("queued", "running"):
        return
    run.state, run.error_class, run.finished_at = "failed", error_class, utcnow()
    coverage = session.execute(select(CoverageWindow).where(CoverageWindow.run_id == run_id)).scalar_one()
    coverage.state = "failed"
