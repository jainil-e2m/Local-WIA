"""E.B1: a real-data call outside an active run plan is refused, in every runtime. Mock transports only."""
from __future__ import annotations

import importlib.util
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest

from backend_pipeline.llm import run_plans
from backend_pipeline.llm.run_plans import FilePlanStore, NoPlan, RunPlanError, from_environment, write_file_plan
from backend_pipeline.llm import LiveProvider

PROJECT = Path(__file__).resolve().parents[3]
SOL = "openai/gpt-6.1-sol"


class Transport:
    def __init__(self, cost=0.01):
        self.requests, self.cost = [], cost

    def __call__(self, transport, request):
        self.requests.append(json.loads(request.content))
        if str(request.url).endswith("/embeddings"):
            return httpx.Response(200, json={"data": [{"index": 0, "embedding": [1.0] * 1536}], "usage": {"cost": self.cost}},
                                  request=request)
        return httpx.Response(200, json={"choices": [{"finish_reason": "stop", "message": {"content": "{}"}}],
                                         "usage": {"cost": self.cost, "prompt_tokens": 10, "completion_tokens": 2},
                                         "provider": "Azure"}, request=request)


@pytest.fixture
def transport(monkeypatch):
    t = Transport()
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", lambda tr, request: t(tr, request))
    return t


def provider(plan=None):
    return LiveProvider(llm_base_url="https://openrouter.ai/api/v1", moments_model="openai/gpt-6-luna", moments_key="k",
                        angles_model=SOL, angles_key="k", embedding_base_url="https://openrouter.ai/api/v1",
                        embedding_model="openai/text-embedding-3-small", embedding_key="k", dimensions=1536, timeout=5,
                        plan=plan)


def plan_file(tmp_path, **changes):
    fields = dict(purpose="test", stages=["angle_generation", "embedding"], models=[SOL, "openai/text-embedding-3-small"],
                  input_set_hash="*", max_calls=3, max_cost_usd=0.05, approver="whitney@example.invalid")
    fields.update(changes)
    return write_file_plan(tmp_path / "plan.json", **fields), tmp_path / "plan.json"


def call(live, fingerprint, stage="angle_generation"):
    return live.json_call(stage=stage, system="s", user="u", schema={"type": "object"}, fingerprint=fingerprint)


def test_a_real_data_call_without_a_plan_is_refused_before_any_request(transport, monkeypatch):
    monkeypatch.delenv("ATELIER_RUN_PLAN_ID", raising=False)
    monkeypatch.delenv("ATELIER_RUN_PLAN_FILE", raising=False)
    live = provider()
    assert isinstance(live.plan, NoPlan)
    with pytest.raises(RunPlanError, match="active run plan"):
        call(live, "f")
    with pytest.raises(RunPlanError):
        live.embed(text="a", fingerprint="f")
    assert transport.requests == [], "nothing leaves without a plan"


def test_a_plan_allows_only_its_stages_models_calls_and_cost(transport, tmp_path):
    plan, path = plan_file(tmp_path)
    live = provider(FilePlanStore(path))
    call(live, "f1")
    with pytest.raises(RunPlanError, match="stage moment_extraction"):
        call(live, "f2", stage="moment_extraction")
    live.embed(text="a", fingerprint="f3")
    stored = json.loads(path.read_text())
    assert stored["calls_used"] == 2 and stored["cost_used_usd"] == pytest.approx(0.02)
    call(live, "f4")
    assert json.loads(path.read_text())["status"] == "exhausted"
    with pytest.raises(RunPlanError, match="exhausted"):
        call(live, "f5")
    assert len(transport.requests) == 3
    ledger = [json.loads(line) for line in path.with_suffix(".calls.jsonl").read_text().splitlines()]
    assert [e["event"] for e in ledger] == ["sent", "succeeded"] * 3, "the call ledger is stored beside the plan"


def test_the_cost_cap_stops_the_next_call(transport, tmp_path):
    transport.cost = 0.04
    _, path = plan_file(tmp_path, max_calls=10, max_cost_usd=0.05)
    live = provider(FilePlanStore(path))
    call(live, "a")
    call(live, "b")
    with pytest.raises(RunPlanError, match="exhausted"):
        call(live, "c")
    assert len(transport.requests) == 2


