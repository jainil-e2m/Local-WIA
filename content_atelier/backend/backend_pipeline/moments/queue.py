"""Queueing a document's extraction (plan 2.B2, 2.B11): one run, one `moment_extraction` job per document.

A run with `run_scope = 'document_extraction'` and no week holds one job for each included document it was asked to read, the
way `documents.intake.queue_normalisation` queues one normalise job per document. A job names its document
(`transcript_id`) and its queue explicitly: `bulk` for a backfill, `default` for a cycle. Its idempotency key is the stage, the
document, the document's content hash, the extractor profile and the knowledge base the prompt reads (its stable refs: the
version and the identity documents), so a document that was extracted is never queued again by accident; asking again for a
document whose job exists reports it as already queued, running, completed or failed instead of creating a second job.

Excluded documents (`included = false`), copies of another document and documents not yet normalised create no job: the
selection helpers in `documents/select.py` never return them and `queue_extraction` refuses them by name.

A live run needs an active run plan (E.B1) that covers the stage and the model and is bound to this run's input set (or to
any, `*`), with enough calls left for one per document. It is refused here, before any job exists; the provider checks it
again at every call.
"""
from __future__ import annotations

from datetime import UTC, datetime

from psycopg.types.json import Jsonb

from .. import costs
from ..jobs import policy
from ..repository import insert
from ..store import canonical_hash
from ..token_budget import BYTES_PER_TOKEN
from . import scenes

RUN_SCOPE = "document_extraction"
STAGE = "moment_extraction"
MODES = {"cached": "replay", "live": "live", "synthetic": "synthetic"}
CHARACTERS_PER_TOKEN = 4


def extraction_key(document: dict, profile: str, knowledge_base: dict | None, model: str | None = None) -> str:
    """Stage, document, content, extractor profile and knowledge-base refs: what makes two extractions the same extraction.
    `model` is named only for a document queued again after its failed job's model was replaced (`queue_extraction`), so
    every other key stays what it was."""
    return canonical_hash([STAGE, document["transcript_id"], document["content_hash"], profile, knowledge_base,
                           *([model] if model else [])])


def view_hash(document: dict) -> str:
    return canonical_hash([document["original_text"], document["passage_map"], document["source_metadata"]])


def frozen_documents(documents: list[dict]) -> list[dict]:
    return [{"id": d["transcript_id"], "hash": d["content_hash"], "view_hash": view_hash(d)}
            for d in sorted(documents, key=lambda d: d["transcript_id"])]


def input_set_hash(documents: list[dict]) -> str:
    """The input set a plan is approved for, in the form `storage_cli plan input-hash` prints for a run (S.B2 review)."""
    return "sha256:" + canonical_hash(frozen_documents(documents))


def knowledge_base(repo, models, mode: str):
    """The extraction stage's context (roster and process catalogue) from the assembly service, and its stable refs."""
    from ..knowledge import held_out
    from ..knowledge.assembly import assemble, stable_refs
    kb = assemble("extraction", root=models.knowledge_base_root, connection=repo.connection, allow_placeholders=mode == "synthetic")
    if mode == "live":
        held_out.check_live(kb.text)
    return kb, stable_refs(kb.refs())


def classify(conn, documents: list[dict], profile: str, kb_refs: dict | None) -> tuple[list[dict], list[dict]]:
    """Split documents into the ones that need a job and the ones that already have one for this very extraction."""
    todo, existing = [], []
    for document in documents:
        key = extraction_key(document, profile, kb_refs)
        job = conn.execute("SELECT job_id,status,run_id FROM pipeline_jobs WHERE idempotency_key=%s", ("extract:" + key,)).fetchone()
        if job is None:
            todo.append(document)
        else:
            existing.append({"transcript_id": document["transcript_id"], "job_id": job["job_id"], "status": job["status"], "key": key})
    return todo, existing


