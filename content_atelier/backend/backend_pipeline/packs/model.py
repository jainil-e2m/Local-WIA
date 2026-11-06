"""Pack versions in the database (content pack contract v2; the content-packs plan, sections 4.1 and 5.3).

One `content_packs` row per pack version, its pack-level fields in `content_body` (contracts_v2.PackBody), and one
`content_assets` row per piece (`slot_key` is the piece key, its envelope in `content_body`, contracts_v2.Piece).

- **Versions.** `content_assets` allows one row per piece per pack (its unique index), so every change that alters copy (a
  person's edit, a revert, an attestation that changes text, "Finish again") writes a new pack row whose `supersedes_id` is
  the previous one, with the five piece rows copied and the changed ones replaced (`write_version`). The current pack is
  the one nothing supersedes; `versions` walks the chain, as `gate_two.versions` does for briefs.
- **The manifest** hashes the pack body with the pieces' keys, order and hashes (`manifest`). Published marks, the marks on
  before-publishing notes and client quotes, and the week's dates are outside it, so marking a piece published or a note
  done never changes a pack's readiness.
- **States** are derived on read (`state_of`), never stored: finishing or waiting from the pack run's jobs; in review
  when finished and not ready; ready to publish when a person marked this exact manifest ready.
- **Decisions** on a pack are audited with `item_kind = pack` (R45, migration 009; `record_decision`).

Every function takes the caller's connection and transaction; nothing here commits.
"""
from __future__ import annotations

from datetime import UTC, datetime

from psycopg.types.json import Jsonb

from ..repository import identifier, insert
from ..store import canonical_hash
from . import contracts_v2 as c2

ACTIVE_JOB = ("queued", "running", "waiting")


def is_v2(pack: dict | None) -> bool:
    return bool(pack) and pack.get("contract_version") == c2.VERSION


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def asset_id(pack_id: str, key: str) -> str:
    return "asset_" + canonical_hash([pack_id, key])[:24]


def body_hash(body: dict) -> str:
    return canonical_hash(body)


def manifest_body(body: dict | None) -> dict | None:
    """The pack body as the manifest sees it: without the marks on its notes (a before-publishing note marked done, a client
    quote cleared). Those are notes for whoever posts, like published marks, so recording one never changes what a person
    marked ready, and they are recorded on the version in place."""
    if body is None:
        return None
    return {**body, "before_publishing": [{k: v for k, v in n.items() if k != "done"} for n in body.get("before_publishing") or []],
            "client_quotes": [{k: v for k, v in q.items() if k != "cleared"} for q in body.get("client_quotes") or []]}


def manifest(pack: dict, rows) -> str:
    """The pack version's manifest: the pack body (without its notes' marks) and each piece's key, order and hash (section
    5.3)."""
    body = manifest_body(pack.get("content_body"))
    return canonical_hash({"version": c2.VERSION, "brief_id": pack["source_brief_id"], "brief_hash": pack["source_brief_hash"],
                           "body": canonical_hash(body) if body is not None else None,
                           "pieces": [{"key": r["slot_key"], "ordinal": r["ordinal"], "hash": r["content_hash"]}
                                      for r in sorted(rows, key=lambda r: r["ordinal"])]})


def pieces(conn, pack_id: str, *, lock: bool = False) -> dict[str, dict]:
    """The pack version's piece rows by key."""
    rows = conn.execute("SELECT * FROM content_assets WHERE pack_id=%s ORDER BY ordinal,asset_id" + (" FOR UPDATE" if lock else ""),
                        (pack_id,)).fetchall()
    return {r["slot_key"]: r for r in rows}


def get(conn, pack_id: str, *, lock: bool = False) -> dict:
    """A pack row; with `lock`, the governing brief, then the pack, then its pieces are locked in that order (the order
    every pack mutation takes, as packs/service.locked does)."""
    head = conn.execute("SELECT source_brief_id FROM content_packs WHERE pack_id=%s", (pack_id,)).fetchone()
    if not head:
        raise LookupError("Pack not found")
    if lock:
        conn.execute("SELECT brief_id FROM content_briefs WHERE brief_id=%s FOR UPDATE", (head["source_brief_id"],))
    return conn.execute("SELECT * FROM content_packs WHERE pack_id=%s" + (" FOR UPDATE" if lock else ""), (pack_id,)).fetchone()


