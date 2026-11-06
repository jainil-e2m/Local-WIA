"""Version 2 brief validators and finalisation (E.B15 b, f, g).

Deterministic checks on the v2 ledger: the approved angle is locked, the CTA is a person's, every quote and number is
bound to its evidence, general-approach claims cite a knowledge-base document, formats stay in the confirmed channel
set, "I" is used only for Whitney's own scene, private speakers stay out of the public narrative (WIA staff may be
credited), the knowledge base's rejection rules apply to public copy, and E.B10's checks run on the narrative.
E.B10's ledger builder replaces the version 1 model review (g).

A finding with gate=True is resolved by a person at Gate 2 (the CTA, before-publishing answers), not by repair.

Contract v2 is superseded by contract v3 for new briefs (`deploy/production-settings.json`: prompts.profile.brief =
brief_document_v3 with writer v4, E.B23). v2 stays for the rows written with it and their revisions; it has no reviewer
from a different model family (standard 2.4a (b), (c), (f)), and every v2 check run says so as a warning rather than
building one for a superseded contract (E.B15 g). Most checks below are shared with v3 (validation_v3).
"""
from __future__ import annotations

import copy
import re
from datetime import UTC, datetime

from ..repository import insert
from ..store import canonical_hash
from .contracts import Dossier
from .contracts_v2 import SCHEMA_V2, BriefBodyV2, BriefDocumentV2, writer_schema_v2
from .handoff import parent_anchor
from .inputs import assert_packet, verify_evidence
from .validation import hash_brief, numbers

PUBLIC_SECTIONS = ("wia_perspective", "supporting_example", "narrative_outline", "format_plan", "cta_why")


def _norm(text):
    return re.sub(r"\s+", " ", (text or "").replace("’", "'")).strip().lower()


# Words of a meeting label that name no one: articles, and the device or room a call joined from.
NOT_A_NAME = {"the", "a", "an", "and", "of", "our", "my", "iphone", "ipad", "android", "phone", "galaxy", "pixel", "zoom",
              "room", "meeting", "macbook", "laptop", "pc", "desktop", "user", "guest", "photo", "video", "+", "&"}


def outside_name(label: str) -> str | None:
    """The word a speaker's label names them by in copy: its first word that is a name, without a possessive.

    N2, 23 October: the label "The Organic Moment Photo + Video" was searched for as "The", which every brief contains
    (eight false blocks), and "Steve’s iPhone" as "Steve’s", which copy naming "Steve" never matched."""
    for word in re.findall(r"[^\W\d_][\w'’-]*", label or ""):
        word = re.sub(r"['’]s$", "", word)
        if word.lower() not in NOT_A_NAME and len(word) >= 2:
            return word
    return None


def _public_text(body: dict) -> str:
    parts = []

    def walk(value):
        if isinstance(value, str):
            parts.append(value)
        elif isinstance(value, dict):
            for k, v in value.items():
                if k != "evidence_ids":
                    walk(v)
        elif isinstance(value, list):
            for v in value:
                walk(v)
    for section in PUBLIC_SECTIONS:
        walk(body.get(section))
    return "\n".join(parts)


def copy_fields(body: BriefBodyV2, *, wide: bool = False) -> list[tuple[str, str, str]]:
    """The reader-facing copy in a v2 brief as (field, label for the reviewer, text). `wide` adds the outline and the Reel
    beats and Stories frames, which become copy too; jobs and the CTA rationale are directions for the writer."""
    out = [("wia_perspective", "the WIA perspective", body.wia_perspective)]
    ex = body.supporting_example
    out += [(f"supporting_example.{k}", "the supporting example", getattr(ex, k)) for k in ("scene", "wia_move", "client_contribution")]
    out += [(f"narrative_outline.hooks[{i}]", f"hook {i}", h.text) for i, h in enumerate(body.narrative_outline.hooks, 1)]
    outline = body.narrative_outline
    if wide:
        out += [("narrative_outline.problems_desires_symptoms", "the problems and desires", " ".join(outline.problems_desires_symptoms)),
                ("narrative_outline.main_point", "the main point", outline.main_point),
                ("narrative_outline.transformation", "the transformation", outline.transformation),
                ("narrative_outline.cta", "the outline's CTA", outline.cta)]
    plan = body.format_plan
    for i, r in enumerate(plan.reels, 1):
        out += [(f"format_plan.reels[{i}].cover_text", f"Reel {i}'s cover text", r.cover_text),
                (f"format_plan.reels[{i}].spoken_opening", f"Reel {i}'s spoken opening", r.spoken_opening)]
        if wide:
            out += [(f"format_plan.reels[{i}].beats", f"Reel {i}'s beats", " ".join(r.beats))]
    if plan.carousel:
        out += [(f"format_plan.carousel.slides[{s.number}].text", f"carousel slide {s.number}", s.text) for s in plan.carousel.slides]
    if plan.email:
        e = plan.email
        out += [("format_plan.email.subject_options", "the email's subject lines", " | ".join(e.subject_options))]
        out += [(f"format_plan.email.{k}", f"the email's {k}", getattr(e, k)) for k in ("preview", "opening", "argument", "transformation", "ending")]
    if plan.caption:
        out += [(f"format_plan.caption.{k}", f"the caption's {k}", getattr(plan.caption, k)) for k in ("hook", "adds", "ending")]
    if plan.stories and wide:
        out += [("format_plan.stories.frames", "the Stories frames", " ".join(plan.stories.frames))]
    return out


