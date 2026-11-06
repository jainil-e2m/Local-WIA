"""Moment embeddings (plan 2.B5): one vector per verified, current moment, under the archive's one embedding contract.

What is embedded. A deterministic text built from the moment (`embedding_text`): the verified quote, then the scene record
(the neutral account of what was asked, noticed, recommended or decided, or for earlier moments the proposition), then the
setup (the context summary), one labelled line each. Nothing else: type, speaker, client and consent are filters, not
meaning. The builder is versioned (`INPUT_VERSION`); the text and the version are hashed into
`key_moments.embedding_input_hash`, so a moment is embedded again only when its text, the builder or the model changed.
Re-running embeds nothing new. A moment whose quote is not verified is never embedded (the table refuses a vector on it).

How it runs, like `documents reembed` (1.B6) for chunks.
* `estimate` states how many moments are pending, the tokens and the cost, and the input-set hash a run plan is approved
  for. It makes no call.
* `queue` freezes the pending moments into one `bulk` run (stage `moment_embedding`) and refuses a process whose embedding
  contract is not the archive's. Nothing is dispatched unless the run is `live`, the encoding catch is on, and an active run
  plan covers the `embedding` stage, the model and this input set.
* The handler (`execute`, called from `SQLWorker.execute`) embeds in bounded batches. Every response is saved before any
  database write, and a vector is cached by contract and text, so a retried job or a moment whose text appears twice is
  never paid for twice. The write re-checks that each moment is still verified, current and unchanged.
"""
from __future__ import annotations

import math
import os
from datetime import UTC, datetime

import numpy as np
from psycopg.types.json import Jsonb

from ..artifacts import store_for
from ..chunk_encoding import cached_vector, validate_response
from ..config import embedding_contract
from ..documents.reembed import CHARACTERS_PER_TOKEN, PRICE_PER_MILLION_TOKENS
from ..llm import embedding_body, live_provider
from ..llm.call import provider_embed
from ..llm.runs import LlmRuns
from ..matching import vector_digest, vector_valid
from ..repository import insert
from ..settings_store import snapshot_refs, value as setting
from ..startup import OVERRIDE
from ..store import canonical_hash

STAGE = "moment_embedding"
RUN_SCOPE = "moment_embedding"
INPUT_VERSION = "moment-scene-v1"
# Well under the encoder's byte bound; the setup is trimmed first, then the record. The quote is never cut.
MAX_CHARACTERS = 6000


def _clean(value) -> str:
    return " ".join(value.split()) if isinstance(value, str) else ""


def embedding_text(body: dict | None) -> str | None:
    """The text that stands for a moment in the vector space, or None when it has no quote to stand on."""
    body = body or {}
    quote, record, setup = _clean(body.get("quote")), _clean(body.get("proposition")), _clean(body.get("context_summary"))
    if not quote:
        return None
    room = MAX_CHARACTERS - len(quote) - len("Quote: \nScene: \nSetup: ")
    record = record[:max(room, 0)]
    setup = setup[:max(room - len(record), 0)]
    lines = [f"Quote: {quote}"] + ([f"Scene: {record}"] if record else []) + ([f"Setup: {setup}"] if setup else [])
    return "\n".join(lines)


def input_hash(text: str) -> str:
    return canonical_hash({"builder": INPUT_VERSION, "text": text})


def contract(models, *, synthetic: bool = False) -> str:
    """The digest a run records and a worker compares: endpoint, model, dimensions, the text builder and the synthetic flag."""
    return canonical_hash({**embedding_contract(models), "input": INPUT_VERSION, "synthetic": synthetic})


