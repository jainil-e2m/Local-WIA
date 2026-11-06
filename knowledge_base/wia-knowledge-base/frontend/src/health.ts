// Fictional health records for the Health & Sentiment scope (kb_tab_scope/04-health-sentiment.md).
// Dimension states are rule-based; the category follows the worst dimension and names its cause (H2).

export type DimId = 'voice' | 'follow' | 'support' | 'onboarding' | 'programme' | 'leads' | 'handling';
export type Level = 'good' | 'middle' | 'worst' | 'na' | 'unavailable';
export type Category = 'Needs attention' | 'Watch' | 'Steady' | 'Settling in' | 'Unassessed';
export interface Driver { text: string; kind: 'Fact' | 'Interpretation'; sourceId?: string; date?: string }
export interface DimState { state: string; level: Level; drivers: Driver[] }
export interface VoiceItem { id: string; clientId: string; type: 'Praise' | 'Concern' | 'Question' | 'Request' | 'Decision'; quote: string; speaker: string; date: string; channel: string; sourceId?: string }
export interface Waiting { clientId: string; from: string; channel: string; date: string; text: string; businessDays: number; sourceId?: string }

export const DIMENSIONS: { id: DimId; label: string; short: string }[] = [
  { id: 'voice', label: 'Client voice', short: 'Voice' },
  { id: 'follow', label: 'Follow-through', short: 'Follow-through' },
  { id: 'support', label: 'Support', short: 'Support' },
  { id: 'onboarding', label: 'Onboarding', short: 'Onboarding' },
  { id: 'programme', label: 'Programme', short: 'Programme' },
  { id: 'leads', label: 'Lead outcomes', short: 'Leads' },
  { id: 'handling', label: 'Lead handling', short: 'Handling' },
];

const na = (why: string): DimState => ({ state: 'Not applicable', level: 'na', drivers: [{ text: why, kind: 'Fact' }] });
const unavailable = (why: string): DimState => ({ state: 'Unavailable', level: 'unavailable', drivers: [{ text: why, kind: 'Fact' }] });

export interface Assessment {
  clientId: string;
  assessedOn: string;
  period: string;
  dims: Record<DimId, DimState>;
  why: string;
  nextStep: string;
  viktor?: { rating: 'Green' | 'Yellow' | 'Red'; date: string; note: string };
  history: Category[]; // last 8 weeks, oldest first
  changed?: { from: Category; date: string; reason: string };
  leadNumbers?: { inquiries: [number, number]; tours: [number, number]; booked: [number, number]; firstResponse: string; uncontacted: number; stalled: number; definitions: string[] };
  coverage: string[];
}

