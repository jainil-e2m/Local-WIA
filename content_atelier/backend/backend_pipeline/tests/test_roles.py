"""0.B9 offline: the role model, its precedence, the request dependencies, and route coverage.

The database half (a `users` row changing what the routes allow; the seed command; GET /storage/me) is in
test_users_db.py.
"""
from __future__ import annotations

from contextlib import contextmanager
from types import SimpleNamespace

import pytest
from fastapi import Depends, FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from psycopg import OperationalError

from backend_pipeline.gates import access, roles
from backend_pipeline.storage_config import StorageSettings

APPROVER, EDITOR, ADMIN, VIEWER = ("whitney@example.invalid", "giselle@example.invalid", "ops@example.invalid",
                                   "reader@example.invalid")


def lists(**extra):
    return StorageSettings(brief_approvers=(APPROVER,), brief_editors=(EDITOR,), intake_admins=(ADMIN,), **extra)


# --- the model ------------------------------------------------------------------------------------------------

def test_roles_are_ordered_and_each_implies_the_ones_below():
    assert roles.ROLES == ("viewer", "editor", "approver", "admin")
    assert roles.chain("viewer") == {"viewer"}
    assert roles.chain("editor") == {"viewer", "editor"}
    assert roles.chain("approver") == {"viewer", "editor", "approver"}
    assert roles.chain("admin") == set(roles.ROLES)


@pytest.mark.parametrize("value,expected", [
    ("Whitney@Example.Invalid", "whitney@example.invalid"), ("  a@b.c  ", "a@b.c"), ("team-id", None), ("user id@x.y", None),
    ("@x.y", None), ("a@", None), ("a@b@c", None), ("", None), (None, None), (7, None), ("a@" + "b" * 320, None)])
def test_only_an_email_address_is_an_identity(value, expected):
    assert roles.clean(value) == expected


def test_a_user_with_no_row_and_on_no_list_is_a_viewer_who_may_do_nothing_else():
    access_ = roles.resolve(lists(), "stranger@example.invalid")
    assert access_.role == "viewer" and access_.roles == {"viewer"} and access_.source == "lists"
    assert not any(access_.capabilities().values())
    assert roles.resolve(lists(), None).roles == frozenset() and roles.resolve(lists(), "").role is None


def test_the_legacy_lists_give_roles_when_there_is_no_row():
    assert roles.resolve(lists(), EDITOR).role == "editor"
    approver = roles.resolve(lists(), APPROVER)
    assert approver.role == "approver" and approver.roles == {"viewer", "editor", "approver"}
    assert approver.can("decide") and approver.can("edit") and not approver.can("manage_users")


def test_an_intake_administrator_on_the_lists_alone_does_not_become_an_approver():
    # Unseeded deployments behave as before: ATELIER_INTAKE_ADMINS gave the intake screens and nothing in Gate 1.
    admin = roles.resolve(lists(), ADMIN)
    assert admin.can("manage_intake") and admin.can("manage_users")
    assert not admin.can("decide") and not admin.can("edit")


def test_a_row_decides_and_the_lists_are_then_ignored():
    # Demotion: still on the approver list, but the row says editor.
    row = roles.resolve(lists(), APPROVER, {"role": "editor", "name": "Whitney", "slack_user_id": "U1"})
    assert row.source == "users" and row.role == "editor" and not row.can("decide")
    assert (row.name, row.slack_user_id) == ("Whitney", "U1")
    # Promotion: on no list, the row says admin, so everything below follows.
    admin = roles.resolve(lists(), "new@example.invalid", {"role": "admin"})
    assert all(admin.can(c) for c in ("edit", "decide", "review", "manage_users", "manage_intake", "edit_packs",
                                      "approve_packs", "schedule"))
    for role, decide, edit in (("viewer", False, False), ("editor", False, True), ("approver", True, True), ("admin", True, True)):
        held = roles.resolve(StorageSettings(), "x@example.invalid", {"role": role})
        assert (held.can("decide"), held.can("edit")) == (decide, edit), role


def test_matching_ignores_case_and_spaces_on_both_sides():
    settings = StorageSettings(brief_approvers=(" Whitney@Example.INVALID ",))
    assert roles.resolve(settings, "WHITNEY@example.invalid").can("decide")
    assert roles.access_for(settings, "  whitney@EXAMPLE.invalid ").can("decide")


