"""3.B7/3.F2 "done when" on the migrated database: a card field a person edited is recorded; a refresh with feedback
writes a new card version from a recorded model response, keeps the reviewer's edited title word for word (the model's
rewrite of it is put back) and changes a field she did not edit; a stale hash is a 409 that queues nothing; a budget
refusal, a provider's 402 and a missing saved answer each show their reason on the card. Synthetic fixtures; the only
model answer is the recorded response in tests/recorded."""
from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend_pipeline import gate_one
from backend_pipeline.angle_profiles import STRATEGIST_V4_PROFILE
from backend_pipeline.cycle import refresh
from backend_pipeline.cycle.verification import carry_forward, ledger_from_database
from backend_pipeline.llm import standing
from backend_pipeline.llm.run_plans import BudgetExhausted, RunPlanError
from backend_pipeline.sql_pipeline import SQLWorker
from backend_pipeline.storage_api import router
from backend_pipeline.store import canonical_hash
from backend_pipeline.tests.platform_db import APPROVER, EDITOR, platform_setup, platform_url  # noqa: F401 (fixture)
from backend_pipeline.tests.test_cards_sql import W1, CardSQLProvider, ranked
from backend_pipeline.tests.test_sql_storage import drain
from backend_pipeline.tests.test_strategist_profile import write_kb
from backend_pipeline.tests.test_strategist_v7 import v7_card

RECORDED = Path(__file__).parent / "recorded" / "card_refresh_feedback_v1.json"
EDITED_TITLE = "How we read a planner's inquiries before we touch the ads"
FEEDBACK = ("Make the point about how we read the inquiry form before touching the ads, and say why that matters to a "
            "planner who already gets plenty of leads.")


class RefreshProvider(CardSQLProvider):
    """The cycle's fake answers, and for a refresh the recorded provider response (or a refusal)."""

    def __init__(self):
        super().__init__()
        self.refreshes, self.failure, self.answer = [], None, None

    def json_call(self, *, stage, system, user, schema, fingerprint):
        if stage == "card_verification" and user.startswith("Reviewer's feedback:"):
            self.refreshes.append({"system": system, "user": user, "schema": schema})
            if self.failure:
                raise self.failure
            if self.answer:
                return self.answer, {"raw": {"choices": [{"finish_reason": "stop", "message": {"content": json.dumps(self.answer)}}]}, "fake": True}
            raw = json.loads(RECORDED.read_text(encoding="utf-8"))
            return json.loads(raw["choices"][0]["message"]["content"]), {"raw": raw, "fake": True}
        return super().json_call(stage=stage, system=system, user=user, schema=schema, fingerprint=fingerprint)


@pytest.fixture
def gate(platform_setup):  # noqa: F811
    repo, models, tmp = platform_setup
    repo.settings.brief_enabled = False
    card_models = models.model_copy(update={"angle_prompt_profile": STRATEGIST_V4_PROFILE,
                                            "knowledge_base_root": write_kb(tmp / "kb")})
    provider = RefreshProvider()
    worker = SQLWorker(repo.settings, card_models, provider=provider)
    repo.submit(W1, "synthetic", models=card_models)
    drain(worker)
    app = FastAPI()
    app.include_router(router(repo.settings))
    client = TestClient(app)

    def call(method, path, body, email=APPROVER):
        headers = {"Authorization": "Bearer test-secret", "X-Atelier-Actor": email, "X-Atelier-Email": email}
        return client.request(method, "/storage" + path, json=body, headers=headers)
    return repo, worker, provider, call


def card_now(repo, angle_id, actor=APPROVER):
    return next(a for a in repo.review(W1, actor)["angles"] if a["angle_id"] == angle_id)


def refresh_runs(repo):
    with repo.connection() as conn:
        return conn.execute("SELECT * FROM pipeline_runs WHERE run_scope='card_refresh' ORDER BY created_at").fetchall()


def edited(repo, call, card, changes, email=EDITOR):
    saved = call("PATCH", f"/angles/{card['angle_id']}", {"expected_hash": card["content_hash"], "changes": changes}, email)
    assert saved.status_code == 200, saved.text
    return card_now(repo, saved.json()["angle_id"])


