"""Phase N8 offline: identities in prompts and checks (1.B12's extension), internal meetings as team practice (1.B13's
extension, D24), strategist v8, scene profile v4 and brief writer v5.2. Synthetic people and accounts only; no database, no
model call."""
from __future__ import annotations

from pathlib import Path

import pytest

from backend_pipeline import angle_profiles as ap
from backend_pipeline import identities, settings_store
from backend_pipeline.briefs import runtime
from backend_pipeline.briefs.contracts_v4 import SCHEMA_V4, BriefWriteV51
from backend_pipeline.briefs.validation_v3 import contract_for
from backend_pipeline.briefs.validation_v4 import checks_v4
from backend_pipeline.briefs.workflow import writer_for
from backend_pipeline.config import BACKEND_ROOT
from backend_pipeline.cycle import verification as v
from backend_pipeline.cycle.verification import load_rules
from backend_pipeline.moments import scenes
from backend_pipeline.normalise import speakers
from backend_pipeline.storage_config import StorageSettings
from backend_pipeline.tests.test_brief_v3 import dossier, provenance
from backend_pipeline.tests.test_brief_v4 import document
from backend_pipeline.tests.test_strategist_v7 import ROSTER, SCENES, v7_card

TEMPLATES = Path(__file__).resolve().parents[1] / "prompt_templates"
LINK = {"what": "the anonymised $18K-to-$52K case study", "markers": ["$18K", "$52K"], "reason": "her name is banned"}
DANA = {"kind": "person", "id": "person_dana", "name": "Dana Reyes", "role": "client", "account": "Fernbrook Estate",
        "heard_as": ["fernbrookdana", "Dani"], "spellings": ["Dana Reyes", "fernbrookdana", "Dani"], "pronouns": "she/her",
        "left_on": None, "naming": "anonymise", "never_link": []}
MARA = {"kind": "person", "id": "person_mara", "name": "Mara Quill", "role": "client", "account": "Larkspur Hall",
        "heard_as": ["Mara"], "spellings": ["Mara Quill", "Mara"], "pronouns": "she/her", "left_on": None, "naming": "never_name",
        "never_link": [LINK]}
LARKSPUR = {"kind": "account", "id": "client_larkspur", "name": "Larkspur Hall", "role": "active", "business": "venue",
            "heard_as": [], "spellings": ["Larkspur Hall", "Larkspur"], "naming": "never_name", "never_link": [LINK]}
FALLON = {"kind": "person", "id": "person_fallon", "name": "Fallon Looney", "role": "former staff", "account": None, "heard_as": ["Fallon"],
          "spellings": ["Fallon Looney"], "pronouns": "she/her", "left_on": "2026-08-14", "naming": "may_name", "never_link": []}


# Identities: prompt lines, the writer's view and the check ----------------------------------------------------------------

def test_prompt_lines_say_who_a_label_is_their_pronouns_and_what_copy_may_do():
    lines = identities.prompt_lines([DANA, MARA, LARKSPUR, FALLON])
    assert lines[0] == ("- fernbrookdana, Dani = Dana Reyes: client at Fernbrook Estate; pronouns she/her; anonymise: never name them "
                        "or their business in public copy (describe the role instead).")
    assert "never name them or their business in public copy, whatever anyone asks" in lines[1]
    assert "never link them to the anonymised $18K-to-$52K case study" in lines[1] and "never link them" in lines[2]
    assert "a former WIA team member (left 14 August 2026); never present them as current" in lines[3]
    view = identities.writer_view([DANA, FALLON])
    assert view[0]["pronouns"] == "she/her" and view[0]["heard_as"] == ["fernbrookdana", "Dani"]
    assert "markers" not in str(view), "the check's markers never reach the writer"
    assert view[1]["left_wia"] == "14 August 2026" and "never present as current" in view[1]["naming"]


