"""Phase 1 on a real database: file intake as documents (1.B3), classification (1.B4), speaker roles (1.B5), dates (1.B11),
segmentation with headers and roles (1.B6), duplicates (1.B10) and the glossary search (1.B12).

Synthetic transcripts only; the model path uses an offline provider. No network."""
from __future__ import annotations

import hashlib
import json
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from backend_pipeline import reference
from backend_pipeline.documents import intake
from backend_pipeline.documents.jobs import normalise
from backend_pipeline.normalise import glossary as glossary_module
from backend_pipeline.normalise.classify import RULES_VERSION
from backend_pipeline.sql_pipeline import SQLWorker
from backend_pipeline.tests.platform_db import platform_setup, platform_url  # noqa: F401 (fixtures)

KB = Path(__file__).resolve().parents[2] / "knowledge_base"
FILLER = " ".join(["we", "talked", "about", "inquiries", "follow-up", "and", "the", "booking", "calendar"] * 8)


def vtt(*turns) -> str:
    cues = [f"{i}\n00:{i // 60:02d}:{i % 60:02d}.000 --> 00:{i // 60:02d}:{i % 60 + 1:02d}.000\n{speaker}: {text}\n"
            for i, (speaker, text) in enumerate(turns, 1)]
    return "WEBVTT\n\n" + "\n".join(cues)


CLIENT_CALL = vtt(("Carmen Cruickshank", f"Welcome Dana. {FILLER}"), ("Dana Lee", f"Thanks Carmen. {FILLER}"),
                  ("Carmen Cruickshank", f"Let us review the LeadLock follow-up. {FILLER}"), ("Dana Lee", "Lead Lock has helped a lot."))
INTERNAL_CALL = vtt(("Whitney Hodges", f"Team sync. {FILLER}"), ("Gisselle Jiménez", f"Agreed. {FILLER}"))
FRAGMENT = vtt(("Carmen Cruickshank", "Hello?"))
WORKSHOP = vtt(("Whitney Hodges", f"Welcome everyone. {FILLER}"), ("Erin Smith", f"Question about pricing. {FILLER}"))


@pytest.fixture
def folder(tmp_path):
    root = tmp_path / "drop"
    root.mkdir()
    (root / "GMT20260312-153000_Recording Carmen Cruickshank's Personal Meeting Room's transcript (3).vtt").write_text(CLIENT_CALL, encoding="utf-8")
    (root / "Check-in with Gisselle.vtt").write_text(INTERNAL_CALL, encoding="utf-8")
    (root / "Zoom recording.vtt").write_text(FRAGMENT, encoding="utf-8")
    (root / "Monthly Q&A workshop 2026-02-10.vtt").write_text(WORKSHOP, encoding="utf-8")
    return root


@pytest.fixture
def ready(platform_setup):  # noqa: F811
    repo, models, tmp_path = platform_setup
    with repo.connection() as conn:
        reference.sync_roster(conn, KB, date(2026, 10, 18))
        reference.add_glossary_term(conn, "LeadLock", "product", ["Lead Lock", "lead luck"])
    return repo, models, tmp_path


def run_jobs(repo, models, limit=20):
    worker = SQLWorker(repo.settings, models)
    for _ in range(limit):
        if not worker.once():
            break


def documents(repo):
    with repo.connection() as conn:
        return {r["title"]: r for r in conn.execute("SELECT * FROM transcripts WHERE week_id IS NULL ORDER BY title")}


def test_importing_the_same_folder_twice_adds_nothing(ready, folder):
    repo, models, _ = ready
    first = intake.import_directory(repo, folder)
    assert first["files"] == 4 and first["new"] == 4 and first["jobs"] == 4
    with repo.connection() as conn:
        counts = [conn.execute(f"SELECT count(*) n FROM {t}").fetchone()["n"] for t in ("transcripts", "pipeline_jobs", "pipeline_runs")]
    again = intake.import_directory(repo, folder)
    assert again["new"] == 0 and again["unchanged"] == 4 and again["jobs"] == 0 and again["run_id"] is None
    with repo.connection() as conn:
        assert [conn.execute(f"SELECT count(*) n FROM {t}").fetchone()["n"] for t in ("transcripts", "pipeline_jobs", "pipeline_runs")] == counts


