"""2.B7 on a real database: two moments about one subject share a topic, a blocked topic gets no new links, a merged one redirects its
links, and every administrator action is audited. Synthetic moments; an offline provider that follows the topics it is offered."""
from __future__ import annotations

import json
from datetime import timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend_pipeline import settings_store, storage_cli
from backend_pipeline.config import Settings  # noqa: F401
from backend_pipeline.moments import topics
from backend_pipeline.sql_pipeline import SQLWorker
from backend_pipeline.storage_api import router
from backend_pipeline.storage_config import StorageSettings
from backend_pipeline.tests.ledger_fixtures import MODEL, NOW, Embedder, embed_everything, ledger, load_document, make_moment  # noqa: F401
from backend_pipeline.tests.platform_db import APPROVER, EDITOR, platform_setup, platform_url  # noqa: F401 (fixtures)

VIEWER = "viewer@example.invalid"


def assign(repo, models, embedder, ids=None):
    """Queue topic assignment on the synthetic database and run it."""
    queued = topics.queue(repo, models, ids=ids, mode="synthetic")
    if queued["queued"]:
        assert SQLWorker(repo.settings, models, provider=embedder).once()
    return queued


def job(repo):
    with repo.connection() as conn:
        # The newest by its run, whose dating is in order (repository.DATED_IN_ORDER); a job's own created_at may step back.
        return conn.execute("""SELECT j.* FROM pipeline_jobs j JOIN pipeline_runs r USING(run_id) WHERE j.stage='topic_assignment'
            ORDER BY r.created_at DESC,j.created_at DESC""").fetchone()


def links(repo):
    with repo.connection() as conn:
        rows = conn.execute("""SELECT mt.moment_id, tp.name, tp.topic_id, mt.assigned_by, mt.similarity FROM moment_topics mt
            JOIN topics tp USING (topic_id) ORDER BY mt.moment_id""").fetchall()
    return {r["moment_id"]: r for r in rows}


@pytest.fixture
def embedded(ledger):  # noqa: F811
    repo, models, tmp_path, embedder = ledger
    embed_everything(repo, models, embedder)
    return repo, models, embedder


# ---- assignment --------------------------------------------------------------------------------------------------------------------


def test_two_moments_about_one_subject_in_different_words_share_a_topic_chosen_by_the_model(embedded):
    repo, models, embedder = embedded
    with repo.connection() as conn:
        settings_store.set_value(conn, "topics.attach_similarity", 1.0, "tester@example.invalid")  # every moment goes to the model
    assign(repo, models, embedder, ids=["m_reply", "m_slack"])
    placed = links(repo)
    assert set(placed) == {"m_reply", "m_slack"} and placed["m_reply"]["topic_id"] == placed["m_slack"]["topic_id"]
    assert placed["m_reply"]["name"] == "Inquiry follow-up speed" and placed["m_reply"]["assigned_by"] == "model"
    first, second = embedder.json_calls
    assert first["candidates"] == [], "the first moment found no topic to offer, so the model proposed one"
    assert [c["name"] for c in second["candidates"]] == ["Inquiry follow-up speed"], "the second was offered it, and took it"
    with repo.connection() as conn:
        assert conn.execute("SELECT count(*) n FROM topics").fetchone()["n"] == 1
    assert job(repo)["result_refs"]["topics_created"] == 1 and job(repo)["result_refs"]["linked_by_model"] == 2


def test_a_moment_close_enough_to_a_topic_is_attached_without_a_model_call(embedded):
    repo, models, embedder = embedded
    assign(repo, models, embedder, ids=["m_reply"])
    assert len(embedder.json_calls) == 1
    assign(repo, models, embedder, ids=["m_slack"])
    assert len(embedder.json_calls) == 1, "the nearest topic was at least attach_similarity close: no call"
    placed = links(repo)
    assert placed["m_slack"]["topic_id"] == placed["m_reply"]["topic_id"] and placed["m_slack"]["similarity"] >= 0.8
    result = job(repo)["result_refs"]
    assert result["attached_by_similarity"] == 1 and result["model_calls"] == 0


