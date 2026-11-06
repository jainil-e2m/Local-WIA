"""Offline checks of Gate 2's field paths and line locks (5.F1, 5.F4, 5.F5), the refresh writer v4.1 and its render
variables (5.B6, interface 1), attested facts in the v3 ledger (5.B7, R57) and the named blockers (5.F2)."""
from __future__ import annotations

from pathlib import Path

import pytest

from backend_pipeline import settings_store
from backend_pipeline.briefs import ledger_v3, paths
from backend_pipeline.briefs.contracts_v3 import SCHEMA_V3
from backend_pipeline.briefs.gate_two import plain_blocker
from backend_pipeline.briefs.runtime import RENDERED_WRITERS, render_writer, system
from backend_pipeline.briefs.workflow import writer_for
from backend_pipeline.storage_config import StorageSettings
from backend_pipeline.tests.brief_v3_fixtures import v3_body

TEMPLATES = Path(__file__).resolve().parents[1] / "prompt_templates"


def body():
    return v3_body({"approved_angle": {"title": "T", "core_perspective": "P"}, "evidence": [{"excerpt": "Owner: How fast do we reply?"}]})


def test_paths_parse_read_write_and_walk_the_body():
    b = body()
    assert paths.parse("format_plan.reels[0].cover_text") == ["format_plan", "reels", 0, "cover_text"]
    assert paths.canonical("format_plan.carousel.slides[3].text") == "format_plan.carousel.slides[3].text"
    for bad in ("", "a..b", "a[x]", "a.b]", "1a"):
        with pytest.raises(ValueError):
            paths.parse(bad)
    assert paths.get(b, "format_plan.email.subject_options[1]") == "Before we touch your ads"
    with pytest.raises(ValueError, match="no field"):
        paths.get(b, "format_plan.reels[3].cover_text")
    changed = paths.put(b, "format_plan.email.preview", "New")
    assert changed["format_plan"]["email"]["preview"] == "New" and b["format_plan"]["email"]["preview"] != "New", "a copy"
    walked = dict(paths.leaves(b))
    assert walked["format_plan.carousel.slides[6].text"].startswith("Slide text") and walked["narrative_outline.hooks[1].style"] == "question"
    assert paths.overlaps("format_plan.email", "format_plan.email.subject_options[0]")
    assert not paths.overlaps("format_plan.email.preview", "format_plan.email.subject_options[0]")


def test_an_edit_locks_the_lines_it_changed_even_when_a_whole_section_is_sent():
    b = body()
    allowed = {"format_plan", "wia_perspective"}
    _, changed = paths.apply(b, {"format_plan.email.subject_options[0]": "Mine"}, allowed)
    assert changed == ["format_plan.email.subject_options[0]"]
    section = paths.put(b, "format_plan.carousel.slides[2].text", "Edited slide")["format_plan"]
    _, changed = paths.apply(b, {"format_plan": section}, allowed)
    assert changed == ["format_plan.carousel.slides[2].text"], "the screen of 20 October sent whole sections"
    with pytest.raises(ValueError, match="not a field a person edits"):
        paths.apply(b, {"claims": []}, allowed)
    assert paths.merge_locks(["format_plan"], ["wia_perspective", "format_plan"]) == ["format_plan", "wia_perspective"]


