"""2.B3 and 2.B6 on a real database: `POST /search` over verified moments and chunks, with filters and one Citation shape.

Synthetic moments; the query is embedded by an offline provider. No network."""
from __future__ import annotations

from datetime import timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend_pipeline.search import query
from backend_pipeline.storage_api import router
from backend_pipeline.tests.ledger_fixtures import (NOW, Embedder, embed_everything, ledger, load_document, make_chunk,  # noqa: F401
                                                    make_document, make_moment)
from backend_pipeline.tests.platform_db import APPROVER, platform_setup, platform_url  # noqa: F401 (fixtures)

CITATION_FIELDS = {"document_id", "document_title", "source_type", "call_type", "passage_ids", "start", "end", "start_ms", "end_ms",
                   "speaker_label", "speaker_id", "speaker_role", "client_id", "client_name", "consent_status", "occurred_at",
                   "recording_url", "quote"}


@pytest.fixture(autouse=True)
def fresh_query_cache():
    query._cache.clear()
    yield
    query._cache.clear()


@pytest.fixture
def api(ledger, monkeypatch):  # noqa: F811
    repo, models, tmp_path, embedder = ledger
    embed_everything(repo, models, embedder)
    with repo.connection() as conn:
        for chunk_id, document, first, last in (("chunk_acme_a", "doc_acme_1", 0, 1), ("chunk_acme_b", "doc_acme_1", 2, 4),
                                                ("chunk_beta_a", "doc_beta_1", 0, 3), ("chunk_gamma_a", "doc_gamma_1", 0, 1)):
            make_chunk(conn, load_document(conn, document), chunk_id, first, last)
    monkeypatch.setattr(query, "make_provider", lambda models, storage: embedder)
    app = FastAPI()
    app.include_router(router(repo.settings))
    http = TestClient(app)

    def search(text, *, k=10, scope="moments", email=APPROVER, **filters):
        response = http.post("/storage/search", json={"text": text, "k": k, "scope": scope, "filters": filters},
                             headers={"Authorization": "Bearer test-secret", "X-Atelier-Actor": email, "X-Atelier-Email": email})
        return response
    return search, repo, embedder, http


def ids(answer, kind="moment"):
    return [h[kind]["moment_id" if kind == "moment" else "chunk_id"] for h in answer["hits"] if h["kind"] == kind]


def test_a_known_moment_is_found_by_its_phrase_and_by_a_paraphrase_in_the_top_five(api):
    search, *_ = api
    exact = search("reply to every inquiry within five minutes").json()
    assert exact["query_embedding_status"] == "used" and ids(exact)[0] == "m_reply"
    assert "phrase" in exact["hits"][0]["matched_by"] and exact["hits"][0]["moment"]["moment_type"] == "result"
    paraphrase = search("how quickly should we respond to new leads").json()
    found = ids(paraphrase)
    assert "m_reply" in found[:5] and found.index("m_reply") < found.index("m_pricing_beta") and found.index("m_reply") < found.index("m_price")
    hit = next(h for h in paraphrase["hits"] if h["moment"]["moment_id"] == "m_reply")
    assert hit["matched_by"] == ["semantic"], "no word of the question is in the quote: only the meaning matched"
    # Pricing is a different subject: the same kind of question about it ranks the pricing moments first.
    assert set(ids(search("what do people think about the price").json())[:2]) == {"m_pricing_beta", "m_price"}


def test_without_the_meaning_only_the_words_rank_and_the_answer_says_so(api, monkeypatch):
    search, repo, embedder, _ = api
    embedder.fail_embeddings = True
    query._cache.clear()
    answer = search("reply to every inquiry within five minutes").json()
    assert answer["query_embedding_status"] == "unavailable" and "OPENAI_API_KEY" in answer["query_embedding_detail"]
    assert ids(answer) == ["m_reply"] and answer["hits"][0]["matched_by"] == ["phrase"], "text-only, never a silent failure"
    nothing = search("how quickly should we respond to new leads").json()
    assert nothing["hits"] == [] and nothing["query_embedding_status"] == "unavailable"


def test_a_client_filter_returns_only_that_clients_hits_for_moments_and_chunks(api):
    search, *_ = api
    for scope in ("moments", "chunks", "all"):
        answer = search("price cost reply calendar love", scope=scope, k=50, client_id="client_beta").json()
        assert answer["hits"], scope
        assert {h["citation"]["client_id"] for h in answer["hits"]} == {"client_beta"}
        assert {h["citation"]["client_name"] for h in answer["hits"]} == {"Beta Bridal"}
    assert {h["citation"]["client_id"] for h in search("reply", k=50).json()["hits"]} > {"client_acme"}


