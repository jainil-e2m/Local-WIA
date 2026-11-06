"""NP.X3: brief 3's v2 pack as production finalizes it (not product code). The paid proof found that a put-back sentence
could repeat the one beside it; commit 8681aeb puts back the brief's paragraph instead. Finalize makes no model call, so
production's replay of this run gives the fixed text: this applies the fixed put_back to the saved pack's put-back changes.
Commit 3f60001: Finish again keeps a Reel the finisher wrote marked "written" (it has no brief copy), so it is relabelled.

Usage (from backend/): python -I ../research/packs-2026-10/np5/proof/shipped.py <pack.json> <out.json>
"""
import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "backend"))
from backend_pipeline.briefs import paths  # noqa: E402
from backend_pipeline.packs import finalize  # noqa: E402

pack = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
for piece in pack["pieces"]:
    if piece["origin"] == "finished" and piece["brief_copy"] is None and piece["content"] is not None:
        piece["origin"] = "written"
        print(f"{piece['key']}: written (no brief copy)")
    for i, change in enumerate(piece["changes"]):
        if change["kind"] != "put_back" or not change.get("before") or not change.get("after"):
            continue
        work = {"content": copy.deepcopy(piece["content"]), "brief_copy": piece["brief_copy"], "locks": piece["locks"]}
        text = paths.get(work["content"], change["path"])
        work["content"] = paths.put(work["content"], change["path"], text.replace(change["after"], change["before"], 1))
        redone = finalize.put_back(work, {"path": change["path"], "text": change["before"]})
        if redone and redone["after"] != change["after"]:
            piece["content"], piece["changes"][i] = work["content"], redone
            print(f"{piece['key']}.{change['path']}: {redone['note']}")
Path(sys.argv[2]).write_text(json.dumps(pack, indent=1, ensure_ascii=False), encoding="utf-8")
