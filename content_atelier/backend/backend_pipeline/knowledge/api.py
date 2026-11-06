"""Context-system routes under /storage/context (Phase L). Installed by storage_api.router.

Reads need the backend secret and a trusted actor; every decision binds to the verified email the Node server
resolves (R37), and the service checks the approver lists. Errors map as elsewhere: 403 for a non-approver,
409 for a stale hash or a refused state change, 503 before migration 006.
"""
from __future__ import annotations

from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from . import compiler, items, mining, performance, review, staleness
from ..api_models import (
    CompileResult, ContextKinds, ContextQueue, ContextSummary, DecisionResult, DiscardResult, EntryResult, ItemHistory, KbVersions,
    KnownItems, PublishedPage, StaleWarnings, VersionDiff, returns,
)

Kind = Literal["rule", "exemplar", "offer", "price", "roster_member", "result", "cta", "process_step", "belief",
               "audience_phrase", "format_rule", "campaign", "content_plan_entry", "performance_note"]


class Payload(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Changes(Payload):
    text: str | None = Field(default=None, max_length=8000)
    body: dict | None = None
    visibility: Literal["public", "internal"] | None = None
    sensitivity: Literal["none", "client_private"] | None = None
    permission: Literal["published", "client_permission", "none"] | None = None
    valid_from: date | None = None
    valid_to: date | None = None


class ItemDecision(Payload):
    expected_hash: str = Field(min_length=10, max_length=128)
    action: Literal["accept", "edit", "reject"]
    reason: str = Field(min_length=1, max_length=2000)
    author: str | None = Field(default=None, max_length=200)
    changes: Changes | None = None


class BatchEntry(Payload):
    item_id: str = Field(max_length=140)
    expected_hash: str = Field(max_length=128)


class BatchDecision(Payload):
    action: Literal["accept", "reject"]
    reason: str = Field(min_length=1, max_length=2000)
    author: str | None = Field(default=None, max_length=200)
    entries: list[BatchEntry] = Field(min_length=1, max_length=review.MAX_BATCH)


class PublishedConfirmation(Payload):
    content_ids: list[str] = Field(min_length=1, max_length=review.MAX_BATCH)
    reason: str = Field(min_length=1, max_length=2000)


class Entry(Payload):
    kind: Kind
    name: str | None = Field(default=None, max_length=200)
    key: str | None = Field(default=None, max_length=200)
    body: dict
    text: str | None = Field(default=None, max_length=8000)
    visibility: Literal["public", "internal"] = "public"
    sensitivity: Literal["none", "client_private"] = "none"
    permission: Literal["published", "client_permission", "none"] | None = None
    valid_from: date | None = None
    # The last day the entry is in use ("In use until"): an offer, price or campaign that ends (L.F2, L.B8).
    valid_to: date | None = None
    author: str | None = Field(default=None, max_length=200)
    reason: str = Field(min_length=1, max_length=2000)
    # A client-generated key: a retried request records one version, not two (L.F2).
    idempotency_key: str | None = Field(default=None, max_length=100)


class Compile(Payload):
    on: date | None = None


class Approval(Payload):
    note: str = Field(min_length=1, max_length=2000)


class Benchmark(Payload):
    passed: bool
    result_ref: str = Field(min_length=1, max_length=500)
    note: str | None = Field(default=None, max_length=2000)


class Piece(Payload):
    published_on: date
    channel: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=2000)
    text: str | None = Field(default=None, max_length=20000)
    brief_id: str | None = Field(default=None, max_length=140)
    pillar: str | None = Field(default=None, max_length=40)
    content_type: str | None = Field(default=None, max_length=100)


class PerformanceEntry(Payload):
    on: date
    metric: str = Field(min_length=1, max_length=100)
    value: str = Field(min_length=1, max_length=500)
    direction: Literal["positive", "negative"] | None = None


class Link(Payload):
    brief_id: str = Field(min_length=1, max_length=140)


class CsvImport(Payload):
    csv: str = Field(min_length=1, max_length=60000)


class Mining(Payload):
    week_id: str | None = Field(default=None, max_length=140)
    since: date | None = None
    until: date | None = None


