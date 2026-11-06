"""The checks that enforce section 4.3 on a v4 brief's assets (E.B24's extension; R60), as Gate 2 findings.

Blocking only where the plan marks it: outcome verbs against the evidence, and hook fidelity against the ledger (a tool
credited with what the call does not have it do, or a decision credited to WIA that the client raised first), unless an
approver attested the fact (R57). Everything else is a warning a person reads: caveat language in copy (validation_v2's
lint, run by checks_v4), a self-audit last line, sibling overlap (a subject repeating the anchor Reel's hook is allowed),
banned phrases (the knowledge base's rejection rules, run by checks_v4) and CTA patterns she never uses, aphoristic kickers,
detail density, the takeaway test and DIY drift on every asset, the email's send header and no bullet lists, "-Whitney" on
first-person captions, a carousel CTA for both DIY and done-for-you readers, the offer descriptor on CONVERT assets, the
register by format, and the Reel set (story, stance, b-roll; two allowed, D30). Across the cycle's briefs (`week_findings`):
one offer CTA a week on Instagram, and covers distinct across the week.

E.B24's warnings decided (Phase N6; `research/n6-n11-2026-10/EB24-decisions.md`): four of them are WIA's house rules,
stated as patterns that do not need a reading, and block: no bullet list in the email, "-Whitney" on a first-person
caption, an offer named on a CONVERT asset without its approved descriptor, and a CTA she never uses. The rest stay
warnings by decision: each needs a person's reading (a kicker, density, overlap, the takeaway, DIY drift, the register, the
CTA slide's two readers) or is a proposal WIA confirms when scheduling (the send header).

The first-touch checks are E.B34's (first_touch.py). Savannah's caption framework as a model check is M6's. Each check has a
failing and a passing test from WIA's own text (tests/test_asset_checks.py).
"""
from __future__ import annotations

import re

from .contracts_v4 import on_screen
from .first_touch import (ACTIONS, _ORIGINATED, assets, attested_texts, finding, offer_descriptors, pairs, sentences, snippet,
                          stems, turn_pairs, without_quotes)

# Outcome words and the evidence that supports each (W4 of 21 October: clicks are not bookings).
OUTCOMES = {
    "booking": (re.compile(r"\b(?:booked|\d+\s+(?:new\s+)?bookings)\b", re.I), re.compile(r"\bbook", re.I)),
    "signing": (re.compile(r"\b(?:signed|\d+\s+(?:new\s+)?contracts)\b", re.I), re.compile(r"\bsign(?:ed|ing)?\b|\bcontract", re.I)),
    "conversion": (re.compile(r"\bconverted\b", re.I), re.compile(r"\bconver", re.I)),
    "revenue": (re.compile(r"\b(?:revenue|sales) (?:went|grew|doubled|tripled|jumped)\b", re.I), re.compile(r"\brevenue|\bsales\b|\$", re.I)),
}
# An imperative the reader runs on their own account, at the start of a sentence ("Take a look at your budget"), or
# "ask yourself" anywhere.
SELF_AUDIT = re.compile(r"\bask yourself\b|^(?:(?:so|now|just|today),?\s+)?(?:take a (?:hard |quick )?look at|look at|check|review|"
                        r"audit|go through|open (?:up )?)\s+(?:what |how )?(?:your|you)\b", re.I)
DIY = re.compile(r"(?:^|[.!?]\s+)(?:(?:so|now|then|first|next),?\s+)?(?:turn off|pause|lower|raise|set up|set|change|switch|add|remove|"
                 r"exclude|adjust|create|build|launch|test|try|use|make sure)\b[^.?!\n]{0,40}\byour (?:campaigns?|ads|budget|account|"
                 r"audiences?|bids?|keywords?|landing page|targeting|settings|objective)\b|\bhere['’]?s how to\b|\bstep (?:one|1)\b", re.I)
