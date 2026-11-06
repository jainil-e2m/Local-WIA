"""The documents API (plan 1.B8): every document, whatever its source, with filters, pagination and extraction status.

GET  /storage/documents               filters: source_type, call_type, included, extraction_status, date_state, client_id, q,
                                      from, to; pagination: limit (1..200, default 50) and offset
GET  /storage/documents/{id}          one document with its passages (speaker and role) and how it was classified
POST /storage/documents/{id}/classification
                                      a person sets the call type (and may override inclusion); it is never overwritten by a rule
POST /storage/documents/import        an editor uploads one transcript file (a Zoom export or any call file) through the same
                                      import as `documents import` (1.F7); a JSON body, so no multipart parser is needed

A document with no week appears here like any other. Reads are open to any signed-in team member; the one write needs an editor.
"""
from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from fastapi import Depends, HTTPException, Query
from psycopg.types.json import Jsonb
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator

from ..normalise.classify import CALL_TYPES, inclusion
from ..normalise.glossary import Glossary

SourceType = Literal["zoom", "fathom", "slack", "manual", "file", "attachment"]
CallType = Literal["client_1to1", "office_hours", "workshop", "prospect", "internal", "vendor", "fragment", "slack_thread", "other"]
ExtractionStatus = Literal["pending", "queued", "running", "completed", "failed", "not_applicable"]


class Answer(BaseModel):
    """A response model: every field it declares is in the schema's required list, so generated types need no `| undefined`."""
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)


class Participant(Answer):
    model_config = ConfigDict(extra="allow", json_schema_serialization_defaults_required=True)
    name: str | None = None
    role: str
    person_id: str | None = None
    basis: str | None = None
    inferred: bool = False
    passages: int | None = None


class DocumentSummary(Answer):
    transcript_id: str
    title: str
    source_type: str
    upstream_id: str | None = None
    occurred_at: datetime | None = None
    date_source: str | None = None
    date_state: Literal["dated", "undated"]
    call_type: str | None = None
    included: bool
    exclusion_reason: str | None = None
    client_id: str | None = None
    client_name: str | None = None
    participants: list[Participant] = Field(default_factory=list)
    passage_count: int
    word_count: int
    extraction_status: str
    canonical_document_id: str | None = None
    week_id: str | None = None
    ingested_at: datetime
    needs_review: bool = False


class DocumentCounts(Answer):
    by_source_type: dict[str, int]
    by_call_type: dict[str, int]
    included: int
    excluded: int
    undated: int
    needs_review: int = 0


class DocumentList(Answer):
    items: list[DocumentSummary]
    total: int
    limit: int
    offset: int
    counts: DocumentCounts


class DocumentPassage(Answer):
    passage_id: str
    ordinal: int
    speaker: str | None = None
    speaker_role: str | None = None
    start_ms: int | None = None
    text: str


class ClassificationRecord(Answer):
    model_config = ConfigDict(extra="allow", json_schema_serialization_defaults_required=True)
    call_type: str | None = None
    method: str | None = None
    reason: str | None = None
    needs_review: bool = False


class DocumentDetail(DocumentSummary):
    passages: list[DocumentPassage]
    classification: ClassificationRecord | None = None


class ClassificationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    call_type: CallType
    included: bool | None = None
    reason: str = Field(min_length=1, max_length=500)


# A transcript upload: one file's text. Two million characters is a call of many hours.
UPLOAD_CHARACTERS = 2_000_000
UPLOAD_SUFFIXES = (".txt", ".vtt", ".webvtt")


class DocumentUpload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    filename: str = Field(min_length=5, max_length=200)
    content: str = Field(min_length=1, max_length=UPLOAD_CHARACTERS)
    occurred_at: AwareDatetime | None = None
    source_type: Literal["zoom", "manual", "file"] = "zoom"

    @field_validator("filename")
    @classmethod
    def _plain_name(cls, value: str) -> str:
        if any(c in value for c in "/\\:") or any(ord(c) < 32 for c in value) or value.startswith("."):
            raise ValueError("A file name only, without a folder")
        if not value.lower().endswith(UPLOAD_SUFFIXES):
            raise ValueError("A transcript is a .txt, .vtt or .webvtt file")
        return value


class DocumentUploadResult(Answer):
    transcript_id: str
    created: bool
    run_id: str | None = None
    document: DocumentSummary


SUMMARY_SQL = """SELECT t.transcript_id,t.title,t.source_type,t.upstream_id,t.occurred_at,t.occurred_at_source AS date_source,
    COALESCE(t.classification->>'needs_review','false')='true' AS needs_review,
    CASE WHEN t.occurred_at IS NULL THEN 'undated' ELSE 'dated' END AS date_state,t.call_type,t.included,t.exclusion_reason,
    t.client_id,c.name AS client_name,t.participants,jsonb_array_length(t.passage_map) AS passage_count,
    COALESCE(array_length(regexp_split_to_array(btrim(t.original_text), E'\\\\s+'), 1), 0) AS word_count,
    t.extraction_status,t.canonical_document_id,t.week_id,t.ingested_at
    FROM transcripts t LEFT JOIN clients c USING (client_id)"""


