"""The AI layer, built but off: contracts, prompts, checks, the OpenRouter client and the runner. No network:
OpenRouter is an httpx MockTransport, Gmail a stub."""
import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import func, select

from backend.config import get_settings
from backend.db import transaction
from backend.models.db import (ActionCandidate, AiRun, ConnectorAccount, ContentUnit, RecordAssociation, SourceRecord,
                               SourceScope, SourceVersion, WorkItem)
from backend.services.ai import contracts, openrouter, runner, skills, sweep, validate
from backend.services.ai.context import Refs
from backend.services.clients import mapping
from backend.services.read_models import portfolio
from backend.services.shared.hashing import sha256_text

SAID = "We will send the revised landing page by Friday so you can approve it."


def walk(node):
    if isinstance(node, dict):
        yield node
        for v in node.values():
            yield from walk(v)
    elif isinstance(node, list):
        for v in node:
            yield from walk(v)


@pytest.mark.parametrize("contract", [s.contract for s in skills.SKILLS.values()])
def test_every_contract_is_strict(contract):
    schema = contracts.strict_schema(contract)
    assert "$ref" not in json.dumps(schema) and "$defs" not in schema
    for node in walk(schema):
        if node.get("type") == "object" and "properties" in node:
            assert node["additionalProperties"] is False and set(node["required"]) == set(node["properties"])


def test_every_prompt_renders_with_its_blocks_and_rules():
    slots = {"meeting", "transcript", "client_card", "open_actions", "previous_digest", "client_emails",
             "internal_comms", "viktor_posts", "client_list", "calendar_event", "call_type", "leads_summary",
             "activity", "digests", "pack", "instructions", "call", "offered",
             # the call type's skill fills the call brief's system prompt (services/callprep/pack.py render)
             "skill_name", "purpose", "decide", "agenda", "leave_out", "guidance", "type_block", "type_block_title",
             "points", "questions", "watch", "highlights"}
    for skill in skills.SKILLS.values():
        system = skills.render(skill.system_file, {k: f"<{k}>" for k in slots})
        user = skills.render(skill.user_file, {k: f"<{k}>" for k in slots})
        assert "{{" not in system + user
        assert skill.name == "call_focus" or "Evidence rules" in system  # the focus pass only picks items
    with pytest.raises(KeyError):
        skills.render("meeting_digest.user.md", {})


def test_quotes_must_be_the_sources_own_words():
    assert validate.exact_quote("we will send the revised landing page", SAID) == "We will send the revised landing page"
    assert validate.exact_quote("we'll send a new page", SAID) is None
    refs = Refs()
    ref = refs.add("T", SAID, record_id=None)
    action = refs.add("A", "Revised landing page", action_ref="cu-1")
    check = validate.Checker(refs, names={"Jacqueline Rivers"}, meeting_date=datetime(2026, 11, 3).date())
    out = validate.check("meeting_digest", {
        "commitments": [{"text": "Send the page", "owner_side": "WIA", "owner_name": "Jacqueline", "due_phrase": "by Friday",
                         "due_date": "2026-11-06", "quote": "we will send the revised landing page by Friday", "ref": ref,
                         "matches_action": "A9"},
                        {"text": "Invented", "owner_side": "WIA", "owner_name": "Someone", "due_phrase": None,
                         "due_date": "2027-12-01", "quote": "words nobody said here", "ref": ref, "matches_action": None},
                        {"text": "Bad ref", "owner_side": "WIA", "owner_name": None, "due_phrase": None, "due_date": None,
                         "quote": SAID, "ref": "T99", "matches_action": None}],
        "decisions": [{"text": "x", "quote": "approve it", "ref": ref}],
        "action_updates": [{"action_ref": action, "signal": "progressed", "quote": "send the revised landing page", "ref": ref}],
        "answered": [], "covered": [], "open_asks": [], "summary": [], "recap_email": "", "call_type_guess": "other"}, check)
    first, invented = out["commitments"]
    assert first["verified"] and first["owner_name"] == "Jacqueline Rivers" and first["due_date"] == "2026-11-06"
    assert first["matches_action"] is None  # A9 was never shown
    assert not invented["verified"] and invented["owner_name"] is None and invented["due_date"] is None
    assert out["decisions"] == []  # "approve it" is in the source, but two words prove nothing
    assert len(out["action_updates"]) == 1 and check.dropped["commitments"] == 1


