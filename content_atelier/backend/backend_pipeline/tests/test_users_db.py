"""0.B9 on a migrated database: a `users` row changes what every route allows; the seed and `users` commands; GET /storage/me.

Synthetic emails only. The platform database (005 and later) comes from platform_db.py.
"""
from __future__ import annotations

import json

import pytest
from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from backend_pipeline.database import connect
from backend_pipeline.gates import roles
from backend_pipeline.intake.api import routers as intake_routers
from backend_pipeline.intake.config import IntakeSettings
from backend_pipeline.storage_api import router
from backend_pipeline.storage_config import StorageSettings
from backend_pipeline.tests.platform_db import empty, platform_url  # noqa: F401 (fixture)

PEOPLE = {role: f"{role}@example.invalid" for role in roles.ROLES}
LISTED_APPROVER = "listed.approver@example.invalid"
SECRET = "test-secret"


@pytest.fixture
def stack(platform_url, tmp_path):  # noqa: F811
    """A migrated, empty database, one person per role in `users`, and the production routers over it."""
    empty(platform_url)
    settings = StorageSettings(database_url=platform_url, artifact_root=tmp_path / "artifacts", synthetic=True, api_secret=SECRET,
                               brief_enabled=True, packs_enabled=True, calendar_enabled=True, context_enabled=True,
                               brief_approvers=(LISTED_APPROVER,))
    with connect(platform_url, vectors=False) as conn:
        for role, email in PEOPLE.items():
            conn.execute("INSERT INTO users(email,role,name) VALUES (%s,%s,%s)", (email, role, role.title()))
        conn.commit()
    app = FastAPI()
    app.include_router(router(settings))
    for part in intake_routers(settings, IntakeSettings(slack_token="bot-secret", admins=())):
        app.include_router(part)
    client = TestClient(app, raise_server_exceptions=False)

    def call(method, path, email, body=None, actor=None):
        headers = {"Authorization": "Bearer " + SECRET, "X-Atelier-Actor": actor or email or "unknown"}
        if email:
            headers["X-Atelier-Email"] = email
        return client.request(method, path, headers=headers, **({"json": body} if body is not None else {}))
    return settings, app, call


# --- GET /storage/me -----------------------------------------------------------------------------------------------

@pytest.mark.parametrize("role,decide,edit,admin", [("viewer", False, False, False), ("editor", False, True, False),
                                                    ("approver", True, True, False), ("admin", True, True, True)])
def test_me_returns_the_roles_of_the_row(stack, role, decide, edit, admin):
    _, _, call = stack
    answer = call("GET", "/storage/me", PEOPLE[role])
    assert answer.status_code == 200
    body = answer.json()
    assert body["email"] == PEOPLE[role] and body["role"] == role and body["source"] == "users" and body["name"] == role.title()
    assert body["roles"] == [r for r in roles.ROLES if roles.RANK[r] <= roles.RANK[role]]
    assert (body["can"]["decide"], body["can"]["approve_briefs"], body["can"]["edit_cards"], body["can"]["manage_users"]) == (decide, decide, edit, admin)


def test_me_for_people_with_no_row_and_for_malformed_callers(stack):
    settings, app, call = stack
    # On a legacy list only (the users table has no row for them): the lists still work, which is the precedence.
    listed = call("GET", "/storage/me", LISTED_APPROVER.upper()).json()
    assert listed["role"] == "approver" and listed["source"] == "lists" and listed["email"] == LISTED_APPROVER
    # On no list and no row: a viewer, who may read /me and nothing else.
    nobody = call("GET", "/storage/me", "nobody@example.invalid").json()
    assert nobody["role"] == "viewer" and not any(nobody["can"].values())
    # The identity is the verified email only: no email, no /me.
    assert call("GET", "/storage/me", None, actor="user-id-7").status_code == 401
    assert call("GET", "/storage/me", "user-id-7").status_code == 401
    # The email wins over a user id in the actor header, so a spoofed id gains nothing.
    assert call("GET", "/storage/me", PEOPLE["viewer"], actor=PEOPLE["admin"]).json()["role"] == "viewer"
    # And the shared secret is still required.
    bare = TestClient(app)
    assert bare.get("/storage/me", headers={"X-Atelier-Email": PEOPLE["admin"], "X-Atelier-Actor": PEOPLE["admin"]}).status_code == 401
    assert settings.api_secret == SECRET


