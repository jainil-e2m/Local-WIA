"""Shared pieces of the data-transfer tools (plan 7.B3, 7.B5, S.B10): the S3 handover bucket, checksums, what is never sent.

Run the tools from a terminal in `backend/` (they need only Python 3.12 and, to upload or download, `boto3`):

    python scripts/transfer/inventory.py        read-only: what is on this machine
    python scripts/transfer/pack_and_upload.py  dump, pack, checksum and upload to the handover bucket
    python scripts/transfer/fetch_and_verify.py download from the handover bucket, verify, unpack

The handover bucket is reached with the Railway CLI's login: when the TRANSFER_S3_* variables are not set, the tools link the Railway project
below (`railway link`), read the `transfer-inbox` bucket's S3 credentials with `railway bucket credentials`, and keep them in memory only.
With a token instead of a login (RAILWAY_API_TOKEN for a workspace token, RAILWAY_TOKEN for a project token), `whoami` and `link`
cannot work (a token has no user), so the project and environment are named by ID for `bucket credentials` alone.
The variables (TRANSFER_S3_ENDPOINT, TRANSFER_S3_BUCKET, TRANSFER_S3_ACCESS_KEY_ID, TRANSFER_S3_SECRET_ACCESS_KEY, and optionally
TRANSFER_S3_REGION and TRANSFER_S3_URL_STYLE) still win when set, for a machine without the CLI.
"""
from __future__ import annotations

import fnmatch
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

# A Windows console may use a code page that cannot print a client's file name; never let that stop a handover.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(errors="replace")
    except (AttributeError, ValueError):
        pass

CHUNK = 1024 * 1024
PART_BYTES = 256 * 1024 * 1024  # a packed part is cut near this size, so an interrupted upload resumes by part
SECRET_SCAN_LIMIT = 8 * 1024 * 1024  # larger files are not scanned as text (they are binary dumps or archives)

# Never packed, whatever the folder holds: credentials, keys, dependency and VCS folders, temporary files.
EXCLUDED_NAMES = (".env", ".env.*", "*.env", "*.pem", "*.key", "*.p12", "*.pfx", "id_rsa*", "id_ed25519*", "*.tmp", ".DS_Store", "Thumbs.db")
EXCLUDED_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", ".pytest_cache", ".ruff_cache", ".mypy_cache"}

# A file whose text looks like a live credential is left out of the pack and named in the manifest (the name only).
SECRET_PATTERNS = {
    "OpenRouter key": re.compile(rb"sk-or-v1-[A-Za-z0-9]{24,}"),
    "API key": re.compile(rb"\bsk-[A-Za-z0-9_-]{32,}"),
    "Slack token": re.compile(rb"\bxox[abprs]-[A-Za-z0-9-]{10,}"),
    "GitHub token": re.compile(rb"\b(?:ghp|gho|ghs|github_pat)_[A-Za-z0-9_]{20,}"),
    "AWS key": re.compile(rb"\bAKIA[0-9A-Z]{16}\b"),
    "private key": re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH |)PRIVATE KEY-----"),
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(CHUNK), b""):
            digest.update(block)
    return digest.hexdigest()


def human(size: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size} B"


def excluded_name(name: str) -> bool:
    return any(fnmatch.fnmatch(name, pattern) for pattern in EXCLUDED_NAMES)


def secret_in(path: Path) -> str | None:
    """The kind of credential a small file seems to contain, or None. Never returns the value."""
    try:
        if path.stat().st_size > SECRET_SCAN_LIMIT:
            return None
        data = path.read_bytes()
    except OSError:
        return None
    for kind, pattern in SECRET_PATTERNS.items():
        if pattern.search(data):
            return kind
    return None


def walk(root: Path):
    """Every regular file under `root` in a stable order, skipping the excluded folders. Yields (path, relative posix name)."""
    root = Path(root)
    for current, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in EXCLUDED_DIRS)
        for name in sorted(files):
            path = Path(current) / name
            if path.is_symlink() or not path.is_file():
                continue
            yield path, path.relative_to(root).as_posix()


RAILWAY_PROJECT = "3409333b-1844-456c-93f9-f572ba92eb92"  # Content Atelier (an identifier, not a secret)
RAILWAY_ENVIRONMENT = "production"
RAILWAY_ENVIRONMENT_ID = "28239d73-fe52-4d23-bf80-94a8064c5eb5"  # its production environment (an identifier, not a secret)
HANDOVER_BUCKET = "transfer-inbox"