def answer(payload: dict, cost=0.012) -> dict:
    return {"model": "anthropic/claude-sonnet-5.5", "choices": [{"message": {"content": json.dumps(payload)}}],
            "usage": {"prompt_tokens": 1200, "completion_tokens": 300, "cost": cost}}


def test_client_routes_privately_and_repairs_once():
    sent = []

    def handler(request: httpx.Request):
        sent.append(json.loads(request.content))
        return httpx.Response(200, json=answer({"commitments": [], "action_updates": []} if len(sent) == 1 else
                                               {"commitments": [], "action_updates": [], "open_asks": []}))
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(get_settings(), "openrouter_api_key", "test-key")
        out = openrouter.call(contracts.EmailActions, model="anthropic/claude-haiku-5.5", system="s", user="u",
                              schema=contracts.strict_schema(contracts.EmailActions), max_tokens=100, reasoning="low",
                              client=httpx.Client(transport=httpx.MockTransport(handler)))
    assert out.repaired and out.cost_usd == pytest.approx(0.024) and len(sent) == 2
    body = sent[0]
    assert body["provider"]["zdr"] is True and body["provider"]["data_collection"] == "deny"
    assert body["response_format"]["json_schema"]["strict"] is True and body["reasoning"] == {"effort": "low"}
    assert "temperature" not in body


def test_client_fails_closed_when_no_private_endpoint():
    client = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(404, json={"error": {}})))
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(get_settings(), "openrouter_api_key", "test-key")
        with pytest.raises(openrouter.RoutingError):
            openrouter.call(contracts.EmailActions, model="m", system="s", user="u", schema={}, max_tokens=10,
                            reasoning=None, client=client)


@pytest.fixture
def meeting():
    with transaction() as s:
        b = mapping.create_client(s, name="Venue One", slug="venue-one", actor="t", discover=False)
        account = ConnectorAccount(id=uuid4(), provider="fathom", provider_account_id="team", expected_identity="team",
                                   credential_ref="FATHOM_API_KEY")
        s.add(account)
        s.flush()
        scope = SourceScope(id=uuid4(), connector_account_id=account.id, kind="recorder", external_id="team", name="Fathom",
                            state="approved", default_domain="meetings", association_mode="per_record")
        s.add(scope)
        s.flush()
        at = datetime.now(UTC) - timedelta(days=1)
        record = SourceRecord(id=uuid4(), connector_account_id=account.id, scope_id=scope.id, record_kind="fathom_recording",
                              external_id="42", occurred_at=at, admitted_at=at)
        s.add(record)
        s.flush()
        version = SourceVersion(id=uuid4(), record_id=record.id, version_key="v1", content_sha256="0" * 64,
                                parser_version="fathom-v2", content_state="content",
                                attributes={"title": "Monthly Strategy | Venue One", "invitees": [{"email": "a@x.com", "name": "Jacqueline Rivers"}]})
        s.add(version)
        s.flush()
        record.current_version_id = version.id
        s.add(ContentUnit(id=uuid4(), version_id=version.id, ordinal=0, unit_kind="transcript_segment",
                          locator={"timestamp": "00:01:00"}, text=SAID, text_sha256=sha256_text(SAID), domain="meetings",
                          occurred_at=at))
        s.add(RecordAssociation(id=uuid4(), record_id=record.id, business_id=b.id, basis="verified_contact"))
        return str(record.id)


DIGEST = {"summary": ["Page approval is next."], "decisions": [],
          "commitments": [{"text": "Send the revised landing page", "owner_side": "WIA", "owner_name": "Jacqueline",
                           "due_phrase": "by Friday", "due_date": None, "quote": "We will send the revised landing page by Friday",
                           "ref": "T1", "matches_action": None}],
          "action_updates": [], "answered": [], "covered": [{"item": "Landing page", "done": True}], "open_asks": [],
          "recap": {"greeting": "Hi! Thanks for the time today.",
                    "points": [{"text": "We'll send the revised landing page by Friday.", "refs": ["T1"]}],
                    "sign_off": "Talk soon, Jacqueline"},
          "call_type_guess": "strategy"}


