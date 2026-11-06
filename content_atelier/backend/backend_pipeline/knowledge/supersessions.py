"""Superseded lines in the three supplied documents (E.B25 (c); WIA rulings R-1 to R-16).

Documents 01 to 03 (Savannah Jordan's content strategy, the founder voice guide, the Tier 1 Accelerator workbook) are
supplied text: nothing compiles them, so every version carries them over from its base. Some of their lines state a
position WIA's rulings have since superseded (referrals as "a ceiling", "you can't DIY ads", a daily TikTok cadence).
The supplied originals stay untouched, in the committed base files and the archive; what changes is what a compiled
version carries.

`backend/knowledge_base/supersessions.json` is the committed, reviewable list: for each line its document, its exact
text, how often it occurs, the ruling, the action and the note. From the file's `effective` date the compiler applies
it to the carried-over text of those documents:

- `remove` drops the line;
- `annotate` keeps it and appends the note in brackets, so the line still says what the supplied document said and
  the reader sees what governs instead;
- `replace` writes the ruling's wording and the note.

A line is matched by its exact text (trailing spaces aside, which the supplied documents carry inconsistently) and
must occur exactly as often as the entry says. Otherwise the compile stops and names it: a changed supplied document
can never silently drop a supersession. The manifest of a version records which entries it applied (and the file's
hash), so a version compiled from it carries the superseded text over and applies only what is new.

A change to these documents is an identity change: the version waits for its benchmark before it becomes the default
(R44).
"""
from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path

FILE = "supersessions.json"
DOCUMENTS = frozenset({"content_strategy", "founder_voice_guide", "accelerator_strategy"})
ACTIONS = ("remove", "annotate", "replace")


def load(root: Path) -> tuple[dict | None, str | None]:
    """The supersessions beside a knowledge base, and the file's hash; (None, None) when it has none."""
    path = Path(root) / FILE
    if not path.is_file():
        return None, None
    raw = path.read_bytes()
    spec = json.loads(raw.decode("utf-8"))
    ids = [e["id"] for e in spec["entries"]]
    if len(ids) != len(set(ids)):
        raise ValueError(f"{FILE}: every entry needs its own id")
    for e in spec["entries"]:
        if e["document"] not in DOCUMENTS or e["action"] not in ACTIONS or not e.get("line", "").strip() \
                or not e.get("note", "").strip() or int(e.get("occurrences", 0)) < 1 \
                or (e["action"] == "replace") != bool((e.get("replacement") or "").strip()):
            raise ValueError(f"{FILE}: entry {e['id']} needs a supplied document, an action, its line, a note, how often the "
                             "line occurs, and a replacement exactly when it replaces")
    return spec, hashlib.sha256(raw).hexdigest()


def due(spec: dict | None, on: date, applied: set[str] | frozenset[str] = frozenset()) -> list[dict]:
    """The entries in force on `on` that the base version has not applied yet."""
    if not spec:
        return []
    return [e for e in spec["entries"] if date.fromisoformat(e.get("effective") or spec["effective"]) <= on
            and e["id"] not in applied]


def apply(text: str, entries: list[dict]) -> str:
    """One document's text with its entries applied; stops, naming the entry, when a line is not where it should be."""
    lines = text.split("\n")
    for e in entries:
        target = e["line"].rstrip()
        found = [i for i, line in enumerate(lines) if line.rstrip() == target]
        if len(found) != int(e["occurrences"]):
            raise ValueError(f"Supersession {e['id']} ({e['document']}, {e['ruling']}) expects {e['occurrences']} line(s) reading "
                             f"{target!r} and found {len(found)}: the supplied document changed, so no version compiles until "
                             f"{FILE} is reviewed")
        for i in found:
            note = f" [{e['note'].strip()}]"
            lines[i] = None if e["action"] == "remove" else (
                target + note if e["action"] == "annotate" else e["replacement"].rstrip() + note)
        lines = [line for line in lines if line is not None]
    return "\n".join(lines)


def counts(entries: list[dict]) -> dict[str, int]:
    """Entries and lines by action, for the record."""
    out: dict[str, int] = {}
    for e in entries:
        out[e["action"]] = out.get(e["action"], 0) + 1
        out[e["action"] + "_lines"] = out.get(e["action"] + "_lines", 0) + int(e["occurrences"])
    return out