def test_a_row_demotes_someone_who_is_still_on_a_list(stack):
    settings, _, call = stack
    assert call("GET", "/storage/me", LISTED_APPROVER).json()["role"] == "approver"
    with connect(settings.database_url, vectors=False) as conn:
        conn.execute("INSERT INTO users(email,role) VALUES (%s,'viewer')", (LISTED_APPROVER,))
        conn.commit()
    demoted = call("GET", "/storage/me", LISTED_APPROVER).json()
    assert demoted["role"] == "viewer" and demoted["source"] == "users" and demoted["can"]["decide"] is False
    # The decision routes agree with /me.
    assert call("POST", "/storage/angles/angle_x/decision", LISTED_APPROVER,
                {"expected_hash": "h", "decision": "rejected", "note": "No"}).status_code == 403


# --- every mutating route, by role -----------------------------------------------------------------------------------

H = {"expected_hash": "h"}
ITEM = {"expected_hash": "h" * 12}
SCHEDULE = {"request_id": "request-0001", "expected_pack_manifest_hash": "h", "items": [
    {"asset_id": "asset_x", "expected_asset_hash": "h", "scheduled_for": "2030-01-01T10:00:00+05:30"}]}
# (method, route template, concrete path, body, the lowest role the route accepts)
MATRIX = [
    ("POST", "/storage/weeks/{week_id}/runs", "/storage/weeks/week_x/runs", {"mode": "replay"}, "editor"),
    # A cycle over a date window, from the app (3.B2): an approver's.
    ("POST", "/storage/cycles", "/storage/cycles", {"window_start": "2026-03-09T00:00:00Z", "selection_hash": "abcdef12"}, "approver"),
    ("POST", "/storage/weeks/{week_id}/reassess", "/storage/weeks/week_x/reassess", None, "editor"),
    ("POST", "/storage/jobs/{job_id}/retry", "/storage/jobs/job_x/retry", None, "editor"),
    ("POST", "/storage/runs/{run_id}/encode", "/storage/runs/run_x/encode", {"mode": "replay"}, "editor"),
    ("PATCH", "/storage/angles/{angle_id}", "/storage/angles/angle_x", {**H, "changes": {"title": "T"}}, "editor"),
    ("POST", "/storage/angles/{angle_id}/quality", "/storage/angles/angle_x/quality", {**H, "scores": {}}, "editor"),
    ("POST", "/storage/angles/{angle_id}/decision", "/storage/angles/angle_x/decision", {**H, "decision": "rejected", "note": "No"}, "approver"),
    # Confirming a v7 card's public stance before development (D31, E.B30): an approver's.
    ("POST", "/storage/angles/{angle_id}/stance", "/storage/angles/angle_x/stance", H, "approver"),
    # 3.B7: an editor asks for a refreshed card version; replay and an unknown card, so a passing role ends in a 409.
    ("POST", "/storage/angles/{angle_id}/refresh", "/storage/angles/angle_x/refresh", {**H, "feedback": "Lead with the form.", "mode": "replay"}, "editor"),
    ("POST", "/storage/weeks/{week_id}/considered/{index}/revive", "/storage/weeks/week_x/considered/0/revive", {**H, "card": {}}, "approver"),
    ("POST", "/storage/weeks/{week_id}/considered/{index}/decision", "/storage/weeks/week_x/considered/0/decision",
     {**H, "disposition": "hold", "reason_code": "timing"}, "approver"),
    ("POST", "/storage/seeds", "/storage/seeds", {"kind": "thought", "text": "A thought"}, "editor"),
    ("POST", "/storage/seeds/{seed_id}/withdraw", "/storage/seeds/seed_x/withdraw", None, "editor"),
    ("POST", "/storage/search/transcripts", "/storage/search/transcripts", {"text": "follow-up"}, "viewer"),
    ("POST", "/storage/angles/{angle_id}/brief", "/storage/angles/angle_x/brief", {"mode": "replay"}, "editor"),
    ("POST", "/storage/angles/{angle_id}/brief/retry", "/storage/angles/angle_x/brief/retry", None, "approver"),
    ("PATCH", "/storage/briefs/{brief_id}", "/storage/briefs/brief_x", {**H, "changes": {"title": "T"}}, "editor"),
    ("POST", "/storage/briefs/{brief_id}/answers", "/storage/briefs/brief_x/answers", {**H, "answers": {}}, "approver"),
    ("POST", "/storage/briefs/{brief_id}/review", "/storage/briefs/brief_x/review",
     {**H, "claim_ids": [], "reason": "r", "history_acknowledged": True}, "approver"),
    ("POST", "/storage/briefs/{brief_id}/clearance", "/storage/briefs/brief_x/clearance",
     {**H, "evidence_id": "e", "permission_reference": "p", "attribution_reference": "a"}, "approver"),
    ("POST", "/storage/briefs/{brief_id}/decision", "/storage/briefs/brief_x/decision", {**H, "decision": "rejected", "note": "No"}, "approver"),
    ("POST", "/storage/briefs/{brief_id}/cta", "/storage/briefs/brief_x/cta", {**H, "choice": "no_explicit_ask"}, "approver"),
    ("POST", "/storage/briefs/{brief_id}/revise", "/storage/briefs/brief_x/revise", {**H, "instructions": "Shorter"}, "editor"),
    # 5.B7: context at either gate (an editor); an attested fact needs an approver.
    ("POST", "/storage/angles/{angle_id}/context", "/storage/angles/angle_x/context", {"kind": "context", "text": "A note"}, "editor"),
    ("POST", "/storage/briefs/{brief_id}/context", "/storage/briefs/brief_x/context", {"kind": "attested_fact", "text": "A fact"}, "approver"),
    # L.B9: a published final against its approved brief.
    ("POST", "/storage/briefs/{brief_id}/published", "/storage/briefs/brief_x/published",
     {"channel": "email", "title": "T", "text": "Final copy.", "published_on": "2026-10-18"}, "editor"),
    # Knowledge screens (Phase L): approver-only.
    ("POST", "/storage/context/items/{item_id}/decision", "/storage/context/items/item_x/decision",
     {**ITEM, "action": "accept", "reason": "r"}, "approver"),
    ("POST", "/storage/context/batch", "/storage/context/batch",
     {"action": "accept", "reason": "r", "entries": [{"item_id": "item_x", "expected_hash": "h"}]}, "approver"),
    ("POST", "/storage/context/items", "/storage/context/items", {"kind": "offer", "body": {}, "reason": "r"}, "approver"),
    ("POST", "/storage/context/published/confirm", "/storage/context/published/confirm", {"content_ids": ["c"], "reason": "r"}, "approver"),
    ("POST", "/storage/context/versions", "/storage/context/versions", {}, "approver"),
    ("POST", "/storage/context/versions/{version}/approve", "/storage/context/versions/v1/approve", {"note": "n"}, "approver"),
    ("POST", "/storage/context/versions/{version}/discard", "/storage/context/versions/v1/discard", {}, "approver"),
    ("POST", "/storage/context/versions/{version}/benchmark", "/storage/context/versions/v1/benchmark",
     {"passed": True, "result_ref": "r"}, "approver"),
    ("POST", "/storage/context/published", "/storage/context/published",
     {"published_on": "2026-10-01", "channel": "email", "title": "T"}, "approver"),
    ("POST", "/storage/context/published/import", "/storage/context/published/import", {"csv": "a,b"}, "approver"),
    ("POST", "/storage/context/published/{content_id}/performance", "/storage/context/published/c_x/performance",
     {"on": "2026-10-01", "metric": "views", "value": "10"}, "approver"),
    ("POST", "/storage/context/published/{content_id}/link", "/storage/context/published/c_x/link", {"brief_id": "brief_x"}, "approver"),
    ("POST", "/storage/context/mining", "/storage/context/mining", {}, "approver"),
    # Packs and the calendar (outside scope, R31): they resolve through the same roles.
    ("POST", "/storage/briefs/{brief_id}/pack", "/storage/briefs/brief_x/pack", {"request_id": "request-0001", "expected_brief_hash": "h"}, "editor"),
    ("POST", "/storage/packs/{pack_id}/decision", "/storage/packs/pack_x/decision",
     {"request_id": "request-0001", "expected_manifest_hash": "h", "decision": "rejected", "note": "No"}, "approver"),
    ("POST", "/storage/packs/{pack_id}/schedule", "/storage/packs/pack_x/schedule", SCHEDULE, "editor"),
    # Content pack v2 (NP.B6): an editor edits, reverts and marks published; an approver clears notes, attests and finishes
    # again. The pack does not exist, so a passing role ends in a 404.
    ("PATCH", "/storage/packs/{pack_id}/pieces/{key}", "/storage/packs/pack_x/pieces/email",
     {"request_id": "request-0001", "expected_manifest_hash": "h", "changes": {"preview": "x"}}, "editor"),
    ("POST", "/storage/packs/{pack_id}/pieces/{key}/revert", "/storage/packs/pack_x/pieces/email/revert",
     {"request_id": "request-0001", "expected_manifest_hash": "h", "paths": ["preview"]}, "editor"),
    ("POST", "/storage/packs/{pack_id}/pieces/{key}/published", "/storage/packs/pack_x/pieces/email/published",
     {"request_id": "request-0001", "published_on": "2026-10-20", "channel": "email", "final_text": "x", "url": None}, "editor"),
    ("POST", "/storage/packs/{pack_id}/clearances", "/storage/packs/pack_x/clearances",
     {"request_id": "request-0001", "expected_manifest_hash": "h", "item_id": "P1", "reference": None, "note": None}, "approver"),
    ("POST", "/storage/packs/{pack_id}/findings/{finding_id}/attest", "/storage/packs/pack_x/findings/fid_x/attest",
     {"request_id": "request-0001", "expected_manifest_hash": "h", "statement": "It is true."}, "approver"),
    ("POST", "/storage/packs/{pack_id}/finish", "/storage/packs/pack_x/finish", {"request_id": "request-0001", "expected_manifest_hash": "h"}, "approver"),
    # NP-7: an editor pastes a recorded take (NP.B14); an approver grants a permission and finishes again with it (NP.B15).
    ("POST", "/storage/packs/{pack_id}/pieces/{key}/recorded", "/storage/packs/pack_x/pieces/reel_1/recorded",
     {"request_id": "request-0001", "expected_manifest_hash": "h", "said": "What Whitney said on the recorded take, start to end, as transcribed."},
     "editor"),
    ("POST", "/storage/packs/{pack_id}/refinish", "/storage/packs/pack_x/refinish",
     {"request_id": "request-0001", "expected_manifest_hash": "h", "grants": [{"item_id": "S1", "statement": "The client agreed."}]}, "approver"),
    ("PATCH", "/storage/calendar/{entry_id}", "/storage/calendar/entry_x",
     {"request_id": "request-0001", "expected_revision": 1, "scheduled_for": "2030-01-01T10:00:00+05:30"}, "editor"),
    ("POST", "/storage/calendar/{entry_id}/cancel", "/storage/calendar/entry_x/cancel", {"request_id": "request-0001", "expected_revision": 1}, "editor"),
    # Settings (0.B8): an approver or above writes; the key is unknown, so a passing role ends in a 422 and changes nothing.
    ("PUT", "/storage/settings/{key}", "/storage/settings/no.such.key", {"value": 1}, "approver"),
    # A failure alert dismissed in the app (6.B4): a decider's, as the other writes on the work.
    ("POST", "/storage/alerts/{alert_id}/dismiss", "/storage/alerts/alert_x/dismiss", None, "editor"),
    # Documents (1.B8): an editor sets what kind of call a document is; the document does not exist, so a passing role ends in a 404.
    ("POST", "/storage/documents/{transcript_id}/classification", "/storage/documents/nope/classification",
     {"call_type": "internal", "reason": "The check-in was internal"}, "editor"),
    # 1.F7: an editor uploads a transcript file; this one holds no passage, so a passing role ends in a 422.
    ("POST", "/storage/documents/import", "/storage/documents/import", {"filename": "empty.vtt", "content": "WEBVTT\n"}, "editor"),
    # Search and the topic registry (Phase 2): anyone searches; an editor files a moment under topics; an approver administers them.
    # The moment and the topics do not exist, so a passing role ends in a 404.
    ("POST", "/storage/search", "/storage/search", {"text": "follow-up"}, "viewer"),
    ("POST", "/storage/moments/{moment_id}/topics", "/storage/moments/m_x/topics", {"add": ["topic_x"]}, "editor"),
    ("POST", "/storage/topics/{topic_id}/rename", "/storage/topics/topic_x/rename", {"name": "A better name"}, "approver"),
    ("POST", "/storage/topics/{topic_id}/merge", "/storage/topics/topic_x/merge", {"into_topic_id": "topic_y"}, "approver"),
    ("POST", "/storage/topics/{topic_id}/block", "/storage/topics/topic_x/block", {}, "approver"),
    ("POST", "/storage/topics/{topic_id}/unblock", "/storage/topics/topic_x/unblock", {}, "approver"),
    # Intake administration.
    ("POST", "/storage/intake/connections/{provider}/activate", "/storage/intake/connections/slack/activate", None, "admin"),
    ("POST", "/storage/intake/refresh", "/storage/intake/refresh", None, "admin"),
    ("POST", "/storage/intake/complete", "/storage/intake/complete", None, "admin"),
    ("POST", "/storage/intake/jobs/{job_id}/retry", "/storage/intake/jobs/job_x/retry", None, "admin"),
    ("POST", "/storage/intake/search", "/storage/intake/search", {"text": "follow-up"}, "viewer"),
]
# Variants of a template whose requirement depends on the body.
VARIANTS = [
    ("POST", "/storage/weeks/{week_id}/runs", "/storage/weeks/week_x/runs", {"mode": "live"}, "approver"),
    ("POST", "/storage/runs/{run_id}/encode", "/storage/runs/run_x/encode", {"mode": "live"}, "approver"),
    ("POST", "/storage/angles/{angle_id}/decision", "/storage/angles/angle_x/decision",
     {**H, "disposition": "skip", "reason_code": "timing"}, "approver"),
]
SERVICE_ROUTES = {("POST", "/intake/v1/slack/batches"), ("PUT", "/intake/v1/assets/{asset_id}/content")}


