import type { PackPieceV2, PackSummaryV2, StoredPackV2, WeekPackPlanV2 } from '../api/types';

/* Synthetic content packs (contract v2) for the pack screens' tests (NP.F1 to NP.F4). Every line is made up for the tests:
   no client text (R48). The pieces are in brief contract v4's leaf shape, with the brief's copy beside them. */

const caption = {
  hook: 'Most inquiries stall at the first reply.',
  body: 'We read the reply before we touch the ads. A couple who waits two days for an answer books someone else.',
  ending: 'Follow-up is part of the ad.',
};

export const EMAIL_COPY = {
  job: 'The whole story', register: 'written',
  send_header: { date: 'Tuesday 3 November', send_time: '9:00 AM Eastern', recipients: 'All subscribers' },
  subject_options: ['Why we read the reply first', 'The inquiry is only the start', 'Before we touch the ads'],
  preview: 'It starts after the inquiry.',
  opening: 'Hi {{contact.first_name}},',
  body: 'Every week a venue owner asks us for more leads. Before we change a single ad, we read the first reply they send.',
  ending: 'Talk soon,\nWhitney',
  offer_descriptor: null, cta: 'reply',
};

const reel = (kind: 'story' | 'stance' | 'broll_text', extra: Record<string, unknown> = {}) => ({
  kind, job: `The ${kind} angle`, register: kind === 'broll_text' ? 'on_screen' : 'spoken',
  title: kind === 'story' ? 'The reply that lost the tour' : kind === 'stance' ? 'Leads are not the problem' : 'Read the reply first',
  cover_text: `Cover: ${kind}`, cover_alternates: [`First alternate cover for ${kind}`, `Second alternate cover for ${kind}`],
  on_screen_hook: `Your ads work. Then the ${kind} reply stops them.`,
  spoken_opening: kind === 'broll_text' ? null : 'The ads were never the problem.',
  script: kind === 'broll_text' ? null : `The ads were never the problem. Here is the ${kind} version of what happened next.`,
  screens: kind === 'broll_text' ? ['Inquiries went up.', 'Tours did not.', 'So we read the reply.'] : null,
  beats: ['a beat'], personal_lines: kind === 'story' ? ['I still think about that call.', 'We all have sent that reply.'] : [],
  read_time_seconds: 45, source: 'new_script', caption, offer_descriptor: null, cta: 'none',
  no_offer_ending: 'Save this for the next inquiry you answer.', ...extra,
});

export const CAROUSEL_COPY = {
  job: 'Go deeper', register: 'written', title: 'When more inquiries are not enough',
  slides: [1, 2, 3, 4, 5, 6, 7].map(n => ({ number: n, job: `Step ${n}`, text: `Slide ${n}, line one.\nSlide ${n}, line two.` })),
  caption, offer_descriptor: null, cta: 'none', no_offer_ending: null,
};

const EDITABLE = {
  email: ['send_header', 'subject_options', 'preview', 'opening', 'body', 'ending'],
  reel: ['title', 'cover_text', 'cover_alternates', 'on_screen_hook', 'spoken_opening', 'script', 'screens', 'caption', 'personal_lines', 'no_offer_ending'],
  carousel: ['title', 'slides', 'caption', 'no_offer_ending'],
};
const META: Record<PackPieceV2['key'], [PackPieceV2['channel'], string, number, PackPieceV2['kind']]> = {
  email: ['email', 'Email', 1, null], carousel: ['carousel', 'Carousel', 2, null], reel_1: ['reel', 'Reel 1', 3, 'story'],
  reel_2: ['reel', 'Reel 2', 4, 'stance'], reel_3: ['reel', 'Reel 3', 5, 'broll_text'],
};
const COPY: Record<PackPieceV2['key'], Record<string, unknown>> = {
  email: EMAIL_COPY, carousel: CAROUSEL_COPY, reel_1: reel('story'), reel_2: reel('stance'), reel_3: reel('broll_text'),
};
// The brief's copy: the finisher changed the email's preview and the story Reel's hook; the rest is the brief's.
const BRIEF_COPY: Record<PackPieceV2['key'], Record<string, unknown>> = {
  email: { ...EMAIL_COPY, preview: 'It all starts after the inquiry arrives.' },
  carousel: CAROUSEL_COPY,
  reel_1: { ...reel('story'), on_screen_hook: 'Your ads work, then the reply stops.' },
  reel_2: reel('stance'), reel_3: reel('broll_text'),
};

