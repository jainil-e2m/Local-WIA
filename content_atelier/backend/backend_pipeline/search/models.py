"""Response models shared by the search route and the moments API.

They are strict (every field a model declares is in the schema's required list), so the generated TypeScript types need no
`| undefined`, and they are checked when a route answers.
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class Answer(BaseModel):
    """A response model: every field it declares is in the schema's required list."""
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)


class TopicRef(Answer):
    topic_id: str
    name: str


class MomentSummary(Answer):
    """A moment as the ledger and search show it. `record` is the neutral scene record (or, for earlier moments, the
    proposition); the quote is the exact text of the source when `quote_verified` is true."""
    moment_id: str
    document_id: str | None = None
    document_title: str | None = None
    source_type: str | None = None
    call_type: str | None = None
    moment_type: str | None = None
    quote: str | None = None
    context_summary: str | None = None
    record: str | None = None
    qualifications: list[str]
    speaker_label: str | None = None
    speaker_role: str
    evidence_kind: str
    client_id: str | None = None
    client_name: str | None = None
    consent_status: str
    sensitivity: str | None = None
    destination: str | None = None
    quote_verified: bool
    is_current: bool
    occurred_at: datetime | None = None
    extractor_version: str | None = None
    topics: list[TopicRef]


class ChunkSpeaker(Answer):
    name: str
    role: str


class ChunkSummary(Answer):
    """A transcript chunk: the header names the call, date, type, client and speakers; `text` is the turns."""
    chunk_id: str
    document_id: str
    document_title: str
    header: str | None = None
    text: str
    occurred_at: datetime | None = None
    speaker_roles: list[ChunkSpeaker]
