"""E.B23 offline: brief contract v3, the claims ledger built after writing, the limited repair, writer v4 and the settings
that select them. No database, no HTTP, no model call."""
from __future__ import annotations

import copy
import json
import sys
from types import SimpleNamespace

import pytest

from backend_pipeline import settings_store
from backend_pipeline.briefs import ledger_v3, runtime
from backend_pipeline.briefs.contracts import Dossier
from backend_pipeline.briefs.contracts_v2 import SCHEMA_V2
from backend_pipeline.briefs.contracts_v3 import SCHEMA_V3, BriefDocumentV3, BriefWriteV3, writer_part, writer_schema_v3
from backend_pipeline.briefs.validation_v2 import repairable
from backend_pipeline.briefs.validation_v3 import checks_v3, hedging_added, ledger_body, repair_packet
from backend_pipeline.config import BACKEND_ROOT, PROJECT_ROOT, Settings
from backend_pipeline.cycle.verification import load_rules
from backend_pipeline.knowledge_base import team_roster
from backend_pipeline.storage_config import StorageSettings
from backend_pipeline.tests.brief_v3_fixtures import v3_body

CARD = {"title": "Why we ask about follow-up first", "core_perspective": "Follow-up shapes lead quality.", "pillar": "WARM",
        "content_type": "behind_the_scenes", "audience": "Venue owners", "offer_connection": None}
def _evidence(evidence_id, speaker, at_ms, role, said):
    # A synthetic call, built here so the file holds no transcript-shaped JSON (R48, test_client_material_guard).
    return {"evidence_id": evidence_id, "transcript_id": "t", "excerpt": f"{speaker}: {said}", "title": "Call",
            "speaker": speaker, "start_ms": at_ms, "role": role, "moment_ids": ["m1"]}


EVIDENCE = [_evidence("ev_a", "Carmen Cruickshank", 4000, "anchor", "How do you reply to a new inquiry today?"),
            _evidence("ev_b", "Shannon Lee", 9000, "support", "We moved to 45 inquiries a month after we changed it."),
            _evidence("ev_c", "Carmen Cruickshank", 12000, "support",
                      "What I see in accounts like this is that the first reply sets the tone for the whole booking.")]
BELIEFS = {"owner": "Whitney Hodges", "statements": ["ads don't create demand they capture it or amplify it"]}


def dossier(cta=None):
    angle = {"angle_id": "angle_1", "week_id": "w", "approved_hash": "h", "cta": cta or {"choice": "decide_in_development"},
             "body": {"card": CARD, "title": CARD["title"], "argument": CARD["core_perspective"], "audience": "Venue owners"}}
    return Dossier(angle=angle, evidence=EVIDENCE, prior=[], queries=[], coverage={}, gaps=[], audit=[], brand={"hash": "b"})


def provenance():
    return {"pinned_inputs": {}, "knowledge_base_keys": ["process_catalogue", "offer_sheet", "belief_statements"],
            "roster": team_roster(BACKEND_ROOT / "knowledge_base"), "beliefs": BELIEFS}


def packet():
    return {"approved_angle": {"title": CARD["title"], "core_perspective": CARD["core_perspective"]}, "card": CARD,
            "evidence": [{k: e[k] for k in ("speaker", "start_ms", "excerpt", "role")} for e in EVIDENCE]}


def document(writer=None, *, verify=None, previous=None, person_fields=frozenset()):
    writer = writer or v3_body(packet())
    body, record = ledger_body(writer, EVIDENCE, provenance(), verify=verify, previous=previous, person_fields=person_fields)
    header = {"schema_version": SCHEMA_V3, "angle_id": "angle_1", "angle_hash": "h", "purpose": "WARM", "content_type": "behind_the_scenes",
              "audience": "Venue owners", "intended_shift": body["intended_shift"], "point_of_view": body["point_of_view"],
              "cta": {**body["cta"], "chosen_by": "writer"}, "channels": ["reel", "carousel", "email", "caption"], "pinned_inputs": {}}
    return {"header": header, "body": body}, record


def check(doc):
    return checks_v3(doc, dossier(), provenance(), None, load_rules(BACKEND_ROOT / "knowledge_base"))


