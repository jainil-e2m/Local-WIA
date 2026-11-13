"""LeadLock (white-labelled HighLevel) adapter. Scope = one client sub-account ("location"). Records = the
venue's leads and their outcomes: contacts, opportunities, conversations, form submissions, appointments,
plus the venue's own invoices and payments.

Access comes from the Marketplace app (services/intake/leadlock_app.py): one agency grant, a token per
sub-account. A sub-account is read only once an admin approves it as a scope of a client (S2).

Privacy: these records are the venue's couples. The KB keeps what lead outcomes, response times and revenue
need, and never their names, emails, phone numbers, addresses, message text, free-text answers, appointment
titles or opportunity names (decided 4 Nov; same principle as email-as-pointer, 30 Oct). Custom fields are
kept only when structured (date, number, money, options, checkbox); free-text fields are where names hide.
Every record is metadata only: no content units, so nothing here goes to AI extraction.
"""
import json
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from backend.db import transaction
from backend.models.db import LeadLockInstallation, LeadLockLocation
from backend.models.domain.intake import (
    BusinessHint,
    ChangeBatch,
    DiscoveryResult,
    Gap,
    IntakeContext,
    NormalisedRecord,
    ScopeCandidate,
)
from backend.services.intake import leadlock_app
from backend.services.intake.adapters.base import ConnectorIdentity
from backend.services.shared.errors import AuthInvalidError, NotFoundError, ScopeDeniedError
from backend.services.shared.http import ProviderClient

API_VERSION = "2021-07-28"  # data endpoints
PAGE = 100
PHASES = ("pipelines", "contacts", "opportunities", "conversations", "form_submissions", "appointments", "invoices",
          "transactions")
FINANCE_PHASES = {"invoices", "transactions"}
STRUCTURED_FIELD_TYPES = {"DATE", "NUMERICAL", "FLOAT", "MONETORY", "MONETARY", "SINGLE_OPTIONS",
                          "MULTIPLE_OPTIONS", "CHECKBOX", "RADIO"}
APPOINTMENT_CHUNK = timedelta(days=90)
APPOINTMENT_HISTORY_FLOOR = datetime(2020, 1, 1, tzinfo=UTC)  # before LeadLock existed
APPOINTMENT_HORIZON = timedelta(days=365)  # booked tours ahead count as outcomes too


def _when(value) -> datetime | None:
    """HighLevel sends ISO strings in some places and epoch milliseconds in others."""
    if value in (None, "", 0):
        return None
    if isinstance(value, (int, float)) or (isinstance(value, str) and value.isdigit()):
        return datetime.fromtimestamp(int(value) / 1000, UTC)
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def _iso(value) -> str | None:
    dt = _when(value)
    return dt.isoformat() if dt else None


