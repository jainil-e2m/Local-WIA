"""Durable work, sync runs, cursors, coverage and audit."""
from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.db.base import Base, IdMixin, TimestampMixin, utcnow

COVERAGE_COUNTS = (
    "discovered", "stored_content", "stored_metadata", "unchanged", "excluded",
    "unsupported", "inaccessible", "failed",
)


class SyncRun(IdMixin, Base):
    __tablename__ = "sync_runs"
    connector_account_id: Mapped[UUID] = mapped_column(ForeignKey("connector_accounts.id"))
    scope_id: Mapped[UUID | None] = mapped_column(ForeignKey("source_scopes.id"), index=True)
    mode: Mapped[str] = mapped_column(String(20))
    window_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))  # NULL = full history
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    state: Mapped[str] = mapped_column(String(20), default="running")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    pages: Mapped[int] = mapped_column(Integer, default=0)
    error_class: Mapped[str | None] = mapped_column(String(30))
    stream_id: Mapped[UUID | None] = mapped_column(ForeignKey("sync_streams.id"), index=True)
    generation: Mapped[int] = mapped_column(Integer, default=1)
    checkpoint: Mapped[dict] = mapped_column(JSONB, default=dict)
    target_external_id: Mapped[str | None] = mapped_column(String(300))
    __table_args__ = (
        CheckConstraint("mode IN ('discovery','backfill','incremental','reconcile','refresh')", name="mode"),
        CheckConstraint("state IN ('queued','running','succeeded','partial','failed')", name="state"),
        Index("uq_sync_run_active_stream", "stream_id", unique=True,
              postgresql_where="state = 'running'"),
    )


class CoverageWindow(IdMixin, Base):
    """What one run discovered/stored/missed for one scope. Complete only when every item is accounted for."""
    __tablename__ = "coverage_windows"
    scope_id: Mapped[UUID] = mapped_column(ForeignKey("source_scopes.id"))
    run_id: Mapped[UUID] = mapped_column(ForeignKey("sync_runs.id"))
    window_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    contract_version: Mapped[str] = mapped_column(String(40))
    counts: Mapped[dict] = mapped_column(JSONB, default=lambda: dict.fromkeys(COVERAGE_COUNTS, 0))
    gaps: Mapped[list] = mapped_column(JSONB, default=list)  # [{external_id, reason}] — IDs only
    state: Mapped[str] = mapped_column(String(20), default="open")
    __table_args__ = (
        UniqueConstraint("scope_id", "run_id"),
        CheckConstraint("state IN ('open','complete','partial','failed')", name="state"),
    )


class SyncCursor(IdMixin, Base):
    __tablename__ = "sync_cursors"
    scope_id: Mapped[UUID] = mapped_column(ForeignKey("source_scopes.id"))
    mode: Mapped[str] = mapped_column(String(20))
    cursor: Mapped[str | None] = mapped_column(Text)
    generation: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    __table_args__ = (UniqueConstraint("scope_id", "mode"),)


class WorkItem(IdMixin, TimestampMixin, Base):
    __tablename__ = "work_items"
    kind: Mapped[str] = mapped_column(String(50))
    lane: Mapped[str] = mapped_column(String(20))
    input_signature: Mapped[str] = mapped_column(String(300))
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    state: Mapped[str] = mapped_column(String(20), default="pending")
    attempt: Mapped[int] = mapped_column(Integer, default=0)
    next_run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    lease_token: Mapped[UUID | None] = mapped_column()
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error_class: Mapped[str | None] = mapped_column(String(30))
    last_error: Mapped[str | None] = mapped_column(Text)  # sanitised: class + safe message only
    __table_args__ = (
        UniqueConstraint("kind", "input_signature"),
        CheckConstraint(
            "state IN ('pending','claimed','retry_wait','succeeded','blocked','failed','cancelled')",
            name="state",
        ),
        Index(
            "ix_work_items_due", "lane", "next_run_at",
            postgresql_where="state IN ('pending','retry_wait')",
        ),
    )


class AuditEvent(IdMixin, Base):
    __tablename__ = "audit_events"
    actor: Mapped[str] = mapped_column(String(200))
    action: Mapped[str] = mapped_column(String(100))
    target_type: Mapped[str] = mapped_column(String(50))
    target_id: Mapped[str] = mapped_column(String(100))
    details: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
