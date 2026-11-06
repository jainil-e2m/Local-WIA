"""N8's cycles on a scratch copy (not product code): preview a window through the stack's API, start it as the app does with
the window's week-dated calls added by hand, wait for it, and save its detail and the week's review.

Usage (from backend/): python -I ../research/n8-2026-10/cycle.py <out_dir> <label> <from> <to> [<undated transcript id>...]
STACK_API, STACK_SECRET and STACK_ACTOR name the stack's API (research/packs-2026-10/np5/api.py); STACK_DB the copy's
database URL from this machine, for the wait.
"""
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "packs-2026-10" / "np5"))
import psycopg  # noqa: E402
from api import call  # noqa: E402


def wait(run_id, limit=3600):
    deadline = time.time() + limit
    while time.time() < deadline:
        with psycopg.connect(os.environ["STACK_DB"], connect_timeout=30) as conn:
            status = conn.execute("SELECT status FROM pipeline_runs WHERE run_id=%s", (run_id,)).fetchone()[0]
        if status not in ("queued", "running"):
            return status
        time.sleep(15)
    return "timeout"


def main():
    out, label, start, end, *undated = sys.argv[1:]
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    status, preview = call("GET", "/cycles/preview", **{"from": start, "to": end})
    if status != 200:
        raise SystemExit(f"preview: {status} {preview}")
    (out / f"{label}.preview.json").write_text(json.dumps(preview, indent=1, default=str), encoding="utf-8")
    status, started = call("POST", "/cycles", {"window_start": start, "window_end": end, "selection_hash": preview["selection_hash"],
                                              "mode": "live", "include_undated": undated})
    if status != 202:
        raise SystemExit(f"start: {status} {started}")
    print(label, started)
    final = wait(started["run_id"])
    _, detail = call("GET", f"/cycles/{started['run_id']}")
    (out / f"{label}.cycle.json").write_text(json.dumps(detail, indent=1, default=str), encoding="utf-8")
    week = detail.get("week_id") or started.get("week_id")
    if week:
        _, review = call("GET", f"/weeks/{week}")
        (out / f"{label}.week.json").write_text(json.dumps(review, indent=1, default=str), encoding="utf-8")
    print(label, final, [f"{s['stage']}:{s['status']}" for s in detail.get("stages", [])])


if __name__ == "__main__":
    main()
