"""3.B2/3.B3 (go-live subset): a cycle over a date window, from the app. The preview lists the window's documents, the
undated ones for a person, the late arrivals (O25) and the estimate before anything is queued; the start queues exactly what
was previewed on the weekly runner; the run records every selected document and the scenes the strategist saw, and no verified
scene of a selected call is dropped below the context budget. Synthetic documents and scripted providers; no network."""
from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend_pipeline.angle_profiles import STRATEGIST_V4_PROFILE
from backend_pipeline.cycle import window
from backend_pipeline.moments.scenes import SCENE_V2_PROFILE
from backend_pipeline.sql_pipeline import SQLWorker
from backend_pipeline.storage_api import router
from backend_pipeline.tests.moments_fixtures import (ScriptedProvider, import_documents, prepare_reference, response, scene,
                                                     standard_scripts, vtt)
from backend_pipeline.tests.platform_db import APPROVER, EDITOR, platform_setup, platform_url  # noqa: F401 (fixture)
from backend_pipeline.tests.test_documents_db import FILLER
from backend_pipeline.tests.test_strategist_profile import card, write_kb

MARCH = datetime(2026, 3, 9, tzinfo=UTC)  # the fixtures' calls are dated 10 to 12 March 2026
HEADERS = {"Authorization": "Bearer test-secret", "X-Atelier-Actor": APPROVER, "X-Atelier-Email": APPROVER}


def doc_d() -> str:
    return vtt(("Carmen Cruickshank", f"Welcome Dana, delta-late-call. {FILLER}"),
               ("Dana Lee", f"We moved the tour reminders to the morning. {FILLER}"))


class CycleProvider(ScriptedProvider):
    """Scenes from the script; one strategist call citing the first scene; flat vectors for the cards' check."""

    def __init__(self, scripts):
        super().__init__(scripts)
        self.strategist_users = []

    def json_call(self, *, stage, system, user, schema, fingerprint):
        if stage == "angle_generation":
            self.strategist_users.append(user)
            refs = re.findall(r"^## Scene (S\d+) ", user, re.MULTILINE)
            return {"week_summary": "Two review calls show how WIA reads follow-up.", "angles": [card(refs[0], 1)],
                    "internal_insights": [], "considered_not_selected": []}, {"fake": True}
        return super().json_call(stage=stage, system=system, user=user, schema=schema, fingerprint=fingerprint)

    def embed(self, *, text, fingerprint):
        return [1.0] + [0.0] * 1535, {"fake": True}


@pytest.fixture
def ready(platform_setup):  # noqa: F811
    repo, models, tmp = platform_setup
    prepare_reference(repo)
    models = models.model_copy(update={"extraction_profile": SCENE_V2_PROFILE, "angle_prompt_profile": STRATEGIST_V4_PROFILE,
                                       "knowledge_base_root": write_kb(tmp / "kb")})
    from backend_pipeline.tests.moments_fixtures import FILES
    docs = import_documents(repo, models, tmp, {k: v for k, v in FILES.items() if not k.endswith("C.vtt")})
    provider = CycleProvider({**standard_scripts(), "delta-late-call": lambda inv, n, system: response(inv, scene(
        quote="We moved the tour reminders to the morning.", setup="The client moved reminders."))})
    app = FastAPI()
    app.include_router(router(repo.settings))
    return repo, models, tmp, docs, provider, TestClient(app)


def run_all(repo, models, provider, run_id):
    worker = SQLWorker(repo.settings, models, provider=provider)
    for _ in range(8):
        if not worker.once(run_id=run_id):
            break


