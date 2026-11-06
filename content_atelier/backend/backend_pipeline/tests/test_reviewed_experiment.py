"""Synthetic recovery tests. Outbound HTTP is forbidden by the test suite."""
import copy
import hashlib
import json

import pytest

from experiments import model_experiment as original
from experiments import reviewed_experiment as reviewed
from backend_pipeline.llm import LiveProvider
from backend_pipeline.tests.test_model_experiment import (
    IndependentProvider,
)
from backend_pipeline.tests.test_model_experiment import (
    suite as suite,  # noqa: PLC0414 -- explicitly export the shared pytest fixture
)


@pytest.fixture
def failed_week(suite, monkeypatch):
    base, root, manifest = suite
    base = base.model_copy(update={"openrouter_moments_key": "synthetic-unused", "openrouter_angles_key": "synthetic-unused"})
    extractor = IndependentProvider("source-with-two-invalid-quotes")
    calls, users = [], []
    def mocked_response(self, **kwargs):
        stage = kwargs["stage"]
        provider = extractor if stage == "moment_extraction" else IndependentProvider(self.angles_model)
        output, metadata = provider.json_call(**kwargs)
        if stage == "moment_extraction":
            template = output["moments"][0]
            keys = sorted(reviewed.APPROVED_KEYS) + [f"other-{i}" for i in range(15)]
            output["moments"] = []
            for i, key in enumerate(keys):
                moment = copy.deepcopy(template)
                moment["local_key"] = key
                if i < 2:
                    moment["quote"] = f"An absent synthetic quote {i}."
                output["moments"].append(moment)
        else:
            users.append(kwargs["user"])
            pool = json.loads(kwargs["user"].split("Moment pool:\n", 1)[1].split("\n\nPrevious eligible", 1)[0])
            output["processed_moment_ids"] = [m["moment_id"] for m in pool]
            output["coverage_notes"] = ["Synthetic fixture selects one of 17 supplied moments."]
        model = self.moments_model if stage == "moment_extraction" else self.angles_model
        metadata["raw"]["model"] = model
        metadata["raw"]["choices"][0]["message"]["content"] = json.dumps(output)
        self.on_response(kwargs["fingerprint"], metadata["raw"])
        calls.append((stage, model))
        return output, metadata
    monkeypatch.setattr(LiveProvider, "json_call", mocked_response)
    with pytest.raises(ValueError, match="quote"):
        original.run_extraction(base, root, 4, live=True)
    extraction = original.extraction_path(root, 4)
    plan = original.read(extraction / "plan.json")
    artifact_path = extraction / "data/experiments/default/runs" / plan["run_id"] / "moment_extraction.failed.json"
    artifact = original.read(artifact_path)
    content = artifact["raw_response"]["choices"][0]["message"]["content"]
    output = json.loads(content)
    refs = original.read(next((extraction / "data").rglob("reference_map.json")))
    edits = []
    for draft in output["moments"][:2]:
        ref = draft["anchor_span_ids"][0]
        item = refs[ref]
        edits.append({"local_key": draft["local_key"], "field": "quote", "original_value": draft["quote"],
                      "proposed_value": "A useful reply helps couples compare venues.", "source_ref": ref,
                      "canonical_span_id": item["canonical_span_id"], "source_turn_text": item["text"],
                      "source_revision_sha256": item["source_revision_sha256"]})
    proposal = {"original_content_sha256": hashlib.sha256(content.encode()).hexdigest(), "changes": edits}
    proposal_path = root.parent / "approved-two-quote-proposal.json"
    original.write(proposal_path, proposal)
    return base, root, proposal_path, calls, users, artifact_path, manifest


def test_recovery_requires_explicit_approval_without_new_calls(failed_week):
    _, root, proposal, calls, _, _, _ = failed_week
    with pytest.raises(ValueError, match="approval"):
        reviewed.prepare_reviewed_recovery(root, proposal)
    assert len(calls) == 1 and not reviewed.home(root).exists()