def railway_environment() -> dict[str, str]:
    """TRANSFER_S3_* values read from the logged-in Railway CLI. Exits with what to do when it cannot."""
    cli = shutil.which("railway")
    if not cli:
        raise SystemExit("The Railway CLI is not installed and the TRANSFER_S3_* variables are not set. Install it (npm i -g @railway/cli) and run `railway login`.")

    token = any(os.environ.get(name, "").strip() for name in ("RAILWAY_API_TOKEN", "RAILWAY_TOKEN"))
    environ = {**os.environ, "RAILWAY_PROJECT_ID": RAILWAY_PROJECT, "RAILWAY_ENVIRONMENT_ID": RAILWAY_ENVIRONMENT_ID} if token else None

    def run(*args):
        return subprocess.run([cli, *args], capture_output=True, text=True, timeout=120, env=environ)

    if token:
        done = run("bucket", "credentials", "--bucket", HANDOVER_BUCKET, "--json")
    else:
        if run("whoami").returncode != 0:
            raise SystemExit("The Railway CLI is not logged in. Run `railway login` (or set RAILWAY_API_TOKEN), then run this again.")
        linked = run("link", "-p", RAILWAY_PROJECT, "-e", RAILWAY_ENVIRONMENT)
        if linked.returncode != 0:
            raise SystemExit("Could not open the Content Atelier Railway project with this login: " + (linked.stderr or linked.stdout).strip()[:300])
        done = run("bucket", "credentials", "--bucket", HANDOVER_BUCKET, "-e", RAILWAY_ENVIRONMENT, "--json")
    try:
        c = json.loads(done.stdout)
        return {"TRANSFER_S3_ENDPOINT": c["endpoint"], "TRANSFER_S3_BUCKET": c["bucketName"], "TRANSFER_S3_ACCESS_KEY_ID": c["accessKeyId"],
                "TRANSFER_S3_SECRET_ACCESS_KEY": c["secretAccessKey"], "TRANSFER_S3_REGION": c.get("region") or "auto",
                "TRANSFER_S3_URL_STYLE": c.get("urlStyle") or "virtual-host"}
    except (ValueError, KeyError, TypeError):
        # The answer holds the bucket's secret key whatever its format, so it is never printed; only the CLI's error is.
        why = done.stderr.strip()[:300] if done.returncode != 0 and done.stderr else "the answer was not the expected JSON"
        raise SystemExit("Could not read the handover bucket's credentials from Railway (" + why + "). Update the Railway CLI "
                         "(npm i -g @railway/cli) or set the TRANSFER_S3_* variables.") from None


class Handover:
    """The handover bucket, reached with the TRANSFER_S3_* variables. `client` may be injected (tests)."""

    def __init__(self, environ=None, client=None):
        env = os.environ if environ is None else environ
        required = ("TRANSFER_S3_ENDPOINT", "TRANSFER_S3_BUCKET", "TRANSFER_S3_ACCESS_KEY_ID", "TRANSFER_S3_SECRET_ACCESS_KEY")
        if client is None and any(not env.get(k, "").strip() for k in required):
            env = railway_environment()
        self.bucket = env.get("TRANSFER_S3_BUCKET", "").strip()
        if client is None:
            try:
                import boto3
                from boto3.s3.transfer import TransferConfig
                from botocore.config import Config
            except ImportError:
                raise SystemExit("Install boto3 first: pip install boto3") from None
            style = "path" if env.get("TRANSFER_S3_URL_STYLE", "virtual-host").strip() == "path" else "virtual"
            client = boto3.client("s3", endpoint_url=env["TRANSFER_S3_ENDPOINT"].strip(), region_name=env.get("TRANSFER_S3_REGION", "auto"),
                                  aws_access_key_id=env["TRANSFER_S3_ACCESS_KEY_ID"].strip(),
                                  aws_secret_access_key=env["TRANSFER_S3_SECRET_ACCESS_KEY"].strip(),
                                  config=Config(s3={"addressing_style": style}, retries={"max_attempts": 8, "mode": "standard"},
                                                connect_timeout=15, read_timeout=120))
            self.config = TransferConfig(multipart_threshold=64 * 1024 * 1024, multipart_chunksize=64 * 1024 * 1024, max_concurrency=4)
        else:
            self.config = None
        self.client = client

    def head(self, key: str) -> dict | None:
        try:
            return self.client.head_object(Bucket=self.bucket, Key=key)
        except Exception as error:  # a missing key is the expected answer; anything else surfaces on the next call
            code = getattr(error, "response", {}).get("Error", {}).get("Code", "")
            if code in {"404", "NoSuchKey", "NotFound"}:
                return None
            raise

    def has(self, key: str, size: int, sha256: str) -> bool:
        found = self.head(key)
        return bool(found) and found.get("ContentLength") == size and (found.get("Metadata") or {}).get("sha256") == sha256

    def upload(self, path: Path, key: str, sha256: str) -> None:
        extra = {"Metadata": {"sha256": sha256}}
        if self.config is not None:
            self.client.upload_file(str(path), self.bucket, key, ExtraArgs=extra, Config=self.config)
        else:
            self.client.upload_file(str(path), self.bucket, key, ExtraArgs=extra)

    def put_bytes(self, key: str, data: bytes, sha256: str) -> None:
        self.client.put_object(Bucket=self.bucket, Key=key, Body=data, Metadata={"sha256": sha256})

    def get_bytes(self, key: str) -> bytes:
        return self.client.get_object(Bucket=self.bucket, Key=key)["Body"].read()

    def download(self, key: str, path: Path) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.client.download_file(self.bucket, key, str(path))

    def keys(self, prefix: str) -> list[dict]:
        found, token = [], None
        while True:
            page = self.client.list_objects_v2(Bucket=self.bucket, Prefix=prefix, **({"ContinuationToken": token} if token else {}))
            found += [{"key": o["Key"], "size": o.get("Size")} for o in page.get("Contents", [])]
            token = page.get("NextContinuationToken") if page.get("IsTruncated") else None
            if not token:
                return found


def say(message: str) -> None:
    print(message, flush=True)


def fail(message: str) -> None:
    print(f"error: {message}", file=sys.stderr, flush=True)
    raise SystemExit(1)
