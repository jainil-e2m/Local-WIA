"""S.B3: Gate 1 roles in every mode, cards included, bound to the verified email (R37)."""
from __future__ import annotations

from contextlib import contextmanager
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend_pipeline import gate_one
from backend_pipeline.sql_pipeline import SQLWorker
from backend_pipeline.storage_api import router
from backend_pipeline.tests.test_cards_sql import DECIDE, W1, cards_setup  # noqa: F401 (fixture)
from backend_pipeline.tests.test_sql_storage import URL, NonemptyProvider, drain, setup  # noqa: F401 (fixture)

APPROVER, EDITOR, VIEWER = "whitney@example.invalid", "editor@example.invalid", "viewer@example.invalid"


def roles_repo(row):
    @contextmanager
    def connection():
        class Conn:
            def execute(self, statement, params=()):
                if "SELECT moment_id" in statement:
                    return [{"moment_id": "moment_a"}]
                if "SELECT moment_body" in statement:
                    return [{"moment_body": {"qualifications": []}}]
                raise AssertionError(statement)
        yield Conn()
    return SimpleNamespace(connection=connection, event=lambda *a, **k: None,
                           settings=SimpleNamespace(brief_approvers=(APPROVER,), brief_editors=(EDITOR,), brief_enabled=False))


@pytest.mark.parametrize("actor,capability,allowed", [
    (APPROVER, "decide", True), (EDITOR, "decide", False), (VIEWER, "decide", False), ("", "decide", False),
    (APPROVER, "edit", True), (EDITOR, "edit", True), (VIEWER, "edit", False)])
def test_require_matches_the_role_lists(actor, capability, allowed):
    repo = roles_repo({})
    if allowed:
        gate_one.require(repo, actor, capability)
    else:
        with pytest.raises(PermissionError):
            gate_one.require(repo, actor, capability)


@pytest.mark.parametrize("decision", ["approved", "rejected"])
def test_decisions_need_an_approver_before_anything_is_read(decision):
    repo = roles_repo({})
    repo.connection = lambda: (_ for _ in ()).throw(AssertionError("no database access before the role check"))
    for actor in (EDITOR, VIEWER):
        with pytest.raises(PermissionError):
            gate_one.decide(repo, "angle_x", "h", decision, None, False, None, actor)


def test_an_editor_cannot_move_readiness_and_an_approver_needs_a_note(monkeypatch):
    strategy = {"title": "T", "core_perspective": "P", "audience": "A", "tension": "X", "evidence_readiness": "research_required",
                "research_questions": ["Which client said it?"]}
    row = {"angle_id": "angle_s", "content_body": {"strategy": strategy, "title": "T"}, "week_id": "w", "run_id": "r",
           "first_generated_at": None, "embedding": None, "embedding_input_hash": None}
    repo = roles_repo(row)
    monkeypatch.setattr(gate_one, "locked", lambda *a, **k: row)
    monkeypatch.setattr(gate_one, "insert", lambda *a, **k: None)
    change = {"evidence_readiness": "supported", "research_questions": []}
    with pytest.raises(PermissionError):
        gate_one.edit(repo, "angle_s", "h", change, EDITOR)
    with pytest.raises(ValueError, match="needs a note"):
        gate_one.edit(repo, "angle_s", "h", change, APPROVER)
    with pytest.raises(PermissionError):
        gate_one.edit(repo, "angle_s", "h", {"title": "New"}, VIEWER)


# Database suite: every decision route, every mode, legacy and card angles -------------------------------------

def client_for(repo):
    repo.settings.api_secret = "test-secret"
    repo.settings.brief_approvers = (APPROVER,)
    repo.settings.brief_editors = (EDITOR,)
    app = FastAPI()
    app.include_router(router(repo.settings))
    client = TestClient(app)

    def call(method, path, email, **kwargs):
        headers = {"Authorization": "Bearer test-secret", "X-Atelier-Actor": email or "unknown"}
        if email:
            headers["X-Atelier-Email"] = email
        return client.request(method, path, headers=headers, **kwargs)
    return call


