"""NP-7's proof of pack-check.v3 against the labelled cases (NP.X5; not product code).

For each saved proof pack it builds exactly the request the pack's check stage sends under v3 (packs/fidelity.py: the
finished and written pieces, locked and personal lines skipped, the sources with the approved brief's WIA perspective), from
the brief's hand-off view on the scratch copy, sends it through the pipeline's own live provider under a capped file run
plan, and scores the answer against research/packs-2026-10/check-cases.json.

Usage (from backend/, ATELIER_DATABASE_URL naming scratch copy B, CHECK_KEY the OpenRouter key):
    python -I ../research/n5-2026-10/check_v3.py <out_dir> <label>=<proof pack file>...
Never prints the key.
"""
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BACKEND = HERE.parents[1] / "backend"
sys.path.insert(0, str(BACKEND))

from backend_pipeline.briefs import gate_two  # noqa: E402
from backend_pipeline.config import Settings  # noqa: E402
from backend_pipeline.llm.providers import live_provider  # noqa: E402
from backend_pipeline.llm.run_plans import new_plan  # noqa: E402
from backend_pipeline.packs import check_cases, fidelity, runtime_v2  # noqa: E402
from backend_pipeline.packs import contracts_v2 as c2  # noqa: E402
from backend_pipeline.repository import ContentRepository  # noqa: E402
from backend_pipeline.storage_config import StorageSettings  # noqa: E402

SONNET = "anthropic/claude-sonnet-5.5"
PROFILE = "2026-10-26.pack-check.v3"


def main():
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    specs = [a.partition("=") for a in sys.argv[2:]]
    plan = new_plan(purpose="NP-7 pack-check.v3 proof on the labelled cases", stages=["pack_check"], models=[SONNET],
                    input_set_hash="*", max_calls=2 * len(specs) + 2, max_cost_usd=0.15 * len(specs) + 0.10,
                    approver="kenil.shah@e2m.solutions", hours=3)
    plan_file = out / "check-v3-plan.json"
    plan_file.write_text(json.dumps(plan, indent=1), encoding="utf-8")
    os.environ["ATELIER_RUN_PLAN_FILE"] = str(plan_file)
    key = os.environ["CHECK_KEY"]
    models = Settings().model_copy(update={"openrouter_angles_key": key, "openrouter_moments_key": key,
                                           "llm_completion_tokens": 32000, "llm_response_format": "json_schema"})
    provider = live_provider(models, model=SONNET)
    repo = ContentRepository(StorageSettings.from_env())
    cases = check_cases.load(HERE.parent / "packs-2026-10" / "check-cases.json")
    statements_all, summary = [], []
    for label, _, file in specs:
        pack = json.loads((HERE.parent / "packs-2026-10" / "np5" / "proof" / file).read_text(encoding="utf-8"))
        pieces = {p["key"]: p for p in pack["pieces"]}
        keys = [k for k in c2.PIECE_KEYS if pieces.get(k, {}).get("origin") in ("finished", "written")]
        handoff = gate_two.handoff_v2(repo, pack["source_brief_id"])
        view, skip = fidelity.view(pieces, keys=keys)
        packet = {"sources": fidelity.sources(handoff, perspective=True), "pack": view, "skip": skip}
        output, meta = provider.json_call(stage="pack_check", system=runtime_v2.template(PROFILE),
                                          user=json.dumps(packet, ensure_ascii=False, sort_keys=True, default=str),
                                          schema=c2.wire_schema("pack_check"), fingerprint=f"np7-check-v3-{label}")
        statements = [s.model_dump() for s in c2.CheckOutput.model_validate(output).statements]
        flags = fidelity.flagged(statements, pieces, skip)
        (out / f"{label}.check-v3.json").write_text(json.dumps({"statements": statements, "flags": flags,
                                                               "usage": (meta.get("raw") or {}).get("usage")}, indent=1,
                                                              ensure_ascii=False), encoding="utf-8")
        statements_all += statements
        summary.append({"label": label, "statements": len(statements), "flagged": len(flags)})
        print(label, len(statements), "statements,", len(flags), "flagged")
    score = check_cases.score(cases, statements_all)
    ledger = json.loads(plan_file.read_text(encoding="utf-8"))
    result = {"packs": summary, "caught": [c["case_id"] for c in score["caught"]], "missed": [c["case_id"] for c in score["missed"]],
              "plan_cost_used_usd": ledger.get("cost_used_usd"), "plan_calls_used": ledger.get("calls_used")}
    (out / "check-v3-result.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
    print(json.dumps(result, indent=1))


if __name__ == "__main__":
    main()
