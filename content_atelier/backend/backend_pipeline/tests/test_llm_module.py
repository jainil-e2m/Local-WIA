"""0.B4: the llm module. Mock providers and transports only; the conftest guard forbids real outbound HTTP.

Done when: saved artifacts replay with no provider call and identical hashes; a forced schema failure makes exactly one
repair; every call writes an `llm_runs` row with model, prompt version, knowledge-base version, tokens and cost (the
database half is in test_llm_runs_db.py).
"""
from __future__ import annotations

import ast
import copy
import json
from collections import Counter
from pathlib import Path

import httpx
import pytest

from backend_pipeline.config import Settings
from backend_pipeline.llm import (LiveProvider, chat_body, mark_prefix, prefix_hash, stage_body, stage_fingerprint,
                                  workflow_fingerprint)
from backend_pipeline.llm.call import json_call
from backend_pipeline.llm.providers import IncompleteResponse, InvalidJson
from backend_pipeline.llm.runs import LlmRuns
from backend_pipeline.llm.stage import SchemaViolation
from backend_pipeline.models import RunManifest
from backend_pipeline.pipeline import Pipeline
from backend_pipeline.store import canonical_hash
from backend_pipeline.tests.plans import OpenTestPlan
from backend_pipeline.tests.test_reuse import CountingProvider, harness  # noqa: F401 (the shared fixture)

BACKEND = Path(__file__).resolve().parents[2]


def ledger(settings):
    path = settings.data_root / "llm_runs.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()] if path.is_file() else []


# --- fingerprints: unchanged, so saved artifacts keep their keys -----------------------------------------------------

def test_the_stage_fingerprint_is_the_recipe_saved_artifacts_were_keyed_with():
    request = chat_body(model="openai/gpt-6-luna", system="s", user="u", schema={"type": "object"})
    expected = canonical_hash({"cache_version": 2, "validation_version": 4, "namespace": "live", "stage": "angle_generation",
                               "endpoint": "https://openrouter.ai/api/v1", "request": request, "input_hash": "abc"})
    assert stage_fingerprint(mode="live", stage="angle_generation", endpoint="https://openrouter.ai/api/v1", request=request,
                             input_hash="abc") == expected
    assert stage_fingerprint(mode="fake", stage="embedding", endpoint="e", request={}, input_hash=None) == canonical_hash(
        {"cache_version": 2, "validation_version": 2, "namespace": "fake", "stage": "embedding", "endpoint": "e",
         "request": {}, "input_hash": None})
    # A pinned value: a change to the recipe would orphan every saved artifact. (It ended in `or True`, so it pinned nothing.)
    assert stage_fingerprint(mode="live", stage="moment_extraction", endpoint="https://openrouter.ai/api/v1",
                             request={"model": "m"}, input_hash="h") == \
        "b0605d1a0d7646d69275fb694bdfedf1f54713719673db8d3d7daf599f5be069"
    # The 12 October SQL run's artifacts were saved under validator version 3; reading their keys names it.
    assert stage_fingerprint(mode="live", stage="moment_extraction", endpoint="https://openrouter.ai/api/v1", request={"model": "m"},
                             input_hash="h", validation_version=3) == canonical_hash(
        {"cache_version": 2, "validation_version": 3, "namespace": "live", "stage": "moment_extraction",
         "endpoint": "https://openrouter.ai/api/v1", "request": {"model": "m"}, "input_hash": "h"})