def blocking(findings):
    return [f["message"] for f in findings if f["severity"] == "blocking"]


def warnings(findings):
    return [f["message"] for f in findings if f["severity"] == "warning"]


def claim_for(doc, text):
    return next(c for c in doc["body"]["claims"] if text in c["text"])


def walk_keys(value):
    if isinstance(value, dict):
        for k, v in value.items():
            yield k
            yield from walk_keys(v)
    elif isinstance(value, list):
        for v in value:
            yield from walk_keys(v)


# The contract ------------------------------------------------------------------------------------------------------

def test_the_writer_schema_has_no_citations_an_optional_decision_and_finished_caption_and_email():
    schema = writer_schema_v3(["reel", "carousel", "email", "caption"])
    keys = set(walk_keys(schema))
    assert "evidence_ids" not in keys and "claims" not in schema["properties"] and "evidence" not in schema["properties"]
    defs = schema["$defs"]
    assert defs["IntendedShiftV3"]["properties"]["do"]["anyOf"][1] == {"type": "null"}
    assert set(defs["CaptionPlanV3"]["properties"]) == {"hook", "body", "ending"}, "the caption has a body, not `adds`"
    assert set(defs["EmailPlanV3"]["properties"]) == {"subject_options", "preview", "opening", "body", "ending"}, "no `argument`"
    assert "script" in defs["ReelPlanV3"]["properties"]
    assert defs["CaptionPlanV3"]["properties"]["body"]["description"].startswith("Copy:")
    assert defs["ReelPlanV3"]["properties"]["beats"]["description"].startswith("Direction:")
    narrowed = writer_schema_v3(["reel", "email"])["$defs"]["FormatPlanV3"]["properties"]
    assert narrowed["carousel"]["type"] == "null" and narrowed["caption"]["type"] == "null" and "anyOf" in narrowed["email"]
    BriefWriteV3.model_validate(v3_body(packet()))
    with pytest.raises(ValueError):
        BriefWriteV3.model_validate({**v3_body(packet()), "claims": []}), "the writer returns no claims"


def test_a_v3_document_validates_and_v2_documents_are_not_v3():
    doc, _ = document()
    BriefDocumentV3.model_validate(doc)
    assert writer_part(doc["body"]) == v3_body(packet())


# The ledger --------------------------------------------------------------------------------------------------------

def test_the_rules_bind_a_repeated_turn_a_quote_a_figure_and_a_belief_and_reject_what_the_call_lacks():
    writer = v3_body(packet())
    writer["wia_perspective"] = ('Our strategist put it plainly: "How do you reply to a new inquiry today?" '
                                 'One owner moved to 45 inquiries a month. Another doubled to 90 tours. '
                                 'As Whitney says, "Ads don\'t create demand. They capture it, or amplify it." '
                                 "The first reply sets the tone for the whole booking, our strategist says.")
    doc, _ = document(writer)
    scene = claim_for(doc, "our strategist asked")
    assert scene["status"] == "bound" and scene["settled_by"] == "deterministic" and "ev_a" in scene["evidence_ids"]
    quoted = claim_for(doc, "Our strategist put it plainly")
    assert quoted["quote"] == "How do you reply to a new inquiry today?" and quoted["public_quote"] and quoted["evidence_ids"] == ["ev_a"]
    figure = claim_for(doc, "45 inquiries")
    assert figure["status"] == "bound" and figure["numeric_facts"][0]["evidence_id"] == "ev_b"
    assert figure["numeric_facts"][0]["source_quote"] in EVIDENCE[1]["excerpt"]
    invented = claim_for(doc, "90 tours")
    assert invented["status"] == "unsupported" and '"90 tours", which is not in the call' in invented["note"]
    experience = claim_for(doc, "sets the tone")
    assert experience["claim_class"] == "attributed_experience" and experience["evidence_ids"] == ["ev_c"], "E.B26"
    belief = claim_for(doc, "As Whitney says")
    assert belief["claim_class"] == "general_approach" and belief["knowledge_base_document"] == "belief_statements"
    assert {r["evidence_id"] for r in doc["body"]["evidence"]} == {"ev_a", "ev_b", "ev_c"}
    found = check(doc)
    assert any("90 tours" in m for m in blocking(found)) and any("public quotation" in m for m in blocking(found))
    assert not any("numeric fact" in m or "number in the public narrative" in m for m in blocking(found)), \
        "a figure the call states is bound, with its numeric fact"
    assert any('"45 inquiries" is a client figure' in m for m in blocking(found)), "and still needs the client's permission"


