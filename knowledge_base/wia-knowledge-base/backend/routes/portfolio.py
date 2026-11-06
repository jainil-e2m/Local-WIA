"""The portfolio the production frontend loads at start, and its client logos. Team only (routes/access.py)."""
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, Response
from sqlalchemy import Text, cast, select
from sqlalchemy.exc import OperationalError

from backend.db import SessionFactory
from backend.models.db import ReadModelSnapshot, SourceRecord, SourceVersion
from backend.routes.access import require_team
from backend.services.read_models import portfolio

router = APIRouter()
SNAPSHOT = ReadModelSnapshot.name == portfolio.NAME


@router.get("")
def get_portfolio(request: Request) -> Response:
    """The stored build as-is (no parse/re-encode). A matching If-None-Match costs one tiny query."""
    require_team()
    try:
        with SessionFactory() as s:
            built_at = s.execute(select(ReadModelSnapshot.built_at).where(SNAPSHOT)).scalar_one_or_none()
            if built_at is None:
                raise HTTPException(status_code=404, detail={"code": "not_built",
                    "message": "The portfolio isn't built yet: run `kb portfolio refresh`."})
            etag = f'"{int(built_at.timestamp() * 1000)}"'
            if request.headers.get("if-none-match") == etag:
                return Response(status_code=304, headers={"ETag": etag})
            body = s.execute(select(cast(ReadModelSnapshot.payload, Text)).where(SNAPSHOT)).scalar_one()
    except OperationalError:
        raise HTTPException(status_code=503, detail={"code": "database_unavailable"}) from None
    return Response(body, media_type="application/json", headers={"ETag": etag, "Cache-Control": "private, no-cache"})


@router.get("/logos/{record_id}")
def logo(record_id: UUID) -> Response:
    """Only a logo the current build chose: this never becomes a way to read any other Drive file."""
    require_team()
    with SessionFactory() as s:
        logos = s.execute(select(ReadModelSnapshot.payload["logos"]).where(SNAPSHOT)).scalar_one_or_none() or {}
        if str(record_id) not in {item.get("recordId") for item in logos.values()}:
            raise HTTPException(status_code=404, detail={"code": "not_a_portfolio_logo"})
        record = s.get(SourceRecord, record_id)
        version = s.get(SourceVersion, record.current_version_id)
    try:
        mime, data = portfolio.logo_bytes(record, version)
    except Exception:  # noqa: BLE001 — the card falls back to initials
        raise HTTPException(status_code=502, detail={"code": "logo_unavailable"}) from None
    return Response(data, media_type=mime, headers={"Cache-Control": "private, max-age=86400"})