def test_the_replay_check_finds_every_saved_artifact_replayable_and_names_an_older_validator(harness):  # noqa: F811
    """0.B4 on saved artifacts: each key recomputes from its recorded request, each output keeps its hash, and nothing is
    called. An artifact keyed under an older validator version is named as needing E.B12a's re-check."""
    from backend_pipeline.llm import replay_check
    settings, provider, pipeline = harness
    live = settings.model_copy(update={"live_enabled": True, "openrouter_moments_key": "k", "openrouter_angles_key": "k",
                                      "embedding_api_key": "k"})
    Pipeline(live, provider).run(1, mode="live", run_id="saved")
    calls = dict(provider.calls)
    report = replay_check.check(settings.data_root)
    assert report["not_replayable"] == 0 and report["replayable"] == len(report["artifacts"]) >= 2
    assert {a["stage"] for a in report["artifacts"]} >= {"moment_extraction", "angle_generation"}
    assert all(a["output_hash_identical"] and a["validation_version"] in (2, 4) and "revalidation_needed" not in a
               for a in report["artifacts"])
    assert dict(provider.calls) == calls, "the check calls nothing"

    # Re-key one saved artifact as the 12 October run did (validator version 3): still found, named as needing a re-check.
    from backend_pipeline.store import JsonStore
    store = JsonStore(settings.data_root)
    entry = next(a for a in report["artifacts"] if a["stage"] == "moment_extraction")
    data = store.find_artifact(entry["fingerprint"])
    old_key = stage_fingerprint(mode="live", stage="moment_extraction", endpoint=live.openrouter_base_url.rstrip("/"),
                                request=data["request"], input_hash=data["input_hashes"][0], validation_version=3)
    store.write_json(f"service_calls/{old_key}/attempts/a/artifact.json", {**data, "request_fingerprint": old_key})
    store.write_json(f"cache/artifacts/{old_key}.json", {"artifact_path": f"service_calls/{old_key}/attempts/a/artifact.json"})
    again = {a["fingerprint"]: a for a in replay_check.check(settings.data_root)["artifacts"]}
    assert again[old_key]["validation_version"] == 3 and "E.B12a" in again[old_key]["revalidation_needed"]

    # A changed output is not replayable.
    store.write_json(f"service_calls/{old_key}/attempts/a/artifact.json", {**data, "request_fingerprint": old_key,
                                                                           "output": {"moments": []}}, overwrite=True)
    assert replay_check.check(settings.data_root)["not_replayable"] == 1


def test_the_workflow_fingerprint_is_the_brief_and_pack_recipe():
    request = {"model": "m", "messages": []}
    assert workflow_fingerprint(workflow="w", stage="brief_write", request=request, endpoint="e", synthetic=True) == canonical_hash(
        {"workflow": "w", "stage": "brief_write", "request": request, "endpoint": "e", "synthetic": True})


# --- replay: no provider call, identical hashes, a replayed row ---------------------------------------------------------

class NoCalls:
    def json_call(self, **kwargs):
        pytest.fail("a replay must not call the provider")

    embed = json_call


def test_saved_artifacts_replay_with_no_provider_call_and_identical_hashes(harness):  # noqa: F811
    settings, provider, _ = harness
    live = settings.model_copy(update={"live_enabled": True, "openrouter_moments_key": "k", "openrouter_angles_key": "k",
                                      "embedding_api_key": "k"})
    pipeline = Pipeline(live, provider)
    first = pipeline.run(1, mode="live", run_id="first")
    assert provider.calls["moment_extraction"] == 1 and provider.calls["angle_generation"] == 1
    saved = {stage: pipeline.store.read_json(f"experiments/default/runs/first/{stage}.json")
             for stage in ("moment_extraction", "angle_generation")}
    replay = Pipeline(live, NoCalls())
    second = replay.run(1, mode="replay", run_id="second")
    assert second["moments"] == first["moments"]
    for stage, original in saved.items():
        again = replay.store.read_json(f"experiments/default/runs/second/{stage}.json")
        assert again["request_fingerprint"] == original["request_fingerprint"], "the same key"
        assert again["output_hash"] == original["output_hash"] and again["output"] == original["output"], "the same bytes"
    rows = [r for r in ledger(live) if r["details"].get("run_id") == "second"]
    assert sorted(r["stage"] for r in rows) == ["angle_generation", "embedding", "moment_extraction"], "the vector is recorded too"
    assert {r["status"] for r in rows} == {"replayed"} and all(r["cost_usd"] == 0 for r in rows)


def test_every_call_is_recorded_with_its_model_prompt_version_and_usage(harness):  # noqa: F811
    settings, provider, pipeline = harness
    pipeline.run(1, run_id="recorded")
    rows = ledger(settings)
    assert [r["stage"] for r in rows] == ["moment_extraction", "angle_generation", "embedding"]
    for row in rows:
        assert row["status"] == "succeeded" and row["provider"] == "fake" and row["routing_policy"] == "offline-fake"
        assert row["model"] == (settings.embedding_model if row["stage"] == "embedding" else settings.model_for(row["stage"]))
        assert row["prompt_version"] or row["stage"] == "embedding", "the prompt version is on every row"
        assert row["input_tokens"] == 10 and (row["output_tokens"] == 10 or row["stage"] == "embedding"), "tokens from the usage"
        assert row["cost_usd"] == 0
        assert row["stage"] == "embedding" or len(row["details"]["prefix_hash"]) == 64, "a chat call records its prefix"


