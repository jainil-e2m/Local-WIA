"""L.B9 "done when" on a migrated database: a published final pasted against an approved brief creates a linked
`published_content` row; its difference from the brief reaches the learning loop as an authored edit; the next cycle's
distinctiveness check sees it.

Synthetic cycles (the version 5 strategist, offline); the finals are recorded through `POST /storage/briefs/{id}/published`
with the verified email, as the brief reader sends them. No provider is called: encoding is off, and the one test that
turns it on embeds with the offline double."""
from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from psycopg.types.json import Jsonb

from backend_pipeline.angle_profiles import STRATEGIST_V5_PROFILE
from backend_pipeline.briefs.validation import hash_brief
from backend_pipeline.config import BACKEND_ROOT, Settings
from backend_pipeline.knowledge import capture, compiler, mining
from backend_pipeline.repository import ContentRepository, insert
from backend_pipeline.search import query
from backend_pipeline.sql_pipeline import SQLWorker
from backend_pipeline.storage_api import router
from backend_pipeline.tests.brief_v2_fixtures import v2_body
from backend_pipeline.tests.ledger_fixtures import Embedder
from backend_pipeline.tests.platform_db import APPROVER, EDITOR, platform_setup, platform_url  # noqa: F401 (fixtures)
from backend_pipeline.tests.test_cards_sql import W1, W2
from backend_pipeline.tests.test_seeds_db import SeedProvider
from backend_pipeline.tests.test_sql_storage import drain

ROOT = BACKEND_ROOT / "knowledge_base"
TODAY = date.today()
VIEWER = "viewer@example.invalid"
PACKET = {"approved_angle": {"title": "Why we ask about follow-up first", "core_perspective": "Follow-up shapes lead quality."},
          "evidence": [{"evidence_id": "ev_a", "speaker": "Carmen Cruickshank", "start_ms": 4000, "role": "anchor",
                        "excerpt": "Carmen Cruickshank: How do you reply to a new inquiry today?"}]}
# The published email keeps the brief's subject and opening, rewrites its argument and adds a line of its own.
FINAL = ("The question we ask every new client\n\nIt starts after the inquiry.\n\nHi {{contact.first_name}},\n\n"
         "Most of the sale happens in the first reply, not in the ad. We read that reply before we touch a campaign.\n\n"
         "You start to see the inquiry as the start of the sale.\n\nReply and tell me what your first reply says.")


def brief_row(brief_id, angle_id, week_id, *, approved=True, channels=("email", "reel", "carousel", "caption"), body=None):
    row = {"brief_id": brief_id, "week_id": week_id, "angle_id": angle_id, "angle_input_hash": "a",
           "content_body": {"schema_version": "brief_document_v2",
                            "document": {"header": {"purpose": "WARM", "channels": list(channels)}, "body": body or v2_body(PACKET)}},
           "selected_evidence": [], "prior_content_context": [], "research_gaps": {"items": [], "coverage": {}}}
    row["content_hash"] = hash_brief(row)
    row.update({"approval_status": "approved" if approved else "pending", "approved_hash": row["content_hash"] if approved else None,
                "approved_by": APPROVER if approved else None, "approved_at": datetime.now(UTC) if approved else None,
                "updated_by": EDITOR})
    return row


