"""Version 4 brief checks (E.B33, E.B34, E.B24's extension).

A v4 brief shares v3's ledger, repair and finalisation (validation_v3.finalize_v3 with contract_for(SCHEMA_V4)) and v2's
checks (the locked angle, the CTA, quoted turns, claims and numbers bound to their evidence, who speaks and who is named,
internal items, clients, the rejection rules, E.B10's narrative checks, E.B24's copy lint). It adds:

- its own format checks (every format in the confirmed channel set, captions on each Instagram asset, slides in order;
  a brief of writer v5.1, NP.B10, has the three Reels: story, stance, b-roll text);
- the first-touch rules (first_touch.py, E.B34): subjects, slide 1, specificity, insider terms, who did what;
- the asset checks (asset_checks.py, E.B24's extension), blocking only where the plan marks it;
- across the cycle's briefs, when they are given (`siblings`): one offer CTA a week on Instagram, covers distinct.

The insider terms and offer descriptors are those the brief pinned when it was written (provenance), so a check re-run at
Gate 2 reads the same data. Attested facts are the ledger's own entries for them (status `attested`, 5.B7).
"""
from __future__ import annotations

from types import SimpleNamespace

from .asset_checks import asset_findings, week_findings
from .contracts import Dossier
from .contracts_v4 import PREMISE_KINDS, THREE_REELS, BriefDocumentV4, copy_fields_v4, reel_shape
from .first_touch import first_touch_findings, insider_terms, offer_descriptors
from .validation_v2 import (_collector, angle_and_cta_checks, before_publishing_checks, email_dm_check, ledger_checks, lint_fields,
                            public_copy_checks)
from .validation_v3 import SETTLED, _snippet, paraphrase_checks


def email_text_v4(plan) -> str:
    e = plan.email
    return " ".join([*e.subject_options, e.preview, e.opening, e.body, e.ending]) if e else ""


def format_checks_v4(add, block, plan, channels: set):
    """Every format in the confirmed channel set and none outside it; captions on the Instagram assets when the caption
    channel is confirmed; slides numbered in order, none repeated."""
    present = {"reel": bool(plan.reels), "carousel": plan.carousel is not None, "email": plan.email is not None,
               "stories": plan.stories is not None,
               "caption": any(r.caption for r in plan.reels) or bool(plan.carousel and plan.carousel.caption)}
    for name, there in present.items():
        if there and name not in channels:
            block(f"The format plan includes {name}, which is outside the confirmed channel set", section="format_plan")
        elif name in channels and not there:
            block(f"The format plan has no {name}, which is in the confirmed channel set", section="format_plan")
    if plan.carousel:
        numbers = [s.number for s in plan.carousel.slides]
        if numbers != list(range(1, len(numbers) + 1)):
            block("Carousel slides must be numbered in order from 1", section="format_plan")
        if len(numbers) > 10:
            add("warning", "More than 10 carousel slides: WIA has approved 11 or 12 only as exceptions", section="format_plan")
        if len({" ".join(s.text.lower().split()) for s in plan.carousel.slides}) != len(numbers):
            block("A carousel slide repeats another slide's text", section="format_plan")


def three_reels_check(add, plan, channels: set, writer: str | None):
    """Writer v5.1 writes three Reels, one of each kind in the pack's order, when the reel channel is confirmed (NP.B10). Its
    answer cannot lack them (BriefWriteV51), so this finds a person's edit at Gate 2 that dropped or reordered one; the pack
    then writes the missing kind. Not a check on a v5 brief, which may have two (D30)."""
    from ..settings_store import PREMISE_WRITERS, THREE_REEL_WRITERS
    if writer in THREE_REEL_WRITERS and "reel" in channels and [r.kind for r in plan.reels] != THREE_REELS:
        add("warning", f"Writer {writer} writes three Reels: the story, the stance and the b-roll text, in that order",
            section="format_plan")
    # Writer v5.3 (Round 2): the central story and two premises of their own, each Reel's copy fitting its production.
    if writer in PREMISE_WRITERS and "reel" in channels:
        if [r.kind for r in plan.reels] != list(PREMISE_KINDS):
            add("warning", f"Writer {writer} writes three Reels: the central story, then two premises of their own, in that "
                           "order", section="format_plan")
        for n, r in enumerate(plan.reels, 1):
            if getattr(r, "production", None) is None:
                continue
            try:
                reel_shape(r)
            except ValueError as exc:
                add("warning", f"Reel {n}: {exc}", section="format_plan")


