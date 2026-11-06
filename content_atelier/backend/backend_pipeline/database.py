from __future__ import annotations

import json
import hashlib
from contextlib import contextmanager
from pathlib import Path
import psycopg
from psycopg.rows import dict_row
from pgvector.psycopg import register_vector

MIGRATIONS = Path(__file__).resolve().parents[1] / "migrations"
# Seconds the database clock may step back between two transactions. `created_at` defaults to now(), the transaction's
# start on the server's clock, so a row written after another can carry an earlier time when that clock is stepped back
# (a virtual machine resynchronising: measured at up to 0.6 s every 30 s on a WSL2 host, 23 October). A query that asks
# "was this written since that" on two transactions' times widens its window by this much, toward the safe answer
# (jobs/recover.py); the rows whose order a person reads are dated in order instead (repository.insert).
CLOCK_STEP_SECONDS = 5
TABLES = set("weeks pipeline_runs transcripts transcript_chunks key_moments content_angles angle_moments content_briefs content_packs content_assets calendar_entries pipeline_jobs pipeline_events".split())


@contextmanager
def connect(url, *, vectors=True):
    with psycopg.connect(url, row_factory=dict_row, autocommit=True) as conn:
        if vectors:
            register_vector(conn)
        # Type discovery must not start the business transaction. Callers can
        # select isolation before their first content query.
        conn.autocommit = False
        yield conn


def catalog(conn):
    return {
        "columns": conn.execute("""SELECT table_name,column_name,data_type,udt_name,is_nullable,
            column_default FROM information_schema.columns WHERE table_schema='public'
            ORDER BY table_name,ordinal_position""").fetchall(),
        "constraints": conn.execute("""SELECT c.conrelid::regclass::text AS table_name,c.conname,
            c.contype,pg_get_constraintdef(c.oid) AS definition FROM pg_constraint c
            JOIN pg_namespace n ON n.oid=c.connamespace WHERE n.nspname='public' AND c.contype <> 'n'
            ORDER BY table_name,c.conname""").fetchall(),
        "indexes": conn.execute("SELECT tablename,indexname,indexdef FROM pg_indexes WHERE schemaname='public' ORDER BY tablename,indexname").fetchall(),
        "vectors": conn.execute("""SELECT c.relname AS table_name,a.attname,format_type(a.atttypid,a.atttypmod) AS type
            FROM pg_attribute a JOIN pg_class c ON c.oid=a.attrelid JOIN pg_namespace n ON n.oid=c.relnamespace
            WHERE n.nspname='public' AND a.attnum>0 AND NOT a.attisdropped AND a.atttypid='vector'::regtype
            ORDER BY c.relname,a.attname""").fetchall(),
    }


# Migrations in order (plan 0.B3, section 4.8). 001 to 004 predate the runner and are detected by
# their marker objects; from 005 on, schema_migrations records what was applied. 006 is the context store
# (plan label 010, L.B1); 007 is the evidence model (plan label 006, 1.B1): the runner assigns the next free number
# when a migration merges.
# One catalogue per recorded version: schema-catalog-<version>.json, generated from a database migrated to that
# version (`python -m backend_pipeline.schema_catalog --write`), and checked against fresh databases in CI so a migration file and its
# catalogue cannot drift apart. 001 to 004 are never recorded alone (005 records them together), so they have none.
MIGRATION_FILES = {'001': '001_approved_schema.sql', '002': '002_brief_retrieval_index.sql',
                   '003': '003_future_intake.sql', '004': '004_packs_calendar.sql', '005': '005_platform.sql',
                   '006': '006_context_store.sql', '007': '007_evidence_model.sql',
                   '008': '008_moments_ledger.sql', '009': '009_content_packs_v2.sql',
                   '010': '010_identities_account_memory.sql', '011': '011_alerts.sql',
                   '012': '012_slack_schedule_notifications.sql'}
LATEST = max(MIGRATION_FILES)
FIRST_RECORDED = '005'


def recorded_version(conn):
    """The newest version in schema_migrations, or None before migration 005."""
    if not conn.execute("SELECT to_regclass('public.schema_migrations') t").fetchone()['t']:
        return None
    row = conn.execute('SELECT max(version) v FROM schema_migrations').fetchone()
    return row['v']


def expected_catalog(version):
    """The catalogue of a database migrated to this version."""
    return json.loads((MIGRATIONS / f'schema-catalog-{version}.json').read_text())


def check(conn):
    """The database must equal its recorded version's catalogue exactly. Nothing is repaired."""
    version = recorded_version(conn)
    if version is None:
        raise RuntimeError('Database has no recorded schema version; run `storage_cli migrate`')
    if version not in MIGRATION_FILES or version < FIRST_RECORDED:
        raise RuntimeError(f'Unknown recorded schema version {version}; no automatic repair was attempted')
    actual = catalog(conn)
    if actual != expected_catalog(version):
        raise RuntimeError("Database differs from approved baseline; no automatic repair was attempted")
    return {"version": version, "tables": len({c['table_name'] for c in actual['columns']}), "vectors": actual['vectors'],
            'schema_sha256': hashlib.sha256((MIGRATIONS / MIGRATION_FILES[version]).read_bytes().replace(b'\r\n', b'\n')).hexdigest(),
            "foreign_keys": sum(c['contype'] == 'f' for c in actual['constraints']),
            "checks": sum(c['contype'] == 'c' for c in actual['constraints'])}