# 2.4a (g): checking language belongs under Before publishing, not in the copy (the live week's briefs, 18 October).
CHECKING_LANGUAGE = re.compile("|".join([
    r"\bnot independently verified\b", r"\bsubject to (?:public[- ]use )?permission\b", r"\bafter permission is confirmed\b",
    r"\bpending permission\b", r"\bpublic[- ]use permission\b",
    r"\b(?:the )?(?:evidence|excerpts?|record|call|transcript)s? (?:does|do) not (?:show|establish)\b", r"\b(?:does|do|did) not establish\b",
    r"\bremains? (?:an idea|a proposal|an open question|unverified)\b", r"\bestablished as implemented\b",
    r"\bnot (?:\w+ ){0,3}(?:documented|implemented)\b", r"\bevidence of implementation\b", r"\bnot (?:a |an )?claimed\b",
    r"\bhistorical (?:call|conversation|proposal|recommendations?|remarks|team discussion)\b",
    r"\bsupplied (?:excerpts?|passages?|evidence|records?)\b", r"\bcited (?:excerpts?|scenes?|evidence)\b"]), re.I)
# A sentence that tells a writer what to do: verbs that never address the reader, or a direction about the piece itself.
INSTRUCTION = re.compile(r"^(?:then\s+)?(?:explain|describe|introduce|credit|omit|preserve|develop (?:a|an|the)\b|"
                         r"do not (?:imply|present|claim|name|retell|include|describe))\b", re.I)
DIRECTING = re.compile(r"^(?:then\s+)?(?:keep|use|begin|start|open|close|end|finish|help|connect|show|make|sign off|add|respect|establish)\b", re.I)
ABOUT_THE_PIECE = re.compile(r"\b(?:the (?:reader|owner|caption|reel|email|carousel|copy|scene|piece)|this (?:scene|piece|caption|email|reel)|"
                             r"savannah's framework|flowing paragraphs|permission|sibling|sign off as|wia's belief|the principle|"
                             r"anonymous|attribution|offer ask)\b", re.I)


def copy_lint(body: BriefBodyV2) -> list[dict]:
    """Warnings, each naming its field: checking language in the copy, and writing instructions in place of copy."""
    return lint_fields(copy_fields(body))


def lint_fields(fields: list[tuple[str, str, str]]) -> list[dict]:
    """E.B24's copy lint over (field, label, text) copy fields of any contract version."""
    findings = []
    for field, label, text in fields:
        if m := CHECKING_LANGUAGE.search(text or ""):
            findings.append({"severity": "warning", "claim_id": None, "gate": False, "section": field.split(".")[0], "field": field,
                             "message": f'{label[0].upper() + label[1:]} carries checking language ("{m.group(0)}"): keep limits '
                                        "like this under Before publishing, and let the copy simply not claim it"})
        for sentence in re.split(r"(?<=[.!?:])\s+|\n+", text or ""):
            sentence = sentence.strip()
            if INSTRUCTION.match(sentence) or DIRECTING.match(sentence) and ABOUT_THE_PIECE.search(sentence):
                snippet = sentence if len(sentence) <= 80 else sentence[:77].rstrip() + "..."
                findings.append({"severity": "warning", "claim_id": None, "gate": False, "section": field.split(".")[0], "field": field,
                                 "message": f'{label[0].upper() + label[1:]} holds a writing instruction ("{snippet}") instead of the copy itself'})
                break
    return findings


