"""Read-only validation of rejected proposals; write research projections only."""
import copy
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from backend_pipeline.config import BACKEND_ROOT
from backend_pipeline.model_experiment import SUITE, verify_suite
from backend_pipeline.models import Transcript
from backend_pipeline.pipeline import Pipeline
from backend_pipeline.weekly import resolve_moment_references

repo = BACKEND_ROOT.parent
suite = repo / "testing/.data/experiments" / SUITE
verify_suite(suite)
home = suite / "extractions/week4"
plan = json.loads((home / "plan.json").read_text(encoding="utf-8"))
run = home / "data/experiments/default/runs" / plan["run_id"]
artifact = json.loads((run / "moment_extraction.failed.json").read_text(encoding="utf-8"))
output = json.loads(artifact["raw_response"]["choices"][0]["message"]["content"])
refs = json.loads(next((home / "data").rglob("reference_map.json")).read_text(encoding="utf-8"))
transcripts = [Transcript.model_validate(t) for t in json.loads(
    (home / "data/cycles/week4/sources.json").read_text(encoding="utf-8"))["transcripts"]]
resolved = resolve_moment_references(output, {ref: item["canonical_span_id"] for ref, item in refs.items()})
# This pure parser needs no initialized provider, settings, store, or HTTP client.
parser = object.__new__(Pipeline)
rows = []
for original, moment in zip(output["moments"], resolved["moments"], strict=True):
    single = copy.deepcopy(resolved)
    single["moments"] = [moment]
    error = None
    try:
        parser._parse_moments(single, "offline-diagnostic-not-an-accepted-run", transcripts)
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
    row = {"local_key": original["local_key"], "individual_parser_check": "failed" if error else "passed",
           "error": error, "proposition": original["proposition"], "quote": original["quote"],
           "anchor_refs": original["anchor_span_ids"], "context_first_ref": original["context_first_span_id"],
           "context_last_ref": original["context_last_span_id"],
           "quote_matches_anchor": any(original["quote"] in refs[ref]["text"] for ref in original["anchor_span_ids"])}
    if error:
        row["original_anchor_turns"] = [{"ref": ref, "text": refs[ref]["text"]} for ref in original["anchor_span_ids"]]
    rows.append(row)
out = repo / "research/week3-week4-comparison-2026-10-15"
out.mkdir(parents=True, exist_ok=True)
diagnostic = {"batch_status": "failed", "accepted_moments": 0, "returned_proposals": len(rows),
              "individual_parser_passes_for_diagnosis_only": sum(r["error"] is None for r in rows),
              "individual_parser_failures": sum(r["error"] is not None for r in rows),
              "provider_reported_cost_usd": artifact["raw_response"]["usage"]["cost"],
              "angle_calls_sent": 0, "partial_pool_created": False, "automatic_repair_performed": False,
              "coverage_notes": output["coverage_notes"], "proposals": rows}