def _markers(conn):
    """Which of 001 to 004 a database already has, from the objects each one creates."""
    tables = {r['tablename'] for r in conn.execute("SELECT tablename FROM pg_tables WHERE schemaname='public'")}
    indexes = {r['indexname'] for r in conn.execute("SELECT indexname FROM pg_indexes WHERE schemaname='public'")}
    return {'001': TABLES.issubset(tables), '002': 'transcript_chunks_text_search_idx' in indexes,
            '003': 'intake_schema_migrations' in tables, '004': 'mutation_receipts' in tables}, tables


def _checksum(name):
    """A file's checksum with line endings normalised, so a Windows and a Linux checkout record the same value."""
    return hashlib.sha256((MIGRATIONS / name).read_bytes().replace(b'\r\n', b'\n')).hexdigest()


def _accepted_checksums(name):
    # Databases migrated before normalisation recorded the raw bytes of the checkout that applied them (LF or CRLF).
    lf = (MIGRATIONS / name).read_bytes().replace(b'\r\n', b'\n')
    return {hashlib.sha256(lf).hexdigest(), hashlib.sha256(lf.replace(b'\n', b'\r\n')).hexdigest()}


def migrate(url, *, actor='storage_cli migrate', target=None, compare=True):
    """Bring a database to the latest version (or to `target`) in one transaction (0.B3).

    A fresh database gets every file. An existing 001 to 004 database is upgraded in place: the missing earlier
    files are applied in order, then 005, which records every version, then the later files. A database at a
    recorded version gets the files after it, once its catalogue and the checksums of what it applied match.
    The result must equal the target version's catalogue exactly, which also refuses a pre-005 database with
    objects the files do not create; any failure rolls the whole transaction back and nothing is repaired.
    `compare=False` skips that comparison and exists only for `schema_catalog.py`, which generates the catalogues.
    """
    target = target or LATEST
    if target not in MIGRATION_FILES or target < FIRST_RECORDED:
        raise ValueError(f'Cannot migrate to {target}; versions {FIRST_RECORDED} to {LATEST} are recorded')
    with connect(url, vectors=False) as conn:
        conn.execute('SELECT pg_advisory_xact_lock(74091213)')
        version = recorded_version(conn)
        if version == target:
            return {'status': 'already_current', **check(conn)}
        if version and version not in MIGRATION_FILES:
            raise RuntimeError(f'Unknown recorded schema version {version}; no automatic repair was attempted')
        if version and version > target:
            raise RuntimeError(f'The database is at {version}, newer than {target}; the runner never moves backwards')
        applied = []
        if version:
            check(conn)  # The database must equal its recorded version's catalogue.
            for row in conn.execute('SELECT version,name,checksum FROM schema_migrations WHERE source=%s', ('applied',)):
                if row['version'] in MIGRATION_FILES and row['checksum'] not in _accepted_checksums(MIGRATION_FILES[row['version']]):
                    raise RuntimeError(f"Migration {row['version']} changed after it was applied; no automatic repair was attempted")
        else:
            present, tables = _markers(conn)
            if tables and not present['001']:
                raise RuntimeError('Refusing to migrate a nonempty database without the approved baseline')
            for number in ('001', '002', '003', '004'):
                if present[number]:
                    continue
                if number == '004' and not present['003'] and '003' not in applied:
                    raise RuntimeError('Migration order violated')
                conn.execute((MIGRATIONS / MIGRATION_FILES[number]).read_text(encoding='utf-8'))
                applied.append(number)
            conn.execute((MIGRATIONS / MIGRATION_FILES['005']).read_text(encoding='utf-8'))
            applied.append('005')
            for number in ('001', '002', '003', '004', '005'):
                conn.execute('INSERT INTO schema_migrations(version,name,checksum,applied_by,source) VALUES (%s,%s,%s,%s,%s)',
                             (number, MIGRATION_FILES[number], _checksum(MIGRATION_FILES[number]), actor,
                              'applied' if number in applied else 'detected'))
            version = '005'
        for number in sorted(n for n in MIGRATION_FILES if version < n <= target):
            conn.execute((MIGRATIONS / MIGRATION_FILES[number]).read_text(encoding='utf-8'))
            conn.execute('INSERT INTO schema_migrations(version,name,checksum,applied_by,source) VALUES (%s,%s,%s,%s,%s)',
                         (number, MIGRATION_FILES[number], _checksum(MIGRATION_FILES[number]), actor, 'applied'))
            applied.append(number)
        if not compare:
            return {'status': 'migrated', 'applied': applied, 'catalog': catalog(conn)}
        if catalog(conn) != expected_catalog(target):
            raise RuntimeError(f'Migrated catalogue differs from schema-catalog-{target}.json; the migration was rolled back')
        return {'status': 'migrated', 'applied': applied, **check(conn)}