@pytest.fixture
def cycle(platform_setup):  # noqa: F811
    """One cycle run (Week 1), and three briefs on its cards: two approved, one pending."""
    repo, _, _ = platform_setup
    models = Settings(llm_payload_format="compact_weekly", extraction_profile="2026-10-13.weekly.v3", angle_prompt_profile=STRATEGIST_V5_PROFILE,
                      knowledge_base_root=ROOT,
                      data_root=repo.settings.artifact_root / "legacy")
    provider = SeedProvider()
    worker = SQLWorker(repo.settings, models, provider=provider)
    repo.submit(W1, "synthetic", models=models)
    drain(worker)
    with repo.connection() as conn:
        cards = conn.execute("SELECT angle_id,week_id FROM content_angles WHERE content_body ? 'card' ORDER BY angle_id").fetchall()
        assert len(cards) >= 2
        insert(conn, "content_briefs", brief_row("brief_cap_a", cards[0]["angle_id"], cards[0]["week_id"]))
        insert(conn, "content_briefs", brief_row("brief_cap_b", cards[1]["angle_id"], cards[1]["week_id"]))
        insert(conn, "content_briefs", brief_row("brief_cap_p", cards[0]["angle_id"], cards[0]["week_id"], approved=False))
    app = FastAPI()
    app.include_router(router(repo.settings))
    client = TestClient(app)

    def call(method, path, body=None, email=EDITOR):
        headers = {"Authorization": "Bearer test-secret", "X-Atelier-Actor": email, "X-Atelier-Email": email}
        return client.request(method, "/storage" + path, json=body, headers=headers)
    return repo, models, provider, worker, cards, call


def final(**changes):
    body = {"channel": "email", "title": "The question we ask every new client", "text": FINAL,
            "published_on": (TODAY - timedelta(days=1)).isoformat(), "url": "https://example.invalid/emails/1",
            "metrics": [{"metric": "Replies", "value": "14"}]}
    body.update(changes)
    return body


def test_a_published_final_becomes_a_linked_row_an_authored_edit_and_what_the_next_cycle_sees(cycle):
    repo, models, provider, worker, cards, call = cycle
    response = call("POST", "/briefs/brief_cap_a/published", final())
    assert response.status_code == 201, response.text
    row = response.json()
    # Linked to its brief and card, with what the brief carries; confirmed, by the person who recorded it.
    assert (row["brief_id"], row["angle_id"], row["status"], row["created"]) == ("brief_cap_a", cards[0]["angle_id"], "confirmed", True)
    assert (row["pillar"], row["content_type"], row["key_message"]) == ("WARM", "behind_the_scenes", "Follow-up shapes lead quality.")
    assert (row["source_kind"], row["source_ref"], row["created_by"]) == ("approved_brief", "capture:brief_cap_a:email:1", EDITOR)
    assert row["details"]["capture"]["url"] == "https://example.invalid/emails/1" and row["text"] == FINAL
    # The difference from the brief's email: the argument it rewrote and the line it added, by its author.
    edit = row["details"]["edit"]
    assert edit["author"] == EDITOR and edit["field"] == "published_email"
    assert edit["before"] == "Follow-up shapes which inquiries become tours."
    assert "Most of the sale happens in the first reply" in edit["after"] and "It starts after the inquiry." not in edit["after"]
    # The figure, in L.B7's shape; encoding is off, so the vector waits and says why.
    assert [(e["metric"], e["value"], e["entered_by"]) for e in row["performance"]] == [("replies", "14", EDITOR)]
    assert row["details"]["embedding"]["status"] == "pending" and "embedding" not in row
    assert call("GET", "/briefs/brief_cap_a/published", email=VIEWER).json()["items"][0]["content_id"] == row["content_id"]
    with repo.connection() as conn:
        assert conn.execute("SELECT embedding FROM published_content WHERE content_id=%s", (row["content_id"],)).fetchone()["embedding"] is None
        decision = conn.execute("SELECT * FROM decisions WHERE item_kind='published_content' AND item_id=%s", (row["content_id"],)).fetchone()
        assert decision["action"] == "published_capture" and decision["actor"] == decision["author"] == EDITOR

        # The learning loop reads it as an edit by its author, beside the Gate 2 edits.
        edits = [e for e in mining.edit_diffs(conn, TODAY - timedelta(days=7), TODAY) if e["version_id"] == row["content_id"]]
        assert len(edits) == 1 and edits[0]["editor"] == EDITOR and edits[0]["brief_id"] == "brief_cap_a"
    # A second brief's final with the same rewrite: two independent edits make a rule candidate citing both, and both
    # finals are exemplar candidates written by WIA.
    second = call("POST", "/briefs/brief_cap_b/published", final(title="Before we touch your ads", metrics=[]), email=APPROVER)
    assert second.status_code == 201, second.text
    with repo.connection() as conn:
        result = mining.run(conn, actor="context_mining")
        assert result["edits_read"] == 2
        rules = conn.execute("SELECT * FROM brand_kit_items WHERE kind='rule' AND source_kind='brief_edit'").fetchall()
        assert len(rules) == 1 and set(rules[0]["source_detail"]["briefs"]) == {"brief_cap_a", "brief_cap_b"}
        assert rules[0]["author"] == ", ".join(sorted({EDITOR, APPROVER}))
        assert "from the approved brief to the published email" in rules[0]["body"]["statement"]
        exemplars = conn.execute("""SELECT * FROM brand_kit_items WHERE kind='exemplar' AND source_kind='published_piece'
            ORDER BY author""").fetchall()
        assert {e["source_detail"]["content_id"] for e in exemplars} == {row["content_id"], second.json()["content_id"]}
        assert not any(e["model_written"] for e in exemplars)
        # The compiled recent-published document reads it too.
        assert row["content_id"] in {r["content_id"] for r in compiler.published_rows(conn, TODAY)}

    # The next cycle: its strategist is told the piece is published, and the run records that it read it.
    run = repo.submit(W2, "synthetic", models=models)
    drain(worker)
    situational = provider.card_users[-1].split("### Published in the last 90 days")[1]
    assert "email: The question we ask every new client" in situational and "email: Before we touch your ads" in situational
    with repo.connection() as conn:
        refs = conn.execute("SELECT input_refs FROM pipeline_runs WHERE run_id=%s", (run["run_id"],)).fetchone()["input_refs"]
    assert {"published": row["content_id"]} in refs["angle_contract"]["knowledge_base"]["context"]["situational"]


