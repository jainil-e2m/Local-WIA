"""S5â€“S6: idempotent record/version/unit upsert, provider identities and deterministic associations."""
from dataclasses import dataclass, replace
from uuid import UUID, uuid4

from sqlalchemy import case, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from backend.models.db import (
    AssociationReview,
    RecordChange,
    ContentUnit,
    ProviderIdentity,
    RecordAssociation,
    SourceRecord,
    SourceScope,
    SourceVersion,
)
from backend.models.db.base import utcnow
from backend.models.domain.intake import IdentityRef, IntakeContext, NormalisedRecord
from backend.services.shared.emails import is_internal
from backend.services.shared.hashing import canonical_hash, normalise_text, sha256_text



@dataclass
class PersistOutcome:
    stored_content: int = 0
    stored_metadata: int = 0
    unchanged: int = 0
    stale_observations: int = 0
    known_without_contact: int = 0
    cancellations: int = 0
    association_conflicts: int = 0


def version_key(rec: NormalisedRecord, parser_version: str = "") -> tuple[str, str]:
    attributes = dict(rec.attributes)
    if rec.record_kind == "gmail_message":
        attributes.pop("labels", None)
        attributes.pop("state", None)
    content_hash = canonical_hash({
        "state": rec.content_state, "attributes": attributes, "domain": rec.domain,
        "change_kind": rec.change_kind, "availability": rec.availability,
        "units": [(u.unit_kind, normalise_text(u.text), u.locator, u.is_quoted, u.provider_generated,
                   u.author, u.occurred_at, u.domain) for u in rec.units],
    })
    return canonical_hash([parser_version, content_hash]), content_hash


class IdentityCache:
    def __init__(self, session: Session, connector_account_id: UUID):
        self.session = session
        self.account_id = connector_account_id
        self._ids: dict[str, UUID] = {}
        self._resolver = None

    def resolve(self, ref: IdentityRef | None) -> UUID | None:
        if ref is None or not ref.external_key:
            return None
        key = ref.external_key[:320]
        if key in self._ids:
            return self._ids[key]
        from backend.services.people.resolve import Resolver, resolve_identity
        if self._resolver is None:
            # Roster mutations take Person locks before identity locks. Acquire the
            # resolver's shared locks in that order before this upsert locks an identity.
            self._resolver = Resolver(self.session)
        email = ref.email.lower() if ref.email else None
        stmt = insert(ProviderIdentity).values(
            id=uuid4(), connector_account_id=self.account_id, external_key=key,
            display_name=(ref.display_name or None), email=email,
            is_internal=is_internal(email) if email else None,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["connector_account_id", "external_key"],
            set_={"display_name": func.coalesce(stmt.excluded.display_name, ProviderIdentity.display_name),
                  "email": func.coalesce(stmt.excluded.email, ProviderIdentity.email),
                  "is_internal": case((ProviderIdentity.party.in_(("internal", "shared_mailbox")), True),
                                      (ProviderIdentity.party.is_not(None), False),
                                      else_=stmt.excluded.is_internal)},
        ).returning(ProviderIdentity)
        identity = self.session.execute(stmt.execution_options(populate_existing=True)).scalar_one()
        if identity.person_id is None or identity.party in (None, "unknown"):
            resolve_identity(self.session, identity, self._resolver)
        identity_id = identity.id
        self._ids[key] = identity_id
        return identity_id


