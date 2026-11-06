"""The first-touch rules as checks (E.B34; plan section 4.3, R59, R60): WIA's corrections of 13 and 20 October, with her
text as the tests (`tests/test_first_touch.py`).

First-touch text is what a cold reader sees before deciding to keep going: the email's subject lines and preview, every
Reel's cover and on-screen hook, the first b-roll screen and carousel slide 1.

(a) **Subject lines** (rule 3) state WIA's counter-expected point or the reader's own question or problem, never a narration
    of what a third party did (W3: "She used AI to set up her Google Ads") and never the process (13 October: "More
    inquiries? Here's what we look at next"; "about... the problem than the process").
(b) **Slide 1 carries the title's promise** (rule 2): never a bare quote (W4), it shares the title's subject, and when the
    title's promise is a problem slide 1 opens on it, not on good news (13 October: "More inquiries. More tours booked.").
(c) **Specific** (rule 1): covers, on-screen hooks and the first b-roll screen name the concrete subject (W5, W7, W8:
    "Did I set this up wrong?" becomes "Did I set my ads up wrong?"). Specificity outranks sibling distinctness: no check
    here or in asset_checks asks a first-touch line to drop its subject to differ from a sibling.
(d) **Insider terms** (rule 4; W6), extending the `block_terms` idea of validation_v2 (a term WIA keeps from public copy)
    with a scope: never in first-touch text (blocking); in a script, an email or a caption at most once (blocking above
    that), explained in plain words (a warning when it is not). The terms are `knowledge_base/insider-terms.json`.
(e) **Who did what** (rule 5; W8): a story beat keeps the actor the record names, or the fact an approver attested at a
    gate (R57). Checked here against attested facts and the call's turns; asset_checks' hook-fidelity check applies the
    same reading to what a hook claims about a tool or a decision.

Everything is deterministic and reads the copy only, so it runs at Gate 2 on every edit and on hand-built packs alike
(`scripts/pack_checks.py`).

Which of these block (E.B24's warnings decided, Phase N6; `research/n6-n11-2026-10/EB24-decisions.md`): WIA gave the
subject, slide 1 and cover corrections twice (13 and 20 October), so (a) blocks on the subject sent first (the other
options warn), (b) blocks on a bare quote or a slide 1 that drops the title's subject (the good-news order warns) and (c)
blocks; a blocking finding in a pack goes to the finisher's repair like every other. An unexplained insider term stays a
warning (whether a sentence explains a term is a reading, not a pattern).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from ..cycle.verification import QUOTE
from .contracts_v4 import on_screen

# The concrete subjects a cold wedding-business reader recognises (rule 1): advertising, its platforms and money, and what
# it produces for a wedding business.
SUBJECT = re.compile(
    r"\b(?:ads?|advertis\w*|budgets?|spend(?:s|ing)?|spent|google|meta|facebook|instagram|campaigns?|inquir(?:y|ies)|leads?|"
    r"bookings?|booked|tours?|consult(?:s|ations?)?|cost per lead|marketing|follow[- ]?up|clicks?|traffic|couples?|"
    r"ai|chatgpt|keywords?|landing pages?|reels?|emails?|website)\b", re.I)
# Words that carry a problem or a tension (rule 2: slide 1 leads with the title's problem, not with good news).
TENSION = re.compile(r"n['’]t\b|\b(?:not|no|never|nothing|none|without|stop(?:s|ped)?|quiet|lost|lose|losing|wrong|"
                     r"enough|still|but|yet|instead|disappear\w*|ghost\w*|waste\w*|can['’]?t|cannot)\b", re.I)
# Words that carry no subject (for the title's promise on slide 1).
_STOP = set("""a an and are as at be but by for from has have he her his i if in into is it its of on or our she so than
that the their them they this to was we were what when which who will with you your about after before because been being
can could did does doing just like more most not now only other over some such then there these those through very would
also how why here here's what's it's don't aren't isn't can't won't doesn't didn't wasn't us me my do done one part
thing things way why's""".split())
# A subject line that narrates what a third party did (rule 3, W3): a client, member or pro as its grammatical subject,
# with a past-tense verb in its first few words.
_THIRD_PARTY = re.compile(
    r"^(?:she|he|they|my client|our client|a (?:new )?(?:client|wedding pro|venue(?: owner)?|planner|photographer|member|"
    r"prospect|couple|bride|groom|owner)|one of our \w+)\b(?:\s+\S+){0,3}?\s+"
    r"(?:\w+ed|used|built|set|made|got|had|did|went|told|said|came|ran|took|brought|lost|found|spent|saw|thought|knew|left|"
    r"wrote|gave|sent|tried|hired)\b", re.I)
