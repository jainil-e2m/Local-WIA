"""The deterministic checks of a content pack (NP.B4; the content-packs plan, section 4.3).

They run on the pack's v4-shaped body (`model.v4_body`: the approved brief's strategy with the pack's pieces as its format
plan) when finalize opens the pack and after every edit, revert and attestation; the result is stored with the version
(`validation_result`) and recomputed on every read. Each finding has the `PackFindingV2` shape: source `check`, a stable
id (a hash of the check, the piece, the path and the message), status `open`, and the piece and path it points at.

- **The brief's checks, unchanged:** the first-touch rules (insider terms block; the rest warn, as at Gate 2), the asset
  checks (outcome verbs and hook fidelity block), anchored on the hand-off's anchor, and consent and names
  (`public_copy_checks`, `copy_quote_checks`): a person is named only when WIA staff, when the client consented to be named
  (`may_name`), or with a clearance. Only what the pack's copy raises is reported: a consent finding the brief's own approved
  copy raises too was settled at Gate 2, and findings on the brief's strategy lines are the brief's.
- **Identities (N8, 1.B12's extension):** a person or account never to be named, or a marker of the published work one must
  never be linked to, blocks wherever it is in the pack's copy, the brief's approved copy included: no consent, clearance,
  approval or lock overrides it (`identity_findings`); a wrong pronoun beside a named person warns. The records are those
  frozen with the pack run when it was queued (`pack_identities`); a run queued before them reads the current ones.
- **New for packs:**
  - quotes exact and attributed (blocking): every quoted span in copy is the words of a turn of the call or a ledger claim's
    quote, fillers aside, and the copy credits it to the kind of speaker who said it (the client, or WIA's team);
  - no new numbers or names (blocking): every figure and every capitalised name in copy is in the brief, its claims, the
    call's evidence, the team roster, the offer descriptors or a short tools list;
  - client quote listed (a note, never a gate): every client's words in copy are listed under the pack's client quotes to
    clear before posting; `missing_client_quotes` gives finalize the entries to add;
  - composition (blocking): exactly the email, the carousel, and Reels 1 to 3 as story, stance and b-roll text, or (finisher
    v3, Round 2) as the central story and two premises of their own; a Reel not written blocks with its reason;
  - voice (warnings, Round 2): copy that praises WIA by comparing it with other agencies (WIA, 26 October: "generic agency
    put-downs"); slogans, repetition and overlapping premises are the editorial reading's (check v4), not a word list's;
  - format (warnings): slide length, caption, script and email length, b-roll screens, three subject options, a Reel's
    title not its job;
  - US spelling (warnings, a list of British forms).
- **Lines a person wrote** (a lock) are theirs: a quote, figure or name in one is a warning for them to check, never a gate,
  as Gate 2 treats a line a person kept (`kept_by_person`). A quote the approved brief already carries passed Gate 2's
  ledger and is not re-judged.
- **A client's quote** without a clearance is a before-publishing note (the client quotes), never a gate (section 4.5); Whitney's
  and the team's quoted words follow the brief's clearance, as at Gate 2.
- **The week** (`week_findings`, when `siblings` are given; computed on read, never stored): one offer CTA a week on
  Instagram; hooks, covers and subjects distinct across the week; emoji in subjects at most twice a month; no central point
  repeated within 60 days.

No model call; nothing here writes.
"""
from __future__ import annotations

import re
from datetime import timedelta

from ..briefs import paths
from ..store import canonical_hash
from . import contracts_v2 as c2
from . import model

VERSION = "pack_checks.v1"
REEL_KEYS = ("reel_1", "reel_2", "reel_3")
KIND_WORDS = {"story": "story", "stance": "stance", "broll_text": "b-roll text", "central": "central story",
              "second": "second premise", "third": "third premise"}
# Copy that compares WIA with other agencies (Round 2; WIA asked for explanations of WIA's own decisions instead).
AGENCY_COMPARISON = re.compile(
    r"\b(?:most|other|many|typical|traditional|a lot of|some)\s+(?:ads?\s+|advertising\s+|marketing\s+)?agencies\b"
    r"|\bunlike (?:most|other|many|a lot of)\b"
    r"|\b(?:expect|hear|get) from an?\s+(?:ads?\s+|advertising\s+|marketing\s+)?agency\b"
    r"|\bmost (?:ads?|advertising|marketing) (?:teams|companies|partners|people)\b", re.I)

# Words a quote may drop or keep without changing what was said (section 4.3: "fillers allowed").
FILLERS = frozenset("um umm uh uhh erm er ah oh like so well just actually basically literally really okay ok yeah right".split())
MULTI_FILLER = re.compile(r"\b(?:you know|i mean|kind of|sort of)\b")
ELLIPSIS = re.compile(r"\.\.\.|…|\[\.\.\.\]")
SAYS = r"(?:said|says|told|tells|asked|asks|explained|explains|wrote|writes|replied|admitted|mentioned|shared|added|put it)"
_WHO = (r"she|he|they|the (?:client|owner|couple|bride|groom|member|prospect|venue owner)|our (?:client|member)|"
        r"one (?:owner|client)|i|we|our (?:strategist|team)|whitney")
