"""Replay check of saved stage artifacts (0.B4 on the real Week 1 and 2 artifacts).

A saved stage artifact replays when the module's recipe gives its recorded request the key it was saved under, the store's
replay lookup (`JsonStore.find_artifact`, what `StageCaller.call_json` reads before any provider call) serves it under that
key, and its output still has its recorded hash. This checks every cached artifact under an artifact root that way, from
the files alone: no provider is constructed, so no call can be made, and nothing is written.

A whole run cannot be rebuilt request for request when its prompt profile has been retired (the 8 October profiles are
archived, not selectable): the requests the product builds today differ, so they are new requests, not replays. Failed
attempts are listed separately; E.B12a re-checks their received responses (`moments import-saved --include-failed`).

    python -m backend_pipeline.llm.replay_check <artifact root> [--stage moment_extraction ...]
"""
from __future__ import annotations

import argparse
import json
import sys

from ..store import JsonStore, canonical_hash
from .request import VALIDATION_VERSION, stage_fingerprint, workflow_fingerprint

BRIEF_WORKFLOWS = ("approved_angle_brief_v1",)


def _endpoint(store: JsonStore, data: dict, fingerprint: str) -> str | None:
    """The endpoint the request was sent to, from the attempt's `request.json` (the artifact itself does not keep it)."""
    folder = f"service_calls/{fingerprint}/attempts"
    try:
        names = store.names(folder)
    except (OSError, ValueError):
        return None
    for name in sorted(names):
        key = f"{folder}/{name}/request.json"
        if store.exists(key):
            endpoint = store.read_json(key).get("endpoint")
            if endpoint:
                return endpoint.rstrip("/")
    return None


def _recipe(store: JsonStore, data: dict, fingerprint: str) -> dict | None:
    """Which recipe gives the recorded request its saved key: the weekly stage recipe (with the validator version it was
    saved under) or the brief workflow recipe."""
    endpoint = _endpoint(store, data, fingerprint)
    endpoints = [e for e in {endpoint, "https://openrouter.ai/api/v1", "https://openrouter.ai/api/v1/"} if e]
    # An embedding is keyed without an input hash; a chat stage with its first input hash.
    input_hashes = [None] if data["stage"] == "embedding" else [(data.get("input_hashes") or [None])[0]]
    versions = [2] if data["stage"] == "embedding" else range(VALIDATION_VERSION, 0, -1)
    for e in endpoints:
        for mode in ("live", "fake"):
            for version in versions:
                for input_hash in input_hashes:
                    if stage_fingerprint(mode=mode, stage=data["stage"], endpoint=e.rstrip("/"), request=data["request"],
                                         input_hash=input_hash, validation_version=version) == fingerprint:
                        return {"recipe": "stage", "namespace": mode, "validation_version": version}
        for workflow in BRIEF_WORKFLOWS:
            for synthetic in (False, True):
                if workflow_fingerprint(workflow=workflow, stage=data["stage"], request=data["request"], endpoint=e,
                                        synthetic=synthetic) == fingerprint:
                    return {"recipe": "workflow", "workflow": workflow, "synthetic": synthetic}
    return None


def check(root, stages: tuple[str, ...] | None = None) -> dict:
    store = JsonStore(root)
    try:
        pointers = sorted(n for n in store.names("cache/artifacts") if n.endswith(".json"))
    except (OSError, ValueError):
        pointers = []
    report = {"root": str(store.root), "artifacts": [], "replayable": 0, "not_replayable": 0, "failed_attempts": [],
              "provider_calls": 0}
    for name in pointers:
        fingerprint = name.removesuffix(".json")
        data = store.find_artifact(fingerprint)
        entry = {"fingerprint": fingerprint}
        if data is None:
            entry["problem"] = "the replay lookup does not serve it (not a validated cache_version 2 artifact with its own hash)"
        elif stages and data.get("stage") not in stages:
            continue
        else:
            recipe = _recipe(store, data, fingerprint)
            entry.update({"stage": data["stage"], "model": data.get("model_id"), "prompt_version": data.get("prompt_version"),
                          "run_id": data.get("run_id"), "key_recomputed": recipe is not None, **(recipe or {}),
                          "output_hash_identical": data.get("output_hash") == canonical_hash(data.get("output"))})
            if recipe is None:
                entry["problem"] = "the recorded request no longer gives the key it was saved under"
            elif not entry["output_hash_identical"]:
                entry["problem"] = "the output no longer has its recorded hash"
            elif recipe.get("validation_version") not in (None, current := 2 if data["stage"] == "embedding" else VALIDATION_VERSION):
                entry["revalidation_needed"] = (f"saved under validator version {recipe['validation_version']}; today's is "
                                                f"{current}, so it is served only after a re-check (E.B12a)")
        ok = "problem" not in entry
        report["replayable" if ok else "not_replayable"] += 1
        report["artifacts"].append(entry)
    try:
        calls = store.names("service_calls")
    except (OSError, ValueError):
        calls = []
    for fingerprint in sorted(calls):
        for attempt in sorted(store.names(f"service_calls/{fingerprint}/attempts")):
            key = f"service_calls/{fingerprint}/attempts/{attempt}/artifact.json"
            if not store.exists(key):
                continue
            data = store.read_json(key)
            if data.get("status") == "failed" and (not stages or data.get("stage") in stages):
                report["failed_attempts"].append({
                    "fingerprint": fingerprint, "stage": data.get("stage"), "run_id": data.get("run_id"),
                    "error": str(data.get("error"))[:200],
                    "received_response_saved": store.exists(f"service_calls/{fingerprint}/attempts/{attempt}/output.received.json")})
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Check that saved stage artifacts replay with identical keys and hashes")
    parser.add_argument("root", help="An artifact root (the folder holding cache/ and service_calls/)")
    parser.add_argument("--stage", action="append", dest="stages", help="Only this stage (repeatable)")
    args = parser.parse_args(argv)
    report = check(args.root, tuple(args.stages) if args.stages else None)
    print(json.dumps(report, indent=2))
    return 0 if report["not_replayable"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
