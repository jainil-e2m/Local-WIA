"""E.B20 "done when" on the migrated database: each disposition writes one decision and one label with its author,
a revived idea appears as a proposed card, and a stale hash returns 409. Synthetic fixtures, fake providers only."""
from __future__ import annotations

from datetime import date, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend_pipeline import gate_one
from backend_pipeline.angle_profiles import STRATEGIST_V4_PROFILE
from backend_pipeline.sql_pipeline import SQLWorker
from backend_pipeline.storage_api import router
from backend_pipeline.tests.platform_db import APPROVER, EDITOR, platform_setup, platform_url  # noqa: F401 (fixture)
from backend_pipeline.tests.test_cards_sql import DECIDE, W1, CardSQLProvider, ranked
from backend_pipeline.tests.test_sql_storage import drain
from backend_pipeline.tests.test_strategist_profile import write_kb

WHITNEY = "Whitney Hodges"


@pytest.fixture
def gate(platform_setup):  # noqa: F811
    repo, models, tmp = platform_setup
    repo.settings.brief_enabled = False
    card_models = models.model_copy(update={"angle_prompt_profile": STRATEGIST_V4_PROFILE,
                                            "knowledge_base_root": write_kb(tmp / "kb")})
    worker = SQLWorker(repo.settings, card_models, provider=CardSQLProvider())
    repo.submit(W1, "synthetic", models=card_models)
    drain(worker)
    app = FastAPI()
    app.include_router(router(repo.settings))
    client = TestClient(app)

    def post(path, body, email=APPROVER):
        headers = {"Authorization": "Bearer test-secret", "X-Atelier-Actor": email, "X-Atelier-Email": email}
        return client.post("/storage" + path, json=body, headers=headers)
    return repo, worker, post


def rows(repo):
    with repo.connection() as conn:
        decisions = conn.execute("SELECT * FROM decisions ORDER BY created_at,decision_id").fetchall()
        # A label is written with its decision, whose dating is in order (repository.DATED_IN_ORDER).
        labels = conn.execute("""SELECT l.* FROM calibration_labels l LEFT JOIN decisions d USING(decision_id)
            ORDER BY d.created_at,l.created_at,l.label_id""").fetchall()
    return decisions, labels


