"""The context-assembly service (L.B5, section 4.12, R51): the one place a stage gets its context from.

`assemble(stage, ...)` returns what that stage receives:

- **Every stage:** the knowledge-base prefix. Identity documents (voice, rules, exemplars, beliefs, format) come
  only from the active approved version, or from the file-backed knowledge base before any version is active
  (the offline fixture). Operating documents (roster, offer sheet, CTA catalogue, results register, process
  catalogue, content plan) are rendered from the confirmed items valid on the run date, so a changed price or a
  new team member reaches the next run without a new version, and an expired item never does. Internal items are
  labelled "internal: never state publicly"; internal and gated prices never enter any document (rulings 2.2).
- **Strategist:** a dated situational block for the user message: the content plan and campaigns valid on the
  date, and pieces published in the last 90 days with their performance.
- **Brief writer:** up to `ATELIER_CONTEXT_EXEMPLARS_K` confirmed exemplars chosen by channel and pillar, in
  place of the whole exemplar document.
- **Verifier:** the roster (former staff and invented names flagged), the rejection-rule patterns, the
  figures of internal items, which it blocks in public copy, and WIA's central points published in the last twelve
  months, which its same-point check compares each card with (E.B25 (f)).
- **Extraction:** the roster with name variants, and the process catalogue.

Every run records the knowledge-base version, the document hashes, and the IDs and hashes of the items it used
(`refs()["context"]`). Budgets come from settings with the section 4.12 defaults.

**The prefix budget is enforced** (E.B25 (d), K50): when a stage's prefix exceeds `context.budget.prefix_tokens`, whole
documents leave it from the bottom of the recorded priority list (`PREFIX_PRIORITY`, versioned as
`PREFIX_PRIORITY_VERSION`) until it fits. The rejection rules, beliefs, voice guide, content strategy, roster and offer
sheet never leave, nor does a document the list does not name (the brief's format guide and CTA catalogue). The run
records the list's version, the budget, the tokens before and after, and what was dropped (`context.prefix_budget`); a
file-backed run that drops nothing records nothing, so its refs are what they were. The setting is the only knob.
"""
from __future__ import annotations

import hashlib
import re
from datetime import date, timedelta
from pathlib import Path

from ..knowledge_base import HEADER_V2, KnowledgeBase, LoadedDocument, _section, load_knowledge_base, load_published, team_roster
from . import compiler, held_out, items, published_points, staleness

STAGES = ("strategist", "brief", "verifier", "extraction", "pack")
# The pack finisher's knowledge base (NP.B7, the content-packs plan section 5.4): of the documents the version marks for the
# brief, her voice, the format guide, the CTA catalogue, the exemplars, the editing guide, her spoken voice and her
# raw-to-final chains, in this order; the planning probe's set. The whole exemplar document stays: the finisher edits every
# format, so no channel's exemplars are chosen out. About 17,000 tokens, inside the prefix budget.
PACK_DOCUMENTS = ("founder_voice_guide", "format_guide", "cta_catalogue", "exemplars", "editing_guide", "spoken_voice",
                  "transformations")


def _load_stage(stage: str) -> str:
    return "brief" if stage == "pack" else stage


def _pack_documents(documents: list[LoadedDocument]) -> list[LoadedDocument]:
    by_key = {d.entry.key: d for d in documents}
    return [by_key[k] for k in PACK_DOCUMENTS if k in by_key]
# Operating documents are rendered live from confirmed items; the rest come from the approved version.
LIVE_DOCUMENTS = {key: kinds for key, kinds in compiler.COMPILED.items() if kinds and set(kinds) <= items.OPERATING_KINDS}
RECENT_DAYS = 90


def stable_refs(refs: dict | None) -> dict | None:
    """The part of a run's knowledge-base refs that must not change while the run is in flight: the version, its
    manifest and the identity documents. Operating facts confirmed mid-run are used as they stand and recorded."""
    if not refs or not refs.get("context"):
        return refs
    identity = sorted((d["key"], d["sha256"]) for d in refs.get("documents", []) if d["key"] not in LIVE_DOCUMENTS)
    return {"version": refs.get("version"), "manifest_sha256": refs.get("manifest_sha256"), "identity_documents": identity,
            "source": refs["context"].get("source")}


def budgets(conn=None) -> dict:
    """Token budgets (section 4.12), from settings (context.budget.*, context.exemplars.k); about four characters a token."""
    from ..settings_store import values
    v = values(("context.budget.prefix_tokens", "context.budget.situational_tokens", "context.budget.exemplar_tokens",
                "context.exemplars.k"), conn)
    return {"prefix": v["context.budget.prefix_tokens"], "situational": v["context.budget.situational_tokens"],
            "exemplars": v["context.budget.exemplar_tokens"], "exemplars_k": v["context.exemplars.k"]}


