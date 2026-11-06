import hashlib
from ..store import canonical_hash
from ..gate_one import comparison_owned
from .contracts import EvidenceItem

def source_digest(source):
    return canonical_hash([source['original_text'],source['passage_map'],source['source_metadata'],source['use_restrictions']])

def source_allowed(source):
    restrictions=source['use_restrictions'] or {}
    if not isinstance(restrictions,dict): return False
    return not restrictions.get('withdrawn') and restrictions.get('research_allowed',True) is True

def angle_packet(conn, angle_id):
    a=conn.execute('SELECT * FROM content_angles WHERE angle_id=%s FOR SHARE',(angle_id,)).fetchone()
    if not a or a['approval_status']!='approved' or a['approved_hash']!=a['content_hash'] or not a['approved_by'] or not a['approved_at']:
        raise ValueError('Brief requires a current hash-bound approved angle')
    # A card built on material removed at a client's request (6.B12) gets no brief, whatever its approval says.
    from ..removal import mark_of
    if mark_of(conn,'angle',angle_id):
        raise ValueError("The card is built on material removed at a client's request")
    # A strategist card may defer its CTA to development (R46); the brief then proposes one for Gate 2.
    deferred=bool((a['content_body'] or {}).get('card')) and a['selected_cta']=={'choice':'decide_in_development'}
    if not deferred and (not a['selected_cta'] or not str(a['selected_cta'].get('text','')).strip()):
        raise ValueError('Approved CTA is missing')
    policy=(a['matching_result'] or {}).get('approval_policy')
    if comparison_owned(conn,angle_id) and not policy:
        raise ValueError('Comparison-only approval is disabled: authoritative threshold selection is pending')
    children=conn.execute('SELECT angle_id FROM content_angles WHERE supersedes_id=%s',(angle_id,)).fetchall()
    if children:
        allowed=(policy or {}).get('refinement_children',[])
        if any(c['angle_id'] not in allowed for c in children):
            raise ValueError('Governing angle has been superseded')
    moments=conn.execute('SELECT m.* FROM key_moments m JOIN angle_moments am USING(moment_id) WHERE am.angle_id=%s ORDER BY m.moment_id FOR SHARE OF m,am',(angle_id,)).fetchall()
    if not moments:
        raise ValueError('Approved angle has no grounded moments')
    digest=canonical_hash({'body':a['content_body'],'moments':[m['moment_id'] for m in moments],'cta':a['selected_cta']})
    if digest!=a['approved_hash']:
        raise ValueError('Approved angle content/evidence/CTA hash does not resolve')
    return {'angle_id':angle_id,'week_id':a['week_id'],'approved_hash':a['approved_hash'],
        'body':a['content_body'],'cta':a['selected_cta'],'steer':a['review_note'],
        'approved_by':a['approved_by'],'approved_at':a['approved_at'].isoformat(),'policy':policy,
        'moment_hashes':{m['moment_id']:canonical_hash([m['moment_body'],m['evidence_refs']]) for m in moments}}

def evidence_from_passage(source, passage, *, moment=None, inherited=False, chunk_id=None):
    if not source_allowed(source):
        raise ValueError('Source use is restricted or withdrawn')
    metadata=source['source_metadata'] or {}
    if hashlib.sha256(source['original_text'].encode()).hexdigest()!=metadata.get('normalized_sha256'):
        raise ValueError('Original source integrity failed')
    start,end=passage['start'],passage['end']
    if not 0<=start<end<=len(source['original_text']):
        raise ValueError('Original evidence range is invalid')
    refs=(moment or {}).get('evidence_refs',[])
    ref=next((r for r in refs if r['transcript_id']==source['transcript_id'] and r['passage_id']==passage['passage_id']),None)
    if ref and (ref['start'],ref['end'])!=(start,end):
        raise ValueError('Moment passage range differs from original')
    body=(moment or {}).get('moment_body',{})
    return EvidenceItem(evidence_id='ev_'+canonical_hash([source['transcript_id'],passage['passage_id'],start,end])[:24],
        transcript_id=source['transcript_id'],source_hash=source['content_hash'],source_digest=source_digest(source),
        passage_id=passage['passage_id'],start=start,end=end,excerpt=source['original_text'][start:end],
        title=source['title'],speaker=passage.get('speaker'),start_ms=passage.get('start_ms'),source_url=source['source_url'],
        moment_ids=[moment['moment_id']] if moment else [],chunk_ids=[chunk_id] if chunk_id else [],
        role='anchor' if inherited and ref and 'anchor' in ref['roles'] else 'qualification' if inherited else 'context',
        qualifications=body.get('qualifications',[]),claim_status=body.get('claim_status','unknown'),sensitivity=body.get('sensitivity','unknown'),inherited=inherited,
        public_use=(source['use_restrictions'] or {}).get('public_use') is True,
        attribution_verified=(source['use_restrictions'] or {}).get('attribution_verified') is True)