def refuse_unextractable(documents: list[dict]) -> None:
    """A document that is excluded, a copy, or not yet normalised creates no job (2.B9): said by name, never dropped silently."""
    for d in documents:
        if not d.get("included"):
            raise ValueError(f"Document {d['transcript_id']} is excluded ({d.get('exclusion_reason')}); it creates no extraction job")
        if d.get("canonical_document_id"):
            raise ValueError(f"Document {d['transcript_id']} is a copy of {d['canonical_document_id']}; extract that one")
        if d.get("normalised_at") is None:
            raise ValueError(f"Document {d['transcript_id']} has not been normalised yet")


def pilot(documents: list[dict], n: int) -> list[dict]:
    """The first `n` documents spread across call types: each call type oldest first (undated last), one document from each
    type in turn (types in name order), so a person reading the pilot sees every kind of call before any kind twice."""
    if n < 1:
        raise ValueError("A pilot needs at least one document")
    far = datetime.max.replace(tzinfo=UTC)
    groups: dict[str, list[dict]] = {}
    for d in sorted(documents, key=lambda d: (d.get("occurred_at") or far, d["transcript_id"])):
        groups.setdefault(d.get("call_type") or "unclassified", []).append(d)
    chosen: list[dict] = []
    while len(chosen) < n and any(groups.values()):
        for call_type in sorted(groups):
            if groups[call_type] and len(chosen) < n:
                chosen.append(groups[call_type].pop(0))
    return chosen


def pending_documents(conn, profile: str | None = None) -> list[dict]:
    """Included, normalised, non-copy documents that this scene profile has not extracted, oldest first: the backfill's and
    the pilot's selection (`--all-pending`, `--pilot`).

    "Not extracted" is per profile, not `transcripts.extraction_status`: a document a weekly run read is marked `completed`
    (by the run, or by migration 007 for Weeks 1 to 5) but holds no scene from this profile, so it is still pending here. A
    document with a per-document job of this profile that is queued, running or completed is not; one whose job failed is
    (queueing it again reports the failed job, and `--retry-failed` revives it)."""
    from ..documents.select import SELECTABLE
    from ..settings_store import value
    profile = profile or value("moments.extraction_profile", conn)
    # SELECTABLE names the table `transcripts` (its current-revision check refers to it), so no alias here.
    return conn.execute(f"""SELECT * FROM transcripts WHERE {SELECTABLE} AND NOT EXISTS (
            SELECT 1 FROM pipeline_jobs j JOIN pipeline_runs pr ON pr.run_id = j.run_id
            WHERE j.stage = %(stage)s AND j.transcript_id = transcripts.transcript_id AND j.status <> 'failed'
              AND pr.run_scope = %(scope)s AND pr.input_refs->>'extraction_profile' = %(profile)s)
        ORDER BY occurred_at NULLS LAST, transcript_id""", {"stage": STAGE, "scope": RUN_SCOPE, "profile": profile}).fetchall()


# ---- the plan a live run needs ---------------------------------------------------------------------------------------------

def plan_row(store) -> dict:
    """The stored plan behind a plan store (database or file)."""
    from ..database import connect
    from ..llm import run_plans
    from ..llm.standing import StandingPlanStore
    if isinstance(store, StandingPlanStore):
        # This week's extraction budget (6.B3).
        return store.plan_for(STAGE)[1]
    if isinstance(store, run_plans.SqlPlanStore):
        with connect(store.database_url, vectors=False) as conn:
            row = conn.execute("SELECT * FROM run_plans WHERE plan_id=%s", (store.plan_id,)).fetchone()
        if row is None:
            raise run_plans.RunPlanError(f"Run plan {store.plan_id} does not exist")
        return row
    return store.show()["plan"]


