"""One-off, user-authorized review-state correction; no application changes."""
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from railway_284_controller import CLI, HERE, OUT, call

REMOTE = r'''
import json, os, sys
from datetime import UTC, datetime
import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
sys.path.insert(0, os.getcwd())
from backend_pipeline.store import canonical_hash
from backend_pipeline.gate_one import stance_matches

assert os.environ['RAILWAY_PROJECT_ID']=='3409333b-1844-456c-93f9-f572ba92eb92'
assert os.environ['RAILWAY_ENVIRONMENT_ID']=='28239d73-fe52-4d23-bf80-94a8064c5eb5'
assert os.environ['RAILWAY_SERVICE_NAME']=='scheduler'
run='run_113a8c5a0b384cfba61e6fc7b59367ee'
stance="An agency's usual setup shouldn't outrank evidence from the wedding business in front of it."
options='-c statement_timeout=20000 -c lock_timeout=5000'
if ACTION=='inspect': options+=' -c default_transaction_read_only=on'
with psycopg.connect(os.environ['ATELIER_DATABASE_URL'],row_factory=dict_row,connect_timeout=15,options=options) as conn:
    if ACTION=='inspect':
        rows=conn.execute("SELECT * FROM content_angles WHERE run_id=%s AND content_body#>>'{card,public_stance,stance}'=%s",(run,stance)).fetchall()
        assert len(rows)==1, 'Expected exactly one card with the quoted public stance'
        a=rows[0]
        confirmation=a['content_body'].get('stance_confirmation')
        assert a['approval_status']=='pending', 'Card no longer pending; stop for review'
        assert confirmation and confirmation['note']=='asdd' and confirmation['by']=='support@weddingindustryads.com'
        assert confirmation['at'].startswith('2026-11-02') and confirmation['stance']==stance
        assert stance_matches(a['content_body']['card'],confirmation)
        events=conn.execute("SELECT * FROM pipeline_events WHERE run_id=%s AND details->>'angle_id'=%s ORDER BY created_at",(run,a['angle_id'])).fetchall()
        result={'at':datetime.now(UTC).isoformat(),'transaction_read_only':conn.execute('SHOW transaction_read_only').fetchone(),
                'card_before':a,'events_before':events,'body_sha256':canonical_hash(a['content_body'])}
    else:
        before=EXPECTED['card_before']
        a=conn.execute('SELECT * FROM content_angles WHERE angle_id=%s FOR UPDATE',(before['angle_id'],)).fetchone()
        assert a and a['run_id']==run and a['approval_status']=='pending'
        assert json.loads(json.dumps(a,default=str))==before, 'Card changed since inspection; no update allowed'
        assert a['content_body']['stance_confirmation']['note']=='asdd'
        assert not conn.execute('SELECT 1 FROM content_angles WHERE supersedes_id=%s LIMIT 1',(a['angle_id'],)).fetchone(), 'Replacement exists'
        assert not conn.execute('SELECT 1 FROM content_briefs WHERE angle_id=%s LIMIT 1',(a['angle_id'],)).fetchone(), 'Brief already exists'
        assert not conn.execute("SELECT 1 FROM pipeline_events WHERE event_type='gate_one_stance_confirmation_reverted' AND details->>'undo_id'=%s",(UNDO_ID,)).fetchone()
        actor='support@weddingindustryads.com: user-requested accidental confirmation undo'
        after=conn.execute("UPDATE content_angles SET content_body=content_body-'stance_confirmation',updated_by=%s,updated_at=now() WHERE angle_id=%s RETURNING *",(actor,a['angle_id'])).fetchone()
        expected_body=dict(a['content_body']); removed=expected_body.pop('stance_confirmation')
        assert after['content_body']==expected_body and 'stance_confirmation' not in after['content_body']
        assert not stance_matches(after['content_body']['card'],after['content_body'].get('stance_confirmation'))
        for key in a:
            if key not in ('content_body','updated_by','updated_at'): assert after[key]==a[key], key+' unexpectedly changed'
        event_id='event_'+__import__('uuid').uuid4().hex
        details={'angle_id':a['angle_id'],'undo_id':UNDO_ID,'actor':actor,'reason':'User requested undo of accidental public stance confirmation and asdd note',
                 'previous_confirmation_by':removed['by'],'previous_confirmation_at':removed['at'],
                 'content_hash_unchanged':True,'card_text_unchanged':True}
        conn.execute("INSERT INTO pipeline_events(event_id,run_id,event_type,message,severity,details) VALUES(%s,%s,%s,%s,%s,%s)",
            (event_id,run,'gate_one_stance_confirmation_reverted','Accidental public stance confirmation reverted','info',Jsonb(details)))
        result={'at':datetime.now(UTC).isoformat(),'card_after':after,'removed_confirmation':removed,'event_id':event_id,'undo_id':UNDO_ID,
                'card_text_unchanged':True,'content_hash_unchanged':True,'approval_status_unchanged':True,'stance_confirmation_absent':True}
if ACTION=='apply':
    with psycopg.connect(os.environ['ATELIER_DATABASE_URL'],row_factory=dict_row,connect_timeout=15,
                         options='-c default_transaction_read_only=on -c statement_timeout=20000') as check:
        persisted=check.execute('SELECT * FROM content_angles WHERE angle_id=%s',(result['card_after']['angle_id'],)).fetchone()
        assert persisted==result['card_after'], 'Persisted state differs from the transaction result'
        assert check.execute('SELECT count(*) AS n FROM pipeline_events WHERE event_id=%s',(result['event_id'],)).fetchone()['n']==1
        result['post_commit_read_only_verification']=True
print(json.dumps(result,default=str),flush=True)
'''