def tokens(text: str) -> int:
    return (len(text or "") + 3) // 4


# E.B25 (d): the order in which a prefix over its budget gives up whole documents, highest priority first (the owner's
# list of 20 October, for the strategist and the brief writer; the verifier and extraction stages are well inside the
# budget and keep everything unless that changes). A change to the list is a new version.
PREFIX_PRIORITY_VERSION = "prefix-priority.v2"
PREFIX_PRIORITY = ("rejection_rules", "belief_statements", "founder_voice_guide", "editing_guide", "content_strategy",
                   "team_roster", "offer_sheet", "exemplars", "audience_language", "content_plan", "recent_published",
                   "process_catalogue", "results_register", "accelerator_strategy", "content_workflow")
NEVER_DROPPED = frozenset({"rejection_rules", "belief_statements", "founder_voice_guide", "content_strategy", "team_roster",
                           "offer_sheet"})
# Knowledge-base version 9 (E.B25 (j), L.B12) adds Whitney's spoken voice (18, brief only) and her raw-to-final chains (19,
# strategist and brief). A version that holds either is assembled under prefix-priority.v3: her own words rank just below
# the never-dropped core, ahead of the exemplar snippets (15), and the audience language leaves before the process
# catalogue (rubric criterion 1: how WIA works). A version without them keeps v2, so its runs assemble exactly as before.
PREFIX_PRIORITY_V3_VERSION = "prefix-priority.v3"
PREFIX_PRIORITY_V3 = ("rejection_rules", "belief_statements", "founder_voice_guide", "editing_guide", "content_strategy",
                      "team_roster", "offer_sheet", "spoken_voice", "transformations", "exemplars", "process_catalogue",
                      "audience_language", "content_plan", "recent_published", "results_register", "accelerator_strategy",
                      "content_workflow")
V3_DOCUMENTS = frozenset({"spoken_voice", "transformations"})


def priority_for(documents: list[LoadedDocument]) -> tuple[str, tuple[str, ...]]:
    """The priority list a prefix is cut by: v3 when the version holds document 18 or 19, else v2."""
    if any(d.entry.key in V3_DOCUMENTS for d in documents):
        return PREFIX_PRIORITY_V3_VERSION, PREFIX_PRIORITY_V3
    return PREFIX_PRIORITY_VERSION, PREFIX_PRIORITY


def within_budget(kb: KnowledgeBase, documents: list[LoadedDocument], budget: int) -> tuple[list[LoadedDocument], str, dict]:
    """The documents a stage keeps under its prefix budget, their text, and the record: from the lowest priority up, whole
    documents leave until the prefix fits or only documents that never leave remain (then it stays over, and says so)."""
    text = _rebuild(kb, documents)
    before, dropped = tokens(text), []
    version, priority = priority_for(documents)
    droppable = [k for k in reversed(priority) if k not in NEVER_DROPPED]
    for key in droppable:
        if tokens(text) <= budget:
            break
        if any(d.entry.key == key for d in documents):
            documents = [d for d in documents if d.entry.key != key]
            dropped.append(key)
            text = _rebuild(kb, documents)
    return documents, text, {"priority": version, "budget": budget, "tokens_before": before,
                             "tokens_after": tokens(text), "dropped": dropped, "over_budget": tokens(text) > budget}


class AssembledKnowledgeBase(KnowledgeBase):
    """A knowledge base as one stage receives it, with what was assembled and from where."""
    context: dict | None = None
    situational: str | None = None
    roster: list[dict] = []
    internal_terms: list[dict] = []
    exemplars: list[dict] = []
    # The verifier's same-point check (E.B25 (f)): WIA's central points published in the last twelve months.
    published_points: list[dict] = []

    def refs(self) -> dict:
        refs = super().refs()
        if self.context:
            refs["context"] = self.context
        return refs


def _tables(conn) -> bool:
    return bool(conn.execute("""SELECT to_regclass('public.brand_kit_items') IS NOT NULL
        AND to_regclass('public.settings') IS NOT NULL AS ok""").fetchone()["ok"])


