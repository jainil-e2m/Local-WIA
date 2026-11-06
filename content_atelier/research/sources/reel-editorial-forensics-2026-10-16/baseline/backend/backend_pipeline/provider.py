from __future__ import annotations

import json
import os
import re
from collections.abc import Callable
from typing import Protocol

import httpx


class ModelProvider(Protocol):
    def json_call(self, *, stage: str, system: str, user: str, schema: dict, fingerprint: str) -> tuple[dict, dict]: ...
    def embed(self, *, text: str, fingerprint: str) -> tuple[list[float], dict]: ...


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
    if model in {"openai/gpt-6-luna", "openai/gpt-6-luna-pro", "openai/gpt-6.1-sol", "anthropic/claude-sonnet-5.5"}:
        # Exact route does not advertise temperature. Keep other model requests
        # byte-compatible with their preserved baseline/replay artifacts.
        body.pop("temperature")
        body["usage"] = {"include": True}
    return body


def embedding_body(*, model: str, text: str | list[str], dimensions: int) -> dict:
    return {"model": model, "input": text, "dimensions": dimensions, "encoding_format": "float"}


class LiveProvider:
    def __init__(
        self,
        *,
        llm_base_url: str,
        moments_model: str,
        moments_key: str | None,
        angles_model: str,
        angles_key: str | None,
        embedding_base_url: str,
        embedding_model: str,
        embedding_key: str | None,
        dimensions: int,
        timeout: float,
        on_response: Callable[[str, dict], None] | None = None,
        max_tokens: int | None = None,
        reasoning_effort: str | None = None,
        response_format: str = "json_schema",
    ):
        self.llm_base_url = llm_base_url.rstrip("/")
        self.moments_model, self.moments_key = moments_model, moments_key
        self.angles_model, self.angles_key = angles_model, angles_key
        self.embedding_base_url, self.embedding_key = embedding_base_url.rstrip("/"), embedding_key
        self.embedding_model = embedding_model
        self.dimensions = dimensions
        self.timeout = timeout
        self.on_response = on_response
        self.max_tokens = max_tokens
        self.reasoning_effort = reasoning_effort
        self.response_format = response_format

    def _received(self, response: httpx.Response, fingerprint: str) -> dict:
        try:
            raw = response.json()
        except ValueError:
            raw = {"unparsed_response": response.text, "http_status": response.status_code}
        # Save the received body before HTTP/JSON/schema processing can fail.
        if self.on_response:
            self.on_response(fingerprint, raw)
        response.raise_for_status()
        if not isinstance(raw, dict):
            raise TypeError("Provider response must be an object")
        return raw

    def _headers(self, key: str | None) -> dict[str, str]:
        key = key or os.getenv("OPENROUTER_API_KEY")
        if not key:
            raise RuntimeError("OPENROUTER_API_KEY is required for live mode")
        return {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://content-atelier.local",
            "X-Title": "Content Atelier",
        }

    def json_call(self, *, stage: str, system: str, user: str, schema: dict, fingerprint: str) -> tuple[dict, dict]:
        if stage not in {'moment_extraction','angle_generation','angle_refinement','brief_plan','brief_grade','brief_write','brief_review','brief_repair','brief_web'}:
            raise ValueError('Unsupported generation stage')
        model = self.moments_model if stage == "moment_extraction" else self.angles_model
        key = self.moments_key if stage == "moment_extraction" else self.angles_key
        body = chat_body(
            model=model,
            system=system,
            user=user,
            schema=schema,
            max_tokens=self.max_tokens,
            reasoning_effort=self.reasoning_effort,
            response_format=self.response_format,
        )
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(f"{self.llm_base_url}/chat/completions", headers=self._headers(key), json=body)
            raw = self._received(response, fingerprint)
        if raw["choices"][0].get("finish_reason") not in {None, "stop"}:
            raise ValueError("Provider response was incomplete or refused")
        content = raw["choices"][0]["message"].get("content")
        if isinstance(content, str):
            return json.loads(content), {"raw": raw, "fingerprint": fingerprint}
        if isinstance(content, dict):
            return content, {"raw": raw, "fingerprint": fingerprint}
        raise ValueError("Provider returned no JSON content")

    def embed(self, *, text: str, fingerprint: str) -> tuple[list[float], dict]:
        key = self.embedding_key or os.getenv("OPENAI_API_KEY")
        if not key:
            raise RuntimeError("OPENAI_API_KEY is required for embeddings")
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        body = embedding_body(model=self.embedding_model, text=text, dimensions=self.dimensions)
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(f"{self.embedding_base_url}/embeddings", headers=headers, json=body)
            raw = self._received(response, fingerprint)
        return raw["data"][0]["embedding"], {"raw": raw, "fingerprint": fingerprint}

    def embed_many(self, *, texts: list[str], fingerprint: str) -> dict:
        """Archive the entire batch before its indices or vectors are validated."""
        if not texts or any(not isinstance(text, str) or not text.strip() for text in texts):
            raise ValueError('Embedding batch requires nonempty text inputs')
        key = self.embedding_key or os.getenv('OPENAI_API_KEY')
        if not key:
            raise RuntimeError('Configured embedding credential is required')
        body = embedding_body(model=self.embedding_model, text=texts, dimensions=self.dimensions)
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(f'{self.embedding_base_url}/embeddings',
                headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'}, json=body)
            return self._received(response, fingerprint)


class FakeProvider:
    """Deterministic offline provider for contract tests; never represents real model output."""

    def __init__(self, dimensions: int = 1536):
        self.dimensions = dimensions

    def json_call(self, *, stage: str, system: str, user: str, schema: dict, fingerprint: str) -> tuple[dict, dict]:
        if stage == "moment_extraction":
            packet = user.split("Source packet:\n", 1)[1]
            if packet.startswith("MEETING "):
                refs = re.findall(r"^((?:m\d+\.t)?\d+)\|", packet, flags=re.MULTILINE)
                refs += [json.loads(line[8:])["ref"] for line in packet.splitlines() if line.startswith("UNTIMED ")]
            else:
                refs = [span["span_id"] for span in json.loads(packet)]
            output = {
                "moments": [],
                "processed_span_ids": refs,
                "coverage_notes": ["offline fake provider: no editorial selection"],
            }
            if "processed_meetings" in schema.get("required", []):
                groups = {}
                for ref in refs:
                    groups.setdefault(ref.split(".", 1)[0], []).append(ref)
                for rs in groups.values():
                    rs.sort(key=lambda ref: int(ref.split(".t", 1)[1]))
                output.pop("processed_span_ids")
                output["processed_meetings"] = [
                    {"meeting_ref": m, "first_span_id": rs[0], "last_span_id": rs[-1], "span_count": len(rs)}
                    for m, rs in groups.items()
                ]
            return output, {
                "fingerprint": fingerprint,
                "fake": True,
            }
        output = {"angles": [], "processed_moment_ids": [], "coverage_notes": ["offline fake provider"]}
        if "internal_insights" in schema.get("required", []):
            output["internal_insights"] = []
        return output, {
            "fingerprint": fingerprint,
            "fake": True,
        }

    def embed(self, *, text: str, fingerprint: str) -> tuple[list[float], dict]:
        import hashlib

        digest = hashlib.sha256(text.encode()).digest()
        vector = [((digest[i % len(digest)] / 255.0) * 2) - 1 for i in range(self.dimensions)]
        return vector, {"fingerprint": fingerprint, "fake": True}
