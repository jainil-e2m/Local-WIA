"""`storage_cli topics ...`: the topic registry from the terminal (plan 2.B7).

    topics list [--status] [--q]             topics with their mention counts
    topics show TOPIC_ID                     one topic: statistics, moments, history
    topics assign --estimate                 how many moments need a model call and what it costs. No call, nothing queued.
    topics assign --mode live|synthetic      queue one bulk run (live needs the catches and an active run plan)
    topics rename|merge|block|unblock ...    administrator actions (approver role), each audited in `decisions`
"""
from __future__ import annotations


def add_cli(sub) -> None:
    group = sub.add_parser("topics", help="The topic registry: list, assign moments to topics, rename, merge, block (2.B7)")
    g = group.add_subparsers(dest="topics_command", required=True)
    p = g.add_parser("list")
    p.add_argument("--status", choices=["active", "blocked", "merged"])
    p.add_argument("--q")
    p.add_argument("--limit", type=int, default=50)
    p = g.add_parser("show")
    p.add_argument("topic_id")
    p = g.add_parser("assign", help="Estimate (--estimate) or queue topic assignment for moments that have none")
    p.add_argument("--estimate", action="store_true")
    p.add_argument("--mode", choices=["live", "synthetic"], default="live")
    p.add_argument("--ids", nargs="*")
    p.add_argument("--price-in", type=float, help="The chat model's USD per million input tokens, for the cost estimate")
    p.add_argument("--price-out", type=float, help="The chat model's USD per million output tokens")
    p.add_argument("--actor", default="local-cli")
    for name in ("rename", "merge", "block", "unblock"):
        p = g.add_parser(name, help=f"{name.capitalize()} a topic (needs an approver)")
        p.add_argument("topic_id")
        p.add_argument("--actor", required=True)
        p.add_argument("--note")
        if name == "rename":
            p.add_argument("--name", required=True)
            p.add_argument("--description")
        if name == "merge":
            p.add_argument("--into", required=True, dest="into")


def run_cli(args, storage, models) -> dict:
    from ..gates.roles import actor_for
    from ..repository import ContentRepository
    from . import topics
    repo = ContentRepository(storage)
    command = args.topics_command
    if command == "list":
        with repo.connection() as conn:
            return topics.listing(conn, status=args.status, q=args.q, limit=args.limit)
    if command == "show":
        with repo.connection() as conn:
            return {**topics.statistics(conn, args.topic_id), "moments": topics.moment_ids(conn, args.topic_id)}
    if command == "assign":
        if args.estimate:
            with repo.connection() as conn:
                return topics.estimate(conn, models, args.ids, price_in=args.price_in, price_out=args.price_out)
        return topics.queue(repo, models, ids=args.ids, mode=args.mode, actor=args.actor)
    actor = actor_for(repo, args.actor)
    if command == "rename":
        done = topics.as_approver(repo, actor, topics.rename, args.topic_id, args.name, description=args.description, note=args.note)
    elif command == "merge":
        done = topics.as_approver(repo, actor, topics.merge, args.topic_id, args.into, note=args.note)
    elif command == "block":
        done = topics.as_approver(repo, actor, topics.block, args.topic_id, note=args.note)
    else:
        done = topics.as_approver(repo, actor, topics.unblock, args.topic_id, note=args.note)
    return {k: done[k] for k in ("topic_id", "name", "status", "merged_into")}