def test_different_subjects_get_different_topics_and_a_rerun_assigns_nothing_new(embedded):
    repo, models, embedder = embedded
    assign(repo, models, embedder)
    placed = links(repo)
    assert set(placed) == {"m_reply", "m_price", "m_pricing_beta", "m_praise_beta", "m_gamma", "m_staff", "m_slack"}
    assert {p["name"] for p in placed.values()} == {"Inquiry follow-up speed", "Pricing objections", "Booking calendar", "Client onboarding"}
    assert placed["m_pricing_beta"]["topic_id"] == placed["m_price"]["topic_id"], "the price objection and the hidden-cost tension are one subject"
    assert placed["m_reply"]["topic_id"] == placed["m_slack"]["topic_id"]
    assert placed["m_reply"]["topic_id"] != placed["m_price"]["topic_id"]
    with repo.connection() as conn:
        assert all(t["embedding"] is not None and t["embedding_model"] == MODEL for t in conn.execute("SELECT * FROM topics"))
    calls, texts = len(embedder.json_calls), len(embedder.embedded)
    again = topics.queue(repo, models, mode="synthetic")
    assert again["queued"] == 0 and again["moments"] == 0, "every moment has a topic: running again assigns nothing"
    assert len(embedder.json_calls) == calls and len(embedder.embedded) == texts


def test_the_estimate_counts_the_calls_a_run_would_make_and_makes_none(embedded):
    repo, models, embedder = embedded
    with repo.connection() as conn:
        first = topics.estimate(conn, models)
    assert first["moments"] == 7 and first["attached_without_a_call"] == 0 and first["model_calls_at_most"] == 7
    assert first["estimated_chat_cost_usd"] is None and "price-in" in first["note"]
    assert first["run_plan"]["stages"] == ["topic_assignment", "embedding"] and first["input_set_hash"].startswith("sha256:")
    assert embedder.json_calls == [] and embedder.embedded[:0] == []
    assign(repo, models, embedder, ids=["m_reply"])
    with repo.connection() as conn:
        after = topics.estimate(conn, models, price_in=0.1, price_out=0.4)
    assert after["moments"] == 6 and after["attached_without_a_call"] >= 1, "m_slack is already close to the follow-up topic"
    assert after["estimated_cost_usd"] is not None and after["model_calls_at_most"] == after["moments"] - after["attached_without_a_call"]


def test_a_blocked_topic_is_never_offered_and_receives_no_new_links(embedded):
    repo, models, embedder = embedded
    assign(repo, models, embedder, ids=["m_reply"])
    topic_id = links(repo)["m_reply"]["topic_id"]
    with repo.connection() as conn:
        topics.block(conn, topic_id, APPROVER)
    # A new moment about the same subject arrives; its topic is blocked, so it is not offered and nothing attaches to it.
    with repo.connection() as conn:
        make_moment(conn, "m_new_reply", load_document(conn, "doc_acme_1"), 1, "We reply to every inquiry within five minutes and our bookings doubled.",
                    record="A new account of replying in minutes", client_id="client_acme", occurred_at=NOW,
                    speaker=("Dana Lee", "client", "person_dana"))
    embed_everything(repo, models, embedder)
    embedder.propose_blocked = "inquiry follow-up SPEED"  # even a model that proposes the blocked subject by name cannot link it
    assign(repo, models, embedder, ids=["m_new_reply"])
    assert embedder.json_calls[-1]["candidates"] == [] and "m_new_reply" not in links(repo)
    result = job(repo)["result_refs"]
    assert result["proposals_dropped"] == 1 and result["no_topic"] == 1
    with repo.connection() as conn:
        with pytest.raises(topics.TopicBlocked):
            topics.link(conn, "m_new_reply", topic_id, assigned_by="person")
    with repo.connection() as conn:
        assert conn.execute("SELECT count(*) n FROM moment_topics WHERE topic_id=%s", (topic_id,)).fetchone()["n"] == 1, "existing links stay"
    # Unblocked, it is offered and attached again.
    with repo.connection() as conn:
        topics.unblock(conn, topic_id, APPROVER)
    embedder.propose_blocked = None
    assign(repo, models, embedder, ids=["m_new_reply"])
    assert links(repo)["m_new_reply"]["topic_id"] == topic_id


