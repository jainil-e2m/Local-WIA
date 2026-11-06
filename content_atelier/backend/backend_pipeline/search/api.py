"""`POST /search` (plan 2.B3, 2.B6): one route over the moments ledger and the transcript chunks.

    POST /storage/search   {text, k (1..50, default 10), scope: moments | chunks | all, filters: {...}}

Any signed-in role may search, like `/search/transcripts` (a POST because it names the verified email, not because it
writes). The answer is the best `k` hits, each with the fused score, the methods that found it (`phrase`, `semantic`), the
moment or chunk, and a complete `Citation`; the response also says whether the query's meaning could be used
(`query_embedding_status`) and which filters were applied, including the consent default. `/search/transcripts` is unchanged.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from fastapi import Depends
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .citation import Citation
from .filters import SearchFilters, resolve_topic
from .models import Answer, ChunkSummary, MomentSummary
from . import hybrid, query, rows

Scope = Literal["moments", "chunks", "all"]


class SearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=1, max_length=2000)
    k: int = Field(default=10, ge=1, le=50)
    scope: Scope = "moments"
    filters: SearchFilters = Field(default_factory=SearchFilters)

    @field_validator("text")
    @classmethod
    def _text(cls, value: str) -> str:
        value = " ".join(value.split())
        if not value:
            raise ValueError("Search text is empty")
        return value

    @model_validator(mode="after")
    def _scope(self):
        if self.scope == "chunks" and self.filters.moment_only():
            raise ValueError("moment_type and topic_id describe moments; use scope 'moments' or 'all'")
        return self


class SearchHit(Answer):
    kind: Literal["moment", "chunk"]
    score: float
    matched_by: list[Literal["phrase", "semantic"]]
    moment: MomentSummary | None = None
    chunk: ChunkSummary | None = None
    citation: Citation


class FiltersApplied(Answer):
    date_from: datetime | None
    date_to: datetime | None
    client_id: str | None
    source_type: str | None
    call_type: str | None
    speaker_role: list[str]
    moment_type: list[str]
    consent_status: list[str]
    consent_defaulted: bool
    topic_id: str | None
    topic_resolved_id: str | None
    document_ids: list[str]
    kinds: list[Literal["moment", "chunk"]]
    verified_only: bool
    current_only: bool


class SearchResponse(Answer):
    hits: list[SearchHit]
    query_embedding_status: Literal["used", "unavailable"]
    query_embedding_detail: str | None
    filters_applied: FiltersApplied
    scope: Scope
    k: int
    hits_withheld: int


def kinds_searched(scope: str, filters: SearchFilters) -> list[str]:
    kinds = []
    if scope in ("moments", "all"):
        kinds.append("moment")
    if scope in ("chunks", "all") and not filters.moment_only():
        kinds.append("chunk")
    return kinds


def run_search(repo, models, request: SearchRequest, *, vector: query.QueryVector | None = None) -> dict:
    """The answer to one search. `vector` is the query's embedding when the caller already has it (the command line)."""
    from .. import settings_store
    from ..normalise.glossary import Glossary
    filters = request.filters
    found = vector or query.embed_query(request.text, models=models, storage=repo.settings)
    with repo.connection() as conn:
        tuning = settings_store.values(["search.rrf_k", "search.candidates", "search.semantic_min_cosine"], conn)
        topic_id = resolve_topic(conn, filters.topic_id)
        kinds = kinds_searched(request.scope, filters)
        chunk_query = Glossary.from_database(conn).normalise(request.text) if "chunk" in kinds else None
        fused = hybrid.search(conn, request.text, found.vector, filters, k=request.k, scope=request.scope, topic_id=topic_id,
                              model=models.embedding_model, rrf_k=tuning["search.rrf_k"], candidates=tuning["search.candidates"],
                              min_cosine=tuning["search.semantic_min_cosine"], chunk_query=chunk_query)
        moments = rows.moment_hits(conn, [h["id"] for h in fused if h["kind"] == "moment"])
        chunks = rows.chunk_hits(conn, [h["id"] for h in fused if h["kind"] == "chunk"])
    hits, withheld = [], 0
    for hit in fused:
        built = (moments if hit["kind"] == "moment" else chunks).get(hit["id"])
        if built is None:
            withheld += 1  # its citation cannot be located in the original text, so it is not cited
            continue
        summary, citation = built
        hits.append({"kind": hit["kind"], "score": hit["score"], "matched_by": hit["matched_by"],
                     "moment": summary if hit["kind"] == "moment" else None,
                     "chunk": summary if hit["kind"] == "chunk" else None, "citation": citation})
    applied = {**filters.model_dump(), "consent_status": filters.consent, "consent_defaulted": filters.consent_defaulted,
               "topic_resolved_id": topic_id, "kinds": kinds, "verified_only": True, "current_only": True}
    return {"hits": hits, "query_embedding_status": found.status, "query_embedding_detail": found.detail,
            "filters_applied": applied, "scope": request.scope, "k": request.k, "hits_withheld": withheld}


def install(routes, repo, decider, action):
    from ..config import Settings

    @routes.post("/search", response_model=SearchResponse)
    def search(payload: SearchRequest, subject: str = Depends(decider)):
        # A read, but a POST: it names the verified email like every other POST (any role may search).
        return action(run_search, repo, Settings.from_env(database_url=repo.settings.database_url), payload)
