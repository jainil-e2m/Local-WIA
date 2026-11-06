import type { ContextItem, ItemKind, Permission, Visibility } from '../api/types';

/* Plain-word labels for the context screens (L.F1 to L.F3), written for a non-technical reviewer (R50):
   no item IDs, hashes, keys or pipeline vocabulary reach the screen. */

export const KIND_ORDER: ItemKind[] = ['offer', 'price', 'roster_member', 'cta', 'result', 'process_step', 'campaign', 'content_plan_entry',
  'performance_note', 'rule', 'exemplar', 'belief', 'audience_phrase', 'format_rule'];

const KINDS: Record<ItemKind, [string, string]> = {
  rule: ['Rule', 'Rules'], exemplar: ['Writing example', 'Writing examples'], offer: ['Offer', 'Offers'], price: ['Price', 'Prices'],
  roster_member: ['Team member', 'Team'], result: ['Result', 'Results'], cta: ['Call to action', 'Calls to action'],
  process_step: ['Process step', 'Processes'], belief: ['Belief', 'Beliefs'], audience_phrase: ['Audience phrase', 'Audience phrases'],
  format_rule: ['Format rule', 'Format rules'], campaign: ['Campaign', 'Campaigns'], content_plan_entry: ['Content plan entry', 'Content plan'],
  performance_note: ['Performance note', 'Performance notes'],
};
export const kindLabel = (kind: string, plural = false) => KINDS[kind as ItemKind]?.[plural ? 1 : 0] ?? kind.replaceAll('_', ' ');

/** Rules, writing examples, beliefs, audience language and format change WIA's voice; Whitney decides them. */
export const IDENTITY_KINDS: ItemKind[] = ['rule', 'exemplar', 'belief', 'audience_phrase', 'format_rule'];

const DOCUMENTS: Record<string, string> = {
  team_roster: 'the team roster', offer_sheet: 'the offer sheet', rejection_rules: 'the rules', process_catalogue: 'the process catalogue',
  format_guide: 'the format guide', cta_catalogue: 'the calls to action', audience_language: 'the audience language',
  results_register: 'the results register', exemplars: 'the writing examples', belief_statements: 'the beliefs',
  content_plan: 'the content plan', recent_published: 'the recent published pieces', voice_guide: 'the voice guide',
  positioning: 'the positioning', ideal_client: 'the ideal client', content_strategy: 'the content strategy',
};
export const documentLabel = (key: string) => DOCUMENTS[key] ?? `the ${key.replaceAll('_', ' ')}`;
export const capitalise = (s: string) => s ? s[0].toUpperCase() + s.slice(1) : s;

