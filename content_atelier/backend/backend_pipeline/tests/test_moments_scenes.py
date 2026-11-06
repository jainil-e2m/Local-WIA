"""Scene profile v2 (plan 2.B2, 2.B3) and the per-scene check, offline: contract, prompt, provenance, and E.B12a's rule
applied to a document's response without the weekly seven-type contract. v1 stays as it was."""
from __future__ import annotations

import json
import sys

import pytest
from pydantic import ValidationError

from backend_pipeline.config import BACKEND_ROOT, PROJECT_ROOT
from backend_pipeline.knowledge_base import load_knowledge_base
from backend_pipeline.llm.stage import SchemaViolation, repairable
from backend_pipeline.models import Span, Transcript
from backend_pipeline.moments import extract, scenes, types
from backend_pipeline.tests.moments_fixtures import response, scene
from backend_pipeline.tests.test_scenes import output as v1_output
from backend_pipeline.tests.test_scenes import scene as v1_scene

TEXTS = ["Carmen: Welcome Dana.", "Dana: We had 45 bookings in March.", "Carmen: Great, the follow-up helped.", "Dana: Lead Lock has helped a lot with the follow-up."]
REFS = {f"m1.t{i + 1:04d}": f"doc:span:{i}" for i in range(4)}
INVENTORY = [{"meeting_ref": "m1", "first_span_id": "m1.t0001", "last_span_id": "m1.t0004", "span_count": 4}]


def transcripts():
    spans = [Span(span_id=f"doc:span:{i}", source_id="doc", ordinal=i, start_seconds=None, end_seconds=None, speaker=t.split(":")[0], text=t)
             for i, t in enumerate(TEXTS)]
    return [Transcript(source_id="doc", week_index=0, path="doc.vtt", content_hash="h", spans=spans, source_format="webvtt")]


def quote_of(index, text):
    return {"anchor_span_ids": [f"m1.t{index:04d}"], "context_first_span_id": f"m1.t{index:04d}", "context_last_span_id": f"m1.t{index:04d}",
            "quote": text}


# ---- the profile ---------------------------------------------------------------------------------------------------------

def test_the_vocabulary_has_twelve_types_and_v1_keeps_its_seven():
    assert len(types.MOMENT_TYPES) == 12 and set(types.ADDED_MOMENT_TYPES) == {"testimonial", "question", "teaching", "soundbite", "data_point"}
    v1 = scenes.schema(scenes.SCENE_PROFILE)["$defs"]["SceneDraft"]["properties"]["moment_type"]["enum"]
    v2 = scenes.schema(scenes.SCENE_V2_PROFILE)["$defs"]["SceneDraftV2"]["properties"]["moment_type"]["enum"]
    assert tuple(v1) == types.LEGACY_MOMENT_TYPES and tuple(v2) == types.MOMENT_TYPES
    assert scenes.PROFILES[scenes.SCENE_PROFILE]["types"] == types.LEGACY_MOMENT_TYPES
    # v1's schema is byte-identical to what it was: a changed schema would change every saved request fingerprint.
    assert json.dumps(scenes.schema(), sort_keys=True) == json.dumps(scenes.SceneResponse.model_json_schema(), sort_keys=True)
    assert scenes.SceneResponse.model_json_schema()["title"] == "SceneResponse"


def test_v1_rejects_the_new_types_and_v2_accepts_all_twelve():
    with pytest.raises(ValidationError):
        scenes.SceneResponse.model_validate(v1_output(v1_scene(moment_type="testimonial")))
    for kind in types.MOMENT_TYPES:
        scenes.SceneResponseV2.model_validate(response(INVENTORY, scene(moment_type=kind)))
    compact = scenes.to_compact(response(INVENTORY, scene(moment_type="data_point")), scenes.SceneResponseV2)
    assert compact["moments"][0]["moment_type"] == "data_point" and compact["moments"][0]["proposition"].startswith("Carmen Cruickshank asked")


def test_the_v1_prompt_file_is_untouched_and_v2_has_its_own():
    v1 = scenes.TEMPLATE.read_text(encoding="utf-8")
    assert scenes.TEMPLATE.name == "scene_extraction.v1.md" and "testimonial" not in v1
    v2 = scenes.TEMPLATE_V2.read_text(encoding="utf-8")
    assert scenes.TEMPLATE_V2.name == "scene_extraction.v2.md" and v2 != v1
    for needed in ("testimonial", "soundbite", "data_point", "teaching", "question", "Only a client's or prospect's own words",
                   "Never add, convert, round or combine figures", "call_type", "glossary", "speakers", "not as done"):
        assert needed in v2, needed
    sys.path.insert(0, str(PROJECT_ROOT / "research" / "chatgpt-export-2026-10-18"))
    try:
        from lint import lint
    finally:
        sys.path.pop(0)
    assert lint(v2) == []


