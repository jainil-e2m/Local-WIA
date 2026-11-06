"""Strict one-pass envelope, with the existing evidence/quality validator reused."""
from .contracts import RefinementResponse, signature_from_fields
from .strategy_contracts import StrategicRefinementResponse
from .citation_adapter import adapt_angle_response, VERSION as CITATION_VERSION


def parse_refinement(pipeline, output, run_id, moments, originals, *, artifact=None):
    strategic = any(o.get('replacement') and 'core_perspective' in o['replacement'] for o in output.get('outcomes', []))
    response = (StrategicRefinementResponse if strategic else RefinementResponse).model_validate(output)
    supplied = [o.original_id for o in response.outcomes]
    if len(supplied)!=len(set(supplied)) or set(supplied)!=set(originals):
        raise ValueError('Refinement target coverage must be exact and unique')
    pipeline._coverage({m.moment_id for m in moments},response.processed_moment_ids,'Moment')
    drafts = []
    for outcome in response.outcomes:
        if (outcome.outcome=='replacement') != (outcome.replacement is not None):
            raise ValueError('Refinement disposition and replacement disagree')
        if outcome.replacement:
            if signature_from_fields(outcome.replacement.model_dump())==signature_from_fields(originals[outcome.original_id]['content_body']):
                raise ValueError('A replacement must change its substantive signature')
            drafts.append(outcome.replacement.model_dump(mode='json'))
    interpreted,citation_changes = adapt_angle_response({'angles':drafts,'processed_moment_ids':response.processed_moment_ids,
                                         **({'internal_insights': []} if strategic else {}),
                                         'coverage_notes':response.coverage_notes or ['No supported alternative']},moments)
    angles = pipeline._parse_angles(interpreted,
                                   run_id,moments,artifact=artifact)
    parents = {}
    iterator = iter(angles)
    dispositions = []
    for outcome in response.outcomes:
        replacement = next(iterator) if outcome.replacement else None
        if replacement:
            replacement.generated_at = originals[outcome.original_id]['first_generated_at']
            parents[replacement.angle_id] = outcome.original_id
        dispositions.append({'original_id':outcome.original_id,'replacement_id':replacement.angle_id if replacement else None,
                             'disposition':outcome.outcome,'explanation':outcome.explanation,'targeted':True,
                             'citation_adapter':CITATION_VERSION,
                             'citation_adaptations':[c for c in citation_changes if outcome.replacement and c['local_key']==outcome.replacement.local_key]})
    return angles,parents,dispositions
