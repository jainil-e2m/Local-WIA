from __future__ import annotations

import hashlib
import json

import pytest

from backend_pipeline.llm import stage as stage_module
from backend_pipeline.config import Settings
from backend_pipeline.costs import call_record, reported_cost
from backend_pipeline.pipeline import Pipeline
from backend_pipeline.llm import chat_body
from backend_pipeline.store import JsonStore
from backend_pipeline.tests.test_generation_only import CompactCountingProvider
from backend_pipeline.token_budget import LUNA_MANIFEST, LUNA_MODEL, preflight


class PaidMockProvider(CompactCountingProvider):
    """Synthetic billed usage only: no real API/key/transcript or payment."""

    bad_quote = False
    timeout = False

    def json_call(self, **kwargs):
        if self.timeout:
            raise TimeoutError("Synthetic unknown provider outcome")
        output, meta = super().json_call(**kwargs)
        if self.bad_quote and kwargs["stage"] == "moment_extraction":
            output["moments"][0]["quote"] = "Fabricated quotation."
        meta["raw"].update(
            model=LUNA_MODEL,
            provider="synthetic-mock",
            usage={
                "prompt_tokens": 1000,
                "completion_tokens": 100,
                "total_tokens": 1100,
                "cost": 0.012 if kwargs["stage"] == "moment_extraction" else 0.006,
                "prompt_tokens_details": {"cached_tokens": 150},
                "completion_tokens_details": {"reasoning_tokens": 30},
                "cost_details": {"upstream_inference_cost": 0.01},
            },
        )
        meta["raw"]["choices"][0]["message"]["content"] = json.dumps(output)
        return output, meta


@pytest.fixture
def paid_harness(tmp_path, monkeypatch):
    week = tmp_path / "inputs" / "week1"
    week.mkdir(parents=True)
    (week / "meeting.vtt").write_text(
        "WEBVTT\n\n00:00:00.000 --> 00:00:05.000\nWhitney: A useful reply helps couples compare venues.\n\n"
        "00:00:05.000 --> 00:00:09.000\nWhitney: This is not a measured result.\n",
        encoding="utf-8",
    )
    settings = Settings(
        data_root=tmp_path / "data",
        transcript_root=tmp_path / "inputs",
        llm_payload_format="compact_weekly",
        live_enabled=True,
        openrouter_moments_key="synthetic-only",
        openrouter_angles_key="synthetic-only",
        llm_completion_tokens=65536,
        llm_reasoning_effort="low",
        llm_response_format="json_object",
    )
    monkeypatch.setattr(stage_module, "preflight", lambda *args: {"fits": True})
    provider = PaidMockProvider()
    return settings, provider, Pipeline(settings, provider)


@pytest.mark.parametrize('model', [LUNA_MODEL, 'openai/gpt-6-luna-pro', 'openai/gpt-6.1-sol'])
def test_luna_body_omits_unsupported_temperature_and_requests_usage(model):
    body = chat_body(
        model=model,
        system="Trusted.",
        user="Source.",
        schema={},
        response_format="json_object",
        max_tokens=65536,
        reasoning_effort="low",
    )
    assert "temperature" not in body
    assert body["usage"] == {"include": True}
    assert body["messages"][1]["content"] == "Source."
    assert body["provider"]["allow_fallbacks"] is False
    original = chat_body(model="apodex/apodex-1.1-mini:free", system="Trusted.", user="Source.", schema={})
    assert original["temperature"] == 0.2 and "usage" not in original


def test_luna_uncapped_body_has_no_explicit_input_or_output_token_limit():
    body = chat_body(model=LUNA_MODEL, system="Trusted.", user="Source.", schema={}, response_format="json_object")
    for field in ("max_tokens", "max_completion_tokens", "max_output_tokens", "truncate", "truncation"):
        assert field not in body
    assert body["messages"][1]["content"] == "Source."


