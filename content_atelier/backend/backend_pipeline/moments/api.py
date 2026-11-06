"""The moments ledger API (plan 2.B8) and the topic registry routes (2.B7).

GET  /storage/moments                  the ledger: filters (the search filters, plus q, quote_verified, is_current, extractor_version),
                                       pagination (limit 1..200, offset) and a stable order, newest first then moment id
GET  /storage/moments/facets           counts for the filter controls, each dimension counted under the other filters
GET  /storage/moments/{id}             one moment: the scene, its verified quote and citation, the passages around it, speaker and
                                       role, timestamp, recording link, consent, topics, checks, repair record and the cards that cite it
POST /storage/moments/{id}/topics      a person adds or removes topics (an editor)

GET  /storage/topics                   topics with their mention statistics
GET  /storage/topics/{id}              one topic: statistics, recent moments, what was merged into it, its audit trail
POST /storage/topics/{id}/rename|merge|block|unblock     administrator actions (an approver), each audited in `decisions`

Reading is open to any signed-in role. A moment is never written here except its topic links. Consent status is computed by the
backend (migration 008, moments/checks.py) and shown as it is stored: the browser never decides whether a quote is usable.
`GET /moments/{id}` answers the shape the card screens already read (`moment`, `passages`) and adds the ledger's fields.
"""
from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal

from fastapi import Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from ..documents.api import CallType, SourceType
from ..search import rows
from ..search.citation import Citation, CitationError, moment_citation, recording_url
from ..search.filters import CONSENT_STATUSES, MOMENT_TYPES, SPEAKER_ROLES, SearchFilters, csv_values, moment_conditions, resolve_topic
from ..search.models import Answer, MomentSummary, TopicRef
from . import topics as registry

SURROUNDING = 4  # passages shown either side of the cited ones
LEDGER_FROM = """FROM key_moments m LEFT JOIN transcripts t ON t.transcript_id = m.document_id LEFT JOIN clients c ON c.client_id = m.client_id"""
Tri = Literal["true", "false", "any"]


# ---- response models ------------------------------------------------------------------------------------------------------------


class MomentList(Answer):
    items: list[MomentSummary]
    total: int
    limit: int
    offset: int


class FacetCount(Answer):
    value: str
    label: str | None
    count: int


class MomentFacets(Answer):
    total: int
    moment_types: list[FacetCount]
    speaker_roles: list[FacetCount]
    consent_statuses: list[FacetCount]
    clients: list[FacetCount]
    source_types: list[FacetCount]
    call_types: list[FacetCount]
    earliest: datetime | None
    latest: datetime | None


class SceneBody(Answer):
    """The moment's stored body: the scene fields the extractors write. Fields an extractor adds beyond these pass through."""
    model_config = ConfigDict(extra="allow", json_schema_serialization_defaults_required=True)
    quote: str | None = None
    context_summary: str | None = None
    proposition: str | None = None
    moment_type: str | None = None
    qualifications: list[str] = Field(default_factory=list)
    claim_status: str | None = None
    sensitivity: str | None = None
    reasons: list[str] = Field(default_factory=list)
    discovery: dict[str, Any] | None = None


class MomentRow(Answer):
    moment_id: str
    week_id: str | None
    run_id: str | None
    moment_body: SceneBody
    evidence_refs: list[dict[str, Any]]


class EvidencePassage(Answer):
    """A passage the moment cites, with its role in the scene (`anchor` holds the quote, `context` frames it)."""
    transcript_id: str
    passage_id: str
    start: int
    end: int
    roles: list[str]
    text: str
    title: str
    speaker: str | None
    speaker_role: str | None
    start_ms: int | None
    end_ms: int | None
    source_url: str | None


class SurroundingPassage(Answer):
    passage_id: str
    ordinal: int
    start: int
    end: int
    speaker: str | None
    speaker_role: str | None
    start_ms: int | None
    end_ms: int | None
    text: str
    cited: bool
    anchor: bool


