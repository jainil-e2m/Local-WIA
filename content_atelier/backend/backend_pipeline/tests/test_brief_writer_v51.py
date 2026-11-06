"""NP.B10 offline: brief writer v5.1 writes three Reels (story, stance, b-roll text) with contract v4, selected by setting;
writer v5's request (prompt, wire schema, execution contract) stays byte for byte what N2 recorded, so its saved answers
replay at USD 0; a v5.1 brief's Reels map straight to the pack's reel_1, reel_2 and reel_3. No database, no model call."""
from __future__ import annotations

import copy
from pathlib import Path
from types import SimpleNamespace

import pytest

from backend_pipeline import settings_store
from backend_pipeline.briefs import first_touch, runtime
from backend_pipeline.briefs.contracts_v4 import (SCHEMA_V4, BriefWriteV4, BriefWriteV51, writer_part_v4, writer_schema_v4,
                                                 writer_schema_v51)
from backend_pipeline.briefs.validation_v3 import contract_for
from backend_pipeline.briefs.validation_v4 import checks_v4
from backend_pipeline.briefs.workflow import writer_for
from backend_pipeline.config import BACKEND_ROOT, Settings
from backend_pipeline.cycle.verification import load_rules
from backend_pipeline.packs import assemble
from backend_pipeline.storage_config import StorageSettings
from backend_pipeline.store import canonical_hash
from backend_pipeline.tests.brief_v4_fixtures import v4_body
from backend_pipeline.tests.pack_v2_fixtures import brief_row, handoff_v2
from backend_pipeline.tests.test_brief_v3 import dossier, packet, provenance
from backend_pipeline.tests.test_brief_v4 import document

TEMPLATES = Path(__file__).resolve().parents[1] / "prompt_templates"
CHANNELS = ["reel", "carousel", "email", "caption"]
THREE = ["story", "stance", "broll_text"]


def _worker(monkeypatch, writer):
    kb = SimpleNamespace(text="KB", refs=lambda: {"version": "kb-test"})
    monkeypatch.setattr(runtime, "knowledge", lambda worker, run=None, stage="brief": kb)
    monkeypatch.setattr(first_touch, "pinned_data", lambda root: {"insider_terms": {}, "offer_descriptors": {}})
    return SimpleNamespace(models=Settings(), storage=StorageSettings(brief_model="m", brief_review_model="m", brief_writer=writer))


def _contract(monkeypatch, writer):
    return runtime.execution_contract(_worker(monkeypatch, writer), SCHEMA_V4,
                                      {"input_refs": {"schema_version": SCHEMA_V4, "writer": writer}})


# Writer v5 is unchanged ---------------------------------------------------------------------------------------------

def test_writer_v5s_request_is_pinned_because_n2s_saved_answers_replay_only_under_it():
    """A v5 brief's call is fingerprinted on its prompt and wire schema: a change to either voids N2's saved answers and
    every v5 replay pays again. Writer v5.1 has its own file, model and schema; these hashes are the ones on main before it
    (6a89b75) and change only with a note in the record."""
    assert canonical_hash(runtime.system("brief_write", SCHEMA_V4, "{knowledge base}", "v5")) == \
        "6525a769166119ca07552cc4af8112d3b439d6b989a12243b4c4a5982c47ef30"
    assert canonical_hash(runtime.system("brief_repair", SCHEMA_V4, "{knowledge base}", "v5")) == \
        "cafde953aafa38ffd1de819a7d7653014fd0acc1d1f375c5130016aebe5280dc"
    assert canonical_hash(BriefWriteV4.model_json_schema()) == "eb069fe23627a86e354f4690007ff302b86431a80d280120b144647381077e3a"
    assert {",".join(c): canonical_hash(writer_schema_v4(c)) for c in (CHANNELS, ["reel", "email"], ["carousel", "email"])} == {
        "reel,carousel,email,caption": "ac3a099edea80b67f0fe50e782db4de767228820b15a62483a384d2f54e29b77",
        "reel,email": "fd48c94670f6cfc64fe6e278ef3965c75dea94e2d3af2077e8fab86bf478167c",
        "carousel,email": "512083d57e03ece389f63a4bafba91505f5ca1a8b3a538dd2f095e92fd7ed5d1"}
    v5 = contract_for(SCHEMA_V4, "v5")
    assert v5.write is BriefWriteV4 and v5.wire is writer_schema_v4, "a v5 run writes and repairs under v5's schema"
    assert contract_for(SCHEMA_V4).write is BriefWriteV4 and contract_for(SCHEMA_V4).wire is writer_schema_v4


