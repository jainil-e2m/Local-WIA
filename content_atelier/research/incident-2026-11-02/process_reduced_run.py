"""Offline request reconstruction and evidence-containment analysis; no model or production access."""
from __future__ import annotations
import copy
import hashlib
import json
import socket
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / "reduced-run-preview"
sys.path.insert(0, str(ROOT / "backend"))

from backend_pipeline.angle_profiles import order_packet, strategist_user, scene_references, _handling
from backend_pipeline.cycle.seeds import prompt_seeds
from backend_pipeline.models import Moment
from backend_pipeline.pipeline import Pipeline
from backend_pipeline.sql_pipeline import consented
from backend_pipeline.storage_sources import reconstruct
from backend_pipeline.store import JsonStore
from backend_pipeline.token_budget import preflight


def write(name, obj):
    (OUT / name).write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load():
    snapshot = json.loads((OUT / "production-snapshot.json").read_text(encoding="utf-8"))
    request_path = next(p for p in snapshot["artifacts"] if p.endswith("/request.json"))
    request = json.loads((OUT / "artifacts" / request_path).read_text(encoding="utf-8"))["request"]
    refs = snapshot["run"]["input_refs"]
    records = {r["transcript_id"]: dict(r) for r in snapshot["transcripts"]}
    for row in records.values():
        if row.get("occurred_at"):
            row["occurred_at"] = datetime.fromisoformat(row["occurred_at"])
    transcripts, _, _ = reconstruct([records[t["id"]] for t in refs["transcripts"]])
    extraction = next(j for j in snapshot["jobs"] if j["stage"] == "moment_extraction")
    ids = extraction["result_refs"]["moment_ids"]
    rows = {r["moment_id"]: r for r in snapshot["moments"]}
    bodies, dropped = consented(rows, ids)
    spans = {s.span_id: s for t in transcripts for s in t.spans}
    moments = []
    for mid in ids:
        if mid not in bodies:
            continue
        evidence = rows[mid]["evidence_refs"]
        context = [r["passage_id"] for r in evidence if "context" in r["roles"]]
        anchors = [r["passage_id"] for r in evidence if "anchor" in r["roles"]]
        moments.append(Moment(moment_id=mid, source_ids=sorted({spans[a].source_id for a in anchors}),
                              anchor_span_ids=anchors, context_span_ids=context, **bodies[mid]))
    packet = order_packet(Pipeline._moment_packet(moments, transcripts))
    team = {mid for mid in ids if rows[mid]["evidence_class"] == "team_practice"} if refs.get("identities") is not None else set()
    def render(p):
        return strategist_user(p, refs["angle_prompt_profile"], prompt_seeds(refs.get("seeds") or []), refs.get("strategy_brief"),
                               team_practice=team, identities=refs.get("identities"))
    rendered = render(packet)
    user_index = next(i for i, m in enumerate(request["messages"]) if m["role"] == "user")
    original_user = request["messages"][user_index]["content"]
    if not original_user.startswith(rendered):
        i = next((i for i, (a,b) in enumerate(zip(original_user, rendered)) if a != b), min(len(original_user), len(rendered)))
        raise AssertionError(f"Frozen prompt did not reconstruct exactly: mismatch at {i}, lengths {len(original_user)}/{len(rendered)}")
    suffix = original_user[len(rendered):]
    return snapshot, request, ids, rows, packet, render, user_index, suffix, dropped


