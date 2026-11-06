"""Minimal OpenRouter runner with a hard spend cap. Never prints the API key."""
import json, os, sys, time, hashlib, pathlib
sys.stdout.reconfigure(encoding="utf-8")
ROOT = pathlib.Path(__file__).parent
# Every request leaves through the product's provider module, so it carries the
# recorded privacy routing (plan S.B1, V17) and fails closed when no endpoint complies.
sys.path.insert(0, str(ROOT.resolve().parents[1] / "backend"))
from backend_pipeline.provider import send, raise_for_routing  # noqa: E402
from backend_pipeline.llm.run_plans import from_environment  # noqa: E402

def _plan():
    """A paid call needs an active run plan (plan E.B1): ATELIER_RUN_PLAN_FILE, or run_plan.json beside the results."""
    return from_environment(default_file=ROOT / "run_plan.json")
LEDGER = ROOT / "ledger.jsonl"
CAP_USD = 3.70
ENV = pathlib.Path(__file__).resolve().parents[2] / "backend" / ".env"

def _key():
    for line in ENV.read_text(encoding="utf-8").splitlines():
        if line.startswith("OPENROUTER_API_KEY="):
            k = line.split("=", 1)[1].strip().strip('"').strip("'")
            if k: return k
    raise SystemExit("OPENROUTER_API_KEY missing")

def spent():
    if not LEDGER.exists(): return 0.0
    return sum(json.loads(l).get("cost", 0) or 0 for l in LEDGER.read_text(encoding="utf-8").splitlines() if l.strip())

def call(run_id, model, system, user, schema=None, schema_name="out", effort="high", max_tokens=32000, estimate_usd=0.5,
         cache_prefix=None):
    """cache_prefix: optional long stable text placed before `system` with an Anthropic cache marker."""
    out = ROOT / "runs" / f"{run_id}.json"
    if out.exists():
        print(f"[skip] {run_id} already exists"); return json.loads(out.read_text(encoding="utf-8"))
    if spent() + estimate_usd > CAP_USD:
        raise SystemExit(f"Refusing {run_id}: spent {spent():.3f} + estimate {estimate_usd} > cap {CAP_USD}")
    sys_content = ([{"type": "text", "text": cache_prefix, "cache_control": {"type": "ephemeral"}},
                    {"type": "text", "text": system}] if cache_prefix else system)
    body = {"model": model, "messages": [{"role": "system", "content": sys_content}, {"role": "user", "content": user}],
            "max_tokens": max_tokens, "usage": {"include": True}}
    if effort: body["reasoning"] = {"effort": effort}
    if schema == "json_object":
        body["response_format"] = {"type": "json_object"}
    elif schema is not None:
        body["response_format"] = {"type": "json_schema", "json_schema": {"name": schema_name, "strict": True, "schema": schema}}
    headers = {"Authorization": "Bearer " + _key(), "Content-Type": "application/json", "X-Title": "Content Atelier quality investigation"}
    t0 = time.time()
    plan = _plan()
    ticket = plan.reserve(stage="evaluation", model=model, fingerprint=run_id)
    response = send("https://openrouter.ai/api/v1/chat/completions", body, headers, timeout=900)
    if response.status_code >= 400:
        err = response.text[:2000]
        LEDGER.open("a", encoding="utf-8").write(json.dumps({"run_id": run_id, "model": model, "error": err, "cost": 0}) + "\n")
        plan.settle(ticket, None, status="failed", error=err[:500])
        raise_for_routing(response)
        raise SystemExit(f"HTTP {response.status_code}: {err}")
    raw = response.json()
    plan.settle(ticket, raw, status="succeeded")
    usage = raw.get("usage", {})
    cost = usage.get("cost") or 0
    content = raw["choices"][0]["message"].get("content") or ""
    try: parsed = json.loads(content)
    except Exception: parsed = None
    rec = {"run_id": run_id, "model": model, "provider": raw.get("provider"), "effort": effort,
           "prompt_tokens": usage.get("prompt_tokens"), "completion_tokens": usage.get("completion_tokens"),
           "reasoning_tokens": (usage.get("completion_tokens_details") or {}).get("reasoning_tokens"),
           "cost": cost, "seconds": round(time.time() - t0, 1), "finish": raw["choices"][0].get("finish_reason"),
           "system_sha": hashlib.sha256((cache_prefix or "").encode() + system.encode()).hexdigest()[:12], "user_sha": hashlib.sha256(user.encode()).hexdigest()[:12],
           "system_chars": len(system), "user_chars": len(user)}
    LEDGER.open("a", encoding="utf-8").write(json.dumps(rec) + "\n")
    out.write_text(json.dumps({"meta": rec, "output": parsed, "content": content if parsed is None else None,
                               "request": {"system": system, "user": user, "schema_name": schema_name,
                                           "cache_prefix_sha": hashlib.sha256((cache_prefix or "").encode()).hexdigest()[:12]}}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[done] {run_id} {model} cost=${cost:.4f} in={rec['prompt_tokens']} out={rec['completion_tokens']} finish={rec['finish']} total=${spent():.3f}")
    return json.loads(out.read_text(encoding="utf-8"))
