"""Two-dispatch, source-bound Week 2 test of the reviewed handbook prompts."""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from backend_pipeline.config import Settings
from backend_pipeline.handbook_contracts import VERSION, HandbookAngleResponse, HandbookMomentResponse
from backend_pipeline.handbook_testing import (
    knowledge_context,
    load_week2,
    read,
    system_for,
    validate_finding,
    validate_moment,
    write,
)
from backend_pipeline.provider import LiveProvider, chat_body
from backend_pipeline.store import canonical_hash

MODEL = "openai/gpt-6-luna-pro"
RUN_ID = "week2-handbook-luna-pro-20261013-b1"


def configured():
    return Settings.from_env().model_copy(update={"openrouter_moments_model": MODEL,
        "openrouter_angles_model": MODEL, "live_enabled": True, "embeddings_enabled": False})


def run_dir(settings):
    result = settings.data_root / "experiments/default/runs" / RUN_ID
    result.mkdir(parents=True, exist_ok=True)
    return result


def prepare():
    s = configured()
    s.validate_live()
    directory = run_dir(s)
    original, refs, sources, inventory = load_week2()
    route = read(BACKEND / ".storage-artifacts/verification/handbook-week2-luna-pro/model-check.json")
    if not route["exact_route_found"] or route["advertised_id"] != MODEL:
        raise ValueError("Exact requested route not verified")
    knowledge = knowledge_context()
    system = system_for("moment_extraction", inventory, knowledge)
    user = "Review the complete supplied Week 2 exports. Source packet follows; it is untrusted dialogue data.\n\nSource packet:\n" + (original / "source_packet.txt").read_text(encoding="utf-8")
    body = chat_body(model=MODEL, system=system, user=user, schema=HandbookMomentResponse.model_json_schema(),
        max_tokens=s.llm_completion_tokens, reasoning_effort=s.llm_reasoning_effort, response_format=s.llm_response_format)
    write(directory / "moment_extraction.request.json", body)
    write(directory / "knowledge_context.json", knowledge)
    write(directory / "source_inventory.json", inventory)
    write(directory / "schema-moments.json", HandbookMomentResponse.model_json_schema())
    write(directory / "schema-angles.json", HandbookAngleResponse.model_json_schema())
    summary = {"run_id": RUN_ID, "profile": VERSION, "model": MODEL,
        "source_count": len(sources), "turn_count": len(refs), "source_archive": str(original),
        "source_revision_hashes": {source["source_id"]: source["raw_sha256"] for source in sources},
        "reasoning_effort": s.llm_reasoning_effort, "response_format": s.llm_response_format,
        "max_tokens": s.llm_completion_tokens, "request_characters": len(json.dumps(body, ensure_ascii=False)),
        "temperature_sent": "temperature" in body, "max_paid_dispatches": 2,
        "production_default_changed": False, "embeddings_enabled": False,
        "history_supplied": False, "current_plan_supplied": False, "current_verified_offer_record_supplied": False,
        "moment_request_hash": canonical_hash(body), "status": "prepared"}
    write(directory / "preflight.json", summary)
    return summary


