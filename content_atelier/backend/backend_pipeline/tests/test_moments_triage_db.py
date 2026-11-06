"""Plan 2.B9: Slack triage before extraction. Deterministic rules set `included = false` with a reason, a person's decision is
never overridden, and an excluded Slack item creates no extraction job. No network."""
from __future__ import annotations

import json

import pytest

from backend_pipeline import reference
from backend_pipeline.documents import slack_export
from backend_pipeline.documents.api import ClassificationRequest, classify_by_person
from backend_pipeline.jobs.executor import run_job
from backend_pipeline.moments import queue
from backend_pipeline.normalise import classify
from backend_pipeline.tests.moments_fixtures import KB, ScriptedProvider, response, scene
from backend_pipeline.tests.platform_db import platform_setup, platform_url  # noqa: F401 (fixtures)
from backend_pipeline.tests.test_documents_db import run_jobs

TS = iter(range(1757000000, 1758000000, 100))


def message(user, text, **extra):
    ts = f"{next(TS)}.000100"
    return {"type": "message", "user": user, "text": text, "ts": ts, **extra}


def export(tmp_path):
    root = tmp_path / "slack"
    for channel in ("wia-general", "wia-closed"):
        (root / channel).mkdir(parents=True)
    (root / "users.json").write_text(json.dumps([
        {"id": "U1", "name": "whitney", "profile": {"real_name": "Whitney Hodges"}},
        {"id": "U2", "name": "gisselle", "profile": {"real_name": "Gisselle Jimenez"}},
        {"id": "U3", "name": "zapier", "profile": {"real_name": "Zapier"}},
        {"id": "U4", "name": "helper", "profile": {"real_name": "Reminder Bot"}}]))
    (root / "channels.json").write_text(json.dumps([{"id": "C1", "name": "wia-general"}, {"id": "C3", "name": "wia-closed"}]))
    root_ts = f"{next(TS)}.000200"
    long = [{"type": "message", "user": "U1", "text": "Has anyone seen the *new* template for inquiry follow-up emails?", "ts": root_ts, "thread_ts": root_ts},
            message("U2", "Yes it is in the drive, I changed the first reply to ask a question about their date.", thread_ts=root_ts)]
    day = long + [message("U1", "Lunch?"),                                                  # too short
                  message("U2", "ok thanks! :thumbsup:"),                                     # too short, emoji is not a word
                  message("U3", "New row added to the leads sheet for the spring open house weekend"),   # automation by name
                  message("U4", "Reminder: the weekly planning meeting starts in five minutes today"),   # a name ending in bot
                  message("U2", "<@U2> has joined the channel"),                              # system text without a subtype
                  message("U1", "short", bot_id="B1")]                                          # a bot_id post is dropped at import
    (root / "wia-general" / "2025-09-04.json").write_text(json.dumps(day))
    (root / "wia-closed" / "2025-09-04.json").write_text(json.dumps([message("U1", "A perfectly long message about the spring open house plan and the ad budget")]))
    return root


@pytest.fixture
def slack(platform_setup):  # noqa: F811
    repo, models, tmp_path = platform_setup
    with repo.connection() as conn:
        reference.sync_roster(conn, KB, __import__("datetime").date(2026, 10, 18))
    result = slack_export.import_export(repo, export(tmp_path), workspace="T1")
    with repo.connection() as conn:
        # A channel a connection switched off: its documents are excluded (the export import itself only skips named channels).
        conn.execute("UPDATE slack_channels SET included=false,exclusion_reason='Switched off' WHERE channel_id='C3'")
    run_jobs(repo, models, limit=40)
    with repo.connection() as conn:
        docs = {d["transcript_id"]: d for d in conn.execute("SELECT * FROM transcripts WHERE source_type='slack'")}
    return repo, models, tmp_path, result, docs


def by_text(docs, needle):
    return next(d for d in docs.values() if needle in d["original_text"])


def test_the_rules_exclude_acknowledgements_automation_system_text_and_closed_channels_with_a_reason(slack):
    repo, models, _, result, docs = slack
    assert result["skipped_messages"] == 1, "only the bot_id post is dropped at import"
    expected = {"Has anyone seen": (True, None), "Lunch?": (False, "too_short"), "ok thanks": (False, "too_short"),
                "New row added": (False, "bot_messages"), "Reminder: the weekly": (False, "bot_messages"),
                "has joined the channel": (False, "system_messages"), "perfectly long message": (False, "excluded_channel")}
    for needle, (included, rule) in expected.items():
        doc = by_text(docs, needle)
        assert doc["included"] is included, needle
        if rule:
            assert doc["classification"]["triage"] == {"rule": rule, "version": classify.TRIAGE_VERSION}, needle
            assert doc["exclusion_reason"].startswith("Slack triage:") and doc["extraction_status"] == "not_applicable"
        else:
            assert doc["extraction_status"] == "pending" and "triage" not in doc["classification"]


