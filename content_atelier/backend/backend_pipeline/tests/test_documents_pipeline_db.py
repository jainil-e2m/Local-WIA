"""Phase 1 pipeline connection on a real database: selection by window or set (1.B13), the planned re-embedding (1.B6),
the Slack export (1.B7), the documents API (1.B8), the model-assisted classification path and live Fathom duplicates (1.B10).

Synthetic transcripts, an offline provider and a mock embedding transport. No network."""
from __future__ import annotations

import json
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from test_documents_db import CLIENT_CALL, FILLER, FRAGMENT, INTERNAL_CALL, WORKSHOP, run_jobs, vtt  # noqa: F401

from backend_pipeline import reference
from backend_pipeline.documents import duplicates, intake, reembed, select, slack_export
from backend_pipeline.documents.jobs import normalise
from backend_pipeline.storage_api import router
from backend_pipeline.tests.platform_db import APPROVER, EDITOR, platform_setup, platform_url  # noqa: F401 (fixtures)

KB = Path(__file__).resolve().parents[2] / "knowledge_base"
UTC_ = UTC


@pytest.fixture
def ready(platform_setup):  # noqa: F811
    repo, models, tmp_path = platform_setup
    with repo.connection() as conn:
        reference.sync_roster(conn, KB, date(2026, 10, 18))
    return repo, models, tmp_path


def drop(tmp_path, name, files):
    root = tmp_path / name
    root.mkdir()
    for filename, text in files.items():
        (root / filename).write_text(text, encoding="utf-8")
    return root


def imported(ready):
    repo, models, tmp_path = ready
    root = drop(tmp_path, "drop", {
        "GMT20260312-153000_Recording Carmen Cruickshank's Personal Meeting Room's transcript (3).vtt": CLIENT_CALL,
        "Check-in with Gisselle.vtt": INTERNAL_CALL, "Zoom recording.vtt": FRAGMENT,
        "Monthly Q&A workshop 2026-02-10.vtt": WORKSHOP,
        "Review with Dana Lee (undated).vtt": CLIENT_CALL.replace("LeadLock", "Frontdesk").replace("Lead Lock", "Front Desk")})
    intake.import_directory(repo, root)
    run_jobs(repo, models)
    with repo.connection() as conn:
        return {r["title"]: r for r in conn.execute("SELECT * FROM transcripts WHERE week_id IS NULL")}


# ---- 1.B13: selection by window or set, never by week ---------------------------------------------------------------

def test_a_window_selects_included_dated_documents_and_a_set_reaches_the_undated_one(ready):
    repo, models, _ = ready
    docs = imported(ready)
    with repo.connection() as conn:
        window = select.by_window(conn, datetime(2026, 3, 9, tzinfo=UTC), datetime(2026, 3, 16, tzinfo=UTC))
        assert [r["title"][:20] for r in window] == ["GMT20260312-153000_R"]
        feb = select.by_window(conn, datetime(2026, 2, 9, tzinfo=UTC), datetime(2026, 2, 16, tzinfo=UTC))
        assert [r["title"] for r in feb] == ["Monthly Q&A workshop 2026-02-10.vtt"]
        assert select.by_window(conn, datetime(2026, 3, 12, 15, 30, tzinfo=UTC), datetime(2026, 3, 12, 15, 31, tzinfo=UTC)), "start is inclusive"
        assert not select.by_window(conn, datetime(2026, 3, 12, 15, 29, tzinfo=UTC), datetime(2026, 3, 12, 15, 30, tzinfo=UTC)), "end is exclusive"
        undated = docs["Review with Dana Lee (undated).vtt"]
        assert undated["occurred_at"] is None
        assert [r["transcript_id"] for r in select.by_set(conn, [undated["transcript_id"]])] == [undated["transcript_id"]]
        with pytest.raises(ValueError, match="excluded: Internal call"):
            select.by_set(conn, [docs["Check-in with Gisselle.vtt"]["transcript_id"]])
        with pytest.raises(ValueError, match="does not exist"):
            select.by_set(conn, ["nope"])
        with pytest.raises(ValueError, match="explicit time zones"):
            select.by_window(conn, datetime(2026, 3, 9), datetime(2026, 3, 16))


