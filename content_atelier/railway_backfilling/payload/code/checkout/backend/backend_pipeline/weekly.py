"""Bridge the lossless packet to canonical source evidence without LLM preprocessing."""

from __future__ import annotations

import copy
from pathlib import Path

from .models import Span, Transcript
from .prepare import packet_for, read_source
from .store import JsonStore, canonical_hash

from .strategy_contracts import STRATEGY_VERSION, StrategicCompactMomentResponse, is_strategic_moment_response

LIVE_COMPACT_VERSION = STRATEGY_VERSION


def load_compact_week(root: Path, week: int, store: JsonStore) -> tuple[list[Transcript], str, dict[str, str], str]:
    directory = root / f"week{week}"
    if not directory.is_dir():
        raise FileNotFoundError(directory)
    paths = sorted(p for p in directory.rglob("*") if p.is_file() and p.suffix.lower() in {".txt", ".vtt", ".webvtt"})
    if not paths:
        raise ValueError("No transcript sources; refusing an empty weekly request")
    sources, raw_sources, first_ref = [], [], 1
    transcripts, reference_map = [], {}
    for i, path in enumerate(paths, 1):
        raw, source = read_source(path, week=week, meeting_ref=f"m{i}", first_ref=first_ref)
        if not source["turns"]:
            raise ValueError(f"Empty source: {path.name}")
        spans = []
        for turn in source["turns"]:
            turn["ref"] = f"m{i}.t{turn['ordinal'] + 1:04d}"
            span_id = f"{source['source_id']}:span:{turn['ordinal']}"
            reference_map[turn["ref"]] = span_id
            spans.append(
                Span(
                    span_id=span_id,
                    source_id=source["source_id"],
                    ordinal=turn["ordinal"],
                    start_seconds=turn.get("start_ms") / 1000 if turn.get("start_ms") is not None else None,
                    end_seconds=turn.get("end_ms") / 1000 if turn.get("end_ms") is not None else None,
                    speaker=turn.get("speaker"),
                    text=turn["text"],
                )
            )
        transcripts.append(
            Transcript(
                source_id=source["source_id"],
                week_index=week,
                path=source["source_path"],
                content_hash=source["raw_sha256"],
                spans=spans,
                source_format="webvtt" if any(t["kind"] == "cue" for t in source["turns"]) else "plain_text",
                source_metadata=source["metadata"],
            )
        )
        sources.append(source)
        raw_sources.append(raw)
        first_ref += len(spans)
    fingerprint = canonical_hash({"profile": LIVE_COMPACT_VERSION, "sources": sources})
    prefix = f"weekly_packets/week{week}/{fingerprint}"
    for source, raw in zip(sources, raw_sources, strict=True):
        store.write_bytes(f"{prefix}/raw/{source['meeting_ref']}.original", raw)
        store.write_json(f"{prefix}/sources/{source['meeting_ref']}.json", source)
    packet = packet_for(sources)
    store.write_text(f"{prefix}/source_packet.txt", packet)
    store.write_json(
        f"{prefix}/reference_map.json",
        {
            ref: {"canonical_span_id": reference_map[ref], "meeting_ref": s["meeting_ref"], **turn}
            for s in sources
            for turn in s["turns"]
            for ref in [turn["ref"]]
        },
    )
    store.write_json(
        f"{prefix}/integrity.json",
        {
            "source_count": len(sources),
            "turn_count": len(reference_map),
            "source_nonblank_lines_accounted": True,
            "raw_bytes_archived": True,
            "silent_truncation": False,
            "metadata_status": "zoom_metadata_not_supplied",
            "profile": LIVE_COMPACT_VERSION,
        },
    )
    return transcripts, packet, reference_map, prefix


def meeting_inventory(reference_map: dict[str, str]) -> list[dict]:
    groups: dict[str, list[str]] = {}
    for ref in reference_map:
        groups.setdefault(ref.split(".", 1)[0], []).append(ref)
    return [
        {"meeting_ref": meeting, "first_span_id": refs[0], "last_span_id": refs[-1], "span_count": len(refs)}
        for meeting, refs in groups.items()
    ]


def resolve_moment_references(output: dict, reference_map: dict[str, str]) -> dict:
    """Preserve the provider's short-ref output; resolve only a validation copy."""
    resolved = copy.deepcopy(output)

    def resolve(ref):
        if not isinstance(ref, str) or ref not in reference_map:
            raise ValueError("Moment response references an unknown compact source ID")
        return reference_map[ref]

    if "processed_meetings" in resolved:
        from .contracts import CompactMomentResponse

        contract = StrategicCompactMomentResponse if is_strategic_moment_response(output) else CompactMomentResponse
        contract.model_validate(output)
        expected = meeting_inventory(reference_map)
        received = resolved.pop("processed_meetings")
        if len(received) != len(expected) or {item["meeting_ref"] for item in received} != {
            item["meeting_ref"] for item in expected
        }:
            raise ValueError("Meeting coverage must acknowledge every supplied meeting exactly once")
        if sorted(received, key=lambda item: item["meeting_ref"]) != sorted(expected, key=lambda item: item["meeting_ref"]):
            raise ValueError("Meeting coverage bounds/counts do not match the delivered source inventory")
        # Canonical IDs are backend delivery provenance, not a claim that the
        # model echoed/read each turn. Review labels explicitly distinguish this.
        resolved["processed_span_ids"] = list(reference_map.values())
    else:
        resolved["processed_span_ids"] = [resolve(ref) for ref in resolved["processed_span_ids"]]
    for moment in resolved["moments"]:
        if "context_first_span_id" in moment:
            first = moment.pop("context_first_span_id")
            last = moment.pop("context_last_span_id")
            resolve(first)
            resolve(last)
            ordered = list(reference_map)
            start, end = ordered.index(first), ordered.index(last)
            if first.split(".", 1)[0] != last.split(".", 1)[0] or start > end:
                raise ValueError("Context boundaries must be chronological within the same meeting")
            moment["context_span_ids"] = ordered[start : end + 1]
        for field in ("anchor_span_ids", "context_span_ids"):
            moment[field] = [resolve(ref) for ref in moment[field]]
    return resolved
