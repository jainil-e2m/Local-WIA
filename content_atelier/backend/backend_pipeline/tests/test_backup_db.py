"""6.B6 on a real database: the dump's manifest counts the rows of the dump's own snapshot, so a write that lands while the
dump runs is in neither (found by the first production dump on 24 October, whose counts were read a moment later)."""
from __future__ import annotations

import psycopg

from backend_pipeline import backup
from backend_pipeline.tests.platform_db import platform_setup, platform_url  # noqa: F401 (fixtures)


def test_snapshot_counts_ignore_writes_after_the_snapshot(platform_setup, platform_url):  # noqa: F811
    with backup.Snapshot(platform_url) as snap:
        assert snap.id and snap.migration()
        before = snap.counts()
        with psycopg.connect(platform_url, autocommit=True) as other:
            other.execute("INSERT INTO settings (key, value, updated_by) VALUES ('backup.test', '1'::jsonb, 'test')")
        assert snap.counts() == before  # the later write is outside the snapshot pg_dump reads
    assert backup.table_counts(platform_url)["settings"] == before["settings"] + 1


class _Store:
    def __init__(self):
        self.data = {}

    def read_bytes(self, key):
        return self.data[key]


def test_the_nightly_run_records_its_dump_and_runs_the_monthly_restore_check_only_when_due(platform_setup, platform_url,  # noqa: F811
                                                                                             monkeypatch):
    import datetime as dt

    from backend_pipeline import alerts
    from backend_pipeline.database import connect
    store, checks = _Store(), []

    def fake_dump(url, store_, *, now, prune):
        key = f"{backup.PREFIX}/atelier-{backup.stamp(now)}.dump"
        store_.data[key] = b"dump"
        return {"key": key, "bytes": 4, "migration": "011", "counts": {"settings": 1}, "created_at": now.isoformat()}

    def fake_verify(url, path, expected, scratch=None):
        checks.append(path.read_bytes())
        return {"matches": not bad, "differences": [] if not bad else ["settings: expected 1, restored 0"], "tables": 1, "rows": 1}

    monkeypatch.setattr(backup, "dump", fake_dump)
    monkeypatch.setattr(backup, "verify", fake_verify)
    first = dt.datetime(2026, 11, 1, 8, 15, tzinfo=dt.timezone.utc)
    bad = False
    assert backup.nightly(platform_url, store, now=first)["restore_check"]["matches"]  # no check on record: due
    backup.nightly(platform_url, store, now=first + dt.timedelta(days=1))  # passed yesterday: not due
    assert checks == [b"dump"]
    with connect(platform_url, vectors=False) as conn:
        rows = {r["key"]: r["value"] for r in conn.execute("SELECT key,value FROM settings WHERE key LIKE 'backup.%%'")}
    assert rows[alerts.BACKUP_KEY]["migration"] == "011" and rows[alerts.RESTORE_KEY]["ok"] is True
    bad = True
    later = first + dt.timedelta(days=29)
    assert backup.nightly(platform_url, store, now=later)["restore_check"]["matches"] is False  # due again after 28 days
    assert backup.restore_check_due(platform_url, later + dt.timedelta(days=1))  # a failed check is due every night
    with connect(platform_url, vectors=False) as conn:
        value = conn.execute("SELECT value FROM settings WHERE key=%s", (alerts.RESTORE_KEY,)).fetchone()["value"]
    assert value["ok"] is False and "expected 1, restored 0" in value["problem"]
