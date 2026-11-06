import json, sys, re, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import runner
sys.stdout.reconfigure(encoding="utf-8")
ROOT = pathlib.Path(__file__).parent
TPL = pathlib.Path(__file__).resolve().parents[2] / "backend" / "backend_pipeline" / "prompt_templates"
FILES = {"w2_m1_buying_research": "Ads Strategy Call _ The Penny's transcript",
         "w2_m2_tour_followup": "Carmen Cruickshank's Personal Meeting Room's transcript (1)",
         "w2_m3_clicks_no_conversions": "Carmen Cruickshank's Personal Meeting Room's transcript",
         "w2_m4_chat_widget": "GHL AI chat widget Review's transcript",
         "w2_m5_prospect_audit": "Whitney Hodges's Personal Meeting Room's transcript"}
def load(n): return (TPL / n).read_text(encoding="utf-8")
def moments(week):
    ms = json.loads((ROOT / "sources" / f"{week}.json").read_text(encoding="utf-8"))
    for m in ms: m["recording"] = FILES.get(m["moment_id"], f"Week 1 recording {m['meeting'][-1]}")
    return ms
REELS = load("reel_approved_examples.md")
KB = (ROOT / "prompts" / "knowledge_base.md").read_text(encoding="utf-8")

def baseline(week, with_kb=False):
    # Exactly prompts._system('angle_generation') and prompts.angle_prompt(), with excerpt-only moment records.
    system = "\n\n".join([load("angle_generation.system.md"), load("wia_strategy.md"), load("editorial_policy.md"),
                          load("reel_editorial.md"), load("reel_calibration.md")])
    if with_kb: system += "\n\n" + KB
    packet = [{"moment_id": m["moment_id"], "source_ids": [m["recording"]],
               "source_evidence": [{"span_id": f"{m['moment_id']}.t{i:03d}", "speaker": t["speaker"], "start": t["t"], "text": t["text"]}
                                   for i, t in enumerate(m["turns"])],
               "speaker_identity_status": "unverified_labels"} for m in moments(week)]
    user = re.sub(r"\{\{([A-Z_]+)\}\}", lambda x: json.dumps({"MOMENT_PACKET": packet, "PRIOR_SIGNATURES": []}[x[1]], ensure_ascii=False),
                  load("angle_generation.user.md"))
    user += "\n\nExisting approved Reel examples: taste and known-content context only; not current source evidence:\n" + REELS
    schema = json.loads((ROOT / "prompts" / "strategic_angle_schema.json").read_text(encoding="utf-8"))
    return system, user, schema, "StrategicAngleResponse"

def proposed(week):
    system = (ROOT / "prompts" / "proposed_angle_system.md").read_text(encoding="utf-8") + "\n\n" + KB
    lines = []
    for m in moments(week):
        lines.append(f"## Moment {m['moment_id']} (recording: {m['recording']})")
        lines.append("Selected turns; dialogue between non-adjacent timestamps is omitted.")
        lines += [f"[{t['t']}] {t['speaker']}: {t['text']}" for t in m["turns"]]
        lines.append("")
    user = ("This week's call moments:\n\n" + "\n".join(lines) +
            "\n\nWhitney's published Reel scripts, for voice and to avoid repeating existing content (not evidence about this week's calls):\n\n" + REELS)
    schema = json.loads((ROOT / "prompts" / "proposed_schema.json").read_text(encoding="utf-8"))
    return system, user, schema, "WeeklyAngles"

if __name__ == "__main__":
    cond, week, model = sys.argv[1], sys.argv[2], sys.argv[3]
    dry = "--dry" in sys.argv
    est = float(next((a.split("=")[1] for a in sys.argv if a.startswith("--est=")), "0.4"))
    s, u, sc, name = {"B0": lambda: baseline(week), "B1": lambda: baseline(week, True), "P1": lambda: proposed(week)}[cond]()
    tag = model.split("/")[-1]
    run_id = f"{cond}-{week}-{tag}"
    print(run_id, "system chars", len(s), "user chars", len(u), "schema chars", len(json.dumps(sc)), "~tokens", (len(s)+len(u)+len(json.dumps(sc)))//4)
    if not dry:
        runner.call(run_id, model, s, u, sc, name, effort="high", max_tokens=40000, estimate_usd=est)
