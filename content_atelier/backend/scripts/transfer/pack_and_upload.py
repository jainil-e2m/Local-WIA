"""Dump, pack, checksum and upload this machine's Content Atelier data to the handover bucket (plan 7.B5, S.B10).

Without --upload it only reports what it would send (no dump, no network). With --upload it:

  1. dumps each --database with pg_dump (custom format, vectors included) or, with --docker-container, with `docker exec ... pg_dump`;
  2. packs the artifact tree and each --extra folder into tar.gz parts of about 256 MB, leaving out credentials (see common.py);
  3. uploads every part with its sha256, skipping a part the bucket already holds (so a broken upload resumes);
  4. uploads the inventory report, then manifest.json LAST: its presence means the handover is complete;
  5. reads every key back (size and checksum metadata) and reports.

    python scripts/transfer/pack_and_upload.py --upload --stamp 2026-10-19 \\
        --database atelier=postgresql://atelier:PASSWORD@127.0.0.1:15432/atelier \\
        --artifacts ../backend/.storage-artifacts --extra zoom-backfill=/path/to/zoom/files

Credentials: TRANSFER_S3_* environment variables (common.py). Nothing here deletes or changes anything on this machine except
the temporary parts it builds under --work.
"""
from __future__ import annotations

import argparse
import gzip
import json
import platform
import shutil
import subprocess
import sys
import tarfile
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import PART_BYTES, Handover, excluded_name, fail, human, say, secret_in, sha256_file, walk  # noqa: E402

TOOL_VERSION = "1"


def plan_tree(root: Path, part_bytes: int = PART_BYTES) -> dict:
    """Which files go, in which part, and which are left out (by name or because they look like they hold a credential)."""
    parts, current, size = [], [], 0
    left_out = []
    total = 0
    for path, rel in walk(root):
        if excluded_name(path.name):
            left_out.append({"file": rel, "reason": "credential or key file name"})
            continue
        if kind := secret_in(path):
            left_out.append({"file": rel, "reason": f"looks like it holds a credential ({kind})"})
            continue
        n = path.stat().st_size
        if current and size + n > part_bytes:
            parts.append(current)
            current, size = [], 0
        current.append((path, rel, n))
        size += n
        total += n
    if current:
        parts.append(current)
    return {"parts": parts, "left_out": left_out, "bytes": total, "files": sum(len(p) for p in parts)}


def build_part(files, target: Path) -> dict:
    """One tar.gz of the files, named by their relative paths, with each file's sha256 recorded for the check after unpacking."""
    target.parent.mkdir(parents=True, exist_ok=True)
    inner = []
    # mtime 0 in the gzip header: the same files always give the same bytes, so a resumed upload recognises a part it already sent.
    with open(target, "wb") as raw, gzip.GzipFile(filename="", mode="wb", fileobj=raw, compresslevel=3, mtime=0) as packed,             tarfile.open(fileobj=packed, mode="w") as tar:
        for path, rel, n in files:
            inner.append({"path": rel, "bytes": n, "sha256": sha256_file(path)})
            info = tar.gettarinfo(str(path), arcname=rel)
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            with open(path, "rb") as handle:
                tar.addfile(info, handle)
    return {"files": inner, "size": target.stat().st_size, "sha256": sha256_file(target)}


