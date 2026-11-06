"""L.B3 "done when" through the API on a migrated database: accept, edit and reject each write a decision and the
right item state; an edit stores its diff; a non-approver gets 403; a stale hash gets 409."""
from __future__ import annotations

from datetime import date, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend_pipeline.database import connect
from backend_pipeline.knowledge import items
from backend_pipeline.storage_api import router
from backend_pipeline.tests.platform_db import APPROVER, EDITOR, platform_setup, platform_url  # noqa: F401 (fixture)

WHITNEY = "whitney.identity@example.invalid"


@pytest.fixture
def api(platform_setup):  # noqa: F811
    repo, _, _ = platform_setup
    settings = repo.settings.model_copy(update={"brief_approvers": (APPROVER, WHITNEY), "identity_approvers": (WHITNEY,),
                                                "context_enabled": True})
    app = FastAPI()
    app.include_router(router(settings))
    client = TestClient(app)

    def call(method, path, body=None, email=APPROVER):
        headers = {"Authorization": "Bearer test-secret", "X-Atelier-Actor": email, "X-Atelier-Email": email}
        return client.request(method, "/storage" + path, json=body, headers=headers)

    def candidate(kind, key, body, ref, **extra):
        with connect(settings.database_url) as conn:
            return items.add_item(conn, kind=kind, key=key, body=body, status="candidate", source_kind="export_seed",
                                  source_ref=ref, author="model", created_by="seed", model_written=True, **extra)[0]
    return settings, call, candidate


def decisions(url, item_id):
    with connect(url) as conn:
        return conn.execute("SELECT * FROM decisions WHERE item_id=%s ORDER BY created_at", (item_id,)).fetchall()


def test_accept_edit_and_reject_each_write_a_decision_and_the_right_state(api):
    settings, call, candidate = api
    assert call("GET", "/flags").json()["context"] is True
    offer = candidate("offer", "offer:elevate", {"name": "ELEVATE", "description": "Done-for-you ads management"}, "r1")
    price = candidate("price", "price:elevate", {"offer": "ELEVATE", "amount": "$1,497/month"}, "r2", visibility="internal")
    cta = candidate("cta", "cta:ads", {"wording": "Comment ADS", "cta_type": "dm_keyword"}, "r3")
    queue = call("GET", "/context/queue").json()
    shown = {i["item_id"]: i for i in queue["items"]}
    assert queue["total"] == 3 and shown[offer]["would_change"]["document"] == "offer_sheet"
    assert shown[offer]["would_change"]["summary"].startswith("Adds an entry")

    accepted = call("POST", f"/context/items/{offer}/decision",
                    {"expected_hash": shown[offer]["hash"], "action": "accept", "reason": "Matches the offer sheet",
                     "author": "Gisselle Jiménez", "changes": {"valid_from": "2026-10-14"}})
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["status"] == "confirmed"
    edited = call("POST", f"/context/items/{price}/decision",
                  {"expected_hash": shown[price]["hash"], "action": "edit", "reason": "The current retainer",
                   "changes": {"body": {"offer": "ELEVATE", "amount": "$1,497/month", "terms": "6-month minimum"}}})
    assert edited.status_code == 200, edited.text
    diff = edited.json()["diff"]
    assert diff["body"]["after"]["terms"] == "6-month minimum" and "terms" not in diff["body"]["before"]
    assert diff["text"]["after"] == "ELEVATE: $1,497/month (6-month minimum)"
    rejected = call("POST", f"/context/items/{cta}/decision",
                    {"expected_hash": shown[cta]["hash"], "action": "reject", "reason": "Retired keyword"})
    assert rejected.json()["status"] == "rejected"

    with connect(settings.database_url) as conn:
        states = {r["item_id"]: r for r in conn.execute("SELECT * FROM brand_kit_items")}
    assert states[offer]["status"] == "confirmed" and states[offer]["reviewed_by"] == APPROVER
    assert states[offer]["valid_from"] == date(2026, 10, 14) and states[offer]["review_note"] == "Matches the offer sheet"
    assert states[price]["status"] == "confirmed" and states[price]["body"]["terms"] == "6-month minimum"
    assert states[cta]["status"] == "rejected"
    for item_id, action in [(offer, "context_accept"), (price, "context_edit"), (cta, "context_reject")]:
        rows = decisions(settings.database_url, item_id)
        assert len(rows) == 1 and rows[0]["action"] == action and rows[0]["actor"] == APPROVER
        assert rows[0]["item_kind"] == "brand_kit_item"
    assert decisions(settings.database_url, offer)[0]["author"] == "Gisselle Jiménez"
    assert decisions(settings.database_url, price)[0]["details"]["diff"]["body"]["after"]["terms"] == "6-month minimum"
    assert call("GET", f"/context/items/{price}/history").json()["decisions"][0]["action"] == "context_edit"


