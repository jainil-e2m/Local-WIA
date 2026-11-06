from __future__ import annotations

import json
import secrets
from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import Field

from ..config import Settings
from ..storage_config import StorageSettings
from .config import IntakeSettings
from .contracts import Payload, SlackBatch
from .repository import IntakeRepository


class Search(Payload):
    text: str = Field(min_length=1, max_length=2000)
    k: int = Field(default=20, ge=1, le=50)


async def bounded_body(request, maximum):
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > maximum:
            raise HTTPException(413, 'Intake request exceeds its size limit')
    return bytes(body)


def routers(storage=None, config=None):
    storage = storage or StorageSettings.from_env()
    config = config or IntakeSettings.from_env()
    if config.slack_token and config.slack_token == storage.api_secret:
        raise ValueError('Slack delivery requires a credential distinct from the backend secret')
    repo = IntakeRepository(storage, config)

    def service(authorization: str = Header(default='')):
        if not config.slack_token or not secrets.compare_digest(authorization.encode(), ('Bearer ' + config.slack_token).encode()):
            raise HTTPException(401, 'Slack intake service authorization required')

    def actor(authorization: str = Header(default=''), x_atelier_actor: str = Header(default=''),
              x_atelier_email: str = Header(default='')):
        if not storage.api_secret or not secrets.compare_digest(authorization.encode(), ('Bearer ' + storage.api_secret).encode()):
            raise HTTPException(401, 'Verified backend authorization required')
        if not x_atelier_actor.strip() or len(x_atelier_actor) > 320:
            raise HTTPException(401, 'Trusted actor required')
        email = x_atelier_email.strip() or x_atelier_actor.strip()
        if len(email) > 320:
            raise HTTPException(401, 'Invalid actor identity')
        return email

    def action(fn, *args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except PermissionError as exc:
            raise HTTPException(403, str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc

    bot = APIRouter(prefix='/intake/v1', dependencies=[Depends(service)])

    @bot.get('/requests')
    def requests():
        return repo.requests()

    @bot.post('/slack/batches', status_code=202)
    async def receive(request: Request):
        raw = await bounded_body(request, config.max_batch_bytes)
        try:
            batch = SlackBatch.model_validate_json(raw)
        except ValueError as exc:
            raise HTTPException(422, 'Invalid Slack batch; consult the versioned schema') from exc
        from starlette.concurrency import run_in_threadpool
        return await run_in_threadpool(action, repo.receive, batch, raw)

    @bot.get('/slack/schema')
    def schema():
        return SlackBatch.model_json_schema()

    @bot.put('/assets/{asset_id}/content', status_code=202)
    async def upload(asset_id: str, request: Request):
        raw = await bounded_body(request, config.max_upload_bytes)
        from starlette.concurrency import run_in_threadpool
        return await run_in_threadpool(action, repo.upload, asset_id, raw)

    @bot.get('/batches/{batch_id}')
    def receipt(batch_id: str):
        return action(repo.batch_status, batch_id)

    ui = APIRouter(prefix='/storage/intake', dependencies=[Depends(actor)])

    @ui.get('/overview')
    def overview(subject: str = Depends(actor)):
        return repo.overview(subject)

    @ui.post('/connections/{provider}/activate', status_code=202)
    def activate(provider: Literal['slack', 'fathom'], subject: str = Depends(actor)):
        return action(repo.activate, provider, subject)

    @ui.post('/refresh', status_code=202)
    def refresh(subject: str = Depends(actor)):
        action(repo.authorize, subject)
        return action(repo.request_collection)

    @ui.post('/complete', status_code=202)
    def complete(subject: str = Depends(actor)):
        action(repo.authorize, subject)
        return action(repo.request_collection, complete=True)

    @ui.post('/jobs/{job_id}/retry', status_code=202)
    def retry(job_id: str, subject: str = Depends(actor)):
        action(repo.retry_intake, job_id, subject)
        return {'status': 'queued'}

    @ui.get('/sources/{source_id}')
    def detail(source_id: str):
        return action(repo.detail, source_id)

    @ui.get('/buckets/{bucket_id}')
    def bucket(bucket_id: str):
        return action(repo.bucket_detail, bucket_id)

    @ui.get('/revisions/{revision_id}/original')
    def original(revision_id: str):
        with repo.connection() as conn:
            row = conn.execute('SELECT raw_artifact FROM intake_revisions WHERE revision_id=%s', (revision_id,)).fetchone()
            if not row:
                raise HTTPException(404, 'Revision not found')
            data = repo.store.path(row['raw_artifact']).read_bytes()
            try:
                return {'revision_id': revision_id, 'original': json.loads(data)}
            except (ValueError, UnicodeError):
                raise HTTPException(409, 'Binary original is available from the attachment download')

    @ui.get('/assets/{asset_id}/content')
    def asset_content(asset_id: str):
        with repo.connection() as conn:
            asset = conn.execute('SELECT * FROM intake_assets WHERE asset_id=%s', (asset_id,)).fetchone()
            if not asset or not asset['raw_artifact']:
                raise HTTPException(404, 'Attachment bytes have not been received')
            return FileResponse(repo.store.path(asset['raw_artifact']), media_type='application/octet-stream', filename=asset_id)

    @ui.post('/search')
    def search(payload: Search):
        # Local full-text search: no hidden embedding-provider call on browsing.
        from ..retrieval import archive
        with repo.connection() as conn:
            snapshot = action(archive, conn, Settings.from_env(), storage.synthetic)
            return conn.execute("""SELECT t.transcript_id,t.title,t.source_url,c.chunk_id,c.chunk_text,c.passage_refs,
                t.source_metadata->'intake'->>'source_id' AS source_id,
                ts_rank_cd(to_tsvector('english',c.chunk_text),websearch_to_tsquery('english',%s)) rank
                FROM transcript_chunks c JOIN transcripts t USING(transcript_id)
                WHERE c.chunk_id=ANY(%s) AND to_tsvector('english',c.chunk_text) @@ websearch_to_tsquery('english',%s)
                ORDER BY rank DESC,c.chunk_id LIMIT %s""", (payload.text, list(snapshot['chunks']), payload.text, payload.k)).fetchall()

    return bot, ui