def approved_text(angle: dict) -> tuple[str, str]:
    card = (angle.get("body") or {}).get("card")
    if card:
        from ..card_contracts import card_point
        # A strategist v7 card's point is `point` (E.B30); earlier cards' is core_perspective.
        return card["title"], card_point(card)
    return angle["body"]["title"], angle["body"]["argument"]


def person_cta(angle: dict) -> dict | None:
    """The CTA a person chose at Gate 1, as a v2 CTA; None when the card deferred it to development."""
    cta = angle.get("cta") or {}
    if cta.get("text"):
        card = (angle.get("body") or {}).get("card") or {}
        return {"choice": "explicit", "track": None, "action": cta["text"], "offer_connection": card.get("offer_connection"),
                "chosen_by": "person"}
    return None


def _collector(findings):
    def add(severity, message, claim_id=None, *, gate=False, section=None):
        findings.append({"severity": severity, "claim_id": claim_id, "message": message, "gate": gate, "section": section})

    def block(message, claim_id=None, **kw):
        add("blocking", message, claim_id, **kw)
    return add, block


def checks_v2(document: dict, dossier, provenance: dict, clearances=None, rules=None) -> list[dict]:
    findings = []
    add, block = _collector(findings)
    doc = BriefDocumentV2.model_validate(document)
    d = Dossier.model_validate(dossier) if isinstance(dossier, dict) else dossier
    body, header = doc.body, doc.header
    evidence = {e.evidence_id: e for e in d.evidence}
    angle_and_cta_checks(add, block, body, header, d.angle)
    public = _public_text(body.model_dump())
    ledger_checks(add, block, body, d, provenance, clearances, public)
    plan = body.format_plan
    format_checks(add, block, plan, set(header.channels))
    email_only = " ".join([*plan.email.subject_options, plan.email.preview, plan.email.opening, plan.email.argument,
                           plan.email.transformation, plan.email.ending]) if plan.email else ""
    email_dm_check(block, email_only)
    used = {i for r in plan.reels for i in r.evidence_ids} | ({i for s in plan.carousel.slides for i in s.evidence_ids} if plan.carousel else set())
    used |= set(plan.email.evidence_ids) if plan.email else set()
    if not used <= set(evidence):
        block("A format cites evidence that is not in the dossier", section="format_plan")
    copy = copy_fields(body, wide=True)
    copy_quote_checks(add, block, copy, d, clearances)
    public_copy_checks(findings, body, header, d, provenance, clearances, rules, public=public,
                       copy=copy, lint=copy_lint(body), email_text=email_only)
    before_publishing_checks(block, body)
    # Standard 2.4a (b), (c) and (f) are a different-family reviewer's findings. Contract v3 runs one (its ledger's
    # verifier); v2 is superseded by v3 for new briefs and gets none, so the reviewer is told (E.B15 g).
    add("warning", NO_REVIEWER_V2, section="review")
    return findings


NO_REVIEWER_V2 = ("No reviewer from a different model family has read this v2 brief, so standard 2.4a (b) WIA perspective "
                  "first, (c) one complete argument and (f) credit and grounding have no findings: read for them yourself. "
                  "New briefs use contract v3, whose ledger runs that reviewer")


def copy_quote_checks(add, block, fields: list[tuple[str, str, str]], d, clearances):
    """Condition 4 inside the copy (v2): words in quotation marks are the words of a turn of the call, and a quoted turn
    is public only with its source-use and attribution clearance (condition 7), as v3's ledger binds them. Without a
    verifier, quotation marks around words no turn says may be an invented quote or a phrase nobody is said to have said:
    a person decides (a warning, as v3's unchecked lines)."""
    from ..cycle.verification import normalise, quotes_in
    for field, label, text in fields:
        for quoted in dict.fromkeys(quotes_in(text or "")):
            said = normalise(quoted)
            turns = [e for e in d.evidence if said and said in normalise(e.excerpt)]
            snippet = quoted if len(quoted) <= 80 else quoted[:77].rstrip() + "..."
            where = label[0].upper() + label[1:]
            section = field.split(".")[0]
            if not turns:
                add("warning", f'{where} puts "{snippet}" in quotation marks, but no turn of the call says it: quote the call '
                               "exactly, or drop the quotation marks", section=section)
            elif not any(e.public_use and e.attribution_verified and e.sensitivity != "internal_only"
                         or (clearances or {}).get(e.evidence_id) for e in turns):
                block(f'{where} quotes "{snippet}" from the call: a public quotation needs source-use and attribution clearance',
                      section=section)


