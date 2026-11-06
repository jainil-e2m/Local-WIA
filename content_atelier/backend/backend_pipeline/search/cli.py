"""`storage_cli search ...`: query the archive from the terminal (plan 2.B6). It runs the same code as `POST /search`.

    search query "how fast should we reply to an inquiry" --client acme --k 5
    search query "follow-up" --scope all --moment-type result testimonial --text-only

Without `--text-only` the query is embedded through the llm module, which needs the encoding catch, a key and an active run
plan; when it cannot be, the search says so and matches on the words alone.
"""
from __future__ import annotations

from datetime import datetime


def _when(text: str) -> datetime:
    value = datetime.fromisoformat(text)
    if value.tzinfo is None:
        raise SystemExit("Give dates with an explicit offset, such as 2026-03-09T00:00:00-05:00")
    return value


def add_cli(sub) -> None:
    group = sub.add_parser("search", help="Search verified moments and transcript chunks (2.B6)")
    g = group.add_subparsers(dest="search_command", required=True)
    p = g.add_parser("query")
    p.add_argument("text")
    p.add_argument("--k", type=int, default=10)
    p.add_argument("--scope", choices=["moments", "chunks", "all"], default="moments")
    p.add_argument("--from", dest="date_from", type=_when)
    p.add_argument("--to", dest="date_to", type=_when)
    p.add_argument("--client")
    p.add_argument("--source-type")
    p.add_argument("--call-type")
    p.add_argument("--speaker-role", nargs="*", default=[])
    p.add_argument("--moment-type", nargs="*", default=[])
    p.add_argument("--consent", nargs="*", help="Default: cleared, anonymise, internal_only; name do_not_use to include it")
    p.add_argument("--topic")
    p.add_argument("--document", nargs="*", default=[], dest="documents")
    p.add_argument("--text-only", action="store_true", help="Do not embed the query (no model call)")


def run_cli(args, storage, models) -> dict:
    from ..repository import ContentRepository
    from .api import SearchRequest, run_search
    from .query import QueryVector
    repo = ContentRepository(storage)
    request = SearchRequest(text=args.text, k=args.k, scope=args.scope, filters={
        "date_from": args.date_from, "date_to": args.date_to, "client_id": args.client, "source_type": args.source_type,
        "call_type": args.call_type, "speaker_role": args.speaker_role, "moment_type": args.moment_type,
        "consent_status": args.consent, "topic_id": args.topic, "document_ids": args.documents})
    vector = QueryVector(None, "unavailable", "--text-only: the query was not embedded") if args.text_only else None
    answer = run_search(repo, models, request, vector=vector)
    hits = [{"kind": h["kind"], "id": h["moment"].moment_id if h["kind"] == "moment" else h["chunk"].chunk_id,
             "score": round(h["score"], 5), "matched_by": h["matched_by"], "citation": h["citation"].model_dump(mode="json")}
            for h in answer["hits"]]
    return {**answer, "hits": hits}
