// Health & Sentiment v3: production metric model.
// Nothing on the v3 page is authored as a result. The page reads four kinds of raw record (the same shape
// the ingestion pipeline stores) and computes every figure with `snapshot(clientId, asOf)`. History is the same
// function run at earlier dates, so any number can be reproduced from the records and the CONFIG below.
//
//   Message     Gmail / Slack / Fathom / Zoom   a client-authored message; the LLM scores tone + theme
//   Thread      Gmail / Slack                   a client-started conversation and our first reply
//   Commitment  Action Hub (ClickUp)       something WIA promised the client, with a due date
//   Issue       Support inbox / Slack           a client-reported problem, with reopen history
import { CLIENTS, addDays, dateLabel, daysBetween } from './data';
import { RECORDS } from './records';
import { THEMES, type Feel, type Theme, type Zone } from './health-v2';

export { THEMES, type Feel, type Theme, type Zone };

/** Evaluation date for the demo. In production: the nightly run's date. */
export const AS_OF = '2026-10-09';

// ---- Configuration: every threshold the page uses, in one place -------------------------------------
export const CONFIG = {
  windowDays: 28,          // rolling window for tone, reply time and on-time rate
  halfLifeDays: 14,        // a message 14 days old counts half as much as one from today
  minScored: 2,            // fewer high-confidence scored messages than this = "Not enough to read"
  feelCuts: [-1, 0, 1],    // score < -1 Frustrated · < 0 Uneasy · < 1 Satisfied · else Delighted
  replyTargetHours: 4,     // first reply within 4 business hours (Mon–Fri, 9:00–18:00 ET)
  waitAtRisk: 1, waitBehind: 2, waitBroken: 4,  // business days a client message has waited on us
  lateBrokenDays: 5,       // a promise more than 5 business days late is Broken
  overdueBrokenCount: 3,   // or 3+ promises late at once
  dueSoonDays: 2,          // open promise due within 2 business days = At risk
  issueSlaDays: 5,         // support issue open longer than this = Behind
  repeatWindowDays: 30,    // reopened within 30 days and still open = Broken
  quietRatio: 0.5,         // messages in the window under half their usual = Quieter than usual
  baselineDays: 84,        // "usual" = average 28-day volume over the previous 84 days
  settlingDays: 60,        // clients newer than this are tracked but not placed on the map
  onTimeTarget: 0.9,       // promises kept on time, team target
};

// ---- Records -----------------------------------------------------------------------------------------
export type Channel = 'Gmail' | 'Slack' | 'Fathom' | 'Zoom';
/** Tone the LLM gave one message: -2 very negative … +2 very positive. null = routine (logistics, no tone). */
export type ToneScore = -2 | -1 | 0 | 1 | 2;
export interface Message { id: string; clientId: string; at: string; channel: Channel; speaker: string; tone: ToneScore | null; confidence: 'High' | 'Low'; theme?: Theme; quote?: string; sourceId?: string }
export interface Thread { id: string; clientId: string; at: string; channel: 'Gmail' | 'Slack'; from: string; text: string; repliedAt?: string; repliedBy?: string; sourceId?: string }
export interface Commitment { id: string; clientId: string; title: string; owner: string; madeOn: string; due: string; doneOn?: string; source: 'Call' | 'Email' | 'Slack' | 'ClickUp'; sourceId?: string }
export interface Issue { id: string; clientId: string; title: string; owner: string; openedOn: string; resolvedOn?: string; reopenedOn?: string[] }

const m = (clientId: string, at: string, channel: Channel, speaker: string, tone: ToneScore, theme: Theme, quote: string, confidence: 'High' | 'Low' = 'High', sourceId?: string): Message =>
  ({ id: `${clientId}-${at}-${theme}`, clientId, at, channel, speaker, tone, confidence, theme, quote, sourceId });

