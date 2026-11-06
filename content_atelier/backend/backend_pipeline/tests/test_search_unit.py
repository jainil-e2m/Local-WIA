"""Search without a database: the Citation shape and the recording link, the filters, the fusion, the query vector and the routes' guards."""
from __future__ import annotations

import tempfile
from datetime import UTC, datetime

import pytest
from fastapi.routing import APIRoute
from pydantic import ValidationError

from backend_pipeline.config import Settings
from backend_pipeline.search import hybrid, query
from backend_pipeline.search.api import SearchRequest
from backend_pipeline.search.citation import Citation, CitationError, chunk_citation, locate_quote, moment_citation, recording_url
from backend_pipeline.search.filters import DEFAULT_CONSENT, SearchFilters, chunk_conditions, csv_values, moment_conditions
from backend_pipeline.storage_config import StorageSettings
from backend_pipeline.tests.ledger_fixtures import Embedder


@pytest.fixture(autouse=True)
def fresh_cache():
    query._cache.clear()
    yield
    query._cache.clear()


# ---- the Citation shape -------------------------------------------------------------------------------------------------------


def test_the_citation_has_exactly_the_agreed_fields():
    assert list(Citation.model_fields) == [
        "document_id", "document_title", "source_type", "call_type", "passage_ids", "start", "end", "start_ms", "end_ms", "speaker_label",
        "speaker_id", "speaker_role", "client_id", "client_name", "consent_status", "occurred_at", "recording_url", "quote"]
    schema = Citation.model_json_schema(mode="serialization")
    assert set(schema["required"]) == set(Citation.model_fields), "every field is required, so generated types need no undefined"


def test_a_recording_link_comes_only_from_what_the_document_holds_and_is_always_http():
    assert recording_url("fathom", "https://fathom.video/share/abc", {}) == "https://fathom.video/share/abc"
    assert recording_url("fathom", None, {"provider_metadata": {"share_url": "https://fathom.video/share/def"}}) == "https://fathom.video/share/def"
    assert recording_url("fathom", None, {"provider_metadata": {"url": "http://example.test/rec"}}) == "http://example.test/rec"
    assert recording_url("zoom", None, {}) is None and recording_url("zoom", None, None) is None
    assert recording_url("fathom", "javascript:alert(1)", {}) is None and recording_url("fathom", "ftp://x/y", {}) is None
    assert recording_url("fathom", "https://x.test/a b", {}) is None and recording_url("fathom", "https://x.test/" + "a" * 2001, {}) is None
    slack = {"slack": {"workspace": "T03P5A3L1DK", "channel": "C082DURRJ2U", "thread_ts": "1760000000.000100"}}
    assert recording_url("slack", None, slack) == "https://app.slack.com/client/T03P5A3L1DK/C082DURRJ2U/thread/C082DURRJ2U-1760000000.000100"
    assert recording_url("slack", "https://wia.slack.com/archives/C1/p1", slack) == "https://wia.slack.com/archives/C1/p1", "a permalink wins"
    assert recording_url("slack", None, {"slack": {"workspace": "", "channel": "C082DURRJ2U", "thread_ts": "1760000000.000100"}}) is None
    assert recording_url("slack", None, {"slack": {"workspace": "T03P5A3L1DK", "channel": "../x", "thread_ts": "1.1"}}) is None
    assert recording_url("zoom", None, slack) is None, "a Slack link is built only for a Slack document"


def test_the_quote_is_located_in_the_anchor_that_holds_it():
    anchors = [{"passage_id": "p1", "start": 0, "end": 20, "text": "Dana: nothing here.", "start_ms": 0, "end_ms": 5},
               {"passage_id": "p2", "start": 21, "end": 60, "text": "Dana: We reply in five minutes.", "start_ms": 9, "end_ms": 20}]
    anchor, start, end = locate_quote(anchors, "We reply in five minutes.")
    assert anchor["passage_id"] == "p2" and (start, end) == (27, 52)
    with pytest.raises(CitationError):
        locate_quote(anchors, "Something never said")
    with pytest.raises(CitationError):
        locate_quote(anchors, "")


def row(**kw):
    base = {"moment_body": {"quote": "We reply in five minutes."}, "document_id": "d1", "document_title": "A call", "source_type": "fathom",
            "call_type": "client_1to1", "speaker_label": "Dana", "speaker_id": "p1", "speaker_role": "client", "client_id": "c1",
            "client_name": "Acme", "consent_status": "cleared", "occurred_at": None,
            "document_occurred_at": datetime(2026, 3, 1, tzinfo=UTC), "source_url": None, "source_metadata": {}}
    return {**base, **kw}


