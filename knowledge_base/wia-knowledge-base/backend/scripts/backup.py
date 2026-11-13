"""Nightly database backups to a bucket, in place of Railway's volume backups (which need a Pro workspace).

The `db-backup` cron service runs `python -m backend.scripts.backup dump` once a night. One run:

1. opens a read-only REPEATABLE READ transaction and exports its snapshot;
2. runs `pg_dump --snapshot` on that snapshot, so the dump and the row counts in its manifest describe the same instant
   while the workers keep writing;
3. checks the file with `pg_restore --list`, uploads it, then streams it back and compares SHA-256 and size;
4. writes the manifest last (a dump without a manifest is an unfinished run and is never chosen to restore);
5. once every RESTORE_CHECK_EVERY, restores that dump into a scratch database on the same server, compares every
   table's count with the manifest, and always drops the scratch database;
6. only then prunes: the newest 14 dumps, the newest of each of the last 8 weeks and of the last 12 months.

Any failure exits non-zero before anything is deleted, so the cron run shows as failed in Railway.

Variables: DATABASE_URL, BACKUP_BUCKET, AWS_ENDPOINT_URL, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION
(the Railway bucket's credentials), BACKUP_S3_ADDRESSING=virtual|path (Railway buckets: virtual).
Credentials reach pg_dump through the environment (PGPASSWORD), never the command line.

    python -m backend.scripts.backup dump [--no-check] [--no-prune]
    python -m backend.scripts.backup list
    python -m backend.scripts.backup verify [--key backups/db/kb-....dump]   # restore check by hand
    python -m backend.scripts.backup counts                                   # this database's exact counts
    python -m backend.scripts.backup fetch [--key ...] FILE                   # download a dump to restore it
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

PREFIX = "backups/db"
NAME = re.compile(r"^kb-(\d{8}T\d{6}Z)\.dump$")
RESTORE_CHECK_EVERY = dt.timedelta(days=28)
KEEP_NEWEST, KEEP_WEEKS, KEEP_MONTHS = 14, 8, 12
CHUNK = 8 * 1024 * 1024


def database_url(environ=None) -> str:
    """DATABASE_URL as libpq wants it (Railway gives postgresql://; the app's own form adds +psycopg)."""
    url = (os.environ if environ is None else environ).get("DATABASE_URL", "")
    if not url:
        raise SystemExit("set DATABASE_URL")
    return re.sub(r"^postgres(ql)?(\+psycopg)?://", "postgresql://", url)


def client_env(url: str, environ=None) -> tuple[dict, str]:
    """The environment for pg_dump/pg_restore and the database name, from a postgresql:// URL."""
    parsed = urlparse(url)
    if not parsed.path.strip("/"):
        raise ValueError("DATABASE_URL must name a database")
    env = dict(os.environ if environ is None else environ)
    env.update({"PGHOST": parsed.hostname or "localhost", "PGPORT": str(parsed.port or 5432),
                "PGUSER": unquote(parsed.username or ""), "PGPASSWORD": unquote(parsed.password or "")})
    if sslmode := parse_qs(parsed.query).get("sslmode"):
        env["PGSSLMODE"] = sslmode[0]
    return env, unquote(parsed.path.strip("/"))


def _with_db(url: str, name: str) -> str:
    return urlparse(url)._replace(path=f"/{name}").geturl()


def stamp(now: dt.datetime) -> str:
    return now.astimezone(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def when(name: str) -> dt.datetime | None:
    match = NAME.match(name)
    return dt.datetime.strptime(match.group(1), "%Y%m%dT%H%M%SZ").replace(tzinfo=dt.timezone.utc) if match else None


def retained(names: list[str]) -> set[str]:
    """The dumps to keep. A name that is not one of our dumps is always kept: never ours to delete."""
    dated = sorted(((when(n), n) for n in names if when(n)), reverse=True)
    keep = {n for n in names if not when(n)}
    keep.update(n for _, n in dated[:KEEP_NEWEST])
    weeks, months = {}, {}
    for at, name in dated:
        weeks.setdefault(at.isocalendar()[:2], name)
        months.setdefault((at.year, at.month), name)
    keep.update(list(weeks.values())[:KEEP_WEEKS])
    keep.update(list(months.values())[:KEEP_MONTHS])
    return keep


def counts_in(conn) -> dict[str, int]:
    """Exact row counts of every table in the public schema, as `conn`'s transaction sees them."""
    from psycopg import sql
    tables = [r[0] for r in conn.execute(
        "select tablename from pg_tables where schemaname = 'public' order by tablename").fetchall()]
    return {t: conn.execute(sql.SQL("select count(*) from {}").format(sql.Identifier("public", t))).fetchone()[0]
            for t in tables}


def migration_in(conn) -> str | None:
    if not conn.execute("select to_regclass('public.alembic_version')").fetchone()[0]:
        return None
    row = conn.execute("select version_num from alembic_version").fetchone()
    return row[0] if row else None


def table_counts(url: str) -> dict[str, int]:
    import psycopg
    with psycopg.connect(url) as conn:
        return counts_in(conn)


def _run(args: list[str], env: dict) -> subprocess.CompletedProcess:
    result = subprocess.run(args, env=env, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(f"{args[0]} failed ({result.returncode}): {result.stderr.strip()[-2000:]}")
    return result


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        while block := f.read(CHUNK):
            digest.update(block)
    return digest.hexdigest()


class Bucket:
    """The backup bucket. Tests pass a folder-backed stand-in with the same five methods."""

    def __init__(self, environ=None):
        import boto3
        from botocore.config import Config
        env = os.environ if environ is None else environ
        self.name = env.get("BACKUP_BUCKET", "").strip()
        if not self.name:
            raise SystemExit("set BACKUP_BUCKET (and the AWS_* credentials of the Railway bucket)")
        addressing = env.get("BACKUP_S3_ADDRESSING", "virtual")
        if addressing not in ("virtual", "path"):
            raise SystemExit("BACKUP_S3_ADDRESSING must be virtual or path")
        # boto3 reads AWS_ENDPOINT_URL, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY and AWS_DEFAULT_REGION itself.
        self.client = boto3.client("s3", region_name=env.get("AWS_DEFAULT_REGION") or "auto", config=Config(
            s3={"addressing_style": addressing}, retries={"max_attempts": 5, "mode": "standard"},
            connect_timeout=10, read_timeout=120))

    def upload(self, path: Path, key: str) -> None:
        self.client.upload_file(str(path), self.name, key)  # multipart above 8 MB; the object appears whole or not at all

    def digest(self, key: str) -> tuple[str, int]:
        """SHA-256 and size of the stored object, streamed (never held in memory)."""
        body, digest, size = self.client.get_object(Bucket=self.name, Key=key)["Body"], hashlib.sha256(), 0
        for block in body.iter_chunks(CHUNK):
            digest.update(block)
            size += len(block)
        return digest.hexdigest(), size

    def download(self, key: str, path: Path) -> None:
        self.client.download_file(self.name, key, str(path))

    def put_json(self, key: str, value: dict) -> None:
        self.client.put_object(Bucket=self.name, Key=key, Body=json.dumps(value, indent=2, default=str).encode(),
                               ContentType="application/json")

    def get_json(self, key: str) -> dict:
        return json.loads(self.client.get_object(Bucket=self.name, Key=key)["Body"].read())

    def names(self, prefix: str) -> list[str]:
        out = []
        for page in self.client.get_paginator("list_objects_v2").paginate(Bucket=self.name, Prefix=prefix + "/"):
            out += [o["Key"].rsplit("/", 1)[-1] for o in page.get("Contents", [])]
        return out

    def delete(self, key: str) -> None:
        self.client.delete_object(Bucket=self.name, Key=key)


def manifest_key(dump_key: str) -> str:
    return dump_key[:-len(".dump")] + ".json"


def complete(bucket) -> list[str]:
    """Finished dumps (those with a manifest), oldest first."""
    names = set(bucket.names(PREFIX))
    return sorted(n for n in names if NAME.match(n) and n[:-len(".dump")] + ".json" in names)


def latest(bucket) -> str:
    done = complete(bucket)
    if not done:
        raise FileNotFoundError(f"no finished dump under {PREFIX}/")
    return f"{PREFIX}/{done[-1]}"


def restore_check_due(bucket, now: dt.datetime) -> bool:
    """True unless a restore check passed within RESTORE_CHECK_EVERY (a failed one is retried the next night)."""
    for name in reversed(complete(bucket)):
        if now - when(name) > RESTORE_CHECK_EVERY:
            return True
        if bucket.get_json(f"{PREFIX}/{name[:-len('.dump')]}.json").get("restore_check", {}).get("matches"):
            return False
    return True


def compare(expected: dict[str, int], actual: dict[str, int]) -> list[str]:
    """Every table whose count differs, or that exists on one side only."""
    return [f"{t}: expected {expected.get(t)}, restored {actual.get(t)}"
            for t in sorted(set(expected) | set(actual)) if expected.get(t) != actual.get(t)]


def verify(url: str, dump_path: Path, expected: dict[str, int], *, now: dt.datetime | None = None) -> dict:
    """Restore `dump_path` into a scratch database next to `url`'s, compare every table's count, always drop it.
    Needs free space on the database volume for a second copy while it runs."""
    import psycopg
    from psycopg import sql
    env, _ = client_env(url)
    scratch = f"kb_restore_check_{stamp(now or dt.datetime.now(dt.timezone.utc)).lower()}"
    admin = _with_db(url, "postgres")
    with psycopg.connect(admin, autocommit=True) as conn:
        conn.execute(sql.SQL("create database {}").format(sql.Identifier(scratch)))
    try:
        _run(["pg_restore", "--no-owner", "--no-acl", "--exit-on-error", f"--dbname={scratch}", str(dump_path)], env)
        actual = table_counts(_with_db(url, scratch))
    finally:
        with psycopg.connect(admin, autocommit=True) as conn:
            conn.execute(sql.SQL("drop database if exists {} with (force)").format(sql.Identifier(scratch)))
    differences = compare(expected, actual)
    return {"scratch_database": scratch, "dropped": True, "tables": len(actual), "rows": sum(actual.values()),
            "matches": not differences, "differences": differences}


def prune(bucket) -> list[str]:
    names = [n for n in bucket.names(PREFIX) if n.endswith(".dump")]
    gone = sorted(set(names) - retained(names))
    for name in gone:
        bucket.delete(f"{PREFIX}/{name}")
        bucket.delete(f"{PREFIX}/{name[:-len('.dump')]}.json")
    return gone


def dump(url: str, bucket, *, now: dt.datetime | None = None, check: bool = True, keep_all: bool = False) -> dict:
    """One nightly run. Raises before pruning when anything is wrong; returns the manifest."""
    import psycopg
    now = now or dt.datetime.now(dt.timezone.utc)
    env, name = client_env(url)
    key = f"{PREFIX}/kb-{stamp(now)}.dump"
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "kb.dump"
        with psycopg.connect(url) as conn:
            # The snapshot stays valid while this transaction is open: pg_dump and the counts read the same rows.
            # Set on the connection, not with a BEGIN statement: psycopg has already opened a transaction by then.
            conn.isolation_level, conn.read_only = psycopg.IsolationLevel.REPEATABLE_READ, True
            snapshot = conn.execute("select pg_export_snapshot()").fetchone()[0]
            _run(["pg_dump", "--format=custom", "--no-owner", "--no-acl", f"--snapshot={snapshot}",
                  f"--file={path}", name], env)
            counts, migration = counts_in(conn), migration_in(conn)
            conn.rollback()
        toc = _run(["pg_restore", "--list", str(path)], env).stdout
        sha, size = sha256_of(path), path.stat().st_size
        bucket.upload(path, key)
        if bucket.digest(key) != (sha, size):
            raise RuntimeError(f"{key}: the stored dump does not read back byte for byte; nothing was pruned")
        manifest = {"key": key, "created_at": now.isoformat(), "database": name, "bytes": size, "sha256": sha,
                    "toc_entries": sum(1 for line in toc.splitlines() if line and not line.startswith(";")),
                    "migration": migration, "counts": counts, "snapshot": snapshot,
                    "pg_dump": _run(["pg_dump", "--version"], env).stdout.strip()}
        if check and restore_check_due(bucket, now):
            try:
                manifest["restore_check"] = verify(url, path, counts, now=now)
            except Exception as error:  # recorded, then re-raised below: a dump that cannot be restored is a failed night
                manifest["restore_check"] = {"matches": False, "error": str(error)[:1000]}
    bucket.put_json(manifest_key(key), manifest)
    if not manifest.get("restore_check", {}).get("matches", True):
        raise RuntimeError(f"{key}: restore check failed, nothing was pruned: {manifest['restore_check']}")
    manifest["pruned"] = [] if keep_all else prune(bucket)
    return manifest


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="python -m backend.scripts.backup", description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    d = sub.add_parser("dump", help="dump DATABASE_URL to the bucket, verify it, restore-check monthly, prune")
    d.add_argument("--no-check", action="store_true", help="skip the restore check even when it is due")
    d.add_argument("--no-prune", action="store_true")
    sub.add_parser("list", help="finished dumps, newest last")
    v = sub.add_parser("verify", help="restore a dump into a scratch database, compare counts, drop it")
    v.add_argument("--key", help="a dump in the bucket (default: the newest finished one)")
    sub.add_parser("counts", help="this database's exact row counts per table")
    f = sub.add_parser("fetch", help="download a dump (default: the newest finished one) to restore it")
    f.add_argument("file")
    f.add_argument("--key")
    args = parser.parse_args(argv)

    if args.command == "counts":
        print(json.dumps(table_counts(database_url()), indent=2))
        return 0
    bucket = Bucket()
    if args.command == "list":
        for name in complete(bucket):
            m = bucket.get_json(f"{PREFIX}/{name[:-len('.dump')]}.json")
            check = m.get("restore_check", {}).get("matches")
            print(f"{name}  {m['bytes'] / 1e6:9.1f} MB  {sum(m['counts'].values()):>10} rows  migration {m['migration']}"
                  + ("" if check is None else f"  restore check {'passed' if check else 'FAILED'}"))
        return 0
    if args.command == "fetch":
        key = args.key or latest(bucket)
        bucket.download(key, Path(args.file))
        expected = bucket.get_json(manifest_key(key))["sha256"]
        if sha256_of(Path(args.file)) != expected:
            raise SystemExit(f"{args.file}: SHA-256 does not match the manifest of {key}")
        print(f"{key} -> {args.file} (SHA-256 matches its manifest)")
        return 0
    url = database_url()
    if args.command == "dump":
        manifest = dump(url, bucket, check=not args.no_check, keep_all=args.no_prune)
        print(json.dumps({k: v for k, v in manifest.items() if k != "counts"}
                         | {"tables": len(manifest["counts"]), "rows": sum(manifest["counts"].values())},
                         indent=2, default=str))
        return 0
    key = args.key or latest(bucket)
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "kb.dump"
        bucket.download(key, path)
        manifest = bucket.get_json(manifest_key(key))
        if sha256_of(path) != manifest["sha256"]:
            raise SystemExit(f"{key}: SHA-256 does not match its manifest")
        result = verify(url, path, manifest["counts"])
    print(json.dumps(result, indent=2))
    return 0 if result["matches"] else 1


if __name__ == "__main__":
    sys.exit(main())
