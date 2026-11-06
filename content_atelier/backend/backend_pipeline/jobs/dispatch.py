"""Putting committed job rows on their queue (plan 0.B5, R35).

The row is written first, in the transaction that decides the work. Dispatch happens after that commit, and the RQ job
id is the row's idempotency key plus the attempt number, so dispatching the same attempt twice is one RQ job and a new
attempt is a new one. Postgres stays the source of truth: if Redis is flushed or a dispatch is lost, the next
reconcile pass (jobs/scheduler.py) finds the queued row with no live RQ job and puts it back.
"""
from __future__ import annotations

import logging
import os
import re

from . import policy

log = logging.getLogger(__name__)

RUN_JOB = "backend_pipeline.jobs.executor.run_job"
LIVE = {"queued", "started", "deferred", "scheduled"}
READY_SQL = """SELECT j.job_id,j.stage,j.queue,j.idempotency_key,j.attempt_count,j.priority,r.run_scope
    FROM pipeline_jobs j JOIN pipeline_runs r USING(run_id)
    WHERE j.status='queued' AND j.executor IN ('rq','postgres')
      AND (r.run_scope='source_intake' OR r.status IN ('queued','running'))
      AND (%(run)s::text IS NULL OR j.run_id=%(run)s)
      AND NOT EXISTS (SELECT 1 FROM jsonb_array_elements_text(COALESCE(j.progress_details->'dependencies','[]')) dep
                      JOIN pipeline_jobs d ON d.job_id=dep.value WHERE d.status<>'completed')
    ORDER BY j.priority DESC,j.created_at,j.job_id LIMIT %(limit)s"""


def redis_url() -> str | None:
    """The queue's Redis, from `ATELIER_REDIS_URL` (or the older `ATELIER_INTAKE_REDIS_URL`); None when unset."""
    return os.getenv("ATELIER_REDIS_URL") or os.getenv("ATELIER_INTAKE_REDIS_URL") or None


def connect_redis(url: str | None = None):
    from redis import Redis
    url = url or redis_url()
    if not url:
        raise RuntimeError("Redis is not configured; set ATELIER_REDIS_URL")
    return Redis.from_url(url)


def transport_id(job) -> str:
    """The RQ job id: the row's idempotency key (RQ allows letters, digits, underscore and dash) and the attempt number."""
    return re.sub(r"[^A-Za-z0-9_-]", "-", job["idempotency_key"]) + f"-{job['attempt_count']}"


def ready_jobs(conn, run_id: str | None = None, limit: int = 500) -> list[dict]:
    return conn.execute(READY_SQL, {"run": run_id, "limit": limit}).fetchall()


def _live(redis_connection, ident: str) -> bool:
    from rq.exceptions import NoSuchJobError
    from rq.job import Job
    from rq.serializers import JSONSerializer
    try:
        existing = Job.fetch(ident, connection=redis_connection, serializer=JSONSerializer)
    except NoSuchJobError:
        return False
    if existing.get_status(refresh=True) in LIVE:
        return True
    existing.delete()
    return False


def dispatch_ready(repo, redis_connection=None, *, run_id: str | None = None, limit: int = 500) -> list[str]:
    """Enqueue every ready row that has no live RQ job. Returns the ids dispatched."""
    from rq import Queue
    from rq.serializers import JSONSerializer
    redis_connection = redis_connection or connect_redis()
    with repo.connection() as conn:
        rows = ready_jobs(conn, run_id, limit)
    sent = []
    for job in rows:
        ident = transport_id(job)
        if _live(redis_connection, ident):
            continue
        queue = job["queue"] or policy.queue_for(job["stage"], intake=job["run_scope"] == policy.INTAKE_SCOPE)
        Queue(queue, connection=redis_connection, serializer=JSONSerializer).enqueue(
            RUN_JOB, job["job_id"], job_id=ident, job_timeout=policy.timeout_for(job["stage"]),
            result_ttl=3600, failure_ttl=86400)
        with repo.connection() as conn:
            conn.execute("UPDATE pipeline_jobs SET rq_job_id=%s WHERE job_id=%s", (ident, job["job_id"]))
        sent.append(job["job_id"])
    return sent


def kick(repo, *, run_id: str | None = None, connection=None) -> list[str]:
    """Best-effort dispatch right after a commit, so a person is not kept waiting for the next reconcile pass.

    Does nothing when Redis is not configured (tests, a host with no queue), and never raises: the row is already
    committed and the reconcile loop will find it.
    """
    if connection is None and not redis_url():
        return []
    try:
        return dispatch_ready(repo, connection, run_id=run_id)
    except Exception:
        log.exception("Dispatch after commit failed; the reconcile loop will queue the job")
        return []
