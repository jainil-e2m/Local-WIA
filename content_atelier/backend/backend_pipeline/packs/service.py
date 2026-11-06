from ..briefs import gate_two
from ..gates.roles import access_for
from ..production_common import ProductionError, receipt, save_receipt
from ..repository import identifier, insert
from ..store import canonical_hash
from .contracts import SLOTS, VERSION, schema


def authorize(repo, actor, action="edit"):
    if not access_for(repo.settings, actor).can("approve_packs" if action == "approve" else "edit_packs"):
        raise PermissionError("Configured pack capability is required")


def assets(conn, pack_id):
    return conn.execute("SELECT * FROM content_assets WHERE pack_id=%s ORDER BY ordinal,asset_id", (pack_id,)).fetchall()


def manifest(pack, rows):
    return canonical_hash(
        {
            "version": VERSION,
            "brief_id": pack["source_brief_id"],
            "brief_hash": pack["source_brief_hash"],
            "assets": [
                {
                    "id": a["asset_id"],
                    "slot": a["slot_key"],
                    "type": a["asset_type"],
                    "ordinal": a["ordinal"],
                    "hash": a["content_hash"],
                }
                for a in rows
            ],
            "validation": pack["validation_result"],
        }
    )


def blockers(repo, conn, pack, rows, *, approved=False, editorial=False):
    from . import model
    if model.is_v2(pack):
        return calendar_blockers_v2(conn, pack, rows, approved=approved, editorial=editorial)
    reasons = []
    if pack.get("contract_version") != VERSION:
        return ["Pack has no verified production provenance"]
    brief = conn.execute("SELECT * FROM content_briefs WHERE brief_id=%s", (pack["source_brief_id"],)).fetchone()
    if not brief or brief["approval_status"] != "approved" or brief["approved_hash"] != pack["source_brief_hash"]:
        reasons.append("Governing brief approval has changed")
    elif gate_two.blockers(conn, brief):
        reasons.append("Governing brief has unresolved review requirements")
    if conn.execute("SELECT 1 FROM content_packs WHERE supersedes_id=%s", (pack["pack_id"],)).fetchone():
        reasons.append("A replacement pack exists")
    if tuple(a["slot_key"] for a in rows) != SLOTS:
        reasons.append("The pack must contain email, carousel and three reels")
    for a in rows:
        if a["brief_id"] != pack["source_brief_id"] or a["brief_input_hash"] != pack["source_brief_hash"]:
            reasons.append("Asset brief lineage differs from the manifest")
        if not a["content_body"] or canonical_hash(a["content_body"]) != a["content_hash"]:
            reasons.append("Asset copy is missing or its hash changed")
        else:
            try:
                schema(a["slot_key"]).model_validate(a["content_body"]["document"])
            except (ValueError, KeyError):
                reasons.append("Stored asset contract is invalid")
    if not (pack.get("validation_result") or {}).get("passed"):
        reasons.append("Production validation has not passed")
    if not pack["manifest_hash"] or pack["manifest_hash"] != manifest(pack, rows):
        reasons.append("Pack manifest is not current")
    if approved and (
        pack["approval_status"] != "approved"
        or pack["approved_hash"] != pack["manifest_hash"]
        or not pack["approved_by"]
        or not pack["approved_at"]
    ):
        reasons.append("Approve this exact pack before scheduling")
    return list(dict.fromkeys(reasons))


def calendar_blockers_v2(conn, pack, rows, *, approved, editorial=False):
    """Planning validity, editorial attention and legacy pack approval are independent checks."""
    from . import checks, model, views
    from . import contracts_v2 as c2
    reasons = []
    brief = views.brief_of(conn, pack)
    if brief['approval_status'] != 'approved' or brief.get('approved_hash') != pack['source_brief_hash']:
        reasons.append('Governing brief approval has changed')
    if model.superseded(conn, pack['pack_id']):
        reasons.append('A replacement pack exists')
    if model.run_active(conn, pack.get('production_run_id')):
        reasons.append('The pack is still being written')
    if {a['slot_key'] for a in rows} != set(c2.PIECE_KEYS):
        reasons.append('The pack must contain email, carousel and three reels')
    for a in rows:
        if not a['content_body'] or canonical_hash(a['content_body']) != a['content_hash']:
            reasons.append('Asset copy is missing or its hash changed')
        if a['brief_id'] != pack['source_brief_id'] or a['brief_input_hash'] != pack['source_brief_hash']:
            reasons.append('Asset brief lineage differs from the manifest')
    if not pack.get('content_body') or not pack.get('manifest_hash') or model.manifest(pack, rows) != pack['manifest_hash']:
        reasons.append('Pack manifest is not current')
    if not reasons and (approved or editorial):
        bodies = checks.bodies_of({a['slot_key']: a for a in rows})
        found = checks.findings(conn, pack, bodies, brief, siblings=checks.week_siblings(conn, pack))
        reasons.extend(views.ready_blockers(bodies, found))
    if approved and (pack['approval_status'] != 'approved' or pack.get('approved_hash') != pack.get('manifest_hash')
                     or not pack.get('approved_by') or not pack.get('approved_at')):
        reasons.append('This pack is scheduled but has not been marked ready to publish')
    return list(dict.fromkeys(reasons))


