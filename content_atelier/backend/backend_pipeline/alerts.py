"""Failure alerts (plan 6.B4, Phase N6): what went wrong, said once, where the team already works.

A failed job, a stuck queue, an intake connection that stopped collecting, a call refused by a weekly budget, a scheduled
run that did not happen, and a backup or restore check that did not happen each become one alert. The app is the channel
(the Sources screen and the bell): the owner ruled out alert emails and Slack for now (25 October 2026), so every alert
records `{"email": "off"}` in `notified` and nothing is sent.

An alert is one row per open condition, keyed by (kind, subject): the scheduler's scan (every pass) opens it once, counts
each pass that still sees it, and resolves it as `cleared` when the condition is gone, so a job that keeps failing is one
alert, not one per pass. A person may dismiss an open alert; a dismissed condition that persists is not reopened, and the
same condition opens a new alert only after it has cleared once.

Conditions come from rows the system already keeps (jobs, intake connections and requests, the scheduler's period claims,
the backup records); nothing here calls a model or an outside service. A failed job counts only from `alerts.watch_since`,
which the first scan sets, so a deployment does not raise an alert for every failure in its history. A silent scheduler
cannot scan for itself, so `listing` adds that one live, from the heartbeat (jobs/health.py).

    GET  /storage/alerts                      open alerts (and, with ?resolved=true, the recent resolved ones)
    POST /storage/alerts/{alert_id}/dismiss   a person acknowledges one
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from psycopg.types.json import Jsonb

from .reference import _id

KINDS = ("job_failed", "job_stuck", "intake_stopped", "budget_refused", "schedule_missed", "backup_missing",
         "restore_check_failed", "accepted_share_low", "scheduler_silent")
WATCH_SINCE_KEY = "alerts.watch_since"
# A ready job (queued, its run active, its dependencies done) older than this on its queue, while nothing on that queue has
# started or finished for as long, means the queue is stuck. Bulk work (re-embedding, extraction) legitimately queues longer.
STUCK_AFTER = {"interactive": timedelta(minutes=15), "default": timedelta(minutes=15), "intake": timedelta(minutes=30),
               "bulk": timedelta(hours=1)}
LEASE_GRACE = timedelta(minutes=5)
# The collector asks for a collection every hour (intake/runtime.py); three hours without one is a stop.
INTAKE_SILENT = timedelta(hours=3)
# The db-backup cron runs nightly; a day and a half without a dump means a night was missed. The restore check is monthly.
DUMP_MISSING = timedelta(hours=36)
RESTORE_CHECK_DUE = timedelta(days=35)
BACKUP_KEY = "backup.last_dump"
RESTORE_KEY = "backup.last_restore_check"
STAGE_WORDS = {"document_normalise": "document normalisation", "moment_extraction": "scene extraction",
               "transcript_chunk_embedding": "transcript embedding", "intake_fathom": "Fathom collection",
               "angle_generation": "card generation", "brief_generation": "brief", "pack_finish": "content pack"}


@dataclass(frozen=True)
class Condition:
    kind: str
    subject: str
    severity: str
    message: str
    details: dict = field(default_factory=dict)


def _words(stage: str | None) -> str:
    return STAGE_WORDS.get(stage or "", (stage or "a").replace("_", " "))


def watch_since(conn, now: datetime) -> datetime:
    """When failed jobs started to count: set by the first scan, never moved."""
    row = conn.execute("SELECT value FROM settings WHERE key=%s", (WATCH_SINCE_KEY,)).fetchone()
    if row and isinstance(row["value"], dict) and row["value"].get("at"):
        return datetime.fromisoformat(row["value"]["at"])
    conn.execute("""INSERT INTO settings(key,value,updated_by) VALUES (%s,%s,'alerts') ON CONFLICT (key) DO NOTHING""",
                 (WATCH_SINCE_KEY, json.dumps({"at": now.isoformat()})))
    return now


def failed_jobs(conn, since: datetime) -> list[Condition]:
    rows = conn.execute("""SELECT job_id,stage,queue,run_id,week_id,transcript_id,brief_id,pack_id,error_summary,attempt_count,
        updated_at FROM pipeline_jobs WHERE status='failed' AND updated_at>=%s ORDER BY updated_at""", (since,)).fetchall()
    return [Condition("job_failed", r["job_id"], "error",
                      f"A {_words(r['stage'])} job failed: {(r['error_summary'] or 'no reason was recorded').strip()[:300]}",
                      {"stage": r["stage"], "queue": r["queue"], "run_id": r["run_id"], "week_id": r["week_id"],
                       "transcript_id": r["transcript_id"], "brief_id": r["brief_id"], "pack_id": r["pack_id"],
                       "attempts": r["attempt_count"], "failed_at": r["updated_at"].isoformat()}) for r in rows]


def stuck_queues(conn, now: datetime) -> list[Condition]:
    """A queue whose oldest ready job waits past its threshold while nothing on it moves, or a running job whose lease ran
    out unnoticed (the reconcile pass settles those; one that stays is stuck)."""
    rows = conn.execute("""SELECT j.queue,
          min(j.created_at) FILTER (WHERE j.status='queued' AND (r.run_scope='source_intake' OR r.status IN ('queued','running'))
            AND NOT EXISTS (SELECT 1 FROM jsonb_array_elements_text(COALESCE(j.progress_details->'dependencies','[]')) dep
                            JOIN pipeline_jobs d ON d.job_id=dep.value WHERE d.status<>'completed')) AS oldest_ready,
          count(*) FILTER (WHERE j.status='running' AND j.lease_expires_at < %s) AS lost,
          count(*) FILTER (WHERE j.status='running' AND j.lease_expires_at >= %s) AS working,
          max(GREATEST(j.started_at,j.finished_at)) AS last_moved
        FROM pipeline_jobs j JOIN pipeline_runs r USING(run_id) WHERE j.executor IN ('rq','postgres') GROUP BY j.queue""",
                        (now - LEASE_GRACE, now)).fetchall()
    out = []
    for r in rows:
        limit = STUCK_AFTER.get(r["queue"], timedelta(minutes=30))
        waited = now - r["oldest_ready"] if r["oldest_ready"] else None
        # A long job holding a live lease (a brief's claim check can take a quarter of an hour) keeps its queue moving.
        idle = not r["working"] and (r["last_moved"] is None or now - r["last_moved"] > limit)
        if r["lost"]:
            out.append(Condition("job_stuck", r["queue"], "error",
                                 f"{r['lost']} running job(s) on the {r['queue']} queue lost their worker and were not picked up again",
                                 {"queue": r["queue"], "lost": r["lost"]}))
        elif waited is not None and waited > limit and idle:
            out.append(Condition("job_stuck", r["queue"], "error",
                                 f"Work on the {r['queue']} queue has waited {int(waited.total_seconds() // 60)} minutes and "
                                 "nothing on that queue is moving: check that its worker is running",
                                 {"queue": r["queue"], "waited_minutes": int(waited.total_seconds() // 60)}))
    return out


def intake_stopped(conn, now: datetime) -> list[Condition]:
    """An activated connection whose last collection failed, or whose discovery has not moved for INTAKE_SILENT. The collector
    moves the checkpoint to the end of every window it has listed (intake/fathom.py), even while a transcript is still being
    published, so a still checkpoint means collection itself stopped."""
    out = []
    for c in conn.execute("SELECT connection_id,provider,activated_at,checkpoint,health,error_summary FROM intake_connections "
                          "WHERE activated_at IS NOT NULL AND activated_at<=%s", (now,)).fetchall():
        since = max(c["checkpoint"] or c["activated_at"], c["activated_at"])
        if c["health"] == "error":
            out.append(Condition("intake_stopped", c["connection_id"], "error",
                                 f"The {c['provider'].title()} connection stopped: {(c['error_summary'] or 'its last collection failed')[:300]}",
                                 {"provider": c["provider"], "health": c["health"]}))
        elif now - since > INTAKE_SILENT:
            hours = int((now - since).total_seconds() // 3600)
            out.append(Condition("intake_stopped", c["connection_id"], "error",
                                 f"No {c['provider'].title()} collection has run for {hours} hours: new calls are not arriving",
                                 {"provider": c["provider"], "checkpoint": since.isoformat()}))
    return out


def budget_refusals(conn) -> list[Condition]:
    rows = conn.execute("""SELECT progress_details->>'budget_purpose' AS purpose,count(*) n,min(updated_at) since,
        (array_agg(progress_details->>'budget_reason' ORDER BY updated_at DESC))[1] AS reason
        FROM pipeline_jobs WHERE status='waiting' AND progress_details->>'waiting_for'='budget' GROUP BY 1""").fetchall()
    return [Condition("budget_refused", r["purpose"] or "unknown", "warning",
                      f"{r['n']} job(s) are waiting for this week's {(r['purpose'] or 'unknown').replace('_', ' ')} budget"
                      + (f": {r['reason']}" if r["reason"] else "") + ". They start by themselves when the budget renews or is raised",
                      {"purpose": r["purpose"], "jobs": r["n"], "since": r["since"].isoformat()}) for r in rows]


def missed_schedules(conn, now: datetime) -> list[Condition]:
    """A scheduled task (jobs/periodic.py) whose period ran out of attempts, recorded by its claim row, until a later period
    of the same task has run (the hourly upkeep's next hour picks up what a missed hour left, so the alert clears itself)."""
    rows = conn.execute("""SELECT key,value,updated_at FROM settings WHERE key LIKE 'schedule.%%'
        AND value->>'state'='failed' AND COALESCE((value->>'attempts')::int,0)>=3""").fetchall()
    done = {}
    for r in conn.execute("""SELECT key,updated_at FROM settings WHERE key LIKE 'schedule.%%' AND value->>'state'='done'""").fetchall():
        task = r["key"].split(".")[1] if r["key"].count(".") >= 2 else r["key"]
        done[task] = max(done.get(task, r["updated_at"]), r["updated_at"])
    out = []
    for r in rows:
        task = r["key"].split(".")[1] if r["key"].count(".") >= 2 else r["key"]
        if task in done and done[task] > r["updated_at"]:
            continue
        from .cycle.schedule import ATTEMPTS, TASK
        attempts, limit = int(r["value"].get("attempts") or 0), ATTEMPTS if task == TASK else 3
        said = ("did not run: " if attempts >= limit else
                f"failed {attempts} times and is tried again by itself (up to {limit} times): ")
        out.append(Condition("schedule_missed", r["key"], "error",
                             f"The scheduled {task.replace('_', ' ')} {said}{(r['value'].get('error') or 'it failed')[:300]}",
                             {"task": task, "key": r["key"], "attempts": attempts, "limit": limit}))
    return out


def backups(conn, now: datetime) -> list[Condition]:
    """The nightly dump and the monthly restore check, from the records the db-backup service writes (backup.py)."""
    out = []
    rows = {r["key"]: r for r in conn.execute("SELECT key,value,updated_at FROM settings WHERE key IN (%s,%s)",
                                              (BACKUP_KEY, RESTORE_KEY)).fetchall()}
    dump = rows.get(BACKUP_KEY)
    if dump is not None and now - dump["updated_at"] > DUMP_MISSING:
        out.append(Condition("backup_missing", "nightly_dump", "error",
                             f"No database backup since {dump['updated_at']:%d %B %Y %H:%M} UTC: check the db-backup service",
                             {"last_dump": dump["updated_at"].isoformat()}))
    check = rows.get(RESTORE_KEY)
    if check is not None and (check["value"] or {}).get("ok") is False:
        out.append(Condition("restore_check_failed", "monthly_restore", "error",
                             "The monthly restore check failed: " + ((check["value"] or {}).get("problem") or "the counts differ")[:300],
                             {"checked_at": check["updated_at"].isoformat()}))
    elif dump is not None and (check is None or now - check["updated_at"] > RESTORE_CHECK_DUE):
        out.append(Condition("restore_check_failed", "monthly_restore", "warning",
                             "No restore check in the last month: the next nightly backup runs one",
                             {"last_check": check["updated_at"].isoformat() if check else None}))
    return out


def conditions(conn, now: datetime) -> list[Condition]:
    from .week_measures import accepted_share_condition
    since = watch_since(conn, now)
    found = (failed_jobs(conn, since) + stuck_queues(conn, now) + intake_stopped(conn, now) + budget_refusals(conn)
             + missed_schedules(conn, now) + backups(conn, now))
    share = accepted_share_condition(conn)
    if share:
        found.append(Condition("accepted_share_low", share["subject"], "warning", share["message"], share["details"]))
    return found


def scan(conn, now: datetime | None = None) -> dict:
    """One pass: open what is new, count what persists, clear what has gone. Returns the counts, for the scheduler's log."""
    now = now or datetime.now(UTC)
    present = {(c.kind, c.subject): c for c in conditions(conn, now)}
    opened = counted = cleared = 0
    open_rows = {(r["kind"], r["subject"]): r for r in conn.execute(
        "SELECT alert_id,kind,subject FROM alerts WHERE resolved_at IS NULL FOR UPDATE").fetchall()}
    for key, row in open_rows.items():
        if key in present:
            c = present[key]
            conn.execute("""UPDATE alerts SET occurrences=occurrences+1,last_seen_at=%s,message=%s,details=%s,severity=%s
                WHERE alert_id=%s""", (now, c.message, Jsonb(c.details), c.severity, row["alert_id"]))
            counted += 1
        else:
            conn.execute("UPDATE alerts SET resolved_at=%s,resolution='cleared',resolved_by='alerts scan' WHERE alert_id=%s",
                         (now, row["alert_id"]))
            cleared += 1
    # A dismissed condition stays quiet while it persists; once it has cleared, the same condition may open a new alert.
    dismissed = {(r["kind"], r["subject"]) for r in conn.execute(
        "SELECT kind,subject FROM alerts WHERE resolution='dismissed' AND NOT (details ? 'cleared_at')").fetchall()}
    for key in dismissed - present.keys():
        conn.execute("""UPDATE alerts SET details=details || %s WHERE kind=%s AND subject=%s AND resolution='dismissed'
            AND NOT (details ? 'cleared_at')""", (Jsonb({"cleared_at": now.isoformat()}), *key))
    for key, c in present.items():
        if key in open_rows or key in dismissed:
            continue
        conn.execute("""INSERT INTO alerts(alert_id,kind,subject,severity,message,details,first_seen_at,last_seen_at,notified)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                     (_id("alert_", f"{c.kind}|{c.subject}|{now.isoformat()}"), c.kind, c.subject, c.severity, c.message,
                      Jsonb(c.details), now, now, Jsonb({"email": "off", "app": now.isoformat()})))
        opened += 1
    return {"opened": opened, "still_open": counted, "cleared": cleared}


def listing(conn, *, resolved: bool = False, limit: int = 100, now: datetime | None = None) -> dict:
    now = now or datetime.now(UTC)
    from .jobs.health import SCHEDULER_SILENT
    from .jobs.scheduler import HEARTBEAT_KEY
    rows = conn.execute("""SELECT alert_id,kind,subject,severity,message,details,occurrences,first_seen_at,last_seen_at,
        resolved_at,resolved_by,resolution FROM alerts WHERE resolved_at IS NULL OR (%s AND resolved_at > %s)
        ORDER BY resolved_at IS NOT NULL, severity='warning', last_seen_at DESC LIMIT %s""",
                        (resolved, now - timedelta(days=14), limit)).fetchall()
    live = []
    beat = conn.execute("SELECT updated_at FROM settings WHERE key=%s", (HEARTBEAT_KEY,)).fetchone()
    if beat is None or now - beat["updated_at"] > SCHEDULER_SILENT * 2:
        live.append({"alert_id": None, "kind": "scheduler_silent", "subject": "scheduler", "severity": "error",
                     "message": "The scheduler has not completed a pass in the last 10 minutes: no scheduled work, retry or "
                                "alert scan is running", "details": {"last_pass": beat["updated_at"].isoformat() if beat else None},
                     "occurrences": 1, "first_seen_at": beat["updated_at"] if beat else None, "last_seen_at": now,
                     "resolved_at": None, "resolved_by": None, "resolution": None})
    alerts = live + [dict(r) for r in rows]
    return {"open": sum(a["resolved_at"] is None for a in alerts), "alerts": alerts, "email": "off"}


def dismiss(conn, alert_id: str, actor: str) -> dict:
    row = conn.execute("""UPDATE alerts SET resolved_at=now(),resolution='dismissed',resolved_by=%s
        WHERE alert_id=%s AND resolved_at IS NULL RETURNING alert_id,kind,subject""", (actor, alert_id)).fetchone()
    if row is None:
        raise LookupError("No open alert with that id")
    return dict(row)


def install(routes, settings, reader, decider, action):
    from fastapi import Depends, Query

    from .api_models import AlertDismissed, AlertList, returns
    from .database import connect

    @routes.get("/alerts", responses=returns(AlertList))
    def alert_list(resolved: bool = Query(default=False), subject: str = Depends(reader)):
        def read():
            with connect(settings.database_url, vectors=False) as conn:
                return listing(conn, resolved=resolved)
        return action(read)

    @routes.post("/alerts/{alert_id}/dismiss", responses=returns(AlertDismissed))
    def alert_dismiss(alert_id: str, subject: str = Depends(decider)):
        def write():
            from .gates.roles import access_for
            if not access_for(settings, subject).can("edit"):  # a viewer reads the alerts; an editor or approver dismisses
                raise PermissionError("Dismissing an alert needs an editor or approver")
            with connect(settings.database_url, vectors=False) as conn:
                result = dismiss(conn, alert_id, subject)
                conn.commit()
                return result
        return action(write)
