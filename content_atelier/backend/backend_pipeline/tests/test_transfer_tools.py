"""The data-transfer tools (plan 7.B3, 7.B5, S.B10): inventory, pack and upload, fetch and verify. Offline: an in-memory bucket.

What matters: credentials never leave the machine, an upload resumes, the completion marker comes last, a download checks every
checksum, and nothing unpacks outside its folder."""
from __future__ import annotations

import io
import json
import sys
import tarfile
from pathlib import Path

import pytest
from botocore.exceptions import ClientError

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts" / "transfer"
sys.path.insert(0, str(SCRIPTS))

import common  # noqa: E402
import fetch_and_verify  # noqa: E402
import inventory  # noqa: E402
import pack_and_upload  # noqa: E402

SECRET = b"OPENROUTER_API_KEY=sk-or-v1-" + b"a1b2c3d4e5f6a7b8c9d0e1f2a3b4"


class Bucket:
    """The few S3 calls the tools make, in memory."""
    def __init__(self):
        self.objects: dict[str, tuple[bytes, dict]] = {}
        self.uploads: list[str] = []

    def head_object(self, *, Bucket, Key):
        if Key not in self.objects:
            raise ClientError({"Error": {"Code": "404", "Message": "x"}}, "HeadObject")
        data, meta = self.objects[Key]
        return {"ContentLength": len(data), "Metadata": meta}

    def upload_file(self, filename, bucket, key, ExtraArgs=None, Config=None):
        self.uploads.append(key)
        self.objects[key] = (Path(filename).read_bytes(), (ExtraArgs or {}).get("Metadata", {}))

    def put_object(self, *, Bucket, Key, Body, Metadata=None):
        self.objects[Key] = (bytes(Body), Metadata or {})

    def get_object(self, *, Bucket, Key):
        return {"Body": io.BytesIO(self.objects[Key][0])}

    def download_file(self, bucket, key, filename):
        Path(filename).write_bytes(self.objects[key][0])

    def list_objects_v2(self, *, Bucket, Prefix="", **_):
        return {"Contents": [{"Key": k, "Size": len(v[0])} for k, v in sorted(self.objects.items()) if k.startswith(Prefix)], "IsTruncated": False}


def handover(bucket):
    return common.Handover(environ={"TRANSFER_S3_BUCKET": "handover"}, client=bucket)


@pytest.fixture
def tree(tmp_path):
    root = tmp_path / "artifacts"
    (root / "runs" / "week1").mkdir(parents=True)
    (root / "runs" / "week1" / "response.json").write_text('{"moments": []}')
    (root / "runs" / "week1" / "request.json").write_text('{"prompt": "hello"}')
    (root / "briefs").mkdir()
    (root / "briefs" / "brief-1.md").write_text("# brief")
    (root / ".env").write_text("ATELIER_API_SECRET=hunter2")
    (root / "notes.txt").write_bytes(SECRET)
    (root / "node_modules").mkdir()
    (root / "node_modules" / "skip.js").write_text("x")
    return root


def run_pack(monkeypatch, bucket, tmp_path, tree, *extra):
    monkeypatch.setattr(pack_and_upload, "Handover", lambda: handover(bucket))
    return pack_and_upload.main(["--artifacts", str(tree), "--work", str(tmp_path / "work"), "--report-dir", str(tmp_path / "reports"),
                                 "--stamp", "2026-10-19", *extra])


def test_a_dry_run_sends_nothing_and_names_what_it_would_leave_out(tmp_path, tree, monkeypatch, capsys):
    bucket = Bucket()
    assert run_pack(monkeypatch, bucket, tmp_path, tree) == 0
    out = capsys.readouterr().out
    assert "Dry run" in out and "left out: .env" in out and "notes.txt" in out and "hunter2" not in out and "sk-or-v1" not in out
    assert not bucket.objects and not (tmp_path / "work").exists()


def test_credentials_never_travel_and_the_manifest_is_the_completion_marker(tmp_path, tree, monkeypatch):
    bucket = Bucket()
    assert run_pack(monkeypatch, bucket, tmp_path, tree, "--upload") == 0
    keys = sorted(bucket.objects)
    assert keys[-1] == "handover/2026-10-19/manifest.json" or "handover/2026-10-19/manifest.json" in keys
    assert bucket.uploads and "handover/2026-10-19/manifest.json" not in bucket.uploads, "the marker is put last, after every part read back"
    manifest = json.loads(bucket.objects["handover/2026-10-19/manifest.json"][0])
    packed = {f["path"] for g in manifest["groups"].values() for p in g["parts"] for f in p["files"]}
    assert packed == {"runs/week1/response.json", "runs/week1/request.json", "briefs/brief-1.md"}
    left = {i["file"] for i in manifest["left_out"]["artifacts"]}
    assert left == {".env", "notes.txt"}, "a credential file name and a file whose text looks like a key are left out, by name only"
    blob = b"".join(data for data, _ in bucket.objects.values())
    assert b"hunter2" not in blob and b"sk-or-v1" not in blob
    # A finished handover is not overwritten.
    with pytest.raises(SystemExit):
        run_pack(monkeypatch, bucket, tmp_path, tree, "--upload")