/** Messages the tone model scored (sample). */
const SCORED: Message[] = [
  m('bloom', '2026-08-06T11:00', 'Gmail', 'Sarah Mitchell', 1, 'Pages & creative', 'Love the autumn dates in the ads, thank you.'),
  m('bloom', '2026-08-20T15:10', 'Zoom', 'Sarah Mitchell', 1, 'Strategy & planning', 'Thank you for walking us through the new campaign plan, that was really clear.'),
  m('bloom', '2026-09-03T11:05', 'Gmail', 'Sarah Mitchell', 1, 'Pages & creative', 'The draft ad copy reads well, a couple of small tweaks only.'),
  m('bloom', '2026-09-11T16:40', 'Gmail', 'Sarah Mitchell', 0, 'Communication', 'We are fine with that, just keep us posted.', 'Low'),
  m('bloom', '2026-09-18T10:20', 'Gmail', 'Sarah Mitchell', 0, 'Communication', 'Got it, thanks for the update on timing.'),
  m('bloom', '2026-09-30T14:30', 'Zoom', 'Sarah Mitchell', 1, 'Pages & creative', 'I would rather get the revised page signed off before we change any of the campaign messaging.', 'High', 'bloom-call'),
  m('bloom', '2026-10-08T10:24', 'Gmail', 'Sarah Mitchell', 1, 'Pages & creative', 'The gallery looks beautiful.', 'High', 'bloom-email'),
  m('bloom', '2026-10-08T10:25', 'Gmail', 'Sarah Mitchell', -1, 'Lead quality', 'Could we talk through what we know about the inquiries coming in? I want to understand where couples are dropping off.', 'High', 'bloom-email'),

  m('rosewood', '2026-08-13T10:00', 'Slack', 'Dana Whitfield', 1, 'Strategy & planning', 'The monthly plan is clear, thanks Jacqueline.'),
  m('rosewood', '2026-08-19T14:00', 'Zoom', 'Dana Whitfield', 0, 'Strategy & planning', 'Let us keep the same budget split for September.'),
  m('rosewood', '2026-08-27T12:50', 'Slack', 'Dana Whitfield', 0, 'Tech & tracking', 'The tour link seems to show the wrong times for some couples.'),
  m('rosewood', '2026-09-04T09:30', 'Slack', 'Dana Whitfield', 1, 'Tech & tracking', 'Thanks for fixing the link so quickly.'),
  m('rosewood', '2026-09-25T13:15', 'Slack', 'Dana Whitfield', 2, 'Pages & creative', 'The new photos are exactly the feel we wanted.'),
  m('rosewood', '2026-10-02T15:00', 'Zoom', 'Dana Whitfield', 2, 'Pages & creative', 'This sounds much more like us now. I am happy to approve the revised follow-up sequence.', 'High', 'rosewood-call'),
  m('rosewood', '2026-10-06T16:20', 'Slack', 'Dana Whitfield', -1, 'Tech & tracking', 'The tour link is showing couples the wrong times again. Can someone look at this before the weekend?'),
  m('rosewood', '2026-10-07T11:00', 'Slack', 'Dana Whitfield', -1, 'Tech & tracking', 'Two couples emailed us confused about their tour time this morning.'),

  m('willow', '2026-08-21T10:00', 'Slack', 'Maya Stone', 1, 'Pages & creative', 'Excited to try the new creative angles this month!'),
  m('willow', '2026-09-02T13:00', 'Slack', 'Maya Stone', 1, 'Programme & sessions', 'Today’s session was really useful, thank you.'),
  m('willow', '2026-09-17T12:00', 'Slack', 'Maya Stone', 0, 'Programme & sessions', 'I will catch the recording if I miss it.', 'Low'),
  m('willow', '2026-09-19T15:00', 'Slack', 'Maya Stone', -1, 'Programme & sessions', 'I am finding it hard to keep up with the weekly tasks.'),
  m('willow', '2026-09-29T09:00', 'Gmail', 'Maya Stone', 0, 'Programme & sessions', 'Can we move my check-in to next week?'),
  m('willow', '2026-10-05T08:40', 'Gmail', 'Maya Stone', -1, 'Programme & sessions', 'I have been a bit stretched these past two weeks and missed the sessions.', 'High', 'willow-email'),
  m('willow', '2026-10-05T08:41', 'Gmail', 'Maya Stone', 0, 'Communication', 'Could someone give me feedback on one example so I can get moving again?', 'High', 'willow-email'),

  m('everly', '2026-08-12T15:00', 'Slack', 'Nina Cole', 1, 'Pages & creative', 'The new reel order works much better.'),
  m('everly', '2026-08-19T11:00', 'Zoom', 'Nina Cole', 0, 'Strategy & planning', 'Let us hold the fall dates until I confirm my calendar.'),
  m('everly', '2026-09-04T11:00', 'Slack', 'Nina Cole', 1, 'Pages & creative', 'Happy with how the reels are landing.'),
  m('everly', '2026-09-22T10:00', 'Slack', 'Nina Cole', 1, 'Pages & creative', 'Loved the first cut of the portfolio page.'),
  m('everly', '2026-10-01T14:00', 'Zoom', 'Nina Cole', 2, 'Pages & creative', 'The portfolio edit feels right.', 'High', 'everly-call'),
  m('everly', '2026-10-07T14:00', 'Slack', 'Nina Cole', 0, 'Tech & tracking', 'Some inquiries seem to be going to spam, can you check?'),

  m('magnolia', '2026-08-11T10:00', 'Slack', 'Tessa Ruiz', 1, 'Programme & sessions', 'Great first office hours, lots to work on.'),
  m('magnolia', '2026-08-18T13:00', 'Slack', 'Tessa Ruiz', 0, 'Strategy & planning', 'Working through the search terms list now.'),
  m('magnolia', '2026-08-25T10:00', 'Slack', 'Tessa Ruiz', 1, 'Programme & sessions', 'The intent worksheet finally made it click for me.'),
  m('magnolia', '2026-09-15T10:00', 'Slack', 'Tessa Ruiz', -1, 'Lead quality', 'I am not sure the keywords match what we actually offer.'),
  m('magnolia', '2026-09-22T09:00', 'Slack', 'Tessa Ruiz', -1, 'Communication', 'Still waiting to hear back on the page review.'),
  m('magnolia', '2026-09-29T11:00', 'Slack', 'Tessa Ruiz', 0, 'Pages & creative', 'Uploaded the revised page, let me know.'),
  m('magnolia', '2026-10-06T10:30', 'Slack', 'Tessa Ruiz', 1, 'Pages & creative', 'Looking forward to feedback on whether the intent matches the page.', 'High', 'magnolia-slack'),
  m('magnolia', '2026-10-08T16:00', 'Slack', 'Tessa Ruiz', 1, 'Programme & sessions', 'Office hours really helped this week.'),

  m('harbor', '2026-09-24T12:00', 'Gmail', 'Elise Bennett', 1, 'Strategy & planning', 'Thanks for the kickoff pack, very thorough.'),
  m('harbor', '2026-10-08T09:30', 'Gmail', 'Elise Bennett', 2, 'Strategy & planning', 'We are excited to get the new process going.', 'High', 'harbor-email'),
];

/** Routine messages (logistics, no tone). Sample volume per week for the 13 weeks to AS_OF, oldest first;
 *  the four weeks before repeat the first value so the 84-day "usual" baseline is complete. */
const ROUTINE_RATE: Record<string, number[]> = {
  bloom: [3, 3, 4, 3, 3, 4, 3, 3, 3, 4, 3, 3, 3],
  rosewood: [4, 4, 3, 4, 4, 3, 4, 4, 3, 4, 4, 4, 5],
  willow: [4, 4, 3, 4, 3, 3, 3, 3, 2, 1, 1, 1, 0],
  everly: [3, 3, 3, 3, 4, 3, 3, 3, 3, 3, 4, 3, 3],
  magnolia: [3, 3, 2, 3, 3, 3, 3, 3, 3, 3, 3, 4, 4],
  harbor: [0, 0, 0, 0, 0, 0, 0, 0, 2, 3, 3, 4, 4],
};
const ROUTINE: Message[] = Object.entries(ROUTINE_RATE).flatMap(([clientId, base]) => [...Array(4).fill(base[0]), ...base].flatMap((n: number, w, rates) =>
  Array.from({ length: n }, (_, k) => {
    const day = addDays(AS_OF, -(rates.length - 1 - w) * 7 - 4 + k); // Mon…Fri of that week
    return { id: `${clientId}-r-${w}-${k}`, clientId, at: `${day}T${10 + k}:00`, channel: (k % 2 ? 'Slack' : 'Gmail') as Channel, speaker: CLIENTS.find(c => c.id === clientId)?.contact || '', tone: null, confidence: 'High' as const };
  })));