def superseded(conn, pack_id: str) -> bool:
    return bool(conn.execute("SELECT 1 FROM content_packs WHERE supersedes_id=%s", (pack_id,)).fetchone())


def head_of(conn, pack_id: str) -> str:
    """The newest version in a pack's lineage (the one nothing supersedes)."""
    seen = set()
    while True:
        nxt = conn.execute("SELECT pack_id FROM content_packs WHERE supersedes_id=%s ORDER BY created_at DESC LIMIT 1",
                           (pack_id,)).fetchone()
        if not nxt or nxt["pack_id"] in seen:
            return pack_id
        seen.add(pack_id)
        pack_id = nxt["pack_id"]


def current_for_brief(conn, brief_id: str) -> dict | None:
    """The brief's current v2 pack: the newest version nothing supersedes."""
    return conn.execute("""SELECT * FROM content_packs p WHERE p.source_brief_id=%s AND p.contract_version=%s
        AND NOT EXISTS (SELECT 1 FROM content_packs n WHERE n.supersedes_id=p.pack_id)
        ORDER BY p.created_at DESC, p.pack_id LIMIT 1""", (brief_id, c2.VERSION)).fetchone()


def run_jobs(conn, run_id: str | None) -> list[dict]:
    if not run_id:
        return []
    # In stage order: a run's six jobs are inserted in one transaction and share one timestamp.
    return conn.execute("""SELECT job_id,stage,status,current_message,error_summary,attempt_count,progress_details,
        heartbeat_at,completed_units,total_units FROM pipeline_jobs WHERE run_id=%s
        ORDER BY array_position(%s::text[], stage), created_at, job_id""", (run_id, list(c2.ALL_STAGES))).fetchall()


def run_active(conn, run_id: str | None) -> bool:
    return any(j["status"] in ACTIVE_JOB for j in run_jobs(conn, run_id))


def state_of(conn, pack: dict) -> tuple[str, str | None]:
    """(state, reason in words) for a v2 pack version (section 4.1)."""
    if superseded(conn, pack["pack_id"]):
        return "superseded", "A newer version of this pack exists"
    if pack.get("content_body") is None:
        jobs = run_jobs(conn, pack.get("production_run_id"))
        waiting = next((j for j in jobs if j["status"] == "waiting"), None)
        if waiting:
            details = waiting.get("progress_details") or {}
            return "waiting", details.get("budget_reason") or waiting.get("current_message") or "Waiting to continue"
        failed = next((j for j in jobs if j["status"] == "failed"), None)
        if failed:
            return "waiting", ("A step failed and can be tried again: "
                               + (failed.get("error_summary") or failed.get("current_message") or failed["stage"]))[:600]
        current = next((j for j in jobs if j["status"] in ("running", "queued")), None)
        if current is None:
            # Every job ended (completed or cancelled) without a finished version: nothing will move on by itself.
            return "waiting", "The pack's run ended without a finished version; create the pack again from the brief"
        return "finishing", current.get("current_message") or "Finishing the pack"
    if pack["approval_status"] == "approved" and pack.get("approved_hash") and pack["approved_hash"] == pack.get("manifest_hash"):
        return "ready_to_publish", None
    return "in_review", None


