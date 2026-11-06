#!/bin/zsh
# Waits for the v1 workers to exit, then queues the v2 backfill and starts 8 workers.
set -u
W=/Users/kenilshah/Desktop/Wedding_industy_ads/atelier-work
until [ "$(for p in $(cat $W/logs/backfill-pids.txt); do kill -0 $p 2>/dev/null && echo x; done | wc -l | tr -d ' ')" = "0" ]; do sleep 10; done
P=$(cat $W/plan-backfill-v2.txt)
export CONTENT_ATELIER_LLM_COMPLETION_TOKENS=24000 CONTENT_ATELIER_LIVE=true ATELIER_ALLOW_GENERATION=true ATELIER_RUN_PLAN_ID=$P AW_KEY=internal
cd /Users/kenilshah/Desktop/Wedding_industy_ads/WIA-Content-Atelier/backend
zsh $W/aw.sh python -m backend_pipeline.storage_cli moments extract --all-pending --profile 2026-10-19.scenes.v2 --mode live > $W/reports/backfill-v2-queue.json 2>&1
: > $W/logs/backfill-v2-pids.txt
for n in 1 2 3 4 5 6 7 8; do
  nohup zsh $W/aw.sh python -m backend_pipeline.storage_cli worker --max-jobs 40 > $W/logs/backfill-v2-worker-$n.log 2>&1 &
  echo $! >> $W/logs/backfill-v2-pids.txt; sleep 1
done
python3 -c "import json;d=json.load(open('$W/reports/backfill-v2-queue.json'));print('queued', d.get('run_id'), len(d.get('jobs',[])))"
