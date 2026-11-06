"""Settings (plan 0.B8, section 4.10, Appendix D): behaviour that changes without a deploy.

Three kinds of configuration, kept apart:

- **Secrets, endpoints, paths and the safety catches stay in the environment** (API keys, database URLs, artifact
  paths, the "allow generation / encoding / brief generation" switches, ATELIER_ALLOW_EMBEDDING_CONTRACT_CHANGE).
  Nothing here can read or write them; `set` refuses a key that looks like a secret.
- **Everything behavioural is a setting** defined once in DEFINITIONS below: its type, its code default, a validator
  and the environment variable(s) it absorbs. The code defaults are the documented defaults of the example
  environment files; a test parses those files and fails when they differ.
- **Stored values** are rows of the `settings` table (key, jsonb value, who, when). The table also holds system
  state of other features (the active knowledge-base version, scheduler markers); only keys defined here are
  settings.

Precedence for one key, highest first:

    table row  >  legacy environment variable  >  code default            (the usual case)
    environment variable  >  table row  >  code default                   (a key marked env_override)

A deployment that keeps its behavioural values in environment variables therefore changes nothing on upgrade (the
variable is the value until a row exists), and `storage_cli settings import-env` records them as rows. From then
on a row wins, so editing a setting changes behaviour without touching the environment. `env_override` is for
development or emergency use only (today: the knowledge-base directory). Every loaded value remembers where it
came from (`default`, `env` or `table`); runs store that as `settings_snapshot` in their `input_refs`.

One reader loads the legacy environment files for everything (`load_env_files`): `backend/.env`, the project
root `.env`, `backend/.env.storage.local` (ATELIER_* keys) and `backend/.env.intake.local`. The process
environment always wins over a file (`setdefault`).
"""
from __future__ import annotations

import hashlib
import json
import logging
import math
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pydantic import BaseModel, PrivateAttr

log = logging.getLogger(__name__)

# Profiles. config.CARD_PROFILES and angle_profiles read these.
LEGACY_ANGLE_PROFILE = "2026-10-19.reel-editorial.v2"
# The legacy profile before E.B11 (3) moved the Reel scripts out of the user message; kept for replay.
LEGACY_ANGLE_PROFILE_V1 = "2026-10-16.reel-editorial.v1"
CARD_PROFILES = ("2026-10-18.wia-strategist.v3", "2026-10-18.wia-strategist.v4", "2026-10-18.wia-strategist.v5",
                 "2026-10-20.wia-strategist.v6", "2026-10-23.wia-strategist.v7", "2026-10-25.wia-strategist.v8",
                 "2026-10-25.wia-strategist.v9")
ANGLE_PROFILES = (LEGACY_ANGLE_PROFILE, LEGACY_ANGLE_PROFILE_V1, *CARD_PROFILES)
# The weekly cycle's moment extraction, the default first (E.B12): the moments ledger's per-document scene profile v2 (2.B2),
# the whole-week weekly v3 prompt (kept for replay and as the fallback), or the weekly path's own scene v1 loop (replay).
# Scene profile v3 (E.B31: human lines and counter-expected decisions) is selectable, last: not the default until M3's gate.
EXTRACTION_PROFILES = ("2026-10-19.scenes.v2", "2026-10-13.weekly.v3", "2026-10-18.scenes.v1", "2026-10-23.scenes.v3",
                       "2026-10-25.scenes.v4")
# The scene profiles a document's own extraction (2.B2) can run, the default first (the weekly whole-week prompt is not one).
DOCUMENT_EXTRACTION_PROFILES = ("2026-10-19.scenes.v2", "2026-10-18.scenes.v1", "2026-10-23.scenes.v3", "2026-10-25.scenes.v4")
# The card verifier's model-pass prompt (E.B10): v3 (E.B26) is the default; v4 (E.B30) adds the point tests of strategist v7.
CARD_VERIFICATION_PROFILES = ("card-verification.v3", "card-verification.v4")
BRIEF_SCHEMAS = ("brief_document_v1", "brief_document_v2", "brief_document_v3", "brief_document_v4")
# The brief writer's prompt. For contract v2 (E.B22): v2 as released on 18 October, or v3 (copy separated from direction,
# caveats beside the copy, R54). For contract v3 (E.B23): v4, the only writer of that contract. A run freezes the one it was
# queued with; the queue refuses a writer the contract does not accept.
# v4.1 (5.B6): writer v4 with the two revision blocks of interface 1 (the reviewer's instructions and the locked lines);
# a refresh of a contract v3 brief uses it whatever the setting (BRIEF_REVISION_WRITERS), and the setting may name it
# for first drafts too, which then read as v4's.
# v5 (E.B33): the writer of contract v4 (the brief WIA reviewed on 20 October: the same idea through different doors, the
# first-touch checklist, register by format), with interface 1's two blocks; it writes first drafts and refreshes alike.
# v5.1 (NP.B10, D43j): writer v5 writing exactly three Reels (story, stance, b-roll text) when the reel channel is
# confirmed, with its own answer schema; selectable by setting only, so v5 runs and their replays are unchanged.
# v5.2 (Phase N8: 1.B12's and 1.B13's extensions, 3.B17): v5.1 with the identity records of the people and accounts in
# the evidence, "what happened next" from the card's account memory as evidence, and internal-meeting evidence marked as
# team practice; same answer schema as v5.1.
# v5.3 (Round 2, WIA's feedback of 26 October 2026): v5.2's inputs, with the Reels as the central story and two premises
# of their own (contracts_v4.BriefWriteV53), the premises it weighed, and E2M's craft and editorial guide.
BRIEF_WRITERS = ("v2", "v3", "v4", "v4.1", "v5", "v5.1", "v5.2", "v5.3")
BRIEF_WRITERS_BY_SCHEMA = {"brief_document_v2": ("v2", "v3"), "brief_document_v3": ("v4", "v4.1"),
                           "brief_document_v4": ("v5", "v5.1", "v5.2", "v5.3")}
# Writers that write exactly three Reels with v5.1's answer schema (NP.B10).
THREE_REEL_WRITERS = ("v5.1", "v5.2")
# Writers that write the central story and two premises with v5.3's answer schema (Round 2).
PREMISE_WRITERS = ("v5.3",)
# Writers that read the identity records, account memory and team-practice marks (Phase N8).
IDENTITY_WRITERS = ("v5.2", "v5.3")
# The writer a refresh with feedback uses for a contract: one whose template renders the revision instructions. The setting's
# writer when it is one of them, else the last: v5 for contract v4, so v5.1 is used only where the setting names it.
BRIEF_REVISION_WRITERS = {"brief_document_v3": ("v4.1",), "brief_document_v4": ("v5.3", "v5.2", "v5.1", "v5")}


def brief_writer_problem(schema: str | None, writer: str | None) -> str | None:
    """Why a brief contract and writer prompt cannot run together, or None (contract v1 has no writer setting)."""
    accepted = BRIEF_WRITERS_BY_SCHEMA.get(schema or "")
    if accepted and writer and writer not in accepted:
        return (f"Brief contract {schema} is written by writer {' or '.join(accepted)}, not {writer}: set "
                f"prompts.profile.brief_writer to match prompts.profile.brief")
    return None

CACHE_SECONDS = "ATELIER_SETTINGS_CACHE_SECONDS"
UNREACHABLE_SECONDS = 30.0


class SettingError(ValueError):
    """An unknown key, a secret, or a value of the wrong type or outside its range."""


# --------------------------------------------------------------------------------------------------------------
# The one reader of the legacy environment files


def env_files() -> list[tuple[Path, str]]:
    """The files in precedence order, with how each is read. Roots come from config at call time, so a test that
    points config.BACKEND_ROOT elsewhere never reads the developer's real files."""
    from . import config
    backend, project = config.BACKEND_ROOT, config.PROJECT_ROOT
    return [(backend / ".env", "dotenv"), (project / ".env", "dotenv"),
            (backend / ".env.storage.local", "atelier"), (backend / ".env.intake.local", "dotenv")]


