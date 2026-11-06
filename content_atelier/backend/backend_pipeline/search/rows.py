"""The rows search, the ledger and the citation read: a moment or chunk joined to its document and client, its anchor passages
with their text, and its topics. SQL only; nothing here calls a model."""
from __future__ import annotations

from .citation import CitationError, chunk_citation, moment_citation
from .models import ChunkSpeaker, ChunkSummary, MomentSummary, TopicRef

MOMENT_FROM = """FROM key_moments m JOIN transcripts t ON t.transcript_id = m.document_id LEFT JOIN clients c ON c.client_id = m.client_id"""
MOMENT_COLUMNS = """m.moment_id, m.document_id, t.title AS document_title, t.source_type, t.call_type, t.source_url, t.source_metadata,
    t.week_id, t.occurred_at AS document_occurred_at, m.occurred_at, m.moment_type, m.moment_body, m.evidence_refs, m.speaker_label,
    m.speaker_id, m.speaker_role, m.evidence_kind, m.client_id, c.name AS client_name, m.consent_status, m.sensitivity,
    m.destination, m.quote_verified, m.is_current, m.extractor_version, m.checks, m.quote_repair, m.unverified_reason"""
MOMENT_SQL = f"SELECT {MOMENT_COLUMNS} {MOMENT_FROM}"

CHUNK_FROM = """FROM transcript_chunks k JOIN transcripts t ON t.transcript_id = k.transcript_id LEFT JOIN clients c ON c.client_id = t.client_id"""
CHUNK_COLUMNS = """k.chunk_id, k.transcript_id, k.chunk_text, k.header, k.passage_refs, k.speaker_roles, k.occurred_at,
    t.title AS document_title, t.source_type, t.call_type, t.source_url, t.source_metadata, t.speaker_map, t.client_id,
    c.name AS client_name, c.consent AS client_consent, t.occurred_at AS document_occurred_at"""
CHUNK_SQL = f"SELECT {CHUNK_COLUMNS} {CHUNK_FROM}"


def moment_rows(conn, moment_ids: list[str]) -> dict[str, dict]:
    rows = conn.execute(f"{MOMENT_SQL} WHERE m.moment_id = ANY(%s)", (moment_ids,)).fetchall()
    return {r["moment_id"]: r for r in rows}


def anchors(conn, moment_ids: list[str]) -> dict[str, list[dict]]:
    """Each moment's anchor passages, in document order: id, character range, text, timestamps and speaker. The range a moment
    recorded must equal the document's passage map; one that does not is left out (so no citation can be built from it)."""
    found: dict[str, list[dict]] = {}
    for r in conn.execute("""SELECT m.moment_id, ref->>'passage_id' AS passage_id, (ref->>'start')::int AS start, (ref->>'end')::int AS "end",
            substr(t.original_text, (ref->>'start')::int + 1, (ref->>'end')::int - (ref->>'start')::int) AS text,
            (p.x->>'start')::int AS map_start, (p.x->>'end')::int AS map_end, (p.x->>'start_ms')::int AS start_ms,
            (p.x->>'end_ms')::int AS end_ms, p.x->>'speaker' AS speaker, (p.x->>'ordinal')::int AS ordinal
        FROM key_moments m JOIN transcripts t ON t.transcript_id = m.document_id
        CROSS JOIN LATERAL jsonb_array_elements(m.evidence_refs) WITH ORDINALITY AS e(ref, n)
        LEFT JOIN LATERAL (SELECT x FROM jsonb_array_elements(t.passage_map) x WHERE x->>'passage_id' = ref->>'passage_id' LIMIT 1) p ON true
        WHERE m.moment_id = ANY(%s) AND ref->'roles' ? 'anchor' AND ref->>'transcript_id' = m.document_id
        ORDER BY m.moment_id, (p.x->>'ordinal')::int NULLS LAST, e.n""", (moment_ids,)):
        if r["map_start"] != r["start"] or r["map_end"] != r["end"]:
            continue
        found.setdefault(r["moment_id"], []).append({k: r[k] for k in ("passage_id", "start", "end", "text", "start_ms", "end_ms", "speaker")})
    return found


