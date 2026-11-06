"""Removal on request (plan 6.B12; architecture section 12): one client's material removed, and everything built on it marked,
never deleted.

`storage_cli clients remove --client-id <id> --actor <email>` does it in one transaction:

- **deleted:** the client's documents (`transcripts` whose `client_id` is the client) and every copy of one (the same call,
  linked by `canonical_document_id` either way, 1.B10); their chunks; their scenes (`key_moments` from those documents, naming
  the client on another call, or quoting a removed document) with their topic links and their links to cards; the founder
  notes about those calls (L.B13);
- **detached:** a finished job keeps its record without the document (`pipeline_jobs.transcript_id`); the intake keeps the
  call's revision as deleted, its source with the title scrubbed, so the collector never brings the call back (it skips a
  revision it has seen);
- **marked, never deleted:** every card (`content_angles`) that cited a removed scene or document (`angle_moments`, or an id
  in its body: the ledger, the evidence), every brief that cited one (`selected_evidence`, its body) or was built on a marked
  card, every pack built on a marked brief (`source_brief_id`, or a v1 pack's assets), and every later version of each. The
  mark is the removal's own `decisions` row (item_kind `client`, action `remove_on_request`), which lists them: no column is
  added, and no gate decision is written on the items, so nothing that reads gate decisions (the week's dispositions, the
  success measures, the learning loop) counts it. `marks` reads it and follows a version, a brief's card and a pack's brief
  back, so a version made after the removal carries the mark too;
- **the account:** kept with consent `no_use`, so nothing new from the client is used (the default); with `--delete-account`
  the client's people rows lose their link to it and the client row is deleted.

Where a person sees the mark ("Built on material removed at a client's request on <date>"): a card is not for public use and
cannot be developed (`public_use`, gate_one.decide); a brief has the removed-material blocker, so it cannot be approved or
consumed (gate_two); a pack has a blocking finding, so it cannot be marked ready (packs/checks.py); the review document says
it on the card and the brief. Each read also carries `removed_material`.

The dry run (`--dry-run`, and what the command prints first) shows what would happen, with the client's name and the
documents' titles for the operator to recognise; the real run needs an administrator and `--confirm` with the client id
repeated, so a typo cannot remove the wrong client. A document with a queued, running or waiting job refuses the removal until
the job is done. The decision records the counts and every id, never a name or any text. The original uploads stay in the
artifact store, which has no delete: the record and the answer list their keys for the operator to remove there.
"""
from __future__ import annotations

from datetime import datetime

from psycopg import sql
from psycopg.types.json import Jsonb

from .repository import identifier, insert

ACTION = "remove_on_request"
KINDS = ("angle", "brief", "pack")
NOTE = "Built on material removed at a client's request"
ACTIVE_JOBS = ("queued", "running", "waiting")
REMOVED_TITLE = "Removed on request"


def mark_note(at: datetime) -> str:
    return f"{NOTE} on {at:%d %B %Y}. Do not use it; develop a new card from other calls."


# ---- what a client's removal covers ---------------------------------------------------------------------------------------

def _column(conn, query, params) -> list[str]:
    """The distinct non-null values of a one-column query, sorted."""
    return sorted({v for r in conn.execute(query, params) for v in r.values() if v is not None})


def documents(conn, client_id: str) -> tuple[list[str], list[str]]:
    """The client's documents, and every copy linked to one of them in either direction (the same call)."""
    own = _column(conn, "SELECT transcript_id FROM transcripts WHERE client_id=%s", (client_id,))
    group = set(own)
    while group:
        more = set(_column(conn, """SELECT transcript_id FROM transcripts WHERE canonical_document_id = ANY(%(g)s)
            UNION SELECT canonical_document_id FROM transcripts WHERE transcript_id = ANY(%(g)s)""", {"g": list(group)})) - group
        if not more:
            break
        group |= more
    return own, sorted(group - set(own))


def _later(conn, table: str, key: str, ids: list[str]) -> list[str]:
    """These rows and every later version of them (rows whose supersedes chain reaches one)."""
    if not ids:
        return []
    return _column(conn, sql.SQL("""WITH RECURSIVE down(id) AS (SELECT unnest(%s::text[])
        UNION SELECT t.{key} FROM {table} t JOIN down d ON t.supersedes_id=d.id) SELECT id FROM down""").format(
        key=sql.Identifier(key), table=sql.Identifier(table)), (ids,))


