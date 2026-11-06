"""Bounded transcript-only backfill; no generation jobs or external inference."""

import argparse
import hashlib
import json
import math
from collections import Counter
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import httpx
from psycopg import sql

from .chunk_encoding import BATCH_SIZE, cached_vector, chunk_view, contract, provenance, queue
from .config import BACKEND_ROOT, Settings
from .database import check
from .matching import vector_digest, vector_valid
from .repository import ContentRepository
from .sql_pipeline import SQLWorker
from .storage_config import StorageSettings
from .storage_sources import capture, chunks
from .store import JsonStore, canonical_hash

PROTECTED = (
    "key_moments",
    "content_angles",
    "angle_moments",
    "content_briefs",
    "content_packs",
    "content_assets",
    "calendar_entries",
)
EXISTING = {
    "weeks": "week_id",
    "transcripts": "transcript_id",
    "transcript_chunks": "chunk_id",
    "pipeline_runs": "run_id",
    "pipeline_jobs": "job_id",
    "pipeline_events": "event_id",
}


# Backfill week 1 began on Monday 1 June 2026 (plan E.B2: Week N starts 7(N-1) days later).
BACKFILL_START = date(2026, 6, 1)


def source_plan(root, reconciliation, *, duplicate_week=10, start=BACKFILL_START):
    """Only Zoom originals and reconciled additional Fathom sources are eligible."""
    root = Path(root).resolve()
    if duplicate_week not in {10, 11}:
        raise ValueError("Duplicated Zoom calls require an explicit Week 10 or Week 11 assignment")
    raw_sources = []
    for week in range(1, 21):
        for path in sorted((root / f"week{week}").glob("*")):
            if path.is_file() and path.suffix.lower() in {".txt", ".vtt", ".webvtt"}:
                raw_sources.append((week, path, hashlib.sha256(path.read_bytes()).hexdigest()))
    by_hash = {}
    for item in raw_sources:
        by_hash.setdefault(item[2], []).append(item)
    selected, excluded = {}, []
    for copies in by_hash.values():
        if len(copies) > 1:
            if len(copies) != 2 or {c[0] for c in copies} != {10, 11}:
                raise ValueError("Unexpected duplicate originals require a source-selection decision")
            chosen = next(c for c in copies if c[0] == duplicate_week)
            excluded.extend(
                {
                    "week": c[0],
                    "path": str(c[1]),
                    "sha256": c[2],
                    "selected_week": duplicate_week,
                    "selected_path": str(chosen[1]),
                }
                for c in copies
                if c != chosen
            )
        else:
            chosen = copies[0]
        selected.setdefault(chosen[0], []).append(chosen[1])
    for source in reconciliation["sources"]:
        if source["category"] != "additional" or source["selected_as_additional_source"] is not True:
            continue
        path = Path(source["folder"]).resolve() / "transcript.raw.json"
        if not path.is_relative_to(root / f"week{source['week']}" / "fathom" / "additional"):
            raise ValueError("Selected Fathom source is outside its additional-source folder")
        if hashlib.sha256(path.read_bytes()).hexdigest() != source["raw_sha256"]:
            raise ValueError("Reconciled Fathom original changed")
        selected.setdefault(source["week"], []).append(path)
    result = []
    for week, paths in sorted(selected.items()):
        records = [capture(p, week, i) for i, p in enumerate(sorted(paths), 1)]
        prepared = [{**c, "transcript_id": r["transcript_id"]} for r in records for c in chunks(r)]
        for c in prepared:
            chunk_view(c)
        # Every original passage occurs exactly once; no omitted or duplicated turns.
        expected = Counter(p["passage_id"] for r in records for p in r["passage_map"])
        actual = Counter(p["passage_id"] for c in prepared for p in c["passage_refs"])
        if expected != actual:
            raise ValueError("Chunk passage coverage is incomplete")
        result.append(
            {
                "week": week,
                "start": start + timedelta(days=(week - 1) * 7),
                "paths": sorted(paths),
                "records": records,
                "chunks": prepared,
            }
        )
    return result, excluded


def frozen_plan(plan):
    return [
        {
            "week": w["week"],
            "start": w["start"].isoformat(),
            "sources": [
                {
                    "path": str(p),
                    "id": r["transcript_id"],
                    "hash": r["content_hash"],
                    "view_hash": canonical_hash([r["original_text"], r["passage_map"], r["source_metadata"]]),
                }
                for p, r in zip(w["paths"], w["records"], strict=True)
            ],
            "chunks": [chunk_view(c) for c in w["chunks"]],
        }
        for w in plan
    ]