def load_env_files(environ=None) -> None:
    """Copy file values into the process environment where it has no value (`setdefault`: the process wins).

    `dotenv` files (backend/.env, the root .env, .env.intake.local) load every KEY=value line with surrounding
    quotes removed. `.env.storage.local` loads ATELIER_* keys only, values as written. .env.intake.local was only
    ever read by Docker Compose; the same keys are now available to a process started without it.
    """
    environ = os.environ if environ is None else environ
    for path, mode in env_files():
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if mode == "atelier":
                if line.strip() and not line.lstrip().startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    if key.strip().startswith("ATELIER_"):
                        environ.setdefault(key.strip(), value.strip())
                continue
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


# --------------------------------------------------------------------------------------------------------------
# Definitions


@dataclass(frozen=True)
class Definition:
    key: str
    type: str  # str, int, float, bool, enum, list, zone
    default: Any
    description: str
    env: tuple[str, ...] = ()  # absorbed variables; the first non-blank one is used (later ones are aliases)
    choices: tuple[str, ...] = ()
    env_aliases: tuple[tuple[str, str], ...] = ()  # accepted environment spellings of a choice
    lo: float | None = None
    hi: float | None = None
    nullable: bool = False
    env_override: bool = False  # the environment beats a stored row (development or emergency)
    table: bool = True  # False: the environment and the code default only (pinned, not settable here)
    restart_required: bool = False
    target: str | None = None  # models, storage or intake: the typed object that carries it
    field: str | None = None
    field_key: str | None = None  # a key inside a dict field
    scopes: tuple[str, ...] = ()  # the run kinds that snapshot it
    group: str = ""


DEFINITIONS: list[Definition] = []
_BY_KEY: dict[str, Definition] = {}

LUNA, SOL, SONNET = "openai/gpt-6-luna", "openai/gpt-6.1-sol", "anthropic/claude-sonnet-5.5"
# stage -> the suffix of its models.* and models.reasoning_effort.* keys
STAGE_SUFFIX = {
    "moment_extraction": "moment_extraction", "angle_generation": "angle_generation",
    "card_verification": "card_verification", "context_mining": "context_mining",
    "document_classification": "document_classification",
    # The topic picker is the same kind of fast classification call (plan 2.B7): it shares that stage's reasoning effort.
    "topic_assignment": "document_classification",
    "brief_write": "brief", "brief_repair": "brief",
    "brief_plan": "brief_review", "brief_grade": "brief_review", "brief_review": "brief_review", "brief_verify": "brief_review",
    "pack_write": "pack_writer", "pack_repair": "pack_writer", "pack_review": "pack_review",
    # Content pack v2 (NP.B5): the finisher, the repair and NP-7's passes on the writer (Opus 5.5); the check on the reviewer.
    "pack_finish": "pack_writer", "pack_caption": "pack_writer", "pack_refinish": "pack_writer",
    "pack_check": "pack_review", "pack_recheck": "pack_review",
}
STAGE_SUFFIXES = ("moment_extraction", "angle_generation", "card_verification", "context_mining", "document_classification",
                  "brief", "brief_review",
                  "pack_writer", "pack_review")
REVIEW_DAYS = {"offer": 30, "price": 30, "roster_member": 30, "cta": 60, "campaign": 14, "content_plan_entry": 14,
               "result": 90, "process_step": 90, "performance_note": 90, "rule": 90, "format_rule": 90,
               "exemplar": 180, "belief": 180, "audience_phrase": 180}


def _add(key, type, default, description, **kw):
    d = Definition(key, type, default, description, **kw)
    DEFINITIONS.append(d)
    _BY_KEY[key] = d
    return d


def _models():
    W, B, P = ("weekly",), ("brief",), ("pack",)
    _add("models.default", "str", LUNA, "Model for every stage without its own (angle refinement, comparison, brief fallback)",
         env=("OPENROUTER_ANGLES_MODEL", "OPENROUTER_MODEL"), target="models", field="openrouter_angles_model",
         scopes=W + B + P, group="models")
    _add("models.moment_extraction", "str", LUNA, "Moment and scene extraction", env=("OPENROUTER_MOMENTS_MODEL",),
         target="models", field="openrouter_moments_model", scopes=W, group="models")
    _add("models.angle_generation", "str", None, "Strategist angle generation; applies to the card profiles only, blank "
         "keeps models.default (use openai/gpt-6.1-sol with the strategist profile)", env=("OPENROUTER_ANGLE_GENERATION_MODEL",),
         nullable=True, target="models", field="openrouter_angle_generation_model", scopes=W, group="models")
    _add("models.card_verification", "str", None, "E.B10's model pass over each week's cards (another model family than the "
         "strategist's); blank skips it", env=("OPENROUTER_VERIFICATION_MODEL",), nullable=True, target="models",
         field="openrouter_verification_model", scopes=W, group="models")
    _add("models.context_mining", "str", None, "The learning loop's edit categoriser (another family than the brief "
         "writer); blank categorises by rules only", env=("OPENROUTER_CONTEXT_MINING_MODEL",), nullable=True, target="models",
         field="openrouter_context_mining_model", group="models")
    _add("models.document_classification", "str", None, "Fast model that places a document the rules cannot (call type); "
         "blank classifies by rules only and marks such documents for a person", nullable=True, target="models",
         field="openrouter_document_classification_model", group="models")
    _add("models.brief", "str", SOL, "Brief writer and repair", env=("ATELIER_BRIEF_MODEL",), nullable=True, target="models+storage",
         field="brief_model", scopes=B, group="models")
    _add("models.brief_review", "str", SONNET, "Brief plan, grade and review", env=("ATELIER_BRIEF_REVIEW_MODEL",),
         nullable=True, target="models+storage", field="brief_review_model", scopes=B, group="models")
    _add("models.pack_writer", "str", None, "Pack writer; production packs refuse to run without it", env=("ATELIER_PACK_WRITER_MODEL",),
         nullable=True, target="models+storage", field="pack_writer_model", scopes=P, group="models")
    _add("models.pack_review", "str", None, "Pack reviewer; production packs refuse to run without it",
         env=("ATELIER_PACK_REVIEW_MODEL",), nullable=True, target="models+storage", field="pack_review_model", scopes=P,
         group="models")
    effort = dict(type="enum", choices=("low", "medium", "high"), nullable=True, target="models")
    _add("models.reasoning_effort.default", default="high", description="Reasoning effort for every stage without its own",
         env=("CONTENT_ATELIER_LLM_REASONING_EFFORT",), field="llm_reasoning_effort", scopes=W + B + P, group="models",
         **effort)
    for suffix in STAGE_SUFFIXES:
        # The pack writer and reviewer run at medium effort, as the planning probe did (NP.B5): high would double the cost.
        _add(f"models.reasoning_effort.{suffix}", default="medium" if suffix.startswith("pack") else None,
             description=f"Reasoning effort for {suffix}; blank uses the default",
             field="stage_reasoning_effort", field_key=suffix, scopes=W if suffix in {
                 "moment_extraction", "angle_generation", "card_verification"} else B if suffix.startswith("brief") else P if
             suffix.startswith("pack") else (), group="models", **effort)
    _add("models.response_format", "enum", "json_schema", "Structured-output request format (R16: json_schema everywhere)",
         choices=("json_schema", "json_object"), env=("CONTENT_ATELIER_LLM_RESPONSE_FORMAT",), target="models",
         field="llm_response_format", scopes=W + B + P, group="models")
    _add("models.payload_format", "enum", "compact_weekly", "How the week is sent to the model (the whole week in one call)",
         choices=("legacy_flat", "compact_weekly"), env=("CONTENT_ATELIER_LLM_PAYLOAD_FORMAT",), target="models",
         field="llm_payload_format", scopes=W, group="models")
    _add("models.completion_tokens", "int", None, "Output token cap; blank sends none (provider default capacity)",
         env=("CONTENT_ATELIER_LLM_COMPLETION_TOKENS",), lo=1, nullable=True, target="models", field="llm_completion_tokens",
         scopes=W + B + P, group="models")
    # Paid evidence (N1 shakedown, 23 October): Luna's scene extractions used a median of 14,058 output tokens, reasoning
    # included, 17,914 at the 90th percentile and 20,607 at most, so the 16,000 every other stage takes would cut a third off.
    _add("models.completion_tokens.moment_extraction", "int", None, "Output token cap for scene extraction; blank uses "
         "models.completion_tokens", lo=1, nullable=True, target="models", field="stage_completion_tokens",
         field_key="moment_extraction", scopes=W, group="models")
    _add("models.input_limits_enabled", "bool", True, "Reject over-size requests locally; false only for an uncapped calibration run",
         env=("CONTENT_ATELIER_LLM_INPUT_LIMITS_ENABLED",), target="models", field="llm_input_limits_enabled", scopes=W,
         group="models")
    _add("models.request_timeout_seconds", "float", 900.0, "Per-request timeout for model calls",
         env=("CONTENT_ATELIER_REQUEST_TIMEOUT_SECONDS",), lo=1, target="models", field="request_timeout_seconds",
         scopes=W + B + P, group="models")
    _add("models.max_request_characters", "int", 120000, "Largest week of source material sent in one request (the trusted "
         "prefix is not counted)", env=("CONTENT_ATELIER_MAX_LLM_REQUEST_CHARACTERS",), lo=1, target="models",
         field="max_llm_request_characters", scopes=W, group="models")


