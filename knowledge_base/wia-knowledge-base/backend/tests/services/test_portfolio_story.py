"""History by rule (one event per thing that happened), its milestones, and the fixed Profile field mapping."""
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

from backend.services.read_models.portfolio import history, profile_field

NOW = datetime(2026, 11, 6, 18, tzinfo=UTC)
ONB, CM = uuid4(), uuid4()


def rec(provider, days_ago, **attrs):
    r = SimpleNamespace(id=uuid4(), provider=provider, occurred_at=NOW - timedelta(days=days_ago), external_id=str(uuid4()),
                        scope_id=attrs.pop("scope", CM), parent_external_id=attrs.pop("parent", None), source_url=None)
    return r, SimpleNamespace(attributes=attrs)


def run(recs):
    ev = {r.id: "kb-" + r.id.hex[:12] for r, _ in recs}
    names = {ONB: "ONBOARDING CLIENTS / Venue · Checklist", CM: "ELEVATE Clients / Venue · Client Management"}
    return history("venue", recs, lambda r: r.provider, ev, names, lambda e: e.endswith("@venue.example"), NOW,
                   lambda v: v.attributes.get("_text", ""))


def ms(days_ago):
    return int((NOW - timedelta(days=days_ago)).timestamp() * 1000)


def test_one_event_per_thing_that_happened():
    recs = [
        rec("gmail", 3, thread_id="t1", subject="Spring dates", **{"from": "dana@venue.example"}),
        rec("gmail", 3, thread_id="t1", subject="Re: Spring dates", **{"from": "jo@agency.example"}),
        rec("slack", 2, channel="C1", ts="1.0", _text="Gallery is ready for review"),
        rec("slack", 2, channel="C1", ts="2.0", thread_ts="1.0", _text="Looks great"),
        rec("calendar", 5, summary="Monthly Strategy | Venue", parent="series-1"),
        rec("fathom", 5, title="Venue strategy", transcript_segments=120),
        rec("calendar", 40, summary="Monthly Strategy | Venue", parent="series-1"),
        rec("clickup", 9, name="Send the revised page", due_date=ms(2)),
        rec("drive", 60, name="Venue Onboarding Questionnaire"),
    ]
    events, _, rhythm = run(recs)
    by = {(e["lane"], e["date"]): e for e in events}
    mail = next(e for e in events if e["title"] == "Spring dates")
    assert mail["count"] == 2 and mail["from"] == "Both" and mail["lane"] == "Communication"
    thread = next(e for e in events if e["title"] == "Gallery is ready for review")
    assert thread["count"] == 2 and thread["from"] == "WIA"
    meeting = next(e for e in events if e["lane"] == "Meetings" and "transcript" in e["detail"] and "state" not in e)
    assert meeting["title"] == "Monthly Strategy | Venue" and meeting["detail"] == "Calendar · Fathom · transcript"
    assert any(e["lane"] == "Meetings" and e.get("state") == "no-transcript" for e in events)  # the older one, no recording
    task = next(e for e in events if e["lane"] == "Commitments")
    assert task["title"] == "Send the revised page" and task["state"] == "missed"
    assert any(e["lane"] == "Onboarding" and e["title"] == "Questionnaire returned" for e in events)
    assert rhythm == ["Monthly Strategy | Venue · recurring, 2 on record"]
    assert len(events) == len(by)


def test_onboarding_tasks_fold_into_steps_and_mark_completion():
    recs = [rec("clickup", 30, name=f"Step {i}", scope=ONB, date_done=ms(20 - i)) for i in range(3)]
    recs.append(rec("calendar", 30, summary="Welcome & Onboarding call"))
    events, milestones, _ = run(recs)
    made = next(e for e in events if e["lane"] == "Onboarding" and e["title"] == "3 onboarding tasks set up")
    assert made["count"] == 3
    assert [m["label"] for m in milestones] == ["Onboarding started", "Onboarding call", "Onboarding complete"]
    assert milestones[-1]["date"] == "2026-10-19"  # the last step done (Chicago date)
    _, open_ms, _ = run(recs + [rec("clickup", 30, name="Last step", scope=ONB)])
    assert "Onboarding complete" not in [m["label"] for m in open_ms]


