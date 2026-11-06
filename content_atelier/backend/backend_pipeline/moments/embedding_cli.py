"""`storage_cli moments-embed ...`: the operator's commands for moment embeddings (plan 2.B5).

    moments-embed report                      is every searchable moment embedded under the contract?
    moments-embed queue --estimate            how many moments, tokens and USD; the input-set hash for the run plan. No call.
    moments-embed queue --mode cached|live    queue one bulk run (live needs the encoding catch and an active run plan)

A queued run is executed by a queue worker (`python -m backend_pipeline.jobs worker`) or inline with `storage_cli worker`.
"""
from __future__ import annotations


def add_cli(sub) -> None:
    group = sub.add_parser("moments-embed", help="Embed verified moments under the archive's embedding contract (2.B5)")
    g = group.add_subparsers(dest="moments_embed_command", required=True)
    g.add_parser("report", help="Searchable moments, how many are embedded under the contract, and what is stale or missing")
    p = g.add_parser("queue", help="Estimate (--estimate) or queue the embedding of moments that have no current vector")
    p.add_argument("--estimate", action="store_true", help="State the count, tokens, cost and run-plan input set; make no call and queue nothing")
    p.add_argument("--mode", choices=["cached", "live"], default="cached")
    p.add_argument("--ids", nargs="*", help="Only these moments")
    p.add_argument("--actor", default="local-cli")


def run_cli(args, storage, models) -> dict:
    from ..repository import ContentRepository
    from . import embedding
    repo = ContentRepository(storage)
    if args.moments_embed_command == "report":
        with repo.connection() as conn:
            return embedding.report(conn, models)
    if args.estimate:
        with repo.connection() as conn:
            return embedding.estimate(conn, models, args.ids)
    return embedding.queue(repo, models, ids=args.ids, mode=args.mode, actor=args.actor)