def test_the_preview_lists_the_window_and_the_estimate_and_queues_nothing(ready):
    repo, models, tmp, docs, provider, client = ready
    shown = window.preview(repo, models, MARCH)
    assert shown["document_count"] == 2 and [d["selected_because"] for d in shown["documents"]] == ["window", "window"]
    assert shown["window"] == {"start": "2026-03-09T00:00:00+00:00", "end": "2026-03-16T00:00:00+00:00"}
    estimate = shown["estimate"]
    assert estimate["provider_calls_made"] == 0 and estimate["documents_to_extract"] == 2
    assert {c["stage"] for c in estimate["components"]} >= {"scene extraction", "strategist"}
    assert shown["budgets"] and {b["purpose"] for b in shown["budgets"]} == {"cycle", "extraction"}
    assert provider.calls == []
    with repo.connection() as conn:
        assert not conn.execute("SELECT 1 FROM pipeline_runs WHERE run_scope='weekly_angles'").fetchone()
    # Undated documents are listed for a person, never selected by a window.
    with repo.connection() as conn:
        conn.execute("UPDATE transcripts SET occurred_at=NULL WHERE transcript_id=%s", (docs["B"]["transcript_id"],))
    again = window.preview(repo, models, MARCH)
    assert again["document_count"] == 1 and [d["transcript_id"] for d in again["undated"]] == [docs["B"]["transcript_id"]]
    assert again["selection_hash"] != shown["selection_hash"]


def test_with_no_weekly_caps_the_preview_never_warns_that_the_estimate_passes_a_budget(ready):
    from backend_pipeline.llm import standing
    from backend_pipeline.settings_store import set_value
    repo, models, tmp, docs, provider, client = ready
    with repo.connection() as conn:
        set_value(conn, "budgets.uncapped", False, APPROVER)
        for name in ("cycle", "extraction"):
            row = standing.ensure(conn, name)
            conn.execute("UPDATE run_plans SET cost_used_usd=max_cost_usd WHERE plan_id=%s", (row["plan_id"],))
        conn.commit()
    capped = window.preview(repo, models, MARCH)
    assert capped["estimate"]["total_usd"] > 0 and not capped["within_budget"]
    with repo.connection() as conn:
        set_value(conn, "budgets.uncapped", True, APPROVER)
        conn.commit()
    shown = window.preview(repo, models, MARCH)
    assert shown["within_budget"] and all(b["uncapped"] and b["cap_usd"] is None for b in shown["budgets"])


def test_the_strategist_estimate_counts_the_call_turns_each_scene_carries(ready):
    """N2, 23 October: the October cycle's strategist read 188,604 input tokens; the preview had counted the scene records
    alone (78,000 tokens, USD 0.32 against 0.61). Each scene reaches the strategist with the turns it spans, so those count."""
    import json as _json
    repo, models, tmp, docs, provider, client = ready
    doc = docs["A"]["transcript_id"]
    body = {"quote": "q", "proposition": "p" * 200}
    refs = [{"transcript_id": doc, "start": 0, "end": 3000}, {"transcript_id": doc, "start": 3000, "end": 4000}]
    with repo.connection() as conn:
        conn.execute("""INSERT INTO key_moments(moment_id,moment_body,evidence_refs,document_id,is_current,quote_verified,
            extractor_version) VALUES ('moment_estimate',%s,%s,%s,true,true,%s)""",
                     (_json.dumps(body), _json.dumps(refs), doc, SCENE_V2_PROFILE))
    estimate = window.preview(repo, models, MARCH)["estimate"]
    strategist = next(c for c in estimate["components"] if c["stage"] == "strategist")
    assert estimate["scenes_in_ledger"] == 1
    from backend_pipeline.settings_store import value
    with repo.connection() as conn:
        prefix = value("context.budget.prefix_tokens", conn)
    # The held scene's record and its 4,000 characters of turns; the documents not yet extracted are sized like it.
    per_scene = len(_json.dumps(body)) + 4000
    scenes = 1 + estimate["scenes_assumed_for_new_documents"]
    assert strategist["input_tokens"] == int(prefix + scenes * per_scene / window.CHARACTERS_PER_TOKEN)


