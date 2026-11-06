"""The skills: one entry per AI task, configured for the reasoning and the output that task needs.

| skill               | model              | reasoning | why                                                                    |
|---------------------|--------------------|-----------|------------------------------------------------------------------------|
| meeting_digest      | Claude Sonnet 5.5  | medium    | a long transcript; quote faithfully and judge who committed to what     |
| team_meeting_digest | Claude Sonnet 5.5  | medium    | the same, plus attributing each item to one of many clients             |
| call_brief          | Claude Sonnet 5.5  | low       | combines inputs that are already structured; the writing quality counts |
| email_actions       | Claude Haiku 5.5   | low       | short texts at volume: plain extraction, the same action shapes         |
| history_moments     | Claude Sonnet 5.5  | low       | judging what mattered across months of merged activity and decisions    |

Override a model with AI_MODELS='{"call_brief": "..."}'; `kb ai check` confirms each id exists on OpenRouter.
A prompt file change re-runs that skill (its hash is in the input hash), but only while the AI is live.
"""
import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel

from backend.config import get_settings
from backend.services.ai import contracts

PROMPTS = Path(__file__).parent / "prompts"
SLOT = re.compile(r"\{\{(\w+)\}\}")
INCLUDE = re.compile(r"\{\{> ([\w.]+)\}\}")


@dataclass(frozen=True)
class Skill:
    name: str
    version: str
    contract: type[BaseModel]
    subject_kind: str  # meeting | call | email_batch | client
    model: str
    reasoning: str | None
    max_tokens: int
    # Worst case for one call including its one repair, reserved against the monthly budget before sending.
    # The actual cost OpenRouter reports is what the run log records.
    max_cost_usd: float
    budgets: dict  # context block -> characters
    system_file: str
    user_file: str


SONNET, HAIKU = "anthropic/claude-sonnet-5.5", "anthropic/claude-haiku-5.5"
SKILLS = {s.name: s for s in (
    Skill("meeting_digest", "1", contracts.MeetingDigest, "meeting", SONNET, "medium", 6000, 0.60,
          {"transcript": 160_000, "open_actions": 6_000, "client_emails": 24_000, "internal_comms": 16_000,
           "viktor_posts": 8_000}, "meeting_digest.system.md", "meeting_digest.user.md"),
    Skill("team_meeting_digest", "1", contracts.TeamMeetingDigest, "meeting", SONNET, "medium", 8000, 0.80,
          {"transcript": 200_000}, "team_meeting_digest.system.md", "team_meeting_digest.user.md"),
    Skill("call_brief", "1", contracts.CallBrief, "call", SONNET, "low", 3000, 0.25,
          {"open_actions": 6_000, "client_emails": 20_000, "internal_comms": 12_000, "viktor_posts": 8_000},
          "call_brief.system.md", "call_brief.user.md"),
    Skill("email_actions", "1", contracts.EmailActions, "email_batch", HAIKU, "low", 2000, 0.06,
          {"open_actions": 6_000, "client_emails": 30_000}, "email_actions.system.md", "email_actions.user.md"),
    Skill("history_moments", "1", contracts.HistoryMoments, "client", SONNET, "low", 3000, 0.15,
          {"activity": 40_000, "digests": 12_000}, "history_moments.system.md", "history_moments.user.md"),
)}


def model_for(skill: Skill) -> str:
    return get_settings().ai_models.get(skill.name, skill.model)


def _load(name: str) -> str:
    text = (PROMPTS / name).read_text(encoding="utf-8")
    return INCLUDE.sub(lambda m: _load(m.group(1)).strip(), text)


def render(name: str, values: dict[str, str]) -> str:
    """Fill every {{slot}}; a slot without a value is a bug, never sent as-is."""
    text = _load(name)
    missing = sorted(set(SLOT.findall(text)) - set(values))
    if missing:
        raise KeyError(f"{name}: no value for {', '.join(missing)}")
    return SLOT.sub(lambda m: values[m.group(1)], text)


def prompt_sha(skill: Skill) -> str:
    return hashlib.sha256((_load(skill.system_file) + "\0" + _load(skill.user_file)).encode()).hexdigest()
