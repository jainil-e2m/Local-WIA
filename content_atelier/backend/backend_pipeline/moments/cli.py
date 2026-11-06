"""`storage_cli moments ...`: the operator's commands for the moments ledger (plan Phase 2).

    moments extract   queue (or estimate) the extraction of documents; the backfill is this command, not a run (2.B11)
    moments report    the numbers and invariants of what was extracted
    moments recheck   re-derive speaker, role, client, evidence kind, consent and checks for stored moments (2.B4)
    moments recall    scene recall against a golden file, comparable between scene profiles
    moments import-saved   import the saved Week 1 and 2 extraction responses with their provenance (2.B10)
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path


def _when(text: str) -> datetime:
    value = datetime.fromisoformat(text)
    if value.tzinfo is None:
        raise SystemExit("Give dates with an explicit offset, such as 2026-03-09T00:00:00-05:00")
    return value


def add_cli(sub) -> None:
    moments = sub.add_parser("moments", help="The moments ledger: extract, report, recheck, recall, import-saved (Phase 2)")
    m = moments.add_subparsers(dest="moments_command", required=True)
    p = m.add_parser("extract", help="Queue the extraction of included documents, one job each (never a paid call without --mode live "
                                     "and an active run plan); --estimate first")
    p.add_argument("--ids", nargs="*", help="Exactly these documents")
    p.add_argument("--week-index", nargs="*", type=int, help="The included documents of these admission weeks (the benchmark's "
                   "Zoom weeks carry no date); with --from and --to, the window's documents are added")
    p.add_argument("--from", dest="start", help="Documents that occurred from this moment (with an offset)")
    p.add_argument("--to", dest="end", help="... until this moment, exclusive (with --from)")
    p.add_argument("--all-pending", action="store_true", help="Every included document this scene profile has not extracted (or whose extraction failed), "
                   "including documents a weekly run read")
    p.add_argument("--pilot", type=int, metavar="N", help="Only N of the selected documents, spread over the call types, "
                   "each type oldest first (default selection: all pending)")
    p.add_argument("--estimate", action="store_true", help="Count documents and input tokens and estimate the cost; calls nothing")
    p.add_argument("--mode", choices=["cached", "live", "synthetic"], default="cached",
                   help="cached: saved responses only, never a call; live: a paid run under an active run plan; synthetic: offline provider")
    p.add_argument("--profile", help="Scene profile (default: the moments.extraction_profile setting)")
    p.add_argument("--queue", choices=["bulk", "default"], default="bulk", help="bulk for a backfill, default for a cycle")
    p.add_argument("--retry-failed", action="store_true", help="Queue again the documents whose job failed")
    p.add_argument("--now", action="store_true", help="Run the jobs inline instead of leaving them to the queue workers")
    p.add_argument("--actor", default="local-cli")
    p = m.add_parser("report", help="Verified-quote share, repairs, roles, types, per call type, zero-scene documents, invariants")
    p.add_argument("--extractor", help="Only this extractor version (compare profiles)")
    p = m.add_parser("recheck", help="Re-derive speaker, role, client, evidence kind, consent and checks for stored moments")
    p.add_argument("--ids", nargs="*", help="These moments")
    p.add_argument("--document", nargs="*", help="The moments of these documents")
    p.add_argument("--client", help="The moments of this client")
    p.add_argument("--dry-run", action="store_true", help="Report what would change and change nothing")
    p = m.add_parser("recall", help="Scene recall against golden scenes, per extractor version")
    p.add_argument("--golden", type=Path, required=True)
    p.add_argument("--profile", nargs="*", help="Extractor versions to compare (default: every one stored for the golden documents)")
    p = m.add_parser("import-saved", help="Import saved file-backed extraction responses (Weeks 1 and 2) as ledger rows; no provider call")
    p.add_argument("path", type=Path, help="A folder holding the saved artifacts (or one artifact file)")
    p.add_argument("--dry-run", action="store_true", help="Report what would be stored and store nothing")
    p.add_argument("--include-failed", action="store_true",
                   help="Also re-check failed attempts' received responses moment by moment (E.B12a); a validated artifact wins")
    p.add_argument("--actor", default="local-cli")


def run_cli(args, storage, models) -> dict:
    from ..repository import ContentRepository
    repo = ContentRepository(storage)
    sub = args.moments_command
    if sub == "extract":
        return _extract(repo, args, models)
    if sub == "report":
        from . import report
        with repo.connection() as conn:
            return report.report(conn, extractor_version=args.extractor)
    if sub == "recheck":
        from . import recheck
        return recheck.recheck(repo, ids=args.ids or None, document_ids=args.document or None, client_id=args.client, apply=not args.dry_run)
    if sub == "recall":
        from . import recall
        golden = recall.load_golden(args.golden)
        with repo.connection() as conn:
            return recall.compare(conn, golden, args.profile or None)
    from . import imports
    return imports.import_saved(repo, args.path, actor=args.actor, apply=not args.dry_run, include_failed=args.include_failed)


def select_documents(repo, args, profile: str | None = None) -> list[dict]:
    from ..documents import select
    from . import queue
    with repo.connection() as conn:
        if getattr(args, "week_index", None):
            # E.B31's re-extraction: the benchmark weeks by their admission week, plus a dated window when one is given.
            documents = conn.execute(f"""SELECT * FROM transcripts WHERE {select.SELECTABLE}
                AND (source_metadata->>'week_index')::int = ANY(%s) ORDER BY transcript_id""", (list(args.week_index),)).fetchall()
            if args.start or args.end:
                if not (args.start and args.end):
                    raise SystemExit("--from and --to go together")
                seen = {d["transcript_id"] for d in documents}
                documents += [d for d in select.by_window(conn, _when(args.start), _when(args.end)) if d["transcript_id"] not in seen]
        elif args.ids:
            documents = select.by_set(conn, args.ids)
        elif args.start or args.end:
            if not (args.start and args.end):
                raise SystemExit("--from and --to go together")
            documents = select.by_window(conn, _when(args.start), _when(args.end))
        elif args.all_pending or args.pilot:
            documents = queue.pending_documents(conn, profile)
        else:
            raise SystemExit("Name the documents: --ids, --from and --to, --all-pending or --pilot N")
    return queue.pilot(documents, args.pilot) if args.pilot else documents


def _extract(repo, args, models) -> dict:
    from . import queue
    with repo.connection() as conn:
        from ..settings_store import value
        profile = args.profile or value("moments.extraction_profile", conn)
    # The backfill's selection (--all-pending, --pilot) is what this profile has not extracted yet.
    documents = select_documents(repo, args, profile)
    mode = queue.MODES[args.mode]
    if args.estimate:
        return queue.estimate(repo, models, documents, profile=profile, mode=mode)
    result = queue.queue_extraction(repo, models, documents, mode=mode, actor=args.actor, queue=args.queue, profile=profile,
                                    retry_failed=args.retry_failed)
    if not result["run_id"] and not result["retried"]:
        return {**result, "selected": len(documents)}
    if args.now:
        from ..sql_pipeline import SQLWorker
        worker, done = SQLWorker(repo.settings, models), []
        while job := worker.once(run_id=result["run_id"]):
            done.append(job)
        with repo.connection() as conn:
            states = {r["status"]: r["n"] for r in conn.execute(
                "SELECT status,count(*) AS n FROM pipeline_jobs WHERE run_id=%s GROUP BY 1", (result["run_id"],))}
        return {**result, "selected": len(documents), "ran": len(done), "job_states": states}
    from ..jobs.dispatch import kick
    kick(repo, run_id=result["run_id"])
    return {**result, "selected": len(documents)}