def _roster_rows(conn, on) -> list[dict]:
    rows = items.items_valid_at(conn, "roster_member", on)
    out = []
    for r in rows:
        b = r["body"]
        status = {"current": "current", "former": "former", "invented": "invented"}.get(b["state"], "outside")
        aliases = list(dict.fromkeys([b["name"], b["name"].split()[0], *b.get("aliases", [])]))
        out.append({"name": b["name"], "role": b["role"], "status": status, "aliases": aliases, "item_id": r["item_id"]})
    return out


def roster(root: Path, conn=None, on: date | None = None) -> list[dict]:
    """The roster every stage uses: confirmed roster items valid on the date, else the roster document."""
    if conn is not None and _tables(conn):
        rows = _roster_rows(conn, on or date.today())
        if rows:
            return [{k: r[k] for k in ("name", "role", "status", "aliases")} for r in rows]
    return [{k: r[k] for k in ("name", "role", "status", "aliases")} for r in team_roster(Path(root))]


def contains_internal(text: str, terms: list[dict]) -> list[str]:
    """The internal terms a text states, matched as whole figures or phrases."""
    return [t["term"] for t in terms if items.contains_term(text, t["term"])]


def internal_terms(conn, on: date) -> list[dict]:
    """Figures and phrases of internal items valid on the date, which the verifier blocks in public copy."""
    out = []
    for r in conn.execute(f"""SELECT item_id,kind,body,text FROM brand_kit_items WHERE visibility='internal'
            AND {items.VALID_AT} ORDER BY item_id""", (on, on)).fetchall():
        # Every internal item, not only prices: its stored block terms, and the figures and quoted words it states.
        said = " ".join([r["text"] or "", *(v for v in r["body"].values() if isinstance(v, str))])
        for term in dict.fromkeys([*(r["body"].get("block_terms") or []), *items.internal_phrases(said)]):
            out.append({"term": term, "item_id": r["item_id"], "kind": r["kind"]})
    return out


def file_internal_terms(root: Path, allow_placeholders: bool = False) -> list[dict]:
    """The internal lines of the file-backed knowledge base, which stand for the store's internal items there."""
    out, label = [], compiler.INTERNAL.strip()
    for doc in load_knowledge_base(root, allow_placeholders=allow_placeholders).documents:
        for n, line in enumerate(doc.text.splitlines()):
            if label in line:
                said = re.sub(r"\(source:[^)]*\)", "", line.split(label, 1)[1])
                out += [{"term": t, "item_id": f"{doc.entry.key}:line{n + 1}", "kind": "document_line"}
                        for t in items.internal_phrases(said)]
    return out


def version_items(conn, version, key) -> set[str]:
    """The item IDs a version's compiled document was built from (empty for a document carried over whole)."""
    row = conn.execute("SELECT compiled_from FROM brand_kit_docs WHERE version=%s AND key=%s", (version, key)).fetchone()
    return {i["id"] for i in ((row or {}).get("compiled_from") or {}).get("items", [])}


def _exemplars(conn, on, channels, pillar, k, budget, allowed: set[str] | None = None) -> list[dict]:
    """Exemplars for the brief writer by channel and pillar. `allowed` limits them to the items of an approved version:
    an exemplar is identity, which reaches a stage only through an approved, benchmarked version (R44, L.B4)."""
    rows = held_out.keep(items.items_valid_at(conn, "exemplar", on))
    if allowed is not None:
        rows = [r for r in rows if r["item_id"] in allowed]
    wanted = {c.lower() for c in channels or ()}

    def score(r):
        b = r["body"]
        # WIA's own copy before a model's draft WIA approved (L.B4): a direction is never chosen over her voice.
        return (bool(wanted) and b["channel"].lower() in wanted, bool(pillar) and (b.get("pillar") or "").lower() == pillar.lower(),
                not compiler.mined_draft(r), not r.get("model_written"), b.get("label") in ("approved_final", "published_final"),
                r["statement_date"] or date.min, r["item_id"])
    chosen, used = [], 0
    for r in sorted(rows, key=score, reverse=True):
        if wanted and r["body"]["channel"].lower() not in wanted:
            continue
        cost = tokens(r["text"])
        if len(chosen) >= k or used + cost > budget:
            continue
        chosen.append(r)
        used += cost
    return chosen