def angle_and_cta_checks(add, block, body, header, angle):
    """The approved angle is locked and the CTA is a person's (contracts v2 and v3)."""
    # The approved angle is locked; a sharper point goes beside it, shown as a diff (2.4a a).
    title, perspective = approved_text(angle)
    if (body.approved_angle.title, body.approved_angle.core_perspective) != (title, perspective):
        block("The approved title or core perspective changed; put a sharper version in sharpened_point", section="approved_angle")
    if header.angle_id != angle["angle_id"] or header.angle_hash != angle["approved_hash"]:
        block("The brief header does not match the approved angle")

    # CTA: a person's choice, or "no explicit ask" confirmed by a person (R46).
    chosen = person_cta(angle)
    if chosen and (header.cta.choice != "explicit" or header.cta.action != chosen["action"]):
        block("The CTA differs from the one a person chose at Gate 1", section="cta")
    if header.cta.chosen_by != "person" or header.cta.choice == "decide_in_development":
        block("The CTA is the writer's proposal; a person confirms it (or no explicit ask) at Gate 2", gate=True, section="cta")
    if re.search(r"\$\s?\d", " ".join(filter(None, [header.cta.action, body.cta_why]))):
        block("A CTA never states a price", section="cta")


def ledger_checks(add, block, body, d, provenance: dict, clearances, narrative: str):
    """Quoted turns, claims and numbers bound to their evidence (contracts v2 and v3). A number in `narrative` needs a
    source-bound claim."""
    evidence = {e.evidence_id: e for e in d.evidence}
    kb_keys = set(provenance.get("knowledge_base_keys") or [])
    # Quoted turns resolve in their evidence, with the same speaker and time.
    for ref in body.evidence:
        e = evidence.get(ref.evidence_id)
        if not e:
            block(f"Evidence {ref.evidence_id} is not in the dossier", section="evidence")
        elif _norm(ref.quote) not in _norm(e.excerpt):
            block(f"The quote for {ref.evidence_id} does not match the original wording", section="evidence")
        elif (ref.speaker or e.speaker) and _norm(ref.speaker) != _norm(e.speaker) or ref.start_ms != e.start_ms:
            block(f"The speaker or time for {ref.evidence_id} differs from the source", section="evidence")

    identifiers = {*evidence, *(c.claim_id for c in body.claims), *(p.angle_id for p in d.prior)}
    if len({c.claim_id for c in body.claims}) != len(body.claims):
        block("Claim identifiers are duplicated", section="claims")
    for claim in body.claims:
        cited = [evidence[i] for i in claim.evidence_ids if i in evidence]
        if len(cited) != len(claim.evidence_ids):
            block("Claim cites unknown evidence", claim.claim_id, section="claims")
        # Attributed experience (v3, E.B26) is a team member's own observation on the call: it cites that turn.
        if claim.claim_class in ("particular_interaction", "outcome", "prevalence", "attributed_experience") and not cited:
            block(f"A {claim.claim_class.replace('_', ' ')} claim needs evidence from the call", claim.claim_id, section="claims")
        # Condition 6: external research may frame a point, never prove what WIA or a client did or achieved.
        if claim.claim_class in ("particular_interaction", "outcome") and any(e.role == "external_framing" for e in cited):
            block("External framing cannot prove a WIA or client result; cite the call", claim.claim_id, section="claims")
        if claim.claim_class == "general_approach" and not cited and claim.knowledge_base_document not in kb_keys:
            block("A general-approach claim cites the knowledge-base document that states it", claim.claim_id, section="claims")
        # Condition 3: a recommendation cites the turn where WIA made it or the document that states it. A v3 ledger claim
        # the verifier flagged instead is already a finding for a person (validation_v3).
        if claim.claim_class == "recommendation" and not cited and claim.knowledge_base_document not in kb_keys \
                and not getattr(claim, "flag", None):
            block("A recommendation claim cites the call's turn where WIA made it, or the knowledge-base document that states it",
                  claim.claim_id, section="claims")
        if claim.claim_class == "prevalence" and cited:
            add("warning", "A prevalence claim generalises from the call; check it is stated as WIA's view", claim.claim_id)
        if numbers(claim.text, identifiers) and not claim.numeric_facts:
            block("A claim with a number needs its structured numeric fact", claim.claim_id, section="claims")
        for fact in claim.numeric_facts:
            e = evidence.get(fact.evidence_id)
            if not e or fact.evidence_id not in claim.evidence_ids or _norm(fact.source_quote) not in _norm(e.excerpt):
                block("A numeric fact is not bound to its cited source", claim.claim_id, section="claims")
            # The value itself must be the one the quote states (condition 5), or a real quote can carry any figure.
            value, quoted = (set(re.findall(r"\d+(?:\.\d+)?", s.replace(",", ""))) for s in (fact.value, fact.source_quote))
            if not value <= quoted or not value and _norm(fact.value) not in _norm(fact.source_quote):
                block("A numeric fact's value does not appear in its source quote", claim.claim_id, section="claims")
        if claim.quote and not any(_norm(claim.quote) in _norm(e.excerpt) for e in cited):
            block("A quotation does not match the original wording", claim.claim_id, section="claims")
        if claim.public_quote and not any(claim.quote and _norm(claim.quote) in _norm(e.excerpt) and
                                          (e.public_use and e.attribution_verified and e.sensitivity != "internal_only"
                                           or (clearances or {}).get(e.evidence_id)) for e in cited):
            block("A public quotation needs source-use and attribution clearance", claim.claim_id, section="claims")

    supported = {n for c in body.claims for f in c.numeric_facts for n in re.findall(r"\d+(?:\.\d+)?", f.value)}
    if numbers(narrative, identifiers) - supported:
        block("A number in the public narrative needs a source-bound claim", section="narrative")


