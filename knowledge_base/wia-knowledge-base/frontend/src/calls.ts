import kbLive from '@kb-live';
// Fictional call-prep records for the Call Preparation scope (kb_tab_scope/05-call-preparation.md).

export type CallTypeKey = 'ads-kickoff' | 'messaging' | 'leadlock-kickoff' | 'strategy' | 'creative' | 'office-hours' | 'checkin' | 'other';
export type BriefState = 'Ready' | 'Stale' | 'Scheduled' | 'Needs type' | 'Cancelled';
export type SectionKey = 'since' | 'asks' | 'owed' | 'agenda' | 'questions' | 'watch' | 'opportunity' | 'typeBlock' | 'limits';

export const SECTION_LABELS: Record<SectionKey, string> = {
  since: 'Since the last call', asks: 'They asked, we haven’t answered', owed: 'What we owe / what they owe', agenda: 'Agenda',
  questions: 'Questions to ask', watch: 'Watch-outs', opportunity: 'One opportunity', typeBlock: 'Type-specific', limits: 'Sources & limits',
};

export interface Template { key: CallTypeKey; name: string; detect: string; purpose: string; sections: SectionKey[]; typeBlock: string; agenda: string[]; leaveOut: string; guidance?: string; /** Live: the skill's "This call must decide". */ decide?: string }

export const TEMPLATES: Template[] = [
  { key: 'ads-kickoff', name: 'Ads kickoff', detect: 'Title contains “Ads Kickoff”', purpose: 'Introductions, set expectations, connect ad accounts', sections: ['owed', 'agenda', 'questions', 'typeBlock', 'limits'], typeBlock: 'Access checklist & what was sold', agenda: ['Introductions and who does what', 'How the work runs and what to expect', 'Connect ad accounts live', 'Next steps and the messaging interview'], leaveOut: 'Performance, strategy opinions, price' },
  { key: 'messaging', name: 'Messaging & positioning interview', detect: 'Title contains “Messaging” or “Positioning”', purpose: 'Deep-dive on the business, audience and voice', sections: ['asks', 'agenda', 'questions', 'typeBlock', 'limits'], typeBlock: 'Questionnaire answers', agenda: ['Their story in their words', 'Ideal couple and objections', 'Offer and what sets them apart', 'Voice: words to use and avoid'], leaveOut: 'Ads, unrelated actions' },
  { key: 'leadlock-kickoff', name: 'LeadLock kickoff', detect: 'Title contains “LeadLock Kickoff” or booked via the LeadLock calendar', purpose: 'Plan the LeadLock build', sections: ['since', 'asks', 'owed', 'agenda', 'watch', 'typeBlock', 'limits'], typeBlock: 'CRM & setup facts', agenda: ['Current inquiry workflow and CRM', 'Who answers new inquiries', 'What WIA sets up vs what stays with the client', 'Setup milestones'], leaveOut: 'Ads strategy' },
  { key: 'strategy', name: 'Monthly strategy', detect: 'Title contains “Strategy”', purpose: 'Review the month and plan the next', sections: ['since', 'asks', 'owed', 'agenda', 'questions', 'watch', 'opportunity', 'typeBlock', 'limits'], typeBlock: 'Results & ads context', agenda: ['Client’s open questions first', 'What was delivered and what’s next', 'Results and what they mean', 'Decisions needed'], leaveOut: 'Onboarding detail' },
  { key: 'creative', name: 'Creative review', detect: 'Title contains “Creative”', purpose: 'Approve creative and page changes', sections: ['since', 'asks', 'owed', 'agenda', 'typeBlock', 'limits'], typeBlock: 'Approvals & voice', agenda: ['What’s ready to review', 'Feedback and decisions', 'Approval and next delivery date'], leaveOut: 'Lead numbers' },
  { key: 'office-hours', name: 'Office hours (group)', detect: 'Title contains “Office Hours”', purpose: 'Programme coaching for several members', sections: ['asks', 'agenda', 'typeBlock', 'limits'], typeBlock: 'Members expected', agenda: ['Quick wins from last week', 'Member questions in turn', 'One task each for next week'], leaveOut: 'Any member’s details beyond their own parts' },
  { key: 'checkin', name: 'Programme check-in (1:1)', detect: 'Title contains “Check-in”', purpose: 'Re-engage an accelerator member', sections: ['since', 'asks', 'owed', 'agenda', 'watch', 'typeBlock', 'limits'], typeBlock: 'Programme progress', agenda: ['What’s getting in the way', 'Pick one concrete next step', 'Confirm the next session'], leaveOut: 'Programme-wide news' },
  { key: 'other', name: 'Other / unclassified', detect: 'Fallback', purpose: 'General client call', sections: ['since', 'asks', 'owed', 'limits'], typeBlock: '', agenda: [], leaveOut: '—' },
];
export const templateFor = (k: CallTypeKey) => TEMPLATES.find(t => t.key === k)!;

