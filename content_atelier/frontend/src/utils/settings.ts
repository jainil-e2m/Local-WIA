import type { Me } from '../api/schema';

/* The Settings screen's reading of GET /settings (6.F7; backend settings_api.py and settings_store.listing): what it shows
   read-only, the few settings an approver changes here, and the checks the backend makes before it stores a value, so a
   bad value is refused before the request and a refusal the screen did not foresee is shown in the backend's words. */

export interface SettingRow {
  key: string;
  value: unknown;
  /** Where the value comes from: `default` (the code), `env` (the server's environment) or `table` (a saved row). */
  source: string;
  default: unknown;
  type: string;
  description: string;
  updated_by?: string | null;
  updated_at?: string | null;
}

export interface SettingsListing { settings: SettingRow[]; problems: string[] }

/** Read the answer defensively: a row without a key is dropped, missing text reads as empty. */
export function readSettings(value: unknown): SettingsListing {
  const v = (value && typeof value === 'object' ? value : {}) as { settings?: unknown; problems?: unknown };
  const rows = Array.isArray(v.settings) ? v.settings : [];
  const text = (x: unknown) => typeof x === 'string' ? x : '';
  return {
    settings: rows.filter((row): row is Record<string, unknown> => !!row && typeof row === 'object' && typeof (row as { key?: unknown }).key === 'string')
      .map(row => ({
        key: row.key as string, value: row.value ?? null, source: text(row.source), default: row.default ?? null, type: text(row.type),
        description: text(row.description), updated_by: typeof row.updated_by === 'string' ? row.updated_by : null,
        updated_at: typeof row.updated_at === 'string' ? row.updated_at : null,
      })),
    problems: Array.isArray(v.problems) ? v.problems.filter((p): p is string => typeof p === 'string') : [],
  };
}

/** Who may read and who may change settings, as the backend decides (settings_api.require_settings_admin): an editor or an
    approver reads, an approver changes. The server checks again; this only decides what to offer. */
export const canReadSettings = (me: Pick<Me, 'can'>) => me.can.edit_cards || me.can.decide;
export const canChangeSettings = (me: Pick<Me, 'can'>) => me.can.decide;

/** The settings an approver changes here: the duplicate cutoff and the weekly cycle's schedule. The Node relay forwards a
    change to these keys only (server/allowlist.mjs SETTABLE, kept equal by allowlist.test.mjs). */
export const EDITABLE_KEYS = ['matching.duplicate', 'cycle.timezone', 'cycle.weekday', 'cycle.hour'] as const;
export type EditableKey = typeof EDITABLE_KEYS[number];

export const WEEKDAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'] as const;

export const EDITABLE_LABELS: Record<EditableKey, { label: string; help: string }> = {
  'matching.duplicate': { label: 'Duplicate cutoff', help: 'How alike two cards of one week must be before the weaker one is folded into the stronger. Between 0.5 and 1; higher folds fewer.' },
  'cycle.timezone': { label: 'Time zone', help: 'The time zone the weekly cycle keeps, for example America/Chicago.' },
  'cycle.weekday': { label: 'Day', help: 'The day the week\'s collection closes and the cycle starts.' },
  'cycle.hour': { label: 'Hour', help: 'The hour, in that time zone, the week\'s collection closes.' },
};

const whole = (text: string, lo: number, hi: number, what: string): { value: number } | { error: string } => {
  const trimmed = text.trim();
  if (!/^\d+$/.test(trimmed)) return { error: `Choose ${what}.` };
  const value = Number(trimmed);
  return value >= lo && value <= hi ? { value } : { error: `${what[0].toUpperCase()}${what.slice(1)} must be between ${lo} and ${hi}.` };
};

/** Whether a time zone name is one the browser knows (the backend checks it against the time zone database too). */
export function knownTimeZone(name: string): boolean {
  try { new Intl.DateTimeFormat('en-US', { timeZone: name }); return true; } catch { return false; }
}

/** The value to send for a key, or why it is refused: the backend's own checks (settings_store.coerce with each key's
    type and bounds in DEFINITIONS: the cutoff a number from 0.5 to 1, the day 0 to 6, the hour 0 to 23, the zone a name). */