def test_a_non_approver_gets_403_and_a_stale_hash_gets_409(api):
    _, call, candidate = api
    offer = candidate("offer", "offer:vault", {"name": "The VAULT", "description": "Membership"}, "r1")
    shown = call("GET", "/context/queue").json()["items"][0]
    body = {"expected_hash": shown["hash"], "action": "accept", "reason": "ok"}
    assert call("POST", f"/context/items/{offer}/decision", body, email=EDITOR).status_code == 403
    assert call("POST", f"/context/items/{offer}/decision", {**body, "expected_hash": "0" * 64}).status_code == 409
    assert call("POST", f"/context/items/{offer}/decision", body).status_code == 200
    assert call("POST", f"/context/items/{offer}/decision", body).status_code == 409, "already decided"
    assert call("POST", f"/context/items/{offer}/decision", {**body, "reason": ""}).status_code == 422


def test_identity_kinds_need_the_identity_approver(api):
    _, call, candidate = api
    rule = candidate("rule", "rule:no-dashes", {"statement": "No em dashes", "level": "ban", "scope": "all", "category": "voice"}, "r1")
    shown = call("GET", "/context/queue", email=WHITNEY).json()["items"][0]
    assert call("GET", "/context/queue").json()["items"][0]["can_decide"] is False
    body = {"expected_hash": shown["hash"], "action": "accept", "reason": "Whitney's rule"}
    assert call("POST", f"/context/items/{rule}/decision", body).status_code == 403
    assert call("POST", f"/context/items/{rule}/decision", body, email=WHITNEY).status_code == 200


def test_a_rule_is_confirmed_only_with_its_category(api):
    """E.B11: every confirmed rule names its category, so each compiled rule shows one; the reviewer sets it."""
    _, call, candidate = api
    rule = candidate("rule", "rule:no-category", {"statement": "Never promise a result", "level": "ban", "scope": "all"}, "r-cat")
    shown = next(i for i in call("GET", "/context/queue", email=WHITNEY).json()["items"] if i["item_id"] == rule)
    refused = call("POST", f"/context/items/{rule}/decision", {"expected_hash": shown["hash"], "action": "accept",
                                                                  "reason": "ok"}, email=WHITNEY)
    assert refused.status_code == 409 and "category" in refused.text
    edited = call("POST", f"/context/items/{rule}/decision", {
        "expected_hash": shown["hash"], "action": "edit", "reason": "ok, a factual rule",
        "changes": {"body": {"statement": "Never promise a result", "level": "ban", "scope": "all", "category": "factual"}}},
        email=WHITNEY)
    assert edited.status_code == 200 and edited.json()["status"] == "confirmed"


def test_batches_only_for_low_risk_kinds_and_published_entries(api):
    settings, call, candidate = api
    phrases = [candidate("audience_phrase", f"audience:p{i}", {"phrase": f"phrase {i}", "theme": "Burned by agencies"}, f"a{i}")
               for i in range(3)]
    offer = candidate("offer", "offer:x", {"name": "X", "description": "Y"}, "o1")
    queue = {i["item_id"]: i["hash"] for i in call("GET", "/context/queue?limit=200", email=WHITNEY).json()["items"]}
    mixed = call("POST", "/context/batch", {"action": "accept", "reason": "WIA's words",
                                            "entries": [{"item_id": i, "expected_hash": queue[i]} for i in [*phrases, offer]]}, email=WHITNEY)
    assert mixed.status_code == 409 and "low-risk" in mixed.text
    done = call("POST", "/context/batch", {"action": "accept", "reason": "WIA's words",
                                           "entries": [{"item_id": i, "expected_hash": queue[i]} for i in phrases]}, email=WHITNEY)
    assert done.status_code == 200 and done.json()["decided"] == 3
    assert all(len(decisions(settings.database_url, i)) == 1 for i in phrases), "each entry still writes its own decision"
    with connect(settings.database_url) as conn:
        conn.execute("""INSERT INTO published_content(content_id,channel,title,status,source_kind,source_ref,created_by)
            VALUES ('pc1','email','Hook','unconfirmed','export_seed','log#1','seed')""")
    assert call("POST", "/context/published/confirm", {"content_ids": ["pc1"], "reason": "Sent"}, email=EDITOR).status_code == 403
    assert call("POST", "/context/published/confirm", {"content_ids": ["pc1"], "reason": "Sent"}).json() == {"confirmed": 1}
    assert call("GET", "/context/published?status=confirmed").json()["items"][0]["content_id"] == "pc1"