export function piece(key: PackPieceV2['key'], overrides: Partial<PackPieceV2> = {}): PackPieceV2 {
  const [channel, label, ordinal, kind] = META[key];
  return {
    key, channel, label, kind, ordinal, origin: 'finished', not_written_reason: null, brief_key: key,
    content: structuredClone(COPY[key]), brief_copy: structuredClone(BRIEF_COPY[key]), locks: [], findings: [],
    changes: key === 'email' ? [{ path: 'preview', kind: 'finished', before: 'It all starts after the inquiry arrives.', after: 'It starts after the inquiry.', note: null }] : [],
    published: [], content_hash: `hash_${key}`, editable: [...EDITABLE[channel]], ...overrides,
  };
}

export const PACK: StoredPackV2 = {
  pack_id: 'pack_1', contract_version: 'content_pack_v2', title: 'Why we read the reply first', week_id: 'week_2026-10-26',
  source_brief_id: 'brief_v4', source_brief_hash: 'brief_hash', angle_id: 'angle_1', pillar: 'WARM', rank: 1,
  state: 'in_review', state_reason: null, approval_status: 'pending', manifest_hash: 'manifest_1', approved_by: null, approved_at: null,
  created_at: '2026-10-24T10:00:00Z', supersedes_id: null, run_id: 'run_1', run_active: false,
  pieces: (['email', 'carousel', 'reel_1', 'reel_2', 'reel_3'] as const).map(k => piece(k)),
  findings: [], ready_blockers: [],
  before_publishing: [
    { id: 'P1', text: 'Confirm the client may be referenced in the story Reel.', kind: 'permission', required: true, answer: null, client_permission: true, done: null },
    { id: 'P2', text: 'Check the offer is still open before the email goes out.', kind: 'fact', required: false, answer: 'It is open until December.', client_permission: false, done: null },
  ],
  client_quotes: [{ quote_id: 'Q1', piece: 'reel_1', quote: 'We never answered on weekends.', speaker: 'the client', evidence_id: null, cleared: null }],
  stronger_with_permission: ['Naming the venue would make the story Reel concrete.'],
  granted: [],
  pack_notes: ['The stance Reel keeps the moment to two lines.'], change_notes: [], creative_choices: [],
  fidelity: null,
  provenance: { brief_id: 'brief_v4', approved_hash: 'brief_hash', brief_schema: 'brief_document_v4', handoff_version: 'brief_handoff_v2', run_id: 'run_1',
    mode: 'replay', finish_mode: 'finish', profiles: { pack_finish: '2026-10-25.pack-finish.v1' }, models: { pack_writer: 'claude-opus-5-5' },
    knowledge_base_version: 'wia-kb-2026-10-20', approved_by: 'approver@example.invalid', approval_delegated: false },
  change: null,
  versions: [{ pack_id: 'pack_1', supersedes_id: null, manifest_hash: 'manifest_1', approval_status: 'pending', created_at: '2026-10-24T10:00:00Z', run_id: 'run_1',
    kind: 'generated', by: 'the system', delegated: false, pieces: [], paths: [], note: null }],
  approval_delegated: false, can_edit: true, can_decide: true, can_finish_again: true, can_mark_published: true,
};

// ---- a pack from the Round 2 finisher: Reel 1 the central story, Reels 2 and 3 each a premise of its own ----

const premiseReel = (kind: 'central' | 'second' | 'third', production: 'face_to_camera' | 'on_screen_text', extra: Record<string, unknown> = {}) => {
  const { kind: _kind, ...base } = reel(production === 'on_screen_text' ? 'broll_text' : 'story');
  return {
    ...base, kind, production,
    title: kind === 'central' ? 'The reply that lost the tour' : kind === 'second' ? 'What a two-day wait tells a couple' : 'The question we ask first',
    premise: kind === 'central' ? 'A venue lost a tour because the first reply took two days.'
      : kind === 'second' ? 'A slow reply tells a couple how the wedding day will feel.' : 'We ask to see the reply before we touch the ads.',
    takeaway: kind === 'central' ? 'The reply is part of the ad.' : kind === 'second' ? 'Speed reads as care.' : 'Start with the reply, not the budget.',
    distinct_because: kind === 'central' ? 'It tells the story itself.' : kind === 'second' ? "It is the couple's view, not the venue's." : "It is WIA's own first move.",
    timestamps: kind === 'central' ? ['4:12 – the owner describes the two-day reply', '6:40 – the tour that never happened'] : ['11:05 – the strategist asks about replies'],
    personal_lines: [], ...extra,
  };
};
const R2_KINDS = { reel_1: ['central', 'face_to_camera'], reel_2: ['second', 'on_screen_text'], reel_3: ['third', 'face_to_camera'] } as const;
const r2Piece = (key: PackPieceV2['key'], overrides: Partial<PackPieceV2> = {}): PackPieceV2 => {
  if (key === 'email' || key === 'carousel') return piece(key, overrides);
  const [kind, production] = R2_KINDS[key];
  return piece(key, { kind, content: premiseReel(kind, production), brief_copy: premiseReel(kind, production), ...overrides });
};

