import type { Seeded } from './render';

/* Synthetic answers of the API, just complete enough for a screen to render from. They carry no client material. */

const anything = (value: unknown) => value as never;

export const WEEK = { week_id: 'week_1', week_start: '2026-10-05', week_end: '2026-10-11', status: 'reviewed', active_run_id: null };

export const ME_APPROVER = {
  email: 'whitney@example.invalid', name: 'Whitney', role: 'approver', roles: ['viewer', 'editor', 'approver'], source: 'users', identity_approver: true,
  can: { edit_cards: true, edit_briefs: true, decide: true, approve_briefs: true, review_knowledge: true, identity_review: true, manage_users: false,
    manage_intake: false, generate_packs: true, approve_packs: true, schedule_calendar: true },
};

export const ME_ADMIN = { ...ME_APPROVER, role: 'admin', roles: ['viewer', 'editor', 'approver', 'admin'], can: { ...ME_APPROVER.can, manage_intake: true, manage_users: true } };

export const ANGLE = {
  angle_id: 'angle_1', run_id: 'run_1', content_hash: 'hash_1', moment_ids: [],
  content_body: { title: 'Follow-up decides the ad', argument: 'a', audience: 'Owners', tension: 't', take: 'k', mechanism: 'm', reader_decision: 'r', qualifiers: [], risks: [], source_assertions: [], inference: null },
  base_score: 4.2, adjusted_score: 4.1, selection_status: 'visible', approval_status: 'pending', first_generated_at: '2026-10-08T11:28:56Z',
  selected_cta: null, matching_result: null, can_approve: true, can_edit: true, can_reject: true, has_replacement: false,
};

export const REVIEW = { week: WEEK, angles: [ANGLE], runs: [], jobs: [], events: [], transcripts: [] };

export const BRIEF_V2 = {
  brief_id: 'brief_1', week_id: 'week_1', angle_id: 'angle_1', content_hash: 'h', approval_status: 'pending', blockers: [], schema_version: 'brief_document_v2',
  can_approve: false, can_edit: true, can_review: true, can_consume: false, has_replacement: false, selected_evidence: [], prior_content_context: [], research_gaps: { items: [], coverage: {} },
  content_body: { schema_version: 'brief_document_v2', review: { findings: [], locked_fields: [] },
    document: { header: { cta: { choice: 'explicit', track: null, action: 'Reply to this email', offer_connection: null, chosen_by: 'writer' }, channels: ['reel'], purpose: 'WARM' },
      body: {
        approved_angle: { title: 'Why we ask about follow-up first', core_perspective: 'Follow-up shapes lead quality.' }, sharpened_point: null,
        strategic_purpose: { pillar: 'WARM', content_type: 'behind_the_scenes', why_now: 'Budget season.' }, audience: { who: 'Venue owners', reason_to_care: 'They want tours.' },
        intended_shift: { understand: 'u', believe: 'b', do: 'd' }, point_of_view: 'we', wia_perspective: 'We look at what happens after the inquiry.',
        supporting_example: { scene: 'A client call.', wia_move: 'Asked how the first reply was written.', client_contribution: 'Described it.' },
        narrative_outline: { hooks: [], problems_desires_symptoms: [], main_point: 'Follow-up is part of the ad.', transformation: 't', cta: 'c' },
        format_plan: { reels: [], carousel: null, email: null, caption: null, stories: null },
        cta: { choice: 'explicit', track: null, action: 'Reply to this email', offer_connection: null, chosen_by: 'writer' }, cta_why: 'Low barrier.',
        before_publishing: [], evidence: [], claims: [],
      } } },
};

export const DOCUMENT = {
  transcript_id: 't_1', title: 'Client call with Maple Venue', source_type: 'zoom', upstream_id: null, occurred_at: '2026-03-04T15:00:00Z', date_source: 'file_name',
  date_state: 'dated', call_type: 'client_1to1', included: true, exclusion_reason: null, client_id: 'client_maple', client_name: 'Maple Venue',
  participants: [{ name: 'Carmen Cruickshank', role: 'staff', person_id: 'p1' }, { name: 'Sam Maple', role: 'client', person_id: null }],
  passage_count: 12, word_count: 3400, extraction_status: 'completed', canonical_document_id: null, week_id: 'week_1', ingested_at: '2026-10-01T00:00:00Z',
  needs_review: false,
};

export const UNDATED_EXCLUDED = {
  ...DOCUMENT, transcript_id: 't_2', title: 'Vendor demo', source_type: 'fathom', occurred_at: null, date_source: null, date_state: 'undated', call_type: 'vendor',
  included: false, exclusion_reason: 'Vendor calls are not content evidence', client_id: null, client_name: null, extraction_status: 'not_applicable',
  canonical_document_id: 't_1', participants: [{ name: 'Vendor rep', role: 'unknown', person_id: null }],
};