def format_checks(add, block, plan, channels: set):
    """Every format in the confirmed channel set and none outside it, each structured per the format guide (v2 and v3)."""
    # Formats: only the confirmed channel set, each structured per the format guide.
    present = {"reel": bool(plan.reels), "carousel": plan.carousel is not None, "email": plan.email is not None,
               "caption": plan.caption is not None, "stories": plan.stories is not None}
    for name, there in present.items():
        if there and name not in channels:
            block(f"The format plan includes {name}, which is outside the confirmed channel set", section="format_plan")
        elif name in channels and not there:
            # 2.4a (d): every format in the confirmed channel set is planned (the schema lets the writer return null).
            block(f"The format plan has no {name}, which is in the confirmed channel set", section="format_plan")
    if len({r.job for r in plan.reels}) != len(plan.reels) or len({_norm(r.spoken_opening) for r in plan.reels}) != len(plan.reels):
        block("Each Reel needs its own job and spoken opening", section="format_plan")
    if plan.carousel:
        slides = [s.number for s in plan.carousel.slides]
        if slides != list(range(1, len(slides) + 1)):
            block("Carousel slides must be numbered in order from 1", section="format_plan")
        if len(slides) > 10:
            add("warning", "More than 10 carousel slides: WIA has approved 11 or 12 only as exceptions")
        if len({_norm(s.text) for s in plan.carousel.slides}) != len(slides):
            block("A carousel slide repeats another slide's text", section="format_plan")
    if plan.caption and any(_norm(plan.caption.hook) == _norm(r.spoken_opening) for r in plan.reels):
        block("The caption's hook repeats the Reel's spoken opening", section="format_plan")


def email_dm_check(block, email_text: str):
    if re.search(r"\b(?:DMs?|DM['’]?d|DMing|direct\s+message)\b", email_text, re.I):
        block("An email asks for a reply, never a DM", section="format_plan")


