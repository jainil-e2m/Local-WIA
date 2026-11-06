"""The Phase 1 commands, run the way an operator runs them: storage_cli documents|people|clients|glossary ... on a real database."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from test_documents_db import CLIENT_CALL, INTERNAL_CALL, run_jobs
from test_documents_pipeline_db import drop

from backend_pipeline import storage_cli
from backend_pipeline.storage_config import StorageSettings
from backend_pipeline.tests.platform_db import platform_setup, platform_url  # noqa: F401 (fixtures)

KB = Path(__file__).resolve().parents[2] / "knowledge_base"


@pytest.fixture
def cli(platform_setup, monkeypatch, capsys):  # noqa: F811
    repo, models, tmp_path = platform_setup
    monkeypatch.setattr(StorageSettings, "from_env", classmethod(lambda cls: repo.settings))
    monkeypatch.setattr(type(models), "from_env", classmethod(lambda cls: models.model_copy(update={"knowledge_base_root": KB})))

    def run(*argv):
        capsys.readouterr()
        storage_cli.main(list(argv))
        return json.loads(capsys.readouterr().out)
    return run, repo, models, tmp_path


def test_the_whole_preparation_runs_from_the_command_line(cli):
    run, repo, models, tmp_path = cli
    assert run("people", "sync")["created"] >= 11 and run("people", "check")["agree"] is True
    clients = tmp_path / "clients.csv"
    clients.write_text("name,aliases\nDana's Barn,Dana Lee\n", encoding="utf-8")
    assert run("clients", "import", "--file", str(clients)) == {"created": 1, "updated": 0, "unchanged": 0}
    assert run("glossary", "add", "LeadLock", "--kind", "product", "--variant", "Lead Lock")["term_id"]
    folder = drop(tmp_path, "calls", {"GMT20260312-153000_Recording Review with Dana Lee.vtt": CLIENT_CALL, "Check-in with Gisselle.vtt": INTERNAL_CALL,
                                      "Undated review with Dana Lee.vtt": CLIENT_CALL.replace("Welcome Dana", "Welcome Dana again")})
    imported = run("documents", "import", str(folder))
    assert imported["new"] == 3 and run("documents", "import", str(folder))["new"] == 0
    run_jobs(repo, models)
    report = run("documents", "report")
    assert report["by_call_type"]["client_1to1"] == 2 and report["by_call_type"]["internal"] == 1
    assert report["dates"]["unknown"] == 1 and report["extraction"]["pending"] >= 2
    with repo.connection() as conn:
        client = conn.execute("SELECT client_id FROM transcripts WHERE title LIKE 'GMT2026%%'").fetchone()
    assert client["client_id"], "the call is tied to the client named in its title"


def test_dates_are_applied_from_a_zoom_listing_and_only_when_asked(cli, tmp_path):
    run, repo, models, _ = cli[0], cli[1], cli[2], cli[3]
    folder = drop(cli[3], "undated", {"Carmen Cruickshank's Personal Meeting Room's transcript (4).vtt": CLIENT_CALL})
    run("people", "sync")
    run("documents", "import", str(folder))
    run_jobs(repo, models)
    listing = cli[3] / "zoom.csv"
    listing.write_text("Topic,Start Time,Duration (Minutes)\nCarmen Cruickshank's Personal Meeting Room,03/12/2026 03:30:00 PM,0.1\n", encoding="utf-8")
    preview = run("documents", "dates", "--zoom-listing", str(listing), "--zoom-timezone", "America/Chicago")
    assert preview["applied"] is False and preview["dated"] == 1 and preview["changes"][0]["source"] == "zoom_listing"
    with repo.connection() as conn:
        assert conn.execute("SELECT occurred_at FROM transcripts WHERE title LIKE 'Carmen%%'").fetchone()["occurred_at"] is None
    applied = run("documents", "dates", "--zoom-listing", str(listing), "--zoom-timezone", "America/Chicago", "--apply")
    assert applied["report"]["by_source"]["zoom_listing"] == 1
    with repo.connection() as conn:
        row = conn.execute("SELECT occurred_at,occurred_at_source FROM transcripts WHERE title LIKE 'Carmen%%'").fetchone()
    assert row["occurred_at_source"] == "zoom_listing" and row["occurred_at"].isoformat().startswith("2026-03-12T20:30")
    with pytest.raises(SystemExit):
        run("documents", "dates", "--zoom-listing", str(listing))


def test_a_listing_date_survives_normalising_again_and_the_chunk_headers_carry_it(cli):
    # The runbook dates the Zoom calls from WIA's recording list after the first normalisation, then embeds; the roster or the
    # client list changing later means `documents normalise --all`. Neither may lose the evidence or leave "Date: unknown".
    from backend_pipeline.documents.jobs import normalise
    run, repo, models, tmp_path = cli
    folder = drop(tmp_path, "undated2", {"Carmen Cruickshank's Personal Meeting Room's transcript (5).vtt": CLIENT_CALL})
    run("people", "sync")
    run("documents", "import", str(folder))
    run_jobs(repo, models)
    listing = tmp_path / "zoom2.csv"
    listing.write_text("Topic,Start Time,Duration (Minutes)\nCarmen Cruickshank's Personal Meeting Room,03/12/2026 03:30:00 PM,0.1\n", encoding="utf-8")
    run("documents", "dates", "--zoom-listing", str(listing), "--zoom-timezone", "America/Chicago", "--apply")
    with repo.connection() as conn:
        doc = conn.execute("SELECT * FROM transcripts WHERE title LIKE 'Carmen%%'").fetchone()
        headers = [r["header"] for r in conn.execute("SELECT header FROM transcript_chunks WHERE transcript_id=%s AND is_current",
                                                      (doc["transcript_id"],))]
    assert doc["occurred_at_source"] == "zoom_listing"
    assert headers and all("Date: 2026-03-12" in h for h in headers), "the headers the re-embedding will embed carry the date"
    normalise(repo, doc["transcript_id"], models=models)
    run("documents", "normalise", "--all", "--now")
    with repo.connection() as conn:
        again = conn.execute("SELECT occurred_at,occurred_at_source FROM transcripts WHERE transcript_id=%s", (doc["transcript_id"],)).fetchone()
        current = [r["header"] for r in conn.execute("SELECT header FROM transcript_chunks WHERE transcript_id=%s AND is_current",
                                                      (doc["transcript_id"],))]
    assert (again["occurred_at"], again["occurred_at_source"]) == (doc["occurred_at"], "zoom_listing"), "evidence is never forgotten"
    assert current == headers, "normalising again changes no chunk, so nothing is embedded twice"


def test_the_classification_calls_are_estimated_before_any_is_made(cli, monkeypatch):
    # The paid classification call (1.B4) is estimated first, like the re-embedding: how many documents the rules cannot
    # place, and the tokens, with nothing queued and nothing sent.
    run, repo, models, tmp_path = cli
    monkeypatch.setattr(type(models), "from_env", classmethod(lambda cls: models.model_copy(
        update={"knowledge_base_root": KB, "openrouter_document_classification_model": "fast/model"})))
    run("people", "sync")
    folder = drop(tmp_path, "estimate", {"Carmen Cruickshank's Personal Meeting Room's transcript (8).vtt": CLIENT_CALL,
                                         "Check-in with Gisselle.vtt": INTERNAL_CALL})
    ids = run("documents", "import", str(folder))["transcript_ids"]
    with repo.connection() as conn:
        jobs_before = conn.execute("SELECT count(*) n FROM pipeline_jobs").fetchone()["n"]
        ambiguous = conn.execute("SELECT transcript_id FROM transcripts WHERE title LIKE 'Carmen%%(8).vtt'").fetchone()["transcript_id"]
    estimate = run("documents", "normalise", "--estimate", "--ids", *ids)
    assert (estimate["documents"], estimate["model_calls"], estimate["model"]) == (2, 1, "fast/model")
    assert estimate["documents_to_ask_about"] == [ambiguous] and estimate["estimated_input_tokens"] > 0
    with repo.connection() as conn:
        assert conn.execute("SELECT count(*) n FROM pipeline_jobs").fetchone()["n"] == jobs_before, "an estimate queues nothing"
    run("documents", "classify", ambiguous, "--call-type", "client_1to1", "--reason", "Dana is a member", "--actor", "whitney@example.invalid")
    assert run("documents", "normalise", "--estimate", "--ids", ambiguous)["model_calls"] == 0, "a person's decision costs nothing"


def test_an_inline_normalise_asks_the_configured_model_like_the_job(cli, monkeypatch):
    """`documents normalise --now` never gave the classifier a provider, so a configured model was silently skipped and
    every ambiguous call waited for a person (found on the real backfill, 19 October)."""
    from dataclasses import replace

    from backend_pipeline import llm
    from backend_pipeline.normalise import classify
    run, repo, models, tmp_path = cli
    monkeypatch.setattr(type(models), "from_env", classmethod(lambda cls: models.model_copy(
        update={"knowledge_base_root": KB, "openrouter_document_classification_model": "fast/model"})))
    from backend_pipeline.storage_config import StorageSettings
    live = repo.settings.model_copy(update={"synthetic": False})
    monkeypatch.setattr(StorageSettings, "from_env", classmethod(lambda cls: live))
    sentinel, asked = object(), []
    monkeypatch.setattr(llm, "live_provider", lambda *a, **k: sentinel)
    real = classify.by_rules

    def by_model(document, mapping, provider, model, runs=None):
        asked.append((provider, model))
        return replace(real(document, {}), call_type="client_1to1", method="model", needs_review=False, reason="model said so")
    monkeypatch.setattr(classify, "by_model", by_model)
    run("people", "sync")
    folder = drop(tmp_path, "inline", {"Carmen Cruickshank's Personal Meeting Room's transcript (9).vtt": CLIENT_CALL})
    (doc_id,) = run("documents", "import", str(folder))["transcript_ids"]
    (done,) = run("documents", "normalise", "--now", "--ids", doc_id)["normalised"]
    assert asked == [(sentinel, "fast/model")] and done["method"] == "model"


def test_a_persons_exclusion_records_the_persons_reason(cli):
    """Filing a call as `other` stored the rules' "Not placed: ... a person decides" although a person had decided (the
    real backfill's non-wedding calls, 19 October); the person's reason is the exclusion reason."""
    run, repo, models, tmp_path = cli
    run("people", "sync")
    folder = drop(tmp_path, "other", {"Carmen Cruickshank's Zoom Meeting's transcript (4).vtt": CLIENT_CALL})
    (doc_id,) = run("documents", "import", str(folder))["transcript_ids"]
    reason = "A client of another business, not a wedding pro"
    done = run("documents", "classify", doc_id, "--call-type", "other", "--reason", reason, "--actor", "whitney@example.invalid")
    assert done["included"] is False and done["exclusion_reason"] == reason


def test_a_person_classifies_and_a_selection_is_previewed_then_queued(cli):
    run, repo, models, tmp_path = cli
    run("people", "sync")
    folder = drop(tmp_path, "calls2", {"GMT20260312-153000_Recording Check-in with Gisselle.vtt": INTERNAL_CALL})
    run("documents", "import", str(folder))
    run_jobs(repo, models)
    with repo.connection() as conn:
        transcript_id = conn.execute("SELECT transcript_id FROM transcripts WHERE title LIKE 'GMT2026%%'").fetchone()["transcript_id"]
    assert run("documents", "select", "--from", "2026-03-09T00:00:00+00:00", "--to", "2026-03-16T00:00:00+00:00", "--dry-run")["selected"] == []
    done = run("documents", "classify", transcript_id, "--call-type", "client_1to1", "--reason", "Whitney: it was a client check-in", "--actor", "whitney@example.invalid")
    assert done["included"] is True and done["classification"]["method"] == "person"
    preview = run("documents", "select", "--from", "2026-03-09T00:00:00+00:00", "--to", "2026-03-16T00:00:00+00:00", "--dry-run")
    assert [d["transcript_id"] for d in preview["selected"]] == [transcript_id]
    queued = run("documents", "select", "--from", "2026-03-09T00:00:00+00:00", "--mode", "synthetic")
    assert queued["selected_by"] == "window" and queued["documents"] == [transcript_id]
    with pytest.raises(SystemExit):
        run("documents", "select", "--from", "2026-03-09T00:00:00")


def test_reembed_states_its_cost_before_it_queues_and_the_index_agreement_names_disagreements(cli):
    run, repo, models, tmp_path = cli
    run("people", "sync")
    folder = drop(tmp_path, "calls3", {"Review with Dana Lee.vtt": CLIENT_CALL, "Check-in with Gisselle.vtt": INTERNAL_CALL})
    run("documents", "import", str(folder))
    run_jobs(repo, models)
    estimate = run("documents", "reembed", "--estimate")
    assert estimate["chunks"] >= 1 and estimate["estimated_cost_usd"] < 0.01
    assert run("documents", "reembed")["chunks"] == estimate["chunks"]
    with repo.connection() as conn:
        rows = conn.execute("SELECT title,content_hash FROM transcripts WHERE week_id IS NULL").fetchall()
    index = tmp_path / "transcripts.json"
    index.write_text(json.dumps([{"contentHash": r["content_hash"][:16], "kind": "client" if r["title"].startswith("Review") else "client"}
                                 for r in rows]), encoding="utf-8")
    result = run("documents", "agreement", str(index))
    assert result["compared"] == 2 and result["agree"] == 1
    assert [d["ours"] for d in result["disagreements"]] == ["internal"] and result["disagreements"][0]["index"] == "client"
