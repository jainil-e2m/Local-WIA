"""Production and calendar acceptance against an explicitly isolated PostgreSQL database."""

import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from test_briefs import BriefProvider, finish, ready
from test_sql_storage import URL, drain
from test_sql_storage import setup as setup  # noqa: PLC0414 - pytest fixture registration

from backend_pipeline import publications
from backend_pipeline.briefs import gate_two
from backend_pipeline.calendar import service as calendar
from backend_pipeline.calendar.contracts import Cancel, Reschedule, Schedule, ScheduleItem
from backend_pipeline.database import check, migrate
from backend_pipeline.packs import service as packs
from backend_pipeline.packs.contracts import Decision, Generate
from backend_pipeline.packs.workflow import queue
from backend_pipeline.production_common import ProductionError
from backend_pipeline.storage_api import router

pytestmark = pytest.mark.skipif(not URL, reason="Requires isolated ATELIER_TEST_DATABASE_URL")


class PackProvider(BriefProvider):
    fail_slot = None

    def json_call(self, *, stage, system, user, schema, fingerprint):
        if stage not in {"pack_write", "pack_review"}:
            return super().json_call(stage=stage, system=system, user=user, schema=schema, fingerprint=fingerprint)
        p = json.loads(user)
        self.calls.append(stage + ":" + p.get("slot", "review"))
        if stage == "pack_review":
            return {"preserves_approved_direction": True, "grounded": True, "distinct_contributions": True, "findings": []}, {
                "fake": True
            }
        slot, brief = p["slot"], p["approved_brief"]
        if self.fail_slot == slot:
            raise ValueError("Synthetic failed slot")
        c = brief["claims"][0]
        output = {
            "title": "Saved " + slot,
            "claims": [{"text": c["text"], "brief_claim_ids": [c["claim_id"]], "qualifications": c["qualifications"]}],
            "evidence_ids": brief["sources"],
            "cta": brief["cta"],
        }
        if slot == "email":
            output.update(
                subject_lines=["A bounded review"],
                subject="A bounded review",
                preview_text="Review the evidence",
                body="An improvement was reported, not measured. Review the original observation.",
            )
        elif slot == "carousel":
            output.update(
                slides=[
                    {
                        "number": s["number"],
                        "headline": "Bounded review",
                        "body": "Keep the limitation.",
                        "direction": "Clear text",
                    }
                    for s in brief["carousel"]
                ],
                caption="A reported observation, not measured.",
            )
        else:
            output.update(
                spoken_script="An improvement was reported. It was not measured. Review the next step.",
                caption="A bounded observation.",
                visual_directions=["Speak clearly."],
            )
        return output, {"fake": True}


@pytest.fixture
def produced(setup):
    repo, models, _ = setup
    with repo.connection() as c:
        c.execute("TRUNCATE mutation_receipts")
    r = ready(setup)
    row = finish(r)
    row = gate_two.get(
        repo,
        gate_two.answers(repo, row["brief_id"], row["content_hash"], {"distribution": "Email first"}, "tester")["brief_id"],
        "tester",
    )
    row = gate_two.get(
        repo,
        gate_two.review(
            repo, row["brief_id"], row["content_hash"], ["claim_observation"], "Checked source and scope", True, "tester"
        )["brief_id"],
        "tester",
    )
    gate_two.decide(repo, row["brief_id"], row["content_hash"], "approved", "Approved", "tester")
    repo.settings.packs_enabled = repo.settings.calendar_enabled = True
    repo.settings.pack_editors = repo.settings.pack_approvers = repo.settings.calendar_schedulers = ("tester",)
    p = PackProvider()
    r[3].provider = p
    request = Generate(request_id=str(uuid4()), expected_brief_hash=row["content_hash"])
    run = queue(repo, row["brief_id"], request, "tester", synthetic=True, model_settings=models)
    drain(r[3], limit=10)
    pack = packs.detail(repo, run["pack_id"], "tester")
    assert pack["can_approve"], pack["blockers"]
    packs.decide(
        repo,
        pack["pack_id"],
        Decision(request_id=str(uuid4()), expected_manifest_hash=pack["manifest_hash"], decision="approved"),
        "tester",
    )
    return repo, packs.detail(repo, pack["pack_id"], "tester"), r[3], p, row