def test_every_hit_carries_a_complete_citation_that_points_into_the_original_text(api):
    search, repo, *_ = api
    answer = search("reply price calendar love onboarding speed", scope="all", k=50, consent_status=["cleared", "anonymise", "internal_only",
                                                                                                       "do_not_use"]).json()
    kinds = {h["kind"] for h in answer["hits"]}
    assert kinds == {"moment", "chunk"} and answer["hits_withheld"] == 0
    with repo.connection() as conn:
        texts = {r["transcript_id"]: r for r in conn.execute("SELECT transcript_id, original_text, source_url FROM transcripts")}
    for hit in answer["hits"]:
        citation = hit["citation"]
        assert set(citation) == CITATION_FIELDS
        original = texts[citation["document_id"]]["original_text"]
        assert original[citation["start"]:citation["end"]] == citation["quote"], hit["kind"]
        assert citation["passage_ids"] and citation["document_title"] and citation["source_type"] and citation["consent_status"]
        assert citation["speaker_role"] in {"staff", "client", "prospect", "vendor", "outside", "ai_agent", "unknown"}
        assert citation["occurred_at"] and 0 <= citation["start"] < citation["end"] <= len(original)
        if citation["source_type"] == "slack":
            assert citation["start_ms"] is None and citation["end_ms"] is None
        else:
            assert citation["start_ms"] is not None and citation["end_ms"] >= citation["start_ms"]
        if hit["kind"] == "moment":
            assert hit["moment"]["quote"] == citation["quote"] and hit["chunk"] is None
        else:
            assert hit["chunk"]["header"].startswith("Call: ") and hit["moment"] is None
    reply = next(h for h in answer["hits"] if h["kind"] == "moment" and h["moment"]["moment_id"] == "m_reply")["citation"]
    assert reply["speaker_label"] == "Dana Lee" and reply["speaker_id"] == "person_dana" and reply["speaker_role"] == "client"
    assert reply["consent_status"] == "cleared" and reply["client_name"] == "Acme Weddings"
    assert reply["recording_url"] == "https://fathom.video/share/acme-1" and reply["passage_ids"] == ["doc_acme_1:span:1"]
    assert (reply["start_ms"], reply["end_ms"]) == (20_000, 35_000)
    slack = next(h for h in answer["hits"] if h["kind"] == "moment" and h["moment"]["moment_id"] == "m_slack")["citation"]
    assert slack["recording_url"] == "https://app.slack.com/client/T03P5A3L1DK/C082DURRJ2U/thread/C082DURRJ2U-1760000000.000100"
    zoom = next(h for h in answer["hits"] if h["kind"] == "moment" and h["moment"]["moment_id"] == "m_pricing_beta")["citation"]
    assert zoom["recording_url"] is None, "a Zoom transcript has no link, and none is invented"


def test_do_not_use_is_hidden_unless_it_is_asked_for_by_name(api):
    search, *_ = api
    default = search("onboarding kickoff we are grateful", scope="all", k=50).json()
    assert "m_gamma" not in ids(default) and default["filters_applied"]["consent_defaulted"] is True
    assert default["filters_applied"]["consent_status"] == ["cleared", "anonymise", "internal_only"]
    assert not [h for h in default["hits"] if h["citation"]["consent_status"] == "do_not_use"], "chunks of a no_use client are hidden too"
    asked = search("onboarding kickoff we are grateful", scope="all", k=50, consent_status=["do_not_use"]).json()
    assert ids(asked) == ["m_gamma"] and asked["filters_applied"]["consent_defaulted"] is False
    assert ids(asked, "chunk") == ["chunk_gamma_a"] and {h["citation"]["consent_status"] for h in asked["hits"]} == {"do_not_use"}
    assert {h["citation"]["consent_status"] for h in search("reply price", k=50, consent_status=["cleared"]).json()["hits"]} == {"cleared"}


def test_an_unverified_or_superseded_moment_is_never_returned(api):
    search, repo, embedder, _ = api
    for text in ("We answer every lead in minutes and bookings tripled", "An older extraction of the reply scene",
                 "Unbindable draft about replies", "reply inquiry minutes bookings leads"):
        answer = search(text, scope="moments", k=50).json()
        assert not {"m_unverified", "m_old"} & set(ids(answer)), text
    assert "m_unverified" not in ids(search("tripled", k=50, consent_status=["cleared", "anonymise", "internal_only", "do_not_use"]).json())


