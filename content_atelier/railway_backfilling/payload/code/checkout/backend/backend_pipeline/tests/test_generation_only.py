from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

import pytest

from backend_pipeline import pipeline as pipeline_module
from backend_pipeline.config import Settings
from backend_pipeline.models import Angle
from backend_pipeline.pipeline import Pipeline
from backend_pipeline.provider import FakeProvider, chat_body
from backend_pipeline.weekly import resolve_moment_references


class CompactCountingProvider:
    """Synthetic editorial response only; no HTTP, private inputs or billing."""

    def __init__(self):
        self.calls = Counter()
        self.allow_embeddings = False

    def json_call(self, *, stage, system, user, schema, fingerprint):
        self.calls[stage] += 1
        if stage == "moment_extraction":
            refs = re.findall(r"^(m\d+\.t\d+)\|", user, re.MULTILINE)
            output = {
                "moments": [
                    {
                        "local_key": "m1",
                        "anchor_span_ids": [refs[0]],
                        "context_first_span_id": refs[0],
                        "context_last_span_id": refs[-1],
                        "quote": "A useful reply helps couples compare venues.",
                        "context_summary": "Useful information matters, not only reply speed.",
                        "moment_type": "observation",
                        "proposition": "Useful replies support comparison.",
                        "audience_relevance": "Wedding venue owners reviewing enquiry replies",
                        "qualifications": ["Not a measured conversion result"],
                        "claim_status": "reported",
                        "sensitivity": "unknown",
                        "strength": 4.0,
                        "reasons": ["Concrete buyer mechanism"],
                    }
                ],
                "processed_meetings": [
                    {"meeting_ref": "m1", "first_span_id": refs[0], "last_span_id": refs[-1], "span_count": len(refs)}
                ],
                "coverage_notes": [],
            }
        else:
            moments = json.loads(user.split("Moment pool:\n", 1)[1].split("\n\nPrevious eligible", 1)[0])
            assert "Whitney:" in moments[0]["source_evidence"][0]["text"]
            assert moments[0]["source_metadata"]
            moment_id = moments[0]["moment_id"]
            output = {
                "angles": [
                    {
                        "local_key": "a1",
                        "title": "Make the first reply useful for comparison",
                        "argument": "A quick venue reply should also answer the comparison decision.",
                        "audience": "Wedding venue owners",
                        "tension": "A fast reply can still leave questions unanswered.",
                        "take": "Include decision-useful information.",
                        "mechanism": "Reduce uncertainty in venue comparison.",
                        "reader_decision": "Review the information in the first enquiry response.",
                        "moment_ids": [moment_id],
                        "source_assertions": [f"[{moment_id}] Useful replies support comparison."],
                        "inference": None,
                        "qualifiers": ["Not a measured conversion result"],
                        "risks": [],
                        "quality": {
                            "grounding": 5.0,
                            "source_relevance": 5.0,
                            "audience_fit": 5.0,
                            "specificity": 5.0,
                            "editorial_usefulness": 5.0,
                            "reasons": ["Synthetic fixture"],
                        },
                    }
                ],
                "processed_moment_ids": [moment_id],
                "coverage_notes": [],
            }
        from backend_pipeline.tests.strategic_fixtures import strategic_output
        output = strategic_output(output, schema)
        return output, {
            "fake": True,
            "raw": {
                "id": "synthetic-only",
                "usage": {"cost": 0},
                "choices": [{"message": {"content": json.dumps(output)}, "finish_reason": "stop"}],
            },
        }

    def embed(self, *, text, fingerprint):
        if not self.allow_embeddings:
            raise AssertionError("Embedding provider must remain disconnected")
        self.calls["embedding"] += 1
        return [1.0, 0.0, 0.0], {"fake": True}


@pytest.fixture
def generation_harness(tmp_path: Path):
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
    )
    provider = CompactCountingProvider()
    return settings, provider, Pipeline(settings, provider)


