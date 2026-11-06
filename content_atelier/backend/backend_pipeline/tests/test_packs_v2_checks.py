"""NP.B4 offline: the deterministic checks of a content pack on synthetic fixtures that reproduce the planning probe's failure
patterns (an invented quote of dialogue, "explained" turned into "agreed" inside a quote, a price hint with a "$" figure, a
hedge stated as certain inside a quote, a client named under anonymise), each with a failing and a passing case; then
composition, format, US spelling, client quotes and the week. Invented text only; no real call text (R48). No database."""
from __future__ import annotations

import copy

import pytest

from backend_pipeline.packs import checks
from backend_pipeline.tests import pack_v2_service_fixtures as fx
from backend_pipeline.tests.test_brief_v3 import EVIDENCE, dossier, provenance
from backend_pipeline.tests.test_brief_v4 import document

CLIENT, STAFF = "Shannon Lee", "Carmen Cruickshank"


def turn(evidence_id, speaker, said, *, transcript="t", public=False):
    # A synthetic turn, built here so the file holds no transcript-shaped JSON (R48, test_client_material_guard).
    return {"evidence_id": evidence_id, "transcript_id": transcript, "excerpt": f"{speaker}: {said}", "title": "Call",
            "speaker": speaker, "start_ms": 20000, "role": "support", "moment_ids": ["m1"], "public_use": public,
            "attribution_verified": public}


PROBE = [turn("ev_explained", STAFF, "I explained that we would test the new page before we moved the ad traffic.", public=True),
         turn("ev_hedge", CLIENT, "It might bring in more inquiries, but I am not sure yet."),
         turn("ev_phone", CLIENT, "Um, I just, I just want the phone to ring with the right couples."),
         turn("ev_lake", CLIENT, "Lakeview Barn gets most of its couples from the website.", transcript="t_lake")]
LAKEVIEW = {"client_id": "client_lake", "name": "Lakeview Barn", "aliases": [], "consent": "anonymise_only", "transcript_ids": ["t_lake"]}


def brief_row(*, clients=(), clearances=None):
    doc, _ = document()
    prov = {**provenance(), "angle": dossier().angle, "brand_hash": "b", "clients": list(clients)}
    return {"brief_id": "brief_synthetic", "week_id": "w", "angle_id": "angle_1", "content_hash": "h", "approved_hash": "h",
            "approved_by": "approver", "supersedes_id": None,
            "content_body": {"schema_version": "brief_document_v4", "document": doc, "provenance": prov,
                             "review": {"clearances": clearances or {}}},
            "selected_evidence": [*EVIDENCE, *PROBE], "prior_content_context": [], "research_gaps": {"coverage": {}, "items": []}}


@pytest.fixture(scope="module")
def base():
    row = brief_row()
    return row, fx.from_brief(row["content_body"]["document"]["body"])


def run(row, bodies, body=None, **kw):
    return checks.findings(None, {"content_body": body or fx.pack_body(row)}, bodies, row, **kw)


def add_to(bodies, key, path, sentence):
    out = copy.deepcopy(bodies)
    content = out[key]["content"]
    if "." in path:
        head, leaf = path.split(".")
        content[head][leaf] = content[head][leaf] + " " + sentence
    else:
        content[path] = content[path] + " " + sentence
    return out


def of(found, check, severity=None):
    return [f for f in found if f["check"] == check and (severity is None or f["severity"] == severity)]


def blocking(found):
    return [f for f in found if f["severity"] == "blocking"]


def test_a_pack_of_the_approved_brief_s_copy_has_no_blocking_finding_and_stable_ids(base):
    row, bodies = base
    found = run(row, bodies)
    assert not blocking(found), blocking(found)
    assert all(f["source"] == "check" and f["status"] == "open" and f["finding_id"].startswith("check_") for f in found)
    assert [f["finding_id"] for f in found] == [f["finding_id"] for f in run(row, bodies)], "ids are stable across reads"