def _situational(conn, on, budget) -> tuple[str | None, list[dict]]:
    """Content plan, campaigns and recent published pieces with performance, dated, for the user message."""
    plan = held_out.keep(items.items_valid_at(conn, None, on, kinds=("content_plan_entry", "campaign")))
    recent = held_out.keep(conn.execute("""SELECT content_id,published_on,channel,title,key_message,status,performance FROM published_content
        WHERE published_on BETWEEN %s AND %s ORDER BY published_on DESC, content_id""", (on - timedelta(days=RECENT_DAYS), on)).fetchall())
    # The year before that (E.B25 (f)): confirmed central points only, so the strategist avoids a point the verifier's
    # same-point check would flag; lowest priority, cut first by the budget.
    seen = {r["content_id"] for r in recent}
    year = [p for p in published_points.recent(conn, on) if p["content_id"] not in seen]
    if not plan and not recent and not year:
        return None, []
    from .performance import strongest_and_weakest
    lines = [f"## Situation on {on.isoformat()} (WIA's plan and recent publishing; context, not call evidence)"]
    refs = []
    if plan:
        lines.append("### Content plan and campaigns")
        for r in plan:
            lines.append("- " + (compiler.INTERNAL if r["visibility"] == "internal" else "") + r["text"])
            refs.append({"id": r["item_id"], "hash": r["hash"]})
    if recent:
        lines.append(f"### Published in the last {RECENT_DAYS} days (do not repeat a central point already published)")
        for r in recent:
            note = "" if r["status"] == "confirmed" else " (unconfirmed)"
            point = f" (central point: {r['key_message']})" if r["key_message"] else ""
            lines.append(f"- {r['published_on'].isoformat()} {r['channel']}: {r['title']}{point}{note}")
            refs.append({"published": r["content_id"]})
        best, worst = strongest_and_weakest(recent)
        if best:
            lines.append("### Strongest recent pieces\n" + "\n".join(f"- {p}" for p in best))
        if worst:
            lines.append("### Weakest recent pieces\n" + "\n".join(f"- {p}" for p in worst))
    if year:
        lines.append("### Central points WIA published earlier in the last twelve months (do not repeat one; if a card returns "
                     "to one, it says what is new since)")
        for p in year:
            lines.append(f"- {p['published_on']} {p['channel']}: {p['key_message']}")
            refs.append({"published": p["content_id"]})
    text, kept = "", []
    for line in lines:
        if tokens(text + line) > budget:
            break
        text += line + "\n"
        kept.append(line)
    return text.strip(), refs


def _rebuild(kb: KnowledgeBase, documents: list[LoadedDocument]) -> str:
    return "\n\n".join([HEADER_V2.format(version=kb.version)] + [_section(d.entry, d.text, 2) for d in documents])