def main():
    # The entire processing phase is offline, including all library helpers.
    def forbidden(*a, **k):
        raise AssertionError("Offline processing forbids network access")
    socket.socket = forbidden
    snapshot, request, ids, rows, packet, render, ui, suffix, dropped = load()
    store = JsonStore(OUT / "artifacts")
    original_report = preflight(request, store)
    refs = scene_references(packet)
    inverse = {mid: ref for ref, mid in refs.items()}
    sizes = {m["moment_id"]: len(render([m]).encode()) - len(render([]).encode()) for m in packet}
    protected = {"human_line", "counter_expected_decision", "team_practice", "decision", "result", "objection", "tension", "story", "testimonial", "soundbite"}
    contexts = {m["moment_id"]: set(m["context_span_ids"]) for m in packet}
    anchors = {m["moment_id"]: set(m["anchor_span_ids"]) for m in packet}
    qualified = {}
    for a in packet:
        mid = a["moment_id"]
        if a["moment_type"] in protected:
            continue
        others = []
        for b in packet:
            bid = b["moment_id"]
            if bid == mid or rows[bid]["document_id"] != rows[mid]["document_id"]:
                continue
            if contexts[mid] <= contexts[bid] and _handling(a) == _handling(b):
                others.append(bid)
        if others:
            qualified[mid] = others
    by_id = {m["moment_id"]: m for m in packet}
    selected = set(ids) - {d["moment_id"] for d in dropped}
    removed = []
    retained_as_cover = set()
    report = original_report
    for mid in sorted(qualified, key=lambda x: (-sizes[x], x)):
        if report["input_token_budget_allowance"] <= 818000:
            break
        if mid in retained_as_cover:
            continue
        covers = [b for b in qualified[mid] if b in selected]
        if not covers:
            continue
        # Prefer keeping a protected scene, then the largest context and stable ID.
        covering = min(covers, key=lambda x: (by_id[x]["moment_type"] not in protected, -len(contexts[x]), x))
        selected.remove(mid)
        retained_as_cover.add(covering)
        reduced = copy.deepcopy(request)
        reduced["messages"][ui]["content"] = render([m for m in packet if m["moment_id"] in selected]) + suffix
        current = preflight(reduced, store)
        row = rows[mid]
        removed.append({"moment_id": mid, "original_scene_ref": inverse[mid], "document_id": row["document_id"],
                        "type": by_id[mid]["moment_type"], "context_summary": row["moment_body"]["context_summary"],
                        "quote": row["moment_body"]["quote"], "covering_moment_id": covering,
                        "covering_original_scene_ref": inverse[covering],
                        "covering_context_summary": rows[covering]["moment_body"]["context_summary"],
                        "context_spans": len(contexts[mid]), "covering_context_spans": len(contexts[covering]),
                        "anchors_retained": anchors[mid] <= contexts[covering],
                        "actual_bytes_saved_this_step": report["input_token_budget_allowance"] - current["input_token_budget_allowance"],
                        "reason": "Every original dialogue span, including all anchors, occurs in one retained scene of the same document; handling and qualifications are identical."})
        report = current
    if not report["fits"]:
        write("strict-containment-insufficient.json", {"strict_candidates": len(qualified), "removed": removed, "preflight": report})
        alternatives = []
        for a in packet:
            mid = a["moment_id"]
            if a["moment_type"] in protected:
                continue
            for b in packet:
                bid = b["moment_id"]
                if mid != bid and rows[mid]["document_id"] == rows[bid]["document_id"] and contexts[mid] <= contexts[bid]:
                    alternatives.append({"moment_id": mid, "ref": inverse[mid], "type": a["moment_type"], "bytes": sizes[mid],
                                         "covered_by": bid, "covered_by_ref": inverse[bid], "covering_type": b["moment_type"],
                                         "handling": _handling(a), "covering_handling": _handling(b),
                                         "summary": a["context_summary"], "covering_summary": b["context_summary"]})
        write("containment-review-candidates.json", sorted(alternatives, key=lambda a: -a["bytes"]))
        print(json.dumps({"strict_candidates": len(qualified), "removed_count": len(removed), "allowance": report["input_token_budget_allowance"], "alternative_pairs": len(alternatives)}))
        # This negative finding is an analysis result, not a reason to auto-cut unique evidence.
        return
    selected_ids = [mid for mid in ids if mid in selected]
    assert len(selected_ids) + len(removed) + len(dropped) == len(ids)
    before_context = set().union(*(contexts[mid] for mid in ids if mid in contexts))
    after_context = set().union(*(contexts[mid] for mid in selected_ids))
    assert before_context == after_context, "Unique dialogue would be lost"
    assert all(r["covering_moment_id"] in selected for r in removed)
    before_docs = Counter(rows[mid]["document_id"] for mid in ids)
    after_docs = Counter(rows[mid]["document_id"] for mid in selected_ids)
    assert set(before_docs) == set(after_docs)
    new_refs = {mid: ref for ref, mid in scene_references([m for m in packet if m["moment_id"] in selected]).items()}
    summary = {"run_id": snapshot["run"]["run_id"], "snapshot_fetched_at": snapshot["fetched_at"],
               "proposal_only": True, "production_changes": False, "model_calls": 0,
               "original_verified": len(ids), "selected": len(selected_ids), "omitted": len(removed),
               "consent_dropped": dropped, "strict_containment_candidates": len(qualified),
               "unique_context_spans_before": len(before_context), "unique_context_spans_after": len(after_context),
               "original_preflight": original_report, "reduced_preflight": report,
               "byte_reduction": original_report["input_token_budget_allowance"] - report["input_token_budget_allowance"],
               "original_prompt_reconstructed_exactly": True, "unchanged_situational_suffix_characters": len(suffix),
               "protected_types": sorted(protected), "selected_ids": selected_ids, "omissions": removed,
               "documents": [{"document_id": d, "title": next(t["title"] for t in snapshot["transcripts"] if t["transcript_id"] == d),
                              "original": before_docs[d], "selected": after_docs[d]} for d in before_docs],
               "reference_mapping": [{"moment_id": mid, "original_ref": inverse[mid], "new_ref": new_refs.get(mid)} for mid in ids]}
    write("selection-proposal.json", summary)
    write("original-preflight.json", original_report)
    write("reduced-preflight.json", report)
    write("reduced-request.json", reduced)
    write("original-extraction-job.json", next(j for j in snapshot["jobs"] if j["stage"] == "moment_extraction"))
    write("all-containment-candidates.json", [{"moment_id": mid, "original_ref": inverse[mid], "approximate_bytes": sizes[mid],
                                             "type": by_id[mid]["moment_type"], "covered_by": qualified[mid]} for mid in qualified])
    lines = ["# Local selection preview — no production changes", "", f"Verified scenes: {len(ids)} → {len(selected_ids)}; omitted scene blocks: {len(removed)}.",
             f"Unique original dialogue spans: {len(before_context)} → {len(after_context)}. All 16 documents retained.", "",
             "Each omitted block's complete dialogue and anchors occur in a retained block of the same document, with identical handling and qualifications.",
             "Human lines, counter-expected decisions, team-practice scenes, decisions, results, objections, tensions, stories, testimonials and soundbites are protected.", ""]
    for r in removed:
        lines += [f"## {r['original_scene_ref']} — {r['moment_id']}", f"Type: {r['type']}; covered by {r['covering_original_scene_ref']} ({r['covering_moment_id']}).",
                  f"Bytes saved: {r['actual_bytes_saved_this_step']}; dialogue spans {r['context_spans']}, all inside retained block of {r['covering_context_spans']} spans.",
                  "", "Omitted scene summary: " + r["context_summary"], "", "Retained scene summary: " + r["covering_context_summary"], "",
                  "Omitted scene anchor quote: " + r["quote"], ""]
    (OUT / "selection-review.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({k: summary[k] for k in ("original_verified", "selected", "omitted", "strict_containment_candidates", "byte_reduction", "unique_context_spans_before", "unique_context_spans_after")}, indent=2))
    print(json.dumps({"original_allowance": original_report["input_token_budget_allowance"], "reduced_allowance": report["input_token_budget_allowance"],
                      "with_margin": report["input_token_budget_allowance"] + report["unmeasured_provider_margin_tokens"], "fits": report["fits"]}, indent=2))


if __name__ == "__main__":
    main()