# A subject line about WIA's process rather than the reader's problem (13 October, 12:50 to 13:11).
_PROCESS = re.compile(r"\bhere['’]?s (?:what|how) we\b|\b(?:what|how) we (?:look at|check|review|investigate|audit) (?:next|first)\b|"
                      r"\bour (?:process|approach) (?:for|to)\b", re.I)
_SENTENCE = re.compile(r"(?<=[.!?…])[\"”’)]*\s+|\n+")
ROOT = Path(__file__).resolve().parents[2] / "knowledge_base"
INSIDER_TERMS = "insider-terms.json"
OFFER_DESCRIPTORS = "offer-descriptors.json"


# Data ------------------------------------------------------------------------------------------------------------

def load_data(name: str, root: Path | str | None = None) -> dict:
    """A machine-readable knowledge-base file (interface 5), from `root` or the committed knowledge base; empty when absent."""
    for base in (Path(root) if root else None, ROOT):
        if base and (base / name).is_file():
            return json.loads((base / name).read_text(encoding="utf-8"))
    return {}


def insider_terms(provenance: dict | None = None, root=None) -> list[dict]:
    """The pinned terms of a brief (provenance), else the knowledge base's."""
    pinned = (provenance or {}).get("insider_terms")
    return pinned["terms"] if isinstance(pinned, dict) else (load_data(INSIDER_TERMS, root).get("terms") or [])


def offer_descriptors(provenance: dict | None = None, root=None) -> list[dict]:
    pinned = (provenance or {}).get("offer_descriptors")
    return pinned["offers"] if isinstance(pinned, dict) else (load_data(OFFER_DESCRIPTORS, root).get("offers") or [])


def pinned_data(root=None) -> dict:
    """What a v4 brief pins in its provenance so its checks re-run on the same data at Gate 2."""
    return {"insider_terms": load_data(INSIDER_TERMS, root) or {"terms": []},
            "offer_descriptors": load_data(OFFER_DESCRIPTORS, root) or {"offers": []}}


# The assets of a v4 body ------------------------------------------------------------------------------------------

def assets(body: dict) -> list[dict]:
    """Each asset of a v4 body: its key (the hand-off key), kind, label, path, first-touch lines and copy parts.

    `first_touch` is [(path, label, text, role)]; `parts` maps a part (script, screens, slides, email, caption) to its
    [(path, label, text)]; `texts` is every copy line of the asset."""
    plan = body.get("format_plan") or {}
    out = []
    for i, r in enumerate(plan.get("reels") or []):
        path, label = f"format_plan.reels[{i}]", f"Reel {i + 1}"
        first = [(f"{path}.cover_text", f"{label}'s cover", r["cover_text"], "cover"),
                 (f"{path}.on_screen_hook", f"{label}'s on-screen hook", r["on_screen_hook"], "on_screen_hook")]
        screens = [(f"{path}.screens[{j}]", f"{label}'s screen {j + 1}", s) for j, s in enumerate(r.get("screens") or [])]
        if screens:
            first.append((*screens[0], "first_screen"))
        parts = {"script": [(f"{path}.script", f"{label}'s script", r["script"])] if r.get("script") else [],
                 "spoken_opening": [(f"{path}.spoken_opening", f"{label}'s spoken opening", r["spoken_opening"])] if r.get("spoken_opening") else [],
                 "screens": screens, "caption": _caption(path, label, r.get("caption"))}
        out.append(_asset(f"reel_{i + 1}", "reel", label, path, r, first, parts, reel_kind=r.get("kind"),
                          on_screen=on_screen(r)))
    if c := plan.get("carousel"):
        path, label = "format_plan.carousel", "the carousel"
        slides = [(f"{path}.slides[{j}].text", f"carousel slide {s['number']}", s["text"]) for j, s in enumerate(c["slides"])]
        first = [(*slides[0], "slide_1")] if slides else []
        parts = {"title": [(f"{path}.title", "the carousel's title", c.get("title") or "")] if c.get("title") else [],
                 "slides": slides, "caption": _caption(path, label, c.get("caption"))}
        out.append(_asset("carousel", "carousel", label, path, c, first, parts))
    if e := plan.get("email"):
        path, label = "format_plan.email", "the email"
        first = [(f"{path}.subject_options[{j}]", f"the email's subject line {j + 1}", s, "subject") for j, s in enumerate(e["subject_options"])]
        first.append((f"{path}.preview", "the email's preview", e["preview"], "preview"))
        parts = {"email": [(f"{path}.{k}", f"the email's {k}", e[k]) for k in ("opening", "body", "ending")]}
        out.append(_asset("email", "email", label, path, e, first, parts))
    return out