def test_the_matrix_names_every_mutating_route_of_the_app(stack):
    _, app, _ = stack
    templates = {(m, r.path) for r in app.routes if isinstance(r, APIRoute) for m in r.methods - {"GET", "HEAD", "OPTIONS"}}
    named = {(m, t) for m, t, *_ in MATRIX}
    assert templates - SERVICE_ROUTES == named, (templates - SERVICE_ROUTES) ^ named


@pytest.mark.parametrize("entry", MATRIX + VARIANTS, ids=lambda e: f"{e[0]} {e[2]} {(e[3] or {}).get('mode') or (e[3] or {}).get('disposition') or ''}")
def test_a_users_row_changes_what_each_mutating_route_allows(stack, entry):
    _, _, call = stack
    method, _, path, body, lowest = entry
    for role in roles.ROLES:
        status = call(method, path, PEOPLE[role], body).status_code
        if roles.RANK[role] < roles.RANK[lowest]:
            assert status == 403, f"{role} must be refused by {method} {path}, got {status}"
        else:
            assert status not in (401, 403), f"{role} must pass the role check of {method} {path}, got {status}"
    # No verified email, no entry: the roles are keyed by it alone.
    assert call(method, path, None, body, actor="user-id-7").status_code == 401
    assert call(method, path, "user-id-7", body).status_code == 401


