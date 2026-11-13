"""Gmail adapter. Scope = mailbox. Record = message.

Every message in the mailbox is recorded as a pointer: IDs, headers, labels, attachment names and a
fingerprint of the body. The body itself is never stored (BF-2, decided 30 Oct): `fetch_body` reads it
from Gmail when someone needs it. Only messages with an approved client contact are admitted to a client.
"""
import json
from collections import Counter
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime

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
)
from backend.services.intake.adapters import google_auth
from backend.services.intake.adapters.base import ConnectorIdentity
from backend.services.intake.normalise.email import message_text
from backend.services.shared.emails import (
    PUBLIC_DOMAINS,
    domain_of,
    is_internal,
    parse_header_addresses,
)
from backend.services.shared.errors import NotFoundError, ScopeDeniedError
from backend.services.shared.hashing import canonical_hash, normalise_text, sha256_text
from backend.services.shared.http import ProviderClient

PAGE_SIZE = 25
FINANCE_SENDERS = {"noreply@dubsado.com"}
POINTER_NOTE = "email body not stored: read from Gmail on demand"


BULK_LABELS = {"CATEGORY_PROMOTIONS", "CATEGORY_SOCIAL", "CATEGORY_FORUMS"}


def _is_bulk(headers: list[dict], labels: list[str]) -> bool:
    """Newsletters, promotions and machine-sent mail: never evidence of a client contact."""
    if any(label in BULK_LABELS for label in labels):
        return True
    if _header(headers, "List-Unsubscribe"):
        return True
    if (_header(headers, "Precedence") or "").lower() in ("bulk", "list", "junk"):
        return True
    return (_header(headers, "Auto-Submitted") or "no").lower() != "no"


def _header(headers: list[dict], name: str) -> str | None:
    return next((h["value"] for h in headers if h.get("name", "").lower() == name.lower()), None)


def _body_sha256(authored: str, quoted: str) -> str | None:
    """Fingerprint of the text, so a changed body is a new version without keeping the text."""
    text = normalise_text(authored + "\n\n" + quoted)
    return sha256_text(text) if text else None


