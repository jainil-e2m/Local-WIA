"""A brief or pack stage call (plan 0.B4): the one implementation behind `briefs/runtime.call` and `packs/runtime.call`.

Both workflows share this layout, which saved briefs were written in and so stays unchanged: a response cache keyed by the
request fingerprint (`<flow>-cache/<fp>.json`), an attempts folder per job attempt with the request, the raw response and
the received output (`<flow>-attempts/<job>/<attempt>/<fp>/`), recovery of a response received by an earlier attempt, a
budget of chat calls per run, and an event per cache reuse, dispatch and validated response.

What this module adds to them is what every stage call gets: the provider built by `live_provider` (privacy routing, run
plan, per-stage effort), an `llm_runs` row for every call (a replay, an offline call and a refusal included), the prompt
and knowledge-base versions on the row, and exactly one repair call when the answer breaks its schema.
"""
from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass

from pydantic import ValidationError

from ..models import StageArtifact
from ..costs import response_usage
from ..store import JsonStore, canonical_hash
from ..artifacts import store_for
from .call import patient_call
from .providers import InvalidJson, NoJsonContent, live_provider
from .request import repair_fingerprint, repair_user
from .runs import LlmRuns


@dataclass(frozen=True)
class Flow:
    name: str                       # "brief" or "pack"
    workflow: str                   # recorded as the artifact's prompt version
    cache: str                      # folder of the response cache
    attempts: str                   # folder of the attempts
    artifact_prefix: str
    budget: int                     # chat calls per run, repairs included
    live_enabled: Callable          # (worker) -> bool: live calls of this kind are switched on
    record: Callable                # (worker, job, run, stage, fingerprint, raw=None, *, dispatched, reused) -> None


def _recover(store: JsonStore, flow: Flow, job, fp: str, request: dict):
    """The answer an earlier attempt of this job received for this exact request, if any."""
    folder = f"{flow.attempts}/{job['job_id']}"
    for key in store.attempt_files(folder, fp, "received.json"):
        return store.read_json(key)
    for key in store.attempt_files(folder, fp, "response.raw.json"):
        saved = store.read_json(key.rsplit("/", 1)[0] + "/request.json")
        if saved != request:
            raise ValueError("Recovered request does not match its fingerprint")
        raw = store.read_json(key)
        if raw.get("error"):
            continue
        choice = raw["choices"][0]
        if choice.get("finish_reason") == "length":
            # Cut off at its output limit: replaying it would fail the step again on every retry, so the call is made
            # again, at the limit the settings now give and with the one raised retry (N2, 23 October).
            continue
        if choice.get("finish_reason") not in {None, "stop"}:
            raise ValueError("Recovered provider response was incomplete or refused")
        content = choice["message"].get("content")
        if not isinstance(content, (str, dict)):
            raise ValueError("Recovered provider response has no JSON content")
        return {"output": json.loads(content) if isinstance(content, str) else content,
                "metadata": {"raw": raw, "recovered": True}}
    return None


def _dispatch(flow: Flow, worker, job, run, store, stage, model, fp, request, base, prompt, payload, wire_schema, context,
              runs: LlmRuns):
    """One chat call: the gate on live calls, the run's budget, the dispatch event, the provider, the saved receipt."""
    mode = run["input_refs"]["mode"]
    if mode != "synthetic" and not (mode == "live" and worker.storage.generation_enabled and flow.live_enabled(worker)):
        raise ValueError(f"No compatible {flow.name} response is cached; external {flow.name} calls are disabled")
    with worker.repo.connection() as conn:
        worker.repo.guard(conn, job)
        count = conn.execute("SELECT count(*) AS n FROM pipeline_events WHERE run_id=%s AND event_type=%s",
                             (run["run_id"], f"{flow.name}_provider_dispatch")).fetchone()["n"]
        # The budget limits calls that were answered: one the provider refused cost nothing and wrote nothing, and counting it
        # left a brief unable to finish after a passing rate limit (production, 2 November).
        count -= conn.execute("""SELECT count(*) AS n FROM llm_runs WHERE details->>'run_id'=%s AND status='failed'
            AND COALESCE(cost_usd,0)=0""", (run["run_id"],)).fetchone()["n"]
        if count >= flow.budget:
            raise ValueError(f"{flow.name.capitalize()} chat-call budget exhausted")
        worker.repo.event(conn, run["run_id"], f"{flow.name}_provider_dispatch", stage, job=job,
                          details={"model": model, "fingerprint": fp, "request_artifact": base + "/request.json",
                                   "synthetic": worker.storage.synthetic})
    provider = worker.provider
    flow.record(worker, job, run, stage, fp, dispatched=True)
    if mode != "synthetic":
        def receipt(_, raw):
            store.write_json(base + "/response.raw.json", raw)
            flow.record(worker, job, run, stage, fp, raw, dispatched=True)
        provider = live_provider(worker.models, storage=worker.storage, on_response=receipt, model=model)
    if not provider:
        raise ValueError(f"Synthetic {flow.name} provider is missing")
    return patient_call(provider, runs, stage=stage, model=model, system=prompt, user=payload, schema=wire_schema, fingerprint=fp,
                         context=context, request=request, details={"run_id": run["run_id"]})


