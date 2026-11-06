"""Provider HTTP client: maps responses to the error taxonomy and honours Retry-After.

The durable job owns retries across attempts; this client only absorbs short
throttles inside one page so a single 429 does not cost a whole job attempt.
URLs, query strings and bodies are never logged.
"""
import random
import threading
import time
from typing import Any

import httpx

from backend.config import get_settings
from backend.services.shared.errors import (
    AuthInvalidError,
    CursorExpiredError,
    IntakeError,
    NotFoundError,
    ScopeDeniedError,
    ThrottledError,
    TransientError,
)

MAX_INLINE_WAIT_SECONDS = 60
MAX_INLINE_THROTTLES = 3

# Google sends rate and quota limits as HTTP 403, told apart from real permission errors only by the
# error reason (BF-1). Anything not listed stays scope_denied.
GOOGLE_RATE_LIMIT_REASONS = {"rateLimitExceeded", "userRateLimitExceeded", "quotaExceeded", "RATE_LIMIT_EXCEEDED"}
GOOGLE_DAILY_LIMIT_REASONS = {"dailyLimitExceeded"}
RATE_LIMIT_RETRY_SECONDS = 60.0
DAILY_LIMIT_RETRY_SECONDS = 3600.0


class ProviderClient:
    def __init__(self, provider: str, base_url: str, headers: dict[str, str] | None = None,
                 min_interval_seconds: float = 0.0):
        self.provider = provider
        self._client = httpx.Client(base_url=base_url, headers=headers or {},
                                    timeout=get_settings().http_timeout_seconds, follow_redirects=False)
        self._min_interval = min_interval_seconds
        self._last_call = 0.0
        self._lock = threading.Lock()
        self.request_count = 0

    def set_header(self, name: str, value: str) -> None:
        self._client.headers[name] = value

    def _pace(self) -> None:
        if not self._min_interval:
            return
        with self._lock:
            wait = self._last_call + self._min_interval - time.monotonic()
            if wait > 0:
                time.sleep(wait)
            self._last_call = time.monotonic()

    def request(self, method: str, path: str, *, params: Any = None, json: Any = None,
                data: Any = None, auth_retry=None) -> httpx.Response:
        throttles = 0
        auth_retried = False
        while True:
            self._pace()
            try:
                response = self._client.request(method, path, params=params, json=json, data=data)
            except httpx.TimeoutException as exc:
                raise TransientError(f"{self.provider}: timeout") from exc
            except httpx.TransportError as exc:
                raise TransientError(f"{self.provider}: transport error {type(exc).__name__}") from exc
            self.request_count += 1
            status = response.status_code
            if status == 401 and auth_retry and not auth_retried:
                auth_retry()  # e.g. refresh an OAuth access token once
                auth_retried = True
                continue
            if status == 429:
                retry_after = _retry_after(response)
                throttles += 1
                if throttles <= MAX_INLINE_THROTTLES and retry_after <= MAX_INLINE_WAIT_SECONDS:
                    time.sleep(retry_after)
                    continue
                raise ThrottledError(f"{self.provider}: throttled", retry_after=retry_after)
            if status >= 500:
                raise TransientError(f"{self.provider}: HTTP {status}")
            if status == 401:
                raise AuthInvalidError(f"{self.provider}: HTTP 401")
            if status == 403:
                reasons = _google_reasons(response)
                if reasons & GOOGLE_DAILY_LIMIT_REASONS:
                    raise ThrottledError(f"{self.provider}: daily quota exhausted",
                                         retry_after=DAILY_LIMIT_RETRY_SECONDS)
                if reasons & GOOGLE_RATE_LIMIT_REASONS:
                    throttles += 1
                    if throttles <= MAX_INLINE_THROTTLES:
                        # No Retry-After on these: exponential backoff with jitter, as Google advises
                        time.sleep(min(2 ** throttles + random.uniform(0, 1), MAX_INLINE_WAIT_SECONDS))
                        continue
                    raise ThrottledError(f"{self.provider}: rate limited (HTTP 403)",
                                         retry_after=RATE_LIMIT_RETRY_SECONDS)
                raise ScopeDeniedError(f"{self.provider}: HTTP 403")
            if status == 404:
                raise NotFoundError(f"{self.provider}: HTTP 404")
            if status == 408:
                raise TransientError(f"{self.provider}: HTTP 408")
            if status == 410:
                raise CursorExpiredError(f"{self.provider}: HTTP 410")
            if status >= 400:
                raise IntakeError(f"{self.provider}: HTTP {status}")  # our request is wrong: a bug
            return response

    def get_json(self, path: str, params: Any = None, **kw) -> Any:
        return self.request("GET", path, params=params, **kw).json()

    def close(self) -> None:
        self._client.close()


def _google_reasons(response: httpx.Response) -> set[str]:
    """Error reasons from a Google error body: `errors[].reason` (v1 APIs) and `details[].reason` (ErrorInfo)."""
    try:
        data = response.json()
    except ValueError:
        return set()
    error = data.get("error") if isinstance(data, dict) else None
    if not isinstance(error, dict):
        return set()
    items = [*(error.get("errors") or []), *(error.get("details") or [])]
    return {i["reason"] for i in items if isinstance(i, dict) and isinstance(i.get("reason"), str)}


def _retry_after(response: httpx.Response) -> float:
    for header in ("Retry-After", "X-RateLimit-Reset-After"):
        value = response.headers.get(header)
        if value:
            try:
                return max(1.0, float(value))
            except ValueError:
                pass
    reset = response.headers.get("X-RateLimit-Reset")  # ClickUp: epoch seconds
    if reset and reset.isdigit():
        return max(1.0, int(reset) - time.time())
    return 30.0