/** An editor's blocking finding on Reel 2's first screen, and a craft note on the same Reel. */
export const EDITORIAL_BLOCKING = {
  finding_id: 'e1', source: 'editorial' as const, issue: 'unsupported_causation', piece: 'reel_2', path: 'screens[0]', sentence: 'Inquiries went up.', severity: 'blocking' as const,
  message: 'Reel 2: "Inquiries went up." states a cause the call does not show (the call never links the ads to the rise)', status: 'open' as const, resolution: null, can_attest: true,
};
export const EDITORIAL_WARNING = {
  finding_id: 'e2', source: 'editorial' as const, issue: 'slogan', piece: 'reel_2', path: 'caption.ending', sentence: 'Follow-up is part of the ad.', severity: 'warning' as const,
  message: 'Reel 2: "Follow-up is part of the ad." reads like a slogan rather than a real explanation', status: 'open' as const, resolution: null, can_attest: true,
};

export const PACK_R2: StoredPackV2 = {
  ...PACK, pack_id: 'pack_r2', manifest_hash: 'manifest_r2', source_brief_id: 'brief_r2',
  pieces: (['email', 'carousel', 'reel_1', 'reel_2', 'reel_3'] as const).map(k => r2Piece(k, k === 'reel_2' ? { findings: [EDITORIAL_BLOCKING, EDITORIAL_WARNING] } : {})),
  ready_blockers: ['Reel 2: "Inquiries went up." states a cause the call does not show. Edit that line, or keep it with a reason'],
  creative_choices: [
    { piece: 'email', considered: ['Why we read the reply first', 'The inquiry is only the start', 'Before we touch the ads'], chosen: 'Why we read the reply first',
      why: "It names what WIA does first, in the owner's words." },
    { piece: 'reel_2', considered: ['A slow reply tells a couple how the day will feel.', 'Owners answer on weekends too.'], chosen: 'A slow reply tells a couple how the day will feel.',
      why: "It gives the couple's view, which no other piece takes." },
  ],
  versions: [{ ...PACK.versions[0], pack_id: 'pack_r2', manifest_hash: 'manifest_r2' }],
};

/** A pack with changes, as a new version of PACK. */
export const version = (packId: string, overrides: Partial<StoredPackV2> = {}): StoredPackV2 => ({
  ...structuredClone(PACK), pack_id: packId, supersedes_id: 'pack_1', manifest_hash: `manifest_${packId}`,
  versions: [...PACK.versions, { ...PACK.versions[0], pack_id: packId, supersedes_id: 'pack_1', manifest_hash: `manifest_${packId}`, kind: 'edit', by: 'whitney@example.invalid' }],
  ...overrides,
});

export const SUMMARY: PackSummaryV2 = {
  pack_id: 'pack_1', title: PACK.title, week_id: PACK.week_id, source_brief_id: 'brief_v4', state: 'in_review', state_reason: null,
  approval_status: 'pending', manifest_hash: 'manifest_1', created_at: PACK.created_at, pillar: 'WARM', rank: 1,
  pieces: PACK.pieces.map(p => ({ key: p.key, label: p.label, kind: p.kind, origin: p.origin, published: false })), open_findings: 1, open_notes: 2,
};

