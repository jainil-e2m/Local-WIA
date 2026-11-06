"""Call types for call prep, detected from the calendar title (frontend/src/calls.ts TEMPLATES, same order).

shortcut: a copy of the frontend's templates. The admin skill editor there saves to the browser only; when it
saves to the KB (named sign-in, Phase E), read these from the database instead.
"""
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class CallType:
    key: str
    name: str
    detect: re.Pattern
    purpose: str
    sections: tuple[str, ...]
    type_block: str
    agenda: tuple[str, ...]
    leave_out: str
    guidance: str


def _t(key, name, pattern, purpose, sections, type_block, agenda, leave_out, guidance):
    return CallType(key, name, re.compile(pattern, re.IGNORECASE), purpose, tuple(sections.split()), type_block,
                    tuple(agenda), leave_out, guidance)


TYPES = (
    _t("ads-kickoff", "Ads kickoff", r"ads\s*kick-?off", "Introductions, set expectations, connect ad accounts",
       "owed agenda questions typeBlock limits", "Access checklist & what was sold",
       ["Introductions and who does what", "How the work runs and what to expect", "Connect ad accounts live",
        "Next steps and the messaging interview"], "Performance, strategy opinions, price",
       "Keep it practical: who does what, what was sold, and which accounts still need connecting. No performance talk yet."),
    _t("messaging", "Messaging & positioning interview", r"messaging|positioning",
       "Deep-dive on the business, audience and voice", "asks agenda questions typeBlock limits", "Questionnaire answers",
       ["Their story in their words", "Ideal couple and objections", "Offer and what sets them apart",
        "Voice: words to use and avoid"], "Ads, unrelated actions",
       "Quote the questionnaire in the client's own words. Suggest follow-up questions where answers are thin or contradict each other."),
    _t("leadlock-kickoff", "LeadLock kickoff", r"lead\s*lock\s*kick-?off", "Plan the LeadLock build",
       "since asks owed agenda watch typeBlock limits", "CRM & setup facts",
       ["Current inquiry workflow and CRM", "Who answers new inquiries", "What WIA sets up vs what stays with the client",
        "Setup milestones"], "Ads strategy",
       "Make the split clear between what WIA sets up and what stays with the client. Flag any missing CRM or access detail."),
    _t("strategy", "Monthly strategy", r"strategy", "Review the month and plan the next",
       "since asks owed agenda questions watch opportunity typeBlock limits", "Results & ads context",
       ["Client's open questions first", "What was delivered and what's next", "Results and what they mean",
        "Decisions needed"], "Onboarding detail",
       "Start with the client's open questions. Explain results in plain language against the playbook thresholds; label interpretations."),
    _t("creative", "Creative review", r"creative", "Approve creative and page changes",
       "since asks owed agenda typeBlock limits", "Approvals & voice",
       ["What's ready to review", "Feedback and decisions", "Approval and next delivery date"], "Lead numbers",
       "List exactly what is ready for approval and what decision is needed on each. Keep voice notes from the profile next to each item."),
    _t("office-hours", "Office hours (group)", r"office\s*hours", "Programme coaching for several members",
       "asks agenda typeBlock limits", "Members expected",
       ["Quick wins from last week", "Member questions in turn", "One task each for next week"],
       "Any member's details beyond their own parts",
       "One short line per expected member. Never show one member's details to another."),
    _t("checkin", "Programme check-in (1:1)", r"check-?in", "Re-engage an accelerator member",
       "since asks owed agenda watch typeBlock limits", "Programme progress",
       ["What's getting in the way", "Pick one concrete next step", "Confirm the next session"], "Programme-wide news",
       "Be warm and specific: what is blocking them, and one small next step. Don't assume missed sessions mean unhappiness."),
)
OTHER = _t("other", "Other / unclassified", r"$^", "General client call", "since asks owed limits", "", [], "-",
           "Summarise recent context and anything owed either way. Ask the host to set a call type if the purpose is unclear.")


def detect(title: str | None) -> CallType:
    return next((t for t in TYPES if t.detect.search(title or "")), OTHER)


def by_key(key: str) -> CallType:
    return next((t for t in TYPES if t.key == key), OTHER)
