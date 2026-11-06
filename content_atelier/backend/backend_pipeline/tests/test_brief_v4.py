"""E.B33 offline: brief contract v4 and writer v5, the settings that select them, v3's ledger over v4's copy, the v4 checks,
and the places a v4 brief renders (the Markdown export, the hand-off pieces, the week's review document). No database, no
HTTP, no model call."""
from __future__ import annotations

import json
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from backend_pipeline import settings_store
from backend_pipeline.briefs import handoff, ledger_v3, paths, review_document
from backend_pipeline.briefs.contracts_v4 import (EDITABLE_V4, SCHEMA_V4, BriefDocumentV4, BriefWriteV4, copy_fields_v4,
                                                 writer_part_v4, writer_schema_v4)
from backend_pipeline.briefs.render_v4 import markdown_v4
from backend_pipeline.briefs.runtime import RENDERED_WRITERS, render_writer, system, writer_of
from backend_pipeline.briefs.validation_v3 import contract_for, ledger_body
from backend_pipeline.briefs.validation_v4 import checks_v4
from backend_pipeline.briefs.workflow import writer_for
from backend_pipeline.config import BACKEND_ROOT
from backend_pipeline.cycle.verification import load_rules
from backend_pipeline.storage_config import StorageSettings
from backend_pipeline.tests.brief_v4_fixtures import v4_body
from backend_pipeline.tests.test_brief_v3 import EVIDENCE, dossier, packet, provenance

TEMPLATES = Path(__file__).resolve().parents[1] / "prompt_templates"
V4 = contract_for(SCHEMA_V4)
CHANNELS = ["reel", "carousel", "email", "caption"]


def document(writer=None, **kw):
    writer = writer or v4_body(packet())
    body, record = ledger_body(writer, EVIDENCE, provenance(), contract=V4, **kw)
    header = {"schema_version": SCHEMA_V4, "angle_id": "angle_1", "angle_hash": "h", "purpose": "WARM", "content_type": "behind_the_scenes",
              "audience": "Venue owners", "intended_shift": body["intended_shift"], "point_of_view": body["point_of_view"],
              "cta": {**body["cta"], "chosen_by": "writer"}, "channels": CHANNELS, "pinned_inputs": {}}
    return {"header": header, "body": body}, record


def check(doc, **kw):
    return checks_v4(doc, dossier(), provenance(), None, load_rules(BACKEND_ROOT / "knowledge_base"), **kw)


# The contract ------------------------------------------------------------------------------------------------------

def test_the_writer_schema_has_the_fields_wia_reviewed_in_the_13_october_order():
    schema = writer_schema_v4(CHANNELS)
    order = list(schema["properties"])
    assert order[:4] == ["approved_angle", "sharpened_point", "central_point", "strategic_purpose"]
    assert order.index("before_publishing") < order.index("format_plan") == len(order) - 1, "the brief, then every asset's copy"
    defs = schema["$defs"]
    reel = defs["ReelPlanV4"]["properties"]
    assert reel["kind"]["enum"] == ["story", "stance", "broll_text"] and reel["register"]["enum"] == ["spoken", "on_screen"]
    assert {"on_screen_hook", "caption", "screens", "offer_descriptor", "personal_lines"} <= set(reel)
    assert {"title", "caption", "register", "offer_descriptor"} <= set(defs["CarouselPlanV4"]["properties"])
    assert set(defs["SendHeader"]["properties"]) == {"date", "send_time", "recipients"}
    assert {"send_header", "register", "offer_descriptor"} <= set(defs["EmailPlanV4"]["properties"])
    assert "desired_response" in defs["StrategicPurposeV4"]["properties"]
    assert {"timestamps", "details", "credits"} <= set(defs["SupportingExampleV4"]["properties"])
    assert defs["SupportingExampleV4"]["properties"]["details"]["maxItems"] == 2, "one moment, at most two concrete details"
    assert "evidence_ids" not in json.dumps(schema) and "claims" not in schema["properties"]
    narrowed = writer_schema_v4(["reel", "email"])["$defs"]
    assert narrowed["FormatPlanV4"]["properties"]["carousel"]["type"] == "null"
    assert narrowed["ReelPlanV4"]["properties"]["caption"]["type"] == "null", "no captions outside the caption channel"
    BriefWriteV4.model_validate(v4_body(packet()))


def test_two_reels_are_allowed_and_b_roll_has_at_most_three_screens():
    two = v4_body(packet())
    two["format_plan"]["reels"] = two["format_plan"]["reels"][:2]
    BriefWriteV4.model_validate(two)
    four = v4_body(packet())
    four["format_plan"]["reels"][2]["screens"] = ["1", "2", "3", "4"]
    with pytest.raises(ValueError):
        BriefWriteV4.model_validate(four)


