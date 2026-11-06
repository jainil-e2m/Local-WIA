"""Create an explicitly reviewed one-run proposal locally. Never applies it."""
import copy
import hashlib
import json
import socket
from collections import Counter

from process_reduced_run import load, write, OUT
from backend_pipeline.angle_profiles import scene_references
from backend_pipeline.store import JsonStore
from backend_pipeline.token_budget import preflight

REASONS = {
    "S74": "Opening VIP Day agenda and support schedule; retain substantive campaign decisions and evidence elsewhere in the call.",
    "S84": "Office-hours attendance, links and time logistics.",
    "S106": "Post-call staff impression of satisfaction, rather than direct client testimony or a measured outcome.",
    "S129": "Administrative follow-up on a proposal that had not arrived; no review findings yet.",
    "S138": "Website-access handoff logistics; no tracking implementation or outcome demonstrated.",
    "S144": "Vague acknowledgement of landing-page edits; no actual feedback or changed content is identified.",
    "S158": "Unspecified confusing pricing-guide wording and a possible future rewrite; no completed finding or revision.",
    "S162": "Routine search-terms screen navigation and relevant-traffic overview; retain the account's more substantive match-type, conversion and positioning scenes.",
    "S192": "Opening messaging-call agenda and requested materials; retain the substantive positioning interview scenes.",
    "S201": "Scheduling and requested-material follow-up for the next day's strategy call.",
    "S202": "Welcome and self-paced access logistics.",
    "S203": "Vault course navigation and booking-resource tour.",
    "S204": "VIP Day scheduling and standard delivery-process explanation, rather than a completed client case.",
    "S205": "Administrative clarification of when the six-month access period starts.",
    "S206": "Routine preparation and asset-review logistics for a future VIP Day; no review result yet.",
    "S207": "Suggested onboarding timetable and recurring office-hours attendance logistics; no client launch commitment or result.",
    "S208": "Orientation introductions and staff responsibility descriptions.",
    "S209": "Standard future Meta kickoff and submission-process explanation; no implemented strategy or outcome.",
    "S211": "Vault tabs, event calendar and replay-location walkthrough.",
    "S213": "Discussion-board participation logistics; no actual member interaction or result.",
    "S214": "Discussion-channel, feedback-submission and direct-message navigation.",
    "S282": "Opening LeadLock walkthrough agenda; excerpt ends before the proposed setup is demonstrated.",
    "S289": "Internal account-permission and linking follow-up; access details remain unconfirmed.",
}