export const DOCUMENT_LIST = {
  items: [DOCUMENT, UNDATED_EXCLUDED], total: 170, limit: 50, offset: 0,
  counts: { by_source_type: { zoom: 164, fathom: 6 }, by_call_type: { client_1to1: 90, vendor: 4 }, included: 150, excluded: 20, undated: 164, needs_review: 3 },
};

/** A call the rules could not place: it waits for a person (1.F6). */
export const WAITING = {
  ...DOCUMENT, transcript_id: 't_3', title: 'Zoom Meeting', call_type: 'client_1to1', client_id: null, client_name: null, needs_review: true, week_id: null,
};

export const DOCUMENT_DETAIL = {
  ...DOCUMENT,
  passages: [{ passage_id: 'p_1', ordinal: 1, speaker: 'Carmen Cruickshank', speaker_role: 'staff', start_ms: 64000, text: 'How do you reply to inquiries today?' }],
  classification: { call_type: 'client_1to1', method: 'rule', reason: 'one client and one staff speaker' },
};

export const INTAKE_OVERVIEW = {
  can_admin: true, schedule: 'Saturday 04:00 America/Chicago', sources: [{ source_id: 's1', title: 'Fathom call', kind: 'fathom', status: 'ready', received_at: '2026-10-10T10:00:00Z' }],
  connections: [], buckets: [{ bucket_id: 'b1', starts_at: '2026-10-03T09:00:00Z', status: 'open' }], requests: [], jobs: [],
};

export const KNOWN_ITEMS = { on: '2026-10-18', items: [], scheduled: [] };

export const seed = (route: string, args: unknown, data: unknown): Seeded => [route, args, anything(data)];

/** GET /schedule (3.B11): the weekly cycle starts by itself on Sunday at 04:00 in Chicago. */
export const SCHEDULE = { enabled: true, at: '2026-11-01T04:00:00-06:00', timezone: 'America/Chicago', text: 'Sunday 04:00 America/Chicago',
  window: { start: '2026-10-25T04:00:00-05:00', end: '2026-11-01T04:00:00-06:00' } };

/** GET /summary (6.F2): Home's cycle summary, with something waiting on every line. */
export const SUMMARY = {
  waiting: {
    cards_at_gate_1: { count: 3, who: 'an approver', by_week: [{ week_id: 'week_2026-10-19', n: 2 }, { week_id: 'week_2026-10-12', n: 1 }] },
    held_cards_due_back: { count: 1, who: 'an approver', cards: [{ angle_id: 'angle_held', week_id: 'week_2026-10-12', title: 'Answer the first inquiry within the hour', hold_until: '2026-10-24' }] },
    briefs_at_gate_2: { count: 2, who: 'an approver' },
    packs_in_review: { count: 1, who: 'an editor or an approver' },
    packs_ready: 1,
    packs_with_the_system: { finishing: 1, waiting: 1, reasons: [{ pack_id: 'pack_waiting', title: 'The tour that sold itself', reason: "This week's packs budget is spent." }] },
  },
  latest_cycle: { run_id: 'run_s', week_id: 'week_2026-10-19', status: 'waiting_for_review', created_at: '2026-10-25T09:02:00+00:00', trigger_type: 'scheduled',
    window: { start: '2026-10-18T09:00:00+00:00', end: '2026-10-25T09:00:00+00:00' }, started_from: 'schedule' },
  next_cycle: { enabled: true, at: '2026-11-01T04:00:00-06:00', timezone: 'America/Chicago', window: { start: '2026-10-25T04:00:00-05:00', end: '2026-11-01T04:00:00-06:00' } },
  sources: { connections: [{ connection_id: 'fathom', provider: 'fathom', activated_at: '2026-10-20T00:00:00+00:00', checkpoint: '2026-10-25T08:00:00+00:00', health: 'ok', error_summary: null }],
    extraction: { completed: 40, failed: 1, pending: 2 }, collector: 'active' },
  alerts: { open: 2, errors: 1 },
  spend: { this_week_usd: 1.25, caps_usd: 5, left_usd: 3.75, limits_reached: [], limits_close: [] },
  at: '2026-10-25T12:00:00+00:00',
};

