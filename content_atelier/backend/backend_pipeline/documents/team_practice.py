"""Internal meetings admitted as team-practice evidence (plan 1.B13's extension, D24).

Normalisation excludes a call where only WIA's team speaks ("not client evidence"). That is right for client evidence and
wrong for WIA's own story: the internal meetings are where its behind-the-scenes work lives (how the team reviews an
account, the standards it holds, what it built for a client, a decision about a service). D24 admits them as evidence of
how WIA works, never as a client's quote, name or figure.

`admit` includes every internal meeting that was excluded only for being internal: by the rule ("Internal call: only WIA
staff speak"), or by a person who confirmed only the team speaks. Anything excluded for another reason stays out (a
non-wedding business, personal chatter, a partner's candid debrief, a test call, a fragment). The setting
`documents.included_call_types` must include `internal` first, so normalising again keeps the rule's documents in; a
person's decision is recorded as a new person decision, which normalisation never overwrites. An admitted document's
scenes are team practice (key_moments.evidence_class, moments/store.py), extracted under scene profile v4, which records
how the team works and keeps client details out.
"""
from __future__ import annotations

from datetime import UTC, datetime

from psycopg.types.json import Jsonb

from ..normalise.classify import REASONS

PERSON_CONFIRMED = "Confirmed by reading: only WIA's team"
BASIS = ("Admitted as team-practice evidence (D24, 1.B13's extension): an internal meeting evidences how WIA works, never a "
         "client's quote, name or figure")


def candidates(conn) -> dict:
    """The internal meetings `admit` would include, and the excluded internal-or-other calls it leaves out, with why."""
    rows = conn.execute("""SELECT transcript_id,title,occurred_at,call_type,exclusion_reason,classification FROM transcripts
        WHERE NOT included AND normalised_at IS NOT NULL AND canonical_document_id IS NULL
          AND call_type IN ('internal','other') ORDER BY occurred_at NULLS LAST,transcript_id""").fetchall()
    admit, keep = [], []
    for r in rows:
        reason = r["exclusion_reason"] or ""
        if r["call_type"] == "internal" and (reason == REASONS["internal"] or reason.startswith(PERSON_CONFIRMED)):
            admit.append(r)
        else:
            keep.append(r)
    return {"admit": admit, "keep": keep}


def admit(repo, *, actor: str, apply: bool = False) -> dict:
    from ..moments import store as ledger
    from ..moments.recheck import recheck_in
    from ..settings_store import value as setting
    from .jobs import resegment
    with repo.connection() as conn:
        if apply and "internal" not in setting("documents.included_call_types", conn):
            raise ValueError("Add 'internal' to documents.included_call_types first (settings apply), so normalising again keeps "
                             "the rule's internal meetings included")
        found = candidates(conn)
        listed = {"admit": [{"transcript_id": r["transcript_id"], "title": r["title"], "was": r["exclusion_reason"]} for r in found["admit"]],
                  "left_excluded": [{"transcript_id": r["transcript_id"], "title": r["title"], "reason": r["exclusion_reason"]}
                                    for r in found["keep"]]}
        if not apply:
            return {"applied": False, **listed}
        now = datetime.now(UTC).isoformat()
        chunks = 0
        for r in found["admit"]:
            record = dict(r["classification"] or {})
            if record.get("method") == "person":
                # A person's decision stands until a person changes it: this admission is that change, recorded as delegated.
                record = {**record, "decided_by": actor, "decided_at": now, "reason": f"{record.get('reason') or ''} {BASIS}".strip()}
            record["team_practice"] = {"admitted_by": actor, "admitted_at": now, "basis": BASIS, "was_excluded_because": r["exclusion_reason"]}
            conn.execute("""UPDATE transcripts SET included=true,exclusion_reason=NULL,classification=%s,
                extraction_status=CASE WHEN extraction_status='not_applicable' THEN 'pending' ELSE extraction_status END
                WHERE transcript_id=%s""", (Jsonb(record), r["transcript_id"]))
            if ledger.has_ledger(conn):
                ledger.align_currency(conn, r["transcript_id"], True)
                recheck_in(conn, document_ids=[r["transcript_id"]])
            chunks += resegment(conn, r["transcript_id"]).get("added", 0)
        return {"applied": True, **listed, "chunks_added": chunks}