def check_contract(conn, models, synthetic: bool) -> None:
    """Refuse a process whose embedding contract is not the one the stored moment vectors were made under (S.B5).

    The dimensions must be the approved ones; no vector may exist under another model; and an earlier completed run's
    digest must be this process's. ATELIER_ALLOW_EMBEDDING_CONTRACT_CHANGE=true lifts the last two while the archive is
    deliberately re-encoded (the moments under the old model are then pending again)."""
    embedding_contract(models)
    if os.getenv(OVERRIDE) == "true":
        return
    other = conn.execute("""SELECT count(*) n, min(embedding_model) model FROM key_moments
        WHERE embedding IS NOT NULL AND embedding_model IS DISTINCT FROM %s""", (models.embedding_model,)).fetchone()
    if other["n"]:
        raise ValueError(f"{other['n']} moment vectors were made under {other['model']}, but this process embeds with "
                         f"{models.embedding_model}. Mixing models would make their distances meaningless: use the archive's "
                         f"embedding settings, or set {OVERRIDE}=true only while deliberately re-encoding it")
    recorded = {r["digest"] for r in conn.execute("""SELECT DISTINCT result_refs->>'contract' AS digest FROM pipeline_jobs
        WHERE stage=%s AND status='completed' AND result_refs ? 'contract'""", (STAGE,))}
    if recorded and contract(models, synthetic=synthetic) not in recorded:
        raise ValueError("The embedding contract differs from the one the stored moment vectors were made under; use the "
                         f"archive's EMBEDDING_BASE_URL and OPENAI_EMBEDDING_MODEL, or set {OVERRIDE}=true only while "
                         "deliberately re-encoding it")


def searchable(conn, ids=None) -> list[dict]:
    """Verified, current moments of included documents that are not copies: the ones search can ever return."""
    return conn.execute("""SELECT m.moment_id, m.moment_body, m.embedding_input_hash, m.embedding_model,
            m.embedding IS NOT NULL AS embedded
        FROM key_moments m JOIN transcripts t ON t.transcript_id = m.document_id
        WHERE m.quote_verified AND m.is_current AND t.included AND t.canonical_document_id IS NULL
          AND (%s::text[] IS NULL OR m.moment_id = ANY(%s)) ORDER BY m.moment_id""", (ids, ids)).fetchall()


def pending(conn, models, ids=None) -> tuple[list[dict], int]:
    """The moments that need a vector now (none, a stale one, or one made under another model), with their text and hash, and
    how many cannot be embedded because they hold no quote."""
    todo, unembeddable = [], 0
    for row in searchable(conn, ids):
        text = embedding_text(row["moment_body"])
        if text is None:
            unembeddable += 1
            continue
        digest = input_hash(text)
        if not (row["embedded"] and row["embedding_input_hash"] == digest and row["embedding_model"] == models.embedding_model):
            todo.append({"moment_id": row["moment_id"], "text": text, "input_hash": digest})
    return todo, unembeddable


def input_set_hash(items: list[dict]) -> str:
    """What a run plan is approved for: the moments and the exact text of each (the `--input-set-hash` of `plan create`)."""
    return "sha256:" + canonical_hash([[i["moment_id"], i["input_hash"]] for i in sorted(items, key=lambda i: i["moment_id"])])


def estimate(conn, models, ids=None) -> dict:
    """What embedding the pending moments would cost, before anything is sent. No call is made."""
    todo, unembeddable = pending(conn, models, ids)
    batch = setting("moments.embedding.batch_size", conn)
    characters = sum(len(i["text"]) for i in todo)
    tokens = characters / CHARACTERS_PER_TOKEN
    return {"moments": len(todo), "unembeddable": unembeddable, "characters": characters, "estimated_tokens": int(tokens),
            "price_per_million_tokens_usd": PRICE_PER_MILLION_TOKENS,
            "estimated_cost_usd": round(tokens / 1_000_000 * PRICE_PER_MILLION_TOKENS, 6), "batch_size": batch,
            "requests": math.ceil(len(todo) / batch), "embedding_model": models.embedding_model,
            "input_set_hash": input_set_hash(todo) if todo else None,
            "run_plan": {"stage": "embedding", "model": models.embedding_model, "input_set_hash": input_set_hash(todo) if todo else None,
                         "max_calls": math.ceil(len(todo) / batch)}}


