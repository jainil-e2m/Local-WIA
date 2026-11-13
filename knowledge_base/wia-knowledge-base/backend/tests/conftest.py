"""Tests run against a separate `kb_test` database in the local compose Postgres."""
import os
from sqlalchemy.engine import make_url

os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL", "postgresql+psycopg://kb:kb@localhost:5440/kb_test")
if make_url(os.environ["DATABASE_URL"]).database != "kb_test":
    raise RuntimeError("Backend tests require a dedicated database named kb_test")

import psycopg  # noqa: E402
import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402

from backend.config import BACKEND_DIR  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def schema():
    admin = os.environ["DATABASE_URL"].replace("postgresql+psycopg", "postgresql").rsplit("/", 1)[0] + "/kb"
    with psycopg.connect(admin, autocommit=True) as conn:
        conn.execute("DROP DATABASE IF EXISTS kb_test WITH (FORCE)")
        conn.execute("CREATE DATABASE kb_test")
    command.upgrade(Config(str(BACKEND_DIR / "alembic.ini")), "head")
    yield


@pytest.fixture(autouse=True)
def clean_tables():
    yield
    from sqlalchemy import text

    from backend.db import engine
    with engine.begin() as conn:
        tables = conn.execute(text(
            "SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename <> 'alembic_version'")).scalars()
        conn.execute(text("TRUNCATE " + ", ".join(tables) + " CASCADE"))
