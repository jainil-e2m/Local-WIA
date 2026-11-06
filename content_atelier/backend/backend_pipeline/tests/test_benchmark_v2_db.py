"""E.B27 (packets): benchmark v2's packets are whole weeks from the moments ledger, built with no model call, each reporting
its scene coverage; an unextracted call leaves the packet pending; a do_not_use scene is counted, never sent; v1 stays."""
from __future__ import annotations

import json
from datetime import UTC, date, datetime

from psycopg.types.json import Jsonb

from backend_pipeline.database import connect
from backend_pipeline.tests.platform_db import empty, platform_url  # noqa: F401
from evaluation import packets, run

TEXT = "Alice: We moved the budget to search first.\nBob: I had no idea what changed.\nAlice: Then we checked the tracking.\n"


def document(conn, tid, *, week_id="week_2026-06-08", included=True, status="completed", call_type="client_1to1",
             occurred=datetime(2026, 6, 9, 15, tzinfo=UTC)):
    if week_id:
        conn.execute("INSERT INTO weeks(week_id,week_start,week_end) VALUES (%s,'2026-06-08','2026-06-14') ON CONFLICT DO NOTHING",
                     (week_id,))
    lines, start, passages = TEXT.splitlines(keepends=True), 0, []
    for i, line in enumerate(lines):
        passages.append({"passage_id": f"{tid}:span:{i}", "start": start, "end": start + len(line.rstrip("\n")), "kind": "cue",
                         "speaker": line.split(":")[0], "start_ms": 1000 * (10 + i), "end_ms": 1000 * (12 + i)})
        start += len(line)
    conn.execute("""INSERT INTO transcripts(transcript_id,week_id,source_type,title,occurred_at,original_text,passage_map,
            content_hash,call_type,included,exclusion_reason,extraction_status) VALUES (%s,%s,'zoom',%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                 (tid, week_id, f"Call {tid}", occurred, TEXT, Jsonb(passages), "sha256:" + tid, call_type, included,
                  None if included else "Internal call: only WIA staff speak, so it is not client evidence.", status))
    return passages


def scene(conn, mid, tid, passages, i, *, kind="observation", verified=True, consent="anonymise"):
    p = passages[i]
    conn.execute("""INSERT INTO key_moments(moment_id,week_id,moment_body,evidence_refs,document_id,moment_type,quote_verified,
            unverified_reason,consent_status,is_current,extractor_version) VALUES (%s,NULL,%s,%s,%s,%s,%s,%s,%s,true,
            '2026-10-23.scenes.v3')""",
                 (mid, Jsonb({"quote": TEXT[p["start"]:p["end"]], "moment_type": kind, "proposition": "x", "sensitivity": "unknown"}),
                  Jsonb([{"passage_id": p["passage_id"], "transcript_id": tid, "start": p["start"], "end": p["end"],
                          "roles": ["anchor", "context"]}]), tid, kind, verified, None if verified else "quote not found", consent))


def test_a_whole_week_packet_lists_every_call_and_every_verified_scene(platform_url):  # noqa: F811
    empty(platform_url)
    with connect(platform_url, vectors=False) as conn:
        a = document(conn, "transcript_a")
        b = document(conn, "transcript_b")
        document(conn, "transcript_internal", included=False, status="not_applicable", call_type="internal")
        scene(conn, "moment_1", "transcript_a", a, 0, kind="counter_expected_decision")
        scene(conn, "moment_2", "transcript_a", a, 2)
        scene(conn, "moment_3", "transcript_b", b, 1, kind="human_line")
        scene(conn, "moment_4", "transcript_b", b, 0, verified=False)
        scene(conn, "moment_5", "transcript_b", b, 2, consent="do_not_use")
        built = packets.build(conn, "week2")
    summary = built["coverage"]["summary"]
    assert built["state"] == "complete" and built["window"]["week_id"] == "week_2026-06-08"
    assert summary["calls"] == 3 and summary["included_calls"] == 2 and summary["excluded_calls"] == 1
    assert summary["verified_scenes"] == 4 and summary["in_packet"] == 3 and summary["held_for_consent"] == 1
    assert summary["every_verified_scene_in_packet"] and summary["within_budget"]
    # Human lines and counter-expected decisions first (E.B31), each scene with the passages it was cut from.
    assert [m["moment_id"] for m in built["scenes"]] == ["moment_1", "moment_3", "moment_2"]
    assert built["scenes"][1]["source_evidence"] == [{"span_id": "transcript_b:span:1", "text": "Bob: I had no idea what changed.",
                                                      "speaker": "Bob", "start_seconds": 11}]
    excluded = next(d for d in built["coverage"]["documents"] if not d["included"])
    assert excluded["state"] == "excluded" and excluded["exclusion_reason"].startswith("Internal call")
    assert built["reference"]["made_by"].startswith("hand-built") and "made_by" in built


def test_a_window_with_an_unextracted_call_is_pending_and_the_harness_refuses_it(platform_url, tmp_path, monkeypatch):  # noqa: F811
    empty(platform_url)
    with connect(platform_url, vectors=False) as conn:
        a = document(conn, "transcript_oct", week_id=None, occurred=datetime(2026, 10, 14, 15, tzinfo=UTC))
        scene(conn, "moment_oct", "transcript_oct", a, 0)
        document(conn, "transcript_waiting", week_id=None, status="pending", occurred=datetime(2026, 10, 15, 15, tzinfo=UTC))
        built = packets.build(conn, "october", start=date(2026, 10, 12), end=date(2026, 10, 19), budget_tokens=10)
    assert built["state"] == "pending" and built["coverage"]["summary"]["pending_extraction"] == ["transcript_waiting"]
    assert not built["coverage"]["summary"]["within_budget"], "reported, never cut"
    assert "reference" not in built, "no prompt and no reference has seen the held-out window"
    monkeypatch.setattr(packets, "OUT", tmp_path)
    packets.write(built, tmp_path)
    monkeypatch.setattr("evaluation.packets.load", lambda name, out=tmp_path: json.loads((tmp_path / f"{name}.json").read_text(encoding="utf-8")))
    try:
        run.packet("october_v2")
    except ValueError as error:
        assert "pending" in str(error)
    else:
        raise AssertionError("a pending packet must not be run")
    # Benchmark v1 stays for replay.
    assert run.packet("week2") and run.packet("week2")[0]["source_evidence"]
