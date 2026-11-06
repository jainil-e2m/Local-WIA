"""A weekly-pipeline stage call, from request to validated artifact (plan 0.B4).

This is `Pipeline._call_json` and its bookkeeping moved into the llm module, with three additions the plan asks of
it: an `llm_runs` row for every call (replays and the offline provider included), the prompt and knowledge-base
versions on that row, and exactly one repair call when a response fails validation.

The on-disk layout is the one saved Week 1 artifacts were written in (`service_calls/<fingerprint>/attempts/...`,
`cache/artifacts/<fingerprint>.json`, `<run>/costs/...`), unchanged, so they replay with no provider call and
identical hashes. Briefs and packs use the other layout, in `llm/workflow.py`.
"""
from __future__ import annotations

import json
import logging
import math
import uuid
from collections.abc import Callable

from ..costs import call_record, response_usage, write_run_summary
from ..models import RunManifest, StageArtifact
from ..store import canonical_hash
from ..token_budget import preflight
from pydantic import ValidationError

from .call import UNATTENDED_STAGES, UNATTENDED_WAITS, patient_call, provider_call, provider_embed
from .providers import IncompleteResponse, InvalidJson, NoJsonContent
from .request import embedding_body, repair_fingerprint, repair_user, stage_body, stage_fingerprint
from .runs import FAKE_POLICY, LlmRuns

log = logging.getLogger(__name__)


# The start of the refusal a whole-week call too large for its model gets (the strategist job falls back on it, sql_pipeline).
OVERSIZED_WEEK = "Whole-week token budget exceeded"