def test_an_unmatched_quotation_goes_to_the_verifier_and_a_direction_s_word_count_is_no_claim():
    """The E.B22 brief for 1f79f6d4 put a question in quotation marks ('Should we change anything yet?') and a word count in
    a Reel's job: neither blocks a v3 brief by rule; the verifier decides whether a quotation is invented."""
    writer = v3_body(packet())
    writer["format_plan"]["email"]["body"] = "That gives the question 'Should we change anything yet?' a more useful shape."
    writer["format_plan"]["reels"][0]["job"] = "Show the move. New talking-head recording, approximately 125 to 140 words."
    doc, _ = document(writer)
    found = check(doc)
    assert claim_for(doc, "Should we change")["status"] == "unchecked", "without the verifier, a person checks it"
    assert not any("Should we change" in m or "125" in m or "140" in m for m in blocking(found)), blocking(found)
    verify = fake_verifier({"Should we change": {"verdict": "unsupported", "claim_class": "particular_interaction", "evidence_refs": [],
                                                 "knowledge_base_document": None,
                                                 "flag": {"kind": "misattribution", "severity": "block", "message": "An invented quote"}}})
    assert any("Should we change" in m and "An invented quote" in m for m in blocking(check(document(writer, verify=verify)[0])))


def test_questions_asks_greetings_and_sign_offs_are_not_statements():
    texts = [s["text"] for s in ledger_v3.statements(v3_body(packet()))]
    for absent in ("What happens in the hour after someone inquires?", "Reply and tell me what your first reply says.",
                   "Save this for your next review.", "Talk soon,", "Whitney"):
        assert absent not in texts, absent
    assert "We look at what happens after the inquiry before we change a single ad." in texts


def fake_verifier(verdicts):
    def verify(open_statements):
        packet, refs = ledger_v3.verifier_packet(open_statements, EVIDENCE, provenance()["roster"], packet_angle())
        assert "ev_a" not in json.dumps(packet), "turns are referred to as E1, E2, ... only"
        out = [{"id": s["id"], **next((v for marker, v in verdicts.items() if marker in s["text"]),
                                      {"verdict": "view", "claim_class": "general_approach", "evidence_refs": [],
                                       "knowledge_base_document": None, "flag": None})} for s in open_statements]
        return {"statements": out}, refs, "anthropic/claude-sonnet-5.5"
    return verify


def packet_angle():
    return {"title": CARD["title"], "core_perspective": CARD["core_perspective"]}


def test_the_verifier_settles_the_rest_and_never_blocks_a_team_member_s_attributed_experience():
    writer = v3_body(packet())
    writer["wia_perspective"] = ("Our strategist sees this pattern across accounts like these. "
                                 "We changed the reply for every client last year. We look at follow-up before ads.")
    verify = fake_verifier({
        "Our strategist sees": {"verdict": "attributed_experience", "claim_class": "prevalence", "evidence_refs": ["E3"],
                                "knowledge_base_document": None,
                                "flag": {"kind": "frequency", "severity": "block", "message": "Generalises from one account"}},
        "We changed the reply": {"verdict": "unsupported", "claim_class": "particular_interaction", "evidence_refs": [],
                                 "knowledge_base_document": None,
                                 "flag": {"kind": "tense", "severity": "block", "message": "The call only plans the change"}},
        "We look at follow-up": {"verdict": "view", "claim_class": "general_approach", "evidence_refs": [],
                                 "knowledge_base_document": "process_catalogue", "flag": None}})
    doc, record = document(writer, verify=verify)
    experience = claim_for(doc, "Our strategist sees")
    assert experience["claim_class"] == "attributed_experience" and experience["evidence_ids"] == ["ev_c"]
    assert experience["flag"]["severity"] == "check", "E.B26: a frequency flag never blocks attributed experience"
    assert claim_for(doc, "We changed the reply")["status"] == "unsupported"
    practice = claim_for(doc, "We look at follow-up")
    assert practice["claim_class"] == "general_approach" and practice["knowledge_base_document"] == "process_catalogue"
    assert record["verifier"] == {"profile": "brief-verification.v1", "model": "anthropic/claude-sonnet-5.5", "status": "run"}
    found = check(doc)
    assert any("We changed the reply" in m and "The call only plans the change" in m for m in blocking(found))
    assert not any("Our strategist sees" in m for m in blocking(found))
    assert any("Generalises from one account" in m for m in warnings(found))
    assert [f for f in repairable(found) if "We changed the reply" in f["message"]], "the repair may fix it"