def test_an_interrupted_upload_resumes_and_a_part_is_recognised_by_its_bytes(tmp_path, tree, monkeypatch):
    bucket = Bucket()
    original = bucket.upload_file
    calls = {"n": 0}

    def flaky(*a, **k):
        calls["n"] += 1
        if calls["n"] == 2:
            raise ConnectionError("link dropped")
        return original(*a, **k)

    bucket.upload_file = flaky
    # Two parts of one file each, so the second upload is the one that fails.
    with pytest.raises(ConnectionError):
        run_pack(monkeypatch, bucket, tmp_path, tree, "--upload", "--part-mb", "0")
    assert "handover/2026-10-19/manifest.json" not in bucket.objects, "an incomplete handover has no marker"
    first = [k for k in bucket.objects if k.endswith(".tar.gz")]
    bucket.upload_file = original
    bucket.uploads.clear()
    assert run_pack(monkeypatch, bucket, tmp_path, tree, "--upload", "--part-mb", "0") == 0
    assert set(first).isdisjoint(bucket.uploads), "a part that was already there is not sent again (the pack is byte-for-byte repeatable)"
    assert "handover/2026-10-19/manifest.json" in bucket.objects


def test_download_verifies_every_checksum_and_restores_the_tree(tmp_path, tree, monkeypatch, capsys):
    bucket = Bucket()
    run_pack(monkeypatch, bucket, tmp_path, tree, "--upload")
    monkeypatch.setattr(fetch_and_verify, "Handover", lambda: handover(bucket))
    target = tmp_path / "received"
    assert fetch_and_verify.main(["download", "--stamp", "2026-10-19", "--to", str(target)]) == 0
    assert (target / "artifacts" / "runs" / "week1" / "response.json").read_text() == '{"moments": []}'
    assert not (target / "artifacts" / ".env").exists() and not (target / "artifacts" / "notes.txt").exists()
    assert "artifacts copy --from" in capsys.readouterr().out
    assert fetch_and_verify.main(["list"]) == 0
    # A corrupted part is caught, not unpacked.
    key = next(k for k in bucket.objects if k.endswith("part-0001.tar.gz"))
    bucket.objects[key] = (bucket.objects[key][0][:-8] + b"corrupt!", bucket.objects[key][1])
    with pytest.raises(SystemExit):
        fetch_and_verify.main(["download", "--stamp", "2026-10-19", "--to", str(tmp_path / "second")])
    # No marker, no download.
    with pytest.raises(SystemExit):
        fetch_and_verify.main(["download", "--stamp", "2020-01-01", "--to", str(tmp_path / "third")])


def test_a_part_cannot_unpack_outside_its_folder(tmp_path):
    archive = tmp_path / "evil.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        data = b"x"
        info = tarfile.TarInfo("../escape.txt")
        info.size = len(data)
        tar.addfile(info, io.BytesIO(data))
    with pytest.raises(SystemExit):
        fetch_and_verify.safe_extract(archive, tmp_path / "safe")
    assert not (tmp_path / "escape.txt").exists()


@pytest.mark.parametrize("field", ["db_file", "group"])
def test_names_in_the_manifest_cannot_write_outside_the_target(tmp_path, tree, monkeypatch, field):
    """The manifest comes from the bucket: a database file or a folder group named `../...` must not place a file outside
    --to (the docstring's promise), whatever its checksum says."""
    bucket = Bucket()
    payload = b"dump bytes"
    sha = common.hashlib.sha256(payload).hexdigest()
    bucket.objects["handover/2026-10-19/db/x.dump"] = (payload, {"sha256": sha})
    manifest = {"databases": [], "groups": {}, "reports": []}
    if field == "db_file":
        manifest["databases"] = [{"name": "atelier", "file": "../../escaped.dump", "key": "handover/2026-10-19/db/x.dump",
                                  "size": len(payload), "sha256": sha}]
    else:
        run_pack(monkeypatch, bucket, tmp_path, tree, "--upload")
        manifest = json.loads(bucket.objects["handover/2026-10-19/manifest.json"][0])
        manifest["groups"] = {"../../escaped": manifest["groups"]["artifacts"]}
    bucket.objects["handover/2026-10-19/manifest.json"] = (json.dumps(manifest).encode(), {})
    monkeypatch.setattr(fetch_and_verify, "Handover", lambda: handover(bucket))
    target = tmp_path / "deep" / "received"
    with pytest.raises(SystemExit):
        fetch_and_verify.main(["download", "--stamp", "2026-10-19", "--to", str(target)])
    assert not (tmp_path / "escaped.dump").exists() and not (tmp_path / "escaped").exists()
    assert not (tmp_path / "deep" / "escaped.dump").exists() and not (tmp_path / "deep" / "escaped").exists()


