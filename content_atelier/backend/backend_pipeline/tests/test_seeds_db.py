"""E.B19 "done when" on the migrated database: a seed saved through the API appears in the next cycle, paired with
scenes or flagged "no call evidence". Synthetic fixtures and fake providers only."""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend_pipeline.angle_profiles import STRATEGIST_V5_PROFILE
from backend_pipeline.sql_pipeline import SQLWorker
from backend_pipeline.storage_api import router
from backend_pipeline.tests.platform_db import APPROVER, EDITOR, platform_setup, platform_url  # noqa: F401 (fixture)
from backend_pipeline.tests.test_cards_sql import W1, W2, CardSQLProvider
from backend_pipeline.tests.test_sql_storage import drain
from backend_pipeline.tests.test_strategist_profile import card, write_kb


class SeedProvider(CardSQLProvider):
    """Version 5 cards; the first seed is paired with scene S1, the second has no call evidence."""

    def json_call(self, *, stage, system, user, schema, fingerprint):
        if stage != "angle_generation":
            return super().json_call(stage=stage, system=system, user=user, schema=schema, fingerprint=fingerprint)
        self.calls.append(stage)
        self.card_users.append(user)
        pairings = [{"seed_ref": "F1", "moment_ids": ["S1"], "note": "The call shows the first reply."}] if "Seed F1" in user else []
        if "Seed F2" in user:
            pairings.append({"seed_ref": "F2", "moment_ids": [], "note": "No call this week touches it."})
        return {"week_summary": "One call; publish rank 2 first.",
                "angles": [card("S1", 1, series="Watch Us Build an Ad Strategy"), card("S1", 2, series=None)],
                "internal_insights": [{"moment_ids": ["S2"], "insight": "A caution.", "use": "Sales."}],
                "considered_not_selected": [], "publishing_order": [2, 1],
                "pillar_notes": [{"pillar": "CONVERT", "note": "No scene shows an offer decision."}],
                "seed_pairings": pairings}, {"fake": True}


@pytest.fixture
def seeded(platform_setup):  # noqa: F811
    repo, models, tmp = platform_setup
    v5 = models.model_copy(update={"angle_prompt_profile": STRATEGIST_V5_PROFILE, "knowledge_base_root": write_kb(tmp / "kb")})
    provider = SeedProvider()
    app = FastAPI()
    app.include_router(router(repo.settings))
    client = TestClient(app)

    def call(method, path, body=None, email=APPROVER):
        headers = {"Authorization": "Bearer test-secret", "X-Atelier-Actor": email, "X-Atelier-Email": email}
        return client.request(method, "/storage" + path, json=body, headers=headers)
    return repo, v5, provider, SQLWorker(repo.settings, v5, provider=provider), call


def test_a_saved_seed_appears_in_the_next_cycle_paired_or_flagged(seeded):
    repo, v5, provider, worker, call = seeded
    assert call("POST", "/seeds", {"kind": "thought", "text": "x"}, email="viewer@example.invalid").status_code == 403
    assert call("POST", "/seeds", {"kind": "asset", "text": "Our tour Reel"}).status_code == 409, "an asset needs its link"
    first = call("POST", "/seeds", {"kind": "thought", "text": "Couples book faster when the first reply names a date.",
                                    "target_offer": "LeadLock", "author": "Whitney Hodges"}, email=EDITOR)
    assert first.status_code == 201, first.text
    evergreen = call("POST", "/seeds", {"kind": "draft", "text": "We build the campaign with you, then hand you the keys.",
                                        "author": "Whitney Hodges", "always_true": True})
    dropped = call("POST", "/seeds", {"kind": "thought", "text": "An idea Whitney withdrew."})
    assert call("POST", f"/seeds/{dropped.json()['seed_id']}/withdraw", {}).json()["status"] == "withdrawn"
    assert [s["seed_id"] for s in call("GET", "/seeds?status=open").json()] == [evergreen.json()["seed_id"], first.json()["seed_id"]]

    run = repo.submit(W1, "synthetic", models=v5)
    drain(worker)
    user = provider.card_users[-1]
    assert "Seed F1 (thought, from Whitney Hodges): Target offer: LeadLock. Couples book faster" in user
    assert "Seed F2 (draft, from Whitney Hodges): We build the campaign" in user and "withdrew" not in user
    selection = repo.review(W1, APPROVER)["selection"]
    pairings = {p["seed_ref"]: p for p in selection["seed_pairings"]}
    assert pairings["F1"]["seed_id"] == first.json()["seed_id"] and pairings["F1"]["moment_ids"][0].startswith("moment_")
    assert pairings["F2"]["seed_id"] == evergreen.json()["seed_id"] and pairings["F2"]["moment_ids"] == [], "no call evidence"
    assert selection["publishing_order"] == [2, 1] and selection["pillar_notes"][0]["pillar"] == "CONVERT"

    seeds = {s["seed_id"]: s for s in call("GET", "/seeds").json()}
    assert seeds[first.json()["seed_id"]]["status"] == "used" and seeds[first.json()["seed_id"]]["used_in_run_id"] == run["run_id"]
    assert seeds[evergreen.json()["seed_id"]]["status"] == "open", "an always-true seed stays for every cycle"

    # The next week's cycle sees only the seed that is still open.
    repo.submit(W2, "synthetic", models=v5)
    drain(worker)
    assert "Seed F1 (draft, from Whitney Hodges)" in provider.card_users[-1] and "Seed F2" not in provider.card_users[-1]


