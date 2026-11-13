import type { EngagementEvent } from './types';
import type { Milestone, Moment } from './records';

/*
 * Sample History data (fictional), in the shape the KB serves. Three layers:
 * - ACTIVITY: every source record folded into one event per thing that happened (rules, no AI):
 *   a conversation on one day, one meeting (invite + recording + transcript), a task created, tasks finished that day.
 * - MILESTONES: account turning points from fixed rules (registry, calendar titles, ClickUp onboarding lists),
 *   or from the KB's reading of calls and messages.
 * - MOMENTS: the 5–15 events that explain the account, chosen by the KB's history reading (AI), each cited.
 */
type Opt = Partial<Pick<EngagementEvent, 'count' | 'from' | 'state' | 'sourceId'>>;
let n = 0;
const e = (clientId: string, date: string, lane: EngagementEvent['lane'], title: string, detail: string, o: Opt = {}): EngagementEvent =>
  ({ id: `act-${clientId}-${++n}`, clientId, date, lane, title, detail, sourceId: o.sourceId || '', ...o });

export const ACTIVITY: EngagementEvent[] = [
  // Bloom Manor: active retainer; the page approval is now the critical path.
  e('bloom', '2026-03-28', 'Communication', 'Inquiry about Elevate', 'Gmail · 3 messages · Sarah, Whitney', { count: 3, from: 'Both' }),
  e('bloom', '2026-04-06', 'Meetings', 'Onboarding call', 'Zoom · video in Drive, no transcript', { state: 'no-transcript' }),
  e('bloom', '2026-04-06', 'Onboarding', '48 onboarding tasks set up', 'ClickUp · Bloom Manor · Onboarding', { count: 48 }),
  e('bloom', '2026-04-09', 'Onboarding', 'Questionnaire returned', 'Drive · Onboarding questionnaire', { sourceId: 'bloom-drive' }),
  e('bloom', '2026-04-14', 'Onboarding', 'Ad accounts connected', 'ClickUp · 3 tasks done', { count: 3 }),
  e('bloom', '2026-05-01', 'Onboarding', 'Onboarding checklist complete', 'ClickUp · 48 of 48 done'),
  e('bloom', '2026-05-12', 'Work delivered', 'Google and Meta campaigns launched', 'ClickUp · 2 tasks done', { count: 2 }),
  e('bloom', '2026-06-03', 'Meetings', 'June strategy call', 'Zoom · transcript'),
  e('bloom', '2026-06-04', 'Commitments', 'Refresh the gallery creative for autumn', 'ClickUp · Jacqueline · due Sep 30'),
  e('bloom', '2026-07-03', 'Work delivered', 'June report sent', 'Gmail · Ivy'),
  e('bloom', '2026-08-05', 'Communication', 'Gallery photo selection', 'Slack · 6 messages · Sarah, Jacqueline', { count: 6, from: 'Both' }),
  e('bloom', '2026-08-14', 'Work delivered', 'Meta lead tracking fixed', 'Slack · Carmen'),
  e('bloom', '2026-09-02', 'Meetings', 'August strategy call', 'Zoom · transcript'),
  e('bloom', '2026-09-30', 'Meetings', 'September strategy call', 'Zoom · transcript', { sourceId: 'bloom-call' }),
  e('bloom', '2026-09-30', 'Commitments', 'Send the revised landing page for approval', 'From the Sep 30 call · Jacqueline · due Oct 8', { state: 'missed', sourceId: 'bloom-call' }),
  e('bloom', '2026-10-03', 'Work delivered', 'Autumn gallery delivered', 'ClickUp · Jacqueline'),
  e('bloom', '2026-10-05', 'Communication', 'Gallery preview', 'Slack · 2 messages · Jacqueline, Sarah', { count: 2, from: 'Both' }),
  e('bloom', '2026-10-07', 'Commitments', 'Landing page moved to In progress', 'ClickUp · Jacqueline', { sourceId: 'bloom-task' }),
  e('bloom', '2026-10-08', 'Communication', 'Inquiry-quality question before the call', 'Gmail · 1 message · Sarah', { count: 1, from: 'Client', sourceId: 'bloom-email' }),

  // Rosewood Estate: Elevate since Feb, LeadLock since Mar; one recurring calendar issue.
  e('rosewood', '2026-02-12', 'Meetings', 'Onboarding call', 'Fathom · transcript'),
  e('rosewood', '2026-02-12', 'Onboarding', '52 onboarding tasks set up', 'ClickUp · Rosewood · Onboarding', { count: 52 }),
  e('rosewood', '2026-02-20', 'Onboarding', 'Questionnaire returned', 'Drive · Onboarding questionnaire', { sourceId: 'rosewood-drive' }),
  e('rosewood', '2026-03-01', 'Onboarding', 'LeadLock kickoff call', 'Fathom · transcript'),
  e('rosewood', '2026-03-18', 'Work delivered', 'LeadLock follow-up sequence live', 'ClickUp · Danielle · 4 tasks done', { count: 4 }),
  e('rosewood', '2026-03-20', 'Onboarding', 'Onboarding checklist complete', 'ClickUp · 52 of 52 done'),
  e('rosewood', '2026-06-05', 'Meetings', 'June strategy call', 'Fathom · transcript'),
  e('rosewood', '2026-09-04', 'Meetings', 'Monthly strategy call', 'Fathom · summary only', { state: 'no-transcript' }),
  e('rosewood', '2026-09-18', 'Communication', 'Duplicate texts to couples', 'Gmail · 4 messages · Dana, Danielle', { count: 4, from: 'Both' }),
  e('rosewood', '2026-09-19', 'Work delivered', 'Duplicate trigger removed', 'Slack · Danielle', { sourceId: 'rosewood-slack' }),
  e('rosewood', '2026-10-02', 'Meetings', 'Follow-up sequence review', 'Zoom · transcript', { sourceId: 'rosewood-call' }),
  e('rosewood', '2026-10-02', 'Commitments', 'Run a test inquiry before go-live', 'From the Oct 2 call · Danielle · due Oct 7', { sourceId: 'rosewood-call' }),
  e('rosewood', '2026-10-06', 'Communication', 'Tour link shows the wrong times again', 'Gmail · 2 messages · Dana, Danielle', { count: 2, from: 'Both' }),
  e('rosewood', '2026-10-07', 'Work delivered', 'Test inquiry passed', 'Slack · Danielle', { sourceId: 'rosewood-slack' }),
  e('rosewood', '2026-10-07', 'Commitments', 'Winter-tour draft for the next call', 'Slack · Jacqueline', { sourceId: 'rosewood-slack' }),
  e('rosewood', '2026-10-08', 'Communication', 'Thanks, and a request to see the winter draft', 'Slack · 1 message · Dana', { count: 1, from: 'Client' }),

  // Willow & Pine: accelerator member who has gone quiet.
  e('willow', '2026-07-14', 'Onboarding', 'Joined the Meta Ads Accelerator', 'ClickUp · programme list'),
  e('willow', '2026-07-15', 'Meetings', 'Programme welcome session', 'Fathom · transcript'),
  e('willow', '2026-08-12', 'Meetings', 'Meta office hours', 'Fathom · transcript'),
  e('willow', '2026-09-24', 'Meetings', 'Office hours · creative review', 'Fathom · transcript', { sourceId: 'willow-fathom' }),
  e('willow', '2026-09-24', 'Commitments', 'Send one mountain-wedding creative example', 'From office hours · Maya · no date', { sourceId: 'willow-fathom' }),
  e('willow', '2026-10-05', 'Communication', 'Asked for feedback on one creative', 'Gmail · 1 message · Maya', { count: 1, from: 'Client', sourceId: 'willow-email' }),
  e('willow', '2026-10-08', 'Meetings', 'Meta office hours', 'Fathom · no transcript', { state: 'no-transcript' }),

  // Everly Films: steady creative work.
  e('everly', '2026-05-18', 'Meetings', 'Onboarding call', 'Zoom · transcript'),
  e('everly', '2026-05-20', 'Onboarding', 'Questionnaire returned', 'Drive · Brand questionnaire', { sourceId: 'everly-drive' }),
  e('everly', '2026-06-10', 'Work delivered', 'Campaigns launched', 'ClickUp · Ivy'),
  e('everly', '2026-10-01', 'Meetings', 'Portfolio & seasonal availability', 'Zoom · transcript', { sourceId: 'everly-call' }),
  e('everly', '2026-10-01', 'Commitments', 'Show spring dates in the inquiry journey', 'From the Oct 1 call · Ivy · due Oct 13', { sourceId: 'everly-call' }),
  e('everly', '2026-10-04', 'Communication', 'Remaining spring dates', 'Gmail · 2 messages · Ivy, Nina', { count: 2, from: 'Both' }),

  // Harbor House: onboarding, week 3.
  e('harbor', '2026-09-10', 'Communication', 'Inquiry about Elevate + LeadLock', 'Gmail · 5 messages · Elise, Whitney', { count: 5, from: 'Both' }),
  e('harbor', '2026-09-21', 'Meetings', 'Welcome & onboarding call', 'Fathom · summary only', { state: 'no-transcript' }),
  e('harbor', '2026-09-21', 'Onboarding', '61 onboarding tasks set up', 'ClickUp · Harbor House · Onboarding', { count: 61 }),
  e('harbor', '2026-09-27', 'Onboarding', 'Questionnaire returned', 'Drive · Onboarding questionnaire', { sourceId: 'harbor-drive' }),
  e('harbor', '2026-10-06', 'Meetings', 'Messaging & positioning interview', 'Zoom · transcript', { sourceId: 'harbor-call' }),
  e('harbor', '2026-10-06', 'Commitments', 'Confirm the CRM and its owner', 'From the interview · Elise · before the kickoff', { sourceId: 'harbor-call' }),
  e('harbor', '2026-10-07', 'Communication', 'Interview recap and CRM question', 'Gmail · 3 messages · Whitney, Elise', { count: 3, from: 'Both' }),
  e('harbor', '2026-10-08', 'Onboarding', 'Domain & DNS task closed (2 checks unticked)', 'ClickUp · Danielle'),
  e('harbor', '2026-10-08', 'Communication', 'Kickoff should cover who sets up what', 'Gmail · 2 messages · Elise, Danielle', { count: 2, from: 'Both', sourceId: 'harbor-email' }),

  // Magnolia Events: accelerator member on track.
  e('magnolia', '2026-06-02', 'Onboarding', 'Joined the Google Search Accelerator', 'ClickUp · programme list'),
  e('magnolia', '2026-06-03', 'Meetings', 'Programme welcome session', 'Fathom · transcript'),
  e('magnolia', '2026-08-18', 'Work delivered', 'First search campaign live (run by Tessa)', 'Slack · Tessa'),
  e('magnolia', '2026-10-06', 'Communication', 'Page revision and keyword groups done', 'Slack · 2 messages · Tessa, Carmen', { count: 2, from: 'Both', sourceId: 'magnolia-slack' }),
  e('magnolia', '2026-10-07', 'Meetings', 'Google office hours', 'Fathom · transcript'),
];