def test_the_week_a_document_was_admitted_in_plays_no_part_in_selection(ready, tmp_path):
    repo, models, _ = ready
    root = drop(tmp_path, "admitted", {"GMT20260105-100000_Recording.vtt": CLIENT_CALL.replace("Welcome Dana", "Welcome back Dana")})
    repo.admit(root, date(2026, 6, 1), 7)  # filed under a June week, but the call was in January
    with repo.connection() as conn:
        row = conn.execute("SELECT transcript_id FROM transcripts WHERE title LIKE 'GMT20260105%%'").fetchone()
    normalise(repo, row["transcript_id"], models=models)
    with repo.connection() as conn:
        doc = conn.execute("SELECT week_id,occurred_at,occurred_at_source FROM transcripts WHERE transcript_id=%s", (row["transcript_id"],)).fetchone()
        assert doc["week_id"] == "week_2026-06-01" and doc["occurred_at"].date() == date(2026, 1, 5) and doc["occurred_at_source"] == "filename"
        assert [r["transcript_id"] for r in select.by_window(conn, datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 1, 8, tzinfo=UTC))] == [row["transcript_id"]]
        assert not select.by_window(conn, datetime(2026, 6, 1, tzinfo=UTC), datetime(2026, 6, 8, tzinfo=UTC))


def test_a_live_intake_document_that_is_included_and_dated_is_selected_by_the_next_window_and_queued_for_extraction(ready):
    repo, models, _ = ready
    imported(ready)
    result = select.submit_window(repo, models, window_start=datetime(2026, 3, 9, tzinfo=UTC), mode="synthetic")
    assert result["selected_by"] == "window" and len(result["documents"]) == 1 and result["week_id"] == "week_2026-03-09"
    with repo.connection() as conn:
        doc = conn.execute("SELECT * FROM transcripts WHERE transcript_id=%s", (result["documents"][0],)).fetchone()
        assert doc["week_id"] is None, "the document still belongs to no week"
        assert doc["extraction_status"] == "queued"
        run = conn.execute("SELECT * FROM pipeline_runs WHERE run_id=%s", (result["run_id"],)).fetchone()
        assert run["input_refs"]["selected_by"] == "window" and [t["id"] for t in run["input_refs"]["transcripts"]] == result["documents"]
        job = conn.execute("SELECT * FROM pipeline_jobs WHERE run_id=%s AND stage='moment_extraction'", (result["run_id"],)).fetchone()
        assert job["status"] == "queued" and job["queue"] == "default"
        other = conn.execute("SELECT extraction_status FROM transcripts WHERE title LIKE 'Monthly%%'").fetchone()
        assert other["extraction_status"] == "pending", "documents outside the window are untouched"


def test_a_queued_window_run_executes_on_week_less_documents_and_tracks_extraction_status(ready):
    repo, models, _ = ready
    imported(ready)
    result = select.submit_window(repo, models, window_start=datetime(2026, 3, 9, tzinfo=UTC), mode="synthetic")
    worker = __import__("backend_pipeline.sql_pipeline", fromlist=["SQLWorker"]).SQLWorker(repo.settings, models)
    first = worker.once(run_id=result["run_id"])
    assert first, "the extraction job was claimed (the week-less document passed the ownership check)"
    with repo.connection() as conn:
        job = conn.execute("SELECT status,error_summary FROM pipeline_jobs WHERE job_id=%s", (first,)).fetchone()
        status = conn.execute("SELECT extraction_status FROM transcripts WHERE transcript_id=%s", (result["documents"][0],)).fetchone()["extraction_status"]
    assert job["status"] in {"completed", "failed"}
    assert status == ("completed" if job["status"] == "completed" else "failed"), (job, status)
    assert "Frozen source identity" not in (job["error_summary"] or "")


