"""Verification may use mock transports and local SQL; outbound HTTP is forbidden."""
import os

import httpx
import pytest

from backend_pipeline import config, settings_store

_REAL_ROOTS = (config.BACKEND_ROOT, config.PROJECT_ROOT)
_REAL_ENV_FILES = settings_store.env_files


@pytest.fixture(autouse=True)
def no_outbound_requests(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('Verification forbids outbound HTTP, OpenRouter and embedding requests')
    monkeypatch.setattr(httpx.HTTPTransport,'handle_request',forbidden)
    monkeypatch.setattr(httpx.AsyncHTTPTransport,'handle_async_request',forbidden)


@pytest.fixture(autouse=True)
def developer_settings_are_not_read(monkeypatch):
    """0.B8: the one environment reader never reads the developer's real backend/.env, root .env, .env.storage.local or
    .env.intake.local, and no settings table is consulted unless a test names a database. A test that points
    config.BACKEND_ROOT at a temporary folder still reads the files it wrote there."""
    def guarded():
        return [] if (config.BACKEND_ROOT, config.PROJECT_ROOT) == _REAL_ROOTS else _REAL_ENV_FILES()
    monkeypatch.setattr(settings_store, 'env_files', guarded)
    monkeypatch.delenv('ATELIER_DATABASE_URL', raising=False)
    settings_store.invalidate()
    # The loader copies file values into os.environ (setdefault); a test that wrote its own .env must not leak them.
    before = dict(os.environ)
    yield
    os.environ.clear()
    os.environ.update(before)
    settings_store.invalidate()