def test_the_new_moment_types_filter_moments_in_post_search(api):
    search, repo, embedder, _ = api
    with repo.connection() as conn:
        document = load_document(conn, "doc_beta_1")
        make_moment(conn, "m_question", document, 0, "Where do prospects drop off?", record="WIA asked where prospects drop off",
                    moment_type="question", client_id="client_beta", speaker=("Whitney Hodges", "staff", "person_whit"),
                    occurred_at=NOW - timedelta(days=40))
        make_moment(conn, "m_data", document, 1, "Our pricing page scares people because the cost is hidden.", record="A figure",
                    moment_type="data_point", client_id="client_beta", occurred_at=NOW - timedelta(days=40))
    from backend_pipeline.config import Settings
    embed_everything(repo, Settings(), embedder)
    expected = {"testimonial": {"m_praise_beta", "m_gamma"}, "soundbite": {"m_slack"}, "teaching": {"m_staff"}, "question": {"m_question"},
                "data_point": {"m_data"}}
    everything = ["cleared", "anonymise", "internal_only", "do_not_use"]
    for moment_type, wanted in expected.items():
        answer = search("reply price calendar love onboarding speed pricing prospects", k=50, moment_type=[moment_type],
                        consent_status=everything).json()
        assert set(ids(answer)) == wanted and {h["moment"]["moment_type"] for h in answer["hits"]} == {moment_type}, moment_type
    two = search("reply price calendar love", k=50, moment_type=["result", "objection"]).json()
    assert {h["moment"]["moment_type"] for h in two["hits"]} == {"result", "objection"}
    assert search("reply", moment_type=["gossip"]).status_code == 422


def test_the_filters_combine_and_a_window_needs_explicit_offsets(api):
    search, repo, *_ = api
    base = "reply price calendar love onboarding speed"
    assert set(ids(search(base, k=50, source_type="zoom").json())) == {"m_pricing_beta", "m_praise_beta"}
    assert set(ids(search(base, k=50, call_type="office_hours").json())) == {"m_pricing_beta", "m_praise_beta"}
    assert set(ids(search(base, k=50, speaker_role=["staff"]).json())) == {"m_staff", "m_slack"}
    assert set(ids(search(base, k=50, document_ids=["doc_beta_1"]).json())) == {"m_pricing_beta", "m_praise_beta"}
    window = search(base, k=50, date_from=(NOW - timedelta(days=12)).isoformat(), date_to=(NOW - timedelta(days=3)).isoformat()).json()
    assert set(ids(window)) == {"m_reply", "m_price", "m_staff"} and "m_slack" not in ids(window), "[from, to): the end is open"
    assert search(base, date_from="2026-03-09T00:00:00").status_code == 422, "a naive time would be read in the server's zone"
    assert search(base, date_from=NOW.isoformat(), date_to=(NOW - timedelta(days=1)).isoformat()).status_code == 422
    both = search(base, k=50, client_id="client_acme", speaker_role=["client"], moment_type=["result"]).json()
    assert ids(both) == ["m_reply"]


def test_a_topic_filter_follows_a_merge(api):
    search, repo, *_ = api
    from backend_pipeline.moments import topics
    with repo.connection() as conn:
        a = topics.create_topic(conn, "Reply speed", "How fast the team replies", origin="person", created_by="t")
        b = topics.create_topic(conn, "Lead response", "Responding to leads", origin="person", created_by="t")
        topics.link(conn, "m_reply", a["topic_id"], assigned_by="person")
        topics.link(conn, "m_slack", b["topic_id"], assigned_by="person")
        topics.merge(conn, a["topic_id"], b["topic_id"], APPROVER)
    text = "reply price calendar love speed"
    assert set(ids(search(text, k=50, topic_id=b["topic_id"]).json())) == {"m_reply", "m_slack"}
    assert set(ids(search(text, k=50, topic_id=a["topic_id"]).json())) == {"m_reply", "m_slack"}, "an old link to the merged topic still works"
    assert search(text, k=50, topic_id="topic_unknown").json()["hits"] == []
    assert {t["name"] for h in search(text, k=50, topic_id=b["topic_id"]).json()["hits"] for t in h["moment"]["topics"]} == {"Lead response"}


def test_chunks_have_no_type_or_topic(api):
    search, *_ = api
    assert search("reply", scope="chunks", moment_type=["result"]).status_code == 422
    assert search("reply", scope="chunks", topic_id="topic_x").status_code == 422
    mixed = search("reply price calendar love", scope="all", k=50, moment_type=["result"]).json()
    assert {h["kind"] for h in mixed["hits"]} == {"moment"} and mixed["filters_applied"]["kinds"] == ["moment"]
    chunks = search("reply inquiry minutes", scope="chunks", k=5).json()
    assert chunks["filters_applied"]["kinds"] == ["chunk"] and ids(chunks, "chunk")[0] == "chunk_acme_a"
    top = chunks["hits"][0]
    assert top["chunk"]["text"].startswith("Whitney Hodges: How quickly") and top["chunk"]["speaker_roles"][0] == {"name": "Whitney Hodges", "role": "staff"}
    assert top["citation"]["passage_ids"] == ["doc_acme_1:span:0", "doc_acme_1:span:1"] and top["citation"]["speaker_label"] == "Whitney Hodges"


