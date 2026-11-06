from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from ..packs import service as packs
from ..production_common import ProductionError, receipt, save_receipt
from ..repository import identifier, insert
from .contracts import Schedule, ScheduleItem


def authorize(repo, actor):
    if not repo.settings.calendar_enabled:
        raise ProductionError("Calendar scheduling is not enabled", "calendar_disabled", 503)
    if actor not in repo.settings.calendar_schedulers:
        raise PermissionError("Configured calendar scheduler capability is required")


def config(repo, actor):
    from ..worker_status import ready

    ZoneInfo(repo.settings.calendar_timezone)
    return {
        "worker_ready": ready(repo.settings),
        "enabled": repo.settings.calendar_enabled,
        "display_timezone": repo.settings.calendar_timezone,
        "server_time": datetime.now(UTC),
        "can_schedule": repo.settings.calendar_enabled and actor in repo.settings.calendar_schedulers,
        "packs_enabled": repo.settings.packs_enabled,
        "can_generate": repo.settings.packs_enabled and actor in repo.settings.pack_editors + repo.settings.pack_approvers,
        "live_generation_enabled": repo.settings.generation_enabled and repo.settings.pack_live_enabled,
    }


def channel(asset):
    return "email" if asset["asset_type"] == "email" else "instagram"


def entry_view(repo, conn, entry, pack=None, rows=None):
    a = conn.execute("SELECT * FROM content_assets WHERE asset_id=%s", (entry["asset_id"],)).fetchone()
    if not a:
        raise ProductionError("Scheduled asset is missing", "broken_lineage")
    if pack is None:
        pack = conn.execute("SELECT * FROM content_packs WHERE pack_id=%s", (a["pack_id"],)).fetchone()
        if not pack:
            raise ProductionError("Scheduled pack is missing", "broken_lineage")
        rows = packs.assets(conn, pack["pack_id"])
    warnings = packs.blockers(repo, conn, pack, rows, approved=True)
    if entry["asset_content_hash"] != a["content_hash"] or entry["pack_manifest_hash"] != pack["manifest_hash"]:
        warnings.append("Scheduled content version differs from its approved manifest")
    effective = "needs_review" if warnings and entry["status"] in {"scheduled", "needs_review"} else entry["status"]
    return {
        **entry,
        "pack_id": pack["pack_id"],
        "pack_title": pack["title"],
        "format": a["asset_type"],
        "title": ((a["content_body"] or {}).get("document") or {}).get("title", pack["title"]),
        "slot_key": a["slot_key"],
        "brief_id": a["brief_id"],
        "week_id": pack["week_id"],
        "effective_status": effective,
        "warnings": warnings,
        "overdue": entry["status"] == "scheduled" and entry["scheduled_for"] < datetime.now(UTC),
    }


def schedule(repo, pack_id, payload, actor):
    authorize(repo, actor)
    data = payload.model_dump(mode="json")
    operation = "schedule:" + pack_id
    with repo.connection() as conn:
        saved = receipt(conn, payload.request_id, actor, operation, data)
        if saved is not None:
            return saved
        pack, rows = packs.locked(repo, conn, pack_id)
        reasons = packs.blockers(repo, conn, pack, rows, approved=True)
        if pack["manifest_hash"] != payload.expected_pack_manifest_hash:
            raise ProductionError("Pack changed; refresh before scheduling", "stale_pack")
        if reasons:
            raise ProductionError("; ".join(reasons), "pack_blocked")
        by_id = {a["asset_id"]: a for a in rows}
        if payload.whole_pack and {i.asset_id for i in payload.items} != set(by_id):
            raise ProductionError("Whole-pack scheduling must include every asset", "incomplete_pack")
        entries = []
        audit_changes = []
        now = datetime.now(UTC)
        for item in sorted(payload.items, key=lambda i: i.asset_id):
            a = by_id.get(item.asset_id)
            if not a or a["content_hash"] != item.expected_asset_hash:
                raise ProductionError("Selected asset changed or does not belong to this pack", "stale_asset")
            if item.scheduled_for <= now:
                raise ProductionError("Choose a publishing time in the future", "past_time")
            if conn.execute(
                "SELECT 1 FROM calendar_entries WHERE asset_id=%s AND status='published'", (a["asset_id"],)
            ).fetchone():
                raise ProductionError("Already published assets require a new version for reuse", "already_published")
            current = conn.execute(
                """SELECT * FROM calendar_entries WHERE asset_id=%s AND channel=%s
                AND status IN ('scheduled','needs_review') FOR UPDATE""",
                (a["asset_id"], channel(a)),
            ).fetchone()
            if current:
                if current["calendar_entry_id"] != item.entry_id or current["revision"] != item.expected_revision:
                    raise ProductionError("Another scheduler changed this entry; refresh", "stale_schedule")
                if current["asset_content_hash"] != a["content_hash"]:
                    raise ProductionError("Replace the schedule rather than changing its content version", "stale_asset")
                conn.execute(
                    """UPDATE calendar_entries SET scheduled_for=%s,display_timezone=%s,status='scheduled',
                    revision=revision+1,updated_by=%s,updated_at=now() WHERE calendar_entry_id=%s""",
                    (item.scheduled_for, item.display_timezone, actor, item.entry_id),
                )
                eid = item.entry_id
            else:
                if item.entry_id is not None:
                    raise ProductionError("Schedule is no longer active; refresh", "stale_schedule")
                eid = identifier("calendar")
                insert(
                    conn,
                    "calendar_entries",
                    {
                        "calendar_entry_id": eid,
                        "asset_id": a["asset_id"],
                        "asset_content_hash": a["content_hash"],
                        "pack_manifest_hash": pack["manifest_hash"],
                        "channel": channel(a),
                        "scheduled_for": item.scheduled_for,
                        "status": "scheduled",
                        "display_timezone": item.display_timezone,
                        "created_by": actor,
                        "updated_by": actor,
                    },
                )
            e = conn.execute("SELECT * FROM calendar_entries WHERE calendar_entry_id=%s", (eid,)).fetchone()
            entries.append(entry_view(repo, conn, e, pack, rows))
            audit_changes.append(
                {
                    "asset_id": a["asset_id"],
                    "entry_id": eid,
                    "previous_time": current["scheduled_for"].isoformat() if current else None,
                    "scheduled_for": e["scheduled_for"].isoformat(),
                    "revision": e["revision"],
                }
            )
        packs.audit(
            repo,
            conn,
            pack,
            actor,
            "schedule_saved",
            {
                "pack_id": pack_id,
                "request_id": payload.request_id,
                "changes": audit_changes,
            },
        )
        # Receipts are JSON values, including timestamps, so replay has identical representation.
        from fastapi.encoders import jsonable_encoder

        return save_receipt(
            conn, payload.request_id, actor, operation, data, jsonable_encoder({"pack_id": pack_id, "entries": entries})
        )


