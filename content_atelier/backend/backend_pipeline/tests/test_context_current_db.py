"""L.B11 on a migrated database: context that keeps itself current.

- A correction WIA makes once in each of two weeks becomes a rule candidate (the support window,
  `context.mining.support_weeks`), proposed once however many passes its window covers.
- A missed mining weekday is caught up on the next pass, over every day the missed passes would have read.
- An identity change confirmed in the app reaches an approved, benchmarked version without a developer: the cycle
  says it waits to be compiled, then to be approved; the scheduler queues its benchmark only under a standing run plan
  a person created, the worker runs benchmark v1 on it (mocked provider, no paid call) and records the result for an
  approver, and the approver's recorded verdict makes it the default.
"""
from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta

import httpx
import pytest

from backend_pipeline.config import BACKEND_ROOT, Settings
from backend_pipeline.knowledge import benchmarking, compiler, mining, review, scheduler, staleness
from backend_pipeline.knowledge_base import load_knowledge_base
from backend_pipeline.llm import transport
from backend_pipeline.llm.run_plans import create_sql_plan
from backend_pipeline.sql_pipeline import SQLWorker
from backend_pipeline.tests.platform_db import APPROVER, platform_setup, platform_url  # noqa: F401 (fixture)
from backend_pipeline.tests.test_context_mining_db import week  # noqa: F401 (fixture)
from backend_pipeline.tests.test_seeds_db import SeedProvider
from backend_pipeline.tests.test_sql_storage import drain

ROOT = BACKEND_ROOT / "knowledge_base"
TODAY = date.today()


def _age(repo, *, decision=None, brief=None, days):
    """Move one Gate decision, or one approved brief and its edit, `days` into the past."""
    when = datetime.now(UTC) - timedelta(days=days)
    with repo.connection() as conn:
        if decision:
            conn.execute("UPDATE decisions SET created_at=%s WHERE decision_id=%s", (when, decision))
        if brief:
            conn.execute("UPDATE content_briefs SET approved_at=%s WHERE brief_id=%s", (when, brief))


def _rules(conn, source_kind):
    return conn.execute("SELECT * FROM brand_kit_items WHERE kind='rule' AND source_kind=%s ORDER BY created_at",
                        (source_kind,)).fetchall()


def test_a_correction_made_once_in_each_of_two_weeks_becomes_a_rule_candidate(week):  # noqa: F811
    repo, decisions, _ = week
    # The fixture's two voice reasons and two voice edits, one of each moved into the week before the mined one.
    _age(repo, decision=decisions[3], days=10)
    _age(repo, brief="brief_1b", days=10)
    since, until = TODAY - timedelta(days=6), TODAY
    with repo.connection() as conn:
        alone = mining.run(conn, since=since, until=until, support_weeks=1)
        assert alone["candidates"]["rule"] == 0, "within one week each pattern has one decision or edit"
        assert not _rules(conn, "gate_decision") and not _rules(conn, "brief_edit")
        conn.rollback()
    with repo.connection() as conn:
        result = mining.run(conn, since=since, until=until)
        assert result["support"] == {"since": (TODAY - timedelta(days=27)).isoformat(), "weeks": 4,
                                     "reasons_read": result["support"]["reasons_read"], "edits_read": result["support"]["edits_read"]}
        learned, edited = _rules(conn, "gate_decision"), _rules(conn, "brief_edit")
        assert len(learned) == 1 and set(learned[0]["source_detail"]["decisions"]) == {decisions[2], decisions[3]}
        assert len(edited) == 1 and set(edited[0]["source_detail"]["briefs"]) == {"brief_0b", "brief_1b"}
        assert set(edited[0]["source_detail"]["edits"]) == {"brief_0b:wia_perspective", "brief_1b:wia_perspective"}
        assert result["reasons_read"] == 2, "the mined week's reasons; the older one supports only"
        # The setting decides the window; a pass a week later, whose own week holds nothing new, proposes nothing again.
        assert mining.run(conn, since=since, until=until)["candidates"]["rule"] == 0
        later = mining.run(conn, since=TODAY + timedelta(days=1), until=TODAY + timedelta(days=7))
        assert later["candidates"]["rule"] == 0
        # A third, similar decision has nothing left to pair with: the first two already stand behind a rule.
        from backend_pipeline.gates.decisions import record
        angle = conn.execute("SELECT angle_id,week_id FROM content_angles WHERE content_body ? 'card' ORDER BY angle_id LIMIT 1").fetchone()
        record(conn, item_kind="angle", item_id=angle["angle_id"], week_id=angle["week_id"], disposition="skip",
               action="gate_one_skip", reason_code="voice", note="Punchy one-liners again; it sounds like AI",
               actor=APPROVER, author="Whitney Hodges")
        assert mining.run(conn, since=since, until=until)["candidates"]["rule"] == 0
        assert len(_rules(conn, "gate_decision")) == 1


