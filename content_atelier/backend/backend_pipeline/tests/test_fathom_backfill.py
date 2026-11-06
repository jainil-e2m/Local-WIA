"""6.B18: Fathom calls from before the collector's activation, as documents (documents fathom-backfill).

The Fathom API is replayed from recorded responses, anonymised: the shape of the October 2026 listing and transcripts (keys,
types, pagination, a second note-taker's recording of one meeting, a transcript not yet published), with invented people and
words. No network and no model call."""
from __future__ import annotations

import hashlib
import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import httpx
import pytest

from backend_pipeline.documents import fathom_backfill as backfill
from backend_pipeline.intake.config import IntakeSettings, fathom_api_key
from backend_pipeline.intake.fathom import FathomClient
from backend_pipeline.tests.platform_db import platform_setup, platform_url  # noqa: F401 (fixtures)

# ---- recorded responses (anonymised) ----------------------------------------------------------------------------------

WORDS = {
    "team": ("we reviewed the lead form follow up numbers for the month and agreed to test a shorter first reply",
             "the venue clients answered faster when the first message named the date and asked one question",
             "next week we compare the booked calls against the inquiries from the new landing page"),
    "kickoff": ("welcome to the kickoff we will set up the campaign and the tracking before any spend goes live",
                "our photographers book most couples in spring so the budget should lean into january and february",
                "send the gallery links and the price guide so the ads can point at real work"),
    "strategy": ("this month the cost per inquiry dropped after we paused the broad audience and kept the lookalike",
                 "the planner said couples ask about the timeline first so the landing page should open with it",
                 "we will rewrite the headline and test two offers against each other for three weeks"),
}


def meeting(rid, start, title, *, created=None, recorder="host@example.test"):
    begin = datetime.fromisoformat(start)
    return {"title": title, "meeting_title": title, "meeting_type": "external", "url": f"https://fathom.example.test/calls/{rid}",
            "meeting_url": "https://zoom.example.test/j/1", "created_at": (created or begin + timedelta(minutes=40)).isoformat().replace("+00:00", "Z"),
            "scheduled_start_time": start, "scheduled_end_time": (begin + timedelta(minutes=45)).isoformat().replace("+00:00", "Z"),
            "recording_id": rid, "recording_start_time": start, "recording_end_time": (begin + timedelta(minutes=38)).isoformat().replace("+00:00", "Z"),
            "calendar_invitees_domains_type": "one_or_more_external", "shared_with": "team", "transcript": None, "transcript_language": "en",
            "default_summary": None, "action_items": None, "highlights": None,
            "calendar_invitees": [{"name": "Alex Rivera", "email": "alex@example.test", "email_domain": "example.test", "is_external": False,
                                   "matched_speaker_display_name": None}],
            "recorded_by": {"name": "Host", "email": recorder, "email_domain": "example.test", "team": "Ads"},
            "share_url": f"https://fathom.example.test/share/{rid}", "crm_matches": None}


def transcript(topic, *, turns=9, speakers=("Alex Rivera", "Sam Example")):
    lines = [WORDS[topic][i % 3] for i in range(turns)]
    return {"transcript": [{"speaker": {"display_name": speakers[i % 2], "matched_calendar_invitee_email": f"p{i % 2}@example.test"},
                            "text": line.capitalize() + ".", "timestamp": f"00:{i:02d}:{i + 1:02d}"} for i, line in enumerate(lines)]}


MEETINGS = [
    meeting(9001, "2026-10-05T17:01:42Z", "Zoom Meeting"),  # a title that says nothing: the call waits for a person
    meeting(9002, "2026-10-05T17:02:10Z", "Weekly Ads Call", recorder="second@example.test"),  # the same meeting, a second note-taker
    meeting(9003, "2026-10-07T14:30:49Z", "Ads Kickoff Call | Studio Example"),                        # also a Zoom document already
    meeting(9004, "2026-10-08T15:00:00Z", "Monthly Strategy Call"),
    meeting(9005, "2026-10-20T15:00:00Z", "After the window", created=datetime(2026, 10, 20, 15, 40, tzinfo=UTC)),
    meeting(9006, "2026-10-04T23:00:00Z", "Before the window (4 October in Texas)"),
    meeting(9007, "2026-10-09T16:00:00Z", "Already imported from a week packet"),
    meeting(9008, "2026-10-14T17:00:00Z", "Transcript not published yet"),
]
TRANSCRIPTS = {9001: transcript("team"), 9002: transcript("team", turns=6), 9003: transcript("kickoff"), 9004: transcript("strategy"),
               9007: transcript("strategy", turns=6, speakers=("Robin Example", "Sam Example"))}


