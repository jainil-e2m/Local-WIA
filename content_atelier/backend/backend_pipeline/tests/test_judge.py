"""E.B3's pairwise judge offline: rubric 2.3a as sent, recorded and reproducible order, the position-bias check, the
agreement maths, the calibration pairs, and no call without a run plan or in a dry run. Mocked provider only."""
from __future__ import annotations

import json
from types import SimpleNamespace

import httpx
import pytest

from backend_pipeline.gates import rubric
from backend_pipeline.llm import transport
from backend_pipeline.llm.run_plans import NoPlan, RunPlanError, write_file_plan
from evaluation import judge, run
from evaluation.__main__ import main
from evaluation.benchmark import build_labels

KB = SimpleNamespace(text="# Knowledge base\n\nWIA runs Google and Meta ads for wedding businesses.", version="kb-test", sha256="h")


def toy_pairs(n=4):
    """Pairs whose preferred side says GOOD: an honest judge can tell, a biased one cannot."""
    pairs = []
    for i in range(1, n + 1):
        bad = judge.Candidate(f"T{i}.draft", (("Text", f"BAD draft number {i} about tours"),), 1, "openai/chatgpt")
        good = judge.Candidate(f"T{i}.whitney", (("Text", f"GOOD version number {i} about tours"),), 2, "person")
        pairs.append(judge.Pair(f"T{i}", "export_pairs", "caption", bad, good, good.id, None, (f"label{i}",)))
    return pairs


def answer(preferred, a=3, b=3):
    content = {"A": dict.fromkeys(rubric.KEYS, a), "B": dict.fromkeys(rubric.KEYS, b), "preferred": preferred, "reason": "r"}
    return {"choices": [{"message": {"content": json.dumps(content)}, "finish_reason": "stop"}], "usage": {"cost": 0.01}}


def fake_send(decide, sent):
    def send(url, body, headers, *, timeout, client=None, before_send=None):
        sent.append(body)
        user = body["messages"][1]["content"]
        a_text = user.split("Candidate A", 1)[1].split("Candidate B", 1)[0]
        return httpx.Response(200, json=decide(a_text), request=httpx.Request("POST", url))
    return send


@pytest.fixture
def offline(monkeypatch, tmp_path):
    """A file run plan in a temporary folder, saved responses there too, and no key anywhere."""
    monkeypatch.setattr(judge, "RUNS", tmp_path / "runs")
    monkeypatch.setattr(run, "_key", lambda: "not-a-key")
    write_file_plan(tmp_path / "plan.json", purpose="test", stages=[judge.STAGE], models=[judge.JUDGE_MODEL],
                    input_set_hash="*", max_calls=100, max_cost_usd=5, approver="test@example.invalid")
    monkeypatch.setenv("ATELIER_RUN_PLAN_FILE", str(tmp_path / "plan.json"))
    return tmp_path


def test_the_rubric_sent_is_gates_rubric_text_and_the_judge_holds_no_copy():
    pair = toy_pairs(1)[0]
    body = judge.request(pair, 0, "REFERENCE")
    system, user = body["messages"][0]["content"], body["messages"][1]["content"]
    assert rubric.TEXT in system and system.index(rubric.TEXT) < system.index("REFERENCE")
    assert body["model"] == judge.JUDGE_MODEL == "anthropic/claude-sonnet-5.5"
    schema = body["response_format"]["json_schema"]["schema"]
    assert schema["properties"]["A"]["required"] == list(rubric.KEYS) == schema["properties"]["B"]["required"]
    assert schema["properties"]["A"]["properties"]["audience"]["enum"] == [1, 2, 3, 4, 5]
    source = open(judge.__file__, encoding="utf-8").read()
    assert not any(c.text in source for c in rubric.CRITERIA) and rubric.ANCHORS[3] not in source, "imported, never copied"
    # K45: the judge's own instructions share no eight-word run with any candidate prompt.
    assert judge.independence()["shared_runs"] == [] and judge.independence()["checked_files"] > 10
    assert "Candidate A" in user and user.index("BAD draft") < user.index("GOOD version"), "order 0 shows x as A"


