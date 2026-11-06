import json
import re
from psycopg.types.json import Jsonb
from ..store import canonical_hash
from ..repository import insert,identifier
from .contracts import BriefDocument,Dossier,SupportReview
from .inputs import verify_evidence,assert_packet
from .runtime import call

def checks(document,dossier,clearances=None):
    doc=BriefDocument.model_validate(document) if isinstance(document,dict) else document
    d=Dossier.model_validate(dossier) if isinstance(dossier,dict) else dossier
    evidence={e.evidence_id:e for e in d.evidence}; findings=[]
    def block(message,claim_id=None): findings.append({'severity':'blocking','claim_id':claim_id,'message':message})
    if doc.angle_statement!=d.angle['body']['argument'] or doc.audience!=d.angle['body']['audience'] or doc.reader_decision!=d.angle['body']['reader_decision']:
        block('Approved argument, audience or reader decision changed')
    if doc.cta!=d.angle['cta']: block('CTA differs from the approved CTA')
    if sorted(s.number for s in doc.carousel)!=list(range(1,9)): block('Carousel must have eight unique ordered slide numbers')
    if len({r.reader_job for r in doc.reels})!=3: block('Reel reader jobs must be distinct')
    if len({c.claim_id for c in doc.claims})!=len(doc.claims): block('Claim identifiers are duplicated')
    if len({q.question_id for q in doc.open_questions})!=len(doc.open_questions): block('Question identifiers are duplicated')
    if len(set(doc.sources))!=len(doc.sources) or not set(doc.sources).issubset(evidence): block('Source list contains unknown or duplicate evidence IDs')
    if doc.claims_requiring_consent: block('Unresolved consent requirements must be cleared and reviewed before approval')
    referenced=set()
    for claim in doc.claims:
        referenced.update(claim.evidence_ids)
        if not set(claim.evidence_ids).issubset(evidence):
            block('Claim references unknown evidence',claim.claim_id); continue
        values=[evidence[i] for i in claim.evidence_ids]
        if claim.kind in {'source_assertion','external_context'} and not values: block('Factual claim lacks evidence',claim.claim_id)
        if claim.kind=='source_assertion' and any(e.role=='external_framing' for e in values): block('External framing cannot establish an internal result',claim.claim_id)
        if claim.kind=='external_context' and any(e.role!='external_framing' for e in values): block('External claim must cite its external source',claim.claim_id)
        if claim.kind=='source_assertion':
            if not all(set(e.qualifications).issubset(claim.qualifications) for e in values): block('Source qualifications were lost',claim.claim_id)
            known={e.claim_status for e in values if e.claim_status!='unknown'}
            if claim.source_status not in (known or {'unknown'}): block('Claim status exceeds the source status',claim.claim_id)
            if re.search(r'\d',claim.text) and not claim.numeric_facts: block('Numerical factual claim lacks structured supporting facts',claim.claim_id)
        if claim.quote and not any(claim.quote in e.excerpt for e in values): block('Quotation does not match original wording',claim.claim_id)
        if claim.public_quote and not claim.quote: block('Public quotation lacks original wording',claim.claim_id)
        if claim.public_quote and not any(claim.quote and claim.quote in e.excerpt and
            (e.public_use and e.attribution_verified and e.sensitivity!='internal_only' or (clearances or {}).get(e.evidence_id)) for e in values):
            block('Public quotation requires explicit source-use and attribution clearance',claim.claim_id)
        for fact in claim.numeric_facts:
            e=evidence.get(fact.evidence_id)
            if not e or fact.evidence_id not in claim.evidence_ids or fact.source_quote not in e.excerpt:
                block('Numeric fact is not bound to the cited source range',claim.claim_id); continue
            if any(part.casefold() not in fact.source_quote.casefold() for part in (fact.value,fact.unit,fact.timeframe,fact.subject)):
                block('Numeric value/unit/timeframe/subject does not resolve in its supporting quote',claim.claim_id)
    referenced.update(i for r in [doc.email,*doc.reels] for i in r.evidence_ids)
    referenced.update(i for slide in doc.carousel for i in slide.evidence_ids)
    if not referenced.issubset(evidence) or not referenced.issubset(doc.sources): block('Format/claim evidence references must resolve in the source list')
    prior={p.angle_id for p in d.prior}
    if not prior.issubset(doc.prior_differences) or not set(doc.prior_differences).issubset(prior): block('Prior coverage differences must cover each supplied historical argument')
    factual_prose=' '.join([doc.reader_promise,doc.why_now,doc.core_insight,doc.audience_pain,*doc.message_spine,*doc.narrative,
        doc.email.direction,*doc.email.outline,*[s.direction for s in doc.carousel],*[r.direction for r in doc.reels]])
    supported_numbers={n for c in doc.claims for f in c.numeric_facts for n in re.findall(r'\d+(?:\.\d+)?',f.value)}
    if set(re.findall(r'\d+(?:\.\d+)?',factual_prose))-supported_numbers:
        block('Numerical prose requires a structured source-bound claim; format numbering is supplied separately')
    body=json.dumps(doc.model_dump(),ensure_ascii=False)
    for e in d.evidence:
        if e.speaker and not (e.public_use and e.attribution_verified or (clearances or {}).get(e.evidence_id)) and re.search(r'\b'+re.escape(e.speaker)+r'\b',body,re.I):
            block('Private speaker name appears without source clearance')
    findings.append({'severity':'warning','claim_id':None,'message':'Legacy publication coverage is incomplete; this is an admitted-archive review.'})
    return findings