def report(conn, models) -> dict:
    """Is every searchable moment embedded under the contract? Counts by state, for the exit check."""
    row = conn.execute("""SELECT count(*) FILTER (WHERE m.quote_verified AND m.is_current) AS searchable,
            count(*) FILTER (WHERE m.quote_verified AND m.is_current AND m.embedding IS NOT NULL AND m.embedding_model = %s) AS embedded,
            count(*) FILTER (WHERE m.embedding IS NOT NULL AND m.embedding_model IS DISTINCT FROM %s) AS other_model,
            count(*) FILTER (WHERE NOT m.quote_verified) AS unverified,
            count(*) FILTER (WHERE NOT m.quote_verified AND m.embedding IS NOT NULL) AS unverified_with_vector
        FROM key_moments m JOIN transcripts t ON t.transcript_id = m.document_id
        WHERE t.included AND t.canonical_document_id IS NULL""", (models.embedding_model, models.embedding_model)).fetchone()
    todo, unembeddable = pending(conn, models)
    return {**row, "stale_or_missing": len(todo), "unembeddable": unembeddable, "embedding_model": models.embedding_model,
            "complete": row["searchable"] > 0 and not todo and not unembeddable and row["other_model"] == 0}


def run_ids(conn, prefix: str, intent: str) -> tuple[str, str, str, bool]:
    """The run and job ids for an intent. The same intent queued twice is one job (a double click); once that job has finished, the
    same intent is new work again (the data changed since), so it gets a fresh identity. Returns (run, job, intent, still waiting)."""
    job_id = f"{prefix}_job_" + intent[:24]
    existing = conn.execute("SELECT status FROM pipeline_jobs WHERE job_id=%s", (job_id,)).fetchone()
    if existing and existing["status"] in ("queued", "running", "waiting"):
        return f"{prefix}_run_" + intent[:24], job_id, intent, True
    if existing:
        intent = canonical_hash([intent, datetime.now(UTC).isoformat()])
    return f"{prefix}_run_" + intent[:24], f"{prefix}_job_" + intent[:24], intent, False


def queue(repo, models, *, ids=None, mode: str = "cached", actor: str = "local-cli") -> dict:
    """Queue one `bulk` run that embeds the pending moments. Returns the run, or `queued: 0` when nothing is pending."""
    if mode not in {"cached", "live"}:
        raise ValueError("Moment embedding mode must be cached or live")
    if mode == "live" and not repo.settings.encoding_enabled:
        raise ValueError("External encoding permission is disabled (ATELIER_ALLOW_ENCODING)")
    synthetic = repo.settings.synthetic
    digest = contract(models, synthetic=synthetic)
    with repo.connection() as conn:
        check_contract(conn, models, synthetic)
        todo, unembeddable = pending(conn, models, ids)
        if not todo:
            return {"queued": 0, "moments": 0, "unembeddable": unembeddable, "contract": digest}
        inputs = [{"moment_id": i["moment_id"], "input_hash": i["input_hash"]} for i in todo]
        intent = canonical_hash([digest, mode, inputs])
        refs = {"contract": digest, "input_version": INPUT_VERSION, "embedding_model": models.embedding_model, "encoding_mode": mode,
                "synthetic": synthetic, "inputs": inputs, "input_set_hash": input_set_hash(todo)}
        refs = {**refs, **snapshot_refs("moment_embedding", models=models, storage=repo.settings, conn=conn)}
        run_id, job_id, intent, waiting = run_ids(conn, "momemb", intent)
        if waiting:
            return {"queued": 0, "already_queued": True, "moments": len(todo), "run_id": run_id, "job_id": job_id, "contract": digest,
                    "input_set_hash": refs["input_set_hash"], "unembeddable": unembeddable}
        insert(conn, "pipeline_runs", {"run_id": run_id, "week_id": None, "run_scope": RUN_SCOPE, "trigger_type": "manual",
                                       "triggered_by": actor, "input_refs": refs}, conflict=True)
        insert(conn, "pipeline_jobs", {"job_id": job_id, "run_id": run_id, "week_id": None, "stage": STAGE,
                                       "idempotency_key": "moment-embedding:" + intent, "input_hash": intent,
                                       "progress_details": Jsonb({"dependencies": [], "encoding_mode": mode}),
                                       "total_units": len(todo),
                                       "current_message": "Verified moments queued for embedding"}, conflict=True)
    return {"queued": len(todo), "moments": len(todo), "run_id": run_id, "job_id": job_id, "contract": digest,
            "input_set_hash": refs["input_set_hash"], "unembeddable": unembeddable}