/** GET /alerts (6.F5): an open error, an open warning, the scheduler's live silence and one dismissed in the last 14 days. */
export const ALERTS = {
  open: 3, email: 'off',
  alerts: [
    { alert_id: null, kind: 'scheduler_silent', subject: 'scheduler', severity: 'error', message: 'The scheduler has not completed a pass in the last 10 minutes', details: {},
      occurrences: 1, first_seen_at: '2026-10-25T11:40:00+00:00', last_seen_at: '2026-10-25T12:00:00+00:00', resolved_at: null, resolved_by: null, resolution: null },
    { alert_id: 'alert_job', kind: 'job_failed', subject: 'job_1', severity: 'error', message: 'A brief job failed: the provider timed out', details: {},
      occurrences: 4, first_seen_at: '2026-10-24T10:00:00+00:00', last_seen_at: '2026-10-25T11:55:00+00:00', resolved_at: null, resolved_by: null, resolution: null },
    { alert_id: 'alert_budget', kind: 'budget_refused', subject: 'briefs', severity: 'warning', message: "2 job(s) are waiting for this week's briefs budget", details: {},
      occurrences: 1, first_seen_at: '2026-10-25T09:00:00+00:00', last_seen_at: '2026-10-25T09:00:00+00:00', resolved_at: null, resolved_by: null, resolution: null },
    { alert_id: 'alert_old', kind: 'intake_stopped', subject: 'fathom', severity: 'error', message: 'No Fathom collection has run for 4 hours', details: {},
      occurrences: 2, first_seen_at: '2026-10-20T10:00:00+00:00', last_seen_at: '2026-10-20T11:00:00+00:00', resolved_at: '2026-10-20T12:00:00+00:00', resolved_by: 'editor@example.invalid', resolution: 'dismissed' },
  ],
};

const costGroup = (key: Record<string, string>, usd: number, calls: number) => ({ ...key, usd, calls, unknown_cost_calls: 0, input_tokens: calls * 1000, output_tokens: calls * 200 });
const costWeek = (week_start: string, usd: number) => ({
  week_start, week_end: week_start, usd, calls: usd ? 12 : 0, unknown_cost_calls: usd ? 1 : 0, input_tokens: 0, output_tokens: 0, external_usd: 0,
  by_purpose: usd ? [costGroup({ purpose: 'cycle', label: 'weekly cycle' }, usd * 0.75, 2), costGroup({ purpose: 'briefs', label: 'briefs' }, usd * 0.25, 10)] : [],
  by_stage: usd ? [costGroup({ stage: 'angle_generation' }, usd * 0.75, 2), costGroup({ stage: 'brief_generation' }, usd * 0.25, 10)] : [],
  by_model: usd ? [costGroup({ model: 'synthetic-large', provider: 'openrouter' }, usd, 12)] : [],
});
/** GET /costs (6.B7): two budget weeks, this week last. */
export const COSTS = {
  window: { start: '2026-10-12T00:00:00+00:00', end: '2026-10-26T00:00:00+00:00' }, currency: 'USD', total_usd: 2.0, by_status: { succeeded: 24 },
  models: { ...costWeek('2026-10-12T00:00:00+00:00', 2.0), calls: 24 },
  external: { calls: 0, usd: 0, by_service: [] },
  weeks: [costWeek('2026-10-12T00:00:00+00:00', 0.8), costWeek('2026-10-19T00:00:00+00:00', 1.2)],
  note: 'Recorded cost only.',
  since: { start: '2026-10-20T00:00:00+00:00', usd: 1.2, calls: 12, unknown_cost_calls: 0 },
  packs: [
    { run_id: 'pack_run_2', pack_id: 'pack_2', title: 'How we lowered a budget', week_id: 'week_2026-10-18', made_at: '2026-10-21T08:38:00+00:00',
      made_again: true, status: 'waiting_for_review', recorded: true, usd: 1.287944, calls: 5, unknown_cost_calls: 0, verified_calls: 5, reused_calls: 0, reused_original_usd: 0 },
    { run_id: 'pack_run_1', pack_id: 'pack_1', title: 'How we read a new ad', week_id: 'week_2026-10-12', made_at: '2026-10-14T17:03:00+00:00',
      made_again: false, status: 'waiting_for_review', recorded: true, usd: 0, calls: 0, unknown_cost_calls: 0, verified_calls: 0, reused_calls: 4, reused_original_usd: 0.6 },
    { run_id: 'pack_run_0', pack_id: 'pack_0', title: 'How we read a new ad', week_id: 'week_2026-10-12', made_at: '2026-10-14T16:28:00+00:00',
      made_again: false, status: 'failed', recorded: false, usd: 0, calls: 0, unknown_cost_calls: 0, verified_calls: 0, reused_calls: 0, reused_original_usd: 0 },
  ],
};

/** What the shell reads on every screen: the flags, who the person is, the stored weeks, the schedule and the summary. */
export const shell = (flags: Partial<Record<'briefs' | 'packs' | 'calendar' | 'context', boolean>> = {}, me: unknown = ME_APPROVER): Seeded[] => [
  seed('/flags', undefined, { briefs: true, packs: false, calendar: false, context: false, ...flags }),
  seed('/me', undefined, me),
  seed('/weeks', undefined, [WEEK]),
  seed('/weeks/{week_id}', { path: { week_id: 'week_1' } }, REVIEW),
  seed('/schedule', undefined, SCHEDULE),
  seed('/summary', undefined, SUMMARY),
];
