"""Shared edits (services/edits.py): load them all at start, save one when a person presses a save button. Team only."""
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.exc import OperationalError

from backend.db import transaction
from backend.routes.access import actor, current_user, require_team
from backend.services import edits

router = APIRouter()


@router.get("")
def load_edits() -> dict:
    require_team()
    try:
        with transaction() as s:
            return edits.load(s)
    except OperationalError:
        raise HTTPException(status_code=503, detail={"code": "database_unavailable"}) from None


class EditBody(BaseModel):
    changes: dict
    expected_revision: int | None = None  # the revision the change is based on; None = "there was no edit yet"
    viewer: str = Field(default="", max_length=100)  # the person named in the app (no named sign-in yet)


@router.put("/{kind}/{key}")
def save_edit(kind: Literal["action", "client"], key: str, body: EditBody) -> dict:
    require_team()
    # Signed in through Command Center: that person, whatever the app sends. Otherwise the name the app gives.
    who = actor() if current_user.get() else f"{body.viewer.strip() or 'someone'} · {actor()}"
    try:
        with transaction() as s:
            return edits.save(s, kind, key, body.changes, expected_revision=body.expected_revision, actor=who[:200])
    except edits.Conflict as conflict:
        by = conflict.current.get("by") or "someone"
        raise HTTPException(status_code=409, detail={
            "code": "changed", "message": f"{by.split(' · ')[0].split(' <')[0]} changed this since you opened it; it now shows their version.",
            "current": conflict.current}) from None
    except edits.EditError as error:
        raise HTTPException(status_code=400, detail={"code": "refused", "message": str(error)}) from None
    except OperationalError:
        raise HTTPException(status_code=503, detail={"code": "database_unavailable"}) from None
