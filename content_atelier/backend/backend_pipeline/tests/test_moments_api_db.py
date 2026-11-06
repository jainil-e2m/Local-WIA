"""2.B8 and 2.B12 on a real database: the moments ledger API (filters, pagination, a stable order, facets, detail) and extraction health.

Synthetic moments. No network."""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend_pipeline.storage_api import router
from backend_pipeline.tests.ledger_fixtures import NOW, embed_everything, ledger, load_document, make_document, make_moment  # noqa: F401
from backend_pipeline.tests.platform_db import APPROVER, EDITOR, empty, platform_setup, platform_url  # noqa: F401 (fixtures)

DEFAULT_ORDER = ["m_slack", "m_price", "m_reply", "m_staff", "m_praise_beta", "m_pricing_beta"]  # newest first, then moment id


def headers(email=APPROVER):
    return {"Authorization": "Bearer test-secret", "X-Atelier-Actor": email, "X-Atelier-Email": email}


@pytest.fixture
def client(ledger):  # noqa: F811
    repo, models, tmp_path, embedder = ledger
    app = FastAPI()
    app.include_router(router(repo.settings))
    http = TestClient(app)

    def get(path, email=APPROVER):
        return http.get("/storage" + path, headers=headers(email))
    return get, repo, http


def ids(answer):
    return [m["moment_id"] for m in answer["items"]]


def test_the_ledger_lists_verified_current_moments_newest_first_and_hides_do_not_use(client):
    get, repo, _ = client
    answer = get("/moments").json()
    assert ids(answer) == DEFAULT_ORDER and answer["total"] == 6 and answer["limit"] == 50 and answer["offset"] == 0
    first = answer["items"][0]
    assert first["quote_verified"] is True and first["is_current"] is True and first["document_title"] == "Slack thread"
    assert first["speaker_role"] == "staff" and first["client_name"] == "Acme Weddings" and first["consent_status"] == "anonymise"
    assert "m_gamma" not in ids(answer) and "m_unverified" not in ids(answer) and "m_old" not in ids(answer)


def test_pagination_walks_the_whole_ledger_once_in_a_stable_order(client):
    get, *_ = client
    seen = []
    for offset in (0, 2, 4, 6):
        page = get(f"/moments?limit=2&offset={offset}").json()
        assert page["total"] == 6 and page["limit"] == 2 and page["offset"] == offset
        seen += ids(page)
    assert seen == DEFAULT_ORDER
    assert ids(get("/moments?limit=2&offset=2").json()) == ids(get("/moments?limit=2&offset=2").json())
    assert get("/moments?limit=201").status_code == 422 and get("/moments?limit=0").status_code == 422
    assert get("/moments?offset=-1").status_code == 422


def test_the_order_is_stable_when_moments_share_a_date(client):
    get, repo, _ = client
    with repo.connection() as conn:
        document = load_document(conn, "doc_acme_1")
        for name in ("m_tie_b", "m_tie_a"):
            make_moment(conn, name, document, 1, "We reply to every inquiry within five minutes and our bookings doubled.",
                        client_id="client_acme", occurred_at=NOW - timedelta(days=10), speaker=("Dana Lee", "client", "person_dana"))
    ordered = ids(get("/moments").json())
    assert ordered[1:6] == ["m_price", "m_reply", "m_staff", "m_tie_a", "m_tie_b"], "equal dates fall back to the moment id"


def test_the_filters_narrow_the_ledger_and_combine(client):
    get, *_ = client
    assert set(ids(get("/moments?client_id=client_beta").json())) == {"m_pricing_beta", "m_praise_beta"}
    assert set(ids(get("/moments?source_type=slack").json())) == {"m_slack"}
    assert set(ids(get("/moments?source_type=zoom&call_type=office_hours").json())) == {"m_pricing_beta", "m_praise_beta"}
    assert set(ids(get("/moments?speaker_role=staff").json())) == {"m_staff", "m_slack"}
    assert set(ids(get("/moments?speaker_role=staff,client&moment_type=testimonial,soundbite").json())) == {"m_slack", "m_praise_beta"}
    assert set(ids(get("/moments?consent_status=do_not_use").json())) == {"m_gamma"}
    assert set(ids(get("/moments?consent_status=cleared,internal_only").json())) == {"m_reply", "m_staff"}
    assert set(ids(get("/moments?document_id=doc_beta_1").json())) == {"m_pricing_beta", "m_praise_beta"}
    assert ids(get("/moments?client_id=client_acme&moment_type=result&speaker_role=client").json()) == ["m_reply"]
    window = get(f"/moments?from={(NOW - timedelta(days=12)).isoformat().replace('+00:00', 'Z')}&to={(NOW - timedelta(days=3)).isoformat().replace('+00:00', 'Z')}")
    assert set(ids(window.json())) == {"m_reply", "m_price", "m_staff"}


