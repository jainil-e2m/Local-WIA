"""E.B15 offline: the v2 contract, the writer's schema and prompts, and the v2 validators. No database, no HTTP."""
from __future__ import annotations

import copy
import json
import sys

import pytest

from backend_pipeline.briefs.contracts import Dossier
from backend_pipeline.briefs.contracts_v2 import SCHEMA_V2, BriefBodyV2, BriefDocumentV2, writer_schema_v2
from backend_pipeline.briefs.runtime import GUARD, system
from backend_pipeline.briefs.validation_v2 import checks_v2, repairable, semantic_hash_v2
from backend_pipeline.config import BACKEND_ROOT, PROJECT_ROOT
from backend_pipeline.cycle.verification import load_rules
from backend_pipeline.knowledge_base import team_roster
from backend_pipeline.tests.brief_v2_fixtures import v2_body

CARD = {"title": "Why we ask about follow-up first", "core_perspective": "Follow-up shapes lead quality.", "pillar": "WARM",
        "content_type": "behind_the_scenes", "audience": "Venue owners", "offer_connection": None}
EVIDENCE = [{"evidence_id": "ev_a", "transcript_id": "t", "excerpt": "Carmen Cruickshank: How do you reply to a new inquiry today?",
             "title": "Call", "speaker": "Carmen Cruickshank", "start_ms": 4000, "role": "anchor", "moment_ids": ["m1"]},
            {"evidence_id": "ev_b", "transcript_id": "t", "excerpt": "Shannon Lee: We moved to 45 inquiries a month after we changed it.",
             "title": "Call", "speaker": "Shannon Lee", "start_ms": 9000, "role": "support", "moment_ids": ["m1"]}]


def dossier(cta=None):
    angle = {"angle_id": "angle_1", "week_id": "w", "approved_hash": "h", "cta": cta or {"choice": "decide_in_development"},
             "body": {"card": CARD, "title": CARD["title"], "argument": CARD["core_perspective"], "audience": "Venue owners"}}
    return Dossier(angle=angle, evidence=EVIDENCE, prior=[], queries=[], coverage={}, gaps=[], audit=[], brand={"hash": "b"})


def provenance():
    return {"pinned_inputs": {}, "knowledge_base_keys": ["process_catalogue", "offer_sheet"],
            "roster": team_roster(BACKEND_ROOT / "knowledge_base")}


def packet():
    return {"approved_angle": {"title": CARD["title"], "core_perspective": CARD["core_perspective"]}, "card": CARD,
            "evidence": [{k: e[k] for k in ("evidence_id", "speaker", "start_ms", "excerpt")} | {"role": e["role"]} for e in EVIDENCE]}


def document(body=None, **header):
    body = body or v2_body(packet())
    cta = {**body["cta"], "chosen_by": "writer"}
    return {"header": {"schema_version": SCHEMA_V2, "angle_id": "angle_1", "angle_hash": "h", "purpose": "WARM",
                       "content_type": "behind_the_scenes", "audience": "Venue owners", "intended_shift": body["intended_shift"],
                       "point_of_view": body["point_of_view"], "cta": cta, "channels": ["reel", "carousel", "email", "caption"],
                       "pinned_inputs": {}, **header}, "body": body}


def messages(findings, severity="blocking"):
    return [f["message"] for f in findings if f["severity"] == severity]


def check(doc, cta=None):
    return checks_v2(doc, dossier(cta), provenance(), None, load_rules(BACKEND_ROOT / "knowledge_base"))


def test_a_clean_v2_brief_has_only_the_gate_two_items_left():
    findings = check(document())
    assert sorted(f["message"] for f in findings if f["severity"] == "blocking") == sorted([
        "The CTA is the writer's proposal; a person confirms it (or no explicit ask) at Gate 2",
        "Required before-publishing items remain unanswered"])
    assert all(f["gate"] for f in findings if f["severity"] == "blocking") and repairable(findings) == []
    confirmed = document()
    confirmed["header"]["cta"]["chosen_by"] = "person"
    confirmed["body"]["before_publishing"][0]["answer"] = "Confirmed with the client on 18 Oct."
    assert messages(check(confirmed)) == []


def test_the_approved_angle_is_locked_and_a_person_s_gate_one_cta_wins():
    body = v2_body(packet(), approved_angle={"title": "A punchier title", "core_perspective": CARD["core_perspective"]})
    assert any("approved title" in m for m in messages(check(document(body))))
    chosen = check(document(), cta={"text": "DM ADS"})
    assert any("differs from the one a person chose" in m for m in messages(chosen))


