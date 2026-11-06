from __future__ import annotations

import json
import math
import uuid
from collections.abc import Callable

from .config import Settings
from .contracts import AngleResponse, MomentResponse, signature_from_fields
from .costs import call_record, response_usage, write_run_summary
from .ingest import discover_week
from .models import Angle, Moment, Quality, RunManifest, StageArtifact
from .prompts import PROMPT_VERSION, angle_prompt, moment_prompt, weekly_moment_prompt
from .provider import FakeProvider, LiveProvider, ModelProvider, chat_body, embedding_body
from .scoring import rank
from .store import JsonStore, canonical_hash
from .token_budget import preflight
from .weekly import LIVE_COMPACT_VERSION, load_compact_week, meeting_inventory, resolve_moment_references
from .strategy_contracts import (
    StrategicAngleResponse, StrategicCompactMomentResponse, StrategicMomentResponse,
    StrategicRefinementResponse, is_strategic_angle_response, is_strategic_moment_response,
)


def uid(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


class Pipeline:
    def __init__(self, settings: Settings, provider: ModelProvider | None = None):
        self.settings = settings
        self.store = JsonStore(settings.data_root)
        self._provider_override = provider
        self.provider: ModelProvider = provider or FakeProvider(dimensions=settings.embedding_dimensions)
        self._attempt_paths: dict[str, str] = {}
        self._cost_context: dict[str, tuple[RunManifest, str, str, str, str]] = {}
        self._dispatched: set[str] = set()
        self._compact_refs: dict[str, str] = {}
        self._packet_prefix: str | None = None

    def _select_provider(self, mode: str) -> None:
        if mode == "live":
            if not self.settings.live_enabled:
                raise RuntimeError("Live mode requires CONTENT_ATELIER_LIVE=true")
            self.settings.validate_live()
        if self._provider_override is not None:
            self.provider = self._provider_override
        elif mode != "live":
            self.provider = FakeProvider(dimensions=self.settings.embedding_dimensions)
        else:
            settings = self.settings
            self.provider = LiveProvider(
                llm_base_url=settings.openrouter_base_url,
                moments_model=settings.openrouter_moments_model,
                moments_key=settings.openrouter_moments_key,
                angles_model=settings.openrouter_angles_model,
                angles_key=settings.openrouter_angles_key,
                embedding_base_url=settings.embedding_base_url,
                embedding_model=settings.embedding_model,
                embedding_key=settings.embedding_api_key,
                dimensions=settings.embedding_dimensions,
                timeout=settings.request_timeout_seconds,
                on_response=self._save_raw_response,
                max_tokens=settings.llm_completion_tokens,
                reasoning_effort=settings.llm_reasoning_effort,
                response_format=settings.llm_response_format,
            )

    def _save_raw_response(self, fingerprint: str, raw: dict) -> None:
        relative = self._attempt_paths[fingerprint]
        self.store.write_json(f"{relative}/response.raw.json", raw)
        if fingerprint in self._cost_context:
            self._record_cost(fingerprint, raw=raw, validation_status="response_received")

    def _record_cost(self, fingerprint: str, *, raw: dict | None = None, validation_status: str) -> None:
        run, run_dir, artifact_id, stage, model = self._cost_context[fingerprint]
        if raw is None:
            raw_path = self.store.path(f"{self._attempt_paths[fingerprint]}/response.raw.json")
            if raw_path.exists():
                raw = self.store.read_json(str(raw_path.relative_to(self.store.root)))
        record = call_record(
            raw=raw,
            dispatched=fingerprint in self._dispatched and run.mode != "fake",
            report_run_id=run.run_id,
            mode=run.mode,
            stage=stage,
            requested_model_id=model,
            request_fingerprint=fingerprint,
            artifact_id=artifact_id,
            validation_status=validation_status,
            request_path=f"{self._attempt_paths[fingerprint]}/request.json",
            raw_response_path=f"{self._attempt_paths[fingerprint]}/response.raw.json" if raw is not None else None,
        )
        self.store.write_json(f"{self._attempt_paths[fingerprint]}/cost.json", record, overwrite=True)
        self.store.write_json(f"{run_dir}/costs/{artifact_id}.json", record, overwrite=True)
        write_run_summary(self.store, run_dir)

    def load_week(self, week_index: int):
        self._compact_refs, self._packet_prefix = {}, None
        if self.settings.llm_payload_format == "compact_weekly":
            transcripts, source_packet, self._compact_refs, self._packet_prefix = load_compact_week(
                self.settings.transcript_root, week_index, self.store
            )
        else:
            transcripts = discover_week(self.settings.transcript_root, week_index)
            source_packet = [span.model_dump(mode="json") for transcript in transcripts for span in transcript.spans]
        for transcript in transcripts:
            # Same raw bytes may previously have been stored with the legacy
            # representation. Keep the lossless source view in its own namespace.
            source_area = "sources/compact_weekly" if self._compact_refs else "sources"
            self.store.write_json(
                f"{source_area}/week{week_index}/{transcript.source_id.replace(':', '_')}/{transcript.content_hash}.json",
                transcript.model_dump(mode="json"),
            )
        snapshot = {"transcripts": [t.model_dump(mode="json") for t in transcripts]}
        snapshot_hash = canonical_hash(snapshot)
        self.store.write_json(f"cycles/week{week_index}/snapshots/{snapshot_hash}.json", snapshot)
        self.store.write_json(f"cycles/week{week_index}/sources.json", snapshot, overwrite=True)
        return transcripts, source_packet

    def plan(self, week_index: int, mode: str = "plan") -> RunManifest:
        transcripts, _ = self.load_week(week_index)
        run = RunManifest(
            run_id=uid("run"),
            week_index=week_index,
            source_root=str(self.settings.transcript_root),
            source_ids=[t.source_id for t in transcripts],
            prompt_profile=LIVE_COMPACT_VERSION if self._compact_refs else PROMPT_VERSION,
            model_id=self.settings.openrouter_angles_model,
            embedding_profile=f"{self.settings.embedding_model}:{self.settings.embedding_dimensions}",
            mode=mode,
            execution_scope="full" if self.settings.embeddings_enabled else "generation_only",
        )
        self.store.write_model(f"experiments/default/runs/{run.run_id}/manifest.json", run)
        return run

    def run(self, week_index: int, *, mode: str = "fake", run_id: str | None = None) -> dict:
        if mode == "plan":
            return self.plan(week_index).model_dump(mode="json")
        if mode not in {"fake", "live", "replay"}:
            raise ValueError("mode must be plan, fake, live or replay")
        self._select_provider(mode)
        transcripts, source_packet = self.load_week(week_index)
        run = RunManifest(
            run_id=run_id or uid("run"),
            week_index=week_index,
            source_root=str(self.settings.transcript_root),
            source_ids=[t.source_id for t in transcripts],
            prompt_profile=LIVE_COMPACT_VERSION if self._compact_refs else PROMPT_VERSION,
            model_id=self.settings.openrouter_angles_model,
            embedding_profile=f"{self.settings.embedding_model}:{self.settings.embedding_dimensions}",
            mode=mode,
            execution_scope="full" if self.settings.embeddings_enabled else "generation_only",
        )
        run_dir = f"experiments/default/runs/{run.run_id}"
        if self.store.path(f"{run_dir}/manifest.json").exists():
            raise ValueError("Run ID already exists; use a new report run to preserve original artifacts")
        self.store.write_model(f"{run_dir}/manifest.json", run)
        try:
            result = self._execute(run, run_dir, transcripts, source_packet)
        except Exception:
            run.status = "failed"
            self.store.write_model(f"{run_dir}/manifest.json", run, overwrite=True)
            raise
        run.status = "completed" if self.settings.embeddings_enabled else "generation_completed"
        self.store.write_model(f"{run_dir}/manifest.json", run, overwrite=True)
        return result

    def _execute(self, run: RunManifest, run_dir: str, transcripts, source_packet: list[dict] | str) -> dict:
        if isinstance(source_packet, str):
            system, user = weekly_moment_prompt(source_packet, meeting_inventory(self._compact_refs))
            self.store.write_json(f"{run_dir}/weekly_packet.json", {"artifact_directory": self._packet_prefix})
        else:
            system, user = moment_prompt(source_packet)
        source_identity = [{"source_id": t.source_id, "revision": t.content_hash} for t in transcripts]
        moment_input_hash = canonical_hash({"system": system, "user": user, "source": source_identity})

        def resolve(output):
            return resolve_moment_references(output, self._compact_refs) if self._compact_refs else output

        moment_artifact = self._call_json(
            "moment_extraction",
            run,
            run_dir,
            system,
            user,
            moment_input_hash,
            StrategicCompactMomentResponse.model_json_schema() if self._compact_refs else StrategicMomentResponse.model_json_schema(),
            validate=lambda output: self._parse_moments(resolve(output), run.run_id, transcripts),
        )
        moments = self._parse_moments(resolve(moment_artifact.output), run.run_id, transcripts)
        self.store.write_json(f"{run_dir}/moments.json", [m.model_dump(mode="json") for m in moments])
        # Stage 2 can inspect actual surrounding turns, not only a model summary.
        angle_system, angle_user = angle_prompt(self._moment_packet(moments, transcripts), [])
        angle_input_hash = canonical_hash(
            {"system": angle_system, "user": angle_user, "moment_ids": [m.moment_id for m in moments]}
        )
        angle_artifact = self._call_json(
            "angle_generation",
            run,
            run_dir,
            angle_system,
            angle_user,
            angle_input_hash,
            StrategicAngleResponse.model_json_schema(),
            validate=lambda output: self._parse_angles(output, run.run_id, moments),
        )
        angles = self._parse_angles(angle_artifact.output, run.run_id, moments, artifact=angle_artifact)
        self.store.write_json(f"{run_dir}/candidates.json", [a.model_dump(mode="json") for a in angles])
        self._write_discovery_outputs(run_dir, angle_artifact.output, angles)
        if not self.settings.embeddings_enabled:
            self.store.write_json(
                f"{run_dir}/review.json",
                {
                    "run_id": run.run_id,
                    "status": "generation_completed",
                    "execution_scope": "generation_only",
                    "candidate_angle_ids": [a.angle_id for a in angles],
                    "visible_angle_ids": [],
                    "angle_count": len(angles),
                    "embeddings_enabled": False,
                    "embedding_requests": 0,
                    "similarity_status": "not_run",
                    "recency_adjustment_status": "not_run",
                    "quality_scores_status": "model_self_scores_not_human_calibrated",
                    "internal_insight_count": len(angle_artifact.output.get("internal_insights", [])),
                    "research_required_angle_ids": [a.angle_id for a in angles if a.strategy and a.strategy.evidence_readiness == "research_required"],
                    "coverage": "meeting_bounds_acknowledged" if self._compact_refs else "span_ids_acknowledged",
                    "source_span_count": sum(len(t.spans) for t in transcripts),
                    "processed_span_count": None if self._compact_refs else len(moment_artifact.output["processed_span_ids"]),
                    "delivered_span_count": sum(len(t.spans) for t in transcripts),
                    "processed_meeting_count": len(moment_artifact.output["processed_meetings"]) if self._compact_refs else None,
                    "coverage_is_proof_of_comprehension": False,
                    "processed_moment_count": len(angle_artifact.output["processed_moment_ids"]),
                },
            )
            return {
                "run_id": run.run_id,
                "week_index": run.week_index,
                "moments": len(moments),
                "angles": len(angles),
                "visible": 0,
                "mode": run.mode,
                "execution_scope": "generation_only",
                "embedding_requests": 0,
                "similarity_status": "not_run",
            }
        for angle in angles:
            artifact = self._embedding(angle, run, run_dir)
            angle.embedding = artifact.output["vector"]
        history = self._load_history(run)
        ranked = rank(
            angles,
            history,
            threshold=self.settings.similarity_threshold,
            visible_threshold=self.settings.visible_threshold,
            half_life=self.settings.recency_half_life_days,
            max_penalty=self.settings.max_recency_penalty,
        )
        self.store.write_json(f"{run_dir}/angles.json", [a.model_dump(mode="json") for a in ranked])
        self.store.write_json(
            f"{run_dir}/review.json",
            {
                "run_id": run.run_id,
                "visible_angle_ids": [a.angle_id for a in ranked if a.status == "visible"],
                "angle_count": len(ranked),
                "coverage": "acknowledged",
                "source_span_count": sum(len(t.spans) for t in transcripts),
                "processed_span_count": None if self._compact_refs else len(moment_artifact.output["processed_span_ids"]),
                "delivered_span_count": sum(len(t.spans) for t in transcripts),
                "processed_moment_count": len(angle_artifact.output["processed_moment_ids"]),
            },
        )
        return {
            "run_id": run.run_id,
            "week_index": run.week_index,
            "moments": len(moments),
            "angles": len(ranked),
            "visible": sum(a.status == "visible" for a in ranked),
            "mode": run.mode,
        }

    def _request_key(self, *, run: RunManifest, stage: str, endpoint: str, request: dict, input_hash: str | None = None) -> str:
        return canonical_hash(
            {
                "cache_version": 2,
                "validation_version": 2 if stage == "embedding" else 4,
                "namespace": "fake" if run.mode == "fake" else "live",
                "stage": stage,
                "endpoint": endpoint,
                "request": request,
                "input_hash": input_hash,
            }
        )

    def _reuse(self, artifact: StageArtifact, run: RunManifest, run_dir: str) -> None:
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

    def _call_json(
        self,
        stage: str,
        run: RunManifest,
        run_dir: str,
        system: str,
        user: str,
        input_hash: str,
        schema: dict,
        *,
        validate: Callable[[dict], object],
    ) -> StageArtifact:
        model = self.settings.openrouter_moments_model if stage == "moment_extraction" else self.settings.openrouter_angles_model
        request = chat_body(
            model=model,
            system=system,
            user=user,
            schema=schema,
            max_tokens=self.settings.llm_completion_tokens,
            reasoning_effort=self.settings.llm_reasoning_effort,
            response_format=self.settings.llm_response_format,
        )
        fingerprint = self._request_key(
            run=run, stage=stage, endpoint=self.settings.openrouter_base_url.rstrip("/"), request=request, input_hash=input_hash
        )
        existing = self.store.find_artifact(fingerprint)
        if existing:
            artifact = StageArtifact.model_validate(existing)
            self._validate_current_contract(artifact.output, schema)
            validate(artifact.output)
            self._reuse(artifact, run, run_dir)
            return artifact
        if run.mode == "replay":
            raise RuntimeError(f"Replay cache miss for {stage}; no provider call was made")
        artifact_id = uid("artifact")
        attempt_dir = f"service_calls/{fingerprint}/attempts/{artifact_id}"
        self._attempt_paths[fingerprint] = attempt_dir
        self._cost_context[fingerprint] = (run, run_dir, artifact_id, stage, model)
        self.store.write_json(
            f"{attempt_dir}/request.json",
            {
                "endpoint": self.settings.openrouter_base_url,
                "stage": stage,
                "request_fingerprint": fingerprint,
                "request": request,
            },
        )
        self._record_cost(fingerprint, validation_status="request_prepared")
        try:
            request_characters = len(json.dumps(request, ensure_ascii=False))
            if run.mode == "live" and not self.settings.llm_input_limits_enabled:
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
            elif run.mode == "live" and self.settings.llm_payload_format == "compact_weekly":
                report = preflight(request, self.settings.data_root)
                self.store.write_json(f"{attempt_dir}/preflight.json", report)
                if not report["fits"]:
                    raise RuntimeError("Whole-week token budget exceeded; no request sent. No batching or truncation permitted.")
            elif run.mode == "live" and request_characters > self.settings.max_llm_request_characters:
                raise RuntimeError(
                    f"{stage} request has {request_characters} characters, above the configured preflight limit "
                    f"of {self.settings.max_llm_request_characters}; no provider call was made. "
                    "Use the verified compact whole-week profile; no automatic batching or truncation is permitted. "
                    "This is a character safeguard, not a model-specific token count."
                )
            self._dispatched.add(fingerprint)
            self._record_cost(fingerprint, validation_status="awaiting_response")
            output, meta = self.provider.json_call(stage=stage, system=system, user=user, schema=schema, fingerprint=fingerprint)
            if meta.get("raw") is not None:
                self._save_raw_response(fingerprint, meta["raw"])
            self.store.write_json(f"{attempt_dir}/output.received.json", output)
            if not isinstance(output, dict) or any(key not in output for key in schema["required"]):
                raise ValueError(f"Invalid {stage} response envelope")
            if any(not isinstance(output[key], list) for key in schema["required"]):
                raise ValueError(f"Invalid {stage} response array")
            self._validate_current_contract(output, schema)
            validate(output)
            artifact = StageArtifact(
                artifact_id=artifact_id,
                run_id=run.run_id,
                stage=stage,
                request_fingerprint=fingerprint,
                prompt_version=run.prompt_profile,
                model_id=model,
                request=request,
                status="validated",
                input_hashes=[input_hash],
                output=output,
                output_hash=canonical_hash(output),
                metadata={k: v for k, v in meta.items() if k != "raw"},
                raw_response=meta.get("raw"),
                usage=response_usage(meta.get("raw")),
            )
        except Exception as exc:
            raw_path = self.store.path(f"{attempt_dir}/response.raw.json")
            raw = self.store.read_json(str(raw_path.relative_to(self.store.root))) if raw_path.exists() else None
            artifact = StageArtifact(
                artifact_id=artifact_id,
                run_id=run.run_id,
                stage=stage,
                request_fingerprint=fingerprint,
                prompt_version=run.prompt_profile,
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
            self._record_cost(fingerprint, raw=raw, validation_status="failed")
            raise
        self.store.write_model(f"{run_dir}/{stage}.json", artifact)
        self.store.cache_artifact(artifact, f"{attempt_dir}/artifact.json")
        self._record_cost(fingerprint, raw=artifact.raw_response, validation_status="validated")
        return artifact

    def _validate_vector(self, output: dict) -> None:
        vector = output.get("vector")
        if not isinstance(vector, list) or len(vector) != self.settings.embedding_dimensions:
            raise ValueError("Embedding dimension mismatch")
        if any(not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value) for value in vector):
            raise ValueError("Embedding contains invalid values")
        if not any(vector):
            raise ValueError("Embedding must be nonzero")

    def _embedding(self, angle: Angle, run: RunManifest, run_dir: str) -> StageArtifact:
        if not self.settings.embeddings_enabled:
            raise RuntimeError("Embeddings are disconnected pending explicit user approval")
        request = embedding_body(
            model=self.settings.embedding_model, text=angle.signature, dimensions=self.settings.embedding_dimensions
        )
        fingerprint = self._request_key(
            run=run, stage="embedding", endpoint=self.settings.embedding_base_url.rstrip("/"), request=request
        )
        existing = self.store.find_artifact(fingerprint)
        if existing:
            artifact = StageArtifact.model_validate(existing)
            self._validate_vector(artifact.output)
            self._reuse(artifact, run, run_dir)
        else:
            if run.mode == "replay":
                raise RuntimeError("Replay cache miss for embedding; no provider call was made")
            artifact_id = uid("artifact")
            attempt_dir = f"service_calls/{fingerprint}/attempts/{artifact_id}"
            self._attempt_paths[fingerprint] = attempt_dir
            self.store.write_json(
                f"{attempt_dir}/request.json",
                {"endpoint": self.settings.embedding_base_url, "request": request, "request_fingerprint": fingerprint},
            )
            try:
                vector, meta = self.provider.embed(text=angle.signature, fingerprint=fingerprint)
                if meta.get("raw") is not None:
                    self._save_raw_response(fingerprint, meta["raw"])
                output = {"vector": vector}
                self.store.write_json(f"{attempt_dir}/output.received.json", output)
                self._validate_vector(output)
                artifact = StageArtifact(
                    artifact_id=artifact_id,
                    run_id=run.run_id,
                    stage="embedding",
                    request_fingerprint=fingerprint,
                    model_id=self.settings.embedding_model,
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
                    model_id=self.settings.embedding_model,
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
                "dimensions": self.settings.embedding_dimensions,
                "new_call": existing is None,
            },
        )
        return artifact

    @staticmethod
    def _coverage(expected: set[str], received: list[str], label: str) -> None:
        if len(received) != len(set(received)) or set(received) != expected:
            raise ValueError(f"{label} coverage must acknowledge every supplied ID exactly once")

    @staticmethod
    def _local_keys(records) -> None:
        keys = [record.local_key for record in records]
        if len(keys) != len(set(keys)):
            raise ValueError("Response local keys must be unique")

    @staticmethod
    def _moment_packet(moments: list[Moment], transcripts) -> list[dict]:
        spans = {span.span_id: span for transcript in transcripts for span in transcript.spans}
        revisions = {transcript.source_id: transcript.content_hash for transcript in transcripts}
        return [
            {
                **moment.model_dump(mode="json"),
                "source_evidence": [spans[span_id].model_dump(mode="json") for span_id in moment.context_span_ids],
                "source_revision_hashes": {source_id: revisions[source_id] for source_id in moment.source_ids},
                **(
                    {"source_metadata": {t.source_id: t.source_metadata for t in transcripts if t.source_id in moment.source_ids}}
                    if any(t.source_metadata for t in transcripts)
                    else {}
                ),
                "speaker_identity_status": "unverified_labels",
            }
            for moment in moments
        ]

    @staticmethod
    def _validate_current_contract(output: dict, schema: dict) -> None:
        contracts = (StrategicMomentResponse, StrategicCompactMomentResponse, StrategicAngleResponse, StrategicRefinementResponse)
        for contract in contracts:
            if schema.get("title") == contract.__name__:
                contract.model_validate(output)
                return

    def _write_discovery_outputs(self, run_dir: str, output: dict, angles: list[Angle]) -> None:
        if is_strategic_angle_response(output):
            self.store.write_json(f"{run_dir}/internal_insights.json", output["internal_insights"])
            self.store.write_json(f"{run_dir}/opportunities.json", [
                {"angle_id": a.angle_id, "source_family_id": a.source_family_id, **a.strategy.model_dump(mode="json")}
                for a in angles if a.strategy
            ])

    def _parse_moments(self, output: dict, run_id: str, transcripts) -> list[Moment]:
        contract = StrategicMomentResponse if is_strategic_moment_response(output) else MomentResponse
        response = contract.model_validate(output)
        spans = {s.span_id: s for t in transcripts for s in t.spans}
        self._coverage(set(spans), response.processed_span_ids, "Span")
        self._local_keys(response.moments)
        if not response.moments and not response.coverage_notes:
            raise ValueError("An empty moment result requires an explanation")
        result = []
        for draft in response.moments:
            raw = draft.model_dump(mode="json")
            anchors, context = draft.anchor_span_ids, draft.context_span_ids
            if any(x not in spans for x in anchors + context):
                raise ValueError("Moment references an unknown source span")
            if len(set(anchors)) != len(anchors) or len(set(context)) != len(context):
                raise ValueError("Moment source references must be unique")
            if not set(anchors).issubset(context):
                raise ValueError("Context must contain every anchor")
            if len({spans[x].source_id for x in anchors + context}) != 1:
                raise ValueError("A moment cannot combine different source conversations")
            ordinals = [spans[x].ordinal for x in context]
            if ordinals != list(range(min(ordinals), max(ordinals) + 1)):
                raise ValueError("Moment context must be contiguous and chronological")
            if [spans[x].ordinal for x in anchors] != sorted(spans[x].ordinal for x in anchors):
                raise ValueError("Moment anchors must be chronological")
            quote = draft.quote
            if not any(quote in spans[x].text for x in anchors):
                raise ValueError("Moment quote must match an existing anchor span")
            identity = canonical_hash({"source_revisions": {t.source_id: t.content_hash for t in transcripts}, "moment": raw})
            result.append(
                Moment(
                    moment_id=f"moment_{identity[:24]}",
                    source_ids=sorted({spans[x].source_id for x in anchors}),
                    anchor_span_ids=anchors,
                    context_span_ids=context,
                    quote=quote,
                    context_summary=draft.context_summary,
                    moment_type=draft.moment_type,
                    proposition=draft.proposition,
                    audience_relevance=draft.audience_relevance,
                    qualifications=draft.qualifications,
                    claim_status=draft.claim_status,
                    sensitivity=draft.sensitivity,
                    strength=draft.strength,
                    reasons=draft.reasons,
                    discovery=getattr(draft, "discovery", None),
                )
            )
        return result

    def _parse_angles(
        self, output: dict, run_id: str, moments: list[Moment], *, artifact: StageArtifact | None = None
    ) -> list[Angle]:
        strategic = is_strategic_angle_response(output)
        response = (StrategicAngleResponse if strategic else AngleResponse).model_validate(output)
        moment_map = {m.moment_id: m for m in moments}
        moment_ids = set(moment_map)
        self._coverage(moment_ids, response.processed_moment_ids, "Moment")
        self._local_keys(response.angles)
        internal = getattr(response, "internal_insights", [])
        for insight in internal:
            if len(insight.moment_ids) != len(set(insight.moment_ids)) or any(mid not in moment_ids for mid in insight.moment_ids):
                raise ValueError("Internal insight references unknown or duplicate moments")
        if not response.angles and not response.coverage_notes and not internal:
            raise ValueError("An empty angle result requires an explanation")
        signatures = set()
        result = []
        for draft in response.angles:
            raw = draft.model_dump(mode="json")
            refs = draft.moment_ids
            if any(x not in moment_ids for x in refs):
                raise ValueError("Angle references an unknown moment")
            if len(refs) != len(set(refs)):
                raise ValueError("Angle moment references must be unique")
            if any(not any(claim.startswith(f"[{ref}] ") for ref in refs) for claim in draft.source_assertions):
                raise ValueError("Every source assertion must start with a referenced [moment_id]")
            signature = signature_from_fields(raw)
            if signature.casefold() in signatures:
                raise ValueError("Duplicate canonical angle arguments in the same response")
            signatures.add(signature.casefold())
            if strategic:
                q = draft.quality
                quality = Quality(grounding=q.grounding, source_relevance=q.source_strength,
                    audience_fit=q.audience_resonance, specificity=q.distinctiveness,
                    editorial_usefulness=q.strategic_fit, reasons=q.reasons,
                    strategic_fit=q.strategic_fit, distinctiveness=q.distinctiveness,
                    audience_resonance=q.audience_resonance, source_strength=q.source_strength)
            else:
                quality = Quality.model_validate(draft.quality.model_dump())
            qualifiers = list(
                dict.fromkeys(draft.qualifiers + [limit for ref in refs for limit in moment_map[ref].qualifications])
            )
            risks = list(
                dict.fromkeys(
                    draft.risks + [f"handling: {moment_map[ref].sensitivity}; public reuse needs review" for ref in refs]
                )
            )
            identity = canonical_hash({"generation": artifact.request_fingerprint if artifact else "validation", "angle": raw})
            lineage = {"generated_at": artifact.created_at} if artifact else {}
            result.append(
                Angle(
                    angle_id=f"angle_{identity[:24]}",
                    run_id=artifact.run_id if artifact else run_id,
                    title=raw.get("title", ""),
                    argument=raw["core_perspective"] if strategic else raw["argument"],
                    audience=raw.get("audience", ""),
                    tension=raw.get("tension", ""),
                    take=raw["core_perspective"] if strategic else raw.get("take", ""),
                    mechanism=(raw["wia_expertise_in_action"] or raw["core_perspective"]) if strategic else raw.get("mechanism", ""),
                    reader_decision=raw.get("reader_decision", ""),
                    moment_ids=refs,
                    source_assertions=raw.get("source_assertions", []),
                    inference=raw.get("inference"),
                    qualifiers=qualifiers,
                    risks=risks,
                    signature=signature,
                    quality=quality,
                    base_score=quality.score(),
                    strategy=draft.model_copy(update={"qualifiers":qualifiers, "risks":risks}) if strategic else None,
                    source_family_id=("source_family_" + canonical_hash(sorted({sid for ref in refs for sid in moment_map[ref].source_ids}))[:24]) if strategic else None,
                    **lineage,
                )
            )
        return result

    def _load_history(self, run: RunManifest) -> list[Angle]:
        history = {}
        for path in (self.settings.data_root / "experiments").glob("**/angles.json"):
            if path.parent.name == run.run_id:
                continue
            try:
                manifest = RunManifest.model_validate_json((path.parent / "manifest.json").read_text(encoding="utf-8"))
                if (
                    manifest.status != "completed"
                    or manifest.week_index > run.week_index
                    or (manifest.mode == "fake") != (run.mode == "fake")
                    or manifest.embedding_profile != run.embedding_profile
                ):
                    continue
                for item in json.loads(path.read_text(encoding="utf-8")):
                    angle = Angle.model_validate(item)
                    history[angle.angle_id] = angle
            except (OSError, ValueError, TypeError):
                continue
        return [a for a in history.values() if a.embedding]
