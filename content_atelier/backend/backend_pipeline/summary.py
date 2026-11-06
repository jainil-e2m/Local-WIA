"""The cycle summary Home shows (plan 6.F2): what is waiting for whom, the latest cycle, the next scheduled one, source health
and the week's spend, in one read.

    GET /storage/summary

Waiting for whom, in the app's own terms: cards at Gate 1, held cards whose date has come (3.B11's reminder) and briefs at
Gate 2 wait for an approver (WIA); packs in review
wait for an editor or an approver to read and mark them ready; a pack still finishing or waiting on a budget or a failed
step waits for the system, with its reason. Source health is the intake connections (6.B1), the extraction health counts
(2.B12) and the open alerts (6.B4). Read only; no model, no outside call.
"""
from __future__ import annotations

from datetime import UTC, datetime

# A weekly limit is close when at most a fifth of it is left (Home says so to an approver, in words, with no figures).
CLOSE_SHARE = 0.2


def waiting(conn) -> dict:
    cards = conn.execute("""SELECT a.week_id,count(*) n FROM content_angles a JOIN weeks w USING (week_id)
        WHERE a.content_body ? 'card' AND w.status<>'archived'
        AND a.approval_status='pending' AND a.selection_status<>'suppressed'
        AND NOT EXISTS (SELECT 1 FROM content_angles b WHERE b.supersedes_id=a.angle_id)
        AND NOT EXISTS (SELECT 1 FROM decisions d WHERE d.item_kind='angle' AND d.item_id=a.angle_id)
        GROUP BY a.week_id ORDER BY a.week_id DESC""").fetchall()
    briefs = conn.execute("""SELECT count(*) n FROM content_briefs b JOIN weeks w USING (week_id)
        WHERE b.approval_status='pending' AND w.status<>'archived'
        AND NOT EXISTS (SELECT 1 FROM content_briefs c WHERE c.supersedes_id=b.brief_id)""").fetchone()["n"]
    from .packs.model import state_of
    packs = {"in_review": 0, "finishing": 0, "waiting": 0, "ready_to_publish": 0}
    reasons = []
    for pack in conn.execute("""SELECT p.* FROM content_packs p JOIN weeks w USING (week_id)
        WHERE p.contract_version='content_pack_v2' AND w.status<>'archived'
        AND NOT EXISTS (SELECT 1 FROM content_packs q WHERE q.supersedes_id=p.pack_id)""").fetchall():
        state, reason = state_of(conn, pack)
        if state in packs:
            packs[state] += 1
        if state == "waiting" and reason:
            reasons.append({"pack_id": pack["pack_id"], "title": pack["title"], "reason": reason})
    # 3.B11's reminder, in the app (no email, the owner, 25 October 2026): a card held until a date that has come is due back
    # at Gate 1, until a later decision on it.
    held = [dict(r) for r in conn.execute("""SELECT a.angle_id,a.week_id,a.content_body->>'title' AS title,d.hold_until
        FROM decisions d JOIN content_angles a ON a.angle_id=d.item_id JOIN weeks w ON w.week_id=a.week_id
        WHERE d.item_kind='angle' AND d.disposition='hold' AND w.status<>'archived'
        AND d.hold_until IS NOT NULL AND d.hold_until<=CURRENT_DATE
        AND NOT EXISTS (SELECT 1 FROM decisions later WHERE later.item_kind='angle' AND later.item_id=d.item_id
                        AND later.created_at>d.created_at)
        ORDER BY d.hold_until""").fetchall()]
    return {"cards_at_gate_1": {"count": sum(r["n"] for r in cards), "by_week": [dict(r) for r in cards], "who": "an approver"},
            "held_cards_due_back": {"count": len(held), "cards": held[:20], "who": "an approver"},
            "briefs_at_gate_2": {"count": briefs, "who": "an approver"},
            "packs_in_review": {"count": packs["in_review"], "who": "an editor or an approver"},
            "packs_ready": packs["ready_to_publish"],
            "packs_with_the_system": {"finishing": packs["finishing"], "waiting": packs["waiting"], "reasons": reasons[:10]}}


def latest_cycle(conn) -> dict | None:
    row = conn.execute("""SELECT r.run_id,r.week_id,r.status,r.created_at,r.trigger_type,r.input_refs->'window' AS window,
        r.input_refs->>'started_from' AS started_from FROM pipeline_runs r WHERE r.run_scope='weekly_angles'
        AND r.input_refs ? 'selected_by' ORDER BY r.created_at DESC LIMIT 1""").fetchone()
    return dict(row) if row else None


def sources(conn) -> dict:
    connections = [dict(r) for r in conn.execute(
        "SELECT connection_id,provider,activated_at,checkpoint,health,error_summary FROM intake_connections ORDER BY 1").fetchall()]
    extraction = {r["extraction_status"]: r["n"] for r in conn.execute("""SELECT extraction_status,count(*) n FROM transcripts
        WHERE included AND canonical_document_id IS NULL GROUP BY 1""").fetchall()}
    return {"connections": connections, "extraction": extraction,
            "collector": "active" if any(c["activated_at"] for c in connections) else "not active: calls are imported by the weekly schedule"}


def summary(conn, now: datetime | None = None) -> dict:
    from .alerts import listing
    from .cycle.schedule import next_run
    from .llm import standing
    now = now or datetime.now(UTC)
    alerts = listing(conn, now=now)
    budgets = standing.status(conn)["budgets"]
    spent = round(sum(b["spent_usd"] for b in budgets), 4)
    capped = [b for b in budgets if b["cap_usd"] is not None]
    limited = [b for b in capped if b["enabled"] and b["cap_usd"] > 0]
    return {"waiting": waiting(conn), "latest_cycle": latest_cycle(conn), "next_cycle": next_run(conn, now),
            "sources": sources(conn), "alerts": {"open": alerts["open"], "errors": sum(a["severity"] == "error" for a in alerts["alerts"])},
            "spend": {"this_week_usd": spent, "caps_usd": round(sum(b["cap_usd"] for b in capped), 2),
                      "left_usd": round(sum(b["left_usd"] for b in capped), 4),
                      # Which weekly limits are reached or close, by their labels, for Home's one line to an approver.
                      "limits_reached": [b["label"] for b in limited if b["left_usd"] <= 0],
                      "limits_close": [b["label"] for b in limited if 0 < b["left_usd"] <= CLOSE_SHARE * b["cap_usd"]]},
            "at": now.isoformat()}


def install(routes, settings, reader, action):
    from fastapi import Depends

    from .api_models import CycleOverview, CycleSchedule, returns
    from .database import connect

    @routes.get("/summary", responses=returns(CycleOverview))
    def cycle_summary(subject: str = Depends(reader)):
        def read():
            with connect(settings.database_url, vectors=False) as conn:
                return summary(conn)
        return action(read)

    @routes.get("/schedule", responses=returns(CycleSchedule))
    def cycle_schedule(subject: str = Depends(reader)):
        def read():
            from .cycle.schedule import next_run
            from .settings_store import cycle_schedule_text
            with connect(settings.database_url, vectors=False) as conn:
                return {**next_run(conn), "text": cycle_schedule_text(conn)}
        return action(read)