def test_writer_v5s_execution_contract_hashes_are_pinned(monkeypatch):
    """A run whose frozen contract differs from the current one fails (CONTEXT_CHANGED): v5's prompt and schema hashes
    are what N2's runs froze."""
    contract = _contract(monkeypatch, "v5")
    assert contract["writer"] == "v5"
    assert canonical_hash(contract["prompt_hashes"]) == "c582da6d5237d1e49bfb4f2c1ff732e0bec04d111dd28d3d0ccb77e3d2d207bf"
    assert canonical_hash(contract["schema_hashes"]) == "2d3f977c627a90286c66681ab37d91699b32f8659f370120aa672ffe67464ab9"


# Writer v5.1 --------------------------------------------------------------------------------------------------------

def test_writer_v51_is_a_new_file_that_is_v5_but_for_the_three_reels():
    v5 = (TEMPLATES / "brief_write.v5.md").read_text(encoding="utf-8")
    v51 = (TEMPLATES / "brief_write.v5.1.md").read_text(encoding="utf-8")
    head, tail = "## The idea, through different doors", "## Two kinds of text"
    assert v51.split(head)[0] == v5.split(head)[0] and v51.split(tail)[1] == v5.split(tail)[1], "the rest of v5 is unchanged"
    doors = v51.split(head)[1].split(tail)[0]
    assert "Write two Reels" not in doors and "Write two Reels" in v5
    assert "write exactly three Reels, one of each kind, in this order: `story`, `stance`, `broll_text`" in doors
    assert "Whitney's stance on the same central point" in doors and "never a sub-lesson" in doors
    assert "one to three screens and no script" in doors and "so a cold viewer follows it from the screens alone" in doors
    assert "{{#revision_instructions}}" in v51 and "{{#locked_fields}}" in v51


def test_writer_v51_is_selected_by_setting_with_contract_v4_and_repairs_with_repair_v5():
    assert settings_store._BY_KEY["prompts.profile.brief_writer"].default == "v2", "the code default is unchanged"
    settings_store.validate_profile({"settings": {"prompts.profile.brief": SCHEMA_V4, "prompts.profile.brief_writer": "v5.1"}})
    with pytest.raises(ValueError):
        settings_store.validate_profile({"settings": {"prompts.profile.brief": "brief_document_v3", "prompts.profile.brief_writer": "v5.1"}})
    assert writer_for(StorageSettings(brief_writer="v5.1"), SCHEMA_V4) == "v5.1"
    assert writer_for(StorageSettings(brief_writer="v5.1"), SCHEMA_V4, revision="brief_x") == "v5.1"
    assert writer_for(StorageSettings(brief_writer="v5"), SCHEMA_V4, revision="brief_x") == "v5"
    assert writer_for(StorageSettings(brief_writer="v4"), SCHEMA_V4, revision="brief_x") == "v5", "v5.1 only where the setting names it"
    assert runtime.RENDERED_WRITERS["v5.1"] == "v5"
    assert runtime.system("brief_repair", SCHEMA_V4, "KB", "v5.1") == runtime.system("brief_repair", SCHEMA_V4, "KB", "v5")
    first = runtime.system("brief_write", SCHEMA_V4, "KB", "v5.1", {"revision_instructions": "", "locked_fields": []})
    assert first.startswith("KB") and "exactly three Reels" in first and "{{#" not in first


def test_writer_v51s_execution_contract_names_its_own_prompt_and_schema(monkeypatch):
    v5, v51 = _contract(monkeypatch, "v5"), _contract(monkeypatch, "v5.1")
    assert v51["writer"] == "v5.1"
    assert v51["prompt_hashes"]["brief_write"] == canonical_hash(runtime.system("brief_write", SCHEMA_V4, "{knowledge base}", "v5.1"))
    assert v51["prompt_hashes"]["brief_write"] != v5["prompt_hashes"]["brief_write"]
    assert v51["schema_hashes"]["brief_write"] == v51["schema_hashes"]["brief_repair"] == canonical_hash(BriefWriteV51.model_json_schema())
    for stage in ("brief_plan", "brief_grade", "brief_verify"):
        assert v51["prompt_hashes"][stage] == v5["prompt_hashes"][stage] and v51["schema_hashes"][stage] == v5["schema_hashes"][stage]
    assert v51["prompt_hashes"]["brief_repair"] == v5["prompt_hashes"]["brief_repair"]


