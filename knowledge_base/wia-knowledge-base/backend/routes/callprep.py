"""Call preparation API: correct a call, read and rebuild its brief versions, edit the call-type skills, and map
ad accounts to clients. Team-only (routes/access.py); every write rebuilds the portfolio.

The viewer's name comes from the app's "viewing as" choice: self-declared until named sign-in (decision D7), and
recorded beside the shared actor, as the action approvals do.
"""
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from backend.config import get_settings
from backend.db import transaction
from backend.models.db import AdAccount, Business, CallBrief
from backend.routes.access import actor, current_user, require_team
from backend.services import ads
from backend.services.ai import runner
from backend.services.callprep import briefs, facts, present, registry, skill_files
from backend.services.read_models import portfolio
from backend.services.shared.hashing import sha256_text
from backend.workers import queue

router = APIRouter()


def _who(viewer: str | None) -> str:
    """Signed in through Command Center: that person, whatever the app sends."""
    return actor() if current_user.get() or not viewer else f"{viewer} · {actor()}"


def _record(call_id: str) -> UUID:
    try:
        return registry.record_id_of(call_id)
    except ValueError:
        raise HTTPException(status_code=404, detail={"code": "unknown_call"}) from None


class OverrideBody(BaseModel):
    call_type: str | None = None
    client: str | None = None
    host: str | None = Field(default=None, max_length=200)
    excluded: bool | None = None
    note: str | None = Field(default=None, max_length=500)
    viewer: str | None = Field(default=None, max_length=100)


@router.put("/calls/{call_id}/override")
def set_override(call_id: str, body: OverrideBody) -> dict:
    require_team()
    record_id = _record(call_id)
    with transaction() as s:
        if registry.get(s, record_id) is None:
            raise HTTPException(status_code=404, detail={"code": "unknown_call"})
        try:
            registry.set_override(s, record_id, actor=_who(body.viewer), call_type=body.call_type, client_slug=body.client,
                                  host=body.host, excluded=body.excluded, note=body.note)
        except ValueError as error:
            raise HTTPException(status_code=400, detail={"code": "refused", "message": str(error)}) from None
        portfolio.request_refresh(s)
    return {"ok": True}


@router.delete("/calls/{call_id}/override")
def clear_override(call_id: str) -> dict:
    require_team()
    with transaction() as s:
        registry.set_override(s, _record(call_id), actor=actor(), clear=True)
        portfolio.request_refresh(s)
    return {"ok": True}


@router.get("/calls/{call_id}/briefs")
def brief_versions(call_id: str) -> dict:
    """Every version, each as the screen's Brief, with the facts as they are now (asks and limits are live)."""
    require_team()
    record_id = _record(call_id)
    with transaction() as s:
        call = registry.get(s, record_id)
        if call is None:
            raise HTTPException(status_code=404, detail={"code": "unknown_call"})
        live = facts.compute(s, call, present.packs.payload(s))
        skills = skill_files.load_all(s)
        rows = briefs.history(s, record_id)
        return {"versions": [{**present.version_row(r, skills), **({"brief": present.brief(r, live)} if r.output else {})}
                             for r in rows]}


class RebuildBody(BaseModel):
    instructions: str | None = Field(default=None, max_length=500)
    viewer: str | None = Field(default=None, max_length=100)


@router.post("/calls/{call_id}/briefs", status_code=202)
def rebuild(call_id: str, body: RebuildBody) -> dict:
    """Queue a new version now: with instructions (regenerate) or without (rebuild after changes)."""
    require_team()
    settings = get_settings()
    if settings.ai_mode != "live":
        raise HTTPException(status_code=409, detail={"code": "ai_off", "message": "The AI is switched off, so brief text can't be built. The facts on the page are current."})
    record_id = _record(call_id)
    with transaction() as s:
        call = registry.get(s, record_id)
        if call is None or call.cancelled or call.excluded:
            raise HTTPException(status_code=409, detail={"code": "not_applicable", "message": "This call is cancelled or set aside."})
        latest = s.execute(select(CallBrief.version).where(CallBrief.record_id == record_id)
                           .order_by(CallBrief.version.desc()).limit(1)).scalar_one_or_none() or 0
        instructions = (body.instructions or "").strip()
        queue.enqueue(s, runner.JOB, "analysis", f"ai:call_brief:{record_id}:regenerate:{latest}:{sha256_text(instructions)[:10]}",
                      {"skill": "call_brief", "subject_id": str(record_id),
                       "options": {"trigger": "regenerate", "built_by": _who(body.viewer), "instructions": instructions}})
    return {"queued": True, "after_version": latest}


@router.get("/call-skills")
def list_skills() -> dict:
    require_team()
    with transaction() as s:
        return {"skills": [skill_files.present(k) for k in skill_files.load_all(s).values()]}


@router.get("/call-skills/{key}/versions")
def skill_versions(key: str) -> dict:
    require_team()
    with transaction() as s:
        return {"versions": skill_files.versions(s, key)}


class SkillBody(BaseModel):
    text: str = Field(min_length=20, max_length=20000)
    note: str | None = Field(default=None, max_length=300)
    viewer: str | None = Field(default=None, max_length=100)


@router.post("/call-skills/{key}")
def save_skill(key: str, body: SkillBody) -> dict:
    require_team()
    with transaction() as s:
        try:
            row = skill_files.save(s, key, body.text, by=_who(body.viewer), note=body.note)
        except skill_files.SkillError as error:
            raise HTTPException(status_code=422, detail={"code": "bad_skill", "message": str(error)}) from None
        portfolio.request_refresh(s)
        return {"key": key, "version": row.version}


class RevertBody(BaseModel):
    viewer: str | None = Field(default=None, max_length=100)


@router.post("/call-skills/{key}/revert/{version}")
def revert_skill(key: str, version: int, body: RevertBody) -> dict:
    require_team()
    with transaction() as s:
        try:
            row = skill_files.revert(s, key, version, by=_who(body.viewer))
        except skill_files.SkillError as error:
            raise HTTPException(status_code=404, detail={"code": "unknown_version", "message": str(error)}) from None
        portfolio.request_refresh(s)
        return {"key": key, "version": row.version}


@router.get("/ads/accounts")
def ad_accounts() -> dict:
    require_team()
    with transaction() as s:
        slugs = dict(s.execute(select(Business.id, Business.slug)).all())
        rows = s.execute(select(AdAccount).order_by(AdAccount.provider, AdAccount.name)).scalars().all()
        return {"status": ads.status(s), "accounts": [
            {"provider": a.provider, "account": a.account_id, "name": a.name, "currency": a.currency, "status": a.status,
             "via": a.via, "client": slugs.get(a.business_id), "suggested": None if a.business_id else ads.suggest_client(s, a.name),
             "lastPulled": a.last_pulled_at.isoformat() if a.last_pulled_at else None, "error": a.last_error} for a in rows]}


class MapBody(BaseModel):
    client: str | None = None
    viewer: str | None = Field(default=None, max_length=100)


@router.put("/ads/accounts/{provider}/{account_id}")
def map_ad_account(provider: str, account_id: str, body: MapBody) -> dict:
    require_team()
    with transaction() as s:
        try:
            ads.map_account(s, provider, account_id, body.client, actor=_who(body.viewer))
        except ValueError as error:
            raise HTTPException(status_code=400, detail={"code": "refused", "message": str(error)}) from None
        if body.client:
            queue.enqueue(s, ads.JOB, "maintenance", f"ads:map:{provider}:{account_id}:{body.client}", {})
        portfolio.request_refresh(s)
    return {"ok": True}