def scheduling(pack, *, whole=True):
    when = (datetime.now(UTC) + timedelta(days=30)).replace(second=0, microsecond=0).astimezone(ZoneInfo("Asia/Kolkata"))
    return Schedule(
        request_id=str(uuid4()),
        expected_pack_manifest_hash=pack["manifest_hash"],
        whole_pack=whole,
        items=[
            ScheduleItem(asset_id=a["asset_id"], expected_asset_hash=a["content_hash"], scheduled_for=when)
            for a in pack["assets"][: 5 if whole else 1]
        ],
    )


def test_end_to_end_persisted_pack_five_schedules_and_receipt(produced):
    repo, pack, _worker, provider, _ = produced
    request = scheduling(pack)
    saved = calendar.schedule(repo, pack["pack_id"], request, "tester")
    assert len(saved["entries"]) == 5
    assert calendar.schedule(repo, pack["pack_id"], request, "tester") == saved
    assert len([c for c in provider.calls if c.startswith("pack_write")]) == 5
    start = request.items[0].scheduled_for - timedelta(hours=1)
    first = calendar.listing(repo, start, start + timedelta(days=1), limit=2)
    second = calendar.listing(repo, start, start + timedelta(days=1), cursor=first["next_cursor"], limit=2)
    third = calendar.listing(repo, start, start + timedelta(days=1), cursor=second["next_cursor"], limit=2)
    assert len(first["items"] + second["items"] + third["items"]) == 5 and third["next_cursor"] is None
    assert all(e["effective_status"] == "scheduled" for e in first["items"])
    assert len(packs.detail(repo, pack["pack_id"], "other-team")["assets"][0]["schedule"]) == 1
    with repo.connection() as c:
        assert check(c)["tables"] >= 14


def test_batch_rollback_stale_asset_and_new_request_conflict(produced):
    repo, pack, *_ = produced
    request = scheduling(pack)
    request.items[-1].expected_asset_hash = "changed"
    with pytest.raises(ProductionError):
        calendar.schedule(repo, pack["pack_id"], request, "tester")
    with repo.connection() as c:
        assert c.execute("SELECT count(*) n FROM calendar_entries").fetchone()["n"] == 0
    request.items[-1].expected_asset_hash = pack["assets"][-1]["content_hash"]
    calendar.schedule(repo, pack["pack_id"], request, "tester")
    with pytest.raises(ProductionError, match="Another scheduler"):
        calendar.schedule(repo, pack["pack_id"], scheduling(pack), "tester")
    request.items[0].scheduled_for += timedelta(minutes=1)
    with pytest.raises(ProductionError, match="Request ID"):
        calendar.schedule(repo, pack["pack_id"], request, "tester")


def test_reschedule_cancel_and_history_are_separate(produced):
    repo, pack, _, _, brief = produced
    request = scheduling(pack, whole=False)
    entry = calendar.schedule(repo, pack["pack_id"], request, "tester")["entries"][0]
    with repo.connection() as c:
        assert publications.confirmed(c, brief["angle_id"]) == []
    moved = Reschedule(
        request_id=str(uuid4()),
        expected_revision=entry["revision"],
        scheduled_for=request.items[0].scheduled_for + timedelta(days=1),
    )
    result = calendar.reschedule(repo, entry["calendar_entry_id"], moved, "tester")
    assert result["entries"][0]["revision"] == 2
    assert calendar.reschedule(repo, entry["calendar_entry_id"], moved, "tester") == result
    with pytest.raises(ProductionError):
        calendar.reschedule(repo, entry["calendar_entry_id"], moved.model_copy(update={"request_id": str(uuid4())}), "tester")
    cancel = Cancel(request_id=str(uuid4()), expected_revision=2)
    assert calendar.cancel(repo, entry["calendar_entry_id"], cancel, "tester")["status"] == "cancelled"
    assert calendar.cancel(repo, entry["calendar_entry_id"], cancel, "tester")["revision"] == 3
    assert gate_two.get(repo, brief["brief_id"], "tester")["can_consume"]


