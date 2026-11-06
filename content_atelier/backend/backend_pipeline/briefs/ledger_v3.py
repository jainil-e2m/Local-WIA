"""The claims ledger of a v3 brief, built after writing (E.B23; R42 as for cards; standard 2.4a (f)).

The writer no longer cites evidence inside copy. This step reads the finished copy and settles each statement:

1. **Deterministic binding** (no model): a quotation must be in a quoted turn (bound, with the turn) or in Whitney's belief
   statements (WIA's view in her words); every figure must be stated in a turn (bound, with a numeric fact quoted from
   it); a sentence whose content words overlap a turn's by at least the card ledger's 0.6 is bound to that turn. A
   figure found nowhere is unsupported; words in quotation marks found nowhere go to the verifier, which tells an invented
   quote from a phrase nobody is said to have said. Questions, asks and greetings are not statements.
2. **The verifier** (a model from another family than the writer's, as R42 does for cards) judges what the binding could
   not settle: supported or paraphrased by named turns, unsupported, WIA's view, or a WIA team member's attributed
   experience (E.B26), with an optional flag (overclaim, tense, misattribution and the rest, as the card verifier).
   Two verdicts never pass silently (section 2.4 conditions 3 and 4): a recommendation the verifier calls WIA's view
   binds to the turns it names, else to a knowledge-base document, else is flagged for a person; and a statement whose
   words in quotation marks the rules found in no turn is flagged even when the verifier finds its point supported (the
   copy presents a paraphrase as a quotation). A phrase in quotation marks the verifier judges WIA's view, attributed to
   nobody, is not a quotation.
3. Without the verifier (not configured, or unavailable), statements that read as facts about the call stay `unchecked`
   for a person, and the rest are WIA's view.

The ledger becomes the brief's `claims` and `evidence`; v2's claim checks then run on it unchanged (validation_v2).
"""
from __future__ import annotations

import re
from typing import Literal

from ..contracts import Contract, Text
from ..cycle.verification import BELIEF_DOCUMENT, QUOTE, _tokens, figures_in, is_belief, normalise, quotes_in, speaker_entry
from ..store import canonical_hash

# v2 (E.B15, 20 October): a recommendation binds to a turn or is flagged; quoted words in no turn are flagged.
LEDGER_VERSION = "brief-ledger-2026-10-20.v2"
VERIFIER_PROFILE = "brief-verification.v1"
OVERLAP = 0.6
# A sentence ends at . ! or ?, after its closing quotation mark or bracket when it has one.
_SPLIT = re.compile(r"(?<=[.!?])\s+|(?<=[.!?][\"”’)])\s+|\n+")
_DIGITS = re.compile(r"\d+(?:\.\d+)?")
# Lines that state nothing: a greeting, a sign-off, a merge tag.
_NOT_A_STATEMENT = re.compile(r"^(?:hi|hello|hey|dear)\b|\{\{|^(?:talk soon|xo|xoxo|cheers|sincerely|warmly|best)\b|^[-–—]?\s*whitney\b"
                              r"|^(?:daniela|xo,? daniela)\b", re.I)
# An ask to the reader (a CTA): never a claim unless it carries a figure or a quote.
_ASK = re.compile(r"^(?:reply|dm|message|save|share|comment|tell|send|book|click|grab|join|follow|tap|hit|download|register|"
                  r"apply|sign up|let us know|let me know|drop|check out)\b", re.I)
# A team member speaking from their own work: "what I see in accounts like this", "in my experience" (E.B26).
FIRST_PERSON = re.compile(r"\bwhat (?:i|we) (?:see|find|notice)\b|\bin my experience\b|\bevery time (?:i|we)\b|"
                          r"\b(?:i|we) (?:always |usually |often |typically )?(?:see|find|notice)\b", re.I)