def chat(flow: Flow, worker, job, run, *, stage: str, model: str, prompt: str, payload: str, request: dict, fp: str, schema,
         wire_schema: dict, packet, knowledge_base_version: str | None = None, repair: bool = True):
    """One brief or pack stage call; returns the validated result model. `schema` is the pydantic model of the result."""
    store = store_for(worker.storage)
    runs = LlmRuns.for_storage(worker.storage)
    context = {"prompt_version": flow.workflow, "knowledge_base_version": knowledge_base_version, "run_id": run["run_id"]}
    cache = f"{flow.cache}/{fp}.json"
    if store.exists(cache):
        data = store.read_json(cache)
        if data["fingerprint"] != fp or canonical_hash(data["output"]) != data["output_hash"]:
            raise ValueError(f"{flow.name.capitalize()} response cache integrity failed")
        result = schema.model_validate(data["output"])
        old = store.read_json(data["artifact"])
        flow.record(worker, job, run, stage, fp, old.get("raw_response"), reused=True)
        runs.record(stage=stage, model=model, fingerprint=fp, status="replayed", routing_policy="replay", cost_usd=0,
                    raw=old.get("raw_response"), prompt_version=context["prompt_version"],
                    knowledge_base_version=knowledge_base_version,
                    details={"run_id": run["run_id"], "artifact": data["artifact"]})
        with worker.repo.connection() as conn:
            worker.repo.event(conn, run["run_id"], f"{flow.name}_cache_reused", stage, job=job,
                              details={"fingerprint": fp, "artifact": data["artifact"]})
        return result
    base = f"{flow.attempts}/{job['job_id']}/{job['attempt_count']}/{fp}"
    store.write_json(base + "/request.json", request)
    recovered = _recover(store, flow, job, fp, request)
    output = metadata = None
    repaired = None
    try:
        if recovered:
            output, metadata = recovered["output"], recovered["metadata"]
        else:
            output, metadata = _dispatch(flow, worker, job, run, store, stage, model, fp, request, base, prompt, payload,
                                         wire_schema, context, runs)
            store.write_json(base + "/received.json", {"output": output, "metadata": metadata})
        result = schema.model_validate(output)
    except (ValidationError, InvalidJson, NoJsonContent) as first:
        if not repair:
            raise
        rejected = output if output is not None else getattr(first, "content", None)
        user = repair_user(payload, rejected, f"{type(first).__name__}: {first}")
        rfp = repair_fingerprint(fp, user)
        rbase = f"{base}/repair-1"
        repair_request = {**request, "messages": [request["messages"][0], {"role": "user", "content": user}]}
        store.write_json(rbase + "/request.json", repair_request)
        try:
            output, metadata = _dispatch(flow, worker, job, run, store, stage, model, rfp, repair_request, rbase, prompt, user,
                                         wire_schema, {**context, "repair_of": fp}, runs)
            store.write_json(rbase + "/received.json", {"output": output, "metadata": metadata})
            result = schema.model_validate(output)
        except (ValueError, TypeError, KeyError) as second:
            second.add_note(f"One repair call was made after: {first}")
            raise
        repaired = {"of": fp, "fingerprint": rfp, "problem": f"{type(first).__name__}: {first}"[:500], "attempt": 1}
    flow.record(worker, job, run, stage, fp, metadata.get("raw"), dispatched=not bool(recovered), reused=bool(recovered))
    artifact = StageArtifact(artifact_id=f"{flow.artifact_prefix}{fp[:24]}", run_id=run["run_id"], stage=stage,
                             request_fingerprint=fp, prompt_version=flow.workflow, model_id=model, status="validated",
                             input_hashes=[canonical_hash(packet)], request=request, output=output,
                             output_hash=canonical_hash(output), raw_response=metadata.get("raw"),
                             metadata={**metadata, **({"repair": repaired} if repaired else {})},
                             usage=response_usage(metadata.get("raw")))
    store.write_json(base + "/validated.json", artifact.model_dump(mode="json"))
    store.cache_artifact(artifact, base + "/validated.json")
    store.write_json(cache, {"fingerprint": fp, "output": output, "output_hash": canonical_hash(output),
                             "artifact": base + "/validated.json"})
    with worker.repo.connection() as conn:
        worker.repo.event(conn, run["run_id"], f"{flow.name}_response_validated", stage, job=job,
                          details={"fingerprint": fp, "artifact": base + "/validated.json", "usage": artifact.usage,
                                   "recovered": bool(recovered), **({"repaired": True} if repaired else {})})
    return result
