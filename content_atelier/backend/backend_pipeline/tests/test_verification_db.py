"""E.B10 on the product path (PostgreSQL): each card is saved with its ledger, a blocking flag stops develop until it
is checked and explained, an edit rebuilds the ledger, and a configured verifier's model pass is recorded.
Synthetic fixtures and fake providers only."""
from __future__ import annotations

import json

import pytest

from backend_pipeline import gate_one
from backend_pipeline.cycle.verification import REFRAME_PROFILE, blocking, criterion_one_failures
from backend_pipeline.tests.test_cards_sql import DECIDE, W1, CardSQLProvider, cards_setup, ranked  # noqa: F401 (fixture)
from backend_pipeline.tests.test_sql_storage import URL, drain, setup  # noqa: F401 (fixture)
from backend_pipeline.tests.test_strategist_profile import card

pytestmark = pytest.mark.skipif(not URL, reason="Requires isolated atelier_test")


class OverclaimProvider(CardSQLProvider):
    """Rank 1 states a figure the call never gave; rank 2 is clean. The verifier, when asked, adds a critic view.

    No roster member speaks in the synthetic call, so every card fails criterion 1 and gets the critic's reframe call;
    this provider's reframe keeps the card's framing, so the attempt is recorded and the card stays as generated."""

    reframe_wia = None

    def json_call(self, *, stage, system, user, schema, fingerprint):
        if stage == "card_verification" and "cards" not in schema["required"]:
            self.calls.append("card_reframe")
            current = json.loads(user.split("Card to reframe:\n", 1)[1])
            return {**{k: current[k] for k in ("title", "core_perspective", "why_it_matters")},
                    "wia_in_action": self.reframe_wia or current["wia_in_action"], "reason": "Reframed."}, {"fake": True}
        if stage == "card_verification":
            self.calls.append(stage)
            return {"cards": [{"rank": r, "bindings": [], "qualifiers": ["The follow-up change was reported, not measured."],
                               "flags": [], "critic": {"wia_is_the_subject": "pass", "worth_attention": "pass", "reason": "Shows the WIA move."}}
                              for r in (1, 2)]}, {"fake": True}
        if stage != "angle_generation":
            return super().json_call(stage=stage, system=system, user=user, schema=schema, fingerprint=fingerprint)
        self.calls.append(stage)
        return {"week_summary": "One call.", "internal_insights": [], "considered_not_selected": [],
                "angles": [card("S1", 1, core_perspective="Leads rose 45% once follow-up changed, idea 1."), card("S1", 2)]}, {"fake": True}


def run(cards_setup, provider=None, **settings):  # noqa: F811
    repo, models, _, _ = cards_setup
    from backend_pipeline.sql_pipeline import SQLWorker
    models = models.model_copy(update=settings)
    provider = provider or OverclaimProvider()
    repo.settings.brief_enabled = False
    repo.submit(W1, "synthetic", models=models)
    drain(SQLWorker(repo.settings, models, provider=provider))
    return repo, provider, ranked(repo.review(W1, "tester"))


def test_a_blocking_ledger_flag_stops_develop_until_it_is_checked_and_explained(cards_setup):  # noqa: F811
    repo, provider, (first, second) = run(cards_setup)
    assert "card_verification" not in provider.calls, "no model pass without a verification model"
    # The run records the context the verifier used (L.B5), beside the strategist's.
    with repo.connection() as conn:
        refs = conn.execute("SELECT result_refs FROM pipeline_jobs WHERE stage='angle_generation' AND status='completed'").fetchone()["result_refs"]
    assert refs["verifier_knowledge_base"]["version"] and refs["verifier_knowledge_base"]["documents"]
    ledger = first["content_body"]["ledger"]
    flags = blocking(ledger)
    assert [f["kind"] for f in flags] == ["number"] and ledger["readiness"] == "research_required"
    assert not blocking(second["content_body"]["ledger"]) and second["content_body"]["ledger"]["model_pass"] == "not_run"
    acks = first["content_body"]["card"]["verify_before_publishing"]
    with pytest.raises(ValueError, match="Resolve every blocking ledger flag"):
        gate_one.decide(repo, first["angle_id"], first["content_hash"], "approved", DECIDE, False, None, "tester", verified=acks)
    with pytest.raises(ValueError, match="needs a note"):
        gate_one.decide(repo, first["angle_id"], first["content_hash"], "approved", DECIDE, False, None, "tester",
                        verified=acks + [flags[0]["id"]])
    approved = gate_one.decide(repo, first["angle_id"], first["content_hash"], "approved", DECIDE, False,
                               "Checked the call: the 45% is in the client's report.", "tester", verified=acks + [flags[0]["id"]])
    assert approved["approval_status"] == "approved"
    with repo.connection() as conn:
        row = conn.execute("SELECT matching_result FROM content_angles WHERE angle_id=%s", (first["angle_id"],)).fetchone()
    assert row["matching_result"]["ledger_flags_acknowledged"] == [flags[0]["id"]]