def test_generation_only_saves_candidates_and_never_embeds_or_ranks(generation_harness, monkeypatch):
    settings, provider, pipeline = generation_harness

    def forbidden(*args, **kwargs):
        raise AssertionError("Vector leg must be disconnected")

    monkeypatch.setattr(pipeline, "_load_history", forbidden)
    monkeypatch.setattr(pipeline_module, "rank", forbidden)
    result = pipeline.run(1)
    assert provider.calls == {"moment_extraction": 1, "angle_generation": 1}
    assert result["embedding_requests"] == 0
    assert result["visible"] == 0 and result["angles"] == 1
    run_dir = f"experiments/default/runs/{result['run_id']}"
    manifest = pipeline.store.read_json(f"{run_dir}/manifest.json")
    assert manifest["status"] == "generation_completed" and manifest["execution_scope"] == "generation_only"
    candidate = pipeline.store.read_json(f"{run_dir}/candidates.json")[0]
    assert candidate["status"] == "candidate" and candidate["embedding"] is None
    assert candidate["adjusted_score"] is None and candidate["max_similarity"] is None
    assert not pipeline.store.path(f"{run_dir}/angles.json").exists()
    assert not pipeline.store.path(f"{run_dir}/embeddings").exists()
    assert pipeline.store.read_json(f"{run_dir}/review.json")["similarity_status"] == "not_run"
    assert len(list(settings.data_root.glob("service_calls/*/attempts/*/request.json"))) == 2


def test_short_references_resolve_without_rewriting_received_response(generation_harness):
    _settings, _provider, pipeline = generation_harness
    result = pipeline.run(1)
    run_dir = f"experiments/default/runs/{result['run_id']}"
    artifact = pipeline.store.read_json(f"{run_dir}/moment_extraction.json")
    assert artifact["output"]["processed_meetings"][0]["span_count"] == 2
    assert artifact["output"]["moments"][0]["anchor_span_ids"] == ["m1.t0001"]
    moment = pipeline.store.read_json(f"{run_dir}/moments.json")[0]
    assert all(ref.startswith("zoom:") for ref in moment["context_span_ids"])
    transcripts, packet = pipeline.load_week(1)
    assert "Whitney:" in packet
    assert transcripts[0].spans[1].text.endswith("observation,\nnot a measured conversion result.")
    assert transcripts[0].spans[1].start_seconds == 4.0  # overlapping cues remain in source order
    assert transcripts[0].source_metadata["date"] is None


def test_generation_only_identical_rerun_reuses_both_llm_responses(generation_harness):
    _settings, provider, pipeline = generation_harness
    first = pipeline.run(1)
    second = pipeline.run(1)
    assert provider.calls == {"moment_extraction": 1, "angle_generation": 1}
    assert first["angles"] == second["angles"] == 1


def test_later_explicit_reconnection_reuses_saved_llm_results(generation_harness):
    settings, provider, pipeline = generation_harness
    first = pipeline.run(1)
    provider.allow_embeddings = True
    full = Pipeline(settings.model_copy(update={"embeddings_enabled": True}), provider)
    later = full.run(1)
    assert provider.calls == {"moment_extraction": 1, "angle_generation": 1, "embedding": 1}
    original = pipeline.store.read_json(f"experiments/default/runs/{first['run_id']}/candidates.json")[0]
    projected = full.store.read_json(f"experiments/default/runs/{later['run_id']}/angles.json")[0]
    assert original["angle_id"] == projected["angle_id"]
    assert original["generated_at"] == projected["generated_at"]


def test_live_generation_only_needs_no_embedding_key(generation_harness, monkeypatch):
    settings, provider, _pipeline = generation_harness
    live = settings.model_copy(
        update={
            "live_enabled": True,
            "openrouter_moments_key": "synthetic-only",
            "openrouter_angles_key": "synthetic-only",
            "llm_completion_tokens": 65536,
        }
    )
    monkeypatch.setattr(pipeline_module, "preflight", lambda request, root: {"fits": True})
    result = Pipeline(live, provider).run(1, mode="live")
    assert result["angles"] == 1 and result["embedding_requests"] == 0
    assert provider.calls == {"moment_extraction": 1, "angle_generation": 1}