def test_restore_puts_back_a_locked_line_and_refuses_a_draft_without_its_place():
    parent = paths.put(body(), "format_plan.email.subject_options[0]", "Mine")
    draft = paths.put(paths.put(body(), "format_plan.email.subject_options[0]", "Theirs"), "format_plan.email.preview", "New preview")
    kept, restored = paths.restore(parent, draft, ["format_plan.email.subject_options[0]"])
    assert kept["format_plan"]["email"]["subject_options"][0] == "Mine" and kept["format_plan"]["email"]["preview"] == "New preview"
    assert restored == [{"path": "format_plan.email.subject_options[0]", "draft": "Theirs"}]
    renumbered = paths.put(draft, "format_plan.carousel.slides[2].number", 9)
    with pytest.raises(ValueError, match="no place for the locked line"):
        paths.restore(parent, renumbered, ["format_plan.carousel.slides[2].text"])
    with pytest.raises(ValueError, match="no place"):
        paths.restore(parent, {**draft, "format_plan": {**draft["format_plan"], "reels": []}}, ["format_plan.reels[0].script"])
    run = {"input_refs": {"instructions": "rewrite the wia_perspective", "unlock": ["format_plan.reels[0].cover_text"]}}
    parent_row = {"content_body": {"review": {"locked_fields": ["wia_perspective", "format_plan.reels[0].cover_text", "format_plan.email.preview"]}}}
    assert paths.revision_locks(run, parent_row) == ["format_plan.email.preview"], "released by name (a section) or explicitly"
    assert paths.locked_values(parent, ["format_plan.email.subject_options[0]", "format_plan.reels[5].script"]) == [
        {"path": "format_plan.email.subject_options[0]", "value": "Mine"}]


def test_writer_v4_1_is_v4_with_the_two_revision_blocks():
    v4 = (TEMPLATES / "brief_write.v4.md").read_text(encoding="utf-8")
    v41 = (TEMPLATES / "brief_write.v4.1.md").read_text(encoding="utf-8")
    assert "{{#revision_instructions}}" in v41 and "{{#locked_fields}}" in v41 and "{{" not in v4
    first = system("brief_write", SCHEMA_V3, "KB", "v4.1", {"revision_instructions": "", "locked_fields": []})
    assert "{{" not in first and "This is a refresh" not in first and "Lines a person wrote" not in first
    rendered = render_writer(v41, "Shorter subject lines.", [{"path": "format_plan.email.preview", "value": 'Say "hi"'}])
    assert "Shorter subject lines." in rendered and '- `format_plan.email.preview`: "Say \\"hi\\""' in rendered
    assert render_writer("Hi {{contact.first_name}}", "x", []) == "Hi {{contact.first_name}}", "only its own variables"
    assert system("brief_repair", SCHEMA_V3, "KB", "v4.1") == system("brief_repair", SCHEMA_V3, "KB", "v4")
    assert RENDERED_WRITERS["v4.1"] == "v4"


def test_a_refresh_of_a_v3_brief_uses_writer_v4_1_and_the_setting_accepts_it():
    assert writer_for(StorageSettings(brief_writer="v4"), SCHEMA_V3, revision="brief_x") == "v4.1"
    assert writer_for(StorageSettings(brief_writer="v4"), SCHEMA_V3) == "v4", "first drafts keep the setting"
    assert writer_for(StorageSettings(brief_writer="v4.1"), SCHEMA_V3) == "v4.1"
    settings_store.validate_profile({"settings": {"prompts.profile.brief": "brief_document_v3", "prompts.profile.brief_writer": "v4.1"}})
    with pytest.raises(ValueError):
        settings_store.validate_profile({"settings": {"prompts.profile.brief": "brief_document_v2", "prompts.profile.brief_writer": "v4.1"}})