def test_only_an_approver_previews_or_starts_and_a_changed_selection_is_refused(ready):
    repo, models, tmp, docs, provider, client = ready
    editor = {**HEADERS, "X-Atelier-Actor": EDITOR, "X-Atelier-Email": EDITOR}
    query = "/storage/cycles/preview?from=2026-03-09T00:00:00Z"
    assert client.get(query, headers=editor).status_code == 403
    shown = client.get(query, headers=HEADERS).json()
    assert shown["document_count"] == 2
    body = {"window_start": "2026-03-09T00:00:00Z", "selection_hash": shown["selection_hash"], "mode": "replay"}
    assert client.post("/storage/cycles", json=body, headers=editor).status_code == 403
    stale = client.post("/storage/cycles", json={**body, "selection_hash": "0" * 64}, headers=HEADERS)
    assert stale.status_code == 409 and "changed since the preview" in stale.json()["detail"]


def test_a_cycle_records_its_documents_and_every_verified_scene_reaches_the_strategist(ready):
    repo, models, tmp, docs, provider, client = ready
    shown = window.preview(repo, models, MARCH)
    started = window.start(repo, models, APPROVER, MARCH, None, mode="synthetic", expected_selection=shown["selection_hash"])
    run_all(repo, models, provider, started["run_id"])
    detail = client.get(f"/storage/cycles/{started['run_id']}", headers=HEADERS).json()
    assert detail["window"]["start"].startswith("2026-03-09") and detail["selected_by"] == "window"
    assert {d["transcript_id"] for d in detail["documents"]} == {docs["A"]["transcript_id"], docs["B"]["transcript_id"]}
    assert detail["estimate"]["total_usd"] == shown["estimate"]["total_usd"], "the run keeps the estimate it was started on"
    coverage = detail["scene_coverage"]
    assert coverage["state"] == "complete", coverage
    # Every verified scene of both calls was sent: A has two (the third quote binds nothing), B two.
    assert coverage["verified"] == coverage["sent"] == 4 and coverage["not_sent"] == []
    assert {d["transcript_id"]: d["sent"] for d in coverage["documents"]} == {docs["A"]["transcript_id"]: 2, docs["B"]["transcript_id"]: 2}
    (user,) = provider.strategist_users
    with repo.connection() as conn:
        quotes = [r["quote"] for r in conn.execute("""SELECT moment_body->>'quote' AS quote FROM key_moments WHERE document_id=ANY(%s)
            AND is_current AND quote_verified""", ([docs["A"]["transcript_id"], docs["B"]["transcript_id"]],))]
        generation = conn.execute("SELECT result_refs FROM pipeline_jobs WHERE run_id=%s AND stage='angle_generation'",
                                  (started["run_id"],)).fetchone()["result_refs"]
    assert len(quotes) == 4 and all(q in user for q in quotes), "no verified scene was dropped below the context budget"
    assert generation["scene_coverage"]["state"] == "complete", "the run records what the strategist saw"
    listed = client.get("/storage/cycles", headers=HEADERS).json()
    assert listed[0]["run_id"] == started["run_id"] and listed[0]["coverage_state"] == "complete" and listed[0]["scenes_sent"] == 4