def locked(repo, conn, pack_id):
    head = conn.execute("SELECT source_brief_id FROM content_packs WHERE pack_id=%s", (pack_id,)).fetchone()
    if not head:
        raise ProductionError("Pack not found", "not_found", 404)
    # Every pack mutation locks governing brief, then pack, then assets in stable order.
    conn.execute("SELECT brief_id FROM content_briefs WHERE brief_id=%s FOR UPDATE", (head["source_brief_id"],))
    pack = conn.execute("SELECT * FROM content_packs WHERE pack_id=%s FOR UPDATE", (pack_id,)).fetchone()
    rows = conn.execute(
        "SELECT * FROM content_assets WHERE pack_id=%s ORDER BY ordinal,asset_id FOR UPDATE", (pack_id,)
    ).fetchall()
    return pack, rows


def detail(repo, pack_id, actor, *, conn=None):
    if conn is None:
        with repo.connection() as c:
            return detail(repo, pack_id, actor, conn=c)
    pack = conn.execute("SELECT * FROM content_packs WHERE pack_id=%s", (pack_id,)).fetchone()
    if not pack:
        raise ProductionError("Pack not found", "not_found", 404)
    rows = assets(conn, pack_id)
    reasons = blockers(repo, conn, pack, rows)
    scheduling = blockers(repo, conn, pack, rows, approved=True)
    access = access_for(repo.settings, actor)
    for row in rows:
        row["schedule"] = conn.execute(
            """SELECT * FROM calendar_entries WHERE asset_id=%s
            AND status IN ('scheduled','needs_review') ORDER BY calendar_entry_id""",
            (row["asset_id"],),
        ).fetchall()
    return {
        **pack,
        "assets": rows,
        "blockers": reasons,
        "schedule_blockers": scheduling,
        "can_approve": not reasons and pack["approval_status"] == "pending" and access.can("approve_packs"),
        "can_schedule": repo.settings.calendar_enabled and not scheduling and access.can("schedule"),
        "can_generate": access.can("edit_packs"),
    }


def listing(repo, actor, week_id=None, status=None, limit=20, offset=0):
    with repo.connection() as conn:
        where = """WHERE (%s::text IS NULL OR week_id=%s) AND (%s::text IS NULL OR approval_status=%s)
          AND NOT EXISTS (SELECT 1 FROM content_packs n WHERE n.supersedes_id=content_packs.pack_id)"""
        params = (week_id, week_id, status, status)
        total = conn.execute("SELECT count(*) n FROM content_packs " + where, params).fetchone()["n"]
        ids = conn.execute(
            "SELECT pack_id FROM content_packs " + where + " ORDER BY created_at DESC,pack_id LIMIT %s OFFSET %s",
            (*params, limit, offset),
        ).fetchall()
        items = [detail(repo, p["pack_id"], actor, conn=conn) for p in ids]
        for item in items:
            for asset in item["assets"]:
                if asset["content_body"]:
                    asset["content_body"] = {
                        "document": {"title": (asset["content_body"].get("document") or {}).get("title", asset["slot_key"])}
                    }
        return {"items": items, "total": total}


def decide(repo, pack_id, payload, actor):
    authorize(repo, actor, "approve")
    data = payload.model_dump(mode="json")
    operation = "pack-decision:" + pack_id
    with repo.connection() as conn:
        saved = receipt(conn, payload.request_id, actor, operation, data)
        if saved is not None:
            return saved
        pack, rows = locked(repo, conn, pack_id)
        if pack["manifest_hash"] != payload.expected_manifest_hash or pack["approval_status"] != "pending":
            raise ProductionError("Pack changed or was already decided; refresh", "stale_pack")
        reasons = blockers(repo, conn, pack, rows)
        if payload.decision == "approved" and reasons:
            raise ProductionError("; ".join(reasons), "pack_blocked")
        if payload.decision == "rejected" and not (payload.note or "").strip():
            raise ProductionError("Rejection needs a reason")
        conn.execute(
            """UPDATE content_packs SET approval_status=%s,approved_hash=%s,approved_by=%s,
            approved_at=CASE WHEN %s='approved' THEN now() ELSE NULL END,review_note=%s,updated_at=now()
            WHERE pack_id=%s""",
            (
                payload.decision,
                pack["manifest_hash"] if payload.decision == "approved" else None,
                actor if payload.decision == "approved" else None,
                payload.decision,
                payload.note,
                pack_id,
            ),
        )
        repo.event(
            conn,
            pack["production_run_id"],
            "pack_" + payload.decision,
            "Pack decision recorded",
            details={
                "actor": actor,
                "manifest_hash": payload.expected_manifest_hash,
                "note": payload.note,
                "request_id": payload.request_id,
            },
        )
        return save_receipt(
            conn, payload.request_id, actor, operation, data, {"pack_id": pack_id, "approval_status": payload.decision}
        )


def audit(repo, conn, pack, actor, kind, details):
    run_id = identifier("schedule_run")
    insert(
        conn,
        "pipeline_runs",
        {
            "run_id": run_id,
            "week_id": pack["week_id"],
            "run_scope": "scheduling",
            "status": "completed",
            "trigger_type": "manual",
            "triggered_by": actor,
            "input_refs": details,
        },
    )
    conn.execute("UPDATE pipeline_runs SET finished_at=now() WHERE run_id=%s", (run_id,))
    repo.event(conn, run_id, kind, kind.replace("_", " "), details={**details, "actor": actor})
