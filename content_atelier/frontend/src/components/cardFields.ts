/* The Gate 1 card's fields (3.B7/3.F2, common brief interface 3): one map from a card field's name to how the card screen
   shows and edits it. The card editor, the card's own display, the "kept as you wrote it" note and the refresh record are
   all built from this map, so a new contract field is shown and edited by adding one entry here.

   The map's order is Whitney's angle card (plan section 4.2): title; pillar and type; audience; the point (with strategist
   v7's tests on it); why this matters; WIA's expertise or process; evidence; guardrail and next step. A v7 card has `point`
   where v3 to v6 cards have `core_perspective` (E.B30); each card shows only the fields it carries.

   - label: the reviewer's word for the field (R50), never its stored name.
   - multiline: a text area rather than a line.
   - editable: the card screen offers it in the editor. Rank and the cited scenes are fixed by the run (gate_one.CARD_EDITABLE).
   - kind: 'text' (default), 'list' (one item per line), 'choice' (one of `options`) or 'record' (a few named `parts`: a
     choice, a tick box with its text, as strategist v7's {surprising, reason} and {takes_stance, stance}).
   - optional: may be left empty (sent as null; a list may be empty).
   - max: the most items a list may hold.
   - choices: a choice's words for the reviewer, by stored value.

   A field is shown and edited only when the card carries it, so a version 4 card is never sent version 5's series. */

export type CardFieldKind = 'text' | 'list' | 'choice' | 'record';
export interface CardPart {
  key: string;
  label: string;
  kind?: 'text' | 'choice' | 'check';
  options?: readonly string[];
  choices?: Record<string, string>;
  multiline?: boolean;
  optional?: boolean;
  // A text part needed only while this tick box is ticked (the stance, when the card takes one).
  neededWhen?: string;
  // How a tick box reads on the card, ticked and not.
  yes?: string;
  no?: string;
}
export interface CardField {
  label: string;
  multiline: boolean;
  editable: boolean;
  kind?: CardFieldKind;
  options?: readonly string[];
  choices?: Record<string, string>;
  parts?: readonly CardPart[];
  optional?: boolean;
  max?: number;
}

export const PILLARS = ['ATTRACT', 'WARM', 'CONVERT'] as const;
export const CONTENT_TYPES = ['polarizing_opinion', 'founder_forward', 'campaign_breakdown', 'trend', 'uvp', 'lightbulb_moment',
  'process_or_framework', 'behind_the_scenes', 'education', 'founder_story', 'solution_selling', 'social_proof'] as const;
// Strategist v7's enumerations (backend card_contracts.py), in the reviewer's words.
export const POINT_IS_ABOUT: Record<string, string> = {
  wia_belief: 'A WIA belief', wia_standard: 'A WIA standard', client_experience: 'A client’s experience',
  platform_or_tactic: 'A platform or tactic (not for public content)',
};
export const BUYERS: Record<string, string> = {
  elevate: 'An ELEVATE buyer', accelerators: 'An Ads Accelerators buyer', leadlock: 'A LeadLock buyer',
  established_owner: 'An established owner who already runs ads',
};
export const CTA_SLOTS: Record<string, string> = {
  offer_cta: 'The week’s offer CTA', soft_invitation: 'A soft invitation', none: 'No CTA',
};