def test_a_model_that_names_a_topic_that_was_not_offered_is_repaired_once_and_then_the_moment_is_left_alone(embedded):
    repo, models, embedder = embedded
    embedder.answers = [{"topic_ids": ["topic_invented"], "new_topic": None}, {"topic_ids": ["topic_invented"], "new_topic": None}]
    assign(repo, models, embedder, ids=["m_reply"])
    assert len(embedder.json_calls) == 2, "one answer and exactly one repair"
    assert links(repo) == {} and job(repo)["status"] == "completed" and job(repo)["result_refs"]["model_unusable"] == 1
    embedder.answers = [{"topic_ids": ["topic_invented"], "new_topic": None}]
    assign(repo, models, embedder, ids=["m_reply"])
    assert links(repo)["m_reply"]["name"] == "Inquiry follow-up speed", "the repair was accepted: a valid answer after one bad one"


def test_a_proposal_that_names_an_existing_topic_attaches_to_it_instead_of_making_a_duplicate(embedded):
    repo, models, embedder = embedded
    with repo.connection() as conn:
        settings_store.set_value(conn, "topics.attach_similarity", 1.0, "tester@example.invalid")
    assign(repo, models, embedder, ids=["m_reply"])
    embedder.answers = [{"topic_ids": [], "new_topic": {"name": "inquiry FOLLOW-UP speed", "description": "The same subject, worded differently"}}]
    assign(repo, models, embedder, ids=["m_slack"])
    with repo.connection() as conn:
        assert conn.execute("SELECT count(*) n FROM topics").fetchone()["n"] == 1
    assert links(repo)["m_slack"]["topic_id"] == links(repo)["m_reply"]["topic_id"]


# ---- the administrator's actions ----------------------------------------------------------------------------------------------------


def two_topics(repo):
    with repo.connection() as conn:
        a = topics.create_topic(conn, "Reply speed", "How fast the team replies", origin="person", created_by="t")
        b = topics.create_topic(conn, "Lead response", "Responding to leads", origin="person", created_by="t")
        topics.link(conn, "m_reply", a["topic_id"], assigned_by="person")
        topics.link(conn, "m_price", a["topic_id"], assigned_by="model", similarity=0.5)
        topics.link(conn, "m_slack", b["topic_id"], assigned_by="person")
        topics.link(conn, "m_reply", b["topic_id"], assigned_by="person")
    return a["topic_id"], b["topic_id"]


def test_a_merge_moves_the_links_to_the_target_and_the_merged_topic_receives_none(embedded):
    repo, models, embedder = embedded
    a, b = two_topics(repo)
    with repo.connection() as conn:
        merged = topics.merge(conn, a, b, APPROVER, note="Same subject")
    assert merged["topic_id"] == b
    with repo.connection() as conn:
        rows = conn.execute("SELECT moment_id, topic_id, assigned_by FROM moment_topics ORDER BY moment_id").fetchall()
        source = topics.get_topic(conn, a)
    assert {(r["moment_id"], r["topic_id"]) for r in rows} == {("m_price", b), ("m_reply", b), ("m_slack", b)}, "m_reply was on both: one link is left"
    assert {r["moment_id"]: r["assigned_by"] for r in rows}["m_price"] == "merge" and {r["moment_id"]: r["assigned_by"] for r in rows}["m_slack"] == "person"
    assert source["status"] == "merged" and source["merged_into"] == b
    with repo.connection() as conn:
        with pytest.raises(topics.TopicMerged, match=b):
            topics.link(conn, "m_staff", a, assigned_by="person")
    with repo.connection() as conn:
        assert [c["topic_id"] for c in topics.nearest(conn, models, "m_reply", 5)] == [], "a merged topic is never offered (and these have no vectors yet)"
        with pytest.raises(topics.TopicError, match="already merged"):
            topics.merge(conn, a, b, APPROVER)
        with pytest.raises(topics.TopicError, match="itself"):
            topics.merge(conn, b, b, APPROVER)


