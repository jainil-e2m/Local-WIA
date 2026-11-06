"""Reading content packs (NP.B6; the content-packs plan, sections 4.1, 5.6 and 5.7): the detail, the list and the production
view behind `GET /packs/{id}`, `GET /packs` and `GET /packs/{id}/production` (packs/api_v2.py).

- **The detail** (`StoredPackV2`) gives the pieces in tab order (Email, Carousel, Reel 1 to 3), each with its copy, the
  brief's copy, its locks, its findings (the fidelity loop's, stored, and the deterministic checks', recomputed on this read
  with the week's other packs), what the finisher and people changed, and its published marks (read from the published
  register by `pack:<brief_id>:<piece>`). Then the pack's own findings, why it is not ready in plain words (R50), the
  before-publishing notes, the client quotes, the versions, the state and what this person may do.
- **Ready** is blocked only by an open blocking fidelity finding, a blocking deterministic finding, or a piece not written;
  before-publishing notes and client quotes never block it (the owner, 24 October).
- **A pack still finishing** answers with no pieces and its state (finishing, or waiting with the reason).
- **The list** (`PackPageV2`) is the current v2 packs, newest first, filtered by week, state or brief (any version of the
  brief's lineage, so the brief page finds its pack).
"""
from __future__ import annotations

import re

from ..artifacts import store_for
from ..gates.roles import access_for
from ..production_common import ProductionError
from . import checks
from . import contracts_v2 as c2
from . import model

EDITABLE_STATES = ("in_review", "ready_to_publish")
_IDENTIFIER = re.compile(r"\b(?:ev|evidence|passage|moment|claim|transcript|brief|angle|pack|asset|finding|check)_[A-Za-z0-9_]+\b")


def plain(text: str) -> str:
    """A reason as the screen shows it: no identifiers (R50), as Gate 2's plain_blocker."""
    return " ".join(_IDENTIFIER.sub("an earlier item", text or "").split())


def source_ref(brief_id: str, key: str) -> str:
    return f"pack:{brief_id}:{key}"


# What an editorial finding says, in a reader's words (Round 2, check v4; contracts_v2.EDITORIAL_ISSUES).
ISSUE_WORDS = {
    "misleading_implication": "could leave a prospect with the wrong impression",
    "missing_context": "needs context to be read correctly",
    "lead_quality": "could suggest the ads brought poor leads",
    "unsupported_causation": "states a cause the call does not show",
    "generalization": "makes a broad claim the sources do not support",
    "not_for_public": "may not be WIA's or the client's to share",
    "technical_aside": "rests the point on a passing technical remark",
    "agency_comparison": "compares WIA with other agencies",
    "slogan": "reads like a slogan rather than a real explanation",
    "repetition": "repeats wording from another piece",
    "premise_overlap": "repeats another Reel's premise",
    "broad_lesson": "states a general lesson instead of WIA's specific decision",
    "weak_hook": "opens weakly",
    "format_rearranged": "reads like another piece rearranged",
    "weak_takeaway": "leaves the reader little to take away",
    "cta_fit": "has a call to action that does not fit",
}


def fidelity_view(key: str, f: dict, *, can_attest: bool) -> dict:
    """A stored fidelity or editorial finding (contracts_v2.Finding) in the PackFindingV2 shape. An editorial finding names
    its issue; "attest" on it means keeping the line with a reason."""
    if f.get("kind") == "editorial":
        verdict = ISSUE_WORDS.get(f.get("issue") or "", "was flagged by the editorial reading")
        source = "editorial"
    else:
        verdict = "goes beyond what the call supports" if f.get("verdict") == "unsupported" else "hints at something kept out of the copy"
        source = "fidelity"
    message = f'{c2.LABELS[key]}: "{checks.snippet(f.get("sentence"), 120)}" {verdict}' + (f" ({f['why']})" if f.get("why") else "")
    return {"finding_id": f["finding_id"], "source": source, "piece": key, "path": f.get("path"), "sentence": f.get("sentence"),
            "severity": f.get("severity") or "blocking", "message": message, "status": f.get("status") or "open",
            "resolution": f.get("resolution"), "can_attest": can_attest and (f.get("status") or "open") == "open",
            "verdict": f.get("verdict"), "issue": f.get("issue")}


