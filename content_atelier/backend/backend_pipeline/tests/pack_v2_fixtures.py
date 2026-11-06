"""Synthetic content pack v2 fixtures (Phase NP): a v4 brief row, its hand-off view v2 built without a database, and a
finisher answer. Anonymised, invented text only (R48)."""
from __future__ import annotations

import copy

from backend_pipeline.briefs import handoff as H
from backend_pipeline.tests.brief_v4_fixtures import v4_body

PACKET = {"evidence": [{"excerpt": "How do you answer a new inquiry? We ask that first."}],
          "approved_angle": {"title": "How we read follow-up before the ads", "core_perspective": "Follow-up is part of the ad."},
          "card": {"pillar": "WARM"}}
EVIDENCE = [{"evidence_id": "ev_synthetic_1", "speaker": "Our strategist", "start_ms": 4000, "quote": "How do you answer a new inquiry?",
             "client_consent": "anonymise", "call_date": "2026-10-14T15:00:00+00:00", "quotable": False},
            {"evidence_id": "ev_synthetic_2", "speaker": "The owner", "start_ms": 9000,
             "quote": "Honestly, um, it usually takes us two days to reply.", "client_consent": "anonymise",
             "call_date": "2026-10-14T15:00:00+00:00", "quotable": True}]


def brief_row(kinds=("story", "stance", "broll_text"), locked=(), changes=None):
    body = v4_body(PACKET)
    body["format_plan"]["reels"] = [r for r in body["format_plan"]["reels"] if r["kind"] in kinds]
    if changes:
        for path, value in changes.items():
            from backend_pipeline.briefs import paths
            body = paths.put(body, path, value)
    body["claims"] = [{"claim_id": "c_1", "text": "Our strategist asked how the owner answers a new inquiry.",
                       "claim_class": "particular_interaction", "evidence_ids": ["ev_synthetic_1"], "knowledge_base_document": None,
                       "numeric_facts": [], "quote": None, "public_quote": False, "field": "supporting_example.scene",
                       "status": "supported", "settled_by": "verifier", "note": None, "flag": None},
                      {"claim_id": "c_2", "text": "The owner said replies usually take two days.", "claim_class": "particular_interaction",
                       "evidence_ids": ["ev_synthetic_2"], "knowledge_base_document": None, "numeric_facts": [],
                       "quote": "it usually takes us two days to reply", "public_quote": True,
                       "field": "format_plan.reels[1].script", "status": "supported", "settled_by": "verifier", "note": None,
                       "flag": None}]
    body["evidence"] = [{"evidence_id": e["evidence_id"], "speaker": e["speaker"], "start_ms": e["start_ms"], "quote": e["quote"]}
                        for e in EVIDENCE]
    header = {"schema_version": "brief_document_v4", "angle_id": "angle_synthetic", "angle_hash": "h", "purpose": "WARM",
              "content_type": "behind_the_scenes", "audience": "Established venue owners", "intended_shift": body["intended_shift"],
              "point_of_view": "we", "cta": body["cta"], "channels": ["reel", "carousel", "email", "caption"], "pinned_inputs": {}}
    return {"brief_id": "brief_synthetic", "content_hash": "hash_synthetic", "approval_status": "approved",
            "approved_hash": "hash_synthetic", "approved_by": "approver@example.com", "approved_at": None, "can_consume": True,
            "blockers": [], "week_id": "week_2026-10-12", "angle_id": "angle_synthetic", "supersedes_id": None,
            "updated_by": "approver@example.com",
            "content_body": {"schema_version": "brief_document_v4", "document": {"header": header, "body": body},
                             "review": {"locked_fields": list(locked)}, "provenance": {}}}


def handoff_v2(row, authors=None):
    """Hand-off view v2 as view_v2 builds it, without the parts that need a database (topics, publishing order, consent)."""
    pieces = H.pieces(row)
    anchor = H.anchor_of(row, pieces)
    for p in pieces:
        p["anchor"] = p["key"] == anchor["key"]
    locks = H.locks(None, row)
    for lock in locks:
        lock["author"] = (authors or {}).get(lock["path"], "approver@example.com")
    places = {p["claim_id"]: p for p in H.claim_places(row)}
    return {"handoff_version": H.HANDOFF_VERSION_V2, "brief_id": row["brief_id"], "schema_version": "brief_document_v4",
            "content_hash": row["content_hash"], "approved_hash": row["approved_hash"], "approved_by": row["approved_by"],
            "can_consume": True, "week_id": row["week_id"], "angle_id": row["angle_id"],
            "title": row["content_body"]["document"]["body"]["approved_angle"]["title"], "purpose": "WARM",
            "cta": H._cta(row), "message_spine": H.message_spine(row), "anchor": {"key": anchor["key"]}, "pieces": pieces,
            "publishing_order": {"rank": 1}, "claims": [{**c, **{k: v for k, v in places[c["claim_id"]].items() if k != "claim_id"}}
                                                        for c in H.claims(row)],
            "before_publishing": H.before_publishing(row), "evidence": copy.deepcopy(EVIDENCE), "strategy": H.strategy(row),
            "locks": locks, "context": [], "beliefs": None, "offer_descriptors": []}


