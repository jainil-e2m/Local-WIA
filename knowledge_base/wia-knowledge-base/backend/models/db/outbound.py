"""Per-person connections used to write back to providers under each person's own name (S1, S12)."""
from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.db.base import Base, IdMixin, utcnow


class ClickUpConnection(IdMixin, Base):
    """One person's ClickUp OAuth grant. The token is stored encrypted (KB_SECRET_KEY) and is only ever
    used for that person's own edits; there is no fallback identity (decided 29 Oct)."""
    __tablename__ = "clickup_connections"
    person_id: Mapped[UUID] = mapped_column(ForeignKey("people.id"), index=True)
    clickup_user_id: Mapped[str] = mapped_column(String(40))
    clickup_username: Mapped[str | None] = mapped_column(String(200))
    workspace_ids: Mapped[list] = mapped_column(JSONB, default=list)
    token_encrypted: Mapped[str] = mapped_column(Text)
    connected_by: Mapped[str] = mapped_column(String(200))
    connected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_reason: Mapped[str | None] = mapped_column(String(200))
    __table_args__ = (
        Index("uq_clickup_connections_active_person", "person_id", unique=True,
              postgresql_where=text("revoked_at IS NULL")),
    )


OUTBOUND_KINDS = ("slack_post", "slack_dm", "clickup_task_update")
OUTBOUND_STATES = ("draft", "approved", "sent", "failed", "refused", "rejected", "expired")


class OutboundRequest(IdMixin, Base):
    """The send log. Every outgoing Slack message or ClickUp edit is a request that a listed approver must
    approve, one at a time, before it is sent. The approval is bound to the payload hash, so a changed
    request needs a new approval. Prior values of edited fields are kept so a change can be seen or undone."""
    __tablename__ = "outbound_requests"
    kind: Mapped[str] = mapped_column(String(30))
    target: Mapped[str] = mapped_column(String(100))  # channel ID, Slack user ID, or ClickUp task ID
    payload: Mapped[dict] = mapped_column(JSONB)  # message text, or the fields to set
    payload_hash: Mapped[str] = mapped_column(String(64))
    preview: Mapped[dict] = mapped_column(JSONB, default=dict)  # e.g. list id, old -> new values
    as_person_id: Mapped[UUID | None] = mapped_column(ForeignKey("people.id"))  # whose ClickUp connection
    state: Mapped[str] = mapped_column(String(20), default="draft")
    drafted_by: Mapped[str] = mapped_column(String(200))
    drafted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    approved_by: Mapped[str | None] = mapped_column(String(200))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_hash: Mapped[str | None] = mapped_column(String(64))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    result: Mapped[dict] = mapped_column(JSONB, default=dict)  # provider IDs, confirmed values
    error: Mapped[str | None] = mapped_column(String(500))
    __table_args__ = (
        CheckConstraint("kind IN ('slack_post','slack_dm','clickup_task_update')", name="kind"),
        CheckConstraint("state IN ('draft','approved','sent','failed','refused','rejected','expired')", name="state"),
        Index("ix_outbound_requests_state", "state"),
    )
