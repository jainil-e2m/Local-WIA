"""1.B14: one normaliser per source. The same Fathom call from the API and from native JSON gives identical passages,
identifiers and speaker emails; Slack messages group by thread; every passage resolves to its original text."""
from __future__ import annotations

import hashlib
import json

import pytest
from test_transcript_backfill import native_source

from backend_pipeline.fathom_sources import capture_fathom
from backend_pipeline.intake.normalize import fathom as live_fathom
from backend_pipeline.normalise.sources import fathom_document, slack_threads, timestamp_ms


def api_view(path):
    """What intake builds for the same recording: the provider metadata and the transcript payload from the API."""
    envelope = json.loads(path.with_name("metadata.json").read_bytes())
    raw = path.read_bytes()
    return live_fathom(envelope["source_metadata"], json.loads(raw), "source_internal_id", hashlib.sha256(raw).hexdigest())


def test_the_same_fathom_call_from_the_api_and_from_native_json_is_identical(tmp_path):
    path, _ = native_source(tmp_path)
    native = capture_fathom(path, 11, 1)
    live = api_view(path)
    assert native["passage_map"] == live["passage_map"], "passages and identifiers"
    assert [p["speaker_email"] for p in native["passage_map"]] == ["speaker@example.test", None]
    assert [p["speaker_email"] for p in live["passage_map"]] == ["speaker@example.test", None]
    for key in ("transcript_id", "source_type", "upstream_id", "title", "original_text", "content_hash", "occurred_at"):
        assert native[key] == live[key], key
    assert native["upstream_id"] == "fathom:42" and native["passage_map"][0]["passage_id"] == "fathom:42:span:0"
    assert native["occurred_at_source"] == live["occurred_at_source"] == "provider"


def test_admission_extras_sit_beside_the_shared_metadata(tmp_path):
    path, _ = native_source(tmp_path)
    native, live = capture_fathom(path, 11, 1), api_view(path)
    assert native["source_metadata"]["week_index"] == 11 and "week_index" not in live["source_metadata"]
    assert native["source_metadata"]["packet_metadata"]["date"] == "2026-08-13"
    assert live["source_metadata"]["provider_metadata"] == native["source_metadata"]["provider_metadata"]
    assert native["use_restrictions"] is None and live["use_restrictions"]["public_use"] is False


@pytest.mark.parametrize("fault", ["no_id", "naive_time", "empty", "backwards", "bad_stamp", "blank_text"])
def test_a_malformed_fathom_call_is_refused(fault):
    meeting = {"recording_id": 7, "title": "x", "recording_start_time": "2026-08-12T19:01:00Z"}
    segments = [{"timestamp": "00:00:01", "text": "a", "speaker": {"display_name": "A"}},
                {"timestamp": "00:00:09", "text": "b", "speaker": {"display_name": "B"}}]
    if fault == "no_id":
        meeting.pop("recording_id")
    elif fault == "naive_time":
        meeting["recording_start_time"] = "2026-08-12T19:01:00"
    elif fault == "empty":
        segments = []
    elif fault == "backwards":
        segments[1]["timestamp"] = "00:00:00"
    elif fault == "bad_stamp":
        segments[1]["timestamp"] = "nine"
    else:
        segments[1]["text"] = "   "
    with pytest.raises(ValueError):
        fathom_document(meeting, {"transcript": segments}, "abc")


def test_timestamps_parse_with_fractions():
    assert timestamp_ms("01:02:03") == 3_723_000 and timestamp_ms("00:02:00.25") == 120_250
    with pytest.raises(ValueError):
        timestamp_ms("2:3")


def messages():
    return [
        {"ts": "1760000000.000100", "text": "Has anyone seen the new template?", "user": "U1"},
        {"ts": "1760000100.000200", "text": "Yes, it is in the drive.", "user": "U2", "thread_ts": "1760000000.000100"},
        {"ts": "1760000050.000300", "text": "Unrelated: lunch?", "user": "U3"},
        {"ts": "1760000200.000400", "text": "Thanks!", "user": "U1", "thread_ts": "1760000000.000100"},
        {"ts": "1760000300.000500", "text": "   ", "user": "U1"},
        {"ts": "1760000400.000600", "text": "gone", "user": "U2", "deleted": True},
    ]


def test_slack_messages_group_by_thread_one_document_each():
    documents = slack_threads(messages(), "C1", workspace="T1", channel_name="wia-general")
    assert [d["source_metadata"]["slack"]["thread_ts"] for d in documents] == ["1760000000.000100", "1760000050.000300"]
    thread = documents[0]
    assert thread["source_metadata"]["slack"]["message_count"] == 3
    assert [p["locator"]["ts"] for p in thread["passage_map"]] == ["1760000000.000100", "1760000100.000200", "1760000200.000400"]
    assert thread["title"].startswith("Slack #wia-general")
    assert thread["upstream_id"] == "slack:T1:C1:1760000000.000100" and thread["week_id"] is None
    assert thread["occurred_at"].isoformat().startswith("2025-10-09") and thread["occurred_at_source"] == "provider"


def test_every_slack_passage_resolves_to_the_original_message_text():
    by_ts = {m["ts"]: m for m in messages()}
    for document in slack_threads(messages(), "C1", workspace="T1"):
        for passage in document["passage_map"]:
            assert document["original_text"][passage["start"]:passage["end"]] == by_ts[passage["locator"]["ts"]]["text"]


def test_a_thread_of_blank_or_deleted_messages_makes_no_document():
    assert slack_threads([m for m in messages() if m["ts"] in {"1760000300.000500", "1760000400.000600"}], "C1") == []


def test_regrouping_the_same_messages_is_stable_and_a_reply_makes_a_new_revision():
    first = slack_threads(messages(), "C1", workspace="T1")
    again = slack_threads(list(reversed(messages())), "C1", workspace="T1")
    assert [d["transcript_id"] for d in first] == [d["transcript_id"] for d in again], "order of delivery does not matter"
    more = messages() + [{"ts": "1760000500.000700", "text": "One more reply", "user": "U2", "thread_ts": "1760000000.000100"}]
    changed = slack_threads(more, "C1", workspace="T1")
    assert changed[0]["transcript_id"] != first[0]["transcript_id"] and changed[1]["transcript_id"] == first[1]["transcript_id"]