def attested_entries(body) -> list[dict]:
    """The ledger's entries for the attested facts and paraphrases given at the gates (5.B7)."""
    claims = body["claims"] if isinstance(body, dict) else [c.model_dump(mode="json") for c in body.claims]
    return [c for c in claims if c.get("status") == "attested" and c.get("field") == "context_items"]


def checks_v4(document: dict, dossier, provenance: dict, clearances=None, rules=None, siblings=None) -> list[dict]:
    findings = []
    add, block = _collector(findings)
    doc = BriefDocumentV4.model_validate(document)
    d = Dossier.model_validate(dossier) if isinstance(dossier, dict) else dossier
    body, header = doc.body, doc.header
    angle_and_cta_checks(add, block, body, header, d.angle)

    # The ledger, as v3's (validation_v3.checks_v3): settled claims face v2's claim checks; the rest are findings.
    copy = copy_fields_v4(body, wide=True)
    narrative = "\n".join(text for _, _, text in copy)
    labels = {field: label for field, label, _ in copy}
    for claim in body.claims:
        label = labels.get(claim.field, claim.field)
        section = claim.field.split(".")[0]
        if claim.status not in SETTLED:
            narrative = narrative.replace(claim.text, " ")
        if claim.status == "unsupported":
            block(f'{label[0].upper() + label[1:]} says "{_snippet(claim.text)}": {claim.note or "the call does not support it"}. '
                  "Remove it, or say only what the call supports", claim.claim_id, section=section)
        elif claim.status == "unchecked":
            add("warning", f'Check against the call: {label} says "{_snippet(claim.text)}" ({claim.note or "not checked"})',
                claim.claim_id, section=section)
        elif claim.status == "kept_by_person":
            add("warning", f'{label[0].upper() + label[1:]} keeps "{_snippet(claim.text)}", which the verifier found no '
                           "support for; a person kept it", claim.claim_id, section=section)
        if claim.flag and claim.status in SETTLED:
            if claim.flag.kind == "consent" and claim.flag.severity == "block":
                cited = [e for e in d.evidence if e.evidence_id in claim.evidence_ids]
                if not any(e.public_use and e.attribution_verified or (clearances or {}).get(e.evidence_id) for e in cited):
                    block(f'{claim.flag.message} ("{_snippet(claim.text, 80)}"); record the client\'s permission as a '
                          "clearance on its evidence", claim.claim_id, section="claims")
            else:
                add("warning", f'{claim.flag.message} ("{_snippet(claim.text, 80)}")', claim.claim_id, section=section)
    paraphrase_checks(block, copy, body.claims, d.evidence)
    settled = SimpleNamespace(evidence=body.evidence, claims=[c for c in body.claims if c.status in SETTLED])
    ledger_checks(add, block, settled, d, provenance, clearances, narrative)

    plan = body.format_plan
    channels = set(header.channels)
    format_checks_v4(add, block, plan, channels)
    three_reels_check(add, plan, channels, provenance.get("writer"))
    email = email_text_v4(plan)
    email_dm_check(block, email)
    public_copy_checks(findings, body, header, d, provenance, clearances, rules, public="\n".join(text for _, _, text in copy),
                       copy=copy, lint=lint_fields(copy_fields_v4(body)), email_text=email)
    before_publishing_checks(block, body)

    # E.B34 and E.B24's extension, on the body as data.
    value = body.model_dump(mode="json")
    evidence = [e.model_dump(mode="json") for e in d.evidence]
    roster = provenance.get("roster") or []
    attested = attested_entries(value)
    findings += first_touch_findings(value, terms=insider_terms(provenance), attested=attested, evidence=evidence, roster=roster)
    findings += asset_findings(value, pillar=header.purpose, channels=channels, evidence=evidence, roster=roster, attested=attested,
                               offers=offer_descriptors(provenance))
    if siblings:
        findings += week_findings(value, siblings)
    return findings

