"""The delegated review of the one-time seed (L.F1, L.X2; decision D12 in plan section 15.1).

The owner instructed on 18 October 2026 that WIA's approvals are given and that Whitney reviews the final product at
the end of the plan, not each step. Under that delegation the implementing engineer reviewed every seeded candidate
and every published-log entry, with a reason for each decision. The record is committed
(`research/chatgpt-export-2026-10-18/seed-review-2026-10-18.json`) so every environment applies the same decisions
after `context-seed`, through the same review service a person uses in the app (one decision row each, the diff on
an edit, hash-bound), with the reviewer recorded as the owner who ran it and the author as the delegated reviewer.

Each decision names its candidate by source reference and the entry's content hash, so a changed draft is never
decided by a stale record: it is reported and left in the queue.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from . import review
from .seed import REPOSITORY_ROOT

RECORD = Path("research/chatgpt-export-2026-10-18/seed-review-2026-10-18.json")
AUTHOR = "Implementing engineer under WIA's delegation (D12, 18 October 2026)"


def normalise_dashes(text: str) -> str:
    """Em dashes in older approved copy become commas (V01: normalise older exemplars before reuse)."""
    text = re.sub(r"\s*—\s*", ", ", text)
    return re.sub(r",\s*,", ",", re.sub(r"  +", " ", text))


def load(root: Path = REPOSITORY_ROOT) -> dict:
    return json.loads((root / RECORD).read_text(encoding="utf-8"))


def apply(conn, settings, actor: str, *, root: Path = REPOSITORY_ROOT) -> dict:
    """Apply the committed review; idempotent (decided entries are skipped)."""
    record = load(root)
    applied, skipped, stale, missing = {"accept": 0, "edit": 0, "reject": 0}, 0, [], []
    for entry in record["decisions"]:
        row = conn.execute("SELECT * FROM brand_kit_items WHERE source_ref=%s AND source_kind=ANY(%s)",
                           (entry["source_ref"], ["export_seed", "knowledge_base"])).fetchone()
        if not row:
            missing.append(entry["source_ref"])
            continue
        if row["status"] != "candidate":
            skipped += 1
            continue
        if entry.get("entry_sha256") and (row["source_detail"] or {}).get("entry_sha256") not in (None, entry["entry_sha256"]):
            stale.append(entry["source_ref"])
            continue
        action, changes = entry["action"], dict(entry.get("changes") or {})
        if "body_update" in changes:
            changes["body"] = {**row["body"], **changes.pop("body_update")}
        if row["kind"] == "exemplar" and action != "reject" and "—" in row["body"].get("text", ""):
            body = changes.get("body") or row["body"]
            changes["body"] = {**body, "text": normalise_dashes(body["text"])}
            changes.setdefault("text", normalise_dashes(row["text"]))
            entry = {**entry, "reason": entry["reason"] + "; em dashes normalised to commas (V01)"}
            action = "edit"
        if action == "accept" and ("body" in changes or "text" in changes):
            action = "edit"
        review.decide(conn, settings, row["item_id"], row["hash"], action, actor, reason=entry["reason"], author=AUTHOR,
                      changes=changes or None)
        applied[action] += 1
    confirmed = 0
    pieces = record.get("published_confirm") or []
    if pieces:
        refs = [p["source_ref"] for p in pieces]
        ids = [r["content_id"] for r in conn.execute(
            "SELECT content_id FROM published_content WHERE source_ref=ANY(%s) AND status='unconfirmed'", (refs,))]
        for start in range(0, len(ids), review.MAX_BATCH):
            confirmed += review.confirm_published(conn, settings, ids[start:start + review.MAX_BATCH], actor,
                                                  reason=record["published_reason"])["confirmed"]
    edits = [apply_edit(conn, settings, actor, edit) for edit in record.get("confirmed_edits") or []]
    left = conn.execute("SELECT count(*) n FROM brand_kit_items WHERE status='candidate'").fetchone()["n"]
    return {"applied": applied, "already_decided": skipped, "stale": stale, "missing": missing,
            "published_confirmed": confirmed, "candidates_left": left, "confirmed_edits": edits}


def apply_edit(conn, settings, actor: str, edit: dict) -> str:
    """An edit to an entry already confirmed: a new version of its key from `valid_from`, entered through the approver
    path (L.F2) with its reason; recorded once (idempotent by its key and date)."""
    from datetime import date, timedelta

    from . import items
    start = date.fromisoformat(edit["valid_from"])
    if conn.execute("""SELECT 1 FROM brand_kit_items WHERE key=%s AND source_kind='approver_entry' AND valid_from=%s
            AND status IN ('confirmed','retired')""", (edit["key"], start)).fetchone():
        return f"{edit['key']}: already applied"
    row = next((r for r in items.items_valid_at(conn, None, start - timedelta(days=1), kinds=items.KINDS)
                if r["key"] == edit["key"]), None)
    if row is None:
        return f"{edit['key']}: no confirmed entry to edit"
    body = {**row["body"], **(edit.get("body_update") or {})}
    if edit.get("patterns_update"):
        body["patterns"] = [{**p, **edit["patterns_update"]} for p in body.get("patterns") or []]
    keep = edit.get("provenance") == "keep"
    if keep and row["kind"] == "rule":
        # A rule refiled, its words unchanged (E.B11): it keeps its author, date and origin, which the new version's own
        # source (an approver entry) would otherwise replace. An origin the prefix cannot show (a quote) becomes the
        # citations it showed; the quote stays on the earlier version.
        from .compiler import rule_origin, short_origin
        if not short_origin(body.get("origin")):
            body["origin"] = rule_origin(row)
    result = review.enter(conn, settings, actor, kind=row["kind"], key=edit["key"], body=body, visibility=row["visibility"],
                          sensitivity=row["sensitivity"], permission=row["permission"], valid_from=start,
                          author=AUTHOR, reason=edit["reason"], today=start,
                          stated=row["statement_date"] if keep else None, stated_by=row["author"] if keep else None,
                          idempotency_key=f"seed-review:{edit['key']}:{edit['valid_from']}")
    return f"{edit['key']}: {'already applied' if result.get('repeated') else 'new version from ' + edit['valid_from']}"


