"""Extraction health (plan 2.B12): is the archive being turned into moments, and where is it stuck?

    GET /storage/documents/extraction-health

Decision: this is a read of documents, so it lives beside the documents API, not on the intake Sources overview (which is about
connections, buckets and revisions). It is pure SQL: no model, no provider, no file. "Included documents" are those the
classification kept (`included`) and that are not copies of another document, the same set extraction works on.

* counts of included documents by `extraction_status`, and failed documents with the failing job's `error_summary`;
* the oldest document still waiting (pending or queued) and how long it has waited;
* the share of completed documents that produced no scene, and the share of moments whose quote is verified;
* each of those again per source type, so one broken connector shows.
"""
from __future__ import annotations

from datetime import datetime

from fastapi import Depends

from ..search.models import Answer

STATUSES = ("pending", "queued", "running", "completed", "failed", "not_applicable")
FAILED_LIMIT = 50


class ExtractionStats(Answer):
    included_documents: int
    by_status: dict[str, int]
    completed_documents: int
    zero_scene_documents: int
    zero_scene_share: float | None
    moments: int
    verified_moments: int
    verified_quote_share: float | None


class SourceTypeStats(ExtractionStats):
    source_type: str


class FailedDocument(Answer):
    document_id: str
    title: str
    source_type: str
    job_id: str | None
    error_summary: str | None
    failed_at: datetime | None
    attempts: int | None


class OldestWaiting(Answer):
    document_id: str
    title: str
    source_type: str
    status: str
    ingested_at: datetime
    waiting_hours: float


class ExtractionHealth(Answer):
    generated_at: datetime
    totals: ExtractionStats
    failed: list[FailedDocument]
    failed_total: int
    oldest_pending: OldestWaiting | None
    by_source_type: list[SourceTypeStats]


DOCUMENTS = "FROM transcripts t WHERE t.included AND t.canonical_document_id IS NULL"


def _share(part: int, whole: int) -> float | None:
    return round(part / whole, 4) if whole else None


def _stats(documents: list[dict], moments: dict) -> dict:
    by_status = {s: 0 for s in STATUSES}
    for row in documents:
        by_status[row["status"]] = by_status.get(row["status"], 0) + row["n"]
    completed = by_status["completed"]
    zero = sum(row["n"] for row in documents if row["status"] == "completed" and row["scenes"] == 0)
    return {"included_documents": sum(by_status.values()), "by_status": by_status, "completed_documents": completed,
            "zero_scene_documents": zero, "zero_scene_share": _share(zero, completed), "moments": moments["moments"],
            "verified_moments": moments["verified"], "verified_quote_share": _share(moments["verified"], moments["moments"])}


def extraction_health(repo) -> dict:
    with repo.connection() as conn:
        rows = conn.execute(f"""SELECT t.source_type, t.extraction_status AS status,
                (SELECT count(*) FROM key_moments m WHERE m.document_id = t.transcript_id AND m.is_current) = 0 AS no_scenes, count(*) AS n
            {DOCUMENTS} GROUP BY 1, 2, 3""").fetchall()
        documents = [{"source_type": r["source_type"], "status": r["status"], "n": r["n"], "scenes": 0 if r["no_scenes"] else 1} for r in rows]
        moment_rows = conn.execute("""SELECT t.source_type, count(*) AS moments, count(*) FILTER (WHERE m.quote_verified) AS verified
            FROM key_moments m JOIN transcripts t ON t.transcript_id = m.document_id
            WHERE m.is_current AND t.included AND t.canonical_document_id IS NULL GROUP BY 1""").fetchall()
        failed_total = conn.execute(f"SELECT count(*) n {DOCUMENTS} AND t.extraction_status = 'failed'").fetchone()["n"]
        failed = conn.execute(f"""SELECT t.transcript_id AS document_id, t.title, t.source_type, j.job_id, j.error_summary,
                COALESCE(j.finished_at, j.updated_at) AS failed_at, j.attempt_count AS attempts
            FROM transcripts t LEFT JOIN LATERAL (SELECT j.* FROM pipeline_jobs j JOIN pipeline_runs r USING (run_id)
                WHERE j.stage = 'moment_extraction' AND j.status = 'failed' AND (j.transcript_id = t.transcript_id
                  OR r.input_refs->'transcripts' @> jsonb_build_array(jsonb_build_object('id', t.transcript_id)))
                ORDER BY j.updated_at DESC LIMIT 1) j ON true
            WHERE t.included AND t.canonical_document_id IS NULL AND t.extraction_status = 'failed'
            ORDER BY failed_at DESC NULLS LAST, t.transcript_id LIMIT {FAILED_LIMIT}""").fetchall()
        waiting = conn.execute(f"""SELECT t.transcript_id AS document_id, t.title, t.source_type, t.extraction_status AS status,
                t.ingested_at, extract(epoch FROM now() - t.ingested_at) / 3600 AS waiting_hours
            {DOCUMENTS} AND t.extraction_status IN ('pending', 'queued') ORDER BY t.ingested_at, t.transcript_id LIMIT 1""").fetchone()
        now = conn.execute("SELECT now() AS now").fetchone()["now"]
    by_type = {r["source_type"]: r for r in moment_rows}
    overall = {"moments": sum(r["moments"] for r in moment_rows), "verified": sum(r["verified"] for r in moment_rows)}
    none = {"moments": 0, "verified": 0}
    return {"generated_at": now, "totals": _stats(documents, overall), "failed": failed, "failed_total": failed_total,
            "oldest_pending": {**waiting, "waiting_hours": round(float(waiting["waiting_hours"]), 2)} if waiting else None,
            "by_source_type": [{"source_type": kind, **_stats([d for d in documents if d["source_type"] == kind], by_type.get(kind, none))}
                               for kind in sorted({d["source_type"] for d in documents})]}


def install(routes, repo, reader, action):
    # Registered before the documents API, whose `/documents/{transcript_id}` would otherwise read "extraction-health" as an id.
    @routes.get("/documents/extraction-health", response_model=ExtractionHealth)
    def health(subject: str = Depends(reader)):
        return action(extraction_health, repo)