def public_copy_checks(findings, body, header, d, provenance: dict, clearances, rules, *, public: str, copy: list, lint: list,
                       email_text: str, identity_checks: bool = True):
    """Who speaks and who is named, E.B24's copy lint, internal items, clients, the rejection rules and E.B10's checks on
    the narrative (contracts v2 and v3). `copy` is the reader-facing fields, `lint` their copy-lint findings. A pack runs
    the identity checks itself, on its own copy and undiscounted (`identity_checks=False`; packs.checks.identity_findings)."""
    add, block = _collector(findings)
    evidence = {e.evidence_id: e for e in d.evidence}
    roster = provenance.get("roster") or []
    # Who speaks: "we" for WIA; "I" only for Whitney's own scene.
    whitney = next((r for r in roster if r["name"].startswith("Whitney")), None)
    cited_speakers = {_norm(evidence[i].speaker) for c in body.claims for i in c.evidence_ids if i in evidence and evidence[i].speaker}
    if body.point_of_view == "I" and not (whitney and cited_speakers & {_norm(a) for a in whitney["aliases"]}):
        block('"I" is only for Whitney\'s own experience; this scene is not hers', section="point_of_view")

    # 2.4a (h), ruled for v2 public copy under D12 (19 October): the stricter brief standard wins over RR-27's "never as
    # current". A former team member is never named in reader-facing copy (credit "our team"); the claims and evidence
    # may still name them.
    for person in (r for r in roster if r["status"] == "former"):
        where = [label for _, label, text in copy
                 if any(len(a) >= 3 and re.search(r"(?<!\w)" + re.escape(a) + r"(?!\w)", text or "") for a in person["aliases"])]
        if where:
            places = ", ".join(dict.fromkeys(where[:4])) + (" and more" if len(set(where)) > 4 else "")
            block(f'{person["name"]} has left WIA and is named in {places}; credit "our team" in public copy', section="narrative")
    findings.extend(lint)

    # Private speakers stay out of the public narrative; WIA staff may be credited (f).
    staff = {_norm(a) for r in roster if r["status"] in ("current", "former") for a in r["aliases"]}
    named = set()
    for e in d.evidence:
        name = (e.speaker or "").strip()
        word = outside_name(name)
        if word and word not in named and _norm(name) not in staff and not any(_norm(name).startswith(s + " ") for s in staff) \
                and not (e.public_use and e.attribution_verified or (clearances or {}).get(e.evidence_id)) \
                and re.search(r"\b" + re.escape(word) + r"\b", public):
            named.add(word)
            block(f"{word} (not WIA staff) is named in the public narrative without clearance", section="narrative")

    # Internal items never reach public copy: an internal price or a private figure blocks (L.B5, rulings 2.2).
    # Checked over everything public in the brief: the locked angle, the sharpened point, the narrative, the claims and
    # the CTA (L.B5, rulings 2.2), matched as whole figures.
    from ..knowledge.items import contains_term
    surface = " ".join(filter(None, [public, body.approved_angle.title, body.approved_angle.core_perspective,
                                     _public_text(body.sharpened_point.model_dump()) if body.sharpened_point else "",
                                     " ".join(c.text for c in body.claims if getattr(c, "text", None)),
                                     header.cta.action or "", body.cta_why]))
    for term in provenance.get("internal_terms") or []:
        if contains_term(surface, term["term"]):
            block(f'The public copy states "{term["term"]}", which WIA keeps internal', section="narrative")

    # Clients on the reviewed list (condition 7, 2.4a h): named in public copy only with consent to be named, or an
    # approver's clearance on that client's own evidence; a client marked no_use is never named. Speaker labels are
    # checked above; this catches a business named in the text.
    named_surface = " ".join(filter(None, [public, body.approved_angle.title, body.approved_angle.core_perspective,
                                           _public_text(body.sharpened_point.model_dump()) if body.sharpened_point else "",
                                           header.cta.action or "", body.cta_why]))
    for client in provenance.get("clients") or []:
        if client.get("consent") == "may_name":
            continue
        own = set(client.get("transcript_ids") or [])
        if client.get("consent") != "no_use" and any((clearances or {}).get(e.evidence_id) for e in d.evidence if e.transcript_id in own):
            continue
        for name in dict.fromkeys([client["name"], *(client.get("aliases") or [])]):
            name = (name or "").strip()
            if len(name) >= 3 and re.search(r"(?<!\w)" + re.escape(name) + r"(?!\w)", named_surface, re.I):
                block(f"{name} (a client) is named in public copy without that client's consent to be named or a clearance",
                      section="narrative")
                break

    # Phase N8 (writer v5.2's provenance): a person or account never to be named, or a marker of the published work one must
    # never be linked to, blocks whatever any clearance says (1.B12's extension); a client name or figure that only an
    # internal meeting's evidence carries blocks too (1.B13's extension, D24).
    identities = provenance.get("identities") or []
    fields = {label: text for _, label, text in copy if text}
    fields["the brief's angle and point"] = named_surface
    if identities and identity_checks:
        from ..identities import copy_findings
        for f in copy_findings(fields, identities, evidence_ids=provenance.get("identity_ids") or [], where="public copy"):
            block(f["message"] + f" (in {f['field']})", section="narrative")
        from ..identities import pronoun_findings
        for f in pronoun_findings(fields, identities, where="public copy"):
            add("warning", f["message"] + f" (in {f['field']})", section="narrative")
    team = set(provenance.get("team_practice_transcripts") or [])
    if team:
        from ..identities import leak_findings
        for f in leak_findings(fields, [e.excerpt for e in d.evidence if e.transcript_id in team],
                               [e.excerpt for e in d.evidence if e.transcript_id not in team], identities, where="public copy"):
            block(f["message"] + f" (in {f['field']})", section="narrative")

    # The knowledge base's rejection rules on public copy: a ban blocks, a flag warns (V23).
    for rule in rules or []:
        # A rule may name the asset it governs (RR-09: emails ask for a reply; a DM keyword is fine on Instagram).
        text = email_text if rule.get("applies_to") == "email" else public
        if rule["scope"] in ("all", "brief") and rule["regex"].search(text):
            add("blocking" if rule["kind"] == "ban" else "warning", f"{rule['id']}: {rule['message']}", section="style")

    # E.B10's checks on the narrative: stated-as-done, zero results, frequency claims, misattribution.
    from ..cycle.verification import BLOCK, CHECK, verify_card
    scenes = {}
    for e in d.evidence:
        for mid in e.moment_ids or [e.evidence_id]:
            scenes.setdefault(mid, []).append({"text": e.excerpt, "speaker": e.speaker})
    # The whole public narrative is checked, the WIA perspective, outline and every format alike.
    pseudo = {"title": body.approved_angle.title, "core_perspective": public,
              "why_it_matters": body.audience.reason_to_care, "wia_in_action": body.supporting_example.wia_move,
              "offer_connection": None, "evidence_points": [], "moment_ids": list(scenes)}
    ledger = verify_card(pseudo, scenes, roster, [])
    for flag in ledger["flags"]:
        if flag["kind"] in ("tense", "status", "zero_claim", "misattribution", "number") and flag["severity"] == BLOCK:
            block(flag["message"], section="narrative")
        elif flag["kind"] == "consent" and flag["severity"] == BLOCK:
            # A client's result in public copy needs that client's permission (E.B10): an approver records it as a
            # clearance on the evidence that states the figure (POST /briefs/{id}/clearance).
            figure = re.sub(r"\D", "", flag["message"].split('"')[1]) if '"' in flag["message"] else ""
            stating = [e for e in d.evidence if figure and figure in re.sub(r"\D", "", e.excerpt or "")]
            if not any(e.public_use and e.attribution_verified or (clearances or {}).get(e.evidence_id) for e in stating):
                block(flag["message"] + "; record the client's permission as a clearance on its evidence", section="claims")
        elif flag["kind"] in ("frequency", "generalised_practice", "former_staff") and flag["severity"] == CHECK:
            add("warning", flag["message"])


