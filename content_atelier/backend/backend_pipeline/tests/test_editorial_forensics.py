"""Offline checks for isolated research, not claims about editorial quality."""
import importlib.util
import sys
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location('editorial_forensics', Path(__file__).parents[2]/'scripts/editorial_forensics.py')
experiment = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = experiment
spec.loader.exec_module(experiment)


def selection():
    return {'assessments':[{'candidate_key':'a','disposition':'priority','reason':'Concrete owner question.',
        'source_issue':None,'idea':4,'audience_connection':4,'framing':4,'voice':3,'reel_focus':4,
        'commercial_meaning':4,'redundancy_with':[]}], 'priority_keys':['a'],'reserve_keys':[], 'coverage_notes':[]}


def test_selection_resolves_every_real_candidate():
    assert experiment.validate_selection(selection(),[{'local_key':'a'}]).priority_keys == ['a']


@pytest.mark.parametrize('mutation', ['unknown','self','source','disagreement','missing'])
def test_selection_rejects_invalid_decisions(mutation):
    out=selection()
    if mutation=='unknown': out['priority_keys']=['invented']
    if mutation=='self': out['assessments'][0]['redundancy_with']=['a']
    if mutation=='source': out['assessments'][0]['source_issue']='Wrong speaker.'
    if mutation=='disagreement': out['assessments'][0]['disposition']='skip'
    if mutation=='missing': out['assessments']=[]
    with pytest.raises(ValueError): experiment.validate_selection(out,[{'local_key':'a'}])


def test_no_live_dispatch_without_explicit_flag():
    with pytest.raises(ValueError,match='--live'): experiment.run('not-a-real-cell')
