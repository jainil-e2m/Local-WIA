"""E.B25 (d), (e): the assembly service keeps a stage's prefix within its budget by dropping whole documents from the
bottom of a recorded priority list, never the ones that must stay, and records what it did; the editing guide joins a
compiled version, once, from the committed additions list. Files only; the database path is in
test_context_closeout_db.py."""
from __future__ import annotations

import hashlib
import json
import shutil
from datetime import date

import pytest

from backend_pipeline.config import BACKEND_ROOT
from backend_pipeline.knowledge import additions, assembly
from backend_pipeline.knowledge_base import load_knowledge_base
from backend_pipeline.tests.test_held_out import V8, V7


def test_the_strategist_prefix_drops_from_the_bottom_of_the_priority_list_and_records_it(monkeypatch):
    monkeypatch.delenv("ATELIER_CONTEXT_PREFIX_TOKENS", raising=False)
    full = load_knowledge_base(V8, stage="strategist")
    kb = assembly.assemble("strategist", root=V8)
    record = kb.context["prefix_budget"]
    # Version 8's strategist prefix is 38,525 tokens; without the workflow and the Accelerator workbook it is still 30,213,
    # so the results register leaves too (priority v2 keeps the process catalogue: how WIA works, rubric criterion 1).
    assert record == {"priority": "prefix-priority.v2", "budget": 30000, "tokens_before": 38525, "tokens_after": 28863,
                      "dropped": ["content_workflow", "accelerator_strategy", "results_register"], "over_budget": False}
    assert assembly.tokens(full.text) == 38525 and assembly.tokens(kb.text) == 28863
    assert [d.entry.key for d in kb.documents] == [d.entry.key for d in full.documents if d.entry.key not in record["dropped"]]
    assert kb.refs()["context"]["prefix_budget"] == record and "editing_guide" in [d["key"] for d in kb.refs()["documents"]]
    assert kb.text == assembly._rebuild(full, kb.documents), "the kept documents byte for byte, in their order"


def test_the_order_is_the_recorded_list_and_the_protected_documents_never_leave(monkeypatch):
    monkeypatch.setenv("ATELIER_CONTEXT_PREFIX_TOKENS", "1")
    kb = assembly.assemble("brief", root=V8)
    record = kb.context["prefix_budget"]
    present = {d.entry.key for d in load_knowledge_base(V8, stage="brief").documents}
    expected = [k for k in reversed(assembly.PREFIX_PRIORITY) if k not in assembly.NEVER_DROPPED and k in present]
    assert record["dropped"] == expected and record["over_budget"] is True
    kept = {d.entry.key for d in kb.documents}
    assert assembly.NEVER_DROPPED <= kept and "rejection_rules" in kept
    # A document the list does not name (the brief's format guide and CTA catalogue) is never dropped either.
    assert {"format_guide", "cta_catalogue"} <= kept and kept == present - set(expected)
    assert assembly.PREFIX_PRIORITY.index("rejection_rules") == 0 and assembly.PREFIX_PRIORITY_VERSION == "prefix-priority.v2"


def test_a_prefix_within_its_budget_is_untouched_and_records_nothing_on_files(monkeypatch):
    monkeypatch.delenv("ATELIER_CONTEXT_PREFIX_TOKENS", raising=False)
    for stage in ("verifier", "extraction"):
        kb = assembly.assemble(stage, root=V8)
        assert kb.context is None and kb.text == load_knowledge_base(V8, stage=stage).text
    monkeypatch.setenv("ATELIER_CONTEXT_PREFIX_TOKENS", "100000")
    kb = assembly.assemble("strategist", root=V8)
    assert kb.context is None and kb.refs() == load_knowledge_base(V8, stage="strategist").refs()


def test_the_committed_additions_list_names_the_reviewed_editing_guide():
    spec, _ = additions.load(BACKEND_ROOT / "knowledge_base")
    # The first entry; version 9's documents 18 and 19 follow it from 22 October (test_kb9.py).
    entry = spec["entries"][0]
    assert [e["id"] for e in spec["entries"]] == ["A01", "A02", "A03"]
    assert entry["key"] == "editing_guide" and entry["stages"] == ["strategist", "brief"] and entry["status"] == "confirmed"
    assert entry["owner"] == "Whitney Hodges (her corrections, derived from the ChatGPT export, E.B25 (e))"
    assert entry["provenance"]["model_written"] is True and additions.effective(spec, entry) == date(2026, 10, 20)
    text = additions.text(BACKEND_ROOT / "knowledge_base", entry)
    assert text.startswith("How Whitney edits:") and "## 6. Refine, don't replace" in text
    assert additions.due(spec, date(2026, 10, 19), set(), set()) == []
    assert additions.due(spec, date(2026, 10, 20), set(), set()) == [entry]
    assert entry not in additions.due(spec, date(2026, 11, 1), {"A01"}, set()), "applied once"
    assert entry not in additions.due(spec, date(2026, 11, 1), set(), {"editing_guide"}), "never over a document the base has"
    assert entry["key"] not in {d.entry.key for d in load_knowledge_base(V7).documents}, "version 7 lacks it"


def test_a_changed_or_incomplete_addition_is_refused(tmp_path):
    root = tmp_path / "kb"
    root.mkdir()
    shutil.copy(BACKEND_ROOT / "knowledge_base" / additions.FILE, root / additions.FILE)
    spec, _ = additions.load(BACKEND_ROOT / "knowledge_base")
    with pytest.raises(FileNotFoundError, match="A01"):
        additions.text(root, spec["entries"][0])
    (root / "17-editing-guide.md").write_text("How Whitney edits: something else.\n", encoding="utf-8")
    with pytest.raises(ValueError, match=r"Addition A01 \(editing_guide\).*not the text that was reviewed"):
        additions.text(root, spec["entries"][0])
    (root / "17-editing-guide.md").write_text("Reviewed.\r\n", encoding="utf-8", newline="")
    entry = {**spec["entries"][0], "sha256": hashlib.sha256(b"Reviewed.").hexdigest()}
    assert additions.text(root, entry) == "Reviewed.", "line endings and outer whitespace aside"
    broken = {**spec, "entries": [{k: v for k, v in spec["entries"][0].items() if k != "sha256"}]}
    (root / additions.FILE).write_text(json.dumps(broken), encoding="utf-8")
    with pytest.raises(ValueError, match="entry A01 needs"):
        additions.load(root)