def require_plan(model: str, input_hash: str, calls: int, *, plan=None) -> dict:
    """Refuse a live extraction unless an active plan covers the stage and model, is bound to this input set (or to any) and has
    a call left for each document. Returns the plan's id and what is left."""
    from ..llm import run_plans
    store = plan if plan is not None else run_plans.from_environment()
    if isinstance(store, run_plans.NoPlan):
        raise run_plans.RunPlanError("A live extraction needs an active run plan (E.B1). Create one with `storage_cli plan create "
                                     f"--stage {STAGE} --model {model} --input-set-hash {input_hash} ...` and set "
                                     "ATELIER_RUN_PLAN_ID (or ATELIER_RUN_PLAN_FILE for a file plan).")
    row = plan_row(store)
    run_plans.check_allowed(row, stage=STAGE, model=model, now=datetime.now(UTC), input_set_hash=input_hash)
    left = int(row["max_calls"]) - int(row["calls_used"])
    if left < calls:
        raise run_plans.RunPlanError(f"Run plan {row['plan_id']} has {left} calls left for {calls} documents; create a plan "
                                     "with a higher call limit (a repair call is a call)")
    return {"plan_id": row["plan_id"], "calls_left": left, "cost_cap_usd": float(row["max_cost_usd"]),
            "cost_used_usd": float(row["cost_used_usd"])}


# ---- the estimate ------------------------------------------------------------------------------------------------------------