def _citing(table: str, key: str, columns: tuple[str, ...]) -> sql.Composed:
    """Rows of `table` whose stored JSON names one of the needles (a removed id, in quotes)."""
    found = sql.SQL(" OR ").join(sql.SQL("strpos(t.{}::text, n)>0").format(sql.Identifier(c)) for c in columns)
    return sql.SQL("SELECT t.{key} FROM {table} t WHERE EXISTS (SELECT 1 FROM unnest(%(needles)s::text[]) AS n WHERE {found})").format(
        key=sql.Identifier(key), table=sql.Identifier(table), found=found)


def plan(conn, client_id: str, *, delete_account: bool = False) -> dict:
    """What removing this client would do: every row it deletes, detaches or marks, by id. Reads only."""
    client = conn.execute("SELECT client_id,name,consent,status FROM clients WHERE client_id=%s", (client_id,)).fetchone()
    if not client:
        raise LookupError(f"Client {client_id} not found")
    own, copies = documents(conn, client_id)
    docs = own + copies
    moments = _column(conn, """SELECT moment_id FROM key_moments WHERE document_id = ANY(%(docs)s) OR client_id=%(client)s
        OR evidence_refs @> ANY(%(refs)s::jsonb[])""",
                      {"docs": docs, "client": client_id, "refs": [Jsonb([{"transcript_id": d}]) for d in docs]})
    # A removed id in quotes, as it appears in stored JSON (a card's ledger, a brief's evidence, a pack's provenance).
    needles = {"needles": [f'"{i}"' for i in docs + moments]}
    angles = _later(conn, "content_angles", "angle_id", sorted(
        set(_column(conn, "SELECT angle_id FROM angle_moments WHERE moment_id = ANY(%s)", (moments,)))
        | set(_column(conn, _citing("content_angles", "angle_id", ("content_body",)), needles))))
    briefs = _later(conn, "content_briefs", "brief_id", sorted(
        set(_column(conn, "SELECT brief_id FROM content_briefs WHERE angle_id = ANY(%s)", (angles,)))
        | set(_column(conn, _citing("content_briefs", "brief_id", ("selected_evidence", "content_body")), needles))))
    packs = _later(conn, "content_packs", "pack_id", sorted(
        set(_column(conn, """SELECT pack_id FROM content_packs WHERE source_brief_id = ANY(%(b)s)
            UNION SELECT pack_id FROM content_assets WHERE brief_id = ANY(%(b)s)""", {"b": briefs}))
        | set(_column(conn, _citing("content_packs", "pack_id", ("content_body",)), needles))))
    cited = {r["angle_id"]: r["moments"] for r in conn.execute("""SELECT angle_id,array_agg(moment_id ORDER BY moment_id) AS moments
        FROM angle_moments WHERE moment_id = ANY(%s) GROUP BY angle_id ORDER BY angle_id""", (moments,))}
    titles = {r["transcript_id"]: r for r in conn.execute(
        "SELECT transcript_id,title,occurred_at FROM transcripts WHERE transcript_id = ANY(%s)", (docs,))}
    jobs = conn.execute("SELECT job_id,stage,status FROM pipeline_jobs WHERE transcript_id = ANY(%s) ORDER BY job_id", (docs,)).fetchall()
    revisions = conn.execute("""SELECT revision_id,source_id,raw_artifact FROM intake_revisions WHERE transcript_id = ANY(%s)
        ORDER BY revision_id""", (docs,)).fetchall()
    # An original upload is stored once per content (documents/intake.py); keep the key of one another document still uses.
    originals = _column(conn, """SELECT t.raw_object_key FROM transcripts t WHERE t.transcript_id = ANY(%(d)s) AND NOT EXISTS
        (SELECT 1 FROM transcripts o WHERE o.raw_object_key=t.raw_object_key AND NOT o.transcript_id = ANY(%(d)s))""", {"d": docs})
    return {
        "client": dict(client), "documents": [_document(titles[d]) for d in own], "copies": [_document(titles[d]) for d in copies],
        "chunks": _column(conn, "SELECT chunk_id FROM transcript_chunks WHERE transcript_id = ANY(%s)", (docs,)),
        "moments": moments,
        "topic_links": [[r["moment_id"], r["topic_id"]] for r in conn.execute(
            "SELECT moment_id,topic_id FROM moment_topics WHERE moment_id = ANY(%s) ORDER BY moment_id,topic_id", (moments,))],
        "founder_notes": _column(conn, "SELECT seed_id FROM seeds WHERE transcript_id = ANY(%s)", (docs,)),
        "jobs": [r["job_id"] for r in jobs], "active_jobs": [dict(r) for r in jobs if r["status"] in ACTIVE_JOBS],
        "intake_revisions": [r["revision_id"] for r in revisions],
        "intake_sources": sorted({r["source_id"] for r in revisions}),
        "originals_kept_in_store": sorted(set(originals) | {r["raw_artifact"] for r in revisions if r["raw_artifact"]}),
        "marked": {"angles": angles, "briefs": briefs, "packs": packs}, "cited": cited,
        "people": _column(conn, "SELECT person_id FROM people WHERE client_id=%s", (client_id,)),
        "account": "deleted; its people unlinked" if delete_account else "kept with consent no_use",
    }


