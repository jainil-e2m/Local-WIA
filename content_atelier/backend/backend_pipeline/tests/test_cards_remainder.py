"""E.B16 (l) to (p): the cutoff is a setting, a deferred CTA blocks Gate 2 and exports, CLI submits freeze the
profile, a changed vector names the angle and the re-encode step, and the preflight accepts Sol. Offline."""
from __future__ import annotations

import hashlib
import inspect

import pytest

from backend_pipeline import matching, storage_cli
from backend_pipeline.briefs import gate_two
from backend_pipeline.matching import card_visibility, duplicate_cosine, pause_message
from backend_pipeline.llm import chat_body
from backend_pipeline.store import JsonStore
from backend_pipeline.token_budget import SOL_MANIFEST, SOL_MODEL, preflight

CARDS = [{"angle_id": "a", "rank": 1}, {"angle_id": "b", "rank": 2}]
PAIRS = {"b": [{"angle_id": "a", "cosine": 0.85}], "a": [{"angle_id": "b", "cosine": 0.85}]}


def test_the_week2_buying_research_pair_collapses_at_the_calibrated_cutoff(monkeypatch):
    # E.B6: the two Week 2 buying-research angles (angle_1d20dd13..., angle_7105aba8...) are 0.8674 apart; 0.90 let them through.
    monkeypatch.delenv("ATELIER_DUPLICATE_COSINE", raising=False)
    pair = {"b": [{"angle_id": "a", "cosine": 0.8674}], "a": [{"angle_id": "b", "cosine": 0.8674}]}
    assert card_visibility(CARDS, pair)["b"]["duplicate_of"] == "a"


def test_the_duplicate_cutoff_is_read_from_a_setting(monkeypatch):
    monkeypatch.delenv("ATELIER_DUPLICATE_COSINE", raising=False)
    assert duplicate_cosine() == 0.86
    assert card_visibility(CARDS, PAIRS)["b"]["selection_status"] == "visible", "0.85 is below the default cutoff"
    monkeypatch.setenv("ATELIER_DUPLICATE_COSINE", "0.80")
    assert duplicate_cosine() == 0.80
    collapsed = card_visibility(CARDS, PAIRS)["b"]
    assert collapsed == {"selection_status": "suppressed", "reason": "duplicate", "duplicate_of": "a", "cosine": 0.85}
    monkeypatch.setenv("ATELIER_DUPLICATE_COSINE", "1.5")
    with pytest.raises(ValueError, match="between 0.5 and 1.0"):
        duplicate_cosine()


def test_no_hard_coded_cutoff_decides_card_collapse():
    source = inspect.getsource(matching.card_visibility) + inspect.getsource(matching.assess)
    assert ">=DUPLICATE_COSINE" not in source.replace(" ", "")


def test_a_deferred_cta_blocks_gate_two_and_the_export_renders_it():
    from backend_pipeline.briefs.validation import checks
    from backend_pipeline.tests.test_phase_s import document as brief_document, dossier as brief_dossier
    deferred = {"choice": "decide_in_development"}
    d = brief_dossier()
    d.angle["cta"] = deferred
    document = brief_document(d)
    document["cta"] = deferred
    messages = [f["message"] for f in checks(document, d) if f["severity"] == "blocking"]
    assert any("decide in development" in m for m in messages)
    row = {"content_body": {"document": document, "review": {"findings": []}}, "selected_evidence": [],
           "prior_content_context": [], "research_gaps": {"items": []}}
    assert "Decide in development (not yet confirmed by a person)" in gate_two.markdown(row)


def test_cli_submit_freezes_the_profile_and_models():
    source = inspect.getsource(storage_cli.main)
    assert "repo.submit(args.week_id,args.mode,workflow=args.workflow,models=models)" in source


def test_a_changed_vector_pause_names_the_angle_and_the_re_encode_step():
    message = pause_message({"status": "incomplete", "problems": ["angle_abc", "angle_def:future_generation"]}, "fallback")
    assert "angle_abc" in message and "Re-encode" in message and "storage_cli encode" in message
    assert "angle_def" in message and "new reassessment" in message
    assert pause_message({"status": "incomplete", "angles": []}, "fallback") == "fallback"


def test_the_compact_weekly_preflight_accepts_sol(tmp_path):
    store = JsonStore(tmp_path)
    store.write_json("route.json", {"data": {"id": SOL_MODEL, "endpoints": [
        {"context_length": 1050000, "max_prompt_tokens": 922000, "max_completion_tokens": 128000,
         "supported_parameters": ["max_tokens", "response_format", "reasoning"]}]}})
    store.write_json(SOL_MANIFEST, {"model": SOL_MODEL, "route_snapshot": "route.json",
                                    "route_sha256": hashlib.sha256(store.path("route.json").read_bytes()).hexdigest()})
    body = chat_body(model=SOL_MODEL, system="Trusted.", user="Scenes", schema={}, max_tokens=65536,
                     reasoning_effort="high", response_format="json_object")
    report = preflight(body, tmp_path)
    assert report["model"] == SOL_MODEL and report["fits"] and not report["native_token_count_available"]
    huge = chat_body(model=SOL_MODEL, system="Trusted.", user="A" * 3100000, schema={}, max_tokens=65536)
    assert preflight(huge, tmp_path)["fits"] is False