def test_the_support_window_is_a_registered_setting(week):  # noqa: F811
    from backend_pipeline import settings_store
    repo, decisions, _ = week
    _age(repo, decision=decisions[3], days=10)
    with repo.connection() as conn:
        settings_store.set_value(conn, "context.mining.support_weeks", 1, APPROVER)
        conn.commit()
        result = mining.run(conn, since=TODAY - timedelta(days=6), until=TODAY)
        assert result["support"]["weeks"] == 1 and not _rules(conn, "gate_decision")


def _next_monday() -> date:
    today = datetime.now(UTC).date()
    return today + timedelta(days=7 - today.weekday())


def test_a_missed_mining_day_is_caught_up_on_the_next_pass(week, monkeypatch):  # noqa: F811
    repo, _, _ = week
    monkeypatch.setenv("ATELIER_CONTEXT_NIGHTLY_HOUR", "3")
    monday = _next_monday()
    tuesday = datetime.combine(monday + timedelta(days=1), datetime.min.time(), UTC).replace(hour=4)
    # The scheduler was down on Monday: Tuesday's first pass runs Monday's learning loop, over the week before Monday.
    first = scheduler.tick(repo.settings, Settings(), now=tuesday)
    assert set(first) == {"staleness", "mining"}
    assert first["mining"]["scheduled_for"] == monday.isoformat() and first["mining"]["caught_up"] is True
    assert first["mining"]["window"] == {"since": (monday - timedelta(days=7)).isoformat(),
                                         "until": (monday - timedelta(days=1)).isoformat(), "week_id": None}
    assert sum(first["mining"]["candidates"].values()) > 0
    with repo.connection() as conn:
        state = conn.execute("SELECT value FROM settings WHERE key=%s", (f"context.mining.ran.{monday.isoformat()}",)).fetchone()["value"]
    assert state["state"] == "done"
    assert "mining" not in scheduler.tick(repo.settings, Settings(), now=tuesday + timedelta(days=1)), "Monday's week runs once"


def test_missed_weeks_are_read_from_the_last_pass_that_ran(week, monkeypatch):  # noqa: F811
    repo, _, _ = week
    monkeypatch.setenv("ATELIER_CONTEXT_NIGHTLY_HOUR", "3")
    monday = _next_monday()
    with repo.connection() as conn:
        # The last pass that ran was three Mondays ago; the two Mondays since were missed.
        conn.execute("INSERT INTO settings(key,value,updated_by) VALUES (%s,%s,'test')",
                     (f"context.mining.ran.{(monday - timedelta(days=21)).isoformat()}", json.dumps({"state": "done"})))
        conn.execute("INSERT INTO settings(key,value,updated_by) VALUES (%s,%s,'test')",
                     (f"context.mining.ran.{(monday - timedelta(days=70)).isoformat()}", json.dumps({"state": "done"})))
    now = datetime.combine(monday, datetime.min.time(), UTC).replace(hour=5)
    done = scheduler.tick(repo.settings, Settings(), now=now)
    assert done["mining"]["window"]["since"] == (monday - timedelta(days=21)).isoformat()
    assert done["mining"]["caught_up"] is True
    # Never further back than the support window, however long the scheduler was down.
    assert scheduler.mining_since(repo.settings, monday + timedelta(days=70), 4) == monday + timedelta(days=70 - 28)
    assert scheduler.mining_day(monday + timedelta(days=3), 0) == monday and scheduler.mining_day(monday, 0) == monday


