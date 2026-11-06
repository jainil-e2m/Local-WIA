from __future__ import annotations

import secrets
import csv
import io
import json
from typing import Literal
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field
from .storage_config import StorageSettings
from .repository import ContentRepository
from . import gate_one
from .sql_pipeline import queue_encoding
from .angle_workflow import WORKFLOW, LEGACY


class Payload(BaseModel):
    model_config = ConfigDict(extra='forbid')

class RunRequest(Payload):
    mode: str = 'replay'
    workflow: Literal['two_call_v1','historical_comparison_v1'] = LEGACY

class Edit(Payload):
    expected_hash: str
    changes: dict

class Assessment(Payload):
    expected_hash: str
    scores: dict

class Decision(Payload):
    expected_hash: str
    decision: str
    cta: dict | None = None
    overlap_acknowledged: bool = False
    note: str | None = None

class BriefAnswers(Payload):
    expected_hash: str
    answers: dict[str,str]

class BriefReview(Payload):
    expected_hash: str
    claim_ids: list[str]
    reason: str
    history_acknowledged: bool

class Clearance(Payload):
    expected_hash: str
    evidence_id: str
    permission_reference: str
    attribution_reference: str

class BriefRevision(Payload):
    expected_hash: str
    instructions: str
    mode: Literal['replay','live']='replay'
    evidence_ids: list[str]=Field(default_factory=list,max_length=40)

class SearchRequest(Payload):
    text: str=Field(min_length=1,max_length=2000)
    k: int=Field(default=20,ge=1,le=50)
    transcript_ids: list[str]=Field(default_factory=list,max_length=100)


