"""0.B7: one artifact-store interface with a local and an S3-compatible implementation, used by every production caller.

The contract tests run on both backends; the end-to-end tests run a synthetic brief (dossiers, cost files, query
encodings) and the intake originals on the S3 backend against an in-memory client, then check that no production module
opens a folder directly.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest
from test_briefs import finish, ready  # noqa: F401 (the synthetic brief of the brief suite)
from test_future_intake import activate, batch, deliver, jobs, message, repo  # noqa: F401 (repo is a fixture)

from backend_pipeline import artifacts
from backend_pipeline.config import Settings
from backend_pipeline.intake.runtime import execute
from backend_pipeline.artifacts import LocalBackend, S3Backend, backend_for, clean_key, read_reference, reference_exists, store_for
from backend_pipeline.store import JsonStore
from backend_pipeline.storage_config import StorageSettings
from backend_pipeline.tests.fake_s3 import FakeS3
from backend_pipeline.tests.platform_db import platform_setup, platform_url  # noqa: F401 (fixtures)


@pytest.fixture(params=["local", "s3"])
def store(request, tmp_path):
    if request.param == "local":
        return JsonStore(tmp_path / "artifacts")
    return JsonStore(S3Backend("atelier-test", FakeS3(), prefix="env/production"))


@pytest.fixture
def s3(monkeypatch):
    """The environment of a platform with no shared disk: every store the code opens is the (fake) bucket."""
    client = FakeS3()
    monkeypatch.setenv("ATELIER_ARTIFACT_STORE", "s3")
    monkeypatch.setenv("ATELIER_S3_BUCKET", client.bucket)
    monkeypatch.setattr(artifacts, "s3_client", lambda environ=None: client)
    return client


# ---- the contract, on both backends -------------------------------------------------------------------------------

def test_json_round_trip_and_immutability(store):
    store.write_json("runs/a/manifest.json", {"value": 1})
    store.write_json("runs/a/manifest.json", {"value": 2})
    assert store.read_json("runs/a/manifest.json") == {"value": 1}, "a completed artifact is not replaced"
    store.write_json("runs/a/manifest.json", {"value": 3}, overwrite=True)
    assert store.read_json("runs/a/manifest.json") == {"value": 3}
    assert store.exists("runs/a/manifest.json") and not store.exists("runs/a/other.json")
    assert store.read_bytes("runs/a/manifest.json").endswith(b"\n")


def test_bytes_are_exact_and_a_different_original_is_refused(store):
    original = b"\x00\xffexact bytes"
    store.write_bytes("source-originals/h1.original", original)
    store.write_bytes("source-originals/h1.original", original)
    assert store.read_bytes("source-originals/h1.original") == original
    with pytest.raises(ValueError, match="Immutable artifact differs"):
        store.write_bytes("source-originals/h1.original", b"different")
    store.write_text("notes/a.md", "héllo")
    assert store.read_text("notes/a.md") == "héllo"


def test_listing_children_and_json_names(store):
    for name in ("costs/b.json", "costs/a.json", "costs/readme.md", "costs/sub/c.json", "other/x.json"):
        store.write_json(name, {"n": name}) if name.endswith(".json") else store.write_text(name, "x")
    assert store.names("costs") == ["a.json", "b.json", "readme.md", "sub"]
    assert store.json_names("costs") == ["costs/a.json", "costs/b.json"]
    assert store.names("missing") == [] and store.json_names("missing") == []
    assert store.exists("costs") and not store.exists("nothing-here")


def test_attempt_files_and_saved_attempts(store):
    fp = "f" * 64
    for attempt, received in (("a1", True), ("a2", True), ("a3", False)):
        base = f"service_calls/{fp}/attempts/{attempt}"
        store.write_json(f"{base}/request.json", {"n": attempt})
        if received:
            store.write_json(f"{base}/output.received.json", {"moments": []})
    saved = store.saved_attempts(fp)
    assert sorted(path for _, path in saved) == [f"service_calls/{fp}/attempts/a1", f"service_calls/{fp}/attempts/a2"]
    store.write_json("chunk-encoding-attempts/job1/t1/fpX/response.raw.json", {"ok": 1})
    store.write_json("chunk-encoding-attempts/job1/t2/fpX/response.raw.json", {"ok": 2})
    assert store.attempt_files("chunk-encoding-attempts/job1", "fpX", "response.raw.json") == [
        "chunk-encoding-attempts/job1/t2/fpX/response.raw.json", "chunk-encoding-attempts/job1/t1/fpX/response.raw.json"]
    assert store.saved_attempts("nothing") == []


def test_a_missing_key_is_a_file_not_found_and_keys_cannot_escape(store):
    with pytest.raises(FileNotFoundError):
        store.read_json("not/there.json")
    for bad in ("../outside.json", "a/../../outside.json", "C:/Windows/x.json"):
        with pytest.raises(ValueError, match="inside the datastore"):
            store.write_json(bad, {})
    assert clean_key("a\\b//c/./d.json") == "a/b/c/d.json"


def test_find_artifact_is_none_when_nothing_is_cached(store):
    assert store.find_artifact("0" * 64) is None


# ---- the S3 implementation ----------------------------------------------------------------------------------------

def test_s3_keys_live_under_the_prefix_and_listing_pages():
    client = FakeS3(page_size=2)
    backend = S3Backend("atelier-test", client, prefix="/env/production/")
    store = JsonStore(backend)
    for n in range(5):
        store.write_json(f"costs/{n}.json", {"n": n})
    assert sorted(client.objects) == [f"env/production/costs/{n}.json" for n in range(5)]
    assert store.names("costs") == [f"{n}.json" for n in range(5)], "every page is read"
    assert backend.description == "s3://atelier-test/env/production"
    assert store.modified("costs/0.json") > 0


def test_s3_errors_other_than_missing_are_not_hidden():
    from botocore.exceptions import ClientError

    class Broken(FakeS3):
        def get_object(self, **kw):
            raise ClientError({"Error": {"Code": "AccessDenied"}, "ResponseMetadata": {"HTTPStatusCode": 403}}, "GetObject")
    store = JsonStore(S3Backend("atelier-test", Broken()))
    with pytest.raises(ClientError):
        store.read_json("x.json")
    with pytest.raises(NotImplementedError):
        store.path("x.json")


# ---- choosing the backend -----------------------------------------------------------------------------------------

def test_the_environment_chooses_the_backend(tmp_path, monkeypatch):
    settings = StorageSettings(artifact_root=tmp_path / "a")
    monkeypatch.delenv("ATELIER_ARTIFACT_STORE", raising=False)
    assert isinstance(backend_for(settings.artifact_root), LocalBackend)
    assert store_for(settings).root == tmp_path / "a"
    client = FakeS3()
    env = {"ATELIER_ARTIFACT_STORE": "s3", "ATELIER_S3_BUCKET": client.bucket, "ATELIER_S3_PREFIX": "p"}
    assert isinstance(backend_for(settings.artifact_root, env, client), S3Backend)
    assert store_for(settings, env, client).root == "s3://atelier-test/p"
    with pytest.raises(ValueError, match="ATELIER_S3_BUCKET"):
        backend_for(settings.artifact_root, {"ATELIER_ARTIFACT_STORE": "s3"}, client)
    with pytest.raises(ValueError, match="local or s3"):
        backend_for(settings.artifact_root, {"ATELIER_ARTIFACT_STORE": "gcs"}, client)


def test_the_s3_client_is_configured_from_the_environment():
    client = artifacts.s3_client({"ATELIER_S3_ENDPOINT": "http://127.0.0.1:9000", "ATELIER_S3_ACCESS_KEY_ID": "k",
                                  "ATELIER_S3_SECRET_ACCESS_KEY": "s", "ATELIER_S3_REGION": "us-east-1"})
    assert client.meta.endpoint_url == "http://127.0.0.1:9000" and client.meta.region_name == "us-east-1"


# ---- the brand bundle, in the store -------------------------------------------------------------------------------

BUNDLE = ('{"status":"approved","approved_by":"whitney@example.invalid","voice":["Plain"],"strategy":["Bounded"],'
          '"cta_rules":["Exact"],"exemplars":[]}')


def test_a_brand_bundle_can_live_in_the_store(tmp_path, s3):
    settings = StorageSettings(artifact_root=tmp_path / "a", brief_brand_path="artifact:brand/bundle.json")
    assert not reference_exists(settings, settings.brief_brand_path)
    store_for(settings).write_text("brand/bundle.json", BUNDLE)
    assert reference_exists(settings, settings.brief_brand_path)
    assert b"whitney" in read_reference(settings, settings.brief_brand_path)
    from backend_pipeline.briefs.runtime import brand_bundle
    assert brand_bundle(settings)["documents"]["approved_by"] == "whitney@example.invalid"
    local = tmp_path / "bundle.json"
    local.write_text(BUNDLE, encoding="utf-8")
    assert reference_exists(settings, local) and read_reference(settings, str(local)) == BUNDLE.encode()


# ---- every production caller, on the bucket -------------------------------------------------------------------------

def test_a_synthetic_brief_runs_entirely_on_the_bucket(platform_setup, s3, tmp_path):
    repo, models, _ = platform_setup
    data = ready((repo, models, None))
    row = finish(data)
    assert row
    keys = sorted(s3.objects)
    assert any(k.startswith("brief-runs/") and k.endswith("/cost_summary.json") for k in keys), "cost files"
    assert any("brief-" in k or "service_calls/" in k for k in keys), "requests and dossiers"
    assert not (repo.settings.artifact_root).exists() or not any(Path(repo.settings.artifact_root).rglob("*.json")), \
        "nothing was written to the local folder"


def test_intake_originals_are_kept_in_and_served_from_the_bucket(s3, repo):
    import hashlib

    request = activate(repo)
    content = b"Client reports better inquiry follow-up."
    asset = {"file_id": "F1", "filename": "notes.txt", "mime_type": "text/plain", "size_bytes": len(content),
             "sha256": hashlib.sha256(content).hexdigest()}
    value = batch(request, messages=[message(files=[asset])])
    deliver(repo, value)
    repo.process_slack(value.batch_id)
    attachment = repo.batch_status(value.batch_id)["assets"][0]
    repo.upload(attachment["asset_id"], content)
    assert repo.store.root.startswith("s3://"), repo.store.root
    with repo.connection() as conn:
        row = conn.execute("SELECT raw_artifact FROM intake_assets").fetchone()
    assert row["raw_artifact"] in s3.objects and s3.objects[row["raw_artifact"]][0] == content, "the original is in the bucket"
    assert repo.store.read_bytes(row["raw_artifact"]) == content
    execute(jobs(repo, "intake_extract")[0]["job_id"], repo=repo, models=Settings())
    with repo.connection() as conn:
        assert conn.execute("SELECT status FROM intake_assets").fetchone()["status"] == "completed"
    assert any(k.startswith("intake/extracted/") for k in s3.objects), "the extraction cache is in the bucket"
    assert not list(Path(repo.settings.artifact_root).rglob("*.json")), "nothing was written to the local folder"


def test_no_production_module_opens_a_folder_directly():
    """Everything that runs in the API or a worker goes through store_for; only the local tools (the legacy runner,
    the experiments, the backfill and the one-off scripts) may open a folder as a store."""
    root = Path(__file__).resolve().parents[1]
    local_tools = {"store.py", "artifacts.py", "backfill.py", "import_history.py", "prepare.py", "token_budget.py", "calibration.py",
                   "pipeline.py", "cli.py", "worker.py"}
    pattern = re.compile(r"JsonStore\(([^)]*artifact_root[^)]*)\)")
    offenders = [f"{p.relative_to(root)}:{n}" for p in root.rglob("*.py") if "tests" not in p.parts and p.name not in local_tools
                 for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1) if pattern.search(line)]
    assert offenders == []


def test_a_live_weekly_call_is_sized_against_the_route_saved_in_the_store_the_workers_share(tmp_path):
    """A live weekly call (extraction, strategist) is checked against the model's saved public route before it is sent
    (token_budget). On the platform the workers share only the bucket, so the route must be read from the store the call
    writes its artifacts to, not from the worker's own disk, where it never is."""
    import hashlib

    from backend_pipeline.models import RunManifest
    from backend_pipeline.pipeline import Pipeline
    from backend_pipeline.tests.test_llm_module import SCHEMA, Stub
    from backend_pipeline.token_budget import LUNA_MANIFEST, LUNA_MODEL
    bucket = JsonStore(S3Backend("atelier-test", FakeS3(), prefix="env/production"))
    route = {"data": {"id": LUNA_MODEL, "endpoints": [{"provider_name": "p", "context_length": 400000, "max_prompt_tokens": None,
                                                        "max_completion_tokens": 128000, "pricing": {"prompt": "1", "completion": "1"},
                                                        "supported_parameters": ["response_format", "max_tokens", "reasoning"]}]}}
    bucket.write_json("provider_catalog/2026-10-19-luna.json", route)
    bucket.write_json(LUNA_MANIFEST, {"model": LUNA_MODEL, "route_snapshot": "provider_catalog/2026-10-19-luna.json",
                                      "route_sha256": hashlib.sha256(bucket.read_bytes("provider_catalog/2026-10-19-luna.json")).hexdigest()})
    stub = Stub()
    worker_disk = tmp_path / "worker-disk"
    pipeline = Pipeline(Settings(data_root=worker_disk, openrouter_moments_model=LUNA_MODEL, llm_payload_format="compact_weekly",
                                 llm_completion_tokens=4000), stub)
    pipeline.store = bucket  # what the SQL worker does: its stage calls read and write the configured artifact store
    run = RunManifest(run_id="r-live", week_index=1, source_root="sql", source_ids=[], prompt_profile="p", model_id=LUNA_MODEL,
                      embedding_profile="e", mode="live")
    artifact = pipeline.calls.call_json("moment_extraction", run, "experiments/default/runs/r-live", "system", "user", "h", SCHEMA,
                                        validate=lambda out: None)
    assert artifact.status == "validated" and stub.calls["moment_extraction"] == 1
    attempt = pipeline.calls.attempt_paths[artifact.request_fingerprint]
    report = bucket.read_json(f"{attempt}/preflight.json")
    assert report["fits"] and report["route_snapshot"] == "provider_catalog/2026-10-19-luna.json"
    assert not (worker_disk / "tokenizers").exists() and not (worker_disk / "provider_catalog").exists()