def test_an_empty_window_and_a_mixed_selection_are_refused(ready):
    repo, models, _ = ready
    imported(ready)
    with pytest.raises(ValueError, match="No included, normalised documents"):
        select.submit_window(repo, models, window_start=datetime(2025, 1, 6, tzinfo=UTC), mode="synthetic")
    with pytest.raises(ValueError, match="not both"):
        select.submit_window(repo, models, window_start=datetime(2026, 3, 9, tzinfo=UTC), transcript_ids=["x"])


def test_weekly_submission_skips_documents_that_were_excluded(ready, tmp_path):
    repo, models, _ = ready
    root = drop(tmp_path, "wk", {"Check-in with Gisselle.vtt": INTERNAL_CALL, "Review with Dana.vtt": CLIENT_CALL})
    repo.admit(root, date(2026, 7, 6), 9)
    with repo.connection() as conn:
        ids = [r["transcript_id"] for r in conn.execute("SELECT transcript_id FROM transcripts WHERE week_id='week_2026-07-06'")]
    for transcript_id in ids:
        normalise(repo, transcript_id, models=models)
    queued = repo.submit("week_2026-07-06", "synthetic")
    with repo.connection() as conn:
        run = conn.execute("SELECT input_refs FROM pipeline_runs WHERE run_id=%s", (queued["run_id"],)).fetchone()
    titles = {conn_row for conn_row in [t["id"] for t in run["input_refs"]["transcripts"]]}
    assert len(titles) == 1, "the internal check-in is not extracted"


# ---- 1.B6: one planned re-embedding under one contract ----------------------------------------------------------------

def test_reembedding_is_estimated_planned_and_leaves_every_current_chunk_under_one_contract(ready, monkeypatch):
    repo, models, _ = ready
    imported(ready)
    with repo.connection() as conn:
        for row in conn.execute("SELECT transcript_id FROM transcripts WHERE normalised_at IS NULL").fetchall():
            normalise(repo, row["transcript_id"], models=models)  # the fixture's two weekly documents, so every document is on v2
    with repo.connection() as conn:
        estimate = reembed.estimate(conn)
        report = reembed.contract_report(conn, models)
    assert estimate["chunks"] >= 2 and estimate["estimated_cost_usd"] < 0.01 and estimate["estimated_tokens"] > 0
    assert not report["complete"] and report["unembedded"] == estimate["chunks"]
    queued = reembed.queue(repo, models, mode="cached")
    assert queued["chunks"] == estimate["chunks"] and queued["runs"] and all(r["job_id"] for r in queued["runs"])
    again = reembed.queue(repo, models, mode="cached")
    assert {r["run_id"] for r in again["runs"]} == {r["run_id"] for r in queued["runs"]}, "queueing twice is one run"
    with repo.connection() as conn:
        job = conn.execute("SELECT stage,queue FROM pipeline_jobs WHERE job_id=%s", (queued["runs"][0]["job_id"],)).fetchone()
    assert (job["stage"], job["queue"]) == ("transcript_chunk_embedding", "bulk")
    worker = __import__("backend_pipeline.sql_pipeline", fromlist=["SQLWorker"]).SQLWorker(repo.settings, models, provider=FakeEmbedder())
    for _ in range(10):
        if not worker.once():
            break
    with repo.connection() as conn:
        report = reembed.contract_report(conn, models)
        failed = conn.execute("SELECT error_summary FROM pipeline_jobs WHERE status='failed'").fetchall()
    assert not failed, failed
    assert report["complete"] and report["under_contract"] == report["current_chunks"] and report["embedding_model"] == models.embedding_model
    assert reembed.queue(repo, models)["runs"] == [], "nothing is left to embed"
    # Research runs over the full archive: every included document and every current chunk, week-less ones included.
    from backend_pipeline import retrieval
    with repo.connection() as conn:
        snapshot = retrieval.archive(conn, models, True)
        week_less = {r["transcript_id"] for r in conn.execute("SELECT transcript_id FROM transcripts WHERE included AND week_id IS NULL")}
        current = {r["chunk_id"] for r in conn.execute("""SELECT c.chunk_id FROM transcript_chunks c JOIN transcripts t USING (transcript_id)
            WHERE c.is_current AND t.included AND t.canonical_document_id IS NULL""")}
    assert week_less <= set(snapshot["sources"]) and set(snapshot["chunks"]) == current
    # A client who must not be used (consent no_use) is no research evidence (2.B4): its calls and their chunks leave the
    # archive, and a snapshot taken before the consent changed is refused rather than written from.
    withheld = sorted(week_less)[0]
    with repo.connection() as conn:
        conn.execute("INSERT INTO clients(client_id,name,consent) VALUES ('client_quiet','Quiet Venue','anonymise_only')")
        conn.execute("UPDATE transcripts SET client_id='client_quiet' WHERE transcript_id=%s", (withheld,))
        before = retrieval.archive(conn, models, True)
        assert withheld in before["sources"], "anonymise_only is research evidence"
        conn.execute("UPDATE clients SET consent='no_use' WHERE client_id='client_quiet'")
        with pytest.raises(ValueError, match="restricted"):
            retrieval.check_archive(conn, before)
        after = retrieval.archive(conn, models, True)
        chunks_of = {r["chunk_id"] for r in conn.execute("SELECT chunk_id FROM transcript_chunks WHERE transcript_id=%s", (withheld,))}
    assert withheld not in after["sources"] and not chunks_of & set(after["chunks"])


