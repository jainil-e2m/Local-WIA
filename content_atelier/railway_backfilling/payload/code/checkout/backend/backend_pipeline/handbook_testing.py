"""Source validation and prompt assembly for the isolated handbook calibration run."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from .handbook_contracts import HandbookMoment, OtherFinding, SelectedAngle

BACKEND = Path(__file__).resolve().parents[1]
PROFILE = BACKEND / "backend_pipeline" / "prompt_templates" / "handbook_v2"


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def active_system(stage):
    text = (PROFILE / f"{stage}.system.md").read_text(encoding="utf-8")
    # Commented predecessor is documentation, not an active model instruction.
    active = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL).strip()
    manifest = read(PROFILE / "manifest.json")
    if hashlib.sha256(active.encode()).hexdigest() != manifest["templates"][stage]["active_sha256"]:
        raise ValueError("Active system prompt no longer matches the reviewed proposal")
    return active


def load_week2():
    baseline = read(BACKEND / ".storage-artifacts/verification/strategic-week2-luna-pro/run-preflight.json")
    original = Path(baseline["raw_source_packet"]).parent
    refs = read(original / "reference_map.json")
    sources = [read(path) for path in (original / "sources").glob("*.json")]
    sources.sort(key=lambda s: int(s["meeting_ref"][1:]))
    for source in sources:
        for path in (original / "raw" / (source["meeting_ref"] + ".original"), Path(source["source_path"])):
            if hashlib.sha256(path.read_bytes()).hexdigest() != source["raw_sha256"]:
                raise ValueError(f"Source revision changed: {source['meeting_ref']}")
    if len(sources) != 11 or len(refs) != 5218:
        raise ValueError("Week 2 source inventory differs from the authorized test")
    inventory = []
    for source in sources:
        turns = sorted((t for t in refs.values() if t["meeting_ref"] == source["meeting_ref"]), key=lambda t: t["ordinal"])
        inventory.append({"meeting_ref": source["meeting_ref"], "source_id": source["source_id"],
            "first_ref": turns[0]["ref"], "last_ref": turns[-1]["ref"], "turn_count": len(turns),
            "filename_label": source["metadata"]["filename_label"], "date": source["metadata"]["date"],
            "input_extent": "complete_supplied_transcript_export; recording/audio completeness not verified"})
    return original, refs, sources, inventory


def knowledge_context():
    ledger = read(BACKEND.parent / "research/2026-10-13-wia-handbook-understanding-ledger.json")
    records = [{"id": r["id"], "title": r["title"], "basis": r["basis"],
        "understanding": r["understanding"], "source_refs": r["source_refs"]} for r in ledger["records"]]
    return {"reference_version": ledger["ledger_version"], "source_sha256": ledger["source"]["sha256"],
        "authority": "User-supplied handbook is the editorial design reference; proposed examples and thresholds remain proposals.",
        "records": records, "current_verified_offer_record": None, "current_content_plan": None,
        "recent_published_content_history": None,
        "limitations": ["Handbook offer descriptions are not independently verified current scope or pricing.",
            "No current publishing plan supplied to this test.", "No recent published-content history supplied; within-batch distinctness only.",
            "Calibration cases describe historical excerpts, not factual evidence for Week 2."]}


def system_for(stage, inventory, knowledge):
    system = active_system(stage)
    system += "\n\nAPPLICATION-DESIGNATED EDITORIAL REFERENCES AND INPUT AVAILABILITY:\n" + json.dumps(knowledge, ensure_ascii=False)
    system += "\n\nTRUSTED DELIVERY INVENTORY (metadata, not conversation evidence):\n" + json.dumps(inventory, ensure_ascii=False)
    return system + packet_adapter(stage)


def packet_adapter(stage, *, full_handbook=False):
    system = "\n\nPACKET ADAPTER\nSource IDs and refs must be copied exactly. A ref such as m2.t0017 is a source turn, not a generated label. "
    system += "Turn order is its supplied source ordinal. Elapsed times are not dates. Context regions specify first_ref/last_ref "
    system += "inclusive within one meeting; the application hydrates every original turn between them. Separate regions remain separate. "
    system += "Do not emit quotation fields: supporting text will be hydrated from original refs without model transcription. "
    if full_handbook:
        system += "source_refs must identify supplied dialogue. For knowledge_refs use handbook or latest_feedback, according to which editorial reference supports the perspective. "
    else:
        system += "source_refs must identify supplied dialogue, while knowledge_refs identify actual H001–H060 reference records. "
    if stage == "moment_extraction":
        system += "\nUser source packet turns use ref|start+duration|exact cue body. Use meeting_ref from the delivery inventory. "
        system += "Copy recording first_ref, last_ref, source_id and turn_count exactly; reviewed_extent records your asserted assessment, not proof of recall. "
        system += "Source assertions use only spoken_view, proposed_action, reported_action, reported_result or expressed_understanding and source_refs. "
        system += "Keep their knowledge_refs empty. Strategic significance is an interpretation, separate from assertions."
    else:
        system += "\nThe user supplies validated moments and evidence_by_ref, containing actual original turns only for their context regions. "
        system += "The moment local_key is the moment key for all angle/accounting references. Every moment must be accounted for exactly once. "
        system += "For factual source claims cite refs from the supporting moments' contexts. Brand perspectives may cite supplied knowledge_refs; "
        system += "editorial inferences must remain bounded and cannot replace missing factual support. "
        system += "SELECT ranks must be unique and contiguous from 1. Tension/offer_connection/possible_format may be null. "
        system += "If no meaningful nearest alternative exists, use null candidate_key and central_point and explain why. "
        if full_handbook:
            system += "history_check must be checked_supplied_history because one relevant archived email is supplied. "
            system += "Compare explicitly against that email, and disclose that this is a limited overlap check, not a complete published-history check. "
            system += "plan_check must be not_supplied because no current content plan is supplied. "
            system += "A nearest alternative candidate_key must not refer to the selected candidate itself. "
            system += "Use a separate actual finding key, the supplied market-research-email history ID, or null with a clearly described considered alternative."
        else:
            system += "history_check and plan_check must be not_supplied because this test provides neither history nor a plan."
    return system


def full_handbook_angle_system(inventory):
    handbook = (PROFILE / "wia_content_system_handbook.md").read_text(encoding="utf-8").strip()
    feedback = (PROFILE / "angle_generation_feedback.md").read_text(encoding="utf-8").strip()
    if not handbook or not feedback:
        raise ValueError("The handbook and latest feedback must be complete and nonempty")
    system = active_system("angle_generation")
    system += "\n\nWIA CONTENT SYSTEM HANDBOOK\n" + handbook
    system += "\n\nLATEST SUPPLIED EDITORIAL FEEDBACK\n" + feedback
    system += "\n\nAPPLICATION GUIDANCE FOR THESE REFERENCES\n"
    system += "The handbook is the supplied editorial design reference; the feedback refines the angle framing and selection expectations. "
    system += "Retain the handbook's own distinction between established guidance and proposed examples or thresholds. "
    system += "Neither reference supplies facts about this week's recordings, current offer details, or publication permission. "
    system += "The reference files contain document content only; do not invent provenance or approval from their formatting. "
    system += "Carry the strongest supported insight from the rationale into the working title, central point and intended shift. "
    system += "For process content, explain the value of WIA's thinking and collaboration; use the tactical detail as the example. "
    system += "Use plain, confident language and choose pillar/type according to the actual audience effect. "
    system += "Assess distinctiveness against the supplied email and explain the substantive new contribution, or defer the overlapping treatment. "
    system += "Treat the archived email as content history only: its historical prices, service statements, comparative claims and wording do not establish current facts or override the handbook. "
    system += "No verified current offer record or current publishing plan is supplied."
    system += "\n\nTRUSTED DELIVERY INVENTORY (metadata, not conversation evidence):\n" + json.dumps(inventory, ensure_ascii=False)
    return system + packet_adapter("angle_generation", full_handbook=True)


def ordered_refs(ids, refs, meeting=None):
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate source reference")
    if any(ref not in refs for ref in ids):
        raise ValueError("Unknown source reference")
    if meeting is not None and any(refs[ref]["meeting_ref"] != meeting for ref in ids):
        raise ValueError("Cross-meeting source reference")
    if ids != sorted(ids, key=lambda ref: (int(refs[ref]["meeting_ref"][1:]), refs[ref]["ordinal"])):
        raise ValueError("Source references are out of original order")


def validate_moment(raw, refs):
    moment = HandbookMoment.model_validate(raw)
    ordered_refs(moment.anchor_refs, refs, moment.meeting_ref)
    context = []
    previous_end = -1
    for region in moment.context_regions:
        ordered_refs([region.first_ref] if region.first_ref == region.last_ref else [region.first_ref, region.last_ref], refs, moment.meeting_ref)
        start, end = refs[region.first_ref]["ordinal"], refs[region.last_ref]["ordinal"]
        if start > end or start <= previous_end:
            raise ValueError("Overlapping, reversed, or unordered context regions")
        previous_end = end
        context.extend(t["ref"] for t in sorted(refs.values(), key=lambda t: t["ordinal"])
            if t["meeting_ref"] == moment.meeting_ref and start <= t["ordinal"] <= end)
    allowed = set(context)
    if not set(moment.anchor_refs) <= allowed:
        raise ValueError("Anchor is outside context")
    for claim in moment.assertions:
        ordered_refs(claim.source_refs, refs, moment.meeting_ref)
        if not claim.source_refs or not set(claim.source_refs) <= allowed or claim.knowledge_refs:
            raise ValueError("Source assertion lacks local dialogue support")
        if claim.state in {"brand_perspective", "editorial_inference"}:
            raise ValueError("Interpretation incorrectly placed in source assertions")
    for contribution in moment.contributions:
        ordered_refs(contribution.source_refs, refs, moment.meeting_ref)
        if not set(contribution.source_refs) <= allowed:
            raise ValueError("Contribution is outside context")
        if any(refs[ref]["speaker"] != contribution.speaker_label for ref in contribution.source_refs):
            raise ValueError("Contribution speaker differs from source label")
    for need in moment.retrieval_needs:
        ordered_refs(need.known_refs, refs, moment.meeting_ref)
    return moment.model_dump(), context


def validate_finding(raw, moments, contexts, refs, knowledge_ids, selected):
    finding = (SelectedAngle if selected else OtherFinding).model_validate(raw)
    if len(finding.moment_keys) != len(set(finding.moment_keys)) or any(key not in moments for key in finding.moment_keys):
        raise ValueError("Unknown or duplicate moment key")
    allowed = {ref for key in finding.moment_keys for ref in contexts[key]}
    ordered_refs(finding.evidence_refs, refs)
    if not set(finding.evidence_refs) <= allowed:
        raise ValueError("Evidence is outside supporting moment context")
    if selected:
        if finding.nearest_alternative.candidate_key == finding.local_key:
            raise ValueError("Nearest alternative cannot point to the selected candidate itself")
        for claim in finding.claims:
            ordered_refs(claim.source_refs, refs)
            if not set(claim.source_refs) <= allowed or not set(claim.knowledge_refs) <= knowledge_ids:
                raise ValueError("Claim has unknown or out-of-context references")
            if claim.state not in {"brand_perspective", "editorial_inference"} and (not claim.source_refs or claim.knowledge_refs):
                raise ValueError("Factual claim requires dialogue evidence, not brand knowledge")
            if claim.state == "brand_perspective" and not claim.knowledge_refs:
                raise ValueError("Brand perspective needs a knowledge reference")
        scores = finding.judgments.model_dump()
        if any(score["value"] <= 2 for score in scores.values()):
            raise ValueError("SELECT has a required-revision score under the initial handbook heuristic")
        for key in ("audience_relevance", "strategic_value_brand_fit", "distinctiveness"):
            if scores[key]["value"] < 4:
                raise ValueError("SELECT is below the initial prioritization threshold")
        if scores["source_support"]["value"] < 4:
            raise ValueError("SELECT has only partial central-claim support")
    else:
        for need in finding.retrieval_needs:
            ordered_refs(need.known_refs, refs)
            if not set(need.known_refs) <= allowed:
                raise ValueError("Retrieval locator is outside supplied supporting evidence")
    return finding.model_dump()