def test_a_person_with_a_users_row_gets_a_live_check_whatever_the_lists_say(gate):
    """WIA's first week: the refresh's worker holds the reviewer's address as a bare string. It was resolved from the environment
    lists only, so an approver who exists only in `users` read as a viewer, and her card's check waited forever for an embedding
    nobody would make: she could not develop the card."""
    repo, *_ = gate
    repo.settings.encoding_enabled = True
    with repo.connection() as conn:
        conn.execute("UPDATE pipeline_runs SET input_refs=jsonb_set(input_refs,'{mode}','\"live\"') WHERE week_id=%s AND run_scope='weekly_angles'", (W1,))
        conn.execute("INSERT INTO users(email,role) VALUES ('owner@example.invalid','admin'),('reader@example.invalid','viewer')")
        assert gate_one.check_encoding_mode(repo, conn, W1, "owner@example.invalid") == "live"
        assert gate_one.check_encoding_mode(repo, conn, W1, "reader@example.invalid") == "cached"
        assert gate_one.check_encoding_mode(repo, conn, W1, "nobody@example.invalid") == "cached"
        assert gate_one.check_encoding_mode(repo, conn, W1, APPROVER) == "live", "the lists still count for a person with no row"


def test_one_click_approves_a_stance_card_with_nothing_ticked_and_records_the_confirmation(gate):
    """gates.one_click, the path WIA's own card takes: no stance confirmed and no verify item ticked, and one press approves it."""
    repo, _, _, call = gate
    top = ranked(repo.review(W1, APPROVER))[0]
    ids = top["content_body"]["card"]["moment_ids"]
    v7 = v7_card(ids[0], public_stance={"takes_stance": True, "stance": "Her stance."}, moment_ids=ids, verify_before_publishing=["Check it."])
    with repo.connection() as conn:
        conn.execute("UPDATE content_angles SET content_body=content_body||%s::jsonb WHERE angle_id=%s", (json.dumps({"card": v7}), top["angle_id"]))
    body = {"expected_hash": top["content_hash"], "disposition": "develop", "cta": {"choice": "decide_in_development"},
            "verify_acknowledged": [], "overlap_acknowledged": False}
    assert call("POST", f"/angles/{top['angle_id']}/decision", body).status_code == 409, "without the setting the gates hold"
    with repo.connection() as conn:
        conn.execute("INSERT INTO settings(key,value,updated_by) VALUES ('gates.one_click','true'::jsonb,'test')")
    done = call("POST", f"/angles/{top['angle_id']}/decision", body)
    assert done.status_code == 200, done.text
    after = card_now(repo, top["angle_id"])
    assert after["approval_status"] == "approved"
    assert after["content_body"]["stance_confirmation"]["stance"] == "Her stance." and after["content_body"]["stance_confirmation"]["by"] == APPROVER


def test_a_refresh_rewrites_a_v7_cards_stance_and_evidence_keeps_what_she_wrote_and_drops_the_old_confirmation(gate):
    repo, worker, provider, call = gate
    top = ranked(repo.review(W1, APPROVER))[0]
    v7 = v7_card(top["content_body"]["card"]["moment_ids"][0], public_stance={"takes_stance": True, "stance": "The old stance."},
                 moment_ids=top["content_body"]["card"]["moment_ids"])
    with repo.connection() as conn:
        conn.execute("UPDATE content_angles SET content_body=content_body||%s::jsonb WHERE angle_id=%s",
                     (json.dumps({"card": v7, "person_edits": ["guardrail"], "stance_confirmation": {
                         "by": APPROVER, "at": "2026-11-02T00:00:00Z", "note": None, "stance": "The old stance.", "point": v7["point"]}}), top["angle_id"]))
    stance = {"takes_stance": True, "stance": "Her own wording for the stance."}
    provider.answer = {**{f: v7[f] for f in refresh.REFRESH_FIELDS_V7}, "reason": "Moved the card to how we audit the follow-up.",
                       "title": "How we audit what happens after an inquiry", "point": "We audit the follow-up and build what is missing.",
                       "public_stance": stance, "evidence_points": ["A line from another part of the call (14:05)."],
                       "guardrail": "The model's guardrail.", "reader_takeaway": "I want a team that looks past the lead."}
    asked = call("POST", f"/angles/{top['angle_id']}/refresh", {"expected_hash": top["content_hash"], "feedback": FEEDBACK}, EDITOR)
    assert asked.status_code == 202, asked.text
    assert asked.json()["kept"] == ["guardrail"]
    drain(worker)
    (sent,) = provider.refreshes
    assert sent["schema"] == refresh.SCHEMA_V7 and sent["system"].startswith(refresh.template_text(v7).strip())
    new = next(a for a in repo.review(W1, APPROVER)["angles"] if a["content_body"].get("refresh"))
    after, made = new["content_body"]["card"], new["content_body"]["refresh"]
    assert after["public_stance"] == stance and after["evidence_points"] == provider.answer["evidence_points"]
    assert after["reader_takeaway"] == provider.answer["reader_takeaway"] and after["title"] == provider.answer["title"]
    assert after["guardrail"] == v7["guardrail"] and made["kept"] == ["guardrail"], "her guardrail is put back"
    assert made["prompt_version"] == refresh.PROFILE_V7 and "public_stance" in made["changed"] and "evidence_points" in made["changed"]
    assert "stance_confirmation" not in new["content_body"], "a confirmed stance does not carry over to new words"