def test_an_expired_or_foreign_model_plan_is_refused(tmp_path):
    plan, path = plan_file(tmp_path)
    plan["expires_at"] = (datetime.now(UTC) - timedelta(minutes=1)).isoformat()
    path.write_text(json.dumps(plan))
    with pytest.raises(RunPlanError, match="expired"):
        FilePlanStore(path).reserve(stage="angle_generation", model=SOL, fingerprint="f")
    plan["expires_at"] = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
    path.write_text(json.dumps(plan))
    with pytest.raises(RunPlanError, match="model openai/gpt-6-luna"):
        FilePlanStore(path).reserve(stage="angle_generation", model="openai/gpt-6-luna", fingerprint="f")


def test_a_failed_call_is_settled_and_counted(monkeypatch, tmp_path):
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request",
                        lambda tr, request: httpx.Response(500, json={"error": {"message": "upstream"}}, request=request))
    _, path = plan_file(tmp_path)
    with pytest.raises(httpx.HTTPStatusError):
        call(provider(FilePlanStore(path)), "f")
    events = [json.loads(line)["event"] for line in path.with_suffix(".calls.jsonl").read_text().splitlines()]
    assert events == ["sent", "failed"] and json.loads(path.read_text())["calls_used"] == 1


@pytest.mark.parametrize("lost", [httpx.RemoteProtocolError("peer closed connection without sending complete message body"),
                                  httpx.ReadError("connection reset"), httpx.ReadTimeout("read timed out")])
def test_a_call_whose_answer_was_lost_after_sending_counts_at_its_worst_case(monkeypatch, tmp_path, lost):
    """N2, 23 October: a Sonnet brief grade was cut off mid-body after 341 seconds. The key was charged about USD 0.14,
    and the briefs budget recorded nothing. The provider may have billed such a call in full, so it counts at its worst
    case; a connection that was never made costs nothing."""
    from backend_pipeline.llm import failures

    def cut(tr, request):
        raise lost
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", cut)
    _, path = plan_file(tmp_path, max_cost_usd=1.0)
    with pytest.raises(type(lost)) as raised:
        call(provider(FilePlanStore(path)), "f")
    stored = json.loads(path.read_text())
    assert stored["cost_used_usd"] > 0, "the lost answer is charged to the plan"
    ledger = [json.loads(line) for line in path.with_suffix(".calls.jsonl").read_text().splitlines()]
    assert ledger[1]["event"] == "failed" and ledger[1]["cost_usd"] == stored["cost_used_usd"]
    assert "counted at its worst case" in ledger[1]["error"]
    reason = failures.plain(raised.value)
    assert reason in (failures.ANSWER_CUT, failures.TIMED_OUT) and "could not be reached" not in reason

    def refused(tr, request):
        raise httpx.ConnectError("refused")
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", refused)
    _, other = plan_file(tmp_path / "other", max_cost_usd=1.0)
    with pytest.raises(httpx.ConnectError):
        call(provider(FilePlanStore(other)), "g")
    assert json.loads(other.read_text())["cost_used_usd"] == 0, "nothing was sent, so nothing is charged"


@pytest.mark.parametrize("body,stage,expected", [
    ({"error": {"message": "Upstream provider overloaded", "code": 502}, "usage": {"cost": 0}}, "angle_generation",
     "Upstream provider overloaded"),
    ({"id": "gen-x", "provider": "Azure", "usage": {"cost": 0}}, "angle_generation", "no choices"),
    ({"choices": [], "usage": {"cost": 0}}, "angle_generation", "no choices"),
    ({"error": {"message": "Embedding upstream timed out"}}, "embedding", "Embedding upstream timed out"),
    ({"model": "openai/text-embedding-3-small", "usage": {"cost": 0}}, "embedding", "no data"),
])
def test_a_200_answer_without_a_result_is_a_failed_call_with_the_providers_message(monkeypatch, tmp_path, body, stage, expected):
    """OpenRouter can answer HTTP 200 with an upstream error in the body, or with no result. That is a failed call: settled
    as failed with the provider's message, and the caller gets the llm module's failure (UpstreamError), not a KeyError
    on `choices` after the call was recorded as succeeded."""
    from backend_pipeline.llm import UpstreamError
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", lambda tr, request: httpx.Response(200, json=body, request=request))
    _, path = plan_file(tmp_path)
    live = provider(FilePlanStore(path))
    with pytest.raises(UpstreamError, match=expected):
        if stage == "embedding":
            live.embed(text="t", fingerprint="f")
        else:
            call(live, "f")
    ledger = [json.loads(line) for line in path.with_suffix(".calls.jsonl").read_text().splitlines()]
    assert [e["event"] for e in ledger] == ["sent", "failed"] and expected in ledger[1]["error"]