export const MESSAGES: Message[] = [...SCORED, ...ROUTINE];

export const THREADS: Thread[] = [
  { id: 'bt1', clientId: 'bloom', at: '2026-08-05T14:00', channel: 'Gmail', from: 'Sarah Mitchell', text: 'Can we add the autumn dates to the ads?', repliedAt: '2026-08-05T15:30', repliedBy: 'Jacqueline' },
  { id: 'bt2', clientId: 'bloom', at: '2026-09-03T11:05', channel: 'Gmail', from: 'Sarah Mitchell', text: 'A couple of small tweaks to the ad copy.', repliedAt: '2026-09-03T16:00', repliedBy: 'Jacqueline' },
  { id: 'bt3', clientId: 'bloom', at: '2026-09-18T10:20', channel: 'Gmail', from: 'Sarah Mitchell', text: 'When will the new page be ready?', repliedAt: '2026-09-18T12:30', repliedBy: 'Jacqueline' },
  { id: 'bt4', clientId: 'bloom', at: '2026-10-08T10:24', channel: 'Gmail', from: 'Sarah Mitchell', text: 'Could we talk through what we know about the inquiries coming in?', sourceId: 'bloom-email' },
  { id: 'rt1', clientId: 'rosewood', at: '2026-08-27T12:50', channel: 'Slack', from: 'Dana Whitfield', text: 'The tour link seems to show the wrong times.', repliedAt: '2026-08-27T15:00', repliedBy: 'Danielle' },
  { id: 'rt2', clientId: 'rosewood', at: '2026-09-18T10:00', channel: 'Slack', from: 'Dana Whitfield', text: 'Couples got the follow-up text twice.', repliedAt: '2026-09-18T10:40', repliedBy: 'Danielle' },
  { id: 'rt3', clientId: 'rosewood', at: '2026-10-06T16:20', channel: 'Slack', from: 'Dana Whitfield', text: 'The tour link is showing the wrong times again.', repliedAt: '2026-10-07T09:30', repliedBy: 'Danielle' },
  { id: 'rt4', clientId: 'rosewood', at: '2026-10-07T11:00', channel: 'Slack', from: 'Dana Whitfield', text: 'Two couples emailed us confused about their tour time.', repliedAt: '2026-10-07T15:00', repliedBy: 'Danielle' },
  { id: 'wt1', clientId: 'willow', at: '2026-08-21T10:00', channel: 'Slack', from: 'Maya Stone', text: 'Which angle should I start with?', repliedAt: '2026-08-21T12:00', repliedBy: 'Jacqueline' },
  { id: 'wt2', clientId: 'willow', at: '2026-09-02T13:00', channel: 'Slack', from: 'Maya Stone', text: 'Can I get the session slides?', repliedAt: '2026-09-03T10:00', repliedBy: 'Jacqueline' },
  { id: 'wt3', clientId: 'willow', at: '2026-09-19T15:00', channel: 'Slack', from: 'Maya Stone', text: 'Finding it hard to keep up with the weekly tasks.', repliedAt: '2026-09-22T10:00', repliedBy: 'Jacqueline' },
  { id: 'wt4', clientId: 'willow', at: '2026-09-29T09:00', channel: 'Gmail', from: 'Maya Stone', text: 'Can we move my check-in to next week?', repliedAt: '2026-09-30T17:00', repliedBy: 'Gisselle' },
  { id: 'wt5', clientId: 'willow', at: '2026-10-05T08:40', channel: 'Gmail', from: 'Maya Stone', text: 'Could someone give me feedback on one example so I can get moving again?', sourceId: 'willow-email' },
  { id: 'et1', clientId: 'everly', at: '2026-09-04T11:00', channel: 'Slack', from: 'Nina Cole', text: 'Can we swap the second reel?', repliedAt: '2026-09-04T12:00', repliedBy: 'Ivy' },
  { id: 'et2', clientId: 'everly', at: '2026-09-22T10:00', channel: 'Slack', from: 'Nina Cole', text: 'Notes on the portfolio first cut.', repliedAt: '2026-09-22T13:00', repliedBy: 'Ivy' },
  { id: 'et3', clientId: 'everly', at: '2026-10-07T14:00', channel: 'Slack', from: 'Nina Cole', text: 'Some inquiries seem to be going to spam.', repliedAt: '2026-10-07T15:10', repliedBy: 'Ivy' },
  { id: 'mt1', clientId: 'magnolia', at: '2026-09-15T10:00', channel: 'Slack', from: 'Tessa Ruiz', text: 'Not sure the keywords match what we offer.', repliedAt: '2026-09-16T11:00', repliedBy: 'Jacqueline' },
  { id: 'mt2', clientId: 'magnolia', at: '2026-09-22T09:00', channel: 'Slack', from: 'Tessa Ruiz', text: 'Still waiting to hear back on the page review.', repliedAt: '2026-10-02T10:00', repliedBy: 'Jacqueline' },
  { id: 'mt3', clientId: 'magnolia', at: '2026-10-06T10:30', channel: 'Slack', from: 'Tessa Ruiz', text: 'Does the intent match the page?', repliedAt: '2026-10-06T12:30', repliedBy: 'Jacqueline' },
  { id: 'ht1', clientId: 'harbor', at: '2026-09-24T12:00', channel: 'Gmail', from: 'Elise Bennett', text: 'Questions on the kickoff pack.', repliedAt: '2026-09-24T14:00', repliedBy: 'Danielle' },
  { id: 'ht2', clientId: 'harbor', at: '2026-10-07T10:00', channel: 'Gmail', from: 'Elise Bennett', text: 'I can’t log in to the LeadLock app.', repliedAt: '2026-10-07T11:00', repliedBy: 'Danielle' },
  { id: 'ht3', clientId: 'harbor', at: '2026-10-08T09:30', channel: 'Gmail', from: 'Elise Bennett', text: 'Which CRM fields do you need from us?', repliedAt: '2026-10-08T12:30', repliedBy: 'Danielle' },
];

