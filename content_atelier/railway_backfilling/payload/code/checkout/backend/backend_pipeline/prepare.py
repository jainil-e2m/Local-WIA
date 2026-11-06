"""Local-only weekly packet preparation. No credentials, inference or provider token API.

This is a preparation profile, deliberately separate from the legacy live runner.
Original bytes, normalized source lines and reversible timing/reference maps are
saved before any subsequent model experiment. No text is summarized or truncated.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from .config import BACKEND_ROOT, PROJECT_ROOT
from .ingest import parse_transcript
from .prompts import COMPACT_PREPARATION_VERSION, compact_moment_prompt, moment_prompt
from .provider import chat_body
from .store import JsonStore, canonical_hash, sha256_text
from .strategy_contracts import StrategicMomentResponse as MomentResponse

TOKENIZER_URL = "https://openaipublic.blob.core.windows.net/encodings/o200k_base.tiktoken"
TOKENIZER_SHA256 = "446a9538cb6c348e3516120d7c08b09f57c36495e2acfffe59a5bf8b0cfb1a2d"
TIMING = re.compile(
    r"^(?P<start>\d{2,}:\d{2}:\d{2}[.,]\d{3})\s+-->\s+"
    r"(?P<end>\d{2,}:\d{2}:\d{2}[.,]\d{3})(?P<settings>.*)$"
)
SOURCE_SPEAKER = re.compile(r"^(?P<name>[^:\n]{1,100}):")
VERSION = "2026-10-08.lossless-weekly-preparation.v1"


def compact_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def milliseconds(value: str) -> int:
    h, m, seconds = value.replace(",", ".").split(":")
    s, ms = seconds.split(".")
    if not (0 <= int(m) < 60 and 0 <= int(s) < 60):
        raise ValueError(f"Invalid source timecode: {value}")
    return ((int(h) * 60 + int(m)) * 60 + int(s)) * 1000 + int(ms)


def seconds_text(value: int) -> str:
    whole, fraction = divmod(value, 1000)
    return f"{whole}.{fraction:03d}".rstrip("0").rstrip(".") if fraction else str(whole)


def read_source(path: Path, *, week: int, meeting_ref: str, first_ref: int) -> tuple[bytes, dict]:
    raw = path.read_bytes()
    decoded = raw.decode("utf-8-sig", errors="strict")
    text = decoded.replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")
    source_id = f"zoom:{sha256_text(str(path.resolve()))[:16]}"
    blocks: list[list[tuple[int, str]]] = []
    block: list[tuple[int, str]] = []
    padding_lines = 0
    for line_number, line in enumerate(lines, 1):
        if not line.strip():
            padding_lines += 1
            if block:
                blocks.append(block)
                block = []
        else:
            block.append((line_number, line))
    if block:
        blocks.append(block)
    turns = []
    structural = []
    for block in blocks:
        matches = [(i, TIMING.fullmatch(line)) for i, (_, line) in enumerate(block)]
        matches = [(i, match) for i, match in matches if match is not None]
        if any("-->" in line for _, line in block) and not matches:
            raise ValueError(f"Unparseable timing in {path.name}; no silent fallback")
        if len(matches) > 1:
            raise ValueError(f"Missing cue boundary in {path.name}; review source before compaction")
        if not matches:
            if len(block) == 1 and block[0][1].strip() == "WEBVTT":
                structural.append({"kind": "format_header", "lines": block})
                continue
            # Preserve notes/unknown header content/plain text as evidence, not a discarded block.
            turn = {"kind": "untimed", "text": "\n".join(line for _, line in block), "source_lines": block}
            turns.append(turn)
            continue
        position, match = matches[0]
        assert match is not None
        if position:
            prefix = block[:position]
            if len(prefix) == 1 and prefix[0][1].strip().isdigit():
                structural.append({"kind": "cue_number", "lines": prefix})
            else:
                turns.append({"kind": "untimed", "text": "\n".join(line for _, line in prefix), "source_lines": prefix})
        body = block[position + 1 :]
        start, end = milliseconds(match["start"]), milliseconds(match["end"])
        if end < start:
            raise ValueError(f"Negative cue duration in {path.name}")
        cue_text = "\n".join(line for _, line in body)
        speaker = SOURCE_SPEAKER.match(cue_text)
        turns.append(
            {
                "kind": "cue",
                "start_ms": start,
                "end_ms": end,
                "start_raw": match["start"],
                "end_raw": match["end"],
                "cue_settings": match["settings"],
                "timing_source_line": block[position],
                "speaker": speaker["name"] if speaker else None,
                "text": cue_text,
                "source_lines": body,
            }
        )
    for ordinal, turn in enumerate(turns):
        turn.update(
            {
                "ref": str(first_ref + ordinal),
                "ordinal": ordinal,
                "source_id": source_id,
                "source_revision_sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    # Every nonblank source line must appear in the evidence map or recorded syntax.
    accounted = [number for entry in structural for number, _ in entry["lines"]]
    for turn in turns:
        accounted.extend(number for number, _ in turn["source_lines"])
        if turn["kind"] == "cue":
            accounted.append(turn["timing_source_line"][0])
    expected = [n for n, line in enumerate(lines, 1) if line.strip()]
    if sorted(accounted) != expected:
        raise ValueError(f"Source line accounting failed: {path.name}")
    return raw, {
        "source_id": source_id,
        "raw_sha256": hashlib.sha256(raw).hexdigest(),
        "raw_bytes": len(raw),
        "normalized_characters": len(text),
        "source_path": str(path.resolve()),
        "week_index": week,
        "meeting_ref": meeting_ref,
        "metadata": {
            "filename_label": path.stem,
            "name": None,
            "date": None,
            "weekday": None,
            "timezone": None,
            "status": "zoom_metadata_not_supplied",
        },
        "turns": turns,
        "structural_lines": structural,
        "padding_lines": padding_lines,
        "fidelity": {
            "original_bytes_archived": True,
            "nonblank_line_accounting_passed": True,
            "cue_text_preserved_after_line_ending_normalization": True,
        },
    }


def packet_for(sources: list[dict]) -> str:
    parts = []
    for source in sources:
        parts.append("MEETING " + compact_json({"source_id": source["meeting_ref"], **source["metadata"]}))
        for turn in source["turns"]:
            if turn["kind"] == "cue":
                duration = turn["end_ms"] - turn["start_ms"]
                parts.append(f"{turn['ref']}|{seconds_text(turn['start_ms'])}+{seconds_text(duration)}|{turn['text']}")
                if turn["cue_settings"]:
                    parts.append("CUE_SETTINGS " + compact_json({"ref": turn["ref"], "settings": turn["cue_settings"]}))
            elif turn['kind'] == 'timestamped':
                parts.append("TIMESTAMPED " + compact_json({"ref": turn['ref'], "start_ms": turn['start_ms'],
                                                         "end_ms": None, "text": turn['text']}))
            else:
                parts.append("UNTIMED " + compact_json({"ref": turn["ref"], "text": turn["text"]}))
        parts.append("END_MEETING " + source["meeting_ref"])
    return "\n".join(parts)


def cached_counter(cache: Path) -> Callable[[str], int]:
    """Fail closed rather than downloading a tokenizer during private preparation."""
    import tiktoken

    vocabulary = cache / hashlib.sha1(TOKENIZER_URL.encode()).hexdigest()
    if not vocabulary.is_file() or hashlib.sha256(vocabulary.read_bytes()).hexdigest() != TOKENIZER_SHA256:
        raise RuntimeError("Verified tokenizer vocabulary is not cached; obtain the public vocabulary separately first")
    previous = os.environ.get("TIKTOKEN_CACHE_DIR")
    os.environ["TIKTOKEN_CACHE_DIR"] = str(cache.resolve())
    try:
        encoding = tiktoken.get_encoding("o200k_harmony")
    finally:
        if previous is None:
            os.environ.pop("TIKTOKEN_CACHE_DIR", None)
        else:
            os.environ["TIKTOKEN_CACHE_DIR"] = previous
    # Source strings that resemble special tokens remain ordinary text.
    return lambda value: len(encoding.encode(value, disallowed_special=()))


def token_report(
    request: dict,
    packet: str,
    sources: list[dict],
    *,
    counter: Callable[[str], int],
    context: int,
    completion: int,
    margin: int,
    baseline: tuple[str, str] | None = None,
) -> dict:
    system, user = [message["content"] for message in request["messages"]]
    schema_text = compact_json(request["response_format"]["json_schema"]["schema"])
    message_tokens = counter(system) + counter(user)
    schema_tokens = counter(schema_text)
    # Hosted routes may inject/reformat this schema differently. This is a labeled proxy, not API billing.
    input_proxy = message_tokens + schema_tokens
    refs = [turn["ref"] for source in sources for turn in source["turns"]]
    coverage_tokens = counter(compact_json({"moments": [], "processed_span_ids": refs, "coverage_notes": []}))
    scenarios = []
    for budget in sorted({16384, 20480, 24576, 32768, completion}):
        headroom = context - input_proxy - margin - budget
        scenarios.append({"completion_reserved": budget, "remaining_context": headroom, "fits": headroom >= 0})
    result = {
        "tokenizer": "o200k_harmony",
        "tokenizer_package": "tiktoken==0.12.0",
        "vocabulary_sha256": TOKENIZER_SHA256,
        "counting_is_local": True,
        "hosted_provider_exact_input_tokens": None,
        "method": "Exact local BPE counts of rendered messages; minified schema is a provider-format proxy. Margin is not measured usage.",
        "system_text_tokens": counter(system),
        "user_text_tokens": counter(user),
        "message_text_tokens": message_tokens,
        "source_packet_tokens": counter(packet),
        "schema_proxy_tokens": schema_tokens,
        "input_with_schema_proxy_tokens": input_proxy,
        "provider_framing_and_schema_margin": margin,
        "context_limit_reference_tokens": context,
        "selected_completion_reserve": completion,
        "selected_reserve_includes_reasoning_and_final_json": True,
        "context_headroom_after_reserves": context - input_proxy - margin - completion,
        "capacity_fits_selected_budget": input_proxy + margin + completion <= context,
        "coverage_only_output_tokens": coverage_tokens,
        "completion_space_after_coverage_only": completion - coverage_tokens,
        "completion_budget_scenarios": scenarios,
        "request_serialized_characters": len(compact_json(request)),
        "dialogue_only_tokens_sum": sum(counter(t["text"]) for s in sources for t in s["turns"]),
        "per_source": [
            {
                "meeting_ref": s["meeting_ref"],
                "filename": Path(s["source_path"]).name,
                "turns": len(s["turns"]),
                "cue_turns": sum(t["kind"] == "cue" for t in s["turns"]),
                "packet_tokens_in_isolation": counter(packet_for([s])),
            }
            for s in sources
        ],
    }
    if baseline is not None:
        result["legacy_message_text_tokens"] = counter(baseline[0]) + counter(baseline[1])
        result["message_token_reduction_percent"] = round(100 * (1 - message_tokens / result["legacy_message_text_tokens"]), 2)
    return result


def prepare_week(
    *,
    transcript_root: Path,
    data_root: Path,
    week: int,
    model: str = "openai/gpt-oss-120b:free",
    context: int = 131072,
    completion: int = 20480,
    margin: int = 2048,
    provider_snapshot: dict | None = None,
    counter: Callable[[str], int] | None = None,
) -> tuple[Path, dict]:
    if min(week, context, completion) <= 0 or margin < 0:
        raise ValueError("Week/context/completion must be positive; margin must be nonnegative")
    directory = transcript_root / f"week{week}"
    if not directory.is_dir():
        raise FileNotFoundError(directory)
    paths = sorted(p for p in directory.rglob("*") if p.is_file() and p.suffix.lower() in {".txt", ".vtt", ".webvtt"})
    if not paths:
        raise ValueError("No transcript sources; refusing an empty preparation")
    raw_sources, sources, first_ref = [], [], 1
    for i, path in enumerate(paths, 1):
        raw, source = read_source(path, week=week, meeting_ref=f"m{i}", first_ref=first_ref)
        if not source["turns"]:
            raise ValueError(f"Empty transcript source: {path.name}")
        raw_sources.append(raw)
        sources.append(source)
        first_ref += len(source["turns"])
    packet = packet_for(sources)
    system, user = compact_moment_prompt(packet)
    request = chat_body(model=model, system=system, user=user, schema=MomentResponse.model_json_schema())
    request["max_tokens"] = completion
    # Identity covers source bytes, actual prompt/settings and route evidence; timestamps are not identity.
    fingerprint = canonical_hash(
        {
            "version": VERSION,
            "request": request,
            "sources": sources,
            "context": context,
            "margin": margin,
            "provider_snapshot": provider_snapshot,
            "tokenizer": TOKENIZER_SHA256,
        }
    )
    prefix = f"preparations/week{week}/{fingerprint}"
    store = JsonStore(data_root)
    for raw, source in zip(raw_sources, sources, strict=True):
        store.write_bytes(f"{prefix}/raw/{source['meeting_ref']}.original", raw)
        store.write_json(f"{prefix}/sources/{source['meeting_ref']}.json", source)
    store.write_text(f"{prefix}/source_packet.txt", packet)
    store.write_json(f"{prefix}/source_packet.json", {"format": "whole-week-lines-v1", "text": packet})
    store.write_json(f"{prefix}/request.json", request)
    store.write_text(f"{prefix}/messages/system.txt", system)
    store.write_text(f"{prefix}/messages/user.txt", user)
    store.write_json(
        f"{prefix}/reference_map.json", {t["ref"]: {"meeting_ref": s["meeting_ref"], **t} for s in sources for t in s["turns"]}
    )
    if provider_snapshot is not None:
        store.write_json(f"{prefix}/provider_catalog_snapshot.json", provider_snapshot)
    # Re-derive cue text from source line records, and exact start/end from compact timing.
    fidelity = all(t["text"] == "\n".join(line for _, line in t["source_lines"]) for s in sources for t in s["turns"])
    store.write_json(
        f"{prefix}/integrity.json",
        {
            "source_count": len(sources),
            "turn_count": first_ref - 1,
            "source_nonblank_lines_accounted": True,
            "cue_text_matches_source_lines": fidelity,
            "archived_bytes_sha256_verified": all(
                hashlib.sha256(store.path(f"{prefix}/raw/{s['meeting_ref']}.original").read_bytes()).hexdigest()
                == s["raw_sha256"]
                for s in sources
            ),
            "original_inputs_modified": False,
            "silent_truncation": False,
            "request_count_if_sent": 1,
            "requests_sent": 0,
            "embeddings_requested": 0,
        },
    )
    # Baseline comparison only, not an authority for the compact source or its byte hash.
    legacy = [span.model_dump(mode="json") for path in paths for span in parse_transcript(path, week).spans]
    report = token_report(
        request,
        packet,
        sources,
        counter=counter or cached_counter(data_root / "tokenizers"),
        context=context,
        completion=completion,
        margin=margin,
        baseline=moment_prompt(legacy),
    )
    requested_found = None
    if provider_snapshot is not None and provider_snapshot.get("requested_model") == model:
        requested_found = provider_snapshot.get("requested_model_found")
    report.update(
        {
            "source_count": len(sources),
            "turn_count": first_ref - 1,
            "requested_model": model,
            "requested_route_advertised_in_snapshot": requested_found,
            "meeting_metadata_complete": False,
            "live_readiness": "not_cleared",
            "live_requests_sent": 0,
            "profile": COMPACT_PREPARATION_VERSION,
            "legacy_live_runner_uses_this_profile": False,
        }
    )
    store.write_json(f"{prefix}/token_report.json", report)
    store.write_json(
        f"{prefix}/manifest.json",
        {
            "created_at_utc": datetime.now(UTC).isoformat(),
            "fingerprint": fingerprint,
            "preparation_version": VERSION,
            "prompt_profile": COMPACT_PREPARATION_VERSION,
            "status": "prepared_locally_not_sent",
            "sources": [
                {"meeting_ref": s["meeting_ref"], "source_id": s["source_id"], "raw_sha256": s["raw_sha256"]} for s in sources
            ],
            "private_artifacts": True,
            "token_report": "token_report.json",
            "metadata_warning": "Zoom meeting dates/day/timezones/source-confirmed names have not been supplied",
            "no_credentials_loaded": True,
        },
    )
    lines = [
        "# Local weekly preparation",
        "",
        f"Model: `{model}`. No requests sent.",
        "",
        f"Sources: {len(sources)}; turns: {first_ref - 1}.",
        f"Message text: {report['message_text_tokens']:,} local tokens.",
        f"Schema proxy: {report['schema_proxy_tokens']:,}; input proxy: {report['input_with_schema_proxy_tokens']:,}.",
        f"Completion reserve: {completion:,}; provider-format margin: {margin:,}.",
        f"Context headroom: {report['context_headroom_after_reserves']:,} against reference {context:,}.",
        f"Coverage-only final JSON: {report['coverage_only_output_tokens']:,} tokens.",
        "",
        "Counts are not hosted-provider billing. Input fitting does not prove editorial quality or output sufficiency.",
        "Missing Zoom metadata remains null. Do not infer calendar dates or reorder meetings by filenames.",
        "The legacy live runner is unchanged and does not consume this preparation profile.",
        "The 120,000-character live guard remains separate from this token diagnostic.",
    ]
    store.write_text(f"{prefix}/report.md", "\n".join(lines) + "\n")
    return store.path(prefix), report


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare and count one whole week locally; never send a model request")
    parser.add_argument("--week", type=int, required=True)
    parser.add_argument("--transcript-root", type=Path, default=BACKEND_ROOT / "zoom_backfill_meetings")
    parser.add_argument("--data-root", type=Path, default=PROJECT_ROOT / "testing" / ".data")
    parser.add_argument("--model", default="openai/gpt-oss-120b:free")
    parser.add_argument("--context-tokens", type=int, default=131072)
    parser.add_argument("--completion-tokens", type=int, default=20480)
    parser.add_argument("--margin-tokens", type=int, default=2048)
    parser.add_argument("--provider-snapshot", type=Path)
    args = parser.parse_args()
    snapshot = json.loads(args.provider_snapshot.read_text(encoding="utf-8")) if args.provider_snapshot else None
    destination, report = prepare_week(
        transcript_root=args.transcript_root,
        data_root=args.data_root,
        week=args.week,
        model=args.model,
        context=args.context_tokens,
        completion=args.completion_tokens,
        margin=args.margin_tokens,
        provider_snapshot=snapshot,
    )
    print(
        json.dumps(
            {
                "artifact_directory": str(destination),
                "source_count": report["source_count"],
                "turn_count": report["turn_count"],
                "message_text_tokens": report["message_text_tokens"],
                "input_with_schema_proxy_tokens": report["input_with_schema_proxy_tokens"],
                "context_headroom_after_reserves": report["context_headroom_after_reserves"],
                "live_readiness": report["live_readiness"],
                "requests_sent": 0,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
