"""NP.X5 offline: the shape of a labelled case file and how a check's statements are scored against it. Invented text only
(R48); the real cases live in research/packs-2026-10/check-cases.json and are read here only for their shape when present."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend_pipeline.packs import check_cases
from backend_pipeline.tests.platform_db import platform_setup, platform_url  # noqa: F401 (fixtures)
from backend_pipeline.tests.test_brief_v4_db import v4  # noqa: F401 (fixture)
from backend_pipeline.tests.test_packs_v2_service_db import ready  # noqa: F401 (fixture)

CASES = [{"case_id": "c1", "source": "a reading", "piece": "carousel", "sentence": "We check every page we ever build this way.",
          "expected": "unsupported", "why": "one page widened into a practice"},
         {"case_id": "c2", "source": "a reading", "piece": "email", "sentence": "A client had that reaction to our ads.",
          "expected": "guardrail", "why": "implies a kept-out judgement"}]


def test_a_case_is_caught_only_by_a_flag_on_its_own_sentence_and_piece():
    statements = [{"piece": "carousel", "text": "We check every page we ever build this way.", "verdict": "unsupported", "in_moment": None},
                  {"piece": "email", "text": "A client had that reaction to our ads.", "verdict": "supported", "in_moment": None}]
    result = check_cases.score(CASES, statements)
    assert [c["case_id"] for c in result["caught"]] == ["c1"] and [c["case_id"] for c in result["missed"]] == ["c2"]
    moved = [{"piece": "email", "text": "A client had that reaction to our ads.", "verdict": "supported", "in_moment": False}]
    assert [c["case_id"] for c in check_cases.score(CASES, moved)["caught"]] == ["c2"], "a quote out of its moment counts as a flag"
    elsewhere = [{"piece": "reel_1", "text": "A client had that reaction to our ads.", "verdict": "guardrail", "in_moment": None}]
    assert check_cases.score(CASES[1:], elsewhere)["missed"], "a flag in another piece does not catch the case"


def test_a_case_file_is_checked_for_its_fields_and_verdicts(tmp_path):
    good = tmp_path / "cases.json"
    good.write_text(json.dumps(CASES), encoding="utf-8")
    assert len(check_cases.load(good)) == 2
    for broken in ([{**CASES[0], "expected": "supported"}], [{**CASES[0], "piece": "reel_9"}], [CASES[0], CASES[0]],
                   [{k: v for k, v in CASES[0].items() if k != "sentence"}]):
        bad = tmp_path / "bad.json"
        bad.write_text(json.dumps(broken), encoding="utf-8")
        with pytest.raises(ValueError):
            check_cases.load(bad)


def test_the_committed_case_file_keeps_its_shape():
    path = Path(__file__).resolve().parents[3] / "research" / "packs-2026-10" / "check-cases.json"
    if not path.exists():
        pytest.skip("research/packs-2026-10/check-cases.json is not in this checkout")
    cases = check_cases.load(path)
    assert {c["case_id"] for c in cases} >= {"np5-pair-02", "np5-pair-06"}


def test_a_week_s_person_made_pack_edits_are_listed_as_candidate_cases(ready):  # noqa: F811
    """On the migrated database: an edit of a pack line is listed once, with the line before and after and who made it."""
    from backend_pipeline.packs import versions, views
    from backend_pipeline.packs.contracts_v2 import PackEdit
    from backend_pipeline.tests.platform_db import EDITOR
    from backend_pipeline.tests.test_packs_v2_service_db import made
    repo, row, _, _ = ready
    pack_id = made(repo, row)
    pack = views.detail(repo, pack_id, EDITOR)
    before = next(p for p in pack["pieces"] if p["key"] == "carousel")["content"]["slides"][1]["text"]
    saved = versions.edit(repo, pack_id, "carousel", PackEdit(request_id="case-edit-1", expected_manifest_hash=pack["manifest_hash"],
                                                              changes={"slides[1].text": "A line a person corrected."}), EDITOR)
    with repo.connection() as conn:
        (found,) = check_cases.candidates(conn, row["week_id"])
    assert found["pack_id"] == saved["pack_id"] and found["piece"] == "carousel" and found["path"] == "slides[1].text"
    assert found["before"] == before and found["after"] == "A line a person corrected." and found["by"] == EDITOR
