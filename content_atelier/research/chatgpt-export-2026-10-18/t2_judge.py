"""T2 judging: which candidate would need fewer edits to become what Whitney approved?

Reference-based pairwise judging (both presentation orders) by a model family different from the generator.
The judge sees Whitney's approved version as the reference; it never sees any prompt or pack text.
Comparisons: G2 vs A0, G1 vs A0, G2 vs G1. Also a deterministic style lint per candidate.
Usage: python t2_judge.py [judge_model] [writer_model]
"""
import json, sys, concurrent.futures as cf
from common import ROOT, load_jsonl, parse_json
from runner import call
from lint import counts

JUDGE = sys.argv[1] if len(sys.argv) > 1 else "anthropic/claude-sonnet-5.5"
WRITER = sys.argv[2] if len(sys.argv) > 2 else "gpt-6.1-sol"
tasks = {t["id"]: t for t in load_jsonl(ROOT / "data" / "t2_tasks.jsonl")}
g1 = json.loads((ROOT / "results" / f"T2-G1-{WRITER}.json").read_text(encoding="utf-8"))
g2 = json.loads((ROOT / "results" / f"T2-G2-{WRITER}.json").read_text(encoding="utf-8"))

SYSTEM = ("You compare two draft pieces of marketing copy for Wedding Industry Ads (WIA), a wedding-industry "
          "advertising agency. You are given the request, the version WIA's co-founder Whitney actually approved or "
          "wrote (the reference), and two candidate drafts. Decide which candidate would need fewer and smaller edits "
          "to become something Whitney would approve. Judge substance first (what is claimed, for whom, how WIA is "
          "positioned, accuracy, whether her own wording was kept where she supplied it), then voice. Do not reward "
          "length, and do not require the candidate to copy the reference wording.\n\nReturn only JSON: "
          '{"winner": "A" or "B" or "tie", "edits_needed_A": "few", "edits_needed_B": "many", "reason": "one or two sentences"}'
          " where edits_needed values are none, few, some or many.")


def cand(arm, tid):
    if arm == "A0":
        return tasks[tid]["chatgpt_draft"]
    return (g1 if arm == "G1" else g2)[tid]["text"]


def run(tid, x, y, order):
    a, b = (x, y) if order == "XY" else (y, x)
    t = tasks[tid]
    user = (f"Request:\n{t['request'][:4000]}\n\nReference (what Whitney approved):\n{t['whitney_final']}\n\n"
            f"Candidate A:\n{cand(a, tid)}\n\nCandidate B:\n{cand(b, tid)}")
    rid = f"T2J-{JUDGE.split('/')[-1]}-{tid}-{x}v{y}-{order}"
    r = call(rid, JUDGE, SYSTEM, user, max_tokens=700, estimate_usd=0.03, temperature=0)
    o = parse_json(r.get("output") or r.get("content")) or {}
    w = o.get("winner")
    win = a if w == "A" else b if w == "B" else "tie" if w == "tie" else None
    return {"task": tid, "pair": f"{x}v{y}", "order": order, "winner": win, "reason": o.get("reason"),
            "cost": r["meta"]["cost"]}


jobs = [(tid, x, y, o) for tid in tasks for (x, y) in (("G2", "A0"), ("G1", "A0"), ("G2", "G1")) for o in ("XY", "YX")]
res = []
with cf.ThreadPoolExecutor(6) as ex:
    for f in cf.as_completed([ex.submit(run, *j) for j in jobs]):
        try:
            res.append(f.result())
        except Exception as e:
            print("ERR", e)
lint = {tid: {arm: counts(cand(arm, tid)) for arm in ("A0", "G1", "G2")} | {"final": counts(tasks[tid]["whitney_final"])}
        for tid in tasks}
out = ROOT / "results" / f"T2-judged-{JUDGE.split('/')[-1]}.json"
out.write_text(json.dumps({"judgements": res, "lint": lint}, indent=1, ensure_ascii=False), encoding="utf-8")
for pair in ("G2vA0", "G1vA0", "G2vG1"):
    rs = [r for r in res if r["pair"] == pair]
    x, y = pair.split("v")
    wx = sum(r["winner"] == x for r in rs); wy = sum(r["winner"] == y for r in rs); ti = sum(r["winner"] == "tie" for r in rs)
    by = {}
    for r in rs:
        by.setdefault(r["task"], set()).add(r["winner"])
    consistent_x = sum(v == {x} for v in by.values()); consistent_y = sum(v == {y} for v in by.values())
    print(f"{pair}: {x} {wx}, {y} {wy}, tie {ti} of {len(rs)} | tasks won both orders: {x} {consistent_x}, {y} {consistent_y}")
tot = {arm: sum(sum(v[arm].values()) for v in lint.values()) for arm in ("A0", "G1", "G2", "final")}
print("lint findings (sum over tasks):", tot)
print("judge cost", round(sum(r["cost"] or 0 for r in res), 3))