def test_each_disposition_writes_one_decision_and_one_label_with_its_author(gate):
    repo, worker, post = gate
    # The approver relays Whitney, one of WIA's reviewers, so each label is WIA's own.
    repo.settings.wia_reviewers = (WHITNEY,)
    top, second, twin = ranked(repo.review(W1, APPROVER))
    path = lambda a: f"/angles/{a['angle_id']}/decision"  # noqa: E731
    later = (date.today() + timedelta(days=14)).isoformat()

    # Approver-only, hash-bound, and every non-develop disposition needs a reason code.
    assert post(path(twin), {"expected_hash": twin["content_hash"], "disposition": "skip", "reason_code": "duplicate"},
                email=EDITOR).status_code == 403
    assert post(path(twin), {"expected_hash": "stale", "disposition": "skip", "reason_code": "duplicate"}).status_code == 409
    assert post(path(twin), {"expected_hash": twin["content_hash"], "disposition": "skip"}).status_code == 409
    assert post(path(twin), {"expected_hash": twin["content_hash"], "disposition": "hold", "reason_code": "timing",
                             "hold_until": date.today().isoformat()}).status_code == 409, "a hold needs a later date"
    assert rows(repo) == ([], []), "refused calls record nothing"

    # Hold: the card stays pending with its date; the hash (and the matching bound to it) is unchanged.
    held = post(path(twin), {"expected_hash": twin["content_hash"], "disposition": "hold", "reason_code": "timing",
                             "note": "After the spring launch.", "hold_until": later, "author": WHITNEY})
    assert held.status_code == 200 and held.json()["hold_until"] == later
    review = repo.review(W1, APPROVER)
    twin_now = next(a for a in review["angles"] if a["angle_id"] == twin["angle_id"])
    assert twin_now["content_hash"] == twin["content_hash"] and twin_now["approval_status"] == "pending"
    assert twin_now["hold"]["until"] == later and twin_now["disposition"]["disposition"] == "hold"

    # Internal: closed for public content; the label says why.
    internal = post(path(twin), {"expected_hash": twin["content_hash"], "disposition": "internal",
                                 "reason_code": "internal_use", "author": WHITNEY})
    assert internal.status_code == 200 and internal.json()["approval_status"] == "rejected"

    # Reframe: a new card version; it must be reassessed before it can be developed.
    assert post(path(second), {"expected_hash": second["content_hash"], "disposition": "reframe", "reason_code": "voice",
                               "reframe": {"title": "Why we ask first"}}).status_code == 409, "central point kept is required"
    reframed = post(path(second), {"expected_hash": second["content_hash"], "disposition": "reframe", "reason_code": "voice",
                                   "reframe": {"title": "Why we ask about your calendar first"}, "central_point_kept": True,
                                   "author": WHITNEY})
    assert reframed.status_code == 200, reframed.text
    new_id = reframed.json()["angle_id"]
    assert reframed.json()["supersedes_id"] == second["angle_id"] and reframed.json()["check"]["status"] == "queued"
    pending = next(a for a in repo.review(W1, APPROVER)["angles"] if a["angle_id"] == new_id)
    assert pending["check"]["status"] == "queued" and not pending["can_approve"], "the screen shows the check, not a stale card"
    drain(worker)
    review = repo.review(W1, APPROVER)
    new = next(a for a in review["angles"] if a["angle_id"] == new_id)
    assert new["content_body"]["card"]["title"] == "Why we ask about your calendar first" and new["can_approve"]
    assert new["check"]["status"] == "checked"

    # Develop: today's approval path, with verify acknowledgements and the deferred CTA.
    for card in (top, new):
        developed = post(path(card), {"expected_hash": card["content_hash"], "disposition": "develop", "cta": DECIDE,
                                      "verify_acknowledged": card["content_body"]["card"]["verify_before_publishing"],
                                      "author": WHITNEY})
        assert developed.status_code == 200, developed.text
        assert developed.json()["approval_status"] == "approved" and developed.json()["decision_id"]
    assert post(path(top), {"expected_hash": top["content_hash"], "disposition": "skip",
                            "reason_code": "other"}).status_code == 409, "an approved card takes no further disposition"

    decisions, labels = rows(repo)
    assert [d["disposition"] for d in decisions] == ["hold", "internal", "reframe", "develop", "develop"]
    assert [lab["decision_id"] for lab in labels] == [d["decision_id"] for d in decisions], "one label per decision"
    assert all(d["author"] == WHITNEY and d["actor"] == APPROVER for d in decisions)
    assert all(lab["rater"] == APPROVER and lab["source"] == "gate" and not lab["proxy"] for lab in labels)
    reframe_row = decisions[2]
    assert reframe_row["resulting_item_id"] == new_id and reframe_row["central_point_kept"] is True
    assert reframe_row["reframe"] == {"title": "Why we ask about your calendar first"}
    assert decisions[0]["hold_until"] == date.fromisoformat(later) and labels[0]["details"]["note"] == "After the spring launch."


def test_an_idea_revives_when_its_scenes_belong_to_documents_not_a_week(gate):
    """Found live on production, 3 November: a cycle over a date window reads scenes with no week of their own, so every revive
    in such a week was refused with "The idea's scenes are not saved for this week"."""
    repo, _, post = gate
    selection = repo.review(W1, APPROVER)["selection"]
    idea = selection["considered_not_selected"][0]
    with repo.connection() as conn:
        conn.execute("UPDATE key_moments SET week_id=NULL WHERE moment_id=ANY(%s)", (idea["moment_ids"],))
    card = {"pillar": "WARM", "content_type": "education", "audience": "Established owners.", "why_it_matters": "Because."}
    revived = post(f"/weeks/{W1}/considered/0/revive", {"expected_hash": selection["selection_hash"], "card": card})
    assert revived.status_code == 201, revived.text


def test_a_revived_idea_in_a_v7_week_is_a_full_v7_card(gate):
    """A revived idea was built on the old card format, so it skipped the public-stance gate and a refresh could only touch its
    framing. In a strategist v7 week it now carries every v7 field, and is checked like its siblings."""
    from backend_pipeline.card_contracts import AngleCardV7
    from backend_pipeline.gates.decisions import _revived_v7
    fields = {"title": "T", "pillar": "WARM", "content_type": "education", "audience": "A", "why_it_matters": "W"}
    made = _revived_v7(fields, {"idea": "An idea."}, ["m1"], ["q1", None, "q2", "q3", "q4"], "Revived", None, 6)
    AngleCardV7.model_validate(made)
    assert made["point"] == "An idea." and made["evidence_points"] == ["q1", "q2", "q3"] and made["rank"] == 6
    assert made["public_stance"] == {"takes_stance": False, "stance": None} and made["verify_before_publishing"] == []


