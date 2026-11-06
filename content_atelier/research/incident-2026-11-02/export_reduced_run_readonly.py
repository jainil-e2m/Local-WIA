"""Remote stdin-only export. All DB statements are SELECT, within a read-only transaction."""
import base64
import gzip
import hashlib
import json
import os
from datetime import UTC, datetime

import psycopg
from psycopg.rows import dict_row
from backend_pipeline.artifacts import backend_for
from backend_pipeline.store import JsonStore
from backend_pipeline.token_budget import BYTE_BUDGET_MODELS

RUN = "run_113a8c5a0b384cfba61e6fc7b59367ee"
assert os.environ["RAILWAY_PROJECT_ID"] == "3409333b-1844-456c-93f9-f572ba92eb92"
assert os.environ["RAILWAY_ENVIRONMENT_ID"] == "28239d73-fe52-4d23-bf80-94a8064c5eb5"
assert os.environ["RAILWAY_GIT_COMMIT_SHA"] == "9b50c9d047a2d1005b19fbd80fea5f9e2476a32b"
store = JsonStore(backend_for("/unused-readonly-export"))
with psycopg.connect(os.environ["ATELIER_DATABASE_URL"], row_factory=dict_row, connect_timeout=15,
                     options="-c default_transaction_read_only=on -c statement_timeout=30000") as conn:
    conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
    out = {"fetched_at": datetime.now(UTC).isoformat(), "read_only": conn.execute("SHOW transaction_read_only").fetchone(),
           "deployment": {k: os.environ.get(k) for k in ("RAILWAY_PROJECT_ID", "RAILWAY_ENVIRONMENT_ID", "RAILWAY_SERVICE_NAME", "RAILWAY_GIT_COMMIT_SHA")}}
    out["run"] = conn.execute("SELECT * FROM pipeline_runs WHERE run_id=%s", (RUN,)).fetchone()
    assert out["run"] is not None
    out["jobs"] = conn.execute("SELECT * FROM pipeline_jobs WHERE run_id=%s ORDER BY created_at,job_id", (RUN,)).fetchall()
    out["events"] = conn.execute("SELECT * FROM pipeline_events WHERE run_id=%s ORDER BY created_at", (RUN,)).fetchall()
    extraction = next(j for j in out["jobs"] if j["stage"] == "moment_extraction")
    ids = extraction["result_refs"]["moment_ids"] + extraction["result_refs"].get("unverified_ids", [])
    out["moments"] = conn.execute("SELECT * FROM key_moments WHERE moment_id=ANY(%s) ORDER BY moment_id", (ids,)).fetchall()
    docs = [d["id"] for d in out["run"]["input_refs"]["transcripts"]]
    out["transcripts"] = conn.execute("SELECT * FROM transcripts WHERE transcript_id=ANY(%s) ORDER BY transcript_id", (docs,)).fetchall()
    out["cards"] = conn.execute("SELECT angle_id,run_id FROM content_angles WHERE run_id=%s", (RUN,)).fetchall()
    out["schedule"] = conn.execute("SELECT * FROM settings WHERE key=%s", ("schedule.weekly_cycle.2026-11-01",)).fetchone()
    out["model_calls"] = conn.execute("SELECT stage,model,status,input_tokens,output_tokens,cost_usd,created_at,error FROM llm_runs WHERE details->>'run_id'=%s ORDER BY created_at", (RUN,)).fetchall()
    conn.rollback()
out["artifacts"] = {}
def capture(key):
    raw = store.read_bytes(key)
    out["artifacts"][key] = {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw), "base64": base64.b64encode(raw).decode()}
    return json.loads(raw)
failed = capture(f"experiments/sql/runs/{RUN}/angle_generation.failed.json")
prefix = f"service_calls/{failed['request_fingerprint']}/attempts"
for name in store.names(prefix):
    for filename in ("preflight.json", "request.json"):
        key = f"{prefix}/{name}/{filename}"
        if store.exists(key):
            obj = capture(key)
            if filename == "preflight.json":
                capture(obj["route_snapshot"])
                capture(BYTE_BUDGET_MODELS[obj["model"]])
print(base64.b64encode(gzip.compress(json.dumps(out, default=str, ensure_ascii=False).encode())).decode(), flush=True)
