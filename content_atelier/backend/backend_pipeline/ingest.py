from __future__ import annotations

import hashlib
import re
from pathlib import Path

from .models import Span, Transcript
from .store import sha256_text

TIMESTAMP = re.compile(r"(?P<h>\d{2}):(?P<m>\d{2}):(?P<s>\d{2})[.,](?P<ms>\d{3})")
SPEAKER = re.compile(r"^\s*(?P<speaker>[^:]{1,100}):\s*(?P<text>.*)$")
WEEK = re.compile(r"week(?P<number>\d+)", re.IGNORECASE)


def seconds(value: str) -> float:
    match = TIMESTAMP.search(value)
    if not match:
        return 0.0
    return int(match["h"]) * 3600 + int(match["m"]) * 60 + int(match["s"]) + int(match["ms"]) / 1000


def parse_transcript(path: Path, week_index: int) -> Transcript:
    raw = path.read_text(encoding="utf-8-sig", errors="replace")
    source_id = f"zoom:{sha256_text(str(path.resolve()))[:16]}"
    lines = raw.splitlines()
    spans: list[Span] = []
    ordinal = 0
    i = 0
    is_vtt = any(" --> " in line for line in lines)
    while i < len(lines):
        if " --> " not in lines[i]:
            i += 1
            continue
        start_raw, end_raw = [part.strip() for part in lines[i].split(" --> ", 1)]
        start, end = seconds(start_raw), seconds(end_raw)
        i += 1
        text_lines: list[str] = []
        while i < len(lines) and lines[i].strip() and " --> " not in lines[i]:
            text_lines.append(lines[i].strip())
            i += 1
        text = " ".join(text_lines).strip()
        if not text:
            continue
        match = SPEAKER.match(text)
        speaker = match.group("speaker").strip() if match else None
        content = match.group("text").strip() if match else text
        spans.append(
            Span(
                span_id=f"{source_id}:span:{ordinal}",
                source_id=source_id,
                ordinal=ordinal,
                start_seconds=start,
                end_seconds=end,
                speaker=speaker,
                text=content,
            )
        )
        ordinal += 1
    if not spans:
        cleaned = " ".join(line.strip() for line in lines if line.strip())
        if cleaned:
            spans = [
                Span(span_id=f"{source_id}:span:0", source_id=source_id, ordinal=0, start_seconds=0, end_seconds=0, text=cleaned)
            ]
    return Transcript(
        source_id=source_id,
        week_index=week_index,
        path=str(path),
        content_hash=hashlib.sha256(raw.encode("utf-8")).hexdigest(),
        spans=spans,
        source_format="webvtt" if is_vtt else "plain_text",
    )


def discover_week(root: Path, week_index: int) -> list[Transcript]:
    directory = root / f"week{week_index}"
    if not directory.exists():
        raise FileNotFoundError(f"No input directory: {directory}")
    return [
        parse_transcript(path, week_index)
        for path in sorted(directory.rglob("*"))
        if path.is_file() and path.suffix.lower() in {".txt", ".vtt", ".webvtt"}
    ]