def fathom(calls=None, meetings=MEETINGS, transcripts=TRANSCRIPTS, *, rate_limited=()):
    """A MockTransport replaying the API: two pages of meetings filtered by created_after/created_before, and transcripts."""
    limited = list(rate_limited)

    def respond(request):
        if calls is not None:
            calls.append(request)
        if request.url.path.endswith("/meetings"):
            after = datetime.fromisoformat(request.url.params["created_after"])
            before = datetime.fromisoformat(request.url.params["created_before"])
            items = [m for m in meetings if after <= datetime.fromisoformat(m["created_at"]) < before]
            if request.url.params.get("cursor") == "page2":
                return httpx.Response(200, json={"items": items[3:], "next_cursor": None, "limit": 3})
            return httpx.Response(200, json={"items": items[:3], "next_cursor": "page2" if len(items) > 3 else None, "limit": 3})
        rid = int(request.url.path.split("/")[-2])
        if rid in limited:
            limited.remove(rid)
            return httpx.Response(429, headers={"retry-after": "0"})
        if rid not in transcripts:
            return httpx.Response(404)
        return httpx.Response(200, content=json.dumps(transcripts[rid]).encode())
    return FathomClient(IntakeSettings(fathom_key="fathom-test-secret"), httpx.MockTransport(respond))


WINDOW = backfill.window(date(2026, 10, 5), date(2026, 10, 19), "America/Chicago")


# ---- offline ----------------------------------------------------------------------------------------------------------

def test_the_fathom_key_is_read_under_either_name():
    assert fathom_api_key({"FATHOM_API_KEY": "local"}) == "local"
    assert fathom_api_key({"ATELIER_FATHOM_API_KEY": "deployed", "FATHOM_API_KEY": "local"}) == "deployed"
    assert fathom_api_key({"ATELIER_FATHOM_API_KEY": "", "FATHOM_API_KEY": "local"}) == "local"
    assert fathom_api_key({}) == ""


def test_the_fathom_key_reaches_the_intake_settings(monkeypatch):
    from backend_pipeline import settings_store
    monkeypatch.delenv("ATELIER_FATHOM_API_KEY", raising=False)
    monkeypatch.setenv("FATHOM_API_KEY", "from-backend-env")
    settings = IntakeSettings.from_effective(settings_store.load(environ={}, read_files=False, rows={}))
    assert settings.fathom_key == "from-backend-env"


def test_the_window_is_whole_days_in_the_named_zone():
    start, end = WINDOW
    assert start.isoformat() == "2026-10-05T00:00:00-05:00" and end.isoformat() == "2026-10-20T00:00:00-05:00"
    with pytest.raises(ValueError, match="ends before"):
        backfill.window(date(2026, 10, 19), date(2026, 10, 5), "UTC")


def test_the_meetings_listed_are_the_ones_recorded_in_the_window_across_pages():
    calls = []
    client = fathom(calls)
    listed = backfill.list_meetings(client, *WINDOW)
    assert [m["recording_id"] for m in listed] == [9001, 9002, 9003, 9004, 9007, 9008]
    pages = [c for c in calls if c.url.path.endswith("/meetings")]
    assert len(pages) == 2 and pages[1].url.params["cursor"] == "page2"
    # A call recorded on the window's last evening is created after it: the listing asks two days past the window.
    assert datetime.fromisoformat(pages[0].url.params["created_before"]) == WINDOW[1] + timedelta(days=2)


def test_a_written_folder_imports_with_the_live_collectors_identity(tmp_path):
    from backend_pipeline.fathom_sources import capture_fathom
    from backend_pipeline.intake.normalize import fathom as live
    raw = json.dumps(TRANSCRIPTS[9001]).encode()
    folder = tmp_path / "2026-10-05" / "9001"
    backfill.write_folder(folder, MEETINGS[0], raw, collected_at=datetime(2026, 10, 22, tzinfo=UTC))
    assert backfill.written(folder) and (folder / "transcript.raw.json").read_bytes() == raw
    envelope = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
    assert envelope["occurrence_ist"] == "2026-10-05T22:31:42+05:30" and envelope["source_metadata"] == MEETINGS[0]
    imported = capture_fathom(folder / "transcript.raw.json", None, 0)
    collected = live(MEETINGS[0], TRANSCRIPTS[9001], "source_x", hashlib.sha256(raw).hexdigest())
    assert imported["transcript_id"] == collected["transcript_id"] and imported["upstream_id"] == "fathom:9001"
    assert imported["original_text"] == collected["original_text"] and imported["occurred_at"] == datetime(2026, 10, 5, 17, 1, 42, tzinfo=UTC)
    (folder / "transcript.raw.json").write_bytes(raw + b" ")
    assert not backfill.written(folder), "a folder whose bytes differ from its envelope is fetched again"
    with pytest.raises(ValueError, match="no recording start time"):
        backfill.envelope({**MEETINGS[0], "recording_start_time": None}, raw, collected_at=datetime.now(UTC))