# --- one repair -------------------------------------------------------------------------------------------------------------

class Flaky(CountingProvider):
    """Answers the extraction badly the first `bad` times, then well."""

    def __init__(self, bad=1, **kwargs):
        super().__init__(**kwargs)
        self.bad, self.users = bad, []

    def json_call(self, *, stage, system, user, schema, fingerprint):
        plain = user.split("\n\n## Correction needed", 1)[0]
        output, meta = super().json_call(stage=stage, system=system, user=plain, schema=schema, fingerprint=fingerprint)
        self.users.append(user)
        if stage == "moment_extraction" and self.calls[stage] <= self.bad:
            output = {key: value for key, value in output.items() if key != "moments"}
        return output, meta


def test_a_schema_failure_makes_exactly_one_repair(harness):  # noqa: F811
    settings, _, _ = harness
    provider = Flaky(bad=1)
    pipeline = Pipeline(settings, provider)
    pipeline.run(1, run_id="repaired")
    assert provider.calls["moment_extraction"] == 2, "the failed answer and its one repair"
    assert "## Correction needed" in provider.users[1] and "moments" in provider.users[1]
    artifact = pipeline.store.read_json("experiments/default/runs/repaired/moment_extraction.json")
    assert artifact["status"] == "validated" and artifact["metadata"]["repair"]["attempt"] == 1
    assert artifact["metadata"]["repair"]["of"] == artifact["request_fingerprint"]
    rows = [r for r in ledger(settings) if r["stage"] == "moment_extraction"]
    assert len(rows) == 2 and rows[1]["details"]["repair_of"] == artifact["request_fingerprint"]
    # Both calls have their own cost record, so the run's summary counts both.
    summary = pipeline.store.read_json("experiments/default/runs/repaired/cost_summary.json")
    assert summary["stages"][0]["attempt_count"] == 2
    # The repaired answer is what is cached: the next run replays it with no call at all.
    again = Flaky(bad=0)
    Pipeline(settings, again).run(1, run_id="again")
    assert again.calls["moment_extraction"] == 0


def test_a_second_schema_failure_stops_after_the_one_repair(harness):  # noqa: F811
    settings, _, _ = harness
    provider = Flaky(bad=5)
    pipeline = Pipeline(settings, provider)
    with pytest.raises(ValueError, match="envelope") as caught:
        pipeline.run(1, run_id="still-bad")
    assert provider.calls["moment_extraction"] == 2 and provider.calls["angle_generation"] == 0
    assert any("repair call's answer failed too" in note for note in caught.value.__notes__)
    assert pipeline.store.read_json("experiments/default/runs/still-bad/manifest.json")["status"] == "failed"


class Stub:
    records_runs = False

    def __init__(self):
        self.calls = Counter()

    def json_call(self, *, stage, system, user, schema, fingerprint):
        self.calls[stage] += 1
        return {"moments": [], "processed_span_ids": [], "coverage_notes": []}, {"fake": True}


SCHEMA = {"type": "object", "title": "x", "required": ["moments"], "properties": {"moments": {"type": "array"}}}


def manifest(mode):
    return RunManifest(run_id=f"r-{mode}", week_index=1, source_root="x", source_ids=[], prompt_profile="p", model_id="m",
                       embedding_profile="e", mode=mode)


def test_a_record_that_cannot_be_written_never_breaks_the_call(tmp_path):
    """The llm_runs record's promise: a call that happened is never undone by its bookkeeping. A fallback file in a folder
    the process may not write (the image's /app) is logged instead of raising."""
    blocked = tmp_path / "not-a-folder"
    blocked.write_text("a file where the folder should be", encoding="utf-8")
    runs = LlmRuns(file=blocked / "llm_runs.jsonl")
    call_id = runs.record(stage="moment_extraction", model="m", fingerprint="f", status="replayed")
    assert call_id.startswith("llm_")
    runs.annotate(call_id, prompt_version="p")