def test_an_attested_fact_settles_the_line_that_states_it_but_never_a_quote():
    item = {"id": "context_1", "kind": "attested_fact", "author": "approver@example.invalid", "created_at": "2026-10-22T10:00:00+00:00",
            "text": "The client's AI assistant made the changes to the account, not the client herself."}
    line = {"id": "c_1", "field": "supporting_example.scene", "label": "the supporting example",
            "text": "Her AI assistant made the changes to the account."}
    claim = ledger_v3.attest(line, [item])
    assert claim["status"] == "attested" and claim["attested"] == {"kind": "attested_fact", "context_id": "context_1",
                                                                     "by": "approver@example.invalid", "on": "2026-10-22"}
    assert ledger_v3.attest({**line, "text": 'She said "her AI assistant made the changes to the account".'}, [item]) is None
    assert ledger_v3.attest({**line, "text": "Her AI assistant made 40 changes to the account."}, [item]) is None, "a figure it lacks"
    assert ledger_v3.attest({**line, "text": "We plan the calendar before the budget."}, [item]) is None
    assert ledger_v3.attest(line, [{**item, "kind": "context"}]) is None, "a note is not evidence"
    [entry] = ledger_v3.attested_entries([item, {**item, "id": "context_2", "kind": "context"}])
    assert entry["field"] == "context_items" and entry["status"] == "attested" and "approver@example.invalid on 2026-10-22" in entry["note"]
    assert ledger_v3.field_path("format_plan.reels[1].cover_text", None) == "format_plan.reels[0].cover_text"
    assert ledger_v3.field_path("format_plan.carousel.slides[3].text", body()) == "format_plan.carousel.slides[2].text"


@pytest.mark.parametrize("kind,message,title", [
    ("open_question", "Required before-publishing items remain unanswered", "A required question has no answer yet."),
    ("cta_unconfirmed", "The CTA is the writer's proposal; a person confirms it", "The call to action is still the writer's suggestion."),
    ("blocking_finding", "The WIA perspective says \"x\": the call does not support it", "The copy has a problem to fix."),
    ("stale", "A replacement brief exists", "A newer version of this brief exists."),
    ("stale", "Angle packet changed", "The approved card or the call excerpts changed since this brief was written."),
    ("claims_check", "Changed document requires a scoped grounding/differentiation review", "Nobody has recorded a check of the claims in this version yet."),
    ("role", "", "Only an approver can approve this brief."),
])
def test_each_blocker_has_a_name_a_reviewer_reads(kind, message, title):
    item = plain_blocker(kind, message)
    assert item["kind"] == kind and item["title"] == title and item["action"]
    assert (item["detail"] == message) == (kind == "blocking_finding")
    assert "evidence_ab12" not in (plain_blocker("blocking_finding", "Evidence evidence_ab12 is missing")["detail"])


def test_a_miscopied_evidence_id_in_the_grading_is_repaired_only_when_it_is_unambiguous():
    """N2, 23 October: Sonnet graded 47 delivered items but wrote one of the 24-character ids with one character changed, and
    the research stage failed after USD 0.30 of correct grading. One character off from exactly one ungraded delivered id is
    that item's grade, recorded; a wider difference, an id two delivered items are equally near, or one already graded is
    left for the coverage check to refuse."""
    from backend_pipeline.briefs.contracts import Grade
    from backend_pipeline.briefs.workflow import repair_graded_ids

    def grade(evidence_id):
        return Grade(evidence_id=evidence_id, relevant=True, role="support", reason="Useful exact source context")
    delivered = ["ev_bf85af6b3cc4878d4aa1c966", "ev_02967f91ba43c732a5df60b9"]
    graded, repairs = repair_graded_ids([grade("ev_bf85af6b4cc4878d4aa1c966"), grade(delivered[1])], delivered)
    assert [g.evidence_id for g in graded] == delivered
    assert repairs == [{"written": "ev_bf85af6b4cc4878d4aa1c966", "repaired_to": "ev_bf85af6b3cc4878d4aa1c966"}]
    # Two characters off: not repaired.
    graded, repairs = repair_graded_ids([grade("ev_bf85af6b44c4878d4aa1c966"), grade(delivered[1])], delivered)
    assert repairs == [] and graded[0].evidence_id == "ev_bf85af6b44c4878d4aa1c966"
    # Equally near two ungraded delivered ids: ambiguous, not repaired.
    twins = ["ev_000000000000000000000001", "ev_000000000000000000000002"]
    graded, repairs = repair_graded_ids([grade("ev_000000000000000000000003")], twins)
    assert repairs == []
    # The near id is already graded: the stray grade is a duplicate, not a miscopy.
    graded, repairs = repair_graded_ids([grade(delivered[0]), grade("ev_bf85af6b4cc4878d4aa1c966")], delivered[:1])
    assert repairs == []