def test_two_transcriptions_of_one_call_share_their_wording_and_two_calls_do_not():
    team = backfill.text_of(MEETINGS[0], json.dumps(TRANSCRIPTS[9001]).encode())
    second = backfill.text_of(MEETINGS[1], json.dumps(TRANSCRIPTS[9002]).encode())
    other = backfill.text_of(MEETINGS[3], json.dumps(TRANSCRIPTS[9004]).encode())
    assert backfill.same_call(team, second) == 1.0
    assert backfill.same_call(team, other) < 0.05
    # Another engine's transcription of the same words, with its own labels and a few words heard differently.
    zoom = "Robin: " + " ".join(WORDS["team"]).replace("shorter", "short").replace("landing page", "landing-page")
    assert backfill.same_call(team, zoom) >= backfill.SAME_CALL_SHARE
    assert backfill.same_call("", team) == 0.0


def test_a_rate_limited_transcript_is_fetched_again():
    waits = []
    client = fathom(rate_limited=[9001, 9001])
    assert backfill.fetch(client, 9001, sleep=waits.append) == json.dumps(TRANSCRIPTS[9001]).encode()
    assert waits == [0.0, 0.0]
    with pytest.raises(httpx.HTTPStatusError):
        backfill.fetch(fathom(rate_limited=[9001] * 3), 9001, attempts=2, sleep=waits.append)


def test_the_folders_are_written_outside_the_repository():
    from backend_pipeline.config import BACKEND_ROOT
    with pytest.raises(ValueError, match="outside the repository"):
        backfill.outside_repository(BACKEND_ROOT / "calls")
    backfill.outside_repository(BACKEND_ROOT.parent / "research" / "fathom-backfill")


@pytest.mark.parametrize("output", ["tmp/atelier-fathom-test", "artifacts/fathom-test", "app-sibling/fathom-test"])
def test_the_image_layout_accepts_folders_outside_the_application(tmp_path, monkeypatch, output):
    from backend_pipeline import config
    # The image installs the backend at /app; use the host's filesystem root on Windows too.
    root = Path(tmp_path.anchor)
    monkeypatch.setattr(config, "BACKEND_ROOT", root / "app")
    backfill.outside_repository(root / output)


@pytest.mark.parametrize("output", ["app", "app/backend_pipeline/calls", "tmp/../app/backend_pipeline/calls"])
def test_the_image_layout_still_protects_application_code(tmp_path, monkeypatch, output):
    from backend_pipeline import config
    root = Path(tmp_path.anchor)
    monkeypatch.setattr(config, "BACKEND_ROOT", root / "app")
    with pytest.raises(ValueError, match="outside the repository"):
        backfill.outside_repository(root / output)


# ---- on a database ----------------------------------------------------------------------------------------------------

@pytest.fixture
def ready(platform_setup):  # noqa: F811
    from pathlib import Path

    from backend_pipeline import reference
    repo, models, tmp_path = platform_setup
    with repo.connection() as conn:
        reference.sync_roster(conn, Path(__file__).resolve().parents[2] / "knowledge_base", date(2026, 10, 18))
    return repo, models, tmp_path


def earlier_imports(repo, tmp_path):
    """What the working copy already holds: 9007 from a week packet (native Fathom), and 9003's call as a Zoom file dated from
    the calendar."""
    from backend_pipeline.documents import intake
    packet = tmp_path / "packet"
    raw = json.dumps(TRANSCRIPTS[9007]).encode()
    backfill.write_folder(packet / "9007", MEETINGS[6], raw, collected_at=datetime(2026, 10, 10, tzinfo=UTC))
    zoom = tmp_path / "zoom"
    zoom.mkdir()
    lines = ["WEBVTT", ""]
    for i, words in enumerate(WORDS["kickoff"]):
        lines += [str(i + 1), f"00:0{i}:01.000 --> 00:0{i}:09.000", f"Robin Example: {words.replace('tracking', 'the tracking')}", ""]
    (zoom / "Ads Kickoff Call _ Studio Example's transcript.vtt").write_text("\n".join(lines), encoding="utf-8")
    intake.import_directory(repo, packet)
    done = intake.import_directory(repo, zoom)
    with repo.connection() as conn:
        conn.execute("UPDATE transcripts SET occurred_at=%s,occurred_at_source='calendar' WHERE transcript_id=%s",
                     (datetime(2026, 10, 7, 14, 30, 49, tzinfo=UTC), done["transcript_ids"][0]))
    return done["transcript_ids"][0]