# ------------------------------------------------------------------------------------------------ the benchmark


def _warnings(repo):
    with repo.connection() as conn:
        return [w["message"] for w in staleness.warnings(conn)]


def _outputs():
    """A saved strategist answer per development week (mocked responses: no request leaves)."""
    runs = BACKEND_ROOT.parent / "research" / "benchmark-v1" / "runs"
    return {w: json.loads((runs / f"strategist_v5-{w}-s1.wia-kb-2026-10-19.c-0b931261.json").read_text(encoding="utf-8"))["output"]
            for w in ("week1", "week2")}


def test_an_identity_change_confirmed_in_the_app_reaches_an_approved_benchmarked_version(week, monkeypatch, tmp_path):  # noqa: F811
    from evaluation import run as ev
    if benchmarking.harness()[1]:
        pytest.skip("Benchmark v1's inputs are not checked out")
    repo, _, _ = week
    settings = repo.settings.model_copy(update={"brief_approvers": (APPROVER,), "identity_approvers": (APPROVER,)})
    monkeypatch.delenv("CONTENT_ATELIER_KNOWLEDGE_BASE_DIR", raising=False)
    monkeypatch.setattr(ev, "OUT", tmp_path / "benchmark-v1")
    monkeypatch.setattr(ev, "_key", lambda: "not-a-key")
    outputs = _outputs()
    _record_configuration(repo, V5)  # the recorded answers below are strategist v5's
    week1 = {m["moment_id"] for m in ev.packet("week1")}
    sent = []

    def answer(url, body, headers, *, timeout, before_send=None):
        sent.append(body["model"])
        user = body["messages"][1]["content"]
        output = outputs["week1" if any(m in user for m in week1) else "week2"]
        return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(output)}, "finish_reason": "stop"}],
                                         "usage": {"cost": 0.05}}, request=httpx.Request("POST", url))
    monkeypatch.setattr(transport, "send", answer)

    # 1. The learning loop proposes a rule; an identity approver accepts it in the review queue.
    with repo.connection() as conn:
        mining.run(conn)
        rule = _rules(conn, "gate_decision")[0]
        review.decide(conn, settings, rule["item_id"], rule["hash"], "accept", APPROVER, reason="Whitney's rule, twice")
    assert any("wait to be compiled (rejection rules)" in w for w in _warnings(repo)), "the cycle says it waits"

    # 2. Compiled and approved in the app: the version waits for its benchmark, and the cycle says why it cannot run yet.
    with repo.connection() as conn:
        compiled = compiler.compile_version(conn, on=TODAY, actor=APPROVER, root=ROOT)
        version = compiled["version"]
        assert compiled["changes"]["rejection_rules"] == "identity"
    assert not any("wait to be compiled" in w for w in _warnings(repo))
    assert any("waits for an identity approver" in w for w in _warnings(repo))
    with repo.connection() as conn:
        assert compiler.approve(conn, settings, version, APPROVER, note="Read the diff")["state"] == "approved_pending_benchmark"
    early = datetime.now(UTC).replace(hour=1)  # before the nightly hour: only the benchmark part runs

    # 3. Safe by default: without a standing plan a person created, nothing is queued and nothing is sent.
    refused = scheduler.tick(repo.settings, Settings(), now=early)["benchmark"]
    assert refused["state"] == "refused" and "no standing run plan" in refused["reason"]
    assert any("cannot run: no standing run plan" in w for w in _warnings(repo))
    with repo.connection() as conn:
        create_sql_plan(conn, purpose="a weekly run", stages=["evaluation"], models=["openai/gpt-6.1-sol"], input_set_hash="*",
                        max_calls=50, max_cost_usd=5, approver=APPROVER)
        small = create_sql_plan(conn, purpose="kb benchmark", stages=["evaluation"], models=["openai/gpt-6.1-sol"],
                                input_set_hash="*", max_calls=5, max_cost_usd=5, approver=APPROVER, hours=24 * 90,
                                details={"standing": "kb_benchmark"})
    refused = scheduler.tick(repo.settings, Settings(), now=early)["benchmark"]
    assert "has 5 calls left and the benchmark needs 12" in refused["reason"], "a plan made for something else is never spent"
    with repo.connection() as conn:
        conn.execute("UPDATE run_plans SET status='closed' WHERE plan_id=%s", (small["plan_id"],))
        plan = create_sql_plan(conn, purpose="Standing: benchmark approved identity changes (L.B11)", stages=["evaluation"],
                               models=["openai/gpt-6.1-sol"], input_set_hash="*", max_calls=12, max_cost_usd=2,
                               approver=APPROVER, hours=24 * 90, details={"standing": "kb_benchmark"})
        assert not conn.execute("SELECT 1 FROM pipeline_jobs WHERE stage='evaluation_run'").fetchone()
    assert not sent

    # 4. Under the standing plan the scheduler queues one job; a second pass does not queue another.
    queued = scheduler.tick(repo.settings, Settings(), now=early)["benchmark"]
    assert queued["state"] == "queued" and queued["plan_id"] == plan["plan_id"]
    assert scheduler.tick(repo.settings, Settings(), now=early)["benchmark"]["state"] == "queued"
    with repo.connection() as conn:
        jobs = conn.execute("SELECT * FROM pipeline_jobs WHERE stage='evaluation_run'").fetchall()
    assert len(jobs) == 1 and jobs[0]["queue"] == "bulk" and jobs[0]["week_id"] is None

    # 5. The worker benchmarks the version and its base under the plan and records the result for an approver.
    worker = SQLWorker(repo.settings, Settings(), provider=SeedProvider())
    drain(worker)
    with repo.connection() as conn:
        job = conn.execute("SELECT * FROM pipeline_jobs WHERE stage='evaluation_run'").fetchone()
        assert job["status"] == "completed", job["error_summary"]
        spent = conn.execute("SELECT calls_used,cost_used_usd,status FROM run_plans WHERE plan_id=%s", (plan["plan_id"],)).fetchone()
        assert spent["calls_used"] == 12 and float(spent["cost_used_usd"]) == pytest.approx(0.6)
        assert conn.execute("SELECT count(*) n FROM llm_runs WHERE plan_id=%s AND status='succeeded'", (plan["plan_id"],)).fetchone()["n"] == 12
        record = {v["version"]: v for v in compiler.versions(conn)}[version]
    assert len(sent) == 12 and set(sent) == {"openai/gpt-6.1-sol"}
    scheduled = record["scheduled_benchmark"]
    assert record["state"] == "approved_pending_benchmark", "the result is recorded for an approver, never approved by the job"
    assert scheduled["state"] == "recorded" and scheduled["suggested"] == "pass" and scheduled["regressions"] == []
    assert scheduled["spent_usd"] == pytest.approx(0.6) and scheduled["base_version"] == load_knowledge_base(ROOT).version
    assert (tmp_path / "benchmark-v1" / "scheduled" / "results").is_dir()
    with repo.connection() as conn:
        assert compiler.active_version(conn) is None
    assert any("found no regression" in w and "An identity approver records the result" in w for w in _warnings(repo))
    assert scheduler.tick(repo.settings, Settings(), now=early)["benchmark"]["state"] == "recorded", "nothing runs twice"
    with repo.connection() as conn:
        assert conn.execute("SELECT count(*) n FROM pipeline_jobs WHERE stage='evaluation_run'").fetchone()["n"] == 1

    # 6. The approver records the verdict with the scheduled result: the version becomes the default.
    with repo.connection() as conn:
        done = compiler.record_benchmark(conn, settings, version, APPROVER, passed=True, result_ref=scheduled["result_ref"],
                                         note="Scheduled benchmark: no regression")
        assert done["state"] == "active" and compiler.active_version(conn) == version
    assert not any("benchmark" in w or "wait to be compiled" in w for w in _warnings(repo))


