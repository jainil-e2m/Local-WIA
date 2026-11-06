"""The review queue's service (L.B3, section 4.12, R51): a person decides every candidate.

- **List** candidates by kind and status, grouped by key, each with its source, author, model-written flag and
  what it would change in the next knowledge-base version.
- **Decide** accept, edit or reject, setting visibility, sensitivity, permission, validity and a reason. Each
  decision writes one `decisions` row (with the diff when the text is edited), and an accepted or edited item is
  confirmed and supersedes the confirmed item with the same key. Decisions are bound to the item's hash: a stale
  hash is refused (409).
- **Batch** decisions only for low-risk kinds (audience phrases) and published-log entries.
- **Approver entries** (L.F2): a fact an approver enters is confirmed on entry, with the approver as reviewer.

Approver-only: the approver role (the `users` table, else `ATELIER_BRIEF_APPROVERS`; gates/roles.py). Identity kinds (rules, exemplars, beliefs, audience
language, format) need an identity approver (`ATELIER_IDENTITY_APPROVERS`, Whitney under rulings 2.5); when that
list is empty, any approver. Confirming a roster member will also update the matching `people` row once Phase 1's
migration creates that table (1.B2).
"""
from __future__ import annotations

import re
from datetime import UTC, date, datetime

from ..gates.roles import access_for
from ..repository import identifier, insert, json_value
from . import items

ACTIONS = ("accept", "edit", "reject")
EDITABLE = ("text", "body", "visibility", "sensitivity", "permission", "valid_from", "valid_to")
MAX_BATCH = 100


def can_review(settings, actor: str, kind: str | None = None) -> bool:
    return bool(actor) and access_for(settings, actor).can_review(kind in items.IDENTITY_KINDS)


def require_reviewer(settings, actor: str):
    """Any reviewer (an approver or an identity approver), checked before anything is read (L.B3); the check for the
    entry's own kind follows once it is known."""
    if not actor or not access_for(settings, actor).can("review"):
        raise PermissionError("Knowledge-base review needs an approver (ATELIER_BRIEF_APPROVERS)")


def require(settings, actor: str, kind: str | None = None):
    if not can_review(settings, actor, kind):
        if kind in items.IDENTITY_KINDS and settings.identity_approvers:
            raise PermissionError("Identity changes (rules, exemplars, voice) need an identity approver (ATELIER_IDENTITY_APPROVERS)")
        raise PermissionError("Knowledge-base review needs an approver (ATELIER_BRIEF_APPROVERS)")


def _public(row: dict) -> dict:
    out = {k: (v.isoformat() if isinstance(v, (date, datetime)) else v) for k, v in row.items() if k != "embedding"}
    return out


def would_change(conn, row: dict) -> dict:
    """What deciding this candidate would change in the next version: the document, and any item it replaces."""
    current = conn.execute("""SELECT item_id,text FROM brand_kit_items WHERE key=%s AND status='confirmed'
        AND item_id<>%s ORDER BY created_at DESC LIMIT 1""", (row["key"], row["item_id"])).fetchone()
    document = items.DOCUMENT_FOR_KIND[row["kind"]]
    layer = "operating (takes effect when confirmed)" if row["kind"] in items.OPERATING_KINDS else \
        "identity (takes effect through an approved, benchmarked version)"
    return {"document": document, "layer": layer,
            "replaces": {"item_id": current["item_id"], "text": current["text"]} if current else None,
            "summary": (f"Replaces the confirmed entry in {document}" if current else f"Adds an entry to {document}")}


WORD = re.compile(r"[a-z0-9$]+")
STOP = frozenset("a an and are as at be but by for from has have in is it its not of on or that the their them they this to "
                 "was we with you your our".split())


def _words(text: str) -> set[str]:
    return {w for w in WORD.findall((text or "").lower()) if w not in STOP and len(w) > 2}


def overlap(a: str, b: str) -> float:
    x, y = _words(a), _words(b)
    return len(x & y) / min(len(x), len(y)) if x and y else 0.0