def find_container(url: str | None) -> str | None:
    """The running Postgres container that serves `url`'s port (or the only Postgres container), so a dump can run inside the server's own image."""
    if not shutil.which("docker"):
        return None
    try:
        listing = subprocess.run(["docker", "ps", "--format", "{{.Names}}|{{.Image}}|{{.Ports}}"], capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    rows = [line.split("|", 2) for line in listing.stdout.splitlines() if line.count("|") == 2]
    postgres = [r for r in rows if "postgres" in r[1].lower() or "pgvector" in r[1].lower()]
    port = urlsplit(url).port if url else None
    if port:
        for name, _, ports in postgres:
            if f":{port}->" in ports:
                return name
    return postgres[0][0] if len(postgres) == 1 else None


def _toc_entries(target: Path, container: str | None) -> int | None:
    """A readable table of contents is a bonus check; a missing pg_restore must not undo a good dump."""
    try:
        listing = subprocess.run(["docker", "exec", "-i", container, "pg_restore", "-l"], input=target.read_bytes(), capture_output=True) \
            if container else subprocess.run(["pg_restore", "-l", str(target)], capture_output=True)
    except OSError:
        return None
    if listing.returncode != 0:
        return None
    return len([line for line in listing.stdout.decode(errors="replace").splitlines() if line and not line.startswith(";")])


def dump_database(name: str, url: str | None, target: Path, *, container: str | None, user: str | None, dbname: str | None) -> dict:
    """pg_dump in custom format, vectors included. Tries the local client first; if it is missing or older than the server (or a
    container is named), runs pg_dump inside the server's own Docker container, found from the URL's port when not named."""
    target.parent.mkdir(parents=True, exist_ok=True)
    parts = urlsplit(url) if url else None
    user = user if user and user != "atelier" else (parts.username if parts and parts.username else (user or "atelier"))
    dbname = dbname or (parts.path.strip("/") if parts and parts.path.strip("/") else name)
    problems = []
    used = None
    if not container and url and shutil.which("pg_dump"):
        done = subprocess.run(["pg_dump", "-Fc", "--no-owner", "--no-acl", "-f", str(target), url], capture_output=True)
        if done.returncode == 0:
            used = "local"
        else:
            problems.append("local pg_dump: " + done.stderr.decode(errors="replace").strip()[:300])
    elif not container and url:
        problems.append("pg_dump is not installed here")
    if used is None:
        container = container or find_container(url)
        if container:
            command = ["docker", "exec", container, "pg_dump", "-Fc", "--no-owner", "--no-acl", "-U", user, "-d", dbname]
            with open(target, "wb") as out:
                done = subprocess.run(command, stdout=out, stderr=subprocess.PIPE)
            if done.returncode == 0:
                used = f"docker:{container}"
            else:
                problems.append(f"docker exec {container} pg_dump: " + done.stderr.decode(errors="replace").strip()[:300])
        else:
            problems.append("no running Postgres container was found to dump from")
    if used is None:
        fail(f"could not dump {name}: " + " | ".join(problems))
    say(f"  dumped {name} with {used}")
    return {"name": name, "file": target.name, "size": target.stat().st_size, "sha256": sha256_file(target), "toc_entries": _toc_entries(target, container if used != "local" else None)}


def describe(plans: dict[str, dict]) -> None:
    for group, plan in plans.items():
        say(f"  {group}: {plan['files']} files, {human(plan['bytes'])}, {len(plan['parts'])} part(s); {len(plan['left_out'])} file(s) left out")
        for item in plan["left_out"][:20]:
            say(f"      left out: {item['file']} ({item['reason']})")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--stamp", default=datetime.now(UTC).strftime("%Y-%m-%d"), help="The handover's name; the bucket prefix is handover/<stamp>/")
    parser.add_argument("--database", action="append", default=[], metavar="NAME=URL", help="A database to dump (the URL may be blank with --docker-container)")
    parser.add_argument("--docker-container", help="Dump through `docker exec <container> pg_dump` (the dump matches the server's own version)")
    parser.add_argument("--docker-user", default="atelier")
    parser.add_argument("--artifacts", type=Path, default=Path("../backend/.storage-artifacts"))
    parser.add_argument("--extra", action="append", default=[], metavar="NAME=FOLDER", help="Another folder to send (the Zoom backfill originals, say)")
    parser.add_argument("--report-dir", type=Path, default=Path("transfer-work"), help="Where inventory.py wrote its report")
    parser.add_argument("--work", type=Path, default=Path("transfer-work/pack"))
    parser.add_argument("--part-mb", type=int, default=PART_BYTES // (1024 * 1024))
    parser.add_argument("--keep-parts", action="store_true", help="Keep each part on disk after it is uploaded (default: delete it to save space)")
    parser.add_argument("--upload", action="store_true", help="Do it. Without this, only report the plan")
    args = parser.parse_args(argv)
    part_bytes = args.part_mb * 1024 * 1024

    sources = {}
    if args.artifacts.is_dir():
        sources["artifacts"] = args.artifacts
    else:
        say(f"note: no artifact tree at {args.artifacts}")
    for item in args.extra:
        name, _, folder = item.partition("=")
        if not folder or not Path(folder).is_dir():
            fail(f"--extra needs NAME=FOLDER with an existing folder, got {item!r}")
        sources["extra-" + name] = Path(folder)
    databases = []
    for item in args.database:
        name, _, url = item.partition("=")
        if not name or (not url and not args.docker_container):
            fail("--database needs NAME=URL (or NAME= with --docker-container)")
        databases.append((name, url))
    if not databases and not sources:
        fail("Nothing to send: give --database and/or an artifact tree")

    plans = {group: plan_tree(folder, part_bytes) for group, folder in sources.items()}
    say(f"Handover {args.stamp}: {len(databases)} database(s), {len(plans)} folder group(s)")
    describe(plans)
    if not args.upload:
        say("Dry run: nothing was dumped, built or sent. Add --upload to do it.")
        return 0

    handover = Handover()
    prefix = f"handover/{args.stamp}/"
    if handover.head(prefix + "manifest.json"):
        fail(f"{prefix}manifest.json already exists: that handover is complete. Use a new --stamp for another one.")
    manifest = {"tool_version": TOOL_VERSION, "stamp": args.stamp, "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
                "machine": platform.node(), "databases": [], "groups": {}, "left_out": {}, "reports": []}
    uploaded = skipped = 0

    def send(path: Path, key: str, sha: str) -> None:
        nonlocal uploaded, skipped
        size = path.stat().st_size
        if handover.has(key, size, sha):
            skipped += 1
            say(f"  already there: {key}")
            return
        handover.upload(path, key, sha)
        uploaded += 1
        say(f"  uploaded {key} ({human(size)})")

    for name, url in databases:
        say(f"Dumping {name} ...")
        info = dump_database(name, url or None, args.work / "db" / f"{name}.dump", container=args.docker_container, user=args.docker_user, dbname=None)
        send(args.work / "db" / info["file"], f"{prefix}db/{info['file']}", info["sha256"])
        manifest["databases"].append({**info, "key": f"{prefix}db/{info['file']}"})
        if not args.keep_parts:
            (args.work / "db" / info["file"]).unlink(missing_ok=True)
    for group, plan in plans.items():
        say(f"Packing {group} ...")
        parts = []
        for number, files in enumerate(plan["parts"], 1):
            local = args.work / group / f"part-{number:04d}.tar.gz"
            built = build_part(files, local)
            key = f"{prefix}{group}/part-{number:04d}.tar.gz"
            send(local, key, built["sha256"])
            parts.append({"key": key, "size": built["size"], "sha256": built["sha256"], "files": built["files"]})
            if not args.keep_parts:
                local.unlink(missing_ok=True)
        manifest["groups"][group] = {"source": str(sources[group]), "files": plan["files"], "bytes": plan["bytes"], "parts": parts}
        manifest["left_out"][group] = plan["left_out"]
    for report in ("inventory-report.json", "inventory-report.md"):
        path = args.report_dir / report
        if path.is_file():
            key = f"{prefix}reports/{report}"
            send(path, key, sha256_file(path))
            manifest["reports"].append(key)
    # Read everything back before the completion marker goes up.
    problems = []
    for entry in manifest["databases"]:
        found = handover.head(entry["key"])
        if not found or found["ContentLength"] != entry["size"]:
            problems.append(entry["key"])
    for group in manifest["groups"].values():
        for part in group["parts"]:
            found = handover.head(part["key"])
            if not found or found["ContentLength"] != part["size"] or (found.get("Metadata") or {}).get("sha256") != part["sha256"]:
                problems.append(part["key"])
    if problems:
        fail("These keys did not read back as uploaded; run the command again (it resumes): " + ", ".join(problems[:10]))
    body = json.dumps(manifest, indent=2).encode()
    handover.put_bytes(prefix + "manifest.json", body, "manifest")
    total = sum(d["size"] for d in manifest["databases"]) + sum(p["size"] for g in manifest["groups"].values() for p in g["parts"])
    say(f"Done. {uploaded} uploaded, {skipped} already there, {human(total)} in the handover {args.stamp}. manifest.json is the completion marker.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