export const ASSESSMENTS: Assessment[] = [
  { clientId: 'bloom', assessedOn: '2026-10-09', period: 'Last 30 days',
    dims: {
      voice: { state: 'Mixed', level: 'middle', drivers: [{ text: 'Sarah asked what we know about inquiry quality and where couples drop off before a tour.', kind: 'Fact', sourceId: 'bloom-email', date: '2026-10-08' }, { text: 'Reads as a worry about lead quality rather than a complaint.', kind: 'Interpretation' }] },
      follow: { state: 'Broken promise', level: 'worst', drivers: [{ text: '“Send the revised landing page for approval” was promised for Oct 8 on the Sep 30 call and hasn’t been sent.', kind: 'Fact', sourceId: 'bloom-call', date: '2026-10-08' }, { text: 'Sarah’s Oct 8 email has had no reply for 1 business day.', kind: 'Fact', sourceId: 'bloom-email' }] },
      support: { state: 'None open', level: 'good', drivers: [{ text: 'No support issues in Gmail or Slack.', kind: 'Fact' }] },
      onboarding: na('Onboarding finished in May.'), programme: na('Not an accelerator client.'),
      leads: na('No LeadLock engagement.'), handling: na('No LeadLock engagement.'),
    },
    why: 'WIA missed the Oct 8 date for the revised landing page that Sarah is waiting to approve, and her question about inquiry quality hasn’t been answered yet. Both come up on today’s 2:00 PM call.',
    nextStep: 'Send the page before the call and open with Sarah’s inquiry-quality question.',
    viktor: { rating: 'Yellow', date: '2026-10-06', note: 'Google leads down 18% vs the prior 30 days' },
    history: ['Steady', 'Steady', 'Steady', 'Steady', 'Watch', 'Steady', 'Steady', 'Needs attention'],
    changed: { from: 'Steady', date: '2026-10-08', reason: 'Promise missed (landing page, Oct 8)' },
    coverage: ['Gmail, Slack, Zoom, ClickUp current', 'No survey responses found'] },
  { clientId: 'rosewood', assessedOn: '2026-10-09', period: 'Last 30 days',
    dims: {
      voice: { state: 'Positive', level: 'good', drivers: [{ text: 'Dana: “This sounds much more like us now. I am happy to approve the revised follow-up sequence.”', kind: 'Fact', sourceId: 'rosewood-call', date: '2026-10-02' }] },
      follow: { state: 'On track', level: 'good', drivers: [{ text: 'No overdue WIA items; the winter-tour draft is due Oct 12.', kind: 'Fact' }] },
      support: { state: 'Repeat issue', level: 'worst', drivers: [{ text: 'Tour-booking link opens in the wrong timezone, reported a 2nd time in 30 days (Oct 6). Still open.', kind: 'Fact', date: '2026-10-06' }] },
      onboarding: na('Onboarding finished in March.'), programme: na('Not an accelerator client.'),
      leads: { state: 'Steady', level: 'good', drivers: [{ text: 'Inquiries 38 (prior 41); tours booked 14 (prior 12); bookings 4 (prior 3).', kind: 'Fact' }] },
      handling: { state: 'Gaps', level: 'middle', drivers: [{ text: '3 inquiries had no contact within 48 hours.', kind: 'Fact' }, { text: 'Two arrived on a Saturday; may be a weekend coverage gap.', kind: 'Interpretation' }] },
    },
    why: 'Dana is happy with the new follow-up sequence, but the tour-booking timezone bug has now come back twice in a month. Lead results are steady; a few weekend inquiries went uncontacted.',
    nextStep: 'Ask Danielle to confirm the timezone fix before the Oct 12 call, and mention the weekend gap.',
    viktor: { rating: 'Green', date: '2026-10-06', note: 'Meta cost per lead stable' },
    history: ['Steady', 'Steady', 'Watch', 'Steady', 'Steady', 'Steady', 'Watch', 'Needs attention'],
    changed: { from: 'Watch', date: '2026-10-06', reason: 'Support issue repeated (tour-link timezone)' },
    leadNumbers: { inquiries: [38, 41], tours: [14, 12], booked: [4, 3], firstResponse: '11 min', uncontacted: 3, stalled: 2, definitions: ['Inquiry = new opportunity in the “Inquiries” pipeline', 'Tour = appointment booked on the Tour calendar', 'Booked = opportunity moved to “Contract signed”', 'Period: rolling 30 days, America/New_York', 'Excludes test contacts and duplicates'] },
    coverage: ['LeadLock read as if access were granted (H6 pending)', 'LeadLock support inbox not connected'] },
  { clientId: 'willow', assessedOn: '2026-10-09', period: 'Last 30 days',
    dims: {
      voice: { state: 'Mixed', level: 'middle', drivers: [{ text: 'Maya: “I have been a bit stretched these past two weeks… I am stuck on which one to start with.”', kind: 'Fact', sourceId: 'willow-email', date: '2026-10-05' }, { text: 'Asking for help, not unhappy with WIA.', kind: 'Interpretation' }] },
      follow: { state: 'Broken promise', level: 'worst', drivers: [{ text: 'Maya’s Oct 5 email asking for feedback has had no reply for 4 business days.', kind: 'Fact', sourceId: 'willow-email' }, { text: 'The check-in Gisselle owns (due Oct 8) hasn’t been acknowledged.', kind: 'Fact' }] },
      support: na('Accelerator clients run their own accounts.'), onboarding: na('Programme started in July.'),
      programme: { state: 'Drifting', level: 'middle', drivers: [{ text: 'Missed Oct 1 office hours; Oct 8 is unknown (sheet note conflicts with the counter).', kind: 'Fact', date: '2026-10-08' }] },
      leads: na('No LeadLock engagement.'), handling: na('No LeadLock engagement.'),
    },
    why: 'Maya asked for help choosing a creative four business days ago and hasn’t heard back, while she has also drifted from office hours. She sounds stretched rather than unhappy.',
    nextStep: 'Reply to Maya today with one example to start from, and confirm the Oct 13 check-in.',
    history: ['Steady', 'Steady', 'Steady', 'Watch', 'Watch', 'Watch', 'Watch', 'Needs attention'],
    changed: { from: 'Watch', date: '2026-10-08', reason: 'Client waiting on us 3+ business days' },
    coverage: ['Shared programme channel: only Maya’s messages counted', 'Attendance from the programme sheet'] },
  { clientId: 'everly', assessedOn: '2026-10-09', period: 'Last 30 days',
    dims: {
      voice: { state: 'Positive', level: 'good', drivers: [{ text: 'Nina: “The portfolio edit feels right.” Renewal signed Oct 6.', kind: 'Fact', sourceId: 'everly-call', date: '2026-10-01' }] },
      follow: { state: 'On track', level: 'good', drivers: [{ text: 'Spring-dates page in progress, due Oct 13.', kind: 'Fact' }] },
      support: { state: 'Open', level: 'middle', drivers: [{ text: 'Contact form sending some inquiries to spam, reported by Nina in Slack on Oct 7. Ivy is looking at it.', kind: 'Fact', date: '2026-10-07' }] },
      onboarding: na('Onboarding finished in June.'), programme: na('Not an accelerator client.'),
      leads: na('No LeadLock engagement.'), handling: na('No LeadLock engagement.'),
    },
    why: 'Nina approved the portfolio edit, renewed, and the page work is on schedule. One open issue: some contact-form inquiries are landing in spam.',
    nextStep: 'Confirm the spam-filter fix with Ivy; ask Nina for the spring-date list.',
    viktor: { rating: 'Green', date: '2026-10-06', note: 'Inquiries up on Meta' },
    history: ['Settling in', 'Steady', 'Steady', 'Steady', 'Steady', 'Steady', 'Steady', 'Watch'],
    coverage: ['Gmail, Slack, Zoom, ClickUp current'] },
  { clientId: 'harbor', assessedOn: '2026-10-09', period: 'Since onboarding (Sep 21)',
    dims: {
      voice: { state: 'Positive', level: 'good', drivers: [{ text: 'Elise: “We are excited to get the new process going.”', kind: 'Fact', sourceId: 'harbor-email', date: '2026-10-08' }] },
      follow: { state: 'On track', level: 'good', drivers: [{ text: 'Kickoff handoff is blocked on the client, not on WIA.', kind: 'Fact' }] },
      support: { state: 'Open', level: 'middle', drivers: [{ text: 'DNS records incomplete; LeadLock login waiting on Elise to accept an invite.', kind: 'Fact', date: '2026-10-08' }] },
      onboarding: { state: 'Waiting on client', level: 'middle', drivers: [{ text: 'CRM and access-owner confirmation outstanding since Oct 6.', kind: 'Fact', sourceId: 'harbor-call' }] },
      programme: na('Not an accelerator client.'),
      leads: unavailable('LeadLock location linked; lead reads not yet authorised (H6).'),
      handling: unavailable('LeadLock location linked; lead reads not yet authorised (H6).'),
    },
    why: 'Onboarding is in week 3 and moving, with the CRM confirmation waiting on Elise. She sounds positive. Two setup issues are open.',
    nextStep: 'Agree the CRM handoff on today’s kickoff call.',
    history: ['Unassessed', 'Unassessed', 'Unassessed', 'Unassessed', 'Unassessed', 'Settling in', 'Settling in', 'Settling in'],
    coverage: ['Client for 3 weeks', 'LeadLock outcomes unavailable'] },
  { clientId: 'magnolia', assessedOn: '2026-10-09', period: 'Last 30 days',
    dims: {
      voice: { state: 'Positive', level: 'good', drivers: [{ text: 'Tessa: “Looking forward to feedback on whether the intent matches the page.”', kind: 'Fact', sourceId: 'magnolia-slack', date: '2026-10-06' }] },
      follow: { state: 'On track', level: 'good', drivers: [{ text: 'Keyword review planned for Oct 14 office hours.', kind: 'Fact' }] },
      support: na('Accelerator clients run their own accounts.'), onboarding: na('Programme started in June.'),
      programme: { state: 'Engaged', level: 'good', drivers: [{ text: 'Attended the last 3 office hours (sheet).', kind: 'Fact' }] },
      leads: na('No LeadLock engagement.'), handling: na('No LeadLock engagement.'),
    },
    why: 'Tessa is attending, finished her page revision and is asking for feedback. On track.',
    nextStep: 'Review her keyword groups at Oct 14 office hours.',
    history: ['Steady', 'Steady', 'Steady', 'Steady', 'Steady', 'Steady', 'Steady', 'Steady'],
    coverage: ['Shared programme channel: only Tessa’s messages counted'] },
];