def test_an_edit_rebuilds_the_ledger_and_a_configured_verifier_adds_its_pass(cards_setup):  # noqa: F811
    repo, provider, (first, _) = run(cards_setup, openrouter_verification_model="anthropic/claude-sonnet-5.5")
    assert provider.calls.count("card_verification") == 1, "one verification call per week"
    ledger = first["content_body"]["ledger"]
    assert ledger["model_pass"] == "anthropic/claude-sonnet-5.5" and ledger["critic"]["reason"] == "Shows the WIA move."
    assert ledger["qualifiers"] == ["The follow-up change was reported, not measured."]
    edited = gate_one.edit(repo, first["angle_id"], first["content_hash"], {"core_perspective": "Follow-up shapes lead quality."}, "editor")
    new = next(a for a in repo.review(W1, "tester")["angles"] if a["angle_id"] == edited["angle_id"])
    assert not blocking(new["content_body"]["ledger"]), "the unsupported figure is gone from the new version"
    # No later cycle re-runs the model pass on this card: its findings on untouched text stay, the edited text is marked.
    assert new["content_body"]["ledger"]["model_pass"] == "anthropic/claude-sonnet-5.5"
    assert [f["text"] for f in new["content_body"]["ledger"]["flags"] if f["kind"] == "edited_after_model_check"] == ["core_perspective"]
    assert provider.calls.count("card_reframe") == 2, "one reframe call per card failing criterion 1"
    assert ledger["critic"]["repair"]["result"] == "still_failing" and criterion_one_failures(ledger)


def test_the_critics_reframe_repairs_a_card_on_the_product_path(cards_setup):  # noqa: F811
    provider = OverclaimProvider()
    provider.reframe_wia = "WIA view (knowledge base): WIA reviews the follow-up before it changes the ads."
    repo, provider, cards = run(cards_setup, provider, openrouter_verification_model="anthropic/claude-sonnet-5.5")
    assert provider.calls.count("card_verification") == 1 and provider.calls.count("card_reframe") == 2
    review = repo.review(W1, "tester")
    ranking = [r["current_angle_id"] for r in review["selection"]["ranking"]]
    assert ranking == [c["angle_id"] for c in cards], "the week's ranking names the repaired cards that were saved"
    for saved in cards:
        ledger = saved["content_body"]["ledger"]
        assert saved["content_body"]["card"]["wia_in_action"] == provider.reframe_wia
        assert not criterion_one_failures(ledger) and ledger["critic"]["reason"] == "Shows the WIA move."
        repair = ledger["critic"]["repair"]
        assert repair["result"] == "repaired" and repair["prompt_version"] == REFRAME_PROFILE
        assert repair["after"]["wia_in_action"] == provider.reframe_wia and repair["before"]["wia_in_action"] != provider.reframe_wia
    assert [f["kind"] for f in blocking(cards[0]["content_body"]["ledger"])] == ["number"], "a reframe never clears a fact flag"


def test_a_verifier_from_the_strategists_family_is_refused(cards_setup):  # noqa: F811
    repo, models, _, _ = cards_setup
    from backend_pipeline.sql_pipeline import SQLWorker
    models = models.model_copy(update={"openrouter_verification_model": models.model_for("angle_generation")})
    repo.submit(W1, "synthetic", models=models)
    drain(SQLWorker(repo.settings, models, provider=OverclaimProvider()))
    jobs = repo.review(W1, "tester")["jobs"]
    failed = next(j for j in jobs if j["stage"] == "angle_generation")
    assert failed["status"] != "completed" and "different family" in (failed["error_summary"] or "")


