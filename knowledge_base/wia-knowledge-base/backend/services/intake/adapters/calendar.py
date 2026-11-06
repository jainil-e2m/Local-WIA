"""Google Calendar adapter. Scope = calendar. Record = one event copy on one calendar (occurrence-level).

Window semantics: events that occur in the window OR were updated in it (so a future
call rescheduled this month is included). Qualification: an approved client contact
is an attendee/organiser. Cross-calendar copies keep their own (calendar, event)
identity and share iCalUID + original start for linking â€” never merged or double-counted.
"""
import json
from urllib.parse import quote
from collections import Counter
from datetime import datetime, timedelta

from backend.models.domain.intake import (
    BusinessHint,
    ChangeBatch,
    ContactCandidate,
    DiscoveryResult,
    IdentityRef,
    IntakeContext,
    NormalisedRecord,
    ScopeCandidate,
    UnitIn,
)
from backend.services.intake.adapters import google_auth
from backend.services.intake.adapters.base import ConnectorIdentity
from backend.services.intake.normalise.email import html_to_text
from backend.services.shared.emails import PUBLIC_DOMAINS, clean, domain_of, is_internal
from backend.services.shared.http import ProviderClient

FULL_HISTORY_HORIZON_DAYS = 365  # without a window, expand occurrences up to a year ahead
UPCOMING_HORIZON_DAYS = 120  # windowed runs: future events changed in the window


def _rfc3339(dt: datetime) -> str:
    return dt.isoformat().replace("+00:00", "Z")


def _when(t: dict | None) -> dict:
    t = t or {}
    return {"date": t.get("date"), "date_time": t.get("dateTime"), "time_zone": t.get("timeZone")}


def _instant(t: dict | None) -> datetime | None:
    if t and t.get("dateTime"):
        return datetime.fromisoformat(t["dateTime"].replace("Z", "+00:00"))
    return None


