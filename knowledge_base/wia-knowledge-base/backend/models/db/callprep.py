"""Call preparation: a person's corrections to a call, the brief versions, the editable call-type skills, and the
ad-platform figures read by the ads scripts (services/ads)."""
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (BigInteger, Boolean, CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, Numeric,
                        String, Text, UniqueConstraint)
from sqlalchemy import text as sql_text  # `text` is also a CallSkill column
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.db.base import Base, IdMixin, utcnow


class CallOverride(Base):
    """What a person set on one calendar event: its type, client, host, or that it isn't a client call."""
    __tablename__ = "call_overrides"
    record_id: Mapped[UUID] = mapped_column(ForeignKey("source_records.id"), primary_key=True)
    call_type: Mapped[str | None] = mapped_column(String(40))
    business_id: Mapped[UUID | None] = mapped_column(ForeignKey("businesses.id"))
    host: Mapped[str | None] = mapped_column(String(200))
    excluded: Mapped[bool | None] = mapped_column(Boolean)  # true: not a client call; false: include despite not_if
    note: Mapped[str | None] = mapped_column(Text)
    set_by: Mapped[str] = mapped_column(String(200))
    set_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class CallBrief(IdMixin, Base):
    """One built version of a call's brief. `facts` is what the model saw; the screen shows live facts beside it.
    Not applicable (cancelled) and Changed since built are derived on read, never stored."""
    __tablename__ = "call_briefs"
    record_id: Mapped[UUID] = mapped_column(ForeignKey("source_records.id"))
    version: Mapped[int] = mapped_column(Integer)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False)
    skill_key: Mapped[str] = mapped_column(String(40))
    skill_ref: Mapped[str] = mapped_column(String(80))
    instructions: Mapped[str | None] = mapped_column(Text)
    fingerprint: Mapped[str] = mapped_column(String(64))
    inputs: Mapped[dict] = mapped_column(JSONB, default=dict)
    facts: Mapped[dict] = mapped_column(JSONB, default=dict)
    output: Mapped[dict | None] = mapped_column(JSONB)
    refs: Mapped[dict] = mapped_column(JSONB, default=dict)
    checks: Mapped[dict] = mapped_column(JSONB, default=dict)
    ai_run_id: Mapped[UUID | None] = mapped_column(ForeignKey("ai_runs.id"))
    trigger: Mapped[str] = mapped_column(String(20))  # first | final | regenerate | skill_changed
    built_by: Mapped[str] = mapped_column(String(200))
    outcome: Mapped[str] = mapped_column(String(20))  # ready | rejected
    built_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    __table_args__ = (
        UniqueConstraint("record_id", "version", name="uq_call_briefs_record_id"),
        CheckConstraint("outcome IN ('ready','rejected')", name="outcome"),
        Index("uq_call_briefs_current", "record_id", unique=True, postgresql_where=sql_text("is_current")),
    )


class CallSkill(IdMixin, Base):
    """A version of a call-type skill file. Seeded from services/callprep/skills; edits in the app add versions."""
    __tablename__ = "call_skills"
    key: Mapped[str] = mapped_column(String(40))
    version: Mapped[int] = mapped_column(Integer)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False)
    text: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(10))  # seed | edit
    seed_sha: Mapped[str | None] = mapped_column(String(64))
    edited_by: Mapped[str] = mapped_column(String(200))
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    __table_args__ = (
        UniqueConstraint("key", "version", name="uq_call_skills_key"),
        CheckConstraint("source IN ('seed','edit')", name="source"),
        Index("uq_call_skills_current", "key", unique=True, postgresql_where=sql_text("is_current")),
    )


class AdAccount(IdMixin, Base):
    """A Google Ads or Meta ad account the scripts can see. Figures are read only once it is mapped to a client."""
    __tablename__ = "ad_accounts"
    provider: Mapped[str] = mapped_column(String(20))  # google_ads | meta
    account_id: Mapped[str] = mapped_column(String(40))
    name: Mapped[str] = mapped_column(String(300))
    currency: Mapped[str | None] = mapped_column(String(3))
    status: Mapped[str | None] = mapped_column(String(40))
    via: Mapped[str | None] = mapped_column(String(120))  # the MCC, or which Meta token sees it
    business_id: Mapped[UUID | None] = mapped_column(ForeignKey("businesses.id"), index=True)
    mapped_by: Mapped[str | None] = mapped_column(String(200))
    mapped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    discovered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_pulled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    pulled_from: Mapped[date | None] = mapped_column(Date)
    last_error: Mapped[str | None] = mapped_column(Text)
    __table_args__ = (
        UniqueConstraint("provider", "account_id", name="uq_ad_accounts_provider"),
        CheckConstraint("provider IN ('google_ads','meta')", name="provider"),
    )


class AdDaily(Base):
    """One campaign's figures for one day. `conversions` = Google's primary conversions, Meta's lead actions."""
    __tablename__ = "ad_daily"
    ad_account_id: Mapped[UUID] = mapped_column(ForeignKey("ad_accounts.id", ondelete="CASCADE"), primary_key=True)
    campaign_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    day: Mapped[date] = mapped_column(Date, primary_key=True, index=True)
    campaign_name: Mapped[str] = mapped_column(String(300))
    channel: Mapped[str] = mapped_column(String(40))
    spend: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    impressions: Mapped[int] = mapped_column(BigInteger)
    clicks: Mapped[int] = mapped_column(BigInteger)
    conversions: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    extra: Mapped[dict] = mapped_column(JSONB, default=dict)  # link clicks, landing page views, budget-lost share
    pulled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