export const COMMITMENTS: Commitment[] = [
  { id: 'bc1', clientId: 'bloom', title: 'Send campaign plan recap', owner: 'Jacqueline', madeOn: '2026-08-20', due: '2026-08-24', doneOn: '2026-08-21', source: 'Call' },
  { id: 'bc2', clientId: 'bloom', title: 'Send new ad copy', owner: 'Jacqueline', madeOn: '2026-08-28', due: '2026-09-09', doneOn: '2026-09-11', source: 'Email' },
  { id: 'bc3', clientId: 'bloom', title: 'Share September report', owner: 'Jacqueline', madeOn: '2026-09-01', due: '2026-09-15', doneOn: '2026-09-15', source: 'ClickUp' },
  { id: 'bc4', clientId: 'bloom', title: 'Send the revised landing page for approval', owner: 'Jacqueline', madeOn: '2026-09-30', due: '2026-10-08', source: 'Call', sourceId: 'bloom-call' },
  { id: 'rc1', clientId: 'rosewood', title: 'Fix the tour-link timezone', owner: 'Danielle', madeOn: '2026-08-27', due: '2026-09-03', doneOn: '2026-09-03', source: 'Slack' },
  { id: 'rc2', clientId: 'rosewood', title: 'Revise the follow-up sequence', owner: 'Jacqueline', madeOn: '2026-09-18', due: '2026-10-02', doneOn: '2026-10-02', source: 'Call' },
  { id: 'rc3', clientId: 'rosewood', title: 'Confirm the timezone fix with Dana', owner: 'Danielle', madeOn: '2026-10-07', due: '2026-10-09', source: 'Slack' },
  { id: 'rc4', clientId: 'rosewood', title: 'Draft the winter-tour messaging', owner: 'Jacqueline', madeOn: '2026-10-02', due: '2026-10-12', source: 'Call', sourceId: 'rosewood-call' },
  { id: 'wc1', clientId: 'willow', title: 'Feedback on the first creative', owner: 'Jacqueline', madeOn: '2026-09-02', due: '2026-09-05', doneOn: '2026-09-05', source: 'Slack' },
  { id: 'wc2', clientId: 'willow', title: 'Send the office-hours recap', owner: 'Gisselle', madeOn: '2026-09-24', due: '2026-09-30', doneOn: '2026-10-01', source: 'ClickUp' },
  { id: 'wc3', clientId: 'willow', title: 'Check-in call with Maya', owner: 'Gisselle', madeOn: '2026-10-01', due: '2026-10-08', source: 'ClickUp' },
  { id: 'ec1', clientId: 'everly', title: 'Deliver the reels batch', owner: 'Ivy', madeOn: '2026-08-27', due: '2026-09-10', doneOn: '2026-09-10', source: 'Call' },
  { id: 'ec2', clientId: 'everly', title: 'Portfolio page edit', owner: 'Ivy', madeOn: '2026-09-22', due: '2026-10-01', doneOn: '2026-09-30', source: 'Slack' },
  { id: 'ec3', clientId: 'everly', title: 'Send renewal paperwork', owner: 'Ivy', madeOn: '2026-09-29', due: '2026-10-06', doneOn: '2026-10-06', source: 'Email' },
  { id: 'ec4', clientId: 'everly', title: 'Check inquiry spam filtering', owner: 'Ivy', madeOn: '2026-10-07', due: '2026-10-14', source: 'Slack' },
  { id: 'mc1', clientId: 'magnolia', title: 'Review the intent worksheet', owner: 'Jacqueline', madeOn: '2026-08-20', due: '2026-08-28', doneOn: '2026-08-27', source: 'Slack' },
  { id: 'mc2', clientId: 'magnolia', title: 'Feedback on the landing-page draft', owner: 'Jacqueline', madeOn: '2026-09-15', due: '2026-09-24', doneOn: '2026-10-02', source: 'Slack' },
  { id: 'mc3', clientId: 'magnolia', title: 'Review the keyword groups against the page', owner: 'Jacqueline', madeOn: '2026-10-06', due: '2026-10-14', source: 'Slack', sourceId: 'magnolia-slack' },
  { id: 'hc1', clientId: 'harbor', title: 'Send the kickoff pack', owner: 'Danielle', madeOn: '2026-09-21', due: '2026-09-24', doneOn: '2026-09-23', source: 'Email' },
  { id: 'hc2', clientId: 'harbor', title: 'Complete the domain DNS setup', owner: 'Danielle', madeOn: '2026-09-28', due: '2026-10-08', doneOn: '2026-10-07', source: 'ClickUp' },
  { id: 'hc3', clientId: 'harbor', title: 'CRM handoff call', owner: 'Danielle', madeOn: '2026-10-08', due: '2026-10-12', source: 'Email', sourceId: 'harbor-email' },
];

export const ISSUES: Issue[] = [
  { id: 'ri1', clientId: 'rosewood', title: 'Tour-booking link opens in the wrong timezone', owner: 'Danielle', openedOn: '2026-08-27', resolvedOn: '2026-09-03', reopenedOn: ['2026-10-06'] },
  { id: 'ri2', clientId: 'rosewood', title: 'Follow-up sequence sent duplicate texts', owner: 'Danielle', openedOn: '2026-09-18', resolvedOn: '2026-09-19' },
  { id: 'ei1', clientId: 'everly', title: 'Inquiries landing in spam', owner: 'Ivy', openedOn: '2026-10-07' },
  { id: 'hi1', clientId: 'harbor', title: 'Can’t log in to the LeadLock app', owner: 'Danielle', openedOn: '2026-10-07' },
];