# Reads that resolve the caller's role like the brief routes (Depends(decider)): every role reads, no verified email is a 401.
READS = [
    # E.B23: the production hand-off of a brief; the brief does not exist, so a passing role ends in "Brief not found".
    ("GET", "/storage/briefs/{brief_id}/handoff", "/storage/briefs/brief_x/handoff", None, "viewer"),
    ("GET", "/storage/briefs/{brief_id}", "/storage/briefs/brief_x", None, "viewer"),
]


def test_the_brief_reads_resolve_every_role_and_name_routes_of_the_app(stack):
    _, app, call = stack
    templates = {(m, r.path) for r in app.routes if isinstance(r, APIRoute) for m in r.methods}
    for method, template, path, body, lowest in READS:
        assert (method, template) in templates, template
        for role in roles.ROLES:
            status = call(method, path, PEOPLE[role], body).status_code
            assert status not in (401, 403), f"{role} must pass the role check of {method} {path}, got {status}"
        assert call(method, path, None, body, actor="user-id-7").status_code == 401
        assert call(method, path, "user-id-7", body).status_code == 401


def test_the_matrix_agrees_with_me_for_every_role(stack):
    _, _, call = stack
    for role, email in PEOPLE.items():
        can = call("GET", "/storage/me", email).json()["can"]
        assert can["decide"] == (roles.RANK[role] >= roles.RANK["approver"])
        assert can["edit_cards"] == (roles.RANK[role] >= roles.RANK["editor"])
        assert can["manage_users"] == (role == "admin")


