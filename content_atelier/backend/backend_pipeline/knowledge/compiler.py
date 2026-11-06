"""Compiled knowledge-base versions (L.B4, section 4.12, R41 as amended by R51).

`kb_compile` renders each compiled document (roster, offer sheet, CTA catalogue, results register, rejection
rules, format guide, process catalogue, audience language, beliefs, exemplars, content plan) from the confirmed
items valid on a date, and carries every other document over from the base version (the active version, or the
file-backed knowledge base before any version is active). The output is a draft version in `brand_kit_docs`
(migration 005) in the format `knowledge_base.py` loads, recording the item IDs and hashes behind each document.
Compilation is deterministic: the same items give the same text and hashes, and compiling with nothing changed
returns the existing version.

A document is compiled only when its kinds have at least one confirmed item; until then the base document,
supplied or draft, carries over, and the result says how many candidates for it are still in the queue.

Approval activates a version. Each changed document is classified operating or identity. An identity change
(rules, exemplars, beliefs, audience language, format) needs an E.B3 smoke result before it becomes the production
default (R44) and shows "approved, pending benchmark" until `record_benchmark` stores a passing one, unless
`context.release.benchmark_required` is off: then the approver's approval releases it, as production does since the
owner's direction of 25 October 2026 (no paid benchmark, no developer in the weekly tone loop; a change WIA asked for is
WIA's to release, and the version before it stays one setting away). Internal and
gated prices never enter a document (rulings 2.2); the verifier receives their figures from the items (L.B5).
"""
from __future__ import annotations

import difflib
import hashlib
import json
import re
from datetime import date, timedelta
from pathlib import Path

from ..knowledge_base import (MANIFEST, DocumentEntry, KnowledgeBaseManifest, Provenance, _manifest_sha256,
                              load_knowledge_base, load_published)
from ..repository import identifier, insert
from . import additions as added, held_out, items, supersessions as superseded

ACTIVE = "knowledge_base.active"
MANIFEST_PREFIX = "knowledge_base.manifest."
# Compiled documents in manifest order, with the kinds each renders and its section order.
COMPILED = {
    "team_roster": ("roster_member",),
    "offer_sheet": ("offer", "price"),
    "rejection_rules": ("rule",),
    "process_catalogue": ("process_step",),
    "format_guide": ("format_rule",),
    "cta_catalogue": ("cta",),
    "audience_language": ("audience_phrase",),
    "results_register": ("result",),
    "content_plan": ("content_plan_entry", "campaign"),
    "exemplars": ("exemplar",),
    "belief_statements": ("belief",),
    "content_workflow": ("process_step",),
}
# How WIA plans and publishes, as opposed to how it works with clients: process steps whose process names it.
WORKFLOW_PROCESSES = ("Content workflow", "Published content")
# Compiled from confirmed published pieces, not items.
PUBLISHED_DOCUMENTS = frozenset({"recent_published"})


def _workflow(row: dict) -> bool:
    return str(row["body"].get("process", "")).startswith(WORKFLOW_PROCESSES)


def _document_items(conn, key: str, on: date) -> list[dict]:
    kinds = COMPILED.get(key)
    if not kinds:
        return []
    rows = items.items_valid_at(conn, None, on, kinds=kinds)
    if key == "process_catalogue":
        rows = [r for r in rows if not _workflow(r)]
    elif key == "content_workflow":
        rows = [r for r in rows if _workflow(r)]
    return rows


def document_rows(conn, key: str, on: date) -> list[dict]:
    """The confirmed items valid on `on` that one compiled document renders (the compiler and assembly share it).
    Items that state held-out benchmark material are left out (E.B17)."""
    return held_out.keep(_document_items(conn, key, on))


def published_rows(conn, on: date) -> list[dict]:
    """Confirmed pieces published in the 90 days before `on` (the strategist's situational block lists them live)."""
    return held_out.keep(conn.execute("""SELECT content_id,published_on,channel,title,key_message,performance FROM published_content
        WHERE status='confirmed' AND published_on BETWEEN %s AND %s
        ORDER BY published_on DESC, content_id""", (on - timedelta(days=RECENT_DAYS), on)).fetchall())


def render_published(rows: list[dict]) -> str:
    lines = ["## Published pieces WIA confirmed (newest first; do not repeat a central point published in the last 90 days)"]
    for r in rows:
        notes = "; ".join(f"{e['metric']}: {e['value']}" for e in r["performance"] or [])
        # The piece's own central point when it has one (E.B25 (i): the register at piece level, not campaign level).
        point = f" (central point: {r['key_message']})" if r.get("key_message") else ""
        lines.append(f"- {r['published_on'].isoformat()} {r['channel']}: {r['title']}{point}" + (f" ({notes})" if notes else ""))
    return "\n".join(lines)


# The supplied documents change only by superseded lines (E.B25 (c)), and they carry WIA's strategy and voice; so does the
# editing guide, a supplied document added from a date (E.B25 (e)).
IDENTITY_DOCUMENTS = frozenset({"rejection_rules", "format_guide", "audience_language", "exemplars", "belief_statements",
                                "editing_guide", "spoken_voice", "transformations"} | superseded.DOCUMENTS)
DEFAULT_STAGES = {"team_roster": ["strategist", "brief", "verifier", "extraction"], "offer_sheet": ["strategist", "brief", "verifier"],
                  "rejection_rules": ["strategist", "brief", "verifier"], "results_register": ["strategist", "brief", "verifier"],
                  "process_catalogue": ["strategist", "brief", "extraction"], "format_guide": ["brief"], "cta_catalogue": ["brief"],
                  # The card verifier checks the strategist's quotes of Whitney against her belief bank; without it, her
                  # own words read as invented quotes (live development week, 18 October).
                  "belief_statements": ["strategist", "brief", "verifier"]}