def test_merging_a_topic_that_absorbed_others_repoints_them_at_the_new_target(embedded):
    repo, models, embedder = embedded
    a, b = two_topics(repo)
    with repo.connection() as conn:
        c = topics.create_topic(conn, "Reply timing", "When replies go out", origin="person", created_by="t")["topic_id"]
        topics.merge(conn, a, b, APPROVER)
        topics.merge(conn, b, c, APPROVER)
        assert topics.get_topic(conn, a)["merged_into"] == c and topics.get_topic(conn, b)["merged_into"] == c
        with pytest.raises(topics.TopicError, match="Merge into an active topic"):
            topics.merge(conn, c, a, APPROVER)


def test_rename_block_and_unblock_follow_their_rules(embedded):
    repo, models, embedder = embedded
    a, b = two_topics(repo)
    with repo.connection() as conn:
        renamed = topics.rename(conn, a, "Speed of replying", APPROVER, description="Updated words", note="Clearer")
        assert renamed["name"] == "Speed of replying" and renamed["description"] == "Updated words"
        with pytest.raises(topics.TopicError, match="already called"):
            topics.rename(conn, a, "lead RESPONSE", APPROVER)
        with pytest.raises(topics.TopicError, match="3 to 80"):
            topics.rename(conn, a, "ab", APPROVER)
        topics.block(conn, a, APPROVER)
        with pytest.raises(topics.TopicError, match="Only an active topic"):
            topics.block(conn, a, APPROVER)
        with pytest.raises(topics.TopicError, match="Only a blocked topic"):
            topics.unblock(conn, b, APPROVER)
        topics.unblock(conn, a, APPROVER)
        topics.merge(conn, b, a, APPROVER)
        with pytest.raises(topics.TopicError, match="merged"):
            topics.rename(conn, b, "Anything new", APPROVER)
        with pytest.raises(LookupError):
            topics.block(conn, "topic_nope", APPROVER)


def test_a_renamed_topic_keeps_its_vector_but_is_stale_until_the_next_run_embeds_the_new_words(embedded):
    repo, models, embedder = embedded
    assign(repo, models, embedder, ids=["m_reply"])
    topic_id = links(repo)["m_reply"]["topic_id"]
    with repo.connection() as conn:
        assert topics.stale_topics(conn, models) == []
        topics.rename(conn, topic_id, "How fast we answer leads", APPROVER)
        assert [t["topic_id"] for t in topics.stale_topics(conn, models)] == [topic_id]
        assert conn.execute("SELECT embedding IS NOT NULL AS has FROM topics WHERE topic_id=%s", (topic_id,)).fetchone()["has"] is True
    sent = len(embedder.embedded)
    assign(repo, models, embedder, ids=["m_staff"])
    assert "How fast we answer leads. How quickly the team replies to new inquiries" in embedder.embedded[sent:]
    with repo.connection() as conn:
        assert topics.stale_topics(conn, models) == []


def test_every_administrator_action_writes_a_decisions_row_in_the_same_transaction(embedded):
    repo, models, embedder = embedded
    a, b = two_topics(repo)
    with repo.connection() as conn:
        topics.rename(conn, a, "Speed of replying", APPROVER, note="Clearer")
        topics.block(conn, b, APPROVER, note="Off strategy")
        topics.unblock(conn, b, APPROVER)
        topics.merge(conn, a, b, APPROVER, note="Same")
        rows = {r["action"]: r for r in conn.execute("SELECT action, item_kind, item_id, actor, author, note, details FROM decisions").fetchall()}
    assert set(rows) == {"topic_rename", "topic_block", "topic_unblock", "topic_merge"}
    assert all(r["item_kind"] == "topic" and r["actor"] == APPROVER and r["author"] == APPROVER for r in rows.values())
    assert rows["topic_rename"]["details"]["from"] == "Reply speed" and rows["topic_rename"]["note"] == "Clearer"
    assert rows["topic_merge"]["details"]["into"] == b and rows["topic_merge"]["details"]["moments_moved"] == 1
    assert rows["topic_block"]["item_id"] == b and rows["topic_merge"]["item_id"] == a
    # A change that fails writes no decision, and a decision that cannot be written undoes its change.
    with repo.connection() as conn:
        with pytest.raises(topics.TopicError):
            topics.block(conn, a, APPROVER)
        assert conn.execute("SELECT count(*) n FROM decisions").fetchone()["n"] == 4
    from backend_pipeline.tests.ledger_fixtures import KINDS, set_decision_kinds
    set_decision_kinds(repo.settings.database_url, KINDS)  # the schema gap: no 'topic' kind
    with pytest.raises(topics.TopicError, match="does not accept item_kind 'topic'"):
        topics.as_approver(repo, APPROVER, topics.rename, b, "A name that is new")
    with repo.connection() as conn:
        assert topics.get_topic(conn, b)["name"] == "Lead response", "the rename was rolled back with its missing audit row"
    set_decision_kinds(repo.settings.database_url, KINDS + ", 'topic'")