# A sentence that tells what happened on a call: a credit, a past action or a report of what someone said.
FACTUAL = re.compile(r"\b(?:said|says|asked|told|noticed|spotted|recommended|suggested|found|showed|shared|mentioned|explained|"
                     r"described|decided|changed|removed|added|built|launched|tested|ran|paused|moved|switched|saw|realised|"
                     r"realized|was|were|had|did|got|came|went|booked|called|wrote|walked|pointed|caught|flagged)\b", re.I)
# What a verifier flag may block (as the card verifier, E.B10): an unsupported fact or a misattribution.
BLOCK_KINDS = {"invented_reason", "overclaim", "tense", "misattribution"}


class VerifierFlag(Contract):
    kind: Literal["invented_reason", "overclaim", "tense", "misattribution", "frequency", "consent", "positioning", "other"]
    severity: Literal["block", "check"]
    message: Text


class VerifierStatement(Contract):
    id: Text
    verdict: Literal["supported", "paraphrase", "unsupported", "view", "attributed_experience"]
    claim_class: Literal["particular_interaction", "general_approach", "recommendation", "prevalence", "outcome",
                         "attributed_experience"]
    evidence_refs: list[str]
    knowledge_base_document: str | None
    flag: VerifierFlag | None


class VerifierOutput(Contract):
    """The verifier's answer: one verdict for each statement it was given."""
    statements: list[VerifierStatement]


def _plain(node):
    if isinstance(node, dict):
        return {k: _plain(v) for k, v in node.items() if k not in ("pattern", "minLength", "maxLength", "title")}
    return [_plain(v) for v in node] if isinstance(node, list) else node


def wire_schema() -> dict:
    """VerifierOutput's schema as sent to the verifier. Anthropic's structured output refuses the full one ("Schema is too
    complex for compilation", 20 October), so string patterns, length bounds and titles are left out; the answer is still
    validated against VerifierOutput."""
    return _plain(VerifierOutput.model_json_schema())


def copy_fields_v3(body, *, wide: bool = False) -> list[tuple[str, str, str]]:
    """The reader-facing copy of a v3 brief as (field, label for the reviewer, text). `wide` adds the narrative outline,
    the Reel beats and the Stories frames, which become copy too; jobs and the CTA rationale are directions."""
    b = body if isinstance(body, dict) else body.model_dump(mode="json")
    from .contracts_v4 import copy_fields_v4, is_v4_body
    if is_v4_body(b):
        # Contract v4 (E.B33) shares this ledger over its own copy fields.
        return copy_fields_v4(b, wide=wide)
    out = [("wia_perspective", "the WIA perspective", b["wia_perspective"])]
    out += [(f"supporting_example.{k}", "the supporting example", b["supporting_example"][k]) for k in ("scene", "wia_move", "client_contribution")]
    outline = b["narrative_outline"]
    out += [(f"narrative_outline.hooks[{i}]", f"hook {i}", h["text"]) for i, h in enumerate(outline["hooks"], 1)]
    if wide:
        out += [("narrative_outline.problems_desires_symptoms", "the problems and desires", " ".join(outline["problems_desires_symptoms"])),
                ("narrative_outline.main_point", "the main point", outline["main_point"]),
                ("narrative_outline.transformation", "the transformation", outline["transformation"]),
                ("narrative_outline.cta", "the outline's CTA", outline["cta"])]
    plan = b["format_plan"]
    for i, r in enumerate(plan.get("reels") or [], 1):
        out += [(f"format_plan.reels[{i}].cover_text", f"Reel {i}'s cover text", r["cover_text"]),
                (f"format_plan.reels[{i}].spoken_opening", f"Reel {i}'s spoken opening", r["spoken_opening"])]
        if r.get("script"):
            out += [(f"format_plan.reels[{i}].script", f"Reel {i}'s script", r["script"])]
        if wide:
            out += [(f"format_plan.reels[{i}].beats", f"Reel {i}'s beats", "\n".join(r["beats"]))]
    if plan.get("carousel"):
        out += [(f"format_plan.carousel.slides[{s['number']}].text", f"carousel slide {s['number']}", s["text"])
                for s in plan["carousel"]["slides"]]
    if plan.get("email"):
        e = plan["email"]
        out += [("format_plan.email.subject_options", "the email's subject lines", " | ".join(e["subject_options"]))]
        out += [(f"format_plan.email.{k}", f"the email's {k}", e[k]) for k in ("preview", "opening", "body", "ending")]
    if plan.get("caption"):
        out += [(f"format_plan.caption.{k}", f"the caption's {k}", plan["caption"][k]) for k in ("hook", "body", "ending")]
    if plan.get("stories") and wide:
        out += [("format_plan.stories.frames", "the Stories frames", "\n".join(plan["stories"]["frames"]))]
    return out


