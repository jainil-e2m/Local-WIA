"""Database backups kept off the database's volume (plan 6.B6, N3).

Railway's own volume backups need a Pro workspace, so production keeps its own: a `db-backup` cron service runs
`python -m backend_pipeline.backup dump` every night. It writes a custom-format `pg_dump` of `ATELIER_DATABASE_URL` and a
manifest (exact row counts per table, the newest migration, size and SHA-256) to the artifact store under `backups/db/`,
checks that `pg_restore` can read the dump, and prunes old dumps (the newest 14, one per week for 8 weeks, one per month
for 12 months). `verify` restores a dump into a scratch database on the same server, compares every table's count with
the manifest (or a counts file) and always drops the scratch database: the monthly restore check, and the rehearsal before
a restore into production. `counts` prints a database's exact counts, the reference a rehearsal compares against.

The monthly restore check runs by itself (Phase N6): after a nightly dump, when the last check is older than
RESTORE_CHECK_EVERY or failed, `dump` restores the dump it has just written and compares it with its own manifest. Both
results are recorded in `settings` (`backup.last_dump`, `backup.last_restore_check`), where the alert scan (alerts.py)
reads them: a missed night or a failed check becomes an alert in the app.

The image carries the PostgreSQL 17 client (`backend/Dockerfile`); Debian's own client is too old for a PG 17 server.
Credentials go to the client tools through the environment (PGPASSWORD), never on a command line.
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
from urllib.parse import unquote, urlparse

PREFIX = "backups/db"
DUMP_KEY, RESTORE_KEY = "backup.last_dump", "backup.last_restore_check"
RESTORE_CHECK_EVERY = dt.timedelta(days=28)
NAME = re.compile(r"^atelier-(\d{8}T\d{6}Z)\.dump$")
KEEP_NEWEST, KEEP_WEEKS, KEEP_MONTHS = 14, 8, 12


def client_env(database_url: str, environ=None) -> tuple[dict, str]:
    """The environment for pg_dump/pg_restore/psql and the database name, from a postgresql:// URL."""
    url = urlparse(database_url)
    if url.scheme not in {"postgresql", "postgres"} or not url.path.strip("/"):
        raise ValueError("ATELIER_DATABASE_URL must be a postgresql:// URL naming a database")
    env = dict(os.environ if environ is None else environ)
    env.update({"PGHOST": url.hostname or "localhost", "PGPORT": str(url.port or 5432),
                "PGUSER": unquote(url.username or ""), "PGPASSWORD": unquote(url.password or "")})
    return env, unquote(url.path.strip("/"))


