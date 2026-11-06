"""E.B17: no knowledge-base text, exemplar or situational line derives from a held-out benchmark week."""
from __future__ import annotations

from backend_pipeline.config import BACKEND_ROOT
from backend_pipeline.knowledge import held_out
from backend_pipeline.knowledge_base import load_knowledge_base


def test_the_week_6_result_and_the_pieces_built_on_it_are_recognised():
    result = {"key": "result:r3", "kind": "result",
              "text": "Ads Accelerator client: venue marketing director: H1 last year more than $22,000 on ad spend"}
    caption = {"key": "exemplar:ex01", "text": "You can't optimize what you can't measure."}
    piece = {"content_id": "pc1", "title": "Case-study Reel and email ($22K to measurable)"}
    belief = {"key": "belief:b1", "text": "good marketing decisions start with good data."}
    assert [held_out.week_of(r) for r in (result, caption, piece, belief)] == [6, 6, 6, None]
    assert held_out.keep([result, caption, piece, belief]) == [belief]
    assert held_out.withheld([result, piece]) == [{"id": None, "key": "result:r3", "week": 6}, {"id": "pc1", "key": None, "week": 6}]
    # A different client's figure is not this week's material.
    assert held_out.week_of({"text": "A photographer went from 7 to 30 inquiries a month"}) is None


def test_the_committed_knowledge_base_states_no_held_out_material():
    """The committed version is what every run without the store loads (E.B11 e): it must hold Week 6 out."""
    kb = load_knowledge_base(BACKEND_ROOT / "knowledge_base")
    found = {d.entry.key: sorted(held_out.text_weeks(d.text)) for d in kb.documents if held_out.text_weeks(d.text)}
    assert found == {}, f"documents stating held-out material: {found}"
    assert not any(held_out.HELD_OUT.keys() & set(d.entry.provenance.derived_from_weeks) for d in kb.documents)


def test_a_live_run_refuses_a_knowledge_base_that_states_held_out_material(tmp_path):
    """The archived version that predates the guard replays its runs; it never feeds a live one (E.B17)."""
    import pytest
    from backend_pipeline.config import Settings
    from backend_pipeline.pipeline import Pipeline
    archived = BACKEND_ROOT / "knowledge_base" / "archive" / "wia-kb-2026-10-18.c-3ccde8c5"
    if not archived.is_dir():
        pytest.skip("version 3 is not archived in this checkout")
    pipeline = Pipeline(Settings(data_root=tmp_path, knowledge_base_root=archived))
    with pytest.raises(ValueError, match="held-out benchmark week 6"):
        pipeline.context("strategist", "live")
    assert pipeline.context("strategist", "replay").version == "wia-kb-2026-10-18.c-3ccde8c5"
    held_out.check_live(load_knowledge_base(BACKEND_ROOT / "knowledge_base").text)


def test_the_reviewed_brand_bundle_points_at_the_committed_version():
    """The brief writer's bundle names the documents it summarises by hash; it moves with the knowledge base (L.B5)."""
    import json
    root = BACKEND_ROOT / "knowledge_base"
    bundle = json.loads((root / "brief-brand-bundle.json").read_text(encoding="utf-8"))
    kb = load_knowledge_base(root)
    assert bundle["knowledge_base_version"] == kb.version
    assert bundle["source_document_hashes"] == {k: kb.document(k).sha256 for k in bundle["source_document_hashes"]}


# Version 5 (L.B4, E.B11): compiled from the store built from committed inputs, approved under D12, benchmarked against
# version 4 (R44; research/benchmark-v1/results/), the default from 19 October until version 6 replaced it; archived.
V5 = BACKEND_ROOT / "knowledge_base" / "archive" / "wia-kb-2026-10-19.c-0b931261"


def test_the_archived_version_5_is_pinned_holds_week_6_out_and_meets_e_b11():
    import re

    from backend_pipeline.knowledge import items
    kb = load_knowledge_base(V5)
    # The hashes every environment records for this version: the store's export produced these bytes, and the database
    # suite rebuilds them from the committed inputs (test_context_closeout_db.py).
    assert kb.version == "wia-kb-2026-10-19.c-0b931261" and kb.format == 2
    assert kb.sha256 == "b48541bfc9a3d04659e5c9d93e5c5bd9e298d8b7f37a3740beed1b68bcd79285"
    assert kb.manifest_sha256 == "d1ceea109ffa59942186d5c78f0f4da7d744fbcfbcd96997eb958ca275278333"
    assert kb.rule_patterns_sha256 == "9e3696571e60057057bc082e4e18166dd9763267a5e402fdcf60968f55225dd3"
    assert not {d.entry.key for d in kb.documents if held_out.text_weeks(d.text)}
    assert all(f"Status: {d.entry.status}; effective {d.entry.effective_date.isoformat()}" in kb.text for d in kb.documents)
    assert "verifier" in kb.document("belief_statements").entry.stages
    categories = "|".join(c.replace("_", " ") for c in items.RULE_CATEGORIES)
    shape = re.compile(rf"\((?:ban|flag); scope (?:angle|brief|all); (?:{categories}); (?:since|stated) .+; by .+; origin: .+\)$")
    rules = [line for line in kb.document("rejection_rules").text.splitlines() if line.startswith("- ")]
    assert rules and all(shape.search(line) for line in rules)
    # The E.B10 lint reads the patterns compiled from these rules; they lint exactly what version 4's hand-kept list did.
    from backend_pipeline.knowledge import compiler
    v4 = __import__("json").loads((BACKEND_ROOT / "knowledge_base" / "archive" / "wia-kb-2026-10-18.c-0cb353e4" / compiler.PATTERNS_FILE).read_text(encoding="utf-8"))["rules"]
    assert compiler.lint_content(kb.rule_patterns) == compiler.lint_content(v4)


