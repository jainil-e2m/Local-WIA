"""Meaningful source-boundary checks before paid handbook calibration."""
import re

import pytest

from experiments.handbook_testing import (
    BACKEND,
    active_system,
    full_handbook_angle_system,
    read,
    validate_finding,
    validate_moment,
)


def refs():
    return {f"m1.t{i+1:04d}": {"ref": f"m1.t{i+1:04d}", "meeting_ref": "m1", "ordinal": i,
        "speaker": "Client" if i == 0 else "Team", "text": "Exact source text."} for i in range(4)} | {
        "m2.t0001": {"ref": "m2.t0001", "meeting_ref": "m2", "ordinal": 0, "speaker": "Other", "text": "Other meeting."}}


def moment():
    return {"local_key": "mkt1", "meeting_ref": "m1", "anchor_refs": ["m1.t0001", "m1.t0002"],
        "context_regions": [{"first_ref": "m1.t0001", "last_ref": "m1.t0003"}],
        "situation": "Client asks about fit.", "source_proposition": "Team discusses fit.",
        "assertions": [{"claim": "Client asks a question.", "state": "spoken_view", "source_refs": ["m1.t0001"], "knowledge_refs": []}],
        "contributions": [{"speaker_label": "Team", "contribution": "Asks a diagnostic question.", "source_refs": ["m1.t0002"]}],
        "lenses": ["process_collaboration"], "strategic_significance": "Shows client-informed judgment.",
        "audience_relevance": "Owners evaluating agency support.", "possible_uses": ["public_candidate"],
        "retrieval_needs": [], "claim_boundaries": ["No result reported."], "shortlist_reason": "Specific process exchange."}


def angle():
    return {"local_key": "a1", "rank": 1, "disposition": "SELECT", "title": "Client knowledge changes the recommendation",
        "central_point": "Client context informs advertising judgment.", "why_worthwhile": "Makes decision work visible.",
        "audience": "Wedding business owners", "intended_shift": "Value collaboration in campaign planning.",
        "primary_pillar": "WARM", "content_type": "process", "strategic_rationale": "Builds trust through a specific decision.",
        "source_demonstration": "Team asks a question.", "moment_keys": ["mkt1"], "evidence_refs": ["m1.t0001", "m1.t0002"],
        "claims": [{"claim": "Team asks a question.", "state": "spoken_view", "source_refs": ["m1.t0002"], "knowledge_refs": []}],
        "claim_boundaries": ["No outcome claim."], "development_direction": "Show the question and response.",
        "tension": None, "offer_connection": None, "possible_format": None,
        "judgments": {key: {"value": 4, "reason": "Supported specific process."} for key in
            ["audience_relevance", "strategic_value_brand_fit", "distinctiveness", "appropriate_depth", "voice_framing", "source_support"]},
        "nearest_alternative": {"candidate_key": None, "central_point": None, "comparison_reason": "No meaningful comparator in the fixture."}}


def test_reviewed_prompts_exact_and_previous_comments_inactive():
    draft = (BACKEND.parent / "research/2026-10-13-handbook-system-prompts-proposal.md").read_text(encoding="utf-8")
    blocks = re.findall(r"```text\n(.*?)\n```", draft, re.DOTALL)
    assert [active_system(stage) for stage in ["moment_extraction", "angle_generation"]] == blocks
    assert "PREVIOUS SYSTEM PROMPT" not in active_system("angle_generation")


def test_context_is_hydrated_including_unselected_turns():
    _, context = validate_moment(moment(), refs())
    assert context == ["m1.t0001", "m1.t0002", "m1.t0003"]


@pytest.mark.parametrize("change", ["unknown", "cross_meeting", "wrong_speaker", "anchor_outside", "overlap", "interpretation_as_fact"])
def test_invalid_source_binding_is_rejected(change):
    data = moment()
    if change == "unknown": data["anchor_refs"][0] = "m1.t9999"
    if change == "cross_meeting": data["context_regions"][0]["last_ref"] = "m2.t0001"
    if change == "wrong_speaker": data["contributions"][0]["speaker_label"] = "Whitney"
    if change == "anchor_outside": data["anchor_refs"] = ["m1.t0004"]
    if change == "overlap": data["context_regions"].append({"first_ref": "m1.t0003", "last_ref": "m1.t0004"})
    if change == "interpretation_as_fact": data["assertions"][0]["state"] = "editorial_inference"
    with pytest.raises(ValueError): validate_moment(data, refs())