TAKEAWAY = re.compile(r"\b(?:you should|you need to|make sure (?:you|your)|don['’]?t forget to)\b", re.I)
NEVER_USED_CTA = re.compile(r"\bfollow along\b|\bstay tuned\b|\bfollow (?:us|me) for more\b", re.I)
SPOKEN_FILLER = re.compile(r"\b(?:um+|uh+|you guys|kinda|gonna|wanna|okay,? so)\b|,\s*right\?", re.I)
OKAY_SO = re.compile(r"^\W*(?:okay|ok),?\s+so\b", re.I)
CONTRACTION = re.compile(r"\b\w+['’](?:s|re|ve|ll|d|t|m)\b", re.I)
FIRST_PERSON = re.compile(r"\b(?:I|I['’](?:m|ve|d|ll)|me|my)\b")
SIGNED = re.compile(r"[-–]\s?Whitney\s*$")
BULLET = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s+", re.M)
# Each reader in the second person or the third ("Others want us to launch their campaigns and guide them", N4).
DIY_READER = re.compile(r"run (?:them|it|your (?:own )?ads) yourself|while (?:you|they) run|run (?:your|their) own|guide (?:you|them)|"
                        r"launch (?:your|their) campaigns|do it (?:yourself|themselves)|accelerator", re.I)
DFY_READER = re.compile(r"manage (?:them|your ads|it|your advertising) for you|manage their (?:ads|advertising) for them|"
                        r"our team (?:to )?manage|manage (?:your|their) ads|done[- ]for[- ]you|run (?:your|their) ads for (?:you|them)|"
                        r"elevate|full[- ]service", re.I)
OFFER_CTA = re.compile(r"\bDM\b[^.?!\n]{0,40}?[\"“]?\b(?:ADS|ELEVATE|AUDIT)\b|\bapply (?:now|today|here)\b|\bjoin the (?:\w+ )?waitlist\b")
CALL_SHARE = re.compile(r"\b(?:most of (?:the|that|our|her|his) (?:\w+ )?call|the (?:whole|entire) (?:\w+ )?call|half (?:of )?the call|"
                        r"an hour on)\b", re.I)
OPERATIONAL = re.compile(
    r"\$\s?\d[\d,]*|\b\d+(?:\.\d+)?\s?%|\b\d+\s+(?:days?|weeks?|months?|leads?|clicks?|campaigns?|keywords?|impressions)\b|"
    r"\b(?:about |roughly )?half\b|\bdaily budget\b|\bretarget\w*|\baudiences?\b|\bimpressions\b|\bkeywords?\b|"
    r"\bconversions? (?:tracking|rate)\b|\btrack(?:ed|ing)\b|\bpixel\b|\bbid(?:s|ding)?\b|\bcost per (?:lead|click)\b|\bobjectives?\b|"
    r"\bplacements?\b|\blookalike\b|\bradius\b|\bzip codes?\b|\bsearch terms\b|\bad sets?\b", re.I)
_PAST = re.compile(r"\b\w+ed\b|\b(?:was|were|did|had|got|went|came|said|told|made|took|brought|left|ran|saw)\b|"
                   r"\b(?:didn|wasn|weren|hadn)['’]t\b", re.I)
# A sentence about someone in the story, not a generic line.
_STORY_SUBJECT = re.compile(r"^(?:she|he|they|we|i|our|her|his|their)\b", re.I)
_NEGATION = re.compile(r"n['’]t\b|\b(?:not|none|never|no|nothing)\b", re.I)
_KICKER_ONE = re.compile(r"^(?:it|that|this)['’]?s? [^,.]{1,25}, but (?:it['’]s|it is|that['’]s|they['’]re) (?:still )?\w+[.!]?$", re.I)
SIGN_OFF = re.compile(r"^(?:talk soon|xo|cheers|best|sincerely|warmly|take care)\b|^[-–]?\s*whitney\b|\{\{", re.I)


def _cap(label: str) -> str:
    return label[0].upper() + label[1:]


def _paragraphs(text: str) -> list[str]:
    return [p.strip() for p in re.split(r"\n\s*\n", text or "") if p.strip()]


