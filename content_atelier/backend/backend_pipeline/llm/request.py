"""Request building and fingerprints (0.B4).

The fingerprint recipes are the ones the saved artifacts were keyed with, so saved Week 1 artifacts replay with
identical hashes; they move here unchanged, with the builders for the request bodies.
"""
from __future__ import annotations

import hashlib
import json

from ..store import canonical_hash

# The models whose route does not advertise temperature (the preserved baseline requests for the others keep it).
# Opus 5.5 is the pack finisher (NP.B5): without it here a request would send temperature with require_parameters and never
# ask for usage, so its cost would settle at 0.
NO_TEMPERATURE = {"openai/gpt-6-luna", "openai/gpt-6-luna-pro", "openai/gpt-6.1-sol", "anthropic/claude-sonnet-5.5",
                  "anthropic/claude-opus-5.5"}


def chat_body(
    *,
    model: str,
    system: str,
    user: str,
    schema: dict,
    max_tokens: int | None = None,
    reasoning_effort: str | None = None,
    response_format: str = "json_schema",
) -> dict:
    if response_format not in {"json_schema", "json_object"}:
        raise ValueError("Unsupported configured response format")
    if response_format == "json_object":
        # JSON mode does not enforce a schema. Supply the entire contract at
        # system authority, outside the untrusted source packet; validate locally.
        system += "\n\nRequired response JSON contract (validated by the backend):\n" + json.dumps(
            schema, ensure_ascii=False, separators=(",", ":")
        )
    body = {
        "model": model,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "temperature": 0.2,
        "response_format": {"type": "json_schema", "json_schema": {"name": "atelier_output", "strict": True, "schema": schema}},
        "provider": {"require_parameters": True, "allow_fallbacks": False},
    }
    if response_format == "json_object":
        body["response_format"] = {"type": "json_object"}
    if max_tokens is not None:
        body["max_tokens"] = max_tokens
    if reasoning_effort is not None:
        body["reasoning"] = {"effort": reasoning_effort}
    if model in NO_TEMPERATURE:
        # Exact route does not advertise temperature. Keep other model requests
        # byte-compatible with their preserved baseline/replay artifacts.
        body.pop("temperature")
        body["usage"] = {"include": True}
    return body


def stage_body(settings, stage: str, system: str, user: str, schema: dict, *, model: str | None = None) -> dict:
    """A chat request for one stage: its model and its reasoning effort come from the settings (per stage)."""
    return chat_body(model=model or settings.model_for(stage), system=system, user=user, schema=schema,
                     max_tokens=settings.completion_tokens_for(stage), reasoning_effort=settings.reasoning_effort_for(stage),
                     response_format=settings.llm_response_format)


def embedding_body(*, model: str, text: str | list[str], dimensions: int) -> dict:
    return {"model": model, "input": text, "dimensions": dimensions, "encoding_format": "float"}


VALIDATION_VERSION = 4


def stage_fingerprint(*, mode: str, stage: str, endpoint: str, request: dict, input_hash: str | None = None,
                      validation_version: int | None = None) -> str:
    """The key of a stage call on the weekly pipeline (file artifacts and the SQL worker).

    The key names the validator version the output passed: an artifact saved under an older one (the 12 October SQL run was
    version 3) is never served as is, only re-checked under today's rules (E.B12a). `validation_version` is for reading
    such keys (`llm/replay_check.py`), never for writing."""
    return canonical_hash({
        "cache_version": 2,
        "validation_version": 2 if stage == "embedding" else (validation_version or VALIDATION_VERSION),
        "namespace": "fake" if mode == "fake" else "live",
        "stage": stage,
        "endpoint": endpoint,
        "request": request,
        "input_hash": input_hash,
    })


def workflow_fingerprint(*, workflow: str, stage: str, request: dict, endpoint: str, synthetic: bool) -> str:
    """The key of a brief or pack call."""
    return canonical_hash({"workflow": workflow, "stage": stage, "request": request, "endpoint": endpoint, "synthetic": synthetic})


def prefix_hash(request: dict) -> str:
    """Hash of the system message: equal across weeks when the prompt and knowledge base are, which is what a provider's
    prompt cache keys on. Recorded on every call, so a change that breaks the prefix shows in `llm_runs`."""
    messages = request.get("messages") or []
    system = messages[0].get("content") if messages and messages[0].get("role") == "system" else ""
    return hashlib.sha256(str(system).encode("utf-8")).hexdigest()


def repair_user(user: str, output, problem: str) -> str:
    """The user message of the one repair call (0.B4): the original material, the rejected answer and what failed."""
    shown = output if isinstance(output, str) else json.dumps(output, ensure_ascii=False)
    return (user + "\n\n## Correction needed\n\nYour previous answer could not be used because it failed validation:\n"
            + problem[:1500] + "\n\nReturn the complete corrected JSON that satisfies the required schema. Keep everything "
            "else unless a fix requires a change.\n\nPrevious answer:\n" + shown[:60000])


def repair_fingerprint(fingerprint: str, user: str) -> str:
    return canonical_hash({"repair_of": fingerprint, "attempt": 1, "user": user})


def retry_fingerprint(fingerprint: str, max_tokens: int) -> str:
    """The key of the one retry of a call that came back with no content at its length limit (E.B1)."""
    return canonical_hash({"retry_of": fingerprint, "attempt": 1, "max_tokens": max_tokens})
