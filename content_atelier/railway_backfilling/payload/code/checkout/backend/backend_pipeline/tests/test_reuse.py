from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import httpx
import pytest

from backend_pipeline import pipeline as pipeline_module
from backend_pipeline.config import Settings
from backend_pipeline.db import project_json_vectors
from backend_pipeline.models import Angle, StageArtifact
from backend_pipeline.pipeline import Pipeline
from backend_pipeline.provider import LiveProvider
from backend_pipeline.store import JsonStore, canonical_hash


class CountingProvider:
    """Nonempty synthetic outputs; all requests stay inside this test process."""

    def __init__(self, dimensions: int = 3):
        self.calls: Counter = Counter()
        self.dimensions = dimensions
        self.fail_embedding = False

    def json_call(self, *, stage, system, user, schema, fingerprint):
        self.calls[stage] += 1
        if stage == "moment_extraction":
            spans = json.loads(user.split("Source packet:\n", 1)[1])
            output = {
                "moments": [
                    {
                        "local_key": "m1",
                        "anchor_span_ids": [spans[0]["span_id"]],
                        "context_span_ids": [s["span_id"] for s in spans],
                        "quote": spans[0]["text"],
                        "context_summary": "A synthetic discussion of timely replies with limits.",
                        "moment_type": "observation",
                        "proposition": "Timely replies can help comparisons.",
                        "audience_relevance": "Venue enquiry follow-up",
                        "qualifications": ["Not a measured result"],
                        "claim_status": "reported",
                        "sensitivity": "public_candidate",
                        "strength": 4,
                        "reasons": ["Concrete mechanism"],
                    }
                ],
                "processed_span_ids": [s["span_id"] for s in spans],
                "coverage_notes": [],
            }
        else:
            moments = json.loads(user.split("Moment pool:\n", 1)[1].split("\n\nPrevious eligible", 1)[0])
            output = {
                "angles": [
                    {
                        "local_key": "a1",
                        "title": "Make venue comparisons easier",
                        "argument": "Reply with comparison information while the enquiry is current.",
                        "audience": "Venue owners",
                        "tension": "A reply can be timely but unhelpful.",
                        "take": "Include concrete comparison information.",
                        "mechanism": "Reduce decision friction.",
                        "reader_decision": "Review the first enquiry response.",
                        "moment_ids": [moments[0]["moment_id"]],
                        "source_assertions": [f"[{moments[0]['moment_id']}] {moments[0]['proposition']}"],
                        "inference": None,
                        "qualifiers": ["Not a measured lift"],
                        "risks": [],
                        "quality": {
                            "grounding": 5,
                            "source_relevance": 5,
                            "audience_fit": 5,
                            "specificity": 5,
                            "editorial_usefulness": 5,
                            "reasons": ["Synthetic fixture"],
                        },
                    }
                ],
                "processed_moment_ids": [m["moment_id"] for m in moments],
                "coverage_notes": [],
            }
        from backend_pipeline.tests.strategic_fixtures import strategic_output
        output = strategic_output(output, schema)
        raw = {
            "id": "mock-only",
            "choices": [{"message": {"content": json.dumps(output)}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 10, "cost": 0},
        }
        return output, {"raw": raw, "fake": True, "fingerprint": fingerprint}

    def embed(self, *, text, fingerprint):
        self.calls["embedding"] += 1
        if self.fail_embedding:
            raise RuntimeError("Synthetic embedding outage")
        vector = [1.0] + [0.0] * (self.dimensions - 1)
        return vector, {
            "raw": {"data": [{"embedding": vector}], "usage": {"prompt_tokens": 10, "cost": 0}},
            "fake": True,
            "fingerprint": fingerprint,
        }


@pytest.fixture
def harness(tmp_path: Path):
    week = tmp_path / "inputs" / "week1"
    week.mkdir(parents=True)
    (week / "meeting.vtt").write_text(
        "WEBVTT\n\n00:00:00.000 --> 00:00:05.000\nWhitney: Faster replies help couples compare venues.\n\n"
        "00:00:05.000 --> 00:00:10.000\nWhitney: This is an observation, not a measured conversion lift.\n",
        encoding="utf-8",
    )
    # Existing full-pipeline tests explicitly opt into the preserved vector leg.
    settings = Settings(
        data_root=tmp_path / "data", transcript_root=tmp_path / "inputs", embedding_dimensions=3, embeddings_enabled=True
    )
    provider = CountingProvider()
    return settings, provider, Pipeline(settings, provider)


def run_record(pipeline: Pipeline, result: dict, name: str):
    return pipeline.store.read_json(f"experiments/default/runs/{result['run_id']}/{name}.json")


def test_nonempty_identical_rerun_reuses_every_call_and_generation_lineage(harness):
    settings, provider, pipeline = harness
    first = pipeline.run(1)
    second = pipeline.run(1)
    assert first["moments"] == first["angles"] == first["visible"] == 1
    assert provider.calls == {"moment_extraction": 1, "angle_generation": 1, "embedding": 1}
    assert run_record(pipeline, first, "moments") == run_record(pipeline, second, "moments")
    original = run_record(pipeline, first, "angles")[0]
    reused = run_record(pipeline, second, "angles")[0]
    for field in ("angle_id", "run_id", "generated_at", "embedding"):
        assert reused[field] == original[field]
    assert reused["run_id"] == first["run_id"] != second["run_id"]
    assert reused["adjusted_score"] == 100  # Replays do not penalise themselves as new history.
    assert run_record(pipeline, second, "manifest")["status"] == "completed"
    artifact = run_record(pipeline, first, "moment_extraction")
    assert artifact["request"]["messages"][1]["content"]
    assert artifact["raw_response"]["id"] == "mock-only"
    assert artifact["usage"]["prompt_tokens"] == 10
    assert len(list(settings.data_root.glob("service_calls/*/attempts/*/request.json"))) == 3
    assert len(list(settings.data_root.glob("service_calls/*/attempts/*/response.raw.json"))) == 3
    reuse_paths = list((settings.data_root / f"experiments/default/runs/{second['run_id']}/reuse").glob("*.json"))
    assert len(reuse_paths) == 3
    assert all(json.loads(p.read_text())["new_inference_cost"] == 0 for p in reuse_paths)


@pytest.mark.parametrize(
    ("field", "value", "expected"),
    [
        ("openrouter_moments_model", "test/moments-v2", {"moment_extraction": 2, "angle_generation": 1, "embedding": 1}),
        ("openrouter_angles_model", "test/angles-v2", {"moment_extraction": 1, "angle_generation": 2, "embedding": 1}),
        ("embedding_model", "test/embedding-v2", {"moment_extraction": 1, "angle_generation": 1, "embedding": 2}),
        ("embedding_base_url", "https://example.invalid/v2", {"moment_extraction": 1, "angle_generation": 1, "embedding": 2}),
        ("visible_threshold", 101, {"moment_extraction": 1, "angle_generation": 1, "embedding": 1}),
    ],
)
def test_dependency_changes_only_invalidate_affected_requests(harness, field, value, expected):
    settings, provider, pipeline = harness
    first = pipeline.run(1)
    updated = settings.model_copy(update={field: value})
    second_pipeline = Pipeline(updated, provider)
    second = second_pipeline.run(1)
    assert provider.calls == expected
    assert len(run_record(second_pipeline, second, "angles")[0]["embedding"]) == 3
    if field == "visible_threshold":
        assert second["visible"] == 0
    if field == "openrouter_angles_model":
        assert (
            run_record(pipeline, first, "angles")[0]["angle_id"] != run_record(second_pipeline, second, "angles")[0]["angle_id"]
        )


def test_dimension_change_reuses_llm_calls_but_not_vectors(harness):
    settings, provider, pipeline = harness
    pipeline.run(1)
    provider.dimensions = 4
    updated_pipeline = Pipeline(settings.model_copy(update={"embedding_dimensions": 4}), provider)
    result = updated_pipeline.run(1)
    assert provider.calls == {"moment_extraction": 1, "angle_generation": 1, "embedding": 2}
    assert len(run_record(updated_pipeline, result, "angles")[0]["embedding"]) == 4
    assert run_record(updated_pipeline, result, "angles")[0]["adjusted_score"] == 100


def test_prompt_change_preserves_stage_one_and_unchanged_signature_vector(harness, monkeypatch):
    settings, provider, pipeline = harness
    pipeline.run(1)
    original = pipeline_module.angle_prompt

    def changed_prompt(*args):
        system, user = original(*args)
        return system + "\nSynthetic prompt revision.", user

    monkeypatch.setattr(pipeline_module, "angle_prompt", changed_prompt)
    Pipeline(settings, provider).run(1)
    assert provider.calls == {"moment_extraction": 1, "angle_generation": 2, "embedding": 1}


def test_source_revisions_are_preserved_and_trigger_new_extraction(harness):
    settings, provider, pipeline = harness
    first = pipeline.run(1)
    path = settings.transcript_root / "week1" / "meeting.vtt"
    path.write_text(path.read_text(encoding="utf-8").replace("Faster replies", "Useful replies"), encoding="utf-8")
    second = pipeline.run(1)
    assert provider.calls == {"moment_extraction": 2, "angle_generation": 2, "embedding": 1}
    assert run_record(pipeline, first, "moments")[0]["moment_id"] != run_record(pipeline, second, "moments")[0]["moment_id"]
    assert len(list(settings.data_root.glob("sources/week1/*/*.json"))) == 2
    assert len(list(settings.data_root.glob("cycles/week1/snapshots/*.json"))) == 2


def test_fake_artifacts_never_satisfy_live_replay_and_replay_needs_no_keys(harness):
    settings, provider, pipeline = harness
    pipeline.run(1, mode="fake")
    with pytest.raises(RuntimeError, match="Replay cache miss"):
        pipeline.run(1, mode="replay")
    assert provider.calls == {"moment_extraction": 1, "angle_generation": 1, "embedding": 1}
    live_settings = settings.model_copy(
        update={
            "live_enabled": True,
            "openrouter_moments_key": "dummy-only",
            "openrouter_angles_key": "dummy-only",
            "embedding_api_key": "dummy-only",
        }
    )
    live_pipeline = Pipeline(live_settings, provider)  # Still the mock, never a real provider.
    first_live = live_pipeline.run(1, mode="live")
    assert provider.calls == {"moment_extraction": 2, "angle_generation": 2, "embedding": 2}
    replayed = Pipeline(settings, provider).run(1, mode="replay")  # No live flag or keys.
    assert provider.calls == {"moment_extraction": 2, "angle_generation": 2, "embedding": 2}
    assert run_record(pipeline, replayed, "angles")[0]["run_id"] == first_live["run_id"]
    saved_requests = list(settings.data_root.glob("service_calls/*/attempts/*/request.json"))
    assert all("dummy-only" not in p.read_text(encoding="utf-8") for p in saved_requests)


def test_failed_later_stage_keeps_upstream_results_for_restart(harness):
    settings, provider, pipeline = harness
    provider.fail_embedding = True
    with pytest.raises(RuntimeError, match="Synthetic embedding outage"):
        pipeline.run(1, run_id="failed-test")
    assert pipeline.store.read_json("experiments/default/runs/failed-test/manifest.json")["status"] == "failed"
    assert pipeline.store.read_json("experiments/default/runs/failed-test/moments.json")
    assert pipeline.store.read_json("experiments/default/runs/failed-test/candidates.json")
    provider.fail_embedding = False
    pipeline.run(1)
    assert provider.calls == {"moment_extraction": 1, "angle_generation": 1, "embedding": 2}
    assert len(list(settings.data_root.glob("service_calls/*/attempts/*/artifact.json"))) == 4


def test_unchanged_signature_has_one_reusable_embedding_even_across_angle_ids(harness):
    _settings, provider, pipeline = harness
    transcripts, _ = pipeline.load_week(1)
    result = pipeline.run(1)
    angle = Angle.model_validate(run_record(pipeline, result, "angles")[0])
    run = pipeline.plan(1, mode="fake")
    angle.angle_id = "another-angle-same-signature"
    run_dir = f"experiments/default/runs/{run.run_id}"
    artifact = pipeline._embedding(angle, run, run_dir)
    assert transcripts and artifact.output["vector"] == angle.embedding
    assert provider.calls["embedding"] == 1
    saved = pipeline.store.read_json(f"{run_dir}/embeddings/{angle.angle_id}.json")
    assert saved["new_call"] is False


def test_wrong_dimensions_and_corrupt_vectors_are_not_promoted(harness):
    settings, provider, pipeline = harness
    provider.dimensions = 2
    with pytest.raises(ValueError, match="dimension mismatch"):
        pipeline.run(1)
    assert len(list(settings.data_root.glob("cache/artifacts/*.json"))) == 2  # Only the validated LLM stages.
    provider.dimensions = 3
    result = pipeline.run(1)
    angle_id = run_record(pipeline, result, "angles")[0]["angle_id"]
    reference = pipeline.store.read_json(f"experiments/default/runs/{result['run_id']}/embeddings/{angle_id}.json")
    pointer = pipeline.store.read_json(f"cache/artifacts/{reference['fingerprint']}.json")
    artifact = pipeline.store.read_json(pointer["artifact_path"])
    artifact["output"]["vector"][0] = 0.5  # Checksum now disagrees.
    pipeline.store.write_json(pointer["artifact_path"], artifact, overwrite=True)
    assert pipeline.store.find_artifact(reference["fingerprint"]) is None
    pipeline.run(1)
    assert provider.calls == {"moment_extraction": 1, "angle_generation": 1, "embedding": 3}


def test_raw_malformed_llm_response_is_saved_before_parsing_failure(harness, monkeypatch):
    settings, _, _ = harness
    raw = {
        "id": "synthetic-invalid",
        "choices": [{"message": {"content": "{not valid JSON"}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 42, "completion_tokens": 5},
    }
    actual_client = httpx.Client
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=raw))
    monkeypatch.setattr(httpx, "Client", lambda **kwargs: actual_client(transport=transport, **kwargs))
    live_settings = settings.model_copy(
        update={
            "live_enabled": True,
            "openrouter_moments_key": "dummy-only",
            "openrouter_angles_key": "dummy-only",
            "embedding_api_key": "dummy-only",
        }
    )
    pipeline = Pipeline(live_settings)
    with pytest.raises(json.JSONDecodeError):
        pipeline.run(1, mode="live", run_id="malformed-test")
    receipts = list(settings.data_root.glob("service_calls/*/attempts/*/response.raw.json"))
    assert len(receipts) == 1 and json.loads(receipts[0].read_text()) == raw
    assert not list(settings.data_root.glob("cache/artifacts/*.json"))
    assert pipeline.store.read_json("experiments/default/runs/malformed-test/manifest.json")["status"] == "failed"
    assert isinstance(pipeline.provider, LiveProvider)


