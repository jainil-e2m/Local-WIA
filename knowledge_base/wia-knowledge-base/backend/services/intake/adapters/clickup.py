"""ClickUp adapter. Scope = list. Record = task (comments are units of the task version).

Window semantics: tasks with date_updated inside the window (includes closed tasks
and subtasks). Full history (window_start=None) drops the filter.
"""
import json
from datetime import UTC, datetime

from backend.config import get_settings
from backend.models.domain.intake import (
    BusinessHint,
    ChangeBatch,
    DiscoveryResult,
    Gap,
    IdentityRef,
    IntakeContext,
    NormalisedRecord,
    ScopeCandidate,
    UnitIn,
)
from backend.services.intake.adapters.base import ConnectorIdentity
from backend.services.shared.errors import AuthInvalidError, NotFoundError, ScopeDeniedError
from backend.services.shared.http import ProviderClient

EXCLUDED_SPACE_NAMES = {"templates"}


def _ms(value) -> datetime | None:
    return datetime.fromtimestamp(int(value) / 1000, UTC) if value not in (None, "", "0") else None


def _option_label(field: dict) -> str | list[str] | None:
    """Decode drop_down/labels values (option index or id) to option names; 0 is a valid index."""
    options = (field.get("type_config") or {}).get("options") or []
    value = field.get("value")
    if not options or value is None:
        return None
    by_key = {}
    for o in options:
        by_key[str(o.get("id"))] = o.get("name") or o.get("label")
        if o.get("orderindex") is not None:
            by_key[str(o["orderindex"])] = o.get("name") or o.get("label")
    if isinstance(value, list):
        return [by_key.get(str(v)) for v in value if str(v) in by_key]
    return by_key.get(str(value))


def _person(u: dict | None) -> IdentityRef | None:
    if not u or not u.get("id"):
        return None
    return IdentityRef(external_key=str(u["id"]), display_name=u.get("username"), email=u.get("email"))


