"""Phase 2 end to end on a real database, offline: documents are extracted one by one with the scene prompt, their scenes are
checked, embedded under the archive's contract, and found by search with a citation that points into the original text.
The pieces have their own suites; this one proves they fit (a moment written by the extraction job is what search reads)."""
from __future__ import annotations

import json

import pytest

from backend_pipeline.documents import select
from backend_pipeline.jobs.executor import run_job
from backend_pipeline.moments import queue
from backend_pipeline.moments.scenes import SCENE_V2_PROFILE
from backend_pipeline.search.api import SearchRequest, SearchResponse, run_search
from backend_pipeline.search.query import QueryVector
from backend_pipeline.tests.ledger_fixtures import Embedder, embed_everything, vector_for
from backend_pipeline.tests.moments_fixtures import (MARK, ScriptedProvider, import_documents, prepare_reference, standard_scripts)
from backend_pipeline.tests.platform_db import platform_setup, platform_url  # noqa: F401 (fixtures)


@pytest.fixture
def archive(platform_setup):  # noqa: F811
    repo, models, tmp_path = platform_setup
    prepare_reference(repo)
    docs = import_documents(repo, models, tmp_path)
    with repo.connection() as conn:
        rows = select.by_set(conn, [d["transcript_id"] for d in docs.values()])
    result = queue.queue_extraction(repo, models, rows, mode="synthetic", actor="tester", queue="bulk", profile=SCENE_V2_PROFILE)
    provider = ScriptedProvider(standard_scripts())
    with repo.connection() as conn:
        jobs = conn.execute("SELECT job_id FROM pipeline_jobs WHERE run_id=%s", (result["run_id"],)).fetchall()
    for job in jobs:
        run_job(job["job_id"], storage=repo.settings, models=models, provider=provider, successors=False)
    return repo, models, docs


def ask(repo, models, text, **filters):
    request = SearchRequest(text=text, k=5, filters=filters)
    answer = run_search(repo, models, request, vector=QueryVector(vector_for(text), "used"))
    return json.loads(SearchResponse.model_validate(answer).model_dump_json())  # what the API sends


def test_what_extraction_writes_is_what_embedding_and_search_read(archive):
    repo, models, docs = archive
    embedder = Embedder(models.embedding_model)
    queued = embed_everything(repo, models, embedder)
    with repo.connection() as conn:
        verified = conn.execute("SELECT count(*) n FROM key_moments WHERE quote_verified AND is_current").fetchone()["n"]
        unverified = conn.execute("SELECT count(*) n FROM key_moments WHERE NOT quote_verified").fetchone()["n"]
        embedded = conn.execute("SELECT count(*) n FROM key_moments WHERE embedding IS NOT NULL").fetchone()["n"]
    assert verified == 4 and unverified == 1, "documents A and B yielded their scenes; the unbindable quote is a record"
    assert queued["queued"] == verified and embedded == verified, "every verified moment, and only those, is embedded"
    spent = len(embedder.embedded)
    assert embed_everything(repo, models, embedder)["queued"] == 0 and len(embedder.embedded) == spent, "running again embeds nothing new"

    # A known moment is found by its exact phrase in the top five, with a citation that points into the original text.
    found = ask(repo, models, "bookings in March")
    top = found["hits"][0]
    assert top["kind"] == "moment" and "phrase" in top["matched_by"] and top["moment"]["quote"] == "We had 45 bookings in March."
    citation = top["citation"]
    assert citation["document_id"] == docs["A"]["transcript_id"] and citation["speaker_role"] == "client"
    with repo.connection() as conn:
        original = conn.execute("SELECT original_text FROM transcripts WHERE transcript_id=%s", (citation["document_id"],)).fetchone()["original_text"]
    assert original[citation["start"]:citation["end"]] == citation["quote"], "the citation is exact"
    assert all(h["citation"]["document_id"] and h["citation"]["consent_status"] for h in found["hits"]), "every hit has a citation"

    # Staff praise is not a testimonial, so the type filter does not find it; the client's own words are.
    testimonials = ask(repo, models, "dreading Mondays", moment_type=["testimonial"])
    quotes = [h["moment"]["quote"] for h in testimonials["hits"]]
    assert quotes == ["I stopped dreading Mondays after the form changed."]
    praise = ask(repo, models, "Dana loves the new inquiry form")
    assert praise["hits"][0]["moment"]["moment_type"] == "observation" and praise["hits"][0]["moment"]["evidence_kind"] == "team_report"

    # The unverified record is never returned, even for its own words.
    assert not [h for h in ask(repo, models, "Nobody said this at all")["hits"] if h["moment"] and "Nobody" in h["moment"]["quote"]]
    assert MARK["A"]  # the marker documents are the ones above