def test_an_invented_quote_of_dialogue_blocks_and_the_call_s_own_words_pass_with_their_fillers(base):
    row, bodies = base
    invented = run(row, add_to(bodies, "reel_1", "script", 'She told us, "I need the ads to fill every Saturday this fall."'))
    (f,) = of(invented, "pack.quote_exact")
    assert f["severity"] == "blocking" and f["piece"] == "reel_1" and f["path"] == "script"
    assert "nobody says those words on the call" in f["message"] and f["sentence"].startswith("I need the ads")
    said = run(row, add_to(bodies, "reel_1", "script", 'She told us, "I just want the phone to ring with the right couples."'))
    assert not of(said, "pack.quote_exact") and not of(said, "pack.quote_attributed")
    assert not blocking(said), "a client's quote is a note for whoever posts, never a gate"


def test_explained_turned_into_agreed_inside_a_quote_blocks(base):
    row, bodies = base
    agreed = run(row, add_to(bodies, "email", "body", 'Our strategist said, "I agreed that we would test the new page before we moved the ad traffic."'))
    assert [f["piece"] for f in of(agreed, "pack.quote_exact", "blocking")] == ["email"]
    explained = run(row, add_to(bodies, "email", "body",
                                'Our strategist said, "I explained that we would test the new page before we moved the ad traffic."'))
    assert not of(explained, "pack.quote_exact") and not of(explained, "pack.quote_attributed")


def test_a_quote_credited_to_the_wrong_speaker_blocks(base):
    row, bodies = base
    found = run(row, add_to(bodies, "email", "body", 'She said, "I explained that we would test the new page before we moved the ad traffic."'))
    (f,) = of(found, "pack.quote_attributed")
    assert f["severity"] == "blocking" and "credits" in f["message"] and "our team said it" in f["message"]


def test_a_hedge_stated_as_certain_inside_a_quote_blocks(base):
    row, bodies = base
    certain = run(row, add_to(bodies, "reel_1", "caption.body", 'She told us, "It will bring in more inquiries."'))
    assert of(certain, "pack.quote_exact", "blocking")
    hedged = run(row, add_to(bodies, "reel_1", "caption.body", 'She told us, "It might bring in more inquiries."'))
    assert not of(hedged, "pack.quote_exact")


def test_a_price_hint_with_a_dollar_figure_blocks_and_a_figure_the_call_holds_passes(base):
    row, bodies = base
    priced = run(row, add_to(bodies, "carousel", "caption.body", "Most venues spend about $3,000 a month before they call us."))
    (f,) = of(priced, "pack.new_number")
    assert f["severity"] == "blocking" and "$3,000" in f["message"] and f["piece"] == "carousel" and f["path"] == "caption.body"
    held = run(row, add_to(bodies, "carousel", "caption.body", "She went to 45 inquiries a month."))
    assert not of(held, "pack.new_number"), "45 is a figure the call holds"


def test_a_name_the_brief_and_the_call_do_not_hold_blocks(base):
    row, bodies = base
    named = run(row, add_to(bodies, "email", "body", "We built it with Margot from the venue team."))
    (f,) = of(named, "pack.new_name")
    assert f["severity"] == "blocking" and "Margot" in f["message"]
    staff = run(row, add_to(bodies, "email", "body", "We built it with Carmen from our team."))
    assert not of(staff, "pack.new_name") and not blocking(staff), "WIA staff may be credited"


def test_a_client_named_under_anonymise_blocks_unless_a_clearance_allows_it():
    row = brief_row(clients=[LAKEVIEW])
    bodies = add_to(fx.from_brief(row["content_body"]["document"]["body"]), "email", "body",
                    "The owner of Lakeview Barn walked us through her follow-up.")
    found = run(row, bodies)
    assert [f["piece"] for f in of(found, "consent.names", "blocking") if "Lakeview Barn (a client)" in f["message"]] == ["email"]
    cleared = brief_row(clients=[LAKEVIEW], clearances={"ev_lake": {"permission_reference": "email of 3 October",
                                                                     "attribution_reference": "call at 0:20"}})
    assert not blocking(run(cleared, bodies)), "a clearance on the client's own evidence allows the name"