// ---- Skills: the editable content behind each brief (admins edit; everyone can read) ----
export type SkillKey = CallTypeKey | 'default';
export interface Skill extends Omit<Template, 'key'> { key: SkillKey }

export const DEFAULT_SKILL_SPEC: Skill = {
  key: 'default', name: 'Default call prep', detect: 'Every call, automatically 2 hours before it starts', purpose: 'The same core sections for every call',
  sections: ['since', 'asks', 'owed', 'agenda', 'questions', 'watch', 'opportunity', 'limits'], typeBlock: '',
  agenda: ['Client’s open questions first', 'What we owe and what they owe', 'Decisions needed before the next call'],
  leaveOut: 'Anything not supported by an approved source',
  guidance: 'Open with the goal of the call in one sentence. Lead with what the client asked and hasn’t had answered. Keep every point to one line, cite the source for each fact, and say plainly when something is unknown.',
};
const GUIDANCE: Record<CallTypeKey, string> = {
  'ads-kickoff': 'Keep it practical: who does what, what was sold, and which accounts still need connecting. No performance talk yet.',
  messaging: 'Quote the questionnaire in the client’s own words. Suggest follow-up questions where answers are thin or contradict each other.',
  'leadlock-kickoff': 'Make the split clear between what WIA sets up and what stays with the client. Flag any missing CRM or access detail.',
  strategy: 'Start with the client’s open questions. Explain results in plain language against the playbook thresholds; label interpretations.',
  creative: 'List exactly what is ready for approval and what decision is needed on each. Keep voice notes from the profile next to each item.',
  'office-hours': 'One short line per expected member. Never show one member’s details to another.',
  checkin: 'Be warm and specific: what is blocking them, and one small next step. Don’t assume missed sessions mean unhappiness.',
  other: 'Summarise recent context and anything owed either way. Ask the host to set a call type if the purpose is unclear.',
};
TEMPLATES.forEach(t => { t.guidance = GUIDANCE[t.key]; });

const ORIGINAL = new Map<SkillKey, Skill>([DEFAULT_SKILL_SPEC, ...TEMPLATES].map(t => [t.key, structuredClone(t) as Skill]));
export const skillFor = (k: SkillKey): Skill => k === 'default' ? DEFAULT_SKILL_SPEC : templateFor(k);
export const skillEdits = new Map<SkillKey, { by: string; on: string }>();
const SKILLS_KEY = 'wia-call-skills-v1';
// The live app saves skill edits on the KB server (CallPrepV2 → /api/v1/call-skills) and loads them from the
// portfolio, so only the sample preview keeps them in this browser.
const persist = () => { if (kbLive.meta) return; try { localStorage.setItem(SKILLS_KEY, JSON.stringify([...skillEdits].map(([k, e]) => ({ key: k, edit: e, skill: skillFor(k) })))); } catch { /* Edits last for this session only. */ } };
/** Saved edits update the shared skill in place, so every view that reads it picks the change up. */
export function saveSkill(next: Skill, by: string, on: string) { Object.assign(skillFor(next.key), structuredClone(next)); skillEdits.set(next.key, { by, on }); persist(); }
export function resetSkill(k: SkillKey) { Object.assign(skillFor(k), structuredClone(ORIGINAL.get(k)!)); skillEdits.delete(k); persist(); }
if (!kbLive.meta) try {
  const saved: { key: SkillKey; edit: { by: string; on: string }; skill: Skill }[] = JSON.parse(localStorage.getItem(SKILLS_KEY) || '[]');
  for (const row of saved) if (ORIGINAL.has(row.key)) { Object.assign(skillFor(row.key), row.skill, { key: row.key }); skillEdits.set(row.key, row.edit); }
} catch { /* Use the original skills. */ }


