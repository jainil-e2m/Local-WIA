"""NP-6: save production's packs as the pack screen reads them, and compare each with the proof's (not product code).

Usage (from backend/, through remote.py): python -I ../research/packs-2026-10/np5/remote.py \
    ../research/packs-2026-10/np5/prodread.py <label>=<pack_id>[:<proof pack file>] ...
Each pack is written to research/packs-2026-10/production/<label>.pack.json; with a proof file, its pieces, notes and
client quotes are compared with the proof's. `week=<week_id>` writes that week's pack listing and proposed plan.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "backend"))

from backend_pipeline.gates.roles import actor_for  # noqa: E402
from backend_pipeline.packs import api_v2  # noqa: E402
from backend_pipeline.repository import ContentRepository  # noqa: E402
from backend_pipeline.storage_config import StorageSettings  # noqa: E402

repo = ContentRepository(StorageSettings.from_env())
actor = actor_for(repo, "ai@weddingindustryads.com")
out = HERE.parent / "production"
out.mkdir(exist_ok=True)
for arg in sys.argv[1:]:
    label, _, rest = arg.partition("=")
    if label == "week":
        listing = api_v2.listing(repo, actor, week_id=rest)
        plan = api_v2.week_plan(repo, rest, actor)
        (out / f"{rest}.week.json").write_text(json.dumps({"listing": listing, "plan": plan}, indent=1, ensure_ascii=False,
                                                          default=str), encoding="utf-8")
        items = listing.get("items") or listing.get("packs") or []
        print("week", rest, "packs:", [(i.get("pack_id"), i.get("state")) for i in items])
        print("plan keys:", sorted(plan))
        continue
    pack_id, _, ref = rest.partition(":")
    prod = api_v2.detail(repo, pack_id, actor)
    (out / f"{label}.pack.json").write_text(json.dumps(prod, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    line = f"{label} {pack_id} state={prod['state']} blockers={len(prod['ready_blockers'])}"
    if ref:
        proof = json.loads((HERE / "proof" / ref).read_text(encoding="utf-8"))
        same = [p["content"] for p in prod["pieces"]] == [p["content"] for p in proof["pieces"]]
        notes = (prod["pack_notes"], prod["client_quotes"]) == (proof["pack_notes"], proof["client_quotes"])
        line += f" pieces_identical={same} notes_and_quotes_identical={notes}"
    print(line)