def _open_quote(text: str) -> bool:
    return text.count('"') % 2 == 1 or text.count("“") > text.count("”")


def sentences(text: str) -> list[str]:
    """The sentences of a text, a quotation kept whole with the sentence that introduces it."""
    out, held = [], ""
    for piece in (p.strip() for p in _SPLIT.split(text or "")):
        if not piece:
            continue
        held = f"{held} {piece}" if held else piece
        if not _open_quote(held):
            out.append(held)
            held = ""
    return out + ([held] if held else [])


def statements(body) -> list[dict]:
    """Each statement in the copy, once per field: {id, field, label, text}. Greetings, sign-offs and asks are left out."""
    out, seen = [], set()
    for field, label, text in copy_fields_v3(body, wide=True):
        for sentence in sentences(text):
            key = (field, normalise(sentence))
            if key in seen or not re.search(r"[A-Za-z]{3}", sentence) or _NOT_A_STATEMENT.search(sentence):
                continue
            if (sentence.endswith("?") or _ASK.search(sentence)) and not quotes_in(sentence) and not _DIGITS.search(sentence):
                continue
            seen.add(key)
            out.append({"id": "c_" + canonical_hash([field, normalise(sentence)])[:12], "field": field, "label": label, "text": sentence})
    return out


def _spans(excerpt: str) -> list[str]:
    return [s for s in re.split(r"(?<=[.!?])\s+|\n+", excerpt or "") if s.strip()]


def best_span(excerpt: str, text: str) -> str:
    """The sentence of an excerpt that shares most content words with the text (a verbatim part of the excerpt)."""
    words = _tokens(text)
    spans = _spans(excerpt) or [excerpt]
    return max(spans, key=lambda s: len(words & _tokens(s))).strip()


def _overlap(text: str, excerpt: str) -> float:
    words = _tokens(text)
    if len(words) < 4:  # a short line shares two words with almost any turn
        return 0.0
    return max((len(words & _tokens(s)) / len(words) for s in _spans(excerpt) or [excerpt]), default=0.0)


def _claim(statement: dict, *, status: str, settled_by: str, claim_class: str = "particular_interaction", evidence_ids=(),
           knowledge_base_document=None, numeric_facts=(), quote=None, public_quote=False, note=None, flag=None) -> dict:
    return {"claim_id": statement["id"], "text": statement["text"], "claim_class": claim_class, "evidence_ids": list(evidence_ids),
            "knowledge_base_document": knowledge_base_document, "numeric_facts": list(numeric_facts), "quote": quote,
            "public_quote": public_quote, "field": statement["field"], "status": status, "settled_by": settled_by, "note": note,
            "flag": flag}


def experience(turn: dict, roster: list[dict] | None) -> bool:
    """Whether a turn is a WIA team member's first-person observation from their own work (E.B26)."""
    entry = speaker_entry(turn.get("speaker"), roster or [])
    return bool(entry and entry["status"] in ("current", "former") and FIRST_PERSON.search(turn.get("excerpt") or ""))