def ready_blockers(bodies, found: list[dict]) -> list[str]:
    """Why the pack cannot be marked ready, in plain words: an open blocking fidelity finding, a blocking deterministic
    finding (a piece not written is one: the composition check), never a before-publishing note or a client quote."""
    out = []
    for key in c2.PIECE_KEYS:
        for f in (bodies.get(key) or {}).get("findings") or []:
            if f.get("status", "open") == "open" and f.get("severity", "blocking") == "blocking":
                if f.get("kind") == "editorial":
                    out.append(f'{c2.LABELS[key]}: "{checks.snippet(f.get("sentence"), 120)}" '
                               f'{ISSUE_WORDS.get(f.get("issue") or "", "was flagged")}. Edit that line, or keep it with a reason')
                    continue
                out.append(f'{c2.LABELS[key]}: "{checks.snippet(f.get("sentence"), 120)}" is not supported by the call. Edit that '
                           "sentence, or attest it is true")
    out += [f["message"] for f in found if f["severity"] == "blocking" and f.get("status", "open") == "open"]
    return list(dict.fromkeys(plain(x) for x in out))


def published_marks(conn, brief_id: str) -> dict[str, list[dict]]:
    """The published marks of a brief's pack pieces, by piece key (PackPublicationV2)."""
    rows = conn.execute("""SELECT content_id,source_ref,channel,published_on,details,created_by,created_at FROM published_content
        WHERE source_kind='approved_brief' AND source_ref LIKE %s ORDER BY created_at,content_id""",
                        (f"pack:{brief_id}:%",)).fetchall()
    out: dict[str, list[dict]] = {}
    for r in rows:
        key = r["source_ref"].rsplit(":", 1)[-1]
        capture = (r["details"] or {}).get("capture") or {}
        out.setdefault(key, []).append({
            "content_id": r["content_id"], "piece": key, "channel": capture.get("platform") or r["channel"],
            "published_on": r["published_on"].isoformat() if hasattr(r["published_on"], "isoformat") else r["published_on"],
            "url": capture.get("url"), "by": capture.get("recorded_by") or r["created_by"],
            "at": r["created_at"].isoformat() if hasattr(r["created_at"], "isoformat") else r["created_at"]})
    return out


def brief_of(conn, pack: dict) -> dict:
    brief = conn.execute("SELECT * FROM content_briefs WHERE brief_id=%s", (pack["source_brief_id"],)).fetchone()
    if not brief:
        raise ProductionError("The pack's brief is missing", "not_found", 404)
    return brief


def _get(conn, pack_id: str) -> dict:
    pack = conn.execute("SELECT * FROM content_packs WHERE pack_id=%s", (pack_id,)).fetchone()
    if not pack:
        raise ProductionError("Pack not found", "not_found", 404)
    return pack


def approval_delegated(conn, pack: dict) -> bool:
    provenance = (pack.get("content_body") or {}).get("provenance") or {}
    if "approval_delegated" in provenance:
        return bool(provenance["approval_delegated"])
    run = conn.execute("SELECT input_refs FROM pipeline_runs WHERE run_id=%s", (pack.get("production_run_id"),)).fetchone()
    return bool(((run or {}).get("input_refs") or {}).get("approval_delegated"))