class CalendarAdapter:
    provider = "calendar"
    parser_version = "calendar-v2"

    def __init__(self):
        self.http = ProviderClient("calendar", "https://www.googleapis.com/calendar/v3/", min_interval_seconds=0.1)
        google_auth.bind(self.http)
        self._refresh = lambda: google_auth.refresh(self.http)

    def _get(self, path, params=None):
        return self.http.get_json(path, params, auth_retry=self._refresh)

    def identify(self) -> ConnectorIdentity:
        primary = self._get("users/me/calendarList/primary")  # calendars.get needs a broader scope than granted
        email = primary["id"].lower()
        return ConnectorIdentity(provider_account_id=email, display_identity=email, expected_identity_value=email,
                                 granted_scopes=google_auth.granted_scopes(), credential_ref="GOOGLE_REFRESH_TOKEN")

    def _events(self, calendar_id: str, params: dict, max_pages: int = 5) -> list[dict]:
        out, token = [], None
        for _ in range(max_pages):
            data = self._get(f"calendars/{quote(calendar_id, safe='')}/events",
                             {**params, "maxResults": 250, **({"pageToken": token} if token else {})})
            out += data.get("items", [])
            token = data.get("nextPageToken")
            if not token:
                break
        return out

    def discover(self, hints: list[BusinessHint], window_start, window_end) -> DiscoveryResult:
        result = DiscoveryResult()
        calendars = self._get("users/me/calendarList").get("items", [])
        lo = window_start or (window_end - timedelta(days=365))
        for cal in calendars:
            role = cal.get("accessRole")
            usable = role in ("owner", "writer", "reader") and "holiday" not in cal["id"]
            stats = {"access_role": role, "time_zone": cal.get("timeZone")}
            per_client: Counter = Counter()
            if usable:
                events = self._events(cal["id"], {"singleEvents": "true", "timeMin": _rfc3339(lo),
                                                  "timeMax": _rfc3339(window_end + timedelta(days=30))}, 2)
                for ev in events:
                    hint = next((h for h in hints if h.matches_text(ev.get("summary"))), None)
                    if not hint:
                        continue
                    per_client[hint.name] += 1
                    for a in ev.get("attendees", []):
                        addr = clean(a.get("email"))
                        if addr and not is_internal(addr) and not a.get("resource"):
                            result.contacts.append(ContactCandidate(
                                hint.business_id, addr, None, a.get("displayName"),
                                f"calendar: attendee of '{ev.get('summary', '')[:60]}'"))
                            d = domain_of(addr)
                            if d and d not in PUBLIC_DOMAINS and hint.matches_text(d):
                                result.contacts.append(ContactCandidate(hint.business_id, None, d, None,
                                                                        "calendar: attendee domain matches client name"))
            stats["client_titled_events"] = dict(per_client)
            result.scopes.append(ScopeCandidate(
                kind="calendar", external_id=cal["id"], name=cal.get("summaryOverride") or cal.get("summary", cal["id"]),
                parent_name=None, default_domain="meetings", association_mode="per_record",
                reason=("contains client-titled events" if per_client else
                        ("no client-titled events in window" if usable else f"access role '{role}': no event detail")),
                stats=stats))
        return result

    def read_page(self, ctx: IntakeContext, checkpoint: dict) -> ChangeBatch:
        from backend.services.intake.adapters.readers import read_page
        return read_page(self, ctx, checkpoint)

    def backfill_page(self, ctx: IntakeContext, cursor: str | None) -> ChangeBatch:
        return self.read_page(ctx, json.loads(cursor) if cursor else {})

    def _normalise(self, calendar_id: str, ev: dict) -> NormalisedRecord:
        attendees = ev.get("attendees", [])
        participants = [IdentityRef(external_key=a["email"].lower(), display_name=a.get("displayName"),
                                    email=a["email"].lower())
                        for a in attendees if clean(a.get("email"))]
        organiser = ev.get("organizer") or {}
        if clean(organiser.get("email")):
            participants.append(IdentityRef(external_key=organiser["email"].lower(),
                                            display_name=organiser.get("displayName"), email=organiser["email"].lower()))
        description = ev.get("description") or ""
        if "<" in description and ">" in description:
            description = html_to_text(description)
        units = []
        if description.strip():
            units.append(UnitIn("event_description", description,
                                {"kind": "calendar_event", "calendar_id": calendar_id, "event_id": ev["id"]},
                                _instant(ev.get("start"))))
        return NormalisedRecord(
            record_kind="calendar_event", external_id=f"{calendar_id}:{ev['id']}",
            occurred_at=_instant(ev.get("start")),
            provider_updated_at=datetime.fromisoformat(ev["updated"].replace("Z", "+00:00")) if ev.get("updated") else None,
            source_url=ev.get("htmlLink"),
            attributes={
                "calendar_id": calendar_id, "event_id": ev["id"], "ical_uid": ev.get("iCalUID"),
                "recurring_event_id": ev.get("recurringEventId"), "original_start": _when(ev.get("originalStartTime")),
                "status": ev.get("status"), "summary": ev.get("summary"), "start": _when(ev.get("start")),
                "end": _when(ev.get("end")), "organizer": organiser.get("email"), "creator": (ev.get("creator") or {}).get("email"),
                "attendees": [{"email": (a.get("email") or "").lower(), "response": a.get("responseStatus"),
                               "organizer": a.get("organizer", False), "optional": a.get("optional", False)}
                              for a in attendees],
                "attendees_omitted": ev.get("attendeesOmitted", False),
                "conference": bool(ev.get("conferenceData") or ev.get("hangoutLink")),
                "location": ev.get("location"), "visibility": ev.get("visibility"),
                "transparency": ev.get("transparency"), "event_type": ev.get("eventType"),
            },
            units=units, participants=participants,
            content_state="content" if units else "metadata_only",
            version_hint=ev.get("etag", "").strip('"') or None,
        )
