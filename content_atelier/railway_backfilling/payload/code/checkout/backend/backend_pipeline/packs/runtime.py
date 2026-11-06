"""Production inference receipts/cache. No external execution without explicit flags."""

import json
from pathlib import Path

from ..briefs import gate_two
from ..costs import call_record, write_run_summary
from ..models import StageArtifact
from ..provider import LiveProvider, chat_body
from ..store import JsonStore, canonical_hash
from .contracts import VERSION, Carousel, Email, Reel, Review

WORKFLOW = VERSION


def system(stage):
    return (Path(__file__).resolve().parent.parent / "prompt_templates" / f"{stage}.v1.md").read_text(encoding="utf-8")


def execution_contract(settings, models=None):
    if models is None:
        from ..config import Settings

        models = Settings.from_env()
    if not settings.synthetic and (not settings.pack_writer_model or not settings.pack_review_model):
        raise ValueError("Configure exact pack writer and reviewer models before production")
    return {
        "writer": settings.pack_writer_model or "synthetic",
        "endpoint": models.openrouter_base_url,
        "max_tokens": models.llm_completion_tokens,
        "reasoning_effort": models.llm_reasoning_effort,
        "response_format": models.llm_response_format,
        "synthetic": settings.synthetic,
        "reviewer": settings.pack_review_model or "synthetic",
        "prompts": {s: canonical_hash(system(s)) for s in ("pack_write", "pack_review")},
        "schemas": [canonical_hash(s.model_json_schema()) for s in (Email, Carousel, Reel, Review)],
    }


def model_id(worker, stage):
    contract = execution_contract(worker.storage, worker.models)
    return contract["reviewer" if stage == "pack_review" else "writer"]


def check_dependencies(worker, run):
    refs = run["input_refs"]
    if not worker.storage.packs_enabled or refs["execution_contract"] != execution_contract(worker.storage, worker.models):
        raise ValueError("Production is disabled or frozen execution contract changed")
    with worker.repo.connection() as conn:
        brief = conn.execute("SELECT * FROM content_briefs WHERE brief_id=%s", (refs["brief"]["brief_id"],)).fetchone()
        if not brief or brief["content_hash"] != refs["brief"]["content_hash"] or brief["approval_status"] != "approved":
            raise ValueError("Approved production brief changed")
        reasons = gate_two.blockers(conn, brief)
        if reasons:
            raise ValueError("; ".join(reasons))


def record(worker, job, run, stage, fingerprint, raw=None, *, dispatched=False, reused=False):
    store = JsonStore(worker.storage.artifact_root)
    directory = f"pack-runs/{run['run_id']}"
    value = call_record(
        raw=raw,
        dispatched=dispatched and not worker.storage.synthetic,
        reused=reused,
        stage=stage,
        job_id=job["job_id"],
        attempt=job["attempt_count"],
        fingerprint=fingerprint,
        synthetic=worker.storage.synthetic,
        real_external_dispatch=dispatched and not worker.storage.synthetic,
    )
    store.write_json(
        f"{directory}/costs/{job['job_id']}-{job['attempt_count']}-{stage}-{fingerprint}.json", value, overwrite=True
    )
    return write_run_summary(store, directory, stages_to_report=("pack_write", "pack_review"))