V5, V6 = "2026-10-18.wia-strategist.v5", "2026-10-20.wia-strategist.v6"


def _record_configuration(repo, profile, model="openai/gpt-6.1-sol"):
    """The configuration of record the benchmark follows (`settings apply` does this in production)."""
    from backend_pipeline import settings_store
    with repo.connection() as conn:
        settings_store.set_value(conn, "prompts.profile.strategist", profile, "tester@example.invalid")
        settings_store.set_value(conn, "models.angle_generation", model, "tester@example.invalid")


def _approved_version(repo, settings):
    with repo.connection() as conn:
        mining.run(conn)
        rule = _rules(conn, "gate_decision")[0]
        review.decide(conn, settings, rule["item_id"], rule["hash"], "accept", APPROVER, reason="ok")
        version = compiler.compile_version(conn, on=TODAY, actor=APPROVER, root=ROOT)["version"]
        compiler.approve(conn, settings, version, APPROVER, note="ok")
    return version


def _scheduled(repo, version):
    with repo.connection() as conn:
        return {v["version"]: v for v in compiler.versions(conn)}[version].get("scheduled_benchmark")


def test_the_benchmark_follows_the_configuration_of_record_not_a_fixed_strategist(week):  # noqa: F811
    from evaluation import run as ev
    repo, _, _ = week
    with repo.connection() as conn:
        config, model, why = benchmarking.configuration(ev, conn)
    assert config is None and "has no benchmark configuration" in why, "the legacy default profile cannot be benchmarked"
    _record_configuration(repo, V6)
    with repo.connection() as conn:
        assert benchmarking.configuration(ev, conn) == ("strategist_v6", "openai/gpt-6.1-sol", None)
    _record_configuration(repo, V5, model="openai/gpt-6-luna")
    with repo.connection() as conn:
        assert benchmarking.configuration(ev, conn) == ("strategist_v5", "openai/gpt-6-luna", None)
    with ev.under(model="openai/gpt-6-luna"):
        assert ev.model_of("strategist_v5") == "openai/gpt-6-luna"
    assert ev.model_of("strategist_v5") == "openai/gpt-6.1-sol", "the harness's own runs keep their configuration's model"


