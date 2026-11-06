"""Bounded Railway transport for this user-requested wording correction."""
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4
from railway_284_controller import CLI, HERE, OUT, call

def main():
    action=sys.argv[1]
    assert action in ('inspect','apply','verify')
    baseline=OUT/'card-wording-before.json'
    expected=json.loads(baseline.read_text(encoding='utf-8')) if action!='inspect' else None
    if action=='inspect': assert not baseline.exists()
    source=(HERE/'card_wording_remote.py').read_text(encoding='utf-8')
    result=call([CLI,'status','--json'])
    assert result.returncode==0 and json.loads(result.stdout)['id']=='3409333b-1844-456c-93f9-f572ba92eb92'
    private=Path.home()/'.ssh'/('id_ed25519_atelier_diagnostic_'+uuid4().hex)
    receipt={'at':datetime.now(UTC).isoformat(),'registered':False,'removed':False}
    try:
        assert call(['ssh-keygen','-t','ed25519','-N','','-C','atelier-card-wording','-f',private]).returncode==0
        receipt['fingerprint']=call(['ssh-keygen','-lf',str(private)+'.pub']).stdout.split()[1]
        assert call([CLI,'ssh','keys','add','--key',str(private)+'.pub','--name','atelier-card-wording']).returncode==0
        receipt['registered']=True
        target=call([CLI,'ssh','config','--service','scheduler','--dry-run'])
        match=re.search(r'^\s*User\s+(\S+)',target.stdout,re.MULTILINE)
        assert target.returncode==0 and match
        code='ACTION='+repr(action)+'\nEXPECTED='+repr(expected)+'\n'+source
        result=call(['ssh','-T','-o','BatchMode=yes','-o','IdentitiesOnly=yes','-o','StrictHostKeyChecking=yes',
                     '-o','UserKnownHostsFile=research/incident-2026-11-02/ssh_known_hosts','-o','ConnectTimeout=20',
                     '-i',private,match[1]+'@ssh.railway.com','python -'],input=code)
        if result.returncode:
            (OUT/f'card-wording-{action}-error.txt').write_text(result.stderr,encoding='utf-8')
            raise RuntimeError(result.stderr[-2000:])
        data=json.loads(result.stdout)
        path=baseline if action=='inspect' else OUT/f'card-wording-{action}.json'
        path.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
        print(json.dumps(data.get('summary',data),indent=2))
    finally:
        if receipt['registered']:
            for _ in range(2):
                if call([CLI,'ssh','keys','remove',receipt['fingerprint']]).returncode==0:
                    receipt['removed']=True
                    break
        private.unlink(missing_ok=True); Path(str(private)+'.pub').unlink(missing_ok=True)
        receipt['local_keys_deleted']=not private.exists() and not Path(str(private)+'.pub').exists()
        (OUT/f'card-wording-access-{action}.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
        print(json.dumps({'temporary_access_removed':receipt['removed'],'local_keys_deleted':receipt['local_keys_deleted']}))
        assert not receipt['registered'] or receipt['removed']

if __name__=='__main__': main()
