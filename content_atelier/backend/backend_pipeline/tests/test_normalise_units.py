"""Phase 1 units without a database: classification rules and the model path, speaker roles, occurrence dates, segmentation, glossary."""
from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from backend_pipeline.normalise import classify, dates, glossary, segment, speakers

PEOPLE = [
    {"person_id": "p_whit", "name": "Whitney Hodges", "role": "staff", "status": "current", "aliases": ["Whitney"], "email": None},
    {"person_id": "p_carm", "name": "Carmen Cruickshank", "role": "staff", "status": "current", "aliases": ["Carmen", "Carmin"], "email": None},
    {"person_id": "p_gis", "name": "Gisselle Jiménez", "role": "staff", "status": "current", "aliases": ["Giselle", "Gisselle"], "email": None},
    {"person_id": "p_chris", "name": "Christina Hill", "role": "staff", "status": "former", "aliases": ["Christina"], "email": None},
    {"person_id": "p_chris2", "name": "Christina Lopez", "role": "client", "status": "current", "aliases": ["Christina"], "email": None},
    {"person_id": "p_emily", "name": "Emily Foster", "role": "outside", "status": "current", "aliases": [], "email": "emily@designs.example"},
]
RESOLVER = speakers.Resolver(PEOPLE, staff_domains=["weddingindustryads.com"])


def doc(title="Call", text=None, source_type="zoom", speakers_=("Carmen Cruickshank", "Dana Lee"), words=120, passage_extra=None):
    body = text or " ".join(["word"] * words)
    passages, cursor = [], 0
    for i, speaker in enumerate(speakers_):
        value = f"{speaker}: {body}" if i == 0 else f"{speaker}: reply {i}"
        passages.append({"passage_id": f"s:span:{i}", "ordinal": i, "start": cursor, "end": cursor + len(value), "speaker": speaker,
                         "start_ms": i * 20_000, "end_ms": i * 20_000 + 10_000, **(passage_extra or {})})
        cursor += len(value) + 1
    original = "\n".join(f"{p['speaker']}: {body}" if i == 0 else f"{p['speaker']}: reply {i}" for i, p in enumerate(passages))
    return {"transcript_id": "t1", "title": title, "source_type": source_type, "original_text": original, "passage_map": passages,
            "occurred_at": None, "occurred_at_source": None, "source_metadata": {}}


# ---- classification rules ---------------------------------------------------------------------------------------

@pytest.mark.parametrize(("title", "labels", "words", "expected"), [
    ("Carmen's Personal Meeting Room's transcript (3).txt", ["Carmen Cruickshank", "Dana Lee"], 200, "client_1to1"),
    ("Monthly Q&A", ["Whitney Hodges", "Dana Lee"], 200, "workshop"),
    ("Press Record workshop", ["Whitney Hodges"], 300, "workshop"),
    ("Check-in with Gisselle", ["Whitney Hodges", "Gisselle Jiménez"], 200, "internal"),
    ("Planning", ["Whitney Hodges", "Dana Lee"], 200, "internal"),
    ("Carmen's Personal Meeting Room's transcript", ["Whitney Hodges", "Carmen Cruickshank"], 200, "internal"),
    ("Google Ads office hours", ["Carmen Cruickshank", "Erin Smith", "Shannon Lee"], 300, "office_hours"),
    ("Intro call with Ridge Venue", ["Whitney Hodges", "Pat Quinn"], 300, "prospect"),
    ("Software demo with CalendarCo", ["Whitney Hodges", "Sam Vendor"], 300, "vendor"),
    # A demo of WIA's own offer to someone outside is a sales call (the real "Rose _ ELEVATE + LeadLock Demo" and
    # "WIA ELEVATE Demo for The Brightside" were filed as a LeadLock team sync and a vendor's demo); with only the team on
    # it, a LeadLock title is still internal.
    ("Rose _ ELEVATE + LeadLock Demo", ["Whitney Hodges", "Rose"], 300, "prospect"),
    ("WIA ELEVATE Demo for The Brightside", ["Whitney Hodges", "Carli Dixon"], 300, "prospect"),
    ("LeadLock Demo", ["Whitney Hodges", "Gisselle Jiménez"], 300, "internal"),
    ("Anything", ["Carmen Cruickshank", "Dana Lee"], 20, "fragment"),
])
def test_rules_place_calls_the_way_the_corpus_index_does(title, labels, words, expected):
    document = doc(title, words=words, speakers_=tuple(labels))
    mapping = speakers.speaker_map(document, RESOLVER, None)
    assert classify.by_rules(document, speakers.externals(mapping)).call_type == expected


