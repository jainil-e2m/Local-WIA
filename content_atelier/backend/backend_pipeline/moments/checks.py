"""Deterministic checks on a moment (plan 2.B4): pure functions, no database and no model.

Three rules decide what a stored moment may be used for, whatever extractor produced it:

* **Role plausibility.** A `result` or a `testimonial` is the client's to claim (`types.CLIENT_CLAIM_TYPES`). Spoken by anyone
  other than a client or prospect (`types.CLIENT_VOICES`), the line is a staff member relaying it, so its `evidence_kind` is
  `team_report`. A `testimonial` spoken by anyone but a client or prospect is retagged `observation` (a staff praise line is
  never a testimonial); the model's own tag stays in the moment body and in `checks.role_plausibility.original_type`, and the
  stored type is re-derived from it, so a later re-normalisation that places the speaker restores the tag. A speaker the
  roster cannot place (`unknown`) is treated the same way: conservatively, as a relay.
* **Numbers.** Every figure the stored quote, setup or record states must appear in the anchor passages' text, compared by
  digits with the same normalisation the card verification uses (`cycle/verification.py`). A figure that is absent fails the
  check (`checks.numbers.passed = false`, the figure listed); the moment stays stored and downstream consumers read the
  result. A figure found only in the surrounding context passages is listed as `context_only`, which also fails: the scene
  record should repeat only what the anchor line says (the v2 prompt says so). Spelled-out counts ("three") are not
  figures here, as in the card check.
* **Consent.** `do_not_use` if the client's consent is `no_use`; else `internal_only` if the sensitivity is `internal_only`;
  else `cleared` only if the client allows naming (`may_name`), the sensitivity is `public_candidate` and the evidence is a
  `direct_quote`; else `anonymise`. Migration 008 states the same rule in SQL for the moments it promotes, and a test keeps
  the two in agreement. The browser never decides it.

`assess` applies all three to one moment and returns the derived columns plus the `checks` document stored beside them.
"""
from __future__ import annotations

import re

from ..cycle import verification
from . import types

CHECKS_VERSION = "moment-checks.v1"
# The record's own labels, not statements of fact: "Process step: Audit, step 12" must not count as a stated figure.
NOT_A_CLAIM = re.compile(r"(?:^|\s\|\s)Process step:[^|]*")


def role_plausibility(original_type: str | None, speaker_role: str | None) -> dict:
    """The stored type and evidence kind for a moment of the given (model-tagged) type spoken by the given role."""
    role = speaker_role or "unknown"
    base = {"speaker_role": role, "original_type": original_type}
    if original_type in types.CLIENT_CLAIM_TYPES and role not in types.CLIENT_VOICES:
        stored = "observation" if original_type == "testimonial" else original_type
        why = ("the roster cannot place the speaker, so the line is treated as a relay" if role == "unknown"
               else f"spoken by {role}, not by a client or prospect")
        return {**base, "passed": False, "moment_type": stored, "evidence_kind": "team_report",
                "reason": f"A {original_type} is the client's to claim; {why}"
                          + ("; retagged observation" if stored != original_type else "")}
    return {**base, "passed": True, "moment_type": original_type, "evidence_kind": "direct_quote"}


def number_check(fields: dict[str, str], anchor_texts: list[str], context_texts: list[str] = ()) -> dict:
    """Every figure the fields state, against the anchor passages' figures (context passages reported separately)."""
    anchor, context = verification.digits_in(anchor_texts), verification.digits_in(context_texts)
    figures, seen = [], set()
    for field, text in fields.items():
        for shown, digits in verification.figures_in(NOT_A_CLAIM.sub(" ", text or "")):
            if (field, digits) in seen:
                continue
            seen.add((field, digits))
            where = "anchor" if digits in anchor else "context" if digits in context else "absent"
            figures.append({"field": field, "figure": shown, "digits": digits, "found_in": where})
    absent = [f["figure"] for f in figures if f["found_in"] == "absent"]
    context_only = [f["figure"] for f in figures if f["found_in"] == "context"]
    return {"passed": not absent and not context_only, "figures": figures, "absent": absent, "context_only": context_only}


def consent_status(client_consent: str | None, sensitivity: str | None, evidence_kind: str | None) -> str:
    """What may be said in public about a moment. `client_consent` is clients.consent, None when no client is known."""
    if client_consent == "no_use":
        return "do_not_use"
    if sensitivity == "internal_only":
        return "internal_only"
    if client_consent == "may_name" and sensitivity == "public_candidate" and evidence_kind == "direct_quote":
        return "cleared"
    return "anonymise"


def consent_record(client_consent, sensitivity, evidence_kind) -> dict:
    status = consent_status(client_consent, sensitivity, evidence_kind)
    return {"status": status, "client_consent": client_consent, "sensitivity": sensitivity, "evidence_kind": evidence_kind}


def assess(*, original_type: str | None, speaker_role: str | None, sensitivity: str | None, client_consent: str | None,
           fields: dict[str, str], anchor_texts: list[str], context_texts: list[str] = ()) -> dict:
    """The derived columns and the checks document for one verified moment."""
    role = role_plausibility(original_type, speaker_role)
    numbers = number_check(fields, anchor_texts, context_texts)
    consent = consent_record(client_consent, sensitivity, role["evidence_kind"])
    return {"moment_type": role["moment_type"], "evidence_kind": role["evidence_kind"], "consent_status": consent["status"],
            "checks": {"version": CHECKS_VERSION, "role_plausibility": role, "numbers": numbers, "consent": consent}}


def assess_unverified(*, original_type: str | None, sensitivity: str | None, client_consent: str | None) -> dict:
    """An unverified record has no anchor passages, so only its consent is derived. It is never proof."""
    consent = consent_record(client_consent, sensitivity, "direct_quote")
    return {"moment_type": original_type, "evidence_kind": "direct_quote", "consent_status": consent["status"],
            "checks": {"version": CHECKS_VERSION, "consent": consent}}


def fallback_role(label: str | None, roster: list[dict] | None) -> str:
    """The role of a speaker whose document has no speaker map yet: staff when the roster knows the name (the card
    verification's lookup), otherwise unknown. Never client: without the document's call type that would be a guess."""
    entry = verification.speaker_entry(label, roster or [])
    if entry and entry.get("status") in ("current", "former"):
        return "staff"
    return "unknown"


def speaker_of(document: dict, passage: dict | None, roster: list[dict] | None = None) -> dict:
    """Who said a passage: the label as the transcript writes it, and the person and role the document's speaker map gives it."""
    label = (passage or {}).get("speaker")
    mapped = (document.get("speaker_map") or {}).get(label or "")
    if mapped:
        return {"label": label, "person_id": mapped.get("person_id"), "role": mapped.get("role") or "unknown"}
    return {"label": label, "person_id": None, "role": fallback_role(label, roster) if label else "unknown"}