def test_identity_approvers_are_a_separate_narrower_list_in_both_modes():
    whitney = "identity@example.invalid"
    settings = StorageSettings(brief_approvers=(APPROVER, whitney), identity_approvers=(whitney,))
    assert roles.resolve(settings, whitney).can_review(identity_kind=True)
    assert not roles.resolve(settings, APPROVER).can_review(identity_kind=True), "an approver is not an identity approver"
    assert roles.resolve(settings, APPROVER).can_review(identity_kind=False)
    # A row does not change that: the list is the only thing that names identity approvers.
    assert not roles.resolve(settings, APPROVER, {"role": "admin"}).can_review(identity_kind=True)
    assert roles.resolve(settings, whitney, {"role": "viewer"}).can("review"), "any reviewer passes the entry gate"
    assert not roles.resolve(settings, whitney, {"role": "viewer"}).can("decide")
    # With the list empty, identity kinds need only an approver.
    assert roles.resolve(StorageSettings(brief_approvers=(APPROVER,)), APPROVER).can_review(identity_kind=True)


def test_packs_and_the_calendar_resolve_here_and_keep_their_behaviour():
    settings = StorageSettings(pack_editors=("packs@example.invalid",), pack_approvers=("packer@example.invalid",),
                               calendar_schedulers=("when@example.invalid",))
    assert roles.resolve(settings, "packs@example.invalid").can("edit_packs")
    assert not roles.resolve(settings, "packs@example.invalid").can("approve_packs")
    packer = roles.resolve(settings, "packer@example.invalid")
    assert packer.can("edit_packs") and packer.can("approve_packs")
    when = roles.resolve(settings, "when@example.invalid")
    assert when.can("schedule") and not when.can("edit_packs") and not when.can("edit"), "a scheduler is not a card editor"
    # With a row, packs follow the role: editor generates and schedules, approver approves.
    assert roles.resolve(settings, "x@example.invalid", {"role": "editor"}).can("schedule")
    assert not roles.resolve(settings, "x@example.invalid", {"role": "editor"}).can("approve_packs")


def test_a_bare_string_resolves_from_the_lists_and_an_actor_carries_its_access():
    settings = StorageSettings(brief_approvers=("tester",))
    assert roles.access_for(settings, "tester").can("decide")
    assert not roles.access_for(settings, "").can("edit") and not roles.access_for(settings, None).can("edit")
    carried = roles.Actor(roles.resolve(settings, "other@example.invalid", {"role": "approver"}))
    assert carried == "other@example.invalid" and isinstance(carried, str)
    assert roles.access_for(settings, carried).can("decide"), "the carried access is used, not the lists"
    assert roles.access_for(settings, roles.Actor(roles.Access(), "raw")) is not None


def test_an_actor_survives_copying_and_pickling_with_its_access():
    import copy
    import pickle
    actor = roles.Actor(roles.resolve(StorageSettings(), "a@example.invalid", {"role": "approver"}))
    for clone in (copy.copy(actor), copy.deepcopy({"actor": actor})["actor"], pickle.loads(pickle.dumps(actor))):
        assert clone == "a@example.invalid" and clone.access == actor.access and clone.access.can("decide")


def test_the_answer_of_me_names_role_roles_source_and_what_the_person_may_do():
    answer = roles.resolve(lists(), APPROVER).describe()
    assert answer["email"] == APPROVER and answer["role"] == "approver" and answer["roles"] == ["viewer", "editor", "approver"]
    assert answer["source"] == "lists" and answer["can"]["approve_briefs"] and answer["can"]["edit_cards"]
    assert answer["can"]["manage_users"] is False
    for name in ("edit_cards", "decide", "approve_briefs", "review_knowledge", "identity_review", "manage_users"):
        assert name in answer["can"]


def test_the_seed_maps_the_lists_to_rows_and_approvers_win_over_editors():
    settings = StorageSettings(
        brief_approvers=("a@example.invalid", "both@example.invalid"), brief_editors=("both@example.invalid", "e@example.invalid"),
        pack_editors=("p@example.invalid",), pack_approvers=("pa@example.invalid",), calendar_schedulers=("s@example.invalid",),
        intake_admins=("a@example.invalid", "i@example.invalid"), identity_approvers=("w@example.invalid", "a@example.invalid"),
        )
    wanted, skipped = roles.wanted(settings)
    assert wanted == {"a@example.invalid": "admin", "i@example.invalid": "admin", "both@example.invalid": "approver",
                      "pa@example.invalid": "approver", "e@example.invalid": "editor", "p@example.invalid": "editor",
                      "s@example.invalid": "editor", "w@example.invalid": "viewer"}
    assert skipped == []
    wanted, skipped = roles.wanted(StorageSettings(brief_approvers=("tester", "Real@Example.invalid")))
    assert wanted == {"real@example.invalid": "approver"} and skipped == ["tester"]


