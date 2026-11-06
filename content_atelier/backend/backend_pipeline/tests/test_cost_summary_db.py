"""6.B7: the cost summary on the migrated database, from the recorded cost only. Synthetic `llm_runs` rows over two budget
weeks (a brief and its query embedding paid by the briefs plan, an unplanned extraction and embedding, a call sent with no
recorded cost, a replayed, a refused and an offline-fake call, a stage no purpose owns, two rows outside the window) and one
`external_calls` row: the totals are the recorded sums to the cent, each call is in its stage, its model and provider and the
budget purpose that paid for it, an unknown cost is counted and never read as zero, the default window is the last eight
budget weeks, and the route and the command answer the same. No model call."""
from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend_pipeline import storage_cli
from backend_pipeline.llm import cost_summary
from backend_pipeline.storage_api import router
from backend_pipeline.tests.platform_db import APPROVER, platform_setup, platform_url  # noqa: F401 (fixtures)

NOW = datetime(2026, 10, 25, 12, 0, tzinfo=UTC)  # a Sunday: the budget week started Monday 19 October
HEADERS = {"Authorization": "Bearer test-secret", "X-Atelier-Actor": APPROVER, "X-Atelier-Email": APPROVER}
PLAN = "plan_standing_briefs_20261019"
# (when, stage, model, provider, plan, status, cost, input tokens, output tokens, routing policy)
ROWS = [
    ("2026-10-20T10:00:00Z", "brief_write", "anthropic/claude-test", "Anthropic", PLAN, "succeeded", "0.12", 1000, 500, "pinned"),
    ("2026-10-20T10:01:00Z", "embedding", "openai/embed-test", "OpenAI", PLAN, "succeeded", "0.00002", 50, 0, "pinned"),
    ("2026-10-13T09:00:00Z", "embedding", "openai/embed-test", "OpenAI", None, "succeeded", "0.0005", 900, 0, "pinned"),
    ("2026-10-13T09:05:00Z", "moment_extraction", "openai/gpt-test", "OpenAI", None, "succeeded", "0.3", 20000, 3000, "pinned"),
    ("2026-10-13T09:06:00Z", "moment_extraction", "openai/gpt-test", None, None, "sent", None, None, None, "pinned"),
    ("2026-10-13T09:07:00Z", "angle_generation", "openai/gpt-test", None, None, "replayed", "0", None, None, "replay"),
    ("2026-10-13T09:08:00Z", "angle_generation", "openai/gpt-test", None, None, "refused", None, None, None, "pinned"),
    ("2026-10-13T09:09:00Z", "angle_generation", "openai/gpt-test", "fake", None, "succeeded", None, 10, 10, "offline-fake"),
    ("2026-10-14T08:00:00Z", "odd_stage", "openai/gpt-test", "OpenAI", None, "succeeded", "0.01", 10, 10, "pinned"),
    ("2026-08-30T23:59:00Z", "brief_write", "anthropic/claude-test", "Anthropic", None, "succeeded", "5", 1, 1, "pinned"),
    ("2026-10-26T00:00:00Z", "brief_write", "anthropic/claude-test", "Anthropic", None, "succeeded", "7", 1, 1, "pinned"),
]


