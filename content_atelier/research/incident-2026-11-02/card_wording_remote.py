import json, os, sys
from datetime import UTC, datetime
import psycopg
from psycopg.rows import dict_row
from contextlib import contextmanager
sys.path.insert(0,os.getcwd())
assert os.environ['RAILWAY_PROJECT_ID']=='3409333b-1844-456c-93f9-f572ba92eb92'
assert os.environ['RAILWAY_ENVIRONMENT_ID']=='28239d73-fe52-4d23-bf80-94a8064c5eb5'
assert os.environ['RAILWAY_SERVICE_NAME']=='scheduler'
RUN='run_113a8c5a0b384cfba61e6fc7b59367ee'
assert ACTION in ('inspect','apply','verify')
targets={
    'angle_c0663bcb1c2a8aff60bf8e44':("Confirm Whitney's public stance on helpful repetition before developing the piece.","Confirm your public stance on helpful repetition before developing the piece."),
    'angle_d03c03643c2a4355563a1427':("Confirm Whitney's public stance before developing the piece.","Confirm your public stance before developing the piece.")}
if ACTION=='apply':
    from backend_pipeline.storage_config import StorageSettings
    from backend_pipeline.repository import ContentRepository
    from backend_pipeline.gate_one import edit
    from backend_pipeline.gates.roles import actor_for
    from backend_pipeline.store import canonical_hash
    before={a['angle_id']:a for a in EXPECTED['cards']}
    changes=[]
    with psycopg.connect(os.environ['ATELIER_DATABASE_URL'],row_factory=dict_row,connect_timeout=15,
        options='-c statement_timeout=20000 -c lock_timeout=5000') as conn:
        # Lock every expected card first; no partial two-card edit can commit.
        for angle_id in sorted(targets):
            live=conn.execute('SELECT * FROM content_angles WHERE angle_id=%s FOR UPDATE',(angle_id,)).fetchone()
            assert json.loads(json.dumps(live,default=str))==before[angle_id], 'Card changed since read-only preview'
            assert live['approval_status']=='pending' and not live['content_body'].get('stance_confirmation')
            assert not conn.execute('SELECT 1 FROM content_angles WHERE supersedes_id=%s LIMIT 1',(angle_id,)).fetchone()
            assert not conn.execute('SELECT 1 FROM content_briefs WHERE angle_id=%s LIMIT 1',(angle_id,)).fetchone()
        repo=ContentRepository(StorageSettings.from_env(conn=conn))
        @contextmanager
        def same_transaction():
            yield conn
        repo.connection=same_transaction
        actor=actor_for(repo,'support@weddingindustryads.com')
        assert actor.access.can('edit') and actor.access.can('decide'), 'Existing user role does not permit this correction'
        for angle_id,(old,new) in targets.items():
            a=before[angle_id]
            checks=a['content_body']['card']['verify_before_publishing']
            assert checks.count(old)==1
            replacement=[new if text==old else text for text in checks]
            changed=edit(repo,angle_id,a['content_hash'],{'verify_before_publishing':replacement},
                actor,
                'User requested wording correction from Whitney to your; the public stance verification requirement is unchanged. Edited through Railway CLI.')
            saved=conn.execute('SELECT * FROM content_angles WHERE angle_id=%s',(changed['angle_id'],)).fetchone()
            assert saved['supersedes_id']==angle_id and saved['approval_status']=='pending'
            assert not saved['content_body'].get('stance_confirmation')
            expected_card=dict(a['content_body']['card']); expected_card['verify_before_publishing']=replacement
            assert saved['content_body']['card']==expected_card, 'Other card text unexpectedly changed'
            moments=conn.execute('SELECT moment_id FROM angle_moments WHERE angle_id=%s ORDER BY moment_id',(saved['angle_id'],)).fetchall()
            assert saved['content_hash']==canonical_hash({'body':saved['content_body'],'moments':[m['moment_id'] for m in moments]})
            changes.append({'previous_angle_id':angle_id,'result':changed,'title':saved['content_body']['title'],'checks':replacement})
    print(json.dumps({'summary':{'at':datetime.now(UTC).isoformat(),'committed':True,'changes':changes}},default=str),flush=True)
    raise SystemExit(0)
with psycopg.connect(os.environ['ATELIER_DATABASE_URL'],row_factory=dict_row,connect_timeout=15,
    options='-c default_transaction_read_only=on -c statement_timeout=20000') as conn:
    cards=conn.execute("SELECT a.* FROM content_angles a WHERE run_id=%s AND NOT EXISTS (SELECT 1 FROM content_angles c WHERE c.supersedes_id=a.angle_id) ORDER BY a.angle_id",(RUN,)).fetchall()
    events=conn.execute("SELECT * FROM pipeline_events WHERE run_id=%s AND event_type LIKE 'gate_one_stance%%' ORDER BY created_at",(RUN,)).fetchall()
    runs=conn.execute("SELECT run_id,run_scope,status,current_message FROM pipeline_runs WHERE week_id='week_2026-10-25' AND run_scope IN ('angle_reassessment','comparison_reassessment') ORDER BY created_at DESC LIMIT 4").fetchall()
    if ACTION=='verify':
        for angle_id,(_,new) in targets.items():
            candidates=[a for a in cards if a['supersedes_id']==angle_id]
            assert len(candidates)==1
            a=candidates[0]
            assert new in a['content_body']['card']['verify_before_publishing']
            assert a['approval_status']=='pending' and not a['content_body'].get('stance_confirmation')
    summary={'at':datetime.now(UTC).isoformat(),'read_only':True,'cards':[{'id':a['angle_id'],'title':a['content_body'].get('title'),
        'status':a['approval_status'],'stance':a['content_body']['card'].get('public_stance'),
        'confirmation':a['content_body'].get('stance_confirmation'),
        'checks':a['content_body']['card']['verify_before_publishing']} for a in cards],'comparison_runs':runs}
print(json.dumps({'summary':summary,'cards':cards,'stance_events':events},default=str),flush=True)
