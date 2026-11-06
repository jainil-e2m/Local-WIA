"""Wait for production runs or jobs to settle and print their state (N4; not product code).

Usage (from backend/, production's variables loaded): python -I wait.py [--timeout SECONDS] <run_id or job_id>...
"""
import os
import sys
import time

import psycopg
from psycopg.rows import dict_row

args = sys.argv[1:]
limit = 900
if args[:1] == ["--timeout"]:
    limit, args = int(args[1]), args[2:]
TERMINAL = {"completed", "failed", "cancelled", "waiting", "blocked", "skipped", "succeeded", "superseded"}
deadline = time.time() + limit
while True:
    with psycopg.connect(os.environ["ATELIER_DATABASE_URL"], connect_timeout=30, row_factory=dict_row) as conn:
        rows = conn.execute("SELECT job_id, run_id, stage, status, current_message, updated_at FROM pipeline_jobs "
                            "WHERE run_id = ANY(%s) OR job_id = ANY(%s) ORDER BY created_at", (args, args)).fetchall()
    settled = rows and all(r["status"] in TERMINAL for r in rows)
    if settled or time.time() > deadline:
        for r in rows:
            print(r["job_id"], r["stage"], r["status"], (r["current_message"] or "")[:200], r["updated_at"].isoformat(timespec="seconds"))
        print("settled" if settled else "still running")
        break
    time.sleep(15)
