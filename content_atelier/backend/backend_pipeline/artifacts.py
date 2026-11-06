"""The artifact store (plan 0.B7): where saved requests and responses, dossiers, cost files, intake originals and the
brand bundle live.

Callers speak to `JsonStore` (store.py) with relative keys such as `brief-runs/<run>/cost_summary.json`; a backend decides
where the bytes go. Two implementations:

* `LocalBackend`: a folder on disk (the default; `ATELIER_ARTIFACT_ROOT`), written atomically with fsync.
* `S3Backend`: an S3-compatible bucket (`ATELIER_ARTIFACT_STORE=s3`), for a platform where the API and every worker are
  separate containers with no shared disk (Railway). An object is written whole or not at all, so the same
  never-replace-an-immutable-artifact rules hold.

`store_for(settings)` is the one way production code opens the store. Keys are relative, use `/`, and cannot leave the
store. A bucket and its credentials are environment-only (they are secrets and endpoints, not behaviour).
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path


def clean_key(key: str) -> str:
    """A key as a store sees it: `/`-separated, relative, no empty or `..` segments."""
    parts = [p for p in str(key).replace("\\", "/").split("/") if p not in ("", ".")]
    if any(p == ".." for p in parts) or (parts and ":" in parts[0] and len(parts[0]) == 2):
        raise ValueError("Artifact path must remain inside the datastore")
    return "/".join(parts)


class ArtifactBackend:
    """What a store needs from its storage; keys are already cleaned."""

    description = ""

    def exists(self, key: str) -> bool:
        raise NotImplementedError

    def read(self, key: str) -> bytes:
        """The bytes, or FileNotFoundError."""
        raise NotImplementedError

    def write(self, key: str, data: bytes) -> None:
        """Store `data` whole, replacing whatever the key held (the caller decides about immutability)."""
        raise NotImplementedError

    def names(self, prefix: str) -> list[str]:
        """The immediate children under a prefix, files and folders alike, sorted. Empty when there are none."""
        raise NotImplementedError

    def modified(self, key: str) -> float:
        raise NotImplementedError

    def local(self, key: str) -> Path | None:
        """The key as a file on this machine, for backends that have one."""
        return None


class LocalBackend(ArtifactBackend):
    def __init__(self, root):
        self.root = Path(root)
        self.description = str(self.root)

    def path(self, key: str) -> Path:
        path = self.root.joinpath(*clean_key(key).split("/")).resolve() if clean_key(key) else self.root.resolve()
        if not path.is_relative_to(self.root.resolve()):
            raise ValueError("Artifact path must remain inside the datastore")
        return path

    local = path

    def exists(self, key):
        return self.path(key).exists()

    def read(self, key):
        return self.path(key).read_bytes()

    def write(self, key, data):
        target = self.path(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_name, target)
        except Exception:
            try:
                os.unlink(temp_name)
            except OSError:
                pass
            raise

    def names(self, prefix):
        folder = self.path(prefix)
        return sorted(p.name for p in folder.iterdir() if not p.name.endswith(".tmp")) if folder.is_dir() else []

    def modified(self, key):
        return self.path(key).stat().st_mtime


class S3Backend(ArtifactBackend):
    """Objects in one bucket under an optional prefix. `client` is a boto3 S3 client (a test passes a stand-in)."""

    def __init__(self, bucket: str, client, *, prefix: str = ""):
        self.bucket, self.client = bucket, client
        self.prefix = clean_key(prefix)
        self.description = f"s3://{bucket}/{self.prefix}".rstrip("/")

    def _key(self, key: str) -> str:
        key = clean_key(key)
        return f"{self.prefix}/{key}" if self.prefix and key else (self.prefix or key)

    @staticmethod
    def _missing(error) -> bool:
        code = str(getattr(error, "response", {}).get("Error", {}).get("Code", ""))
        return code in {"404", "NoSuchKey", "NotFound"} or getattr(error, "response", {}).get("ResponseMetadata", {}).get("HTTPStatusCode") == 404

    def exists(self, key):
        from botocore.exceptions import ClientError
        try:
            self.client.head_object(Bucket=self.bucket, Key=self._key(key))
            return True
        except ClientError as error:
            if self._missing(error):
                # A folder-like prefix counts as existing when something is stored beneath it.
                return bool(self.names(key))
            raise

    def read(self, key):
        from botocore.exceptions import ClientError
        try:
            return self.client.get_object(Bucket=self.bucket, Key=self._key(key))["Body"].read()
        except ClientError as error:
            if self._missing(error):
                raise FileNotFoundError(f"{self.description}/{clean_key(key)}") from error
            raise

    def write(self, key, data):
        self.client.put_object(Bucket=self.bucket, Key=self._key(key), Body=data)

    def names(self, prefix):
        base = self._key(prefix)
        base = base + "/" if base else ""
        found, token = set(), None
        while True:
            args = {"Bucket": self.bucket, "Prefix": base, "Delimiter": "/", **({"ContinuationToken": token} if token else {})}
            page = self.client.list_objects_v2(**args)
            found.update(p["Prefix"][len(base):].rstrip("/") for p in page.get("CommonPrefixes", []))
            found.update(o["Key"][len(base):] for o in page.get("Contents", []) if o["Key"] != base)
            token = page.get("NextContinuationToken") if page.get("IsTruncated") else None
            if not token:
                return sorted(n for n in found if n)

    def modified(self, key):
        return self.client.head_object(Bucket=self.bucket, Key=self._key(key))["LastModified"].timestamp()


def s3_client(environ=None):
    import boto3
    from botocore.config import Config
    env = os.environ if environ is None else environ
    return boto3.client(
        "s3", endpoint_url=env.get("ATELIER_S3_ENDPOINT") or None, region_name=env.get("ATELIER_S3_REGION") or "auto",
        aws_access_key_id=env.get("ATELIER_S3_ACCESS_KEY_ID") or None,
        aws_secret_access_key=env.get("ATELIER_S3_SECRET_ACCESS_KEY") or None,
        config=Config(s3={"addressing_style": "path" if env.get("ATELIER_S3_PATH_STYLE", "true") != "false" else "virtual"},
                      retries={"max_attempts": 5, "mode": "standard"}, connect_timeout=5, read_timeout=60))


def backend_for(root, environ=None, client=None) -> ArtifactBackend:
    """The backend the environment names: an S3-compatible bucket when `ATELIER_ARTIFACT_STORE=s3`, else the folder `root`."""
    env = os.environ if environ is None else environ
    kind = (env.get("ATELIER_ARTIFACT_STORE") or "local").strip().lower()
    if kind == "local":
        return LocalBackend(root)
    if kind != "s3":
        raise ValueError(f"ATELIER_ARTIFACT_STORE must be local or s3, not {kind!r}")
    bucket = env.get("ATELIER_S3_BUCKET", "").strip()
    if not bucket:
        raise ValueError("ATELIER_ARTIFACT_STORE=s3 needs ATELIER_S3_BUCKET")
    return S3Backend(bucket, client or s3_client(env), prefix=env.get("ATELIER_S3_PREFIX", ""))


def store_for(settings, environ=None, client=None):
    """The artifact store production code uses: `settings.artifact_root` locally, the bucket when the environment says so."""
    from .store import JsonStore
    return JsonStore(backend_for(settings.artifact_root, environ, client))


REFERENCE = "artifact:"


def read_reference(settings, reference, *, environ=None, client=None) -> bytes:
    """A configured file, local (a path) or in the store (`artifact:<key>`), as bytes. The brand bundle uses this, so a
    platform with no shared disk keeps it in the store beside everything else."""
    text = str(reference)
    if text.startswith(REFERENCE):
        return store_for(settings, environ, client).read_bytes(text[len(REFERENCE):])
    return Path(text).read_bytes()


def reference_exists(settings, reference, *, environ=None, client=None) -> bool:
    text = str(reference)
    if text.startswith(REFERENCE):
        return store_for(settings, environ, client).exists(text[len(REFERENCE):])
    return Path(text).is_file()


def copy_tree(source, target, *, dry_run: bool = False, verify: bool = True) -> dict:
    """Copy every file under the folder `source` into the store `target` (a JsonStore), key for key.

    This is how a backup of the artifact folder is restored into a bucket (and how a bucket is seeded from the
    developer's folder). A key that already holds the same bytes is skipped; one that holds different bytes is reported
    and left alone, because artifacts are immutable; nothing is ever deleted. With `verify`, every copied file is read
    back and compared."""
    root = Path(source)
    if not root.is_dir():
        raise ValueError(f"{root} is not a folder")
    copied = skipped = 0
    different, failed = [], []
    for path in sorted(p for p in root.rglob("*") if p.is_file() and not p.name.endswith(".tmp")):
        key = clean_key(path.relative_to(root).as_posix())
        data = path.read_bytes()
        if target.exists(key):
            if target.read_bytes(key) == data:
                skipped += 1
            else:
                different.append(key)
            continue
        if dry_run:
            copied += 1
            continue
        target.backend.write(key, data)
        copied += 1
        if verify and target.read_bytes(key) != data:
            failed.append(key)
    return {"copied": copied, "skipped": skipped, "different": different, "failed": failed, "dry_run": dry_run}


def main(argv=None) -> int:
    """python -m backend_pipeline.artifacts copy --from <folder> [--dry-run]: restore a folder into the configured store."""
    import argparse
    import json
    parser = argparse.ArgumentParser(prog="python -m backend_pipeline.artifacts")
    sub = parser.add_subparsers(dest="command", required=True)
    copy = sub.add_parser("copy", help="Copy a folder of artifacts into the store the environment names (never deletes or replaces)")
    copy.add_argument("--from", dest="source", required=True)
    copy.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    from .storage_config import StorageSettings
    result = copy_tree(args.source, store_for(StorageSettings.from_env()), dry_run=args.dry_run)
    print(json.dumps(result, indent=2))
    return 1 if result["different"] or result["failed"] else 0


if __name__ == "__main__":
    # Run as `python -m`, this file is `__main__`, a second copy of the module: `store.py` checks the backend against
    # `backend_pipeline.artifacts.ArtifactBackend`, so the copy must not build the store. Use the package's own module.
    from backend_pipeline.artifacts import main as package_main
    raise SystemExit(package_main())
