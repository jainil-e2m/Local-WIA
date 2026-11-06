"""`storage_cli documents|people|clients|glossary|identities ...`: the operator's commands for Phase 1 (identities: N8; removal on
request: 6.B12, `clients remove`)."""
from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path


def _when(text: str) -> datetime:
    value = datetime.fromisoformat(text)
    if value.tzinfo is None:
        raise SystemExit("Give dates with an explicit offset, such as 2026-03-09T00:00:00-05:00")
    return value


def add_cli(sub) -> None:
    documents = sub.add_parser("documents", help="Documents: import, normalise, classify, date, embed, select (Phase 1)")
    d = documents.add_subparsers(dest="documents_command", required=True)
    p = d.add_parser("import", help="Import a folder of transcripts as week-less documents (idempotent)")
    p.add_argument("directory", type=Path)
    p.add_argument("--source-type", default="zoom", choices=["zoom", "manual", "file"])
    p = d.add_parser("fathom-backfill", help="Fathom calls recorded before the collector's activation: list them through the API, "
                     "write native Fathom folders, import, normalise by the rules and estimate the embedding (6.B18)")
    p.add_argument("--from", dest="start", type=date.fromisoformat, required=True, help="First calendar day, YYYY-MM-DD")
    p.add_argument("--to", dest="end", type=date.fromisoformat, required=True, help="Last calendar day (included), YYYY-MM-DD")
    p.add_argument("--timezone", default="America/Chicago", help="The zone the days are read in (WIA's, by default)")
    p.add_argument("--out", type=Path, required=True, help="Where the folders are written: outside the repository (R48)")
    only = p.add_mutually_exclusive_group()
    only.add_argument("--dry-run", action="store_true", help="List the meetings and what would happen; fetch and write nothing")
    only.add_argument("--estimate", action="store_true", help="As --dry-run, plus the paid steps' estimate for what is stored")
    p.add_argument("--embed", choices=["cached", "live"], help="Also queue the embedding (a live run spends only under a run plan)")
    p.add_argument("--actor", default="local-cli")
    p = d.add_parser("slack-export", help="Import a Slack workspace export (folder or zip), one document per thread")
    p.add_argument("path", type=Path)
    p.add_argument("--workspace", default="")
    p = d.add_parser("normalise", help="Queue (or with --now, run) the normalise job for documents")
    p.add_argument("--ids", nargs="*")
    p.add_argument("--all", action="store_true", help="Every document, including already normalised ones (after the roster, clients or glossary changed)")
    p.add_argument("--now", action="store_true", help="Run inline instead of queueing")
    p.add_argument("--estimate", action="store_true", help="Count the classification model calls and tokens first; queue nothing")
    p = d.add_parser("classify", help="A person sets a document's call type (never overwritten by a rule)")
    p.add_argument("transcript_id")
    p.add_argument("--call-type", required=True)
    p.add_argument("--reason", required=True)
    p.add_argument("--include", dest="included", action="store_true", default=None)
    p.add_argument("--exclude", dest="included", action="store_false")
    p.add_argument("--actor", required=True)
    p = d.add_parser("dates", help="Date undated documents from evidence (Zoom recording list, calendar export, names, "
                                      "spoken cues inside a Zoom week folder)")
    p.add_argument("--zoom-listing", type=Path, help="Zoom recording or meeting list exported as CSV")
    p.add_argument("--zoom-timezone", help="The Zoom account's time zone (required with --zoom-listing)")
    p.add_argument("--calendar", type=Path, help="A calendar export, .ics or CSV")
    p.add_argument("--calendar-timezone", default="UTC")
    p.add_argument("--apply", action="store_true", help="Write the dates; without it, only report what would be set")
    d.add_parser("report", help="Counts: sources, call types, inclusion, dates, extraction, chunks and the embedding contract")
    p = d.add_parser("team-practice", help="Admit internal meetings as team-practice evidence (D24): those excluded only for being internal")
    p.add_argument("--actor", required=True)
    p.add_argument("--apply", action="store_true", help="Include them; without it, list what would be admitted and what stays out")
    p = d.add_parser("reembed", help="Estimate or queue the encoding of current chunks that have no vector")
    p.add_argument("--estimate", action="store_true")
    p.add_argument("--mode", choices=["cached", "live"], default="cached")
    p.add_argument("--ids", nargs="*")
    p.add_argument("--actor", default="local-cli")
    p = d.add_parser("select", help="Select documents by date window or explicit set and queue a cycle's extraction")
    p.add_argument("--from", dest="start")
    p.add_argument("--to", dest="end")
    p.add_argument("--ids", nargs="*")
    p.add_argument("--mode", choices=["replay", "live", "synthetic"], default="replay")
    p.add_argument("--dry-run", action="store_true", help="List what would be selected and queue nothing")
    p.add_argument("--actor", default="local-cli")
    p = d.add_parser("unlink", help="Say a document is not a copy of its canonical document")
    p.add_argument("transcript_id")
    p.add_argument("--actor", required=True)
    p = d.add_parser("agreement", help="Compare our call types with the Command Center corpus index (corpus/zoom/transcripts.json)")
    p.add_argument("index", type=Path)

    people = sub.add_parser("people", help="People: mirror the confirmed roster (1.B2)")
    pp = people.add_subparsers(dest="people_command", required=True)
    pp.add_parser("sync", help="Bring people into agreement with the confirmed roster (or the roster document)")
    pp.add_parser("check", help="Does every roster staff member have a people row, and the reverse?")
    clients = sub.add_parser("clients", help="Clients from a reviewed list kept outside the repository (1.B2)")
    cc = clients.add_subparsers(dest="clients_command", required=True)
    p = cc.add_parser("import")
    p.add_argument("--file", type=Path, required=True)
    p.add_argument("--update-consent", action="store_true", help="Let the list change an existing client's consent")
    p = cc.add_parser("remove", help="Removal on request (6.B12): delete one client's documents, chunks and scenes, and mark "
                      "every card, brief and pack built on them; prints what it would do first")
    p.add_argument("--client-id", required=True)
    p.add_argument("--actor", required=True, help="Who removes it (recorded); the real run needs an administrator")
    p.add_argument("--dry-run", action="store_true", help="Only show what would be removed and marked")
    p.add_argument("--confirm", metavar="CLIENT_ID", help="The client id again: without it nothing is removed")
    p.add_argument("--delete-account", action="store_true",
                   help="Also unlink the client's people and delete the client row (default: keep it with consent no_use)")
    glossary = sub.add_parser("glossary", help="Names and their mis-transcriptions (1.B12)")
    gg = glossary.add_subparsers(dest="glossary_command", required=True)
    p = gg.add_parser("add")
    p.add_argument("term")
    p.add_argument("--kind", default="other", choices=["product", "staff", "client", "other"])
    p.add_argument("--variant", action="append", default=[])
    p = gg.add_parser("import")
    p.add_argument("--file", type=Path, required=True)
    gg.add_parser("refresh", help="Recompute every current chunk's search copy after the glossary changed")
    identities = sub.add_parser("identities", help="People and accounts with aliases, pronouns, staff dates and naming flags (1.B12)")
    ii = identities.add_subparsers(dest="identities_command", required=True)
    p = ii.add_parser("import", help="Load a reviewed identities file (clients, people, staff dates)")
    p.add_argument("--file", type=Path, required=True)
    p.add_argument("--actor", required=True, help="Who reviewed the list (recorded on every identity)")
    p.add_argument("--update-consent", action="store_true", help="Let the file change an existing client's consent")
    p = ii.add_parser("apply", help="Re-normalise the documents whose speakers or client the list now resolves differently")
    p.add_argument("--dry-run", action="store_true")
    p = ii.add_parser("show", help="The identities a set of documents carries, as the strategist and the writer read them")
    p.add_argument("--document", action="append", default=[])


