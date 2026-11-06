"""Outbound guard and approval: nothing reaches Slack or ClickUp without mode, allow-list and a typed yes."""
from datetime import timedelta
from types import SimpleNamespace

import pytest
from cryptography.fernet import Fernet
from sqlalchemy import select

from backend.config import get_settings
from backend.db import transaction
from backend.models.db import AuditEvent
from backend.models.db.base import utcnow
from backend.models.db.outbound import OutboundRequest
from backend.services.outbound import clickup_oauth, guard
from backend.services.outbound import requests as outbound
from backend.services.people import roster

CHANNEL, DM_USER, LIST, OTHER_LIST = "C000SANDBOX", "U000SANDBOX", "900000001", "900000002"


@pytest.fixture(autouse=True)
def sandbox(monkeypatch):
    s = get_settings()
    for k, v in {"outbound_mode": "sandbox", "outbound_kill_switch": False, "outbound_approvers": ["approver"],
                 "outbound_sandbox_slack_channels": [CHANNEL], "outbound_sandbox_slack_users": [DM_USER],
                 "outbound_sandbox_clickup_lists": [LIST], "kb_secret_key": Fernet.generate_key().decode(),
                 "slack_bot_token": "xoxb-example", "clickup_team_id": "9000001"}.items():
        monkeypatch.setattr(s, k, v)


class FakeSlack:
    def __init__(self):
        self.calls = []

    def post(self, url, headers=None, json=None, timeout=None):
        self.calls.append((url.rsplit("/", 1)[1], json))
        if url.endswith("conversations.open"):
            return SimpleNamespace(json=lambda: {"ok": True, "channel": {"id": "D000EXAMPLE"}})
        return SimpleNamespace(json=lambda: {"ok": True, "channel": json["channel"], "ts": "1.0001"})


class FakeClickUp:
    def __init__(self, list_id=LIST):
        self.task = {"id": "t1", "name": "Test task", "list": {"id": list_id, "name": "KB Sandbox"},
                     "status": {"status": "to do"}, "due_date": None, "assignees": []}
        self.writes = []

    def get(self, url, headers=None, timeout=None):
        if "/list/" in url:
            return SimpleNamespace(status_code=200, json=lambda: {"statuses": [{"status": "to do"}, {"status": "done"},
                                                                               {"status": "Closed"}]})
        return SimpleNamespace(status_code=200, json=lambda: dict(self.task))

    def put(self, url, headers=None, json=None, timeout=None):
        self.writes.append(json)
        if "status" in json:
            self.task["status"] = {"status": json["status"]}
        if "due_date" in json:
            self.task["due_date"] = str(json["due_date"])
        return SimpleNamespace(status_code=200, json=lambda: {})


@pytest.fixture
def alex():
    with transaction() as s:
        p = roster.create_person(s, name="Alex Example", kind="staff", actor="test")
        roster.add_address(s, p.id, "clickup_user", "10000001", actor="test")
        user = lambda: {"user": {"id": "10000001", "username": "Alex Example"}}
        fake = SimpleNamespace(get=lambda url, headers=None, timeout=None: SimpleNamespace(
            status_code=200, json=user if url.endswith("user") else (lambda: {"teams": [{"id": "9000001"}]})))
        clickup_oauth.connect(s, "tok-example", actor="test", http=fake)
        return p.id


def approve(s, req, typed="yes", approver="approver", interactive=True):
    return outbound.approve(s, req.id, approver=approver, typed=typed, interactive=interactive)


# Guard

@pytest.mark.parametrize("change", [{"outbound_mode": "off"}, {"outbound_kill_switch": True}, {"outbound_mode": "weird"}])
def test_off_kill_switch_and_unknown_mode_refuse_everything(monkeypatch, change):
    for k, v in change.items():
        monkeypatch.setattr(get_settings(), k, v)
    with pytest.raises(guard.OutboundRefused):
        guard.check("slack_post", CHANNEL)


def test_sandbox_allows_only_listed_targets():
    guard.check("slack_post", CHANNEL)
    guard.check("slack_dm", DM_USER)
    guard.check("clickup_task_update", "t1", clickup_list_id=LIST)
    for kind, target, lst in (("slack_post", "C000CLIENT", None), ("slack_dm", "U000OTHER", None),
                              ("clickup_task_update", "t1", OTHER_LIST), ("clickup_task_update", "t1", None)):
        with pytest.raises(guard.OutboundRefused):
            guard.check(kind, target, clickup_list_id=lst)


# Draft -> approve -> send

def test_nothing_is_sent_without_approval():
    slack = FakeSlack()
    with transaction() as s:
        req = outbound.draft_slack_post(s, CHANNEL, "test", actor="test")
        assert req.state == "draft"
        with pytest.raises(outbound.OutboundError, match="only approved"):
            outbound.send(s, req.id, slack_http=slack)
    assert slack.calls == []


