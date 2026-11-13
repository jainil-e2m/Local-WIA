"""Fathom adapter. Scope = the recorder key's visible meetings. Record = recording.

Identity check: the key must see meetings recorded by WIA (weddingindustryads.com).
This is the guard against the 20 Oct duplicate-key incident (an E2M key silently
replaced the WIA key). Qualification: an approved client contact is a calendar
invitee. Transcript segments are client/staff speech; the Fathom summary and
action items are stored as provider-generated units, never as client speech.
"""
import json
from collections import Counter
from datetime import datetime

from backend.models.domain.intake import (
    BusinessHint,
    ChangeBatch,
    ContactCandidate,
    DiscoveryResult,
    Gap,
    IdentityRef,
    IntakeContext,
    NormalisedRecord,
    ScopeCandidate,
    UnitIn,
)
from backend.config import get_settings
from backend.services.intake.adapters.base import ConnectorIdentity
from backend.services.shared.emails import PUBLIC_DOMAINS, clean, domain_of, is_internal
from backend.services.shared.errors import AuthInvalidError, NotFoundError, ScopeDeniedError
from backend.services.shared.http import ProviderClient

EXPECTED_RECORDER_DOMAIN = "weddingindustryads.com"
PAGE_SIZE_HINT = 10


def _dt(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None


def _seconds(ts: str | None) -> float | None:
    """'00:12:34' â†’ 754.0"""
    if not ts:
        return None
    parts = [float(p) for p in ts.split(":")]
    total = 0.0
    for p in parts:
        total = total * 60 + p
    return total


class FathomAdapter:
    provider = "fathom"
    parser_version = "fathom-v2"

    def __init__(self):
        key = get_settings().fathom_api_key
        if not key:
            raise AuthInvalidError("FATHOM_API_KEY not configured")
        # 60 requests/min globally (stricter for heavy content): pace at 1.2 s
        self.http = ProviderClient("fathom", "https://api.fathom.ai/external/v1/",
                                   headers={"X-Api-Key": key, "Accept": "application/json"}, min_interval_seconds=1.2)

    def identify(self) -> ConnectorIdentity:
        data = self.http.get_json("meetings")
        recorders = Counter((m.get("recorded_by") or {}).get("email", "").lower() for m in data.get("items", []))
        wia = [e for e in recorders if e.endswith("@" + EXPECTED_RECORDER_DOMAIN)]
        if not wia:
            raise AuthInvalidError("fathom key sees no WIA-recorded meetings (wrong key?)")
        primary = max(wia, key=lambda e: recorders[e])
        return ConnectorIdentity(provider_account_id=primary, display_identity=f"recorder {primary}",
                                 expected_identity_value=EXPECTED_RECORDER_DOMAIN, granted_scopes=[],
                                 credential_ref="FATHOM_API_KEY")

    def _page(self, window_start, cursor: str | None) -> dict:
        params = {"include_action_items": "true"}
        if window_start:
            params["created_after"] = window_start.isoformat().replace("+00:00", "Z")
        if cursor:
            params["cursor"] = cursor
        return self.http.get_json("meetings", params)

    def discover(self, hints: list[BusinessHint], window_start, window_end) -> DiscoveryResult:
        me = self.identify()
        result = DiscoveryResult(scopes=[ScopeCandidate(
            kind="recorder", external_id=me.provider_account_id, name=f"Fathom ({me.display_identity})",
            parent_name=None, default_domain="meetings", association_mode="per_record",
            reason="all meetings visible to this key; records qualify by approved client contacts")])
        cursor, pages, per_client = None, 0, Counter()
        while pages < 10:
            data = self._page(window_start, cursor)
            pages += 1
            for m in data.get("items", []):
                hint = next((h for h in hints if h.matches_text(m.get("title") or m.get("meeting_title"))), None)
                if not hint:
                    continue
                per_client[hint.name] += 1
                for inv in m.get("calendar_invitees", []):
                    addr = clean(inv.get("email"))
                    if addr and not is_internal(addr):
                        result.contacts.append(ContactCandidate(hint.business_id, addr, None, inv.get("name"),
                                                                f"fathom: invitee of '{(m.get('title') or '')[:60]}'"))
                        d = domain_of(addr)
                        if d and d not in PUBLIC_DOMAINS and hint.matches_text(d):
                            result.contacts.append(ContactCandidate(hint.business_id, None, d, None,
                                                                    "fathom: invitee domain matches client name"))
            cursor = data.get("next_cursor")
            if not cursor:
                break
        result.scopes[0].stats = {"client_titled_meetings": dict(per_client)}
        return result

    def read_page(self, ctx: IntakeContext, checkpoint: dict) -> ChangeBatch:
        from backend.services.intake.adapters.readers import read_page
        return read_page(self, ctx, checkpoint)

    def backfill_page(self, ctx: IntakeContext, cursor: str | None) -> ChangeBatch:
        return self.read_page(ctx, json.loads(cursor) if cursor else {})

    @staticmethod
    def _pointer(m: dict) -> NormalisedRecord:
        """A meeting no client contact attended: who and when only, no transcript calls (6 Nov: every item keeps
        a pointer, so a contact approved later attaches it with one refresh instead of a full re-read)."""
        invitees = [IdentityRef(external_key=clean(i["email"]), display_name=i.get("name"), email=clean(i["email"]))
                    for i in m.get("calendar_invitees", []) if clean(i.get("email"))]
        return NormalisedRecord(
            record_kind="fathom_recording", external_id=str(m["recording_id"]),
            occurred_at=_dt(m.get("recording_start_time") or m.get("scheduled_start_time")), provider_updated_at=None,
            source_url=m.get("url"),
            attributes={"title": m.get("title"), "meeting_title": m.get("meeting_title"),
                        "scheduled_start": m.get("scheduled_start_time"), "recording_start": m.get("recording_start_time"),
                        "created_at": m.get("created_at"), "recorded_by": (m.get("recorded_by") or {}).get("email"),
                        "invitees": [{"email": i.email, "name": i.display_name} for i in invitees]},
            units=[], participants=invitees, content_state="metadata_only", admitted=False, authoritative=True)

    def _normalise(self, m: dict) -> NormalisedRecord:
        rid = str(m["recording_id"])
        transcript = self.http.get_json(f"recordings/{rid}/transcript").get("transcript") or []
        summary = (self.http.get_json(f"recordings/{rid}/summary").get("summary") or {})
        started = _dt(m.get("recording_start_time") or m.get("scheduled_start_time"))
        invitees = [IdentityRef(external_key=clean(i["email"]), display_name=i.get("name"), email=clean(i["email"]))
                    for i in m.get("calendar_invitees", []) if clean(i.get("email"))]
        recorder = m.get("recorded_by") or {}
        units = []
        for n, seg in enumerate(transcript):
            speaker = seg.get("speaker") or {}
            email = clean(speaker.get("matched_calendar_invitee_email"))
            author = IdentityRef(external_key=email or f"speaker:{speaker.get('display_name')}",
                                 display_name=speaker.get("display_name"), email=email)
            units.append(UnitIn("transcript_segment", seg.get("text") or "",
                                {"kind": "fathom_transcript", "recording_id": rid, "segment": n,
                                 "timestamp": seg.get("timestamp"), "offset_seconds": _seconds(seg.get("timestamp"))},
                                started, author))
        if summary.get("markdown_formatted"):
            units.append(UnitIn("provider_summary", summary["markdown_formatted"],
                                {"kind": "fathom_summary", "recording_id": rid, "template": summary.get("template_name")},
                                started, provider_generated=True))
        for n, item in enumerate(m.get("action_items") or []):
            assignee = item.get("assignee") or {}
            units.append(UnitIn("provider_action_item", item.get("description") or "",
                                {"kind": "fathom_action_item", "recording_id": rid, "item": n,
                                 "timestamp": item.get("recording_timestamp"),
                                 "assignee": assignee.get("email") or assignee.get("name"),
                                 "completed": item.get("completed"), "user_generated": item.get("user_generated")},
                                started, provider_generated=True))
        state = "content" if transcript else "content_pending"
        return NormalisedRecord(
            record_kind="fathom_recording", external_id=rid, occurred_at=started, provider_updated_at=None,
            source_url=m.get("url"),
            attributes={
                "title": m.get("title"), "meeting_title": m.get("meeting_title"),
                "scheduled_start": m.get("scheduled_start_time"), "scheduled_end": m.get("scheduled_end_time"),
                "recording_start": m.get("recording_start_time"), "recording_end": m.get("recording_end_time"),
                "created_at": m.get("created_at"), "recorded_by": recorder.get("email"),
                "invitees": [{"email": i.email, "name": i.display_name} for i in invitees],
                "transcript_segments": len(transcript), "summary_present": bool(summary.get("markdown_formatted")),
                "action_items": len(m.get("action_items") or []), "share_url_present": bool(m.get("share_url")),
            },
            units=units, participants=invitees, content_state=state,
            coverage_notes=[] if transcript else ["transcript not yet available; re-poll required"],
        )
