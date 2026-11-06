"""S.B1: every chat and embedding request carries the recorded privacy routing and fails closed.

Mock transports only; the conftest guard forbids real outbound HTTP.
"""
from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

import httpx
import pytest

from backend_pipeline.llm import routing as routing_module
from backend_pipeline.tests.plans import OpenTestPlan
from backend_pipeline.llm import (
    ROUTING_POLICY, ROUTING_PREFERENCES, LiveProvider, RoutingError, chat_body, embedding_body, route,
)

BACKEND = Path(__file__).resolve().parents[2]
PROJECT = BACKEND.parent
HARNESS_RUNNERS = [PROJECT / "research" / "quality-experiments-2026-10-18" / "runner.py",
                   PROJECT / "research" / "chatgpt-export-2026-10-18" / "runner.py"]


class Capture:
    """Records each request body and answers like OpenRouter would."""

    def __init__(self, status=200):
        self.bodies: list[dict] = []
        self.urls: list[str] = []
        self.status = status

    def __call__(self, transport, request):
        body = json.loads(request.content)
        self.bodies.append(body)
        self.urls.append(str(request.url))
        if self.status == 404:
            return httpx.Response(404, json={"error": {"message": "No endpoints found matching your data policy"}},
                                  request=request)
        if str(request.url).endswith("/embeddings"):
            inputs = body["input"] if isinstance(body["input"], list) else [body["input"]]
            data = [{"index": i, "embedding": [1.0] + [0.0] * 1535} for i, _ in enumerate(inputs)]
            return httpx.Response(200, json={"data": data, "model": body["model"]}, request=request)
        return httpx.Response(200, json={"choices": [{"finish_reason": "stop", "message": {"content": "{\"ok\": true}"}}],
                                         "usage": {"cost": 0.0}}, request=request)


@pytest.fixture
def capture(monkeypatch):
    c = Capture()
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", lambda transport, request: c(transport, request))
    return c


def live(**kwargs):
    return LiveProvider(llm_base_url="https://openrouter.ai/api/v1", moments_model="openai/gpt-6-luna", moments_key="k",
                        angles_model="openai/gpt-6.1-sol", angles_key="k", embedding_base_url="https://openrouter.ai/api/v1",
                        embedding_model="openai/text-embedding-3-small", embedding_key="k", dimensions=1536, timeout=5,
                        plan=kwargs.pop("plan", OpenTestPlan()), **kwargs)


def assert_routed(body):
    for key, value in ROUTING_PREFERENCES.items():
        assert body["provider"][key] == value


def test_route_adds_preferences_and_keeps_existing_ones():
    body = chat_body(model="openai/gpt-6.1-sol", system="s", user="u", schema={"type": "object"})
    routed = route(body)
    assert_routed(routed)
    assert routed["provider"]["require_parameters"] is True and routed["provider"]["allow_fallbacks"] is False
    assert "zdr" not in body["provider"], "route() must not mutate the fingerprinted request"


@pytest.mark.parametrize("override", [{"data_collection": "allow"}, {"zdr": False}])
def test_route_refuses_a_request_that_weakens_the_position(override):
    with pytest.raises(RoutingError):
        route({"model": "m", "provider": override})


@pytest.mark.parametrize("stage", ["moment_extraction", "angle_generation", "brief_write", "brief_review"])
def test_every_chat_stage_sends_the_preferences(capture, stage):
    output, meta = live().json_call(stage=stage, system="s", user="u", schema={"type": "object"}, fingerprint="f")
    assert output == {"ok": True}
    assert_routed(capture.bodies[-1])
    assert meta["routing"] == {"policy": ROUTING_POLICY, "preferences": ROUTING_PREFERENCES}