def detail(repo, pack_id: str, actor, *, conn=None) -> dict:
    """GET /packs/{id} -> StoredPackV2."""
    if conn is None:
        with repo.connection() as c:
            return detail(repo, pack_id, actor, conn=c)
    pack = _get(conn, pack_id)
    if not model.is_v2(pack):
        from .service import detail as v1_detail
        return v1_detail(repo, pack_id, actor, conn=conn)
    state, reason = model.state_of(conn, pack)
    active = model.run_active(conn, pack.get("production_run_id"))
    access = access_for(repo.settings, actor)
    open_to_change = state in EDITABLE_STATES and not active
    body = pack.get("content_body")
    pieces, pack_findings, blockers = [], [], []
    if body is not None:
        brief = brief_of(conn, pack)
        rows = model.pieces(conn, pack_id)
        bodies = checks.bodies_of(rows)
        found = checks.findings(conn, pack, bodies, brief, siblings=checks.week_siblings(conn, pack))
        marks = published_marks(conn, pack["source_brief_id"])
        can_attest = access.can("approve_packs") and open_to_change
        for key in c2.TAB_ORDER:
            row = rows.get(key)
            if not row:
                continue
            piece = bodies[key]
            content = piece.get("content")
            pieces.append({
                "key": key, "channel": piece.get("channel") or c2.CHANNEL[key], "label": piece.get("label") or c2.LABELS[key],
                "kind": (content or {}).get("kind") or c2.KEY_KIND.get(key), "ordinal": c2.ORDINAL[key],
                "origin": piece.get("origin"), "not_written_reason": piece.get("not_written_reason"),
                "brief_key": piece.get("brief_key"), "content": content, "brief_copy": piece.get("brief_copy"),
                "locks": piece.get("locks") or [],
                "findings": [fidelity_view(key, f, can_attest=can_attest) for f in piece.get("findings") or []]
                + [f for f in found if f["piece"] == key],
                "changes": piece.get("changes") or [], "published": marks.get(key, []), "content_hash": row["content_hash"],
                "asset_id": row['asset_id'],
                "schedule": conn.execute("SELECT * FROM calendar_entries WHERE asset_id=%s AND status IN ('scheduled','needs_review')",
                                         (row['asset_id'],)).fetchone(),
                "editable": list(c2.EDITABLE[c2.CHANNEL[key]])})
        pack_findings = [f for f in found if f["piece"] is None or f["piece"] not in rows]
        blockers = ready_blockers(bodies, found)
    body = body or {}
    return {
        "pack_id": pack["pack_id"], "contract_version": c2.VERSION, "title": pack["title"], "week_id": pack["week_id"],
        "source_brief_id": pack["source_brief_id"], "source_brief_hash": pack["source_brief_hash"],
        "angle_id": body.get("angle_id"), "pillar": body.get("pillar"), "rank": body.get("rank"),
        "state": state, "state_reason": reason, "approval_status": pack["approval_status"], "manifest_hash": pack.get("manifest_hash"),
        "approved_by": pack.get("approved_by"), "approved_at": pack.get("approved_at"), "created_at": pack["created_at"],
        "supersedes_id": pack.get("supersedes_id"), "run_id": pack.get("production_run_id"), "run_active": active,
        "pieces": pieces, "findings": pack_findings, "ready_blockers": blockers,
        "before_publishing": body.get("before_publishing") or [], "client_quotes": body.get("client_quotes") or [],
        "stronger_with_permission": body.get("stronger_with_permission") or [], "granted": body.get("granted") or [],
        "pack_notes": body.get("pack_notes") or [], "creative_choices": body.get("creative_choices") or [],
        "change_notes": body.get("change_notes") or [], "fidelity": body.get("fidelity"), "provenance": body.get("provenance"),
        "change": body.get("change"), "versions": model.versions(conn, pack_id), "approval_delegated": approval_delegated(conn, pack),
        "can_edit": access.can("edit_packs") and open_to_change,
        "can_decide": access.can("approve_packs") and open_to_change,
        "can_finish_again": access.can("approve_packs") and open_to_change,
        "can_mark_published": access.can("edit_packs") and open_to_change,
        # Built on material removed at a client's request (6.B12): its blocking finding is among the pack's findings.
        "removed_material": removal_mark(conn, pack)}


def removal_mark(conn, pack: dict) -> dict | None:
    from ..removal import mark_of
    return mark_of(conn, "brief", pack.get("source_brief_id")) or mark_of(conn, "pack", pack["pack_id"])


def lineage(conn, brief_id: str) -> list[str]:
    """Every version of a brief's lineage: from its first version, every version after it."""
    root, seen = brief_id, {brief_id}
    while True:
        row = conn.execute("SELECT supersedes_id FROM content_briefs WHERE brief_id=%s", (root,)).fetchone()
        if not row or not row["supersedes_id"] or row["supersedes_id"] in seen:
            break
        root = row["supersedes_id"]
        seen.add(root)
    rows = conn.execute("""WITH RECURSIVE chain AS (SELECT brief_id FROM content_briefs WHERE brief_id=%s
        UNION SELECT b.brief_id FROM content_briefs b JOIN chain c ON b.supersedes_id=c.brief_id) SELECT brief_id FROM chain""",
                        (root,)).fetchall()
    return sorted({r["brief_id"] for r in rows} | seen)


