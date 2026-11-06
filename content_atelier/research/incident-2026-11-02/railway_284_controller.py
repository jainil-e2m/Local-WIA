"""Bounded Railway CLI/SSH actions for the single user-approved run; temporary access always revoked."""
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import UTC,datetime
from pathlib import Path
from uuid import uuid4

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
OUT=HERE/'reduced-run-preview'
CLI=Path(os.environ['APPDATA'])/'npm/node_modules/@railway/cli/bin/railway.exe'
sys.path.insert(0,str(ROOT/'backend'))
from backend_pipeline.store import canonical_hash

def call(args,**kwargs):
    return subprocess.run([str(x) for x in args],cwd=ROOT,capture_output=True,encoding='utf-8',errors='replace',timeout=55,**kwargs)

def payload(action):
    snapshot_raw=(OUT/'production-snapshot.json').read_bytes()
    approved=json.loads((OUT/'generation-input-284-validated.json').read_text(encoding='utf-8'))
    assert hashlib.sha256(snapshot_raw).hexdigest()==approved['snapshot_sha256']
    snap=json.loads(snapshot_raw)
    gen=next(j for j in snap['jobs'] if j['stage']=='angle_generation')
    ext=next(j for j in snap['jobs'] if j['stage']=='moment_extraction')
    fields=['moment_id','moment_body','evidence_refs','consent_status','quote_verified','evidence_class','document_id','extractor_version']
    ids=ext['result_refs']['moment_ids']
    return {**approved,'action':action,'user_authorized_execution':action=='apply',
            'original_result_refs':ext['result_refs'],'input_refs_sha256':canonical_hash(snap['run']['input_refs']),
            'job_statuses':{j['job_id']:j['status'] for j in snap['jobs']},
            'generation_attempt_count':gen['attempt_count'],'generation_error':gen['error_summary'],
            'schedule_value':snap['schedule']['value'],'baseline_model_call_count':len(snap['model_calls']),
            'moment_hash_fields':fields,'moment_hashes':{r['moment_id']:canonical_hash({k:r.get(k) for k in fields}) for r in snap['moments'] if r['moment_id'] in ids},
            'omitted_ids':[o['moment_id'] for o in approved['omissions']],
            'profile':snap['run']['input_refs']['angle_prompt_profile'],
            'original_request_fingerprint':'b711709c8a5be0b742458b57ed5d535c00efc09db772d2b77c14e23328d8a941'}

