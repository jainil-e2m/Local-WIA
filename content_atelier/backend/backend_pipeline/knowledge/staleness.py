"""Staleness and validity (L.B8; absorbs 6.B14; section 4.12).

Each item kind and each document has a review interval. The nightly job:

- retires confirmed items whose `valid_to` has passed, with a decision row for each, so the next run cannot use
  them (the assembly service also filters by date, so a run never sees an expired item even before the job);
- warns on items and documents past their review date: a roster or an offer sheet not reviewed in 30 days, a
  rule in 90, and so on.

The warnings appear on the cycle (`GET /storage/weeks/{id}` returns `context_warnings`) and are recorded on
each run that uses the store (`refs()["context"]["warnings"]`). Beside them (L.B11), the cycle says when confirmed
identity items (rules, exemplars, beliefs, audience language, format) wait to be compiled into a version, and where an
approved identity change stands with its scheduled benchmark.
"""
from __future__ import annotations

import json
import logging
from datetime import UTC, date, datetime, timedelta

from .. import settings_store
from ..repository import identifier, insert
from . import compiler, items

# Review intervals in days, per kind (operating facts monthly, identity quarterly; section 4.12's layers).
REVIEW_DAYS = settings_store.REVIEW_DAYS
log = logging.getLogger(__name__)
MARKER = "context.staleness"


def review_days(kind: str, conn=None) -> int:
    """The kind's interval: the context.review_interval.<kind> setting (a row, else
    ATELIER_CONTEXT_REVIEW_DAYS_<KIND>, for example ATELIER_CONTEXT_REVIEW_DAYS_ROSTER_MEMBER, else the default)."""
    return settings_store.value(f"context.review_interval.{kind}", conn)


def warnings(conn, today: date | None = None) -> list[dict]:
    """Items and documents past their review date, as short messages for the cycle and the run."""
    today = today or date.today()
    if not items.table_ready(conn):
        return []
    out = []
    rows = conn.execute("""SELECT kind,count(*) n,min(coalesce(reviewed_at::date,created_at::date)) oldest
        FROM brand_kit_items WHERE status='confirmed' GROUP BY kind ORDER BY kind""").fetchall()
    for r in rows:
        due = r["oldest"] + timedelta(days=review_days(r["kind"], conn))
        if today > due:
            overdue = conn.execute("""SELECT count(*) n FROM brand_kit_items WHERE status='confirmed' AND kind=%s
                AND coalesce(reviewed_at::date,created_at::date) < %s""", (r["kind"], today - timedelta(days=review_days(r["kind"], conn)))).fetchone()["n"]
            out.append({"scope": "kind", "kind": r["kind"], "overdue": overdue, "since": due.isoformat(),
                        "message": f"{overdue} confirmed {r['kind'].replace('_', ' ')} entries are past their "
                                   f"{review_days(r['kind'], conn)}-day review"})
    version = compiler.active_version(conn)
    if version:
        for d in conn.execute("""SELECT key,effective_date,review_interval_days FROM brand_kit_docs WHERE version=%s
                ORDER BY key""", (version,)).fetchall():
            due = d["effective_date"] + timedelta(days=d["review_interval_days"])
            if today > due:
                out.append({"scope": "document", "key": d["key"], "since": due.isoformat(),
                            "message": f"The {d['key'].replace('_', ' ')} document was due for review on {due.isoformat()}"})
    try:
        # A savepoint: a notice that cannot be worked out (a knowledge base that does not load here) never breaks the
        # cycle's view or a run's context; the review warnings above stand.
        with conn.transaction():
            out += identity_notices(conn, today)
    except Exception:
        log.warning("The knowledge-base notices could not be worked out", exc_info=True)
    return out


def identity_notices(conn, today: date) -> list[dict]:
    """L.B11: confirmed identity items no version has compiled yet, and an approved identity change waiting for its
    benchmark (with what the scheduled benchmark found, or why it cannot run)."""
    from ..cycle.verification import knowledge_root
    from . import benchmarking
    out = []
    waiting = compiler.identity_waiting(conn, today, knowledge_root())
    if waiting["documents"]:
        names = ", ".join(k.replace("_", " ") for k in waiting["documents"])
        counted = f"{waiting['items']} confirmed identity items" if waiting["items"] else "Confirmed identity items"
        out.append({"scope": "compile", "documents": waiting["documents"], "items": waiting["items"],
                    "message": f"{counted} wait to be compiled ({names}): compile a new version under What the system "
                               "knows, Versions, and approve it; its benchmark is scheduled once it is approved"})
    for draft in waiting["drafts"]:
        when = f"compiled on {draft['on']}" if draft.get("on") else draft["version"]
        out.append({"scope": "approval", "key": draft["version"],
                    "message": f"The knowledge base {when} changes identity documents and waits for an identity approver: "
                               "open its changes under What the system knows, Versions, and approve it"})
    if message := benchmarking.notice(benchmarking.status(conn)):
        out.append({"scope": "benchmark", "message": message})
    return out


def plan_warning(conn, today: date | None = None) -> str | None:
    """The content plan's owner (L.B10): a cycle whose newest confirmed content plan entry was entered more than
    context.plan_max_age_days (30) ago, or that has none, says so in its week summary; the review owner's next monthly
    entry (L.F2) clears it. None without the context store."""
    today = today or date.today()
    if not items.table_ready(conn):
        return None
    days = settings_store.value("context.plan_max_age_days", conn)
    latest = conn.execute("""SELECT max(coalesce(reviewed_at,created_at))::date AS latest FROM brand_kit_items
        WHERE kind='content_plan_entry' AND status='confirmed'""").fetchone()["latest"]
    advice = "so strategic fit ranks against nothing current. Add this month's plan under What the system knows"
    if latest is None:
        return f"No content plan entry is recorded, {advice}."
    if (today - latest).days > days:
        return f"The content plan was last updated on {latest.isoformat()}, {(today - latest).days} days ago, {advice}."
    return None


def run(conn, *, actor: str = "staleness job", today: date | None = None) -> dict:
    """The nightly job: retire expired items, record the warnings. Idempotent for a day."""
    today = today or date.today()
    if not items.table_ready(conn):
        raise RuntimeError("Apply migration 006 before running the staleness job")
    expired = conn.execute("""UPDATE brand_kit_items SET status='retired',updated_at=now()
        WHERE status='confirmed' AND valid_to IS NOT NULL AND valid_to < %s RETURNING item_id,kind,key""", (today,)).fetchall()
    for row in expired:
        items.rehash(conn, row["item_id"])
        insert(conn, "decisions", {"decision_id": identifier("decision"), "item_kind": "brand_kit_item", "item_id": row["item_id"],
                                   "action": "context_retire", "note": "valid_to passed", "actor": actor, "author": actor,
                                   "details": {"kind": row["kind"], "key": row["key"], "on": today.isoformat()}})
    found = warnings(conn, today)
    record = {"run_on": today.isoformat(), "ran_at": datetime.now(UTC).isoformat(), "retired": [r["item_id"] for r in expired],
              "warnings": found}
    conn.execute("""INSERT INTO settings(key,value,updated_by) VALUES (%s,%s,%s)
        ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value,updated_by=EXCLUDED.updated_by,updated_at=now()""",
                 (MARKER, json.dumps(record), actor))
    return {"retired": len(expired), "warnings": found}
