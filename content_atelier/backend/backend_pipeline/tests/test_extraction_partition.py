"""E.B12a on the file-backed runner: one unbindable quote no longer fails the week.

The runner keeps moments that bind, repairs whitespace and punctuation near-misses with the repair recorded, and keeps
the rest as unverified records that never reach the angle call. A schema or coverage failure still fails the week
(the accepted coverage rule). Synthetic fixtures and fake providers only: no HTTP and no paid model calls.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from backend_pipeline.config import Settings
from backend_pipeline.moment_validation import COVERAGE_RULE, REPAIR_RULE, MomentPartition
from backend_pipeline.pipeline import Pipeline
from backend_pipeline.tests.test_generation_only import CompactCountingProvider
from backend_pipeline.weekly import resolve_moment_references

EXACT = "A useful reply helps couples compare venues."
NEAR = "A useful reply helps couples, compare venues"  # Punctuation only: repaired to the exact text.
INVENTED = "An invented quotation absent from the source."


def strict_extraction(self, output, run_id, transcripts):
    """The file runner before E.B12a, for building saved failed attempts: one unbindable quote failed the week."""
    resolved = resolve_moment_references(output, self._compact_refs) if self._compact_refs else output
    return MomentPartition(moments=self._parse_moments(resolved, run_id, transcripts))


class MixedExtractionProvider(CompactCountingProvider):
    """One exact, one near-miss and one invented quote; the angle answer covers whatever pool it is sent."""

    def __init__(self, mutate=None):
        super().__init__()
        self.mutate, self.angle_users = mutate, []

    def json_call(self, **kwargs):
        if kwargs["stage"] == "moment_extraction" and self.mutate == "no_call":
            raise AssertionError("A saved response must be re-validated without a provider call")
        output, meta = super().json_call(**kwargs)
        if kwargs["stage"] == "moment_extraction":
            near, invented = copy.deepcopy(output["moments"][0]), copy.deepcopy(output["moments"][0])
            near.update(local_key="near", quote=NEAR, proposition="A second reading of the same turn.")
            invented.update(local_key="invented", quote=INVENTED)
            output["moments"] += [near, invented]
            if self.mutate == "schema":
                output["moments"][2]["strength"] = "high"
            elif self.mutate == "coverage":
                output["processed_meetings"][0]["span_count"] = 99
            elif self.mutate == "all_unbindable":
                output["moments"] = [invented]
        else:
            self.angle_users.append(kwargs["user"])
            pool = json.loads(kwargs["user"].split("Moment pool:\n", 1)[1].split("\n\nPrevious eligible", 1)[0])
            output["processed_moment_ids"] = [m["moment_id"] for m in pool]
        meta["raw"]["choices"][0]["message"]["content"] = json.dumps(output)
        return output, meta


@pytest.fixture
def week(tmp_path: Path) -> Settings:
    folder = tmp_path / "inputs" / "week1"
    folder.mkdir(parents=True)
    (folder / "meeting.vtt").write_bytes(
        b"WEBVTT\r\n\r\n1\r\n00:00:00.000 --> 00:00:05.000\r\nWhitney: A useful reply helps couples compare venues.\r\n\r\n"
        b"2\r\n00:00:04.000 --> 00:00:09.500\r\nWhitney: This is an observation,\r\nnot a measured conversion result.\r\n\r\n")
    return Settings(data_root=tmp_path / "data", transcript_root=tmp_path / "inputs", llm_payload_format="compact_weekly",
                    embedding_dimensions=3)


def test_file_runner_keeps_every_bindable_moment_and_records_the_repair(week):
    provider = MixedExtractionProvider()
    pipeline = Pipeline(week, provider)
    result = pipeline.run(1, run_id="mixed")
    prefix = "experiments/default/runs/mixed"
    assert result["moments"] == 2 and provider.calls == {"moment_extraction": 1, "angle_generation": 1}
    assert pipeline.store.read_json(f"{prefix}/manifest.json")["status"] == "generation_completed"
    moments = pipeline.store.read_json(f"{prefix}/moments.json")
    assert [m["quote"] for m in moments] == [EXACT, "A useful reply helps couples compare venues"]
    validation = pipeline.store.read_json(f"{prefix}/moment_validation.json")
    assert validation["repair_rule"] == REPAIR_RULE and validation["coverage_rule"] == COVERAGE_RULE
    [repair] = validation["quote_repairs"]
    assert repair["local_key"] == "near" and repair["original_quote"] == NEAR
    assert repair["repaired_quote"] == "A useful reply helps couples compare venues" and repair["moment_id"] == moments[1]["moment_id"]
    [unverified] = validation["unverified_moments"]
    assert unverified["local_key"] == "invented" and "quote must match" in unverified["reason"]
    assert unverified["usable_as_proof"] is False and validation["unverified_usable_as_proof"] is False


def test_unverified_moments_never_reach_the_angle_call_or_the_candidates(week):
    provider = MixedExtractionProvider()
    pipeline = Pipeline(week, provider)
    pipeline.run(1, run_id="proof")
    [user] = provider.angle_users
    assert INVENTED not in user and NEAR not in user, "only bound or repaired quotes are evidence"
    kept = {m["moment_id"] for m in pipeline.store.read_json("experiments/default/runs/proof/moments.json")}
    candidates = pipeline.store.read_json("experiments/default/runs/proof/candidates.json")
    assert candidates and all(set(c["moment_ids"]) <= kept for c in candidates)
    assert all(m["quote"] != INVENTED for m in pipeline.store.read_json("experiments/default/runs/proof/moments.json"))


@pytest.mark.parametrize("mutation,message", [("schema", "strength"), ("coverage", "coverage"),
                                              ("all_unbindable", "No proposed moment binds")])
def test_a_response_level_failure_still_fails_the_week_before_the_angle_call(week, mutation, message):
    provider = MixedExtractionProvider(mutation)
    pipeline = Pipeline(week, provider)
    with pytest.raises(ValueError, match=message):
        pipeline.run(1, run_id=f"failed-{mutation}")
    prefix = f"experiments/default/runs/failed-{mutation}"
    assert pipeline.store.read_json(f"{prefix}/manifest.json")["status"] == "failed"
    assert pipeline.store.read_json(f"{prefix}/moment_extraction.failed.json")["status"] == "failed"
    # A response that breaks its schema gets exactly one repair call (0.B4); a coverage or binding failure is a content
    # failure and gets none. Either way no angle call is paid for after a week-level failure.
    assert provider.calls == {"moment_extraction": 2 if mutation == "schema" else 1},         "no angle call is paid for after a week-level failure"


def test_a_saved_strict_failure_is_revalidated_by_the_file_runner_without_a_provider_call(week, monkeypatch):
    first = MixedExtractionProvider()
    with monkeypatch.context() as earlier:
        earlier.setattr(Pipeline, "_extraction_partition", strict_extraction)
        with pytest.raises(ValueError, match="quote must match"):
            Pipeline(week, first).run(1, run_id="strict-era")
    assert first.calls == {"moment_extraction": 1}
    again = MixedExtractionProvider("no_call")
    pipeline = Pipeline(week, again)
    result = pipeline.run(1, run_id="revalidated")
    assert again.calls == {"angle_generation": 1} and result["moments"] == 2
    validation = pipeline.store.read_json("experiments/default/runs/revalidated/moment_validation.json")
    assert validation["revalidated_from_attempt"].startswith("service_calls/") and len(validation["quote_repairs"]) == 1