export const MILESTONES: Milestone[] = [
  { id: 'ms-b1', clientId: 'bloom', date: '2026-04-02', label: 'Agreement signed', basis: 'Rule' },
  { id: 'ms-b2', clientId: 'bloom', date: '2026-04-06', label: 'Engagement started', basis: 'Rule' },
  { id: 'ms-b3', clientId: 'bloom', date: '2026-05-01', label: 'Onboarding complete', basis: 'Rule' },
  { id: 'ms-b4', clientId: 'bloom', date: '2026-05-12', label: 'Campaigns live', basis: 'KB reading' },
  { id: 'ms-r1', clientId: 'rosewood', date: '2026-02-12', label: 'Engagement started', basis: 'Rule' },
  { id: 'ms-r2', clientId: 'rosewood', date: '2026-03-18', label: 'LeadLock live', basis: 'KB reading' },
  { id: 'ms-r3', clientId: 'rosewood', date: '2026-03-20', label: 'Onboarding complete', basis: 'Rule' },
  { id: 'ms-w1', clientId: 'willow', date: '2026-07-14', label: 'Joined the programme', basis: 'Rule' },
  { id: 'ms-e1', clientId: 'everly', date: '2026-05-18', label: 'Engagement started', basis: 'Rule' },
  { id: 'ms-e2', clientId: 'everly', date: '2026-06-10', label: 'Campaigns live', basis: 'KB reading' },
  { id: 'ms-h1', clientId: 'harbor', date: '2026-09-19', label: 'Agreement signed', basis: 'Rule' },
  { id: 'ms-h2', clientId: 'harbor', date: '2026-09-21', label: 'Engagement started', basis: 'Rule' },
  { id: 'ms-m1', clientId: 'magnolia', date: '2026-06-02', label: 'Joined the programme', basis: 'Rule' },
];

