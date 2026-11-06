"""Read-only row verification after the explicit additive brief-index upgrade."""
import json
from pathlib import Path
from psycopg import sql
from backend_pipeline.database import TABLES,check,catalog
from backend_pipeline.storage_config import StorageSettings
from backend_pipeline.repository import ContentRepository
from backend_pipeline.store import canonical_hash

settings=StorageSettings.from_env()
assert not settings.synthetic
switches={k:getattr(settings,k) for k in ('generation_enabled','encoding_enabled','refinement_enabled','brief_enabled','brief_live_enabled','brief_web_enabled')}
assert not any(switches.values()),'Persistent external/brief switches must remain disabled'
repo=ContentRepository(settings);root=settings.artifact_root/'verification'
before=json.loads((root/'brief-implementation-real-before.json').read_text(encoding='utf-8'))
tables={}
with repo.connection() as conn:
    assert conn.info.dbname=='atelier','Real verification is scoped to the known local atelier database'
    conn.execute('SET TRANSACTION READ ONLY')
    summary=check(conn); actual=catalog(conn)
    for table in sorted(TABLES):
        rows=[r['row'] for r in conn.execute(sql.SQL('SELECT to_jsonb(t) AS row FROM {} t').format(sql.Identifier(table)))]
        tables[table]={'count':len(rows),'hash':canonical_hash(sorted(rows,key=canonical_hash))}
    assert tables==before['tables'],'A real content or execution row changed'
    for key in ('columns','constraints','vectors'):
        assert actual[key]==before['catalog'][key],'Unapproved structural change: '+key
    added=[i for i in actual['indexes'] if i not in before['catalog']['indexes']]
    assert not [i for i in before['catalog']['indexes'] if i not in actual['indexes']]
    assert len(added)==1 and added[0]['indexname']=='transcript_chunks_text_search_idx'
    vector_counts={table:conn.execute(sql.SQL('SELECT count(*) n FROM {} WHERE embedding IS NOT NULL').format(sql.Identifier(table))).fetchone()['n'] for table in ('content_angles','transcript_chunks')}
    assert vector_counts=={'content_angles':12,'transcript_chunks':329}
    assert conn.execute("SELECT count(*) n FROM content_angles WHERE approval_status='pending'").fetchone()['n']==12
result={'real_data_unchanged':True,'tables':tables,'catalog':actual,'schema':summary,'added_indexes':added,
    'vector_counts':vector_counts,'persistent_switches':switches,'real_briefs_created':0,'real_approvals_created':0,
    'verification_external_requests':0,'basis':'Offline test transport guard; no real provider execution; all real row fingerprints unchanged.'}
(root/'brief-implementation-real-after.json').write_text(json.dumps(result,indent=2,default=str),encoding='utf-8')
print(json.dumps({k:result[k] for k in ('real_data_unchanged','vector_counts','persistent_switches','real_briefs_created','real_approvals_created','verification_external_requests')}))
