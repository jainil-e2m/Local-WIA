import type { PackFindingV2, PackLockV2, PackPieceV2, StoredPackV2, WeekPlanSlotV2 } from '../api/types';
import { plainBlocker } from './BriefReaderV2';
import { plainMessage } from '../utils/plainText';

/* The content pack's pieces as the screens read them (NP.F1, NP.F2; the content-packs plan, sections 4.2 and 5.7). A piece
   is in brief contract v4's leaf shape (backend packs/contracts_v2.py): its `content` holds the copy and `brief_copy` the
   approved brief's leaves, both addressed by the same dotted paths the Gate 2 editor writes, here relative to the piece's
   content (`caption.hook`, `slides[2].text`, `subject_options[0]`). This file turns a piece into labelled sections in the
   layout of the packs WIA saw on 20 October, into plain text for Copy and Copy all, and builds the bodies of the pack's
   writes. Nothing here describes an API shape by hand: the types are the generated ones. */

export type PieceKey = PackPieceV2['key'];
export type PackStateName = StoredPackV2['state'];

// ---- words ------------------------------------------------------------------------------------------------------------

export const STATE_LABELS: Record<PackStateName, string> = {
  finishing: 'Finishing', waiting: 'Waiting', in_review: 'Generated', ready_to_publish: 'Generated', superseded: 'Superseded',
};
/** What a state means when the API gives no reason of its own. */
export const STATE_HINTS: Record<PackStateName, string> = {
  finishing: 'The pack is being written. This page updates by itself.',
  waiting: 'The pack is waiting to continue.',
  in_review: 'Review the content checks, schedule each piece, and record publication when it goes out.',
  ready_to_publish: 'Review the content checks, schedule each piece, and record publication when it goes out.',
  superseded: 'A newer version of this pack exists.',
};
export const STATE_STYLES: Record<PackStateName, string> = {
  finishing: 'bg-[#EFF3FF] text-[#3F55C8] border-[#D1DBFF]',
  waiting: 'bg-amber-50 text-amber-900 border-amber-200',
  in_review: 'bg-[#F4F0FF] text-[#5B3FB8] border-[#E1D8FF]',
  ready_to_publish: 'bg-emerald-50 text-emerald-800 border-emerald-200',
  superseded: 'bg-slate-100 text-slate-600 border-slate-200',
};
// The kinds of Reel, as the mock and the export name them (contracts_v2.KIND_LABELS). A pack written since Round 2 has Reel 1 as
// the central story and Reels 2 and 3 each with a premise of its own; how a Reel is made is then said apart (PRODUCTION_LABELS).
export const KIND_LABELS: Record<string, string> = {
  story: 'face to camera, story', stance: 'face to camera, stance', broll_text: 'b-roll with on-screen text',
  central: 'Central story', second: 'Own premise', third: 'Own premise',
};
export const PRODUCTION_LABELS: Record<string, string> = { face_to_camera: 'Face to camera', on_screen_text: 'On-screen text' };
const PREMISE_KINDS = ['central', 'second', 'third'];
export const ORIGIN_LABELS: Record<PackPieceV2['origin'], string> = {
  brief: "The brief's copy", finished: 'Finished from the brief', written: 'Written by the system', not_written: 'Not written',
};
// The pack run's stages (contracts_v2.STAGES), for the progress shown while a pack is finishing.
export const STAGE_NAMES: Record<string, string> = {
  pack_assemble: 'Assembling the pieces from the brief', pack_finish: 'Finishing the copy', pack_check: 'Checking every statement against the call',
  pack_repair: 'Repairing flagged sentences', pack_recheck: 'Checking the repairs', pack_finalize: 'Final checks',
};
// What each step did to a line (contracts_v2.Change.kind), for "What the finisher changed".
export const CHANGE_LABELS: Record<string, string> = {
  finished: 'Finished', written: 'Written by the system', repaired: 'Repaired after the check', put_back: "The brief's sentence put back",
  restored_lock: 'A locked line put back word for word', kept_brief_carousel: "The brief's carousel kept", missed_patch: 'A repair that did not apply',
  edited: 'Edited by a person', reverted: "The brief's line used", recorded: 'What Whitney said on the recorded take',
  captioned: 'Written from the recorded take',
};
// Why each version exists (contracts_v2.ChangeRecord.kind).
export const VERSION_LABELS: Record<string, string> = {
  generated: 'Made from the approved brief', edit: 'Edited', revert: "The brief's line used", attest: 'A finding attested',
  clearance: 'A note marked done', finish_again: 'Finished again', finishing: 'Being finished',
  recorded_take: 'Caption and covers from the recorded take', refinish: 'Finished again with a permission',
};
export const CTA_LABELS: Record<NonNullable<WeekPlanSlotV2['cta']>, string> = {
  offer: "The week's offer ask", no_offer: 'No offer ask', reply: 'Reply', link: 'Link', none: 'No call to action',
};
export const CHANNELS = [['email', 'Email'], ['instagram', 'Instagram'], ['facebook', 'Facebook']] as const;
export type PublishChannel = typeof CHANNELS[number][0];