def counts(repo):
    with repo.connection() as conn:
        return {t: conn.execute(f"SELECT count(*) n FROM {t}").fetchone()["n"] for t in ("transcripts", "pipeline_jobs", "pipeline_runs")}


def test_scheduled_collection_imports_once_with_the_image_layout(ready, monkeypatch):
    from backend_pipeline import config
    from backend_pipeline.cycle import schedule
    from backend_pipeline.intake import fathom as intake_fathom

    repo, models, tmp_path = ready
    monkeypatch.setattr(config, "BACKEND_ROOT", Path(tmp_path.anchor) / "app")
    monkeypatch.setenv("ATELIER_FATHOM_API_KEY", "fathom-test-secret")
    calls = []
    # Exercise the real scheduled collection and backfill; only the provider's HTTP is replaced.
    monkeypatch.setattr(intake_fathom, "FathomClient", lambda settings: fathom(
        calls, meetings=[MEETINGS[3]], transcripts={9004: TRANSCRIPTS[9004]}))

    first = schedule.collect_window(repo, models, *WINDOW, "America/Chicago", "tester")
    assert first["meetings_listed"] == first["imported"] == first["normalised"] == 1
    after = counts(repo)
    calls.clear()
    again = schedule.collect_window(repo, models, *WINDOW, "America/Chicago", "tester")
    assert again["imported"] == 0 and again["by_state"] == {"already_a_document": 1}
    assert counts(repo) == after
    assert not any("/recordings/" in str(call.url) for call in calls), "a stored transcript is not fetched again"


def test_the_october_calls_become_documents_once_each(ready):
    repo, models, tmp_path = ready
    zoom_id = earlier_imports(repo, tmp_path)
    out = tmp_path / "fathom-backfill"
    before = counts(repo)

    preview = backfill.run(repo, models, fathom(), start=WINDOW[0], end=WINDOW[1], out=out, timezone="America/Chicago", dry_run=True)
    assert preview["meetings_listed"] == 6 and preview["by_state"] == {"to_fetch": 5, "already_a_document": 1}
    flagged = {m["recording_id"]: m.get("possible_same_call") for m in preview["meetings"]}
    assert flagged[9001] == [9002] and flagged[9003] == [zoom_id] and flagged[9004] == []
    assert not out.exists() and counts(repo) == before, "a dry run fetches and writes nothing"

    calls = []
    done = backfill.run(repo, models, fathom(calls), start=WINDOW[0], end=WINDOW[1], out=out, timezone="America/Chicago")
    states = {m["recording_id"]: m for m in done["meetings"]}
    assert {rid: m["state"] for rid, m in states.items()} == {
        9001: "fetched", 9002: "same_call_as_recording", 9003: "same_call_as_document", 9004: "fetched",
        9007: "already_a_document", 9008: "transcript_not_ready"}
    assert states[9002]["same_as"] == 9001 and states[9003]["same_as"] == zoom_id and states[9003]["similarity"] >= 0.3
    assert not any("/recordings/9007/" in str(c.url) for c in calls), "a stored recording is not fetched"
    assert sorted(p.parent.name for p in out.rglob("transcript.raw.json")) == ["9001", "9004"], "only what is imported is written"
    assert done["imported"] == 2 and done["already_documents"] == 1 and done["same_call_as_a_document"] == 1
    assert done["same_call_as_another_recording"] == 1 and done["fetched"] == 4
    assert done["documents"] == 3 and done["normalised"] == 3 and done["normalised_now"] == 3 and done["dated_by_provider"] == 3
    assert done["waiting_for_classification"] == 1 and done["included"] >= 1
    assert done["embedding_estimate"]["chunks"] >= 1 and done["embedding_queued"] is None
    assert done["next"][2].startswith("ATELIER_ALLOW_ENCODING=true python -m backend_pipeline.storage_cli documents reembed --mode live --ids ")
    with repo.connection() as conn:
        rows = {r["upstream_id"]: r for r in conn.execute("SELECT * FROM transcripts WHERE source_type='fathom'")}
        embedded = conn.execute("SELECT count(*) n FROM transcript_chunks WHERE embedding IS NOT NULL").fetchone()["n"]
    assert set(rows) == {"fathom:9001", "fathom:9004", "fathom:9007"}
    assert rows["fathom:9001"]["occurred_at"] == datetime(2026, 10, 5, 17, 1, 42, tzinfo=UTC)
    assert rows["fathom:9001"]["occurred_at_source"] == "provider" and rows["fathom:9001"]["normalised_at"] is not None
    assert rows["fathom:9001"]["source_metadata"]["provider_metadata"]["recording_id"] == 9001
    assert embedded == 0, "embedding is a paid step, queued only when asked"
    assert done["classification"] and all(c["call_type"] for c in done["classification"])

    # A rerun adds nothing and fetches nothing: the imported recordings are documents, the twin and the Zoom call match again.
    after = counts(repo)
    calls.clear()
    again = backfill.run(repo, models, fathom(calls), start=WINDOW[0], end=WINDOW[1], out=out, timezone="America/Chicago")
    assert again["imported"] == 0 and again["import"]["new"] == 0 and counts(repo) == after
    assert {m["recording_id"]: m["state"] for m in again["meetings"]} == {
        9001: "already_a_document", 9002: "same_call_as_document", 9003: "same_call_as_document", 9004: "already_a_document",
        9007: "already_a_document", 9008: "transcript_not_ready"}
    assert {str(c.url).split("/")[-2] for c in calls if "/recordings/" in str(c.url)} == {"9002", "9003", "9008"}

    # The estimate reads what is stored: the embedding of the window's documents, no call made.
    estimate = backfill.run(repo, models, fathom(), start=WINDOW[0], end=WINDOW[1], out=out, timezone="America/Chicago", estimate=True)
    assert estimate["estimate"]["embedding"]["documents"] == 3 and estimate["estimate"]["classification"] is None
    assert counts(repo) == after


