"""The portfolio the production frontend loads at start, and its client logos. Team only (routes/access.py)."""
import gzip
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
# The current build, gzipped once: {etag: bytes}. Each load would otherwise read the whole snapshot (tens of MB at
# full history) and gzip it at level 9 in the event loop, stalling every request on the single web process.
_gzipped: dict[str, bytes] = {}


@router.get("")
def get_portfolio(request: Request) -> Response:
    """The stored build as-is (no parse/re-encode). A matching If-None-Match costs one tiny query.

    A sync route, so it runs in the thread pool: the read and the compression stay off the event loop. The gzip
    header makes GZipMiddleware pass the body through untouched."""
    require_team()
    gzip_ok = "gzip" in request.headers.get("accept-encoding", "")
    try:
        with SessionFactory() as s:
            built_at = s.execute(select(ReadModelSnapshot.built_at).where(SNAPSHOT)).scalar_one_or_none()
            if built_at is None:
                raise HTTPException(status_code=404, detail={"code": "not_built",
                    "message": "The portfolio isn't built yet: run `kb portfolio refresh`."})
            etag = f'"{int(built_at.timestamp() * 1000)}"'
            if request.headers.get("if-none-match") == etag:
                return Response(status_code=304, headers={"ETag": etag})
            gz = _gzipped.get(etag) if gzip_ok else None
            body = None if gz is not None else \
                s.execute(select(cast(ReadModelSnapshot.payload, Text)).where(SNAPSHOT)).scalar_one()
    except OperationalError:
        raise HTTPException(status_code=503, detail={"code": "database_unavailable"}) from None
    headers = {"ETag": etag, "Cache-Control": "private, no-cache", "Vary": "Accept-Encoding"}
    if not gzip_ok:
        return Response(body, media_type="application/json", headers=headers)
    if gz is None:
        gz = gzip.compress(body.encode(), compresslevel=6)
        _gzipped.clear()  # keep only the current build
        _gzipped[etag] = gz
    return Response(gz, media_type="application/json", headers={**headers, "Content-Encoding": "gzip"})


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
