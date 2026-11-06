"""Explicitly approved two-quote recovery, without changing the sealed experiment."""
from __future__ import annotations

import copy
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from experiments import model_experiment as original
from backend_pipeline.config import BACKEND_ROOT, Settings
from backend_pipeline.models import RunManifest
from backend_pipeline.pipeline import Pipeline
from backend_pipeline.prompts import PROMPT_VERSION, angle_prompt
from backend_pipeline.llm import LiveProvider, chat_body
from backend_pipeline.store import JsonStore, canonical_hash
from backend_pipeline.strategy_contracts import StrategicAngleResponse
from backend_pipeline.weekly import load_compact_week, resolve_moment_references

RECOVERY = "week4-reviewed-quotes-v1"
APPROVED_KEYS = {"m4_google_conversion_correction", "m6_adjacent_search_intent"}
APPROVAL = "Approve reviewed quote recovery and remaining calls"
ADAPTER_FILES = [BACKEND_ROOT / "experiments/reviewed_experiment.py",
                 BACKEND_ROOT / "scripts/run_reviewed_week4.py"]


def home(suite):
    return suite / "recoveries" / RECOVERY


def adapter_identity():
    return {p.name: original.digest(p) for p in ADAPTER_FILES}


def apply_quote_edits(output, edits, reference_map, transcripts):
    """Validate quote-only provenance on a copy; never rewrite a provider response."""
    changed = copy.deepcopy(output)
    by_key = {m["local_key"]: m for m in changed["moments"]}
    spans = {s.span_id: s for t in transcripts for s in t.spans}
    revisions = {t.source_id: t.content_hash for t in transcripts}
    keys = [e["local_key"] for e in edits]
    if len(keys) != len(set(keys)) or not edits:
        raise ValueError("Quote edits must have unique keys")
    for edit in edits:
        if edit["field"] != "quote" or edit["local_key"] not in by_key:
            raise ValueError("Only an existing quote field may be edited")
        draft = by_key[edit["local_key"]]
        ref = edit["source_ref"]
        if ref not in draft["anchor_span_ids"] or ref not in reference_map:
            raise ValueError("Replacement must use an existing anchor")
        span = spans[reference_map[ref]]
        if (edit["canonical_span_id"] != span.span_id or edit["source_turn_text"] != span.text
                or edit["source_revision_sha256"] != revisions[span.source_id]):
            raise ValueError("Edit provenance differs from the frozen original source")
        replacement = edit["proposed_value"]
        if (draft["quote"] != edit["original_value"] or not isinstance(replacement, str)
                or not replacement or replacement not in span.text or replacement == draft["quote"]):
            raise ValueError("Quote edit is not an exact, attributable replacement")
        draft["quote"] = replacement
    return changed


def source_views(suite):
    manifest = original.verify_suite(suite)
    plan = next(p for p in manifest["extractions"] if p["week"] == 4)
    transcripts, packet, refs, _ = load_compact_week(suite / "inputs", 4, JsonStore(home(suite) / "source-view"))
    if hashlib.sha256(packet.encode("utf-8")).hexdigest() != plan["source_packet_sha256"]:
        raise ValueError("Rebuilt source packet differs from the approved extraction")
    return transcripts, refs


def failure_inputs(suite):
    extraction = original.extraction_path(suite, 4)
    plan = original.read(extraction / "plan.json")
    run = extraction / "data/experiments/default/runs" / plan["run_id"]
    paths = {"failed_artifact": run / "moment_extraction.failed.json", "failed_result": extraction / "result.json",
             "failed_manifest": run / "manifest.json", "extraction_started": extraction / "started.json",
             "extraction_dispatch": extraction / "moment_extraction.dispatch.json"}
    artifact = original.read(paths["failed_artifact"])
    raw = artifact["raw_response"]
    if (artifact["status"] != "failed" or original.read(paths["failed_result"])["status"] != "failed"
            or original.read(paths["failed_manifest"])["mode"] != "live"
            or raw.get("model") != original.EXTRACTOR or (run / "moment_extraction.json").exists()):
        raise ValueError("Recovery requires the original failed live Luna extraction")
    raw_files = list((extraction / "data/service_calls").rglob("response.raw.json"))
    if len(raw_files) != 1 or original.read(raw_files[0]) != raw:
        raise ValueError("Failed response does not match its original receipt")
    paths["raw_receipt"] = raw_files[0]
    output = json.loads(raw["choices"][0]["message"]["content"])
    return plan, output, paths


