"""E.B15's verified remainder, offline: Gate 2 re-checks a brief with the rules of the knowledge-base version it pins,
a recommendation binds to the call or a document or is flagged (condition 3), words in quotation marks inside the copy
bind to the turn that says them or are flagged (condition 4), and a v2 brief says no different-family reviewer read it.
Contract v3 first, v2 where the same code serves both. Constructed briefs and synthetic evidence; no database, no model."""
from __future__ import annotations

import copy
import json

import pytest

from backend_pipeline.briefs import gate_two, ledger_v3, rules
from backend_pipeline.briefs.contracts_v2 import SCHEMA_V2
from backend_pipeline.briefs.contracts_v3 import SCHEMA_V3
from backend_pipeline.knowledge_base import _read_text
from backend_pipeline.tests import test_brief_v2 as v2
from backend_pipeline.tests import test_brief_v3 as v3
from backend_pipeline.tests.brief_v2_fixtures import v2_body
from backend_pipeline.tests.brief_v3_fixtures import v3_body


def blocking(findings):
    return [f["message"] for f in findings if f["severity"] == "blocking"]


def warnings(findings):
    return [f["message"] for f in findings if f["severity"] == "warning"]


# Gate 2 loads the pinned version's rules ---------------------------------------------------------------------------

def _rule(rule_id, pattern):
    return {"id": rule_id, "pattern": pattern, "kind": "ban", "scope": "all", "since": "2026-01-01", "message": f"{rule_id} test ban"}


