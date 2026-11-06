"""Published pieces and their performance (L.B7; content memory, architecture §7.1).

- CSV import and manual entry: date, channel, piece and metric, stored on `published_content.performance` and
  linked to the brief behind the piece (`published_content.brief_id`, with the brief's card as `angle_id`).
- The export's recorded outcomes (synthesis 4.6 and the published-content log), seeded once by L.B2 onto the
  pieces they describe. They are qualitative ("replies within a week; one spot sold"), so each carries a
  direction: positive or negative.
- The strategist's situational block lists the last 90 days' strongest and weakest pieces (L.B5).

Each entry is {date, metric, value, direction, source, entered_by}. Numeric values are compared only within
the same metric: a piece ranks by its best percentile within its metrics.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
from datetime import date

from ..repository import identifier, insert
from . import review

MAX_ROWS = 2000
# The outcomes the export records (synthesis 4.6, published-content log), matched to their pieces by the
# published-log row's date and a phrase from its title.
EXPORT_OUTCOMES = [
    ("2025-09-24", "reality check", "positive", "Replies within a week; one promo spot sold and a contract sent by 7 Oct 2025"),
    ("2025-11", "Want the replay", "positive", '"Want the replay? Just reply": "That got me some replies"'),
    ("2026-01-20", "Venue Masterclass", "positive", 'Reply "Send it" email: "a great response"'),
    ("2026-04", "conversation clips", "negative", 'Repeated short conversation clips: "we lost a lot of followers"'),
    ("2026-04-30", "More leads won't fix this", "negative", "Sent to the WIA list (about 840): no demos booked; the host-sent version booked demos"),
    ("2026-06-02", "Visibility Blueprint", "negative", "Visibility Blueprint email: 2 opt-ins; carousel: 1 profile visit"),
    ("2026-07-31", "Case-study Reel", "positive", 'Case-study Reel and email: "They did well"'),
    ("2026-08-03", "New welcome DM", "positive", "Multi-message replies within 48 hours"),
]


def _entry_id(*parts) -> str:
    return hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest()[:16]


def _append(conn, content_id, item) -> bool:
    row = conn.execute("SELECT performance FROM published_content WHERE content_id=%s FOR UPDATE", (content_id,)).fetchone()
    if not row:
        raise LookupError("Published piece not found")
    if any(e.get("id") == item["id"] for e in row["performance"]):
        return False
    conn.execute("UPDATE published_content SET performance=performance || %s::jsonb,updated_at=now() WHERE content_id=%s",
                 (json.dumps([item]), content_id))
    return True


def seed_export_outcomes(conn, actor: str) -> int:
    """Attach the export's recorded outcomes to their published-log pieces; idempotent."""
    added = 0
    for when, phrase, direction, value in EXPORT_OUTCOMES:
        rows = conn.execute("""SELECT content_id FROM published_content WHERE source_kind='export_seed'
            AND details->>'date_text' LIKE %s AND title ILIKE %s ORDER BY content_id""", (when + "%", f"%{phrase}%")).fetchall()
        for r in rows:
            entry = {"id": _entry_id("export", r["content_id"], phrase), "date": when, "metric": "outcome", "value": value,
                     "direction": direction, "source": "ChatGPT export (synthesis 4.6, published-content log)", "entered_by": actor}
            added += _append(conn, r["content_id"], entry)
    return added


def _number(value):
    try:
        return float(str(value).replace(",", "").replace("%", "").strip())
    except ValueError:
        return None


def strongest_and_weakest(rows: list[dict], n: int = 3) -> tuple[list[str], list[str]]:
    """The strongest and weakest pieces among rows with performance, as lines for the situational block."""
    scored = []
    by_metric: dict[str, list[float]] = {}
    for r in rows:
        for e in r.get("performance") or []:
            v = _number(e.get("value"))
            if v is not None:
                by_metric.setdefault(e["metric"], []).append(v)
    for r in rows:
        best, note = None, None
        for e in r.get("performance") or []:
            v = _number(e.get("value"))
            if v is not None and len(by_metric[e["metric"]]) > 1:
                values = sorted(by_metric[e["metric"]])
                score = values.index(v) / (len(values) - 1)
            elif e.get("direction") in ("positive", "negative"):
                score = 1.0 if e["direction"] == "positive" else 0.0
            else:
                continue
            if best is None or score > best:
                best, note = score, f"{e['metric']}: {e['value']}"
        if best is not None:
            when = r["published_on"].isoformat() if r.get("published_on") else "undated"
            scored.append((best, f"{when} {r['channel']}: {r['title']} ({note})"))
    scored.sort(key=lambda x: x[0])
    strong = [line for score, line in reversed(scored) if score >= 0.5][:n]
    weak = [line for score, line in scored if score < 0.5][:n]
    return strong, weak