export interface Brief {
  thirty: string[];
  since: { text: string; date: string; sourceId?: string }[];
  asks: { quote: string; who: string; date: string; sourceId?: string }[];
  agenda: { item: string; why: string }[];
  questions: string[];
  watch: string[];
  opportunity?: { text: string; why: string; sourceId?: string };
  typeBlock: { label: string; value: string }[];
  limits: string[];
  more: Partial<Record<SectionKey, string>>;
  /** Live: what a person's instructions asked for that no approved source can give. */
  declined?: string;
}

// ---- Live call prep (backend/services/callprep): facts computed by code, versions of the model's text ----
export type Tone = 'ok' | 'watch' | 'bad' | 'none';
export interface Chip { value: string; note: string; tone: Tone }
export interface AdTotals { spend: number; leads: number; clicks: number; impressions: number; cpl: number | null; ctr: number | null; link_ctr?: number | null; lpv_rate?: number; budget_lost_is?: number }
export interface AdPlatform {
  provider: 'google_ads' | 'meta'; label: string; state: 'connected' | 'not_mapped' | 'not_connected';
  accounts?: { id: string; name: string; currency: string | null; error: string | null; pulled: string | null }[];
  current?: AdTotals; previous?: AdTotals | null; campaigns?: (AdTotals & { name: string; channel: string })[];
}
export interface LiveAction { id: string; title: string; owner: string; due: string; status: string; late: boolean; lateDays: number; sourceId: string }
export interface CallFacts {
  window: { since: string; basis: string; until: string };
  pulse: { ads: Chip; leads: Chip; delivery: Chip; client: Chip };
  settle: { who: string; text: string; age: string; tone: 'late' | 'ask' | 'wait'; sourceId?: string }[];
  owed: { we: LiveAction[]; they: LiveAction[]; overdue: number; due_before_call: number };
  asks: { quote: string; who: string; date: string; sourceId: string }[];
  awaiting: { subject: string; from: string; date: string; hours: number; sourceId: string }[];
  promised: { recap: { id: string; date: string; title: string; decisions: string[]; covered: { item: string; done: boolean }[]; sourceId?: string } | null;
    items: { text: string; who: string; when: string; status: string; now: string; actionId: string | null }[] };
  changed: { id: string; text: string; detail: string; date: string; lane: string; from: 'Client' | 'Internal'; sourceId: string; state?: string | null }[];
  leads: { inquiries: [number, number | null]; tours: [number, number | null]; won: [number | null, number | null] | null; awaiting: number; collecting: boolean } | null;
  ads: { period_days: number; through: string; platforms: AdPlatform[] };
  attendance: string | null;
  limits: string[];
}
export interface LiveVersion { n: number; by: string; at: string; skill: string; trigger: string; outcome: 'ready' | 'rejected'; prompt: string; declined?: string; rejected?: string[]; brief?: Brief }

export interface CallMeta {
  id: string; clientId: string; date: string; time: string; duration: string; title: string; host: string; attendees: string[];
  type: CallTypeKey; typeSource: 'Calendar title' | 'Proposed by KB' | 'Set by the team' | 'Fallback'; state: BriefState; stateNote?: string; builtAt?: string; extra?: boolean;
  brief?: Brief;
  /** Live only (the sample calls compute these in the browser). */
  recordId?: string; hostSource?: string; facts?: CallFacts; versions?: LiveVersion[]; changedReasons?: string[];
  attendeeDetail?: { name: string; side: 'WIA' | 'Client'; response: string }[];
}
export interface ExcludedCall { id: string; clientId: string; title: string; date: string; time: string; why: string }
export const EXCLUDED_CALLS: ExcludedCall[] = [];
/** Live: the call-type skill files as the KB stores them (raw text and version, for the editor). */
export const SKILL_FILES = new Map<string, { text: string; ref: string; edited?: { by: string; at: string; version: number } }>();

