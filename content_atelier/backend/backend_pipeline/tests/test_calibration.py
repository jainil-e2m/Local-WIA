"""Partial-pool calibration stays explicit, source-bound and disconnected from vectors."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from backend_pipeline import pipeline as pipeline_module
from backend_pipeline.llm import stage as stage_module
from backend_pipeline.calibration import diagnose_received_moments, run_calibration
from backend_pipeline.config import Settings
from backend_pipeline.moment_validation import COVERAGE_RULE, REPAIR_RULE
from backend_pipeline.pipeline import Pipeline
from backend_pipeline.tests.test_extraction_partition import strict_extraction
from backend_pipeline.tests.test_generation_only import CompactCountingProvider


class MixedResponseProvider(CompactCountingProvider):
    def __init__(self):
        super().__init__()
        self.invalid_angle = False
        self.angle_users = []

    def json_call(self, **kwargs):
        output, meta = super().json_call(**kwargs)
        if kwargs["stage"] == "moment_extraction":
            rejected = copy.deepcopy(output["moments"][0])
            rejected.update(local_key="bad-quote", quote="An invented quotation absent from the source.")
            output["moments"].append(rejected)
        else:
            self.angle_users.append(kwargs["user"])
            # Acknowledge the whole pool the diagnostic sends (one moment unless a test adds a repaired one).
            pool = json.loads(kwargs["user"].split("Moment pool:\n", 1)[1].split("\n\nPrevious eligible", 1)[0])
            output["processed_moment_ids"] = [m["moment_id"] for m in pool]
            if self.invalid_angle:
                output["angles"][0]["moment_ids"] = ["invented-moment"]
        return output, meta


@pytest.fixture
def calibration_harness(tmp_path: Path, monkeypatch):
    week = tmp_path / "inputs" / "week1"
    week.mkdir(parents=True)
    (week / "meeting.vtt").write_bytes(
        b"WEBVTT\r\n\r\n1\r\n00:00:00.000 --> 00:00:05.000\r\n"
        b"Whitney: A useful reply helps couples compare venues.\r\n\r\n"
        b"2\r\n00:00:04.000 --> 00:00:09.500\r\nWhitney: This is an observation,\r\n"
        b"not a measured conversion result.\r\n\r\n"
    )
    settings = Settings(
        data_root=tmp_path / "data",
        transcript_root=tmp_path / "inputs",
        llm_payload_format="compact_weekly",
        embedding_dimensions=3,
        live_enabled=True,
        openrouter_moments_key="synthetic-only",
        openrouter_angles_key="synthetic-only",
    )
    monkeypatch.setattr(stage_module, "preflight", lambda *args: {"fits": True})
    provider = MixedResponseProvider()
    pipeline = Pipeline(settings, provider)
    with monkeypatch.context() as earlier:
        # The diagnostic reads a response that failed before E.B12a, when one unbindable quote failed the week.
        earlier.setattr(Pipeline, "_extraction_partition", strict_extraction)
        with pytest.raises(ValueError, match="quote must match"):
            pipeline.run(1, mode="live", run_id="failed-extraction")
    return settings, provider, pipeline


def received_output(pipeline):
    failed = pipeline.store.read_json("experiments/default/runs/failed-extraction/moment_extraction.failed.json")
    return f"service_calls/{failed['request_fingerprint']}/attempts/{failed['artifact_id']}/output.received.json"


def forbidden(*args, **kwargs):
    raise AssertionError("No embedding, history or ranking calls are permitted")


def test_partial_diagnostic_preserves_failure_and_rejected_record(calibration_harness, monkeypatch):
    settings, provider, pipeline = calibration_harness
    original_path = pipeline.store.path(received_output(pipeline))
    original_bytes = original_path.read_bytes()
    monkeypatch.setattr(Pipeline, "_embedding", forbidden)
    monkeypatch.setattr(Pipeline, "_load_history", forbidden)
    monkeypatch.setattr(pipeline_module, "rank", forbidden)
    result = run_calibration(settings, source_run_id="failed-extraction", run_id="diagnostic", mode="live", provider=provider)
    assert result["angles"] == result["accepted_moments"] == result["rejected_moments"] == 1
    assert provider.calls == {"moment_extraction": 1, "angle_generation": 1}
    assert original_path.read_bytes() == original_bytes
    assert pipeline.store.read_json("experiments/default/runs/failed-extraction/manifest.json")["status"] == "failed"
    prefix = "experiments/default/runs/diagnostic"
    assert pipeline.store.read_json(f"{prefix}/manifest.json")["status"] == "partial"
    review = pipeline.store.read_json(f"{prefix}/review.json")
    assert not review["full_weekly_pipeline_succeeded"] and not review["human_approved"]
    assert review["visible_angle_ids"] == [] and review["embedding_requests"] == 0
    rejected = pipeline.store.read_json(f"{prefix}/rejected_moments.json")[0]
    assert rejected["received_record"]["quote"] == "An invented quotation absent from the source."
    assert not pipeline.store.path(f"{prefix}/angles.json").exists()
    assert not pipeline.store.path(f"{prefix}/embeddings").exists()
    assert len(list(settings.data_root.glob("cache/artifacts/*.json"))) == 1  # Call 2 only.


def test_default_cache_only_replay_preserves_original_angle_lineage(calibration_harness):
    settings, provider, pipeline = calibration_harness
    run_calibration(settings, source_run_id="failed-extraction", run_id="live-diagnostic", mode="live", provider=provider)
    attempts_before = list(settings.data_root.glob("service_calls/*/attempts/*/request.json"))
    run_calibration(settings, source_run_id="failed-extraction", run_id="replayed", provider=provider)
    assert list(settings.data_root.glob("service_calls/*/attempts/*/request.json")) == attempts_before
    assert provider.calls == {"moment_extraction": 1, "angle_generation": 1}
    old = pipeline.store.read_json("experiments/default/runs/live-diagnostic/candidates.json")
    new = pipeline.store.read_json("experiments/default/runs/replayed/candidates.json")
    assert old == new
    assert pipeline.store.read_json("experiments/default/runs/replayed/manifest.json")["mode"] == "replay"


def test_uncached_default_replay_never_calls_provider(calibration_harness):
    settings, provider, _pipeline = calibration_harness
    with pytest.raises(RuntimeError, match="Replay cache miss"):
        run_calibration(settings, source_run_id="failed-extraction", run_id="replay-miss", provider=provider)
    assert provider.calls == {"moment_extraction": 1}


def test_source_byte_change_rejects_even_when_dialogue_is_unchanged(calibration_harness):
    settings, provider, pipeline = calibration_harness
    path = settings.transcript_root / "week1" / "meeting.vtt"
    path.write_bytes(path.read_bytes() + b"\r\n")
    with pytest.raises(ValueError, match="snapshot changed"):
        diagnose_received_moments(pipeline, "failed-extraction")
    assert provider.calls == {"moment_extraction": 1}


def test_empty_valid_pool_refuses_call_two(calibration_harness):
    _settings, provider, pipeline = calibration_harness
    path = received_output(pipeline)
    output = pipeline.store.read_json(path)
    output["moments"][0]["quote"] = "Also an invented quote."
    pipeline.store.write_json(path, output, overwrite=True)  # Synthetic mutation only.
    with pytest.raises(ValueError, match="No individually source-valid moments"):
        diagnose_received_moments(pipeline, "failed-extraction")
    assert provider.calls == {"moment_extraction": 1}


def test_duplicate_local_keys_are_not_lost_by_individual_validation(calibration_harness):
    _settings, _provider, pipeline = calibration_harness
    path = received_output(pipeline)
    output = pipeline.store.read_json(path)
    output["moments"][1]["local_key"] = output["moments"][0]["local_key"]
    pipeline.store.write_json(path, output, overwrite=True)
    with pytest.raises(ValueError, match="unique"):
        diagnose_received_moments(pipeline, "failed-extraction")


def test_embedding_enablement_rejected_before_diagnostic(calibration_harness):
    settings, provider, _pipeline = calibration_harness
    with pytest.raises(RuntimeError, match="disconnected"):
        run_calibration(settings.model_copy(update={"embeddings_enabled": True}), source_run_id="unused", run_id="unused")
    assert provider.calls == {"moment_extraction": 1}


def test_invalid_angle_still_fails_strict_validator(calibration_harness):
    settings, provider, pipeline = calibration_harness
    provider.invalid_angle = True
    with pytest.raises(ValueError, match="unknown moment"):
        run_calibration(settings, source_run_id="failed-extraction", run_id="bad-angle", mode="live", provider=provider)
    assert pipeline.store.read_json("experiments/default/runs/bad-angle/manifest.json")["status"] == "failed"
    assert not list(settings.data_root.glob("cache/artifacts/*.json"))
    assert provider.calls == {"moment_extraction": 1, "angle_generation": 1}


def test_full_week_acknowledgement_still_required(calibration_harness):
    _settings, provider, pipeline = calibration_harness
    path = received_output(pipeline)
    output = pipeline.store.read_json(path)
    output["processed_meetings"][0]["span_count"] += 1
    pipeline.store.write_json(path, output, overwrite=True)
    # A coverage failure is week-level (the accepted E.B12a rule): it fails before any moment is judged.
    with pytest.raises(ValueError, match="coverage"):
        diagnose_received_moments(pipeline, "failed-extraction")
    assert provider.calls == {"moment_extraction": 1}


def add_near_miss(pipeline):
    path = received_output(pipeline)
    output = pipeline.store.read_json(path)
    near = copy.deepcopy(output["moments"][0])
    near.update(local_key="near-miss", quote="A useful reply helps couples, compare venues", proposition="Second reading.")
    output["moments"].append(near)
    pipeline.store.write_json(path, output, overwrite=True)  # Synthetic mutation only.


def test_diagnostic_repairs_a_near_miss_quote_and_records_the_repair(calibration_harness):
    settings, provider, pipeline = calibration_harness
    add_near_miss(pipeline)
    result = run_calibration(settings, source_run_id="failed-extraction", run_id="repaired", mode="live", provider=provider)
    assert result["accepted_moments"] == 2 and result["rejected_moments"] == 1 and result["quote_repairs"] == 1
    prefix = "experiments/default/runs/repaired"
    diagnostic = pipeline.store.read_json(f"{prefix}/moment_diagnostic.json")
    [repair] = diagnostic["quote_repairs"]
    assert diagnostic["repair_rule"] == REPAIR_RULE and diagnostic["coverage_rule"] == COVERAGE_RULE
    assert repair["local_key"] == "near-miss" and repair["original_quote"] == "A useful reply helps couples, compare venues"
    assert repair["repaired_quote"] == "A useful reply helps couples compare venues"
    moments = pipeline.store.read_json(f"{prefix}/moments.json")
    assert repair["moment_id"] == moments[1]["moment_id"] and moments[1]["quote"] == repair["repaired_quote"]
    validation = pipeline.store.read_json(f"{prefix}/moment_validation.json")
    assert validation["quote_repairs"] == diagnostic["quote_repairs"] and validation["unverified_usable_as_proof"] is False


def test_rejected_moments_are_never_sent_to_the_angle_call(calibration_harness):
    settings, provider, pipeline = calibration_harness
    run_calibration(settings, source_run_id="failed-extraction", run_id="proof", mode="live", provider=provider)
    [user] = provider.angle_users
    assert "An invented quotation absent from the source." not in user
    rejected = pipeline.store.read_json("experiments/default/runs/proof/rejected_moments.json")
    assert [r["usable_as_proof"] for r in rejected] == [False]
    assert pipeline.store.read_json("experiments/default/runs/proof/moment_diagnostic.json")["rejected_usable_as_proof"] is False


def test_a_schema_failure_still_fails_the_diagnostic(calibration_harness):
    _settings, provider, pipeline = calibration_harness
    path = received_output(pipeline)
    output = pipeline.store.read_json(path)
    output["moments"][1]["strength"] = "high"
    pipeline.store.write_json(path, output, overwrite=True)
    with pytest.raises(ValueError, match="strength"):
        diagnose_received_moments(pipeline, "failed-extraction")
    assert provider.calls == {"moment_extraction": 1}