STAGE_ORDER = ("strategist", "brief", "verifier", "extraction")
# A compiled document's heading where the base version's heading describes a draft: once compiled from confirmed items,
# the heading and the status agree.
COMPILED_HEADINGS = {"content_plan": "Content plan and campaigns (entries WIA confirmed; each holds only for its own dates)"}


def _stages(key: str, stages: list[str] | None) -> list[str]:
    """A document's stages: those the base version gave it, plus every stage this compiler requires for it."""
    wanted = set(stages or DEFAULT_STAGES.get(key, ["strategist", "brief"])) | set(DEFAULT_STAGES.get(key, []))
    return [s for s in STAGE_ORDER if s in wanted]
INTERNAL = "(internal: never state publicly) "
# The prefix budget (section 4.12): the exemplar document carries the strongest pieces, newest first, up to this many
# characters; the brief writer still receives exemplars chosen for its channels (L.B5).
EXEMPLAR_DOCUMENT_CHARACTERS = 10000
EXEMPLAR_CHARACTERS = 900
# Contrastive pairs (a draft and the version Whitney chose) keep this share, so finals never crowd them out.
EXEMPLAR_PAIR_CHARACTERS = 2500
EXEMPLAR_PAIR_SIDE = 400
# Model-written cards and brief sections WIA approved in Content Atelier (the learning loop's directions; R52) are
# planning prose, not WIA's voice: they sit in their own labelled list, after WIA's copy, within this share.
EXEMPLAR_DIRECTION_CHARACTERS = 1500
# WIA's own copy first, newest first: published and approved finals, then her drafts and accepted hooks.
EXEMPLAR_PRIORITY = {"approved_final": 0, "published_final": 0, "her_draft": 1, "accepted_hook": 1}
RECENT_DAYS = 90
ROSTER_GROUPS = (("current", "Current team"), ("former", "Former staff: never present as current"),
                 ("outside", "Outside people often named: not staff"), ("not_a_person", "Not people"),
                 ("invented", "Invented names: never use"))


def mined_draft(row: dict) -> bool:
    """A model-written card or brief section that WIA approved in Content Atelier (L.B6): an approved direction, not
    WIA's voice. What WIA then publishes from it reaches the voice exemplars as a published final."""
    label = str(row["body"].get("label") or "")
    return row.get("source_kind") in ("approved_card", "approved_brief") or label.startswith(("approved_card", "approved_brief_"))


def _clip(text: str, limit: int) -> str:
    text = (text or "").strip()
    return text if len(text) <= limit else text[:limit].rsplit(" ", 1)[0] + " [...]"


def _newest(r: dict) -> int:
    return -(r["statement_date"].toordinal() if r.get("statement_date") else 0)


def _exemplar_sections(rows: list[dict]) -> list[str]:
    """The exemplar document (L.B4): WIA's own copy first (Whitney's and WIA's finals and her drafts before finals a
    model drafted for her, newest first), then contrastive pairs with a reserved share, then, clearly apart and capped,
    model-written directions WIA approved in Content Atelier, which are never presented as WIA's voice."""
    pairs = sorted((r for r in rows if r["body"].get("label") == "preference_pair" and not mined_draft(r)),
                   key=lambda r: (bool(r.get("model_written")), _newest(r), r["item_id"]))
    directions = sorted((r for r in rows if mined_draft(r)), key=lambda r: (_newest(r), r["item_id"]))
    finals = sorted((r for r in rows if r["body"].get("label") != "preference_pair" and not mined_draft(r)),
                    key=lambda r: (bool(r.get("model_written")), EXEMPLAR_PRIORITY.get(r["body"].get("label"), 4), _newest(r),
                                   r["item_id"]))

    def take(candidates, budget, block):
        chosen, used = [], 0
        for r in candidates:
            text = block(r)
            if used + len(text) <= budget:
                chosen.append(text)
                used += len(text)
        return chosen, used

    def dated(r):
        return f", {r['statement_date'].isoformat()}" if r.get("statement_date") else ""

    pair_blocks, pairs_used = take(pairs, EXEMPLAR_PAIR_CHARACTERS, lambda r: (
        f"### {r['body']['channel']}{dated(r)}\nDraft she replaced: {_clip(r['body'].get('ai_text') or '', EXEMPLAR_PAIR_SIDE)}\n"
        f"Her version: {_clip(r['body']['text'], EXEMPLAR_PAIR_SIDE)}"))
    direction_blocks, directions_used = take(directions, EXEMPLAR_DIRECTION_CHARACTERS, lambda r: (
        f"### {r['body']['channel']}{dated(r)}\n{_clip(r['body']['text'], EXEMPLAR_CHARACTERS)}"))
    final_blocks, _ = take(finals, EXEMPLAR_DOCUMENT_CHARACTERS - pairs_used - directions_used, lambda r: (
        f"### {r['body']['channel']}{dated(r)}\n{_clip(r['body']['text'], EXEMPLAR_CHARACTERS)}"))
    parts = ["Patterns, not formulas: WIA's own approved and published copy, newest first. Never copy a line; never repeat "
             "a central point published in the last 90 days.\n\n" + "\n\n".join(final_blocks)]
    if pair_blocks:
        parts.append("## Contrastive pairs: a draft and the version Whitney chose instead\n\n" + "\n\n".join(pair_blocks))
    if direction_blocks:
        parts.append("## Approved directions: model drafts WIA approved in Content Atelier (what to say, not how WIA "
                     "writes; never a voice model)\n\n" + "\n\n".join(direction_blocks))
    return parts