def test_inputs_that_are_absent_skip_the_benchmark_with_a_recorded_reason(week, monkeypatch):  # noqa: F811
    repo, _, _ = week
    settings = repo.settings.model_copy(update={"brief_approvers": (APPROVER,)})
    version = _approved_version(repo, settings)
    now = datetime.now(UTC).replace(hour=1)
    # The production image: no research/ inputs. Nothing is queued; the version says why, once.
    monkeypatch.setattr(benchmarking, "harness", lambda: (None, "benchmark v1's inputs are not on this machine (research/ is not in the image, R48)"))
    first = scheduler.tick(repo.settings, Settings(), now=now)["benchmark"]
    assert first["state"] == "refused" and first["skip"] is True
    held = _scheduled(repo, version)
    assert held["state"] == "skipped" and "research/ is not in the image" in held["reason"]
    scheduler.tick(repo.settings, Settings(), now=now + timedelta(minutes=1))
    assert _scheduled(repo, version)["at"] == held["at"], "the same reason is recorded once, not on every pass"
    assert any("cannot run: benchmark v1's inputs are not on this machine" in w for w in _warnings(repo))
    with repo.connection() as conn:
        assert not conn.execute("SELECT 1 FROM pipeline_jobs WHERE stage='evaluation_run'").fetchone()
        assert compiler.active_version(conn) is None, "a skipped benchmark approves nothing"
    # A profile the harness has no configuration for is skipped the same way (the legacy default).
    monkeypatch.undo()
    from evaluation import run as ev
    if benchmarking.harness()[1]:
        pytest.skip("Benchmark v1's inputs are not checked out")
    scheduler.tick(repo.settings, Settings(), now=now + timedelta(minutes=2))
    assert "has no benchmark configuration" in _scheduled(repo, version)["reason"]
    assert ev.CONFIGS["strategist_v6"]