def _version(folder, version, patterns, *, by_hand=False):
    """A knowledge-base folder holding only its manifest and lint patterns: named and hash-bound in the manifest (a
    compiled version), or beside it unnamed (a version kept by hand before E.B11 (2))."""
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "rejection-rules.patterns.json"
    path.write_text(json.dumps({"rules": patterns}), encoding="utf-8")
    manifest = {"knowledge_base_version": version, "documents": []}
    if not by_hand:
        manifest["rule_patterns"] = {"file": path.name, "sha256": _read_text(path, 2)[1], "rules": len(patterns)}
    (folder / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return folder


@pytest.fixture
def knowledge(tmp_path, monkeypatch):
    """Today's files are version kb-now and ban "single ad"; the archive keeps kb-then, which bans "inquiry" instead.
    Both phrases are in the constructed briefs' WIA perspective."""
    root = _version(tmp_path / "kb", "kb-now", [_rule("RR-NOW", r"\bsingle ad\b")])
    _version(root / "archive" / "kb-then", "kb-then", [_rule("RR-THEN", r"\binquiry\b")])
    _version(root / "archive" / "kb-by-hand", "kb-by-hand", [_rule("RR-HAND", r"\binquiry\b")], by_hand=True)
    monkeypatch.setenv("CONTENT_ATELIER_KNOWLEDGE_BASE_DIR", str(root))
    return root


def row(schema, version):
    module = v3 if schema == SCHEMA_V3 else v2
    doc = module.document()[0] if schema == SCHEMA_V3 else module.document()
    d = module.dossier()
    provenance = {**module.provenance(), "pinned_inputs": {"knowledge_base": {"version": version, "sha256": "0" * 64}},
                  "angle": d.angle, "brand_hash": "b", "run_id": "brief_run_test"}
    return {"brief_id": "brief_test", "content_body": {"schema_version": schema, "document": doc, "provenance": provenance,
                                                       "review": {"clearances": {}}},
            "selected_evidence": [e.model_dump(mode="json") for e in d.evidence], "prior_content_context": [],
            "research_gaps": {"items": [], "coverage": {}}}


@pytest.mark.parametrize("schema", [SCHEMA_V3, SCHEMA_V2])
def test_gate_two_checks_a_brief_with_its_pinned_version_s_rules_not_today_s_files(knowledge, schema):
    found = blocking(gate_two.findings_v2(row(schema, "kb-then")))
    assert any(m.startswith("RR-THEN") for m in found), found
    assert not any(m.startswith("RR-NOW") for m in found), "today's files are another version"
    by_hand = blocking(gate_two.findings_v2(row(schema, "kb-by-hand")))
    assert any(m.startswith("RR-HAND") for m in by_hand), "a version kept by hand keeps its patterns file"
    current = blocking(gate_two.findings_v2(row(schema, "kb-now")))
    assert any(m.startswith("RR-NOW") for m in current) and not any(m.startswith("RR-THEN") for m in current), \
        "a brief written with today's version is checked with it"


@pytest.mark.parametrize("schema", [SCHEMA_V3, SCHEMA_V2])
def test_a_pinned_version_found_nowhere_or_altered_blocks_rather_than_borrowing_today_s_rules(knowledge, schema):
    missing = blocking(gate_two.findings_v2(row(schema, "kb-lost")))
    assert any("knowledge base kb-lost" in m and "neither the store nor knowledge_base/archive/" in m for m in missing), missing
    assert not any(m.startswith("RR-NOW") for m in missing)
    (knowledge / "archive" / "kb-then" / "rejection-rules.patterns.json").write_text(
        json.dumps({"rules": [_rule("RR-EDITED", "x")]}), encoding="utf-8")
    altered = blocking(gate_two.findings_v2(row(schema, "kb-then")))
    assert any("knowledge base kb-then" in m and "could not be read" in m for m in altered), altered
    assert not any(m.startswith(("RR-EDITED", "RR-NOW")) for m in altered)


def test_the_pinned_version_is_read_from_the_brief_s_provenance(knowledge):
    assert rules.pinned_version({"pinned_inputs": {"knowledge_base": {"version": "kb-then"}}}) == "kb-then"
    assert rules.pinned_version({"pinned_inputs": {}}) is None
    loaded, problem = rules.pinned_rules(None, {"pinned_inputs": {"knowledge_base": {"version": "kb-then"}}})
    assert problem is None and [r["id"] for r in loaded] == ["RR-THEN"]


# Condition 3: a recommendation binds or is flagged -------------------------------------------------------------------

def _recommendation(**changes):
    return {"claim_id": "c_rec", "text": "Answer every inquiry within the hour.", "claim_class": "recommendation", "evidence_ids": [],
            "knowledge_base_document": None, "numeric_facts": [], "quote": None, "public_quote": False, **changes}


def test_a_v2_recommendation_that_cites_nothing_blocks():
    body = v2_body(v2.packet())
    body["claims"].append(_recommendation())
    assert any("recommendation claim cites" in m for m in blocking(v2.check(v2.document(body))))
    for cited in ({"evidence_ids": ["ev_a"]}, {"knowledge_base_document": "process_catalogue"}):
        body["claims"][-1] = _recommendation(**cited)
        assert not any("recommendation claim" in m for m in blocking(v2.check(v2.document(body)))), cited


def test_a_v3_recommendation_the_verifier_calls_a_view_binds_to_its_turn_or_is_flagged():
    writer = v3_body(v3.packet())
    writer["wia_perspective"] = "Answer every new inquiry within the hour. Read the first reply before the ads."
    unbound = v3.fake_verifier({"Answer every": {"verdict": "view", "claim_class": "recommendation", "evidence_refs": [],
                                                 "knowledge_base_document": None, "flag": None}})
    doc, _ = v3.document(writer, verify=unbound)
    claim = v3.claim_for(doc, "Answer every")
    assert claim["claim_class"] == "recommendation" and claim["evidence_ids"] == [] and claim["flag"]["severity"] == "check"
    found = v3.check(doc)
    assert any("cites neither a turn of the call nor a knowledge-base document" in m for m in warnings(found))
    assert not any("Answer every" in m or "recommendation claim" in m for m in blocking(found)), "flagged for a person, not blocked"
    bound = v3.fake_verifier({"Answer every": {"verdict": "view", "claim_class": "recommendation", "evidence_refs": ["E1"],
                                               "knowledge_base_document": None, "flag": None}})
    doc, _ = v3.document(writer, verify=bound)
    claim = v3.claim_for(doc, "Answer every")
    assert claim["evidence_ids"] == ["ev_a"] and claim["flag"] is None
    assert not any("cites neither" in m for m in warnings(v3.check(doc)))
    documented = v3.fake_verifier({"Answer every": {"verdict": "view", "claim_class": "recommendation", "evidence_refs": [],
                                                    "knowledge_base_document": "process_catalogue", "flag": None}})
    doc, _ = v3.document(writer, verify=documented)
    assert v3.claim_for(doc, "Answer every")["knowledge_base_document"] == "process_catalogue"
    assert not any("cites neither" in m for m in warnings(v3.check(doc)))


# Condition 4: quoted words inside the copy -------------------------------------------------------------------------

QUOTED_TURN = "How do you reply to a new inquiry today?"


def test_v2_quoted_words_in_the_copy_bind_to_the_turn_that_says_them_or_are_flagged():
    body = v2_body(v2.packet())
    body["wia_perspective"] = 'Our strategist asked the owner, "answer every inquiry within the hour," and the owner agreed.'
    found = v2.check(v2.document(body))
    assert any('"answer every inquiry within the hour,"' in m and "no turn of the call says it" in m for m in warnings(found))
    body["wia_perspective"] = f'Our strategist asked, "{QUOTED_TURN}"'
    found = v2.check(v2.document(body))
    assert any(QUOTED_TURN in m and "needs source-use and attribution clearance" in m for m in blocking(found))
    assert not any("no turn of the call says it" in m for m in warnings(found)), "the turn says it"
    cleared = v2.checks_v2(v2.document(body), v2.dossier(), v2.provenance(),
                           {"ev_a": {"permission_reference": "p", "attribution_reference": "a"}},
                           v2.load_rules(v2.BACKEND_ROOT / "knowledge_base"))
    assert not any(QUOTED_TURN in m for m in blocking(cleared))


def test_v3_quoted_words_the_verifier_finds_supported_but_no_turn_says_are_flagged():
    writer = v3_body(v3.packet())
    writer["wia_perspective"] = 'Our strategist asked the owner, "answer every inquiry within the hour," and the owner agreed.'
    paraphrase = v3.fake_verifier({"answer every inquiry": {"verdict": "paraphrase", "claim_class": "particular_interaction",
                                                            "evidence_refs": ["E1"], "knowledge_base_document": None, "flag": None}})
    doc, _ = v3.document(writer, verify=paraphrase)
    claim = v3.claim_for(doc, "answer every inquiry")
    assert claim["status"] == "supported" and claim["flag"]["message"] == ledger_v3.UNBOUND_QUOTE
    assert any("in no turn of the call" in m for m in warnings(v3.check(doc)))
    # A quotation the rules bind is the turn's words, with no such flag; one the verifier calls invented still blocks.
    writer["wia_perspective"] = f'Our strategist asked, "{QUOTED_TURN}"'
    doc, _ = v3.document(writer, verify=paraphrase)
    assert v3.claim_for(doc, "Our strategist asked")["settled_by"] == "deterministic"
    assert not any("in no turn of the call" in m for m in warnings(v3.check(doc)))


def test_the_ledger_version_records_the_new_rules():
    assert ledger_v3.LEDGER_VERSION == "brief-ledger-2026-10-20.v2"


# (g): a v2 brief says no different-family reviewer read it -------------------------------------------------------------

def test_a_v2_brief_warns_that_no_different_family_reviewer_read_it_and_a_v3_brief_does_not():
    from backend_pipeline.briefs.validation_v2 import NO_REVIEWER_V2
    assert NO_REVIEWER_V2 in warnings(v2.check(v2.document()))
    assert NO_REVIEWER_V2 not in warnings(v3.check(v3.document()[0]))
    assert "2.4a (b)" in NO_REVIEWER_V2 and "(c)" in NO_REVIEWER_V2 and "(f)" in NO_REVIEWER_V2
    assert copy.deepcopy(v2.check(v2.document())) == v2.check(v2.document()), "deterministic"