def author_label(author: str | None) -> str:
    """Whose rule it is, as the prefix shows it (R52, K49): Whitney, the team, both, or a draft of the analysis."""
    a = (author or "").strip()
    if a.startswith("Whitney and"):
        return "Whitney and the team"
    if a.startswith("Whitney"):
        return "Whitney"
    if a.startswith("team"):
        return "the team"
    if a.startswith("model"):
        return "the export analysis, from WIA's material"
    if "@" in a:
        return "a WIA reviewer"
    return a or "WIA"


def short_origin(origin: str | None) -> str | None:
    """A recorded origin the prefix can show as it is: short and quote-free."""
    origin = " ".join((origin or "").split())
    return origin if origin and len(origin) <= 120 and not any(c in origin for c in '"“$') else None


def rule_origin(row: dict) -> str:
    """A short origin for a compiled rule: its recorded origin when short and quote-free (rulings and chunk reports),
    else the conversations, chunk reports, decisions or document it cites. Quotes stay on the item, out of the prefix."""
    body, detail = row["body"], row.get("source_detail") or {}
    if origin := short_origin(body.get("origin")):
        return origin
    cites = [*detail.get("chunks", [])[:3], *detail.get("conversations", [])[:2], *detail.get("attachments", [])[:1]]
    if cites:
        return ", ".join(cites)
    if detail.get("decisions"):
        return f"{len(detail['decisions'])} Gate decisions in Content Atelier"
    if detail.get("briefs"):
        return f"Gate 2 edits on {len(detail['briefs'])} briefs in Content Atelier"
    if detail.get("document"):
        return f"{detail['document'].rsplit('/', 1)[-1]}, {detail.get('section') or 'whole document'}"
    return {"approver_entry": "entered by a WIA approver"}.get(row.get("source_kind"), row.get("source_kind") or "not recorded")


def rule_line(row: dict) -> str:
    """One compiled rule: code, statement, then level, scope, category, date, author and origin (E.B11)."""
    b = row["body"]
    meta = [b["level"], f"scope {b['scope']}"]
    if b.get("category"):
        meta.append(b["category"].replace("_", " "))
    meta.append(f"since {b['since']}" if b.get("since") else
                f"stated {row['statement_date'].isoformat()}" if row.get("statement_date") else "undated")
    meta += [f"by {author_label(row.get('author'))}", f"origin: {rule_origin(row)}"]
    head = f"{b['code']}: " if b.get("code") else ""
    return f"{head}{' '.join(b['statement'].split())} ({'; '.join(meta)})"


def _line(row: dict, heading: str | None = None) -> str:
    text = row["text"].replace("\n", " ").strip()
    if heading and text.lower().startswith(heading.lower() + ":"):
        # The section heading already says it ("## Content workflow: A typical week"); the entry does not repeat it.
        text = text[len(heading) + 1:].strip()
    return "- " + (INTERNAL if row["visibility"] == "internal" else "") + text


def _lines(rows: list[dict], heading: str | None = None) -> str:
    """Entries under one heading, each once: two items that render the same line (one entry naming two invented
    people, seeded once per name) are listed once."""
    return "\n".join(dict.fromkeys(_line(r, heading) for r in rows))


def render_document(key: str, rows: list[dict]) -> str:
    """One compiled document from its items, in a stable order. Internal items are labelled; internal and gated
    prices, and results that may never be used, are left out of the text (rulings 2.2, 2.4)."""
    rows = sorted(rows, key=lambda r: (r["kind"], r["body"].get("code") is None, r["body"].get("code") or "", r["key"],
                                       str(r.get("valid_from") or ""), r["item_id"]))
    parts = []
    if key == "team_roster":
        for state, title in ROSTER_GROUPS:
            group = [r for r in rows if r["body"].get("state") == state]
            if group:
                parts.append(f"## {title}\n" + _lines(group))
    elif key == "offer_sheet":
        offers = [r for r in rows if r["kind"] == "offer" and not r["body"].get("section")]
        current = [r for r in offers if r["body"].get("state") != "retired"]
        descriptors = [r for r in rows if r["kind"] == "offer" and r["body"].get("section") == "descriptor"]
        terms = [r for r in rows if r["kind"] == "offer" and r["body"].get("section") == "insider_term"]
        retired = [r for r in offers if r["body"].get("state") == "retired"]
        prices = [r for r in rows if r["kind"] == "price" and r["visibility"] == "public"]
        if current:
            parts.append("## Current offers\n" + _lines(current))
        if retired:
            parts.append("## Retired names, never present as current\n" + _lines(retired))
        if descriptors:
            parts.append("## Approved descriptors: when copy names an offer as the solution, it names it with one of these "
                         "(an offer name is never an insider term)\n" + _lines(descriptors))
        if terms:
            parts.append("## Insider terms: WIA's program internals a cold reader may not know. Never in first-touch text "
                         "(subjects, previews, covers, on-screen hooks, the first b-roll screen, carousel slide 1); in a "
                         "script, an email or a caption at most once, explained in the plain words given\n" + _lines(terms))
        parts.append("## Prices\n" + ("\n".join(_line(r) for r in prices) + "\n" if prices else "") +
                     "- No other price is stated in any content; internal and gated prices are never written here.")
    elif key == "rejection_rules":
        # A rule compiles as its statement, level, scope, category, date, author and a short origin (E.B11); its full
        # evidence stays on the item (the review screen). A rule stated twice in the same words is listed once.
        seen = set()
        for level, title in (("ban", "Bans: reject or rewrite"), ("flag", "Flags: warn and show the line")):
            lines = []
            for r in (r for r in rows if r["body"].get("level") == level):
                said = " ".join(r["body"]["statement"].lower().split())
                if said in seen:
                    continue
                seen.add(said)
                lines.append("- " + (INTERNAL if r["visibility"] == "internal" else "") + rule_line(r))
            if lines:
                parts.append(f"## {title}\n" + "\n".join(lines))
    elif key == "exemplars":
        parts.extend(_exemplar_sections(rows))
    elif key == "results_register":
        public = [r for r in rows if r.get("permission") == "published"]
        allowed = [r for r in rows if r.get("permission") == "client_permission"]
        private = [r for r in rows if r.get("permission") == "none" and (r["body"].get("framing") or "") != "never use"]
        if public:
            parts.append("## Published results (re-use keeps the original framing; client unnamed unless WIA named them)\n"
                         + _lines(public))
        if allowed:
            parts.append("## Results the client has allowed\n" + _lines(allowed))
        if private:
            parts.append("## Private results: context only, never in public copy without the client's permission\n"
                         + "\n".join("- " + INTERNAL + r["text"] for r in private))
    else:
        by_group: dict[str, list[dict]] = {}
        for r in rows:
            group = (r["body"].get("process") or r["body"].get("format") or r["body"].get("theme") or
                     r["body"].get("channel") or "").strip() or "Entries"
            by_group.setdefault(group, []).append(r)
        for group in sorted(by_group):
            parts.append(f"## {group}\n" + _lines(by_group[group], group))
    return "\n\n".join(parts).strip()


