"""Explicit public asset fetch; private request counting is strictly local."""

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


def cache_luna_route(root: Path) -> dict:
    """Public catalog only; no keys, transcript data or claimed native tokenizer."""
    store = JsonStore(root)
    with httpx.Client(timeout=90) as client:
        response = client.get(f"https://openrouter.ai/api/v1/models/{LUNA_MODEL}/endpoints")
        response.raise_for_status()
        catalog = response.json()
    if catalog["data"]["id"] != LUNA_MODEL:
        raise RuntimeError("Public route ID does not match the explicitly requested model")
    stamp = datetime.now(UTC).isoformat()
    path = f"provider_catalog/{stamp.replace(':', '-')}-gpt6-luna.json"
    store.write_json(path, catalog)
    manifest = {
        "model": LUNA_MODEL,
        "route_snapshot": path,
        "route_sha256": hashlib.sha256(store.path(path).read_bytes()).hexdigest(),
        "fetched_at_utc": stamp,
        "counting_note": "Conservative UTF-8 text-byte allowance, not exact native token counting. Hosted usage is authoritative.",
    }
    store.write_json(LUNA_MANIFEST, manifest, overwrite=True)
    return manifest


def luna_preflight(request: dict, root: Path) -> dict:
    """Budget conservatively without mislabelling another model's tokenizer."""
    store = JsonStore(root)
    manifest = store.read_json(LUNA_MANIFEST)
    catalog_path = store.path(manifest["route_snapshot"])
    if manifest["model"] != LUNA_MODEL or hashlib.sha256(catalog_path.read_bytes()).hexdigest() != manifest["route_sha256"]:
        raise RuntimeError("Luna public route snapshot identity/checksum mismatch")
    catalog = store.read_json(manifest["route_snapshot"])["data"]
    if catalog["id"] != request["model"]:
        raise RuntimeError("Luna route/model mismatch")
    required = {"response_format", "max_tokens"}
    if request.get("reasoning"):
        required.add("reasoning")
    endpoints = [e for e in catalog["endpoints"] if required.issubset(e["supported_parameters"])]
    if not endpoints:
        raise RuntimeError("No advertised Luna endpoint supports the required request parameters")
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
    input_allowance = text_bytes + format_bytes
    margin = max(4096, (input_allowance + 9) // 10)
    context = min(e["context_length"] for e in endpoints)
    prompt_limit = min(e.get("max_prompt_tokens") or e["context_length"] for e in endpoints)
    headroom = context - input_allowance - margin - completion
    return {
        "model": LUNA_MODEL,
        "counting_method": "conservative_utf8_byte_allowance_not_native_token_count",
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
    store = JsonStore(root)
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
    if request["model"] == LUNA_MODEL:
        return luna_preflight(request, root)
    from tokenizers import Tokenizer

    if request["model"] != MODEL:
        raise RuntimeError("No verified compact live token profile for this model; refusing a request")
    store = JsonStore(root)
    manifest = store.read_json(MANIFEST)
    file = manifest["files"]["tokenizer.json"]
    vocabulary = store.path(file["path"])
    if hashlib.sha256(vocabulary.read_bytes()).hexdigest() != file["sha256"]:
        raise RuntimeError("Apodex tokenizer checksum mismatch")
    tokenizer = Tokenizer.from_file(str(vocabulary))

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
    parser.add_argument("--model", choices=[MODEL, LUNA_MODEL], default=MODEL)
    args = parser.parse_args()
    result = cache_luna_route(args.data_root) if args.model == LUNA_MODEL else cache_public_assets(args.data_root)
    print(json.dumps({"model": args.model, "route_snapshot": result["route_snapshot"], "private_data_sent": False}, indent=2))


if __name__ == "__main__":
    main()