def test_excluded_slack_items_create_no_extraction_job_and_the_included_one_does(slack):
    repo, models, tmp_path, _, docs = slack
    with repo.connection() as conn:
        pending = queue.pending_documents(conn)
    assert [d["transcript_id"] for d in pending] == [by_text(docs, "Has anyone seen")["transcript_id"]]
    result = queue.queue_extraction(repo, models, pending, mode="synthetic", actor="tester", queue="bulk", profile="2026-10-19.scenes.v2")
    assert len(result["jobs"]) == 1
    with repo.connection() as conn:
        jobs = conn.execute("SELECT transcript_id FROM pipeline_jobs WHERE stage='moment_extraction'").fetchall()
    assert {j["transcript_id"] for j in jobs} == {pending[0]["transcript_id"]}
    for needle in ("Lunch?", "New row added", "has joined the channel", "perfectly long message"):
        with pytest.raises(ValueError, match="excluded"):
            queue.queue_extraction(repo, models, [by_text(docs, needle)], mode="synthetic", actor="tester", queue="bulk")
    # The included thread goes through the whole path, a Slack passage and speaker included.
    scripts = {"seen the *new* template": lambda inv, n, system: response(inv, scene(
        quote="Has anyone seen the *new* template for inquiry follow-up emails?", anchor_span_ids=["m1.t0001"],
        context_first_span_id="m1.t0001", context_last_span_id="m1.t0002", moment_type="question", client_contribution=None,
        sensitivity="unknown"))}
    provider = ScriptedProvider(scripts)
    run_job(result["jobs"][0], storage=repo.settings, models=models, provider=provider, successors=False)
    with repo.connection() as conn:
        (moment,) = conn.execute("SELECT * FROM key_moments").fetchall()
    assert moment["moment_type"] == "question" and moment["speaker_label"] == "Whitney Hodges" and moment["speaker_role"] == "staff"
    assert moment["document_id"] == pending[0]["transcript_id"] and moment["quote_verified"]


def test_a_persons_decision_is_never_overridden_by_triage_and_the_rules_apply_again_when_it_is_gone(slack):
    repo, models, _, _, docs = slack
    lunch = by_text(docs, "Lunch?")
    assert lunch["included"] is False
    classify_by_person(repo, lunch["transcript_id"], ClassificationRequest(
        call_type="slack_thread", included=True, reason="The lunch thread decided the offsite; keep it"), "whitney@example.invalid", models)
    from backend_pipeline.documents.jobs import normalise
    normalise(repo, lunch["transcript_id"], models=models)
    with repo.connection() as conn:
        kept = conn.execute("SELECT * FROM transcripts WHERE transcript_id=%s", (lunch["transcript_id"],)).fetchone()
        pending = {d["transcript_id"] for d in queue.pending_documents(conn)}
    assert kept["included"] is True and kept["classification"]["method"] == "person" and "triage" not in kept["classification"]
    assert kept["extraction_status"] in {"pending", "queued"} and lunch["transcript_id"] in pending
    # And a person can exclude a thread the rules keep.
    seen = by_text(docs, "Has anyone seen")
    classify_by_person(repo, seen["transcript_id"], ClassificationRequest(call_type="slack_thread", included=False, reason="Private"),
                       "whitney@example.invalid", models)
    with repo.connection() as conn:
        assert seen["transcript_id"] not in {d["transcript_id"] for d in queue.pending_documents(conn)}


def test_the_word_count_ignores_links_mentions_emoji_and_punctuation():
    assert classify.slack_words("<@U1> :thumbsup: ok!! <https://x.example/a|a link> https://y.example") == 1
    assert classify.slack_words("Has anyone seen the new template") == 6
    assert classify.slack_words("") == 0
    doc = {"original_text": "ok", "passage_map": [{"start": 0, "end": 2, "speaker": "A"}], "title": "Slack #wia-general · 2025-09-04",
           "source_metadata": {"slack": {"channel": "C1"}}}
    assert classify.triage_slack(doc, min_words=1) is None
    assert classify.triage_slack(doc, min_words=2).rule == "too_short"
    assert classify.triage_slack(doc, min_words=0, excluded_channels=["#WIA-General"]).rule == "excluded_channel"
    assert classify.triage_slack({**doc, "source_metadata": {"slack": {"channel": "C9"}}}, min_words=0, closed_channel_ids=["C9"]).rule == "excluded_channel"
    assert classify.triage_slack({**doc, "passage_map": [{"start": 0, "end": 2, "speaker": "Deploy Bot"}]}, min_words=0).rule == "bot_messages"
    assert classify.triage_slack({**doc, "passage_map": [{"start": 0, "end": 2, "speaker": None}]}, min_words=0) is None, "no speaker is not a bot"