PATTERNS_FILE = "rejection-rules.patterns.json"
PATTERN_FIELDS = ("id", "pattern", "kind", "scope", "applies_to", "message")


def derive_patterns(rows: list[dict]) -> list[dict]:
    """The lint patterns of a version's rules (E.B11 (2)), in the rules' stable order: each rule's patterns under its
    code (or key), with the date it binds from. The E.B10 lint reads these, never a hand-kept list."""
    out = []
    for r in sorted(rows, key=lambda r: (r["body"].get("code") is None, r["body"].get("code") or "", r["key"], r["item_id"])):
        b = r["body"]
        since = next(iter(sorted(re.findall(r"\d{4}-\d\d-\d\d", b.get("since") or ""))), None) or (
            r["statement_date"].isoformat() if r.get("statement_date") else None)
        for p in b.get("patterns") or []:
            out.append({"id": b.get("code") or r["key"], "pattern": p["pattern"], "kind": p["kind"], "scope": p["scope"],
                        **({"applies_to": p["applies_to"]} if p.get("applies_to") else {}),
                        **({"since": since} if since else {}), "message": p["message"]})
    return out


FILE_ORDER = ("id", "pattern", "kind", "scope", "applies_to", "since", "message")


def patterns_text(rules: list[dict]) -> str:
    """The patterns file as written and hashed: one rule a line in a fixed key order (the database reorders keys),
    ASCII-escaped, LF endings."""
    def ordered(r):
        return {**{k: r[k] for k in FILE_ORDER if k in r}, **{k: r[k] for k in sorted(r) if k not in FILE_ORDER}}
    return "{\n  \"rules\": [\n" + ",\n".join("    " + json.dumps(ordered(r), ensure_ascii=True) for r in rules) + "\n  ]\n}"


def lint_content(rules: list[dict]) -> list[tuple]:
    """What a pattern list lints: the same ids, patterns, kinds, scopes, assets and messages, whatever their dates."""
    return [tuple(r.get(k) for k in PATTERN_FIELDS) for r in rules or []]


def _base_patterns(conn, root: Path, base_version: str) -> list[dict]:
    stored = conn.execute("SELECT value FROM settings WHERE key=%s", (MANIFEST_PREFIX + base_version,)).fetchone()
    if stored and stored["value"].get("patterns") is not None:
        return stored["value"]["patterns"]
    path = Path(root) / PATTERNS_FILE
    return json.loads(path.read_text(encoding="utf-8"))["rules"] if path.is_file() else []


def version_patterns(conn, version: str | None) -> list[dict] | None:
    """A compiled version's lint patterns, or None when the version records none (a file version before E.B11 (2))."""
    if not version:
        return None
    stored = conn.execute("SELECT value FROM settings WHERE key=%s", (MANIFEST_PREFIX + version,)).fetchone()
    return stored["value"].get("patterns") if stored else None


def _base(conn, root: Path):
    """The base version: the active compiled version, else the file-backed knowledge base."""
    active = conn.execute("SELECT value FROM settings WHERE key=%s", (ACTIVE,)).fetchone()
    if active:
        kb = load_published(conn, active["value"]["version"])
        stored = conn.execute("SELECT value FROM settings WHERE key=%s", (MANIFEST_PREFIX + kb.version,)).fetchone()["value"]
        return kb, KnowledgeBaseManifest.model_validate(stored["manifest"])
    manifest = KnowledgeBaseManifest.model_validate(json.loads((Path(root) / MANIFEST).read_text(encoding="utf-8-sig")))
    return load_knowledge_base(root), manifest


def _version_name(on: date, documents: dict, stages: dict | None = None) -> str:
    # The stages each document reaches are part of what a version is; a version that changes only them is a new one.
    named = {**documents, "_stages": stages} if stages else documents
    digest = hashlib.sha256(json.dumps(named, sort_keys=True).encode()).hexdigest()[:8]
    return f"wia-kb-{on.isoformat()}.c-{digest}"