def caption(hook, body, ending):
    return {"hook": hook, "body": body, "ending": ending}


def finish_answer(**changes):
    """A finisher answer for the synthetic brief: every piece edited a little, three Reels."""
    answer = {
        "email": {"subject_options": ["Why we read your first reply before your ads", "The question we ask every new client",
                                      "Your inquiries are up. Now what?"],
                  "preview": "It starts after the inquiry.", "opening": "Hi {{contact.first_name}},\n\nThe first reply shapes which inquiries become tours.",
                  "body": "Follow-up is part of the ad.\n\n**The reply is where the sale starts.**\n\nOwners start to see the inquiry as the start of the sale.",
                  "ending": "Reply and tell me what your first reply says.\n\nTalk soon,\nWhitney", "offer_descriptor": None, "cta": "reply"},
        "reels": [
            {"kind": "story", "title": "The question before the ads", "job": "The moment, face to camera",
             "cover_text": "The question we ask before touching your ads", "cover_alternates": ["Before your ads, your reply", "We start after the inquiry"],
             "on_screen_hook": "Before we touch your ads, one question", "spoken_opening": "Before we touch your ads, we ask one thing.",
             "script": "Before we touch your ads, we ask one thing. How do you answer a new inquiry? The owner told us it usually takes "
                       "two days to reply. That's where we start.",
             "screens": None, "beats": ["The question", "What it shows"],
             "caption": caption("Most of the sale happens after the inquiry.", "The ad starts the conversation. The reply carries it.",
                                "Save this for your next review. -Whitney"),
             "personal_lines": [], "read_time_seconds": 45, "cta": "none", "no_offer_ending": None, "offer_descriptor": None},
            {"kind": "stance", "title": "Follow-up is advertising", "job": "Whitney's stance on the same point",
             "cover_text": "Your first reply is part of your ads", "cover_alternates": ["The reply is the ad", "Follow-up sells the tour"],
             "on_screen_hook": "Your follow-up is part of your advertising", "spoken_opening": "Here's what I believe about follow-up.",
             "script": "Here's what I believe about follow-up. The reply is part of the advertising. We asked one owner how they answer a "
                       "new inquiry, and that question told us where to start.",
             "screens": None, "beats": ["The belief", "The moment as proof"],
             "caption": caption("Follow-up is part of the advertising.", "We read the first reply with the same care as the campaign.",
                                "That's where I start. -Whitney"),
             "personal_lines": [], "read_time_seconds": 40, "cta": "none", "no_offer_ending": None, "offer_descriptor": None},
            {"kind": "broll_text", "title": "After the inquiry", "job": "The turn of the story in screens",
             "cover_text": "What happens after the inquiry", "cover_alternates": ["After the inquiry", "The reply decides"],
             "on_screen_hook": "Her inquiries were up", "spoken_opening": None, "script": None,
             "screens": ["Her inquiries were up.", "The first reply took two days.", "So we started there."], "beats": ["Three screens"],
             "caption": caption("The reply is where the booking starts.", "A venue owner's inquiries were climbing, and we started with the reply.",
                                "Follow-up is part of the ad."),
             "personal_lines": [], "read_time_seconds": 15, "cta": "none", "no_offer_ending": None, "offer_descriptor": None}],
        "carousel": {"title": "When more inquiries aren't turning into tours",
                     "slides": [{"number": 1, "text": "When more inquiries aren't turning into tours,\nlook at the reply."},
                                *[{"number": n, "text": f"Slide about follow-up,\npart {chr(64 + n)}."} for n in range(2, 7)],
                                {"number": 7, "text": "Want our team to manage your ads?\nOr launch them and guide you?\nWe start with the reply."}],
                     "caption": caption("Getting the inquiry is only part of the job.", "We read the reply before the report.",
                                        "Follow-up is part of the advertising."),
                     "cta": "none", "no_offer_ending": None, "offer_descriptor": None},
        "client_quotes": [{"piece": "reel_1", "quote": "it usually takes us two days to reply", "speaker": "The owner"}],
        "stronger_with_permission": [], "pack_notes": [], "change_notes": ["Tightened every piece"]}
    answer.update(changes)
    return answer
