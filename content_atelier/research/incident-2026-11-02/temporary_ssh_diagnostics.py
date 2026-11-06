"""Use explicitly approved temporary SSH access; always revoke it and delete its key."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
CLI = Path(os.environ["APPDATA"]) / "npm/node_modules/@railway/cli/bin/railway.exe"
NAME = "atelier-incident-20261102-temporary"


def run(args, **kwargs):
    return subprocess.run([str(a) for a in args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", cwd=ROOT, **kwargs)


@contextmanager
def temporary_key_files():
    # The CLI selects keys discovered directly in ~/.ssh. Never replace an existing key.
    key_root = (Path.home() / ".ssh").resolve()
    private = key_root / ("id_ed25519_atelier_diagnostic_" + uuid4().hex)
    public = Path(str(private) + ".pub")
    assert private.parent == key_root and public.parent == key_root
    if private.exists() or public.exists():
        raise RuntimeError("Refusing to replace an existing key file")
    try:
        yield private
    finally:
        for item in (private, public):
            if item.exists():
                item.unlink()


def monitor_remote(args, source):
    """Stream read-only progress and save snapshots while this approved access is open."""
    proc = subprocess.Popen([str(a) for a in args], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace", cwd=ROOT)
    try:
        proc.stdin.write(source)
        proc.stdin.close()
        for line in proc.stdout:
            evidence = json.loads(line)
            (OUT / "weekly-recovery-monitor-latest.json").write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
            with (OUT / "weekly-recovery-monitor-history.jsonl").open("a", encoding="utf-8") as history:
                history.write(line)
            print(json.dumps({"at": evidence.get("at"),
                "schedule": (evidence.get("schedule") or {}).get("value", {}).get("state"),
                "runs": [{k: run.get(k) for k in ("run_id", "status", "current_message", "error_summary", "has_review_document")}
                         for run in evidence.get("runs", [])],
                "jobs": [{k: job.get(k) for k in ("stage", "status", "current_message", "error_summary")}
                         for job in evidence.get("jobs", [])],
                "cards": evidence.get("cards"), "documents": evidence.get("documents"),
                "stop_reason": evidence.get("stop_reason"), "error_type": evidence.get("error_type")}), flush=True)
        code = proc.wait(timeout=10)
        error = proc.stderr.read()
        if code:
            print("Remote read-only monitor ended:", error, flush=True)
        return code
    finally:
        if proc.poll() is None:
            proc.terminate()
            proc.wait(timeout=10)


def main():
    receipt = {"at": datetime.now(UTC).isoformat(), "registered": False, "removed": False}
    with temporary_key_files() as private:
        made = run(["ssh-keygen", "-t", "ed25519", "-N", "", "-C", NAME, "-f", private], timeout=15)
        if made.returncode:
            raise RuntimeError("Temporary key generation failed; private key output withheld")
        fingerprint = run(["ssh-keygen", "-lf", str(private) + ".pub"], timeout=15).stdout.split()[1]
        receipt["fingerprint"] = fingerprint
        registered = run([CLI, "ssh", "keys", "add", "--key", str(private) + ".pub", "--name", NAME], timeout=35)
        if registered.returncode:
            print(registered.stdout, registered.stderr, flush=True)
            raise RuntimeError("Temporary public key registration failed")
        receipt["registered"] = True
        print("Approved dedicated temporary SSH key registered.", flush=True)
        try:
            config = run([CLI, "ssh", "config", "--service", "scheduler", "--dry-run"], timeout=35)
            match = re.search(r"^\s*User\s+(\S+)", config.stdout, re.MULTILINE)
            if config.returncode or not match:
                raise RuntimeError("Could not resolve deployed scheduler SSH target")
            monitoring = "--monitor-recovery" in sys.argv
            capacity = "--capacity-detail" in sys.argv
            recovery = "--recovery-status" in sys.argv or "--rearm-weekly" in sys.argv or monitoring or capacity
            source = (OUT / ("recover_weekly.py" if recovery else "inspect_production.py")).read_text(encoding="utf-8")
            detail = "--collector-detail" in sys.argv
            remote_args = " --capacity-detail" if capacity else " --monitor" if monitoring else " --rearm" if "--rearm-weekly" in sys.argv else " --collector-detail-only" if detail else ""
            ssh_args = ["ssh", "-T", "-o", "BatchMode=yes", "-o", "IdentitiesOnly=yes",
                          "-o", "StrictHostKeyChecking=yes",
                          "-o", "UserKnownHostsFile=research/incident-2026-11-02/ssh_known_hosts",
                          "-o", "ServerAliveInterval=15", "-o", "ServerAliveCountMax=3",
                          "-o", "ConnectTimeout=20", "-i", private,
                          match[1] + "@ssh.railway.com", "python - --inside-container" + remote_args]
            if monitoring:
                receipt["remote_exit_code"] = monitor_remote(ssh_args, source)
                result = None
            else:
                result = run(ssh_args,
                         input=source, timeout=100)
                receipt["remote_exit_code"] = result.returncode
            if result is None:
                pass
            elif result.returncode:
                print("Remote diagnostic did not complete:", result.stdout, result.stderr, flush=True)
            else:
                evidence = json.loads(result.stdout)
                filename = "collector-readonly-evidence.json" if detail else "production-readonly-evidence.json"
                if recovery:
                    suffix = "capacity" if capacity else "rearm" if "--rearm-weekly" in sys.argv else "status"
                    filename = "weekly-recovery-" + suffix + "-" + datetime.now(UTC).strftime("%H%M%S") + ".json"
                (OUT / filename).write_text(
                    json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
                print(json.dumps(evidence, indent=2), flush=True)
        finally:
            for attempt in range(2):
                removed = run([CLI, "ssh", "keys", "remove", fingerprint], timeout=35)
                if removed.returncode == 0:
                    receipt["removed"] = True
                    print("Dedicated temporary Railway SSH registration removed.", flush=True)
                    break
            (OUT / "temporary-access-cleanup.json").write_text(
                json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
            if not receipt["removed"]:
                print("ATTENTION: Temporary key registration cleanup needs retry:", fingerprint, flush=True)
    receipt["local_temporary_key_files_deleted"] = not private.exists() and not Path(str(private) + ".pub").exists()
    (OUT / "temporary-access-cleanup.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print("Temporary private and public key files deleted.", flush=True)


if __name__ == "__main__":
    main()
