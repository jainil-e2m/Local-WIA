"""BF-1: Google rate limits arrive as HTTP 403. Only the error reason separates them from real denials."""
import httpx
import pytest

from backend.models.domain.intake import ChangeBatch
from backend.services.intake.adapters.readers import fetch_or_gap
from backend.services.shared import http
from backend.services.shared.errors import ScopeDeniedError, ThrottledError


def _google_403(reason: str, style: str = "errors") -> httpx.Response:
    item = {"reason": reason, "domain": "usageLimits"}
    error = {"code": 403, "message": "denied", "status": "PERMISSION_DENIED",
             **({"errors": [item]} if style == "errors" else {"details": [item]})}
    return httpx.Response(403, json={"error": error})


def _client(responses: list[httpx.Response]) -> http.ProviderClient:
    """A Gmail-style client that answers each request with the next queued response."""
    client = http.ProviderClient("gmail", "https://example.test/")
    queue = list(responses)
    client._client = httpx.Client(base_url="https://example.test/",
                                  transport=httpx.MockTransport(lambda request: queue.pop(0)))
    return client


@pytest.fixture
def sleeps(monkeypatch):
    waited: list[float] = []
    monkeypatch.setattr(http.time, "sleep", waited.append)
    return waited


@pytest.mark.parametrize("reason", ["rateLimitExceeded", "userRateLimitExceeded", "quotaExceeded"])
def test_rate_limit_403_backs_off_and_retries(reason, sleeps):
    client = _client([_google_403(reason), httpx.Response(200, json={"ok": True})])
    assert client.get_json("messages") == {"ok": True}
    assert len(sleeps) == 1 and 2 <= sleeps[0] <= 3


def test_error_info_detail_reason_is_a_rate_limit(sleeps):
    client = _client([_google_403("RATE_LIMIT_EXCEEDED", style="details"), httpx.Response(200, json={})])
    assert client.get_json("files") == {}
    assert len(sleeps) == 1


def test_persistent_rate_limit_becomes_a_retryable_throttle(sleeps):
    client = _client([_google_403("userRateLimitExceeded")] * (http.MAX_INLINE_THROTTLES + 1))
    with pytest.raises(ThrottledError) as exc:
        client.get_json("messages")
    assert exc.value.retryable and exc.value.retry_after == http.RATE_LIMIT_RETRY_SECONDS
    assert len(sleeps) == http.MAX_INLINE_THROTTLES
    assert sleeps == sorted(sleeps)  # exponential, not a fixed wait


def test_daily_limit_throttles_without_waiting_inline(sleeps):
    client = _client([_google_403("dailyLimitExceeded")])
    with pytest.raises(ThrottledError) as exc:
        client.get_json("files")
    assert exc.value.retry_after == http.DAILY_LIMIT_RETRY_SECONDS
    assert sleeps == []


@pytest.mark.parametrize("response", [
    _google_403("insufficientPermissions"),
    _google_403("forbidden"),
    _google_403("accessNotConfigured"),  # same usageLimits domain, but the API is off: not a throttle
    httpx.Response(403, text="<html>Forbidden</html>"),
    httpx.Response(403, json=["not", "an", "object"]),
    httpx.Response(403),
])
def test_other_403s_stay_scope_denied(response, sleeps):
    with pytest.raises(ScopeDeniedError):
        _client([response]).get_json("messages")
    assert sleeps == []


def test_throttled_item_is_retried_not_recorded_as_a_gap(sleeps):
    """Before BF-1 a quota 403 on one message became an 'inaccessible' gap and a partial run."""
    client = _client([_google_403("rateLimitExceeded")] * (http.MAX_INLINE_THROTTLES + 1))
    batch = ChangeBatch([], None, False)
    with pytest.raises(ThrottledError):
        fetch_or_gap(batch, "gmail_message", "m1", None, lambda: client.get_json("messages/m1"))
    assert batch.gaps == []


def test_real_denial_on_an_item_is_still_a_gap(sleeps):
    client = _client([_google_403("insufficientPermissions")] * 2)
    batch = ChangeBatch([], None, False)
    assert fetch_or_gap(batch, "gmail_message", "m1", None, lambda: client.get_json("messages/m1")) is None
    assert [g.reason for g in batch.gaps] == ["scope_denied"]