def suggest(conn, row: dict, confirmed: list[dict] | None = None) -> dict:
    """A suggested decision with its reason, to speed the reviewer up. Never applied without a person's decision.

    The rules are mechanical: a near-duplicate of a confirmed entry, a quote superseded by a later one, an
    analysis note that cites only its draft, or a client-private result kept internal so the verifier blocks it.
    """
    detail = row.get("source_detail") or {}
    body = row.get("body") or {}
    if confirmed is None:
        confirmed = conn.execute("SELECT item_id,key,kind,text,body FROM brand_kit_items WHERE status='confirmed' AND kind=%s",
                                 (row["kind"],)).fetchall()
    if detail.get("citations_from") == "draft":
        return {"action": "reject", "reason": "An analysis note that cites no conversation; not WIA's own statement"}
    if "out of scope" in (detail.get("section") or "").lower():
        return {"action": "reject", "reason": "The draft marks this section out of scope for WIA's own marketing"}
    same_key = [c for c in confirmed if c["key"] == row["key"]]
    if row["kind"] == "rule" and body.get("statement"):
        # A rule is covered when a confirmed rule says the same thing; the draft's evidence stays in the draft.
        rule = max(confirmed, key=lambda c: overlap(body["statement"], (c["body"] or {}).get("statement", "")), default=None)
        if rule is not None and overlap(body["statement"], rule["body"].get("statement", "")) >= 0.6:
            return {"action": "reject", "reason": f"Covered by confirmed rule {rule['body'].get('code') or ''}: "
                                                  f"{rule['body']['statement'][:160]}".replace("  ", " "),
                    "duplicate_of": rule["item_id"]}
    best = max(confirmed, key=lambda c: overlap(row["text"], c["text"]), default=None)
    if best is not None and overlap(row["text"], best["text"]) >= 0.8 and len(_words(row["text"])) <= 1.3 * len(_words(best["text"])):
        return {"action": "reject", "reason": f"Already covered by a confirmed entry: {best['text'][:160]}",
                "duplicate_of": best["item_id"]}
    if row["kind"] == "price":
        later = conn.execute("""SELECT count(*) n FROM brand_kit_items WHERE kind='price' AND item_id<>%s
            AND body->>'offer'=%s AND statement_date>%s""", (row["item_id"], body.get("offer"), row["statement_date"])).fetchone()["n"]
        if later:
            return {"action": "reject", "reason": "A later quote for the same offer exists; this price is out of date"}
        return {"action": "accept", "reason": "The latest quote for this offer; internal, so it never reaches public copy",
                "changes": {"visibility": "internal"}}
    if row["kind"] == "result":
        if row.get("permission") == "published":
            return {"action": "accept", "reason": "WIA published this result; reuse keeps the original framing"}
        return {"action": "accept", "reason": "Kept internal so the verifier blocks it in public copy until the client agrees",
                "changes": {"visibility": "internal", "sensitivity": "client_private"}}
    if row["kind"] == "exemplar":
        if body.get("label") in ("approved_final", "accepted_hook", "preference_pair"):
            return {"action": "accept", "reason": "Copy Whitney approved, published or rewrote herself"}
        return {"action": "review", "reason": "A draft of hers; accept only if it reads as finished"}
    if row["kind"] == "offer" and row.get("statement_date") and row["statement_date"].year < 2026:
        return {"action": "reject", "reason": "A 2025 offer fact; the 14 October 2026 offer sheet supersedes it"}
    if same_key:
        return {"action": "review", "reason": "Would replace the confirmed entry for the same key; compare them"}
    if row.get("confidence") == "low":
        return {"action": "review", "reason": "Low confidence in the draft"}
    return {"action": "accept", "reason": "Cited to WIA's own material and not covered by a confirmed entry"}


