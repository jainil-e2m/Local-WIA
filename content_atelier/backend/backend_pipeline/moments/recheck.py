"""`moments recheck` (plan 2.B4): re-derive what depends on the document, the roles and the client, for moments already stored.

A moment's speaker, role, client, evidence kind, consent status and checks are derived (`moments/store.derive_columns`) from
facts that can change after it was stored: a document is normalised again (a speaker is placed, the call is re-typed, the client
is found), or a client's consent changes. `recheck` runs the same derivation again over the stored rows, from the moment's
own immutable record (`moment_body`) and the evidence it cites, and updates only what differs. It is idempotent: running it
twice changes nothing the second time. It never touches the quote, the evidence, the body, the extractor version or the vector.

An unverified record has no evidence, so only its client, date and consent are re-derived. A row with no document (a moment
that predates the ledger and could not be tied to one) is counted and left alone.
"""
from __future__ import annotations

from psycopg.types.json import Jsonb

from . import checks, store

# The keys of `checks` that this derivation owns; every other key (provenance: extraction, imported_from, local_key) is kept.
DERIVED = ("version", "role_plausibility", "numbers", "consent")
COLUMNS = ("speaker_label", "speaker_id", "speaker_role", "client_id", "occurred_at", "moment_type", "evidence_kind", "consent_status",
           "sensitivity", "destination", "evidence_class")


def select_rows(conn, *, ids=None, document_ids=None, client_id=None) -> list[dict]:
    """The stored moments to re-derive: those named, those of the documents named, those of the client named, or all."""
    return conn.execute("""SELECT * FROM key_moments WHERE document_id IS NOT NULL
        AND (%(ids)s::text[] IS NULL OR moment_id=ANY(%(ids)s))
        AND (%(docs)s::text[] IS NULL OR document_id=ANY(%(docs)s))
        AND (%(client)s::text IS NULL OR client_id=%(client)s OR document_id IN (SELECT transcript_id FROM transcripts WHERE client_id=%(client)s))
        ORDER BY document_id, moment_id""", {"ids": ids, "docs": document_ids, "client": client_id}).fetchall()


def derive(row: dict, document: dict, consent: str | None, roster, people: set[str]) -> dict:
    """The columns and checks one stored row should have now."""
    body = row["moment_body"]
    if not row["quote_verified"]:
        assessed = checks.assess_unverified(original_type=body.get("moment_type"), sensitivity=body.get("sensitivity"), client_consent=consent)
        return {"client_id": document.get("client_id"), "occurred_at": document.get("occurred_at"),
                "consent_status": assessed["consent_status"], "evidence_class": store.evidence_class(document),
                "checks": {**row["checks"], **assessed["checks"]}}
    by_id = {p["passage_id"]: p for p in document["passage_map"]}
    refs = row["evidence_refs"]
    anchors = [by_id[r["passage_id"]] for r in refs if "anchor" in r["roles"] and r["passage_id"] in by_id]
    context = [by_id[r["passage_id"]] for r in refs if r["passage_id"] in by_id]
    columns = store.derive_columns(body=body, document=document, anchors=anchors, context=context, client_consent=consent, roster=roster)
    if columns["speaker_id"] not in people:
        columns["speaker_id"] = None
    kept = {k: v for k, v in row["checks"].items() if k not in DERIVED}
    return {**{c: columns[c] for c in COLUMNS}, "checks": {**kept, **columns["checks"]}}


def recheck(repo, *, ids=None, document_ids=None, client_id=None, apply: bool = True) -> dict:
    """Re-derive the selected moments. Returns how many were read, how many changed (and which columns), and how many were skipped."""
    with repo.connection() as conn:
        return recheck_in(conn, ids=ids, document_ids=document_ids, client_id=client_id, apply=apply)


def recheck_in(conn, *, ids=None, document_ids=None, client_id=None, apply: bool = True) -> dict:
    """`recheck` inside the caller's transaction. Normalisation calls it for the document it just normalised, and the client
    import for a client whose consent changed, so what may be said about a moment follows the facts without a manual step.
    The roster is read only when there is a stored moment to re-derive (normalising a document before its extraction needs
    no knowledge base)."""
    from ..repository import review_roster
    changed, columns_changed, skipped = [], {}, 0
    rows = select_rows(conn, ids=ids, document_ids=document_ids, client_id=client_id)
    if not rows:
        return {"read": 0, "changed": 0, "columns_changed": {}, "skipped_without_document": 0, "applied": apply, "moment_ids": []}
    roster = review_roster(conn)
    documents = {d["transcript_id"]: d for d in conn.execute(
        "SELECT * FROM transcripts WHERE transcript_id=ANY(%s)", (sorted({r["document_id"] for r in rows}),))}
    consents = {c["client_id"]: c["consent"] for c in conn.execute("SELECT client_id,consent FROM clients")}
    people = {p["person_id"] for p in conn.execute("SELECT person_id FROM people")}
    for row in rows:
        document = documents.get(row["document_id"])
        if document is None:
            skipped += 1
            continue
        new = derive(row, document, consents.get(document.get("client_id")), roster, people)
        diff = [c for c in new if row.get(c) != new[c]]
        if not diff:
            continue
        changed.append(row["moment_id"])
        for c in diff:
            columns_changed[c] = columns_changed.get(c, 0) + 1
        if apply:
            conn.execute(f"UPDATE key_moments SET {','.join(f'{c}=%s' for c in new)} WHERE moment_id=%s",
                         [Jsonb(v) if c == "checks" else v for c, v in new.items()] + [row["moment_id"]])
    return {"read": len(rows), "changed": len(changed), "columns_changed": columns_changed, "skipped_without_document": skipped,
            "applied": apply, "moment_ids": changed[:200]}
