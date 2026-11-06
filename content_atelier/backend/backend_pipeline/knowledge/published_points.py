"""Twelve months of WIA's published central points (E.B25 (f)) and the same-point check they feed (3.B5).

The context seed records WIA's published log as `published_content` rows (source_kind `export_seed`, unconfirmed, the
title only). `backend/knowledge_base/published-central-points.json` is derived once from that committed log (never from
the export, R52): for every row, its first publish date and its central point as the engineer read it (D21). `apply`
(`storage_cli context-published-points`) writes each point onto its row as `key_message`, dates a row the log dates only
by month, inserts a row the seed has not, and confirms the rows through the review service, one decision each. It is
idempotent: a second run changes nothing.

A campaign is its pieces (E.B25 (i), the 3.B10 extension): an entry may list `pieces`, each published piece of the campaign
with its own date, channel, title and central point (the 5 October 2026 audit giveaway's posts argued their own points, not
"apply for a free audit"). A piece is its own row (`<campaign source_ref>/<piece>`), confirmed like any other, so the
same-point check and the recency penalty (cycle.recency) compare a card with each piece.

`recent(conn, on)` gives the card verifier the confirmed central points of the last twelve months (`WINDOW_DAYS`),
leaving out anything that states held-out benchmark material (E.B17); the verifier's same-point check
(`cycle.verification.same_point`) flags a card that repeats one, naming it.
"""
from __future__ import annotations

import hashlib
import json
from datetime import date, timedelta
from pathlib import Path

from ..config import BACKEND_ROOT
from ..repository import insert
from . import held_out, review

FILE = BACKEND_ROOT / "knowledge_base" / "published-central-points.json"
WINDOW_DAYS = 365
SOURCE_KIND = "export_seed"
PRECISIONS = ("day", "month", "approximate")


def load(path: Path = FILE) -> list[dict]:
    entries = json.loads(Path(path).read_text(encoding="utf-8"))["entries"]
    refs = [e["source_ref"] for e in entries]
    if len(refs) != len(set(refs)):
        raise ValueError(f"{Path(path).name}: each log row appears once")
    for e in [*entries, *(p for e in entries for p in pieces(e))]:
        date.fromisoformat(e["published_on"])
        if e.get("date_precision") not in PRECISIONS or not (e.get("key_message") or "").strip() or not (e.get("title") or "").strip():
            raise ValueError(f"{Path(path).name}: {e['source_ref']} needs a date, its precision, a title and a central point")
    return entries


def pieces(entry: dict) -> list[dict]:
    """A campaign entry's pieces as entries of their own: each names its campaign's row and its own key."""
    out = []
    for p in entry.get("pieces") or []:
        if not (p.get("piece") or "").strip():
            raise ValueError(f"{FILE.name}: every piece of {entry['source_ref']} needs its own key")
        out.append({"export_status": entry.get("export_status"), **{k: v for k, v in p.items() if k != "piece"},
                    "source_ref": f"{entry['source_ref']}/{p['piece']}", "campaign": entry["source_ref"]})
    return out


def flat(entries: list[dict]) -> list[dict]:
    """Every row the published register holds: each entry, then its pieces."""
    return [x for e in entries for x in (e, *pieces(e))]


def _point(e: dict) -> dict:
    return {"key_message": e["key_message"].strip(), "date_precision": e["date_precision"], "source": FILE.name}


def apply(conn, settings, actor, *, path: Path = FILE) -> dict:
    """Write each central point onto its published row and confirm it (an approver, through the review service)."""
    review.require(settings, actor)
    entries = load(path)
    rows = flat(entries)
    created = updated = 0
    waiting = []
    for e in rows:
        on, point = date.fromisoformat(e["published_on"]), _point(e)
        row = conn.execute("""SELECT content_id,status,published_on,key_message,details FROM published_content
            WHERE source_kind=%s AND source_ref=%s FOR UPDATE""", (SOURCE_KIND, e["source_ref"])).fetchone()
        if not row:
            content_id = "published_" + hashlib.sha256(e["source_ref"].encode()).hexdigest()[:24]
            insert(conn, "published_content", {
                "content_id": content_id, "published_on": on, "channel": e["channel"], "title": e["title"][:2000],
                "key_message": point["key_message"], "status": "unconfirmed", "source_kind": SOURCE_KIND,
                "source_ref": e["source_ref"], "created_by": str(actor),
                "details": {"date_text": e.get("date_text"), "export_status": e.get("export_status"), "central_point": point,
                            **({"campaign": e["campaign"]} if e.get("campaign") else {})}})
            created += 1
            waiting.append(content_id)
            continue
        if row["key_message"] != point["key_message"] or row["published_on"] is None \
                or (row["details"] or {}).get("central_point") != point:
            conn.execute("""UPDATE published_content SET key_message=%s,published_on=COALESCE(published_on,%s),
                details=details || jsonb_build_object('central_point',%s::jsonb),updated_at=now() WHERE content_id=%s""",
                         (point["key_message"], on, json.dumps(point), row["content_id"]))
            updated += 1
        if row["status"] == "unconfirmed":
            waiting.append(row["content_id"])
    confirmed = 0
    reason = ("Published central points (E.B25 (f)): the piece is in WIA's published log, confirmed with its central "
              "point by the engineer under D21")
    for start in range(0, len(waiting), review.MAX_BATCH):
        confirmed += review.confirm_published(conn, settings, waiting[start:start + review.MAX_BATCH], actor, reason=reason)["confirmed"]
    return {"entries": len(entries), "pieces": len(rows) - len(entries), "created": created, "updated": updated,
            "confirmed": confirmed, "unchanged": len(rows) - created - updated}


def recent(conn, on: date, days: int = WINDOW_DAYS) -> list[dict]:
    """The confirmed central points published in the `days` before `on`, newest first, for the same-point check."""
    if not conn.execute("SELECT to_regclass('public.published_content') AS t").fetchone()["t"]:
        return []
    rows = conn.execute("""SELECT content_id,published_on,channel,title,key_message FROM published_content
        WHERE status='confirmed' AND key_message IS NOT NULL AND published_on BETWEEN %s AND %s
        ORDER BY published_on DESC, content_id""", (on - timedelta(days=days), on)).fetchall()
    # The held-out filter reads `text`: a central point that states held-out material is withheld like its title.
    kept = held_out.keep([{**r, "text": r["key_message"]} for r in rows])
    return [{"content_id": r["content_id"], "published_on": r["published_on"].isoformat(), "channel": r["channel"],
             "title": r["title"], "key_message": r["key_message"]} for r in kept]
