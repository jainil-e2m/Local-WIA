"""6.B3: standing weekly budgets. Each purpose has one database plan per week, found with no run-plan variable; a call that
would pass the cap is refused before it is sent, the job waits with the reason in words, and a raised cap or the next week's
plan queues it again. Mock transports only; no network."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import httpx
import pytest

from backend_pipeline.database import connect
from backend_pipeline.jobs import scheduler
from backend_pipeline.llm import standing
from backend_pipeline.llm.run_plans import BudgetExhausted, RunPlanError, from_environment
from backend_pipeline.settings_store import BUDGET_DEFAULTS, set_value
from backend_pipeline.tests.platform_db import APPROVER, empty, platform_url  # noqa: F401 (fixture)
from backend_pipeline.tests.test_run_plans import Transport, call, provider

MONDAY = datetime(2026, 10, 26, 9, 0, tzinfo=UTC)


@pytest.fixture
def url(platform_url, monkeypatch):  # noqa: F811
    empty(platform_url)
    for name in ("ATELIER_RUN_PLAN_ID", "ATELIER_RUN_PLAN_FILE"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("ATELIER_DATABASE_URL", platform_url)
    return platform_url


@pytest.fixture
def transport(monkeypatch):
    t = Transport(cost=0.02)
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", lambda tr, request: t(tr, request))
    return t


def store(url, now=MONDAY):
    return standing.StandingPlanStore(url, clock=lambda: now)


def plans(url):
    with connect(url, vectors=False) as conn:
        return {r["plan_id"]: r for r in conn.execute("SELECT * FROM run_plans ORDER BY plan_id")}


def test_the_defaults_follow_plan_d36_and_are_recorded():
    assert set(BUDGET_DEFAULTS) == set(standing.PURPOSES)
    total = sum(usd for purpose, (usd, _) in BUDGET_DEFAULTS.items() if purpose != "packs")
    assert 2 <= total <= 4, "D36: live operation about USD 2 to 4 a week"
    assert BUDGET_DEFAULTS["packs"] == (3.50, 60), "D43f: content packs at USD 3.50 a week, 60 calls"


def test_every_pack_stage_is_on_the_packs_budget_from_the_first_week():
    """NP.B5: a week's plan freezes its stage list when created, so every pack stage, NP-7's included, is listed now."""
    from backend_pipeline.packs.contracts_v2 import MODEL_STAGES
    assert set(MODEL_STAGES) <= set(standing.ALL_STAGES)
    assert {standing.STAGE_PURPOSE[s] for s in MODEL_STAGES} == {"packs"}
    assert standing.purpose_for_job("pack_generation", "pack_finish") == "packs"


def test_a_worker_with_no_variable_spends_its_purposes_weekly_plan(url, transport):
    assert isinstance(from_environment(), standing.StandingPlanStore), "found without ATELIER_RUN_PLAN_ID"
    live = provider(store(url))
    with standing.purpose("briefs"):
        call(live, "b1", stage="brief_write")
        live.embed(text="query", fingerprint="b2")  # a brief's query embedding is the brief's
    call(live, "c1", stage="angle_generation")  # no job names a purpose: the stage does
    rows = plans(url)
    assert set(rows) == {"plan_standing_briefs_20261026", "plan_standing_cycle_20261026"}
    briefs = rows["plan_standing_briefs_20261026"]
    assert briefs["calls_used"] == 2 and float(briefs["cost_used_usd"]) == pytest.approx(0.04)
    assert float(briefs["max_cost_usd"]) == BUDGET_DEFAULTS["briefs"][0] and briefs["approver"] == standing.DEFAULT_APPROVER
    assert briefs["details"]["cap_source"] == "plan D36 default"
    assert briefs["expires_at"] == datetime(2026, 11, 2, tzinfo=UTC), "the week ends on Monday 00:00 UTC"
    with connect(url, vectors=False) as conn:
        runs = conn.execute("SELECT plan_id,status FROM llm_runs").fetchall()
    # Which plan each call spent, not their created_at order: the local database clock can step back between two calls.
    assert sorted(r["plan_id"] for r in runs) == ["plan_standing_briefs_20261026"] * 2 + ["plan_standing_cycle_20261026"]
    # A named plan stays the override for a one-off run.
    assert len(transport.requests) == 3


def test_the_call_that_would_pass_the_cap_is_refused_before_sending(url, transport):
    with connect(url, vectors=False) as conn:
        set_value(conn, "budgets.weekly_usd.refreshes", 0.03, APPROVER)
        conn.commit()
    live = provider(store(url))
    with standing.purpose("refreshes"):
        call(live, "r1", stage="brief_write")
        call(live, "r2", stage="brief_write")  # 0.04 spent: the plan is exhausted after it settles
        with pytest.raises(BudgetExhausted) as refused:
            call(live, "r3", stage="brief_write")
    assert len(transport.requests) == 2, "the refused call never left"
    error = refused.value
    assert error.purpose == "refreshes" and error.plan_id == "plan_standing_refreshes_20261026"
    assert "This week's refreshes budget is spent (USD 0.04 of USD 0.03)" in str(error)
    assert "renews on Monday 02 November" in str(error)
    assert standing.refusal(RuntimeError("wrapped").with_traceback(None)) is None
    try:
        raise ValueError("outer") from error
    except ValueError as wrapped:
        assert standing.refusal(wrapped) is error


def test_a_call_limit_reached_is_said_as_calls_not_as_money_spent(url, transport):
    """N1 shakedown: a refreshes budget capped at one call read "budget is spent (USD 0.00 of USD 0.50)"."""
    with connect(url, vectors=False) as conn:
        set_value(conn, "budgets.weekly_calls.refreshes", 1, APPROVER)
        conn.commit()
    live = provider(store(url))
    with standing.purpose("refreshes"):
        call(live, "c1", stage="brief_write")
        with pytest.raises(BudgetExhausted) as refused:
            call(live, "c2", stage="brief_write")
    assert "This week's refreshes budget has used all 1 calls it allows, so the next call was not sent" in str(refused.value)
    assert "is spent" not in str(refused.value)


def test_the_worst_case_check_holds_the_cap_for_the_call_itself(url, transport):
    with connect(url, vectors=False) as conn:
        set_value(conn, "budgets.weekly_usd.cycle", 0.01, APPROVER)
        conn.commit()
    live = provider(store(url))
    live.max_tokens = 200_000  # Sol's output price: up to USD 2 for this call
    with pytest.raises(BudgetExhausted, match="could cost up to USD 2.00, so it was not sent"):
        call(live, "w1", stage="angle_generation")
    assert transport.requests == []


def test_a_purpose_without_a_budget_and_switched_off_budgets_refuse_with_the_way_out(url, transport):
    with connect(url, vectors=False) as conn:
        set_value(conn, "budgets.weekly_usd.context_mining", None, APPROVER)
        conn.commit()
    live = provider(store(url))
    with pytest.raises(RunPlanError, match="No standing budget is set for context mining"):
        call(live, "m1", stage="context_mining")
    with pytest.raises(RunPlanError, match="No standing budget covers the pack_write stage"):
        store(url).reserve(stage="pack_write", model="x", fingerprint="p")
    with connect(url, vectors=False) as conn:
        set_value(conn, "budgets.standing", False, APPROVER)
        conn.commit()
    with pytest.raises(RunPlanError, match="switched off"):
        call(live, "c1", stage="angle_generation")
    assert transport.requests == []


def waiting_job(url, purpose, plan_id, left):
    """A brief job left waiting by a refusal, as SQLWorker records it."""
    with connect(url, vectors=False) as conn:
        conn.execute("INSERT INTO weeks(week_id,week_start,week_end) VALUES ('week_x','2026-10-19','2026-10-25')")
        conn.execute("""INSERT INTO pipeline_runs(run_id,week_id,run_scope,status,trigger_type,triggered_by,input_refs)
            VALUES ('run_x','week_x','brief_generation','partially_completed','manual','t','{}')""")
        conn.execute("""INSERT INTO pipeline_jobs(job_id,run_id,week_id,stage,status,idempotency_key,progress_details)
            VALUES ('job_x','run_x','week_x','brief_research','waiting','run_x:brief_research',%s::jsonb)""",
                     ('{"waiting_for":"budget","budget_purpose":"%s","budget_plan_id":"%s","budget_left_usd":%s,'
                      '"budget_reason":"spent","dependencies":[]}' % (purpose, plan_id, left),))
        conn.commit()


def job(url):
    with connect(url, vectors=False) as conn:
        return conn.execute("SELECT j.status,j.progress_details,r.status AS run_status FROM pipeline_jobs j JOIN pipeline_runs r "
                            "USING(run_id) WHERE job_id='job_x'").fetchone()


def test_a_raised_call_limit_queues_a_job_its_call_limit_stopped(url, transport):
    """N1 shakedown: a refresh stopped by its budget's call limit waited on after the limit was raised, because its money left
    had not changed."""
    with connect(url, vectors=False) as conn:
        set_value(conn, "budgets.weekly_calls.briefs", 1, APPROVER)
        conn.commit()
    live = provider(store(url))
    with standing.purpose("briefs"):
        call(live, "k1", stage="brief_write")
    left = standing.left_usd(plans(url)["plan_standing_briefs_20261026"])
    waiting_job(url, "briefs", "plan_standing_briefs_20261026", left)
    with connect(url, vectors=False) as conn:
        assert standing.release_waits(conn, MONDAY) == [], "no call left: it keeps waiting"
        result = standing.set_cap(conn, "briefs", APPROVER, calls=5, now=MONDAY)
        conn.commit()
    assert result["released_jobs"] == ["job_x"] and job(url)["status"] == "queued"


def test_a_raised_cap_or_the_next_week_queues_the_waiting_job_again(url, transport):
    with connect(url, vectors=False) as conn:
        set_value(conn, "budgets.weekly_usd.briefs", 0.02, APPROVER)
        conn.commit()
    live = provider(store(url))
    with standing.purpose("briefs"):
        call(live, "b1", stage="brief_write")
    waiting_job(url, "briefs", "plan_standing_briefs_20261026", 0.0)
    with connect(url, vectors=False) as conn:
        assert standing.release_waits(conn, MONDAY) == [], "no room: it keeps waiting"
        conn.commit()
    assert job(url)["status"] == "waiting"
    with connect(url, vectors=False) as conn:
        result = standing.set_cap(conn, "briefs", APPROVER, usd=1.0, now=MONDAY)
        conn.commit()
    assert result["released_jobs"] == ["job_x"] and result["status"] == "active" and result["left_usd"] == pytest.approx(0.98)
    row = job(url)
    assert row["status"] == "queued" and row["run_status"] == "queued" and "waiting_for" not in row["progress_details"]
    assert row["progress_details"]["budget_released"]["after"] == "spent"
    assert plans(url)["plan_standing_briefs_20261026"]["approver"] == APPROVER

    # Next week: last week's plan expires, the new one is made, a job that waited on the old one is released.
    with connect(url, vectors=False) as conn:
        conn.execute("UPDATE pipeline_jobs SET status='waiting',progress_details=progress_details||%s::jsonb WHERE job_id='job_x'",
                     ('{"waiting_for":"budget","budget_purpose":"briefs","budget_plan_id":"plan_standing_briefs_20261026",'
                      '"budget_left_usd":5}',))
        conn.commit()
    with connect(url, vectors=False) as conn:
        renewed = standing.renew(conn, MONDAY + timedelta(days=7))
        conn.commit()
    assert "plan_standing_briefs_20261026" in renewed["expired"] and renewed["released_jobs"] == ["job_x"]
    assert renewed["plans"]["briefs"] == "plan_standing_briefs_20261102"
    assert set(renewed["plans"]) == set(standing.PURPOSES)


def test_the_status_lists_every_purpose_with_what_is_left_and_waits(url, transport):
    live = provider(store(url))
    call(live, "c1", stage="angle_generation")
    with connect(url, vectors=False) as conn:
        shown = standing.status(conn, MONDAY)
    by = {b["purpose"]: b for b in shown["budgets"]}
    assert shown["week_start"] == "2026-10-26T00:00:00+00:00" and set(by) == set(standing.PURPOSES)
    assert by["cycle"]["spent_usd"] == pytest.approx(0.02) and by["cycle"]["status"] == "active"
    assert by["briefs"]["status"] == "not_started" and by["briefs"]["left_usd"] == BUDGET_DEFAULTS["briefs"][0]
    assert shown["total_cap_usd"] == pytest.approx(7.0), "D36's USD 3.50 and the packs purpose's USD 3.50 (D43f)"


def test_the_scheduler_renews_weekly_and_reconcile_releases(url):
    from backend_pipeline.storage_config import StorageSettings
    storage = StorageSettings(database_url=url)
    (task,) = [t for t in scheduler.periodic_tasks(storage, None) if t.name == "standing_budgets"]
    assert task.period(MONDAY) == "2026-W44"
    result = task.run(MONDAY)
    assert result["plans"]["cycle"] == "plan_standing_cycle_20261026"


def test_uncapped_lets_every_call_through_lifts_an_exhausted_week_and_still_records_the_spend(url, transport):
    """budgets.uncapped (the owner, 27 October 2026): no weekly cap binds; spend is still recorded and shown."""
    with connect(url, vectors=False) as conn:
        set_value(conn, "budgets.weekly_usd.refreshes", 0.03, APPROVER)
        conn.commit()
    live = provider(store(url))
    with standing.purpose("refreshes"):
        call(live, "u1", stage="brief_write")
        call(live, "u2", stage="brief_write")
        with pytest.raises(BudgetExhausted):
            call(live, "u3", stage="brief_write")
    with connect(url, vectors=False) as conn:
        set_value(conn, "budgets.uncapped", True, APPROVER)
        conn.commit()
    live = provider(store(url))
    with standing.purpose("refreshes"):
        for n in range(4, 9):
            call(live, f"u{n}", stage="brief_write")
    assert len(transport.requests) == 7, "every call after uncapping was sent"
    row = plans(url)["plan_standing_refreshes_20261026"]
    assert row["status"] == "active" and float(row["max_cost_usd"]) >= standing.UNCAPPED_USD
    with connect(url, vectors=False) as conn:
        week = standing.status(conn, now=MONDAY)
    item = next(b for b in week["budgets"] if b["purpose"] == "refreshes")
    assert week["uncapped"] is True and item["uncapped"] is True and item["cap_usd"] is None
    assert item["spent_usd"] == pytest.approx(0.14) and item["calls_used"] == 7