def test_quotes_numbers_and_claims_bind_to_their_evidence():
    body = v2_body(packet())
    body["evidence"][0]["quote"] = "A sentence nobody said"
    body["claims"].append({"claim_id": "c2", "text": "Inquiries rose to 45 a month.", "claim_class": "outcome", "evidence_ids": [],
                           "knowledge_base_document": None, "numeric_facts": [], "quote": None, "public_quote": False})
    body["claims"].append({"claim_id": "c3", "text": "We ask this on every audit.", "claim_class": "general_approach", "evidence_ids": [],
                           "knowledge_base_document": "not_a_document", "numeric_facts": [], "quote": None, "public_quote": False})
    body["wia_perspective"] = "Inquiries rose to 45 a month once we changed the reply."
    found = messages(check(document(body)))
    for expected in ("does not match the original wording", "outcome claim needs evidence", "A claim with a number",
                     "general-approach claim cites", "number in the public narrative"):
        assert any(expected in m for m in found), expected
    assert repairable(check(document(body))), "the writer can fix these, so repair runs"


def test_formats_stay_in_the_channel_set_and_each_reel_has_its_own_job():
    body = v2_body(packet())
    body["format_plan"]["stories"] = {"frames": ["A frame"]}
    body["format_plan"]["reels"].append(copy.deepcopy(body["format_plan"]["reels"][0]))
    body["format_plan"]["caption"]["hook"] = body["format_plan"]["reels"][0]["spoken_opening"]
    body["format_plan"]["email"]["ending"] = "DM us the word ADS."
    found = messages(check(document(body)))
    for expected in ("outside the confirmed channel set", "its own job and spoken opening", "repeats the Reel's spoken opening",
                     "never a DM"):
        assert any(expected in m for m in found), expected
    schema = writer_schema_v2(["reel", "email"])
    plan = schema["$defs"]["FormatPlan"]["properties"]
    assert plan["carousel"] == {"type": "null", "title": plan["carousel"]["title"]} and "anyOf" in plan["email"]


def test_who_speaks_and_private_speakers_in_the_public_narrative():
    body = v2_body(packet(), point_of_view="I")
    assert any('"I" is only for Whitney' in m for m in messages(check(document(body))))
    body = v2_body(packet())
    body["supporting_example"]["client_contribution"] = "Shannon described the change."
    body["supporting_example"]["wia_move"] = "Carmen asked how the first reply was written."
    found = messages(check(document(body)))
    assert any("Shannon (not WIA staff)" in m for m in found) and not any("Carmen" in m for m in found), "WIA staff may be credited"


def test_a_meeting_label_is_matched_by_the_name_in_it_once(monkeypatch):
    """N2, 23 October: "The Organic Moment Photo + Video" was searched for as "The" (eight false blocks on brief 2), and
    "Steve’s iPhone" as "Steve’s", which copy naming "Steve" never matched."""
    from backend_pipeline.briefs.validation_v2 import outside_name
    assert outside_name("The Organic Moment Photo + Video") == "Organic" and outside_name("Steve’s iPhone") == "Steve"
    assert outside_name("iPhone") is None and outside_name("Shannon Lee") == "Shannon"
    monkeypatch.setitem(EVIDENCE[1], "speaker", "The Organic Moment Photo + Video")
    body = v2_body(packet())
    body["supporting_example"]["client_contribution"] = "The owner described the change."
    assert not any("not WIA staff" in m for m in messages(check(document(body)))), "an article names no one"
    monkeypatch.setitem(EVIDENCE[1], "speaker", "Steve’s iPhone")
    body = v2_body(packet())
    body["supporting_example"]["client_contribution"] = "Steve described the change, and Steve agreed."
    assert [m for m in messages(check(document(body))) if "not WIA staff" in m] == [
        "Steve (not WIA staff) is named in the public narrative without clearance"]


def test_rules_and_e_b10_checks_run_on_the_narrative():
    body = v2_body(packet(), wia_perspective="We removed the old reply — and leads followed.")
    found = check(document(body))
    assert any(m.startswith("RR-01") for m in messages(found)), "an em dash is a ban in public copy"
    body = v2_body(packet())
    body["narrative_outline"]["main_point"] = "Almost nobody looks at follow-up."
    assert any("frequency or prevalence" in m for m in messages(check(document(body)), "warning"))