def test_text_filters_match_words_and_substrings_of_the_quote(client):
    get, *_ = client
    assert ids(get("/moments?q=inquiry doubled").json()) == ["m_reply"]
    assert set(ids(get("/moments?q=reply").json())) >= {"m_reply", "m_slack"}
    assert ids(get("/moments?q=within five").json()) == ["m_reply"], "a phrase from the quote"
    assert ids(get("/moments?q=scares peo").json()) == ["m_pricing_beta"], "a part of a word, which the words index would miss"
    assert get("/moments?q=" + "x" * 201).status_code == 422
    assert get("/moments?q=100%25").json()["total"] == 0, "a % in the text is a character, not a wildcard"


def test_verified_and_current_states_can_be_asked_for(client):
    get, *_ = client
    unverified = get("/moments?quote_verified=false").json()
    assert ids(unverified) == ["m_unverified"] and unverified["items"][0]["quote_verified"] is False
    assert ids(get("/moments?is_current=false").json()) == ["m_old"]
    assert set(ids(get("/moments?quote_verified=any&is_current=any&consent_status=cleared,anonymise,internal_only,do_not_use").json())) \
        == set(DEFAULT_ORDER) | {"m_gamma", "m_unverified", "m_old"}
    assert set(ids(get("/moments?extractor_version=2026-10-13.weekly.v3&is_current=any").json())) == {"m_old"}
    assert get("/moments?quote_verified=maybe").status_code == 422


def test_bad_filters_are_a_422_not_a_500(client):
    get, *_ = client
    for bad in ("speaker_role=gossip", "moment_type=result,gossip", "consent_status=sure", "source_type=email", "call_type=chat",
                "from=2026-03-09T00:00:00", "from=not-a-date", f"from={NOW.isoformat().replace('+00:00', 'Z')}&to=2020-01-01T00:00:00Z"):
        assert get(f"/moments?{bad}").status_code == 422, bad


def test_a_topic_filter_and_each_moments_topics(client):
    get, repo, _ = client
    from backend_pipeline.moments import topics
    with repo.connection() as conn:
        topic = topics.create_topic(conn, "Reply speed", "How fast the team replies", origin="person", created_by="t")
        topics.link(conn, "m_reply", topic["topic_id"], assigned_by="person")
    answer = get(f"/moments?topic_id={topic['topic_id']}").json()
    assert ids(answer) == ["m_reply"] and answer["items"][0]["topics"] == [{"topic_id": topic["topic_id"], "name": "Reply speed"}]
    assert next(m for m in get("/moments").json()["items"] if m["moment_id"] == "m_price")["topics"] == []


def test_facets_count_each_dimension_under_the_other_filters(client):
    get, *_ = client
    facets = get("/moments/facets").json()
    by = lambda name: {f["value"]: f["count"] for f in facets[name]}  # noqa: E731
    assert facets["total"] == 6
    assert by("moment_types") == {"result": 1, "objection": 1, "tension": 1, "testimonial": 1, "teaching": 1, "soundbite": 1}
    assert by("speaker_roles") == {"client": 4, "staff": 2}
    assert by("consent_statuses") == {"cleared": 1, "anonymise": 4, "internal_only": 1, "do_not_use": 1}, "do_not_use is counted so it can be chosen"
    assert by("source_types") == {"fathom": 3, "zoom": 2, "slack": 1}
    assert by("call_types") == {"client_1to1": 3, "office_hours": 2, "slack_thread": 1}
    assert {c["value"]: (c["label"], c["count"]) for c in facets["clients"]} == {"client_acme": ("Acme Weddings", 4), "client_beta": ("Beta Bridal", 2)}
    assert datetime.fromisoformat(facets["earliest"]) < datetime.fromisoformat(facets["latest"])
    narrowed = get("/moments/facets?client_id=client_beta").json()
    assert {c["value"] for c in narrowed["clients"]} == {"client_acme", "client_beta"}, "a client control still lists the other clients"
    assert {f["value"] for f in narrowed["moment_types"]} == {"tension", "testimonial"} and narrowed["total"] == 2
    window = get(f"/moments/facets?from={(NOW - timedelta(days=12)).isoformat().replace('+00:00', 'Z')}").json()
    assert datetime.fromisoformat(window["earliest"]) < NOW - timedelta(days=39), "the date range ignores the date filter, so a control can widen it"
    assert get("/moments/facets?speaker_role=gossip").status_code == 422


