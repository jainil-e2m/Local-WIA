from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel

from .artifacts import ArtifactBackend, LocalBackend, clean_key
from .models import StageArtifact

T = TypeVar("T", bound=BaseModel)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def canonical_hash(value: Any) -> str:
    return sha256_text(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")))


class JsonStore:
    """Single-writer, atomic store of immutable artifacts, over a folder or an S3-compatible bucket (artifacts.py).

    `root` is a folder (or an `ArtifactBackend`). Keys are relative and `/`-separated. The local backend also offers
    `path()`, for the tools that work on files directly; code that must run on any backend uses `exists`, `read_bytes`,
    `read_text`, `names` and `modified` instead.
    """

    def __init__(self, root):
        self.backend = root if isinstance(root, ArtifactBackend) else LocalBackend(root)
        self.root = self.backend.root if isinstance(self.backend, LocalBackend) else self.backend.description

    def path(self, *parts: str) -> Path:
        if not isinstance(self.backend, LocalBackend):
            raise NotImplementedError(f"{self.backend.description} is not a folder; use exists, read_bytes or names")
        return self.backend.path("/".join(parts))

    def exists(self, relative: str) -> bool:
        return self.backend.exists(clean_key(relative))

    def names(self, relative: str) -> list[str]:
        return self.backend.names(clean_key(relative))

    def modified(self, relative: str) -> float:
        return self.backend.modified(clean_key(relative))

    def read_bytes(self, relative: str) -> bytes:
        return self.backend.read(clean_key(relative))

    def read_text(self, relative: str) -> str:
        return self.read_bytes(relative).decode("utf-8")

    def attempt_files(self, folder: str, fingerprint: str, filename: str) -> list[str]:
        """Keys `<folder>/<attempt>/<fingerprint>/<filename>` that exist, newest attempt name first."""
        base = clean_key(folder)
        keys = [f"{base}/{n}/{fingerprint}/{filename}" for n in self.backend.names(base)]
        return sorted((k for k in keys if self.backend.exists(k)), reverse=True)

    def json_names(self, relative: str) -> list[str]:
        """Keys of the `.json` files directly under a folder, sorted."""
        base = clean_key(relative)
        return [f"{base}/{n}" for n in self.backend.names(base) if n.endswith(".json")]

    def write_json(self, relative: str, value: Any, *, overwrite: bool = False):
        key = clean_key(relative)
        # A completed immutable artifact is never overwritten. This also avoids
        # Windows file-provider races when replaying a source snapshot.
        if not overwrite and self.backend.exists(key):
            return self.backend.local(key)
        self.backend.write(key, (json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n").encode("utf-8"))
        return self.backend.local(key)

    def read_json(self, relative: str) -> Any:
        return json.loads(self.read_bytes(relative).decode("utf-8"))

    def write_bytes(self, relative: str, value: bytes, *, overwrite: bool = False):
        """Archive exact bytes atomically; never replace a different immutable artifact."""
        key = clean_key(relative)
        if not overwrite and self.backend.exists(key):
            if self.backend.read(key) != value:
                raise ValueError(f"Immutable artifact differs: {self.backend.description}/{key}")
            return self.backend.local(key)
        self.backend.write(key, value)
        return self.backend.local(key)

    def write_text(self, relative: str, value: str, *, overwrite: bool = False):
        return self.write_bytes(relative, value.encode("utf-8"), overwrite=overwrite)

    def write_model(self, relative: str, value: BaseModel, *, overwrite: bool = False) -> Path:
        return self.write_json(relative, value.model_dump(mode="json"), overwrite=overwrite)

    def cache_artifact(self, artifact: StageArtifact, relative: str) -> None:
        self.write_model(relative, artifact)
        self.write_json(f"cache/artifacts/{artifact.request_fingerprint}.json", {"artifact_path": relative}, overwrite=True)

    def saved_attempts(self, fingerprint: str) -> list[tuple[JsonStore, str]]:
        """Earlier attempts for one exact request that saved a received output, newest first."""
        try:
            folder = f"service_calls/{clean_key(fingerprint)}/attempts"
            names = self.names(folder)
        except ValueError:
            return []
        found = [n for n in names if self.exists(f"{folder}/{n}/output.received.json")]
        found.sort(key=lambda n: (self.modified(f"{folder}/{n}/output.received.json"), n), reverse=True)
        return [(self, f"{folder}/{n}") for n in found]

    def find_artifact(self, fingerprint: str) -> dict | None:
        # Older cache files omit model/provider identity and may contain fake
        # results. Retain them as history, but never promote them into v2 reuse.
        try:
            pointer = self.read_json(f"cache/artifacts/{fingerprint}.json")
            data = self.read_json(pointer["artifact_path"])
        except (OSError, ValueError, KeyError, TypeError):
            return None
        if not isinstance(data, dict):
            return None
        if data.get("cache_version") != 2 or data.get("status") != "validated" or data.get("request_fingerprint") != fingerprint:
            return None
        if data.get("output_hash") != canonical_hash(data.get("output")):
            return None
        return data