def _document(row: dict) -> dict:
    return {"transcript_id": row["transcript_id"], "title": row["title"],
            "occurred_at": row["occurred_at"].isoformat() if row["occurred_at"] else None}


def counts(found: dict) -> dict:
    return {k: len(found[k]) for k in ("documents", "copies", "chunks", "moments", "topic_links", "founder_notes", "jobs",
                                       "intake_revisions", "people")} | {k: len(v) for k, v in found["marked"].items()}


# ---- the removal --------------------------------------------------------------------------------------------------------

def remove(conn, client_id: str, *, actor: str, delete_account: bool = False) -> dict:
    """Remove the client's material and mark what was built on it, in the caller's transaction; returns the record."""
    if not conn.execute("SELECT 1 FROM clients WHERE client_id=%s FOR UPDATE", (client_id,)).fetchone():
        raise LookupError(f"Client {client_id} not found")
    found = plan(conn, client_id, delete_account=delete_account)
    docs = [d["transcript_id"] for d in found["documents"] + found["copies"]]
    conn.execute("SELECT transcript_id FROM transcripts WHERE transcript_id = ANY(%s) FOR UPDATE", (docs,))
    if found["active_jobs"]:
        raise ValueError("A job is still working on this client's documents; wait for it to finish, then remove: "
                         + ", ".join(f"{j['job_id']} ({j['stage']}, {j['status']})" for j in found["active_jobs"]))
    moments = found["moments"]
    conn.execute("DELETE FROM angle_moments WHERE moment_id = ANY(%s)", (moments,))
    conn.execute("DELETE FROM moment_topics WHERE moment_id = ANY(%s)", (moments,))
    conn.execute("DELETE FROM key_moments WHERE moment_id = ANY(%s)", (moments,))
    conn.execute("DELETE FROM transcript_chunks WHERE transcript_id = ANY(%s)", (docs,))
    conn.execute("DELETE FROM seeds WHERE transcript_id = ANY(%s)", (docs,))
    conn.execute("UPDATE pipeline_jobs SET transcript_id=NULL,updated_at=now() WHERE transcript_id = ANY(%s)", (docs,))
    conn.execute("UPDATE intake_revisions SET transcript_id=NULL,deleted=true WHERE transcript_id = ANY(%s)", (docs,))
    conn.execute("""UPDATE intake_sources SET title=%s,source_url=NULL,metadata='{}'::jsonb,status='deleted'
        WHERE source_id = ANY(%s)""", (REMOVED_TITLE, found["intake_sources"]))
    conn.execute("UPDATE transcripts SET canonical_document_id=NULL WHERE transcript_id = ANY(%s)", (docs,))
    conn.execute("DELETE FROM transcripts WHERE transcript_id = ANY(%s)", (docs,))
    consent = found["client"]["consent"]
    if delete_account:
        conn.execute("UPDATE people SET client_id=NULL,updated_at=now() WHERE client_id=%s", (client_id,))
        conn.execute("DELETE FROM clients WHERE client_id=%s", (client_id,))
    else:
        conn.execute("UPDATE clients SET consent='no_use',updated_at=now() WHERE client_id=%s", (client_id,))
    decision_id = identifier("decision")
    tally = counts(found)
    # Ids and counts only: the record outlives the material, so it carries no name, title or text.
    insert(conn, "decisions", {
        "decision_id": decision_id, "item_kind": "client", "item_id": client_id, "action": ACTION, "actor": actor, "author": actor,
        "note": "Removed on request (counts): " + ", ".join(f"{k.replace('_', ' ')} {n}" for k, n in tally.items() if n) + ".",
        "details": {"counts": tally, "documents": [d["transcript_id"] for d in found["documents"]],
                    "copies": [d["transcript_id"] for d in found["copies"]], "chunks": found["chunks"], "moments": moments,
                    "topic_links": found["topic_links"], "founder_notes": found["founder_notes"], "jobs_detached": found["jobs"],
                    "intake_revisions": found["intake_revisions"], "intake_sources": found["intake_sources"],
                    "originals_kept_in_store": found["originals_kept_in_store"], "marked": found["marked"], "cited": found["cited"],
                    "people_unlinked": found["people"] if delete_account else [],
                    "account": "deleted" if delete_account else "kept", "consent_before": consent,
                    "consent_after": None if delete_account else "no_use"}})
    return {"decision_id": decision_id, "client_id": client_id, "counts": tally, "marked": found["marked"],
            "account": found["account"], "originals_kept_in_store": found["originals_kept_in_store"]}


