"""5.B14 (Markdown): the week's review document, rendered from the stored structure in the layout WIA reviews. Synthetic
cards and briefs only."""
from __future__ import annotations

import copy
from datetime import UTC, date, datetime

from backend_pipeline.briefs import review_document as doc
from backend_pipeline.tests.brief_v3_fixtures import v3_body
from backend_pipeline.tests.test_strategist_profile import card

PACKET = {"approved_angle": {"title": "How we read follow-up before ads", "core_perspective": "Follow-up shapes lead quality."},
          "card": {"pillar": "ATTRACT"},
          "evidence": [{"excerpt": "Strategist: How do you answer a new inquiry? We look there first.", "speaker": "Strategist",
                        "start_ms": 83000, "role": "anchor"}]}


def v3_brief(**changes):
    body = v3_body(PACKET, **changes)
    body["evidence"] = [{"evidence_id": "e1", "speaker": "Strategist", "start_ms": 83000, "quote": "How do you answer a new inquiry?"}]
    body["claims"] = []
    return {"brief_id": "brief_1", "approval_status": "pending", "approved_by": None, "updated_by": "system", "version_number": 1,
            "content_body": {"document": {"header": {"schema_version": "brief_document_v3"}, "body": body}}}


def angle(angle_id, rank, **card_changes):
    return {"angle_id": angle_id, "approval_status": "approved" if rank == 1 else "pending", "approved_by": "whitney@example.invalid",
            "content_body": {"card": card("m1", rank, **card_changes)}}


def material(briefs=None):
    return {"week": {"week_id": "week_2026-10-12", "week_start": date(2026, 10, 12), "week_end": date(2026, 10, 18)},
            "cards": [angle("a1", 1, pillar="ATTRACT"), angle("a2", 2)], "briefs": briefs if briefs is not None else {"a1": v3_brief()},
            "run_refs": {"window": {"start": "2026-10-12T00:00:00+00:00", "end": "2026-10-19T00:00:00+00:00"},
                         "transcripts": [{"id": "t1"}, {"id": "t2"}], "angle_prompt_profile": "2026-10-20.wia-strategist.v6"}}


def test_the_header_and_the_pack_layout_follow_the_review_document():
    text = doc.render(material(), exported=datetime(2026, 10, 27, 9, 0, tzinfo=UTC))
    lines = text.splitlines()
    assert lines[:5] == ["# Content Atelier Review", "", "Content Angles, Briefs and Packs", "", "Wedding Industry Ads"]
    assert "**Week:** 12 October 2026 to 18 October 2026" in text and "**Calls from:** 2026-10-12 to 2026-10-19 (2 calls)" in text
    assert "**Made by:** the Content Atelier system (cards: strategist profile 2026-10-20.wia-strategist.v6)" in text
    # The headings packs2docx.py reads, in its order.
    order = ["# Pack 1 · ATTRACT", "## Content angle", "### How we read a planner's lead quality, idea 1", "## Content brief",
             "## Email", "## Reel 1: The question we ask first", "## Carousel: Walk through the first reply", "## Caption",
             "## Before you publish Pack 1", "# Content bank", "## How we read a planner's lead quality, idea 2"]
    positions = [lines.index(h) for h in order]
    assert positions == sorted(positions)


def test_every_asset_line_is_rendered_from_the_structure():
    text = doc.render(material())
    body = v3_brief()["content_body"]["document"]["body"]
    plan = body["format_plan"]
    assert "**Content pillar / type:** ATTRACT · behind the scenes" in text
    assert "**Why this matters:** Owners stop blaming the platform." in text
    assert "**Editorial guardrail / next step:**\n\n- Confirm the client may be referenced." in text
    assert "**Gate 1:** developed by whitney@example.invalid" in text
    assert "**Central point.** Follow-up shapes lead quality." in text
    assert "**WIA perspective.** " + body["wia_perspective"] in text
    assert '- Strategist at 1:23: "How do you answer a new inquiry?"' in text
    assert "**SUBJECT:** The question we ask every new client" in text
    assert "**OTHER SUBJECT OPTIONS:** Before we touch your ads" in text and "**PREVIEW TEXT:** It starts after the inquiry." in text
    for copy_text in (plan["email"]["opening"], plan["email"]["body"], plan["email"]["ending"], plan["reels"][0]["script"],
                      plan["caption"]["hook"], plan["caption"]["body"], plan["caption"]["ending"]):
        assert copy_text in text, copy_text
    assert "**Cover:** The question we ask first" in text
    for slide in plan["carousel"]["slides"]:
        assert f"**Slide {slide['number']}**\n{slide['text']}" in text
    assert "- Confirm the client may be referenced. (required) Unanswered." in text
    assert "*Written by the Content Atelier system (brief contract v3). Gate 2: pending.*" in text