class LeadLockAdapter:
    provider = "leadlock"
    parser_version = "leadlock-v3"  # v2: DATE fields as YYYY-MM-DD; v3: full form-submission history + stage order

    def __init__(self):
        self.http = ProviderClient("leadlock", leadlock_app.API + "/",
                                   headers={"Version": API_VERSION, "Accept": "application/json",
                                            "User-Agent": leadlock_app.USER_AGENT},
                                   min_interval_seconds=0.12)  # HighLevel: 100 requests / 10 s per sub-account
        self._fields: dict[str, dict] | None = None
        self._pipelines: dict[str, dict] | None = None
        self._forms: dict[str, str] | None = None

    # --- identity and discovery (no client data) --------------------------------------------------------

    def identify(self) -> ConnectorIdentity:
        try:
            leadlock_app.company_token()  # proves the agency grant still refreshes
        except leadlock_app.LeadLockAppError as exc:
            raise AuthInvalidError(f"leadlock: {exc}") from None
        with transaction() as s:
            inst = s.execute(select(LeadLockInstallation).where(LeadLockInstallation.revoked_at.is_(None))).scalar_one()
            active = s.execute(select(LeadLockLocation).where(LeadLockLocation.state == "active")).scalars().all()
            return ConnectorIdentity(provider_account_id=inst.company_id,
                                     display_identity=f"LeadLock agency app ({len(active)} sub-accounts with a token)",
                                     expected_identity_value=inst.company_id, granted_scopes=list(inst.scopes),
                                     credential_ref="leadlock_installations (KB database)")

    def discover(self, hints: list[BusinessHint], window_start, window_end) -> DiscoveryResult:
        """Every sub-account the app is installed on, matched to a client by name where one fits. The list
        comes from the app's own records (`kb leadlock reconcile`), so discovery makes no API calls."""
        result = DiscoveryResult()
        with transaction() as s:
            locations = s.execute(select(LeadLockLocation).where(LeadLockLocation.state != "uninstalled")
                                  .order_by(LeadLockLocation.name)).scalars().all()
            for loc in locations:
                match = next((h for h in hints if h.matches_text(loc.name)), None)
                reason = (f"sub-account name matches alias of {match.name}" if match
                          else "LeadLock sub-account; no client matches: add the client or exclude")
                if loc.state != "active":
                    reason += f" ({loc.state}: {loc.last_error or 'no token yet'})"
                result.scopes.append(ScopeCandidate(
                    kind="location", external_id=loc.location_id, name=loc.name or loc.location_id,
                    parent_name="LeadLock", default_domain="leads", association_mode="dedicated",
                    suggested_business_id=match.business_id if match else None, reason=reason,
                    stats={"state": loc.state}))
        return result

    def describe_scope(self, kind: str, external_id: str) -> ScopeCandidate:
        if kind != "location":
            raise NotFoundError(f"leadlock: scopes are locations (sub-accounts), not {kind}")
        with transaction() as s:
            loc = s.execute(select(LeadLockLocation).where(LeadLockLocation.location_id == external_id)).scalar_one_or_none()
            if loc is None or loc.state == "uninstalled":
                raise NotFoundError("leadlock: the app is not installed on that sub-account (run `kb leadlock reconcile`)")
            return ScopeCandidate(kind="location", external_id=loc.location_id, name=loc.name or loc.location_id,
                                  parent_name="LeadLock", default_domain="leads", association_mode="dedicated",
                                  reason="added by ID", stats={"state": loc.state})

    # --- reading ------------------------------------------------------------------------------------------

    def backfill_page(self, ctx: IntakeContext, cursor: str | None) -> ChangeBatch:
        return self.read_page(ctx, json.loads(cursor) if cursor else {})

    def read_page(self, ctx: IntakeContext, checkpoint: dict) -> ChangeBatch:
        """One API page of one phase. The checkpoint holds the phase and its provider cursor, never data.
        Every run reads the whole sub-account (lead volumes are small); unchanged records hash identically,
        so a re-run only versions what changed."""
        st = dict(checkpoint or {})
        st.setdefault("phase", PHASES[0])
        location_id = ctx.scope_external_id
        self._authorise(location_id)
        batch = ChangeBatch([], None, False)
        phase = st["phase"]
        try:
            records, cursor = getattr(self, f"_page_{phase}")(ctx, location_id, st.get("cursor") or {})
        except (ScopeDeniedError, AuthInvalidError) as exc:
            # A refused feature (e.g. a scope this sub-account's plan lacks) is a gap for this phase only.
            batch.gaps.append(Gap(external_id=f"{location_id}:{phase}", reason="scope_denied", detail=str(exc)[:200]))
            records, cursor = [], None
        batch.records.extend(records)
        batch.discovered = len(records)
        if cursor:
            st["cursor"] = cursor
        else:
            st.pop("cursor", None)
            following = PHASES.index(phase) + 1
            if following < len(PHASES):
                st["phase"] = PHASES[following]
            else:
                st.pop("phase")
        batch.checkpoint = st
        batch.terminal = "phase" not in st
        batch.committed_cursor = {"watermark": ctx.window_end.isoformat()} if batch.terminal else None
        return batch

    def _authorise(self, location_id: str) -> None:
        def mint():
            try:
                return leadlock_app.mint_location_token(location_id)
            except (leadlock_app.LeadLockAppError, AuthInvalidError) as exc:
                # One paused or removed sub-account must not block the whole LeadLock connector.
                raise ScopeDeniedError(f"leadlock: no token for this sub-account ({exc})") from None
        try:
            token = leadlock_app.location_token(location_id)
        except leadlock_app.LeadLockAppError:
            token = mint()
        except AuthInvalidError as exc:
            raise ScopeDeniedError(f"leadlock: no token for this sub-account ({exc})") from None
        self.http.set_header("Authorization", f"Bearer {token}")
        self._remint = lambda: self.http.set_header("Authorization", f"Bearer {mint()}")

    def _get(self, path: str, params=None) -> dict:
        return self.http.get_json(path, params, auth_retry=self._remint)

    # Definitions, fetched once per page job

    def _field_types(self, location_id: str) -> dict[str, dict]:
        if self._fields is None:
            data = self._get(f"locations/{location_id}/customFields")
            self._fields = {f["id"]: {"name": f.get("name"), "type": str(f.get("dataType") or "").upper()}
                            for f in data.get("customFields", []) if f.get("id")}
        return self._fields

    def _structured(self, location_id: str, values: list) -> dict:
        """Structured custom field values by field name; free-text and contact-detail fields are dropped."""
        defs, out = self._field_types(location_id), {}
        for v in values or []:
            d = defs.get(v.get("id"))
            if not d or d["type"] not in STRUCTURED_FIELD_TYPES:
                continue
            value = next((v[k] for k in ("value", "fieldValue", "field_value", "fieldValueArray") if v.get(k) not in (None, "")), None)
            if value is not None and d["type"] == "DATE" and _when(value):
                value = _when(value).date().isoformat()  # epoch ms or ISO -> YYYY-MM-DD
            if value is not None and d["name"]:
                out[d["name"]] = value
        return out

    def _pipeline_map(self, location_id: str) -> dict[str, dict]:
        if self._pipelines is None:
            data = self._get("opportunities/pipelines", {"locationId": location_id})
            self._pipelines = {p["id"]: {"name": p.get("name"), "stages": {s["id"]: s.get("name") for s in p.get("stages", [])}}
                               for p in data.get("pipelines", []) if p.get("id")}
        return self._pipelines

    def _form_names(self, location_id: str) -> dict[str, str]:
        if self._forms is None:
            data = self._get("forms/", {"locationId": location_id, "limit": 100})
            self._forms = {f["id"]: f.get("name") for f in data.get("forms", []) if f.get("id")}
        return self._forms

    # Phases: each returns (records, next cursor or None)

    def _page_pipelines(self, ctx, location_id, cursor):
        """Pipeline definitions with their stages in HighLevel's order, so a funnel reads left to right."""
        pipelines = self._get("opportunities/pipelines", {"locationId": location_id}).get("pipelines", [])
        return [self._pipeline(location_id, p) for p in pipelines if p.get("id")], None

    def _page_contacts(self, ctx, location_id, cursor):
        params = {"locationId": location_id, "limit": PAGE, **cursor}
        data = self._get("contacts/", params)
        rows = data.get("contacts", [])
        records = [self._contact(location_id, c) for c in rows]
        meta = data.get("meta") or {}
        more = len(rows) == PAGE and meta.get("startAfterId")
        return records, ({"startAfterId": meta["startAfterId"], "startAfter": meta.get("startAfter")} if more else None)

    def _page_opportunities(self, ctx, location_id, cursor):
        data = self._get("opportunities/search", {"location_id": location_id, "limit": PAGE, **cursor})
        rows = data.get("opportunities", [])
        pipelines = self._pipeline_map(location_id) if rows else {}
        records = [self._opportunity(location_id, o, pipelines) for o in rows]
        meta = data.get("meta") or {}
        more = len(rows) == PAGE and meta.get("startAfterId")
        return records, ({"startAfterId": meta["startAfterId"], "startAfter": meta.get("startAfter")} if more else None)

    def _page_conversations(self, ctx, location_id, cursor):
        params = {"locationId": location_id, "limit": PAGE, "sortBy": "last_message_date", "sort": "asc", **cursor}
        data = self._get("conversations/search", params)
        rows = data.get("conversations", [])
        records = [self._conversation(location_id, c) for c in rows]
        if len(rows) < PAGE:
            return records, None
        last = rows[-1]
        after = (last.get("sort") or [None])[0] or last.get("lastMessageDate")
        return records, ({"startAfterDate": after} if after else None)

    def _page_form_submissions(self, ctx, location_id, cursor):
        # Without startAt/endAt HighLevel returns only the last 30 days (found 5 Nov: 237 of 1,208 for one venue).
        page = int(cursor.get("page", 1))
        start = max(ctx.window_start or APPOINTMENT_HISTORY_FLOOR, APPOINTMENT_HISTORY_FLOOR).date().isoformat()
        end = (ctx.window_end + timedelta(days=1)).date().isoformat()
        data = self._get("forms/submissions", {"locationId": location_id, "limit": PAGE, "page": page,
                                               "startAt": start, "endAt": end})
        rows = data.get("submissions", [])
        names = self._form_names(location_id) if rows else {}
        records = [self._submission(location_id, f, names) for f in rows]
        nxt = (data.get("meta") or {}).get("nextPage")
        return records, ({"page": int(nxt)} if nxt and rows else None)

    def _page_appointments(self, ctx, location_id, cursor):
        """Calendar by calendar, in 90-day windows from when the sub-account was created (or the window
        start, if later) to a year ahead. Starting at creation skips years of empty windows."""
        if "calendars" not in cursor:
            calendars = self._get("calendars/", {"locationId": location_id}).get("calendars", [])
            if not calendars:
                return [], None
            created = _when((self._get(f"locations/{location_id}").get("location") or {}).get("dateAdded"))
            start = max(d for d in (ctx.window_start, created, APPOINTMENT_HISTORY_FLOOR) if d)
            cursor = {"calendars": [c["id"] for c in calendars if c.get("id")], "index": 0,
                      "first": start.isoformat(), "from": start.isoformat()}
        cal_ids, i = cursor["calendars"], cursor["index"]
        lo = datetime.fromisoformat(cursor["from"])
        hi = lo + APPOINTMENT_CHUNK
        data = self._get("calendars/events", {"locationId": location_id, "calendarId": cal_ids[i],
                                              "startTime": int(lo.timestamp() * 1000), "endTime": int(hi.timestamp() * 1000)})
        records = [self._appointment(location_id, e) for e in data.get("events", [])]
        if hi < ctx.window_end + APPOINTMENT_HORIZON:
            return records, {**cursor, "from": hi.isoformat()}
        if i + 1 < len(cal_ids):
            return records, {**cursor, "index": i + 1, "from": cursor["first"]}
        return records, None

    def _page_invoices(self, ctx, location_id, cursor):
        offset = int(cursor.get("offset", 0))
        data = self._get("invoices/", {"altId": location_id, "altType": "location", "limit": PAGE, "offset": offset})
        rows = data.get("invoices", [])
        return [self._invoice(location_id, v) for v in rows], ({"offset": offset + PAGE} if len(rows) == PAGE else None)

    def _page_transactions(self, ctx, location_id, cursor):
        offset = int(cursor.get("offset", 0))
        data = self._get("payments/transactions", {"altId": location_id, "altType": "location", "limit": PAGE,
                                                   "offset": offset})
        rows = data.get("data", [])
        return [self._transaction(location_id, t) for t in rows], ({"offset": offset + PAGE} if len(rows) == PAGE else None)

    # Normalisers: only the fields listed here are kept (see the module docstring)

    def _record(self, kind, external_id, location_id, occurred, updated, attributes, domain=None) -> NormalisedRecord:
        return NormalisedRecord(
            record_kind=kind, external_id=str(external_id), occurred_at=_when(occurred), provider_updated_at=_when(updated),
            source_url=None, attributes={"location_id": location_id, **attributes}, units=[],
            content_state="metadata_only", domain=domain, authoritative=True)

    def _pipeline(self, location_id, p) -> NormalisedRecord:
        stages = sorted(p.get("stages") or [], key=lambda s: (s.get("position") is None, s.get("position") or 0))
        return self._record("leadlock_pipeline", p["id"], location_id, None, None, {
            "name": p.get("name"),
            "stages": [{"id": s.get("id"), "name": s.get("name"), "position": i} for i, s in enumerate(stages)]})

    def _contact(self, location_id, c) -> NormalisedRecord:
        attributions = [{k: a.get(k) for k in ("medium", "utmSource", "utmMedium", "utmCampaign", "utmContent",
                                                "sessionSource", "isFirst", "isConversion") if a.get(k) is not None}
                        for a in c.get("attributions") or [] if isinstance(a, dict)]
        return self._record("leadlock_contact", c["id"], location_id, c.get("dateAdded"), c.get("dateUpdated"), {
            "type": c.get("type"), "source": c.get("source"), "tags": sorted(c.get("tags") or []),
            "assigned_user_id": c.get("assignedTo"), "dnd": c.get("dnd"), "attributions": attributions,
            "custom_fields": self._structured(location_id, c.get("customFields")),
            "date_added": _iso(c.get("dateAdded"))})

    def _opportunity(self, location_id, o, pipelines) -> NormalisedRecord:
        pipeline = pipelines.get(o.get("pipelineId")) or {}
        return self._record("leadlock_opportunity", o["id"], location_id, o.get("createdAt"), o.get("updatedAt"), {
            "contact_id": o.get("contactId"), "pipeline_id": o.get("pipelineId"), "pipeline": pipeline.get("name"),
            "stage_id": o.get("pipelineStageId"), "stage": (pipeline.get("stages") or {}).get(o.get("pipelineStageId")),
            "status": o.get("status"), "monetary_value": o.get("monetaryValue"), "source": o.get("source"),
            "assigned_user_id": o.get("assignedTo"), "lost_reason_id": o.get("lostReasonId"),
            "last_status_change_at": _iso(o.get("lastStatusChangeAt")), "last_stage_change_at": _iso(o.get("lastStageChangeAt")),
            "custom_fields": self._structured(location_id, o.get("customFields"))})

    def _conversation(self, location_id, c) -> NormalisedRecord:
        return self._record("leadlock_conversation", c["id"], location_id, c.get("dateAdded"), c.get("dateUpdated"), {
            "contact_id": c.get("contactId"), "channel": c.get("type"), "last_message_type": c.get("lastMessageType"),
            "last_message_direction": c.get("lastMessageDirection"), "last_message_at": _iso(c.get("lastMessageDate")),
            "unread_count": c.get("unreadCount"), "assigned_user_id": c.get("assignedTo")})

    def _submission(self, location_id, f, names) -> NormalisedRecord:
        return self._record("leadlock_form_submission", f["id"], location_id, f.get("createdAt"), None, {
            "contact_id": f.get("contactId"), "form_id": f.get("formId"), "form": names.get(f.get("formId"))})

    def _appointment(self, location_id, e) -> NormalisedRecord:
        return self._record("leadlock_appointment", e["id"], location_id, e.get("dateAdded"), e.get("dateUpdated"), {
            "contact_id": e.get("contactId"), "calendar_id": e.get("calendarId"),
            "status": e.get("appointmentStatus") or e.get("status"), "start_at": _iso(e.get("startTime")),
            "end_at": _iso(e.get("endTime")), "assigned_user_id": e.get("assignedUserId")})

    def _invoice(self, location_id, v) -> NormalisedRecord:
        return self._record("leadlock_invoice", v.get("_id") or v.get("id"), location_id, v.get("createdAt"),
                            v.get("updatedAt"), {
            "number": v.get("invoiceNumber"), "title": v.get("title") or v.get("name"), "status": v.get("status"),
            "currency": v.get("currency"), "total": v.get("total"), "amount_paid": v.get("amountPaid"),
            "amount_due": v.get("amountDue"), "issue_date": _iso(v.get("issueDate")), "due_date": _iso(v.get("dueDate")),
            "contact_id": (v.get("contactDetails") or {}).get("id"), "live_mode": v.get("liveMode")}, domain="finance")

    def _transaction(self, location_id, t) -> NormalisedRecord:
        return self._record("leadlock_transaction", t.get("_id") or t.get("id"), location_id, t.get("createdAt"),
                            t.get("updatedAt"), {
            "amount": t.get("amount"), "currency": t.get("currency"), "status": t.get("status"),
            "entity_type": t.get("entityType"), "entity_id": t.get("entityId"), "contact_id": t.get("contactId"),
            "payment_provider": (t.get("paymentProvider") or {}).get("type") if isinstance(t.get("paymentProvider"), dict) else None,
            "live_mode": t.get("liveMode")}, domain="finance")