def test_a_cycle_reads_the_scenes_a_document_extraction_already_made_without_calling_again(ready):
    """Found by the N1 shakedown, and the order Phase N2 runs: the delivery window is extracted document by document
    (`moments extract`, week-less runs), then the window's cycle starts. Its extraction stage finds each document's saved
    answer, which belongs to a week-less run; the origin check refused it ("Cached origin run belongs to another week"), so
    every extracted document failed the cycle (or, on a paid run, would have been paid for twice)."""
    from backend_pipeline.documents import select
    from backend_pipeline.jobs.executor import run_job
    from backend_pipeline.moments import queue
    repo, models, tmp, docs, provider, client = ready
    with repo.connection() as conn:
        rows = select.by_set(conn, [docs["A"]["transcript_id"], docs["B"]["transcript_id"]])
    queued = queue.queue_extraction(repo, models, rows, mode="synthetic", actor="tester", queue="bulk", profile=SCENE_V2_PROFILE)
    for job_id in queued["jobs"]:
        run_job(job_id, storage=repo.settings, models=models, provider=provider, successors=False)
    shown = window.preview(repo, models, MARCH)
    started = window.start(repo, models, APPROVER, MARCH, None, mode="synthetic", expected_selection=shown["selection_hash"])
    run_all(repo, models, provider, started["run_id"])
    with repo.connection() as conn:
        stages = {r["stage"]: (r["status"], r["error_summary"]) for r in conn.execute(
            "SELECT stage,status,error_summary FROM pipeline_jobs WHERE run_id=%s", (started["run_id"],))}
    assert stages["moment_extraction"][0] == "completed", stages["moment_extraction"]
    assert stages["angle_generation"][0] == "completed", stages
    detail = client.get(f"/storage/cycles/{started['run_id']}", headers=HEADERS).json()
    assert detail["scene_coverage"]["state"] == "complete" and detail["scene_coverage"]["sent"] == 4
    assert len(provider.strategist_users) == 1


def test_a_cycle_reads_a_document_extracted_again_under_a_new_model(ready):
    """N1 shakedown: a document whose extraction failed under one model is queued again under today's (its job's key names
    the model); the cycle reads it from the scene ledger, with no new call."""
    from backend_pipeline.documents import select
    from backend_pipeline.jobs.executor import run_job
    from backend_pipeline.moments import queue
    repo, models, tmp, docs, provider, client = ready
    ids = [docs["A"]["transcript_id"], docs["B"]["transcript_id"]]
    with repo.connection() as conn:
        rows = select.by_set(conn, ids)
    first = queue.queue_extraction(repo, models, rows, mode="synthetic", actor="tester", queue="bulk", profile=SCENE_V2_PROFILE)
    for job_id in first["jobs"]:
        run_job(job_id, storage=repo.settings, models=models, provider=provider, successors=False)
    with repo.connection() as conn:  # B's extraction failed under the first model
        conn.execute("UPDATE pipeline_jobs SET status='failed' WHERE stage='moment_extraction' AND transcript_id=%s", (ids[1],))
        conn.execute("UPDATE key_moments SET is_current=false WHERE document_id=%s", (ids[1],))
        rows = select.by_set(conn, ids)
    models = models.model_copy(update={"openrouter_moments_model": "another/extraction-model"})
    again = queue.queue_extraction(repo, models, rows, mode="synthetic", actor="tester", queue="bulk", profile=SCENE_V2_PROFILE,
                                   retry_failed=True)
    assert again["requeued_for_new_model"] == [ids[1]]
    for job_id in again["jobs"]:
        run_job(job_id, storage=repo.settings, models=models, provider=provider, successors=False)
    calls = len(provider.calls)
    shown = window.preview(repo, models, MARCH)
    started = window.start(repo, models, APPROVER, MARCH, None, mode="synthetic", expected_selection=shown["selection_hash"])
    run_all(repo, models, provider, started["run_id"])
    with repo.connection() as conn:
        extraction = conn.execute("SELECT status,result_refs FROM pipeline_jobs WHERE run_id=%s AND stage='moment_extraction'",
                                  (started["run_id"],)).fetchone()
    assert extraction["status"] == "completed"
    assert all("reused_from_job" in d for d in extraction["result_refs"]["documents"]), extraction["result_refs"]["documents"]
    assert len(provider.strategist_users) == 1 and len(provider.calls) - calls <= 1, "the strategist only"