def bind(statement: dict, evidence: list[dict], beliefs: dict | None, roster: list[dict] | None = None) -> dict | None:
    """The deterministic binding of one statement: a claim when the rules settle it (bound or unsupported), else None. A
    statement bound to a team member's own observation is their attributed experience (E.B26), not a claim of prevalence."""
    text = statement["text"]
    cited, facts, quote, public_quote, problems = [], [], None, False, []
    belief = unmatched = False
    for q in quotes_in(text):
        said = normalise(q)
        turn = next((e for e in evidence if said and said in normalise(e["excerpt"])), None)
        if turn:
            cited.append(turn["evidence_id"])
            # The quote as the turn writes it, so v2's check (the quote inside the excerpt) holds.
            quote, public_quote = _verbatim(turn["excerpt"], q) or q, True
        elif is_belief(q, beliefs):
            belief = True
        else:
            # Words in quotation marks the rules cannot find: an invented quote, or a question or phrase nobody is said to
            # have said. The verifier tells them apart (the 1f79f6d4 brief's 'Should we change anything yet?').
            unmatched = True
    for figure, digits in figures_in(text) + [(d, d) for d in _DIGITS.findall(text.replace(",", ""))]:
        if any(f["value"] == figure for f in facts) or any(digits in _DIGITS.findall(f["value"].replace(",", "")) for f in facts):
            continue
        turn = next((e for e in evidence if digits in _DIGITS.findall((e["excerpt"] or "").replace(",", ""))), None)
        if turn:
            source = next((s for s in _spans(turn["excerpt"]) if digits in _DIGITS.findall(s.replace(",", ""))), turn["excerpt"]).strip()
            unit = figure[len(re.match(r"\$?\s?[\d,.]+\s*%?", figure).group(0)):].strip() if re.match(r"\$?\s?[\d,.]+", figure) else ""
            facts.append({"value": figure, "unit": unit or "as stated", "timeframe": "as stated on the call",
                          "subject": text[:160], "evidence_id": turn["evidence_id"], "source_quote": source})
            cited.append(turn["evidence_id"])
        else:
            problems.append(f'states "{figure}", which is not in the call')
    if problems:
        return _claim(statement, status="unsupported", settled_by="deterministic", evidence_ids=dict.fromkeys(cited),
                      note="; ".join(dict.fromkeys(problems)))
    if unmatched:
        # Left for the verifier, with what the rules did bind (a figure's numeric fact) kept for its verdict.
        statement["bound_facts"], statement["bound_evidence"] = facts, list(dict.fromkeys(cited))
        statement["unmatched_quote"] = True
        return None
    if not cited:
        turn = max(evidence, key=lambda e: _overlap(text, e["excerpt"]), default=None)
        if turn and _overlap(text, turn["excerpt"]) >= OVERLAP:
            cited.append(turn["evidence_id"])
    if cited:
        turns = [e for e in evidence if e["evidence_id"] in cited]
        klass = "attributed_experience" if turns and all(experience(e, roster) for e in turns) else "particular_interaction"
        return _claim(statement, status="bound", settled_by="deterministic", claim_class=klass, evidence_ids=dict.fromkeys(cited),
                      numeric_facts=facts, quote=quote, public_quote=public_quote)
    if belief:
        return _claim(statement, status="bound", settled_by="deterministic", claim_class="general_approach",
                      knowledge_base_document=BELIEF_DOCUMENT)
    return None


def _verbatim(excerpt: str, quote: str) -> str | None:
    """The quoted words as the excerpt writes them (case and punctuation), when they are there."""
    target = normalise(quote)
    words = (excerpt or "").split()
    for i in range(len(words)):
        for j in range(i + 1, len(words) + 1):
            candidate = normalise(" ".join(words[i:j]))
            if candidate == target:
                return " ".join(words[i:j])
            if len(candidate) > len(target):
                break
    return None


def looks_factual(text: str) -> bool:
    return bool(FACTUAL.search(text) or QUOTE.search(text))