def uid(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


class SchemaViolation(ValueError):
    """The response is not the object the stage's schema describes (missing keys, wrong array types)."""


def repairable(error: BaseException) -> bool:
    """A response that does not satisfy its schema can be asked for once more: unparseable JSON, no JSON content, a
    missing key or wrong type, a pydantic contract failure. Content failures (a quote that is not in the source, a card
    that cites an unknown scene) have their own repairs; a cut-off answer, a refusal by the plan or the routing and a
    failed request cannot be fixed by asking again."""
    return isinstance(error, (SchemaViolation, ValidationError, InvalidJson, NoJsonContent)) and not isinstance(error, IncompleteResponse)


class StageCaller:
    """The stage-call engine of a Pipeline. `owner` supplies settings, store and provider, which the SQL worker replaces
    after construction, so they are read when used."""

    def __init__(self, owner, runs: LlmRuns | None = None):
        self.owner = owner
        self.runs = runs
        # Whether to make the one repair call when a response fails validation (0.B4). Off only in tests of the failure.
        self.repair_invalid = True
        self.attempt_paths: dict[str, str] = {}
        self.cost_context: dict[str, tuple[RunManifest, str, str, str, str]] = {}
        self.dispatched: set[str] = set()

    @property
    def settings(self):
        return self.owner.settings

    @property
    def store(self):
        return self.owner.store

    # --- the recorded request -------------------------------------------------------------------------------------

    def request_key(self, *, run: RunManifest, stage: str, endpoint: str, request: dict, input_hash: str | None = None) -> str:
        return stage_fingerprint(mode=run.mode, stage=stage, endpoint=endpoint, request=request, input_hash=input_hash)

    def save_raw_response(self, fingerprint: str, raw: dict) -> None:
        relative = self.attempt_paths[fingerprint]
        self.store.write_json(f"{relative}/response.raw.json", raw)
        if fingerprint in self.cost_context:
            self.record_cost(fingerprint, raw=raw, validation_status="response_received")

    def record_cost(self, fingerprint: str, *, raw: dict | None = None, validation_status: str) -> None:
        run, run_dir, artifact_id, stage, model = self.cost_context[fingerprint]
        if raw is None:
            raw_key = f"{self.attempt_paths[fingerprint]}/response.raw.json"
            if self.store.exists(raw_key):
                raw = self.store.read_json(raw_key)
        record = call_record(
            raw=raw,
            dispatched=fingerprint in self.dispatched and run.mode != "fake",
            report_run_id=run.run_id,
            mode=run.mode,
            stage=stage,
            requested_model_id=model,
            request_fingerprint=fingerprint,
            artifact_id=artifact_id,
            validation_status=validation_status,
            request_path=f"{self.attempt_paths[fingerprint]}/request.json",
            raw_response_path=f"{self.attempt_paths[fingerprint]}/response.raw.json" if raw is not None else None,
        )
        self.store.write_json(f"{self.attempt_paths[fingerprint]}/cost.json", record, overwrite=True)
        self.store.write_json(f"{run_dir}/costs/{artifact_id}.json", record, overwrite=True)
        write_run_summary(self.store, run_dir)

    # --- the llm_runs record --------------------------------------------------------------------------------------

    def _context(self, stage: str, prompt_version: str | None, run: RunManifest, knowledge_base_version: str | None) -> dict:
        kb = knowledge_base_version or self.owner.kb_version_for(stage)
        return {"prompt_version": prompt_version or run.prompt_profile, "knowledge_base_version": kb, "run_id": run.run_id}

    def _record_unplanned(self, *, status, stage, model, fingerprint, run, raw=None, error=None, context=None, details=None,
                          offline=False) -> None:
        if self.runs is None:
            return
        context = context or {}
        self.runs.record(
            stage=stage, model=model, fingerprint=fingerprint, status=status, raw=raw, error=error,
            provider="fake" if offline else None, routing_policy=FAKE_POLICY if offline else "replay",
            prompt_version=context.get("prompt_version"), knowledge_base_version=context.get("knowledge_base_version"),
            cost_usd=0 if status == "replayed" else None,
            details={"run_id": run.run_id, "mode": run.mode, **(details or {})})

    def _provider_call(self, provider, *, stage, system, user, schema, fingerprint, run, model, context, request):
        """One call to the provider, recorded (llm.call.provider_call); the weekly scenes and cards wait out passing failures."""
        call = dict(stage=stage, model=model, system=system, user=user, schema=schema, fingerprint=fingerprint, context=context,
                    request=request, details={"mode": run.mode})
        if stage in UNATTENDED_STAGES and run.mode == "live":
            return patient_call(provider, self.runs, waits=UNATTENDED_WAITS, **call)
        return provider_call(provider, self.runs, **call)

    # --- validation -------------------------------------------------------------------------------------------------

    @staticmethod
    def check_envelope(output, schema: dict, stage: str) -> None:
        if not isinstance(output, dict) or any(key not in output for key in schema["required"]):
            raise SchemaViolation(f"Invalid {stage} response envelope")
        if any(not isinstance(output[key], list) for key in schema["required"]
               if schema["properties"][key].get("type") == "array"):
            raise SchemaViolation(f"Invalid {stage} response array")

    # --- the call -----------------------------------------------------------------------------------------------------

    def call_json(self, stage: str, run: RunManifest, run_dir: str, system: str, user: str, input_hash: str, schema: dict, *,
                  validate: Callable[[dict], object], prompt_version: str | None = None,
                  knowledge_base_version: str | None = None) -> StageArtifact:
        owner, settings = self.owner, self.settings
        model = settings.model_for(stage)
        request = stage_body(settings, stage, system, user, schema)
        fingerprint = self.request_key(run=run, stage=stage, endpoint=settings.openrouter_base_url.rstrip("/"), request=request,
                                       input_hash=input_hash)
        context = self._context(stage, prompt_version, run, knowledge_base_version)
        existing = self.store.find_artifact(fingerprint)
        if existing:
            artifact = StageArtifact.model_validate(existing)
            owner._validate_current_contract(artifact.output, schema)
            validate(artifact.output)
            self.reuse(artifact, run, run_dir)
            self._record_unplanned(status="replayed", stage=stage, model=model, fingerprint=fingerprint, run=run,
                                   raw=artifact.raw_response, context=context, details={"artifact_id": artifact.artifact_id})
            return artifact
        if stage == "moment_extraction":
            recovered = self.revalidate_saved(stage, run, run_dir, fingerprint, schema, validate,
                                              request=request, input_hash=input_hash, prompt_version=prompt_version, model=model)
            if recovered:
                self._record_unplanned(status="replayed", stage=stage, model=model, fingerprint=fingerprint, run=run,
                                       raw=recovered.raw_response, context=context,
                                       details={"artifact_id": recovered.artifact_id, "revalidated": True})
                return recovered
        if run.mode == "replay":
            raise RuntimeError(f"Replay cache miss for {stage}; no provider call was made")
        artifact_id = uid("artifact")
        attempt_dir = f"service_calls/{fingerprint}/attempts/{artifact_id}"
        self.attempt_paths[fingerprint] = attempt_dir
        self.cost_context[fingerprint] = (run, run_dir, artifact_id, stage, model)
        self.store.write_json(
            f"{attempt_dir}/request.json",
            {"endpoint": settings.openrouter_base_url, "stage": stage, "request_fingerprint": fingerprint, "request": request},
        )
        self.record_cost(fingerprint, validation_status="request_prepared")
        try:
            request_characters = len(json.dumps(request, ensure_ascii=False))
            if run.mode == "live" and not settings.llm_input_limits_enabled:
                # User-authorised uncapped test: diagnostics only, no local input
                # rejection, hidden output reserve, splitting or truncation.
                self.store.write_json(
                    f"{attempt_dir}/preflight.json",
                    {
                        "model": model,
                        "local_input_limits_enforced": False,
                        "capacity_validation": "disabled_by_explicit_test_configuration",
                        "request_characters": request_characters,
                        "message_text_utf8_bytes": sum(len(m["content"].encode("utf-8")) for m in request["messages"]),
                        "request_output_token_cap": request.get("max_tokens"),
                        "native_token_count_available": False,
                        "input_truncated": False,
                        "provider_limits_still_apply": True,
                    },
                )
            elif run.mode == "live" and settings.llm_payload_format == "compact_weekly":
                # The saved route is read from the store this call writes to: on the platform that is the bucket the
                # workers share, never a worker's own disk (0.B7).
                report = preflight(request, self.store)
                self.store.write_json(f"{attempt_dir}/preflight.json", report)
                if not report["fits"]:
                    raise RuntimeError(f"{OVERSIZED_WEEK}; no request sent. No batching or truncation permitted.")
            elif run.mode == "live" and (request_characters - len(json.dumps(system, ensure_ascii=False))
                                         > settings.max_llm_request_characters):
                # The trusted system prefix (prompt and knowledge base) does not count, as for briefs (E.B15 e): a
                # reviewed knowledge base growing never blocks a week; the week's material is what the limit guards.
                raise RuntimeError(
                    f"{stage} request has {request_characters - len(json.dumps(system, ensure_ascii=False))} characters "
                    "outside the system prompt and knowledge base, above the configured preflight limit "
                    f"of {settings.max_llm_request_characters}; no provider call was made. "
                    "Use the verified compact whole-week profile; no automatic batching or truncation is permitted. "
                    "This is a character safeguard, not a model-specific token count."
                )
            self.dispatched.add(fingerprint)
            self.record_cost(fingerprint, validation_status="awaiting_response")
            output, repair = None, None
            try:
                output, meta = self._provider_call(owner.provider, stage=stage, system=system, user=user, schema=schema,
                                                   fingerprint=fingerprint, run=run, model=model, context=context, request=request)
                if meta.get("raw") is not None:
                    self.save_raw_response(fingerprint, meta["raw"])
                self.store.write_json(f"{attempt_dir}/output.received.json", output)
                self._validated(owner, output, schema, stage, validate)
            except Exception as first:
                if not (self.repair_invalid and run.mode != "replay" and repairable(first)):
                    raise
                # An answer that is not JSON is shown to the repair as the text it was.
                rejected = output if output is not None else getattr(first, "content", None)
                output, meta, repair = self._repair(owner, stage, run, run_dir, system, user, schema, validate, request, model,
                                                    fingerprint, attempt_dir, rejected, first, context)
            artifact = StageArtifact(
                artifact_id=artifact_id,
                run_id=run.run_id,
                stage=stage,
                request_fingerprint=fingerprint,
                prompt_version=prompt_version or run.prompt_profile,
                model_id=model,
                request=request,
                status="validated",
                input_hashes=[input_hash],
                output=output,
                output_hash=canonical_hash(output),
                metadata={**{k: v for k, v in meta.items() if k != "raw"}, **({"repair": repair} if repair else {})},
                raw_response=meta.get("raw"),
                usage=response_usage(meta.get("raw")),
            )
        except Exception as exc:
            raw_key = f"{attempt_dir}/response.raw.json"
            raw = self.store.read_json(raw_key) if self.store.exists(raw_key) else None
            artifact = StageArtifact(
                artifact_id=artifact_id,
                run_id=run.run_id,
                stage=stage,
                request_fingerprint=fingerprint,
                prompt_version=prompt_version or run.prompt_profile,
                model_id=model,
                request=request,
                status="failed",
                input_hashes=[input_hash],
                error=str(exc),
                raw_response=raw if isinstance(raw, dict) else None,
                usage=response_usage(raw),
            )
            self.store.write_model(f"{attempt_dir}/artifact.json", artifact)
            self.store.write_model(f"{run_dir}/{stage}.failed.json", artifact)
            self.record_cost(fingerprint, raw=raw, validation_status="failed")
            raise
        self.store.write_model(f"{run_dir}/{stage}.json", artifact)
        self.store.cache_artifact(artifact, f"{attempt_dir}/artifact.json")
        # After a repair the first answer's own cost stays on the first attempt's record (read from its saved
        # response); the repair call has its own record, so the run's cost summary counts both.
        self.record_cost(fingerprint, raw=None if artifact.metadata.get("repair") else artifact.raw_response,
                         validation_status="repaired" if artifact.metadata.get("repair") else "validated")
        return artifact

    def _validated(self, owner, output, schema: dict, stage: str, validate: Callable[[dict], object]) -> None:
        self.check_envelope(output, schema, stage)
        owner._validate_current_contract(output, schema)
        validate(output)

    def _repair(self, owner, stage, run, run_dir, system, user, schema, validate, request, model, fingerprint, attempt_dir, output,
                first_error, context):
        """The one repair call (0.B4): the same request, plus the rejected answer and what failed. It is its own call: its
        own fingerprint, attempt folder, cost record and llm_runs row, and it counts against the run plan. If its
        answer fails too, the stage fails with that error; there is no second repair."""
        problem = f"{type(first_error).__name__}: {first_error}"
        repaired_user = repair_user(user, output, problem)
        rfp = repair_fingerprint(fingerprint, repaired_user)
        repair_id = uid("artifact")
        repair_dir = f"{attempt_dir}/repair-1"
        repair_request = stage_body(self.settings, stage, system, repaired_user, schema)
        self.attempt_paths[rfp] = repair_dir
        self.cost_context[rfp] = (run, run_dir, repair_id, stage, model)
        self.store.write_json(f"{repair_dir}/request.json", {"endpoint": self.settings.openrouter_base_url, "stage": stage,
                                                              "request_fingerprint": rfp, "repair_of": fingerprint,
                                                              "problem": problem, "request": repair_request})
        self.record_cost(rfp, validation_status="request_prepared")
        self.dispatched.add(rfp)
        self.record_cost(rfp, validation_status="awaiting_response")
        try:
            repaired, meta = self._provider_call(owner.provider, stage=stage, system=system, user=repaired_user, schema=schema,
                                                 fingerprint=rfp, run=run, model=model,
                                                 context={**context, "repair_of": fingerprint}, request=repair_request)
        except (ValueError, TypeError, KeyError) as second:
            self.record_cost(rfp, validation_status="failed")
            second.add_note(f"One repair call was made after: {first_error}")
            raise
        if meta.get("raw") is not None:
            self.save_raw_response(rfp, meta["raw"])
        self.store.write_json(f"{repair_dir}/output.received.json", repaired)
        try:
            self._validated(owner, repaired, schema, stage, validate)
        except Exception as second:
            self.record_cost(rfp, validation_status="failed")
            second.add_note(f"The one repair call's answer failed too; the first answer failed with: {first_error}")
            raise
        self.record_cost(rfp, raw=meta.get("raw"), validation_status="validated")
        return repaired, meta, {"of": fingerprint, "fingerprint": rfp, "problem": problem[:500], "attempt": 1}

    # --- saved responses -----------------------------------------------------------------------------------------------

    def reuse(self, artifact: StageArtifact, run: RunManifest, run_dir: str) -> None:
        # The pointer keeps the original artifact/time; replay is a report event.
        self.store.write_json(
            f"{run_dir}/reuse/{artifact.artifact_id}.json",
            {
                "report_run_id": run.run_id,
                "original_run_id": artifact.run_id,
                "artifact_id": artifact.artifact_id,
                "stage": artifact.stage,
                "request_fingerprint": artifact.request_fingerprint,
                "generated_at_original": artifact.created_at.isoformat(),
                "new_inference_cost": 0,
            },
        )
        if artifact.stage != "embedding":
            self.store.write_model(f"{run_dir}/{artifact.stage}.json", artifact)
            self.store.write_json(
                f"{run_dir}/costs/{artifact.artifact_id}.json",
                call_record(
                    raw=artifact.raw_response,
                    reused=True,
                    report_run_id=run.run_id,
                    mode=run.mode,
                    stage=artifact.stage,
                    requested_model_id=artifact.model_id,
                    request_fingerprint=artifact.request_fingerprint,
                    artifact_id=artifact.artifact_id,
                    original_run_id=artifact.run_id,
                    validation_status="reused_validated",
                ),
            )
            write_run_summary(self.store, run_dir)

    def revalidate_saved(self, stage, run, run_dir, fingerprint, schema, validate, *, request, input_hash,
                         prompt_version, model) -> StageArtifact | None:
        """Re-check a response already received for this exact request under the current validator (E.B12a).

        A response that failed an earlier, stricter check is promoted without a provider call; the original
        attempt keeps its failed record and cost. Nothing is promoted that the current validator rejects.
        """
        for store, attempt in self.store.saved_attempts(fingerprint):
            try:
                output = store.read_json(f"{attempt}/output.received.json")
                if not isinstance(output, dict) or any(key not in output for key in schema["required"]):
                    continue
                self.owner._validate_current_contract(output, schema)
                validate(output)
            except (OSError, ValueError, TypeError, KeyError):
                continue
            original, raw = {}, None
            if store.exists(f"{attempt}/artifact.json"):
                original = store.read_json(f"{attempt}/artifact.json")
            if store.exists(f"{attempt}/response.raw.json"):
                raw = store.read_json(f"{attempt}/response.raw.json")
            artifact = StageArtifact(
                artifact_id=uid("artifact"),
                run_id=original.get("run_id") or run.run_id,
                stage=stage,
                request_fingerprint=fingerprint,
                prompt_version=prompt_version or run.prompt_profile,
                model_id=model,
                request=request,
                status="validated",
                input_hashes=[input_hash],
                output=output,
                output_hash=canonical_hash(output),
                metadata={"revalidated_from_attempt": attempt, "revalidated_from_store": str(store.root),
                          "original_error": original.get("error")},
                raw_response=raw if isinstance(raw, dict) else None,
                usage=response_usage(raw),
                **({"created_at": original["created_at"]} if original.get("created_at") else {}),
            )
            self.store.cache_artifact(artifact, f"service_calls/{fingerprint}/attempts/{artifact.artifact_id}/artifact.json")
            self.reuse(artifact, run, run_dir)
            return artifact
        return None

    # --- embeddings ----------------------------------------------------------------------------------------------------

    @staticmethod
    def validate_vector(output: dict, dimensions: int) -> None:
        vector = output.get("vector")
        if not isinstance(vector, list) or len(vector) != dimensions:
            raise ValueError("Embedding dimension mismatch")
        if any(not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value) for value in vector):
            raise ValueError("Embedding contains invalid values")
        if not any(vector):
            raise ValueError("Embedding must be nonzero")

    def embedding(self, angle, run: RunManifest, run_dir: str) -> StageArtifact:
        """The vector of an angle's signature, with the same cache, saved receipts, cost record and llm_runs row."""
        settings = self.settings
        if not settings.embeddings_enabled:
            raise RuntimeError("Embeddings are disconnected pending explicit user approval")
        request = embedding_body(model=settings.embedding_model, text=angle.signature, dimensions=settings.embedding_dimensions)
        fingerprint = self.request_key(run=run, stage="embedding", endpoint=settings.embedding_base_url.rstrip("/"), request=request)
        existing = self.store.find_artifact(fingerprint)
        if existing:
            artifact = StageArtifact.model_validate(existing)
            self.validate_vector(artifact.output, settings.embedding_dimensions)
            self.reuse(artifact, run, run_dir)
            self._record_unplanned(status="replayed", stage="embedding", model=settings.embedding_model, fingerprint=fingerprint,
                                   run=run, raw=artifact.raw_response, details={"artifact_id": artifact.artifact_id})
        else:
            if run.mode == "replay":
                raise RuntimeError("Replay cache miss for embedding; no provider call was made")
            artifact_id = uid("artifact")
            attempt_dir = f"service_calls/{fingerprint}/attempts/{artifact_id}"
            self.attempt_paths[fingerprint] = attempt_dir
            self.store.write_json(
                f"{attempt_dir}/request.json",
                {"endpoint": settings.embedding_base_url, "request": request, "request_fingerprint": fingerprint},
            )
            try:
                vector, meta = provider_embed(self.owner.provider, self.runs, model=settings.embedding_model, text=angle.signature,
                                              fingerprint=fingerprint, context={"run_id": run.run_id})
                if meta.get("raw") is not None:
                    self.save_raw_response(fingerprint, meta["raw"])
                output = {"vector": vector}
                self.store.write_json(f"{attempt_dir}/output.received.json", output)
                self.validate_vector(output, settings.embedding_dimensions)
                artifact = StageArtifact(
                    artifact_id=artifact_id,
                    run_id=run.run_id,
                    stage="embedding",
                    request_fingerprint=fingerprint,
                    model_id=settings.embedding_model,
                    status="validated",
                    input_hashes=[canonical_hash(angle.signature)],
                    request=request,
                    output=output,
                    output_hash=canonical_hash(output),
                    raw_response=meta.get("raw"),
                    usage=(meta.get("raw") or {}).get("usage"),
                    metadata={k: v for k, v in meta.items() if k != "raw"},
                )
            except Exception as exc:
                artifact = StageArtifact(
                    artifact_id=artifact_id,
                    run_id=run.run_id,
                    stage="embedding",
                    request_fingerprint=fingerprint,
                    model_id=settings.embedding_model,
                    status="failed",
                    input_hashes=[canonical_hash(angle.signature)],
                    request=request,
                    error=str(exc),
                )
                self.store.write_model(f"{attempt_dir}/artifact.json", artifact)
                raise
            self.store.cache_artifact(artifact, f"{attempt_dir}/artifact.json")
        self.store.write_json(
            f"{run_dir}/embeddings/{angle.angle_id}.json",
            {
                "angle_id": angle.angle_id,
                "fingerprint": fingerprint,
                "artifact_id": artifact.artifact_id,
                "vector": artifact.output["vector"],
                "model": artifact.model_id,
                "dimensions": settings.embedding_dimensions,
                "new_call": existing is None,
            },
        )
        return artifact