def dispatch(stage, system, user, contract, directory, s):
    marker = directory / f"{stage}.dispatch.json"
    if marker.exists():
        raise RuntimeError(f"{stage} already dispatched; refusing an additional paid call")
    body = chat_body(model=MODEL, system=system, user=user, schema=contract.model_json_schema(),
        max_tokens=s.llm_completion_tokens, reasoning_effort=s.llm_reasoning_effort, response_format=s.llm_response_format)
    write(directory / f"{stage}.request.json", body)
    fingerprint = canonical_hash(body)
    write(marker, {"requested_model": MODEL, "request_hash": fingerprint,
        "dispatched_at": datetime.now(UTC).isoformat(), "status": "dispatched"})
    provider = LiveProvider(llm_base_url=s.openrouter_base_url, moments_model=MODEL, moments_key=s.openrouter_moments_key,
        angles_model=MODEL, angles_key=s.openrouter_angles_key, embedding_base_url=s.embedding_base_url,
        embedding_model=s.embedding_model, embedding_key=None, dimensions=s.embedding_dimensions,
        timeout=s.request_timeout_seconds, max_tokens=s.llm_completion_tokens, reasoning_effort=s.llm_reasoning_effort,
        response_format=s.llm_response_format,
        on_response=lambda _, raw: write(directory / f"{stage}.raw.json", raw))
    print(json.dumps({"stage": stage, "status": "dispatching", "model": MODEL}), flush=True)
    try:
        output, receipt = provider.json_call(stage=stage, system=system, user=user,
            schema=contract.model_json_schema(), fingerprint=fingerprint)
        write(directory / f"{stage}.output.json", output)
        if receipt["raw"].get("model") != MODEL:
            raise ValueError("Provider returned a different model; receipt preserved")
        raw = receipt["raw"]
        write(marker, {**read(marker), "status": "received", "returned_model": raw["model"],
            "provider": raw.get("provider"), "usage": raw.get("usage"),
            "finish_reason": raw["choices"][0].get("finish_reason")})
        return output
    except Exception as error:
        write(directory / f"{stage}.failure.json", {"error_type": type(error).__name__, "error": str(error)})
        raise


def extract():
    s = configured()
    directory = run_dir(s)
    preflight = read(directory / "preflight.json")
    if preflight["profile"] != VERSION or preflight["model"] != MODEL:
        raise ValueError("Preflight profile or model differs from the authorized test")
    _, refs, _, inventory = load_week2()
    body = read(directory / "moment_extraction.request.json")
    # JSON-object mode already added the schema to the saved system; avoid double insertion.
    system = system_for("moment_extraction", inventory, read(directory / "knowledge_context.json"))
    output = dispatch("moment_extraction", system, body["messages"][1]["content"], HandbookMomentResponse, directory, s)
    top_errors, rejected, valid, contexts = [], [], [], {}
    try:
        HandbookMomentResponse.model_validate(output)
    except ValueError as error:
        top_errors.append(str(error))
    coverage = output.get("recordings", [])
    expected = {i["meeting_ref"]: i for i in inventory}
    if len(coverage) != len(expected) or len({r.get("meeting_ref") for r in coverage}) != len(expected):
        top_errors.append("Recording coverage is incomplete or duplicated")
    for record in coverage:
        original = expected.get(record.get("meeting_ref"))
        if not original or any(record.get(key) != original[key] for key in ("source_id", "first_ref", "last_ref", "turn_count")):
            top_errors.append("Recording metadata differs from delivered inventory")
        if record.get("reviewed_extent") != "all_supplied":
            top_errors.append(f"Incomplete asserted assessment: {record.get('meeting_ref')}")
    keys = Counter(r.get("local_key") for r in output.get("moments", []))
    for raw in output.get("moments", []):
        try:
            if keys[raw.get("local_key")] != 1:
                raise ValueError("Duplicate moment local key")
            moment, context = validate_moment(raw, refs)
            valid.append(moment)
            contexts[moment["local_key"]] = context
        except (ValueError, KeyError, TypeError) as error:
            rejected.append({"record": raw, "error": str(error)})
    write(directory / "moments.json", valid)
    write(directory / "moment-context-refs.json", contexts)
    write(directory / "rejected-moments.json", rejected)
    summary = {"proposed": len(output.get("moments", [])), "validated": len(valid),
        "rejected": len(rejected), "coverage_contract_errors": top_errors,
        "status": "partial" if rejected or top_errors else "source_bound_complete",
        "quotation_text_generated": False, "semantic_claims_independently_verified": False,
        "source_references_validated": True, "source_coverage_is_model_assertion_not_proof_of_recall": True}
    write(directory / "moment-validation.json", summary)
    return summary


