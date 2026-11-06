"""Read-only incident inspection; secrets stay in memory and SQL is enforced read-only."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import traceback
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import urlsplit

import httpx
import psycopg
from psycopg.rows import dict_row

PROJECT = "3409333b-1844-456c-93f9-f572ba92eb92"
ENVIRONMENT = "28239d73-fe52-4d23-bf80-94a8064c5eb5"
CLI = Path(os.environ.get("APPDATA", "")) / "npm/node_modules/@railway/cli/bin/railway.exe"
OUT = Path(__file__).resolve().parent
START = datetime(2026, 10, 25, 10, tzinfo=UTC)
END = datetime(2026, 11, 1, 10, tzinfo=UTC)


def variables(service):
    result = subprocess.run(
        [str(CLI), "variable", "list", "--project", PROJECT, "--environment", ENVIRONMENT,
         "--service", service, "--json"], capture_output=True, text=True, timeout=45,
    )
    if result.returncode:
        raise RuntimeError(f"Could not read configuration for {service}; output withheld to protect secrets")
    return json.loads(result.stdout)


def fathom_only():
    """List provider metadata only; do not download transcripts or import anything."""
    config = variables("scheduler")
    key = config.get("ATELIER_FATHOM_API_KEY") or config.get("FATHOM_API_KEY")
    if not key:
        raise RuntimeError("Fathom key absent")
    now = datetime.now(UTC)
    report = {"inspected_at": now.isoformat(), "listing_complete": False,
              "missed_window": {"start": START.isoformat(), "end": END.isoformat()},
              "note": "Recording metadata only. No database reconciliation or transcript comparison performed."}
    cursor, seen, found = None, set(), {}
    with httpx.Client(base_url="https://api.fathom.ai/external/v1/", headers={"X-Api-Key": key},
                      timeout=45, follow_redirects=False) as client:
        for _ in range(100):
            params = {"created_after": START.isoformat(), "created_before": max(END + timedelta(days=2), now).isoformat()}
            if cursor:
                params["cursor"] = cursor
            response = client.get("meetings", params=params)
            if response.status_code != 200:
                report["http_status"] = response.status_code
                break
            body = response.json()
            for item in body.get("items", []):
                timestamp = next((item.get(k) for k in ("recording_start_time", "scheduled_start_time", "created_at") if item.get(k)), None)
                when = datetime.fromisoformat(timestamp) if timestamp else None
                if when is not None and START <= when <= now:
                    found[item["recording_id"]] = {"recording_id": item["recording_id"],
                        "title": item.get("recording_name") or item.get("title"), "occurred_at": when.isoformat(),
                        "window": "missed_week" if when < END else "after_missed_run"}
            cursor = body.get("next_cursor")
            if not cursor:
                report["listing_complete"] = True
                break
            if cursor in seen:
                raise RuntimeError("Repeated pagination cursor")
            seen.add(cursor)
    report["recordings"] = sorted(found.values(), key=lambda x: x["occurred_at"])
    report["counts"] = {window: sum(r["window"] == window for r in found.values())
                        for window in ("missed_week", "after_missed_run")}
    path = OUT / "fathom-metadata-evidence.json"
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


def collector_detail():
    """Additional SQL-only inspection of the collector; no provider requests."""
    report = {"inspected_at": datetime.now(UTC).isoformat()}
    with psycopg.connect(os.environ["ATELIER_DATABASE_URL"], row_factory=dict_row, connect_timeout=15,
                         options="-c default_transaction_read_only=on -c statement_timeout=20000") as conn:
        report["read_only"] = conn.execute("SHOW transaction_read_only").fetchone()
        report["source_states"] = conn.execute("""SELECT status,count(*) AS count,
            count(*) FILTER (WHERE latest_revision_id IS NULL) AS without_revision
            FROM intake_sources WHERE connection_id='fathom' GROUP BY status""").fetchall()
        report["pending_sources"] = conn.execute("""SELECT source_id,upstream_id,title,status,occurred_at,received_at,
            latest_revision_id,metadata->>'last_checked_at' AS last_checked_at FROM intake_sources
            WHERE connection_id='fathom' AND (status='pending_transcript' OR latest_revision_id IS NULL)
            ORDER BY occurred_at""").fetchall()
        report["job_states"] = conn.execute("""SELECT status,count(*) AS count,min(attempt_count) AS min_attempts,
            max(attempt_count) AS max_attempts,min(created_at) AS oldest_created,max(updated_at) AS last_updated
            FROM pipeline_jobs WHERE stage='intake_fathom' GROUP BY status""").fetchall()
        report["waiting_job_examples"] = conn.execute("""SELECT j.job_id,j.status,j.attempt_count,j.error_summary,
            j.created_at,j.updated_at,j.progress_details->>'retry_at' AS retry_at,
            r.input_refs->>'request_id' AS request_id FROM pipeline_jobs j JOIN pipeline_runs r USING(run_id)
            WHERE j.stage='intake_fathom' AND j.status IN ('waiting','failed','running')
            ORDER BY j.updated_at DESC LIMIT 8""").fetchall()
        report["pending_request_range"] = conn.execute("""SELECT status,count(*) AS count,
            min(window_start) AS oldest_start,max(window_end) AS latest_end
            FROM intake_requests GROUP BY status""").fetchall()
        report["missing_recording_ids_present_anywhere"] = conn.execute("""SELECT transcript_id,source_type,
            upstream_id,title,occurred_at,canonical_document_id FROM transcripts
            WHERE upstream_id=ANY(%s) ORDER BY upstream_id""", ([f"fathom:{rid}" for rid in
                (196273263,196306102,196305821,196331219,196389453)],)).fetchall()
        conn.rollback()
    print(json.dumps(report, indent=2, default=str))


def main():
    inside_container = "--inside-container" in sys.argv
    db_vars = os.environ if inside_container else variables("postgres")
    scheduler_vars = os.environ if inside_container else variables("scheduler")
    report = {"inspected_at": datetime.now(UTC).isoformat(), "project": PROJECT,
              "window": {"start": START.isoformat(), "end": END.isoformat()}}
    if inside_container:
        from backend_pipeline.config import BACKEND_ROOT
        from backend_pipeline.documents.fathom_backfill import outside_repository
        report["container_backend_root"] = str(BACKEND_ROOT)
        report["container_inferred_repository"] = str(BACKEND_ROOT.parent.resolve())
        try:
            outside_repository(Path("/tmp/atelier-fathom-diagnostic"))
            report["container_guard_result"] = "allowed"
        except ValueError as error:
            report["container_guard_result"] = str(error)
    url = db_vars.get("ATELIER_DATABASE_URL") if inside_container else db_vars.get("DATABASE_PUBLIC_URL")
    if not url or (not inside_container and (urlsplit(url).hostname or "").endswith(".railway.internal")):
        report["database_access"] = "No existing public database URL; no networking changes attempted"
        print(json.dumps(report, indent=2))
        return
    with psycopg.connect(url, row_factory=dict_row, connect_timeout=15,
                         options="-c default_transaction_read_only=on -c statement_timeout=20000") as conn:
        def query(sql, args=()):
            return conn.execute(sql, args or None).fetchall()

        report["database"] = query("SELECT current_database() AS name, current_setting('transaction_read_only') AS read_only, now() AS at")[0]
        report["settings"] = query("""SELECT key,value,updated_at FROM settings WHERE key IN
            ('cycle.timezone','cycle.weekday','cycle.hour','cycle.schedule.enabled','cycle.schedule.first_day',
             'cycle.schedule.actor','jobs.scheduler.heartbeat','schedule.weekly_cycle.2026-11-01') ORDER BY key""")
        report["weekly_schedule_history"] = query("SELECT key,value,updated_at FROM settings WHERE key LIKE 'schedule.weekly_cycle.%' ORDER BY key")
        report["alerts"] = query("""SELECT alert_id,kind,subject,message,occurrences,first_seen_at,last_seen_at,resolved_at,resolution
            FROM alerts WHERE kind='schedule_missed' OR resolved_at IS NULL ORDER BY first_seen_at""")
        report["connections"] = query("SELECT connection_id,provider,activated_at,checkpoint,health,error_summary,updated_at FROM intake_connections ORDER BY connection_id")
        report["intake_requests"] = query("SELECT connection_id,status,count(*) AS count,min(window_start) AS first_start,max(window_end) AS last_end FROM intake_requests GROUP BY 1,2")
        report["intake_buckets"] = query("SELECT bucket_id,starts_at,cutoff,status,completed_at FROM intake_buckets ORDER BY starts_at DESC LIMIT 5")
        report["recent_weekly_runs"] = query("""SELECT run_id,week_id,status,trigger_type,created_at,finished_at,
            input_refs->'window' AS window,input_refs->>'started_from' AS started_from,
            input_refs->>'scheduled_for' AS scheduled_for, input_refs->>'selected_by' AS selected_by
            FROM pipeline_runs WHERE run_scope='weekly_angles' ORDER BY created_at DESC LIMIT 12""")
        report["document_history"] = query("""SELECT source_type,count(*) AS count,max(occurred_at) AS latest_occurrence,
            max(ingested_at) AS latest_ingested FROM transcripts GROUP BY source_type""")
        report["documents_in_missed_window"] = query("""SELECT transcript_id,source_type,upstream_id,title,occurred_at,ingested_at,
            included,call_type,normalised_at,canonical_document_id,extraction_status FROM transcripts
            WHERE occurred_at >= %s AND occurred_at < %s ORDER BY occurred_at""", (START, END))
        report["recent_imports"] = query("""SELECT source_type,count(*) AS count,min(ingested_at) AS first_ingested,max(ingested_at) AS last_ingested
            FROM transcripts WHERE ingested_at >= %s GROUP BY source_type""", (START,))
        report["new_outputs_since_scheduled_run"] = {}
        for table in ("content_angles", "content_briefs", "content_packs"):
            report["new_outputs_since_scheduled_run"][table] = query(
                f"SELECT count(*) AS count,max(created_at) AS latest FROM {table} WHERE created_at >= %s", (END,))[0]
        report["model_activity_since_scheduled_run"] = query("""SELECT stage,status,count(*) AS calls,
            sum(cost_usd) AS usd FROM llm_runs WHERE created_at >= %s GROUP BY stage,status ORDER BY stage,status""", (END,))
        known = query("SELECT transcript_id,source_type,upstream_id,occurred_at,canonical_document_id FROM transcripts")
        key = scheduler_vars.get("ATELIER_FATHOM_API_KEY") or scheduler_vars.get("FATHOM_API_KEY")
        if key:
            fetched = {}
            cursor = None
            seen = set()
            with httpx.Client(base_url="https://api.fathom.ai/external/v1/",
                              headers={"X-Api-Key": key}, timeout=45, follow_redirects=False) as client:
                for _ in range(100):
                    params = {"created_after": START.isoformat(), "created_before": (END + timedelta(days=2)).isoformat()}
                    if cursor:
                        params["cursor"] = cursor
                    response = client.get("meetings", params=params)
                    if response.status_code != 200:
                        report["fathom_error"] = {"status": response.status_code}
                        break
                    body = response.json()
                    for item in body.get("items", []):
                        timestamp = next((item.get(k) for k in ("recording_start_time", "scheduled_start_time", "created_at") if item.get(k)), None)
                        when = datetime.fromisoformat(timestamp) if timestamp else None
                        if when is not None and START <= when < END:
                            rid = item["recording_id"]
                            exact = [d["transcript_id"] for d in known if d["source_type"] == "fathom" and d["upstream_id"] == f"fathom:{rid}"]
                            nearby = [d["transcript_id"] for d in known if d["canonical_document_id"] is None
                                      and d["occurred_at"] is not None and abs(d["occurred_at"]-when) <= timedelta(minutes=10)]
                            fetched[rid] = {"recording_id": rid, "title": item.get("recording_name") or item.get("title"),
                                            "occurred_at": when.isoformat(), "already_imported": exact,
                                            "nearby_documents_not_verified_duplicates": nearby}
                    cursor = body.get("next_cursor")
                    if not cursor:
                        report["fathom_listing_complete"] = True
                        break
                    if cursor in seen:
                        raise RuntimeError("Repeated Fathom pagination cursor")
                    seen.add(cursor)
            report["fathom_recordings_in_missed_window"] = sorted(fetched.values(), key=lambda x: x["occurred_at"])
        else:
            report["fathom_error"] = "No Fathom key configured in scheduler"
        conn.rollback()
    if not inside_container:
        path = OUT / "production-readonly-evidence.json"
        path.write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    try:
        if "--collector-detail-only" in sys.argv:
            collector_detail()
        elif "--fathom-list" in sys.argv:
            fathom_only()
        else:
            main()
    except Exception as exc:
        print(json.dumps({"inspection_failed": type(exc).__name__, "sqlstate": getattr(exc, "sqlstate", None),
                          "location": [{"file": Path(frame.filename).name, "line": frame.lineno, "function": frame.name}
                                       for frame in traceback.extract_tb(exc.__traceback__)[-4:]],
                          "reason": "Message withheld to avoid exposing configuration credentials"}))
        raise SystemExit(1)