def test_off_means_nothing_is_sent_or_queued(meeting):
    with transaction() as s:
        assert [d[0] for d in sweep.due(s)] == ["meeting_digest"]  # it knows what is due...
        assert sweep.sweep(s) == 0  # ...but queues nothing while off
    with pytest.raises(runner.AiRefused):
        runner.run("meeting_digest", meeting, client=httpx.Client(transport=httpx.MockTransport(
            lambda r: pytest.fail("a request was sent while AI_MODE=off"))))
    with transaction() as s:
        assert s.scalar(select(func.count()).select_from(AiRun)) == 0
        assert not s.execute(select(WorkItem).where(WorkItem.kind == runner.JOB)).first()


def test_preview_renders_the_real_prompt_without_sending(meeting):
    with transaction() as s:
        p = runner.prepare(s, "meeting_digest", meeting, fetch=lambda mid: {"authored": ""})
    assert "[T1]" in p.user and SAID in p.user and "Venue One" in p.user and "Evidence rules" in p.system


def test_live_run_stores_checked_output_candidates_and_the_recap(meeting, monkeypatch):
    monkeypatch.setattr(get_settings(), "ai_mode", "live")
    monkeypatch.setattr(get_settings(), "openrouter_api_key", "test-key")
    monkeypatch.setattr(get_settings(), "ai_monthly_budget_usd", 5.0)
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(200, json=answer(DIGEST))
    client = httpx.Client(transport=httpx.MockTransport(handler))
    run = runner.run("meeting_digest", meeting, client=client, fetch=lambda mid: {"authored": ""})
    assert run.state == "succeeded" and run.is_current and float(run.cost_usd) == pytest.approx(0.012)
    assert runner.run("meeting_digest", meeting, client=client, fetch=lambda mid: {"authored": ""}).id == run.id
    assert len(calls) == 1  # same inputs: never paid for twice
    with transaction() as s:
        [c] = s.execute(select(ActionCandidate)).scalars().all()
        assert (c.kind, c.status, c.verified, c.owner_name) == ("new", "proposed", True, "Jacqueline Rivers")
        assert s.execute(select(WorkItem).where(WorkItem.kind == portfolio.JOB)).first()
    built = portfolio.build()
    [recap] = built["recaps"]
    assert recap["commitments"][0]["status"] == "Proposed" and recap["email"].startswith("Hi")
    [item] = built["reviewItems"]
    assert item["reason"] == "AI proposal" and item["quote"].startswith("We will send")
    monkeypatch.setattr(get_settings(), "ai_monthly_budget_usd", 0.05)  # spent 0.012 + reserve 0.60 > 0.05
    with transaction() as s:
        s.execute(AiRun.__table__.update().values(input_hash="changed"))
    with pytest.raises(runner.AiRefused):
        runner.run("meeting_digest", meeting, client=client, fetch=lambda mid: {"authored": ""})


def test_history_moments_take_dates_and_sources_from_their_refs(monkeypatch):
    from backend.models.db import ReadModelSnapshot
    with transaction() as s:
        mapping.create_client(s, name="Venue One", slug="venue-one", actor="t", discover=False)
        s.add(ReadModelSnapshot(name="portfolio", built_at=datetime.now(UTC), payload={"events": [
            {"clientId": "venue-one", "date": "2026-09-30", "lane": "Meetings", "title": "September strategy call",
             "detail": "Calendar · Fathom · transcript", "sourceId": "kb-aaaaaaaaaaaa"},
            {"clientId": "venue-one", "date": "2026-10-08", "lane": "Communication", "title": "Inquiry-quality question",
             "detail": "Gmail · 1 message", "sourceId": "kb-bbbbbbbbbbbb"},
            {"clientId": "someone-else", "date": "2026-10-01", "lane": "Meetings", "title": "Not theirs", "sourceId": "kb-c"}]}))
    with transaction() as s:
        assert ("history_moments", "venue-one", datetime.now(UTC).strftime("%G-W%V")) in sweep.due(s)
        p = runner.prepare(s, "history_moments", "venue-one")
    assert "[H1] 2026-09-30 · Meetings · September strategy call" in p.user and "Not theirs" not in p.user
    monkeypatch.setattr(get_settings(), "ai_mode", "live")
    monkeypatch.setattr(get_settings(), "openrouter_api_key", "test-key")
    monkeypatch.setattr(get_settings(), "ai_monthly_budget_usd", 5.0)
    payload = {"moments": [
        {"kind": "Decision", "title": "Page approval comes first", "why": "Every change waits on it.", "refs": ["H1"]},
        {"kind": "Client signal", "title": "Lead quality questioned", "why": "Expect it to lead the next call.", "refs": ["H2", "H9"]},
        {"kind": "Risk", "title": "Invented", "why": "No source.", "refs": ["H42"]}]}
    client = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json=answer(payload))))
    run = runner.run("history_moments", "venue-one", client=client)
    assert run.subject_kind == "client" and run.checks["dropped"] == {"moments": 1}
    first, second = portfolio.build()["moments"]
    assert (first["date"], first["lane"], first["sourceIds"]) == ("2026-09-30", "Meetings", ["kb-aaaaaaaaaaaa"])
    assert second["sourceIds"] == ["kb-bbbbbbbbbbbb"] and second["kind"] == "Client signal"


