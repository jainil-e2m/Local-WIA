"""T2: does export-derived context make first drafts closer to what Whitney approves?

Tasks (data/t2_tasks.jsonl): ten real requests Whitney made of her ChatGPT (captions, emails, a carousel, Threads,
stories, a sponsor blurb, podcast pitches), with ChatGPT's first draft and the version she approved or wrote.
Arms, both on the planned brief and strategist model:
  G1  the knowledge base as loaded today
  G2  the knowledge base plus the export pack (data/pack_rules.md and pack_exemplars.jsonl, same conversation removed)
ChatGPT's own first draft (A0) had the conversation's history and memory; G1 and G2 see only the request.
Usage: python t2_write.py <G1|G2> [model]
"""
import json, sys, concurrent.futures as cf
from common import ROOT, kb_text, load_jsonl
from runner import call

ARM = sys.argv[1]
MODEL = sys.argv[2] if len(sys.argv) > 2 else "openai/gpt-6.1-sol"
tasks = load_jsonl(ROOT / "data" / "t2_tasks.jsonl")

WRITER = ("You write marketing copy for Wedding Industry Ads (WIA), an advertising agency for wedding venues and "
          "wedding professionals, in the voice of its co-founder, Whitney Hodges. The request below is from Whitney. "
          "Produce the one finished piece she asked for. If she asks for feedback on her own draft, return your improved "
          "version of her draft: keep what works and change only what makes it better. Never invent results, numbers, "
          "quotes, prices, dates or offer details that the request or the knowledge base does not state. Return only "
          "the finished copy, with no commentary.")


def prefix_for(task):
    kb = kb_text()
    if ARM == "G1":
        return kb, WRITER
    pack = (ROOT / "data" / "pack_rules.md").read_text(encoding="utf-8")
    ex = [e for e in load_jsonl(ROOT / "data" / "pack_exemplars.jsonl") if e.get("file") != task["file"]]
    ex_text = "\n\n".join(f"[{e['channel']}, {e['date']}]\n{e['text']}" for e in ex)
    return (kb + "\n\n# HOW WHITNEY EDITS (from her ChatGPT history)\n\n" + pack +
            "\n\n# COPY WHITNEY WROTE OR APPROVED (patterns, not formulas)\n\n" + ex_text), WRITER


def run(task):
    prefix, system = prefix_for(task)
    rid = f"T2-{ARM}-{MODEL.split('/')[-1]}-{task['id']}"
    r = call(rid, MODEL, system, task["request"], effort="medium", max_tokens=6000, estimate_usd=0.12,
             cache_prefix=prefix)
    return task["id"], (r.get("content") or json.dumps(r.get("output")) or "").strip(), r["meta"]["cost"]


res = {}
with cf.ThreadPoolExecutor(5) as ex:
    for f in cf.as_completed([ex.submit(run, t) for t in tasks]):
        try:
            tid, text, cost = f.result()
            res[tid] = {"text": text, "cost": cost}
        except Exception as e:
            print("ERR", e)
out = ROOT / "results" / f"T2-{ARM}-{MODEL.split('/')[-1]}.json"
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
print(ARM, MODEL, "done", len(res), "cost", round(sum(v["cost"] or 0 for v in res.values()), 3))