def test_both_candidates_show_the_same_fields_and_a_labels_notes_are_never_sent():
    rich = judge.card_candidate("a", {"title": "One", "audience": "Venues", "offer_connection": "ELEVATE"})
    poor = judge.card_candidate("b", {"title": "Two", "audience": "Planners"})
    body = judge.request(judge.Pair("p", "dispositions", "content card", rich, poor, "a"), 0, "")
    user = body["messages"][1]["content"]
    assert "Offer connection" not in user and user.count("Title:") == 2 and user.count("Audience:") == 2
    pairs, _ = judge.pairs_from_labels(build_labels())
    why = {r["item_id"]: r["details"]["why"] for r in build_labels() if r["item_kind"] == "export_pair"}
    for pair in pairs[:38]:
        sent = json.dumps(judge.request(pair, 1, "")["messages"], ensure_ascii=False)
        assert why[pair.pair_id][:60] not in sent


def test_the_order_is_drawn_from_a_recorded_seed_and_reproduces(offline, monkeypatch):
    ids = [f"P{i:02d}" for i in range(1, 39)]
    draws = [judge.first_order(judge.DEFAULT_SEED, i) for i in ids]
    assert draws == [judge.first_order(judge.DEFAULT_SEED, i) for i in ids], "the same seed, the same orders"
    assert 0 < sum(draws) < len(draws), "both orders are drawn"
    assert draws != [judge.first_order(7, i) for i in ids], "another seed, other orders"
    monkeypatch.setattr(transport, "send", lambda *a, **k: pytest.fail("a dry run sends nothing"))
    first = judge.calibrate(toy_pairs(6), mode="dry", kb=KB)
    again = judge.calibrate(toy_pairs(6), mode="dry", kb=KB)
    assert first["input_set_hash"] == again["input_set_hash"] and first["judge"]["seed"] == judge.DEFAULT_SEED
    sent = []
    monkeypatch.setattr(transport, "send", fake_send(lambda a: answer("A" if "GOOD" in a else "B"), sent))
    result = judge.calibrate(toy_pairs(6), mode="paid", kb=KB)
    rows = result["comparisons"]
    assert len(rows) == 12 and all(r["seed"] == judge.DEFAULT_SEED for r in rows)
    for pair in toy_pairs(6):
        mine = [r for r in rows if r["pair_id"] == pair.pair_id]
        assert [r["order"] for r in mine] == [judge.first_order(judge.DEFAULT_SEED, pair.pair_id),
                                               1 - judge.first_order(judge.DEFAULT_SEED, pair.pair_id)]
        assert [r["first"] for r in mine] == [True, False]
    assert all(r["rubric_version"] == rubric.VERSION and r["rubric_text_sha256"] == rubric.TEXT_SHA256
               and r["judge_model"] == judge.JUDGE_MODEL and r["request_fingerprint"] for r in rows)
    single = judge.calibrate(toy_pairs(6), mode="replay", kb=KB, both_orders=False)
    assert [r["order"] for r in single["comparisons"]] == [judge.first_order(judge.DEFAULT_SEED, p.pair_id) for p in toy_pairs(6)]


def test_both_order_scoring_detects_a_judge_that_follows_the_position(offline, monkeypatch):
    sent = []
    monkeypatch.setattr(transport, "send", fake_send(lambda a: answer("A", 4, 2), sent))
    biased = judge.calibrate(toy_pairs(4), mode="paid", kb=KB)["groups"]["export_pairs"]
    assert biased["position_bias"]["flip_rate"] == 1.0 and biased["position_bias"]["chose_A"]["share"] == 1.0
    assert biased["judgements"]["share"] == 0.5 and biased["pairs_right_in_both_orders"]["agree"] == 0
    assert len(sent) == 8

    monkeypatch.setattr(judge, "RUNS", offline / "honest")
    monkeypatch.setattr(transport, "send", fake_send(lambda a: answer("A", 5, 2) if "GOOD" in a else answer("B", 2, 5), sent))
    honest = judge.calibrate(toy_pairs(4), mode="paid", kb=KB)
    group = honest["groups"]["export_pairs"]
    assert group["position_bias"]["flip_rate"] == 0.0 and group["pairs_right_in_both_orders"]["share"] == 1.0
    assert group["criterion_means"]["label_preferred"]["audience"] == 5 and group["criterion_means"]["other"]["audience"] == 2
    assert honest["prescreen"]["passes_first_test"] is None, "the bar is judged only on all 38 export pairs"
    assert honest["total_cost_usd"] == pytest.approx(0.08)

    # Replay: saved responses only, reused for the identical request; nothing is sent and nothing is paid.
    monkeypatch.setattr(transport, "send", lambda *a, **k: pytest.fail("replay sends nothing"))
    replayed = judge.calibrate(toy_pairs(4), mode="replay", kb=KB)
    assert replayed["groups"] == honest["groups"] and replayed["total_cost_usd"] == 0 and replayed["missing"] == 0
    assert judge.calibrate(toy_pairs(5), mode="replay", kb=KB)["missing"] == 2, "a pair never judged is missing, not called"