def test_every_asset_field_is_marked_copy_or_direction():
    defs = BriefWriteV4.model_json_schema()["$defs"]
    copy = {"cover_text", "on_screen_hook", "spoken_opening", "script", "screens", "caption", "title", "subject_options", "preview",
            "opening", "body", "ending"}
    for name in ("ReelPlanV4", "CarouselPlanV4", "EmailPlanV4"):
        for field, spec in defs[name]["properties"].items():
            if field in copy:
                assert (spec.get("description") or "").startswith("Copy:"), (name, field)
            if field in ("job", "beats", "personal_lines"):
                assert spec["description"].startswith("Direction:"), (name, field)


# Settings and the writer --------------------------------------------------------------------------------------------

def test_contract_v4_is_written_by_writer_v5_and_selected_by_setting_not_by_default():
    assert settings_store._BY_KEY["prompts.profile.brief"].default == "brief_document_v1", "not the default until M3"
    settings_store.validate_profile({"settings": {"prompts.profile.brief": SCHEMA_V4, "prompts.profile.brief_writer": "v5"}})
    with pytest.raises(ValueError):
        settings_store.validate_profile({"settings": {"prompts.profile.brief": SCHEMA_V4, "prompts.profile.brief_writer": "v4.1"}})
    with pytest.raises(ValueError):
        settings_store.validate_profile({"settings": {"prompts.profile.brief": "brief_document_v3", "prompts.profile.brief_writer": "v5"}})
    assert writer_for(StorageSettings(brief_writer="v5"), SCHEMA_V4) == "v5"
    assert writer_for(StorageSettings(brief_writer="v4"), SCHEMA_V4, revision="brief_x") == "v5", "a refresh of a v4 brief uses v5"
    assert writer_of({"input_refs": {"schema_version": SCHEMA_V4}}) == "v5"
    assert RENDERED_WRITERS["v5"] == "v5" and RENDERED_WRITERS["v4.1"] == "v4"


def test_writer_v5_carries_interface_1s_blocks_and_never_asks_for_a_distinct_point():
    v5 = (TEMPLATES / "brief_write.v5.md").read_text(encoding="utf-8")
    assert "{{#revision_instructions}}" in v5 and "{{#locked_fields}}" in v5 and "reviewer_context" in v5
    assert "distinct point" not in v5 and "different doors" in v5
    for rule in ("Specific.", "Slide 1 carries the promise.", "Subject lines", "No insider terms.", "Who did what.",
                 "insider_terms", "offer_descriptors", "guardrail", "knowledge-base document 18", "follow along"):
        assert rule in v5, rule
    first = system("brief_write", SCHEMA_V4, "KB", "v5", {"revision_instructions": "", "locked_fields": []})
    assert first.startswith("KB") and "{{#" not in first and "This is a refresh" not in first
    assert "{{contact.first_name}}" in first, "the email's merge tag is left as written"
    rendered = render_writer(v5, "Make the subject about the problem.", [{"path": "format_plan.reels[0].cover_text", "value": "Mine"}])
    assert "Make the subject about the problem." in rendered and '- `format_plan.reels[0].cover_text`: "Mine"' in rendered
    repair = system("brief_repair", SCHEMA_V4, "KB", "v5")
    assert "keep its concrete subject" in repair and repair == "KB\n\n" + (TEMPLATES / "brief_repair.v5.md").read_text(encoding="utf-8")


def test_no_week_2_text_or_wia_correction_is_in_the_v5_prompts():
    # D28: her 20 October corrections are tests, never exemplars.
    text = "\n".join((TEMPLATES / n).read_text(encoding="utf-8") for n in ("brief_write.v5.md", "brief_repair.v5.md")).lower()
    for line in ("did i set my ads up wrong", "your ads are working, and then they stop", "she used ai to set up",
                 "when more inquiries aren't enough", "accelerator members recently", "office hours", "why we lowered"):
        assert line not in text, line


# The ledger over v4's copy ------------------------------------------------------------------------------------------

def test_v3s_ledger_reads_v4s_copy_and_its_fields_map_to_paths():
    doc, record = document()
    BriefDocumentV4.model_validate(doc)
    assert writer_part_v4(doc["body"]) == v4_body(packet())
    fields = {f for f, _, _ in copy_fields_v4(doc["body"], wide=True)}
    assert {"format_plan.reels[3].screens[0]", "format_plan.reels[1].caption.hook", "format_plan.carousel.title",
            "format_plan.email.subject_options[0]", "central_point"} <= fields
    assert ledger_v3.copy_fields_v3(doc["body"]) == copy_fields_v4(doc["body"]), "the ledger dispatches on the body's shape"
    for field in fields:
        assert paths.exists(doc["body"], ledger_v3.field_path(field, doc["body"])), field
    scene = next(c for c in doc["body"]["claims"] if c["field"] == "supporting_example.scene")
    assert scene["status"] == "bound" and record["counts"]["bound"] >= 1


