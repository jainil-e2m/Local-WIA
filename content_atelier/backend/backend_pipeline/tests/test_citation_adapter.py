import copy
from types import SimpleNamespace
import pytest
from backend_pipeline.citation_adapter import adapt_angle_response


def fixture():
    moment=SimpleNamespace(moment_id='moment_current',context_span_ids=['zoom:current:span:1','zoom:current:span:2'])
    draft={'local_key':'one','title':'Supported decision','argument':'A bounded decision','audience':'Owners','tension':'A choice',
           'take':'Review','mechanism':'Comparison','reader_decision':'Check evidence','moment_ids':['moment_current'],
           'source_assertions':['An observation was reported (zoom:current:span:1; zoom:current:span:2).'],
           'inference':None,'qualifiers':['Reported only'],'risks':['Unverified identity'],
           'quality':{n:4. for n in ('grounding','source_relevance','audience_fit','specificity','editorial_usefulness')} | {'reasons':['Bounded source']}}
    return {'angles':[draft],'processed_moment_ids':['moment_current'],'coverage_notes':[]},[moment]


def test_prefix_adaptation_is_lossless_auditable_and_idempotent():
    raw,moments=fixture();before=copy.deepcopy(raw)
    adapted,changes=adapt_angle_response(raw,moments)
    assert raw==before
    assert adapted['angles'][0]['source_assertions'][0]=='[moment_current] '+raw['angles'][0]['source_assertions'][0]
    assert changes[0]['moment_id']=='moment_current'
    assert adapted['angles'][0]['quality']==raw['angles'][0]['quality']
    assert adapted['angles'][0]['qualifiers']==raw['angles'][0]['qualifiers']
    assert adapt_angle_response(adapted,moments)==(adapted,[])


@pytest.mark.parametrize('assertion',['An uncited claim.','A claim (zoom:historical:span:1).',
                                   '[moment_historical] A claim (zoom:current:span:1).',
                                   '[moment_current] A claim (zoom:historical:span:1).'])
def test_uncited_unknown_or_historical_evidence_is_rejected(assertion):
    raw,moments=fixture();raw['angles'][0]['source_assertions']=[assertion]
    with pytest.raises(ValueError):adapt_angle_response(raw,moments)


def test_ambiguous_or_undeclared_moment_links_are_not_invented():
    raw,moments=fixture();other=SimpleNamespace(moment_id='moment_other',context_span_ids=moments[0].context_span_ids)
    raw['angles'][0]['moment_ids'].append(other.moment_id)
    with pytest.raises(ValueError,match='unambiguously'):adapt_angle_response(raw,moments+[other])
    raw['angles'][0]['moment_ids']=['moment_unknown']
    with pytest.raises(ValueError,match='unknown moment'):adapt_angle_response(raw,moments)