def _caption(path, label, caption):
    if not caption:
        return []
    return [(f"{path}.caption.{k}", f"{label}'s caption {k}", caption[k]) for k in ("hook", "body", "ending")]


def _asset(key, kind, label, path, value, first, parts, reel_kind=None, on_screen=False):
    texts = [(p, lab, t) for p, lab, t, _ in first] + [x for part in parts.values() for x in part]
    return {"key": key, "kind": kind, "reel_kind": reel_kind, "on_screen": on_screen, "label": label, "path": path, "value": value,
            "register": value.get("register"), "offer_descriptor": value.get("offer_descriptor"),
            "first_touch": first, "parts": parts, "texts": list(dict.fromkeys(texts))}


# Helpers ---------------------------------------------------------------------------------------------------------

def finding(severity: str, check: str, message: str, field: str | None = None) -> dict:
    """A Gate 2 finding in the v2-family shape, with the check's name and the field it points at."""
    return {"severity": severity, "claim_id": None, "message": message, "gate": False,
            "section": (field or "format_plan").split(".")[0], "field": field, "check": check}


def sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENTENCE.split(text or "") if s and s.strip()]


def without_quotes(text: str) -> str:
    """The text with quoted words removed: a client's own words are hers, not the copy's claim or its subject."""
    return QUOTE.sub(" ", text or "")


def stems(text: str) -> set[str]:
    words = re.findall(r"[a-z][a-z'’]+", (text or "").lower())
    return {w.replace("’", "'")[:4] if len(w) > 4 else w for w in words if w.replace("’", "'") not in _STOP and len(w) > 1}


def snippet(text: str, n: int = 90) -> str:
    text = " ".join((text or "").split())
    return text if len(text) <= n else text[:n - 3].rstrip() + "..."


def bare_quote(text: str) -> bool:
    """A slide that opens on someone's words in quotation marks, with nothing of its own first (W4)."""
    first = (sentences(text) or [""])[0]
    stripped = first.strip().lstrip("*_ ")
    if stripped[:1] not in ('"', "“", "‘", "'"):
        return False
    line = (text or "").strip().split("\n")[0]
    quoted = sum(len(q) for q in re.findall(r'"[^"]+"|“[^”]+”', line))
    return quoted >= 0.6 * len(line.strip())


# (a) Subject lines ------------------------------------------------------------------------------------------------

def subject_problem(subject: str) -> str | None:
    s = (subject or "").strip().strip('"“”')
    if _THIRD_PARTY.search(s):
        return ("narrates what a third party did; a subject states WIA's counter-expected point or the reader's own "
                "question or problem")
    if _PROCESS.search(s):
        return "is about WIA's process; a subject is about the reader's problem, not the process"
    return None


# (c) Specific ----------------------------------------------------------------------------------------------------

def names_subject(text: str) -> bool:
    return bool(SUBJECT.search(without_quotes(text) if without_quotes(text).strip() else text))


# (b) Slide 1 -----------------------------------------------------------------------------------------------------

def slide_one_problems(title: str, slide: str) -> list[str]:
    problems = []
    if bare_quote(slide):
        problems.append("opens on a bare quote; slide 1 is the first thing a cold reader sees and carries the carousel's promise")
    wanted = stems(title)
    if wanted and not wanted & stems(slide):
        problems.append(f'does not carry the title\'s promise ("{snippet(title, 60)}")')
    first = (sentences(slide) or [""])[0]
    if TENSION.search(title or "") and not TENSION.search(first) and not bare_quote(slide):
        problems.append(f'opens on good news ("{snippet(first, 50)}") while the title\'s promise is a problem: lead with the problem')
    return problems