def checked_response(suite, proposal):
    transcripts, refs = source_views(suite)
    plan, output, paths = failure_inputs(suite)
    raw = original.read(paths["raw_receipt"])
    content_hash = hashlib.sha256(raw["choices"][0]["message"]["content"].encode("utf-8")).hexdigest()
    if (proposal["original_content_sha256"] != content_hash or len(output["moments"]) != 17
            or len(proposal["changes"]) != 2
            or {e["local_key"] for e in proposal["changes"]} != APPROVED_KEYS):
        raise ValueError("Recovery differs from the two edits approved by the user")
    checker = object.__new__(Pipeline)
    try:
        checker._parse_moments(resolve_moment_references(output, refs), plan["run_id"], transcripts)
    except ValueError as exc:
        if str(exc) != "Moment quote must match an existing anchor span":
            raise ValueError("Original extraction failed for an unapproved reason") from exc
    else:
        raise ValueError("Recovery is not applicable to an already valid extraction")
    derived = apply_quote_edits(output, proposal["changes"], refs, transcripts)
    moments = checker._parse_moments(resolve_moment_references(derived, refs), f"{plan['run_id']}-reviewed-quotes-v1", transcripts)
    if len(moments) != 17:
        raise ValueError("Whole-response recovery must retain all 17 moments")
    return plan, derived, transcripts, refs, moments, {k: original.digest(p) for k, p in paths.items()}


def prepare_reviewed_recovery(suite: Path, proposal_path: Path, *, approved=False):
    if not approved:
        raise ValueError("Explicit approval for reviewed recovery is required")
    original.verify_suite(suite)
    target = home(suite)
    if target.exists():
        raise ValueError("Recovery already exists; preserve its provenance and execution markers")
    if (suite / "shared/week4/freeze.json").exists() or any(
            (original.cell_path(suite, 4, slug) / "started.json").exists() for slug in original.MODELS):
        raise ValueError("Week 4 angle execution has already begun")
    lock = suite / "active-cell.lock"
    original.exclusive(lock, {"stage": "prepare_reviewed_recovery"})
    try:
        proposal = original.read(proposal_path)
        plan, derived, transcripts, refs, moments, originals = checked_response(suite, proposal)
        pool = {"week": 4, "extractor_model": original.EXTRACTOR, "mode": "live_reviewed",
                "extraction_run_id": plan["run_id"], "evidence_run_id": f"{plan['run_id']}-reviewed-quotes-v1",
                "evidence_origin": "User-approved quote-only derivative of a failed live extraction",
                "reference_map": refs, "transcripts": [t.model_dump(mode="json") for t in transcripts],
                "moments": [m.model_dump(mode="json") for m in moments],
                "moment_packet": Pipeline._moment_packet(moments, transcripts), "coverage_notes": derived["coverage_notes"]}
        store = JsonStore(target)
        store.write_json("approved-proposal.json", proposal)
        store.write_json("derived-response.json", derived)
        store.write_json("edit-log.json", proposal["changes"])
        store.write_json("evidence-packet.json", pool)
        approval = {"origin": "explicit_user_reply", "text": APPROVAL, "recorded_at_utc": datetime.now(UTC).isoformat(),
                    "scope": "Only the two proposed quote edits; all 17 moments; three remaining Week 4 angle calls; no extraction retry"}
        store.write_json("approval.json", approval)
        hashes, capacities, messages = {}, {}, None
        for slug, model in original.MODELS.items():
            system, user = angle_prompt(pool["moment_packet"], [])
            body = chat_body(model=model, system=system, user=user, schema=StrategicAngleResponse.model_json_schema(),
                             reasoning_effort="high", response_format="json_object")
            if messages is not None and body["messages"] != messages:
                raise ValueError("Reviewed angle evidence must be identical across models")
            messages = body["messages"]
            capacities[slug] = original.catalog_check(original.read(suite / f"catalogs/{slug}.json"), body)
            path = original.cell_path(suite, 4, slug) / "prepared-angle.request.json"
            if path.exists():
                raise ValueError("Refusing to overwrite an existing angle preview")
            original.exclusive(path, body)
            hashes[slug] = canonical_hash(body)
        seal = {"baseline_manifest_hash": original.read(suite / "seal.json")["manifest_hash"],
                "adapter_identity": adapter_identity(), "original_failure_hashes": originals,
                "proposal_hash": canonical_hash(proposal), "derived_hash": canonical_hash(derived),
                "approval_hash": canonical_hash(approval), "pool_hash": canonical_hash(pool),
                "edit_log_hash": canonical_hash(proposal["changes"]), "angle_request_hashes": hashes,
                "angle_capacity_checks": capacities}
        original.exclusive(target / "freeze.json", seal)
        original.render_pool_review(pool, target)
        review = target / "review.md"
        review.write_text("> **Reviewed recovery:** The original extraction failed. This is a user-approved derivative changing only two "
                          "quote fields to literal source excerpts. All 17 moments pass the unchanged whole-response parser. "
                          "The original failure and edit log remain preserved. No extraction was repeated.\n\n"
                          + review.read_text(encoding="utf-8"), encoding="utf-8")
        verify_reviewed_pool(suite)
        return {"status": "reviewed_evidence_frozen", "moments": 17, "new_calls": 0, "pool_hash": seal["pool_hash"]}
    finally:
        lock.unlink()


