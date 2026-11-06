"""Delegated Gate 1 edits (not product code): PATCH each card as the card screen does and save the answers.

Usage (from backend/): python -I ../research/n6-n11-2026-10/gate1_edit.py <edits.json> <out.json>; STACK_* as for gate1.py.
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "packs-2026-10" / "np5"))
import psycopg  # noqa: E402
from api import call  # noqa: E402

spec = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
out = []
for card in spec["cards"]:
    with psycopg.connect(os.environ["STACK_DB"]) as conn:
        (content_hash,) = conn.execute("SELECT content_hash FROM content_angles WHERE angle_id=%s", (card["angle_id"],)).fetchone()
    request = {"expected_hash": content_hash, "changes": card["changes"], "note": card["note"]}
    status, response = call("PATCH", f"/angles/{card['angle_id']}", request)
    out.append({"angle_id": card["angle_id"], "request": request, "status": status, "response": response})
    print(card["angle_id"], status, json.dumps(response, default=str)[:300])
Path(sys.argv[2]).write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