def test_plans_need_an_approver_and_limits(tmp_path):
    with pytest.raises(ValueError, match="approver"):
        plan_file(tmp_path, approver="")
    with pytest.raises(ValueError, match="positive"):
        plan_file(tmp_path, max_calls=0)
    plan_file(tmp_path)
    with pytest.raises(ValueError, match="never overwritten"):
        plan_file(tmp_path)


def test_the_environment_selects_the_store(monkeypatch, tmp_path):
    monkeypatch.delenv("ATELIER_RUN_PLAN_ID", raising=False)
    monkeypatch.delenv("ATELIER_RUN_PLAN_FILE", raising=False)
    assert isinstance(from_environment(), NoPlan)
    _, path = plan_file(tmp_path)
    assert isinstance(from_environment(default_file=path), FilePlanStore)
    monkeypatch.setenv("ATELIER_RUN_PLAN_ID", "plan_x")
    monkeypatch.delenv("ATELIER_DATABASE_URL", raising=False)
    with pytest.raises(RunPlanError, match="ATELIER_DATABASE_URL"):
        from_environment()
    monkeypatch.setenv("ATELIER_DATABASE_URL", "postgresql://x@127.0.0.1/atelier_test")
    assert isinstance(from_environment(), run_plans.SqlPlanStore)