def test_a_content_failure_is_not_repaired_and_replay_never_repairs(tmp_path):
    stub = Stub()
    pipeline = Pipeline(Settings(data_root=tmp_path / "data"), stub)
    run = manifest("fake")
    seen = Counter()

    def stricter(output):
        seen["validate"] += 1
        raise ValueError("a quote that is not in the source")
    with pytest.raises(ValueError, match="not in the source"):
        pipeline.calls.call_json("moment_extraction", run, "experiments/default/runs/content", "s", "u", "h", SCHEMA, validate=stricter)
    assert stub.calls["moment_extraction"] == 1 and seen["validate"] == 1, "no repair for a content failure"
    replay = manifest("replay")
    with pytest.raises(RuntimeError, match="Replay cache miss"):
        pipeline.calls.call_json("moment_extraction", replay, "experiments/default/runs/replay", "s", "u2", "h2", SCHEMA,
                                 validate=lambda out: None)
    assert stub.calls["moment_extraction"] == 1, "a replay never calls, so it never repairs"


def reply(content, *, finish="stop"):
    return httpx.Response(200, json={"choices": [{"finish_reason": finish, "message": {"content": content}}],
                                     "usage": {"cost": 0.01, "prompt_tokens": 7, "completion_tokens": 3}},
                          request=httpx.Request("POST", "https://x"))


def live(plan=None, **kwargs):
    return LiveProvider(llm_base_url="https://openrouter.ai/api/v1", moments_model="openai/gpt-6-luna", moments_key="k",
                        angles_model="openai/gpt-6.1-sol", angles_key="k", embedding_base_url="https://openrouter.ai/api/v1",
                        embedding_model="openai/text-embedding-3-small", embedding_key="k", dimensions=1536, timeout=5,
                        plan=plan or OpenTestPlan(), **kwargs)


def test_unparseable_json_is_repaired_once_and_a_cut_off_answer_is_asked_again_never_repaired(monkeypatch):
    answers = iter(["{not json", '{"edits": []}'])
    sent = []

    def handle(transport, request):
        sent.append(json.loads(request.content))
        return reply(next(answers))
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", handle)
    plan = OpenTestPlan()
    out = json_call(live(plan), None, stage="context_mining", model="openai/gpt-6.1-sol", system="s", user="u",
                    schema={"type": "object"}, fingerprint="fp")
    assert out == {"edits": []} and len(sent) == 2 and len(plan.reserved) == 2, "the repair is its own planned call"
    assert "{not json" in sent[1]["messages"][1]["content"], "the repair shows the rejected answer"
    # A cut-off answer cannot be repaired: it is asked once more with a raised output limit, and no more.
    sent.clear()
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request",
                        lambda t, r: (sent.append(json.loads(r.content)), reply('{"edits": [', finish="length"))[1])
    with pytest.raises(IncompleteResponse, match="after one retry"):
        json_call(live(), None, stage="context_mining", model="m", system="s", user="u", schema={"type": "object"}, fingerprint="f2")
    assert len(sent) == 2 and sent[1]["max_tokens"] == 24000 and sent[0]["messages"] == sent[1]["messages"]


def test_the_validator_decides_what_a_repair_may_fix():
    class Provider:
        records_runs = False

        def __init__(self, answers):
            self.answers, self.n = answers, 0

        def json_call(self, **kwargs):
            self.n += 1
            return self.answers[min(self.n, len(self.answers)) - 1], {"fake": True}

    def need_edits(out):
        if "edits" not in out:
            raise SchemaViolation("missing edits")
    rows = LlmRuns()
    good = Provider([{}, {"edits": []}])
    assert json_call(good, rows, stage="context_mining", model="m", system="s", user="u", schema={}, fingerprint="f",
                     validate=need_edits) == {"edits": []} and good.n == 2
    never = Provider([{}, {}])
    with pytest.raises(SchemaViolation):
        json_call(never, rows, stage="context_mining", model="m", system="s", user="u", schema={}, fingerprint="f",
                  validate=need_edits)
    assert never.n == 2, "exactly one repair"

    def content(out):
        raise ValueError("not a schema matter")
    plain = Provider([{}])
    with pytest.raises(ValueError, match="schema matter"):
        json_call(plain, rows, stage="context_mining", model="m", system="s", user="u", schema={}, fingerprint="f", validate=content)
    assert plain.n == 1, "a content failure is not repaired"