def test_one_unreadable_file_or_an_unselected_fathom_capture_does_not_stop_an_import(ready, folder, tmp_path):
    # The real backfill tree (S.B10) holds, beside the 170 selected originals, Fathom captures of calls Zoom already has
    # (not selected for admission) and may hold a file that does not parse. Each is named with its reason; the rest import.
    from backend_pipeline.tests.test_transcript_backfill import native_source
    repo, models, _ = ready
    # Zoom's own downloads are .txt files holding WebVTT, with a byte-order mark and Windows line endings.
    (folder / "Carmen Cruickshank's Personal Meeting Room's transcript (17).txt").write_bytes(
        ("﻿" + CLIENT_CALL.replace("Welcome Dana", "Welcome back Dana")).replace("\n", "\r\n").encode("utf-8"))
    (folder / "broken timing.vtt").write_text("WEBVTT\n\n1\n00:00:01.000 --> later\nCarmen Cruickshank: hello\n", encoding="utf-8")
    (folder / "latin1 notes.txt").write_bytes("Caf\xe9 follow-up with the venue".encode("latin-1"))
    (folder / "empty.txt").write_bytes(b"")
    (folder / "._Check-in with Gisselle.vtt").write_bytes(b"\x00\x05\x16\x07\x00\x02\x00\x00Mac OS X")  # macOS AppleDouble
    selected, _ = native_source(folder, week=11)
    overlap = folder / "week12" / "fathom" / "zoom_overlap" / "77"
    overlap.mkdir(parents=True)
    (overlap / "transcript.raw.json").write_bytes(selected.read_bytes())
    envelope = json.loads(selected.with_name("metadata.json").read_text(encoding="utf-8"))
    (overlap / "metadata.json").write_text(json.dumps({**envelope, "classification": "zoom_overlap",
                                                       "selected_as_additional_source": False}), encoding="utf-8")
    result = intake.import_directory(repo, folder)
    assert result["new"] == 6 and result["jobs"] == 6, result  # the four calls, the .txt download and the selected Fathom call
    assert {f["file"]: f["reason"].split(":")[0] for f in result["failed"]} == {
        "broken timing.vtt": "ValueError", "latin1 notes.txt": "UnicodeDecodeError", "empty.txt": "ValueError"}
    assert [s["file"] for s in result["skipped"]] == ["week12/fathom/zoom_overlap/77/transcript.raw.json"]
    assert "not selected for admission" in result["skipped"][0]["reason"]
    with repo.connection() as conn:
        txt = conn.execute("SELECT * FROM transcripts WHERE title LIKE '%%(17).txt'").fetchone()
        assert {p["speaker"] for p in txt["passage_map"]} == {"Carmen Cruickshank", "Dana Lee"}
        assert conn.execute("SELECT count(*) n FROM transcripts WHERE source_type='fathom'").fetchone()["n"] == 1
    again = intake.import_directory(repo, folder)
    assert again["new"] == 0 and again["unchanged"] == 6 and len(again["failed"]) == 3 and len(again["skipped"]) == 1


def test_importing_the_backfill_tree_over_the_restored_database_finds_the_fathom_calls_already_admitted(ready, tmp_path):
    # S.B10 restores the developer's database (170 transcripts admitted into weeks on 15 October) and the runbook then imports
    # the same originals. The six Fathom calls were admitted before 1.B14 added `locator` and `extraction_method` to each
    # passage: same recording, same bytes, same text and passages, so the same document. One real conflict is that file's
    # failure with its reason, never the whole import's.
    from backend_pipeline.fathom_sources import capture_fathom
    from backend_pipeline.repository import insert
    from backend_pipeline.tests.test_transcript_backfill import native_source
    repo, models, _ = ready
    root = tmp_path / "backfill"
    root.mkdir()
    path, _ = native_source(root, week=11)
    legacy = capture_fathom(path, 11, 1)
    legacy["passage_map"] = [{k: v for k, v in p.items() if k not in ("locator", "extraction_method")} for p in legacy["passage_map"]]
    with repo.connection() as conn:
        conn.execute("INSERT INTO weeks(week_id,week_start,week_end) VALUES ('week_2026-08-10','2026-08-10','2026-08-16')")
        insert(conn, "transcripts", {**legacy, "week_id": "week_2026-08-10", "processing_status": "admitted"})
    (root / "week11" / "Dana Lee call.vtt").write_text(CLIENT_CALL, encoding="utf-8")
    result = intake.import_directory(repo, root)
    assert result["failed"] == [] and result["new"] == 1 and result["unchanged"] == 1, result
    with repo.connection() as conn:
        stored = conn.execute("SELECT passage_map,week_id FROM transcripts WHERE transcript_id=%s", (legacy["transcript_id"],)).fetchone()
        conn.execute("UPDATE transcripts SET original_text=original_text || ' (edited)' WHERE transcript_id=%s", (legacy["transcript_id"],))
    assert stored["passage_map"] == legacy["passage_map"] and stored["week_id"] == "week_2026-08-10", "the stored document is untouched"
    conflict = intake.import_directory(repo, root)
    assert [f["file"] for f in conflict["failed"]] == ["week11/fathom/additional/42/transcript.raw.json"]
    assert "immutable stored document" in conflict["failed"][0]["reason"] and conflict["unchanged"] == 1