def reschedule(repo, entry_id, payload, actor):
    authorize(repo, actor)
    with repo.connection() as conn:
        e = conn.execute(
            """SELECT ce.*,a.pack_id FROM calendar_entries ce JOIN content_assets a USING(asset_id)
            WHERE calendar_entry_id=%s""",
            (entry_id,),
        ).fetchone()
        if not e:
            raise ProductionError("Calendar entry not found", "not_found", 404)
    # The shared schedule service performs receipt lookup before version/time validation.
    request = Schedule(
        request_id=payload.request_id,
        expected_pack_manifest_hash=e["pack_manifest_hash"],
        items=[
            ScheduleItem(
                asset_id=e["asset_id"],
                expected_asset_hash=e["asset_content_hash"],
                entry_id=entry_id,
                expected_revision=payload.expected_revision,
                scheduled_for=payload.scheduled_for,
                display_timezone=payload.display_timezone,
            )
        ],
    )
    return schedule(repo, e["pack_id"], request, actor)


def cancel(repo, entry_id, payload, actor):
    authorize(repo, actor)
    data = payload.model_dump(mode="json")
    operation = "cancel:" + entry_id
    with repo.connection() as conn:
        saved = receipt(conn, payload.request_id, actor, operation, data)
        if saved is not None:
            return saved
        head = conn.execute(
            """SELECT a.pack_id FROM calendar_entries ce JOIN content_assets a USING(asset_id)
            WHERE calendar_entry_id=%s""",
            (entry_id,),
        ).fetchone()
        if not head:
            raise ProductionError("Calendar entry not found", "not_found", 404)
        pack, _ = packs.locked(repo, conn, head["pack_id"])
        e = conn.execute("SELECT * FROM calendar_entries WHERE calendar_entry_id=%s FOR UPDATE", (entry_id,)).fetchone()
        if e["revision"] != payload.expected_revision or e["status"] not in {"scheduled", "needs_review"}:
            raise ProductionError("Schedule changed or is no longer active; refresh", "stale_schedule")
        conn.execute(
            """UPDATE calendar_entries SET status='cancelled',revision=revision+1,updated_by=%s,
            updated_at=now() WHERE calendar_entry_id=%s""",
            (actor, entry_id),
        )
        packs.audit(
            repo,
            conn,
            pack,
            actor,
            "schedule_cancelled",
            {
                "entry_id": entry_id,
                "previous_time": e["scheduled_for"].isoformat(),
                "request_id": payload.request_id,
                "reason": payload.reason,
            },
        )
        return save_receipt(
            conn,
            payload.request_id,
            actor,
            operation,
            data,
            {"calendar_entry_id": entry_id, "status": "cancelled", "revision": e["revision"] + 1},
        )


def listing(repo, start, end, *, status="active", cursor=0, limit=200):
    if not repo.settings.calendar_enabled:
        raise ProductionError("Calendar is not enabled", "calendar_disabled", 503)
    if start.tzinfo is None or end.tzinfo is None or not timedelta(0) < end - start <= timedelta(days=93):
        raise ProductionError("Use an offset-aware date range of at most 93 days", "invalid_range", 422)
    states = ["scheduled", "needs_review"] if status == "active" else ["published"]
    with repo.connection() as conn:
        rows = conn.execute(
            """SELECT * FROM calendar_entries WHERE scheduled_for>=%s AND scheduled_for<%s
            AND status=ANY(%s) ORDER BY scheduled_for,calendar_entry_id LIMIT %s OFFSET %s""",
            (start, end, states, limit + 1, cursor),
        ).fetchall()
        values = [entry_view(repo, conn, e) for e in rows[:limit]]
        return {
            "items": values,
            "next_cursor": cursor + limit if len(rows) > limit else None,
            "from": start,
            "to": end,
            "display_timezone": repo.settings.calendar_timezone,
            "server_time": datetime.now(UTC),
        }