def test_any_signed_in_role_may_search_and_only_the_shared_secret_opens_the_door(api):
    search, repo, embedder, http = api
    assert search("reply", email="nobody@example.invalid").status_code == 200, "a viewer may search"
    assert http.post("/storage/search", json={"text": "reply"}).status_code == 401
    assert http.post("/storage/search", json={"text": "reply"}, headers={"Authorization": "Bearer wrong", "X-Atelier-Actor": "a@b.c"}).status_code == 401


def test_the_request_is_checked(api):
    search, *_ = api
    assert search("reply", k=51).status_code == 422 and search("reply", k=0).status_code == 422
    assert search("   ").status_code == 422 and search("x" * 2001).status_code == 422
    response = search("reply", scope="everything")
    assert response.status_code == 422


def test_a_hit_whose_citation_cannot_be_located_is_withheld_and_counted(api):
    search, repo, *_ = api
    with repo.connection() as conn:
        conn.execute("""UPDATE key_moments SET moment_body = jsonb_set(moment_body, '{quote}', '"A line nobody ever said, about reply speed"')
            WHERE moment_id='m_reply'""")
    answer = search("reply to every inquiry within five minutes", k=50).json()
    assert "m_reply" not in ids(answer) and answer["hits_withheld"] >= 1


def test_the_order_is_stable_and_the_text_endpoint_is_unchanged(api):
    search, repo, embedder, http = api
    first = [(h["kind"], h["moment"]["moment_id"], h["score"]) for h in search("reply price calendar", k=50).json()["hits"]]
    second = [(h["kind"], h["moment"]["moment_id"], h["score"]) for h in search("reply price calendar", k=50).json()["hits"]]
    assert first == second and first == sorted(first, key=lambda h: (-h[2], h[1]))
    from backend_pipeline.api import app
    spec = app.openapi()["paths"]
    assert "/storage/search/transcripts" in spec and "/storage/search" in spec


def test_the_search_command_runs_the_same_code_and_can_skip_the_model(api, monkeypatch, capsys):
    import json

    from backend_pipeline import storage_cli
    from backend_pipeline.storage_config import StorageSettings
    search, repo, embedder, _ = api
    from backend_pipeline.config import Settings
    monkeypatch.setattr(StorageSettings, "from_env", classmethod(lambda cls: repo.settings))
    monkeypatch.setattr(Settings, "from_env", classmethod(lambda cls, *a, **k: Settings()))

    def run(*argv):
        capsys.readouterr()
        storage_cli.main(["search", "query", *argv])
        return json.loads(capsys.readouterr().out)
    sent = len(embedder.embedded)
    text_only = run("reply to every inquiry within five minutes", "--text-only", "--k", "3")
    assert text_only["query_embedding_status"] == "unavailable" and len(embedder.embedded) == sent, "--text-only makes no model call"
    assert text_only["hits"][0]["id"] == "m_reply" and text_only["hits"][0]["matched_by"] == ["phrase"]
    meaning = run("how quickly should we respond to new leads", "--client", "client_acme", "--moment-type", "result", "--k", "3")
    assert meaning["query_embedding_status"] == "used" and [h["id"] for h in meaning["hits"]] == ["m_reply"]
    assert meaning["hits"][0]["citation"]["quote"].startswith("We reply to every inquiry")
    chunks = run("reply inquiry minutes", "--scope", "chunks", "--from", "2020-01-01T00:00:00+00:00")
    assert {h["kind"] for h in chunks["hits"]} == {"chunk"}


def test_fusion_uses_the_configured_constant(api):
    search, repo, *_ = api
    from backend_pipeline import settings_store
    base = search("reply to every inquiry within five minutes").json()["hits"][0]["score"]
    with repo.connection() as conn:
        settings_store.set_value(conn, "search.rrf_k", 5, "tester@example.invalid")
    tuned = search("reply to every inquiry within five minutes").json()["hits"][0]["score"]
    # The top hit is first by the words and r-th by meaning: its score is 1/(k+1) + 1/(k+r).
    rank = next(r for r in (1, 2, 3, 4) if abs(base - (1 / 61 + 1 / (60 + r))) < 1e-9)
    assert tuned > base and abs(tuned - (1 / 6 + 1 / (5 + rank))) < 1e-9
