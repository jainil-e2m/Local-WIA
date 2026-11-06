"""Repeat corrections become rules (L.B14; R60: a correction given twice becomes a rule candidate).

The learning loop (L.B6, `mining.py`) mines Gate reasons with a reason code and the edits between brief versions. A
correction WIA gives as feedback reached none of it: the note on a Gate 1 or Gate 2 decision, the feedback of a card
refresh (3.B7, a `card_refresh` run's `feedback`; a refresh writes no decision row), the instructions of a brief refresh
(5.B6, a brief run's `instructions` with `revision_of`) and a content pack's review note (NP.B13: back to review, or ready,
with a note; a person's pack edits reach the loop as authored edits, `mining.edit_diffs`). On 20 October Whitney repeated two corrections she had given on 13
October (the subject line, slide 1) and nothing noticed.

Here every such feedback in the support window (`context.mining.support_weeks`) is sorted into a kind of correction by
fixed patterns (`KINDS`: subject lines, slide 1, covers and hooks, insider terms, who did what, register, how-to drift,
CTAs, length, em dashes), deterministic and with no model call. A kind given twice, on two different cards or briefs or on
two different days, with at least one of them in the mined window, becomes one rule candidate in the review queue: the
kind's rule in general terms (never the client's words), citing every feedback behind it, its authors and dates. Feedback
of no known kind is grouped by wording as the loop groups Gate reasons (`mining.clusters`), and a group of two becomes a
candidate whose statement is the reviewer's note, for the reviewer to restate. Feedback already behind a learned rule
never supports another, so each pattern is proposed once; nothing confirms itself (L.B3).
"""
from __future__ import annotations

import re
from datetime import date

SOURCE = "gate_feedback"
# Each kind: the patterns that recognise it in feedback, the rule it proposes (in general terms), the rule's category
# (E.B11) and scope. The order decides a feedback naming two kinds: the first match.
KINDS = (
    ("subject_line", r"\bsubject(?:\s+lines?)?\b", "Email subject lines state WIA's counter-expected point or the reader's "
     "own question or problem, not the process and never a narration of what a third party did (first-touch rule 3)", "voice", "brief"),
    ("slide_one", r"\bslide\s+(?:one|1)\b|\bfirst\s+slide\b", "Carousel slide 1 carries the carousel's title or promise for a "
     "cold reader; a bare quote or a teaser is not a slide 1 (first-touch rule 2)", "voice", "brief"),
    ("insider_term", r"\boffice[- ]hours\b|\bjargon\b|\binsider\b|\bthe vault\b|\bwon'?t know (?:the|what)\b|\bnot in the program\b",
     "WIA's program internals never appear in first-touch text, and at most once in a script or body, explained in plain words "
     "(first-touch rule 4)", "audience", "brief"),
    ("who_did_what", r"\bwho did\b|\bwho (?:made|changed|decided)\b|\bcredit(?:ed|s)?\b|\battribut", "Story beats keep the actor "
     "the record names, or the fact a reviewer attested at a gate (first-touch rule 5)", "factual", "all"),
    ("specific", r"\bcovers?\b|\b(?:hook|title|screen)\b[^.]{0,60}\b(?:specific|ambiguous|vague|generic|about ads)\b|"
     r"\b(?:more specific|so ambiguous|too vague)\b", "Covers, on-screen hooks and first screens name the concrete subject (ads, "
     "budget, Google, Meta, inquiries) so a cold reader knows what it is about (first-touch rule 1)", "voice", "brief"),
    ("register", r"\b(?:casual|polished|conversational|punchier|stiff|formal|robotic)\b", "Scripts are spoken: casual, a little "
     "unpolished, punchy first lines; emails and captions stay written", "voice", "brief"),
    ("how_to", r"\bhow-?to\b|\beducational\b|\btutorial\b|\blesson\b|\bteaching\b", "Content shows WIA's thinking and work; it "
     "never turns into a how-to lesson for the reader", "audience", "all"),
    ("cta", r"\bcta\b|\bcall to action\b|\bfollow along\b", "CTAs use the closings in the CTA catalogue; never a pattern she "
     "does not use", "cta", "brief"),
    ("length", r"\btoo long\b|\btoo short\b|\bshorter\b|\bcut (?:it )?down\b", "Keep each asset within its format's length "
     "(KB 09)", "voice", "brief"),
    ("em_dash", r"\bem[- ]?dash(?:es)?\b|\bm dash(?:es)?\b|—", "No em dashes in new copy (V01)", "voice", "all"),
)
_PATTERNS = [(kind, re.compile(pattern, re.I), statement, category, scope) for kind, pattern, statement, category, scope in KINDS]


