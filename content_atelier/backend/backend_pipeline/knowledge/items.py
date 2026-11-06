"""Brand-kit items: the context store (L.B1, section 4.12, R51; migration 006, plan label 010).

An item is one dated, sourced fact or rule about WIA: an offer, a price, a team member, a CTA, a result with its
permission, a rule, an exemplar. Its body is typed per kind and validated by that kind's schema, so a malformed
body never reaches the store. Items move candidate -> confirmed or rejected -> retired (section 4.9); only
confirmed items valid on a date compile into a knowledge-base version or reach a stage.

Confirming an item supersedes the confirmed item with the same key: the older one stays valid until the day
before the newer one starts, then retires. So a price changed with a `valid_from` is a new item version, which
runs use from that date (L.F2).
"""
from __future__ import annotations

import functools
import re
import unicodedata
from datetime import UTC, date, datetime, timedelta
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from ..repository import identifier, insert
from ..store import canonical_hash

KINDS = ("rule", "exemplar", "offer", "price", "roster_member", "result", "cta", "process_step", "belief",
         "audience_phrase", "format_rule", "campaign", "content_plan_entry", "performance_note")
# Operating facts change when the business changes and take effect when confirmed; identity (voice, rules,
# exemplars) takes effect only through an approved, benchmarked knowledge-base version (L.B4, R44).
OPERATING_KINDS = frozenset({"offer", "price", "roster_member", "result", "cta", "process_step", "campaign",
                             "content_plan_entry", "performance_note"})
IDENTITY_KINDS = frozenset(KINDS) - OPERATING_KINDS
# The compiled knowledge-base document each kind renders into (L.B4); keys match manifest format 2.
DOCUMENT_FOR_KIND = {"roster_member": "team_roster", "offer": "offer_sheet", "price": "offer_sheet",
                     "rule": "rejection_rules", "process_step": "process_catalogue", "format_rule": "format_guide",
                     "cta": "cta_catalogue", "audience_phrase": "audience_language", "result": "results_register",
                     "exemplar": "exemplars", "belief": "belief_statements", "campaign": "content_plan",
                     "content_plan_entry": "content_plan", "performance_note": "recent_published"}
# Kinds a reviewer may decide in a batch (L.B3): low risk, many entries.
LOW_RISK_KINDS = frozenset({"audience_phrase"})
STATUSES = ("candidate", "confirmed", "rejected", "retired")
VISIBILITIES = ("public", "internal")
SENSITIVITIES = ("none", "client_private", "personal", "confidential")
PERMISSIONS = ("published", "client_permission", "none")
SOURCE_KINDS = ("export_seed", "knowledge_base", "gate_decision", "approved_card", "approved_brief", "brief_edit",
                "published_piece", "performance_entry", "approver_entry", "seed", "learning_loop")
KEY_PREFIX = {"rule": "rule", "exemplar": "exemplar", "offer": "offer", "price": "price", "roster_member": "roster",
              "result": "result", "cta": "cta", "process_step": "process", "belief": "belief",
              "audience_phrase": "audience", "format_rule": "format", "campaign": "campaign",
              "content_plan_entry": "plan", "performance_note": "performance"}
KEY = re.compile(r"^[a-z_]+:[a-z0-9][a-z0-9_.:-]*$")

Text = Annotated[str, Field(min_length=1, max_length=8000, pattern=r"\S")]
Short = Annotated[str, Field(min_length=1, max_length=400, pattern=r"\S")]


