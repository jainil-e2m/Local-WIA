"""E.B31: scene profile v3 (human lines and counter-expected decisions), offline: template, contract, provenance, the
verbatim check and the type rule. v2 stays for replay and stays the default. Invented text only."""
from __future__ import annotations

import hashlib
import sys

import pytest
from pydantic import ValidationError

from backend_pipeline import settings_store
from backend_pipeline.config import BACKEND_ROOT, PROJECT_ROOT, Settings
from backend_pipeline.moments import extract, scenes, types
from backend_pipeline.search.filters import MOMENT_TYPES, SearchFilters
from backend_pipeline.tests.moments_fixtures import response, scene
from backend_pipeline.tests.test_moments_scenes import INVENTORY, REFS, quote_of, transcripts

V2 = scenes.TEMPLATE_V2.read_text(encoding="utf-8")
V3 = scenes.TEMPLATE_V3.read_text(encoding="utf-8")


def v3_scene(**changes):
    return scene(**{"departure": None, **changes})


def run(*items):
    return extract.partition_scenes(response(INVENTORY, *items), REFS, transcripts(), scenes.SCENE_V3_PROFILE)


def test_v3_keeps_v2_and_adds_the_two_kinds_with_invented_examples():
    assert hashlib.sha256(V2.replace("\r\n", "\n").encode()).hexdigest() == \
        "796e52cff6ea71f237532d3d231d721390971474213006a48b2e2e9592b530de", "v2 stays byte for byte for replay"
    text = V3.lower()
    for rule in ("a human line", "a counter-expected decision", "word for word", "costs wia something", "departure",
                 "human_line", "counter_expected_decision", "do not interpret"):
        assert rule in text, rule
    for example in scenes.SCENE_V3_EXAMPLES:
        assert example["derived_from_weeks"] == [] and example["text"].lower() in text, example["text"]
    sys.path.insert(0, str(PROJECT_ROOT / "research" / "chatgpt-export-2026-10-18"))
    try:
        from lint import lint
    finally:
        sys.path.pop(0)
    assert lint(V3) == []


def test_v3_is_selectable_for_documents_and_cycles_but_v2_stays_the_default():
    assert settings_store.default("moments.extraction_profile") == scenes.SCENE_V2_PROFILE == settings_store.default("prompts.profile.extraction")
    assert scenes.SCENE_V3_PROFILE in settings_store.definition("moments.extraction_profile").choices
    assert Settings(extraction_profile=scenes.SCENE_V3_PROFILE).extraction_profile == scenes.SCENE_V3_PROFILE
    assert scenes.PROFILES[scenes.SCENE_V3_PROFILE]["types"] == types.MOMENT_TYPES + types.SCENE_V3_TYPES
    assert set(types.SCENE_V3_TYPES) <= set(MOMENT_TYPES), "the ledger filters on the new types"
    SearchFilters(moment_type=["human_line", "counter_expected_decision"])


def test_the_v3_prompt_is_v2s_packet_under_the_v3_template():
    record = {"call_type": "client_1to1", "speaker_map": {}, "original_text": "", "use_restrictions": {}, "source_metadata": {}}
    v2_system, v2_user = scenes.prompt_for(scenes.SCENE_V2_PROFILE, "PACKET", INVENTORY, "KB", record, [])
    v3_system, v3_user = scenes.prompt_for(scenes.SCENE_V3_PROFILE, "PACKET", INVENTORY, "KB", record, [])
    assert v3_user == v2_user and v3_system.startswith(V3.strip())
    assert v3_system.removeprefix(V3.strip()) == v2_system.removeprefix(V2.strip())
    assert "departure" in scenes.schema(scenes.SCENE_V3_PROFILE)["$defs"]["SceneDraftV3"]["required"]
    assert "departure" not in str(scenes.schema(scenes.SCENE_V2_PROFILE)), "v2's schema is unchanged"


def test_the_new_kinds_are_checked_verbatim_against_the_transcript_like_every_scene():
    human = v3_scene(local_key="h", moment_type="human_line", **quote_of(4, "Lead Lock has helped a lot with the follow-up."))
    invented = v3_scene(local_key="x", moment_type="human_line", **quote_of(4, "Honestly, I dread every Monday."))
    decision = v3_scene(local_key="d", moment_type="counter_expected_decision", **quote_of(3, "Great, the follow-up helped."),
                        wia_moves=[{"speaker": "Carmen Cruickshank", "move": "recommended", "what": "Keep the budget as it is"}],
                        departure="The client asked to spend more; the strategist recommended spending the same.")
    result = run(human, invented, decision)
    assert [(result.local_keys[m.moment_id], m.moment_type) for m in result.moments] == [
        ("h", "human_line"), ("d", "counter_expected_decision")]
    assert [u["local_key"] for u in result.unverified] == ["x"] and "quote must match" in result.unverified[0]["reason"]
    stored = next(m for m in result.moments if m.moment_type == "counter_expected_decision")
    assert "Against the default: The client asked to spend more" in stored.proposition
    assert not result.retyped


def test_a_counter_expected_decision_without_its_move_or_departure_is_kept_as_a_decision():
    no_move = v3_scene(local_key="a", moment_type="counter_expected_decision", **quote_of(3, "Great, the follow-up helped."),
                       departure="It cost WIA an upsell.")
    no_departure = v3_scene(local_key="b", moment_type="counter_expected_decision", **quote_of(2, "We had 45 bookings in March."),
                            wia_moves=[{"speaker": "Carmen Cruickshank", "move": "decided", "what": "Hold the budget"}])
    raw = response(INVENTORY, no_move, no_departure)
    result = extract.partition_scenes(raw, REFS, transcripts(), scenes.SCENE_V3_PROFILE)
    assert [m.moment_type for m in result.moments] == ["decision", "decision"]
    assert [(r["local_key"], r["reason"]) for r in result.retyped] == [("a", "no WIA move decides or recommends"),
                                                                        ("b", "no departure recorded")]
    assert result.summary()["retyped_scenes"] == result.retyped
    assert raw["scenes"][0]["moment_type"] == "counter_expected_decision", "the provider's output is never changed"


def test_v2_rejects_the_new_kinds_and_v3_requires_the_departure_field():
    with pytest.raises(ValidationError):
        extract.partition_scenes(response(INVENTORY, scene(moment_type="human_line", **quote_of(2, "We had 45 bookings in March."))),
                                 REFS, transcripts(), scenes.SCENE_V2_PROFILE)
    with pytest.raises(ValidationError):
        run(scene(moment_type="human_line", **quote_of(2, "We had 45 bookings in March.")))


def test_the_re_extraction_command_is_documented_with_its_estimate():
    readme = (BACKEND_ROOT / "docs" / "Angle-Prompt-Profiles.md").read_text(encoding="utf-8")
    assert "moments extract" in readme and scenes.SCENE_V3_PROFILE in readme and "--estimate" in readme