CREDIT_BEFORE = re.compile(r"\b(?P<who>" + _WHO + r")\b(?:\s+\w+){0,2}?\s+" + SAYS + r"\b", re.I)
CREDIT_AFTER = re.compile(r"\b" + SAYS + r"\s+(?P<who>" + _WHO + r")\b", re.I)
WIA_WHO = re.compile(r"^(?:i|we|our (?:strategist|team)|whitney)$", re.I)
FIGURE = re.compile(r"\$?\d[\d,]*(?:\.\d+)?%?")
NAME = re.compile(r"(?<![\w'’])([A-Z][A-Za-z]+)(?:['’]s)?(?![\w])")
SENTENCE_START = set(".!?:;\"“”‘'([—–-•*…\n")
# Platforms and tools a cold reader knows, which copy may name though no call does (section 4.3).
TOOLS = frozenset("""google meta facebook instagram canva chatgpt openai claude gemini tiktok youtube pinterest zoom gmail outlook
excel calendly honeybook dubsado squarespace wordpress wix shopify mailchimp flodesk kajabi linkedin threads ai gpt iphone
android apple microsoft yelp knot weddingwire zola leadlock""".split())
COMMON_NAMES = frozenset("""i ok okay hi hey dm dms ps faq ads cta seo ppc roi crm us usa monday tuesday wednesday thursday friday
saturday sunday january february march april may june july august september october november december reel reels""".split())
# British forms and their US spelling (section 4.3). Only whole words; "advertise", "expertise" and the like are US too.
BRITISH = {
    "colour": "color", "colours": "colors", "favour": "favor", "favourite": "favorite", "favourites": "favorites",
    "behaviour": "behavior", "behaviours": "behaviors", "honour": "honor", "labour": "labor", "neighbour": "neighbor",
    "organise": "organize", "organised": "organized", "organising": "organizing", "organisation": "organization",
    "organisations": "organizations", "realise": "realize", "realised": "realized", "realising": "realizing",
    "recognise": "recognize", "recognised": "recognized", "prioritise": "prioritize", "prioritised": "prioritized",
    "optimise": "optimize", "optimised": "optimized", "optimising": "optimizing", "optimisation": "optimization",
    "analyse": "analyze", "analysed": "analyzed", "analysing": "analyzing", "apologise": "apologize", "personalise": "personalize",
    "personalised": "personalized", "customise": "customize", "customised": "customized", "minimise": "minimize",
    "maximise": "maximize", "summarise": "summarize", "emphasise": "emphasize", "specialise": "specialize",
    "specialised": "specialized", "centre": "center", "centres": "centers", "theatre": "theater", "metre": "meter",
    "travelled": "traveled", "travelling": "traveling", "cancelled": "canceled", "cancelling": "canceling",
    "modelling": "modeling", "labelled": "labeled", "enrol": "enroll", "enrolment": "enrollment", "licence": "license",
    "defence": "defense", "offence": "offense", "programme": "program", "programmes": "programs", "cheque": "check",
    "grey": "gray", "judgement": "judgment", "ageing": "aging", "whilst": "while", "amongst": "among", "learnt": "learned",
    "spelt": "spelled", "enquiry": "inquiry", "enquiries": "inquiries", "enquire": "inquire", "mum": "mom",
    "catalogue": "catalog", "fulfil": "fulfill", "jewellery": "jewelry", "practise": "practice", "storey": "story",
}
_BRITISH = re.compile(r"\b(" + "|".join(sorted(BRITISH, key=len, reverse=True)) + r")\b", re.I)
EMOJI = re.compile("[\U0001F300-\U0001FAFF\U0001F000-\U0001F2FF☀-➿⭐⬆↔-↪]")
OFFER_ASK = re.compile(r"\bDM\b[^.?!\n]{0,40}?[\"“]?\b(?:ADS|ELEVATE|AUDIT)\b|\bapply (?:now|today|here)\b|\bjoin the (?:\w+ )?waitlist\b")


# ---- the shape of a finding --------------------------------------------------------------------------------------

def finding(check: str, severity: str, message: str, piece: str | None = None, path: str | None = None,
            sentence: str | None = None) -> dict:
    return {"finding_id": "check_" + canonical_hash([check, piece, path, message])[:16], "source": "check", "check": check,
            "piece": piece, "path": path, "sentence": sentence, "severity": severity, "message": message, "status": "open",
            "resolution": None, "can_attest": False}


def snippet(text: str, n: int = 80) -> str:
    text = " ".join((text or "").split())
    return text if len(text) <= n else text[:n - 3].rstrip() + "..."


def _cap(text: str) -> str:
    return text[:1].upper() + text[1:]


# ---- reading a pack ---------------------------------------------------------------------------------------------

def bodies_of(pieces) -> dict[str, dict]:
    """The piece envelopes by key, from piece rows (`model.pieces`), a list of rows, or the envelopes themselves."""
    if isinstance(pieces, list):
        pieces = {r["slot_key"]: r for r in pieces}
    out = {}
    for key, value in (pieces or {}).items():
        out[key] = (value.get("content_body") if isinstance(value, dict) and "slot_key" in value else value) or {}
    return out


def copy_lines(key: str, content: dict | None) -> list[tuple[str, str, str]]:
    """(path relative to the piece's content, label, text) for every copy line of a piece; direction (job, beats, send
    header, read time) is not copy."""
    if not content:
        return []
    label, channel, out = c2.LABELS[key], c2.CHANNEL[key], []

    def add(path, what, text):
        if isinstance(text, str) and text.strip():
            out.append((path, f"{label}'s {what}", text))
    if channel == "email":
        for j, s in enumerate(content.get("subject_options") or []):
            add(f"subject_options[{j}]", f"subject line {j + 1}", s)
        for k in ("preview", "opening", "body", "ending"):
            add(k, k, content.get(k))
        return out
    add("title", "title", content.get("title"))
    if channel == "reel":
        add("cover_text", "cover", content.get("cover_text"))
        for j, s in enumerate(content.get("cover_alternates") or []):
            add(f"cover_alternates[{j}]", f"cover alternate {j + 1}", s)
        add("on_screen_hook", "on-screen hook", content.get("on_screen_hook"))
        add("spoken_opening", "spoken opening", content.get("spoken_opening"))
        add("script", "script", content.get("script"))
        for j, s in enumerate(content.get("screens") or []):
            add(f"screens[{j}]", f"screen {j + 1}", s)
    else:
        for j, s in enumerate(content.get("slides") or []):
            add(f"slides[{j}].text", f"slide {s.get('number', j + 1)}", s.get("text"))
    caption = content.get("caption") or {}
    for k in ("hook", "body", "ending"):
        add(f"caption.{k}", f"caption {k}", caption.get(k))
    add("no_offer_ending", "no-offer ending", content.get("no_offer_ending"))
    return out


def piece_text(key: str, content: dict | None) -> str:
    """A piece's copy as text, in reading order: what the published-final difference is measured against."""
    return "\n".join(text for _, _, text in copy_lines(key, content))


def person_paths(piece: dict) -> list[str]:
    return [lock["path"] for lock in piece.get("locks") or []]


def _by_person(path: str, locked: list[str]) -> bool:
    try:
        return any(paths.overlaps(path, p) for p in locked)
    except ValueError:
        return False