def run_cli(args, storage, models) -> dict:
    from ..repository import ContentRepository
    repo = ContentRepository(storage)
    command = args.command
    if command == "people":
        return _people(repo, args, models)
    if command == "clients" and args.clients_command == "remove":
        from .. import removal
        try:
            return removal.run(repo, args.client_id, args.actor, confirm=args.confirm, dry_run=args.dry_run,
                               delete_account=args.delete_account)
        except (LookupError, ValueError, PermissionError) as error:
            raise SystemExit(str(error)) from None
    if command == "clients":
        from .. import reference
        with repo.connection() as conn:
            return reference.import_clients(conn, args.file, update_consent=args.update_consent)
    if command == "glossary":
        return _glossary(repo, args)
    if command == "identities":
        return _identities(repo, args)
    return _documents(repo, args, models)


def _identities(repo, args) -> dict:
    from .. import identities
    if args.identities_command == "import":
        with repo.connection() as conn:
            return identities.import_file(conn, args.file, actor=args.actor, update_consent=args.update_consent)
    if args.identities_command == "apply":
        return identities.apply(repo, dry_run=args.dry_run)
    with repo.connection() as conn:
        found = identities.notes(conn, document_ids=args.document)
    return {"identities": found, "prompt_lines": identities.prompt_lines(found)}


def _people(repo, args, models) -> dict:
    from .. import reference
    with repo.connection() as conn:
        if args.people_command == "sync":
            return reference.sync_roster(conn, models.knowledge_base_root)
        return reference.roster_agreement(conn, models.knowledge_base_root)


