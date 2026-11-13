"""Admin decisions on AI-proposed actions (Action Hub → Needs review). Approved ones join the Action Hub."""
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.exc import OperationalError

from backend.db import transaction
from backend.routes.access import actor, current_user, require_team
from backend.services.ai import decisions

router = APIRouter()


class Decision(BaseModel):
    decision: Literal["approve", "reject"]
    admin: str = Field(min_length=1, max_length=100)  # the admin named in the app (see decisions.py shortcut)
    edits: dict = Field(default_factory=dict)  # title, owner, due (YYYY-MM-DD or ""), side
    reason: str = Field(default="", max_length=200)


@router.post("/proposals/{ref}/decision")
def decide(ref: str, body: Decision) -> dict:
    require_team()
    try:
        with transaction() as s:
            return decisions.decide(s, ref, body.decision == "approve", body.edits,
                                    actor=actor() if current_user.get() else f"{body.admin} · {actor()}", reason=body.reason)
    except decisions.DecisionError as error:
        raise HTTPException(status_code=400, detail={"code": "refused", "message": str(error)}) from None
    except OperationalError:
        raise HTTPException(status_code=503, detail={"code": "database_unavailable"}) from None
