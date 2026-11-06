"""Regenerate backend/sql/schema.sql: the final production schema in one file.

Builds an empty scratch database from every Alembic migration, dumps its schema with the local compose
Postgres (pg_dump inside the `db` container), and wraps it so that applying it also records the current
Alembic revision. Run from the repository root with the compose database up:

    python -m backend.scripts.schema_export
"""
import os
import re
import subprocess
from datetime import date
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "backend/sql/schema.sql"
ADMIN = "postgresql://kb:kb@localhost:5440/kb"
SCRATCH = "kb_schema_export"

HEADER = """-- WIA Client Knowledge Base: production schema, final state at migration {rev}.
--
-- Generated {day} by building an empty PostgreSQL 16 database from every Alembic migration
-- (backend/sql/migrations/versions) and dumping its schema. Same result as running the migrations, in one step.
--
-- Use ONLY on an empty production database:
--   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f backend/sql/schema.sql
-- It also records the Alembic revision, so later schema changes are applied as normal migrations
-- (alembic upgrade head) once production holds data. Never re-run this file on a database with data.
--
-- Regenerate after any new migration:  python -m backend.scripts.schema_export

BEGIN;
"""
FOOTER = """
-- Mark the database as being at the latest migration, so future migrations start from here.
INSERT INTO public.alembic_version (version_num) VALUES ('{rev}');

COMMIT;
"""


def main() -> None:
    with psycopg.connect(ADMIN, autocommit=True) as conn:
        conn.execute(f"DROP DATABASE IF EXISTS {SCRATCH} WITH (FORCE)")
        conn.execute(f"CREATE DATABASE {SCRATCH}")
    env = {**os.environ, "DATABASE_URL": f"postgresql+psycopg://kb:kb@localhost:5440/{SCRATCH}"}
    subprocess.run(["python", "-m", "alembic", "-c", "backend/alembic.ini", "upgrade", "head"],
                   cwd=ROOT, env=env, check=True)
    with psycopg.connect(f"postgresql://kb:kb@localhost:5440/{SCRATCH}") as conn:
        rev = conn.execute("SELECT version_num FROM alembic_version").fetchone()[0]
    dump = subprocess.run(["docker", "compose", "-f", "backend/docker-compose.yml", "exec", "-T", "db", "pg_dump",
                           "-U", "kb", "-d", SCRATCH, "--schema-only", "--no-owner", "--no-privileges", "--no-comments"],
                          cwd=ROOT, check=True, capture_output=True, text=True, encoding="utf-8").stdout
    body = "\n".join(line for line in dump.splitlines() if not line.startswith("\\"))  # psql-only meta lines
    body = re.sub(r"\n{3,}", "\n\n", body).strip()
    OUT.write_text(HEADER.format(rev=rev, day=date.today().isoformat()) + body + "\n" + FOOTER.format(rev=rev),
                   encoding="utf-8", newline="\n")
    with psycopg.connect(ADMIN, autocommit=True) as conn:
        conn.execute(f"DROP DATABASE {SCRATCH} WITH (FORCE)")
    print(f"wrote {OUT.relative_to(ROOT)} at revision {rev}")


if __name__ == "__main__":
    main()
