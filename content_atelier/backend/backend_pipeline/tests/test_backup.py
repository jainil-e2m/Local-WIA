"""6.B6 (N3): the nightly database dump kept off the database's volume, its retention and its restore check."""
from __future__ import annotations

import datetime as dt
import json

import pytest

from backend_pipeline import backup
from backend_pipeline.artifacts import LocalBackend
from backend_pipeline.store import JsonStore

UTC = dt.timezone.utc


def name(when: dt.datetime) -> str:
    return f"atelier-{backup.stamp(when)}.dump"


def test_client_env_passes_credentials_through_the_environment_not_the_command_line():
    env, database = backup.client_env("postgresql://atelier:p%40ss@db.internal:6543/atelier", environ={})
    assert database == "atelier"
    assert env == {"PGHOST": "db.internal", "PGPORT": "6543", "PGUSER": "atelier", "PGPASSWORD": "p@ss"}
    with pytest.raises(ValueError):
        backup.client_env("mysql://x@y/z", environ={})
    with pytest.raises(ValueError):
        backup.client_env("postgresql://x@y/", environ={})


def test_stamp_round_trips_and_only_our_names_parse():
    when = dt.datetime(2026, 10, 24, 8, 0, 5, tzinfo=UTC)
    assert backup.parse_stamp(name(when)) == when
    assert backup.parse_stamp("atelier-latest.dump") is None
    assert backup.parse_stamp("notes.txt") is None


def test_retention_keeps_newest_fourteen_one_per_week_and_one_per_month():
    start = dt.datetime(2025, 1, 1, 8, tzinfo=UTC)
    names = [name(start + dt.timedelta(days=d)) for d in range(500)]
    kept = backup.retained(names + ["hand-made.dump"])
    assert "hand-made.dump" in kept  # never ours to delete
    newest = sorted(names)[-14:]
    assert set(newest) <= kept
    dated = sorted(n for n in kept if backup.parse_stamp(n))
    months = {(backup.parse_stamp(n).year, backup.parse_stamp(n).month) for n in dated}
    assert len(months) == 12
    # At most newest 14 + 8 weekly + 12 monthly, and nothing older than twelve months survives.
    assert len(dated) <= 14 + 8 + 12
    assert min(backup.parse_stamp(n) for n in dated) > backup.parse_stamp(sorted(names)[-1]) - dt.timedelta(days=366)


def test_retention_keeps_everything_while_there_are_few_dumps():
    start = dt.datetime(2026, 10, 24, 8, tzinfo=UTC)
    names = [name(start + dt.timedelta(days=d)) for d in range(10)]
    assert backup.retained(names) == set(names)


def test_compare_names_every_table_that_differs_or_is_missing():
    assert backup.compare({"a": 1, "b": 2}, {"a": 1, "b": 2}) == []
    assert backup.compare({"a": 1, "b": 2}, {"a": 1, "b": 3, "c": 0}) == [
        "b: expected 2, restored 3", "c: expected None, restored 0"]


def test_prune_removes_only_dumps_outside_retention_and_their_manifests(tmp_path):
    store = JsonStore(LocalBackend(tmp_path))
    start = dt.datetime(2025, 1, 1, 8, tzinfo=UTC)
    names = [name(start + dt.timedelta(days=d)) for d in range(60)]
    for n in names:
        store.backend.write(f"{backup.PREFIX}/{n}", b"dump")
        store.backend.write(f"{backup.PREFIX}/{n[:-5]}.json", b"{}")
    store.backend.write(f"{backup.PREFIX}/README.txt", b"keep")
    gone = backup.prune_old(store)
    left = set(store.backend.names(backup.PREFIX))
    assert gone and not any(g in left or g[:-5] + ".json" in left for g in gone)
    assert "README.txt" in left
    assert {n for n in left if n.endswith(".dump")} == backup.retained(names)
    assert backup.latest(store) == f"{backup.PREFIX}/{sorted(names)[-1]}"


def test_dump_writes_the_dump_and_a_manifest_and_reads_it_back(tmp_path, monkeypatch):
    store = JsonStore(LocalBackend(tmp_path))
    calls = []

    def fake_run(args, env):
        calls.append((args, env))
        if args[0] == "pg_dump" and "--version" not in args:
            target = next(a for a in args if a.startswith("--file=")).split("=", 1)[1]
            open(target, "wb").write(b"PGDMP fake")
        out = {"pg_restore": "; header\n1; 1259 TABLE public a\n2; 1259 TABLE public b\n", "pg_dump": "pg_dump (PostgreSQL) 17.6"}
        return type("R", (), {"stdout": out.get(args[0], "")})()

    class FakeSnapshot:
        id = "00000003-0000001B-1"

        def __init__(self, url):
            assert url == "postgresql://u:secret@h:5432/atelier"

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            pass

        def counts(self):
            # Counted in the dump's own snapshot, after pg_dump has written the file.
            assert any(a[0] == "pg_dump" and "--version" not in a for a, _ in calls)
            return {"a": 3, "b": 0}

        def migration(self):
            return "008"

    monkeypatch.setattr(backup, "_run", fake_run)
    monkeypatch.setattr(backup, "snapshot", FakeSnapshot)
    when = dt.datetime(2026, 10, 24, 8, tzinfo=UTC)
    manifest = backup.dump("postgresql://u:secret@h:5432/atelier", store, now=when)
    key = f"{backup.PREFIX}/atelier-20261024T080000Z.dump"
    assert manifest["key"] == key and store.read_bytes(key) == b"PGDMP fake"
    stored = json.loads(store.read_bytes(key[:-5] + ".json"))
    assert stored["counts"] == {"a": 3, "b": 0} and stored["migration"] == "008" and stored["toc_entries"] == 2
    assert stored["database"] == "atelier" and stored["bytes"] == len(b"PGDMP fake")
    # pg_dump reads the same snapshot the counts were taken in, so the manifest describes exactly the dumped rows.
    dump_args = next(a for a, _ in calls if a[0] == "pg_dump" and "--version" not in a)
    assert "--snapshot=00000003-0000001B-1" in dump_args and stored["snapshot"] == "00000003-0000001B-1"
    # The password reaches the tools only through the environment.
    assert all("secret" not in " ".join(args) and env["PGPASSWORD"] == "secret" for args, env in calls)
    assert manifest["pruned"] == []


def test_verify_refuses_a_scratch_name_that_could_be_a_real_database():
    with pytest.raises(ValueError):
        backup.verify("postgresql://u:p@h:5432/atelier", None, {}, scratch="atelier")
