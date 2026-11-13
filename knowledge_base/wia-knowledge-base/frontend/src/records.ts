import { CLIENTS, SLACK_CHANNELS } from './data';
import type { Client, EngagementEvent, SourceKind } from './types';

// Fictional client-record data for the Client Portfolio scope (kb_tab_scope/02-client-portfolio.md).

export type Lifecycle = 'Onboarding' | 'Active' | 'Paused' | 'Offboarding';
export type SourceLabel = 'Documented client fact' | 'Voice of customer' | 'Strategic interpretation' | 'Ads data' | 'WIA benchmark';
export interface ProfileFact { label: string; value: string; tag: SourceLabel; sourceId?: string; sourceNote?: string; engagement?: string }
/** `basis` says where the start date came from (signed agreement, contract, checklist, or an estimate); `note` flags a conflict. */
export interface Engagement { type: string; start: string; programme?: string; phase?: string; signed?: string; basis?: string; note?: string }
export interface SourceRow { source: string; account: string; state: 'Linked' | 'Partial' | 'Blocked' | 'Not linked' | 'Not applicable'; lastSync?: string; from?: string; items?: number; note?: string }
/** Something WIA set up or manages that isn't working for the client. New work is a commitment; a question is an ask. */
export interface SupportIssue { id: string; title: string; raised: string; by: string; area: SupportArea; owner: string; state: 'Open' | 'Waiting on client' | 'Resolved' | 'Unknown'; latest: string; evidence?: string; actionId?: string; repeats?: number;
  channel?: SourceKind; resolved?: string; timeline?: { date: string; text: string; sourceId?: string }[] }
export const SUPPORT_AREAS = ['LeadLock workflow', 'LeadLock calendar', 'LeadLock access', 'Forms & tracking', 'Domain / DNS', 'Landing page', 'Ad account access', 'Reporting'] as const;
export type SupportArea = typeof SUPPORT_AREAS[number];
/** `recordId` is the KB record (live data only); `link` comes from Fathom or was added by the team. */
export interface MeetingRecord { id: string; recordId?: string; link?: string; linkSource?: 'Fathom' | 'Added by the team'; date: string; type: string; title: string; source: 'Fathom' | 'Zoom' | 'Drive archive' | 'Calendar'; transcript: 'Available' | 'Summary only' | 'Recording link only' | 'Not found'; attendees: string; summary?: string; decisions: string[]; actionIds: string[]; sourceId?: string; engagement?: string; shared?: boolean }
/** The owner as shown: confirmed name, else the suggestion, labelled as one. */
export const ownerText = (r: ClientRecord) => r.owner || (!r.ownerSuggestion ? 'Unassigned'
  : r.ownerSuggestion.confidence === 'Low' ? `Not set · likely ${r.ownerSuggestion.name} (default)` : `Suggested: ${r.ownerSuggestion.name}`);
/** The evidence behind an owner suggestion, as one sentence (shown on hover and in the details editor). */
export const suggestionWhy = (s: NonNullable<ClientRecord['ownerSuggestion']>) =>
  `${s.changed ? `Owner may have changed: ${s.name} runs the account now. ` : ''}${s.lead ? `Most activity: ${s.lead}. ` : ''}${s.why}.`;

export interface Change { id: string; date: string; kind: string; text: string; sourceId?: string }

export interface ClientRecord {
  owner: string;
  /** Read from the work (relationship tasks, client calls, email) until WIA confirms an owner. */
  ownerSuggestion?: { name: string; confidence: 'High' | 'Medium' | 'Low'; why: string; lead?: string; changed?: boolean };
  lifecycle: Lifecycle;
  aliases?: string[];
  engagements: Engagement[];
  earliestEvidence: string;
  processedThrough: string;
  lastContact: { date: string; channel: SourceKind };
  /** The Now tab's communication window: from the day of the last client call, else the last 30 days (`call` null). */
  commsWindow?: { since: string; call: string | null };
  links: { slack: string; drive: string; clickup: string; leadlock?: string };
  related?: { name: string; note: string };
  onboarding?: { phase: string; steps: { label: string; done: boolean; side: 'WIA' | 'Client' }[] };
  narrative: { status: 'Approved' | 'Draft waiting' | 'Stale'; approvedBy: string; approvedOn: string; staleReason?: string; draft?: { picture: string; focus: string; trigger: string; sourceIds: string[] } };
  profile: { section: string; facts: ProfileFact[] }[];
  contacts: { name: string; role: string; email: string; note?: string }[];
  team: { name: string; role: string }[];
  sources: SourceRow[];
  backfill: { state: 'Complete' | 'In progress'; percent: number; unprocessed: number };
  mappingSuggestion?: string;
  support: SupportIssue[];
  supportCoverage: string;
  meetings: MeetingRecord[];
  changes: Change[];
  /** Recurring meetings and reports (from calendar series and ClickUp recurring tasks). */
  cadence?: string[];
  /** Sensitive topics and preferences read from calls and email (KB reading). */
  sensitivities?: { text: string; sourceId?: string }[];
}

