from pathlib import Path
import csv,hashlib,json,sys
root=Path(__file__).resolve().parents[1]
payload=root/'payload'
errors=[];count=0;total=0;listed=set()
with (root/'reports/payload-manifest.csv').open(encoding='utf-8-sig',newline='') as f:
    for row in csv.DictReader(f):
        p=(payload/row['path']).resolve()
        if not p.is_relative_to(payload.resolve()):
            errors.append({'path':row['path'],'reason':'path outside payload'});continue
        listed.add(p);count+=1
        if not p.is_file():
            errors.append({'path':row['path'],'reason':'missing'});continue
        h=hashlib.sha256()
        with p.open('rb') as src:
            for block in iter(lambda:src.read(1024*1024),b''):h.update(block)
        size=p.stat().st_size;total+=size
        if size!=int(row['bytes']) or h.hexdigest()!=row['sha256']:
            errors.append({'path':row['path'],'reason':'checksum or size mismatch'})
for p in payload.rglob('*'):
    if p.is_file() and p.resolve() not in listed:errors.append({'path':p.relative_to(payload).as_posix(),'reason':'unexpected file'})
print(json.dumps({'status':'passed' if not errors else 'failed','files':count,'bytes':total,'errors':errors}))
sys.exit(bool(errors))