def protected_snapshot(conn, ids=None):
    if ids is None:
        ids = {
            table: [
                r["id"]
                for r in conn.execute(sql.SQL("SELECT {} AS id FROM {}").format(sql.Identifier(column), sql.Identifier(table)))
            ]
            for table, column in EXISTING.items()
        }
    hashes = {}
    for table in PROTECTED + tuple(EXISTING):
        query = sql.SQL("SELECT to_jsonb(t) AS body FROM {} t").format(sql.Identifier(table))
        args = ()
        if table in EXISTING:
            query += sql.SQL(" WHERE {}=ANY(%s)").format(sql.Identifier(EXISTING[table]))
            args = (ids[table],)
        rows = [r["body"] for r in conn.execute(query, args)]
        hashes[table] = {"count": len(rows), "hash": canonical_hash(sorted(rows, key=canonical_hash))}
    return {"ids": ids, "tables": hashes}


def verify_week(repo, models, store, week, *, require_vectors=True):
    digest = contract(models)
    with repo.connection() as conn:
        sources = repo.frozen_sources(conn, "week_" + week["start"].isoformat())
        if {r["transcript_id"] for r in sources} != {r["transcript_id"] for r in week["records"]}:
            raise ValueError("Stored source set differs from the frozen selection")
        for r in sources:
            original = store.path(f"source-originals/{r['content_hash']}.original").read_bytes()
            if hashlib.sha256(original).hexdigest() != r["content_hash"]:
                raise ValueError("Archived original integrity failed")
        rows = conn.execute(
            "SELECT * FROM transcript_chunks WHERE transcript_id=ANY(%s) ORDER BY chunk_id",
            ([r["transcript_id"] for r in sources],),
        ).fetchall()
        expected = {c["chunk_id"]: c for c in week["chunks"]}
        if set(expected) != {r["chunk_id"] for r in rows}:
            raise ValueError("Stored chunk coverage differs from the frozen plan")
        proof = provenance(conn, digest)
        artifacts = set()
        encoded = 0
        for row in rows:
            view = chunk_view(row)
            if view != chunk_view(expected[row["chunk_id"]]):
                raise ValueError("Stored chunks differ from the prepared inputs")
            if row["embedding"] is None and not require_vectors:
                continue
            p = proof.get(row["chunk_id"], {})
            if (
                not vector_valid(row["embedding"])
                or p.get("vector_digest") != vector_digest(row["embedding"])
                or any(p.get(k) != v for k, v in view.items())
            ):
                raise ValueError("Stored vector/provenance integrity failed")
            cached = cached_vector(store, p["cache"], digest, view["input_hash"])
            if cached["vector_digest"] != p["vector_digest"]:
                raise ValueError("Stored vector differs from its immutable cache")
            artifacts.add(p["response_artifact"])
            encoded += 1
    return {
        "week": week["week"],
        "week_id": "week_" + week["start"].isoformat(),
        "transcripts": len(sources),
        "passages": sum(len(r["passage_map"]) for r in sources),
        "chunks": len(rows),
        "verified_vectors": encoded,
        "response_artifacts": sorted(artifacts),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument("--execute", action="store_true")
    actions.add_argument("--prepare-only", action="store_true", help="Admit/chunk locally; every HTTP request forbidden")
    parser.add_argument("--retry-failed", action="store_true")
    parser.add_argument("--duplicate-week", type=int, choices=[10, 11], required=True)
    parser.add_argument("--root", type=Path, default=BACKEND_ROOT / "zoom_backfill_meetings")
    parser.add_argument(
        "--reconciliation", type=Path, default=BACKEND_ROOT.parent / "research/fathom-backfill-completed-2026-10-14.json"
    )
    parser.add_argument("--local-preflight", action="store_true", help="No database or external requests")
    # The archive's identity and week calendar (S.B6). Defaults are the developer's original archive.
    parser.add_argument("--start-date", type=date.fromisoformat, default=BACKFILL_START,
                        help="Monday of backfill week 1; week N starts 7(N-1) days later")
    parser.add_argument("--database-name", default="atelier")
    parser.add_argument("--database-host", default="127.0.0.1")
    parser.add_argument("--database-port", type=int, default=15432)
    args = parser.parse_args()
    reconciliation = json.loads(args.reconciliation.read_text(encoding="utf-8"))
    plan, excluded = source_plan(args.root, reconciliation, duplicate_week=args.duplicate_week, start=args.start_date)
    frozen = frozen_plan(plan)
    fingerprint = canonical_hash(frozen)
    summary = {
        "plan_hash": fingerprint,
        "selected_transcripts": sum(len(w["records"]) for w in plan),
        "selected_chunks": sum(len(w["chunks"]) for w in plan),
        "excluded_duplicate_zoom_files": len(excluded),
        "maximum_chunk_utf8_bytes": max(len(c["chunk_text"].encode()) for w in plan for c in w["chunks"]),
        "weeks": [{"week": w["week"], "transcripts": len(w["records"]), "chunks": len(w["chunks"])} for w in plan],
    }
    print(json.dumps(summary), flush=True)
    if args.local_preflight:
        return
    persistent, models = StorageSettings.from_env(), Settings.from_env()
    if persistent.synthetic or any(
        (
            persistent.generation_enabled,
            persistent.encoding_enabled,
            persistent.refinement_enabled,
            persistent.brief_live_enabled,
            persistent.brief_web_enabled,
            models.live_enabled,
            models.embeddings_enabled,
        )
    ):
        raise ValueError("Persistent external capabilities must remain disabled")
    if (
        models.embedding_base_url.rstrip("/") != "https://openrouter.ai/api/v1"
        or models.embedding_model != "openai/text-embedding-3-small"
        or models.embedding_dimensions != 1536
    ):
        raise ValueError("Approved embedding profile is required")
    repo = ContentRepository(persistent)
    with repo.connection() as conn:
        expected = (args.database_name, args.database_host, args.database_port)
        if (conn.info.dbname, conn.info.host, conn.info.port) != expected:
            raise ValueError(f"Only the named archive database is authorized: {expected[0]} at {expected[1]}:{expected[2]}")
        conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
        schema = check(conn)
        before = protected_snapshot(conn)
        if conn.execute("SELECT 1 FROM pipeline_jobs WHERE status IN ('queued','running') LIMIT 1").fetchone():
            raise ValueError("An active job requires inspection before a bounded backfill")
    if not args.execute and not args.prepare_only:
        print(json.dumps({"database_preflight": "passed", "schema": schema}), flush=True)
        return
    if args.execute and not models.embedding_api_key:
        raise ValueError("Embedding credential is required")
    store = JsonStore(persistent.artifact_root)
    base = "verification/transcript-backfill/" + fingerprint
    baseline_path = base + "/baseline.json"
    if store.path(baseline_path).exists():
        before = store.read_json(baseline_path)["protected"]
        with repo.connection() as conn:
            if protected_snapshot(conn, before["ids"]) != before:
                raise ValueError("Protected baseline changed; inspect before resuming")
    else:
        store.write_json(
            baseline_path,
            {"protected": before, "selection": frozen, "excluded_aliases": excluded, "duplicate_assignment": args.duplicate_week},
        )
    storage = persistent.model_copy(update={"encoding_enabled": args.execute})
    repo = ContentRepository(storage)
    worker = SQLWorker(storage, models) if args.execute else None
    endpoint = models.embedding_base_url.rstrip("/") + "/embeddings"
    permitted = {canonical_hash(c["chunk_text"]): c["chunk_text"] for w in plan for c in w["chunks"]}
    calls, verified, seen = [], [], set()
    original_transport = httpx.HTTPTransport.handle_request
    maximum_calls = sum(math.ceil(len(w["chunks"]) / BATCH_SIZE) for w in plan)
    attempt = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")

    def embeddings_only(transport, request):
        if not args.execute:
            raise ValueError("Local preparation forbids all HTTP requests")
        if str(request.url) != endpoint or request.method != "POST":
            raise ValueError("Transcript backfill forbids every non-embedding HTTP request")
        payload = json.loads(request.content)
        texts = payload.get("input")
        if (
            not isinstance(texts, list)
            or not 0 < len(texts) <= BATCH_SIZE
            or payload.get("model") != models.embedding_model
            or payload.get("dimensions") != 1536
            or payload.get("encoding_format") != "float"
        ):
            raise ValueError("Unauthorized embedding request shape")
        hashes = [canonical_hash(t) for t in texts]
        if any(permitted.get(h) != t for h, t in zip(hashes, texts, strict=True)):
            raise ValueError("Outbound embedding text is outside the frozen selection")
        if seen.intersection(hashes) or len(set(hashes)) != len(hashes) or len(calls) >= maximum_calls:
            raise ValueError("Repeated or excessive live embedding requests are forbidden")
        seen.update(hashes)
        calls.append({"inputs": len(texts), "input_hashes": hashes, "at_utc": datetime.now(UTC).isoformat()})
        store.write_json(base + "/attempts/" + attempt + "/dispatches.json", calls, overwrite=True)
        print(json.dumps({"embedding_batch": len(calls), "inputs": len(texts)}), flush=True)
        return original_transport(transport, request)

    httpx.HTTPTransport.handle_request = embeddings_only
    try:
        for w in plan:
            # Validate original bytes AND metadata again before each mutation.
            fresh = [capture(p, w["week"], i) for i, p in enumerate(w["paths"], 1)]
            def view(r):
                return [r["original_text"], r["passage_map"], r["source_metadata"]]
            if any(
                a["content_hash"] != b["content_hash"] or view(a) != view(b) for a, b in zip(fresh, w["records"], strict=True)
            ):
                raise ValueError("Source changed after preflight")
            if w["week"] <= 2:
                verified.append(verify_week(repo, models, store, w))
                print(json.dumps({"week": w["week"], "status": "existing_vectors_preserved"}), flush=True)
                continue
            repo.admit(args.root / f"week{w['week']}", w["start"], w["week"], selected_paths=w["paths"])
            if args.prepare_only:
                verified.append(verify_week(repo, models, store, w, require_vectors=False))
                print(
                    json.dumps(
                        {"week": w["week"], "status": "prepared_without_external_calls", "chunks": verified[-1]["chunks"]}
                    ),
                    flush=True,
                )
                continue
            queued = queue(repo, models, "week_" + w["start"].isoformat(), "live", "authorized-transcript-backfill")
            with repo.connection() as conn:
                job = conn.execute("SELECT * FROM pipeline_jobs WHERE job_id=%s", (queued["job_id"],)).fetchone()
                if job["stage"] != "transcript_chunk_embedding":
                    raise ValueError("Non-transcript job is forbidden")
            if job["status"] == "failed":
                if not args.retry_failed:
                    raise ValueError("Inspect saved artifacts and explicitly use --retry-failed")
                repo.retry(job["job_id"], "explicit-transcript-backfill-recovery")
            if job["status"] != "completed":
                worker.once(run_id=queued["run_id"])
            with repo.connection() as conn:
                done = conn.execute(
                    "SELECT status,error_summary FROM pipeline_jobs WHERE job_id=%s", (queued["job_id"],)
                ).fetchone()
            if done["status"] != "completed":
                raise ValueError(done["error_summary"] or "Transcript encoding did not complete")
            verified.append(verify_week(repo, models, store, w))
            print(json.dumps({"week": w["week"], "status": "verified", "chunks": verified[-1]["chunks"]}), flush=True)
    finally:
        httpx.HTTPTransport.handle_request = original_transport
        with repo.connection() as conn:
            unchanged = protected_snapshot(conn, before["ids"]) == before
        store.write_json(
            base + "/attempts/" + attempt + "/protected-verification.json",
            {"protected_records_unchanged": unchanged, "embedding_dispatches": len(calls), "generation_calls": 0},
            overwrite=True,
        )
        if not unchanged:
            raise ValueError("Protected angle/moment/downstream or earlier records changed")
    paths = sorted({p for w in verified for p in w["response_artifacts"]})
    usage = [store.read_json(p).get("usage", {}) for p in paths]
    report = {
        **summary,
        "status": "prepared_awaiting_embeddings" if args.prepare_only else "completed",
        "verified_weeks": verified,
        "model": models.embedding_model,
        "dimensions": 1536,
        "embedding_dispatches_this_attempt": len(calls),
        "generation_calls": 0,
        "protected_records_unchanged": True,
        "persistent_external_switches_unchanged": True,
        "reported_cost_usd_all_selected_cache_responses": (
            sum(u["cost"] for u in usage) if all(isinstance(u.get("cost"), (int, float)) for u in usage) else None
        ),
        "embedding_response_artifacts": paths,
        "operation_artifacts": base,
        "completed_at_utc": datetime.now(UTC).isoformat(),
        "excluded_duplicate_aliases": excluded,
    }
    report_name = "prepared.json" if args.prepare_only else "completed.json"
    store.write_json(base + "/" + report_name, report, overwrite=True)
    readiness_name = "transcript-backfill-preparation.json" if args.prepare_only else "transcript-backfill-readiness.json"
    store.write_json("verification/" + readiness_name, report, overwrite=True)
    print(
        json.dumps(
            {
                k: report[k]
                for k in (
                    "status",
                    "selected_transcripts",
                    "selected_chunks",
                    "embedding_dispatches_this_attempt",
                    "generation_calls",
                    "protected_records_unchanged",
                    "operation_artifacts",
                )
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
