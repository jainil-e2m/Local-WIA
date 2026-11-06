"""The one function every queue worker runs (plan 0.B5, R35): `run_job(job_id)`.

The job row says what to do. The handler for its stage lives where it always did (the intake connectors in
`intake/runtime.py`, every editorial, brief and pack stage in `SQLWorker.execute`); this module is the single door in:
claim the row under a lease (exactly one worker wins), run the handler with a heartbeat on the row, record the outcome
on the row, then dispatch whatever the finished stage unblocked. Nothing here decides whether to retry a paid stage;
`jobs/recover.py` does, from the rows and the `llm_runs` record.
"""
from __future__ import annotations

import logging

from . import policy
from .dispatch import kick

log = logging.getLogger(__name__)


def scope_of(repo, job_id: str):
    with repo.connection() as conn:
        return conn.execute("""SELECT j.run_id,j.stage,r.run_scope FROM pipeline_jobs j JOIN pipeline_runs r USING(run_id)
            WHERE j.job_id=%s""", (job_id,)).fetchone()


def _queue_connection():
    """The Redis connection of the RQ job running this function (None when called directly, outside a queue)."""
    from rq import get_current_job
    current = get_current_job()
    return current.connection if current else None


def run_job(job_id, *, storage=None, models=None, provider=None, successors=True):
    """Run one job and return its id, or None when the row is no longer runnable (already running elsewhere, finished,
    its run closed). `provider` is for synthetic databases only (SQLWorker refuses it elsewhere)."""
    from ..repository import ContentRepository
    from ..storage_config import StorageSettings
    storage = storage or StorageSettings.from_env()
    repo = ContentRepository(storage)
    row = scope_of(repo, job_id)
    if row is None:
        log.warning("Job %s is not in the database; nothing to run", job_id)
        return None
    if row["run_scope"] == policy.INTAKE_SCOPE:
        from ..intake import runtime
        runtime.execute(job_id, models=models)
        result = job_id
    else:
        from ..sql_pipeline import SQLWorker
        result = SQLWorker(storage, models, provider=provider).run(job_id)
    if successors:
        kick(repo, run_id=row["run_id"], connection=_queue_connection())
    return result
