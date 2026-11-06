"""One shared Luna extraction per week; isolated angle comparisons on frozen evidence."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .config import BACKEND_ROOT, Settings
from .models import Moment, RunManifest, Transcript
from .pipeline import Pipeline
from .prompts import PROMPT_VERSION, angle_prompt, weekly_moment_prompt
from .provider import LiveProvider, chat_body
from .store import JsonStore, canonical_hash
from .strategy_contracts import StrategicAngleResponse, StrategicCompactMomentResponse
from .weekly import meeting_inventory, resolve_moment_references

MODELS = {
    "luna-pro": "openai/gpt-6-luna-pro",
    "sol": "openai/gpt-6.1-sol",
    "sonnet": "anthropic/claude-sonnet-5.5",
}
WEEKS = (3, 4)
SUITE = "week3-week4-shared-luna-angle-quality-20261015"
EXTRACTOR = MODELS["luna-pro"]
RUNTIME_FILES = [
    "model_experiment.py", "config.py", "pipeline.py", "provider.py", "prompts.py", "weekly.py", "prepare.py",
    "strategy_contracts.py", "contracts.py", "models.py", "store.py", "costs.py",
    *[f"prompt_templates/{name}.md" for name in (
        "moment_extraction.system", "wia_strategy", "editorial_policy", "moment_extraction.weekly_v3",
        "angle_generation.system", "angle_generation.user",
    )],
]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def runtime_identity() -> dict:
    return {name: digest(BACKEND_ROOT / "backend_pipeline" / name) for name in RUNTIME_FILES}


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value) -> None:
    JsonStore(path.parent).write_json(path.name, value, overwrite=True)


def exclusive(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)


def cell_path(suite: Path, week: int, slug: str) -> Path:
    if week not in WEEKS or slug not in MODELS:
        raise ValueError("Only the six prepared week/model combinations are permitted")
    return suite / "cells" / f"week{week}" / slug


def extraction_path(suite: Path, week: int) -> Path:
    if week not in WEEKS:
        raise ValueError("Only prepared weeks are permitted")
    return suite / "extractions" / f"week{week}"


def cell_settings(base: Settings, suite: Path, week: int, slug: str) -> Settings:
    return base.model_copy(update={
        "data_root": cell_path(suite, week, slug) / "data", "transcript_root": suite / "inputs",
        "openrouter_moments_model": EXTRACTOR, "openrouter_angles_model": MODELS[slug],
        "llm_payload_format": "compact_weekly", "llm_reasoning_effort": "high", "llm_response_format": "json_object",
        "llm_completion_tokens": None, "llm_input_limits_enabled": False,
        "embeddings_enabled": False, "live_enabled": True,
    })


def extraction_settings(base: Settings, suite: Path, week: int) -> Settings:
    return cell_settings(base, suite, week, "luna-pro").model_copy(update={
        "data_root": extraction_path(suite, week) / "data", "openrouter_angles_model": EXTRACTOR})


def catalog_check(catalog: dict, body: dict) -> dict:
    """Conservative byte allowance, explicitly not a native token count."""
    if not catalog.get("exact_route_found") or catalog.get("advertised_id") != body["model"]:
        raise ValueError("Exact requested model route has not been verified")
    endpoints = [e for e in catalog["endpoints"]
                 if {"reasoning", "response_format"} <= set(e["supported_parameters"])]
    if not endpoints:
        raise ValueError("No advertised endpoint supports the requested reasoning and response format")
    allowance = sum(len(m["content"].encode("utf-8")) for m in body["messages"])
    allowance += len(json.dumps(body["response_format"]).encode("utf-8"))
    margin = max(4096, (allowance + 9) // 10)
    eligible = [e for e in endpoints if e.get("context_length") and e.get("max_completion_tokens")
                and allowance + margin <= (e.get("max_prompt_tokens") or e["context_length"])
                and allowance + margin + e["max_completion_tokens"] <= e["context_length"]]
    if len(eligible) != len(endpoints):
        raise ValueError("Whole request exceeds the conservative route allowance; no trimming or dispatch permitted")
    return {"method": "conservative_utf8_byte_allowance_not_native_token_count", "input_allowance": allowance,
            "margin": margin, "advertised_eligible_endpoints": len(eligible),
            "output_reserve": max(e["max_completion_tokens"] for e in eligible),
            "request_has_explicit_output_cap": False, "fits_conservative_allowance": True,
            "provider_defaults_and_limits_still_apply": True}


def prepare_suite(base: Settings, suite: Path, catalogs: Path) -> dict:
    if suite.exists():
        raise ValueError("Suite already exists; preserve it and its frozen approval inputs")
    suite.mkdir(parents=True)
    store = JsonStore(suite)
    sources = []
    for week in WEEKS:
        origin = base.transcript_root / f"week{week}"
        paths = sorted(p for p in origin.rglob("*") if p.is_file() and p.suffix.lower() in {".txt", ".vtt", ".webvtt"})
        if not paths:
            raise ValueError(f"Week {week} contains no transcript sources")
        for path in paths:
            relative = Path("inputs") / f"week{week}" / path.relative_to(origin)
            raw = path.read_bytes()
            store.write_bytes(relative.as_posix(), raw)
            if path.read_bytes() != raw:
                raise ValueError("Source changed during snapshot capture")
            sources.append({"week": week, "origin": path.as_posix(), "snapshot": relative.as_posix(),
                            "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)})
    schemas = {"moment_extraction": StrategicCompactMomentResponse.model_json_schema(),
               "angle_generation": StrategicAngleResponse.model_json_schema()}
    for stage, schema in schemas.items():
        store.write_json(f"schemas/{stage}.json", schema)
    for slug, model in MODELS.items():
        catalog = read(catalogs / slug / "model-check.json")
        if not catalog.get("exact_route_found") or catalog.get("advertised_id") != model:
            raise ValueError("Exact requested model route has not been verified")
        store.write_json(f"catalogs/{slug}.json", catalog)
    cells, extractions = [], []
    for week in WEEKS:
        settings = extraction_settings(base, suite, week)
        pipeline = Pipeline(settings)
        transcripts, packet = pipeline.load_week(week)
        system, user = weekly_moment_prompt(packet, meeting_inventory(pipeline._compact_refs))
        body = chat_body(model=EXTRACTOR, system=system, user=user, schema=schemas["moment_extraction"],
                         reasoning_effort="high", response_format="json_object")
        catalog = read(suite / "catalogs/luna-pro.json")
        entry = {"stage": "moment_extraction", "week": week, "slug": "luna-pro", "model": EXTRACTOR,
                 "reasoning_effort": "high", "run_id": f"{SUITE}-w{week}-shared-extraction",
                 "source_count": len(transcripts), "source_turns": sum(len(t.spans) for t in transcripts),
                 "source_packet_sha256": hashlib.sha256(packet.encode("utf-8")).hexdigest(),
                 "request_hash": canonical_hash(body), "request_characters": len(json.dumps(body, ensure_ascii=False)),
                 "catalog_hash": canonical_hash(catalog), "capacity_check": catalog_check(catalog, body),
                 "timeout_seconds": settings.request_timeout_seconds}
        write(extraction_path(suite, week) / "prepared-extraction.request.json", body)
        write(extraction_path(suite, week) / "plan.json", entry)
        extractions.append(entry)
        for slug, model in MODELS.items():
            cell = cell_path(suite, week, slug)
            angle_system, _ = angle_prompt([], [])
            write(cell / "prepared-angle-system.json", {"system": angle_system, "pool_status": "pending_shared_extraction"})
            entry = {"stage": "angle_generation", "week": week, "slug": slug, "model": model, "reasoning_effort": "high",
                     "run_id": f"{SUITE}-w{week}-{slug}", "source_count": len(transcripts),
                     "source_turns": sum(len(t.spans) for t in transcripts),
                     "source_packet_sha256": extractions[-1]["source_packet_sha256"],
                     "catalog_hash": canonical_hash(read(suite / f"catalogs/{slug}.json")),
                     "timeout_seconds": settings.request_timeout_seconds,
                     "angle_request_status": "Built from the same frozen shared Luna evidence as the other angle models"}
            write(cell / "plan.json", entry)
            cells.append(entry)
    manifest = {"suite": SUITE, "status": "prepared_awaiting_user_approval", "sources": sources, "cells": cells,
                "extractions": extractions, "extractor_model": EXTRACTOR,
                "runtime_identity": runtime_identity(), "schema_hashes": {k: canonical_hash(v) for k, v in schemas.items()},
                "endpoint": base.openrouter_base_url, "max_paid_calls": 8, "calls_per_cell": 1,
                "execution_order": [item for w in WEEKS for item in [f"week{w}/extract-luna", *[f"week{w}/angles-{slug}" for slug in MODELS]]],
                "history_supplied": False, "embeddings": False, "matching": False, "refinement": False,
                "auto_retries": False, "partial_acceptance": False, "forced_angle_count": None,
                "paid_calls_during_preparation": 0}
    store.write_json("suite.json", manifest)
    store.write_json("seal.json", {"manifest_hash": canonical_hash(manifest)})
    return manifest


def verify_suite(suite: Path) -> dict:
    manifest = read(suite / "suite.json")
    if canonical_hash(manifest) != read(suite / "seal.json")["manifest_hash"]:
        raise ValueError("Prepared suite changed; approval inputs must be reviewed again")
    if runtime_identity() != manifest["runtime_identity"]:
        raise ValueError("Prompt or engine files changed after preparation")
    for source in manifest["sources"]:
        if digest(suite / source["snapshot"]) != source["sha256"]:
            raise ValueError("Frozen source changed after preparation")
    for stage, contract in (("moment_extraction", StrategicCompactMomentResponse), ("angle_generation", StrategicAngleResponse)):
        if canonical_hash(contract.model_json_schema()) != manifest["schema_hashes"][stage]:
            raise ValueError("Active schema changed after preparation")
    return manifest


class ExactModelProvider(LiveProvider):
    def __init__(self, settings: Settings, suite: Path, cell: Path, on_response):
        super().__init__(llm_base_url=settings.openrouter_base_url, moments_model=settings.openrouter_moments_model,
            angles_model=settings.openrouter_angles_model, moments_key=settings.openrouter_moments_key,
            angles_key=settings.openrouter_angles_key, embedding_base_url=settings.embedding_base_url,
            embedding_model=settings.embedding_model, embedding_key=None, dimensions=settings.embedding_dimensions,
            timeout=settings.request_timeout_seconds, max_tokens=None, reasoning_effort="high",
            response_format="json_object", on_response=on_response)
        self.suite, self.cell = suite, cell

    def json_call(self, *, stage, system, user, schema, fingerprint):
        manifest = verify_suite(self.suite)
        plan = read(self.cell / "plan.json")
        if plan not in manifest["cells"] + manifest["extractions"] or stage != plan["stage"]:
            raise ValueError("Cell plan differs from the sealed suite")
        body = chat_body(model=plan["model"], system=system, user=user, schema=schema,
                         reasoning_effort="high", response_format="json_object")
        catalog = read(self.suite / "catalogs" / f"{plan['slug']}.json")
        if canonical_hash(catalog) != plan["catalog_hash"] or self.llm_base_url != manifest["endpoint"].rstrip("/"):
            raise ValueError("Prepared route configuration changed")
        budget = catalog_check(catalog, body)
        if stage == "moment_extraction" and canonical_hash(body) != plan["request_hash"]:
            raise ValueError("Extraction request differs from the approved preview")
        if stage == "angle_generation":
            pool, seal = verify_pool(self.suite, plan["week"])
            if pool["mode"] != "live":
                raise ValueError("Synthetic extraction evidence cannot be used for live angle generation")
            if canonical_hash(body) != seal["angle_request_hashes"][plan["slug"]]:
                raise ValueError("Angle request differs from the frozen shared evidence")
        exclusive(self.cell / f"{stage}.dispatch.json", {"request_hash": canonical_hash(body), "capacity_check": budget})
        result, receipt = super().json_call(stage=stage, system=system, user=user, schema=schema, fingerprint=fingerprint)
        if receipt["raw"].get("model") != plan["model"]:
            raise ValueError("Returned model differs from the exact requested model; raw response preserved")
        return result, receipt

    def embed(self, **kwargs):
        raise RuntimeError("Embeddings are prohibited in this comparison")


def verify_pool(suite: Path, week: int) -> tuple[dict, dict]:
    verify_suite(suite)
    home = suite / "shared" / f"week{week}"
    if not (home / "freeze.json").exists():
        raise ValueError("Shared extraction must pass whole-response validation and be frozen before angles")
    pool, seal = read(home / "evidence-packet.json"), read(home / "freeze.json")
    if canonical_hash(pool) != seal["pool_hash"]:
        raise ValueError("Frozen evidence packet changed")
    artifact = read(extraction_path(suite, week) / "data" / "experiments/default/runs"
                    / pool["extraction_run_id"] / "moment_extraction.json")
    if artifact["status"] != "validated" or canonical_hash(artifact["output"]) != pool["extraction_output_hash"]:
        raise ValueError("Shared evidence differs from the original validated extraction")
    transcripts = [Transcript.model_validate(t) for t in pool["transcripts"]]
    checker = Pipeline(Settings(data_root=home / "validation-only"))
    validated = checker._parse_moments(resolve_moment_references(artifact["output"], pool["reference_map"]),
                                      pool["extraction_run_id"], transcripts)
    if [m.model_dump(mode="json") for m in validated] != pool["moments"]:
        raise ValueError("Frozen moments differ from normal extraction resolution")
    if checker._moment_packet(validated, transcripts) != pool["moment_packet"]:
        raise ValueError("Frozen angle inputs differ from original supporting evidence")
    for slug, expected in seal["angle_request_hashes"].items():
        if canonical_hash(read(cell_path(suite, week, slug) / "prepared-angle.request.json")) != expected:
            raise ValueError("Prepared angle request changed after evidence freeze")
    return pool, seal


def freeze_pool(suite: Path, week: int, pipeline: Pipeline, run: RunManifest,
                transcripts, moments, artifact) -> dict:
    home = suite / "shared" / f"week{week}"
    pool = {"week": week, "extractor_model": EXTRACTOR, "mode": run.mode, "extraction_run_id": run.run_id,
            "extraction_output_hash": canonical_hash(artifact.output), "reference_map": pipeline._compact_refs,
            "transcripts": [t.model_dump(mode="json") for t in transcripts],
            "moments": [m.model_dump(mode="json") for m in moments],
            "moment_packet": pipeline._moment_packet(moments, transcripts),
            "coverage_notes": artifact.output["coverage_notes"]}
    # Preserve the validated pool even if a later angle-size check needs attention.
    JsonStore(home).write_json("evidence-packet.json", pool)
    hashes, capacities, messages = {}, {}, None
    for slug, model in MODELS.items():
        system, user = angle_prompt(pool["moment_packet"], [])
        body = chat_body(model=model, system=system, user=user, schema=StrategicAngleResponse.model_json_schema(),
                         reasoning_effort="high", response_format="json_object")
        if messages is not None and messages != body["messages"]:
            raise ValueError("Angle models did not receive identical instructions and frozen evidence")
        messages = body["messages"]
        capacities[slug] = catalog_check(read(suite / f"catalogs/{slug}.json"), body)
        JsonStore(cell_path(suite, week, slug)).write_json("prepared-angle.request.json", body)
        hashes[slug] = canonical_hash(body)
    seal = {"pool_hash": canonical_hash(pool), "angle_request_hashes": hashes, "angle_capacity_checks": capacities}
    JsonStore(home).write_json("freeze.json", seal)
    render_pool_review(pool, home)
    return seal


def run_extraction(base: Settings, suite: Path, week: int, *, live=False, provider=None) -> dict:
    return _run_stage(base, suite, week, "luna-pro", "moment_extraction", live=live, provider=provider)


def run_cell(base: Settings, suite: Path, week: int, slug: str, *, live=False, provider=None) -> dict:
    """An angle-only call on shared evidence; provider injection is only for offline tests."""
    return _run_stage(base, suite, week, slug, "angle_generation", live=live, provider=provider)


def _run_stage(base, suite, week, slug, stage, *, live, provider):
    manifest = verify_suite(suite)
    if not live and provider is None:
        raise ValueError("Explicit --live is required after user approval")
    extraction = stage == "moment_extraction"
    pool, seal = (None, None) if extraction else verify_pool(suite, week)
    if pool is not None and (not pool["moments"] or live and pool["mode"] != "live"):
        raise ValueError("Live angles require nonempty, validated live extraction evidence")
    cell = extraction_path(suite, week) if extraction else cell_path(suite, week, slug)
    plans = manifest["extractions"] if extraction else manifest["cells"]
    plan = next(c for c in plans if c["week"] == week and c["slug"] == slug)
    if read(cell / "plan.json") != plan:
        raise ValueError("Cell plan differs from the sealed suite")
    settings = extraction_settings(base, suite, week) if extraction else cell_settings(base, suite, week, slug)
    if live:
        settings.validate_live()
    if settings.openrouter_base_url != manifest["endpoint"] or settings.request_timeout_seconds != plan["timeout_seconds"]:
        raise ValueError("Execution endpoint or timeout differs from the prepared setup")
    if any((settings.data_root / "cache/artifacts").glob("*.json")):
        raise ValueError("Fresh comparison cells may not reuse cached model outputs")
    lock = suite / "active-cell.lock"
    exclusive(lock, {"week": week, "slug": slug})
    try:
        exclusive(cell / "started.json", {"mode": "live" if live else "synthetic_offline", "run_id": plan["run_id"]})
        pipeline = Pipeline(settings, provider=provider)
        if provider is None:
            pipeline._provider_override = ExactModelProvider(settings, suite, cell, pipeline._save_raw_response)
        mode = "live" if live else "fake"
        pipeline._select_provider(mode)
        if extraction:
            transcripts, packet = pipeline.load_week(week)
        else:
            transcripts = [Transcript.model_validate(t) for t in pool["transcripts"]]
        run = RunManifest(run_id=plan["run_id"], week_index=week, source_root=str(settings.transcript_root),
            source_ids=[t.source_id for t in transcripts], prompt_profile=PROMPT_VERSION, model_id=plan["model"],
            embedding_profile="disabled", mode=mode, execution_scope="generation_only",
            parent_run_id=pool["extraction_run_id"] if pool else None)
        run_dir = f"experiments/default/runs/{run.run_id}"
        pipeline.store.write_model(f"{run_dir}/manifest.json", run)
        try:
            if extraction:
                system, user = weekly_moment_prompt(packet, meeting_inventory(pipeline._compact_refs))
                def resolve(out):
                    return resolve_moment_references(out, pipeline._compact_refs)
                artifact = pipeline._call_json(stage, run, run_dir, system, user,
                    canonical_hash({"system": system, "user": user, "sources": plan["source_packet_sha256"]}),
                    StrategicCompactMomentResponse.model_json_schema(),
                    validate=lambda out: pipeline._parse_moments(resolve(out), run.run_id, transcripts))
                moments = pipeline._parse_moments(resolve(artifact.output), run.run_id, transcripts)
                pipeline.store.write_json(f"{run_dir}/moments.json", [m.model_dump(mode="json") for m in moments])
                freeze = freeze_pool(suite, week, pipeline, run, transcripts, moments, artifact)
                result = {"run_id": run.run_id, "week_index": week, "stage": stage,
                          "moments": len(moments), "pool_hash": freeze["pool_hash"], "next": "inspect_shared_pool_then_angles"}
            else:
                moments = [Moment.model_validate(m) for m in pool["moments"]]
                system, user = angle_prompt(pool["moment_packet"], [])
                artifact = pipeline._call_json(stage, run, run_dir, system, user,
                    canonical_hash({"system": system, "user": user, "pool_hash": seal["pool_hash"]}),
                    StrategicAngleResponse.model_json_schema(),
                    validate=lambda out: pipeline._parse_angles(out, run.run_id, moments))
                angles = pipeline._parse_angles(artifact.output, run.run_id, moments, artifact=artifact)
                pipeline.store.write_json(f"{run_dir}/moments.json", pool["moments"])
                pipeline.store.write_json(f"cycles/week{week}/sources.json", {"transcripts": pool["transcripts"]})
                pipeline.store.write_json(f"{run_dir}/candidates.json", [a.model_dump(mode="json") for a in angles])
                pipeline._write_discovery_outputs(run_dir, artifact.output, angles)
                result = {"run_id": run.run_id, "week_index": week, "stage": stage, "moments": len(moments),
                          "angles": len(angles), "pool_hash": seal["pool_hash"], "embedding_requests": 0,
                          "similarity_status": "not_run"}
        except Exception as error:
            run.status = "failed"
            pipeline.store.write_model(f"{run_dir}/manifest.json", run, overwrite=True)
            write(cell / "result.json", {"status": "failed", "error_type": type(error).__name__, "error": str(error)})
            raise
        run.status = "generation_completed"
        pipeline.store.write_model(f"{run_dir}/manifest.json", run, overwrite=True)
        write(cell / "result.json", {"status": "completed", **result})
        if not extraction:
            render_review(suite, cell, result)
        return result
    finally:
        lock.unlink()


def render_pool_review(pool: dict, home: Path) -> Path:
    moments = {m["moment_id"]: m for m in pool["moments"]}
    spans = {s["span_id"]: s for t in pool["transcripts"] for s in t["spans"]}
    lines = [f"# Week {pool['week']} shared Luna Pro shortlist", "",
             "One validated extraction, frozen for all three angle models. Source binding does not establish exhaustive recall or editorial approval.", "",
             "**Coverage notes:** " + json.dumps(pool["coverage_notes"], ensure_ascii=False), ""]
    for moment in moments.values():
        lines.extend([f"## {moment['moment_id']}", "", moment["proposition"], "",
                      "**Discovery:** " + json.dumps(moment["discovery"], ensure_ascii=False), "",
                      "**Qualifications:** " + json.dumps(moment["qualifications"], ensure_ascii=False), ""])
        for ref in moment["context_span_ids"]:
            span = spans[ref]
            lines.extend([f"**[{span['start_seconds']} seconds]** {span['text']}", ""])
    path = home / "review.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def render_review(suite: Path, cell: Path, result: dict) -> Path:
    store = JsonStore(cell / "data")
    run = f"experiments/default/runs/{result['run_id']}"
    plan = read(cell / "plan.json")
    candidates = store.read_json(f"{run}/candidates.json")
    moments = {m["moment_id"]: m for m in store.read_json(f"{run}/moments.json")}
    transcripts = store.read_json(f"cycles/week{plan['week']}/sources.json")["transcripts"]
    spans = {s["span_id"]: s for t in transcripts for s in t["spans"]}
    lines = [f"# Week {plan['week']} · {plan['model']}", "", "Reasoning: high. Independent angle generation from the shared frozen Luna Pro extraction; no history, embeddings, matching, refinement or approval.", "",
             "Week numbers identify supplied folders; recording dates and public reuse permission are not established by those labels.", "",
             f"Moments: {len(moments)}. Candidate angles: {len(candidates)}. Model scores are provisional, not editorial approval.", ""]
    def support(moment_ids):
        result = ["### Supporting source content", "", "Original turns from each supporting moment's context; separate ranges may be nonadjacent. Timestamps are elapsed recording time.", ""]
        for mid in moment_ids:
            moment = moments[mid]
            result.extend([f"**Moment:** {mid} · **Source:** {', '.join(moment['source_ids'])}", ""])
            for ref in moment["context_span_ids"]:
                span = spans[ref]
                seconds = int(span["start_seconds"]) if span["start_seconds"] is not None else None
                stamp = "untimed" if seconds is None else f"{seconds//3600:02d}:{seconds//60%60:02d}:{seconds%60:02d}"
                result.extend([f"**[{stamp}]** {span['text']}", ""])
        return result

    for index, candidate in enumerate(candidates, 1):
        angle = candidate["strategy"]
        lines.extend([f"## {index}. {angle['title']}", ""])
        for field in ("content_opportunity", "strategic_purpose", "content_type", "strategic_rationale", "audience",
                      "core_perspective", "tension", "wia_expertise_in_action", "service_relevance", "reader_decision",
                      "evidence_readiness", "research_questions", "selection_reason", "source_assertions", "inference",
                      "qualifiers", "risks", "quality"):
            value = angle[field]
            lines.extend([f"**{field}:** {json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else value}", ""])
        lines.extend(support(angle["moment_ids"]))
    lines.extend(["## Internal insights", ""])
    for insight in store.read_json(f"{run}/internal_insights.json"):
        lines.extend([insight["insight"], "", "**Strategic use:** " + insight["strategic_use"], "",
                      "**Research questions:** " + json.dumps(insight["research_questions"], ensure_ascii=False), ""])
        lines.extend(support(insight["moment_ids"]))
    path = cell / "review.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