class MisattributionProvider(OverclaimProvider):
    """The model pass blocks rank 2 for a misattribution in why_it_matters; rank 2 has a point no rule can bind."""

    def json_call(self, *, stage, system, user, schema, fingerprint):
        if stage == "card_verification" and "cards" in schema["required"]:
            output, meta = super().json_call(stage=stage, system=system, user=user, schema=schema, fingerprint=fingerprint)
            output["cards"][1]["flags"] = [{"kind": "misattribution", "severity": "block", "field": "why_it_matters",
                                            "text": "Owners stop blaming the platform.", "message": "The client said this, not WIA."}]
            output["cards"][1]["bindings"] = [{"point_index": 1, "scene_refs": ["S1"], "status": "unsupported"}]
            return output, meta
        output, meta = super().json_call(stage=stage, system=system, user=user, schema=schema, fingerprint=fingerprint)
        if stage == "angle_generation":
            output["angles"][1]["evidence_points"] = ["The strategist asks about pricing.",
                                                       "She checks what couples see first on every account she runs."]
        return output, meta


class UnavailableVerifier(MisattributionProvider):
    def json_call(self, *, stage, system, user, schema, fingerprint):
        if stage == "card_verification":
            raise ValueError("Provider returned no JSON content")
        return super().json_call(stage=stage, system=system, user=user, schema=schema, fingerprint=fingerprint)


def test_an_edit_keeps_what_the_model_pass_found_in_the_text_it_did_not_change(cards_setup):  # noqa: F811
    """E.B10 with E.B16 (c): an edit rebuilds the deterministic ledger, but no later cycle re-runs the model pass on
    that card, so an edit to one field must not drop a model finding on another, or the model's binding of an
    unchanged evidence point. The text the edit did change is marked as checked by rule only."""
    repo, _, (_, second) = run(cards_setup, MisattributionProvider(), openrouter_verification_model="anthropic/claude-sonnet-5.5")
    ledger = second["content_body"]["ledger"]
    assert [f["kind"] for f in blocking(ledger)] == ["misattribution"]
    assert any(f["kind"] == "unsupported_point" for f in ledger["flags"])
    edited = gate_one.edit(repo, second["angle_id"], second["content_hash"], {"title": "Why we read the pricing copy first"}, "editor")
    new = next(a for a in repo.review(W1, "tester")["angles"] if a["angle_id"] == edited["angle_id"])["content_body"]["ledger"]
    assert [f["kind"] for f in blocking(new)] == ["misattribution"], "the untouched field's finding still blocks"
    assert new["model_pass"] == "anthropic/claude-sonnet-5.5" and new["bindings"][1]["status"] == "unsupported"
    assert any(f["kind"] == "unsupported_point" for f in new["flags"])
    assert any(f["kind"] == "edited_after_model_check" and "title" in f["text"] for f in new["flags"])
    assert new == __import__("backend_pipeline.cycle.verification", fromlist=["finish"]).finish(new)
    # Rewriting the flagged field itself replaces the finding with the rule check of the new text.
    again = gate_one.edit(repo, edited["angle_id"], edited["content_hash"], {"why_it_matters": "Owners see where lead quality is set."},
                          "editor")
    latest = next(a for a in repo.review(W1, "tester")["angles"] if a["angle_id"] == again["angle_id"])["content_body"]["ledger"]
    assert not blocking(latest) and any(f["kind"] == "edited_after_model_check" for f in latest["flags"])


def test_an_edit_keeps_the_points_an_unavailable_model_pass_left_to_check(cards_setup):  # noqa: F811
    """Plan 4.11: with the model pass unavailable each point it would have checked is a blocking flag; an edit to the
    title must not clear them."""
    repo, _, (_, second) = run(cards_setup, UnavailableVerifier(), openrouter_verification_model="anthropic/claude-sonnet-5.5")
    ledger = second["content_body"]["ledger"]
    assert ledger["model_pass"] == "unavailable" and {f["kind"] for f in blocking(ledger)} == {"unchecked_point"}
    edited = gate_one.edit(repo, second["angle_id"], second["content_hash"], {"title": "Why we read the pricing copy first"}, "editor")
    new = next(a for a in repo.review(W1, "tester")["angles"] if a["angle_id"] == edited["angle_id"])["content_body"]["ledger"]
    assert new["model_pass"] == "unavailable"
    assert sorted(f["id"] for f in blocking(new)) == sorted(f["id"] for f in blocking(ledger)), "the same points still to check"