def test_a_moment_citation_needs_a_document_and_a_located_quote():
    anchors = [{"passage_id": "p2", "start": 21, "end": 60, "text": "Dana: We reply in five minutes.", "start_ms": 9, "end_ms": None}]
    citation = moment_citation(row(), anchors)
    assert citation.occurred_at == datetime(2026, 3, 1, tzinfo=UTC), "the document's date when the moment has none"
    assert (citation.start, citation.end, citation.start_ms, citation.end_ms, citation.passage_ids) == (27, 52, 9, None, ["p2"])
    with pytest.raises(CitationError):
        moment_citation(row(document_id=None), anchors)
    with pytest.raises(CitationError):
        moment_citation(row(), [])
    with pytest.raises(CitationError):
        moment_citation(row(moment_body={}), anchors)


def test_a_chunk_citation_is_the_chunks_passage_range_and_never_cleared():
    chunk = {"transcript_id": "d1", "document_title": "A call", "source_type": "zoom", "call_type": "client_1to1", "client_id": "c1",
             "client_name": "Acme", "client_consent": "may_name", "occurred_at": None, "document_occurred_at": None, "source_url": None,
             "source_metadata": {}, "speaker_map": {"Whitney": {"role": "staff", "person_id": "p9"}},
             "passage_refs": [{"passage_id": "a", "start": 0, "end": 10, "overlap": True}, {"passage_id": "b", "start": 11, "end": 30}]}
    passages = [{"speaker": "Dana", "start_ms": 0, "end_ms": 4}, {"speaker": "Whitney", "start_ms": 5, "end_ms": 9}]
    citation = chunk_citation(chunk, passages, "the original text of that range")
    assert (citation.start, citation.end, citation.start_ms, citation.end_ms) == (0, 30, 0, 9)
    assert citation.speaker_label == "Whitney" and citation.speaker_role == "staff", "the first turn that is not the overlap"
    assert citation.consent_status == "anonymise", "a chunk is never cleared, even for a client who may be named"
    assert chunk_citation({**chunk, "client_consent": "no_use"}, passages, "x").consent_status == "do_not_use"
    with pytest.raises(CitationError):
        chunk_citation(chunk, passages[:1], "x")


# ---- the filters ----------------------------------------------------------------------------------------------------------------


def test_the_filters_default_consent_hides_do_not_use_and_dates_need_an_offset():
    assert SearchFilters().consent == list(DEFAULT_CONSENT) and "do_not_use" not in DEFAULT_CONSENT
    assert SearchFilters(consent_status=["do_not_use"]).consent == ["do_not_use"]
    assert SearchFilters(consent_status=[]).consent_defaulted is True, "an empty list is the default, not 'nothing'"
    with pytest.raises(ValidationError):
        SearchFilters(date_from=datetime(2026, 3, 9))
    with pytest.raises(ValidationError):
        SearchFilters(date_from=datetime(2026, 3, 9, tzinfo=UTC), date_to=datetime(2026, 3, 9, tzinfo=UTC))
    with pytest.raises(ValidationError):
        SearchFilters(moment_type=["gossip"])
    with pytest.raises(ValidationError):
        SearchFilters(unknown_filter="x")
    assert SearchFilters(speaker_role=["client", "client"]).speaker_role == ["client"]
    assert SearchFilters(moment_type=["testimonial"]).moment_only() == ["moment_type"] and SearchFilters(topic_id="t").moment_only() == ["topic_id"]


def test_the_conditions_only_ever_search_verified_current_moments_of_included_documents():
    where, args = moment_conditions(SearchFilters(), topic_id=None)
    assert {"m.quote_verified", "m.is_current", "t.included", "t.canonical_document_id IS NULL"} <= set(where)
    assert args["consent"] == list(DEFAULT_CONSENT)
    where, args = moment_conditions(SearchFilters(client_id="c", moment_type=["result"], topic_id="old"), topic_id="new")
    assert args["topic_id"] == "new" and args["client_id"] == "c" and args["moment_type"] == ["result"]
    chunk_where, chunk_args = chunk_conditions(SearchFilters(speaker_role=["client"], moment_type=["result"]))
    assert "k.is_current" in chunk_where and "moment_type" not in chunk_args and chunk_args["speaker_role"] == ["client"]


def test_comma_separated_filters_are_checked_against_their_closed_set():
    assert csv_values("speaker_role", "client, prospect,client", ("client", "prospect", "staff")) == ["client", "prospect"]
    assert csv_values("speaker_role", None, ("client",)) == [] and csv_values("speaker_role", "", ("client",)) == []
    with pytest.raises(ValueError, match="gossip"):
        csv_values("speaker_role", "client,gossip", ("client",))