@pytest.mark.parametrize("payload_format", ["compact_weekly", "legacy_flat"])
def test_uncapped_live_setting_bypasses_local_size_gates_not_validation(paid_harness, monkeypatch, payload_format):
    settings, provider, _pipeline = paid_harness
    settings = settings.model_copy(
        update={"llm_input_limits_enabled": False, "llm_completion_tokens": None, "max_llm_request_characters": 1}
    )
    # Compact source is loaded first; the configured gate type is changed only
    # for _call_json so the same synthetic compact response contract is used.
    pipeline = Pipeline(settings, provider)
    original_load = pipeline.load_week

    def load(week):
        result = original_load(week)
        settings.llm_payload_format = payload_format
        return result

    pipeline.load_week = load
    monkeypatch.setattr(stage_module, "preflight", lambda *args: pytest.fail("Disabled preflight must not run"))
    result = pipeline.run(1, mode="live", run_id="uncapped")
    assert result["embedding_requests"] == 0
    assert provider.calls == {"moment_extraction": 1, "angle_generation": 1}
    for path in settings.data_root.glob("service_calls/*/attempts/*/request.json"):
        body = pipeline.store.read_json(str(path.relative_to(settings.data_root)))["request"]
        assert "max_tokens" not in body and "max_completion_tokens" not in body
    for path in settings.data_root.glob("service_calls/*/attempts/*/preflight.json"):
        report = pipeline.store.read_json(str(path.relative_to(settings.data_root)))
        assert report["local_input_limits_enforced"] is False and report["request_output_token_cap"] is None
        assert not report["input_truncated"]


def test_uncapped_live_still_rejects_bad_quotes_and_records_cost(paid_harness):
    settings, provider, _pipeline = paid_harness
    settings = settings.model_copy(update={"llm_input_limits_enabled": False, "llm_completion_tokens": None})
    provider.bad_quote = True
    pipeline = Pipeline(settings, provider)
    with pytest.raises(ValueError, match="quote must match"):
        pipeline.run(1, mode="live", run_id="uncapped-invalid")
    summary = pipeline.store.read_json("experiments/default/runs/uncapped-invalid/cost_summary.json")
    assert summary["total_new_cost_usd"] == 0.012
    assert provider.calls == {"moment_extraction": 1}


@pytest.mark.parametrize("value", [None, True, -1, "NaN", "Infinity", "invalid"])
def test_missing_or_invalid_cost_is_unknown_not_zero(value):
    assert reported_cost({"usage": {"cost": value}}) is None
    assert call_record(raw={"usage": {"cost": value}}, dispatched=True)["new_cost_usd"] is None


def test_real_zero_cost_and_replayed_original_cost_are_distinct():
    assert reported_cost({"usage": {"cost": 0}}) == 0.0
    record = call_record(raw={"usage": {"cost": 0.024}}, reused=True)
    assert record["new_cost_usd"] == 0 and record["original_reported_cost_usd"] == 0.024


@pytest.mark.parametrize("raw", [[], {"usage": "invalid"}])
def test_malformed_response_usage_does_not_hide_unknown_billing(raw):
    record = call_record(raw=raw, dispatched=True)
    assert record["new_cost_usd"] is None and record["usage"] is None


def test_both_paid_stages_saved_and_summed_without_reasoning_double_count(paid_harness):
    settings, provider, pipeline = paid_harness
    result = pipeline.run(1, mode="live", run_id="paid")
    prefix = "experiments/default/runs/paid"
    summary = pipeline.store.read_json(f"{prefix}/cost_summary.json")
    assert summary["total_new_cost_usd"] == 0.018 and summary["all_new_costs_known"]
    assert [stage["new_cost_usd"] for stage in summary["stages"]] == [0.012, 0.006]
    assert all(stage["calls"][0]["usage"]["completion_tokens"] == 100 for stage in summary["stages"])
    assert result["embedding_requests"] == 0
    assert provider.calls == {"moment_extraction": 1, "angle_generation": 1}
    assert "$0.01800000" in pipeline.store.path(f"{prefix}/cost_summary.md").read_text(encoding="utf-8")
    assert len(list(settings.data_root.glob("service_calls/*/attempts/*/cost.json"))) == 2


def test_replay_reports_zero_new_cost_but_preserves_original_usage(paid_harness):
    settings, provider, pipeline = paid_harness
    pipeline.run(1, mode="live", run_id="original")
    replay = Pipeline(settings, provider)
    replay.run(1, mode="replay", run_id="replay")
    summary = replay.store.read_json("experiments/default/runs/replay/cost_summary.json")
    assert summary["total_new_cost_usd"] == 0
    assert [s["calls"][0]["original_reported_cost_usd"] for s in summary["stages"]] == [0.012, 0.006]
    assert provider.calls == {"moment_extraction": 1, "angle_generation": 1}