def test_a_revived_idea_appears_as_a_proposed_card_once(gate):
    repo, worker, post = gate
    selection = repo.review(W1, APPROVER)["selection"]
    idea = selection["considered_not_selected"][0]
    assert idea["index"] == 0 and idea["disposition"] is None
    base = f"/weeks/{W1}/considered/0"
    card = {"pillar": "WARM", "content_type": "behind_the_scenes", "audience": "Venue owners",
            "why_it_matters": "Shows how WIA reads a business before it advertises it."}

    assert post(base + "/revive", {"expected_hash": "stale", "card": card}).status_code == 409
    assert post(base + "/revive", {"expected_hash": selection["selection_hash"], "card": card},
                email=EDITOR).status_code == 403
    assert post(f"/weeks/{W1}/considered/9/revive", {"expected_hash": selection["selection_hash"],
                                                     "card": card}).status_code == 409
    skipped = post(base + "/decision", {"expected_hash": selection["selection_hash"], "disposition": "skip",
                                        "reason_code": "strategic_fit", "author": WHITNEY})
    assert skipped.status_code == 200

    revived = post(base + "/revive", {"expected_hash": selection["selection_hash"], "card": card,
                                      "note": "Worth a second look.", "author": WHITNEY})
    assert revived.status_code == 201, revived.text
    angle_id = revived.json()["angle_id"]
    assert post(base + "/revive", {"expected_hash": selection["selection_hash"], "card": card}).status_code == 409

    review = repo.review(W1, APPROVER)
    proposed = next(a for a in review["angles"] if a["angle_id"] == angle_id)
    body = proposed["content_body"]
    assert body["card"]["rank"] == 4 and body["card"]["title"] == "Generic tips."
    assert body["card"]["moment_ids"] == idea["moment_ids"] and body["revived_from"].endswith(":0")
    # A revived card is verified like any other (E.B10): its ledger is built from its own scenes, so its approval
    # checks the same blocking flags as a generated card's.
    assert body["ledger"]["ledger_hash"] and body["ledger"]["version"].startswith("ledger-")
    assert len(body["ledger"]["bindings"]) == len(body["card"]["evidence_points"])
    assert proposed["approval_status"] == "pending" and not proposed["can_approve"], "matching must assess it first"
    assert review["selection"]["considered_not_selected"][0]["disposition"]["disposition"] == "revive"
    roster = {r["name"]: r for r in review["roster"]}
    assert roster["Carmen Cruickshank"]["status"] == "current" and roster["Fallon Looney"]["status"] == "former", (
        "the card screen labels speakers from the knowledge base's roster (E.F2)")

    decisions, labels = rows(repo)
    assert [d["disposition"] for d in decisions] == ["skip", "revive"]
    assert decisions[1]["resulting_item_id"] == angle_id and len(labels) == 2
    assert all(d["item_kind"] == "considered_idea" and d["author"] == WHITNEY for d in decisions)

    # The revive queued the new card's check; once the worker runs it, the card can be developed.
    assert revived.json()["check"]["status"] == "queued"
    drain(worker)
    current = next(a for a in ranked(repo.review(W1, APPROVER)) if a["angle_id"] == angle_id)
    assert current["matching_result"]["status"] == "complete" and current["check"]["status"] == "checked" and current["can_approve"]
    developed = post(f"/angles/{angle_id}/decision", {"expected_hash": current["content_hash"], "disposition": "develop", "cta": DECIDE,
                                                      "verify_acknowledged": [], "note": "Checked against the call.",
                                                      "author": WHITNEY})
    assert developed.status_code == 200 and developed.json()["approval_status"] == "approved", developed.text


