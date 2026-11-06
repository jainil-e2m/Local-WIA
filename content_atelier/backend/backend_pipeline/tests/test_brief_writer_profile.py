"""E.B22: the v2 contract's writer prompt is a setting, frozen with each run, and runs queued before it keep their contract."""
import json
from types import SimpleNamespace

import pytest

from backend_pipeline import settings_store
from backend_pipeline.briefs import runtime
from backend_pipeline.briefs.contracts_v2 import SCHEMA_V2, BriefBodyV2
from backend_pipeline.config import Settings
from backend_pipeline.llm.request import canonical_hash
from backend_pipeline.storage_config import StorageSettings


def test_the_writer_setting_defaults_to_the_released_prompt_and_offers_v3_and_v4():
    d = settings_store.definition("prompts.profile.brief_writer")
    assert d.default == "v2" and set(d.choices) == {"v2", "v3", "v4", "v4.1", "v5", "v5.1", "v5.2", "v5.3"}, "v4 and v4.1 (5.B6) write contract v3 (E.B23), v5, v5.1 (NP.B10), v5.2 (N8) and v5.3 (Round 2) contract v4 (E.B33); the default is unchanged"
    assert StorageSettings().brief_writer == "v2"


def test_v3_selects_its_own_writer_and_repair_prompts_and_shares_plan_and_grade():
    v2, v3 = (runtime.system("brief_write", SCHEMA_V2, "KB", w) for w in ("v2", "v3"))
    assert v2.startswith("KB") and v3.startswith("KB"), "the knowledge base stays the trusted prefix"
    assert "Two kinds of text" in v3 and "Two kinds of text" not in v2
    assert "never by adding a caveat" in runtime.system("brief_repair", SCHEMA_V2, "KB", "v3")
    assert "never by adding a caveat" not in runtime.system("brief_repair", SCHEMA_V2, "KB", "v2")
    for stage in ("brief_plan", "brief_grade"):
        assert runtime.system(stage, SCHEMA_V2, None, "v3") == runtime.system(stage, SCHEMA_V2, None, "v2")


def _worker(monkeypatch, writer="v2"):
    kb = SimpleNamespace(text="# WIA KNOWLEDGE BASE\n\nVoice guide line.", refs=lambda: {"version": "kb-test"})
    monkeypatch.setattr(runtime, "knowledge", lambda worker, run=None: kb)
    return SimpleNamespace(models=Settings(), storage=StorageSettings(brief_model="m", brief_review_model="m", brief_writer=writer))


def test_a_run_freezes_its_writer_and_a_run_queued_before_the_setting_keeps_its_contract(monkeypatch):
    worker = _worker(monkeypatch, writer="v3")
    old = runtime.execution_contract(worker, SCHEMA_V2, {"input_refs": {"schema_version": SCHEMA_V2}})
    assert "writer" not in old, "a run queued before E.B22 keeps the contract it was frozen with"
    assert old["prompt_hashes"]["brief_write"] == canonical_hash(runtime.system("brief_write", SCHEMA_V2, "{knowledge base}", "v2"))
    new = runtime.execution_contract(worker, SCHEMA_V2, {"input_refs": {"schema_version": SCHEMA_V2, "writer": "v3"}})
    assert new["writer"] == "v3"
    assert new["prompt_hashes"]["brief_write"] == canonical_hash(runtime.system("brief_write", SCHEMA_V2, "{knowledge base}", "v3"))
    assert new["prompt_hashes"]["brief_write"] != old["prompt_hashes"]["brief_write"]
    assert new["prompt_hashes"]["brief_plan"] == old["prompt_hashes"]["brief_plan"]


def test_the_call_sends_the_frozen_writer_not_the_current_setting(monkeypatch):
    worker = _worker(monkeypatch, writer="v2")
    sent = []
    monkeypatch.setattr(runtime, "check_dependencies", lambda worker, run: None)
    monkeypatch.setattr(runtime, "chat", lambda *a, **k: sent.append(k["request"]) or "written")
    run = {"run_id": "r", "input_refs": {"schema_version": SCHEMA_V2, "mode": "replay", "writer": "v3"}}
    assert runtime.call(worker, {}, run, "brief_write", BriefBodyV2, {"evidence": ["e"]}, {"type": "object"}) == "written"
    assert "Two kinds of text" in json.dumps(sent[0], ensure_ascii=False)


@pytest.mark.parametrize("value", ["v1", "v6", ""])
def test_an_unknown_writer_is_refused(value):
    with pytest.raises(settings_store.SettingError):
        settings_store.coerce(settings_store.definition("prompts.profile.brief_writer"), value)