def test_one_document_that_fails_to_normalise_stops_no_other_in_its_import(ready, folder, monkeypatch):
    # An import is one run with a document_normalise job per document (170 for the backfill). The first document that fails
    # must fail its own job only: the others are still claimed and normalised, and the run says how many failed.
    from backend_pipeline.documents import jobs as document_jobs
    repo, models, _ = ready
    real, seen = document_jobs.normalise, []

    def first_fails(repo_, transcript_id, **kwargs):
        seen.append(transcript_id)
        if len(seen) == 1:
            raise ValueError("Synthetic failure of one document")
        return real(repo_, transcript_id, **kwargs)
    monkeypatch.setattr(document_jobs, "normalise", first_fails)
    result = intake.import_directory(repo, folder)
    run_jobs(repo, models)
    with repo.connection() as conn:
        states = {r["transcript_id"]: r["status"] for r in conn.execute("SELECT transcript_id,status FROM pipeline_jobs WHERE run_id=%s", (result["run_id"],))}
        run = conn.execute("SELECT status,has_partial_failures FROM pipeline_runs WHERE run_id=%s", (result["run_id"],)).fetchone()
        normalised = {r["transcript_id"] for r in conn.execute("SELECT transcript_id FROM transcripts WHERE normalised_at IS NOT NULL")}
    assert states[seen[0]] == "failed" and sorted(states.values()) == ["completed"] * 3 + ["failed"], states
    assert normalised == set(result["transcript_ids"]) - {seen[0]}
    assert run["status"] == "partially_completed" and run["has_partial_failures"] is True


def test_a_document_has_no_week_and_its_original_bytes_are_in_the_store(ready, folder):
    repo, models, _ = ready
    intake.import_directory(repo, folder)
    from backend_pipeline.artifacts import store_for
    store = store_for(repo.settings)
    for row in documents(repo).values():
        assert row["week_id"] is None and row["normalised_at"] is None
        assert row["raw_object_key"] == f"source-originals/{row['content_hash']}.original" and store.exists(row["raw_object_key"])
        assert hashlib.sha256(store.read_bytes(row["raw_object_key"])).hexdigest() == row["content_hash"], "the exact bytes were archived"
    moved = folder.parent / "elsewhere"
    moved.mkdir()
    for f in folder.iterdir():
        (moved / ("copy-" + f.name)).write_bytes(f.read_bytes())
    assert intake.import_directory(repo, moved)["new"] == 0, "identity is the content, not the path or the name"