def test_invalid_json_stays_a_json_decode_error_that_carries_the_text(monkeypatch):
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", lambda t, r: reply("{nope"))
    with pytest.raises(json.JSONDecodeError) as caught:
        live().json_call(stage="angle_generation", system="s", user="u", schema={"type": "object"}, fingerprint="f")
    assert isinstance(caught.value, InvalidJson) and caught.value.content == "{nope" and caught.value.raw["usage"]["cost"] == 0.01


# --- E.B1: no content at the length limit is asked again once, with a raised limit ------------------------------------------

NULL_CONTENT = json.loads((Path(__file__).parent / "null_content_length_response.json").read_text(encoding="utf-8"))
SOL = "openai/gpt-6.1-sol"


def answers(*bodies):
    """A transport that sends the given response bodies in turn and keeps every request."""
    queue, sent = iter(bodies), []

    def handle(transport, request):
        sent.append(json.loads(request.content))
        return httpx.Response(200, json=next(queue), request=request)
    return handle, sent


def good(content='{"angles": []}'):
    return {"id": "gen-good", "choices": [{"finish_reason": "stop", "message": {"role": "assistant", "content": content}}],
            "usage": {"cost": 0.03, "prompt_tokens": 65495, "completion_tokens": 400}}


def test_null_content_with_a_length_finish_is_retried_once_with_a_raised_limit_and_both_calls_are_recorded(monkeypatch, tmp_path):
    """A recorded response (20 October: Sonnet 5.5 through Google, reasoning forced, content null at the limit)."""
    from backend_pipeline.llm.run_plans import FilePlanStore
    from backend_pipeline.tests.plans import file_plan
    handle, sent = answers(NULL_CONTENT, good())
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", handle)
    path, _ = file_plan(tmp_path, monkeypatch, models=[SOL], stages=["angle_generation"], max_calls=5, max_cost_usd=2.0)
    provider = live(FilePlanStore(path), max_tokens=9000)
    with provider.call_context(prompt_version="strategist.v6"):
        output, meta = provider.json_call(stage="angle_generation", system="s", user="u", schema={"type": "object"}, fingerprint="fp1")
    assert output == {"angles": []}
    assert [r.get("max_tokens") for r in sent] == [9000, 24000], "the retry has the raised limit, twice the cap up to the floor"
    assert sent[0]["messages"] == sent[1]["messages"] and sent[1]["provider"]["zdr"] is True, "the same request, still routed privately"
    assert meta["raw"]["id"] == "gen-good" and meta["retried"]["fingerprint"] == "fp1"
    assert meta["retried"]["usage"]["cost"] == 0.2214745 and meta["retried"]["raised_max_tokens"] == 24000, "the lost spend stays visible"
    shown = FilePlanStore(path).show()
    assert shown["plan"]["calls_used"] == 2 and shown["plan"]["cost_used_usd"] == pytest.approx(0.2214745 + 0.03)
    sent_events = [c for c in shown["calls"] if c["event"] == "sent"]
    assert len(sent_events) == 2 and sent_events[1]["fingerprint"] != "fp1", "the retry is its own planned call"
    first, second = [c for c in shown["calls"] if c["event"] == "annotate"]
    assert first["details"]["empty_content"] is True and first["details"]["finish_reason"] == "length"
    assert second["details"]["retry_of"] == "fp1" and second["details"]["raised_max_tokens"] == 24000
    assert second["prompt_version"] == "strategist.v6" == first["prompt_version"]
    assert "empty_content" not in second["details"]


@pytest.mark.parametrize("empty", [None, "", "   "])
def test_an_empty_answer_at_the_limit_is_asked_again_like_a_null_one(monkeypatch, empty):
    nothing = copy.deepcopy(NULL_CONTENT)
    nothing["choices"][0]["message"]["content"] = empty
    handle, sent = answers(nothing, good())
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", handle)
    plan = OpenTestPlan()
    output, _ = live(plan).json_call(stage="angle_generation", system="s", user="u", schema={"type": "object"}, fingerprint="f")
    assert output == {"angles": []} and len(sent) == 2 and len(plan.reserved) == 2
    assert "max_tokens" not in sent[0] and sent[1]["max_tokens"] == 24000, "a call with no cap is raised from what it used"


def test_the_retry_happens_once_and_a_second_empty_answer_is_incomplete(monkeypatch):
    handle, sent = answers(NULL_CONTENT, NULL_CONTENT, good())
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", handle)
    plan = OpenTestPlan()
    with pytest.raises(IncompleteResponse, match="after one retry"):
        live(plan, max_tokens=30000).json_call(stage="angle_generation", system="s", user="u", schema={"type": "object"},
                                               fingerprint="f")
    assert len(sent) == 2 and len(plan.reserved) == 2, "never a third call"
    assert sent[1]["max_tokens"] == 60000


def test_a_refused_or_complete_answer_is_never_retried(monkeypatch):
    for finish, content in [("content_filter", None), ("stop", None)]:
        raw = good(content)
        raw["choices"][0]["finish_reason"] = finish
        handle, sent = answers(raw, good())
        monkeypatch.setattr(httpx.HTTPTransport, "handle_request", handle)
        with pytest.raises((IncompleteResponse, ValueError)):
            live().json_call(stage="angle_generation", system="s", user="u", schema={"type": "object"}, fingerprint="f")
        assert len(sent) == 1, (finish, content)


def test_a_json_answer_cut_off_part_way_is_asked_again_once_with_a_raised_limit(monkeypatch):
    """N2, 23 October: a brief's claim check of 126 statements used 8,601 reasoning tokens and stopped at statement 100,
    at its 16,000-token limit. Part of a JSON answer is no answer, so it is asked again like an empty one."""
    cut = good('{"statements": [{"id": "c_1"}, {"id": "c_')
    cut["choices"][0]["finish_reason"] = "length"
    cut["usage"]["completion_tokens"] = 16000
    handle, sent = answers(cut, good())
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", handle)
    plan = OpenTestPlan()
    output, meta = live(plan, max_tokens=16000).json_call(stage="angle_generation", system="s", user="u",
                                                          schema={"type": "object"}, fingerprint="f")
    assert output == {"angles": []} and len(plan.reserved) == 2, "the retry is its own planned call"
    assert [r["max_tokens"] for r in sent] == [16000, 32000]
    assert meta["retried"]["raised_max_tokens"] == 32000 and meta["retried"]["finish_reason"] == "length"


def test_a_cut_off_answer_from_a_caller_that_reads_text_is_not_retried():
    from backend_pipeline.llm.transport import cut_off
    raw = {"choices": [{"finish_reason": "length", "message": {"content": "part of a sentence"}}]}
    assert cut_off(raw, structured=True) and not cut_off(raw, structured=False)
    assert cut_off({"choices": [{"finish_reason": "length", "message": {"content": None}}]}, structured=False)


def test_a_call_already_at_the_ceiling_is_not_retried(monkeypatch):
    handle, sent = answers(NULL_CONTENT, good())
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", handle)
    with pytest.raises(IncompleteResponse):
        live(max_tokens=64000).json_call(stage="angle_generation", system="s", user="u", schema={"type": "object"}, fingerprint="f")
    assert len(sent) == 1, "a higher limit is not possible, so a second call would only repeat the loss"


def test_a_retry_the_plan_cannot_afford_is_refused_and_says_why(monkeypatch, tmp_path):
    from backend_pipeline.llm.run_plans import FilePlanStore, RunPlanError
    from backend_pipeline.tests.plans import file_plan
    handle, sent = answers(NULL_CONTENT, good())
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", handle)
    path, _ = file_plan(tmp_path, monkeypatch, models=[SOL], stages=["angle_generation"], max_calls=1, max_cost_usd=2.0)
    with pytest.raises(RunPlanError, match="the one retry of a call that returned no content"):
        live(FilePlanStore(path), max_tokens=9000).json_call(stage="angle_generation", system="s", user="u",
                                                             schema={"type": "object"}, fingerprint="f")
    assert len(sent) == 1, "nothing was sent for the refused retry"


def test_the_raised_limit_is_twice_the_cap_between_the_floor_and_the_ceiling():
    from backend_pipeline.llm.transport import raised_output_limit
    used = {"usage": {"completion_tokens": 16000}}
    assert raised_output_limit({"max_tokens": 9000}, used) == 24000
    assert raised_output_limit({"max_tokens": 16000}, used) == 32000
    assert raised_output_limit({}, used) == 32000, "no cap: twice what the answer used"
    assert raised_output_limit({}, {}) == 24000
    assert raised_output_limit({"max_tokens": 50000}, used) == 64000
    assert raised_output_limit({"max_tokens": 64000}, used) is None


# --- one stable prefix, per-stage effort --------------------------------------------------------------------------------

def test_two_weeks_share_one_prefix_and_the_cache_marker_is_applied_at_dispatch_only(monkeypatch):
    week1 = chat_body(model="anthropic/claude-sonnet-5.5", system="PROMPT\n\nKNOWLEDGE BASE", user="week one", schema={})
    week2 = chat_body(model="anthropic/claude-sonnet-5.5", system="PROMPT\n\nKNOWLEDGE BASE", user="week two", schema={})
    assert prefix_hash(week1) == prefix_hash(week2) != prefix_hash({"messages": [{"role": "system", "content": "other"}]})
    marked = mark_prefix(week1)
    assert marked["messages"][0]["content"] == [{"type": "text", "text": "PROMPT\n\nKNOWLEDGE BASE",
                                                  "cache_control": {"type": "ephemeral"}}]
    assert week1["messages"][0]["content"] == "PROMPT\n\nKNOWLEDGE BASE", "the fingerprinted request is not changed"
    openai = chat_body(model="openai/gpt-6.1-sol", system="s", user="u", schema={})
    assert mark_prefix(openai) is openai, "OpenAI caches an identical prefix by itself"
    posted = []
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request",
                        lambda t, r: (posted.append(json.loads(r.content)), reply("{}"))[1])
    provider = live(stage_models={"card_verification": "anthropic/claude-sonnet-5.5"})
    provider.json_call(stage="card_verification", system="S", user="u", schema={"type": "object"}, fingerprint="f")
    assert posted[0]["messages"][0]["content"][0]["cache_control"] == {"type": "ephemeral"}
    assert posted[0]["provider"]["zdr"] is True, "the cache marker keeps the privacy routing"