def test_a_refresh_keeps_the_edited_title_word_for_word_and_changes_a_field_she_did_not_edit(gate):
    repo, worker, provider, call = gate
    top = ranked(repo.review(W1, APPROVER))[0]
    before = top["content_body"]["card"]

    # (a) Any card field is editable, and the screen's edit records which fields a person wrote.
    mine = edited(repo, call, top, {"title": EDITED_TITLE, "audience": before["audience"]})
    assert mine["content_body"]["card"]["title"] == EDITED_TITLE
    assert mine["content_body"]["person_edits"] == ["title"], "an unchanged field sent with the edit is not recorded"

    # A stale hash is a conflict and queues nothing.
    stale = call("POST", f"/angles/{mine['angle_id']}/refresh", {"expected_hash": top["content_hash"], "feedback": FEEDBACK})
    assert stale.status_code == 409 and "refresh before saving" in stale.json()["detail"]
    assert refresh_runs(repo) == []
    assert call("POST", f"/angles/{mine['angle_id']}/refresh", {"expected_hash": mine["content_hash"], "feedback": FEEDBACK},
                "nobody@example.invalid").status_code == 403

    asked = call("POST", f"/angles/{mine['angle_id']}/refresh", {"expected_hash": mine["content_hash"], "feedback": FEEDBACK,
                                                                  "author": "Whitney Hodges"}, EDITOR)
    assert asked.status_code == 202, asked.text
    assert asked.json()["kept"] == ["title"] and asked.json()["mode"] == "synthetic"
    again = call("POST", f"/angles/{mine['angle_id']}/refresh", {"expected_hash": mine["content_hash"], "feedback": FEEDBACK})
    assert again.status_code == 409 and "already being written" in again.json()["detail"]
    waiting = card_now(repo, mine["angle_id"])["refresh"]
    assert waiting["status"] == "queued" and waiting["feedback"] == FEEDBACK and waiting["kept"] == ["title"]

    drain(worker)
    (sent,) = provider.refreshes
    assert sent["user"].startswith("Reviewer's feedback:\n" + FEEDBACK)
    assert f"- title: {json.dumps(EDITED_TITLE)}" in sent["user"], "the prompt lists the edited title as fixed"
    assert sent["system"].startswith(refresh.template_text().strip())
    review = repo.review(W1, APPROVER)
    new = next(a for a in review["angles"] if a["content_body"].get("refresh"))
    recorded = json.loads(json.loads(RECORDED.read_text(encoding="utf-8"))["choices"][0]["message"]["content"])
    after = new["content_body"]["card"]
    assert new["supersedes_id"] == mine["angle_id"] and new["approval_status"] == "pending"
    # The recorded answer rewrote the title; the lock put the reviewer's words back, character for character.
    assert recorded["title"] != EDITED_TITLE and after["title"] == EDITED_TITLE
    assert after["why_it_matters"] == recorded["why_it_matters"] != before["why_it_matters"]
    assert after["core_perspective"] == recorded["core_perspective"] != before["core_perspective"]
    assert after["evidence_points"] == before["evidence_points"] and after["moment_ids"] == before["moment_ids"]
    assert after["rank"] == before["rank"] and after["verify_before_publishing"] == before["verify_before_publishing"]
    made = new["content_body"]["refresh"]
    assert made["maker"] == "model" and made["feedback"] == FEEDBACK and made["author"] == "Whitney Hodges"
    assert made["kept"] == ["title"] and made["changed"] == ["core_perspective", "why_it_matters"]
    assert made["prompt_version"] == refresh.PROFILE and made["reason"] == recorded["reason"]
    assert new["content_body"]["person_edits"] == ["title"], "the model's fields are not a person's edits"
    # Re-verified like any reframe: its own ledger, and its comparison check before it can be developed.
    with repo.connection() as conn:
        rechecked = carry_forward(mine["content_body"]["ledger"], mine["content_body"]["card"], after,
                                  ledger_from_database(conn, after))
    assert new["content_body"]["ledger"] == rechecked, "the ledger is the rule checks run on the refreshed text"
    assert new["check"]["status"] == "checked" and new["refresh"] is None
    assert not any(a["angle_id"] == mine["angle_id"] for a in review["angles"] if not a["has_replacement"])
    with repo.connection() as conn:
        event = conn.execute("SELECT details FROM pipeline_events WHERE event_type='card_refreshed'").fetchone()["details"]
        call_row = conn.execute("SELECT * FROM llm_runs WHERE prompt_version=%s", (refresh.PROFILE,)).fetchone()
        job = conn.execute("SELECT queue,status FROM pipeline_jobs WHERE stage='card_refresh'").fetchone()
    assert event["locked_changed_by_model"] == ["title"] and event["kept"] == ["title"]
    assert call_row["status"] == "succeeded" and call_row["stage"] == "card_verification"
    assert job == {"queue": "interactive", "status": "completed"}
    (run,) = refresh_runs(repo)
    assert run["input_refs"]["prompt_sha256"] == canonical_hash(refresh.template_text()) and run["status"] == "completed"

    # A later person's edit of another field is recorded beside the first; the refresh record goes with the model's version.
    later = edited(repo, call, new, {"why_it_matters": "Fit beats volume for a planner with a full inbox."})
    assert later["content_body"]["person_edits"] == ["title", "why_it_matters"] and "refresh" not in later["content_body"]


