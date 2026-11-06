"""Phase N10's autonomy pass on a real database: what a person used to do after every import, the system now does by itself.

- a second recording of one meeting (another note-taker) is linked to the first and excluded, as the backfill already did;
- a new client's call adds the account its title names, with its outside speakers as people, anonymised, for a person to
  check; another spelling of an existing account joins that account; a title that names nothing adds nothing;
- WIA's own private matters (a tax-planning call) are excluded by rule;
- the hourly upkeep queues the extraction of new documents only, never the archive.

Synthetic transcripts, no network."""
from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from test_documents_db import FILLER

from backend_pipeline import reference, upkeep
from backend_pipeline.documents import intake
from backend_pipeline.documents.jobs import normalise
from backend_pipeline.normalise.sources import fathom_document
from backend_pipeline.tests.platform_db import platform_setup, platform_url  # noqa: F401 (fixtures)

KB = Path(__file__).resolve().parents[2] / "knowledge_base"
OTHER = " ".join(["the", "landing", "page", "converted", "better", "than", "the", "old", "one", "this", "month"] * 8)


@pytest.fixture
def ready(platform_setup):  # noqa: F811
    repo, models, tmp_path = platform_setup
    with repo.connection() as conn:
        reference.sync_roster(conn, KB, date(2026, 10, 18))
    return repo, models, tmp_path


def payload(client_name, client_email, words=FILLER, extra=""):
    return {"transcript": [
        {"timestamp": "00:00:01", "text": f"Welcome. {words}",
         "speaker": {"display_name": "Carmen Cruickshank", "matched_calendar_invitee_email": "carmen@weddingindustryads.com"}},
        {"timestamp": "00:01:00", "text": f"Thanks for having me. {words} {extra}",
         "speaker": {"display_name": client_name, "matched_calendar_invitee_email": client_email}}]}


def add(repo, recording_id, title, start, body, digest):
    from backend_pipeline.artifacts import store_for
    meeting = {"recording_id": recording_id, "title": title, "recording_start_time": start}
    document = fathom_document(meeting, body, digest * 64)
    with repo.connection() as conn:
        intake.register(conn, store_for(repo.settings), document, digest.encode())
    return document["transcript_id"]


def row(repo, transcript_id):
    with repo.connection() as conn:
        return conn.execute("SELECT * FROM transcripts WHERE transcript_id=%s", (transcript_id,)).fetchone()


def test_a_second_recording_of_one_meeting_is_linked_to_the_first_and_excluded(ready):
    repo, models, _ = ready
    first = add(repo, 7001, "Larkhill Barn Ads Strategy Call", "2026-10-22T16:01:00Z", payload("Dana Lee", "dana@barn.example"), "a")
    # Another note-taker: the same conversation with a few words more, starting two minutes later.
    second = add(repo, 7002, "Impromptu Zoom Meeting", "2026-10-22T16:03:00Z",
                 payload("Dana Lee", "dana@barn.example", extra="um yes right"), "b")
    other = add(repo, 7003, "Larkhill Barn Ads Strategy Call", "2026-10-22T16:05:00Z",
                payload("Dana Lee", "dana@barn.example", words=OTHER), "c")  # a different call at the same time
    for transcript_id in (first, second, other):
        normalise(repo, transcript_id, models=models)
    assert row(repo, first)["canonical_document_id"] is None and row(repo, first)["included"]
    copy = row(repo, second)
    assert copy["canonical_document_id"] == first and not copy["included"]
    assert copy["exclusion_reason"].startswith("Another recording of the same meeting as")
    assert row(repo, other)["canonical_document_id"] is None, "a different conversation at the same time is not a copy"


def test_a_new_clients_call_adds_the_account_its_title_names_for_a_person_to_check(ready):
    repo, models, _ = ready
    first = add(repo, 7101, "Matlai Photography Ads Kickoff Call", "2026-10-22T16:01:00Z",
                payload("Priya Matlai", "priya@matlai.example"), "d")
    normalise(repo, first, models=models)
    doc = row(repo, first)
    assert doc["call_type"] == "client_1to1" and doc["client_id"]
    with repo.connection() as conn:
        account = conn.execute("SELECT * FROM clients WHERE client_id=%s", (doc["client_id"],)).fetchone()
        people = conn.execute("SELECT name,role,pronouns,source FROM people WHERE client_id=%s", (doc["client_id"],)).fetchall()
    assert (account["name"], account["consent"], account["do_not_name"], account["source"], account["reviewed"]) == \
        ("Matlai Photography", "anonymise_only", False, "call", None)
    assert [(p["name"], p["role"], p["pronouns"], p["source"]) for p in people] == [("Priya Matlai", "client", None, "call")]
    # The next call with the same client finds the account through its person, whatever its title says.
    second = add(repo, 7102, "Impromptu Zoom Meeting", "2026-10-29T16:01:00Z",
                 payload("Priya Matlai", "priya@matlai.example", words=OTHER), "e")
    normalise(repo, second, models=models)
    assert row(repo, second)["client_id"] == doc["client_id"]


