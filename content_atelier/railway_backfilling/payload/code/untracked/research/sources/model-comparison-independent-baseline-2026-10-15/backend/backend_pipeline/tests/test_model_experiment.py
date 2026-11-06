"""Isolation and dispatch safeguards only; every model response here is synthetic."""
import copy
import json

import pytest

from backend_pipeline import model_experiment as experiment
from backend_pipeline import pipeline as pipeline_module
from backend_pipeline.config import Settings
from backend_pipeline.provider import LiveProvider, chat_body
from backend_pipeline.store import canonical_hash
from backend_pipeline.strategy_contracts import StrategicCompactMomentResponse
from backend_pipeline.tests.test_generation_only import CompactCountingProvider


@pytest.fixture
def suite(tmp_path):
    inputs = tmp_path / "originals"
    for week in (3, 4):
        path = inputs / f"week{week}" / "meeting.vtt"
        path.parent.mkdir(parents=True)
        path.write_bytes(b"WEBVTT\n\n00:00:00.000 --> 00:00:05.000\nWhitney: A useful reply helps couples compare venues.\n\n"
                         b"00:00:05.000 --> 00:00:09.000\nWhitney: Not a measured conversion result.\n")
    catalogs = tmp_path / "catalogs"
    for slug, model in experiment.MODELS.items():
        experiment.write(catalogs / slug / "model-check.json", {
            "exact_route_found": True, "advertised_id": model,
            "endpoints": [{"supported_parameters": ["reasoning", "response_format"], "context_length": 1000000,
                           "max_prompt_tokens": 900000, "max_completion_tokens": 128000}],
        })
    base = Settings(transcript_root=inputs, data_root=tmp_path / "normal-datastore")
    target = tmp_path / "comparison"
    manifest = experiment.prepare_suite(base, target, catalogs)
    return base, target, manifest


class IndependentProvider(CompactCountingProvider):
    def __init__(self, marker, *, invalid=False):
        super().__init__()
        self.marker, self.invalid, self.users = marker, invalid, []

    def json_call(self, **kwargs):
        self.users.append(kwargs["user"])
        output, metadata = super().json_call(**kwargs)
        if kwargs["stage"] == "moment_extraction":
            output["moments"][0]["context_summary"] += f" Synthetic marker {self.marker}."
            if self.invalid:
                output["moments"][0]["quote"] = "An absent synthetic quote."
        else:
            output["angles"][0]["title"] = self.marker
        metadata["raw"]["choices"][0]["message"]["content"] = json.dumps(output)
        return output, metadata


def test_prepare_freezes_six_distinct_datastores_and_equal_weekly_messages(suite):
    base, root, manifest = suite
    assert manifest["max_paid_calls"] == 12 and len(manifest["cells"]) == 6
    assert not list(root.rglob("*.dispatch.json"))
    assert not base.data_root.exists()
    roots = set()
    for week in (3, 4):
        messages = []
        for slug in experiment.MODELS:
            settings = experiment.cell_settings(base, root, week, slug)
            roots.add(settings.data_root)
            assert not settings.embeddings_enabled
            assert settings.llm_reasoning_effort == "high"
            cell = experiment.cell_path(root, week, slug)
            body = experiment.read(cell / "prepared-extraction.request.json")
            messages.append(body["messages"])
            assert "temperature" not in body
            assert body["reasoning"] == {"effort": "high"}
        assert messages[0] == messages[1] == messages[2]
    assert len(roots) == 6


def test_six_synthetic_runs_never_read_sibling_results_history_or_vectors(suite, monkeypatch):
    base, root, _ = suite
    def forbidden(*args, **kwargs):
        raise AssertionError("History, embeddings and ranking are forbidden")
    monkeypatch.setattr(pipeline_module.Pipeline, "_load_history", forbidden)
    monkeypatch.setattr(pipeline_module, "rank", forbidden)
    finished = []
    for week in (3, 4):
        for slug in experiment.MODELS:
            marker = f"synthetic-w{week}-{slug}"
            provider = IndependentProvider(marker)
            result = experiment.run_cell(base, root, week, slug, provider=provider)
            assert provider.calls == {"moment_extraction": 1, "angle_generation": 1}
            assert result["similarity_status"] == "not_run"
            assert marker in provider.users[1]
            assert all(previous not in provider.users[1] for previous in finished)
            assert provider.users[1].endswith("[]\n")
            cell = experiment.cell_path(root, week, slug)
            before = (cell / "review.md").read_bytes()
            assert marker.encode() in before
            assert "Supporting source content" in before.decode()
            assert len(list((cell / "data/service_calls").rglob("response.raw.json"))) == 2
            with pytest.raises((ValueError, FileExistsError)):
                experiment.run_cell(base, root, week, slug, provider=provider)
            assert before == (cell / "review.md").read_bytes()
            finished.append(marker)
    assert not base.data_root.exists()