# --- reads mark what the caller may do, from the same resolution ---------------------------------------------------------

def test_the_review_and_brief_flags_follow_the_row(stack):
    settings, _, call = stack
    from backend_pipeline.repository import ContentRepository
    repo = ContentRepository(settings)
    # The viewer, editor and approver rows reach the weekly review without error and see their own flags.
    with connect(settings.database_url, vectors=False) as conn:
        conn.execute("INSERT INTO weeks(week_id,week_start,week_end,status) VALUES ('week_r','2026-06-01','2026-06-07','reviewed')")
        conn.commit()
    for role in roles.ROLES:
        answer = call("GET", "/storage/weeks/week_r", PEOPLE[role])
        assert answer.status_code == 200, answer.text
    assert repo.review("week_r", roles.actor_for(repo, PEOPLE["editor"]))["angles"] == []
    assert call("GET", "/storage/calendar/config", PEOPLE["editor"]).json()["can_schedule"] is True
    assert call("GET", "/storage/calendar/config", PEOPLE["viewer"]).json()["can_schedule"] is False


# --- the seed and users commands --------------------------------------------------------------------------------------------

def lists():
    return StorageSettings(
        brief_approvers=("Ann@Example.invalid", "both@example.invalid", "tester"), brief_editors=("both@example.invalid", "ed@example.invalid"),
        pack_editors=("pack@example.invalid",), calendar_schedulers=("cal@example.invalid",),
        intake_admins=("ops@example.invalid",), identity_approvers=("whitney@example.invalid", "ann@example.invalid"))