def test_the_semantic_hash_ignores_answers_and_the_cta_confirmation():
    doc = document()
    answered = copy.deepcopy(doc)
    answered["body"]["before_publishing"][0]["answer"] = "Yes"
    answered["header"]["cta"]["chosen_by"] = "person"
    assert semantic_hash_v2(doc) == semantic_hash_v2(answered)
    changed = copy.deepcopy(doc)
    changed["body"]["wia_perspective"] = "Something else."
    assert semantic_hash_v2(changed) != semantic_hash_v2(doc)
    BriefDocumentV2.model_validate(doc)


def test_the_writer_takes_the_knowledge_base_as_its_trusted_prefix():
    kb = "# WIA KNOWLEDGE BASE\n\nVoice guide."
    prompt = system("brief_write", SCHEMA_V2, kb)
    assert prompt.startswith("# WIA KNOWLEDGE BASE") and GUARD.strip() not in prompt, "no guard line over the trusted prefix"
    assert system("brief_plan", SCHEMA_V2).startswith(GUARD) and "WIA perspective" in system("brief_plan", SCHEMA_V2)
    assert system("brief_write").startswith(GUARD) and "brief_document_v1" not in system("brief_write"), "v1 prompts unchanged"
    with pytest.raises(ValueError, match="knowledge base"):
        system("brief_write", SCHEMA_V2)


def test_the_v2_prompts_pass_the_style_lint_and_drop_the_fixed_bundle():
    sys.path.insert(0, str(PROJECT_ROOT / "research" / "chatgpt-export-2026-10-18"))
    try:
        from lint import lint
    finally:
        sys.path.pop(0)
    templates = BACKEND_ROOT / "backend_pipeline" / "prompt_templates"
    for name in ("brief_write", "brief_repair", "brief_plan", "brief_grade"):
        text = (templates / f"{name}.v2.md").read_text(encoding="utf-8")
        assert [hit for hit in lint(text) if hit[0] != "price_in_public_copy"] == [], name
    writer = (templates / "brief_write.v2.md").read_text(encoding="utf-8")
    assert "three Reels, one carousel and one marketing email" not in writer and "confirmed channel set" in writer
    assert "I don't think the problem is X" not in writer and "observation" in writer, "observation-style example (E.B15 c)"
    assert '"we" for WIA' in writer and "CTA catalogue" in writer
    BriefBodyV2.model_validate(v2_body(packet()))


def test_an_internal_figure_in_public_copy_blocks_the_brief():
    """L.B5: internal items reach the writer's prefix labelled, and the Gate 2 checks block them in public copy."""
    body = v2_body(packet())
    body["wia_perspective"] = body["wia_perspective"] + " The retainer is $1,497/month."
    terms = {**provenance(), "internal_terms": [{"term": "$1,497", "item_id": "item_price"}]}
    findings = checks_v2(document(body), dossier(), terms, None, load_rules(BACKEND_ROOT / "knowledge_base"))
    assert any('states "$1,497", which WIA keeps internal' in m for m in messages(findings))
    clean = checks_v2(document(), dossier(), terms, None, load_rules(BACKEND_ROOT / "knowledge_base"))
    assert not any("keeps internal" in m for m in messages(clean))


@pytest.mark.parametrize("field", ["cta_why", "approved_angle", "claims"])
def test_an_internal_figure_anywhere_public_in_the_brief_blocks_it(field):
    """S.B2 review: the check covers the locked angle, the claims and the CTA, not only the narrative."""
    body = v2_body(packet())
    if field == "cta_why":
        body["cta_why"] += " It costs $1,497/month."
    elif field == "approved_angle":
        body["approved_angle"] = {**body["approved_angle"], "core_perspective": body["approved_angle"]["core_perspective"] + " At $1,497."}
    else:
        if not body.get("claims"):
            pytest.skip("The fixture brief has no claims")
        body["claims"][0]["text"] += " ($1,497/month)"
    terms = {**provenance(), "internal_terms": [{"term": "$1,497", "item_id": "item_price"}]}
    findings = checks_v2(document(body), dossier(), terms, None, load_rules(BACKEND_ROOT / "knowledge_base"))
    assert any('states "$1,497", which WIA keeps internal' in m for m in messages(findings))
    larger = {**provenance(), "internal_terms": [{"term": "$149", "item_id": "item_price"}]}
    assert not any("keeps internal" in m for m in messages(checks_v2(document(body), dossier(), larger, None,
                                                                     load_rules(BACKEND_ROOT / "knowledge_base"))))


