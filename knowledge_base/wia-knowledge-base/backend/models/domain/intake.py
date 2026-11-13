"""Provider-neutral intake types. Adapters produce these; everything after is provider-agnostic."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass(frozen=True)
class IdentityRef:
    external_key: str  # provider user ID, or email when that is the only key
    display_name: str | None = None
    email: str | None = None


@dataclass
class UnitIn:
    unit_kind: str
    text: str
    locator: dict[str, Any]
    occurred_at: datetime | None = None
    author: IdentityRef | None = None
    is_quoted: bool = False
    provider_generated: bool = False
    domain: str | None = None  # None = record/scope default


@dataclass
class NormalisedRecord:
    record_kind: str
    external_id: str
    occurred_at: datetime | None
    provider_updated_at: datetime | None
    source_url: str | None
    attributes: dict[str, Any]
    units: list[UnitIn]
    participants: list[IdentityRef] = field(default_factory=list)
    content_state: str = "content"  # content | metadata_only | content_pending | unsupported | partial
    coverage_notes: list[str] = field(default_factory=list)
    version_hint: str | None = None  # provider version token, when meaningful
    domain: str | None = None  # overrides the scope default for every unit without its own domain
    change_kind: str = "snapshot"  # snapshot | patch | tombstone
    availability: str = "available"
    admitted: bool = True  # explicit qualification, independent of whether text exists
    participants_complete: bool = True
    provider_state: dict[str, Any] = field(default_factory=dict)
    parent_external_id: str | None = None
    authoritative: bool = False  # fetched current state, not an event payload
    carry_content: bool = False  # lifecycle patches retain the last evidence units


@dataclass
class Gap:
    external_id: str
    reason: str  # error class: inaccessible | unsupported | failed | ...
    detail: str = ""


@dataclass
class ChangeBatch:
    records: list[NormalisedRecord]
    next_cursor: str | None
    terminal: bool
    discovered: int = 0  # items enumerated on this page, before qualification
    excluded: int = 0  # enumerated but not qualified (e.g. not a client message)
    gaps: list[Gap] = field(default_factory=list)
    checkpoint: dict[str, Any] = field(default_factory=dict)
    committed_cursor: dict[str, Any] | None = None
    memberships: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class ApprovedContact:
    business_id: UUID
    email: str | None
    domain: str | None


@dataclass
class IntakeContext:
    """What an adapter may know about the client registry while enumerating one scope."""
    window_start: datetime | None  # None = full history
    window_end: datetime
    scope_external_id: str
    scope_kind: str
    contacts: list[ApprovedContact]
    settings: Any = None
    connector_account_id: UUID | None = None
    scope_id: UUID | None = None
    association_mode: str = "per_record"
    business_id: UUID | None = None
    # Injected batch lookup. It opens a short session, never holds one across HTTP.
    lookup_records: Any = None
    mode: str = "backfill"
    target_external_id: str | None = None
    stream_cursor: dict[str, Any] = field(default_factory=dict)
    internal_emails: frozenset = frozenset()  # WIA's own addresses (roster): spots internal-only meetings

    def matches(self, emails: list[str]) -> set[UUID]:
        """Businesses whose approved contact (exact email or domain) appears in `emails`."""
        found: set[UUID] = set()
        lowered = {e.lower() for e in emails if e}
        domains = {e.split("@", 1)[1] for e in lowered if "@" in e}
        for c in self.contacts:
            if (c.email and c.email in lowered) or (c.domain and c.domain in domains):
                found.add(c.business_id)
        return found


@dataclass
class ScopeCandidate:
    kind: str
    external_id: str
    name: str
    parent_name: str | None
    default_domain: str
    association_mode: str  # dedicated | per_record
    suggested_business_id: UUID | None = None
    reason: str | None = None
    stats: dict[str, Any] = field(default_factory=dict)


@dataclass
class ContactCandidate:
    business_id: UUID
    email: str | None
    domain: str | None
    display_name: str | None
    evidence: str  # e.g. "calendar: 3 events titled 'Dogwood …'"


@dataclass
class DiscoveryResult:
    scopes: list[ScopeCandidate] = field(default_factory=list)
    contacts: list[ContactCandidate] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    possible_partners: dict[str, set] = field(default_factory=dict)  # sender key -> business ids


@dataclass(frozen=True)
class BusinessHint:
    business_id: UUID
    name: str
    aliases: tuple[str, ...]

    def matches_text(self, text: str | None) -> bool:
        if not text:
            return False
        haystack = text.lower().replace("_", " ").replace("-", " ")
        compact = haystack.replace(" ", "")
        return any(a.lower() in haystack or a.lower().replace(" ", "") in compact for a in self.aliases)