def main():
    socket.socket = lambda *a, **k: (_ for _ in ()).throw(AssertionError("Offline processing forbids network access"))
    snapshot, request, ids, rows, packet, render, ui, suffix, dropped = load()
    assert snapshot["run"]["status"] == "failed"
    refs = scene_references(packet)
    inverse = {mid: ref for ref, mid in refs.items()}
    assert set(REASONS) <= set(refs)
    omitted = {refs[ref] for ref in REASONS}
    selected_ids = [mid for mid in ids if mid not in omitted]
    selected_packet = [m for m in packet if m["moment_id"] not in omitted]
    protected = {"human_line", "counter_expected_decision", "team_practice", "decision", "result", "objection", "tension", "story", "testimonial", "soundbite"}
    by_id = {m["moment_id"]: m for m in packet}
    assert all(by_id[mid]["moment_type"] not in protected for mid in omitted)
    reduced = copy.deepcopy(request)
    reduced["messages"][ui]["content"] = render(selected_packet) + suffix
    store = JsonStore(OUT / "artifacts")
    before, after = preflight(request, store), preflight(reduced, store)
    assert not before["fits"] and after["fits"]
    assert after["input_token_budget_allowance"] <= 818000
    assert before["input_token_budget_allowance"] == 859563
    assert request["model"] == reduced["model"] == "openai/gpt-6.1-sol"
    assert request["max_tokens"] == reduced["max_tokens"] == 32000
    assert request["response_format"] == reduced["response_format"]
    assert len(ids) == 291 and len(selected_ids) == 268 and len(omitted) == 23
    assert not dropped
    assert len(set(selected_ids)) == len(selected_ids)
    assert [mid for mid in ids if mid in set(selected_ids)] == selected_ids
    for i, (a, b) in enumerate(zip(request["messages"], reduced["messages"])):
        if i != ui:
            assert a == b
    before_docs = Counter(rows[mid]["document_id"] for mid in ids)
    after_docs = Counter(rows[mid]["document_id"] for mid in selected_ids)
    assert set(before_docs) == set(after_docs) and len(after_docs) == 16
    before_types = Counter(by_id[mid]["moment_type"] for mid in ids)
    after_types = Counter(by_id[mid]["moment_type"] for mid in selected_ids)
    assert all(before_types[t] == after_types[t] for t in protected)
    all_context = set().union(*(set(m["context_span_ids"]) for m in packet))
    kept_context = set().union(*(set(m["context_span_ids"]) for m in selected_packet))
    omissions = []
    for ref, reason in REASONS.items():
        mid = refs[ref]
        m = by_id[mid]
        context = set(m["context_span_ids"])
        omissions.append({"original_scene_ref": ref, "moment_id": mid, "document_id": rows[mid]["document_id"],
                          "type": m["moment_type"], "reason": reason, "summary": m["context_summary"],
                          "anchor_quote": m["quote"], "qualifications": m["qualifications"],
                          "context_span_count": len(context), "spans_not_in_retained_scenes": sorted(context-kept_context),
                          "dialogue_completely_covered_elsewhere": context <= kept_context})
    extraction = next(j for j in snapshot["jobs"] if j["stage"] == "moment_extraction")
    generation = next(j for j in snapshot["jobs"] if j["stage"] == "angle_generation")
    after_refs = {mid: ref for ref, mid in scene_references(selected_packet).items()}
    proposal = {"run_id": snapshot["run"]["run_id"], "extraction_job_id": extraction["job_id"], "generation_job_id": generation["job_id"],
                "proposal_only": True, "production_changes": False, "model_calls": 0, "snapshot_fetched_at": snapshot["fetched_at"],
                "review_basis": "Local editorial review of stored scene summaries, propositions, qualifications, anchors and original dialogue. Not a confidence-score ranking or lossless deduplication.",
                "original_verified": len(ids), "selected": len(selected_ids), "omitted": len(omitted),
                "unverified_unchanged": len(extraction["result_refs"].get("unverified_ids", [])),
                "selected_ids": selected_ids, "omissions": omissions,
                "original_preflight": before, "reduced_preflight": after,
                "byte_reduction": before["input_token_budget_allowance"]-after["input_token_budget_allowance"],
                "prompt_budget_headroom_after_margin": after["prompt_limit_reference_tokens"]-after["input_token_budget_allowance"]-after["unmeasured_provider_margin_tokens"],
                "original_prompt_reconstructed_exactly": True, "unchanged_situational_suffix_characters": len(suffix),
                "original_request_sha256": hashlib.sha256(json.dumps(request, sort_keys=True, ensure_ascii=False).encode()).hexdigest(),
                "reduced_request_sha256": hashlib.sha256(json.dumps(reduced, sort_keys=True, ensure_ascii=False).encode()).hexdigest(),
                "original_extraction_result_sha256": hashlib.sha256(json.dumps(extraction["result_refs"], sort_keys=True, ensure_ascii=False).encode()).hexdigest(),
                "unique_dialogue_spans_before": len(all_context), "unique_dialogue_spans_after": len(kept_context),
                "unique_dialogue_spans_omitted": len(all_context-kept_context),
                "protected_types": sorted(protected), "types_before": dict(before_types), "types_after": dict(after_types),
                "documents": [{"id": d, "title": next(t["title"] for t in snapshot["transcripts"] if t["transcript_id"]==d),
                               "original_scenes": before_docs[d], "selected_scenes": after_docs[d]} for d in before_docs],
                "reference_mapping": [{"moment_id": mid, "original_ref": inverse[mid], "new_ref": after_refs.get(mid)} for mid in ids],
                "coverage_restoration_note": "Restore original extraction result after the attempt. Retain actual selected IDs and reconcile generated scene_coverage with 291 originals; native coverage will truthfully be incomplete due to intentional omissions.",
                "retry_note": "Proposal only. No retry permitted by this preparation step. A future retry uses the existing generation-job retry mechanism, never the schedule counter."}
    write("selection-proposal.json", proposal)
    write("original-preflight.json", before)
    write("reduced-preflight.json", after)
    write("reduced-request.json", reduced)
    write("original-extraction-job.json", extraction)
    write("original-generation-job.json", generation)
    lines = ["# Proposed selection for this run — LOCAL ONLY", "", "No production records, jobs, settings or deployments were changed. No model calls were made.",
             "", "291 verified scene blocks → 268 selected; 23 routine operational/orientation scenes omitted. All 16 documents remain represented.",
             "This is editorial pruning, not lossless deduplication. Original unique dialogue is intentionally absent from the reduced request; all records remain preserved locally and in production.",
             "All human_line, counter_expected_decision, team_practice, decision, result, objection, tension, story, testimonial and soundbite scenes are retained.", "",
             f"Input allowance: {before['input_token_budget_allowance']:,} → {after['input_token_budget_allowance']:,} bytes. With margin: {after['input_token_budget_allowance']+after['unmeasured_provider_margin_tokens']:,} against {after['prompt_limit_reference_tokens']:,}. These are conservative byte allowances, not measured native tokens.", "",
             "## Per-document coverage", "", "| Document | Original scenes | Selected scenes |", "|---|---:|---:|"]
    lines += [f"| {d['title'].replace('|', '&#124;')} ({d['id']}) | {d['original_scenes']} | {d['selected_scenes']} |" for d in proposal["documents"]]
    lines += ["", "## Omission rationale", ""]
    for o in omissions:
        lines += [f"### {o['original_scene_ref']} — {o['moment_id']}", f"Type: {o['type']}. Document: {o['document_id']}.", "", o["reason"], "", "Scene: " + o["summary"],
                  "", "Anchor quote (omitted with the entire scene block): " + o["anchor_quote"], "", "Qualifications: " + "; ".join(o["qualifications"]), ""]
    lines += ["## Practical limits", "", "The preview reproduces the saved failed request exactly before pruning. A live retry can assemble updated situational context, so its final preflight must still pass. Passing this check does not guarantee downstream model or verification success.",
              "", "Restoration must preserve the original extraction result and actual sent IDs, and reconcile coverage snapshots. Native coverage will show intentional omissions as incomplete; do not mark them as consent exclusions or conceal them.", ""]
    (OUT/"selection-review.md").write_text("\n".join(lines),encoding="utf-8")
    print(json.dumps({k:proposal[k] for k in ("original_verified","selected","omitted","byte_reduction","prompt_budget_headroom_after_margin","unique_dialogue_spans_before","unique_dialogue_spans_after","unique_dialogue_spans_omitted")},indent=2))
    print(json.dumps({"preflight": after, "types_omitted":dict(before_types-after_types), "documents":proposal["documents"]}, indent=2))

if __name__ == "__main__":
    main()