def _brief_parts(brief_row: dict) -> tuple[dict, dict, dict, dict]:
    content = brief_row["content_body"]
    document = content["document"]
    return document["body"], document["header"], content.get("provenance") or {}, (content.get("review") or {}).get("clearances") or {}


def _strings(value) -> list[str]:
    return [v for _, v in paths.leaves(value) if isinstance(v, str)]


def _normalise(text: str) -> str:
    from ..cycle.verification import normalise
    return normalise(text)


def _tokens(text: str) -> list[str]:
    words = [w for w in _normalise(MULTI_FILLER.sub(" ", _normalise(text))).replace("'", "").split() if w not in FILLERS]
    return [w for i, w in enumerate(words) if i == 0 or w != words[i - 1]]


def _matches(quote: str, source: list[str]) -> bool:
    """Whether a quoted span is the source's words in order: each part between ellipses a run of the source's words,
    fillers and stutters aside."""
    segments = [s for s in (_tokens(p) for p in ELLIPSIS.split(quote)) if s]
    pos = 0
    for seg in segments:
        found = next((i for i in range(pos, len(source) - len(seg) + 1) if source[i:i + len(seg)] == seg), None)
        if found is None:
            return False
        pos = found + len(seg)
    return bool(segments)


def speaker_class(speaker: str | None, roster) -> str | None:
    """`wia` for a team member on the roster (current or former), `client` for anyone else, None when unknown."""
    if not (speaker or "").strip():
        return None
    from ..cycle.verification import speaker_entry
    entry = speaker_entry(speaker, roster or [])
    return "wia" if entry and entry.get("status") in ("current", "former") else "client"


def quote_sources(brief_row: dict) -> list[dict]:
    """What a quote in copy may be: a turn of the call, a quoted turn of the brief, or a ledger claim's quote."""
    body, _, provenance, _ = _brief_parts(brief_row)
    roster = provenance.get("roster") or []
    evidence = {e["evidence_id"]: e for e in brief_row.get("selected_evidence") or []}
    out = [{"tokens": _tokens(e.get("excerpt")), "speaker": e.get("speaker"), "evidence_id": e["evidence_id"]} for e in evidence.values()]
    for ref in body.get("evidence") or []:
        speaker = ref.get("speaker") or (evidence.get(ref.get("evidence_id")) or {}).get("speaker")
        out.append({"tokens": _tokens(ref.get("quote")), "speaker": speaker, "evidence_id": ref.get("evidence_id")})
    for claim in body.get("claims") or []:
        if claim.get("quote"):
            cited = next((evidence[i] for i in claim.get("evidence_ids") or [] if i in evidence), {})
            out.append({"tokens": _tokens(claim["quote"]), "speaker": cited.get("speaker"), "evidence_id": cited.get("evidence_id")})
    for source in out:
        source["class"] = speaker_class(source["speaker"], roster)
    return [s for s in out if s["tokens"]]


def _quotes(text: str) -> list[str]:
    from ..cycle.verification import quotes_in
    return list(dict.fromkeys(quotes_in(text or "")))


def _sentence_of(text: str, quoted: str) -> str:
    from ..briefs.first_touch import sentences
    return next((s for s in sentences(text) if quoted in s), text)


def credited(sentence: str, quoted: str) -> str | None:
    """Who the copy says spoke the quoted words: `wia`, `client`, or None when it names no one."""
    outside = sentence.replace(quoted, " ")
    from ..briefs.first_touch import without_quotes
    outside = without_quotes(outside)
    m = CREDIT_BEFORE.search(outside) or CREDIT_AFTER.search(outside)
    if not m:
        return None
    return "wia" if WIA_WHO.match(m.group("who").strip()) else "client"


# ---- the brief's checks on the pack -------------------------------------------------------------------------------

_PLAN = re.compile(r"^format_plan\.(?:reels\[(\d+)\]|(carousel|email))(?:\.(.+)|(\[.+))?$")
_REEL_LABEL = re.compile(r"\bReel ([1-3])\b")


def written_reels(bodies: dict[str, dict]) -> list[str]:
    """The pack's Reels in the order the v4-shaped body lists them (written ones only, model.v4_format_plan)."""
    return [k for k in REEL_KEYS if (bodies.get(k) or {}).get("content")]


def locate(field: str | None, reels: list[str]) -> tuple[str | None, str | None]:
    """A brief check's field (`format_plan.reels[1].cover_text`, 0-based) as (pack piece key, path in its content)."""
    m = _PLAN.match(field or "")
    if not m:
        return None, None
    if m.group(1) is not None:
        index = int(m.group(1))
        if index >= len(reels):
            return None, None
        piece = reels[index]
    else:
        piece = m.group(2)
    return piece, (m.group(3) or m.group(4) or None)


def relabel(message: str, reels: list[str]) -> str:
    """A brief check numbers the Reels it was given; with a Reel not written those numbers are not the pack's."""
    labels = {str(i + 1): c2.LABELS[k] for i, k in enumerate(reels)}
    return _REEL_LABEL.sub(lambda m: labels.get(m.group(1), m.group(0)), message)


def anchor_key(brief_row: dict, bodies: dict[str, dict], reels: list[str], pack_body: dict | None = None) -> str:
    """The anchor as the v4-shaped body's asset key: the pack body's `anchor` (the pack key finished first, remapped from the
    brief's anchor by assemble) when it has one, else the hand-off's anchor found by each piece's `brief_key`; the first
    Reel when neither is found."""
    pack_key = (pack_body or {}).get("anchor")
    if pack_key not in c2.PIECE_KEYS:
        from ..briefs.handoff import anchor_of
        try:
            brief_key = anchor_of(brief_row)["key"]
        except (KeyError, TypeError, ValueError):
            brief_key = None
        pack_key = next((k for k, b in bodies.items() if brief_key and b.get("brief_key") == brief_key), None)
    if pack_key in reels:
        return f"reel_{reels.index(pack_key) + 1}"
    return pack_key if pack_key in ("carousel", "email") else "reel_1"


