"""Privacy routing and dispatch (plan S.B1, backend/docs/Privacy-Routing-Addendum.md; part of the llm module, 0.B4).

Every chat and embedding request leaves through send(), which adds these OpenRouter provider
preferences. OpenRouter then routes only to endpoints that neither collect prompts
nor retain them; when no endpoint qualifies it returns an error, and send() raises
instead of retrying without the preferences (fail closed).

The preferences are applied at dispatch and are deliberately not part of request
fingerprints: they constrain where a request runs, not what it asks, so saved
responses keep replaying and E.B12a re-validation still finds its exact request. The same holds for the
prompt-cache marker on the stable system prefix (see mark_prefix).
"""
from __future__ import annotations

import json
import time
from collections.abc import Callable

import httpx

ROUTING_POLICY = "2026-10-18.deny-collection-zdr.v1"
ROUTING_PREFERENCES = {"data_collection": "deny", "zdr": True}

# Free models (plan 5.0c, the free-model shakedown; D41). Every endpoint of a `:free` model may collect prompts, so under
# ROUTING_PREFERENCES OpenRouter excludes them all and the request cannot run. A free model's request therefore leaves through
# this same dispatch without those two preferences, under its own recorded policy, and waits out the free tier's rate limit
# (HTTP 429) and its endpoints' passing failures (502, 503) instead of failing on the first. That is the only difference: any
# other model id takes the preferences, and a paid request is sent exactly as before.
FREE_SUFFIX = ":free"
FREE_POLICY = "2026-10-23.free-models.v1"
FREE_RATE_LIMIT_WAITS = (10, 20, 40, 60, 60, 60)
FREE_RETRY_STATUSES = (429, 502, 503)
# The schemas' "not blank" pattern (contracts.Text). JSON Schema does not anchor a pattern, and OpenAI's route honours that,
# but the grammar engines behind the free endpoints match it whole, so r"\S" let a free model write one character per field
# ("m" for "m1.t0001"), and a pattern rewritten to match whole ([\s\S]*\S[\s\S]*) sent one into a loop of closing quotes and
# braces until its output limit (N1 shakedown). A free request goes without the pattern: minLength stays, and the local
# validator still refuses a blank string and asks for the one repair.
NOT_BLANK = r"\S"
# A free model asked for high reasoning effort spent its whole output limit thinking on a long call, at 16,000 and again at
# the raised 32,000 tokens, and the NVIDIA endpoint did the same at low effort (N1 shakedown); so a free request asks for no
# reasoning, and its whole output goes to the answer. A paid request keeps the stage's setting.
FREE_REASONING = {"enabled": False}


def is_free(model) -> bool:
    return isinstance(model, str) and model.endswith(FREE_SUFFIX)


def policy_for(model) -> str:
    """The routing policy a request to this model is sent under (recorded on its llm_runs row)."""
    return FREE_POLICY if is_free(model) else ROUTING_POLICY


class RoutingError(RuntimeError):
    """No endpoint satisfies the recorded privacy routing, or a request tried to weaken it."""


def route(body: dict) -> dict:
    """A copy of a chat or embedding request body carrying the recorded privacy routing."""
    if not isinstance(body, dict):
        raise TypeError("Request body must be an object")
    preferences = dict(body.get("provider") or {})
    if is_free(body.get("model")):
        routed = {**body, "provider": preferences}
        if "response_format" in body:
            routed["response_format"] = _without_not_blank(body["response_format"])
        if "reasoning" in body:
            routed["reasoning"] = dict(FREE_REASONING)
        return routed
    for key, value in ROUTING_PREFERENCES.items():
        if key in preferences and preferences[key] != value:
            raise RoutingError(f"Request sets provider.{key}={preferences[key]!r}; the recorded routing requires {value!r}")
        preferences[key] = value
    return {**body, "provider": preferences}


def _without_not_blank(node):
    """A copy of a response format without the not-blank pattern, which a free endpoint's grammar engine misreads."""
    if isinstance(node, dict):
        return {k: _without_not_blank(v) for k, v in node.items() if not (k == "pattern" and v == NOT_BLANK)}
    if isinstance(node, list):
        return [_without_not_blank(v) for v in node]
    return node


