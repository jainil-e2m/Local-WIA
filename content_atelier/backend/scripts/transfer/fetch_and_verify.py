"""Download a handover from the bucket, verify every checksum and unpack it (plan 7.B5, S.B10).

    python scripts/transfer/fetch_and_verify.py list
    python scripts/transfer/fetch_and_verify.py download --stamp 2026-10-19 --to ../handover-2026-10-19 [--no-unpack]

The handover is complete only when its manifest.json exists. Every database dump and every packed part is downloaded, its sha256
is compared with the manifest's, each unpacked file is compared with the file list recorded when it was packed, and nothing is
written outside --to. The command ends by printing how to restore the databases and the artifact tree on this machine.

Credentials: TRANSFER_S3_* environment variables (common.py).
"""
from __future__ import annotations

import argparse
import json
import sys
import tarfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import Handover, fail, human, say, sha256_file  # noqa: E402


def safe_extract(archive: Path, target: Path) -> list[str]:
    """Unpack a part, refusing any member that would land outside `target` (absolute paths, `..`, links)."""
    names = []
    root = target.resolve()
    with tarfile.open(archive, "r:gz") as tar:
        for member in tar.getmembers():
            destination = (root / member.name).resolve()
            if not member.isfile() or root not in destination.parents:
                fail(f"{archive.name} holds an unsafe member {member.name!r}; nothing more was unpacked")
            names.append(member.name)
        tar.extractall(root, members=tar.getmembers(), filter="data")
    return names


def safe_name(value, what: str) -> str:
    """A name from the manifest (which comes from the bucket) used as one file or folder name under --to: one plain path
    segment, never `..`, a separator or a drive, so nothing can be placed outside the target."""
    text = str(value or "")
    if (not text or text in {".", ".."} or "/" in text or "\\" in text or ":" in text or text != text.strip()
            or any(ord(ch) < 32 for ch in text)):
        fail(f"the manifest names an unsafe {what} {text!r}; nothing was downloaded")
    return text


def check_names(manifest: dict) -> None:
    """Every name the manifest gives a local file or folder, checked before anything is written."""
    for db in manifest.get("databases", []):
        safe_name(db.get("file"), "database file")
    for group, info in manifest.get("groups", {}).items():
        safe_name(group, "folder group")
        for part in info.get("parts", []):
            safe_name(Path(str(part.get("key", ""))).name, "part")
    for report in manifest.get("reports", []):
        safe_name(Path(str(report)).name, "report")


def verify_unpacked(group_dir: Path, files: list[dict]) -> list[str]:
    bad = []
    for entry in files:
        path = group_dir / entry["path"]
        if not path.is_file() or path.stat().st_size != entry["bytes"] or sha256_file(path) != entry["sha256"]:
            bad.append(entry["path"])
    return bad


def restore_notes(manifest: dict, to: Path) -> str:
    lines = ["", "Restore on this machine:", ""]
    for db in manifest["databases"]:
        lines += [f"  # database {db['name']}: into a local pgvector Postgres (the CI image pgvector/pgvector:0.8.2-pg17), then check the counts against the inventory",
                  f"  createdb -h 127.0.0.1 -p 25432 -U atelier restored_{db['name']}   # or: docker exec <container> createdb -U atelier restored_{db['name']}",
                  f"  pg_restore --no-owner --no-acl -h 127.0.0.1 -p 25432 -U atelier -d restored_{db['name']} {to / 'db' / db['file']}",
                  "  # or, from a container: docker exec -i <container> pg_restore --no-owner --no-acl -U atelier -d restored_" + db["name"] + f" < {to / 'db' / db['file']}", ""]
    if "artifacts" in manifest["groups"]:
        lines += ["  # the artifact tree, into the folder the backend reads (never replaces a file that differs)",
                  f"  python -m backend_pipeline.artifacts copy --from {to / 'artifacts'} --dry-run",
                  f"  python -m backend_pipeline.artifacts copy --from {to / 'artifacts'}", ""]
    others = [g for g in manifest["groups"] if g != "artifacts"]
    if others:
        lines += ["  # other folders (the Zoom backfill originals): " + ", ".join(f"{to / g}" for g in others),
                  "  python -m backend_pipeline.storage_cli documents import <folder>   # then the order in backend/docs/Phase-2-Moments-Handover.md", ""]
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list", help="The handovers in the bucket and whether each is complete")
    down = sub.add_parser("download")
    down.add_argument("--stamp", required=True)
    down.add_argument("--to", type=Path, required=True)
    down.add_argument("--no-unpack", action="store_true", help="Download and verify the parts only")
    args = parser.parse_args(argv)
    handover = Handover()

    if args.command == "list":
        stamps: dict[str, bool] = {}
        for item in handover.keys("handover/"):
            parts = item["key"].split("/")
            if len(parts) >= 3:
                stamps.setdefault(parts[1], False)
                if parts[2] == "manifest.json":
                    stamps[parts[1]] = True
        for stamp, complete in sorted(stamps.items()):
            say(f"{stamp}: {'complete' if complete else 'INCOMPLETE (no manifest.json yet)'}")
        if not stamps:
            say("No handover in the bucket yet.")
        return 0

    prefix = f"handover/{args.stamp}/"
    if not handover.head(prefix + "manifest.json"):
        fail(f"{prefix}manifest.json is not there: the handover is not complete (or the stamp is wrong). Run `list`.")
    manifest = json.loads(handover.get_bytes(prefix + "manifest.json"))
    check_names(manifest)
    args.to.mkdir(parents=True, exist_ok=True)
    (args.to / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    problems = []
    for db in manifest["databases"]:
        target = args.to / "db" / db["file"]
        if not (target.is_file() and target.stat().st_size == db["size"] and sha256_file(target) == db["sha256"]):
            say(f"Downloading {db['key']} ({human(db['size'])}) ...")
            handover.download(db["key"], target)
        if sha256_file(target) != db["sha256"]:
            problems.append(db["key"])
        else:
            say(f"  verified {db['file']}")
    for group, info in manifest["groups"].items():
        group_dir = args.to / group
        archives = args.to / ".parts" / group
        for part in info["parts"]:
            local = archives / Path(part["key"]).name
            if not (local.is_file() and local.stat().st_size == part["size"] and sha256_file(local) == part["sha256"]):
                say(f"Downloading {part['key']} ({human(part['size'])}) ...")
                handover.download(part["key"], local)
            if sha256_file(local) != part["sha256"]:
                problems.append(part["key"])
                continue
            if not args.no_unpack:
                safe_extract(local, group_dir)
                bad = verify_unpacked(group_dir, part["files"])
                if bad:
                    problems.append(f"{part['key']} (unpacked files differ: {', '.join(bad[:5])})")
        say(f"  {group}: {info['files']} files, {human(info['bytes'])} {'verified' if not args.no_unpack else 'downloaded'}")
    for report in manifest.get("reports", []):
        handover.download(report, args.to / "reports" / Path(report).name)
    if problems:
        fail("These did not verify; run the command again (it keeps what verified): " + "; ".join(problems[:10]))
    left_out = {g: v for g, v in manifest.get("left_out", {}).items() if v}
    if left_out:
        say("Left out of the pack on the sending machine (credentials), by name: " + "; ".join(f"{g}: {len(v)} file(s)" for g, v in left_out.items()))
    say(f"Handover {args.stamp} downloaded and verified into {args.to}")
    say(restore_notes(manifest, args.to))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
