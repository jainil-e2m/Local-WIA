"""The model and embedding providers (plan 0.B4): one live implementation, with S.B1 routing, the E.B1 run-plan check,
cost capture and the `llm_runs` record on every call, and the offline fake used by the test suites.

Callers never build requests to a model endpoint themselves: they use these, or `llm.transport.dispatch` for a single
JSON request (the evaluation harness), and a test scans the source for anything else.
"""
from __future__ import annotations

import json
import os
import re
from collections.abc import Callable
from contextlib import contextmanager
from typing import Protocol

from .request import chat_body, embedding_body
from .routing import routing_record
from .runs import FAKE_POLICY, LlmRuns
from .transport import dispatch_retrying_empty

# Content packs (Phase NP): v1's two stages and every v2 stage, NP-7's included. Without them a live pack call was refused
# here as an unsupported stage (found by NP.X2a's capped call before any paid pack run).
PACK_STAGES = {'pack_write', 'pack_review', 'pack_finish', 'pack_check', 'pack_repair', 'pack_recheck', 'pack_caption', 'pack_refinish'}
JSON_STAGES = {'moment_extraction', 'angle_generation', 'angle_refinement', 'card_verification', 'context_mining', 'document_classification', 'brief_plan',
               'brief_grade', 'brief_write', 'brief_review', 'brief_repair', 'brief_verify', 'brief_web', 'topic_assignment', *PACK_STAGES}


class ModelProvider(Protocol):
    def json_call(self, *, stage: str, system: str, user: str, schema: dict, fingerprint: str) -> tuple[dict, dict]: ...
    def embed(self, *, text: str, fingerprint: str) -> tuple[list[float], dict]: ...


class ProviderOutputError(ValueError):
    """The provider answered, but not with usable JSON. Carries what it said, for the repair call and the record."""

    def __init__(self, message: str, *, content=None, raw=None):
        super().__init__(message)
        self.content, self.raw = content, raw


class InvalidJson(ProviderOutputError, json.JSONDecodeError):
    """The answer is not parseable JSON (repairable once). Still a JSONDecodeError, as callers expect."""

    def __init__(self, decode_error: json.JSONDecodeError, *, content=None, raw=None):
        json.JSONDecodeError.__init__(self, decode_error.msg, decode_error.doc, decode_error.pos)
        self.content, self.raw = content, raw


class NoJsonContent(ProviderOutputError):
    """The answer carries no JSON content (repairable once)."""


class IncompleteResponse(ProviderOutputError):
    """The answer was cut off or refused (finish_reason is not "stop"). A repair cannot fix a truncated answer."""