@pytest.mark.parametrize("failure,reason", [
    (RunPlanError("Run plan weekly-refreshes would pass its cap of USD 2.00"), "spending limit for model calls"),
    (httpx.HTTPStatusError("Client error '402 Payment Required'", request=httpx.Request("POST", "https://llm.example.invalid"),
                           response=httpx.Response(402)), "out of credit"),
])
def test_a_refused_refresh_shows_its_reason_on_the_card(gate, failure, reason):
    repo, worker, provider, call = gate
    top = ranked(repo.review(W1, APPROVER))[0]
    provider.failure = failure
    assert call("POST", f"/angles/{top['angle_id']}/refresh", {"expected_hash": top["content_hash"],
                                                              "feedback": FEEDBACK}).status_code == 202
    drain(worker)
    card = card_now(repo, top["angle_id"])
    assert card["content_hash"] == top["content_hash"] and not card["has_replacement"], "the card is unchanged"
    shown = card["refresh"]
    assert shown["status"] == "failed" and reason in shown["message"] and shown["feedback"] == FEEDBACK
    assert type(failure).__name__ not in shown["message"], "the reviewer reads the reason, not the exception"
    with repo.connection() as conn:
        summary = conn.execute("SELECT error_summary FROM pipeline_jobs WHERE stage='card_refresh'").fetchone()["error_summary"]
    assert type(failure).__name__ in summary, "the team still sees the detail"
    # Asking again is allowed once the failure is shown.
    provider.failure = None
    assert call("POST", f"/angles/{top['angle_id']}/refresh", {"expected_hash": top["content_hash"],
                                                              "feedback": FEEDBACK}).status_code == 202


