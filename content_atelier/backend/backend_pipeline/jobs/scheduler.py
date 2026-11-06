"""The scheduler and the reconcile loop for every job (plan 0.B6, R35).

One process, one loop, every 30 seconds:

1. **reconcile** (every pass): jobs whose worker is gone are settled (`recover.py`), intake jobs waiting for a retry
   time are released, and every committed row that is ready but has no live RQ job is put back on its queue. This is
   what makes a flushed Redis, a lost dispatch or a killed worker end correctly after one pass.
2. **scheduled work**: the cycle's weekly collection and finalisation (intake), the context staleness and learning jobs,
   and the keyed periodic tasks (`periodic.py`: expiry, reminders and backups as their phases land). Each runs at most
   once per period, and a pass after downtime runs the periods it missed.
3. **review documents and alerts** (every pass): the week's review document for a scheduled cycle that has finished
   (3.B11), then the alert scan, which opens, counts and clears the failure alerts the app shows (6.B4, alerts.py).
4. **heartbeat**: the pass records when it finished, so job health can say the scheduler is alive.
"""
from __future__ import annotations

import ctypes
import json
import logging
import os
import sys
import time
from datetime import UTC, datetime

from . import periodic
from .dispatch import connect_redis, dispatch_ready
from .recover import recover_expired

log = logging.getLogger(__name__)

HEARTBEAT_KEY = "jobs.scheduler.heartbeat"
PASS_SECONDS = 30
# The scheduler's resident memory, past which it starts itself again between two passes (os.execv: the same process and
# container, so the platform counts no restart). On production it grew by about 1 GB a day, a step at each hour's upkeep,
# until a deploy reset it (2.4 GB on 30 October to 5.5 GB on 2 November, 8 GB the limit). Every pass is idempotent and the
# scheduled tasks are claimed in the database, so starting again between passes loses nothing.
MEMORY_LIMIT_MB = int(os.getenv("ATELIER_SCHEDULER_MEMORY_LIMIT_MB", "1024"))
# Never sooner than this after it started, so a limit set below what the process needs at rest cannot loop it.
MIN_UPTIME_SECONDS = 600
STARTED = time.monotonic()


def release_waiting(repo) -> int:
    """Intake jobs waiting for a retry time go back to queued once that time has passed."""
    with repo.connection() as conn:
        return conn.execute("""UPDATE pipeline_jobs SET status='queued',updated_at=now() WHERE status='waiting'
            AND stage='intake_fathom' AND COALESCE((progress_details->>'retry_at')::timestamptz,updated_at+interval '10 minutes')<=now()
            """).rowcount


def release_budget_waits(repo) -> list[str]:
    """Jobs waiting for a standing weekly budget (6.B3) go back to queued once that purpose has room again."""
    from ..llm.standing import release_waits
    with repo.connection() as conn:
        return release_waits(conn)


def reconcile(repo, redis_connection=None) -> dict:
    """One reconcile pass over every job. Returns what it did, for the log and the tests."""
    recovered = recover_expired(repo)
    released = release_waiting(repo)
    budget = release_budget_waits(repo)
    dispatched = dispatch_ready(repo, redis_connection)
    return {"recovered": recovered, "released": released, "budget_released": budget, "dispatched": dispatched}


def beat(storage, now: datetime) -> None:
    from ..database import connect
    with connect(storage.database_url) as conn:
        conn.execute("""INSERT INTO settings(key,value,updated_by) VALUES (%s,%s,'scheduler')
            ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value,updated_at=now()""",
                     (HEARTBEAT_KEY, json.dumps({"at": now.isoformat()})))
        conn.commit()


def renew_budgets(storage, now: datetime) -> dict:
    """The standing weekly budgets (6.B3): this week's plan for every purpose, last week's closed, waiting jobs released."""
    from ..database import connect
    from ..llm.standing import renew
    with connect(storage.database_url, vectors=False) as conn:
        result = renew(conn, now)
        conn.commit()
    return result


def review_documents(storage, now: datetime) -> dict:
    """The week's review document for each scheduled cycle that has finished (cycle/schedule.py)."""
    from ..cycle.schedule import review_documents as make
    return make(storage, now)


def scan_alerts(storage, now: datetime) -> dict:
    """The failure alerts (6.B4): one scan, in its own transaction, after the pass's other work."""
    from ..alerts import scan
    from ..database import connect
    with connect(storage.database_url, vectors=False) as conn:
        result = scan(conn, now)
        conn.commit()
    return result


