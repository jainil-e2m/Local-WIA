"""Re-embedding after segmentation v2, as a planned `bulk` run under one embedding contract (plan 1.B6, S.B5).

Segmentation v2 makes new chunk rows (header, roles, overlap) and retires the old ones, which stay readable for what already
cites them. The new rows have no vector. `queue` freezes the documents' current chunks that lack one into encoding runs (one
per week container, because the encoder checks each run's documents against one week; week-less documents form one group),
and the existing encoder executes them: bounded batches, a cache keyed by contract and text, a saved response before any
database write, and `embedding_model` recorded on each chunk. Nothing is dispatched to a provider unless the run is `live`,
the encoding catch is on, and a run plan is active.

`estimate` states the cost before any paid run: input tokens are about a quarter of the characters.
"""
from __future__ import annotations

from collections import defaultdict

from psycopg.types.json import Jsonb

from ..chunk_encoding import STAGE, VERSION, chunk_view, contract
from ..repository import insert
from ..store import canonical_hash

# USD per million input tokens for openai/text-embedding-3-small on OpenRouter (checked 18 October 2026).
PRICE_PER_MILLION_TOKENS = 0.02
CHARACTERS_PER_TOKEN = 4


def pending_chunks(conn, transcript_ids=None) -> list[dict]:
    """Current chunks of included, normalised, non-duplicate documents that have no vector yet."""
    return conn.execute("""SELECT c.*,t.week_id FROM transcript_chunks c JOIN transcripts t USING (transcript_id)
        WHERE c.is_current AND c.embedding IS NULL AND t.included AND t.normalised_at IS NOT NULL
          AND t.canonical_document_id IS NULL AND (%s::text[] IS NULL OR c.transcript_id=ANY(%s))
        ORDER BY t.week_id NULLS FIRST, c.transcript_id, c.chunk_id""", (transcript_ids, transcript_ids)).fetchall()


def estimate(conn, transcript_ids=None) -> dict:
    """What embedding the pending chunks would cost, before anything is sent."""
    rows = pending_chunks(conn, transcript_ids)
    characters = sum(len(r["chunk_text"]) for r in rows)
    tokens = characters / CHARACTERS_PER_TOKEN
    return {"chunks": len(rows), "documents": len({r["transcript_id"] for r in rows}), "characters": characters,
            "estimated_tokens": int(tokens), "price_per_million_tokens_usd": PRICE_PER_MILLION_TOKENS,
            "estimated_cost_usd": round(tokens / 1_000_000 * PRICE_PER_MILLION_TOKENS, 4)}


def contract_report(conn, models) -> dict:
    """Is every current chunk embedded under the one contract? Counts by state, for the exit check."""
    row = conn.execute("""SELECT count(*) FILTER (WHERE embedding IS NOT NULL AND embedding_model=%s) AS under_contract,
        count(*) FILTER (WHERE embedding IS NULL) AS unembedded,
        count(*) FILTER (WHERE embedding IS NOT NULL AND embedding_model IS DISTINCT FROM %s) AS other_model,
        count(*) AS current_chunks FROM transcript_chunks c JOIN transcripts t USING (transcript_id)
        WHERE c.is_current AND t.included AND t.canonical_document_id IS NULL""", (models.embedding_model, models.embedding_model)).fetchone()
    return {**row, "complete": row["current_chunks"] > 0 and row["under_contract"] == row["current_chunks"],
            "embedding_model": models.embedding_model}


def queue(repo, models, *, transcript_ids=None, mode: str = "cached", actor: str = "local-cli") -> dict:
    """Queue encoding for the current chunks without a vector. Returns the runs created (none when nothing is pending)."""
    if mode not in {"cached", "live"}:
        raise ValueError("Chunk encoding mode must be cached or live")
    if mode == "live" and not repo.settings.encoding_enabled:
        raise ValueError("External chunk encoding permission is disabled")
    digest = contract(models, synthetic=repo.settings.synthetic)
    runs = []
    with repo.connection() as conn:
        groups: dict[str | None, list[dict]] = defaultdict(list)
        for row in pending_chunks(conn, transcript_ids):
            groups[row["week_id"]].append(row)
        for week_id, rows in groups.items():
            rows = sorted(rows, key=lambda r: r["chunk_id"])  # the encoder re-reads a run's chunks in this order
            sources = conn.execute("SELECT * FROM transcripts WHERE transcript_id=ANY(%s) ORDER BY transcript_id",
                                   (sorted({r["transcript_id"] for r in rows}),)).fetchall()
            refs = {"transcripts": [{"id": s["transcript_id"], "hash": s["content_hash"],
                                     "view_hash": canonical_hash([s["original_text"], s["passage_map"], s["source_metadata"]])}
                                    for s in sources],
                    "chunks": [chunk_view(r) for r in rows], "contract": digest, "input_version": VERSION,
                    "synthetic": repo.settings.synthetic, "mode": "synthetic" if repo.settings.synthetic else "replay",
                    "encoding_mode": mode, "week_index": sources[0]["source_metadata"].get("week_index", 0),
                    "selected_by": "set", "segmentation": "v2"}
            intent = canonical_hash([week_id, refs])
            run_id, job_id = "chunk_run_" + intent[:24], "chunk_job_" + intent[:24]
            from ..settings_store import snapshot_refs
            refs = {**refs, **snapshot_refs("encoding", models=models, storage=repo.settings, conn=conn)}
            insert(conn, "pipeline_runs", {"run_id": run_id, "week_id": week_id, "run_scope": "transcript_encoding",
                                           "trigger_type": "manual", "triggered_by": actor, "input_refs": refs}, conflict=True)
            insert(conn, "pipeline_jobs", {"job_id": job_id, "run_id": run_id, "week_id": week_id, "stage": STAGE,
                                           "idempotency_key": "chunk-reencoding:" + intent, "input_hash": intent,
                                           "progress_details": Jsonb({"dependencies": [], "encoding_mode": mode}),
                                           "total_units": len(rows),
                                           "current_message": "Re-segmented transcript chunks queued for encoding"}, conflict=True)
            runs.append({"run_id": run_id, "job_id": job_id, "week_id": week_id, "chunks": len(rows)})
    return {"runs": runs, "chunks": sum(r["chunks"] for r in runs), "contract": digest}
