export type ViewId = 'dashboard' | 'clients' | 'calls' | 'calls-v2' | 'actions' | 'actions-v2' | 'actions-v3' | 'health' | 'health-v2' | 'health-v3' | 'assistant' | 'money' | 'sources' | 'settings';

/** What an "Ask about this" button attaches to a Client 360 question. */
export interface AskContext { kind: 'client' | 'action' | 'call' | 'evidence' | 'health' | 'quote'; clientId: string; id?: string; label: string; quote?: string }
export type ClientTab = 'now' | 'profile' | 'history' | 'brief' | 'commitments' | 'meetings' | 'health' | 'support' | 'leads' | 'money' | 'attendance' | 'sources';
export type Health = 'On track' | 'Needs attention' | 'Settling in';
export type SourceKind = 'Zoom' | 'Slack' | 'Gmail' | 'Drive' | 'ClickUp' | 'HighLevel' | 'Calendar' | 'Fathom';
export type Tone = 'blue' | 'green' | 'amber' | 'rose' | 'neutral' | 'gold';

export interface Client {
  id: string;
  /** Optional stable asset ID from clientCovers.ts, suitable for live client records. */
  coverId?: string;
  name: string;
  initials: string;
  contact: string;
  email: string;
  location: string;
  service: string;
  type: 'retainer' | 'accelerator';
  category: string;
  health: Health;
  tone: Tone;
  since: string;
  summary: string;
  focus: string;
  sentiment: string;
  lastTouch: string;
  coverage: number;
  activity: number[];
  story: string;
  audience: string;
  differentiator: string;
  voice: string;
  goal: string;
  profileSource: string;
}

export interface Evidence {
  id: string;
  clientId: string;
  kind: SourceKind;
  title: string;
  date: string;
  author: string;
  excerpt: string;
  locator: string;
  tag: 'Decision' | 'Client signal' | 'Commitment' | 'Background' | 'Delivery';
}

export type ActionOrigin = 'ClickUp' | 'Slack' | 'Gmail' | 'Meeting' | 'Manual' | 'AI proposal';

export interface ActionHistoryEntry { date: string; text: string; at?: string; }

export interface Action {
  id: string;
  clientId: string;
  title: string;
  /** Empty string means the owner is unknown ("Unassigned"); never filled in by default. */
  owner: string;
  /** Empty string means no agreed deadline; an unknown deadline is never overdue. */
  due: string;
  status: 'Open' | 'In progress' | 'Blocked' | 'Done' | 'Verified';
  side: 'WIA' | 'Client';
  acknowledged: boolean;
  sourceId: string;
  note: string;
  origin?: ActionOrigin;
  /** Date the current owner was assigned; drives "awaiting acknowledgement". */
  assignedOn?: string;
  ackMethod?: string;
  lastActivity?: string;
  /** Flagged types (client-facing deliverables/fixes) need a separate Verified check. */
  verifyRequired?: boolean;
  actionType?: string;
  conflict?: string;
  quote?: string;
  clickupUrl?: string;
  completionBasis?: string;
  verification?: { by: string; check: string; date: string };
  history?: ActionHistoryEntry[];
  notes?: { by: string; date: string; text: string; at?: string }[];
  snoozedUntil?: string;
  snoozeReason?: string;
  /** Sample priority set by the team; missing on older saved actions (shown as Medium). */
  priority?: Priority;
  /** Date the action was completed (Done), when known. */
  completedOn?: string;
  /** A pending request to move the deadline; an admin approves or declines it. */
  deadlineRequest?: { to: string; reason: string; by: string; on: string };
  /** Last Slack ping from the Action Hub (preview only: nothing is posted). */
  slackPingedAt?: string;
  slackChannel?: string;
  /** Set when an internal programme task is shown in the action detail modal. */
  kind?: 'action' | 'programme';
  programme?: string;
  recurring?: string;
}

export type Priority = 'High' | 'Medium' | 'Low';

export type ReviewReason = 'Possibly stale' | 'Owner unclear' | 'Client match unclear' | 'Possible duplicate' | 'AI proposal' | 'Checklist incomplete';

export interface ReviewItem {
  id: string;
  reason: ReviewReason;
  explanation: string;
  title: string;
  clientId?: string;
  candidateClients?: string[];
  duplicateOf?: string;
  origin: ActionOrigin;
  author: string;
  date: string;
  quote: string;
  suggestedOwner?: string;
  suggestedDue?: string;
  side: 'WIA' | 'Client';
}

export interface ProgrammeTask {
  id: string;
  programme: string;
  title: string;
  owner: string;
  due: string;
  status: 'Open' | 'Done';
  recurring?: string;
  note?: string;
  history?: ActionHistoryEntry[];
  notes?: { by: string; date: string; text: string; at?: string }[];
  slackPingedAt?: string;
  slackChannel?: string;
}

export interface Call {
  id: string;
  clientId: string;
  date: string;
  time: string;
  duration: string;
  type: string;
  host: string;
  objective: string;
  context: string;
  needs: string[];
  agenda: string[];
  opportunity: string;
  sourceIds: string[];
}

export interface Invoice {
  id: string;
  clientId: string;
  amount: number;
  issued: string;
  due: string;
  status: 'Paid' | 'Open' | 'Overdue';
  paid?: string;
  reminders: string[];
  terms: string;
}

export interface EngagementEvent {
  id: string;
  clientId: string;
  date: string;
  lane: 'Onboarding' | 'Communication' | 'Meetings' | 'Commitments' | 'Work delivered' | 'Commercial';
  title: string;
  detail: string;
  sourceId: string;
  /** Items merged into this one event: messages in a conversation that day, tasks finished that day. */
  count?: number;
  /** Communication only: who wrote in this conversation. */
  from?: 'Client' | 'WIA' | 'Both';
  /** Meetings: held but no transcript. Commitments: its date passed while it was still open. */
  state?: 'no-transcript' | 'missed';
}

export interface WorkspaceProps {
  actions: Action[];
  navigate: (view: ViewId) => void;
  openClient: (id: string, tab?: ClientTab) => void;
  openCall: (id: string) => void;
  showEvidence: (id: string) => void;
  updateAction: (id: string, patch: Partial<Action>) => void;
  notify: (message: string) => void;
  /** Who the preview is shown as; drives My actions / My clients. */
  viewer: string;
  setViewer: (name: string) => void;
  /** Opens the Client 360 side panel, optionally about a record. */
  ask?: (context?: AskContext) => void;
}