def before_publishing_checks(block, body):
    if any(q.required and not (q.answer or "").strip() for q in body.before_publishing):
        block("Required before-publishing items remain unanswered", gate=True, section="before_publishing")


def repairable(findings):
    return [f for f in findings if f["severity"] == "blocking" and not f.get("gate")]


def semantic_hash_v2(document: dict) -> str:
    """The reviewed content: before-publishing answers and the CTA confirmation are recorded separately."""
    value = copy.deepcopy(document)
    for item in value["body"].get("before_publishing", []):
        item["answer"] = None
    value["header"]["cta"] = value["body"]["cta"] = None
    return canonical_hash(value)


def header_for(run, body: BriefBodyV2, provenance: dict) -> dict:
    angle = run["input_refs"]["angle"]
    card = (angle.get("body") or {}).get("card") or {}
    cta = person_cta(angle) or {**body.cta.model_dump(mode="json"), "chosen_by": "writer"}
    return {"schema_version": SCHEMA_V2, "angle_id": angle["angle_id"], "angle_hash": angle["approved_hash"],
            "purpose": card.get("pillar") or body.strategic_purpose.pillar,
            "content_type": card.get("content_type") or body.strategic_purpose.content_type,
            "audience": card.get("audience") or angle["body"]["audience"],
            "intended_shift": body.intended_shift.model_dump(mode="json"), "point_of_view": body.point_of_view,
            "cta": cta, "channels": list(run["input_refs"].get("channels") or []),
            "pinned_inputs": provenance["pinned_inputs"]}


def refresh_change(run) -> dict:
    """Why a refreshed version exists, for the versions list (5.F5 d): who asked, with what instructions."""
    refs = run["input_refs"]
    created = run.get("created_at")
    return {"kind": "refresh", "by": refs.get("queued_by"), "at": created.isoformat() if hasattr(created, "isoformat") else created,
            "instructions": refs.get("instructions"), "unlocked": list(refs.get("unlock") or []), "writer": refs.get("writer"),
            "mode": refs.get("mode")}


