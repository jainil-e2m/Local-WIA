"""PostgreSQL work runner: claim, execute outside a transaction, publish under a lease.

    python -m backend.workers.runner            # all configured lanes, runs forever
    python -m backend.workers.runner --drain    # stop when no due work remains (tests, one-shot runs)
"""
import argparse
import random
import signal
import threading
import time
from datetime import timedelta
from uuid import UUID

from psycopg import OperationalError as DriverOperationalError
from sqlalchemy.exc import DBAPIError, TimeoutError as PoolTimeout

from backend.config import get_settings
from backend.db import transaction
from backend.logging.config import configure, get_logger
from backend.models.db import ConnectorAccount, SourceScope, SyncRun, WorkItem
from backend.services.shared.errors import (AuthInvalidError, CrashLoopError, IntakeError, ScopeDeniedError,
                                            ThrottledError)
from backend.workers import queue
from backend.services import ads
from backend.services.ai import runner as ai_runner
from backend.services.intake import leadlock_app, sync
from backend.workers.jobs import intake

log = get_logger("worker")
JOBS = {**intake.JOBS, **leadlock_app.JOBS, ai_runner.JOB: ai_runner.run_job, ads.JOB: ads.run_job}
AI_SWEEP_SECONDS = 300
# Tries count claims whose worker died mid-job too. A job's normal retries stop at the length of its ladder, so only
# crashes pass it by CRASH_MARGIN: a page that kills its worker (out of memory, say) then fails its run instead of
# looping forever (5 tries for an intake page). `kb run resume` resets the count.
CRASH_MARGIN = 2


def retry_delays(kind: str, payload: dict) -> list[int]:
    """AI jobs outlast a provider outage (services/ai/runner.py RETRY_DELAYS); everything else retries for minutes."""
    return (kind == ai_runner.JOB and ai_runner.retry_delays(payload)) or get_settings().retry_delays_seconds


def crash_limit(kind: str, payload: dict) -> int:
    return len(retry_delays(kind, payload)) + CRASH_MARGIN
stopping = threading.Event()  # set by SIGTERM (Railway redeploy): finish the current job, claim nothing new