def test_a_client_figure_in_public_copy_needs_its_clearance_and_a_price_is_banned():
    """E.B15: v2 keeps E.B10's consent check (a client's result needs permission, recorded as a clearance on its
    evidence) and the knowledge base's brief-scope rules (RR-04: no prices; RR-09: emails ask for a reply)."""
    from backend_pipeline.cycle.verification import load_rules as rules_for
    body = v2_body(packet(), wia_perspective="We changed the first reply, and the venue moved to 45 inquiries a month.")
    body["claims"].append({"claim_id": "c2", "text": "The venue moved to 45 inquiries a month.", "claim_class": "outcome",
                           "evidence_ids": ["ev_b"], "knowledge_base_document": None, "quote": None, "public_quote": False,
                           "numeric_facts": [{"value": "45", "unit": "inquiries a month", "subject": "the venue", "timeframe": "a month",
                                              "evidence_id": "ev_b",
                                              "source_quote": "We moved to 45 inquiries a month"}]})
    rules = rules_for(BACKEND_ROOT / "knowledge_base", stage="brief")
    found = checks_v2(document(body), dossier(), provenance(), None, rules)
    assert any("permission" in m and "45 inquiries" in m for m in messages(found)), messages(found)
    cleared = checks_v2(document(body), dossier(), provenance(), {"ev_b": {"permission_reference": "email 2026-10-01",
                                                                          "attribution_reference": "client"}}, rules)
    assert not any("permission" in m and "45 inquiries" in m for m in messages(cleared))
    priced = v2_body(packet(), wia_perspective="We look at follow-up first; the audit normally costs $297.")
    assert any(m.startswith("RR-04") for m in messages(checks_v2(document(priced), dossier(), provenance(), None, rules)))
    dm = v2_body(packet())
    dm["format_plan"]["caption"]["ending"] = "DM us ADS to talk about your follow-up."
    assert not any(m.startswith("RR-09") for m in messages(checks_v2(document(dm), dossier(), provenance(), None, rules))), \
        "a DM keyword is fine on Instagram; RR-09 is for email assets"


def test_a_numeric_fact_s_value_must_appear_in_its_source_quote():
    """Condition 5 and 4.B8: a fabricated figure stays blocked even when the writer binds it to a real quote."""
    body = v2_body(packet(), wia_perspective="We changed the first reply, and the venue moved to 90 inquiries a month.")
    body["claims"].append({"claim_id": "c2", "text": "The venue moved to 90 inquiries a month.", "claim_class": "outcome",
                           "evidence_ids": ["ev_b"], "knowledge_base_document": None, "quote": None, "public_quote": False,
                           "numeric_facts": [{"value": "90", "unit": "inquiries a month", "subject": "the venue", "timeframe": "a month",
                                              "evidence_id": "ev_b", "source_quote": "We moved to 45 inquiries a month"}]})
    found = messages(check(document(body)))
    assert any("does not appear in its source quote" in m for m in found), found
    assert any(f["message"].startswith("A numeric fact") for f in repairable(check(document(body)))), "the writer can fix it"
    body["claims"][-1]["numeric_facts"][0]["value"] = "45"
    body["claims"][-1]["text"] = "The venue moved to 45 inquiries a month."
    body["wia_perspective"] = "We changed the first reply, and the venue moved to 45 inquiries a month."
    assert not any("source quote" in m for m in messages(check(document(body))))


def test_external_framing_never_proves_a_wia_or_client_result():
    """Condition 6: an external research item may frame a point, never prove what WIA or a client did or achieved."""
    external = {"evidence_id": "ev_x", "excerpt": "Industry survey: couples book within 30 days.", "title": "Survey",
                "speaker": None, "start_ms": None, "role": "external_framing", "source_url": "https://example.test/survey"}
    d = dossier()
    d = d.model_copy(update={"evidence": [*d.evidence, type(d.evidence[0]).model_validate(external)]})
    for claim_class in ("outcome", "particular_interaction"):
        body = v2_body(packet())
        body["claims"].append({"claim_id": "c2", "text": "Couples booked within a month of the change.", "claim_class": claim_class,
                               "evidence_ids": ["ev_x"], "knowledge_base_document": None, "quote": None, "public_quote": False,
                               "numeric_facts": []})
        found = messages(checks_v2(document(body), d, provenance(), None, load_rules(BACKEND_ROOT / "knowledge_base")))
        assert any("External framing cannot prove" in m for m in found), (claim_class, found)
    body["claims"][-1]["claim_class"] = "prevalence"
    found = messages(checks_v2(document(body), d, provenance(), None, load_rules(BACKEND_ROOT / "knowledge_base")))
    assert not any("External framing cannot prove" in m for m in found), "external framing may support a prevalence claim"