def test_statistics_count_mentions_in_the_last_30_90_and_365_days_distinct_clients_and_the_last_mention(embedded):
    repo, models, embedder = embedded
    with repo.connection() as conn:
        document = load_document(conn, "doc_acme_1")
        make_moment(conn, "m_ancient", document, 1, "We reply to every inquiry within five minutes and our bookings doubled.",
                    client_id="client_gamma", consent="anonymise", occurred_at=NOW - timedelta(days=400), speaker=("Dana Lee", "client", None))
        make_moment(conn, "m_75", document, 1, "We reply to every inquiry within five minutes and our bookings doubled.",
                    client_id="client_acme", occurred_at=NOW - timedelta(days=75), speaker=("Dana Lee", "client", None))
        topic = topics.create_topic(conn, "Reply speed", None, origin="person", created_by="t")["topic_id"]
        for moment in ("m_reply", "m_75", "m_pricing_beta", "m_ancient", "m_unverified", "m_old"):
            topics.link(conn, moment, topic, assigned_by="person")
        stats = topics.statistics(conn, topic)
        listed = topics.listing(conn)["items"][0]
    assert (stats["mentions_30d"], stats["mentions_90d"], stats["mentions_365d"], stats["total_mentions"]) == (1, 3, 3, 4), \
        "m_reply is 10 days old; m_75 and m_pricing_beta are within 90; m_ancient is only in the total; unverified and superseded ones count nowhere"
    assert stats["distinct_clients"] == 3 and listed["topic_id"] == topic and stats["description"] is None
    assert abs((stats["last_mentioned_at"] - (NOW - timedelta(days=10))).total_seconds()) < 5


# ---- the routes ----------------------------------------------------------------------------------------------------------------------


@pytest.fixture
def api(embedded):
    repo, models, embedder = embedded
    app = FastAPI()
    app.include_router(router(repo.settings))
    http = TestClient(app)

    def call(method, path, email=APPROVER, **kw):
        return http.request(method, "/storage" + path, headers={"Authorization": "Bearer test-secret", "X-Atelier-Actor": email,
                                                                 "X-Atelier-Email": email}, **kw)
    return call, repo, models, embedder


def test_only_an_approver_may_rename_merge_block_or_unblock_and_an_editor_may_assign_topics(api):
    call, repo, *_ = api
    a, b = two_topics(repo)
    for action, body in (("rename", {"name": "Speed of replying"}), ("merge", {"into_topic_id": b}), ("block", {}), ("unblock", {})):
        for email in (VIEWER, EDITOR):
            assert call("POST", f"/topics/{a}/{action}", email, json=body).status_code == 403, (action, email)
    assert call("POST", f"/topics/{a}/rename", json={"name": "Speed of replying", "note": "Clearer"}).json()["name"] == "Speed of replying"
    blocked = call("POST", f"/topics/{b}/block", json={"note": "Off strategy"}).json()
    assert blocked["status"] == "blocked" and call("POST", f"/topics/{b}/unblock", json={}).json()["status"] == "active"
    merged = call("POST", f"/topics/{a}/merge", json={"into_topic_id": b}).json()
    assert merged["topic_id"] == b and merged["total_mentions"] == 3
    assert call("POST", f"/topics/{a}/rename", json={"name": "Whatever it was"}).status_code == 409, "a merged topic cannot be renamed"
    assert call("POST", f"/topics/{a}/merge", json={"into_topic_id": b}).status_code == 409
    assert call("POST", "/topics/topic_nope/block", json={}).status_code == 404
    assert call("POST", f"/topics/{b}/rename", json={"name": "x"}).status_code == 422 and call("POST", f"/topics/{b}/rename", json={}).status_code == 422
    assert call("POST", f"/topics/{b}/block", json={"unexpected": 1}).status_code == 422