def test_week_5_stories_are_recognised_and_its_clients_names_and_whitneys_competitor_list_are_not():
    """E.B17: Week 5 is the clean held-out label week of E.B13 and E.X3; its stories are withheld, not its clients."""
    prospect = {"key": "result:r9", "text": "A venue owner paying $2,500 a month with Hitched booked 15 tours from a wedding show"}
    elia = {"content_id": "pc9", "title": "We've had tours, but the conversions are down since we went all-inclusive"}
    trip = {"key": "belief:b9", "text": "It's coming out of my bank account every month and I never check it"}
    assert [held_out.week_of(r) for r in (prospect, elia, trip)] == [5, 5, 5]
    assert held_out.withheld([prospect, elia]) == [{"id": None, "key": "result:r9", "week": 5}, {"id": "pc9", "key": None, "week": 5}]
    # The clients return in later weeks, and the agencies are on Whitney's competitor list (03-accelerator-strategy).
    for text in ("The Elia's ads strategy call", "Alexis renewed her Vault membership", "Experience Lux Travel onboarding",
                 "- Hitched https://www.instagram.com/hitched_marketing/", "- I Do Society https://www.instagram.com/theidosociety/"):
        assert held_out.week_of({"text": text}) is None, text
    assert held_out.text_weeks("booked 15 tours, and the venue marketing director spent $22,000") == {5, 6}


def test_no_published_version_and_no_prompt_template_states_week_5_material():
    """Checked against Week 5's six documents (19 October): no committed or archived version and no prompt template
    carries Week 5 material, so the guard withholds nothing that version 5 or an earlier version compiled."""
    root = BACKEND_ROOT / "knowledge_base"
    versions = [root, *sorted(p for p in (root / "archive").iterdir() if p.is_dir())]
    found = {v.name: [f.name for f in sorted(v.glob("*.md")) if 5 in held_out.text_weeks(f.read_text(encoding="utf-8"))]
             for v in versions}
    assert all(names == [] for names in found.values()), found
    templates = [f for f in (BACKEND_ROOT / "backend_pipeline" / "prompt_templates").rglob("*") if f.is_file()]
    assert templates and not [f.name for f in templates if 5 in held_out.text_weeks(f.read_text(encoding="utf-8", errors="replace"))]


# Version 6 (E.B11 (1), (4)): version 5 with eleven rules refiled under their reviewed category and the proof rule
# without the figure a venue client vetoed; compiled on 20 October from the committed review, approved under D12 and,
# after its E.B3 smoke result on benchmark v1 (R44; no regression against version 5,
# research/benchmark-v1/results/2026-10-19-strategist_v5.wia-kb-2026-10-20.c-886de379.json), the default from 20 October
# until version 7 replaced it the same day; archived.
V6 = BACKEND_ROOT / "knowledge_base" / "archive" / "wia-kb-2026-10-20.c-886de379"


def test_the_archived_version_6_is_pinned_and_changes_only_the_rules():
    from backend_pipeline.knowledge import compiler
    kb, v5 = load_knowledge_base(V6), load_knowledge_base(V5)
    assert kb.version == "wia-kb-2026-10-20.c-886de379" and kb.format == 2
    assert kb.sha256 == "e07b57699bcef8fdd42b9a409504fff75351014c8025347d2144482cc7b57172"
    assert kb.manifest_sha256 == "4e40b10ddea1bdfa2c9e6871c3a1c13aed67024884a6c4399d852254077f1367"
    assert kb.rule_patterns_sha256 == v5.rule_patterns_sha256 and compiler.lint_content(kb.rule_patterns) == compiler.lint_content(v5.rule_patterns)
    assert [d.entry.key for d in kb.documents if d.sha256 != v5.document(d.entry.key).sha256] == ["rejection_rules"]
    assert not {d.entry.key for d in kb.documents if held_out.text_weeks(d.text)}