def test_every_format_in_the_confirmed_channel_set_is_planned():
    """2.4a (d): a confirmed channel with no entry in the format plan blocks, and the writer is asked to repair it."""
    for missing in ("email", "caption", "carousel"):
        body = v2_body(packet())
        body["format_plan"][missing] = None
        findings = check(document(body))
        assert any(f"has no {missing}" in f["message"] for f in repairable(findings)), (missing, messages(findings))
    body = v2_body(packet())
    body["format_plan"]["reels"] = []
    assert any("has no reel" in m for m in messages(check(document(body))))
    assert not any("has no " in m for m in messages(check(document(v2_body(packet())))))


def test_checking_language_and_writing_instructions_in_copy_are_shown_as_warnings():
    """2.4a (g), from the live week's briefs: limits such as "subject to permission" or "not implemented" belong under
    Before publishing, and a copy field holds copy, not instructions to a writer. Warnings until E.X2 rules, each naming
    the field it was found in; a clean brief has none."""
    body = v2_body(packet())
    body["wia_perspective"] = "We suggested an earlier call. Both were recommendations on that call, not changes we have documented."
    body["supporting_example"]["scene"] = "These are observations, not independently verified visitor data."
    body["format_plan"]["carousel"]["slides"][2]["text"] = "The evidence does not show Jacqueline reviewing the page."
    body["format_plan"]["email"]["argument"] = ("An owner wants to know what to change. Explain why that distinction matters. "
                                                "Use this account-specific scene only after permission is confirmed.")
    body["format_plan"]["caption"]["adds"] = "Develop a concise, substantive caption using Savannah's framework."
    body["format_plan"]["caption"]["ending"] = "Finish on the distinction. Sign off as Whitney."
    findings = check(document(body))
    warned = [f for f in findings if f["severity"] == "warning" and f.get("field")]
    fields = {f["field"] for f in warned}
    assert {"wia_perspective", "supporting_example.scene", "format_plan.carousel.slides[3].text", "format_plan.email.argument",
            "format_plan.caption.adds", "format_plan.caption.ending"} <= fields, fields
    assert any("checking language" in f["message"] and "The email's argument" in f["message"] for f in warned)
    assert any("writing instruction" in f["message"] and "The caption's adds" in f["message"] for f in warned)
    assert not any(f["severity"] == "blocking" and f.get("field") for f in findings), "warnings only (2.4a g)"
    clean = v2_body(packet())
    clean["format_plan"]["carousel"]["slides"][0]["text"] = "Start with your calendar. Keep the first reply short."
    assert not [f for f in check(document(clean)) if f.get("field")], "copy that addresses the reader is not an instruction"


def test_a_former_team_member_is_never_named_in_reader_facing_copy():
    """2.4a (h), the lead's ruling under D12: the stricter brief standard wins over RR-27 for public copy. A former team
    member named in any copy field blocks (credit "our team"); naming them in the claims and evidence stays allowed."""
    body = v2_body(packet())
    body["format_plan"]["reels"][0]["beats"] = ["Fallon Looney, a former team member, proposed reviewing the nurture.", "Why it matters"]
    body["format_plan"]["email"]["argument"] = "Fallon also proposed a supplemental email."
    found = [f for f in check(document(body)) if f["severity"] == "blocking" and "has left WIA" in f["message"]]
    assert len(found) == 1 and "Reel 1" in found[0]["message"] and "email" in found[0]["message"], found
    assert repairable(found), "the writer credits our team instead"
    allowed = v2_body(packet())
    allowed["claims"][0]["text"] = "Fallon Looney, a former team member, proposed reviewing the nurture."
    assert not any("has left WIA" in m for m in messages(check(document(allowed))))