def test_another_spelling_joins_the_existing_account_and_a_title_naming_nothing_adds_nothing(ready):
    repo, models, _ = ready
    with repo.connection() as conn:
        conn.execute("""INSERT INTO clients(client_id,name,aliases,status,consent,source)
            VALUES ('client_bright','The Brightside','[]','active','anonymise_only','reviewed_identities')""")
    spelled = add(repo, 7201, "Brightside | Ads Strategy Call", "2026-10-23T15:04:00Z",
                  payload("Rose Hart", "rose@bright.example"), "f")
    nothing = add(repo, 7202, "Impromptu Zoom Meeting", "2026-10-23T18:00:00Z",
                  payload("Sam Rowe", "sam@rowe.example", words=OTHER), "g")
    normalise(repo, spelled, models=models)
    normalise(repo, nothing, models=models)
    assert row(repo, spelled)["client_id"] == "client_bright"
    with repo.connection() as conn:
        assert conn.execute("SELECT aliases FROM clients WHERE client_id='client_bright'").fetchone()["aliases"] == ["Brightside"]
        assert conn.execute("SELECT count(*) n FROM clients").fetchone()["n"] == 1, "a title that names nothing adds no account"
    assert row(repo, nothing)["client_id"] is None


def test_wias_own_private_matter_is_excluded_by_rule(ready):
    repo, models, _ = ready
    private = add(repo, 7301, "WIA + Whitney Tax Planning Call", "2026-10-23T17:01:00Z",
                  payload("Ann Ledger", "ann@cpa.example"), "h")
    normalise(repo, private, models=models)
    doc = row(repo, private)
    assert (doc["call_type"], doc["included"], doc["client_id"]) == ("vendor", False, None)
    with repo.connection() as conn:
        assert conn.execute("SELECT count(*) n FROM clients").fetchone()["n"] == 0


def test_the_hourly_upkeep_queues_new_documents_only(ready, monkeypatch):
    repo, models, _ = ready
    fresh = add(repo, 7401, "Larkhill Barn Ads Strategy Call", "2026-10-22T16:01:00Z", payload("Dana Lee", "dana@barn.example"), "i")
    old = add(repo, 7402, "Larkhill Barn Ads Strategy Call", "2026-06-02T16:01:00Z",
              payload("Dana Lee", "dana@barn.example", words=OTHER), "j")
    for transcript_id in (fresh, old):
        normalise(repo, transcript_id, models=models)
    now = datetime.now(UTC)
    with repo.connection() as conn:  # read before, under an earlier profile: never re-extracted by the upkeep
        conn.execute("UPDATE transcripts SET extraction_status='completed' WHERE transcript_id=%s", (old,))
    queued = []
    monkeypatch.setattr(type(repo.settings), "generation_enabled", property(lambda self: True), raising=False)
    from backend_pipeline.moments import queue

    def fake(repo_, models_, documents, **kw):
        queued.append(([d["transcript_id"] for d in documents], kw))
        return {"run_id": None, "jobs": [], "skipped": []}
    monkeypatch.setattr(queue, "queue_extraction", fake)
    result = upkeep.hourly(repo, models, now)
    assert queued and queued[0][0] == [fresh] and queued[0][1]["mode"] == "live" and queued[0][1]["queue"] == "bulk"
    assert result["scenes"]["queued"] == 0


def test_a_used_up_budget_makes_the_upkeep_wait_not_fail(ready, monkeypatch):
    # Production's first pass (25 October): the week's extraction budget was used up and the hour was recorded as a failed
    # schedule, an error alert, though the documents only had to wait for Monday's renewal.
    repo, models, _ = ready
    from backend_pipeline.llm.run_plans import BudgetExhausted
    monkeypatch.setattr(upkeep, "extract_new", lambda *a, **k: (_ for _ in ()).throw(
        BudgetExhausted("Run plan plan_standing_extraction is exhausted", purpose="extraction")))
    result = upkeep.hourly(repo, models, datetime.now(UTC))
    assert result["scenes"] == {"queued": 0, "waiting": "this week's extraction budget is used up; queued after it renews or "
                                                        "is raised"}
    assert "embeddings" in result, "one part waiting never stops the other"


def test_the_upkeep_queues_nothing_where_paid_calls_are_off(ready):
    repo, models, _ = ready
    assert upkeep.hourly(repo, models, datetime.now(UTC))["scenes"]["skipped"].startswith("paid generation is off")