def queue(conn, *, kind=None, status="candidate", limit=50, offset=0, actor=None, settings=None) -> dict:
    if status not in items.STATUSES:
        raise ValueError("Unknown status")
    if kind is not None and kind not in items.SCHEMAS:
        raise ValueError("Unknown item kind")
    where, params = "status=%s", [status]
    if kind:
        where += " AND kind=%s"
        params.append(kind)
    total = conn.execute(f"SELECT count(*) n FROM brand_kit_items WHERE {where}", params).fetchone()["n"]
    rows = conn.execute(f"""SELECT * FROM brand_kit_items WHERE {where}
        ORDER BY kind, key, statement_date DESC NULLS LAST, item_id LIMIT %s OFFSET %s""", [*params, limit, offset]).fetchall()
    out, confirmed = [], {}
    for r in rows:
        item = _public(r)
        item["would_change"] = would_change(conn, r)
        if status == "candidate":
            if r["kind"] not in confirmed:
                confirmed[r["kind"]] = conn.execute("""SELECT item_id,key,kind,text,body FROM brand_kit_items
                    WHERE status='confirmed' AND kind=%s""", (r["kind"],)).fetchall()
            item["suggestion"] = suggest(conn, r, confirmed[r["kind"]])
        if settings is not None and actor:
            item["can_decide"] = can_review(settings, actor, r["kind"])
        out.append(item)
    groups: dict[str, list[str]] = {}
    for item in out:
        groups.setdefault(item["key"], []).append(item["item_id"])
    return {"items": out, "groups": {k: v for k, v in groups.items() if len(v) > 1}, "total": total,
            "limit": limit, "offset": offset, "batch_kinds": sorted(items.LOW_RISK_KINDS)}


def summary(conn) -> dict:
    rows = conn.execute("SELECT kind,status,count(*) n FROM brand_kit_items GROUP BY kind,status ORDER BY kind,status").fetchall()
    by_kind: dict[str, dict] = {}
    for r in rows:
        by_kind.setdefault(r["kind"], {})[r["status"]] = r["n"]
    published = conn.execute("SELECT status,count(*) n FROM published_content GROUP BY status").fetchall()
    return {"kinds": by_kind, "candidates": sum(v.get("candidate", 0) for v in by_kind.values()),
            "published": {r["status"]: r["n"] for r in published}}


def _date(value):
    if value in (None, ""):
        return None
    return value if isinstance(value, date) else date.fromisoformat(str(value))


def _diff(before: dict, after: dict) -> dict:
    return {k: {"before": _json(before.get(k)), "after": _json(after.get(k))} for k in EDITABLE
            if _json(before.get(k)) != _json(after.get(k))}


def _json(value):
    return value.isoformat() if isinstance(value, date) else value


def record(conn, *, item_id, action, disposition, actor, author, note, expected_hash, details, reason_code=None):
    decision_id = identifier("decision")
    insert(conn, "decisions", {"decision_id": decision_id, "item_kind": "brand_kit_item", "item_id": item_id,
                               "action": action, "disposition": disposition, "reason_code": reason_code, "note": note,
                               "actor": actor, "author": author, "expected_hash": expected_hash,
                               "resulting_item_id": item_id, "details": details})
    return decision_id