def install(routes, settings, repo, actor, decider, action):
    def enabled():
        # The Knowledge screens' routes answer only while the feature is on (R31, section 0 rule 7), as packs and the
        # calendar do: with the flag off, nothing can approve or activate a knowledge-base version from outside.
        if not settings.context_enabled:
            raise HTTPException(404, "The Knowledge screens are switched off (ATELIER_CONTEXT_ENABLED)")
    ctx = APIRouter(dependencies=[Depends(enabled)])

    def with_conn(fn, *args, **kwargs):
        def run():
            with repo.connection() as conn:
                return fn(conn, *args, **kwargs)
        return action(run)

    @ctx.get("/context/summary", responses=returns(ContextSummary))
    def context_summary():
        return with_conn(review.summary)

    @ctx.get("/context/queue", responses=returns(ContextQueue))
    def context_queue(kind: Kind | None = None, status: Literal["candidate", "confirmed", "rejected", "retired"] = "candidate",
                      limit: int = Query(default=50, ge=1, le=200), offset: int = Query(default=0, ge=0),
                      subject: str = Depends(decider)):
        return with_conn(review.queue, kind=kind, status=status, limit=limit, offset=offset, actor=subject, settings=settings)

    @ctx.post("/context/items/{item_id}/decision", responses=returns(DecisionResult))
    def context_decide(item_id: str, payload: ItemDecision, subject: str = Depends(decider)):
        changes = payload.changes.model_dump(exclude_unset=True) if payload.changes else None
        return with_conn(review.decide, settings, item_id, payload.expected_hash, payload.action, subject,
                         reason=payload.reason, author=payload.author, changes=changes)

    @ctx.post("/context/batch")
    def context_batch(payload: BatchDecision, subject: str = Depends(decider)):
        return with_conn(review.batch, settings, [e.model_dump() for e in payload.entries], payload.action, subject,
                         reason=payload.reason, author=payload.author)

    @ctx.get("/context/items", responses=returns(KnownItems))
    def context_known(kind: Kind | None = None, on: date | None = None):
        return with_conn(review.known, kind=kind, on=on)

    @ctx.post("/context/items", status_code=201, responses=returns(EntryResult, 201))
    def context_enter(payload: Entry, subject: str = Depends(decider)):
        fields = payload.model_dump(exclude={"reason"})
        return with_conn(review.enter, settings, subject, reason=payload.reason, **fields)

    @ctx.get("/context/items/{item_id}/history", responses=returns(ItemHistory))
    def context_history(item_id: str):
        return with_conn(review.history, item_id)

    @ctx.get("/context/published", responses=returns(PublishedPage))
    def context_published(status: Literal["unconfirmed", "confirmed"] | None = None,
                          limit: int = Query(default=100, ge=1, le=500), offset: int = Query(default=0, ge=0)):
        def run(conn):
            rows = conn.execute("""SELECT content_id,published_on,channel,title,status,source_kind,source_ref,details,
                angle_id,brief_id,performance FROM published_content WHERE (%s::text IS NULL OR status=%s)
                ORDER BY published_on DESC NULLS LAST,content_id LIMIT %s OFFSET %s""", (status, status, limit, offset)).fetchall()
            return {"items": [review._public(r) for r in rows]}
        return with_conn(run)

    @ctx.post("/context/published/confirm")
    def context_published_confirm(payload: PublishedConfirmation, subject: str = Depends(decider)):
        return with_conn(review.confirm_published, settings, payload.content_ids, subject, reason=payload.reason)

    @ctx.get("/context/versions", responses=returns(KbVersions))
    def context_versions():
        return with_conn(lambda conn: {"active": compiler.active_version(conn), "versions": compiler.versions(conn)})

    @ctx.post("/context/versions", status_code=201, responses=returns(CompileResult, 201))
    def context_compile(payload: Compile, subject: str = Depends(decider)):
        from ..cycle.verification import knowledge_root

        def run(conn):
            review.require(settings, subject)
            return compiler.compile_version(conn, on=payload.on or date.today(), actor=subject, root=knowledge_root())
        return with_conn(run)

    @ctx.get("/context/versions/{version}/diff", responses=returns(VersionDiff))
    def context_diff(version: str, against: str | None = None):
        return with_conn(compiler.diff, version, against)

    @ctx.post("/context/versions/{version}/approve")
    def context_approve(version: str, payload: Approval, subject: str = Depends(decider)):
        return with_conn(compiler.approve, settings, version, subject, note=payload.note)

    @ctx.post("/context/versions/{version}/discard", responses=returns(DiscardResult))
    def context_discard(version: str, subject: str = Depends(decider)):
        return with_conn(compiler.discard, settings, version, subject)

    @ctx.post("/context/versions/{version}/benchmark")
    def context_benchmark(version: str, payload: Benchmark, subject: str = Depends(decider)):
        return with_conn(compiler.record_benchmark, settings, version, subject, passed=payload.passed,
                         result_ref=payload.result_ref, note=payload.note or "")

    @ctx.post("/context/published", status_code=201)
    def context_piece(payload: Piece, subject: str = Depends(decider)):
        return with_conn(performance.add_piece, settings, subject, **payload.model_dump())

    @ctx.post("/context/published/import")
    def context_import(payload: CsvImport, subject: str = Depends(decider)):
        return with_conn(performance.import_csv, settings, subject, payload.csv)

    @ctx.post("/context/published/{content_id}/performance")
    def context_performance(content_id: str, payload: PerformanceEntry, subject: str = Depends(decider)):
        return with_conn(performance.enter, settings, subject, content_id, on=payload.on, metric=payload.metric,
                         value=payload.value, direction=payload.direction)

    @ctx.post("/context/published/{content_id}/link")
    def context_link(content_id: str, payload: Link, subject: str = Depends(decider)):
        return with_conn(performance.link, settings, subject, content_id, payload.brief_id)

    @ctx.get("/context/warnings", responses=returns(StaleWarnings))
    def context_staleness():
        return with_conn(lambda conn: {"warnings": staleness.warnings(conn)})

    @ctx.get("/context/mining")
    def context_mining_last():
        def run(conn):
            row = conn.execute("SELECT value FROM settings WHERE key='context.mining.last'").fetchone()
            return {"last": row["value"] if row else None}
        return with_conn(run)

    @ctx.post("/context/mining")
    def context_mining(payload: Mining, subject: str = Depends(decider)):
        def run(conn):
            review.require(settings, subject)
            # The categorisation model, when configured, is a paid call: it runs from the scheduler or the CLI
            # under a run plan, never from a browser request. This route reads and groups only.
            return mining.run(conn, actor=subject, week_id=payload.week_id, since=payload.since, until=payload.until)
        return with_conn(run)

    @ctx.get("/context/kinds", responses=returns(ContextKinds))
    def context_kinds():
        return {"kinds": list(items.KINDS), "operating": sorted(items.OPERATING_KINDS), "identity": sorted(items.IDENTITY_KINDS),
                "batch": sorted(items.LOW_RISK_KINDS), "documents": items.DOCUMENT_FOR_KIND,
                "schemas": {k: v.model_json_schema() for k, v in items.SCHEMAS.items()}}
    routes.include_router(ctx)
    return routes