def review_findings(review,doc,evidence_ids,prior_angle_ids=()):
    if len(review.reviewed_claim_ids)!=len(doc.claims) or set(review.reviewed_claim_ids)!={c.claim_id for c in doc.claims}:
        raise ValueError('Grounding review must cover every claim exactly once')
    # Coverage findings can cite supplied prior arguments. This does not admit
    # those arguments as grounding for current claims: checks() still resolves
    # every claim/format evidence reference against original evidence only.
    permitted_refs=set(evidence_ids)|set(prior_angle_ids)
    if any(f.claim_id and f.claim_id not in review.reviewed_claim_ids or not set(f.evidence_ids).issubset(permitted_refs) for f in review.findings):
        raise ValueError('Grounding review contains unknown claim/evidence IDs')
    findings=[f.model_dump() for f in review.findings]
    if not review.preserves_approved_direction: findings.append({'severity':'blocking','message':'Grounding review found changed approved direction','claim_id':None})
    if not review.distinct_treatment: findings.append({'severity':'blocking','message':'Meaningful historical differentiation remains unresolved','claim_id':None})
    return findings

def hash_brief(row):
    return canonical_hash({k:row[k] for k in ('angle_id','angle_input_hash','content_body','selected_evidence','prior_content_context','research_gaps')})

def unlocked_fields(instructions,fields):
    return {f for f in fields if re.search(r'\b(?:change|revise|rewrite|develop|update)\s+(?:the\s+)?'+re.escape(f)+r'\b',instructions,re.I)}

def finalize(worker,job,run,dossier,document):
    from .gate_two import semantic_hash
    from .runtime import compact_dossier
    d=Dossier.model_validate(dossier); doc=BriefDocument.model_validate(document)
    parent=None
    if run['input_refs'].get('revision_of'):
        from .gate_two import get
        parent=get(worker.repo,run['input_refs']['revision_of'])
        locks=parent['content_body'].get('review',{}).get('locked_fields',[])
        instructions=run['input_refs'].get('instructions') or ''
        for field in locks:
            if field not in unlocked_fields(instructions,locks) and doc.model_dump().get(field)!=parent['content_body']['document'].get(field):
                raise ValueError('Revision changed a locked field without explicit instructions')
    evidence_ids={e.evidence_id for e in d.evidence}
    def assess(value):
        review=call(worker,job,run,'brief_review',SupportReview,{'document':value.model_dump(),'dossier':compact_dossier(d)})
        return checks(value,d)+review_findings(review,value,evidence_ids,{p.angle_id for p in d.prior})
    findings=assess(doc)
    repaired=False
    if any(f['severity']=='blocking' for f in findings):
        doc=call(worker,job,run,'brief_repair',BriefDocument,{'document':doc.model_dump(),'dossier':compact_dossier(d),'failures':findings,'instructions':run['input_refs'].get('instructions'),'locked_fields':parent['content_body']['review']['locked_fields'] if parent else [],'current_brief':parent['content_body'] if parent else None})
        findings=assess(doc); repaired=True
    if parent:
        for field in parent['content_body'].get('review',{}).get('locked_fields',[]):
            if field not in unlocked_fields(run['input_refs'].get('instructions') or '',parent['content_body']['review']['locked_fields']) and doc.model_dump().get(field)!=parent['content_body']['document'].get(field):
                raise ValueError('Repair changed a locked field')
    envelope={'schema_version':'brief_document_v1','document':doc.model_dump(mode='json'),
        'review':{'locked_fields':parent['content_body'].get('review',{}).get('locked_fields',[]) if parent else [],
            'findings':findings,'support_reviewed_document_hash':semantic_hash(doc.model_dump(mode='json')),
            'history_acknowledged':False,'clearances':{},'repair_used':repaired},
        'provenance':{'brand_hash':d.brand['hash'],'dossier_hash':canonical_hash(d.model_dump(mode='json')),
            'run_id':run['run_id'],'angle':d.angle}}
    row={'brief_id':'brief_'+canonical_hash([run['run_id'],doc.model_dump()])[:24],
        'week_id':d.angle['week_id'],'angle_id':d.angle['angle_id'],'angle_input_hash':d.angle['approved_hash'],
        'content_body':envelope,'selected_evidence':[e.model_dump(mode='json') for e in d.evidence],
        'prior_content_context':[p.model_dump(mode='json') for p in d.prior],
        'research_gaps':{'items':d.gaps,'coverage':d.coverage},'supersedes_id':run['input_refs'].get('revision_of')}
    row['content_hash']=hash_brief(row)
    with worker.repo.connection() as conn:
        assert_packet(conn,d.angle); verify_evidence(conn,d.evidence)
        from ..retrieval import check_prior
        check_prior(conn,d.prior)
        if parent:
            from .gate_two import locked
            locked(conn,parent['brief_id'],parent['content_hash'])
        old=conn.execute('SELECT * FROM content_briefs WHERE brief_id=%s',(row['brief_id'],)).fetchone()
        if old and old['content_hash']!=row['content_hash']: raise ValueError('Saved brief identity differs from recovered output')
        insert(conn,'content_briefs',row,conflict=True)
        worker.repo.finish(conn,job,{'brief_id':row['brief_id'],'content_hash':row['content_hash'],'blocking':sum(f['severity']=='blocking' for f in findings)},message='Brief ready for Gate 2')
