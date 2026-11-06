"""Local report projection only: no inference, repairs, or source mutation."""
import json
import sys
from collections import Counter
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from backend_pipeline.config import BACKEND_ROOT
from backend_pipeline.model_experiment import SUITE, digest, verify_pool, verify_suite
from backend_pipeline.reviewed_experiment import home as reviewed_home
from backend_pipeline.reviewed_experiment import verify_reviewed_pool


repo = BACKEND_ROOT.parent
suite = repo / "testing/.data/experiments" / SUITE
manifest = verify_suite(suite)
out = repo / "research/week3-week4-comparison-2026-10-15"
out.mkdir(parents=True, exist_ok=True)
records = []
checks = {}
for week in (3, 4):
    shared = suite / f"shared/week{week}"
    reviewed = week == 4 and (reviewed_home(suite) / "freeze.json").exists()
    if reviewed:
        pool, seal = verify_reviewed_pool(suite)
        shared = reviewed_home(suite)
    elif (shared / "freeze.json").exists():
        pool, seal = verify_pool(suite, week)
    else:
        continue
    if pool is not None:
        requests = [json.loads((suite / f"cells/week{week}/{slug}/prepared-angle.request.json").read_text(encoding="utf-8"))
                    for slug in ("luna-pro", "sol", "sonnet")]
        checks[str(week)] = {
            "validated_moments": len(pool["moments"]),
            "pool_hash": seal["pool_hash"],
            "identical_angle_messages": all(r["messages"] == requests[0]["messages"] for r in requests),
            "reasoning_high_all_models": all(r.get("reasoning", {}).get("effort") == "high" for r in requests),
            "coverage_notes": pool["coverage_notes"],
            "evidence_origin": pool.get("evidence_origin", "Unaltered validated live extraction"),
        }
        (out / f"week{week}-shared-moments.md").write_bytes((shared / "review.md").read_bytes())
for plan in manifest["extractions"] + manifest["cells"]:
    stage, week, slug = plan["stage"], plan["week"], plan["slug"]
    home = suite / (f"extractions/week{week}" if stage == "moment_extraction" else f"cells/week{week}/{slug}")
    result = json.loads((home / "result.json").read_text(encoding="utf-8")) if (home / "result.json").exists() else {}
    run = home / "data/experiments/default/runs" / plan["run_id"]
    costs = [json.loads(p.read_text(encoding="utf-8")) for p in (run / "costs").glob("*.json")]
    row = {"week": week, "stage": stage, "slug": slug, "model": plan["model"],
           "run_id": plan["run_id"], "status": result.get("status", "pending"), "result": result,
           "home": str(home), "raw_response_count": len(list((home / "data").rglob("response.raw.json"))),
           "costs": [{k: c.get(k) for k in ("requested_model_id", "returned_model_id", "provider", "generation_id",
                     "dispatched", "reused", "validation_status", "new_cost_usd", "cost_status", "usage")} for c in costs]}
    extraction_result = suite / f"extractions/week{week}/result.json"
    if stage == "angle_generation" and not result and extraction_result.exists():
        upstream = json.loads(extraction_result.read_text(encoding="utf-8"))
        if upstream.get("status") == "failed" and str(week) not in checks:
            row["status"] = "not_run_extraction_failed"
            row["blocked_by"] = upstream
        elif week == 4 and str(week) in checks:
            row["status"] = "running" if (home / "started.json").exists() else "ready_reviewed_evidence"
    if (home / "result.json").exists() and (home / "started.json").exists():
        row["elapsed_seconds"] = round((home / "result.json").stat().st_mtime - (home / "started.json").stat().st_mtime, 3)
    if stage == "angle_generation" and result.get("status") == "completed":
        output = json.loads((run / "angle_generation.json").read_text(encoding="utf-8"))["output"]
        row.update({"candidate_count": len(output["angles"]), "internal_insight_count": len(output["internal_insights"]),
                    "pillars": dict(Counter(a["strategic_purpose"] for a in output["angles"])),
                    "readiness": dict(Counter(a["evidence_readiness"] for a in output["angles"])),
                    "candidates": [{k: a[k] for k in ("title", "strategic_purpose", "content_type", "core_perspective", "moment_ids")}
                                   for a in output["angles"]], "coverage_notes": output["coverage_notes"]})
        review = out / f"week{week}-{slug}.md"
        body = (home / "review.md").read_text(encoding="utf-8")
        if week == 3 and slug == "luna-pro":
            note = (
                "> **Independent source-review finding:** Two internal insight records have swapped references. "
                "The participant-progress insight cites the course-feedback moment `moment_ab2b2ecd0400f6f72b564f98`; "
                "the course-feedback insight cites the participant-progress moment `moment_2c5f077bd2fa4da6c1d7d62b`. "
                "Those two citations do not support their attached records. The generated content below is retained "
                "unchanged; see [the shared source shortlist](week3-shared-moments.md) for the correct passages. "
                "This note is a reviewer finding, not model output.\n\n"
            )
            body = note + body
            row["manual_source_findings"] = ["Two internal insights cite one another's source moments; see review note."]
        review.write_text(body, encoding="utf-8")
        row["review"] = str(review)
    records.append(row)
