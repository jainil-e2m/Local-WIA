"""Gate 2 on a scratch copy through the API, as the brief screen does it (not product code): the reviewer's edits, the CTA
confirmed as proposed, the before-publishing answers, the claims check, then the approval that starts the pack. Usage:
python -I gate2.py <actions.json> <label>; STACK_* as for research/packs-2026-10/np5/api.py."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "packs-2026-10" / "np5"))
from api import call  # noqa: E402

actions = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
spec = next(b for b in actions["briefs"] if b["label"] == sys.argv[2])
bid, steps = spec["brief_id"], []


def get():
    status, row = call("GET", f"/briefs/{bid}")
    assert status == 200, row
    return row


def step(name, method, path, body):
    global bid
    status, result = call(method, path, body)
    assert status == 200, (name, status, result)
    bid = result.get("brief_id") or bid
    steps.append({name: status, "brief_id": bid, **({"pack_run": result.get("pack_run")} if result.get("pack_run") else {})})
    return result


row = get()
if spec.get("edits"):
    step("edits", "PATCH", f"/briefs/{bid}", {"expected_hash": row["content_hash"], "changes": spec["edits"]})
    row = get()
cta = row["content_body"]["document"]["header"]["cta"]
if cta.get("chosen_by") != "person":
    step("cta", "POST", f"/briefs/{bid}/cta", {"expected_hash": row["content_hash"],
                                                **{k: cta.get(k) for k in ("choice", "track", "action", "offer_connection")}})
    row = get()
step("answers", "POST", f"/briefs/{bid}/answers", {"expected_hash": row["content_hash"], "answers": spec["answers"]})
row = get()
claims = [c["claim_id"] for c in row["content_body"]["document"]["body"]["claims"]]
step("review", "POST", f"/briefs/{bid}/review", {"expected_hash": row["content_hash"], "claim_ids": claims,
                                                  "reason": spec["review_reason"], "history_acknowledged": True})
row = get()
left = [b for b in row["blocker_items"] if b["kind"] != "role"]
if left:
    print(json.dumps({"blocked": left, "steps": steps}, indent=1, default=str))
    sys.exit(1)
step("decision", "POST", f"/briefs/{bid}/decision", {"expected_hash": row["content_hash"], "decision": "approved",
                                                      "author": actions["author"],
                                                      "note": "Approved by the WIA team under delegation (D12); Whitney has not reviewed it."})
print(json.dumps({"label": spec["label"], "steps": steps}, indent=1, default=str))