def test_reasoning_effort_is_asked_per_stage():
    class PerStage(Settings):
        def reasoning_effort_for(self, stage):
            return {"angle_generation": "high", "card_verification": "low"}.get(stage)
    settings = PerStage()
    assert stage_body(settings, "angle_generation", "s", "u", {})["reasoning"] == {"effort": "high"}
    assert stage_body(settings, "card_verification", "s", "u", {})["reasoning"] == {"effort": "low"}
    assert "reasoning" not in stage_body(settings, "moment_extraction", "s", "u", {})
    seen = []

    def handle(transport, request):
        seen.append(json.loads(request.content).get("reasoning"))
        return reply("{}")
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(httpx.HTTPTransport, "handle_request", handle)
        provider = live(effort_for=settings.reasoning_effort_for)
        for stage in ("angle_generation", "card_verification", "moment_extraction"):
            provider.json_call(stage=stage, system="s", user="u", schema={"type": "object"}, fingerprint=stage)
    assert seen == [{"effort": "high"}, {"effort": "low"}, None]


# --- every call site is on the module ----------------------------------------------------------------------------------------

def python_files(*folders):
    for folder in folders:
        for path in (BACKEND / folder).rglob("*.py"):
            if ".venv" not in path.parts and "tests" not in path.parts and "__pycache__" not in path.parts:
                yield path


