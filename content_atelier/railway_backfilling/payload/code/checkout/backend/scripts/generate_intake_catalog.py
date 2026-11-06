"""Regenerate approved additive catalogs using ONLY atelier_intake_test.

Run with INTAKE_TEST_DATABASE_URL. Rebuilds that disposable database's public schema.
Never reads or alters the application database.
"""
import json
import os
from backend_pipeline.database import connect, catalog, MIGRATIONS

url = os.environ['INTAKE_TEST_DATABASE_URL']
with connect(url, vectors=False) as conn:
    if conn.info.dbname != 'atelier_intake_test':
        raise RuntimeError('Catalog generation refuses any database except atelier_intake_test')
    conn.execute('DROP SCHEMA public CASCADE')
    conn.execute('CREATE SCHEMA public')
    conn.execute((MIGRATIONS / '001_approved_schema.sql').read_text())
with connect(url) as conn:
    conn.execute((MIGRATIONS / '003_future_intake.sql').read_text())
    (MIGRATIONS / 'schema-catalog-intake.json').write_text(json.dumps(catalog(conn), indent=2) + '\n')
    conn.execute((MIGRATIONS / '002_brief_retrieval_index.sql').read_text())
    (MIGRATIONS / 'schema-catalog-intake-brief.json').write_text(json.dumps(catalog(conn), indent=2) + '\n')
print('Generated intake catalogs from isolated atelier_intake_test')
