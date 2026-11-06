"""E.B11 (e) in the database suite: a published knowledge-base version reads back with identical text and hashes."""
from __future__ import annotations

import shutil

import pytest

from backend_pipeline.config import BACKEND_ROOT
from backend_pipeline.database import connect
from backend_pipeline.knowledge_base import load_knowledge_base, load_published, publish
from backend_pipeline.tests.platform_db import empty, platform_url  # noqa: F401 (fixture)

KB = BACKEND_ROOT / "knowledge_base"


def test_published_version_matches_the_files_in_every_stage(platform_url):  # noqa: F811
    empty(platform_url)
    with connect(platform_url, vectors=False) as conn:
        first = publish(conn, KB, approver="whitney@example.invalid")
        again = publish(conn, KB, approver="whitney@example.invalid")
        assert first["written"] and not first["unchanged"]
        assert again["written"] == [] and set(again["unchanged"]) == set(first["written"]), "publishing is idempotent"
        for stage in (None, "strategist", "brief", "verifier", "extraction"):
            files, published = load_knowledge_base(KB, stage=stage), load_published(conn, files_version := load_knowledge_base(KB).version, stage=stage)
            assert published.text == files.text and published.refs() == files.refs() and published.sha256 == files.sha256
            assert files_version == "wia-kb-2026-10-22.c-a1a75795"
        # The verifier reads Whitney's belief statements from a published version too (E.B10), although this version's
        # manifest lists them for the strategist and brief only.
        assert load_published(conn, files_version, stage="verifier").document("belief_statements") is not None


def test_a_published_version_never_changes(platform_url, tmp_path):  # noqa: F811
    empty(platform_url)
    copy = tmp_path / "kb"
    shutil.copytree(KB, copy, ignore=shutil.ignore_patterns("archive"))
    with connect(platform_url, vectors=False) as conn:
        publish(conn, copy, approver="whitney@example.invalid")
        (copy / "04-team-roster.md").write_text((copy / "04-team-roster.md").read_text(encoding="utf-8") + "\nNew line.\n",
                                                encoding="utf-8")
        with pytest.raises(ValueError, match="already published"):
            publish(conn, copy, approver="whitney@example.invalid")
