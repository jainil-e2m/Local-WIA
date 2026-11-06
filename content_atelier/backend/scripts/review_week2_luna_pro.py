"""Offline source/cost/lineage review of the approved Week 2 Luna Pro test."""
import json
import sys
from collections import Counter
from decimal import Decimal
from pathlib import Path

BACKEND=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BACKEND))

from backend_pipeline.config import Settings
from backend_pipeline.store import canonical_hash

PARENT="week2-luna-pro-strategic-20261013-a1"
CHILD="week2-luna-pro-strategic-angles-20261013-a2"
REPLAY="week2-luna-pro-strategic-angles-20261013-r1"

# Original cue ordinals, including context needed to show the exchange behind each idea.
SUPPORTING_TURNS={
    "moment_320404b2bc5d92895b225dda": [545,548,552,557,564,568,572,576,581],
    "moment_86ec3df1112e407a165587c0": [83,84,85,87,88,96,102,105,107,111,114,
        139,141,147,148,150,151,154,197,198,199,203,204],
    "moment_e0d8f47e45ba342a1efcd623": [354,356,359,360,362,373,412,414,415,416,
        494,499,500,563,565,566,569,571,573,574,578,582],
    "moment_c1abec47fcf4f256f5ea03f7": [33,38,39,40,43,44,62,64,66,70,
        132,134,135,136,142,143,144,145,146,148,149,151,154,155,156,157,158,159],
    "moment_aa285901c5f1b5e2e3275c1c": [155,157,160,214,219,266,270,286,
        288,289,291,292,294,295,298,303,306],
}


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def supporting_source_content(moment_ids, moments_by_id, refs_by_span, sources_by_id):
    lines=[]
    for moment_id in moment_ids:
        moment=moments_by_id[moment_id]
        source_id,=moment["source_ids"]
        source=sources_by_id[source_id]
        selected={f"{source_id}:span:{ordinal}" for ordinal in SUPPORTING_TURNS[moment_id]}
        allowed=set(moment["anchor_span_ids"]) | set(moment["context_span_ids"])
        if not selected <= allowed:
            raise RuntimeError(f"Supporting turns fall outside validated context: {moment_id}")
        label=source["metadata"]["filename_label"]
        source_path=Path(source["source_path"]).as_posix()
        lines += ["", "#### Supporting source content (Zoom meeting · Week 2)", "",
            f"**Recording:** [{label}](<{source_path}>)", "",
            "Selected turns below are separated in the original dialogue unless their timestamps are adjacent.", ""]
        for span_id in sorted(selected,key=lambda key: refs_by_span[key]["ordinal"]):
            turn=refs_by_span[span_id]
            seconds=turn["start_ms"]//1000
            timestamp=f"{seconds//3600:02d}:{seconds//60%60:02d}:{seconds%60:02d}"
            # Source text already includes the original speaker label.
            lines += [f"**[{timestamp}]** {turn['text']}", ""]
    return lines


