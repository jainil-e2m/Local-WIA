"""Isolated two-stage model comparisons. Preparation never dispatches a provider."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .config import BACKEND_ROOT, Settings
from .pipeline import Pipeline
from .prompts import weekly_moment_prompt
from .provider import LiveProvider, chat_body
from .store import JsonStore, canonical_hash
from .strategy_contracts import StrategicAngleResponse, StrategicCompactMomentResponse
from .weekly import meeting_inventory

MODELS = {
    "luna-pro": "openai/gpt-6-luna-pro",
    "sol": "openai/gpt-6.1-sol",
    "sonnet": "anthropic/claude-sonnet-5.5",
}
WEEKS = (3, 4)
SUITE = "week3-week4-model-quality-20261015"
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


def cell_settings(base: Settings, suite: Path, week: int, slug: str) -> Settings:
    return base.model_copy(update={
        "data_root": cell_path(suite, week, slug) / "data", "transcript_root": suite / "inputs",
        "openrouter_moments_model": MODELS[slug], "openrouter_angles_model": MODELS[slug],
        "llm_payload_format": "compact_weekly", "llm_reasoning_effort": "high", "llm_response_format": "json_object",
        "llm_completion_tokens": None, "llm_input_limits_enabled": False,
        "embeddings_enabled": False, "live_enabled": True,
    })


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
    cells = []
    for week in WEEKS:
        reference_request = None
        for slug, model in MODELS.items():
            cell = cell_path(suite, week, slug)
            settings = cell_settings(base, suite, week, slug)
            pipeline = Pipeline(settings)
            transcripts, packet = pipeline.load_week(week)
            system, user = weekly_moment_prompt(packet, meeting_inventory(pipeline._compact_refs))
            body = chat_body(model=model, system=system, user=user, schema=schemas["moment_extraction"],
                             reasoning_effort="high", response_format="json_object")
            # Equality of actual messages, not merely similar model-facing instructions.
            if reference_request is not None and body["messages"] != reference_request:
                raise ValueError("Models did not receive identical weekly source/instruction messages")
            reference_request = body["messages"]
            catalog = read(catalogs / slug / "model-check.json")
            budget = catalog_check(catalog, body)
            store.write_json(f"catalogs/{slug}.json", catalog)
            write(cell / "prepared-extraction.request.json", body)
            entry = {"week": week, "slug": slug, "model": model, "reasoning_effort": "high",
                     "run_id": f"{SUITE}-w{week}-{slug}", "source_count": len(transcripts),
                     "source_turns": sum(len(t.spans) for t in transcripts),
                     "source_packet_sha256": hashlib.sha256(packet.encode("utf-8")).hexdigest(),
                     "extraction_request_hash": canonical_hash(body), "request_characters": len(json.dumps(body, ensure_ascii=False)),
                     "catalog_hash": canonical_hash(catalog), "capacity_check": budget,
                     "timeout_seconds": settings.request_timeout_seconds,
                     "angle_request_status": "Built only after this model's whole extraction passes validation"}
            write(cell / "plan.json", entry)
            cells.append(entry)
    manifest = {"suite": SUITE, "status": "prepared_awaiting_user_approval", "sources": sources, "cells": cells,
                "runtime_identity": runtime_identity(), "schema_hashes": {k: canonical_hash(v) for k, v in schemas.items()},
                "endpoint": base.openrouter_base_url, "max_paid_calls": 12, "calls_per_cell": 2,
                "execution_order": [f"week{w}/{slug}" for w in WEEKS for slug in MODELS],
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
        if stage not in {"moment_extraction", "angle_generation"}:
            raise ValueError("Only the two generation stages are permitted")
        plan = read(self.cell / "plan.json")
        if plan not in manifest["cells"]:
            raise ValueError("Cell plan differs from the sealed suite")
        body = chat_body(model=plan["model"], system=system, user=user, schema=schema,
                         reasoning_effort="high", response_format="json_object")
        catalog = read(self.suite / "catalogs" / f"{plan['slug']}.json")
        if canonical_hash(catalog) != plan["catalog_hash"] or self.llm_base_url != manifest["endpoint"].rstrip("/"):
            raise ValueError("Prepared route configuration changed")
        budget = catalog_check(catalog, body)
        if stage == "moment_extraction" and canonical_hash(body) != plan["extraction_request_hash"]:
            raise ValueError("Extraction request differs from the approved preview")
        exclusive(self.cell / f"{stage}.dispatch.json", {"request_hash": canonical_hash(body), "capacity_check": budget})
        result, receipt = super().json_call(stage=stage, system=system, user=user, schema=schema, fingerprint=fingerprint)
        if receipt["raw"].get("model") != plan["model"]:
            raise ValueError("Returned model differs from the exact requested model; raw response preserved")
        return result, receipt

    def embed(self, **kwargs):
        raise RuntimeError("Embeddings are prohibited in this comparison")


def run_cell(base: Settings, suite: Path, week: int, slug: str, *, live=False, provider=None) -> dict:
    """CLI live execution is explicitly gated; provider injection is for offline mechanics tests."""
    manifest = verify_suite(suite)
    if not live and provider is None:
        raise ValueError("Explicit --live is required after user approval")
    cell = cell_path(suite, week, slug)
    plan = next(c for c in manifest["cells"] if c["week"] == week and c["slug"] == slug)
    if read(cell / "plan.json") != plan:
        raise ValueError("Cell plan differs from the sealed suite")
    settings = cell_settings(base, suite, week, slug)
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
        try:
            result = pipeline.run(week, mode="live" if live else "fake", run_id=plan["run_id"])
        except Exception as error:
            write(cell / "result.json", {"status": "failed", "error_type": type(error).__name__, "error": str(error)})
            raise
        write(cell / "result.json", {"status": "completed", **result})
        render_review(suite, cell, result)
        return result
    finally:
        lock.unlink()


def render_review(suite: Path, cell: Path, result: dict) -> Path:
    store = JsonStore(cell / "data")
    run = f"experiments/default/runs/{result['run_id']}"
    plan = read(cell / "plan.json")
    candidates = store.read_json(f"{run}/candidates.json")
    moments = {m["moment_id"]: m for m in store.read_json(f"{run}/moments.json")}
    transcripts = store.read_json(f"cycles/week{plan['week']}/sources.json")["transcripts"]
    spans = {s["span_id"]: s for t in transcripts for s in t["spans"]}
    lines = [f"# Week {plan['week']} · {plan['model']}", "", "Reasoning: high. Independent two-stage generation; no history, embeddings, matching, refinement or approval.", "",
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