def test_the_normalise_job_classifies_resolves_dates_and_segments(ready, folder):
    repo, models, _ = ready
    intake.import_directory(repo, folder)
    run_jobs(repo, models)
    rows = documents(repo)
    client = next(r for t, r in rows.items() if "Personal Meeting Room" in t)
    assert client["call_type"] == "client_1to1" and client["included"] and client["exclusion_reason"] is None
    assert client["classification"]["method"] == "rule" and client["classification"]["rule_version"] == RULES_VERSION
    roles = {p["name"]: p["role"] for p in client["participants"]}
    assert roles == {"Carmen Cruickshank": "staff", "Dana Lee": "client"}
    carmen = client["speaker_map"]["Carmen Cruickshank"]
    assert carmen["basis"] == "name" and carmen["inferred"] is True and carmen["person_id"]
    assert client["speaker_map"]["Dana Lee"]["inferred"] is True
    assert client["occurred_at"] == datetime(2026, 3, 12, 15, 30, tzinfo=UTC) and client["occurred_at_source"] == "filename"
    internal = rows["Check-in with Gisselle.vtt"]
    assert (internal["call_type"], internal["included"]) == ("internal", False) and "Internal call" in internal["exclusion_reason"]
    fragment = rows["Zoom recording.vtt"]
    assert (fragment["call_type"], fragment["included"]) == ("fragment", False) and "Fragment" in fragment["exclusion_reason"]
    workshop = rows["Monthly Q&A workshop 2026-02-10.vtt"]
    assert workshop["call_type"] == "workshop" and workshop["included"] and workshop["occurred_at"].date() == date(2026, 2, 10)
    assert {p["name"]: p["role"] for p in workshop["participants"]}["Erin Smith"] == "client"
    # What is excluded is not segmented; what is included is, with a header.
    with repo.connection() as conn:
        chunks = conn.execute("SELECT * FROM transcript_chunks WHERE transcript_id=%s AND is_current", (client["transcript_id"],)).fetchall()
        assert conn.execute("SELECT count(*) n FROM transcript_chunks WHERE transcript_id=%s", (internal["transcript_id"],)).fetchone()["n"] == 0
    assert chunks and all(c["segmentation_version"] == "v2" for c in chunks)
    header = chunks[0]["header"]
    assert "Date: 2026-03-12" in header and "Type: Client call" in header
    assert "Carmen Cruickshank (WIA)" in header and "Dana Lee (client)" in header
    assert chunks[0]["chunk_text"].startswith(header) and chunks[0]["occurred_at"] == client["occurred_at"]
    assert {s["role"] for c in chunks for s in c["speaker_roles"]} == {"staff", "client"}


def test_stored_text_and_passages_are_never_changed_by_normalisation(ready, folder):
    repo, models, _ = ready
    intake.import_directory(repo, folder)
    with repo.connection() as conn:
        before = {r["transcript_id"]: (r["original_text"], r["passage_map"], r["content_hash"]) for r in conn.execute("SELECT * FROM transcripts")}
    run_jobs(repo, models)
    with repo.connection() as conn:
        after = {r["transcript_id"]: (r["original_text"], r["passage_map"], r["content_hash"]) for r in conn.execute("SELECT * FROM transcripts")}
    assert before == after


def test_each_passage_of_a_client_call_has_a_role_and_staff_are_recognised_by_name(ready, folder):
    repo, models, _ = ready
    intake.import_directory(repo, folder)
    run_jobs(repo, models)
    client = next(r for t, r in documents(repo).items() if "Personal Meeting Room" in t)
    from backend_pipeline.normalise import speakers
    roles = speakers.passage_roles(client, client["speaker_map"])
    assert len(roles) == len(client["passage_map"]) and set(roles) == {"staff", "client"} and "unknown" not in roles
    assert [p["speaker"] for p, role in zip(client["passage_map"], roles) if role == "staff"] == ["Carmen Cruickshank"] * 2


def test_a_search_for_a_product_finds_a_misspelt_segment_and_the_original_text_is_unchanged(ready, folder):
    repo, models, _ = ready
    intake.import_directory(repo, folder)
    run_jobs(repo, models)
    with repo.connection() as conn:
        client = conn.execute("SELECT * FROM transcripts WHERE title LIKE '%%Personal Meeting Room%%'").fetchone()
        hits = glossary_module.search(conn, "LeadLock")
        assert any(h["transcript_id"] == client["transcript_id"] for h in hits)
        assert "Lead Lock has helped a lot." in client["original_text"], "the speaker's words stay as spoken"
        chunk = conn.execute("SELECT * FROM transcript_chunks WHERE transcript_id=%s AND chunk_text LIKE '%%Lead Lock%%'",
                             (client["transcript_id"],)).fetchone()
        assert chunk is not None and "LeadLock has helped a lot." in chunk["search_text"] and "Lead Lock has helped a lot." in chunk["chunk_text"]
        # Without the glossary the misspelling is not found by the product name.
        conn.execute("DELETE FROM glossary_terms")
        glossary_module.refresh_search_text(conn)
        spelled = [h for h in glossary_module.search(conn, "Lead Lock") if h["transcript_id"] == client["transcript_id"]]
        assert spelled, "the literal spelling is still searchable"