def angles():
    s = configured()
    directory = run_dir(s)
    _, refs, _, _ = load_week2()
    moments = read(directory / "moments.json")
    contexts = read(directory / "moment-context-refs.json")
    if not moments:
        raise ValueError("No validated moments; refusing an unsupported second-stage call")
    knowledge = read(directory / "knowledge_context.json")
    evidence = {ref: {key: refs[ref][key] for key in ("ref", "canonical_span_id", "meeting_ref", "ordinal", "start_ms", "end_ms", "speaker", "text")}
        for ref in dict.fromkeys(ref for context in contexts.values() for ref in context)}
    delivery = {"validated_moments": len(moments), "context_turns": len(evidence),
        "pool_validation": read(directory / "moment-validation.json"),
        "history_supplied": False, "plan_supplied": False, "current_verified_offers_supplied": False}
    system = system_for("angle_generation", delivery, knowledge)
    user = json.dumps({"moments": moments, "evidence_by_ref": evidence,
        "recent_published_history": None, "current_content_plan": None, "current_verified_offer_record": None,
        "input_limitation": "Only the validated extraction pool and original context regions are supplied; do not claim unseen full-recording coverage."}, ensure_ascii=False)
    output = dispatch("angle_generation", system, user, HandbookAngleResponse, directory, s)
    contract_errors, rejected, selected, others = [], [], [], []
    try:
        HandbookAngleResponse.model_validate(output)
    except ValueError as error:
        contract_errors.append(str(error))
    by_key = {m["local_key"]: m for m in moments}
    knowledge_ids = {r["id"] for r in knowledge["records"]}
    all_raw = output.get("selected_angles", []) + output.get("other_findings", [])
    keys = Counter(r.get("local_key") for r in all_raw)
    for kind, raws, dest in ((True, output.get("selected_angles", []), selected), (False, output.get("other_findings", []), others)):
        for raw in raws:
            try:
                if keys[raw.get("local_key")] != 1:
                    raise ValueError("Duplicate finding local key")
                dest.append(validate_finding(raw, by_key, contexts, refs, knowledge_ids, kind))
            except (ValueError, KeyError, TypeError) as error:
                rejected.append({"record": raw, "error": str(error)})
    ranks = sorted(a["rank"] for a in selected)
    if ranks != list(range(1, len(selected) + 1)):
        contract_errors.append("Validated SELECT ranks are not unique and contiguous")
    account = output.get("source_accounting", [])
    if Counter(a.get("moment_key") for a in account) != Counter(list(by_key)):
        contract_errors.append("Source accounting does not cover each supplied moment exactly once")
    known_keys = set(keys)
    for row in account:
        if any(key not in known_keys for key in row.get("finding_keys", [])):
            contract_errors.append("Source accounting references an unknown finding")
    for angle in selected:
        if angle["nearest_alternative"]["candidate_key"] not in known_keys | {None}:
            contract_errors.append("Nearest alternative references an unknown finding")
    notes = output.get("batch_notes", {})
    if notes.get("history_check") != "not_supplied" or notes.get("plan_check") != "not_supplied":
        contract_errors.append("The response claims a missing history/plan check")
    selected.sort(key=lambda a: a["rank"])
    write(directory / "selected-angles.json", selected)
    write(directory / "other-findings.json", others)
    write(directory / "rejected-findings.json", rejected)
    summary = {"proposed_selects": len(output.get("selected_angles", [])), "validated_selects": len(selected),
        "other_dispositions": dict(Counter(a["disposition"] for a in others)), "rejected": len(rejected),
        "contract_errors": contract_errors, "status": "partial" if rejected or contract_errors else "source_bound_complete",
        "purpose_counts": dict(Counter(a["primary_pillar"] for a in selected)),
        "optional_tension_null": sum(a["tension"] is None for a in selected),
        "editorial_claim_truth_and_founder_approval_not_established": True}
    write(directory / "angle-validation.json", summary)
    return summary


