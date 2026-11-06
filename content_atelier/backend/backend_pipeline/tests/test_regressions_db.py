"""E.B3's brief regression cases on the product's own path (migrated database, fake providers): a Gate 2 section edit
keeps every untouched value byte for byte, and a line a person approved survives a later revision word for word until
an instruction names it. The card cases run on every configuration's samples (test_regressions.py, test_evaluation.py)."""
from __future__ import annotations

from backend_pipeline.briefs import gate_two
from backend_pipeline.tests.platform_db import APPROVER, platform_setup, platform_url  # noqa: F401 (fixtures)
from backend_pipeline.tests.test_brief_v2_db import revised_child, v2  # noqa: F401 (fixture)
from evaluation import regressions


def test_a_section_edit_and_a_revision_pass_the_brief_regression_cases(v2):  # noqa: F811
    repo, provider, _, row, _, _, _ = v2
    before = row["content_body"]["document"]
    approved = before["body"]["wia_perspective"] + " We read the first reply before we touch the ads."
    edited = gate_two.edit(repo, row["brief_id"], row["content_hash"], {"wia_perspective": approved}, APPROVER)
    after = gate_two.get(repo, edited["brief_id"], APPROVER)["content_body"]["document"]
    assert regressions.local_edit_findings(before, after, ["body.wia_perspective"]) == []
    assert regressions.local_edit_findings(before, after, []) == ["body.wia_perspective: changed outside the edit"]

    gate_two.revise(repo, edited["brief_id"], edited["content_hash"], "Tighten the carousel", APPROVER, "synthetic")
    child = revised_child(repo, provider, edited["brief_id"])
    assert regressions.approved_line_findings([approved], child["content_body"]["document"]) == []
    # Naming the section releases it (Phase 5); the case then reports the line as lost, as it should.
    gate_two.revise(repo, child["brief_id"], child["content_hash"], "Rewrite the WIA perspective in plainer words", APPROVER,
                    "synthetic")
    released = revised_child(repo, provider, child["brief_id"])
    assert regressions.approved_line_findings([approved], released["content_body"]["document"])