def compile_version(conn, *, on: date, actor: str, root: Path, supersessions: bool = True, additions: bool = True) -> dict:
    """Compile a draft version from confirmed items valid on `on`; returns the version and what changed.

    The supplied documents carried over take the superseded lines of `root`'s supersessions.json in force on `on`
    (E.B25 (c)); `supersessions=False` compiles without them, as versions did before. The documents `root`'s
    additions.json adds from a date join a version whose base lacks them, once (E.B25 (e)); `additions=False` compiles
    without them."""
    if not items.table_ready(conn):
        raise RuntimeError("Apply migration 006 before compiling knowledge-base versions")
    if bad := items.uncategorised_rules(document_rows(conn, "rejection_rules", on)):
        raise ValueError(f"{len(bad)} confirmed rules have no known category, so no version compiles (E.B11); "
                         "give each one through the review queue: " + ", ".join(bad[:10]))
    base, base_manifest = _base(conn, root)
    base_docs = {d.entry.key: d for d in base.documents}
    spec, spec_sha = superseded.load(root) if supersessions else (None, None)
    already = set(base_manifest.supersessions.applied) if base_manifest.supersessions else set()
    due = superseded.due(spec, on, already)
    if missing := sorted({e["document"] for e in due} - {e.key for e in base_manifest.documents}):
        raise ValueError(f"{superseded.FILE} names documents the base version does not have: {', '.join(missing)}")
    add_spec, add_sha = added.load(root) if additions else (None, None)
    added_before = set(base_manifest.additions.applied) if base_manifest.additions else set()
    adding = added.due(add_spec, on, added_before, {e.key for e in base_manifest.documents})
    new_documents = {e["key"]: (DocumentEntry.model_validate({**added.document_entry(e, added.effective(add_spec, e)), "version": base.version}),
                                added.text(root, e)) for e in adding}
    entries, bodies, sources, changes, pending = [], {}, {}, {}, {}
    for entry in [*base_manifest.documents, *(e for e, _ in new_documents.values())]:
        key = entry.key
        kinds = COMPILED.get(key)
        rows = document_rows(conn, key, on)
        published = published_rows(conn, on) if key in PUBLISHED_DOCUMENTS else []
        waiting = conn.execute("SELECT count(*) n FROM brand_kit_items WHERE status='candidate' AND kind = ANY(%s)",
                               (list(kinds),)).fetchone()["n"] if kinds else 0
        if key in PUBLISHED_DOCUMENTS:
            waiting = conn.execute("SELECT count(*) n FROM published_content WHERE status='unconfirmed'").fetchone()["n"]
        if waiting:
            pending[key] = waiting
        # What the document leaves out because it derives from a held-out week (E.B17), for the version's record.
        withheld = held_out.withheld(_document_items(conn, key, on)) if kinds else []
        if key in PUBLISHED_DOCUMENTS:
            withheld = held_out.withheld(conn.execute("""SELECT content_id,title FROM published_content
                WHERE status='confirmed' AND published_on BETWEEN %s AND %s""", (on - timedelta(days=RECENT_DAYS), on)).fetchall())
        if published:
            text = render_published(published)
            sources[key] = {"on": on.isoformat(), "published": [r["content_id"] for r in published],
                            **({"withheld": withheld} if withheld else {})}
            new_entry = entry.model_copy(update={
                "status": "confirmed", "effective_date": on,
                "provenance": Provenance(source=f"compiled from {len(published)} published pieces WIA confirmed (L.B4)",
                                         author="WIA (confirmed published pieces)", model_written=False), "approver": None})
        elif rows:
            text = render_document(key, rows)
            sources[key] = {"on": on.isoformat(), "items": [{"id": r["item_id"], "hash": r["hash"]} for r in rows],
                            **({"withheld": withheld} if withheld else {})}
            new_entry = entry.model_copy(update={
                "status": "confirmed", "effective_date": on, "heading": COMPILED_HEADINGS.get(key, entry.heading),
                "provenance": Provenance(source=f"compiled from {len(rows)} confirmed items valid on {on.isoformat()} (L.B4)",
                                         author="WIA (confirmed items)", model_written=False), "approver": None})
        elif key in new_documents:
            text, new_entry = new_documents[key][1], entry
        else:
            text = base_docs[key].text if key in base_docs else _published_body(conn, base.version, key)
            if mine := [e for e in due if e["document"] == key]:
                text = superseded.apply(text, mine)
            new_entry = entry
        stages = _stages(key, entry.stages)
        new_entry = new_entry.model_copy(update={"stages": stages})
        bodies[key] = text
        entries.append(new_entry)
        before = base_docs[key].text if key in base_docs else None
        if before != text:
            changes[key] = "identity" if key in IDENTITY_DOCUMENTS else "operating"
        else:
            # The same text reaching another stage changes no prompt a stage already had; it takes effect on approval.
            changes[key] = "unchanged" if stages == (entry.stages or []) else "operating"
    digests = {k: hashlib.sha256(v.encode("utf-8")).hexdigest() for k, v in bodies.items()}
    # The lint patterns derive from the rules this version compiles (E.B11 (2)); while no confirmed rule carries one, the
    # base version's patterns carry over. A change to them alone is an operating change: it alters no prompt.
    base_patterns = _base_patterns(conn, root, base.version)
    rule_rows = document_rows(conn, "rejection_rules", on)
    patterns = derive_patterns(rule_rows) if any(r["body"].get("patterns") for r in rule_rows) else base_patterns
    patterns_changed = lint_content(patterns) != lint_content(base_patterns)
    if all(c == "unchanged" for c in changes.values()) and not patterns_changed:
        return {"status": "unchanged", "version": base.version, "documents": digests, "pending_candidates": pending}
    patterns_sha = hashlib.sha256(patterns_text(patterns).encode("utf-8")).hexdigest()
    version = _version_name(on, {**digests, **({"_patterns": patterns_sha} if patterns else {})}, {e.key: e.stages for e in entries})
    if conn.execute("SELECT 1 FROM brand_kit_docs WHERE version=%s LIMIT 1", (version,)).fetchone():
        stored = conn.execute("SELECT value FROM settings WHERE key=%s", (MANIFEST_PREFIX + version,)).fetchone()["value"]
        return {"status": "exists", "version": version, "documents": digests, "changes": stored["compiled"]["changes"],
                "pending_candidates": pending, "state": stored["compiled"]["state"]}
    manifest = {"knowledge_base_version": version, "format": 2,
                "documents": [e.model_copy(update={"version": version if changes[e.key] != "unchanged" else e.version}).model_dump(mode="json", exclude_none=True)
                              for e in entries]}
    if patterns:
        manifest["rule_patterns"] = {"file": PATTERNS_FILE, "sha256": patterns_sha, "rules": len(patterns)}
    applied = sorted(already | {e["id"] for e in due})
    if due:
        manifest["supersessions"] = {"file": superseded.FILE, "sha256": spec_sha, "applied": applied}
    elif base_manifest.supersessions:
        manifest["supersessions"] = base_manifest.supersessions.model_dump(mode="json")
    if adding:
        manifest["additions"] = {"file": added.FILE, "sha256": add_sha, "applied": sorted(added_before | {e["id"] for e in adding})}
    elif base_manifest.additions:
        manifest["additions"] = base_manifest.additions.model_dump(mode="json")
    for entry in entries:
        identity_change = changes[entry.key] == "identity"
        insert(conn, "brand_kit_docs", {
            "key": entry.key, "version": version, "heading": entry.heading, "owner": entry.owner, "status": (
                "confirmed" if entry.key in sources else entry.status if entry.status in ("supplied", "confirmed", "draft") else "unconfirmed"),
            "effective_date": entry.effective_date or on, "review_interval_days": entry.review_interval_days or 30,
            "approver": None, "sha256": digests[entry.key], "body": bodies[entry.key], "object_key": entry.file,
            "compiled_from": sources.get(entry.key), "benchmark_state": "pending" if identity_change else "not_required"})
    manifest_bytes = json.dumps(manifest, sort_keys=True, ensure_ascii=False).encode("utf-8")
    state = {"state": "draft", "base_version": base.version, "on": on.isoformat(), "changes": changes,
             "created_by": actor, "pending_candidates": pending,
             "patterns": {"rules": len(patterns), "changed": patterns_changed,
                          "derived_from_items": any(r["body"].get("patterns") for r in rule_rows)},
             **({"supersessions": {"applied": [e["id"] for e in due], **superseded.counts(due)}} if due else {}),
             **({"additions": {"applied": [e["id"] for e in adding], "documents": [e["key"] for e in adding]}} if adding else {})}
    conn.execute("INSERT INTO settings(key,value,updated_by) VALUES (%s,%s,%s)",
                 (MANIFEST_PREFIX + version, json.dumps({"manifest": manifest, "sha256": _manifest_sha256(manifest_bytes, 2),
                                                         "compiled": state, "patterns": patterns}), actor))
    return {"status": "compiled", "version": version, "documents": digests, "changes": changes, "pending_candidates": pending,
            "state": "draft"}


