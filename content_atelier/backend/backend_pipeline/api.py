from __future__ import annotations

from contextlib import asynccontextmanager

import anyio.to_thread
from fastapi import FastAPI
from fastapi.concurrency import run_in_threadpool

from .config import Settings
from .storage_api import router
from .intake.api import routers as intake_routers
from .storage_config import StorageSettings
from .repository import ContentRepository
from .errors import install_schema_handler
from .jobs.dispatch import kick
from . import startup


# Requests one process runs at a time; each holds a database connection (PostgreSQL's limit is 100, shared with the workers).
REQUEST_THREADS = 16


@asynccontextmanager
async def lifespan(_app):
    anyio.to_thread.current_default_thread_limiter().total_tokens = REQUEST_THREADS
    # Refuse to serve with an embedding contract or brief configuration that would fail later.
    startup.verify(StorageSettings.from_env(), settings)
    yield


# The routes: /storage (the editorial API and the intake's screens), /intake/v1 (the intake service's delivery, by its
# token) and /health. The file-backed experiment routes (POST /runs, GET /runs/{id}/review) are retired (plan 6.B8); the
# experiment runner stays a local command (`python -m backend_pipeline`).
app = FastAPI(title="Content Atelier transcript-to-angle pipeline", version="0.1.0", lifespan=lifespan)
settings = Settings.from_env()
app.include_router(router())
install_schema_handler(app)


@app.middleware("http")
async def dispatch_after_write(request, call_next):
    """A committed write may have queued a job: put it on its queue now instead of waiting for the next reconcile pass
    (plan 0.B5: the row is committed first, dispatch follows). A failure here only delays the job by one pass."""
    response = await call_next(request)
    if request.method in {"POST", "PUT", "PATCH", "DELETE"} and response.status_code < 400:
        await run_in_threadpool(kick, ContentRepository(StorageSettings.from_env()))
    return response


for intake_router in intake_routers():
    app.include_router(intake_router)


@app.get("/health")
def health() -> dict:
    """The platform's health check: the process is up. It names nothing about the configuration (models, switches),
    which anyone who can reach the port could otherwise read. Job health is `python -m backend_pipeline.jobs health`."""
    return {"status": "ok"}