(out / "week4-validation-diagnostic.json").write_text(json.dumps(diagnostic, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
(out / "week4-rejected-proposals.json").write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
lines = ["# Week 4 rejected extraction: source review", "",
         "The model returned 17 proposals, but the whole extraction failed exact-quote validation. "
         "No proposals were admitted and no Week 4 angle model was called. "
         "Individual checks below are diagnostics only, not partial acceptance or a recovered evidence pool.", "",
         "The response passed the strategic response contract and compact-reference resolution. "
         "Fifteen proposals pass the normal parser individually; two fail literal quote matching. "
         "This does not establish semantic correctness or exhaustive source coverage.", "",
         "## Two literal-quote failures", ""]
for row in rows:
    if row["error"]:
        lines.extend([f"### {row['local_key']}", "", row["proposition"], "",
                      "**Model quote:** " + json.dumps(row["quote"], ensure_ascii=False), "",
                      "**Failure:** " + row["error"], ""])
        for anchor in row["original_anchor_turns"]:
            if (row["local_key"] == "m4_google_conversion_correction" and anchor["ref"] == "m4.t0256"
                or row["local_key"] == "m6_adjacent_search_intent" and anchor["ref"] == "m6.t0429"):
                lines.extend([f"**Original {anchor['ref']}:** {anchor['text']}", ""])
lines.extend(["## All rejected proposals with original source context", "",
              "Model interpretations below are retained as rejected proposals. Speaker labels are supplied transcript labels. "
              "Elapsed timestamps and original turn text are projected directly from the frozen source map.", ""])
order = list(refs)
for proposal, row in zip(output["moments"], rows, strict=True):
    lines.extend([f"### {row['local_key']}", "", row["proposition"], "",
                  f"**Individual parser check (diagnostic only):** {row['individual_parser_check']}", "",
                  "**Provisional discovery:** " + json.dumps(proposal["discovery"], ensure_ascii=False), "",
                  "**Qualifications:** " + json.dumps(proposal["qualifications"], ensure_ascii=False), ""])
    first, last = order.index(row["context_first_ref"]), order.index(row["context_last_ref"])
    for ref in order[first:last + 1]:
        item = refs[ref]
        seconds = item.get("start_ms")
        seconds = int(seconds // 1000) if seconds is not None else None
        stamp = "untimed" if seconds is None else f"{seconds//3600:02d}:{seconds//60%60:02d}:{seconds%60:02d}"
        lines.extend([f"**[{stamp}] {ref}** {item['text']}", ""])
(out / "week4-rejected-extraction-review.md").write_text("\n".join(lines), encoding="utf-8")
preview = copy.deepcopy(output)
replacements = {
    "m4_google_conversion_correction": ("m4.t0256", "or I guess this wouldn't be if they've actually booked the tour, this is them looking at the book a tour page."),
    "m6_adjacent_search_intent": ("m6.t0429", "we wouldn't want you ranking to say, like, marquee lights available, and then people click on an ad and get there, and then they're not there"),
}
edits = []
for proposal in preview["moments"]:
    if proposal["local_key"] not in replacements:
        continue
    ref, exact = replacements[proposal["local_key"]]
    assert ref in proposal["anchor_span_ids"] and exact in refs[ref]["text"]
    edits.append({"local_key": proposal["local_key"], "field": "quote", "original_value": proposal["quote"],
                  "proposed_value": exact, "source_ref": ref, "canonical_span_id": refs[ref]["canonical_span_id"],
                  "source_turn_text": refs[ref]["text"], "source_revision_sha256": refs[ref]["source_revision_sha256"]})
    proposal["quote"] = exact
validated_preview = parser._parse_moments(
    resolve_moment_references(preview, {ref: item["canonical_span_id"] for ref, item in refs.items()}),
    "offline-preview-not-an-accepted-run", transcripts)
reversed_preview = copy.deepcopy(preview)
for proposal in reversed_preview["moments"]:
    for edit in edits:
        if proposal["local_key"] == edit["local_key"]:
            proposal["quote"] = edit["original_value"]
assert reversed_preview == output and len(edits) == 2 and len(validated_preview) == 17
proposal_report = {"status": "proposal_only_not_applied", "changes": edits,
                   "whole_response_preview_parser_moments": len(validated_preview), "only_two_quote_fields_changed": True,
                   "original_content_sha256": hashlib.sha256(artifact["raw_response"]["choices"][0]["message"]["content"].encode()).hexdigest(),
                   "no_new_calls": True, "no_canonical_artifacts_changed": True, "accepted_pool_created": False,
                   "requires_explicit_recovery_protocol": True}
(out / "week4-quote-recovery-proposal.json").write_text(json.dumps(proposal_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
(out / "week4-quote-recovery-preview.json").write_text(json.dumps(preview, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({k: v for k, v in diagnostic.items() if k not in ("coverage_notes", "proposals")}, indent=2))
print("Local two-quote recovery preview: 17 moments pass; NOT applied or admitted.")
