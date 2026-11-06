"""Verification may use mock transports and local SQL; outbound HTTP is forbidden."""
import httpx
import pytest


@pytest.fixture(autouse=True)
def no_outbound_requests(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('Verification forbids outbound HTTP, OpenRouter and embedding requests')
    monkeypatch.setattr(httpx.HTTPTransport,'handle_request',forbidden)
    monkeypatch.setattr(httpx.AsyncHTTPTransport,'handle_async_request',forbidden)
