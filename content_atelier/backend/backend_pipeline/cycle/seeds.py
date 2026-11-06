"""Founder seeds (E.B19; 3.B8 pulled forward). Whitney's best work starts from her own words.

Whitney or the team adds a thought, a draft or a published asset, with an optional target offer, as a seed for
a cycle. Seeds are frozen into the run at submit, so a retry or replay sends the same prompt. Strategist profile
v5 pairs each seed with the scenes that support it, or says it has no call evidence (E.B21). After a successful
generation the seeds it used are marked used, except those marked always true, which stay open for every cycle.

A founder note (L.B13, D29) is a seed of its own kind: Whitney's one "what stood out to me" line about one call, linked to
that call. It copies her own starting point, where her note has already chosen the moment. It reaches only a strategist that
reads notes (profile v8), which pairs it with that call's scenes or with none; the cycle's selection shows each note paired
or unanswered, and the week's review document carries the line (briefs/review_document.py).
"""
from __future__ import annotations

from urllib.parse import urlsplit

from .. import gate_one
from ..repository import identifier, insert

KINDS = ("thought", "draft", "asset", "founder_note")
MAX_TEXT = 8000
MAX_NOTE = 600  # one line, as she would say it


def _table(conn):
    return bool(conn.execute("SELECT to_regclass('public.seeds') AS t").fetchone()["t"])


def add(repo, actor, *, kind, text, target_offer=None, source_url=None, author=None, week_id=None, always_true=False,
        transcript_id=None):
    gate_one.require(repo, actor, "edit")
    if kind not in KINDS:
        raise ValueError("A seed is a thought, a draft, an asset or a founder note")
    text = (text or "").strip()
    if not text or len(text) > MAX_TEXT:
        raise ValueError(f"A seed needs its text (at most {MAX_TEXT} characters)")
    if kind == "founder_note":
        if not transcript_id:
            raise ValueError("A founder note names the call it is about")
        if len(text) > MAX_NOTE:
            raise ValueError(f"A founder note is one line (at most {MAX_NOTE} characters)")
        if always_true:
            raise ValueError("A founder note is about one call, so it is never kept for every cycle")
    elif transcript_id:
        raise ValueError("Only a founder note is linked to a call")
    if source_url and urlsplit(source_url).scheme not in {"http", "https"}:
        raise ValueError("A seed's link must be an http or https address")
    if kind == "asset" and not source_url:
        raise ValueError("An asset seed needs the link to the published asset")
    author = (author or "").strip() or actor
    with repo.connection() as conn:
        if week_id and not conn.execute("SELECT 1 FROM weeks WHERE week_id=%s", (week_id,)).fetchone():
            raise ValueError("Week not found")
        if transcript_id and not conn.execute("SELECT 1 FROM transcripts WHERE transcript_id=%s AND included",
                                              (transcript_id,)).fetchone():
            raise ValueError("The call is not an included document")
        seed_id = identifier("seed")
        # created_at is the order seeds were added (the list, and F1, F2 ... in the cycle), so it must never tie or run
        # backwards: a database clock can step back (a VM resync) and now() is the transaction's start. Adds are
        # serialised, and each is stamped strictly after every earlier seed.
        conn.execute("SELECT pg_advisory_xact_lock(hashtext('seeds.created_at'))")
        insert(conn, "seeds", {"seed_id": seed_id, "kind": kind, "text": text, "target_offer": (target_offer or "").strip() or None,
                               "source_url": source_url or None, "always_true": bool(always_true), "author": author[:200],
                               "created_by": actor, "week_id": week_id,
                               **({"transcript_id": transcript_id} if transcript_id else {})})
        conn.execute("""UPDATE seeds SET created_at=greatest(clock_timestamp(),
            (SELECT max(created_at) FROM seeds WHERE seed_id<>%s) + interval '1 microsecond') WHERE seed_id=%s""",
                     (seed_id, seed_id))
        return conn.execute("SELECT * FROM seeds WHERE seed_id=%s", (seed_id,)).fetchone()


def listing(repo, status=None):
    with repo.connection() as conn:
        return conn.execute("""SELECT * FROM seeds WHERE (%s::text IS NULL OR status=%s)
            ORDER BY created_at DESC,seed_id""", (status, status)).fetchall()


def withdraw(repo, seed_id, actor):
    gate_one.require(repo, actor, "edit")
    with repo.connection() as conn:
        row = conn.execute("UPDATE seeds SET status='withdrawn' WHERE seed_id=%s AND status='open' RETURNING seed_id,status",
                           (seed_id,)).fetchone()
        if not row:
            raise ValueError("No open seed with that ID")
        return row