export const CARD_FIELDS: Record<string, CardField> = {
  title: { label: 'Title', multiline: false, editable: true },
  pillar: { label: 'Pillar', multiline: false, editable: true, kind: 'choice', options: PILLARS },
  content_type: { label: 'Type', multiline: false, editable: true, kind: 'choice', options: CONTENT_TYPES },
  series: { label: 'Series', multiline: false, editable: true, optional: true },
  audience: { label: 'Who it is for', multiline: true, editable: true },
  // The point: v7's `point` with its tests (E.B30), or the older cards' core perspective.
  point: { label: 'The point', multiline: true, editable: true },
  core_perspective: { label: 'The point', multiline: true, editable: true },
  point_is_about: { label: 'What the point is about', multiline: false, editable: true, kind: 'choice',
    options: Object.keys(POINT_IS_ABOUT), choices: POINT_IS_ABOUT },
  surprise_for_experienced_advertiser: { label: 'Would it surprise an owner who already runs ads?', multiline: false, editable: true,
    kind: 'record', parts: [
      { key: 'surprising', label: 'Yes, it would surprise them', kind: 'check', yes: 'Yes', no: 'No' },
      { key: 'reason', label: 'Why', multiline: true },
    ] },
  reader_takeaway: { label: 'What the reader comes away thinking', multiline: true, editable: true },
  reader_fit: { label: 'Who the reader is', multiline: false, editable: true, kind: 'record', parts: [
    { key: 'buyer', label: 'Buyer', kind: 'choice', options: Object.keys(BUYERS), choices: BUYERS },
    { key: 'buyer_statement', label: 'In Whitney’s words', multiline: true },
    { key: 'why', label: 'Why it fits', multiline: true },
  ] },
  belief_ref: { label: 'The belief it proves', multiline: false, editable: true },
  why_it_matters: { label: 'Why it matters', multiline: true, editable: true },
  wia_in_action: { label: 'WIA’s expertise or process', multiline: true, editable: true, optional: true },
  offer_connection: { label: 'Offer connection', multiline: true, editable: true, optional: true },
  evidence_points: { label: 'Evidence', multiline: true, editable: true, kind: 'list' },
  recurrence: { label: 'How often it came up this week', multiline: false, editable: true, optional: true },
  // Guardrail and next step: the brief writer reads the guardrail; the offer fit says which CTA the card takes.
  guardrail: { label: 'Editorial guardrail', multiline: true, editable: true },
  offer_fit: { label: 'Next step: the offer and CTA', multiline: false, editable: true, kind: 'record', parts: [
    { key: 'offer', label: 'Offer', optional: true },
    { key: 'cta_slot', label: 'CTA', kind: 'choice', options: Object.keys(CTA_SLOTS), choices: CTA_SLOTS },
    { key: 'calendar_note', label: 'Why it fits the offer calendar', multiline: true },
  ] },
  public_stance: { label: 'Public stance', multiline: false, editable: true, kind: 'record', parts: [
    { key: 'takes_stance', label: 'This card takes a public stance', kind: 'check', yes: 'Takes a public stance', no: 'No public stance' },
    { key: 'stance', label: 'The stance', multiline: true, optional: true, neededWhen: 'takes_stance' },
  ] },
  verify_before_publishing: { label: 'Verify before publishing', multiline: true, editable: true, kind: 'list', optional: true, max: 2 },
  why_selected: { label: 'Why it was chosen', multiline: true, editable: true },
  rank: { label: 'Rank', multiline: false, editable: false },
  moment_ids: { label: 'The scenes it cites', multiline: false, editable: false },
};

const words = (s: string) => s.replaceAll('_', ' ');
/** A field's label for the reviewer; a field missing from the map still reads as words, never as its stored name. */
export const cardFieldLabel = (name: string) => CARD_FIELDS[name]?.label ?? words(name);
/** A choice as the reviewer reads it ("behind the scenes", "A WIA belief"). */
export const choiceLabel = (value: string, choices?: Record<string, string>) => choices?.[value] ?? words(value);

type CardValues = Record<string, unknown>;
type Parts = Record<string, unknown>;
/** The editable fields this card carries, in the map's order. */
export const editableFields = (card: CardValues) => Object.entries(CARD_FIELDS).filter(([name, f]) => f.editable && name in card).map(([name]) => name);

/** A record field's value as the card shows it: each part in words, the tick boxes as their yes or no. */
export function recordText(field: CardField, value: unknown): string {
  const parts = (value && typeof value === 'object' ? value : {}) as Parts;
  return (field.parts ?? []).map(p => {
    const v = parts[p.key];
    if (p.kind === 'check') return v ? p.yes ?? p.label : p.no ?? `Not: ${p.label.toLowerCase()}`;
    if (v == null || v === '') return null;
    const text = p.kind === 'choice' ? choiceLabel(String(v), p.choices) : String(v);
    return `${p.label}: ${text}`;
  }).filter(Boolean).join(' · ');
}