def decide(conn, settings, item_id, expected_hash, action, actor, *, reason, author=None, changes=None,
           today: date | None = None) -> dict:
    """Accept, edit or reject one candidate; one decision row; the item's new state and hash."""
    if action not in ACTIONS:
        raise ValueError("A decision is accept, edit or reject")
    reason = (reason or "").strip()
    if not reason:
        raise ValueError("Every decision records its reason")
    require_reviewer(settings, actor)
    row = items.get_item(conn, item_id, lock=True)
    require(settings, actor, row["kind"])
    if row["hash"] != expected_hash:
        raise ValueError("This entry changed since it was shown; reload the queue")
    if row["status"] != "candidate":
        raise ValueError(f"This entry is already {row['status']}")
    author = (author or "").strip() or actor
    changes = dict(changes or {})
    unknown = set(changes) - set(EDITABLE)
    if unknown:
        raise ValueError("Unknown fields: " + ", ".join(sorted(unknown)))
    if action == "edit" and not ({"text", "body"} & set(changes)):
        raise ValueError("An edit changes the text or the body; use accept to set only exposure or validity")
    if action == "reject" and changes:
        raise ValueError("A rejection takes a reason only")
    after = {k: row[k] for k in EDITABLE}
    if "body" in changes:
        after["body"] = items.validate_body(row["kind"], changes["body"])
    if "text" in changes:
        after["text"] = (changes["text"] or "").strip()
        if not after["text"]:
            raise ValueError("The text cannot be empty")
        if "body" not in changes:
            # The reviewer's exact wording is what every stage reads, so it is written into the body too.
            field = items.PRIMARY_FIELD[row["kind"]]
            after["body"] = items.validate_body(row["kind"], {**row["body"], field: after["text"]})
    elif "body" in changes:
        after["text"] = items.render(row["kind"], after["body"])
    for k in ("visibility", "sensitivity", "permission"):
        if k in changes:
            after[k] = changes[k]
    for k in ("valid_from", "valid_to"):
        if k in changes:
            after[k] = _date(changes[k])
    items.check_fields(row["kind"], row["key"], after["visibility"], after["sensitivity"], after["permission"],
                       after["valid_from"], after["valid_to"])
    after["body"] = items.internal_figures(row["kind"], after["body"], after["text"], after["visibility"])
    diff = _diff(row, after)
    status = "rejected" if action == "reject" else "confirmed"
    if status == "confirmed":
        items.require_category(row["kind"], after["body"])
    conn.execute("""UPDATE brand_kit_items SET text=%s,body=%s,visibility=%s,sensitivity=%s,permission=%s,valid_from=%s,
        valid_to=%s,status=%s,reviewed_by=%s,reviewed_at=%s,review_note=%s,updated_at=now() WHERE item_id=%s""",
                 (after["text"], json_value(after["body"]), after["visibility"], after["sensitivity"], after["permission"],
                  after["valid_from"], after["valid_to"], status, actor, datetime.now(UTC), reason, item_id))
    superseded = items.supersede(conn, item_id, today) if status == "confirmed" else []
    digest = items.rehash(conn, item_id)
    decision_id = record(conn, item_id=item_id, action="context_" + action,
                         disposition="reject" if action == "reject" else "approve", actor=actor, author=author,
                         note=reason, expected_hash=expected_hash,
                         details={"kind": row["kind"], "key": row["key"], "diff": diff, "superseded": superseded,
                                  "hash_after": digest, "source_kind": row["source_kind"], "source_ref": row["source_ref"]})
    return {"item_id": item_id, "status": status, "hash": digest, "decision_id": decision_id, "superseded": superseded,
            "diff": diff}


def batch(conn, settings, decisions: list[dict], action: str, actor: str, *, reason: str, author=None) -> dict:
    """Accept or reject several low-risk candidates at once; each still writes its own decision."""
    if action not in ("accept", "reject"):
        raise ValueError("A batch accepts or rejects; edit entries one by one")
    if not decisions or len(decisions) > MAX_BATCH:
        raise ValueError(f"A batch holds 1 to {MAX_BATCH} entries")
    # The role first, so a non-approver learns nothing about the entries (403, not 409).
    require(settings, actor)
    for d in decisions:
        kind = items.get_item(conn, d["item_id"])["kind"]
        if kind not in items.LOW_RISK_KINDS:
            raise ValueError(f"Batch decisions are only for low-risk kinds ({', '.join(sorted(items.LOW_RISK_KINDS))}); "
                             "decide this entry on its own")
    results = [decide(conn, settings, d["item_id"], d["expected_hash"], action, actor, reason=reason, author=author)
               for d in decisions]
    return {"decided": len(results), "results": results}


def confirm_published(conn, settings, content_ids: list[str], actor: str, *, reason: str) -> dict:
    """Confirm published-log entries (a low-risk batch): WIA says the piece went out."""
    require(settings, actor)
    if not content_ids or len(content_ids) > MAX_BATCH:
        raise ValueError(f"A batch holds 1 to {MAX_BATCH} entries")
    if not (reason or "").strip():
        raise ValueError("Every decision records its reason")
    rows = conn.execute("""UPDATE published_content SET status='confirmed',updated_at=now()
        WHERE content_id = ANY(%s) AND status='unconfirmed' RETURNING content_id""", (content_ids,)).fetchall()
    for r in rows:
        insert(conn, "decisions", {"decision_id": identifier("decision"), "item_kind": "published_content",
                                   "item_id": r["content_id"], "action": "published_confirm", "disposition": "approve",
                                   "note": reason.strip(), "actor": actor, "author": actor, "details": {}})
    return {"confirmed": len(rows)}