def test_questionnaire_questions_land_in_fixed_fields():
    assert profile_field("What are your package prices?") == ("Offer", "Packages & pricing")
    assert profile_field("Describe your ideal couple") == ("Ideal client", "Who their couples are")
    assert profile_field("What sets you apart from other venues?") == ("Differentiators & proof", "What sets them apart")
    assert profile_field("Any words we should avoid?") == ("Voice", "Words to avoid")
    assert profile_field("What does success look like this year?") == ("Goals", "What success means")
    assert profile_field("What's your average couple's budget?") == ("Ideal client", "Budget")
    assert profile_field("Instagram handle") is None  # stays in the questionnaire, not the profile


# ---- Now → "Communication since the last call" --------------------------------------------------------------------
from backend.services.read_models.portfolio import client_comms

CLIENT, WIA, PARTNER = "dana@venue.example", "hello@agency.example", "pat@consultant.example"


def comms_window(recs, days=30):
    ev = {r.id: "kb-" + r.id.hex[:12] for r, _ in recs}
    side = lambda e: "Client" if e == CLIENT else "WIA" if e == WIA else None
    name = lambda e: {CLIENT: "Dana", WIA: "WIA team"}.get(e, e)
    author = lambda v: (v.attributes.get("_who", "Alex"), v.attributes.get("_party", "internal"), v.attributes.get("_text", ""))
    return client_comms(recs, lambda r: r.provider, ev, side, name, author, NOW, days)


def comms(recs, days=30):
    return comms_window(recs, days)[:2]


def test_the_window_starts_at_the_last_call_and_includes_that_days_mail():
    recs = [rec("gmail", 10, subject="Before the call", **{"from": CLIENT}),
            rec("calendar", 6, summary="Monthly Strategy | Venue", attendees=[{"email": CLIENT}]),
            rec("gmail", 6, subject="Recap", **{"from": WIA}),
            rec("gmail", 2, subject="Follow-up question", **{"from": CLIENT})]
    items, _, window = comms_window(recs)
    assert [c["text"] for c in items] == ["Follow-up question", "Recap", "Monthly Strategy | Venue"]
    assert window == {"since": items[-1]["date"], "call": "Monthly Strategy | Venue"}


def test_with_no_call_on_record_the_window_is_the_last_30_days():
    items, _, window = comms_window([rec("gmail", 20, subject="Dates", **{"from": CLIENT}),
                                     rec("gmail", 45, subject="Too old", **{"from": CLIENT})])
    assert [c["text"] for c in items] == ["Dates"] and window["call"] is None
    assert window["since"] == "2026-10-07"


def test_email_counts_by_who_wrote_it_and_partners_are_left_out():
    recs = [rec("gmail", 1, subject="Spring dates", **{"from": CLIENT}),
            rec("gmail", 2, subject="Re: Spring dates", **{"from": WIA}),
            rec("gmail", 3, subject="Intro", **{"from": PARTNER})]
    items, last = comms(recs)
    assert [(c["from"], c["who"], c["text"], c["channel"]) for c in items] == [
        ("Client", "Dana", "Spring dates", "Gmail"), ("WIA", "WIA team", "Re: Spring dates", "Gmail")]
    assert last["text"] == "Spring dates" and all(c["sourceId"].startswith("kb-") for c in items)


def test_the_teams_slack_threads_show_as_team_items_and_never_as_client_contact():
    recs = [rec("slack", 3, _party="internal", _who="Alex", _text="Gallery is ready", channel="C1", ts="1.0"),
            rec("slack", 1, _party="internal", _who="Sam", _text="Approved", channel="C1", ts="2.0", thread_ts="1.0"),
            rec("slack", 2, _party="internal", _who="Alex", _text="New pixel live", channel="C1", ts="3.0"),
            rec("slack", 2, _party="bot", _text="Daily ad report", channel="C1", ts="4.0"),
            rec("slack", 4, _party="client", _who="Dana", _text="Thanks, love it", channel="C1", ts="5.0")]
    items, last = comms(recs)
    assert [(c["from"], c["who"], c["text"], c["date"]) for c in items] == [
        ("Team", "Alex, Sam", "Gallery is ready · 2 messages", "2026-11-05"), ("Team", "Alex", "New pixel live", "2026-11-04"),
        ("Client", "Dana", "Thanks, love it", "2026-11-02")]
    assert last["from"] == "Client"
    assert comms(recs[:2])[1] is None  # team posts alone: no contact with the client