const partKey = (name: string, part: string) => `${name}.${part}`;

/** What the editor's form holds for each field: text, with a list as one item per line and a record as one entry per part
    (`reader_fit.buyer`; a tick box as 'true' or 'false'). */
export function formValues(card: CardValues): Record<string, string> {
  return Object.fromEntries(editableFields(card).flatMap(name => {
    const value = card[name];
    const field = CARD_FIELDS[name];
    if (field.kind === 'record') {
      const parts = (value && typeof value === 'object' ? value : {}) as Parts;
      return (field.parts ?? []).map(p => [partKey(name, p.key), p.kind === 'check' ? String(!!parts[p.key]) : parts[p.key] == null ? '' : String(parts[p.key])]);
    }
    return [[name, Array.isArray(value) ? value.join('\n') : value == null ? '' : String(value)]];
  }));
}

/** Two values the same, whatever order their keys are stored in (the database keeps a record's keys in its own order). */
function same(a: unknown, b: unknown): boolean {
  const canonical = (v: unknown): unknown => Array.isArray(v) ? v.map(canonical)
    : v && typeof v === 'object' ? Object.fromEntries(Object.keys(v as Parts).sort().map(k => [k, canonical((v as Parts)[k])])) : v;
  return JSON.stringify(canonical(a)) === JSON.stringify(canonical(b));
}

/** A record field from its form entries, or what is wrong with it. Parts the map does not name are kept as they were. */
function recordValue(name: string, field: CardField, original: unknown, form: Record<string, string>): { value: Parts } | { error: string } {
  const value: Parts = { ...((original && typeof original === 'object' ? original : {}) as Parts) };
  for (const part of field.parts ?? []) {
    const raw = form[partKey(name, part.key)] ?? '';
    if (part.kind === 'check') { value[part.key] = raw === 'true'; continue; }
    const text = raw.trim();
    const needed = part.neededWhen ? form[partKey(name, part.neededWhen)] === 'true' : !part.optional;
    if (!text && needed) return { error: `${field.label}: ${part.label.toLowerCase()} cannot be empty.` };
    if (part.kind === 'choice' && part.options && !part.options.includes(text)) return { error: `${field.label}: choose the ${part.label.toLowerCase()}.` };
    value[part.key] = text || null;
  }
  return { value };
}

/** The changes the form makes to the card (PATCH /angles/{id}'s `changes`), or the reason they cannot be sent yet. Only a
    field whose value changed is sent, so the backend records exactly the fields this person wrote (content_body.person_edits). */
export function cardChanges(card: CardValues, form: Record<string, string>): { changes: Record<string, unknown> } | { error: string } {
  const changes: Record<string, unknown> = {};
  for (const name of editableFields(card)) {
    const field = CARD_FIELDS[name];
    const raw = form[name] ?? '';
    let value: unknown;
    if (field.kind === 'record') {
      const made = recordValue(name, field, card[name], form);
      if ('error' in made) return made;
      value = made.value;
    } else if (field.kind === 'list') {
      const items = raw.split('\n').map(line => line.trim()).filter(Boolean);
      if (!items.length && !field.optional) return { error: `${field.label} needs at least one line.` };
      if (field.max && items.length > field.max) return { error: `${field.label} holds at most ${field.max} items.` };
      value = items;
    } else {
      const text = raw.trim();
      if (!text && !field.optional) return { error: `${field.label} cannot be empty.` };
      if (field.kind === 'choice' && field.options && !field.options.includes(text)) return { error: `Choose a ${field.label.toLowerCase()}.` };
      value = text || null;
    }
    if (!same(value, card[name] ?? (field.kind === 'list' ? [] : null))) changes[name] = value;
  }
  return Object.keys(changes).length ? { changes } : { error: 'Nothing has changed yet.' };
}
