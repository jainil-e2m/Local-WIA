"""E.B25 (f) on a migrated database: the published log's central points are written onto the seed's rows and confirmed,
once; the verifier receives the last twelve months of them (without held-out material); a card repeating one is
flagged, naming the piece, in the cycle's check and in the check an edited card gets."""
from __future__ import annotations

import json
from datetime import date, timedelta

import pytest

from backend_pipeline import storage_cli
from backend_pipeline.config import BACKEND_ROOT
from backend_pipeline.cycle import verification as v
from backend_pipeline.database import connect
from backend_pipeline.knowledge import assembly, delegated, published_points, seed
from backend_pipeline.repository import insert
from backend_pipeline.storage_config import StorageSettings
from backend_pipeline.tests.platform_db import empty, platform_url  # noqa: F401

OWNER = "owner@example.invalid"
ON = date(2026, 10, 20)
seeded = pytest.mark.skipif(not (seed.REPOSITORY_ROOT / seed.DRAFTS).is_dir() or not (seed.REPOSITORY_ROOT / delegated.RECORD).is_file(),
                            reason="The export analysis drafts are not checked out")
UVP_CARD = {"title": "Your ads start before the ad account",
            "core_perspective": "Before you write a single ad or build a landing page, define your unique value proposition.",
            "why_it_matters": "x", "wia_in_action": "WIA view (knowledge base): x", "evidence_points": [], "moment_ids": []}


def run_cli(capsys, *args):
    storage_cli.main(list(args))
    return json.loads(capsys.readouterr().out)


@seeded
def test_the_central_points_are_confirmed_once_and_the_verifier_checks_cards_against_twelve_months(platform_url, monkeypatch, capsys):  # noqa: F811
    empty(platform_url)
    with connect(platform_url) as c:
        seed.run(c, actor="seed", approver=OWNER)
        reviewed = delegated.apply(c, StorageSettings(brief_approvers=(OWNER,)), OWNER)["published_confirmed"]
        with pytest.raises(PermissionError):
            published_points.apply(c, StorageSettings(brief_approvers=(OWNER,)), "viewer@example.invalid")
    monkeypatch.setenv("ATELIER_DATABASE_URL", platform_url)
    monkeypatch.setenv("ATELIER_BRIEF_APPROVERS", OWNER)
    first = run_cli(capsys, "context-published-points", "--actor", OWNER)
    # The 5 October 2026 giveaway is its pieces (E.B25 (i)): five rows of their own beside the campaign's.
    assert first == {"entries": 56, "pieces": 5, "created": 5, "updated": 56, "confirmed": 61 - reviewed, "unchanged": 0}
    second = run_cli(capsys, "context-published-points", "--actor", OWNER)
    assert second == {"entries": 56, "pieces": 5, "created": 0, "updated": 0, "confirmed": 0, "unchanged": 61}, "idempotent"
    with connect(platform_url) as c:
        rows = c.execute("SELECT * FROM published_content WHERE source_kind='export_seed' ORDER BY source_ref").fetchall()
        assert len(rows) == 61 and all(r["status"] == "confirmed" and r["key_message"] and r["published_on"] for r in rows)
        assert c.execute("SELECT count(*) n FROM decisions WHERE item_kind='published_content' AND action='published_confirm'"
                         ).fetchone()["n"] == 61, "one decision per confirmed piece"
        june = next(r for r in rows if r["published_on"] == date(2026, 6, 10))
        assert june["title"].startswith('"The question we ask every new client"') and june["details"]["central_point"]["date_precision"] == "day"

        # Twelve months before the cycle, without the pieces built on held-out Week 6 (E.B17).
        recent = published_points.recent(c, ON)
        dates = [date.fromisoformat(p["published_on"]) for p in recent]
        assert len(recent) == 48 and min(dates) >= ON - timedelta(days=365) and dates == sorted(dates, reverse=True)
        assert not any("22K" in p["title"] or "$70K" in p["title"] for p in recent)
        uvp = next(p for p in recent if "unique value proposition" in p["key_message"])

    # The cycle's verifier receives them from the assembly service and records which it used.
    kb = assembly.assemble("verifier", root=BACKEND_ROOT / "knowledge_base", connection=lambda: connect(platform_url), on=ON)
    assert kb.published_points == recent and kb.refs()["context"]["published_points"] == [p["content_id"] for p in recent]
    flags = [f for f in v.verify_card(UVP_CARD, {}, kb.roster, [], published=kb.published_points)["flags"] if f["kind"] == "published_point"]
    assert len(flags) == 1 and flags[0]["published"]["content_id"] == uvp["content_id"] and flags[0]["severity"] == v.CHECK
    assert "2026-09-15" in flags[0]["message"] and "What I taught my clients this week" in flags[0]["message"]
    # The strategist sees them first (its situational block): a recent piece with its central point, and the year before.
    strategist = assembly.assemble("strategist", root=BACKEND_ROOT / "knowledge_base", connection=lambda: connect(platform_url), on=ON)
    assert f"(central point: {uvp['key_message']})" in strategist.situational
    assert "### Central points WIA published earlier in the last twelve months" in strategist.situational
    assert f"- 2026-06-10 {june['channel']}: {june['key_message']}" in strategist.situational
    assert not any("22K" in line or "$70K" in line for line in strategist.situational.splitlines())
    other = {**UVP_CARD, "title": "One job per landing page", "core_perspective": "A landing page converts when it asks for one action."}
    assert not [f for f in v.verify_card(other, {}, kb.roster, [], published=kb.published_points)["flags"] if f["kind"] == "published_point"]


def test_an_edited_card_is_checked_against_the_points_published_in_the_last_twelve_months(platform_url):  # noqa: F811
    empty(platform_url)
    today = date.today()
    with connect(platform_url) as c:
        for content_id, published_on in (("published_recent", today - timedelta(days=30)), ("published_old", today - timedelta(days=400))):
            insert(c, "published_content", {"content_id": content_id, "published_on": published_on, "channel": "Email",
                                             "title": "What I taught my clients this week", "status": "confirmed",
                                             "key_message": "Advertising starts before the ads: define your unique value proposition "
                                                            "before you write an ad or build a landing page.",
                                             "source_kind": "approver_entry", "source_ref": content_id, "created_by": OWNER})
        ledger = v.ledger_from_database(c, UVP_CARD)
    flags = [f for f in ledger["flags"] if f["kind"] == "published_point"]
    assert [f["published"]["content_id"] for f in flags] == ["published_recent"], "older than twelve months is not compared"