def test_legacy_unsafe_cache_is_ignored_and_store_paths_cannot_escape(tmp_path):
    store = JsonStore(tmp_path / "data")
    legacy = StageArtifact(
        artifact_id="legacy",
        run_id="old",
        stage="embedding",
        request_fingerprint="test",
        model_id="old",
        input_hashes=[],
        status="validated",
        output={"vector": [1.0]},
        cache_version=1,
    )
    legacy.output_hash = canonical_hash(legacy.output)
    store.cache_artifact(legacy, "legacy.json")
    assert store.find_artifact("test") is None
    with pytest.raises(ValueError, match="inside the datastore"):
        store.write_json("../outside.json", {})


def test_saved_vectors_can_rebuild_projection_without_an_embedding_request(harness):
    settings, provider, _pipeline = harness
    provider.dimensions = 1536
    pipeline = Pipeline(settings.model_copy(update={"embedding_dimensions": 1536}), provider)
    result = pipeline.run(1)
    saved_angles = run_record(pipeline, result, "angles")

    class RecordingConnection:
        def __init__(self):
            self.statements = []

        def execute(self, statement, parameters=None):
            self.statements.append((statement, parameters))

    connection = RecordingConnection()  # No real database or external write.
    assert project_json_vectors(connection=connection, angle_records=saved_angles) == 1
    inserted = [params for _statement, params in connection.statements if params is not None]
    assert inserted[0][-1] == saved_angles[0]["embedding"]
    assert provider.calls == {"moment_extraction": 1, "angle_generation": 1, "embedding": 1}
