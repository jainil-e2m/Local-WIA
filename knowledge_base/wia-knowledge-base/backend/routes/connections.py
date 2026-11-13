"""Connections endpoints (S11 slice): LeadLock sub-account ↔ client mapping for the Connections screen and a
client's Accounts & sources tab. Both call `services.clients.connections`, which calls the S2 mapping commands.

Locally they are open; anywhere else they sit behind the shared team password (routes/access.py) until named
sign-in (S10) records each admin as the actor.
"""
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy.exc import OperationalError

from backend.config import get_settings
from backend.routes.access import actor, require_team
from backend.db import transaction
from backend.services.clients import client_connections, connections, mapping
from backend.services.intake import leadlock_app

router = APIRouter()


class MapBody(BaseModel):
    client: str
    expected_revision: int | None = None
    reactivate: bool = False


class RevisionBody(BaseModel):
    expected_revision: int | None = None
    reason: str | None = None


def _run(fn):
    require_team()
    try:
        with transaction() as s:
            return fn(s)
    except mapping.RevisionConflict as error:
        raise HTTPException(status_code=409, detail={"code": "changed_elsewhere", "message": str(error)}) from None
    except mapping.MappingError as error:
        raise HTTPException(status_code=400, detail={"code": "refused", "message": str(error)}) from None
    except OperationalError:
        raise HTTPException(status_code=503, detail={"code": "database_unavailable"}) from None


class LinkBody(BaseModel):
    client: str | None = None
    channel: str
    ref: dict
    expected_revision: int | None = None
    reactivate: bool = False


class ContactBody(BaseModel):
    client: str
    value: str


class ApplicableBody(BaseModel):
    client: str
    channel: str
    applicable: bool
    reason: str | None = None


def _then_collect(out: dict) -> dict:
    """Second transaction, after the mapping committed (see connections.start_collection for why)."""
    scope_id = out.pop("scope_id", None)
    if scope_id:
        try:
            out["collection"] = _run(lambda s: connections.start_collection(s, UUID(scope_id)))
        except HTTPException:  # mapping saved; the scheduler's sweep starts it if queueing failed here
            out["collection"] = "queued_by_scheduler" if get_settings().sync_scheduler_enabled else "not_started"
    return out


@router.get("/clients")
def clients_overview() -> dict:
    """Every client and its five intake channels (the Connections screen)."""
    return _run(client_connections.overview)


@router.post("/link")
def link(body: LinkBody) -> dict:
    if not body.client:
        raise HTTPException(status_code=400, detail={"code": "refused", "message": "choose the client"})
    return _then_collect(_run(lambda s: client_connections.link(s, client=body.client, channel=body.channel,
        ref=body.ref, expected_revision=body.expected_revision, actor=actor(), reactivate=body.reactivate)))


@router.post("/unlink")
def unlink(body: LinkBody) -> dict:
    return _run(lambda s: client_connections.unlink(s, channel=body.channel, ref=body.ref,
                                                    expected_revision=body.expected_revision, actor=actor()))


@router.post("/contacts")
def add_contact(body: ContactBody) -> dict:
    return _run(lambda s: client_connections.add_contact(s, client=body.client, value=body.value, actor=actor()))


@router.post("/applicable")
def applicable(body: ApplicableBody) -> dict:
    return _run(lambda s: client_connections.set_applicable(s, client=body.client, channel=body.channel,
                                                            applicable=body.applicable, reason=body.reason, actor=actor()))


@router.get("/leadlock")
def leadlock(client: str | None = None) -> dict:
    return _run(lambda s: connections.leadlock_rows(s, client))


@router.post("/leadlock/{location_id}/map")
def map_location(location_id: str, body: MapBody) -> dict:
    return _then_collect(_run(lambda s: connections.map_location(s, location_id, body.client,
        expected_revision=body.expected_revision, actor=actor(), reactivate=body.reactivate)))


@router.post("/leadlock/{location_id}/unmap")
def unmap_location(location_id: str, body: RevisionBody) -> dict:
    return _run(lambda s: connections.unmap_location(s, location_id, expected_revision=body.expected_revision,
                                                     actor=actor()))


@router.post("/leadlock/{location_id}/not-a-client")
def not_a_client(location_id: str, body: RevisionBody) -> dict:
    return _run(lambda s: connections.mark_not_a_client(s, location_id, expected_revision=body.expected_revision,
                                                        actor=actor(), reason=body.reason))


@router.post("/leadlock/{location_id}/restore")
def restore(location_id: str, body: RevisionBody) -> dict:
    return _run(lambda s: connections.restore_location(s, location_id, expected_revision=body.expected_revision,
                                                       actor=actor()))


@router.post("/leadlock/refresh")
def refresh() -> dict:
    """Re-read which sub-accounts the app is installed on and their names (one LeadLock call)."""
    require_team()
    try:
        return leadlock_app.reconcile()
    except leadlock_app.LeadLockAppError as error:
        raise HTTPException(status_code=502, detail={"code": "leadlock_unavailable", "message": str(error)}) from None