def test_token_failure_blocks_provider_without_splitting_or_truncation(generation_harness, monkeypatch):
    settings, provider, _pipeline = generation_harness
    live = settings.model_copy(
        update={
            "live_enabled": True,
            "openrouter_moments_key": "synthetic-only",
            "openrouter_angles_key": "synthetic-only",
            "llm_completion_tokens": 65536,
        }
    )
    monkeypatch.setattr(pipeline_module, "preflight", lambda request, root: {"fits": False})
    with pytest.raises(RuntimeError, match="No batching or truncation"):
        Pipeline(live, provider).run(1, mode="live")
    assert not provider.calls


def test_direct_embedding_method_is_guarded(generation_harness):
    _settings, _provider, pipeline = generation_harness
    result = pipeline.run(1)
    record = pipeline.store.read_json(f"experiments/default/runs/{result['run_id']}/candidates.json")[0]
    with pytest.raises(RuntimeError, match="disconnected"):
        pipeline._embedding(Angle.model_validate(record), pipeline.plan(1, "fake"), "unused")


def test_unknown_compact_reference_is_rejected():
    output = {"moments": [], "processed_span_ids": ["999"], "coverage_notes": []}
    with pytest.raises(ValueError, match="unknown compact"):
        resolve_moment_references(output, {"1": "canonical"})
    assert output["processed_span_ids"] == ["999"]


def test_meeting_acknowledgement_requires_exact_bounds_and_count():
    output = {
        "moments": [],
        "processed_meetings": [{"meeting_ref": "m1", "first_span_id": "m1.t0001", "last_span_id": "m1.t0002", "span_count": 3}],
        "coverage_notes": ["Synthetic fixture"],
    }
    with pytest.raises(ValueError, match="bounds/counts"):
        resolve_moment_references(output, {"m1.t0001": "canonical1", "m1.t0002": "canonical2"})


def test_meeting_ack_is_not_relabelled_as_llm_span_echo(generation_harness):
    _settings, _provider, pipeline = generation_harness
    result = pipeline.run(1)
    review = pipeline.store.read_json(f"experiments/default/runs/{result['run_id']}/review.json")
    assert review["coverage"] == "meeting_bounds_acknowledged"
    assert review["processed_span_count"] is None
    assert review["delivered_span_count"] == 2
    assert review["processed_meeting_count"] == 1
    assert review["coverage_is_proof_of_comprehension"] is False


def test_json_object_mode_supplies_schema_at_system_authority():
    schema = {"type": "object", "required": ["moments"], "properties": {"moments": {"type": "array"}}}
    body = chat_body(
        model="synthetic-only",
        system="Trusted instruction.",
        user="Untrusted source.",
        schema=schema,
        response_format="json_object",
        max_tokens=65536,
        reasoning_effort="low",
    )
    assert body["response_format"] == {"type": "json_object"}
    assert json.dumps(schema, separators=(",", ":")) in body["messages"][0]["content"]
    assert body["messages"][1]["content"] == "Untrusted source."
    assert body["max_tokens"] == 65536
    assert body["provider"]["allow_fallbacks"] is False


def test_plain_text_retained_as_untimed_with_unknown_timing(tmp_path):
    week = tmp_path / "inputs" / "week1"
    week.mkdir(parents=True)
    (week / "plain.txt").write_text("Hello everyone.\nNo timing metadata.\n", encoding="utf-8")
    settings = Settings(data_root=tmp_path / "data", transcript_root=tmp_path / "inputs", llm_payload_format="compact_weekly")
    pipeline = Pipeline(settings, FakeProvider())
    result = pipeline.run(1)
    transcripts, packet = pipeline.load_week(1)
    assert "UNTIMED " in packet
    assert transcripts[0].spans[0].start_seconds is None
    assert result["embedding_requests"] == 0