@pytest.fixture
def recorded(platform_setup):  # noqa: F811
    repo, _, _ = platform_setup
    with repo.connection() as conn:
        conn.execute("""INSERT INTO run_plans(plan_id,purpose,stages,models,input_set_hash,max_calls,max_cost_usd,approver,approved_at,
            expires_at,details) VALUES (%s,'standing weekly budget: briefs',ARRAY['brief_write','embedding'],ARRAY['*'],'*',100,2,
            'approver@example.invalid','2026-10-19T00:00:00Z','2026-10-26T00:00:00Z','{"standing": "weekly", "budget_purpose": "briefs"}')""",
                     (PLAN,))
        for n, (at, stage, model, provider, plan, status, cost, tokens_in, tokens_out, policy) in enumerate(ROWS):
            conn.execute("""INSERT INTO llm_runs(llm_run_id,plan_id,stage,model,provider,routing_policy,request_fingerprint,input_tokens,
                output_tokens,cost_usd,status,created_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                         (f"llm_cost_{n}", plan, stage, model, provider, policy, f"fp{n}", tokens_in, tokens_out, cost, status, at))
        conn.execute("""INSERT INTO external_calls(call_id,service,operation,status,cost_usd,created_at)
            VALUES ('call_cost_1','fathom','list_meetings','succeeded',0.05,'2026-10-21T08:00:00Z')""")
    return repo


def by(items, key):
    return {i[key] if isinstance(key, str) else tuple(i[k] for k in key): i for i in items}


def test_the_summary_is_the_recorded_cost_by_week_stage_model_and_purpose(recorded):
    with recorded.connection() as conn:
        s = cost_summary.summary(conn, now=NOW)
    assert s["window"] == {"start": "2026-08-31T00:00:00+00:00", "end": "2026-10-26T00:00:00+00:00"}, "the last eight budget weeks"
    assert len(s["weeks"]) == 8 and s["weeks"][0]["week_start"] == "2026-08-31T00:00:00+00:00"
    m = s["models"]
    assert m["usd"] == 0.43052 and m["calls"] == 9, "two rows outside the window are left out"
    assert s["total_usd"] == 0.48052 and s["external"]["usd"] == 0.05 and s["external"]["calls"] == 1
    assert m["unknown_cost_calls"] == 1, "a sent call without a cost is unknown; replayed, refused and fake calls are not"
    assert s["by_status"] == {"refused": 1, "replayed": 1, "sent": 1, "succeeded": 6}
    purposes = by(m["by_purpose"], "purpose")
    assert purposes["briefs"]["usd"] == 0.12002 and purposes["briefs"]["calls"] == 2, "the brief's query embedding was paid by briefs"
    assert purposes["embedding"]["usd"] == 0.0005 and purposes["extraction"]["usd"] == 0.3
    assert purposes["extraction"]["unknown_cost_calls"] == 1 and purposes["cycle"] == {**purposes["cycle"], "usd": 0.0, "calls": 3}
    assert purposes["other"]["usd"] == 0.01 and purposes["extraction"]["label"] == "scene extraction"
    assert [p["purpose"] for p in m["by_purpose"]][:2] == ["extraction", "briefs"], "biggest spend first"
    stages = by(m["by_stage"], "stage")
    assert stages["embedding"]["usd"] == 0.00052 and stages["embedding"]["calls"] == 2, "embedding runs are in every view"
    assert stages["moment_extraction"]["input_tokens"] == 20000 and stages["brief_write"]["output_tokens"] == 500
    models = by(m["by_model"], ("model", "provider"))
    assert models[("openai/embed-test", "OpenAI")]["usd"] == 0.00052 and models[("anthropic/claude-test", "Anthropic")]["usd"] == 0.12
    weeks = by(s["weeks"], "week_start")
    this, last = weeks["2026-10-19T00:00:00+00:00"], weeks["2026-10-12T00:00:00+00:00"]
    assert (this["usd"], this["external_usd"], this["calls"]) == (0.12002, 0.05, 2)
    assert (last["usd"], last["calls"], last["unknown_cost_calls"]) == (0.3105, 7, 1)
    assert by(last["by_purpose"], "purpose")["extraction"]["usd"] == 0.3
    assert sum(w["calls"] for w in s["weeks"]) == m["calls"] and weeks["2026-09-07T00:00:00+00:00"]["calls"] == 0


def test_a_window_is_honoured_and_an_empty_one_answers_zero(recorded):
    with recorded.connection() as conn:
        one = cost_summary.summary(conn, datetime(2026, 10, 19, tzinfo=UTC), datetime(2026, 10, 26, tzinfo=UTC))
        empty = cost_summary.summary(conn, datetime(2026, 1, 5), datetime(2026, 1, 12))
        conn.execute("DELETE FROM external_calls")
        none = cost_summary.summary(conn, datetime(2026, 10, 19, tzinfo=UTC), datetime(2026, 10, 26, tzinfo=UTC))
    assert one["models"]["usd"] == 0.12002 and [w["week_start"][:10] for w in one["weeks"]] == ["2026-10-19"]
    assert empty["total_usd"] == 0 and empty["models"]["by_stage"] == [] and empty["window"]["start"] == "2026-01-05T00:00:00+00:00"
    assert none["external"] == {"calls": 0, "usd": 0.0, "by_service": []} and none["total_usd"] == 0.12002
    with pytest.raises(ValueError, match="end must come after"):
        cost_summary.window(datetime(2026, 10, 26, tzinfo=UTC), datetime(2026, 10, 19, tzinfo=UTC))


def test_the_route_and_the_command_answer_the_same(recorded, monkeypatch, capsys):
    app = FastAPI()
    app.include_router(router(recorded.settings))
    client = TestClient(app)
    query = "/storage/costs?from=2026-10-12T00:00:00Z&to=2026-10-26T00:00:00Z"
    answer = client.get(query, headers=HEADERS)
    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert body["models"]["usd"] == 0.43052 and len(body["weeks"]) == 2 and body["total_usd"] == 0.48052
    assert client.get(query).status_code in (401, 403), "a team member's read, like the budgets"
    assert client.get("/storage/costs?from=2026-10-26T00:00:00Z&to=2026-10-12T00:00:00Z", headers=HEADERS).status_code == 422
    monkeypatch.setenv("ATELIER_DATABASE_URL", recorded.settings.database_url)
    monkeypatch.setenv("ATELIER_ARTIFACT_ROOT", str(recorded.settings.artifact_root))
    capsys.readouterr()
    storage_cli.main(["costs", "--from", "2026-10-12", "--to", "2026-10-26", "--json"])
    assert json.loads(capsys.readouterr().out) == body
    storage_cli.main(["costs", "--from", "2026-10-12", "--to", "2026-10-26"])
    words = capsys.readouterr().out
    assert words.startswith("Costs from 2026-10-12 to 2026-10-26") and "USD 0.4805 in all" in words
    assert "- scene extraction: USD 0.3000 over 2 calls, 1 with no recorded cost" in words
    assert "- fathom list_meetings: USD 0.0500 over 1 calls" in words and "- 2026-10-19: USD 0.1700 over 2 calls" in words
    with pytest.raises(SystemExit):
        storage_cli.main(["costs", "--from", "2026-10-26", "--to", "2026-10-12"])


def test_the_running_total_counts_every_sent_call_from_the_set_day(recorded):
    from backend_pipeline.settings_store import set_value
    with recorded.connection() as conn:
        assert cost_summary.since(conn) is None, "blank: no running total"
        set_value(conn, "costs.count_from", "2026-10-20", APPROVER)
        total = cost_summary.since(conn)
    # The brief, its query embedding, the later brief and the external call; never a refused, replayed or offline-fake call.
    assert total == {"start": "2026-10-20T00:00:00+00:00", "usd": 7.17002, "calls": 3, "unknown_cost_calls": 0}
    body = cost_summary.report(recorded)
    assert body["since"] == total and body["packs"] == []


def test_nothing_before_the_hand_over_moment_counts_anywhere_on_the_costs_page(recorded):
    from backend_pipeline.settings_store import set_value
    with recorded.connection() as conn:
        # Half a minute after the brief of 20 October, 10:00: it was the team's own test.
        set_value(conn, "costs.count_from", "2026-10-20T10:00:30Z", APPROVER)
    body = cost_summary.report(recorded)
    assert body["since"] == {"start": "2026-10-20T10:00:30+00:00", "usd": 7.05002, "calls": 2, "unknown_cost_calls": 0}
    assert body["window"]["start"] == "2026-10-20T10:00:30+00:00" and body["total_usd"] == 7.05002
    assert body["weeks"][0]["week_start"] == "2026-10-19T00:00:00+00:00" and body["weeks"][0]["calls"] == 1
    assert {g["stage"] for g in body["models"]["by_stage"]} == {"embedding", "brief_write"}
    # A window that ends before the moment is left as asked.
    early = cost_summary.report(recorded, datetime(2026, 10, 12, tzinfo=UTC), datetime(2026, 10, 19, tzinfo=UTC))
    assert early["window"]["start"] == "2026-10-12T00:00:00+00:00"


class _Store:
    def __init__(self, files):
        self.files = files

    def exists(self, key):
        return key in self.files

    def read_json(self, key):
        return self.files[key]


def _call(stage, *, cost=None, reused=False, dispatched=True, original=None, generation="gen-1"):
    return {"stage": stage, "dispatched": dispatched, "reused": reused, "generation_id": generation,
            "original_reported_cost_usd": original if original is not None else cost,
            "new_cost_usd": 0.0 if reused else cost, "cost_status": "reused_no_new_charge" if reused else
            "reported" if cost is not None else "unknown"}


def test_a_packs_cost_is_what_the_provider_reported_for_each_call_its_run_sent():
    made = datetime(2026, 10, 27, 8, 38, tzinfo=UTC)
    runs = [{"run_id": "pack_run_a", "status": "waiting_for_review", "created_at": made, "pack_id": "pack_a", "title": "A pack",
             "week_id": "week_2026-10-18", "supersedes_id": "pack_old"},
            {"run_id": "pack_run_b", "status": "waiting_for_review", "created_at": made, "pack_id": "pack_b", "title": "B pack",
             "week_id": "week_2026-10-12", "supersedes_id": None},
            {"run_id": "pack_run_c", "status": "failed", "created_at": made, "pack_id": "pack_c", "title": "C pack",
             "week_id": "week_2026-10-12", "supersedes_id": None}]
    store = _Store({
        "pack-runs/pack_run_a/cost_summary.json": {"stages": [
            {"stage": "pack_finish", "calls": [_call("pack_finish", cost=0.4), _call("pack_finish", cost=0.57)]},
            {"stage": "pack_check", "calls": [_call("pack_check", cost=0.075616), _call("pack_check")]},
            # An attempt refused before it was sent: no generation id and no cost, so no call.
            {"stage": "pack_repair", "calls": [_call("pack_repair", generation=None)]}]},
        "pack-runs/pack_run_b/cost_summary.json": {"stages": [
            {"stage": "pack_finish", "calls": [_call("pack_finish", reused=True, original=0.6)]},
            {"stage": "pack_check", "calls": [_call("pack_check", dispatched=False)]}]},
    })
    a, b, c = cost_summary.pack_costs(store, runs)
    assert (a["usd"], a["calls"], a["verified_calls"], a["unknown_cost_calls"], a["made_again"]) == (1.045616, 4, 3, 1, True)
    assert (b["usd"], b["calls"], b["reused_calls"], b["reused_original_usd"], b["made_again"]) == (0.0, 0, 1, 0.6, False)
    assert (c["recorded"], c["usd"], c["calls"]) == (False, 0.0, 0)
