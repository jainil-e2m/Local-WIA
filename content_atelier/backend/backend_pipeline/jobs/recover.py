"""A job whose worker is gone (plan 0.B5, 0.B6, R35): decide, once, whether it is run again or left for a person.

A job `running` past its lease has an uncertain outcome. The rule the plan sets for paid work is that it is not run
again after a lost lease unless a saved response can be replayed:

* a call the job reserved but never settled leaves an `llm_runs` row still `sent`. If the retry is certain to take a
  saved answer for that exact request without calling (a validated artifact: the weekly stage cache, or the brief and
  pack response caches, which the stage reads before it sends anything), it is queued again and pays nothing; the
  orphaned row is closed. Otherwise the answer may exist on the provider's side and a second request would pay for it
  again, so the job fails with a message and an explicit retry decides. A received output that was never validated
  does not count: the stages other than extraction never replay one, and extraction replays it only when it passes
  today's validator, which is often why the job was retried in the first place;
* a job with no such call (a crash before any request, a free stage, a replayed one) is queued again, up to
  `MAX_ATTEMPTS`;
* a chunk-embedding job is never queued again automatically (the intake rule): its archived attempt is inspected first.
"""
from __future__ import annotations

import logging

from ..artifacts import store_for
from ..database import CLOCK_STEP_SECONDS
from ..store import JsonStore
from . import policy

log = logging.getLogger(__name__)

LOST = "Worker lease expired; review artifacts and explicitly retry"
# What the app shows first for a job left failed (R50): the cycle, the card's brief panel and Gate 2 show a job's error.
STOPPED = ("The worker stopped while this step was running{why}, so it is not run again by itself. Retry this step to run it "
           "again.\n")


def unresolved_calls(conn, job) -> list[dict]:
    """The model calls this attempt reserved and never settled (`llm_runs` rows still `sent`, created since it started).

    A planned row carries its run only after the call settles, so an orphan cannot be tied to its job more exactly than by
    time; a call another worker has in flight at that moment is counted too. That errs toward failing a recoverable job
    (a person retries it), never toward paying twice. For the same reason the window opens a few seconds before the attempt
    started: both times are the database's clock in separate transactions, and a clock stepped back between the claim and
    the call would date the call before its own attempt and queue the job again (database.CLOCK_STEP_SECONDS)."""
    since = job.get("started_at") or job.get("created_at")
    return conn.execute(
        """SELECT llm_run_id,stage,request_fingerprint FROM llm_runs
           WHERE status='sent' AND created_at>=%s::timestamptz-%s*interval '1 second' ORDER BY created_at,llm_run_id""",
        (since, CLOCK_STEP_SECONDS)).fetchall()


# The response caches of the brief and pack calls (llm/workflow.py, Flow.cache): a validated answer per fingerprint.
# The progress line of a job put back on the queue (it said "Processing" until a new worker took it).
QUEUED_AGAIN = "Waiting to run again: its worker stopped before it finished"
RETRY_REQUESTED = "Waiting to run again: a person asked for a retry"
WORKFLOW_CACHES = ("brief-cache", "pack-cache")


def _replayable(store: JsonStore, fingerprint: str | None) -> bool:
    """True only when the retry takes a validated answer for this exact request before it would send one: the weekly
    stage cache (`StageCaller.call_json` reads `find_artifact` first) or a brief or pack response cache (`workflow.chat`).
    A saved received output is not enough (module docstring)."""
    if not fingerprint:
        return False
    if store.find_artifact(fingerprint):
        return True
    return any(store.exists(f"{cache}/{fingerprint}.json") for cache in WORKFLOW_CACHES)



def recover_expired(repo, *, run_id: str | None = None) -> list[dict]:
    """Settle every job whose lease has run out. Returns what was done, one entry per job."""
    store = store_for(repo.settings)
    done = []
    with repo.connection() as conn:
        expired = conn.execute(
            """SELECT j.*,r.run_scope FROM pipeline_jobs j JOIN pipeline_runs r USING(run_id)
               WHERE j.status='running' AND j.lease_expires_at<now() AND (%s::text IS NULL OR j.run_id=%s)
               ORDER BY j.created_at FOR UPDATE OF j SKIP LOCKED""", (run_id, run_id)).fetchall()
        for job in expired:
            orphans = unresolved_calls(conn, job)
            lost = [c for c in orphans if not _replayable(store, c["request_fingerprint"])]
            if job["stage"] in policy.NEVER_AUTO_RETRY:
                outcome, message = "failed", "Intake worker lease expired; embedding retries require review"
            elif lost:
                outcome = "failed"
                message = (STOPPED.format(why=", after it sent a model call whose answer was not saved (it may already have "
                                              "been paid for)")
                           + f"{LOST} ({len(lost)} model call(s) were sent and not settled; their answers were not saved)")
            elif job["attempt_count"] >= policy.MAX_ATTEMPTS:
                outcome, message = "failed", STOPPED.format(why=" on its last allowed attempt") + f"{LOST} (attempt limit reached)"
            else:
                outcome, message = "queued", "Worker lease expired; queued again (no unsettled model call)"
            for call in orphans:
                conn.execute("""UPDATE llm_runs SET status='failed',error=%s WHERE llm_run_id=%s AND status='sent'""",
                             ("Orphaned: the worker was lost before the answer was settled"
                              + ("; the saved answer is replayed on retry" if _replayable(store, call["request_fingerprint"]) else ""),
                              call["llm_run_id"]))
            # The progress line said "Processing" until now; a person reading the queue sees what happened instead (N1 shakedown).
            progress = QUEUED_AGAIN if outcome == "queued" else "Stopped: its worker was lost"
            conn.execute("""UPDATE pipeline_jobs SET status=%s,error_summary=%s,current_message=%s,lease_token=NULL,lease_expires_at=NULL,
                finished_at=CASE WHEN %s='failed' THEN now() ELSE NULL END,updated_at=now() WHERE job_id=%s""",
                         (outcome, message if outcome == "failed" else None, progress, outcome, job["job_id"]))
            if job["run_scope"] in policy.PER_DOCUMENT_SCOPES:
                # One document's lost worker must not stop the run's other documents (2.B2): the run is as finished as its jobs.
                from ..moments.queue import settle_run
                settle_run(conn, job["run_id"], done_word=policy.PER_DOCUMENT_SCOPES[job["run_scope"]])
            else:
                conn.execute("UPDATE pipeline_runs SET status=%s,error_summary=%s,updated_at=now() WHERE run_id=%s",
                             ("failed" if outcome == "failed" else "queued", message if outcome == "failed" else None, job["run_id"]))
            if job["run_scope"] == policy.INTAKE_SCOPE and outcome == "failed" and job["stage"] == "transcript_chunk_embedding":
                conn.execute("""UPDATE intake_revisions SET indexing_status='failed',error_summary=%s
                    WHERE revision_id=(SELECT input_refs->>'revision_id' FROM pipeline_runs WHERE run_id=%s)""",
                             (message, job["run_id"]))
            repo.event(conn, job["run_id"], "lease_expired", message, job=job, severity="warning",
                       details={"outcome": outcome, "unsettled_calls": [c["llm_run_id"] for c in orphans]})
            done.append({"job_id": job["job_id"], "stage": job["stage"], "outcome": outcome, "message": message})
    return done
