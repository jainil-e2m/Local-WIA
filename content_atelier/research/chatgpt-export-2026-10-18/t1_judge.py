"""T1: can a model judge predict which version Whitney chose?

Items: preference pairs from the ChatGPT export (an AI or team draft, and the version Whitney wrote or approved),
WIA marketing copy only, no item flagged as private client information (data/t1_pairs.jsonl).
Each pair is judged in both presentation orders. Configurations:
  J0  a one-paragraph description of WIA only
  J1  plus the knowledge base as the strategist loads it today
  J2  plus the export-derived voice and positioning pack (data/pack_rules.md), with exemplars from the same
      conversation removed (leave-one-out)
Usage: python t1_judge.py <config> <model> [limit]
"""
import json, sys, concurrent.futures as cf, pathlib
from common import ROOT, kb_text, load_jsonl, parse_json
from runner import call

CONFIG, MODEL = sys.argv[1], sys.argv[2]
LIMIT = int(sys.argv[3]) if len(sys.argv) > 3 else None
pairs = load_jsonl(ROOT / "data" / "t1_pairs.jsonl")[:LIMIT]

BASE = ("You are evaluating marketing content for Wedding Industry Ads (WIA), an advertising agency that runs "
        "Google and Meta ads and lead follow-up for wedding venues and wedding professionals. WIA's founder is "
        "Whitney Hodges. You will see two versions of the same piece of WIA content. Decide which version Whitney "
        "would approve to publish or send as it is.\n\nReturn only JSON: "
        '{"choice": "A" or "B", "confidence": 1 to 5, "reason": "one short sentence"}')


def system_for(item):
    if CONFIG == "J0":
        return BASE, None
    if CONFIG == "J1":
        return BASE, kb_text()
    if CONFIG == "J2":
        pack = (ROOT / "data" / "pack_rules.md").read_text(encoding="utf-8")
        ex = [e for e in load_jsonl(ROOT / "data" / "pack_exemplars.jsonl") if e.get("file") != item.get("file")]
        ex_text = "\n\n".join(f"[{e['channel']}, {e['date']}] {e['text']}" for e in ex[:14])
        prefix = kb_text() + "\n\n# HOW WHITNEY EDITS (from her ChatGPT history)\n\n" + pack
        return BASE + "\n\nExamples of copy Whitney wrote or approved:\n\n" + ex_text, prefix
    raise SystemExit("unknown config")


def run(item, order):
    a, b = (item["her_text"], item["ai_text"]) if order == "HA" else (item["ai_text"], item["her_text"])
    sys_text, prefix = system_for(item)
    user = f"Channel: {item['channel']}\n\nVersion A:\n{a}\n\nVersion B:\n{b}"
    rid = f"T1-{CONFIG}-{MODEL.split('/')[-1]}-{item['id']}-{order}"
    r = call(rid, MODEL, sys_text, user, max_tokens=900, estimate_usd=0.02, cache_prefix=prefix, temperature=0)
    out = parse_json(r.get("output") or r.get("content"))
    choice = (out or {}).get("choice")
    her = "A" if order == "HA" else "B"
    return {"id": item["id"], "order": order, "choice": choice, "correct": choice == her,
            "confidence": (out or {}).get("confidence"), "reason": (out or {}).get("reason"), "cost": r["meta"]["cost"]}


jobs = [(it, o) for it in pairs for o in ("HA", "AH")]
res = []
with cf.ThreadPoolExecutor(6) as ex:
    for f in cf.as_completed([ex.submit(run, it, o) for it, o in jobs]):
        try:
            res.append(f.result())
        except Exception as e:
            print("ERR", e)
out = ROOT / "results" / f"T1-{CONFIG}-{MODEL.split('/')[-1]}.json"
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
n = len(res)
acc = sum(r["correct"] for r in res) / n if n else 0
by = {}
for r in res:
    by.setdefault(r["id"], []).append(r["correct"])
both = sum(all(v) for v in by.values()); split = sum(len(set(v)) > 1 for v in by.values())
print(f"{CONFIG} {MODEL}: calls={n} accuracy={acc:.2f} pairs_right_both_orders={both}/{len(by)} order_flips={split} cost=${sum(r['cost'] or 0 for r in res):.3f}")