def test_separate_context_regions_remain_separate():
    data = moment()
    data["anchor_refs"] = ["m1.t0001", "m1.t0004"]
    data["context_regions"] = [{"first_ref": "m1.t0001", "last_ref": "m1.t0002"}, {"first_ref": "m1.t0004", "last_ref": "m1.t0004"}]
    assert validate_moment(data, refs())[1] == ["m1.t0001", "m1.t0002", "m1.t0004"]


def validate_angle(data):
    m, context = validate_moment(moment(), refs())
    return validate_finding(data, {"mkt1": m}, {"mkt1": context}, refs(), {"H001"}, True)


def test_process_angle_can_have_no_tension_or_offer():
    data = validate_angle(angle())
    assert data["tension"] is None and data["offer_connection"] is None


@pytest.mark.parametrize("change", ["unknown_moment", "outside_context", "knowledge_as_case_fact", "partial_support", "weak_dimension", "self_alternative"])
def test_unsupported_or_ineligible_select_is_rejected(change):
    data = angle()
    if change == "unknown_moment": data["moment_keys"] = ["unknown"]
    if change == "outside_context": data["claims"][0]["source_refs"] = ["m1.t0004"]
    if change == "knowledge_as_case_fact": data["claims"][0]["knowledge_refs"] = ["H001"]
    if change == "partial_support": data["judgments"]["source_support"]["value"] = 3
    if change == "weak_dimension": data["judgments"]["voice_framing"]["value"] = 2
    if change == "self_alternative": data["nearest_alternative"]["candidate_key"] = data["local_key"]
    with pytest.raises(ValueError): validate_angle(data)


@pytest.mark.parametrize("disposition", ["HOLD", "INTERNAL", "REFRAME"])
def test_other_dispositions_require_actionable_use(disposition):
    data = {"local_key": "other", "disposition": disposition, "moment_keys": ["mkt1"], "evidence_refs": ["m1.t0001"],
        "summary": "Useful incomplete insight.", "disposition_reason": "Source gap.", "proposed_reframe": None,
        "retrieval_needs": [], "internal_use": None}
    with pytest.raises(ValueError): validate_finding(data, {"mkt1": moment()}, {"mkt1": ["m1.t0001"]}, refs(), set(), False)


def test_content_only_handbook_preserves_all_substantive_source_content():
    source = read(BACKEND.parent / "research/sources/wia-handbook-2026-10-13/source-extract.json")
    text = (BACKEND / "backend_pipeline/prompt_templates/handbook_v2/wia_content_system_handbook.md").read_text(encoding="utf-8")
    assert not re.search(r"\b(?:B\d{3}|H\d{3})\b|SHA256|<a\s|<!--|Version\s+\d", text)
    assert "Prepared for Whitney Hodges | 13 October 2026" not in text
    assert sum(line.startswith("| ---") for line in text.splitlines()) == 11
    for block in source["blocks"]:
        if block["kind"] == "p" and block.get("text") and block["id"] != "B002":
            if block.get("links"):
                assert all(link["text"] in text and link["target"] in text for link in block["links"])
            else:
                assert block["text"] in text
        elif block["kind"] == "tbl":
            for row in block["rows"]:
                for cell in row["cells"]:
                    expected = re.sub(r"\s+Version\s+\d+(?:\.\d+)*", "", cell).replace("|", "\\|").replace("\n", " ")
                    assert expected in text


def test_full_reference_system_contains_complete_content_and_consistent_history_flags():
    profile = BACKEND / "backend_pipeline/prompt_templates/handbook_v2"
    system = full_handbook_angle_system({"validated_moments": 2, "history_coverage": "one related email"})
    assert (profile / "wia_content_system_handbook.md").read_text(encoding="utf-8").strip() in system
    assert (profile / "angle_generation_feedback.md").read_text(encoding="utf-8").strip() in system
    assert "reference_version" not in system and "source_sha256" not in system
    assert "H001–H060" not in system and "PREVIOUS SYSTEM PROMPT PRESERVED" not in system
    assert "history_check must be checked_supplied_history" in system
    assert "history_check and plan_check must be not_supplied" not in system
    assert "plan_check must be not_supplied" in system
    assert "not a complete published-history check" in system


def test_new_knowledge_reference_names_are_valid_with_actual_source_support():
    data = angle()
    data["claims"].append({"claim": "Client expertise should inform advertising decisions.", "state": "brand_perspective",
        "source_refs": [], "knowledge_refs": ["handbook"]})
    m, context = validate_moment(moment(), refs())
    assert validate_finding(data, {"mkt1": m}, {"mkt1": context}, refs(), {"handbook", "latest_feedback"}, True)