/** The Client Marketing Profile: the same sections and fields for every client (kb_tab_scope/02 B2). */
export const PROFILE_SCHEMA: { section: string; fields: { label: string; hint: string }[] }[] = [
  { section: 'Business', fields: [{ label: 'Who they are', hint: 'What they do and their story' }, { label: 'Category', hint: 'Venue, planner, photographer…' }, { label: 'Location & service area', hint: 'Where they are and where they travel' }] },
  { section: 'Offer', fields: [{ label: 'Packages & pricing', hint: 'Packages and starting prices' }, { label: 'Capacity & availability', hint: 'Weddings a year, booking window, open dates' }, { label: 'Minimums & policies', hint: 'Minimum spend, guest counts, deposits' }] },
  { section: 'Ideal client', fields: [{ label: 'Who their couples are', hint: 'The couples they want more of' }, { label: 'Budget', hint: 'What their couples typically spend' }, { label: 'What couples worry about', hint: 'Objections and questions couples raise' }] },
  { section: 'Differentiators & proof', fields: [{ label: 'What sets them apart', hint: 'Why couples choose them' }, { label: 'Proof to cite', hint: 'Reviews, awards, features, results' }] },
  { section: 'Voice', fields: [{ label: 'Tone', hint: 'How they sound' }, { label: 'Words to use', hint: 'Their own phrases' }, { label: 'Words to avoid', hint: 'Words they don’t want used' }] },
  { section: 'Goals', fields: [{ label: 'What success means', hint: 'In their words' }, { label: 'How WIA will judge it', hint: 'The playbook threshold or agreed target' }] },
];

export type MomentKind = 'Milestone' | 'Decision' | 'Client signal' | 'Commitment' | 'Delivery' | 'Risk';
/** A turning point on the account: chosen by the KB's history reading (AI), every one cited. */
export interface Moment { id: string; clientId: string; date: string; lane: EngagementEvent['lane']; kind: MomentKind; title: string; why: string; sourceIds: string[] }
/** An account milestone on the timeline. `Rule`: from a fixed rule on the record; `KB reading`: from calls or messages. */
export interface Milestone { id: string; clientId: string; date: string; label: string; basis: 'Rule' | 'KB reading' | 'Set by WIA'; sourceId?: string }

type Extras = { offer: string; capacity: string; serviceArea: string; objection: [string, string?]; proof: string; avoid: string; kpi: string; extraGoal?: ProfileFact; minimums?: string; budget?: string; use?: string };

function buildProfile(c: Client, x: Extras) {
  const src = c.profileSource;
  return [
    { section: 'Business', facts: [
      { label: 'Who they are', value: c.story, tag: 'Strategic interpretation' as const, sourceId: src },
      { label: 'Category', value: c.category, tag: 'Documented client fact' as const, sourceId: src },
      { label: 'Location & service area', value: `${c.location} · ${x.serviceArea}`, tag: 'Documented client fact' as const, sourceId: src },
    ] },
    { section: 'Offer', facts: [
      { label: 'Packages & pricing', value: x.offer, tag: 'Documented client fact' as const, sourceId: src },
      { label: 'Capacity & availability', value: x.capacity, tag: 'Documented client fact' as const, sourceId: src },
      ...(x.minimums ? [{ label: 'Minimums & policies', value: x.minimums, tag: 'Documented client fact' as const, sourceId: src }] : []),
    ] },
    { section: 'Ideal client', facts: [
      { label: 'Who their couples are', value: c.audience, tag: 'Documented client fact' as const, sourceId: src },
      ...(x.budget ? [{ label: 'Budget', value: x.budget, tag: 'Documented client fact' as const, sourceId: src }] : []),
      { label: 'What couples worry about', value: x.objection[0], tag: 'Voice of customer' as const, sourceId: x.objection[1] || src },
    ] },
    { section: 'Differentiators & proof', facts: [
      { label: 'What sets them apart', value: c.differentiator, tag: 'Documented client fact' as const, sourceId: src },
      { label: 'Proof to cite', value: x.proof, tag: 'Voice of customer' as const, sourceNote: 'Reviews linked in the Drive brand folder' },
    ] },
    { section: 'Voice', facts: [
      { label: 'Tone', value: c.voice, tag: 'Documented client fact' as const, sourceId: src },
      ...(x.use ? [{ label: 'Words to use', value: x.use, tag: 'Voice of customer' as const, sourceNote: 'Client’s own words, onboarding questionnaire' }] : []),
      { label: 'Words to avoid', value: x.avoid, tag: 'Strategic interpretation' as const, sourceNote: 'WIA team note, approved by account owner' },
    ] },
    { section: 'Goals', facts: [
      { label: 'What success means', value: c.goal, tag: 'Documented client fact' as const, sourceId: src },
      { label: 'How WIA will judge it', value: x.kpi, tag: 'WIA benchmark' as const, sourceNote: 'WIA playbook threshold' },
      ...(x.extraGoal ? [x.extraGoal] : []),
    ] },
  ];
}

