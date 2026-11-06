import json,re,unicodedata,collections
from pathlib import Path
from difflib import SequenceMatcher
root=Path.cwd();base=root/'content_atelier/backend/fathom_backfill_staging/2026-10-14';inventory=json.loads((root/'content_atelier/research/zoom-local-reconciliation-inventory-2026-10-14.json').read_text(encoding='utf-8'))
def tokens(s):return re.findall(r'[a-z0-9]+',unicodedata.normalize('NFKD',s).encode('ascii','ignore').decode().lower())
def grams(t):return set(tuple(t[i:i+5]) for i in range(max(0,len(t)-4)))
local=[]
for row in inventory:
 lines=Path(row['path']).read_text(encoding='utf-8-sig').splitlines();dialogue=[]
 for line in lines:
  if '-->' in line:continue
  if (m:=re.match(r'^([^:\n]{1,100}):\s*(.*)$',line.strip())):dialogue.append(m[2])
 ts=tokens(' '.join(dialogue));local.append({**row,'tokens':ts,'grams':grams(ts)})
results=[]
for d in sorted(base.iterdir()):
 if not d.is_dir() or not (d/'transcript.raw.json').exists():continue
 body=json.loads((d/'transcript.raw.json').read_text(encoding='utf-8'));ts=tokens(' '.join(s['text'] for s in body['transcript']));gs=grams(ts)
 candidates=[]
 for z in local:
  common=len(gs&z['grams']); f=common/max(1,len(gs));q=common/max(1,len(z['grams']))
  candidates.append((common,f,q,z))
 candidates.sort(key=lambda x:x[0],reverse=True);top=[]
 for common,f,q,z in candidates[:4]:
  seq=SequenceMatcher(None,ts,z['tokens'],autojunk=False);blocks=seq.get_matching_blocks();matched=sum(x.size for x in blocks)
  top.append({'week':z['week'],'path':z['path'],'filename':z['filename'],'shared_5grams':common,'fathom_5gram_coverage':f,'zoom_5gram_coverage':q,'matched_tokens':matched,'fathom_token_coverage':matched/max(1,len(ts)),'zoom_token_coverage':matched/max(1,len(z['tokens'])),'zoom_token_count':len(z['tokens']),'zoom_last_cue_seconds':z['last_cue_end_seconds'],'speakers':list(z['speakers'])})
 results.append({'recording_id':int(d.name),'segments':len(body['transcript']),'token_count':len(ts),'speakers':list(dict.fromkeys(s.get('speaker',{}).get('display_name','unknown') for s in body['transcript'])),'candidates':top})
 print(json.dumps({'recording_id':int(d.name),'tokens':len(ts),'speakers':results[-1]['speakers'],'best':[{k:x[k] for k in ['week','filename','fathom_5gram_coverage','zoom_5gram_coverage','fathom_token_coverage','zoom_token_coverage']} for x in top[:2]]},ensure_ascii=False),flush=True)
(base/'text-comparison.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
