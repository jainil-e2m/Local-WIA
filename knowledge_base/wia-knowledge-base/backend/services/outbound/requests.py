"""Outbound requests: draft -> approved by a listed approver at an interactive terminal -> sent, once.

Nothing changes in Slack or ClickUp unless a person approves that exact request. The approval is bound
to the payload hash and expires (OUTBOUND_APPROVAL_TTL_HOURS). The guard is checked when drafting and
again when sending. ClickUp edits touch only owner (assignees), due date and status, use the acting
person's own connection, keep the prior values, and are re-read afterwards to confirm.
"""
import hashlib
import json
from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy import select

from backend.config import get_settings
from backend.models.db import AuditEvent
from backend.models.db.base import utcnow
from backend.models.db.outbound import OutboundRequest
from backend.services.outbound import clickup_oauth, guard

SLACK_API = "https://slack.com/api/"
CLICKUP_API = clickup_oauth.API
EDITABLE_FIELDS = ("status", "due_date", "assignees_add", "assignees_remove")


class OutboundError(RuntimeError):
    pass


def _hash(kind, target, payload, as_person_id) -> str:
    blob = json.dumps({"kind": kind, "target": target, "payload": payload,
                       "as": str(as_person_id) if as_person_id else None}, sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()


def _audit(s, actor, action, req, **details):
    s.add(AuditEvent(actor=actor, action=action, target_type="outbound_request", target_id=str(req.id),
                     details={"kind": req.kind, "target": req.target, **details}))


def _new(s, kind, target, payload, *, actor, as_person_id=None, preview=None) -> OutboundRequest:
    req = OutboundRequest(kind=kind, target=target, payload=payload, preview=preview or {},
                          payload_hash=_hash(kind, target, payload, as_person_id), as_person_id=as_person_id,
                          state="draft", drafted_by=actor, drafted_at=utcnow(), result={})
    s.add(req)
    s.flush()
    try:
        guard.check(kind, target, clickup_list_id=(preview or {}).get("list_id"))
    except guard.OutboundRefused as exc:
        req.state, req.error = "refused", str(exc)[:500]
    _audit(s, actor, f"outbound.{req.state}", req, reason=req.error)
    return req


# Drafting (no provider writes; ClickUp drafts only read the task)

def draft_slack_post(s, channel: str, text: str, *, actor: str) -> OutboundRequest:
    if not text.strip():
        raise OutboundError("empty message")
    return _new(s, "slack_post", channel, {"text": text}, actor=actor)


def draft_slack_dm(s, user_id: str, text: str, *, actor: str) -> OutboundRequest:
    if not text.strip():
        raise OutboundError("empty message")
    return _new(s, "slack_dm", user_id, {"text": text}, actor=actor)


def _due_ms(value: str | None) -> int | None:
    if not value:
        return None
    return int(datetime.strptime(value, "%Y-%m-%d").replace(hour=12, tzinfo=UTC).timestamp() * 1000)


def _read_task(token: str, task_id: str, http) -> dict:
    r = http.get(CLICKUP_API + f"task/{task_id}", headers={"Authorization": token},
                 timeout=get_settings().http_timeout_seconds)
    if r.status_code != 200:
        raise OutboundError(f"ClickUp task {task_id} could not be read (HTTP {r.status_code})")
    return r.json()


def draft_clickup_update(s, task_id: str, *, as_person_id, actor: str, status: str | None = None,
                         due_date: str | None = None, assignees_add=(), assignees_remove=(),
                         http=httpx) -> OutboundRequest:
    """Prepare an edit of owner / due date / status, made later with `as_person_id`'s own connection."""
    payload = {k: v for k, v in {"status": status, "due_date": _due_ms(due_date),
                                 "assignees_add": [str(a) for a in assignees_add],
                                 "assignees_remove": [str(a) for a in assignees_remove]}.items() if v}
    if not payload:
        raise OutboundError("nothing to change: give a status, a due date or an assignee")
    token = clickup_oauth.token_for(s, as_person_id)  # NotConnected if they haven't connected: no fallback
    task = _read_task(token, task_id, http)
    list_id = str((task.get("list") or {}).get("id") or "")
    if status:
        if status.strip().lower() == "closed":
            raise OutboundError('"Closed" is never set by the KB: use "done" (onboarding) or "complete"')
        lst = http.get(CLICKUP_API + f"list/{list_id}", headers={"Authorization": token},
                       timeout=get_settings().http_timeout_seconds).json()
        allowed = {st["status"].lower() for st in lst.get("statuses", [])}
        if allowed and status.lower() not in allowed:
            raise OutboundError(f'status "{status}" is not used in this list ({", ".join(sorted(allowed))})')
    preview = {"task_name": task.get("name"), "list_id": list_id, "list_name": (task.get("list") or {}).get("name"),
               "before": {"status": (task.get("status") or {}).get("status"), "due_date": task.get("due_date"),
                          "assignees": [str(a.get("id")) for a in task.get("assignees", [])]}}
    return _new(s, "clickup_task_update", str(task_id), payload, actor=actor, as_person_id=as_person_id,
                preview=preview)


# Approval (a person, one request at a time)

def approve(s, request_id, *, approver: str, typed: str, interactive: bool) -> OutboundRequest:
    """Approve one draft. Callers must pass interactive=True only when a person is at a real terminal."""
    req = s.get(OutboundRequest, request_id, with_for_update=True)
    if req is None:
        raise OutboundError("no such request")
    approvers = {a.strip().lower() for a in get_settings().outbound_approvers}
    if not interactive:
        raise OutboundError("approval needs a person at an interactive terminal")
    if approver.strip().lower() not in approvers:
        raise OutboundError(f"{approver!r} is not an approver (OUTBOUND_APPROVERS)")
    if req.state != "draft":
        raise OutboundError(f"request is {req.state}, not waiting for approval")
    if _expired(req.drafted_at):
        req.state = "expired"
        _audit(s, approver, "outbound.expired", req)
        raise OutboundError("this draft is older than the approval window: draft it again")
    if typed.strip().lower() != "yes":
        req.state = "rejected"
        _audit(s, approver, "outbound.rejected", req)
        raise OutboundError("not approved (only typing yes approves)")
    req.state, req.approved_by, req.approved_at, req.approved_hash = "approved", approver, utcnow(), req.payload_hash
    _audit(s, approver, "outbound.approved", req)
    return req


def reject(s, request_id, *, approver: str) -> OutboundRequest:
    req = s.get(OutboundRequest, request_id, with_for_update=True)
    if req is None or req.state not in ("draft", "approved"):
        raise OutboundError("nothing to reject")
    req.state = "rejected"
    _audit(s, approver, "outbound.rejected", req)
    return req


def _expired(when) -> bool:
    return when < utcnow() - timedelta(hours=get_settings().outbound_approval_ttl_hours)


# Sending (only approved, unchanged, unexpired requests; guard re-checked)

def send(s, request_id, *, slack_http=httpx, clickup_http=httpx) -> OutboundRequest:
    req = s.get(OutboundRequest, request_id, with_for_update=True)
    if req is None:
        raise OutboundError("no such request")
    if req.state == "sent":
        return req  # one approval, one send: a retry never sends twice
    if req.state != "approved":
        raise OutboundError(f"request is {req.state}: only approved requests are sent")
    if req.approved_hash != _hash(req.kind, req.target, req.payload, req.as_person_id):
        req.state, req.error = "refused", "request changed after approval"
        _audit(s, "system", "outbound.refused", req, reason=req.error)
        raise OutboundError(req.error)
    if _expired(req.approved_at):
        req.state = "expired"
        _audit(s, "system", "outbound.expired", req)
        raise OutboundError("approval expired: draft and approve again")
    try:
        if req.kind == "clickup_task_update":
            req.result = _send_clickup(s, req, clickup_http)
        else:
            guard.check(req.kind, req.target)
            req.result = _send_slack(req, slack_http)
    except guard.OutboundRefused as exc:
        req.state, req.error = "refused", str(exc)[:500]
        _audit(s, "system", "outbound.refused", req, reason=req.error)
        raise OutboundError(req.error) from exc
    except (OutboundError, clickup_oauth.ClickUpConnectError, httpx.HTTPError) as exc:
        req.state, req.error = "failed", str(exc)[:500]
        _audit(s, "system", "outbound.failed", req, reason=req.error)
        raise OutboundError(req.error) from exc
    req.state, req.sent_at = "sent", utcnow()
    _audit(s, req.approved_by or "system", "outbound.sent", req, result=req.result)
    return req


def _send_slack(req, http) -> dict:
    headers = {"Authorization": f"Bearer {get_settings().slack_bot_token}"}
    timeout = get_settings().http_timeout_seconds
    channel = req.target
    if req.kind == "slack_dm":
        opened = http.post(SLACK_API + "conversations.open", headers=headers, json={"users": req.target},
                           timeout=timeout).json()
        if not opened.get("ok"):
            raise OutboundError(f"Slack could not open the DM: {opened.get('error')}")
        channel = opened["channel"]["id"]
    sent = http.post(SLACK_API + "chat.postMessage", headers=headers,
                     json={"channel": channel, "text": req.payload["text"]}, timeout=timeout).json()
    if not sent.get("ok"):
        raise OutboundError(f"Slack refused the message: {sent.get('error')}")
    return {"channel": sent.get("channel", channel), "ts": sent.get("ts")}


def _send_clickup(s, req, http) -> dict:
    token = clickup_oauth.token_for(s, req.as_person_id)
    current = _read_task(token, req.target, http)
    guard.check(req.kind, req.target, clickup_list_id=str((current.get("list") or {}).get("id") or ""))
    body = {}
    if "status" in req.payload:
        body["status"] = req.payload["status"]
    if "due_date" in req.payload:
        body["due_date"], body["due_date_time"] = req.payload["due_date"], False
    if req.payload.get("assignees_add") or req.payload.get("assignees_remove"):
        body["assignees"] = {"add": [int(a) for a in req.payload.get("assignees_add", [])],
                             "rem": [int(a) for a in req.payload.get("assignees_remove", [])]}
    r = http.put(CLICKUP_API + f"task/{req.target}", headers={"Authorization": token}, json=body,
                 timeout=get_settings().http_timeout_seconds)
    if r.status_code != 200:
        raise OutboundError(f"ClickUp refused the edit (HTTP {r.status_code})")
    after = _read_task(token, req.target, http)
    confirmed = {"status": (after.get("status") or {}).get("status"), "due_date": after.get("due_date"),
                 "assignees": [str(a.get("id")) for a in after.get("assignees", [])]}
    problems = []
    if "status" in req.payload and (confirmed["status"] or "").lower() != req.payload["status"].lower():
        problems.append("status")
    if "due_date" in req.payload and str(confirmed["due_date"] or "") != str(req.payload["due_date"]):
        problems.append("due date")
    if any(a not in confirmed["assignees"] for a in req.payload.get("assignees_add", [])) or \
            any(a in confirmed["assignees"] for a in req.payload.get("assignees_remove", [])):
        problems.append("assignees")
    if problems:
        raise OutboundError(f"ClickUp accepted the edit but the re-read differs: {', '.join(problems)}")
    return {"before": req.preview.get("before"), "after": confirmed}


def pending(s) -> list[OutboundRequest]:
    return s.execute(select(OutboundRequest).where(OutboundRequest.state == "draft")
                     .order_by(OutboundRequest.drafted_at)).scalars().all()