def _prompts_and_kb():
    _add("prompts.profile.strategist", "enum", LEGACY_ANGLE_PROFILE, "Angle prompt profile (the strategist card profiles are "
         "opt-in; v3 and the legacy v1 are kept for replay; v7, E.B30: the point tests, beliefs and her card format)",
         choices=ANGLE_PROFILES, env=("CONTENT_ATELIER_ANGLE_PROMPT_PROFILE",), target="models",
         field="angle_prompt_profile", scopes=("weekly",), group="prompts")
    _add("prompts.profile.extraction", "enum", EXTRACTION_PROFILES[0], "Moment extraction: the moments ledger's per-document scenes (v2, or v3 with human lines and counter-expected decisions, E.B31), the whole-week prompt or the v1 scene loop",
         choices=EXTRACTION_PROFILES, env=("CONTENT_ATELIER_EXTRACTION_PROFILE",), target="models", field="extraction_profile",
         scopes=("weekly",), group="prompts")
    _add("prompts.profile.card_verification", "enum", CARD_VERIFICATION_PROFILES[0], "The card verifier's model-pass prompt: "
         "v3 (E.B26), or v4 (E.B30: the point tests of strategist v7, with the reason a card is rejected for public use)",
         choices=CARD_VERIFICATION_PROFILES, target="models", field="card_verification_profile", scopes=("weekly",),
         group="prompts")
    _add("prompts.profile.brief", "enum", BRIEF_SCHEMAS[0], "Brief contract for new briefs (v2 after its writer benchmark; v3, "
         "E.B23: the ledger built after writing, with writer v4; v4, E.B33: each asset's full copy in the 13 October order, "
         "with writer v5)",
         choices=BRIEF_SCHEMAS, env_aliases=(("v1", BRIEF_SCHEMAS[0]), ("v2", BRIEF_SCHEMAS[1]), ("v3", BRIEF_SCHEMAS[2]),
                                             ("v4", BRIEF_SCHEMAS[3])),
         env=("ATELIER_BRIEF_SCHEMA",),
         target="storage", field="brief_schema", scopes=("brief",), group="prompts")
    _add("prompts.profile.brief_writer", "enum", BRIEF_WRITERS[0], "The brief writer's prompt: v2, or v3 (E.B22: finished copy "
         "kept apart from direction, caveats only in Before publishing and Claims) for contract v2; v4 for contract v3 (E.B23), "
         "or v4.1 (v4 with the refresh's instructions and locked lines; a refresh of a v3 brief always uses it, 5.B6); "
         "v5 for contract v4 (E.B33), or v5.1 (v5 writing three Reels: story, stance, b-roll text; NP.B10), or v5.2 (v5.1 with "
         "identities, what happened next and team-practice evidence; N8), or v5.3 (v5.2 with the central story and two "
         "premises of their own, the premises it weighed and E2M's craft and editorial guide; Round 2)",
         choices=BRIEF_WRITERS,
         env=("ATELIER_BRIEF_WRITER",), target="storage", field="brief_writer", scopes=("brief",), group="prompts")
    # Content pack v2 (NP.B5, the content-packs plan section 5.4): the finisher, the fidelity check and the repair, each a
    # released prompt file (E.B17), and how the finisher runs.
    for stage, text in (("pack_finish", "The pack finisher's prompt (Opus 5.5 edits the approved brief's copy to the house "
                                        "style and writes a missing Reel kind)"),
                        ("pack_check", "The pack's fidelity check (every statement about the real event, supported or not)"),
                        ("pack_repair", "The pack's repair (patches for flagged sentences only)"),
                        ("pack_caption", "The post-recording pass (NP.B14: a Reel's caption and three covers from what Whitney "
                                         "said on the recorded take)"),
                        ("pack_refinish", "Finishing again with a permission (NP.B15: the finisher with the granted items and "
                                          "stated facts as evidence)")):
        released = PACK_PROFILES[stage]
        default = [p for p in released if p not in ROUND_TWO_PACK_PROFILES][-1]
        _add(f"prompts.profile.{stage}", "enum", default, text, choices=released, target="storage",
             field=f"{stage}_profile", scopes=("pack",), group="prompts")
    _add("packs.finish_mode", "enum", "finish", "How a pack is finished after Gate 2: finish (the finisher and its fidelity "
         "loop), missing_only (the brief's copy verbatim, only a missing Reel kind written and checked) or assemble (no "
         "model call; a missing Reel kind shows as not written)", choices=("finish", "missing_only", "assemble"),
         target="storage", field="pack_finish_mode", scopes=("pack",), group="packs")
    _add("knowledge_base.version", "str", None, "Pin a compiled knowledge-base version for every stage; blank uses the "
         "active approved version", nullable=True, scopes=("weekly", "brief"), group="knowledge_base")
    _add("knowledge_base.directory", "str", None, "Development override: a file knowledge base to load instead of "
         "backend/knowledge_base. Environment only", env=("CONTENT_ATELIER_KNOWLEDGE_BASE_DIR",), nullable=True,
         env_override=True, table=False, target="models", field="knowledge_base_root", scopes=("weekly", "brief"), group="knowledge_base")
    _add("briefs.channels", "list", ("reel", "carousel", "email", "caption"), "The confirmed channel set for v2 format plans",
         env=("ATELIER_BRIEF_CHANNELS",), target="storage", field="brief_channels", scopes=("brief",), group="briefs")
    _add("gates.one_click", "bool", False, "The two approvals are one click and the screens ask only for feedback: the public stance, "
         "verify items, CTA, before-publishing answers and claims check no longer stop an approval. Material a client asked to "
         "remove, a stale version and a card rejected for public use still do", target="storage", scopes=("brief",), group="briefs")
    _add("briefs.max_characters", "int", 120000, "Largest brief request, in characters", env=("ATELIER_BRIEF_MAX_CHARACTERS",),
         lo=1, target="storage", field="brief_max_characters", scopes=("brief", "pack"), group="briefs")


