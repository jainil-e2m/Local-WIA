"""The `moment_extraction` job of one document (plan 2.B2): the handler a queue worker runs for it.

`SQLWorker.execute` hands a `moment_extraction` job that names a document to `execute` here; the weekly per-run path is
unchanged. The handler reads the document from the database, builds the scene profile's packet (the roster and process
catalogue from the context-assembly service, the call type, the speakers' roles, glossary hints and the handling tags),
makes the one call through the llm module (cache, run plan, routing, an `llm_runs` row, exactly one repair on a schema
failure), checks every scene alone (`moments/extract.py`), and stores the result through the one ledger writer
(`moments/store.py`).

Re-running a completed document makes no provider call, for two reasons that each suffice: the handler stops before the call
when the ledger already holds this very extraction (same key: document, content, profile, knowledge base), and the call
itself is keyed by its request, so a saved validated response is reused whatever the job. A response that fails its schema
twice fails this document's job only; the run keeps going and the failed job can be retried from the saved response.
"""
from __future__ import annotations

from ..store import canonical_hash
from . import extract, queue, scenes, store


def already_extracted(conn, transcript_id: str, key: str, job_id: str) -> dict | None:
    """What a previous extraction of this very input left: its job (a document with no scene leaves no row) and its moments."""
    job = conn.execute("""SELECT job_id,result_refs FROM pipeline_jobs WHERE stage='moment_extraction' AND transcript_id=%s
        AND input_hash=%s AND status='completed' AND job_id<>%s ORDER BY finished_at DESC LIMIT 1""",
                       (transcript_id, key, job_id)).fetchone()
    rows = conn.execute("""SELECT moment_id,quote_verified FROM key_moments WHERE document_id=%s AND is_current
        AND checks->'extraction'->>'extraction_key'=%s""", (transcript_id, key)).fetchall()
    if job is None and not rows:
        return None
    return {"job_id": job["job_id"] if job else None, "moment_ids": [r["moment_id"] for r in rows if r["quote_verified"]],
            "unverified_ids": [r["moment_id"] for r in rows if not r["quote_verified"]]}


def execute(worker, job) -> None:
    """Extract one document's scenes and finish its job."""
    from ..knowledge.assembly import stable_refs
    from ..storage_sources import reconstruct
    repo, transcript_id = worker.repo, job["transcript_id"]
    with repo.connection() as conn:
        run = conn.execute("SELECT * FROM pipeline_runs WHERE run_id=%s", (job["run_id"],)).fetchone()
        document = conn.execute("SELECT * FROM transcripts WHERE transcript_id=%s", (transcript_id,)).fetchone()
        terms = conn.execute("SELECT term,kind,variants FROM glossary_terms WHERE status='active'").fetchall()
    if run is None or run["run_scope"] != queue.RUN_SCOPE:
        raise ValueError("A moment_extraction job that names a document belongs to a document_extraction run")
    refs = run["input_refs"]
    frozen = next((t for t in refs["transcripts"] if t["id"] == transcript_id), None)
    if frozen is None or document is None:
        raise ValueError("The document is not part of this run")
    if document["content_hash"] != frozen["hash"] or queue.view_hash(document) != frozen["view_hash"]:
        raise ValueError("Frozen source identity changed; queue the extraction again")
    profile = refs["extraction_profile"]
    if profile not in scenes.PROFILES:
        raise ValueError(f"Unknown scene profile {profile}")
    model = worker.models.model_for("moment_extraction")
    if refs["models"]["moment_extraction"] != model:
        raise ValueError(f"The extraction model frozen at queue time ({refs['models']['moment_extraction']}) differs from the "
                         f"worker's ({model}); restore it, or queue the extraction again (`moments extract ... --retry-failed` gives the document a job "
                         "under today's model)")
    # An excluded document (excluded after it was queued), or one that became a copy, is skipped: no scene is stored for it.
    if not document["included"] or document["canonical_document_id"]:
        why = f"excluded ({document['exclusion_reason']})" if not document["included"] else f"a copy of {document['canonical_document_id']}"
        with repo.connection() as conn:
            repo.finish(conn, job, {"skipped": why, "dispatched": False, "provider_calls": 0}, message=f"Skipped: document is {why}")
            conn.execute("UPDATE transcripts SET extraction_status=%s WHERE transcript_id=%s",
                         ("not_applicable" if not document["included"] else document["extraction_status"], transcript_id))
        return
    transcripts, packet, ref_map = reconstruct([document])
    p, manifest = worker.adapter(run, transcripts, ref_map)
    kb = p.context("extraction", manifest.mode)
    if stable_refs(kb.refs()) != refs["knowledge_base"]:
        raise ValueError("The knowledge base frozen at queue time changed (a new approved version); queue the extraction again")
    key = job["input_hash"]
    with repo.connection() as conn:
        done = already_extracted(conn, transcript_id, key, job["job_id"])
        if done is not None:
            repo.guard(conn, job)
            repo.finish(conn, job, {"extraction_key": key, "extraction_profile": profile, "reused_from_job": done["job_id"],
                                    "moment_ids": done["moment_ids"], "unverified_ids": done["unverified_ids"], "dispatched": False,
                                    "provider_calls": 0}, message="Already extracted; no provider call")
            return
    def finish(conn, saved, result, artifact):
        repo.finish(conn, job, {
            "extraction_key": key, "extraction_profile": profile, "moment_ids": saved["moment_ids"],
            "unverified_ids": saved["unverified_ids"], "artifact_id": artifact.artifact_id, "request_fingerprint": artifact.request_fingerprint,
            "dispatched": artifact.request_fingerprint in p._dispatched,
            "cache_reused": artifact.request_fingerprint not in p._dispatched,
            "revalidated_from_attempt": artifact.metadata.get("revalidated_from_attempt"),
            "repaired_response": bool(artifact.metadata.get("repair")), "coverage": "complete_delivery_acknowledged",
            "coverage_notes": artifact.output["coverage_notes"], **result.summary(), "coverage_is_comprehension_proof": False,
            "extraction_knowledge_base": kb.refs()},
            message=f"Saved {len(saved['moment_ids'])} scenes"
                    + (f"; {len(result.repairs)} quotes repaired" if result.repairs else "")
                    + (f"; {len(result.unverified)} unverified, not used as proof" if result.unverified else "")
                    + ("" if result.moments or result.unverified else " (the document holds none)"))

    extract_document(worker, run, job, document, profile=profile, key=key, terms=terms, p=p, manifest=manifest, kb=kb,
                     reconstructed=(transcripts, packet, ref_map), then=finish)