def assemble(stage: str, *, root: Path, connection=None, on: date | None = None, allow_placeholders: bool = False,
             channels=(), pillar: str | None = None, version: str | None = None) -> AssembledKnowledgeBase:
    """The context for one stage. `connection` is a context-manager factory for the database, or None (files only).
    `version` evaluates a named version instead of the active one: the E.B3 smoke run behind an identity change."""
    if stage not in STAGES:
        raise ValueError(f"Unknown stage: {stage}")
    on = on or date.today()
    if connection is None:
        return _files(stage, root, allow_placeholders)
    with connection() as conn:
        if not _tables(conn):
            return _files(stage, root, allow_placeholders)
        # The knowledge_base.version setting pins a compiled version for every stage (0.B8); blank follows the active one.
        from ..settings_store import knowledge_base_pin
        version = version or knowledge_base_pin(conn) or compiler.active_version(conn)
        base = load_published(conn, version, stage=_load_stage(stage)) if version else load_knowledge_base(
            root, allow_placeholders=allow_placeholders, stage=_load_stage(stage))
        if base.format != 2:
            return _files(stage, root, allow_placeholders)
        b = budgets(conn)
        documents, used, expired = [], {}, []
        compiled = {r["key"] for r in conn.execute(
            "SELECT key FROM brand_kit_docs WHERE version=%s AND compiled_from IS NOT NULL", (version,))} if version else set()
        for doc in base.documents:
            rows = compiler.document_rows(conn, doc.entry.key, on) if doc.entry.key in LIVE_DOCUMENTS else []
            if rows or doc.entry.key in LIVE_DOCUMENTS and doc.entry.key in compiled:
                # A compiled operating document is rebuilt from the items valid today, even when none is: the approved
                # version's text would otherwise still carry every entry that has since expired (L.B5).
                text = compiler.render_document(doc.entry.key, rows) if rows else (
                    compiler.render_document(doc.entry.key, []).strip() or "- Nothing current: every entry has passed its end date.")
                entry = doc.entry.model_copy(update={"status": "confirmed", "effective_date": on})
                doc = LoadedDocument(entry=entry, text=text, sha256=hashlib.sha256(text.encode("utf-8")).hexdigest())
                used[doc.entry.key] = [{"id": r["item_id"], "hash": r["hash"]} for r in rows]
            documents.append(doc)
        if version:
            # Items the approved version was compiled from that are no longer valid on the run date.
            valid = {i["id"] for ids in used.values() for i in ids}
            for row in conn.execute("SELECT key,compiled_from FROM brand_kit_docs WHERE version=%s AND compiled_from IS NOT NULL", (version,)):
                if row["key"] in LIVE_DOCUMENTS:
                    expired += [i["id"] for i in row["compiled_from"]["items"] if i["id"] not in valid]
        if stage == "pack":
            documents = _pack_documents(documents)
        exemplars = []
        if stage == "brief":
            chosen = _exemplars(conn, on, channels, pillar, b["exemplars_k"], b["exemplars"],
                                allowed=version_items(conn, version, "exemplars") if version else set())
            if chosen:
                text = "\n\n".join(f"### {r['body']['channel']}" + (f", {r['body']['pillar']}" if r["body"].get("pillar") else "")
                                   + f" ({(r['statement_date'] or on).isoformat()})\n{r['body']['text']}" for r in chosen)
                exemplars = [{"id": r["item_id"], "hash": r["hash"], "channel": r["body"]["channel"]} for r in chosen]
                documents = [d if d.entry.key != "exemplars" else LoadedDocument(
                    entry=d.entry.model_copy(update={"status": "confirmed",
                                                     "heading": "Exemplars chosen for this brief (WIA-approved; patterns, not formulas)"}),
                    text=text, sha256=hashlib.sha256(text.encode("utf-8")).hexdigest()) for d in documents]
        situational, situational_refs = (None, [])
        if stage == "strategist":
            situational, situational_refs = _situational(conn, on, b["situational"])
        terms = internal_terms(conn, on) if stage in ("verifier", "brief", "pack") else []
        points = published_points.recent(conn, on) if stage == "verifier" else []
        if not (version or used or exemplars or situational_refs or terms or points):
            # Nothing came from the store: the run sees, and records, exactly the file-backed knowledge base.
            return _files(stage, root, allow_placeholders)
        if terms and not version:
            # The documents are still the files', so their internal lines are blocked too.
            terms += file_internal_terms(root, allow_placeholders)
        documents, text, budget = within_budget(base, documents, b["prefix"])
        people = roster(root, conn, on)
        context = {"source": "database" if version else "files", "on": on.isoformat(), "version": base.version,
                   "documents": [{"key": d.entry.key, "sha256": d.sha256} for d in documents],
                   "items": used, "expired_excluded": sorted(set(expired)), "exemplars": exemplars,
                   "situational": situational_refs, "internal_terms": [t["item_id"] for t in terms],
                   **({"published_points": [p["content_id"] for p in points]} if points else {}),
                   "tokens": {"prefix": tokens(text), "situational": tokens(situational or "")},
                   "warnings": [w["message"] for w in staleness.warnings(conn, on)],
                   "prefix_budget": budget, "over_budget": budget["over_budget"]}
        return AssembledKnowledgeBase(version=base.version, format=2, stage=stage, manifest_sha256=base.manifest_sha256,
                                      documents=documents, text=text, context=context, situational=situational,
                                      roster=people, internal_terms=terms, exemplars=exemplars, published_points=points,
                                      rule_patterns=base.rule_patterns, rule_patterns_sha256=base.rule_patterns_sha256)


def _files(stage, root, allow_placeholders) -> AssembledKnowledgeBase:
    """The file-backed knowledge base, unchanged: the offline fixture and the default before Phase L's store."""
    kb = load_knowledge_base(root, allow_placeholders=allow_placeholders, stage=_load_stage(stage))
    terms = file_internal_terms(root, allow_placeholders) if stage in ("verifier", "brief", "pack") else []
    fields = kb.model_dump()
    if kb.format == 2 and stage == "pack":
        documents = _pack_documents(kb.documents)
        fields.update(documents=[d.model_dump() for d in documents], text=_rebuild(kb, documents), stage="pack",
                      context={"source": "files", "version": kb.version, "documents": [{"key": d.entry.key, "sha256": d.sha256}
                                                                                      for d in documents]})
    elif kb.format == 2:
        documents, text, budget = within_budget(kb, kb.documents, budgets()["prefix"])
        if budget["dropped"] or budget["over_budget"]:
            fields.update(documents=[d.model_dump() for d in documents], text=text,
                          context={"source": "files", "version": kb.version, "prefix_budget": budget})
    return AssembledKnowledgeBase(**fields, roster=roster(root), internal_terms=terms)