# (d) Insider terms -----------------------------------------------------------------------------------------------

def _term_re(term: dict):
    return re.compile(term["pattern"], re.I)


def _explained(term: dict, sentence_and_neighbours: str) -> bool:
    low = sentence_and_neighbours.lower()
    return any(k in low for k in term.get("explained_by") or [])


def insider_findings(asset_list: list[dict], terms: list[dict]) -> list[dict]:
    out = []
    for term in terms:
        pattern = _term_re(term)
        for a in asset_list:
            for path, label, text, _ in a["first_touch"]:
                if pattern.search(text or ""):
                    out.append(finding("blocking", "first_touch.insider_term",
                                       f'{label[0].upper() + label[1:]} uses "{term["term"]}", a WIA program term a cold reader may '
                                       f'not know: first-touch text never uses it (say "{term["plain"]}" instead)', path))
            # In a body: at most once per part (a script, the email, a caption, the slides), explained in plain words.
            for part, lines in a["parts"].items():
                # A Reel's spoken opening is its script's first line, counted with the script.
                if part == "title" or part == "spoken_opening" and a["parts"].get("script"):
                    continue
                hits = []
                for path, label, text in lines:
                    ss = sentences(text)
                    for k, s in enumerate(ss):
                        for _ in pattern.finditer(s):
                            hits.append((path, label, " ".join(ss[max(0, k - 1):k + 2])))
                if len(hits) > 1:
                    path, label, _ = hits[0]
                    where = a["label"] if part != "caption" else f"{a['label']}'s caption"
                    if part == "script":
                        where = f"{a['label']}'s script"
                    out.append(finding("blocking", "first_touch.insider_term",
                                       f'{where[0].upper() + where[1:]} uses "{term["term"]}" {len(hits)} times: a script or body '
                                       "uses a WIA program term at most once, explained in plain words", path))
                elif hits and not _explained(term, hits[0][2]):
                    path, label, context = hits[0]
                    out.append(finding("warning", "first_touch.insider_term",
                                       f'{label[0].upper() + label[1:]} uses "{term["term"]}" without explaining it: say what it is '
                                       f'in plain words ("{term["plain"]}")', path))
    return out


# (e) Who did what ------------------------------------------------------------------------------------------------
# The actors a story beat can credit, by class. "you" (the reader) and "it" are never actors here.
_ACTORS = [
    ("tool", r"(?:(?:her|his|their|the|my|our|an?)\s+)?(?:own\s+)?(?:ai(?:\s+(?:assistant|agent|tool))?|assistant|chatgpt|"
             r"automation|the algorithm)"),
    ("wia", r"we|our (?:team|strategist|strategists|experts?)|whitney|i"),
    ("client", r"she|he|they|the (?:client|owner|prospect|member|venue|director|couple)|our (?:client|member)|"
               r"a (?:wedding pro|venue owner|client|member|prospect)"),
]
_ACTOR = re.compile(r"\b(?P<actor>" + "|".join(f"(?P<{k}>{p})" for k, p in _ACTORS) + r")\b", re.I)
# Action families: what a beat says someone did.
ACTIONS = {
    "change": r"chang(?:e|ed|es|ing)\b|made (?:a few |some |several |all |the )?changes|mak(?:e|es|ing) (?:a few |some |several |the )?changes|"
              r"tweak\w*|adjust\w*|edit(?:s|ed|ing)?\b|optimi[sz]\w*",
    "run": r"ran\b|run(?:s|ning)?\b|manag(?:e|ed|es|ing)\b",
    "set_up": r"set (?:\w+ )?up\b|sets (?:\w+ )?up\b|setting (?:\w+ )?up\b",
    "turn_off": r"turn(?:ed|s|ing)? (?:\w+ )?off\b|paus(?:e|ed|es|ing)\b",
    "lower": r"lower(?:ed|s|ing)?\b|cut (?:the |her |his |their )?budget|reduc\w*|br(?:ing|ought) (?:it |the budget |her budget )?down|spend(?:ing)? less",
    "raise": r"rais(?:e|ed|es|ing)\b|increas\w*|scal(?:e|ed|ing)\b|spend(?:ing)? more",
}
_ACTION = {k: re.compile(r"\b(?:" + p + ")", re.I) for k, p in ACTIONS.items()}
# A decision or recommendation the copy credits ("our first recommendation was", "we suggested", "she decided").
_ORIGINATED = re.compile(r"\b(?:recommend\w*|suggest\w*|decid\w*|decision|idea|first move)\b", re.I)
_OTHER_SUBJECT = re.compile(r"\b(?:it|you|what|which|who|that|this|everyone|someone|nobody)\b", re.I)
# What a reader may want is not a beat: the offers' close ("Whether you'd like our team to manage your ads, or want us to
# launch your campaigns and guide you while you run them") describes the offers, not who did what in the story.
_WANTED = re.compile(r"\b(?:wants?|wanted)\s+(?:us|a team|our team|someone|an agency)\s+to\b|\bwould like\b|['’]d like\b|"
                     r"\bwhether\b", re.I)