def freeze(conn, week_id, *, founder_notes: bool = False):
    """The open seeds for this cycle, in the order they were added; empty before migration 005. Founder notes only when the
    strategist reads them (`founder_notes`), each with its call named; a strategist that does not leaves them open."""
    if not _table(conn):
        return []
    rows = conn.execute("""SELECT seed_id,kind,text,target_offer,source_url,author,always_true FROM seeds
        WHERE status='open' AND (week_id IS NULL OR week_id=%s) ORDER BY created_at,seed_id""", (week_id,)).fetchall()
    frozen = [dict(r) for r in rows if founder_notes or r["kind"] != "founder_note"]
    notes = [s for s in frozen if s["kind"] == "founder_note"]
    if notes:
        calls = {r["seed_id"]: r for r in conn.execute("""SELECT s.seed_id,s.transcript_id,t.title,t.occurred_at,t.source_metadata
            FROM seeds s JOIN transcripts t USING (transcript_id) WHERE s.seed_id=ANY(%s)""", ([s["seed_id"] for s in notes],))}
        for seed in notes:
            call = calls[seed["seed_id"]]
            seed["transcript_id"] = call["transcript_id"]
            seed["call"] = call_label(call)
    return frozen


def call_label(call: dict) -> str:
    """A founder note's call named exactly as the strategist's scenes name their recording (angle_profiles._recording: the
    packet's file label or name, and its date when the packet has one), so the strategist can find that call's scenes (N8
    shakedown: a note named by the document's title read as another call)."""
    # The packet header storage_sources.reconstruct builds: the document's own packet metadata, else its title and date.
    meta = (call.get("source_metadata") or {}).get("packet_metadata") or {
        "filename_label": call["title"], "date": call["occurred_at"].date().isoformat() if call.get("occurred_at") else None}
    label = meta.get("filename_label") or meta.get("name") or call["title"]
    return f"\"{label}, {meta['date']}\"" if meta.get("date") else f"\"{label}\""


def prompt_seeds(frozen):
    """What the strategist sees for each seed (angle_profiles._seed_lines): kind, author, offer, text and link."""
    return [{"kind": s["kind"], "author": s["author"], "target_offer": s.get("target_offer"),
             "text": s["text"] + (f" (link: {s['source_url']})" if s.get("source_url") else ""),
             **({"call": s.get("call")} if s["kind"] == "founder_note" else {})} for s in frozen]


def resolve_pairings(selection, frozen):
    """Seed references F1, F2 ... in the strategist's pairings become seed IDs, in freeze order."""
    by_ref = {f"F{i}": s["seed_id"] for i, s in enumerate(frozen, 1)}
    texts = {s["seed_id"]: s["text"][:300] for s in frozen}
    notes = {s["seed_id"]: s for s in frozen if s.get("kind") == "founder_note"}
    pairings = selection.setdefault("seed_pairings", [])
    for pairing in pairings:
        pairing["seed_id"] = by_ref.get(pairing.get("seed_ref"))
        # The seed's own words, so the reviewer sees the seed rather than its reference (R50).
        pairing["seed_text"] = texts.get(pairing["seed_id"])
        if pairing["seed_id"] in notes:
            pairing.update(_note_fields(notes[pairing["seed_id"]]))
    # A seed the strategist did not answer is shown as such, with no call evidence, and stays open (E.B19): it is
    # never consumed silently.
    answered = {p["seed_id"] for p in pairings}
    pairings += [{"seed_ref": ref, "seed_id": seed_id, "seed_text": texts.get(seed_id), "moment_ids": [], "unanswered": True,
                  "note": "The strategist did not answer this seed; it stays open for the next cycle.",
                  **(_note_fields(notes[seed_id]) if seed_id in notes else {})}
                 for ref, seed_id in by_ref.items() if seed_id not in answered]
    return selection


def _note_fields(seed: dict) -> dict:
    """What a founder note's pairing carries for the reviewer: its kind, author and call."""
    return {"seed_kind": "founder_note", "seed_author": seed.get("author"), "transcript_id": seed.get("transcript_id"),
            "call": seed.get("call")}


def mark_used(conn, frozen, run_id, selection=None):
    """Seeds the cycle answered (paired with scenes or flagged "no call evidence") are used; an always-true seed
    stays for every cycle, and an unanswered one for the next."""
    answered = None if selection is None else {p["seed_id"] for p in selection.get("seed_pairings", []) if not p.get("unanswered")}
    ids = [s["seed_id"] for s in frozen if not s.get("always_true") and (answered is None or s["seed_id"] in answered)]
    if ids:
        conn.execute("UPDATE seeds SET status='used',used_in_run_id=%s WHERE seed_id=ANY(%s) AND status='open'", (run_id, ids))
