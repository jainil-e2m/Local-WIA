"""Source registry, versions and normalised content units (Ingestion design §6)."""
from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.db.base import Base, IdMixin, TimestampMixin, utcnow

PROVIDERS = "('slack','clickup','gmail','drive','calendar','fathom','zoom','leadlock','ghl_billing')"
DOMAINS = (
    "('registry','actions','communications','meetings','profile','support',"
    "'programme','leads','health','finance')"
)


class ConnectorAccount(IdMixin, TimestampMixin, Base):
    """One credential's view of one provider account. Secrets are referenced, never stored."""
    __tablename__ = "connector_accounts"
    provider: Mapped[str] = mapped_column(String(30))
    provider_account_id: Mapped[str] = mapped_column(String(200))
    display_identity: Mapped[str | None] = mapped_column(String(320))
    expected_identity: Mapped[str] = mapped_column(String(320))  # registered; a mismatch blocks the account
    credential_ref: Mapped[str] = mapped_column(String(100))  # env var name only
    credential_owner: Mapped[str | None] = mapped_column(String(200))
    granted_scopes: Mapped[list] = mapped_column(JSONB, default=list)
    state: Mapped[str] = mapped_column(String(20), default="active")
    blocked_reason: Mapped[str | None] = mapped_column(String(200))
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    lease_token: Mapped[UUID | None] = mapped_column()
    lease_work_id: Mapped[UUID | None] = mapped_column()
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_request_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    heavy_request_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        UniqueConstraint("provider", "provider_account_id"),
        CheckConstraint(f"provider IN {PROVIDERS}", name="provider"),
        CheckConstraint("state IN ('active','blocked')", name="state"),
    )


class SourceScope(IdMixin, TimestampMixin, Base):
    """A channel, list, folder, mailbox, calendar or recorder. Only `approved` scopes are ingested."""
    __tablename__ = "source_scopes"
    connector_account_id: Mapped[UUID] = mapped_column(ForeignKey("connector_accounts.id"), index=True)
    kind: Mapped[str] = mapped_column(String(30))
    external_id: Mapped[str] = mapped_column(String(300))
    name: Mapped[str] = mapped_column(String(500))
    parent_name: Mapped[str | None] = mapped_column(String(500))
    state: Mapped[str] = mapped_column(String(20), default="candidate")
    default_domain: Mapped[str] = mapped_column(String(30))
    business_id: Mapped[UUID | None] = mapped_column(ForeignKey("businesses.id"))
    association_mode: Mapped[str] = mapped_column(String(20))
    suggested_business_id: Mapped[UUID | None] = mapped_column(ForeignKey("businesses.id"))
    suggestion_reason: Mapped[str | None] = mapped_column(String(300))
    discovery_stats: Mapped[dict] = mapped_column(JSONB, default=dict)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_by: Mapped[str | None] = mapped_column(String(200))
    last_successful_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revision: Mapped[int] = mapped_column(Integer, default=1)
    __table_args__ = (
        UniqueConstraint("connector_account_id", "kind", "external_id"),
        CheckConstraint("state IN ('candidate','approved','excluded','retired')", name="state"),
        CheckConstraint("association_mode IN ('dedicated','per_record')", name="association_mode"),
        CheckConstraint(
            "association_mode <> 'dedicated' OR state <> 'approved' OR business_id IS NOT NULL",
            name="dedicated_has_business",
        ),
        CheckConstraint(f"default_domain IN {DOMAINS}", name="default_domain"),
    )


class SourceRecord(IdMixin, Base):
    __tablename__ = "source_records"
    connector_account_id: Mapped[UUID] = mapped_column(ForeignKey("connector_accounts.id"))
    scope_id: Mapped[UUID | None] = mapped_column(ForeignKey("source_scopes.id"), index=True)
    record_kind: Mapped[str] = mapped_column(String(40))
    external_id: Mapped[str] = mapped_column(String(300))
    availability: Mapped[str] = mapped_column(String(30), default="available")
    qualification: Mapped[str] = mapped_column(String(20), default="content")
    current_version_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("source_versions.id", use_alter=True, name="fk_source_records_current_version")
    )
    source_url: Mapped[str | None] = mapped_column(Text)
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    admitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revision: Mapped[int] = mapped_column(Integer, default=0)
    provider_state: Mapped[dict] = mapped_column(JSONB, default=dict)
    parent_external_id: Mapped[str | None] = mapped_column(String(300), index=True)
    last_observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        UniqueConstraint("connector_account_id", "record_kind", "external_id"),
        CheckConstraint(
            "availability IN ('available','deleted_upstream','access_lost','out_of_scope')",
            name="availability",
        ),
        CheckConstraint("qualification IN ('content','metadata_only')", name="qualification"),
    )


