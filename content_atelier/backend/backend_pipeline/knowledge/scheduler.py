"""When the context jobs run (L.B6, L.B8) until Phase 0's scheduler (0.B6) takes them over.

`storage_cli context-scheduler` loops: the staleness job once a day after `ATELIER_CONTEXT_NIGHTLY_HOUR` (UTC,
default 3), and the learning loop once a week on `ATELIER_CONTEXT_MINING_WEEKDAY` (0 is Monday, the default),
over the seven days before it. Each run is recorded in `settings`, so a restart or a second scheduler does not
repeat a day or a week. `--once` makes one pass, for a cron service.

A missed mining day is caught up (L.B11): each pass after the nightly hour looks for the latest mining weekday on or
before today, and runs it if it has not run, over the week before that day. When earlier weekdays were missed too, the
window starts where the last pass that ran stopped reading (that pass's weekday), at most `context.mining.support_weeks`
weeks back, so nothing between two passes goes unread. Every pass also queues the benchmark of an approved identity change that waits for one,
when a standing run plan can pay for it (`benchmarking.py`).

The learning loop's categorisation model runs only in live mode (`ATELIER_CONTEXT_MINING_LIVE=true`), under the
active run plan (E.B1) and S.B1's routing; otherwise edits are categorised by rules.
"""
from __future__ import annotations

import logging
import time
from datetime import UTC, date, datetime, timedelta

from ..database import connect
# The claim-before-run rule is shared with the rest of the scheduler (jobs/periodic.py): a job that raised runs again on a
# later pass, up to MAX_ATTEMPTS; one left "running" by a process that died is claimed again after STALE (L.B6, L.B8).
from ..jobs.periodic import MAX_ATTEMPTS, STALE  # noqa: F401
from ..jobs.periodic import claim as _shared_claim
from ..jobs.periodic import fail as _fail  # noqa: F401
from ..jobs.periodic import finish as _finish  # noqa: F401
from . import mining, staleness

log = logging.getLogger(__name__)


def _claim(storage, key) -> bool:
    return _shared_claim(storage, key, by="context scheduler")


def staleness_now(storage, *, actor="staleness job", today=None):
    with connect(storage.database_url) as conn:
        result = staleness.run(conn, actor=actor, today=today)
        conn.commit()
    return result


def _provider(models, storage=None):
    from ..llm import live_provider
    return live_provider(models, storage=storage)


def mining_now(storage, models, *, actor="context_mining", week_id=None, since=None, until=None, live=False):
    model = models.openrouter_context_mining_model if live else None
    if live and not model:
        raise ValueError("Live categorisation needs OPENROUTER_CONTEXT_MINING_MODEL")
    provider = _provider(models, storage) if live else None
    writer = storage.brief_model or models.openrouter_angles_model

    def run(provider, model):
        with connect(storage.database_url) as conn:
            result = mining.run(conn, actor=actor, week_id=week_id, since=since, until=until, provider=provider, model=model,
                                writer_model=writer)
            conn.commit()
        return result
    if provider is None:
        return run(None, None)
    from ..llm.run_plans import RunPlanError
    from ..llm import RoutingError
    import httpx
    try:
        return run(provider, model)
    except (RunPlanError, RoutingError, httpx.HTTPError, ValueError) as error:
        # The categoriser is refused (no plan, no compliant route) or down: the week is still mined, by rules, and the
        # result says why, rather than the week being lost (L.B6). Nothing was committed by the failed attempt.
        log.warning("Context mining categoriser unavailable; categorising by rules: %s", error)
        return {**run(None, None), "categoriser_unavailable": f"{type(error).__name__}: {error}"[:500]}


MINING_KEY = "context.mining.ran."


def mining_day(today: date, weekday: int) -> date:
    """The latest mining weekday on or before `today`: today on the weekday itself, else the one a pass missed."""
    return today - timedelta(days=(today.weekday() - weekday) % 7)


def mining_since(storage, due: date, weeks: int) -> date:
    """Where the pass for `due` starts reading: the week before it, or, when earlier weekdays were missed, the weekday of
    the last pass that ran (its key; it read up to the day before), at most `weeks` weeks back (L.B11)."""
    with connect(storage.database_url) as conn:
        rows = conn.execute("""SELECT key FROM settings WHERE starts_with(key,%s) AND value->>'state'='done'""",
                            (MINING_KEY,)).fetchall()
    earlier = []
    for r in rows:
        try:
            ran = date.fromisoformat(r["key"][len(MINING_KEY):])
        except ValueError:
            continue
        if ran < due:
            earlier.append(ran)
    if not earlier:
        # No pass has run before: the week before the day, as always.
        return due - timedelta(days=7)
    return max(due - timedelta(days=7 * weeks), min(due - timedelta(days=7), max(earlier)))


def mining_pass(storage, models, due: date, today: date, weeks: int, live: bool) -> dict:
    since = mining_since(storage, due, weeks)
    result = mining_now(storage, models, since=since, until=due - timedelta(days=1), live=live)
    # Said when the pass ran after its weekday or read more than one week (L.B11).
    caught_up = due < today or since < due - timedelta(days=7)
    return {**result, "scheduled_for": due.isoformat(), **({"caught_up": True} if caught_up else {})}


def benchmark_now(storage, now) -> dict | None:
    """Queue the benchmark of an approved identity change that waits for one (L.B11); None when none waits."""
    from ..repository import ContentRepository
    from . import benchmarking
    return benchmarking.schedule(ContentRepository(storage), now)


def tick(storage, models, now=None) -> dict:
    """One pass: the day's staleness job and the week's learning loop, each at most once (a missed weekday is caught up),
    and the benchmark of an approved identity change that waits for one."""
    now = now or datetime.now(UTC)
    today = now.date()
    done = {}
    from ..settings_store import values
    settings = values(("context.schedule.nightly_hour", "context.schedule.mining_weekday", "context.schedule.mining_live",
                       "context.mining.support_weeks"), database_url=storage.database_url)
    hour, weekday = settings["context.schedule.nightly_hour"], settings["context.schedule.mining_weekday"]
    stale_key = f"context.staleness.ran.{today.isoformat()}"
    due = mining_day(today, weekday)
    week_key = f"{MINING_KEY}{due.isoformat()}"
    jobs = []
    if now.hour >= hour:
        jobs.append(("staleness", stale_key, lambda: staleness_now(storage, today=today)))
        jobs.append(("mining", week_key, lambda: mining_pass(storage, models, due, today, settings["context.mining.support_weeks"],
                                                             settings["context.schedule.mining_live"])))
    for name, key, job in jobs:
        if not _claim(storage, key):
            continue
        try:
            done[name] = job()
        except Exception as error:
            # Recorded, and claimed again on a later pass (L.B6, L.B8); the other job still runs.
            log.exception("Context %s job failed; it runs again on a later pass", name)
            _fail(storage, key, error)
            done.setdefault("failed", []).append(name)
            continue
        _finish(storage, key, done[name])
    try:
        # Not claimed by period: a version approved at noon is queued on the next pass. The job's own key and the version's
        # record keep it to one benchmark at a time.
        if (benchmark := benchmark_now(storage, now)) is not None:
            done["benchmark"] = benchmark
    except Exception:
        log.exception("Scheduling the knowledge-base benchmark failed; the next pass tries again")
        done.setdefault("failed", []).append("benchmark")
    return done


def loop(storage, models, *, once=False, sleep_seconds=300):
    while True:
        try:
            done = tick(storage, models)
        except Exception:
            log.exception("Context scheduler pass failed; retrying")
            done = {"error": True}
        if once:
            return done
        time.sleep(sleep_seconds)