def test_an_attested_fact_settles_a_v4_line_and_enters_the_ledger():
    item = {"id": "context_1", "kind": "attested_fact", "author": "approver@example.invalid", "created_at": "2026-10-22T10:00:00+00:00",
            "text": "Her inquiries were up when she came to us, and her first reply took two days."}
    doc, record = document(attested=[item])
    entries = [c for c in doc["body"]["claims"] if c["field"] == "context_items"]
    assert entries and entries[0]["status"] == "attested" and entries[0]["attested"]["by"] == "approver@example.invalid"
    assert any(c["status"] == "attested" and c["field"].startswith("format_plan.reels[3]") for c in doc["body"]["claims"])
    assert record["counts"]["attested"] >= 2


# The checks ---------------------------------------------------------------------------------------------------------

def test_a_clean_v4_brief_has_only_the_gate_findings():
    doc, _ = document()
    blocking = [f["message"] for f in check(doc) if f["severity"] == "blocking"]
    assert all("Gate 2" in m or "before-publishing" in m for m in blocking), blocking
    assert not [f for f in check(doc) if (f.get("check") or "").startswith(("first_touch.", "copy.", "format."))]


def test_the_v4_checks_include_the_first_touch_asset_and_week_checks():
    writer = v4_body(packet())
    writer["format_plan"]["reels"][1]["cover_text"] = "Did I set this up wrong?"
    writer["format_plan"]["reels"][1]["on_screen_hook"] = "One question from office hours"
    writer["format_plan"]["email"]["body"] = "What we built:\n- a welcome video\n- a reply in the first hour"
    doc, _ = document(writer)
    found = check(doc, siblings=[{"brief_id": "b2", "title": "Another idea", "body": v4_body(packet())}])
    checks = {f.get("check") for f in found}
    assert {"first_touch.specific", "first_touch.insider_term", "format.email_bullets", "week.covers"} <= checks
    assert any(f["severity"] == "blocking" and f.get("check") == "first_touch.insider_term" for f in found)


def test_the_caveat_lint_and_the_rejection_rules_run_on_v4_copy():
    writer = v4_body(packet())
    writer["format_plan"]["reels"][0]["caption"]["body"] = "The reply carries it — this is not independently verified."
    doc, _ = document(writer)
    messages = [f["message"] for f in check(doc)]
    assert any("checking language" in m for m in messages) and any(m.startswith("RR-01") for m in messages)


def test_a_missing_caption_or_format_in_the_channel_set_blocks():
    writer = v4_body(packet())
    writer["format_plan"]["email"] = None
    for r in writer["format_plan"]["reels"]:
        r["caption"] = None
    writer["format_plan"]["carousel"]["caption"] = None
    doc, _ = document(writer)
    blocking = [f["message"] for f in check(doc) if f["severity"] == "blocking"]
    assert any("no email" in m for m in blocking) and any("no caption" in m for m in blocking)


# Where a v4 brief renders -------------------------------------------------------------------------------------------

def row_for(doc):
    return {"brief_id": "brief_v4", "week_id": "w", "angle_id": "angle_1", "approval_status": "pending", "approved_by": None,
            "updated_by": "system", "version_number": 1, "selected_evidence": EVIDENCE, "prior_content_context": [],
            "research_gaps": {"items": [], "coverage": {}},
            "content_body": {"schema_version": SCHEMA_V4, "document": doc, "review": {"findings": [], "locked_fields": []},
                             "provenance": {}}}


def test_the_markdown_export_follows_the_13_october_order_and_the_pack_layout():
    doc, _ = document()
    text = markdown_v4(row_for(doc))
    order = ["## Central point", "## Strategic purpose and desired response", "## Audience and reason to care", "## WIA perspective",
             "## Supporting example", "## Narrative outline", "## Format and creative approach", "## CTA and essential boundaries",
             "## Email", "## Reel 1: The moment, face to camera", "## Reel 3: The turn of the story in screens",
             "## Carousel: When more inquiries aren't turning into tours", "## Evidence", "## Claims", "## Checks"]
    lines = text.splitlines()
    assert [lines.index(h) for h in order] == sorted(lines.index(h) for h in order)
    for line in ("**DATE:** Tuesday of the publishing week", "**SUBJECT:** When more inquiries aren't enough",
                 "**Format:** b-roll with on-screen text", "**On-screen hook:** Before we touch your ads, one question",
                 "1. Her inquiries were up.", "- 0:04 the question about the first reply", "Desired response: I want an ads partner"):
        assert any(x.startswith(line) for x in lines), line