# --- failures: what they cost, whether they retry, and what they never do --------------------------------------

@pytest.fixture
def live(monkeypatch):
    monkeypatch.setattr(get_settings(), "ai_mode", "live")
    monkeypatch.setattr(get_settings(), "openrouter_api_key", "test-key")
    monkeypatch.setattr(get_settings(), "ai_monthly_budget_usd", 50.0)


def runs_of(skill="meeting_digest"):
    with transaction() as s:
        return s.execute(select(AiRun).where(AiRun.skill == skill).order_by(AiRun.created_at)).scalars().all()


def no_email(mid):
    return {"authored": ""}


def test_a_schema_failure_is_billed_for_both_calls_and_never_retried(meeting, live):
    client = httpx.Client(transport=httpx.MockTransport(
        lambda r: httpx.Response(200, json={"choices": [{"message": {"content": "{not json"}}],
                                            "usage": {"prompt_tokens": 1000, "completion_tokens": 50, "cost": 0.05}})))
    with pytest.raises(openrouter.SchemaFailure) as caught:
        runner.run("meeting_digest", meeting, client=client, fetch=no_email)
    assert caught.value.retryable is False
    [run] = runs_of()
    assert (run.state, run.error_class, float(run.cost_usd), run.prompt_tokens) == ("failed", "ai_schema", 0.10, 2000)
    with transaction() as s:
        assert float(runner.month_spend(s, datetime.now(UTC))) == pytest.approx(0.10)


def test_a_timeout_is_charged_at_the_reserve_and_a_connect_error_at_nothing(meeting, live):
    def timeout(request):
        raise httpx.ReadTimeout("slow", request=request)

    def refused(request):
        raise httpx.ConnectError("down", request=request)
    for handler in (timeout, refused):
        with pytest.raises(openrouter.ProviderError) as caught:
            runner.run("meeting_digest", meeting, client=httpx.Client(transport=httpx.MockTransport(handler)), fetch=no_email)
        assert caught.value.retryable  # the job retries on the AI ladder
    estimated, unsent = runs_of()
    reserve = skills.SKILLS["meeting_digest"].max_cost_usd
    assert float(estimated.cost_usd) == reserve and estimated.checks["cost_estimated"] is True
    assert float(unsent.cost_usd) == 0 and "cost_estimated" not in unsent.checks


def test_anything_that_breaks_after_a_paid_answer_still_records_the_cost(meeting, live, monkeypatch):
    monkeypatch.setattr(validate, "check", lambda *a, **k: 1 / 0)
    client = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json=answer(DIGEST, cost=0.03))))
    with pytest.raises(ZeroDivisionError):
        runner.run("meeting_digest", meeting, client=client, fetch=no_email)
    [run] = runs_of()
    assert (run.state, float(run.cost_usd)) == ("failed", 0.03)


def test_out_of_credits_waits_and_a_refused_request_fails(meeting, live):
    from backend.services.shared.errors import ThrottledError
    for status, kind in ((402, openrouter.OutOfCredits), (400, openrouter.ProviderRejected)):
        client = httpx.Client(transport=httpx.MockTransport(lambda r, st=status: httpx.Response(st, json={})))
        with pytest.raises(kind):
            runner.run("meeting_digest", meeting, client=client, fetch=no_email)
    assert isinstance(openrouter.OutOfCredits("x"), ThrottledError) and openrouter.ProviderRejected.retryable is False


