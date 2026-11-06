"""Processes of the one executor (plan 0.B5, 0.B6):

    python -m backend_pipeline.jobs worker [--queues interactive,default,bulk]   an RQ worker
    python -m backend_pipeline.jobs scheduler [--once]                          reconcile and scheduled work, every 30 s
    python -m backend_pipeline.jobs reconcile                                    one reconcile pass, then exit
    python -m backend_pipeline.jobs health                                       job health from the job rows, as JSON

The editorial worker serves `interactive`, `default` and `bulk`; the intake worker serves `intake`; the media worker
serves `media` (it carries the speech and OCR models). All read the same job rows through `executor.run_job`.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys

from . import policy

DEFAULT_QUEUES = {"worker": ",".join(policy.EDITORIAL_QUEUES)}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m backend_pipeline.jobs")
    sub = parser.add_subparsers(dest="command", required=True)
    worker = sub.add_parser("worker", help="An RQ worker on the named queues")
    worker.add_argument("--queues", default=DEFAULT_QUEUES["worker"], help="Comma-separated; any of " + ", ".join(policy.QUEUES))
    scheduler = sub.add_parser("scheduler", help="The reconcile loop and the scheduled work")
    scheduler.add_argument("--once", action="store_true", help="One pass, then exit (a cron service)")
    sub.add_parser("reconcile", help="One reconcile pass, then exit")
    sub.add_parser("health", help="Job health from the job rows")
    return parser


def queue_names(value: str) -> list[str]:
    names = [x.strip() for x in value.split(",") if x.strip()]
    unknown = [n for n in names if n not in policy.QUEUES]
    if not names or unknown:
        raise SystemExit(f"Unknown queue(s) {unknown or value!r}; choose from {', '.join(policy.QUEUES)}")
    return names


def run_worker(names: list[str]) -> None:
    from redis import Redis
    from rq import Queue, SimpleWorker, Worker
    from rq.serializers import JSONSerializer

    from ..config import Settings
    from ..startup import verify
    from ..storage_config import StorageSettings
    from .dispatch import redis_url
    storage, models = StorageSettings.from_env(), Settings.from_env()
    editorial = bool(set(names) & set(policy.EDITORIAL_QUEUES))
    # Editorial workers carry the brief and embedding contracts; the intake workers check the embedding contract only.
    verify(storage, models, briefs=editorial, schema=editorial)
    url = redis_url()
    if not url:
        raise SystemExit("Set ATELIER_REDIS_URL: the workers read their queues from Redis")
    connection = Redis.from_url(url)
    queues = [Queue(n, connection=connection, serializer=JSONSerializer) for n in names]
    # RQ forks a work horse per job; Windows cannot fork, so a host run there executes the job in the worker itself.
    (SimpleWorker if os.name == "nt" else Worker)(queues, connection=connection, serializer=JSONSerializer).work()


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    if args.command == "worker":
        run_worker(queue_names(args.queues))
        return 0
    from ..config import Settings
    from ..repository import ContentRepository
    from ..storage_config import StorageSettings
    storage = StorageSettings.from_env()
    if args.command == "health":
        from .health import summary
        with ContentRepository(storage).connection() as conn:
            print(json.dumps(summary(conn), indent=2, default=str))
        return 0
    from . import scheduler
    if args.command == "reconcile":
        from .dispatch import connect_redis
        done = scheduler.reconcile(ContentRepository(storage), connect_redis())
        print(json.dumps(done, indent=2, default=str))
        return 0
    from ..intake.config import IntakeSettings
    from ..intake.repository import IntakeRepository
    models = Settings.from_env()
    scheduler.loop(storage, models, intake_repo=IntakeRepository(storage, IntakeSettings.from_env()), once=args.once)
    return 0


if __name__ == "__main__":
    sys.exit(main())