def test_single_and_batch_embeddings_send_the_preferences(capture):
    vector, meta = live().embed(text="a", fingerprint="f")
    assert len(vector) == 1536 and meta["routing"]["policy"] == ROUTING_POLICY
    live().embed_many(texts=["a", "b"], fingerprint="g")
    assert [u.rsplit("/", 1)[1] for u in capture.urls] == ["embeddings", "embeddings"]
    for body in capture.bodies:
        assert_routed(body)
        assert {k: body[k] for k in ("model", "dimensions", "encoding_format")} == {
            k: embedding_body(model="openai/text-embedding-3-small", text="a", dimensions=1536)[k]
            for k in ("model", "dimensions", "encoding_format")}


def test_no_compliant_endpoint_fails_closed_without_a_second_request(monkeypatch):
    refused = Capture(status=404)
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", lambda transport, request: refused(transport, request))
    saved = []
    with pytest.raises(RoutingError):
        live(on_response=lambda fp, raw: saved.append(raw)).json_call(
            stage="angle_generation", system="s", user="u", schema={"type": "object"}, fingerprint="f")
    assert len(refused.bodies) == 1, "a refused request is never retried without the preferences"
    assert saved and "error" in saved[0], "the refusal is saved before it is raised"
    with pytest.raises(RoutingError):
        live().embed(text="a", fingerprint="f")


def test_before_send_sees_the_routed_body(capture):
    seen = []
    live(before_send=lambda url, body: seen.append((url, body))).json_call(
        stage="angle_generation", system="s", user="u", schema={"type": "object"}, fingerprint="f")
    assert seen[0][0].endswith("/chat/completions")
    assert_routed(seen[0][1])


