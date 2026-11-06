from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from backend_pipeline.calendar.contracts import Reschedule, Schedule, ScheduleItem
from backend_pipeline.calendar.service import authorize, listing
from backend_pipeline.packs.runtime import execution_contract
from backend_pipeline.packs.workflow import validate_copy
from backend_pipeline.production_common import ProductionError
from backend_pipeline.storage_config import StorageSettings


@pytest.mark.parametrize(
    "instant,zone",
    [
        ("2026-10-17T09:00:00", "Asia/Kolkata"),
        ("2026-10-17T09:00:00+00:00", "Asia/Kolkata"),
        ("2026-03-08T02:30:00-06:00", "America/Chicago"),
        ("2026-10-17T09:00:00+05:30", "not/a/timezone"),
    ],
)
def test_invalid_local_time_and_timezone_are_rejected(instant, zone):
    with pytest.raises(ValidationError):
        ScheduleItem(asset_id="asset_one", expected_asset_hash="hash", scheduled_for=instant, display_timezone=zone)
    with pytest.raises(ValidationError):
        Reschedule(request_id="request_123", expected_revision=1, scheduled_for=instant, display_timezone=zone)


def test_explicit_fold_offset_and_unique_targets():
    item = ScheduleItem(
        asset_id="asset_one",
        expected_asset_hash="hash",
        scheduled_for="2026-11-01T01:30:00-05:00",
        display_timezone="America/Chicago",
    )
    assert item.scheduled_for.utcoffset() == timedelta(hours=-5)
    with pytest.raises(ValidationError):
        Schedule(request_id="request_123", expected_pack_manifest_hash="manifest", items=[item, item])
    with pytest.raises(ValidationError):
        ScheduleItem(
            asset_id="asset_one", expected_asset_hash="hash", entry_id="entry_one", scheduled_for="2026-10-17T09:00:00+05:30"
        )


def test_disabled_or_unauthorized_scheduling_never_opens_database():
    repo = SimpleNamespace(settings=StorageSettings())
    with pytest.raises(ProductionError, match="not enabled"):
        authorize(repo, "tester")
    repo.settings.calendar_enabled = True
    with pytest.raises(PermissionError):
        authorize(repo, "tester")
    now = datetime.now(UTC)
    with pytest.raises(ProductionError, match="at most 93 days"):
        listing(repo, now, now + timedelta(days=94))


def test_production_models_are_explicit_and_contract_is_frozen():
    from backend_pipeline.config import Settings

    settings = StorageSettings()
    models = Settings()
    with pytest.raises(ValueError, match="exact pack writer"):
        execution_contract(settings, models)
    settings.pack_writer_model = "configured/writer"
    settings.pack_review_model = "configured/reviewer"
    original = execution_contract(settings, models)
    models.llm_reasoning_effort = "low"  # the default is "high" (the documented default)
    assert execution_contract(settings, models) != original


def test_asset_validation_preserves_cta_claims_and_qualifications():
    brief = {
        "cta": {"text": "Approved next step"},
        "sources": ["evidence_one"],
        "claims": [{"claim_id": "reported", "qualifications": ["Not measured"]}],
        "carousel": [{"number": 1}],
    }
    copy = {
        "cta": brief["cta"],
        "evidence_ids": ["evidence_one"],
        "claims": [{"text": "A reported observation.", "brief_claim_ids": ["reported"], "qualifications": ["Not measured"]}],
    }
    validate_copy(brief, copy, "email")
    copy["claims"][0]["qualifications"] = []
    with pytest.raises(ValueError, match="qualification"):
        validate_copy(brief, copy, "email")
    copy["claims"] = []
    copy["cta"] = {"text": "Unapproved offer"}
    with pytest.raises(ValueError, match="CTA"):
        validate_copy(brief, copy, "email")
