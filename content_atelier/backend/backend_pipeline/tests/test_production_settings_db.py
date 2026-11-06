"""E.X4 (provisional): `settings apply` stores a configuration file as rows, all or nothing, and a second run changes nothing."""
import pytest

from backend_pipeline import settings_store
from backend_pipeline.database import connect
from backend_pipeline.settings_store import SettingError
from backend_pipeline.tests.platform_db import platform_setup, platform_url  # noqa: F401 (fixtures)
from backend_pipeline.tests.test_settings_db import database  # noqa: F401 (fixture)

PROFILE = {"settings": {"prompts.profile.brief": "brief_document_v2", "prompts.profile.brief_writer": "v3",
                        "models.brief": "openai/gpt-6.1-sol"}}


def test_a_configuration_applies_all_or_nothing_and_twice_changes_nothing(database):  # noqa: F811
    with connect(database, vectors=False) as conn:
        dry = settings_store.apply_profile(conn, PROFILE, "approver@example.invalid", dry_run=True)
        assert set(dry["would_change"]) == set(PROFILE["settings"])
        assert settings_store.load(conn, read_files=False).sources["prompts.profile.brief_writer"] == "default", "a dry run stores nothing"
        out = settings_store.apply_profile(conn, PROFILE, "approver@example.invalid")
        conn.commit()
        assert {a["key"] for a in out["applied"]} == set(PROFILE["settings"])
        effective = settings_store.load(conn, read_files=False)
        assert effective.values["prompts.profile.brief_writer"] == "v3" and effective.sources["prompts.profile.brief_writer"] == "table"
        again = settings_store.apply_profile(conn, PROFILE, "approver@example.invalid")
        assert again["applied"] == [] and set(again["unchanged"]) == set(PROFILE["settings"])
        with pytest.raises(SettingError):
            settings_store.apply_profile(conn, {"settings": {"prompts.profile.brief_writer": "v2", "models.nope": "x"}}, "a@b.c")
        conn.rollback()
        assert settings_store.load(conn, read_files=False).values["prompts.profile.brief_writer"] == "v3", "nothing was stored"
