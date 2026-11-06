"""Render the strategic prompts/requests for review. Never dispatch inference."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from backend_pipeline.config import Settings
from backend_pipeline.models import Moment
from backend_pipeline.pipeline import Pipeline
from backend_pipeline.prompts import angle_prompt, weekly_moment_prompt
from backend_pipeline.llm import chat_body
from backend_pipeline.strategy_contracts import (
    STRATEGY_VERSION, StrategicMomentResponse, StrategicCompactMomentResponse, StrategicAngleResponse,
)
from backend_pipeline.weekly import meeting_inventory


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def prepare(week=None):
    settings = Settings.from_env()
    output = BACKEND / ".storage-artifacts" / "verification" / "strategic-discovery-v1"
    output.mkdir(parents=True, exist_ok=True)
    source = BACKEND / "backend_pipeline" / "prompt_templates"
    review = ["# Content Atelier: strategic discovery prompt release", "", f"Version: `{STRATEGY_VERSION}`.", "",
        "Derived from Whitney's Week 1 feedback and the additional analysis supplied on 13 October 2026.", "",
        "This snapshot shows the exact static templates used by the renderer. The shared strategy and editorial policy",
        "are appended to both stage system messages. The full typed response schema is supplied in each request.",
        "Whole-week extraction uses the lossless supplement and trusted meeting inventory; SQL paths use the same",
        "strategy and angle-record instructions. Source packets are untrusted evidence, supplied separately.", "",
        "Dynamic request previews, when prepared, are local review artifacts. No inference is dispatched by this script.", ""]
    templates = ["wia_strategy.md", "editorial_policy.md", "moment_extraction.system.md", "moment_extraction.user.md",
                 "moment_extraction.weekly_v3.md", "angle_generation.system.md", "angle_generation.user.md",
                 "angle_generation.sql_comparison_v1.md", "angle_refinement.sql_comparison_v1.md"]
    for template in templates:
        review += [f"## {template}", "", "```text", (source / template).read_text(encoding="utf-8").rstrip(), "```", ""]
    (BACKEND / "prompts-strategic-v1.md").write_text("\n".join(review), encoding="utf-8")
    for contract in (StrategicMomentResponse, StrategicCompactMomentResponse, StrategicAngleResponse):
        write_json(output / f"{contract.__name__}.schema.json", contract.model_json_schema())
    summary = {"profile":STRATEGY_VERSION, "inference_requests":0, "embedding_requests":0,
        "model_configuration_changed":False, "moment_model":settings.openrouter_moments_model,
        "angle_model":settings.openrouter_angles_model, "week":week}
    if week is not None:
        preview_settings = settings.model_copy(update={"data_root":output / "evidence", "llm_payload_format":"compact_weekly"})
        pipeline = Pipeline(preview_settings)
        transcripts, packet = pipeline.load_week(week)
        system, user = weekly_moment_prompt(packet, meeting_inventory(pipeline._compact_refs))
        request = chat_body(model=settings.openrouter_moments_model,system=system,user=user,
            schema=StrategicCompactMomentResponse.model_json_schema(),max_tokens=settings.llm_completion_tokens,
            reasoning_effort=settings.llm_reasoning_effort,response_format=settings.llm_response_format)
        write_json(output / f"week{week}-moment-extraction.request.json", request)
        summary.update(source_count=len(transcripts),source_turn_count=sum(len(t.spans) for t in transcripts))
        if week == 1:
            historic = BACKEND.parent / "testing" / ".data" / "experiments" / "default" / "runs" / "week1-gpt6-luna-partial-angle-diagnostic-20261008-a4"
            if (historic / "moments.json").exists():
                moments = [Moment.model_validate(m) for m in json.loads((historic / "moments.json").read_text(encoding="utf-8"))]
                spans = {s.span_id:s for t in transcripts for s in t.spans}
                for moment in moments:
                    if any(ref not in spans for ref in moment.context_span_ids + moment.anchor_span_ids):
                        raise ValueError("Historical moment references no longer match the source packet")
                    if not any(moment.quote in spans[ref].text for ref in moment.anchor_span_ids):
                        raise ValueError("Historical moment quote no longer matches its source")
                # Also compare full raw revisions with the original archived packet.
                parent = historic.parent / "week1-gpt6-luna-generation-only-20261008-a3"
                original_pointer = json.loads((parent / "weekly_packet.json").read_text(encoding="utf-8"))["artifact_directory"]
                original_sources = BACKEND.parent / "testing" / ".data" / original_pointer / "sources"
                originals = [json.loads(path.read_text(encoding="utf-8")) for path in original_sources.glob("*.json")]
                if {s["source_id"]:s["raw_sha256"] for s in originals}!={t.source_id:t.content_hash for t in transcripts}:
                    raise ValueError("Original Week 1 source revisions changed; refusing a misleading preview")
                system, user = angle_prompt(pipeline._moment_packet(moments,transcripts), [])
                request = chat_body(model=settings.openrouter_angles_model,system=system,user=user,
                    schema=StrategicAngleResponse.model_json_schema(),max_tokens=settings.llm_completion_tokens,
                    reasoning_effort=settings.llm_reasoning_effort,response_format=settings.llm_response_format)
                write_json(output / "week1-saved-pool-angle-generation.request.json", request)
                summary.update(angle_preview_source="historical seven-moment partial pool; no new extraction",
                               accepted_saved_moment_count=len(moments),original_source_revisions_verified=True)
    write_json(output / "readiness.json", summary)
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--week", type=int)
    print(json.dumps(prepare(parser.parse_args().week), indent=2))