def upkeep(storage, models, now: datetime) -> dict:
    """The archive kept current (upkeep.py): new documents' scenes extracted within the hour."""
    from ..repository import ContentRepository
    from ..upkeep import hourly
    return hourly(ContentRepository(storage), models, now)


def periodic_tasks(storage, models):
    """The keyed tasks the scheduler runs (periodic.Task): the weekly budgets (6.B3), the hourly upkeep and the scheduled
    weekly cycle (3.B11, keyed by its scheduled day). The context jobs claim their own periods and run as their own part of
    `tick`; the nightly dump is the db-backup service's (backup.py)."""
    from ..cycle import schedule
    return [periodic.Task("standing_budgets", lambda now: periodic.week(now), lambda now: renew_budgets(storage, now)),
            periodic.Task("upkeep", periodic.hour, lambda now: upkeep(storage, models, now)),
            periodic.Task(schedule.TASK, lambda now: schedule.due(storage, now), lambda now: schedule.run(storage, models, now),
                          attempts=schedule.ATTEMPTS)]


def tick(storage, models, *, repo=None, intake_repo=None, redis_connection=None, now=None, tasks=None) -> dict:
    """One scheduler pass. A failure in one part is logged and the others still run."""
    from ..repository import ContentRepository
    now = now or datetime.now(UTC)
    repo = repo or ContentRepository(storage)
    result: dict = {}
    parts = [("reconcile", lambda: reconcile(repo, redis_connection))]
    if intake_repo is not None:
        from ..intake import runtime
        parts.append(("intake", lambda: runtime.tick(intake_repo, now=now)))
    if storage.context_enabled:
        from ..knowledge import scheduler as context
        parts.append(("context", lambda: context.tick(storage, models, now)))
    parts.append(("periodic", lambda: periodic.run_due(storage, tasks if tasks is not None else periodic_tasks(storage, models), now)))
    parts.append(("review_documents", lambda: review_documents(storage, now)))
    parts.append(("alerts", lambda: scan_alerts(storage, now)))
    from ..slack_schedule_notifications import tick as notify_schedules
    # Earlier periodic work may take minutes: notification leases need the current clock, not the pass's start.
    parts.append(("slack_schedules", lambda: notify_schedules(storage)))
    for name, part in parts:
        try:
            result[name] = part()
        except Exception:
            log.exception("Scheduler part %s failed; the next pass retries it", name)
            result[name] = {"error": True}
    try:
        beat(storage, now)
    except Exception:
        log.exception("Scheduler heartbeat could not be written")
    return result


def resident_mb() -> float | None:
    """This process's resident memory in MB (Linux), or None where /proc is not there."""
    try:
        with open("/proc/self/status") as status:
            return next(int(line.split()[1]) / 1024 for line in status if line.startswith("VmRSS:"))
    except (OSError, StopIteration, ValueError):
        return None


def release_memory() -> None:
    """Hand freed heap back to the system (glibc keeps it otherwise); nothing where glibc is not the allocator."""
    try:
        ctypes.CDLL("libc.so.6").malloc_trim(0)
    except (OSError, AttributeError):
        pass


def restart_if_large(limit_mb: int = MEMORY_LIMIT_MB, *, execv=os.execv, uptime: float | None = None) -> bool:
    """Between passes: past the limit, start the scheduler again in this process. Returns False when it did not."""
    used = resident_mb()
    uptime = time.monotonic() - STARTED if uptime is None else uptime
    if used is None or used < limit_mb or uptime < MIN_UPTIME_SECONDS:
        return False
    log.warning("Scheduler uses %.0f MB, past %d MB: starting it again between passes", used, limit_mb)
    for handler in logging.getLogger().handlers:
        handler.flush()
    execv(sys.executable, [sys.executable, "-m", "backend_pipeline.jobs", "scheduler"])
    return True


def loop(storage, models, *, intake_repo=None, once=False, sleep_seconds=PASS_SECONDS):
    redis_connection = None
    while True:
        try:
            redis_connection = redis_connection or connect_redis()
            done = tick(storage, models, intake_repo=intake_repo, redis_connection=redis_connection)
        except Exception:
            log.exception("Scheduler pass failed; retrying")
            redis_connection, done = None, {"error": True}
        if once:
            return done
        release_memory()
        restart_if_large()
        time.sleep(sleep_seconds)
