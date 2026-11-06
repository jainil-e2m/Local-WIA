"""E.B1 in the database suite: plans in run_plans, each call an llm_runs row, caps enforced."""
from __future__ import annotations

import httpx
import pytest

from backend_pipeline.database import connect
from backend_pipeline.llm.run_plans import RunPlanError, SqlPlanStore, create_sql_plan
from backend_pipeline.tests.platform_db import APPROVER, empty, platform_url  # noqa: F401 (fixture)
from backend_pipeline.tests.test_run_plans import SOL, Transport, call, provider


@pytest.fixture
def plan(platform_url):  # noqa: F811
    empty(platform_url)
    with connect(platform_url, vectors=False) as conn:
        created = create_sql_plan(conn, purpose="Week 5 held-out run (test)", stages=["angle_generation"], models=[SOL],
                                  input_set_hash="week5-inputs", max_calls=2, max_cost_usd=0.05, approver=APPROVER)
    return platform_url, created


def test_calls_under_a_database_plan_are_recorded_and_capped(plan, monkeypatch):
    url, created = plan
    transport = Transport(cost=0.01)
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", lambda tr, request: transport(tr, request))
    live = provider(SqlPlanStore(url, created["plan_id"]))
    # A weekly run names its input set, which this plan is bound to (E.B1); a call naming none is refused.
    with pytest.raises(RunPlanError, match="names no input set"):
        call(live, "fp-0")
    live.input_set_hash = "week5-inputs"
    call(live, "fp-1")
    call(live, "fp-2")
    with pytest.raises(RunPlanError, match="exhausted"):
        call(live, "fp-3")
    assert len(transport.requests) == 2
    with connect(url, vectors=False) as conn:
        stored = conn.execute("SELECT * FROM run_plans WHERE plan_id=%s", (created["plan_id"],)).fetchone()
        # By fingerprint, not created_at: the local database's clock can step back between the two calls' transactions.
        runs = conn.execute("SELECT * FROM llm_runs WHERE plan_id=%s ORDER BY request_fingerprint", (created["plan_id"],)).fetchall()
    assert stored["calls_used"] == 2 and float(stored["cost_used_usd"]) == pytest.approx(0.02)
    assert stored["status"] == "exhausted" and stored["approver"] == APPROVER
    assert [(r["status"], r["request_fingerprint"], r["provider"]) for r in runs] == [
        ("succeeded", "fp-1", "Azure"), ("succeeded", "fp-2", "Azure")]
    assert all(r["routing_policy"] == "2026-10-18.deny-collection-zdr.v1" and r["input_tokens"] == 10 for r in runs)


def test_a_missing_or_closed_plan_refuses(plan):
    url, created = plan
    with pytest.raises(RunPlanError, match="does not exist"):
        SqlPlanStore(url, "plan_missing").reserve(stage="angle_generation", model=SOL, fingerprint="f")
    with connect(url, vectors=False) as conn:
        conn.execute("UPDATE run_plans SET status='closed',closed_reason='test' WHERE plan_id=%s", (created["plan_id"],))
    with pytest.raises(RunPlanError, match="closed"):
        SqlPlanStore(url, created["plan_id"]).reserve(stage="angle_generation", model=SOL, fingerprint="f")
