"""NP-7's proofs on a scratch copy (not product code): a recorded take on a face-to-camera Reel, then a grant, through the
stack's API exactly as the app sends them, each waited on and saved.

Usage (from backend/): python -I ../research/n5-2026-10/passes.py <out_dir> <pack_id> <take file> <grant statement> [--skip-take]
STACK_API, STACK_SECRET and STACK_ACTOR name the API (research/packs-2026-10/np5/api.py); STACK_DB the copy's database URL
from this machine, for the waits.
"""
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "packs-2026-10" / "np5"))
import psycopg  # noqa: E402
from api import call  # noqa: E402

TERMINAL = {"completed", "failed", "cancelled", "waiting", "blocked"}


def wait(run_id, limit=900):
    deadline = time.time() + limit
    while True:
        with psycopg.connect(os.environ["STACK_DB"], connect_timeout=30) as conn:
            rows = conn.execute("SELECT stage,status,current_message FROM pipeline_jobs WHERE run_id=%s ORDER BY created_at", (run_id,)).fetchall()
        if rows and all(r[1] in TERMINAL for r in rows) or time.time() > deadline:
            return [{"stage": r[0], "status": r[1], "message": r[2]} for r in rows]
        time.sleep(10)


def run(out, label, method, path, body):
    status, started = call(method, path, body)
    if status != 202:
        raise SystemExit(f"{label}: {status} {started}")
    jobs = wait(started["run_id"])
    _, pack = call("GET", f"/packs/{started['pack_id']}")
    (out / f"{label}.pack.json").write_text(json.dumps(pack, indent=1, default=str), encoding="utf-8")
    (out / f"{label}.jobs.json").write_text(json.dumps(jobs, indent=1), encoding="utf-8")
    print(label, started["pack_id"], pack.get("state"), [f"{j['stage']}:{j['status']}" for j in jobs])
    return pack


def main():
    out, pack_id, take_file, statement = Path(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4]
    out.mkdir(parents=True, exist_ok=True)
    _, pack = call("GET", f"/packs/{pack_id}")
    if "--skip-take" not in sys.argv:
        said = Path(take_file).read_text(encoding="utf-8").strip()
        pack = run(out, "caption-pass", "POST", f"/packs/{pack_id}/pieces/reel_1/recorded",
                   {"request_id": f"np7-take-{pack_id}", "expected_manifest_hash": pack["manifest_hash"], "said": said})
    pack = run(out, "refinish", "POST", f"/packs/{pack['pack_id']}/refinish",
               {"request_id": f"np7-grant-{pack['pack_id']}", "expected_manifest_hash": pack["manifest_hash"],
                "grants": [{"item_id": "S1" if pack.get("stronger_with_permission") else None, "statement": statement}]})


if __name__ == "__main__":
    main()