class FakeEmbedder:
    def __init__(self):
        self.batches = []

    def embed_many(self, *, texts, fingerprint):
        self.batches.append(list(texts))
        data = []
        for i, text in enumerate(texts):
            vector = [0.0] * 1536
            vector[hash(text) % 1536] = 1.0
            data.append({"index": i, "embedding": vector})
        return {"model": "text-embedding-3-small", "data": data}

    def embed(self, *, text, fingerprint):
        raise AssertionError("batched only")


def test_resegmenting_keeps_old_chunks_readable_and_research_reads_only_current_ones(ready):
    repo, models, tmp_path = ready
    root = drop(tmp_path, "wk2", {"Review with Dana.vtt": CLIENT_CALL})
    repo.admit(root, date(2026, 8, 3), 11)
    with repo.connection() as conn:
        row = conn.execute("SELECT transcript_id FROM transcripts WHERE title='Review with Dana.vtt'").fetchone()
        old = [r["chunk_id"] for r in conn.execute("SELECT chunk_id FROM transcript_chunks WHERE transcript_id=%s AND segmentation_version='v1'", (row["transcript_id"],))]
    assert old
    normalise(repo, row["transcript_id"], models=models)
    with repo.connection() as conn:
        rows = conn.execute("SELECT chunk_id,is_current,segmentation_version FROM transcript_chunks WHERE transcript_id=%s", (row["transcript_id"],)).fetchall()
        assert {r["chunk_id"] for r in rows if r["segmentation_version"] == "v1"} == set(old) and not any(r["is_current"] for r in rows if r["chunk_id"] in old)
        assert all(r["is_current"] for r in rows if r["segmentation_version"] == "v2")
        assert conn.execute("SELECT count(*) n FROM transcript_chunks WHERE chunk_id=ANY(%s)", (old,)).fetchone()["n"] == len(old), "old rows stay readable"


# ---- 1.B7: the Slack export -----------------------------------------------------------------------------------------

def export_folder(tmp_path):
    root = tmp_path / "slack-export"
    (root / "wia-general").mkdir(parents=True)
    (root / "wia-ai-team-testing").mkdir()
    (root / "users.json").write_text(json.dumps([{"id": "U1", "name": "whitney", "profile": {"real_name": "Whitney Hodges"}},
                                                  {"id": "U2", "name": "gisselle", "profile": {"real_name": "Gisselle Jiménez"}}]))
    (root / "channels.json").write_text(json.dumps([{"id": "C1", "name": "wia-general"}, {"id": "C2", "name": "wia-ai-team-testing"}]))
    day1 = [{"type": "message", "user": "U1", "text": "Has anyone seen the *new* template? <@U2>", "ts": "1757000000.000100", "thread_ts": "1757000000.000100"},
            {"type": "message", "subtype": "channel_join", "user": "U2", "text": "joined", "ts": "1757000010.000100"},
            {"type": "message", "user": "U2", "text": "Yes, it is in the drive.", "ts": "1757000100.000200", "thread_ts": "1757000000.000100"},
            {"type": "message", "user": "U1", "text": "Lunch?", "ts": "1757000200.000300"},
            {"type": "message", "subtype": "bot_message", "text": "A bot post", "ts": "1757000300.000400"},
            {"type": "message", "user": "U1", "text": "", "ts": "1757000400.000500", "files": [{"id": "F1"}]}]
    day2 = [{"type": "message", "user": "U1", "text": "Thanks!", "ts": "1757086400.000100", "thread_ts": "1757000000.000100"}]
    (root / "wia-general" / "2025-09-04.json").write_text(json.dumps(day1))
    (root / "wia-general" / "2025-09-05.json").write_text(json.dumps(day2))
    (root / "wia-ai-team-testing" / "2025-09-04.json").write_text(json.dumps([{"type": "message", "user": "U1", "text": "test post", "ts": "1757001000.000100"}]))
    return root