def extract_document(worker, run, job, document, *, profile: str, key: str, terms, p, manifest, kb, reconstructed, then=None):
    """One document's scene call, scene-by-scene partition and save: the part a document's own job and the weekly cycle
    (E.B12) share, so both store the same scenes, with the same repairs, under the same extraction key.

    The call is made through `p` (the caller's run: its mode, plan and cache), the response is checked by
    `extract.partition_scenes`, and the result is saved through the one ledger writer, superseding an earlier extraction of
    this document under this profile. `then(conn, saved, result, artifact)` runs in the saving transaction. Returns
    `(saved, result, artifact)`."""
    from ..weekly import meeting_inventory
    repo, transcript_id = worker.repo, document["transcript_id"]
    transcripts, packet, ref_map = reconstructed
    system, user = scenes.prompt_for(profile, packet, meeting_inventory(ref_map), kb.text, document, terms)
    input_hash = canonical_hash({"system": system, "user": user,
                                 "source": [{"source_id": t.source_id, "revision": t.content_hash} for t in transcripts]})
    run_dir = f"experiments/sql/runs/{run['run_id']}/documents/{transcript_id}"
    artifact = p._call_json("moment_extraction", manifest, run_dir, system, user, input_hash, scenes.schema(profile),
                            validate=lambda out: extract.partition_scenes(out, ref_map, transcripts, profile,
                                                                          call_type=document.get("call_type")), prompt_version=profile)
    result = extract.partition_scenes(artifact.output, ref_map, transcripts, profile, call_type=document.get("call_type"))
    p.store.write_json(f"{run_dir}/moment_validation.json", result.summary(), overwrite=True)
    provenance = {m.moment_id: {"extraction": {"profile": profile, "extraction_key": key, "local_key": result.local_keys[m.moment_id],
                                               "scene": result.scenes[m.moment_id], "artifact_id": artifact.artifact_id,
                                               "request_fingerprint": artifact.request_fingerprint, "job_id": job["job_id"]}}
                  for m in result.moments}
    with repo.connection() as conn:
        repo.guard(conn, job)
        worker.origin(conn, artifact, run)
        # An unverified record carries the key of the extraction that produced it, so a re-run finds it too.
        unverified = [{**u, "provenance": {"extraction": {"profile": profile, "extraction_key": key, "job_id": job["job_id"]}}}
                      for u in result.unverified]
        saved = store.save(conn, result.moments, [document], run_id=run["run_id"], week_id=None, extractor_version=profile,
                           unverified=unverified, repairs=result.repairs, provenance=provenance,
                           unverified_scope=f"{transcript_id}:{profile}", roster=kb.roster,
                           # A later extraction of this document under this profile replaces an earlier one as current.
                           supersede={"extraction_key": key, "job_id": job["job_id"]})
        if then is not None:
            then(conn, saved, result, artifact)
    return saved, result, artifact