def estimate(repo, models, documents: list[dict], *, profile: str, mode: str = "cached") -> dict:
    """What extracting these documents would cost, before anything is sent: no model is called.

    Input tokens are counted from the prompt each document would send (the template, the knowledge base, the document context
    and the packet) at about four characters a token, beside the conservative one-token-per-two-bytes allowance the card
    preflight uses (`token_budget.BYTES_PER_TOKEN`), because Luna and Sol have no public tokenizer. Output tokens are an assumption
    (`moments.estimate.output_tokens_per_document`), reasoning included, to be replaced by the pilot's measured figure.
    The price comes from the table in costs.py, or from the settings when the model is not in it."""
    from ..settings_store import values
    from ..storage_sources import reconstruct
    from ..weekly import meeting_inventory
    kb, kb_refs = knowledge_base(repo, models, mode)
    with repo.connection() as conn:
        todo, existing = classify(conn, documents, profile, kb_refs)
        terms = conn.execute("SELECT term,kind,variants FROM glossary_terms WHERE status='active'").fetchall()
        v = values(("moments.estimate.output_tokens_per_document", "moments.estimate.input_usd_per_million",
                    "moments.estimate.output_usd_per_million"), conn)
    schema_characters = len(str(scenes.schema(profile)))
    characters = bytes_total = 0
    for document in todo:
        _, packet, refs = reconstruct([document])
        system, user = scenes.prompt_for(profile, packet, meeting_inventory(refs), kb.text, document, terms)
        characters += len(system) + len(user) + schema_characters
        bytes_total += len(system.encode()) + len(user.encode()) + schema_characters
    model = models.model_for("moment_extraction")
    input_tokens = characters // CHARACTERS_PER_TOKEN
    output_tokens = len(todo) * v["moments.estimate.output_tokens_per_document"]
    price = costs.price_of(model, input_override=v["moments.estimate.input_usd_per_million"],
                           output_override=v["moments.estimate.output_usd_per_million"])
    return {"profile": profile, "model": model, "documents": len(todo), "already_have_a_job": existing,
            "input_characters": characters, "input_tokens_estimate": input_tokens, "input_token_allowance_conservative": -(-bytes_total // BYTES_PER_TOKEN),
            "output_tokens_assumed": output_tokens, "price_usd_per_million": {"input": price[0], "output": price[1]} if price else None,
            "estimated_cost_usd": costs.estimate_usd(model, input_tokens, output_tokens,
                                                     input_override=v["moments.estimate.input_usd_per_million"],
                                                     output_override=v["moments.estimate.output_usd_per_million"]),
            "input_set_hash": input_set_hash(todo) if todo else None, "knowledge_base_version": kb.refs().get("version"),
            "provider_calls_made": 0,
            "note": "An estimate, not a charge: hosted usage is authoritative, and reasoning tokens are part of the output."}


# ---- queueing ----------------------------------------------------------------------------------------------------------------

def queue_extraction(repo, models, documents: list[dict], *, mode: str, actor: str, queue: str, profile: str | None = None,
                     retry_failed: bool = False, plan=None) -> dict:
    """Queue one `moment_extraction` job per document that does not already have one for this extraction.

    `mode` is replay (saved responses only), live (a paid run, under a plan) or synthetic (the offline provider, in a synthetic
    database). `queue` is named by the caller: `bulk` for a backfill, `default` for a cycle."""
    from ..settings_store import value
    if mode not in {"replay", "live", "synthetic"}:
        raise ValueError("mode must be replay, live or synthetic")
    if queue not in policy.EDITORIAL_QUEUES:
        raise ValueError(f"queue must be one of {', '.join(policy.EDITORIAL_QUEUES)}")
    if mode == "synthetic" and not repo.settings.synthetic:
        raise ValueError("Synthetic providers require a separate synthetic database")
    refuse_unextractable(documents)
    with repo.connection() as conn:
        profile = profile or value("moments.extraction_profile", conn)
    if profile not in scenes.PROFILES:
        raise ValueError(f"Unknown scene profile {profile}")
    if mode == "live":
        if not repo.settings.generation_enabled:
            raise ValueError("SQL generation permission is disabled")
        models.require_explicit_models()
    kb, kb_refs = knowledge_base(repo, models, mode)
    model = models.model_for("moment_extraction")
    with repo.connection() as conn:
        todo, existing = classify(conn, documents, profile, kb_refs)
        revived, remodelled = [], set()
        for index, found in enumerate(existing):
            frozen = conn.execute("""SELECT pr.input_refs->'models'->>'moment_extraction' AS model FROM pipeline_jobs j
                JOIN pipeline_runs pr USING (run_id) WHERE j.job_id=%s""", (found["job_id"],)).fetchone()["model"]
            if found["status"] == "failed" and frozen and frozen != model:
                # Revived, the job would be refused for the model it was frozen with (moments.jobs). The document's extraction
                # under today's model is a job of its own (its key names the model); the failed one stays as the record (found
                # by the N1 shakedown).
                document = next(d for d in documents if d["transcript_id"] == found["transcript_id"])
                key = extraction_key(document, profile, kb_refs, model)
                job = conn.execute("SELECT job_id,status,run_id FROM pipeline_jobs WHERE idempotency_key=%s", ("extract:" + key,)).fetchone()
                if job is None:
                    if retry_failed:
                        remodelled.add(found["transcript_id"])
                        todo.append(document)
                    continue
                found = existing[index] = {"transcript_id": found["transcript_id"], "job_id": job["job_id"], "status": job["status"],
                                           "key": key}
            if found["status"] == "failed" and retry_failed:
                conn.execute("""UPDATE pipeline_jobs SET status='queued',error_summary=NULL,current_message='Waiting to extract scenes',
                    finished_at=NULL,updated_at=now() WHERE job_id=%s""", (found["job_id"],))
                conn.execute("""UPDATE pipeline_runs SET status='queued',error_summary=NULL,updated_at=now()
                    WHERE run_id=(SELECT run_id FROM pipeline_jobs WHERE job_id=%s)""", (found["job_id"],))
                conn.execute("UPDATE transcripts SET extraction_status='queued' WHERE transcript_id=%s AND included", (found["transcript_id"],))
                revived.append(found["job_id"])
        waiting = [f for f in existing if f["job_id"] not in revived and f["transcript_id"] not in remodelled]
        if not todo:
            return {"run_id": None, "queue": queue, "profile": profile, "jobs": [], "retried": revived, "skipped": waiting}
        input_hash = input_set_hash(todo)
        plan_info = require_plan(model, input_hash, len(todo), plan=plan) if mode == "live" else None
        from ..settings_store import snapshot_refs
        refs = {"transcripts": frozen_documents(todo), "week_index": 0, "mode": mode, "synthetic": repo.settings.synthetic,
                "coverage": "document_extraction", "selected_by": "documents", "extraction_profile": profile,
                "models": {"moment_extraction": model}, "knowledge_base": kb_refs, "queue": queue,
                **snapshot_refs("weekly", models=models, storage=repo.settings, conn=conn)}
        keys = {d["transcript_id"]: extraction_key(d, profile, kb_refs, model if d["transcript_id"] in remodelled else None)
                for d in todo}
        run_id = "docext_" + canonical_hash(sorted(keys.values()))[:24]
        insert(conn, "pipeline_runs", {"run_id": run_id, "week_id": None, "run_scope": RUN_SCOPE, "trigger_type": "manual",
                                       "triggered_by": actor, "input_refs": refs}, conflict=True)
        jobs = []
        for document in sorted(todo, key=lambda d: d["transcript_id"]):
            key = keys[document["transcript_id"]]
            job_id = "extjob_" + key[:24]
            insert(conn, "pipeline_jobs", {"job_id": job_id, "run_id": run_id, "week_id": None, "transcript_id": document["transcript_id"],
                                           "stage": STAGE, "idempotency_key": "extract:" + key, "input_hash": key,
                                           "executor": "rq", "queue": queue, "progress_details": Jsonb({"dependencies": []}),
                                           "current_message": "Waiting to extract scenes"}, conflict=True)
            jobs.append(job_id)
        conn.execute("UPDATE transcripts SET extraction_status='queued' WHERE transcript_id=ANY(%s) AND included",
                     ([d["transcript_id"] for d in todo],))
        repo.event(conn, run_id, "submitted", f"Extraction of {len(jobs)} documents queued on {queue}; no provider was called",
                   details={"profile": profile, "queue": queue, "mode": mode})
    return {"run_id": run_id, "queue": queue, "profile": profile, "mode": mode, "jobs": jobs, "retried": revived, "skipped": waiting,
            "requeued_for_new_model": sorted(remodelled),
            "input_set_hash": input_hash, "plan": plan_info}


def settle_run(conn, run_id: str, *, done_word: str = "extracted") -> dict:
    """A document run is as finished as its jobs. While any job is open the run keeps running, so a failed document never stops
    the others; when none is, it is completed, partially completed (some failed) or failed (all failed). `done_word` says what
    a finished job did (jobs.policy.PER_DOCUMENT_SCOPES): extracted, or normalised for an import."""
    # Two workers finishing the last two jobs at once must not both see the other's job still open: take the run's lock first.
    conn.execute("SELECT 1 FROM pipeline_runs WHERE run_id=%s FOR UPDATE", (run_id,))
    n ={r["status"]: r["n"] for r in conn.execute("SELECT status,count(*) AS n FROM pipeline_jobs WHERE run_id=%s GROUP BY status", (run_id,))}
    total, failed, done = sum(n.values()), n.get("failed", 0), n.get("completed", 0)
    still = total - failed - done
    status = "running" if still else ("partially_completed" if failed and done else "failed" if failed else "completed")
    error = conn.execute("SELECT error_summary FROM pipeline_jobs WHERE run_id=%s AND status='failed' ORDER BY finished_at LIMIT 1",
                         (run_id,)).fetchone()
    message = f"{done} of {total} documents {done_word}" + (f", {failed} failed" if failed else "") + (f", {still} to go" if still else "")
    conn.execute("""UPDATE pipeline_runs SET status=%s,has_partial_failures=%s,current_message=%s,error_summary=%s,
        finished_at=CASE WHEN %s THEN NULL ELSE now() END,updated_at=now() WHERE run_id=%s""",
                 (status, bool(failed), message, error["error_summary"] if error else None, bool(still), run_id))
    return {"run_id": run_id, "status": status, "completed": done, "failed": failed, "open": still}