def brief_check_findings(v4: dict, brief_row: dict, bodies: dict[str, dict], pack_body: dict | None = None) -> list[dict]:
    """The first-touch rules and the asset checks on the v4-shaped pack body, as pack findings on their pieces."""
    from ..briefs.asset_checks import asset_findings
    from ..briefs.first_touch import first_touch_findings, insider_terms, offer_descriptors
    from ..briefs.validation_v4 import attested_entries
    body, header, provenance, _ = _brief_parts(brief_row)
    evidence = brief_row.get("selected_evidence") or []
    roster = provenance.get("roster") or []
    attested = attested_entries(body)
    reels = written_reels(bodies)
    raw = first_touch_findings(v4, terms=insider_terms(provenance), attested=attested, evidence=evidence, roster=roster)
    raw += asset_findings(v4, pillar=header.get("purpose"), channels=set(header.get("channels") or ()), evidence=evidence,
                          roster=roster, attested=attested, offers=offer_descriptors(provenance),
                          anchor_key=anchor_key(brief_row, bodies, reels, pack_body))
    out = []
    for f in raw:
        piece, path = locate(f.get("field"), reels)
        if piece is None and (f.get("field") or "") not in ("format_plan", "format_plan.reels"):
            continue  # a finding on the brief's strategy lines is the brief's, settled at Gate 2
        out.append(finding(f.get("check") or "brief", f["severity"], relabel(f["message"], reels), piece, path))
    return out


def _consent_run(body_v4: dict, doc, dossier, provenance, names_ok: dict, quotes_ok: dict, rules) -> list[dict]:
    from ..briefs.contracts_v4 import copy_fields_v4
    from ..briefs.validation_v2 import _collector, copy_quote_checks, lint_fields, public_copy_checks
    found: list[dict] = []
    # What a pack publishes: its copy, never the direction beside it (a Reel's beats are notes for the maker). Judging the
    # beats raised a blocker no one could edit in the pack (found by NP.X3: a beat "with no results").
    copy = copy_fields_v4(body_v4)
    email = (body_v4.get("format_plan") or {}).get("email") or {}
    email_text = " ".join([*(email.get("subject_options") or []), *(email.get(k) or "" for k in ("preview", "opening", "body", "ending"))])
    public_copy_checks(found, doc.body, doc.header, dossier, provenance, names_ok, rules, public="\n".join(t for _, _, t in copy),
                       copy=copy, lint=lint_fields(copy_fields_v4(body_v4)), email_text=email_text, identity_checks=False)
    add, block = _collector(found)
    copy_quote_checks(add, block, copy, dossier, quotes_ok)
    # A quotation no turn says is the pack's own blocking check (quotes exact and attributed), not this warning.
    return [f for f in found if "no turn of the call says it" not in f["message"]]


def pack_identities(conn, brief_row: dict) -> dict:
    """The identity records a pack run's checks read, frozen with the run when it is queued: the people and accounts of the
    brief's evidence calls and every identity never to be named or linked (`identities.notes`), and the ones its evidence is
    built on, so a never-link marker is caught when the copy leaves the name out."""
    from .. import identities
    docs = sorted({e.get("transcript_id") for e in brief_row.get("selected_evidence") or [] if e.get("transcript_id")})
    found = identities.notes(conn, document_ids=docs)
    return {"identities": found, "identity_ids": sorted(identities.ids_for(found, document_ids=docs, conn=conn))}


def frozen_identities(conn, pack_row: dict | None, brief_row: dict) -> tuple[list[dict], list[str]]:
    """The pack run's frozen identity records; for a run queued before they were frozen, the brief's own (writer v5.2), else
    the current ones (without a database, the brief's only)."""
    run_id = (pack_row or {}).get("production_run_id")
    if conn is not None and run_id:
        row = conn.execute("SELECT input_refs FROM pipeline_runs WHERE run_id=%s", (run_id,)).fetchone()
        refs = (row or {}).get("input_refs") or {}
        if refs.get("identities") is not None:
            return refs["identities"], refs.get("identity_ids") or []
    provenance = _brief_parts(brief_row)[2]
    if provenance.get("identities") or conn is None:
        return provenance.get("identities") or [], provenance.get("identity_ids") or []
    current = pack_identities(conn, brief_row)
    return current["identities"], current["identity_ids"]


def identity_findings(conn, pack_row: dict | None, v4: dict, brief_row: dict, bodies: dict[str, dict]) -> list[dict]:
    """Never-name and never-link on the pack's copy (blocking) and a wrong pronoun beside a named person (a warning). Never
    discounted as the brief's own: a brief approved before the records existed may carry a name they forbid."""
    found, built_on = frozen_identities(conn, pack_row, brief_row)
    if not found:
        return []
    from ..briefs.contracts_v4 import copy_fields_v4
    from ..briefs.ledger_v3 import field_path
    from ..identities import copy_findings, pronoun_findings
    copy = copy_fields_v4(v4)
    labels, fields = {f: label for f, label, _ in copy}, {f: text for f, _, text in copy if text}
    reels = written_reels(bodies)
    out = []
    for severity, raised in (("blocking", copy_findings(fields, found, evidence_ids=built_on, where="the pack's copy")),
                             ("warning", pronoun_findings(fields, found, where="the pack's copy"))):
        for f in raised:
            piece, path = locate(field_path(f["field"], v4), reels)
            out.append(finding("consent.names", severity, relabel(f"{f['message']} (in {labels[f['field']]})", reels), piece, path))
    return out


def _find(bodies: dict[str, dict], needle: str) -> tuple[str | None, str | None]:
    if not needle:
        return None, None
    for key in c2.PIECE_KEYS:
        for path, _, text in copy_lines(key, (bodies.get(key) or {}).get("content")):
            if needle in text:
                return key, path
    return None, None