/** R58: every pack on screen is system output, never a hand-built reference. */
export const PROVENANCE_LINE = 'Written by the system from the approved brief';
/** R55: shown only when the approval was the team's under delegation. */
export const DELEGATED_LINE = 'Approved by the team under delegation; Whitney has not reviewed it';

// ---- reading a piece --------------------------------------------------------------------------------------------------

type Copy = Record<string, unknown>;
const str = (value: unknown): string | null => typeof value === 'string' ? value : null;
const strings = (value: unknown): string[] => Array.isArray(value) ? value.filter((v): v is string => typeof v === 'string') : [];

/** The value at a dotted path (`caption.hook`, `slides[2].text`), or undefined. */
export function leafAt(node: unknown, path: string): unknown {
  let current = node;
  for (const token of path.match(/[^.[\]]+|\[\d+\]/g) ?? []) {
    if (current === null || current === undefined) return undefined;
    if (token.startsWith('[')) {
      if (!Array.isArray(current)) return undefined;
      current = current[Number(token.slice(1, -1))];
    } else {
      if (typeof current !== 'object' || Array.isArray(current)) return undefined;
      current = (current as Copy)[token];
    }
  }
  return current;
}

/** How a Reel is made: its own `production`, else what an earlier kind implies (b-roll text is on-screen text). */
export function reelProduction(reel: { kind?: string | null; content?: Record<string, unknown> | null; production?: unknown }): 'face_to_camera' | 'on_screen_text' | null {
  const said = reel.production ?? reel.content?.production;
  if (said === 'face_to_camera' || said === 'on_screen_text') return said;
  const kind = reel.kind ?? str(reel.content?.kind);
  return kind === 'broll_text' ? 'on_screen_text' : kind === 'story' || kind === 'stance' ? 'face_to_camera' : null;
}

/** A Reel's kind in words: "Own premise · On-screen text" for a Reel written since Round 2, the earlier wording otherwise. */
export function reelKindWords(kind: string | null | undefined, production: string | null | undefined): string {
  const made = production ? PRODUCTION_LABELS[production] ?? production.replaceAll('_', ' ') : '';
  if (!kind) return made;
  const named = KIND_LABELS[kind] ?? kind.replaceAll('_', ' ');
  return PREMISE_KINDS.includes(kind) && made ? `${named} · ${made}` : named;
}

/** The piece's line above its title: "Email", "Carousel · 9 slides", "Reel 1 · face to camera, story", "Reel 2 · Own premise ·
    On-screen text". */
export function pieceMeta(piece: Pick<PackPieceV2, 'key' | 'label' | 'channel' | 'kind' | 'content'>): string {
  if (piece.channel === 'carousel') {
    const slides = Array.isArray(piece.content?.slides) ? piece.content.slides.length : 0;
    return slides ? `${piece.label} · ${slides} ${slides === 1 ? 'slide' : 'slides'}` : piece.label;
  }
  if (piece.channel === 'reel') {
    const kind = piece.kind ?? str(piece.content?.kind);
    const named = reelKindWords(kind, kind && PREMISE_KINDS.includes(kind) ? reelProduction(piece) : null);
    return named ? `${piece.label} · ${named}` : piece.label;
  }
  return piece.label;
}

/** The piece's working title: a Reel's or the carousel's title, the email's best subject line. */
export function pieceTitle(piece: Pick<PackPieceV2, 'label' | 'channel' | 'content'>): string {
  const copy = piece.content;
  if (!copy) return piece.label;
  if (piece.channel === 'email') return strings(copy.subject_options)[0] || piece.label;
  return str(copy.title) || piece.label;
}