def test_a_credentials_answer_that_is_not_json_is_never_printed(monkeypatch):
    """`railway bucket credentials` returns the bucket's secret key; if an older CLI answers in another format, the tool
    must say what failed without echoing that answer to the terminal."""
    secret = "SECRETKEY" + "x" * 30

    class Done:
        def __init__(self, stdout="", stderr="", returncode=0):
            self.stdout, self.stderr, self.returncode = stdout, stderr, returncode

    def fake_run(command, **_):
        if "credentials" in command:
            return Done(stdout=f"endpoint: https://s3.example\naccessKeyId: AKID\nsecretAccessKey: {secret}\n")
        return Done()
    monkeypatch.setattr(common.shutil, "which", lambda name: "railway")
    monkeypatch.setattr(common.subprocess, "run", fake_run)
    with pytest.raises(SystemExit) as raised:
        common.railway_environment()
    assert secret not in str(raised.value) and "AKID" not in str(raised.value)
    assert "credentials" in str(raised.value)


def test_without_the_variables_the_tools_ask_the_railway_cli_and_say_what_is_missing(monkeypatch):
    monkeypatch.setattr(common.shutil, "which", lambda name: None)
    for name in ("TRANSFER_S3_ENDPOINT", "TRANSFER_S3_BUCKET", "TRANSFER_S3_ACCESS_KEY_ID", "TRANSFER_S3_SECRET_ACCESS_KEY"):
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(SystemExit) as raised:
        common.Handover()
    assert "Railway CLI" in str(raised.value)


def test_the_inventory_holds_names_and_counts_but_no_secret_and_no_text(tmp_path, tree):
    repo = tmp_path / "repo"
    (repo / "backend").mkdir(parents=True)
    (repo / "backend" / ".env").write_text("OPENROUTER_API_KEY=sk-or-v1-" + "z" * 30 + "\nATELIER_API_SECRET=\nEMPTY_ONE=\n")
    zoom = tmp_path / "zoom"
    zoom.mkdir()
    for i in range(6):
        (zoom / f"call {i}.vtt").write_text("WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nPrivate client words here\n")
    out = tmp_path / "out"
    assert inventory.main(["--repo", str(repo), "--artifacts", str(tree), "--search-dir", str(tmp_path), "--out", str(out)]) == 0
    text = (out / "inventory-report.json").read_text() + (out / "inventory-report.md").read_text()
    assert "OPENROUTER_API_KEY" in text and "sk-or-v1" not in text and "Private client words" not in text
    report = json.loads((out / "inventory-report.json").read_text())
    (env,) = [e for e in report["environment_files"] if e["file"].endswith(".env")]
    assert env["names_with_a_value"] == ["OPENROUTER_API_KEY"] and "EMPTY_ONE" in env["variable_names"]
    assert any(f["path"].endswith("zoom") and f["transcript_files"] == 6 for f in report["transcript_folders"])
    flagged = report["artifact_trees"][0]["files_that_look_like_they_hold_a_credential"]
    assert [f["file"] for f in flagged] == ["notes.txt"]
    assert inventory.redact("postgresql://u:pw@h:5/d") == "postgresql://u:***@h:5/d"


def test_with_a_token_the_tools_name_the_project_by_id_and_never_ask_for_a_login(monkeypatch):
    """A workspace token (RAILWAY_API_TOKEN) has no user, so `railway whoami` and `railway link` fail with it; the owner's
    restore of 19 October needed the credentials read with the project and environment named by ID instead."""
    seen = []

    class Done:
        def __init__(self, stdout="", returncode=0):
            self.stdout, self.stderr, self.returncode = stdout, "", returncode

    def fake_run(command, env=None, **_):
        seen.append((command[1:], env))
        if "credentials" in command:
            return Done(stdout=json.dumps({"endpoint": "https://s3.example", "bucketName": "transfer-inbox-x", "accessKeyId": "A",
                                           "secretAccessKey": "S", "region": "auto", "urlStyle": "virtual-host"}))
        return Done(returncode=1)  # whoami and link fail with a token
    monkeypatch.setattr(common.shutil, "which", lambda name: "railway")
    monkeypatch.setattr(common.subprocess, "run", fake_run)
    monkeypatch.setenv("RAILWAY_API_TOKEN", "token-value")
    values = common.railway_environment()
    assert values["TRANSFER_S3_BUCKET"] == "transfer-inbox-x" and values["TRANSFER_S3_URL_STYLE"] == "virtual-host"
    ((args, env),) = seen
    assert args == ["bucket", "credentials", "--bucket", "transfer-inbox", "--json"]
    assert env["RAILWAY_PROJECT_ID"] == common.RAILWAY_PROJECT and env["RAILWAY_ENVIRONMENT_ID"] == common.RAILWAY_ENVIRONMENT_ID