def deterministic(body, evidence: list[dict], beliefs: dict | None, roster: list[dict] | None = None,
                  attested=()) -> tuple[list[dict], list[dict]]:
    """(claims the rules settled, statements left for the verifier). A statement the call does not settle that says what
    an approver attested at a gate is settled by that person (R57, 5.B7)."""
    settled, open_ = [], []
    for s in statements(body):
        claim = bind(s, evidence, beliefs, roster)
        if attested and (claim is None or claim["status"] == "unsupported"):
            claim = attest(s, attested) or claim
        (settled if claim else open_).append(claim or s)
    return settled, open_


# Attested facts (R57, 5.B7) ---------------------------------------------------------------------------------------
# A fact an approver states at a gate is evidence: it enters the ledger as `attested`, with the person and the date, and a
# statement of the copy that says what it says is settled by it. A paraphrase of a client's words supports a statement the
# same way, but is never quoted: a statement with quotation marks is never settled by an attestation, and checks_v3 blocks
# copy that puts a paraphrase in quotation marks.
ATTESTED_KINDS = ("attested_fact", "paraphrase")


def attestation(item: dict) -> dict:
    return {"kind": item["kind"], "context_id": item["id"], "by": item["author"], "on": str(item["created_at"])[:10]}


def attested_note(item: dict) -> str:
    what = "A paraphrase of the client's words" if item["kind"] == "paraphrase" else "A fact"
    return f"{what} attested at a gate by {item['author']} on {str(item['created_at'])[:10]}"


def attest(statement: dict, items) -> dict | None:
    """The attested claim for a statement that says what an attested item says: at least two of its content words and
    OVERLAP of them are the item's, and any figure it states is in the item. None otherwise."""
    text = statement["text"]
    if quotes_in(text):
        return None
    words = _tokens(text)
    figures = set(_DIGITS.findall(text.replace(",", "")))
    for item in items:
        if item.get("kind") not in ATTESTED_KINDS:
            continue
        shared = words & _tokens(item["text"])
        if len(shared) >= 2 and len(shared) / len(words) >= OVERLAP and figures <= set(_DIGITS.findall(item["text"].replace(",", ""))):
            return {**_claim(statement, status="attested", settled_by="person", note=attested_note(item)),
                    "attested": attestation(item)}
    return None


def attested_entries(items) -> list[dict]:
    """Each attested fact and paraphrase as its own ledger entry, so the ledger shows who stated it and when."""
    return [{**_claim({"id": "a_" + canonical_hash(["attested", item["id"]])[:12], "field": "context_items", "text": item["text"]},
                      status="attested", settled_by="person", note=attested_note(item)), "attested": attestation(item)}
            for item in items if item.get("kind") in ATTESTED_KINDS]


def field_path(field: str, body: dict | None) -> str:
    """A ledger field as a path into the body (briefs/paths.py): the ledger numbers Reels and hooks from 1 and slides by
    their number; a path counts list items from 0."""
    m = re.match(r"^format_plan\.carousel\.slides\[(\d+)\](.*)$", field)
    if m:
        slides = (((body or {}).get("format_plan") or {}).get("carousel") or {}).get("slides") or []
        index = next((i for i, s in enumerate(slides) if s.get("number") == int(m.group(1))), None)
        return "format_plan.carousel.slides" if index is None else f"format_plan.carousel.slides[{index}]{m.group(2)}"
    m = re.match(r"^(narrative_outline\.hooks|format_plan\.reels)\[(\d+)\]", field)
    if m:
        return f"{m.group(1)}[{int(m.group(2)) - 1}]" + field[m.end():]
    return field


def _edited(field: str, person_fields, body: dict | None) -> bool:
    """Whether a person's edit touched the field: an edited path inside it or around it (a whole section, as before)."""
    from .paths import touched
    try:
        return touched(field_path(field, body), person_fields)
    except ValueError:
        return field.split(".")[0] in person_fields


