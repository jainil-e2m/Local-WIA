"""WIA's notes of 13 and 20 October as the judge's labelled set (E.B3; plan section 3.3: "her notes become a labelled set
the judge and the checks are measured against"). A diagnostic, never the measure: WIA's judgement on live weeks is (4.5).

The set (`research/judge-labels/wia-notes-2026-10.json`, client material, R48) holds one label per asset WIA commented on:
the text she was shown (hand-built packs, never system output, R58), her verdict (fail or pass), her words, the kind of
correction and, where she worded one, her corrected text. Process and scope notes (W9 to W13) are kept and never scored.

Two measurements:

- **Recorded judge outputs, offline** (`score_recorded`): a recorded verdict per label (`research/judge-labels/recorded/`,
  each with its source and granularity) is scored against her verdicts: her failures it caught, her passes it kept, and
  the agreement by kind of correction. No model call. The second blind review of 20 October is the one recorded today: its
  pack-level "light edits" for Packs 1 and 3 passes every asset of those packs, so it caught none of W3 to W8.
- **The pairwise judge, a paid run** (`pairs`, `measure`): each label with her corrected text becomes a pair, the shown
  text against hers, which the judge should prefer, through E.B3's own judge (rubric 2.3a, both orders, a recorded seed,
  the run plan, saved responses reused). The shown text was written with Claude, so the judge is from another family
  (GPT-6.1 Sol by default; the judge refuses its own family). `--dry` counts the calls and gives the plan command.
"""
from __future__ import annotations

import json
from pathlib import Path

from . import judge
from .benchmark import RESEARCH

LABELS = RESEARCH / "judge-labels" / "wia-notes-2026-10.json"
RECORDED = RESEARCH / "judge-labels" / "recorded"
RESULTS = RESEARCH / "judge-labels" / "results"
GROUP = "wia_notes"
JUDGE_MODEL = "openai/gpt-6.1-sol"
# Who wrote the shown text: the hand-built packs were written with Claude (the developer's sessions and subagents).
SHOWN_BY = "anthropic/claude-opus-5"
VERDICTS = ("pass", "fail")


def load(path: Path = LABELS) -> dict:
    spec = json.loads(Path(path).read_text(encoding="utf-8"))
    ids = [label["id"] for label in spec["labels"]]
    if len(ids) != len(set(ids)):
        raise ValueError(f"{Path(path).name}: every label needs its own id")
    for label in spec["labels"]:
        if label.get("scored") and (label.get("verdict") not in VERDICTS or not label.get("shown")):
            raise ValueError(f"{Path(path).name}: scored label {label['id']} needs a verdict (pass or fail) and the text shown")
    return spec


def scored(spec: dict) -> list[dict]:
    return [label for label in spec["labels"] if label.get("scored")]


def score_recorded(spec: dict, recorded: dict) -> dict:
    """One recorded judge's verdicts against her labels: failures caught, passes kept, agreement by kind."""
    labels = {label["id"]: label for label in scored(spec)}
    verdicts = recorded["verdicts"]
    unknown = sorted(set(verdicts) - set(labels))
    if unknown:
        raise ValueError(f"{recorded.get('judge')}: verdicts for labels the set does not hold: {', '.join(unknown)}")
    rows = [{"id": i, "kind": labels[i]["kind"], "hers": labels[i]["verdict"], "judge": v, "agrees": labels[i]["verdict"] == v}
            for i, v in sorted(verdicts.items())]
    fails = [r for r in rows if r["hers"] == "fail"]
    passes = [r for r in rows if r["hers"] == "pass"]
    kinds = {}
    for r in rows:
        kinds.setdefault(r["kind"], []).append(r["agrees"])
    return {"judge": recorded["judge"], "source": recorded["source"], "granularity": recorded.get("granularity"),
            "labels_judged": len(rows), "labels_not_judged": sorted(set(labels) - set(verdicts)),
            "agreement": judge.share(sum(r["agrees"] for r in rows), len(rows)),
            "her_failures_caught": judge.share(sum(r["judge"] == "fail" for r in fails), len(fails)),
            "her_passes_kept": judge.share(sum(r["judge"] == "pass" for r in passes), len(passes)),
            "missed": [r["id"] for r in fails if r["judge"] != "fail"],
            "by_kind": {k: judge.share(sum(v), len(v)) for k, v in sorted(kinds.items())}, "rows": rows}


def recorded_outputs(directory: Path = RECORDED) -> list[dict]:
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(Path(directory).glob("*.json"))]


def pairs(spec: dict) -> list[judge.Pair]:
    """Each label with her corrected text, as a pair the judge should decide for her version."""
    out = []
    for label in scored(spec):
        if not label.get("corrected"):
            continue
        shown = judge.Candidate(f"{label['id']}:shown", (("Text", label["shown"]),), None, SHOWN_BY)
        hers = judge.Candidate(f"{label['id']}:whitney", (("Text", label["corrected"]),), None, "whitney")
        out.append(judge.Pair(f"wia-{label['id']}", GROUP, f"first-touch copy: {label['asset']} (the first thing a cold reader sees)",
                              shown, hers, hers.id, label_ids=(label["id"],),
                              details={"kind": label["kind"], "date": label["date"]}))
    return out


def measure(spec: dict, *, model: str = JUDGE_MODEL, context: str = judge.DEFAULT_CONTEXT, seed: int = judge.DEFAULT_SEED,
            mode: str = "paid", kb=None) -> dict:
    """The pairwise judge on her pairs, both orders: how often it prefers her version, and its order flips."""
    labelled = pairs(spec)
    head, comparisons = judge._judge_all(labelled, model=model, context=context, seed=seed, both_orders=True, mode=mode, kb=kb)
    head["labels"] = {"set": spec["version"], "pairs": len(labelled)}
    if mode == "dry":
        return judge._dry(head, comparisons, "E.B3 judge on WIA's notes")
    judged = [c for c in comparisons if c["status"] == "judged"]
    by_pair = {}
    for c in judged:
        by_pair.setdefault(c["pair_id"], []).append(c)
    both = [v for v in by_pair.values() if len(v) == 2]
    return {**head, "judgements": judge.share(sum(c["agrees"] for c in judged), len(judged)),
            "pairs_right_in_both_orders": judge.share(sum(x["agrees"] and y["agrees"] for x, y in both), len(both)),
            "order_flips": sum(x["preferred"] != y["preferred"] for x, y in both),
            "missing": sum(c["status"] == "missing" for c in comparisons),
            "unparsed": sum(c["status"] == "unparsed" for c in comparisons),
            "total_cost_usd": round(sum(c.get("cost") or 0 for c in comparisons), 6), "comparisons": judge._rows(comparisons),
            "notes": ["A diagnostic, never the measure (E.B3, plan 4.5): WIA's judgement on live weeks is the measure.",
                      "The shown texts are hand-built (R58); her corrected texts are hers. Neither is a prompt exemplar (D28)."]}


def report(*, recorded_dir: Path = RECORDED) -> dict:
    """The offline part: every recorded judge output scored against her labels."""
    spec = load()
    return {"set": spec["version"], "labels": len(spec["labels"]), "scored_labels": len(scored(spec)),
            "her_failures": sum(label["verdict"] == "fail" for label in scored(spec)),
            "pairs_for_the_judge": len(pairs(spec)),
            "recorded": [score_recorded(spec, r) for r in recorded_outputs(recorded_dir)]}