class Body(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # Terms that must never appear in public copy (an internal price's amount, a private figure). The verifier
    # blocks public card and brief text that contains one (L.B5).
    block_terms: list[Short] = Field(default_factory=list, max_length=20)
    notes: str | None = Field(default=None, max_length=2000)


# What a rule governs (E.B11): factual (facts, figures, names, dates, sources, results); audience (who a piece speaks to
# and how it frames them); mechanism (what WIA's work is and how it produces results: its scope, ads beside other
# channels, LeadLock); offer (offers, prices, access, availability); voice (wording, tone, constructions); cta (calls to
# action and channel conventions); edit_scope (how WIA's copy is edited and the working process).
RULE_CATEGORIES = ("factual", "audience", "mechanism", "offer", "voice", "cta", "edit_scope")


class RulePattern(BaseModel):
    """One lint pattern of a rule (E.B10, E.B11): the verifier matches it, case-insensitively, against generated copy.
    `kind` is ban (blocks) or flag (warns); `scope` the copy it lints (cards, briefs or both); `applies_to` narrows a
    brief pattern to one asset type (an email)."""
    model_config = ConfigDict(extra="forbid")
    pattern: Annotated[str, Field(min_length=1, max_length=2000)]
    kind: Literal["ban", "flag"]
    scope: Literal["angle", "brief", "all"]
    message: Short
    applies_to: str | None = Field(default=None, max_length=40)

    @field_validator("pattern")
    @classmethod
    def _compiles(cls, value):
        try:
            re.compile(value, re.I)
        except re.error as error:
            raise ValueError(f"The pattern does not compile: {error}") from None
        return value


class RuleBody(Body):
    statement: Text
    level: Literal["ban", "flag"]
    scope: Literal["angle", "brief", "all"]
    code: str | None = Field(default=None, max_length=40)
    since: str | None = Field(default=None, max_length=80)
    origin: str | None = Field(default=None, max_length=2000)
    # Required before a rule is confirmed (E.B11); a candidate may carry a suggestion the reviewer changes.
    category: Literal["factual", "audience", "mechanism", "offer", "voice", "cta", "edit_scope"] | None = None
    # What the deterministic lint matches for this rule; compiled into the version's lint patterns (E.B11 (2)).
    patterns: list[RulePattern] = Field(default_factory=list, max_length=10)


class ConfirmedRuleBody(RuleBody):
    """A confirmed rule (E.B11): its category is required. Confirmation checks it, and the compiler checks every rule it
    renders against it, so a version never compiles a rule without one."""
    category: Literal["factual", "audience", "mechanism", "offer", "voice", "cta", "edit_scope"]


class ExemplarBody(Body):
    channel: Short
    text: Text
    pillar: str | None = Field(default=None, max_length=200)
    label: str | None = Field(default=None, max_length=200)
    why: str | None = Field(default=None, max_length=4000)
    published: bool | None = None
    # A preference pair keeps the model's draft that Whitney rewrote, for comparison only.
    ai_text: str | None = Field(default=None, max_length=8000)


class OfferBody(Body):
    name: Short
    description: Text
    ownership: str | None = Field(default=None, max_length=400)
    access: str | None = Field(default=None, max_length=400)
    state: Literal["current", "retired"] = "current"
    aliases: list[Short] = Field(default_factory=list, max_length=10)
    # Prose the offer sheet keeps beside the offers (E.B25 (j), knowledge-base version 9): an offer's approved descriptor
    # (how copy names it) or an insider term of WIA's programs (never in first-touch text). Absent on an offer itself.
    section: Literal["descriptor", "insider_term"] | None = None


class PriceBody(Body):
    offer: Short
    amount: Short
    terms: str | None = Field(default=None, max_length=2000)

    @field_validator("amount")
    @classmethod
    def _figure(cls, value):
        if not re.search(r"\d", value):
            raise ValueError("A price needs a figure")
        return value


class RosterMemberBody(Body):
    name: Short
    role: Short
    state: Literal["current", "former", "outside", "not_a_person", "invented"]
    aliases: list[Short] = Field(default_factory=list, max_length=10)
    left_on: str | None = Field(default=None, max_length=80)


class ResultBody(Body):
    claim: Text
    client_type: str | None = Field(default=None, max_length=400)
    offer: str | None = Field(default=None, max_length=200)
    first_published: str | None = Field(default=None, max_length=400)
    framing: str | None = Field(default=None, max_length=2000)


class CtaBody(Body):
    wording: Text
    cta_type: Literal["dm_keyword", "reply", "waitlist", "apply", "register", "link", "podcast", "none", "rule", "other"]
    used_for: str | None = Field(default=None, max_length=400)
    channel: str | None = Field(default=None, max_length=100)
    offer: str | None = Field(default=None, max_length=200)


class ProcessStepBody(Body):
    process: Short
    what: Text
    step: str | None = Field(default=None, max_length=200)
    owner: str | None = Field(default=None, max_length=200)


class BeliefBody(Body):
    statement: Text
    said_or_published: str | None = Field(default=None, max_length=100)


class AudiencePhraseBody(Body):
    phrase: Text
    theme: Short
    speaker: str | None = Field(default=None, max_length=100)


class FormatRuleBody(Body):
    format: Short
    rule: Text


class CampaignBody(Body):
    name: Short
    starts: date | None = None
    ends: date | None = None
    offer: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=4000)


