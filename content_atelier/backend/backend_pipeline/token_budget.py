"""Explicit public asset fetch; private request counting is strictly local.

The saved routes and tokenizer files live in an artifact store: a folder (the file runner, `--data-root`) or the store
the workers share (`--store`, plan 0.B7), which is where a live weekly call reads them before it is sent.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import httpx

from .config import PROJECT_ROOT
from .store import JsonStore

MODEL = "apodex/apodex-1.1-mini:free"
REPOSITORY = "apodex/Apodex-1.1-mini-NVFP4"
MANIFEST = "tokenizers/apodex/manifest.json"
LUNA_MODEL = "openai/gpt-6-luna"
LUNA_MANIFEST = "tokenizers/gpt6-luna/manifest.json"
SOL_MODEL = "openai/gpt-6.1-sol"
SOL_MANIFEST = "tokenizers/gpt6.1-sol/manifest.json"
SONNET_MODEL = "anthropic/claude-sonnet-5.5"
SONNET_MANIFEST = "tokenizers/claude-sonnet-5.5/manifest.json"
# Models budgeted with the conservative byte allowance (no public native tokenizer), with their manifests.
# Sol was added for the strategist profile (E.B16 p); the preflight refused it before. Sonnet 5.5 is the production card
# verifier (E.B10): its model pass is a weekly call on the compact payload too, and was refused until it had a profile
# (found by the M1 exit test, 23 October).
# The free-model shakedown's two models (plan 5.0c) are sized the same way, so their weekly calls take the paid models' path.
NEMOTRON_FREE_MODEL = "nvidia/nemotron-3.5-super-vl:free"
NEMOTRON_FREE_MANIFEST = "tokenizers/nemotron-3.5-super-vl-free/manifest.json"
DOTS_FREE_MODEL = "dots-studio/dots-3-note-preview:free"
DOTS_FREE_MANIFEST = "tokenizers/dots-3-note-preview-free/manifest.json"
# The byte allowance counts one token for every BYTES_PER_TOKEN bytes. One a byte refused WIA's first live week (2 November
# 2026): 816,111 bytes were counted against the 922,000-token prompt limit, and the provider counted 216,072 tokens for that
# request, 3.78 bytes a token. The next week was already larger by its Thursday (319 scenes against 291), so two a byte would
# have refused a week of about 600 scenes. Three still counts about a quarter more tokens than the provider measured, the 10%
# margin stays on top, and a refusal now starts at about 2.5 MB, near 660,000 real tokens against the 922,000 limit.
BYTES_PER_TOKEN = 3
BYTE_BUDGET_MODELS = {LUNA_MODEL: LUNA_MANIFEST, SOL_MODEL: SOL_MANIFEST, SONNET_MODEL: SONNET_MANIFEST,
                      NEMOTRON_FREE_MODEL: NEMOTRON_FREE_MANIFEST, DOTS_FREE_MODEL: DOTS_FREE_MANIFEST}


def _store(root) -> JsonStore:
    """A folder or a store: the preflight reads through the store's interface, so a bucket works as a folder does."""
    return root if isinstance(root, JsonStore) else JsonStore(root)


def cache_luna_route(root: Path) -> dict:
    """Public catalog only; no keys, transcript data or claimed native tokenizer."""
    return cache_byte_budget_route(root, LUNA_MODEL)


def cache_byte_budget_route(root: Path, model: str) -> dict:
    """Snapshot a model's public route for the byte-allowance preflight. Sends no private data."""
    if model not in BYTE_BUDGET_MODELS:
        raise ValueError(f"No byte-allowance profile for {model}")
    store = _store(root)
    with httpx.Client(timeout=90) as client:
        response = client.get(f"https://openrouter.ai/api/v1/models/{model}/endpoints")
        response.raise_for_status()
        catalog = response.json()
    if catalog["data"]["id"] != model:
        raise RuntimeError("Public route ID does not match the explicitly requested model")
    stamp = datetime.now(UTC).isoformat()
    # A model id may carry a variant (`:free`); a colon is not allowed in a Windows file name, so it goes in neither part.
    path = f"provider_catalog/{stamp.replace(':', '-')}-{model.split('/')[-1].replace(':', '-')}.json"
    store.write_json(path, catalog)
    manifest = {
        "model": model,
        "route_snapshot": path,
        "route_sha256": hashlib.sha256(store.read_bytes(path)).hexdigest(),
        "fetched_at_utc": stamp,
        "counting_note": "Conservative UTF-8 text-byte allowance, not exact native token counting. Hosted usage is authoritative.",
    }
    store.write_json(BYTE_BUDGET_MODELS[model], manifest, overwrite=True)
    return manifest