def _with_reels(kinds, **change):
    body = v4_body(packet())
    by_kind = {r["kind"]: r for r in body["format_plan"]["reels"]}
    body["format_plan"]["reels"] = [{**copy.deepcopy(by_kind[k]), **change.get(k, {})} for k in kinds]
    return body


def test_writer_v51s_answer_needs_the_three_kinds_in_order():
    BriefWriteV51.model_validate(_with_reels(THREE))
    BriefWriteV51.model_validate(_with_reels([]))  # no reel channel, no Reels
    for kinds in (["story", "stance"], ["story", "broll_text"], ["stance", "story", "broll_text"], ["story", "stance", "stance"]):
        with pytest.raises(ValueError, match="story, stance and broll_text"):
            BriefWriteV51.model_validate(_with_reels(kinds))
        BriefWriteV4.model_validate(_with_reels(kinds))  # writer v5's answer is not held to it
    with pytest.raises(ValueError, match="broll_text Reel"):
        BriefWriteV51.model_validate(_with_reels(THREE, broll_text={"script": "A script it must not have."}))
    with pytest.raises(ValueError, match="broll_text Reel"):
        BriefWriteV51.model_validate(_with_reels(THREE, broll_text={"screens": None}))


def test_writer_v51s_wire_schema_asks_for_three_reels_only_with_the_reel_channel():
    schema = writer_schema_v51(CHANNELS)
    reels = schema["$defs"]["FormatPlanV4"]["properties"]["reels"]
    assert reels["minItems"] == reels["maxItems"] == 3 and "story, stance, broll_text" in reels["description"]
    assert writer_schema_v51(["carousel", "email"])["$defs"]["FormatPlanV4"]["properties"]["reels"]["maxItems"] == 0
    assert schema["title"] == "BriefWriteV51"
    assert "minItems" not in writer_schema_v4(CHANNELS)["$defs"]["FormatPlanV4"]["properties"]["reels"]
    c = contract_for(SCHEMA_V4, "v5.1")
    assert c.write is BriefWriteV51 and c.wire is writer_schema_v51 and c.part is writer_part_v4, "a repair keeps the three Reels"


def test_the_checks_hold_a_v51_brief_to_its_three_reels_after_a_persons_edit():
    rules = load_rules(BACKEND_ROOT / "knowledge_base")
    message = "Writer v5.1 writes three Reels"
    two, _ = document(_with_reels(["story", "broll_text"]))
    assert any(message in f["message"] and f["severity"] == "warning" for f in checks_v4(two, dossier(), {**provenance(), "writer": "v5.1"}, None, rules))
    assert not any(message in f["message"] for f in checks_v4(two, dossier(), provenance(), None, rules)), "a v5 brief may have two"
    three, _ = document()
    assert not any(message in f["message"] for f in checks_v4(three, dossier(), {**provenance(), "writer": "v5.1"}, None, rules))


# The pack -----------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("mode", ["finish", "missing_only", "assemble"])
def test_a_v51_briefs_three_reels_map_straight_to_the_packs_reels_with_none_written(mode):
    row = brief_row()
    row["content_body"]["provenance"] = {"writer": "v5.1"}
    body = row["content_body"]["document"]["body"]
    BriefWriteV51.model_validate(writer_part_v4(body))
    assert [r["kind"] for r in body["format_plan"]["reels"]] == THREE
    plan = assemble.draft(handoff_v2(row), finish_mode=mode)
    assert {k: plan["brief_map"][k] for k in ("reel_1", "reel_2", "reel_3")} == {"reel_1": "reel_1", "reel_2": "reel_2", "reel_3": "reel_3"}
    assert plan["missing"] == [] and plan["sources"] == {}, "no Reel kind is left for the finisher to write"
    for key, kind in zip(("reel_1", "reel_2", "reel_3"), THREE):
        assert plan["pieces"][key]["origin"] == "brief" and plan["pieces"][key]["content"]["kind"] == kind