def test_failed_source_validation_retains_billed_usage_and_skips_call_two(paid_harness):
    _settings, provider, pipeline = paid_harness
    provider.bad_quote = True
    with pytest.raises(ValueError, match="quote must match"):
        pipeline.run(1, mode="live", run_id="failed")
    prefix = "experiments/default/runs/failed"
    summary = pipeline.store.read_json(f"{prefix}/cost_summary.json")
    artifact = pipeline.store.read_json(f"{prefix}/moment_extraction.failed.json")
    assert artifact["usage"]["cost"] == 0.012 and artifact["raw_response"]
    assert summary["total_new_cost_usd"] == 0.012
    assert summary["stages"][0]["calls"][0]["validation_status"] == "failed"
    assert summary["stages"][1]["status"] == "not_attempted"
    assert provider.calls == {"moment_extraction": 1}


def test_preflight_refusal_records_no_dispatch_or_charge(paid_harness, monkeypatch):
    _settings, provider, pipeline = paid_harness
    monkeypatch.setattr(stage_module, "preflight", lambda *args: {"fits": False})
    with pytest.raises(RuntimeError, match="No batching or truncation"):
        pipeline.run(1, mode="live", run_id="blocked")
    summary = pipeline.store.read_json("experiments/default/runs/blocked/cost_summary.json")
    assert summary["total_new_cost_usd"] == 0 and not provider.calls
    assert summary["stages"][0]["calls"][0]["cost_status"] == "not_sent"


def test_timeout_without_response_cost_remains_unknown(paid_harness):
    _settings, provider, pipeline = paid_harness
    provider.timeout = True
    with pytest.raises(TimeoutError):
        pipeline.run(1, mode="live", run_id="timeout")
    summary = pipeline.store.read_json("experiments/default/runs/timeout/cost_summary.json")
    assert summary["total_new_cost_usd"] is None and not summary["all_new_costs_known"]


def route_store(tmp_path):
    store = JsonStore(tmp_path)
    store.write_json(
        "route.json",
        {
            "data": {
                "id": LUNA_MODEL,
                "endpoints": [
                    {
                        "context_length": 1050000,
                        "max_prompt_tokens": 922000,
                        "max_completion_tokens": 128000,
                        "supported_parameters": ["max_tokens", "response_format", "reasoning"],
                    }
                ],
            }
        },
    )
    store.write_json(
        LUNA_MANIFEST,
        {
            "model": LUNA_MODEL,
            "route_snapshot": "route.json",
            "route_sha256": hashlib.sha256(store.path("route.json").read_bytes()).hexdigest(),
        },
    )
    return store


def test_luna_preflight_is_labelled_conservative_not_native(tmp_path):
    route_store(tmp_path)
    body = chat_body(
        model=LUNA_MODEL, system="Trusted.", user="Whitney: Hi!", schema={}, response_format="json_object", max_tokens=65536
    )
    report = preflight(body, tmp_path)
    assert report["fits"] and report["counting_is_local"]
    assert not report["native_token_count_available"] and not report["hosted_usage_is_exact"]
    assert report["completion_reserved_tokens"] == 65536


def test_luna_preflight_blocks_overflow_without_editing_payload(tmp_path):
    route_store(tmp_path)
    body = chat_body(model=LUNA_MODEL, system="Trusted.", user="A" * 3100000, schema={}, max_tokens=65536)
    assert preflight(body, tmp_path)["fits"] is False
    assert len(body["messages"][1]["content"]) == 3100000


def test_the_first_live_weeks_packet_fits(tmp_path):
    # 2 November 2026: 816,111 bytes were refused at one token a byte; the provider counted 216,072 tokens for them.
    route_store(tmp_path)
    body = chat_body(model=LUNA_MODEL, system="Trusted.", user="A" * 816111, schema={}, max_tokens=32000)
    report = preflight(body, tmp_path)
    assert report["fits"] and report["input_token_budget_allowance"] < 420000


def test_luna_route_snapshot_checksum_is_enforced(tmp_path):
    store = route_store(tmp_path)
    store.write_json("route.json", {"changed": True}, overwrite=True)
    body = chat_body(model=LUNA_MODEL, system="Trusted.", user="Source.", schema={}, max_tokens=65536)
    with pytest.raises(RuntimeError, match="checksum"):
        preflight(body, tmp_path)