def test_a_moment_opens_with_its_scene_citation_passages_speaker_topics_checks_and_cards(client):
    get, repo, _ = client
    from backend_pipeline.moments import topics
    with repo.connection() as conn:
        topic = topics.create_topic(conn, "Reply speed", "How fast the team replies", origin="person", created_by="t")
        topics.link(conn, "m_reply", topic["topic_id"], assigned_by="person")
        conn.execute("UPDATE key_moments SET checks=%s::jsonb, quote_repair=%s::jsonb WHERE moment_id='m_reply'",
                     ('{"role": {"ok": true}, "numbers": {"found": ["five"]}}', '{"method": "whitespace", "from": "We reply  to every"}'))
        conn.execute("INSERT INTO weeks (week_id, week_start, week_end) VALUES ('week_x', '2026-06-01', '2026-06-07')")
        conn.execute("""INSERT INTO pipeline_runs (run_id, week_id, run_scope, trigger_type, input_refs) VALUES ('run_x','week_x','weekly_angles','manual','{}')""")
        conn.execute("""INSERT INTO content_angles (angle_id, week_id, run_id, content_body, content_hash, first_generated_at)
            VALUES ('angle_x','week_x','run_x','{"card": {"title": "Reply in five minutes"}}','h',now())""")
        conn.execute("INSERT INTO angle_moments (angle_id, moment_id, evidence_role) VALUES ('angle_x','m_reply','primary')")
    detail = get("/moments/m_reply").json()
    assert detail["summary"]["moment_id"] == "m_reply" and detail["summary"]["record"].startswith("Dana described")
    assert detail["moment"]["moment_body"]["quote"] == "We reply to every inquiry within five minutes and our bookings doubled."
    assert detail["moment"]["moment_body"]["context_summary"] and detail["moment"]["evidence_refs"]
    assert detail["evidence_intact"] is True
    citation = detail["citation"]
    assert citation["quote"] == detail["moment"]["moment_body"]["quote"] and citation["recording_url"] == "https://fathom.video/share/acme-1"
    assert citation["speaker_role"] == "client" and citation["consent_status"] == "cleared" and citation["start_ms"] == 20000
    assert detail["document"] == {"document_id": "doc_acme_1", "title": "Acme check-in", "source_type": "fathom", "call_type": "client_1to1",
                                  "occurred_at": detail["document"]["occurred_at"], "recording_url": "https://fathom.video/share/acme-1"}
    # The cited passages, as the card screens already read them.
    roles = {p["passage_id"]: p["roles"] for p in detail["passages"]}
    assert roles == {"doc_acme_1:span:0": ["context"], "doc_acme_1:span:1": ["anchor", "context"], "doc_acme_1:span:2": ["context"]}
    anchor = next(p for p in detail["passages"] if "anchor" in p["roles"])
    assert anchor["text"].startswith("Dana Lee: We reply") and anchor["title"] == "Acme check-in" and anchor["speaker"] == "Dana Lee"
    assert (anchor["speaker_role"], anchor["start_ms"], anchor["end_ms"]) == ("client", 20000, 35000)
    # The passages around them, with offsets, so a person can read the call before and after.
    around = detail["surrounding"]
    assert [p["ordinal"] for p in around] == [0, 1, 2, 3, 4] and [p["cited"] for p in around] == [True, True, True, False, False]
    assert [p["anchor"] for p in around] == [False, True, False, False, False] and around[3]["text"].startswith("Dana Lee: Honestly the price")
    assert all(p["start"] < p["end"] for p in around) and around[1]["speaker_role"] == "client"
    assert detail["topics"] == [{"topic_id": topic["topic_id"], "name": "Reply speed", "assigned_by": "person", "similarity": None}]
    assert detail["checks"]["numbers"]["found"] == ["five"] and detail["quote_repair"]["method"] == "whitespace"
    assert detail["cards"] == [{"angle_id": "angle_x", "week_id": "week_x", "title": "Reply in five minutes", "evidence_role": "primary",
                                "approval_status": "pending", "selection_status": "candidate"}]
    assert detail["unverified_reason"] is None


def test_an_unverified_moment_opens_without_a_citation_and_says_why(client):
    get, *_ = client
    detail = get("/moments/m_unverified").json()
    assert detail["citation"] is None and detail["summary"]["quote_verified"] is False and detail["passages"] == []
    assert detail["unverified_reason"] == "The quote does not bind to its source" and detail["surrounding"] == []
    assert get("/moments/m_old").json()["summary"]["is_current"] is False
    assert get("/moments/not_a_moment").status_code == 404


def test_a_reference_that_no_longer_matches_the_original_is_left_out_and_flagged(client):
    get, repo, _ = client
    with repo.connection() as conn:
        conn.execute("""UPDATE key_moments SET evidence_refs = jsonb_set(evidence_refs, '{1,start}', '3') WHERE moment_id='m_reply'""")
    detail = get("/moments/m_reply").json()
    assert detail["evidence_intact"] is False and len(detail["passages"]) == 2 and detail["citation"] is None


