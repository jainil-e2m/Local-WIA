"""Database engine and session factory. Services own transactions; routes never do."""
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from backend.config import get_settings

_settings = get_settings()

engine = create_engine(
    _settings.database_url,
    pool_size=5,
    max_overflow=0,
    pool_timeout=5,
    pool_pre_ping=True,
    connect_args={"options": "-c statement_timeout=30000 -c lock_timeout=2000"},
)

SessionFactory = sessionmaker(bind=engine, expire_on_commit=False)


def wait_for_locks(session, seconds: int = 15) -> None:
    """For a person's edit while a copy runs: every intake page briefly share-locks the roster
    (people/resolve.py), so the default 2 s lock wait would fail admin edits during a backfill."""
    session.execute(text(f"SET LOCAL lock_timeout = '{int(seconds)}s'"))


@contextmanager
def transaction() -> Iterator[Session]:
    """One unit of work: commits on success, rolls back on error."""
    with SessionFactory.begin() as session:
        yield session
