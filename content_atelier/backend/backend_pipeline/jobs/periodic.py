"""Scheduled work, keyed by period (plan 0.B6, Appendix B).

A task has a name, a function that says which period it is due for (a date, an ISO week, an hour; None when it is not
due) and the work. The scheduler claims `(task, period)` in the `settings` table before it runs, so a restart, a
second scheduler or a missed pass never runs a period twice, and a pass after downtime still runs the period that was
missed (the key is the period, not the time the tick fires). A run that raised, or one left `running` by a process
that died, is claimed again on a later pass until it has had `MAX_ATTEMPTS`.
"""
from __future__ import annotations

import json
import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from ..database import connect

log = logging.getLogger(__name__)

MAX_ATTEMPTS = 3
STALE = timedelta(hours=1)
# A run that raised is claimed again only after this long times its failed attempts (10, 20, 30 minutes...), so a passing
# outage cannot use up every attempt within a minute: 1 November 2026's weekly run used its three in 90 seconds, and
# only an edit of its claim in the database brought it back.
RETRY_AFTER = timedelta(minutes=10)


def claim(storage, key, *, by="scheduler", attempts=MAX_ATTEMPTS) -> bool:
    """Record the run before it starts; only the first caller to claim it runs it. A run that raised was counted by
    `fail` and waits RETRY_AFTER per failed attempt; one left `running` by a process that died is counted here, when it is
    claimed again, so a run that keeps killing its process stops at `attempts` like one that keeps raising."""
    with connect(storage.database_url) as conn:
        conn.execute("SELECT pg_advisory_xact_lock(7312)")
        row = conn.execute("""INSERT INTO settings(key,value,updated_by) VALUES (%s,%s,%s)
            ON CONFLICT (key) DO UPDATE SET value=jsonb_build_object('state','running','attempts',
                COALESCE((settings.value->>'attempts')::int,1)
                + CASE WHEN settings.value->>'state'='running' THEN 1 ELSE 0 END),updated_at=now()
            WHERE (settings.value->>'state'='failed'
                   AND settings.updated_at <= now() - %s * COALESCE((settings.value->>'attempts')::int,1)
                   OR settings.value->>'state'='running' AND settings.updated_at < now()-%s)
              AND COALESCE((settings.value->>'attempts')::int,1)
                  + CASE WHEN settings.value->>'state'='running' THEN 1 ELSE 0 END < %s
            RETURNING key""", (key, json.dumps({"state": "running", "attempts": 0}), by, RETRY_AFTER, STALE, attempts)).fetchone()
        conn.commit()
    return bool(row)


def fail(storage, key, error: Exception):
    with connect(storage.database_url) as conn:
        conn.execute("""UPDATE settings SET value=jsonb_build_object('state','failed','error',%s::text,
            'attempts',COALESCE((value->>'attempts')::int,0)+1),updated_at=now() WHERE key=%s""",
                     (f"{type(error).__name__}: {error}"[:500], key))
        conn.commit()


def finish(storage, key, value):
    with connect(storage.database_url) as conn:
        conn.execute("UPDATE settings SET value=%s,updated_at=now() WHERE key=%s", (json.dumps({"state": "done", **value}), key))
        conn.commit()


def day(now: datetime, *, hour: int = 0) -> str | None:
    """The date once `hour` UTC has passed (a daily task)."""
    return now.date().isoformat() if now.hour >= hour else None


def hour(now: datetime) -> str:
    """The UTC hour (an hourly task): a pass later in the same hour finds it claimed."""
    return now.strftime("%Y-%m-%dT%H")


def week(now: datetime, *, weekday: int = 0, hour: int = 0) -> str | None:
    """The ISO week of a task due on `weekday` from `hour` UTC; a later pass in the same week still runs a missed one."""
    due = (now.weekday(), now.hour) >= (weekday, hour)
    year, number, _ = now.isocalendar()
    return f"{year}-W{number:02d}" if due else None


@dataclass(frozen=True)
class Task:
    name: str
    period: Callable[[datetime], str | None]
    run: Callable[[datetime], dict | None]
    attempts: int = MAX_ATTEMPTS


def run_due(storage, tasks, now: datetime | None = None) -> dict:
    """One pass over `tasks`: each due `(task, period)` runs at most once. Returns {'ran': [...], 'failed': [...]}."""
    now = now or datetime.now(UTC)
    ran, failed = [], []
    for task in tasks:
        period = task.period(now)
        if period is None:
            continue
        key = f"schedule.{task.name}.{period}"
        if not claim(storage, key, attempts=task.attempts):
            continue
        try:
            result = task.run(now) or {}
        except Exception as error:
            log.exception("Scheduled task %s (%s) failed; it runs again on a later pass", task.name, period)
            fail(storage, key, error)
            failed.append(f"{task.name}:{period}")
            continue
        finish(storage, key, {"result": json.loads(json.dumps(result, default=str))})
        ran.append(f"{task.name}:{period}")
    return {"ran": ran, "failed": failed}