def test_profile_v3_is_refused_for_new_live_runs_and_kept_for_replay():
    from backend_pipeline.angle_profiles import STRATEGIST_PROFILE, STRATEGIST_V4_PROFILE, check_live_profile
    with pytest.raises(ValueError, match="replay only"):
        check_live_profile(STRATEGIST_PROFILE, "live")
    for mode in ("replay", "synthetic", "fake"):
        check_live_profile(STRATEGIST_PROFILE, mode)
    # Version 4's user message carries all six Reel scripts, and Reel 5 derives from held-out Week 6 (E.B17): it
    # replays its saved runs, and a new live run uses version 5.
    with pytest.raises(ValueError, match="Week 6"):
        check_live_profile(STRATEGIST_V4_PROFILE, "live")
    check_live_profile(STRATEGIST_V4_PROFILE, "replay")
    from backend_pipeline.angle_profiles import STRATEGIST_V5_PROFILE
    check_live_profile(STRATEGIST_V5_PROFILE, "live")


def test_the_sql_worker_refuses_a_live_run_on_a_replay_only_profile_however_it_was_submitted():
    """E.B17: submit checks the profile when it is given the models; a live run queued without them (a script, an older
    caller) must still be refused by the worker before extraction, not run on the worker's replay-only profile."""
    from types import SimpleNamespace
    from backend_pipeline.angle_profiles import STRATEGIST_PROFILE, STRATEGIST_V4_PROFILE, STRATEGIST_V5_PROFILE
    from backend_pipeline.config import Settings
    from backend_pipeline.sql_pipeline import SQLWorker
    for profile in (STRATEGIST_PROFILE, STRATEGIST_V4_PROFILE):
        worker = SimpleNamespace(models=Settings(angle_prompt_profile=profile))
        with pytest.raises(ValueError, match="replay only|Week 6"):
            SQLWorker.frozen_profile(worker, {"input_refs": {"mode": "live"}})
        assert SQLWorker.frozen_profile(worker, {"input_refs": {"mode": "replay"}}) == profile
    worker = SimpleNamespace(models=Settings(angle_prompt_profile=STRATEGIST_V5_PROFILE))
    assert SQLWorker.frozen_profile(worker, {"input_refs": {"mode": "live"}}) == STRATEGIST_V5_PROFILE


def test_the_file_pipeline_refuses_a_live_v3_run_before_any_call(tmp_path):
    from backend_pipeline.angle_profiles import STRATEGIST_PROFILE
    from backend_pipeline.config import Settings
    from backend_pipeline.pipeline import Pipeline
    settings = Settings(data_root=tmp_path, angle_prompt_profile=STRATEGIST_PROFILE)
    with pytest.raises(ValueError, match="replay only"):
        Pipeline(settings).run(1, mode="live")


def test_consent_stricter_than_the_label_decides_what_the_strategist_and_verifier_see():
    """E.B16 f, R40: do_not_use never reaches a model; internal_only consent is internal however the extractor labelled
    the scene; the verifier and Gate 1 block a public card that cites either."""
    from backend_pipeline import gate_one
    from backend_pipeline.cycle import verification as v
    from backend_pipeline.sql_pipeline import consented
    saved = {"a": {"moment_body": {"sensitivity": "public_candidate", "quote": "q"}, "consent_status": "cleared"},
             "b": {"moment_body": {"sensitivity": "public_candidate", "quote": "q"}, "consent_status": "internal_only"},
             "c": {"moment_body": {"sensitivity": "public_candidate", "quote": "q"}, "consent_status": "do_not_use"},
             "d": {"moment_body": {"sensitivity": "unknown", "quote": "q"}}}
    bodies, dropped = consented(saved, ["a", "b", "c", "d"])
    assert set(bodies) == {"a", "b", "d"} and [d["moment_id"] for d in dropped] == ["c"]
    assert bodies["b"]["sensitivity"] == "internal_only" and bodies["a"]["sensitivity"] == "public_candidate"
    assert saved["b"]["moment_body"]["sensitivity"] == "public_candidate", "the stored row is not changed"
    assert v.moment_handling(saved["c"]) == "do_not_use" and v.moment_handling(saved["b"]) == "internal_only"
    assert v.moment_handling(saved["a"]) == "public_candidate" and v.moment_handling(saved["d"]) == "unknown"
    card = {"title": "t", "core_perspective": "p", "why_it_matters": "w", "wia_in_action": "WIA view (knowledge base): x",
            "evidence_points": [], "moment_ids": ["c"], "verify_before_publishing": []}
    ledger = v.verify_card(card, {"c": []}, [], [], sensitivity={"c": "do_not_use"})
    assert [f["kind"] for f in v.blocking(ledger)] == ["do_not_use_scene"]
    with pytest.raises(ValueError, match="asked not to be used"):
        gate_one.check_card_approval(card, [f["id"] for f in v.blocking(ledger)], {"c": "do_not_use"}, ledger, "Checked")