class ContentPlanEntryBody(Body):
    topic: Text
    week_of: date | None = None
    channel: str | None = Field(default=None, max_length=100)
    purpose: Literal["attract", "warm", "convert"] | None = None
    offer: str | None = Field(default=None, max_length=200)


class PerformanceNoteBody(Body):
    note: Text
    content_id: str | None = Field(default=None, max_length=200)
    metric: str | None = Field(default=None, max_length=200)


SCHEMAS: dict[str, type[Body]] = {
    "rule": RuleBody, "exemplar": ExemplarBody, "offer": OfferBody, "price": PriceBody,
    "roster_member": RosterMemberBody, "result": ResultBody, "cta": CtaBody, "process_step": ProcessStepBody,
    "belief": BeliefBody, "audience_phrase": AudiencePhraseBody, "format_rule": FormatRuleBody,
    "campaign": CampaignBody, "content_plan_entry": ContentPlanEntryBody, "performance_note": PerformanceNoteBody,
}


def validate_body(kind: str, body) -> dict:
    """The kind's schema applied to a body; a malformed body raises ValueError naming the field."""
    if kind not in SCHEMAS:
        raise ValueError("Unknown item kind; use one of: " + ", ".join(KINDS))
    if not isinstance(body, dict):
        raise ValueError(f"A {kind} body must be an object")
    try:
        value = SCHEMAS[kind].model_validate(body).model_dump(mode="json", exclude_none=True)
    except ValidationError as e:
        problems = "; ".join(f"{'.'.join(str(p) for p in err['loc']) or kind}: {err['msg']}" for err in e.errors())
        raise ValueError(f"Malformed {kind} body: {problems}") from None
    if kind == "price":
        # A price's figures must never reach public copy unless WIA published them (rulings 2.2).
        terms = value.get("block_terms") or []
        value["block_terms"] = [*terms, *[f for f in figures(value["amount"]) if f not in terms]]
    if not value.get("block_terms"):
        value.pop("block_terms", None)
    if kind == "rule" and not value.get("patterns"):
        value.pop("patterns", None)
    return value


FIGURE = re.compile(r"\$\s?\d[\d,]*(?:\.\d+)?\s?[kK]?")


def figures(text: str) -> list[str]:
    """Dollar figures in a text, as written ("$1,497", "$22K")."""
    return list(dict.fromkeys(m.group(0).strip() for m in FIGURE.finditer(text or "")))


# What an internal item states that public copy must never repeat, beyond dollar figures (L.B5): measured figures
# and the words it quotes (a client's private praise, an internal policy line). Durations are left out: "6 weeks" is
# ordinary copy. Quotes shorter than three words ("approved pool") are too common to block.
METRIC = re.compile(r"\b\d[\d,]*(?:\.\d+)?\s?%|\b\d[\d,]*(?:\.\d+)?x\b|\b\d[\d,]*(?:\.\d+)?\s+(?:leads?|bookings?|booked|"
                    r"inquir(?:y|ies)|enquir(?:y|ies)|weddings?|events?|tours?|clients?|consultations?|contracts?|sales|"
                    r"purchases?|followers?)\b", re.I)
