"""One call to a provider, and the plain JSON call built on it (plan 0.B4).

`provider_call` is the single place that sends a JSON request to a provider and makes sure the call is recorded: a live
provider writes its own `llm_runs` row (the plan store, then the annotation); the offline provider, and any test
double, does not, so the row is written here with the offline policy. `json_call` adds validation and the one repair for
the callers that have no artifact store of their own (the learning loop's categoriser).
"""
from __future__ import annotations

import re
import time
from collections.abc import Callable

import httpx
from pydantic import ValidationError

from .providers import IncompleteResponse, InvalidJson, NoJsonContent
from .request import prefix_hash, repair_fingerprint, repair_user
from .runs import FAKE_POLICY, LlmRuns
from .transport import UpstreamError

# A provider's passing limit or outage is waited out, not handed to a person as a failed step. Found on production, 2 November:
# large brief requests on the one route the privacy rules allow were answered 429 for minutes while small ones passed. The
# waits fit inside every stage's timeout, and a call answered with an error costs nothing.
TRANSIENT_WAITS = (20, 60, 120)
# The weekly cycle's two stages it cannot finish without, the scenes and the cards. The cycle runs unattended early on Sunday
# (the first live week, 1 to 2 November 2026, needed a person for every failure), so their passing limits and outages are
# waited out for longer, about 14 minutes in all, inside the stages' hour (jobs/policy.py). The cycle's optional calls (the
# card verifier's model pass) still degrade at the first failure.
UNATTENDED_WAITS = (30, 90, 240, 480)
UNATTENDED_STAGES = frozenset({"moment_extraction", "angle_generation"})
_TRANSIENT_IN_BODY = re.compile(r"answered with an error \((?:429|5\d\d)\)")


def transient(error: BaseException) -> bool:
    """Whether a failed call is the provider's passing limit or outage: HTTP 429 or 5xx, the same inside a 200 body, or a
    connection that could not be opened (nothing was sent, so nothing was charged). A read timeout is not: the provider may
    have answered and charged."""
    if isinstance(error, httpx.HTTPStatusError):
        return error.response.status_code == 429 or error.response.status_code >= 500
    if isinstance(error, (httpx.ConnectError, httpx.ConnectTimeout)):
        return True
    if isinstance(error, IncompleteResponse):
        # An answer that ended in the provider's own error with nothing written (finish_reason "error", 0 tokens out:
        # a call of 4 November, read as cut off, failed its document's scenes). A real cut-off ("length") is not passing.
        choices = (getattr(error, "raw", None) or {}).get("choices") or [{}]
        return choices[0].get("finish_reason") == "error" and not (choices[0].get("message") or {}).get("content")
    return isinstance(error, UpstreamError) and bool(_TRANSIENT_IN_BODY.search(str(error)))


def provider_call(provider, runs: LlmRuns | None, *, stage: str, model: str, system: str, user: str, schema: dict, fingerprint: str,
                  context: dict | None = None, request: dict | None = None, details: dict | None = None):
    """Returns the provider's (output, meta). `context` names the prompt and knowledge-base versions (and anything else
    worth keeping about the call) for the llm_runs row."""
    context = {k: v for k, v in (context or {}).items() if v is not None}
    records = getattr(provider, "records_runs", False)
    extra = {**(details or {}), **({"prefix_hash": prefix_hash(request)} if request else {}),
             **{k: v for k, v in context.items() if k not in ("prompt_version", "knowledge_base_version")}}
    try:
        if records and hasattr(provider, "call_context"):
            with provider.call_context(**context):
                return provider.json_call(stage=stage, system=system, user=user, schema=schema, fingerprint=fingerprint)
        result = provider.json_call(stage=stage, system=system, user=user, schema=schema, fingerprint=fingerprint)
    except Exception as exc:
        if not records and runs is not None:
            refused = type(exc).__name__ in ("RoutingError", "RunPlanError")
            runs.record(stage=stage, model=model, fingerprint=fingerprint, status="refused" if refused else "failed",
                        error=f"{type(exc).__name__}: {exc}"[:500], provider="fake", routing_policy=FAKE_POLICY,
                        prompt_version=context.get("prompt_version"), knowledge_base_version=context.get("knowledge_base_version"),
                        details=extra)
        raise
    if not records and runs is not None:
        runs.record(stage=stage, model=model, fingerprint=fingerprint, status="succeeded", raw=result[1].get("raw"),
                    provider="fake", routing_policy=FAKE_POLICY, prompt_version=context.get("prompt_version"),
                    knowledge_base_version=context.get("knowledge_base_version"), details=extra)
    return result


