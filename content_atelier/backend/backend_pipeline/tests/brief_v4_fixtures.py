"""A synthetic v4 writer body built from the writer's own packet (E.B33): the brief in the 13 October order and the finished
copy of every asset, written to pass the first-touch and asset checks. Its scene repeats the first turn's words, so the
ledger binds it to that turn without a model. Anonymised, invented text (R48)."""
from __future__ import annotations

import copy

from backend_pipeline.tests.brief_v3_fixtures import first_sentence


def caption(hook, body, ending):
    return {"hook": hook, "body": body, "ending": ending}


def v4_body(packet, **changes):
    first = packet["evidence"][0]
    body = {
        "approved_angle": copy.deepcopy(packet["approved_angle"]), "sharpened_point": None,
        "central_point": "The first reply to an inquiry shapes which couples book a tour.",
        "strategic_purpose": {"pillar": (packet.get("card") or {}).get("pillar") or "WARM", "content_type": "behind_the_scenes",
                              "why_now": "Owners are planning next season's budget.",
                              "desired_response": "I want an ads partner who looks past the click."},
        "intended_shift": {"understand": "How WIA reads follow-up before advertising.", "believe": "Follow-up shapes lead quality.",
                           "do": None},
        "audience": {"who": "Established venue owners", "reason_to_care": "They want inquiries that turn into tours."},
        "point_of_view": "we",
        "wia_perspective": "We look at what happens after the inquiry before we change a single ad.",
        "supporting_example": {"scene": first_sentence(first["excerpt"]).rstrip("?.! ") + ", our strategist asked.",
                               "wia_move": "Our strategist looks at the first reply before the ads.",
                               "client_contribution": "The owner walks us through the follow-up.",
                               "timestamps": ["0:04 the question about the first reply"],
                               "details": ["the first reply"],
                               "credits": [{"actor": "our strategist", "did": "asked about the first reply"}]},
        "narrative_outline": {"hooks": [{"style": "observation", "text": "The first reply to an inquiry decides more than the ad does."},
                                        {"style": "question", "text": "What happens in the hour after a couple inquires?"}],
                              "problems_desires_symptoms": ["Inquiries that go quiet"], "main_point": "Follow-up is part of the ad.",
                              "transformation": "Owners see the inquiry as the start of the sale.", "cta": "Reply and tell us about your follow-up."},
        "cta": {"choice": "explicit", "track": "Any offer, general", "action": "Reply to this email", "offer_connection": None, "chosen_by": "writer"},
        "cta_why": "A low barrier: one reply beats picking an offer.",
        "before_publishing": [{"text": "Confirm the client may be referenced.", "kind": "permission", "required": True, "answer": None}],
        "format_plan": {
            "reels": [
                {"kind": "story", "job": "The moment, face to camera", "register": "spoken",
                 "cover_text": "The question we ask before touching your ads", "on_screen_hook": "Before we touch your ads, one question",
                 "spoken_opening": "Before we touch your ads, we ask one thing.",
                 "script": "Before we touch your ads, we ask one thing. How do you answer a new inquiry? It's the part a report "
                           "leaves out, and it's where we start.",
                 "screens": None, "beats": ["The question", "What it shows"], "personal_lines": [], "read_time_seconds": 45,
                 "source": "new_script",
                 "caption": caption("Most of the sale happens after the inquiry.",
                                    "The ad starts the conversation. The reply carries it, and that is where we look first.",
                                    "Save this for your next review."),
                 "offer_descriptor": None},
                {"kind": "stance", "job": "WIA's view of the moment", "register": "spoken",
                 "cover_text": "Your inquiries deserve a better first reply", "on_screen_hook": "What your ads report leaves out",
                 "spoken_opening": "Here is what I believe about follow-up.",
                 "script": "Here is what I believe about follow-up. The reply is part of the advertising, and we treat it that way "
                           "with the clients we work with.",
                 "screens": None, "beats": ["The belief"], "personal_lines": [], "read_time_seconds": 40, "source": "new_script",
                 "caption": caption("Follow-up is part of the advertising.",
                                    "We read the first reply with the same care as the campaign that earned the inquiry.",
                                    "That's where I start. -Whitney"),
                 "offer_descriptor": None},
                {"kind": "broll_text", "job": "The turn of the story in screens", "register": "on_screen",
                 "cover_text": "What happens after the inquiry", "on_screen_hook": "Her inquiries were up",
                 "spoken_opening": None, "script": None,
                 "screens": ["Her inquiries were up.", "The first reply took two days.", "So we started there."],
                 "beats": ["Three screens"], "personal_lines": [], "read_time_seconds": 15, "source": "new_script",
                 "caption": caption("The reply is where the booking starts.",
                                    "A venue owner's inquiries were climbing, and we started with the reply.",
                                    "Follow-up is part of the ad."),
                 "offer_descriptor": None}],
            "carousel": {"job": "Walk through the first reply", "register": "written", "title": "When more inquiries aren't turning into tours",
                         "slides": [{"number": 1, "job": "The promise", "text": "When more inquiries aren't turning into tours, look at the reply."},
                                    *[{"number": n, "job": f"Step {n}", "text": f"Slide text about follow-up, part {chr(64 + n)}."} for n in range(2, 7)],
                                    {"number": 7, "job": "CTA", "text": "Whether you'd like our team to manage your ads for you, or you'd like "
                                                                        "us to launch your campaigns and guide you while you run them, we start with the reply."}],
                         "caption": caption("Getting the inquiry is only part of the job.",
                                            "We read the reply before we read the report, because that is where couples decide.",
                                            "Follow-up is part of the advertising."),
                         "offer_descriptor": None},
            "email": {"job": "The whole story", "register": "written",
                      "send_header": {"date": "Tuesday of the publishing week", "send_time": "Your usual Tuesday morning send",
                                      "recipients": "The full list (confirm the segment)"},
                      "subject_options": ["When more inquiries aren't enough", "The question we ask every new client"],
                      "preview": "It starts after the inquiry.",
                      "opening": "Hi {{contact.first_name}},\n\nThe first reply shapes which inquiries become tours.",
                      "body": "Follow-up is part of the ad.\n\n**The reply is where the sale starts.**\n\nOwners start to see the inquiry as the start of the sale.",
                      "ending": "Reply and tell me what your first reply says.\n\nTalk soon,\nWhitney", "offer_descriptor": None},
            "stories": None},
    }
    body.update(changes)
    return body