class DocumentRef(Answer):
    document_id: str
    title: str
    source_type: str
    call_type: str | None
    occurred_at: datetime | None
    recording_url: str | None


class MomentTopic(Answer):
    topic_id: str
    name: str
    assigned_by: str
    similarity: float | None


class CitingCard(Answer):
    angle_id: str
    week_id: str
    title: str | None
    evidence_role: str
    approval_status: str
    selection_status: str


class MomentDetail(Answer):
    moment: MomentRow
    passages: list[EvidencePassage]
    summary: MomentSummary
    citation: Citation | None
    document: DocumentRef | None
    surrounding: list[SurroundingPassage]
    evidence_intact: bool
    topics: list[MomentTopic]
    checks: dict[str, Any]
    quote_repair: dict[str, Any] | None
    unverified_reason: str | None
    cards: list[CitingCard]


class TopicSummary(Answer):
    topic_id: str
    name: str
    description: str | None
    pillars: list[str]
    status: Literal["active", "blocked", "merged"]
    merged_into: str | None
    origin: Literal["model", "person"]
    created_by: str | None
    created_at: datetime
    updated_at: datetime
    embedded: bool
    total_mentions: int
    mentions_30d: int
    mentions_90d: int
    mentions_365d: int
    distinct_clients: int
    last_mentioned_at: datetime | None


class TopicList(Answer):
    items: list[TopicSummary]
    total: int
    limit: int
    offset: int
    counts: dict[str, int]


class TopicDecision(Answer):
    decision_id: str
    action: str
    actor: str
    note: str | None
    created_at: datetime
    details: dict[str, Any]


class TopicDetail(TopicSummary):
    merged_from: list[TopicRef]
    moments: list[MomentSummary]
    history: list[TopicDecision]


class MomentTopics(Answer):
    moment_id: str
    topics: list[MomentTopic]


