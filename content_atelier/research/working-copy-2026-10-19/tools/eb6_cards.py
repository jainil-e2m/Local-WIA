"""E.B6: embed every distinct Week 1-2 benchmark card with matching's own signature, and list same-week pairs by cosine."""
import glob, json, math, os, sys
from backend_pipeline.config import Settings
from backend_pipeline.contracts import signature_from_fields
from backend_pipeline.llm.providers import live_provider
from backend_pipeline.storage_config import StorageSettings
from backend_pipeline.store import canonical_hash
R = "/Users/kenilshah/Desktop/Wedding_industy_ads/WIA-Content-Atelier/research/benchmark-v1/runs/"
out = sys.argv[1]
cards, seen = [], set()
for path in sorted(glob.glob(R + "*.json")):
    run = json.load(open(path)); name = os.path.basename(path)
    for a in (run.get("output") or {}).get("angles") or []:
        sig = signature_from_fields(a)
        if sig in seen: continue
        seen.add(sig)
        cards.append({"id": f"c{len(cards):03d}", "week": run["week"], "run": name, "rank": a.get("rank"), "title": a["title"],
                      "argument": a.get("core_perspective"), "moment_ids": a.get("moment_ids") or [], "signature": sig})
models = Settings.from_env()
provider = live_provider(models, storage=StorageSettings.from_env(), chat=False)
vectors = []
for i in range(0, len(cards), 64):
    batch = [c["signature"] for c in cards[i:i + 64]]
    raw = provider.embed_many(texts=batch, fingerprint=canonical_hash({"eb6": batch}))
    vectors += [d["embedding"] for d in sorted(raw["data"], key=lambda d: d["index"])]
def cos(a, b): return sum(x * y for x, y in zip(a, b)) / math.sqrt(sum(x * x for x in a) * sum(y * y for y in b))
pairs = []
for i in range(len(cards)):
    for j in range(i + 1, len(cards)):
        if cards[i]["week"] == cards[j]["week"]:
            pairs.append({"a": cards[i]["id"], "b": cards[j]["id"], "cosine": round(cos(vectors[i], vectors[j]), 4),
                          "same_run": cards[i]["run"] == cards[j]["run"],
                          "shared_moments": sorted(set(cards[i]["moment_ids"]) & set(cards[j]["moment_ids"]))})
pairs.sort(key=lambda p: -p["cosine"])
json.dump({"cards": cards, "pairs": pairs}, open(out, "w"), indent=1)
print(len(cards), "cards", len(pairs), "same-week pairs")
