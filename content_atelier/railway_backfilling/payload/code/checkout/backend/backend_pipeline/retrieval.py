from .publications import confirmed
"""Filtered exact semantic/full-text discovery. No inference or provider fallback."""
from datetime import datetime, UTC
import numpy as np
from .store import canonical_hash
from .chunk_encoding import contract as chunk_contract, provenance, chunk_view
from .storage_config import encoding_contract
from .matching import vector_valid,vector_digest,history,vector_provenance
from .contracts import signature_from_fields
from .briefs.inputs import source_allowed,source_digest,evidence_from_passage
from .briefs.contracts import PriorItem

def archive(conn, models, synthetic):
    sources=[s for s in conn.execute('SELECT * FROM transcripts ORDER BY transcript_id') if source_allowed(s)]
    # Legacy admission remains strict. Live revisions enter research only when
    # fully indexed and current; receiving a new item cannot disable the archive.
    if any((s['source_metadata'] or {}).get('intake') for s in sources):
        ready={r['transcript_id'] for r in conn.execute("""SELECT r.transcript_id FROM intake_revisions r
            JOIN intake_sources s ON s.latest_revision_id=r.revision_id
            WHERE r.indexing_status='ready' AND NOT r.deleted
              AND (s.kind<>'attachment' OR EXISTS (
                SELECT 1 FROM intake_assets a JOIN intake_revisions parent ON parent.revision_id=a.revision_id
                JOIN intake_sources p ON p.latest_revision_id=parent.revision_id
                WHERE a.source_id=s.source_id AND NOT parent.deleted))""")}
        sources=[s for s in sources if not (s['source_metadata'] or {}).get('intake') or s['transcript_id'] in ready]
    ids=[s['transcript_id'] for s in sources]
    rows=conn.execute('SELECT * FROM transcript_chunks WHERE transcript_id=ANY(%s) ORDER BY chunk_id',(ids,)).fetchall()
    proof=provenance(conn,chunk_contract(models,synthetic=synthetic))
    if not sources or not rows: raise ValueError('Permitted research archive is empty')
    for r in rows:
        p=proof.get(r['chunk_id'],{})
        if not vector_valid(r['embedding']) or p.get('vector_digest')!=vector_digest(r['embedding']) or any(p.get(k)!=v for k,v in chunk_view(r).items()):
            raise ValueError('Research awaits compatible chunk embeddings and provenance')
    return {'sources':{s['transcript_id']:source_digest(s) for s in sources},
        'chunks':{r['chunk_id']:canonical_hash([chunk_view(r),vector_digest(r['embedding'])]) for r in rows},
        'moments':{m['moment_id']:canonical_hash([m['moment_body'],m['evidence_refs']]) for m in conn.execute('SELECT * FROM key_moments ORDER BY moment_id') if all(r['transcript_id'] in ids for r in m['evidence_refs'])},
        'embedding_model':models.embedding_model,'embedding_endpoint':models.embedding_base_url.rstrip('/'),
        'dimensions':1536,'synthetic':synthetic}

def check_archive(conn,snapshot):
    for mid,digest in snapshot.get('moments',{}).items():
        m=conn.execute('SELECT moment_body,evidence_refs FROM key_moments WHERE moment_id=%s FOR SHARE',(mid,)).fetchone()
        if not m or canonical_hash([m['moment_body'],m['evidence_refs']])!=digest: raise ValueError('Frozen research moment/qualification changed')
    for sid,digest in snapshot['sources'].items():
        s=conn.execute('SELECT * FROM transcripts WHERE transcript_id=%s',(sid,)).fetchone()
        if not s or not source_allowed(s) or source_digest(s)!=digest:
            raise ValueError('Frozen archive source changed or was restricted')
    rows=conn.execute('SELECT * FROM transcript_chunks WHERE chunk_id=ANY(%s)',(list(snapshot['chunks']),)).fetchall()
    if len(rows)!=len(snapshot['chunks']): raise ValueError('Frozen research chunk disappeared')
    for row in rows:
        if not vector_valid(row['embedding']) or canonical_hash([chunk_view(row),vector_digest(row['embedding'])])!=snapshot['chunks'][row['chunk_id']]:
            raise ValueError('Frozen research vector/input changed')