def test_one_call_per_meeting_day_the_invite_title_wins_and_cancelled_or_future_events_are_skipped():
    recs = [rec("fathom", 4, title="Venue strategy", invitees=[{"email": CLIENT}]),
            rec("calendar", 4, summary="Monthly Strategy | Venue", attendees=[{"email": CLIENT}, {"email": WIA}]),
            rec("calendar", 6, summary="Cancelled sync", status="cancelled", attendees=[{"email": CLIENT}]),
            rec("calendar", -2, summary="Next call", attendees=[{"email": CLIENT}])]
    items, _ = comms(recs)
    [call] = items
    assert (call["from"], call["channel"], call["text"], call["who"]) == ("Call", "Calendar", "Monthly Strategy | Venue", "Dana, WIA team")


def test_only_recent_items_are_listed_but_the_last_contact_looks_at_all_history():
    items, last = comms([rec("gmail", 40, subject="Old thread", **{"from": CLIENT})])
    assert items == [] and last["date"] == "2026-09-27" and last["channel"] == "Gmail"
    assert comms([]) == ([], None)


# ---- Meetings tab ------------------------------------------------------------------------------------------------
from backend.services.read_models.portfolio import meeting_list


def meetings(recs, links=None):
    ev = {r.id: "kb-" + r.id.hex[:12] for r, _ in recs}
    return meeting_list(recs, lambda r: r.provider, ev, links or {}, lambda e: e.split("@")[0], NOW)


def test_calendar_meetings_without_a_recording_are_listed_with_no_link():
    [m] = meetings([rec("calendar", 30, summary="Monthly Strategy | Venue", ical_uid="u1", attendees=[{"email": CLIENT}])])
    assert (m["source"], m["transcript"], m["type"], m["attendees"]) == ("Calendar", "Not found", "Monthly strategy", "dana")
    assert "link" not in m and m["recordId"]


def test_a_recording_joins_the_closest_meeting_that_day_and_brings_its_link():
    early = rec("calendar", 5, summary="Kickoff", ical_uid="a")
    late = rec("calendar", 5, summary="Monthly Strategy | Venue", ical_uid="b")
    late[0].occurred_at += timedelta(hours=4)
    fathom = rec("fathom", 5, title="Venue strategy", transcript_segments=80)
    fathom[0].occurred_at += timedelta(hours=4, minutes=2)
    fathom[0].source_url = "https://fathom.video/calls/1"
    by_title = {m["title"]: m for m in meetings([early, late, fathom])}
    assert by_title["Monthly Strategy | Venue"]["source"] == "Fathom" and by_title["Monthly Strategy | Venue"]["transcript"] == "Available"
    assert by_title["Monthly Strategy | Venue"]["link"] == "https://fathom.video/calls/1"
    assert by_title["Kickoff"]["source"] == "Calendar" and len(by_title) == 2


def test_copies_cancelled_and_future_invites_and_a_team_link():
    one = rec("calendar", 9, summary="Check-in", ical_uid="same")
    copy = rec("calendar", 9, summary="Check-in", ical_uid="same")
    copy[0].occurred_at = one[0].occurred_at
    listed = meetings([one, copy, rec("calendar", 8, summary="Off", status="cancelled"), rec("calendar", -3, summary="Next")],
                      links={one[0].id: "https://zoom.us/rec/abc"})
    [m] = listed
    assert (m["link"], m["linkSource"], m["transcript"]) == ("https://zoom.us/rec/abc", "Added by the team", "Recording link only")


def test_a_recording_with_no_invite_is_listed_on_its_own():
    [m] = meetings([rec("fathom", 3, title="Quick sync", invitees=[{"email": CLIENT}])])
    assert (m["title"], m["source"], m["transcript"]) == ("Quick sync", "Fathom", "Not found")


