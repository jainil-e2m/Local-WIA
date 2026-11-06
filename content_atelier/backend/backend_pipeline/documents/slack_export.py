"""Slack export import (plan 1.B7): a workspace export as documents, one per thread.

The export is a folder (or a zip of one) holding `users.json`, `channels.json` and, for each channel, one JSON file of
messages per day. Each thread becomes one document whose passages are exactly the messages' original text, in order, each
with a locator (channel and timestamp) that resolves back to the exported message. A message with no thread is a thread of one.

Left out, and said so in the result: channels listed in `documents.slack_export.excluded_channels` (by default the testing
channel `wia-ai-team-testing`), join/leave/topic and other system messages, bot posts, deleted messages, and messages with no
text (an attachment alone). The export is client material: it goes to the artifact store and the database, never into git.
"""
from __future__ import annotations

import json
import zipfile
from pathlib import Path

from ..normalise.sources import LIVE_RESTRICTIONS, slack_threads
from ..settings_store import value as setting
from ..store import canonical_hash
from . import intake

SYSTEM_SUBTYPES = {"channel_join", "channel_leave", "channel_topic", "channel_purpose", "channel_name", "channel_archive",
                   "channel_unarchive", "pinned_item", "unpinned_item", "bot_add", "bot_remove", "bot_message", "reminder_add",
                   "group_join", "group_leave", "group_topic", "group_purpose", "group_name", "group_archive", "group_unarchive",
                   "tombstone", "sh_room_created", "sh_room_shared", "reply_broadcast_removed"}


class Export:
    """A readable view of an export folder or zip."""

    def __init__(self, path):
        self.path = Path(path)
        self.zip = zipfile.ZipFile(self.path) if self.path.is_file() and self.path.suffix.lower() == ".zip" else None
        if self.zip is None and not self.path.is_dir():
            raise ValueError("A Slack export is a folder or a .zip of one")
        self.names = self.zip.namelist() if self.zip else [p.relative_to(self.path).as_posix() for p in self.path.rglob("*.json")]
        # A zip may wrap everything in one top folder.
        self.prefix = ""
        if "users.json" not in self.names and "channels.json" not in self.names:
            roots = {n.split("/", 1)[0] for n in self.names if "/" in n}
            if len(roots) == 1 and f"{next(iter(roots))}/channels.json" in self.names:
                self.prefix = next(iter(roots)) + "/"

    def read(self, name: str):
        full = self.prefix + name
        raw = self.zip.read(full) if self.zip else (self.path / full).read_bytes()
        return json.loads(raw.decode("utf-8-sig"))

    def has(self, name: str) -> bool:
        return (self.prefix + name) in self.names

    def channel_files(self, channel_name: str) -> list[str]:
        base = f"{self.prefix}{channel_name}/"
        return sorted(n[len(self.prefix):] for n in self.names if n.startswith(base) and n.endswith(".json"))


def people_names(export: Export) -> dict[str, str]:
    if not export.has("users.json"):
        return {}
    names = {}
    for user in export.read("users.json"):
        profile = user.get("profile") or {}
        names[user["id"]] = profile.get("real_name") or user.get("real_name") or profile.get("display_name") or user.get("name") or user["id"]
    return names


def usable(message: dict) -> bool:
    # A post by an app or integration (`bot_id`) is automation, with or without the `bot_message` subtype (plan 2.B9).
    return (message.get("type", "message") == "message" and message.get("subtype") not in SYSTEM_SUBTYPES
            and not message.get("hidden") and not message.get("bot_id") and bool((message.get("text") or "").strip()) and "ts" in message)


def import_export(repo, path, *, workspace: str = "", actor: str = "local-cli") -> dict:
    """Import every included channel's threads as week-less documents. Idempotent: a thread already stored is not stored again."""
    from ..artifacts import store_for
    from ..normalise import NORMALISER_VERSION
    export = Export(path)
    if not export.has("channels.json"):
        raise ValueError("This does not look like a Slack export: channels.json is missing")
    channels = export.read("channels.json")
    users = people_names(export)
    with repo.connection() as conn:
        excluded_names = {str(n).lower().lstrip("#") for n in setting("documents.slack_export.excluded_channels", conn)}
    store = store_for(repo.settings)
    report = {"channels": [], "excluded_channels": [], "threads": 0, "new": 0, "unchanged": 0, "messages": 0, "skipped_messages": 0}
    created: list[str] = []
    with repo.connection() as conn:
        for channel in channels:
            name, channel_id = channel["name"], channel["id"]
            skip = name.lower() in excluded_names
            conn.execute("""INSERT INTO slack_channels(channel_id,name,workspace,included,exclusion_reason) VALUES (%s,%s,%s,%s,%s)
                ON CONFLICT (channel_id) DO UPDATE SET name=EXCLUDED.name,workspace=EXCLUDED.workspace,included=EXCLUDED.included,
                exclusion_reason=EXCLUDED.exclusion_reason,updated_at=now()""",
                         (channel_id, name, workspace or None, not skip, "Testing channel; not evidence." if skip else None))
            if skip:
                report["excluded_channels"].append(name)
                continue
            messages, skipped = [], 0
            for file in export.channel_files(name):
                for message in export.read(file):
                    if not usable(message):
                        skipped += 1
                        continue
                    messages.append({**message, "user_name": users.get(message.get("user"), message.get("user"))})
            report["messages"] += len(messages)
            report["skipped_messages"] += skipped
            for document in slack_threads(messages, channel_id, workspace=workspace, channel_name=name, use_restrictions=LIVE_RESTRICTIONS):
                thread = document["source_metadata"]["slack"]["thread_ts"]
                raw = json.dumps([m for m in messages if (m.get("thread_ts") or m["ts"]) == thread], sort_keys=True,
                                 ensure_ascii=False).encode("utf-8")
                report["threads"] += 1
                if intake.register(conn, store, {**document, "source_type": "slack"}, raw):
                    created.append(document["transcript_id"])
                    report["new"] += 1
                else:
                    report["unchanged"] += 1
            report["channels"].append({"name": name, "messages": len(messages)})
        queued = intake.queue_normalisation(conn, created, actor=actor, version=NORMALISER_VERSION)
    return {**report, "run_id": queued["run_id"], "jobs": len(queued["jobs"]), "export_hash": canonical_hash(sorted(export.names))[:16]}
