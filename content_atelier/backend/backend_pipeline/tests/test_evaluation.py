"""E.B2 and E.B3 offline: benchmark version 1's labels and guard, and the evaluation command's requests and report.
No database and no HTTP; a paid sample is refused without a run plan."""
from __future__ import annotations

import json

import httpx

import pytest

from backend_pipeline.angle_profiles import STRATEGIST_V5_PROFILE
from backend_pipeline.config import PROJECT_ROOT
from backend_pipeline.llm import transport
from backend_pipeline.llm.run_plans import NoPlan, RunPlanError
from backend_pipeline.store import canonical_hash
from evaluation import benchmark, regressions, run
from evaluation.__main__ import main


def test_benchmark_v1_labels_record_their_source_and_proxy_flag():
    labels = benchmark.build_labels()
    by_source = {}
    for row in labels:
        by_source.setdefault(row["source"], []).append(row)
    week1 = by_source["whitney_week1_review_2026-10-13"]
    assert len(week1) == 6 and not any(r["proxy"] for r in week1), "Whitney's own verdict and reframes"
    assert all(r["disposition"] == "reframe" and r["central_point_kept"] is False and r["reframe"]["title"] for r in week1)
    assert all(r["rubric_ratings"]["overall"] == 1 for r in week1) and week1[0]["week_id"] == "week_2026-06-01"
    assert [r["proxy"] for r in by_source["chatgpt_review_week2"]] == [True]
    assert len(by_source["root_cause_2026-10-16"]) == 6 and all(r["proxy"] for r in by_source["root_cause_2026-10-16"])
    pairs = by_source["chatgpt_export"]
    assert len(pairs) == 38 and all(r["proxy"] and r["details"]["her_text"] for r in pairs), "the calibration set survives L.X2"
    assert len({r["label_id"] for r in labels}) == len(labels), "stable, unique label IDs"
    assert {r["week_id"] for r in labels} >= {"week_2026-06-15", "week_2026-06-22"} and "week_2026-07-06" not in {r["week_id"] for r in labels}


def test_week_6_is_never_read_and_the_weeks_follow_the_backfill():
    with pytest.raises(ValueError, match="Week 6 is held out"):
        benchmark.guard(PROJECT_ROOT / "backend" / "zoom_backfill_meetings" / "week6" / "call.vtt")
    assert benchmark.guard(PROJECT_ROOT / "week16.json")
    assert benchmark.week_start(5).isoformat() == "2026-06-29" and benchmark.week_start(6).isoformat() == "2026-07-06"
    manifest = benchmark.manifest()
    assert manifest["held_out"]["week6"].startswith("held out") and all(v["sha256"] for v in manifest["sources"].values())


def test_requests_are_built_by_the_products_own_prompt_builders():
    default, _ = run.request("default", "week1")
    v5, moments = run.request("strategist_v5", "week2")
    assert default["model"] == "openai/gpt-6-luna" and default["response_format"]["json_schema"]["schema"]["title"] == "StrategicAngleResponse"
    assert v5["model"] == "openai/gpt-6.1-sol" and v5["reasoning"] == {"effort": "high"}
    assert v5["response_format"]["json_schema"]["schema"]["title"] == "WeeklyAngleCardsV5"
    assert "wia-kb-2026-10-22.c-a1a75795" in v5["messages"][0]["content"] and "## Scene S1" in v5["messages"][1]["content"]
    assert [m["moment_id"] for m in moments][0].startswith("w2_")


def test_a_paid_sample_needs_a_run_plan(monkeypatch, tmp_path):
    monkeypatch.setattr(run, "OUT", tmp_path)
    # As in CI: no key anywhere. The plan is checked first, so the refusal is the plan's.
    monkeypatch.setattr(run, "_key", lambda: (_ for _ in ()).throw(SystemExit("OPENROUTER_API_KEY is not set")))
    monkeypatch.setattr(run, "from_environment", lambda default_file=None: NoPlan())
    monkeypatch.setattr(transport, "send", lambda *a, **k: pytest.fail("no request may leave without a plan"))
    with pytest.raises(RunPlanError):
        run.generate("default", "week1", 1)
    assert run.generate("default", "week1", 1, dry=True)["characters"] > 1000
    with pytest.raises(SystemExit, match="three samples"):
        main(["run", "--samples", "2"])