export const CALL_META: CallMeta[] = [
  { id: 'call-bloom', clientId: 'bloom', date: '2026-10-09', time: '14:00', duration: '45 min', title: 'Monthly Strategy | Bloom Manor', host: 'Whitney', attendees: ['Whitney', 'Jacqueline', 'Carmen', 'Sarah Mitchell'], type: 'strategy', typeSource: 'Calendar title', state: 'Stale', stateNote: 'Built Oct 8, 7:00 PM. Since then: “Send the revised landing page” became overdue (midnight).', builtAt: '2026-10-08 19:00',
    brief: {
      thirty: ['Sarah wants to understand inquiry quality before anything else.', 'Must achieve: get the revised page to Sarah and agree when she’ll approve it.', 'Risk: WIA missed the Oct 8 page date we promised on the last call.'],
      since: [{ text: 'Sep 30 call: page approval comes before any campaign messaging change.', date: '2026-09-30', sourceId: 'bloom-call' }, { text: 'Landing-page task moved to In progress.', date: '2026-10-07', sourceId: 'bloom-task' }, { text: 'Sarah emailed with a question about inquiry quality.', date: '2026-10-08', sourceId: 'bloom-email' }],
      asks: [{ quote: 'Could we talk through what we know about the inquiries coming in? I want to understand which couples are a good fit, and where they are dropping off before booking a tour.', who: 'Sarah Mitchell', date: '2026-10-08', sourceId: 'bloom-email' }],
      agenda: [{ item: 'Sarah’s inquiry-quality question', why: 'Her open ask; she raised it before the call' }, { item: 'Revised landing page: share it and agree an approval date', why: 'Promised Oct 8, still open' }, { item: 'What the inquiry data shows', why: 'Supports her question; Viktor flagged Google leads down' }, { item: 'Next creative refresh, once the page is approved', why: 'Sep 30 decision' }],
      questions: ['Which recent inquiries felt like a good fit?', 'Who else needs to see the page before approval (Tom?)'],
      watch: ['Acknowledge the missed Oct 8 page date up front; don’t promise a new date you can’t keep.', 'Lead quality is her question, not a confirmed decline. Don’t present it as a problem.'],
      opportunity: { text: 'Add a short “is this the right venue for you?” section to the page to filter couples before they inquire.', why: 'Directly answers her fit question, uses the page already in progress, and can ship before the next call.', sourceId: 'bloom-drive' },
      typeBlock: [{ label: 'Ads (Viktor, Oct 6)', value: 'Yellow: Google leads down 18% vs prior 30 days (attributed)' }, { label: 'Health', value: 'Needs attention: follow-through, promise missed' }, { label: 'Lead outcomes', value: 'Not a LeadLock client' }],
      limits: ['Sources: Zoom (Sep 30), Gmail (Oct 8), ClickUp, Drive questionnaire', 'No survey responses found', 'Ad data only from Viktor’s posts (paid media not connected)'],
      more: { since: 'Earlier: onboarding completed in May; the autumn gallery was delivered Oct 3.', agenda: 'Allow 10 minutes for the inquiry question; Sarah prefers to see examples.', watch: 'Tom joins budget discussions only; no budget topics planned.' },
    } },
  { id: 'call-everly', clientId: 'everly', date: '2026-10-09', time: '15:30', duration: '30 min', title: 'Creative Review | Everly Films', host: 'Whitney', attendees: ['Whitney', 'Ivy', 'Nina Cole'], type: 'creative', typeSource: 'Calendar title', state: 'Ready', builtAt: '2026-10-08 19:00',
    brief: {
      thirty: ['Nina approved the portfolio edit and renewed for 2027.', 'Must achieve: agree how the spring dates appear on the page.', 'Risk: we still need her list of spring dates.'],
      since: [{ text: 'Portfolio edit approved on the Oct 1 call.', date: '2026-10-01', sourceId: 'everly-call' }, { text: 'Spring-dates page update in progress (Ivy).', date: '2026-10-06' }],
      asks: [{ quote: 'The main thing I need next is to make it clear that we have a few spring dates open.', who: 'Nina Cole', date: '2026-10-01', sourceId: 'everly-call' }],
      agenda: [{ item: 'Where the availability message sits on the page', why: 'Her open ask' }, { item: 'Confirm the remaining spring dates', why: 'Client owes the list' }, { item: 'Approval and go-live date', why: 'Page due Oct 13' }],
      questions: [], watch: ['Keep it personal; she dislikes promotional wording.'],
      typeBlock: [{ label: 'Pending approval', value: 'Spring availability section (draft by Ivy)' }, { label: 'Voice', value: 'Human, observant, intimate. Avoid: “cinematic”, “epic”, “breathtaking”' }],
      limits: ['Sources: Zoom (Oct 1), Drive, ClickUp'], more: {},
    } },
  { id: 'call-harbor', clientId: 'harbor', date: '2026-10-09', time: '16:30', duration: '45 min', title: 'LeadLock Kickoff | Harbor House', host: 'Danielle', attendees: ['Danielle', 'Whitney', 'Elise Bennett'], type: 'leadlock-kickoff', typeSource: 'Calendar title', state: 'Ready', builtAt: '2026-10-09 08:10',
    brief: {
      thirty: ['Elise is positive and wants clarity on who sets up what.', 'Must achieve: confirm the current CRM and who answers new inquiries.', 'Risk: CRM confirmation has been outstanding since Oct 6.'],
      since: [{ text: 'Messaging interview done; CRM question raised.', date: '2026-10-06', sourceId: 'harbor-call' }, { text: 'Elise asked the kickoff to cover responsibilities.', date: '2026-10-08', sourceId: 'harbor-email' }],
      asks: [{ quote: 'Could the kickoff cover which parts stay with us and which parts your team will set up?', who: 'Elise Bennett', date: '2026-10-08', sourceId: 'harbor-email' }],
      agenda: [{ item: 'Current inquiry workflow and CRM', why: 'Outstanding since Oct 6' }, { item: 'Who answers each new inquiry', why: 'Their stated priority in the questionnaire' }, { item: 'What WIA sets up vs what stays with Harbor', why: 'Elise’s open ask' }, { item: 'Setup milestones and the DNS issue', why: 'Open support issue' }],
      questions: ['Name of the venue coordinator who handles inquiries today?'],
      watch: ['Elise can’t log into LeadLock yet (invite not accepted). Help her on the call.'],
      typeBlock: [{ label: 'Current CRM', value: 'Unknown, Elise is checking with the coordinator' }, { label: 'Who answers inquiries', value: 'The venue coordinator (questionnaire, Sep 21)' }, { label: 'Open setup issues', value: 'DNS records incomplete; LeadLock login pending' }, { label: 'Offer sold', value: 'Foolproof Follow-Up Advantage (via GHL checkout)' }],
      limits: ['Sales call notes not in the KB (sales calls are out of scope)', 'LeadLock lead data unavailable (H6)'], more: {},
    } },
  { id: 'call-rosewood', clientId: 'rosewood', date: '2026-10-12', time: '11:00', duration: '45 min', title: 'Monthly Strategy | Rosewood Estate', host: 'Whitney', attendees: ['Whitney', 'Jacqueline', 'Danielle', 'Dana Whitfield'], type: 'strategy', typeSource: 'Calendar title', state: 'Scheduled', stateNote: 'Builds Oct 11, 7:00 PM (evening before).',
    brief: {
      thirty: ['Dana is happy with the new follow-up sequence.', 'Must achieve: agree the winter-tour message.', 'Risk: the tour-link timezone bug came back a second time.'],
      since: [{ text: 'Follow-up sequence approved; test inquiry passed.', date: '2026-10-07', sourceId: 'rosewood-slack' }],
      asks: [{ quote: 'The tour link is showing couples the wrong times again. Can someone look at this before the weekend?', who: 'Dana Whitfield', date: '2026-10-06' }],
      agenda: [{ item: 'Tour-link fix status', why: 'Repeat support issue' }, { item: 'Winter-tour messaging draft', why: 'Jacqueline committed to it for this call' }, { item: 'Lead results', why: 'Steady; 3 weekend inquiries uncontacted' }],
      questions: [], watch: ['Confirm the bug is fixed before saying so.'],
      opportunity: { text: 'Weekend auto-reply that offers a tour slot, to close the weekend gap.', why: 'Lead handling shows 3 uncontacted weekend inquiries; LeadLock can do it now.' },
      typeBlock: [{ label: 'Lead outcomes', value: 'Inquiries 38 (prior 41) · tours 14 (12) · bookings 4 (3)' }, { label: 'Ads (Viktor, Oct 6)', value: 'Green: Meta cost per lead stable' }],
      limits: ['LeadLock read as if access were granted (H6)'], more: {},
    } },
  { id: 'call-willow', clientId: 'willow', date: '2026-10-13', time: '12:00', duration: '20 min', title: 'Check-in | Maya (Meta Accelerator)', host: 'Gisselle', attendees: ['Gisselle', 'Jacqueline', 'Maya Stone'], type: 'checkin', typeSource: 'Calendar title', state: 'Scheduled', stateNote: 'Builds Oct 12, 7:00 PM.',
    brief: {
      thirty: ['Maya is stretched and stuck choosing a creative.', 'Must achieve: one concrete next step.', 'Risk: her Oct 5 email still has no reply.'],
      since: [{ text: 'Missed Oct 1 office hours; Oct 8 unclear.', date: '2026-10-08' }, { text: 'Asked for feedback on one example.', date: '2026-10-05', sourceId: 'willow-email' }],
      asks: [{ quote: 'Could someone give me feedback on one example so I can get moving again?', who: 'Maya Stone', date: '2026-10-05', sourceId: 'willow-email' }],
      agenda: [{ item: 'What’s getting in the way', why: 'Her email' }, { item: 'Pick one creative to start from', why: 'Her open ask' }, { item: 'Confirm the next office hours', why: 'Attendance drifting' }],
      questions: [], watch: ['Don’t treat missed sessions as unhappiness.'],
      typeBlock: [{ label: 'Programme', value: 'Meta Ads Accelerator · week 13 of 16' }, { label: 'Attendance', value: 'Sep 24 attended · Oct 1 missed · Oct 8 unknown' }],
      limits: ['Shared programme channel: only Maya’s messages used'], more: {},
    } },
  { id: 'call-magnolia', clientId: 'magnolia', date: '2026-10-14', time: '13:00', duration: '60 min', title: 'Google Office Hours', host: 'Carmen', attendees: ['Carmen', 'Gisselle', 'Tessa Ruiz', '+5 members'], type: 'office-hours', typeSource: 'Calendar title', state: 'Scheduled', stateNote: 'Builds Oct 13, 7:00 PM.',
    brief: {
      thirty: ['Group session; Tessa (Magnolia) is bringing keyword groups.', 'Must achieve: review intent vs page for each member who asks.', 'Risk: none flagged.'],
      since: [{ text: 'Tessa finished her page revision and grouped keywords.', date: '2026-10-06', sourceId: 'magnolia-slack' }],
      asks: [{ quote: 'Looking forward to feedback on whether the intent matches the page.', who: 'Tessa Ruiz', date: '2026-10-06', sourceId: 'magnolia-slack' }],
      agenda: [{ item: 'Quick wins from last week', why: 'Template' }, { item: 'Tessa: keyword groups vs revised page', why: 'Her open ask' }, { item: 'One task each for next week', why: 'Template' }],
      questions: [], watch: [],
      typeBlock: [{ label: 'Members expected', value: 'Tessa Ruiz (Magnolia) · 5 others (not KB clients)' }, { label: 'Tessa', value: 'Attended last 3 sessions; asked for intent feedback' }],
      limits: ['Only each member’s own parts are shown'], more: {},
    } },
  { id: 'call-everly-x', clientId: 'everly', date: '2026-10-10', time: '10:00', duration: '15 min', title: 'Quick check-in | Everly Films', host: 'Ivy', attendees: ['Ivy', 'Nina Cole'], type: 'other', typeSource: 'Calendar title', state: 'Cancelled', stateNote: 'Cancelled by Nina on Oct 8. Brief not applicable; nothing deleted.', extra: true },
  { id: 'call-tessa-x', clientId: 'magnolia', date: '2026-10-10', time: '17:00', duration: '20 min', title: 'Catch up w/ Tessa', host: 'Carmen', attendees: ['Carmen', 'Tessa Ruiz'], type: 'office-hours', typeSource: 'Proposed by KB', state: 'Needs type', stateNote: 'Title doesn’t say the call type. KB proposes “Programme check-in (1:1)”.', extra: true,
    brief: { thirty: ['Tessa is engaged and attending.', 'Must achieve: agree her next campaign-building step.', 'Risk: none flagged.'], since: [{ text: 'Page revision done; keywords grouped.', date: '2026-10-06', sourceId: 'magnolia-slack' }], asks: [{ quote: 'Looking forward to feedback on whether the intent matches the page.', who: 'Tessa Ruiz', date: '2026-10-06', sourceId: 'magnolia-slack' }], agenda: [{ item: 'Feedback on keyword intent vs page', why: 'Her open ask' }, { item: 'Next campaign-building step', why: 'Programme week 19' }], questions: [], watch: [], typeBlock: [{ label: 'Programme', value: 'Google Search Accelerator · week 19' }, { label: 'Attendance', value: 'Last 3 sessions attended' }], limits: ['Shared programme channel: only Tessa’s messages used'], more: {} } },
];
export const UNMATCHED_EVENTS = kbLive.meta ? 0 : 2; // the intake snapshot holds client-matched events only
export const metaFor = (id: string) => CALL_META.find(c => c.id === id);