class SourceVersion(IdMixin, Base):
    """An immutable observed version. Units of old versions stay so old citations resolve."""
    __tablename__ = "source_versions"
    record_id: Mapped[UUID] = mapped_column(ForeignKey("source_records.id"), index=True)
    version_key: Mapped[str] = mapped_column(String(200))
    content_sha256: Mapped[str] = mapped_column(String(64))
    provider_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    parser_version: Mapped[str] = mapped_column(String(40))
    content_state: Mapped[str] = mapped_column(String(20))
    coverage_notes: Mapped[list] = mapped_column(JSONB, default=list)  # unsupported parts, truncation
    attributes: Mapped[dict] = mapped_column(JSONB, default=dict)  # normalised fields, never raw payload
    unit_count: Mapped[int] = mapped_column(Integer, default=0)
    __table_args__ = (
        UniqueConstraint("record_id", "version_key"),
        CheckConstraint(
            "content_state IN ('metadata_only','content','content_pending','unsupported','partial')",
            name="content_state",
        ),
    )


class ContentUnit(IdMixin, Base):
    """Smallest citable piece: a message, transcript segment, doc block or sheet row."""
    __tablename__ = "content_units"
    version_id: Mapped[UUID] = mapped_column(ForeignKey("source_versions.id"))
    ordinal: Mapped[int] = mapped_column(Integer)
    unit_kind: Mapped[str] = mapped_column(String(40))
    locator: Mapped[dict] = mapped_column(JSONB)
    author_identity_id: Mapped[UUID | None] = mapped_column(ForeignKey("provider_identities.id"))
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    text: Mapped[str] = mapped_column(Text)
    text_sha256: Mapped[str] = mapped_column(String(64))
    is_quoted: Mapped[bool] = mapped_column(Boolean, default=False)
    provider_generated: Mapped[bool] = mapped_column(Boolean, default=False)
    domain: Mapped[str] = mapped_column(String(30))
    retention_category: Mapped[str] = mapped_column(String(40), default="temporary_originals")
    retention_state: Mapped[str] = mapped_column(String(20), default="retained")
    __table_args__ = (
        UniqueConstraint("version_id", "ordinal"),
        CheckConstraint(f"domain IN {DOMAINS}", name="domain"),
        CheckConstraint("retention_state IN ('retained','expired')", name="retention_state"),
    )


class ProviderIdentity(IdMixin, Base):
    """A provider author/speaker/assignee/invitee with canonical person and party resolution."""
    __tablename__ = "provider_identities"
    connector_account_id: Mapped[UUID] = mapped_column(ForeignKey("connector_accounts.id"))
    external_key: Mapped[str] = mapped_column(String(320))
    display_name: Mapped[str | None] = mapped_column(String(200))
    email: Mapped[str | None] = mapped_column(String(320))
    is_internal: Mapped[bool | None] = mapped_column(Boolean)
    person_id: Mapped[UUID | None] = mapped_column(ForeignKey("people.id"))
    party: Mapped[str | None] = mapped_column(String(20))
    party_business_id: Mapped[UUID | None] = mapped_column(ForeignKey("businesses.id"))
    resolution_basis: Mapped[str | None] = mapped_column(String(30))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        UniqueConstraint("connector_account_id", "external_key"),
        CheckConstraint("party IS NULL OR party IN ('internal','shared_mailbox','client','partner','automated','bot','unknown')", name="party"),
        CheckConstraint("resolution_basis IS NULL OR resolution_basis IN ('provider_id','email','client_contact','client_domain','partner_rule','automated','display_name','admin')", name="resolution_basis"),
    )


class RecordAssociation(IdMixin, Base):
    """Deterministic record→client links only (rungs 1–2). Everything else stays unresolved."""
    __tablename__ = "record_associations"
    record_id: Mapped[UUID] = mapped_column(ForeignKey("source_records.id"), index=True)
    business_id: Mapped[UUID] = mapped_column(ForeignKey("businesses.id"), index=True)
    basis: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(20), default="associated")
    multi_client: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    __table_args__ = (
        UniqueConstraint("record_id", "business_id"),
        CheckConstraint("basis IN ('scope_mapping','verified_contact','series_mapping','manual_review')", name="basis"),
        CheckConstraint("status IN ('associated','unresolved','rejected')", name="status"),
    )


Index("ix_content_units_version", ContentUnit.version_id)