def test_a_never_name_identity_and_a_do_not_link_marker_are_blocking():
    named = identities.copy_findings({"title": "How Mara's venue doubled its tours"}, [MARA])
    assert [f["kind"] for f in named] == ["do_not_name"] and named[0]["severity"] == "blocking"
    # Anonymised, but built on her call and carrying the case study's figure: still a link.
    linked = identities.copy_findings({"point": "From 18K spent to 52K booked in one season."}, [MARA, LARKSPUR],
                                      evidence_ids=["person_mara"])
    assert {f["kind"] for f in linked} == {"do_not_link"} and "anonymised $18K-to-$52K case study" in linked[0]["message"]
    # The same figures in a card about someone else are not a link; nor is "52" without its K.
    assert identities.copy_findings({"point": "From 18K spent to 52K booked."}, [MARA, LARKSPUR]) == []
    assert identities.copy_findings({"point": "We saw 52 inquiries."}, [MARA], evidence_ids=["person_mara"]) == []
    assert identities.copy_findings({"point": "$52,000 in bookings."}, [MARA], evidence_ids=["person_mara"])[0]["kind"] == "do_not_link"


def test_a_lower_case_label_that_is_a_word_is_never_a_mention():
    assert identities._mentioned("rose", "prices rose in May") is False
    assert identities._mentioned("Rose", "Rose asked about tours") is True
    assert identities._mentioned("fernbrookdana", "fernbrookdana joined late") is True
    assert identities._mentioned("Dani", "the danish pastry") is False


def test_a_client_identity_takes_the_role_of_the_call_and_no_role_before_the_call_type_is_known():
    people = [{"person_id": "person_dana", "name": "Dana Reyes", "role": "client", "status": "current",
               "aliases": ["fernbrookdana"], "email": None, "client_id": "client_fern"}]
    resolver = speakers.Resolver(people)
    assert resolver.resolve("fernbrookdana", None, "prospect")["role"] == "prospect"
    assert resolver.resolve("fernbrookdana", None, "client_1to1") == {"person_id": "person_dana", "name": "Dana Reyes",
                                                                      "role": "client", "basis": "name", "inferred": True,
                                                                      "status": "current"}
    # The classifier's first pass sends the roles it always sent, so a model's earlier placement still matches its request.
    assert resolver.resolve("fernbrookdana", None, None)["role"] == "unknown"


# Team practice ------------------------------------------------------------------------------------------------------------

def test_a_client_name_or_figure_only_an_internal_meeting_carries_is_blocking():
    team = ["Whitney: Larkspur's cost per lead went to $31 after we split the campaigns."]
    other = ["Carmen: We split the campaigns so each one had its own budget."]
    found = identities.leak_findings({"point": "We split a venue's campaigns and its cost per lead fell to $31."}, team, other, [LARKSPUR])
    assert [f["kind"] for f in found] == ["team_practice_figure"]
    named = identities.leak_findings({"title": "What Larkspur taught us about splitting campaigns"}, team, other, [LARKSPUR])
    assert [f["kind"] for f in named] == ["team_practice_name"]
    assert identities.leak_findings({"point": "We split campaigns so each has its own budget."}, team, other, [LARKSPUR]) == []


def test_the_card_check_blocks_identities_and_team_practice_leaks():
    scenes_ = {**SCENES, "moment_team": [{"text": "Whitney: Larkspur went from 12 to 40 tours once we split the campaigns.",
                                          "speaker": "Whitney Hodges"}]}
    card = {**v7_card(), "moment_ids": ["moment_a", "moment_team"],
            "point": "We split a venue's campaigns before adding budget, and its tours went from 12 to 40."}
    ledger = v.verify_card(card, scenes_, ROSTER, [], team_practice={"moment_team"}, identities=[MARA, LARKSPUR],
                           identity_ids={"moment_team": []})
    kinds = {f["kind"]: f["severity"] for f in ledger["flags"]}
    assert kinds.get("team_practice_figure") == v.BLOCK and ledger["readiness"] == "research_required"
    named = {**v7_card(), "title": "What we learned from Mara about tours"}
    assert any(f["kind"] == "do_not_name" for f in v.verify_card({**named, "moment_ids": ["moment_a"]}, SCENES, ROSTER, [],
                                                                 identities=[MARA])["flags"])
    # The evidence points tell the reviewer who said what: they may name people.
    quoted = {**v7_card(), "evidence_points": ["Mara asked about tours (03:10)."], "moment_ids": ["moment_a"]}
    assert not any(f["kind"] == "do_not_name" for f in v.verify_card(quoted, SCENES, ROSTER, [], identities=[MARA])["flags"])


