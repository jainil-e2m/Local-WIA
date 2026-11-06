"""Upgrade synthetic mechanics fixtures, not model outputs or editorial evidence."""
import copy


def strategic_angle(old):
    q = old["quality"]
    return {
        "local_key": old["local_key"], "title": old["title"],
        "content_opportunity": old["argument"], "strategic_purpose": "WARM", "content_type": "education",
        "strategic_rationale": "Synthetic opportunity for a pipeline mechanics test.",
        "audience": old["audience"], "core_perspective": old["argument"], "tension": old["tension"],
        "wia_expertise_in_action": old["mechanism"], "service_relevance": None,
        "reader_decision": old["reader_decision"], "evidence_readiness": "supported",
        "research_questions": [], "selection_reason": "Synthetic mechanics fixture, not founder-fit evidence.",
        "moment_ids": old["moment_ids"], "source_assertions": old["source_assertions"],
        "inference": old["inference"], "qualifiers": old["qualifiers"], "risks": old["risks"],
        "quality": {"grounding": q["grounding"], "strategic_fit": q["editorial_usefulness"],
            "distinctiveness": q["specificity"], "audience_resonance": q["audience_fit"],
            "source_strength": q["source_relevance"], "reasons": q["reasons"]},
    }


def strategic_output(output, schema):
    if not schema.get("title", "").startswith("Strategic"):
        return output
    output = copy.deepcopy(output)
    for moment in output.get("moments", []):
        moment["discovery"] = {
            "lenses": ["audience_insight", "broader_principle"], "destination": "public_opportunity",
            "wia_contribution": None, "attention_reason": "The synthetic exchange raises a buyer-understanding concern.",
            "research_questions": [],
        }
    if "angles" in output:
        output["angles"] = [strategic_angle(a) if "core_perspective" not in a else a for a in output["angles"]]
        output.setdefault("internal_insights", [])
    return output
