"""The outbound guard: the one place that decides whether anything may reach Slack or ClickUp.

Checked when a request is drafted and again at the moment it is sent:
  - the kill switch stops everything;
  - mode "off" (the default everywhere) stops everything;
  - mode "sandbox" allows only the allow-listed channel, DM users and ClickUp lists;
  - mode "live" is only ever set by hand on production.
A refusal happens before any call to the provider.
"""
from backend.config import get_settings

MODES = ("off", "sandbox", "live")


class OutboundRefused(RuntimeError):
    pass


def check(kind: str, target: str, *, clickup_list_id: str | None = None) -> None:
    s = get_settings()
    mode = (s.outbound_mode or "off").lower()
    if s.outbound_kill_switch:
        raise OutboundRefused("the outbound kill switch is on: nothing is sent")
    if mode not in MODES:
        raise OutboundRefused(f"unknown OUTBOUND_MODE {s.outbound_mode!r}: treated as off")
    if mode == "off":
        raise OutboundRefused("OUTBOUND_MODE is off: nothing is sent")
    if mode == "live":
        return
    if kind == "slack_post" and target not in s.outbound_sandbox_slack_channels:
        raise OutboundRefused(f"sandbox mode: channel {target} is not on the sandbox allow-list")
    if kind == "slack_dm" and target not in s.outbound_sandbox_slack_users:
        raise OutboundRefused(f"sandbox mode: Slack user {target} is not on the sandbox allow-list")
    if kind == "clickup_task_update":
        if not clickup_list_id:
            raise OutboundRefused("sandbox mode: the task's ClickUp list could not be confirmed")
        if clickup_list_id not in s.outbound_sandbox_clickup_lists:
            raise OutboundRefused(f"sandbox mode: ClickUp list {clickup_list_id} is not the sandbox list")