def kind_of(text: str) -> str | None:
    """The kind of correction a feedback gives, by fixed patterns; None when it names no known kind."""
    for kind, pattern, *_ in _PATTERNS:
        if pattern.search(text or ""):
            return kind
    return None


def feedback(conn, since: date, until: date) -> list[dict]:
    """Every feedback given at a gate between the two dates: decision notes, card refresh feedback, brief refresh
    instructions. Each record names its source, the card or brief it was about, its author and day."""
    out = []
    for r in conn.execute("""SELECT decision_id,item_kind,item_id,note,author,created_at FROM decisions
            WHERE item_kind IN ('angle','considered_idea','brief') AND coalesce(btrim(note),'')<>''
            AND created_at::date BETWEEN %s AND %s ORDER BY created_at,decision_id""", (since, until)).fetchall():
        out.append({"id": f"decision:{r['decision_id']}", "source": "gate_decision", "item": f"{r['item_kind']}:{r['item_id']}",
                    "text": r["note"], "author": r["author"], "on": r["created_at"].date(), "decision_id": r["decision_id"]})
    # A content pack's review note (NP.B13): sending it back to review, or marking it ready, with a note. Its item is the
    # pack's brief, so the versions of one pack are one item.
    for r in conn.execute("""SELECT decision_id,item_id,note,author,created_at,details FROM decisions WHERE item_kind='pack'
            AND action IN ('pack_in_review','pack_ready_to_publish') AND coalesce(btrim(note),'')<>''
            AND created_at::date BETWEEN %s AND %s ORDER BY created_at,decision_id""", (since, until)).fetchall():
        brief_id = (r["details"] or {}).get("brief_id")
        out.append({"id": f"decision:{r['decision_id']}", "source": "pack_review",
                    "item": f"brief:{brief_id}" if brief_id else f"pack:{r['item_id']}", "text": r["note"], "author": r["author"],
                    "on": r["created_at"].date(), "decision_id": r["decision_id"]})
    for r in conn.execute("""SELECT run_id,run_scope,input_refs,triggered_by,created_at FROM pipeline_runs
            WHERE created_at::date BETWEEN %s AND %s AND (run_scope='card_refresh' OR input_refs ? 'revision_of')
            ORDER BY created_at,run_id""", (since, until)).fetchall():
        refs = r["input_refs"] or {}
        if r["run_scope"] == "card_refresh" and (refs.get("feedback") or "").strip():
            out.append({"id": f"refresh:{r['run_id']}", "source": "card_refresh", "item": f"angle:{refs.get('angle_id')}",
                        "text": refs["feedback"], "author": refs.get("author") or r["triggered_by"], "on": r["created_at"].date()})
        elif refs.get("revision_of") and (refs.get("instructions") or "").strip():
            out.append({"id": f"revise:{r['run_id']}", "source": "brief_revise", "item": f"brief:{refs['revision_of']}",
                        "text": refs["instructions"], "author": refs.get("queued_by") or r["triggered_by"], "on": r["created_at"].date()})
    roots: dict[str, str] = {}
    for r in out:
        r["lineage"] = roots.get(r["item"]) or roots.setdefault(r["item"], lineage(conn, r["item"]))
    return out


LINEAGE = {"angle": ("content_angles", "angle_id"), "brief": ("content_briefs", "brief_id")}