def test_a_saved_answer_from_a_week_less_document_extraction_serves_a_weeks_cycle(ready):
    """The live replay path of the test above (synthetic runs do not replay): the cycle's extraction stage reads a document's
    saved answer, made by its own week-less extraction run, and records where the answer came from. The origin check
    refused any run of another week, and a week-less run is never the cycle's week."""
    from types import SimpleNamespace
    repo, models, tmp, docs, provider, client = ready
    worker = SQLWorker(repo.settings, models, provider=provider)
    with repo.connection() as conn:
        conn.execute("""INSERT INTO weeks(week_id,week_start,week_end) VALUES ('week_2026-03-02','2026-03-02','2026-03-08'),
            ('week_2026-03-09','2026-03-09','2026-03-15') ON CONFLICT DO NOTHING""")
        conn.execute("""INSERT INTO pipeline_runs(run_id,week_id,run_scope,status,trigger_type,input_refs)
            VALUES ('docext_saved',NULL,'document_extraction','completed','manual','{}'),
                   ('weekly_other','week_2026-03-02','weekly_angles','completed','manual','{}')""")
        cycle = {"run_id": "cycle_now", "week_id": "week_2026-03-09", "input_refs": {"mode": "live"}}
        worker.origin(conn, SimpleNamespace(run_id="docext_saved", created_at=datetime.now(UTC)), cycle)  # refused before N1
        with pytest.raises(ValueError, match="another week"):
            worker.origin(conn, SimpleNamespace(run_id="weekly_other", created_at=datetime.now(UTC)), cycle)


def test_the_coverage_names_a_verified_scene_that_was_not_sent_and_one_held_for_consent(ready):
    repo, models, tmp, docs, provider, client = ready
    shown = window.preview(repo, models, MARCH)
    started = window.start(repo, models, APPROVER, MARCH, None, mode="synthetic", expected_selection=shown["selection_hash"])
    run_all(repo, models, provider, started["run_id"])
    with repo.connection() as conn:
        run = conn.execute("SELECT * FROM pipeline_runs WHERE run_id=%s", (started["run_id"],)).fetchone()
        sent = conn.execute("SELECT result_refs FROM pipeline_jobs WHERE run_id=%s AND stage='angle_generation'",
                            (started["run_id"],)).fetchone()["result_refs"]["moment_ids"]
        # Had the strategist seen one scene fewer, and had one client withdrawn consent, the record would say which.
        coverage = window.scene_coverage(conn, run, sent=sent[2:], dropped=[{"moment_id": sent[0], "reason": "do_not_use"}])
    assert coverage["state"] == "incomplete" and coverage["not_sent"] == [sent[1]] and coverage["held_for_consent"] == 1


def test_a_call_that_arrives_after_its_windows_cycle_is_listed_for_the_next_window(ready):
    repo, models, tmp, docs, provider, client = ready
    shown = window.preview(repo, models, MARCH)
    started = window.start(repo, models, APPROVER, MARCH, None, mode="synthetic", expected_selection=shown["selection_hash"])
    run_all(repo, models, provider, started["run_id"])
    late = import_documents(repo, models, tmp, {"Review with Dana Lee 2026-03-13 D.vtt": doc_d}, name="late")["D"]
    with repo.connection() as conn:
        # It arrived after the March cycle started.
        conn.execute("UPDATE transcripts SET ingested_at=%s WHERE transcript_id=%s",
                     (datetime.now(UTC) + timedelta(minutes=5), late["transcript_id"]))
    following = window.preview(repo, models, MARCH + timedelta(days=7))
    assert [d["transcript_id"] for d in following["late_arrivals"]] == [late["transcript_id"]]
    assert following["late_arrivals"][0]["missed_window"]["start"].startswith("2026-03-09")
    assert following["document_count"] == 1, "the next window reads it"
    nxt = window.start(repo, models, APPROVER, MARCH + timedelta(days=7), None, mode="synthetic",
                       expected_selection=following["selection_hash"])
    assert nxt["late_arrivals"] == [late["transcript_id"]]
    detail = window.detail(repo, nxt["run_id"])
    assert [d["selected_because"] for d in detail["documents"]] == ["late_arrival"]
    # Read once, it is not late any more.
    assert window.preview(repo, models, MARCH + timedelta(days=14))["late_arrivals"] == []