def routes(angle, week):
    body = {"expected_hash": angle["content_hash"]}
    return [("PATCH", f"/storage/angles/{angle['angle_id']}", {**body, "changes": {"title": "Edited"}}, "edit"),
            ("POST", f"/storage/angles/{angle['angle_id']}/quality",
             {**body, "scores": {"grounding": 5., "source_relevance": 5., "audience_fit": 5., "specificity": 5.,
                                 "editorial_usefulness": 5., "reasons": ["r"]}}, "edit"),
            ("POST", f"/storage/angles/{angle['angle_id']}/decision", {**body, "decision": "approved", "cta": DECIDE}, "decide"),
            ("POST", f"/storage/angles/{angle['angle_id']}/decision", {**body, "decision": "rejected", "note": "No"}, "decide"),
            ("POST", f"/storage/weeks/{week}/reassess", None, "edit")]


@pytest.mark.skipif(not URL, reason="Requires isolated atelier_test")
@pytest.mark.parametrize("briefs_enabled", [False, True])
def test_non_approvers_get_403_on_every_gate_one_route_in_every_mode(setup, briefs_enabled):
    repo, models, _ = setup
    repo.settings.brief_enabled = briefs_enabled
    worker = SQLWorker(repo.settings, models, provider=NonemptyProvider())
    repo.submit("week_2026-06-01", "synthetic")
    drain(worker)
    call = client_for(repo)
    angle = next(a for a in repo.review("week_2026-06-01")["angles"])
    for method, path, payload, capability in routes(angle, "week_2026-06-01"):
        assert call(method, path, VIEWER, json=payload).status_code == 403, (path, VIEWER)
        if capability == "decide":
            assert call(method, path, EDITOR, json=payload).status_code == 403, (path, EDITOR)
        # Without the verified email the route refuses before any role check.
        assert call(method, path, None, json=payload).status_code == 401, path
    review = call("GET", "/storage/weeks/week_2026-06-01", VIEWER).json()
    assert not any(a["can_approve"] or a["can_edit"] or a["can_reject"] for a in review["angles"])
    review = call("GET", "/storage/weeks/week_2026-06-01", EDITOR).json()
    assert all(a["can_edit"] and not a["can_approve"] and not a["can_reject"] for a in review["angles"] if not a["has_replacement"])


@pytest.mark.skipif(not URL, reason="Requires isolated atelier_test")
def test_card_decisions_need_an_approver(cards_setup):
    repo, models, provider, worker = cards_setup
    repo.submit(W1, "synthetic", models=models)
    drain(worker)
    call = client_for(repo)
    top = next(a for a in repo.review(W1, APPROVER)["angles"] if a["content_body"].get("card"))
    payload = {"expected_hash": top["content_hash"], "decision": "approved", "cta": DECIDE,
               "verify_acknowledged": top["content_body"]["card"]["verify_before_publishing"]}
    for email in (VIEWER, EDITOR):
        assert call("POST", f"/storage/angles/{top['angle_id']}/decision", email, json=payload).status_code == 403
    edit = call("PATCH", f"/storage/angles/{top['angle_id']}", EDITOR,
                json={"expected_hash": top["content_hash"], "changes": {"why_it_matters": "Owners see the process."}})
    assert edit.status_code == 200
    accepted = call("POST", f"/storage/angles/{top['angle_id']}/decision", APPROVER, json=payload)
    assert accepted.status_code == 409, "the approver reaches the card rule; the edit made the old version stale"


