"""E.B3: WIA's notes of 13 and 20 October as the judge's labelled set, a diagnostic never the measure. The recorded judge output
is scored offline; the pairwise judge's run is counted (dry), never sent, in tests. The set lives in research/ (R48); the
tests that read it skip when it is not checked out."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from evaluation import judge, wia_notes

present = pytest.mark.skipif(not wia_notes.LABELS.is_file(), reason="research/judge-labels is not checked out")


@present
def test_the_set_holds_every_note_and_scores_only_the_ones_with_a_text():
    spec = wia_notes.load()
    ids = {label["id"] for label in spec["labels"]}
    assert {f"W{i}" for i in (1, 2, 3, 4, 5, 6, 7)} | {f"W{i}" for i in range(9, 14)} <= ids and {"O13-1", "O13-2"} <= ids
    scored = wia_notes.scored(spec)
    assert all(label["shown"] and label["verdict"] in ("pass", "fail") for label in scored)
    assert not any(label["id"] in {"W1", "W9", "W10", "W11", "W12", "W13"} for label in scored), "process notes are kept, not scored"
    assert sum(label["verdict"] == "fail" for label in scored) == 9


@present
def test_the_recorded_blind_review_caught_none_of_her_failures():
    result = wia_notes.report()
    blind = result["recorded"][0]
    assert blind["her_failures_caught"]["agree"] == 0 and blind["her_failures_caught"]["of"] == 7
    assert blind["her_passes_kept"] == judge.share(4, 4)
    assert blind["missed"] == ["W3", "W4", "W5", "W6", "W7", "W8-cover", "W8-screen2"]
    assert blind["labels_not_judged"] == ["O13-1", "O13-2"], "it never saw the 13 October packs"


def test_a_recorded_verdict_for_an_unknown_label_is_refused():
    spec = {"version": "x", "labels": [{"id": "A", "kind": "specific", "verdict": "fail", "scored": True, "shown": "What changed?"}]}
    assert wia_notes.score_recorded(spec, {"judge": "j", "source": "s", "verdicts": {"A": "fail"}})["her_failures_caught"]["agree"] == 1
    with pytest.raises(ValueError, match="does not hold"):
        wia_notes.score_recorded(spec, {"judge": "j", "source": "s", "verdicts": {"B": "pass"}})


@present
def test_her_corrections_are_pairs_the_judge_should_decide_for_her_and_a_paid_run_is_only_counted(monkeypatch):
    spec = wia_notes.load()
    pairs = wia_notes.pairs(spec)
    assert [p.label_ids[0] for p in pairs] == ["W5", "W6", "W7", "W8-screen2", "O13-1", "O13-2"]
    assert all(p.preferred == p.y.id and p.y.id.endswith(":whitney") for p in pairs)
    kb = SimpleNamespace(text="WIA reference text.", version="test", sha256="0")
    monkeypatch.setattr(judge, "dispatch", lambda **kw: (_ for _ in ()).throw(AssertionError("no call in tests")))
    dry = wia_notes.measure(spec, mode="dry", context="kb", kb=kb)
    assert dry["dry"] and dry["calls"] == 12 and dry["judge"]["model"] == "openai/gpt-6.1-sol"
    assert "plan create" in dry["plan_command"]
    # The shown text was written with Claude: a Claude judge is refused (K45).
    with pytest.raises(ValueError, match="same family"):
        wia_notes.measure(spec, model="anthropic/claude-sonnet-5.5", mode="dry", context="kb", kb=kb)
