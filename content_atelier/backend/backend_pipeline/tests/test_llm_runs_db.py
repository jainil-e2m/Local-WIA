"""0.B4: every call writes an `llm_runs` row with model, prompt version, knowledge-base version, tokens and cost.

On the migrated database, with a real SQL run plan and a mock transport (the conftest guard forbids real HTTP)."""
from __future__ import annotations

import json

import httpx
import pytest

from backend_pipeline.config import Settings
from backend_pipeline.database import connect
from backend_pipeline.llm import LlmRuns
from backend_pipeline.llm.run_plans import RunPlanError, create_sql_plan
from backend_pipeline.models import RunManifest
from backend_pipeline.pipeline import Pipeline
from backend_pipeline.tests.platform_db import platform_url  # noqa: F401 (fixture)

SCHEMA = {"type": "object", "title": "x", "required": ["moments"], "properties": {"moments": {"type": "array"}}}
MODEL = "openai/gpt-6-luna"


def manifest(mode):
    return RunManifest(run_id=f"r-{mode}", week_index=1, source_root="x", source_ids=[], prompt_profile="p", model_id=MODEL,
                       embedding_profile="e", mode=mode)


@pytest.fixture
def plan(platform_url, monkeypatch):  # noqa: F811
    with connect(platform_url, vectors=False) as conn:
        conn.execute("TRUNCATE llm_runs, run_plans CASCADE")
        made = create_sql_plan(conn, purpose="llm_runs test", stages=["moment_extraction"], models=[MODEL], input_set_hash="*",
                               max_calls=5, max_cost_usd=1, approver="tester@example.invalid")
        conn.commit()
    monkeypatch.setenv("ATELIER_RUN_PLAN_ID", made["plan_id"])
    monkeypatch.setenv("ATELIER_DATABASE_URL", platform_url)
    return made


@pytest.fixture
def transport(monkeypatch):
    sent = []

    def handle(_, request):
        sent.append(json.loads(request.content))
        raw = {"id": "gen-1", "provider": "Azure", "model": MODEL,
               "choices": [{"finish_reason": "stop", "message": {"content": json.dumps({"moments": []})}}],
               "usage": {"prompt_tokens": 120, "completion_tokens": 30, "cost": 0.0123,
                         "prompt_tokens_details": {"cached_tokens": 64}}}
        return httpx.Response(200, json=raw, request=request)
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", handle)
    return sent


def pipeline_for(tmp_path, url):
    settings = Settings(data_root=tmp_path / "data", live_enabled=True, llm_input_limits_enabled=False, openrouter_moments_key="k", openrouter_angles_key="k")
    return Pipeline(settings, runs=LlmRuns.for_database(url))


def rows(url):
    with connect(url, vectors=False) as conn:
        return conn.execute("SELECT * FROM llm_runs ORDER BY created_at, llm_run_id").fetchall()


def by(url, key):
    """The rows by a property that tells them apart: their created_at order is not their write order when the local
    database clock steps back between two calls (database.CLOCK_STEP_SECONDS)."""
    return {key(r): r for r in rows(url)}


def test_a_planned_call_has_a_row_with_model_versions_tokens_and_cost(platform_url, plan, transport, tmp_path):  # noqa: F811
    pipeline = pipeline_for(tmp_path, platform_url)
    pipeline._select_provider("live")
    artifact = pipeline.calls.call_json("moment_extraction", manifest("live"), "runs/live", "SYSTEM", "USER", "hash", SCHEMA,
                                        validate=lambda out: None, prompt_version="scenes.v9",
                                        knowledge_base_version="wia-kb-2026-10-18.c-0cb353e4")
    assert artifact.status == "validated" and len(transport) == 1
    [row] = rows(platform_url)
    assert row["plan_id"] == plan["plan_id"] and row["status"] == "succeeded"
    assert row["stage"] == "moment_extraction" and row["model"] == MODEL and row["provider"] == "Azure"
    assert row["prompt_version"] == "scenes.v9" and row["knowledge_base_version"] == "wia-kb-2026-10-18.c-0cb353e4"
    assert (row["input_tokens"], row["output_tokens"]) == (120, 30) and float(row["cost_usd"]) == pytest.approx(0.0123)
    assert row["routing_policy"].endswith("deny-collection-zdr.v1") and row["request_fingerprint"] == artifact.request_fingerprint
    assert len(row["details"]["prefix_hash"]) == 64 and row["details"]["cached_tokens"] == 64
    assert row["details"]["run_id"] == "r-live" and row["details"]["generation_id"] == "gen-1"
    with connect(platform_url, vectors=False) as conn:
        used = conn.execute("SELECT calls_used,cost_used_usd FROM run_plans WHERE plan_id=%s", (plan["plan_id"],)).fetchone()
    assert used["calls_used"] == 1 and float(used["cost_used_usd"]) == pytest.approx(0.0123), "the plan counts what the row records"