def test_approved_recovery_preserves_failure_and_sends_three_equal_angle_only_calls(failed_week):
    base, root, proposal, calls, users, artifact_path, manifest = failed_week
    before = {p: p.read_bytes() for p in original.extraction_path(root, 4).rglob("*") if p.is_file()}
    week3_before = {p: p.read_bytes() for p in (root / "cells/week3").rglob("*") if p.is_file()}
    prepared = reviewed.prepare_reviewed_recovery(root, proposal, approved=True)
    assert prepared["moments"] == 17 and prepared["new_calls"] == 0 and len(calls) == 1
    pool, seal = reviewed.verify_reviewed_pool(root)
    assert pool["mode"] == "live_reviewed" and "failed" in pool["evidence_origin"]
    assert original.read(artifact_path)["status"] == "failed"
    assert original.verify_suite(root) == manifest
    with pytest.raises(ValueError, match="Shared extraction"):
        original.run_cell(base, root, 4, "sol", live=True)
    for slug in original.MODELS:
        result = reviewed.run_reviewed_cell(base, root, slug, live=True)
        assert result["angles"] == 1 and result["pool_hash"] == seal["pool_hash"]
        assert result["embedding_requests"] == 0 and result["similarity_status"] == "not_run"
        cell = original.cell_path(root, 4, slug)
        assert "Evidence provenance" in (cell / "review.md").read_text(encoding="utf-8")
        assert original.read(cell / "data/experiments/default/runs" / result["run_id"] / "manifest.json")["parent_run_id"] == pool["evidence_run_id"]
        with pytest.raises((ValueError, FileExistsError)):
            reviewed.run_reviewed_cell(base, root, slug, live=True)
    assert calls == [("moment_extraction", original.EXTRACTOR)] + [("angle_generation", m) for m in original.MODELS.values()]
    assert users[0] == users[1] == users[2]
    history = users[0].split("Previous eligible signatures, for awareness only:\n", 1)[1]
    assert json.loads(history.split("\n\nExisting approved Reel examples:", 1)[0]) == []
    assert all(p.read_bytes() == data for p, data in before.items())
    assert all(p.read_bytes() == data for p, data in week3_before.items())
    assert len(list(root.rglob("*.dispatch.json"))) == 4 and not (root / "active-cell.lock").exists()
    assert not (root / "shared/week4/freeze.json").exists()


@pytest.mark.parametrize("change", ["derived", "edits", "pool", "receipt", "request", "source", "adapter"])
def test_recovery_tampering_blocks_dispatch(change, failed_week, monkeypatch):
    base, root, proposal, calls, _, artifact_path, _ = failed_week
    reviewed.prepare_reviewed_recovery(root, proposal, approved=True)
    target = reviewed.home(root)
    if change == "source":
        path = root / "inputs/week4/meeting.vtt"
        path.write_bytes(path.read_bytes() + b"changed")
    elif change == "adapter":
        monkeypatch.setattr(reviewed, "adapter_identity", lambda: {"changed": "changed"})
    else:
        paths = {"derived": target / "derived-response.json", "edits": target / "edit-log.json",
                 "pool": target / "evidence-packet.json", "request": original.cell_path(root, 4, "sol") / "prepared-angle.request.json",
                 "receipt": artifact_path}
        path = paths[change]
        value = original.read(path)
        if isinstance(value, dict):
            value["tampered"] = True
        else:
            value[0]["proposed_value"] = "Changed"
        original.write(path, value)
    with pytest.raises(ValueError):
        reviewed.run_reviewed_cell(base, root, "sol", live=True)
    assert len(calls) == 1 and not (original.cell_path(root, 4, "sol") / "started.json").exists()


@pytest.mark.parametrize("change", ["field", "quote", "anchor", "old_quote", "revision", "duplicate"])
def test_only_attributable_quote_edits_can_be_admitted(change, failed_week):
    _, root, proposal_path, calls, _, _, _ = failed_week
    proposal = original.read(proposal_path)
    edit = proposal["changes"][0]
    if change == "field":
        edit["field"] = "proposition"
    elif change == "quote":
        edit["proposed_value"] = "An invented quote."
    elif change == "anchor":
        edit["source_ref"] = "m1.t0002"
    elif change == "old_quote":
        edit["original_value"] = "Changed"
    elif change == "revision":
        edit["source_revision_sha256"] = "Changed"
    else:
        proposal["changes"][1] = copy.deepcopy(edit)
    original.write(proposal_path, proposal)
    with pytest.raises(ValueError):
        reviewed.prepare_reviewed_recovery(root, proposal_path, approved=True)
    assert len(calls) == 1 and not (reviewed.home(root) / "freeze.json").exists()


def test_live_flag_and_repeat_preparation_guards(failed_week):
    base, root, proposal, calls, _, _, _ = failed_week
    reviewed.prepare_reviewed_recovery(root, proposal, approved=True)
    with pytest.raises(ValueError, match="already exists"):
        reviewed.prepare_reviewed_recovery(root, proposal, approved=True)
    with pytest.raises(ValueError, match="--live"):
        reviewed.run_reviewed_cell(base, root, "sol")
    assert len(calls) == 1