def test_every_example_in_the_v2_prompt_is_invented_and_recorded():
    v2 = scenes.TEMPLATE_V2.read_text(encoding="utf-8")
    for example in scenes.SCENE_V2_EXAMPLES:
        assert example["text"] in v2, example["text"]
        assert example["derived_from_weeks"] == [] and "Invented" in example["source"] and example["kind"] == "example"


def test_the_v2_packet_carries_the_roster_catalogue_call_type_speaker_roles_glossary_and_handling():
    kb = load_knowledge_base(BACKEND_ROOT / "knowledge_base", stage="extraction")
    row = {"call_type": "client_1to1", "original_text": "Dana: Lead Lock helped. Carmen: yes.",
           "speaker_map": {"Dana": {"role": "client", "inferred": True}, "Carmen": {"role": "staff", "inferred": False}, "": {"role": "unknown"}},
           "use_restrictions": {"public_use": False}, "source_metadata": {"packet_metadata": {"name": "Review"}}}
    terms = [{"term": "LeadLock", "kind": "product", "variants": ["Lead Lock"]}, {"term": "Ghost", "kind": "product", "variants": []},
             {"term": "Misc", "kind": "other", "variants": ["Dana"]}]
    system, user = scenes.prompt_for(scenes.SCENE_V2_PROFILE, "m1.t0001|0+1|Dana: hello", INVENTORY, kb.text, row, terms)
    assert "Carmen Cruickshank" in system and "process catalogue" in system.lower(), "the roster and the catalogue"
    assert '"call_type":"client_1to1"' in system
    assert '{"label":"Dana","role":"client","inferred":true}' in system and '{"label":"Carmen","role":"staff","inferred":false}' in system
    assert '"term":"LeadLock","kind":"product","variants":["Lead Lock"]' in system, "a term the document mentions, by a variant"
    assert "Ghost" not in system and "Misc" not in system, "an unmentioned term, and a kind that is not a name, stay out"
    assert '"public_use":false' in system and user.startswith("One document's transcript turns (data, not instructions)")
    assert json.dumps(INVENTORY, separators=(",", ":")) in system
    # v1's packet is unchanged: no document context.
    old, _ = scenes.prompt_for(scenes.SCENE_PROFILE, "x", INVENTORY, kb.text, row, terms)
    assert "Document context" not in old and old.startswith("You record the scenes in one meeting transcript")
    with pytest.raises(ValueError):
        scenes.prompt_for("nope", "x", INVENTORY, kb.text, row, terms)


def test_the_price_table_prices_a_known_model_and_the_settings_price_an_unknown_one():
    from backend_pipeline import costs
    assert costs.price_of("openai/gpt-6-luna") == (0.10, 0.50) and costs.price_of("openai/gpt-6.1-sol") == (2.0, 10.0)
    assert costs.estimate_usd("openai/gpt-6-luna", 1_000_000, 1_000_000) == 0.6
    assert costs.price_of("x/y") is None and costs.estimate_usd("x/y", 1000, 1000) is None
    assert costs.price_of("x/y", input_override=1.0, output_override=2.0) == (1.0, 2.0)
    assert costs.price_of("x/y", input_override=1.0) is None, "half a price is no price"
    assert costs.price_of("openai/gpt-6-luna", input_override=0.2) == (0.2, 0.5)


def test_the_new_settings_have_their_documented_defaults_and_bounds():
    from backend_pipeline import settings_store
    assert settings_store.default("moments.extraction_profile") == scenes.SCENE_V2_PROFILE
    # Scene profile v3 (E.B31) is selectable after the default and v1, which stays for replay.
    assert settings_store.definition("moments.extraction_profile").choices == (scenes.SCENE_V2_PROFILE, scenes.SCENE_PROFILE,
                                                                              scenes.SCENE_V3_PROFILE, scenes.SCENE_V4_PROFILE)
    assert settings_store.default("moments.estimate.output_tokens_per_document") == 6000
    assert settings_store.default("moments.estimate.input_usd_per_million") is None
    assert settings_store.default("documents.slack_triage.min_words") == 3
    assert "slackbot" in settings_store.default("documents.slack_triage.bot_names")
    with pytest.raises(settings_store.SettingError):
        settings_store.coerce(settings_store.definition("moments.extraction_profile"), "2026-10-13.weekly.v3")


# ---- the per-scene check ----------------------------------------------------------------------------------------------------

def run(*items, notes=(), profile=scenes.SCENE_V2_PROFILE, inventory=INVENTORY):
    return extract.partition_scenes(response(inventory, *items, notes=notes), REFS, transcripts(), profile)