def test_approved_post_and_dm_are_sent_once():
    slack = FakeSlack()
    with transaction() as s:
        post = outbound.draft_slack_post(s, CHANNEL, "hello", actor="test")
        dm = outbound.draft_slack_dm(s, DM_USER, "hi", actor="test")
        approve(s, post), approve(s, dm)
        outbound.send(s, post.id, slack_http=slack)
        outbound.send(s, dm.id, slack_http=slack)
        outbound.send(s, post.id, slack_http=slack)  # retry: no second send
        assert post.state == dm.state == "sent" and dm.result["channel"] == "D000EXAMPLE"
    assert [c[0] for c in slack.calls] == ["chat.postMessage", "conversations.open", "chat.postMessage"]


@pytest.mark.parametrize("kwargs,match", [({"interactive": False}, "interactive terminal"),
                                          ({"approver": "someone-else"}, "not an approver"),
                                          ({"typed": "y"}, "only typing yes")])
def test_approval_needs_a_listed_person_at_a_terminal_typing_yes(kwargs, match):
    with transaction() as s:
        req = outbound.draft_slack_post(s, CHANNEL, "hello", actor="test")
        with pytest.raises(outbound.OutboundError, match=match):
            approve(s, req, **kwargs)
        assert req.state in ("draft", "rejected")


def test_target_outside_sandbox_is_refused_at_draft_and_never_approvable():
    with transaction() as s:
        req = outbound.draft_slack_post(s, "C000CLIENT", "hello", actor="test")
        assert req.state == "refused"
        with pytest.raises(outbound.OutboundError, match="not waiting"):
            approve(s, req)


def test_kill_switch_after_approval_still_stops_the_send(monkeypatch):
    slack = FakeSlack()
    with transaction() as s:
        req = outbound.draft_slack_post(s, CHANNEL, "hello", actor="test")
        approve(s, req)
        monkeypatch.setattr(get_settings(), "outbound_kill_switch", True)
        with pytest.raises(outbound.OutboundError, match="kill switch"):
            outbound.send(s, req.id, slack_http=slack)
        assert req.state == "refused"
    assert slack.calls == []


def test_changed_request_after_approval_is_refused():
    slack = FakeSlack()
    with transaction() as s:
        req = outbound.draft_slack_post(s, CHANNEL, "hello", actor="test")
        approve(s, req)
        req.payload = {"text": "something else"}
        s.flush()
        with pytest.raises(outbound.OutboundError, match="changed after approval"):
            outbound.send(s, req.id, slack_http=slack)
    assert slack.calls == []


def test_old_drafts_and_old_approvals_expire():
    with transaction() as s:
        old = outbound.draft_slack_post(s, CHANNEL, "hello", actor="test")
        old.drafted_at = utcnow() - timedelta(hours=25)
        with pytest.raises(outbound.OutboundError, match="older than the approval window"):
            approve(s, old)
        req = outbound.draft_slack_post(s, CHANNEL, "hello", actor="test")
        approve(s, req)
        req.approved_at = utcnow() - timedelta(hours=25)
        with pytest.raises(outbound.OutboundError, match="expired"):
            outbound.send(s, req.id, slack_http=FakeSlack())


# ClickUp edits

def test_clickup_edit_uses_own_connection_keeps_prior_values_and_confirms(alex):
    cu = FakeClickUp()
    with transaction() as s:
        req = outbound.draft_clickup_update(s, "t1", as_person_id=alex, actor="test", status="done", http=cu)
        assert req.preview["before"]["status"] == "to do" and req.preview["list_id"] == LIST
        approve(s, req)
        outbound.send(s, req.id, clickup_http=cu)
        assert req.state == "sent" and req.result["after"]["status"] == "done"
    assert cu.writes == [{"status": "done"}]


def test_clickup_edit_outside_sandbox_list_is_refused(alex):
    with transaction() as s:
        req = outbound.draft_clickup_update(s, "t1", as_person_id=alex, actor="test", status="done",
                                            http=FakeClickUp(list_id=OTHER_LIST))
        assert req.state == "refused"


def test_clickup_never_sets_closed_and_needs_a_connection(alex):
    with transaction() as s:
        with pytest.raises(outbound.OutboundError, match="Closed"):
            outbound.draft_clickup_update(s, "t1", as_person_id=alex, actor="test", status="Closed", http=FakeClickUp())
        nobody = roster.create_person(s, name="Sam Sample", kind="staff", actor="test")
        with pytest.raises(clickup_oauth.NotConnected):
            outbound.draft_clickup_update(s, "t1", as_person_id=nobody.id, actor="test", status="done", http=FakeClickUp())


def test_every_step_is_audited():
    with transaction() as s:
        req = outbound.draft_slack_post(s, CHANNEL, "hello", actor="test")
        approve(s, req)
        outbound.send(s, req.id, slack_http=FakeSlack())
        actions = s.execute(select(AuditEvent.action).where(AuditEvent.target_id == str(req.id))
                            .order_by(AuditEvent.created_at)).scalars().all()
    assert actions == ["outbound.draft", "outbound.approved", "outbound.sent"]
