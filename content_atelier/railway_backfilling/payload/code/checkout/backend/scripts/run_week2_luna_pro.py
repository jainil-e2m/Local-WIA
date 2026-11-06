"""User-authorized two-stage Week 2 strategic-discovery test on exact Luna Pro."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BACKEND=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BACKEND))

from backend_pipeline.config import Settings
from backend_pipeline.pipeline import Pipeline
from backend_pipeline.calibration import run_calibration
from backend_pipeline.prompts import weekly_moment_prompt
from backend_pipeline.provider import chat_body
from backend_pipeline.strategy_contracts import StrategicCompactMomentResponse, STRATEGY_VERSION
from backend_pipeline.store import canonical_hash
from backend_pipeline.weekly import meeting_inventory

MODEL="openai/gpt-6-luna-pro"
VERIFY=BACKEND/".storage-artifacts"/"verification"/"strategic-week2-luna-pro"


def settings():
    configured=Settings.from_env()
    return configured.model_copy(update={"openrouter_moments_model":MODEL,"openrouter_angles_model":MODEL,
        "live_enabled":True,"embeddings_enabled":False,"llm_payload_format":"compact_weekly"})


def prepare():
    s=settings()
    s.validate_live()
    route=json.loads((VERIFY/"model-check.json").read_text(encoding="utf-8"))
    if not route["exact_route_found"] or route["advertised_id"]!=MODEL:
        raise RuntimeError("The requested exact model route has not been verified")
    p=Pipeline(s)
    transcripts,packet=p.load_week(2)
    system,user=weekly_moment_prompt(packet,meeting_inventory(p._compact_refs))
    request=chat_body(model=MODEL,system=system,user=user,schema=StrategicCompactMomentResponse.model_json_schema(),
        max_tokens=s.llm_completion_tokens,reasoning_effort=s.llm_reasoning_effort,response_format=s.llm_response_format)
    (VERIFY/"moment-extraction.request-preview.json").write_text(json.dumps(request,ensure_ascii=False,indent=2),encoding="utf-8")
    summary={"profile":STRATEGY_VERSION,"week":2,"moments_model":MODEL,"angles_model":MODEL,
        "transcript_count":len(transcripts),"turn_count":sum(len(t.spans) for t in transcripts),
        "source_revision_hashes":{t.source_id:t.content_hash for t in transcripts},
        "raw_source_packet":str(p.store.path(p._packet_prefix)/"source_packet.txt"),
        "moment_request_hash":canonical_hash(request),"request_characters":len(json.dumps(request,ensure_ascii=False)),
        "temperature_sent":"temperature" in request,"output_cap":s.llm_completion_tokens,
        "input_limits_enabled":s.llm_input_limits_enabled,"reasoning_effort":s.llm_reasoning_effort,
        "response_format":s.llm_response_format,"request_timeout_seconds":s.request_timeout_seconds,
        "embeddings_enabled":False,"inference_requests":0}
    (VERIFY/"run-preflight.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")
    return summary


def run(run_id,mode,source_run=None):
    p=Pipeline(settings())
    try:
        result=(run_calibration(settings(),source_run_id=source_run,run_id=run_id,mode=mode)
                if source_run else p.run(2,mode=mode,run_id=run_id))
    except Exception as error:
        print(json.dumps({"run_id":run_id,"status":"failed","error_type":type(error).__name__,"error":str(error)},indent=2),flush=True)
        raise
    print(json.dumps(result,indent=2),flush=True)
    directory=f"experiments/default/runs/{run_id}"
    cost=p.store.read_json(f"{directory}/cost_summary.json")
    print(json.dumps({"artifacts":str(p.store.path(directory)),"total_new_cost_usd":cost["total_new_cost_usd"],
        "known_reported_new_cost_usd":cost["known_reported_new_cost_usd"],
        "stage_dispatches":{stage["stage"]:stage["dispatched_count"] for stage in cost["stages"]}},indent=2),flush=True)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare",action="store_true")
    parser.add_argument("--run-id")
    parser.add_argument("--mode",choices=["live","replay"],default="replay")
    parser.add_argument("--continue-from-run",help="Explicit partial-pool angle diagnostic; never reruns extraction")
    args=parser.parse_args()
    if args.prepare:
        print(json.dumps(prepare(),indent=2))
    elif args.run_id:
        run(args.run_id,args.mode,args.continue_from_run)
    else:
        parser.error("Provide --prepare or a fresh --run-id")