def test_a_brief_that_is_not_approved_or_changed_since_is_refused(cycle):
    repo, *_, call = cycle
    pending = call("POST", "/briefs/brief_cap_p/published", final())
    assert pending.status_code == 409 and "approved brief" in pending.json()["detail"]
    with repo.connection() as conn:
        # Content changed in place after approval: its stored hash no longer describes it.
        conn.execute("UPDATE content_briefs SET content_body=jsonb_set(content_body,'{document,body,wia_perspective}',%s) WHERE brief_id='brief_cap_b'",
                     (Jsonb("A different perspective."),))
        # The table binds approved_hash to content_hash (brief_approval_is_bound); a hash moved without the content is refused too.
        conn.execute("UPDATE content_briefs SET approved_hash='stale',content_hash='stale' WHERE brief_id='brief_cap_a'")
    for brief in ("brief_cap_a", "brief_cap_b"):
        changed = call("POST", f"/briefs/{brief}/published", final())
        assert changed.status_code == 409 and "changed after it was approved" in changed.json()["detail"]
    assert call("POST", "/briefs/brief_unknown/published", final()).status_code == 404
    with repo.connection() as conn:
        assert conn.execute("SELECT count(*) n FROM published_content").fetchone()["n"] == 0


def test_sending_the_same_final_again_answers_the_same_row(cycle):
    repo, *_, call = cycle
    first = call("POST", "/briefs/brief_cap_a/published", final())
    assert first.status_code == 201
    again = call("POST", "/briefs/brief_cap_a/published", final())
    assert again.status_code == 200 and again.json()["created"] is False and again.json()["metrics_added"] == 0
    assert again.json()["content_id"] == first.json()["content_id"]
    # A later figure on the same final is added once; the figure already recorded is not.
    later = call("POST", "/briefs/brief_cap_a/published", final(metrics=[{"metric": "replies", "value": "14"},
                                                                          {"metric": "opens", "value": "41%", "on": TODAY.isoformat()}]))
    assert later.status_code == 200 and later.json()["metrics_added"] == 1
    # A different final for the same piece is refused and the recorded one kept; another reel is its own piece.
    different = call("POST", "/briefs/brief_cap_a/published", final(text=FINAL + "\n\nP.S. One more thing."))
    assert different.status_code == 409 and "already recorded" in different.json()["detail"]
    reel = call("POST", "/briefs/brief_cap_a/published", final(channel="reel", title="The question we ask first", text="Before we touch your ads, we ask one thing."))
    assert reel.status_code == 201 and reel.json()["source_ref"] == "capture:brief_cap_a:reel:1"
    assert call("POST", "/briefs/brief_cap_a/published", final(channel="email", piece=2)).status_code == 409
    with repo.connection() as conn:
        rows = conn.execute("SELECT * FROM published_content WHERE source_ref LIKE 'capture:brief_cap_a:%%' ORDER BY source_ref").fetchall()
        assert [r["source_ref"] for r in rows] == ["capture:brief_cap_a:email:1", "capture:brief_cap_a:reel:1"]
        assert rows[0]["text"] == FINAL and [e["metric"] for e in rows[0]["performance"]] == ["replies", "opens"]
        assert conn.execute("SELECT count(*) n FROM decisions WHERE action='published_capture'").fetchone()["n"] == 2
        assert len([e for e in mining.edit_diffs(conn, TODAY - timedelta(days=7), TODAY) if e["brief_id"] == "brief_cap_a"]) == 2