def verify_reviewed_pool(suite):
    original.verify_suite(suite)
    target = home(suite)
    seal = original.read(target / "freeze.json")
    if (seal["adapter_identity"] != adapter_identity()
            or seal["baseline_manifest_hash"] != original.read(suite / "seal.json")["manifest_hash"]):
        raise ValueError("Reviewed recovery code or baseline identity changed")
    proposal = original.read(target / "approved-proposal.json")
    approval = original.read(target / "approval.json")
    if (canonical_hash(proposal) != seal["proposal_hash"] or canonical_hash(approval) != seal["approval_hash"]
            or approval["text"] != APPROVAL or canonical_hash(original.read(target / "edit-log.json")) != seal["edit_log_hash"]):
        raise ValueError("Approved quote edits or authorization changed")
    plan, derived, transcripts, refs, moments, originals = checked_response(suite, proposal)
    if originals != seal["original_failure_hashes"]:
        raise ValueError("Original failed extraction or receipt changed")
    if canonical_hash(derived) != seal["derived_hash"] or original.read(target / "derived-response.json") != derived:
        raise ValueError("Reviewed response differs from the exact approved quote edits")
    pool = original.read(target / "evidence-packet.json")
    expected = {"week": 4, "extractor_model": original.EXTRACTOR, "mode": "live_reviewed",
                "extraction_run_id": plan["run_id"], "evidence_run_id": f"{plan['run_id']}-reviewed-quotes-v1",
                "evidence_origin": "User-approved quote-only derivative of a failed live extraction",
                "reference_map": refs, "transcripts": [t.model_dump(mode="json") for t in transcripts],
                "moments": [m.model_dump(mode="json") for m in moments],
                "moment_packet": Pipeline._moment_packet(moments, transcripts), "coverage_notes": derived["coverage_notes"]}
    if pool != expected or canonical_hash(pool) != seal["pool_hash"]:
        raise ValueError("Reviewed evidence differs from original source and approved edits")
    for slug, expected_hash in seal["angle_request_hashes"].items():
        if canonical_hash(original.read(original.cell_path(suite, 4, slug) / "prepared-angle.request.json")) != expected_hash:
            raise ValueError("Reviewed angle request changed after evidence freeze")
    return pool, seal


class ReviewedAngleProvider(original.ExactModelProvider):
    def json_call(self, *, stage, system, user, schema, fingerprint):
        if stage != "angle_generation":
            raise ValueError("Reviewed recovery may not repeat extraction")
        manifest = original.verify_suite(self.suite)
        pool, seal = verify_reviewed_pool(self.suite)
        plan = original.read(self.cell / "plan.json")
        if plan not in manifest["cells"] or plan["week"] != 4:
            raise ValueError("Only the three prepared Week 4 angle calls are authorized")
        body = chat_body(model=plan["model"], system=system, user=user, schema=schema,
                         reasoning_effort="high", response_format="json_object")
        catalog = original.read(self.suite / f"catalogs/{plan['slug']}.json")
        if (canonical_hash(catalog) != plan["catalog_hash"] or self.llm_base_url != manifest["endpoint"].rstrip("/")
                or canonical_hash(body) != seal["angle_request_hashes"][plan["slug"]] or pool["mode"] != "live_reviewed"):
            raise ValueError("Reviewed angle request or route differs from its frozen plan")
        capacity = original.catalog_check(catalog, body)
        original.exclusive(self.cell / "angle_generation.dispatch.json", {"request_hash": canonical_hash(body),
                           "pool_hash": seal["pool_hash"], "evidence_origin": pool["evidence_origin"], "capacity_check": capacity})
        result, receipt = LiveProvider.json_call(self, stage=stage, system=system, user=user, schema=schema, fingerprint=fingerprint)
        if receipt["raw"].get("model") != plan["model"]:
            raise ValueError("Returned model differs from exact requested route")
        return result, receipt