def call(worker, job, run, stage, schema, packet):
    check_dependencies(worker, run)
    prompt = system(stage)
    payload = json.dumps(packet, ensure_ascii=False, sort_keys=True, default=str)
    model = model_id(worker, stage)
    request = chat_body(
        model=model,
        system=prompt,
        user=payload,
        schema=schema.model_json_schema(),
        max_tokens=worker.models.llm_completion_tokens,
        reasoning_effort=worker.models.llm_reasoning_effort,
        response_format=worker.models.llm_response_format,
    )
    if len(json.dumps(request, ensure_ascii=False)) > worker.storage.brief_max_characters:
        raise ValueError("Required pack request exceeds preflight; essential evidence was not omitted")
    fp = canonical_hash(
        {
            "workflow": WORKFLOW,
            "stage": stage,
            "request": request,
            "endpoint": worker.models.openrouter_base_url,
            "synthetic": worker.storage.synthetic,
        }
    )
    store = JsonStore(worker.storage.artifact_root)
    cache = f"pack-cache/{fp}.json"
    if store.path(cache).is_file():
        data = store.read_json(cache)
        if data["fingerprint"] != fp or canonical_hash(data["output"]) != data["output_hash"]:
            raise ValueError("Brief response cache integrity failed")
        result = schema.model_validate(data["output"])
        old = store.read_json(data["artifact"])
        record(worker, job, run, stage, fp, old.get("raw_response"), reused=True)
        with worker.repo.connection() as conn:
            worker.repo.event(
                conn,
                run["run_id"],
                "pack_cache_reused",
                stage,
                job=job,
                details={"fingerprint": fp, "artifact": data["artifact"]},
            )
        return result
    base = f"pack-attempts/{job['job_id']}/{job['attempt_count']}/{fp}"
    store.write_json(base + "/request.json", request)
    recovered = None
    root = store.path("pack-attempts", job["job_id"])
    for path in sorted(root.glob(f"*/{fp}/received.json"), reverse=True):
        recovered = json.loads(path.read_text(encoding="utf-8"))
        break
    if recovered is None:
        for path in sorted(root.glob(f"*/{fp}/response.raw.json"), reverse=True):
            saved = json.loads(path.with_name("request.json").read_text(encoding="utf-8"))
            if saved != request:
                raise ValueError("Recovered request does not match its fingerprint")
            raw = json.loads(path.read_text(encoding="utf-8"))
            if raw.get("error"):
                continue
            choice = raw["choices"][0]
            if choice.get("finish_reason") not in {None, "stop"}:
                raise ValueError("Recovered provider response was incomplete or refused")
            content = choice["message"].get("content")
            if not isinstance(content, (str, dict)):
                raise TypeError("Recovered provider response has no JSON content")
            recovered = {
                "output": json.loads(content) if isinstance(content, str) else content,
                "metadata": {"raw": raw, "recovered": True},
            }
            break
    if recovered:
        output, metadata = recovered["output"], recovered["metadata"]
    else:
        mode = run["input_refs"]["mode"]
        if mode != "synthetic" and not (
            mode == "live" and worker.storage.generation_enabled and worker.storage.pack_live_enabled
        ):
            raise ValueError("No compatible pack response is cached; external pack calls are disabled")
        with worker.repo.connection() as conn:
            worker.repo.guard(conn, job)
            count = conn.execute(
                "SELECT count(*) AS n FROM pipeline_events WHERE run_id=%s AND event_type='pack_provider_dispatch'",
                (run["run_id"],),
            ).fetchone()["n"]
            if count >= 8:
                raise ValueError("Pack chat-call budget exhausted")
            worker.repo.event(
                conn,
                run["run_id"],
                "pack_provider_dispatch",
                stage,
                job=job,
                details={
                    "model": model,
                    "fingerprint": fp,
                    "request_artifact": base + "/request.json",
                    "synthetic": worker.storage.synthetic,
                },
            )
        provider = worker.provider
        record(worker, job, run, stage, fp, dispatched=True)
        if mode != "synthetic":

            def receipt(_, raw):
                store.write_json(base + "/response.raw.json", raw)
                record(worker, job, run, stage, fp, raw, dispatched=True)

            provider = LiveProvider(
                llm_base_url=worker.models.openrouter_base_url,
                moments_model=model,
                angles_model=model,
                moments_key=worker.models.openrouter_angles_key,
                angles_key=worker.models.openrouter_angles_key,
                embedding_base_url=worker.models.embedding_base_url,
                embedding_model=worker.models.embedding_model,
                embedding_key=worker.models.embedding_api_key,
                dimensions=1536,
                timeout=worker.models.request_timeout_seconds,
                max_tokens=worker.models.llm_completion_tokens,
                reasoning_effort=worker.models.llm_reasoning_effort,
                response_format=worker.models.llm_response_format,
                on_response=receipt,
            )
        if not provider:
            raise ValueError("Synthetic pack provider is missing")
        output, metadata = provider.json_call(
            stage=stage, system=prompt, user=payload, schema=schema.model_json_schema(), fingerprint=fp
        )
        store.write_json(base + "/received.json", {"output": output, "metadata": metadata})
    record(worker, job, run, stage, fp, metadata.get("raw"), dispatched=not bool(recovered), reused=bool(recovered))
    result = schema.model_validate(output)
    artifact = StageArtifact(
        artifact_id="pack_artifact_" + fp[:24],
        run_id=run["run_id"],
        stage=stage,
        request_fingerprint=fp,
        prompt_version=WORKFLOW,
        model_id=model,
        status="validated",
        input_hashes=[canonical_hash(packet)],
        request=request,
        output=output,
        output_hash=canonical_hash(output),
        raw_response=metadata.get("raw"),
        metadata=metadata,
        usage=metadata.get("raw", {}).get("usage"),
    )
    store.write_json(base + "/validated.json", artifact.model_dump(mode="json"))
    store.cache_artifact(artifact, base + "/validated.json")
    store.write_json(
        cache, {"fingerprint": fp, "output": output, "output_hash": canonical_hash(output), "artifact": base + "/validated.json"}
    )
    with worker.repo.connection() as conn:
        worker.repo.event(
            conn,
            run["run_id"],
            "pack_response_validated",
            stage,
            job=job,
            details={
                "fingerprint": fp,
                "artifact": base + "/validated.json",
                "usage": artifact.usage,
                "recovered": bool(recovered),
            },
        )
    return result