def test_permissions_blocked_versions_and_api(produced):
    repo, pack, *_ = produced
    request = scheduling(pack)
    with pytest.raises(PermissionError):
        calendar.schedule(repo, pack["pack_id"], request, "reader")
    repo.settings.api_secret = "calendar-test-secret"
    app = FastAPI()
    app.include_router(router(repo.settings))
    client = TestClient(app)
    assert client.get("/storage/packs").status_code == 401
    # Roles key on the verified email alone (R37, 0.B9): "tester" is still on the lists, but an actor that is not an
    # email address holds no role, so the API refuses it where the services (called with the bare name) still accept it.
    bare = {"authorization": "Bearer calendar-test-secret", "x-atelier-actor": "tester"}
    assert not client.get("/storage/calendar/config", headers=bare).json()["can_schedule"]
    assert client.post("/storage/packs/" + pack["pack_id"] + "/schedule", json=request.model_dump(mode="json"), headers=bare).status_code == 401
    repo.settings.calendar_schedulers = ("tester", "scheduler@example.invalid")
    headers = {"authorization": "Bearer calendar-test-secret", "x-atelier-actor": "Scheduler@Example.invalid"}
    assert client.get("/storage/calendar/config", headers=headers).json()["can_schedule"]
    assert (
        client.post(
            "/storage/packs/" + pack["pack_id"] + "/schedule", json=request.model_dump(mode="json"), headers=headers
        ).status_code
        == 200
    )
    assert client.get("/storage/packs/" + pack["pack_id"], headers=headers).json()["pack_id"] == pack["pack_id"]
    with repo.connection() as c:
        c.execute("UPDATE content_packs SET approval_status='rejected' WHERE pack_id=%s", (pack["pack_id"],))
    with pytest.raises(ProductionError):
        calendar.schedule(repo, pack["pack_id"], scheduling(pack), "tester")
    start = request.items[0].scheduled_for - timedelta(hours=1)
    assert all(e["effective_status"] == "needs_review" for e in calendar.listing(repo, start, start + timedelta(days=1))["items"])


def test_empty_calendar_and_migration_idempotence(setup):
    repo, *_ = setup
    assert migrate(repo.settings.database_url)["status"] == "already_current"
    repo.settings.calendar_enabled = True
    now = datetime.now(UTC)
    assert calendar.listing(repo, now, now + timedelta(days=1))["items"] == []


def test_concurrent_schedulers_have_one_winner(produced):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    repo, pack, *_ = produced
    barrier = Barrier(2)

    def attempt():
        request = scheduling(pack, whole=False)
        barrier.wait(timeout=5)
        try:
            return calendar.schedule(repo, pack["pack_id"], request, "tester")
        except ProductionError as error:
            return error.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: attempt(), range(2)))
    assert sum(isinstance(v, dict) for v in results) == 1
    assert "stale_schedule" in results
    with repo.connection() as conn:
        assert conn.execute("SELECT count(*) n FROM calendar_entries").fetchone()["n"] == 1


def test_failed_slot_retry_reuses_successful_siblings(produced):
    repo, pack, worker, provider, brief = produced
    request = Generate(request_id=str(uuid4()), expected_brief_hash=brief["content_hash"], supersedes_id=pack["pack_id"])
    repo.settings.pack_writer_model = "synthetic-retry"
    provider.fail_slot = "email"
    run = queue(repo, brief["brief_id"], request, "tester", synthetic=True, model_settings=worker.models)
    drain(worker, limit=10)
    with repo.connection() as conn:
        failed = conn.execute("SELECT job_id FROM pipeline_jobs WHERE run_id=%s AND status='failed'", (run["run_id"],)).fetchone()
    assert failed
    provider.fail_slot = None
    from collections import Counter

    before = Counter(provider.calls)
    repo.retry(failed["job_id"], "tester")
    drain(worker, limit=10)
    result = packs.detail(repo, run["pack_id"], "tester")
    assert result["can_approve"], result["blockers"]
    # Already validated output/cache is reused; no new request for successful siblings.
    after = Counter(provider.calls)
    assert after["pack_write:email"] == before["pack_write:email"] + 1
    for slot in ("carousel", "reel_1", "reel_2", "reel_3"):
        assert after["pack_write:" + slot] == 2  # one original pack, one replacement; no repeat after retry