def test_a_persons_classification_is_never_overwritten_by_a_rule(ready, folder):
    repo, models, _ = ready
    intake.import_directory(repo, folder)
    run_jobs(repo, models)
    internal = documents(repo)["Check-in with Gisselle.vtt"]
    with repo.connection() as conn:
        conn.execute("""UPDATE transcripts SET call_type='client_1to1',included=true,exclusion_reason=NULL,
            classification='{"method":"person","reason":"Whitney says this was a client check-in","decided_by":"whitney@example.invalid"}'
            WHERE transcript_id=%s""", (internal["transcript_id"],))
    result = normalise(repo, internal["transcript_id"], models=models)
    assert result["method"] == "person" and result["call_type"] == "client_1to1" and result["included"] is True
    again = documents(repo)["Check-in with Gisselle.vtt"]
    assert again["classification"]["decided_by"] == "whitney@example.invalid"


def test_normalising_again_changes_nothing(ready, folder):
    repo, models, _ = ready
    intake.import_directory(repo, folder)
    run_jobs(repo, models)
    with repo.connection() as conn:
        ids = {r["transcript_id"]: r["chunk_id"] for r in conn.execute("SELECT transcript_id,chunk_id FROM transcript_chunks WHERE is_current")}
    for transcript_id in {r["transcript_id"] for r in documents(repo).values()}:
        normalise(repo, transcript_id, models=models)
    with repo.connection() as conn:
        again = {r["transcript_id"]: r["chunk_id"] for r in conn.execute("SELECT transcript_id,chunk_id FROM transcript_chunks WHERE is_current")}
        assert conn.execute("SELECT count(*) n FROM transcript_chunks").fetchone()["n"] == len(ids) >= 2
    assert again == ids


def test_a_new_date_adds_new_chunks_and_retires_the_old_ones_which_stay_readable(ready, folder):
    repo, models, _ = ready
    intake.import_directory(repo, folder)
    run_jobs(repo, models)
    client = next(r for t, r in documents(repo).items() if "Personal Meeting Room" in t)
    with repo.connection() as conn:
        old = {r["chunk_id"] for r in conn.execute("SELECT chunk_id FROM transcript_chunks WHERE transcript_id=%s AND is_current", (client["transcript_id"],))}
        conn.execute("UPDATE transcripts SET occurred_at='2026-03-13T10:00:00Z',occurred_at_source='manual' WHERE transcript_id=%s", (client["transcript_id"],))
    normalise(repo, client["transcript_id"], models=models)
    with repo.connection() as conn:
        new = {r["chunk_id"] for r in conn.execute("SELECT chunk_id FROM transcript_chunks WHERE transcript_id=%s AND is_current", (client["transcript_id"],))}
        retired = {r["chunk_id"] for r in conn.execute("SELECT chunk_id FROM transcript_chunks WHERE transcript_id=%s AND NOT is_current", (client["transcript_id"],))}
        assert conn.execute("SELECT occurred_at_source FROM transcripts WHERE transcript_id=%s", (client["transcript_id"],)).fetchone()["occurred_at_source"] == "manual"
    assert old.isdisjoint(new) and retired == old, "the date is in the header, so the chunks are new rows; the old ones remain"


def test_no_date_is_derived_from_a_week(ready, tmp_path):
    repo, models, _ = ready
    folder = tmp_path / "weekly"
    folder.mkdir()
    (folder / "Untitled call.vtt").write_text(CLIENT_CALL, encoding="utf-8")
    repo.admit(folder, date(2026, 6, 1), 1)
    with repo.connection() as conn:
        row = conn.execute("SELECT transcript_id FROM transcripts WHERE title='Untitled call.vtt'").fetchone()
    result = normalise(repo, row["transcript_id"], models=models)
    assert result["dated"] == "unknown"
    with repo.connection() as conn:
        doc = conn.execute("SELECT * FROM transcripts WHERE transcript_id=%s", (row["transcript_id"],)).fetchone()
        assert doc["occurred_at"] is None and doc["occurred_at_source"] == "unknown" and doc["week_id"] == "week_2026-06-01"
        from backend_pipeline.normalise import dates
        assert dates.report(conn)["unknown"] == 1