def topics_of(conn, moment_ids: list[str]) -> dict[str, list[TopicRef]]:
    out: dict[str, list[TopicRef]] = {}
    for r in conn.execute("""SELECT mt.moment_id, tp.topic_id, tp.name FROM moment_topics mt JOIN topics tp USING (topic_id)
        WHERE mt.moment_id = ANY(%s) ORDER BY mt.moment_id, tp.name, tp.topic_id""", (moment_ids,)):
        out.setdefault(r["moment_id"], []).append(TopicRef(topic_id=r["topic_id"], name=r["name"]))
    return out


def moment_summary(row: dict, topics: list[TopicRef]) -> MomentSummary:
    body = row["moment_body"] or {}
    qualifications = body.get("qualifications")
    return MomentSummary(
        moment_id=row["moment_id"], document_id=row["document_id"], document_title=row["document_title"],
        source_type=row["source_type"], call_type=row["call_type"], moment_type=row["moment_type"] or body.get("moment_type"),
        quote=body.get("quote"), context_summary=body.get("context_summary"), record=body.get("proposition"),
        qualifications=[q for q in qualifications if isinstance(q, str)] if isinstance(qualifications, list) else [],
        speaker_label=row["speaker_label"], speaker_role=row["speaker_role"], evidence_kind=row["evidence_kind"],
        client_id=row["client_id"], client_name=row["client_name"], consent_status=row["consent_status"],
        sensitivity=row["sensitivity"], destination=row["destination"], quote_verified=row["quote_verified"],
        is_current=row["is_current"], occurred_at=row["occurred_at"] or row["document_occurred_at"],
        extractor_version=row["extractor_version"], topics=topics)


def moment_hits(conn, moment_ids: list[str]) -> dict[str, tuple[MomentSummary, object]]:
    """Summary and citation for each moment whose citation can be built; a moment that cannot be located is absent."""
    rows = moment_rows(conn, moment_ids)
    found, topics, built = anchors(conn, list(rows)), topics_of(conn, list(rows)), {}
    for moment_id, row in rows.items():
        try:
            citation = moment_citation(row, found.get(moment_id, []))
        except CitationError:
            continue
        built[moment_id] = (moment_summary(row, topics.get(moment_id, [])), citation)
    return built


def chunk_hits(conn, chunk_ids: list[str]) -> dict[str, tuple[ChunkSummary, object]]:
    rows = {r["chunk_id"]: r for r in conn.execute(f"{CHUNK_SQL} WHERE k.chunk_id = ANY(%s)", (chunk_ids,)).fetchall()}
    wanted = {(r["transcript_id"], ref["passage_id"]) for r in rows.values() for ref in r["passage_refs"] or []}
    passages: dict[tuple[str, str], dict] = {}
    if wanted:
        for p in conn.execute("""SELECT t.transcript_id, p.x AS passage FROM transcripts t, jsonb_array_elements(t.passage_map) p(x)
                WHERE t.transcript_id = ANY(%s) AND p.x->>'passage_id' = ANY(%s)""",
                              (sorted({d for d, _ in wanted}), sorted({i for _, i in wanted}))):
            passages[(p["transcript_id"], p["passage"]["passage_id"])] = p["passage"]
    built = {}
    for chunk_id, row in rows.items():
        refs = row["passage_refs"] or []
        members = [passages.get((row["transcript_id"], ref["passage_id"])) for ref in refs]
        if not refs or any(m is None or (m["start"], m["end"]) != (ref["start"], ref["end"]) for m, ref in zip(members, refs, strict=True)):
            continue
        start, end = min(r["start"] for r in refs), max(r["end"] for r in refs)
        text = conn.execute("SELECT substr(original_text, %s, %s) AS t FROM transcripts WHERE transcript_id = %s",
                            (start + 1, end - start, row["transcript_id"])).fetchone()["t"]
        try:
            citation = chunk_citation(row, members, text)
        except CitationError:
            continue
        header, body = row["header"], row["chunk_text"]
        if header and body.startswith(header):
            body = body[len(header):].lstrip("\n")
        roles = [ChunkSpeaker(name=s["name"], role=s["role"]) for s in (row["speaker_roles"] or []) if isinstance(s, dict) and "name" in s and "role" in s]
        built[chunk_id] = (ChunkSummary(chunk_id=chunk_id, document_id=row["transcript_id"], document_title=row["document_title"],
                                        header=header, text=body, occurred_at=row["occurred_at"] or row["document_occurred_at"],
                                        speaker_roles=roles), citation)
    return built