def test_the_brief_checks_block_a_do_not_link_reference_in_copy():
    doc, _ = document()
    doc["body"]["wia_perspective"] = "When a venue goes from $18K wasted to $52K booked, the work started with tracking."
    rules = load_rules(BACKEND_ROOT / "knowledge_base")
    found = checks_v4(doc, dossier(), {**provenance(), "identities": [MARA, LARKSPUR], "identity_ids": ["client_larkspur"]}, None, rules)
    assert any("$18K-to-$52K case study" in f["message"] and f["severity"] == "blocking" for f in found)
    assert not any("case study" in f["message"] for f in checks_v4(doc, dossier(), provenance(), None, rules)), \
        "a brief written before N8 (no identities in its provenance) is checked as before"


# Strategist v8 ------------------------------------------------------------------------------------------------------------

def packet():
    span = lambda t: {"span_id": "m1.t1", "source_id": "s1", "ordinal": 1, "start_seconds": 5.0, "end_seconds": 9.0,  # noqa: E731
                      "speaker": "Whitney Hodges", "text": f"Whitney Hodges: {t}"}
    return [{"moment_id": "moment_call", "source_ids": ["s1"], "moment_type": "decision", "sensitivity": "public_candidate",
             "source_evidence": [span("We hold the budget.")], "qualifications": []},
            {"moment_id": "moment_team", "source_ids": ["s2"], "moment_type": "team_practice", "sensitivity": "public_candidate",
             "source_evidence": [span("Two of us read every page on a phone first.")], "qualifications": []}]


def test_v8_is_v7_with_team_practice_identities_and_founder_notes():
    v7 = (TEMPLATES / "angle_generation.wia_strategist_v7.md").read_text(encoding="utf-8")
    v8 = (TEMPLATES / "angle_generation.wia_strategist_v8.md").read_text(encoding="utf-8")
    assert v8 != v7 and "## The five tests" in v8 and v8.split("## The five tests")[1].split("## The scenes and seeds")[0] == \
        v7.split("## The five tests")[1].split("## The scenes and seeds")[0], "the method and the five tests are v7's"
    for rule in ("team-practice scene", "never quote it in copy", "founder note", "never pair it with another call's scenes",
                 "## People and accounts", "recorded pronouns", "never a guessed pronoun", "never be linked"):
        assert rule in v8
    assert ap.STRATEGIST_V8_PROFILE in settings_store.CARD_PROFILES and ap.card_contract(ap.STRATEGIST_V8_PROFILE) is ap.card_contract(
        ap.STRATEGIST_V7_PROFILE)
    provenance_ = ap.EXAMPLE_PROVENANCE[ap.STRATEGIST_V8_PROFILE]
    assert all(2 not in (e["derived_from_weeks"] or []) for e in provenance_), "Week 2 is never used (D28)"
    for e in provenance_:
        assert e["text"] in v8 or e["kind"] == "rule", e["text"]


def test_v8s_user_message_marks_team_practice_lists_identities_and_names_a_founder_notes_call():
    seeds = [{"kind": "founder_note", "author": "Whitney Hodges", "text": "The phone read caught a broken form.",
              "call": "\"WIA Weekly Meeting\" (19 October 2026)"}]
    user = ap.strategist_user(packet(), ap.STRATEGIST_V8_PROFILE, seeds, None, team_practice={"moment_team"}, identities=[DANA])
    scene_2 = user.split("## Scene S2")[1].split("## Scene")[0]
    assert ap.TEAM_PRACTICE_HANDLING in scene_2 and ap.TEAM_PRACTICE_HANDLING not in user.split("## Scene S2")[0]
    assert ap.PEOPLE_LABEL in user and "fernbrookdana, Dani = Dana Reyes" in user
    assert user.index(ap.PEOPLE_LABEL) < user.index(ap.SEEDS_LABEL)
    assert "- Seed F1 (founder note, from Whitney Hodges, about the call \"WIA Weekly Meeting\" (19 October 2026)): The phone read" in user
    empty = ap.strategist_user(packet(), ap.STRATEGIST_V8_PROFILE, [], None, team_practice=set(), identities=[])
    assert "No outside person or account is recorded for these calls." in empty


def test_v7s_user_message_is_unchanged_by_n8():
    """A v7 run never sees the team-practice line or the identity records, so its saved answers still replay."""
    plain = ap.strategist_user(packet(), ap.STRATEGIST_V7_PROFILE, [], None)
    marked = ap.strategist_user(packet(), ap.STRATEGIST_V7_PROFILE, [], None, team_practice={"moment_team"}, identities=[DANA])
    assert plain == marked and ap.PEOPLE_LABEL not in plain and "team practice" not in plain