def _filters(source_type, call_type, included, extraction_status, date_state, client_id, q, from_, to, glossary, needs_review=None):
    where, args = [], []
    if needs_review is not None:
        where.append(("" if needs_review else "NOT ") + "COALESCE(t.classification->>'needs_review','false')='true'")
    for column, value in (("t.source_type", source_type), ("t.call_type", call_type), ("t.extraction_status", extraction_status),
                          ("t.client_id", client_id)):
        if value is not None:
            where.append(f"{column}=%s")
            args.append(value)
    if included is not None:
        where.append("t.included=%s")
        args.append(included)
    if date_state == "dated":
        where.append("t.occurred_at IS NOT NULL")
    elif date_state == "undated":
        where.append("t.occurred_at IS NULL")
    if from_ is not None:
        where.append("t.occurred_at >= %s")
        args.append(from_)
    if to is not None:
        where.append("t.occurred_at < %s")
        args.append(to)
    if q:
        normal = glossary.normalise(q)
        where.append("(t.title ILIKE %s OR EXISTS (SELECT 1 FROM transcript_chunks k WHERE k.transcript_id=t.transcript_id AND k.is_current "
                     "AND k.tsv @@ websearch_to_tsquery('english', %s)))")
        args.extend([f"%{q}%", normal])
    return (" WHERE " + " AND ".join(where)) if where else "", args


def list_documents(repo, *, source_type=None, call_type=None, included=None, extraction_status=None, date_state=None, client_id=None,
                   q=None, from_=None, to=None, limit=50, offset=0, needs_review=None) -> dict:
    with repo.connection() as conn:
        glossary = Glossary.from_database(conn) if q else None
        where, args = _filters(source_type, call_type, included, extraction_status, date_state, client_id, q, from_, to, glossary,
                               needs_review)
        total = conn.execute(f"SELECT count(*) n FROM transcripts t{where}", args).fetchone()["n"]
        items = conn.execute(f"{SUMMARY_SQL}{where} ORDER BY t.occurred_at DESC NULLS LAST, t.transcript_id LIMIT %s OFFSET %s",
                             [*args, limit, offset]).fetchall()
        by_source = {r["k"]: r["n"] for r in conn.execute("SELECT source_type k,count(*) n FROM transcripts GROUP BY 1")}
        by_call = {r["k"]: r["n"] for r in conn.execute("SELECT COALESCE(call_type,'unclassified') k,count(*) n FROM transcripts GROUP BY 1")}
        flags = conn.execute("""SELECT count(*) FILTER (WHERE included) AS included, count(*) FILTER (WHERE NOT included) AS excluded,
            count(*) FILTER (WHERE occurred_at IS NULL) AS undated,
            count(*) FILTER (WHERE classification->>'needs_review'='true') AS needs_review FROM transcripts""").fetchone()
    return {"items": items, "total": total, "limit": limit, "offset": offset,
            "counts": {"by_source_type": by_source, "by_call_type": by_call, **flags}}


def get_document(repo, transcript_id: str) -> dict:
    with repo.connection() as conn:
        summary = conn.execute(f"{SUMMARY_SQL} WHERE t.transcript_id=%s", (transcript_id,)).fetchone()
        if summary is None:
            raise LookupError("Document not found")
        row = conn.execute("SELECT original_text,passage_map,speaker_map,classification,call_type FROM transcripts WHERE transcript_id=%s",
                           (transcript_id,)).fetchone()
    roles = row["speaker_map"] or {}
    passages = [{"passage_id": p["passage_id"], "ordinal": p["ordinal"], "speaker": p.get("speaker"),
                 "speaker_role": (roles.get(p.get("speaker") or "") or {}).get("role") if row["speaker_map"] else None,
                 "start_ms": p.get("start_ms"), "text": row["original_text"][p["start"]:p["end"]]} for p in row["passage_map"]]
    classification = {"call_type": row["call_type"], **row["classification"]} if row["classification"] else None
    return {**summary, "passages": passages, "classification": classification}