def mark_prefix(body: dict) -> dict:
    """Mark the stable system prefix as cacheable for the models that need an explicit marker (0.B4).

    The system message holds the prompt and then the knowledge base, which are identical from week to week, and the
    user message holds the week; so the prefix is the cacheable part. OpenAI models cache an identical prefix
    automatically and need nothing; Anthropic models cache what carries a `cache_control` block, so the system
    message is sent as one text block with that marker. Applied at dispatch only, like the routing, so fingerprints
    and saved requests are unchanged.
    """
    model = str(body.get("model") or "")
    messages = body.get("messages")
    if not model.startswith("anthropic/") or not isinstance(messages, list) or not messages:
        return body
    first = messages[0]
    if first.get("role") != "system" or not isinstance(first.get("content"), str):
        return body
    marked = {**first, "content": [{"type": "text", "text": first["content"], "cache_control": {"type": "ephemeral"}}]}
    return {**body, "messages": [marked, *messages[1:]]}


def send(url: str, body: dict, headers: dict[str, str], *, timeout: float, client: httpx.Client | None = None,
         before_send: Callable[[str, dict], None] | None = None) -> httpx.Response:
    """The single dispatch point for model and embedding requests.

    before_send receives the routed body (the run-plan check of E.B1 hooks in here).
    The caller saves the response, then calls raise_for_routing(); nothing retries
    a refused request without the preferences.
    """
    routed = mark_prefix(route(body))
    if before_send is not None:
        before_send(url, routed)
    if client is None:
        with httpx.Client(timeout=timeout) as owned:
            return _post(owned, url, headers, routed)
    return _post(client, url, headers, routed)


def _post(client: httpx.Client, url: str, headers: dict[str, str], routed: dict) -> httpx.Response:
    response = client.post(url, headers=headers, json=routed)
    if not is_free(routed.get("model")):
        return response
    for wait in FREE_RATE_LIMIT_WAITS:
        if not _passing_failure(response):
            break
        time.sleep(_retry_after(response) or wait)
        response = client.post(url, headers=headers, json=routed)
    return response


def _passing_failure(response: httpx.Response) -> bool:
    """A free endpoint's refusal worth waiting out: an HTTP 429, 502 or 503, or a 200 answer whose body carries the
    upstream's 429, 502, 503 or 504 (OpenRouter's "Upstream idle timeout exceeded" from an overloaded free endpoint)."""
    if response.status_code in FREE_RETRY_STATUSES:
        return True
    if response.status_code != 200:
        return False
    try:
        error = response.json().get("error")
    except (ValueError, AttributeError):
        return False
    return isinstance(error, dict) and error.get("code") in (*FREE_RETRY_STATUSES, 504)


def _retry_after(response: httpx.Response) -> float | None:
    try:
        return min(120.0, max(1.0, float(response.headers.get("retry-after", ""))))
    except ValueError:
        return None


def raise_for_routing(response: httpx.Response) -> None:
    """OpenRouter answers 404 when no endpoint satisfies the provider preferences."""
    if response.status_code != 404:
        return
    try:
        message = (response.json().get("error") or {}).get("message", "")
    except ValueError:
        message = response.text[:300]
    # The policy the request was sent under: a free model's has no privacy preferences, so OpenRouter refusing it means the
    # account's own data policy excludes free endpoints (NP.X1), not this routing.
    try:
        model = json.loads(response.request.content or b"{}").get("model")
    except (ValueError, RuntimeError, AttributeError):
        model = None
    raise RoutingError(f"No endpoint satisfies the privacy routing {policy_for(model)}; the request was not sent "
                       f"elsewhere: {message}")


def routing_record(model: str | None = None) -> dict:
    if is_free(model):
        return {"policy": FREE_POLICY, "preferences": {}}
    return {"policy": ROUTING_POLICY, "preferences": dict(ROUTING_PREFERENCES)}
