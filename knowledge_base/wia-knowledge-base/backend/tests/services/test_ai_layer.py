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
             "activity", "digests"}
    for skill in skills.SKILLS.values():
        system = skills.render(skill.system_file, {})
        user = skills.render(skill.user_file, {k: f"<{k}>" for k in slots})
        assert "Evidence rules" in system and "{{" not in system + user
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
          "recap_email": "Hi! We'll send the page by Friday.", "call_type_guess": "strategy"}


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