def test_a_replay_and_a_refusal_are_rows_too(platform_url, plan, transport, tmp_path, monkeypatch):  # noqa: F811
    pipeline = pipeline_for(tmp_path, platform_url)
    pipeline._select_provider("live")
    first = pipeline.calls.call_json("moment_extraction", manifest("live"), "runs/live", "S", "U", "h", SCHEMA,
                                     validate=lambda out: None, prompt_version="p")
    again = pipeline_for(tmp_path, platform_url)
    again._select_provider("replay")
    second = again.calls.call_json("moment_extraction", manifest("replay"), "runs/replay", "S", "U", "h", SCHEMA,
                                   validate=lambda out: None, prompt_version="p")
    assert second.request_fingerprint == first.request_fingerprint and second.output_hash == first.output_hash
    assert len(transport) == 1, "the replay sent nothing"
    statuses = by(platform_url, lambda r: r["status"])
    assert set(statuses) == {"succeeded", "replayed"}
    paid, replayed = statuses["succeeded"], statuses["replayed"]
    assert replayed["plan_id"] is None and float(replayed["cost_usd"]) == 0
    assert replayed["request_fingerprint"] == paid["request_fingerprint"]
    # No plan (no named plan, standing budgets switched off, 6.B3): refused before any request, and the refusal is on record.
    monkeypatch.delenv("ATELIER_RUN_PLAN_ID")
    from backend_pipeline.database import connect
    from backend_pipeline.settings_store import set_value
    with connect(platform_url, vectors=False) as conn:
        set_value(conn, "budgets.standing", False, "whitney@example.invalid")
        conn.commit()
    refused = pipeline_for(tmp_path / "other", platform_url)
    refused._select_provider("live")
    with pytest.raises(RunPlanError):
        refused.calls.call_json("moment_extraction", manifest("live"), "runs/refused", "S", "U2", "h2", SCHEMA,
                                validate=lambda out: None, prompt_version="p")
    assert len(transport) == 1
    [last] = [r for r in rows(platform_url) if r["llm_run_id"] not in {paid["llm_run_id"], replayed["llm_run_id"]}]
    assert last["status"] == "refused" and last["plan_id"] is None and "run plan" in last["error"].lower()
    assert last["details"]["refused_by"] == "run_plan"


def test_the_repair_call_is_a_planned_call_with_its_own_row(platform_url, plan, monkeypatch, tmp_path):  # noqa: F811
    answers = iter([{"nope": 1}, {"moments": []}])
    sent = []

    def handle(_, request):
        sent.append(json.loads(request.content))
        raw = {"id": f"gen-{len(sent)}", "choices": [{"finish_reason": "stop", "message": {"content": json.dumps(next(answers))}}],
               "usage": {"prompt_tokens": 10, "completion_tokens": 5, "cost": 0.01}}
        return httpx.Response(200, json=raw, request=request)
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", handle)
    pipeline = pipeline_for(tmp_path, platform_url)
    pipeline._select_provider("live")
    artifact = pipeline.calls.call_json("moment_extraction", manifest("live"), "runs/live", "S", "U", "h", SCHEMA,
                                        validate=lambda out: None, prompt_version="p")
    assert artifact.metadata["repair"]["attempt"] == 1 and len(sent) == 2
    calls = by(platform_url, lambda r: "repair" if r["details"].get("repair_of") else "first")
    assert len(calls) == 2
    first, repair = calls["first"], calls["repair"]
    assert first["request_fingerprint"] == artifact.request_fingerprint
    assert repair["request_fingerprint"] == artifact.metadata["repair"]["fingerprint"]
    assert repair["details"]["repair_of"] == first["request_fingerprint"]
    with connect(platform_url, vectors=False) as conn:
        assert conn.execute("SELECT calls_used FROM run_plans WHERE plan_id=%s", (plan["plan_id"],)).fetchone()["calls_used"] == 2


def test_an_empty_answer_at_the_length_limit_and_its_retry_are_two_rows_on_one_plan(platform_url, plan, monkeypatch, tmp_path):  # noqa: F811
    """E.B1: the recorded null-content response (anonymised), then the answer to the one retry."""
    from pathlib import Path
    recorded = json.loads((Path(__file__).parent / "null_content_length_response.json").read_text(encoding="utf-8"))
    answers = iter([recorded, {"id": "gen-retry", "choices": [{"finish_reason": "stop", "message": {"content": json.dumps({"moments": []})}}],
                               "usage": {"prompt_tokens": 120, "completion_tokens": 300, "cost": 0.01}}])
    sent = []

    def handle(_, request):
        sent.append(json.loads(request.content))
        return httpx.Response(200, json=next(answers), request=request)
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", handle)
    pipeline = pipeline_for(tmp_path, platform_url)
    pipeline._select_provider("live")
    artifact = pipeline.calls.call_json("moment_extraction", manifest("live"), "runs/live", "S", "U", "h", SCHEMA,
                                        validate=lambda out: None, prompt_version="scenes.v9")
    assert artifact.status == "validated" and len(sent) == 2 and sent[1]["max_tokens"] == 24000
    assert artifact.metadata["retried"]["usage"]["completion_tokens"] == 9000 and "repair" not in artifact.metadata
    calls = by(platform_url, lambda r: "retry" if r["details"].get("retry_of") else "first")
    assert len(calls) == 2
    first, retry = calls["first"], calls["retry"]
    assert first["request_fingerprint"] == artifact.request_fingerprint and retry["request_fingerprint"] != first["request_fingerprint"]
    assert (first["status"], retry["status"]) == ("succeeded", "succeeded") and first["plan_id"] == retry["plan_id"] == plan["plan_id"]
    assert first["details"]["empty_content"] is True and first["details"]["finish_reason"] == "length"
    assert float(first["cost_usd"]) == pytest.approx(0.2214745, abs=1e-5) and first["output_tokens"] == 9000
    assert retry["details"]["retry_of"] == first["request_fingerprint"] and retry["details"]["raised_max_tokens"] == 24000
    assert retry["prompt_version"] == first["prompt_version"] == "scenes.v9"
    with connect(platform_url, vectors=False) as conn:
        used = conn.execute("SELECT calls_used,cost_used_usd FROM run_plans WHERE plan_id=%s", (plan["plan_id"],)).fetchone()
    assert used["calls_used"] == 2 and float(used["cost_used_usd"]) == pytest.approx(0.2314745, abs=1e-4), "the plan counts both calls"
