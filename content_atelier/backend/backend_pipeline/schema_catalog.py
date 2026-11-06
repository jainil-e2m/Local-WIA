"""Generate or check the schema catalogues, one per recorded migration version (plan 0.B3).

    python -m backend_pipeline.schema_catalog --check      # CI: fails when a migration file and its catalogue disagree
    python -m backend_pipeline.schema_catalog --write      # after adding or changing a migration

Each version is built from nothing on a throwaway database named atelier_test_catalog, next to the database the
URL names. The URL is ATELIER_TEST_DATABASE_URL (an isolated test database named atelier_test); the application
database is never read or altered.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from urllib.parse import urlsplit, urlunsplit

import psycopg
from psycopg import sql

from .database import FIRST_RECORDED, MIGRATION_FILES, MIGRATIONS, catalog, connect, migrate

SCRATCH = 'atelier_test_catalog'


def scratch_url(admin_url):
    parts = urlsplit(admin_url)
    if parts.path != '/atelier_test':
        raise SystemExit('Catalogue generation refuses any database except atelier_test (it creates atelier_test_catalog beside it)')
    return urlunsplit(parts._replace(path='/' + SCRATCH))


def build(admin_url, version):
    """The catalogue of a database migrated from nothing to `version`."""
    url = scratch_url(admin_url)
    with psycopg.connect(admin_url, autocommit=True) as admin:
        admin.execute(sql.SQL('DROP DATABASE IF EXISTS {} WITH (FORCE)').format(sql.Identifier(SCRATCH)))
        admin.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(SCRATCH)))
    try:
        migrate(url, target=version, actor='schema_catalog', compare=False)
        with connect(url, vectors=False) as conn:
            return catalog(conn)
    finally:
        with psycopg.connect(admin_url, autocommit=True) as admin:
            admin.execute(sql.SQL('DROP DATABASE IF EXISTS {} WITH (FORCE)').format(sql.Identifier(SCRATCH)))


def render(value):
    return json.dumps(value, indent=2) + '\n'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check', action='store_true')
    mode.add_argument('--write', action='store_true')
    args = parser.parse_args(argv)
    admin_url = os.getenv('ATELIER_TEST_DATABASE_URL')
    if not admin_url:
        raise SystemExit('Set ATELIER_TEST_DATABASE_URL to an isolated atelier_test database')
    drift = []
    for version in sorted(v for v in MIGRATION_FILES if v >= FIRST_RECORDED):
        path = MIGRATIONS / f'schema-catalog-{version}.json'
        built = render(build(admin_url, version))
        if args.write:
            path.write_text(built, encoding='utf-8', newline='\n')
            print(f'wrote {path.name}')
        elif not path.is_file() or json.loads(path.read_text(encoding='utf-8')) != json.loads(built):
            drift.append(path.name)
    stale = sorted(p.name for p in MIGRATIONS.glob('schema-catalog-*.json')
                   if p.stem.rsplit('-', 1)[1] not in MIGRATION_FILES or p.stem.rsplit('-', 1)[1] < FIRST_RECORDED)
    if args.check:
        if drift or stale:
            print('Schema drift: ' + ', '.join(drift) + (f'; unused catalogues: {", ".join(stale)}' if stale else ''), file=sys.stderr)
            return 1
        print('Every catalogue matches a database migrated from nothing')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