/** A Reel's direction since Round 2, kept apart from its copy (never copied or published): its premise, what a viewer takes
    away, why it differs from the other Reels and where its material is in the calls. Null for a Reel without a premise. */
export type ReelDirection = { premise: string; takeaway: string | null; distinct: string | null; timestamps: string[] };
export function reelDirection(piece: Pick<PackPieceV2, 'channel' | 'content'>): ReelDirection | null {
  const copy = piece.content;
  const premise = piece.channel === 'reel' && copy ? str(copy.premise)?.trim() : '';
  if (!copy || !premise) return null;
  return { premise, takeaway: str(copy.takeaway)?.trim() || null, distinct: str(copy.distinct_because)?.trim() || null,
    timestamps: strings(copy.timestamps).filter(t => t.trim()) };
}

/** The openings or premises the writer weighed for a piece, the chosen one marked, and why; null when the pack recorded none. */
export function choiceFor(pack: Pick<StoredPackV2, 'creative_choices'>, key: string): { options: { text: string; chosen: boolean }[]; why: string } | null {
  const choice = (pack.creative_choices ?? []).find(c => c.piece === key);
  if (!choice) return null;
  const considered = strings(choice.considered).filter(c => c.trim());
  const listed = !choice.chosen || considered.includes(choice.chosen) ? considered : [choice.chosen, ...considered];
  if (!listed.length) return null;
  return { options: listed.map(text => ({ text, chosen: text === choice.chosen })), why: str(choice.why) ?? '' };
}

export type PackField = { path: string; label: string; text: string; multiline: boolean };
/** How a section's fields join in plain text: paragraphs (an email's body, a caption), numbered (subject lines),
    blocks (slides, each under its label) or labelled lines. */
export type Join = 'paragraphs' | 'numbered' | 'blocks' | 'labelled';
export type PackSection = { id: string; label: string; note?: string; layout?: 'third'; join: Join; fields: PackField[] };

const field = (path: string, label: string, text: string | null, multiline = false): PackField | null =>
  text === null ? null : { path, label, text, multiline: multiline || text.length > 90 || text.includes('\n') };
const section = (id: string, label: string, fields: (PackField | null)[], extra: Partial<PackSection> = {}): PackSection | null => {
  const present = fields.filter((f): f is PackField => f !== null);
  return present.length ? { id, label, join: 'labelled', ...extra, fields: present } : null;
};

function caption(copy: Copy): (PackSection | null)[] {
  const c = (copy.caption && typeof copy.caption === 'object' ? copy.caption : null) as Copy | null;
  return [
    c ? section('caption', 'Caption', [field('caption.hook', 'Hook', str(c.hook)), field('caption.body', 'Body', str(c.body), true),
      field('caption.ending', 'Ending', str(c.ending), true)], { join: 'paragraphs' }) : null,
    section('no_offer_ending', 'Caption ending without the offer', [field('no_offer_ending', 'Ending without the offer', str(copy.no_offer_ending), true)],
      { note: 'for a week this is not the offer post' }),
  ];
}

/** A piece's copy as labelled sections, in the order of the packs WIA saw (the mock's pack tab). Every field carries its
    path, so the same list drives reading, Copy, editing, comparing and "Use the brief's line". */