def test_a_model_variant_route_is_saved_under_a_name_every_store_accepts(tmp_path, monkeypatch):
    """A `:free` model id put a colon in the snapshot's file name, which a Windows folder store refuses (found by the N1
    shakedown, 23 October); the saved route is still found by the preflight through its manifest."""
    import httpx

    from backend_pipeline import token_budget
    model = token_budget.NEMOTRON_FREE_MODEL
    catalog = {"data": {"id": model, "endpoints": [{"provider_name": "p", "context_length": 1000000, "max_prompt_tokens": None,
                                                    "max_completion_tokens": 131072, "pricing": {"prompt": "0", "completion": "0"},
                                                    "supported_parameters": ["response_format", "max_tokens", "reasoning"]}]}}
    monkeypatch.setattr(httpx.Client, "get", lambda self, url: httpx.Response(200, json=catalog, request=httpx.Request("GET", url)))
    manifest = token_budget.cache_byte_budget_route(tmp_path, model)
    assert ":" not in manifest["route_snapshot"] and manifest["route_snapshot"].endswith("nemotron-3.5-super-vl-free.json")
    request = {"model": model, "max_tokens": 16000, "messages": [{"role": "system", "content": "s"}, {"role": "user", "content": "u"}],
               "response_format": {"type": "json_schema"}}
    assert token_budget.preflight(request, tmp_path)["fits"]