def stamp(now: dt.datetime) -> str:
    return now.astimezone(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def parse_stamp(name: str) -> dt.datetime | None:
    match = NAME.match(name)
    return dt.datetime.strptime(match.group(1), "%Y%m%dT%H%M%SZ").replace(tzinfo=dt.timezone.utc) if match else None


def retained(names: list[str]) -> set[str]:
    """Which dumps to keep: the newest KEEP_NEWEST, the newest of each of the last KEEP_WEEKS ISO weeks and the newest of
    each of the last KEEP_MONTHS months. A name that is not a dump of ours is always kept (never ours to delete)."""
    dated = sorted(((parse_stamp(n), n) for n in names if parse_stamp(n)), reverse=True)
    keep = {n for n in names if not parse_stamp(n)}
    keep.update(n for _, n in dated[:KEEP_NEWEST])
    weeks, months = {}, {}
    for when, name in dated:
        weeks.setdefault(when.isocalendar()[:2], name)
        months.setdefault((when.year, when.month), name)
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


def table_counts(database_url: str) -> dict[str, int]:
    import psycopg
    with psycopg.connect(database_url) as conn:
        return counts_in(conn)


def migration_in(conn) -> str | None:
    if not conn.execute("select to_regclass('public.schema_migrations')").fetchone()[0]:
        return None
    row = conn.execute("select max(version) from schema_migrations").fetchone()
    return row[0] if row else None


class Snapshot:
    """One REPEATABLE READ transaction whose snapshot pg_dump shares (`--snapshot`), so the manifest's counts describe
    exactly the rows in the dump even while the platform keeps writing (found by the first production dump, 24 October:
    counts read a moment after the dump differed by the rows written in between)."""

    def __init__(self, database_url: str):
        self.database_url = database_url

    def __enter__(self):
        import psycopg
        self.conn = psycopg.connect(self.database_url)
        self.conn.execute("begin isolation level repeatable read read only")
        self.id = self.conn.execute("select pg_export_snapshot()").fetchone()[0]
        return self

    def counts(self) -> dict[str, int]:
        return counts_in(self.conn)

    def migration(self) -> str | None:
        return migration_in(self.conn)

    def __exit__(self, *exc):
        self.conn.rollback()
        self.conn.close()


def _run(args: list[str], env: dict) -> subprocess.CompletedProcess:
    result = subprocess.run(args, env=env, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(f"{args[0]} failed ({result.returncode}): {result.stderr.strip()[-2000:]}")
    return result


snapshot = Snapshot  # replaced in tests


def _store():
    from .artifacts import store_for
    from .storage_config import StorageSettings
    return store_for(StorageSettings.from_env())


def dump(database_url: str, store, *, now: dt.datetime | None = None, prune: bool = True) -> dict:
    """Write a dump and its manifest to the store, verify the dump is readable, then prune old dumps."""
    now = now or dt.datetime.now(dt.timezone.utc)
    env, name = client_env(database_url)
    key = f"{PREFIX}/atelier-{stamp(now)}.dump"
    with tempfile.TemporaryDirectory() as folder, snapshot(database_url) as snap:
        path = Path(folder) / "atelier.dump"
        _run(["pg_dump", "--format=custom", "--no-owner", "--no-acl", f"--snapshot={snap.id}", f"--file={path}", name], env)
        counts, migration = snap.counts(), snap.migration()
        listing = _run(["pg_restore", "--list", str(path)], env).stdout
        data = path.read_bytes()
    manifest = {
        "key": key, "created_at": now.isoformat(), "database": name, "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(), "toc_entries": sum(1 for line in listing.splitlines() if line and not line.startswith(";")),
        "migration": migration, "counts": counts, "snapshot": snap.id,
        "pg_dump": _run(["pg_dump", "--version"], env).stdout.strip(),
    }
    store.backend.write(key, data)
    store.backend.write(key[:-len(".dump")] + ".json", json.dumps(manifest, indent=2).encode())
    if store.read_bytes(key) != data:
        raise RuntimeError(f"{key}: the stored dump does not read back byte for byte")
    manifest["pruned"] = prune_old(store) if prune else []
    return manifest


def record(database_url: str, key: str, value: dict) -> None:
    """Write one result where the app's alert scan reads it (a settings row; the dump's counts were taken before it)."""
    import psycopg
    with psycopg.connect(database_url) as conn:
        conn.execute("""INSERT INTO settings(key,value,updated_by) VALUES (%s,%s,'db-backup')
            ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value,updated_by=EXCLUDED.updated_by,updated_at=now()""",
                     (key, json.dumps(value, default=str)))
        conn.commit()


def restore_check_due(database_url: str, now: dt.datetime) -> bool:
    """True when no restore check passed within RESTORE_CHECK_EVERY."""
    import psycopg
    with psycopg.connect(database_url) as conn:
        row = conn.execute("SELECT value,updated_at FROM settings WHERE key=%s", (RESTORE_KEY,)).fetchone()
    return row is None or not (row[0] or {}).get("ok") or now - row[1] > RESTORE_CHECK_EVERY


def nightly(database_url: str, store, *, now: dt.datetime | None = None, prune: bool = True, check: bool = True) -> dict:
    """The db-backup service's run: the dump, its record, and the monthly restore check of that same dump when it is due."""
    now = now or dt.datetime.now(dt.timezone.utc)
    manifest = dump(database_url, store, now=now, prune=prune)
    record(database_url, DUMP_KEY, {"key": manifest["key"], "bytes": manifest["bytes"], "migration": manifest["migration"],
                                    "rows": sum(manifest["counts"].values()), "at": manifest["created_at"]})
    if check and restore_check_due(database_url, now):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "atelier.dump"
            path.write_bytes(store.read_bytes(manifest["key"]))
            try:
                result = verify(database_url, path, manifest["counts"])
                problem = "; ".join(result["differences"][:5]) or None
            except Exception as error:  # a restore that cannot run is a failed check, recorded, not a lost night
                result, problem = {"matches": False, "error": str(error)[:500]}, f"the restore could not run: {str(error)[:300]}"
        record(database_url, RESTORE_KEY, {"ok": bool(result.get("matches")), "dump": manifest["key"], "problem": problem,
                                           "tables": result.get("tables"), "rows": result.get("rows"), "at": now.isoformat()})
        manifest["restore_check"] = result
    return manifest


def prune_old(store) -> list[str]:
    names = [n for n in store.backend.names(PREFIX) if n.endswith(".dump")]
    gone = sorted(set(names) - retained(names))
    backend = store.backend
    for name in gone:
        for key in (f"{PREFIX}/{name}", f"{PREFIX}/{name[:-len('.dump')]}.json"):
            if hasattr(backend, "client"):
                backend.client.delete_object(Bucket=backend.bucket, Key=backend._key(key))
            elif backend.local(key):
                backend.local(key).unlink(missing_ok=True)
    return gone


def latest(store) -> str:
    names = sorted(n for n in store.backend.names(PREFIX) if NAME.match(n))
    if not names:
        raise FileNotFoundError(f"no dump under {PREFIX}/ in the store")
    return f"{PREFIX}/{names[-1]}"


def compare(expected: dict[str, int], actual: dict[str, int]) -> list[str]:
    """Every table whose count differs, or that exists on one side only."""
    return [f"{t}: expected {expected.get(t)}, restored {actual.get(t)}"
            for t in sorted(set(expected) | set(actual)) if expected.get(t) != actual.get(t)]


def verify(database_url: str, dump_path: Path, expected: dict[str, int], *, scratch: str | None = None) -> dict:
    """Restore `dump_path` into a scratch database next to `database_url`'s, compare counts, drop it."""
    import psycopg
    from psycopg import sql
    env, _ = client_env(database_url)
    scratch = scratch or f"atelier_restore_check_{stamp(dt.datetime.now(dt.timezone.utc)).lower()}"
    if not re.fullmatch(r"atelier_restore_check_[a-z0-9_]+|atelier_rehearsal[a-z0-9_]*", scratch):
        raise ValueError("the scratch database must be named atelier_restore_check_* or atelier_rehearsal*")
    admin = urlparse(database_url)._replace(path="/postgres").geturl()
    with psycopg.connect(admin, autocommit=True) as conn:
        conn.execute(sql.SQL("create database {}").format(sql.Identifier(scratch)))
    try:
        _run(["pg_restore", "--no-owner", "--no-acl", "--exit-on-error", f"--dbname={scratch}", str(dump_path)], env)
        actual = table_counts(urlparse(database_url)._replace(path=f"/{scratch}").geturl())
    finally:
        with psycopg.connect(admin, autocommit=True) as conn:
            conn.execute(sql.SQL("drop database if exists {} with (force)").format(sql.Identifier(scratch)))
    differences = compare(expected, actual)
    return {"scratch_database": scratch, "dropped": True, "tables": len(actual), "rows": sum(actual.values()),
            "matches": not differences, "differences": differences}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="python -m backend_pipeline.backup", description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    d = sub.add_parser("dump", help="Dump ATELIER_DATABASE_URL into the artifact store, prune old dumps, record the result and "
                                    "run the monthly restore check when it is due")
    d.add_argument("--no-prune", action="store_true")
    d.add_argument("--no-check", action="store_true", help="Skip the monthly restore check even when it is due")
    v = sub.add_parser("verify", help="Restore a dump into a scratch database, compare counts, drop it")
    v.add_argument("--key", help="A dump in the store (default: the newest)")
    v.add_argument("--file", help="A local dump instead of one in the store")
    v.add_argument("--expect", help="A counts JSON file (default: the dump's manifest)")
    v.add_argument("--scratch", help="The scratch database's name (atelier_restore_check_* or atelier_rehearsal*)")
    sub.add_parser("counts", help="Print ATELIER_DATABASE_URL's exact row counts per table as JSON")
    args = parser.parse_args(argv)
    url = os.environ.get("ATELIER_DATABASE_URL", "")
    if not url:
        parser.error("set ATELIER_DATABASE_URL")
    if args.command == "counts":
        print(json.dumps(table_counts(url), indent=2))
        return 0
    if args.command == "dump":
        manifest = nightly(url, _store(), prune=not args.no_prune, check=not args.no_check)
        print(json.dumps({k: v for k, v in manifest.items() if k != "counts"} | {"tables": len(manifest["counts"]),
                         "rows": sum(manifest["counts"].values())}, indent=2, default=str))
        return 0 if manifest.get("restore_check", {}).get("matches", True) else 1
    with tempfile.TemporaryDirectory() as folder:
        if args.file:
            path = Path(args.file)
            expected = json.loads(Path(args.expect).read_text()) if args.expect else None
        else:
            store = _store()
            key = args.key or latest(store)
            path = Path(folder) / "atelier.dump"
            path.write_bytes(store.read_bytes(key))
            manifest = json.loads(store.read_bytes(key[:-len(".dump")] + ".json"))
            expected = json.loads(Path(args.expect).read_text()) if args.expect else manifest["counts"]
        if expected is None:
            parser.error("--file needs --expect (a counts file from `counts` on the source database)")
        result = verify(url, path, expected, scratch=args.scratch)
    print(json.dumps(result, indent=2))
    return 0 if result["matches"] else 1


if __name__ == "__main__":
    sys.exit(main())