# Scene profile v4 ---------------------------------------------------------------------------------------------------------

def test_scene_v4_is_v3_with_internal_meetings_and_the_team_practice_type():
    v3 = (TEMPLATES / "scene_extraction.v3.md").read_text(encoding="utf-8")
    v4 = (TEMPLATES / "scene_extraction.v4.md").read_text(encoding="utf-8")
    assert "## Internal meetings" in v4 and "## Internal meetings" not in v3 and "**team_practice:**" in v4
    assert "There is no client contribution in an internal meeting" in v4
    assert "team_practice" in str(scenes.schema(scenes.SCENE_V4_PROFILE)) and "team_practice" not in str(scenes.schema(scenes.SCENE_V3_PROFILE))
    assert scenes.SCENE_V4_PROFILE in settings_store.DOCUMENT_EXTRACTION_PROFILES


def test_team_practice_outside_an_internal_meeting_is_kept_as_an_observation():
    output = {"scenes": [{"local_key": "a", "moment_type": "team_practice", "wia_moves": []},
                         {"local_key": "b", "moment_type": "team_practice", "wia_moves": []}]}
    work, changes = scenes.check_scene_types(output, call_type="client_1to1")
    assert [s["moment_type"] for s in work["scenes"]] == ["observation", "observation"] and changes[0]["rule"] == scenes.TEAM_RULE
    kept, none = scenes.check_scene_types(output, call_type="internal")
    assert [s["moment_type"] for s in kept["scenes"]] == ["team_practice", "team_practice"] and none == []
    assert output["scenes"][0]["moment_type"] == "team_practice", "the provider's output is never changed"


# Writer v5.2 --------------------------------------------------------------------------------------------------------------

def test_writer_v52_is_v51_with_people_what_happened_next_and_team_practice():
    v51 = (TEMPLATES / "brief_write.v5.1.md").read_text(encoding="utf-8")
    v52 = (TEMPLATES / "brief_write.v5.2.md").read_text(encoding="utf-8")
    for section in ("## People and accounts", "## What happened next", "## Evidence from internal meetings"):
        assert section in v52 and section not in v51
    assert v52.split("## Context the reviewers gave")[1] == v51.split("## Context the reviewers gave")[1], "the refresh blocks are v5.1's"
    assert "write exactly three Reels" in v52
    assert writer_for(StorageSettings(brief_writer="v5.2"), SCHEMA_V4) == "v5.2"
    assert writer_for(StorageSettings(brief_writer="v5.2"), SCHEMA_V4, revision="brief_x") == "v5.2"
    assert runtime.RENDERED_WRITERS["v5.2"] == "v5" and contract_for(SCHEMA_V4, "v5.2").write is BriefWriteV51
    settings_store.validate_profile({"settings": {"prompts.profile.brief": SCHEMA_V4, "prompts.profile.brief_writer": "v5.2"}})
    with pytest.raises(ValueError):
        settings_store.validate_profile({"settings": {"prompts.profile.brief": "brief_document_v3", "prompts.profile.brief_writer": "v5.2"}})


def test_v8_demotes_a_card_still_on_an_internal_only_scene_after_its_repair():
    output = {"angles": [{"rank": 1, "title": "A", "moment_ids": ["S1"]}, {"rank": 2, "title": "B", "moment_ids": ["S2", "S1"]},
                         {"rank": 3, "title": "C", "moment_ids": ["S3"]}],
              "internal_insights": [], "publishing_order": [3, 1, 2]}
    references = {"S1": "m1", "S2": "m2", "S3": "m3"}
    out, moved = ap.demote_internal_cards(output, references, {"m2": "internal_only"})
    assert [a["title"] for a in out["angles"]] == ["A", "C"] and [a["rank"] for a in out["angles"]] == [1, 2]
    assert out["publishing_order"] == [2, 1] and moved == [{"rank": 2, "title": "B"}]
    assert out["internal_insights"][0]["moment_ids"] == ["S2", "S1"] and "internal only" in out["internal_insights"][0]["use"]