QUOTED = re.compile(r'"([^"\n]{8,200})"|“([^”\n]{8,200})”')


def internal_phrases(text: str) -> list[str]:
    """The figures and quoted words an internal item states, as public copy would repeat them."""
    found = figures(text) + [m.group(0).strip() for m in METRIC.finditer(text or "")]
    found += [q.strip(" .,;:") for m in QUOTED.finditer(text or "") for q in m.groups() if q and len(q.split()) >= 3]
    return list(dict.fromkeys(found))


@functools.lru_cache(maxsize=8192)
def term_pattern(term: str) -> re.Pattern:
    """A blocked term as a whole figure or phrase: "$500" never matches "$5,000" or "$500,000".

    A dollar figure matches with or without its thousands separators ("$1497" is "$1,497"); a phrase matches across
    any whitespace and either apostrophe."""
    money = re.fullmatch(r"\$\s?(\d[\d,]*)(\.\d+)?(\s?[kK])?", term.strip())
    if money:
        body = r"\$\s?" + ",?".join(money.group(1).replace(",", "")) + re.escape(money.group(2) or "")
        body += r"\s?[kK]\b" if money.group(3) else r"(?!\s?[kK]\b)"
    else:
        body = r"\s+".join(re.sub(r"\\?['’]", "['’]", re.escape(w)) for w in term.split())
    return re.compile(r"(?<![\w$,.])" + body + r"(?![\d,]*\d)(?!\.\d)", re.I)


def contains_term(text: str, term: str) -> bool:
    return bool(term_pattern(term).search(text or ""))


# The body field that carries an item's meaning; a text-only edit is written into it (L.B3), so stages that read
# the body never see the unedited wording.
PRIMARY_FIELD = {"rule": "statement", "exemplar": "text", "offer": "description", "price": "terms", "roster_member": "role",
                 "result": "claim", "cta": "wording", "process_step": "what", "belief": "statement", "audience_phrase": "phrase",
                 "format_rule": "rule", "campaign": "description", "content_plan_entry": "topic", "performance_note": "note"}


def internal_figures(kind: str, body: dict, text: str, visibility: str) -> dict:
    """An internal price or offer fact blocks every dollar figure its text or body states (rulings 2.2)."""
    if visibility != "internal" or kind not in ("price", "offer"):
        return body
    found = figures(text) + figures(" ".join(str(v) for v in body.values() if isinstance(v, str)))
    terms = list(body.get("block_terms") or [])
    extra = [f for f in dict.fromkeys(found) if f not in terms]
    return {**body, "block_terms": [*terms, *extra][:20]} if extra else body


def render(kind: str, body: dict) -> str:
    """The item as one line of knowledge-base text."""
    b = body
    if kind == "rule":
        head = f"{b['code']}: " if b.get("code") else ""
        category = f"; {b['category'].replace('_', ' ')}" if b.get("category") else ""
        since = f"; since {b['since']}" if b.get("since") else ""
        return f"{head}{b['statement']} ({b['level']}; scope {b['scope']}{category}{since})"
    if kind == "exemplar":
        meta = ", ".join(x for x in (b["channel"], b.get("pillar"), b.get("label")) if x)
        return f"[{meta}] {b['text']}"
    if kind == "offer":
        head = b["name"] + (" (retired name; never present as current)" if b.get("state") == "retired" else "")
        tail = "".join(f"; {label}: {b[k]}" for k, label in (("ownership", "who does what"), ("access", "how a buyer gets to it"))
                       if b.get(k))
        return f"{head}: {b['description']}{tail}"
    if kind == "price":
        return f"{b['offer']}: {b['amount']}" + (f" ({b['terms']})" if b.get("terms") else "")
    if kind == "roster_member":
        aka = f"; shown as {', '.join(b['aliases'])}" if b.get("aliases") else ""
        left = f"; left {b['left_on']}" if b.get("left_on") else ""
        return f"{b['name']}: {b['role']} ({b['state'].replace('_', ' ')}{left}{aka})"
    if kind == "result":
        who = f"{b['client_type']}: " if b.get("client_type") else ""
        return who + b["claim"] + (f" (first published: {b['first_published']})" if b.get("first_published") else "")
    if kind == "cta":
        used = f" for {b['used_for']}" if b.get("used_for") else ""
        channel = f" on {b['channel']}" if b.get("channel") else ""
        return f"{b['cta_type'].replace('_', ' ')}{channel}{used}: {b['wording']}"
    if kind == "process_step":
        step = f" {b['step']}" if b.get("step") else ""
        owner = f" (owner: {b['owner']})" if b.get("owner") else ""
        return f"{b['process']}{step}: {b['what']}{owner}"
    if kind == "belief":
        return b["statement"]
    if kind == "audience_phrase":
        return f"{b['theme']}: {b['phrase']}"
    if kind == "format_rule":
        return f"{b['format']}: {b['rule']}"
    if kind == "campaign":
        window = " to ".join(str(x) for x in (b.get("starts"), b.get("ends")) if x)
        return b["name"] + (f" ({window})" if window else "") + (f": {b['description']}" if b.get("description") else "")
    if kind == "content_plan_entry":
        meta = ", ".join(str(x) for x in (b.get("week_of"), b.get("channel"), b.get("purpose"), b.get("offer")) if x)
        return (f"[{meta}] " if meta else "") + b["topic"]
    return b["note"]


