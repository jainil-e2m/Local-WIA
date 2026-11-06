"""Where a job runs and for how long (plan 0.B5, R35): one place that names the queue and the timeout of every stage.

Queues (plan 0.B5): `interactive` for the briefs, packs and card refreshes a person is waiting on, `default` for the weekly cycle,
`bulk` for backfill, re-embedding and evaluation, `intake` and `media` for the intake connectors. Every job is a row in
`pipeline_jobs` first; the row carries its queue, and the dispatcher puts it on that queue after the row is committed.
"""
from __future__ import annotations

INTERACTIVE, DEFAULT, BULK, INTAKE, MEDIA = "interactive", "default", "bulk", "intake", "media"
QUEUES = (INTERACTIVE, DEFAULT, BULK, INTAKE, MEDIA)
EDITORIAL_QUEUES = (INTERACTIVE, DEFAULT, BULK)
INTAKE_QUEUES = (INTAKE, MEDIA)

# The run scope of the jobs the intake connectors own (their handlers live in intake/runtime.py).
INTAKE_SCOPE = "source_intake"

BRIEF_STAGES = ("brief_prepare", "brief_research", "brief_context", "brief_writing", "brief_validation")

# A stage with a longer (or shorter) budget than the default, in seconds. RQ kills the work horse past it; the SQL row
# then shows an expired lease and the reconcile loop decides (jobs/recover.py).
DEFAULT_TIMEOUT = 1800
TIMEOUTS = {
    "moment_extraction": 3600,
    "angle_generation": 3600,
    "angle_refinement": 3600,
    "brief_research": 2400,
    "brief_writing": 2400,
    "transcript_chunk_embedding": 3600,
    "moment_embedding": 3600,
    "topic_assignment": 3600,
    "intake_extract": 3600,
    "history_context": 600,
    "angle_matching": 600,
    "angle_initial_assessment": 600,
    "angle_final_assessment": 600,
    "brief_prepare": 300,
    # Gate 1's refresh with feedback (3.B7): one card-sized call and its one repair.
    "card_refresh": 900,
    "brief_validation": 300,
    # The scheduled knowledge-base benchmark (L.B11): up to twelve strategist calls, each allowed 15 minutes.
    "evaluation_run": 3 * 3600,
}

# Stages whose paid answer is never retried automatically after a lost lease: a lost embedding response needs the
# archived attempt inspected first (the intake rule, kept).
NEVER_AUTO_RETRY = frozenset({"transcript_chunk_embedding", "moment_embedding", "topic_assignment"})

# How many attempts a job may use before a lost lease fails it instead of queueing it again.
MAX_ATTEMPTS = 3

# Runs with one job per document (an import's normalisation, 1.B4; a document extraction run, 2.B2), and what a finished
# job did to its document. Such a run is as finished as its jobs: a failed document fails its own job, never the run, so
# the other documents are still claimed (moments.queue.settle_run).
PER_DOCUMENT_SCOPES = {"document_intake": "normalised", "document_extraction": "extracted"}


def timeout_for(stage: str) -> int:
    return TIMEOUTS.get(stage, DEFAULT_TIMEOUT)


def queue_for(stage: str, *, intake: bool = False) -> str:
    """The queue a stage runs on. `intake` marks the intake connectors' own chunk embedding."""
    if stage in {"intake_slack", "intake_fathom"}:
        return INTAKE
    if stage == "intake_extract":
        return MEDIA
    if stage == "transcript_chunk_embedding":
        return INTAKE if intake else BULK
    if stage in BRIEF_STAGES or stage.startswith("pack_") or stage == "card_refresh":
        return INTERACTIVE
    if stage in {"evaluation_run", "document_normalise", "moment_embedding", "topic_assignment"}:
        return BULK
    return DEFAULT


def placement(stage: str, *, intake: bool = False) -> dict:
    """The columns a new job row carries: the executor and its queue."""
    return {"executor": "rq", "queue": queue_for(stage, intake=intake)}