// ---- Time helpers ------------------------------------------------------------------------------------
const day = (s: string) => s.slice(0, 10);
const ms = (s: string) => new Date(`${s.length === 10 ? `${s}T23:59` : s}:00Z`).getTime();
const isWeekday = (d: string) => { const w = new Date(`${d}T12:00:00Z`).getUTCDay(); return w !== 0 && w !== 6; };
/** Weekdays after `from` up to and including `to`. Oct 8 → Oct 9 = 1. */
export const businessDays = (from: string, to: string) => { let n = 0; for (let d = addDays(from, 1); d <= to; d = addDays(d, 1)) if (isWeekday(d)) n++; return n; };
/** Hours between two timestamps that fall Mon–Fri, 9:00–18:00. */
export function businessHours(a: string, b: string) {
  const start = ms(a), end = ms(b); let h = 0;
  for (let d = day(a); ms(d) - 86399000 < end; d = addDays(d, 1)) {
    if (!isWeekday(d)) continue;
    const open = ms(`${d}T09:00`), close = ms(`${d}T18:00`);
    const s = Math.max(open, start), e = Math.min(close, end);
    if (e > s) h += (e - s) / 3600000;
  }
  return h;
}
const inWindow = (d: string, asOf: string, days = CONFIG.windowDays) => d > addDays(asOf, -days) && d <= asOf;
const median = (xs: number[]) => { if (!xs.length) return null; const s = [...xs].sort((a, b) => a - b); const h = s.length >> 1; return s.length % 2 ? s[h] : (s[h - 1] + s[h]) / 2; };

// ---- Metric definitions (shown on the page, so the numbers can be checked) --------------------------
export type MetricId = 'tone' | 'negShare' | 'toneChange' | 'volume' | 'lastHeard' | 'waiting' | 'reply' | 'overdue' | 'onTime' | 'issues' | 'needMove' | 'coverage';
export interface MetricDef { label: string; question: string; formula: string; source: string; window: string; target?: string }
export const METRICS: Record<MetricId, MetricDef> = {
  tone: { label: 'Tone score', question: 'How do they sound about working with us?', formula: 'Weighted average of the tone the model gave each client message (−2 to +2). Recent messages weigh more: a message 14 days old counts half. Only high-confidence, non-routine messages count; fewer than 2 = “Not enough to read”.', source: 'Gmail, Slack, Fathom, Zoom · client speakers only', window: 'Last 28 days', target: '≥ 0 (Satisfied or better)' },
  negShare: { label: 'Negative messages', question: 'How much of what they say is a concern?', formula: 'Scored messages with tone below 0 ÷ all scored messages.', source: 'Same as tone score', window: 'Last 28 days' },
  toneChange: { label: 'Tone change', question: 'Is it getting better or worse?', formula: 'Tone score today minus tone score 28 days ago (same formula, earlier date).', source: 'Same as tone score', window: 'This 28 days vs the 28 before' },
  volume: { label: 'Messages vs usual', question: 'Have they gone quiet?', formula: 'Client messages in the last 28 days ÷ their average 28-day count over the 84 days before. Under 50% = quieter than usual.', source: 'All client messages, routine included', window: '28 days vs prior 84' },
  lastHeard: { label: 'Last heard', question: 'When did they last write to us?', formula: 'Days since the latest client-authored message on any channel.', source: 'Gmail, Slack, Fathom, Zoom', window: 'All time' },
  waiting: { label: 'Waiting on our reply', question: 'Is anyone waiting on us right now?', formula: 'Client-started threads with no staff reply yet, aged in business days.', source: 'Gmail + Slack thread timestamps', window: 'Now', target: '0 waiting 1+ business day' },
  reply: { label: 'Median first reply', question: 'How fast do we answer?', formula: 'Median business hours (Mon–Fri, 9–18 ET) from a client starting a thread to our first reply. Threads still waiting are counted under “Waiting on our reply”.', source: 'Gmail + Slack thread timestamps', window: 'Threads started in the last 28 days', target: '≤ 4 business hours' },
  overdue: { label: 'Promises late', question: 'Are we behind on what we promised?', formula: 'Open WIA commitments past their due date, aged in business days.', source: 'Action Hub (ClickUp), commitments from calls and email', window: 'Now', target: '0' },
  onTime: { label: 'Promises kept on time', question: 'Do we do what we say, when we say?', formula: 'Commitments due in the window that were done on or before their due date ÷ all commitments due in the window. Open and past due counts as late.', source: 'Action Hub (ClickUp)', window: 'Due in the last 28 days', target: '≥ 90%' },
  issues: { label: 'Open support issues', question: 'Is something broken for them?', formula: 'Client-reported issues not resolved. “Repeat” = reopened within 30 days.', source: 'Support inbox + Slack', window: 'Now', target: '0 repeat, none past 5 business days' },
  needMove: { label: 'Clients needing a move', question: 'How many clients need us to act?', formula: 'Clients on the map whose zone is not Steady. Settling-in and unreadable clients are counted separately.', source: 'Computed zones', window: 'Now vs 7 days ago' },
  coverage: { label: 'Readable tone', question: 'Can we trust the sentiment side?', formula: 'Active clients with at least 2 high-confidence scored messages in 28 days ÷ active clients.', source: 'Tone model output', window: 'Last 28 days', target: '≥ 80%' },
};

export const FEEL_LABEL = ['Frustrated', 'Uneasy', 'Satisfied', 'Delighted'] as const;
export const DELIVERY_LABEL = ['On track', 'At risk', 'Behind', 'Broken'] as const;
export const TONE_LABEL: Record<ToneScore, string> = { [-2]: 'Very negative', [-1]: 'Negative', 0: 'Neutral', 1: 'Positive', 2: 'Very positive' };
export type ZoneV3 = Zone | 'Settling in' | 'Not enough to read';
export const ZONE_MOVE: Record<ZoneV3, string> = {
  Rescue: 'Both sides are slipping. Owner fixes our side today; Whitney joins the next call.',
  'Fix our side': 'They haven’t felt it yet. Clear what we owe before they do.',
  'Reach out': 'We’re on track but they sound uneasy. Talk to them about it.',
  Steady: 'Nothing to act on. Keep going.',
  'Settling in': 'New client: tracked, not judged until day 60.',
  'Not enough to read': 'Too few scored messages to read tone. Our side is still measured.',
};

