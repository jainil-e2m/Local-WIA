// Fictional weekly history for the revised Health & Sentiment view.
// Two separate measures, never combined (KB-CH-42):
//  - Feel: the LLM's weekly reading of the client's own words, on four steps with no neutral middle
//    (0 Frustrated, 1 Uneasy | 2 Satisfied, 3 Delighted). Routine messages carry no weight.
//  - Delivery: facts from code about WIA's side (0 On track, 1 At risk | 2 Behind, 3 Broken).
// Both axes split in the middle: positive vs negative tone, and nothing late vs something late.
// The zone comes from where the two meet, so it always says whose move it is.
import { DEMO_DATE, addDays } from './data';

/** Tone of a single message. A message can be routine (Neutral); the weekly reading can't. */
export const MOODS = ['Frustrated', 'Uneasy', 'Neutral', 'Satisfied', 'Delighted'] as const;
/** Weekly reading of how the client feels: four steps, split between Uneasy and Satisfied. */
export const FEEL = ['Frustrated', 'Uneasy', 'Satisfied', 'Delighted'] as const;
export type Feel = 0 | 1 | 2 | 3;
/** The message-tone step each weekly reading corresponds to (used for colour and the timeline). */
export const feelTone = (f: Feel): Tone => ([0, 1, 3, 4] as const)[f];
export const FEEL_RULES = [
  'Open dissatisfaction: a complaint, escalation, or talk of pausing or leaving.',
  'Doubts or friction: questioning results or value, hesitation, mild frustration.',
  'Positive and cooperative: approvals, appreciation, easy back-and-forth.',
  'Openly enthusiastic: praise, warm thanks, referrals.',
] as const;
/** How WIA is doing: four steps, split between "nothing late yet" and "something late". */
export const DELIVERY = ['On track', 'At risk', 'Behind', 'Broken'] as const;
export const DELIVERY_RULES = [
  'Nothing due soon is at risk, and no client message is waiting on us.',
  'Something due within 2 days isn’t acknowledged or started, a reply has waited 1 business day, or a support issue is near its target.',
  'A WIA item is up to 5 business days late, a reply has waited 2–3 business days, or a support issue is past its target.',
  'A client-facing deadline is over 5 business days late, a reply has waited 4+ business days, the same issue was reported twice, or 3+ items are late.',
] as const;
export type Zone = 'Steady' | 'Fix our side' | 'Reach out' | 'Rescue';
export type Tone = 0 | 1 | 2 | 3 | 4;
/** Fixed topics WIA chose up front, so themes stay comparable month to month. */
export const THEMES = ['Lead quality', 'Pages & creative', 'Tech & tracking', 'Communication', 'Programme & sessions', 'Strategy & planning'] as const;
export type Theme = (typeof THEMES)[number];
export const toneKind = (t: Tone) => t <= 1 ? 'Concern' : t === 2 ? 'Neutral' : 'Positive';

export const ZONES: { id: Zone; move: string; who: string }[] = [
  { id: 'Rescue', move: 'Both sides are slipping. Whitney steps in.', who: 'Whitney + owner' },
  { id: 'Fix our side', move: 'They haven’t felt it yet. Catch up before they do.', who: 'Owner' },
  { id: 'Reach out', move: 'We’re on track but they’re uneasy. Talk to them.', who: 'Owner' },
  { id: 'Steady', move: 'Keep going.', who: '—' },
];

/** A client message the LLM has read. Only words the client wrote or said, speaker checked. */
export interface ToneReading { date: string; theme: Theme; tone: Tone; confidence: 'High' | 'Low'; quote: string; speaker: string; channel: 'Gmail' | 'Slack' | 'Fathom' | 'Zoom'; sourceId?: string }
export interface OurEvent { date: string; text: string; kind: 'slip' | 'fix' }

export interface Pulse {
  clientId: string;
  /** Weekly reading of how they feel, oldest first; null = not enough to read (only routine messages). */
  mood: (Feel | null)[];
  delivery: (0 | 1 | 2 | 3)[];
  readings: ToneReading[];
  ourSide: OurEvent[];
  /** One line naming what moved this client this week. */
  story?: string;
  settling?: boolean;
}

/** The eight week-ending dates the history covers, oldest first. */
export const WEEKS = Array.from({ length: 8 }, (_, i) => addDays(DEMO_DATE, (i - 7) * 7));