def test_rule_order_matches_the_index_a_workshop_title_beats_an_internal_title():
    document = doc("LeadLock workshop", speakers_=("Whitney Hodges", "Dana Lee"))
    mapping = speakers.speaker_map(document, RESOLVER, None)
    assert classify.by_rules(document, speakers.externals(mapping)).call_type == "workshop"


def test_an_uninformative_title_with_an_outside_voice_is_ambiguous_and_marked_for_a_person():
    document = doc("Carmen Cruickshank's Personal Meeting Room's transcript (17)")
    decision = classify.by_rules(document, ["Dana Lee"])
    assert decision.call_type == "client_1to1" and decision.needs_review
    named = classify.by_rules(doc("Review with Dana Lee"), ["Dana Lee"])
    assert named.call_type == "client_1to1" and not named.needs_review
    # Zoom's name for a meeting started on the spot says nothing either (13 production documents carried it, N4).
    impromptu = classify.by_rules(doc("Impromptu Zoom Meeting"), ["Dana Lee"])
    assert impromptu.call_type == "client_1to1" and impromptu.needs_review


def test_a_fathom_call_takes_the_recordings_name_when_the_calendar_title_says_nothing():
    from backend_pipeline.normalise.sources import fathom_title
    # N4: a consultation recorded under Zoom's "Impromptu Zoom Meeting" was filed as a client call; its recording's name
    # makes it the prospect call it was.
    consult = {"meeting_title": "Impromptu Zoom Meeting", "title": "Ads Consultation with Peter Example\n"}
    assert fathom_title(consult) == "Ads Consultation with Peter Example"
    document = doc(fathom_title(consult), speakers_=("Whitney Hodges", "Peter Example"))
    mapping = speakers.speaker_map(document, RESOLVER, None)
    assert classify.by_rules(document, speakers.externals(mapping)).call_type == "prospect"
    # An informative calendar title stays the title, as before; a missing one falls back to the recording, then the id.
    assert fathom_title({"meeting_title": "Google Ads Weekly Meeting", "title": "Google ads meeting"}) == "Google Ads Weekly Meeting"
    assert fathom_title({"meeting_title": "Impromptu Zoom Meeting", "title": ""}) == "Impromptu Zoom Meeting"
    assert fathom_title({"title": "Kickoff"}, 7) == "Kickoff" and fathom_title({}, 7) == "Fathom 7"


def test_a_slack_thread_is_a_slack_thread_and_an_attachment_waits_for_a_person():
    assert classify.by_rules(doc("Slack #general", source_type="slack"), []).call_type == "slack_thread"
    attachment = classify.by_rules(doc("notes.pdf", source_type="attachment"), [])
    assert attachment.call_type == "other" and attachment.needs_review and not classify.inclusion("other")[0]


class Model:
    def __init__(self, answer):
        self.answer, self.calls = answer, []

    def json_call(self, *, stage, system, user, schema, fingerprint):
        self.calls.append((stage, user))
        return self.answer, {"fake": True}


def test_the_model_places_only_what_the_rules_cannot():
    ambiguous = doc("Carmen Cruickshank's Personal Meeting Room's transcript (17)")
    mapping = speakers.speaker_map(ambiguous, RESOLVER, None)
    model = Model({"call_type": "office_hours", "reason": "Several members take turns asking questions.", "confidence": "high"})
    decision = classify.classify(ambiguous, mapping, provider=model, model="fast/model")
    assert (decision.call_type, decision.method, decision.needs_review) == ("office_hours", "model", False)
    stage, user = model.calls[0]
    assert stage == "document_classification" and "Dana Lee" in user and '"role": "unknown"' in user
    clear = Model({"call_type": "vendor", "reason": "x", "confidence": "high"})
    named = doc("Review with Dana Lee")
    assert classify.classify(named, speakers.speaker_map(named, RESOLVER, None), provider=clear, model="fast/model").method == "rule"
    assert clear.calls == [], "a call the rules place is never sent to a model"


