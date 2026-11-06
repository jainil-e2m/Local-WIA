"""One answer for a database that is not at the code's migration (plan 0.B11)."""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from psycopg.errors import UndefinedColumn, UndefinedTable

SCHEMA_NOT_READY = "Storage schema is not ready; apply the explicit migration"


class NeedsInput(ValueError):
    """A request a person completes in place (a missing note, a CTA not chosen): answered 422, so the screen shows it beside
    the form. Every other refusal is a 409, which the app shows as "this changed while you were working on it" with a reload
    (found by the N1 shakedown: editing a held card without a note was shown as a conflict)."""


def install_schema_handler(app: FastAPI) -> None:
    """A missing table or column is the deployment's fault, not a defect in the request: answer 503 on every route,
    not only on the routes that remember to catch it."""
    @app.exception_handler(UndefinedTable)
    @app.exception_handler(UndefinedColumn)
    async def schema_not_ready(_request: Request, _error: Exception):
        return JSONResponse({"detail": SCHEMA_NOT_READY}, status_code=503)