export const PULSE: Pulse[] = [
  { clientId: 'bloom', mood: [2, 2, 2, 2, 2, 2, 2, 1], delivery: [0, 0, 0, 0, 2, 0, 0, 2],
    story: 'Sarah’s question about inquiry quality reads as a real worry, and the landing page missed its Oct 8 date.',
    readings: [
      { date: '2026-08-20', theme: 'Strategy & planning', tone: 3, confidence: 'High', quote: 'Thank you for walking us through the new campaign plan, that was really clear.', speaker: 'Sarah Mitchell', channel: 'Zoom' },
      { date: '2026-09-11', theme: 'Communication', tone: 2, confidence: 'Low', quote: 'We are fine with that, just keep us posted.', speaker: 'Sarah Mitchell', channel: 'Gmail' },
      { date: '2026-09-30', theme: 'Pages & creative', tone: 3, confidence: 'High', quote: 'I would rather get the revised page signed off before we change any of the campaign messaging.', speaker: 'Sarah Mitchell', channel: 'Zoom', sourceId: 'bloom-call' },
      { date: '2026-10-08', theme: 'Pages & creative', tone: 3, confidence: 'High', quote: 'The gallery looks beautiful.', speaker: 'Sarah Mitchell', channel: 'Gmail', sourceId: 'bloom-email' },
      { date: '2026-10-08', theme: 'Lead quality', tone: 1, confidence: 'High', quote: 'Could we talk through what we know about the inquiries coming in? I want to understand where couples are dropping off.', speaker: 'Sarah Mitchell', channel: 'Gmail', sourceId: 'bloom-email' },
    ],
    ourSide: [{ date: '2026-09-11', text: 'Ad copy sent two days late', kind: 'slip' }, { date: '2026-09-30', text: 'Page promised for Oct 8', kind: 'fix' }, { date: '2026-10-08', text: 'Page not sent', kind: 'slip' }] },
  { clientId: 'rosewood', mood: [2, 2, 2, 2, 2, 3, 3, 2], delivery: [0, 0, 2, 0, 0, 0, 2, 3],
    story: 'Dana loved the new sequence, then the tour-link bug came back a second time.',
    readings: [
      { date: '2026-08-27', theme: 'Tech & tracking', tone: 2, confidence: 'High', quote: 'The tour link seems to show the wrong times for some couples.', speaker: 'Dana Whitfield', channel: 'Slack' },
      { date: '2026-09-25', theme: 'Pages & creative', tone: 4, confidence: 'High', quote: 'The new photos are exactly the feel we wanted.', speaker: 'Dana Whitfield', channel: 'Slack' },
      { date: '2026-10-02', theme: 'Pages & creative', tone: 4, confidence: 'High', quote: 'This sounds much more like us now. I am happy to approve the revised follow-up sequence.', speaker: 'Dana Whitfield', channel: 'Zoom', sourceId: 'rosewood-call' },
      { date: '2026-10-06', theme: 'Tech & tracking', tone: 1, confidence: 'High', quote: 'The tour link is showing couples the wrong times again. Can someone look at this before the weekend?', speaker: 'Dana Whitfield', channel: 'Slack' },
    ],
    ourSide: [{ date: '2026-08-27', text: 'Timezone bug reported', kind: 'slip' }, { date: '2026-09-03', text: 'Bug marked fixed', kind: 'fix' }, { date: '2026-10-06', text: 'Bug reported again', kind: 'slip' }] },
  { clientId: 'willow', mood: [2, 2, 2, 1, 1, 1, 1, 1], delivery: [0, 0, 0, 0, 1, 1, 1, 3],
    story: 'Maya asked for help four business days ago and is still waiting on our reply.',
    readings: [
      { date: '2026-08-21', theme: 'Pages & creative', tone: 3, confidence: 'High', quote: 'Excited to try the new creative angles this month!', speaker: 'Maya Stone', channel: 'Slack' },
      { date: '2026-09-17', theme: 'Programme & sessions', tone: 2, confidence: 'Low', quote: 'I will catch the recording if I miss it.', speaker: 'Maya Stone', channel: 'Slack' },
      { date: '2026-10-05', theme: 'Programme & sessions', tone: 1, confidence: 'High', quote: 'I have been a bit stretched these past two weeks and missed the sessions.', speaker: 'Maya Stone', channel: 'Gmail', sourceId: 'willow-email' },
      { date: '2026-10-05', theme: 'Communication', tone: 2, confidence: 'High', quote: 'Could someone give me feedback on one example so I can get moving again?', speaker: 'Maya Stone', channel: 'Gmail', sourceId: 'willow-email' },
    ],
    ourSide: [{ date: '2026-09-17', text: 'Office hours missed (client)', kind: 'slip' }, { date: '2026-10-05', text: 'Her question unanswered', kind: 'slip' }, { date: '2026-10-08', text: 'Check-in overdue', kind: 'slip' }] },
  { clientId: 'everly', mood: [2, 2, 3, 3, 3, 3, 3, 3], delivery: [0, 0, 0, 0, 0, 0, 0, 1],
    readings: [
      { date: '2026-09-04', theme: 'Pages & creative', tone: 3, confidence: 'High', quote: 'Happy with how the reels are landing.', speaker: 'Nina Cole', channel: 'Slack' },
      { date: '2026-10-01', theme: 'Pages & creative', tone: 4, confidence: 'High', quote: 'The portfolio edit feels right.', speaker: 'Nina Cole', channel: 'Zoom', sourceId: 'everly-call' },
      { date: '2026-10-07', theme: 'Tech & tracking', tone: 2, confidence: 'Low', quote: 'Some inquiries seem to be going to spam, can you check?', speaker: 'Nina Cole', channel: 'Slack' },
    ],
    ourSide: [{ date: '2026-10-06', text: 'Renewal signed', kind: 'fix' }, { date: '2026-10-07', text: 'Spam issue opened (Ivy on it)', kind: 'slip' }] },
  { clientId: 'magnolia', mood: [2, 2, 2, 2, 1, 1, 1, 2], delivery: [0, 0, 0, 0, 2, 2, 2, 0],
    story: 'Tessa was unsure for three weeks; after three office hours in a row she’s positive again.',
    readings: [
      { date: '2026-09-15', theme: 'Lead quality', tone: 1, confidence: 'High', quote: 'I am not sure the keywords match what we actually offer.', speaker: 'Tessa Ruiz', channel: 'Slack' },
      { date: '2026-09-24', theme: 'Communication', tone: 1, confidence: 'Low', quote: 'Still waiting to hear back on the page review.', speaker: 'Tessa Ruiz', channel: 'Slack' },
      { date: '2026-10-06', theme: 'Pages & creative', tone: 3, confidence: 'High', quote: 'Looking forward to feedback on whether the intent matches the page.', speaker: 'Tessa Ruiz', channel: 'Slack', sourceId: 'magnolia-slack' },
    ],
    ourSide: [{ date: '2026-09-24', text: 'Page review late', kind: 'slip' }, { date: '2026-10-02', text: 'Page review sent', kind: 'fix' }] },
  { clientId: 'harbor', mood: [null, null, null, null, null, 2, 2, 3], delivery: [0, 0, 0, 0, 0, 0, 0, 0], settling: true,
    readings: [
      { date: '2026-09-24', theme: 'Strategy & planning', tone: 3, confidence: 'High', quote: 'Thanks for the kickoff pack, very thorough.', speaker: 'Elise Bennett', channel: 'Gmail' },
      { date: '2026-10-08', theme: 'Strategy & planning', tone: 4, confidence: 'High', quote: 'We are excited to get the new process going.', speaker: 'Elise Bennett', channel: 'Gmail', sourceId: 'harbor-email' },
    ],
    ourSide: [{ date: '2026-09-21', text: 'Onboarding started', kind: 'fix' }] },
];

export const zoneOf = (mood: Feel | null, delivery: number): Zone | null => {
  if (mood === null) return null;
  const feelsOk = mood >= 2, doingOk = delivery <= 1;
  return feelsOk && doingOk ? 'Steady' : feelsOk ? 'Fix our side' : doingOk ? 'Reach out' : 'Rescue';
};
const ZONE_RANK: Record<Zone, number> = { Steady: 0, 'Reach out': 1, 'Fix our side': 1, Rescue: 2 };
export const zoneRank = (z: Zone | null) => z ? ZONE_RANK[z] : -1;
export const pulseFor = (id: string) => PULSE.find(p => p.clientId === id)!;
