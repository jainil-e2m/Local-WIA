"""Gate 2 on production through its API, one step per call (N4 7.X1; not product code).

Usage: python -I gate2api.py gate2-x1.json <step> [brief_id], where step is edit, revise, cta, answers, review or approve. STACK_API,
STACK_SECRET and STACK_ACTOR name the API (through a temporary TCP proxy), its shared secret and the signed-in person.
Each step reads the named version (each step returns the next version's id) and sends its hash, as the app does.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "packs-2026-10" / "np5"))
from api import call  # noqa: E402

acts = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
step = sys.argv[2]


def newest(bid):
    status, row = call("GET", f"/briefs/{bid}")
    assert status == 200, (status, row)
    assert not row.get("has_replacement"), f"{bid} has a newer version: pass its id"
    return row


def leaf(body, path):
    import re
    cur = body
    for part in re.findall(r"[^.\[\]]+|\[\d+\]", path):
        cur = cur[int(part[1:-1])] if part.startswith("[") else cur[part]
    return cur


row = newest(sys.argv[3] if len(sys.argv) > 3 else acts["brief_id"])
bid, h = row["brief_id"], row["content_hash"]
body = row["content_body"]["document"]["body"]
if step == "edit":
    changes = {}
    for e in acts["edits"]:
        current = changes.get(e["path"], leaf(body, e["path"]))
        assert current.count(e["old"]) == 1, (e["path"], current.count(e["old"]))
        changes[e["path"]] = current.replace(e["old"], e["new"])
    result = call("PATCH", f"/briefs/{bid}", {"expected_hash": h, "changes": changes, "note": acts["edit_note"]})
elif step == "revise":
    result = call("POST", f"/briefs/{bid}/revise", {"expected_hash": h, "instructions": acts["revise"], "mode": "live"})
elif step == "cta":
    result = call("POST", f"/briefs/{bid}/cta", {"expected_hash": h, **acts["cta"]})
elif step == "answers":
    result = call("POST", f"/briefs/{bid}/answers", {"expected_hash": h, "answers": acts["answers"]})
elif step == "review":
    claims = [c["claim_id"] for c in body["claims"]]
    result = call("POST", f"/briefs/{bid}/review", {"expected_hash": h, "claim_ids": claims, "reason": acts["review_reason"],
                                                     "history_acknowledged": True})
elif step == "approve":
    result = call("POST", f"/briefs/{bid}/decision", {"expected_hash": h, "decision": "approved", "note": acts["decision_note"],
                                                       "author": acts["author"], "reason_code": None})
elif step == "show":
    result = (200, {"brief_id": bid, "content_hash": h, "approval_status": row["approval_status"],
                    "blockers": row["blocker_items"], "locked": row.get("locked_fields")})
else:
    raise SystemExit(f"unknown step {step}")
print(json.dumps({"step": step, "from": bid, "status": result[0], "result": result[1]}, indent=1, default=str, ensure_ascii=False)[:6000])
