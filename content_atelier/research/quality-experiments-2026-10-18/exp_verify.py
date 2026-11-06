"""E.B10 evidence: the verification step over the 18 October outputs the judges reviewed.

Deterministic pass (free): python exp_verify.py
Model pass (paid; a different family than each generator, under a run plan and S.B1 routing):
  python exp_verify.py --model [--dry]
"""
import json, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import runner  # noqa: E402  (puts backend/ on sys.path)
from backend_pipeline.config import BACKEND_ROOT  # noqa: E402
from backend_pipeline.cycle import verification as v  # noqa: E402
from backend_pipeline.knowledge_base import load_knowledge_base, team_roster  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
ROOT = pathlib.Path(__file__).parent
KB = BACKEND_ROOT / "knowledge_base"
OUTPUTS = ["P1-week1-claude-sonnet-5", "P1-week2-claude-sonnet-5", "P1-week1-gpt-6.1-sol", "P1-week2-gpt-6.1-sol",
           "B0-week1-gpt-6.1-sol", "B0-week2-gpt-6.1-sol"]
# A verifier from another family than the generator (E.B10).
VERIFIER = {"claude-sonnet-5": "openai/gpt-6.1-sol", "gpt-6.1-sol": "anthropic/claude-sonnet-5.5"}


def seconds(stamp):
    h, m, s = (int(x) for x in stamp.split(":"))
    return h * 3600 + m * 60 + s


def scenes(week):
    data = json.loads((ROOT / "sources" / f"{week}.json").read_text(encoding="utf-8"))
    return {m["moment_id"]: [{"text": t["text"], "speaker": t["speaker"], "start_seconds": seconds(t["t"])} for t in m["turns"]]
            for m in data}


def cards(run_id):
    """Card-shaped views of an output: P1 is already a card; B0's strategic angle maps field by field."""
    out = json.loads((ROOT / "runs" / f"{run_id}.json").read_text(encoding="utf-8"))["output"]
    result = []
    for i, a in enumerate(out["angles"], 1):
        if "core_perspective" in a and "pillar" in a:
            result.append(a)
        else:
            result.append({"rank": i, "title": a["title"], "pillar": a["strategic_purpose"], "content_type": a["content_type"],
                           "audience": a["audience"], "core_perspective": a["core_perspective"], "why_it_matters": a["tension"],
                           "wia_in_action": a.get("wia_expertise_in_action"), "offer_connection": a.get("service_relevance"),
                           "moment_ids": a["moment_ids"], "evidence_points": a.get("source_assertions", [])})
    return result


def deterministic(run_id):
    week = run_id.split("-")[1]
    roster, rules = team_roster(KB), v.load_rules(KB)
    found = scenes(week)
    return [(c, v.verify_card(c, found, roster, rules)) for c in cards(run_id)], found


def model_pass(run_id, dry):
    pairs, found = deterministic(run_id)
    generator = run_id.split("-", 2)[2]
    model = VERIFIER[generator]
    kb = load_knowledge_base(KB, stage="verifier").text
    system, user, refs = v.model_pass_prompt([c for c, _ in pairs], found, [ledger for _, ledger in pairs], kb)
    rid = f"VER-{model.split('/')[-1]}-{run_id}"
    print(rid, "system chars", len(system), "user chars", len(user))
    if dry:
        return None
    result = runner.call(rid, model, system, user, v.MODEL_PASS_SCHEMA, "CardVerification", effort="medium",
                         max_tokens=16000, estimate_usd=0.12)["output"]
    by_rank = {item["rank"]: item for item in result["cards"]}
    return [(c, v.merge_model_pass(ledger, by_rank.get(c["rank"], {}), refs, model)) for c, ledger in pairs]


def show(run_id, pairs):
    print(f"\n=== {run_id}")
    for card, ledger in pairs:
        print(f"  #{card['rank']} {card['title'][:70]} :: {ledger['readiness']}"
              + (f" :: critic {ledger['critic']}" if ledger.get("critic") else ""))
        for f in ledger["flags"]:
            if f["severity"] != v.STYLE:
                print(f"     [{f['severity']}] {f['kind']} ({f['source']}, {f['field']}): {f['message'][:150]}")


if __name__ == "__main__":
    model, dry = "--model" in sys.argv, "--dry" in sys.argv
    for run_id in OUTPUTS:
        pairs = model_pass(run_id, dry) if model else deterministic(run_id)[0]
        if pairs:
            show(run_id, pairs)