def test_a_reframed_card_is_checked_and_developed_without_a_manual_step(gate):
    """E.B16 and E.B20: a reframe's new version gets its own check (embedding, matching, duplicates) queued with it, so
    nothing outside the card screen is needed before it can be developed. Two reframes in a row share one check, and a
    version saved while another run is working on the week is checked when that run ends."""
    repo, worker, post = gate
    top, second, _ = ranked(repo.review(W1, APPROVER))
    path = lambda a: f"/angles/{a['angle_id']}/decision"  # noqa: E731
    body = {"disposition": "reframe", "reason_code": "voice", "central_point_kept": True}
    first = post(path(top), {**body, "expected_hash": top["content_hash"], "reframe": {"title": "Why we read the calendar first"}}).json()
    again = post(path(second), {**body, "expected_hash": second["content_hash"], "reframe": {"title": "What a quiet inbox tells us"}}).json()
    with repo.connection() as conn:
        runs = {r["run_id"]: r["status"] for r in conn.execute("SELECT run_id,status FROM pipeline_runs WHERE input_refs ? 'card_check'")}
    assert runs == {first["check"]["run_id"]: "cancelled", again["check"]["run_id"]: "queued"}, (
        "the unstarted check is replaced by one that includes both")
    drain(worker)
    review = {a["angle_id"]: a for a in repo.review(W1, APPROVER)["angles"]}
    for new in (first["angle_id"], again["angle_id"]):
        assert review[new]["can_approve"] and review[new]["check"]["status"] == "checked"
    card = review[first["angle_id"]]
    developed = post(path(card), {"expected_hash": card["content_hash"], "disposition": "develop", "cta": DECIDE,
                                  "verify_acknowledged": card["content_body"]["card"]["verify_before_publishing"]})
    assert developed.status_code == 200 and developed.json()["approval_status"] == "approved", developed.text

    # Deferred: while a run is working on the week, the new version waits for it, then its check is queued.
    with repo.connection() as conn:
        busy = conn.execute("SELECT run_id FROM pipeline_runs WHERE week_id=%s AND run_scope='weekly_angles' LIMIT 1", (W1,)).fetchone()
        conn.execute("UPDATE pipeline_runs SET status='running' WHERE run_id=%s", (busy["run_id"],))
    third = review[again["angle_id"]]
    later = post(path(third), {**body, "expected_hash": third["content_hash"], "reframe": {"title": "Why the inbox goes quiet"}}).json()
    assert later["check"]["status"] == "deferred"
    waiting = next(a for a in repo.review(W1, APPROVER)["angles"] if a["angle_id"] == later["angle_id"])
    assert waiting["check"]["status"] == "not_queued" and "in progress" in waiting["check"]["message"]
    with repo.connection() as conn:
        conn.execute("UPDATE pipeline_runs SET status='waiting_for_review' WHERE run_id=%s", (busy["run_id"],))
        assert gate_one.queue_deferred_checks(repo, conn, W1)["status"] == "queued"
    drain(worker)
    assert next(a for a in repo.review(W1, APPROVER)["angles"] if a["angle_id"] == later["angle_id"])["can_approve"]


def test_a_check_that_cannot_embed_says_why_on_the_card(gate):
    """Outside a synthetic database a replay cycle never pays: the new version's check waits for its embedding, and the
    card says so instead of staying silently unchecked."""
    repo, worker, post = gate
    top = ranked(repo.review(W1, APPROVER))[0]
    saved = post(f"/angles/{top['angle_id']}/decision", {"expected_hash": top["content_hash"], "disposition": "reframe",
                                                         "reason_code": "voice", "central_point_kept": True,
                                                         "reframe": {"core_perspective": "The calendar shows which couples book."}}).json()
    with repo.connection() as conn:
        conn.execute("UPDATE pipeline_runs SET input_refs=jsonb_set(input_refs,'{mode}','\"replay\"') WHERE run_id=%s",
                     (saved["check"]["run_id"],))
    drain(worker)
    card = next(a for a in repo.review(W1, APPROVER)["angles"] if a["angle_id"] == saved["angle_id"])
    assert card["check"]["status"] == "waiting" and "embedding" in card["check"]["message"].lower() and not card["can_approve"]


def test_a_decision_not_made_by_wia_is_a_delegated_proxy_label(gate):
    """Section 2.3 (measured by WIA) and D12: a decision recorded by someone who is not one of WIA's own reviewers
    (ATELIER_WIA_REVIEWERS), and not relaying one of them, is kept, but its label is a proxy from source
    gate_delegated, so it never calibrates the judge, E.B5 or E.B6 as if it were Whitney's."""
    repo, _, post = gate
    top, second, twin = ranked(repo.review(W1, APPROVER))
    path = lambda a: f"/angles/{a['angle_id']}/decision"  # noqa: E731
    repo.settings.wia_reviewers = ()
    assert post(path(twin), {"expected_hash": twin["content_hash"], "disposition": "skip", "reason_code": "duplicate"}).status_code == 200
    repo.settings.wia_reviewers = ("whitney@wia.example", WHITNEY)
    # The same approver relaying Whitney's verdict, named as its author, records WIA's judgement.
    assert post(path(second), {"expected_hash": second["content_hash"], "disposition": "internal", "reason_code": "internal_use",
                               "author": WHITNEY}).status_code == 200
    repo.settings.wia_reviewers = (APPROVER,)
    body = {"expected_hash": top["content_hash"], "decision": "approved", "cta": DECIDE,
            "verify_acknowledged": top["content_body"]["card"]["verify_before_publishing"]}
    assert post(path(top), body).status_code == 200
    decisions, labels = rows(repo)
    assert [(lab["source"], lab["proxy"]) for lab in labels] == [("gate_delegated", True), ("gate", False), ("gate", False)]
    assert [d["details"]["wia_review"] for d in decisions] == [False, True, True]
    assert labels[0]["details"]["delegated"] is True and len(decisions) == 3, "the delegated decision itself is kept"