def slug(value: str, limit: int = 80) -> str:
    text = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")[:limit].strip("-")
    return text or "item"


def key_for(kind: str, name: str) -> str:
    return f"{KEY_PREFIX[kind]}:{slug(name)}"


def item_hash(row: dict) -> str:
    """What a reviewer saw: body, text, validity, exposure and state. Decisions are bound to it (409 when stale)."""
    return canonical_hash({k: (row.get(k).isoformat() if isinstance(row.get(k), date) else row.get(k))
                           for k in ("kind", "key", "body", "text", "valid_from", "valid_to", "status", "visibility",
                                     "sensitivity", "permission")})


def check_fields(kind, key, visibility, sensitivity, permission, valid_from, valid_to):
    if not KEY.match(key or ""):
        raise ValueError("An item key is a kind prefix and a slug, such as offer:elevate")
    if visibility not in VISIBILITIES:
        raise ValueError("Visibility is public or internal")
    if sensitivity not in SENSITIVITIES:
        raise ValueError("Sensitivity is none, client_private, personal or confidential")
    if kind == "result" and permission not in PERMISSIONS:
        raise ValueError("A result needs its permission: published, client_permission or none")
    if kind != "result" and permission is not None:
        raise ValueError("Only results carry a permission")
    if valid_from and valid_to and valid_to < valid_from:
        raise ValueError("An item cannot end before it starts")
    if sensitivity in ("personal", "confidential"):
        # Personal and confidential material never enters the store (R52, L.B2).
        raise ValueError("Personal and confidential material is never stored as context")
    if sensitivity == "client_private" and visibility != "internal":
        raise ValueError("Client-private material is internal")


def require_category(kind: str, body: dict):
    """A confirmed rule names its category (E.B11), so every rule in a compiled version shows one."""
    if kind == "rule" and not (body or {}).get("category"):
        raise ValueError("A rule needs its category before it is confirmed: " + ", ".join(RULE_CATEGORIES))


def uncategorised_rules(rows: list[dict]) -> list[str]:
    """The keys of rules that fail the confirmed-rule schema (no category, or an unknown one)."""
    bad = []
    for r in rows:
        try:
            ConfirmedRuleBody.model_validate(r["body"])
        except ValidationError:
            bad.append(r["key"])
    return bad


def table_ready(conn) -> bool:
    return bool(conn.execute("SELECT to_regclass('public.brand_kit_items') AS t").fetchone()["t"])


