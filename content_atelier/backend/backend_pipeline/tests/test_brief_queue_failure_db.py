"""S.B13 "done when" in the database suite: an approval with briefs on and no usable brand bundle is
recorded, its brief run fails with a clear reason that the research route returns, and an approver can
retry through the API once the bundle is fixed."""
from __future__ import annotations

import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend_pipeline import gate_one
from backend_pipeline.sql_pipeline import SQLWorker
from backend_pipeline.storage_api import router
from backend_pipeline.tests.test_sql_storage import URL, NonemptyProvider, drain, setup  # noqa: F401 (fixture)

pytestmark = pytest.mark.skipif(not URL, reason="Requires isolated atelier_test")
APPROVER = "whitney@example.invalid"


def test_approval_without_a_bundle_records_a_failed_run_and_the_api_retries_it(setup):
    repo, models, tmp = setup
    repo.settings.brief_enabled = True
    repo.settings.api_secret = "test-secret"
    repo.settings.brief_approvers = (APPROVER,)
    repo.settings.brief_brand_path = tmp / "missing-brand.json"
    worker = SQLWorker(repo.settings, models, provider=NonemptyProvider())
    repo.submit("week_2026-06-01", "synthetic")
    drain(worker)
    angle = next(a for a in repo.review("week_2026-06-01", APPROVER)["angles"] if a["can_approve"])

    approval = gate_one.decide(repo, angle["angle_id"], angle["content_hash"], "approved", {"text": "Discuss follow-up"},
                               True, "Reviewed", APPROVER)
    assert approval["approval_status"] == "approved"
    assert approval["brief_run"]["status"] == "failed" and "missing-brand.json" in approval["brief_run"]["error"]
    with repo.connection() as conn:
        stored = conn.execute("SELECT approval_status FROM content_angles WHERE angle_id=%s", (angle["angle_id"],)).fetchone()
        assert stored["approval_status"] == "approved", "the approval survives the failed queue"

    app = FastAPI()
    app.include_router(router(repo.settings))
    client = TestClient(app)
    headers = {"Authorization": "Bearer test-secret", "X-Atelier-Actor": APPROVER, "X-Atelier-Email": APPROVER}
    research = client.get(f"/storage/angles/{angle['angle_id']}/research", headers=headers).json()
    assert research["status"] == "failed" and "missing-brand.json" in research["error_summary"]

    retry = f"/storage/angles/{angle['angle_id']}/brief/retry"
    other = {**headers, "X-Atelier-Email": "viewer@example.invalid"}
    assert client.post(retry, headers=other).status_code == 403
    still_broken = client.post(retry, headers=headers)
    assert still_broken.status_code == 409 and "missing-brand.json" in still_broken.json()["detail"]
    with repo.connection() as conn:
        failed = conn.execute("SELECT count(*) n FROM pipeline_runs WHERE run_id LIKE 'brief_run_unqueued_%%'").fetchone()["n"]
    assert failed == 1, "a retry that fails again records nothing more"

    (tmp / "brand.json").write_text(json.dumps({"status": "approved", "approved_by": APPROVER, "voice": ["Plain"],
                                                "strategy": ["Decide"], "cta_rules": ["Exact CTA"], "exemplars": []}),
                                    encoding="utf-8")
    repo.settings.brief_brand_path = tmp / "brand.json"
    queued = client.post(retry, headers=headers)
    assert queued.status_code == 202 and queued.json()["status"] == "queued"
    assert queued.json()["retried_run_id"].startswith("brief_run_unqueued_")
    research = client.get(f"/storage/angles/{angle['angle_id']}/research", headers=headers).json()
    assert research["status"] == "queued" and research["error_summary"] is None
    assert client.post(retry, headers=headers).status_code == 409, "nothing left to retry"


def test_research_status_names_the_angles_current_brief(setup):
    """S.F4: the card links to its brief through the research route."""
    from backend_pipeline.briefs import gate_two
    from backend_pipeline.tests.test_briefs import ready, finish
    data = ready(setup)
    repo, angle = data[0], data[4]
    brief_id = finish(data)
    brief_id = brief_id['brief_id'] if isinstance(brief_id, dict) else brief_id
    status = gate_two.research(repo, angle['angle_id'])
    assert status['brief_id'] == brief_id
