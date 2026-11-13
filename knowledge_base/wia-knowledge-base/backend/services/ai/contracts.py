"""What each skill must answer, shaped like the screens that show it (frontend/src/calls.ts Recap and Brief).

Every claim carries `ref`, a reference from the input (T12, E3, S5, V2, A4). Dates, sources and the "owed" and
"limits" sections are filled in by code from those refs, never by the model.
"""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

CallType = Literal["ads-kickoff", "messaging", "leadlock-kickoff", "strategy", "creative", "office-hours", "checkin",
                   "other"]
Ref = Field(description="One reference from the input, exactly as shown, e.g. T12")
Quote = Field(description="Words copied exactly from that reference, 3 to 40 words")


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Decision(Strict):
    text: str = Field(description="What was decided, one plain sentence")
    quote: str = Quote
    ref: str = Ref


class Commitment(Strict):
    text: str = Field(description="What will be done, starting with a verb")
    owner_side: Literal["WIA", "Client"]
    owner_name: str | None = Field(description="A name from the provided people only; null if not said")
    due_phrase: str | None = Field(description="The timing words exactly as said (e.g. 'by Friday'); null if none")
    due_date: str | None = Field(description="YYYY-MM-DD resolved from due_phrase against the meeting date; else null")
    quote: str = Quote
    ref: str = Ref
    matches_action: str | None = Field(description="The open action ref (A#) this restates or advances; else null")


class ActionUpdate(Strict):
    action_ref: str = Field(description="An open action ref (A#)")
    signal: Literal["done", "progressed", "blocked", "date_changed"]
    quote: str = Quote
    ref: str = Ref


class Ask(Strict):
    quote: str = Field(description="The client's question or request, copied exactly")
    who: str = Field(description="Who asked, as named in the input")
    ref: str = Ref


class Answered(Strict):
    question: str
    answer: str
    ref: str = Ref


class Covered(Strict):
    item: str
    done: bool


class RecapPoint(Strict):
    text: str = Field(description="One line of the email body, in WIA's voice")
    refs: list[str] = Field(description="The transcript [T#] or client email [E#] refs this line comes from; never S, V or A")


class RecapEmail(Strict):
    """Built line by line so code can check each line's sources before a person sees the draft."""
    greeting: str = Field(description="The opening line, e.g. 'Hi Dana,'. No facts here")
    points: list[RecapPoint] = Field(description="3 to 7 lines: what each side will do next, and anything not covered")
    sign_off: str = Field(description="The closing line and the WIA host's first name. No facts here")


class MeetingDigest(Strict):
    """Call 1 for a client meeting: the Last meeting tab and action candidates."""
    summary: list[str] = Field(description="3 to 6 short bullets: what the meeting was about and where it landed")
    decisions: list[Decision]
    commitments: list[Commitment]
    action_updates: list[ActionUpdate]
    answered: list[Answered]
    covered: list[Covered]
    open_asks: list[Ask] = Field(description="Client questions or requests not answered in the meeting")
    recap: RecapEmail = Field(description="A recap email draft to the client, from what was said with the client only")
    call_type_guess: CallType


class TeamCommitment(Commitment):
    client: str | None = Field(description="The client id from the client list this is for; null if not one client")


class TeamDecision(Decision):
    client: str | None = Field(description="The client id from the client list; null if team-wide")


class TeamMeetingDigest(Strict):
    """Call 1 for WIA's internal team meeting: actions attributed to clients."""
    summary: list[str]
    decisions: list[TeamDecision]
    commitments: list[TeamCommitment]
    action_updates: list[ActionUpdate]


class TypeFact(Strict):
    label: str
    value: str
    ref: str | None = Field(description="A reference, or null for a fact from the call type itself")


Refs = Field(description="1 to 3 references from the input it rests on, exactly as shown (e.g. A3, E2)")


class TalkingPoint(Strict):
    text: str = Field(description="What to raise, one line")
    why: str = Field(description="Why it is on the list, a few words")
    refs: list[str] = Refs


class Question(Strict):
    text: str = Field(description="The question for the host to ask")
    gap: str = Field(description="The gap in the input it fills, a few words")
    refs: list[str] = Refs


class WatchOut(Strict):
    text: str
    audience: Literal["internal", "ok_to_say"] = Field(description="internal: for the host only; ok_to_say: fine to say")
    refs: list[str] = Refs


class Opportunity(Strict):
    text: str
    why: str = Field(description="The client need it answers")
    refs: list[str] = Refs


class CallBrief(Strict):
    """Call 2, before a call. Only the judgement: owed, asks, changes, figures and limits are computed in code and
    shown beside it (services/callprep)."""
    goal: str = Field(description="This call must ...: the call type's decision, made specific to this client now")
    standing: str = Field(description="Where things stand with this client, one sentence")
    risk: str | None = Field(description="The main risk for this call, one sentence; null if none is supported")
    talking_points: list[TalkingPoint] = Field(description="In the order to take them, the client's open asks first")
    questions: list[Question]
    watch_outs: list[WatchOut]
    opportunity: Opportunity | None
    type_block: list[TypeFact] = Field(description="The call type's own section, facts selected from the input")
    changed_highlights: list[str] = Field(description="The H refs of the changes worth reading first")
    declined: str | None = Field(description="Only when instructions ask for something the sources can't give: why")


class CallFocus(Strict):
    """Regenerate, first pass: which extra items the instructions need, from the offered list."""
    fetch: list[str] = Field(description="Up to 4 ids from the offered items, only those the instructions need")
    declined: str | None = Field(description="What the instructions ask that no approved source can give, and why")


MomentKind = Literal["Milestone", "Decision", "Client signal", "Commitment", "Delivery", "Risk"]


class MomentOut(Strict):
    kind: MomentKind
    title: str = Field(description="What happened, in at most 12 words")
    why: str = Field(description="Why it mattered for the account, one sentence")
    refs: list[str] = Field(description="1 to 3 refs from the input (H# activity, D# meeting decisions) it rests on")


class HistoryMoments(Strict):
    """History tab: the events that explain the account. Date, lane and sources come from the refs, in code."""
    moments: list[MomentOut] = Field(description="The 5 to 15 events that explain this account, oldest first")


class EmailActions(Strict):
    """Email batch for one client: the same action shapes as Call 1."""
    commitments: list[Commitment]
    action_updates: list[ActionUpdate]
    open_asks: list[Ask]


def strict_schema(model: type[BaseModel]) -> dict:
    """The model's JSON schema in OpenRouter/OpenAI strict form: refs inlined, every property required (optional
    ones are nullable), no extra properties, no titles or defaults."""
    raw = model.model_json_schema()
    defs = raw.pop("$defs", {})

    def walk(node):
        if isinstance(node, list):
            return [walk(n) for n in node]
        if not isinstance(node, dict):
            return node
        if "$ref" in node:
            return walk(defs[node["$ref"].rsplit("/", 1)[1]])
        node = {k: walk(v) for k, v in node.items() if k not in ("title", "default")}
        if node.get("type") == "object" and "properties" in node:
            node["required"] = list(node["properties"])
            node["additionalProperties"] = False
        return node

    return walk(raw)