def test_an_approver_entry_is_confirmed_on_entry_and_versions_a_price(api):
    _, call, _ = api
    start = (date.today() + timedelta(days=10)).isoformat()
    first = call("POST", "/context/items", {"kind": "price", "name": "ELEVATE retainer", "visibility": "internal",
                                            "body": {"offer": "ELEVATE", "amount": "$1,497/month"}, "reason": "Current"})
    assert first.status_code == 201, first.text
    assert first.json()["status"] == "confirmed"
    second = call("POST", "/context/items", {"kind": "price", "key": first.json()["key"], "visibility": "internal",
                                             "body": {"offer": "ELEVATE", "amount": "$1,697/month"}, "valid_from": start,
                                             "reason": "New price from next month"})
    assert second.json()["supersedes_id"] == first.json()["item_id"]
    today = call("GET", "/context/items?kind=price").json()
    later = call("GET", f"/context/items?kind=price&on={start}").json()
    assert [i["body"]["amount"] for i in today["items"]] == ["$1,497/month"]
    assert [i["body"]["amount"] for i in today["scheduled"]] == ["$1,697/month"]
    assert [i["body"]["amount"] for i in later["items"]] == ["$1,697/month"]
    assert call("POST", "/context/items", {"kind": "price", "name": "x", "body": {"offer": "x", "amount": "free"},
                                           "reason": "bad"}).status_code == 409, "a malformed body is refused"


def test_an_approver_entry_can_end_on_a_date_and_is_gone_after_it(api):
    """L.F2, L.B8: "In use until" on the operating-facts form is the item's valid_to; the offer is absent after it."""
    _, call, _ = api
    ends = date.today() + timedelta(days=5)
    entered = call("POST", "/context/items", {"kind": "campaign", "name": "Autumn enrolment", "valid_to": ends.isoformat(),
                                              "body": {"name": "Autumn enrolment", "description": "Accelerator enrolment open"},
                                              "reason": "Enrolment closes on the date"})
    assert entered.status_code == 201, entered.text
    assert entered.json()["valid_to"] == ends.isoformat()

    def names(on):
        return [i["body"]["name"] for i in call("GET", f"/context/items?kind=campaign&on={on.isoformat()}").json()["items"]]
    assert names(ends) == ["Autumn enrolment"] and names(ends + timedelta(days=1)) == []
    backwards = call("POST", "/context/items", {"kind": "campaign", "name": "Wrong way round", "valid_from": ends.isoformat(),
                                                "valid_to": date.today().isoformat(), "body": {"name": "Wrong way round"},
                                                "reason": "x"})
    assert backwards.status_code == 409 and "end" in backwards.json()["detail"].lower()


def test_the_seeded_queue_carries_a_suggestion_for_every_candidate_and_applies_none(api):
    from backend_pipeline.knowledge import seed
    settings, call, _ = api
    with connect(settings.database_url) as conn:
        seed.run(conn, actor="seed", approver=APPROVER)
    queue = call("GET", "/context/queue?limit=200&kind=rule", email=WHITNEY).json()
    assert queue["total"] > 50 and all(i["suggestion"]["action"] in ("accept", "reject", "review") for i in queue["items"])
    covered = [i for i in queue["items"] if i["suggestion"].get("duplicate_of")]
    assert covered, "drafted rules that a confirmed rule already covers are suggested for rejection"
    with connect(settings.database_url) as conn:
        target = conn.execute("SELECT status,source_kind FROM brand_kit_items WHERE item_id=%s", (covered[0]["suggestion"]["duplicate_of"],)).fetchone()
        assert target["status"] == "confirmed" and target["source_kind"] == "knowledge_base"
        assert conn.execute("SELECT count(*) n FROM decisions").fetchone()["n"] == 0, "a suggestion decides nothing"
    prices = call("GET", "/context/queue?limit=200&kind=price").json()["items"]
    assert any(p["suggestion"]["action"] == "reject" and "later quote" in p["suggestion"]["reason"] for p in prices)

