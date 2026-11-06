"""One paid request, from reservation to settlement (plan 0.B4, E.B1, S.B1).

The live provider and the evaluation harness both send through `dispatch`: it reserves the call against the run plan,
sends the request with the privacy routing, saves the received body before anything can fail, raises on a routing
refusal or an HTTP error, settles the call (cost, tokens, status) and completes the `llm_runs` row. Nothing here retries
a refused request without the preferences. The one retry it does make is `dispatch_retrying_empty`'s: an answer with no
content at its length limit, or a structured answer cut off there, is asked again once with a higher limit, as its own
planned call (E.B1).
"""
from __future__ import annotations

from collections.abc import Callable

import httpx

from .request import prefix_hash, retry_fingerprint
from .routing import RoutingError, raise_for_routing, send
from .run_plans import RunPlanError, worst_case_usd
from .runs import LlmRuns, usage_of


class UpstreamError(ValueError):
    """The provider answered HTTP 200 without a result: an upstream error inside the body, or no `choices` (chat) or `data`
    (embeddings). The call failed; it is settled as failed with the provider's message. A ValueError, so the callers that
    degrade on an unavailable model (the verifier's model pass, the learning loop's categoriser) treat it as one, and it is
    never a schema failure, so it is not repaired."""


# The request reached the provider but its answer was lost on the way back: the connection closed mid-body, or the read
# failed or timed out. The provider may have finished and billed it (N2, 23 October: a Sonnet brief grade cut off after 341
# seconds cost USD 0.14 that its plan never saw), so the call is settled at its worst case, never at nothing: the plan's
# spend must not fall below what the key was charged.
ANSWER_LOST = (httpx.RemoteProtocolError, httpx.ReadError, httpx.ReadTimeout)


def lost_answer_charge(model: str, body: dict) -> dict | None:
    """What a call whose answer was lost is settled at: its worst case (None when the model's price is unknown)."""
    worst = worst_case_usd(model, body)
    return {"usage": {"cost": worst}, "cost_basis": "worst_case_answer_lost"} if worst else None


def _missing_result(raw: dict, body: dict | None) -> str | None:
    """Why a 200 body holds no usable result, or None when it does."""
    error = raw.get("error")
    if error:
        message = error.get("message") if isinstance(error, dict) else str(error)
        code = error.get("code") if isinstance(error, dict) else None
        return f"the provider answered with an error{f' ({code})' if code else ''}: {str(message or error)[:300]}"
    if body and "messages" in body and not (isinstance(raw.get("choices"), list) and raw["choices"]):
        return "the provider's answer has no choices"
    if body and "input" in body and "messages" not in body and not (isinstance(raw.get("data"), list) and raw["data"]):
        return "the provider's answer has no data"
    return None


def received(response: httpx.Response, fingerprint: str, on_response: Callable[[str, dict], None] | None = None,
             body: dict | None = None) -> dict:
    try:
        raw = response.json()
    except ValueError:
        raw = {"unparsed_response": response.text, "http_status": response.status_code}
    # Save the received body before HTTP/JSON/schema processing can fail.
    if on_response:
        on_response(fingerprint, raw)
    raise_for_routing(response)
    response.raise_for_status()
    if not isinstance(raw, dict):
        raise TypeError("Provider response must be an object")
    # OpenRouter can answer 200 with an upstream failure in the body (cost 0); that is a failed call, not a success.
    if why := _missing_result(raw, body):
        raise UpstreamError(f"Model call failed: {why}")
    return raw


# E.B1 (extension): a reasoning model can spend its whole output limit thinking and answer `content: null` with a
# length finish (Sonnet 5.5 through Google on 20 October, at 9,000 and 16,000 output tokens: about USD 0.40 lost).
# Asking again with the same limit would do the same, so the one retry raises it: twice the limit the call had (or the
# tokens the answer used when it had none), at least the floor and at most the ceiling.
RETRY_LIMIT_FACTOR, RETRY_LIMIT_FLOOR, RETRY_LIMIT_CEILING = 2, 24_000, 64_000


def _choice(raw) -> dict:
    choices = raw.get("choices") if isinstance(raw, dict) else None
    return choices[0] if isinstance(choices, list) and choices and isinstance(choices[0], dict) else {}


def has_no_content(raw) -> bool:
    """The first choice carries no answer: content is null, empty or blank."""
    message = _choice(raw).get("message")
    content = message.get("content") if isinstance(message, dict) else None
    return content is None or (isinstance(content, (str, list, dict)) and not (content.strip() if isinstance(content, str) else content))


def cut_off_without_content(raw) -> bool:
    """No content and a length finish: the answer ran out of output limit before it wrote anything."""
    return _choice(raw).get("finish_reason") == "length" and has_no_content(raw)


def cut_off(raw, *, structured: bool) -> bool:
    """The answer ran out of output limit and cannot be used: it wrote nothing, or, when a structured (JSON) answer was
    asked for, it stopped part way, which no parser can read (N2, 23 October: a brief's claim check of 126 statements
    used 8,601 reasoning tokens and stopped at statement 100 of its 16,000)."""
    return _choice(raw).get("finish_reason") == "length" and (structured or has_no_content(raw))


def raised_output_limit(body: dict, raw: dict) -> int | None:
    """The limit for the one retry, or None when the call already had the ceiling (a retry could not help)."""
    used = (raw.get("usage") or {}).get("completion_tokens") if isinstance(raw, dict) else None
    had = body.get("max_tokens") or body.get("max_completion_tokens") or (used if isinstance(used, int) else 0)
    limit = min(RETRY_LIMIT_CEILING, max(RETRY_LIMIT_FLOOR, had * RETRY_LIMIT_FACTOR))
    return limit if limit > (body.get("max_tokens") or body.get("max_completion_tokens") or 0) else None


