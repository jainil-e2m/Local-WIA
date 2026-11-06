"""The vocabularies of the moments ledger (plan 2.B1, 2.B3, 2.B4): one place, so extraction, checks, search and the API agree.

Moment types are tags for filtering and for a brief's proof sections, not a gate (R43). The first seven are the types every
earlier extraction profile (the weekly v3 contract and scene profile v1) can emit; their schemas are not changed, because
a changed schema changes the request fingerprint of every saved response. The scene profile v2 may emit all twelve.
"""
from __future__ import annotations

LEGACY_MOMENT_TYPES = ("result", "objection", "decision", "tension", "mechanism", "observation", "story")
ADDED_MOMENT_TYPES = ("testimonial", "question", "teaching", "soundbite", "data_point")
MOMENT_TYPES = LEGACY_MOMENT_TYPES + ADDED_MOMENT_TYPES
# Scene profile v3 (E.B31): a verbatim human line (a feeling, a self-description, a business confession) and a WIA decision
# that went against the default or cost WIA something. The strategist packet lists them first.
SCENE_V3_TYPES = ("human_line", "counter_expected_decision")
V3_MOMENT_TYPES = MOMENT_TYPES + SCENE_V3_TYPES
# Scene profile v4 (1.B13's extension, D24): in an internal meeting, a team member describing or deciding how WIA works.
SCENE_V4_TYPES = ("team_practice",)
V4_MOMENT_TYPES = V3_MOMENT_TYPES + SCENE_V4_TYPES
# Every type a stored moment can carry: what search and the ledger filter on.
LEDGER_MOMENT_TYPES = V4_MOMENT_TYPES

# Who spoke the anchor line. These are the roles of `people` (1.B2) plus `unknown` for a speaker the roster cannot place.
SPEAKER_ROLES = ("staff", "client", "prospect", "vendor", "outside", "ai_agent", "unknown")
# The roles whose words count as a client's own (a testimonial or a result needs one of these to be a direct quote).
CLIENT_VOICES = frozenset({"client", "prospect"})

# direct_quote: said by the person it is credited to. team_report: a staff member relaying a result or praise.
# screenshot_text: text read from an image or pasted in (2.B13, deferred).
EVIDENCE_KINDS = ("direct_quote", "team_report", "screenshot_text")
# Types whose truth depends on who says them: a testimonial or a result is the client's to claim.
CLIENT_CLAIM_TYPES = frozenset({"result", "testimonial"})

# cleared: the client allows named use. anonymise: the default. internal_only. do_not_use.
CONSENT_STATUSES = ("cleared", "anonymise", "internal_only", "do_not_use")
SENSITIVITIES = ("public_candidate", "internal_only", "unknown")
DESTINATIONS = ("public_opportunity", "internal_intelligence", "research_needed")

SCENE_V1_PROFILE = "2026-10-18.scenes.v1"
SCENE_V2_PROFILE = "2026-10-19.scenes.v2"
SCENE_V3_PROFILE = "2026-10-23.scenes.v3"
SCENE_V4_PROFILE = "2026-10-25.scenes.v4"
