"""Knowledge-base version 9 (E.B25 (i), (j); L.B12), offline: the committed version is pinned, changes only what it says,
holds no held-out or Week 2 material, agrees with the files the checks read, and fits every stage's prefix budget with
Whitney's own words kept. It passed its reading in phase N2 (the minimal gate, D40;
research/n2-delivery-2026-10/kb9-reading.wia-kb-2026-10-22.c-a1a75795.json) and is the committed default from 23 October;
version 8 is archived."""
from __future__ import annotations

import json
import re

from backend_pipeline.config import BACKEND_ROOT
from backend_pipeline.knowledge import additions, assembly, entries, held_out
from backend_pipeline.knowledge_base import load_knowledge_base
from backend_pipeline.tests.test_held_out import V8

KB = BACKEND_ROOT / "knowledge_base"
V9 = KB


def test_version_9_is_pinned_and_changes_only_what_it_adds():
    kb, v8 = load_knowledge_base(V9), load_knowledge_base(V8)
    assert v8.version == "wia-kb-2026-10-20.c-6bf62f94", "version 9's base, archived"
    assert kb.version == "wia-kb-2026-10-22.c-a1a75795" and kb.format == 2
    assert kb.sha256 == "0aa167df0adbd19c60725d3b10326f5ca899ecfbf3860d52024f881fb7349d64"
    assert kb.manifest_sha256 == "f055aad6a5a93d41208402cb2d0df1dce9cd474f94ddad0b8b91c66839b83391"
    assert kb.rule_patterns_sha256 == v8.rule_patterns_sha256
    assert [d.entry.key for d in kb.documents] == [d.entry.key for d in v8.documents] + ["spoken_voice", "transformations"]
    changed = [d.entry.key for d in v8.documents if kb.document(d.entry.key).sha256 != d.sha256]
    assert changed == ["offer_sheet", "format_guide", "recent_published"]
    spec, digest = additions.load(V9)
    manifest = json.loads((V9 / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["additions"] == {"file": "additions.json", "sha256": digest, "applied": ["A01", "A02", "A03"]}
    for entry in spec["entries"][1:]:
        document = kb.document(entry["key"])
        assert document.text == additions.text(V9, entry), "the reviewed text, verbatim"
        assert document.entry.status == "confirmed" and not document.entry.provenance.model_written
    assert kb.document("spoken_voice").entry.stages == ["brief"], "scripts only (E.B25 (j))"
    assert kb.document("transformations").entry.stages == ["strategist", "brief"]


def test_version_9_holds_no_held_out_or_week_2_material():
    kb = load_knowledge_base(V9)
    assert not {d.entry.key for d in kb.documents if held_out.text_weeks(d.text)}
    new = kb.document("spoken_voice").text + kb.document("transformations").text + kb.document("format_guide").text
    # Week 2's packs and WIA's 20 October corrections are tests, never exemplars (D28): none of their lines is here.
    for line in ("Why we lowered a new client's ad budget", "She used AI to set up her Google Ads", "Did I set my ads up wrong",
                 "your ads are working, and then they stop", "Something's working, and then it stops", "I don't know what I've done"):
        assert line.lower() not in new.lower(), line


def test_document_18_leads_with_the_18_august_reel_and_document_19_holds_six_chains_in_her_words():
    kb = load_knowledge_base(V9)
    spoken = kb.document("spoken_voice").text
    reels = re.findall(r"^## Reel[^\n]*", spoken, re.M)
    assert len(reels) == 5 and "18 August 2026" in reels[0]
    assert "What would happen if your wedding business didn't post on Instagram for the next 10 weeks?" in spoken
    chains = kb.document("transformations").text
    assert len(re.findall(r"^## Chain \d", chains, re.M)) == 6
    # Her own text only (D34): the drafts she turned down are left out, her reasons and finals are in.
    assert "You are very obtuse. Here's my edit:" in chains and "Predictable sales > more leads" in chains
    assert "17 events last year to 90" in chains and "RR-10" in chains, "her raw slip is marked against the rule"
    assert "—" not in chains and "—" not in spoken


def test_document_05_names_every_term_and_descriptor_the_checks_read():
    offer = load_knowledge_base(V9).document("offer_sheet").text
    terms = json.loads((KB / "insider-terms.json").read_text(encoding="utf-8"))["terms"]
    descriptors = json.loads((KB / "offer-descriptors.json").read_text(encoding="utf-8"))["offers"]
    assert "## Insider terms" in offer and "## Approved descriptors" in offer
    assert all(f"- {t['term']}:" in offer and t["plain"] in offer for t in terms)
    assert all(d in offer for o in descriptors for d in o["descriptors"])
    # The reviewed list derives them from the same files, so a term added there reaches document 05 on the next apply.
    derived = entries.derived()
    assert {e["body"]["name"] for e in derived if e["body"]["section"] == "insider_term"} == {t["term"] for t in terms}
    assert {e["body"]["name"] for e in derived if e["body"]["section"] == "descriptor"} == {o["offer"] for o in descriptors}


def test_document_09_states_the_first_touch_rules_and_reconciles_the_slide_count():
    guide = load_knowledge_base(V9).document("format_guide").text
    assert "## First-touch text" in guide and "7 to 12 slides, usually 9 or 10 for a story" in guide
    assert "Usually 7 to 10 slides" not in guide
    for rule in ("Specific.", "Slide 1 carries the promise.", "Subject lines state", "No insider terms.", "Who did what."):
        assert f"- {rule}" in guide
    assert "\"More leads won't fix this...\"" in guide and "\"Are Your Google Ads Actually Working?\"" in guide


def test_document_13_is_the_register_at_piece_level():
    register = load_knowledge_base(V9).document("recent_published").text
    assert "Google Reps Aren't Your Marketing Strategist" in register
    assert "(central point: Google's own recommendations serve Google's goals" in register


def test_every_stage_of_version_9_fits_its_prefix_budget_with_her_words_kept(monkeypatch):
    monkeypatch.delenv("ATELIER_CONTEXT_PREFIX_TOKENS", raising=False)
    for stage, kept in (("strategist", {"transformations", "process_catalogue"}), ("brief", {"spoken_voice", "transformations"}),
                        ("verifier", set()), ("extraction", set())):
        kb = assembly.assemble(stage, root=V9)
        record = (kb.context or {}).get("prefix_budget")
        assert assembly.tokens(kb.text) <= 30000, stage
        assert kept <= {d.entry.key for d in kb.documents}, stage
        if record:
            assert record["priority"] == "prefix-priority.v3" and not record["over_budget"]
    # Version 8 is cut exactly as before (prefix-priority.v2).
    assert assembly.assemble("strategist", root=V8).context["prefix_budget"]["priority"] == "prefix-priority.v2"