def test_explicit_live_required_and_sources_cannot_drift(suite):
    base, root, _ = suite
    with pytest.raises(ValueError, match="--live"):
        experiment.run_cell(base, root, 3, "luna-pro")
    path = root / "inputs/week3/meeting.vtt"
    path.write_bytes(path.read_bytes() + b"changed")
    with pytest.raises(ValueError, match="Frozen source"):
        experiment.run_cell(base, root, 3, "luna-pro", provider=IndependentProvider("unused"))
    assert not list(root.rglob("started.json"))


def test_partial_or_invalid_extraction_never_dispatches_angles_or_poison_sibling(suite):
    base, root, _ = suite
    failed = IndependentProvider("bad-source-binding", invalid=True)
    with pytest.raises(ValueError, match="quote"):
        experiment.run_cell(base, root, 3, "luna-pro", provider=failed)
    assert failed.calls == {"moment_extraction": 1}
    good = IndependentProvider("independent-sol")
    result = experiment.run_cell(base, root, 3, "sol", provider=good)
    assert result["angles"] == 1
    assert "bad-source-binding" not in good.users[1]


def test_runtime_and_plan_drift_fail_before_run(suite, monkeypatch):
    base, root, manifest = suite
    changed = copy.deepcopy(manifest["runtime_identity"])
    changed["prompts.py"] = "changed"
    with monkeypatch.context() as patch:
        patch.setattr(experiment, "runtime_identity", lambda: changed)
        with pytest.raises(ValueError, match="engine files"):
            experiment.run_cell(base, root, 3, "sol", provider=IndependentProvider("unused"))
    cell = experiment.cell_path(root, 3, "sol")
    plan = experiment.read(cell / "plan.json")
    experiment.write(cell / "plan.json", {**plan, "model": "different"})
    with pytest.raises(ValueError, match="plan differs"):
        experiment.run_cell(base, root, 3, "sol", provider=IndependentProvider("unused"))


def test_exact_route_guard_refuses_model_substitution_and_second_dispatch(suite, monkeypatch):
    base, root, _ = suite
    cell = experiment.cell_path(root, 3, "luna-pro")
    settings = experiment.cell_settings(base, root, 3, "luna-pro")
    seen = []
    def response(self, **kwargs):
        raw = {"model": "different-model"}
        self.on_response(kwargs["fingerprint"], raw)
        return {}, {"raw": raw}
    monkeypatch.setattr(LiveProvider, "json_call", response)
    guarded = experiment.ExactModelProvider(settings, root, cell, lambda _, raw: seen.append(raw))
    body = experiment.read(cell / "prepared-extraction.request.json")
    # Strip only the provider-managed schema suffix before reconstructing it once.
    system = body["messages"][0]["content"].split("\n\nRequired response JSON contract", 1)[0]
    args = {"stage": "moment_extraction", "system": system, "user": body["messages"][1]["content"],
            "schema": StrategicCompactMomentResponse.model_json_schema(), "fingerprint": canonical_hash(body)}
    with pytest.raises(ValueError, match="Returned model"):
        guarded.json_call(**args)
    assert seen == [{"model": "different-model"}]
    with pytest.raises(FileExistsError):
        guarded.json_call(**args)
    assert len(seen) == 1


@pytest.mark.parametrize("model", list(experiment.MODELS.values()))
def test_all_requested_models_omit_sampling_settings(model):
    body = chat_body(model=model, system="Synthetic", user="Synthetic", schema={},
                     reasoning_effort="high", response_format="json_object")
    assert "temperature" not in body and body["reasoning"] == {"effort": "high"}


def test_catalog_capacity_and_exact_id_checked_without_network():
    body = {"model": "exact", "messages": [{"content": "x" * 10000}], "response_format": {"type": "json_object"}}
    catalog = {"exact_route_found": True, "advertised_id": "exact", "endpoints": [
        {"supported_parameters": ["reasoning", "response_format"], "context_length": 1000, "max_completion_tokens": 500}]}
    with pytest.raises(ValueError, match="allowance"):
        experiment.catalog_check(catalog, body)
    with pytest.raises(ValueError, match="Exact requested"):
        experiment.catalog_check({**catalog, "advertised_id": "other"}, body)