def test_grades_for_items_never_delivered_or_given_twice_are_dropped_and_the_missing_items_are_named():
    from backend_pipeline.briefs.contracts import Grade
    from backend_pipeline.briefs.workflow import settle_grades

    def grade(evidence_id):
        return Grade(evidence_id=evidence_id, relevant=True, role="support", reason="Useful exact source context")
    kept, missing, dropped = settle_grades([grade("ev_a"), grade("ev_a"), grade("ev_x")], ["ev_a", "ev_b"])
    assert [g.evidence_id for g in kept] == ["ev_a"] and missing == ["ev_b"] and dropped == ["ev_a", "ev_x"]


def test_research_grades_the_items_the_first_answer_missed_in_a_follow_up_call(monkeypatch):
    """NP-7's paid proof (25 October): a grading answer that skipped an item and graded one never delivered failed the research
    stage, and a retry replayed the same saved answer. The missing item is graded in a follow-up call of its own."""
    from contextlib import contextmanager
    from datetime import UTC, datetime
    from types import SimpleNamespace

    from backend_pipeline.briefs import workflow
    from backend_pipeline.briefs.contracts import EvidenceItem, GradeResponse, QueryPlan

    def item(n):
        return EvidenceItem(evidence_id=f"ev_{n}", excerpt=f"An invented passage {n}.", title="A synthetic call", role="support")
    pool = [item(n) for n in range(6)]
    sent = []

    def call(worker, job, run, stage, schema, packet):
        sent.append((stage, packet))
        if stage == "brief_plan":
            return QueryPlan(queries=[{"text": f"query {n}", "purpose": "support"} for n in range(6)])
        ids = [e["evidence_id"] for e in packet["evidence"]]
        if packet.get("ungraded_from_first_answer"):
            return GradeResponse(grades=[{"evidence_id": i, "relevant": True, "role": "support", "reason": "Graded later"} for i in ids], gaps=[])
        graded = ids[1:] + ["ev_never_delivered", ids[1]]
        return GradeResponse(grades=[{"evidence_id": i, "relevant": True, "role": "context", "reason": "Graded first"} for i in graded], gaps=[])

    class Conn:
        def execute(self, *a, **k):
            return []

    @contextmanager
    def connection():
        yield Conn()
    monkeypatch.setattr(workflow, "call", call)
    monkeypatch.setattr(workflow, "progress", lambda *a, **k: None)
    monkeypatch.setattr(workflow, "query_vectors", lambda worker, job, run, texts: {t: [0.0] for t in texts})
    monkeypatch.setattr(workflow.retrieval, "search", lambda conn, text, vector, snapshot: [text])
    monkeypatch.setattr(workflow.retrieval, "expand", lambda conn, hits, snapshot: [pool[int(hits[0].split()[-1])]])
    monkeypatch.setattr(workflow.retrieval, "check_prior", lambda conn, prior: None)
    worker = SimpleNamespace(repo=SimpleNamespace(connection=connection))
    run = {"input_refs": {"angle": {"title": "A synthetic card"}, "brand": {}}, "created_at": datetime(2026, 10, 25, tzinfo=UTC)}
    dossier = workflow.research(worker, None, run, {"evidence": [], "archive": {"chunks": [], "sources": {}}, "prior": []})
    grades = [p for stage, p in sent if stage == "brief_grade"]
    assert len(grades) == 2 and [e["evidence_id"] for e in grades[1]["evidence"]] == ["ev_0"]
    assert {e.evidence_id for e in dossier.evidence} == {f"ev_{n}" for n in range(6)}
    record = next(a for a in dossier.audit if "grades" in a)
    assert record["dropped_grades"] == ["ev_never_delivered", "ev_1"] and record["followup_grading"]["missing"] == ["ev_0"]