def identity_waiting(conn, on: date, root: Path) -> dict:
    """Confirmed identity items that no version has compiled yet (L.B11): the identity documents whose text, compiled
    today, would differ from the version in force, and how many of their items it does not carry (when that version was
    compiled from items). A document already compiled into a version waiting for approval or its benchmark, from the
    version in force, is not waiting to be compiled. Nothing is written."""
    if not items.table_ready(conn):
        return {"documents": [], "items": 0, "drafts": []}
    base, _ = _base(conn, root)
    base_docs = {d.entry.key: d.text for d in base.documents}
    queued = {(r["key"], r["body"]) for r in conn.execute("""SELECT d.key,d.body FROM brand_kit_docs d JOIN settings s
            ON s.key='knowledge_base.manifest.'||d.version
        WHERE s.value->'compiled'->>'state' IN ('draft','approved_pending_benchmark')
          AND s.value->'compiled'->>'base_version'=%s""", (base.version,)).fetchall()}
    used = {(i["id"], i["hash"]) for r in conn.execute("SELECT compiled_from FROM brand_kit_docs WHERE version=%s", (base.version,))
            for i in (r["compiled_from"] or {}).get("items", [])}
    documents, count = [], 0
    for key in sorted(IDENTITY_DOCUMENTS & set(COMPILED)):
        rows = document_rows(conn, key, on)
        if not rows:
            continue
        text = render_document(key, rows)
        if text == base_docs.get(key) or (key, text) in queued:
            continue
        documents.append(key)
        count += sum((r["item_id"], r["hash"]) not in used for r in rows) if used else 0
    drafts = [{"version": r["key"][len(MANIFEST_PREFIX):], "on": r["value"]["compiled"].get("on")}
              for r in conn.execute("""SELECT key,value FROM settings WHERE starts_with(key,%s)
                  AND value->'compiled'->>'state'='draft' AND value->'compiled'->>'base_version'=%s ORDER BY key""",
                                    (MANIFEST_PREFIX, base.version)).fetchall()
              if "identity" in (r["value"]["compiled"].get("changes") or {}).values()]
    return {"documents": documents, "items": count, "base_version": base.version, "drafts": drafts}