export const MOMENTS: Moment[] = [
  { id: 'mo-b1', clientId: 'bloom', date: '2026-04-06', lane: 'Onboarding', kind: 'Milestone', title: 'Started with a messaging refresh, then a new inquiry journey', why: 'Set the order of work that every later decision follows.', sourceIds: ['bloom-drive'] },
  { id: 'mo-b2', clientId: 'bloom', date: '2026-05-12', lane: 'Work delivered', kind: 'Delivery', title: 'Google and Meta campaigns went live', why: 'Inquiry data starts here, so lead-quality questions can only look back to May.', sourceIds: [] },
  { id: 'mo-b3', clientId: 'bloom', date: '2026-09-30', lane: 'Meetings', kind: 'Decision', title: 'Page approval comes before any campaign messaging change', why: 'Every campaign change now waits on the page: it is the critical path.', sourceIds: ['bloom-call'] },
  { id: 'mo-b4', clientId: 'bloom', date: '2026-10-08', lane: 'Commitments', kind: 'Risk', title: 'The promised page date passed', why: 'Sarah was told Oct 8 and still hasn’t had it, while she’s asking harder questions.', sourceIds: ['bloom-task'] },
  { id: 'mo-b5', clientId: 'bloom', date: '2026-10-08', lane: 'Communication', kind: 'Client signal', title: 'Sarah asked what we know about inquiry quality', why: 'The first time she has questioned lead quality; expect it to lead the next call.', sourceIds: ['bloom-email'] },

  { id: 'mo-r1', clientId: 'rosewood', date: '2026-03-18', lane: 'Work delivered', kind: 'Milestone', title: 'LeadLock follow-up went live', why: 'From here every inquiry gets an automatic first reply; LeadLock data starts in March.', sourceIds: [] },
  { id: 'mo-r2', clientId: 'rosewood', date: '2026-09-18', lane: 'Communication', kind: 'Risk', title: 'Couples got duplicate texts', why: 'Dana’s first complaint; fixed in a day, and it’s why she now asks for a test inquiry.', sourceIds: ['rosewood-slack'] },
  { id: 'mo-r3', clientId: 'rosewood', date: '2026-10-02', lane: 'Meetings', kind: 'Decision', title: 'Revised follow-up sequence approved', why: 'Dana said it finally sounds like Rosewood; the tone is now settled.', sourceIds: ['rosewood-call'] },
  { id: 'mo-r4', clientId: 'rosewood', date: '2026-10-02', lane: 'Meetings', kind: 'Decision', title: 'Winter tours are the next focus', why: 'Sets the agenda for the next call and the winter campaign.', sourceIds: ['rosewood-call'] },
  { id: 'mo-r5', clientId: 'rosewood', date: '2026-10-06', lane: 'Communication', kind: 'Risk', title: 'Tour-time bug reported a second time', why: 'A repeat problem on the booking page couples use; it needs a confirmed fix.', sourceIds: [] },

  { id: 'mo-w1', clientId: 'willow', date: '2026-09-24', lane: 'Meetings', kind: 'Decision', title: 'Start from one clear planning moment', why: 'Jacqueline’s advice that unblocks Maya’s next creative.', sourceIds: ['willow-fathom'] },
  { id: 'mo-w2', clientId: 'willow', date: '2026-10-05', lane: 'Communication', kind: 'Client signal', title: 'Maya asked for help choosing a creative', why: 'She’s stuck and has missed two office hours: a personal check-in is due.', sourceIds: ['willow-email'] },

  { id: 'mo-e1', clientId: 'everly', date: '2026-10-01', lane: 'Meetings', kind: 'Decision', title: 'Portfolio edit approved; spring dates go into the inquiry journey', why: 'The next deliverable and the tone to keep (not promotional).', sourceIds: ['everly-call'] },

  { id: 'mo-h1', clientId: 'harbor', date: '2026-09-21', lane: 'Onboarding', kind: 'Milestone', title: 'Onboarding started for Elevate and LeadLock together', why: 'Two setups run at once, so the order of steps matters.', sourceIds: [] },
  { id: 'mo-h2', clientId: 'harbor', date: '2026-10-06', lane: 'Meetings', kind: 'Risk', title: 'Nobody knows which CRM they use or who owns it', why: 'Blocks the LeadLock kickoff until Elise confirms.', sourceIds: ['harbor-call'] },
  { id: 'mo-h3', clientId: 'harbor', date: '2026-10-08', lane: 'Communication', kind: 'Client signal', title: 'Elise wants the split of work spelled out', why: 'The kickoff must say what WIA sets up and what stays with her team.', sourceIds: ['harbor-email'] },

  { id: 'mo-m1', clientId: 'magnolia', date: '2026-10-06', lane: 'Work delivered', kind: 'Delivery', title: 'Tessa finished her page revision and keyword groups', why: 'She is on track and ready for search-intent feedback.', sourceIds: ['magnolia-slack'] },
];
