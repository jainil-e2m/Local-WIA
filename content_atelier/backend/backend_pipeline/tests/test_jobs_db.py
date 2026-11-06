"""0.B5 / 0.B6: one executor for every job, and a reconcile loop that makes Redis loss and worker loss end correctly.

Real PostgreSQL (the migrated platform database), fakeredis for the queues, RQ workers run in-process in burst mode.
No network and no paid call: the synthetic cycle uses the offline provider, the synthetic brief the offline fake of
test_briefs.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import fakeredis
import pytest
from rq import Queue, SimpleWorker
from rq.serializers import JSONSerializer
from test_briefs import finish, ready  # noqa: F401 (the synthetic brief of the brief suite)

from backend_pipeline.database import connect
from backend_pipeline.jobs import dispatch, health, periodic, policy, scheduler
from backend_pipeline.jobs.executor import run_job
from backend_pipeline.jobs.recover import recover_expired
from backend_pipeline.sql_pipeline import SQLWorker
from backend_pipeline.storage_config import StorageSettings
from backend_pipeline.tests.platform_db import platform_setup, platform_url  # noqa: F401 (fixtures)
from backend_pipeline.tests.test_sql_storage import NonemptyProvider

WEEK = "week_2026-06-01"


@pytest.fixture
def redis():
    connection = fakeredis.FakeRedis()
    yield connection
    connection.flushall()


@pytest.fixture
def executor(platform_setup, monkeypatch):
    """The environment an RQ worker finds: storage from `from_env`, and the offline provider in SQLWorker."""
    repo, models, tmp_path = platform_setup
    provider = NonemptyProvider()
    monkeypatch.setattr(StorageSettings, "from_env", classmethod(lambda cls: repo.settings))
    original = SQLWorker.__init__
    monkeypatch.setattr(SQLWorker, "__init__", lambda self, storage, m=None, *, provider=None: original(self, storage, models, provider=provider or provider_of[0]))
    provider_of = [provider]
    return repo, models, provider_of


def work(redis, queues=policy.QUEUES, max_jobs=None):
    """A worker that drains the named queues and stops (RQ's burst mode)."""
    SimpleWorker([Queue(n, connection=redis, serializer=JSONSerializer) for n in queues], connection=redis,
                 serializer=JSONSerializer).work(burst=True, with_scheduler=False, max_jobs=max_jobs)


def rows(repo, sql, *args):
    with repo.connection() as conn:
        return conn.execute(sql, args).fetchall()


def cycle_done(repo, run_id):
    """A weekly run ends at the editor gate; every job of it has completed."""
    status = rows(repo, "SELECT status FROM pipeline_runs WHERE run_id=%s", run_id)[0]["status"]
    return status == "waiting_for_review" and not rows(repo, "SELECT 1 FROM pipeline_jobs WHERE run_id=%s AND status<>'completed'", run_id)


def run_until_idle(repo, redis, limit=12):
    """Reconcile (dispatch what is ready), work the queues, repeat: the scheduler and the workers, taking turns."""
    for _ in range(limit):
        done = scheduler.reconcile(repo, redis)
        before = len(rows(repo, "SELECT 1 FROM pipeline_jobs WHERE status='completed'"))
        work(redis)
        if not done["dispatched"] and not done["recovered"] and len(rows(repo, "SELECT 1 FROM pipeline_jobs WHERE status='completed'")) == before:
            return
    raise AssertionError("jobs did not settle")


# ---- the policy ----------------------------------------------------------------------------------------------------

def test_every_stage_has_a_queue_and_a_timeout():
    assert policy.queue_for("brief_writing") == "interactive" and policy.queue_for("pack_writing") == "interactive"
    assert policy.queue_for("moment_extraction") == "default" and policy.queue_for("angle_matching") == "default"
    assert policy.queue_for("transcript_chunk_embedding") == "bulk" and policy.queue_for("document_normalise") == "bulk"
    assert policy.queue_for("transcript_chunk_embedding", intake=True) == "intake"
    assert policy.queue_for("intake_extract") == "media" and policy.queue_for("intake_slack") == "intake"
    assert policy.timeout_for("moment_extraction") > policy.timeout_for("brief_prepare") > 0
    assert policy.timeout_for("a_stage_nobody_listed") == policy.DEFAULT_TIMEOUT
    assert policy.placement("brief_context") == {"executor": "rq", "queue": "interactive"}


def test_every_new_job_row_names_its_executor_and_queue(executor):
    repo, models, _ = executor
    repo.submit(WEEK, "synthetic")
    jobs = rows(repo, "SELECT stage,executor,queue FROM pipeline_jobs")
    assert jobs and all(j["executor"] == "rq" and j["queue"] == policy.queue_for(j["stage"]) for j in jobs)


# ---- 0.B5: a synthetic cycle and a synthetic brief complete on it ---------------------------------------------------

def test_a_synthetic_cycle_completes_on_the_queues(executor, redis):
    repo, models, _ = executor
    submitted = repo.submit(WEEK, "synthetic")
    run_until_idle(repo, redis)
    assert cycle_done(repo, submitted["run_id"])
    jobs = rows(repo, "SELECT stage,status,attempt_count,rq_job_id FROM pipeline_jobs WHERE run_id=%s", submitted["run_id"])
    assert jobs and all(j["status"] == "completed" and j["attempt_count"] == 1 and j["rq_job_id"] for j in jobs)
    assert len({j["rq_job_id"] for j in jobs}) == len(jobs), "one RQ job per row and attempt"
    assert not rows(repo, "SELECT 1 FROM pipeline_jobs WHERE status<>'completed'")


def test_a_synthetic_brief_completes_on_the_queues(executor, redis, monkeypatch):
    repo, models, provider_of = executor
    ready_data = ready((repo, models, None))
    provider_of[0] = ready_data[2]
    run = ready_data[5]
    run_until_idle(repo, redis, limit=30)
    jobs = rows(repo, "SELECT stage,status,queue FROM pipeline_jobs WHERE run_id=%s", run["run_id"])
    assert jobs and all(j["status"] == "completed" and j["queue"] == "interactive" for j in jobs), jobs
    assert rows(repo, "SELECT 1 FROM content_briefs WHERE angle_id=%s", ready_data[4]["angle_id"])


def test_dispatching_twice_is_one_rq_job_and_two_workers_run_a_row_once(executor, redis):
    repo, models, _ = executor
    repo.submit(WEEK, "synthetic")
    first = dispatch.dispatch_ready(repo, redis)
    assert first and dispatch.dispatch_ready(repo, redis) == [], "a live RQ job is not dispatched again"
    assert Queue("default", connection=redis, serializer=JSONSerializer).count == len(first)
    job_id = first[0]
    assert run_job(job_id) == job_id
    assert run_job(job_id) is None, "the second worker finds the row finished"
    assert rows(repo, "SELECT attempt_count FROM pipeline_jobs WHERE job_id=%s", job_id)[0]["attempt_count"] == 1


def test_the_rq_job_id_is_the_idempotency_key_and_the_attempt(executor, redis):
    repo, models, _ = executor
    repo.submit(WEEK, "synthetic")
    [first, *_] = dispatch.dispatch_ready(repo, redis)
    row = rows(repo, "SELECT idempotency_key,rq_job_id FROM pipeline_jobs WHERE job_id=%s", first)[0]
    assert row["rq_job_id"] == dispatch.transport_id({"idempotency_key": row["idempotency_key"], "attempt_count": 0})
    assert ":" not in row["rq_job_id"]


def test_the_inline_runner_and_the_queue_worker_claim_the_same_way(executor, redis):
    repo, models, _ = executor
    submitted = repo.submit(WEEK, "synthetic")
    inline = SQLWorker(repo.settings, models).once(run_id=submitted["run_id"])
    assert inline
    first = rows(repo, "SELECT stage,executor FROM pipeline_jobs WHERE job_id=%s", inline)[0]
    assert first["executor"] == "rq"


# ---- 0.B5/0.B6 drills: Redis flushed, worker killed --------------------------------------------------------------

def test_flushing_redis_mid_cycle_ends_correctly_after_one_loop(executor, redis):
    repo, models, provider_of = executor
    submitted = repo.submit(WEEK, "synthetic")
    run_id = submitted["run_id"]
    scheduler.reconcile(repo, redis)
    work(redis, max_jobs=1)  # the first stage ran and dispatched its successor
    assert Queue("default", connection=redis, serializer=JSONSerializer).count == 1
    redis.flushall()  # everything queued is lost
    assert Queue("default", connection=redis, serializer=JSONSerializer).count == 0
    left = rows(repo, "SELECT 1 FROM pipeline_jobs WHERE run_id=%s AND status<>'completed'", run_id)
    assert left, "work remained when Redis was lost"
    calls_before = len(provider_of[0].calls)
    jobs_before = rows(repo, "SELECT count(*) n FROM pipeline_jobs")[0]["n"]
    run_until_idle(repo, redis)
    assert cycle_done(repo, run_id)
    assert rows(repo, "SELECT count(*) n FROM pipeline_jobs")[0]["n"] == jobs_before, "no duplicate rows"
    stages = [j["stage"] for j in rows(repo, "SELECT stage FROM pipeline_jobs WHERE run_id=%s", run_id)]
    assert len(stages) == len(set(stages))
    assert len(provider_of[0].calls) > calls_before, "the remaining stages ran, once each"
    assert max(j["attempt_count"] for j in rows(repo, "SELECT attempt_count FROM pipeline_jobs WHERE run_id=%s", run_id)) == 1


def test_every_call_of_a_weekly_run_on_the_queues_is_a_database_row(executor, redis):
    """0.B4 on the SQL path: the weekly stage calls (extraction, strategist) record their llm_runs rows in the database the
    run lives in, with the prompt version, not in a file on the worker's disk (lost with the container, and not writable
    in the image)."""
    repo, models, provider_of = executor
    run_id = repo.submit(WEEK, "synthetic")["run_id"]
    run_until_idle(repo, redis)
    assert cycle_done(repo, run_id) and provider_of[0].calls
    recorded = rows(repo, "SELECT stage,status,prompt_version,provider FROM llm_runs WHERE details->>'run_id'=%s", run_id)
    assert {r["stage"] for r in recorded} >= {"moment_extraction", "angle_generation"}
    chat = [r for r in recorded if r["stage"] != "embedding"]
    assert all(r["prompt_version"] and r["provider"] == "fake" and r["status"] == "succeeded" for r in chat), chat
    from pathlib import Path
    assert not list(Path(repo.settings.artifact_root).rglob("llm_runs*.jsonl")), "nothing went to a file on the worker's disk"


def test_a_worker_killed_before_any_call_is_queued_again_once(executor, redis):
    repo, models, provider_of = executor
    submitted = repo.submit(WEEK, "synthetic")
    killed = repo.claim(run_id=submitted["run_id"])  # a worker took it and died: the lease will run out
    with repo.connection() as conn:
        conn.execute("UPDATE pipeline_jobs SET lease_expires_at=now()-interval '1 second' WHERE job_id=%s", (killed["job_id"],))
    one = scheduler.reconcile(repo, redis)
    assert [r["outcome"] for r in one["recovered"]] == ["queued"] and one["dispatched"] == [killed["job_id"]]
    run_until_idle(repo, redis)
    assert cycle_done(repo, submitted["run_id"])
    assert rows(repo, "SELECT attempt_count FROM pipeline_jobs WHERE job_id=%s", killed["job_id"])[0]["attempt_count"] == 2
    events = rows(repo, "SELECT 1 FROM pipeline_events WHERE run_id=%s AND event_type='lease_expired'", submitted["run_id"])
    assert len(events) == 1


def sent_call(repo, fingerprint, status="sent"):
    with repo.connection() as conn:
        conn.execute("""INSERT INTO llm_runs(llm_run_id,stage,model,routing_policy,request_fingerprint,status)
            VALUES ('llm_orphan','moment_extraction','m','p',%s,%s)""", (fingerprint, status))


def test_a_worker_killed_after_a_paid_call_was_sent_is_not_run_again(executor, redis):
    repo, models, provider_of = executor
    submitted = repo.submit(WEEK, "synthetic")
    killed = repo.claim(run_id=submitted["run_id"])
    sent_call(repo, "fp-the-answer-was-never-saved")
    with repo.connection() as conn:
        conn.execute("UPDATE pipeline_jobs SET lease_expires_at=now()-interval '1 second' WHERE job_id=%s", (killed["job_id"],))
    one = scheduler.reconcile(repo, redis)
    assert [r["outcome"] for r in one["recovered"]] == ["failed"] and one["dispatched"] == []
    calls = len(provider_of[0].calls)
    llm_rows = rows(repo, "SELECT count(*) n FROM llm_runs")[0]["n"]
    for _ in range(3):
        scheduler.reconcile(repo, redis)
        work(redis)
    assert len(provider_of[0].calls) == calls and rows(repo, "SELECT count(*) n FROM llm_runs")[0]["n"] == llm_rows
    job = rows(repo, "SELECT status,error_summary,attempt_count FROM pipeline_jobs WHERE job_id=%s", killed["job_id"])[0]
    assert job["status"] == "failed" and "not saved" in job["error_summary"] and job["attempt_count"] == 1
    assert rows(repo, "SELECT status FROM llm_runs WHERE llm_run_id='llm_orphan'")[0]["status"] == "failed"
    assert rows(repo, "SELECT status FROM pipeline_runs WHERE run_id=%s", submitted["run_id"])[0]["status"] == "failed"
    # An explicit retry is the decision a person makes; it then runs once.
    repo.retry(killed["job_id"], "team-user")
    from backend_pipeline.jobs.recover import RETRY_REQUESTED
    assert rows(repo, "SELECT current_message FROM pipeline_jobs WHERE job_id=%s", killed["job_id"])[0]["current_message"] == RETRY_REQUESTED
    run_until_idle(repo, redis)
    assert cycle_done(repo, submitted["run_id"])


def lose_lease(repo, job):
    with repo.connection() as conn:
        conn.execute("UPDATE pipeline_jobs SET lease_expires_at=now()-interval '1 second' WHERE job_id=%s", (job["job_id"],))


@pytest.mark.parametrize("cache", ["stage", "brief-cache", "pack-cache"])
def test_a_sent_call_whose_answer_was_saved_is_replayed_not_failed(executor, redis, tmp_path, cache):
    """The retry reads a validated answer for the exact request before it sends anything: the weekly stage cache
    (StageCaller.call_json) or a brief or pack response cache (llm/workflow.chat). So it pays nothing."""
    repo, models, _ = executor
    from backend_pipeline.models import StageArtifact
    from backend_pipeline.store import JsonStore, canonical_hash
    submitted = repo.submit(WEEK, "synthetic")
    killed = repo.claim(run_id=submitted["run_id"])
    fingerprint = "fp-saved-answer"
    store = JsonStore(repo.settings.artifact_root)
    if cache == "stage":
        output = {"moments": []}
        store.cache_artifact(StageArtifact(artifact_id="artifact_saved", run_id=submitted["run_id"], stage="moment_extraction",
                                           request_fingerprint=fingerprint, model_id="m", status="validated", input_hashes=["h"],
                                           output=output, output_hash=canonical_hash(output)),
                             f"service_calls/{fingerprint}/attempts/artifact_saved/artifact.json")
        assert store.find_artifact(fingerprint)
    else:
        store.write_json(f"{cache}/{fingerprint}.json", {"fingerprint": fingerprint, "output": {}, "output_hash": canonical_hash({})})
    sent_call(repo, fingerprint)
    lose_lease(repo, killed)
    [result] = recover_expired(repo)
    assert result["outcome"] == "queued"
    assert rows(repo, "SELECT status FROM llm_runs WHERE llm_run_id='llm_orphan'")[0]["status"] == "failed", "the orphaned row is closed"
    # Found by the N1 shakedown: a job put back on the queue still said "Processing".
    from backend_pipeline.jobs.recover import QUEUED_AGAIN
    assert rows(repo, "SELECT current_message FROM pipeline_jobs WHERE job_id=%s", killed["job_id"])[0]["current_message"] == QUEUED_AGAIN


def test_a_sent_call_whose_only_saved_answer_the_retry_would_not_take_is_not_run_again(executor, redis):
    """An earlier attempt's received output for the same request (one that failed validation, say, which is why a
    person retried) is not a replay: only extraction re-reads such an output, and only when it now validates. Queueing
    the job again would send the request a second time while the lost call may already have been billed (0.B5)."""
    repo, models, provider_of = executor
    from backend_pipeline.store import JsonStore
    submitted = repo.submit(WEEK, "synthetic")
    killed = repo.claim(run_id=submitted["run_id"])
    fingerprint = "fp-received-never-validated"
    store = JsonStore(repo.settings.artifact_root)
    store.write_json(f"service_calls/{fingerprint}/attempts/attempt-1/output.received.json", {"not": "what the schema asks"})
    assert store.saved_attempts(fingerprint) and not store.find_artifact(fingerprint)
    sent_call(repo, fingerprint)
    lose_lease(repo, killed)
    [result] = recover_expired(repo)
    assert result["outcome"] == "failed" and "not saved" in result["message"]
    calls = len(provider_of[0].calls)
    for _ in range(2):
        scheduler.reconcile(repo, redis)
        work(redis)
    assert len(provider_of[0].calls) == calls, "nothing is sent again until a person retries"
    stopped = rows(repo, "SELECT status,current_message FROM pipeline_jobs WHERE job_id=%s", killed["job_id"])[0]
    assert stopped["status"] == "failed" and stopped["current_message"] != "Processing"


def test_a_chunk_embedding_lost_lease_always_needs_review(executor, redis):
    repo, models, _ = executor
    repo.submit(WEEK, "synthetic")
    with repo.connection() as conn:
        job = conn.execute("SELECT job_id FROM pipeline_jobs ORDER BY created_at LIMIT 1").fetchone()
        conn.execute("""UPDATE pipeline_jobs SET stage='transcript_chunk_embedding',status='running',lease_token='x',
            lease_expires_at=now()-interval '1 minute',attempt_count=1 WHERE job_id=%s""", (job["job_id"],))
    [result] = recover_expired(repo)
    assert result["outcome"] == "failed" and "review" in result["message"]


def test_attempts_are_capped(executor, redis):
    repo, models, _ = executor
    repo.submit(WEEK, "synthetic")
    with repo.connection() as conn:
        job = conn.execute("SELECT job_id FROM pipeline_jobs ORDER BY created_at LIMIT 1").fetchone()
        conn.execute("""UPDATE pipeline_jobs SET status='running',lease_token='x',lease_expires_at=now()-interval '1 minute',
            attempt_count=%s WHERE job_id=%s""", (policy.MAX_ATTEMPTS, job["job_id"]))
    [result] = recover_expired(repo)
    assert result["outcome"] == "failed" and "attempt limit" in result["message"]


# ---- 0.B6: the scheduler ------------------------------------------------------------------------------------------

def due_on(weekday, hour=0):
    return periodic.Task("weekly-test", lambda now: periodic.week(now, weekday=weekday, hour=hour), lambda now: {"ran": True})


def test_a_period_runs_once_however_many_passes_and_schedulers(executor):
    repo, models, _ = executor
    ran = []
    task = periodic.Task("daily-test", lambda now: periodic.day(now, hour=3), lambda now: ran.append(now) or {"n": len(ran)})
    morning = datetime(2026, 10, 19, 4, 0, tzinfo=UTC)
    assert periodic.run_due(repo.settings, [task], morning)["ran"] == ["daily-test:2026-10-19"]
    assert periodic.run_due(repo.settings, [task], morning + timedelta(minutes=1))["ran"] == []
    assert periodic.run_due(repo.settings, [task], morning - timedelta(hours=2))["ran"] == [], "not yet due"
    assert len(ran) == 1
    assert periodic.run_due(repo.settings, [task], morning + timedelta(days=1))["ran"] == ["daily-test:2026-10-20"]


def test_a_missed_tick_is_recovered_on_the_next_loop(executor):
    """The scheduler was down for the whole hour a weekly task fell due: the first pass afterwards runs that week."""
    repo, models, _ = executor
    ran = []
    task = periodic.Task("weekly-test", lambda now: periodic.week(now, weekday=0, hour=9), lambda now: ran.append(1) or {})
    down = datetime(2026, 10, 19, 9, 0, tzinfo=UTC)  # Monday 09:00: due, but nothing was running
    back = down + timedelta(days=2, hours=5)  # the scheduler returns Wednesday afternoon
    assert periodic.run_due(repo.settings, [task], down - timedelta(hours=1))["ran"] == []
    assert periodic.run_due(repo.settings, [task], back)["ran"] == ["weekly-test:2026-W43"]
    assert periodic.run_due(repo.settings, [task], back + timedelta(hours=1))["ran"] == []
    assert len(ran) == 1


def test_a_failed_period_runs_again_until_the_attempt_limit(executor):
    repo, models, _ = executor
    attempts = []

    def boom(now):
        attempts.append(1)
        raise RuntimeError("source not ready")
    task = periodic.Task("flaky-test", lambda now: periodic.day(now), boom)
    now = datetime(2026, 10, 19, 4, 0, tzinfo=UTC)
    periodic.run_due(repo.settings, [task], now)
    periodic.run_due(repo.settings, [task], now)
    assert len(attempts) == 1, "a failed period waits before it is tried again (1 November: three attempts in 90 seconds)"
    for _ in range(6):
        with connect(repo.settings.database_url, vectors=False) as conn:
            conn.execute("UPDATE settings SET updated_at=now()-interval '1 day' WHERE key='schedule.flaky-test.2026-10-19'")
            conn.commit()
        periodic.run_due(repo.settings, [task], now)
    assert len(attempts) == periodic.MAX_ATTEMPTS
    weekly = periodic.Task("flaky-weekly", lambda now: periodic.day(now), boom, attempts=5)
    attempts.clear()
    for _ in range(8):
        periodic.run_due(repo.settings, [weekly], now)
        with connect(repo.settings.database_url, vectors=False) as conn:
            conn.execute("UPDATE settings SET updated_at=now()-interval '1 day' WHERE key='schedule.flaky-weekly.2026-10-19'")
            conn.commit()
    assert len(attempts) == 5
    with connect(repo.settings.database_url, vectors=False) as conn:
        value = conn.execute("SELECT value FROM settings WHERE key='schedule.flaky-test.2026-10-19'").fetchone()["value"]
    assert value["state"] == "failed" and "source not ready" in value["error"]


def test_a_period_left_running_by_a_dead_scheduler_is_claimed_again(executor):
    repo, models, _ = executor
    key = "schedule.dead-test.2026-10-19"
    assert periodic.claim(repo.settings, key) and not periodic.claim(repo.settings, key)
    with connect(repo.settings.database_url, vectors=False) as conn:
        conn.execute("UPDATE settings SET updated_at=now()-interval '2 hours' WHERE key=%s", (key,))
        conn.commit()
    assert periodic.claim(repo.settings, key)


def test_a_period_that_keeps_killing_its_scheduler_stops_at_the_attempt_limit(executor):
    """A run that never returns (the process dies in it) counts as an attempt too, so it is not started again every hour
    for ever; with a paid step inside (the learning loop's categoriser) that would also pay each time."""
    repo, models, _ = executor
    key = "schedule.crash-test.2026-10-19"
    claims = 0
    for _ in range(periodic.MAX_ATTEMPTS + 3):
        if periodic.claim(repo.settings, key):
            claims += 1
        with connect(repo.settings.database_url, vectors=False) as conn:  # the process died inside the run
            conn.execute("UPDATE settings SET updated_at=now()-interval '2 hours' WHERE key=%s", (key,))
            conn.commit()
    assert claims == periodic.MAX_ATTEMPTS


def test_one_scheduler_pass_reconciles_runs_scheduled_work_and_beats(executor, redis):
    repo, models, _ = executor
    repo.submit(WEEK, "synthetic")
    ran = []
    task = periodic.Task("each-pass", lambda now: "p", lambda now: ran.append(1) or {})
    result = scheduler.tick(repo.settings, models, repo=repo, redis_connection=redis, tasks=[task])
    assert result["reconcile"]["dispatched"] and result["periodic"]["ran"] == ["each-pass:p"] and ran
    with connect(repo.settings.database_url, vectors=False) as conn:
        assert conn.execute("SELECT 1 FROM settings WHERE key=%s", (scheduler.HEARTBEAT_KEY,)).fetchone()


def test_a_failing_part_does_not_stop_the_others(executor, redis, monkeypatch):
    repo, models, _ = executor
    repo.submit(WEEK, "synthetic")
    monkeypatch.setattr(scheduler.periodic, "run_due", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    result = scheduler.tick(repo.settings, models, repo=repo, redis_connection=redis)
    assert result["periodic"] == {"error": True} and result["reconcile"]["dispatched"]


def test_intake_jobs_waiting_for_a_retry_are_released_when_due(executor):
    repo, models, _ = executor
    repo.submit(WEEK, "synthetic")
    with repo.connection() as conn:
        job = conn.execute("SELECT job_id FROM pipeline_jobs LIMIT 1").fetchone()
        conn.execute("""UPDATE pipeline_jobs SET stage='intake_fathom',status='waiting',
            progress_details=COALESCE(progress_details,'{}'::jsonb)||'{"retry_at":"2020-01-01T00:00:00+00:00"}'::jsonb WHERE job_id=%s""", (job["job_id"],))
    assert scheduler.release_waiting(repo) == 1
    assert rows(repo, "SELECT status FROM pipeline_jobs WHERE job_id=%s", job["job_id"])[0]["status"] == "queued"


# ---- job health from the job rows ---------------------------------------------------------------------------------

def test_health_is_computed_from_the_job_rows(executor, redis):
    repo, models, _ = executor
    submitted = repo.submit(WEEK, "synthetic")
    with repo.connection() as conn:
        silent = health.summary(conn)
    assert not silent["ok"] and any("scheduler" in p for p in silent["problems"])
    scheduler.tick(repo.settings, models, repo=repo, redis_connection=redis, tasks=[])
    with repo.connection() as conn:
        fresh = health.summary(conn)
    assert fresh["ok"] and fresh["queues"]["default"]["queued"] >= 1 and fresh["queues"]["default"]["oldest_queued_seconds"] is not None
    killed = repo.claim(run_id=submitted["run_id"])
    with repo.connection() as conn:
        conn.execute("UPDATE pipeline_jobs SET lease_expires_at=now()-interval '1 second' WHERE job_id=%s", (killed["job_id"],))
        lost = health.summary(conn)
    assert not lost["ok"] and lost["queues"][killed["queue"]]["lost"] == 1
    assert any("lost their lease" in p for p in lost["problems"])
    later = datetime.now(UTC) + timedelta(minutes=30)
    with repo.connection() as conn:
        assert any("waited" in p for p in health.summary(conn, now=later)["problems"])


def test_workers_ready_reads_the_worker_registry(redis):
    assert not health.workers_ready(("default",), redis)
    worker = SimpleWorker([Queue("default", connection=redis, serializer=JSONSerializer)], connection=redis, serializer=JSONSerializer)
    worker.register_birth()
    worker.heartbeat()
    assert health.workers_ready(("default",), redis) and not health.workers_ready(("intake",), redis)


def test_the_polling_worker_and_its_heartbeat_files_are_gone():
    import importlib.util
    import backend_pipeline.storage_cli as cli
    assert importlib.util.find_spec("backend_pipeline.worker_status") is None
    with pytest.raises(SystemExit, match="polling worker is gone"):
        cli.main(["worker", "--watch"])


def test_the_command_line_has_the_four_processes():
    from backend_pipeline.jobs.__main__ import build_parser, queue_names
    parser = build_parser()
    assert parser.parse_args(["worker", "--queues", "intake"]).queues == "intake"
    assert parser.parse_args(["scheduler", "--once"]).once
    assert queue_names("interactive,default") == ["interactive", "default"]
    with pytest.raises(SystemExit):
        queue_names("nonsense")
    assert json.dumps(sorted(policy.QUEUES)) == json.dumps(sorted(["interactive", "default", "bulk", "intake", "media"]))


# ---- Phase 1: a document's normalise job runs on the bulk queue ------------------------------------------------------

def test_a_documents_normalise_job_is_queued_on_bulk_and_runs_on_the_one_executor(executor, redis, tmp_path):
    from test_documents_db import CLIENT_CALL

    from backend_pipeline.documents import intake
    repo, models, _ = executor
    folder = tmp_path / "drop"
    folder.mkdir()
    (folder / "GMT20260312-153000_Recording Review with Dana Lee.vtt").write_text(CLIENT_CALL, encoding="utf-8")
    result = intake.import_directory(repo, folder)
    jobs = rows(repo, "SELECT stage,queue,executor FROM pipeline_jobs WHERE run_id=%s", result["run_id"])
    assert jobs == [{"stage": "document_normalise", "queue": "bulk", "executor": "rq"}]
    run_until_idle(repo, redis)
    assert rows(repo, "SELECT status FROM pipeline_runs WHERE run_id=%s", result["run_id"])[0]["status"] == "completed"
    doc = rows(repo, "SELECT call_type,included,normalised_at FROM transcripts WHERE week_id IS NULL")[0]
    assert doc["call_type"] == "client_1to1" and doc["included"] and doc["normalised_at"] is not None


@pytest.mark.parametrize("how", ["failed", "lost"])
def test_one_document_that_fails_normalising_does_not_stop_the_rest_of_its_batch(executor, redis, tmp_path, how):
    """An import is one run with one `document_normalise` job per document. A document that fails (a handler error, or a
    worker lost past its attempts) must fail its own job only: the run stays open while other documents wait, and ends
    partially completed. Before, the run was set failed and every other queued document was never claimed."""
    from test_documents_db import CLIENT_CALL, INTERNAL_CALL

    from backend_pipeline.documents import intake
    repo, models, _ = executor
    folder = tmp_path / "drop"
    folder.mkdir()
    (folder / "GMT20260312-153000_Recording Review with Dana Lee.vtt").write_text(CLIENT_CALL, encoding="utf-8")
    (folder / "GMT20260313-153000_Team sync.vtt").write_text(INTERNAL_CALL, encoding="utf-8")
    result = intake.import_directory(repo, folder)
    run_id = result["run_id"]
    first = repo.claim(run_id=run_id)
    if how == "failed":
        repo.fail(first, "Unreadable file")
    else:
        with repo.connection() as conn:
            conn.execute("UPDATE pipeline_jobs SET attempt_count=%s,lease_expires_at=now()-interval '1 second' WHERE job_id=%s",
                         (policy.MAX_ATTEMPTS, first["job_id"]))
        assert [r["outcome"] for r in recover_expired(repo)] == ["failed"]
    assert rows(repo, "SELECT status FROM pipeline_runs WHERE run_id=%s", run_id)[0]["status"] == "running"
    run_until_idle(repo, redis)
    jobs = {r["job_id"]: r["status"] for r in rows(repo, "SELECT job_id,status FROM pipeline_jobs WHERE run_id=%s", run_id)}
    assert jobs[first["job_id"]] == "failed" and sorted(jobs.values()) == ["completed", "failed"]
    run = rows(repo, "SELECT status,current_message FROM pipeline_runs WHERE run_id=%s", run_id)[0]
    assert run["status"] == "partially_completed" and "normalised" in run["current_message"]
