/* The moments ledger's synthetic answers (Phase 2): moments, facets, search, one moment's detail and the extraction health,
   as the API answers them, with every field present. They carry no client material. Used by tests only. */

export const MOMENT = {
  moment_id: 'm_reply', document_id: 't_1', document_title: 'Client call with Maple Venue', moment_type: 'result',
  quote: 'We reply to every inquiry within five minutes and our bookings doubled.',
  record: 'Maple Venue answers every inquiry within five minutes and says its bookings doubled.', context_summary: 'Sam describes the change since the follow-up routine began.',
  qualifications: ['Said about the spring season only'], speaker_label: 'Sam Maple', speaker_role: 'client', consent_status: 'cleared', sensitivity: 'public_candidate',
  evidence_kind: 'direct_quote', quote_verified: true, is_current: true, extractor_version: '2026-10-19.scenes.v2', destination: null,
  occurred_at: '2026-03-04T15:00:00Z', client_id: 'client_maple', client_name: 'Maple Venue', source_type: 'zoom', call_type: 'client_1to1',
  topics: [{ topic_id: 'topic_followup', name: 'Inquiry follow-up speed' }],
};
export const MOMENT_STAFF = {
  ...MOMENT, moment_id: 'm_staff', moment_type: 'observation', quote: 'Most couples go quiet if nobody writes back in a day.', record: 'Carmen explains why a slow reply loses couples.',
  speaker_label: 'Carmen Cruickshank', speaker_role: 'staff', consent_status: 'anonymise', evidence_kind: 'team_report', occurred_at: null, qualifications: [], topics: [], client_id: null, client_name: null,
};
export const MOMENT_INTERNAL = { ...MOMENT, moment_id: 'm_internal', moment_type: 'tension', quote: 'We nearly lost the venue over the deposit.', record: 'The deposit dispute.', consent_status: 'internal_only', topics: [] };
export const MOMENT_DNU = { ...MOMENT, moment_id: 'm_dnu', moment_type: 'testimonial', quote: 'Best decision we ever made.', record: 'A glowing review the client has withdrawn.', consent_status: 'do_not_use', topics: [] };
export const MOMENT_UNVERIFIED = { ...MOMENT, moment_id: 'm_unverified', moment_type: 'story', quote: 'I think we said something like three weeks.', record: 'A story about timing.', quote_verified: false, consent_status: 'anonymise', topics: [] };

export const MOMENT_LIST = { items: [MOMENT, MOMENT_STAFF], total: 40, limit: 25, offset: 0 };

const facet = (value: string, count: number, label: string | null = null) => ({ value, label, count });
export const MOMENT_FACETS = {
  total: 40,
  moment_types: [facet('result', 12), facet('observation', 9), facet('story', 4)],
  speaker_roles: [facet('client', 30), facet('staff', 10)],
  consent_statuses: [facet('cleared', 12), facet('anonymise', 20), facet('internal_only', 6), facet('do_not_use', 2)],
  clients: [facet('client_maple', 25, 'Maple Venue'), facet('client_oak', 15, 'Oak Florals')],
  source_types: [facet('zoom', 30), facet('fathom', 10)], call_types: [facet('client_1to1', 28), facet('office_hours', 12)],
  earliest: '2026-01-05T00:00:00Z', latest: '2026-10-01T00:00:00Z',
};

const topic = (topic_id: string, name: string, total_mentions: number, origin: string) => ({
  topic_id, name, description: null, pillars: [], status: 'active', merged_into: null, origin, created_by: null, created_at: '2026-10-01T00:00:00Z',
  updated_at: '2026-10-01T00:00:00Z', embedded: true, total_mentions, mentions_30d: 0, mentions_90d: 0, mentions_365d: total_mentions, distinct_clients: 2, last_mentioned_at: '2026-10-01T00:00:00Z',
});
export const TOPICS = { items: [topic('topic_followup', 'Inquiry follow-up speed', 7, 'model'), topic('topic_pricing', 'Raising prices', 3, 'person')], total: 2, limit: 200, offset: 0, counts: { active: 2 } };

export const CITATION = {
  document_id: 't_1', document_title: 'Client call with Maple Venue', source_type: 'zoom', call_type: 'client_1to1', passage_ids: ['p_2'], start: 110, end: 110 + MOMENT.quote.length, start_ms: 725000, end_ms: 740000,
  speaker_label: 'Sam Maple', speaker_id: null, speaker_role: 'client', client_id: 'client_maple', client_name: 'Maple Venue', consent_status: 'cleared',
  occurred_at: '2026-03-04T15:00:00Z', recording_url: 'https://fathom.video/share/abc', quote: MOMENT.quote,
};

