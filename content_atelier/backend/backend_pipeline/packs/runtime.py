"""Production inference receipts/cache. No external execution without explicit flags."""

import json
from pathlib import Path

from ..briefs import gate_two
from ..costs import call_record, write_run_summary
from ..llm import stage_body, workflow_fingerprint
from ..llm.workflow import chat
from ..store import canonical_hash
from ..artifacts import store_for
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
    store = store_for(worker.storage)
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


def _flow():
    from ..llm.workflow import Flow

    return Flow(name="pack", workflow=WORKFLOW, cache="pack-cache", attempts="pack-attempts", artifact_prefix="pack_artifact_",
                budget=8, live_enabled=lambda worker: worker.storage.pack_live_enabled, record=record)


def call(worker, job, run, stage, schema, packet):
    """A pack stage call; the call itself (cache, recovery, dispatch, record, one repair) is the llm module's (0.B4)."""
    check_dependencies(worker, run)
    prompt = system(stage)
    payload = json.dumps(packet, ensure_ascii=False, sort_keys=True, default=str)
    model = model_id(worker, stage)
    wire_schema = schema.model_json_schema()
    request = stage_body(worker.models, stage, prompt, payload, wire_schema, model=model)
    if len(json.dumps(request, ensure_ascii=False)) > worker.storage.brief_max_characters:
        raise ValueError("Required pack request exceeds preflight; essential evidence was not omitted")
    fp = workflow_fingerprint(workflow=WORKFLOW, stage=stage, request=request, endpoint=worker.models.openrouter_base_url,
                              synthetic=worker.storage.synthetic)
    return chat(_flow(), worker, job, run, stage=stage, model=model, prompt=prompt, payload=payload, request=request, fp=fp,
                schema=schema, wire_schema=wire_schema, packet=packet)