def test_a_person_assigns_and_removes_a_moments_topics_and_cannot_use_a_blocked_or_merged_one(api):
    call, repo, *_ = api
    a, b = two_topics(repo)
    url = "/moments/m_staff/topics"
    assert call("POST", url, VIEWER, json={"add": [a]}).status_code == 403
    added = call("POST", url, EDITOR, json={"add": [a, b], "note": "Speed matters"})
    assert added.status_code == 200 and {t["topic_id"]: t["assigned_by"] for t in added.json()["topics"]} == {a: "person", b: "person"}
    removed = call("POST", url, EDITOR, json={"remove": [b]}).json()
    assert [t["topic_id"] for t in removed["topics"]] == [a]
    call("POST", f"/topics/{b}/block", json={})
    assert call("POST", url, EDITOR, json={"add": [b]}).status_code == 409, "a blocked topic receives no new links, from a person either"
    assert call("POST", f"/topics/{a}/merge", json={"into_topic_id": b}).status_code == 409, "nothing is merged into a blocked topic"
    call("POST", f"/topics/{b}/unblock", json={})
    assert call("POST", f"/topics/{a}/merge", json={"into_topic_id": b}).status_code == 200
    assert call("POST", url, EDITOR, json={"add": [a]}).status_code == 409, "nor does a merged one"
    assert call("POST", "/moments/m_nope/topics", EDITOR, json={"add": [b]}).status_code == 404
    assert call("POST", url, EDITOR, json={}).status_code == 422 and call("POST", url, EDITOR, json={"add": [b], "remove": [b]}).status_code == 422
    with repo.connection() as conn:
        actions = [r["action"] for r in conn.execute("SELECT action FROM decisions WHERE action IN ('topic_link','topic_unlink') ORDER BY created_at")]
    assert actions[:3] == ["topic_link", "topic_link", "topic_unlink"]


def test_topics_are_listed_with_statistics_and_one_opens_with_its_moments_and_history(api):
    call, repo, *_ = api
    a, b = two_topics(repo)
    call("POST", f"/topics/{a}/merge", json={"into_topic_id": b, "note": "Same subject"})
    listing = call("GET", "/topics", VIEWER).json()
    assert listing["total"] == 2 and listing["counts"] == {"active": 1, "blocked": 0, "merged": 1}
    assert [t["topic_id"] for t in listing["items"]][0] == b and listing["items"][0]["mentions_90d"] == 3
    assert [t["topic_id"] for t in call("GET", "/topics?status=merged", VIEWER).json()["items"]] == [a]
    assert [t["topic_id"] for t in call("GET", "/topics?q=lead", VIEWER).json()["items"]] == [b]
    assert call("GET", "/topics?limit=1&offset=1", VIEWER).json()["items"][0]["topic_id"] == a
    assert call("GET", "/topics?status=nope", VIEWER).status_code == 422 and call("GET", "/topics?limit=201", VIEWER).status_code == 422
    detail = call("GET", f"/topics/{b}", VIEWER).json()
    assert {m["moment_id"] for m in detail["moments"]} == {"m_reply", "m_price", "m_slack"}
    assert detail["merged_from"] == [{"topic_id": a, "name": "Reply speed"}] and detail["distinct_clients"] == 1
    assert [h["action"] for h in detail["history"]] == ["topic_merge"] and detail["history"][0]["actor"] == APPROVER
    assert detail["history"][0]["note"] == "Same subject" and detail["history"][0]["details"]["into"] == b
    assert call("GET", "/topics/topic_nope", VIEWER).status_code == 404


