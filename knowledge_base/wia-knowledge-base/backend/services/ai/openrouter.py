"""The one way a KB prompt leaves the building: OpenRouter chat completions with strict JSON output.

Lifted and trimmed from Content Atelier's llm module (routing.py, request.py, call.py), which runs this in
production:
- privacy routing on every request: only endpoints that neither collect nor retain prompts (zero data retention);
  when none qualifies OpenRouter answers 404 and the call fails closed, never re-sent elsewhere;
- strict `json_schema` output, then local validation, and exactly one repair call if the answer breaks the schema;
- a provider's passing limit (429/5xx) is waited out 20, 60 then 120 s;
- `usage: {include: true}`, so the run records what the call actually cost.

Every failure says what it spent (`ProviderError.spent`), so the run log and the monthly budget count billed
attempts that produced nothing. Which failures retry:

| failure                                   | billed?            | class            | the job              |
|-------------------------------------------|--------------------|------------------|----------------------|
| 429 / 5xx after the waits, connect error  | no                 | ProviderError    | retries (AI ladder)  |
| timeout or dropped connection mid-request | unknown: estimated | ProviderError    | retries (AI ladder)  |
| 402 out of credits                        | no                 | OutOfCredits     | waits 6 h            |
| 400 / 401 / 403 / 413 refused             | no                 | ProviderRejected | fails (fix, then `kb ai retry`) |
| schema broken after the one repair        | yes, both calls    | SchemaFailure    | fails: retrying the same input repeats it |
"""
import json
import time
from dataclasses import dataclass

import httpx
from pydantic import BaseModel, ValidationError

from backend.config import get_settings
from backend.services.shared.errors import ThrottledError, TransientError

PRIVACY = {"data_collection": "deny", "zdr": True, "require_parameters": True, "allow_fallbacks": False}
WAITS = (20, 60, 120)
TIMEOUT_SECONDS = 300  # a long transcript with reasoning can take minutes; a timeout costs an estimated call
# Transport errors raised before the request could reach OpenRouter: nothing can have been billed.
NOT_SENT = (httpx.ConnectError, httpx.ConnectTimeout, httpx.PoolTimeout)


class RoutingError(RuntimeError):
    """No endpoint satisfies the privacy routing. The request was not sent anywhere else."""


@dataclass
class Spent:
    """What a call billed before it failed. `unknown`: a request may have been billed without its usage reaching
    us (a timeout or dropped connection mid-request); the runner then records an estimate."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_usd: float = 0.0
    unknown: bool = False


class ProviderError(TransientError):
    """OpenRouter failed or answered badly. Retryable unless a subclass says otherwise; see the table above."""
    error_class = "ai_provider"

    def __init__(self, message: str, *, unknown: bool = False, retry_after: float | None = None):
        super().__init__(message, retry_after=retry_after)
        self.spent = Spent(unknown=unknown)


class SchemaFailure(ProviderError):
    """Still not the schema after the repair: the same input would fail the same way, and both calls were paid."""
    error_class = "ai_schema"
    retryable = False


class ProviderRejected(ProviderError):
    """OpenRouter refused the request itself (bad request, key, permissions, too large): retrying can't help."""
    error_class = "ai_rejected"
    retryable = False


class OutOfCredits(ProviderError, ThrottledError):
    """The OpenRouter account has no credits: wait, like the monthly budget, instead of failing."""
    error_class = "ai_credits"

    def __init__(self, message: str):
        super().__init__(message, retry_after=6 * 3600)


@dataclass
class Answer:
    output: BaseModel
    model: str
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float
    repaired: bool


def body(*, model: str, system: str, user: str, schema: dict, max_tokens: int, reasoning: str | None) -> dict:
    out = {
        "model": model,
        # Anthropic models cache a marked system prefix; the system prompt is the stable part of every call.
        "messages": [{"role": "system", "content": [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]}
                     if model.startswith("anthropic/") else {"role": "system", "content": system},
                     {"role": "user", "content": user}],
        "response_format": {"type": "json_schema", "json_schema": {"name": "kb_output", "strict": True, "schema": schema}},
        "provider": dict(PRIVACY),
        "max_tokens": max_tokens,
        "usage": {"include": True},
    }
    if reasoning:
        out["reasoning"] = {"effort": reasoning}
    return out


