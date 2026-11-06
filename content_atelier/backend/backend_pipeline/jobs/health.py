"""Job health from the job rows themselves (plan 0.B6): no heartbeat files, no extra service.

Every running job renews `heartbeat_at` and its lease on its own row; a queued row has an age; the scheduler records
the end of each pass. From those, one answer: what is queued, running, lost or failed on each queue, how long the
oldest queued job has waited, and whether the scheduler is alive. `ok` is false when a lease has run out unnoticed,
a queued job has waited too long, or the scheduler has not completed a pass recently.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from .scheduler import HEARTBEAT_KEY

QUEUED_TOO_LONG = timedelta(minutes=10)
SCHEDULER_SILENT = timedelta(minutes=5)


def summary(conn, *, now: datetime | None = None) -> dict:
    now = now or datetime.now(UTC)
    rows = conn.execute("""SELECT queue,status,count(*) n,min(created_at) FILTER (WHERE status='queued') oldest_queued,
        count(*) FILTER (WHERE status='running' AND lease_expires_at<now()) lost,
        max(heartbeat_at) FILTER (WHERE status='running') last_heartbeat
        FROM pipeline_jobs WHERE status IN ('queued','running','failed','waiting') GROUP BY queue,status""").fetchall()
    queues: dict[str, dict] = {}
    for row in rows:
        q = queues.setdefault(row["queue"], {"queued": 0, "running": 0, "failed": 0, "waiting": 0, "lost": 0,
                                             "oldest_queued_seconds": None, "last_heartbeat": None})
        q[row["status"]] = row["n"]
        q["lost"] += row["lost"] or 0
        if row["oldest_queued"]:
            q["oldest_queued_seconds"] = int((now - row["oldest_queued"]).total_seconds())
        if row["last_heartbeat"]:
            q["last_heartbeat"] = row["last_heartbeat"].isoformat()
    beat = conn.execute("SELECT value,updated_at FROM settings WHERE key=%s", (HEARTBEAT_KEY,)).fetchone()
    scheduler_at = beat["updated_at"] if beat else None
    problems = []
    for name, q in queues.items():
        if q["lost"]:
            problems.append(f"{q['lost']} running job(s) on {name} have lost their lease")
        if q["oldest_queued_seconds"] is not None and q["oldest_queued_seconds"] > QUEUED_TOO_LONG.total_seconds():
            problems.append(f"a job on {name} has waited {q['oldest_queued_seconds'] // 60} minutes")
    if scheduler_at is None or now - scheduler_at > SCHEDULER_SILENT:
        problems.append("the scheduler has not completed a pass in the last 5 minutes")
    return {"ok": not problems, "problems": problems, "queues": queues,
            "scheduler_last_pass": scheduler_at.isoformat() if scheduler_at else None}


def workers_ready(queues=("interactive", "default"), redis_connection=None) -> bool:
    """True when an RQ worker listening on one of `queues` has a fresh heartbeat in Redis. False when Redis is
    not configured or cannot be reached."""
    try:
        from rq import Worker
        from rq.serializers import JSONSerializer

        from .dispatch import connect_redis
        connection = redis_connection or connect_redis()
        cutoff = datetime.now(UTC) - timedelta(seconds=150)
        for worker in Worker.all(connection=connection, serializer=JSONSerializer):
            beat = worker.last_heartbeat
            if beat is None:
                continue
            beat = beat if beat.tzinfo else beat.replace(tzinfo=UTC)
            if beat >= cutoff and set(worker.queue_names()) & set(queues):
                return True
    except Exception:
        return False
    return False
