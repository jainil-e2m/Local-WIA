"""People, exact provider addresses, shared-role history and account-team membership."""
from datetime import date, datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.db.base import Base, IdMixin, TimestampMixin, utcnow

INTERNAL_KINDS = frozenset({"staff", "contractor", "former", "shared_mailbox", "service_account"})
PERSON_KINDS = INTERNAL_KINDS | {"client_contact", "partner", "prospect", "programme_member", "unknown"}
FUNCTIONS = frozenset({"leadership", "operations", "support", "client_communication", "review", "ads_google",
    "ads_meta", "landing_page_feedback", "leadlock_copy", "leadlock_technical", "creative",
    "bot"})  # "bot" only on service accounts that are chat bots: they resolve to party "bot"
TEAM_ROLES = frozenset({"owner", "ads_google", "ads_meta", "copy", "technical", "creative", "operations"})
ADDRESS_KINDS = frozenset({"email", "slack_user", "clickup_user", "fathom_email", "display_name"})
PARTIES = frozenset({"internal", "shared_mailbox", "client", "partner", "automated", "bot", "unknown"})
RESOLUTION_BASES = frozenset({"provider_id", "email", "client_contact", "client_domain", "partner_rule",
                             "automated", "display_name", "admin"})


def sql_values(values):
    return "(" + ",".join(repr(v) for v in sorted(values)) + ")"


class Person(IdMixin, TimestampMixin, Base):
    __tablename__ = "people"
    name: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(20))
    business_id: Mapped[UUID | None] = mapped_column(ForeignKey("businesses.id"))
    functions: Mapped[list] = mapped_column(JSONB, default=list)
    status: Mapped[str] = mapped_column(String(20), default="confirmed")
    merged_into_id: Mapped[UUID | None] = mapped_column(ForeignKey("people.id"))
    notes: Mapped[str | None] = mapped_column(String(500))
    revision: Mapped[int] = mapped_column(Integer, default=1)
    __table_args__ = (
        CheckConstraint(f"kind IN {sql_values(PERSON_KINDS)}", name="kind"),
        CheckConstraint("status IN ('confirmed','pending')", name="status"),
        CheckConstraint("merged_into_id IS NULL OR merged_into_id <> id", name="not_self_merged"),
    )

    @property
    def is_internal(self):
        return self.kind in INTERNAL_KINDS


class PersonAddress(IdMixin, Base):
    __tablename__ = "person_addresses"
    person_id: Mapped[UUID] = mapped_column(ForeignKey("people.id"), index=True)
    kind: Mapped[str] = mapped_column(String(20))
    value: Mapped[str] = mapped_column(String(320))
    source: Mapped[str] = mapped_column(String(30), default="admin")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    __table_args__ = (
        UniqueConstraint("kind", "value"),
        CheckConstraint(f"kind IN {sql_values(ADDRESS_KINDS)}", name="kind"),
        CheckConstraint("source IN ('roster','admin','client_contact')", name="source"),
    )


class MailboxHolder(IdMixin, Base):
    __tablename__ = "mailbox_holders"
    mailbox_person_id: Mapped[UUID] = mapped_column(ForeignKey("people.id"), index=True)
    holder_person_id: Mapped[UUID] = mapped_column(ForeignKey("people.id"))
    valid_from: Mapped[date | None] = mapped_column(Date)
    valid_to: Mapped[date | None] = mapped_column(Date)
    note: Mapped[str | None] = mapped_column(String(500))
    __table_args__ = (CheckConstraint("valid_from IS NULL OR valid_to IS NULL OR valid_from <= valid_to", name="date_order"),)


class AccountTeamMember(IdMixin, TimestampMixin, Base):
    __tablename__ = "account_team_members"
    business_id: Mapped[UUID] = mapped_column(ForeignKey("businesses.id"), index=True)
    person_id: Mapped[UUID] = mapped_column(ForeignKey("people.id"))
    role: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(20), default="suggested")
    source: Mapped[str] = mapped_column(String(30))
    evidence: Mapped[dict] = mapped_column(JSONB, default=dict)
    started_on: Mapped[date | None] = mapped_column(Date)
    ended_on: Mapped[date | None] = mapped_column(Date)
    confirmed_by: Mapped[str | None] = mapped_column(String(200))
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revision: Mapped[int] = mapped_column(Integer, default=1)
    __table_args__ = (
        CheckConstraint(f"role IN {sql_values(TEAM_ROLES)}", name="role"),
        CheckConstraint("status IN ('suggested','confirmed','ended')", name="status"),
        CheckConstraint("source IN ('clickup_assignments','admin','roster_file')", name="source"),
        CheckConstraint("started_on IS NULL OR ended_on IS NULL OR started_on <= ended_on", name="date_order"),
        Index("uq_account_team_active", "business_id", "role", "person_id", unique=True,
              postgresql_where=text("status <> 'ended'")),
        Index("uq_account_team_confirmed_owner", "business_id", unique=True,
              postgresql_where=text("role = 'owner' AND status = 'confirmed'")),
    )
