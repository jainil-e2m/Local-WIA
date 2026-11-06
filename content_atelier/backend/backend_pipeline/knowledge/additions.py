"""Supplied documents added to the knowledge base from a date (E.B25 (e)).

Some documents are written outside the store and reviewed as a whole, like the editing guide: Whitney's corrections to
drafts in her ChatGPT history, distilled once into rules for whoever writes or plans WIA copy (section 1.8, T2: the export
pack made the writer's drafts closer to what she approves and halved the constructions she rejects). Nothing compiles
them from items, and the runtime never reads the export (R52): the reviewed text is a committed file beside the
knowledge base.

`backend/knowledge_base/additions.json` is the committed, reviewable list: for each document its key, file, heading,
owner, status, stages, provenance, review interval, the date it takes effect, and the hash of its reviewed text. From
that date the compiler adds it, once, to a version whose base lacks the document; the manifest records the entries
applied (and the list's hash), and every later version carries the document over unchanged from its base, like any
supplied document. A file whose text no longer matches its recorded hash stops the compile, naming the entry: a
reviewed document never changes without a new review.

A new document changes what a stage is told, so it is an identity change: the version waits for its benchmark before
it becomes the default (R44).
"""
from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path

FILE = "additions.json"
STATUSES = ("supplied", "confirmed")
FIELDS = ("id", "key", "file", "heading", "owner", "status", "stages", "provenance", "review_interval_days", "sha256")


def load(root: Path) -> tuple[dict | None, str | None]:
    """The additions beside a knowledge base, and the file's hash; (None, None) when it has none."""
    path = Path(root) / FILE
    if not path.is_file():
        return None, None
    raw = path.read_bytes()
    spec = json.loads(raw.decode("utf-8"))
    for name in ("id", "key"):
        values = [e.get(name) for e in spec["entries"]]
        if len(values) != len(set(values)):
            raise ValueError(f"{FILE}: every entry needs its own {name}")
    for e in spec["entries"]:
        if any(not e.get(f) for f in FIELDS) or e["status"] not in STATUSES or not set(e["stages"]) <= {
                "strategist", "brief", "verifier", "extraction"}:
            raise ValueError(f"{FILE}: entry {e.get('id')} needs {', '.join(FIELDS)}, a status of {' or '.join(STATUSES)} "
                             "and known stages")
    return spec, hashlib.sha256(raw).hexdigest()


def due(spec: dict | None, on: date, applied: set[str] | frozenset[str], present: set[str]) -> list[dict]:
    """The entries in force on `on` that the base version has not applied and whose document it lacks."""
    if not spec:
        return []
    return [e for e in spec["entries"] if effective(spec, e) <= on and e["id"] not in applied and e["key"] not in present]


def effective(spec: dict, entry: dict) -> date:
    return date.fromisoformat(entry.get("effective") or spec["effective"])


def text(root: Path, entry: dict) -> str:
    """The reviewed text of an entry's file, normalised as the loader reads it; stops, naming the entry, when it is not the
    text that was reviewed."""
    path = (Path(root) / entry["file"]).resolve()
    if Path(root).resolve() not in path.parents or not path.is_file():
        raise FileNotFoundError(f"Addition {entry['id']} ({entry['key']}) names a file the knowledge base does not hold: {entry['file']}")
    body = path.read_bytes().decode("utf-8-sig").replace("\r\n", "\n").strip()
    if hashlib.sha256(body.encode("utf-8")).hexdigest() != entry["sha256"]:
        raise ValueError(f"Addition {entry['id']} ({entry['key']}): {entry['file']} is not the text that was reviewed (its hash "
                         f"differs from the one {FILE} records), so no version compiles until it is reviewed again")
    return body


def document_entry(entry: dict, effective: date) -> dict:
    """The manifest entry an addition becomes (the compiler names its version)."""
    return {"key": entry["key"], "file": entry["file"], "heading": entry["heading"], "owner": entry["owner"],
            "status": entry["status"], "stages": list(entry["stages"]), "provenance": entry["provenance"],
            "effective_date": effective, "review_interval_days": int(entry["review_interval_days"])}
