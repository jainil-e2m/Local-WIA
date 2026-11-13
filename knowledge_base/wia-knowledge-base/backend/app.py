"""FastAPI application: health checks, the ops-only intake API, the ClickUp connection flow, the
LeadLock Marketplace app (install callback + webhooks), the team API and, when built, the portfolio itself.

Run from the repository root: uvicorn backend.app:app
"""
from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from backend.config import get_settings
from backend.db import engine
from backend.logging.config import configure
from backend.routes import (access, actions, auth, callprep, clickup, clients, connections, edits, leadlock,
                            ops_sources, portfolio)

configure()
app = FastAPI(title="WIA Client Knowledge Base", version="0.1.0")
app.add_middleware(GZipMiddleware, minimum_size=2048)
app.middleware("http")(access.gate)
app.include_router(auth.router, prefix="/api/auth")
app.include_router(ops_sources.router, prefix="/api/v1/ops")
app.include_router(clickup.router, prefix="/api/v1/clickup")
app.include_router(leadlock.router, prefix="/api/v1/leadlock")
app.include_router(clients.router, prefix="/api/v1/clients")
app.include_router(connections.router, prefix="/api/v1/connections")
app.include_router(portfolio.router, prefix="/api/v1/portfolio")
app.include_router(actions.router, prefix="/api/v1/actions")
app.include_router(edits.router, prefix="/api/v1/edits")
app.include_router(callprep.router, prefix="/api/v1")


@app.get("/health/live")
def live() -> dict:
    return {"status": "ok"}


@app.get("/health/ready")
def ready() -> dict:
    with engine.connect() as conn:
        version = conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
    settings = get_settings()
    return {"status": "ok", "schema": version, "mode": settings.mode, "environment": settings.environment,
            "sync_scheduler": settings.sync_scheduler_enabled, "ai": settings.ai_mode}


# The built portfolio (production image). Last, so every API and health route above wins; hash routes need no
# fallback. Locally the Vite dev server serves the frontend instead.
if get_settings().frontend_dist and get_settings().frontend_dist.is_dir():
    app.mount("/", StaticFiles(directory=get_settings().frontend_dist, html=True), name="portfolio")
