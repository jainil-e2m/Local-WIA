"""Destructive schema checks ONLY in the explicitly named disposable migration database."""

import argparse

import psycopg

from backend_pipeline.database import MIGRATIONS, apply_brief_indexes, apply_calendar, apply_intake, check, connect


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--database-url", required=True)
    args = parser.parse_args()
    with psycopg.connect(args.database_url) as conn:
        if conn.info.dbname != "atelier_calendar_migration_test":
            raise RuntimeError("Migration verification requires exact atelier_calendar_migration_test database")
    for migrations in (
        [],
        ["002_brief_retrieval_index.sql"],
        ["003_future_intake.sql"],
        ["002_brief_retrieval_index.sql", "003_future_intake.sql"],
    ):
        with connect(args.database_url, vectors=False) as conn:
            conn.execute("DROP SCHEMA public CASCADE")
            conn.execute("CREATE SCHEMA public")
            conn.execute((MIGRATIONS / "001_approved_schema.sql").read_text(encoding="utf-8"))
            for migration in migrations:
                conn.execute((MIGRATIONS / migration).read_text(encoding="utf-8"))
            check(conn)
        assert apply_calendar(args.database_url)["status"] == "applied"
        assert apply_calendar(args.database_url)["status"] == "already_applied"
        apply_brief_indexes(args.database_url)
        apply_intake(args.database_url)
        with connect(args.database_url) as conn:
            check(conn)
        print("PASS calendar upgrade and later additive upgrades:", ", ".join(migrations) or "baseline")


if __name__ == "__main__":
    main()