def test_a_low_confidence_model_answer_still_goes_to_a_person_and_no_model_means_rules_with_a_flag():
    ambiguous = doc("Carmen Cruickshank's Personal Meeting Room's transcript (17)")
    mapping = speakers.speaker_map(ambiguous, RESOLVER, None)
    low = classify.classify(ambiguous, mapping, provider=Model({"call_type": "prospect", "reason": "maybe", "confidence": "low"}),
                            model="fast/model")
    assert low.call_type == "prospect" and low.needs_review
    none = classify.classify(ambiguous, mapping)
    assert none.method == "rule" and none.needs_review


def test_a_model_answer_with_an_unknown_type_is_refused():
    ambiguous = doc("Carmen Cruickshank's Personal Meeting Room's transcript (17)")
    mapping = speakers.speaker_map(ambiguous, RESOLVER, None)
    with pytest.raises(Exception):
        classify.classify(ambiguous, mapping, provider=Model({"call_type": "gossip", "reason": "x", "confidence": "high"}), model="m")


def test_a_call_where_no_speaker_is_named_is_not_called_internal_but_left_for_a_person():
    # A transcript with no speaker labels at all (a plain-text export, a recording without speaker identification) says
    # nothing about who spoke. "Only WIA staff speak" would be a false reason that silently excludes a client call.
    unnamed = doc("Carmen Cruickshank's Personal Meeting Room's transcript (21)")
    unnamed["passage_map"] = [{**p, "speaker": None} for p in unnamed["passage_map"]]
    mapping = speakers.speaker_map(unnamed, RESOLVER, None)
    decision = classify.classify(unnamed, mapping)
    assert decision.call_type != "internal" and decision.needs_review and "No speaker is named" in decision.reason
    model = Model({"call_type": "client_1to1", "reason": "A member asks about her inquiries.", "confidence": "high"})
    assert classify.classify(unnamed, mapping, provider=model, model="fast/model").method == "model", "the model may place it"
    named_title = doc("Check-in with Gisselle")
    named_title["passage_map"] = [{**p, "speaker": None} for p in named_title["passage_map"]]
    assert classify.by_rules(named_title, []).call_type == "internal", "a title the rules know still decides"


def test_inclusion_follows_the_setting_and_every_exclusion_has_a_reason():
    for call_type in ("internal", "vendor", "fragment", "other"):
        included, reason = classify.inclusion(call_type)
        assert not included and reason
    assert classify.inclusion("prospect")[0] and classify.inclusion("client_1to1")[0] and classify.inclusion("slack_thread")[0]
    assert classify.inclusion("internal", ("internal",)) == (True, None), "inclusion is a setting, not a constant"


# ---- speakers ---------------------------------------------------------------------------------------------------

def test_staff_are_recognised_by_name_and_marked_inferred_for_zoom():
    a = RESOLVER.resolve("Carmen Cruickshank", None, "client_1to1")
    assert (a["role"], a["person_id"], a["basis"], a["inferred"]) == ("staff", "p_carm", "name", True)
    assert RESOLVER.resolve("Giselle", None, None)["person_id"] == "p_gis", "an alias"
    assert RESOLVER.resolve("Whitney (Guest)", None, None)["person_id"] == "p_whit", "a recorder's decoration is ignored"
    assert RESOLVER.resolve("carmen cruickshank", None, None)["role"] == "staff", "case does not matter"


def test_a_first_name_two_people_share_is_not_guessed():
    assert RESOLVER.resolve("Christina", None, "client_1to1")["person_id"] is None


def test_an_unmatched_voice_is_a_client_in_a_client_call_a_prospect_in_a_prospect_call_and_unknown_otherwise():
    assert RESOLVER.resolve("Dana Lee", None, "client_1to1")["role"] == "client"
    assert RESOLVER.resolve("Dana Lee", None, "workshop")["role"] == "client"
    assert RESOLVER.resolve("Dana Lee", None, "prospect")["role"] == "prospect"
    unknown = RESOLVER.resolve("Dana Lee", None, None)
    assert unknown["role"] == "unknown" and unknown["inferred"] is True


