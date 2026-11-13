"""LeadLock (white-labelled HighLevel) Marketplace app: one agency grant, one token per client sub-account (S1).

The private app "WIA Client Knowledge Base" is installed once by a LeadLock agency admin across the
sub-accounts. The agency (Company) token is the only long-lived credential; location tokens are minted from
it on demand and never refreshed themselves, so exactly one refresh token rotates. Tokens are stored
encrypted (KB_SECRET_KEY) and never logged.
"""
from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.db.base import Base, IdMixin, TimestampMixin, utcnow


class LeadLockInstallation(IdMixin, TimestampMixin, Base):
    """The agency-level grant from one install. A reinstall replaces the active row."""
    __tablename__ = "leadlock_installations"
    company_id: Mapped[str] = mapped_column(String(64))
    app_id: Mapped[str | None] = mapped_column(String(64))
    installed_by_user_id: Mapped[str | None] = mapped_column(String(64))
    access_token_encrypted: Mapped[str] = mapped_column(Text)
    refresh_token_encrypted: Mapped[str] = mapped_column(Text)
    access_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    scopes: Mapped[list] = mapped_column(JSONB, default=list)
    is_bulk_installation: Mapped[bool | None] = mapped_column(Boolean)
    install_to_future_locations: Mapped[bool | None] = mapped_column(Boolean)
    approve_all_locations: Mapped[bool | None] = mapped_column(Boolean)
    approved_location_ids: Mapped[list] = mapped_column(JSONB, default=list)
    installed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    refreshed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revision: Mapped[int] = mapped_column(Integer, default=1)  # +1 per refresh: shows the rotation happened
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_reason: Mapped[str | None] = mapped_column(String(200))
    __table_args__ = (
        Index("uq_leadlock_installations_active_company", "company_id", unique=True,
              postgresql_where=text("revoked_at IS NULL")),
    )


LOCATION_STATES = ("pending", "active", "uninstalled", "failed")


class LeadLockLocation(IdMixin, TimestampMixin, Base):
    """One client sub-account the app is installed on. Mapping it to a KB client stays an admin step (S2)."""
    __tablename__ = "leadlock_locations"
    installation_id: Mapped[UUID | None] = mapped_column(ForeignKey("leadlock_installations.id"), index=True)
    location_id: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str | None] = mapped_column(String(300))
    state: Mapped[str] = mapped_column(String(20), default="pending")
    access_token_encrypted: Mapped[str | None] = mapped_column(Text)
    access_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    scopes: Mapped[list] = mapped_column(JSONB, default=list)
    installed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    uninstalled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_token_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(String(300))  # sanitised: never a token or a response body
    __table_args__ = (
        CheckConstraint("state IN ('pending','active','uninstalled','failed')", name="state"),
    )


class LeadLockAppEvent(IdMixin, Base):
    """Every verified webhook from the app (install / uninstall), once. Duplicates are acknowledged, not redone."""
    __tablename__ = "leadlock_app_events"
    delivery_key: Mapped[str] = mapped_column(String(200), unique=True)  # webhookId, else the body hash
    event_type: Mapped[str] = mapped_column(String(40))
    company_id: Mapped[str | None] = mapped_column(String(64))
    location_id: Mapped[str | None] = mapped_column(String(64))
    outcome: Mapped[str] = mapped_column(String(60))
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
