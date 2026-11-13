"""AI-proposed actions wait for an admin: approved (as proposed or edited) they join the Action Hub, rejected they
leave the review queue, and each is decided once."""
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.db import transaction
from backend.models.db import ActionCandidate, AiRun, AuditEvent, Business
from backend.services.read_models import portfolio
from backend.tests.services.test_ai_layer import (
    meeting,  # noqa: F401  (fixture: a client with one Fathom meeting)
)


def client():
    from backend.app import app
    return TestClient(app)


def propose(record_id: str, title="Send the revised landing page") -> str:
    with transaction() as s:
        business = s.execute(select(Business).where(Business.slug == "venue-one")).scalar_one()
        run = AiRun(id=uuid4(), skill="meeting_digest", skill_version="t", model="t", subject_kind="meeting",
                    subject_id=record_id + str(uuid4()), business_id=business.id, input_hash=uuid4().hex, state="succeeded")
        s.add(run)
        s.flush()
        c = ActionCandidate(id=uuid4(), run_id=run.id, business_id=business.id, kind="new", title=title, owner_side="WIA",
                            owner_name="Jacqueline", quote="We will send the revised landing page by Friday",
                            source_record_id=UUID(record_id), verified=True)
        s.add(c)
        return "ai-" + c.id.hex


def decide(ref, decision, **body):
    return client().post(f"/api/v1/actions/proposals/{ref}/decision", json={"decision": decision, "admin": "Whitney", **body})


def test_a_proposal_waits_in_review_and_is_not_an_action(meeting):  # noqa: F811
    ref = propose(meeting)
    built = portfolio.build()
    assert [i["id"] for i in built["reviewItems"]] == [ref]
    assert ref not in {a["id"] for a in built["actions"]}


def test_an_admin_approves_with_edits_and_it_becomes_an_action(meeting):  # noqa: F811
    ref = propose(meeting)
    r = decide(ref, "approve", edits={"title": "  Send the  new landing page ", "owner": "Carmen", "due": "2026-11-20"})
    assert r.status_code == 200 and r.json() == {"id": ref, "status": "approved", "edited": ["due_date", "owner_name", "title"]}
    built = portfolio.build()
    assert not built["reviewItems"]
    [action] = [a for a in built["actions"] if a["id"] == ref]
    assert (action["title"], action["owner"], action["due"], action["status"], action["origin"]) == (
        "Send the new landing page", "Carmen", "2026-11-20", "Open", "Meeting")
    assert "Whitney" in action["note"] and action["sourceId"].startswith("kb-")
    with transaction() as s:
        event = s.execute(select(AuditEvent).where(AuditEvent.action == "action_candidate.approved")).scalar_one()
        assert event.details["edited"]["title"] == {"from": "Send the revised landing page", "to": "Send the new landing page"}
        assert event.actor.startswith("Whitney")


def test_a_rejected_proposal_leaves_review_and_never_becomes_an_action(meeting):  # noqa: F811
    ref = propose(meeting)
    assert decide(ref, "reject", reason="Already handled").json()["status"] == "rejected"
    built = portfolio.build()
    assert not built["reviewItems"] and ref not in {a["id"] for a in built["actions"]}


def test_each_proposal_is_decided_once_and_bad_requests_change_nothing(meeting):  # noqa: F811
    ref = propose(meeting)
    for body in ({"edits": {"title": " "}}, {"edits": {"due": "Friday"}}, {"edits": {"side": "Agency"}},
                 {"edits": {"quote": "x"}}):
        r = decide(ref, "approve", **body)
        assert r.status_code == 400 and r.json()["detail"]["code"] == "refused"
    assert decide("ai-" + uuid4().hex, "approve").status_code == 400
    assert decide("not-an-id", "approve").status_code == 400
    assert decide(ref, "approve").status_code == 200
    again = decide(ref, "reject")
    assert again.status_code == 400 and "already approved by Whitney" in again.json()["detail"]["message"]


def test_test_proposals_seed_into_review_and_remove_cleanly(meeting):  # noqa: F811
    from backend.scripts import seed_test_proposals
    with transaction() as s:
        assert seed_test_proposals.seed(s) == 2
    items = portfolio.build()["reviewItems"]
    assert len(items) == 2 and all(i["title"].startswith("[TEST] ") for i in items)
    assert decide(items[0]["id"], "approve").status_code == 200
    with transaction() as s:
        assert seed_test_proposals.remove(s) == 2
    built = portfolio.build()
    assert not built["reviewItems"] and not [a for a in built["actions"] if a["title"].startswith("[TEST]")]
