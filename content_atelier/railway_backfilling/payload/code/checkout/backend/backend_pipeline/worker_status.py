"""Shared-volume liveness; no credentials or content are written here."""

import os
import socket
from datetime import UTC, datetime, timedelta

from .store import JsonStore


def heartbeat(settings):
    store = JsonStore(settings.artifact_root)
    name = f"{socket.gethostname()}-{os.getpid()}"
    store.write_json(f"workers/editorial-{name}.json", {"last_seen": datetime.now(UTC).isoformat()}, overwrite=True)


def ready(settings):
    store = JsonStore(settings.artifact_root)
    cutoff = datetime.now(UTC) - timedelta(seconds=150)
    for path in store.path("workers").glob("editorial-*.json"):
        try:
            import json

            value = json.loads(path.read_text(encoding="utf-8"))
            if datetime.fromisoformat(value["last_seen"]) >= cutoff:
                return True
        except (ValueError, KeyError, OSError):
            continue
    return False