@pytest.mark.parametrize("runner", ["quality-experiments-2026-10-18", "chatgpt-export-2026-10-18"])
def test_the_evaluation_harnesses_refuse_without_a_plan(runner, tmp_path, monkeypatch, transport):
    monkeypatch.delenv("ATELIER_RUN_PLAN_ID", raising=False)
    monkeypatch.delenv("ATELIER_RUN_PLAN_FILE", raising=False)
    path = PROJECT / "research" / runner / "runner.py"
    spec = importlib.util.spec_from_file_location(f"plan_{runner.replace('-', '_')}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "LEDGER", tmp_path / "ledger.jsonl")
    monkeypatch.setattr(module, "_key", lambda: "test-key")
    (tmp_path / "runs").mkdir()
    with pytest.raises(RunPlanError):
        module.call("no-plan", SOL, "system", "user", schema="json_object", estimate_usd=0)
    assert transport.requests == []


def test_a_closed_file_plan_refuses_further_calls_and_the_cli_closes_it(transport, tmp_path, capsys):
    from backend_pipeline import storage_cli
    _, path = plan_file(tmp_path, max_calls=10)
    live = provider(FilePlanStore(path))
    call(live, "a")
    storage_cli.main(["plan", "show", "--file", str(path)])
    shown = json.loads(capsys.readouterr().out)
    assert shown["plan"]["calls_used"] == 1 and [e["event"] for e in shown["calls"]] == ["sent", "succeeded"]
    storage_cli.main(["plan", "close", "--file", str(path), "--reason", "smoke run finished"])
    assert json.loads(capsys.readouterr().out)["status"] == "closed"
    with pytest.raises(RunPlanError, match="closed"):
        call(live, "b")
    assert FilePlanStore(path).close("again")["error"].endswith("already closed")
    assert len(transport.requests) == 1


def test_a_plan_approved_for_one_input_set_refuses_another(tmp_path):
    """S.B2 review: a paid weekly run spends only a plan approved for its own input set, or one for any ("*")."""
    from backend_pipeline.llm.run_plans import FilePlanStore
    path = tmp_path / "plan.json"
    write_file_plan(path, purpose="t", stages=["angle_generation"], models=["m"], input_set_hash="sha256:week5",
                    max_calls=5, max_cost_usd=1, approver="owner@example.invalid")
    store = FilePlanStore(path)
    with pytest.raises(RunPlanError, match="another input set"):
        store.reserve(stage="angle_generation", model="m", fingerprint="f", input_set_hash="sha256:week2")
    assert store.reserve(stage="angle_generation", model="m", fingerprint="f", input_set_hash="sha256:week5")
    # A plan bound to one input set is spent only by calls that name it (E.B1): a caller that names none (a brief, a
    # harness, the learning loop) runs under a plan recorded as covering any input set, never under Week 5's.
    with pytest.raises(RunPlanError, match="names no input set"):
        store.reserve(stage="angle_generation", model="m", fingerprint="g")
    write_file_plan(tmp_path / "any.json", purpose="t", stages=["angle_generation"], models=["m"], input_set_hash="*",
                    max_calls=5, max_cost_usd=1, approver="owner@example.invalid")
    assert FilePlanStore(tmp_path / "any.json").reserve(stage="angle_generation", model="m", fingerprint="f", input_set_hash="x")
    assert FilePlanStore(tmp_path / "any.json").reserve(stage="angle_generation", model="m", fingerprint="g")


def test_a_weekly_runs_provider_names_its_input_set_and_a_plan_for_another_week_spends_nothing(transport, tmp_path):
    """S.B2 review: the SQL worker sets the provider's input set from the run's frozen transcripts."""
    from backend_pipeline.sql_pipeline import run_input_set_hash
    week5 = {"input_refs": {"transcripts": [{"source_id": "zoom:week5/a", "sha256": "1"}]}}
    week2 = {"input_refs": {"transcripts": [{"source_id": "zoom:week2/a", "sha256": "2"}]}}
    assert run_input_set_hash(week5) == run_input_set_hash(json.loads(json.dumps(week5))) != run_input_set_hash(week2)
    _, path = plan_file(tmp_path, input_set_hash=run_input_set_hash(week5))
    live = provider(FilePlanStore(path))
    live.input_set_hash = run_input_set_hash(week2)
    with pytest.raises(RunPlanError, match="another input set"):
        call(live, "f")
    assert transport.requests == []
    live.input_set_hash = run_input_set_hash(week5)
    call(live, "f")
    assert len(transport.requests) == 1


def test_a_call_whose_worst_case_would_pass_the_cap_is_refused_before_it_is_sent(tmp_path):
    """S.B8, 20 October: a USD 0.33 plan ended at USD 0.41, because the cap was only checked against what was already
    spent. A call whose worst case (the whole body as input, plus its output cap, at the model's price) would pass the
    cap is refused; a smaller one goes ahead; a model without a known price is checked as before."""
    plan, path = plan_file(tmp_path)
    plan["max_cost_usd"], plan["cost_used_usd"] = 0.33, 0.20
    path.write_text(json.dumps(plan))
    big = {"model": SOL, "messages": [{"role": "user", "content": "x" * 400_000}], "max_tokens": 12000}
    small = {"model": SOL, "messages": [{"role": "user", "content": "x" * 4_000}], "max_tokens": 2000}
    assert run_plans.worst_case_usd(SOL, big) > 0.13 > run_plans.worst_case_usd(SOL, small) > 0
    with pytest.raises(RunPlanError, match="could cost up to USD"):
        FilePlanStore(path).reserve(stage="angle_generation", model=SOL, fingerprint="f",
                                    worst_case_usd=run_plans.worst_case_usd(SOL, big))
    assert json.loads(path.read_text())["calls_used"] == 0, "a refused call reserves nothing"
    assert FilePlanStore(path).reserve(stage="angle_generation", model=SOL, fingerprint="g",
                                       worst_case_usd=run_plans.worst_case_usd(SOL, small))
    assert run_plans.worst_case_usd("unknown/model", big) is None