def _words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+(?:['’][a-z]+)?", (text or "").lower().replace("’", "'"))


def _story_parts(a: dict) -> list[tuple[str, str, str]]:
    """The parts of an asset that tell its story: a script, its screens, its slides, the email, a caption."""
    return [x for part in ("script", "screens", "slides", "email", "caption") for x in a["parts"].get(part) or []]


def _last_lines(a: dict) -> list[tuple[str, str, str]]:
    """Where an asset ends: a script's last paragraph, the last screen or slide, the email's ending, a caption's ending."""
    out = []
    for part in ("script", "screens", "slides", "email", "caption"):
        lines = a["parts"].get(part) or []
        if lines:
            path, label, text = lines[-1]
            paragraphs = _paragraphs(text)
            out.append((path, label, paragraphs[-1] if paragraphs else text))
    return out


# Copy checks -----------------------------------------------------------------------------------------------------

def outcome_findings(asset_list, evidence) -> list[dict]:
    """Outcome verbs against the evidence (blocking): a booking, a signing, a conversion or revenue stated as a result needs
    a turn of the call that speaks of that outcome. Without a dossier (a hand-built pack) there is nothing to check against."""
    if not evidence:
        return []
    said = " ".join(e.get("excerpt") or "" for e in evidence)
    out = []
    for a in asset_list:
        for path, label, text in a["texts"]:
            for sentence in sentences(without_quotes(text)):
                if sentence.endswith("?"):
                    continue
                for name, (claim, support) in OUTCOMES.items():
                    if claim.search(sentence) and not support.search(said):
                        out.append(finding("blocking", "copy.outcome_verbs",
                                           f'{_cap(label)} states a {name} ("{snippet(sentence, 80)}"), but the call speaks of no '
                                           f"{name}: say only what happened (a click, a lead, an inquiry)", path))
    return out


def self_audit_findings(asset_list) -> list[dict]:
    out = []
    for a in asset_list:
        for path, label, text in _last_lines(a):
            last = sentences(text)[-2:]
            if m := next((SELF_AUDIT.search(s.strip()) for s in last if SELF_AUDIT.search(s.strip())), None):
                out.append(finding("warning", "copy.self_audit",
                                   f'{_cap(label)} ends on a self-audit ("{m.group(0)}"): end on what WIA believes or does, not a '
                                   "check the reader runs on their own account", path))
    return out


def takeaway_findings(asset_list) -> list[dict]:
    out = []
    for a in asset_list:
        for path, label, text in _last_lines(a):
            if m := TAKEAWAY.search(without_quotes(text)):
                out.append(finding("warning", "copy.takeaway",
                                   f'{_cap(label)} leaves the reader with what they should do ("{m.group(0)}"): the takeaway is '
                                   '"I want a team that thinks like this", never "I should change this in my account"', path))
    return out


def diy_findings(asset_list) -> list[dict]:
    out = []
    for a in asset_list:
        for path, label, text in _story_parts(a):
            if m := DIY.search(without_quotes(text)):
                out.append(finding("warning", "copy.diy_drift",
                                   f'{_cap(label)} drifts into how-to ("{snippet(m.group(0).strip(" .!?"), 60)}"): show how WIA '
                                   "thinks and works, not steps for the reader's own account", path))
                break
    return out


def kicker_findings(asset_list) -> list[dict]:
    """Aphoristic kickers: a paragraph closed by a short, generic contrast ("Meta is great at following instructions.
    Somebody has to write good ones."), the construction her team rejects as an AI phrase."""
    out = []
    for a in asset_list:
        for path, label, text in _story_parts(a):
            for paragraph in _paragraphs(without_quotes(text)):
                ss = [s for s in sentences(paragraph) if not SIGN_OFF.search(s)]
                if not ss or ss[-1].endswith("?"):
                    continue
                pair = ss[-2:] if len(ss) >= 2 else []
                generic = pair and all(len(_words(s)) <= 9 and not _PAST.search(s) and not FIRST_PERSON.search(s)
                                       and not _STORY_SUBJECT.search(s) for s in pair)
                turn = generic and (any(_NEGATION.search(s) for s in pair)
                                    or re.match(r"^(?:somebody|someone|and|but|that['’]s|it['’]s)\b", pair[1], re.I))
                if turn or _KICKER_ONE.match(ss[-1]):
                    kicker = " ".join(pair) if generic else ss[-1]
                    out.append(finding("warning", "copy.kicker",
                                       f'{_cap(label)} closes on an aphoristic kicker ("{snippet(kicker, 80)}"): end on the story '
                                       "or the plain principle", path))
                    break
    return out


def detail_findings(asset_list, limit: int = 3) -> list[dict]:
    """Detail density: more than three operational details (figures, settings, account mechanics) in one story."""
    out = []
    for a in asset_list:
        details = {}
        for path, label, text in _story_parts(a):
            for m in OPERATIONAL.finditer(without_quotes(text)):
                details.setdefault(re.sub(r"\s+", " ", m.group(0).lower().strip()), path)
        if len(details) > limit:
            first = next(iter(details.values()))
            out.append(finding("warning", "copy.detail_density",
                               f"{_cap(a['label'])} tells its story with {len(details)} operational details ("
                               + ", ".join(list(details)[:6]) + "): one moment and at most two concrete details", first))
    return out


def _spans(text: str, n: int) -> set[tuple[str, ...]]:
    words = _words(without_quotes(text))
    return {tuple(words[i:i + n]) for i in range(len(words) - n + 1)}


def overlap_findings(asset_list, *, anchor_key: str | None = None, allowed=(), n: int = 8) -> list[dict]:
    """Sibling overlap: assets of one brief repeat the idea, never the language (KB 09, F01 and F02). A shared run of eight
    or more words (a repeated sentence, not a shared phrase), outside quotations, sign-offs, CTAs and offer descriptors, is a warning. A subject line repeating the anchor
    Reel's on-screen hook or cover is allowed (Pack 1 of 20 October does it)."""
    exempt = set()
    for text in allowed:
        exempt |= _spans(text, n)

    def lines(a):
        return [(p, lab, t) for p, lab, t in a["texts"] if not OFFER_CTA.search(t) and not SIGN_OFF.search(t.strip())]
    anchor = next((a for a in asset_list if a["key"] == anchor_key), None)
    anchor_first = {_norm(t) for _, _, t, _ in (anchor or {}).get("first_touch", [])}
    out = []
    for i, a in enumerate(asset_list):
        for b in asset_list[i + 1:]:
            best = None
            for pa, la, ta in lines(a):
                sa = _spans(ta, n) - exempt
                if not sa:
                    continue
                for pb, lb, tb in lines(b):
                    if "subject_options" in pa and _norm(tb) in anchor_first or "subject_options" in pb and _norm(ta) in anchor_first:
                        continue
                    shared = sa & _spans(tb, n)
                    if shared and (not best or len(shared) > best[0]):
                        best = (len(shared), pa, la, lb, " ".join(sorted(shared)[0]))
            if best:
                _, path, la, lb, span = best
                out.append(finding("warning", "copy.sibling_overlap",
                                   f'{_cap(la)} and {lb} repeat the same words ("{span}..."): siblings repeat the idea, never the '
                                   "language", path))
    return out


def _norm(text: str) -> str:
    return " ".join(_words(text))


def never_used_cta_findings(asset_list) -> list[dict]:
    out = []
    for a in asset_list:
        for path, label, text in a["texts"]:
            if m := NEVER_USED_CTA.search(text or ""):
                out.append(finding("blocking", "copy.never_used_cta",
                                   f'{_cap(label)} uses "{m.group(0)}", a CTA Whitney never uses: take one from the CTA catalogue, '
                                   "or end on the principle", path))
    return out


def hook_fidelity_findings(body: dict, asset_list, evidence=(), roster=None, attested=()) -> list[dict]:
    """Hook fidelity against the ledger: what a hook, subject or cover says a tool did, or who decided, matches the call or an
    attested fact (blocking on a mismatch unless attested); how much of a call something took is a person's check."""
    facts = attested_texts(attested)
    attested_pairs = {(k, act) for f in facts for k, act, _ in pairs(f["text"], window=10)}
    turns = sorted(evidence or [], key=lambda e: e.get("start_ms") or 0)
    call_pairs = [(k, act) for t in turns for k, act, _ in turn_pairs(t, roster)]
    hooks = [(p, lab, t) for a in asset_list for p, lab, t, _ in a["first_touch"]]
    hooks += [(f"narrative_outline.hooks[{i}].text", f"hook {i + 1}", h["text"])
              for i, h in enumerate((body.get("narrative_outline") or {}).get("hooks") or [])]
    out = []
    for path, label, text in hooks:
        if m := CALL_SHARE.search(text or ""):
            if not any(m.group(0).lower() in f["text"].lower() for f in facts):
                out.append(finding("warning", "copy.hook_fidelity",
                                   f'{_cap(label)} says how much of a call something took ("{m.group(0)}"): check it against the '
                                   "call before publishing", path))
        if not turns and not facts:
            continue
        for klass, action, clause in pairs(text):
            if (klass, action) in attested_pairs:
                continue
            # What the call has a tool do; an attested fact allows more but never narrows it.
            tool_did = {act for k, act in call_pairs if k == "tool"}
            if klass == "tool" and tool_did and action not in tool_did:
                out.append(finding("blocking", "copy.hook_fidelity",
                                   f'{_cap(label)} says the tool did "{snippet(clause, 60)}" ({action.replace("_", " ")}), but the '
                                   f'record has it {" and ".join(sorted(a.replace("_", " ") for a in tool_did))} only', path))
        if _ORIGINATED.search(without_quotes(text)) and turns:
            for action, pattern in ACTIONS.items():
                if not re.search(r"\b(?:" + pattern + ")", without_quotes(text), re.I) or ("wia", action) in attested_pairs:
                    continue
                if re.search(r"\b(?:our|we|i)\b", text, re.I) is None:
                    continue
                first = next((t for t in turns if re.search(r"\b(?:" + pattern + ")", t.get("excerpt") or "", re.I)), None)
                if first and next((k for k, act, _ in turn_pairs(first, roster) if act == action), None) == "client":
                    out.append(finding("blocking", "copy.hook_fidelity",
                                       f'{_cap(label)} credits the decision to WIA ("{snippet(text, 70)}"), but the client raised it '
                                       "first on the call: say what WIA asked and did, and keep who decided", path))
    return out


# Format checks ---------------------------------------------------------------------------------------------------

def email_findings(asset_list) -> list[dict]:
    out = []
    for a in (x for x in asset_list if x["kind"] == "email"):
        header = a["value"].get("send_header") or {}
        missing = [k.upper().replace("_", " ") for k in ("date", "send_time", "recipients") if not (header.get(k) or "").strip()]
        if missing:
            out.append(finding("warning", "format.send_header",
                               "The email has no " + ", ".join(missing) + " in its send header (proposed for WIA to confirm)",
                               "format_plan.email.send_header"))
        for path, label, text in a["parts"]["email"]:
            if BULLET.search(text or ""):
                out.append(finding("blocking", "format.email_bullets", f"{_cap(label)} has a bullet list: the email is short "
                                                                     "flowing paragraphs", path))
    return out


def caption_findings(asset_list) -> list[dict]:
    out = []
    for a in asset_list:
        caption = a["parts"].get("caption") or []
        if not caption:
            continue
        text = "\n".join(t for _, _, t in caption)
        first_person = any(FIRST_PERSON.search(s) for s in sentences(without_quotes(text)) if not s.endswith("?"))
        if first_person and not SIGNED.search(caption[-1][2].strip()):
            out.append(finding("blocking", "format.caption_signoff",
                               f"{_cap(a['label'])}'s caption speaks as Whitney (\"I\") without \"-Whitney\" at the end", caption[-1][0]))
    return out


def carousel_cta_findings(asset_list) -> list[dict]:
    out = []
    for a in (x for x in asset_list if x["kind"] == "carousel"):
        slides = a["parts"]["slides"]
        tail = " ".join(t for _, _, t in slides[-2:])
        if not (DIY_READER.search(tail) and DFY_READER.search(tail)):
            out.append(finding("warning", "format.carousel_cta",
                               "The carousel's CTA slide speaks to only one reader: name both the owner who wants our team to "
                               "run their ads and the one who wants us to launch them and guide them", slides[-1][0] if slides else a["path"]))
    return out


def offer_findings(asset_list, pillar: str | None, offers) -> list[dict]:
    """On a CONVERT brief, every asset that names an offer as the solution carries one of its approved descriptors."""
    if pillar != "CONVERT":
        return []
    out = []
    for a in asset_list:
        text = without_quotes(" \n".join(t for _, _, t in a["texts"]))
        low = text.lower()
        for offer in offers:
            if not re.search(offer["pattern"], text, re.I):
                continue
            phrases = [d.lower() for d in offer.get("descriptors") or []] + [k.lower() for k in offer.get("key_phrases") or []]
            if not any(p in low for p in phrases):
                out.append(finding("blocking", "format.offer_descriptor",
                                   f"{_cap(a['label'])} names {offer['offer']} without its approved descriptor (\""
                                   f"{offer['descriptors'][0]}\")", a["path"]))
            if "offer_descriptor" in a["value"]:
                given = (a["value"].get("offer_descriptor") or "").strip().lower()
                if not given:
                    out.append(finding("warning", "format.offer_descriptor",
                                       f"{_cap(a['label'])} names {offer['offer']} but its offer_descriptor is empty", f"{a['path']}.offer_descriptor"))
                elif given not in [d.lower() for d in offer.get("descriptors") or []]:
                    out.append(finding("warning", "format.offer_descriptor",
                                       f"{_cap(a['label'])}'s offer_descriptor is not one of {offer['offer']}'s approved descriptors",
                                       f"{a['path']}.offer_descriptor"))
    return out


def register_findings(asset_list) -> list[dict]:
    """Register by format: face-to-camera scripts are spoken; the email and captions are written, not spoken."""
    out = []
    for a in asset_list:
        if a["kind"] == "reel" and a["register"]:
            wanted = "on_screen" if a.get("on_screen") else "spoken"
            if a["register"] != wanted:
                made = "on-screen text" if a.get("on_screen") else "face-to-camera"
                out.append(finding("warning", "format.register", f"{a['label']} is a {made} Reel, so its register is {wanted}, "
                                                                 f"not {a['register']}", f"{a['path']}.register"))
        for path, label, text in a["parts"].get("script") or []:
            if OKAY_SO.search(text or ""):
                out.append(finding("warning", "format.register", f'{_cap(label)} opens with "Okay, so": start on the first real line', path))
            words = _words(text)
            if len(words) >= 40 and not CONTRACTION.search(text or ""):
                out.append(finding("warning", "format.register", f"{_cap(label)} reads as written, not spoken: no contractions in "
                                                                 f"{len(words)} words", path))
        for part in ("email", "caption"):
            for path, label, text in a["parts"].get(part) or []:
                if m := SPOKEN_FILLER.search(without_quotes(text)):
                    out.append(finding("warning", "format.register", f'{_cap(label)} carries a spoken filler ("{m.group(0)}"): emails '
                                                                     "and captions are clean and declarative", path))
    return out


def reel_set_findings(body: dict, channels) -> list[dict]:
    """The same idea through different doors (section 4.3, D30): Reel 1 the story, then the stance and b-roll; two Reels when
    the idea does not support three; b-roll has one to three screens and no script; every Instagram asset has its caption."""
    reels = (body.get("format_plan") or {}).get("reels") or []
    out = []
    if "reel" in (channels or ()) and len(reels) == 1:
        out.append(finding("warning", "format.reels", "One Reel: write two or three (story, stance, b-roll), two when the idea "
                                                      "does not support three", "format_plan.reels"))
    kinds = [r.get("kind") for r in reels]
    if reels and kinds[0] not in ("story", "central"):
        out.append(finding("warning", "format.reels", "Reel 1 is the central story, face to camera", "format_plan.reels[0].kind"))
    if len(set(kinds)) != len(kinds):
        out.append(finding("warning", "format.reels", "Two Reels have the same place: Reel 1 is the central story, Reels 2 and 3 "
                                                      "each have a premise of their own", "format_plan.reels"))
    for i, r in enumerate(reels):
        path = f"format_plan.reels[{i}]"
        if on_screen(r):
            if not 1 <= len(r.get("screens") or []) <= 3:
                out.append(finding("warning", "format.reels", f"Reel {i + 1} is on-screen text and needs one to three screens",
                                   f"{path}.screens"))
        elif r.get("source") == "new_script" and not (r.get("script") or "").strip():
            out.append(finding("warning", "format.reels", f"Reel {i + 1} is a new script without its script", f"{path}.script"))
        if "caption" in (channels or ()) and not r.get("caption"):
            out.append(finding("warning", "format.reels", f"Reel {i + 1} has no caption", f"{path}.caption"))
    carousel = (body.get("format_plan") or {}).get("carousel")
    if carousel and "caption" in (channels or ()) and not carousel.get("caption"):
        out.append(finding("warning", "format.reels", "The carousel has no caption", "format_plan.carousel.caption"))
    return out


# All of E.B24's extension ----------------------------------------------------------------------------------------

def asset_findings(body: dict, *, pillar=None, channels=("reel", "carousel", "email", "caption"), evidence=(), roster=None,
                   attested=(), offers=None, anchor_key="reel_1") -> list[dict]:
    asset_list = assets(body)
    offers = offers if offers is not None else offer_descriptors()
    allowed = [d for o in offers for d in o.get("descriptors") or []]
    return (outcome_findings(asset_list, evidence) + hook_fidelity_findings(body, asset_list, evidence, roster, attested)
            + self_audit_findings(asset_list) + takeaway_findings(asset_list) + diy_findings(asset_list)
            + kicker_findings(asset_list) + detail_findings(asset_list) + never_used_cta_findings(asset_list)
            + overlap_findings(asset_list, anchor_key=anchor_key, allowed=allowed) + email_findings(asset_list)
            + caption_findings(asset_list) + carousel_cta_findings(asset_list) + offer_findings(asset_list, pillar, offers)
            + register_findings(asset_list) + reel_set_findings(body, channels))


# Across the cycle's briefs ---------------------------------------------------------------------------------------

def _instagram_offer_ctas(body: dict) -> list[str]:
    return [a["label"] for a in assets(body) if a["kind"] in ("reel", "carousel")
            and any(OFFER_CTA.search(t or "") for _, _, t in a["texts"])]


def _covers(body: dict) -> list[tuple[str, str]]:
    return [(f"Reel {i + 1}", r.get("cover_text") or "") for i, r in enumerate(((body.get("format_plan") or {}).get("reels") or []))]


def week_findings(body: dict, siblings: list[dict]) -> list[dict]:
    """One offer CTA a week on Instagram, and covers distinct across the week, over this brief and the cycle's other current
    briefs (`siblings`: [{brief_id, title, body}])."""
    out = []
    mine = _instagram_offer_ctas(body)
    theirs = [(s["title"], label) for s in siblings for label in _instagram_offer_ctas(s["body"])]
    if mine and len(mine) + len(theirs) > 1:
        others = [f'{label} of "{snippet(title, 40)}"' for title, label in theirs]
        out.append(finding("warning", "week.offer_cta",
                           "One offer CTA a week on Instagram: this brief's " + " and ".join(mine) + " ask for it"
                           + (", and so do " + ", ".join(others) if others else "") + ". Keep one; the rest end on the principle",
                           "format_plan"))
    for i, (label, cover) in enumerate(_covers(body)):
        mine_stems = stems(cover)
        for s in siblings:
            for other_label, other in _covers(s["body"]):
                theirs_stems = stems(other)
                union = mine_stems | theirs_stems
                if union and len(mine_stems & theirs_stems) / len(union) >= 0.8:
                    out.append(finding("warning", "week.covers",
                                       f'{label}\'s cover repeats {other_label}\'s cover of "{snippet(s["title"], 40)}" ("{snippet(other, 50)}"): '
                                       "covers are distinct across the week", f"format_plan.reels[{i}].cover_text"))
    return out


def week_siblings(conn, row: dict) -> list[dict]:
    """The cycle's other current briefs (same week, not replaced, not rejected) that have assets to compare."""
    rows = conn.execute(
        "SELECT b.brief_id, b.content_body FROM content_briefs b WHERE b.week_id=%s AND b.angle_id<>%s "
        "AND b.approval_status<>'rejected' AND NOT EXISTS (SELECT 1 FROM content_briefs n WHERE n.supersedes_id=b.brief_id) "
        "ORDER BY b.brief_id", (row["week_id"], row["angle_id"])).fetchall()
    out = []
    for r in rows:
        body = ((r["content_body"] or {}).get("document") or {}).get("body") or {}
        if isinstance(body.get("format_plan"), dict):
            out.append({"brief_id": r["brief_id"], "title": (body.get("approved_angle") or {}).get("title") or r["brief_id"], "body": body})
    return out