def _glossary(repo, args) -> dict:
    from .. import reference
    from ..normalise.glossary import refresh_search_text
    with repo.connection() as conn:
        if args.glossary_command == "add":
            term_id = reference.add_glossary_term(conn, args.term, args.kind, args.variant)
            return {"term_id": term_id, "chunks_updated": refresh_search_text(conn)}
        if args.glossary_command == "import":
            return {**reference.import_glossary(conn, args.file), "chunks_updated": refresh_search_text(conn)}
        return {"chunks_updated": refresh_search_text(conn)}


def _documents(repo, args, models) -> dict:
    sub = args.documents_command
    if sub == "import":
        from .intake import import_directory
        return import_directory(repo, args.directory, source_type=args.source_type)
    if sub == "fathom-backfill":
        return _fathom_backfill(repo, args, models)
    if sub == "slack-export":
        from .slack_export import import_export
        return import_export(repo, args.path, workspace=args.workspace)
    if sub == "normalise":
        return _normalise(repo, args, models)
    if sub == "classify":
        from .api import ClassificationRequest, classify_by_person
        done = classify_by_person(repo, args.transcript_id, ClassificationRequest(
            call_type=args.call_type, included=args.included, reason=args.reason), args.actor, models)
        return {k: done[k] for k in ("transcript_id", "call_type", "included", "exclusion_reason", "classification")}
    if sub == "dates":
        return _dates(repo, args)
    if sub == "team-practice":
        from .team_practice import admit
        return admit(repo, actor=args.actor, apply=args.apply)
    if sub == "report":
        return _report(repo, models)
    if sub == "reembed":
        from . import reembed
        if args.estimate:
            with repo.connection() as conn:
                return reembed.estimate(conn, args.ids)
        return reembed.queue(repo, models, transcript_ids=args.ids, mode=args.mode, actor=args.actor)
    if sub == "select":
        return _select(repo, args, models)
    if sub == "unlink":
        from . import duplicates
        with repo.connection() as conn:
            duplicates.unlink(conn, args.transcript_id, actor=args.actor)
        return {"transcript_id": args.transcript_id, "unlinked": True}
    return _agreement(repo, args)


def fathom_client():
    """The live collector's client, with the key from the environment (`ATELIER_FATHOM_API_KEY`, else `FATHOM_API_KEY`)."""
    from ..intake.config import IntakeSettings, fathom_api_key
    from ..intake.fathom import FathomClient
    key = fathom_api_key()
    if not key:
        raise SystemExit("Set ATELIER_FATHOM_API_KEY (or FATHOM_API_KEY) to the Fathom key first")
    return FathomClient(IntakeSettings(fathom_key=key))


def _fathom_backfill(repo, args, models) -> dict:
    from . import fathom_backfill
    start, end = fathom_backfill.window(args.start, args.end, args.timezone)
    client = fathom_client()
    try:
        return fathom_backfill.run(repo, models, client, start=start, end=end, out=args.out, timezone=args.timezone,
                                   dry_run=args.dry_run, estimate=args.estimate, embed=args.embed, actor=args.actor)
    finally:
        client.close()


def _normalise(repo, args, models) -> dict:
    from ..normalise import NORMALISER_VERSION
    from .intake import queue_normalisation
    from .jobs import normalise
    with repo.connection() as conn:
        if args.ids:
            ids = args.ids
        elif args.all:
            ids = [r["transcript_id"] for r in conn.execute("SELECT transcript_id FROM transcripts ORDER BY transcript_id")]
        else:
            ids = [r["transcript_id"] for r in conn.execute("SELECT transcript_id FROM transcripts WHERE normalised_at IS NULL ORDER BY transcript_id")]
    if args.estimate:
        from .jobs import classification_estimate
        return classification_estimate(repo, ids, models)
    if args.now:
        # Inline runs ask the model exactly as the queued job does (it was never given a provider, so a configured
        # classification model was silently skipped and every ambiguous call waited for a person).
        from .jobs import classification_provider
        provider = classification_provider(models, repo.settings)
        return {"normalised": [normalise(repo, i, models=models, provider=provider) for i in ids]}
    salt = datetime.now().isoformat() if (args.all or args.ids) else NORMALISER_VERSION
    with repo.connection() as conn:
        queued = queue_normalisation(conn, ids, actor="local-cli", version=NORMALISER_VERSION + ":" + salt)
    return {"documents": len(ids), "run_id": queued["run_id"], "jobs": len(queued["jobs"])}