def test_the_context_routes_answer_only_with_the_flag_on_and_unknown_ids_are_404(platform_setup):  # noqa: F811
    """With ATELIER_CONTEXT_ENABLED off nothing can read, approve or activate a version through the API (R31); an
    unknown item or version is a 404, and a non-approver's batch is a 403 before any entry is looked at (L.B3)."""
    repo, _, _ = platform_setup
    for enabled in (False, True):
        settings = repo.settings.model_copy(update={"brief_approvers": (APPROVER,), "context_enabled": enabled})
        app = FastAPI()
        app.include_router(router(settings))
        client = TestClient(app)

        def call(method, path, body=None, email=APPROVER):
            headers = {"Authorization": "Bearer test-secret", "X-Atelier-Actor": email, "X-Atelier-Email": email}
            return client.request(method, "/storage" + path, json=body, headers=headers)
        if not enabled:
            for method, path in (("GET", "/context/queue"), ("POST", "/context/versions/v1/approve"), ("GET", "/context/kinds")):
                assert call(method, path, {"note": "x"} if method == "POST" else None).status_code == 404, path
            assert call("GET", "/flags").json()["context"] is False
            continue
        assert call("POST", "/context/items/item_missing/decision",
                    {"expected_hash": "h" * 64, "action": "reject", "reason": "x"}).status_code == 404
        assert call("GET", "/context/versions/wia-kb-missing/diff").status_code == 404
        with connect(settings.database_url) as conn:
            rule = items.add_item(conn, kind="rule", key="rule:batch", body={"statement": "Never promise a result", "level": "ban", "scope": "all"},
                                  status="candidate", source_kind="export_seed", source_ref="batch-r1", author="model",
                                  created_by="seed", model_written=True)[0]
            digest = items.get_item(conn, rule)["hash"]
        batch = call("POST", "/context/batch", {"action": "accept", "reason": "x", "entries": [{"item_id": rule, "expected_hash": digest}]},
                     email=EDITOR)
        assert batch.status_code == 403, batch.text


def test_a_non_approver_gets_403_on_every_context_write_route(api):
    """L.B3: every route that changes the store or a version needs an approver, checked before anything is read."""
    _, call, _ = api
    writes = [
        ("/context/items", {"kind": "offer", "name": "x", "body": {"name": "x", "description": "y"}, "reason": "r"}),
        ("/context/published", {"published_on": "2026-10-01", "channel": "email", "title": "t"}),
        ("/context/published/confirm", {"content_ids": ["pc_x"], "reason": "r"}),
        ("/context/published/import", {"csv": "date,channel,piece,metric,value"}),
        ("/context/published/pc_x/performance", {"on": "2026-10-01", "metric": "m", "value": "v"}),
        ("/context/published/pc_x/link", {"brief_id": "brief_x"}),
        ("/context/versions", {}),
        ("/context/versions/wia-kb-x/approve", {"note": "n"}),
        ("/context/versions/wia-kb-x/benchmark", {"passed": True, "result_ref": "r"}),
        ("/context/mining", {}),
        ("/context/batch", {"action": "reject", "reason": "r", "entries": [{"item_id": "item_x", "expected_hash": "h" * 64}]}),
        ("/context/items/item_x/decision", {"expected_hash": "h" * 64, "action": "reject", "reason": "r"}),
    ]
    for path, body in writes:
        response = call("POST", path, body, email=EDITOR)
        assert response.status_code == 403, (path, response.status_code, response.text)



def test_an_identity_approver_outside_the_approver_list_still_decides_identity(platform_setup):  # noqa: F811
    """The early role check admits either kind of reviewer; the entry's own kind decides who may act on it."""
    repo, _, _ = platform_setup
    settings = repo.settings.model_copy(update={"brief_approvers": (APPROVER,), "identity_approvers": (WHITNEY,), "context_enabled": True})
    with connect(settings.database_url) as conn:
        rule = items.add_item(conn, kind="rule", key="rule:identity-only", body={"statement": "No stock AI phrases", "level": "flag",
                              "scope": "all", "category": "voice"}, status="candidate", source_kind="export_seed", source_ref="identity-only",
                              author="model", created_by="seed", model_written=True)[0]
        digest = items.get_item(conn, rule)["hash"]
        from backend_pipeline.knowledge import review
        assert review.decide(conn, settings, rule, digest, "accept", WHITNEY, reason="Whitney's own rule")["status"] == "confirmed"