# ---- the fusion ---------------------------------------------------------------------------------------------------------------------


def test_reciprocal_rank_fusion_adds_the_reciprocals_and_breaks_ties_by_kind_then_id():
    ranked = [("moment", "phrase", ["a", "b", "c"]), ("moment", "semantic", ["b", "a", "d"]), ("chunk", "phrase", ["a"])]
    hits = hybrid.fuse(ranked, rrf_k=60, k=10)
    scores = {(h["kind"], h["id"]): h["score"] for h in hits}
    assert scores[("moment", "a")] == pytest.approx(1 / 61 + 1 / 62) and scores[("moment", "b")] == pytest.approx(1 / 62 + 1 / 61)
    assert [(h["kind"], h["id"]) for h in hits][:3] == [("moment", "a"), ("moment", "b"), ("chunk", "a")], "tie: id order, then the chunk by its score"
    assert hits[0]["matched_by"] == ["phrase", "semantic"] and next(h for h in hits if h["id"] == "c")["matched_by"] == ["phrase"]
    assert len(hybrid.fuse(ranked, rrf_k=60, k=2)) == 2
    assert hybrid.fuse([("moment", "phrase", ["a"])], rrf_k=1, k=1)[0]["score"] == pytest.approx(0.5), "a smaller constant weighs ranks more"
    assert hybrid.fuse([], rrf_k=60, k=5) == []


def test_the_request_rejects_what_it_cannot_search():
    assert SearchRequest(text="  reply   fast ").text == "reply fast"
    for bad in ({"text": ""}, {"text": "x", "k": 0}, {"text": "x", "k": 51}, {"text": "x", "scope": "everywhere"}, {"text": "x", "extra": 1},
                {"text": "x", "scope": "chunks", "filters": {"moment_type": ["result"]}}, {"text": "x", "scope": "chunks", "filters": {"topic_id": "t"}}):
        with pytest.raises(ValidationError):
            SearchRequest(**bad)
    assert SearchRequest(text="x", scope="all", filters={"moment_type": ["result"]}).scope == "all"


# ---- the query vector ----------------------------------------------------------------------------------------------------------------


def storage(**kw):
    # No database: the call record goes to a file beside the artifacts (llm/runs.py), so nothing here waits on a connection.
    return StorageSettings(database_url="", artifact_root=tempfile.mkdtemp(prefix="atelier-search-"), **kw)


def test_a_query_is_not_embedded_when_the_encoding_catch_is_off_and_the_answer_says_why():
    answer = query.embed_query("reply fast", models=Settings(), storage=storage())
    assert answer.status == "unavailable" and answer.vector is None and "ATELIER_ALLOW_ENCODING" in answer.detail


