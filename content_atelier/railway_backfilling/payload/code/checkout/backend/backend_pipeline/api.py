from __future__ import annotations

import os
import secrets

from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel

from .config import Settings
from .pipeline import Pipeline
from .storage_api import router
from .storage_config import StorageSettings

app = FastAPI(title="Content Atelier transcript-to-angle pipeline", version="0.1.0")
settings = Settings.from_env()
pipeline = Pipeline(settings)
app.include_router(router())
from .intake.api import routers as intake_routers
for intake_router in intake_routers():
    app.include_router(intake_router)


class RunRequest(BaseModel):
    week_index: int
    mode: str = "plan"


@app.get("/health")
def health() -> dict:
    storage = StorageSettings.from_env()
    return {
        "status": "ok",
        "live_enabled": settings.live_enabled,
        "moments_model": settings.openrouter_moments_model,
        "angles_model": settings.openrouter_angles_model,
        "embedding_model": settings.embedding_model,
        'sql_generation_enabled':storage.generation_enabled,
        'sql_encoding_enabled':storage.encoding_enabled,
    }


def legacy_authorized(authorization):
    secret = StorageSettings.from_env().api_secret
    if os.getenv('ATELIER_ENABLE_LEGACY_API')!='true' or not secret or not secrets.compare_digest(authorization,'Bearer '+secret):
        raise HTTPException(403,'Legacy experiment HTTP routes are disabled; use the local experiment CLI')


@app.post("/runs")
def create_run(request: RunRequest,authorization:str=Header(default='')) -> dict:
    legacy_authorized(authorization)
    if request.mode not in {"plan", "fake", "live", "replay"}:
        raise HTTPException(status_code=400, detail="mode must be plan, fake, live or replay")
    if request.mode == "live" and not settings.live_enabled:
        raise HTTPException(status_code=409, detail="live mode is disabled")
    try:
        result = (
            pipeline.plan(request.week_index, request.mode)
            if request.mode == "plan"
            else pipeline.run(request.week_index, mode=request.mode)
        )
        return result.model_dump(mode="json") if hasattr(result, "model_dump") else result
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/runs/{run_id}/review")
def get_review(run_id: str,authorization:str=Header(default='')) -> dict:
    legacy_authorized(authorization)
    try:
        return pipeline.store.read_json(f"experiments/default/runs/{run_id}/review.json")
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="run review not found") from exc