def test_a_week_folder_bounds_a_spoken_day_and_the_evidence_is_kept_beside_the_date(ready, tmp_path):
    """1.B11: the folder's week is a window. A greeting dates a call to its day inside it; a call with nothing better is
    dated to the week (date_evidence keeps the window, occurred_at stays null); a person's date is never replaced."""
    from backend_pipeline.normalise import dates
    repo, models, _ = ready
    greeting = vtt(("Carmen Cruickshank", f"Happy Wednesday, Dana! {FILLER}"), ("Dana Lee", f"Thanks Carmen. {FILLER}"),
                   ("Carmen Cruickshank", f"Let us review the follow-up. {FILLER}"))
    for name, text, start, index in (("Spoken day call.vtt", greeting, date(2026, 6, 15), 3),
                                     ("Plain week call.vtt", CLIENT_CALL, date(2026, 6, 22), 4)):
        folder = tmp_path / f"week{index}"
        folder.mkdir()
        (folder / name).write_text(text, encoding="utf-8")
        repo.admit(folder, start, index)
    with repo.connection() as conn:
        ids = {r["title"]: r["transcript_id"] for r in conn.execute("SELECT title,transcript_id FROM transcripts WHERE source_metadata->>'week_index' IN ('3','4')")}
    for transcript_id in ids.values():
        normalise(repo, transcript_id, models=models)
    with repo.connection() as conn:
        rows = {r["title"]: r for r in conn.execute("SELECT * FROM transcripts WHERE transcript_id = ANY(%s)", (list(ids.values()),))}
        spoken, plain = rows["Spoken day call.vtt"], rows["Plain week call.vtt"]
        assert spoken["occurred_at"] == datetime(2026, 6, 17, 17, tzinfo=UTC) and spoken["occurred_at_source"] == "content"
        assert "Happy Wednesday" in spoken["date_evidence"]["detail"] and spoken["date_evidence"]["window"]["basis"].startswith("week folder 3")
        assert plain["occurred_at"] is None and plain["occurred_at_source"] == "unknown"
        assert plain["date_evidence"]["window"]["start"].startswith("2026-06-22T00:00:00+05:30") and plain["date_evidence"]["conflicts"] == []
        report = dates.report(conn)
        assert report["dated_to_week"] >= 1 and report["by_source"].get("content") == 1
        conn.execute("UPDATE transcripts SET occurred_at='2026-06-16T15:00:00Z',occurred_at_source='manual',date_evidence=NULL WHERE transcript_id=%s",
                     (spoken["transcript_id"],))
        assert dates.apply(conn, spoken["transcript_id"], dates.resolve(spoken)) is False
        kept = conn.execute("SELECT occurred_at,date_evidence FROM transcripts WHERE transcript_id=%s", (spoken["transcript_id"],)).fetchone()
        assert kept["occurred_at"] == datetime(2026, 6, 16, 15, tzinfo=UTC) and kept["date_evidence"] is None


def test_a_copy_of_an_admitted_week_document_is_linked_to_it_and_excluded(ready, tmp_path):
    repo, models, _ = ready
    weekly = tmp_path / "weekly"
    weekly.mkdir()
    (weekly / "Carmen call.vtt").write_text(CLIENT_CALL, encoding="utf-8")
    repo.admit(weekly, date(2026, 6, 1), 1)
    drop = tmp_path / "drop2"
    drop.mkdir()
    (drop / "Carmen call (another download).vtt").write_text(CLIENT_CALL, encoding="utf-8")
    intake.import_directory(repo, drop)
    run_jobs(repo, models)
    with repo.connection() as conn:
        admitted = conn.execute("SELECT * FROM transcripts WHERE title='Carmen call.vtt'").fetchone()
        copy = conn.execute("SELECT * FROM transcripts WHERE title='Carmen call (another download).vtt'").fetchone()
    assert copy["canonical_document_id"] == admitted["transcript_id"] and copy["included"] is False
    assert "Duplicate of" in copy["exclusion_reason"] and copy["extraction_status"] == "not_applicable"
    normalise(repo, admitted["transcript_id"], models=models)
    with repo.connection() as conn:
        again = conn.execute("SELECT canonical_document_id,included FROM transcripts WHERE transcript_id=%s", (admitted["transcript_id"],)).fetchone()
        assert again["canonical_document_id"] is None and again["included"] is True, "the original stays the canonical one"


def test_classification_agreement_with_the_corpus_index_names_each_disagreement():
    from backend_pipeline.normalise.classify import agreement
    result = agreement([("a", "client_1to1", "client"), ("b", "office_hours", "client"), ("c", "internal", "internal"),
                        ("d", "fragment", "internal"), ("e", "workshop", "workshop"), ("f", "client_1to1", "internal")])
    assert result["compared"] == 6 and result["agree"] == 4
    assert [d["document"] for d in result["disagreements"]] == ["d", "f"]
    assert json.dumps(result)