def _published_body(conn, version, key):
    row = conn.execute("SELECT body FROM brand_kit_docs WHERE version=%s AND key=%s", (version, key)).fetchone()
    if not row:
        raise ValueError(f"Base version {version} has no {key}")
    return row["body"]


def _stored(conn, version):
    row = conn.execute("SELECT value FROM settings WHERE key=%s FOR UPDATE", (MANIFEST_PREFIX + version,)).fetchone()
    if not row or "compiled" not in row["value"]:
        raise LookupError("Compiled version not found")
    return row["value"]


def _save(conn, version, value, actor):
    conn.execute("UPDATE settings SET value=%s,updated_by=%s,updated_at=now() WHERE key=%s",
                 (json.dumps(value), actor, MANIFEST_PREFIX + version))


def _activate(conn, version, actor):
    value = json.dumps({"version": version, "activated_by": actor, "activated_at": date.today().isoformat()})
    conn.execute("""INSERT INTO settings(key,value,updated_by) VALUES (%s,%s,%s)
        ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value,updated_by=EXCLUDED.updated_by,updated_at=now()""",
                 (ACTIVE, value, actor))


def _decision(conn, version, action, disposition, actor, note, details):
    decision_id = identifier("decision")
    insert(conn, "decisions", {"decision_id": decision_id, "item_kind": "brand_kit_version", "item_id": version,
                               "action": action, "disposition": disposition, "note": note, "actor": actor, "author": actor,
                               "details": details})
    return decision_id


def _require_current_base(conn, compiled):
    """A draft compiled from an older active version would roll back what was approved since: recompile it."""
    conn.execute("SELECT pg_advisory_xact_lock(7311)")
    active = active_version(conn)
    base = compiled.get("base_version")
    if active is not None and base != active:
        raise ValueError(f"This version was compiled from {base}, but {active} is active now; compile again")


def approve(conn, settings, version: str, actor: str, *, note: str) -> dict:
    """Approve a draft version. Operating-only versions activate at once; identity changes wait for a benchmark when
    `context.release.benchmark_required` is on, and activate at once when it is off."""
    from ..settings_store import value as setting
    from .review import require, require_reviewer
    require_reviewer(settings, actor)
    value = _stored(conn, version)
    compiled = value["compiled"]
    identity = [k for k, c in compiled["changes"].items() if c == "identity"]
    require(settings, actor, "rule" if identity else "offer")
    _require_current_base(conn, compiled)
    if compiled["state"] != "draft":
        raise ValueError(f"This version is already {compiled['state'].replace('_', ' ')}")
    if not (note or "").strip():
        raise ValueError("An approval records its note")
    conn.execute("UPDATE brand_kit_docs SET approver=%s,approved_at=now() WHERE version=%s", (actor, version))
    waits = bool(identity) and setting("context.release.benchmark_required", conn)
    compiled.update(state="approved_pending_benchmark" if waits else "active", approved_by=actor,
                    approved_on=date.today().isoformat())
    if identity and not waits:
        compiled["released_without_benchmark"] = {"by": actor, "basis": "context.release.benchmark_required is off"}
    if not waits:
        _activate(conn, version, actor)
    _save(conn, version, value, actor)
    decision_id = _decision(conn, version, "kb_approve", "approve", actor, note.strip(),
                            {"changes": compiled["changes"], "identity_documents": identity})
    return {"version": version, "state": compiled["state"], "decision_id": decision_id,
            "pending_benchmark": identity if waits else []}


def used_by_runs(conn, version: str) -> bool:
    """Whether any run or model call recorded this version (its name is a unique fingerprint, so any mention counts)."""
    if conn.execute("SELECT 1 FROM pipeline_runs WHERE strpos(input_refs::text, %s) > 0 LIMIT 1", (version,)).fetchone():
        return True
    return bool(conn.execute("SELECT 1 FROM llm_runs WHERE knowledge_base_version=%s LIMIT 1", (version,)).fetchone())


def discard(conn, settings, version: str, actor: str) -> dict:
    """Remove a draft version nobody approved or used: its documents and its manifest go, and the decision is kept. A
    version that is active, approved, pinned or recorded by any run stays, so what a run read can always be read again."""
    from ..settings_store import knowledge_base_pin
    from .review import require, require_reviewer
    require_reviewer(settings, actor)
    require(settings, actor)
    value = _stored(conn, version)
    compiled = value["compiled"]
    if version == active_version(conn):
        raise ValueError("This version is the one in use, so it cannot be discarded")
    if compiled["state"] != "draft":
        raise ValueError("This version has been approved, so it is kept")
    if knowledge_base_pin(conn) == version:
        raise ValueError("Settings pin this version, so it cannot be discarded")
    if used_by_runs(conn, version):
        raise ValueError("A run has used this version, so it is kept")
    conn.execute("DELETE FROM brand_kit_docs WHERE version=%s", (version,))
    conn.execute("DELETE FROM settings WHERE key=%s", (MANIFEST_PREFIX + version,))
    decision_id = _decision(conn, version, "kb_discard", "reject", actor, None,
                            {"changes": compiled.get("changes"), "base_version": compiled.get("base_version")})
    return {"version": version, "state": "discarded", "decision_id": decision_id}