def run(repo, client_id: str, actor: str, *, confirm: str | None = None, dry_run: bool = False,
        delete_account: bool = False) -> dict:
    """`storage_cli clients remove`: the plan first; the removal only with the client id repeated, by an administrator."""
    from .gates.roles import actor_for
    with repo.connection() as conn:
        would = plan(conn, client_id, delete_account=delete_account)
    answer = {"dry_run": True, "client_id": client_id, "would_remove": would, "counts": counts(would)}
    if dry_run or confirm is None:
        return {**answer, "next": f"Nothing was removed. To remove it, run again with --confirm {client_id}"}
    if confirm != client_id:
        raise ValueError("--confirm must repeat --client-id exactly; nothing was removed")
    who = actor_for(repo, actor)
    if not who.access.can("manage_intake"):
        raise PermissionError("Removing a client's material needs an administrator")
    with repo.connection() as conn:
        done = remove(conn, client_id, actor=str(who), delete_account=delete_account)
    return {**answer, "dry_run": False, "removed": done}


# ---- reading the mark ----------------------------------------------------------------------------------------------------

# One step back from an item to what it was built on: an earlier version, a brief's card, a pack's brief (v2 by
# source_brief_id, v1 through its assets). One reference to `up`, so PostgreSQL accepts it in a recursive query.
_LINEAGE = """WITH RECURSIVE up(item, kind, id, depth) AS (
    SELECT i, %(kind)s::text, i, 0 FROM unnest(%(ids)s::text[]) AS i
    UNION ALL
    SELECT up.item, n.kind, n.id, up.depth + 1 FROM up CROSS JOIN LATERAL (
        SELECT 'angle'::text, a.supersedes_id FROM content_angles a WHERE up.kind='angle' AND a.angle_id=up.id AND a.supersedes_id IS NOT NULL
        UNION ALL SELECT 'brief', b.supersedes_id FROM content_briefs b WHERE up.kind='brief' AND b.brief_id=up.id AND b.supersedes_id IS NOT NULL
        UNION ALL SELECT 'angle', b.angle_id FROM content_briefs b WHERE up.kind='brief' AND b.brief_id=up.id
        UNION ALL SELECT 'pack', p.supersedes_id FROM content_packs p WHERE up.kind='pack' AND p.pack_id=up.id AND p.supersedes_id IS NOT NULL
        UNION ALL SELECT 'brief', p.source_brief_id FROM content_packs p WHERE up.kind='pack' AND p.pack_id=up.id AND p.source_brief_id IS NOT NULL
        UNION ALL SELECT DISTINCT 'brief', s.brief_id FROM content_assets s WHERE up.kind='pack' AND s.pack_id=up.id
    ) AS n(kind, id) WHERE up.depth < 50)
SELECT item, kind, id FROM up ORDER BY item, depth"""


def marks(conn, kind: str, ids) -> dict[str, dict]:
    """The removal mark each item carries, directly or through what it was built on: {item_id: {decision_id, removed_at,
    note}}. Empty, after one query, when nothing was ever removed; empty on a database without the decisions table."""
    if kind not in KINDS:
        raise ValueError(f"Unknown item kind {kind!r}")
    ids = [i for i in dict.fromkeys(ids or []) if i]
    if not ids or not conn.execute("SELECT to_regclass('public.decisions') AS t").fetchone()["t"]:
        return {}
    records = conn.execute("""SELECT decision_id,created_at,details FROM decisions WHERE item_kind='client' AND action=%s
        ORDER BY created_at,decision_id""", (ACTION,)).fetchall()
    marked: dict[tuple[str, str], dict] = {}
    for r in records:
        mark = {"decision_id": r["decision_id"], "removed_at": r["created_at"].isoformat(), "note": mark_note(r["created_at"])}
        for k in KINDS:
            for i in ((r["details"] or {}).get("marked") or {}).get(k + "s") or []:
                marked.setdefault((k, i), mark)
    if not marked:
        return {}
    out: dict[str, dict] = {}
    for r in conn.execute(_LINEAGE, {"kind": kind, "ids": ids}):
        if r["item"] not in out and (r["kind"], r["id"]) in marked:
            out[r["item"]] = marked[(r["kind"], r["id"])]
    return out


def mark_of(conn, kind: str, item_id: str | None) -> dict | None:
    return marks(conn, kind, [item_id]).get(item_id) if item_id else None