SEALED_EXPERIMENTS = {"experiments/model_experiment.py", "experiments/reviewed_experiment.py"}


def test_providers_are_built_only_by_the_llm_module_and_only_it_sends():
    """Exit criterion: every call site on the llm module. A live provider is built by `live_provider`, a request leaves
    only through `routing.send`, and nothing outside llm/ calls a provider's `json_call` method directly."""
    problems = []
    for path in python_files("backend_pipeline", "evaluation", "scripts", "experiments"):
        relative = path.relative_to(BACKEND).as_posix()
        if relative.startswith("backend_pipeline/llm/") or relative == "backend_pipeline/provider.py":
            continue
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if isinstance(func, ast.Name) and func.id == "LiveProvider":
                problems.append(f"{relative}:{node.lineno} builds a LiveProvider")
            if isinstance(func, ast.Attribute) and func.attr == "json_call" and relative not in SEALED_EXPERIMENTS:
                problems.append(f"{relative}:{node.lineno} calls a provider's json_call directly")
            if isinstance(func, ast.Attribute) and func.attr == "LiveProvider" and relative not in SEALED_EXPERIMENTS:
                problems.append(f"{relative}:{node.lineno} builds a LiveProvider")
    assert problems == [], "\n".join(problems)


def test_the_two_saved_layouts_live_in_the_llm_module_and_the_callers_hold_none_of_it():
    for relative in ("backend_pipeline/briefs/runtime.py", "backend_pipeline/packs/runtime.py"):
        text = (BACKEND / relative).read_text(encoding="utf-8")
        assert "provider.json_call" not in text and ".glob(" not in text and "received.json" not in text, relative
    pipeline = (BACKEND / "backend_pipeline/pipeline.py").read_text(encoding="utf-8")
    assert "service_calls/{fingerprint}/attempts" not in pipeline, "the stage call's layout is the llm module's"