def record_benchmark(conn, settings, version: str, actor: str, *, passed: bool, result_ref: str, note: str) -> dict:
    """Store an E.B3 smoke result for an approved identity change; a pass makes the version active (R44)."""
    from .review import require
    require(settings, actor, "rule")  # an identity approver before anything is read (L.B3)
    value = _stored(conn, version)
    compiled = value["compiled"]
    _require_current_base(conn, compiled)
    if compiled["state"] != "approved_pending_benchmark":
        raise ValueError("Only an approved version with an identity change waits for a benchmark")
    if not (result_ref or "").strip():
        raise ValueError("Name the benchmark result (its file or run) behind this decision")
    state = "passed" if passed else "failed"
    conn.execute("UPDATE brand_kit_docs SET benchmark_state=%s WHERE version=%s AND benchmark_state='pending'", (state, version))
    compiled.update(state="active" if passed else "benchmark_failed", benchmark={"result": result_ref, "passed": passed,
                                                                                "recorded_by": actor, "note": note})
    if passed:
        _activate(conn, version, actor)
    _save(conn, version, value, actor)
    decision_id = _decision(conn, version, "kb_benchmark", "approve" if passed else "reject", actor, note or None,
                            {"result": result_ref, "passed": passed})
    return {"version": version, "state": compiled["state"], "decision_id": decision_id}


def export(conn, version: str, directory: Path) -> dict:
    """Write a version as a file knowledge base (manifest format 2 and one file per document), so the committed
    knowledge base, the offline fixture and every environment without a database use the reviewed content."""
    stored = conn.execute("SELECT value FROM settings WHERE key=%s", (MANIFEST_PREFIX + version,)).fetchone()
    if not stored:
        raise LookupError("Version not found")
    manifest = stored["value"]["manifest"]
    bodies = {r["key"]: r for r in conn.execute("SELECT key,body,approver,approved_at FROM brand_kit_docs WHERE version=%s", (version,))}
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    for entry in manifest["documents"]:
        (directory / entry["file"]).write_text(bodies[entry["key"]]["body"] + "\n", encoding="utf-8", newline="\n")
        if bodies[entry["key"]]["approver"] and not entry.get("approver"):
            entry["approver"] = bodies[entry["key"]]["approver"]
    if manifest.get("rule_patterns"):
        # The lint patterns are written from the version, never by hand; the loader checks them against this hash.
        (directory / manifest["rule_patterns"]["file"]).write_text(patterns_text(stored["value"]["patterns"]) + "\n",
                                                                   encoding="utf-8", newline="\n")
    (directory / MANIFEST).write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    files = load_knowledge_base(directory)
    published = load_published(conn, version)
    if {d.entry.key: d.sha256 for d in files.documents} != {d.entry.key: d.sha256 for d in published.documents} \
            or files.rule_patterns_sha256 != published.rule_patterns_sha256:
        raise RuntimeError("The exported files do not reproduce the version's hashes")
    return {"version": version, "directory": str(directory), "documents": len(files.documents), "sha256": files.sha256}


def active_version(conn) -> str | None:
    if not conn.execute("SELECT to_regclass('public.settings') AS t").fetchone()["t"]:
        return None
    row = conn.execute("SELECT value FROM settings WHERE key=%s", (ACTIVE,)).fetchone()
    return row["value"]["version"] if row else None


def versions(conn) -> list[dict]:
    rows = conn.execute("SELECT key,value,updated_at FROM settings WHERE starts_with(key,%s) ORDER BY updated_at DESC",
                        (MANIFEST_PREFIX,)).fetchall()
    active = active_version(conn)
    out = []
    for r in rows:
        version = r["key"][len(MANIFEST_PREFIX):]
        compiled = r["value"].get("compiled") or {"state": "published from files"}
        runs = conn.execute("""SELECT run_id,run_scope,status,created_at FROM pipeline_runs
            WHERE jsonb_path_exists(input_refs, '$.**.knowledge_base.version ? (@ == $v)', jsonb_build_object('v', %s::text))
            ORDER BY created_at DESC LIMIT 50""", (version,)).fetchall()
        out.append({"version": version, "active": version == active, **{k: v for k, v in compiled.items()},
                    "runs": [{**dict(x), "created_at": x["created_at"].isoformat()} for x in runs]})
    return out


def diff(conn, version: str, against: str | None = None) -> dict:
    """Per-document unified diff between a version and its base (or another version)."""
    value = _stored(conn, version)
    against = against or value["compiled"]["base_version"]
    new = {r["key"]: r["body"] for r in conn.execute("SELECT key,body FROM brand_kit_docs WHERE version=%s", (version,))}
    old = {r["key"]: r["body"] for r in conn.execute("SELECT key,body FROM brand_kit_docs WHERE version=%s", (against,))}
    if not old:
        # A file version as base: the committed one, or an earlier one kept under archive/ once a compiled version
        # replaced it; the diff names the base it was taken from.
        from ..cycle.verification import knowledge_root
        root = Path(knowledge_root())
        files = load_knowledge_base(root / "archive" / against if against and (root / "archive" / against).is_dir() else root)
        against = files.version
        old = {d.entry.key: d.text for d in files.documents}
    documents = []
    for key in new:
        if new[key] == old.get(key):
            continue
        lines = list(difflib.unified_diff((old.get(key) or "").splitlines(), new[key].splitlines(), against, version, lineterm="", n=1))
        documents.append({"key": key, "change": value["compiled"]["changes"].get(key), "diff": "\n".join(lines)})
    return {"version": version, "against": against, "state": value["compiled"]["state"], "documents": documents}
