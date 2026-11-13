"""Recording links people add to past meetings that have none (Meetings tab). Kept apart from source data:
a re-sync never overwrites them, and removing one brings back whatever the sources say (Fathom, or no link)."""
from urllib.parse import urlparse
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert

from backend.models.db import AuditEvent, MeetingLink, RecordAssociation, SourceRecord
from backend.models.db.base import utcnow
from backend.services.clients.mapping import MappingError, business_by_slug
from backend.services.read_models import portfolio

MEETING_KINDS = ("calendar_event", "fathom_recording")
MAX_URL = 1000


def clean_url(url: str) -> str:
    url = (url or "").strip()
    parsed = urlparse(url)
    if len(url) > MAX_URL or parsed.scheme not in ("http", "https") or not parsed.netloc or any(c.isspace() for c in url):
        raise MappingError("give a full http(s) link, e.g. https://zoom.us/rec/…")
    return url


def _meeting(s, slug: str, record_id: UUID) -> SourceRecord:
    business = business_by_slug(s, slug)
    record = s.get(SourceRecord, record_id)
    linked = record is not None and s.execute(select(RecordAssociation.id).where(
        RecordAssociation.record_id == record_id, RecordAssociation.business_id == business.id,
        RecordAssociation.status == "associated")).first()
    if not linked or record.record_kind not in MEETING_KINDS:
        raise MappingError("that meeting isn't one of this client's")
    return record


def set_link(s, slug: str, record_id: UUID, url: str, *, actor: str) -> dict:
    record = _meeting(s, slug, record_id)
    url = clean_url(url)
    values = {"url": url, "added_by": actor, "added_at": utcnow()}
    s.execute(insert(MeetingLink).values(record_id=record.id, **values)
              .on_conflict_do_update(index_elements=["record_id"], set_=values))
    s.add(AuditEvent(actor=actor, action="meeting.link_set", target_type="source_record", target_id=str(record.id),
                     details={"client": slug}))
    portfolio.request_refresh(s)
    return {"recordId": str(record.id), "link": url}


def clear_link(s, slug: str, record_id: UUID, *, actor: str) -> dict:
    record = _meeting(s, slug, record_id)
    s.execute(delete(MeetingLink).where(MeetingLink.record_id == record.id))
    s.add(AuditEvent(actor=actor, action="meeting.link_cleared", target_type="source_record", target_id=str(record.id),
                     details={"client": slug}))
    portfolio.request_refresh(s)
    return {"recordId": str(record.id), "link": None}
