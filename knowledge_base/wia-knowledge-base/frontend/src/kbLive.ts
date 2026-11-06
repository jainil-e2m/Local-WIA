import { createElement } from 'react';
import kb from '@kb-live';
import { CALLS, CLIENTS, CONNECTORS, EVENTS, EVIDENCE, INITIAL_ACTIONS, INVOICES, PROGRAMME_TASKS, REVIEW_ITEMS, SLACK_CHANNELS, SYNC_STATUS } from './data';
import { RECORDS, type ClientRecord, type Milestone, type Moment } from './records';
import { MILESTONES, MOMENTS } from './story';
import { ASSESSMENTS, DIMENSIONS, VOICE, WAITING, type Assessment, type DimId } from './health';
import { PULSE } from './health-v2';
import { CALL_META, RECAPS, TIMEZONES, type CallMeta, type Recap } from './calls';
import { PERFORMANCE } from './performance';
import { AGREEMENTS, FAILED_PAYMENTS, INVOICES2, PLANS, UNMATCHED } from './finance';
import { LOGOS, type ClientLogo } from './logos';
import type { Action, Call, Client, EngagementEvent, Evidence, ReviewItem } from './types';

/*
 * Real KB data. Production (`npm run build:live`): '@kb-live' is filled from GET /api/v1/portfolio before this
 * module runs (main.tsx). Local WIA export (`npm run export:wia`): it is src/kb-live.local.json, written by
 * `python -m backend.scripts.export_frontend_snapshot` (real client data, gitignored). Every other build gets an
 * empty stub and this module does nothing.
 *
 * When data is present, every fictional dataset is replaced in place, so no sample client, quote, invoice or
 * health reading survives next to real records. Fields that need AI extraction arrive as explicit
 * "Not extracted yet" states from the snapshot; this module adds only matching "not assessed" defaults.
 */
export interface KbLive {
  meta?: { asOf: string; generatedAt: string; windowStart: string | null; windowEnd: string; note: string };
  clients?: Client[];
  evidence?: Evidence[];
  actions?: Action[];
  calls?: Call[];
  callMeta?: CallMeta[];
  /** Last-meeting recaps from the AI meeting digest (empty while the AI is off). */
  recaps?: Recap[];
  /** AI-proposed actions waiting in Needs review (empty while the AI is off). */
  reviewItems?: ReviewItem[];
  /** History: account milestones (rules) and the moments that shaped the account (AI; empty while off). */
  milestones?: Milestone[];
  moments?: Moment[];
  events?: EngagementEvent[];
  records?: Record<string, ClientRecord>;
  slackChannels?: Record<string, { channel: string; audience: 'client' | 'programme' }>;
  timezones?: Record<string, { label: string; offsetFromIST: number }>;
  connectors?: { name: string; kind: string; detail: string; records: number; state: string; note: string }[];
  syncStatus?: { source: string; at: string }[];
  /** P10: logo chosen from the client's Drive brand files; bytes embedded only in this local export. */
  /** `scale` enlarges logos with wide padding; `source` names where a logo came from when it isn't the Drive brand folder. */
  /** `dataUri` in the local export; `src` (the logo route) in production. */
  logos?: Record<string, { dataUri?: string; src?: string; recordId?: string; file: string; folder: string; extracted: string; scale?: number; source?: ClientLogo['source'] }>;
}

const replace = <T>(target: T[], items: T[] = []) => { target.splice(0, target.length, ...items); };
const replaceMap = <T>(target: Record<string, T>, items: Record<string, T> = {}) => {
  Object.keys(target).forEach(key => delete target[key]);
  Object.assign(target, items);
};

const notAssessed = (clientId: string): Assessment => ({
  clientId, assessedOn: kb.meta!.asOf, period: 'Not assessed',
  dims: Object.fromEntries(DIMENSIONS.map(d => [d.id, {
    state: 'Unavailable', level: 'unavailable',
    drivers: [{ text: 'Not assessed: health readings need extraction (Stage 3).', kind: 'Fact' }],
  }])) as Assessment['dims'] & Record<DimId, unknown>,
  why: 'Not assessed yet. This preview holds source records only.',
  nextStep: '',
  history: Array(8).fill('Unassessed'),
  coverage: ['Health is not assessed in the intake test'],
});

if (kb.meta) {
  replace(CLIENTS, kb.clients);
  replace(EVIDENCE, kb.evidence);
  replace(INITIAL_ACTIONS, kb.actions);
  replace(CALLS, kb.calls);
  replace(EVENTS, kb.events);
  replace(MILESTONES, kb.milestones);
  replace(MOMENTS, kb.moments);
  replace(CALL_META, kb.callMeta);
  replace(SYNC_STATUS as { source: string; at: string }[], kb.syncStatus);
  replace(CONNECTORS as unknown as NonNullable<KbLive['connectors']>, kb.connectors);
  replaceMap(RECORDS, kb.records);
  replaceMap(SLACK_CHANNELS, kb.slackChannels);
  replaceMap(TIMEZONES, kb.timezones);

  // Not assessed / not extracted: keep the screens rendering without inventing readings.
  replace(ASSESSMENTS, (kb.clients ?? []).map(c => notAssessed(c.id)));
  replace(PULSE, (kb.clients ?? []).map(c => ({
    clientId: c.id, mood: Array(8).fill(null), delivery: Array(8).fill(0), readings: [], ourSide: [],
    story: 'Not assessed: tone readings need extraction.',
  })));
  replace(VOICE);
  replace(WAITING);
  replace(RECAPS, kb.recaps);
  replace(REVIEW_ITEMS, kb.reviewItems);
  replace(PROGRAMME_TASKS);
  replaceMap(PERFORMANCE);
  replaceMap(LOGOS, Object.fromEntries(Object.entries(kb.logos ?? {}).map(([id, l]) => [id, {
    mark: createElement('img', { src: l.src ?? l.dataUri, alt: `${l.file} (logo)`, style: { ['--portfolio-logo-scale' as string]: l.scale ?? 1, maxWidth: '78%', maxHeight: '70%', objectFit: 'contain' } }),
    tint: '#f6f7f4', source: l.source || 'Drive · Brand folder', file: l.folder ? `${l.folder} / ${l.file}` : l.file, extracted: l.extracted,
  }])));

  // Finance is out of the intake test (GHL billing is Stage 3); drop the fictional sample.
  replace(INVOICES);
  replace(AGREEMENTS);
  replace(INVOICES2);
  replace(PLANS);
  replace(UNMATCHED);
  replace(FAILED_PAYMENTS);
}
