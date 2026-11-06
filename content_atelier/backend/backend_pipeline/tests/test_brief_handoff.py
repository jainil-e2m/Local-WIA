"""E.B23 offline: the production hand-off's piece keys, anchor rule, a person's anchor choice and the message spine, for
v1, v2 and v3 briefs. No database, no HTTP, no model call."""
from __future__ import annotations

import copy

import pytest

from backend_pipeline.briefs import handoff
from backend_pipeline.briefs.contracts_v2 import SCHEMA_V2, BriefBodyV2
from backend_pipeline.briefs.contracts_v3 import COPY, DIRECTION, SCHEMA_V3, CaptionPlanV3, EmailPlanV3, ReelPlanV3, writer_schema_v3
from backend_pipeline.tests.brief_v2_fixtures import v2_body
from backend_pipeline.tests.brief_v3_fixtures import v3_body


def _turn(evidence_id, speaker, said):
    # Synthetic evidence built by a helper, so this file holds no transcript-shaped JSON (test_client_material_guard).
    return {"evidence_id": evidence_id, "speaker": speaker, "start_ms": 1000, "excerpt": f"{speaker}: {said}", "role": "anchor"}


PACKET = {"approved_angle": {"title": "Why we ask about follow-up first", "core_perspective": "Follow-up shapes lead quality."},
          "card": {"pillar": "WARM"}, "evidence": [_turn("ev_a", "Carmen", "How do you reply to a new inquiry today?")]}


def row(version, body, anchor=None):
    review = {"locked_fields": [], "findings": [], **({"anchor": anchor} if anchor else {})}
    return {"content_body": {"schema_version": version, "document": {"header": {}, "body": body}, "review": review}}


def v3(**changes):
    return row(SCHEMA_V3, v3_body(PACKET, **changes))


def v1(reels=3):
    direction = {"reader_job": "Understand", "direction": "Explain", "outline": ["One"], "evidence_ids": ["ev_a"]}
    document = {"title": "T", "core_insight": "A reported change is a starting point.",
                "message_spine": ["Inspect the observation", "A reported change is a starting point.", "Choose a review"],
                "reels": [direction] * reels, "carousel_reader_job": "Apply it",
                "carousel": [{"number": n, "direction": f"Step {n}", "evidence_ids": ["ev_b"]} for n in range(1, 9)], "email": direction}
    return {"content_body": {"document": document, "review": {"locked_fields": [], "findings": []}}}


def test_every_piece_has_a_stable_key_from_the_plan_and_the_first_reel_is_the_anchor():
    brief = v3()
    two_reels = copy.deepcopy(brief)
    plan = two_reels["content_body"]["document"]["body"]["format_plan"]
    plan["reels"].append(copy.deepcopy(plan["reels"][0]))
    assert [p["key"] for p in handoff.pieces(brief)] == ["reel_1", "carousel", "email", "caption"]
    assert [p["key"] for p in handoff.pieces(two_reels)] == ["reel_1", "reel_2", "carousel", "email", "caption"]
    assert [p["key"] for p in handoff.pieces(two_reels)] == [p["key"] for p in handoff.pieces(copy.deepcopy(two_reels))], "same plan, same keys"
    assert {p["key"]: (p["channel"], p["platform"]) for p in handoff.pieces(brief)} == {
        "reel_1": ("reel", "instagram"), "carousel": ("carousel", "instagram"), "email": ("email", "email"), "caption": ("caption", "instagram")}
    anchor = handoff.anchor_of(brief)
    assert anchor["key"] == "reel_1" and anchor["chosen_by"] == "rule" and anchor["note"] is None
    assert [o["key"] for o in anchor["options"]] == ["reel_1", "carousel", "email", "caption"]


@pytest.mark.parametrize("dropped, expected", [(("reels",), "carousel"), (("reels", "carousel"), "email"),
                                               (("reels", "carousel", "email"), "caption"), (("reels", "carousel", "email", "caption"), None)])
def test_the_anchor_rule_falls_back_in_order(dropped, expected):
    brief = v3()
    plan = brief["content_body"]["document"]["body"]["format_plan"]
    for name in dropped:
        plan[name] = [] if name == "reels" else None
    assert handoff.anchor_of(brief)["key"] == expected
    assert handoff.default_anchor(["stories"]) == "stories"


def test_a_person_chooses_the_anchor_and_a_choice_whose_piece_left_the_plan_falls_back_to_the_rule():
    brief = v3()
    handoff.choose_anchor(brief, "email", "approver@example.invalid")
    chosen = handoff.anchor_of(brief)
    assert chosen["key"] == "email" and chosen["chosen_by"] == "person" and chosen["actor"] == "approver@example.invalid"
    with pytest.raises(ValueError, match="one of this brief's pieces: reel_1, carousel, email, caption"):
        handoff.choose_anchor(brief, "reel_4", "approver@example.invalid")
    brief["content_body"]["document"]["body"]["format_plan"]["email"] = None
    stale = handoff.anchor_of(brief)
    assert stale["key"] == "reel_1" and stale["chosen_by"] == "rule" and "(email) is no longer in the format plan" in stale["note"]
    handoff.choose_anchor(brief)  # KEEP: an edit that removed the piece drops the stale choice
    assert "anchor" not in brief["content_body"]["review"]
    handoff.choose_anchor(brief, "carousel", "a")
    handoff.choose_anchor(brief, None, "a")
    assert handoff.anchor_of(brief)["chosen_by"] == "rule", "null returns to the rule"
    assert handoff.parent_anchor({"content_body": {"review": {"anchor": {"key": "email"}}}}) == {"anchor": {"key": "email"}}
    assert handoff.parent_anchor(None) == {}


