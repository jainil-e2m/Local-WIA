from __future__ import annotations

import argparse
import json
import time
from datetime import date
from pathlib import Path
from .config import Settings
from .storage_config import StorageSettings
from .database import initialize, check, apply_brief_indexes, apply_calendar
from .repository import ContentRepository
from .import_history import import_luna
from .sql_pipeline import SQLWorker, queue_encoding
from .gate_one import reassess
from .angle_workflow import WORKFLOW, LEGACY


def main():
    parser = argparse.ArgumentParser(description='Approved SQL pipeline. External calls disabled by default.')
    sub = parser.add_subparsers(dest='command',required=True)
    sub.add_parser('init'); sub.add_parser('check')
    sub.add_parser('brief-indexes'); sub.add_parser('calendar-migrate')
    brief=sub.add_parser('brief'); brief.add_argument('--angle-id',required=True)
    brief.add_argument('--actor',required=True); brief.add_argument('--mode',choices=['replay','live'],default='replay')
    activate=sub.add_parser('activate-brief');activate.add_argument('--run-id',required=True);activate.add_argument('--expected-input-hash',required=True);activate.add_argument('--actor',required=True)
    admit = sub.add_parser('admit')
    admit.add_argument('--directory',type=Path,required=True); admit.add_argument('--start',type=date.fromisoformat,required=True)
    admit.add_argument('--week-index',type=int,required=True)
    for name in ('import-luna','review','submit','reassess'):
        s=sub.add_parser(name); s.add_argument('--week-id',required=True)
        if name=='submit':
            s.add_argument('--mode',choices=['replay','live'],default='replay')
            s.add_argument('--workflow',choices=[LEGACY,WORKFLOW],default=LEGACY)
    report=sub.add_parser('comparison'); report.add_argument('--run-id',required=True)
    retry=sub.add_parser('retry'); retry.add_argument('--job-id',required=True)
    encode=sub.add_parser('encode'); encode.add_argument('--run-id',required=True)
    encode.add_argument('--mode',choices=['cached','live'],default='cached')
    chunk_encode=sub.add_parser('encode-chunks')
    chunk_encode.add_argument('--week-id',required=True)
    chunk_encode.add_argument('--mode',choices=['cached','live'],default='cached')
    worker=sub.add_parser('worker'); worker.add_argument('--max-jobs',type=int,default=1)
    worker.add_argument('--watch',action='store_true')
    args = parser.parse_args()
    models = Settings.from_env()
    storage = StorageSettings.from_env(); repo=ContentRepository(storage)
    if args.command=='init': result=initialize(storage.database_url)
    elif args.command=='calendar-migrate': result=apply_calendar(storage.database_url)
    elif args.command=='brief-indexes': result=apply_brief_indexes(storage.database_url)
    elif args.command=='brief':
        from .briefs.workflow import queue
        from .briefs.gate_two import authorize
        authorize(repo,args.actor)
        result=queue(repo,args.angle_id,args.actor,args.mode)
    elif args.command=='activate-brief':
        from .briefs.workflow import activate_live
        result=activate_live(repo,args.run_id,args.expected_input_hash,args.actor)
    elif args.command=='check':
        with repo.connection() as c: result=check(c)
    elif args.command=='admit': result=repo.admit(args.directory,args.start,args.week_index)
    elif args.command=='import-luna': result=import_luna(repo,models,args.week_id)
    elif args.command=='review': result=repo.review(args.week_id)
    elif args.command=='submit': result=repo.submit(args.week_id,args.mode,workflow=args.workflow)
    elif args.command=='comparison': result=repo.comparison_report(args.run_id)
    elif args.command=='retry': result=repo.retry(args.job_id,'local-cli')
    elif args.command=='encode': result=queue_encoding(repo,args.run_id,args.mode)
    elif args.command=='encode-chunks':
        from .chunk_encoding import queue
        result=queue(repo,models,args.week_id,args.mode)
    elif args.command=='reassess': result=reassess(repo,args.week_id,'local-cli')
    else:
        w=SQLWorker(storage,models); jobs=[]
        if args.watch:
            while True:
                j=w.once()
                if j: print(json.dumps({'processed_job':j}),flush=True)
                else: time.sleep(2)
        for _ in range(args.max_jobs):
            j=w.once()
            if not j: break
            jobs.append(j)
        result={'processed_jobs':jobs}
    print(json.dumps(result,indent=2,default=str))


if __name__=='__main__':
    main()
