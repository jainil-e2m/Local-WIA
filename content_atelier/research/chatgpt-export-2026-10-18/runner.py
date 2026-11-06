"""OpenRouter runner with a hard spend cap, thread-safe ledger and optional prompt caching.
Never prints the API key. Each call is saved under runs/<run_id>.json and skipped if it exists."""
import json, sys, time, hashlib, threading, pathlib

sys.stdout.reconfigure(encoding="utf-8")
ROOT = pathlib.Path(__file__).parent
# Every request leaves through the product's provider module, so it carries the
# recorded privacy routing (plan S.B1, V17) and fails closed when no endpoint complies.
sys.path.insert(0, str(ROOT.resolve().parents[1] / "backend"))
from backend_pipeline.provider import RoutingError, send, raise_for_routing  # noqa: E402
from backend_pipeline.llm.run_plans import from_environment  # noqa: E402


def _plan():
    """A paid call needs an active run plan (plan E.B1): ATELIER_RUN_PLAN_FILE, or run_plan.json beside the results."""
    return from_environment(default_file=ROOT / "run_plan.json")
LEDGER = ROOT / "ledger.jsonl"
CAP_USD = 3.70
ENV = pathlib.Path(__file__).resolve().parents[2] / "backend" / ".env"
_LOCK = threading.Lock()


def _key():
    for line in ENV.read_text(encoding="utf-8").splitlines():
        if line.startswith("OPENROUTER_API_KEY="):
            k = line.split("=", 1)[1].strip().strip('"').strip("'")
            if k:
                return k
    raise SystemExit("OPENROUTER_API_KEY missing")


def spent():
    if not LEDGER.exists():
        return 0.0
    return sum(json.loads(l).get("cost", 0) or 0 for l in LEDGER.read_text(encoding="utf-8").splitlines() if l.strip())


def call(run_id, model, system, user, schema=None, schema_name="out", effort=None, max_tokens=8000,
         estimate_usd=0.05, cache_prefix=None, temperature=None):
    """cache_prefix: optional long stable text placed before `system` with an Anthropic cache marker."""
    out = ROOT / "runs" / f"{run_id}.json"
    if out.exists():
        return json.loads(out.read_text(encoding="utf-8"))
    with _LOCK:
        if spent() + estimate_usd > CAP_USD:
            raise RuntimeError(f"Refusing {run_id}: spent {spent():.3f} + estimate {estimate_usd} > cap {CAP_USD}")
    if cache_prefix:
        sys_content = [{"type": "text", "text": cache_prefix, "cache_control": {"type": "ephemeral"}},
                       {"type": "text", "text": system}]
    else:
        sys_content = system
    body = {"model": model, "messages": [{"role": "system", "content": sys_content}, {"role": "user", "content": user}],
            "max_tokens": max_tokens, "usage": {"include": True},
            # Export text is client material; send() adds the recorded routing (deny collection, ZDR).
            "provider": {"allow_fallbacks": True}}
    if effort:
        body["reasoning"] = {"effort": effort}
    if temperature is not None:
        body["temperature"] = temperature
    if schema == "json_object":
        body["response_format"] = {"type": "json_object"}
    elif schema is not None:
        body["response_format"] = {"type": "json_schema", "json_schema": {"name": schema_name, "strict": True, "schema": schema}}
    headers = {"Authorization": "Bearer " + _key(), "Content-Type": "application/json",
               "X-Title": "Content Atelier export investigation"}
    t0 = time.time()
    raw = None
    plan = _plan()
    for attempt in range(3):
        # Every attempt is a paid call, so each one reserves against the plan.
        ticket = plan.reserve(stage="evaluation", model=model, fingerprint=run_id)
        try:
            response = send("https://openrouter.ai/api/v1/chat/completions", body, headers, timeout=600)
        except RoutingError:
            plan.settle(ticket, None, status="refused")
            raise
        except Exception as exc:  # network
            plan.settle(ticket, None, status="failed", error=str(exc)[:500])
            if attempt < 2:
                time.sleep(5)
                continue
            raise
        if response.status_code >= 400:
            err = response.text[:1500]
            plan.settle(ticket, None, status="failed", error=err[:500])
            if response.status_code in (429, 500, 502, 503) and attempt < 2:
                time.sleep(5 * (attempt + 1))
                continue
            with _LOCK:
                LEDGER.open("a", encoding="utf-8").write(json.dumps({"run_id": run_id, "model": model, "error": err, "cost": 0}) + "\n")
            raise_for_routing(response)
            raise RuntimeError(f"HTTP {response.status_code} on {run_id}: {err[:300]}")
        raw = response.json()
        plan.settle(ticket, raw, status="succeeded")
        break
    usage = raw.get("usage", {})
    cost = usage.get("cost") or 0
    content = raw["choices"][0]["message"].get("content") or ""
    try:
        parsed = json.loads(content)
    except Exception:
        parsed = None
    rec = {"run_id": run_id, "model": model, "provider": raw.get("provider"), "effort": effort,
           "prompt_tokens": usage.get("prompt_tokens"), "completion_tokens": usage.get("completion_tokens"),
           "cached_tokens": (usage.get("prompt_tokens_details") or {}).get("cached_tokens"),
           "cost": cost, "seconds": round(time.time() - t0, 1), "finish": raw["choices"][0].get("finish_reason"),
           "system_sha": hashlib.sha256((cache_prefix or "").encode() + system.encode()).hexdigest()[:12],
           "user_sha": hashlib.sha256(user.encode()).hexdigest()[:12]}
    with _LOCK:
        LEDGER.open("a", encoding="utf-8").write(json.dumps(rec) + "\n")
    out.write_text(json.dumps({"meta": rec, "output": parsed, "content": content if parsed is None else None,
                               "request": {"system": system, "user": user, "cache_prefix_sha": rec["system_sha"]}},
                              ensure_ascii=False, indent=1), encoding="utf-8")
    return json.loads(out.read_text(encoding="utf-8"))
