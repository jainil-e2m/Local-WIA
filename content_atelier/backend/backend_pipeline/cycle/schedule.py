"""The weekly cycle on a schedule (plan 3.B11, Phase N7): the week's calls come in, the cycle starts and the week's review
document is made, every week, without a person.

The owner set the first run for Sunday 1 November 2026 at 04:00 America/Chicago, and every Sunday at that time after it
(25 October 2026; the plan's Saturday slot moved). The settings say when (`cycle.timezone`, `cycle.weekday`, `cycle.hour`,
the same ones that close the intake's weekly bucket), from which day (`cycle.schedule.first_day`), whether it runs at all
(`cycle.schedule.enabled`) and whose approval it starts under (`cycle.schedule.actor`, an approver and intake administrator:
the run records that it was started by the schedule on their standing approval).

At the scheduled time, for the window of the seven days before it, the scheduler:

1. **Brings in the window's calls.** Every Fathom recording of the window that is not yet a document is fetched, imported,
   normalised by the rules and its chunks queued for embedding (6.B18's backfill, which is idempotent: a recording already
   stored is neither fetched nor written again, and a second recording of one meeting is not imported). This catches up
   whatever the hourly collector missed, and on the first run it brings the week before activation, which the collector
   never fetches.
2. **Activates the hourly collector** (6.B1) the first time, so from then on a new call arrives within the hour and exactly
   one collector runs (7.B6's connector step).
3. **Starts the cycle** over the window, exactly as an approver's preview and start would (`window.preview`, `window.start`):
   the scenes of new calls are extracted by the cycle, the strategist writes the week's cards, Gate 1 waits for WIA. A window
   with no included call starts nothing and says so.

Then, once the cycle has finished, `review_documents` makes the week's review document (Markdown and Word) and keeps it with
the run, for the app's download; nothing is emailed (the owner, 25 October 2026). A run that fails three times is a missed
schedule and an alert (alerts.py); every step is recorded on the scheduler's claim for the week.
"""
from __future__ import annotations

import logging
import tempfile
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

log = logging.getLogger(__name__)

TASK = "weekly_cycle"
# The weekly run is tried up to eight times, the waits between growing by ten minutes (jobs/periodic.py): about four and a
# half hours from the first failure to the last attempt, so a passing outage on a Sunday morning does not lose the week.
ATTEMPTS = 8
REVIEW_TASK = "cycle_review_documents"
STARTED_FROM = "schedule"


def scheduled_end(now: datetime, schedule: dict) -> datetime:
    """The latest scheduled time at or before `now`: the end of the window the schedule reads."""
    zone = ZoneInfo(schedule["timezone"])
    local = now.astimezone(zone)
    day = local.date() - timedelta(days=(local.weekday() - schedule["weekday"]) % 7)
    end = datetime.combine(day, time(schedule["hour"]), zone)
    if end > local:
        end -= timedelta(days=7)
    return end


def settings(conn) -> dict:
    from ..settings_store import cycle_schedule, values
    v = values(["cycle.schedule.enabled", "cycle.schedule.first_day", "cycle.schedule.actor"], conn)
    return {**cycle_schedule(conn), "enabled": bool(v["cycle.schedule.enabled"]), "actor": v["cycle.schedule.actor"],
            "first_day": date.fromisoformat(v["cycle.schedule.first_day"]) if v["cycle.schedule.first_day"] else None}


def due(storage, now: datetime) -> str | None:
    """The scheduler's period for this week (the scheduled day, in the cycle's time zone), or None when not due."""
    from ..database import connect
    with connect(storage.database_url, vectors=False) as conn:
        s = settings(conn)
    if not s["enabled"] or not s["first_day"]:
        return None
    end = scheduled_end(now, s)
    if end.date() < s["first_day"]:
        return None
    return end.date().isoformat()


def next_run(conn, now: datetime | None = None) -> dict:
    """When the schedule runs next, for the app (the sidebar's "Next run" and the settings view)."""
    now = now or datetime.now(UTC)
    s = settings(conn)
    end = scheduled_end(now, s) + timedelta(days=7)
    if s["first_day"]:
        while end.date() < s["first_day"]:
            end += timedelta(days=7)
    return {"enabled": s["enabled"], "at": end.isoformat() if s["enabled"] else None, "timezone": s["timezone"],
            "window": {"start": (end - timedelta(days=7)).isoformat(), "end": end.isoformat()} if s["enabled"] else None}


