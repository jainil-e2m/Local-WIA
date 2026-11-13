"""Shared edits: one person's saved change is everyone's, a stale save never overwrites a colleague's."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.db import transaction
from backend.models.db import AuditEvent
from backend.services import edits
from backend.services.clients import mapping


@pytest.fixture
def venue():
    with transaction() as s:
        mapping.create_client(s, name="Venue One", slug="venue-one", actor="t", discover=False)


def client():
    from backend.app import app
    return TestClient(app)


def test_a_saved_change_is_loaded_by_everyone_and_merges_field_by_field(venue):
    c = client()
    first = c.put("/api/v1/edits/action/cu-123", json={"changes": {"status": "Done", "note": "Sent the page"},
                                                       "expected_revision": None, "viewer": "Whitney"})
    assert first.status_code == 200 and first.json()["revision"] == 1
    second = c.put("/api/v1/edits/action/cu-123", json={"changes": {"owner": "Gisselle", "note": None},
                                                        "expected_revision": 1, "viewer": "Gisselle"})
    assert second.json()["data"] == {"status": "Done", "owner": "Gisselle"}  # null: the note follows the KB again
    loaded = c.get("/api/v1/edits").json()
    assert loaded["actions"]["cu-123"]["revision"] == 2 and loaded["actions"]["cu-123"]["by"].startswith("Gisselle")
    with transaction() as s:
        audit = s.execute(select(AuditEvent).where(AuditEvent.action == "edit.action")).scalars().all()
    assert [a.details["fields"] for a in audit] == [["note", "status"], ["note", "owner"]]
    assert "Sent the page" not in str([a.details for a in audit])  # which fields, never their values


def test_a_save_based_on_an_old_copy_is_refused_with_the_current_one(venue):
    c = client()
    c.put("/api/v1/edits/client/venue-one", json={"changes": {"coverId": "olive-arch"}, "viewer": "Whitney"})
    stale = c.put("/api/v1/edits/client/venue-one", json={"changes": {"coverId": "white-roses"}, "viewer": "Gisselle"})
    assert stale.status_code == 409
    detail = stale.json()["detail"]
    assert detail["current"]["data"] == {"coverId": "olive-arch"} and detail["message"].startswith("Whitney changed this")
    ok = c.put("/api/v1/edits/client/venue-one", json={"changes": {"coverId": "white-roses"}, "expected_revision": 1})
    assert ok.status_code == 200 and ok.json()["data"]["coverId"] == "white-roses"


@pytest.mark.parametrize("kind, key, changes, why", [
    ("action", "cu-1", {"password": "x"}, "unknown field"),
    ("action", "cu-1", {"status": "Finished"}, "bad status"),
    ("action", "cu-1", {"due": "next week"}, "due must be"),
    ("action", "app-1", {"created": True, "clientId": "nobody", "title": "x"}, "unknown client"),
    ("client", "nobody", {"archived": True}, "unknown client"),
    ("client", "venue-one", {}, "nothing to save"),
    ("client", "venue-one", {"logo": {"dataUri": "x" * 4_000_000}}, "too large"),
    ("action", "../etc", {"note": "x"}, "bad key"),
])
def test_what_cannot_be_saved(venue, kind, key, changes, why):
    with transaction() as s, pytest.raises(edits.EditError, match=why):
        edits.save(s, kind, key, changes, expected_revision=None, actor="t")
