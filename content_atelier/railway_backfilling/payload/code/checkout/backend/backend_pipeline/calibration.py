"""Explicit partial-pool diagnostic, not a successful full weekly run.

Uses individually strict-validated moments from a preserved received response.
Never repairs quotations, admits unknown/cross-meeting refs, or generates vectors.
"""

from __future__ import annotations

import argparse
import json

from .config import Settings
from .contracts import CompactMomentResponse
from .strategy_contracts import StrategicAngleResponse, StrategicCompactMomentResponse, is_strategic_moment_response
from .models import RunManifest
from .pipeline import Pipeline
from .prompts import angle_prompt
from .store import canonical_hash
from .weekly import LIVE_COMPACT_VERSION, resolve_moment_references


def diagnose_received_moments(pipeline: Pipeline, source_run_id: str):
    source_dir = f"experiments/default/runs/{source_run_id}"
    source_run = RunManifest.model_validate(pipeline.store.read_json(f"{source_dir}/manifest.json"))
    if source_run.status != "failed" or source_run.mode != "live" or source_run.prompt_profile != LIVE_COMPACT_VERSION:
        raise ValueError("Diagnostic requires a received live response from the current exact weekly profile")
    transcripts, _packet = pipeline.load_week(source_run.week_index)
    failed = pipeline.store.read_json(f"{source_dir}/moment_extraction.failed.json")
    attempt = f"service_calls/{failed['request_fingerprint']}/attempts/{failed['artifact_id']}"
    received = pipeline.store.read_json(f"{attempt}/output.received.json")
    response = (StrategicCompactMomentResponse if is_strategic_moment_response(received) else CompactMomentResponse).model_validate(received)
    pipeline._local_keys(response.moments)
    original = pipeline.store.read_json(f"{source_dir}/weekly_packet.json")["artifact_directory"]
    original_map = pipeline.store.read_json(f"{original}/reference_map.json")
    current_map = pipeline.store.read_json(f"{pipeline._packet_prefix}/reference_map.json")
    original_sources = [
        pipeline.store.read_json(str(path.relative_to(pipeline.store.root)))
        for path in pipeline.store.path(f"{original}/sources").glob("*.json")
    ]
    original_revisions = {source["source_id"]: source["raw_sha256"] for source in original_sources}
    current_revisions = {transcript.source_id: transcript.content_hash for transcript in transcripts}
    if original_map != current_map or original_revisions != current_revisions:
        raise ValueError("Source snapshot changed; cannot diagnose received output against different evidence")
    accepted, rejected = [], []
    for draft in received["moments"]:
        packet = {**received, "moments": [draft]}
        try:
            canonical = resolve_moment_references(packet, pipeline._compact_refs)
            accepted.extend(pipeline._parse_moments(canonical, source_run.run_id, transcripts))
        except (ValueError, KeyError, TypeError) as error:
            rejected.append({"local_key": draft["local_key"], "error": str(error), "received_record": draft})
    if not accepted:
        raise ValueError("No individually source-valid moments; refusing an empty angle diagnostic")
    return source_run, transcripts, accepted, rejected, received, attempt


def run_calibration(settings: Settings, *, source_run_id: str, run_id: str, mode: str = "replay", provider=None) -> dict:
    if settings.embeddings_enabled:
        raise RuntimeError("Calibration requires embeddings to remain disconnected")
    pipeline = Pipeline(settings, provider)
    source_run, transcripts, moments, rejected, received, attempt = diagnose_received_moments(pipeline, source_run_id)
    pipeline._select_provider(mode)
    run = RunManifest(
        run_id=run_id,
        week_index=source_run.week_index,
        source_root=source_run.source_root,
        source_ids=source_run.source_ids,
        prompt_profile=LIVE_COMPACT_VERSION,
        model_id=settings.openrouter_angles_model,
        embedding_profile=f"{settings.embedding_model}:{settings.embedding_dimensions}",
        mode=mode,
        parent_run_id=source_run_id,
        status="partial",
        execution_scope="generation_only",
    )
    run_dir = f"experiments/default/runs/{run_id}"
    if pipeline.store.path(f"{run_dir}/manifest.json").exists():
        raise ValueError("Diagnostic report ID already exists; original records are immutable")
    pipeline.store.write_model(f"{run_dir}/manifest.json", run)
    pipeline.store.write_json(
        f"{run_dir}/moment_diagnostic.json",
        {
            "purpose": "angle_prompt_test_from_partial_individually_validated_pool",
            "source_run_id": source_run_id,
            "received_attempt_directory": attempt,
            "source_profile": source_run.prompt_profile,
            "source_week_complete_run": False,
            "original_proposal_count": len(received["moments"]),
            "accepted_count": len(moments),
            "rejected_count": len(rejected),
            "no_quotes_repaired": True,
            "new_extraction_requests": 0,
            "delivery_span_count": sum(len(t.spans) for t in transcripts),
        },
    )
    pipeline.store.write_json(f"{run_dir}/rejected_moments.json", rejected)
    pipeline.store.write_json(f"{run_dir}/moments.json", [m.model_dump(mode="json") for m in moments])
    system, user = angle_prompt(pipeline._moment_packet(moments, transcripts), [])
    dependencies = canonical_hash({"system": system, "user": user, "moment_ids": [m.moment_id for m in moments]})
    try:
        artifact = pipeline._call_json(
            "angle_generation",
            run,
            run_dir,
            system,
            user,
            dependencies,
            StrategicAngleResponse.model_json_schema(),
            validate=lambda output: pipeline._parse_angles(output, run_id, moments),
        )
        candidates = pipeline._parse_angles(artifact.output, run_id, moments, artifact=artifact)
        pipeline.store.write_json(f"{run_dir}/candidates.json", [a.model_dump(mode="json") for a in candidates])
        pipeline._write_discovery_outputs(run_dir, artifact.output, candidates)
        pipeline.store.write_json(
            f"{run_dir}/review.json",
            {
                "run_id": run_id,
                "status": "partial",
                "purpose": "partial_pool_angle_prompt_diagnostic",
                "source_run_id": source_run_id,
                "full_weekly_pipeline_succeeded": False,
                "accepted_moment_count": len(moments),
                "rejected_moment_count": len(rejected),
                "candidate_angle_ids": [a.angle_id for a in candidates],
                "visible_angle_ids": [],
                "angle_count": len(candidates),
                "embedding_requests": 0,
                "similarity_status": "not_run",
                "recency_adjustment_status": "not_run",
                "human_approved": False,
            },
        )
    except Exception:
        run.status = "failed"
        pipeline.store.write_model(f"{run_dir}/manifest.json", run, overwrite=True)
        raise
    # Keep partial: a successful Call 2 is not a successful complete extraction.
    return {
        "run_id": run_id,
        "status": "partial",
        "source_run_id": source_run_id,
        "accepted_moments": len(moments),
        "rejected_moments": len(rejected),
        "angles": len(candidates),
        "embedding_requests": 0,
        "new_extraction_requests": 0,
    }


def main():
    parser = argparse.ArgumentParser(description="Explicit partial-pool angle diagnostic; no new extraction or embeddings")
    parser.add_argument("--from-run", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--mode", choices=["live", "replay"], default="replay")
    args = parser.parse_args()
    print(
        json.dumps(
            run_calibration(Settings.from_env(), source_run_id=args.from_run, run_id=args.run_id, mode=args.mode), indent=2
        )
    )


if __name__ == "__main__":
    main()