def consent_findings(conn, v4: dict, brief_row: dict, bodies: dict[str, dict], *, consent=None, rules=None) -> list[dict]:
    """Consent and names (blocking) and the copy lint, on what the pack's copy raises beyond the brief's approved copy."""
    from pydantic import ValidationError
    from ..briefs.contracts_v4 import BriefDocumentV4
    from ..briefs.gate_two import dossier as dossier_of
    from ..briefs.ledger_v3 import field_path
    body, _, provenance, clearances = _brief_parts(brief_row)
    try:
        doc = BriefDocumentV4.model_validate(brief_row["content_body"]["document"])
        dossier = dossier_of(brief_row)
    except (ValidationError, KeyError, TypeError) as exc:
        return [finding("consent.names", "blocking", f"Consent and names could not be checked: the approved brief could not be read ({type(exc).__name__})")]
    if rules is None:
        from ..briefs.rules import pinned_rules
        rules, _ = pinned_rules(conn, provenance)
    consent = consent if consent is not None else evidence_consent(conn, brief_row)
    roster = provenance.get("roster") or []
    # A client who consented to be named may be named (section 4.3); a client's quote is a note for whoever posts, never a
    # gate (section 4.5), so it needs no clearance here; the team's quoted words keep the brief's clearance.
    names_ok = {**clearances, **{eid: {"client_consent": "may_name"} for eid, level in consent.items() if level == "may_name"}}
    quotes_ok = {**names_ok, **{e.evidence_id: {"client_quote": "before publishing"} for e in dossier.evidence
                                if speaker_class(e.speaker, roster) == "client"}}
    ours = _consent_run(v4, doc, dossier, provenance, names_ok, quotes_ok, rules)
    theirs = {(f["severity"], f["message"]) for f in _consent_run(body, doc, dossier, provenance, names_ok, quotes_ok, rules)}
    reels = written_reels(bodies)
    out = []
    for f in ours:
        if (f["severity"], f["message"]) in theirs:
            continue
        message = relabel(f["message"], reels)
        piece, path = None, None
        if f.get("field"):
            piece, path = locate(field_path(f["field"], v4), reels)
        if piece is None:
            quoted = re.search(r'"([^"]{3,})"', f["message"])
            word = f["message"].split(" (", 1)[0] if " (" in f["message"] else None
            piece, path = _find(bodies, (quoted.group(1).rstrip(".") if quoted else None) or word)
        check = "copy.lint" if f.get("field") else "consent.names"
        out.append(finding(check, f["severity"], message, piece, path))
    return out


def evidence_consent(conn, brief_row: dict) -> dict[str, str]:
    """Each evidence item's client consent (no_use, anonymise_only, may_name, unknown), as the hand-off reads it."""
    if conn is None:
        return {}
    from ..briefs.handoff import evidence_consent as consent_of
    return {e["evidence_id"]: e["client_consent"] for e in consent_of(conn, brief_row, set())}


# ---- the checks new for packs -------------------------------------------------------------------------------------

def quote_findings(bodies: dict[str, dict], brief_row: dict, sources=None) -> list[dict]:
    """Quotes exact and attributed (blocking)."""
    sources = sources if sources is not None else quote_sources(brief_row)
    body = _brief_parts(brief_row)[0]
    approved = _tokens(" \n ".join(_strings({k: v for k, v in body.items() if k not in ("claims", "evidence")})))
    out = []
    for key in c2.PIECE_KEYS:
        piece = bodies.get(key) or {}
        locked = person_paths(piece)
        for path, label, text in copy_lines(key, piece.get("content")):
            for quoted in _quotes(text):
                if len(_tokens(quoted)) < 3 or _matches(quoted, approved):
                    continue
                said = [s for s in sources if _matches(quoted, s["tokens"])]
                severity = "warning" if _by_person(path, locked) else "blocking"
                who = "a person wrote this line; check it against the call" if severity == "warning" else None
                if not said:
                    out.append(finding("pack.quote_exact", severity,
                                       f'{_cap(label)} puts "{snippet(quoted)}" in quotation marks, but nobody says those words on '
                                       "the call: quote the call exactly, or drop the quotation marks" + (f" ({who})" if who else ""),
                                       key, path, quoted))
                    continue
                credit = credited(_sentence_of(text, quoted), quoted)
                classes = {s["class"] for s in said if s["class"]}
                if credit and classes and credit not in classes:
                    names = {"wia": "our team", "client": "the client"}
                    out.append(finding("pack.quote_attributed", severity,
                                       f'{_cap(label)} credits "{snippet(quoted)}" to {names[credit]}, but on the call '
                                       f"{' and '.join(names[c] for c in sorted(classes))} said it: keep the quote with its speaker"
                                       + (f" ({who})" if who else ""), key, path, quoted))
    return out


def _material(pack_body: dict | None) -> list[str]:
    """The call's turns behind the premise Reels (finisher v4), which the copy may draw on as it draws on the brief's."""
    return [t.get("said") or "" for turns in ((pack_body or {}).get("premise_material") or {}).values() for t in turns]


def _allowed_words(brief_row: dict, pack_body: dict | None = None) -> set[str]:
    body, header, provenance, _ = _brief_parts(brief_row)
    from ..briefs.first_touch import offer_descriptors
    texts = _strings(body) + _strings(header) + _material(pack_body)
    for e in brief_row.get("selected_evidence") or []:
        texts += [e.get("excerpt") or "", e.get("speaker") or "", e.get("title") or ""]
    for r in provenance.get("roster") or []:
        texts += [r.get("name") or "", *(r.get("aliases") or [])]
    for o in offer_descriptors(provenance):
        texts += [o.get("offer") or "", *(o.get("descriptors") or []), *(o.get("key_phrases") or [])]
    words = {w.replace("’", "'") for t in texts for w in re.findall(r"[a-z][a-z'’]*", (t or "").lower())}
    return words | {w.split("'")[0] for w in words} | TOOLS | COMMON_NAMES


def _allowed_figures(brief_row: dict, pack_body: dict | None = None) -> set[str]:
    body, header, provenance, _ = _brief_parts(brief_row)
    from ..briefs.first_touch import offer_descriptors
    texts = _strings(body) + _strings(header) + [e.get("excerpt") or "" for e in brief_row.get("selected_evidence") or []]
    texts += _material(pack_body)
    texts += [d for o in offer_descriptors(provenance) for d in o.get("descriptors") or []]
    return {_digits(m.group(0)) for t in texts for m in FIGURE.finditer(t or "")}


def _digits(token: str) -> str:
    return re.sub(r"[^\d.]", "", token).rstrip(".")


def _title_case(line: str) -> bool:
    words = re.findall(r"[A-Za-z][A-Za-z'’]*", line)
    return len(words) >= 3 and sum(w[0].isupper() for w in words) / len(words) >= 0.6


def _new_names(text: str, allowed: set[str]) -> list[str]:
    found = []
    for line in (text or "").split("\n"):
        if _title_case(line):
            continue
        for m in NAME.finditer(line):
            before = line[:m.start()].rstrip(" \t")
            if not before or before[-1] in SENTENCE_START or before.endswith("{{"):
                continue
            word = m.group(1).lower()
            if word in allowed or word.rstrip("s") in allowed or len(word) < 2:
                continue
            found.append(m.group(1))
    return list(dict.fromkeys(found))