def test_a_later_live_collection_of_a_backfilled_call_adds_no_document(ready):
    from backend_pipeline.intake.fathom import collect
    from backend_pipeline.intake.repository import IntakeRepository
    repo, models, tmp_path = ready
    backfill.run(repo, models, fathom(), start=WINDOW[0], end=WINDOW[1], out=tmp_path / "out", timezone="America/Chicago")
    with repo.connection() as conn:
        before = conn.execute("SELECT transcript_id FROM transcripts WHERE upstream_id='fathom:9001'").fetchone()["transcript_id"]
    stored_before = counts(repo)["transcripts"]
    admin = "admin@example.test"
    live = IntakeRepository(repo.settings, IntakeSettings(fathom_key="fathom-test-secret", admins=(admin,)))
    live.activate("fathom", admin, now=datetime(2026, 10, 1, tzinfo=UTC))
    request = live.request_collection(cutoff=datetime(2026, 10, 22, tzinfo=UTC))["request_ids"][0]
    collect(live, request, fathom(meetings=[MEETINGS[0]]))
    with repo.connection() as conn:
        revision = conn.execute("SELECT transcript_id FROM intake_revisions").fetchone()
    assert revision["transcript_id"] == before and counts(repo)["transcripts"] == stored_before


def test_the_command_line_runs_the_backfill(ready, monkeypatch, capsys):
    from backend_pipeline import storage_cli
    from backend_pipeline.config import Settings
    from backend_pipeline.documents import cli as documents_cli
    from backend_pipeline.storage_config import StorageSettings
    repo, models, tmp_path = ready
    monkeypatch.setattr(StorageSettings, "from_env", classmethod(lambda cls: repo.settings))
    monkeypatch.setattr(Settings, "from_env", classmethod(lambda cls: models))
    monkeypatch.setattr(documents_cli, "fathom_client", lambda: fathom())
    argv = ["documents", "fathom-backfill", "--from", "2026-10-05", "--to", "2026-10-19", "--out", str(tmp_path / "out")]
    storage_cli.main([*argv, "--dry-run"])
    assert json.loads(capsys.readouterr().out)["by_state"] == {"to_fetch": 6}
    storage_cli.main(argv)
    result = json.loads(capsys.readouterr().out)
    assert result["imported"] == 4 and result["same_call_as_another_recording"] == 1 and result["waiting_for_classification"] == 1
    with pytest.raises(SystemExit):
        storage_cli.main([*argv, "--dry-run", "--estimate"])


def test_the_command_says_when_no_fathom_key_is_set(monkeypatch):
    from backend_pipeline.documents import cli as documents_cli
    monkeypatch.delenv("ATELIER_FATHOM_API_KEY", raising=False)
    monkeypatch.delenv("FATHOM_API_KEY", raising=False)
    with pytest.raises(SystemExit, match="FATHOM_API_KEY"):
        documents_cli.fathom_client()
