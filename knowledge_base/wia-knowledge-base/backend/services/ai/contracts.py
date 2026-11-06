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


class MeetingDigest(Strict):
    """Call 1 for a client meeting: the Last meeting tab and action candidates."""
    summary: list[str] = Field(description="3 to 6 short bullets: what the meeting was about and where it landed")
    decisions: list[Decision]
    commitments: list[Commitment]
    action_updates: list[ActionUpdate]
    answered: list[Answered]
    covered: list[Covered]
    open_asks: list[Ask] = Field(description="Client questions or requests not answered in the meeting")
    recap_email: str = Field(description="A short recap email draft to the client, in WIA's voice; empty if internal")
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


class SinceItem(Strict):
    text: str = Field(description="What happened since the last call, one line")
    ref: str = Ref


class AgendaItem(Strict):
    item: str
    why: str = Field(description="Why it is on the agenda, a few words")


class Opportunity(Strict):
    text: str
    why: str
    ref: str = Ref


class TypeFact(Strict):
    label: str
    value: str
    ref: str | None = Field(description="A reference, or null for a fact from the call type itself")


class CallBrief(Strict):
    """Call 2, before a call: the call prep brief (the Next call tab). `owed` and `limits` are computed in code."""
    thirty: list[str] = Field(description="Exactly 3 lines: the client's focus; what the call must achieve; the main risk")
    since: list[SinceItem]
    asks: list[Ask] = Field(description="What they asked that we haven't answered yet")
    agenda: list[AgendaItem]
    questions: list[str]
    watch: list[str] = Field(description="Watch-outs for the host, plain and specific")
    opportunity: Opportunity | None
    type_block: list[TypeFact] = Field(description="The call type's specific section")


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