def test_a_refresh_spends_the_refreshes_budget_and_waits_for_it_with_the_reason_on_the_card(gate):
    repo, worker, provider, call = gate
    top = ranked(repo.review(W1, APPROVER))[0]
    spent = ("This week's refreshes budget has USD 0.01 left of USD 2.00, and the next call could cost up to USD 0.05, so it "
             "was not sent. It renews on Monday 26 October at 00:00 UTC, or an administrator can raise it.")
    purposes = []

    class Refusing(RefreshProvider):
        def json_call(self, *, stage, system, user, schema, fingerprint):
            if user.startswith("Reviewer's feedback:"):
                purposes.append(standing.purpose_of(stage))
                raise BudgetExhausted(spent, purpose="refreshes", plan_id="plan_standing_refreshes_20261019", left_usd=0.01)
            return super().json_call(stage=stage, system=system, user=user, schema=schema, fingerprint=fingerprint)

    refusing = SQLWorker(repo.settings, worker.models, provider=Refusing())
    assert call("POST", f"/angles/{top['angle_id']}/refresh", {"expected_hash": top["content_hash"],
                                                              "feedback": FEEDBACK}).status_code == 202
    drain(refusing)
    assert purposes == ["refreshes"], "the call spends the refreshes budget, not the cycle's (its stage's own purpose)"
    shown = card_now(repo, top["angle_id"])["refresh"]
    assert shown["status"] == "waiting" and shown["feedback"] == FEEDBACK
    assert shown["message"].startswith("This week's refreshes budget has USD 0.01 left") and "storage_cli" not in shown["message"]
    with repo.connection() as conn:
        job = conn.execute("SELECT status,progress_details FROM pipeline_jobs WHERE stage='card_refresh'").fetchone()
    assert job["status"] == "waiting" and job["progress_details"]["budget_purpose"] == "refreshes"
    again = call("POST", f"/angles/{top['angle_id']}/refresh", {"expected_hash": top["content_hash"], "feedback": FEEDBACK})
    assert again.status_code == 409, "one refresh waits per card"


def test_replay_without_a_saved_answer_and_closed_cards_are_explained(gate):
    repo, worker, provider, call = gate
    top, second = ranked(repo.review(W1, APPROVER))[:2]
    assert call("POST", f"/angles/{top['angle_id']}/refresh", {"expected_hash": top["content_hash"], "feedback": FEEDBACK,
                                                              "mode": "replay"}).status_code == 202
    drain(worker)
    assert provider.refreshes == [], "replay never calls the provider"
    assert card_now(repo, top["angle_id"])["refresh"]["message"].startswith("Model calls are switched off")
    assert call("POST", f"/angles/{top['angle_id']}/refresh", {"expected_hash": top["content_hash"], "feedback": "  "}).status_code == 409
    skipped = call("POST", f"/angles/{second['angle_id']}/decision", {"expected_hash": second["content_hash"], "disposition": "skip",
                                                                     "reason_code": "duplicate"})
    assert skipped.status_code == 200
    closed = call("POST", f"/angles/{second['angle_id']}/refresh", {"expected_hash": second["content_hash"], "feedback": FEEDBACK})
    assert closed.status_code == 409 and "already has a decision" in closed.json()["detail"]


def test_a_card_edited_while_the_refresh_waits_is_not_overwritten(gate):
    repo, worker, provider, call = gate
    top = ranked(repo.review(W1, APPROVER))[0]
    assert call("POST", f"/angles/{top['angle_id']}/refresh", {"expected_hash": top["content_hash"],
                                                              "feedback": FEEDBACK}).status_code == 202
    mine = edited(repo, call, top, {"title": EDITED_TITLE})
    drain(worker)
    assert card_now(repo, mine["angle_id"])["content_body"]["card"]["title"] == EDITED_TITLE
    with repo.connection() as conn:
        summary = conn.execute("SELECT error_summary FROM pipeline_jobs WHERE stage='card_refresh'").fetchone()["error_summary"]
        versions = conn.execute("SELECT count(*) n FROM content_angles WHERE content_body ? 'refresh'").fetchone()["n"]
    assert summary.startswith("The card changed while the refreshed version was being written") and versions == 0
