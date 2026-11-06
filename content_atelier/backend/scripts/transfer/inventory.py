"""Read-only inventory of a machine that holds Content Atelier data (plan 7.B3).

Writes `inventory-report.json` and `inventory-report.md` to the output folder. The report holds sizes, counts, schema versions,
the NAMES of environment variables (never their values) and git state. It holds no secret and no client text: a transcript
folder is reported by path, file count and bytes only. Nothing is changed, copied or sent anywhere.

    python scripts/transfer/inventory.py --repo .. --database atelier=postgresql://atelier:PASSWORD@127.0.0.1:15432/atelier
        [--database intake=postgresql://...] [--artifacts backend/.storage-artifacts] [--search-dir ~/Desktop] [--out transfer-work]

A database URL may be given as `--database name=URL`; the password can be left out and supplied by PGPASSWORD.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import EXCLUDED_DIRS, human, secret_in, say, walk  # noqa: E402

TRANSCRIPT_SUFFIXES = {".vtt", ".webvtt", ".srt"}
TRANSCRIPT_NAMES = {"transcript.raw.json", "transcript.json"}
ENV_VAR = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=", re.M)
KEY_TABLES = ("transcripts", "transcript_chunks", "key_moments", "content_angles", "content_briefs", "pipeline_runs", "pipeline_jobs")


def redact(url: str) -> str:
    """The URL without its password."""
    parts = urlsplit(url)
    if parts.password:
        netloc = f"{parts.username}:***@{parts.hostname}" + (f":{parts.port}" if parts.port else "")
        return urlunsplit(parts._replace(netloc=netloc))
    return url


def database_report(name: str, url: str) -> dict:
    try:
        import psycopg
        from psycopg.rows import dict_row
    except ImportError:
        return {"name": name, "error": "psycopg is not installed here; run this from the backend virtual environment (pip install -r requirements.txt)"}
    report: dict = {"name": name, "url": redact(url)}
    try:
        with psycopg.connect(url, row_factory=dict_row, connect_timeout=10) as conn:
            conn.read_only = True
            report["server_version"] = conn.execute("SHOW server_version").fetchone()["server_version"]
            report["size_bytes"] = conn.execute("SELECT pg_database_size(current_database()) n").fetchone()["n"]
            ext = conn.execute("SELECT extversion FROM pg_extension WHERE extname='vector'").fetchone()
            report["pgvector"] = ext["extversion"] if ext else None
            tables = [r["tablename"] for r in conn.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY 1")]
            report["tables"] = {t: conn.execute(f'SELECT count(*) n FROM "{t}"').fetchone()["n"] for t in tables}
            if "schema_migrations" in tables:
                report["schema_versions"] = [r["version"] for r in conn.execute("SELECT version FROM schema_migrations ORDER BY version")]
            else:
                report["schema_versions"] = None
            if "transcript_chunks" in tables:
                cols = {r["column_name"] for r in conn.execute(
                    "SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name='transcript_chunks'")}
                row = conn.execute("SELECT count(*) FILTER (WHERE embedding IS NOT NULL) embedded, count(*) total FROM transcript_chunks").fetchone()
                report["chunk_embeddings"] = {"embedded": row["embedded"], "chunks": row["total"]}
                if "embedding_model" in cols:
                    report["chunk_embedding_models"] = {str(r["m"]): r["n"] for r in conn.execute(
                        "SELECT embedding_model m, count(*) n FROM transcript_chunks WHERE embedding IS NOT NULL GROUP BY 1")}
                dims = conn.execute("SELECT vector_dims(embedding) d, count(*) n FROM transcript_chunks WHERE embedding IS NOT NULL GROUP BY 1").fetchall() \
                    if report["pgvector"] else []
                report["chunk_embedding_dimensions"] = {str(r["d"]): r["n"] for r in dims}
            if "transcripts" in tables:
                cols = {r["column_name"] for r in conn.execute(
                    "SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name='transcripts'")}
                report["transcripts_by_source_type"] = {str(r["s"]): r["n"] for r in conn.execute(
                    "SELECT source_type s, count(*) n FROM transcripts GROUP BY 1 ORDER BY 1")}
                if "occurred_at" in cols:
                    report["transcripts_dated"] = conn.execute("SELECT count(*) FILTER (WHERE occurred_at IS NOT NULL) dated, count(*) total FROM transcripts").fetchone()
            report["key_table_counts"] = {t: report["tables"].get(t) for t in KEY_TABLES}
    except Exception as error:
        report["error"] = f"{type(error).__name__}: {str(error)[:300]}"
    return report


def tree_report(root: Path, *, secrets: bool = True) -> dict:
    root = Path(root)
    if not root.is_dir():
        return {"path": str(root), "exists": False}
    top: dict[str, dict] = {}
    suffixes: dict[str, int] = {}
    files = size = 0
    flagged = []
    for path, rel in walk(root):
        n = path.stat().st_size
        files, size = files + 1, size + n
        group = rel.split("/", 1)[0] if "/" in rel else "(top level)"
        entry = top.setdefault(group, {"files": 0, "bytes": 0})
        entry["files"] += 1
        entry["bytes"] += n
        suffixes[path.suffix.lower() or "(none)"] = suffixes.get(path.suffix.lower() or "(none)", 0) + 1
        if secrets and (kind := secret_in(path)):
            flagged.append({"file": rel, "looks_like": kind})
    return {"path": str(root), "exists": True, "files": files, "bytes": size, "size": human(size),
            "top_level": dict(sorted(top.items())), "by_suffix": dict(sorted(suffixes.items(), key=lambda kv: -kv[1])[:15]),
            "files_that_look_like_they_hold_a_credential": flagged}


def env_files(repo: Path) -> list[dict]:
    found = []
    for folder in (repo, repo / "backend", repo / "frontend", repo.parent):
        if not folder.is_dir():
            continue
        for path in sorted(set(folder.glob(".env*")) | set(folder.glob("*.env"))):
            if path.is_file():
                text = path.read_text(encoding="utf-8", errors="replace")
                names = sorted(set(ENV_VAR.findall(text)))
                filled = sorted(n for n in names if re.search(rf"^[ 	]*(?:export[ 	]+)?{re.escape(n)}[ 	]*=[ 	]*[^\s#]", text, re.M))
                found.append({"file": str(path), "variable_names": names, "names_with_a_value": filled})
    return found


def git(repo: Path, *args: str) -> str:
    try:
        done = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, timeout=60)
        return done.stdout.strip() if done.returncode == 0 else f"(git failed: {done.stderr.strip()[:200]})"
    except (OSError, subprocess.SubprocessError) as error:
        return f"(git unavailable: {error})"


def git_report(repo: Path) -> dict:
    if not (repo / ".git").exists():
        return {"repository": False, "path": str(repo)}
    remotes = re.sub(r"//[^/@\s]+@", "//***@", git(repo, "remote", "-v"))
    status = git(repo, "status", "--porcelain=v1").splitlines()
    return {"repository": True, "path": str(repo), "head": git(repo, "rev-parse", "--short", "HEAD"), "branch": git(repo, "branch", "--show-current"),
            "remotes": remotes.splitlines(),
            "branches": git(repo, "for-each-ref", "--format=%(refname:short)|%(upstream:short)|%(upstream:track)", "refs/heads").splitlines(),
            "commits_not_on_any_remote": git(repo, "log", "--branches", "--not", "--remotes", "--oneline").splitlines(),
            "stashes": git(repo, "stash", "list").splitlines(),
            "uncommitted_or_untracked_files": [line for line in status if not line.startswith("!!")],
            "worktrees": git(repo, "worktree", "list").splitlines()}


def transcript_folders(search: list[Path], minimum: int = 5) -> list[dict]:
    """Folders that hold at least `minimum` transcript-like files. Paths, counts and bytes only; no text is read."""
    found = {}
    for base in search:
        if not base.is_dir():
            continue
        for current, dirs, files in __import__("os").walk(base):
            dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS and not d.startswith(".")]
            hits = [f for f in files if Path(f).suffix.lower() in TRANSCRIPT_SUFFIXES or f in TRANSCRIPT_NAMES]
            if len(hits) >= minimum:
                found[current] = {"path": current, "transcript_files": len(hits), "bytes": sum((Path(current) / f).stat().st_size for f in hits)}
    return sorted(found.values(), key=lambda e: e["path"])


def markdown(report: dict) -> str:
    lines = [f"# Inventory of {report['machine']}", "", f"Taken {report['taken_at']}. Read-only; no secret and no client text.", ""]
    for db in report["databases"]:
        lines += [f"## Database `{db['name']}`", ""]
        if "error" in db:
            lines += [f"Could not read it: {db['error']}", ""]
            continue
        lines += [f"- Server {db['server_version']}, pgvector {db['pgvector']}, {human(db['size_bytes'])}",
                  f"- Schema versions recorded: {db['schema_versions']}"]
        if "chunk_embeddings" in db:
            lines.append(f"- Chunk embeddings: {db['chunk_embeddings']['embedded']} of {db['chunk_embeddings']['chunks']}; models {db.get('chunk_embedding_models')}; dimensions {db.get('chunk_embedding_dimensions')}")
        lines += ["- Key tables: " + ", ".join(f"{k} {v}" for k, v in db["key_table_counts"].items()), "- All tables: " + ", ".join(f"{k} {v}" for k, v in db["tables"].items()), ""]
    for tree in report["artifact_trees"]:
        lines += [f"## Artifact tree `{tree['path']}`", ""]
        if not tree["exists"]:
            lines += ["Not found.", ""]
            continue
        lines += [f"- {tree['files']} files, {tree['size']}", "- Top level: " + ", ".join(f"{k} ({v['files']} files, {human(v['bytes'])})" for k, v in tree["top_level"].items())]
        if tree["files_that_look_like_they_hold_a_credential"]:
            lines.append("- **Files that look like they hold a credential (they will be left out of the pack):** " + ", ".join(f["file"] for f in tree["files_that_look_like_they_hold_a_credential"]))
        lines.append("")
    lines += ["## Transcript-like folders found", ""] + [f"- `{f['path']}`: {f['transcript_files']} files, {human(f['bytes'])}" for f in report["transcript_folders"]] + [""]
    lines += ["## Environment files (variable names only)", ""] + [f"- `{e['file']}`: {', '.join(e['names_with_a_value']) or 'no value set'}" for e in report["environment_files"]] + [""]
    g = report["git"]
    lines += ["## Git", ""]
    if g.get("repository"):
        lines += [f"- {g['path']} at {g['head']} on {g['branch']}", f"- Commits on no remote: {len(g['commits_not_on_any_remote'])}", f"- Stashes: {len(g['stashes'])}",
                  f"- Uncommitted or untracked files: {len(g['uncommitted_or_untracked_files'])}"]
        lines += [f"  - {x}" for x in g["commits_not_on_any_remote"][:30]] + [f"  - {x}" for x in g["uncommitted_or_untracked_files"][:50]]
    else:
        lines.append("Not a git checkout.")
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo", type=Path, default=Path(".."), help="The WIA-Content-Atelier checkout (default ..: run from backend/)")
    parser.add_argument("--database", action="append", default=[], metavar="NAME=URL")
    parser.add_argument("--artifacts", type=Path, action="append", default=[], help="An artifact tree (default <repo>/backend/.storage-artifacts)")
    parser.add_argument("--search-dir", type=Path, action="append", default=[], help="Where to look for other transcript folders (the Zoom backfill)")
    parser.add_argument("--out", type=Path, default=Path("transfer-work"))
    args = parser.parse_args(argv)
    repo = args.repo.resolve()
    artifacts = [p.resolve() for p in args.artifacts] or [repo / "backend" / ".storage-artifacts"]
    databases = []
    for item in args.database:
        name, _, url = item.partition("=")
        if not url:
            raise SystemExit("--database needs NAME=URL")
        databases.append(database_report(name, url))
    report = {"taken_at": datetime.now(UTC).isoformat(timespec="seconds"), "machine": __import__("platform").node(),
              "databases": databases, "artifact_trees": [tree_report(p) for p in artifacts],
              "transcript_folders": transcript_folders([repo, *[p.resolve() for p in args.search_dir]]),
              "environment_files": env_files(repo), "git": git_report(repo)}
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "inventory-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (args.out / "inventory-report.md").write_text(markdown(report), encoding="utf-8")
    say(f"Wrote {args.out / 'inventory-report.md'} and inventory-report.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