// ---- Computation --------------------------------------------------------------------------------------
export interface Trigger { level: 1 | 2 | 3; kind: 'late' | 'due' | 'waiting' | 'issue' | 'pileup'; text: string; rule: string }
export interface Snapshot {
  clientId: string; asOf: string; settling: boolean;
  score: number | null; feel: Feel | null; scored: { msg: Message; weight: number }[]; lowExcluded: number;
  negShare: number | null; priorScore: number | null;
  volume: number; usual: number;
  lastHeard: Message | null;
  waiting: { thread: Thread; days: number }[];
  replyHours: number[]; replyMedian: number | null;
  overdue: { c: Commitment; days: number }[]; dueSoon: Commitment[];
  onTime: { kept: number; due: number };
  issues: { issue: Issue; days: number; repeat: boolean }[];
  delivery: 0 | 1 | 2 | 3; triggers: Trigger[];
  zone: ZoneV3;
}

const feelOf = (score: number): Feel => { const [a, b, c] = CONFIG.feelCuts; return score < a ? 0 : score < b ? 1 : score < c ? 2 : 3; };

function toneAt(clientId: string, asOf: string) {
  const inScope = MESSAGES.filter(x => x.clientId === clientId && x.tone !== null && inWindow(day(x.at), asOf));
  const scored = inScope.filter(x => x.confidence === 'High').map(msg => ({ msg, weight: Math.pow(0.5, daysBetween(day(msg.at), asOf) / CONFIG.halfLifeDays) }));
  const w = scored.reduce((s, x) => s + x.weight, 0);
  const score = scored.length >= CONFIG.minScored ? scored.reduce((s, x) => s + x.weight * x.msg.tone!, 0) / w : null;
  return { score, scored, lowExcluded: inScope.length - scored.length };
}

const issueOpenOn = (i: Issue, asOf: string) => {
  const events = [{ d: i.openedOn, open: true }, ...(i.resolvedOn ? [{ d: i.resolvedOn, open: false }] : []), ...(i.reopenedOn || []).map(d => ({ d, open: true }))].filter(e => e.d <= asOf).sort((a, b) => a.d.localeCompare(b.d));
  const last = events[events.length - 1];
  return last?.open ? last.d : null;
};

const clientSince = (id: string) => CLIENTS.find(c => c.id === id)?.since || '2000-01-01';

export function snapshot(clientId: string, asOf: string = AS_OF): Snapshot {
  const settling = daysBetween(clientSince(clientId), asOf) < CONFIG.settlingDays;
  const { score, scored, lowExcluded } = toneAt(clientId, asOf);
  const prior = toneAt(clientId, addDays(asOf, -CONFIG.windowDays));
  const all = MESSAGES.filter(x => x.clientId === clientId && day(x.at) <= asOf);
  const volume = all.filter(x => inWindow(day(x.at), asOf)).length;
  const usual = all.filter(x => inWindow(day(x.at), addDays(asOf, -CONFIG.windowDays), CONFIG.baselineDays)).length / (CONFIG.baselineDays / CONFIG.windowDays);
  const lastHeard = [...all].sort((a, b) => b.at.localeCompare(a.at))[0] || null;
  const end = `${asOf}T23:59`;

  const threads = THREADS.filter(t => t.clientId === clientId && day(t.at) <= asOf);
  const waiting = threads.filter(t => !t.repliedAt || t.repliedAt > end).map(thread => ({ thread, days: businessDays(day(thread.at), asOf) })).sort((a, b) => b.days - a.days);
  const replyHours = threads.filter(t => inWindow(day(t.at), asOf) && t.repliedAt && t.repliedAt <= end).map(t => businessHours(t.at, t.repliedAt!));

  const commits = COMMITMENTS.filter(c => c.clientId === clientId && c.madeOn <= asOf);
  const open = commits.filter(c => !c.doneOn || c.doneOn > asOf);
  const overdue = open.filter(c => c.due < asOf).map(c => ({ c, days: businessDays(c.due, asOf) })).filter(x => x.days > 0).sort((a, b) => b.days - a.days);
  const dueSoon = open.filter(c => c.due >= asOf && businessDays(asOf, c.due) <= CONFIG.dueSoonDays);
  const dueInWindow = commits.filter(c => inWindow(c.due, asOf) && c.due < asOf);
  const onTime = { kept: dueInWindow.filter(c => c.doneOn && c.doneOn <= c.due && c.doneOn <= asOf).length, due: dueInWindow.length };

  const issues = ISSUES.filter(i => i.clientId === clientId).map(issue => { const since = issueOpenOn(issue, asOf); return since ? { issue, days: businessDays(since, asOf), repeat: (issue.reopenedOn || []).some(d => d <= asOf && inWindow(d, asOf, CONFIG.repeatWindowDays)) } : null; }).filter(Boolean) as Snapshot['issues'];

  const triggers: Trigger[] = [];
  overdue.forEach(({ c, days }) => triggers.push({ level: days > CONFIG.lateBrokenDays ? 3 : 2, kind: 'late', text: `“${c.title}” is ${days} business ${days === 1 ? 'day' : 'days'} late (due ${dateLabel(c.due)}, ${c.owner})`, rule: days > CONFIG.lateBrokenDays ? `Promise more than ${CONFIG.lateBrokenDays} business days late` : 'Promise past its due date' }));
  if (overdue.length >= CONFIG.overdueBrokenCount) triggers.push({ level: 3, kind: 'pileup', text: `${overdue.length} promises late at once`, rule: `${CONFIG.overdueBrokenCount}+ promises late` });
  dueSoon.forEach(c => triggers.push({ level: 1, kind: 'due', text: `“${c.title}” is due ${c.due === asOf ? 'today' : dateLabel(c.due)} and still open (${c.owner})`, rule: `Open promise due within ${CONFIG.dueSoonDays} business days` }));
  waiting.forEach(({ thread, days }) => { const lvl = days >= CONFIG.waitBroken ? 3 : days >= CONFIG.waitBehind ? 2 : days >= CONFIG.waitAtRisk ? 1 : 0; if (lvl) triggers.push({ level: lvl as 1 | 2 | 3, kind: 'waiting', text: `${thread.from.split(' ')[0]}’s ${thread.channel} message has waited ${days} business ${days === 1 ? 'day' : 'days'} for a reply`, rule: `Client waiting ${lvl === 3 ? `${CONFIG.waitBroken}+` : lvl === 2 ? `${CONFIG.waitBehind}–${CONFIG.waitBroken - 1}` : `${CONFIG.waitAtRisk}`} business ${lvl === 1 ? 'day' : 'days'}` }); });
  issues.forEach(({ issue, days, repeat }) => triggers.push({ level: repeat ? 3 : days > CONFIG.issueSlaDays ? 2 : 1, kind: 'issue', text: `“${issue.title}” ${repeat ? 'reported again and still open' : `open ${days} business ${days === 1 ? 'day' : 'days'}`}`, rule: repeat ? `Issue reopened within ${CONFIG.repeatWindowDays} days` : days > CONFIG.issueSlaDays ? `Issue open past ${CONFIG.issueSlaDays} business days` : 'Support issue open' }));
  triggers.sort((a, b) => b.level - a.level);
  const delivery = (triggers[0]?.level || 0) as 0 | 1 | 2 | 3;

  const feel = score === null ? null : feelOf(score);
  const zone: ZoneV3 = settling ? 'Settling in' : feel === null ? 'Not enough to read'
    : feel >= 2 ? (delivery <= 1 ? 'Steady' : 'Fix our side') : (delivery <= 1 ? 'Reach out' : 'Rescue');

  return {
    clientId, asOf, settling, score, feel, scored, lowExcluded,
    negShare: scored.length ? scored.filter(x => x.msg.tone! < 0).length / scored.length : null,
    priorScore: prior.score, volume, usual, lastHeard,
    waiting: waiting.filter(w => w.days >= 0), replyHours, replyMedian: median(replyHours),
    overdue, dueSoon, onTime, issues, delivery, triggers, zone,
  };
}