def _client_email(meeting_record_id):
    """One admitted client email the day before the meeting, so the digest reads Gmail."""
    with transaction() as s:
        record = s.get(SourceRecord, meeting_record_id)
        business_id = s.execute(select(RecordAssociation.business_id).where(RecordAssociation.record_id == record.id)).scalar()
        gmail = ConnectorAccount(id=uuid4(), provider="gmail", provider_account_id="hello@x", expected_identity="hello@x",
                                 credential_ref="GOOGLE_REFRESH_TOKEN")
        s.add(gmail)
        s.flush()
        at = record.occurred_at - timedelta(days=1)
        r = SourceRecord(id=uuid4(), connector_account_id=gmail.id, record_kind="gmail_message", external_id="m1",
                         occurred_at=at, admitted_at=at, qualification="metadata_only")
        s.add(r)
        s.flush()
        v = SourceVersion(id=uuid4(), record_id=r.id, version_key="v", content_sha256="0" * 64, parser_version="gmail-v3",
                          content_state="metadata_only", attributes={"from": "dana@venue.example", "subject": "Dates"})
        s.add(v)
        s.flush()
        r.current_version_id = v.id
        s.add(RecordAssociation(id=uuid4(), record_id=r.id, business_id=business_id, basis="verified_contact"))


def test_gmail_trouble_stops_the_run_before_anything_is_sent_but_a_deleted_email_is_skipped(meeting, live):
    from uuid import UUID

    from backend.services.shared.errors import AuthInvalidError, NotFoundError, ThrottledError
    _client_email(UUID(meeting))
    never = httpx.Client(transport=httpx.MockTransport(lambda r: pytest.fail("sent with half the email")))

    def expired(mid):
        raise AuthInvalidError("google refresh rejected")

    def throttled(mid):
        raise ThrottledError("429", retry_after=30)
    with pytest.raises(runner.SourceUnavailable):  # waits for the credential, no attempt used, nothing paid
        runner.run("meeting_digest", meeting, client=never, fetch=expired)
    with pytest.raises(ThrottledError):
        runner.run("meeting_digest", meeting, client=never, fetch=throttled)
    assert runs_of() == []

    def deleted(mid):
        raise NotFoundError("404")
    with transaction() as s:
        p = runner.prepare(s, "meeting_digest", meeting, fetch=deleted)
    assert p.checks["clipped"].get("client_emails") == 1 and not any(r.startswith("E") for r in p.refs.items)


def test_ai_jobs_retry_over_hours_then_fail_visibly_and_kb_ai_retry_requeues(meeting, monkeypatch):
    from backend.workers import queue as q
    from backend.workers import runner as worker
    with transaction() as s:
        q.enqueue(s, runner.JOB, "analysis", "ai:test", {"skill": "meeting_digest", "subject_id": meeting})
    outcome = [openrouter.ProviderError("OpenRouter kept answering 408/429/5xx")]

    def fail(*a, **k):
        raise outcome[0]
    monkeypatch.setattr(runner, "run", fail)

    def item():
        with transaction() as s:
            return s.execute(select(WorkItem).where(WorkItem.kind == runner.JOB)).scalar_one()

    def due_now():
        with transaction() as s:
            s.execute(WorkItem.__table__.update().values(next_run_at=q.db_now(s)))
    for n in range(len(runner.RETRY_DELAYS)):
        assert worker.run_one(["analysis"])
        assert (item().state, item().attempt) == ("retry_wait", n + 1)
        due_now()
    assert worker.run_one(["analysis"]) and item().state == "failed"  # the ladder (~11 h) ran out
    assert worker.crash_limit(runner.JOB, {"skill": "meeting_digest"}) > len(runner.RETRY_DELAYS)
    assert worker.retry_delays(runner.JOB, {"skill": "call_brief"}) == get_settings().retry_delays_seconds
    with transaction() as s:
        assert runner.requeue_failed(s, "meeting_digest") == 1
    assert (item().state, item().attempt) == ("pending", 0)
    outcome[0] = openrouter.SchemaFailure("still broken")
    assert worker.run_one(["analysis"]) and item().state == "failed"  # never retried: the same input fails again


def test_email_windows_missed_while_the_worker_was_down_are_still_due(meeting):
    from uuid import UUID
    _client_email(UUID(meeting))  # two days ago: not the latest window
    with transaction() as s:
        assert any(skill == "email_actions" for skill, _, _ in sweep.due(s))


# --- re-digests ------------------------------------------------------------------------------------------------

