"""A synthetic v3 writer body built from the writer's own packet: finished copy and directions, no citations. Its scene
repeats the first turn's words, so the ledger binds it to that turn without a model."""
from __future__ import annotations

import copy
import re


def first_sentence(excerpt: str) -> str:
    text = re.sub(r"^[^:\n]{1,40}:\s*", "", excerpt.strip().split("\n")[0])
    return re.split(r"(?<=[.!?])\s+", text)[0].strip()


def v3_body(packet, **changes):
    first = packet["evidence"][0]
    body = {
        "approved_angle": copy.deepcopy(packet["approved_angle"]), "sharpened_point": None,
        "strategic_purpose": {"pillar": (packet.get("card") or {}).get("pillar") or "WARM", "content_type": "behind_the_scenes",
                              "why_now": "Owners are planning next season's budget."},
        "audience": {"who": "Established venue owners", "reason_to_care": "They want inquiries that turn into tours."},
        "intended_shift": {"understand": "How WIA reads follow-up before advertising.", "believe": "Follow-up shapes lead quality.",
                           "do": None},
        "point_of_view": "we",
        "wia_perspective": "We look at what happens after the inquiry before we change a single ad.",
        "supporting_example": {"scene": first_sentence(first["excerpt"]).rstrip("?.! ") + ", our strategist asked.",
                               "wia_move": "Our strategist looks at the first reply before the ads.",
                               "client_contribution": "The owner walks us through the follow-up."},
        "narrative_outline": {"hooks": [{"style": "observation", "text": "The first reply decides more than the ad does."},
                                        {"style": "question", "text": "What happens in the hour after someone inquires?"}],
                              "problems_desires_symptoms": ["Inquiries that go quiet"], "main_point": "Follow-up is part of the ad.",
                              "transformation": "Owners see the inquiry as the start of the sale.", "cta": "Reply and tell us about your follow-up."},
        "format_plan": {
            "reels": [{"job": "Show the WIA move", "cover_text": "The question we ask first", "spoken_opening": "Before we touch your ads, we ask one thing.",
                       "script": "Before we touch your ads, we ask one thing. How do you answer a new inquiry? The answer tells us where the sale starts.",
                       "beats": ["The question", "What it shows"], "read_time_seconds": 30, "source": "new_script"}],
            "carousel": {"job": "Walk through the first reply", "slides": [
                {"number": n, "job": f"Step {n}", "text": f"Slide text about follow-up, part {chr(64 + n)}."} for n in range(1, 8)]},
            "email": {"subject_options": ["The question we ask every new client", "Before we touch your ads"], "preview": "It starts after the inquiry.",
                      "opening": "Hi {{contact.first_name}},\n\nThe first reply shapes which inquiries become tours.",
                      "body": "Follow-up is part of the ad.\n\nOwners start to see the inquiry as the start of the sale.",
                      "ending": "Reply and tell me what your first reply says.\n\nTalk soon,\nWhitney"},
            "caption": {"hook": "Most of the sale happens after the click.", "body": "The ad starts the conversation. The reply carries it.",
                        "ending": "Save this for your next review."},
            "stories": None},
        "cta": {"choice": "explicit", "track": "Any offer, general", "action": "Reply to this email", "offer_connection": None, "chosen_by": "writer"},
        "cta_why": "A low barrier: one reply beats picking an offer.",
        "before_publishing": [{"text": "Confirm the client may be referenced.", "kind": "permission", "required": True, "answer": None}],
    }
    body.update(changes)
    return body
