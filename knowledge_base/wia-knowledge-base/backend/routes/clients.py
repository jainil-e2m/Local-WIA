"""Client read endpoints for the KB frontend (S11 slice). The first one feeds the client record's Leads tab.

Locally they are open; anywhere else they sit behind the shared team password (routes/access.py). Per-client
visibility comes with named sign-in (S10).
"""
import re
from datetime import date
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy.exc import OperationalError

from backend.db import SessionFactory, transaction
from backend.routes.access import actor, require_team
from backend.services.clients import mapping, meeting_links
from backend.services.read_models import leads

router = APIRouter()


class NewClient(BaseModel):
    name: str


def slug_for(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:80] or "client"


@router.post("", status_code=201)
def create_client(body: NewClient) -> dict:
    """Add a client (S2: an admin adds a client and maps it on the spot). Adding queues discovery for it."""
    require_team()
    name = " ".join(body.name.split())
    if not 2 <= len(name) <= 200:
        raise HTTPException(status_code=400, detail={"code": "refused", "message": "a client name needs 2–200 characters"})
    try:
        with transaction() as s:
            business = mapping.create_client(s, name=name, slug=slug_for(name), actor=actor())
            return {"slug": business.slug, "name": business.name, "status": business.status, "revision": business.revision}
    except mapping.MappingError as error:
        raise HTTPException(status_code=400, detail={"code": "refused", "message": str(error)}) from None
    except OperationalError:
        raise HTTPException(status_code=503, detail={"code": "database_unavailable"}) from None


@router.get("/{slug}/leads")
def client_leads(slug: str, period: str = "90d", start: date | None = None, end: date | None = None) -> dict:
    """`period` picks a preset ending now; `start` and `end` (YYYY-MM-DD, inclusive) pick a custom range instead."""
    require_team()
    custom = start is not None or end is not None
    if not custom and period not in leads.PERIODS:
        raise HTTPException(status_code=400, detail={"code": "bad_period", "allowed": list(leads.PERIODS)})
    try:
        with SessionFactory() as s:
            return leads.client_leads(s, slug, period, start_date=start, end_date=end)
    except ValueError as error:
        raise HTTPException(status_code=400, detail={"code": "bad_range", "message": str(error)}) from None
    except leads.UnknownClient:
        raise HTTPException(status_code=404, detail={"code": "unknown_client"}) from None
    except OperationalError:
        # Locally this means Postgres is down (Docker Desktop stopped); say so instead of a bare 500.
        raise HTTPException(status_code=503, detail={"code": "database_unavailable"}) from None


class MeetingLinkBody(BaseModel):
    url: str


def _meeting_link(fn):
    require_team()
    try:
        with transaction() as s:
            return fn(s)
    except mapping.MappingError as error:
        raise HTTPException(status_code=400, detail={"code": "refused", "message": str(error)}) from None
    except OperationalError:
        raise HTTPException(status_code=503, detail={"code": "database_unavailable"}) from None


@router.put("/{slug}/meetings/{record_id}/link")
def set_meeting_link(slug: str, record_id: UUID, body: MeetingLinkBody) -> dict:
    """Add or replace the recording link of a past meeting that has none in the sources."""
    return _meeting_link(lambda s: meeting_links.set_link(s, slug, record_id, body.url, actor=actor()))


@router.delete("/{slug}/meetings/{record_id}/link")
def clear_meeting_link(slug: str, record_id: UUID) -> dict:
    return _meeting_link(lambda s: meeting_links.clear_link(s, slug, record_id, actor=actor()))