def rows(url):
    with connect(url, vectors=False) as conn:
        return {r["email"]: r["role"] for r in conn.execute("SELECT email,role FROM users")}


def test_seed_creates_rows_from_the_lists_and_is_idempotent(platform_url):  # noqa: F811
    empty(platform_url)
    settings = lists().model_copy(update={"database_url": platform_url})
    with connect(platform_url, vectors=False) as conn:
        first = roles.seed(conn, settings, actor="Operator@Example.invalid")
        conn.commit()
    assert rows(platform_url) == {"ann@example.invalid": "approver", "both@example.invalid": "approver", "ed@example.invalid": "editor",
                                  "pack@example.invalid": "editor", "cal@example.invalid": "editor", "ops@example.invalid": "admin",
                                  "whitney@example.invalid": "viewer"}
    assert len(first["created"]) == 7 and first["skipped_not_email"] == ["tester"] and first["total_rows"] == 7
    # What the rows allow that the lists did not (one role cannot say it), named so the operator can lower it.
    gains = {g["email"]: g["gains"] for g in first["gains_beyond_the_lists"]}
    assert "approve_briefs" in gains["ops@example.invalid"] and "cal@example.invalid" in gains
    assert "edit_cards" in gains["cal@example.invalid"]
    # The second run changes nothing and says so.
    with connect(platform_url, vectors=False) as conn:
        second = roles.seed(conn, settings, actor="operator@example.invalid")
        conn.commit()
    assert second["created"] == [] and second["updated"] == [] and second["differs"] == [] and second["total_rows"] == 7
    # Who ran it is recorded, first and last.
    with connect(platform_url, vectors=False) as conn:
        last = conn.execute("SELECT value,updated_by FROM settings WHERE key='users.seed.last'").fetchone()
    assert last["updated_by"] == "operator@example.invalid" and last["value"]["created"] == []