def test_seeds_keep_the_order_they_were_added_when_the_clock_steps_back(seeded):
    """E.B19: the list (newest first) and the cycle's F1, F2 ... (oldest first) follow the order seeds were added, even
    when the database clock steps back between two of them (a VM clock resync) or two land in the same instant. The
    earlier seed is moved an hour ahead here, as if the clock had been an hour fast when it was added."""
    from backend_pipeline.cycle import seeds as founder_seeds
    repo, _, _, _, call = seeded
    first = call("POST", "/seeds", {"kind": "thought", "text": "The first seed."}).json()["seed_id"]
    with repo.connection() as conn:
        conn.execute("UPDATE seeds SET created_at=created_at+interval '1 hour' WHERE seed_id=%s", (first,))
    second = call("POST", "/seeds", {"kind": "thought", "text": "The second seed."}).json()["seed_id"]
    third = call("POST", "/seeds", {"kind": "thought", "text": "The third seed."}).json()["seed_id"]
    assert [s["seed_id"] for s in call("GET", "/seeds?status=open").json()] == [third, second, first]
    with repo.connection() as conn:
        assert [s["seed_id"] for s in founder_seeds.freeze(conn, W1)] == [first, second, third]


def test_a_cycle_with_no_seeds_says_so(seeded):
    repo, v5, provider, worker, _ = seeded
    repo.submit(W1, "synthetic", models=v5)
    drain(worker)
    assert "No founder seeds this cycle." in provider.card_users[-1]
    assert repo.review(W1, APPROVER)["selection"]["seed_pairings"] == []


class SilentProvider(SeedProvider):
    """The strategist answers no seed at all (an omission the contract cannot prevent)."""

    def json_call(self, *, stage, system, user, schema, fingerprint):
        output, meta = super().json_call(stage=stage, system=system, user=user, schema=schema, fingerprint=fingerprint)
        if stage == "angle_generation":
            output = {**output, "seed_pairings": []}
        return output, meta


def test_a_seed_the_strategist_did_not_answer_stays_open_and_is_flagged(seeded):
    """E.B19: a seed appears paired or flagged "no call evidence"; one left unanswered is never silently consumed."""
    repo, v5, _, _, call = seeded
    seed = call("POST", "/seeds", {"kind": "thought", "text": "Couples book faster when the first reply names a date.",
                                   "author": "Whitney Hodges"})
    provider = SilentProvider()
    worker = SQLWorker(repo.settings, v5, provider=provider)
    repo.submit(W1, "synthetic", models=v5)
    drain(worker)
    pairing = repo.review(W1, APPROVER)["selection"]["seed_pairings"][0]
    assert pairing["seed_id"] == seed.json()["seed_id"] and pairing["moment_ids"] == [] and pairing["unanswered"] is True
    assert {s["seed_id"]: s for s in call("GET", "/seeds").json()}[seed.json()["seed_id"]]["status"] == "open"