def write_version(repo, conn, *, parent: dict | None, pack_id: str | None, run_id: str, brief: dict, body: dict,
                  piece_bodies: dict[str, dict], actor: str, validation: dict | None = None,
                  reuse_row: bool = False) -> dict:
    """Write a pack version: the pack row (with its body, hash and manifest, pending) and its five piece rows.

    - A new version (`reuse_row` false) inserts a pack row superseding `parent` (when given).
    - The first version of a run (`reuse_row` true) fills the row the run's queue inserted (content_body still null).
    Bodies are validated against the contract first. Returns {pack_id, manifest_hash}."""
    c2.PackBody.model_validate(body)
    for key in c2.PIECE_KEYS:
        if key not in piece_bodies:
            raise ValueError(f"A pack version needs all five pieces; {key} is missing")
        piece = c2.Piece.model_validate(piece_bodies[key])
        if piece.content is not None:
            c2.COPY_MODELS[piece.channel].model_validate(piece.content)
    pack_id = pack_id or identifier("pack")
    digest = body_hash(body)
    if reuse_row:
        row = conn.execute("SELECT * FROM content_packs WHERE pack_id=%s FOR UPDATE", (pack_id,)).fetchone()
        if not row or row.get("content_body") is not None:
            raise ValueError("The pack row is missing or already written")
        conn.execute("UPDATE content_packs SET content_body=%s,content_hash=%s,title=%s,updated_by=%s,updated_at=now() WHERE pack_id=%s",
                     (Jsonb(body), digest, body["title"], actor, pack_id))
    else:
        insert(conn, "content_packs", {
            "pack_id": pack_id, "week_id": brief["week_id"], "supersedes_id": parent["pack_id"] if parent else None,
            "title": body["title"], "source_brief_id": brief["brief_id"], "source_brief_hash": brief["approved_hash"],
            "production_run_id": run_id, "contract_version": c2.VERSION, "content_body": Jsonb(body), "content_hash": digest,
            "updated_by": actor})
    conn.execute("DELETE FROM content_assets WHERE pack_id=%s", (pack_id,))
    for key in c2.PIECE_KEYS:
        piece = piece_bodies[key]
        copy = piece.get("content") or {}
        insert(conn, "content_assets", {
            "asset_id": asset_id(pack_id, key), "pack_id": pack_id, "brief_id": brief["brief_id"],
            "brief_input_hash": brief["approved_hash"], "slot_key": key, "ordinal": c2.ORDINAL[key],
            "asset_type": c2.CHANNEL[key], "reader_contribution": (copy.get("job") or c2.LABELS[key])[:2000],
            "status": "not_written" if piece["origin"] == "not_written" else "generated",
            "content_body": Jsonb(piece), "content_hash": canonical_hash(piece), "updated_by": actor})
    pack = conn.execute("SELECT * FROM content_packs WHERE pack_id=%s", (pack_id,)).fetchone()
    digest_m = manifest(pack, pieces(conn, pack_id).values())
    conn.execute("UPDATE content_packs SET manifest_hash=%s,validation_result=%s,approval_status='pending',approved_hash=NULL,"
                 "approved_by=NULL,approved_at=NULL,updated_at=now() WHERE pack_id=%s",
                 (digest_m, Jsonb(validation) if validation is not None else None, pack_id))
    return {"pack_id": pack_id, "manifest_hash": digest_m}


def versions(conn, pack_id: str) -> list[dict]:
    """Every version of a pack's lineage, oldest first, with why each exists (its change record)."""
    row = conn.execute("SELECT pack_id,supersedes_id FROM content_packs WHERE pack_id=%s", (pack_id,)).fetchone()
    if not row:
        raise LookupError("Pack not found")
    seen = set()
    while row["supersedes_id"]:
        if row["pack_id"] in seen:
            raise ValueError("Pack version cycle")
        seen.add(row["pack_id"])
        row = conn.execute("SELECT pack_id,supersedes_id FROM content_packs WHERE pack_id=%s", (row["supersedes_id"],)).fetchone()
    rows = conn.execute("""WITH RECURSIVE chain AS (
        SELECT pack_id,supersedes_id,manifest_hash,approval_status,created_at,updated_by,content_body,production_run_id,0 AS depth
        FROM content_packs WHERE pack_id=%s
        UNION ALL SELECT p.pack_id,p.supersedes_id,p.manifest_hash,p.approval_status,p.created_at,p.updated_by,p.content_body,
        p.production_run_id,c.depth+1 FROM content_packs p JOIN chain c ON p.supersedes_id=c.pack_id)
        SELECT * FROM chain ORDER BY depth,created_at,pack_id""", (row["pack_id"],)).fetchall()
    out = []
    for r in rows:
        change = (r["content_body"] or {}).get("change") or {}
        out.append({"pack_id": r["pack_id"], "supersedes_id": r["supersedes_id"], "manifest_hash": r["manifest_hash"],
                    "approval_status": r["approval_status"], "created_at": r["created_at"], "run_id": r["production_run_id"],
                    "kind": change.get("kind") or ("finishing" if r["content_body"] is None else "generated"),
                    "by": change.get("by") or r["updated_by"], "delegated": bool(change.get("delegated")),
                    "pieces": change.get("pieces") or [], "paths": change.get("paths") or [], "note": change.get("note")})
    return out