def test_a_client_speaker_is_named_only_with_their_consent_to_be_named(base):
    row, bodies = base
    named = add_to(bodies, "email", "body", "Shannon walked us through her follow-up.")
    assert any("Shannon (not WIA staff)" in f["message"] for f in of(run(row, named), "consent.names", "blocking"))
    consent = {e["evidence_id"]: "may_name" for e in row["selected_evidence"] if e["speaker"] == CLIENT}
    assert not blocking(run(row, named, consent=consent)), "may_name consent allows the name"


def test_a_line_a_person_wrote_warns_instead_of_blocking(base):
    row, bodies = base
    mine = add_to(bodies, "reel_1", "script", 'She told us, "I need the ads to fill every Saturday this fall." It cost $3,000.')
    mine["reel_1"]["locks"] = [{"path": "script", "author": "giselle@example.invalid", "delegated": True, "at": None, "origin": "pack"}]
    found = run(row, mine)
    assert of(found, "pack.quote_exact", "warning") and of(found, "pack.new_number", "warning")
    assert not of(found, "pack.quote_exact", "blocking") and not of(found, "pack.new_number", "blocking")


def test_a_client_quote_in_copy_is_listed_for_its_okay_and_never_blocks(base):
    row, bodies = base
    quoted = add_to(bodies, "reel_1", "script", 'She told us, "I just want the phone to ring with the right couples."')
    (note,) = of(run(row, quoted), "pack.client_quote_listed")
    assert note["severity"] == "warning" and note["piece"] == "reel_1" and "client's okay before posting" in note["message"]
    listed = fx.pack_body(row, client_quotes=[{"quote_id": "Q1", "piece": "email", "quote": "An earlier quote", "speaker": CLIENT,
                                               "evidence_id": "ev_b", "cleared": None}])
    (added,) = checks.missing_client_quotes(listed, quoted, row)
    assert added["quote_id"] == "Q2" and added["piece"] == "reel_1" and added["speaker"] == CLIENT and added["evidence_id"] == "ev_phone"
    done = {**listed, "client_quotes": [*listed["client_quotes"], added]}
    assert not of(run(row, quoted, done), "pack.client_quote_listed") and not checks.missing_client_quotes(done, quoted, row)


def test_composition_blocks_a_reel_not_written_with_its_reason_and_a_reel_of_the_wrong_kind(base):
    row, _ = base
    two = fx.from_brief(row["content_body"]["document"]["body"], kinds=("story", "broll_text"))
    (f,) = of(run(row, two), "pack.composition")
    assert f["severity"] == "blocking" and f["message"] == f"Reel 2 (stance) was not written: {fx.NOT_WRITTEN}"
    swapped = fx.from_brief(row["content_body"]["document"]["body"])
    swapped["reel_2"]["content"]["kind"] = "story"
    assert any("Reel 2 is the stance Reel" in f["message"] for f in of(run(row, swapped), "pack.composition", "blocking"))


def test_a_brief_check_lands_on_the_pack_s_piece_and_label_when_a_reel_was_not_written(base):
    row, _ = base
    two = fx.from_brief(row["content_body"]["document"]["body"], kinds=("story", "broll_text"))
    two["reel_3"]["content"]["on_screen_hook"] = "One question from office hours"
    (f,) = [f for f in run(row, two) if f["check"] == "first_touch.insider_term"]
    assert f["severity"] == "blocking" and f["piece"] == "reel_3" and f["path"] == "on_screen_hook"
    assert f["message"].startswith("Reel 3's on-screen hook"), "relabelled from the second written Reel to the pack's Reel 3"