# ---- 0.B7 / 0.B11: the platform's health check and port ---------------------------------------------------------------

def test_health_names_nothing_about_the_configuration():
    from fastapi.testclient import TestClient

    from backend_pipeline.api import app
    response = TestClient(app).get("/health")
    assert response.status_code == 200 and response.json() == {"status": "ok"}


def test_the_image_listens_on_the_platform_port(monkeypatch):
    dockerfile = (Path(__file__).resolve().parents[2] / "Dockerfile").read_text(encoding="utf-8")
    assert 'CMD ["python", "-m", "backend_pipeline.serve"]' in dockerfile
    from backend_pipeline import serve
    bound = []
    monkeypatch.setattr(serve, "listening_socket", lambda port: bound.append(port) or "socket")
    monkeypatch.setattr(serve.uvicorn.Server, "run", lambda self, sockets: bound.append((self.config.app, sockets)))
    monkeypatch.setenv("PORT", "8123")
    monkeypatch.setenv("WEB_CONCURRENCY", "1")
    serve.main()
    assert bound == [8123, (serve.APP, ["socket"])]


def test_the_api_runs_several_processes_on_one_socket_by_default(monkeypatch):
    """One process serves one core's worth of the reads, however many cores the host has (3 November)."""
    from backend_pipeline import serve
    started = []
    monkeypatch.setattr(serve, "listening_socket", lambda port: "socket")

    class Supervisor:
        def __init__(self, config, target, sockets):
            started.append((config.app, config.workers, sockets))

        def run(self):
            pass
    monkeypatch.setattr(serve, "Multiprocess", Supervisor)
    monkeypatch.delenv("WEB_CONCURRENCY", raising=False)
    serve.main()
    assert started == [(serve.APP, serve.DEFAULT_WORKERS, ["socket"])] and serve.DEFAULT_WORKERS > 1