def test_contract_v4_fields_render_by_their_table_rows_when_present():
    brief = v3_brief()
    plan = brief["content_body"]["document"]["body"]["format_plan"]
    plan["email"].update(send_date="Tuesday 27 October 2026", send_time="Tuesday morning (confirm)", recipients="Full list (confirm)")
    plan["reels"][0].update(on_screen_hook="Why we lowered a new client's ad budget", caption="A Reel caption.\n\n-Whitney")
    plan["carousel"].update(title="Before we spent more, we spent less", caption="The carousel's caption.")
    text = doc.render(material({"a1": brief}))
    for line in ("**DATE:** Tuesday 27 October 2026", "**SEND TIME:** Tuesday morning (confirm)", "**RECIPIENTS:** Full list (confirm)",
                 "**On-screen hook:** Why we lowered a new client's ad budget", "A Reel caption.\n\n-Whitney",
                 "## Carousel: Before we spent more, we spent less", "The carousel's caption."):
        assert line in text, line
    # A new row is all a new field needs.
    rows = copy.copy(doc.REEL_FIELDS)
    try:
        doc.REEL_FIELDS.append(("B-roll", "b_roll"))
        plan["reels"][0]["b_roll"] = "Hands on a laptop"
        assert "**B-roll:** Hands on a laptop" in doc.render(material({"a1": brief}))
    finally:
        doc.REEL_FIELDS[:] = rows


def test_an_edited_version_names_the_person_and_a_v1_brief_renders_its_directions():
    edited = {**v3_brief(), "version_number": 3, "updated_by": "giselle@example.invalid", "approval_status": "approved",
              "approved_by": "whitney@example.invalid"}
    text = doc.render(material({"a1": edited}))
    assert ("Written by the Content Atelier system (brief contract v3); version 3, last changed at Gate 2 by "
            "giselle@example.invalid. Gate 2: approved by whitney@example.invalid") in text
    v1 = {"brief_id": "b1", "approval_status": "pending", "version_number": 1, "content_body": {"document": {
        "angle_statement": "Follow-up first.", "core_insight": "The reply matters.", "audience": "Owners", "audience_pain": "Quiet inquiries",
        "why_now": "Season planning.", "message_spine": ["One", "Two", "Three"], "narrative": ["Open", "Close"],
        "evidence_boundaries": ["No numbers."], "email": {"reader_job": "Explain.", "direction": "Story first."},
        "reels": [{"reader_job": "Hook.", "direction": "Face to camera."}], "carousel_reader_job": "Teach.",
        "carousel": [{"number": 1, "direction": "Promise."}], "cta": {"text": "Reply"},
        "open_questions": [{"text": "Is the client named?", "required": True, "answer": "No"}]}}}
    text = doc.render(material({"a1": v1}))
    assert "**Central point.** Follow-up first." in text and "- Reel 1: Hook. Face to camera." in text
    assert "- Is the client named? (required) Answer: No" in text and "## Email" not in text


def test_a_week_with_no_developed_card_still_has_the_content_bank():
    text = doc.render(material({}))
    assert "# Pack" not in text and "# Content bank" in text and text.count("\n## How we read") == 2


def test_a_week_with_no_cards_does_not_say_every_idea_was_developed():
    """Found by the N1 shakedown: the October week before its cycle exported 'Every idea this week was developed'."""
    text = doc.render({**material({}), "cards": []})
    assert "Every idea this week was developed" not in text and "No ideas for this week yet" in text
    assert "Every idea this week was developed" in doc.render(material({"a1": v3_brief(), "a2": v3_brief()}))


# Integration: strategist v7 cards and contract v4 briefs in WIA's layout ------------------------------------------------

V7 = dict(point="Lead quality is decided on the form, not in the ad account.", point_is_about="wia_belief",
          surprise_for_experienced_advertiser={"surprising": True, "reason": "They tune the ads first."},
          reader_takeaway="I want a team that reads the whole path.",
          reader_fit={"buyer": "elevate", "buyer_statement": "Owners who want leads that book.", "why": "Lead quality is their pain."},
          belief_ref="B3", guardrail="Do not name the client; keep the pricing vague.",
          offer_fit={"offer": "ELEVATE", "cta_slot": "soft_invitation", "calendar_note": "ELEVATE is open this window."},
          public_stance={"takes_stance": True, "stance": "AI cannot replace the strategy behind your ads."},
          recurrence="Came up on two calls.", verify_before_publishing=[])


def v7_angle(angle_id, rank, confirmed=False):
    value = angle(angle_id, rank, **V7)
    value["content_body"]["card"].pop("core_perspective")
    if confirmed:
        value["content_body"]["stance_confirmation"] = {"stance": V7["public_stance"]["stance"], "point": V7["point"],
                                                        "by": "whitney@example.invalid", "at": "2026-10-23T09:00:00+00:00"}
    return value


