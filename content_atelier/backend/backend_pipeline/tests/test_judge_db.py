"""E.B3's judge calibration on the migrated database: the labels come through benchmark.ground_truth, WIA's Gate 1
dispositions become pairs (developed or reframed over skipped or internal), and a delegated decision never does (R55).
Fake providers only; a dry run makes no call."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from backend_pipeline.llm import transport
from backend_pipeline.tests.platform_db import APPROVER, platform_setup, platform_url  # noqa: F401 (fixtures)
from backend_pipeline.tests.test_cards_sql import DECIDE, W1, ranked
from backend_pipeline.tests.test_gate_one_decisions_db import WHITNEY, gate  # noqa: F401 (fixture)
from evaluation import benchmark, judge


def test_gate_dispositions_become_calibration_pairs_and_delegated_ones_do_not(gate, monkeypatch, tmp_path):  # noqa: F811
    repo, _, post = gate
    repo.settings.wia_reviewers = (WHITNEY,)
    top, second, twin = ranked(repo.review(W1, APPROVER))
    path = lambda a: f"/angles/{a['angle_id']}/decision"  # noqa: E731
    developed = post(path(top), {"expected_hash": top["content_hash"], "disposition": "develop", "cta": DECIDE, "author": WHITNEY,
                                 "verify_acknowledged": top["content_body"]["card"]["verify_before_publishing"]})
    assert developed.status_code == 200, developed.text
    assert post(path(twin), {"expected_hash": twin["content_hash"], "disposition": "skip", "reason_code": "distinctiveness",
                             "author": WHITNEY}).status_code == 200
    # Recorded by the approver for no one at WIA: a delegated label (D12), which never calibrates the judge.
    assert post(path(second), {"expected_hash": second["content_hash"], "disposition": "internal",
                               "reason_code": "internal_use"}).status_code == 200
    with repo.connection() as conn:
        benchmark.seed(conn)
    monkeypatch.setenv("ATELIER_DATABASE_URL", repo.settings.database_url)
    labels, cards, source = judge.load_labels("auto")
    assert source == "db" and {r["source"] for r in labels} >= {"gate", "gate_delegated", "chatgpt_export"}
    pairs, excluded = judge.pairs_from_labels(labels, cards)
    assert excluded["gate_delegated"] == 1
    assert [(p.group, p.preferred, p.x.id) for p in pairs if p.group == "dispositions"] == [
        ("dispositions", top["angle_id"], twin["angle_id"])]
    assert [p.group for p in pairs].count("export_pairs") == 38 and [p.group for p in pairs].count("week1_reframes") == 6
    shown = judge.request(next(p for p in pairs if p.group == "dispositions"), 0, "")["messages"][1]["content"]
    assert top["content_body"]["card"]["title"] in shown and twin["content_body"]["card"]["title"] in shown

    monkeypatch.setattr(judge, "RUNS", tmp_path / "runs")
    monkeypatch.setattr(transport, "send", lambda *a, **k: pytest.fail("a dry run sends nothing"))
    dry = judge.calibrate(pairs, mode="dry", kb=SimpleNamespace(text="# KB\n\nWIA runs ads.", version="v", sha256="h"),
                          label_source=source, excluded=excluded)
    assert dry["calls"] == 90 and dry["labels"]["pairs"] == {"export_pairs": 38, "week1_reframes": 6, "dispositions": 1}
