"""Call registry: a calendar event becomes a Call with its client, type, host, attendees (with RSVP) and the
previous meetings, or is set aside as not a client call. A person's correction (`call_overrides`) always wins.

shortcut: only calendar events already associated to a client (by approved contacts) become calls; an event with
no client match isn't listed for assigning yet. Add an "Unmatched" queue when the team asks for one.
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import select

from backend.models.db import (Business, CallOverride, Person, PersonAddress, RecordAssociation, ServiceEngagement,
                               SourceRecord, SourceVersion)
from backend.services.callprep import skill_files
from backend.services.shared.emails import INTERNAL_DOMAINS

STAFF_KINDS = ("staff", "contractor", "shared_mailbox")


@dataclass
class Attendee:
    email: str
    name: str
    side: str  # WIA | Client
    response: str  # accepted | declined | tentative | needsAction


@dataclass
class Call:
    record_id: UUID
    title: str
    starts_at: datetime
    ends_at: datetime | None
    cancelled: bool
    business: Business
    skill: skill_files.Skill
    type_source: str  # Calendar title | Set by the team | Fallback
    host: str
    host_source: str  # Organiser | First WIA attendee | Set by the team | Not set
    attendees: list[Attendee]
    excluded: str | None  # why this isn't a client call, or None
    previous: datetime | None  # the last held meeting with this client before the call
    previous_record_id: UUID | None
    version_id: UUID
    location: str = ""
    override: dict = field(default_factory=dict)

    @property
    def call_id(self) -> str:
        return "cal-" + self.record_id.hex

    @property
    def attendance_risk(self) -> str | None:
        client = [a for a in self.attendees if a.side == "Client"]
        if not client:
            return None
        if any(a.response == "declined" for a in client):
            return "A client attendee declined the invite"
        if all(a.response == "needsAction" for a in client):
            return "The client hasn't accepted the invite yet"
        return None


def record_id_of(call_id: str) -> UUID:
    if not call_id.startswith("cal-"):
        raise ValueError("not a call id")
    return UUID(call_id[4:])


class Staff:
    """WIA's people by email, and WIA's own email domains (anyone there is WIA, even if not in the roster)."""

    def __init__(self, s):
        rows = s.execute(select(PersonAddress.value, Person.name, Person.kind).join(Person, Person.id == PersonAddress.person_id)
                         .where(PersonAddress.kind.in_(("email", "fathom_email")), Person.kind.in_(STAFF_KINDS),
                                Person.merged_into_id.is_(None))).all()
        self.names = {v.lower(): (n if k != "shared_mailbox" else None) for v, n, k in rows}
        self.domains = {v.lower().split("@")[-1] for v, _, k in rows if k == "staff"} | INTERNAL_DOMAINS

    def is_wia(self, email: str) -> bool:
        email = (email or "").lower()
        return email in self.names or email.split("@")[-1] in self.domains

    def name(self, email: str) -> str | None:
        return self.names.get((email or "").lower())


def _parse(value) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


def build(s, record: SourceRecord, version: SourceVersion, business: Business, *, skills=None, staff=None,
          override: CallOverride | None = None, engagements=None) -> Call:
    skills = skills or skill_files.load_all(s)
    staff = staff or Staff(s)
    a = version.attributes
    title = a.get("summary") or "Call"
    o = override
    if o is not None and o.business_id:
        business = s.get(Business, o.business_id) or business

    attendees = []
    for x in a.get("attendees") or []:
        email = (x.get("email") or "").lower()
        if not email or email.endswith("resource.calendar.google.com"):
            continue
        wia = staff.is_wia(email)
        attendees.append(Attendee(email, (staff.name(email) if wia else None) or x.get("display_name") or email,
                                  "WIA" if wia else "Client", x.get("response") or "needsAction"))

    if o is not None and o.call_type and o.call_type in skills:
        skill, type_source = skills[o.call_type], "Set by the team"
    else:
        skill = skill_files.detect(skills, title)
        type_source = "Fallback" if skill.key == "other" else "Calendar title"

    organiser = (a.get("organizer") or "").lower()
    if o is not None and o.host:
        host, host_source = o.host, "Set by the team"
    elif staff.name(organiser):
        host, host_source = staff.name(organiser), "Organiser"
    else:
        first = next((x for x in attendees if x.side == "WIA" and x.response == "accepted" and staff.name(x.email)), None)
        host, host_source = (first.name, "First WIA attendee") if first else ("Not set", "Not set")

    excluded = None
    if o is not None and o.excluded is not None:
        excluded = "Set aside by the team" if o.excluded else None
    else:
        pattern = skill_files.excluded(skills, title)
        if pattern:
            excluded = f"Title looks like a sales or intro call ({pattern})"
        elif engagements is not None:
            starts = [d for d in engagements.get(business.id, []) if d]
            if starts and min(starts) > record.occurred_at.date():
                excluded = "No engagement had started by this date"

    previous = s.execute(
        select(SourceRecord.id, SourceRecord.occurred_at).join(RecordAssociation, RecordAssociation.record_id == SourceRecord.id)
        .join(SourceVersion, SourceVersion.id == SourceRecord.current_version_id)
        .where(RecordAssociation.business_id == business.id, RecordAssociation.status == "associated",
               SourceRecord.record_kind.in_(("fathom_recording", "calendar_event")),
               SourceRecord.occurred_at < min(record.occurred_at, datetime.now(record.occurred_at.tzinfo)) - timedelta(hours=1),
               SourceVersion.attributes["status"].astext.is_distinct_from("cancelled"))
        .order_by(SourceRecord.occurred_at.desc()).limit(1)).first()
    return Call(record_id=record.id, title=title, starts_at=record.occurred_at,
                ends_at=_parse((a.get("end") or {}).get("date_time")), cancelled=a.get("status") == "cancelled",
                business=business, skill=skill, type_source=type_source, host=host, host_source=host_source,
                attendees=attendees, excluded=excluded, previous=previous[1] if previous else None,
                previous_record_id=previous[0] if previous else None, version_id=version.id,
                location=a.get("location") or "",
                override={k: getattr(o, k) for k in ("call_type", "host", "excluded", "note", "set_by")} if o else {})


def calls(s, start: datetime, end: datetime, *, include_cancelled: bool = True) -> list[Call]:
    """Client calls starting in [start, end), one per real occurrence (copies on several calendars merged)."""
    skills, staff = skill_files.load_all(s), Staff(s)
    engagements = {}
    for bid, started in s.execute(select(ServiceEngagement.business_id, ServiceEngagement.started_on)).all():
        engagements.setdefault(bid, []).append(started)
    overrides = {o.record_id: o for o in s.execute(select(CallOverride)).scalars()}
    rows = s.execute(
        select(SourceRecord, SourceVersion, Business)
        .join(SourceVersion, SourceVersion.id == SourceRecord.current_version_id)
        .join(RecordAssociation, RecordAssociation.record_id == SourceRecord.id)
        .join(Business, Business.id == RecordAssociation.business_id)
        .where(SourceRecord.record_kind == "calendar_event", SourceRecord.availability == "available",
               RecordAssociation.status == "associated", Business.status == "active",
               SourceRecord.occurred_at >= start, SourceRecord.occurred_at < end)
        .order_by(SourceRecord.occurred_at, Business.name)).all()
    out, seen = [], set()
    for record, version, business in rows:
        key = (version.attributes.get("ical_uid") or record.external_id, record.occurred_at)
        if key in seen:
            continue  # the same meeting on two calendars, or linked to two clients: the first client wins
        seen.add(key)
        call = build(s, record, version, business, skills=skills, staff=staff, override=overrides.get(record.id),
                     engagements=engagements)
        if include_cancelled or not call.cancelled:
            out.append(call)
    return out


def get(s, record_id: UUID) -> Call | None:
    row = s.execute(
        select(SourceRecord, SourceVersion, Business)
        .join(SourceVersion, SourceVersion.id == SourceRecord.current_version_id)
        .join(RecordAssociation, RecordAssociation.record_id == SourceRecord.id)
        .join(Business, Business.id == RecordAssociation.business_id)
        .where(SourceRecord.id == record_id, SourceRecord.record_kind == "calendar_event",
               RecordAssociation.status == "associated", Business.status == "active")
        .order_by(Business.name).limit(1)).first()
    if row is None:
        return None
    engagements = {}
    for bid, started in s.execute(select(ServiceEngagement.business_id, ServiceEngagement.started_on)
                                  .where(ServiceEngagement.business_id == row[2].id)).all():
        engagements.setdefault(bid, []).append(started)
    return build(s, *row, override=s.get(CallOverride, record_id), engagements=engagements)


def set_override(s, record_id: UUID, *, actor: str, call_type=None, client_slug=None, host=None, excluded=None,
                 note=None, clear: bool = False) -> None:
    from backend.models.db.base import utcnow
    o = s.get(CallOverride, record_id)
    if clear:
        if o is not None:
            s.delete(o)
        return
    if call_type is not None and call_type not in skill_files.load_all(s):
        raise ValueError(f"unknown call type {call_type}")
    business_id = None
    if client_slug:
        b = s.execute(select(Business).where(Business.slug == client_slug, Business.status == "active")).scalar_one_or_none()
        if b is None:
            raise ValueError(f"unknown client {client_slug}")
        business_id = b.id
    if o is None:
        o = CallOverride(record_id=record_id, set_by=actor)
        s.add(o)
    for name, value in (("call_type", call_type), ("business_id", business_id), ("host", host), ("excluded", excluded),
                        ("note", note)):
        if value is not None:
            setattr(o, name, value)
    o.set_by, o.set_at = actor, utcnow()