def dispatch(*, plan, runs: LlmRuns | None, stage: str, model: str, fingerprint: str, url: str, body: dict, headers: dict | Callable[[], dict],
             timeout: float, input_set_hash: str | None = None, on_response: Callable[[str, dict], None] | None = None,
             before_send: Callable[[str, dict], None] | None = None, context: dict | None = None) -> dict:
    """Reserve a planned call, send it with the privacy routing, save and settle the response; returns the parsed body.

    `headers` may be a function, called after the plan has accepted the call: a missing credential is then a failed call
    that is settled, never a reason to skip the plan check."""
    context = context or {}
    details = {"prefix_hash": prefix_hash(body), **{k: v for k, v in context.items()
                                                    if k not in ("prompt_version", "knowledge_base_version")}}
    prompt_version, kb_version = context.get("prompt_version"), context.get("knowledge_base_version")
    try:
        ticket = plan.reserve(stage=stage, model=model, fingerprint=fingerprint, input_set_hash=input_set_hash,
                              worst_case_usd=worst_case_usd(model, body))
    except RunPlanError as exc:
        if runs is not None:
            runs.record(stage=stage, model=model, fingerprint=fingerprint, status="refused", error=str(exc)[:500],
                        prompt_version=prompt_version, knowledge_base_version=kb_version,
                        details={"refused_by": "run_plan", **details})
        raise
    response = None
    try:
        response = send(url, body, headers() if callable(headers) else headers, timeout=timeout, before_send=before_send)
        raw = received(response, fingerprint, on_response, body)
    except (Exception, SystemExit) as exc:
        # SystemExit too: a harness's credential lookup exits, and the reserved call must still be settled (E.B1).
        try:
            saved = response.json() if response is not None else None
        except ValueError:
            saved = None
        error = f"{type(exc).__name__}: {exc}"
        if saved is None and isinstance(exc, ANSWER_LOST) and (charge := lost_answer_charge(model, body)):
            saved, error = charge, f"{error} (the answer was lost after the request was sent: counted at its worst case)"
        plan.settle(ticket, saved, status="refused" if isinstance(exc, RoutingError) else "failed", error=error[:500])
        _annotate(plan, runs, ticket, prompt_version, kb_version, details)
        raise
    plan.settle(ticket, raw, status="succeeded")
    usage = usage_of(raw)
    finish = _choice(raw).get("finish_reason")
    details = {**details, **{k: usage[k] for k in ("cached_tokens", "cache_write_tokens") if usage[k] is not None},
               **({"generation_id": usage["generation_id"]} if usage["generation_id"] else {}),
               **({"finish_reason": finish} if finish not in (None, "stop") else {}),
               **({"empty_content": True} if "messages" in body and has_no_content(raw) else {})}
    _annotate(plan, runs, ticket, prompt_version, kb_version, details)
    return raw


def dispatch_retrying_empty(*, fingerprint: str, body: dict, context: dict | None = None, structured: bool = False,
                            **rest) -> tuple[dict, dict | None]:
    """`dispatch`, and when the answer has no content at its length limit (or, `structured`, is cut off there), once more
    with a raised limit.

    Both calls are planned calls: each reserves against the run plan (the retry at its own, larger worst case), is sent
    with the privacy routing, and has its own `llm_runs` row; the first row says `empty_content` and its `finish_reason`,
    the second `retry_of` the first's fingerprint and the raised limit. Returns the last answer and, when a retry was
    made, what the first one cost, so no spend is hidden. A retry the plan refuses raises RunPlanError, saying why it was
    asked. An answer that still has no content is returned as it is; the caller treats it as incomplete."""
    raw = dispatch(fingerprint=fingerprint, body=body, context=context, **rest)
    if not cut_off(raw, structured=structured) or (limit := raised_output_limit(body, raw)) is None:
        return raw, None
    reason = "no content at the length limit" if has_no_content(raw) else "cut off at the length limit"
    said = "returned no content at its length limit" if has_no_content(raw) else "was cut off at its length limit"
    first = {"fingerprint": fingerprint, "max_tokens": body.get("max_tokens"), "usage": raw.get("usage"),
             "finish_reason": "length"}
    # The caller keeps the answer to the call it made: the retry's response is received under the first call's fingerprint.
    saved = rest.get("on_response")
    again_rest = {**rest, "on_response": (lambda _, answer: saved(fingerprint, answer)) if saved else None}
    try:
        again = dispatch(fingerprint=retry_fingerprint(fingerprint, limit), body={**body, "max_tokens": limit},
                         context={**(context or {}), "retry_of": fingerprint, "raised_max_tokens": limit,
                                  "retry_reason": reason}, **again_rest)
    except RunPlanError as refused:
        raise RunPlanError(f"{refused} (this was the one retry of a call that {said})") from refused
    return again, {**first, "raised_max_tokens": limit}


def _annotate(plan, runs, ticket, prompt_version, kb_version, details) -> None:
    """Complete the call's record: its llm_runs row, or, for a file plan, its line in the plan's ledger."""
    if runs is not None:
        runs.annotate(ticket.call_id, prompt_version=prompt_version, knowledge_base_version=kb_version, details=details)
    elif hasattr(plan, "annotate") and (prompt_version or kb_version):
        plan.annotate(ticket.call_id, prompt_version=prompt_version, knowledge_base_version=kb_version, details=details)