def test_the_knowledge_base_prefix_does_not_count_against_the_request_budget(monkeypatch):
    """E.B15 (e): the 120,000-character limit applies to the writer's message (the dossier), not to the trusted
    knowledge-base prefix, which alone is larger than the limit here; an oversized message is still refused."""
    from types import SimpleNamespace

    from backend_pipeline.briefs import runtime
    from backend_pipeline.config import Settings
    from backend_pipeline.storage_config import StorageSettings
    kb = SimpleNamespace(text="# WIA KNOWLEDGE BASE\n\n" + "Voice guide line.\n" * 2000, refs=lambda: {"version": "kb-test"})
    sent = []
    monkeypatch.setattr(runtime, "check_dependencies", lambda worker, run: None)
    monkeypatch.setattr(runtime, "knowledge", lambda worker, run=None: kb)
    monkeypatch.setattr(runtime, "chat", lambda *a, **k: sent.append(k["request"]) or "written")
    worker = SimpleNamespace(models=Settings(), storage=StorageSettings(brief_max_characters=5000, brief_model="m", brief_review_model="m"))
    run = {"run_id": "r", "input_refs": {"schema_version": SCHEMA_V2, "mode": "replay"}}
    assert len(kb.text) > worker.storage.brief_max_characters
    assert runtime.call(worker, {}, run, "brief_write", BriefBodyV2, {"evidence": ["a short dossier"]}, {"type": "object"}) == "written"
    assert kb.text.strip() in json.dumps(sent[0], ensure_ascii=False).replace("\\n", "\n"), "the prefix is sent whole"
    with pytest.raises(ValueError, match="exceeds preflight"):
        runtime.call(worker, {}, run, "brief_write", BriefBodyV2, {"evidence": ["x" * 6000]}, {"type": "object"})


def test_the_v2_export_states_prior_coverage_and_how_complete_it_is():
    """Section 2.4 condition 9 on the surface: the v2 brief as Whitney reads it lists the overlapping earlier pieces, or
    says none were found, and how complete the comparison set was (the v1 export had this; the v2 export did not)."""
    from backend_pipeline.briefs.gate_two import markdown_v2
    row = {"content_body": {"document": document(), "review": {"findings": []}}, "prior_content_context": [],
           "research_gaps": {"items": [], "coverage": {"published_archive": "incomplete_legacy_catalogue_missing",
                                                      "prior_coverage_gaps": [{"angle_id": "angle_old", "reason": "no_compatible_vector"}]}}}
    text = markdown_v2(row)
    section = text[text.index("## Prior coverage"):]
    assert "No earlier idea or brief on this point was found" in section
    assert "published content is not yet part of the comparison" in section and "1 earlier idea could not be compared" in section
    row["prior_content_context"] = [{"angle_id": "angle_prior", "argument": "Follow-up decides which inquiries become tours.",
                                     "approval_status": "approved", "briefs": [{"approval_status": "approved"}], "publications": []}]
    section = markdown_v2(row)[markdown_v2(row).index("## Prior coverage"):]
    assert "Follow-up decides which inquiries become tours. (approved idea; 1 approved brief; not published)" in section
    assert "angle_prior" not in section, "no identifiers on the reader's surface (R50)"


def test_a_client_without_consent_is_not_named_in_public_copy():
    """Condition 7 and 2.4a (h): a client on the reviewed list is named in public copy only with consent to be named or
    an approver's clearance on that client's evidence; a client marked no_use is never named."""
    clients = [{"client_id": "cl_1", "name": "Willow Creek Barn", "aliases": ["Willow Creek"], "consent": "anonymise_only",
                "transcript_ids": ["t"]},
               {"client_id": "cl_2", "name": "Harbor House", "aliases": [], "consent": "may_name", "transcript_ids": []}]
    with_clients = {**provenance(), "clients": clients}
    rules = load_rules(BACKEND_ROOT / "knowledge_base")
    body = v2_body(packet())
    body["supporting_example"]["scene"] = "At Willow Creek, the owner walked us through the first reply."
    found = messages(checks_v2(document(body), dossier(), with_clients, None, rules))
    assert any("Willow Creek" in m and "consent" in m for m in found), found
    cleared = checks_v2(document(body), dossier(), with_clients, {"ev_a": {"permission_reference": "email 2026-10-01",
                                                                          "attribution_reference": "owner"}}, rules)
    assert not any("Willow Creek" in m for m in messages(cleared)), "a clearance on that client's evidence allows it"
    no_use = {**provenance(), "clients": [{**clients[0], "consent": "no_use"}]}
    assert any("Willow Creek" in m for m in messages(checks_v2(document(body), dossier(), no_use, {"ev_a": {"x": 1}}, rules))), \
        "a brief clearance never overrides no_use"
    named = v2_body(packet())
    named["supporting_example"]["scene"] = "At Harbor House, the owner walked us through the first reply."
    assert not any("Harbor House" in m for m in messages(checks_v2(document(named), dossier(), with_clients, None, rules)))
    assert not any("consent" in m for m in messages(checks_v2(document(v2_body(packet())), dossier(), with_clients, None, rules)))
