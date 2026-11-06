"""A failed job's reason, in words a reviewer reads first (R50), with the technical detail for the team after it.

The worker stores a job's error as its `error_summary`, which the app shows on the cycle, on a developed card's brief panel
and on Gate 2. A provider that refuses a paid call (an account out of credit, a key it does not accept, too many requests,
its own failure) or a request no privacy-compliant route can take is said in plain words on the first line; the exception
follows on the next, unchanged, so nothing the team needs is lost. Any other error is stored as it was. A standing budget's
refusal never reaches here: the job waits with its own reason (llm/standing.py). A card refresh words its own reasons
(cycle/refresh.py).
"""
from __future__ import annotations

import httpx

from .providers import IncompleteResponse
from .routing import RoutingError
from .transport import ANSWER_LOST, UpstreamError

OUT_OF_CREDIT = ("The model provider refused the request because the account is out of credit, so nothing was written. "
                 "Retry this step once the team has topped the account up.")
TIMED_OUT = ("The model took longer to answer than the time allowed, so nothing was written. Retry this step; if it happens "
             "again, the team raises the time allowed (models.request_timeout_seconds).")
ANSWER_CUT = ("The model provider's answer was cut off on its way back, so nothing was written. The call may have been "
              "charged, so the budget counts it at its most. Retry this step later.")
KEY_LIMIT = ("The model provider refused the request because the server's key has used up its spending limit, so nothing was "
             "written. Retry this step once the limit resets or the team raises it.")


def _key_limit(response: httpx.Response) -> bool:
    """OpenRouter refuses a key past its own spending limit with 403 (not 402): `Key limit exceeded`, limit_source
    `openrouter_key_limit` (seen on the internal key on 23 October)."""
    try:
        error = response.json().get("error") or {}
    except ValueError:
        return "key limit exceeded" in response.text.lower()
    metadata = error.get("metadata") if isinstance(error.get("metadata"), dict) else {}
    return metadata.get("limit_source") == "openrouter_key_limit" or "key limit exceeded" in str(error.get("message", "")).lower()


def plain(error: BaseException | None) -> str | None:
    """The reviewer's reason for a provider's refusal behind this error (a caller may have wrapped it), or None."""
    seen = set()
    while error is not None and id(error) not in seen:
        seen.add(id(error))
        if isinstance(error, httpx.HTTPStatusError):
            code = error.response.status_code
            if code == 402:
                return OUT_OF_CREDIT
            if code == 403 and _key_limit(error.response):
                return KEY_LIMIT
            if code in (401, 403):
                return "The model provider did not accept the server's key, so nothing was written. The team checks the key; then retry this step."
            if code == 429:
                return "The model provider is limiting requests just now, so nothing was written. Retry this step in a few minutes."
            if code >= 500:
                return f"The model provider failed to answer (error {code}), so nothing was written. Retry this step later."
            return f"The model provider refused the request (error {code}), so nothing was written. Retry this step later."
        if isinstance(error, UpstreamError):
            # HTTP 200 with the provider's failure in the body (an upstream 502, for example): the same reason as a 5xx.
            return "The model provider failed to answer, so nothing was written. Retry this step later."
        if isinstance(error, IncompleteResponse):
            return ("The model's answer was cut off before it finished, so nothing was written. Retry this step; if it is cut "
                    "off again, the team raises the output limit (models.completion_tokens).")
        if isinstance(error, RoutingError):
            return "No model route met the privacy rules for this request, so nothing was sent."
        if isinstance(error, httpx.TimeoutException):
            return TIMED_OUT
        if isinstance(error, ANSWER_LOST):
            return ANSWER_CUT
        if isinstance(error, httpx.TransportError):
            return "The model provider could not be reached, so nothing was written. Retry this step later."
        error = error.__cause__ or error.__context__
    return None


def message(error: BaseException) -> str:
    """What a failed job stores: the plain reason first when there is one, then the error as it was raised."""
    reason = plain(error)
    return f"{reason}\n{type(error).__name__}: {error}" if reason else str(error)