def delegated(settings, actor: str | None) -> bool:
    """Whether an action is recorded under D12's delegation rather than as WIA's own (R55)."""
    from ..gates.decisions import wia_review
    return not wia_review(settings, actor, actor)


def record_decision(conn, pack: dict, *, action: str, actor: str, settings=None, note: str | None = None,
                    details: dict | None = None, disposition: str | None = None) -> str | None:
    """One audited decision on a pack (R45): `item_kind = pack`. Ready to publish records an approval with its label;
    an edit, a revert, a clearance or an attestation records the decision alone."""
    if not conn.execute("SELECT to_regclass('public.decisions') AS t").fetchone()["t"]:
        return None
    payload = {**(details or {}), "manifest_hash": pack.get("manifest_hash"), "brief_id": pack.get("source_brief_id"),
               "delegated": delegated(settings, actor)}
    if disposition:
        from ..gates.decisions import record
        return record(conn, item_kind="pack", item_id=pack["pack_id"], week_id=pack["week_id"], disposition=disposition,
                      action=action, actor=actor, author=actor, note=note, expected_hash=pack.get("manifest_hash"),
                      details=payload, settings=settings)
    decision_id = identifier("decision")
    insert(conn, "decisions", {"decision_id": decision_id, "item_kind": "pack", "item_id": pack["pack_id"],
                               "week_id": pack["week_id"], "action": action, "actor": actor, "author": actor, "note": note,
                               "expected_hash": pack.get("manifest_hash"), "details": payload})
    return decision_id


# ---- the v4 shape, for the brief's checks ------------------------------------------------------------------------------

V4_REEL = ("kind", "job", "register", "cover_text", "on_screen_hook", "spoken_opening", "script", "screens", "beats",
           "personal_lines", "read_time_seconds", "source", "caption", "offer_descriptor")
V4_CAROUSEL = ("job", "register", "title", "slides", "caption", "offer_descriptor")
V4_EMAIL = ("job", "register", "send_header", "subject_options", "preview", "opening", "body", "ending", "offer_descriptor")


def v4_format_plan(piece_bodies: dict[str, dict]) -> dict:
    """The pack's pieces as a v4 `format_plan` (Reels in the order story, stance, b-roll text; written ones only), with the
    pack's extra fields left out, so the brief's checks (first_touch, asset_checks) read the pack unchanged."""
    def pick(copy, names):
        return {n: copy.get(n) for n in names}
    # A Round 2 Reel keeps its production, so the brief's checks read an on-screen text Reel as one (contracts_v4.on_screen).
    reels = [pick(piece_bodies[k]["content"], V4_REEL) | ({"production": piece_bodies[k]["content"]["production"]}
                                                          if piece_bodies[k]["content"].get("production") else {})
             for k in ("reel_1", "reel_2", "reel_3") if piece_bodies.get(k) and piece_bodies[k].get("content")]
    carousel = piece_bodies.get("carousel", {}).get("content")
    email = piece_bodies.get("email", {}).get("content")
    return {"reels": reels, "carousel": pick(carousel, V4_CAROUSEL) if carousel else None,
            "email": pick(email, V4_EMAIL) if email else None, "stories": None}


def v4_body(brief_body: dict, piece_bodies: dict[str, dict]) -> dict:
    """A v4 writer body: the approved brief's strategy sections with the pack's pieces as its format plan."""
    return {**brief_body, "format_plan": v4_format_plan(piece_bodies)}