class Payload(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RenameRequest(Payload):
    name: str = Field(min_length=3, max_length=80)
    description: str | None = Field(default=None, max_length=300)
    note: str | None = Field(default=None, max_length=500)


class MergeRequest(Payload):
    into_topic_id: str = Field(min_length=1, max_length=140)
    note: str | None = Field(default=None, max_length=500)


class NoteRequest(Payload):
    note: str | None = Field(default=None, max_length=500)


class MomentTopicsRequest(Payload):
    add: list[str] = Field(default_factory=list, max_length=10)
    remove: list[str] = Field(default_factory=list, max_length=10)
    note: str | None = Field(default=None, max_length=500)


# ---- the ledger -------------------------------------------------------------------------------------------------------------------


def _tri(value: str) -> bool | None:
    return None if value == "any" else value == "true"


def ledger_filters(**given) -> SearchFilters:
    """The filters a ledger query carries, as one checked object; a bad value is a 422, not a 500."""
    try:
        return SearchFilters(
            date_from=given.get("date_from"), date_to=given.get("date_to"), client_id=given.get("client_id"),
            source_type=given.get("source_type"), call_type=given.get("call_type"),
            speaker_role=csv_values("speaker_role", given.get("speaker_role"), SPEAKER_ROLES),
            moment_type=csv_values("moment_type", given.get("moment_type"), MOMENT_TYPES),
            consent_status=csv_values("consent_status", given.get("consent_status"), CONSENT_STATUSES) or None,
            topic_id=given.get("topic_id"), document_ids=[given["document_id"]] if given.get("document_id") else [])
    except (ValueError, ValidationError) as exc:
        raise HTTPException(422, str(exc)) from exc


def _like(text: str) -> str:
    return "%" + text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


def _where(conn, filters: SearchFilters, *, q, verified, current, extractor_version, consent=None):
    where, args = moment_conditions(filters, topic_id=resolve_topic(conn, filters.topic_id), verified=verified, current=current,
                                    extractor_version=extractor_version, documentless=True, consent=consent)
    if q:
        where.append("(m.tsv @@ websearch_to_tsquery('english', %(q)s) OR m.moment_body->>'quote' ILIKE %(like)s)")
        args.update(q=q, like=_like(q))
    return " WHERE " + " AND ".join(where), args


def list_moments(repo, filters: SearchFilters, *, q=None, verified=True, current=True, extractor_version=None, limit=50, offset=0) -> dict:
    with repo.connection() as conn:
        where, args = _where(conn, filters, q=q, verified=verified, current=current, extractor_version=extractor_version)
        total = conn.execute(f"SELECT count(*) n {LEDGER_FROM}{where}", args).fetchone()["n"]
        found = conn.execute(f"""SELECT {rows.MOMENT_COLUMNS} {LEDGER_FROM}{where}
            ORDER BY COALESCE(m.occurred_at, t.occurred_at) DESC NULLS LAST, m.moment_id LIMIT %(limit)s OFFSET %(offset)s""",
                             {**args, "limit": limit, "offset": offset}).fetchall()
        topics = rows.topics_of(conn, [r["moment_id"] for r in found])
    return {"items": [rows.moment_summary(r, topics.get(r["moment_id"], [])) for r in found], "total": total, "limit": limit,
            "offset": offset}


DIMENSIONS = (  # facet, filter it ignores, value, label
    ("moment_types", "moment_type", "m.moment_type", "NULL"),
    ("speaker_roles", "speaker_role", "m.speaker_role", "NULL"),
    ("consent_statuses", "consent_status", "m.consent_status", "NULL"),
    ("clients", "client_id", "m.client_id", "c.name"),
    ("source_types", "source_type", "t.source_type", "NULL"),
    ("call_types", "call_type", "t.call_type", "NULL"),
)


def facets(repo, filters: SearchFilters, *, q=None, verified=True, current=True, extractor_version=None) -> dict:
    """Each dimension is counted under every other filter, so a control shows what choosing another value would leave. Consent counts
    include do_not_use, which the list hides until it is asked for."""
    out: dict = {}
    with repo.connection() as conn:
        for name, ignored, value, label in DIMENSIONS:
            narrowed = filters.model_copy(update={ignored: [] if isinstance(getattr(filters, ignored), list) else None})
            where, args = _where(conn, narrowed, q=q, verified=verified, current=current, extractor_version=extractor_version,
                                 consent=list(CONSENT_STATUSES) if ignored == "consent_status" else None)
            out[name] = [{"value": r["value"], "label": r["label"], "count": r["count"]} for r in conn.execute(
                f"""SELECT {value} AS value, {label} AS label, count(*) AS count {LEDGER_FROM}{where} AND {value} IS NOT NULL
                    GROUP BY 1, 2 ORDER BY count DESC, value""", args)]
        undated = filters.model_copy(update={"date_from": None, "date_to": None})
        where, args = _where(conn, undated, q=q, verified=verified, current=current, extractor_version=extractor_version)
        span = conn.execute(f"""SELECT min(COALESCE(m.occurred_at, t.occurred_at)) AS earliest,
            max(COALESCE(m.occurred_at, t.occurred_at)) AS latest {LEDGER_FROM}{where}""", args).fetchone()
        where, args = _where(conn, filters, q=q, verified=verified, current=current, extractor_version=extractor_version)
        total = conn.execute(f"SELECT count(*) n {LEDGER_FROM}{where}", args).fetchone()["n"]
    return {**out, "total": total, "earliest": span["earliest"], "latest": span["latest"]}


def _passage_role(document: dict, speaker: str | None) -> str | None:
    mapped = (document["speaker_map"] or {}).get(speaker or "") if speaker else None
    return mapped.get("role") if isinstance(mapped, dict) else None


def get_moment(repo, moment_id: str) -> dict:
    with repo.connection() as conn:
        row = conn.execute(f"SELECT {rows.MOMENT_COLUMNS}, m.week_id AS moment_week_id, m.run_id AS moment_run_id {LEDGER_FROM} "
                           "WHERE m.moment_id = %s", (moment_id,)).fetchone()
        if row is None:
            raise LookupError("Moment not found")
        refs = [r for r in (row["evidence_refs"] or []) if isinstance(r, dict) and r.get("transcript_id")]
        wanted = sorted({r["transcript_id"] for r in refs} | ({row["document_id"]} if row["document_id"] else set()))
        documents = {d["transcript_id"]: d for d in conn.execute(
            """SELECT transcript_id, title, source_type, source_url, source_metadata, original_text, passage_map, speaker_map
               FROM transcripts WHERE transcript_id = ANY(%s)""", (wanted,))}
        topics = rows.topics_of(conn, [moment_id])
        assigned = conn.execute("""SELECT tp.topic_id, tp.name, mt.assigned_by, mt.similarity FROM moment_topics mt JOIN topics tp USING (topic_id)
            WHERE mt.moment_id = %s ORDER BY tp.name, tp.topic_id""", (moment_id,)).fetchall()
        cards = conn.execute("""SELECT a.angle_id, a.week_id, COALESCE(a.content_body->'card'->>'title', a.content_body->>'title') AS title,
                am.evidence_role, a.approval_status, a.selection_status FROM angle_moments am JOIN content_angles a USING (angle_id)
            WHERE am.moment_id = %s ORDER BY a.created_at DESC, a.angle_id""", (moment_id,)).fetchall()
        anchors = rows.anchors(conn, [moment_id]).get(moment_id, [])
    intact, evidence = True, []
    for ref in refs:
        document = documents.get(ref["transcript_id"])
        passage = next((p for p in document["passage_map"] if p["passage_id"] == ref.get("passage_id")), None) if document else None
        if passage is None or (passage["start"], passage["end"]) != (ref.get("start"), ref.get("end")):
            intact = False  # a reference that no longer matches the original is left out, and the answer says so
            continue
        evidence.append({"transcript_id": ref["transcript_id"], "passage_id": ref["passage_id"], "start": ref["start"], "end": ref["end"],
                         "roles": [r for r in (ref.get("roles") or []) if isinstance(r, str)],
                         "text": document["original_text"][ref["start"]:ref["end"]], "title": document["title"],
                         "speaker": passage.get("speaker"), "speaker_role": _passage_role(document, passage.get("speaker")),
                         "start_ms": passage.get("start_ms"), "end_ms": passage.get("end_ms"),
                         "source_url": recording_url(document["source_type"], document["source_url"], document["source_metadata"])})
    home = documents.get(row["document_id"] or (refs[0]["transcript_id"] if refs else ""))
    surrounding = []
    if home is not None:
        cited = {r["passage_id"] for r in evidence if r["transcript_id"] == home["transcript_id"]}
        anchored = {r["passage_id"] for r in evidence if r["transcript_id"] == home["transcript_id"] and "anchor" in r["roles"]}
        ordinals = [p["ordinal"] for p in home["passage_map"] if p["passage_id"] in cited]
        if ordinals:
            low, high = min(ordinals) - SURROUNDING, max(ordinals) + SURROUNDING
            for p in home["passage_map"]:
                if low <= p["ordinal"] <= high:
                    surrounding.append({"passage_id": p["passage_id"], "ordinal": p["ordinal"], "start": p["start"], "end": p["end"],
                                        "speaker": p.get("speaker"), "speaker_role": _passage_role(home, p.get("speaker")),
                                        "start_ms": p.get("start_ms"), "end_ms": p.get("end_ms"),
                                        "text": home["original_text"][p["start"]:p["end"]], "cited": p["passage_id"] in cited,
                                        "anchor": p["passage_id"] in anchored})
    citation = None
    if row["quote_verified"]:
        try:
            citation = moment_citation(row, anchors)
        except CitationError:
            intact = False
    body = row["moment_body"] if isinstance(row["moment_body"], dict) else {}
    document = None
    if home is not None and row["document_id"]:
        document = {"document_id": home["transcript_id"], "title": home["title"], "source_type": home["source_type"],
                    "call_type": row["call_type"], "occurred_at": row["document_occurred_at"],
                    "recording_url": recording_url(home["source_type"], home["source_url"], home["source_metadata"])}
    return {"moment": {"moment_id": moment_id, "week_id": row["moment_week_id"], "run_id": row["moment_run_id"], "moment_body": body,
                       "evidence_refs": row["evidence_refs"] or []},
            "passages": evidence, "summary": rows.moment_summary(row, topics.get(moment_id, [])), "citation": citation,
            "document": document, "surrounding": surrounding, "evidence_intact": intact, "topics": assigned,
            "checks": row["checks"] or {}, "quote_repair": row["quote_repair"], "unverified_reason": row["unverified_reason"],
            "cards": cards}


# ---- topics ------------------------------------------------------------------------------------------------------------------------


def get_topic_detail(repo, topic_id: str) -> dict:
    with repo.connection() as conn:
        stats = registry.statistics(conn, topic_id)
        ids = registry.moment_ids(conn, topic_id, 20)
        found = conn.execute(f"SELECT {rows.MOMENT_COLUMNS} {LEDGER_FROM} WHERE m.moment_id = ANY(%s)", (ids,)).fetchall()
        by_id = {r["moment_id"]: r for r in found}
        topics = rows.topics_of(conn, ids)
        merged_from = [TopicRef(topic_id=r["topic_id"], name=r["name"]) for r in conn.execute(
            "SELECT topic_id, name FROM topics WHERE merged_into = %s ORDER BY name, topic_id", (topic_id,))]
        history = conn.execute("""SELECT decision_id, action, actor, note, created_at, details FROM decisions
            WHERE item_kind = %s AND (item_id = %s OR details->>'into' = %s) ORDER BY created_at DESC, decision_id""",
                               (registry.AUDIT_KIND, topic_id, topic_id)).fetchall()
    return {**stats, "merged_from": merged_from, "history": history,
            "moments": [rows.moment_summary(by_id[i], topics.get(i, [])) for i in ids if i in by_id]}


def topic_summary(repo, topic_id: str) -> dict:
    with repo.connection() as conn:
        return registry.statistics(conn, topic_id)


def install(routes, repo, decider, reader, action):
    def filters_from(**given):
        return ledger_filters(**given)

    @routes.get("/moments", response_model=MomentList)
    def moments(
        q: Annotated[str | None, Query(max_length=200)] = None, client_id: Annotated[str | None, Query(max_length=140)] = None,
        source_type: SourceType | None = None, call_type: CallType | None = None,
        speaker_role: Annotated[str | None, Query(max_length=200, description="Comma-separated: " + ", ".join(SPEAKER_ROLES))] = None,
        moment_type: Annotated[str | None, Query(max_length=300, description="Comma-separated: " + ", ".join(MOMENT_TYPES))] = None,
        consent_status: Annotated[str | None, Query(max_length=100, description="Comma-separated; default excludes do_not_use")] = None,
        topic_id: Annotated[str | None, Query(max_length=140)] = None, document_id: Annotated[str | None, Query(max_length=140)] = None,
        from_: Annotated[datetime | None, Query(alias="from")] = None, to: datetime | None = None,
        quote_verified: Tri = "true", is_current: Tri = "true", extractor_version: Annotated[str | None, Query(max_length=100)] = None,
        limit: int = Query(default=50, ge=1, le=200), offset: int = Query(default=0, ge=0, le=1000000),
        subject: str = Depends(reader),
    ):
        filters = filters_from(date_from=from_, date_to=to, client_id=client_id, source_type=source_type, call_type=call_type,
                               speaker_role=speaker_role, moment_type=moment_type, consent_status=consent_status, topic_id=topic_id,
                               document_id=document_id)
        return action(list_moments, repo, filters, q=q, verified=_tri(quote_verified), current=_tri(is_current),
                      extractor_version=extractor_version, limit=limit, offset=offset)

    # Before the `{moment_id}` route below, which would read "facets" as an id.
    @routes.get("/moments/facets", response_model=MomentFacets)
    def moment_facets(
        q: Annotated[str | None, Query(max_length=200)] = None, client_id: Annotated[str | None, Query(max_length=140)] = None,
        source_type: SourceType | None = None, call_type: CallType | None = None,
        speaker_role: Annotated[str | None, Query(max_length=200)] = None, moment_type: Annotated[str | None, Query(max_length=300)] = None,
        consent_status: Annotated[str | None, Query(max_length=100)] = None, topic_id: Annotated[str | None, Query(max_length=140)] = None,
        document_id: Annotated[str | None, Query(max_length=140)] = None,
        from_: Annotated[datetime | None, Query(alias="from")] = None, to: datetime | None = None,
        quote_verified: Tri = "true", is_current: Tri = "true", extractor_version: Annotated[str | None, Query(max_length=100)] = None,
        subject: str = Depends(reader),
    ):
        filters = filters_from(date_from=from_, date_to=to, client_id=client_id, source_type=source_type, call_type=call_type,
                               speaker_role=speaker_role, moment_type=moment_type, consent_status=consent_status, topic_id=topic_id,
                               document_id=document_id)
        return action(facets, repo, filters, q=q, verified=_tri(quote_verified), current=_tri(is_current),
                      extractor_version=extractor_version)

    @routes.get("/moments/{moment_id}", response_model=MomentDetail)
    def moment(moment_id: str, subject: str = Depends(reader)):
        return action(get_moment, repo, moment_id)

    @routes.post("/moments/{moment_id}/topics", response_model=MomentTopics)
    def moment_topics(moment_id: str, payload: MomentTopicsRequest, subject: str = Depends(decider)):
        if not payload.add and not payload.remove:
            raise HTTPException(422, "Name a topic to add or to remove")
        if set(payload.add) & set(payload.remove):
            raise HTTPException(422, "A topic cannot be both added and removed")
        done = action(registry.as_editor, repo, subject, registry.assign_by_person, moment_id, payload.add, payload.remove,
                      note=payload.note)
        return {"moment_id": moment_id, "topics": done}

    @routes.get("/topics", response_model=TopicList)
    def topics(status: Literal["active", "blocked", "merged"] | None = None, q: Annotated[str | None, Query(max_length=100)] = None,
               limit: int = Query(default=50, ge=1, le=200), offset: int = Query(default=0, ge=0, le=1000000),
               subject: str = Depends(reader)):
        def run():
            with repo.connection() as conn:
                return registry.listing(conn, status=status, q=q, limit=limit, offset=offset)
        return action(run)

    @routes.get("/topics/{topic_id}", response_model=TopicDetail)
    def topic(topic_id: str, subject: str = Depends(reader)):
        return action(get_topic_detail, repo, topic_id)

    @routes.post("/topics/{topic_id}/rename", response_model=TopicSummary)
    def rename(topic_id: str, payload: RenameRequest, subject: str = Depends(decider)):
        def run():
            registry.as_approver(repo, subject, registry.rename, topic_id, payload.name, description=payload.description, note=payload.note)
            return topic_summary(repo, topic_id)
        return action(run)

    @routes.post("/topics/{topic_id}/merge", response_model=TopicSummary)
    def merge(topic_id: str, payload: MergeRequest, subject: str = Depends(decider)):
        def run():
            registry.as_approver(repo, subject, registry.merge, topic_id, payload.into_topic_id, note=payload.note)
            return topic_summary(repo, payload.into_topic_id)
        return action(run)

    @routes.post("/topics/{topic_id}/block", response_model=TopicSummary)
    def block(topic_id: str, payload: NoteRequest, subject: str = Depends(decider)):
        def run():
            registry.as_approver(repo, subject, registry.block, topic_id, note=payload.note)
            return topic_summary(repo, topic_id)
        return action(run)

    @routes.post("/topics/{topic_id}/unblock", response_model=TopicSummary)
    def unblock(topic_id: str, payload: NoteRequest, subject: str = Depends(decider)):
        def run():
            registry.as_approver(repo, subject, registry.unblock, topic_id, note=payload.note)
            return topic_summary(repo, topic_id)
        return action(run)
