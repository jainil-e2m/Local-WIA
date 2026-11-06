"""The production portfolio: built by the refresh job, served whole with an ETag; logos only from the build."""
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.db import transaction
from backend.models.db import WorkItem
from backend.services.clients import mapping
from backend.services.read_models import portfolio


def client():
    from backend.app import app
    return TestClient(app)


def test_not_built_yet_says_so():
    r = client().get("/api/v1/portfolio")
    assert r.status_code == 404 and r.json()["detail"]["code"] == "not_built"


def test_refresh_then_serve_with_etag_and_304():
    with transaction() as s:
        mapping.create_client(s, name="Venue One", slug="venue-one", actor="t", discover=False)
    portfolio.refresh()
    c = client()
    r = c.get("/api/v1/portfolio")
    assert r.status_code == 200 and [x["id"] for x in r.json()["clients"]] == ["venue-one"]
    assert c.get("/api/v1/portfolio", headers={"If-None-Match": r.headers["etag"]}).status_code == 304


def test_a_mapping_decision_queues_one_coalesced_rebuild():
    with transaction() as s:
        mapping.create_client(s, name="Venue One", slug="venue-one", actor="t", discover=False)
        mapping.create_client(s, name="Venue Two", slug="venue-two", actor="t", discover=False)
    with transaction() as s:
        rows = s.execute(select(WorkItem.lane, WorkItem.next_run_at).where(WorkItem.kind == portfolio.JOB)).all()
    assert len(rows) == 1 and rows[0].lane == "maintenance"


def test_logo_route_serves_only_logos_the_build_chose():
    portfolio.refresh()
    assert client().get(f"/api/v1/portfolio/logos/{uuid4()}").status_code == 404
