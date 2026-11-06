"""SQL-only citation formatting bridge; never rewrites a factual assertion.

A missing moment prefix can be derived only when every explicit passage citation
belongs to exactly one of the draft's declared, validated current-week moments.
Unknown, historical, undeclared or ambiguous references remain validation failures.
The exact provider response remains in artifacts; adaptation is a business view.
"""
import copy
import re
from .contracts import AngleResponse
from .strategy_contracts import StrategicAngleResponse, is_strategic_angle_response

VERSION = 'current_moment_passages_v1'
PASSAGE = re.compile(r'[A-Za-z0-9_.:-]+:span:\d+')


def adapt_angle_response(output, moments):
    response = (StrategicAngleResponse if is_strategic_angle_response(output) else AngleResponse).model_validate(output)
    pool = {m.moment_id:m for m in moments}
    adapted = copy.deepcopy(output)
    changes = []
    for draft,record in zip(response.angles,adapted['angles']):
        if any(mid not in pool for mid in draft.moment_ids):
            raise ValueError('Angle references an unknown moment')
        contexts = {mid:set(pool[mid].context_span_ids) for mid in draft.moment_ids}
        allowed = set().union(*contexts.values())
        for index,assertion in enumerate(draft.source_assertions):
            cited = set(PASSAGE.findall(assertion))
            if cited-allowed:
                raise ValueError('Assertion cites a passage outside its declared current-week moments')
            if any(assertion.startswith(f'[{mid}] ') for mid in draft.moment_ids):
                continue
            if re.match(r'^\s*\[',assertion):
                raise ValueError('Invalid or unknown assertion moment prefix')
            owners = [mid for mid,context in contexts.items() if cited and cited.issubset(context)]
            if len(owners)!=1:
                raise ValueError('Missing moment prefix cannot be resolved unambiguously from explicit current evidence')
            mid = owners[0]
            record['source_assertions'][index] = f'[{mid}] '+assertion
            changes.append({'local_key':draft.local_key,'assertion_index':index,'moment_id':mid,'passage_ids':sorted(cited)})
    return adapted,changes