def main():
    action=sys.argv[1] if len(sys.argv)==2 else None
    assert action in ('inspect','apply','status','finalize','messages')
    source=(HERE/'execute_284_remote.py').read_text(encoding='utf-8')
    config=payload(action)
    # Verify existing deployments by a read-only Railway CLI request before registering diagnostic access.
    status=call([CLI,'status','--json'])
    assert status.returncode==0, 'Railway status failed; credential-bearing stderr withheld'
    platform=json.loads(status.stdout)
    assert platform['id']=='3409333b-1844-456c-93f9-f572ba92eb92'
    production=next(e['node'] for e in platform['environments']['edges'] if e['node']['id']=='28239d73-fe52-4d23-bf80-94a8064c5eb5')
    for edge in production['serviceInstances']['edges']:
        n=edge['node']
        if n['serviceName'] in ('scheduler','editorial-worker','bulk-worker'):
            assert n['latestDeployment']['status']=='SUCCESS' and n['latestDeployment']['meta']['commitHash']=='9b50c9d047a2d1005b19fbd80fea5f9e2476a32b', 'Backend deployment changed'
    private=Path.home()/'.ssh'/('id_ed25519_atelier_diagnostic_'+uuid4().hex)
    assert private.parent.resolve()==(Path.home()/'.ssh').resolve() and not private.exists()
    receipt={'at':datetime.now(UTC).isoformat(),'action':action,'registered':False,'removed':False}
    try:
        made=call(['ssh-keygen','-t','ed25519','-N','','-C','atelier-approved284-recovery','-f',private])
        assert made.returncode==0
        fp=call(['ssh-keygen','-lf',str(private)+'.pub']).stdout.split()[1]
        receipt['fingerprint']=fp
        reg=call([CLI,'ssh','keys','add','--key',str(private)+'.pub','--name','atelier-approved284-recovery'])
        assert reg.returncode==0, 'Temporary key registration failed'
        receipt['registered']=True
        target=call([CLI,'ssh','config','--service','scheduler','--dry-run'])
        match=re.search(r'^\s*User\s+(\S+)',target.stdout,re.MULTILINE)
        assert target.returncode==0 and match
        remote='CONFIG='+repr(config)+'\nREMOTE_SOURCE='+repr(source)+"\nexec(compile(REMOTE_SOURCE,'<approved284-recovery>','exec'))\n"
        args=['ssh','-T','-o','BatchMode=yes','-o','IdentitiesOnly=yes','-o','StrictHostKeyChecking=yes',
              '-o','UserKnownHostsFile=research/incident-2026-11-02/ssh_known_hosts','-o','ConnectTimeout=20',
              '-i',private,match[1]+'@ssh.railway.com','python -']
        result=call(args,input=remote)
        receipt['remote_exit_code']=result.returncode
        stamp=datetime.now(UTC).strftime('%H%M%S')
        if result.returncode:
            (OUT/f'production-284-{action}-error-{stamp}.txt').write_text(result.stderr,encoding='utf-8')
            raise RuntimeError('Recovery action failed: '+result.stderr[-2400:])
        data=json.loads(result.stdout)
        (OUT/f'production-284-{action}-{stamp}.json').write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
        for document in data.get('documents',[]):
            import base64
            raw=base64.b64decode(document['base64'])
            assert hashlib.sha256(raw).hexdigest()==document['sha256']
            filename='recovered-week-review.'+('md' if document['kind']=='markdown' else 'docx')
            (OUT/filename).write_bytes(raw)
        state=data.get('status',{})
        print(json.dumps({'action':action,'database_verification':data.get('database_verification'),
                          'integrity':data.get('integrity'),'inspection':data.get('inspection'),'application':data.get('application'),
                          'restoration':data.get('restoration'),'watchdog_pid':data.get('watchdog_pid'),
                          'at':state.get('at'),'run':state.get('run'),
                          'jobs':[{k:j.get(k) for k in ('stage','status','attempt_count','current_message','error_summary')} for j in state.get('jobs',[])],
                          'extraction_count':state.get('extraction_count'),'cards':len(state.get('cards',[])),
                          'calls':[{k:c.get(k) for k in ('stage','model','status','input_tokens','output_tokens','cost_usd','error')} for c in state.get('calls',[]) if c.get('stage')!='moment_extraction'],
                          'generation_attempt_artifacts':[{**{k:a.get(k) for k in ('attempt','model','scene_count','raw_response_saved')},
                              'preflight_fits':(a.get('preflight') or {}).get('fits')} for a in state.get('generation_attempt_artifacts',[])],
                          'watchdog_error':state.get('watchdog_error'),
                          'applied':state.get('applied'),'restored':state.get('restored')},indent=2),flush=True)
    finally:
        if receipt['registered']:
            for _ in range(2):
                r=call([CLI,'ssh','keys','remove',receipt['fingerprint']])
                if r.returncode==0:
                    receipt['removed']=True
                    break
        private.unlink(missing_ok=True); Path(str(private)+'.pub').unlink(missing_ok=True)
        receipt['local_key_files_deleted']=not private.exists() and not Path(str(private)+'.pub').exists()
        (OUT/'production-284-access-latest.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
        print(json.dumps({'temporary_ssh_removed':receipt['removed'],'local_key_files_deleted':receipt['local_key_files_deleted']}),flush=True)
        assert not receipt['registered'] or receipt['removed'], 'Temporary access revocation needs retry'

if __name__=='__main__': main()
