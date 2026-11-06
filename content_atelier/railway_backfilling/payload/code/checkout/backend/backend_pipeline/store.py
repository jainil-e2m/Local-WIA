from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel

from .models import StageArtifact

T = TypeVar("T", bound=BaseModel)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def canonical_hash(value: Any) -> str:
    return sha256_text(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")))


class JsonStore:
    """Single-writer, atomic, file-backed store used before the production schema."""

    def __init__(self, root: Path):
        self.root = root

    def path(self, *parts: str) -> Path:
        path = self.root.joinpath(*parts).resolve()
        if not path.is_relative_to(self.root.resolve()):
            raise ValueError("Artifact path must remain inside the datastore")
        return path

    def write_json(self, relative: str, value: Any, *, overwrite: bool = False) -> Path:
        target = self.path(*relative.replace("\\", "/").split("/"))
        target.parent.mkdir(parents=True, exist_ok=True)
        # A completed immutable artifact is never overwritten. This also avoids
        # Windows file-provider races when replaying a source snapshot.
        if target.exists() and not overwrite:
            return target
        fd, temp_name = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                json.dump(value, handle, ensure_ascii=False, indent=2, default=str)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_name, target)
        except Exception:
            try:
                os.unlink(temp_name)
            except OSError:
                pass
            raise
        return target

    def read_json(self, relative: str) -> Any:
        with self.path(*relative.replace("\\", "/").split("/")).open(encoding="utf-8") as handle:
            return json.load(handle)

    def write_bytes(self, relative: str, value: bytes, *, overwrite: bool = False) -> Path:
        """Archive exact bytes atomically; never replace a different immutable artifact."""
        target = self.path(*relative.replace("\\", "/").split("/"))
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and not overwrite:
            if target.read_bytes() != value:
                raise ValueError(f"Immutable artifact differs: {target}")
            return target
        fd, temp_name = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(value)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_name, target)
        except Exception:
            try:
                os.unlink(temp_name)
            except OSError:
                pass
            raise
        return target

    def write_text(self, relative: str, value: str, *, overwrite: bool = False) -> Path:
        return self.write_bytes(relative, value.encode("utf-8"), overwrite=overwrite)

    def write_model(self, relative: str, value: BaseModel, *, overwrite: bool = False) -> Path:
        return self.write_json(relative, value.model_dump(mode="json"), overwrite=overwrite)

    def cache_artifact(self, artifact: StageArtifact, relative: str) -> None:
        self.write_model(relative, artifact)
        self.write_json(f"cache/artifacts/{artifact.request_fingerprint}.json", {"artifact_path": relative}, overwrite=True)

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
