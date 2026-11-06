import hashlib
import json
import os
from datetime import date

import pytest

from backend_pipeline.backfill import source_plan
from backend_pipeline.fathom_sources import capture_fathom
from backend_pipeline.repository import ContentRepository
from backend_pipeline.storage_config import StorageSettings
from backend_pipeline.storage_sources import capture, chunks, reconstruct
from backend_pipeline.tests.test_sql_storage import setup as sql_setup  # noqa: F401


def native_source(tmp_path, *, week=11, selection=True):
    folder = tmp_path / f"week{week}" / "fathom" / "additional" / "42"
    folder.mkdir(parents=True)
    raw = {
        "transcript": [
            {
                "timestamp": "00:00:01",
                "speaker": {"display_name": "Full Speaker Name", "matched_calendar_invitee_email": "speaker@example.test"},
                "text": "Exact first line.\nSecond line remains intact.",
            },
            {
                "timestamp": "00:02:00.250",
                "speaker": {"display_name": "Another Speaker"},
                "text": "Later turn after the conversational gap.",
            },
        ]
    }
    path = folder / "transcript.raw.json"
    path.write_text(json.dumps(raw), encoding="utf-8")
    metadata = {
        "source_type": "fathom",
        "classification": "additional",
        "selected_as_additional_source": selection,
        "recording_id": 42,
        "week": week,
        "occurrence_ist": "2026-08-13T00:31:00+05:30",
        "transcript_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "source_metadata": {
            "recording_id": 42,
            "recording_start_time": "2026-08-12T19:01:00Z",
            "meeting_title": "Native call",
            "url": "https://example.test/42",
        },
    }
    path.with_name("metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
    return path, raw


def test_native_segments_reconstruct_exactly_with_unknown_end_times(tmp_path):
    path, raw = native_source(tmp_path)
    record = capture(path, 11, 1)
    assert record["source_type"] == "fathom" and record["upstream_id"] == "fathom:42"
    for passage, segment in zip(record["passage_map"], raw["transcript"], strict=True):
        assert passage["end_ms"] is None
        assert record["original_text"][passage["start"] : passage["end"]] == (
            segment["speaker"]["display_name"] + ": " + segment["text"]
        )
    assert record["passage_map"][1]["start_ms"] == 120250
    assert len(chunks(record)) == 2
    transcripts, packet, refs = reconstruct([record])
    assert transcripts[0].source_format == "timestamped_text"
    assert transcripts[0].spans[0].end_seconds is None
    assert "TIMESTAMPED " in packet and '"end_ms":null' in packet
    assert len(refs) == 2


def test_native_identity_stays_stable_when_the_file_moves(tmp_path):
    path, _ = native_source(tmp_path)
    first = capture_fathom(path, 11, 1)
    moved = tmp_path / "another-location"
    moved.mkdir()
    for name in ("transcript.raw.json", "metadata.json"):
        (moved / name).write_bytes(path.with_name(name).read_bytes())
    assert capture_fathom(moved / "transcript.raw.json", 11, 1) == first


@pytest.mark.parametrize("fault", ["unselected", "hash", "timestamp", "backwards", "identity"])
def test_native_admission_rejects_corrupt_or_unselected_sources(tmp_path, fault):
    path, raw = native_source(tmp_path)
    meta_path = path.with_name("metadata.json")
    metadata = json.loads(meta_path.read_text())
    if fault == "unselected":
        metadata["selected_as_additional_source"] = False
    elif fault == "hash":
        metadata["transcript_sha256"] = "changed"
    elif fault == "identity":
        metadata["source_metadata"]["recording_id"] = 99
    else:
        raw["transcript"][1]["timestamp"] = "invalid" if fault == "timestamp" else "00:00:00"
        path.write_text(json.dumps(raw), encoding="utf-8")
        metadata["transcript_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    meta_path.write_text(json.dumps(metadata), encoding="utf-8")
    with pytest.raises(ValueError):
        capture_fathom(path, 11, 1)


def test_selection_deduplicates_zoom_and_excludes_alternate_fathom(tmp_path):
    for week in (10, 11):
        folder = tmp_path / f"week{week}"
        folder.mkdir()
        (folder / "same.vtt").write_text("WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nA: Same original.\n")
    path, _ = native_source(tmp_path)
    reconciliation = {
        "sources": [
            {
                "category": "additional",
                "selected_as_additional_source": True,
                "week": 11,
                "folder": str(path.parent),
                "raw_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            },
            {"category": "zoom-overlap", "selected_as_additional_source": False, "folder": "must-not-be-read"},
        ]
    }
    plan, excluded = source_plan(tmp_path, reconciliation, duplicate_week=10)
    assert [w["week"] for w in plan] == [10, 11]
    assert plan[0]["records"][0]["source_type"] == "zoom"
    assert plan[1]["records"][0]["source_type"] == "fathom"
    assert excluded[0]["week"] == 11 and excluded[0]["selected_week"] == 10
    assert len(plan[0]["chunks"]) == 1


def test_admission_rejects_wrong_ist_week_before_any_database_connection(tmp_path):
    path, _ = native_source(tmp_path)
    repo = ContentRepository(StorageSettings())
    with pytest.raises(ValueError, match="outside the assigned IST week"):
        repo.admit(path.parents[3], date(2026, 8, 3), 11, selected_paths=[path])


@pytest.mark.skipif(not os.getenv("ATELIER_TEST_DATABASE_URL"), reason="Requires isolated atelier_test")
def test_sql_native_admission_and_embedding_only_reuse(request):
    from backend_pipeline.chunk_encoding import queue
    from backend_pipeline.sql_pipeline import SQLWorker
    from backend_pipeline.tests.test_chunk_encoding import BatchProvider

    repo, models, tmp_path = request.getfixturevalue('sql_setup')
    path, _ = native_source(tmp_path)
    week = "week_2026-08-10"
    repo.admit(path.parents[3], date(2026, 8, 10), 11, selected_paths=[path])
    provider = BatchProvider()
    worker = SQLWorker(repo.settings, models, provider=provider)
    queued = queue(repo, models, week)
    worker.once(run_id=queued["run_id"])
    with repo.connection() as conn:
        source = conn.execute("SELECT * FROM transcripts WHERE week_id=%s", (week,)).fetchone()
        assert source["source_type"] == "fathom"
        assert all(p["end_ms"] is None for p in source["passage_map"])
        assert (
            conn.execute(
                "SELECT count(*) n FROM transcript_chunks WHERE transcript_id=%s AND embedding IS NOT NULL",
                (source["transcript_id"],),
            ).fetchone()["n"]
            == 2
        )
        assert conn.execute("SELECT count(*) n FROM key_moments").fetchone()["n"] == 0
        assert conn.execute("SELECT count(*) n FROM content_angles").fetchone()["n"] == 0
    assert len(provider.calls) == 1
    assert queue(repo, models, week) == queued
    assert worker.once(run_id=queued["run_id"]) is None
    assert len(provider.calls) == 1