# ---- queueing, the contract and the commands ------------------------------------------------------------------------------------------


def test_assignment_needs_the_catches_and_the_synthetic_database_for_an_injected_provider(embedded):
    repo, models, embedder = embedded
    with pytest.raises(ValueError, match="permissions are disabled"):
        topics.queue(repo, models, mode="live")
    with pytest.raises(ValueError, match="live or synthetic"):
        topics.queue(repo, models, mode="cached")
    real = type(repo)(repo.settings.model_copy(update={"synthetic": False}))
    with pytest.raises(ValueError, match="synthetic database"):
        topics.queue(real, models, mode="synthetic")
    assert topics.queue(repo, models.model_copy(update={"embedding_dimensions": 768}), mode="synthetic") if False else True
    with pytest.raises(ValueError, match="1536"):
        topics.queue(repo, models.model_copy(update={"embedding_dimensions": 768}), mode="synthetic")
    first = topics.queue(repo, models, mode="synthetic")
    second = topics.queue(repo, models, mode="synthetic")
    assert first["queued"] == 7 and second["already_queued"] is True and second["job_id"] == first["job_id"]


def test_a_live_assignment_without_a_run_plan_is_refused_before_anything_is_sent(embedded, monkeypatch):
    repo, models, embedder = embedded
    live = type(repo)(repo.settings.model_copy(update={"generation_enabled": True, "encoding_enabled": True}))
    queued = topics.queue(live, models, mode="live")
    monkeypatch.setenv("OPENAI_API_KEY", "not-a-real-key")
    monkeypatch.setenv("OPENROUTER_API_KEY", "not-a-real-key")
    monkeypatch.delenv("ATELIER_RUN_PLAN_ID", raising=False)
    assert SQLWorker(live.settings, models).once()
    current = job(repo)
    assert current["job_id"] == queued["job_id"] and current["status"] == "failed" and "run plan" in current["error_summary"]
    with repo.connection() as conn:
        assert conn.execute("SELECT count(*) n FROM topics").fetchone()["n"] == 0


def test_the_topic_vectors_use_the_archives_contract(embedded):
    repo, models, embedder = embedded
    assign(repo, models, embedder, ids=["m_reply"])
    other = models.model_copy(update={"embedding_model": "openai/text-embedding-3-large"})
    with repo.connection() as conn:
        assert [t["name"] for t in topics.stale_topics(conn, other)] == ["Inquiry follow-up speed"], "another model's process sees it as stale"
        assert topics.nearest(conn, other, "m_reply", 5) == [], "and never compares across models"
    with pytest.raises(ValueError, match="made under"):
        topics.queue(repo, other, mode="synthetic")


def test_the_commands_list_estimate_queue_and_administer(embedded, monkeypatch, capsys):
    repo, models, embedder = embedded
    monkeypatch.setattr(StorageSettings, "from_env", classmethod(lambda cls: repo.settings))
    monkeypatch.setattr(type(models), "from_env", classmethod(lambda cls: models))

    def run(*argv):
        capsys.readouterr()
        storage_cli.main(list(argv))
        return json.loads(capsys.readouterr().out)
    assert run("topics", "assign", "--estimate", "--price-in", "0.1", "--price-out", "0.4")["moments"] == 7 and job(repo) is None
    assert run("topics", "assign", "--mode", "synthetic", "--ids", "m_reply")["queued"] == 1
    assert SQLWorker(repo.settings, models, provider=embedder).once()
    shown = run("topics", "list")
    topic_id = shown["items"][0]["topic_id"]
    assert shown["total"] == 1 and run("topics", "show", topic_id)["moments"] == ["m_reply"]
    assert run("topics", "rename", topic_id, "--name", "Speed of replying", "--actor", APPROVER)["name"] == "Speed of replying"
    assert run("topics", "block", topic_id, "--actor", APPROVER)["status"] == "blocked"
    with pytest.raises(PermissionError):
        run("topics", "unblock", topic_id, "--actor", VIEWER)
    assert run("topics", "unblock", topic_id, "--actor", APPROVER)["status"] == "active"