export function categoryOf(a: Assessment, onboarding: boolean): { category: Category; causes: string[] } {
  const entries = DIMENSIONS.filter(d => d.id !== 'leads' && d.id !== 'handling').map(d => ({ d, s: a.dims[d.id] }));
  const worst = entries.filter(e => e.s.level === 'worst');
  const middle = entries.filter(e => e.s.level === 'middle');
  const assessed = entries.filter(e => e.s.level === 'good' || e.s.level === 'middle' || e.s.level === 'worst');
  if (worst.length) return { category: 'Needs attention', causes: worst.map(e => `${e.d.label}: ${e.s.state.toLowerCase()}`) };
  if (onboarding) return { category: 'Settling in', causes: ['In onboarding', ...middle.map(e => `${e.d.label}: ${e.s.state.toLowerCase()}`)] };
  if (assessed.length < 2) return { category: 'Unassessed', causes: ['Not enough coverage to judge'] };
  if (middle.length) return { category: 'Watch', causes: middle.map(e => `${e.d.label}: ${e.s.state.toLowerCase()}`) };
  return { category: 'Steady', causes: ['All assessed dimensions fine'] };
}

export const VOICE: VoiceItem[] = [
  { id: 'v1', clientId: 'bloom', type: 'Question', quote: 'Could we talk through what we know about the inquiries coming in? I want to understand which couples are a good fit, and where they are dropping off before booking a tour.', speaker: 'Sarah Mitchell', date: '2026-10-08', channel: 'Gmail', sourceId: 'bloom-email' },
  { id: 'v2', clientId: 'bloom', type: 'Praise', quote: 'The gallery looks beautiful.', speaker: 'Sarah Mitchell', date: '2026-10-08', channel: 'Gmail', sourceId: 'bloom-email' },
  { id: 'v3', clientId: 'bloom', type: 'Decision', quote: 'I would rather get the revised page signed off before we change any of the campaign messaging.', speaker: 'Sarah Mitchell', date: '2026-09-30', channel: 'Zoom', sourceId: 'bloom-call' },
  { id: 'v4', clientId: 'rosewood', type: 'Praise', quote: 'This sounds much more like us now. I am happy to approve the revised follow-up sequence.', speaker: 'Dana Whitfield', date: '2026-10-02', channel: 'Zoom', sourceId: 'rosewood-call' },
  { id: 'v5', clientId: 'rosewood', type: 'Concern', quote: 'The tour link is showing couples the wrong times again. Can someone look at this before the weekend?', speaker: 'Dana Whitfield', date: '2026-10-06', channel: 'Slack' },
  { id: 'v6', clientId: 'willow', type: 'Request', quote: 'Could someone give me feedback on one example so I can get moving again?', speaker: 'Maya Stone', date: '2026-10-05', channel: 'Gmail', sourceId: 'willow-email' },
  { id: 'v7', clientId: 'willow', type: 'Concern', quote: 'I have been a bit stretched these past two weeks and missed the sessions.', speaker: 'Maya Stone', date: '2026-10-05', channel: 'Gmail', sourceId: 'willow-email' },
  { id: 'v8', clientId: 'everly', type: 'Praise', quote: 'The portfolio edit feels right.', speaker: 'Nina Cole', date: '2026-10-01', channel: 'Zoom', sourceId: 'everly-call' },
  { id: 'v9', clientId: 'everly', type: 'Request', quote: 'The main thing I need next is to make it clear that we have a few spring dates open.', speaker: 'Nina Cole', date: '2026-10-01', channel: 'Zoom', sourceId: 'everly-call' },
  { id: 'v10', clientId: 'harbor', type: 'Praise', quote: 'We are excited to get the new process going.', speaker: 'Elise Bennett', date: '2026-10-08', channel: 'Gmail', sourceId: 'harbor-email' },
  { id: 'v11', clientId: 'harbor', type: 'Question', quote: 'Could the kickoff cover which parts stay with us and which parts your team will set up?', speaker: 'Elise Bennett', date: '2026-10-08', channel: 'Gmail', sourceId: 'harbor-email' },
  { id: 'v12', clientId: 'magnolia', type: 'Request', quote: 'Looking forward to feedback on whether the intent matches the page.', speaker: 'Tessa Ruiz', date: '2026-10-06', channel: 'Slack', sourceId: 'magnolia-slack' },
];

export const WAITING: Waiting[] = [
  { clientId: 'willow', from: 'Maya Stone', channel: 'Gmail', date: '2026-10-05', text: 'Could someone give me feedback on one example so I can get moving again?', businessDays: 4, sourceId: 'willow-email' },
  { clientId: 'bloom', from: 'Sarah Mitchell', channel: 'Gmail', date: '2026-10-08', text: 'Could we talk through what we know about the inquiries coming in?', businessDays: 1, sourceId: 'bloom-email' },
];

export const assessmentFor = (id: string) => ASSESSMENTS.find(a => a.clientId === id)!;
