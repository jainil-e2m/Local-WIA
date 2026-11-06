"""Durable synchronization state. No credentials or raw provider payloads."""
from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.db.base import Base, IdMixin, TimestampMixin, utcnow


class SyncStream(IdMixin, TimestampMixin, Base):
    __tablename__ = "sync_streams"
    connector_account_id: Mapped[UUID] = mapped_column(ForeignKey("connector_accounts.id"), index=True)
    # Drive streams are account-wide, routed to all approved folder memberships.
    stream_key: Mapped[str] = mapped_column(String(320))
    scope_id: Mapped[UUID] = mapped_column(ForeignKey("source_scopes.id"))
    cursor: Mapped[dict] = mapped_column(JSONB, default=dict)
    generation: Mapped[int] = mapped_column(Integer, default=1)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    next_sync_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    next_reconcile_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_incremental_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_reconciled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (UniqueConstraint("connector_account_id", "stream_key"),)


class ScopeMembership(IdMixin, Base):
    __tablename__ = "scope_memberships"
    record_id: Mapped[UUID] = mapped_column(ForeignKey("source_records.id"), index=True)
    scope_id: Mapped[UUID] = mapped_column(ForeignKey("source_scopes.id"), index=True)
    state: Mapped[str] = mapped_column(String(20), default="active")
    seen_run_id: Mapped[UUID | None] = mapped_column(ForeignKey("sync_runs.id"))
    __table_args__ = (UniqueConstraint("record_id", "scope_id"),)


class DriveNode(IdMixin, Base):
    __tablename__ = "drive_nodes"
    connector_account_id: Mapped[UUID] = mapped_column(ForeignKey("connector_accounts.id"))
    external_id: Mapped[str] = mapped_column(String(300))
    parents: Mapped[list] = mapped_column(JSONB, default=list)
    is_folder: Mapped[bool] = mapped_column(Boolean, default=False)
    name: Mapped[str] = mapped_column(String(500), default="")
    __table_args__ = (UniqueConstraint("connector_account_id", "external_id"),)


class AssociationReview(IdMixin, TimestampMixin, Base):
    __tablename__ = "association_reviews"
    record_id: Mapped[UUID] = mapped_column(ForeignKey("source_records.id"), index=True)
    version_id: Mapped[UUID] = mapped_column(ForeignKey("source_versions.id"))
    existing_business_ids: Mapped[list] = mapped_column(JSONB)
    proposed_business_ids: Mapped[list] = mapped_column(JSONB)
    reason: Mapped[str] = mapped_column(String(60))
    state: Mapped[str] = mapped_column(String(20), default="pending")
    __table_args__ = (Index("uq_association_review_pending", "record_id", unique=True,
                           postgresql_where=text("state = 'pending'")),)


class WebhookReceipt(IdMixin, Base):
    __tablename__ = "webhook_receipts"
    connector_account_id: Mapped[UUID] = mapped_column(ForeignKey("connector_accounts.id"))
    delivery_id: Mapped[str] = mapped_column(String(200))
    content_hash: Mapped[str] = mapped_column(String(64))
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    run_id: Mapped[UUID | None] = mapped_column(ForeignKey("sync_runs.id"))
    __table_args__ = (UniqueConstraint("connector_account_id", "delivery_id"),)


class RecordChange(IdMixin, Base):
    """Transactional outbox for future reducers/briefs; revision fences publication."""
    __tablename__ = "record_changes"
    record_id: Mapped[UUID] = mapped_column(ForeignKey("source_records.id"), index=True)
    revision: Mapped[int] = mapped_column(Integer)
    version_id: Mapped[UUID | None] = mapped_column(ForeignKey("source_versions.id"))
    availability: Mapped[str] = mapped_column(String(30))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    __table_args__ = (UniqueConstraint("record_id", "revision"),)
