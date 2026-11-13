"""AI runs (log, cost, validated output) and the action candidates they propose (6 Nov design)."""
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.db.base import Base, IdMixin, utcnow


class AiRun(IdMixin, Base):
    """One skill call (or refusal). `output` is the validated, checked answer; `refs` maps the prompt's short
    references to record/unit ids (never their text: email bodies are not stored)."""
    __tablename__ = "ai_runs"
    skill: Mapped[str] = mapped_column(String(40))
    skill_version: Mapped[str] = mapped_column(String(20))
    model: Mapped[str] = mapped_column(String(100))
    subject_kind: Mapped[str] = mapped_column(String(20))  # meeting | call | email_batch | client
    subject_id: Mapped[str] = mapped_column(String(300))
    business_id: Mapped[UUID | None] = mapped_column(ForeignKey("businesses.id"))
    input_hash: Mapped[str] = mapped_column(String(64))
    state: Mapped[str] = mapped_column(String(20))
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[Decimal] = mapped_column(Numeric(12, 6), default=0)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    error_class: Mapped[str | None] = mapped_column(String(60))
    refs: Mapped[dict] = mapped_column(JSONB, default=dict)
    output: Mapped[dict | None] = mapped_column(JSONB)
    checks: Mapped[dict] = mapped_column(JSONB, default=dict)  # dropped items, clipped blocks, repair
    is_current: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    __table_args__ = (
        CheckConstraint("subject_kind IN ('meeting','call','email_batch','client')", name="subject_kind"),
        CheckConstraint("state IN ('succeeded','failed','refused')", name="state"),
        Index("uq_ai_runs_succeeded_input", "skill", "input_hash", unique=True,
              postgresql_where=text("state = 'succeeded'")),
        Index("uq_ai_runs_current", "skill", "subject_id", unique=True, postgresql_where=text("is_current")),
        Index("ix_ai_runs_created", "created_at"),
    )


class ActionCandidate(IdMixin, Base):
    """A proposed action (new) or a signal on an open one (update). Admins approve or reject new ones (decisions.py)."""
    __tablename__ = "action_candidates"
    run_id: Mapped[UUID] = mapped_column(ForeignKey("ai_runs.id"), index=True)
    business_id: Mapped[UUID | None] = mapped_column(ForeignKey("businesses.id"), index=True)
    kind: Mapped[str] = mapped_column(String(10))  # new | update
    title: Mapped[str] = mapped_column(Text)
    owner_side: Mapped[str | None] = mapped_column(String(10))
    owner_name: Mapped[str | None] = mapped_column(String(200))
    due_date: Mapped[date | None] = mapped_column(Date)
    due_phrase: Mapped[str | None] = mapped_column(String(200))
    signal: Mapped[str | None] = mapped_column(String(20))
    target_action_ref: Mapped[str | None] = mapped_column(String(120))
    quote: Mapped[str] = mapped_column(Text)
    source_record_id: Mapped[UUID | None] = mapped_column(ForeignKey("source_records.id"))
    unit_id: Mapped[UUID | None] = mapped_column(ForeignKey("content_units.id"))
    verified: Mapped[bool] = mapped_column(Boolean)
    status: Mapped[str] = mapped_column(String(20), default="proposed")
    decided_by: Mapped[str | None] = mapped_column(String(200))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    __table_args__ = (
        CheckConstraint("kind IN ('new','update')", name="kind"),
        CheckConstraint("owner_side IS NULL OR owner_side IN ('WIA','Client')", name="owner_side"),
        CheckConstraint("signal IS NULL OR signal IN ('done','progressed','blocked','date_changed')", name="signal"),
        CheckConstraint("status IN ('proposed','approved','rejected','superseded')", name="status"),
    )