def _brief_link(conn, brief_id):
    if not brief_id:
        return None, None
    row = conn.execute("SELECT brief_id,angle_id,approval_status FROM content_briefs WHERE brief_id=%s", (brief_id,)).fetchone()
    if not row:
        raise ValueError("Brief not found")
    if row["approval_status"] != "approved":
        raise ValueError("Link a published piece to the approved brief behind it")
    return row["brief_id"], row["angle_id"]


def add_piece(conn, settings, actor, *, published_on: date, channel: str, title: str, text=None, brief_id=None,
              pillar=None, content_type=None, reason="Published") -> dict:
    """An approver records a published piece, optionally linked to the approved brief behind it."""
    review.require(settings, actor)
    brief_id, angle_id = _brief_link(conn, brief_id)
    content_id = identifier("published")
    insert(conn, "published_content", {"content_id": content_id, "published_on": published_on, "channel": channel.strip(),
                                       "title": title.strip(), "text": text, "pillar": pillar, "content_type": content_type,
                                       "status": "confirmed", "source_kind": "approved_brief" if brief_id else "approver_entry",
                                       "source_ref": content_id, "brief_id": brief_id, "angle_id": angle_id,
                                       "created_by": actor, "details": {"reason": reason}})
    return {"content_id": content_id, "brief_id": brief_id, "angle_id": angle_id}


def link(conn, settings, actor, content_id, brief_id) -> dict:
    review.require(settings, actor)
    brief_id, angle_id = _brief_link(conn, brief_id)
    row = conn.execute("UPDATE published_content SET brief_id=%s,angle_id=%s,updated_at=now() WHERE content_id=%s RETURNING content_id",
                       (brief_id, angle_id, content_id)).fetchone()
    if not row:
        raise LookupError("Published piece not found")
    return {"content_id": content_id, "brief_id": brief_id, "angle_id": angle_id}


def entry(content_id, *, on: date, metric: str, value, direction=None, source="manual entry", actor) -> dict:
    """One measurement in the shape every reader takes. The same date, metric and value on the same piece is the same
    entry, however it arrived (manual entry, CSV or a published final's capture, L.B9), so it is never counted twice."""
    metric = (metric or "").strip().lower()
    if not metric or value in (None, ""):
        raise ValueError("A performance entry needs its metric and value")
    return {"id": _entry_id("manual", content_id, on, metric, value), "date": on.isoformat(), "metric": metric,
            "value": value, "source": source, "entered_by": str(actor), **({"direction": direction} if direction else {})}


def enter(conn, settings, actor, content_id, *, on: date, metric: str, value, direction=None, source="manual entry") -> dict:
    review.require(settings, actor)
    added = _append(conn, content_id, entry(content_id, on=on, metric=metric, value=value, direction=direction, source=source,
                                            actor=actor))
    return {"content_id": content_id, "added": added}


def import_csv(conn, settings, actor, text: str) -> dict:
    """CSV with date, channel, piece, metric and value (and an optional brief_id). A piece is matched by its ID,
    or by date, channel and title; an unknown piece is recorded as a new confirmed published piece."""
    review.require(settings, actor)
    reader = csv.DictReader(io.StringIO(text))
    need = {"date", "channel", "piece", "metric", "value"}
    if not reader.fieldnames or not need <= {f.strip().lower() for f in reader.fieldnames}:
        raise ValueError("The CSV needs the columns date, channel, piece, metric and value")
    added = created = 0
    for i, raw in enumerate(reader, 1):
        if i > MAX_ROWS:
            raise ValueError(f"At most {MAX_ROWS} rows per import")
        row = {k.strip().lower(): (v or "").strip() for k, v in raw.items() if k}
        try:
            on = date.fromisoformat(row["date"])
        except ValueError:
            raise ValueError(f"Row {i}: the date must be YYYY-MM-DD") from None
        piece = conn.execute("""SELECT content_id FROM published_content WHERE content_id=%s
            OR (published_on=%s AND lower(channel)=lower(%s) AND lower(title)=lower(%s)) ORDER BY content_id LIMIT 1""",
                             (row["piece"], on, row["channel"], row["piece"])).fetchone()
        if piece:
            content_id = piece["content_id"]
        else:
            content_id = add_piece(conn, settings, actor, published_on=on, channel=row["channel"], title=row["piece"],
                                   brief_id=row.get("brief_id") or None, reason="CSV performance import")["content_id"]
            created += 1
        added += enter(conn, settings, actor, content_id, on=on, metric=row["metric"], value=row["value"], source="CSV import")["added"]
    return {"entries_added": added, "pieces_created": created}
