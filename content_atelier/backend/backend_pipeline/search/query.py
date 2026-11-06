"""The vector of a search query (plan 2.B6), made only when it can be made.

A query is embedded through the llm module like any other model call: the encoding catch must be on, a key must be set,
and an active run plan (E.B1) must cover the `embedding` stage, or the provider refuses. Any of those missing is not an
error for the person searching: the search runs on the words alone and the answer says so (`query_embedding_status:
unavailable`, with the reason), so a missing key never looks like "no results" and never silently changes what a
ranking means.

Nothing is cached on disk. A small in-process cache keeps a repeated query (a person paging or refining filters) from
being paid for again; it is keyed by the embedding contract and the exact text.
"""
from __future__ import annotations

import logging
from collections import OrderedDict
from dataclasses import dataclass

from ..config import embedding_contract
from ..llm import live_provider
from ..llm.call import provider_embed
from ..llm.runs import LlmRuns
from ..matching import vector_valid
from ..store import canonical_hash

log = logging.getLogger(__name__)
CACHE_SIZE = 512
_cache: OrderedDict[str, list[float]] = OrderedDict()


@dataclass(frozen=True)
class QueryVector:
    vector: list[float] | None
    status: str  # "used" or "unavailable"
    detail: str | None = None


def make_provider(models, storage):
    """The embeddings provider (tests replace this with an offline double; a live one needs a key and a run plan)."""
    return live_provider(models, storage=storage, chat=False)


def _unavailable(detail: str) -> QueryVector:
    return QueryVector(None, "unavailable", detail)


def embed_query(text: str, *, models, storage, purpose: str = "search_query") -> QueryVector:
    """`purpose` names the caller in the llm_runs record: a search query, or a published final (L.B9)."""
    if not storage.encoding_enabled and not storage.synthetic:
        return _unavailable("Embedding is switched off for this deployment (ATELIER_ALLOW_ENCODING); matched on the words only")
    try:
        contract = embedding_contract(models)
    except ValueError as exc:
        return _unavailable(str(exc))
    key = canonical_hash({"contract": contract, "text": text})
    if key in _cache:
        _cache.move_to_end(key)
        return QueryVector(_cache[key], "used")
    try:
        provider = make_provider(models, storage)
        runs = LlmRuns.for_storage(storage) if storage.database_url else None
        vector, _ = provider_embed(provider, runs, model=models.embedding_model, text=text,
                                   fingerprint=canonical_hash({"purpose": purpose, "key": key}),
                                   context={"purpose": purpose})
    except Exception as exc:  # no key, no plan, routing, a provider outage: the search still answers, and says why
        log.info("Query embedding unavailable: %s", type(exc).__name__)
        return _unavailable(f"{type(exc).__name__}: {exc}"[:300])
    if not vector_valid(vector):
        return _unavailable("The embedding provider returned a vector that is not usable")
    _cache[key] = [float(x) for x in vector]
    while len(_cache) > CACHE_SIZE:
        _cache.popitem(last=False)
    return QueryVector(_cache[key], "used")
