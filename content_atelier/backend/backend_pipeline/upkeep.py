"""The archive kept current without a person (Phase N10's autonomy pass; the owner, 25 October 2026: everything is maintained
by the system week after week by itself).

A new call becomes a document, is normalised and its transcript chunks embedded by the intake chain. Its scenes were not
extracted until a person ran `moments extract` or the next cycle read its window, so account memory and the founder-note
picker did not see a call for up to a week. The scheduler now queues, every hour (`jobs/scheduler.py`), the extraction of
every included document no extraction has ever read (`extraction_status` still `pending`, which a new document has after
its normalisation), on the `bulk` queue. Only those: a document read under an earlier scene profile is never re-extracted
here (that stays a deliberate command, `moments extract --all-pending`); the archive's ingestion dates cannot tell new
from old, because the whole archive was ingested in October 2026. The same pass embeds the scenes that have no vector yet (`moments.embedding`, about USD 0.01 for the whole archive), so
search finds a scene by its meaning and not only by its words; topics are not assigned here (only the Moments screen's topic
filter reads them, and each assignment is a chat call).

Both are paid work under their standing weekly budgets (6.B3: extraction, embedding), queued only when the process may make
paid calls (`ATELIER_ALLOW_GENERATION`, `ATELIER_ALLOW_ENCODING`); otherwise the pass says why and queues nothing. Queueing is idempotent by its inputs, so an
hour that finds nothing new queues nothing and a job already waiting is reported, never doubled.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime

log = logging.getLogger(__name__)

ACTOR = "upkeep"


def new_documents(conn, profile: str) -> list[dict]:
    """Documents no extraction has read (still `pending`) that the profile has not queued (moments.queue.pending_documents)."""
    from .moments.queue import pending_documents
    return [d for d in pending_documents(conn, profile) if d["extraction_status"] == "pending"]


def extract_new(repo, models, now: datetime | None = None) -> dict:
    from .moments import queue
    from .settings_store import value
    now = now or datetime.now(UTC)
    if not repo.settings.generation_enabled:
        return {"queued": 0, "skipped": "paid generation is off in this process (ATELIER_ALLOW_GENERATION)"}
    with repo.connection() as conn:
        profile = value("moments.extraction_profile", conn)
        documents = new_documents(conn, profile)
    if not documents:
        return {"queued": 0, "profile": profile}
    result = queue.queue_extraction(repo, models, documents, mode="live", actor=ACTOR, queue="bulk", profile=profile)
    if result.get("run_id"):
        from .jobs.dispatch import kick
        kick(repo, run_id=result["run_id"])
    return {"queued": len(result.get("jobs") or []), "profile": profile, "run_id": result.get("run_id"),
            "already": len(result.get("skipped") or [])}


def embed_new_scenes(repo, models) -> dict:
    from .moments import embedding
    if not repo.settings.encoding_enabled:
        return {"queued": 0, "skipped": "paid encoding is off in this process (ATELIER_ALLOW_ENCODING)"}
    with repo.connection() as conn:
        busy = conn.execute("""SELECT count(*) n FROM pipeline_jobs WHERE stage='moment_extraction'
            AND status IN ('queued','running')""").fetchone()["n"]
    if busy:
        # Both write the scenes' rows; an embedding run beside an extraction deadlocked on the scratch copy (25 October).
        return {"queued": 0, "skipped": f"{busy} scene extraction(s) still running: the scenes are embedded next hour"}
    result = embedding.queue(repo, models, mode="live", actor=ACTOR)
    if result.get("run_id") and result.get("queued"):
        from .jobs.dispatch import kick
        kick(repo, run_id=result["run_id"])
    return {k: result.get(k) for k in ("queued", "run_id", "already_queued") if k in result}


RETRY_LIMIT = 3


def retry_interrupted(repo) -> dict:
    """Retry the upkeep's own scene jobs that a restart stopped (a deploy or a platform move expires the worker's lease, and
    the job then waits for a person: production, 25 October). Only runs this pass started (`triggered_by` upkeep), only
    extraction and embedding (about a cent a call, so a repeated call costs nothing that matters), at most RETRY_LIMIT
    attempts; a job that failed for another reason stays failed and on the alerts."""
    with repo.connection() as conn:
        rows = conn.execute("""SELECT j.job_id FROM pipeline_jobs j JOIN pipeline_runs r USING (run_id)
            WHERE r.triggered_by=%s AND j.status='failed' AND j.stage IN ('moment_extraction','moment_embedding')
            AND j.attempt_count < %s AND j.error_summary ILIKE '%%lease expired%%'""", (ACTOR, RETRY_LIMIT)).fetchall()
    retried = []
    for row in rows:
        repo.retry(row["job_id"], ACTOR)
        retried.append(row["job_id"])
    if retried:
        from .jobs.dispatch import kick
        kick(repo)
    return {"retried": retried}


def hourly(repo, models, now: datetime) -> dict:
    """One upkeep pass. A refused budget or a missing plan is a reason in the result, not a failed hour; one part failing
    never stops the other. A purpose whose weekly budget is used up waits: the first hour after the budget renews (Monday
    00:00 UTC) or is raised queues the same documents, so nothing is lost (production's first pass, 25 October)."""
    from .llm.run_plans import BudgetExhausted
    out = {}
    for name, part in (("interrupted", lambda: retry_interrupted(repo)), ("scenes", lambda: extract_new(repo, models, now)),
                       ("embeddings", lambda: embed_new_scenes(repo, models))):
        try:
            out[name] = part()
        except BudgetExhausted as error:
            log.info("Upkeep %s waits for its budget: %s", name, error)
            out[name] = {"queued": 0, "waiting": f"this week's {error.purpose or name} budget is used up; queued after it renews "
                                                  "or is raised"}
        except (ValueError, LookupError) as error:
            log.warning("Upkeep %s: %s", name, error)
            out[name] = {"queued": 0, "error": f"{type(error).__name__}: {error}"[:300]}
    return out
