"""History by rule (one event per thing that happened), its milestones, and the fixed Profile field mapping."""
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

from backend.services.read_models.portfolio import history, profile_field

NOW = datetime(2026, 11, 6, 18, tzinfo=UTC)
ONB, CM = uuid4(), uuid4()


def rec(provider, days_ago, **attrs):
    r = SimpleNamespace(id=uuid4(), provider=provider, occurred_at=NOW - timedelta(days=days_ago), external_id=str(uuid4()),
                        scope_id=attrs.pop("scope", CM), parent_external_id=attrs.pop("parent", None))
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