def persist_record(session: Session, scope: SourceScope, ctx: IntakeContext, rec: NormalisedRecord,
                   identities: IdentityCache, parser_version: str, outcome: PersistOutcome) -> SourceRecord:
    now = utcnow()
    record = session.execute(select(SourceRecord).where(
        SourceRecord.connector_account_id == scope.connector_account_id,
        SourceRecord.record_kind == rec.record_kind, SourceRecord.external_id == rec.external_id
    ).with_for_update()).scalar_one_or_none()
    if record is None:
        record = SourceRecord(id=uuid4(), connector_account_id=scope.connector_account_id,
            scope_id=scope.id, record_kind=rec.record_kind, external_id=rec.external_id,
            first_seen_at=now, revision=0, provider_state={})
        session.add(record)
    current = session.get(SourceVersion, record.current_version_id) if record.current_version_id else None
    record.last_seen_at = now
    if current and current.provider_updated_at and rec.provider_updated_at and rec.provider_updated_at < current.provider_updated_at:
        outcome.stale_observations += 1
        return record
    if current and record.availability == "deleted_upstream" and rec.availability == "available" and not rec.authoritative and (
            not rec.provider_updated_at or not current.provider_updated_at or rec.provider_updated_at <= current.provider_updated_at):
        outcome.stale_observations += 1
        return record
    old_availability = record.availability
    if record.admitted_at and rec.change_kind == "snapshot" and not ctx.matches([p.email for p in rec.participants if p.email]):
        outcome.known_without_contact += 1
    if rec.admitted and record.admitted_at is None:
        record.admitted_at = now
    record.parent_external_id = rec.parent_external_id or record.parent_external_id
    record.provider_state = {**(record.provider_state or {}), **rec.provider_state}
    # Pure operational patches (e.g. Gmail labels) do not version/extract content.
    if rec.change_kind == "patch" and not rec.attributes and current and rec.availability == record.availability:
        outcome.unchanged += 1
        return record
    carried_units = []
    if rec.change_kind != "snapshot" and current:
        attrs = {**current.attributes, **rec.attributes}
        fields = set(current.attributes.get("_last_known_fields", []))
        fields.update(k for k in current.attributes if k not in rec.attributes and not k.startswith("_"))
        fields.difference_update(rec.attributes)
        attrs["_last_known_fields"] = sorted(fields)
        rec = replace(rec, attributes=attrs, occurred_at=rec.occurred_at or record.occurred_at,
                      source_url=rec.source_url or record.source_url)
    if rec.carry_content and current:
        carried_units = session.execute(select(ContentUnit).where(
            ContentUnit.version_id == current.id).order_by(ContentUnit.ordinal)).scalars().all()
        rec = replace(rec, content_state=current.content_state)
    expired = session.execute(select(ContentUnit.id).join(SourceVersion).where(
        SourceVersion.record_id == record.id, ContentUnit.retention_state == "expired").limit(1)).first()
    if expired and rec.units:
        rec = replace(rec, units=[], content_state="metadata_only",
                      coverage_notes=[*rec.coverage_notes, "retention: text refetch suppressed"])
    record.availability = rec.availability
    record.qualification = "metadata_only" if rec.content_state == "metadata_only" else "content"
    record.source_url, record.occurred_at = rec.source_url, rec.occurred_at
    record.last_observed_at = now
    key, content_hash = version_key(rec, parser_version)
    if carried_units:
        key = canonical_hash([key, [(u.text_sha256, u.retention_state) for u in carried_units]])
    if current and current.version_key == key:
        outcome.unchanged += 1
        _associate(session, scope, ctx, record, rec, outcome)
        return record
    existing = session.execute(select(SourceVersion).where(
        SourceVersion.record_id == record.id, SourceVersion.version_key == key)).scalar_one_or_none()
    if existing:
        version = existing
    else:
        version = SourceVersion(id=uuid4(), record_id=record.id, version_key=key,
            content_sha256=content_hash, provider_updated_at=rec.provider_updated_at or
            (current.provider_updated_at if current and rec.change_kind != "snapshot" else None),
            observed_at=now, parser_version=parser_version, content_state=rec.content_state,
            coverage_notes=rec.coverage_notes, attributes=rec.attributes,
            unit_count=len(rec.units) + len(carried_units))
        session.add(version)
        session.flush([record, version])
        for ordinal, unit in enumerate(rec.units):
            value = normalise_text(unit.text)
            session.add(ContentUnit(id=uuid4(), version_id=version.id, ordinal=ordinal,
                unit_kind=unit.unit_kind, locator=unit.locator, author_identity_id=identities.resolve(unit.author),
                occurred_at=unit.occurred_at, text=value, text_sha256=sha256_text(value),
                is_quoted=unit.is_quoted, provider_generated=unit.provider_generated,
                domain=unit.domain or rec.domain or scope.default_domain))
        for ordinal, unit in enumerate(carried_units, start=len(rec.units)):
            session.add(ContentUnit(id=uuid4(), version_id=version.id, ordinal=ordinal,
                **{k: getattr(unit, k) for k in ("unit_kind", "locator", "author_identity_id", "occurred_at",
                    "text", "text_sha256", "is_quoted", "provider_generated", "domain", "retention_category", "retention_state")}))
    record.current_version_id = version.id
    record.revision += 1
    session.add(RecordChange(id=uuid4(), record_id=record.id, revision=record.revision,
                            version_id=version.id, availability=record.availability))
    if record.qualification == "content":
        outcome.stored_content += 1
    else:
        outcome.stored_metadata += 1
    if rec.attributes.get("status") == "cancelled" and old_availability != "deleted_upstream":
        outcome.cancellations += 1
    for ref in rec.participants:
        identities.resolve(ref)
    _associate(session, scope, ctx, record, rec, outcome)
    return record


def _associate(session, scope, ctx, record, rec, outcome):
    if not record.admitted_at:
        return
    existing = set(session.execute(select(RecordAssociation.business_id).where(
        RecordAssociation.record_id == record.id, RecordAssociation.status == "associated")).scalars())
    basis = "verified_contact"
    if scope.association_mode == "dedicated" and scope.business_id:
        matches, basis = {scope.business_id}, "scope_mapping"
    else:
        matches = ctx.matches([p.email for p in rec.participants if p.email])
    if not matches and rec.parent_external_id:
        parent = session.execute(select(SourceRecord.id).where(
            SourceRecord.connector_account_id == scope.connector_account_id,
            SourceRecord.record_kind == rec.record_kind, SourceRecord.external_id == rec.parent_external_id)).scalar_one_or_none()
        if parent:
            matches = set(session.execute(select(RecordAssociation.business_id).where(
                RecordAssociation.record_id == parent, RecordAssociation.status == "associated")).scalars())
            basis = "series_mapping"
    if existing:
        if rec.change_kind == "snapshot" and rec.participants_complete and matches != existing:
            row = session.execute(select(AssociationReview).where(
                AssociationReview.record_id == record.id, AssociationReview.state == "pending")).scalar_one_or_none()
            if row is None:
                row = AssociationReview(id=uuid4(), record_id=record.id)
                session.add(row)
            row.version_id = record.current_version_id
            row.existing_business_ids = sorted(map(str, existing))
            row.proposed_business_ids = sorted(map(str, matches))
            row.reason = "different_client" if matches else "contact_no_longer_matches"
            outcome.association_conflicts += 1
        matches = existing
    elif rec.admitted:
        for bid in matches:
            stmt = insert(RecordAssociation).values(id=uuid4(), record_id=record.id, business_id=bid,
                basis=basis, status="associated", multi_client=len(matches) > 1, created_at=utcnow())
            session.execute(stmt.on_conflict_do_update(index_elements=["record_id", "business_id"],
                set_={"status": "associated", "basis": basis, "multi_client": len(matches) > 1}))
    session.execute(update(RecordAssociation).where(RecordAssociation.record_id == record.id,
        RecordAssociation.status == "associated").values(multi_client=len(matches) > 1))
