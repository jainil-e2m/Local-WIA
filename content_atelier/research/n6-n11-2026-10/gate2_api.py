"""Gate 2 through the API, as the brief screen does it (not product code): the CTA confirmed as proposed, the
before-publishing answers, the claims check, then the approval that starts the pack. Reads the same actions file as
np5/gate2.py (edits are not supported here). Usage: python -I gate2_api.py <actions.json> <label>; STACK_* as for api.py."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "packs-2026-10" / "np5"))
from api import call  # noqa: E402

actions = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
spec = next(b for b in actions["briefs"] if b["label"] == sys.argv[2])
assert not spec["edits"], "edits are applied with np5/gate2.py"
bid, steps = spec["brief_id"], []


def get(brief_id):
    status, row = call("GET", f"/briefs/{brief_id}")
    assert status == 200, row
    return row


def step(name, path, body):
    global bid
    status, result = call("POST", f"/briefs/{bid}/{path}", body)
    assert status == 200, (name, status, result)
    bid = result.get("brief_id") or bid
    steps.append({name: status, "brief_id": bid, **({"pack_run": result.get("pack_run")} if result.get("pack_run") else {})})
    return result


row = get(bid)
cta = row["content_body"]["document"]["header"]["cta"]
if cta.get("chosen_by") != "person":
    step("cta", "cta", {"expected_hash": row["content_hash"], **{k: cta.get(k) for k in ("choice", "track", "action", "offer_connection")}})
    row = get(bid)
answers = {k: (actions["client_okay"] if v == "client_okay" else v) for k, v in spec["answers"].items()}
step("answers", "answers", {"expected_hash": row["content_hash"], "answers": answers})
row = get(bid)
claims = [c["claim_id"] for c in row["content_body"]["document"]["body"]["claims"]]
step("review", "review", {"expected_hash": row["content_hash"], "claim_ids": claims, "reason": spec["review_reason"],
                          "history_acknowledged": True})
row = get(bid)
left = [b for b in row["blocker_items"] if b["kind"] != "role"]
if left:
    print(json.dumps({"blocked": left, "steps": steps}, indent=1, default=str))
    sys.exit(1)
step("decision", "decision", {"expected_hash": row["content_hash"], "decision": "approved", "author": actions["author"],
                              "note": "Approved by the WIA team under delegation (D12); Whitney has not reviewed it."})
print(json.dumps({"label": spec["label"], "steps": steps}, indent=1, default=str))
