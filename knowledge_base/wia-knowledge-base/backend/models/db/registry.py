"""Minimal client registry. Created manually by WIA (FR-INT-01); never from a source event."""
from datetime import date, datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.db.base import Base, IdMixin, TimestampMixin


class Business(IdMixin, TimestampMixin, Base):
    __tablename__ = "businesses"
    name: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(100), unique=True)
    status: Mapped[str] = mapped_column(String(20), default="active")  # inactive = archived: syncing paused
    status_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    lifecycle_stage: Mapped[str | None] = mapped_column(String(30))  # rules pending AR-22
    revision: Mapped[int] = mapped_column(Integer, default=1)
    __table_args__ = (CheckConstraint("status IN ('active','inactive')", name="status"),)


class BusinessAlias(IdMixin, Base):
    """Names used to *suggest* mappings during discovery. Never an automatic match."""
    __tablename__ = "business_aliases"
    business_id: Mapped[UUID] = mapped_column(ForeignKey("businesses.id"), index=True)
    alias: Mapped[str] = mapped_column(String(200))
    __table_args__ = (UniqueConstraint("business_id", "alias"),)


class ServiceEngagement(IdMixin, TimestampMixin, Base):
    __tablename__ = "service_engagements"
    business_id: Mapped[UUID] = mapped_column(ForeignKey("businesses.id"), index=True)
    service: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(20), default="active")
    started_on: Mapped[date | None] = mapped_column(Date)


class Contact(IdMixin, TimestampMixin, Base):
    """A client email or email domain. Only `approved` contacts qualify or associate records."""
    __tablename__ = "contacts"
    business_id: Mapped[UUID] = mapped_column(ForeignKey("businesses.id"), index=True)
    email: Mapped[str | None] = mapped_column(String(320))
    domain: Mapped[str | None] = mapped_column(String(253))
    display_name: Mapped[str | None] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(20), default="candidate")
    origin: Mapped[str] = mapped_column(String(20), default="manual")  # manual | discovery
    revision: Mapped[int] = mapped_column(Integer, default=1)
    __table_args__ = (
        CheckConstraint("(email IS NULL) <> (domain IS NULL)", name="email_xor_domain"),
        CheckConstraint("status IN ('candidate','approved','rejected')", name="status"),
        UniqueConstraint("business_id", "email"),
        UniqueConstraint("business_id", "domain"),
    )


class ClientSourceDecision(IdMixin, Base):
    """An admin's explicit "this source does not apply to this client", so coverage is never silently empty."""
    __tablename__ = "client_source_decisions"
    business_id: Mapped[UUID] = mapped_column(ForeignKey("businesses.id"), index=True)
    provider: Mapped[str] = mapped_column(String(20))
    state: Mapped[str] = mapped_column(String(20), default="not_applicable")
    reason: Mapped[str] = mapped_column(String(300))
    decided_by: Mapped[str] = mapped_column(String(200))
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        CheckConstraint("state IN ('not_applicable')", name="state"),
        UniqueConstraint("business_id", "provider"),
    )


class SenderRule(IdMixin, Base):
    """An admin's ruling on an address or domain across all clients. Team and blocked senders are
    never proposed or associated; a partner (agency, consultant, vendor serving several clients) is
    never a client contact, so its mail is associated only through a client's own contacts or review."""
    __tablename__ = "sender_rules"
    kind: Mapped[str] = mapped_column(String(20))  # team | partner | blocked
    email: Mapped[str | None] = mapped_column(String(320), unique=True)
    domain: Mapped[str | None] = mapped_column(String(253), unique=True)
    reason: Mapped[str] = mapped_column(String(300))
    created_by: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        CheckConstraint("kind IN ('team','partner','blocked')", name="kind"),
        CheckConstraint("(email IS NULL) <> (domain IS NULL)", name="email_xor_domain"),
    )