class ClickUpAdapter:
    provider = "clickup"
    parser_version = "clickup-v2"

    def __init__(self):
        s = get_settings()
        if not s.clickup_token or not s.clickup_team_id:
            raise AuthInvalidError("CLICKUP_TOKEN / CLICKUP_TEAM_ID not configured")
        self.team_id = s.clickup_team_id
        # 100 req/min per token on most plans: pace at 0.7 s
        self.http = ProviderClient("clickup", "https://api.clickup.com/api/v2/",
                                   headers={"Authorization": s.clickup_token}, min_interval_seconds=0.7)

    def identify(self) -> ConnectorIdentity:
        user = self.http.get_json("user")["user"]
        teams = self.http.get_json("team")["teams"]
        team = next((t for t in teams if str(t["id"]) == str(self.team_id)), None)
        if team is None:
            raise AuthInvalidError("clickup: configured team not authorised for this token")
        return ConnectorIdentity(provider_account_id=str(team["id"]),
                                 display_identity=f"{team['name']} via {user.get('username')}",
                                 expected_identity_value=str(team["id"]), granted_scopes=[],
                                 credential_ref="CLICKUP_TOKEN")

    def discover(self, hints: list[BusinessHint], window_start, window_end) -> DiscoveryResult:
        """Lists whose folder or name matches a client, plus every folder (or folderless list) in a
        configured client space, matched or not, so a new client surfaces for mapping. Archived folders
        and lists are included and flagged (G-02): they hold history the backfill needs."""
        result = DiscoveryResult()
        client_spaces = {n.strip().lower() for n in get_settings().clickup_client_spaces}
        spaces = self.http.get_json(f"team/{self.team_id}/space", {"archived": "false"})["spaces"]
        for space in spaces:
            if space["name"].strip().lower() in EXCLUDED_SPACE_NAMES:
                continue
            client_space = space["name"].strip().lower() in client_spaces
            for folder, lists in self._containers(space["id"]):
                folder_match = next((h for h in hints if folder and h.matches_text(folder["name"])), None)
                for lst in lists:
                    match = folder_match or next((h for h in hints if h.matches_text(lst["name"])), None)
                    if not match and not client_space:
                        continue  # only client-looking lists are proposed; the rest stay unregistered
                    archived = bool(lst.get("archived") or (folder and folder.get("archived")))
                    parent = f"{space['name']} / {folder['name']}" if folder else space["name"]
                    if match:
                        reason = f"{'folder' if folder_match else 'list'} name matches alias of {match.name}"
                    else:
                        reason = (f"{'folder' if folder else 'list'} in client space {space['name']}; "
                                  "no client matches: add the client or exclude")
                    result.scopes.append(ScopeCandidate(
                        kind="list", external_id=str(lst["id"]), name=lst["name"], parent_name=parent,
                        default_domain="actions", association_mode="dedicated",
                        suggested_business_id=match.business_id if match else None,
                        reason=("archived; " if archived else "") + reason,
                        stats={"task_count_hint": lst.get("task_count"), "archived": archived,
                               "client_container": (folder or lst)["name"] if client_space else None},
                    ))
        return result

    def _containers(self, space_id: str) -> list[tuple[dict | None, list[dict]]]:
        """(folder, lists) pairs for active and archived folders; lists deduplicated, archived included."""
        out = []
        for archived in ("false", "true"):
            for folder in self.http.get_json(f"space/{space_id}/folder", {"archived": archived})["folders"]:
                lists = {str(x["id"]): x for x in folder.get("lists", [])}
                for x in self.http.get_json(f"folder/{folder['id']}/list", {"archived": "true"})["lists"]:
                    lists.setdefault(str(x["id"]), x)
                out.append((folder, list(lists.values())))
            out += [(None, [lst]) for lst in self.http.get_json(f"space/{space_id}/list", {"archived": archived})["lists"]]
        return out

    def describe_scope(self, kind: str, external_id: str) -> ScopeCandidate:
        """Confirm a list exists and is readable before an admin adds it by ID (G-02)."""
        if kind != "list":
            raise NotFoundError(f"clickup: scopes are lists, not {kind}")
        lst = self.http.get_json(f"list/{external_id}")
        folder, space = lst.get("folder") or {}, lst.get("space") or {}
        parent = " / ".join(x for x in (space.get("name"), None if folder.get("hidden") else folder.get("name")) if x)
        return ScopeCandidate(kind="list", external_id=str(lst["id"]), name=lst["name"], parent_name=parent or None,
                              default_domain="actions", association_mode="dedicated", reason="added by ID",
                              stats={"archived": bool(lst.get("archived"))})

    def read_page(self, ctx: IntakeContext, checkpoint: dict) -> ChangeBatch:
        from backend.services.intake.adapters.readers import read_page
        return read_page(self, ctx, checkpoint)

    def backfill_page(self, ctx: IntakeContext, cursor: str | None) -> ChangeBatch:
        return self.read_page(ctx, json.loads(cursor) if cursor else {})

    def _comments(self, task_id: str) -> list[dict]:
        out, params = [], {}
        while True:
            batch = self.http.get_json(f"task/{task_id}/comment", params or None).get("comments", [])
            out.extend(batch)
            if len(batch) < 25:
                return out
            oldest = batch[-1]
            params = {"start": oldest["date"], "start_id": oldest["id"]}

    def _normalise(self, t: dict, comments: list[dict]) -> NormalisedRecord:
        creator = _person(t.get("creator"))
        units = []
        body = "\n\n".join(x for x in [t.get("name") or "", t.get("markdown_description") or t.get("text_content") or ""] if x)
        units.append(UnitIn(unit_kind="task_body", text=body, author=creator, occurred_at=_ms(t.get("date_created")),
                            locator={"kind": "clickup_task", "task_id": t["id"], "part": "body"}))
        for c in sorted(comments, key=lambda c: int(c.get("date") or 0)):
            text = c.get("comment_text") or ""
            if text.strip():
                units.append(UnitIn(unit_kind="task_comment", text=text, author=_person(c.get("user")),
                                    occurred_at=_ms(c.get("date")),
                                    locator={"kind": "clickup_comment", "task_id": t["id"], "comment_id": c["id"]}))
        assignees = [_person(a) for a in t.get("assignees", [])]
        status = t.get("status") or {}
        return NormalisedRecord(
            record_kind="clickup_task", external_id=t["id"], occurred_at=_ms(t.get("date_created")),
            provider_updated_at=_ms(t.get("date_updated")), source_url=t.get("url"),
            attributes={
                "name": t.get("name"), "custom_id": t.get("custom_id"),
                "status": {"id": status.get("id"), "status": status.get("status"), "type": status.get("type")},
                "assignee_ids": [a.external_key for a in assignees if a],
                "creator_id": creator.external_key if creator else None,
                "watcher_ids": [str(w.get("id")) for w in t.get("watchers", []) if w.get("id")],
                "due_date": t.get("due_date"), "start_date": t.get("start_date"),  # raw ms strings: date/time semantics kept for the reducer
                "date_done": t.get("date_done"), "date_closed": t.get("date_closed"),
                "parent": t.get("parent"), "list_id": (t.get("list") or {}).get("id"),
                "folder_id": (t.get("folder") or {}).get("id"), "space_id": (t.get("space") or {}).get("id"),
                "locations": [loc.get("id") for loc in t.get("locations", [])],
                "custom_fields": [{"id": f.get("id"), "name": f.get("name"), "type": f.get("type"),
                                   "value": f.get("value"), "label": _option_label(f)}
                                  for f in t.get("custom_fields", []) if "value" in f],
                "checklists": [{"name": c.get("name"),
                                "items": [{"name": i.get("name"), "resolved": i.get("resolved")} for i in c.get("items", [])]}
                               for c in t.get("checklists", [])],
                "tags": [tag.get("name") for tag in t.get("tags", [])],
                "comment_count": len(comments),
            },
            units=units, participants=[p for p in [creator, *assignees] if p], version_hint=None,
        )