const standardSources = (id: string, o: Partial<Record<string, Partial<SourceRow>>> = {}): SourceRow[] => {
  const c = CLIENTS.find(x => x.id === id)!;
  const base: SourceRow[] = [
    { source: 'Slack', account: SLACK_CHANNELS[id].channel, state: 'Linked', lastSync: '9:40 AM', from: c.since, items: 214 },
    { source: 'Gmail', account: `${c.email.split('@')[1]} + 2 contacts`, state: 'Linked', lastSync: '9:38 AM', from: c.since, items: 63 },
    { source: 'ClickUp', account: `${c.name} · Client Management`, state: 'Linked', lastSync: '9:42 AM', from: c.since, items: 41 },
    { source: 'Fathom', account: 'Matched by contact email', state: 'Linked', lastSync: '9:15 AM', from: '2026-06-01', items: 6, note: 'Fathom used for all calls since Jun 2026' },
    { source: 'Zoom history', account: 'Drive archive: Call recordings', state: 'Partial', lastSync: '9:15 AM', from: c.since, items: 3, note: 'Older recordings are video only; no transcription in scope' },
    { source: 'Drive', account: `${c.name} / Client folder`, state: 'Linked', lastSync: '9:36 AM', from: c.since, items: 28 },
    { source: 'LeadLock', account: 'Not part of this engagement', state: 'Not applicable' },
    { source: 'Calendar', account: 'Events with contact emails', state: 'Linked', lastSync: '9:41 AM', from: c.since, items: 12 },
  ];
  return base.map(row => ({ ...row, ...(o[row.source] || {}) }));
};
const leadlockBlocked: Partial<SourceRow> = { account: 'LeadLock location linked', state: 'Blocked', note: 'Account link works; lead and support reads are denied (scope). Shown as Unavailable' };

const c = (id: string) => CLIENTS.find(x => x.id === id)!;