def _dates(repo, args) -> dict:
    from ..normalise import dates
    if bool(args.zoom_listing) != bool(args.zoom_timezone):
        raise SystemExit("--zoom-listing and --zoom-timezone go together: the export shows local times without a zone")
    events = []
    if args.zoom_listing:
        events += dates.read_zoom_listing(args.zoom_listing, args.zoom_timezone)
    if args.calendar:
        events += dates.read_calendar(args.calendar, args.calendar_timezone)
    changes, left, to_week, examined = [], 0, 0, []
    with repo.connection() as conn:
        # Window-aware: an event inside a document's week folder competes only with that week's documents (1.B11).
        events, contested = dates.exclusive(conn.execute("SELECT * FROM transcripts").fetchall(), events)
        for row in conn.execute("SELECT * FROM transcripts WHERE occurred_at IS NULL AND occurred_at_source IS DISTINCT FROM 'manual' ORDER BY transcript_id").fetchall():
            result = dates.resolve(row, events, names=(row["source_metadata"].get("filename") or "",))
            examined.append({"transcript_id": row["transcript_id"], "title": row["title"], "source": result.source,
                             "occurred_at": result.occurred_at.isoformat() if result.occurred_at else None,
                             "window": result.window.record() if result.window else None, "detail": result.detail,
                             "conflicts": list(result.conflicts)})
            if result.occurred_at is None:
                left += 1
                to_week += result.window is not None
                if args.apply:
                    dates.apply(conn, row["transcript_id"], result)
                continue
            changes.append({"transcript_id": row["transcript_id"], "source": result.source, "occurred_at": result.occurred_at.isoformat(),
                            "detail": result.detail, "conflicts": list(result.conflicts),
                            "window": result.window.record() if result.window else None})
            if args.apply and dates.apply(conn, row["transcript_id"], result) and row["normalised_at"] is not None:
                # The chunk headers name the date: re-segment now, before the planned re-embedding reads them (1.B6).
                from .jobs import resegment
                resegment(conn, row["transcript_id"])
        report = dates.report(conn)
    return {"applied": args.apply, "dated": len(changes), "still_undated": left, "dated_to_week": to_week, "changes": changes,
            "documents": examined, "report": report,
            "events_fitting_several_documents": [{"title": e.title, "start": e.start.isoformat(), "origin": e.origin} for e in contested]}


def _report(repo, models) -> dict:
    from ..normalise import dates
    from . import reembed
    with repo.connection() as conn:
        return {
            "documents": conn.execute("""SELECT count(*) total, count(*) FILTER (WHERE normalised_at IS NULL) AS not_normalised,
                count(*) FILTER (WHERE included) AS included, count(*) FILTER (WHERE canonical_document_id IS NOT NULL) AS copies,
                count(*) FILTER (WHERE classification->>'needs_review'='true') AS needing_a_person FROM transcripts""").fetchone(),
            "by_call_type": {r["k"]: r["n"] for r in conn.execute(
                "SELECT COALESCE(call_type,'unclassified') k,count(*) n FROM transcripts GROUP BY 1 ORDER BY 1")},
            "excluded": conn.execute("SELECT exclusion_reason AS reason,count(*) n FROM transcripts WHERE NOT included GROUP BY 1 ORDER BY 2 DESC").fetchall(),
            "dates": dates.report(conn),
            "extraction": {r["k"]: r["n"] for r in conn.execute(
                "SELECT extraction_status k,count(*) n FROM transcripts WHERE included GROUP BY 1 ORDER BY 1")},
            "embedding": reembed.contract_report(conn, models), "pending_embedding": reembed.estimate(conn)}


def _select(repo, args, models) -> dict:
    from . import select
    if args.dry_run:
        with repo.connection() as conn:
            rows = select.by_set(conn, args.ids) if args.ids else select.by_window(conn, _when(args.start), _when(args.end))
        return {"selected": [{"transcript_id": r["transcript_id"], "title": r["title"], "occurred_at": r["occurred_at"]} for r in rows]}
    if args.ids:
        return select.submit_window(repo, models, transcript_ids=args.ids, mode=args.mode, actor=args.actor)
    return select.submit_window(repo, models, window_start=_when(args.start), window_end=_when(args.end) if args.end else None,
                                mode=args.mode, actor=args.actor)


def _agreement(repo, args) -> dict:
    from ..normalise.classify import agreement
    index = json.loads(Path(args.index).read_text(encoding="utf-8"))
    kinds = {entry["contentHash"]: entry["kind"] for entry in index}
    pairs, uncovered = [], []
    with repo.connection() as conn:
        for row in conn.execute("SELECT transcript_id,title,content_hash,call_type,classification FROM transcripts WHERE call_type IS NOT NULL").fetchall():
            kind = kinds.get(row["content_hash"][:16])
            if kind is None:
                uncovered.append({"transcript_id": row["transcript_id"], "title": row["title"], "call_type": row["call_type"],
                                  "method": (row["classification"] or {}).get("method")})
            else:
                pairs.append((row["transcript_id"], row["call_type"], kind))
    return {**agreement(pairs), "not_covered_by_the_index": uncovered,
            "note": "Each disagreement and each uncovered document is resolved by a person: documents classify <id> --call-type ..."}