def finalize_v2(worker, job, run, dossier, body, provenance):
    """Build the v2 document, check it, repair once if needed, and save it for Gate 2."""
    from .runtime import call, compact_dossier
    from ..cycle.verification import load_rules, knowledge_root, rules_for
    from .runtime import knowledge
    from . import paths
    d = Dossier.model_validate(dossier)
    # The lint patterns of the version this brief was written with (E.B11 (2)), else the files'.
    rules = rules_for(knowledge(worker, run), worker.models.knowledge_base_root, "brief") or load_rules(knowledge_root(), stage="brief")
    # A revision keeps every line a person edited (5.F5; a whole section for locks recorded before 22 October), unless
    # the reviewer released it for this refresh or, for a section, the instruction names it (Phase 5 refine, as v1).
    parent, keep, restored = None, [], []
    if run["input_refs"].get("revision_of"):
        from .gate_two import get
        parent = get(worker.repo, run["input_refs"]["revision_of"])
        keep = paths.revision_locks(run, parent)

    def assemble(value):
        value = BriefBodyV2.model_validate(value)
        if keep:
            kept, back = paths.restore(parent["content_body"]["document"]["body"], value.model_dump(mode="json"), keep)
            restored.extend(back)
            value = BriefBodyV2.model_validate(kept)
        if (cta := person_cta(d.angle)) is not None:
            value = value.model_copy(update={"cta": value.cta.model_copy(update=cta)})
        document = {"header": header_for(run, value, provenance), "body": value.model_dump(mode="json")}
        return document, checks_v2(document, d, provenance, None, rules)

    document, findings = assemble(body)
    repaired = False
    if repairable(findings):
        fixed = call(worker, job, run, "brief_repair", BriefBodyV2,
                     {"brief": document["body"], "dossier": compact_dossier(d), "findings": repairable(findings),
                      "channels": run["input_refs"].get("channels")}, writer_schema_v2(run["input_refs"].get("channels") or []))
        document, findings = assemble(fixed.model_dump(mode="json"))
        repaired = True
    envelope = {"schema_version": SCHEMA_V2, "document": document,
                "review": {"locked_fields": keep, **({"locks_restored": restored} if parent else {}),
                           "findings": findings, "support_reviewed_document_hash": semantic_hash_v2(document),
                           "history_acknowledged": False, "clearances": {}, "repair_used": repaired,
                           "review_kind": "deterministic_ledger_e_b10",
                           # A person's anchor choice carries into a revision; the hand-off view ignores it if its piece left the plan.
                           **parent_anchor(parent)},
                # The brand source is the knowledge base (E.B11 f): its hash, not a separate bundle's (older v2 rows).
                "provenance": {"brand_hash": ((provenance.get("pinned_inputs") or {}).get("knowledge_base") or {}).get("sha256")
                               if d.brand.get("source") == "knowledge_base" else d.brand["hash"],
                               "dossier_hash": canonical_hash(d.model_dump(mode="json")),
                               "run_id": run["run_id"], "angle": d.angle, **provenance},
                **({"context_items": run["input_refs"]["context_items"]} if run["input_refs"].get("context_items") else {}),
                **({"change": refresh_change(run)} if parent else {})}
    row = {"brief_id": "brief_" + canonical_hash([run["run_id"], document])[:24], "week_id": d.angle["week_id"],
           "angle_id": d.angle["angle_id"], "angle_input_hash": d.angle["approved_hash"], "content_body": envelope,
           "selected_evidence": [e.model_dump(mode="json") for e in d.evidence],
           "prior_content_context": [p.model_dump(mode="json") for p in d.prior],
           "research_gaps": {"items": d.gaps, "coverage": d.coverage}, "supersedes_id": run["input_refs"].get("revision_of")}
    row["content_hash"] = hash_brief(row)
    with worker.repo.connection() as conn:
        assert_packet(conn, d.angle)
        verify_evidence(conn, d.evidence)
        from ..retrieval import check_prior
        check_prior(conn, d.prior)
        if parent:
            # The parent must still be the current version, or two revisions would fork it (v1 checks the same).
            from .gate_two import locked
            locked(conn, parent["brief_id"], parent["content_hash"])
        old = conn.execute("SELECT * FROM content_briefs WHERE brief_id=%s", (row["brief_id"],)).fetchone()
        if old and old["content_hash"] != row["content_hash"]:
            raise ValueError("Saved brief identity differs from recovered output")
        insert(conn, "content_briefs", row, conflict=True)
        worker.repo.finish(conn, job, {"brief_id": row["brief_id"], "content_hash": row["content_hash"], "schema_version": SCHEMA_V2,
                                       "blocking": sum(f["severity"] == "blocking" for f in findings), "repair_used": repaired,
                                       "finished_at": datetime.now(UTC).isoformat()}, message="Brief ready for Gate 2")