def test_a_wrong_pronoun_beside_a_named_person_is_a_warning_and_they_never_is():
    found = identities.pronoun_findings({"guardrail": "Noa is a prospect; do not present him as a client."},
                                        [{**DANA, "name": "Noa Vale", "spellings": ["Noa Vale", "Noa"]}])
    assert [f["kind"] for f in found] == ["pronoun"] and found[0]["severity"] == "warning" and "'him'" in found[0]["message"]
    assert identities.pronoun_findings({"point": "Noa said they would test it; she did."},
                                       [{**DANA, "name": "Noa Vale", "spellings": ["Noa Vale", "Noa"]}]) == []
    card = {**v7_card(), "guardrail": "Dani is the owner; never show him as unhappy."}
    flags = v.verify_card({**card, "moment_ids": ["moment_a"]}, SCENES, ROSTER, [], identities=[DANA])["flags"]
    assert any(f["kind"] == "pronoun" and f["severity"] == v.CHECK for f in flags)


def test_the_brief_checks_block_a_client_name_or_figure_only_an_internal_meeting_gives():
    doc, _ = document()
    doc["body"]["wia_perspective"] = "When Shannon's venue moved to 45 inquiries a month, we knew the first reply had changed."
    shannon = {**DANA, "id": "person_shannon", "name": "Shannon Lee", "account": None, "spellings": ["Shannon Lee", "Shannon"],
               "naming": "anonymise"}
    rules = load_rules(BACKEND_ROOT / "knowledge_base")
    found = checks_v4(doc, dossier(), {**provenance(), "identities": [shannon], "team_practice_transcripts": ["t"]}, None, rules)
    messages = [f["message"] for f in found if f["severity"] == "blocking"]
    assert any("only an internal meeting mentions" in m and "Shannon" in m for m in messages)
    assert any("figure 45" in m and "only an internal meeting gives" in m for m in messages)
    plain = checks_v4(doc, dossier(), {**provenance(), "identities": [shannon]}, None, rules)
    assert not any("internal meeting" in f["message"] for f in plain), "the same evidence from a client call is not a leak"


def test_a_pack_blocks_a_never_named_person_even_when_its_approved_brief_carried_the_name():
    from backend_pipeline.packs import checks as pack_checks
    from backend_pipeline.tests import pack_v2_service_fixtures as fx
    from backend_pipeline.tests.test_packs_v2_checks import brief_row, run
    row = brief_row()
    plan = row["content_body"]["document"]["body"]["format_plan"]
    plan["email"]["body"] += " Mara from the venue team walked us through it."
    bodies = fx.from_brief(row["content_body"]["document"]["body"])
    assert not any("never be named" in f["message"] for f in run(row, bodies)), "no records, no identity check (as before N8)"
    row["content_body"]["provenance"]["identities"] = [MARA, DANA]
    found = [f for f in run(row, bodies) if f["severity"] == "blocking" and "never be named" in f["message"]]
    assert [f["piece"] for f in found] == ["email"] and "'Mara' (Mara Quill)" in found[0]["message"]
    consent = {e["evidence_id"]: "may_name" for e in row["selected_evidence"]}
    assert any("never be named" in f["message"] for f in run(row, bodies, consent=consent)), "no consent overrides it"
    plan["email"]["body"] = plan["email"]["body"].replace(" Mara from the venue team walked us through it.", "")
    marker = fx.from_brief(row["content_body"]["document"]["body"])
    marker["email"]["content"]["body"] += " The venue went from $18K to $52K."
    row["content_body"]["provenance"]["identity_ids"] = ["person_mara"]
    assert any("must never be linked" in f["message"] and f["severity"] == "blocking" for f in run(row, marker)), "her evidence"
    row["content_body"]["provenance"]["identity_ids"] = []
    assert not any("must never be linked" in f["message"] for f in run(row, marker)), "copy built on someone else: no link"

    class Frozen:  # the pack run's own records win over the brief's
        def execute(self, *_):
            return self

        def fetchone(self):
            return {"input_refs": {"identities": [DANA], "identity_ids": ["person_dana"]}}
    assert pack_checks.frozen_identities(Frozen(), {"production_run_id": "pack_run_x"}, row) == ([DANA], ["person_dana"])
    assert pack_checks.frozen_identities(None, {"production_run_id": "pack_run_x"}, row)[0] == [MARA, DANA]