def test_the_api_socket_answers_ipv4_and_ipv6_clients():
    """`uvicorn --host ::` answered IPv6 only (asyncio sets IPV6_V6ONLY), so the local Frontend, the compose health check
    and every IPv4 client were refused (found by the N1 shakedown, 23 October); the image's socket takes both."""
    import socket
    from backend_pipeline.serve import listening_socket
    server = listening_socket(0)
    try:
        port = server.getsockname()[1]
        with socket.create_connection(("127.0.0.1", port), timeout=3):
            pass
        if socket.has_ipv6 and server.family == socket.AF_INET6:
            with socket.create_connection(("::1", port), timeout=3):
                pass
    finally:
        server.close()


def test_the_image_listens_on_ipv6_and_writes_only_where_its_user_may():
    """Railway's private network (the Frontend's way to the API) is IPv6 only, so the API binds `::` with IPV6_V6ONLY off
    (dual stack), never 0.0.0.0 alone. The app user (uid 10001) cannot write under /app, so the image's artifact root is
    /artifacts, which it owns."""
    import re
    root = Path(__file__).resolve().parents[2]
    dockerfile = (root / "Dockerfile").read_text(encoding="utf-8")
    serve = (root / "backend_pipeline" / "serve.py").read_text(encoding="utf-8")
    assert 'sock.bind(("::", port))' in serve and "IPV6_V6ONLY, 0" in serve
    assert re.search(r"^ENV .*\bATELIER_ARTIFACT_ROOT=/artifacts\b", dockerfile, re.M)
    assert re.search(r"chown atelier:atelier[^\n]*/artifacts", dockerfile)
    deployment = (root.parent / "DEPLOYMENT.md").read_text(encoding="utf-8")
    assert "--host 0.0.0.0" not in deployment and "python -m backend_pipeline.serve" in deployment