def test_an_email_is_fact_not_inference():
    staff = RESOLVER.resolve("W. Hodges", "whitney@weddingindustryads.com", "client_1to1")
    assert staff["role"] == "staff" and staff["inferred"] is False and staff["basis"] == "email_domain"
    outside = RESOLVER.resolve("Dana", "dana@venue.example", "client_1to1")
    assert outside["role"] == "client" and outside["basis"] == "email" and outside["inferred"] is False
    known = RESOLVER.resolve("E Foster", "Emily@designs.example", None)
    assert known["person_id"] == "p_emily" and known["role"] == "outside" and known["inferred"] is False


def test_a_staff_member_who_books_with_their_own_domain_is_staff():
    """The real WIA Weekly Meeting (Fathom): Jacqueline Hood, the Meta ads manager, is invited at her own domain, so the
    email alone made WIA's own meeting a client call (19 October). The full roster name decides; a first name never does."""
    own = RESOLVER.resolve("Carmen Cruickshank", "carmen@cruickshank.example", "client_1to1")
    assert (own["role"], own["person_id"], own["basis"], own["inferred"]) == ("staff", "p_carm", "name_with_outside_email", True)
    assert RESOLVER.resolve("Carmen", "carmen@venue.example", "client_1to1")["role"] == "client", "a first name is not enough"
    assert RESOLVER.resolve("Dana Lee", "dana@venue.example", "client_1to1")["role"] == "client"


def test_every_passage_has_a_role_including_one_with_no_label():
    document = doc(speakers_=("Carmen Cruickshank", "Dana Lee", ""))
    document["passage_map"][2]["speaker"] = None
    mapping = speakers.speaker_map(document, RESOLVER, "client_1to1")
    roles = speakers.passage_roles(document, mapping)
    assert roles == ["staff", "client", "unknown"] and mapping[""]["basis"] == "no_label"
    assert [p["name"] for p in speakers.participants(document, mapping)] == ["Carmen Cruickshank", "Dana Lee"]


# ---- dates ------------------------------------------------------------------------------------------------------

TODAY = date(2026, 10, 18)


@pytest.mark.parametrize(("name", "expected"), [
    ("GMT20260312-153000_Recording.transcript.vtt", datetime(2026, 3, 12, 15, 30, tzinfo=UTC)),
    ("Client call 2026-03-12.txt", datetime(2026, 3, 12, 12, tzinfo=UTC)),
    ("Client call 20260312.txt", datetime(2026, 3, 12, 12, tzinfo=UTC)),
    ("Client call 03-12-2026.txt", datetime(2026, 3, 12, 12, tzinfo=UTC)),
    ("Workshop Mar 12, 2026.txt", datetime(2026, 3, 12, 12, tzinfo=UTC)),
    ("Workshop 12th March 2026.txt", datetime(2026, 3, 12, 12, tzinfo=UTC)),
])
def test_a_date_in_a_name_is_read_and_its_source_is_the_filename(name, expected):
    assert dates.from_filename(name, TODAY)[0] == expected
    result = dates.resolve({**doc(name), "title": name}, today=TODAY)
    assert result.source == "filename" and result.occurred_at == expected


@pytest.mark.parametrize("name", ["Carmen's Personal Meeting Room's transcript (17).txt", "call 2031-01-01.txt", "call 2026-13-45.txt",
                                  "invoice 20190101.txt", "Untitled"])
def test_no_evidence_means_explicitly_undated(name):
    result = dates.resolve({**doc(name), "title": name}, today=TODAY)
    assert result.occurred_at is None and result.source == "unknown" and result.detail


def test_a_week_is_never_a_source():
    document = {**doc("Untitled"), "week_id": "week_2026-06-01", "source_metadata": {"week_index": 1, "date": "2026-06-01"}}
    result = dates.resolve(document, today=TODAY)
    assert result.source == "unknown" and result.occurred_at is None
    assert "week" not in dates.SOURCES
    # The folder is kept as a window beside the missing date: dated to the week, not to a day.
    assert result.window and "week folder 1" in result.detail and result.evidence()["window"]["basis"].startswith("week folder 1")


