from datetime import datetime
from typing import Annotated, Literal

from fastapi import Depends, Query

from .calendar import service as calendar
from .calendar.contracts import Cancel, Reschedule, Schedule
from .packs import service as packs
from .packs.contracts import Decision, Generate
from .packs.workflow import queue
from .production_common import ProductionError


def install(routes, repo, actor, action):
    def enabled():
        if not repo.settings.packs_enabled:
            raise ProductionError("Pack production is not enabled", "packs_disabled", 503)

    @routes.get("/calendar/config")
    def configuration(subject: str = Depends(actor)):
        return action(calendar.config, repo, subject)

    @routes.get("/calendar")
    def entries(
        from_: Annotated[datetime, Query(alias="from")],
        to: datetime,
        status: Literal["active", "published"] = "active",
        cursor: int = Query(default=0, ge=0, le=1000000),
        subject: str = Depends(actor),
    ):
        return action(calendar.listing, repo, from_, to, status=status, cursor=cursor)

    @routes.get("/packs")
    def pack_list(
        week_id: str | None = None,
        status: Literal["pending", "approved", "rejected"] | None = None,
        limit: int = Query(default=20, ge=1, le=100),
        offset: int = Query(default=0, ge=0, le=1000000),
        subject: str = Depends(actor),
    ):
        action(enabled)
        return action(packs.listing, repo, subject, week_id, status, limit, offset)

    @routes.get("/packs/{pack_id}")
    def pack_detail(pack_id: str, subject: str = Depends(actor)):
        action(enabled)
        return action(packs.detail, repo, pack_id, subject)

    @routes.get("/packs/{pack_id}/production")
    def production(pack_id: str, subject: str = Depends(actor)):
        action(enabled)
        pack = action(packs.detail, repo, pack_id, subject)
        with repo.connection() as conn:
            jobs = conn.execute(
                """SELECT job_id,stage,status,current_message,error_summary,attempt_count,heartbeat_at,
                completed_units,total_units FROM pipeline_jobs WHERE run_id=%s ORDER BY created_at,stage""",
                (pack["production_run_id"],),
            ).fetchall()
        from .store import JsonStore

        store = JsonStore(repo.settings.artifact_root)
        path = f"pack-runs/{pack['production_run_id']}/cost_summary.json"
        return {"jobs": jobs, "costs": store.read_json(path) if store.path(path).is_file() else None}

    @routes.post("/briefs/{brief_id}/pack", status_code=202)
    def generate(brief_id: str, payload: Generate, subject: str = Depends(actor)):
        return action(queue, repo, brief_id, payload, subject)

    @routes.post("/packs/{pack_id}/decision")
    def decide(pack_id: str, payload: Decision, subject: str = Depends(actor)):
        action(enabled)
        return action(packs.decide, repo, pack_id, payload, subject)

    @routes.post("/packs/{pack_id}/schedule")
    def schedule(pack_id: str, payload: Schedule, subject: str = Depends(actor)):
        return action(calendar.schedule, repo, pack_id, payload, subject)

    @routes.patch("/calendar/{entry_id}")
    def move(entry_id: str, payload: Reschedule, subject: str = Depends(actor)):
        return action(calendar.reschedule, repo, entry_id, payload, subject)

    @routes.post("/calendar/{entry_id}/cancel")
    def cancel(entry_id: str, payload: Cancel, subject: str = Depends(actor)):
        return action(calendar.cancel, repo, entry_id, payload, subject)