def test_the_agreement_maths_on_a_toy_label_set():
    assert judge.wilson(31, 38) == [0.6658, 0.9078] and judge.wilson(0, 5)[0] == 0.0 and judge.wilson(5, 5)[1] == 1.0
    assert judge.wilson(0, 0) is None
    assert judge.kendall_tau_b([1, 2, 3, 4], [1, 1, 2, 2]) == 0.8165 and judge.kendall_tau_b([3, 2, 1], [1, 2, 3]) == -1.0
    pairs = toy_pairs(3)

    def row(pair, order, side):
        a, b = judge.shown(pair, order)
        preferred = a.id if side == "A" else b.id
        return {"pair_id": pair.pair_id, "status": "judged", "A": a.id, "B": b.id, "preferred_side": side, "preferred": preferred,
                "label_preferred": pair.preferred, "agrees": preferred == pair.preferred,
                "ratings": {"A": dict.fromkeys(rubric.KEYS, 4 if a.id == pair.preferred else 2),
                            "B": dict.fromkeys(rubric.KEYS, 4 if b.id == pair.preferred else 2)},
                "overall": {"A": 4.0 if a.id == pair.preferred else 2.0, "B": 4.0 if b.id == pair.preferred else 2.0}}
    # T1 right in both orders; T2 follows the position (A both times); T3 wrong in both orders.
    rows = [row(pairs[0], 0, "B"), row(pairs[0], 1, "A"), row(pairs[1], 0, "A"), row(pairs[1], 1, "A"),
            row(pairs[2], 0, "A"), row(pairs[2], 1, "B")]
    group = judge.summarise(pairs, rows)["groups"]["export_pairs"]
    assert group["judgements"] == {"agree": 3, "of": 6, "share": 0.5, "ci95": judge.wilson(3, 6)}
    assert group["pairs_right_in_both_orders"]["agree"] == 1 and group["pairs_right_in_both_orders"]["of"] == 3
    assert group["position_bias"]["order_flips"] == 1 and group["position_bias"]["flip_rate"] == 0.3333
    # Ranks: one week, four candidates on two tiers, scored 2, 3, 4 and 4 against tiers 1, 1, 4 and 4.
    week = [judge.Pair(f"W{i}", "dispositions", "content card", judge.Candidate(f"c{i}", (("Title", "x"),), 1),
                       judge.Candidate(f"d{i}", (("Title", "y"),), 4), f"d{i}", "week_a") for i in range(2)]
    judged = [{"pair_id": p.pair_id, "A": p.x.id, "B": p.y.id, "overall": {"A": 2.0 + i, "B": 4.0}} for i, p in enumerate(week)]
    rank = judge.rank_agreement(week, judged)
    assert rank["weeks"]["week_a"]["candidates"] == 4 and rank["weeks"]["week_a"]["kendall_tau_b"] == 0.8944
    assert judge.rank_agreement(pairs, rows) is None, "export pairs have no week, so no ranking"