export const PLAN: WeekPackPlanV2 = {
  week_id: 'week_2026-10-26', publishing_week_start: '2026-11-02', publishing_week_end: '2026-11-08',
  slots: [
    { slot: 'tuesday_email', label: 'Tuesday email', date: '2026-11-03', weekday: 'Tuesday', pack_id: 'pack_1', piece: 'email', piece_label: 'Email', title: PACK.title, cta: 'reply', note: null },
    { slot: 'instagram_1', label: 'Instagram 1', date: '2026-11-02', weekday: 'Monday', pack_id: 'pack_1', piece: 'reel_1', piece_label: 'Reel 1', title: 'The reply that lost the tour', cta: 'no_offer', note: null },
    { slot: 'instagram_2', label: 'Instagram 2', date: '2026-11-04', weekday: 'Wednesday', pack_id: 'pack_2', piece: 'carousel', piece_label: 'Carousel', title: 'Inquiry season', cta: 'no_offer', note: null },
    { slot: 'instagram_3', label: 'Instagram 3', date: '2026-11-06', weekday: 'Friday', pack_id: null, piece: null, piece_label: null, title: null, cta: 'offer', note: 'No CONVERT pack this week: choose the strongest piece.' },
  ],
  bank: [{ pack_id: 'pack_1', piece: 'reel_2', piece_label: 'Reel 2', title: 'Leads are not the problem', suggested_week: 2, reason: 'A second Reel from the same pack' }],
  findings: [{ severity: 'warning', message: 'Two covers this week open with the same words.', pieces: ['pack_1:reel_1', 'pack_2:carousel'] }],
  packs: [{ pack_id: 'pack_1', title: PACK.title, state: 'in_review', pillar: 'WARM', rank: 1 }, { pack_id: 'pack_2', title: 'Inquiry season', state: 'ready_to_publish', pillar: 'ATTRACT', rank: 2 }],
};

// ---- a v4 brief at Gate 2, for the hand-over (NP.F3) ----

const cta = { choice: 'explicit', track: null, action: 'Reply to this email', offer_connection: null, chosen_by: 'person' };
const briefReel = (kind: 'story' | 'stance' | 'broll_text') => {
  const { title: _title, cover_alternates: _alternates, cta: _cta, no_offer_ending: _ending, ...v4 } = reel(kind);
  return v4;
};
const BRIEF_BODY = {
  approved_angle: { title: 'Why we read the reply first', core_perspective: 'The first reply decides the tour.' }, sharpened_point: null,
  central_point: 'The first reply shapes which couples book a tour.',
  strategic_purpose: { pillar: 'WARM', content_type: 'behind_the_scenes', why_now: 'Inquiry season.', desired_response: 'I want a partner who looks past the click.' },
  intended_shift: { understand: 'u', believe: 'b', do: null }, audience: { who: 'Venue owners', reason_to_care: 'They want tours.' }, point_of_view: 'we',
  wia_perspective: 'We look at what happens after the inquiry.',
  supporting_example: { scene: 'A call about slow tours.', wia_move: 'Our strategist asked to see the reply.', client_contribution: 'The owner shared it.', timestamps: ['0:04 the question'],
    details: ['the first reply'], credits: [{ actor: 'our strategist', did: 'asked to see the reply' }] },
  narrative_outline: { hooks: [{ style: 'question', text: 'What happens after a couple inquires?' }], problems_desires_symptoms: ['Quiet inquiries'], main_point: 'm', transformation: 't', cta: 'c' },
  cta, cta_why: 'A low barrier.',
  before_publishing: [{ text: 'Confirm the client may be referenced.', kind: 'permission', required: false, answer: null }],
  format_plan: { reels: [briefReel('story'), briefReel('stance')], carousel: (({ cta: _c, no_offer_ending: _n, ...v4 }) => v4)(CAROUSEL_COPY),
    email: (({ cta: _c, ...v4 }) => v4)(EMAIL_COPY), stories: null },
  evidence: [], claims: [],
};

export const BRIEF_V4 = {
  brief_id: 'brief_v4', content_hash: 'h4', angle_id: 'angle_1', week_id: 'week_2026-10-26', approval_status: 'pending', blockers: [], schema_version: 'brief_document_v4',
  can_approve: true, can_edit: true, can_review: true, can_consume: false, can_record_published: false, has_replacement: false, locked_fields: [], anchor: null,
  selected_evidence: [], prior_content_context: [], research_gaps: { items: [], coverage: {} }, blocker_items: [], context_items: [],
  content_body: { schema_version: 'brief_document_v4', document: { header: { schema_version: 'brief_document_v4', cta, channels: ['reel', 'email', 'carousel', 'caption'], purpose: 'WARM' },
    body: BRIEF_BODY }, review: { findings: [], locked_fields: [] } },
};
export const BRIEF_V4_APPROVED = { ...BRIEF_V4, approval_status: 'approved', can_approve: false, can_consume: true, can_record_published: true };