export interface Recap {
  id: string; clientId: string; date: string; title: string; type: CallTypeKey; transcript: boolean; sourceId?: string;
  decisions: string[]; commitments: { text: string; who: string; when: string; actionId?: string; status: 'In register' | 'Proposed' }[];
  answered: string[]; covered: { item: string; done: boolean }[]; email: string;
}

export const RECAPS: Recap[] = [
  { id: 'r-bloom-0930', clientId: 'bloom', date: '2026-09-30', title: 'September strategy call', type: 'strategy', transcript: true, sourceId: 'bloom-call',
    decisions: ['Get the revised page approved before changing any campaign messaging.'],
    commitments: [{ text: 'Send the revised landing page for approval', who: 'Jacqueline', when: 'Oct 8', actionId: 'a1', status: 'In register' }, { text: 'Approve the autumn gallery page', who: 'Sarah Mitchell', when: 'After receiving the page', actionId: 'a3', status: 'In register' }],
    answered: ['Whether the new gallery could go live before the page (answered: after approval)'],
    covered: [{ item: 'Gallery status', done: true }, { item: 'Page approval process', done: true }, { item: 'Creative refresh timing', done: true }, { item: 'September lead results', done: false }],
    email: 'Hi Sarah,\n\nThank you for today! A quick recap:\n\n• We’ll send the revised landing page with the new gallery for your approval by October 8.\n• Once it’s approved, we’ll use it as the starting point for the next creative refresh.\n\nWe didn’t get to the September lead results, so I’ll include a short summary with the page.\n\nTalk soon,\nWhitney' },
  { id: 'r-rose-1002', clientId: 'rosewood', date: '2026-10-02', title: 'Follow-up sequence review', type: 'strategy', transcript: true, sourceId: 'rosewood-call',
    decisions: ['Revised follow-up sequence approved.', 'Next focus: winter-tour messaging.'],
    commitments: [{ text: 'Run a test inquiry before marking the sequence complete', who: 'Danielle', when: 'Oct 7', actionId: 'a4', status: 'In register' }, { text: 'Send the winter gallery', who: 'Dana Whitfield', when: 'Not set', status: 'Proposed' }],
    answered: ['Whether the new sequence sounds like Rosewood (yes, approved)'],
    covered: [{ item: 'Sequence review', done: true }, { item: 'Approval', done: true }, { item: 'Winter plans', done: true }],
    email: 'Hi Dana,\n\nThanks for today, and for approving the new follow-up sequence!\n\n• Danielle will run a test inquiry before we switch it on fully.\n• Next, we’ll focus on the winter-tour message. Could you send over the winter gallery when it’s ready?\n\nBest,\nWhitney' },
  { id: 'r-willow-0924', clientId: 'willow', date: '2026-09-24', title: 'Meta office hours · creative review', type: 'office-hours', transcript: true, sourceId: 'willow-fathom',
    decisions: ['Start with one clear planning moment for the next creative.'],
    commitments: [{ text: 'Send one mountain-wedding creative example', who: 'Maya Stone', when: 'No date agreed', actionId: 'a12', status: 'In register' }],
    answered: [], covered: [{ item: 'Maya’s creative angles', done: true }],
    email: 'Hi Maya,\n\nGreat session today! As discussed, pick one of your mountain wedding examples and send it over, and we’ll work through the hook together next time.\n\nJacqueline' },
  { id: 'r-meta-1008', clientId: 'willow', date: '2026-10-08', title: 'Meta office hours', type: 'office-hours', transcript: false,
    decisions: [], commitments: [], answered: [], covered: [], email: '' },
];

export const TIMEZONES: Record<string, { label: string; offsetFromIST: number }> = {
  bloom: { label: 'Austin (CDT)', offsetFromIST: -10.5 }, rosewood: { label: 'Charleston (EDT)', offsetFromIST: -9.5 }, willow: { label: 'Asheville (EDT)', offsetFromIST: -9.5 },
  everly: { label: 'Nashville (CDT)', offsetFromIST: -10.5 }, harbor: { label: 'Portland, ME (EDT)', offsetFromIST: -9.5 }, magnolia: { label: 'Denver (MDT)', offsetFromIST: -11.5 },
};
