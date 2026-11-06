"""NP.X2a: one capped live Opus 5.5 call through the pipeline's own provider (not product code).

It proves, before any paid pack run, that an Opus request built by `llm.request.chat_body` (strict json_schema with the
finisher's own wire schema, reasoning medium, no temperature, usage asked for) passes S.B1's routing, is accepted, and
settles its reported cost against a run plan. The output cap is 2,000 tokens and the file run plan's cap USD 0.06, so the
call cannot cost more (a retry whose worst case passes the cap is refused before sending).

Usage (from backend/): python -I ../research/packs-2026-10/np5/x2a_capped_call.py <out_dir>
Never prints the key.
"""
import json
import os
import sys
import time
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[3] / "backend"
sys.path.insert(0, str(BACKEND))

from backend_pipeline.config import Settings  # noqa: E402
from backend_pipeline.llm.providers import live_provider  # noqa: E402
from backend_pipeline.llm.run_plans import new_plan  # noqa: E402
from backend_pipeline.packs import contracts_v2 as c2  # noqa: E402

OPUS = "anthropic/claude-opus-5.5"


def key():
    for line in (BACKEND / ".env").read_text(encoding="utf-8").splitlines():
        if line.startswith("OPENROUTER_API_KEY_INTERNAL="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("key missing")


def main():
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    plan = new_plan(purpose="NP.X2a capped live Opus call", stages=["pack_finish"], models=[OPUS], input_set_hash="*",
                    max_calls=2, max_cost_usd=0.06, approver="kenil.shah@e2m.solutions", hours=2)
    plan_file = out / "x2a-plan.json"
    plan_file.write_text(json.dumps(plan, indent=1), encoding="utf-8")
    os.environ["ATELIER_RUN_PLAN_FILE"] = str(plan_file)
    models = Settings().model_copy(update={"openrouter_angles_key": key(), "openrouter_moments_key": key(),
                                           "llm_completion_tokens": 2000, "llm_response_format": "json_schema"})
    provider = live_provider(models, model=OPUS)
    system = ("You are testing a structured-output contract. Return one JSON object that matches the schema with the shortest "
              "valid values: two or three words per text field, exactly three reels in the order story, stance, broll_text "
              "(the broll_text reel has one screen and a null script and spoken_opening; the other two have a one-sentence "
              "script), three subject options, two cover alternates per reel, one beat per reel, empty lists elsewhere, "
              "and a carousel with exactly seven slides numbered 1 to 7.")
    user = json.dumps({"topic": "a synthetic test about replying to wedding inquiries"})
    t0 = time.time()
    output, meta = provider.json_call(stage="pack_finish", system=system, user=user, schema=c2.wire_schema("pack_finish"),
                                      fingerprint="np-x2a-1")
    seconds = round(time.time() - t0, 1)
    raw = meta.get("raw") or {}
    validated = c2.FinishOutput.model_validate(output)
    ledger = json.loads(plan_file.read_text(encoding="utf-8"))
    result = {"seconds": seconds, "model": raw.get("model"), "provider": raw.get("provider"),
              "finish_reason": (raw.get("choices") or [{}])[0].get("finish_reason"), "usage": raw.get("usage"),
              "strict_schema_accepted": True, "validated_reels": [r.kind for r in validated.reels],
              "plan_cost_used_usd": ledger.get("cost_used_usd"), "plan_calls_used": ledger.get("calls_used")}
    (out / "x2a-result.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
    print(json.dumps(result, indent=1))


if __name__ == "__main__":
    main()