# ---- Accounts & sources: how much history each source holds ------------------------------------------------------
from backend.services.read_models.portfolio import scope_copy, source_copy


def run_(state, full=True, days_ago=1):
    return SimpleNamespace(state=state, window_start=None if full else NOW - timedelta(days=30), started_at=NOW - timedelta(days=days_ago))


def test_one_finished_full_copy_is_complete_even_if_a_later_recheck_failed():
    assert scope_copy([run_("failed"), run_("succeeded", days_ago=2)]) == ("complete", None)
    assert scope_copy([run_("running"), run_("succeeded", full=False)])[0] == "copying"
    assert scope_copy([run_("partial")])[0] == "incomplete"
    assert scope_copy([run_("succeeded", full=False)]) == ("window", NOW - timedelta(days=30))
    assert scope_copy([]) == ("none", None)


def test_a_source_is_linked_only_once_every_account_holds_its_whole_history():
    done = ("complete", None)
    assert source_copy([done, done], "calendar") == ("Linked", "")
    assert source_copy([done, ("incomplete", NOW)] + [("incomplete", NOW)] * 3, "calendar") == (
        "Partial", "Full history copy stopped short for 4 of 5 calendars")
    state, note = source_copy([("copying", NOW - timedelta(days=9))], "mailbox")
    assert state == "Partial" and note == "Full history still copying (started Oct 28, 2026)"
    assert source_copy([("window", NOW - timedelta(days=30)), ("none", None)], "list") == (
        "Partial", "Only copied from Oct 7, 2026 for 1 of 2 lists; History not copied yet for 1 of 2 lists")
    assert source_copy([done], "channel", blocked=True)[0] == "Blocked"


# ---- Account owner and team, from the work -----------------------------------------------------------------------
from collections import Counter

from backend.services.read_models.portfolio import (
    account_team,
    suggest_owner,
    team_signals,
)

AM, OPS, LEAD = "Ana", "Oli", "Lee"
WHO = {("clickup_user", "1"): AM, ("clickup_user", "2"): OPS, ("email", "ana@agency.example"): AM,
       ("email", "lee@agency.example"): LEAD}


def signals(recs):
    names = {CM: "ELEVATE Clients / Client Management", ONB: "ONBOARDING CLIENTS / Onboarding"}
    return team_signals(recs, lambda r: r.provider, names, lambda k, v: WHO.get((k, (v or "").lower())),
                        lambda v: v.attributes.get("_poster"), NOW)


def role(label):
    return [{"name": "Role", "label": label}]


def test_owner_signals_come_from_relationship_tasks_calls_and_email_within_90_days():
    recs = [rec("clickup", 10, name="Monthly strategy call prep", assignee_ids=[1]),
            rec("clickup", 10, name="Monthly strategy call prep", assignee_ids=[1], scope=ONB),  # not the CM list
            rec("clickup", 12, name="Fix pixel", assignee_ids=[1]),  # CM list but not relationship work
            rec("calendar", 5, summary="Monthly Strategy", attendees=[{"email": "Ana@agency.example"}, {"email": CLIENT}]),
            rec("calendar", 5, summary="Same day follow-up", attendees=[{"email": "ana@agency.example"}]),
            rec("calendar", -20, summary="Next", attendees=[{"email": "ana@agency.example"}]),
            rec("calendar", 3, summary="Off", status="cancelled", attendees=[{"email": "ana@agency.example"}]),
            rec("gmail", 2, **{"from": "ana@agency.example"}),
            rec("gmail", 120, **{"from": "ana@agency.example"}),  # older than 90 days
            rec("gmail", 2, **{"from": CLIENT})]
    owner, _, _ = signals(recs)
    assert sorted(k for n, k, _ in owner if n == AM) == ["call", "call", "email", "relationship"]