def _embedding_matching_scoring():
    pinned = dict(table=False, target="models", scopes=("weekly", "brief", "encoding", "matching"), group="embedding")
    _add("embedding.endpoint", "str", "https://openrouter.ai/api/v1", "Embedding endpoint of the archive's contract. Environment "
         "only: changing it means re-encoding (ATELIER_ALLOW_EMBEDDING_CONTRACT_CHANGE)", env=("EMBEDDING_BASE_URL",),
         field="embedding_base_url", **pinned)
    _add("embedding.model", "str", "openai/text-embedding-3-small", "Embedding model string of the archive's contract. Environment only",
         env=("OPENAI_EMBEDDING_MODEL",), field="embedding_model", **pinned)
    _add("embedding.dimensions", "int", 1536, "Embedding dimensions of the archive's contract. Environment only",
         env=("CONTENT_ATELIER_EMBEDDING_DIMENSIONS",), field="embedding_dimensions", **pinned)
    _add("matching.related", "float", 0.78, "Cosine at which a past angle counts as related", env=("CONTENT_ATELIER_SIMILARITY_THRESHOLD",),
         lo=0, hi=1, target="models", field="similarity_threshold", scopes=("weekly", "matching"), group="matching")
    _add("matching.close", "float", 0.90, "Cosine at which two angles of one week are flagged as close (cards collapse at "
         "matching.duplicate)", env=("CONTENT_ATELIER_CLOSE_THRESHOLD",), lo=0, hi=1, target="models", field="close_similarity_threshold", scopes=("weekly", "matching"), group="matching")
    # E.B6: calibrated on 4,152 labelled same-week card pairs of Weeks 1 and 2 (research/duplicate-labels-2026-10-19): 0.86
    # collapses the Week 2 buying-research pair (0.867) at precision 0.90; 0.90 let it through (K6).
    _add("matching.duplicate", "float", 0.86, "Cosine at which a card collapses into a better-ranked one (E.B6)",
         env=("ATELIER_DUPLICATE_COSINE",), lo=0.5, hi=1.0, scopes=("weekly", "matching"), group="matching")
    _add("matching.half_life_days", "float", 28.0, "Recency half-life of a past angle's risk", lo=0.1, target="models",
         field="recency_half_life_days", scopes=("weekly", "matching"), group="matching")
    _add("matching.max_recency_penalty", "float", 0.50, "Largest score reduction for a repeated angle", lo=0, hi=1, target="models",
         field="max_recency_penalty", scopes=("weekly", "matching"), group="matching")
    _add("matching.approval_cutoff", "float", None, "The comparison cutoff Gate 1 approval uses; blank until an authoritative "
         "policy is selected", env=("ATELIER_ANGLE_APPROVAL_CUTOFF",), lo=0, hi=1, nullable=True, target="storage",
         field="angle_approval_cutoff", scopes=("weekly", "matching"), group="matching")
    _add("scoring.visible_threshold", "float", 70.0, "Adjusted score above which a legacy angle is visible",
         env=("CONTENT_ATELIER_VISIBLE_THRESHOLD",), lo=0, hi=100, target="models", field="visible_threshold", scopes=("weekly", "matching"),
         group="scoring")


def _features_cycle_context():
    for name, var, attribute, text in (
            ("briefs", "ATELIER_BRIEFS_ENABLED", "brief_enabled", "Briefs (Gate 2, research, writer); needs a reviewed brand bundle"),
            ("packs", "ATELIER_PACKS_ENABLED", "packs_enabled", "Content packs"),
            ("calendar", "ATELIER_CALENDAR_ENABLED", "calendar_enabled", "The production calendar"),
            ("context", "ATELIER_CONTEXT_ENABLED", "context_enabled", "The Knowledge screens and review queue (Phase L)")):
        _add(f"features.{name}", "bool", False, text, env=(var,), target="storage", field=attribute,
             scopes=("brief",) if name == "briefs" else (), group="features")
    _add("display.timezone", "zone", "Asia/Kolkata", "Calendar display time zone only", env=("ATELIER_CALENDAR_TIMEZONE",),
         target="storage", field="calendar_timezone", group="display")
    _add("slack.schedule_notifications.email_channel_id", "str", None, "Email scheduling notification channel; blank disables it",
         env=("ATELIER_SLACK_EMAIL_CHANNEL_ID",), nullable=True, group="slack")
    _add("slack.schedule_notifications.social_channel_id", "str", None, "Social scheduling notification channel; blank disables it",
         env=("ATELIER_SLACK_SOCIAL_CHANNEL_ID",), nullable=True, group="slack")
    _add("slack.schedule_notifications.public_app_url", "str", None, "Public HTTPS Atelier origin for direct piece links",
         env=("ATELIER_PUBLIC_APP_URL",), nullable=True, group="slack")
    _add("cycle.timezone", "zone", "America/Chicago", "The weekly cycle's time zone (R36)", scopes=("cycle",), group="cycle")
    _add("cycle.weekday", "int", 6, "The weekday the weekly collection closes and the scheduled cycle starts, 0 Monday to 6 "
         "Sunday (R36 said Saturday; the owner moved it to Sunday, 25 October 2026)", lo=0, hi=6, scopes=("cycle",), group="cycle")
    _add("cycle.hour", "int", 4, "The hour, in the cycle time zone, the weekly collection closes and the scheduled cycle starts "
         "(R36)", lo=0, hi=23, scopes=("cycle",), group="cycle")
    _add("cycle.schedule.enabled", "bool", False, "The weekly cycle starts by itself at the scheduled time (3.B11, Phase N7)",
         group="cycle")
    _add("cycle.schedule.first_day", "str", None, "The first day the scheduled cycle runs, YYYY-MM-DD in the cycle time zone",
         group="cycle")
    _add("cycle.schedule.actor", "str", None, "The approver (and intake administrator) whose standing approval the scheduled "
         "cycle starts under", group="cycle")
    ctx = ("weekly", "brief")
    _add("context.budget.prefix_tokens", "int", 30000, "Knowledge-base prefix budget (about four characters a token)",
         env=("ATELIER_CONTEXT_PREFIX_TOKENS",), lo=1, scopes=ctx, group="context")
    _add("context.budget.situational_tokens", "int", 6000, "Dated situational block budget", env=("ATELIER_CONTEXT_SITUATIONAL_TOKENS",),
         lo=1, scopes=ctx, group="context")
    _add("context.budget.exemplar_tokens", "int", 4000, "Exemplar budget", env=("ATELIER_CONTEXT_EXEMPLAR_TOKENS",), lo=1,
         scopes=ctx, group="context")
    _add("context.exemplars.k", "int", 3, "Exemplars chosen per brief", env=("ATELIER_CONTEXT_EXEMPLARS_K",), lo=0, scopes=ctx,
         group="context")
    _add("context.schedule.nightly_hour", "int", 3, "Hour (UTC) the nightly staleness job may run", env=("ATELIER_CONTEXT_NIGHTLY_HOUR",),
         lo=0, hi=23, group="context")
    _add("context.schedule.mining_weekday", "int", 0, "Weekday (0 Monday) of the learning loop", env=("ATELIER_CONTEXT_MINING_WEEKDAY",),
         lo=0, hi=6, group="context")
    _add("context.schedule.mining_live", "bool", False, "Whether the learning loop's categoriser may make a paid call",
         env=("ATELIER_CONTEXT_MINING_LIVE",), group="context")
    _add("offers.status", "list", (), "Offer status changes made in the app, over the offer calendar file: each line 'Offer: "
         "status' or 'Offer: status until YYYY-MM-DD' (open, waitlist, delivering or closed). Read by every cycle's strategy brief",
         group="context")
    _add("context.release.benchmark_required", "bool", True, "Whether an approved identity change (rules, exemplars, beliefs, "
         "audience language, format) waits for a benchmark result before it is used (R44). Off in production: the approver's "
         "approval releases it (the owner, 25 October 2026: no paid benchmark and no developer in the weekly loop)",
         group="context")
    _add("context.plan_max_age_days", "int", 30, "A cycle whose newest content plan entry is older than this many days "
         "warns in its week summary (L.B10)", lo=1, scopes=("weekly",), group="context")
    _add("context.mining.support_weeks", "int", 4, "Weeks of Gate reasons and edits a learned rule candidate's two-decision "
         "support may span; 1 is the mined week alone (L.B11)", lo=1, hi=12, group="context")
    _add("context.same_point.window_days", "int", 60, "A card repeating a central point WIA published this many days ago or "
         "less ranks below the cards that do not (3.B5, D23)", lo=0, hi=365, scopes=("weekly",), group="context")
    _add("context.same_point.fresh_angle_days", "int", 30, "The window for a fresh angle on a published point: the card's point "
         "repeats it but its title does not (3.B5, D23)", lo=0, hi=365, scopes=("weekly",), group="context")
    for kind, days in REVIEW_DAYS.items():
        _add(f"context.review_interval.{kind}", "int", days, f"Review interval in days for {kind} items",
             env=(f"ATELIER_CONTEXT_REVIEW_DAYS_{kind.upper()}",), lo=1, group="context")
    _add("documents.included_call_types", "list", ("client_1to1", "office_hours", "workshop", "prospect", "slack_thread"),
         "Call types whose documents are included in extraction and cycles; internal, vendor and fragment are excluded by "
         "default, 'other' waits for a person (plan 1.B4)", group="documents")
    _add("documents.staff_email_domains", "list", ("weddingindustryads.com",), "Email domains that mark a call participant as "
         "WIA staff (a Fathom invitee address); names are resolved against the roster", group="documents")
    _add("documents.slack_export.excluded_channels", "list", ("wia-ai-team-testing",), "Slack channels (by name) the export import "
         "leaves out: testing channels are not evidence", group="documents")
    _add("documents.fragment_words", "int", 50, "A transcript with fewer words than this is a fragment: the recording started "
         "and the meeting did not", lo=1, group="documents")
    _add("documents.segmentation.max_characters", "int", 2400, "Largest chunk body, in characters; a turn longer than this "
         "stays whole", lo=200, hi=6000, group="documents")
    _add("documents.segmentation.gap_seconds", "int", 90, "A pause longer than this starts a new chunk", lo=10, group="documents")
    _add("documents.slack_triage.min_words", "int", 3, "A Slack thread with fewer words than this (emoji and links not counted) "
         "is excluded before extraction: an acknowledgement is not evidence (plan 2.B9)", lo=0, group="documents")
    _add("documents.slack_triage.bot_names", "list", ("slackbot", "zapier", "workflow builder", "github", "google calendar", "zoom"),
         "Speaker names (any name ending in 'bot' too) whose Slack posts are automation; a thread of only these is excluded "
         "before extraction (plan 2.B9)", group="documents")
    _add("moments.extraction_profile", "enum", DOCUMENT_EXTRACTION_PROFILES[0], "Scene profile for a document's own extraction "
         "(2.B2): v2 emits all twelve moment types and carries the call type, speaker roles and glossary; v3 (E.B31) adds human "
         "lines and counter-expected decisions; v1 stays for replay "
         "and comparison", choices=DOCUMENT_EXTRACTION_PROFILES, group="moments")
    _add("moments.estimate.output_tokens_per_document", "int", 6000, "Output tokens (reasoning included) assumed per document by "
         "`moments extract --estimate`; an assumption to replace with the pilot's measured figure", lo=1, group="moments")
    _add("moments.estimate.input_usd_per_million", "float", None, "USD per million input tokens for the extraction model when "
         "it is not in the price table (costs.py); blank uses the table", lo=0, nullable=True, group="moments")
    _add("moments.estimate.output_usd_per_million", "float", None, "USD per million output tokens for the extraction model when "
         "it is not in the price table (costs.py); blank uses the table", lo=0, nullable=True, group="moments")
    _add("intake.slack.workspace", "str", "T03P5A3L1DK", "Slack workspace of the intake connector", env=("ATELIER_SLACK_WORKSPACE",),
         target="intake", field="workspace", group="intake")
    _add("intake.slack.channels", "list", ("C082DURRJ2U", "C09LQ656BPU", "C091CPQD8L9"), "Slack channels the intake connector reads",
         env=("ATELIER_SLACK_CHANNELS",), target="intake", field="channels", group="intake")
    _add("intake.audio_model", "str", "small.en", "Speech-to-text model for audio uploads", env=("ATELIER_INTAKE_AUDIO_MODEL",),
         target="intake", field="audio_model", group="intake")