def test_copy_and_direction_follow_the_v3_contract_marks():
    """The hand-off's copy and direction tables agree with contracts_v3's field descriptions (COPY, DIRECTION)."""
    for model, (copy_fields, direction_fields) in ((ReelPlanV3, handoff.REEL[SCHEMA_V3]), (EmailPlanV3, handoff.EMAIL[SCHEMA_V3]),
                                                  (CaptionPlanV3, handoff.CAPTION[SCHEMA_V3])):
        marked = {name: (f.description or "") for name, f in model.model_fields.items()}
        assert {n for n, d in marked.items() if d.startswith(COPY)} == set(copy_fields), model.__name__
        assert {n for n, d in marked.items() if d.startswith(DIRECTION)} <= set(direction_fields), model.__name__
        assert set(copy_fields) | set(direction_fields) == set(marked), f"{model.__name__}: every field is copy or direction"
    pieces = {p["key"]: p for p in handoff.pieces(v3())}
    assert set(pieces["reel_1"]["copy"]) == {"cover_text", "spoken_opening", "script"} and pieces["reel_1"]["evidence_ids"] == []
    assert pieces["carousel"]["copy"]["slides"][0] == {"number": 1, "text": "Slide text about follow-up, part A."}
    assert pieces["carousel"]["direction"]["slides"][0] == {"number": 1, "job": "Step 1"}
    assert set(pieces["email"]["copy"]) == {"subject_options", "preview", "opening", "body", "ending"}


def test_a_v2_brief_maps_with_its_cited_evidence_and_its_directions():
    body = BriefBodyV2.model_validate(v2_body({**PACKET, "evidence": [{**PACKET["evidence"][0], "excerpt": "How do you reply today?"}]})).model_dump(mode="json")
    pieces = {p["key"]: p for p in handoff.pieces(row(SCHEMA_V2, body))}
    assert pieces["reel_1"]["evidence_ids"] == ["ev_a"] and "script" not in pieces["reel_1"]["copy"]
    assert list(pieces) == ["reel_1", "carousel", "email", "caption"]
    assert set(pieces["email"]["copy"]) == {"subject_options", "preview", "opening", "ending"}
    assert set(pieces["email"]["direction"]) == {"argument", "transformation"}
    assert pieces["caption"]["direction"] == {"adds": body["format_plan"]["caption"]["adds"]}


def test_a_v1_brief_maps_its_three_reels_carousel_and_email_as_direction():
    pieces = handoff.pieces(v1())
    assert [p["key"] for p in pieces] == ["reel_1", "reel_2", "reel_3", "carousel", "email"]
    assert all(p["copy"] == {} for p in pieces) and pieces[3]["evidence_ids"] == ["ev_b"]
    assert handoff.anchor_of(v1())["key"] == "reel_1"
    spine = handoff.message_spine(v1())
    assert spine == {"text": "A reported change is a starting point.", "source": "core_insight",
                     "supporting": ["Inspect the observation", "Choose a review"]}


def test_the_message_spine_is_the_sharpened_point_else_the_approved_perspective():
    plain = handoff.message_spine(v3())
    assert plain["text"] == "Follow-up shapes lead quality." and plain["source"] == "approved_angle"
    assert plain["supporting"] == ["We look at what happens after the inquiry before we change a single ad.", "Follow-up is part of the ad."]
    sharpened = handoff.message_spine(v3(sharpened_point={"text": "The ad starts the sale; the reply finishes it.", "reason": "Sharper"}))
    assert sharpened["text"] == "The ad starts the sale; the reply finishes it." and sharpened["source"] == "sharpened_point"


def test_the_writer_request_is_unchanged():
    """The anchor, the keys and the spine are derived after writing: nothing reaches the writer's schema."""
    text = str(writer_schema_v3(["reel", "carousel", "email", "caption"]))
    assert "anchor" not in text and "spine" not in text and "reel_1" not in text


class _Rows:
    def __init__(self, rows):
        self.rows = rows

    def fetchone(self):
        return self.rows[0] if self.rows else None


class _Conn:
    """Answers the two reads publishing() makes: the angle's run, then that run's card-generation result."""
    def __init__(self, order):
        self.order = order

    def execute(self, sql, params):
        if "content_angles" in sql:
            return _Rows([{"run_id": "run_1"}])
        return _Rows([{"result_refs": {"publishing_order": self.order}}] if self.order is not None else [])


@pytest.mark.parametrize("order, expected", [([3, 2, 1], {"rank": 2, "position": 2, "of": 3, "held": False, "known": True}),
                                             ([1, 3], {"rank": 2, "position": None, "of": 2, "held": True, "known": True}),
                                             (None, {"rank": 2, "position": None, "of": None, "held": False, "known": False})])
def test_the_series_and_publishing_order_come_from_the_card_and_its_run(order, expected):
    brief = {"angle_id": "angle_1", "content_body": {"provenance": {"angle": {"body": {"card": {"rank": 2, "series": "Behind the ads"}}}}}}
    assert handoff.publishing(_Conn(order), brief) == {"series": "Behind the ads", "publishing_order": expected}
