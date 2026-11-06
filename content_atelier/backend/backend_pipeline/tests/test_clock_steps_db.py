"""The database clock can step back between two transactions (database.CLOCK_STEP_SECONDS): a WSL2 host's virtual machine
resynchronises its clock by up to 0.6 s every 30 s, so a row written after another can carry an earlier now(). What a
person reads in order, and what decides whether a paid call is sent again, does not depend on that clock moving forward.

Each test stands in for a step by moving an earlier row a minute into the future: the next row's now() is then behind it.
"""
from __future__ import annotations

from backend_pipeline.gates.decisions import record
from backend_pipeline.jobs.recover import recover_expired
from backend_pipeline.tests.platform_db import platform_setup, platform_url  # noqa: F401 (fixtures)

WEEK1, WEEK2 = "week_2026-06-01", "week_2026-06-08"


def test_a_run_queued_after_a_clock_step_is_still_the_latest_run(platform_setup):  # noqa: F811
    repo, _, _ = platform_setup
    first = repo.submit(WEEK1, "synthetic")
    with repo.connection() as conn:
        conn.execute("UPDATE pipeline_runs SET created_at=now()+interval '1 minute' WHERE run_id=%s", (first["run_id"],))
    second = repo.submit(WEEK2, "synthetic")
    with repo.connection() as conn:
        order = [r["run_id"] for r in conn.execute(
            "SELECT run_id FROM pipeline_runs WHERE run_id=ANY(%s) ORDER BY created_at", ([first["run_id"], second["run_id"]],))]
    # The week's history (matching.history) admits the runs created before this one; Gate 2 shows a card's latest run.
    assert order == [first["run_id"], second["run_id"]]


def test_a_decision_after_a_clock_step_is_the_items_current_one_and_the_audit_keeps_its_order(platform_setup):  # noqa: F811
    repo, _, _ = platform_setup
    decide = dict(item_kind="considered_idea", week_id=WEEK1, action="disposition", actor="tester", author="Tester")
    with repo.connection() as conn:
        skipped = record(conn, item_id="idea:0", disposition="skip", **decide)
        conn.execute("UPDATE decisions SET created_at=now()+interval '1 minute' WHERE decision_id=%s", (skipped,))
        conn.commit()
        revived = record(conn, item_id="idea:0", disposition="revive", **decide)
        other = record(conn, item_id="idea:1", disposition="skip", **decide)
        at = {r["decision_id"]: r["created_at"] for r in conn.execute("SELECT decision_id,created_at FROM decisions")}
    assert at[skipped] < at[revived], "the later decision is the item's current disposition"
    assert at[revived] < at[other], "decisions on other items keep the order they were made in"


def test_a_call_dated_before_its_attempt_by_a_clock_step_still_stops_the_job(platform_setup):  # noqa: F811
    """An unsettled call written just after the claim but dated before it is still this attempt's call (0.B5): the job
    fails for a person to retry instead of being queued again, which would send (and pay for) the request twice."""
    repo, _, _ = platform_setup
    submitted = repo.submit(WEEK1, "synthetic")
    claimed = repo.claim(run_id=submitted["run_id"])
    with repo.connection() as conn:
        conn.execute("""INSERT INTO llm_runs(llm_run_id,stage,model,routing_policy,request_fingerprint,status,created_at)
            VALUES ('llm_stepped','moment_extraction','m','p','fp-stepped','sent',%s::timestamptz-interval '1 second')""",
                     (claimed["started_at"],))
        conn.execute("UPDATE pipeline_jobs SET lease_expires_at=now()-interval '1 second' WHERE job_id=%s", (claimed["job_id"],))
    [result] = recover_expired(repo)
    assert result["outcome"] == "failed" and "not saved" in result["message"]