def test_a_query_without_a_key_or_a_plan_is_unavailable_never_an_error(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ATELIER_RUN_PLAN_ID", raising=False)
    answer = query.embed_query("reply fast", models=Settings(), storage=storage(encoding_enabled=True))
    assert answer.status == "unavailable" and "OPENAI_API_KEY" in answer.detail
    monkeypatch.setenv("OPENAI_API_KEY", "not-a-real-key")
    answer = query.embed_query("reply fast", models=Settings(), storage=storage(encoding_enabled=True))
    assert answer.status == "unavailable" and "run plan" in answer.detail, "no plan: the provider refuses before anything is sent"


def test_a_query_is_embedded_once_and_a_repeat_is_free(monkeypatch):
    embedder = Embedder()
    monkeypatch.setattr(query, "make_provider", lambda models, store: embedder)
    first = query.embed_query("reply fast", models=Settings(), storage=storage(encoding_enabled=True))
    again = query.embed_query("reply fast", models=Settings(), storage=storage(encoding_enabled=True))
    assert first.status == again.status == "used" and first.vector == again.vector and embedder.embedded == ["reply fast"]
    query.embed_query("another question", models=Settings(), storage=storage(encoding_enabled=True))
    assert embedder.embedded == ["reply fast", "another question"]


def test_a_provider_that_returns_a_bad_vector_is_unavailable(monkeypatch):
    class Bad(Embedder):
        def embed(self, *, text, fingerprint):
            return [0.0] * 1536, {}
    monkeypatch.setattr(query, "make_provider", lambda models, store: Bad())
    assert query.embed_query("x", models=Settings(), storage=storage(encoding_enabled=True)).status == "unavailable"


# ---- the stages ---------------------------------------------------------------------------------------------------------------------------


def test_the_two_stages_run_on_the_bulk_queue_with_a_timeout_and_are_never_retried_automatically():
    from backend_pipeline.jobs import policy
    from backend_pipeline.llm import JSON_STAGES
    from backend_pipeline.search.jobs import STAGES
    assert STAGES == {"moment_embedding", "topic_assignment"}
    for stage in STAGES:
        assert policy.queue_for(stage) == "bulk" and policy.placement(stage) == {"executor": "rq", "queue": "bulk"}
        assert policy.timeout_for(stage) == 3600 and stage in policy.NEVER_AUTO_RETRY, "a lost paid answer is inspected, not asked for again"
    assert "topic_assignment" in JSON_STAGES, "the live provider accepts the topic picker as a JSON stage"
    assert Settings().reasoning_effort_for("topic_assignment") == Settings().reasoning_effort_for("document_classification")


def test_the_search_settings_are_registered_with_their_documented_defaults_and_bounds():
    from backend_pipeline import settings_store
    expected = {"search.rrf_k": 60, "search.candidates": 100, "search.semantic_min_cosine": 0.0, "moments.embedding.batch_size": 32,
                "topics.candidates": 5, "topics.attach_similarity": 0.80}
    for key, default in expected.items():
        assert settings_store.default(key) == default, key
    assert settings_store.definition("topics.attach_similarity").lo == 0.5 and settings_store.definition("search.rrf_k").lo == 1
    for key, bad in (("search.rrf_k", 0), ("moments.embedding.batch_size", 0), ("topics.attach_similarity", 0.2), ("search.semantic_min_cosine", 1.5)):
        with pytest.raises(settings_store.SettingError):
            settings_store.coerce(settings_store.definition(key), bad)


# ---- the routes ---------------------------------------------------------------------------------------------------------------------------


def app_routes():
    from backend_pipeline.api import app
    return {(m, r.path): r for r in app.routes if isinstance(r, APIRoute) for m in r.methods if m not in {"HEAD", "OPTIONS"}}


PHASE_2_ROUTES = [
    ("POST", "/storage/search"), ("GET", "/storage/moments"), ("GET", "/storage/moments/facets"), ("GET", "/storage/moments/{moment_id}"),
    ("POST", "/storage/moments/{moment_id}/topics"), ("GET", "/storage/topics"), ("GET", "/storage/topics/{topic_id}"),
    ("POST", "/storage/topics/{topic_id}/rename"), ("POST", "/storage/topics/{topic_id}/merge"),
    ("POST", "/storage/topics/{topic_id}/block"), ("POST", "/storage/topics/{topic_id}/unblock"),
    ("GET", "/storage/documents/extraction-health")]


def test_every_phase_2_route_is_mounted_guarded_and_in_the_openapi_document():
    from backend_pipeline.api import app
    routes, spec = app_routes(), app.openapi()
    for method, path in PHASE_2_ROUTES:
        assert (method, path) in routes, f"{method} {path} is not mounted"
        operation = spec["paths"][path][method.lower()]
        schema = operation["responses"]["200"]["content"]["application/json"]["schema"]
        assert schema.get("$ref"), f"{method} {path} publishes no response model"
        names = [getattr(call, "__name__", "") for call in _calls(routes[(method, path)].dependant)]
        assert "trusted" in names, f"{method} {path} does not check the shared secret"
        if method == "POST":
            assert "current_user" in names, f"{method} {path} does not resolve the verified email"
        else:
            assert "optional_user" in names, f"{method} {path} does not resolve the caller's roles"
    assert ("POST", "/storage/search/transcripts") in routes, "the earlier text search is kept"
    paths = [r.path for r in app.routes if isinstance(r, APIRoute)]
    assert paths.index("/storage/moments/facets") < paths.index("/storage/moments/{moment_id}"), "facets must not be read as a moment id"
    assert paths.index("/storage/documents/extraction-health") < paths.index("/storage/documents/{transcript_id}")


def _calls(dependant):
    for dep in dependant.dependencies:
        yield dep.call
        yield from _calls(dep)


def test_the_response_models_are_strict_so_generated_types_need_no_undefined():
    from backend_pipeline.api import app
    schemas = app.openapi()["components"]["schemas"]
    for name in ("SearchResponse", "SearchHit", "Citation", "MomentSummary", "ChunkSummary", "FiltersApplied", "MomentList", "MomentFacets",
                 "MomentDetail", "TopicList", "TopicDetail", "ExtractionHealth"):
        schema = schemas[name]
        assert set(schema["required"]) == set(schema["properties"]), name