export const RECORDS: Record<string, ClientRecord> = {
  bloom: {
    owner: 'Jacqueline', lifecycle: 'Active', aliases: ['Bloom Manor Estate'],
    engagements: [{ type: 'Elevate', start: '2026-04-06', signed: '2026-04-02' }],
    earliestEvidence: '2026-03-28', processedThrough: '2026-10-09', lastContact: { date: '2026-10-08', channel: 'Gmail' },
    links: { slack: '#client-bloom-manor', drive: 'Bloom Manor / Client folder', clickup: 'Bloom Manor · Client Management' },
    narrative: { status: 'Draft waiting', approvedBy: 'Jacqueline', approvedOn: '2026-10-02', draft: { picture: 'Sarah emailed on Oct 8 asking what we know about inquiry quality before Thursday’s call. The revised landing page was due to her on Oct 8 and hasn’t gone out yet, so her approval is still waiting on us.', focus: 'Send the revised page today, and lead the Oct 9 call with Sarah’s inquiry-quality question.', trigger: 'New client email (Oct 8) and a missed commitment date', sourceIds: ['bloom-email', 'bloom-call'] } },
    profile: buildProfile(c('bloom'), { offer: 'Full-weekend venue hire; one wedding per weekend. Peak Saturdays from $14,000.', capacity: 'One celebration per weekend. Spring and autumn weekends book 12–14 months ahead.', serviceArea: 'Hill Country, within 45 minutes of Austin', objection: ['Whether the garden works if it rains, and how private the weekend really is.'], proof: 'Reviews repeatedly mention privacy, the covered garden and "felt like our own estate".', avoid: '"Luxury", "dream venue", "exclusive". Let the setting do the talking.', kpi: 'Landing-page conversion of at least 3.5% (Google playbook flags anything lower).', minimums: 'Saturday minimum spend $14,000; 120 guests maximum; 30% deposit to hold a date.', budget: '$30,000–$55,000 all-in, venue about a third of it.', use: '“Your own estate for the weekend”, “unhurried”, “garden ceremony”.' }),
    contacts: [{ name: 'Sarah Mitchell', role: 'Owner · approves all copy and pages', email: 'sarah@bloom.example', note: 'Prefers email; decides quickly once she has the page' }, { name: 'Tom Mitchell', role: 'Co-owner · budget decisions', email: 'tom@bloom.example' }],
    team: [{ name: 'Jacqueline', role: 'Account owner' }, { name: 'Carmen', role: 'Ads manager' }, { name: 'Whitney', role: 'Strategy calls' }],
    sources: standardSources('bloom'), backfill: { state: 'Complete', percent: 100, unprocessed: 4 },
    support: [
      { id: 's0', title: 'Thank-you page wasn’t recording Meta leads', raised: '2026-08-11', by: 'Carmen', area: 'Forms & tracking', owner: 'Carmen', state: 'Resolved', resolved: '2026-08-14', channel: 'Slack', latest: 'Pixel event re-added and checked with a test inquiry',
        evidence: 'Slack · Carmen, Aug 14: “Lead event firing again, test inquiry recorded in Events Manager.”',
        timeline: [{ date: '2026-08-11', text: 'Carmen noticed Meta leads dropped to zero while inquiries kept arriving.' }, { date: '2026-08-12', text: 'Cause found: the page rebuild removed the Lead event.' }, { date: '2026-08-14', text: 'Event re-added; a test inquiry was recorded.' }] },
    ], supportCoverage: 'Support requests from Gmail and Slack only.',
    cadence: ['Monthly strategy call with Sarah (first week of the month)', 'Monthly report by the 5th', 'Ads checked daily by Carmen'],
    sensitivities: [{ text: 'Budget topics only when Tom is on the call.', sourceId: 'bloom-call' }, { text: 'Sarah reads everything before calls; send material the day before.', sourceId: 'bloom-email' }],
    meetings: [
      { id: 'm-bloom-1', date: '2026-09-30', type: 'Strategy', title: 'September strategy call', source: 'Zoom', transcript: 'Available', attendees: 'Sarah, Whitney, Jacqueline', summary: 'Reviewed the autumn gallery and the revised landing page. Sarah wants the page signed off before any campaign messaging changes, and asked to understand inquiry quality before the next refresh.', decisions: ['Get the revised page approved before changing campaign messaging.', 'Page goes to Sarah for approval by Oct 8.'], actionIds: ['a1'], sourceId: 'bloom-call' },
      { id: 'm-bloom-3', date: '2026-07-07', type: 'Check-in', title: 'July check-in', source: 'Calendar', transcript: 'Not found', attendees: 'Sarah, Whitney', decisions: [], actionIds: [] },
      { id: 'm-bloom-2', date: '2026-04-06', type: 'Onboarding', title: 'Onboarding call', source: 'Drive archive', transcript: 'Recording link only', attendees: 'Sarah, Tom, Whitney', decisions: [], actionIds: [] },
    ],
    changes: [
      { id: 'ch-b1', date: '2026-10-08', kind: 'Client message', text: 'Sarah asked about inquiry quality before the call.', sourceId: 'bloom-email' },
      { id: 'ch-b2', date: '2026-10-08', kind: 'Missed date', text: '"Send the revised landing page" passed its Oct 8 date.' },
      { id: 'ch-b3', date: '2026-10-07', kind: 'ClickUp', text: 'Landing-page task moved to In progress.', sourceId: 'bloom-task' },
    ],
  },
  rosewood: {
    owner: 'Jacqueline', lifecycle: 'Active',
    engagements: [{ type: 'Elevate', start: '2026-02-12', signed: '2026-02-09' }, { type: 'LeadLock', start: '2026-03-01', phase: 'Live', signed: '2026-02-24' }],
    earliestEvidence: '2026-01-30', processedThrough: '2026-10-09', lastContact: { date: '2026-10-07', channel: 'Slack' },
    links: { slack: '#client-rosewood', drive: 'Rosewood Estate / Client folder', clickup: 'Rosewood Estate · Client Management', leadlock: 'Rosewood Estate (location)' },
    related: { name: 'Rosewood Cottages', note: 'Sister property. Shares #client-rosewood; separate LeadLock location and no WIA engagement' },
    narrative: { status: 'Approved', approvedBy: 'Jacqueline', approvedOn: '2026-10-07' },
    profile: buildProfile(c('rosewood'), { offer: 'Venue + on-site accommodation packages; midweek micro-weddings from $6,500.', capacity: 'Two weddings a week in peak season; winter dates open.', serviceArea: 'Lowcountry, Charleston and Kiawah', objection: ['How guests get between the house and the accommodation in bad weather.'], proof: 'Hosted 40+ weddings in 2025; reviews praise the venue host by name.', avoid: '"Luxury", "opulent". Use concrete details instead.', kpi: 'Meta landing-page views at least 50% of link clicks (Meta playbook).', budget: '$25,000–$40,000; micro-weddings under $12,000.', use: '“Stay the whole weekend”, “the house and the gardens”.', extraGoal: { label: 'LeadLock goal', value: 'Every new inquiry gets a personal reply within 5 minutes, day or night.', tag: 'Documented client fact', sourceId: 'rosewood-call', engagement: 'LeadLock' } }),
    contacts: [{ name: 'Dana Whitfield', role: 'Venue director · approves copy', email: 'dana@rosewood.example', note: 'Likes to see a test inquiry before sign-off' }],
    team: [{ name: 'Jacqueline', role: 'Account owner' }, { name: 'Danielle', role: 'LeadLock specialist' }, { name: 'Ivy', role: 'Reporting' }],
    sources: standardSources('rosewood', { LeadLock: leadlockBlocked }), backfill: { state: 'Complete', percent: 100, unprocessed: 7 },
    support: [
      { id: 's1', title: 'Follow-up sequence sent duplicate texts', raised: '2026-09-18', by: 'Dana Whitfield', area: 'LeadLock workflow', owner: 'Danielle', state: 'Resolved', resolved: '2026-09-19', channel: 'Gmail', latest: 'Trigger fixed and re-tested', evidence: 'Slack · Danielle, Sep 19: "Duplicate trigger removed, test inquiry clean."',
        timeline: [{ date: '2026-09-18', text: 'Dana emailed: two couples got the same text twice.' }, { date: '2026-09-18', text: 'Danielle found a second trigger on the same form.' }, { date: '2026-09-19', text: 'Duplicate trigger removed; test inquiry clean.', sourceId: 'rosewood-slack' }] },
      { id: 's2', title: 'Tour-booking link opens in the wrong timezone', raised: '2026-10-06', by: 'Dana Whitfield', area: 'LeadLock calendar', owner: 'Danielle', state: 'Open', channel: 'Gmail', latest: 'Danielle reproduced it; fix not yet confirmed', repeats: 2, actionId: 'a5',
        timeline: [{ date: '2026-09-29', text: 'First report: a couple booked a tour an hour off.' }, { date: '2026-10-06', text: 'Dana reported it again: “showing couples the wrong times again”.' }, { date: '2026-10-06', text: 'Danielle reproduced it on the booking page.' }] },
    ], supportCoverage: 'Support requests from Gmail and Slack only. The LeadLock support inbox is not connected.',
    cadence: ['Monthly strategy call with Dana', 'LeadLock follow-up review every quarter', 'Monthly report by the 5th'],
    sensitivities: [{ text: 'Dana wants a test inquiry before anything is called done.', sourceId: 'rosewood-call' }],
    meetings: [
      { id: 'm-rw-1', date: '2026-10-02', type: 'Strategy', title: 'Follow-up sequence review', source: 'Zoom', transcript: 'Available', attendees: 'Dana, Whitney, Danielle', summary: 'Dana approved the revised follow-up sequence and said it finally sounds like Rosewood. Danielle will run a test inquiry before it goes live, and winter tours are the next focus.', decisions: ['Revised follow-up sequence approved.', 'Danielle runs a test inquiry before it is marked complete.', 'Next focus: winter-tour messaging.'], actionIds: ['a4', 'a5'], sourceId: 'rosewood-call', engagement: 'LeadLock' },
      { id: 'm-rw-2', date: '2026-09-04', type: 'Strategy', title: 'Monthly strategy call', source: 'Fathom', transcript: 'Summary only', attendees: 'Dana, Whitney, Jacqueline', decisions: ['Pause winter Meta campaigns until new gallery is ready.'], actionIds: [], engagement: 'Elevate' },
    ],
    changes: [{ id: 'ch-r1', date: '2026-10-07', kind: 'Slack', text: 'Jacqueline committed to a winter-tour draft for the next call.', sourceId: 'rosewood-slack' }, { id: 'ch-r2', date: '2026-10-07', kind: 'Done', text: 'Danielle reported the test inquiry passed.', sourceId: 'rosewood-slack' }],
  },
  willow: {
    owner: 'Jacqueline', lifecycle: 'Active',
    engagements: [{ type: 'Meta Ads Accelerator', start: '2026-07-14', programme: 'Meta Ads Accelerator · Summer cohort', phase: 'Week 13 of 16', signed: '2026-07-10' }],
    earliestEvidence: '2026-07-08', processedThrough: '2026-10-09', lastContact: { date: '2026-10-05', channel: 'Gmail' },
    links: { slack: '#meta-accelerator', drive: 'Meta Accelerator / Willow & Pine', clickup: 'Meta Ads Accelerator · Client Management' },
    narrative: { status: 'Stale', approvedBy: 'Gisselle', approvedOn: '2026-09-26', staleReason: 'Maya emailed on Oct 5, after this was approved. A new draft is being prepared.' },
    profile: buildProfile(c('willow'), { offer: 'Full planning from $7,500; partial planning from $4,200.', capacity: 'About 20 weddings a year; books mostly May–October.', serviceArea: 'Western North Carolina mountains', objection: ['Whether a planner adds enough to justify the cost for a small wedding.', 'willow-email'], proof: 'Long-standing supplier relationships; planner of record for 3 local venues.', avoid: 'Hype words. Keep it practical and reassuring.', kpi: 'Meta link CTR of at least 1% (Meta playbook).' }),
    contacts: [{ name: 'Maya Stone', role: 'Owner · runs her own campaigns', email: 'maya@willow.example', note: 'Does best with one concrete next step at a time' }],
    team: [{ name: 'Jacqueline', role: 'Account owner · Meta office hours' }, { name: 'Gisselle', role: 'Programme operations' }],
    sources: standardSources('willow', { Slack: { account: '#meta-accelerator (shared programme channel)', note: 'Only messages by or about Maya are linked to this client', items: 37 }, ClickUp: { account: 'Meta Ads Accelerator · Client Management (shared list)', items: 9 } }), backfill: { state: 'Complete', percent: 100, unprocessed: 2 },
    support: [], supportCoverage: 'Accelerator clients run their own ad accounts; support requests come through office hours and Gmail.',
    cadence: ['Meta office hours every Wednesday (group)', 'Programme check-in every 4 weeks'],
    sensitivities: [{ text: 'Maya does best with one concrete next step at a time.', sourceId: 'willow-email' }],
    meetings: [
      { id: 'm-w-1', date: '2026-09-24', type: 'Office hours', title: 'Meta office hours · creative review', source: 'Fathom', transcript: 'Available', attendees: 'Maya, Jacqueline + 6 members', summary: 'Group creative review. Maya shared two draft concepts; Jacqueline suggested starting from one clear planning moment rather than the whole service.', decisions: ['Start with one clear planning moment for the next creative.'], actionIds: ['a12'], sourceId: 'willow-fathom', shared: true },
      { id: 'm-w-2', date: '2026-10-08', type: 'Office hours', title: 'Meta office hours', source: 'Fathom', transcript: 'Not found', attendees: 'Programme session', decisions: [], actionIds: [], shared: true },
    ],
    changes: [{ id: 'ch-w1', date: '2026-10-05', kind: 'Client message', text: 'Maya asked for feedback on one creative example.', sourceId: 'willow-email' }],
  },
  everly: {
    owner: 'Ivy', lifecycle: 'Active',
    engagements: [{ type: 'Elevate', start: '2026-05-18', signed: '2026-05-14' }],
    earliestEvidence: '2026-05-06', processedThrough: '2026-10-09', lastContact: { date: '2026-10-08', channel: 'Slack' },
    links: { slack: '#client-everly-films', drive: 'Everly Films / Client folder', clickup: 'Everly Films · Client Management' },
    narrative: { status: 'Approved', approvedBy: 'Ivy', approvedOn: '2026-10-02' },
    profile: buildProfile(c('everly'), { offer: 'Documentary films from $3,800; elopement films from $1,900.', capacity: 'Three spring 2027 dates still open.', serviceArea: 'Nashville and travel across the Southeast', objection: ['Whether a small crew will miss important moments.'], proof: 'Couples quote the real audio and vows in reviews; featured on two wedding blogs.', avoid: '"Cinematic", "epic", "breathtaking".', kpi: 'Inquiries mentioning the documentary style, tracked monthly.' }),
    contacts: [{ name: 'Nina Cole', role: 'Owner & filmmaker', email: 'nina@everly.example' }],
    team: [{ name: 'Ivy', role: 'Account owner' }, { name: 'Whitney', role: 'Strategy calls' }],
    sources: standardSources('everly'), backfill: { state: 'Complete', percent: 100, unprocessed: 11 },
    support: [], supportCoverage: 'Support requests from Gmail and Slack only.',
    cadence: ['Creative review with Nina every month', 'Monthly report by the 5th'],
    sensitivities: [{ text: 'Keep it personal; Nina dislikes promotional wording.', sourceId: 'everly-call' }],
    meetings: [{ id: 'm-e-1', date: '2026-10-01', type: 'Creative review', title: 'Portfolio & seasonal availability', source: 'Zoom', transcript: 'Available', attendees: 'Nina, Whitney, Ivy', summary: 'Nina approved the new portfolio edit. The team agreed to show spring availability in the inquiry journey without making the page feel promotional.', decisions: ['Portfolio edit approved.', 'Bring available spring dates into the inquiry journey without making it promotional.'], actionIds: ['a7', 'a11', 'a16'], sourceId: 'everly-call' }],
    changes: [{ id: 'ch-e1', date: '2026-10-06', kind: 'ClickUp', text: 'Spring-dates page update moved to In progress.' }],
  },
  harbor: {
    owner: 'Danielle', lifecycle: 'Onboarding', aliases: ['Harbor House Weddings'],
    engagements: [{ type: 'Elevate', start: '2026-09-21', phase: 'Messaging', signed: '2026-09-19' }, { type: 'LeadLock', start: '2026-09-21', phase: 'Kickoff', signed: '2026-09-19' }],
    earliestEvidence: '2026-09-10', processedThrough: '2026-10-09', lastContact: { date: '2026-10-08', channel: 'Gmail' },
    links: { slack: '#client-harbor-house', drive: 'Harbor House / Client folder', clickup: 'Harbor House · Onboarding', leadlock: 'Harbor House (location)' },
    onboarding: { phase: 'Week 3 · LeadLock kickoff', steps: [
      { label: 'Onboarding questionnaire returned', done: true, side: 'Client' }, { label: 'Messaging & positioning interview', done: true, side: 'WIA' },
      { label: 'Confirm current CRM and access owner', done: false, side: 'Client' }, { label: 'LeadLock kickoff call', done: false, side: 'WIA' },
      { label: 'Domain & DNS setup', done: false, side: 'WIA' }, { label: 'Share ad-account access', done: false, side: 'Client' }, { label: 'Campaigns live', done: false, side: 'WIA' },
    ] },
    narrative: { status: 'Approved', approvedBy: 'Danielle', approvedOn: '2026-10-08' },
    profile: buildProfile(c('harbor'), { offer: 'Waterfront ceremony + reception packages from $11,000.', capacity: 'Weekend weddings May–October; Fridays available.', serviceArea: 'Southern Maine coast', objection: ['Weather plans for a waterfront ceremony.', 'harbor-email'], proof: 'Not yet collected. Ask for reviews during onboarding.', avoid: 'Not yet agreed.', kpi: 'Google CTR 3–5% once campaigns launch (Google playbook).', extraGoal: { label: 'LeadLock goal', value: 'One clear owner for every new inquiry, with nothing left unanswered.', tag: 'Documented client fact', sourceId: 'harbor-drive', engagement: 'LeadLock' } }),
    contacts: [{ name: 'Elise Bennett', role: 'Owner · signs off', email: 'elise@harbor.example' }, { name: 'Unknown', role: 'Venue coordinator · handles inquiries today', email: 'Not yet known', note: 'Elise is checking CRM access with them' }],
    team: [{ name: 'Danielle', role: 'Account owner · LeadLock' }, { name: 'Whitney', role: 'Messaging interview' }],
    sources: standardSources('harbor', { LeadLock: leadlockBlocked, Fathom: { from: '2026-09-21', items: 2 }, 'Zoom history': { state: 'Not applicable', account: 'Client started after the move to Fathom', note: undefined, items: undefined, from: undefined, lastSync: undefined } }),
    backfill: { state: 'In progress', percent: 64, unprocessed: 0 },
    mappingSuggestion: 'Drive folder "Harbor House – Brand Photos" (created Oct 7) looks like it belongs to this client.',
    support: [
      { id: 's3', title: 'LeadLock domain DNS records incomplete', raised: '2026-10-08', by: 'Danielle', area: 'Domain / DNS', owner: 'Danielle', state: 'Open', channel: 'ClickUp', latest: 'ClickUp task closed but SPF/DKIM and form test unticked (in Needs review)',
        timeline: [{ date: '2026-10-08', text: 'Domain task marked complete in ClickUp with two checklist items unticked.' }, { date: '2026-10-08', text: 'Flagged for review: email from the new domain may land in spam.' }] },
      { id: 's4', title: 'Can’t log in to the LeadLock app', raised: '2026-10-07', by: 'Elise Bennett', area: 'LeadLock access', owner: 'Danielle', state: 'Waiting on client', channel: 'Gmail', latest: 'Invite re-sent; Elise needs to accept it',
        timeline: [{ date: '2026-10-07', text: 'Elise emailed: the login link had expired.', sourceId: 'harbor-email' }, { date: '2026-10-07', text: 'Danielle re-sent the invite.' }] },
    ], supportCoverage: 'Support requests from Gmail and Slack only. The LeadLock support inbox is not connected.',
    cadence: ['Weekly onboarding check-in with Elise until launch', 'LeadLock kickoff call, then a monthly LeadLock review'],
    sensitivities: [{ text: 'Elise wants it clear which parts stay with her team.', sourceId: 'harbor-email' }],
    meetings: [
      { id: 'm-h-1', date: '2026-10-06', type: 'Messaging interview', title: 'Messaging & positioning interview', source: 'Zoom', transcript: 'Available', attendees: 'Elise, Whitney', summary: 'Deep-dive on Harbor House’s story, couples and voice. Elise isn’t sure which CRM the team uses today or who owns it, which needs answering before the LeadLock kickoff.', decisions: ['Confirm the CRM and its owner before the LeadLock kickoff.'], actionIds: ['a8', 'a9'], sourceId: 'harbor-call', engagement: 'Elevate' },
      { id: 'm-h-2', date: '2026-09-21', type: 'Onboarding', title: 'Welcome & onboarding call', source: 'Fathom', transcript: 'Summary only', attendees: 'Elise, Danielle', decisions: ['Questionnaire due Sep 28.'], actionIds: [], engagement: 'LeadLock' },
    ],
    changes: [{ id: 'ch-h1', date: '2026-10-08', kind: 'Client message', text: 'Elise asked the kickoff to cover who sets up what.', sourceId: 'harbor-email' }, { id: 'ch-h2', date: '2026-10-08', kind: 'Support', text: 'New issue: DNS records incomplete.' }],
  },
  magnolia: {
    owner: 'Carmen', lifecycle: 'Active',
    engagements: [{ type: 'Google Search Accelerator', start: '2026-06-02', programme: 'Google Search Accelerator · Summer cohort', phase: 'Week 19', signed: '2026-05-29' }],
    earliestEvidence: '2026-05-27', processedThrough: '2026-10-09', lastContact: { date: '2026-10-06', channel: 'Slack' },
    links: { slack: '#google-accelerator', drive: 'Google Accelerator / Magnolia Events', clickup: 'Google Search Accelerator · Client Management' },
    narrative: { status: 'Approved', approvedBy: 'Carmen', approvedOn: '2026-10-06' },
    profile: buildProfile(c('magnolia'), { offer: 'Three planning packages: day-of $2,200, partial $4,800, full $8,500.', capacity: 'Up to 25 weddings a year.', serviceArea: 'Denver metro and Front Range', objection: ['Not knowing which package fits their wedding.'], proof: 'Clear package comparison page; testimonials mention calm on the day.', avoid: '"Stress-free" (overused).', kpi: 'Google CTR 3–5%; conversion rate above 3.5% (Google playbook).' }),
    contacts: [{ name: 'Tessa Ruiz', role: 'Owner · runs her own campaigns', email: 'tessa@magnolia.example' }],
    team: [{ name: 'Carmen', role: 'Account owner · Google office hours' }, { name: 'Gisselle', role: 'Programme operations' }],
    sources: standardSources('magnolia', { Slack: { account: '#google-accelerator (shared programme channel)', note: 'Only messages by or about Tessa are linked to this client', items: 29 }, ClickUp: { account: 'Google Search Accelerator · Client Management (shared list)', items: 7 } }), backfill: { state: 'Complete', percent: 100, unprocessed: 1 },
    support: [], supportCoverage: 'Accelerator clients run their own ad accounts; support requests come through office hours and Gmail.',
    cadence: ['Google office hours every Tuesday (group)'],
    meetings: [{ id: 'm-m-1', date: '2026-10-07', type: 'Office hours', title: 'Google office hours', source: 'Fathom', transcript: 'Available', attendees: 'Tessa, Carmen + 5 members', summary: 'Group session on search intent. Tessa showed her revised landing page; Carmen asked members to bring keyword groups to the next session.', decisions: ['Bring keyword groups to the next session.'], actionIds: ['a10'], shared: true }],
    changes: [{ id: 'ch-m1', date: '2026-10-06', kind: 'Slack', text: 'Tessa finished her page revision and grouped keywords.', sourceId: 'magnolia-slack' }],
  },
};

