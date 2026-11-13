"""Logical page identity and duplicate publication fences. Uses existing work rows."""
from copy import deepcopy

from sqlalchemy import select

from backend.models.db import WorkItem
from backend.services.shared.errors import IntakeError
from backend.services.shared.hashing import canonical_hash
from backend.workers import queue

PAGE_JOB = "intake.backfill_page"


class PageInvariantError(IntakeError):
    pass


def input_key(run_id, scope_id, generation, checkpoint, executor):
    return canonical_hash([str(run_id), str(scope_id), generation, checkpoint, executor])


def enqueue_page(session, run, executor, lane="bulk"):
    checkpoint = deepcopy(run.checkpoint)
    key = input_key(run.id, run.scope_id, run.generation, checkpoint, executor)
    signature = f"page:{run.id}:{run.generation}:{key}"
    existing = session.execute(select(WorkItem).where(WorkItem.kind == PAGE_JOB,
        WorkItem.input_signature == signature)).scalar_one_or_none()
    if existing is not None and existing.state == "succeeded":
        raise PageInvariantError("provider checkpoint revisited an already published page")
    payload = {"scope_id": str(run.scope_id), "run_id": str(run.id), "generation": run.generation,
               "checkpoint": checkpoint, "input_key": key, "executor": executor, "page": run.pages}
    if existing is not None and existing.payload != payload:
        raise PageInvariantError("conflicting continuation payload")
    queue.enqueue(session, PAGE_JOB, lane, signature, payload)


def validate(session, item, run, payload, executor):
    """Caller holds the work and run locks. False acknowledges an obsolete job."""
    if item.payload != payload or run is None or payload.get("run_id") != str(run.id) or \
            payload.get("scope_id") != str(run.scope_id):
        raise PageInvariantError("work/run/scope binding mismatch")
    if payload.get("executor") != executor or "input_key" not in payload:
        raise PageInvariantError("legacy or incompatible page job; reconcile the old run")
    generation, checkpoint = payload.get("generation"), payload.get("checkpoint")
    if type(generation) is not int or not isinstance(checkpoint, dict) or payload["input_key"] != input_key(
            run.id, run.scope_id, generation, checkpoint, executor):
        raise PageInvariantError("invalid logical page identity")
    if run.state not in ("running", "queued") or generation < run.generation:
        queue.complete(session, item.id, item.lease_token)
        return False
    if generation > run.generation:
        raise PageInvariantError("page belongs to a future run generation")
    if checkpoint == run.checkpoint:
        return True
    published = session.execute(select(WorkItem.id).where(WorkItem.kind == PAGE_JOB,
        WorkItem.state == "succeeded", WorkItem.id != item.id,
        WorkItem.payload["run_id"].astext == str(run.id),
        WorkItem.payload["input_key"].astext == payload["input_key"])).first()
    if published:
        queue.complete(session, item.id, item.lease_token)
        return False
    raise PageInvariantError("page input differs from the durable run checkpoint")