def test_a_provider_date_wins_and_a_header_line_dates_a_transcript():
    stamp = datetime(2026, 5, 1, 9, tzinfo=UTC)
    assert dates.resolve({**doc("x"), "occurred_at": stamp, "occurred_at_source": "provider"}, today=TODAY).source == "provider"
    document = doc("Untitled")
    document["original_text"] = "Recorded on: March 3, 2026\n" + document["original_text"]
    assert dates.resolve(document, today=TODAY).source == "content"


def test_a_zoom_listing_dates_a_call_by_topic_and_length_and_refuses_an_ambiguous_match(tmp_path):
    listing = tmp_path / "zoom.csv"
    listing.write_text("Topic,ID,Start Time,Duration (Minutes)\n"
                       "Carmen Cruickshank's Personal Meeting Room,1,03/12/2026 03:30:00 PM,0.2\n"
                       "Carmen Cruickshank's Personal Meeting Room,2,03/19/2026 10:00:00 AM,0.2\n"
                       "Monthly Q&A,3,2026-02-10 18:00:00,1\n", encoding="utf-8")
    events = dates.read_zoom_listing(listing, "America/Chicago")
    assert len(events) == 3 and events[0].start == datetime(2026, 3, 12, 15, 30, tzinfo=events[0].start.tzinfo)
    qa = {**doc("Monthly Q&A's transcript (2)"), "title": "Monthly Q&A's transcript (2)"}
    result = dates.resolve(qa, events, today=TODAY)
    assert result.source == "zoom_listing" and result.occurred_at.date() == date(2026, 2, 10)
    twin = {**doc("Carmen Cruickshank's Personal Meeting Room's transcript (4)"), "title": "Carmen Cruickshank's Personal Meeting Room's transcript (4)"}
    ambiguous = dates.resolve(twin, events, today=TODAY)
    assert ambiguous.occurred_at is None and "not guessed" in ambiguous.detail


def test_one_meeting_dates_at_most_one_document(tmp_path):
    """The real backfill: six "Check-in with Gisselle" calls of 33 to 37 minutes all fit one 35-minute Fathom calendar
    entry, which would have dated all six to 6 October (untimed files fit any length, as here). An event that fits several documents dates none of them."""
    calendar = tmp_path / "cal.csv"
    calendar.write_text("title,start,end\nCheck-in with Gisselle,2026-10-06T17:02:12Z,2026-10-06T17:40:00Z\n"
                        "Strategy session with Dana,2026-10-07T15:00:00Z,2026-10-07T15:01:00Z\n", encoding="utf-8")
    events = dates.read_calendar(calendar, "UTC")
    untimed = []
    for n in range(3):
        d = {**doc(f"Check-in with Gisselle's transcript ({n})"), "title": f"Check-in with Gisselle's transcript ({n})"}
        for p in d["passage_map"]:
            p["start_ms"] = p["end_ms"] = None
        untimed.append(d)
    dana = {**doc("Strategy session with Dana"), "title": "Strategy session with Dana"}
    usable, contested = dates.exclusive([*untimed, dana], events)
    assert [e.title for e in contested] == ["Check-in with Gisselle"] and [e.title for e in usable] == ["Strategy session with Dana"]
    assert all(dates.resolve(d, usable, today=TODAY).occurred_at is None for d in untimed)
    assert dates.resolve(dana, usable, today=TODAY).source == "calendar"


def test_a_calendar_export_dates_a_call_and_the_listing_outranks_a_filename(tmp_path):
    ics = tmp_path / "cal.ics"
    ics.write_text("BEGIN:VCALENDAR\nBEGIN:VEVENT\nUID:a1\nSUMMARY:Strategy session with Dana\nDTSTART;TZID=America/Chicago:20260312T150000\n"
                   "DTEND;TZID=America/Chicago:20260312T150100\nEND:VEVENT\nEND:VCALENDAR\n", encoding="utf-8")
    events = dates.read_calendar(ics)
    assert len(events) == 1 and events[0].minutes == 1
    document = {**doc("Strategy session with Dana 2026-03-01"), "title": "Strategy session with Dana"}
    document["title"] = "Strategy session with Dana"
    result = dates.resolve(document, events, today=TODAY, names=("call 2026-03-01.vtt",))
    assert result.source == "calendar" and result.occurred_at.date() == date(2026, 3, 12)
    assert result.conflicts and "filename" in result.conflicts[0], "a disagreement is recorded, not hidden"