def test_each_slack_thread_is_a_document_whose_passages_resolve_to_the_original_message_text(ready, tmp_path):
    repo, models, _ = ready
    root = export_folder(tmp_path)
    result = slack_export.import_export(repo, root, workspace="T1")
    assert result["threads"] == 2 and result["new"] == 2 and result["excluded_channels"] == ["wia-ai-team-testing"]
    assert result["skipped_messages"] == 3 and result["messages"] == 4
    with repo.connection() as conn:
        threads = conn.execute("SELECT * FROM transcripts WHERE source_type='slack' ORDER BY occurred_at").fetchall()
        assert [t["week_id"] for t in threads] == [None, None] and not conn.execute("SELECT 1 FROM transcripts WHERE original_text LIKE '%%test post%%'").fetchone()
        first = threads[0]
        messages = {m["ts"]: m for m in json.loads((root / "wia-general" / "2025-09-04.json").read_text()) + json.loads((root / "wia-general" / "2025-09-05.json").read_text())}
        assert [p["locator"]["ts"] for p in first["passage_map"]] == ["1757000000.000100", "1757000100.000200", "1757086400.000100"]
        for p in first["passage_map"]:
            assert first["original_text"][p["start"]:p["end"]] == messages[p["locator"]["ts"]]["text"]
        assert [p["speaker"] for p in first["passage_map"]] == ["Whitney Hodges", "Gisselle Jiménez", "Whitney Hodges"]
        channels = {c["name"]: c for c in conn.execute("SELECT * FROM slack_channels")}
        assert channels["wia-general"]["included"] and not channels["wia-ai-team-testing"]["included"] and channels["wia-ai-team-testing"]["exclusion_reason"]
    assert slack_export.import_export(repo, root, workspace="T1")["new"] == 0, "importing the export twice adds nothing"
    run_jobs(repo, models)
    with repo.connection() as conn:
        row = conn.execute("SELECT call_type,included,occurred_at_source FROM transcripts WHERE source_type='slack' ORDER BY occurred_at LIMIT 1").fetchone()
    assert (row["call_type"], row["included"], row["occurred_at_source"]) == ("slack_thread", True, "provider")


def test_a_zipped_export_imports_the_same_documents(ready, tmp_path):
    import zipfile
    repo, models, _ = ready
    root = export_folder(tmp_path)
    archive = tmp_path / "export.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        for path in root.rglob("*.json"):
            zf.write(path, "export-2025-09/" + path.relative_to(root).as_posix())
    assert slack_export.import_export(repo, archive, workspace="T1")["threads"] == 2
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(ValueError, match="channels.json"):
        slack_export.import_export(repo, empty, workspace="T1")


# ---- 1.B10: live and backfilled copies --------------------------------------------------------------------------------

def fathom_payload():
    return {"transcript": [{"timestamp": "00:00:01", "text": f"Welcome. {FILLER}", "speaker": {"display_name": "Carmen Cruickshank", "matched_calendar_invitee_email": "carmen@weddingindustryads.com"}},
                           {"timestamp": "00:01:00", "text": f"Thanks for having me. {FILLER}", "speaker": {"display_name": "Dana Lee", "matched_calendar_invitee_email": "dana@barn.example"}}]}