def _sentence(n):
    return " ".join(["the reply"] * (n // 2))


def test_format_warnings_name_what_to_change_and_a_piece_in_the_house_format_has_none(base):
    row, bodies = base
    good = copy.deepcopy(bodies)
    email = good["email"]["content"]
    email.update(subject_options=["One", "Two", "Three"], body=_sentence(300))
    for slide in good["carousel"]["content"]["slides"]:
        slide["text"] = _sentence(14) + "\n" + _sentence(14) + "\n" + _sentence(6)
    for key in ("carousel", "reel_1", "reel_2", "reel_3"):
        good[key]["content"]["caption"]["body"] = _sentence(170)
    for key in ("reel_1", "reel_2"):
        good[key]["content"]["script"] = _sentence(150)
    assert not checks.format_findings(good)
    bad = copy.deepcopy(good)
    bad["email"]["content"]["subject_options"] = ["One", "Two"]
    bad["carousel"]["content"]["slides"][2]["text"] = "Too short"
    bad["reel_1"]["content"]["title"] = bad["reel_1"]["content"]["job"]
    bad["reel_3"]["content"]["screens"] = []
    bad["reel_2"]["content"]["caption"]["body"] = "Short."
    messages = [f["message"] for f in checks.format_findings(bad)]
    assert "The email has 2 subject options: give three, best first" in messages
    assert any(m.startswith("Carousel slide 3 has 1 line") for m in messages)
    assert any(m.startswith("Carousel slide 3 has 2 words") for m in messages)
    assert "Reel 1's title repeats its creative direction: give it a working title of its own" in messages
    assert "Reel 3 is on-screen text and needs one to three screens" in messages
    assert any(m.startswith("Reel 2's caption runs") for m in messages)
    assert all(f["severity"] == "warning" for f in checks.format_findings(bad))


def test_british_spelling_is_a_warning_with_the_us_form(base):
    row, bodies = base
    british = add_to(bodies, "email", "body", "We prioritise enquiries in her favourite colour.")
    found = of(run(row, british), "pack.us_spelling")
    assert {f["message"].split('"')[1] for f in found} == {"prioritise", "enquiries", "favourite", "colour"}
    assert all(f["severity"] == "warning" and f["piece"] == "email" for f in found)
    assert any('write "inquiries"' in f["message"] for f in found)
    assert not of(run(row, add_to(bodies, "email", "body", "We prioritize inquiries.")), "pack.us_spelling")


def test_the_week_keeps_one_offer_ask_on_instagram_and_distinct_covers(base):
    row, bodies = base
    mine = copy.deepcopy(bodies)
    mine["reel_1"]["content"]["cta"] = "offer"
    other = copy.deepcopy(bodies)
    other["carousel"]["content"]["cta"] = "offer"
    sibling = {"pack_id": "pack_other", "title": "Another idea", "pieces": other, "body": {}, "created_at": None}
    pack = {"pack_id": "pack_mine", "week_id": "w", "source_brief_id": "brief_synthetic", "content_body": fx.pack_body(row)}
    found = checks.week_findings(None, pack, mine, [sibling])
    (offer,) = of(found, "week.offer_cta")
    assert offer["severity"] == "warning" and "Give Reel 1 a no-offer ending" in offer["message"]
    assert of(found, "week.distinct"), "the sibling repeats this pack's covers and hooks"
    mine["reel_1"]["content"]["no_offer_ending"] = "That's where we start. -Whitney"
    other["carousel"]["content"]["no_offer_ending"] = "Follow-up is part of the advertising."
    assert not of(checks.week_findings(None, pack, mine, [sibling]), "week.offer_cta"), "the week plan can post one ask"
    distinct = copy.deepcopy(other)
    for key in ("reel_1", "reel_2", "reel_3"):
        distinct[key]["content"]["cover_text"] = f"A different cover {key[-1]} about pricing pages"
        distinct[key]["content"]["on_screen_hook"] = f"A different hook {key[-1]} about pricing pages"
    distinct["email"]["content"]["subject_options"] = ["Pricing pages that work", "Another subject entirely"]
    assert not of(checks.week_findings(None, pack, mine, [{**sibling, "pieces": distinct}]), "week.distinct")
    assert not of(run(row, mine), "week.offer_cta"), "week findings run only when siblings are given"


def test_a_reel_beat_is_direction_and_never_raises_a_blocking_finding(base):
    """NP.X3: a beat ("with no results") is a note for the maker, never published, and not editable in the pack: the pack's
    checks judge only its copy, so it raises nothing, while the same words in a caption still do."""
    row, bodies = base
    beat = copy.deepcopy(bodies)
    beat["reel_1"]["content"]["beats"] = [*beat["reel_1"]["content"]["beats"], "Show the two pages side by side, with no results."]
    assert not blocking(run(row, beat))
    said = add_to(bodies, "reel_1", "caption.body", "The new page brought no results.")
    assert any("no results" in f["message"] for f in blocking(run(row, said))), "in copy it is still judged"