# ---- week folders and spoken cues (1.B11) -----------------------------------------------------------------------

def folder_doc(week, *lines, title="Morgan Example's Personal Meeting Room's transcript.txt", minute=1):
    """A Zoom backfill document in week folder `week`, its lines spoken from `minute` on, a minute apart."""
    cues = [f"00:{minute + i:02d}:00.000 --> 00:{minute + i:02d}:30.000\n{line}\n" for i, line in enumerate(lines)]
    first = date(2026, 6, 1) + (date(2026, 6, 8) - date(2026, 6, 1)) * (week - 1)
    return {**doc(title), "title": title, "original_text": "WEBVTT\n\n" + "\n".join(cues), "week_id": f"week_{first.isoformat()}",
            "source_metadata": {"week_index": week, "file_order": 1}}


def test_a_week_folder_is_a_window_in_india_time_and_only_zoom_backfill_documents_have_one():
    kolkata = dates.FOLDER_TIMEZONE
    one, twenty = dates.window_of(folder_doc(1, "Ann: hi")), dates.window_of(folder_doc(20, "Ann: hi"))
    assert (one.start, one.end) == (datetime(2026, 6, 1, tzinfo=kolkata), datetime(2026, 6, 8, tzinfo=kolkata))
    assert one.start == datetime(2026, 5, 31, 18, 30, tzinfo=UTC)
    assert (twenty.start, twenty.end) == (datetime(2026, 10, 12, tzinfo=kolkata), datetime(2026, 10, 19, tzinfo=kolkata))
    assert "2026-10-12 to 2026-10-18" in twenty.basis
    # Chicago days: a partial Sunday at each end.
    assert one.days()[0] == date(2026, 5, 31) and one.days()[-1] == date(2026, 6, 7) and len(one.days()) == 8
    assert dates.window_of({**folder_doc(3, "Ann: hi"), "source_type": "fathom"}) is None
    assert dates.window_of({**doc("x"), "source_metadata": {"week_index": 0}}) is None, "a loose file's week index is 0"
    assert dates.window_of({**folder_doc(3, "Ann: hi"), "week_id": "week_2026-03-02"}) is None, "another calendar's week 3"


def test_happy_monday_as_a_call_opens_dates_it_to_the_monday_of_its_folder():
    # Week 3 is 15 to 21 June (IST); Monday 15 June in Chicago, noon there is 17:00 UTC.
    document = folder_doc(3, "Ann Example: Hi Morgan, happy Monday!", "Morgan Example: Happy Monday, how was your weekend?")
    result = dates.resolve(document, today=TODAY)
    assert result.source == "content" and result.occurred_at == datetime(2026, 6, 15, 17, tzinfo=UTC)
    assert "happy Monday" in result.detail and "week folder 3" in result.detail and "2 cues agree" in result.detail
    assert result.window and not result.conflicts


@pytest.mark.parametrize("line", [
    "Ann Example: I'll send it Friday once the numbers are in.",
    "Ann Example: Oh yeah, it's Wednesday.",  # the meeting on the calendar is Wednesday, not today
    "Ann Example: On Monday we launched the new campaign.",
    "Ann Example: If today is Thursday then the report is late.",
    "Ann Example: Is today the 17th?",
    "Ann Example: Happy Sunday!",  # the IST week touches two Chicago Sundays
])
def test_a_weekday_that_is_not_said_as_today_dates_nothing(line):
    result = dates.resolve(folder_doc(3, line), today=TODAY)
    assert result.occurred_at is None and result.source == "unknown" and not result.conflicts
    assert result.window and "dated to week folder 3" in result.detail


