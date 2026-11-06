from __future__ import annotations

import csv
import io
import json
from datetime import date
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field, StrictInt
from .storage_config import StorageSettings
from .repository import ContentRepository
from .errors import NeedsInput
from . import gate_one
from .gates import decisions as dispositions
from .gates import rubric
from .sql_pipeline import queue_encoding
from .angle_workflow import LEGACY
from .gates import access
from .api_models import (
    AngleContextResult, AngleResearch, BriefContextResult, BriefHandoff, BriefPage, BriefPublishedPage, BriefVersion, BriefWriteResult, CardRefreshQueued, Flags, Me,
    PublishedCaptureResult, Seed, StanceConfirmed,
    StoredBriefV1, StoredBriefV2, StoredBriefV3, StoredBriefV4, StoredWeek, StrategyBrief, TranscriptOriginal, WeekReview, returns,
)


class Payload(BaseModel):
    model_config = ConfigDict(extra='forbid')

class RunRequest(Payload):
    mode: str = 'replay'
    workflow: Literal['two_call_v1','historical_comparison_v1'] = LEGACY

class BriefStart(RunRequest):
    # A fresh run for the same approved card after its pinned context changed mid-run (V13, 4.B1's counter).
    regenerate: bool = False

class Edit(Payload):
    expected_hash: str
    changes: dict
    # Required when an approver moves an opportunity out of research_required (S.B3).
    note: str | None = Field(default=None,max_length=2000)

class Assessment(Payload):
    expected_hash: str
    scores: dict

class Decision(Payload):
    expected_hash: str
    decision: str
    cta: dict | None = None
    overlap_acknowledged: bool = False
    note: str | None = None
    # Strategist cards: every verify-before-publishing item, acknowledged at approval.
    verify_acknowledged: list[str] = Field(default_factory=list,max_length=40)

class AngleDecision(Decision):
    """Gate 1 for a card: a disposition (E.B20), or the earlier approve or reject for earlier angles."""
    decision: str | None = None
    disposition: Literal['develop','reframe','hold','internal','skip'] | None = None
    reason_code: str | None = Field(default=None,max_length=40)
    author: str | None = Field(default=None,max_length=200)
    reframe: dict[str,str] | None = None
    central_point_kept: bool | None = None
    hold_until: date | None = None
    # Rubric 2.3a ratings of the card (E.X7): every criterion 1 to 5, against the version the form showed (both required
    # together; gates/rubric.py checks them, and a refused set is a 422 that records nothing).
    rubric_ratings: dict[str,StrictInt] | None = None
    rubric_version: str | None = Field(default=None,max_length=40)

class ConsideredDecision(Payload):
    expected_hash: str
    disposition: Literal['hold','internal','skip']
    reason_code: str = Field(max_length=40)
    note: str | None = Field(default=None,max_length=2000)
    author: str | None = Field(default=None,max_length=200)
    hold_until: date | None = None

class StanceConfirmation(Payload):
    """An approver confirms the public stance a strategist v7 card takes (D31, E.B30) before it is developed."""
    expected_hash: str
    note: str | None = Field(default=None,max_length=2000)

class Revival(Payload):
    expected_hash: str
    card: dict[str,str|None]
    reason_code: str | None = Field(default=None,max_length=40)
    note: str | None = Field(default=None,max_length=2000)
    author: str | None = Field(default=None,max_length=200)

class CardRefreshRequest(Payload):
    """Refresh with feedback (3.B7): a new card version written from the reviewer's words; fields a person edited stay."""
    expected_hash: str
    feedback: str = Field(min_length=1,max_length=4000)
    author: str | None = Field(default=None,max_length=200)
    # Unset: live (synthetic on a test database). replay serves saved answers only.
    mode: Literal['live','replay'] | None = None

class SeedRequest(Payload):
    kind: Literal['thought','draft','asset','founder_note']
    text: str = Field(min_length=1,max_length=8000)
    target_offer: str | None = Field(default=None,max_length=200)
    source_url: str | None = Field(default=None,max_length=2000)
    author: str | None = Field(default=None,max_length=200)
    week_id: str | None = Field(default=None,max_length=140)
    always_true: bool = False
    # A founder note's call (L.B13); refused on any other kind.
    transcript_id: str | None = Field(default=None,max_length=140)

