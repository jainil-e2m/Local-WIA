"""E.B25 (c): the superseded lines of the supplied documents 01 to 03, applied by exact line (no database)."""
from __future__ import annotations

import json
from collections import Counter
from datetime import date

import pytest

from backend_pipeline.config import BACKEND_ROOT
from backend_pipeline.knowledge import supersessions as s
from backend_pipeline.knowledge_base import load_knowledge_base

ROOT = BACKEND_ROOT / "knowledge_base"


def entry(**changes):
    return {"id": "X1", "document": "content_strategy", "line": "- Old line", "occurrences": 1, "ruling": "R-6",
            "action": "remove", "note": "A note", **changes}


def test_remove_annotate_and_replace_by_exact_line():
    text = "# Title\n- Old line   \n- Keep\n- Old line\nLast"
    assert s.apply(text, [entry(occurrences=2)]) == "# Title\n- Keep\nLast", "every occurrence, trailing spaces aside"
    assert s.apply("- Keep\n- Old line", [entry(action="annotate", note="Ruling R-9: soft CTA")]) == "- Keep\n- Old line [Ruling R-9: soft CTA]"
    assert s.apply("- Old line", [entry(action="replace", replacement="- New line", note="R-14")]) == "- New line [R-14]"
    # A line that is not there, or not as often as the entry says, stops the compile and names the entry.
    with pytest.raises(ValueError, match=r"X1 \(content_strategy, R-6\) expects 1 line.*found 0"):
        s.apply("- Old line, edited", [entry()])
    with pytest.raises(ValueError, match="expects 1 line.*found 2"):
        s.apply("- Old line\n- Old line", [entry()])
    assert s.apply("- Old line is longer", [entry(line="- Old line is longer")]) == "", "matched whole, never as a prefix"
    with pytest.raises(ValueError, match="found 0"):
        s.apply("- Old line is longer", [entry()])


def test_entries_are_due_from_their_date_and_once():
    spec = {"effective": "2026-10-20", "entries": [entry(), entry(id="X2", effective="2026-11-01")]}
    assert s.due(spec, date(2026, 10, 19)) == []
    assert [e["id"] for e in s.due(spec, date(2026, 10, 20))] == ["X1"]
    assert [e["id"] for e in s.due(spec, date(2026, 11, 2), {"X1"})] == ["X2"], "an entry the base applied is not applied again"
    assert s.due(None, date(2026, 11, 2)) == []


def test_the_committed_list_is_the_engineers_decision_and_applies_to_the_supplied_documents(tmp_path):
    spec, digest = s.load(ROOT)
    assert spec["effective"] == "2026-10-20" and len(digest) == 64
    entries = spec["entries"]
    assert Counter(e["action"] for e in entries) == {"remove": 11, "annotate": 14, "replace": 1}
    assert s.counts(entries)["remove_lines"] == 14
    assert {e["ruling"] for e in entries} == {"R-1", "R-3, R-4", "R-6", "R-7", "R-8", "R-9", "R-10", "R-12", "R-13", "R-14", "R-15", "R-16"}
    # The supplied originals as WIA gave them: unchanged up to version 6 (archived); version 7 is the list applied.
    from backend_pipeline.tests.test_held_out import V6
    kb = load_knowledge_base(V6)
    for key in sorted(s.DOCUMENTS):
        original = kb.document(key).text
        mine = [e for e in entries if e["document"] == key]
        after = s.apply(original, mine)  # every line is found exactly as often as its entry says
        for e in mine:
            # Each line the list names sits at the line numbers it gives in the committed original.
            assert [original.split("\n")[n - 1].rstrip() for n in e["lines"]] == [e["line"]] * e["occurrences"], e["id"]
            if e["action"] == "remove":
                assert e["line"] not in after.split("\n"), e["id"]
            else:
                assert f"[{e['note']}]" in after, e["id"]
        # The audience's own history stays (03:14, 03:181, 03:364).
        if key == "accelerator_strategy":
            for kept in ("Tried DIY Google Ads.", "- Trying to DIY too many things", "- You’ve taken a DIY ads course"):
                assert kept in after
    after = s.apply(kb.document("content_strategy").text, [e for e in entries if e["document"] == "content_strategy"])
    assert "- We are an all-female, Millennial + Gen Z team. [" in after and "20s and 30s" not in after
    assert "you can’t DIY" not in after and "you can't DIY" not in after and "beautiful ceiling" not in after
    # A malformed list is refused when it is read.
    bad = tmp_path / s.FILE
    bad.write_text(json.dumps({"effective": "2026-10-20", "entries": [entry(action="replace")]}), encoding="utf-8")
    with pytest.raises(ValueError, match="X1 needs"):
        s.load(tmp_path)
    assert s.load(tmp_path / "none") == (None, None)
