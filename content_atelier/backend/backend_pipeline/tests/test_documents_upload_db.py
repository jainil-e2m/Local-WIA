"""1.F6 and 1.F7 on a real database: a call that waits for a person is found and classified from the app, and the decision
survives every later rule pass; a transcript file uploaded from the Sources screen goes through `documents import`.

Synthetic transcripts; no network and no model call."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
from test_documents_db import CLIENT_CALL, FILLER, run_jobs, vtt
from test_documents_pipeline_db import headers, ready  # noqa: F401 (fixture)

from backend_pipeline.documents import intake
from backend_pipeline.documents.jobs import normalise
from backend_pipeline.storage_api import router
from backend_pipeline.tests.platform_db import EDITOR, platform_setup, platform_url  # noqa: F401 (fixtures)

# A title that says nothing about the call, and someone outside WIA speaking: the rules cannot place it, so it waits.
WAITING = vtt(("Carmen Cruickshank", f"Hello again. {FILLER}"), ("Jordan Example", f"Thanks for making time. {FILLER}"))


def app(repo):
    api = FastAPI()
    api.include_router(router(repo.settings))
    return TestClient(api)


def test_a_waiting_call_is_listed_classified_by_an_editor_and_never_overwritten_by_a_rule(ready, tmp_path):  # noqa: F811
    repo, models, _ = ready
    folder = tmp_path / "drop"
    folder.mkdir()
    (folder / "Zoom Meeting.vtt").write_text(WAITING, encoding="utf-8")
    (folder / "GMT20260312-153000_Recording Review with Dana Lee.vtt").write_text(CLIENT_CALL, encoding="utf-8")
    intake.import_directory(repo, folder)
    run_jobs(repo, models)
    http = app(repo)
    waiting = http.get("/storage/documents?needs_review=true", headers=headers()).json()
    assert waiting["total"] == 1 and waiting["counts"]["needs_review"] == 1
    item = waiting["items"][0]
    assert item["title"] == "Zoom Meeting.vtt" and item["needs_review"] is True
    assert http.get("/storage/documents?needs_review=false", headers=headers()).json()["total"] >= 1
    url = f"/storage/documents/{item['transcript_id']}/classification"
    body = {"call_type": "client_1to1", "reason": "A check-in with a member, from the recording"}
    assert http.post(url, json=body, headers=headers("nobody@example.invalid")).status_code == 403
    done = http.post(url, json=body, headers=headers(EDITOR)).json()
    assert done["needs_review"] is False and done["classification"]["method"] == "person" and done["classification"]["decided_by"] == EDITOR
    assert http.get("/storage/documents?needs_review=true", headers=headers()).json()["total"] == 0
    # The rules run again (a roster change, a new normaliser): the person's decision stands, and the call does not wait again.
    again = normalise(repo, item["transcript_id"], models=models)
    assert again["call_type"] == "client_1to1" and again["method"] == "person" and again["needs_review"] is False
    intake.import_directory(repo, folder)
    run_jobs(repo, models)
    detail = http.get(f"/storage/documents/{item['transcript_id']}", headers=headers()).json()
    assert detail["call_type"] == "client_1to1" and detail["classification"]["reason"] == body["reason"] and not detail["needs_review"]


def test_an_editor_uploads_a_transcript_through_the_same_import(ready):  # noqa: F811
    repo, models, _ = ready
    http = app(repo)
    body = {"filename": "Member review's transcript.vtt", "content": CLIENT_CALL, "occurred_at": "2026-10-14T12:00:00Z"}
    assert http.post("/storage/documents/import", json=body, headers=headers("nobody@example.invalid")).status_code == 403
    first = http.post("/storage/documents/import", json=body, headers=headers(EDITOR))
    assert first.status_code == 200, first.text
    result = first.json()
    assert result["created"] is True and result["run_id"] and result["document"]["title"] == "Member review's transcript.vtt"
    assert result["document"]["source_type"] == "zoom" and result["document"]["date_source"] == "manual"
    # The same file again is the same document, with nothing queued; the same bytes from `documents import` too.
    again = http.post("/storage/documents/import", json={**body, "occurred_at": None}, headers=headers(EDITOR)).json()
    assert again["created"] is False and again["transcript_id"] == result["transcript_id"] and again["run_id"] is None
    run_jobs(repo, models)
    with repo.connection() as conn:
        row = conn.execute("SELECT * FROM transcripts WHERE transcript_id=%s", (result["transcript_id"],)).fetchone()
    assert row["normalised_at"] is not None and row["occurred_at_source"] == "manual" and row["occurred_at"].isoformat().startswith("2026-10-14")
    assert row["source_metadata"]["uploaded_by"] == EDITOR and row["raw_object_key"].startswith("source-originals/")
    # A plain text export with speaker lines, as a manual entry.
    text = http.post("/storage/documents/import", headers=headers(EDITOR), json={
        "filename": "notes.txt", "source_type": "manual", "content": f"Carmen Cruickshank: {FILLER}\nDana Lee: {FILLER} thanks\n"}).json()
    assert text["created"] and text["document"]["source_type"] == "manual" and text["document"]["date_state"] == "undated"
    for bad, status in [({**body, "filename": "../escape.vtt"}, 422), ({**body, "filename": "call.pdf"}, 422),
                        ({**body, "filename": "dir/call.vtt"}, 422), ({**body, "content": ""}, 422),
                        ({**body, "occurred_at": "2026-10-14T12:00:00"}, 422), ({**body, "source_type": "fathom"}, 422),
                        ({**body, "extra": 1}, 422), ({**body, "filename": "broken.vtt", "content": "WEBVTT\n\n1\n00:00:01.000 --> later\nA: hi\n"}, 422)]:
        response = http.post("/storage/documents/import", json=bad, headers=headers(EDITOR))
        assert response.status_code == status, (bad["filename"], response.text)
    assert "could not" in http.post("/storage/documents/import", headers=headers(EDITOR), json={
        **body, "filename": "empty.vtt", "content": "WEBVTT\n"}).json()["detail"]


def test_the_upload_route_is_published_for_generated_types():
    from backend_pipeline.api import app as backend
    spec = backend.openapi()
    assert "post" in spec["paths"]["/storage/documents/import"]
    assert {"filename", "content", "occurred_at", "source_type"} <= set(spec["components"]["schemas"]["DocumentUpload"]["properties"])
    assert "needs_review" in spec["components"]["schemas"]["DocumentSummary"]["properties"]