# In the copy, a clause addressed to the reader describes the offer or the reader, not the story ("Inside it, we set up the
# follow-up system around your own conversations"); the story's people are named in the third person.
_READER = re.compile(r"\byou(?:rs?)?\b", re.I)
# A group the clause speaks of in general: a "they" after it is that group, not the story's client.
_GENERAL_GROUP = re.compile(r"\b(?:others|other owners|some (?:owners|venues|pros|people|clients|couples)|owners|venues|"
                            r"wedding pros|businesses|people|many|most|anyone|couples)\b", re.I)
_CLAUSE = re.compile(r"[.;:!?\n]|,\s*(?:and|but|so)\s+|\bthen\b", re.I)
_BEAT_SENTENCE = re.compile(r"[.;:!?\n]")
# A person named inside a relative clause is not the subject of the verb after it: in "the team member I was talking with
# had set them up", the team member set them up, not "I" (Round 2: the check misread a prospect's own setup as ours).
_RELATIVE = re.compile(r"\b(?:with|to|for|from|about|on|at)\s+(?:had|has|have|was|were|is|would|will|could)\s*$", re.I)


def pairs(text: str, *, window: int = 6, copy: bool = False) -> list[tuple[str, str, str]]:
    """(actor class, action, the clause) for each beat in a text that names who did something. Quoted words are skipped:
    they are a speaker's own, read separately as a turn. `copy` reads published copy, where a clause addressed to the reader
    is not a beat."""
    found = []
    for sentence in _BEAT_SENTENCE.split(without_quotes(text)):
        # What a reader may want, or a general group, governs the whole sentence: "Others want us to launch their campaigns,
        # then guide them while they run them" is the offers' close, even in the clause after "then" (Round 2).
        earlier = ""
        for clause in _CLAUSE.split(sentence):
            context, earlier = earlier, earlier + " " + clause
            if copy and _READER.search(clause):
                continue
            for action, pattern in _ACTION.items():
                for m in pattern.finditer(clause):
                    before = clause[:m.start()]
                    actors = list(_ACTOR.finditer(before))
                    if not actors:
                        continue
                    last = actors[-1]
                    between = before[last.end():]
                    # Too far, or another subject in between ("she had no idea what it had changed": "it" changed).
                    if len(between.split()) > window or _OTHER_SUBJECT.search(between) or _RELATIVE.search(between):
                        continue
                    if _WANTED.search(context + " " + before) or last.group(0).lower() == "they" and \
                            _GENERAL_GROUP.search(context + " " + before[:last.start()]):
                        continue
                    klass = next(k for k, _ in _ACTORS if last.group(k))
                    found.append((klass, action, clause.strip()))
    return found


def turn_pairs(turn: dict, roster: list[dict] | None) -> list[tuple[str, str, str]]:
    """The beats a turn of the call names: "I" and "we" are the speaker (WIA staff on the roster, else the client)."""
    from ..cycle.verification import speaker_entry
    entry = speaker_entry(turn.get("speaker"), roster or [])
    me = "wia" if entry and entry.get("status") in ("current", "former") else "client"
    text = re.sub(r"^[^:\n]{1,40}:\s*", "", turn.get("excerpt") or "")
    out = []
    for klass, action, clause in pairs(text):
        first_person = re.search(r"\b(?:i|we|my|our)\b", clause, re.I) and klass == "wia"
        out.append((me if first_person else klass, action, clause))
    return out


