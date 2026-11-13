"""Batched account-scoped recognition, independent of content state."""
from dataclasses import dataclass, field
from sqlalchemy import select, tuple_
from backend.db import transaction
from backend.models.db import ContentUnit, RecordAssociation, SourceRecord, SourceVersion


@dataclass(frozen=True)
class StoredRecord:
    admitted: bool
    attributes: dict = field(default_factory=dict)
    business_ids: frozenset = frozenset()
    expired: bool = False
    availability: str = "available"


def lookup(account_id, keys):
    result = {}
    for offset in range(0, len(keys), 500):
        with transaction() as s:
            rows = s.execute(select(SourceRecord, SourceVersion.attributes).outerjoin(
                SourceVersion, SourceVersion.id == SourceRecord.current_version_id).where(
                SourceRecord.connector_account_id == account_id,
                tuple_(SourceRecord.record_kind, SourceRecord.external_id).in_(keys[offset:offset + 500]))).all()
            ids = [r.id for r, _ in rows]
            links = {}
            for rid, bid in s.execute(select(RecordAssociation.record_id, RecordAssociation.business_id).where(
                    RecordAssociation.record_id.in_(ids), RecordAssociation.status == "associated")):
                links.setdefault(rid, set()).add(bid)
            expired = set(s.execute(select(SourceVersion.record_id).join(
                ContentUnit, ContentUnit.version_id == SourceVersion.id).where(
                SourceVersion.record_id.in_(ids), ContentUnit.retention_state == "expired")).scalars())
            for r, attributes in rows:
                result[(r.record_kind, r.external_id)] = StoredRecord(r.admitted_at is not None,
                    attributes or {}, frozenset(links.get(r.id, ())), r.id in expired, r.availability)
    return result


def recognize(ctx, kind, ids):
    records = ctx.lookup_records([(kind, i) for i in set(ids)]) if ctx.lookup_records else {}
    return {i: records[(kind, i)] for i in set(ids) if (kind, i) in records}


def qualifies(ctx, emails, stored=None):
    return bool((stored and stored.admitted) or
                (ctx.association_mode == "dedicated" and ctx.business_id) or ctx.matches(emails))


def content_allowed(stored):
    return not (stored and stored.expired)