# ---- restoring a backup into the bucket -------------------------------------------------------------------------------

def test_a_folder_backup_is_copied_into_the_bucket_without_replacing_or_deleting(tmp_path):
    from backend_pipeline.artifacts import copy_tree
    source = tmp_path / "backup"
    (source / "service_calls/f1/attempts/a1").mkdir(parents=True)
    (source / "service_calls/f1/attempts/a1/output.received.json").write_text('{"moments": []}\n', encoding="utf-8")
    (source / "source-originals").mkdir()
    (source / "source-originals/h1.original").write_bytes(b"\x00exact")
    (source / "leftover.tmp").write_bytes(b"half written")
    bucket = JsonStore(S3Backend("atelier-test", FakeS3()))
    bucket.write_bytes("source-originals/h2.original", b"already there")
    preview = copy_tree(source, bucket, dry_run=True)
    assert preview["copied"] == 2 and not bucket.exists("source-originals/h1.original")
    done = copy_tree(source, bucket)
    assert done == {"copied": 2, "skipped": 0, "different": [], "failed": [], "dry_run": False}
    assert bucket.read_bytes("source-originals/h1.original") == b"\x00exact" and bucket.exists("source-originals/h2.original")
    assert bucket.saved_attempts("f1"), "the saved response is found by the code that replays it"
    again = copy_tree(source, bucket)
    assert again["copied"] == 0 and again["skipped"] == 2
    bucket.write_bytes("source-originals/h3.original", b"bucket version")
    (source / "source-originals/h3.original").write_bytes(b"backup version")
    clash = copy_tree(source, bucket)
    assert clash["different"] == ["source-originals/h3.original"]
    assert bucket.read_bytes("source-originals/h3.original") == b"bucket version", "an immutable artifact is never replaced"
    with pytest.raises(ValueError):
        copy_tree(tmp_path / "missing", bucket)


def test_the_documented_copy_command_runs_as_a_module(tmp_path):
    """`python -m backend_pipeline.artifacts copy` (the runbook's restore step) failed with a TypeError: run as `__main__`,
    the module was a second copy whose LocalBackend `store.py` did not recognise (found restoring the handover)."""
    import json
    import os
    import subprocess
    import sys
    source = tmp_path / "backup"
    (source / "source-originals").mkdir(parents=True)
    (source / "source-originals/h1.original").write_bytes(b"\x00exact")
    env = {**os.environ, "ATELIER_ARTIFACT_ROOT": str(tmp_path / "store"), "ATELIER_ARTIFACT_STORE": "local"}
    backend = Path(__file__).resolve().parents[2]
    done = subprocess.run([sys.executable, "-m", "backend_pipeline.artifacts", "copy", "--from", str(source)], cwd=backend, env=env,
                          capture_output=True, text=True, timeout=60)
    assert done.returncode == 0, done.stderr
    assert json.loads(done.stdout)["copied"] == 1
    assert (tmp_path / "store" / "source-originals" / "h1.original").read_bytes() == b"\x00exact"