def add_item(conn, *, kind, key, body, status, source_kind, source_ref, author, created_by, text=None,
             visibility="public", sensitivity="none", permission=None, source_detail=None, statement_date=None,
             model_written=False, confidence=None, valid_from=None, valid_to=None, reviewed_by=None, review_note=None,
             supersedes_id=None, embedding=None) -> tuple[str, bool]:
    """Insert one item; idempotent by (source_kind, source_ref). Returns (item_id, created)."""
    body = validate_body(kind, body)
    check_fields(kind, key, visibility, sensitivity, permission, valid_from, valid_to)
    body = internal_figures(kind, body, text or "", visibility)
    if status not in ("candidate", "confirmed"):
        raise ValueError("New items are candidates, or confirmed with a reviewer")
    if source_kind not in SOURCE_KINDS:
        raise ValueError("Unknown source kind")
    if not (source_ref or "").strip():
        raise ValueError("Every item cites its source")
    if status == "confirmed" and not (reviewed_by or "").strip():
        raise ValueError("Nothing is confirmed without a recorded reviewer")
    if status == "confirmed":
        require_category(kind, body)
    if model_written and status == "confirmed" and source_kind != "knowledge_base":
        # Model-written text is only ever a candidate until a person confirms its exact wording in review
        # (section 4.12); only a WIA-confirmed supplied document's entries load as confirmed (L.B2).
        raise ValueError("Model-written text enters as a candidate")
    existing = conn.execute("SELECT item_id FROM brand_kit_items WHERE source_kind=%s AND source_ref=%s",
                            (source_kind, source_ref)).fetchone()
    if existing:
        return existing["item_id"], False
    text = (text or "").strip() or render(kind, body)
    row = {"item_id": identifier("item"), "kind": kind, "key": key, "body": body, "text": text,
           "valid_from": valid_from, "valid_to": valid_to, "status": status, "visibility": visibility,
           "sensitivity": sensitivity, "permission": permission, "source_kind": source_kind,
           "source_ref": source_ref, "source_detail": source_detail or {}, "statement_date": statement_date,
           "author": author, "model_written": bool(model_written), "confidence": confidence,
           "supersedes_id": supersedes_id, "reviewed_by": reviewed_by, "review_note": review_note,
           "reviewed_at": datetime.now(UTC) if status == "confirmed" else None, "created_by": created_by}
    row["hash"] = item_hash(row)
    if embedding is not None:
        row["embedding"] = embedding
    insert(conn, "brand_kit_items", row)
    if status == "confirmed":
        supersede(conn, row["item_id"])
    return row["item_id"], True


def get_item(conn, item_id, *, lock=False) -> dict:
    row = conn.execute("SELECT * FROM brand_kit_items WHERE item_id=%s" + (" FOR UPDATE" if lock else ""),
                       (item_id,)).fetchone()
    if not row:
        raise LookupError("Item not found")
    return row


def rehash(conn, item_id) -> str:
    row = get_item(conn, item_id)
    digest = item_hash(row)
    conn.execute("UPDATE brand_kit_items SET hash=%s,updated_at=now() WHERE item_id=%s", (digest, item_id))
    return digest


def supersede(conn, item_id, today: date | None = None) -> list[str]:
    """Make a newly confirmed item the current version of its key; returns the items it superseded.

    A roster item also updates the matching `people` row in the same transaction (plan 1.B2): the roster is the editing
    surface for staff facts, `people` is where speakers resolve."""
    superseded = _supersede(conn, item_id, today)
    new = get_item(conn, item_id)
    if new["kind"] == "roster_member" and new["status"] == "confirmed":
        from ..reference import mirror_roster_key
        mirror_roster_key(conn, new["key"], today)
    return superseded