def test_a_v7_card_renders_its_fields_in_whitneys_order():
    text = doc.render({**material({}), "cards": [v7_angle("a1", 1, confirmed=True), v7_angle("a2", 2)]})
    first = text.split("## How we read a planner's lead quality, idea 2")[0]
    order = ["**Content pillar / type:**", "**Audience:**", "**Central point:** Lead quality is decided on the form, not in the ad account. (a WIA belief)",
             "**Would it surprise an owner who already runs ads:** Yes. They tune the ads first.", "**The reader:**",
             "- Comes away thinking: I want a team that reads the whole path.",
             "- Buyer: an ELEVATE buyer. Owners who want leads that book.", "**The belief it proves:** B3", "**Why this matters:**",
             "**WIA's expertise or process:**", "**Evidence in the referenced call:**", "**How often it came up:** Came up on two calls.",
             "**Editorial guardrail / next step:**", "- Do not name the client; keep the pricing vague.",
             "- Next step: ELEVATE, a soft invitation. ELEVATE is open this window.",
             "**Public stance:** AI cannot replace the strategy behind your ads. (confirmed by whitney@example.invalid on 2026-10-23)"]
    at = [first.index(line) for line in order]
    assert at == sorted(at), [line for line, i in zip(order, at)]
    assert "(not confirmed yet: an approver confirms it before the card is developed)" in text.split("## How we read a planner's lead quality, idea 2")[1]
    for stored in ("wia_belief", "soft_invitation", "takes_stance", "None"):
        assert stored not in text, stored


def test_every_v4_asset_field_appears_in_the_review_layout():
    from backend_pipeline.tests.brief_v4_fixtures import v4_body
    body = v4_body(PACKET)
    plan = body["format_plan"]
    plan["reels"][0]["personal_lines"] = ["Honestly, that one stuck with me."]
    plan["reels"][1]["offer_descriptor"] = "ELEVATE, our done-for-you ads management"
    plan["carousel"]["offer_descriptor"] = "the Ads Accelerators, where we launch your campaigns and guide you"
    plan["email"]["offer_descriptor"] = "ELEVATE, our done-for-you ads management"
    body.update(evidence=[], claims=[])
    brief = {"brief_id": "b4", "approval_status": "pending", "approved_by": None, "updated_by": "system", "version_number": 1,
             "content_body": {"document": {"header": {"schema_version": "brief_document_v4"}, "body": body}}}
    text = doc.render(material({"a1": brief}))
    assert "(brief contract v4)" in text
    expected = [f"**Central point.** {body['central_point']}", body["strategic_purpose"]["desired_response"],
                *body["supporting_example"]["timestamps"], "Details the copy uses: the first reply",
                "Who did what: our strategist: asked about the first reply",
                f"**DATE:** {plan['email']['send_header']['date']}", f"**SEND TIME:** {plan['email']['send_header']['send_time']}",
                f"**RECIPIENTS:** {plan['email']['send_header']['recipients']}", f"**Job:** {plan['email']['job']}", "**Register:** written",
                f"**PREVIEW TEXT:** {plan['email']['preview']}", "Offer descriptor: ELEVATE, our done-for-you ads management",
                "**Personal lines for Whitney to keep or cut:**\n\n- Honestly, that one stuck with me.",
                "**Offer descriptor:** ELEVATE, our done-for-you ads management",
                "**Offer descriptor:** the Ads Accelerators, where we launch your campaigns and guide you",
                f"## Carousel: {plan['carousel']['title']}", "*Job: The promise*"]
    for reel in plan["reels"]:
        expected += [f"**Cover:** {reel['cover_text']}", f"**On-screen hook:** {reel['on_screen_hook']}", f"**Register:** {reel['register'].replace('_', ' ')}",
                     f"**Job:** {reel['job']}", reel["caption"]["hook"], reel["caption"]["body"], reel["caption"]["ending"]]
        expected += [s for s in reel["screens"] or []] + ([reel["script"]] if reel["script"] else [])
    expected += [plan["carousel"]["caption"][k] for k in ("hook", "body", "ending")]
    expected += [plan["email"][k] for k in ("opening", "body", "ending")] + plan["email"]["subject_options"]
    expected += [f"**Slide {s['number']}**\n{s['text']}" for s in plan["carousel"]["slides"]]
    for line in expected:
        assert line in text, line
    assert text.index("## Email") < text.index("## Reel 1:") < text.index("## Reel 3:") < text.index("## Carousel:")


def test_an_evidence_quote_names_its_speaker_once():
    """N1 shakedown: 'Steve's iPhone at 1:50: "Steve's iPhone: Okay, got it."'."""
    brief = v3_brief()
    brief["content_body"]["document"]["body"]["evidence"] = [dict(evidence_id="e1", speaker="Owner", start_ms=110000,
                                                                  quote="Owner: Okay, got it.")]
    text = doc.render(material({"a1": brief}))
    assert '- Owner at 1:50: "Okay, got it."' in text and "Owner: Owner" not in text