def test_reading_is_open_to_any_signed_in_role_and_needs_the_shared_secret(client):
    get, repo, http = client
    for path in ("/moments", "/moments/facets", "/moments/m_reply", "/topics", "/documents/extraction-health"):
        assert get(path, "nobody@example.invalid").status_code == 200, path
        assert http.get("/storage" + path).status_code == 401, path


# ---- 2.B12: extraction health -----------------------------------------------------------------------------------------------------


def test_extraction_health_counts_documents_by_status_and_shows_where_it_is_stuck(client):
    get, repo, _ = client
    with repo.connection() as conn:
        zoom = make_document(conn, "doc_zoom_pending", "Zoom call", [("Dana Lee", "hello there")], source_type="zoom", occurred_at=NOW)
        conn.execute("UPDATE transcripts SET extraction_status='pending', ingested_at = now() - interval '5 hours' WHERE transcript_id=%s",
                     (zoom["transcript_id"],))
        make_document(conn, "doc_zoom_failed", "Broken call", [("Dana Lee", "hello again")], source_type="zoom", occurred_at=NOW)
        conn.execute("UPDATE transcripts SET extraction_status='failed' WHERE transcript_id='doc_zoom_failed'")
        conn.execute("INSERT INTO weeks (week_id, week_start, week_end) VALUES ('week_h', '2026-06-01', '2026-06-07')")
        conn.execute("INSERT INTO pipeline_runs (run_id, week_id, run_scope, trigger_type, input_refs) VALUES ('run_h','week_h','document_extraction','manual','{}')")
        conn.execute("""INSERT INTO pipeline_jobs (job_id, run_id, week_id, stage, transcript_id, status, idempotency_key, error_summary, attempt_count)
            VALUES ('job_h','run_h','week_h','moment_extraction','doc_zoom_failed','failed','k1','Schema failure after one repair', 2)""")
        make_document(conn, "doc_excluded", "Internal sync", [("Whitney Hodges", "team only")], included=False, call_type="internal")
        conn.execute("UPDATE transcripts SET extraction_status='not_applicable' WHERE transcript_id='doc_excluded'")
        make_document(conn, "doc_empty", "A call with no scenes", [("Dana Lee", "nothing notable")], source_type="zoom")
    health = get("/documents/extraction-health").json()
    totals = health["totals"]
    # Five included documents had scenes (doc_acme_1, doc_beta_1, doc_gamma_1, doc_slack_1) or completed with none (doc_empty).
    assert totals["included_documents"] == 7 and "doc_excluded" not in str(health)
    assert totals["by_status"] == {"pending": 1, "queued": 0, "running": 0, "completed": 5, "failed": 1, "not_applicable": 0}
    assert totals["completed_documents"] == 5 and totals["zero_scene_documents"] == 1 and totals["zero_scene_share"] == 0.2
    assert totals["moments"] == 8 and totals["verified_moments"] == 7, "current moments only: the superseded one does not count"
    assert totals["verified_quote_share"] == 0.875
    assert health["failed_total"] == 1 and health["failed"][0]["document_id"] == "doc_zoom_failed"
    assert health["failed"][0]["error_summary"] == "Schema failure after one repair" and health["failed"][0]["job_id"] == "job_h"
    assert health["failed"][0]["attempts"] == 2 and health["failed"][0]["source_type"] == "zoom"
    assert health["oldest_pending"]["document_id"] == "doc_zoom_pending" and 4.9 < health["oldest_pending"]["waiting_hours"] < 5.2
    by_type = {s["source_type"]: s for s in health["by_source_type"]}
    assert set(by_type) == {"fathom", "zoom", "slack"}
    assert by_type["zoom"]["included_documents"] == 4 and by_type["zoom"]["by_status"]["failed"] == 1 and by_type["zoom"]["zero_scene_documents"] == 1
    assert by_type["fathom"]["zero_scene_share"] == 0.0 and by_type["fathom"]["moments"] == 5 and by_type["fathom"]["verified_quote_share"] == 0.8
    assert by_type["slack"]["verified_quote_share"] == 1.0


def test_extraction_health_on_an_empty_archive_has_no_shares_instead_of_a_division_by_zero(platform_setup):  # noqa: F811
    repo, models, tmp_path = platform_setup
    empty(repo.settings.database_url)
    app = FastAPI()
    app.include_router(router(repo.settings))
    health = TestClient(app).get("/storage/documents/extraction-health", headers=headers()).json()
    assert health["totals"]["included_documents"] == 0 and health["totals"]["zero_scene_share"] is None
    assert health["totals"]["verified_quote_share"] is None and health["failed"] == [] and health["oldest_pending"] is None
    assert health["by_source_type"] == []
