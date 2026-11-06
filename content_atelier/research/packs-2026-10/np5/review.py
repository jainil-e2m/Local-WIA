"""NP.X3 and NP-6: the WIA team's delegated pack review (R55, D12), applied through the pack service (not product code).

Each step of the review file goes through the same functions the pack screen's routes call (`packs/api_v2.py`), as the
named team account: an edit (an exact replacement in one copy leaf, which locks the line as a person's), an attestation of
an open finding (R57), Finish again, or a create (retry a waiting run, or replace one stuck on a changed contract). The
brief is found by its first id and followed to its newest version; the pack is that brief's current pack. Every step reads the pack's current manifest hash, so a step refused as stale is visible.

Usage (from backend/, ATELIER_DATABASE_URL and the artifact store set):
    python -I ../research/packs-2026-10/np5/review.py <review.json> [--dry-run]
"""
import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve()
sys.path.insert(0, str(_HERE.parents[3] / "backend"))

from backend_pipeline.briefs import paths  # noqa: E402
from backend_pipeline.gates.roles import actor_for  # noqa: E402
from backend_pipeline.packs import api_v2, model  # noqa: E402
from backend_pipeline.packs.contracts_v2 import PackAttest, PackCreate, PackEdit, PackFinishAgain  # noqa: E402
from backend_pipeline.repository import ContentRepository  # noqa: E402
from backend_pipeline.storage_config import StorageSettings  # noqa: E402

sys.path.insert(0, str(_HERE.parent))
from gate2 import head, norm  # noqa: E402


def main():
    review = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    dry = "--dry-run" in sys.argv
    repo = ContentRepository(StorageSettings.from_env())
    actor = actor_for(repo, review["actor"])
    out = []
    only = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else None
    for n, step in enumerate(review["steps"], 1):
        if only and not step["label"].startswith(only):
            continue
        try:
            out.append(apply(repo, actor, review, n, step, dry))
        except Exception as error:  # noqa: BLE001 - each step's refusal is recorded, the rest still run
            out.append({"step": n, "label": step["label"], "error": f"{type(error).__name__}: {error}"})
    print(json.dumps(out, indent=1, default=str))


def apply(repo, actor, review, n, step, dry):
    bid = head(repo, step["brief_id"])
    with repo.connection() as conn:
        pack = model.current_for_brief(conn, bid)
    if not pack and step["action"] != "create":
        return {"step": n, "label": step["label"], "brief_id": bid, "error": "no pack"}
    found = api_v2.detail(repo, pack["pack_id"], actor) if pack else {"manifest_hash": None, "state": None, "pieces": []}
    manifest, request_id = found["manifest_hash"], f"np6-review-{review['name']}-{n}"
    record = {"step": n, "label": step["label"], "action": step["action"], "pack_id": pack and pack["pack_id"],
              "state": found["state"]}
    if step["action"] == "edit":
        piece = next(p for p in found["pieces"] if p["key"] == step["key"])
        current = paths.get(piece["content"], step["path"])
        if step["old"] not in current and step["new"] in current:
            return {**record, "result": "already applied"}
        assert current.count(step["old"]) == 1, (step["label"], step["path"], current.count(step["old"]))
        changes = {step["path"]: current.replace(step["old"], step["new"])}
        if not dry:
            done = api_v2.edit(repo, pack["pack_id"], step["key"],
                               PackEdit(request_id=request_id, expected_manifest_hash=manifest, changes=changes), actor)
            record.update(new_pack_id=done.get("pack_id"), result=done.get("state"))
    elif step["action"] == "attest":
        finding = next(f for p in found["pieces"] for f in p.get("findings") or []
                       if f.get("status") == "open" and norm(step["sentence"]) in norm(f.get("sentence")))
        record["finding_id"] = finding["finding_id"]
        if not dry:
            done = api_v2.attest(repo, pack["pack_id"], finding["finding_id"],
                                 PackAttest(request_id=request_id, expected_manifest_hash=manifest,
                                            statement=step["statement"]), actor)
            record.update(new_pack_id=done.get("pack_id"), result=done.get("state"))
    elif step["action"] == "create":
        # POST /briefs/{id}/pack: retry a waiting run, or replace one stuck on a changed contract (queue.create).
        if not dry:
            done = api_v2.create(repo, bid, PackCreate(request_id=request_id, mode=step.get("mode")), actor)
            record.update(new_pack_id=done.get("pack_id"), result=done.get("status"), run_id=done.get("run_id"),
                          mode=done.get("mode"))
    elif step["action"] == "finish_again":
        if not dry:
            done = api_v2.finish_again(repo, pack["pack_id"],
                                       PackFinishAgain(request_id=request_id, expected_manifest_hash=manifest), actor)
            record.update(new_pack_id=done.get("pack_id"), result=done.get("state"), run_id=done.get("run_id"))
    return record


if __name__ == "__main__":
    main()
