"""Optional bounded external framing interface; never an internal proof source."""
from datetime import datetime,UTC,timedelta
from urllib.parse import urlparse
from pydantic import Field
from ..contracts import Contract,Text
from ..store import canonical_hash
from ..store import JsonStore
from typing import Protocol
import re
from .contracts import EvidenceItem

class WebFinding(Contract):
    url: Text
    title: Text
    published_at: Text
    excerpt: Text

class WebResponse(Contract):
    findings: list[WebFinding] = Field(max_length=10)
    usage: dict | None = None

class WebResearchProvider(Protocol):
    def research(self,*,topic:str,questions:list[str],fingerprint:str)->dict: ...

def sanitize(topic,dossier):
    value=topic
    for e in dossier.evidence:
        for name in (e.speaker,e.title):
            if name: value=re.sub(re.escape(name),'[redacted]',value,flags=re.I)
    if 'http://' in value or 'https://' in value or '@' in value:
        raise ValueError('External query contains identifying/link data')
    if re.search(r'\b\+?\d[\d\s()-]{7,}\d\b',value): raise ValueError('External query contains a possible private contact identifier')
    return value

def enrich(worker,job,run,dossier):
    if not worker.storage.brief_web_enabled: return dossier
    # A deliberately explicit provider interface: no hidden web-enabled chat call.
    provider=getattr(worker,'web_provider',None)
    if not provider:
        dossier.coverage['external']='unavailable'
        dossier.gaps.append('External framing unavailable: no authorized web adapter is configured.')
        return dossier
    try:
        # An approved public packet avoids relying on incomplete entity extraction
        # to sanitize derived business/client context. Private source text stays local.
        public=dossier.brand['documents'].get('public_research')
        if not isinstance(public,dict) or not public.get('topic'):
            raise ValueError('Reviewed public research topic/questions are missing from the brand bundle')
        topic=sanitize(public['topic'],dossier)
        questions=[sanitize(q,dossier) for q in public.get('questions',[])[:4]]
        request={'topic':topic,'questions':questions,'as_of':run['created_at'].isoformat(),'lookback_days':90,
            'allowed_domains':public.get('allowed_domains',[]),'synthetic':worker.storage.synthetic}
        fp=canonical_hash(request); base=f'brief-web/{fp}';store=JsonStore(worker.storage.artifact_root)
        store.write_json(base+'/request.json',request)
        from .billing import record
        dispatched=False
        if store.path(base+'/response.raw.json').is_file(): raw=store.read_json(base+'/response.raw.json')
        else:
            mode=run['input_refs']['mode']
            if not (mode=='synthetic' and worker.storage.synthetic or mode=='live' and worker.storage.brief_live_enabled and worker.storage.generation_enabled):
                raise ValueError('External framing is not cached; replay never dispatches a web provider')
            with worker.repo.connection() as conn:
                worker.repo.guard(conn,job)
                previous=conn.execute("SELECT 1 FROM pipeline_events WHERE run_id=%s AND event_type='brief_web_dispatch'",(run['run_id'],)).fetchone()
                if previous: raise ValueError('External request already dispatched; explicit recovery is required')
                worker.repo.event(conn,run['run_id'],'brief_web_dispatch','Bounded public external framing request',job=job,details={'fingerprint':fp,'artifact':base+'/request.json'})
            record(worker,job,run,'brief_web',fp,dispatched=True)
            dispatched=True
            raw=provider.research(topic=topic,questions=questions,fingerprint=fp)
            store.write_json(base+'/response.raw.json',raw)
        record(worker,job,run,'brief_web',fp,raw,dispatched=dispatched,reused=not dispatched)
        response=WebResponse.model_validate(raw)
        now=datetime.fromisoformat(run['created_at'].isoformat())
        admitted=[];dates={}
        for finding in response.findings:
            parsed=urlparse(finding.url); date=datetime.fromisoformat(finding.published_at.replace('Z','+00:00'))
            allowed=request['allowed_domains']
            if parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password or date.tzinfo is None or not now-timedelta(days=90)<=date<=now or allowed and parsed.hostname not in allowed:
                raise ValueError('External framing URL/date is not admissible')
            eid='external_'+canonical_hash(finding.model_dump())[:24]
            admitted.append(EvidenceItem(evidence_id=eid,excerpt=finding.excerpt,
                title=finding.title,source_url=finding.url,role='external_framing'))
            dates[eid]=finding.published_at
        dossier.evidence.extend(admitted)
        dossier.coverage['external_publication_dates']=dates
        dossier.coverage['external']='completed'
        dossier.audit.append({'external_request':base+'/request.json','external_response':base+'/response.raw.json','hash':canonical_hash(raw)})
    except (ValueError,RuntimeError) as error:
        dossier.coverage['external']='unavailable'; dossier.gaps.append('External framing unavailable: '+str(error))
    return dossier
