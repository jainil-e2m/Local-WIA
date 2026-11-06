"""Hybrid retrieval over moments and chunks (plan 2.B6), exact SQL with no approximate index.

The corpus is thousands of rows, so every query is a scan the planner can afford: cosine distance on the stored vector
(`<=>`) for meaning, a full-text match (`websearch_to_tsquery`) for the words, and the two ranked lists are fused by
reciprocal rank fusion, `sum(1 / (k + rank))` over the lists a hit appears in. Nothing is ever approximate and nothing
calls a model here: the query vector is made by the caller (search/query.py) or is absent, and then only the words count.

Moments: only verified, current ones, never an unverified row (the filters add that, and the column constraint keeps an
unverified row from having a vector). Chunks: current chunks. Only vectors made under the archive's embedding model take
part in the meaning list, so a mixed archive is never compared across models.
"""
from __future__ import annotations

import numpy as np

from .filters import SearchFilters, chunk_conditions, moment_conditions

KIND_ORDER = {"moment": 0, "chunk": 1}


def _where(conditions: list[str]) -> str:
    return " WHERE " + " AND ".join(conditions)


def moment_lists(conn, text: str, vector, filters: SearchFilters, *, topic_id: str | None, model: str, limit: int,
                 min_cosine: float) -> dict[str, list[str]]:
    where, args = moment_conditions(filters, topic_id=topic_id)
    from .rows import MOMENT_FROM
    lists: dict[str, list[str]] = {"phrase": [], "semantic": []}
    lists["phrase"] = [r["id"] for r in conn.execute(
        f"""SELECT m.moment_id AS id, ts_rank_cd(m.tsv, q.query) AS rank {MOMENT_FROM}
            CROSS JOIN websearch_to_tsquery('english', %(text)s) AS q(query)
            {_where(where + ["m.tsv @@ q.query"])} ORDER BY rank DESC, m.moment_id LIMIT %(limit)s""",
        {**args, "text": text, "limit": limit})]
    if vector is not None:
        lists["semantic"] = [r["id"] for r in conn.execute(
            f"""SELECT m.moment_id AS id, 1 - (m.embedding <=> %(vector)s) AS cosine {MOMENT_FROM}
                {_where(where + ["m.embedding IS NOT NULL", "m.embedding_model = %(model)s"])}
                AND 1 - (m.embedding <=> %(vector)s) >= %(floor)s ORDER BY m.embedding <=> %(vector)s, m.moment_id LIMIT %(limit)s""",
            {**args, "vector": np.asarray(vector, dtype=np.float32), "model": model, "floor": min_cosine, "limit": limit})]
    return lists


def chunk_lists(conn, text: str, vector, filters: SearchFilters, *, model: str, limit: int, min_cosine: float) -> dict[str, list[str]]:
    where, args = chunk_conditions(filters)
    from .rows import CHUNK_FROM
    lists: dict[str, list[str]] = {"phrase": [], "semantic": []}
    lists["phrase"] = [r["id"] for r in conn.execute(
        f"""SELECT k.chunk_id AS id, ts_rank_cd(k.tsv, q.query) AS rank {CHUNK_FROM}
            CROSS JOIN websearch_to_tsquery('english', %(text)s) AS q(query)
            {_where(where + ["k.tsv @@ q.query"])} ORDER BY rank DESC, k.chunk_id LIMIT %(limit)s""",
        {**args, "text": text, "limit": limit})]
    if vector is not None:
        lists["semantic"] = [r["id"] for r in conn.execute(
            f"""SELECT k.chunk_id AS id, 1 - (k.embedding <=> %(vector)s) AS cosine {CHUNK_FROM}
                {_where(where + ["k.embedding IS NOT NULL", "k.embedding_model = %(model)s"])}
                AND 1 - (k.embedding <=> %(vector)s) >= %(floor)s ORDER BY k.embedding <=> %(vector)s, k.chunk_id LIMIT %(limit)s""",
            {**args, "vector": np.asarray(vector, dtype=np.float32), "model": model, "floor": min_cosine, "limit": limit})]
    return lists


def fuse(ranked: list[tuple[str, str, list[str]]], *, rrf_k: int, k: int) -> list[dict]:
    """Reciprocal rank fusion. `ranked` is [(kind, method, ids best first)]; the answer is the best `k`, each with its fused
    score and the methods that found it, ordered by score, then moments before chunks, then id (so a tie is stable)."""
    hits: dict[tuple[str, str], dict] = {}
    for kind, method, ids in ranked:
        for rank, ident in enumerate(ids, 1):
            hit = hits.setdefault((kind, ident), {"kind": kind, "id": ident, "score": 0.0, "matched_by": []})
            hit["score"] += 1.0 / (rrf_k + rank)
            if method not in hit["matched_by"]:
                hit["matched_by"].append(method)
    for hit in hits.values():
        hit["matched_by"].sort(key=("phrase", "semantic").index)
    return sorted(hits.values(), key=lambda h: (-h["score"], KIND_ORDER[h["kind"]], h["id"]))[:k]


def search(conn, text: str, vector, filters: SearchFilters, *, k: int, scope: str, topic_id: str | None, model: str, rrf_k: int,
           candidates: int, min_cosine: float, chunk_query: str | None = None) -> list[dict]:
    """The fused hits, best first. `vector` may be None: then the words alone rank. `chunk_query` is the text with the glossary
    applied, which is what chunks' search copy was written with (plan 1.B12)."""
    ranked: list[tuple[str, str, list[str]]] = []
    if scope in ("moments", "all"):
        for method, ids in moment_lists(conn, text, vector, filters, topic_id=topic_id, model=model, limit=candidates,
                                        min_cosine=min_cosine).items():
            ranked.append(("moment", method, ids))
    # A chunk has no type and no topic: a filter on either leaves no chunk that can satisfy it.
    if scope in ("chunks", "all") and not filters.moment_only():
        for method, ids in chunk_lists(conn, chunk_query or text, vector, filters, model=model, limit=candidates, min_cosine=min_cosine).items():
            ranked.append(("chunk", method, ids))
    return fuse(ranked, rrf_k=rrf_k, k=k)