def attested_texts(facts) -> list[dict]:
    """Attested facts as {text, author, at}, from context items (interface 2), ledger claims or plain strings."""
    out = []
    for f in facts or []:
        if isinstance(f, str):
            out.append({"text": f, "author": None, "at": None})
        elif isinstance(f, dict) and f.get("text"):
            # A context item (interface 2) of kind attested_fact, or the ledger's own entry for one (5.B7: field
            # "context_items", status attested); a copy line the attestation settled is not a fact of its own.
            attested = f.get("attested") or {}
            if f.get("kind") == "attested_fact" or f.get("status") == "attested" and f.get("field") == "context_items"                     and attested.get("kind") == "attested_fact":
                out.append({"text": f["text"], "author": f.get("author") or attested.get("by"),
                            "at": f.get("created_at") or attested.get("on")})
    return out


def who_did_what(asset_list: list[dict], attested=(), evidence=(), roster=None) -> list[dict]:
    """Rule 5: each beat's actor is the one an attested fact or the call names for that action. A mismatch with an attested
    fact, or with the call where no attested fact allows it, blocks (hook fidelity: "blocking on a mismatch unless
    attested")."""
    facts = attested_texts(attested)
    said = {}
    for f in facts:
        for klass, action, _ in pairs(f["text"], window=10):
            said.setdefault(action, {}).setdefault("attested", set()).add(klass)
    for turn in evidence or []:
        for klass, action, _ in turn_pairs(turn, roster):
            said.setdefault(action, {}).setdefault("call", set()).add(klass)
    names = {"tool": "the AI tool", "wia": "our team", "client": "the client"}
    out, seen = [], set()
    for a in asset_list:
        for path, label, text in a["texts"]:
            for klass, action, clause in pairs(text, copy=True):
                record = said.get(action) or {}
                attested_by = record.get("attested") or set()
                call = record.get("call") or set()
                if attested_by and klass not in attested_by:
                    why = f"the attested fact says {' or '.join(names[k] for k in sorted(attested_by))} did it"
                elif not attested_by and call and klass not in call:
                    why = f"the call has {' or '.join(names[k] for k in sorted(call))} doing it"
                else:
                    continue
                if (path, action) in seen:
                    continue
                seen.add((path, action))
                verb = action.replace("_", " ")
                out.append(finding("blocking", "first_touch.who_did_what",
                                   f'{label[0].upper() + label[1:]} credits {names[klass]} with "{snippet(clause, 70)}" ({verb}), but '
                                   f"{why}: keep the actor the record names, or the fact an approver attested", path))
    return out


# All of E.B34 ----------------------------------------------------------------------------------------------------

def first_touch_findings(body: dict, *, terms=None, attested=(), evidence=(), roster=None) -> list[dict]:
    asset_list = assets(body)
    out = []
    for a in asset_list:
        for path, label, text, role in a["first_touch"]:
            if role == "subject" and (problem := subject_problem(text)):
                sent_first = path.endswith("subject_options[0]")
                out.append(finding("blocking" if sent_first else "warning", "first_touch.subject",
                                   f'The email\'s {"first " if sent_first else ""}subject "{snippet(text, 70)}" {problem}', path))
            if role in ("cover", "on_screen_hook", "first_screen") and not names_subject(text):
                out.append(finding("blocking", "first_touch.specific",
                                   f'{label[0].upper() + label[1:]} "{snippet(text, 70)}" does not name its concrete subject (ads, '
                                   "budget, Google, Meta, inquiries, bookings): a cold reader cannot tell what it is about", path))
            if role == "slide_1":
                title = (a["value"].get("title") or "").strip()
                for problem in slide_one_problems(title, text) if title else []:
                    out.append(finding("warning" if problem.startswith("opens on good news") else "blocking",
                                       "first_touch.slide_one", f"Carousel slide 1 {problem}", path))
    out += insider_findings(asset_list, terms if terms is not None else insider_terms())
    out += who_did_what(asset_list, attested, evidence, roster)
    return out
