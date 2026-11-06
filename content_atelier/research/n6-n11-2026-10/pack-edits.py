"""N11 benchmark (copy D): the WIA team's delegated pack edits, as a reviewer makes them on the pack screen (not product code).

Usage (from research/packs-2026-10/np5, the stack's API up): python -I ../../n6-n11-2026-10/pack-edits.py <edits.json>
Each edit is an exact replacement inside one field of one piece (PATCH /packs/{id}/pieces/{key}); an edit already applied
is skipped, so a rerun resumes. With "decision" set, the pack is then marked ready to publish (or left in review).
"""
import json
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "packs-2026-10" / "np5"))
from api import call  # noqa: E402


def field(content, path):
    node = content
    for part in path.replace("]", "").replace("[", ".").split("."):
        node = node[int(part)] if part.isdigit() else node[part]
    return node


def head(pack_id):
    """The newest version of a pack: an interrupted run resumes on it."""
    while True:
        status, pack = call("GET", f"/packs/{pack_id}")
        newer = (pack.get("versions") or [{}])[-1].get("pack_id") if isinstance(pack, dict) else None
        if not newer or newer == pack_id:
            return pack_id
        pack_id = newer


def main():
    spec = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    pid, out = head(spec["pack_id"]), []
    for e in spec["edits"]:
        status, pack = call("GET", f"/packs/{pid}")
        piece = next(p for p in pack["pieces"] if p["key"] == e["piece"])
        current = field(piece["content"], e["path"])
        if e["new"] in current and e["old"] not in current:
            out.append({"edit": f"{e['piece']}.{e['path']}", "status": "already applied"})
            continue
        assert current.count(e["old"]) == 1, (e["piece"], e["path"], current.count(e["old"]))
        status, saved = call("PATCH", f"/packs/{pid}/pieces/{e['piece']}",
                             {"request_id": uuid.uuid4().hex, "expected_manifest_hash": pack["manifest_hash"], "changes": {e["path"]: current.replace(e["old"], e["new"])}})
        out.append({"edit": f"{e['piece']}.{e['path']}", "status": status})
        assert status == 200, saved
        pid = saved["pack_id"]  # every edit is a new version
    status, pack = call("GET", f"/packs/{pid}")
    out.append({"ready_blockers": pack["ready_blockers"],
                "open": [f"{p['key']}: {f['check']} ({f['severity']})" for p in pack["pieces"] for f in p["findings"] if f["status"] == "open"]})
    if spec.get("decision") and not pack["ready_blockers"]:
        status, done = call("POST", f"/packs/{pid}/decision", {"request_id": uuid.uuid4().hex, "expected_manifest_hash": pack["manifest_hash"],
                                                               "decision": spec["decision"], "note": spec.get("note")})
        out.append({"decision": status, "state": (done or {}).get("state") if isinstance(done, dict) else done})
    print(json.dumps(out, indent=1, default=str))


if __name__ == "__main__":
    main()