def run_reviewed_cell(base: Settings, suite: Path, slug: str, *, live=False):
    if not live:
        raise ValueError("Explicit --live is required for the approved remaining call")
    manifest = original.verify_suite(suite)
    pool, seal = verify_reviewed_pool(suite)
    cell = original.cell_path(suite, 4, slug)
    plan = next(p for p in manifest["cells"] if p["week"] == 4 and p["slug"] == slug)
    if original.read(cell / "plan.json") != plan:
        raise ValueError("Cell differs from its sealed plan")
    settings = original.cell_settings(base, suite, 4, slug)
    settings.validate_live()
    if settings.openrouter_base_url != manifest["endpoint"] or settings.request_timeout_seconds != plan["timeout_seconds"]:
        raise ValueError("Execution endpoint or timeout differs from prepared setup")
    if any((settings.data_root / "cache/artifacts").glob("*.json")):
        raise ValueError("Reviewed comparison cells may not reuse generated outputs")
    lock = suite / "active-cell.lock"
    original.exclusive(lock, {"week": 4, "slug": slug, "evidence_origin": pool["evidence_origin"]})
    try:
        original.exclusive(cell / "started.json", {"mode": "live", "run_id": plan["run_id"], "recovery": RECOVERY})
        pipeline = Pipeline(settings)
        pipeline._provider_override = ReviewedAngleProvider(settings, suite, cell, pipeline._save_raw_response)
        # The sealed experiment sends only the approved requests; a repair call is another request (0.B4).
        pipeline.calls.repair_invalid = False
        pipeline._select_provider("live")
        from backend_pipeline.models import Moment
        moments = [Moment.model_validate(m) for m in pool["moments"]]
        run = RunManifest(run_id=plan["run_id"], week_index=4, source_root=str(settings.transcript_root),
                          source_ids=[t["source_id"] for t in pool["transcripts"]], prompt_profile=PROMPT_VERSION,
                          model_id=plan["model"], embedding_profile="disabled", mode="live", execution_scope="generation_only",
                          parent_run_id=pool["evidence_run_id"])
        run_dir = f"experiments/default/runs/{run.run_id}"
        pipeline.store.write_model(f"{run_dir}/manifest.json", run)
        lineage = {"recovery": RECOVERY, "pool_hash": seal["pool_hash"], "evidence_origin": pool["evidence_origin"],
                   "original_failed_extraction_run_id": pool["extraction_run_id"], "extraction_repeated": False,
                   "approved_edits": original.read(home(suite) / "edit-log.json")}
        pipeline.store.write_json(f"{run_dir}/reviewed-evidence.json", lineage)
        try:
            system, user = angle_prompt(pool["moment_packet"], [])
            artifact = pipeline._call_json("angle_generation", run, run_dir, system, user,
                canonical_hash({"system": system, "user": user, "pool_hash": seal["pool_hash"]}),
                StrategicAngleResponse.model_json_schema(),
                validate=lambda out: pipeline._parse_angles(out, run.run_id, moments))
            angles = pipeline._parse_angles(artifact.output, run.run_id, moments, artifact=artifact)
            pipeline.store.write_json(f"{run_dir}/moments.json", pool["moments"])
            pipeline.store.write_json("cycles/week4/sources.json", {"transcripts": pool["transcripts"]})
            pipeline.store.write_json(f"{run_dir}/candidates.json", [a.model_dump(mode="json") for a in angles])
            pipeline._write_discovery_outputs(run_dir, artifact.output, angles)
        except Exception as exc:
            run.status = "failed"
            pipeline.store.write_model(f"{run_dir}/manifest.json", run, overwrite=True)
            original.write(cell / "result.json", {"status": "failed", "error_type": type(exc).__name__, "error": str(exc), **lineage})
            raise
        result = {"run_id": run.run_id, "week_index": 4, "stage": "angle_generation", "moments": len(moments),
                  "angles": len(angles), "pool_hash": seal["pool_hash"], "embedding_requests": 0,
                  "similarity_status": "not_run", "evidence_origin": pool["evidence_origin"], "recovery": RECOVERY}
        run.status = "generation_completed"
        pipeline.store.write_model(f"{run_dir}/manifest.json", run, overwrite=True)
        original.write(cell / "result.json", {"status": "completed", **result})
        review = original.render_review(suite, cell, result)
        review.write_text("> **Evidence provenance:** All three Week 4 models use the same user-approved, two-quote derivative of "
                          "the failed Luna extraction. No extraction was repeated; the original failure remains preserved.\n\n"
                          + review.read_text(encoding="utf-8"), encoding="utf-8")
        return result
    finally:
        lock.unlink()