def _open_findings(rows: dict, pack: dict) -> int:
    stored = [f for r in rows.values() for f in (r.get("content_body") or {}).get("findings") or []
              if f.get("status", "open") == "open" and f.get("severity", "blocking") == "blocking"]
    checked = [f for f in (pack.get("validation_result") or {}).get("findings") or [] if f.get("severity") == "blocking"]
    return len(stored) + len(checked)


def _open_notes(body: dict) -> int:
    return (sum(1 for n in body.get("before_publishing") or [] if not n.get("done"))
            + sum(1 for q in body.get("client_quotes") or [] if not q.get("cleared")))


def summary(conn, pack: dict, state: str, reason: str | None) -> dict:
    body = pack.get("content_body") or {}
    rows = model.pieces(conn, pack["pack_id"])
    marks = published_marks(conn, pack["source_brief_id"]) if rows else {}
    return {"pack_id": pack["pack_id"], "title": pack["title"], "week_id": pack["week_id"], "source_brief_id": pack["source_brief_id"],
            "state": state, "state_reason": reason, "approval_status": pack["approval_status"], "manifest_hash": pack.get("manifest_hash"),
            "created_at": pack["created_at"], "pillar": body.get("pillar"), "rank": body.get("rank"),
            "pieces": [{"key": key, "label": c2.LABELS[key], "kind": ((rows[key]["content_body"] or {}).get("content") or {}).get("kind")
                        or c2.KEY_KIND.get(key), "origin": (rows[key]["content_body"] or {}).get("origin"), "published": bool(marks.get(key))}
                       for key in c2.TAB_ORDER if key in rows],
            "open_findings": _open_findings(rows, pack), "open_notes": _open_notes(body)}


def listing(repo, actor, week_id=None, state=None, limit=20, offset=0, *, brief_id=None) -> dict:
    """GET /packs -> PackPageV2: the current v2 packs, newest first. The state is derived, so it filters after reading."""
    with repo.connection() as conn:
        briefs = lineage(conn, brief_id) if brief_id else None
        rows = conn.execute("""SELECT * FROM content_packs p WHERE p.contract_version=%s AND (%s::text IS NULL OR p.week_id=%s)
            AND (%s::text[] IS NULL OR p.source_brief_id=ANY(%s::text[]))
            AND NOT EXISTS (SELECT 1 FROM content_packs n WHERE n.supersedes_id=p.pack_id)
            ORDER BY p.created_at DESC,p.pack_id""", (c2.VERSION, week_id, week_id, briefs, briefs)).fetchall()
        items = []
        for pack in rows:
            found, reason = model.state_of(conn, pack)
            if state and not (found in EDITABLE_STATES if state == "generated" else found == state):
                continue
            items.append((pack, found, reason))
        page = [summary(conn, pack, found, reason) for pack, found, reason in items[offset:offset + limit]]
    return {"items": page, "total": len(items)}


def production(repo, pack_id: str, actor) -> dict:
    """GET /packs/{id}/production -> PackProductionV2: the run's jobs, its costs and why it waits."""
    with repo.connection() as conn:
        pack = _get(conn, pack_id)
        if not model.is_v2(pack):
            raise ProductionError("This is a version 1 pack; its production view is the v1 one", "pack_v1", 409)
        state, reason = model.state_of(conn, pack)
        # One transaction writes the six jobs with one timestamp: they are shown in the order they run.
        order = {stage: n for n, stage in enumerate(c2.ALL_STAGES)}
        jobs = sorted(model.run_jobs(conn, pack.get("production_run_id")), key=lambda j: order.get(j["stage"], len(order)))
    for job in jobs:
        details = job.pop("progress_details", None) or {}
        if job["status"] == "waiting" and details.get("budget_reason"):
            job["waiting_reason"] = details["budget_reason"]
    store = store_for(repo.settings)
    path = f"pack-runs/{pack.get('production_run_id')}/cost_summary.json"
    return {"run_id": pack.get("production_run_id"), "state": state, "state_reason": reason, "jobs": jobs,
            "costs": store.read_json(path) if pack.get("production_run_id") and store.exists(path) else None}
