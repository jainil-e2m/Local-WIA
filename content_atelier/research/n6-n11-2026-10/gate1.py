"""N11's benchmark on a scratch copy (not product code): Gate 1 as the WIA team's delegated reviewer (D12, R55). Develops one
card through the stack's API exactly as the card screen does: every verify-before-publishing item acknowledged, the CTA
decided in development, the note naming the delegation. Saves the request and the answer.

Usage (from backend/): python -I ../research/n6-n11-2026-10/gate1.py <angle_id> <out.json> "<note>" [--overlap]
(`--overlap` acknowledges an overlap with another card of the batch, the note saying how this one is distinct.)
STACK_API, STACK_SECRET and STACK_ACTOR name the stack's API (research/packs-2026-10/np5/api.py); STACK_DB the copy's
database URL from this machine.
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "packs-2026-10" / "np5"))
import psycopg  # noqa: E402
from api import call  # noqa: E402

angle_id, out, note = sys.argv[1], Path(sys.argv[2]), sys.argv[3]
overlap = "--overlap" in sys.argv[4:]
with psycopg.connect(os.environ["STACK_DB"]) as conn:
    content_hash, verify = conn.execute(
        "SELECT content_hash,content_body->'card'->'verify_before_publishing' FROM content_angles WHERE angle_id=%s",
        (angle_id,)).fetchone()
request = {"expected_hash": content_hash, "disposition": "develop", "author": os.environ.get("GATE_AUTHOR", "kenil.shah@e2m.solutions (delegated, D12)"),
           "note": note, "cta": {"choice": "decide_in_development"}, "verify_acknowledged": verify or [],
           "overlap_acknowledged": overlap}
status, response = call("POST", f"/angles/{angle_id}/decision", request)
out.write_text(json.dumps({"angle_id": angle_id, "request": request, "status": status, "response": response}, indent=1,
                          default=str), encoding="utf-8")
print(status, json.dumps(response, default=str)[:600])