def test_only_an_editor_or_approver_records_a_final(cycle):
    repo, *_, call = cycle
    refused = call("POST", "/briefs/brief_cap_a/published", final(), email=VIEWER)
    assert refused.status_code == 403
    # Whether a brief exists is not for a viewer to learn from the error.
    assert call("POST", "/briefs/brief_unknown/published", final(), email=VIEWER).status_code == 403
    with repo.connection() as conn:
        assert conn.execute("SELECT count(*) n FROM published_content").fetchone()["n"] == 0
    assert call("POST", "/briefs/brief_cap_a/published", final(), email=APPROVER).status_code == 201


def test_with_encoding_on_the_final_is_embedded_through_the_query_path(cycle, monkeypatch):
    repo, *_ = cycle
    embedder = Embedder()
    monkeypatch.setattr(query, "make_provider", lambda models, storage: embedder)
    query._cache.clear()
    encoding = ContentRepository(repo.settings.model_copy(update={"encoding_enabled": True}))
    try:
        row = capture.record(encoding, "brief_cap_a", EDITOR, channel="email", title="The question", text=FINAL,
                             published_on=TODAY)
    finally:
        query._cache.clear()
    assert embedder.embedded == [capture.embedding_text("The question", FINAL)]
    assert row["details"]["embedding"]["status"] == "stored"
    with repo.connection() as conn:
        assert conn.execute("SELECT embedding IS NOT NULL AS has FROM published_content WHERE content_id=%s", (row["content_id"],)).fetchone()["has"]


def test_the_brief_copy_and_the_difference_read_each_channel():
    row = {"content_body": {"schema_version": "brief_document_v2", "document": {"header": {}, "body": v2_body(PACKET)}}}
    assert capture.brief_copy(row, "caption") == "Most of the sale happens after the click.\nThe story behind the question.\nSave this for your next review."
    assert capture.brief_copy(row, "reel").startswith("The question we ask first\nBefore we touch your ads")
    assert capture.brief_copy(row, "reel", 2) is None and capture.brief_copy(row, "stories") is None
    assert capture.brief_copy(row, "carousel").count("\n") == 6
    v1 = {"content_body": {"document": {"email": {"direction": "Open with the reply.", "outline": ["One", "Two"]}, "reels": [],
                                        "carousel": [{"number": 1, "direction": "Slide one"}]}}}
    assert capture.brief_copy(v1, "email") == "Open with the reply.\nOne\nTwo" and capture.brief_copy(v1, "reel") is None
    assert capture.difference("Keep this. Change this.", "Keep this.  Change this.") is None, "spacing is no edit"
    changed = capture.difference("Keep this. Change this.", "Keep this. Changed, and better.\nA new line.")
    assert changed["before"] == "Change this." and changed["after"] == "Changed, and better.\nA new line."
    assert changed["units"] == {"brief": 2, "final": 3, "removed": 1, "added": 2}