export function pieceSections(piece: Pick<PackPieceV2, 'channel' | 'content'>): PackSection[] {
  const copy = piece.content;
  if (!copy) return [];
  const out: (PackSection | null)[] = [];
  if (piece.channel === 'email') {
    const header = (copy.send_header && typeof copy.send_header === 'object' ? copy.send_header : {}) as Copy;
    out.push(
      section('date', 'Date', [field('send_header.date', 'Date', str(header.date))], { layout: 'third' }),
      section('send_time', 'Send time', [field('send_header.send_time', 'Send time', str(header.send_time))], { layout: 'third' }),
      section('recipients', 'Recipients', [field('send_header.recipients', 'Recipients', str(header.recipients))], { layout: 'third' }),
      section('subjects', 'Subject options', strings(copy.subject_options).map((s, i) => field(`subject_options[${i}]`, i === 0 ? 'Subject 1 (best)' : `Subject ${i + 1}`, s)),
        { join: 'numbered', note: 'best first' }),
      section('preview', 'Preview', [field('preview', 'Preview', str(copy.preview))]),
      section('email', 'Email', [field('opening', 'Opening', str(copy.opening), true), field('body', 'Body', str(copy.body), true),
        field('ending', 'Ending', str(copy.ending), true)], { join: 'paragraphs' }),
    );
  } else if (piece.channel === 'reel') {
    const screens = Array.isArray(copy.screens) ? strings(copy.screens) : [];
    out.push(
      section('title', 'Title', [field('title', 'Title', str(copy.title))]),
      section('cover', 'Cover', [field('cover_text', 'Cover', str(copy.cover_text)),
        ...strings(copy.cover_alternates).map((s, i) => field(`cover_alternates[${i}]`, `Alternate ${i + 1}`, s))]),
      section('hook', 'On-screen hook', [field('on_screen_hook', 'On-screen hook', str(copy.on_screen_hook))]),
      str(copy.script) ? section('script', 'Script', [field('script', 'Script', str(copy.script), true)])
        : section('spoken_opening', 'Spoken opening', [field('spoken_opening', 'Spoken opening', str(copy.spoken_opening))]),
      screens.length ? section('screens', 'Screens', screens.map((s, i) => field(`screens[${i}]`, `Screen ${i + 1}`, s))) : null,
      ...caption(copy),
      section('personal_lines', 'Personal lines', strings(copy.personal_lines).map((s, i) => field(`personal_lines[${i}]`, `Personal line ${i + 1}`, s)),
        { note: 'for Whitney to keep or cut', join: 'numbered' }),
    );
  } else {
    const slides = Array.isArray(copy.slides) ? copy.slides as Copy[] : [];
    out.push(
      section('title', 'Title', [field('title', 'Title', str(copy.title))]),
      section('slides', 'Slides', slides.map((s, i) => field(`slides[${i}].text`, `Slide ${typeof s?.number === 'number' ? s.number : i + 1}`, str(s?.text), true)),
        { join: 'blocks' }),
      ...caption(copy),
    );
  }
  return out.filter((s): s is PackSection => s !== null);
}

/** A section's copy as plain text, joined the way it is posted. */
export function sectionText(s: PackSection): string {
  if (s.join === 'paragraphs') return s.fields.map(f => f.text).join('\n\n');
  if (s.join === 'numbered') return s.fields.map((f, i) => `${i + 1}. ${f.text}`).join('\n');
  if (s.join === 'blocks') return s.fields.map(f => `${f.label}\n${f.text}`).join('\n\n');
  return s.fields.length === 1 ? s.fields[0].text : s.fields.map(f => `${f.label}: ${f.text}`).join('\n');
}

/** Every section of a piece, unabbreviated, without the piece's heading (the final text a published mark starts from). */
export function pieceBodyText(piece: Pick<PackPieceV2, 'channel' | 'content' | 'origin' | 'not_written_reason'>): string {
  if (piece.origin === 'not_written' || !piece.content) return '';
  return pieceSections(piece).map(s => `${s.label}${s.note ? ` (${s.note})` : ''}\n${sectionText(s)}`).join('\n\n');
}

/** One piece in full as plain text, as the mock's "Copy" gave it: its order, meta line and title, then every section. */
export function piecePlainText(piece: PackPieceV2): string {
  const head = `${piece.ordinal}. ${pieceMeta(piece)}`;
  if (piece.origin === 'not_written' || !piece.content) return `${head}: Not written\n\n${piece.not_written_reason || 'This piece was not written.'}`;
  return `${head}: ${pieceTitle(piece)}\n\n${pieceBodyText(piece)}`;
}

/** The whole pack as plain text ("Copy all"): every piece in full, in tab order. */
export function packPlainText(pack: Pick<StoredPackV2, 'title' | 'pieces'>): string {
  return [`CONTENT PACK: ${pack.title}`, ...[...pack.pieces].sort((a, b) => a.ordinal - b.ordinal).map(piecePlainText)].join('\n\n');
}

// ---- editing, locks and comparing -------------------------------------------------------------------------------------

/** Whether a person may edit this path of the piece: its head is one of the piece's editable leaves (`piece.editable`,
    contracts_v2.EDITABLE), and inside the slides only a slide's text. */