def new_fact_findings(bodies: dict[str, dict], brief_row: dict, pack_body: dict | None = None) -> list[dict]:
    """No new numbers or names (blocking): a figure or a name the brief, the call, the roster, the offers and the tools list
    do not hold (and, under finisher v4, the call's turns behind the premise Reels)."""
    figures, words = _allowed_figures(brief_row, pack_body), _allowed_words(brief_row, pack_body)
    out = []
    for key in c2.PIECE_KEYS:
        piece = bodies.get(key) or {}
        locked = person_paths(piece)
        for path, label, text in copy_lines(key, piece.get("content")):
            severity = "warning" if _by_person(path, locked) else "blocking"
            tail = " (a person wrote this line; check it)" if severity == "warning" else ""
            new = [m.group(0) for m in FIGURE.finditer(text) if _digits(m.group(0)) and _digits(m.group(0)) not in figures]
            if new:
                out.append(finding("pack.new_number", severity,
                                   f'{_cap(label)} states {", ".join(dict.fromkeys(new))}, a figure neither the brief nor the call '
                                   "holds: say only what they hold" + tail, key, path))
            names = _new_names(text, words)
            if names:
                out.append(finding("pack.new_name", severity,
                                   f'{_cap(label)} names {", ".join(names)}, which the brief, the call and the team roster do not '
                                   "hold: name only who and what they hold" + tail, key, path))
    return out


def client_quotes_in_copy(bodies: dict[str, dict], brief_row: dict, sources=None) -> list[dict]:
    """Every client's words quoted in copy: {piece, path, quote, speaker, evidence_id}."""
    sources = sources if sources is not None else quote_sources(brief_row)
    out = []
    for key in c2.PIECE_KEYS:
        for path, _, text in copy_lines(key, (bodies.get(key) or {}).get("content")):
            for quoted in _quotes(text):
                said = next((s for s in sources if s["class"] == "client" and len(_tokens(quoted)) >= 3 and _matches(quoted, s["tokens"])), None)
                if said:
                    out.append({"piece": key, "path": path, "quote": quoted, "speaker": said["speaker"], "evidence_id": said["evidence_id"]})
    return out


def _listed(quote: str, listed: list[str]) -> bool:
    said = _normalise(quote)
    return any(said and (said in q or q in said) for q in listed if q)


def missing_client_quotes(pack_body: dict | None, piece_bodies, brief_row: dict) -> list[dict]:
    """The client quotes in copy the pack body does not list yet, as `ClientQuote` entries numbered after the listed ones,
    for finalize (and an edit) to add to `client_quotes`."""
    bodies = bodies_of(piece_bodies)
    present = list((pack_body or {}).get("client_quotes") or [])
    listed = [_normalise(q.get("quote")) for q in present]
    numbers = [int(m.group(1)) for q in present if (m := re.match(r"^Q(\d+)$", q.get("quote_id") or ""))]
    n = max(numbers, default=0)
    out = []
    for q in client_quotes_in_copy(bodies, brief_row):
        if _listed(q["quote"], listed):
            continue
        n += 1
        listed.append(_normalise(q["quote"]))
        out.append({"quote_id": f"Q{n}", "piece": q["piece"], "quote": q["quote"], "speaker": q["speaker"],
                    "evidence_id": q["evidence_id"], "cleared": None})
    return out


def client_quote_findings(pack_body: dict | None, bodies: dict[str, dict], brief_row: dict) -> list[dict]:
    """Client quote listed (a note, never a gate)."""
    out = []
    for q in missing_client_quotes(pack_body, bodies, brief_row):
        label = c2.LABELS[q["piece"]]
        path = next((x["path"] for x in client_quotes_in_copy({q["piece"]: bodies[q["piece"]]}, brief_row) if x["quote"] == q["quote"]), None)
        out.append(finding("pack.client_quote_listed", "warning",
                           f'{label} quotes the client ("{snippet(q["quote"])}"): list it under client quotes, for the client\'s '
                           "okay before posting", q["piece"], path, q["quote"]))
    return out


def premise_pack(bodies: dict[str, dict]) -> bool:
    """Whether the pack's Reels are the central story and two premises (finisher v3), by the kinds its Reels hold."""
    return any(((bodies.get(k) or {}).get("content") or {}).get("kind") in c2.PREMISE_KINDS for k in REEL_KEYS) or any(
        "premise of its own" in ((bodies.get(k) or {}).get("not_written_reason") or "") for k in REEL_KEYS)


def composition_findings(bodies: dict[str, dict]) -> list[dict]:
    """Exactly the email, the carousel, and Reels 1 to 3 as story, stance and b-roll text, or as the central story and two
    premises of their own (blocking)."""
    out = []
    expected = c2.KEY_PREMISE if premise_pack(bodies) else c2.KEY_KIND
    for key in c2.PIECE_KEYS:
        piece, label = bodies.get(key), c2.LABELS[key]
        kind = expected.get(key)
        if not piece:
            out.append(finding("pack.composition", "blocking", f"The pack has no {label}", key))
            continue
        if piece.get("channel") and piece["channel"] != c2.CHANNEL[key]:
            out.append(finding("pack.composition", "blocking", f"{label} holds a {piece['channel']}, not a {c2.CHANNEL[key]}", key))
        content = piece.get("content")
        if piece.get("origin") == "not_written" or not content:
            reason = piece.get("not_written_reason") or "no reason was recorded"
            what = f"{label} ({KIND_WORDS[kind]})" if kind else label
            out.append(finding("pack.composition", "blocking", f"{what} was not written: {reason}", key))
            continue
        if kind and content.get("kind") != kind:
            out.append(finding("pack.composition", "blocking",
                               f"{label} is the {KIND_WORDS[kind]} Reel, but it holds a {KIND_WORDS.get(content.get('kind'), 'different')} Reel",
                               key, "kind"))
    return out


def _words(text: str) -> int:
    return len(re.findall(r"[A-Za-z0-9]+(?:['’][A-Za-z]+)?", text or ""))