def main():
    action=sys.argv[1]
    assert action in ('inspect','apply')
    baseline=OUT/'accidental-stance-before.json'
    expected=json.loads(baseline.read_text(encoding='utf-8')) if action=='apply' else None
    if action=='inspect': assert not baseline.exists(), 'Preserve the original snapshot'
    status=call([CLI,'status','--json'])
    assert status.returncode==0
    platform=json.loads(status.stdout)
    assert platform['id']=='3409333b-1844-456c-93f9-f572ba92eb92'
    private=Path.home()/'.ssh'/('id_ed25519_atelier_diagnostic_'+uuid4().hex)
    receipt={'at':datetime.now(UTC).isoformat(),'action':action,'registered':False,'removed':False}
    try:
        assert call(['ssh-keygen','-t','ed25519','-N','','-C','atelier-accidental-stance-undo','-f',private]).returncode==0
        fingerprint=call(['ssh-keygen','-lf',str(private)+'.pub']).stdout.split()[1]
        receipt['fingerprint']=fingerprint
        assert call([CLI,'ssh','keys','add','--key',str(private)+'.pub','--name','atelier-accidental-stance-undo']).returncode==0
        receipt['registered']=True
        target=call([CLI,'ssh','config','--service','scheduler','--dry-run'])
        match=re.search(r'^\s*User\s+(\S+)',target.stdout,re.MULTILINE)
        assert target.returncode==0 and match
        source='ACTION='+repr(action)+'\nEXPECTED='+repr(expected)+'\nUNDO_ID="accidental-asdd-stance-20261102"\n'+REMOTE
        args=['ssh','-T','-o','BatchMode=yes','-o','IdentitiesOnly=yes','-o','StrictHostKeyChecking=yes',
              '-o','UserKnownHostsFile=research/incident-2026-11-02/ssh_known_hosts','-o','ConnectTimeout=20',
              '-i',private,match[1]+'@ssh.railway.com','python -']
        result=call(args,input=source)
        receipt['remote_exit_code']=result.returncode
        if result.returncode:
            (OUT/f'accidental-stance-{action}-error.txt').write_text(result.stderr,encoding='utf-8')
            raise RuntimeError(result.stderr[-2400:])
        data=json.loads(result.stdout)
        destination=baseline if action=='inspect' else OUT/'accidental-stance-undo-receipt.json'
        destination.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
        card=data.get('card_before',data.get('card_after'))
        print(json.dumps({'action':action,'at':data['at'],'angle_id':card['angle_id'],'title':card['content_body'].get('title'),
                         'approval_status':card['approval_status'],'stance_confirmation':card['content_body'].get('stance_confirmation'),
                         'event_id':data.get('event_id'),'transaction_read_only':data.get('transaction_read_only')},indent=2))
    finally:
        if receipt['registered']:
            for _ in range(2):
                if call([CLI,'ssh','keys','remove',receipt['fingerprint']]).returncode==0:
                    receipt['removed']=True
                    break
        private.unlink(missing_ok=True)
        Path(str(private)+'.pub').unlink(missing_ok=True)
        receipt['local_key_files_deleted']=not private.exists() and not Path(str(private)+'.pub').exists()
        (OUT/f'accidental-stance-access-{action}.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
        print(json.dumps({'temporary_access_removed':receipt['removed'],'local_keys_deleted':receipt['local_key_files_deleted']}))
        assert not receipt['registered'] or receipt['removed']

if __name__=='__main__': main()
