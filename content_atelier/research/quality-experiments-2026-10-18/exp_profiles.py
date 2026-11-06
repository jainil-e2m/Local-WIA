"""E.B21 smoke check: strategist profile v4 against v5 on development Weeks 1 and 2.

Both prompts are built by the backend itself (angle_profiles.strategist_angle_prompt with knowledge base v2 at the
strategist stage), so the comparison is of the product's own requests. Every call goes through runner.call: the
product's provider module (S.B1 routing) under an active run plan (E.B1).

The judge is the calibrated configuration from plan section 1.8 (T1, J2): Claude Sonnet 5.5 with the knowledge base
and the export's "how Whitney edits" pack, on top of exp_judge's pairwise rubric. Each week is judged in both orders.

Usage:
  python exp_profiles.py generate <v4|v5> <week1|week2> [--dry] [--est=0.3]
  python exp_profiles.py judge <week1|week2> <X run> <Y run> [--dry] [--est=0.08]
  python exp_profiles.py summary
"""
import json, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import runner  # noqa: E402  (puts backend/ on sys.path)
import exp_judge  # noqa: E402
from backend_pipeline.angle_profiles import (STRATEGIST_V4_PROFILE, STRATEGIST_V5_PROFILE, card_contract,  # noqa: E402
                                             card_schema, resolve_card_references, scene_references,
                                             strategist_angle_prompt)
from backend_pipeline.config import BACKEND_ROOT, PROJECT_ROOT  # noqa: E402
from backend_pipeline.knowledge_base import load_knowledge_base  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
ROOT = pathlib.Path(__file__).parent
MODEL, JUDGE = "openai/gpt-6.1-sol", "anthropic/claude-sonnet-5.5"
PROFILES = {"v4": STRATEGIST_V4_PROFILE, "v5": STRATEGIST_V5_PROFILE}
EXPORT = PROJECT_ROOT / "research" / "chatgpt-export-2026-10-18" / "data"
FILES = {"w2_m1_buying_research": "Ads Strategy Call _ The Penny's transcript",
         "w2_m2_tour_followup": "Carmen Cruickshank's Personal Meeting Room's transcript (1)",
         "w2_m3_clicks_no_conversions": "Carmen Cruickshank's Personal Meeting Room's transcript",
         "w2_m4_chat_widget": "GHL AI chat widget Review's transcript",
         "w2_m5_prospect_audit": "Whitney Hodges's Personal Meeting Room's transcript"}


def seconds(stamp):
    h, m, s = (int(x) for x in stamp.split(":"))
    return h * 3600 + m * 60 + s


def packet(week):
    """The harness's excerpt moments as the backend's moment packet: speaker turns, no extractor interpretation."""
    out = []
    for m in json.loads((ROOT / "sources" / f"{week}.json").read_text(encoding="utf-8")):
        source = FILES.get(m["moment_id"], f"Week 1 recording {m['meeting'][-1]}")
        out.append({"moment_id": m["moment_id"], "source_ids": [source], "source_metadata": {}, "sensitivity": "unknown",
                    "qualifications": [], "source_evidence": [{"text": t["text"], "speaker": t["speaker"],
                                                               "start_seconds": seconds(t["t"])} for t in m["turns"]]})
    return out


def kb():
    return load_knowledge_base(BACKEND_ROOT / "knowledge_base", stage="strategist")