def test_a_live_fathom_document_and_its_backfilled_copy_are_linked(ready, tmp_path):
    from backend_pipeline.normalise.sources import fathom_document
    repo, models, _ = ready
    meeting = {"recording_id": 5150, "title": "Review with Dana", "recording_start_time": "2026-03-12T15:30:00Z"}
    payload = fathom_payload()
    backfilled = fathom_document(meeting, payload, "a" * 64, use_restrictions=None)
    live = fathom_document(meeting, json.loads(json.dumps(payload, indent=2)), "b" * 64)  # same call, different bytes
    assert backfilled["transcript_id"] != live["transcript_id"] and backfilled["original_text"] == live["original_text"]
    from backend_pipeline.artifacts import store_for
    store = store_for(repo.settings)
    with repo.connection() as conn:
        conn.execute("INSERT INTO weeks(week_id,week_start,week_end) VALUES ('week_2026-03-09','2026-03-09','2026-03-15')")
        intake.register(conn, store, {**backfilled, "week_id": "week_2026-03-09"}, b"a")
        intake.register(conn, store, live, b"b")
    normalise(repo, backfilled["transcript_id"], models=models)
    normalise(repo, live["transcript_id"], models=models)
    with repo.connection() as conn:
        copy = conn.execute("SELECT * FROM transcripts WHERE transcript_id=%s", (live["transcript_id"],)).fetchone()
        original = conn.execute("SELECT * FROM transcripts WHERE transcript_id=%s", (backfilled["transcript_id"],)).fetchone()
    assert copy["canonical_document_id"] == original["transcript_id"] and not copy["included"]
    assert original["canonical_document_id"] is None and original["included"]
    assert original["speaker_map"]["Carmen Cruickshank"]["basis"] == "email_domain" or original["speaker_map"]["Carmen Cruickshank"]["person_id"]
    assert original["speaker_map"]["Dana Lee"]["inferred"] is False, "a calendar email is fact"
    with repo.connection() as conn:
        duplicates.unlink(conn, live["transcript_id"], actor="whitney@example.invalid")
    normalise(repo, live["transcript_id"], models=models)
    with repo.connection() as conn:
        assert conn.execute("SELECT canonical_document_id FROM transcripts WHERE transcript_id=%s", (live["transcript_id"],)).fetchone()["canonical_document_id"] is None, \
            "a person's unlink stands"


# ---- the model path through a job -------------------------------------------------------------------------------------

class Classifier:
    def __init__(self):
        self.calls = []
        self.runs = None

    def json_call(self, *, stage, system, user, schema, fingerprint):
        self.calls.append(stage)
        return {"call_type": "office_hours", "reason": "Several members ask in turn.", "confidence": "high"}, {"fake": True}


def test_an_ambiguous_call_is_placed_by_the_model_when_one_is_configured(ready, tmp_path):
    repo, models, _ = ready
    root = drop(tmp_path, "amb", {"Carmen Cruickshank's Personal Meeting Room's transcript (17).vtt": CLIENT_CALL})
    intake.import_directory(repo, root)
    with repo.connection() as conn:
        transcript_id = conn.execute("SELECT transcript_id FROM transcripts WHERE title LIKE 'Carmen%%'").fetchone()["transcript_id"]
    models = models.model_copy(update={"openrouter_document_classification_model": "fast/model"})
    provider = Classifier()
    result = normalise(repo, transcript_id, models=models, provider=provider)
    assert provider.calls == ["document_classification"] and result["method"] == "model" and result["call_type"] == "office_hours"
    # Normalising again (a roster or client change, `documents normalise --all`, `dates --apply`) asks the model nothing new
    # and keeps its placement, with or without a model configured now: a paid decision is neither re-bought nor lost.
    again = normalise(repo, transcript_id, models=models, provider=provider)
    assert provider.calls == ["document_classification"] and (again["method"], again["call_type"]) == ("model", "office_hours")
    kept = normalise(repo, transcript_id, models=models.model_copy(update={"openrouter_document_classification_model": None}))
    assert (kept["method"], kept["call_type"], kept["included"]) == ("model", "office_hours", True)
    # With no model, an ambiguous call the model never placed keeps the rules' guess and is marked for a person.
    other = drop(tmp_path, "amb2", {"Carmen Cruickshank's Personal Meeting Room's transcript (18).vtt": CLIENT_CALL.replace("Welcome Dana", "Hi Dana")})
    intake.import_directory(repo, other)
    with repo.connection() as conn:
        fresh = conn.execute("SELECT transcript_id FROM transcripts WHERE title LIKE '%%(18).vtt'").fetchone()["transcript_id"]
    unplaced = normalise(repo, fresh, models=models.model_copy(update={"openrouter_document_classification_model": None}))
    assert unplaced["method"] == "rule" and unplaced["needs_review"]