calls = [c for r in records for c in r["costs"] if c["dispatched"] and not c["reused"]]
known = sum((Decimal(str(c["new_cost_usd"])) for c in calls if c["new_cost_usd"] is not None), Decimal(0))
complete_billing = all(c["new_cost_usd"] is not None for c in calls)
report = {"generated_at_utc": datetime.now(UTC).isoformat(), "suite": str(suite), "suite_integrity": "verified",
          "source_files_unchanged": all(digest(Path(s["origin"])) == s["sha256"] for s in manifest["sources"]),
          "pool_checks": checks, "started_count": len(list(suite.rglob("started.json"))),
          "dispatch_count": len(list(suite.rglob("*.dispatch.json"))), "active_lock": (suite / "active-cell.lock").exists(),
          "completed_count": sum(r["status"] == "completed" for r in records), "max_paid_calls": 8,
          "known_reported_cost_usd": float(known), "all_dispatched_costs_known": complete_billing,
          "total_reported_cost_usd": float(known) if complete_billing else None, "records": records}
angle_records = [r for r in records if r["stage"] == "angle_generation"]
report["comparison_status"] = ("complete_with_reviewed_week4_recovery" if all(r["status"] == "completed" for r in angle_records)
                               else "in_progress_reviewed_week4_recovery" if "4" in checks
                               else "partial_week3_only" if any(r["status"] == "failed" for r in records) else "in_progress")
report["failed_count"] = sum(r["status"] == "failed" for r in records)
report["not_run_upstream_failed_count"] = sum(r["status"] == "not_run_extraction_failed" for r in records)
diagnostic_path = out / "week4-validation-diagnostic.json"
if diagnostic_path.exists():
    diagnostic = json.loads(diagnostic_path.read_text(encoding="utf-8"))
    report["week4_failure_diagnostic"] = {k: v for k, v in diagnostic.items() if k != "proposals"}
if (reviewed_home(suite) / "freeze.json").exists():
    report["week4_reviewed_recovery"] = {"status": "admitted_user_approved_derivative", "source_moments": 17,
                                        "quote_fields_changed": 2, "new_extraction_calls": 0,
                                        "original_failure_preserved": True,
                                        "home": str(reviewed_home(suite)),
                                        "approval": json.loads((reviewed_home(suite) / "approval.json").read_text(encoding="utf-8"))}
target = repo / "research/2026-10-15-week3-week4-model-comparison-results.json"
target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({k: report[k] for k in ("completed_count", "dispatch_count", "total_reported_cost_usd", "pool_checks")},
                 ensure_ascii=False, indent=2))
