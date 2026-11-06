"""4.B1 with 6.B3: developing a card starts its brief live, under the standing weekly budget. Developing twice makes one brief;
a replay run queued for the same approval no longer blocks the live start; over budget the brief waits, with the reason on
the card, and starts once the budget has room. Synthetic cards, mock transports; nothing leaves the machine."""
from __future__ import annotations

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend_pipeline import gate_one
from backend_pipeline.angle_profiles import STRATEGIST_V4_PROFILE
from backend_pipeline.briefs import gate_two
from backend_pipeline.briefs.workflow import develop_mode, queue
from backend_pipeline.chunk_encoding import queue as encode_chunks
from backend_pipeline.database import connect
from backend_pipeline.llm import standing
from backend_pipeline.settings_store import set_value
from backend_pipeline.sql_pipeline import SQLWorker
from backend_pipeline.storage_api import router
from backend_pipeline.tests.platform_db import APPROVER, platform_setup, platform_url  # noqa: F401 (fixture)
from backend_pipeline.tests.test_brief_v3_db import BriefV3Provider
from backend_pipeline.tests.test_cards_sql import DECIDE, W1, W2, ranked
from backend_pipeline.tests.test_sql_storage import drain
from backend_pipeline.tests.test_strategist_profile import write_kb


class NoNetwork:
    def __init__(self):
        self.requests = []

    def __call__(self, transport, request):
        self.requests.append(str(request.url))
        raise AssertionError("no request may leave in this test")