def test_an_uploaded_file_name_names_the_title_without_its_extension():
    from backend_pipeline.identities import account_name_from_title
    # A staff member's meeting room uploaded as .vtt became the account "Whitney Hodges's 's (9).vtt" (N11's suite).
    assert account_name_from_title("Whitney Hodges's Personal Meeting Room's transcript (9).vtt") == "Whitney Hodges"
    assert account_name_from_title("Fernbrook Estate Kickoff.docx") == "Fernbrook Estate"
    assert account_name_from_title("transcript.txt") is None
    # Dates and counters are not part of the name; a trade alone names no one.
    assert account_name_from_title("Review with Dana Lee 2026-03-10 A.vtt") == "Dana Lee"
    assert account_name_from_title("WIA x Fernbrook - 10/21") == "Fernbrook"
    assert account_name_from_title("Oct 21, 2026 - Barn at Willow Creek") == "Barn at Willow Creek"
    assert account_name_from_title("Cedar B Ranch x WIA Strategy Call") == "Cedar B Ranch"
    assert account_name_from_title("Venue Call #2") is None


def test_a_reviewed_list_replaces_the_systems_guess_but_never_rewrites_recorded_consent_by_default(ready, tmp_path):
    repo, _, _ = ready
    with repo.connection() as conn:
        conn.execute("""INSERT INTO clients(client_id,name,aliases,status,consent,source) VALUES
            ('client_guess','Guessed Venue','[]','active','anonymise_only','call'),
            ('client_named','Named Venue','[]','active','may_name','reviewed_list'),
            ('client_quiet','Quiet Venue','[]','active','anonymise_only','reviewed_list')""")
        listed = tmp_path / "clients.json"
        listed.write_text(__import__("json").dumps([
            {"name": "Guessed Venue", "consent": "may_name"},  # the first reviewed value replaces the system's guess
            {"name": "Named Venue"},  # no consent stated: the default never narrows a permission
            {"name": "Quiet Venue", "consent": "may_name"}]), encoding="utf-8")  # an old list never widens by itself
        reference.import_clients(conn, listed)
        got = {r["client_id"]: (r["consent"], r["source"]) for r in conn.execute("SELECT client_id,consent,source FROM clients")}
        assert got == {"client_guess": ("may_name", "reviewed_list"), "client_named": ("may_name", "reviewed_list"),
                       "client_quiet": ("anonymise_only", "reviewed_list")}
        listed.write_text(__import__("json").dumps([{"name": "Guessed Venue", "consent": "no_use"}]), encoding="utf-8")
        reference.import_clients(conn, listed)
        assert conn.execute("SELECT consent FROM clients WHERE client_id='client_guess'").fetchone()["consent"] == "may_name", \
            "once reviewed, the account's consent changes only with update_consent, as any other"


def test_the_upkeep_retries_its_own_scene_jobs_a_restart_stopped(ready):
    # Production, 25 October: a deploy restarted the bulk worker during the upkeep's embedding job; it waited for a person.
    repo, models, _ = ready
    with repo.connection() as conn:
        for run_id, by in (("run_upkeep", upkeep.ACTOR), ("run_person", "someone@example.com")):
            conn.execute("""INSERT INTO pipeline_runs(run_id,run_scope,status,trigger_type,triggered_by,input_refs)
                VALUES (%s,'moment_embedding','failed','manual',%s,'{}')""", (run_id, by))
        for job_id, run_id, attempts, error in (
                ("job_cut", "run_upkeep", 1, "Worker lease expired; embedding retries require review"),
                ("job_spent", "run_upkeep", 3, "Worker lease expired; embedding retries require review"),
                ("job_other", "run_upkeep", 1, "The provider refused the input"),
                ("job_theirs", "run_person", 1, "Worker lease expired; embedding retries require review")):
            conn.execute("""INSERT INTO pipeline_jobs(job_id,run_id,stage,status,idempotency_key,progress_details,queue,executor,
                attempt_count,error_summary) VALUES (%s,%s,'moment_embedding','failed',%s,'{"dependencies": []}','bulk','rq',%s,%s)""",
                         (job_id, run_id, job_id, attempts, error))
    assert upkeep.retry_interrupted(repo) == {"retried": ["job_cut"]}, "only its own, cut short, under the attempt limit"
    with repo.connection() as conn:
        status = {r["job_id"]: r["status"] for r in conn.execute("SELECT job_id,status FROM pipeline_jobs WHERE job_id = ANY(%s)", (["job_cut", "job_spent", "job_other", "job_theirs"],))}
    assert status == {"job_cut": "queued", "job_spent": "failed", "job_other": "failed", "job_theirs": "failed"}