def test_today_by_ordinal_by_date_and_by_tomorrow():
    assert dates.from_speech(folder_doc(3, "Ann: Yeah, today is the 17th.")["original_text"],
                             dates.window_of(folder_doc(3, "x")))[0].date() == date(2026, 6, 17)
    assert dates.from_speech(folder_doc(3, "Ann: Today's June 18th, so we have time.")["original_text"],
                             dates.window_of(folder_doc(3, "x")))[0].date() == date(2026, 6, 18)
    assert dates.from_speech(folder_doc(3, "Ann: Tomorrow is Friday, thankfully.")["original_text"],
                             dates.window_of(folder_doc(3, "x")))[0].date() == date(2026, 6, 18)
    value, detail = dates.from_speech(folder_doc(3, "Ann: Today, Wednesday, June 17th. Let me see.")["original_text"],
                                      dates.window_of(folder_doc(3, "x")))
    assert value.date() == date(2026, 6, 17) and "2 cues agree" in detail
    assert dates.from_speech(folder_doc(3, "Ann: If I don't do it today, I'll do it Tuesday.")["original_text"],
                             dates.window_of(folder_doc(3, "x"))) == (None, "")


def test_a_greeting_late_in_a_call_is_someone_drafting_a_post_and_dates_nothing():
    document = folder_doc(3, "Ann Example: Start each week with a post, something like.", "Ann Example: Happy Tuesday, what is on your agenda?",
                          minute=25)
    assert dates.resolve(document, today=TODAY).occurred_at is None


def test_cues_that_disagree_date_nothing_and_the_disagreement_is_kept():
    document = folder_doc(3, "Ann Example: Happy Monday!", "Morgan Example: Well, today is Thursday for me.")
    result = dates.resolve(document, today=TODAY)
    assert result.occurred_at is None and result.source == "unknown" and result.window
    assert len(result.conflicts) == 1 and result.conflicts[0].startswith("conflicting spoken cues")
    assert "2026-06-15" in result.conflicts[0] and "2026-06-18" in result.conflicts[0]


def test_a_cue_outside_the_window_is_rejected():
    result = dates.resolve(folder_doc(3, "Ann Example: Yeah, today is the 28th."), today=TODAY)
    assert result.occurred_at is None and "outside week folder 3" in result.conflicts[0]


def test_a_listing_event_unique_inside_its_week_dates_the_document_though_the_topic_recurs(tmp_path):
    listing = tmp_path / "zoom.csv"
    listing.write_text("Host,Topic,ID,Start Time,File Size (MB)\n"
                       'a@example.invalid,Morgan Example\'s Personal Meeting Room,1,"Jun 2, 2026 10:58:35 AM",10\n'
                       'a@example.invalid,Morgan Example\'s Personal Meeting Room,1,"Jun 25, 2026 01:56:28 PM",10\n'
                       'a@example.invalid,Morgan Example\'s Personal Meeting Room,1,"Jul 13, 2026 01:12:04 PM",10\n', encoding="utf-8-sig")
    events = dates.read_zoom_listing(listing, "America/Chicago")
    first = folder_doc(1, "Ann: hello")
    others = [{**folder_doc(2, "Ann: hello"), "transcript_id": "t2"},  # a week with no event: dated to its week
              {**folder_doc(7, "Ann: hello"), "transcript_id": "t7a"}, {**folder_doc(7, "Ann: hi"), "transcript_id": "t7b"}]
    usable, contested = dates.exclusive([first, *others], events)
    assert [e.start.date() for e in contested] == [date(2026, 7, 13)], "two documents of the topic in week 7: ambiguous"
    result = dates.resolve(first, usable, today=TODAY)
    assert result.source == "zoom_listing" and result.occurred_at == datetime(2026, 6, 2, 15, 58, 35, tzinfo=UTC)
    assert result.window and not result.conflicts
    for other in others:
        assert dates.resolve(other, usable, today=TODAY).occurred_at is None
    # Without the window the topic fits every document: nothing would be dated.
    corpus_wide = [{**d, "source_type": "file"} for d in (first, *others)]
    assert dates.exclusive(corpus_wide, events)[0] == []


# ---- segmentation -----------------------------------------------------------------------------------------------

def many_turns(count=10, size=500):
    passages, parts, cursor = [], [], 0
    for i in range(count):
        speaker = "Carmen Cruickshank" if i % 2 == 0 else "Dana Lee"
        value = f"{speaker}: " + ("x" * size)
        passages.append({"passage_id": f"s:span:{i}", "ordinal": i, "start": cursor, "end": cursor + len(value), "speaker": speaker,
                         "start_ms": i * 10_000, "end_ms": i * 10_000 + 5_000})
        parts.append(value)
        cursor += len(value) + 1
    return {"transcript_id": "t9", "title": "Long call", "original_text": "\n".join(parts), "passage_map": passages,
            "occurred_at": datetime(2026, 3, 12, 15, tzinfo=UTC)}


