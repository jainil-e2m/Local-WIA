"""Taste data and current-call evidence must remain distinguishable in every builder."""
import json
from pathlib import Path

import pytest

from backend_pipeline import prompts
from backend_pipeline.model_experiment import read
from backend_pipeline.store import canonical_hash
from backend_pipeline.tests.test_generation_only import generation_harness as generation_harness  # noqa: PLC0414


def test_calibration_uses_complete_literal_corpus_only_at_user_authority():
    corpus=prompts.REEL_CORPUS.read_text(encoding='utf-8')
    original=Path(__file__).resolve().parents[3]/'corpus/instagram/instagram_reels/instagram_reel.md'
    assert prompts.REEL_CORPUS.read_bytes()==original.read_bytes()
    system,user=prompts.angle_prompt([{'moment_id':'m','quote':'{{PRIOR_SIGNATURES}}'}],[])
    assert corpus not in system and user.endswith(corpus)
    assert prompts.REEL_EXAMPLE_LABEL in user
    assert 'not current source evidence' in user
    assert 'forecast' in system and 'different cost bases' in system
    received=json.loads(user.split('Moment pool:\n')[1].split('\n\nPrevious eligible')[0])
    assert received==[{'moment_id':'m','quote':'{{PRIOR_SIGNATURES}}'}]


def test_sql_generation_and_refinement_keep_source_and_examples_separate():
    pool=[{'moment_id':'m','context_span_ids':['s'],'source_evidence':[{'span_id':'s','text':'Original evidence.'}]}]
    for builder,args in [(prompts.sql_angle_prompt,(pool,[])),(prompts.sql_refinement_prompt,(pool,[],[],[]))]:
        system,user=builder(*args)
        packet=json.loads(user)
        assert packet['approved_reel_examples']==prompts.approved_reel_examples()
        assert packet['evidence_by_id']=={'s':{'span_id':'s','text':'Original evidence.'}}
        assert packet['historical_archive']==[]
        assert 'six existing scripts' in system


def test_missing_or_empty_corpus_cannot_silently_downgrade_calibration(tmp_path,monkeypatch):
    p=tmp_path/'missing.md'
    monkeypatch.setattr(prompts,'REEL_CORPUS',p)
    with pytest.raises(FileNotFoundError):prompts.angle_prompt([],[])
    p.write_text('  ',encoding='utf-8')
    with pytest.raises(ValueError,match='empty'):prompts.sql_angle_prompt([],[])


def test_angle_upgrade_leaves_extraction_prompt_bytes_unchanged():
    root=Path(__file__).resolve().parents[3]
    baseline=root/'research/sources/reel-editorial-forensics-2026-10-16/baseline'
    manifest=read(baseline/'manifest.json')
    for item in manifest['files']:
        if 'moment_extraction.' in item['path']:
            assert (root/item['path']).read_bytes()==(baseline/item['path']).read_bytes()
    system,_=prompts.weekly_moment_prompt('source',[])
    assert 'Reel editorial judgment' not in system


def test_actual_combined_experiment_matches_installed_default_builder():
    root=Path(__file__).resolve().parents[3]
    cell=root/'testing/.data/experiments/reel-editorial-forensics-20261016/E-w3-sol'
    if not cell.exists():pytest.skip('Local paid research artifacts are not shipped as test fixtures')
    pool=read(cell/'pool.json')
    body=read(cell/'request.json')
    system,user=prompts.angle_prompt(pool['moment_packet'],[])
    assert body['messages'][0]['content'].split('\n\nRequired response JSON contract')[0]==system
    assert body['messages'][1]['content']==user
    assert canonical_hash(pool['moment_packet'])==canonical_hash(read(cell/'pool.json')['moment_packet'])


def test_calibration_change_regenerates_only_angles_and_records_stage_version(generation_harness,monkeypatch):
    _settings,provider,pipeline=generation_harness
    first=pipeline.run(1)
    loader=prompts._load
    monkeypatch.setattr(prompts,'_load',lambda name:loader(name)+('\nSynthetic editorial calibration revision.' if name=='reel_editorial.md' else ''))
    second=pipeline.run(1)
    assert provider.calls=={'moment_extraction':1,'angle_generation':2}
    roots=[f"experiments/default/runs/{r['run_id']}" for r in (first,second)]
    assert pipeline.store.read_json(roots[0]+'/moments.json')==pipeline.store.read_json(roots[1]+'/moments.json')
    artifact=pipeline.store.read_json(roots[1]+'/angle_generation.json')
    assert artifact['prompt_version']==prompts.ANGLE_PROMPT_VERSION
    assert pipeline.store.read_json(roots[1]+'/moment_extraction.json')['prompt_version']!=prompts.ANGLE_PROMPT_VERSION