const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
/** "2026-10-14" or an ISO timestamp as "14 October 2026"; anything else unchanged. Independent of the browser locale. */
export function formatDate(value: string | null | undefined): string {
  if (!value) return '';
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(value);
  if (!m || +m[2] < 1 || +m[2] > 12) return value;
  return `${+m[3]} ${MONTHS[+m[2] - 1]} ${m[1]}`;
}
export const todayIso = (now = new Date()) => `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;

export function validityLabel(from: string | null | undefined, to: string | null | undefined): string {
  if (from && to) return `In use from ${formatDate(from)} to ${formatDate(to)}`;
  if (from) return `In use from ${formatDate(from)}`;
  if (to) return `In use until ${formatDate(to)}`;
  return 'In use with no set dates';
}

export const STATUS_LABELS: Record<string, string> = { candidate: 'Waiting for review', confirmed: 'Confirmed', rejected: 'Rejected', retired: 'No longer used' };
export const VISIBILITY_LABELS: Record<Visibility, string> = { public: 'Can appear in public copy', internal: 'Internal: never stated in public copy' };
export const PERMISSION_LABELS: Record<Permission, string> = { published: 'WIA has published it', client_permission: 'The client gave permission', none: 'No permission to publish' };
export const sensitivityLabel = (s: string | null | undefined) => s === 'client_private' ? 'Client-private' : null;

/** Who said it: a person's name, or the model when the analysis wrote it. */
export function authorLabel(author: string | null | undefined): string {
  const a = (author || '').trim();
  if (!a) return 'Not recorded';
  if (/^model\b/i.test(a)) return 'The model (from WIA\'s material)';
  if (/^team \(/i.test(a)) return 'A WIA team member';
  return a;
}

const SOURCE_SECTION = (s?: string | null) => (s || '').replace(/^\s*\d+[.)]\s*/, '').trim();
const BRIEF_SECTIONS: Record<string, string> = { wia_perspective: 'WIA perspective', supporting_example: 'supporting example' };

/** Where a candidate came from, in words, and a small "sources" line of the conversations it cites. */
export function sourceInWords(item: Pick<ContextItem, 'source_kind' | 'source_detail' | 'statement_date'>): { from: string; sources: string | null; notes: string[] } {
  const d = item.source_detail || {};
  const when = d.date_text?.trim() || formatDate(item.statement_date);
  const section = SOURCE_SECTION(d.subsection ? `${d.section} · ${d.subsection}` : d.section);
  const join = (...parts: (string | null | undefined)[]) => parts.filter(Boolean).join(', ');
  const notes: string[] = [];
  let from: string;
  switch (item.source_kind) {
    case 'export_seed': from = `From ${join("Whitney's ChatGPT", section, when)}`; break;
    case 'knowledge_base': from = `From ${join("WIA's confirmed knowledge base", section)}`; break;
    case 'gate_decision':
      from = d.corrects ? `From a correction recorded at a gate decision${d.correction ? ` ("${d.correction.from}" should read "${d.correction.to}")` : ''}`
        : d.category ? `From ${d.decisions?.length || 'several'} gate decisions giving the same ${d.category} reason`
        : 'From a reason recorded at a gate decision';
      break;
    case 'approved_card': from = d.disposition === 'reframe' ? 'From a reframed card WIA approved' : 'From a card WIA approved'; break;
    case 'approved_brief': from = `From a brief WIA approved${d.section ? `, its ${BRIEF_SECTIONS[d.section] || d.section.replaceAll('_', ' ')} section` : ''}`; break;
    case 'brief_edit': from = `From ${d.diffs?.length || 'several'} edits to approved briefs${d.category ? ` (${d.category})` : ''}`; break;
    case 'published_piece': from = 'From a published piece linked to the brief behind it'; break;
    case 'performance_entry': from = 'From a performance figure'; break;
    case 'approver_entry': from = 'Entered by an approver'; break;
    case 'seed': from = 'From a founder seed marked "always true"'; break;
    case 'learning_loop': from = 'From the weekly learning from approved work'; break;
    default: from = 'From WIA\'s own material';
  }
  if (item.source_kind !== 'export_seed' && when) from += `, ${when}`;
  const cited = [...(d.conversations || []).map(c => `conversation ${c}`), ...(d.attachments || []), ...(d.chunks || []).map(c => `report ${c}`)];
  if (d.citations_from === 'section' && cited.length) notes.push('Sources cited by its section');
  if (d.citations_from === 'draft') notes.push('No conversation cited');
  if (d.date_from === 'section') notes.push('Date from its section');
  return { from, sources: cited.length ? `Sources: ${cited.join('; ')}` : null, notes };
}

/** What deciding a candidate would change in the next knowledge-base version. */
export function changeInWords(item: Pick<ContextItem, 'would_change' | 'kind'>): string {
  const w = item.would_change;
  if (!w) return '';
  const doc = documentLabel(w.document);
  const when = IDENTITY_KINDS.includes(item.kind) ? 'It takes effect once an approved version passes its benchmark.' : 'It takes effect when confirmed.';
  return `${w.replaces ? `Replaces the current entry in ${doc}.` : `Adds an entry to ${doc}.`} ${when}`;
}

/** A request error as the reviewer should read it, and whether the data is stale (409): the screen offers a reload, never forces one. */
export function contextError(e: unknown): { message: string; reload: boolean } {
  const status = (e as { status?: number })?.status;
  const message = e instanceof Error ? e.message : 'The request failed.';
  if (status === 503) return { message: 'The knowledge store is not set up yet.', reload: false };
  if (status === 403) return { message: 'Only an approver can do this. Ask the weekly owner, or Whitney for rules, writing examples and voice.', reload: false };
  if (status === 409) {
    const said = message.replace(/\s*\(ATELIER_[A-Z_]+\)/g, '').trim();
    return { message: /[.!?]$/.test(said) ? said : `${said}.`, reload: true };
  }
  return { message, reload: false };
}

/** Who can decide an entry the current reviewer cannot. */
export const whoDecides = (kind: string) => IDENTITY_KINDS.includes(kind as ItemKind)
  ? 'Only Whitney can decide rules, writing examples, beliefs, audience language and format.'
  : 'Only an approver can decide this. Ask the weekly owner.';

export const button = 'rounded-lg border border-[#E0DFE2] bg-white px-3 py-2 text-sm text-[#221E17] hover:bg-[#FAF9F7] disabled:opacity-40 disabled:cursor-not-allowed';
export const primaryButton = 'rounded-lg bg-[#5070FF] px-3 py-2 text-sm text-white hover:bg-[#3F5DE8] disabled:opacity-40 disabled:cursor-not-allowed';
export const field = 'block w-full rounded-lg border border-[#E0DFE2] bg-white p-2 mt-1 text-sm text-[#221E17]';

/** The failure as the knowledge screens word it, for the shared guarded action. */
export const contextFailure = (e: unknown) => contextError(e).message;