def format_findings(bodies: dict[str, dict]) -> list[dict]:
    """The house format by piece (warnings)."""
    out = []

    def warn(key, path, message):
        out.append(finding("pack.format", "warning", message, key, path))
    email = (bodies.get("email") or {}).get("content")
    if email:
        n = len(email.get("subject_options") or [])
        if n != 3:
            warn("email", "subject_options", f"The email has {n} subject option{'s' if n != 1 else ''}: give three, best first")
        words = _words(" ".join(email.get(k) or "" for k in ("opening", "body", "ending")))
        if not 250 <= words <= 450:
            warn("email", "body", f"The email runs {words} words: it stands alone in 250 to 450")
    carousel = (bodies.get("carousel") or {}).get("content")
    if carousel:
        for j, slide in enumerate(carousel.get("slides") or []):
            text = slide.get("text") or ""
            lines = [x for x in text.split("\n") if x.strip()]
            words = _words(text)
            if not 2 <= len(lines) <= 5:
                warn("carousel", f"slides[{j}].text", f"Carousel slide {slide.get('number', j + 1)} has {len(lines)} line"
                                                     f"{'s' if len(lines) != 1 else ''}: a slide is 2 to 5 short stacked lines")
            if not 18 <= words <= 60:
                warn("carousel", f"slides[{j}].text", f"Carousel slide {slide.get('number', j + 1)} has {words} words: about 20 to 55")
    for key in ("carousel", *REEL_KEYS):
        content = (bodies.get(key) or {}).get("content")
        if not content:
            continue
        label = c2.LABELS[key]
        caption = content.get("caption")
        if caption:
            words = _words(" ".join(caption.get(k) or "" for k in ("hook", "body", "ending")))
            if not 150 <= words <= 300:
                warn(key, "caption", f"{label}'s caption runs {words} words: 150 to 300")
        if key == "carousel":
            continue
        text_reel = content.get("production") == "on_screen_text" or content.get("kind") == "broll_text"
        if not text_reel and content.get("source") == "new_script":
            words = _words(content.get("script"))
            if not 120 <= words <= 220:
                warn(key, "script", f"{label}'s script runs {words} words: 120 to 220 (45 to 90 seconds)")
        if text_reel and not 1 <= len(content.get("screens") or []) <= 3:
            warn(key, "screens", f"{label} is on-screen text and needs one to three screens")
        if _normalise(content.get("title")) and _normalise(content.get("title")) == _normalise(content.get("job")):
            warn(key, "title", f"{label}'s title repeats its creative direction: give it a working title of its own")
    return out


def voice_findings(bodies: dict[str, dict]) -> list[dict]:
    """Copy that praises WIA by comparing it with other agencies (warnings, Round 2)."""
    out = []
    for key in c2.PIECE_KEYS:
        for path, label, text in copy_lines(key, (bodies.get(key) or {}).get("content")):
            if m := AGENCY_COMPARISON.search(text):
                out.append(finding("pack.voice", "warning", f'{_cap(label)} compares WIA with other agencies ("{m.group(0)}"): '
                                                             "explain the decision WIA made instead", key, path))
    return out


def spelling_findings(bodies: dict[str, dict]) -> list[dict]:
    """US spelling (warnings)."""
    out = []
    for key in c2.PIECE_KEYS:
        for path, label, text in copy_lines(key, (bodies.get(key) or {}).get("content")):
            for word in dict.fromkeys(m.group(1) for m in _BRITISH.finditer(text)):
                us = BRITISH[word.lower()]
                us = us.capitalize() if word[:1].isupper() else us
                out.append(finding("pack.us_spelling", "warning", f'{_cap(label)} uses the British "{word}": write "{us}"', key, path))
    return out


# ---- the week -----------------------------------------------------------------------------------------------------

def week_siblings(conn, pack: dict) -> list[dict]:
    """The week's other current v2 packs that have copy: {pack_id, title, brief_id, body, pieces, created_at}."""
    rows = conn.execute("""SELECT * FROM content_packs p WHERE p.week_id=%s AND p.pack_id<>%s AND p.contract_version=%s
        AND p.content_body IS NOT NULL AND p.source_brief_id<>%s
        AND NOT EXISTS (SELECT 1 FROM content_packs n WHERE n.supersedes_id=p.pack_id) ORDER BY p.created_at,p.pack_id""",
                        (pack["week_id"], pack["pack_id"], c2.VERSION, pack["source_brief_id"])).fetchall()
    return [{"pack_id": r["pack_id"], "title": r["title"], "brief_id": r["source_brief_id"], "body": r["content_body"],
             "pieces": bodies_of(model.pieces(conn, r["pack_id"])), "created_at": r["created_at"]} for r in rows]


def _similar(a: str, b: str) -> bool:
    from ..briefs.first_touch import stems
    x, y = stems(a), stems(b)
    union = x | y
    return bool(union) and len(x & y) / len(union) >= 0.8


def _offer_pieces(bodies: dict[str, dict]) -> list[tuple[str, bool]]:
    """(label, has a no-offer ending) for each Instagram piece that asks for the offer."""
    out = []
    for key in ("carousel", *REEL_KEYS):
        content = (bodies.get(key) or {}).get("content")
        if content and (content.get("cta") == "offer" or any(OFFER_ASK.search(t) for _, _, t in copy_lines(key, content))):
            out.append((c2.LABELS[key], bool((content.get("no_offer_ending") or "").strip())))
    return out


def _first_touch(bodies: dict[str, dict]) -> list[tuple[str, str, str, str]]:
    """(piece, path, what, text) for the lines a week keeps distinct: Reel hooks and covers, email subjects."""
    out = []
    for key in REEL_KEYS:
        content = (bodies.get(key) or {}).get("content") or {}
        for path, what in (("on_screen_hook", "hook"), ("cover_text", "cover")):
            if content.get(path):
                out.append((key, path, what, content[path]))
    for j, s in enumerate(((bodies.get("email") or {}).get("content") or {}).get("subject_options") or []):
        out.append(("email", f"subject_options[{j}]", "subject", s))
    return out