def _supersede(conn, item_id, today: date | None = None) -> list[str]:
    today = today or date.today()
    new = get_item(conn, item_id)
    # Two confirmations of the same key never both stand (a concurrent decide or enter waits here).
    conn.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 7310))", (new["key"],))
    older = conn.execute("""SELECT * FROM brand_kit_items WHERE key=%s AND status='confirmed' AND item_id<>%s
        ORDER BY coalesce(valid_from,'-infinity'::date), created_at FOR UPDATE""", (new["key"], item_id)).fetchall()
    if not older:
        return []
    start = new["valid_from"]
    if start is None:
        start = today
        conn.execute("UPDATE brand_kit_items SET valid_from=%s WHERE item_id=%s", (start, item_id))
    superseded = []
    for old in older:
        if old["valid_from"] and old["valid_from"] >= start:
            # Fully replaced: the new version starts no later than the old one.
            conn.execute("UPDATE brand_kit_items SET status='retired',updated_at=now() WHERE item_id=%s", (old["item_id"],))
        else:
            end = start - timedelta(days=1)
            if old["valid_to"] and old["valid_to"] < end:
                end = old["valid_to"]
            status = "retired" if end < today else "confirmed"
            conn.execute("UPDATE brand_kit_items SET valid_to=%s,status=%s,updated_at=now() WHERE item_id=%s",
                         (end, status, old["item_id"]))
        rehash(conn, old["item_id"])
        superseded.append(old["item_id"])
    conn.execute("UPDATE brand_kit_items SET supersedes_id=%s WHERE item_id=%s", (superseded[-1], item_id))
    rehash(conn, item_id)
    return superseded


VALID_AT = """status='confirmed' AND (valid_from IS NULL OR valid_from<=%s) AND (valid_to IS NULL OR valid_to>=%s)"""


def items_valid_at(conn, kind: str | None, on: date, *, kinds=None) -> list[dict]:
    """Confirmed items valid on a date, by kind (or kinds), in a stable order."""
    wanted = list(kinds) if kinds else [kind]
    if any(k not in SCHEMAS for k in wanted):
        raise ValueError("Unknown item kind")
    return conn.execute(f"""SELECT * FROM brand_kit_items WHERE kind = ANY(%s) AND {VALID_AT}
        ORDER BY kind, key, coalesce(valid_from,'-infinity'::date), item_id""", (wanted, on, on)).fetchall()


def delete_source(conn, *, source_kind, source_ref=None, source_ref_prefix=None, actor, reason) -> dict:
    """Remove a source's candidates and unconfirmed published pieces, and record the deletion (L.B1).

    Confirmed items stay: a person reviewed them, and runs may have used them. The record lists every deleted
    row by ID and hash (never its text) and every confirmed item kept.
    """
    if bool(source_ref) == bool(source_ref_prefix):
        raise ValueError("Name one source, or one source prefix")
    if not (reason or "").strip():
        raise ValueError("A deletion needs its reason")
    match = "source_ref=%s" if source_ref else "starts_with(source_ref,%s)"
    ref = source_ref or source_ref_prefix
    deleted = conn.execute(f"""DELETE FROM brand_kit_items WHERE source_kind=%s AND {match}
        AND status IN ('candidate','rejected') RETURNING item_id,kind,key,hash""", (source_kind, ref)).fetchall()
    published = []
    if conn.execute("SELECT to_regclass('public.published_content') AS t").fetchone()["t"]:
        published = conn.execute(f"""DELETE FROM published_content WHERE source_kind=%s AND {match}
            AND status='unconfirmed' RETURNING content_id""", (source_kind, ref)).fetchall()
    kept = conn.execute(f"""SELECT item_id,kind,key,hash FROM brand_kit_items WHERE source_kind=%s AND {match}""",
                        (source_kind, ref)).fetchall()
    decision_id = identifier("decision")
    insert(conn, "decisions", {
        "decision_id": decision_id, "item_kind": "brand_kit_source", "item_id": f"{source_kind}:{ref}",
        "action": "delete_source", "actor": actor, "author": actor, "note": reason.strip(),
        "details": {"source_kind": source_kind, "source_ref": source_ref, "source_ref_prefix": source_ref_prefix,
                    "deleted_items": [dict(r) for r in deleted],
                    "deleted_published": [r["content_id"] for r in published],
                    "kept_confirmed": [dict(r) for r in kept]}})
    return {"decision_id": decision_id, "deleted_items": len(deleted), "deleted_published": len(published),
            "kept_confirmed": len(kept)}
