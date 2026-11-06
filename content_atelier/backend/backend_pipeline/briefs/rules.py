"""The rules a brief is re-checked with at Gate 2: those of the knowledge-base version it was written with (E.B15).

A v2 or v3 brief pins the knowledge-base version its writer used (`provenance.pinned_inputs.knowledge_base.version`).
Gate 2's checks, and every re-check after a person's edit, answer, clearance or CTA confirmation, use that version's
rejection rules and lint patterns, never the version in force or the files as they are now:

1. the store: the version as published or compiled into `brand_kit_docs` (`load_published`), with the patterns its
   manifest records;
2. the folder: `knowledge_base/archive/<version>/`, or `knowledge_base/` itself while it still is that version, with the
   patterns its manifest names (hash-checked) or, for a version kept by hand before E.B11 (2), the patterns file beside it.

A version that records no patterns has none to apply. A pinned version found in neither place is a blocking finding:
its rules cannot be re-checked, and the rules of another version are no substitute.
"""
from __future__ import annotations

import json
from pathlib import Path

from ..cycle.verification import knowledge_root, load_rules, store_rules


def pinned_version(provenance: dict | None) -> str | None:
    return (((provenance or {}).get("pinned_inputs") or {}).get("knowledge_base") or {}).get("version")


def _from_store(conn, version: str) -> tuple[bool, list[dict] | None]:
    """(whether the store holds the version, its patterns or None)."""
    if conn is None or not conn.execute("SELECT to_regclass('public.settings') AS t").fetchone()["t"]:
        return False, None
    from ..knowledge_base import load_published
    try:
        kb = load_published(conn, version)
    except ValueError:
        return False, None
    return True, kb.rule_patterns


def _from_folder(version: str, root: Path) -> tuple[bool, list[dict] | None]:
    """(whether a folder holds the version, its patterns or None): the archive first, then the knowledge base itself."""
    from ..knowledge_base import KnowledgeBaseManifest, _rule_patterns
    for folder in (root / "archive" / version, root):
        path = folder / "manifest.json"
        if not path.is_file():
            continue
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
        if raw.get("knowledge_base_version") != version:
            continue
        patterns, _ = _rule_patterns(folder, KnowledgeBaseManifest.model_validate(raw))
        if patterns is None and (folder / "rejection-rules.patterns.json").is_file():
            patterns = json.loads((folder / "rejection-rules.patterns.json").read_text(encoding="utf-8"))["rules"]
        return True, patterns
    return False, None


def version_patterns(conn, version: str, root: Path | None = None) -> list[dict]:
    """The lint patterns of one knowledge-base version: the store's, else the archive folder's. Raises LookupError when
    neither holds the version."""
    in_store, patterns = _from_store(conn, version)
    if patterns is not None:
        return patterns
    in_folder, patterns = _from_folder(version, Path(root or knowledge_root()))
    if patterns is not None:
        return patterns
    if in_store or in_folder:
        return []  # the version records no patterns
    raise LookupError(version)


def pinned_rules(conn, provenance: dict | None, stage: str = "brief") -> tuple[list[dict], str | None]:
    """(the rules of the brief's pinned version, None), or ([], the blocking message) when they cannot be loaded.

    A brief that pins no version (none the product writes; constructed rows) is checked with the rules in force."""
    version = pinned_version(provenance)
    if not version:
        return (store_rules(conn, knowledge_root(), stage) if conn is not None else load_rules(knowledge_root(), stage)), None
    try:
        return load_rules(knowledge_root(), stage, patterns=version_patterns(conn, version)), None
    except LookupError:
        problem = "is in neither the store nor knowledge_base/archive/"
    except (ValueError, FileNotFoundError) as error:
        problem = f"could not be read ({error})"
    return [], (f"The rules of knowledge base {version}, which this brief was written with, {problem}: Gate 2 cannot re-check "
                "them, and another version's rules are no substitute. Restore that version (publish it, or keep it under "
                "knowledge_base/archive/)")