def lineage(conn, item: str) -> str:
    """The card or brief a version belongs to: the first version its versions supersede. A refreshed card is a new version
    with its own id, and two notes on one card are one correction given, not two (N1 shakedown)."""
    kind, _, ident = item.partition(":")
    if kind not in LINEAGE:
        return item
    table, key = LINEAGE[kind]
    row = conn.execute(f"""WITH RECURSIVE up AS (SELECT {key} AS id,supersedes_id,0 AS depth FROM {table} WHERE {key}=%s
        UNION ALL SELECT t.{key},t.supersedes_id,up.depth+1 FROM {table} t JOIN up ON t.{key}=up.supersedes_id WHERE up.depth<100)
        SELECT id FROM up ORDER BY depth DESC LIMIT 1""", (ident,)).fetchone()
    return f"{kind}:{row['id']}" if row else item


def cited(conn) -> set[str]:
    """Feedback a learned rule item (of any status) already cites, by record id, and the decisions any learned rule cites."""
    ids = set()
    for r in conn.execute("""SELECT source_detail FROM brand_kit_items WHERE kind='rule'
            AND source_kind IN ('gate_decision','brief_edit')""").fetchall():
        detail = r["source_detail"] or {}
        ids.update(detail.get("feedback") or [])
        ids.update(f"decision:{d}" for d in detail.get("decisions") or [])
    return ids


def independent(records: list[dict]) -> bool:
    """Given twice: on two different cards or briefs (not two versions of one), or on two different days."""
    return len({r.get("lineage") or r["item"] for r in records}) >= 2 or len({r["on"] for r in records}) >= 2


def run(conn, *, since: date, until: date, support: date, actor: str = "context_mining") -> dict:
    """Rule candidates from repeated feedback; returns how many were made and what each cites."""
    from .mining import _add, _ref, clusters
    taken = cited(conn)
    records = [r for r in feedback(conn, support, until) if r["id"] not in taken]
    groups: dict[str, list[dict]] = {}
    loose = []
    for r in records:
        kind = kind_of(r["text"])
        (groups.setdefault(kind, []).append(r) if kind else loose.append(r))
    proposals = [(kind, group) for kind, group in groups.items()]
    proposals += [(None, group) for group in clusters(loose, lambda r: r["text"], lambda r: r["item"])]
    made, proposed = 0, []
    spec = {kind: (statement, category, scope) for kind, _, statement, category, scope in _PATTERNS}
    for kind, group in proposals:
        if not independent(group) or not any(r["on"] >= since for r in group):
            continue
        ids = sorted(r["id"] for r in group)
        if kind:
            statement, category, scope = spec[kind]
        else:
            lead = max(group, key=lambda r: len(r["text"]))
            statement, category, scope = lead["text"][:8000], "voice", "all"
        detail = {"kind": kind or "unclassified", "feedback": ids,
                  "decisions": sorted(r["decision_id"] for r in group if r.get("decision_id")),
                  "sources": sorted({r["source"] for r in group}), "items": sorted({r["item"] for r in group}),
                  "dates": sorted({r["on"].isoformat() for r in group}), "authors": sorted({r["author"] or "unknown" for r in group}),
                  "given": [{"id": r["id"], "on": r["on"].isoformat(), "author": r["author"], "text": r["text"][:600]} for r in group]}
        made += _add(conn, "rule", f"rule:repeat.{kind or 'unclassified'}.{_ref(ids)[7:19]}",
                     {"statement": statement, "level": "flag", "scope": scope, "category": category,
                      "origin": f"{SOURCE}: a correction of the same kind given {len(group)} times ({', '.join(detail['dates'])})"},
                     source_kind="gate_decision", ref=_ref("repeat", kind, ids), detail=detail,
                     author=", ".join(detail["authors"])[:200], actor=actor, statement_date=max(r["on"] for r in group))
        proposed.append({"kind": kind or "unclassified", "feedback": ids})
    return {"rules": made, "proposed": proposed, "feedback_read": len(records)}