def _new_version(meeting_id, text):
    with transaction() as s:
        record = s.get(SourceRecord, meeting_id)
        old = s.get(SourceVersion, record.current_version_id)
        v = SourceVersion(id=uuid4(), record_id=record.id, version_key=str(uuid4()), content_sha256="1" * 64,
                          parser_version="fathom-v2", content_state="content",
                          attributes={**old.attributes, "summary_present": True})
        s.add(v)
        s.flush()
        s.add(ContentUnit(id=uuid4(), version_id=v.id, ordinal=0, unit_kind="transcript_segment", locator={},
                          text=text, text_sha256=sha256_text(text), domain="meetings", occurred_at=record.occurred_at))
        record.current_version_id = v.id


def test_a_new_version_with_the_same_transcript_is_not_digested_again(meeting, live):
    from uuid import UUID
    client = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json=answer(DIGEST))))
    runner.run("meeting_digest", meeting, client=client, fetch=no_email)
    _new_version(UUID(meeting), SAID)  # Fathom added its summary: same words
    with transaction() as s:
        assert not [d for d in sweep.due(s) if d[0] == "meeting_digest"]
    _new_version(UUID(meeting), SAID + " And the photos next week.")  # the transcript itself changed
    with transaction() as s:
        assert [d[0] for d in sweep.due(s) if d[0] == "meeting_digest"] == ["meeting_digest"]


def test_a_re_digest_never_proposes_what_an_admin_already_decided(meeting, live):
    from uuid import UUID
    client = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json=answer(DIGEST))))
    runner.run("meeting_digest", meeting, client=client, fetch=no_email)
    with transaction() as s:
        s.execute(ActionCandidate.__table__.update().values(status="approved"))
    _new_version(UUID(meeting), SAID + " And the photos next week.")
    with transaction() as s:
        p = runner.prepare(s, "meeting_digest", meeting, fetch=no_email)
    assert "Approved" in p.user  # the approved action is on the list the model reads
    second = runner.run("meeting_digest", meeting, client=client, fetch=no_email)  # the model proposes it anyway
    with transaction() as s:
        assert [c.status for c in s.execute(select(ActionCandidate)).scalars()] == ["approved"]
    assert second.checks["dropped"].get("already_decided") == 1


# --- the client recap email ------------------------------------------------------------------------------------

def test_the_recap_keeps_only_lines_from_what_was_said_with_the_client():
    refs = Refs()
    t = refs.add("T", "We will send the revised landing page by Friday and book the shoot for 12 May.")
    e_ok = refs.add("E", "Could you also check the gallery page?", finance=False, side="Client")
    e_money = refs.add("E", "Invoice 1042 is overdue.", finance=True, side="Client")
    e_ours = refs.add("E", "Internal note: push them on the retainer.", finance=False, side="Guest")
    refs.add("S", "between us they are three weeks late on the retainer payment again")
    v_ref = refs.add("V", "churn risk is high for this venue")
    check = validate.Checker(refs, names=set(), meeting_date=None)
    email = check.recap({"greeting": "Hi Dana,", "sign_off": "Thanks, Jacqueline", "points": [
        {"text": "We'll send the revised landing page by Friday.", "refs": [t]},
        {"text": "The shoot is booked for 12 May.", "refs": [t]},
        {"text": "We'll look at the gallery page too.", "refs": [e_ok]},
        {"text": "The shoot is booked for 14 May.", "refs": [t]},  # a figure the source doesn't hold
        {"text": "A reminder that invoice 1042 is due.", "refs": [e_money]},  # finance email
        {"text": "Let's talk about the retainer.", "refs": [e_ours]},  # not an email the client wrote
        {"text": "We know you are three weeks late on the retainer payment again.", "refs": [t]},  # copied from Slack
        {"text": "We want to keep you happy.", "refs": [v_ref]},  # cites Viktor
        {"text": "Next steps below.", "refs": []},  # cites nothing
        {"text": "We'll follow up.", "refs": ["T99"]}]})  # never shown
    assert email == ("Hi Dana,\n\nWe'll send the revised landing page by Friday.\nThe shoot is booked for 12 May.\n"
                     "We'll look at the gallery page too.\n\nThanks, Jacqueline")
    assert check.dropped["recap_points"] == 7
    nothing_safe = validate.Checker(refs, names=set(), meeting_date=None).recap(
        {"greeting": "Hi", "sign_off": "", "points": [{"text": "x", "refs": [v_ref]}]})
    assert nothing_safe == ""  # no draft: the host writes it