def test_without_the_verifier_factual_statements_stay_for_a_person_and_views_pass():
    writer = v3_body(packet())
    writer["wia_perspective"] = "The owner told us the replies were slow. We look at follow-up before ads."

    def skipped(_):
        raise ledger_v3.VerifierSkipped("not configured")
    doc, record = document(writer, verify=skipped)
    assert record["verifier"]["status"] == "skipped" and record["verifier"]["reason"] == "not configured"
    assert claim_for(doc, "The owner told us")["status"] == "unchecked"
    assert not [c for c in doc["body"]["claims"] if "We look at follow-up" in c["text"]], "a view is not a claim"
    found = check(doc)
    assert any("Check against the call" in m and "The owner told us" in m for m in warnings(found))
    assert not any("The owner told us" in m for m in blocking(found))


def test_a_rebuild_keeps_verdicts_and_a_person_who_keeps_an_unsupported_line_owns_it():
    writer = v3_body(packet())
    writer["wia_perspective"] = "We changed the reply for every client last year."
    verify = fake_verifier({"We changed the reply": {"verdict": "unsupported", "claim_class": "particular_interaction",
                                                     "evidence_refs": [], "knowledge_base_document": None, "flag": None}})
    doc, _ = document(writer, verify=verify)
    previous = doc["body"]["claims"]
    edited = {**writer, "audience": {**writer["audience"], "who": "Venue owners with a sales team"}}
    again, _ = document(edited, previous=previous, person_fields={"audience"})
    assert claim_for(again, "We changed the reply")["status"] == "unsupported", "an untouched section keeps its verdict"
    kept, _ = document({**writer, "wia_perspective": writer["wia_perspective"]}, previous=previous, person_fields={"wia_perspective"})
    claim = claim_for(kept, "We changed the reply")
    assert claim["status"] == "kept_by_person" and claim["settled_by"] == "person"
    assert not any("We changed the reply" in m for m in blocking(check(kept)))
    assert any("a person kept it" in m for m in warnings(check(kept)))


# Checks ------------------------------------------------------------------------------------------------------------

def test_a_clean_v3_brief_has_only_the_gate_two_items_left():
    doc, _ = document()
    found = check(doc)
    assert sorted(blocking(found)) == sorted(["The CTA is the writer's proposal; a person confirms it (or no explicit ask) at Gate 2",
                                               "Required before-publishing items remain unanswered"])
    assert repairable(found) == []


def test_v3_format_and_copy_checks():
    writer = v3_body(packet())
    writer["format_plan"]["reels"][0]["script"] = None
    writer["format_plan"]["caption"]["body"] = "Credit Jacqueline for the idea. This is not independently verified."
    writer["format_plan"]["email"]["ending"] = "DM us the word ADS."
    writer["format_plan"]["stories"] = {"frames": ["A frame"]}
    found = check(document(writer)[0])
    for expected in ("never a DM", "outside the confirmed channel set"):
        assert any(expected in m for m in blocking(found)), expected
    assert "Reel 1 is a new script without its script" in warnings(found), "missing copy warns; it never sends the brief to repair"
    lint = [f for f in found if f.get("field") == "format_plan.caption.body"]
    assert any("checking language" in f["message"] for f in lint) and any("writing instruction" in f["message"] for f in lint)