def _provider(worker, run, store, attempt_base: str):
    """The embeddings provider: the injected one on a synthetic database, otherwise live (S.B1 routing, E.B1 run plan)."""
    provider = worker.provider
    if provider is None or not worker.storage.synthetic:
        provider = live_provider(worker.models, storage=worker.storage, chat=False,
                                 on_response=lambda _, raw: store.write_json(attempt_base + "/response.raw.json", raw))
    if hasattr(provider, "input_set_hash"):
        provider.input_set_hash = run["input_refs"]["input_set_hash"]  # the plan must have been approved for exactly this set
    return provider


def execute(worker, job) -> None:
    """The queue worker's handler: embed the frozen moments in batches, then finish the job."""
    repo, models, storage = worker.repo, worker.models, worker.storage
    with repo.connection() as conn:
        run = conn.execute("SELECT * FROM pipeline_runs WHERE run_id=%s", (job["run_id"],)).fetchone()
        refs = run["input_refs"]
        digest = contract(models, synthetic=storage.synthetic)
        if refs["contract"] != digest:
            raise ValueError("The frozen moment embedding contract changed; queue a new run")
        check_contract(conn, models, storage.synthetic)
        batch = setting("moments.embedding.batch_size", conn)
        repo.guard(conn, job)
    mode = refs["encoding_mode"]
    if mode == "live" and not storage.encoding_enabled:
        raise ValueError("External encoding permission is disabled (ATELIER_ALLOW_ENCODING)")
    store = store_for(storage)
    frozen = refs["inputs"]
    embedded = reused = requests = 0
    skipped = {"changed": 0, "already_embedded": 0}
    for start in range(0, len(frozen), batch):
        group = frozen[start:start + batch]
        with repo.connection() as conn:
            now = {r["moment_id"]: r for r in conn.execute("""SELECT moment_id, moment_body, quote_verified, is_current, embedding_input_hash,
                embedding_model, embedding IS NOT NULL AS embedded FROM key_moments WHERE moment_id = ANY(%s)""",
                                                          ([g["moment_id"] for g in group],))}
        todo = {}
        for item in group:
            row = now.get(item["moment_id"])
            text = embedding_text(row["moment_body"]) if row else None
            if row is None or not row["quote_verified"] or not row["is_current"] or text is None or input_hash(text) != item["input_hash"]:
                skipped["changed"] += 1  # unverified, superseded or edited since it was frozen: not embedded
            elif row["embedded"] and row["embedding_input_hash"] == item["input_hash"] and row["embedding_model"] == models.embedding_model:
                skipped["already_embedded"] += 1
            else:
                todo[item["moment_id"]] = (item["input_hash"], text)
        vectors: dict[str, dict] = {}
        missing: dict[str, str] = {}  # input hash -> text, once however many moments share it
        for moment_id, (ih, text) in todo.items():
            path = "moment-embedding/" + canonical_hash({"contract": digest, "input_hash": ih}) + ".json"
            if ih in vectors or ih in missing:
                continue
            if store.exists(path):
                vectors[ih] = {**cached_vector(store, path, digest, ih), "cache": path}
                reused += 1
            else:
                missing[ih] = text
        if missing:
            if mode != "live" and not storage.synthetic:
                raise ValueError("Compatible moment vectors are not cached; live embedding must be explicitly enabled")
            fingerprint = canonical_hash({"contract": digest, "inputs": list(missing)})
            base = f"moment-embedding-attempts/{job['job_id']}/{job['attempt_count']}/{fingerprint}"
            body = embedding_body(model=models.embedding_model, text=list(missing.values()), dimensions=1536)
            store.write_json(base + "/request.json", {"endpoint": models.embedding_base_url.rstrip("/") + "/embeddings",
                                                      "contract": digest, "body": body, "input_hashes": list(missing)})
            provider = _provider(worker, run, store, base)
            if not callable(getattr(provider, "embed_many", None)):
                raise ValueError("A batch embedding provider is required")
            requests += 1
            with repo.connection() as conn:
                repo.guard(conn, job)
                repo.event(conn, run["run_id"], "moment_embedding_dispatch", f"Embedding batch of {len(missing)} moments", job=job,
                           details={"fingerprint": fingerprint, "input_count": len(missing)})
            raw = provider_embed(provider, LlmRuns.for_storage(storage), model=models.embedding_model, texts=list(missing.values()),
                                 fingerprint=fingerprint, context={"run_id": run["run_id"]})
            response_path = base + "/response.raw.json"
            store.write_json(response_path, raw)  # saved before anything is validated or written to the database
            received = validate_response(raw, len(missing), models.embedding_model)
            for ih, vector in zip(missing, received, strict=True):
                path = "moment-embedding/" + canonical_hash({"contract": digest, "input_hash": ih}) + ".json"
                store.write_json(path, {"contract": digest, "input_hash": ih, "vector": vector, "vector_digest": vector_digest(vector),
                                        "returned_model": raw["model"], "response_artifact": response_path, "usage": raw.get("usage"),
                                        "created_at": datetime.now(UTC).isoformat()})
                vectors[ih] = {**cached_vector(store, path, digest, ih), "cache": path}
        with repo.connection() as conn:
            repo.guard(conn, job)
            locked = {r["moment_id"]: r for r in conn.execute(
                "SELECT moment_id, moment_body, quote_verified, is_current FROM key_moments WHERE moment_id = ANY(%s) FOR UPDATE",
                (list(todo),))}
            for moment_id, (ih, _) in todo.items():
                row = locked.get(moment_id)
                text = embedding_text(row["moment_body"]) if row else None
                if row is None or not row["quote_verified"] or not row["is_current"] or text is None or input_hash(text) != ih:
                    skipped["changed"] += 1  # changed while the vectors were being made
                    continue
                vector = vectors[ih]["vector"]
                if not vector_valid(vector):
                    raise ValueError("A moment vector is not usable")
                conn.execute("""UPDATE key_moments SET embedding=%s, embedding_model=%s, embedding_input_hash=%s
                    WHERE moment_id=%s AND quote_verified AND is_current""",
                             (np.asarray(vector, dtype=np.float32), models.embedding_model, ih, moment_id))
                embedded += 1
            done = min(start + batch, len(frozen))
            conn.execute("""UPDATE pipeline_jobs SET completed_units=%s, total_units=%s, current_step='embedding_moments',
                current_message=%s, updated_at=now() WHERE job_id=%s""",
                         (done, len(frozen), f"{done}/{len(frozen)} moments handled", job["job_id"]))
    result = {"contract": digest, "input_version": INPUT_VERSION, "moments": len(frozen), "embedded": embedded,
              "cache_reused": reused, "embedding_dispatches": requests, "skipped": skipped,
              "input_set_hash": refs["input_set_hash"]}
    with repo.connection() as conn:
        repo.finish(conn, job, result, message=f"{embedded} moments embedded, {sum(skipped.values())} left as they were")