def _post(client: httpx.Client, payload: dict) -> dict:
    settings = get_settings()
    headers = {"Authorization": f"Bearer {settings.openrouter_api_key}", "Content-Type": "application/json",
               "X-Title": "WIA Client Knowledge Base"}
    for wait in (*WAITS, None):
        try:
            response = client.post(f"{settings.openrouter_base_url.rstrip('/')}/chat/completions", headers=headers,
                                   json=payload, timeout=TIMEOUT_SECONDS)
        except httpx.TransportError as exc:
            raise ProviderError(f"OpenRouter unreachable: {type(exc).__name__}",
                                unknown=not isinstance(exc, NOT_SENT)) from None
        status = response.status_code
        if status == 404:
            raise RoutingError("no zero-retention endpoint serves this model with these parameters")
        if (status in (408, 429) or status >= 500) and wait is not None:
            time.sleep(wait)
            continue
        if status == 402:
            raise OutOfCredits("OpenRouter: out of credits")
        if status in (400, 401, 403, 413):
            raise ProviderRejected(f"OpenRouter refused the request ({status})")
        if status >= 400:
            raise ProviderError(f"OpenRouter answered {status}")
        try:
            data = response.json()
        except ValueError:
            raise ProviderError("OpenRouter answered with something that isn't JSON", unknown=True) from None
        if isinstance(data.get("error"), dict):
            # An error inside a 200 (the provider failed mid-answer): any usage it reports was billed.
            error = ProviderError(f"OpenRouter error {data['error'].get('code')}")
            error.spent = _usage(data)
            raise error
        return data
    raise ProviderError("OpenRouter kept answering 408/429/5xx")


def _usage(data: dict) -> Spent:
    u = data.get("usage") or {}
    return Spent(int(u.get("prompt_tokens") or 0), int(u.get("completion_tokens") or 0), float(u.get("cost") or 0))


def _content(data: dict) -> str:
    try:
        return data["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError, TypeError):
        raise ProviderError("answer had no message content") from None


def call(contract: type[BaseModel], *, model: str, system: str, user: str, schema: dict, max_tokens: int,
         reasoning: str | None, client: httpx.Client | None = None) -> Answer:
    """One validated answer. A schema failure gets exactly one repair call that shows the model its error."""
    owned = client is None
    client = client or httpx.Client()
    spent = Spent()
    try:
        payload = body(model=model, system=system, user=user, schema=schema, max_tokens=max_tokens, reasoning=reasoning)
        for attempt in (0, 1):
            data = _post(client, payload)
            u = _usage(data)
            spent.prompt_tokens += u.prompt_tokens
            spent.completion_tokens += u.completion_tokens
            spent.cost_usd += u.cost_usd
            text = _content(data)
            try:
                output = contract.model_validate(json.loads(text))
                return Answer(output, data.get("model") or model, spent.prompt_tokens, spent.completion_tokens,
                              spent.cost_usd, bool(attempt))
            except (ValueError, ValidationError) as error:
                if attempt:
                    raise SchemaFailure(f"answer failed the schema after one repair: {type(error).__name__}") from None
                payload = {**payload, "messages": [*payload["messages"], {"role": "assistant", "content": text},
                    {"role": "user", "content": "That answer does not match the required JSON schema "
                     f"({str(error)[:600]}). Answer again with JSON only, matching the schema exactly."}]}
    except ProviderError as error:
        # Everything paid before the failure, plus the failing request's own (known or unknown) part.
        error.spent = Spent(spent.prompt_tokens + error.spent.prompt_tokens,
                            spent.completion_tokens + error.spent.completion_tokens,
                            spent.cost_usd + error.spent.cost_usd, error.spent.unknown)
        raise
    finally:
        if owned:
            client.close()
    raise AssertionError("unreachable")


def models_available(ids: list[str]) -> dict[str, bool]:
    """Whether each model id exists on OpenRouter (the public model list; no key, no completion)."""
    response = httpx.get(f"{get_settings().openrouter_base_url.rstrip('/')}/models", timeout=30)
    response.raise_for_status()
    known = {m.get("id") for m in response.json().get("data", [])}
    return {i: i in known for i in ids}
