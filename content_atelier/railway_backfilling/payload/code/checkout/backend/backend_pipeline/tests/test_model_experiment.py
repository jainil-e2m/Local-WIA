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
    def __init__(self, marker, *, invalid=False, invalid_angle=False, empty=False):
        super().__init__()
        self.marker, self.invalid, self.users = marker, invalid, []
        self.invalid_angle, self.empty = invalid_angle, empty

    def json_call(self, **kwargs):
        self.users.append(kwargs["user"])
        output, metadata = super().json_call(**kwargs)
        if kwargs["stage"] == "moment_extraction":
            output["moments"][0]["context_summary"] += f" Synthetic marker {self.marker}."
            if self.invalid:
                output["moments"][0]["quote"] = "An absent synthetic quote."
            if self.empty:
                output["moments"] = []
                output["coverage_notes"] = ["Synthetic empty shortlist with a complete delivery acknowledgement."]
        else:
            output["angles"][0]["title"] = self.marker
            if self.invalid_angle:
                output["angles"][0]["source_assertions"] = ["[foreign] Unsupported synthetic reference."]
        metadata["raw"]["choices"][0]["message"]["content"] = json.dumps(output)
        return output, metadata


def test_prepare_freezes_two_extractions_and_six_angle_only_plans(suite):
    base, root, manifest = suite
    assert manifest["max_paid_calls"] == 8 and len(manifest["cells"]) == 6 and len(manifest["extractions"]) == 2
    assert not list(root.rglob("*.dispatch.json"))
    assert not base.data_root.exists()
    roots = set()
    for week in (3, 4):
        settings = experiment.extraction_settings(base, root, week)
        roots.add(settings.data_root)
        body = experiment.read(experiment.extraction_path(root, week) / "prepared-extraction.request.json")
        assert body["model"] == experiment.EXTRACTOR
        assert "temperature" not in body and body["reasoning"] == {"effort": "high"}
        for slug in experiment.MODELS:
            settings = experiment.cell_settings(base, root, week, slug)
            roots.add(settings.data_root)
            assert not settings.embeddings_enabled
            assert settings.llm_reasoning_effort == "high"
            cell = experiment.cell_path(root, week, slug)
            assert settings.openrouter_moments_model == experiment.EXTRACTOR
            assert not (cell / "prepared-extraction.request.json").exists()
            assert experiment.read(cell / "plan.json")["stage"] == "angle_generation"
    assert len(roots) == 8


def test_eight_calls_share_exact_evidence_but_never_read_sibling_angles_or_vectors(suite, monkeypatch):
    base, root, _ = suite
    def forbidden(*args, **kwargs):
        raise AssertionError("History, embeddings and ranking are forbidden")
    monkeypatch.setattr(pipeline_module.Pipeline, "_load_history", forbidden)
    monkeypatch.setattr(pipeline_module, "rank", forbidden)
    finished = []
    all_providers = []
    for week in (3, 4):
        extractor = IndependentProvider(f"shared-evidence-week{week}")
        extracted = experiment.run_extraction(base, root, week, provider=extractor)
        assert extractor.calls == {"moment_extraction": 1}
        all_providers.append(extractor)
        requests = []
        for slug in experiment.MODELS:
            marker = f"synthetic-w{week}-{slug}"
            provider = IndependentProvider(marker)
            all_providers.append(provider)
            result = experiment.run_cell(base, root, week, slug, provider=provider)
            assert provider.calls == {"angle_generation": 1}
            assert result["similarity_status"] == "not_run"
            assert result["pool_hash"] == extracted["pool_hash"]
            assert f"shared-evidence-week{week}" in provider.users[0]
            assert all(previous not in provider.users[0] for previous in finished)
            history = provider.users[0].split("Previous eligible signatures, for awareness only:\n", 1)[1]
            assert json.loads(history.split("\n\nExisting approved Reel examples:", 1)[0]) == []
            requests.append(provider.users[0])
            cell = experiment.cell_path(root, week, slug)
            before = (cell / "review.md").read_bytes()
            assert marker.encode() in before
            assert "Supporting source content" in before.decode()
            assert len(list((cell / "data/service_calls").rglob("response.raw.json"))) == 1
            with pytest.raises((ValueError, FileExistsError)):
                experiment.run_cell(base, root, week, slug, provider=provider)
            assert before == (cell / "review.md").read_bytes()
            finished.append(marker)
        assert requests[0] == requests[1] == requests[2]
        assert all(f"shared-evidence-week{7-week}" not in request for request in requests)
        with pytest.raises((ValueError, FileExistsError)):
            experiment.run_extraction(base, root, week, provider=extractor)
    assert sum(sum(p.calls.values()) for p in all_providers) == 8
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


def test_failed_shared_extraction_blocks_all_week_angles_but_not_the_other_week(suite):
    base, root, _ = suite
    failed = IndependentProvider("bad-source-binding", invalid=True)
    with pytest.raises(ValueError, match="quote"):
        experiment.run_extraction(base, root, 3, provider=failed)
    assert failed.calls == {"moment_extraction": 1}
    for slug in experiment.MODELS:
        with pytest.raises(ValueError, match="Shared extraction"):
            experiment.run_cell(base, root, 3, slug, provider=IndependentProvider("unused"))
    experiment.run_extraction(base, root, 4, provider=IndependentProvider("other-week-source"))
    good = IndependentProvider("independent-sol")
    result = experiment.run_cell(base, root, 4, "sol", provider=good)
    assert result["angles"] == 1
    assert "bad-source-binding" not in good.users[0]


