import json, pathlib
ROOT = pathlib.Path(__file__).parent
def load(run_id): return json.loads((ROOT / "runs" / f"{run_id}.json").read_text(encoding="utf-8"))
def cards(run_id, limits=True):
    o = load(run_id)["output"]; out = []
    if "angles" in o and o["angles"] and "core_perspective" in o["angles"][0] and "strategic_purpose" in o["angles"][0]:
        for a in o["angles"]:
            out.append({"title": a["title"], "purpose": f'{a["strategic_purpose"]} / {a["content_type"]}', "audience": a["audience"],
                        "core_perspective": a["core_perspective"], "why_it_matters": a["tension"],
                        "wia_contribution": a.get("wia_expertise_in_action"), "moments": a["moment_ids"],
                        "limits": (a.get("qualifiers") or [])[:3]})
        internal = [i["insight"] for i in o.get("internal_insights", [])]
    else:
        for a in sorted(o["angles"], key=lambda x: x["rank"]):
            out.append({"title": a["title"], "purpose": f'{a["pillar"]} / {a["content_type"]}', "audience": a["audience"],
                        "core_perspective": a["core_perspective"], "why_it_matters": a["why_it_matters"],
                        "wia_contribution": a.get("wia_in_action"), "moments": a["moment_ids"],
                        "limits": (a.get("verify_before_publishing") or [])[:3]})
        internal = [i["insight"] for i in o.get("internal_insights", [])]
    return out, internal
def as_text(run_id, label):
    cs, internal = cards(run_id)
    lines = [f"### {label}: {len(cs)} public angles, {len(internal)} internal insights"]
    for i, c in enumerate(cs, 1):
        lines.append(f"\n**{label}{i}. {c['title']}**\n- Purpose/type: {c['purpose']}\n- Audience: {c['audience']}\n- Core perspective: {c['core_perspective']}\n- Why it matters: {c['why_it_matters']}\n- WIA contribution shown: {c['wia_contribution']}\n- Source moments: {', '.join(c['moments'])}")
        if c["limits"]: lines.append("- Evidence limits: " + " | ".join(c["limits"]))
    if internal:
        lines.append("\nInternal insights (not for public content):")
        lines += [f"- {x}" for x in internal]
    return "\n".join(lines)
