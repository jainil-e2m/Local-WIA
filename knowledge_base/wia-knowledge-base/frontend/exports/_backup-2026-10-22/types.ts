export type ViewId = 'dashboard' | 'clients' | 'calls' | 'actions' | 'health' | 'money' | 'sources' | 'settings';
export type ClientTab = 'now' | 'profile' | 'history' | 'brief' | 'commitments' | 'meetings' | 'money' | 'attendance';
export type Health = 'On track' | 'Needs attention' | 'Settling in';
export type SourceKind = 'Zoom' | 'Slack' | 'Gmail' | 'Drive' | 'ClickUp' | 'HighLevel' | 'Calendar' | 'Fathom';
export type Tone = 'blue' | 'green' | 'amber' | 'rose' | 'neutral' | 'gold';

export interface Client {
  id: string;
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

export interface Action {
  id: string;
  clientId: string;
  title: string;
  owner: string;
  due: string;
  status: 'Open' | 'In progress' | 'Done' | 'Verified';
  side: 'WIA' | 'Client';
  acknowledged: boolean;
  sourceId: string;
  note: string;
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
  lane: 'Onboarding' | 'Communication' | 'Meetings' | 'Commitments' | 'Work delivered';
  title: string;
  detail: string;
  sourceId: string;
}

export interface WorkspaceProps {
  actions: Action[];
  navigate: (view: ViewId) => void;
  openClient: (id: string, tab?: ClientTab) => void;
  openCall: (id: string) => void;
  showEvidence: (id: string) => void;
  updateAction: (id: string, patch: Partial<Action>) => void;
  notify: (message: string) => void;
}