# The verifier -----------------------------------------------------------------------------------------------------

def verifier_packet(open_statements: list[dict], evidence: list[dict], roster: list[dict], approved: dict) -> tuple[dict, dict[str, str]]:
    """(the verifier's user message, the evidence references) for the one verification call over a brief's unsettled
    statements. Turns are referred to as E1, E2, ... so no evidence identifier reaches the model."""
    refs = {e["evidence_id"]: f"E{i}" for i, e in enumerate(evidence, 1)}

    def who(speaker):
        entry = speaker_entry(speaker, roster)
        if not entry:
            return "client or prospect"
        return f"WIA, {entry['role']}" + (", former team member" if entry["status"] == "former" else "")
    packet = {"approved_angle": approved,
              "turns": [{"ref": refs[e["evidence_id"]], "speaker": e.get("speaker"), "who": who(e.get("speaker")), "text": e["excerpt"]}
                        for e in evidence],
              "statements": [{"id": s["id"], "where": s["label"], "text": s["text"]} for s in open_statements]}
    return packet, refs


class VerifierSkipped(Exception):
    """The verifier did not run (not configured from another family, or unavailable outside replay); the ledger keeps
    what the rules settled and leaves the rest for a person."""


def merge(open_statements: list[dict], output: dict | None, refs: dict[str, str], kb_keys: set[str], model: str | None) -> tuple[list[dict], list[str]]:
    """Claims from the verifier's verdicts, and the statements it judged WIA's view without a flag (kept by text, so a
    rebuild need not ask again). Without an output, factual-looking statements stay unchecked for a person; a statement
    the verifier left out is treated the same way, and a verdict for a statement it was not given is ignored."""
    by_ref = {r: i for i, r in refs.items()}
    verdicts = {v["id"]: v for v in (output or {}).get("statements", [])}
    claims, views = [], []
    for s in open_statements:
        v = verdicts.get(s["id"])
        if v is None:
            if looks_factual(s["text"]):
                claims.append(_claim(s, status="unchecked", settled_by="none", note="The verifier did not check it"))
            else:
                views.append(normalise(s["text"]))
            continue
        ids = list(dict.fromkeys([*s.get("bound_evidence", []), *(by_ref[r] for r in v["evidence_refs"] if r in by_ref)]))
        facts = s.get("bound_facts", [])
        doc = v["knowledge_base_document"] if v["knowledge_base_document"] in kb_keys else None
        flag = v["flag"]
        if flag:
            severity = flag["severity"] if flag["kind"] in BLOCK_KINDS or flag["kind"] == "consent" else "check"
            # E.B26: a team member's own observation is attributed experience; a frequency flag never blocks it.
            if v["verdict"] == "attributed_experience" and flag["kind"] == "frequency":
                severity = "check"
            flag = {"kind": flag["kind"], "severity": severity, "message": flag["message"], "source": model}
        if v["verdict"] == "unsupported" or flag and flag["severity"] == "block" and flag["kind"] in BLOCK_KINDS:
            claims.append(_claim(s, status="unsupported", settled_by="verifier", claim_class=v["claim_class"], evidence_ids=ids,
                                 note=(flag or {}).get("message") or "The verifier found no support in the call", flag=flag))
        elif v["verdict"] in ("supported", "paraphrase", "attributed_experience"):
            klass = "attributed_experience" if v["verdict"] == "attributed_experience" else v["claim_class"]
            if s.get("unmatched_quote"):
                # Condition 4: words in quotation marks the rules found in no turn are not the call's words, even when the
                # verifier finds the point supported. The copy presents a paraphrase as a quotation: a person's look.
                flag = _with_check(flag, UNBOUND_QUOTE, model)
            if not ids:
                # A verdict of support names its turns; without them a person checks it.
                claims.append(_claim(s, status="unchecked", settled_by="verifier", claim_class=klass, flag=flag,
                                     note="The verifier named no turn for it"))
            else:
                claims.append(_claim(s, status="supported", settled_by="verifier", claim_class=klass, evidence_ids=ids,
                                     knowledge_base_document=doc, numeric_facts=facts, flag=flag))
        elif v["claim_class"] == "recommendation" and not doc:
            # Condition 3: a recommendation binds to the turn where WIA made it, or is flagged for a person; it never
            # passes as an unrecorded view.
            claims.append(_claim(s, status="supported", settled_by="verifier", claim_class="recommendation", evidence_ids=ids,
                                 numeric_facts=facts, flag=flag if ids else _with_check(flag, UNBOUND_RECOMMENDATION, model)))
        elif doc or flag:
            # WIA's view: recorded as a claim when it cites the document that states it, or when the verifier flagged it.
            claims.append(_claim(s, status="supported", settled_by="verifier", claim_class="general_approach" if doc else "recommendation",
                                 evidence_ids=ids if facts else [], knowledge_base_document=doc, numeric_facts=facts, flag=flag))
        else:
            views.append(normalise(s["text"]))
    return claims, views