def review():
    settings=Settings.from_env()
    data=settings.data_root
    runs=data/"experiments"/"default"/"runs"
    parent,child,replay=(runs/name for name in (PARENT,CHILD,REPLAY))
    moments=read(child/"moments.json")
    opportunities=read(child/"opportunities.json")
    insights=read(child/"internal_insights.json")
    first=read(parent/"moment_extraction.failed.json")
    second=read(child/"angle_generation.json")
    c1,c2=read(parent/"cost_summary.json"),read(child/"cost_summary.json")
    total=Decimal(str(c1["total_new_cost_usd"]))+Decimal(str(c2["total_new_cost_usd"]))
    same=read(child/"candidates.json")==read(replay/"candidates.json")
    keys=[k for k in (settings.openrouter_moments_key,settings.openrouter_angles_key) if k]
    checked=[]
    for folder in (parent,child,replay):
        checked.extend(folder.rglob("*.json"))
    for artifact in (first,second):
        checked.extend((data/"service_calls"/artifact["request_fingerprint"]/"attempts"/artifact["artifact_id"]).glob("*.json"))
    secret_hits=sum(any(key in path.read_text(encoding="utf-8") for key in keys) for path in checked)
    if secret_hits: raise RuntimeError("Supplied API key appears in an artifact; do not deliver it")
    verify=BACKEND/".storage-artifacts"/"verification"/"strategic-week2-luna-pro"
    preflight=read(verify/"run-preflight.json")
    original=Path(preflight["raw_source_packet"]).parent
    sources=[read(path) for path in (original/"sources").glob("*.json")]
    sources_by_id={s["source_id"]:s for s in sources}
    refs_by_span={t["canonical_span_id"]:t for t in read(original/"reference_map.json").values()}
    moments_by_id={m["moment_id"]:m for m in moments}
    import hashlib
    raw_matches=all(hashlib.sha256((original/"raw"/(s["meeting_ref"]+".original")).read_bytes()).hexdigest()==s["raw_sha256"] for s in sources)
    model_receipts=[{"stage":name,"requested_model":a["model_id"],"returned_model":a["raw_response"].get("model"),
        "provider":a["raw_response"].get("provider"),"finish_reason":a["raw_response"]["choices"][0].get("finish_reason"),
        "usage":a["usage"]} for name,a in (("moment_extraction",first),("angle_generation",second))]
    audit={"parent_run":PARENT,"angle_run":CHILD,"replay_run":REPLAY,"status":"partial",
        "transcript_count":len(sources),"source_turn_count":preflight["turn_count"],
        "extraction_proposals":7,"validated_moments":len(moments),"rejected_moments":2,
        "public_candidates":len(opportunities),"internal_insights":len(insights),
        "purpose_counts":dict(Counter(a["strategic_purpose"] for a in opportunities)),
        "optional_decisions_null":sum(a["reader_decision"] is None for a in opportunities),
        "quality_scores":{a["angle_id"]:a["base_score"] for a in read(child/"candidates.json")},
        "model_receipts":model_receipts,"actual_paid_dispatches":2,"total_reported_cost_usd":float(total),
        "replay_outputs_identical":same,"replay_cost_usd":read(replay/"cost_summary.json")["total_new_cost_usd"],
        "raw_source_hashes_match":raw_matches,"supplied_key_value_hits":secret_hits,"artifact_json_files_scanned":len(checked),
        "parent_remains_failed":read(parent/"manifest.json")["status"]=="failed",
        "human_approved":False,"embedding_requests":0,"model_history_similarity":"not_run",
        "candidate_hash":canonical_hash(read(child/"candidates.json"))}
    if not same or not raw_matches or not audit["parent_remains_failed"]:
        raise RuntimeError("Replay/source/parent status verification failed")
    (verify/"final-test-audit.json").write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding="utf-8")
    lines=["# Week 2 strategic-discovery test: GPT-6 Luna Pro", "", "Recorded 13 October 2026, Asia/Calcutta.", "",
        "Both requested LLM stages executed with exact `openai/gpt-6-luna-pro`, returned provider OpenAI. The revised",
        "`2026-10-13.wia-strategic-discovery.v1` prompts were used. The user explicitly approved both OpenRouter transfers.", "",
        "**Result: partial-pool diagnostic, not a full end-to-end pass.** Extraction returned seven proposed moments from",
        "all eleven Week 2 exports (5,218 turns). Five records passed individual source validation; two quotations failed",
        "exact matching. The ordinary runner stopped. The approved angle call then used only the five valid records",
        "and their original surrounding context, producing four public candidates and one internal sales insight.", "",
        "The failed parent remains failed. No quotation or anchor was repaired, no extraction retry was purchased, and",
        "no similarity ranking, brief generation or publication approval was performed. Source week labels are historical",
        "folder labels; this run date does not establish the recordings' occurrence dates.", "",
        "## Costs and returned usage", "", "| Stage | Input tokens | Completion tokens | Reported new USD |", "|---|---:|---:|---:|"]
    for receipt in model_receipts:
        usage=receipt["usage"]
        lines.append(f"| {receipt['stage']} | {usage['prompt_tokens']:,} | {usage['completion_tokens']:,} | ${usage['cost']:.8f} |")
    lines += ["",f"Total reported inference cost: **${total}**. Cache charges are included in the returned billing; reasoning",
        "is already included in completion usage. Credit-purchase fees are excluded. Actual cache-only replay reproduced",
        "all four candidates with original IDs and lineage, zero provider dispatches and $0 new cost.", "",
        "## Four generated directions", "", "These are the model's working directions, not approved hooks, scripts or service claims.", "",
        "Supporting excerpts below are copied from the original archived transcript turns. Speaker labels and wording",
        "are preserved as exported, including transcription and encoding artifacts. Timestamps show elapsed recording",
        "time. Meeting dates were not supplied in the exports, so recordings are identified by their source filenames.", ""]
    for number,a in enumerate(opportunities,1):
        lines += [f"### {number}. {a['title']}", "",f"**Purpose/type:** {a['strategic_purpose']} · {a['content_type']}", "",
            f"**Audience:** {a['audience']}", "",f"**Opportunity:** {a['content_opportunity']}", "",
            f"**Core perspective:** {a['core_perspective']}", "",f"**WIA expertise shown:** {a['wia_expertise_in_action']}", "",
            f"**Why the model selected it:** {a['selection_reason']}", "",
            f"**Evidence state:** {a['evidence_readiness']} as a proposal/process direction; public permission and current service scope remain subject to review.", "",
            "Evidence/claim limits:", ""]
        lines += [f"- {q}" for q in a["qualifiers"]]
        lines += supporting_source_content(a["moment_ids"],moments_by_id,refs_by_span,sources_by_id)
    lines += ["## Internal sales intelligence", ""]
    for insight in insights:
        lines += [insight["insight"], "",insight["strategic_use"], "", "Source research questions:", ""]
        lines += [f"- {q}" for q in insight["research_questions"]]
        lines += supporting_source_content(insight["moment_ids"],moments_by_id,refs_by_span,sources_by_id)
    lines += ["", "## Extraction failures", "",
        "The budget-discussion quotation `a pretty drastic decline` and capable-owner quotation",
        "`I have my own systems all built out` did not match an anchored cue literally. Searching the same meetings",
        "also found no exact occurrence of either string. The latter source contains a qualified expression with",
        "`I kind of have`, which the generated quotation omitted. The records and their rejection reasons remain intact.", "",
        "The excluded exchanges are still potentially meaningful strategy material. Their technical rejection is not",
        "an editorial assessment that they are weak. It limits the angle pool and the conclusions we can draw.", "",
        "## Assistant assessment against the feedback", "",
        "The revised fields are working: all four records state purpose/type, a core perspective, WIA's actual contribution",
        "and traceable support. All reader decisions are null. The prospect's audit/learning-preference conversation is",
        "kept as internal intelligence rather than automatically turned into public purchasing advice. Team contributions",
        "and proposed work are visible without inventing implementation or outcomes.", "",
        "The buying-research and venue-follow-up directions give the clearest demonstrations of strategic thinking and",
        "collaboration in this small pool. The corporate-campaign direction needs an explicit bridge to the intended wedding",
        "audience and must retain the actual campaign context. The chat-widget direction reveals process thinking, but",
        "does not establish a current client-ready WIA service; its relevance to current offer priorities needs founder judgment.", "",
        "The output is still entirely WARM and uses one public treatment per retained public moment. No ATTRACT or CONVERT",
        "candidate or multiple substantive treatment from one source emerged. This is not grounds to impose a quota, but",
        "it means the feedback's broader discovery capability has not yet been demonstrated. Some working titles and",
        "perspectives remain cautious and technical. Stronger audience stakes and commercial relevance need editorial",
        "assessment; polished hooks alone would not establish improvement.", "",
        "All four pipeline base scores are 80 because their lowest scored dimension is 4. They do not establish a useful",
        "founder-calibrated ordering. Repeated qualifiers remain in the preserved records. The model calls each direction",
        "supported as a process/proposal, which is not publication clearance or evidence of performance.", "",
        "The extraction coverage notes exclude several unresolved or internal exchanges. Their correctness and exhaustive",
        "opportunity recall have not been independently established. Eleven delivery acknowledgements are not proof that",
        "these seven were the strongest opportunities. This run also changes the model and validated pool relative to the",
        "older Week 2 test, so it is not a controlled measurement of the prompt revision alone.", "",
        "The outstanding technical issue is literal quotation fidelity. The next editorial questions are whether Whitney",
        "would develop these directions and whether supported source families offer stronger perspectives across purposes.", "",
        "## Artifacts", "",
        f"- Extraction: `{PARENT}` (failed; received response preserved).",
        f"- Angle generation: `{CHILD}` (partial, validated five-moment pool).",
        f"- Zero-cost replay: `{REPLAY}`.",
        "- Full strategic records: `opportunities.json`; internal research: `internal_insights.json` in the angle run.",
        "- Verification: `.storage-artifacts/verification/strategic-week2-luna-pro/final-test-audit.json`.",
        "- Original requests, raw responses, source archives, cost records and rejected moments remain available.", ""]
    text="\n".join(lines)
    (child/"review.md").write_text(text,encoding="utf-8")
    research=BACKEND.parent/"research"/"week2-luna-pro-strategic-test-review-2026-10-13.md"
    research.write_text(text,encoding="utf-8")
    return {"review":str(research),"angles":len(opportunities),"internal_insights":len(insights),
        "total_new_cost_usd":float(total),"status":"partial","replay_identical":same,"supplied_key_hits":secret_hits}


if __name__=="__main__":
    print(json.dumps(review(),indent=2))