def _search_and_topics():
    """Search over the moments ledger and the topic registry (plan 2.B5 to 2.B7). Read per call from the settings table."""
    _add("search.rrf_k", "int", 60, "Reciprocal rank fusion constant: a hit ranked r by a method adds 1/(k + r); a larger k "
         "flattens the difference between ranks", lo=1, hi=1000, group="search")
    _add("search.candidates", "int", 100, "Candidates each method (phrase, meaning) hands to the fusion for each kind of hit; "
         "the answer is the best k of them", lo=10, hi=500, group="search")
    _add("search.semantic_min_cosine", "float", 0.0, "Meaning matches below this cosine are dropped before fusion; 0 keeps the "
         "nearest candidates whatever their cosine. Raise it only after measuring on real moments", lo=0, hi=1, group="search")
    _add("moments.embedding.batch_size", "int", 32, "Moments sent to the embedding model in one request", lo=1, hi=256,
         scopes=("moment_embedding",), group="moments")
    _add("topics.candidates", "int", 5, "Nearest topics offered for a moment, by embedding", lo=1, hi=20, scopes=("topics",),
         group="topics")
    _add("topics.attach_similarity", "float", 0.80, "A moment whose nearest active topic is at least this similar (cosine) is "
         "attached to it without a model call", lo=0.5, hi=1.0, scopes=("topics",), group="topics")


# The released pack prompt profiles (packs/contracts_v2.RELEASED, which a test keeps in step). The default is the last before
# Round 2 (contracts_v2.PROFILES): Round 2's profiles (finisher v3, check v4, repair v2, refinish v2) are chosen by setting.
PACK_PROFILES = {"pack_finish": ("2026-10-25.pack-finish.v1", "2026-10-25.pack-finish.v2", "2026-10-27.pack-finish.v3",
                                 "2026-10-27.pack-finish.v4"),
                 "pack_check": ("2026-10-25.pack-check.v1", "2026-10-25.pack-check.v2", "2026-10-26.pack-check.v3",
                                "2026-10-27.pack-check.v4"),
                 "pack_repair": ("2026-10-25.pack-repair.v1", "2026-10-27.pack-repair.v2"),
                 "pack_caption": ("2026-10-26.pack-caption.v1",),
                 "pack_refinish": ("2026-10-26.pack-refinish.v1", "2026-10-27.pack-refinish.v2", "2026-10-27.pack-refinish.v3")}
ROUND_TWO_PACK_PROFILES = ("2026-10-27.pack-finish.v3", "2026-10-27.pack-check.v4", "2026-10-27.pack-repair.v2",
                           "2026-10-27.pack-refinish.v2", "2026-10-27.pack-finish.v4", "2026-10-27.pack-refinish.v3")
BUDGET_PURPOSES = ("cycle", "briefs", "refreshes", "embedding", "extraction", "context_mining", "packs")
# Standing weekly budgets (6.B3), in USD and calls per week. Plan D36 sizes live operation at about USD 2 to 4 a week, scaled
# from the 18 October development week (USD 1.19 for three cards and three briefs on excerpts) to whole-week input; these
# defaults total USD 3.50: a whole-week strategist call with verification (cycle), three briefs with their research and
# review (briefs), two refreshes, the week's new calls' scenes (extraction) and the learning loop. Measured in the first live
# week and reset with `storage_cli budgets set`.
# Content packs (D43f, the owner, 24 October): USD 3.50 a week, three packs at up to USD 0.85, two post-recording passes and
# one Finish again; 60 calls. The week of 26 October is set to USD 6.00 on production with `budgets set`.
BUDGET_DEFAULTS = {"cycle": (1.20, 80), "briefs": (1.20, 200), "refreshes": (0.50, 120), "embedding": (0.10, 600),
                   "extraction": (0.40, 200), "context_mining": (0.10, 60), "packs": (3.50, 60)}


def _budgets():
    _add("budgets.standing", "bool", True, "Paid calls without a named run plan spend this week's standing budget for their "
         "purpose (6.B3); false refuses them, as before standing budgets", group="budgets")
    _add("costs.count_from", "str", None, "The moment the costs page counts from (ISO 8601, for example "
         "2026-10-27T17:45:00Z; a day alone counts from 00:00 UTC): its totals, weeks and content packs leave out everything "
         "earlier, such as the team's own tests; blank counts the last weeks in full", nullable=True, group="budgets")
    _add("budgets.uncapped", "bool", False, "No weekly spending caps (the owner, 27 October 2026): every purpose's weekly plan "
         "is unlimited, so no paid call is refused or made to wait for a cap; spend is still recorded and shown. The model "
         "provider's own key limit still applies", group="budgets")
    for purpose, (usd, calls) in BUDGET_DEFAULTS.items():
        _add(f"budgets.weekly_usd.{purpose}", "float", usd, f"Standing weekly cap in USD for {purpose.replace('_', ' ')} calls; "
             "blank means no standing budget, so those calls need a named run plan", lo=0.01, hi=100, nullable=True,
             group="budgets")
        _add(f"budgets.weekly_calls.{purpose}", "int", calls, f"Standing weekly call limit for {purpose.replace('_', ' ')} "
             "(a repair call is a call)", lo=1, hi=100000, group="budgets")


