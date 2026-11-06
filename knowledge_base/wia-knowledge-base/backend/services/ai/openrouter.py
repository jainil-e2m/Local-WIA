"""The one way a KB prompt leaves the building: OpenRouter chat completions with strict JSON output.

Lifted and trimmed from Content Atelier's llm module (routing.py, request.py, call.py), which runs this in
production:
- privacy routing on every request: only endpoints that neither collect nor retain prompts (zero data retention);
  when none qualifies OpenRouter answers 404 and the call fails closed, never re-sent elsewhere;
- strict `json_schema` output, then local validation, and exactly one repair call if the answer breaks the schema;
- a provider's passing limit (429/5xx) is waited out 20, 60 then 120 s;
- `usage: {include: true}`, so the run records what the call actually cost.
"""
import json
import time
from dataclasses import dataclass

import httpx
from pydantic import BaseModel, ValidationError

from backend.config import get_settings
from backend.services.shared.errors import TransientError

PRIVACY = {"data_collection": "deny", "zdr": True, "require_parameters": True, "allow_fallbacks": False}
WAITS = (20, 60, 120)
TIMEOUT_SECONDS = 180


class RoutingError(RuntimeError):
    """No endpoint satisfies the privacy routing. The request was not sent anywhere else."""


class ProviderError(TransientError):
    """OpenRouter failed or answered badly: the job retries a few times, then the run is logged as failed."""
    error_class = "ai_provider"


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
        response = client.post(f"{settings.openrouter_base_url.rstrip('/')}/chat/completions", headers=headers,
                               json=payload, timeout=TIMEOUT_SECONDS)
        if response.status_code == 404:
            raise RoutingError("no zero-retention endpoint serves this model with these parameters")
        if (response.status_code == 429 or response.status_code >= 500) and wait is not None:
            time.sleep(wait)
            continue
        if response.status_code >= 400:
            raise ProviderError(f"OpenRouter answered {response.status_code}")
        data = response.json()
        if isinstance(data.get("error"), dict):
            raise ProviderError(f"OpenRouter error {data['error'].get('code')}")
        return data
    raise ProviderError("OpenRouter kept answering 429/5xx")


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
    usage = {"prompt_tokens": 0, "completion_tokens": 0, "cost": 0.0}
    try:
        payload = body(model=model, system=system, user=user, schema=schema, max_tokens=max_tokens, reasoning=reasoning)
        for attempt in (0, 1):
            data = _post(client, payload)
            for key in usage:
                usage[key] += (data.get("usage") or {}).get(key) or 0
            text = _content(data)
            try:
                output = contract.model_validate(json.loads(text))
                return Answer(output, data.get("model") or model, int(usage["prompt_tokens"]),
                              int(usage["completion_tokens"]), float(usage["cost"]), bool(attempt))
            except (ValueError, ValidationError) as error:
                if attempt:
                    raise ProviderError(f"answer failed the schema after one repair: {type(error).__name__}") from None
                payload = {**payload, "messages": [*payload["messages"], {"role": "assistant", "content": text},
                    {"role": "user", "content": "That answer does not match the required JSON schema "
                     f"({str(error)[:600]}). Answer again with JSON only, matching the schema exactly."}]}
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
