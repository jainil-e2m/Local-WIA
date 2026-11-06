"""PostgreSQL-backed work queue (decision D-4: no Redis/RQ).

Correctness lives in `work_items`: enqueue is idempotent on (kind, input_signature),
claims use FOR UPDATE SKIP LOCKED, and a job may only publish while it holds the
live lease token. Moving to RQ later changes transport only (runner.py), not jobs.
"""
from datetime import timedelta
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.models.db import WorkItem


class LeaseLostError(Exception):
    """The worker no longer owns this work item; its result must not be published."""


def db_now(session: Session):
    """Actual PostgreSQL time, evaluated after any row-lock wait."""
    return session.scalar(select(func.clock_timestamp()))


def enqueue(session: Session, kind: str, lane: str, signature: str, payload: dict,
            delay_seconds: float = 0) -> None:
    if len(signature) > 300:
        raise ValueError("work signature exceeds 300 characters")
    now = db_now(session)
    session.execute(
        insert(WorkItem)
        .values(id=uuid4(), kind=kind, lane=lane, input_signature=signature, payload=payload,
                state="pending", attempt=0, next_run_at=now + timedelta(seconds=delay_seconds),
                created_at=now, updated_at=now)
        .on_conflict_do_nothing(index_elements=["kind", "input_signature"])
    )


def claim(session: Session, lanes: list[str]) -> WorkItem | None:
    """Claim one due item. Expired claims (crashed worker) become claimable again."""
    now = db_now(session)
    item = session.execute(
        select(WorkItem)
        .where(WorkItem.lane.in_(lanes))
        .where(
            ((WorkItem.state.in_(("pending", "retry_wait"))) & (WorkItem.next_run_at <= now))
            | ((WorkItem.state == "claimed") & (WorkItem.lease_until < now))
        )
        .order_by(WorkItem.next_run_at, WorkItem.id)
        .limit(1)
        .with_for_update(skip_locked=True)
    ).scalar_one_or_none()
    if item is None:
        return None
    item.state = "claimed"
    item.lease_token = uuid4()
    item.lease_until = db_now(session) + timedelta(seconds=get_settings().lease_seconds)
    return item


def assert_lease(session: Session, work_id: UUID, lease_token: UUID) -> WorkItem:
    """Acquire publication ownership while the lease is live.

    The lock protects the entire transaction even if the deadline subsequently
    passes. Record that proof on this transaction, never on the Session lifetime.
    """
    item = session.execute(
        select(WorkItem).where(WorkItem.id == work_id).with_for_update()
        .execution_options(populate_existing=True)
    ).scalar_one_or_none()
    if item is None or item.state != "claimed" or item.lease_token != lease_token or \
            item.lease_until is None or item.lease_until <= db_now(session):
        raise LeaseLostError(str(work_id))
    session.info.setdefault("publication_leases", {})[(work_id, lease_token)] = (
        session.get_nested_transaction() or session.get_transaction())
    return item


def complete(session: Session, work_id: UUID, lease_token: UUID) -> None:
    """Finish in the caller's publication transaction. Never commits or opens a session."""
    proof = session.info.get("publication_leases", {}).get((work_id, lease_token))
    current_transaction = session.get_nested_transaction() or session.get_transaction()
    if proof is not current_transaction or proof is None:
        item = assert_lease(session, work_id, lease_token)
    else:
        item = session.get(WorkItem, work_id)
    if item.state != "claimed" or item.lease_token != lease_token:
        raise LeaseLostError(str(work_id))
    item.state = "succeeded"
    item.lease_token = item.lease_until = None
    item.last_error_class = item.last_error = None
    item.updated_at = db_now(session)


def renew(session: Session, work_id: UUID, lease_token: UUID) -> bool | None:
    """True=renewed, False=lost, None=temporarily locked by publication.

    Lock before evaluating time: a delayed heartbeat cannot resurrect a lease
    that expired while waiting. SKIP LOCKED avoids contending with publication.
    """
    item = session.execute(select(WorkItem).where(WorkItem.id == work_id)
        .with_for_update(skip_locked=True).execution_options(populate_existing=True)).scalar_one_or_none()
    if item is None:
        return None if session.get(WorkItem, work_id) is not None else False
    now = db_now(session)
    if item.state != "claimed" or item.lease_token != lease_token or \
            item.lease_until is None or item.lease_until <= now:
        return False
    item.lease_until = now + timedelta(seconds=get_settings().lease_seconds)
    return True