_models()
_prompts_and_kb()
_embedding_matching_scoring()
_features_cycle_context()
_search_and_topics()
_budgets()
SECRET_SEGMENTS = {"secret", "secrets", "password", "passwords", "credential", "credentials", "token", "dsn", "apikey"}


def looks_secret(key: str) -> bool:
    """A key naming a secret, token, password, API key or database URL (these stay in the environment)."""
    import re
    parts = set(re.split(r"[._\-\s]+", key.lower()))
    return bool(parts & SECRET_SEGMENTS) or {"api", "key"} <= parts or {"database", "url"} <= parts




def definition(key: str) -> Definition:
    try:
        return _BY_KEY[key]
    except KeyError:
        if looks_secret(key):
            raise SettingError(f"{key} looks like a secret or an endpoint; those stay in environment variables") from None
        raise SettingError(f"Unknown setting {key}; `storage_cli settings list` shows the keys") from None


def default(key: str):
    """The code default of a key (pydantic field defaults read this, so code and registry cannot differ)."""
    return _BY_KEY[key].default


def keys_for(scope: str) -> list[str]:
    return [d.key for d in DEFINITIONS if scope in d.scopes]


# --------------------------------------------------------------------------------------------------------------
# Typing


def _fail(d, why, source=None):
    where = f"{source} (setting {d.key})" if source else d.key
    raise SettingError(f"{where}: {why}")


def coerce(d: Definition, raw, *, source: str | None = None):
    """Validate a value from a table row (JSON), the environment (text) or the CLI; return the typed value."""
    if raw is None or (isinstance(raw, str) and not raw.strip() and d.type != "str"):
        if d.nullable:
            return None
        _fail(d, "a value is required", source)
    if d.type == "str" or d.type == "zone":
        if not isinstance(raw, str):
            _fail(d, f"expected text, got {type(raw).__name__}", source)
        value = raw.strip()
        if not value:
            if d.nullable:
                return None
            _fail(d, "a value is required", source)
        if d.type == "zone":
            from zoneinfo import ZoneInfo
            try:
                ZoneInfo(value)
            except Exception:
                _fail(d, f"{value!r} is not a time zone name (for example America/Chicago)", source)
        return value
    if d.type == "bool":
        if isinstance(raw, bool):
            return raw
        if isinstance(raw, str) and raw.strip().lower() in {"true", "false"}:
            return raw.strip().lower() == "true"
        _fail(d, "expected true or false", source)
    if d.type in {"int", "float"}:
        if isinstance(raw, bool):
            _fail(d, "expected a number", source)
        try:
            number = float(raw) if d.type == "float" else (raw if isinstance(raw, int) else int(str(raw).strip()))
        except (TypeError, ValueError):
            _fail(d, f"expected {'a number' if d.type == 'float' else 'a whole number'}, got {raw!r}", source)
        if d.type == "int" and isinstance(raw, float):
            _fail(d, "expected a whole number", source)
        if isinstance(number, float) and not math.isfinite(number):
            _fail(d, "expected a finite number", source)
        if (d.lo is not None and number < d.lo) or (d.hi is not None and number > d.hi):
            span = (f"between {d.lo} and {d.hi}" if d.lo is not None and d.hi is not None
                    else f"at least {d.lo}" if d.lo is not None else f"at most {d.hi}")
            _fail(d, f"must be {span}", source)
        return number
    if d.type == "enum":
        if not isinstance(raw, str):
            _fail(d, "expected text", source)
        value = dict(d.env_aliases).get(raw.strip(), raw.strip())
        if value not in d.choices:
            _fail(d, f"{raw!r} is not one of {', '.join(d.choices)}", source)
        return value
    if d.type == "list":
        items = [x.strip() for x in raw.split(",")] if isinstance(raw, str) else raw
        if not isinstance(items, (list, tuple)) or not all(isinstance(x, str) for x in items):
            _fail(d, "expected a list of text values", source)
        items = tuple(x.strip() for x in items if x.strip())
        if not items:
            _fail(d, "at least one value is required", source)
        return items
    raise AssertionError(d.type)


def plain(value):
    """JSON form of a typed value."""
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, Path):
        return str(value)
    return value


# --------------------------------------------------------------------------------------------------------------
# The table

_CACHE: dict[str, dict] = {}


def invalidate(url: str | None = None) -> None:
    """Forget cached table reads in this process (a write calls this; others see it within the cache window)."""
    if url is None:
        _CACHE.clear()
    else:
        _CACHE.pop(url, None)


def _read(conn) -> tuple[dict, str]:
    """Rows of the settings table, and 'table' or 'no_table' (a database below migration 005). A savepoint keeps a
    missing table from aborting the caller's transaction."""
    from psycopg.errors import UndefinedTable
    try:
        with conn.transaction():
            rows = conn.execute("SELECT key,value,updated_by,updated_at FROM settings").fetchall()
    except UndefinedTable:
        return {}, "no_table"
    return {r["key"]: {"value": r["value"], "updated_by": r["updated_by"], "updated_at": r["updated_at"]} for r in rows}, "table"


def _fetch(url: str) -> dict:
    """The table through a short-lived connection, cached for ATELIER_SETTINGS_CACHE_SECONDS (default 5). A database
    that cannot be reached degrades to the environment and defaults (start-up refuses such a process anyway)."""
    ttl = float(os.environ.get(CACHE_SECONDS) or 5)
    entry = _CACHE.get(url)
    now = time.monotonic()
    if entry and now - entry["at"] < (UNREACHABLE_SECONDS if entry["state"] == "unreachable" else ttl):
        return entry
    import psycopg
    from psycopg.rows import dict_row
    try:
        with psycopg.connect(url, row_factory=dict_row, connect_timeout=3, autocommit=True) as conn:
            rows, state = _read(conn)
    except psycopg.OperationalError as error:
        if not entry or entry["state"] != "unreachable":
            log.warning("Settings table unreachable; using environment and defaults: %s", str(error).strip()[:200])
        rows, state = {}, "unreachable"
    stamp = hashlib.sha256(json.dumps({k: [r["value"], str(r["updated_at"])] for k, r in sorted(rows.items())},
                                      sort_keys=True, default=str).encode()).hexdigest()[:16] + state
    _CACHE[url] = entry = {"at": now, "rows": rows, "state": state, "stamp": stamp}
    return entry


@dataclass
class Effective:
    """The effective settings: one typed value per key, and where each came from."""
    values: dict[str, Any]
    sources: dict[str, str]
    rows: dict[str, dict] = field(default_factory=dict)
    state: str = "not_configured"  # table, no_table, unreachable, not_configured
    problems: list[str] = field(default_factory=list)
    shadowed: dict[str, str] = field(default_factory=dict)  # key -> the environment variable a row overrides
    database_url: str | None = None
    stamp: str = ""

    def __getitem__(self, key):
        return self.values[key]

    def source(self, key):
        return self.sources[key]