export const SEARCH_RESPONSE = {
  hits: [
    { kind: 'moment', score: 0.03, matched_by: ['phrase', 'semantic'], moment: MOMENT, chunk: null, citation: CITATION },
    { kind: 'moment', score: 0.02, matched_by: ['semantic'], moment: MOMENT_STAFF, chunk: null, citation: { ...CITATION, speaker_label: 'Carmen Cruickshank', speaker_role: 'staff' } },
  ],
  query_embedding_status: 'used', query_embedding_detail: null, scope: 'moments', k: 50, hits_withheld: 0,
  filters_applied: {
    call_type: null, client_id: null, consent_defaulted: true, consent_status: ['cleared', 'anonymise', 'internal_only'], current_only: true, date_from: null, date_to: null,
    document_ids: [], kinds: ['moment'], moment_type: [], source_type: null, speaker_role: [], topic_id: null, topic_resolved_id: null, verified_only: true,
  },
};

const around = (passage_id: string, ordinal: number, start: number, end: number, speaker: string, speaker_role: string, text: string, start_ms: number, cited = false, anchor = false) =>
  ({ passage_id, ordinal, start, end, speaker, speaker_role, start_ms, end_ms: null, text, cited, anchor });
const ANCHOR_TEXT = `Honestly, ${MOMENT.quote} It changed the season.`;

export const MOMENT_DETAIL = {
  moment: {
    moment_id: 'm_reply', week_id: null, run_id: null, evidence_refs: [],
    moment_body: { quote: MOMENT.quote, context_summary: MOMENT.context_summary, proposition: null, moment_type: 'result', qualifications: [], claim_status: null, sensitivity: 'public_candidate', reasons: [], discovery: null },
  },
  passages: [{
    transcript_id: 't_1', passage_id: 'p_2', start: 100, end: 100 + ANCHOR_TEXT.length, roles: ['anchor'], text: ANCHOR_TEXT, title: 'Client call with Maple Venue',
    speaker: 'Sam Maple', speaker_role: 'client', start_ms: 725000, end_ms: null, source_url: 'https://fathom.video/share/abc',
  }],
  summary: MOMENT, citation: CITATION,
  document: { document_id: 't_1', title: 'Client call with Maple Venue', source_type: 'zoom', call_type: 'client_1to1', occurred_at: '2026-03-04T15:00:00Z', recording_url: 'https://fathom.video/share/abc' },
  surrounding: [
    around('p_1', 1, 0, 99, 'Carmen Cruickshank', 'staff', 'How do you reply to inquiries today?', 700000),
    around('p_2', 2, 100, 100 + ANCHOR_TEXT.length, 'Sam Maple', 'client', ANCHOR_TEXT, 725000, true, true),
    around('p_3', 3, 300, 330, 'Carmen Cruickshank', 'staff', 'That is a strong result.', 760000),
  ],
  evidence_intact: true, topics: [{ topic_id: 'topic_followup', name: 'Inquiry follow-up speed', assigned_by: 'model', similarity: 0.91 }],
  checks: {
    version: 'moment-checks.v1',
    role_plausibility: { passed: true, speaker_role: 'client', original_type: 'result', moment_type: 'result', evidence_kind: 'direct_quote' },
    numbers: { passed: true, figures: [], absent: [], context_only: [] },
    consent: { status: 'cleared', client_consent: 'may_name', sensitivity: 'public_candidate', evidence_kind: 'direct_quote' },
  },
  quote_repair: null, unverified_reason: null,
  cards: [{ angle_id: 'angle_1', week_id: 'week_1', title: 'Follow-up decides the ad', evidence_role: 'supports_argument', approval_status: 'pending', selection_status: 'selected' }],
};

export const EXTRACTION_HEALTH = {
  generated_at: '2026-10-19T12:00:00Z',
  totals: {
    included_documents: 100, by_status: { pending: 6, queued: 2, running: 1, completed: 85, failed: 3, not_applicable: 3 }, completed_documents: 85,
    zero_scene_documents: 5, zero_scene_share: 0.0588, moments: 200, verified_moments: 170, verified_quote_share: 0.85,
  },
  failed: [
    { document_id: 't_9', title: 'Long strategy call', source_type: 'zoom', job_id: 'job_1', error_summary: 'The model answered with something that was not usable', failed_at: '2026-10-18T09:00:00Z', attempts: 2 },
    { document_id: 't_10', title: 'Slack thread about pricing', source_type: 'slack', job_id: null, error_summary: null, failed_at: null, attempts: null },
  ],
  failed_total: 3,
  oldest_pending: { document_id: 't_11', title: 'Office hours in March', source_type: 'fathom', status: 'pending', ingested_at: '2026-10-10T00:00:00Z', waiting_hours: 220.5 },
  by_source_type: [
    { source_type: 'zoom', included_documents: 80, by_status: { completed: 70, failed: 2, pending: 8 }, completed_documents: 70, zero_scene_documents: 4, zero_scene_share: 0.0571, moments: 150, verified_moments: 120, verified_quote_share: 0.8 },
    { source_type: 'slack', included_documents: 20, by_status: { completed: 15, failed: 1, pending: 0 }, completed_documents: 15, zero_scene_documents: 1, zero_scene_share: 0.0667, moments: 50, verified_moments: 50, verified_quote_share: null },
  ],
};
