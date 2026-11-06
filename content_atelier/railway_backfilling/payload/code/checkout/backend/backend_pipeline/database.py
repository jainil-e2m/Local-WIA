from __future__ import annotations

import json
import hashlib
from contextlib import contextmanager
from pathlib import Path
import psycopg
from psycopg.rows import dict_row
from pgvector.psycopg import register_vector

MIGRATIONS = Path(__file__).resolve().parents[1] / "migrations"
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


def check(conn):
    actual = catalog(conn)
    recognized = [json.loads(p.read_text()) for p in MIGRATIONS.glob('schema-catalog*.json')]
    if actual not in recognized:
        raise RuntimeError("Database differs from approved baseline; no automatic repair was attempted")
    return {"tables": len({c['table_name'] for c in actual['columns']}), "vectors": actual['vectors'],
            'schema_sha256':hashlib.sha256((MIGRATIONS/'001_approved_schema.sql').read_bytes()).hexdigest(),
            "foreign_keys": sum(c['contype']=='f' for c in actual['constraints']),
            "checks": sum(c['contype']=='c' for c in actual['constraints'])}


def initialize(url):
    # Explicit administrator operation only. Atomic DDL, serialized baseline application.
    with connect(url, vectors=False) as conn:
        conn.execute("SELECT pg_advisory_xact_lock(74091213)")
        tables = {r['tablename'] for r in conn.execute("SELECT tablename FROM pg_tables WHERE schemaname='public'")}
        if tables:
            if not TABLES.issubset(tables):
                raise RuntimeError("Refusing baseline against a nonempty or partially migrated database")
            return check(conn)
        conn.execute((MIGRATIONS / "001_approved_schema.sql").read_text(encoding='utf-8'))
        return check(conn)


def apply_brief_indexes(url):
    """Atomic explicit upgrade between two exact recognized catalogs."""
    with connect(url) as conn:
        conn.execute('SELECT pg_advisory_xact_lock(74091213)')
        check(conn)
        upgraded=json.loads((MIGRATIONS/'schema-catalog-brief.json').read_text())
        before = catalog(conn)
        if any(i['indexname']=='transcript_chunks_text_search_idx' for i in before['indexes']) or before==upgraded:
            return {'status':'already_applied', **check(conn)}
        conn.execute((MIGRATIONS/'002_brief_retrieval_index.sql').read_text(encoding='utf-8'))
        recognized = [json.loads(p.read_text()) for p in MIGRATIONS.glob('schema-catalog*.json')]
        if catalog(conn) not in recognized:
            raise RuntimeError('Brief index catalog differs; upgrade rolled back')
        return {'status':'applied', **check(conn)}


def apply_intake(url):
    """Explicit upgrade only. No activation, historical registration or model calls."""
    with connect(url) as conn:
        conn.execute('SELECT pg_advisory_xact_lock(74091213)')
        check(conn)
        if conn.execute("SELECT to_regclass('public.intake_schema_migrations') t").fetchone()['t']:
            return {'status': 'already_applied', **check(conn)}
        conn.execute((MIGRATIONS / '003_future_intake.sql').read_text(encoding='utf-8'))
        return {'status': 'applied', **check(conn)}


def apply_calendar(url):
    """Explicit additive production/calendar upgrade; no content creation or provider calls."""
    with connect(url) as conn:
        conn.execute('SELECT pg_advisory_xact_lock(74091213)')
        check(conn)
        if conn.execute("SELECT to_regclass('public.mutation_receipts') t").fetchone()['t']:
            return {'status':'already_applied', **check(conn)}
        conn.execute((MIGRATIONS/'004_packs_calendar.sql').read_text(encoding='utf-8'))
        return {'status':'applied', **check(conn)}