def classify_by_person(repo, transcript_id: str, request: ClassificationRequest, actor: str, models=None) -> dict:
    """A person decides what kind of call this is. The rules and the model never overwrite it."""
    from datetime import UTC
    from psycopg.types.json import Jsonb

    from ..settings_store import value as setting
    from .jobs import normalise
    with repo.connection() as conn:
        row = conn.execute("SELECT transcript_id FROM transcripts WHERE transcript_id=%s FOR UPDATE", (transcript_id,)).fetchone()
        if row is None:
            raise LookupError("Document not found")
        included_types = tuple(setting("documents.included_call_types", conn))
        wanted, why = inclusion(request.call_type, included_types)
        if request.included is not None:
            wanted, why = request.included, (None if request.included else request.reason)
        elif not wanted and request.reason:
            # A person's exclusion carries the person's reason, not the rules' ("Not placed: ... a person decides").
            why = request.reason
        if not wanted and not why:
            why = request.reason
        record = {"method": "person", "reason": request.reason, "decided_by": actor, "decided_at": datetime.now(UTC).isoformat()}
        conn.execute("UPDATE transcripts SET call_type=%s,included=%s,exclusion_reason=%s,classification=%s WHERE transcript_id=%s",
                     (request.call_type, wanted, why, Jsonb(record), transcript_id))
    normalise(repo, transcript_id, models=models)
    return get_document(repo, transcript_id)


def upload_document(repo, upload: DocumentUpload, actor: str) -> dict:
    """One transcript file through `documents import` (1.F7): the same parsing, identity, original storage and normalise job.
    The same file uploaded twice is one document. A date given by the person is recorded as theirs ("manual") on a new
    document only; the normaliser keeps a person's date."""
    import tempfile
    from pathlib import Path

    from .intake import import_directory, text_document
    raw = upload.content.encode("utf-8")
    with tempfile.TemporaryDirectory(prefix="atelier-upload-") as folder:
        path = Path(folder) / upload.filename
        path.write_bytes(raw)
        try:
            transcript_id = text_document(path, raw, upload.source_type)["transcript_id"]
        except (ValueError, KeyError, TypeError) as exc:
            raise ValueError(f"The file could not be read as a transcript: {exc}"[:300]) from exc
        result = import_directory(repo, folder, source_type=upload.source_type, actor=actor)
    if result["failed"]:
        raise ValueError(f"The file could not be imported: {result['failed'][0]['reason']}")
    created = transcript_id in result["transcript_ids"]
    with repo.connection() as conn:
        if created:
            conn.execute("UPDATE transcripts SET source_metadata=source_metadata || %s WHERE transcript_id=%s",
                         (Jsonb({"uploaded_by": actor}), transcript_id))
        if created and upload.occurred_at is not None:
            conn.execute("UPDATE transcripts SET occurred_at=%s,occurred_at_source='manual' WHERE transcript_id=%s",
                         (upload.occurred_at, transcript_id))
        document = conn.execute(f"{SUMMARY_SQL} WHERE t.transcript_id=%s", (transcript_id,)).fetchone()
    return {"transcript_id": transcript_id, "created": created, "run_id": result["run_id"], "document": document}


def install(routes, repo, decider, reader, action):
    from .. import gate_one

    @routes.get("/documents", response_model=DocumentList)
    def documents(
        source_type: SourceType | None = None, call_type: CallType | None = None, included: bool | None = None,
        extraction_status: ExtractionStatus | None = None, date_state: Literal["dated", "undated"] | None = None,
        client_id: Annotated[str | None, Query(max_length=140)] = None, q: Annotated[str | None, Query(max_length=200)] = None,
        from_: Annotated[datetime | None, Query(alias="from")] = None, to: datetime | None = None,
        limit: int = Query(default=50, ge=1, le=200), offset: int = Query(default=0, ge=0, le=1000000),
        needs_review: bool | None = None, subject: str = Depends(reader),
    ):
        return action(list_documents, repo, source_type=source_type, call_type=call_type, included=included,
                      extraction_status=extraction_status, date_state=date_state, client_id=client_id, q=q, from_=from_, to=to,
                      limit=limit, offset=offset, needs_review=needs_review)

    @routes.post("/documents/import", response_model=DocumentUploadResult)
    def upload(payload: DocumentUpload, subject: str = Depends(decider)):
        def run():
            gate_one.require(repo, subject, "edit")
            try:
                return upload_document(repo, payload, subject)
            except ValueError as exc:  # the file is not a transcript: the request's fault, said with the reason
                raise HTTPException(422, str(exc)) from exc
        return action(run)

    @routes.get("/documents/{transcript_id}", response_model=DocumentDetail)
    def document(transcript_id: str, subject: str = Depends(reader)):
        return action(get_document, repo, transcript_id)

    @routes.post("/documents/{transcript_id}/classification", response_model=DocumentDetail)
    def classification(transcript_id: str, payload: ClassificationRequest, subject: str = Depends(decider)):
        def run():
            gate_one.require(repo, subject, "edit")
            if payload.call_type not in CALL_TYPES:
                raise HTTPException(422, "Unknown call type")
            return classify_by_person(repo, transcript_id, payload, subject)
        return action(run)
