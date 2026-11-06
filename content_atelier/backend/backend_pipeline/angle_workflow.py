"""Pure eligibility and family selection; no model calls or SQL mutations."""
from __future__ import annotations

WORKFLOW = 'historical_comparison_v1'
LEGACY = 'two_call_v1'
CUTOFFS = (.78, .85, .90)
STAGES = ('moment_extraction', 'history_context', 'angle_generation',
          'angle_initial_embedding', 'angle_initial_assessment', 'angle_refinement',
          'angle_refined_embedding', 'angle_final_assessment')


def diagnoses(metrics, cutoff):
    reasons = []
    if metrics.get('evidence_readiness','supported')!='supported':
        reasons.append('source_research_required')
    if not metrics.get('grounding_valid', False):
        reasons.append('invalid_grounding')
    if not metrics.get('coverage_complete', False):
        reasons.append('incomplete_matching')
    if metrics.get('base_score') is None or metrics['base_score'] <= 70:
        reasons.append('quality')
    if metrics.get('max_historical_cosine') is None or metrics['max_historical_cosine'] >= cutoff:
        reasons.append('historical_overlap')
    return reasons


def scenarios(families, metrics):
    """Unrounded strict boundaries. Count each original family exactly once."""
    output = []
    for cutoff in CUTOFFS:
        counts = dict(initial_qualified=0, final_qualified=0, recovered=0,
                      retained_original_fallbacks=0, failing_quality=0,
                      failing_history=0, failing_both=0, no_supported_alternative=0)
        selections = []
        for family in families:
            original = metrics[family['original_id']]
            replacement = metrics.get(family.get('replacement_id'))
            initial_reasons = diagnoses(original, cutoff)
            counts['initial_qualified'] += not initial_reasons
            replacement_reasons = diagnoses(replacement, cutoff) if replacement else None
            chosen = replacement if replacement and not replacement_reasons else original if not initial_reasons else None
            counts['final_qualified'] += chosen is not None
            counts['recovered'] += bool(initial_reasons and chosen)
            counts['retained_original_fallbacks'] += bool(chosen is original and family.get('targeted'))
            counts['no_supported_alternative'] += family.get('disposition') == 'no_supported_alternative'
            if chosen is None:
                # Use the attempted final candidate for failure diagnostics; preserve
                # both candidates' reasons below so no original outcome is hidden.
                reasons = replacement_reasons if replacement else initial_reasons
                quality, overlap = 'quality' in reasons, 'historical_overlap' in reasons
                counts['failing_quality'] += quality and not overlap
                counts['failing_history'] += overlap and not quality
                counts['failing_both'] += quality and overlap
            selections.append({**family, 'selected_id':chosen['angle_id'] if chosen else None,
                               'original_reasons':initial_reasons, 'replacement_reasons':replacement_reasons,
                               'selected_assessment':chosen})
        output.append({'cutoff':cutoff, 'counts':counts, 'families':selections,
                       'selected_ids':[s['selected_id'] for s in selections if s['selected_id']]})
    return output
