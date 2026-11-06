"""`moments report` (plan 2.B11): what the extraction produced, in numbers a person can read before and after a backfill.

The verified-quote share (moments whose quote is in the source, over all stored moments), how many quotes were repaired, how
many are unverified, the distribution of speaker roles and moment types, the same per call type, the documents that yielded no
scene at all, how many figures fail the number check, and the invariants a backfill must keep:

* no document that is excluded has a *current* moment, and none has an extraction job still to run;
* every included, extracted document is accounted for (it has moments, or it is listed as having none).

`current` counts the newest extractor's moments of each included document (`is_current`); a filter on `extractor_version`
reports one extractor alone, which is how two scene profiles are compared on the same documents.
"""
from __future__ import annotations

from . import store


def share(part: int, whole: int) -> float | None:
    return round(part / whole, 4) if whole else None


def summary(conn, *, extractor_version: str | None = None, current_only: bool = True) -> dict:
    """The numbers for the moments stored, optionally for one extractor version and optionally only the current ones."""
    where = f"m.document_id IS NOT NULL AND {store.extracted_by()} AND (NOT %(cur)s OR m.is_current)"
    args = {**store.extracted_by_params(extractor_version), "cur": current_only}
    total = conn.execute(f"""SELECT count(*) AS stored, count(*) FILTER (WHERE m.quote_verified) AS verified,
        count(*) FILTER (WHERE NOT m.quote_verified) AS unverified,
        count(*) FILTER (WHERE m.quote_verified AND m.quote_repair IS NOT NULL) AS repaired,
        count(*) FILTER (WHERE m.quote_verified AND (m.checks->'numbers'->>'passed')::boolean IS FALSE) AS number_check_failed,
        count(*) FILTER (WHERE m.quote_verified AND m.checks ? 'numbers') AS number_checked
        FROM key_moments m WHERE {where}""", args).fetchone()

    def distribution(column: str) -> dict:
        return {r["k"] or "none": r["n"] for r in conn.execute(
            f"SELECT m.{column} AS k,count(*) AS n FROM key_moments m WHERE {where} AND m.quote_verified GROUP BY 1 ORDER BY 2 DESC,1", args)}

    per_call_type = {}
    for r in conn.execute(f"""SELECT COALESCE(t.call_type,'unclassified') AS k,count(DISTINCT t.transcript_id) AS documents,
        count(m.moment_id) AS stored, count(m.moment_id) FILTER (WHERE m.quote_verified) AS verified,
        count(m.moment_id) FILTER (WHERE m.quote_verified AND m.quote_repair IS NOT NULL) AS repaired
        FROM key_moments m JOIN transcripts t ON t.transcript_id=m.document_id WHERE {where} GROUP BY 1 ORDER BY 1""", args):
        per_call_type[r["k"]] = {"documents_with_moments": r["documents"], "stored": r["stored"], "verified": r["verified"],
                                 "verified_quote_share": share(r["verified"], r["stored"]), "repaired": r["repaired"]}
    roles = {}
    for r in conn.execute(f"""SELECT COALESCE(t.call_type,'unclassified') AS ct,m.speaker_role AS role,count(*) AS n
        FROM key_moments m JOIN transcripts t ON t.transcript_id=m.document_id WHERE {where} AND m.quote_verified GROUP BY 1,2 ORDER BY 1,2""", args):
        roles.setdefault(r["ct"], {})[r["role"]] = r["n"]
    for call_type, entry in per_call_type.items():
        entry["role_distribution"] = roles.get(call_type, {})
    return {"extractor_version": extractor_version, "current_only": current_only, "moments_stored": total["stored"],
            "verified": total["verified"], "unverified": total["unverified"], "verified_quote_share": share(total["verified"], total["stored"]),
            "quote_repairs": total["repaired"], "number_check": {"checked": total["number_checked"], "failed": total["number_check_failed"]},
            "role_distribution": distribution("speaker_role"), "type_distribution": distribution("moment_type"),
            "evidence_kind_distribution": distribution("evidence_kind"), "consent_distribution": distribution("consent_status"),
            "by_call_type": per_call_type}


def documents(conn) -> dict:
    """Documents by extraction status, and the included, extracted documents that yielded no scene."""
    status = {r["k"]: r["n"] for r in conn.execute("SELECT extraction_status AS k,count(*) AS n FROM transcripts GROUP BY 1 ORDER BY 1")}
    zero = conn.execute("""SELECT t.transcript_id,COALESCE(t.call_type,'unclassified') AS call_type,t.title FROM transcripts t
        WHERE t.included AND t.canonical_document_id IS NULL AND t.extraction_status='completed'
          AND NOT EXISTS (SELECT 1 FROM key_moments m WHERE m.document_id=t.transcript_id) ORDER BY t.transcript_id""").fetchall()
    return {"by_extraction_status": status, "included": conn.execute("SELECT count(*) AS n FROM transcripts WHERE included").fetchone()["n"],
            "with_zero_scenes": {"count": len(zero), "by_call_type": _count(zero, "call_type"),
                                 "documents": [{"transcript_id": z["transcript_id"], "call_type": z["call_type"]} for z in zero[:100]]}}


def _count(rows, key) -> dict:
    out: dict = {}
    for r in rows:
        out[r[key]] = out.get(r[key], 0) + 1
    return out


def invariants(conn) -> dict:
    """What a backfill must never break. `ok` is false with the offending documents listed when it does."""
    current = conn.execute("""SELECT DISTINCT m.document_id FROM key_moments m JOIN transcripts t ON t.transcript_id=m.document_id
        WHERE NOT t.included AND m.is_current ORDER BY 1""").fetchall()
    retired = conn.execute("""SELECT count(*) AS n FROM key_moments m JOIN transcripts t ON t.transcript_id=m.document_id
        WHERE NOT t.included AND NOT m.is_current""").fetchone()["n"]
    open_jobs = conn.execute("""SELECT j.job_id,j.transcript_id FROM pipeline_jobs j JOIN transcripts t ON t.transcript_id=j.transcript_id
        WHERE j.stage='moment_extraction' AND NOT t.included AND j.status IN ('queued','running') ORDER BY 1""").fetchall()
    return {"no_current_moment_for_an_excluded_document": {"ok": not current, "documents": [r["document_id"] for r in current]},
            "no_open_extraction_job_for_an_excluded_document": {"ok": not open_jobs, "jobs": [r["job_id"] for r in open_jobs]},
            "moments_kept_readable_for_documents_excluded_since": retired}


def report(conn, *, extractor_version: str | None = None) -> dict:
    """The whole report: the numbers, the documents and the invariants."""
    out = {"moments": summary(conn, extractor_version=extractor_version), "documents": documents(conn), "invariants": invariants(conn)}
    out["all_stored"] = summary(conn, extractor_version=extractor_version, current_only=False)
    out["ok"] = all(v["ok"] for v in out["invariants"].values() if isinstance(v, dict) and "ok" in v)
    return out