def test_the_weeks_review_document_comes_from_the_route_and_the_command(ready, monkeypatch, tmp_path, capsys):
    repo, models, tmp, docs, provider, client = ready
    shown = window.preview(repo, models, MARCH)
    started = window.start(repo, models, APPROVER, MARCH, None, mode="synthetic", expected_selection=shown["selection_hash"])
    run_all(repo, models, provider, started["run_id"])
    answer = client.get(f"/storage/weeks/{started['week_id']}/review.md", headers=HEADERS)
    assert answer.status_code == 200 and answer.headers["content-type"].startswith("text/markdown")
    text = answer.text
    assert text.startswith("# Content Atelier Review") and "# Content bank" in text
    assert "## How we read a planner's lead quality, idea 1" in text, "the undeveloped card is in the content bank"
    assert "**Calls from:** 2026-03-09 to 2026-03-16 (2 calls)" in text
    assert client.get("/storage/weeks/week_missing/review.md", headers=HEADERS).status_code == 404
    from backend_pipeline import storage_cli
    monkeypatch.setenv("ATELIER_DATABASE_URL", repo.settings.database_url)
    monkeypatch.setenv("ATELIER_ARTIFACT_ROOT", str(repo.settings.artifact_root))
    out = tmp_path / "review.md"
    storage_cli.main(["review-document", "--week-id", started["week_id"], "--out", str(out)])
    assert out.read_text(encoding="utf-8").split("**Exported:**")[0] == text.split("**Exported:**")[0]


def test_the_weeks_review_document_downloads_as_a_word_file_from_the_route_and_the_command(ready, monkeypatch, tmp_path):
    """5.B14 (.docx): one route and one command produce the week's review document as a Word file on the template in the
    image; it opens with python-docx, the header once from the template, the Markdown's headings as Word headings."""
    import io

    import docx

    from backend_pipeline.briefs import review_docx
    from backend_pipeline.briefs.review_document import HEADER
    repo, models, tmp, docs, provider, client = ready
    shown = window.preview(repo, models, MARCH)
    started = window.start(repo, models, APPROVER, MARCH, None, mode="synthetic", expected_selection=shown["selection_hash"])
    run_all(repo, models, provider, started["run_id"])
    week_id = started["week_id"]
    markdown = client.get(f"/storage/weeks/{week_id}/review.md", headers=HEADERS).text
    headings = [line.lstrip("#").strip() for line in markdown.splitlines()[1:] if line.startswith("#")]
    answer = client.get(f"/storage/weeks/{week_id}/review.docx", headers=HEADERS)
    assert answer.status_code == 200 and answer.headers["content-type"] == review_docx.MEDIA_TYPE
    assert answer.headers["content-disposition"] == f'attachment; filename="content-atelier-review-{week_id}.docx"'
    word = docx.Document(io.BytesIO(answer.content))
    assert [p.text for p in word.paragraphs[:3]] == list(HEADER)
    assert [p.text for p in word.paragraphs if p.style.name.startswith("Heading")] == headings
    assert "How we read a planner's lead quality, idea 1" in headings, "the content bank's card"
    assert word.core_properties.title == f"Content Atelier Review, {week_id}"
    assert client.get("/storage/weeks/week_missing/review.docx", headers=HEADERS).status_code == 404
    from backend_pipeline import storage_cli
    monkeypatch.setenv("ATELIER_DATABASE_URL", repo.settings.database_url)
    monkeypatch.setenv("ATELIER_ARTIFACT_ROOT", str(repo.settings.artifact_root))
    out = tmp_path / "out" / "review.docx"
    storage_cli.main(["review-document", "--week-id", week_id, "--format", "docx", "--out", str(out)])
    assert [p.text for p in docx.Document(str(out)).paragraphs if p.style.name.startswith("Heading")] == headings
    with pytest.raises(SystemExit):
        storage_cli.main(["review-document", "--week-id", week_id, "--format", "docx"])