def test_roles_come_from_the_clickup_role_field_and_slack_posts():
    recs = [rec("clickup", 5, name="Build ads", assignee_ids=[1], custom_fields=role("Ads Manager")) for _ in range(2)]
    recs += [rec("clickup", 5, name="Workflow", assignee_ids=[2], custom_fields=role("GHL Specialist"))]  # only one
    recs += [rec("clickup", 5, name="Chase", assignee_ids=[3], custom_fields=role("Assistant"))]  # shared account
    recs += [rec("slack", 1, _poster=OPS) for _ in range(10)] + [rec("slack", 1, _poster=LEAD) for _ in range(12)]
    _, roles, slack = signals(recs)
    team = account_team(roles, slack, {AM: ["ads_google", "ads_meta"], OPS: ["operations"], LEAD: ["leadership"]})
    assert team == [{"name": AM, "role": "Google & Meta Ads"}, {"name": LEAD, "role": "Leadership"}, {"name": OPS, "role": "Operations"}]


def sig(name, kind, n, days_ago=5):
    return [(name, kind, NOW - timedelta(days=days_ago))] * n


def test_owner_confidence_and_the_leadership_fallback():
    high = suggest_owner(sig(AM, "relationship", 3) + sig(OPS, "call", 1) + sig(LEAD, "call", 9), [LEAD], NOW)
    assert (high["name"], high["confidence"], high["why"]) == (AM, "High", "3 relationship tasks in 90 days")
    medium = suggest_owner(sig(AM, "call", 2) + sig(AM, "email", 1) + sig(OPS, "call", 1), [LEAD], NOW)
    assert (medium["name"], medium["confidence"]) == (AM, "Medium")
    low = suggest_owner(sig(AM, "email", 2) + sig(OPS, "email", 2), [LEAD], NOW)
    assert (low["name"], low["confidence"], low["lead"]) == (LEAD, "Low", AM)
    assert suggest_owner([], [LEAD], NOW)["why"] == "No relationship tasks, client calls or emails in 90 days"


def test_a_quiet_confirmed_owner_is_flagged_when_someone_else_runs_the_account():
    signals_ = sig(AM, "relationship", 3) + sig(OPS, "email", 1, days_ago=80)
    assert suggest_owner(signals_, [LEAD], NOW, confirmed=OPS).get("changed") is True
    assert "changed" not in suggest_owner(signals_ + sig(OPS, "email", 1), [LEAD], NOW, confirmed=OPS)


def test_slack_only_members_are_labelled_by_their_function():
    team = account_team(Counter(), Counter({AM: 11, "Ivy": 10, "New": 15}), {AM: ["ads_google", "ads_meta"], "Ivy": ["creative"]})
    assert team == [{"name": AM, "role": "Google & Meta Ads"}, {"name": "Ivy", "role": "Creatives"}, {"name": "New", "role": "Team member"}]


def test_where_a_meta_specialist_is_on_the_account_the_both_person_handles_google():
    roles = Counter({(AM, "ads"): 3, ("Jo", "ads"): 2, ("Tia", "LeadLock copy, sequences & page design"): 2})
    team = account_team(roles, Counter(), {AM: ["ads_google", "ads_meta"], "Jo": ["ads_meta"]})
    assert team == [{"name": AM, "role": "Google Ads"}, {"name": "Jo", "role": "Meta Ads"}, {"name": "Tia", "role": "LeadLock copy, sequences & page design"}]


# ---- Client since: each engagement starts at the agreement behind it ---------------------------------------------
from backend.services.read_models.portfolio import engagements

LL, GM = uuid4(), uuid4()


def engaged(recs, leadlock=False):
    names = {LL: "LeadLock Onboarding", GM: "Google + Meta Onboarding", CM: "Client Management"}
    return engagements(recs, lambda r: r.provider, lambda sid: names.get(sid, ""), "ELEVATE", leadlock)