def patient_call(provider, runs: LlmRuns | None, *, waits=TRANSIENT_WAITS, **call):
    """`provider_call` for a stage a person is waiting on (a brief, a pack, a refresh) or that must finish unattended (the weekly
    scenes and cards, with UNATTENDED_WAITS): the provider's passing limits are waited out, each attempt recorded. The weekly
    cycle's optional calls stay on `provider_call`, which degrades at the first failure."""
    for wait in (*waits, None):
        try:
            return provider_call(provider, runs, **call)
        except Exception as exc:
            if wait is None or not transient(exc):
                raise
            time.sleep(wait)


def provider_embed(provider, runs: LlmRuns | None, *, model: str, fingerprint: str, text: str | None = None,
                   texts: list[str] | None = None, context: dict | None = None):
    """One embedding call (`embed` for a text, `embed_many` for a batch), recorded like provider_call's."""
    context = {k: v for k, v in (context or {}).items() if v is not None}
    records = getattr(provider, "records_runs", False)
    extra = {**{k: v for k, v in context.items() if k not in ("prompt_version", "knowledge_base_version")},
             "inputs": len(texts) if texts is not None else 1}
    try:
        if texts is not None:
            result = provider.embed_many(texts=texts, fingerprint=fingerprint)
        else:
            result = provider.embed(text=text, fingerprint=fingerprint)
    except Exception as exc:
        if not records and runs is not None:
            runs.record(stage="embedding", model=model, fingerprint=fingerprint, status="failed",
                        error=f"{type(exc).__name__}: {exc}"[:500], provider="fake", routing_policy=FAKE_POLICY,
                        prompt_version=context.get("prompt_version"), details=extra)
        raise
    if not records and runs is not None:
        raw = result if texts is not None else result[1].get("raw")
        runs.record(stage="embedding", model=model, fingerprint=fingerprint, status="succeeded", raw=raw if isinstance(raw, dict) else None,
                    provider="fake", routing_policy=FAKE_POLICY, prompt_version=context.get("prompt_version"), details=extra)
    return result


def json_call(provider, runs: LlmRuns | None, *, stage: str, model: str, system: str, user: str, schema: dict, fingerprint: str,
              validate: Callable[[dict], None] | None = None, repair: bool = True, context: dict | None = None):
    """A JSON call with no artifact store: dispatch, validate, and on a schema failure exactly one repair call.

    `validate` raises ValidationError or SchemaViolation for a schema failure (repairable) and anything else for a content
    failure (not). Returns the validated output.
    """
    from .stage import SchemaViolation  # noqa: F401  (the failure type validators raise)
    from .stage import repairable
    rejected = None
    try:
        output, _ = provider_call(provider, runs, stage=stage, model=model, system=system, user=user, schema=schema,
                                  fingerprint=fingerprint, context=context)
        rejected = output
        if validate:
            validate(output)
        return output
    except (ValidationError, InvalidJson, NoJsonContent, ValueError, TypeError, KeyError) as first:
        if not (repair and repairable(first)):
            raise
        shown = rejected if rejected is not None else getattr(first, "content", None)
        repaired_user = repair_user(user, shown, f"{type(first).__name__}: {first}")
        try:
            output, _ = provider_call(provider, runs, stage=stage, model=model, system=system, user=repaired_user, schema=schema,
                                      fingerprint=repair_fingerprint(fingerprint, repaired_user),
                                      context={**(context or {}), "repair_of": fingerprint})
            if validate:
                validate(output)
        except (ValueError, TypeError, KeyError) as second:
            second.add_note(f"One repair call was made after: {first}")
            raise
        return output