def test_a_former_team_member_named_in_the_caption_body_blocks():
    roster = provenance()["roster"]
    former = next((r for r in roster if r["status"] == "former"), None)
    if former is None:
        pytest.skip("the committed roster lists no former team member")
    writer = v3_body(packet())
    writer["format_plan"]["caption"]["body"] = f"{former['aliases'][0]} spotted it first."
    assert any("has left WIA" in m for m in blocking(check(document(writer)[0])))


# Repair ------------------------------------------------------------------------------------------------------------

def test_a_repair_that_adds_claim_boundary_language_to_copy_is_caught_by_the_lint():
    before = v3_body(packet())
    after = copy.deepcopy(before)
    after["wia_perspective"] += " That remains an idea to explore, and the call does not establish it."
    after["format_plan"]["email"]["body"] = "Follow-up is part of the ad, subject to permission."
    assert hedging_added(before, after) == ["the WIA perspective: remains an idea", "the WIA perspective: the call does not establish",
                                            "the email's body: subject to permission"]
    reworded = copy.deepcopy(before)
    reworded["wia_perspective"] = "We read the first reply before we touch an ad."
    assert hedging_added(before, reworded) == [], "removing or rewording is what a repair is for"
    already = copy.deepcopy(before)
    already["wia_perspective"] += " This is not independently verified."
    assert hedging_added(already, already) == [], "only language the repair adds counts"


def test_the_repair_gets_the_writer_s_sections_the_turns_and_the_findings_and_a_template_that_forbids_hedging():
    doc, _ = document()
    sent = repair_packet(doc, dossier(), [{"message": "A finding", "section": "wia_perspective"}], ["reel"])
    assert set(sent["brief"]) == set(BriefWriteV3.model_fields) and "claims" not in sent["brief"]
    assert "evidence_id" not in json.dumps(sent["evidence"]) and sent["findings"] == [{"section": "wia_perspective", "problem": "A finding"}]
    template = runtime.system("brief_repair", SCHEMA_V3, "KB", "v4")
    assert template.startswith("KB") and "Never add a qualifier" in template and "is rejected" in template


# Prompts and settings ----------------------------------------------------------------------------------------------

def test_contract_v3_selects_writer_v4_repair_v4_and_the_verifier_and_shares_plan_and_grade():
    write = runtime.system("brief_write", SCHEMA_V3, "KB", "v4")
    assert write.startswith("KB") and "You do not cite evidence or list claims" in write
    for rule in ("Two kinds of text", "credit \"our team\"", "Quote a belief only in Whitney's own words", "never drop it",
                 "at the strength they said it", "leave `do` null", "write the whole `script`"):
        assert rule in write, rule
    assert "## Claims" not in write and "evidence ID" not in write
    verify = runtime.system("brief_verify", SCHEMA_V3, "KB")
    assert verify.startswith("KB") and "attributed_experience" in verify
    for stage in ("brief_plan", "brief_grade"):
        assert runtime.system(stage, SCHEMA_V3, None, "v4") == runtime.system(stage, SCHEMA_V2, None, "v3")
    assert runtime.system("brief_write", SCHEMA_V2, "KB", "v3") == "KB\n\n" + (
        BACKEND_ROOT / "backend_pipeline" / "prompt_templates" / "brief_write.v3.md").read_text(encoding="utf-8"), "v3 kept for replay"


def test_the_new_templates_pass_the_e_b10_lint():
    sys.path.insert(0, str(PROJECT_ROOT / "research" / "chatgpt-export-2026-10-18"))
    try:
        from lint import lint
    finally:
        sys.path.pop(0)
    templates = BACKEND_ROOT / "backend_pipeline" / "prompt_templates"
    for name in ("brief_write.v4.md", "brief_repair.v4.md", "brief_verify.v1.md"):
        assert [hit for hit in lint((templates / name).read_text(encoding="utf-8")) if hit[0] != "price_in_public_copy"] == [], name