def test_chunks_carry_a_header_roles_a_date_and_a_one_turn_overlap():
    document = many_turns()
    mapping = speakers.speaker_map(document, RESOLVER, "client_1to1")
    chunks = segment.chunk_document(document, {"call_type": "client_1to1", "client_name": "Dana's Barn"}, mapping, max_characters=1200)
    assert len(chunks) >= 3
    first = chunks[0]
    assert first["header"].splitlines()[:3] == ["Call: Long call", "Date: 2026-03-12", "Type: Client call"]
    assert "Client: Dana's Barn" in first["header"] and "Carmen Cruickshank (WIA)" in first["header"] and "Dana Lee (client)" in first["header"]
    assert first["occurred_at"] == document["occurred_at"] and {s["role"] for s in first["speaker_roles"]} == {"staff", "client"}
    for earlier, later in zip(chunks, chunks[1:]):
        assert later["passage_refs"][0]["passage_id"] == earlier["passage_refs"][-1]["passage_id"], "the last turn opens the next chunk"
        assert later["passage_refs"][0]["overlap"] is True
    everything = {r["passage_id"] for c in chunks for r in c["passage_refs"]}
    assert everything == {p["passage_id"] for p in document["passage_map"]}, "every turn is in some chunk"
    for chunk in chunks:
        assert chunk["chunk_text"].startswith(chunk["header"]) and len(chunk["chunk_text"].encode()) <= segment.BYTE_LIMIT


def test_a_long_pause_breaks_a_chunk_without_an_overlap_and_a_huge_turn_stays_whole():
    document = many_turns(4, 100)
    for later in document["passage_map"][2:]:
        later["start_ms"] += 600_000
        later["end_ms"] += 600_000
    chunks = segment.chunk_document(document, {"call_type": "client_1to1"}, max_characters=5000)
    assert len(chunks) == 2 and "overlap" not in chunks[1]["passage_refs"][0]
    huge = many_turns(1, 5000)
    assert len(segment.chunk_document(huge, {}, max_characters=800)) == 1, "a quotation is never cut"


def test_chunk_identity_changes_with_the_header_and_the_hash_covers_text_and_references():
    document = many_turns()
    mapping = speakers.speaker_map(document, RESOLVER, "client_1to1")
    one = segment.chunk_document(document, {"call_type": "client_1to1"}, mapping)
    other = segment.chunk_document({**document, "occurred_at": None}, {"call_type": "client_1to1"}, mapping)
    assert {c["chunk_id"] for c in one}.isdisjoint({c["chunk_id"] for c in other})
    from backend_pipeline.chunk_encoding import chunk_view
    assert chunk_view({**one[0], "transcript_id": "t9"})["view_hash"], "the encoder's own integrity check accepts a v2 chunk"


# ---- glossary ---------------------------------------------------------------------------------------------------

TERMS = [{"term": "LeadLock", "kind": "product", "variants": ["Lead Lock", "lead luck", "Lead Lock Pro"], "status": "active"},
         {"term": "Carmen", "kind": "staff", "variants": ["Carmin"], "status": "active"}]


def test_the_glossary_normalises_a_search_copy_and_never_the_original():
    g = glossary.Glossary(TERMS)
    original = "We use Lead Lock Pro and lead luck, and Carmin said so; Lead Locks is another word."
    assert g.normalise(original) == "We use LeadLock and LeadLock, and Carmen said so; Lead Locks is another word."
    assert original == "We use Lead Lock Pro and lead luck, and Carmin said so; Lead Locks is another word."


def test_the_glossary_hints_name_terms_in_any_spelling():
    hints = glossary.Glossary(TERMS).hints("Carmin explained lead luck to everyone")
    assert [h["term"] for h in hints] == ["Carmen", "LeadLock"]
    assert hints[1] == {"term": "LeadLock", "kind": "product", "heard_as": ["lead luck"]}
    assert glossary.Glossary([]).hints("anything") == [] and glossary.Glossary([]).normalise("a") == "a"