export const recordFor = (id: string) => RECORDS[id];
export const ENGAGEMENT_TYPES = ['Elevate', 'LeadLock', 'Google Search Accelerator', 'Meta Ads Accelerator'];
export const LIFECYCLES: Lifecycle[] = ['Onboarding', 'Active', 'Paused', 'Offboarding'];
export const linkedCount = (r: ClientRecord) => { const applicable = r.sources.filter(s => s.state !== 'Not applicable'); return { linked: applicable.filter(s => s.state !== 'Not linked').length, total: applicable.length }; };

// Client communication log for the Now sub-tab's "this week" card. Calls count once, for both sides.
/** 'Team' = the WIA team's own thread in the client's (internal) Slack channel: work on the client, not contact with them. */
export interface Comm { id: string; date: string; channel: SourceKind; from: 'Client' | 'WIA' | 'Call' | 'Team'; who: string; text: string; sourceId?: string }
export const COMMS: Record<string, Comm[]> = {
  bloom: [
    { id: 'cm-b1', date: '2026-10-03', channel: 'Slack', from: 'WIA', who: 'Jacqueline', text: 'Shared the autumn gallery preview for a final look.' },
    { id: 'cm-b2', date: '2026-10-05', channel: 'Slack', from: 'Client', who: 'Sarah Mitchell', text: 'Said the gallery looks beautiful and asked when the page is coming.' },
    { id: 'cm-b3', date: '2026-10-07', channel: 'Gmail', from: 'WIA', who: 'Jacqueline', text: 'Said the revised landing page would be with her by Oct 8.', sourceId: 'bloom-task' },
    { id: 'cm-b4', date: '2026-10-08', channel: 'Gmail', from: 'Client', who: 'Sarah Mitchell', text: 'Asked what we know about inquiry quality before Thursday’s call.', sourceId: 'bloom-email' },
  ],
  rosewood: [
    { id: 'cm-r1', date: '2026-10-06', channel: 'Gmail', from: 'Client', who: 'Dana Whitfield', text: 'Reported the tour link showing couples the wrong times again.' },
    { id: 'cm-r2', date: '2026-10-06', channel: 'Gmail', from: 'WIA', who: 'Danielle', text: 'Acknowledged the timezone issue and started looking into it.' },
    { id: 'cm-r3', date: '2026-10-07', channel: 'Slack', from: 'WIA', who: 'Jacqueline', text: 'Confirmed the test inquiry passed and a winter-tour draft is coming.', sourceId: 'rosewood-slack' },
    { id: 'cm-r4', date: '2026-10-08', channel: 'Slack', from: 'Client', who: 'Dana Whitfield', text: 'Thanked the team and asked to see the winter draft on the next call.' },
  ],
  willow: [
    { id: 'cm-w1', date: '2026-10-05', channel: 'Gmail', from: 'Client', who: 'Maya Stone', text: 'Asked for feedback on one creative example so she can get moving.', sourceId: 'willow-email' },
  ],
  everly: [
    { id: 'cm-e1', date: '2026-10-04', channel: 'Gmail', from: 'WIA', who: 'Ivy', text: 'Asked Nina for her remaining spring dates for the page.' },
    { id: 'cm-e2', date: '2026-10-06', channel: 'Gmail', from: 'Client', who: 'Nina Cole', text: 'Said she’ll send the spring dates after checking her calendar.' },
  ],
  harbor: [
    { id: 'cm-h1', date: '2026-10-06', channel: 'Zoom', from: 'Call', who: 'Elise, Whitney', text: 'Messaging & positioning interview.', sourceId: 'harbor-call' },
    { id: 'cm-h2', date: '2026-10-07', channel: 'Gmail', from: 'WIA', who: 'Whitney', text: 'Sent the interview recap and asked about the current CRM.' },
    { id: 'cm-h3', date: '2026-10-08', channel: 'Gmail', from: 'Client', who: 'Elise Bennett', text: 'Asked the kickoff to cover which parts stay with them.', sourceId: 'harbor-email' },
    { id: 'cm-h4', date: '2026-10-08', channel: 'Gmail', from: 'WIA', who: 'Danielle', text: 'Confirmed the kickoff agenda will cover who sets up what.' },
  ],
  magnolia: [
    { id: 'cm-m1', date: '2026-10-06', channel: 'Slack', from: 'Client', who: 'Tessa Ruiz', text: 'Finished her page revision and grouped keywords.', sourceId: 'magnolia-slack' },
    { id: 'cm-m2', date: '2026-10-06', channel: 'Slack', from: 'WIA', who: 'Carmen', text: 'Said she’ll review both at the next office hours.' },
    { id: 'cm-m3', date: '2026-10-07', channel: 'Fathom', from: 'Call', who: 'Tessa, Carmen + 5 members', text: 'Google office hours.' },
  ],
};
