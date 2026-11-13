"""Nightly backups (scripts/backup.py): consistent, read back, restorable, and nothing pruned after a failure."""
import datetime as dt
import hashlib
import json
import os
import shutil
from pathlib import Path

import pytest

from backend.db import transaction
from backend.models.db.edits import SharedEdit
from backend.scripts import backup

T0 = dt.datetime(2026, 11, 14, 8, 15, tzinfo=dt.timezone.utc)
needs_pg_dump = pytest.mark.skipif(not shutil.which("pg_dump"), reason="pg_dump is not installed here")


class FolderBucket:
    """The five Bucket methods over a folder."""

    def __init__(self, root: Path):
        self.root = root

    def _p(self, key):
        path = self.root / key
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def upload(self, path, key):
        shutil.copyfile(path, self._p(key))

    def digest(self, key):
        data = self._p(key).read_bytes()
        return hashlib.sha256(data).hexdigest(), len(data)

    def download(self, key, path):
        shutil.copyfile(self._p(key), path)

    def put_json(self, key, value):
        self._p(key).write_text(json.dumps(value, default=str))

    def get_json(self, key):
        return json.loads(self._p(key).read_text())

    def names(self, prefix):
        folder = self.root / prefix
        return [p.name for p in folder.iterdir()] if folder.exists() else []

    def delete(self, key):
        self._p(key).unlink(missing_ok=True)


def _edit(key):
    with transaction() as s:
        s.add(SharedEdit(kind="action", key=key, data={"note": key}, updated_by="test"))


def test_database_url_takes_every_form():
    for url in ("postgres://u:p@h:5432/kb", "postgresql://u:p@h:5432/kb", "postgresql+psycopg://u:p@h:5432/kb"):
        assert backup.database_url({"DATABASE_URL": url}) == "postgresql://u:p@h:5432/kb"
    env, name = backup.client_env("postgresql://u:p%40ss@h:6543/kb?sslmode=require", environ={})
    assert (name, env["PGPASSWORD"], env["PGPORT"], env["PGSSLMODE"]) == ("kb", "p@ss", "6543", "require")


def test_retention_keeps_dailies_weeklies_monthlies_and_foreign_files():
    names = [f"kb-{(T0 - dt.timedelta(days=d)):%Y%m%dT%H%M%SZ}.dump" for d in range(400)] + ["notes.txt"]
    keep = backup.retained(names)
    assert "notes.txt" in keep and names[0] in keep and names[13] in keep
    assert names[399] not in keep
    assert 14 <= len(keep) - 1 <= 14 + 8 + 12


def _same_major() -> bool:
    """pg_restore of a newer client cannot restore into an older server (e.g. SET transaction_timeout on 16)."""
    import re
    import subprocess

    import psycopg
    client = int(re.search(r"(\d+)", subprocess.run(["pg_restore", "--version"], capture_output=True, text=True).stdout).group(1))
    with psycopg.connect(backup.database_url()) as conn:
        return client == conn.info.server_version // 10000


@needs_pg_dump
def test_dump_is_consistent_verified_and_restorable(tmp_path, monkeypatch):
    if not _same_major():
        pytest.skip("local pg_restore and server majors differ; the production image pairs 18 with 18")
    url = backup.database_url()
    _edit("a"), _edit("b")
    run = backup._run

    def write_during_dump(args, env):
        result = run(args, env)
        if args[0] == "pg_dump" and "--version" not in args:
            _edit("written-while-dumping")  # after the snapshot: in neither the dump nor its counts
        return result

    monkeypatch.setattr(backup, "_run", write_during_dump)
    bucket = FolderBucket(tmp_path)
    m = backup.dump(url, bucket, now=T0)
    assert m["counts"]["shared_edits"] == 2 and m["migration"]
    assert m["restore_check"]["matches"] and m["restore_check"]["dropped"]
    assert backup.latest(bucket) == m["key"] and bucket.get_json(backup.manifest_key(m["key"]))["sha256"] == m["sha256"]

    # the next night: the restore check passed 1 day ago, so it is not due
    m2 = backup.dump(url, bucket, now=T0 + dt.timedelta(days=1))
    assert "restore_check" not in m2 and m2["counts"]["shared_edits"] == 3


@needs_pg_dump
def test_nothing_is_pruned_or_marked_finished_when_the_upload_is_corrupt(tmp_path, monkeypatch):
    bucket = FolderBucket(tmp_path)
    old = f"{backup.PREFIX}/kb-20250101T081500Z.dump"
    bucket.upload(Path(__file__), old), bucket.put_json(backup.manifest_key(old), {"counts": {}})
    monkeypatch.setattr(bucket, "digest", lambda key: ("0" * 64, 0))
    with pytest.raises(RuntimeError, match="byte for byte"):
        backup.dump(backup.database_url(), bucket, now=T0, check=False)
    assert backup.complete(bucket) == ["kb-20250101T081500Z.dump"]  # old dump kept, new one never finished


@needs_pg_dump
def test_a_failed_restore_check_is_recorded_and_stops_pruning(tmp_path, monkeypatch):
    bucket = FolderBucket(tmp_path)
    old = f"{backup.PREFIX}/kb-20250101T081500Z.dump"
    bucket.upload(Path(__file__), old), bucket.put_json(backup.manifest_key(old), {"counts": {}})
    monkeypatch.setattr(backup, "verify", lambda *a, **k: {"matches": False, "differences": ["x: expected 1, restored 0"]})
    with pytest.raises(RuntimeError, match="restore check failed"):
        backup.dump(backup.database_url(), bucket, now=T0)
    assert len(backup.complete(bucket)) == 2  # the old one survives; the new manifest records the failure
    assert backup.restore_check_due(bucket, T0 + dt.timedelta(days=1))  # retried the next night