UNBOUND_QUOTE = "Its words in quotation marks are in no turn of the call: quote the turn exactly, or drop the quotation marks"
UNBOUND_RECOMMENDATION = ("A recommendation that cites neither a turn of the call nor a knowledge-base document: check it is "
                          "WIA's practice before publishing")


def _with_check(flag: dict | None, message: str, model: str | None) -> dict:
    """A flag for a person's look: the verifier's own flag with the message added, or a new check."""
    if flag:
        return {**flag, "message": f'{flag["message"]}. {message}'}
    return {"kind": "other", "severity": "check", "message": message, "source": model}


def evidence_refs(claims: list[dict], evidence: list[dict]) -> list[dict]:
    """The quoted turns the ledger cites, each once, quoting the part of the turn closest to what cites it."""
    turns = {e["evidence_id"]: e for e in evidence}
    out = {}
    for c in claims:
        for i in c["evidence_ids"]:
            if i in turns and i not in out:
                e = turns[i]
                out[i] = {"evidence_id": i, "speaker": e.get("speaker"), "start_ms": e.get("start_ms"),
                          "quote": c["quote"] if c["quote"] and normalise(c["quote"]) in normalise(e["excerpt"]) else best_span(e["excerpt"], c["text"])}
    return list(out.values())


def carry(open_statements: list[dict], previous: list[dict], views: list[str], *, person_fields: set[str] = frozenset(),
          body: dict | None = None) -> tuple[list[dict], list[dict], list[str]]:
    """Reuse earlier verdicts for statements whose text is unchanged (a repair or an edit rebuilds the ledger).

    A statement the verifier found unsupported that a person kept, in a field they edited (a path, or a whole section), is
    the person's: it becomes `kept_by_person` (a warning), never silently cleared; an unsupported line beside the edited
    one keeps its verdict. Attestations are not carried: they are settled again from the attested items on every build.
    Returns (carried claims, statements still open, views kept)."""
    earlier = {normalise(c["text"]): c for c in previous if c.get("status") != "attested"}
    seen_views = set(views)
    carried, still, kept_views = [], [], []
    for s in open_statements:
        key = normalise(s["text"])
        c = earlier.get(key)
        if c and c["settled_by"] in ("verifier", "person"):
            if c["status"] == "unsupported" and _edited(s["field"], person_fields, body):
                carried.append({**c, "claim_id": s["id"], "field": s["field"], "status": "kept_by_person", "settled_by": "person",
                                "note": "Kept by a person after the verifier found no support: " + (c.get("note") or "")})
            else:
                carried.append({**c, "claim_id": s["id"], "field": s["field"]})
        elif key in seen_views:
            kept_views.append(key)
        else:
            still.append(s)
    return carried, still, kept_views
