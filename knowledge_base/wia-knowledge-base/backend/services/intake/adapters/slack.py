"""Slack adapter. Scope = channel. Identity key = (workspace, channel, ts) as strings.

Window semantics ("activity in window"): a thread is in scope when its root OR any
reply falls inside the window; such threads are stored whole. Roots are read back
`slack_thread_lookback_days` before the window so replies to older roots are found.
Full history (window_start=None) reads the channel from the beginning.
"""
import json
from datetime import UTC, datetime, timedelta

from backend.config import get_settings
from backend.models.domain.intake import (
    BusinessHint,
    ChangeBatch,
    DiscoveryResult,
    IdentityRef,
    IntakeContext,
    NormalisedRecord,
    ScopeCandidate,
    UnitIn,
)
from backend.services.intake.adapters.base import ConnectorIdentity
from backend.services.shared.errors import AuthInvalidError, IntakeError, ScopeDeniedError
from backend.services.shared.http import ProviderClient

EXCLUDED_CHANNELS = {"wia-ai-team-testing"}


def _ts_to_dt(ts: str | None) -> datetime | None:
    return datetime.fromtimestamp(float(ts), UTC) if ts else None


class SlackAdapter:
    provider = "slack"
    parser_version = "slack-v2"

    def __init__(self):
        token = get_settings().slack_bot_token
        if not token:
            raise AuthInvalidError("SLACK_BOT_TOKEN not configured")
        # conversations.* for internal apps is Tier 3 (~50/min): pace at ~1.2 s
        self.http = ProviderClient("slack", "https://slack.com/api/",
                                   headers={"Authorization": f"Bearer {token}"}, min_interval_seconds=1.2)
        self._users: dict[str, IdentityRef] = {}
        self._workspace: str | None = None

    def _call(self, method: str, **params) -> dict:
        response = self.http.request("GET", method, params=params)
        data = response.json()
        if not data.get("ok"):
            error = data.get("error", "unknown")
            if error in ("invalid_auth", "not_authed", "token_revoked", "account_inactive"):
                raise AuthInvalidError(f"slack: {error}")
            if error in ("missing_scope", "not_in_channel", "channel_not_found", "access_denied"):
                raise ScopeDeniedError(f"slack: {error}")
            raise IntakeError(f"slack: {error}")
        if self._workspace is None and method == "auth.test":
            self._workspace = data.get("url")
        return data

    def identify(self) -> ConnectorIdentity:
        data = self._call("auth.test")
        scopes = self.http.request("GET", "auth.test").headers.get("x-oauth-scopes", "")
        return ConnectorIdentity(provider_account_id=data["team_id"], display_identity=f"{data['team']} ({data['user']})",
                                 expected_identity_value=data["team_id"],
                                 granted_scopes=[s for s in scopes.split(",") if s],
                                 credential_ref="SLACK_BOT_TOKEN")

    def discover(self, hints: list[BusinessHint], window_start, window_end) -> DiscoveryResult:
        result = DiscoveryResult()
        cursor = None
        while True:
            data = self._call("users.conversations", types="public_channel,private_channel",
                              exclude_archived="true", limit=200, **({"cursor": cursor} if cursor else {}))
            for ch in data.get("channels", []):
                name = ch.get("name", "")
                match = next((h for h in hints if h.matches_text(name)), None)
                reason = None
                if name in EXCLUDED_CHANNELS:
                    reason = "synthetic testing channel: never client evidence"
                elif match:
                    reason = f"channel name matches alias of {match.name}"
                result.scopes.append(ScopeCandidate(
                    kind="channel", external_id=ch["id"], name=f"#{name}", parent_name=None,
                    default_domain="communications",
                    association_mode="dedicated" if match else "per_record",
                    suggested_business_id=match.business_id if match else None, reason=reason,
                    stats={"private": ch.get("is_private"), "members": ch.get("num_members")},
                ))
            cursor = (data.get("response_metadata") or {}).get("next_cursor")
            if not cursor:
                break
        return result

    def _user(self, user_id: str | None) -> IdentityRef | None:
        if not user_id:
            return None
        if user_id not in self._users:
            try:
                info = self._call("users.info", user=user_id)["user"]
                profile = info.get("profile") or {}
                name = profile.get("real_name") or profile.get("display_name") or info.get("name")
                self._users[user_id] = IdentityRef(external_key=user_id, display_name=name,
                                                   email=profile.get("email"))
            except IntakeError:
                self._users[user_id] = IdentityRef(external_key=user_id)
        return self._users[user_id]

    def read_page(self, ctx: IntakeContext, checkpoint: dict) -> ChangeBatch:
        from backend.services.intake.adapters.readers import read_page
        return read_page(self, ctx, checkpoint)

    def backfill_page(self, ctx: IntakeContext, cursor: str | None) -> ChangeBatch:
        return self.read_page(ctx, json.loads(cursor) if cursor else {})

    def _replies(self, channel: str, ts: str) -> list[dict]:
        out, cursor = [], None
        while True:
            data = self._call("conversations.replies", channel=channel, ts=ts, limit=200,
                              **({"cursor": cursor} if cursor else {}))
            out.extend(data.get("messages", []))
            cursor = (data.get("response_metadata") or {}).get("next_cursor") if data.get("has_more") else None
            if not cursor:
                return out

    def _normalise(self, channel: str, m: dict) -> NormalisedRecord:
        author = self._user(m.get("user")) or (
            IdentityRef(external_key=f"bot:{m['bot_id']}", display_name=m.get("username")) if m.get("bot_id") else None)
        files = [{"id": f.get("id"), "name": f.get("name"), "mimetype": f.get("mimetype"), "size": f.get("size")}
                 for f in m.get("files", [])]
        text = m.get("text") or ""
        units = []
        if text.strip():
            units.append(UnitIn(unit_kind="message", text=text, author=author, occurred_at=_ts_to_dt(m["ts"]),
                                locator={"kind": "slack_message", "channel": channel, "ts": m["ts"],
                                         "thread_ts": m.get("thread_ts")}))
        notes = ["attachments are referenced, not parsed"] if files else []
        state = "content" if units else "metadata_only"
        edited = (m.get("edited") or {}).get("ts")
        return NormalisedRecord(
            record_kind="slack_message", external_id=f"{channel}:{m['ts']}",
            occurred_at=_ts_to_dt(m["ts"]), provider_updated_at=_ts_to_dt(edited),
            source_url=f"{(self._workspace or 'https://weddingindustryads.slack.com/').rstrip('/')}/archives/{channel}/p{m['ts'].replace('.', '')}",
            attributes={
                "channel": channel, "ts": m["ts"], "thread_ts": m.get("thread_ts"),
                "is_thread_root": m.get("thread_ts") in (None, m["ts"]), "reply_count": m.get("reply_count", 0),
                "subtype": m.get("subtype"), "bot_id": m.get("bot_id"), "edited_ts": edited,
                "reactions": [{"name": r.get("name"), "count": r.get("count"), "users": r.get("users", [])}
                              for r in m.get("reactions", [])],
                "files": files,
            },
            units=units, participants=[author] if author else [], content_state=state, coverage_notes=notes,
        )