/** Week-ending dates for history, oldest first; each is a full re-run of `snapshot`. */
export const WEEK_ENDS = Array.from({ length: 8 }, (_, i) => addDays(AS_OF, (i - 7) * 7));
export const ACTIVE_IDS = CLIENTS.map(c => c.id).filter(id => RECORDS[id]);
export const ownerOf = (id: string) => RECORDS[id]?.owner || '';

const ZONE_SEVERITY: Record<ZoneV3, number> = { Rescue: 3, 'Fix our side': 2, 'Reach out': 2, Steady: 0, 'Not enough to read': 1, 'Settling in': -1 };
export const severity = (z: ZoneV3) => ZONE_SEVERITY[z];
export const isPlaced = (s: Snapshot) => s.zone !== 'Settling in' && s.zone !== 'Not enough to read';

export interface Book { asOf: string; snaps: Snapshot[]; needMove: number; placed: number; waiting: number; oldestWait: number; replyMedian: number | null; kept: number; due: number; overdue: number; maxLate: number; readable: number; active: number }
export function book(asOf: string = AS_OF, ids: string[] = ACTIVE_IDS): Book {
  const snaps = ids.map(id => snapshot(id, asOf));
  const placed = snaps.filter(isPlaced);
  const waits = snaps.flatMap(s => s.waiting.filter(w => w.days >= 1));
  const overdue = snaps.flatMap(s => s.overdue);
  return {
    asOf, snaps, placed: placed.length, needMove: placed.filter(s => s.zone !== 'Steady').length,
    waiting: waits.length, oldestWait: Math.max(0, ...waits.map(w => w.days)),
    replyMedian: median(snaps.flatMap(s => s.replyHours)),
    kept: snaps.reduce((n, s) => n + s.onTime.kept, 0), due: snaps.reduce((n, s) => n + s.onTime.due, 0),
    overdue: overdue.length, maxLate: Math.max(0, ...overdue.map(o => o.days)),
    readable: snaps.filter(s => s.score !== null).length, active: snaps.length,
  };
}

/** The single next move a rule picks for a client, most urgent fact first. */
export function nextMove(s: Snapshot): { text: string; why: string } {
  const c = CLIENTS.find(x => x.id === s.clientId)!; const first = c.contact.split(' ')[0];
  const w = s.waiting.find(x => x.days >= 1);
  if (w) return { text: `Reply to ${first}’s ${w.thread.channel} message from ${dateLabel(w.thread.at.slice(0, 10))}: “${w.thread.text}”`, why: `Waiting ${w.days} business ${w.days === 1 ? 'day' : 'days'}; replies are the fastest thing a client feels.` };
  if (s.overdue[0]) return { text: `Deliver “${s.overdue[0].c.title}” or agree a new date with ${first} today.`, why: `${s.overdue[0].days} business ${s.overdue[0].days === 1 ? 'day' : 'days'} late; a silent miss costs more than a moved date.` };
  const rep = s.issues.find(i => i.repeat);
  if (rep) return { text: `Confirm the fix for “${rep.issue.title}” and tell ${first} what changed.`, why: 'Reported twice: the second fix has to be visibly different.' };
  if (s.feel !== null && s.feel <= 1) { const t = topConcern(s); return { text: `Call ${first} and open with ${t ? `their concern about ${t.toLowerCase()}` : 'how things feel on their side'}.`, why: `Tone score ${fmtScore(s.score)} with nothing late on our side: the gap is in the relationship, not the work.` }; }
  if (s.usual >= 2 && s.volume < s.usual * CONFIG.quietRatio) return { text: `Check in with ${first}: they’ve gone quiet.`, why: `${s.volume} messages in 28 days vs about ${Math.round(s.usual)} usually.` };
  if (s.dueSoon[0]) return { text: `Make sure “${s.dueSoon[0].title}” lands by ${dateLabel(s.dueSoon[0].due)}.`, why: 'Due within 2 business days and still open.' };
  return { text: 'No move needed this week.', why: 'Nothing waiting, nothing late, tone positive.' };
}