class Heartbeat(threading.Thread):
    """Renews the lease with its own short sessions while a long job runs."""

    def __init__(self, work_id, lease_token):
        super().__init__(daemon=True)
        self.work_id, self.lease_token = work_id, lease_token
        self.stop = threading.Event()

    def run(self):
        interval = max(5, get_settings().lease_seconds // 3)
        while not self.stop.wait(interval):
            try:
                with transaction() as session:
                    if queue.renew(session, self.work_id, self.lease_token) is False:
                        return
            except Exception as exc:
                # A lock/connection error does not establish ownership loss. Publication
                # will recheck the deadline; never let a heartbeat fail the business run.
                log.warning("heartbeat unavailable", extra={"work_id": str(self.work_id),
                            "error_type": type(exc).__name__})


def run_one(lanes: list[str]) -> bool:
    try:
        with transaction() as session:
            item = queue.claim(session, lanes)
            if item is None:
                return False
            work_id, token, kind, payload, attempt = item.id, item.lease_token, item.kind, item.payload, item.attempt
    except (DBAPIError, PoolTimeout, DriverOperationalError):
        log.warning("queue unavailable; persisted leases will recover")
        return False

    if attempt >= crash_limit(kind, payload):
        _handle_failure(work_id, token, kind, payload, attempt,
                        CrashLoopError(f"worker died {attempt} times running this job"))
        return True
    job = JOBS.get(kind)
    beat = Heartbeat(work_id, token)
    beat.start()
    try:
        if job is None:
            raise IntakeError(f"no job registered for {kind}")
        job(work_id, token, payload)
        _verify_completion(work_id, token)
    except queue.LeaseLostError:
        log.warning("lease lost; result discarded", extra={"work_id": str(work_id), "kind": kind})
    except Exception as exc:  # classify, never swallow
        _handle_failure(work_id, token, kind, payload, attempt, exc)
    finally:
        beat.stop.set()
        beat.join(timeout=1)
    return True


def _verify_completion(work_id, token):
    """Durable jobs own success. A handler returning is not a commit receipt."""
    with transaction() as session:
        item = session.get(WorkItem, work_id)
        if item is not None and item.state == "succeeded":
            return
        if item is None or item.lease_token != token:
            raise queue.LeaseLostError(str(work_id))
        raise IntakeError("job returned without transaction-local completion")


def _transient_database_error(exc):
    original = getattr(exc, "orig", exc)
    code = getattr(original, "sqlstate", None)
    return (isinstance(exc, (PoolTimeout, DriverOperationalError)) or
            bool(getattr(exc, "connection_invalidated", False)) or
            (isinstance(exc, DBAPIError) and not code) or
            bool(code and (code.startswith("08") or code in ("40001", "40P01", "55P03", "57014"))))


def _handle_failure(work_id, token, kind, payload, attempt, exc):
    """Fence ALL failure effects on the work row, including connector/run changes.

    Commit acknowledgement and post-commit cleanup can fail after success. In that
    case the cleared token makes this an intentional no-op, not a failed run.
    """
    try:
        with transaction() as session:
            try:
                item = queue.assert_lease(session, work_id, token)
            except queue.LeaseLostError:
                return False
            # Only the immutable persisted job may identify the run/account to change.
            kind, payload, attempt = item.kind, item.payload, item.attempt
            if kind == intake.pipeline.PAGE_JOB and payload.get("input_key"):
                from backend.services.intake import positions
                try:
                    run_id = UUID(payload.get("run_id", ""))
                except (ValueError, TypeError, AttributeError):
                    run_id = None
                run = session.get(SyncRun, run_id, with_for_update=True) if run_id else None
                try:
                    executor = "sync" if run is not None and run.stream_id else "legacy"
                    if not positions.validate(session, item, run, payload, executor):
                        # A different work row already published this logical page.
                        # Acknowledge this duplicate, without retry/block/fail effects.
                        return False
                except positions.PageInvariantError as invariant:
                    exc = invariant
            error_class = "transient" if _transient_database_error(exc) else getattr(exc, "error_class", "bug")
            retryable = error_class == "transient" or getattr(exc, "retryable", False)
            # Provider/DB exception messages can contain URLs, queries or values.
            safe = f"{type(exc).__name__}: {error_class}"
            delays = retry_delays(kind, payload)
            permanent = False
            if isinstance(exc, ThrottledError):
                state, delay = "retry_wait", exc.retry_after or 30
            elif isinstance(exc, (AuthInvalidError, ScopeDeniedError)):
                state, delay, permanent = "blocked", None, True
            elif retryable and attempt < len(delays):
                state = "retry_wait"
                delay = delays[attempt] * (1 + random.uniform(-0.2, 0.2))
                item.attempt = attempt + 1
            else:
                state, delay, permanent = "failed", None, True
                item.attempt = attempt + 1
            if permanent:
                # Runs and connector state are in this same transaction, never a
                # callback after an ownership-blind settlement transaction.
                intake.on_permanent_failure(session, kind, payload, error_class)
                if error_class == "auth_invalid" and payload.get("scope_id"):
                    scope = session.get(SourceScope, payload["scope_id"])
                    if scope is not None:
                        account = session.get(ConnectorAccount, scope.connector_account_id, with_for_update=True)
                        account.state, account.blocked_reason = "blocked", safe
            item.state, item.lease_token, item.lease_until = state, None, None
            item.last_error_class, item.last_error = error_class, safe
            if delay is not None:
                item.next_run_at = queue.db_now(session) + timedelta(seconds=delay)
        log.error("job attempt settled", extra={"work_id": str(work_id), "kind": kind,
                                               "error_class": error_class, "state": state})
        return True
    except (DBAPIError, PoolTimeout, DriverOperationalError):
        # Unknown commit outcome: leave the durable row as the authority. Once DB
        # access recovers, success is visible or the old claim can be reclaimed.
        log.warning("failure settlement unavailable; awaiting durable recovery", extra={"work_id": str(work_id)})
        return False


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--drain", action="store_true", help="exit when no due work remains")
    parser.add_argument("--lanes", default=None)
    args = parser.parse_args()
    configure()
    settings = get_settings()
    signal.signal(signal.SIGTERM, lambda *_: stopping.set())
    lanes = (args.lanes or settings.worker_lanes).split(",")
    log.info("worker started", extra={"lanes": lanes, "mode": settings.mode,
                                      "sync_scheduler": settings.sync_scheduler_enabled})
    idle_since, last_sweep, last_ai_sweep = None, float("-inf"), float("-inf")
    ai = "analysis" in lanes and settings.ai_mode == "live"  # only the AI worker finds AI work, only while live
    while not stopping.is_set():
        # The scheduler lives in the worker loop: every worker may sweep, the advisory lock lets one through.
        if settings.sync_scheduler_enabled and time.monotonic() - last_sweep >= settings.scheduler_sweep_seconds:
            last_sweep = time.monotonic()
            _sweep()
        if ai and time.monotonic() - last_ai_sweep >= AI_SWEEP_SECONDS:
            last_ai_sweep = time.monotonic()
            _ai_sweep()
        did_work = run_one(lanes)
        if did_work:
            idle_since = None
            continue
        if args.drain:
            idle_since = idle_since or time.monotonic()
            if _nothing_pending(lanes) or time.monotonic() - idle_since > 300:
                log.info("drained")
                return
        stopping.wait(settings.poll_idle_seconds)
    log.info("worker stopped (SIGTERM): the current job finished; nothing new was claimed")


def _sweep() -> None:
    try:
        with transaction() as session:
            started = sync.sweep(session)
            ads.sweep(session)  # one ad-figures pull a day, while an ad platform is configured
        if started:
            log.info("sync sweep", extra={"runs_started": started})
    except Exception as exc:  # a failed sweep is retried next interval; it must never stop the worker
        log.warning("sync sweep failed", extra={"error_type": type(exc).__name__})


def _ai_sweep() -> None:
    from backend.services.ai import sweep
    try:
        with transaction() as session:
            queued = sweep.sweep(session)
        if queued:
            log.info("ai sweep", extra={"due": queued})
    except Exception as exc:  # retried next interval; never stops the worker
        log.warning("ai sweep failed", extra={"error_type": type(exc).__name__})


def _nothing_pending(lanes) -> bool:
    from sqlalchemy import func, select
    with transaction() as session:
        n = session.execute(
            select(func.count()).select_from(WorkItem)
            .where(WorkItem.lane.in_(lanes), WorkItem.state.in_(("pending", "retry_wait", "claimed")))
        ).scalar_one()
    return n == 0


if __name__ == "__main__":
    main()