def test_each_engagement_takes_its_own_agreement_best_source_first():
    recs = [rec("clickup", 190, scope=LL, name="Kickoff"), rec("clickup", 70, scope=GM, name="Kickoff"),
            rec("clickup", 300, scope=CM, name="Monthly report"),  # not an engagement list
            rec("gmail", 191, subject="Contract Completed for Dana - Agency"),
            rec("drive", 190, name="LeadLock Countersigned Contract | Venue"),
            rec("gmail", 74, subject="Proposal Signed - Next Steps"), rec("gmail", 76, subject="Contract Completed for Dana"),
            rec("gmail", 70, subject="Re: Contract Completed for Dana"),  # a reply isn't the signing
            rec("drive", 73, name="ELEVATE Ads Management Countersigned Contract"),
            rec("calendar", 400, summary="Ads Consultation")]  # sales calls never start anything
    ll, gm = engaged(recs)
    assert (ll["type"], ll["start"], ll["basis"], ll["signed"]) == ("LeadLock", "2026-04-29", "From the signed agreement", "2026-04-29")
    assert (gm["type"], gm["start"], gm["basis"]) == ("Google + Meta ads", "2026-08-22", "From the signed agreement")
    [only] = engaged([rec("clickup", 70, scope=GM, name="Kickoff"), rec("gmail", 72, subject="Proposal Signed - Next Steps")])
    assert (only["start"], only["basis"]) == ("2026-08-26", "From the signed proposal")


def test_a_checklist_ticked_weeks_later_is_flagged_and_estimates_are_labelled():
    signed = rec("clickup", 70, scope=GM, name="Countersign Contract", date_done=ms(70))
    [gm] = engaged([signed, rec("gmail", 100, subject="Contract Completed for Dana")])
    assert gm["start"] == "2026-07-29" and gm["note"] == "The onboarding checklist marks it signed on Aug 28, 2026"
    [gm] = engaged([signed])
    assert (gm["start"], gm["basis"]) == ("2026-08-28", "From the onboarding checklist") and "signed" not in gm
    est, ll = engaged([rec("clickup", 20, scope=GM, name="Kickoff")], leadlock=True)
    assert (est["basis"], ll) == ("Estimated from the onboarding start", {"type": "LeadLock", "start": "", "basis": "Start not recorded"})


def test_slack_markup_reads_as_people_see_it():
    from backend.services.read_models.portfolio import slack_text
    names = {"U1": "Gia Lopez"}.get
    assert slack_text("<@U1> brief for <#C9|c_venue> is <https://x.example/a|here>, ping <!here> or <@U2>", names) == (
        "@Gia brief for #c_venue is here, ping @here or @someone")
    assert slack_text("see <https://x.example/a>") == "see https://x.example/a"


# ---- Owner to suggest for tasks no person holds (never written) ---------------------------------------------------
from backend.services.read_models.portfolio import suggest_task_owner

COPY = "LeadLock copy, sequences & page design"
FN = {"Cara": ["ads_google", "ads_meta"], "Jo": ["ads_meta"], "Tia": ["leadlock_copy"], "Dan": ["leadlock_technical"]}


def test_a_role_finds_its_person_on_the_account_team_first():
    team = [{"name": "Tia Two", "role": COPY}, {"name": "Cara", "role": "Google Ads"}, {"name": "Jo", "role": "Meta Ads"}]
    hint = suggest_task_owner("LeadLock Designer", "Write the nurture sequence", team, FN)
    assert hint == {"name": "Tia", "why": f"ClickUp Role “LeadLock Designer” → {COPY} on this account's team"}
    assert suggest_task_owner("Ads Manager", "Launch Meta retargeting", team, FN)["name"] == "Jo"
    assert suggest_task_owner("Ads Manager", "Launch Google Search campaign", team, FN)["name"] == "Cara"
    assert suggest_task_owner("Ads Manager", "Monthly ads review", team, FN)["name"] == "Cara or Jo"  # split account, unclear task


def test_without_that_role_on_the_team_wias_split_decides_and_some_roles_name_nobody():
    hint = suggest_task_owner("GHL Specialist", "Fix the workflow", [], FN)
    assert hint == {"name": "Dan", "why": "ClickUp Role “GHL Specialist” → Technical LeadLock at WIA (not seen on this account yet)"}
    assert suggest_task_owner("Ads Manager", "Launch Meta ads", [], FN)["name"] == "Cara"  # the one who does both
    for role in ("Assistant", "Client", "CEO", None):
        assert suggest_task_owner(role, "Anything", [], FN) is None