export const topConcern = (s: Snapshot): Theme | null => {
  const counts = new Map<Theme, number>();
  s.scored.filter(x => x.msg.tone! < 0 && x.msg.theme).forEach(x => counts.set(x.msg.theme!, (counts.get(x.msg.theme!) || 0) + 1));
  return [...counts.entries()].sort((a, b) => b[1] - a[1])[0]?.[0] || null;
};
export const fmtScore = (n: number | null) => n === null ? '—' : `${n > 0 ? '+' : n < 0 ? '−' : ''}${Math.abs(n).toFixed(2)}`;
export const fmtHours = (h: number | null) => h === null ? '—' : h < 1 ? `${Math.round(h * 60)} min` : `${h.toFixed(h < 10 ? 1 : 0)} h`;
export const pct = (a: number, b: number) => b ? Math.round(a / b * 100) : null;

/** Everything that happened with a client, both sides, derived from the records. */
export interface RecordEvent { date: string; side: 'client' | 'us'; kind: 'said' | 'promised' | 'kept' | 'late' | 'missed' | 'replied' | 'slow-reply' | 'waiting' | 'issue-open' | 'issue-reopen' | 'issue-fixed'; text: string; msg?: Message; good?: boolean }
export function recordFor(clientId: string, asOf: string = AS_OF, from: string = WEEK_ENDS[0]): RecordEvent[] {
  const ev: RecordEvent[] = [];
  const lo = addDays(from, -6);
  MESSAGES.filter(x => x.clientId === clientId && x.tone !== null).forEach(msg => ev.push({ date: day(msg.at), side: 'client', kind: 'said', text: msg.quote || '', msg }));
  COMMITMENTS.filter(c => c.clientId === clientId).forEach(c => {
    ev.push({ date: c.madeOn, side: 'us', kind: 'promised', text: `Promised “${c.title}” by ${dateLabel(c.due)} (${c.source})` });
    if (c.doneOn && c.doneOn <= asOf) ev.push(c.doneOn <= c.due ? { date: c.doneOn, side: 'us', kind: 'kept', text: `Delivered “${c.title}” on time`, good: true } : { date: c.doneOn, side: 'us', kind: 'late', text: `Delivered “${c.title}” ${businessDays(c.due, c.doneOn)} business days late` });
    else if (c.due < asOf) ev.push({ date: addDays(c.due, 1), side: 'us', kind: 'missed', text: `Missed the ${dateLabel(c.due)} date for “${c.title}”` });
  });
  THREADS.filter(t => t.clientId === clientId).forEach(t => {
    if (t.repliedAt && day(t.repliedAt) <= asOf) { const h = businessHours(t.at, t.repliedAt); ev.push({ date: day(t.repliedAt), side: 'us', kind: h > CONFIG.replyTargetHours ? 'slow-reply' : 'replied', text: `${t.repliedBy} replied to “${t.text}” in ${fmtHours(h)}`, good: h <= CONFIG.replyTargetHours }); }
    else if (day(t.at) <= asOf) ev.push({ date: asOf, side: 'us', kind: 'waiting', text: `No reply yet to “${t.text}” (${businessDays(day(t.at), asOf)} business days)` });
  });
  ISSUES.filter(i => i.clientId === clientId).forEach(i => {
    ev.push({ date: i.openedOn, side: 'us', kind: 'issue-open', text: `Issue reported: “${i.title}”` });
    if (i.resolvedOn) ev.push({ date: i.resolvedOn, side: 'us', kind: 'issue-fixed', text: `Marked fixed: “${i.title}”`, good: true });
    (i.reopenedOn || []).forEach(d => ev.push({ date: d, side: 'us', kind: 'issue-reopen', text: `Reported again: “${i.title}”` }));
  });
  return ev.filter(e => e.date >= lo && e.date <= asOf).sort((a, b) => b.date.localeCompare(a.date) || (a.side === 'client' ? -1 : 1));
}

/** Negative mentions per theme across the book, this window vs the one before. */
export function themeTrend(asOf: string = AS_OF, ids: string[] = ACTIVE_IDS) {
  const neg = (d: string) => MESSAGES.filter(x => ids.includes(x.clientId) && x.tone !== null && x.tone < 0 && x.confidence === 'High' && inWindow(day(x.at), d));
  const now = neg(asOf), before = neg(addDays(asOf, -CONFIG.windowDays));
  return THEMES.map(t => ({ theme: t, now: now.filter(x => x.theme === t), before: before.filter(x => x.theme === t).length, clients: new Set(now.filter(x => x.theme === t).map(x => x.clientId)).size }))
    .sort((a, b) => b.now.length - a.now.length || b.before - a.before);
}

/** What the pipeline read for a client in the window: shown so a reader can judge the evidence. */
export function coverageFor(clientId: string, asOf: string = AS_OF) {
  const msgs = MESSAGES.filter(x => x.clientId === clientId && inWindow(day(x.at), asOf));
  return {
    messages: msgs.length, scored: msgs.filter(x => x.tone !== null && x.confidence === 'High').length, low: msgs.filter(x => x.tone !== null && x.confidence === 'Low').length, routine: msgs.filter(x => x.tone === null).length,
    channels: [...new Set(msgs.map(x => x.channel))],
    threads: THREADS.filter(t => t.clientId === clientId && inWindow(day(t.at), asOf)).length,
    commitments: COMMITMENTS.filter(c => c.clientId === clientId && (inWindow(c.due, asOf) || (!c.doneOn && c.madeOn <= asOf))).length,
  };
}