export function isEditablePath(piece: Pick<PackPieceV2, 'editable'>, path: string): boolean {
  const covered = piece.editable.some(e => path === e || path.startsWith(`${e}.`) || path.startsWith(`${e}[`));
  if (!covered) return false;
  return path.split(/[.[]/, 1)[0] === 'slides' ? /^slides\[\d{1,2}\]\.text$/.test(path) : true;
}

/** The lock that keeps this line word for word, if any: a lock on it, on something around it, or on the whole piece. */
export function lockFor(piece: Pick<PackPieceV2, 'locks'>, path: string): PackLockV2 | null {
  return piece.locks.find(l => !l.path || l.path === '*' || path === l.path || path.startsWith(`${l.path}.`) || path.startsWith(`${l.path}[`)) ?? null;
}

/** A lock in words: who wrote the line, where, and whether under delegation (R55). */
export function lockText(lock: PackLockV2): string {
  return `Locked · written by ${lock.author}${lock.origin === 'gate_two' ? ' at Gate 2' : ' in the pack'}${lock.delegated ? ' (delegated)' : ''}`;
}

/** The brief's line at this path, when the brief had the piece and the line. */
export function briefLine(piece: Pick<PackPieceV2, 'brief_copy'>, path: string): string | null {
  return piece.brief_copy ? str(leafAt(piece.brief_copy, path)) : null;
}

export type DiffPart = { kind: 'same' | 'added' | 'removed'; text: string };

/** A word diff of the brief's line against the pack's (longest common subsequence over words and spaces). */
export function diffWords(before: string, after: string): DiffPart[] {
  const a = before.split(/(\s+)/).filter(Boolean), b = after.split(/(\s+)/).filter(Boolean);
  const n = a.length, m = b.length;
  const table = Array.from({ length: n + 1 }, () => new Uint32Array(m + 1));
  for (let i = n - 1; i >= 0; i--) for (let j = m - 1; j >= 0; j--) table[i][j] = a[i] === b[j] ? table[i + 1][j + 1] + 1 : Math.max(table[i + 1][j], table[i][j + 1]);
  const parts: DiffPart[] = [];
  const push = (kind: DiffPart['kind'], text: string) => {
    const last = parts[parts.length - 1];
    if (last?.kind === kind) last.text += text; else parts.push({ kind, text });
  };
  let i = 0, j = 0;
  while (i < n && j < m) {
    if (a[i] === b[j]) { push('same', a[i]); i++; j++; }
    else if (table[i + 1][j] >= table[i][j + 1]) push('removed', a[i++]);
    else push('added', b[j++]);
  }
  while (i < n) push('removed', a[i++]);
  while (j < m) push('added', b[j++]);
  return parts;
}

// ---- findings ---------------------------------------------------------------------------------------------------------

export type PackFinding = PackFindingV2 & { piece: string | null };

/** Every finding of the pack and its pieces, once each, with the piece it is on. */
export function packFindings(pack: Pick<StoredPackV2, 'findings' | 'pieces'>): PackFinding[] {
  const seen = new Map<string, PackFinding>();
  for (const f of pack.findings) seen.set(f.finding_id, { ...f, piece: f.piece ?? null });
  for (const p of pack.pieces) for (const f of p.findings) if (!seen.has(f.finding_id)) seen.set(f.finding_id, { ...f, piece: f.piece ?? p.key });
  return [...seen.values()];
}

/** A finding's message in the reviewer's words (R50): no evidence or passage identifiers. */
export const findingText = (message: string) => plainBlocker(message);

/** An editor's finding (Round 2) on its own piece, in plain words: the piece's name in front is dropped, since the piece is on
    screen. */
export function editorialText(finding: Pick<PackFindingV2, 'message'>, label: string): string {
  const text = plainMessage(findingText(finding.message));
  return text.startsWith(`${label}: `) ? text.slice(label.length + 2) : text;
}

/** How many before-publishing items are left: notes not yet done and client quotes not yet cleared. */
export const toCheck = (pack: Pick<StoredPackV2, 'before_publishing' | 'client_quotes'>) =>
  pack.before_publishing.filter(n => !n.done).length + pack.client_quotes.filter(q => !q.cleared).length;

// ---- the pack's writes ------------------------------------------------------------------------------------------------

type Result = { body: Record<string, unknown> } | { error: string };

/** PATCH /packs/{id}/pieces/{key}: the drafted lines that changed, by path, with the manifest hash the edit was made on, and
    why the person made the edit when they say (the weekly learning loop reads it). */
export function editRequest(manifest: string | null | undefined, fields: PackField[], drafts: Record<string, string>, reason = ''): Result {
  if (!manifest) return { error: 'This pack version cannot be edited yet.' };
  const changes: Record<string, string> = {};
  for (const f of fields) {
    if (!(f.path in drafts) || drafts[f.path] === f.text) continue;
    if (!drafts[f.path].trim()) return { error: `${f.label} cannot be empty.` };
    changes[f.path] = drafts[f.path];
  }
  if (!Object.keys(changes).length) return { error: 'Nothing changed.' };
  const why = reason.trim();
  if (why.length > 1000) return { error: 'Say why in 1,000 characters or fewer.' };
  return { body: { expected_manifest_hash: manifest, changes, ...(why ? { reason: why } : {}) } };
}

export const revertRequest = (manifest: string, paths: string[]): Result =>
  paths.length ? { body: { expected_manifest_hash: manifest, paths } } : { error: 'Choose a line to put back.' };

export const clearanceRequest = (manifest: string, itemId: string, reference: string, note = ''): Result =>
  ({ body: { expected_manifest_hash: manifest, item_id: itemId, reference: reference.trim() || null, note: note.trim() || null } });

export const attestRequest = (manifest: string, statement: string): Result =>
  statement.trim().length < 3 ? { error: 'Say why the sentence is true, for the record.' } : { body: { expected_manifest_hash: manifest, statement: statement.trim() } };

/** Keeping an editor's finding as it is: the attestation's route, its statement why the line is fine as it is. */
export const keepRequest = (manifest: string, reason: string): Result =>
  reason.trim().length < 3 ? { error: 'Say why the line is fine as it is.' } : { body: { expected_manifest_hash: manifest, statement: reason.trim() } };

export const decisionRequest = (manifest: string, decision: 'ready_to_publish' | 'in_review', note = ''): Result =>
  ({ body: { expected_manifest_hash: manifest, decision, note: note.trim() || null } });

/** The post-recording pass (NP.B14): what Whitney said on the take, pasted as it was transcribed. */
export const recordedTakeRequest = (manifest: string, said: string): Result =>
  said.trim().length < 40 ? { error: 'Paste the whole take: what Whitney said, start to end.' }
    : said.length > 20000 ? { error: 'The take is longer than 20,000 characters; paste one Reel\'s take.' }
    : { body: { expected_manifest_hash: manifest, said: said.trim() } };

/** Finishing again with a permission (NP.B15): each granted item ("S1"...) or stated fact, in the person's own words. */
export const refinishRequest = (manifest: string, grants: { item_id: string | null; statement: string }[]): Result => {
  const given = grants.map(g => ({ item_id: g.item_id, statement: g.statement.trim() })).filter(g => g.statement);
  if (!given.length) return { error: 'Say what may now be used: grant an item in your own words, or state a fact.' };
  if (given.some(g => g.statement.length < 3)) return { error: 'Each grant needs a few words: what may now be said.' };
  return { body: { expected_manifest_hash: manifest, grants: given } };
};

export type PublishedForm = { published_on: string; channel: PublishChannel; final_text: string; url: string };

/** POST /packs/{id}/pieces/{key}/published: the date, channel and final text, and the link when there is one. */
export function publishedRequest(form: PublishedForm): Result {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(form.published_on)) return { error: 'Choose the date it was published.' };
  const date = new Date(`${form.published_on}T12:00:00Z`);
  if (!Number.isFinite(date.getTime()) || date.toISOString().slice(0, 10) !== form.published_on) return { error: 'Choose a valid publication date.' };
  if (form.published_on > today()) return { error: 'The publication date cannot be in the future.' };
  if (!form.final_text.trim()) return { error: 'Paste the text as it was published.' };
  const url = form.url.trim();
  if (url && !/^https?:\/\/\S+$/i.test(url)) return { error: 'The link must be a full web address, starting with https://' };
  return { body: { published_on: form.published_on, channel: form.channel, final_text: form.final_text, url: url || null } };
}

/** The channel a piece is usually published on: the email by email, the rest on Instagram. */
export const defaultChannel = (piece: Pick<PackPieceV2, 'channel'>): PublishChannel => piece.channel === 'email' ? 'email' : 'instagram';

/** Today's date as YYYY-MM-DD in the browser's own time zone. */
export function today(now = new Date()): string {
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
}

/** A web address that is safe to link to (http or https only). */
export const safeUrl = (value: string | null | undefined) => value && /^https?:\/\//i.test(value) ? value : null;
