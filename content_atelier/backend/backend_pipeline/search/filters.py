"""Search and ledger filters (plan 2.B3, 2.B6, 2.B8): one definition, turned into SQL for moments and for chunks.

Only verified, current moments are ever searched, and only documents that are included and not a copy of another. The
consent filter hides `do_not_use` unless it is asked for by name. Dates need an explicit offset (a naive time would be
read in whatever zone the server happens to use); the window is closed at the start and open at the end, like the
documents list.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ..documents.api import CallType, SourceType
from ..moments.types import CONSENT_STATUSES, SPEAKER_ROLES
from ..moments.types import LEDGER_MOMENT_TYPES as MOMENT_TYPES

SpeakerRole = Literal["staff", "client", "prospect", "vendor", "outside", "ai_agent", "unknown"]
MomentType = Literal["result", "objection", "decision", "tension", "mechanism", "observation", "story", "testimonial", "question",
                     "teaching", "soundbite", "data_point", "human_line", "counter_expected_decision", "team_practice"]
ConsentStatus = Literal["cleared", "anonymise", "internal_only", "do_not_use"]
# What a search or the ledger shows when no consent status is asked for: everything a person may read internally.
DEFAULT_CONSENT: tuple[str, ...] = ("cleared", "anonymise", "internal_only")
# Filters that only a moment can satisfy (a chunk has no type and no topic).
MOMENT_ONLY = ("moment_type", "topic_id")

assert set(SPEAKER_ROLES) == set(SpeakerRole.__args__) and set(MOMENT_TYPES) == set(MomentType.__args__)  # type: ignore[attr-defined]
assert set(CONSENT_STATUSES) == set(ConsentStatus.__args__)  # type: ignore[attr-defined]


def aware(value: datetime | None) -> datetime | None:
    if value is not None and value.tzinfo is None:
        raise ValueError("Give dates with an explicit offset, such as 2026-03-09T00:00:00-05:00")
    return value


class SearchFilters(BaseModel):
    """What a search, the ledger or its facets are narrowed to. Lists are alternatives within one filter; filters combine with AND."""
    model_config = ConfigDict(extra="forbid")
    date_from: datetime | None = Field(default=None, description="Closed start of the window; an explicit offset is required")
    date_to: datetime | None = Field(default=None, description="Open end of the window; an explicit offset is required")
    client_id: str | None = Field(default=None, max_length=140)
    source_type: SourceType | None = None
    call_type: CallType | None = None
    speaker_role: list[SpeakerRole] = Field(default_factory=list, max_length=7)
    moment_type: list[MomentType] = Field(default_factory=list, max_length=12)
    consent_status: list[ConsentStatus] | None = Field(
        default=None, max_length=4, description="Default: cleared, anonymise and internal_only. do_not_use only when named")
    topic_id: str | None = Field(default=None, max_length=140)
    document_ids: list[str] = Field(default_factory=list, max_length=200)

    @field_validator("date_from", "date_to")
    @classmethod
    def _offset(cls, value):
        return aware(value)

    @field_validator("speaker_role", "moment_type", "document_ids")
    @classmethod
    def _unique(cls, value):
        return list(dict.fromkeys(value))

    @field_validator("consent_status")
    @classmethod
    def _unique_consent(cls, value):
        return None if value is None else list(dict.fromkeys(value))

    @model_validator(mode="after")
    def _window(self):
        if self.date_from and self.date_to and self.date_from >= self.date_to:
            raise ValueError("date_from must be before date_to")
        return self

    @property
    def consent(self) -> list[str]:
        return list(self.consent_status) if self.consent_status else list(DEFAULT_CONSENT)

    @property
    def consent_defaulted(self) -> bool:
        return not self.consent_status

    def moment_only(self) -> list[str]:
        return [name for name in MOMENT_ONLY if getattr(self, name)]


def resolve_topic(conn, topic_id: str | None) -> str | None:
    """A topic that was merged into another is the other: an old link or a saved filter keeps working."""
    seen = set()
    while topic_id and topic_id not in seen:
        seen.add(topic_id)
        row = conn.execute("SELECT status,merged_into FROM topics WHERE topic_id=%s", (topic_id,)).fetchone()
        if row is None or row["status"] != "merged" or not row["merged_into"]:
            return topic_id
        topic_id = row["merged_into"]
    return topic_id


def moment_conditions(filters: SearchFilters, *, topic_id: str | None, verified: bool | None = True, current: bool | None = True,
                      extractor_version: str | None = None, documentless: bool = False,
                      consent: list[str] | None = None) -> tuple[list[str], dict]:
    """WHERE conditions over `key_moments m JOIN transcripts t` (and `clients c`), with named parameters.

    `verified` and `current` are True for search; the ledger may ask for either state or (None) both. The ledger joins documents
    on the left (`documentless`), because an unverified draft loaded from an earlier run may not name its document."""
    where = ["(t.transcript_id IS NULL OR (t.included AND t.canonical_document_id IS NULL))"] if documentless         else ["t.included", "t.canonical_document_id IS NULL"]
    args: dict = {}
    if verified is not None:
        where.append("m.quote_verified" if verified else "NOT m.quote_verified")
    if current is not None:
        where.append("m.is_current" if current else "NOT m.is_current")
    if extractor_version:
        where.append("m.extractor_version = %(extractor_version)s")
        args["extractor_version"] = extractor_version
    if filters.date_from:
        where.append("COALESCE(m.occurred_at, t.occurred_at) >= %(date_from)s")
        args["date_from"] = filters.date_from
    if filters.date_to:
        where.append("COALESCE(m.occurred_at, t.occurred_at) < %(date_to)s")
        args["date_to"] = filters.date_to
    for column, name in (("m.client_id", "client_id"), ("t.source_type", "source_type"), ("t.call_type", "call_type")):
        if getattr(filters, name):
            where.append(f"{column} = %({name})s")
            args[name] = getattr(filters, name)
    for column, name in (("m.speaker_role", "speaker_role"), ("m.moment_type", "moment_type")):
        if getattr(filters, name):
            where.append(f"{column} = ANY(%({name})s)")
            args[name] = list(getattr(filters, name))
    where.append("m.consent_status = ANY(%(consent)s)")
    args["consent"] = consent if consent is not None else filters.consent
    if filters.topic_id:
        where.append("EXISTS (SELECT 1 FROM moment_topics mt WHERE mt.moment_id = m.moment_id AND mt.topic_id = %(topic_id)s)")
        args["topic_id"] = topic_id or filters.topic_id
    if filters.document_ids:
        where.append("m.document_id = ANY(%(document_ids)s)")
        args["document_ids"] = list(filters.document_ids)
    return where, args


def chunk_conditions(filters: SearchFilters) -> tuple[list[str], dict]:
    """WHERE conditions over `transcript_chunks k JOIN transcripts t LEFT JOIN clients c`, with named parameters.

    A chunk has no type or topic, so those filters never reach here (the caller rejects or skips them). Its consent is the
    document-level one: `do_not_use` for a client who must not be used, `anonymise` for everyone else."""
    where = ["k.is_current", "t.included", "t.canonical_document_id IS NULL"]
    args: dict = {}
    if filters.date_from:
        where.append("COALESCE(k.occurred_at, t.occurred_at) >= %(date_from)s")
        args["date_from"] = filters.date_from
    if filters.date_to:
        where.append("COALESCE(k.occurred_at, t.occurred_at) < %(date_to)s")
        args["date_to"] = filters.date_to
    for column, name in (("t.client_id", "client_id"), ("t.source_type", "source_type"), ("t.call_type", "call_type")):
        if getattr(filters, name):
            where.append(f"{column} = %({name})s")
            args[name] = getattr(filters, name)
    if filters.speaker_role:
        where.append("CASE WHEN jsonb_typeof(k.speaker_roles) = 'array' THEN EXISTS (SELECT 1 FROM "
                     "jsonb_array_elements(k.speaker_roles) s WHERE s->>'role' = ANY(%(speaker_role)s)) ELSE false END")
        args["speaker_role"] = list(filters.speaker_role)
    where.append("(CASE WHEN c.consent = 'no_use' THEN 'do_not_use' ELSE 'anonymise' END) = ANY(%(consent)s)")
    args["consent"] = filters.consent
    if filters.document_ids:
        where.append("k.transcript_id = ANY(%(document_ids)s)")
        args["document_ids"] = list(filters.document_ids)
    return where, args


def csv_values(name: str, text: str | None, allowed: tuple[str, ...]) -> list[str]:
    """A comma-separated query parameter (`speaker_role=client,prospect`), checked against its closed set. The Node relay allows each
    query parameter once, so a list travels as one."""
    if not text:
        return []
    values = [part.strip() for part in text.split(",") if part.strip()]
    bad = [v for v in values if v not in allowed]
    if bad:
        raise ValueError(f"{name}: unknown value {bad[0]!r}; use any of {', '.join(allowed)}")
    return list(dict.fromkeys(values))