def test_runtime_and_plan_drift_fail_before_run(suite, monkeypatch):
    base, root, manifest = suite
    changed = copy.deepcopy(manifest["runtime_identity"])
    changed["prompts.py"] = "changed"
    with monkeypatch.context() as patch:
        patch.setattr(experiment, "runtime_identity", lambda: changed)
        with pytest.raises(ValueError, match="engine files"):
            experiment.run_cell(base, root, 3, "sol", provider=IndependentProvider("unused"))
    cell = experiment.extraction_path(root, 3)
    plan = experiment.read(cell / "plan.json")
    experiment.write(cell / "plan.json", {**plan, "model": "different"})
    with pytest.raises(ValueError, match="plan differs"):
        experiment.run_extraction(base, root, 3, provider=IndependentProvider("unused"))


def test_exact_route_guard_refuses_model_substitution_and_second_dispatch(suite, monkeypatch):
    base, root, _ = suite
    cell = experiment.extraction_path(root, 3)
    settings = experiment.extraction_settings(base, root, 3)
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


def test_bad_angle_output_does_not_change_shared_pool_or_other_angle_calls(suite):
    base, root, _ = suite
    experiment.run_extraction(base, root, 3, provider=IndependentProvider("source-only"))
    _, before = experiment.verify_pool(root, 3)
    broken = IndependentProvider("bad-angle", invalid_angle=True)
    with pytest.raises(ValueError, match="source assertion"):
        experiment.run_cell(base, root, 3, "sol", provider=broken)
    good = IndependentProvider("independent-sonnet")
    result = experiment.run_cell(base, root, 3, "sonnet", provider=good)
    assert broken.users == good.users
    assert result["pool_hash"] == before["pool_hash"]
    assert experiment.verify_pool(root, 3)[1] == before


@pytest.mark.parametrize("change", ["pool", "angle_request", "original_output"])
def test_shared_pool_and_its_lineage_cannot_drift(change, suite):
    base, root, _ = suite
    result = experiment.run_extraction(base, root, 3, provider=IndependentProvider("source-only"))
    if change == "pool":
        path = root / "shared/week3/evidence-packet.json"
        value = experiment.read(path)
        value["moment_packet"][0]["context_summary"] = "changed"
    elif change == "angle_request":
        path = experiment.cell_path(root, 3, "sol") / "prepared-angle.request.json"
        value = experiment.read(path)
        value["messages"][1]["content"] = "changed"
    else:
        path = experiment.extraction_path(root, 3) / "data/experiments/default/runs" / result["run_id"] / "moment_extraction.json"
        value = experiment.read(path)
        value["output"]["coverage_notes"] = ["changed"]
    experiment.write(path, value)
    with pytest.raises(ValueError):
        experiment.run_cell(base, root, 3, "sonnet", provider=IndependentProvider("unused"))
    assert not (experiment.cell_path(root, 3, "sonnet") / "started.json").exists()


def test_empty_valid_shared_pool_does_not_purchase_three_empty_angle_calls(suite):
    base, root, _ = suite
    result = experiment.run_extraction(base, root, 3, provider=IndependentProvider("empty", empty=True))
    assert result["moments"] == 0
    for slug in experiment.MODELS:
        with pytest.raises(ValueError, match="nonempty"):
            experiment.run_cell(base, root, 3, slug, provider=IndependentProvider("unused"))


def test_synthetic_extraction_cannot_be_promoted_into_a_live_angle_run(suite):
    base, root, _ = suite
    experiment.run_extraction(base, root, 3, provider=IndependentProvider("synthetic"))
    with pytest.raises(ValueError, match="live extraction evidence"):
        experiment.run_cell(base, root, 3, "sol", live=True)
    assert not (experiment.cell_path(root, 3, "sol") / "started.json").exists()


def test_guarded_live_code_path_uses_one_extraction_and_equal_angle_requests_without_http(suite, monkeypatch):
    base, root, _ = suite
    base = base.model_copy(update={"openrouter_moments_key": "synthetic-unused", "openrouter_angles_key": "synthetic-unused"})
    extractor = IndependentProvider("shared-only")
    angles = {model: IndependentProvider(f"output-{slug}") for slug, model in experiment.MODELS.items()}
    seen = []
    def mocked_response(self, **kwargs):
        stage = kwargs["stage"]
        model = self.moments_model if stage == "moment_extraction" else self.angles_model
        provider = extractor if stage == "moment_extraction" else angles[model]
        output, metadata = provider.json_call(**kwargs)
        metadata["raw"]["model"] = model
        self.on_response(kwargs["fingerprint"], metadata["raw"])
        seen.append((stage, model))
        return output, metadata
    monkeypatch.setattr(LiveProvider, "json_call", mocked_response)
    extraction = experiment.run_extraction(base, root, 3, live=True)
    for slug in experiment.MODELS:
        result = experiment.run_cell(base, root, 3, slug, live=True)
        assert result["pool_hash"] == extraction["pool_hash"]
    assert seen == [("moment_extraction", experiment.EXTRACTOR)] + [
        ("angle_generation", model) for model in experiment.MODELS.values()]
    assert len({p.users[0] for p in angles.values()}) == 1
    assert len(list(root.rglob("*.dispatch.json"))) == 4


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