# --- per-role outcomes behind the Node server's relay (6.X2) ----------------------------------------------------

@pytest.mark.parametrize("who,role,may_read,may_change", [
    (VIEWER, "viewer", False, False), (EDITOR, "editor", True, False), (APPROVER, "approver", True, True)])
def test_the_relay_forwards_every_team_write_and_the_backend_decides_by_role(who, role, may_read, may_change):
    """The Node server forwards a team session's write with its verified email and decides nothing more (its role matrix:
    frontend/server/roles.test.mjs); the role is decided here. Settings, the newest relayed write (6.F7): an editor reads,
    only an approver changes, a viewer does neither."""
    from backend_pipeline import settings_api
    repo = SimpleNamespace(settings=lists())
    assert roles.resolve(lists(), who).role == role
    for capability, allowed in (("read", may_read), ("write", may_change)):
        if allowed:
            settings_api.require_settings_admin(repo, who, capability)
        else:
            with pytest.raises(PermissionError):
                settings_api.require_settings_admin(repo, who, capability)


# --- the dependencies ------------------------------------------------------------------------------------------

def fake_repo(settings, row=None, fail=None):
    @contextmanager
    def connection():
        if fail:
            raise fail

        class Conn:
            def execute(self, statement, params=()):
                assert "FROM users" in statement
                self.row = row
                return self

            def fetchone(self):
                return self.row

            def rollback(self):
                pass
        yield Conn()
    return SimpleNamespace(settings=settings, connection=connection)


def app_for(repo, secret="s3cret"):
    deps = access.dependencies(lambda: secret, repo)
    app = FastAPI()

    @app.get("/trusted")
    def trusted_only(who=Depends(deps.trusted)):
        return {"actor": who}

    @app.post("/strict")
    def strict(user=Depends(deps.current_user)):
        return user.access.describe()

    @app.get("/lenient")
    def lenient(user=Depends(deps.optional_user)):
        return {"value": str(user), "role": user.access.role, "source": user.access.source}
    return TestClient(app)


def headers(actor=None, email=None, secret="s3cret"):
    result = {"authorization": "Bearer " + secret} if secret else {}
    if actor is not None:
        result["x-atelier-actor"] = actor
    if email is not None:
        result["x-atelier-email"] = email
    return result


def test_every_route_needs_the_shared_secret_and_an_actor():
    client = app_for(fake_repo(lists()))
    for path, method in (("/trusted", "get"), ("/strict", "post"), ("/lenient", "get")):
        call = getattr(client, method)
        assert call(path).status_code == 401
        assert call(path, headers=headers("x@example.invalid", secret="wrong")).status_code == 401
        assert call(path, headers=headers(secret=None, actor="x@example.invalid")).status_code == 401
        assert call(path, headers=headers(actor="")).status_code == 401, "no actor"
        assert call(path, headers=headers(actor="x" * 321)).status_code == 401
    assert app_for(fake_repo(lists()), secret="").get("/trusted", headers=headers("a@b.c", secret="")).status_code == 401, \
        "no configured secret refuses everything"
    assert client.get("/trusted", headers=headers("not-an-email")).json() == {"actor": "not-an-email"}, \
        "reads that need no roles keep taking any trusted actor"


def test_the_verified_email_is_the_only_identity_for_roles():
    client = app_for(fake_repo(lists()))
    # Mutating routes: an actor that is not an email is refused, and so is an email header that is not one.
    assert client.post("/strict", headers=headers("user-id-7")).status_code == 401
    assert client.post("/strict", headers=headers(APPROVER, email="user-id-7")).status_code == 401
    assert client.post("/strict", headers=headers("team-id", email="")).status_code == 401
    # The Node server sends the verified email in both headers (R37); either one alone is enough.
    assert client.post("/strict", headers=headers(APPROVER)).json()["email"] == APPROVER
    assert client.post("/strict", headers=headers(APPROVER, email=APPROVER)).json()["role"] == "approver"
    # When they differ the email header decides: a user id in the actor header decides nothing.
    answer = client.post("/strict", headers=headers("user-id-7", email=EDITOR.upper())).json()
    assert answer["email"] == EDITOR and answer["role"] == "editor"
    assert client.post("/strict", headers=headers(APPROVER, email="stranger@example.invalid")).json()["role"] == "viewer"
    # Reads that only mark capabilities: no email, no roles, and no error.
    assert client.get("/lenient", headers=headers("tester")).json() == {"value": "tester", "role": None, "source": "none"}
    assert client.get("/lenient", headers=headers("x", email=EDITOR)).json()["role"] == "editor"