def test_seed_never_overwrites_what_an_administrator_set_unless_asked(platform_url):  # noqa: F811
    empty(platform_url)
    settings = lists().model_copy(update={"database_url": platform_url})
    with connect(platform_url, vectors=False) as conn:
        roles.seed(conn, settings, actor="op@example.invalid")
        conn.execute("UPDATE users SET role='viewer' WHERE email='ann@example.invalid'")
        conn.commit()
    with connect(platform_url, vectors=False) as conn:
        kept = roles.seed(conn, settings, actor="op@example.invalid")
        conn.commit()
    assert rows(platform_url)["ann@example.invalid"] == "viewer"
    assert kept["differs"] == [{"email": "ann@example.invalid", "row": "viewer", "lists": "approver"}]
    with connect(platform_url, vectors=False) as conn:
        forced = roles.seed(conn, settings, actor="op@example.invalid", overwrite=True)
        conn.commit()
    assert rows(platform_url)["ann@example.invalid"] == "approver"
    assert forced["updated"] == [{"email": "ann@example.invalid", "from": "viewer", "to": "approver"}]


def test_users_set_needs_an_administrator_and_lowercases_the_email(platform_url):  # noqa: F811
    empty(platform_url)
    settings = StorageSettings(database_url=platform_url, intake_admins=("boss@example.invalid",))
    with connect(platform_url, vectors=False) as conn:
        with pytest.raises(PermissionError):
            roles.set_user(conn, settings, actor="stranger@example.invalid", email="x@example.invalid", role="admin")
        conn.rollback()
        # An administrator on the legacy list may (there are no rows yet), and a row's admin may after that.
        made = roles.set_user(conn, settings, actor="Boss@Example.invalid", email="New.Person@Example.invalid", role="approver",
                              name="New Person", slack_user_id="U123")
        assert made == {"email": "new.person@example.invalid", "name": "New Person", "role": "approver", "slack_user_id": "U123"}
        roles.set_user(conn, settings, actor="boss@example.invalid", email="boss@example.invalid", role="admin")
        with pytest.raises(PermissionError):
            roles.set_user(conn, settings, actor="new.person@example.invalid", email="n@example.invalid", role="viewer")
        again = roles.set_user(conn, settings, actor="boss@example.invalid", email="NEW.person@example.invalid", role="editor")
        assert again["role"] == "editor" and again["slack_user_id"] == "U123" and again["name"] == "New Person"
        with pytest.raises(ValueError, match="email"):
            roles.set_user(conn, settings, actor="boss@example.invalid", email="team-id", role="viewer")
        with pytest.raises(ValueError, match="Role"):
            roles.set_user(conn, settings, actor="boss@example.invalid", email="a@example.invalid", role="owner")
        conn.rollback()
        conn.commit()
    with connect(platform_url, vectors=False) as conn:
        last = conn.execute("SELECT value,updated_by FROM settings WHERE key='users.last_change'").fetchone()
        assert last is None, "the rolled-back changes left no trace"


