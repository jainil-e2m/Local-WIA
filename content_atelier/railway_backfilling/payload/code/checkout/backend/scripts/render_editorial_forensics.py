"""Render local research artifacts and exact installed prompt text; no provider calls."""
import difflib
import hashlib
import json
from decimal import Decimal
from pathlib import Path

from backend_pipeline import prompts
from backend_pipeline.config import PROJECT_ROOT
from backend_pipeline.model_experiment import read, write
from backend_pipeline.strategy_contracts import (
    StrategicAngleResponse,
    StrategicCompactMomentResponse,
    StrategicRefinementResponse,
)
from scripts.editorial_forensics import HOME, OLD, RESEARCH


def main():
    results=[read(p) for p in sorted(HOME.glob('*/result.json'))]
    total=sum((Decimal(str(r['reported_new_cost_usd'])) for r in results),Decimal(0))
    summary={'suite':str(HOME),'new_paid_calls':len(results),'reported_new_cost_usd':str(total),
             'validated_cells':sum(r['status']=='completed' for r in results),'failed_cells':sum(r['status']=='failed' for r in results),
             'old_unreturned_week4_luna_charge':'unknown_not_included','results':results,
             'editorial_approval_not_established':True,'no_reference_answers_supplied':True}
    write(PROJECT_ROOT/'research/2026-10-16-editorial-experiment-results.json',summary)
    lines=['# Actual controlled-comparison outputs','',
        'These are generated proposals, not approved content. Original responses are immutable. Failed review text below is diagnostic material, not an accepted recommendation. All cells have independent data roots; no embeddings or history writes ran. The six reference answers were excluded from inputs.','',
        f'New paid calls: **{len(results)}**. Provider-reported cost: **USD {total}**. This excludes earlier calls and the old Week 4 Luna dispatch with unknown charge.','',
        '| Cell | Status | Returned counts | Cost USD |','|---|---|---|---|']
    for r in results:
        lines.append(f"| {r['cell']} | {r['status']} | {json.dumps(r.get('counts',{}))} | {r['reported_new_cost_usd']} |")
    for r in results:
        cell=HOME/r['cell']; plan=read(cell/'plan.json'); pool=read(cell/'pool.json')
        lines += ['',f"## {r['cell']}",'',f"Role: {plan['role']}. Model: `{read(cell/'request.json')['model']}`; high reasoning. Status: **{r['status']}**.",'',
                  f"[Exact request]({(cell/'request.json').as_posix()}) · [Result and cost]({(cell/'result.json').as_posix()})",'']
        if (cell/'output.json').exists():out=read(cell/'output.json')
        else:
            paths=list((cell/'data').rglob('output.received.json'))
            out=read(paths[0]) if paths else {}
            lines += [f"Validation failure: {r.get('error')}. The received text remains separate from accepted output.",'']
        source_map={m['moment_id']:m for m in pool['moment_packet']}
        source_names={t['source_id']:Path(t['path']).name for t in pool['transcripts']}
        public=out.get('angles',[])
        for rec in out.get('recommendations',[]):
            public.append({**rec['angle'],'review_candidate':rec['candidate_key'],'review_disposition':rec['disposition']})
        for a in public:
            lines += [f"### {a['local_key']}: {a['title']}",'',f"**Core:** {a['core_perspective']}",'',
                      f"**Audience:** {a['audience']}",'',f"**Why retained:** {a['selection_reason']}",'',
                      f"**Purpose:** {a['strategic_purpose']} / {a['content_type']}. Readiness: {a['evidence_readiness']}.",'']
            if 'review_disposition' in a:lines += [f"Raw failed-review suggestion: {a['review_disposition']}; parent `{a['review_candidate']}`.",'']
            lines += ['**Supporting source content**','',
                      'Quotes below are literal extraction anchors from the cited source interval; separately listed anchors may be non-adjacent. The complete surrounding turns remain in the linked input pool.','']
            for mid in a['moment_ids']:
                m=source_map[mid]; spans=m['source_evidence']; first,last=spans[0],spans[-1]
                def stamp(seconds):
                    n=int(seconds); return f'{n//3600:02d}:{n%3600//60:02d}:{n%60:02d}'
                anchors=[s for s in spans if s['span_id'] in m['anchor_span_ids'] and m['quote'] in s['text']]
                label=anchors[0]['speaker'] if anchors else 'See original context for speaker'
                seconds=anchors[0]['start_seconds'] if anchors else first['start_seconds']
                names=', '.join(source_names.get(sid,sid) for sid in m['source_ids'])
                lines += [f"`{mid}` · {names} · context {stamp(first['start_seconds'])}–{stamp(last['start_seconds'])}.",'',
                          f"**[{stamp(seconds)}] {label}:** {m['quote']}",'']
            lines += ['**Factual assertions:**','',*[f'- {s}' for s in a['source_assertions']],'',
                      '**Limits:**','',*[f'- {s}' for s in a['qualifiers']],'']
        if 'moments' in out:
            for m in out['moments']:
                lines += [f"### {m['local_key']}",'',m['proposition'],'',f"Literal quote: {m['quote']}",'']
        for field in ('decisions','assessments'):
            for d in out.get(field,[]):lines += [f"- `{d['candidate_key']}` — {d['disposition']}: {d.get('reason','')}"]
        if out.get('coverage_notes'):lines += ['','**Coverage / exclusions:**','',*[f'- {n}' for n in out['coverage_notes']]]
        if 'angles' in out:lines += ['',f"Internal findings remain in [the structured response]({(cell/'output.json').as_posix()}); they are not extra public angles."]
    (PROJECT_ROOT/'research/2026-10-16-editorial-experiment-outputs.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')

    appendix=['# Installed OpenRouter prompts — editorial calibration v1','',
        'These are the installed builder outputs, with runtime source inputs marked explicitly. The exact paid request bodies are stored in each experiment cell. The default angle builder is byte-equivalent to tested arm E before transport appends its JSON contract (verified by test). SQL builders carry the same editorial policy and examples in their structured packets; live SQL execution was unavailable.','',
        f'Angle/refinement artifact version: `{prompts.ANGLE_PROMPT_VERSION}`. Extraction version remains unchanged. No new review/selection stage is installed.','',
        '## Inputs, responsibilities and contracts','',
        '| Call | Responsibility | Runtime inputs | Output / consumer |','|---|---|---|---|',
        '| Weekly extraction | Discover source-grounded moments, not final angles | Complete cue packet and trusted meeting inventory | StrategicCompactMomentResponse → cue resolution, exact quotes, full context expansion |',
        '| Initial angles | Reinterpret source, calibrate against examples, develop distinct proposals and internal intelligence | Current moment packet + literal context, prior signatures, bundled approved scripts | StrategicAngleResponse → source/ID/coverage validation and stored candidates |',
        '| SQL comparison generation | Same task with deduplicated source and eligible archive | moments, evidence_by_id, historical_archive, approved_reel_examples | Same initial response, existing citation adapter/parser/storage |',
        '| Targeted SQL refinement | Supported replacement per real target, or explicit no alternative | Current source, targets, proposals, frozen archive, examples | StrategicRefinementResponse; no internal_insights field or new intelligence records |','',
        'Failure boundaries: unknown/duplicate references, incomplete coverage, nonliteral quotes, cross-source context, duplicate canonical arguments and invalid schema fail existing validation. Missing/empty calibration file fails before dispatch. Evidence checks are not a semantic truth oracle or creative-approval gate. No automatic repair/retry was added.','']
    weekly_system,_=prompts.weekly_moment_prompt('{{WEEKLY_SOURCE_PACKET}}',[])
    weekly_system=weekly_system.rsplit('[]',1)[0]+'{{TRUSTED_MEETING_INVENTORY_JSON}}'
    forms=[('Weekly source discovery',weekly_system,prompts.KEY_MOMENTS_WEEKLY_PREFIX+'{{WEEKLY_SOURCE_PACKET}}'),
           ('Initial angle generation',prompts._system('angle_generation'),
            prompts._load('angle_generation.user.md')+'\n\n'+prompts.REEL_EXAMPLE_LABEL+'\n'+prompts.approved_reel_examples())]
    for name,builder,args,keys in [('SQL comparison generation',prompts.sql_angle_prompt,([],[]),
        ['moments','evidence_by_id','historical_archive','approved_reel_examples']),
        ('Targeted SQL refinement',prompts.sql_refinement_prompt,([],[],[],[]),
         ['moments','evidence_by_id','targets','current_proposals','historical_archive','approved_reel_examples'])]:
        system,user=builder(*args)
        # Full literal example data retained; only runtime collections marked.
        data=json.loads(user)
        for key in keys:
            if key!='approved_reel_examples':data[key]='{{RUNTIME_'+key.upper()+'}}'
        forms.append((name,system,json.dumps(data,ensure_ascii=False,indent=2)))
    for name,system,user in forms:
        appendix += [f'## {name}','', '### System','', '```text',system,'```','', '### User','', '```text',user,'```','']
    appendix += ['## Transport schema appendix','',
        'In JSON-object mode provider.chat_body appends the compact complete JSON schema to system authority under `Required response JSON contract (validated by the backend):`. JSON mode is validated locally; it is not advertised as server-enforced strict schema. Required nullable fields still appear.','']
    for name,contract in [('moment_extraction',StrategicCompactMomentResponse),('angle_generation',StrategicAngleResponse),('angle_refinement',StrategicRefinementResponse)]:
        path=RESEARCH/f'installed-{name}.schema.json';write(path,contract.model_json_schema())
        appendix += [f'- [{name} complete schema]({path.as_posix()})']
    (PROJECT_ROOT/'research/2026-10-16-installed-editorial-prompts.md').write_text('\n'.join(appendix)+'\n',encoding='utf-8')

    manifest=read(RESEARCH/'baseline/manifest.json')
    diff=[]; changed=[]
    for item in manifest['files']:
        relative=item['path']; old=RESEARCH/'baseline'/relative; new=PROJECT_ROOT/relative
        if hashlib.sha256(old.read_bytes()).hexdigest()!=item['sha256']:raise ValueError('Baseline snapshot changed')
        if new.exists() and old.read_bytes()!=new.read_bytes():
            changed.append(relative)
            diff.extend(difflib.unified_diff(old.read_text(encoding='utf-8').splitlines(True),new.read_text(encoding='utf-8').splitlines(True),fromfile='before/'+relative,tofile='after/'+relative))
    (PROJECT_ROOT/'research/2026-10-16-editorial-implementation.diff').write_text(''.join(diff),encoding='utf-8')
    source_manifest=read(OLD/'suite.json')
    for s in source_manifest['sources']:
        assert hashlib.sha256((OLD/s['snapshot']).read_bytes()).hexdigest()==s['sha256']
    write(PROJECT_ROOT/'research/2026-10-16-editorial-provenance-check.json',{
        'baseline_snapshot_unchanged':True,'frozen_source_files_unchanged':len(source_manifest['sources']),
        'changed_existing_baseline_files':changed,'bundled_examples_source':'corpus/instagram/instagram_reels/instagram_reel.md',
        'bundled_examples_sha256':hashlib.sha256(prompts.REEL_CORPUS.read_bytes()).hexdigest(),
        'active_examples_equal_original':prompts.REEL_CORPUS.read_bytes()==(PROJECT_ROOT/'corpus/instagram/instagram_reels/instagram_reel.md').read_bytes(),
        'optional_review_stage_installed':False})
    print(json.dumps({'rendered':True,'calls':len(results),'reported_cost_usd':str(total),'baseline_verified':True,'source_files_verified':len(source_manifest['sources'])}))


if __name__=='__main__':main()
