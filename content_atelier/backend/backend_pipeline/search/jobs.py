"""The queue stages Phase 2's search side owns (plan 2.B5, 2.B7), dispatched from `SQLWorker.execute`."""
from __future__ import annotations

STAGES = frozenset({"moment_embedding", "topic_assignment"})


def execute(worker, job) -> None:
    if job["stage"] == "moment_embedding":
        from ..moments.embedding import execute as run
    elif job["stage"] == "topic_assignment":
        from ..moments.topics import execute as run
    else:
        raise ValueError(f"Not a search stage: {job['stage']}")
    run(worker, job)
