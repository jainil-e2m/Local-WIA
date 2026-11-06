"""Local-only diagnostic preparation. Never writes to Railway, PostgreSQL or S3."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "reduced-run-preview"
CLI = Path(os.environ["APPDATA"]) / "npm/node_modules/@railway/cli/bin/railway.exe"
RUN_ID = "run_113a8c5a0b384cfba61e6fc7b59367ee"
sys.path.insert(0, str(ROOT / "backend"))


def cli_json(*args):
    p = subprocess.run([str(CLI), *args], capture_output=True, encoding="utf-8", cwd=ROOT, timeout=45)
    if p.returncode:
        raise RuntimeError("Read-only Railway CLI request failed; credential-bearing output withheld")
    return json.loads(p.stdout)


def variables(service):
    return cli_json("variables", "--service", service, "--environment", "production", "--json")


def main():
    OUT.mkdir(exist_ok=True)
    if sys.argv[1:] == ["--inspect-access"]:
        import importlib.util
        status = cli_json("status", "--json")
        assert status["id"] == "3409333b-1844-456c-93f9-f572ba92eb92"
        deployments = []
        for env in status["environments"]["edges"]:
            if env["node"]["id"] == "28239d73-fe52-4d23-bf80-94a8064c5eb5":
                for edge in env["node"]["serviceInstances"]["edges"]:
                    n = edge["node"]
                    if n["serviceName"] in ("scheduler", "editorial-worker", "bulk-worker"):
                        d = n.get("latestDeployment") or {}
                        deployments.append({"service": n["serviceName"], "id": d.get("id"),
                                            "status": d.get("status"), "commit": d.get("meta", {}).get("commitHash")})
        pg = variables("postgres")
        sched = variables("scheduler")
        print(json.dumps({"deployments": deployments,
                          "postgres_public_url_available": bool(pg.get("DATABASE_PUBLIC_URL")),
                          "postgres_variable_names": sorted(pg),
                          "scheduler_artifact_variable_names": sorted(k for k in sched if "ARTIFACT" in k or "S3" in k),
                          "python": sys.executable,
                          "modules": {m: importlib.util.find_spec(m) is not None for m in ("psycopg", "boto3", "pydantic")}}, indent=2))
        (OUT / "deployment-status.json").write_text(json.dumps(deployments, indent=2) + "\n", encoding="utf-8")
        return
    raise SystemExit("Only --inspect-access is currently implemented")


if __name__ == "__main__":
    main()