def test_the_table_refuses_what_the_model_refuses(platform_url):  # noqa: F811
    import psycopg
    empty(platform_url)
    with connect(platform_url, vectors=False) as conn:
        with pytest.raises(psycopg.errors.CheckViolation):
            conn.execute("INSERT INTO users(email,role) VALUES ('Mixed@Example.invalid','viewer')")
        conn.rollback()
        with pytest.raises(psycopg.errors.CheckViolation):
            conn.execute("INSERT INTO users(email,role) VALUES ('team-id','viewer')")
        conn.rollback()
        conn.execute("INSERT INTO users(email,role,slack_user_id) VALUES ('a@example.invalid','viewer','U1')")
        with pytest.raises(psycopg.errors.UniqueViolation):
            conn.execute("INSERT INTO users(email,role,slack_user_id) VALUES ('b@example.invalid','viewer','U1')")


def test_the_users_command_prints_json_and_records_the_actor(platform_url, capsys, monkeypatch):  # noqa: F811
    from backend_pipeline import storage_cli
    empty(platform_url)
    monkeypatch.setenv("ATELIER_DATABASE_URL", platform_url)
    monkeypatch.setenv("ATELIER_BRIEF_APPROVERS", "Ann@Example.invalid")
    monkeypatch.setenv("ATELIER_INTAKE_ADMINS", "ops@example.invalid")
    monkeypatch.setattr(StorageSettings, "from_env", classmethod(lambda cls: cls(
        database_url=platform_url, brief_approvers=("Ann@Example.invalid",), intake_admins=("ops@example.invalid",))))
    storage_cli.main(["users", "seed", "--actor", "Op@Example.invalid"])
    assert json.loads(capsys.readouterr().out)["total_rows"] == 2
    storage_cli.main(["users", "set", "--actor", "ops@example.invalid", "--email", "Z@Example.invalid", "--role", "editor", "--slack-user-id", "U9"])
    assert json.loads(capsys.readouterr().out)["email"] == "z@example.invalid"
    storage_cli.main(["users", "list"])
    listed = {u["email"]: u["role"] for u in json.loads(capsys.readouterr().out)["users"]}
    assert listed == {"ann@example.invalid": "approver", "ops@example.invalid": "admin", "z@example.invalid": "editor"}
    with pytest.raises(PermissionError):
        storage_cli.main(["users", "set", "--actor", "z@example.invalid", "--email", "q@example.invalid", "--role", "admin"])


def test_a_database_without_the_users_table_keeps_working_from_the_lists(platform_url):  # noqa: F811
    """A deployment that has not applied 005 (the shared baseline schema has no users table): the lists decide."""
    with connect(platform_url, vectors=False) as conn:
        conn.execute("ALTER TABLE users RENAME TO users_hidden")
        conn.commit()
    try:
        from backend_pipeline.repository import ContentRepository
        settings = StorageSettings(database_url=platform_url, brief_approvers=("a@example.invalid",), api_secret=SECRET)
        repo = ContentRepository(settings)
        assert roles.load(repo, "A@Example.invalid").can("decide")
        assert roles.load(repo, "z@example.invalid").role == "viewer"
        app = FastAPI()
        app.include_router(router(settings))
        client = TestClient(app)
        answer = client.get("/storage/me", headers={"Authorization": "Bearer " + SECRET, "X-Atelier-Actor": "a@example.invalid"})
        assert answer.status_code == 200 and answer.json()["role"] == "approver" and answer.json()["source"] == "lists"
    finally:
        with connect(platform_url, vectors=False) as conn:
            conn.execute("ALTER TABLE users_hidden RENAME TO users")
            conn.commit()