def anchors(conn, packet):
    result={}
    for mid in packet['moment_hashes']:
        m=conn.execute('SELECT * FROM key_moments WHERE moment_id=%s',(mid,)).fetchone()
        if not m or canonical_hash([m['moment_body'],m['evidence_refs']])!=packet['moment_hashes'][mid]:
            raise ValueError('Approved evidence changed')
        for ref in m['evidence_refs']:
            source=conn.execute('SELECT * FROM transcripts WHERE transcript_id=%s',(ref['transcript_id'],)).fetchone()
            if not source: raise ValueError('Original evidence source missing')
            p=next((p for p in source['passage_map'] if p['passage_id']==ref['passage_id']),None)
            if not p: raise ValueError('Original evidence passage missing')
            item=evidence_from_passage(source,p,moment=m,inherited=True)
            if item.evidence_id in result:
                old=result[item.evidence_id]
                item=item.model_copy(update={'moment_ids':sorted(set(old.moment_ids+item.moment_ids)),
                    'qualifications':list(dict.fromkeys(old.qualifications+item.qualifications)),
                    'sensitivity':'internal_only' if 'internal_only' in {old.sensitivity,item.sensitivity} else item.sensitivity,
                    'role':'anchor' if 'anchor' in {old.role,item.role} else item.role})
            result[item.evidence_id]=item
        if not any(m['moment_body']['quote'] in i.excerpt for i in result.values() if mid in i.moment_ids and i.role=='anchor'):
            raise ValueError('Inherited quote fails original binding')
    return list(result.values())

def verify_evidence(conn, items):
    # Each transcript and moment is read and hashed once: a brief cites hundreds of passages of a few transcripts, and reading the
    # whole transcript for each one took the brief screens past the relay's timeout (production, 3 November).
    sources,digests,passages,moments={}, {}, {}, {}
    for value in items:
        item=EvidenceItem.model_validate(value) if isinstance(value,dict) else value
        if item.role=='external_framing':
            if not item.source_url or not item.source_url.startswith(('https://','http://')):
                raise ValueError('External evidence requires a source URL')
            continue
        tid=item.transcript_id
        if tid not in sources:
            sources[tid]=conn.execute('SELECT * FROM transcripts WHERE transcript_id=%s FOR SHARE',(tid,)).fetchone()
            if sources[tid]:
                digests[tid]=source_digest(sources[tid])
                passages[tid]={p['passage_id']:p for p in sources[tid]['passage_map']}
        s=sources[tid]
        if not s or not source_allowed(s) or digests[tid]!=item.source_digest or s['content_hash']!=item.source_hash:
            raise ValueError('Selected evidence dependency changed or was restricted')
        p=passages[tid].get(item.passage_id)
        if not p or (p['start'],p['end'])!=(item.start,item.end) or s['original_text'][item.start:item.end]!=item.excerpt:
            raise ValueError('Selected evidence does not resolve to the original')
        restrictions=s['use_restrictions'] or {}
        if item.public_use!=(restrictions.get('public_use') is True) or item.attribution_verified!=(restrictions.get('attribution_verified') is True):
            raise ValueError('Evidence public-use flags differ from original source permissions')
        if item.title!=s['title'] or item.source_url!=s['source_url'] or item.speaker!=p.get('speaker') or item.start_ms!=p.get('start_ms'):
            raise ValueError('Evidence attribution metadata differs from its preserved original')
        for mid in item.moment_ids:
            if mid not in moments:
                moments[mid]=conn.execute('SELECT moment_body,evidence_refs FROM key_moments WHERE moment_id=%s FOR SHARE',(mid,)).fetchone()
            moment=moments[mid]
            if not moment or not any(r['transcript_id']==item.transcript_id and r['passage_id']==item.passage_id and (r['start'],r['end'])==(item.start,item.end) for r in moment['evidence_refs']):
                raise ValueError('Evidence moment link does not resolve to the cited original range')
            if not set(moment['moment_body'].get('qualifications',[])).issubset(item.qualifications):
                raise ValueError('Selected evidence lost a current source qualification')
            if moment['moment_body'].get('sensitivity')=='internal_only' and item.sensitivity!='internal_only':
                raise ValueError('Selected evidence lost its internal-use sensitivity')

def assert_packet(conn, packet):
    if angle_packet(conn,packet['angle_id'])!=packet:
        raise ValueError('Approved angle input changed; regenerate research')