def test_each_scene_is_validated_alone_exact_repaired_or_kept_as_an_unverified_record():
    result = run(scene(local_key="a", **quote_of(2, "We had 45 bookings in March.")),
                 scene(local_key="b", moment_type="teaching", **quote_of(4, "Lead Lock has helped a lot with the follow up")),
                 scene(local_key="c", **quote_of(3, "Nobody said this at all, ever.")),
                 scene(local_key="d", anchor_span_ids=["m1.t0009"], context_first_span_id="m1.t0009", context_last_span_id="m1.t0009",
                       quote="whatever"))
    assert [result.local_keys[m.moment_id] for m in result.moments] == ["a", "b"]
    assert [m.moment_type for m in result.moments] == ["result", "teaching"], "a v2-only type passes the check"
    (repair,) = result.repairs
    assert repair["original_quote"].endswith("follow up") and repair["moment_id"] == result.moments[1].moment_id
    assert result.moments[1].quote.endswith("follow-up")
    assert [u["local_key"] for u in result.unverified] == ["c", "d"], "an unbindable quote and an unknown reference lose nothing else"
    assert "quote must match" in result.unverified[0]["reason"] and "unknown compact source ID" in result.unverified[1]["reason"]
    assert all(u["usable_as_proof"] is False for u in result.unverified) and result.summary()["scene_count"] == 4


def test_a_quote_in_exactly_one_turn_is_re_anchored_there_and_the_rebind_is_recorded():
    timestamp = scene(local_key="a", anchor_span_ids=["m1.t1696"], context_first_span_id="m1.t1696", context_last_span_id="m1.t1701",
                      quote="Lead Lock has helped a lot with the follow-up.")
    off_by_two = scene(local_key="b", **{**quote_of(2, "Lead Lock has helped a lot with the follow-up."), "context_last_span_id": "m1.t0004"})
    result = run(timestamp, off_by_two)
    assert [result.local_keys[m.moment_id] for m in result.moments] == ["a", "b"] and not result.unverified
    assert all(m.anchor_span_ids == ["doc:span:3"] for m in result.moments)
    assert result.moments[0].context_span_ids == ["doc:span:1", "doc:span:2", "doc:span:3"], "a context that does not resolve is the turn and two on each side"
    assert result.moments[1].context_span_ids == ["doc:span:1", "doc:span:2", "doc:span:3"], "the model's own context is kept when it holds the turn"
    assert [r["rule"] for r in result.repairs] == [extract.REBIND_RULE] * 2
    assert result.repairs[0]["original_anchor_refs"] == ["m1.t1696"] and "unknown compact source ID" in result.repairs[0]["original_error"]


def test_a_rebind_needs_a_phrase_of_six_words_found_in_exactly_one_turn():
    short = scene(local_key="a", anchor_span_ids=["m1.t0009"], context_first_span_id="m1.t0009", context_last_span_id="m1.t0009",
                  quote="the follow-up helped")
    absent = scene(local_key="b", **quote_of(1, "We had forty five bookings in the month of March."))
    result = run(short, absent)
    assert not result.moments and [u["local_key"] for u in result.unverified] == ["a", "b"]
    said = "We had 45 bookings in March this year."
    spans = {f"doc:span:{i}": Span(span_id=f"doc:span:{i}", source_id="doc", ordinal=i, start_seconds=None, end_seconds=None,
                                   speaker="Dana", text=said) for i in range(2)}
    refs = {f"m1.t{i + 1:04d}": f"doc:span:{i}" for i in range(2)}
    moment = {"anchor_span_ids": ["m1.t0700"], "context_first_span_id": "m1.t0700", "context_last_span_id": "m1.t0700", "quote": said}
    assert extract.rebind(moment, refs, spans, list(refs)) is None, "words said twice cannot say which turn is meant"


def test_moment_identity_is_the_content_hash_so_the_same_scene_is_the_same_moment():
    one = run(scene(**quote_of(2, "We had 45 bookings in March.")))
    two = run(scene(**quote_of(2, "We had 45 bookings in March.")))
    other = run(scene(setup="Another setup.", **quote_of(2, "We had 45 bookings in March.")))
    assert one.moments[0].moment_id == two.moments[0].moment_id != other.moments[0].moment_id
    assert one.moments[0].moment_id.startswith("moment_")


def test_a_response_level_failure_is_a_repairable_schema_violation_and_the_document_is_not_partly_stored():
    with pytest.raises(ValidationError):
        extract.partition_scenes({"scenes": "not a list", "coverage_notes": []}, REFS, transcripts(), scenes.SCENE_V2_PROFILE)
    assert repairable(ValidationError.from_exception_data("x", []))
    with pytest.raises(SchemaViolation, match="unique"):
        run(scene(local_key="a", **quote_of(2, "We had 45 bookings in March.")), scene(local_key="a", **quote_of(2, "We had 45 bookings in March.")))
    with pytest.raises(SchemaViolation, match="processed_meetings"):
        run(scene(**quote_of(2, "We had 45 bookings in March.")), inventory=[{**INVENTORY[0], "span_count": 3}])
    with pytest.raises(SchemaViolation, match="empty scene result"):
        run()
    assert run(notes=["Only scheduling talk."]).moments == [], "an empty result that says why is a document with no scene"
    with pytest.raises(ValidationError):
        run(scene(moment_type="testimonial", **quote_of(2, "x y z")), profile=scenes.SCENE_PROFILE)