def luna_preflight(request: dict, root: Path) -> dict:
    """Budget conservatively without mislabelling another model's tokenizer."""
    return byte_budget_preflight(request, root, LUNA_MODEL)


def byte_budget_preflight(request: dict, root: Path, model: str) -> dict:
    """Conservative UTF-8 byte allowance against the model's saved public route (Luna, Sol, Sonnet 5.5)."""
    label = model.split("/")[-1]
    store = _store(root)
    if not store.exists(BYTE_BUDGET_MODELS[model]):
        raise RuntimeError(f"No saved public route for {model}, so a live weekly call to it is not sized and not sent. Cache it "
                           f"once: python -m backend_pipeline.token_budget --model {model} --store (DEPLOYMENT.md)")
    manifest = store.read_json(BYTE_BUDGET_MODELS[model])
    snapshot = store.read_bytes(manifest["route_snapshot"])
    if manifest["model"] != model or hashlib.sha256(snapshot).hexdigest() != manifest["route_sha256"]:
        raise RuntimeError(f"{label} public route snapshot identity/checksum mismatch")
    catalog = json.loads(snapshot.decode("utf-8"))["data"]
    if catalog["id"] != request["model"]:
        raise RuntimeError(f"{label} route/model mismatch")
    required = {"response_format", "max_tokens"}
    if request.get("reasoning"):
        required.add("reasoning")
    endpoints = [e for e in catalog["endpoints"] if required.issubset(e["supported_parameters"])]
    if not endpoints:
        raise RuntimeError(f"No advertised {label} endpoint supports the required request parameters")
    completion = request.get("max_tokens")
    if not isinstance(completion, int) or isinstance(completion, bool) or completion <= 0:
        raise RuntimeError("Compact live requests require an explicit positive completion reserve")
    if any(completion > e["max_completion_tokens"] for e in endpoints):
        raise RuntimeError("Completion reserve exceeds advertised endpoint output capacity")
    # Installed tiktoken cannot map this model. A generous byte-sized allowance
    # is an engineering ceiling for byte-level text segmentation, not measured
    # Luna tokens. Include separate provider framing margin; never cloud-count
    # private text or reuse Apodex/GPT-OSS counts under the Luna label.
    text_bytes = sum(len(m["content"].encode("utf-8")) for m in request["messages"])
    format_bytes = len(json.dumps(request["response_format"], ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
    input_allowance = -(-(text_bytes + format_bytes) // BYTES_PER_TOKEN)
    margin = max(4096, (input_allowance + 9) // 10)
    context = min(e["context_length"] for e in endpoints)
    prompt_limit = min(e.get("max_prompt_tokens") or e["context_length"] for e in endpoints)
    headroom = context - input_allowance - margin - completion
    return {
        "model": model,
        "counting_method": "conservative_utf8_byte_allowance_not_native_token_count",
        "bytes_per_token_allowance": BYTES_PER_TOKEN,
        "message_text_utf8_bytes": text_bytes,
        "response_format_utf8_bytes": format_bytes,
        "input_token_budget_allowance": input_allowance,
        "unmeasured_provider_margin_tokens": margin,
        "completion_reserved_tokens": completion,
        "context_reference_tokens": context,
        "prompt_limit_reference_tokens": prompt_limit,
        "headroom_tokens": headroom,
        "fits": headroom >= 0 and input_allowance + margin <= prompt_limit,
        "native_token_count_available": False,
        "counting_is_local": True,
        "hosted_usage_is_exact": False,
        "route_snapshot": manifest["route_snapshot"],
        "measured_at_utc": datetime.now(UTC).isoformat(),
    }


def cache_public_assets(root: Path) -> dict:
    store = _store(root)
    with httpx.Client(timeout=90, follow_redirects=True) as client:
        route = client.get(f"https://openrouter.ai/api/v1/models/{MODEL}/endpoints")
        route.raise_for_status()
        route_data = route.json()
        repository = client.get(f"https://huggingface.co/api/models/{REPOSITORY}")
        repository.raise_for_status()
        revision = repository.json()["sha"]
        files = {}
        for name in ("tokenizer.json", "tokenizer_config.json", "chat_template.jinja"):
            response = client.get(f"https://huggingface.co/{REPOSITORY}/resolve/{revision}/{name}")
            response.raise_for_status()
            relative = f"tokenizers/apodex/{revision}/{name}"
            store.write_bytes(relative, response.content)
            files[name] = {"path": relative, "sha256": hashlib.sha256(response.content).hexdigest()}
    stamp = datetime.now(UTC).isoformat()
    route_path = f"provider_catalog/{stamp.replace(':', '-')}-apodex.json"
    store.write_json(route_path, route_data)
    manifest = {
        "model": MODEL,
        "repository": REPOSITORY,
        "revision": revision,
        "files": files,
        "route_snapshot": route_path,
        "fetched_at_utc": stamp,
        "counting_note": "Published Apodex tokenizer; served BF16 template/framing may differ. Not provider billing.",
    }
    store.write_json(MANIFEST, manifest, overwrite=True)
    return manifest


def preflight(request: dict, root: Path) -> dict:
    if request["model"] in BYTE_BUDGET_MODELS:
        return byte_budget_preflight(request, root, request["model"])
    from tokenizers import Tokenizer

    if request["model"] != MODEL:
        raise RuntimeError(f"No verified compact live token profile for {request['model']}; refusing a request. A model "
                           "is sized by its saved public route only once it is listed in token_budget.BYTE_BUDGET_MODELS")
    store = _store(root)
    manifest = store.read_json(MANIFEST)
    file = manifest["files"]["tokenizer.json"]
    vocabulary = store.read_bytes(file["path"])
    if hashlib.sha256(vocabulary).hexdigest() != file["sha256"]:
        raise RuntimeError("Apodex tokenizer checksum mismatch")
    tokenizer = Tokenizer.from_str(vocabulary.decode("utf-8"))

    def count(text):
        return len(tokenizer.encode(text, add_special_tokens=False).ids)

    route = store.read_json(manifest["route_snapshot"])["data"]
    endpoints = [
        e
        for e in route["endpoints"]
        if e["pricing"]["prompt"] == "0"
        and e["pricing"]["completion"] == "0"
        and {"response_format", "max_tokens"}.issubset(e["supported_parameters"])
    ]
    if not endpoints:
        raise RuntimeError("No advertised free JSON-output endpoint in the saved route snapshot")
    completion = request.get("max_tokens")
    if not isinstance(completion, int) or isinstance(completion, bool) or completion <= 0:
        raise RuntimeError("Compact live requests require an explicit positive completion reserve")
    context = min(e["context_length"] for e in endpoints)
    if any(completion > e["max_completion_tokens"] for e in endpoints):
        raise RuntimeError("Completion reserve exceeds advertised endpoint output capacity")
    message_tokens = sum(count(m["content"]) for m in request["messages"])
    schema_tokens = count(json.dumps(request["response_format"], ensure_ascii=False, separators=(",", ":")))
    # Provider framing/schema injection is not public. Reserve both a minimum
    # and 10% of the proxy; never call these local counts exact hosted usage.
    margin = max(4096, (message_tokens + schema_tokens + 9) // 10)
    headroom = context - message_tokens - schema_tokens - margin - completion
    report = {
        "model": MODEL,
        "tokenizer_repository": REPOSITORY,
        "tokenizer_revision": manifest["revision"],
        "tokenizer_sha256": file["sha256"],
        "message_text_tokens": message_tokens,
        "schema_proxy_tokens": schema_tokens,
        "unmeasured_provider_margin_tokens": margin,
        "completion_reserved_tokens": completion,
        "context_reference_tokens": context,
        "headroom_tokens": headroom,
        "fits": headroom >= 0,
        "counting_is_local": True,
        "hosted_usage_is_exact": False,
        "route_snapshot": manifest["route_snapshot"],
        "measured_at_utc": datetime.now(UTC).isoformat(),
    }
    return report


def main():
    parser = argparse.ArgumentParser(description="Cache public model preflight assets; sends no private data")
    parser.add_argument("--data-root", type=Path, default=PROJECT_ROOT / "testing" / ".data")
    parser.add_argument("--store", action="store_true", help="Save into the artifact store the environment names "
                        "(ATELIER_ARTIFACT_STORE, ATELIER_ARTIFACT_ROOT): the store the workers read before a live call")
    parser.add_argument("--model", choices=[MODEL, *BYTE_BUDGET_MODELS], default=MODEL)
    args = parser.parse_args()
    root = args.data_root
    if args.store:
        from .artifacts import store_for
        from .storage_config import StorageSettings
        root = store_for(StorageSettings.from_env())
    result = (cache_byte_budget_route(root, args.model) if args.model in BYTE_BUDGET_MODELS
              else cache_public_assets(root))
    print(json.dumps({"model": args.model, "route_snapshot": result["route_snapshot"], "private_data_sent": False}, indent=2))


if __name__ == "__main__":
    main()