def test_the_calibration_pairs_come_from_wia_labels_and_the_export_pairs_never_a_delegated_one():
    pairs, excluded = judge.pairs_from_labels(build_labels())
    groups = [p.group for p in pairs]
    assert groups.count("export_pairs") == 38 and groups.count("week1_reframes") == 6 and "dispositions" not in groups
    assert excluded == {"chatgpt_review_week2": 1, "root_cause_2026-10-16": 6}
    assert all(p.preferred == p.y.id and p.y.generator == "person" for p in pairs)
    week1 = next(p for p in pairs if p.group == "week1_reframes")
    assert judge.shared_labels(week1.x, week1.y) == ["Title"], "the originals survive as titles"

    def gate(label_id, item, disposition, week="week_2026-06-29", source="gate", proxy=False, kept=None):
        return {"label_id": label_id, "item_kind": "angle", "item_id": item, "week_id": week, "disposition": disposition,
                "central_point_kept": kept, "source": source, "proxy": proxy, "details": {}}
    labels = [gate("l1", "a1", "skip"), gate("l1b", "a1", "develop"),  # the latest label decides
              gate("l2", "a2", "skip"), gate("l3", "a3", "internal"), gate("l4", "a4", "hold"),
              gate("l5", "a5", "reframe", kept=True), gate("l6", "a6", "skip", source="gate_delegated", proxy=True)]
    cards = {f"a{i}": {"week_id": "week_2026-06-29", "content_body": {"card": {"title": f"Card {i}", "audience": "Venues"}}}
             for i in range(1, 7)}
    pairs, excluded = judge.pairs_from_labels(labels, cards)
    assert excluded == {"gate_delegated": 1}, "R55: a delegated decision never calibrates the judge"
    assert sorted((p.preferred, p.x.id) for p in pairs) == [("a1", "a2"), ("a1", "a3"), ("a5", "a2"), ("a5", "a3")]
    assert {p.details["accepted"] + ">" + p.details["closed"] for p in pairs} == {"develop>skip", "develop>internal",
                                                                                  "reframe>skip", "reframe>internal"}
    with pytest.raises(ValueError, match="same family"):
        judge.check_family("openai/gpt-6.1-sol", pairs)


def test_the_context_never_carries_a_candidates_text():
    kb = SimpleNamespace(text="# KB\n\nWIA runs ads for wedding venues and planners across the country.\n\n"
                              "Whitney wrote: the couples you want to book are already searching for you right now today.",
                         version="v", sha256="h")
    text, record = judge.judge_context("kb", ["They are already searching for you right now today, she said"], kb=kb)
    assert "already searching" not in text and "WIA runs ads" in text
    assert record["knowledge_base_units_removed"] == 1 and record["candidate_runs_left"] == 0
    long = SimpleNamespace(text="\n".join(["A long voice guide line about weddings number %d." % i for i in range(60)]
                                          + ["the couples you want to book are already searching for you right now"]),
                           version="v", sha256="h")
    text, record = judge.judge_context("kb", ["you want to book are already searching for you right now"], kb=long)
    assert record["knowledge_base_units_removed"] == 1 and "number 59" in text, "a long paragraph loses only the line"
    assert judge.judge_context("none", ["x"])[0] == ""


