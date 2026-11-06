"""Prepare a full-handbook angle request; paid execution requires explicit --live."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from backend_pipeline.config import Settings
from experiments.handbook_contracts import HandbookAngleResponse
from experiments.handbook_testing import (
    PROFILE,
    full_handbook_angle_system,
    load_week2,
    read,
    validate_finding,
    validate_moment,
    write,
)
from backend_pipeline.llm import chat_body
from backend_pipeline.store import canonical_hash

MODEL = "openai/gpt-6-luna-pro"
PARENT = "week2-handbook-luna-pro-20261013-b1"
RUN_ID = "week2-full-handbook-angle-20261013-c1"


def settings():
    return Settings.from_env().model_copy(update={"openrouter_moments_model": MODEL,
        "openrouter_angles_model": MODEL, "embeddings_enabled": False})


def directory(s):
    return s.data_root / "experiments/default/runs" / RUN_ID


def prepare():
    s = settings()
    target = directory(s)
    if (target / "angle_generation.dispatch.json").exists():
        raise RuntimeError("This angle call has already been dispatched; preserve its prepared request")
    target.mkdir(parents=True, exist_ok=True)
    parent = s.data_root / "experiments/default/runs" / PARENT
    _, refs, _, _ = load_week2()
    moments = read(parent / "moments.json")
    contexts = read(parent / "moment-context-refs.json")
    if not moments:
        raise ValueError("No validated moments available for this angle-only setup")
    for moment in moments:
        validated, context = validate_moment(moment, refs)
        if validated != moment or context != contexts[moment["local_key"]]:
            raise ValueError("Saved source pool differs from validation; no repair is permitted")
    evidence = {ref: {key: refs[ref][key] for key in ("ref", "canonical_span_id", "meeting_ref", "ordinal", "start_ms", "end_ms", "speaker", "text")}
        for ref in dict.fromkeys(ref for context in contexts.values() for ref in context)}
    history = [{"record_id": "market-research-email", "title": "The question we ask every new client",
        "content": (PROFILE / "market_research_email.md").read_text(encoding="utf-8").strip(),
        "use": "Existing content for overlap assessment only; historical commercial and performance claims are not current verified facts."}]
    delivery = {"validated_moments": len(moments), "context_turns": len(evidence),
        "pool_limitation": "Two individually source-bound moments from a prior partial Week 2 extraction; five rejected records remain excluded.",
        "history_supplied": True, "history_coverage": "One relevant archived email; not a complete publishing history.",
        "current_content_plan_supplied": False, "current_verified_offer_record_supplied": False}
    system = full_handbook_angle_system(delivery)
    user = json.dumps({"moments": moments, "evidence_by_ref": evidence, "content_history": history,
        "current_content_plan": None, "current_verified_offer_record": None,
        "input_limitation": delivery["pool_limitation"], "history_limitation": delivery["history_coverage"]}, ensure_ascii=False)
    schema = HandbookAngleResponse.model_json_schema()
    body = chat_body(model=MODEL, system=system, user=user, schema=schema,
        max_tokens=s.llm_completion_tokens, reasoning_effort=s.llm_reasoning_effort, response_format=s.llm_response_format)
    handbook = (PROFILE / "wia_content_system_handbook.md").read_text(encoding="utf-8").strip()
    feedback = (PROFILE / "angle_generation_feedback.md").read_text(encoding="utf-8").strip()
    if handbook not in body["messages"][0]["content"] or feedback not in body["messages"][0]["content"]:
        raise ValueError("Complete handbook or feedback was not rendered")
    if "PREVIOUS SYSTEM PROMPT PRESERVED" in body["messages"][0]["content"]:
        raise ValueError("Inactive predecessor leaked into the model request")
    keys = [key for key in (s.openrouter_moments_key, s.openrouter_angles_key, s.embedding_api_key) if key]
    if any(key in json.dumps(body, ensure_ascii=False) for key in keys):
        raise ValueError("A configured credential appears in the request content")
    write(target / "angle_generation.request.json", body)
    write(target / "prompt-messages.json", {"system": system, "user": user})
    write(target / "moments.json", moments)
    write(target / "moment-context-refs.json", contexts)
    write(target / "content-history.json", history)
    write(target / "schema-angles.json", schema)
    git_head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=BACKEND.parent, text=True).strip()
    summary = {"run_id": RUN_ID, "parent_moment_run": PARENT, "status": "prepared_not_dispatched",
        "model": MODEL, "stage": "angle_generation_only", "validated_moments": len(moments),
        "context_turns": len(evidence), "history_records": len(history),
        "history_coverage": delivery["history_coverage"], "full_handbook_included": True,
        "handbook_characters": len(handbook), "latest_feedback_included": True,
        "content_only_handbook": True, "request_characters": len(json.dumps(body, ensure_ascii=False)),
        "request_hash": canonical_hash(body), "handbook_content_hash": hashlib.sha256(handbook.encode()).hexdigest(),
        "setup_git_head": git_head, "configured_response_format": s.llm_response_format,
        "reasoning_effort": s.llm_reasoning_effort, "max_tokens": s.llm_completion_tokens,
        "current_plan_supplied": False, "current_verified_offer_record_supplied": False,
        "paid_dispatches": 0, "new_inference_cost_usd": 0, "embeddings_enabled": False}
    write(target / "preflight.json", summary)
    preview = "# Prepared Week 2 angle request\n\nThis is a local request preview. No model call has been made. The source pool is the same two validated moments from the prior partial extraction.\n\n"
    preview += "## System message before JSON contract\n\n" + system + "\n\n"
    preview += "## Source input and known limits\n\nThe request JSON contains both validated moments and their complete archived context regions. It also includes the full body of the related market-research email for a limited overlap check. The current plan and verified offer record are absent.\n"
    (target / "request-preview.md").write_text(preview, encoding="utf-8")
    return summary


def execute():
    # Imported only on explicit paid execution; prepare never instantiates a provider.
    from run_week2_handbook import dispatch

    s = settings()
    s.validate_live()
    target = directory(s)
    preflight = read(target / "preflight.json")
    messages = read(target / "prompt-messages.json")
    saved = read(target / "angle_generation.request.json")
    if preflight["model"] != MODEL or saved["model"] != MODEL:
        raise ValueError("Prepared model differs from the requested route")
    actual = chat_body(model=MODEL, system=messages["system"], user=messages["user"],
        schema=HandbookAngleResponse.model_json_schema(), max_tokens=s.llm_completion_tokens,
        reasoning_effort=s.llm_reasoning_effort, response_format=s.llm_response_format)
    if canonical_hash(actual) != preflight["request_hash"] or actual != saved:
        raise ValueError("Prepared request/configuration changed; inspect a fresh preview before dispatch")
    _, refs, _, _ = load_week2()
    moments = {m["local_key"]: m for m in read(target / "moments.json")}
    contexts = read(target / "moment-context-refs.json")
    output = dispatch("angle_generation", messages["system"], messages["user"], HandbookAngleResponse, target, s)
    HandbookAngleResponse.model_validate(output)
    selected = [validate_finding(a, moments, contexts, refs, {"handbook", "latest_feedback"}, True)
        for a in output["selected_angles"]]
    others = [validate_finding(a, moments, contexts, refs, {"handbook", "latest_feedback"}, False)
        for a in output["other_findings"]]
    finding_keys = [a["local_key"] for a in selected + others]
    if len(finding_keys) != len(set(finding_keys)):
        raise ValueError("Duplicate candidate/finding key")
    if sorted(a["rank"] for a in selected) != list(range(1, len(selected) + 1)):
        raise ValueError("SELECT ranks are not unique and contiguous")
    if Counter(a["moment_key"] for a in output["source_accounting"]) != Counter(list(moments)):
        raise ValueError("Each supplied moment must be accounted for exactly once")
    known = set(finding_keys)
    for account in output["source_accounting"]:
        if any(key not in known for key in account["finding_keys"]):
            raise ValueError("Accounting points to an unknown finding")
    for angle in selected:
        alternative = angle["nearest_alternative"]["candidate_key"]
        if alternative is not None and alternative not in known | {"market-research-email"}:
            raise ValueError("Alternative points to an unknown candidate or history item")
    if output["batch_notes"]["history_check"] != "checked_supplied_history" or output["batch_notes"]["plan_check"] != "not_supplied":
        raise ValueError("History/plan coverage does not match the prepared inputs")
    write(target / "selected-angles.json", selected)
    write(target / "other-findings.json", others)
    return {"run_id": RUN_ID, "status": "received", "selected": len(selected), "other_findings": len(others)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Dispatch the prepared paid angle call once; default is local preparation only")
    args = parser.parse_args()
    print(json.dumps(execute() if args.live else prepare(), indent=2), flush=True)