def test_a_disposition_and_a_decision_together_are_refused(gate):
    repo, _, post = gate
    top = ranked(repo.review(W1, APPROVER))[0]
    body = {"expected_hash": top["content_hash"], "disposition": "skip", "decision": "rejected", "reason_code": "other"}
    assert post(f"/angles/{top['angle_id']}/decision", body).status_code == 422
    assert post(f"/angles/{top['angle_id']}/decision", {"expected_hash": top["content_hash"]}).status_code == 422


def test_a_card_approved_without_a_disposition_is_still_one_decision_and_one_label(gate):
    """R45: the plain approve route records the decision too, so the decision log and the learning loop see it."""
    repo, worker, post = gate
    top = ranked(repo.review(W1, APPROVER))[0]
    body = {"expected_hash": top["content_hash"], "decision": "approved", "cta": DECIDE,
            "verify_acknowledged": top["content_body"]["card"]["verify_before_publishing"]}
    done = post(f"/angles/{top['angle_id']}/decision", body)
    assert done.status_code == 200, done.text
    decisions, labels = rows(repo)
    assert [(d["item_id"], d["disposition"], d["action"], d["actor"]) for d in decisions] == [
        (top["angle_id"], "develop", "gate_one_approved", APPROVER)]
    assert [label["decision_id"] for label in labels] == [done.json()["decision_id"]]


def test_a_disposition_records_the_rubric_ratings_with_their_version(gate):
    """E.X7: the Gate 1 form shows rubric 2.3a from the API, and a card's disposition records every criterion's rating on
    the label with the rubric's version and text hash. Ratings that miss or invent a criterion, fall outside the scale,
    are not whole numbers, name an old version or none, or come with a plain decision are refused (422) and record
    nothing."""
    from backend_pipeline.gates import rubric
    repo, _, post = gate
    review = repo.review(W1, APPROVER)
    assert review["rubric"]["version"] == "rubric-2.3a.v1" and review["rubric"]["text"] == rubric.TEXT
    top, second, twin = ranked(review)
    path = lambda a: f"/angles/{a['angle_id']}/decision"  # noqa: E731
    ratings = {"wia_is_the_subject": 2, "strategic_purpose": 4, "audience": 3, "worth_attention": 2, "sounds_like_whitney": 4}
    skip = {"expected_hash": twin["content_hash"], "disposition": "skip", "reason_code": "distinctiveness", "author": WHITNEY}
    partial = {k: v for k, v in ratings.items() if k != "audience"}
    refused = [{**skip, "rubric_ratings": partial, "rubric_version": rubric.VERSION},
               {**skip, "rubric_ratings": {**ratings, "tone": 3}, "rubric_version": rubric.VERSION},
               *({**skip, "rubric_ratings": {**ratings, "audience": bad}, "rubric_version": rubric.VERSION}
                 for bad in (0, 6, 2.5, True, "3")),
               {**skip, "rubric_ratings": ratings, "rubric_version": "rubric-2.3a.v0"},
               {**skip, "rubric_ratings": ratings}]
    for body in refused:
        assert post(path(twin), body).status_code == 422, body
    plain = {"expected_hash": top["content_hash"], "decision": "approved", "cta": DECIDE, "rubric_ratings": ratings,
             "verify_acknowledged": top["content_body"]["card"]["verify_before_publishing"]}
    assert post(path(top), plain).status_code == 422
    assert rows(repo) == ([], []), "refused calls record nothing"
    done = post(path(twin), {**skip, "rubric_ratings": ratings, "rubric_version": rubric.VERSION})
    assert done.status_code == 200, done.text
    decisions, labels = rows(repo)
    assert labels[0]["rubric_ratings"] == {"version": "rubric-2.3a.v1", "text_sha256": rubric.TEXT_SHA256,
                                           "criteria": ratings, "overall": 3.0}
    assert decisions[0]["details"]["rubric_version"] == "rubric-2.3a.v1"
    shown = next(a for a in repo.review(W1, APPROVER)["angles"] if a["angle_id"] == twin["angle_id"])
    assert shown["disposition"]["rubric_ratings"]["overall"] == 3.0
    # Rating is optional: a disposition without it records none.
    assert post(path(second), {"expected_hash": second["content_hash"], "disposition": "internal",
                               "reason_code": "internal_use"}).status_code == 200
    assert rows(repo)[1][1]["rubric_ratings"] is None