# Version 7 (E.B25 (c)): version 6 with the lines of the supplied documents 01 to 03 that rulings R-1 to R-16 supersede
# removed, annotated or replaced (backend/knowledge_base/supersessions.json); compiled on 20 October from the committed
# review and supersessions, approved under D12 and D21 and, after its E.B3 smoke result on benchmark v1 (R44; no accuracy
# regression against version 6, research/benchmark-v1/results/2026-10-20-strategist_v5.wia-kb-2026-10-20.c-b953624b.json),
# the default from 20 October until version 8 replaced it the same day; archived.
V7 = BACKEND_ROOT / "knowledge_base" / "archive" / "wia-kb-2026-10-20.c-b953624b"


def test_the_archived_version_7_is_pinned_and_changes_only_the_supplied_documents():
    import json

    from backend_pipeline.knowledge import supersessions
    kb, v6 = load_knowledge_base(V7), load_knowledge_base(V6)
    assert kb.version == "wia-kb-2026-10-20.c-b953624b" and kb.format == 2
    assert kb.sha256 == "a612d2a73ecfefd33a9ff84b5e77341a7ea477b4988714c579f82e40978ebf62"
    assert kb.manifest_sha256 == "778c5c59fc01492efa79298be5a99efb30949610dd046a95cc2011cb0ecca0ab"
    assert kb.rule_patterns_sha256 == v6.rule_patterns_sha256
    assert [d.entry.key for d in kb.documents if d.sha256 != v6.document(d.entry.key).sha256] == [
        "content_strategy", "founder_voice_guide", "accelerator_strategy"]
    manifest = json.loads((V7 / "manifest.json").read_text(encoding="utf-8"))
    spec, digest = supersessions.load(BACKEND_ROOT / "knowledge_base")
    assert manifest["supersessions"] == {"file": "supersessions.json", "sha256": digest, "applied": [e["id"] for e in spec["entries"]]}
    # Each document is exactly the supplied original (unchanged in version 6) with its supersessions applied.
    originals = v6
    for key in sorted(supersessions.DOCUMENTS):
        mine = [e for e in spec["entries"] if e["document"] == key]
        assert kb.document(key).text == supersessions.apply(originals.document(key).text, mine), key
    assert not {d.entry.key for d in kb.documents if held_out.text_weeks(d.text)}


# Version 8 (E.B25 (e)): version 7 with the editing guide (backend/knowledge_base/17-editing-guide.md, added from 20 October
# by backend/knowledge_base/additions.json); compiled on 20 October from the committed review and lists, approved under D12
# and D21 and, after its E.B3 smoke result on benchmark v1 (R44; strategist v6, the slim prefix under prefix-priority.v2
# against version 7's full prefix: no accuracy regression and the calibrated judge's preference,
# research/benchmark-v1/results/2026-10-20-strategist_v6.wia-kb-2026-10-20.c-6bf62f94.json), the default from 20 October
# until version 9 replaced it on 23 October; archived with the additions list it applied (the committed list now also adds
# version 9's documents 18 and 19).
V8 = BACKEND_ROOT / "knowledge_base" / "archive" / "wia-kb-2026-10-20.c-6bf62f94"


def test_the_archived_version_8_is_pinned_and_adds_only_the_editing_guide():
    import json

    from backend_pipeline.knowledge import additions
    kb, v7 = load_knowledge_base(V8), load_knowledge_base(V7)
    assert kb.version == "wia-kb-2026-10-20.c-6bf62f94" and kb.format == 2
    assert kb.sha256 == "d1defc442f225aa0b702290ea5f71e54145197c2217ba1ae5ea2b2186d8337bd"
    assert kb.manifest_sha256 == "34be51883182c40ebd1d2cbcd1ba8a7bc311010d33fdd7333ae4089990c46783"
    assert kb.rule_patterns_sha256 == v7.rule_patterns_sha256
    assert [d.entry.key for d in kb.documents] == [d.entry.key for d in v7.documents] + ["editing_guide"]
    assert all(d.sha256 == v7.document(d.entry.key).sha256 for d in v7.documents), "everything else carries over"
    spec, digest = additions.load(V8)
    guide = kb.document("editing_guide")
    assert guide.text == additions.text(V8, spec["entries"][0]), "the reviewed text, verbatim"
    assert additions.load(BACKEND_ROOT / "knowledge_base")[0]["entries"][0] == spec["entries"][0], "the committed list keeps A01"
    assert guide.entry.stages == ["strategist", "brief"] and guide.entry.status == "confirmed" and guide.entry.provenance.model_written
    assert guide.entry.provenance.source.startswith("research/chatgpt-export-2026-10-18/data/pack_rules.md")
    manifest = json.loads((V8 / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["additions"] == {"file": "additions.json", "sha256": digest, "applied": ["A01"]}
    assert manifest["supersessions"] == json.loads((V7 / "manifest.json").read_text(encoding="utf-8"))["supersessions"]
    assert not {d.entry.key for d in kb.documents if held_out.text_weeks(d.text)}