def search(conn,text,vector,snapshot,k=50):
    if not isinstance(text,str) or not text.strip() or not 1<=k<=50 or not vector_valid(vector):
        raise ValueError('Search requires a bounded text query and compatible vector')
    check_archive(conn,snapshot)
    vector=np.asarray(vector,dtype=np.float32)
    ids=list(snapshot['chunks'])
    semantic=conn.execute('WITH permitted AS MATERIALIZED (SELECT chunk_id,embedding FROM transcript_chunks WHERE chunk_id=ANY(%s)) SELECT chunk_id,1-(embedding <=> %s) AS cosine FROM permitted ORDER BY embedding <=> %s,chunk_id LIMIT %s',
        (ids,vector,vector,k)).fetchall()
    lexical=conn.execute("""SELECT chunk_id,ts_rank_cd(to_tsvector('english',chunk_text),websearch_to_tsquery('english',%s)) AS lexical
        FROM transcript_chunks WHERE chunk_id=ANY(%s) AND to_tsvector('english',chunk_text) @@ websearch_to_tsquery('english',%s)
        ORDER BY lexical DESC,chunk_id LIMIT %s""",(text,ids,text,k)).fetchall()
    fused={}
    for method,ranked in (('semantic',semantic),('lexical',lexical)):
        for rank,item in enumerate(ranked,1):
            hit=fused.setdefault(item['chunk_id'],{'chunk_id':item['chunk_id'],'rrf':0.})
            hit.update(item); hit[method+'_rank']=rank; hit['rrf']+=1/(60+rank)
    return sorted(fused.values(),key=lambda r:(-r['rrf'],r['chunk_id']))[:k]

def expand(conn,hits,snapshot):
    items={}
    moments=conn.execute('SELECT * FROM key_moments WHERE moment_id=ANY(%s) ORDER BY moment_id',(list(snapshot.get('moments',{})),)).fetchall()
    for hit in hits:
        chunk=conn.execute('SELECT * FROM transcript_chunks WHERE chunk_id=%s',(hit['chunk_id'],)).fetchone()
        if not chunk or chunk['chunk_id'] not in snapshot['chunks']: raise ValueError('Search hit outside allowed archive')
        source=conn.execute('SELECT * FROM transcripts WHERE transcript_id=%s',(chunk['transcript_id'],)).fetchone()
        byid={p['passage_id']:p for p in source['passage_map']}
        selected={r['passage_id'] for r in chunk['passage_refs']}
        if not selected.issubset(byid): raise ValueError('Chunk original references are invalid')
        for ref in chunk['passage_refs']:
            p=byid[ref['passage_id']]
            if (ref['start'],ref['end'])!=(p['start'],p['end']): raise ValueError('Chunk ranges changed')
            for ordinal in (p['ordinal']-1,p['ordinal'],p['ordinal']+1):
                if 0<=ordinal<len(source['passage_map']): selected.add(source['passage_map'][ordinal]['passage_id'])
        linked=[m for m in moments if any(r['transcript_id']==source['transcript_id'] and r['passage_id'] in selected for r in m['evidence_refs'])]
        for m in linked:
            for r in m['evidence_refs']:
                if r['transcript_id'] not in snapshot['sources']: raise ValueError('Required qualification is outside allowed archive')
                s=source if r['transcript_id']==source['transcript_id'] else conn.execute('SELECT * FROM transcripts WHERE transcript_id=%s',(r['transcript_id'],)).fetchone()
                p=next((p for p in s['passage_map'] if p['passage_id']==r['passage_id']),None)
                if not p: raise ValueError('Linked qualification disappeared')
                value=evidence_from_passage(s,p,moment=m,chunk_id=chunk['chunk_id'])
                old=items.get(value.evidence_id)
                if old:
                    value=value.model_copy(update={'moment_ids':sorted(set(old.moment_ids+value.moment_ids)),
                        'qualifications':list(dict.fromkeys(old.qualifications+value.qualifications)),
                        'sensitivity':'internal_only' if 'internal_only' in {old.sensitivity,value.sensitivity} else value.sensitivity,
                        'chunk_ids':sorted(set(old.chunk_ids+value.chunk_ids))})
                items[value.evidence_id]=value
        for pid in sorted(selected,key=lambda pid:byid[pid]['ordinal']):
            value=evidence_from_passage(source,byid[pid],chunk_id=chunk['chunk_id'])
            items.setdefault(value.evidence_id,value)
    return list(items.values())

def family(conn,angle_id):
    parents={r['angle_id']:r['supersedes_id'] for r in conn.execute('SELECT angle_id,supersedes_id FROM content_angles')}
    seen=set()
    while parents.get(angle_id):
        if angle_id in seen: raise ValueError('Angle family cycle')
        seen.add(angle_id); angle_id=parents[angle_id]
    return angle_id

