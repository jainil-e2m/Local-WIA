from __future__ import annotations

import argparse
import json
from datetime import date, datetime
from pathlib import Path
from . import settings_store
from .config import Settings
from .storage_config import StorageSettings
from .database import check, migrate
from .repository import ContentRepository
from .import_history import import_luna
from .sql_pipeline import SQLWorker, queue_encoding
from .gate_one import reassess
from .angle_workflow import WORKFLOW, LEGACY


def main(argv=None):
    parser = argparse.ArgumentParser(description='Approved SQL pipeline. External calls disabled by default.')
    sub = parser.add_subparsers(dest='command',required=True)
    sub.add_parser('check', help="Compare the database with its recorded version's catalogue")
    sub.add_parser('migrate', help='Apply every migration up to the latest version, in one transaction')
    brief=sub.add_parser('brief'); brief.add_argument('--angle-id',required=True)
    brief.add_argument('--actor',required=True); brief.add_argument('--mode',choices=['replay','live'],default=None,help='Default replay; a regeneration keeps the mode of the run it replaces')
    brief.add_argument('--regenerate',action='store_true',help='Start a fresh run for the same approved card after its pinned context changed mid-run (V13)')
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
    kb=sub.add_parser('kb-publish',help='Publish the knowledge-base version into brand_kit_docs (E.B11 e)')
    kb.add_argument('--approver',required=True); kb.add_argument('--root',type=Path,default=None)
    kbcheck=sub.add_parser('kb-check',help='Compare the files with the published version: same hashes in every environment')
    kbcheck.add_argument('--root',type=Path,default=None)
    cseed=sub.add_parser('context-seed',help='One-time seed of the context store from the export analysis and KB 04 to 06 (L.B2)')
    cseed.add_argument('--approver',required=True,help="The E.X2 approver whose confirmations KB 04 to 06 carry")
    cseed.add_argument('--actor',required=True)
    cdel=sub.add_parser('context-delete-source',help="Remove a source's candidates and record the deletion (L.B1)")
    cdel.add_argument('--source-kind',required=True); cdel.add_argument('--source-ref'); cdel.add_argument('--source-ref-prefix')
    cdel.add_argument('--actor',required=True); cdel.add_argument('--reason',required=True)
    kbc=sub.add_parser('kb-compile',help='Compile a draft knowledge-base version from confirmed items (L.B4)')
    kbc.add_argument('--on',type=date.fromisoformat,default=None); kbc.add_argument('--actor',required=True)
    kbc.add_argument('--root',type=Path,default=None)
    kba=sub.add_parser('kb-approve',help='Approve a compiled version (L.B4)'); kba.add_argument('--version',required=True)
    kba.add_argument('--actor',required=True); kba.add_argument('--note',required=True)
    kbb=sub.add_parser('kb-benchmark',help="Record an identity change's E.B3 smoke result (L.B4)")
    kbb.add_argument('--version',required=True); kbb.add_argument('--actor',required=True)
    kbb.add_argument('--result',required=True,help='The benchmark result file or run'); kbb.add_argument('--note',default='')
    kbb_pass=kbb.add_mutually_exclusive_group(required=True); kbb_pass.add_argument('--passed',action='store_true'); kbb_pass.add_argument('--failed',action='store_true')
    sub.add_parser('kb-versions',help='List compiled versions and the runs that used them')
    kbe=sub.add_parser('kb-export',help='Write a compiled version as a file knowledge base (L.B4)')
    kbe.add_argument('--version',required=True); kbe.add_argument('--dir',type=Path,required=True)
    crev=sub.add_parser('context-review-apply',help="Apply the committed delegated review of the seed (L.F1, D12)")
    crev.add_argument('--actor',required=True,help='The approver who runs it, recorded as reviewer')
    cpts=sub.add_parser('context-published-points',help="Confirm the published log's rows with their dates and central points (E.B25 f)")
    cpts.add_argument('--actor',required=True,help='The approver who runs it, recorded as reviewer')
    cent=sub.add_parser('context-entries-apply',help="Enter the reviewed entries of knowledge-base version 9: document 05's descriptors and glossary, document 09's first-touch rules (E.B25 i, j)")
    cent.add_argument('--actor',required=True,help='The approver who runs it, recorded as reviewer')
    cmine=sub.add_parser('context-mining',help="The weekly learning loop over WIA's approved work (L.B6)")
    cmine.add_argument('--week-id'); cmine.add_argument('--since',type=date.fromisoformat); cmine.add_argument('--until',type=date.fromisoformat)
    cmine.add_argument('--actor',default='context_mining')
    cmine.add_argument('--mode',choices=['rules','live'],default='rules',help='live: categorise edits with OPENROUTER_CONTEXT_MINING_MODEL under a run plan')
    cstale=sub.add_parser('context-staleness',help='Retire expired items and record review warnings (L.B8)')
    cstale.add_argument('--actor',default='staleness job')
    csched=sub.add_parser('context-scheduler',help='Run the nightly staleness job and the weekly learning loop (L.B6, L.B8)')
    csched.add_argument('--once',action='store_true',help='One pass, for a cron service')
    plan=sub.add_parser('plan',help='Run plans for paid calls (E.B1)'); plan_sub=plan.add_subparsers(dest='plan_command',required=True)
    create=plan_sub.add_parser('create'); create.add_argument('--purpose',required=True)
    create.add_argument('--stage',action='append',required=True); create.add_argument('--model',action='append',required=True)
    create.add_argument('--input-set-hash',required=True); create.add_argument('--max-calls',type=int,required=True)
    create.add_argument('--max-cost-usd',type=float,required=True); create.add_argument('--approver',required=True)
    create.add_argument('--hours',type=float,default=24)
    create.add_argument('--file',type=Path,help='Write a file plan beside a harness run instead of the database')
    create.add_argument('--standing',choices=['kb_benchmark'],help="A standing plan the scheduler may spend for this purpose: "
                        "kb_benchmark benchmarks an approved identity change of the knowledge base (L.B11)")
    ihash=plan_sub.add_parser('input-hash',help="The input-set hash of a weekly run, for --input-set-hash"); ihash.add_argument('--run-id',required=True)
    show=plan_sub.add_parser('show'); show.add_argument('--plan-id'); show.add_argument('--file',help='A harness file plan')
    close=plan_sub.add_parser('close'); close.add_argument('--plan-id'); close.add_argument('--file',help='A harness file plan')
    close.add_argument('--reason',required=True)
    budgets=sub.add_parser('budgets',help='Standing weekly budgets for paid calls (6.B3)')
    budgets_sub=budgets.add_subparsers(dest='budgets_command',required=True)
    budgets_sub.add_parser('show',help="This week's cap, spend and waiting jobs for every purpose")
    bset=budgets_sub.add_parser('set',help="Change a purpose's weekly cap (and this week's plan); --actor must be an approver")
    from .llm.standing import PURPOSES as BUDGET_PURPOSES  # every standing purpose, packs included (NP.B5)
    bset.add_argument('--purpose',required=True,choices=list(BUDGET_PURPOSES))
    bset.add_argument('--weekly-usd',type=float); bset.add_argument('--weekly-calls',type=int)
    bset.add_argument('--clear',action='store_true',help='Remove the standing budget: the purpose then needs a named run plan')
    bset.add_argument('--actor',required=True)
    budgets_sub.add_parser('renew',help="Create this week's plans and queue again the jobs that waited (the scheduler does this weekly)")
    weeks_cmd=sub.add_parser('weeks',help="Archive or restore a week (week_archive.py): an archived week stays as the record, out of the app's lists")
    weeks_sub=weeks_cmd.add_subparsers(dest='weeks_command',required=True)
    warch=weeks_sub.add_parser('archive'); warch.add_argument('--week-id',required=True); warch.add_argument('--reason',required=True); warch.add_argument('--actor',required=True)
    wrest=weeks_sub.add_parser('restore'); wrest.add_argument('--week-id',required=True); wrest.add_argument('--actor',required=True)
    review_doc=sub.add_parser('review-document',help="The week's review document (5.B14): cards, briefs and every asset's copy, as Markdown or a Word file")
    review_doc.add_argument('--week-id',required=True); review_doc.add_argument('--out',type=Path,help='Write the file here; without it the Markdown is printed (a .docx needs it)')
    review_doc.add_argument('--format',choices=('markdown','docx'),default='markdown',help='markdown (the default) or docx, the same document as a Word file on the template in the image')
    canned=sub.add_parser('pack-canned',help="NP.X1 only: put a canned finisher answer in a free-model shakedown pack run's response cache")
    canned.add_argument('--run-id',required=True); canned.add_argument('--answer',type=Path,required=True)
    pack_doc=sub.add_parser('pack-document',help="The week's pack document (NP.B12): the week's plan and every pack's pieces in full, as Markdown or a Word file")
    pack_doc.add_argument('--week',dest='week_id',required=True); pack_doc.add_argument('--out',type=Path,help='Write the file here; without it the Markdown is printed (a .docx needs it)')
    pack_doc.add_argument('--format',choices=('markdown','docx'),default='markdown',help='markdown (the default) or docx, the same document as a Word file')
    costs=sub.add_parser('costs',help="What the model and embedding calls cost (6.B7), from the recorded cost, read only: per budget week, stage, model and provider, and budget purpose")
    costs.add_argument('--from',dest='start',type=datetime.fromisoformat,help='Start, YYYY-MM-DD or a time (UTC without a zone); default the last eight budget weeks')
    costs.add_argument('--to',dest='end',type=datetime.fromisoformat,help='End, excluded; default the next Monday 00:00 UTC')
    costs.add_argument('--json',action='store_true',help='Print JSON (the same as GET /storage/costs) instead of the report in words')
    measures=sub.add_parser('week-measures',help="The week's success measures (7.X2; plan 4.5, packs plan 4.6) from the database, read only: WIA's own and delegated counts, and each threshold")
    measures.add_argument('--week',dest='week_id',required=True); measures.add_argument('--json',action='store_true',help='Print JSON instead of the report in words')
    users=sub.add_parser('users',help='Users and roles (0.B9)'); users_sub=users.add_subparsers(dest='users_command',required=True)
    useed=users_sub.add_parser('seed',help='Create a users row for every address on the legacy allowlists; never changes an existing row unless --overwrite')
    useed.add_argument('--actor',required=True,help='Who ran it (recorded)'); useed.add_argument('--overwrite',action='store_true')
    users_sub.add_parser('list')
    uset=users_sub.add_parser('set',help='Create or change one person; --actor must be an administrator')
    uset.add_argument('--actor',required=True); uset.add_argument('--email',required=True); uset.add_argument('--role',required=True,choices=['viewer','editor','approver','admin'])
    uset.add_argument('--name'); uset.add_argument('--slack-user-id')
    settings_store.add_cli(sub)  # settings list|get|set|unset|import-env (0.B8)
    from .documents.cli import add_cli as add_documents_cli
    add_documents_cli(sub)  # documents, people, clients, glossary (Phase 1), identities (N8)
    from .moments.embedding_cli import add_cli as add_moments_embed_cli
    from .moments.topics_cli import add_cli as add_topics_cli
    from .search.cli import add_cli as add_search_cli
    add_moments_embed_cli(sub); add_topics_cli(sub); add_search_cli(sub)  # moments-embed, topics, search (Phase 2)
    from .moments.cli import add_cli as add_moments_cli
    add_moments_cli(sub)  # moments extract|report|recheck|recall|import-saved (Phase 2)
    worker=sub.add_parser('worker',help='Run ready jobs inline, then exit (queue workers: python -m backend_pipeline.jobs worker)')
    worker.add_argument('--max-jobs',type=int,default=1)
    worker.add_argument('--watch',action='store_true',help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.command in {'pack-document','review-document'} and args.format=='docx' and not args.out:
        parser.error(f'{args.command} --format docx needs --out')
    models = Settings.from_env()
    storage = StorageSettings.from_env(); repo=ContentRepository(storage)
    if args.command=='migrate': result=migrate(storage.database_url)
    elif args.command in {'kb-publish','kb-check'}:
        from .knowledge_base import load_knowledge_base, load_published, publish
        from .database import connect
        root=args.root or models.knowledge_base_root
        with connect(storage.database_url,vectors=False) as c:
            if args.command=='kb-publish': result=publish(c,root,approver=args.approver)
            else:
                files=load_knowledge_base(root)
                published=load_published(c,files.version)
                result={'version':files.version,'files_sha256':files.sha256,'published_sha256':published.sha256,
                        'identical':files.refs()==published.refs() and files.text==published.text}
    elif args.command in {'context-seed','context-delete-source'}:
        from .database import connect
        from .knowledge import items as context_items, seed as context_seed
        with connect(storage.database_url) as c:
            if args.command=='context-seed':
                result=context_seed.run(c,actor=args.actor,approver=args.approver)
            else:
                result=context_items.delete_source(c,source_kind=args.source_kind,source_ref=args.source_ref,
                                                   source_ref_prefix=args.source_ref_prefix,actor=args.actor,reason=args.reason)
            c.commit()
    elif args.command=='context-review-apply':
        from .database import connect
        from .knowledge import delegated
        with connect(storage.database_url) as c:
            from .gates.roles import actor_for
            result=delegated.apply(c,storage,actor_for(repo,args.actor)); c.commit()
    elif args.command=='context-entries-apply':
        from .database import connect
        from .knowledge import entries
        with connect(storage.database_url) as c:
            from .gates.roles import actor_for
            result=entries.apply(c,storage,actor_for(repo,args.actor)); c.commit()
    elif args.command=='context-published-points':
        from .database import connect
        from .knowledge import published_points
        with connect(storage.database_url) as c:
            from .gates.roles import actor_for
            result=published_points.apply(c,storage,actor_for(repo,args.actor)); c.commit()
    elif args.command in {'kb-compile','kb-approve','kb-benchmark','kb-versions','kb-export'}:
        from .database import connect
        from .knowledge import compiler
        from .gates.roles import actor_for
        with connect(storage.database_url) as c:
            if args.command=='kb-compile':
                result=compiler.compile_version(c,on=args.on or date.today(),actor=args.actor,root=args.root or models.knowledge_base_root)
            elif args.command=='kb-approve': result=compiler.approve(c,storage,args.version,actor_for(repo,args.actor),note=args.note)
            elif args.command=='kb-export': result=compiler.export(c,args.version,args.dir)
            elif args.command=='kb-benchmark':
                result=compiler.record_benchmark(c,storage,args.version,actor_for(repo,args.actor),passed=args.passed,result_ref=args.result,note=args.note)
            else: result={'active':compiler.active_version(c),'versions':compiler.versions(c)}
            c.commit()
    elif args.command in {'context-mining','context-staleness','context-scheduler'}:
        from .knowledge import scheduler as context_scheduler
        if args.command=='context-scheduler':
            result=context_scheduler.loop(storage,models,once=args.once)
        elif args.command=='context-staleness':
            result=context_scheduler.staleness_now(storage,actor=args.actor)
        else:
            result=context_scheduler.mining_now(storage,models,actor=args.actor,week_id=args.week_id,since=args.since,
                                                until=args.until,live=args.mode=='live')
    elif args.command=='plan':
        from .llm.run_plans import create_sql_plan, write_file_plan
        from .database import connect
        if args.plan_command=='input-hash':
            from .sql_pipeline import run_input_set_hash
            with connect(storage.database_url,vectors=False) as c:
                run=c.execute('SELECT input_refs FROM pipeline_runs WHERE run_id=%s',(args.run_id,)).fetchone()
            if not run:
                raise SystemExit('Run not found')
            result={'run_id':args.run_id,'input_set_hash':run_input_set_hash(run)}
        elif args.plan_command=='create':
            fields=dict(purpose=args.purpose,stages=args.stage,models=args.model,input_set_hash=args.input_set_hash,
                        max_calls=args.max_calls,max_cost_usd=args.max_cost_usd,approver=args.approver,hours=args.hours,
                        **({'details':{'standing':args.standing}} if args.standing else {}))
            if args.standing and args.file:
                raise SystemExit('A standing plan is a database plan: the scheduler reads it from run_plans')
            if args.file:
                result=write_file_plan(args.file,**fields)
            else:
                with connect(storage.database_url,vectors=False) as c: result=create_sql_plan(c,**fields)
        elif args.plan_command in ('show','close') and args.file:
            from .llm.run_plans import FilePlanStore
            store=FilePlanStore(args.file)
            result=store.show() if args.plan_command=='show' else store.close(args.reason)
        elif not args.plan_id:
            raise SystemExit('Name the plan with --plan-id, or a harness plan with --file')
        elif args.plan_command=='show':
            with connect(storage.database_url,vectors=False) as c:
                result={'plan':c.execute('SELECT * FROM run_plans WHERE plan_id=%s',(args.plan_id,)).fetchone(),
                        'calls':c.execute('SELECT llm_run_id,stage,model,status,cost_usd,created_at FROM llm_runs WHERE plan_id=%s ORDER BY created_at',(args.plan_id,)).fetchall()}
        else:
            with connect(storage.database_url,vectors=False) as c:
                result=c.execute("UPDATE run_plans SET status='closed',closed_at=now(),closed_reason=%s WHERE plan_id=%s AND status='active' RETURNING plan_id,status",(args.reason,args.plan_id)).fetchone() or {'error':'no active plan with that id'}
    elif args.command=='budgets':
        from .database import connect
        from .llm import standing
        with connect(storage.database_url,vectors=False) as c:
            if args.budgets_command=='set':
                from .gates.roles import actor_for
                actor=actor_for(repo,args.actor)
                from .gate_one import require
                require(repo,actor,'decide')  # an approver sets a budget
                result=standing.set_cap(c,args.purpose,actor,usd=args.weekly_usd,calls=args.weekly_calls,clear=args.clear)
            elif args.budgets_command=='renew': result=standing.renew(c)
            else: result=standing.status(c)
            c.commit()
    elif args.command=='weeks':
        from . import week_archive
        with repo.connection() as c:
            result=(week_archive.archive(c,args.week_id,reason=args.reason,actor=args.actor) if args.weeks_command=='archive'
                    else week_archive.restore(c,args.week_id,actor=args.actor))
    elif args.command=='review-document' and args.format=='docx':
        from .briefs.review_docx import docx
        data=docx(repo,args.week_id)
        args.out.parent.mkdir(parents=True,exist_ok=True); args.out.write_bytes(data)
        result={'week_id':args.week_id,'path':str(args.out),'format':'docx','bytes':len(data)}
    elif args.command=='review-document':
        from .briefs.review_document import render_week
        text=render_week(repo,args.week_id)
        if not args.out:
            print(text,end=''); return
        args.out.parent.mkdir(parents=True,exist_ok=True); args.out.write_text(text,encoding='utf-8')
        result={'week_id':args.week_id,'path':str(args.out),'characters':len(text)}
    elif args.command=='pack-canned':
        from .packs.shakedown import seed_finish
        result=seed_finish(SQLWorker(storage,models),args.run_id,json.loads(args.answer.read_text(encoding='utf-8')))
    elif args.command=='pack-document' and args.format=='docx':
        from .packs.document_docx import docx
        data=docx(repo,args.week_id)
        args.out.parent.mkdir(parents=True,exist_ok=True); args.out.write_bytes(data)
        result={'week_id':args.week_id,'path':str(args.out),'format':'docx','bytes':len(data)}
    elif args.command=='pack-document':
        from .packs.document import markdown
        text=markdown(repo,args.week_id)
        if not args.out:
            print(text,end=''); return
        args.out.parent.mkdir(parents=True,exist_ok=True); args.out.write_text(text,encoding='utf-8')
        result={'week_id':args.week_id,'path':str(args.out),'characters':len(text)}
    elif args.command=='costs':
        from .llm.cost_summary import run_cli as costs_report
        try:
            print(costs_report(repo,args.start,args.end,args.json),end='')
        except ValueError as error:
            raise SystemExit(str(error)) from None
        return
    elif args.command=='week-measures':
        from .week_measures import run_cli as week_measures
        try:
            print(week_measures(repo,args.week_id,args.json),end='')
        except LookupError as error:
            raise SystemExit(str(error)) from None
        return
    elif args.command=='users':
        from .gates.roles import run_users
        result=run_users(storage,args)
    elif args.command=='brief':
        from .briefs.workflow import queue
        from .briefs.gate_two import authorize
        from .gates.roles import actor_for
        actor=actor_for(repo,args.actor)
        authorize(repo,actor)
        if args.regenerate:
            from .briefs.workflow import regenerate
            result=regenerate(repo,args.angle_id,actor,args.mode)
        else:
            result=queue(repo,args.angle_id,actor,args.mode or 'replay')
    elif args.command=='activate-brief':
        from .briefs.workflow import activate_live
        from .gates.roles import actor_for
        result=activate_live(repo,args.run_id,args.expected_input_hash,actor_for(repo,args.actor))
    elif args.command=='check':
        with repo.connection() as c: result=check(c)
    elif args.command=='admit': result=repo.admit(args.directory,args.start,args.week_index)
    elif args.command=='import-luna': result=import_luna(repo,models,args.week_id)
    elif args.command=='review': result=repo.review(args.week_id)
    # The profile, knowledge base and models are validated and frozen at submit, as the API does (E.B16 n).
    elif args.command=='submit': result=repo.submit(args.week_id,args.mode,workflow=args.workflow,models=models)
    elif args.command=='settings': result=settings_store.run_cli(args,storage)
    elif args.command in {'documents','people','clients','glossary','identities'}:
        from .documents.cli import run_cli as run_documents_cli
        result=run_documents_cli(args,storage,models)
    elif args.command in {'moments-embed','topics','search'}:
        if args.command=='moments-embed':
            from .moments.embedding_cli import run_cli as run_phase2_cli
        elif args.command=='topics':
            from .moments.topics_cli import run_cli as run_phase2_cli
        else:
            from .search.cli import run_cli as run_phase2_cli
        result=run_phase2_cli(args,storage,models)
    elif args.command=='moments':
        from .moments.cli import run_cli as run_moments_cli
        result=run_moments_cli(args,storage,models)
    elif args.command=='comparison': result=repo.comparison_report(args.run_id)
    elif args.command=='retry': result=repo.retry(args.job_id,'local-cli')
    elif args.command=='encode': result=queue_encoding(repo,args.run_id,args.mode)
    elif args.command=='encode-chunks':
        from .chunk_encoding import queue
        result=queue(repo,models,args.week_id,args.mode)
    elif args.command=='reassess': result=reassess(repo,args.week_id,'local-cli')
    else:
        if args.watch:
            raise SystemExit('The polling worker is gone (0.B5). Start a queue worker with: python -m backend_pipeline.jobs worker')
        from .startup import verify
        verify(storage,models)
        w=SQLWorker(storage,models); jobs=[]
        for _ in range(args.max_jobs):
            j=w.once()
            if not j: break
            jobs.append(j)
        result={'processed_jobs':jobs}
    print(json.dumps(result,indent=2,default=str))


if __name__=='__main__':
    main()
