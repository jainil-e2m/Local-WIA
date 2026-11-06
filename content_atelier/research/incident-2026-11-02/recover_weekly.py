"""Inspect, or conditionally re-arm only the explicitly authorized November 1 schedule."""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

PROJECT = "3409333b-1844-456c-93f9-f572ba92eb92"
ENVIRONMENT = "28239d73-fe52-4d23-bf80-94a8064c5eb5"
COMMIT = "9b50c9d047a2d1005b19fbd80fea5f9e2476a32b"
KEY = "schedule.weekly_cycle.2026-11-01"
END = datetime(2026, 11, 1, 10, tzinfo=UTC)
START = END - timedelta(days=7)
ORIGINAL_ERROR = "ValueError: Write the Fathom folders outside the repository (R48), not under /"


def environment():
    from backend_pipeline.config import BACKEND_ROOT
    from backend_pipeline.documents.fathom_backfill import outside_repository
    info = {name: os.environ.get(name) for name in (
        "RAILWAY_PROJECT_ID", "RAILWAY_ENVIRONMENT_ID", "RAILWAY_SERVICE_NAME", "RAILWAY_GIT_COMMIT_SHA")}
    if info["RAILWAY_PROJECT_ID"] != PROJECT or info["RAILWAY_ENVIRONMENT_ID"] != ENVIRONMENT:
        raise RuntimeError("Unexpected deployment environment")
    if info["RAILWAY_SERVICE_NAME"] != "scheduler" or info["RAILWAY_GIT_COMMIT_SHA"] != COMMIT:
        raise RuntimeError("Expected the approved scheduler commit")
    outside_repository(Path("/tmp/atelier-weekly-recovery-check"))
    try:
        outside_repository(BACKEND_ROOT / "backend_pipeline" / "calls")
    except ValueError:
        pass
    else:
        raise RuntimeError("Application directory protection failed")
    return info


def candidate_runs(conn):
    return conn.execute("""SELECT run_id,week_id,status,trigger_type,created_at,started_at,finished_at,
        current_message,error_summary,input_refs->'window' AS window,
        input_refs->>'scheduled_for' AS scheduled_for,input_refs ? 'review_document' AS has_review_document,
        jsonb_array_length(COALESCE(input_refs->'transcripts','[]'::jsonb)) AS documents
        FROM pipeline_runs WHERE run_scope='weekly_angles' AND (created_at >= %s
            OR input_refs->>'scheduled_for'=%s) ORDER BY created_at""", (END, END.isoformat())).fetchall()


def snapshot(conn):
    data = {"at": datetime.now(UTC).isoformat(), "deployment": environment()}
    data["schedule"] = conn.execute("SELECT key,value,updated_at,updated_by FROM settings WHERE key=%s", (KEY,)).fetchone()
    data["heartbeat"] = conn.execute("""SELECT updated_at,
        extract(epoch FROM clock_timestamp()-updated_at) AS age_seconds FROM settings
        WHERE key='jobs.scheduler.heartbeat'""").fetchone()
    data["runs"] = candidate_runs(conn)
    ids = [r["run_id"] for r in data["runs"]]
    data["jobs"] = conn.execute("""SELECT job_id,run_id,stage,status,current_message,error_summary,attempt_count,
        started_at,finished_at,updated_at,progress_details->>'waiting_for' AS waiting_for,
        progress_details->>'budget_reason' AS budget_reason FROM pipeline_jobs
        WHERE run_id=ANY(%s) ORDER BY created_at,job_id""", (ids,)).fetchall() if ids else []
    data["cards"] = conn.execute("""SELECT run_id,count(*) AS count FROM content_angles
        WHERE run_id=ANY(%s) GROUP BY run_id""", (ids,)).fetchall() if ids else []
    data["documents"] = conn.execute("""SELECT count(*) AS total,
        count(*) FILTER (WHERE included AND canonical_document_id IS NULL) AS included,
        count(*) FILTER (WHERE included AND canonical_document_id IS NULL AND extraction_status='completed') AS extracted
        FROM transcripts WHERE occurred_at >= %s AND occurred_at < %s""", (START, END)).fetchone()
    data["alerts"] = conn.execute("""SELECT kind,subject,message,resolved_at,resolution,occurrences
        FROM alerts WHERE subject=%s ORDER BY first_seen_at DESC""", (KEY,)).fetchall()
    return data