def previous(conn,angle,evidence,snapshot,models,synthetic,as_of=None):
    current=conn.execute('SELECT * FROM content_angles WHERE angle_id=%s',(angle['angle_id'],)).fetchone()
    digest=encoding_contract(models,synthetic=synthetic)
    proof=vector_provenance(conn,digest)
    current_input=canonical_hash(signature_from_fields(current['content_body']))
    if not vector_valid(current['embedding']) or current['embedding_input_hash']!=current_input or proof.get((current['angle_id'],current_input),{}).get('vector_digest')!=vector_digest(current['embedding']):
        raise ValueError('Approved argument awaits a compatible provenance-bound vector')
    # Brief research considers content already created by its frozen execution
    # clock, including later-labelled editorial weeks. The angle's original
    # week still governs its storage and original novelty assessment.
    latest_week=conn.execute('SELECT week_id FROM weeks ORDER BY week_start DESC LIMIT 1').fetchone()['week_id']
    candidates=history(conn,{'created_at':as_of or datetime.now(UTC),'week_id':latest_week,
        'input_refs':{'synthetic':synthetic,'workflow':'historical_comparison_v1','transcripts':[]}},[current])
    # Own-family use is inspected separately from novelty exclusion.
    own=[r for r in conn.execute('SELECT * FROM content_angles ORDER BY created_at') if family(conn,r['angle_id'])==family(conn,current['angle_id'])]
    admitted_families={family(conn,a['angle_id']) for a in candidates+own}
    # A family representative may use different evidence from its retained
    # original. Actual briefs remain attached to that exact original record.
    used=conn.execute('SELECT a.* FROM content_angles a WHERE EXISTS (SELECT 1 FROM content_briefs b WHERE b.angle_id=a.angle_id) ORDER BY a.angle_id').fetchall()
    candidates+=[a for a in used if family(conn,a['angle_id']) in admitted_families]
    candidates+=own
    result=[]
    for a in {a['angle_id']:a for a in candidates}.values():
        moments=conn.execute('SELECT m.* FROM key_moments m JOIN angle_moments am USING(moment_id) WHERE am.angle_id=%s',(a['angle_id'],)).fetchall()
        if not moments or any(r['transcript_id'] not in snapshot['sources'] for m in moments for r in m['evidence_refs']): continue
        overlap=any(i.transcript_id==r['transcript_id'] and i.start<r['end'] and r['start']<i.end
            for i in evidence if i.transcript_id for m in moments for r in m['evidence_refs'])
        briefs=conn.execute('SELECT brief_id,content_hash,approval_status,content_body FROM content_briefs WHERE angle_id=%s ORDER BY created_at',(a['angle_id'],)).fetchall()
        if a['angle_id']==current['angle_id'] and not briefs: continue
        ih=canonical_hash(signature_from_fields(a['content_body']))
        provenance_item=proof.get((a['angle_id'],ih),{})
        if not vector_valid(a['embedding']) or a['embedding_input_hash']!=ih or provenance_item.get('vector_digest')!=vector_digest(a['embedding']):
            raise ValueError('Prior coverage awaits compatible angle vectors')
        cosine=None
        if vector_valid(current['embedding']):
            cosine=float(conn.execute('SELECT 1-(embedding <=> %s) AS cosine FROM content_angles WHERE angle_id=%s',(current['embedding'],a['angle_id'])).fetchone()['cosine'])
        pub=confirmed(conn,a['angle_id'])
        result.append(PriorItem(angle_id=a['angle_id'],argument=a['content_body']['argument'],audience=a['content_body']['audience'],
            mechanism=a['content_body']['mechanism'],approval_status=a['approval_status'],cosine=cosine,
            discovery=['semantic']+(['passage_overlap'] if overlap else [])+(['own_family'] if a['angle_id'] in {o['angle_id'] for o in own} else []),
            briefs=[{'brief_id':b['brief_id'],'hash':b['content_hash'],'approval_status':b['approval_status'],
                'message_spine':b['content_body'].get('document',{}).get('message_spine',[])} for b in briefs],
            publications=pub,content_hash=a['content_hash']))
    return sorted(result,key=lambda p:(-(p.cosine if p.cosine is not None else -1),p.angle_id))

def check_prior(conn,items):
    """Guard the exact argument/use records supplied to the writer."""
    for value in items:
        item=value.model_dump(mode='json') if hasattr(value,'model_dump') else value
        a=conn.execute('SELECT content_hash,approval_status FROM content_angles WHERE angle_id=%s FOR SHARE',(item['angle_id'],)).fetchone()
        if not a or a['content_hash']!=item['content_hash'] or a['approval_status']!=item['approval_status']:
            raise ValueError('Frozen prior argument/approval changed; create a new research intent')
        for b in item['briefs']:
            actual=conn.execute('SELECT content_hash,approval_status FROM content_briefs WHERE brief_id=%s FOR SHARE',(b['brief_id'],)).fetchone()
            if not actual or actual['content_hash']!=b['hash'] or actual['approval_status']!=b['approval_status']:
                raise ValueError('Frozen prior brief changed; create a new research intent')
        pub=confirmed(conn,item['angle_id'])
        if canonical_hash(sorted(pub,key=canonical_hash))!=canonical_hash(sorted(item['publications'],key=canonical_hash)):
            raise ValueError('Frozen publication context changed; refresh research')
