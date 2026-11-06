"""Fetch only; temporary access is revoked in finally. Contains no production write/retry path."""
import base64
import gzip
import hashlib
import json
import os
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / "reduced-run-preview"
CLI = Path(os.environ["APPDATA"]) / "npm/node_modules/@railway/cli/bin/railway.exe"

def call(args, **kwargs):
    return subprocess.run([str(x) for x in args], cwd=ROOT, capture_output=True, encoding="utf-8", timeout=45, **kwargs)

def main():
    OUT.mkdir(exist_ok=True)
    if (OUT / "production-snapshot.json").exists():
        raise RuntimeError("Refusing to overwrite preserved production snapshot")
    # Railway CLI discovers registrable keys only directly under the user's .ssh directory.
    key_root = (Path.home() / ".ssh").resolve()
    key = key_root / ("id_ed25519_atelier_diagnostic_" + uuid4().hex)
    assert key.parent == key_root and not key.exists() and not Path(str(key) + ".pub").exists()
    receipt = {"at": datetime.now(UTC).isoformat(), "registered": False, "removed": False, "database_writes": False}
    try:
        p = call(["ssh-keygen", "-t", "ed25519", "-N", "", "-C", "atelier-approved-readonly-fetch", "-f", key])
        assert p.returncode == 0, "Temporary key creation failed"
        fp = call(["ssh-keygen", "-lf", str(key) + ".pub"]).stdout.split()[1]
        receipt["fingerprint"] = fp
        p = call([CLI, "ssh", "keys", "add", "--key", str(key) + ".pub", "--name", "atelier-approved-readonly-fetch"])
        assert p.returncode == 0, "Temporary SSH registration failed: " + p.stdout + p.stderr
        receipt["registered"] = True
        config = call([CLI, "ssh", "config", "--service", "scheduler", "--dry-run"])
        match = re.search(r"^\s*User\s+(\S+)", config.stdout, re.MULTILINE)
        assert config.returncode == 0 and match, "Could not resolve Railway SSH target"
        args = ["ssh", "-T", "-o", "BatchMode=yes", "-o", "IdentitiesOnly=yes", "-o", "StrictHostKeyChecking=yes",
                "-o", "UserKnownHostsFile=research/incident-2026-11-02/ssh_known_hosts", "-o", "ConnectTimeout=20",
                "-i", key, match[1] + "@ssh.railway.com", "python -"]
        result = call(args, input=(HERE / "export_reduced_run_readonly.py").read_text(encoding="utf-8"))
        if result.returncode:
            # Tracebacks describe queries and schema only, never connection strings.
            raise RuntimeError("Read-only export failed: " + result.stderr[-2500:])
        raw = gzip.decompress(base64.b64decode(result.stdout.strip()))
        snapshot = json.loads(raw)
        (OUT / "production-snapshot.json").write_bytes(raw)
        artifacts = snapshot.pop("artifacts")
        for name, obj in artifacts.items():
            path = (OUT / "artifacts" / name).resolve()
            assert path.is_relative_to((OUT / "artifacts").resolve())
            content = base64.b64decode(obj["base64"])
            assert hashlib.sha256(content).hexdigest() == obj["sha256"]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        receipt["snapshot_sha256"] = hashlib.sha256(raw).hexdigest()
        receipt["snapshot_bytes"] = len(raw)
        receipt["artifact_count"] = len(artifacts)
        print(json.dumps({"fetched_at": snapshot["fetched_at"], "read_only": snapshot["read_only"],
                          "run_status": snapshot["run"]["status"], "documents": len(snapshot["transcripts"]),
                          "stored_moments": len(snapshot["moments"]), "cards": len(snapshot["cards"]),
                          "jobs": [{k: j[k] for k in ("job_id", "stage", "status")} for j in snapshot["jobs"]],
                          "artifact_count": len(artifacts), "snapshot_bytes": len(raw)}, indent=2), flush=True)
    finally:
        if receipt["registered"]:
            for _ in range(2):
                p = call([CLI, "ssh", "keys", "remove", receipt["fingerprint"]])
                if p.returncode == 0:
                    receipt["removed"] = True
                    break
        for item in (key, Path(str(key) + ".pub")):
            item.unlink(missing_ok=True)
        receipt["local_key_files_deleted"] = not key.exists() and not Path(str(key) + ".pub").exists()
        (OUT / "fetch-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"temporary_ssh_removed": receipt["removed"], "local_key_files_deleted": receipt["local_key_files_deleted"]}), flush=True)
        if receipt["registered"] and not receipt["removed"]:
            raise RuntimeError("Temporary SSH registration cleanup needs retry")

if __name__ == "__main__":
    main()