def test_a_saved_sample_is_reused_only_for_the_exact_same_request(monkeypatch, tmp_path):
    """E.B3: a sample saved under another knowledge base, prompt or model is never reported as this configuration's."""
    monkeypatch.setattr(run, "OUT", tmp_path)
    monkeypatch.setattr(transport, "send", lambda *a, **k: pytest.fail("no paid call in this test"))
    saved = tmp_path / "runs" / "default-week1-s1.json"
    saved.parent.mkdir(parents=True)
    saved.write_text(json.dumps({"request_fingerprint": "an older request", "output": {}}), encoding="utf-8")
    with pytest.raises(SystemExit, match="another request"):
        run.generate("default", "week1", 1)
    body, _ = run.request("default", "week1")
    current = canonical_hash({"benchmark": run.VERSION, "config": "default", "week": "week1", "sample": 1, "body": body})
    saved.write_text(json.dumps({"request_fingerprint": current, "output": {"angles": []}}), encoding="utf-8")
    assert run.generate("default", "week1", 1)["output"] == {"angles": []}


def test_a_failed_or_unreadable_paid_sample_is_settled_and_kept(monkeypatch, tmp_path):
    """E.B1: every reserved call is settled, whatever happens to the request; a paid answer that does not parse is
    saved for inspection instead of being lost."""
    monkeypatch.setattr(run, "OUT", tmp_path)
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    settled = []

    class Plan:
        def reserve(self, **kw):
            return "ticket"

        def settle(self, ticket, raw, *, status, error=None):
            settled.append((status, error))
    monkeypatch.setattr(run, "from_environment", lambda default_file=None: Plan())

    def down(*a, **k):
        raise httpx.ConnectError("connection reset")
    monkeypatch.setattr(transport, "send", down)
    with pytest.raises(httpx.ConnectError):
        run.generate("default", "week1", 1)
    assert settled[-1][0] == "failed" and "connection reset" in settled[-1][1]
    # A missing key after the reservation is settled too; nothing was sent.
    monkeypatch.setattr(run, "_key", lambda: (_ for _ in ()).throw(SystemExit("OPENROUTER_API_KEY is not set")))
    with pytest.raises(SystemExit, match="not set"):
        run.generate("default", "week1", 3)
    assert settled[-1][0] == "failed" and "not set" in settled[-1][1]
    monkeypatch.setattr(run, "_key", lambda: "test-key")

    garbled = {"choices": [{"message": {"content": "not json"}, "finish_reason": "stop"}], "usage": {"cost": 0.02}}
    monkeypatch.setattr(transport, "send", lambda *a, **k: httpx.Response(200, json=garbled, request=httpx.Request("POST", "https://x")))
    with pytest.raises(SystemExit, match="did not parse"):
        run.generate("default", "week1", 2)
    assert settled[-1][0] == "succeeded", "the call was paid for and is counted"
    saved = json.loads((tmp_path / "runs" / "default-week1-s2.json").read_text(encoding="utf-8"))
    assert saved["output"] is None and saved["raw_content"] == "not json"


def test_the_report_measures_each_sample_and_the_variance_across_them(monkeypatch, tmp_path):
    saved = json.loads((PROJECT_ROOT / "research" / "quality-experiments-2026-10-18" / "runs" / "V5-week1-gpt-6.1-sol.json").read_text(encoding="utf-8"))
    record = {"config": "strategist_v5", "week": "week1", "sample": 1, "cost": 0.1, "output": saved["output"]}
    metrics = run.sample_metrics("strategist_v5", "week1", record)
    assert metrics["public_cards"] == 3 and sum(metrics["pillars"].values()) == 3
    assert {"blocking_flags", "check_flags", "without_wia_contribution", "near_duplicate_title_pairs", "reframe_alignment"} <= set(metrics)
    assert 0 <= metrics["reframe_alignment"] <= 1
    # E.B3's card regression cases are reported on every sample (evaluation/regressions.py).
    assert set(metrics["regressions"]) == set(regressions.CARD_CASES) and all(v >= 0 for v in metrics["regressions"].values())
    other = {**metrics, "public_cards": 5, "titles": ["Something else entirely"], "cost": 0.2}
    summary = run.summarise([metrics, other])
    assert summary["public_cards"] == {"mean": 4, "stdev": 1.0, "values": [3, 5]} and summary["title_stability"] < 1
    assert set(summary["regressions"]) == set(regressions.CARD_CASES)
    assert run.CONFIGS["strategist_v5"]["profile"] == STRATEGIST_V5_PROFILE
