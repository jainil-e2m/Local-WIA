"""E.X7: rubric 2.3a exists in code as text with a version; the Gate 1 form and E.B3's judge read it from gates/rubric.py."""
from __future__ import annotations

import pytest

from backend_pipeline.config import BACKEND_ROOT
from backend_pipeline.gates import rubric

PLAN = BACKEND_ROOT / "docs" / "Content-Atelier-Implementation-Plan-Brief-Generation.md"


def test_the_rubric_is_the_confirmed_text_under_its_version():
    # Section 2.3a is the confirmed text (D12); each criterion and the anchors are carried word for word.
    section = PLAN.read_text(encoding="utf-8").split("### 2.3a Review rubric v1", 1)[1].split("### 2.4", 1)[0]
    for i, (_key, name, text) in enumerate(rubric.CRITERIA, 1):
        assert f"{i}. **{name}.** {text}" in section, name
    assert "(" + "; ".join(f"{n} = {a}" for n, a in rubric.ANCHORS.items()) + ")" in section
    assert rubric.VERSION == "rubric-2.3a.v1" and rubric.KEYS[0] == "wia_is_the_subject" and rubric.KEYS[3] == "worth_attention"
    # A change to the text is a new version (section 2.3a): this pin fails on an edit that keeps the version.
    assert rubric.TEXT_SHA256 == "d669ed20831e02a96f3f176b14f177c6c5ca79298fa74e29a74a26aa94970429"
    form = rubric.form()
    assert form["text"] == rubric.TEXT and [c["key"] for c in form["criteria"]] == list(rubric.KEYS)
    assert form["scale"] == [1, 2, 3, 4, 5] and form["version"] == rubric.VERSION


def test_ratings_cover_every_criterion_from_1_to_5_against_the_version_shown():
    values = dict.fromkeys(rubric.KEYS, 3) | {"wia_is_the_subject": 1, "sounds_like_whitney": 5}
    rated = rubric.ratings(values, rubric.VERSION)
    assert rated == {"version": rubric.VERSION, "text_sha256": rubric.TEXT_SHA256, "criteria": values, "overall": 3.0}
    assert rubric.ratings(None) is None and rubric.ratings({}) is None
    with pytest.raises(ValueError, match="missing: audience"):
        rubric.ratings({k: v for k, v in values.items() if k != "audience"})
    with pytest.raises(ValueError, match="unknown: tone"):
        rubric.ratings({**values, "tone": 3})
    for bad in (0, 6, 2.5, True, "3"):
        with pytest.raises(ValueError, match="whole number"):
            rubric.ratings({**values, "audience": bad})
    with pytest.raises(ValueError, match="reload"):
        rubric.ratings(values, "rubric-2.3a.v0")