export function settingInput(key: EditableKey, text: string): { value: number | string } | { error: string } {
  const trimmed = text.trim();
  if (key === 'matching.duplicate') {
    if (!trimmed) return { error: 'Enter a cutoff, for example 0.86.' };
    const value = Number(trimmed);
    if (!Number.isFinite(value)) return { error: 'The cutoff is a number, for example 0.86.' };
    return value >= 0.5 && value <= 1 ? { value } : { error: 'The cutoff must be between 0.5 and 1.' };
  }
  if (key === 'cycle.weekday') return whole(trimmed, 0, 6, 'a day');
  if (key === 'cycle.hour') return whole(trimmed, 0, 23, 'an hour');
  if (!trimmed) return { error: 'Enter a time zone, for example America/Chicago.' };
  return knownTimeZone(trimmed) ? { value: trimmed } : { error: `${trimmed} is not a time zone name. Use one like America/Chicago.` };
}

/** A value as the screen writes it in its field. */
export const fieldText = (value: unknown) => value === null || value === undefined ? '' : String(value);

// ---- the read-only parts

const MODEL_LABELS: Record<string, string> = {
  'models.default': 'Every other step', 'models.moment_extraction': 'Scenes from the calls', 'models.angle_generation': 'Card writing',
  'models.card_verification': 'Card check', 'models.context_mining': 'Learning from edits', 'models.document_classification': 'Call sorting',
  'models.brief': 'Brief writing', 'models.brief_review': 'Brief review', 'models.pack_writer': 'Pack finishing', 'models.pack_review': 'Pack check',
};
const PROFILE_LABELS: Record<string, string> = {
  'prompts.profile.strategist': 'Card writing', 'prompts.profile.extraction': 'Scenes from the calls', 'prompts.profile.card_verification': 'Card check',
  'prompts.profile.brief': 'Brief format', 'prompts.profile.brief_writer': 'Brief writing', 'prompts.profile.pack_finish': 'Pack finishing',
  'prompts.profile.pack_check': 'Pack check', 'prompts.profile.pack_repair': 'Pack repair', 'prompts.profile.pack_caption': 'Caption after recording',
  'prompts.profile.pack_refinish': 'Finishing again with a permission',
};
const BUDGET_LABELS: Record<string, string> = {
  cycle: 'Weekly cycle', briefs: 'Briefs', refreshes: 'Refreshes', embedding: 'Search encoding', extraction: 'Scenes from new calls',
  context_mining: 'Learning from edits', packs: 'Content packs',
};

export interface LabelledSetting { label: string; row: SettingRow }
export interface BudgetLine { purpose: string; label: string; usd?: SettingRow; calls?: SettingRow }

const words = (s: string) => s.replaceAll('_', ' ');

/** The listing as the screen's parts: the model and prompt profile of each step, the knowledge-base pin, the standing weekly
    budgets (or `uncapped`: no weekly limits at all, budgets.uncapped), and the rows of the editable settings. A key the backend
    adds later shows under its own name. */
export function settingsView(listing: SettingsListing) {
  const rows = listing.settings;
  const models = rows.filter(row => /^models\.[a-z_]+$/.test(row.key) && row.type.startsWith('str'))
    .map(row => ({ label: MODEL_LABELS[row.key] ?? words(row.key.slice('models.'.length)), row }));
  const profiles = rows.filter(row => row.key.startsWith('prompts.profile.'))
    .map(row => ({ label: PROFILE_LABELS[row.key] ?? words(row.key.slice('prompts.profile.'.length)), row }));
  const budgets: BudgetLine[] = rows.filter(row => row.key.startsWith('budgets.weekly_usd.')).map(row => {
    const purpose = row.key.slice('budgets.weekly_usd.'.length);
    return { purpose, label: BUDGET_LABELS[purpose] ?? words(purpose), usd: row, calls: rows.find(r => r.key === `budgets.weekly_calls.${purpose}`) };
  });
  const editable = Object.fromEntries(EDITABLE_KEYS.map(key => [key, rows.find(row => row.key === key)])) as Record<EditableKey, SettingRow | undefined>;
  const uncapped = rows.find(row => row.key === 'budgets.uncapped')?.value === true;
  return { models, profiles, knowledgeBase: rows.find(row => row.key === 'knowledge_base.version') ?? null, budgets, uncapped, editable };
}

/** Where a value comes from, in words. */
export function sourceText(row: Pick<SettingRow, 'source' | 'updated_by' | 'updated_at'>): string {
  if (row.source === 'table') {
    const on = row.updated_at ? new Date(row.updated_at) : null;
    const date = on && Number.isFinite(on.getTime()) ? ` on ${on.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })}` : '';
    return `Set${row.updated_by ? ` by ${row.updated_by}` : ''}${date}`;
  }
  if (row.source === 'env') return 'Set in the server\'s environment';
  return 'The built-in default';
}