def test_a_job_that_reaches_a_worker_without_the_inputs_finishes_as_skipped_not_failed(week, monkeypatch):  # noqa: F811
    from evaluation import run as ev
    if benchmarking.harness()[1]:
        pytest.skip("Benchmark v1's inputs are not checked out")
    repo, _, _ = week
    settings = repo.settings.model_copy(update={"brief_approvers": (APPROVER,)})
    _record_configuration(repo, V6)
    version = _approved_version(repo, settings)
    with repo.connection() as conn:
        create_sql_plan(conn, purpose="standing", stages=["evaluation"], models=["openai/gpt-6.1-sol"], input_set_hash="*",
                        max_calls=12, max_cost_usd=2, approver=APPROVER, hours=24 * 90, details={"standing": "kb_benchmark"})
    queued = scheduler.tick(repo.settings, Settings(), now=datetime.now(UTC).replace(hour=1))["benchmark"]
    assert queued["state"] == "queued" and queued["config"] == "strategist_v6"
    with repo.connection() as conn:
        refs = conn.execute("SELECT input_refs FROM pipeline_runs WHERE run_scope='kb_benchmark'").fetchone()["input_refs"]
    assert refs["config"] == "strategist_v6" and refs["model"] == "openai/gpt-6.1-sol"
    # The job runs on a worker whose image has no research/ folder.
    monkeypatch.setattr(benchmarking, "harness", lambda: (None, "benchmark v1's inputs are not on this machine"))
    drain(SQLWorker(repo.settings, Settings(), provider=SeedProvider()))
    with repo.connection() as conn:
        job = conn.execute("SELECT * FROM pipeline_jobs WHERE stage='evaluation_run'").fetchone()
        assert job["status"] == "completed", job["error_summary"]
        assert conn.execute("SELECT calls_used FROM run_plans WHERE details->>'standing'='kb_benchmark'").fetchone()["calls_used"] == 0
    held = _scheduled(repo, version)
    assert held["state"] == "skipped" and "not on this machine" in held["reason"]
    assert ev.CONFIGS


def test_the_benchmark_job_never_runs_where_the_harness_is_missing(week, monkeypatch):  # noqa: F811
    repo, _, _ = week
    settings = repo.settings.model_copy(update={"brief_approvers": (APPROVER,)})
    monkeypatch.setattr(benchmarking, "harness", lambda: (None, "the evaluation harness is not installed where the scheduler runs"))
    with repo.connection() as conn:
        mining.run(conn)
        rule = _rules(conn, "gate_decision")[0]
        review.decide(conn, settings, rule["item_id"], rule["hash"], "accept", APPROVER, reason="ok")
        version = compiler.compile_version(conn, on=TODAY, actor=APPROVER, root=ROOT)["version"]
        compiler.approve(conn, settings, version, APPROVER, note="ok")
        create_sql_plan(conn, purpose="standing", stages=["evaluation"], models=["openai/gpt-6.1-sol"], input_set_hash="*",
                        max_calls=12, max_cost_usd=2, approver=APPROVER, hours=24 * 90, details={"standing": "kb_benchmark"})
    done = scheduler.tick(repo.settings, Settings(), now=datetime.now(UTC).replace(hour=1))["benchmark"]
    assert done["state"] == "refused" and "not installed" in done["reason"]
    with repo.connection() as conn:
        assert not conn.execute("SELECT 1 FROM pipeline_jobs WHERE stage='evaluation_run'").fetchone()
