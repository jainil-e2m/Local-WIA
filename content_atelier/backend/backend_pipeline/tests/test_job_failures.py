"""M1 exit (offline): a failed job's stored error says a provider's refusal in words first (R50), with the technical detail
after it for the team; any other error is stored as it was raised."""
from __future__ import annotations

import httpx

from backend_pipeline.jobs import recover
from backend_pipeline.llm import failures
from backend_pipeline.llm.routing import RoutingError


def refused(code: int) -> httpx.HTTPStatusError:
    request = httpx.Request("POST", "https://llm.example.invalid/api/v1/chat/completions")
    return httpx.HTTPStatusError(f"Client error '{code}'", request=request, response=httpx.Response(code, request=request))


def test_a_provider_out_of_credit_is_said_in_words_first_and_the_detail_follows():
    stored = failures.message(refused(402))
    reason, detail = stored.split("\n", 1)
    assert reason == failures.OUT_OF_CREDIT and "out of credit" in reason
    assert detail == "HTTPStatusError: Client error '402'", "the team still reads what the provider answered"


def test_a_wrapped_refusal_is_found_and_other_refusals_have_their_own_words():
    try:
        try:
            raise refused(402)
        except httpx.HTTPStatusError as error:
            raise ValueError("Brief writing failed") from error
    except ValueError as wrapped:
        assert failures.plain(wrapped) == failures.OUT_OF_CREDIT
    assert "did not accept the server's key" in failures.plain(refused(401))
    assert "limiting requests" in failures.plain(refused(429))
    assert "(error 503)" in failures.plain(refused(503))
    assert "privacy rules" in failures.plain(RoutingError("no endpoint"))
    assert "could not be reached" in failures.plain(httpx.ConnectError("refused"))


# OpenRouter's answer to a key past its own spending limit, as received on the internal key on 23 October (the key's link
# removed). It is 403, not 402, so before N1 it read as a key the provider did not accept.
KEY_LIMIT_BODY = {"error": {"message": "Key limit exceeded (weekly limit). Manage it using https://openrouter.ai/settings/keys "
                                       "$5.08 of $5.00 used; resets 2026-10-26T00:00:00.000Z.", "code": 403,
                            "metadata": {"limit_source": "openrouter_key_limit"}}}


def test_a_key_past_its_spending_limit_is_said_as_such_not_as_a_key_refused():
    request = httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions")
    limit = httpx.HTTPStatusError("Client error '403 Forbidden'", request=request,
                                  response=httpx.Response(403, json=KEY_LIMIT_BODY, request=request))
    assert failures.plain(limit) == failures.KEY_LIMIT and "spending limit" in failures.KEY_LIMIT
    assert failures.message(limit).split(chr(10), 1)[0] == failures.KEY_LIMIT
    assert "did not accept the server's key" in failures.plain(refused(403)), "a plain 403 is still a key refused"
    from backend_pipeline.cycle.refresh import plain_reason
    assert "spending limit" in plain_reason(limit)


def test_an_upstream_failure_inside_a_200_answer_is_said_in_words_first():
    """OpenRouter can answer 200 with the provider's failure in the body (`Upstream error from Nvidia: Internal server error`,
    code 502, seen in the N1 shakedown); the job stored only the technical message."""
    from backend_pipeline.llm.transport import UpstreamError
    error = UpstreamError("Model call failed: the provider answered with an error (502): Upstream error from Nvidia")
    reason, detail = failures.message(error).split(chr(10), 1)
    assert reason == "The model provider failed to answer, so nothing was written. Retry this step later."
    assert "Upstream error from Nvidia" in detail


def test_an_answer_cut_off_twice_is_said_in_words_first():
    """Scene extraction of a long October call on the free model ran out of output twice (N1 shakedown); the job stored
    "Provider response was incomplete or refused (after one retry with a raised output limit)"."""
    from backend_pipeline.llm.providers import IncompleteResponse
    error = IncompleteResponse("Provider response was incomplete or refused (after one retry with a raised output limit)")
    reason, detail = failures.message(error).split(chr(10), 1)
    assert reason.startswith("The model's answer was cut off before it finished") and "after one retry" in detail


def test_a_call_past_its_time_allowed_is_said_as_such():
    """N1 shakedown: a call past models.request_timeout_seconds read "could not be reached"."""
    from backend_pipeline.cycle.refresh import plain_reason
    late = httpx.ReadTimeout("timed out", request=httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions"))
    assert failures.plain(late) == failures.TIMED_OUT and "could not be reached" not in failures.TIMED_OUT
    assert plain_reason(late).startswith("The model took longer to answer than the time allowed")
    assert "could not be reached" in failures.plain(httpx.ConnectError("refused")), "a refused connection is still unreachable"


def test_any_other_error_is_stored_as_it_was_raised():
    assert failures.plain(ValueError("Research awaits compatible chunk embeddings")) is None
    assert failures.message(ValueError("Research awaits compatible chunk embeddings")) == "Research awaits compatible chunk embeddings"


def test_a_job_its_worker_lost_says_why_it_is_not_run_again_and_how_to_retry_it():
    first = recover.STOPPED.format(why=", after it sent a model call whose answer was not saved").split("\n")[0]
    assert first.startswith("The worker stopped while this step was running") and first.endswith("Retry this step to run it again.")
