"""A throwaway database migrated to the latest version (005+), for items that need the platform tables.

The shared atelier_test database stays at the baseline schema other suites expect; this one sits
beside it as atelier_test_platform_test (synthetic runs need a name ending in _test), is created once per session, and is emptied before each test.
"""
from __future__ import annotations

from datetime import date

import pytest
from psycopg import sql

from backend_pipeline.config import Settings
from backend_pipeline.database import connect, migrate
from backend_pipeline.repository import ContentRepository
from backend_pipeline.storage_config import StorageSettings
from backend_pipeline.tests.test_migrations_db import URL, recreate

APPROVER, EDITOR = "whitney@example.invalid", "giselle@example.invalid"


@pytest.fixture(scope="session")
def platform_url():
    if not URL:
        pytest.skip("Set isolated ATELIER_TEST_DATABASE_URL to run PostgreSQL integration tests")
    url = recreate("atelier_test_platform_test")
    migrate(url)
    return url


def empty(url):
    with connect(url, vectors=False) as conn:
        names = [r["tablename"] for r in conn.execute(
            "SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename<>'schema_migrations'")]
        conn.execute(sql.SQL("TRUNCATE {} CASCADE").format(sql.SQL(",").join(map(sql.Identifier, sorted(names)))))


@pytest.fixture
def platform_setup(platform_url, tmp_path):
    """Like test_sql_storage.setup, on the migrated database: two synthetic weeks admitted."""
    empty(platform_url)
    settings = StorageSettings(database_url=platform_url, artifact_root=tmp_path / "artifacts", synthetic=True,
                               api_secret="test-secret", brief_approvers=(APPROVER, "tester"), brief_editors=(EDITOR, "editor"))
    repo = ContentRepository(settings)
    # The synthetic weeks are made for the whole-week prompt; the ledger profile (the default, E.B12) has its own tests.
    models = Settings(data_root=tmp_path / "legacy", llm_payload_format="compact_weekly", extraction_profile="2026-10-13.weekly.v3")
    for i, start in [(1, date(2026, 6, 1)), (2, date(2026, 6, 8))]:
        folder = tmp_path / f"week{i}"
        folder.mkdir()
        (folder / "meeting.vtt").write_text(
            "WEBVTT\n\n1\n00:00:01.000 --> 00:00:04.000\nAlice: We improved the follow-up.\n\n2\n"
            "00:00:04.000 --> 00:00:09.000\nAlice: It was an observation, not a measured result.\n", encoding="utf-8")
        repo.admit(folder, start, i)
    return repo, models, tmp_path
