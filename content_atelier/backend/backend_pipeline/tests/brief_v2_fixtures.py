"""A synthetic v2 brief body built from the writer's own packet, so its quotes and claims bind to real evidence."""
from __future__ import annotations

import copy


def v2_body(packet, **changes):
    evidence = packet["evidence"]
    first = evidence[0]
    quote = first["excerpt"].strip().split("\n")[0][:60].strip()
    body = {
        "approved_angle": copy.deepcopy(packet["approved_angle"]), "sharpened_point": None,
        "strategic_purpose": {"pillar": (packet.get("card") or {}).get("pillar") or "WARM", "content_type": "behind_the_scenes",
                              "why_now": "Owners are planning next season's budget."},
        "audience": {"who": "Established venue owners", "reason_to_care": "They want inquiries that turn into tours."},
        "intended_shift": {"understand": "How WIA reads follow-up before advertising.", "believe": "Follow-up shapes lead quality.",
                           "do": "Look at the first reply before changing the ads."},
        "point_of_view": "we",
        "wia_perspective": "We look at what happens after the inquiry before we change a single ad.",
        "supporting_example": {"scene": "On a client call, the team looked at how follow-up worked.",
                               "wia_move": "The strategist asked how the first reply was written.",
                               "client_contribution": "The client described the follow-up change."},
        "narrative_outline": {"hooks": [{"style": "observation", "text": "I had a conversation with a client this week about follow-up."},
                                        {"style": "question", "text": "What happens in the hour after someone inquires?"}],
                              "problems_desires_symptoms": ["Inquiries that go quiet"], "main_point": "Follow-up is part of the ad.",
                              "transformation": "Owners see the inquiry as the start of the sale.", "cta": "Reply and tell us about your follow-up."},
        "format_plan": {
            "reels": [{"job": "Show the WIA move", "cover_text": "The question we ask first", "spoken_opening": "Before we touch your ads, we ask one thing.",
                       "beats": ["The question", "What it shows"], "read_time_seconds": 30, "source": "new_script",
                       "evidence_ids": [first["evidence_id"]]}],
            "carousel": {"job": "Walk through the first reply", "slides": [
                {"number": n, "job": f"Step {n}", "text": f"Slide text about follow-up, part {chr(64 + n)}.", "evidence_ids": []} for n in range(1, 8)]},
            "email": {"subject_options": ["The question we ask every new client", "Before we touch your ads"], "preview": "It starts after the inquiry.",
                      "opening": "Hi {{contact.first_name}},", "argument": "Follow-up shapes which inquiries become tours.",
                      "transformation": "You start to see the inquiry as the start of the sale.", "ending": "Reply and tell me what your first reply says.",
                      "evidence_ids": []},
            "caption": {"hook": "Most of the sale happens after the click.", "adds": "The story behind the question.", "ending": "Save this for your next review."},
            "stories": None},
        "cta": {"choice": "explicit", "track": "Any offer, general", "action": "Reply to this email", "offer_connection": None, "chosen_by": "writer"},
        "cta_why": "A low barrier: one reply beats picking an offer.",
        "before_publishing": [{"text": "Confirm the client may be referenced.", "kind": "permission", "required": True, "answer": None}],
        "evidence": [{"evidence_id": first["evidence_id"], "speaker": first["speaker"], "start_ms": first["start_ms"], "quote": quote}],
        "claims": [{"claim_id": "c1", "text": "On a client call, the team discussed the follow-up change.", "claim_class": "particular_interaction",
                    "evidence_ids": [first["evidence_id"]], "knowledge_base_document": None, "numeric_facts": [], "quote": None,
                    "public_quote": False}],
    }
    body.update(changes)
    return body