def load(conn=None, *, database_url: str | None = None, read_files: bool = True, environ=None, definitions=None,
         use_cache: bool = True, rows: dict | None = None) -> Effective:
    """Resolve every setting. `conn` reads the table in the caller's transaction; otherwise `database_url` or
    ATELIER_DATABASE_URL names the database (cached for a few seconds); with neither, the environment and
    defaults apply. `rows` ({key: {"value": ...}}) stands in for the table (tests and tools)."""
    env = os.environ if environ is None else environ
    if read_files and environ is None:
        load_env_files()
    url = None
    if rows is not None:
        rows, state, stamp = rows, "table", ""
    elif conn is not None:
        rows, state = _read(conn)
        stamp = ""
    else:
        url = database_url or env.get("ATELIER_DATABASE_URL") or None
        if url:
            if not use_cache:
                invalidate(url)
            entry = _fetch(url)
            rows, state, stamp = entry["rows"], entry["state"], entry["stamp"]
        else:
            rows, state, stamp = {}, "not_configured", ""
    values, sources, problems, shadowed = {}, {}, [], {}
    for d in definitions or DEFINITIONS:
        env_name = next((v for v in d.env if (env.get(v) or "").strip()), None)
        layers = []
        if env_name:
            layers.append(("env", coerce(d, env[env_name], source=env_name)))
        if d.table and d.key in rows:
            try:
                row_value = ("table", coerce(d, rows[d.key]["value"], source=f"settings row {d.key}"))
                layers.insert(0 if not d.env_override else len(layers), row_value)
            except SettingError as error:
                problems.append(str(error))
        elif not d.table and d.key in rows:
            problems.append(f"settings row {d.key}: this key is environment-only; the row is ignored")
        if layers:
            sources[d.key], values[d.key] = layers[0][0], layers[0][1]
            if len(layers) > 1 and layers[0][0] == "table" and layers[1][1] != layers[0][1]:
                shadowed[d.key] = env_name
        else:
            sources[d.key], values[d.key] = "default", d.default
    return Effective(values, sources, rows if conn is not None or state == "table" else {}, state, problems, shadowed, url, stamp)


def value(key: str, conn=None, **kw):
    """One setting's effective value (the callers that read a single threshold or budget)."""
    return load(conn, read_files=False, **kw).values[key]


def values(keys, conn=None, **kw) -> dict:
    eff = load(conn, read_files=False, **kw)
    return {k: eff.values[k] for k in keys}


def cycle_schedule(conn=None) -> dict:
    """When the weekly collection closes (R36): zone name, weekday (0 Monday) and hour."""
    eff = load(conn, read_files=False)
    return {"timezone": eff["cycle.timezone"], "weekday": eff["cycle.weekday"], "hour": eff["cycle.hour"]}


def cycle_schedule_text(conn=None) -> str:
    """For example 'Saturday 04:00 America/Chicago'."""
    import calendar
    s = cycle_schedule(conn)
    return f"{calendar.day_name[s['weekday']]} {s['hour']:02d}:00 {s['timezone']}"


def knowledge_base_pin(conn) -> str | None:
    return load(conn, read_files=False)["knowledge_base.version"]


# --------------------------------------------------------------------------------------------------------------
# Writing


def _writable(key: str) -> Definition:
    d = definition(key)
    if not d.table:
        raise SettingError(f"{key} is environment-only ({', '.join(d.env)}); it cannot be set in the table")
    return d


def set_value(conn, key: str, raw, actor: str) -> dict:
    """Validate and store one setting; returns the old and new effective values. The caller commits."""
    if not actor or not actor.strip():
        raise SettingError("An actor is required to change a setting")
    d = _writable(key)
    typed = coerce(d, raw, source="value")
    before = load(conn, read_files=False)
    conn.execute("""INSERT INTO settings(key,value,updated_by) VALUES (%s,%s,%s)
        ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value,updated_by=EXCLUDED.updated_by,updated_at=now()""",
                 (key, json.dumps(plain(typed)), actor.strip()))
    invalidate()
    return {"key": key, "before": plain(before.values[key]), "before_source": before.sources[key], "value": plain(typed),
            "updated_by": actor.strip()}


def validate_profile(profile: dict) -> dict:
    """A configuration file's settings, every key checked writable and every value coerced before any is stored."""
    values = profile.get("settings") if isinstance(profile, dict) else None
    if not isinstance(values, dict) or not values:
        raise SettingError("A configuration file needs a non-empty \"settings\" object")
    problems, typed = [], {}
    for key, raw in values.items():
        try:
            typed[key] = coerce(_writable(key), raw, source="file")
        except SettingError as error:
            problems.append(str(error))
    if problem := brief_writer_problem(typed.get("prompts.profile.brief"), typed.get("prompts.profile.brief_writer")):
        problems.append(problem)
    if problems:
        raise SettingError("; ".join(problems))
    return typed


def apply_profile(conn, profile: dict, actor: str, *, dry_run: bool = False) -> dict:
    """Store a whole configuration (for example the production configuration, plan E.X4) as rows, all or nothing.
    Keys whose effective value already equals the file's are left alone. The caller commits."""
    typed = validate_profile(profile)
    current = load(conn, read_files=False)
    changes = [k for k, v in typed.items() if not (current.sources[k] == "table" and plain(current.values[k]) == plain(v))]
    if dry_run:
        return {"dry_run": True, "would_change": changes, "unchanged": [k for k in typed if k not in changes]}
    applied = [set_value(conn, k, plain(typed[k]), actor) for k in changes]
    return {"applied": applied, "unchanged": [k for k in typed if k not in changes]}


def unset_value(conn, key: str, actor: str) -> dict:
    """Delete the row, so the legacy environment variable (if any) and then the code default apply again."""
    d = _writable(key)
    before = load(conn, read_files=False)
    removed = conn.execute("DELETE FROM settings WHERE key=%s RETURNING key", (d.key,)).fetchone()
    invalidate()
    after = load(conn, read_files=False)
    return {"key": key, "was_set": bool(removed), "before": plain(before.values[key]), "value": plain(after.values[key]),
            "source": after.sources[key], "unset_by": actor}


def import_env(conn, actor: str, *, environ=None, overwrite: bool = False) -> dict:
    """Record the behavioural environment variables as rows (once per key unless `overwrite`), so the table holds
    the deployment's values and the variables can be removed."""
    env = os.environ if environ is None else environ
    imported, skipped, invalid = [], [], []
    eff = load(conn, read_files=False, environ={})  # the rows only: an invalid variable is reported below, not raised
    for d in DEFINITIONS:
        name = next((v for v in d.env if (env.get(v) or "").strip()), None)
        if not name or not d.table:
            continue
        try:
            typed = coerce(d, env[name], source=name)
        except SettingError as error:
            invalid.append(str(error))
            continue
        if d.key in eff.rows and not overwrite:
            skipped.append({"key": d.key, "reason": "a row exists"})
            continue
        set_value(conn, d.key, plain(typed), actor)
        imported.append({"key": d.key, "env": name, "value": plain(typed)})
    return {"imported": imported, "skipped": skipped, "invalid": invalid, "actor": actor}


def listing(conn=None, *, environ=None) -> list[dict]:
    eff = load(conn, read_files=False, environ=environ)
    out = []
    for d in DEFINITIONS:
        row = eff.rows.get(d.key)
        out.append({"key": d.key, "value": plain(eff.values[d.key]), "source": eff.sources[d.key], "default": plain(d.default),
                    "type": d.type + ("?" if d.nullable else ""), "choices": list(d.choices) or None, "env": list(d.env) or None,
                    "settable": d.table, "restart_required": d.restart_required, "description": d.description,
                    **({"env_ignored": eff.shadowed[d.key]} if d.key in eff.shadowed else {}),
                    **({"updated_by": row["updated_by"], "updated_at": row["updated_at"]} if row and d.table else {})})
    return out


# --------------------------------------------------------------------------------------------------------------
# Typed objects built from the effective settings


class LoadedSettings(BaseModel):
    """Base of Settings, StorageSettings and IntakeSettings: remembers the effective settings it was built from, so
    a long-running process can pick up a changed row (`refreshed`) and a run can snapshot where values came from."""
    _effective: Any = PrivateAttr(default=None)
    _stamp: str | None = PrivateAttr(default=None)
    _refreshable: bool = PrivateAttr(default=False)

    def __setattr__(self, name, value):
        if not name.startswith("_") and self._refreshable:
            self._refreshable = False  # code overrode a loaded value: it is no longer the table's
        super().__setattr__(name, value)

    def model_copy(self, *, update=None, deep=False):
        copy = super().model_copy(update=update, deep=deep)
        if update:
            copy._refreshable = False
        return copy

    @classmethod
    def from_effective(cls, eff: Effective):  # pragma: no cover - overridden
        raise NotImplementedError

    def _attach(self, eff: Effective):
        self._effective, self._stamp, self._refreshable = eff, eff.stamp, True
        return self

    @property
    def setting_sources(self) -> dict[str, str]:
        return dict(self._effective.sources) if self._effective is not None else {}

    def refreshed(self):
        """This object, or a fresh one when the settings table changed since it was loaded. Objects built by hand,
        copied with changes, or loaded without a database come back unchanged."""
        if not self._refreshable or not self._effective.database_url:
            return self
        url = self._effective.database_url
        if _fetch(url)["stamp"] == self._stamp:
            return self
        eff = load(database_url=url, read_files=False)
        return type(self).from_effective(eff)


