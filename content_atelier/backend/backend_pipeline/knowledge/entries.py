"""Reviewed knowledge-base entries for version 9 (E.B25 (i), (j)), entered once through the approver path (L.F2).

Two documents change in version 9 by their items, not by text pasted beside them, because the compiler renders both from
the store and the assembly service re-renders the offer sheet from the items valid on the run date:

- **Document 05, the offer sheet**, gains each offer's approved descriptors and the insider-term glossary. Both are derived
  here from the files the first-touch and asset checks read (`offer-descriptors.json`, `insider-terms.json`), so the prose
  the writer reads and the checks that judge its copy never disagree: a term or descriptor added to those files reaches
  document 05 the next time this runs.
- **Document 09, the format guide**, gains the first-touch rules (plan section 4.3, R59) in general terms with Whitney's own
  published subject lines and covers as exemplars, and its carousel length line is reconciled with section 4.3. These are
  the engineer's reviewed entries in `reviewed-entries.json` (D12, D21).

`apply` (`storage_cli context-entries-apply`) enters each one with its reason, valid from the list's date, idempotently (a
second run changes nothing; a changed entry is entered as a new version of its key). An edit names the confirmed key it
replaces and only the fields it changes. Week 2 text and WIA's 20 October corrections never appear here (D28): they are
the checks' test cases.
"""
from __future__ import annotations

import hashlib
import json
from datetime import date, timedelta
from pathlib import Path

from ..config import BACKEND_ROOT
from . import items, review

ROOT = BACKEND_ROOT / "knowledge_base"
FILE = "reviewed-entries.json"
DESCRIPTORS = "offer-descriptors.json"
TERMS = "insider-terms.json"


def _read(root: Path, name: str) -> dict:
    return json.loads((Path(root) / name).read_text(encoding="utf-8"))


def derived(root: Path = ROOT) -> list[dict]:
    """Document 05's descriptor and glossary entries, from the files the checks read."""
    out = []
    for offer in _read(root, DESCRIPTORS)["offers"]:
        named = "; or ".join(f'"{d}"' for d in offer["descriptors"])
        out.append({"id": f"descriptor:{offer['offer']}", "kind": "offer", "name": f"descriptor {offer['offer']}",
                    "body": {"name": offer["offer"], "section": "descriptor",
                             "description": f"Name it with its descriptor: {named}",
                             "ownership": offer["who_does_what"]},
                    "reason": f"The approved descriptors of {offer['offer']} the asset checks read ({DESCRIPTORS})"})
    for term in _read(root, TERMS)["terms"]:
        out.append({"id": f"insider_term:{term['term']}", "kind": "offer", "name": f"insider term {term['term']}",
                    "body": {"name": term["term"], "section": "insider_term",
                             "description": f"Never in first-touch text. In a script, an email or a caption at most once, "
                                            f"explained: {term['plain']}."},
                    "reason": f"An insider term the first-touch check reads ({TERMS})"})
    return out


def load(root: Path = ROOT) -> dict:
    spec = _read(root, FILE)
    date.fromisoformat(spec["valid_from"])
    listed = [*spec["entries"], *derived(root)]
    ids = [e["id"] for e in listed]
    if len(ids) != len(set(ids)):
        raise ValueError(f"{FILE}: every entry needs its own id")
    for e in listed:
        if not (e.get("reason") or "").strip() or e["kind"] not in items.KINDS or not (e.get("edit") or e.get("name")):
            raise ValueError(f"{FILE}: entry {e['id']} needs a kind, a name or the key it edits, and a reason")
        if not e.get("edit"):
            items.validate_body(e["kind"], e["body"])
    return {**spec, "entries": listed}


def _fingerprint(entry: dict) -> str:
    return hashlib.sha256(json.dumps(entry, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()[:12]


def apply(conn, settings, actor: str, *, root: Path = ROOT) -> dict:
    """Enter every reviewed entry once (an approver, recorded as reviewer; the delegated engineer as author)."""
    review.require(settings, actor)
    spec = load(root)
    start = date.fromisoformat(spec["valid_from"])
    entered, repeated, missing = [], 0, []
    for e in spec["entries"]:
        key = e.get("edit") or items.key_for(e["kind"], e["name"])
        idempotency = f"reviewed-entries:{e['id']}:{_fingerprint(e)}"
        body = e.get("body")
        if e.get("edit"):
            row = next((r for r in items.items_valid_at(conn, None, start - timedelta(days=1), kinds=(e["kind"],))
                        if r["key"] == key), None)
            if row is None and not conn.execute("""SELECT 1 FROM brand_kit_items WHERE source_kind='approver_entry'
                    AND source_ref=%s""", (f"entry:{actor}:{idempotency}",)).fetchone():
                missing.append(key)
                continue
            body = {**(row["body"] if row else {}), **e["body_update"]}
        result = review.enter(conn, settings, actor, kind=e["kind"], key=key, body=body, valid_from=start,
                              author=spec["author"], reason=e["reason"], today=start, idempotency_key=idempotency)
        if result.get("repeated"):
            repeated += 1
        else:
            entered.append(key)
    return {"entries": len(spec["entries"]), "entered": len(entered), "already_entered": repeated, "missing": missing,
            "valid_from": spec["valid_from"]}
