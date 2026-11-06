"""P-02: attach mail, calendar events and Fathom meetings that were read before a contact was approved.

Every Gmail message, calendar event and Fathom meeting keeps a pointer (who, when, title) even when no client
contact was on it. Approving a contact, or reactivating a client, queues `qualify.recheck`. It finds pointers
that name the contact and are not admitted yet:

- Gmail stores no body (BF-2), so the pointer is everything intake keeps: admit it and associate it here.
- Calendar and Fathom keep text (description, transcript): queue a refresh of that one item, which re-reads
  it and now admits it.

Lock order: record writes and refresh requests run in separate transactions, so this never holds a record
lock while waiting on a stream (page jobs take stream -> record).
"""
from uuid import UUID

from sqlalchemy import String, cast, select

from backend.db import transaction
from backend.models.db import Business, ConnectorAccount, Contact, SourceRecord, SourceScope, SourceVersion
from backend.models.db.base import utcnow
from backend.models.domain.intake import ApprovedContact, IdentityRef, IntakeContext, NormalisedRecord
from backend.services.intake import sync
from backend.services.intake.persist import PersistOutcome, _associate
from backend.services.intake.scoping import is_live, live_contacts
from backend.services.read_models import portfolio
from backend.workers import queue

JOB = "qualify.recheck"
PROVIDERS = ("gmail", "calendar", "fathom")
# shortcut: one approval re-checks at most this many pointers and scans attributes without an index;
# add a GIN index on source_versions.attributes if approving a contact gets slow.
LIMIT = 500


def request(s, contact: Contact) -> None:
    """Queue a re-check for one approved contact, in the caller's transaction (a work-item insert only)."""
    queue.enqueue(s, JOB, "maintenance", f"recheck:{contact.id}:{contact.revision}", {"contact_id": str(contact.id)})


def request_for_business(s, business_id: UUID) -> None:
    for contact in s.execute(select(Contact).where(Contact.business_id == business_id,
                                                   Contact.status == "approved")).scalars():
        request(s, contact)


def _emails(kind: str, attrs: dict) -> list[str]:
    if kind == "gmail_message":
        return [attrs.get("from") or "", *(attrs.get("to") or []), *(attrs.get("cc") or [])]
    if kind == "calendar_event":
        return [a.get("email") or "" for a in attrs.get("attendees") or []] + [attrs.get("organizer") or ""]
    return [i.get("email") or "" for i in attrs.get("invitees") or []]


def _names(contact: Contact, emails: list[str]) -> bool:
    lowered = {e.lower() for e in emails if e}
    return (contact.email in lowered) if contact.email else any(e.endswith("@" + contact.domain) for e in lowered)


def recheck(contact_id: UUID) -> dict:
    """Returns counts: admitted (Gmail, here), refreshed (Calendar/Fathom, queued), skipped."""
    out = {"admitted": 0, "refreshed": 0, "skipped": 0}
    with transaction() as s:
        contact = s.get(Contact, contact_id)
        if contact is None or contact.status != "approved" or s.get(Business, contact.business_id).status != "active":
            return out
        live = live_contacts(s)
        if all(c.id != contact.id for c in live):
            return out  # a sender rule or the team roster covers this address: it never decides a client
        needle = contact.email or "@" + contact.domain
        rows = s.execute(
            select(SourceRecord, SourceVersion, ConnectorAccount.provider)
            .join(SourceVersion, SourceVersion.id == SourceRecord.current_version_id)
            .join(ConnectorAccount, ConnectorAccount.id == SourceRecord.connector_account_id)
            .where(SourceRecord.admitted_at.is_(None), SourceRecord.availability == "available",
                   ConnectorAccount.provider.in_(PROVIDERS),
                   cast(SourceVersion.attributes, String).contains(needle))
            .order_by(SourceRecord.occurred_at.desc().nulls_last()).limit(LIMIT)).all()
        hits = [(r, v, p) for r, v, p in rows if _names(contact, _emails(r.record_kind, v.attributes))]
        contacts = [ApprovedContact(c.business_id, c.email, c.domain) for c in live]
        refresh = []
        for record, version, provider in hits:
            scope = s.get(SourceScope, record.scope_id) if record.scope_id else None
            if scope is None or not is_live(s, scope):
                out["skipped"] += 1
                continue
            if provider != "gmail":
                refresh.append(record.id)
                continue
            emails = _emails(record.record_kind, version.attributes)
            ctx = IntakeContext(None, utcnow(), scope.external_id, scope.kind, contacts,
                                association_mode=scope.association_mode, business_id=scope.business_id)
            rec = NormalisedRecord(record.record_kind, record.external_id, record.occurred_at, None, record.source_url,
                                   {}, [], participants=[IdentityRef(e, email=e) for e in emails if e],
                                   change_kind="patch", parent_external_id=record.parent_external_id)
            record.admitted_at = utcnow()
            _associate(s, scope, ctx, record, rec, PersistOutcome())
            out["admitted"] += 1
        if out["admitted"]:
            portfolio.request_refresh(s)
    for record_id in refresh:
        # One transaction each: request_run locks the item's stream, nothing else.
        with transaction() as s:
            record = s.get(SourceRecord, record_id)
            try:
                sync.request_run(s, record.scope_id, "refresh", target=record.external_id)
                out["refreshed"] += 1
            except ValueError:
                out["skipped"] += 1
    return out


def run_job(work_id: UUID, lease_token: UUID, payload: dict) -> None:
    recheck(UUID(payload["contact_id"]))
    with transaction() as s:
        queue.complete(s, work_id, lease_token)