class GmailAdapter:
    provider = "gmail"
    parser_version = "gmail-v3"  # v3: pointer only, the body is never stored (BF-2)

    def __init__(self):
        self.http = ProviderClient("gmail", "https://gmail.googleapis.com/gmail/v1/users/me/",
                                   min_interval_seconds=0.05)
        google_auth.bind(self.http)
        self._refresh = lambda: google_auth.refresh(self.http)

    def _get(self, path, params=None):
        return self.http.get_json(path, params, auth_retry=self._refresh)

    def identify(self) -> ConnectorIdentity:
        profile = self._get("profile")
        email = profile["emailAddress"].lower()
        return ConnectorIdentity(provider_account_id=email, display_identity=email, expected_identity_value=email,
                                 granted_scopes=google_auth.granted_scopes(), credential_ref="GOOGLE_REFRESH_TOKEN")

    def _search(self, q: str, max_pages: int = 2) -> list[str]:
        ids, token = [], None
        for _ in range(max_pages):
            params = {"q": q, "maxResults": 100, **({"pageToken": token} if token else {})}
            data = self._get("messages", params)
            ids += [m["id"] for m in data.get("messages", [])]
            token = data.get("nextPageToken")
            if not token:
                break
        return ids

    def discover(self, hints: list[BusinessHint], window_start, window_end) -> DiscoveryResult:
        """Propose the people the mailbox actually corresponds with about each client.

        Bulk mail (newsletters, promotions, auto-submitted) is skipped. Only direct correspondents count:
        the sender of a message to this mailbox, or a recipient of a message from it. Others copied on
        someone else's email, and everyone in mail that merely mentions the client, are not proposed.
        A domain is proposed only when it carries the client's name. Platform, internal, team and partner
        senders are removed later, across all providers (discovery.filter_contacts)."""
        me = self.identify()
        mailbox = me.provider_account_id
        result = DiscoveryResult(scopes=[ScopeCandidate(
            kind="mailbox", external_id=mailbox, name=me.display_identity, parent_name=None,
            default_domain="communications", association_mode="per_record",
            reason="shared WIA mailbox; records qualify by approved client contacts")])
        after = f" after:{int(window_start.timestamp())}" if window_start else ""
        for hint in hints:
            terms = " OR ".join(f'"{a}"' for a in hint.aliases)
            seen: Counter = Counter()
            names: dict[str, str] = {}
            for mid in self._search(f"({terms}){after}"):
                meta = self._get(f"messages/{mid}", {"format": "metadata", "metadataHeaders": [
                    "From", "To", "Cc", "List-Unsubscribe", "Precedence", "Auto-Submitted"]})
                headers = meta.get("payload", {}).get("headers", [])
                if _is_bulk(headers, meta.get("labelIds", [])):
                    continue
                sender = parse_header_addresses(_header(headers, "From"))
                recipients = parse_header_addresses(_header(headers, "To"), _header(headers, "Cc"))
                if sender and sender[0][1] == mailbox:
                    people = recipients  # we wrote to them
                elif any(addr == mailbox for _, addr in recipients):
                    people = sender  # they wrote to us
                else:
                    people = []  # neither side is this mailbox (e.g. a forward to an alias)
                for name, addr in people:
                    if addr == mailbox or is_internal(addr):
                        continue
                    seen[addr] += 1
                    names.setdefault(addr, name)
            for addr, n in seen.most_common():
                result.contacts.append(ContactCandidate(hint.business_id, addr, None, names.get(addr) or None,
                                                        f"gmail: {n} direct message(s) about {hint.name}"))
            domains = Counter(domain_of(a) for a in seen)
            for domain, n in domains.items():
                if domain not in PUBLIC_DOMAINS and hint.matches_text(domain):
                    result.contacts.append(ContactCandidate(hint.business_id, None, domain, None,
                                                            f"gmail: domain matches client name ({n} address(es))"))
        return result

    def read_page(self, ctx: IntakeContext, checkpoint: dict) -> ChangeBatch:
        from backend.services.intake.adapters.readers import read_page
        return read_page(self, ctx, checkpoint)

    def backfill_page(self, ctx: IntakeContext, cursor: str | None) -> ChangeBatch:
        return self.read_page(ctx, json.loads(cursor) if cursor else {})

    def fetch_body(self, message_id: str) -> dict:
        """One email's text, read live from Gmail for viewing (and later the AI step). Never persisted.

        Raises NotFoundError when the message is gone from Gmail. Compare `body_sha256` with the stored
        pointer's to see whether the text changed since intake.
        """
        msg = self._get(f"messages/{message_id}", {"format": "full"})
        authored, quoted, attachments, fmt = message_text(msg.get("payload", {}))
        return {"message_id": msg["id"], "thread_id": msg.get("threadId"), "authored": authored, "quoted": quoted,
                "attachments": attachments, "body_format": fmt, "body_sha256": _body_sha256(authored, quoted)}

    def _normalise(self, msg: dict) -> NormalisedRecord:
        payload = msg.get("payload", {})
        headers = payload.get("headers", [])
        sender = parse_header_addresses(_header(headers, "From"))
        recipients = parse_header_addresses(_header(headers, "To"), _header(headers, "Cc"))
        participants = [IdentityRef(external_key=addr, display_name=name or None, email=addr)
                        for name, addr in sender + recipients]
        internal = datetime.fromtimestamp(int(msg["internalDate"]) / 1000, UTC)
        try:
            sent = parsedate_to_datetime(_header(headers, "Date")) if _header(headers, "Date") else None
        except (TypeError, ValueError):
            sent = None
        # A `format=full` read has the body: keep only its fingerprint and attachment names, never the text.
        authored, quoted, attachments, fmt = message_text(payload)
        body_sha256 = _body_sha256(authored, quoted)
        labels = msg.get("labelIds", [])
        from_addr = sender[0][1] if sender else None
        notes = [POINTER_NOTE]
        if attachments:
            notes.append("attachments are referenced, not parsed")
        return NormalisedRecord(
            record_kind="gmail_message", external_id=msg["id"], occurred_at=internal, provider_updated_at=None,
            source_url=f"https://mail.google.com/mail/u/0/#all/{msg['id']}",
            attributes={
                "thread_id": msg.get("threadId"), "rfc_message_id": _header(headers, "Message-ID"),
                "in_reply_to": _header(headers, "In-Reply-To"), "subject": _header(headers, "Subject"),
                "from": from_addr, "to": [a for _, a in parse_header_addresses(_header(headers, "To"))],
                "cc": [a for _, a in parse_header_addresses(_header(headers, "Cc"))],
                "sent_header_at": sent.isoformat() if sent else None, "labels": labels,
                "state": "draft" if "DRAFT" in labels else ("sent" if "SENT" in labels else "received"),
                "attachments": attachments, "body_format": fmt, "body_sha256": body_sha256,
            },
            units=[], participants=participants,
            content_state="metadata_only", coverage_notes=notes,
            domain="finance" if from_addr in FINANCE_SENDERS else None,
            # Gmail message content is immutable; labels change on read/archive. Version on the
            # immutable parts only. Label state is the incremental sync's concern (before_production P-04).
            version_hint="gm:" + canonical_hash({"body_sha256": body_sha256,
                                                 "headers": [_header(headers, h) for h in
                                                             ("From", "To", "Cc", "Subject", "Date", "Message-ID")],
                                                 "attachments": attachments}),
        )