class BriefDecision(Payload):
    expected_hash: str
    decision: Literal['approved','rejected']
    note: str | None = Field(default=None,max_length=2000)
    # E.F1 on briefs: the reason and whose judgement it records (R45).
    reason_code: str | None = Field(default=None,max_length=40)
    author: str | None = Field(default=None,max_length=200)
    # E.X9: the reviewer's ratings on review rubric 2.3a, all criteria or none, with the version the form showed (as Gate 1).
    rubric_ratings: dict[str,StrictInt] | None = None
    rubric_version: str | None = Field(default=None,max_length=40)

class CtaConfirmation(Payload):
    expected_hash: str
    choice: Literal['explicit','no_explicit_ask']
    action: str | None = Field(default=None,max_length=300)
    track: str | None = Field(default=None,max_length=200)
    offer_connection: str | None = Field(default=None,max_length=300)

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
    # The screen refreshes live (5.B6); replay stays a test mode. The default is kept for older callers.
    mode: Literal['replay','live']='replay'
    evidence_ids: list[str]=Field(default_factory=list,max_length=40)
    # Locked lines (paths, 5.F5) the reviewer releases for this refresh; every other locked line is kept verbatim.
    unlock: list[str]=Field(default_factory=list,max_length=100)

class GateContext(Payload):
    """Context or an attested fact at either gate (5.B7, R57; interface 2). `author` is whose statement it is when a team
    member relays it (R45); the signed-in person when left out."""
    kind: Literal['context','attested_fact','paraphrase']
    text: str = Field(min_length=1,max_length=4000)
    author: str | None = Field(default=None,max_length=200)

class PublishedFigure(Payload):
    metric: str = Field(min_length=1,max_length=100)
    value: str = Field(min_length=1,max_length=500)
    # The day the figure was read; the publish date when left out.
    on: date | None = None
    direction: Literal['positive','negative'] | None = None

class PublishedFinal(Payload):
    """A published final recorded against its approved brief (L.B9)."""
    channel: Literal['reel','carousel','email','caption','stories']
    title: str = Field(min_length=1,max_length=2000)
    text: str = Field(min_length=1,max_length=20000)
    published_on: date
    url: str | None = Field(default=None,max_length=2000)
    # Which reel, when the brief plans more than one; every other channel has one piece.
    piece: int = Field(default=1,ge=1,le=3)
    metrics: list[PublishedFigure] = Field(default_factory=list,max_length=20)

class SearchRequest(Payload):
    text: str=Field(min_length=1,max_length=2000)
    k: int=Field(default=20,ge=1,le=50)
    transcript_ids: list[str]=Field(default_factory=list,max_length=100)