def test_the_row_found_by_the_dependency_wins_over_the_lists():
    client = app_for(fake_repo(lists(), row={"email": APPROVER, "name": "W", "role": "viewer", "slack_user_id": None}))
    answer = client.post("/strict", headers=headers(APPROVER)).json()
    assert answer["role"] == "viewer" and answer["source"] == "users" and answer["can"]["decide"] is False


def test_an_unreachable_user_store_is_a_503_not_a_guess():
    client = app_for(fake_repo(lists(), fail=OperationalError("down")))
    assert client.post("/strict", headers=headers(APPROVER)).status_code == 503
    assert client.get("/lenient", headers=headers(APPROVER)).status_code == 503
    assert client.get("/trusted", headers=headers(APPROVER)).status_code == 200, "no role lookup, no database"


# --- coverage of the production app ----------------------------------------------------------------------------

# Mutating routes that are not behind a person's roles, each with the reason and the other check it carries.
EXEMPT = {
    ("POST", "/intake/v1/slack/batches"): "Slack intake service delivery: the dedicated service token, no human actor",
    ("PUT", "/intake/v1/assets/{asset_id}/content"): "Slack intake attachment upload: the dedicated service token, no human actor",
}
# Reads outside the role model: the process's own health check.
OPEN_READS = {("GET", "/health"): "the container health check (0.B11 trims it to non-sensitive fields)"}


def walk(dependant):
    for dep in dependant.dependencies:
        yield dep.call
        yield from walk(dep)


def production_routes():
    from backend_pipeline.api import app
    return [r for r in app.routes if isinstance(r, APIRoute)]


def marks(route):
    calls = list(walk(route.dependant))
    return {"secret": any(getattr(c, "checks_shared_secret", False) for c in calls),
            "roles": any(getattr(c, "resolves_roles", False) for c in calls),
            "service": any(getattr(c, "checks_service_token", False) for c in calls)}


def test_every_mutating_route_of_the_production_app_checks_the_secret_and_the_roles_by_email():
    unchecked, seen = [], set()
    for route in production_routes():
        for method in route.methods - {"GET", "HEAD", "OPTIONS"}:
            seen.add((method, route.path))
            found = marks(route)
            if (method, route.path) in EXEMPT:
                assert found["service"], f"{method} {route.path} is exempt only for its service token"
                continue
            if not (found["secret"] and found["roles"]):
                unchecked.append(f"{method} {route.path} {found}")
    assert unchecked == [], "mutating routes without the shared secret and the role dependency: " + "; ".join(unchecked)
    assert set(EXEMPT) <= seen, "an exemption names a route that no longer exists: " + str(set(EXEMPT) - seen)
    assert len(seen) > 40, "the walk found the storage, intake and knowledge routes"
    assert {"/storage/context/versions/{version}/approve", "/storage/intake/refresh"} <= {p for _, p in seen}


def test_the_legacy_experiment_routes_are_retired():
    """6.B8: the file-backed experiment routes are gone; every route is /storage, the intake service's /intake/v1 or /health."""
    paths = {route.path for route in production_routes()}
    assert not {p for p in paths if p.startswith("/runs")}
    assert {p for p in paths if not p.startswith(("/storage/", "/intake/v1/"))} == {"/health"}


def test_every_read_of_the_production_app_is_behind_the_secret_or_its_service_token():
    open_reads = []
    for route in production_routes():
        for method in route.methods & {"GET"}:
            found = marks(route)
            if (method, route.path) in OPEN_READS:
                continue
            if not (found["secret"] or found["service"]):
                open_reads.append(f"{method} {route.path}")
    assert open_reads == []


def test_the_coverage_walk_would_catch_a_route_that_skips_the_dependency():
    app = FastAPI()
    deps = access.dependencies(lambda: "s", fake_repo(lists()))

    @app.post("/storage/unchecked")
    def unchecked():
        return {}

    @app.post("/storage/checked")
    def checked(user=Depends(deps.current_user)):
        return {}
    by_path = {r.path: marks(r) for r in app.routes if isinstance(r, APIRoute)}
    assert by_path["/storage/unchecked"] == {"secret": False, "roles": False, "service": False}
    assert by_path["/storage/checked"]["secret"] and by_path["/storage/checked"]["roles"]