def test_the_contract_and_writer_must_match_and_the_default_is_unchanged():
    assert settings_store.definition("prompts.profile.brief").default == "brief_document_v1"
    assert settings_store.definition("prompts.profile.brief_writer").default == "v2"
    assert "brief_document_v3" in settings_store.definition("prompts.profile.brief").choices
    with pytest.raises(settings_store.SettingError, match="written by writer v4"):
        settings_store.validate_profile({"settings": {"prompts.profile.brief": "brief_document_v3", "prompts.profile.brief_writer": "v3"}})
    with pytest.raises(settings_store.SettingError, match="v2 or v3, not v4"):
        settings_store.validate_profile({"settings": {"prompts.profile.brief": "brief_document_v2", "prompts.profile.brief_writer": "v4"}})
    settings_store.validate_profile({"settings": {"prompts.profile.brief": "brief_document_v3", "prompts.profile.brief_writer": "v4"}})
    from backend_pipeline.briefs.workflow import writer_for
    assert writer_for(StorageSettings(brief_writer="v4"), SCHEMA_V3) == "v4"
    with pytest.raises(ValueError, match="written by writer v4"):
        writer_for(StorageSettings(brief_writer="v3"), SCHEMA_V3)
    assert writer_for(StorageSettings(brief_writer="v4"), SCHEMA_V2, revision="brief_x") == "v3", "a v2 brief's revision keeps v2"


def test_a_v3_run_freezes_its_ledger_and_verifier_in_the_execution_contract(monkeypatch):
    kb = SimpleNamespace(text="# WIA KNOWLEDGE BASE\n\nVoice guide line.", refs=lambda: {"version": "kb-test"})
    monkeypatch.setattr(runtime, "knowledge", lambda worker, run=None, stage="brief": kb)
    worker = SimpleNamespace(models=Settings(), storage=StorageSettings(brief_model="openai/x", brief_review_model="anthropic/y",
                                                                         brief_writer="v4", brief_schema=SCHEMA_V3))
    contract = runtime.execution_contract(worker, SCHEMA_V3, {"input_refs": {"schema_version": SCHEMA_V3, "writer": "v4"}})
    assert contract["writer"] == "v4" and contract["ledger"] == {"version": ledger_v3.LEDGER_VERSION, "verifier": ledger_v3.VERIFIER_PROFILE}
    assert set(contract["prompt_hashes"]) == {"brief_plan", "brief_grade", "brief_write", "brief_repair", "brief_verify"}
    assert runtime.model_id(worker, "brief_verify") == "anthropic/y", "the verifier is the review model"


def test_a_live_run_refuses_a_verifier_of_the_writer_s_family_and_other_modes_skip_it(monkeypatch):
    worker = SimpleNamespace(models=Settings(), storage=StorageSettings(brief_model="openai/a", brief_review_model="openai/b"))
    angle = {"angle_id": "a", "body": {"card": CARD, "title": CARD["title"], "argument": CARD["core_perspective"]}}
    live = runtime.verifier_for(worker, {}, {"input_refs": {"angle": angle, "mode": "live"}}, EVIDENCE, provenance())
    with pytest.raises(ValueError, match="another model family"):
        live([{"id": "c_1", "label": "x", "text": "y"}])
    replay = runtime.verifier_for(worker, {}, {"input_refs": {"angle": angle, "mode": "synthetic"}}, EVIDENCE, provenance())
    with pytest.raises(ledger_v3.VerifierSkipped):
        replay([{"id": "c_1", "label": "x", "text": "y"}])


def test_the_verifier_schema_sent_leaves_out_what_anthropic_cannot_compile():
    """Anthropic's structured output refused VerifierOutput's full schema ("too complex for compilation", 20 October): the
    schema sent drops string patterns, length bounds and titles, keeps every field, enum and requirement, and the answer
    is still validated against the full contract."""
    sent, full = ledger_v3.wire_schema(), ledger_v3.VerifierOutput.model_json_schema()
    text = json.dumps(sent)
    assert '"pattern"' not in text and '"minLength"' not in text and '"title"' not in text
    statement = sent["$defs"]["VerifierStatement"]
    assert statement["required"] == full["$defs"]["VerifierStatement"]["required"]
    assert statement["properties"]["verdict"]["enum"] == full["$defs"]["VerifierStatement"]["properties"]["verdict"]["enum"]
    with pytest.raises(ValueError):
        ledger_v3.VerifierOutput.model_validate({"statements": [{"id": " ", "verdict": "supported", "claim_class": "outcome",
                                                                 "evidence_refs": [], "knowledge_base_document": None, "flag": None}]})