def main():
    if "--capacity-detail" in sys.argv:
        environment()
        from backend_pipeline.artifacts import store_for
        from backend_pipeline.storage_config import StorageSettings
        run_id = "run_113a8c5a0b384cfba61e6fc7b59367ee"
        with psycopg.connect(os.environ["ATELIER_DATABASE_URL"], row_factory=dict_row, connect_timeout=15,
                             options="-c default_transaction_read_only=on -c statement_timeout=15000") as conn:
            store = store_for(StorageSettings.from_env(conn=conn))
            report = {"at": datetime.now(UTC).isoformat(), "run_id": run_id}
            failed = store.read_json(f"experiments/sql/runs/{run_id}/angle_generation.failed.json")
            report["failed_artifact"] = {k: failed.get(k) for k in ("request_fingerprint", "model", "status", "error")}
            fingerprint = failed["request_fingerprint"]
            base = f"service_calls/{fingerprint}/attempts"
            report["preflight_reports"] = []
            for name in store.names(base):
                key = f"{base}/{name}/preflight.json"
                if store.exists(key):
                    report["preflight_reports"].append({"key": key, "report": store.read_json(key)})
            report["model_records"] = conn.execute("""SELECT stage,model,status,input_tokens,output_tokens,cost_usd,
                created_at,error FROM llm_runs WHERE details->>'run_id'=%s ORDER BY created_at""", (run_id,)).fetchall()
            report["scene_summary"] = conn.execute("""SELECT current_message,result_refs->>'unverified_count' AS unverified_count,
                jsonb_array_length(result_refs->'moment_ids') AS verified_scenes
                FROM pipeline_jobs WHERE run_id=%s AND stage='moment_extraction'""", (run_id,)).fetchone()
            conn.rollback()
        print(json.dumps(report, default=str))
        return
    if "--monitor" in sys.argv:
        for iteration in range(60):
            with psycopg.connect(os.environ["ATELIER_DATABASE_URL"], row_factory=dict_row, connect_timeout=15,
                                 options="-c default_transaction_read_only=on -c statement_timeout=15000") as conn:
                data = snapshot(conn)
                conn.rollback()
            claim = (data.get("schedule") or {}).get("value", {})
            runs = data["runs"]
            stop = None
            if claim.get("state") == "failed" and claim.get("attempts", 0) >= 3:
                stop = "schedule_failed"
            elif any(run["status"] in ("failed", "cancelled") for run in runs):
                stop = "pipeline_stopped"
            elif runs and all(run["status"] in ("waiting_for_review", "completed", "partially_completed")
                              and run["has_review_document"] for run in runs):
                stop = "ready_for_review_with_document"
            elif iteration == 59:
                stop = "monitor_window_ended"
            data["monitor_iteration"] = iteration
            data["stop_reason"] = stop
            print(json.dumps(data, default=str), flush=True)
            if stop:
                return
            time.sleep(30)
        return
    write = "--rearm" in sys.argv
    environment()
    options = "-c statement_timeout=15000 -c lock_timeout=5000"
    if not write:
        options += " -c default_transaction_read_only=on"
    with psycopg.connect(os.environ["ATELIER_DATABASE_URL"], row_factory=dict_row,
                         connect_timeout=15, options=options) as conn:
        if write:
            from backend_pipeline.cycle import schedule
            # Coordinate with the existing scheduler claim mechanism; do not start a second scheduler.
            conn.execute("SELECT pg_advisory_xact_lock(7312)")
            row = conn.execute("SELECT key,value,updated_at,updated_by FROM settings WHERE key=%s FOR UPDATE", (KEY,)).fetchone()
            previous = row["value"] if row else None
            if candidate_runs(conn):
                print(json.dumps({"changed": False, "reason": "A weekly run already exists; no retry counter changed"}))
                conn.rollback()
                return
            if previous != {"state": "failed", "attempts": 3, "error": ORIGINAL_ERROR}:
                print(json.dumps({"changed": False, "reason": "Claim no longer matches the original exhausted folder failure",
                                  "schedule": row}, default=str))
                conn.rollback()
                return
            now = datetime.now(UTC)
            config = schedule.settings(conn)
            if not config["enabled"] or schedule.scheduled_end(now, config).astimezone(UTC) != END:
                raise RuntimeError("The authorized scheduled period is no longer the current enabled period")
            heartbeat = conn.execute("""SELECT extract(epoch FROM clock_timestamp()-updated_at) AS age
                FROM settings WHERE key='jobs.scheduler.heartbeat'""").fetchone()
            if heartbeat is None or heartbeat["age"] > 300:
                raise RuntimeError("Scheduler heartbeat is not current")
            changed = conn.execute("""UPDATE settings SET value=jsonb_set(value,'{attempts}','0'::jsonb),
                updated_at=clock_timestamp(),updated_by='ai@weddingindustryads.com: authorized November 1 recovery'
                WHERE key=%s AND value=%s RETURNING key,value,updated_at,updated_by""", (KEY, Jsonb(previous))).fetchall()
            if len(changed) != 1:
                raise RuntimeError("Expected exactly one authorized schedule claim update")
            conn.commit()
            print(json.dumps({"changed": True, "before": row, "after": changed[0],
                              "note": "Existing scheduler will claim the period; no task was invoked directly"}, default=str))
        else:
            print(json.dumps(snapshot(conn), default=str))
            conn.rollback()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(json.dumps({"error_type": type(exc).__name__, "sqlstate": getattr(exc, "sqlstate", None),
                          "message": str(exc) if isinstance(exc, RuntimeError) else "Database detail withheld"}))
        raise SystemExit(1)