def refresh(settings):
    """`settings.refreshed()` for a loaded settings object; anything else comes back unchanged."""
    refreshed = getattr(settings, "refreshed", None)
    return refreshed() if refreshed is not None else settings


# --------------------------------------------------------------------------------------------------------------
# Snapshots


def _current(obj, d: Definition):
    value = getattr(obj, d.field)
    if d.field_key:
        value = value.get(d.field_key)
    if d.key == "knowledge_base.directory":
        from . import config
        return None if Path(value) == config.BACKEND_ROOT / "knowledge_base" else str(value)
    return plain(value)


def snapshot(scope: str, *, models=None, storage=None, intake=None, conn=None) -> dict:
    """The effective values of the behavioural keys a run of this scope uses, and where each came from. A value is
    read from the typed object the run was started with (so it is what the run used); a key that no object holds
    comes from the table through `conn`."""
    keys = keys_for(scope)
    fresh = None
    carriers = {"models": models, "storage": storage, "intake": intake}
    out = {}
    for key in keys:
        d = _BY_KEY[key]
        holders = [carriers.get(t) for t in (d.target or "").split("+") if carriers.get(t) is not None]
        holder = holders[0] if holders else None
        eff = getattr(holder, "_effective", None) if holder is not None else None
        if holder is not None and d.field:
            current = _current(holder, d)
        else:
            if fresh is None:
                fresh = load(conn, read_files=False)
            eff, current = fresh, plain(fresh.values[key])
        if eff is not None and plain(eff.values[key]) == current:
            source = eff.sources[key]
        else:
            source = "default" if current == plain(d.default) else "explicit"
        out[key] = {"value": current, "source": source}
    return {"version": 1, "scope": scope, "values": out}


def snapshot_refs(scope: str, **kw) -> dict:
    """`**snapshot_refs('weekly', models=..., storage=...)` inside a run's input_refs."""
    return {"settings_snapshot": snapshot(scope, **kw)}


# --------------------------------------------------------------------------------------------------------------
# A live run names its models


def _source_in_use(obj, key):
    """Where the value an object holds came from: its recorded source, or 'explicit' when code changed it since."""
    eff = getattr(obj, "_effective", None)
    if eff is None:
        return "explicit"
    d = _BY_KEY[key]
    if d.field and _current(obj, d) != plain(eff.values[key]):
        return "explicit"
    return eff.sources[key]


def explicit_model_gaps(models=None, storage=None, *, brief=False) -> list[str]:
    """Settings of the paid stages whose model is only the code default. Objects built by hand (tests, scripts), or
    changed by code after loading, name their models themselves and have no gaps."""
    gaps = []
    if getattr(models, "_effective", None) is not None and not brief:
        if _source_in_use(models, "models.moment_extraction") == "default":
            gaps.append("models.moment_extraction")
        angle = "models.angle_generation" if models.angle_prompt_profile in CARD_PROFILES else None
        if not (angle and _source_in_use(models, angle) != "default") and _source_in_use(models, "models.default") == "default":
            gaps.append("models.default" + (" (or models.angle_generation)" if angle else ""))
    if getattr(storage, "_effective", None) is not None and brief:
        gaps += [k for k in ("models.brief", "models.brief_review") if _source_in_use(storage, k) == "default"]
    return gaps


def explicit_profile_gaps(models=None, storage=None, *, brief=False) -> list[str]:
    """Prompt profiles of the paid stages that are only the code default. The code defaults are the configuration WIA rated
    1 of 5 (plan E.X4: kept so released runs replay and their tests hold), so a live run that has not had the production
    configuration applied must say so instead of quietly running it. Objects built by hand name their profiles in code."""
    gaps = []
    if getattr(models, "_effective", None) is not None and not brief:
        if _source_in_use(models, "prompts.profile.strategist") == "default":
            gaps.append("prompts.profile.strategist")
    if getattr(storage, "_effective", None) is not None and brief:
        gaps += [k for k in ("prompts.profile.brief", "prompts.profile.brief_writer") if _source_in_use(storage, k) == "default"]
    return gaps


def require_explicit_models(models=None, storage=None, *, brief=False) -> None:
    """Live mode refuses to start a paid stage whose model or prompt profile was never chosen (section 4.10, E.X4)."""
    gaps = explicit_model_gaps(models, storage, brief=brief)
    if gaps:
        raise SettingError(
            "Live mode needs the model set explicitly, not left at the code default: " + ", ".join(gaps) +
            ". Set it with `python -m backend_pipeline.storage_cli settings set <key> <model>` (or its environment variable) "
            "after choosing the model.")
    if profiles := explicit_profile_gaps(models, storage, brief=brief):
        raise SettingError(
            "Live mode needs the prompt profile set explicitly: " + ", ".join(profiles) + " is still the code default, the "
            "configuration WIA rated 1 of 5. Apply the production configuration with `python -m backend_pipeline.storage_cli "
            "settings apply --file deploy/production-settings.json --actor <approver email>`, or set the key (a row or its "
            "environment variable) to the profile you mean to run.")


# --------------------------------------------------------------------------------------------------------------
# Command line (storage_cli settings ...)


def add_cli(sub) -> None:
    p = sub.add_parser("settings", help="Behavioural settings stored in the database (plan 0.B8)")
    s = p.add_subparsers(dest="settings_command", required=True)
    s.add_parser("list", help="Every setting with its value, its source (default, env or table) and its default")
    g = s.add_parser("get"); g.add_argument("key")
    st = s.add_parser("set", help="Validate and store one value; the next job or request uses it"); st.add_argument("key")
    st.add_argument("value", help="Text, a number, true/false, a comma list, or JSON (null clears an optional model)")
    st.add_argument("--actor", required=True, help="Who changes it, recorded with the row")
    un = s.add_parser("unset", help="Delete the row: the environment variable (if any) and then the default apply again")
    un.add_argument("key"); un.add_argument("--actor", required=True)
    ap = s.add_parser("apply", help="Store every setting of a configuration file as rows, all or nothing "
                      "(e.g. backend/deploy/production-settings.json)")
    ap.add_argument("--file", required=True); ap.add_argument("--actor", required=True); ap.add_argument("--dry-run", action="store_true")
    ie = s.add_parser("import-env", help="Store the behavioural environment variables of this process as rows")
    ie.add_argument("--actor", required=True); ie.add_argument("--overwrite", action="store_true")


def parse_cli_value(text: str):
    try:
        return json.loads(text)
    except ValueError:
        return text


def run_cli(args, storage) -> dict:
    """Run one `settings` command; a refused key or value ends the command with its message (exit status 1)."""
    try:
        return _run_cli(args, storage)
    except SettingError as error:
        raise SystemExit(f"settings: {error}") from error


def _run_cli(args, storage) -> dict:
    from .database import connect
    with connect(storage.database_url, vectors=False) as conn:
        command = args.settings_command
        if command == "list":
            return {"settings": listing(conn), "problems": load(conn, read_files=False).problems}
        if command == "get":
            definition(args.key)
            return next(r for r in listing(conn) if r["key"] == args.key)
        if command == "set":
            d = _writable(args.key)
            raw = parse_cli_value(args.value)
            if d.type in {"str", "zone", "enum"} and not isinstance(raw, str) and raw is not None:
                raw = args.value
            result = set_value(conn, args.key, raw, args.actor)
        elif command == "unset":
            result = unset_value(conn, args.key, args.actor)
        elif command == "apply":
            result = apply_profile(conn, json.loads(Path(args.file).read_text(encoding="utf-8")), args.actor, dry_run=args.dry_run)
        else:
            result = import_env(conn, args.actor, overwrite=args.overwrite)
        conn.commit()
        return result