def test_a_pipeline_given_a_fake_provider_never_reaches_a_model_endpoint(harness):  # noqa: F811
    settings, provider, pipeline = harness
    copy.deepcopy(settings)
    pipeline.run(1, run_id="offline")  # the conftest guard fails the test on any outbound HTTP
    assert provider.calls


class _Flaky:
    """Answers with the given failures in turn, then succeeds."""
    records_runs = False

    def __init__(self, *failures):
        self.failures, self.calls = list(failures), 0

    def json_call(self, **_):
        self.calls += 1
        if self.failures:
            raise self.failures.pop(0)
        return {"ok": True}, {"raw": {}}


def _flaky_call(provider):
    from backend_pipeline.llm.call import patient_call
    return patient_call(provider, None, stage="brief_write", model="m", system="s", user="u", schema={}, fingerprint="f")


def _status(code):
    import httpx
    request = httpx.Request("POST", "https://x.invalid")
    return httpx.HTTPStatusError(str(code), request=request, response=httpx.Response(code, request=request))


def test_a_providers_passing_limit_is_waited_out_and_nothing_else_is(monkeypatch):
    """Production, 2 November: one upstream 429 failed a brief's writing step, and only a person could start it again."""
    import pytest

    from backend_pipeline.llm import call
    from backend_pipeline.llm.transport import UpstreamError
    waits = []
    monkeypatch.setattr(call.time, "sleep", waits.append)
    limited = UpstreamError("Model call failed: the provider answered with an error (429): temporarily rate-limited upstream.")
    provider = _Flaky(limited, _status(503))
    assert _flaky_call(provider)[0] == {"ok": True} and provider.calls == 3 and waits == [20, 60]
    # A limit that does not pass fails the step after the last wait, with the provider's own error.
    waits.clear()
    provider = _Flaky(*[_status(429)] * 4)
    with pytest.raises(Exception, match="429"):
        _flaky_call(provider)
    assert provider.calls == 4 and waits == list(call.TRANSIENT_WAITS)
    # Out of credit, a refused key or a refused request cannot pass by waiting.
    waits.clear()
    for error in (_status(402), _status(403), _status(400), ValueError("bad"), UpstreamError("Model call failed: the provider's answer has no choices")):
        provider = _Flaky(error)
        with pytest.raises(Exception):
            _flaky_call(provider)
        assert provider.calls == 1 and waits == []


def test_the_weekly_scenes_and_cards_wait_out_an_outage_and_the_optional_verifier_does_not(monkeypatch):
    """The cycle runs unattended on Sunday: its two required stages wait out a passing failure, longer than a person would;
    the card verifier's model pass still degrades at the first failure. A read timeout is never resent (it may be charged)."""
    import httpx
    import pytest

    from backend_pipeline.llm import call
    from backend_pipeline.llm.stage import StageCaller as StageCalls
    waits = []
    monkeypatch.setattr(call.time, "sleep", waits.append)
    live = type("Run", (), {"mode": "live"})()
    calls = StageCalls.__new__(StageCalls)
    calls.runs = None
    request = httpx.Request("POST", "https://x.invalid")
    def send(stage, provider):
        return calls._provider_call(provider, stage=stage, system="s", user="u", schema={}, fingerprint="f", run=live, model="m",
                                    context={}, request=None)
    provider = _Flaky(_status(503), httpx.ConnectError("refused", request=request), _status(429))
    assert send("angle_generation", provider)[0] == {"ok": True} and waits == list(call.UNATTENDED_WAITS[:3])
    waits.clear()
    provider = _Flaky(_status(503))
    with pytest.raises(httpx.HTTPStatusError):
        send("card_verification", provider)
    assert provider.calls == 1 and waits == []
    provider = _Flaky(httpx.ReadTimeout("slow", request=request))
    with pytest.raises(httpx.ReadTimeout):
        send("moment_extraction", provider)
    assert provider.calls == 1 and waits == []


def test_an_answer_that_ends_in_the_providers_error_is_passing_and_a_real_cut_off_is_not():
    """4 November 2026: one scene extraction answered with finish_reason "error" and nothing written; it was read as cut off."""
    from backend_pipeline.llm.call import transient
    from backend_pipeline.llm.providers import IncompleteResponse
    def answer(finish, content=None):
        return IncompleteResponse("incomplete", raw={"choices": [{"finish_reason": finish, "message": {"content": content}}]})
    assert transient(answer("error"))
    assert not transient(answer("length")) and not transient(answer("error", '{"scenes": [')) and not transient(answer("content_filter"))