def review():
    s = configured()
    directory = run_dir(s)
    _, refs, sources, _ = load_week2()
    extraction = read(directory / "moment-validation.json")
    generation = read(directory / "angle-validation.json")
    selected, others = read(directory / "selected-angles.json"), read(directory / "other-findings.json")
    receipts = [read(directory / f"{stage}.dispatch.json") for stage in ("moment_extraction", "angle_generation")]
    costs = [receipt.get("usage", {}).get("cost") for receipt in receipts]
    total = sum(Decimal(str(cost)) for cost in costs) if all(cost is not None for cost in costs) else None
    source_by_meeting = {source["meeting_ref"]: source for source in sources}
    lines = ["# Week 2 handbook prompt test", "", "Recorded 13 October 2026. This tests the isolated handbook v2 profile on exact `openai/gpt-6-luna-pro`.", "",
        "The previous system prompts are preserved as inactive comments in the versioned templates. The reviewed behavioral prompts were used with a matching test-only contract and packet adapter. Existing production defaults, SQL workflows and UI were not migrated.", "",
        f"All 11 original Week 2 exports (5,218 turns) were supplied. Extraction proposed {extraction['proposed']} moments; {extraction['validated']} passed structural/source-reference checks and {extraction['rejected']} were rejected. Angle generation used only that validated pool and its original context.", "",
        f"Validated SELECT records: **{len(selected)}**. Other dispositions: `{generation['other_dispositions']}`. Rejected angle/finding records: {generation['rejected']}.", "",
        "These checks establish source binding and contract behavior, not independent factual verification, exhaustive opportunity recall, editorial quality or founder approval. All selections await editorial review. Source dates and naming permissions were not supplied.", "",
        "## Calls and cost", "", "| Stage | Returned model | Provider | Input tokens | Completion tokens | Reported USD |", "|---|---|---|---:|---:|---:|"]
    for stage, receipt in zip(("Moment shortlisting", "Angle selection"), receipts):
        usage = receipt.get("usage", {})
        lines.append(f"| {stage} | {receipt.get('returned_model')} | {receipt.get('provider')} | {usage.get('prompt_tokens')} | {usage.get('completion_tokens')} | {usage.get('cost')} |")
    lines += ["", f"Total reported new inference cost: **${total}**." if total is not None else "Total cost unavailable in one or more provider receipts.", "",
        "Two paid dispatches maximum, no automatic retries, no embeddings, no third model judge, no scripts or publication. Current verified offers, current content plan and recent published history were absent and explicitly disclosed.", "",
        "## Ranked selected angles", ""]

    def support(evidence_refs):
        result = ["#### Supporting source content (Zoom meeting · Week 2)", "",
            "Selected turns are separated in the original dialogue unless their timestamps are adjacent. Text and source speaker labels are reproduced from the archive; timestamps are elapsed recording time.", ""]
        meeting = None
        for ref in evidence_refs:
            turn = refs[ref]
            if turn["meeting_ref"] != meeting:
                meeting = turn["meeting_ref"]
                source = source_by_meeting[meeting]
                result += [f"**Recording:** [{source['metadata']['filename_label']}](<{Path(source['source_path']).as_posix()}>)", ""]
            seconds = turn["start_ms"] // 1000 if turn.get("start_ms") is not None else None
            time = f"{seconds//3600:02d}:{seconds//60%60:02d}:{seconds%60:02d}" if seconds is not None else "untimed"
            result += [f"**[{time}]** {turn['text']}", ""]
        return result

    for angle in selected:
        lines += [f"### {angle['rank']}. {angle['title']}", ""]
        for label, value in (("Central point", angle["central_point"]), ("Purpose/type", angle["primary_pillar"] + " · " + angle["content_type"]),
            ("Audience", angle["audience"]), ("Intended shift", angle["intended_shift"]), ("Why worthwhile", angle["why_worthwhile"]),
            ("Strategic reason", angle["strategic_rationale"]), ("Source demonstration", angle["source_demonstration"]),
            ("Development direction", angle["development_direction"]), ("Tension", angle["tension"]), ("Offer connection", angle["offer_connection"]),
            ("Nearest alternative", angle["nearest_alternative"]["comparison_reason"])):
            lines += [f"**{label}:** {value if value is not None else 'Not required for this direction.'}", ""]
        lines += ["Claim boundaries:", ""] + [f"- {boundary}" for boundary in angle["claim_boundaries"]] + ["",
            "| Dimension | Model judgment | Reason |", "|---|---:|---|"]
        for dimension, judgment in angle["judgments"].items():
            lines.append(f"| {dimension} | {judgment['value']} | {judgment['reason'].replace('|', '/')} |")
        lines += [""] + support(angle["evidence_refs"])
    lines += ["## Other findings and dispositions", ""]
    for finding in others:
        lines += [f"### {finding['disposition']} · {finding['summary']}", "", finding["disposition_reason"], ""]
        if finding["internal_use"]:
            lines += ["**Internal use:** " + finding["internal_use"], ""]
        if finding["proposed_reframe"]:
            lines += ["**Proposed reframe:** " + finding["proposed_reframe"], ""]
        for need in finding["retrieval_needs"]:
            lines += ["**Missing evidence:** " + need["question"], "", "**Retrieve:** " + need["needed_segment_or_record"], "",
                "**Resolution condition:** " + need["resolution_condition"], ""]
        if finding["evidence_refs"]:
            lines += support(finding["evidence_refs"])
    notes = read(directory / "angle_generation.output.json").get("batch_notes", {})
    lines += ["## Model batch rationale and input limits", "", notes.get("selection_rationale", ""), "", notes.get("mix_rationale", ""), ""]
    lines += [f"- {note}" for note in notes.get("limitations", []) + notes.get("evidence_dependent_gaps", [])]
    lines += ["", "## Validation limits", "", "Extraction validation:", "", "```json", json.dumps(extraction, indent=2), "```", "",
        "Angle validation:", "", "```json", json.dumps(generation, indent=2), "```", "",
        "This changes the prompt profile, response contract and validated source pool relative to the prior strategic-v1 test. It is not a controlled prompt-text-only experiment. Missing history limits novelty to this batch. Model scores are provisional judgments, not founder approval probabilities.", "",
        ]
    assessment = directory / "assistant-assessment.md"
    if assessment.exists():
        lines += [assessment.read_text(encoding="utf-8"), ""]
    lines += ["## Artifacts", "", f"Run: `{RUN_ID}`. Requests, raw receipts, untouched model outputs, source-reference maps, rejected records, and validation results remain in the run directory.", ""]
    text = "\n".join(lines)
    (directory / "review.md").write_text(text, encoding="utf-8")
    research = BACKEND.parent / "research/week2-handbook-luna-pro-test-review-2026-10-13.md"
    research.write_text(text, encoding="utf-8")
    # Scan only key values actually configured; never print them.
    keys = [key for key in (s.openrouter_moments_key, s.openrouter_angles_key) if key]
    hits = [path.name for path in directory.glob("*.json") if any(key in path.read_text(encoding="utf-8") for key in keys)]
    if hits:
        raise RuntimeError("Configured API key value found in an artifact; withhold delivery")
    summary = {"run_id": RUN_ID, "profile": VERSION, "technical_status": "partial" if extraction["status"] == "partial" or generation["status"] == "partial" else "source_bound_complete",
        "selected": len(selected), "other_dispositions": generation["other_dispositions"], "purpose_counts": generation["purpose_counts"],
        "paid_dispatches": len(receipts), "total_reported_new_cost_usd": float(total) if total is not None else None,
        "supplied_key_value_hits": 0, "human_approved": False, "review": str(research)}
    diagnostics = directory / "postrun-diagnostics.json"
    if diagnostics.exists():
        postrun = read(diagnostics)
        summary.update(skipped_material_reference_errors=len(postrun["skipped_material_reference_errors"]),
            nearest_alternative_self_references=len(postrun["nearest_alternative_self_references"]),
            editorial_acceptance="not_established; post-run issues found")
    write(directory / "final-summary.json", summary)
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["prepare", "extract", "angles", "review"])
    args = parser.parse_args()
    try:
        result = {"prepare": prepare, "extract": extract, "angles": angles, "review": review}[args.action]()
        print(json.dumps(result, indent=2), flush=True)
    except Exception as error:
        print(json.dumps({"action": args.action, "status": "failed", "error_type": type(error).__name__, "error": str(error)}), flush=True)
        raise