def generate(version, week, dry, est):
    profile, moments = PROFILES[version], packet(week)
    system, user = strategist_angle_prompt(moments, kb(), profile)
    schema = card_schema(profile)
    run_id = f"{version.upper()}-{week}-{MODEL.split('/')[-1]}"
    print(run_id, "system chars", len(system), "user chars", len(user), "schema chars", len(json.dumps(schema)),
          "~tokens", (len(system) + len(user) + len(json.dumps(schema))) // 4)
    if dry:
        return
    result = runner.call(run_id, MODEL, system, user, schema, "atelier_output", effort="high", max_tokens=40000,
                         estimate_usd=est)
    output = result.get("output")
    card_contract(profile).model_validate(output)  # The product's own contract check.
    print("contract ok:", len(output["angles"]), "angles,", len(output["internal_insights"]), "internal insights")


def as_text(run_id, label):
    raw = json.loads((ROOT / "runs" / f"{run_id}.json").read_text(encoding="utf-8"))["output"]
    week = run_id.split("-")[1]
    out = resolve_card_references(raw, scene_references(packet(week)))
    lines = [f"### {label}: {len(out['angles'])} public angles, {len(out['internal_insights'])} internal insights"]
    for i, a in enumerate(sorted(out["angles"], key=lambda x: x["rank"]), 1):
        lines.append(f"\n**{label}{i}. {a['title']}**\n- Purpose/type: {a['pillar']} / {a['content_type']}\n"
                     f"- Audience: {a['audience']}\n- Core perspective: {a['core_perspective']}\n"
                     f"- Why it matters: {a['why_it_matters']}\n- WIA contribution shown: {a.get('wia_in_action')}\n"
                     f"- Source moments: {', '.join(a['moment_ids'])}")
        if a.get("series"):
            lines.append(f"- Series: {a['series']}")
        if a.get("verify_before_publishing"):
            lines.append("- Evidence limits: " + " | ".join(a["verify_before_publishing"][:3]))
    if out["internal_insights"]:
        lines.append("\nInternal insights (not for public content):")
        lines += [f"- {x['insight']}" for x in out["internal_insights"]]
    return "\n".join(lines)


def judge_system():
    """(cached prefix, system): the knowledge base and export pack, as T1's J2, then the pairwise rubric."""
    pack = (EXPORT / "pack_rules.md").read_text(encoding="utf-8")
    exemplars = [json.loads(line) for line in (EXPORT / "pack_exemplars.jsonl").read_text(encoding="utf-8").splitlines()
                 if line.strip()][:14]
    prefix = kb().text + "\n\n# HOW WHITNEY EDITS (from her ChatGPT history)\n\n" + pack
    return prefix, (exp_judge.SYSTEM + "\n\nExamples of copy Whitney wrote or approved:\n\n"
                    + "\n\n".join(f"[{e['channel']}, {e['date']}] {e['text']}" for e in exemplars))


def judge(week, x, y, dry, est):
    user = ("Call excerpts both systems worked from (WIA team: Whitney Hodges (founder), Carmen Cruickshank, Fallon Looney, "
            "Danielle McGinnis, Gisselle; everyone else is a client, prospect or student):\n\n" + exp_judge.excerpts(week)
            + (("\n\n# Whitney's own alternative angles for these same excerpts (her reference for what good looks like)\n"
                + exp_judge.P("whitney_alternatives_w1.md")) if week == "week1" else "")
            + "\n\n# Set X\n\n" + as_text(x, "X") + "\n\n# Set Y\n\n" + as_text(y, "Y"))
    prefix, system = judge_system()
    run_id = f"JP-{JUDGE.split('/')[-1]}-X_{x}-Y_{y}"
    print(run_id, "prefix chars", len(prefix), "system chars", len(system), "user chars", len(user))
    if not dry:
        runner.call(run_id, JUDGE, system, user, exp_judge.SCHEMA, "PairwiseJudgment", effort="medium",
                    max_tokens=16000, estimate_usd=est, cache_prefix=prefix)


def summary():
    rows = []
    for path in sorted((ROOT / "runs").glob("JP-*.json")):
        out = json.loads(path.read_text(encoding="utf-8"))["output"]
        x, y = path.stem.split("-X_")[1].split("-Y_")
        winner = {"X": x, "Y": y}.get(out["overall_preference"], "tie")
        rows.append({"judgment": path.stem, "preferred": winner, "rating": out["estimated_whitney_rating"],
                     "criteria": {c["criterion"]: {"X": x, "Y": y}.get(c["better"], "tie") for c in out["criteria"]},
                     "factual_problems": len(out["factual_problems"])})
    print(json.dumps(rows, indent=1))


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry = "--dry" in sys.argv
    est = float(next((a.split("=")[1] for a in sys.argv if a.startswith("--est=")), "0.3"))
    if args[0] == "generate":
        generate(args[1], args[2], dry, est)
    elif args[0] == "judge":
        judge(args[1], args[2], args[3], dry, est)
    else:
        summary()