def load_runner(path, tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location(f"runner_{path.parent.name.replace('-', '_')}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "LEDGER", tmp_path / "ledger.jsonl")
    monkeypatch.setattr(module, "_key", lambda: "test-key")
    (tmp_path / "runs").mkdir()
    from backend_pipeline.tests.plans import file_plan
    file_plan(tmp_path, monkeypatch, stages=["evaluation"], models=["openai/gpt-6.1-sol"])
    return module


@pytest.mark.parametrize("path", HARNESS_RUNNERS, ids=lambda p: p.parent.name)
def test_both_experiment_harnesses_dispatch_through_the_provider_module(capture, tmp_path, monkeypatch, path):
    runner = load_runner(path, tmp_path, monkeypatch)
    runner.call("routing-check", "openai/gpt-6.1-sol", "system", "user", schema="json_object", estimate_usd=0)
    assert len(capture.bodies) == 1
    assert_routed(capture.bodies[0])


@pytest.mark.parametrize("path", HARNESS_RUNNERS, ids=lambda p: p.parent.name)
def test_harness_refusal_is_a_routing_error(monkeypatch, tmp_path, path):
    refused = Capture(status=404)
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", lambda transport, request: refused(transport, request))
    runner = load_runner(path, tmp_path, monkeypatch)
    with pytest.raises(RoutingError):
        runner.call("routing-refused", "openai/gpt-6.1-sol", "system", "user", schema="json_object", estimate_usd=0)
    assert len(refused.bodies) == 1


def test_only_the_llm_module_posts_to_model_endpoints():
    """Every call site goes through llm.routing.send(); a new direct post would bypass the routing. The evaluation
    harness is scanned too, and a post to a URL held in a variable counts, in any file that names a model endpoint."""
    sources = [p for p in (BACKEND / "backend_pipeline").rglob("*.py") if "tests" not in p.parts]
    sources += list((BACKEND / "scripts").glob("*.py")) + list((BACKEND / "experiments").glob("*.py"))
    sources += list((BACKEND / "evaluation").rglob("*.py")) + list((PROJECT / "research").rglob("*.py"))
    direct = re.compile(r"urlopen\(|requests\.post\(|httpx\.post\(|\.post\(\s*f?['\"][^'\"]*(chat/completions|/embeddings)")
    endpoint = re.compile(r"chat/completions|/embeddings|openrouter\.ai|api\.openai\.com")
    posts = re.compile(r"\.post\(|\.request\(\s*['\"]POST|method\s*=\s*['\"]POST|\.stream\(\s*['\"]POST")

    def bypasses(text):
        return bool(direct.search(text) or endpoint.search(text) and posts.search(text))
    offenders = [str(p.relative_to(PROJECT)) for p in sources
                 if p.resolve() != Path(routing_module.__file__).resolve() and bypasses(p.read_text(encoding="utf-8"))]
    assert offenders == []
    assert bypasses('client.post(url, json=body)  # https://openrouter.ai/api/v1/chat/completions'), "a variable URL counts"


def test_the_evaluation_harness_sends_the_routing_preferences(monkeypatch, tmp_path):
    """E.B3's harness reaches the model through provider.send(), with S.B1's routing on its body."""
    from evaluation import run as harness
    capture = Capture()
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", lambda transport, request: capture(transport, request))
    monkeypatch.setattr(harness, "OUT", tmp_path)
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

    class Plan:
        def reserve(self, **kw):
            return "ticket"

        def settle(self, *a, **k):
            pass
    monkeypatch.setattr(harness, "from_environment", lambda default_file=None: Plan())
    harness.generate("default", "week1", 1)
    assert len(capture.bodies) == 1 and capture.urls[0].endswith("/chat/completions")
    assert_routed(capture.bodies[0])


# ---- free models (plan 5.0c, the free-model shakedown; D41) -------------------------------------------------------------

FREE = "nvidia/nemotron-3.5-super-vl:free"


def answering(*statuses):
    """A client whose transport answers each request with the next status (the last one repeats), recording the bodies."""
    seen, queue = [], list(statuses)

    def handler(request):
        seen.append(json.loads(request.content))
        status = queue.pop(0) if len(queue) > 1 else queue[0]
        if status == 200:
            return httpx.Response(200, json={"choices": [{"finish_reason": "stop", "message": {"content": "{}"}}]})
        if status == 504:  # what OpenRouter sends when a free endpoint idles out: HTTP 200 with the upstream's 504 inside
            return httpx.Response(200, json={"error": {"message": "Upstream idle timeout exceeded", "code": 504}})
        return httpx.Response(status, json={"error": {"message": "rate limited"}})
    return httpx.Client(transport=httpx.MockTransport(handler)), seen


def test_a_paid_request_is_sent_exactly_as_before_and_a_free_one_only_without_the_two_preferences():
    paid = chat_body(model="openai/gpt-6.1-sol", system="s", user="u", schema={"type": "object"}, max_tokens=10)
    assert route(paid)["provider"] == {"require_parameters": True, "allow_fallbacks": False, **ROUTING_PREFERENCES}
    free = chat_body(model=FREE, system="s", user="u", schema={"type": "object"}, max_tokens=10)
    routed = route(free)
    assert routed["provider"] == {"require_parameters": True, "allow_fallbacks": False}, "every free endpoint may collect prompts"
    assert {k: v for k, v in routed.items() if k != "provider"} == {k: v for k, v in free.items() if k != "provider"}
    # A model id merely containing the word is not free; only the suffix is.
    assert route({"model": "free/model", "messages": []})["provider"] == ROUTING_PREFERENCES
    assert routing_module.policy_for(FREE) == routing_module.FREE_POLICY != ROUTING_POLICY
    assert routing_module.policy_for("openai/gpt-6.1-sol") == ROUTING_POLICY
    assert routing_module.routing_record(FREE)["policy"] == routing_module.FREE_POLICY
    assert routing_module.routing_record("openai/gpt-6.1-sol") == routing_module.routing_record()


def test_a_free_request_goes_without_the_not_blank_pattern_and_a_paid_one_keeps_it():
    r"""The free endpoints' grammar engines misread contracts.Text's unanchored r"\S": matched whole it let them write one
    character per field ("m" for "m1.t0001"), and rewritten to match whole it sent one into a loop of closing quotes (N1
    shakedown). OpenAI's route reads it as JSON Schema says (a saved Luna answer has whole span ids). A free request goes
    without it (minLength stays; the local validator still refuses a blank string); a paid request is sent unchanged, and
    the request fingerprint never sees the change."""
    from pydantic import BaseModel

    from backend_pipeline.contracts import Text

    class Coverage(BaseModel):
        meeting_ref: Text
        notes: list[Text]
    schema = Coverage.model_json_schema()

    def patterns(node):
        if isinstance(node, dict):
            return [v for k, v in node.items() if k == "pattern"] + [p for v in node.values() for p in patterns(v)]
        return [p for v in node for p in patterns(v)] if isinstance(node, list) else []
    free = route(chat_body(model=FREE, system="s", user="u", schema=schema, max_tokens=10))
    assert patterns(free["response_format"]) == [] and '"minLength": 1' in json.dumps(free["response_format"])
    assert set(patterns(schema)) == {r"\S"}, "the schema itself, and so the fingerprint, is unchanged"
    paid = chat_body(model="openai/gpt-6-luna", system="s", user="u", schema=schema, max_tokens=10)
    assert route(paid)["response_format"] == paid["response_format"], "a paid request's schema is untouched"


def test_a_free_request_asks_for_no_reasoning_and_a_paid_one_keeps_its_own():
    free = chat_body(model=FREE, system="s", user="u", schema={"type": "object"}, max_tokens=10, reasoning_effort="high")
    assert route(free)["reasoning"] == {"enabled": False} and free["reasoning"] == {"effort": "high"}
    paid = chat_body(model="openai/gpt-6.1-sol", system="s", user="u", schema={"type": "object"}, max_tokens=10, reasoning_effort="high")
    assert route(paid)["reasoning"] == {"effort": "high"}


def test_only_a_free_model_waits_out_a_rate_limit(monkeypatch):
    slept = []
    monkeypatch.setattr(routing_module.time, "sleep", slept.append)
    client, seen = answering(429, 429, 200)
    response = routing_module.send("https://openrouter.ai/api/v1/chat/completions", {"model": FREE, "messages": []}, {},
                                   timeout=5, client=client)
    assert response.status_code == 200 and len(seen) == 3 and slept == [10, 20]
    client, seen = answering(429, 200)
    response = routing_module.send("https://openrouter.ai/api/v1/chat/completions", {"model": "openai/gpt-6.1-sol", "messages": []},
                                   {}, timeout=5, client=client)
    assert response.status_code == 429 and len(seen) == 1, "a paid request is never repeated by the dispatch"
    assert seen[0]["provider"] == ROUTING_PREFERENCES
    client, seen = answering(504, 200)
    response = routing_module.send("https://openrouter.ai/api/v1/chat/completions", {"model": FREE, "messages": []}, {},
                                   timeout=5, client=client)
    assert response.status_code == 200 and len(seen) == 2, "an upstream 504 inside a 200 answer is waited out too"
    client, seen = answering(504, 200)
    response = routing_module.send("https://openrouter.ai/api/v1/chat/completions", {"model": "openai/gpt-6.1-sol", "messages": []},
                                   {}, timeout=5, client=client)
    assert len(seen) == 1, "never for a paid request"
    client, seen = answering(502, 503, 200)
    response = routing_module.send("https://openrouter.ai/api/v1/chat/completions", {"model": FREE, "messages": []}, {},
                                   timeout=5, client=client)
    assert response.status_code == 200 and len(seen) == 3, "a free endpoint's passing failure is waited out"
    client, seen = answering(502, 200)
    response = routing_module.send("https://openrouter.ai/api/v1/chat/completions", {"model": "openai/gpt-6.1-sol", "messages": []},
                                   {}, timeout=5, client=client)
    assert response.status_code == 502 and len(seen) == 1
    client, seen = answering(429)
    response = routing_module.send("https://openrouter.ai/api/v1/chat/completions", {"model": FREE, "messages": []}, {},
                                   timeout=5, client=client)
    assert response.status_code == 429 and len(seen) == 1 + len(routing_module.FREE_RATE_LIMIT_WAITS), "the waits are bounded"


def test_no_configuration_of_record_names_a_free_model():
    for name in ("production-settings.json",):
        settings = json.loads((BACKEND / "deploy" / name).read_text(encoding="utf-8"))["settings"]
        assert not [k for k, v in settings.items() if routing_module.is_free(v)], name