def week_findings(conn, pack: dict, bodies: dict[str, dict], siblings: list[dict]) -> list[dict]:
    """The week's checks (warnings), over this pack and the week's other current packs."""
    out = []
    # The week plan posts one offer ask and gives every other piece its no-offer ending (section 4.4), so a clash is a piece
    # that asks for the offer and has no ending without the ask.
    mine = _offer_pieces(bodies)
    theirs = [(s["title"], label) for s in siblings for label, _ in _offer_pieces(s["pieces"])]
    stuck = [label for label, has in mine if not has]
    if stuck and len(mine) + len(theirs) > 1:
        others = [f'{label} of "{snippet(title, 40)}"' for title, label in theirs]
        out.append(finding("week.offer_cta", "warning",
                           "One offer CTA a week on Instagram: this pack's " + " and ".join(label for label, _ in mine) + " ask for the offer"
                           + (", and so do " + ", ".join(others) if others else "") + ". Give " + " and ".join(stuck)
                           + " a no-offer ending, so the week posts one ask"))
    for key, path, what, text in _first_touch(bodies):
        for s in siblings:
            for _, _, other_what, other in _first_touch(s["pieces"]):
                if other_what == what and _similar(text, other):
                    out.append(finding("week.distinct", "warning",
                                       f'{c2.LABELS[key]}\'s {what} repeats a {what} of "{snippet(s["title"], 40)}" ("{snippet(other, 50)}"): '
                                       f"{what}s are distinct across the week", key, path))
                    break
    out += _emoji_findings(conn, pack, bodies)
    out += _repeat_findings(conn, pack)
    return out


def _emoji_findings(conn, pack, bodies) -> list[dict]:
    subjects = ((bodies.get("email") or {}).get("content") or {}).get("subject_options") or []
    if conn is None or not subjects or not EMOJI.search(subjects[0]):
        return []
    week = conn.execute("SELECT week_start FROM weeks WHERE week_id=%s", (pack["week_id"],)).fetchone()
    if not week:
        return []
    start = week["week_start"].replace(day=1)
    end = (start + timedelta(days=32)).replace(day=1)
    rows = conn.execute("""SELECT p.pack_id FROM content_packs p JOIN weeks w ON w.week_id=p.week_id WHERE p.contract_version=%s
        AND p.content_body IS NOT NULL AND w.week_start>=%s AND w.week_start<%s AND p.source_brief_id<>%s
        AND NOT EXISTS (SELECT 1 FROM content_packs n WHERE n.supersedes_id=p.pack_id)""",
                        (c2.VERSION, start, end, pack["source_brief_id"])).fetchall()
    others = 0
    for r in rows:
        email = (bodies_of(model.pieces(conn, r["pack_id"])).get("email") or {}).get("content") or {}
        if (email.get("subject_options") or [""])[0] and EMOJI.search(email["subject_options"][0]):
            others += 1
    if others + 1 <= 2:
        return []
    return [finding("week.emoji", "warning", f"Emoji in email subjects at most twice a month: this month's emails already use "
                                             f"{others}; send this one without", "email", "subject_options[0]")]


def _repeat_findings(conn, pack) -> list[dict]:
    """No central point repeated within 60 days: against the other ideas' packs and the published register."""
    point = (pack.get("content_body") or {}).get("message_spine")
    if conn is None or not point or not pack.get("created_at"):
        return []
    since, until = pack["created_at"] - timedelta(days=60), pack["created_at"] + timedelta(days=60)
    rows = conn.execute("""SELECT p.title,p.content_body->>'message_spine' AS point FROM content_packs p WHERE p.contract_version=%s
        AND p.content_body IS NOT NULL AND p.source_brief_id<>%s AND p.created_at BETWEEN %s AND %s
        AND NOT EXISTS (SELECT 1 FROM content_packs n WHERE n.supersedes_id=p.pack_id)""",
                        (c2.VERSION, pack["source_brief_id"], since, until)).fetchall()
    published = conn.execute("""SELECT title,key_message AS point FROM published_content WHERE published_on BETWEEN %s AND %s
        AND (brief_id IS NULL OR brief_id<>%s)""", (since.date(), until.date(), pack["source_brief_id"])).fetchall()
    for r in [*rows, *published]:
        if r["point"] and _similar(point, r["point"]):
            return [finding("week.central_point", "warning",
                            f'This pack\'s central point repeats "{snippet(r["title"], 50)}" within 60 days ("{snippet(r["point"], 60)}")')]
    return []


# ---- all of them --------------------------------------------------------------------------------------------------

def removed_findings(conn, pack_row: dict | None, brief_row: dict) -> list[dict]:
    """A pack built on material removed at a client's request (6.B12, removal.py): its brief, or the pack itself, is marked.
    One blocking finding that no attestation clears; without a database, none."""
    if conn is None:
        return []
    from ..removal import mark_of
    mark = mark_of(conn, "brief", brief_row.get("brief_id")) or mark_of(conn, "pack", (pack_row or {}).get("pack_id"))
    return [finding("consent.removed", "blocking", mark["note"])] if mark else []


def findings(conn, pack_row: dict | None, pieces, brief_row: dict, *, siblings=None, consent=None, rules=None) -> list[dict]:
    """Every deterministic finding of a pack version, in the PackFindingV2 shape. `pieces` are the five piece rows or
    envelopes; `pack_row` carries the pack body (its client quotes; finalize passes the body it is about to write). With
    `siblings` (the week's other current packs, `week_siblings`) the week's checks run too; they are never stored."""
    bodies = bodies_of(pieces)
    body = _brief_parts(brief_row)[0]
    v4 = model.v4_body(body, bodies)
    pack_body = (pack_row or {}).get("content_body")
    sources = quote_sources(brief_row)
    out = (removed_findings(conn, pack_row, brief_row) + composition_findings(bodies) + brief_check_findings(v4, brief_row, bodies, pack_body)
           + consent_findings(conn, v4, brief_row, bodies, consent=consent, rules=rules)
           + identity_findings(conn, pack_row, v4, brief_row, bodies)
           + quote_findings(bodies, brief_row, sources) + new_fact_findings(bodies, brief_row, pack_body)
           + client_quote_findings(pack_body, bodies, brief_row) + format_findings(bodies) + voice_findings(bodies)
           + spelling_findings(bodies))
    if siblings is not None and pack_row:
        out += week_findings(conn, pack_row, bodies, siblings)
    return list({f["finding_id"]: f for f in out}.values())


def result(found: list[dict]) -> dict:
    """What a version stores as its `validation_result`."""
    return {"version": VERSION, "findings": found, "blocking": sum(f["severity"] == "blocking" for f in found)}