def enter(conn, settings, actor: str, *, kind: str, name: str | None = None, key: str | None = None, body: dict,
          text=None, visibility="public", sensitivity="none", permission=None, valid_from=None, valid_to=None,
          author=None, reason: str, today: date | None = None, idempotency_key: str | None = None,
          stated: date | None = None, stated_by: str | None = None) -> dict:
    """An approver's own entry (L.F2): confirmed on entry, superseding the current version of its key. When the entry
    changes how earlier words are filed, not what they say, `stated` and `stated_by` keep when and by whom they were
    first stated; the decision still records the approver's author."""
    require(settings, actor, kind)
    reason = (reason or "").strip()
    if not reason:
        raise ValueError("Every entry records its reason")
    if valid_from and valid_to and _date(valid_to) < _date(valid_from):
        raise ValueError("The end date must be on or after the start date")
    if not key:
        if not name:
            raise ValueError("Name the entry, or give the key of the entry it changes")
        key = items.key_for(kind, name)
    elif not key.startswith(items.KEY_PREFIX.get(kind, "?") + ":"):
        raise ValueError("That key belongs to another kind")
    ref = f"entry:{actor}:{idempotency_key.strip()}" if (idempotency_key or "").strip() else identifier("entry")
    existing = conn.execute("SELECT item_id FROM brand_kit_items WHERE source_kind='approver_entry' AND source_ref=%s",
                            (ref,)).fetchone()
    if existing:
        row = items.get_item(conn, existing["item_id"])
        return {"item_id": row["item_id"], "key": row["key"], "status": row["status"], "hash": row["hash"],
                "valid_from": _json(row["valid_from"]), "supersedes_id": row["supersedes_id"], "decision_id": None,
                "repeated": True}
    item_id, _ = items.add_item(conn, kind=kind, key=key, body=body, text=text, status="confirmed",
                                source_kind="approver_entry", source_ref=ref,
                                author=(stated_by or "").strip() or (author or "").strip() or actor,
                                created_by=actor, visibility=visibility, sensitivity=sensitivity, permission=permission,
                                valid_from=_date(valid_from), valid_to=_date(valid_to), reviewed_by=actor,
                                review_note=reason, statement_date=stated or today or date.today(), confidence="high")
    row = items.get_item(conn, item_id)
    decision_id = record(conn, item_id=item_id, action="context_enter", disposition="approve", actor=actor,
                         author=(author or "").strip() or actor, note=reason, expected_hash=None,
                         details={"kind": kind, "key": key, "supersedes_id": row["supersedes_id"], "hash_after": row["hash"]})
    return {"item_id": item_id, "key": key, "status": row["status"], "hash": row["hash"], "valid_from": _json(row["valid_from"]),
            "valid_to": _json(row["valid_to"]), "supersedes_id": row["supersedes_id"], "decision_id": decision_id}


def known(conn, *, kind=None, on: date | None = None) -> dict:
    """What the system knows (L.F2): confirmed items valid on a date, by kind, with source and validity."""
    on = on or date.today()
    kinds = [kind] if kind else list(items.KINDS)
    rows = items.items_valid_at(conn, None, on, kinds=kinds)
    scheduled = conn.execute("""SELECT * FROM brand_kit_items WHERE status='confirmed' AND valid_from>%s AND kind = ANY(%s)
        ORDER BY kind,key,valid_from""", (on, kinds)).fetchall()
    return {"on": on.isoformat(), "items": [_public(r) for r in rows], "scheduled": [_public(r) for r in scheduled]}


def history(conn, item_id: str) -> dict:
    """Every version of an item's key and every decision on them."""
    row = items.get_item(conn, item_id)
    versions = conn.execute("SELECT * FROM brand_kit_items WHERE key=%s ORDER BY created_at", (row["key"],)).fetchall()
    ids = [v["item_id"] for v in versions]
    decisions = conn.execute("""SELECT decision_id,item_id,action,disposition,note,actor,author,details,created_at
        FROM decisions WHERE item_kind='brand_kit_item' AND item_id = ANY(%s) ORDER BY created_at""", (ids,)).fetchall()
    return {"key": row["key"], "versions": [_public(v) for v in versions], "decisions": [_public(d) for d in decisions]}