class LiveProvider:
    records_runs = True

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
        stage_models: dict[str, str] | None = None,
        before_send: Callable[[str, dict], None] | None = None,
        plan=None,
        runs: LlmRuns | None = None,
        effort_for: Callable[[str], str | None] | None = None,
        tokens_for: Callable[[str], int | None] | None = None,
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
        # Reasoning effort per stage (0.B4); a single value when no per-stage source is given.
        self.effort_for = effort_for
        # The output cap per stage (models.completion_tokens.<stage>); max_tokens when no per-stage source is given.
        self.tokens_for = tokens_for
        self.response_format = response_format
        # Per-stage model overrides that share the angles credential (e.g. angle_generation).
        self.stage_models = dict(stage_models or {})
        # Called with each routed request just before it leaves.
        self.before_send = before_send
        # Every live call reserves against an active run plan (E.B1); without one it is refused.
        if plan is None:
            from .run_plans import from_environment
            plan = from_environment()
        self.plan = plan
        # The llm_runs recorder for refused attempts and the prompt and knowledge-base versions of planned calls.
        self.runs = runs
        # The input set this provider's calls are for (a weekly run's transcripts); the plan must cover it.
        self.input_set_hash = None
        # What the caller knows about the next calls (prompt and knowledge-base versions, the run), for llm_runs.
        self.context: dict = {}

    @contextmanager
    def call_context(self, **context):
        """Name the prompt version, the knowledge-base version and run for the calls made inside the block."""
        before = self.context
        self.context = {**before, **{k: v for k, v in context.items() if v is not None}}
        try:
            yield self
        finally:
            self.context = before

    def _dispatch(self, *, stage: str, model: str, fingerprint: str, url: str, body: dict, headers: dict) -> dict:
        """Reserve a planned call, send it with the privacy routing, save and settle the response."""
        return self._dispatch_retrying(stage=stage, model=model, fingerprint=fingerprint, url=url, body=body, headers=headers)[0]

    def _dispatch_retrying(self, *, stage: str, model: str, fingerprint: str, url: str, body: dict, headers: dict,
                           structured: bool = False):
        """`_dispatch`, and a chat answer with no content at its length limit (a JSON answer: cut off there) is asked again
        once, with a raised limit (E.B1); returns the answer and what the first call was when a retry was made."""
        return dispatch_retrying_empty(plan=self.plan, runs=self.runs, stage=stage, model=model, fingerprint=fingerprint, url=url,
                                       body=body, headers=headers, timeout=self.timeout, input_set_hash=self.input_set_hash,
                                       on_response=self.on_response, before_send=self.before_send, context=self.context,
                                       structured=structured)

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
        if stage not in JSON_STAGES:
            raise ValueError('Unsupported generation stage')
        model = self.moments_model if stage == "moment_extraction" else self.stage_models.get(stage, self.angles_model)
        key = self.moments_key if stage == "moment_extraction" else self.angles_key
        body = chat_body(
            model=model,
            system=system,
            user=user,
            schema=schema,
            max_tokens=self.tokens_for(stage) if self.tokens_for else self.max_tokens,
            reasoning_effort=self.effort_for(stage) if self.effort_for else self.reasoning_effort,
            response_format=self.response_format,
        )
        raw, retried = self._dispatch_retrying(stage=stage, model=model, fingerprint=fingerprint,
                                               url=f"{self.llm_base_url}/chat/completions", body=body, headers=self._headers(key),
                                               structured=True)
        choice = raw["choices"][0]
        if choice.get("finish_reason") not in {None, "stop"}:
            raise IncompleteResponse("Provider response was incomplete or refused"
                                     + (" (after one retry with a raised output limit)" if retried else ""), raw=raw)
        # What the first call cost is kept beside the answer that replaced it: the artifact's usage is the last call's.
        meta = {"raw": raw, "fingerprint": fingerprint, "routing": routing_record(model), **({"retried": retried} if retried else {})}
        content = choice["message"].get("content")
        if isinstance(content, str):
            try:
                return json.loads(content), meta
            except json.JSONDecodeError as exc:
                raise InvalidJson(exc, content=content, raw=raw) from exc
        if isinstance(content, dict):
            return content, meta
        raise NoJsonContent("Provider returned no JSON content", raw=raw)

    def embed(self, *, text: str, fingerprint: str) -> tuple[list[float], dict]:
        key = self.embedding_key or os.getenv("OPENAI_API_KEY")
        if not key:
            raise RuntimeError("OPENAI_API_KEY is required for embeddings")
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        body = embedding_body(model=self.embedding_model, text=text, dimensions=self.dimensions)
        raw = self._dispatch(stage="embedding", model=self.embedding_model, fingerprint=fingerprint,
                             url=f"{self.embedding_base_url}/embeddings", body=body, headers=headers)
        return raw["data"][0]["embedding"], {"raw": raw, "fingerprint": fingerprint, "routing": routing_record()}

    def embed_many(self, *, texts: list[str], fingerprint: str) -> dict:
        """Archive the entire batch before its indices or vectors are validated."""
        if not texts or any(not isinstance(text, str) or not text.strip() for text in texts):
            raise ValueError('Embedding batch requires nonempty text inputs')
        key = self.embedding_key or os.getenv('OPENAI_API_KEY')
        if not key:
            raise RuntimeError('Configured embedding credential is required')
        body = embedding_body(model=self.embedding_model, text=texts, dimensions=self.dimensions)
        return self._dispatch(stage='embedding', model=self.embedding_model, fingerprint=fingerprint,
                              url=f'{self.embedding_base_url}/embeddings', body=body,
                              headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'})


class FakeProvider:
    """Deterministic offline provider for contract tests; never represents real model output."""

    records_runs = False
    policy = FAKE_POLICY

    def __init__(self, dimensions: int = 1536):
        self.dimensions = dimensions

    def json_call(self, *, stage: str, system: str, user: str, schema: dict, fingerprint: str) -> tuple[dict, dict]:
        if stage == "moment_extraction" and "scenes" in schema.get("required", []):
            # A document's scene extraction (2.B2): no editorial selection, the delivered meeting acknowledged as inventoried.
            inventory = json.loads(re.search(r"\(not conversation evidence\):\n(\[[^\n]*\])", system).group(1))
            return {"scenes": [], "processed_meetings": inventory,
                    "coverage_notes": ["offline fake provider: no editorial selection"]}, {"fingerprint": fingerprint, "fake": True}
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
        if "week_summary" in schema.get("required", []):
            return {"week_summary": "offline fake provider: no editorial selection", "angles": [],
                    "internal_insights": [], "considered_not_selected": []}, {"fingerprint": fingerprint, "fake": True}
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


def live_provider(models, *, storage=None, on_response=None, model: str | None = None, stage_models: dict | None = None,
                  runs: LlmRuns | None = None, plan=None, chat: bool = True, key: str | None = None) -> LiveProvider:
    """The live provider every caller builds (0.B4): models and reasoning effort per stage from the settings, the run
    plan from the environment, and the llm_runs record in the storage database when `storage` is given.

    `model` serves every chat stage with one model (brief and pack stages, whose models come from the storage
    settings); otherwise each stage takes `models.model_for(stage)`. `chat=False` builds an embeddings-only provider.
    """
    stages = {s: models.model_for(s) for s in JSON_STAGES} if model is None else {}
    stages.update(stage_models or {})
    if runs is None and storage is not None:
        runs = LlmRuns.for_storage(storage)
    angles_key = key or models.openrouter_angles_key
    return LiveProvider(
        llm_base_url=models.openrouter_base_url, moments_model=(model or models.openrouter_moments_model) if chat else "",
        moments_key=(key or models.openrouter_moments_key) if model is None else angles_key,
        angles_model=(model or models.openrouter_angles_model) if chat else "", angles_key=angles_key,
        embedding_base_url=models.embedding_base_url, embedding_model=models.embedding_model, embedding_key=models.embedding_api_key,
        dimensions=models.embedding_dimensions, timeout=models.request_timeout_seconds, on_response=on_response,
        max_tokens=models.llm_completion_tokens, effort_for=models.reasoning_effort_for, tokens_for=models.completion_tokens_for,
        response_format=models.llm_response_format, stage_models=stages, runs=runs, plan=plan)