@pytest.mark.skipif(not URL, reason="Requires isolated atelier_test")
def test_an_edit_missing_its_note_is_a_request_to_complete_not_a_conflict(cards_setup):
    """N1 shakedown: editing a held card without a note answered 409, which the app shows as "this changed while you were
    working on it" with a reload. It is 422 now, shown beside the form; a stale version is still a 409 conflict."""
    import json as _json
    repo, models, provider, worker = cards_setup
    repo.submit(W1, "synthetic", models=models)
    drain(worker)
    call = client_for(repo)
    top = next(a for a in repo.review(W1, APPROVER)["angles"] if a["content_body"].get("card"))
    with repo.connection() as conn:
        body = {**top["content_body"], "gate_one_hold": {"until": "2026-11-08", "reason": "offer"}}
        conn.execute("UPDATE content_angles SET content_body=%s WHERE angle_id=%s", (_json.dumps(body), top["angle_id"]))
    held = next(a for a in repo.review(W1, APPROVER)["angles"] if a["angle_id"] == top["angle_id"])
    path, change = f"/storage/angles/{top['angle_id']}", {"why_it_matters": "Owners see the process."}
    missing = call("PATCH", path, APPROVER, json={"expected_hash": held["content_hash"], "changes": change})
    assert missing.status_code == 422 and "needs a note" in missing.json()["detail"]
    assert call("PATCH", path, APPROVER, json={"expected_hash": "stale", "changes": change, "note": "Why"}).status_code == 409
    done = call("PATCH", path, APPROVER, json={"expected_hash": held["content_hash"], "changes": change, "note": "Checked the offer."})
    assert done.status_code == 200


def card_edit_repo(monkeypatch, body):
    """An offline repository for card edits: one locked card row and the inserts it writes."""
    row = {"angle_id": "angle_card", "content_body": body, "week_id": "w", "run_id": "r",
           "first_generated_at": None, "embedding": None, "embedding_input_hash": None}

    @contextmanager
    def connection():
        class Conn:
            def execute(self, statement, params=()):
                assert statement.startswith("SELECT moment_id FROM angle_moments"), statement
                return [{"moment_id": "moment_a"}]
        yield Conn()

    writes = []
    repo = SimpleNamespace(connection=connection, event=lambda *a, **k: None,
                           settings=SimpleNamespace(brief_approvers=(APPROVER,), brief_editors=(EDITOR,)))
    monkeypatch.setattr(gate_one, "locked", lambda *a, **k: row)
    monkeypatch.setattr(gate_one, "insert", lambda conn, table, data: writes.append((table, data)))
    # The new version's comparison check is queued in the database (test_gate_one_decisions_db.py covers it).
    monkeypatch.setattr(gate_one, "queue_card_check", lambda *a, **k: {"status": "queued"})
    return repo, writes


def test_an_editor_cannot_remove_what_the_approver_must_check_or_lift_a_hold(monkeypatch):
    """S.B3: removing a verify-before-publishing item, or editing a held card, is an approver action with a note.

    Otherwise an editor's plain edit empties the list the approver must acknowledge at approval (E.B16 b), or drops an
    approver's hold, with no approver action recorded.
    """
    from backend_pipeline.tests.test_cards_downstream import card_body
    body = card_body()
    assert body["card"]["verify_before_publishing"], "the fixture card carries an item to check"
    repo, writes = card_edit_repo(monkeypatch, body)
    with pytest.raises(PermissionError):
        gate_one.edit(repo, "angle_card", "h", {"verify_before_publishing": []}, EDITOR)
    with pytest.raises(ValueError, match="note"):
        gate_one.edit(repo, "angle_card", "h", {"verify_before_publishing": []}, APPROVER)
    assert writes == []
    gate_one.edit(repo, "angle_card", "h", {"verify_before_publishing": []}, APPROVER, "Checked the date against the call")
    assert writes and writes[0][1]["content_body"]["card"]["verify_before_publishing"] == []
    # Adding a check, or editing other text, stays an editor's edit.
    writes.clear()
    more = [*body["card"]["verify_before_publishing"], "Confirm the client agreed to be named"][:2]
    gate_one.edit(repo, "angle_card", "h", {"verify_before_publishing": more}, EDITOR)
    gate_one.edit(repo, "angle_card", "h", {"why_it_matters": "Owners see the process."}, EDITOR)
    assert len([w for w in writes if w[0] == "content_angles"]) == 2

    held = {**card_body(), "gate_one_hold": {"until": "2099-01-01", "reason_code": "timing", "note": None, "author": APPROVER}}
    repo, writes = card_edit_repo(monkeypatch, held)
    with pytest.raises(PermissionError):
        gate_one.edit(repo, "angle_card", "h", {"why_it_matters": "Owners see the process."}, EDITOR)
    gate_one.edit(repo, "angle_card", "h", {"why_it_matters": "Owners see the process."}, APPROVER, "Released early")
    assert "gate_one_hold" not in writes[0][1]["content_body"]