def router(settings=None):
    settings = settings or StorageSettings.from_env()
    repo = ContentRepository(settings)
    def actor(authorization: str=Header(default=''),x_atelier_actor: str=Header(default='')):
        if not settings.api_secret or not secrets.compare_digest(authorization,'Bearer '+settings.api_secret):
            raise HTTPException(401,'Verified backend authorization required')
        if not x_atelier_actor or len(x_atelier_actor)>320:
            raise HTTPException(401,'Trusted actor required')
        return x_atelier_actor
    routes = APIRouter(prefix='/storage',dependencies=[Depends(actor)])
    from .production_common import ProductionError
    from psycopg.errors import UndefinedTable, UndefinedColumn
    def action(fn,*args,**kwargs):
        try:
            return fn(*args,**kwargs)
        except ProductionError as e:
            raise HTTPException(e.status, {'code':e.code,'message':str(e)}) from e
        except (UndefinedTable, UndefinedColumn) as e:
            raise HTTPException(503, 'Storage schema is not ready; apply the explicit migration') from e
        except ValueError as e:
            raise HTTPException(409,str(e)) from e
        except PermissionError as e:
            raise HTTPException(403,str(e)) from e
    @routes.get('/weeks')
    def weeks():
        with repo.connection() as c:
            return c.execute('SELECT * FROM weeks ORDER BY week_start DESC').fetchall()
    @routes.get('/weeks/{week_id}')
    def review(week_id:str,subject:str=Depends(actor)):
        return action(repo.review,week_id,subject)
    @routes.get('/moments/{moment_id}')
    def evidence(moment_id:str):
        return action(repo.moment_context,moment_id)
    @routes.get('/transcripts/{transcript_id}')
    def original(transcript_id:str):
        return action(repo.transcript_original,transcript_id)
    @routes.get('/runs/{run_id}/comparison')
    def comparison(run_id:str):
        return action(repo.comparison_report,run_id)
    @routes.get('/runs/{run_id}/comparison.csv')
    def comparison_csv(run_id:str):
        data = action(repo.comparison_report,run_id)
        if data['completion_state']!='comparison_complete':
            raise HTTPException(409,'Comparison report is not complete; no qualified counts available')
        output = io.StringIO(newline='')
        columns = ['run_id','cutoff','original_id','replacement_id','selected_id','disposition','explanation',
                   'original_quality','original_max_cosine','replacement_quality','replacement_max_cosine',
                   'original_reasons','replacement_reasons','current_batch_flags','counts','assessment_snapshot']
        writer = csv.DictWriter(output,fieldnames=columns); writer.writeheader()
        report = data['report']
        for scenario in report['scenarios']:
            # Empty generation still exports its explained zero-count scenario.
            for family in scenario['families'] or [{}]:
                original = report['assessments'].get(family.get('original_id'),{})
                replacement = report['assessments'].get(family.get('replacement_id'),{})
                row = {k:family.get(k,'') for k in ('original_id','replacement_id','selected_id','disposition','explanation')}
                row.update(run_id=run_id,cutoff=scenario['cutoff'],original_quality=original.get('base_score'),
                           original_max_cosine=original.get('max_historical_cosine'),replacement_quality=replacement.get('base_score'),
                           replacement_max_cosine=replacement.get('max_historical_cosine'))
                for k in ('original_reasons','replacement_reasons'):
                    row[k] = json.dumps(family.get(k))
                row['current_batch_flags'] = json.dumps(scenario['current_batch_flags'].get(family.get('selected_id'),[]))
                row['counts'] = json.dumps(scenario['counts'],sort_keys=True)
                row['assessment_snapshot'] = json.dumps(report['assessment_snapshot'],sort_keys=True)
                writer.writerow({k:("'"+v if isinstance(v,str) and v.lstrip().startswith(('=','+','-','@')) else v) for k,v in row.items()})
        return Response(output.getvalue(),media_type='text/csv',headers={'Content-Disposition':'attachment; filename="angle-comparison.csv"'})
    @routes.post('/weeks/{week_id}/runs',status_code=202)
    def submit(week_id:str,payload:RunRequest,subject:str=Depends(actor)):
        return action(repo.submit,week_id,payload.mode,actor=subject,workflow=payload.workflow)
    @routes.post('/weeks/{week_id}/reassess',status_code=202)
    def reassess(week_id:str,subject:str=Depends(actor)):
        return action(gate_one.reassess,repo,week_id,subject)
    @routes.post('/jobs/{job_id}/retry',status_code=202)
    def retry(job_id:str,subject:str=Depends(actor)):
        action(repo.retry,job_id,subject); return {'status':'queued'}
    @routes.post('/runs/{run_id}/encode',status_code=202)
    def encode(run_id:str,payload:RunRequest,subject:str=Depends(actor)):
        return action(queue_encoding,repo,run_id,'cached' if payload.mode=='replay' else payload.mode,subject)
    @routes.patch('/angles/{angle_id}')
    def edit(angle_id:str,payload:Edit,subject:str=Depends(actor)):
        return action(gate_one.edit,repo,angle_id,payload.expected_hash,payload.changes,subject)
    @routes.post('/angles/{angle_id}/quality')
    def quality(angle_id:str,payload:Assessment,subject:str=Depends(actor)):
        action(gate_one.rescore,repo,angle_id,payload.expected_hash,payload.scores,subject); return {'status':'saved'}
    @routes.post('/angles/{angle_id}/decision')
    def decision(angle_id:str,payload:Decision,subject:str=Depends(actor)):
        return action(gate_one.decide,repo,angle_id,payload.expected_hash,payload.decision,payload.cta,payload.overlap_acknowledged,payload.note,subject)
    from .briefs import gate_two as briefs
    from .briefs.workflow import queue as queue_brief
    @routes.get('/briefs/contract')
    def brief_contract():
        from .briefs.contracts import BriefDocument
        return BriefDocument.model_json_schema()
    @routes.get('/briefs')
    def brief_list(week_id:str|None=None,status:Literal['pending','approved','rejected']|None=None,
                   limit:int=Query(default=20,ge=1,le=100),offset:int=Query(default=0,ge=0),subject:str=Depends(actor)):
        with repo.connection() as conn:
            rows=conn.execute("""SELECT b.brief_id FROM content_briefs b WHERE (%s::text IS NULL OR week_id=%s)
                AND (%s::text IS NULL OR approval_status=%s) AND NOT EXISTS (SELECT 1 FROM content_briefs n WHERE n.supersedes_id=b.brief_id)
                ORDER BY created_at DESC,brief_id LIMIT %s OFFSET %s""",(week_id,week_id,status,status,limit,offset)).fetchall()
            total=conn.execute("""SELECT count(*) n FROM content_briefs b WHERE (%s::text IS NULL OR week_id=%s)
                AND (%s::text IS NULL OR approval_status=%s) AND NOT EXISTS (SELECT 1 FROM content_briefs n WHERE n.supersedes_id=b.brief_id)""",(week_id,week_id,status,status)).fetchone()['n']
        return {'items':[action(briefs.get,repo,r['brief_id'],subject) for r in rows],'total':total,'limit':limit,'offset':offset}
    @routes.get('/briefs/{brief_id}')
    def brief_detail(brief_id:str,subject:str=Depends(actor)): return action(briefs.get,repo,brief_id,subject)
    @routes.get('/briefs/{brief_id}/versions')
    def brief_versions(brief_id:str): return action(briefs.versions,repo,brief_id)
    @routes.get('/briefs/{brief_id}/export.json')
    def brief_json(brief_id:str,subject:str=Depends(actor)): return action(briefs.get,repo,brief_id,subject)
    @routes.get('/briefs/{brief_id}/export.md')
    def brief_markdown(brief_id:str,subject:str=Depends(actor)):
        row=action(briefs.get,repo,brief_id,subject)
        return Response(briefs.markdown(row),media_type='text/markdown',headers={'Content-Disposition':'attachment; filename="content-brief.md"'})
    @routes.get('/angles/{angle_id}/research')
    def research_status(angle_id:str): return action(briefs.research,repo,angle_id)
    @routes.post('/angles/{angle_id}/brief',status_code=202)
    def start_brief(angle_id:str,payload:RunRequest,subject:str=Depends(actor)):
        action(briefs.authorize,repo,subject)
        return action(queue_brief,repo,angle_id,subject,payload.mode)
    @routes.patch('/briefs/{brief_id}')
    def edit_brief(brief_id:str,payload:Edit,subject:str=Depends(actor)):
        return action(briefs.edit,repo,brief_id,payload.expected_hash,payload.changes,subject)
    @routes.post('/briefs/{brief_id}/answers')
    def answer_brief(brief_id:str,payload:BriefAnswers,subject:str=Depends(actor)):
        return action(briefs.answers,repo,brief_id,payload.expected_hash,payload.answers,subject)
    @routes.post('/briefs/{brief_id}/review')
    def review_brief(brief_id:str,payload:BriefReview,subject:str=Depends(actor)):
        return action(briefs.review,repo,brief_id,payload.expected_hash,payload.claim_ids,payload.reason,payload.history_acknowledged,subject)
    @routes.post('/briefs/{brief_id}/clearance')
    def clear_brief(brief_id:str,payload:Clearance,subject:str=Depends(actor)):
        return action(briefs.clearance,repo,brief_id,payload.expected_hash,payload.evidence_id,payload.permission_reference,payload.attribution_reference,subject)
    @routes.post('/briefs/{brief_id}/decision')
    def decide_brief(brief_id:str,payload:Decision,subject:str=Depends(actor)):
        return action(briefs.decide,repo,brief_id,payload.expected_hash,payload.decision,payload.note,subject)
    @routes.post('/briefs/{brief_id}/revise',status_code=202)
    def revise_brief(brief_id:str,payload:BriefRevision,subject:str=Depends(actor)):
        row=action(briefs.get,repo,brief_id,subject)
        data=action(briefs.research,repo,row['angle_id'])
        byid={e['evidence_id']:e for e in (data.get('dossier') or {}).get('evidence',[])}
        if len(set(payload.evidence_ids))!=len(payload.evidence_ids) or not set(payload.evidence_ids).issubset(byid):
            raise HTTPException(409,'Added context must use inspected current research evidence IDs')
        return action(briefs.revise,repo,brief_id,payload.expected_hash,payload.instructions,subject,payload.mode,[byid[i] for i in payload.evidence_ids])
    @routes.post('/search/transcripts')
    def transcript_search(payload:SearchRequest):
        from .briefs.search import cached_search
        return action(cached_search,repo,payload.text,payload.k,payload.transcript_ids)
    from .production_api import install
    install(routes, repo, actor, action)
    return routes