def test_the_hand_off_view_gives_each_v4_piece_its_copy_and_direction():
    doc, _ = document()
    pieces = handoff.pieces(row_for(doc))
    assert [p["key"] for p in pieces] == ["reel_1", "reel_2", "reel_3", "carousel", "email"]
    reel = pieces[2]
    assert reel["copy"]["screens"] and reel["copy"]["caption"]["hook"] and reel["direction"]["kind"] == "broll_text"
    assert pieces[3]["copy"]["title"] and pieces[3]["copy"]["caption"] and pieces[3]["direction"]["register"] == "written"
    assert pieces[4]["direction"]["send_header"]["date"] and "subject_options" in pieces[4]["copy"]
    assert handoff.message_spine(row_for(doc))["supporting"][0] == doc["body"]["central_point"]


def test_the_review_document_renders_a_v4_brief():
    from backend_pipeline.tests.test_review_document import angle
    doc, _ = document()
    brief = {**row_for(doc), "content_body": {"document": doc}}
    material = {"week": {"week_id": "w", "week_start": date(2026, 10, 12), "week_end": date(2026, 10, 18)},
                "cards": [angle("a1", 1, pillar="WARM")], "briefs": {"a1": brief}, "run_refs": {}}
    text = review_document.render(material, exported=datetime(2026, 10, 27, tzinfo=UTC))
    for line in ("**Central point.** The first reply to an inquiry shapes which couples book a tour.",
                 "**DATE:** Tuesday of the publishing week", "**Format:** b-roll with on-screen text",
                 "**On-screen hook:** Before we touch your ads, one question", "**Title:** When more inquiries aren't turning into tours",
                 "**Register:** spoken", "(brief contract v4)"):
        assert line in text, line


def test_every_v4_section_a_person_may_edit_is_a_path_the_editor_can_walk():
    doc, _ = document()
    assert EDITABLE_V4 == set(BriefWriteV4.model_fields) - {"approved_angle", "cta"}
    edited, changed = paths.apply(writer_part_v4(doc["body"]), {"format_plan.reels[2].screens[1]": "The first reply took a day.",
                                                                  "format_plan.email.send_header.date": "Wednesday"}, EDITABLE_V4)
    assert changed == ["format_plan.email.send_header.date", "format_plan.reels[2].screens[1]"]
    BriefWriteV4.model_validate(edited)


def test_writer_v5_reads_each_turn_without_its_speaker_label():
    """N1 shakedown: an excerpt began with its speaker ("Steve's iPhone: Okay, got it."), and writer v5 copied the label into
    the copy. The speaker has its own field; the words go without it, and only a whole "Speaker:" prefix is dropped."""
    from types import SimpleNamespace

    from backend_pipeline.briefs.workflow import writer_packet_v4
    from backend_pipeline.config import BACKEND_ROOT

    def turn(i, speaker, words):
        return dict(evidence_id=f"e{i}", speaker=speaker, start_ms=i, role="anchor", excerpt=words, qualifications=[])
    run = {"input_refs": {"angle": {"body": {"title": "T", "argument": "A", "audience": "Owners", "card": {}}, "steer": None,
                                    "cta": None}, "channels": ["email"]}}
    dossier = {"evidence": [turn(1, "Steve’s iPhone", "Steve’s iPhone: Okay, got it."),
                            turn(2, "Whitney Hodges", "Whitney Hodges said it twice."), turn(3, None, "No label: kept.")],
               "prior": [], "gaps": [], "brand": {}}
    worker = SimpleNamespace(models=SimpleNamespace(knowledge_base_root=BACKEND_ROOT / "knowledge_base"))
    packet = writer_packet_v4(worker, run, dossier)
    assert [e["excerpt"] for e in packet["evidence"]] == ["Okay, got it.", "Whitney Hodges said it twice.", "No label: kept."]
    assert packet["evidence"][0]["speaker"] == "Steve’s iPhone"


def test_the_v4_markdown_names_an_evidence_speaker_once():
    from backend_pipeline.briefs import turns
    assert turns.words("Owner: Okay, got it.", "Owner") == "Okay, got it."
    assert turns.words("Owner's partner said so.", "Owner") == "Owner's partner said so."
    assert turns.words("Note: kept", None) == "Note: kept"