def router(settings=None):
    settings = settings or StorageSettings.from_env()
    repo = ContentRepository(settings)
    # One set of dependencies for every route (gates/access.py, 0.B9): the shared secret, then the verified email
    # (R37), then its roles from the users table or the legacy lists. `actor` is the secret check alone, applied to
    # the whole router; `decider` resolves the roles and is on every mutating route; `reader` does the same for the
    # reads that only mark what the caller may do.
    actor, decider, reader = access.dependencies(lambda: settings.api_secret, repo)
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
        except LookupError as e:
            # An unknown item, version or piece (L.B3): not found, not a server error. A KeyError or IndexError is a
            # defect, not a missing record, and stays a 500.
            if isinstance(e,(KeyError,IndexError)):
                raise
            raise HTTPException(404,str(e)) from e
        except NeedsInput as e:
            raise HTTPException(422,str(e)) from e
        except ValueError as e:
            raise HTTPException(409,str(e)) from e
        except PermissionError as e:
            raise HTTPException(403,str(e)) from e
    @routes.get('/flags',responses=returns(Flags))
    def flags():
        # One read-only answer for the app (S.B11): out-of-scope features are hidden unless switched on (R31).
        current = repo.settings  # features.* settings change without a restart (0.B8)
        from .settings_store import value as setting
        return {'briefs':current.brief_enabled,'packs':current.packs_enabled,'calendar':current.calendar_enabled,
                'context':current.context_enabled,**({'one_click':True} if setting('gates.one_click') else {})}
    @routes.get('/weeks',responses=returns(list[StoredWeek]))
    def weeks(include_archived:bool=Query(default=False)):
        # An archived week (week_archive.py: superseded or below the standard) stays out of the app's lists unless asked.
        with repo.connection() as c:
            return c.execute("SELECT * FROM weeks WHERE %s OR status<>'archived' ORDER BY week_start DESC",(include_archived,)).fetchall()
    @routes.get('/weeks/{week_id}',responses=returns(WeekReview))
    def review(week_id:str,subject:str=Depends(reader)):
        # Capabilities on the review answer what this person's email may decide (S.B3, R37).
        return action(repo.review,week_id,subject)
    @routes.get('/me',responses=returns(Me))
    def me(subject:str=Depends(decider)):
        # Who the signed-in person is to this system (0.B9): their roles and what they may do, from the same
        # resolution every route uses. Read-only; anyone Command Center admits may ask. Nothing here grants access.
        return subject.access.describe()
    @routes.get('/transcripts/{transcript_id}',responses=returns(TranscriptOriginal))
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
    def submit(week_id:str,payload:RunRequest,subject:str=Depends(decider)):
        # The worker's angle profile is validated and frozen at submit, before extraction is paid for.
        from .config import Settings
        action(gate_one.require,repo,subject,'decide' if payload.mode=='live' else 'edit')
        return action(repo.submit,week_id,payload.mode,actor=subject,workflow=payload.workflow,models=Settings.from_env(database_url=settings.database_url))
    @routes.post('/weeks/{week_id}/reassess',status_code=202)
    def reassess(week_id:str,subject:str=Depends(decider)):
        return action(gate_one.reassess,repo,week_id,subject)
    @routes.post('/jobs/{job_id}/retry',status_code=202)
    def retry(job_id:str,subject:str=Depends(decider)):
        action(gate_one.require,repo,subject,'edit')
        action(repo.retry,job_id,subject); return {'status':'queued'}
    @routes.post('/runs/{run_id}/encode',status_code=202)
    def encode(run_id:str,payload:RunRequest,subject:str=Depends(decider)):
        action(gate_one.require,repo,subject,'decide' if payload.mode=='live' else 'edit')
        return action(queue_encoding,repo,run_id,'cached' if payload.mode=='replay' else payload.mode,subject)
    @routes.patch('/angles/{angle_id}')
    def edit(angle_id:str,payload:Edit,subject:str=Depends(decider)):
        return action(gate_one.edit,repo,angle_id,payload.expected_hash,payload.changes,subject,payload.note)
    @routes.post('/angles/{angle_id}/quality')
    def quality(angle_id:str,payload:Assessment,subject:str=Depends(decider)):
        action(gate_one.rescore,repo,angle_id,payload.expected_hash,payload.scores,subject); return {'status':'saved'}
    @routes.post('/angles/{angle_id}/decision')
    def decision(angle_id:str,payload:AngleDecision,subject:str=Depends(decider)):
        if payload.disposition:
            if payload.decision:
                raise HTTPException(422,'Send a disposition or a decision, not both')
            if payload.rubric_ratings:
                if not payload.rubric_version:
                    raise HTTPException(422,'Rubric ratings need the rubric version the form showed')
                try:
                    rubric.ratings(payload.rubric_ratings,payload.rubric_version)
                except ValueError as e:
                    raise HTTPException(422,str(e)) from e
            return action(dispositions.dispose,repo,angle_id,payload.expected_hash,payload.disposition,subject,
                          reason_code=payload.reason_code,note=payload.note,author=payload.author,reframe=payload.reframe,
                          central_point_kept=payload.central_point_kept,hold_until=payload.hold_until,cta=payload.cta,
                          overlap_ack=payload.overlap_acknowledged,verified=payload.verify_acknowledged,
                          rubric_ratings=payload.rubric_ratings,rubric_version=payload.rubric_version)
        if payload.rubric_ratings:
            raise HTTPException(422,'Rubric ratings go with a disposition on a strategist card')
        if not payload.decision:
            raise HTTPException(422,'A disposition or a decision is required')
        return action(gate_one.decide,repo,angle_id,payload.expected_hash,payload.decision,payload.cta,payload.overlap_acknowledged,payload.note,subject,
                      verified=payload.verify_acknowledged)
    @routes.post('/angles/{angle_id}/stance',responses=returns(StanceConfirmed))
    def confirm_stance(angle_id:str,payload:StanceConfirmation,subject:str=Depends(decider)):
        # D31: a card that takes a public stance is developed only after an approver confirms it (E.B30).
        return action(gate_one.confirm_stance,repo,angle_id,payload.expected_hash,subject,payload.note)
    @routes.get('/strategy-brief',responses=returns(StrategyBrief))
    def strategy_brief_preview(on:date|None=None,subject:str=Depends(reader)):
        # The window's strategy brief a cycle started on that date would be given (E.B28); no model call, nothing stored.
        from .config import Settings
        from .cycle.strategy_brief import assemble_for
        return action(assemble_for,Settings.from_env(database_url=settings.database_url),repo.connection,on or date.today(),'cached')
    @routes.post('/angles/{angle_id}/refresh',status_code=202,responses=returns(CardRefreshQueued,202))
    def refresh_card(angle_id:str,payload:CardRefreshRequest,subject:str=Depends(decider)):
        # 3.B7: an editor or approver, against the version they read (a stale hash is a 409 the screen shows as a conflict).
        from .cycle import refresh
        from .jobs.dispatch import kick
        result=action(refresh.queue,repo,angle_id,payload.expected_hash,payload.feedback,subject,author=payload.author,mode=payload.mode)
        kick(repo,run_id=result['run_id'])
        return result
    @routes.post('/weeks/{week_id}/considered/{index}/revive',status_code=201)
    def revive(week_id:str,index:int,payload:Revival,subject:str=Depends(decider)):
        return action(dispositions.revive,repo,week_id,index,payload.expected_hash,payload.card,subject,
                      reason_code=payload.reason_code,note=payload.note,author=payload.author)
    @routes.post('/weeks/{week_id}/considered/{index}/decision')
    def considered(week_id:str,index:int,payload:ConsideredDecision,subject:str=Depends(decider)):
        return action(dispositions.considered_decision,repo,week_id,index,payload.expected_hash,payload.disposition,subject,
                      reason_code=payload.reason_code,note=payload.note,author=payload.author,hold_until=payload.hold_until)
    from .cycle import seeds as founder_seeds
    @routes.get('/seeds',responses=returns(list[Seed]))
    def seed_list(status:Literal['open','used','withdrawn']|None=None):
        return action(founder_seeds.listing,repo,status)
    @routes.post('/seeds',status_code=201)
    def seed_add(payload:SeedRequest,subject:str=Depends(decider)):
        return action(founder_seeds.add,repo,subject,**payload.model_dump())
    @routes.post('/seeds/{seed_id}/withdraw')
    def seed_withdraw(seed_id:str,subject:str=Depends(decider)):
        return action(founder_seeds.withdraw,repo,seed_id,subject)
    from .briefs import gate_two as briefs
    from .briefs.workflow import queue as queue_brief
    @routes.get('/briefs/contract')
    def brief_contract(schema_version:Literal['brief_document_v1','brief_document_v2','brief_document_v3','brief_document_v4']='brief_document_v1'):
        from .briefs.contracts import BriefDocument
        from .briefs.contracts_v2 import BriefDocumentV2
        from .briefs.contracts_v3 import BriefDocumentV3
        from .briefs.contracts_v4 import BriefDocumentV4
        return {'brief_document_v2':BriefDocumentV2,'brief_document_v3':BriefDocumentV3,
                'brief_document_v4':BriefDocumentV4}.get(schema_version,BriefDocument).model_json_schema()
    @routes.get('/briefs',responses=returns(BriefPage))
    def brief_list(week_id:str|None=None,status:Literal['pending','approved','rejected']|None=None,
                   limit:int=Query(default=20,ge=1,le=100),offset:int=Query(default=0,ge=0),subject:str=Depends(decider)):
        with repo.connection() as conn:
            rows=conn.execute("""SELECT b.brief_id FROM content_briefs b WHERE (%s::text IS NULL OR week_id=%s)
                AND (%s::text IS NULL OR approval_status=%s) AND NOT EXISTS (SELECT 1 FROM content_briefs n WHERE n.supersedes_id=b.brief_id)
                ORDER BY created_at DESC,brief_id LIMIT %s OFFSET %s""",(week_id,week_id,status,status,limit,offset)).fetchall()
            total=conn.execute("""SELECT count(*) n FROM content_briefs b WHERE (%s::text IS NULL OR week_id=%s)
                AND (%s::text IS NULL OR approval_status=%s) AND NOT EXISTS (SELECT 1 FROM content_briefs n WHERE n.supersedes_id=b.brief_id)""",(week_id,week_id,status,status)).fetchone()['n']
        return {'items':[action(briefs.get,repo,r['brief_id'],subject) for r in rows],'total':total,'limit':limit,'offset':offset}
    @routes.get('/briefs/{brief_id}',responses=returns(StoredBriefV1 | StoredBriefV2 | StoredBriefV3 | StoredBriefV4))
    def brief_detail(brief_id:str,subject:str=Depends(decider)): return action(briefs.get,repo,brief_id,subject)
    @routes.get('/briefs/{brief_id}/versions',responses=returns(list[BriefVersion]))
    def brief_versions(brief_id:str): return action(briefs.versions,repo,brief_id)
    @routes.get('/briefs/{brief_id}/handoff',responses=returns(BriefHandoff))
    def brief_handoff(brief_id:str,subject:str=Depends(decider)):
        # E.B23: what production reads for a brief of any contract version; it acts only when can_consume is true.
        return action(briefs.handoff,repo,brief_id,subject)
    @routes.get('/briefs/{brief_id}/export.json')
    def brief_json(brief_id:str,subject:str=Depends(decider)): return action(briefs.get,repo,brief_id,subject)
    @routes.get('/briefs/{brief_id}/export.md')
    def brief_markdown(brief_id:str,subject:str=Depends(decider)):
        row=action(briefs.get,repo,brief_id,subject)
        return Response(briefs.markdown(row),media_type='text/markdown',headers={'Content-Disposition':'attachment; filename="content-brief.md"'})
    @routes.get('/angles/{angle_id}/research',responses=returns(AngleResearch))
    def research_status(angle_id:str): return action(briefs.research,repo,angle_id)
    @routes.post('/angles/{angle_id}/brief',status_code=202)
    def start_brief(angle_id:str,payload:BriefStart,subject:str=Depends(decider)):
        action(briefs.authorize,repo,subject)
        if payload.regenerate:
            from .briefs.workflow import regenerate
            return action(regenerate,repo,angle_id,subject,payload.mode)
        return action(queue_brief,repo,angle_id,subject,payload.mode)
    @routes.post('/angles/{angle_id}/brief/retry',status_code=202)
    def retry_brief(angle_id:str,subject:str=Depends(decider)):
        from .briefs.workflow import retry_unqueued
        return action(retry_unqueued,repo,angle_id,subject)
    @routes.patch('/briefs/{brief_id}',responses=returns(BriefWriteResult))
    def edit_brief(brief_id:str,payload:Edit,subject:str=Depends(decider)):
        return action(briefs.edit,repo,brief_id,payload.expected_hash,payload.changes,subject)
    @routes.post('/briefs/{brief_id}/answers',responses=returns(BriefWriteResult))
    def answer_brief(brief_id:str,payload:BriefAnswers,subject:str=Depends(decider)):
        return action(briefs.answers,repo,brief_id,payload.expected_hash,payload.answers,subject)
    @routes.post('/briefs/{brief_id}/review',responses=returns(BriefWriteResult))
    def review_brief(brief_id:str,payload:BriefReview,subject:str=Depends(decider)):
        return action(briefs.review,repo,brief_id,payload.expected_hash,payload.claim_ids,payload.reason,payload.history_acknowledged,subject)
    @routes.post('/briefs/{brief_id}/clearance',responses=returns(BriefWriteResult))
    def clear_brief(brief_id:str,payload:Clearance,subject:str=Depends(decider)):
        return action(briefs.clearance,repo,brief_id,payload.expected_hash,payload.evidence_id,payload.permission_reference,payload.attribution_reference,subject)
    @routes.post('/briefs/{brief_id}/decision',responses=returns(BriefWriteResult))
    def decide_brief(brief_id:str,payload:BriefDecision,subject:str=Depends(decider)):
        if payload.rubric_ratings:
            if not payload.rubric_version:
                raise HTTPException(422,'Rubric ratings need the rubric version the form showed')
            try:
                rubric.ratings(payload.rubric_ratings,payload.rubric_version)
            except ValueError as e:
                raise HTTPException(422,str(e)) from e
        return action(briefs.decide,repo,brief_id,payload.expected_hash,payload.decision,payload.note,subject,
                      reason_code=payload.reason_code,author=payload.author,rubric_ratings=payload.rubric_ratings,
                      rubric_version=payload.rubric_version)
    @routes.post('/briefs/{brief_id}/cta',responses=returns(BriefWriteResult))
    def confirm_brief_cta(brief_id:str,payload:CtaConfirmation,subject:str=Depends(decider)):
        return action(briefs.confirm_cta,repo,brief_id,payload.expected_hash,payload.model_dump(exclude={'expected_hash'}),subject)
    @routes.post('/briefs/{brief_id}/revise',status_code=202,responses=returns(BriefWriteResult, 202))
    def revise_brief(brief_id:str,payload:BriefRevision,subject:str=Depends(decider)):
        # The role first: whether this brief exists is not for a viewer to learn from the error.
        action(briefs.authorize,repo,subject)
        row=action(briefs.get,repo,brief_id,subject)
        data=action(briefs.research,repo,row['angle_id'])
        byid={e['evidence_id']:e for e in (data.get('dossier') or {}).get('evidence',[])}
        if len(set(payload.evidence_ids))!=len(payload.evidence_ids) or not set(payload.evidence_ids).issubset(byid):
            raise HTTPException(409,'Added context must use inspected current research evidence IDs')
        return action(briefs.revise,repo,brief_id,payload.expected_hash,payload.instructions,subject,payload.mode,[byid[i] for i in payload.evidence_ids],
                      payload.unlock)
    from .briefs import context as gate_context
    @routes.post('/angles/{angle_id}/context',status_code=201,responses=returns(AngleContextResult,201))
    def angle_context(angle_id:str,payload:GateContext,subject:str=Depends(decider)):
        # Gate 1 (5.B7): context, a paraphrase, or a fact an approver attests, on a card; it reaches the card's brief.
        return action(gate_context.add_to_angle,repo,angle_id,payload.kind,payload.text,subject,payload.author)
    @routes.post('/briefs/{brief_id}/context',status_code=201,responses=returns(BriefContextResult,201))
    def brief_context(brief_id:str,payload:GateContext,subject:str=Depends(decider)):
        # Gate 2 (5.B7): a new brief version holding the item; an attested fact settles the copy that states it (R57).
        return action(gate_context.add_to_brief,repo,brief_id,payload.kind,payload.text,subject,payload.author)
    from .knowledge import capture
    @routes.get('/briefs/{brief_id}/published',responses=returns(BriefPublishedPage))
    def brief_published(brief_id:str):
        return action(capture.listing,repo,brief_id)
    @routes.post('/briefs/{brief_id}/published',status_code=201,responses={**returns(PublishedCaptureResult,201),**returns(PublishedCaptureResult)})
    def record_published(brief_id:str,payload:PublishedFinal,response:Response,subject:str=Depends(decider)):
        # L.B9: an editor or approver records what WIA published from an approved brief. 201 when this request stored it,
        # 200 when the same final was already recorded (only figures not yet recorded are added).
        result=action(capture.record,repo,brief_id,subject,**payload.model_dump())
        if not result['created']: response.status_code=200
        return result
    @routes.post('/search/transcripts')
    def transcript_search(payload:SearchRequest,subject:str=Depends(decider)):
        # A read, but a POST: it names the verified email like every other POST (any role may search).
        from .briefs.search import cached_search
        return action(cached_search,repo,payload.text,payload.k,payload.transcript_ids)
    from .knowledge.api import install as install_context
    install_context(routes, settings, repo, actor, decider, action)
    from .production_api import install
    install(routes, repo, decider, reader, action)
    from .settings_api import install as install_settings
    install_settings(routes, repo, decider, action)
    # Phase 2: extraction health first (the documents API would read "extraction-health" as a document id), then the moments
    # ledger and the topic registry (GET /moments/{id} is theirs now), then the search route.
    from .moments.health import install as install_health
    install_health(routes, repo, reader, action)
    from .moments.api import install as install_moments
    install_moments(routes, repo, decider, reader, action)
    from .search.api import install as install_search
    install_search(routes, repo, decider, action)
    from .documents.api import install as install_documents
    install_documents(routes, repo, decider, reader, action)
    # A cycle over a date window from the app (3.B2/3.B3), the standing budgets (6.B3) and the week's review document (5.B14).
    from .cycle.api import install as install_cycles
    install_cycles(routes, repo, decider, reader, action, settings)
    # Failure alerts (6.B4): what the scheduler's scan found, for the Sources screen and the bell.
    from .alerts import install as install_alerts
    install_alerts(routes, settings, reader, decider, action)
    # Home's cycle summary (6.F2) and the scheduled cycle's next run (3.B11).
    from .summary import install as install_summary
    install_summary(routes, settings, reader, action)
    # The week's measures and editorial monitoring (7.X2, 6.B13), for the cycle screen.
    from .week_measures import install as install_measures
    install_measures(routes, repo, reader, action)
    return routes