def collect_window(repo, models, start: datetime, end: datetime, timezone: str, actor: str) -> dict:
    """Step 1: the window's Fathom recordings not yet documents, imported (fathom_backfill.run, embedding queued live)."""
    from ..documents import fathom_backfill
    from ..intake.config import IntakeSettings, fathom_api_key
    from ..intake.fathom import FathomClient
    key = fathom_api_key()
    if not key:
        return {"skipped": "no Fathom key in this process (ATELIER_FATHOM_API_KEY)"}
    client = FathomClient(IntakeSettings(fathom_key=key))
    try:
        with tempfile.TemporaryDirectory(prefix="atelier-fathom-") as folder:
            embed = "live" if repo.settings.encoding_enabled else None
            result = fathom_backfill.run(repo, models, client, start=start, end=end, out=Path(folder), timezone=timezone,
                                         embed=embed, actor=actor)
    finally:
        client.close()
    return {k: result.get(k) for k in ("meetings_listed", "fetched", "failed", "by_state", "imported", "normalised")
            if k in result}


def activate_collector(actor: str, now: datetime) -> dict:
    """Step 2: the hourly collector, activated once (activation never rewinds an existing checkpoint)."""
    from ..intake.runtime import repository
    try:
        intake = repository()
    except Exception as error:  # no intake configuration in this process: the weekly step above still collects
        return {"skipped": f"intake is not configured here: {error}"[:300]}
    if not intake.intake.fathom_key:
        return {"skipped": "no Fathom key in this process"}
    row = intake.activate("fathom", actor, now=now)
    return {"activated_at": row["activated_at"].isoformat(), "checkpoint": row["checkpoint"].isoformat()}


def run(storage, models, now: datetime) -> dict:
    """The week's scheduled run (steps 1 to 3)."""
    from ..database import connect
    from ..repository import ContentRepository
    from . import window
    repo = ContentRepository(storage)
    with connect(storage.database_url, vectors=False) as conn:
        s = settings(conn)
    if not s["actor"]:
        raise ValueError("cycle.schedule.actor names no approver: the scheduled cycle cannot start")
    if not repo.settings.generation_enabled:
        raise ValueError("Paid generation is off in the scheduler (ATELIER_ALLOW_GENERATION): the cycle cannot start")
    end = scheduled_end(now, s).astimezone(UTC)
    start = end - timedelta(days=7)
    out = {"window": {"start": start.isoformat(), "end": end.isoformat()},
           "collected": collect_window(repo, models, start, end, s["timezone"], s["actor"]),
           "collector": activate_collector(s["actor"], now)}
    shown = window.preview(repo, models, start, end)
    if not shown["document_count"]:
        return {**out, "cycle": None, "note": "No included call fell in the window: no cycle this week"}
    started = window.start(repo, models, s["actor"], start, end, mode="live", expected_selection=shown["selection_hash"])
    with repo.connection() as conn:
        conn.execute("""UPDATE pipeline_runs SET input_refs=input_refs || jsonb_build_object('started_from',%s::text,
            'scheduled_for',%s::text),trigger_type='scheduled' WHERE run_id=%s""", (STARTED_FROM, end.isoformat(), started["run_id"]))
    return {**out, "cycle": {k: started.get(k) for k in ("run_id", "week_id", "status", "documents", "late_arrivals")},
            "estimate_usd": (started.get("estimate") or {}).get("total_usd")}


def review_documents(storage, now: datetime | None = None) -> dict:
    """The week's review document for every scheduled cycle that has finished and has none yet: Markdown and Word, kept in
    the artifact store and named on the run, for the app's download."""
    from ..artifacts import store_for
    from ..briefs import review_docx, review_document
    from ..repository import ContentRepository
    repo = ContentRepository(storage)
    made_at = now or datetime.now(UTC)
    with repo.connection() as conn:
        runs = conn.execute("""SELECT run_id,week_id FROM pipeline_runs WHERE run_scope='weekly_angles'
            AND input_refs->>'started_from'=%s AND status IN ('waiting_for_review','completed','partially_completed')
            AND NOT (input_refs ? 'review_document')""", (STARTED_FROM,)).fetchall()
    store, made = store_for(storage), []
    for run in runs:
        text = review_document.render_week(repo, run["week_id"], exported=made_at)
        keys = {"markdown": f"weeks/{run['week_id']}/review-{run['run_id']}.md",
                "docx": f"weeks/{run['week_id']}/review-{run['run_id']}.docx"}
        store.backend.write(keys["markdown"], text.encode("utf-8"))
        store.backend.write(keys["docx"], review_docx.render(text, title=f"Content Atelier Review, {run['week_id']}", created=made_at))
        with repo.connection() as conn:
            conn.execute("""UPDATE pipeline_runs SET input_refs=input_refs || jsonb_build_object('review_document',%s::jsonb)
                WHERE run_id=%s""", (__import__("json").dumps({**keys, "at": made_at.isoformat()}), run["run_id"]))
        made.append(run["run_id"])
    return {"made": made}
