"""Ops-only intake views, behind a service token until the Command Center hand-off exists (AR-04).

Returns IDs, names, states and counts only — no content.
"""
import secrets

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select

from backend.config import get_settings
from backend.db import SessionFactory
from backend.models.db import ConnectorAccount, CoverageWindow, SourceScope, SyncRun


def require_ops_token(x_ops_token: str = Header(default="")) -> None:
    expected = get_settings().ops_token
    if not expected or not secrets.compare_digest(x_ops_token, expected):
        raise HTTPException(status_code=401, detail={"code": "unauthorised"})


router = APIRouter(dependencies=[Depends(require_ops_token)])


@router.get("/connectors")
def connectors() -> list[dict]:
    with SessionFactory() as s:
        return [{"id": str(a.id), "provider": a.provider, "identity": a.display_identity, "state": a.state,
                 "blocked_reason": a.blocked_reason, "last_verified_at": a.last_verified_at,
                 "credential_ref": a.credential_ref}
                for a in s.execute(select(ConnectorAccount)).scalars()]


@router.get("/scopes")
def scopes(state: str | None = None) -> list[dict]:
    with SessionFactory() as s:
        q = select(SourceScope, ConnectorAccount.provider).join(ConnectorAccount)
        if state:
            q = q.where(SourceScope.state == state)
        return [{"id": str(sc.id), "provider": p, "kind": sc.kind, "name": sc.name, "state": sc.state,
                 "association_mode": sc.association_mode,
                 "business_id": str(sc.business_id) if sc.business_id else None,
                 "last_successful_sync_at": sc.last_successful_sync_at}
                for sc, p in s.execute(q)]


@router.get("/runs")
def runs(limit: int = 50) -> list[dict]:
    with SessionFactory() as s:
        q = (select(SyncRun, CoverageWindow).outerjoin(CoverageWindow, CoverageWindow.run_id == SyncRun.id)
             .order_by(SyncRun.started_at.desc()).limit(min(limit, 200)))
        return [{"id": str(r.id), "scope_id": str(r.scope_id) if r.scope_id else None, "mode": r.mode,
                 "state": r.state, "window_start": r.window_start, "window_end": r.window_end, "pages": r.pages,
                 "error_class": r.error_class, "coverage": c.counts if c else None,
                 "coverage_state": c.state if c else None, "gap_count": len(c.gaps) if c else 0}
                for r, c in s.execute(q)]