def test_with_no_run_plan_the_model_is_not_asked_and_the_call_waits_for_a_person(ready, tmp_path, monkeypatch):
    # The classification model is set, but no run plan is active: the live provider refuses the paid call (E.B1). That must
    # not fail the document's normalisation (a live call would then never be indexed and its bucket never close): the rules'
    # guess stands, marked for a person, and the refusal is said.
    from backend_pipeline.llm import live_provider
    for name in ("ATELIER_RUN_PLAN_ID", "ATELIER_RUN_PLAN_FILE"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("OPENROUTER_API_KEY", "placeholder-never-sent")  # the plan refuses before anything is sent
    repo, models, _ = ready
    root = drop(tmp_path, "noplan", {"Carmen Cruickshank's Personal Meeting Room's transcript (19).vtt": CLIENT_CALL})
    intake.import_directory(repo, root)
    with repo.connection() as conn:
        transcript_id = conn.execute("SELECT transcript_id FROM transcripts WHERE title LIKE '%%(19).vtt'").fetchone()["transcript_id"]
    models = models.model_copy(update={"openrouter_document_classification_model": "fast/model"})
    result = normalise(repo, transcript_id, models=models, provider=live_provider(models))
    assert (result["method"], result["call_type"], result["included"], result["needs_review"]) == ("rule", "client_1to1", True, True)
    with repo.connection() as conn:
        record = conn.execute("SELECT classification FROM transcripts WHERE transcript_id=%s", (transcript_id,)).fetchone()["classification"]
    assert "not asked" in record["reason"] and record["needs_review"] is True


# ---- 1.B8: the documents API ------------------------------------------------------------------------------------------

@pytest.fixture
def client(ready):
    repo, models, _ = ready
    imported(ready)
    app = FastAPI()
    app.include_router(router(repo.settings))
    return TestClient(app), repo


def headers(email=EDITOR):
    return {"Authorization": "Bearer test-secret", "X-Atelier-Actor": email, "X-Atelier-Email": email}


def test_the_documents_api_lists_every_document_with_filters_and_pagination(client):
    http, repo = client
    everything = http.get("/storage/documents?limit=200", headers=headers()).json()
    assert everything["total"] >= 5 and len(everything["items"]) == everything["total"] and everything["counts"]["undated"] >= 1
    week_less = [d for d in everything["items"] if d["week_id"] is None]
    assert len(week_less) == 5, "a week-less document appears like any other"
    item = next(d for d in week_less if d["call_type"] == "client_1to1" and d["occurred_at"])
    assert item["date_state"] == "dated" and item["date_source"] == "filename" and item["included"] and item["extraction_status"] == "pending"
    assert {p["role"] for p in item["participants"]} == {"staff", "client"} and item["passage_count"] == 4 and item["word_count"] > 100
    first = http.get("/storage/documents?limit=2&offset=0", headers=headers()).json()
    second = http.get("/storage/documents?limit=2&offset=2", headers=headers()).json()
    assert len(first["items"]) == 2 and first["total"] == second["total"]
    assert {d["transcript_id"] for d in first["items"]}.isdisjoint({d["transcript_id"] for d in second["items"]})
    excluded = http.get("/storage/documents?included=false&source_type=zoom", headers=headers()).json()
    assert excluded["total"] >= 2 and all(d["exclusion_reason"] for d in excluded["items"])
    assert {d["call_type"] for d in excluded["items"]} >= {"internal", "fragment"}
    assert http.get("/storage/documents?call_type=workshop", headers=headers()).json()["total"] == 1
    assert http.get("/storage/documents?date_state=undated&call_type=client_1to1", headers=headers()).json()["total"] == 1
    window = http.get("/storage/documents?from=2026-03-01T00:00:00Z&to=2026-04-01T00:00:00Z", headers=headers()).json()
    assert window["total"] == 1
    assert http.get("/storage/documents?q=Frontdesk", headers=headers()).json()["total"] == 1
    assert http.get("/storage/documents?q=LeadLock", headers=headers()).json()["total"] >= 1
    assert http.get("/storage/documents?limit=500", headers=headers()).status_code == 422
    assert http.get("/storage/documents?call_type=gossip", headers=headers()).status_code == 422


def test_a_document_opens_with_its_passages_roles_and_how_it_was_classified(client):
    http, repo = client
    item = next(d for d in http.get("/storage/documents?call_type=client_1to1&date_state=dated", headers=headers()).json()["items"])
    detail = http.get(f"/storage/documents/{item['transcript_id']}", headers=headers()).json()
    assert [p["speaker_role"] for p in detail["passages"]] == ["staff", "client", "staff", "client"]
    assert detail["passages"][1]["text"].startswith("Dana Lee: Thanks Carmen") and detail["classification"]["method"] == "rule"
    assert http.get("/storage/documents/nope", headers=headers()).status_code == 404


def test_documents_need_the_backend_secret_and_only_an_editor_may_classify(client):
    http, repo = client
    assert http.get("/storage/documents").status_code == 401
    item = http.get("/storage/documents?call_type=internal", headers=headers()).json()["items"][0]
    url = f"/storage/documents/{item['transcript_id']}/classification"
    body = {"call_type": "client_1to1", "reason": "Whitney says this was a client check-in"}
    assert http.post(url, json=body, headers=headers("nobody@example.invalid")).status_code == 403
    done = http.post(url, json=body, headers=headers(EDITOR))
    assert done.status_code == 200, done.text
    detail = done.json()
    assert detail["call_type"] == "client_1to1" and detail["included"] is True and detail["classification"]["method"] == "person"
    assert detail["classification"]["decided_by"] == EDITOR and detail["extraction_status"] == "pending"
    assert http.post(url, json={"call_type": "gossip", "reason": "x"}, headers=headers(EDITOR)).status_code == 422
    assert http.post(url, json={"call_type": "vendor", "reason": ""}, headers=headers(EDITOR)).status_code == 422
    excluded = http.post(url, json={"call_type": "vendor", "reason": "A supplier call after all"}, headers=headers(EDITOR)).json()
    assert excluded["included"] is False and excluded["exclusion_reason"]
    assert http.post("/storage/documents/nope/classification", json=body, headers=headers(EDITOR)).status_code == 404


def test_the_documents_response_shape_is_published_for_generated_types():
    from backend_pipeline.api import app
    spec = app.openapi()
    assert "/storage/documents" in spec["paths"] and "DocumentList" in spec["components"]["schemas"]
    summary = spec["components"]["schemas"]["DocumentSummary"]["properties"]
    assert {"transcript_id", "occurred_at", "date_state", "call_type", "included", "exclusion_reason", "participants",
            "extraction_status", "canonical_document_id", "week_id"} <= set(summary)


def test_the_command_line_reports_what_a_person_needs_to_resolve(ready, capsys):
    from backend_pipeline import storage_cli
    repo, models, _ = ready
    imported(ready)
    result = __import__("backend_pipeline.documents.cli", fromlist=["x"]).run_cli(
        __import__("argparse").Namespace(command="documents", documents_command="report"), repo.settings, models)
    assert result["documents"]["included"] >= 3 and result["dates"]["unknown"] >= 1 and "workshop" in result["by_call_type"]
    assert result["embedding"]["unembedded"] > 0 and result["pending_embedding"]["chunks"] > 0
    assert storage_cli  # the module wires the commands
