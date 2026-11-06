from .artifacts import store_for
from .api_models import (CalendarConfig, CalendarPage, PackPageV2, PackProductionV2, PackPublishedV2, PackQueuedV2, PackSavedV2,
                         StoredPackV2, WeekPackPlanV2, returns)
from datetime import datetime
from typing import Annotated, Literal

from fastapi import Depends, Query, Response

from .calendar import service as calendar
from .calendar.contracts import Cancel, Reschedule, Schedule
from .packs import api_v2 as packs_v2
from .packs import service as packs
from .packs.contracts import Decision
from .packs.document_docx import MEDIA_TYPE as DOCX
from .packs.contracts_v2 import (VERSION, PackAttest, PackClearance, PackCreate, PackEdit, PackFinishAgain, PackMarkPublished,
                                 PackDecisionV2, PackRecordedTake, PackRefinish, PackRevert)
from .production_common import ProductionError

PieceKey = Literal["email", "carousel", "reel_1", "reel_2", "reel_3"]


def install(routes, repo, decider, reader, action):
    def enabled():
        if not repo.settings.packs_enabled:
            raise ProductionError("Pack production is not enabled", "packs_disabled", 503)

    def version_of(pack_id):
        with repo.connection() as conn:
            row = conn.execute("SELECT contract_version FROM content_packs WHERE pack_id=%s", (pack_id,)).fetchone()
        if not row:
            raise ProductionError("Pack not found", "not_found", 404)
        return row["contract_version"]

    @routes.get("/calendar/config", responses=returns(CalendarConfig))
    def configuration(subject: str = Depends(reader)):
        return action(calendar.config, repo, subject)

    @routes.get("/calendar", responses=returns(CalendarPage))
    def entries(
        from_: Annotated[datetime, Query(alias="from")],
        to: datetime,
        status: Literal["active", "published", "all"] = "active",
        cursor: int = Query(default=0, ge=0, le=1000000),
        subject: str = Depends(reader),
    ):
        return action(calendar.listing, repo, from_, to, status=status, cursor=cursor)

    # Content packs, contract v2 (Phase NP; the content-packs plan, section 5.6). A v1 pack stays readable through the
    # old service (packs/service.py); every new pack is v2.
    @routes.get("/packs", responses=returns(PackPageV2))
    def pack_list(
        week_id: str | None = None,
        brief_id: str | None = None,
        state: Literal["finishing", "waiting", "in_review", "ready_to_publish", "generated"] | None = None,
        limit: int = Query(default=20, ge=1, le=100),
        offset: int = Query(default=0, ge=0, le=1000000),
        subject: str = Depends(reader),
    ):
        action(enabled)
        return action(packs_v2.listing, repo, subject, week_id, state, limit, offset, brief_id=brief_id)

    @routes.get("/packs/{pack_id}", responses=returns(StoredPackV2))
    def pack_detail(pack_id: str, subject: str = Depends(reader)):
        action(enabled)
        if action(version_of, pack_id) != VERSION:
            return action(packs.detail, repo, pack_id, subject)
        return action(packs_v2.detail, repo, pack_id, subject)

    @routes.get("/packs/{pack_id}/production", responses=returns(PackProductionV2))
    def production(pack_id: str, subject: str = Depends(reader)):
        action(enabled)
        if action(version_of, pack_id) == VERSION:
            return action(packs_v2.production, repo, pack_id, subject)
        pack = action(packs.detail, repo, pack_id, subject)
        with repo.connection() as conn:
            jobs = conn.execute(
                """SELECT job_id,stage,status,current_message,error_summary,attempt_count,heartbeat_at,
                completed_units,total_units FROM pipeline_jobs WHERE run_id=%s ORDER BY created_at,stage""",
                (pack["production_run_id"],),
            ).fetchall()

        store = store_for(repo.settings)
        path = f"pack-runs/{pack['production_run_id']}/cost_summary.json"
        return {"jobs": jobs, "costs": store.read_json(path) if store.exists(path) else None}

    @routes.post("/briefs/{brief_id}/pack", status_code=202, responses=returns(PackQueuedV2, 202))
    def generate(brief_id: str, payload: PackCreate, subject: str = Depends(decider)):
        action(enabled)
        return action(packs_v2.create, repo, brief_id, payload, subject)

    @routes.patch("/packs/{pack_id}/pieces/{key}", responses=returns(PackSavedV2))
    def edit_piece(pack_id: str, key: PieceKey, payload: PackEdit, subject: str = Depends(decider)):
        action(enabled)
        return action(packs_v2.edit, repo, pack_id, key, payload, subject)

    @routes.post("/packs/{pack_id}/pieces/{key}/revert", responses=returns(PackSavedV2))
    def revert_piece(pack_id: str, key: PieceKey, payload: PackRevert, subject: str = Depends(decider)):
        action(enabled)
        return action(packs_v2.revert, repo, pack_id, key, payload, subject)

    @routes.post("/packs/{pack_id}/clearances", responses=returns(PackSavedV2))
    def clear(pack_id: str, payload: PackClearance, subject: str = Depends(decider)):
        action(enabled)
        return action(packs_v2.clearance, repo, pack_id, payload, subject)

    @routes.post("/packs/{pack_id}/findings/{finding_id}/attest", responses=returns(PackSavedV2))
    def attest(pack_id: str, finding_id: str, payload: PackAttest, subject: str = Depends(decider)):
        action(enabled)
        return action(packs_v2.attest, repo, pack_id, finding_id, payload, subject)

    @routes.post("/packs/{pack_id}/finish", status_code=202, responses=returns(PackSavedV2, 202))
    def finish_again(pack_id: str, payload: PackFinishAgain, subject: str = Depends(decider)):
        action(enabled)
        return action(packs_v2.finish_again, repo, pack_id, payload, subject)

    # NP-7's person-started passes: the post-recording pass (NP.B14) and finishing again with a permission (NP.B15).
    @routes.post("/packs/{pack_id}/pieces/{key}/recorded", status_code=202, responses=returns(PackSavedV2, 202))
    def recorded_take(pack_id: str, key: PieceKey, payload: PackRecordedTake, subject: str = Depends(decider)):
        action(enabled)
        return action(packs_v2.recorded_take, repo, pack_id, key, payload, subject)

    @routes.post("/packs/{pack_id}/refinish", status_code=202, responses=returns(PackSavedV2, 202))
    def refinish(pack_id: str, payload: PackRefinish, subject: str = Depends(decider)):
        action(enabled)
        return action(packs_v2.refinish, repo, pack_id, payload, subject)

    @routes.post("/packs/{pack_id}/decision", responses=returns(PackSavedV2))
    def decide(pack_id: str, payload: PackDecisionV2 | Decision, subject: str = Depends(decider)):
        action(enabled)
        if isinstance(payload, Decision):
            return action(packs.decide, repo, pack_id, payload, subject)
        return action(packs_v2.decide, repo, pack_id, payload, subject)

    @routes.post("/packs/{pack_id}/pieces/{key}/published", responses=returns(PackPublishedV2))
    def mark_published(pack_id: str, key: PieceKey, payload: PackMarkPublished, subject: str = Depends(decider)):
        action(enabled)
        return action(packs_v2.published, repo, pack_id, key, payload, subject)

    @routes.get("/weeks/{week_id}/pack-plan", responses=returns(WeekPackPlanV2))
    def week_plan(week_id: str, subject: str = Depends(reader)):
        action(enabled)
        return action(packs_v2.week_plan, repo, week_id, subject)

    @routes.get("/weeks/{week_id}/packs.md")
    def week_document(week_id: str, subject: str = Depends(reader)):
        action(enabled)
        text = action(packs_v2.week_document, repo, week_id, subject)
        return Response(text, media_type="text/markdown",
                        headers={"Content-Disposition": f'attachment; filename="content-atelier-packs-{week_id}.md"'})

    @routes.get("/weeks/{week_id}/packs.docx")
    def week_document_docx(week_id: str, subject: str = Depends(reader)):
        action(enabled)
        data = action(packs_v2.week_document_docx, repo, week_id, subject)
        return Response(data, media_type=DOCX,
                        headers={"Content-Disposition": f'attachment; filename="content-atelier-packs-{week_id}.docx"'})

    @routes.post("/packs/{pack_id}/schedule")
    def schedule(pack_id: str, payload: Schedule, subject: str = Depends(decider)):
        return action(calendar.schedule, repo, pack_id, payload, subject)

    @routes.patch("/calendar/{entry_id}")
    def move(entry_id: str, payload: Reschedule, subject: str = Depends(decider)):
        return action(calendar.reschedule, repo, entry_id, payload, subject)

    @routes.post("/calendar/{entry_id}/cancel")
    def cancel(entry_id: str, payload: Cancel, subject: str = Depends(decider)):
        return action(calendar.cancel, repo, entry_id, payload, subject)
