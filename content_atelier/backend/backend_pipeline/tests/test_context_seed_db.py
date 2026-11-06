"""L.B2 on a migrated database: the seed loads once, a second run changes nothing, and nothing is confirmed
without a recorded reviewer."""
from __future__ import annotations

import pytest

from backend_pipeline.database import connect
from backend_pipeline.knowledge import seed
from backend_pipeline.tests.platform_db import empty, platform_url  # noqa: F401

pytestmark = pytest.mark.skipif(not (seed.REPOSITORY_ROOT / seed.DRAFTS).is_dir(), reason="The export analysis drafts are not checked out")
APPROVER = "owner@example.invalid"


def snapshot(conn):
    return (conn.execute("SELECT item_id,hash,status FROM brand_kit_items ORDER BY item_id").fetchall(),
            conn.execute("SELECT content_id,status FROM published_content ORDER BY content_id").fetchall())


def test_the_seed_loads_once_and_a_second_run_changes_nothing(platform_url):  # noqa: F811
    empty(platform_url)
    with connect(platform_url) as conn:
        first = seed.run(conn, actor="seed@example.invalid", approver=APPROVER)
        conn.commit()
        assert first["status"] == "seeded"
        assert first["created"]["candidates"] > 600 and first["created"]["confirmed"] == first["confirmed_items"]
        assert first["created"]["published"] == first["published_content"]
        before = snapshot(conn)
        second = seed.run(conn, actor="seed@example.invalid", approver=APPROVER)
        conn.commit()
        assert second["status"] == "already_seeded" and not any(second["created"].values())
        assert snapshot(conn) == before

        # Nothing is confirmed without a recorded reviewer; only E.X2's documents load as confirmed.
        rows = conn.execute("SELECT status,source_kind,reviewed_by,review_note,model_written FROM brand_kit_items").fetchall()
        confirmed = [r for r in rows if r["status"] == "confirmed"]
        assert confirmed and all(r["reviewed_by"] == APPROVER and r["review_note"].startswith("E.X2")
                                 and r["source_kind"] == "knowledge_base" for r in confirmed)
        assert all(r["reviewed_by"] is None for r in rows if r["status"] == "candidate")
        assert all(r["status"] == "candidate" for r in rows if r["model_written"])
        assert conn.execute("SELECT count(*) n FROM published_content WHERE status<>'unconfirmed'").fetchone()["n"] == 0

        # After the seed, nothing from ChatGPT is accepted (R52): a run with other inputs is refused.
        conn.execute("UPDATE settings SET value=jsonb_set(value,'{input_sha256}','\"changed\"') WHERE key=%s", (seed.SEED_MARKER,))
        with pytest.raises(ValueError, match="already run with other inputs"):
            seed.run(conn, actor="seed@example.invalid", approver=APPROVER)
        conn.rollback()


def test_the_seed_needs_the_context_store_and_an_approver(platform_url):  # noqa: F811
    empty(platform_url)
    with connect(platform_url) as conn:
        with pytest.raises(ValueError, match="E.X2 approver"):
            seed.run(conn, actor="seed", approver=" ")


def test_the_command_seeds_and_deletes_by_source(platform_url, monkeypatch, capsys):  # noqa: F811
    import json

    from backend_pipeline import storage_cli
    empty(platform_url)
    monkeypatch.setenv("ATELIER_DATABASE_URL", platform_url)
    storage_cli.main(["context-seed", "--approver", APPROVER, "--actor", "seed@example.invalid"])
    seeded = json.loads(capsys.readouterr().out)
    assert seeded["status"] == "seeded"
    storage_cli.main(["context-delete-source", "--source-kind", "export_seed", "--source-ref-prefix",
                      "research/chatgpt-export-2026-10-18/kb-candidates/belief-statements.md", "--actor", "owner@example.invalid",
                      "--reason", "test of delete-by-source"])
    deleted = json.loads(capsys.readouterr().out)
    assert deleted["deleted_items"] > 50 and deleted["kept_confirmed"] == 0
    with connect(platform_url) as conn:
        assert conn.execute("SELECT count(*) n FROM brand_kit_items WHERE kind='belief'").fetchone()["n"] == 0
        assert conn.execute("SELECT count(*) n FROM decisions WHERE action='delete_source'").fetchone()["n"] == 1
    # The deletion lasts (L.B1): running the seed again brings none of the deleted entries back.
    storage_cli.main(["context-seed", "--approver", APPROVER, "--actor", "seed@example.invalid"])
    again = json.loads(capsys.readouterr().out)
    assert not any(again["created"].values()) and again["skipped_deleted"] > 50
    with connect(platform_url) as conn:
        assert conn.execute("SELECT count(*) n FROM brand_kit_items WHERE kind='belief'").fetchone()["n"] == 0


def test_a_chatgpt_draft_wia_approved_is_still_model_written(platform_url):  # noqa: F811
    """R52: author attribution separates Whitney from the model; a ChatGPT draft Whitney approved is model-written."""
    empty(platform_url)
    with connect(platform_url) as conn:
        seed.run(conn, actor="seed@example.invalid", approver=APPROVER)
        rows = conn.execute("SELECT author,model_written FROM brand_kit_items WHERE kind='exemplar'").fetchall()
    drafted = [r for r in rows if "chatgpt" in (r["author"] or "").lower()]
    assert drafted and all(r["model_written"] for r in drafted)


def test_the_seed_explains_where_it_runs(platform_url, tmp_path):  # noqa: F811
    empty(platform_url)
    with connect(platform_url) as conn:
        with pytest.raises(RuntimeError, match="repository checkout"):
            seed.run(conn, actor="seed", approver=APPROVER, root=tmp_path)