def test_a_dry_run_counts_and_estimates_without_a_call(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(judge, "RUNS", tmp_path / "runs")
    monkeypatch.delenv("ATELIER_DATABASE_URL", raising=False)
    monkeypatch.setattr(transport, "send", lambda *a, **k: pytest.fail("a dry run sends nothing"))
    monkeypatch.setattr(judge, "from_environment", lambda **k: pytest.fail("a dry run needs no plan"))
    main(["judge-calibrate", "--dry", "--labels", "files"])
    result = json.loads(capsys.readouterr().out)
    assert result["dry"] and result["calls"] == 88 and result["to_call"] == 88
    assert result["labels"]["pairs"] == {"export_pairs": 38, "week1_reframes": 6, "dispositions": 0}
    assert 0 < result["estimated_cost_usd"]["with_prompt_cache"] < result["estimated_cost_usd"]["without_prompt_cache"]
    assert result["input_set_hash"] in result["plan_command"] and "--stage evaluation_judge" in result["plan_command"]
    assert result["judge"]["context"]["candidate_runs_left"] == 0 and not (tmp_path / "runs").exists()


def test_a_paid_run_without_a_plan_is_refused(monkeypatch, tmp_path):
    monkeypatch.setattr(judge, "RUNS", tmp_path / "runs")
    monkeypatch.setattr(run, "_key", lambda: pytest.fail("the plan is checked before any credential"))
    monkeypatch.setattr(judge, "from_environment", lambda **k: NoPlan())
    monkeypatch.setattr(transport, "send", lambda *a, **k: pytest.fail("no request may leave without a plan"))
    with pytest.raises(RunPlanError):
        judge.calibrate(toy_pairs(2), mode="paid", kb=KB)
    assert not (tmp_path / "runs").exists()
    with pytest.raises(ValueError, match="same family"):
        judge.calibrate(toy_pairs(2), mode="dry", kb=KB, model="openai/gpt-6.1-sol")


def test_a_reframe_that_drops_the_central_point_forms_no_pair_and_her_ratings_are_compared_never_sent(offline, monkeypatch):
    """Accepted is section 2.3's: developed, or reframed with the central point kept. Where the reviewer rated a card on
    rubric 2.3a (E.X3), the report gives the judge's distance from her ratings; the ratings themselves are never sent."""
    hers = {"version": rubric.VERSION, "criteria": dict.fromkeys(rubric.KEYS, 4)}
    old = {"version": "rubric-2.3a.v0", "criteria": dict.fromkeys(rubric.KEYS, 1)}

    def gate(label_id, item, disposition, kept=None, ratings=None):
        return {"label_id": label_id, "item_kind": "angle", "item_id": item, "week_id": "week_2026-06-29", "disposition": disposition,
                "central_point_kept": kept, "source": "gate", "proxy": False, "details": {}, "rubric_ratings": ratings}
    labels = [gate("l1", "a1", "develop", ratings=hers), gate("l2", "a2", "reframe", kept=False),
              gate("l3", "a3", "skip", ratings=old), gate("l4", "a4", "hold")]
    cards = {f"a{i}": {"week_id": "week_2026-06-29", "content_body": {"card": {"title": f"Card {i} GOOD" if i == 1 else f"Card {i}"}}}
             for i in range(1, 5)}
    pairs, _ = judge.pairs_from_labels(labels, cards)
    assert [(p.preferred, p.x.id) for p in pairs] == [("a1", "a3")], "a dropped central point and a hold form no pair"
    assert pairs[0].details["ratings"] == {"a1": hers["criteria"]}, "ratings on another rubric version are not compared"
    assert [c.tier for c in (pairs[0].x, pairs[0].y)] == [1, judge.ACCEPTED_TIER]
    sent = []
    monkeypatch.setattr(transport, "send", fake_send(lambda a: answer("A", 5, 2) if "GOOD" in a else answer("B", 2, 5), sent))
    group = judge.calibrate(pairs, mode="paid", kb=KB)["groups"]["dispositions"]
    assert all('"wia_is_the_subject": 4' not in json.dumps(b) for b in sent)
    assert group["rubric_ratings"] == {"rated_cards": 1, "mean_absolute_difference": dict.fromkeys(rubric.KEYS, 1),
                                       "overall_mean_absolute_difference": 1}
    assert group["by_disposition"]["develop_over_skip"]["share"] == 1.0


def saved_samples(root, name, cards_by_sample, model="openai/gpt-6.1-sol"):
    (root / "runs").mkdir(parents=True, exist_ok=True)
    config, _, version = name.partition("@")
    for (week, s), cards in cards_by_sample.items():
        path = root / "runs" / f"{config}-{week}-s{s}{'.' + version if version else ''}.json"
        path.write_text(json.dumps({"model": model, "output": {"cards": cards}}), encoding="utf-8")


def slate(tag, n, reference=False):
    return [{"title": f"{tag} card {i}", "pillar": "WARM", "audience": "Venues", "core_perspective": f"{tag} view {i}",
             "evidence_points": [f"[w1_m{i}] {tag} said something" if reference else f"{tag} said something"]}
            for i in range(1, n + 1)]


def test_two_configurations_are_compared_slate_against_slate_in_one_plain_format(offline, monkeypatch):
    """The evaluation command's pairwise judge: each week's sample s of one configuration against sample s of the
    other, in one plain format (moment references removed), in both orders from the seed; the report gives each
    configuration's share of judgements, pairs won in both orders, mean rubric scores and the order flips."""
    monkeypatch.setattr(run, "OUT", offline)
    monkeypatch.setattr(run, "cards_of", lambda config, week, output: (output["cards"], []))
    saved_samples(offline, "default", {(w, s): slate("BAD", 5, reference=True) for w in ("week1", "week2") for s in (1, 2, 3)},
                  model="openai/gpt-6-luna")
    saved_samples(offline, "strategist_v5@kb-v5", {(w, s): slate("GOOD", 3) for w in ("week1", "week2") for s in (1, 2)})
    names = ["default", "strategist_v5@kb-v5"]
    pairs, missing = judge.config_pairs(names, ["week1", "week2"], 3)
    assert len(pairs) == 4 and missing == ["strategist_v5@kb-v5 week1 s3", "strategist_v5@kb-v5 week2 s3"]
    assert all(p.preferred is None and p.group == judge.CONFIG_GROUP for p in pairs)
    user = judge.request(pairs[0], 0, "")["messages"][1]["content"]
    assert "[w1_m" not in user and "Evidence: - BAD said something" in user and "Evidence: - GOOD said something" in user
    assert "default" not in user and "strategist" not in user and "gpt" not in user, "nothing names the configuration"
    with pytest.raises(ValueError, match="two different"):
        judge.config_pairs(["default", "default"], ["week1"], 1)
    with pytest.raises(ValueError, match="Unknown configuration"):
        judge.config_pairs(["default", "nope"], ["week1"], 1)

    monkeypatch.setattr(transport, "send", lambda *a, **k: pytest.fail("a dry run sends nothing"))
    dry = judge.compare_configs(names, ["week1", "week2"], 2, mode="dry", kb=KB)
    assert dry["calls"] == 8 and dry["configurations"]["missing_samples"] == [] and "--max-calls 8" in dry["plan_command"]
    # With a sample still to generate, the dry run says what is missing and plans nothing: the plan binds the slates.
    waiting = judge.compare_configs(names, ["week1", "week2"], 3, mode="dry", kb=KB)
    assert waiting["plan_command"] is None and waiting["configurations"]["missing_samples"] == missing
    assert waiting["configurations"]["calls_once_saved"] == 12

    sent = []
    monkeypatch.setattr(transport, "send", fake_send(lambda a: answer("A", 4, 2) if "GOOD" in a else answer("B", 2, 4), sent))
    result = judge.compare_configs(names, ["week1", "week2"], 3, mode="paid", kb=KB)
    assert len(sent) == 8 and {r["order"] for r in result["comparisons"]} == {0, 1}
    good, bad = result["configs"]["strategist_v5@kb-v5"], result["configs"]["default"]
    assert good["preferred"]["share"] == 1.0 and good["pairs_won_in_both_orders"] == 4 and bad["preferred"]["agree"] == 0
    assert good["mean_overall"] == 4 and bad["criterion_means"]["audience"] == 2
    assert result["by_week"]["week1"] == {"default": 0, "strategist_v5@kb-v5": 4, "judgements": 4}
    assert result["position_bias"]["order_flips"] == 0 and result["total_cost_usd"] == pytest.approx(0.08)
    assert all(r["agrees"] is None and r["rubric_version"] == rubric.VERSION for r in result["comparisons"])
    monkeypatch.setattr(transport, "send", lambda *a, **k: pytest.fail("replay sends nothing"))
    assert judge.compare_configs(names, ["week1", "week2"], 3, mode="replay", kb=KB)["configs"] == result["configs"]
    with pytest.raises(ValueError, match="No sample index"):
        judge.compare_configs(["default", "strategist_v4"], ["week1"], 1, mode="replay", kb=KB)


def test_judge_compare_on_the_command_line_counts_without_a_call(offline, monkeypatch, capsys):
    monkeypatch.setattr(run, "OUT", offline)
    monkeypatch.setattr(run, "cards_of", lambda config, week, output: (output["cards"], []))
    monkeypatch.setattr(judge, "knowledge", lambda: KB)
    saved_samples(offline, "default", {("week1", 1): slate("BAD", 2)}, model="openai/gpt-6-luna")
    saved_samples(offline, "strategist_v5", {("week1", 1): slate("GOOD", 2)})
    monkeypatch.setattr(transport, "send", lambda *a, **k: pytest.fail("a dry run sends nothing"))
    main(["judge-compare", "--configs", "default,strategist_v5", "--weeks", "week1", "--samples", "1", "--dry"])
    result = json.loads(capsys.readouterr().out)
    assert result["calls"] == 2 and result["configurations"]["pairs"] == 1 and result["judge"]["seed"] == judge.DEFAULT_SEED
