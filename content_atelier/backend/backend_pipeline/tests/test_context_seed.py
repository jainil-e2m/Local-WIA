"""L.B2 offline: every draft entry becomes a cited, dated, attributed candidate; nothing personal is loaded."""
from __future__ import annotations

import re

import pytest

from backend_pipeline.knowledge import items, seed

ROOT = seed.REPOSITORY_ROOT
pytestmark = pytest.mark.skipif(not (ROOT / seed.DRAFTS).is_dir(), reason="The export analysis drafts are not checked out")


@pytest.fixture(scope="module")
def parsed():
    return seed.candidates(ROOT)


def test_every_draft_document_contributes_entries(parsed):
    drafts, published, _ = parsed
    files = {d["source_detail"]["draft"].rsplit("/", 1)[-1] for d in drafts if "draft" in d["source_detail"]}
    expected = {p.name for p in (ROOT / seed.DRAFTS).iterdir()}
    assert files == expected, "every kb-candidates document is seeded"
    assert len(published) >= 50 and all(r["status"] == "unconfirmed" for r in published)
    assert {d["kind"] for d in drafts} >= {"rule", "offer", "price", "roster_member", "cta", "process_step", "format_rule",
                                          "audience_phrase", "belief", "result", "exemplar"}


def test_every_candidate_cites_its_source_date_author_and_flags(parsed):
    everything, _, _ = parsed
    plan = [d for d in everything if d["source_kind"] == "knowledge_base"]
    # KB 14, the model-drafted content plan, is a set of candidates citing its document (section 4.12).
    assert plan and all(d["kind"] == "content_plan_entry" and d["model_written"] and d["status"] == "candidate"
                        and d["source_detail"]["document"].endswith("14-content-plan.md") for d in plan)
    assert {d["body"].get("week_of") for d in plan} >= {"2026-10-19", "2026-11-02", "2026-11-16"}
    drafts = [d for d in everything if d["source_kind"] != "knowledge_base"]
    for d in drafts:
        detail = d["source_detail"]
        assert d["status"] == "candidate" and d["source_kind"] == "export_seed"
        assert d["source_ref"].startswith("research/chatgpt-export-2026-10-18/kb-candidates/")
        assert d["statement_date"] is not None, d["source_ref"]
        assert d["author"] and isinstance(d["model_written"], bool) and d["visibility"] in ("public", "internal")
        assert detail["draft"] and detail["export"].startswith("ChatGPT export")
        cites = any(detail.get(k) for k in ("conversations", "attachments", "chunks"))
        assert cites or detail.get("citations_from") == "draft", d["source_ref"]
        if detail.get("citations_from") == "draft":
            assert d["confidence"] == "low", "an uncited summary line is a low-confidence candidate"
    direct = sum(1 for d in drafts if d["source_detail"].get("conversations") or d["source_detail"].get("attachments"))
    assert direct / len(drafts) > 0.6, "most entries cite a conversation file or an attachment"


def test_source_references_are_unique_and_stable(parsed):
    drafts, published, _ = parsed
    refs = [d["source_ref"] for d in drafts] + [p["source_ref"] for p in published]
    assert len(refs) == len(set(refs))
    again, again_published, _ = seed.candidates(ROOT)
    assert [d["source_ref"] for d in again] == [d["source_ref"] for d in drafts]
    assert [d["body"] for d in again] == [d["body"] for d in drafts]


def test_distinct_draft_entries_never_share_a_key(parsed):
    # Confirming an item supersedes the confirmed item with the same key (L.B3), so two different draft entries under
    # one key would retire each other when both are accepted: only the last would reach the knowledge base. Only a key
    # given on purpose (a person, an offer, a price named by its subject) may be shared.
    drafts, _, _ = parsed
    positional = re.compile(r"\.(?:row|rule|bullet|numbered|paragraph)\d\d$")
    seen: dict[str, str] = {}
    for d in drafts:
        if positional.search(d["key"]):
            assert d["key"] not in seen, f"{d['source_ref']} and {seen[d['key']]} share {d['key']}"
            seen[d["key"]] = d["source_ref"]
    assert seen


def test_bodies_validate_and_internal_prices_and_private_results_are_internal(parsed):
    drafts, _, _ = parsed
    for d in drafts:
        items.validate_body(d["kind"], d["body"])
        items.check_fields(d["kind"], d["key"], d["visibility"], d["sensitivity"], d["permission"], None, None)
    prices = [d for d in drafts if d["kind"] == "price"]
    assert prices and all(d["visibility"] == "internal" for d in prices if "internal" in d["text"].lower())
    private = [d for d in drafts if d["kind"] == "result" and d["permission"] != "published"]
    assert private and all(d["visibility"] == "internal" and d["sensitivity"] == "client_private" for d in private)


def test_no_candidate_carries_personal_or_confidential_material(parsed):
    drafts, published, skipped = parsed
    texts = [d["text"] for d in drafts] + [str(d["body"]) for d in drafts] + [p["title"] for p in published]
    for reason, pattern in seed.PERSONAL:
        assert not any(pattern.search(t) for t in texts), reason
    assert not any(re.search(r"[\w.+-]+@[\w-]+\.\w+", t) for t in texts)
    assert set(skipped) <= {r for r, _ in seed.PERSONAL}


def test_the_screen_catches_contact_hr_and_financial_details():
    assert seed.screen("write to her at someone@example.com") == "contact detail"
    assert seed.screen("call 312-555-0142 tomorrow") == "contact detail"
    assert seed.screen("her salary was discussed") == "HR detail"
    assert seed.screen("our monthly revenue was 40K") == "WIA financials"
    assert seed.screen("59 leads in roughly 90 days; $90,000 in booked revenue") is None, "a published client result stays"


def test_confirmed_entries_come_only_from_the_ex2_documents_with_their_ruling():
    confirmed = seed.confirmed_from_knowledge_base(ROOT, "owner@example.invalid")
    assert {c["source_detail"]["document"].rsplit("/", 1)[-1] for c in confirmed} == {
        "04-team-roster.md", "05-offer-sheet.md", "06-rejection-rules.md"}
    assert all(c["status"] == "confirmed" and c["reviewed_by"] == "owner@example.invalid" and c["review_note"].startswith("E.X2")
               for c in confirmed)
    names = {c["body"]["name"]: c["body"]["state"] for c in confirmed if c["kind"] == "roster_member"}
    assert names["Fallon Looney"] == "former" and names["Savannah Jordan"] == "outside"
    assert names["Matt"] == "invented" and names["Viktor"] == "not_a_person"
    assert "Jacqueline" in [a for c in confirmed if c["kind"] == "roster_member" for a in c["body"].get("aliases", [])]
    codes = {c["body"].get("code") for c in confirmed if c["kind"] == "rule"}
    assert {"RR-01", "RR-46"} <= codes