@pytest.fixture
def cards(platform_setup, monkeypatch):  # noqa: F811
    """A week of synthetic cards, then the live switches on and standing budgets found from the database."""
    repo, models, tmp = platform_setup
    repo.settings.brief_enabled = True
    repo.settings.brief_schema, repo.settings.brief_writer = "brief_document_v3", "v4"
    repo.settings.brief_model, repo.settings.brief_review_model = "openai/gpt-6.1-sol", "anthropic/claude-sonnet-5.5"
    card_models = models.model_copy(update={"angle_prompt_profile": STRATEGIST_V4_PROFILE, "knowledge_base_root": write_kb(tmp / "kb")})
    worker = SQLWorker(repo.settings, card_models, provider=BriefV3Provider())
    repo.submit(W1, "synthetic", models=card_models)
    drain(worker)
    for week in (W1, W2):
        encode_chunks(repo, card_models, week)
    drain(worker)
    top = ranked(repo.review(W1, APPROVER))[0]
    repo.settings.generation_enabled = repo.settings.brief_live_enabled = True
    for name in ("ATELIER_RUN_PLAN_ID", "ATELIER_RUN_PLAN_FILE"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("ATELIER_DATABASE_URL", repo.settings.database_url)
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-only")
    network = NoNetwork()
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", lambda tr, request: network(tr, request))
    return repo, card_models, top, network


def develop(repo, top):
    ledger = [f["id"] for f in top["content_body"]["ledger"]["flags"] if f["severity"] == "block"]
    return gate_one.decide(repo, top["angle_id"], top["content_hash"], "approved", DECIDE, False, "Checked." if ledger else None,
                           APPROVER, verified=top["content_body"]["card"]["verify_before_publishing"] + ledger)


def runs(repo, angle_id):
    with repo.connection() as conn:
        return conn.execute("""SELECT run_id,status,input_refs FROM pipeline_runs WHERE input_refs->'angle'->>'angle_id'=%s
            ORDER BY created_at""", (angle_id,)).fetchall()


def test_the_develop_mode_is_live_wherever_live_briefs_are_switched_on(platform_setup):  # noqa: F811
    settings = platform_setup[0].settings
    assert develop_mode(settings) == "synthetic"
    settings.synthetic = False
    assert develop_mode(settings) == "replay", "replay only where the live switches are off: a test and development mode"
    settings.generation_enabled = settings.brief_live_enabled = True
    assert develop_mode(settings) == "live"


def test_developing_starts_the_brief_live_and_twice_is_one_brief(cards):
    repo, models, top, _ = cards
    repo.settings.synthetic = False  # a live database
    approval = develop(repo, top)
    (run,) = runs(repo, top["angle_id"])
    assert approval["brief_run"]["run_id"] == run["run_id"] and run["input_refs"]["mode"] == "live" and run["status"] == "queued"
    again = queue(repo, top["angle_id"], APPROVER, "live")
    assert again["run_id"] == run["run_id"], "developing twice makes one brief"
    assert len(runs(repo, top["angle_id"])) == 1


def test_a_replay_run_for_the_same_approval_no_longer_blocks_the_live_start(cards):
    repo, models, top, _ = cards
    repo.settings.synthetic = False
    repo.settings.generation_enabled = False  # an earlier deployment: develop queued replay
    replay = develop(repo, top)["brief_run"]
    repo.settings.generation_enabled = True
    live = queue(repo, top["angle_id"], APPROVER, "live")
    assert live["run_id"] != replay["run_id"]
    by = {r["run_id"]: r for r in runs(repo, top["angle_id"])}
    assert by[replay["run_id"]]["status"] == "cancelled"
    assert by[replay["run_id"]]["input_refs"]["superseded_by"]["run_id"] == live["run_id"]
    assert by[live["run_id"]]["input_refs"]["mode"] == "live" and by[live["run_id"]]["status"] == "queued"
    assert queue(repo, top["angle_id"], APPROVER, "live")["run_id"] == live["run_id"]


def test_over_budget_the_brief_waits_with_the_reason_on_the_card_and_starts_when_raised(cards):
    repo, models, top, network = cards
    with connect(repo.settings.database_url, vectors=False) as conn:
        set_value(conn, "budgets.weekly_usd.briefs", 0.05, APPROVER)
        # This week's briefs have spent it already.
        conn.execute("UPDATE run_plans SET cost_used_usd=0.05,status='exhausted' WHERE plan_id=%s",
                     (standing.ensure(conn, "briefs")["plan_id"],))
        conn.commit()
    # The synthetic archive stands in for the live one's embeddings; the brief itself runs live, as a developed card's does.
    develop(repo, top)
    started = queue(repo, top["angle_id"], APPROVER, "live")["run_id"]
    worker = SQLWorker(repo.settings, models)
    for _ in range(4):
        worker.once(run_id=started)
    run = next(r for r in runs(repo, top["angle_id"]) if r["run_id"] == started)
    with repo.connection() as conn:
        jobs = {j["stage"]: j for j in conn.execute("SELECT * FROM pipeline_jobs WHERE run_id=%s", (run["run_id"],))}
        refused = conn.execute("SELECT * FROM llm_runs WHERE status='refused'").fetchall()
    waiting = [j for j in jobs.values() if j["status"] == "waiting"]
    assert len(waiting) == 1 and waiting[0]["progress_details"]["waiting_for"] == "budget", {s: (j["status"], j["error_summary"]) for s, j in jobs.items()}
    assert not [j for j in jobs.values() if j["status"] == "failed"], "a spent budget waits; it does not fail the brief"
    assert network.requests == [], "the refused call was never sent"
    assert refused and refused[0]["details"]["refused_by"] == "run_plan"
    assert run["status"] == "partially_completed"

    # The card shows why, in words (the research answer the card's brief panel reads).
    app = FastAPI()
    app.include_router(router(repo.settings))
    headers = {"Authorization": "Bearer test-secret", "X-Atelier-Actor": APPROVER, "X-Atelier-Email": APPROVER}
    shown = TestClient(app).get(f"/storage/angles/{top['angle_id']}/research", headers=headers).json()
    assert shown["mode"] == "live" and shown["waiting_reason"].startswith("This week's briefs budget is spent (USD 0.05 of USD 0.05)")
    assert "renews on Monday" in shown["waiting_reason"]
    assert gate_two.research(repo, top["angle_id"])["waiting_reason"] == shown["waiting_reason"]

    # An approver raises the cap: the stage is queued again, with no command for the brief itself.
    with connect(repo.settings.database_url, vectors=False) as conn:
        result = standing.set_cap(conn, "briefs", APPROVER, usd=2.0)
        conn.commit()
    assert result["released_jobs"] == [waiting[0]["job_id"]]
    with repo.connection() as conn:
        again = conn.execute("SELECT status FROM pipeline_jobs WHERE job_id=%s", (waiting[0]["job_id"],)).fetchone()
        status = conn.execute("SELECT status FROM pipeline_runs WHERE run_id=%s", (run["run_id"],)).fetchone()
    assert again["status"] == "queued" and status["status"] == "queued"
