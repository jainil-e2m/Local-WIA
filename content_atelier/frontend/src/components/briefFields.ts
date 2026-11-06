/* Gate 2's field map and path walker (5.F1, 5.F4; interface 4). The editor is built over the brief document, not over
   one contract: the walker visits every value in the sections a person may edit and names it by its path, the same
   syntax the backend locks (backend/backend_pipeline/briefs/paths.py): sections and keys joined by dots, list items
   counted from 0, as `format_plan.reels[1].cover_text`. The map below only labels fields and says how each is edited;
   a field it does not name is still shown and editable as text, with a label made from its path, so contract v4's new
   fields appear without a change here (add a map entry to give one a better label). */

export type FieldKind = 'text' | 'number' | 'choice';
export type BriefField = { path: string; section: string; label: string; value: string | number | null; kind: FieldKind;
  multiline: boolean; options?: string[]; nullable?: boolean };
// `options` may depend on the field's value: a Reel from the Round 2 writer chooses among its own kinds, an earlier one among
// the earlier kinds.
type Entry = { label: string | ((n: number[]) => string); multiline?: boolean; editable?: boolean; options?: string[] | ((value: unknown) => string[]); nullable?: boolean };

// Sections a person edits, by contract (the backend's EDITABLE_V2, EDITABLE_V3 and EDITABLE_V4). Contract v4 (E.B33) is in
// the 13 October order: the brief, then the copy of every asset.
export const EDITABLE_SECTIONS: Record<string, string[]> = {
  brief_document_v2: ['sharpened_point', 'strategic_purpose', 'audience', 'intended_shift', 'point_of_view', 'wia_perspective',
    'supporting_example', 'narrative_outline', 'format_plan', 'cta_why', 'before_publishing'],
  brief_document_v3: ['sharpened_point', 'strategic_purpose', 'audience', 'intended_shift', 'point_of_view', 'wia_perspective',
    'supporting_example', 'narrative_outline', 'format_plan', 'cta_why', 'before_publishing'],
};
EDITABLE_SECTIONS.brief_document_v4 = ['sharpened_point', 'central_point', 'strategic_purpose', 'intended_shift', 'audience',
  'point_of_view', 'wia_perspective', 'supporting_example', 'narrative_outline', 'cta_why', 'before_publishing', 'format_plan'];

export const SECTION_LABELS: Record<string, string> = {
  wia_perspective: 'WIA perspective', supporting_example: 'Supporting example', format_plan: 'The copy of each piece',
  narrative_outline: 'Narrative outline', audience: 'Audience', intended_shift: 'The shift', strategic_purpose: 'Strategic purpose',
  sharpened_point: 'Sharper point', point_of_view: 'Point of view', cta_why: 'Why this CTA', before_publishing: 'Before publishing',
  central_point: 'Central point',
};

const KINDS = ['story', 'stance', 'broll_text'];
const PREMISE_KINDS = ['central', 'second', 'third'];
const reelKinds = (value: unknown) => PREMISE_KINDS.includes(String(value)) ? PREMISE_KINDS : KINDS;

/** A choice as a person reads it in the editor: the Reel kinds and how a Reel is made in words, the rest without underscores. */
const OPTION_WORDS: Record<string, string> = {
  central: 'Central story', second: 'Own premise (Reel 2)', third: 'Own premise (Reel 3)',
  face_to_camera: 'Face to camera', on_screen_text: 'On-screen text',
};
export const optionWords = (option: string) => OPTION_WORDS[option] ?? option.replaceAll('_', ' ');

const n1 = (n: number[], i = 0) => (n[i] ?? 0) + 1;
/** Field map: a path with its list indexes written `[]` → how the field is labelled and edited. */
export const FIELD_MAP: Record<string, Entry> = {
  wia_perspective: { label: 'WIA perspective', multiline: true },
  'supporting_example.scene': { label: 'The scene', multiline: true },
  'supporting_example.wia_move': { label: 'What WIA did', multiline: true },
  'supporting_example.client_contribution': { label: 'What the client contributed', multiline: true },
  'sharpened_point.text': { label: 'Sharper point' }, 'sharpened_point.reason': { label: 'Why it is sharper', multiline: true },
  'strategic_purpose.pillar': { label: 'Pillar', options: ['ATTRACT', 'WARM', 'CONVERT'] },
  'strategic_purpose.content_type': { label: 'Content type' }, 'strategic_purpose.why_now': { label: 'Why now', multiline: true },
  'audience.who': { label: 'Who it is for' }, 'audience.reason_to_care': { label: 'Why the audience cares', multiline: true },
  'intended_shift.understand': { label: 'Understand' }, 'intended_shift.believe': { label: 'Believe' },
  'intended_shift.do': { label: 'Do (optional)', nullable: true },
  point_of_view: { label: 'Point of view', options: ['we', 'I'] },
  'narrative_outline.hooks[].text': { label: n => `Hook ${n1(n)}` },
  'narrative_outline.hooks[].style': { label: n => `Hook ${n1(n)} style`, options: ['observation', 'contrarian_belief', 'question', 'result', 'cultural_moment'] },
  'narrative_outline.problems_desires_symptoms[]': { label: n => `Problem, desire or symptom ${n1(n)}` },
  'narrative_outline.main_point': { label: 'Main point', multiline: true },
  'narrative_outline.transformation': { label: 'Transformation', multiline: true }, 'narrative_outline.cta': { label: "The outline's CTA" },
  'format_plan.reels[].job': { label: n => `Reel ${n1(n)}: its job (direction)` },
  'format_plan.reels[].cover_text': { label: n => `Reel ${n1(n)}: cover` },
  'format_plan.reels[].spoken_opening': { label: n => `Reel ${n1(n)}: spoken opening`, multiline: true },
  'format_plan.reels[].script': { label: n => `Reel ${n1(n)}: script`, multiline: true, nullable: true },
  'format_plan.reels[].beats[]': { label: n => `Reel ${n1(n)}: beat ${n1(n, 1)}` },
  'format_plan.reels[].read_time_seconds': { label: n => `Reel ${n1(n)}: read time (seconds)` },
  'format_plan.reels[].source': { label: n => `Reel ${n1(n)}: source`, options: ['new_script', 'existing_clip'] },
  'format_plan.carousel.job': { label: 'Carousel: its job (direction)' },
  'format_plan.carousel.slides[].number': { label: 'Slide number', editable: false },
  'format_plan.carousel.slides[].job': { label: n => `Slide ${n1(n)}: its job (direction)` },
  'format_plan.carousel.slides[].text': { label: n => `Slide ${n1(n)}`, multiline: true },
  'format_plan.email.subject_options[]': { label: n => `Email subject option ${n1(n)}` },
  'format_plan.email.preview': { label: 'Email preview' },
  'format_plan.email.opening': { label: 'Email opening', multiline: true },
  'format_plan.email.body': { label: 'Email body', multiline: true },
  'format_plan.email.ending': { label: 'Email ending', multiline: true },
  'format_plan.caption.hook': { label: 'Caption hook' },
  'format_plan.caption.body': { label: 'Caption body', multiline: true },
  'format_plan.caption.ending': { label: 'Caption ending' },
  'format_plan.stories.frames[]': { label: n => `Stories frame ${n1(n)}` },
  // Contract v4 (E.B33): the 13 October brief and each asset's own copy.
  central_point: { label: 'Central point', multiline: true },
  'strategic_purpose.desired_response': { label: 'Desired response', multiline: true },
  'supporting_example.timestamps[]': { label: n => `Call time ${n1(n)}` },
  'supporting_example.details[]': { label: n => `Detail ${n1(n)} the copy uses` },
  'supporting_example.credits[].actor': { label: n => `Beat ${n1(n)}: who` },
  'supporting_example.credits[].did': { label: n => `Beat ${n1(n)}: what they did` },
  'format_plan.reels[].kind': { label: n => `Reel ${n1(n)}: kind`, options: reelKinds },
  // The Round 2 writer's Reels (brief_write v5): each Reel's own premise, how it is made, and the premises weighed (a record
  // of the writer's choice, read in the brief, not edited).
  'format_plan.reels[].production': { label: n => `Reel ${n1(n)}: how it is made`, options: ['face_to_camera', 'on_screen_text'] },
  'format_plan.reels[].premise': { label: n => `Reel ${n1(n)}: premise (direction)`, multiline: true },
  'format_plan.reels[].takeaway': { label: n => `Reel ${n1(n)}: takeaway (direction)`, multiline: true },
  'format_plan.reels[].distinct_because': { label: n => `Reel ${n1(n)}: why it is different (direction)`, multiline: true },
  'format_plan.reels[].timestamps[]': { label: n => `Reel ${n1(n)}: call time ${n1(n, 1)}` },
  'format_plan.premise_options[].premise': { label: n => `Premise considered ${n1(n)}`, editable: false },
  'format_plan.premise_options[].type': { label: n => `Premise considered ${n1(n)}: type`, editable: false },
  'format_plan.premise_options[].material': { label: n => `Premise considered ${n1(n)}: material`, editable: false },
  'format_plan.premise_options[].used_for': { label: n => `Premise considered ${n1(n)}: used for`, editable: false },
  'format_plan.premise_options[].why': { label: n => `Premise considered ${n1(n)}: why`, editable: false },
  'format_plan.reels[].register': { label: n => `Reel ${n1(n)}: register`, options: ['spoken', 'on_screen'] },
  'format_plan.reels[].on_screen_hook': { label: n => `Reel ${n1(n)}: on-screen hook` },
  'format_plan.reels[].screens[]': { label: n => `Reel ${n1(n)}: screen ${n1(n, 1)}` },
  'format_plan.reels[].personal_lines[]': { label: n => `Reel ${n1(n)}: personal line ${n1(n, 1)} (keep or cut)` },
  'format_plan.reels[].caption.hook': { label: n => `Reel ${n1(n)}: caption hook` },
  'format_plan.reels[].caption.body': { label: n => `Reel ${n1(n)}: caption body`, multiline: true },
  'format_plan.reels[].caption.ending': { label: n => `Reel ${n1(n)}: caption ending`, multiline: true },
  'format_plan.reels[].offer_descriptor': { label: n => `Reel ${n1(n)}: offer descriptor`, nullable: true },
  'format_plan.carousel.title': { label: 'Carousel title' },
  'format_plan.carousel.register': { label: 'Carousel register', editable: false },
  'format_plan.carousel.caption.hook': { label: 'Carousel caption hook' },
  'format_plan.carousel.caption.body': { label: 'Carousel caption body', multiline: true },
  'format_plan.carousel.caption.ending': { label: 'Carousel caption ending', multiline: true },
  'format_plan.carousel.offer_descriptor': { label: 'Carousel offer descriptor', nullable: true },
  'format_plan.email.job': { label: 'Email: its job (direction)' },
  'format_plan.email.register': { label: 'Email register', editable: false },
  'format_plan.email.send_header.date': { label: 'Email DATE (proposed)' },
  'format_plan.email.send_header.send_time': { label: 'Email SEND TIME (proposed)' },
  'format_plan.email.send_header.recipients': { label: 'Email RECIPIENTS (proposed)' },
  'format_plan.email.offer_descriptor': { label: 'Email offer descriptor', nullable: true },
  cta_why: { label: 'Why this CTA', multiline: true },
  'before_publishing[].text': { label: n => `Before publishing P${n1(n)}`, multiline: true },
  // Answered through the answers route (an approver's), and a required item is lowered only by an approver.
  'before_publishing[].answer': { label: 'Answer', editable: false },
  'before_publishing[].required': { label: 'Required', editable: false },
  'before_publishing[].kind': { label: n => `Before publishing P${n1(n)}: kind` },
};

/** A path with its list indexes taken out: `format_plan.reels[1].cover_text` → (`format_plan.reels[].cover_text`, [1]). */
export function pattern(path: string): { key: string; indexes: number[] } {
  const indexes: number[] = [];
  const key = path.replace(/\[(\d+)\]/g, (_, i: string) => { indexes.push(Number(i)); return '[]'; });
  return { key, indexes };
}

const words = (s: string) => s.replaceAll('_', ' ');
/** A field's label: the map's, else one made from its path (a field the map does not know yet, such as v4's). */
export function fieldLabel(path: string): string {
  const { key, indexes } = pattern(path);
  const entry = FIELD_MAP[key];
  if (entry) return typeof entry.label === 'function' ? entry.label(indexes) : entry.label;
  let i = 0;
  const made = key.split('.').map(part => part.replace(/\[\]/g, () => ` ${(indexes[i++] ?? 0) + 1}`)).map(words);
  const head = made[0] === 'format plan' ? made.slice(1) : made;
  const text = head.join(': ');
  return text.charAt(0).toUpperCase() + text.slice(1);
}

function walk(node: unknown, path: string, out: [string, unknown][]) {
  if (Array.isArray(node)) node.forEach((v, i) => walk(v, `${path}[${i}]`, out));
  else if (node && typeof node === 'object') Object.entries(node as Record<string, unknown>).forEach(([k, v]) => walk(v, path ? `${path}.${k}` : k, out));
  else out.push([path, node]);
}

/** Every editable field of a brief body, in document order, grouped by section. */
export function briefFields(body: Record<string, unknown>, schemaVersion: string): { section: string; label: string; fields: BriefField[] }[] {
  const sections = EDITABLE_SECTIONS[schemaVersion] ?? EDITABLE_SECTIONS.brief_document_v3;
  const groups: { section: string; label: string; fields: BriefField[] }[] = [];
  for (const section of sections) {
    if (!(section in body)) continue;
    const leaves: [string, unknown][] = [];
    walk(body[section], section, leaves);
    const fields: BriefField[] = [];
    for (const [path, value] of leaves) {
      const entry = FIELD_MAP[pattern(path).key];
      if (entry?.editable === false || typeof value === 'boolean') continue;
      if (value === null && !entry?.nullable) continue;
      const kind: FieldKind = entry?.options ? 'choice' : typeof value === 'number' ? 'number' : 'text';
      const text = typeof value === 'string' ? value : '';
      const options = typeof entry?.options === 'function' ? entry.options(value) : entry?.options;
      fields.push({ path, section, label: fieldLabel(path), value: value as string | number | null, kind, options,
        nullable: entry?.nullable, multiline: entry?.multiline ?? (text.length > 90 || text.includes('\n')) });
    }
    if (fields.length) groups.push({ section, label: SECTION_LABELS[section] ?? fieldLabel(section), fields });
  }
  return groups;
}

/** The value a field's draft is saved as: a number field's number, an optional field left empty as null. */
export function fieldValue(field: BriefField, draft: string): string | number | null {
  if (field.kind === 'number') return Number(draft);
  if (field.nullable && !draft.trim()) return null;
  return draft;
}

/** The edit route's body for the drafted fields (only those that changed), or what is wrong with them. */
export function fieldChanges(expected: string, fields: BriefField[], drafts: Record<string, string>): { body: Record<string, unknown> } | { error: string } {
  const changes: Record<string, unknown> = {};
  for (const field of fields) {
    if (!(field.path in drafts)) continue;
    const value = fieldValue(field, drafts[field.path]);
    if (value === field.value) continue;
    if (field.kind === 'number' && !Number.isFinite(value)) return { error: `${field.label} must be a number.` };
    if (typeof value === 'string' && !value.trim()) return { error: `${field.label} cannot be empty.` };
    changes[field.path] = value;
  }
  if (!Object.keys(changes).length) return { error: 'Nothing changed.' };
  return { body: { expected_hash: expected, changes } };
}

/** Whether a field is kept verbatim by a refresh: a lock on it or on a section or item around it. */
export const isLocked = (path: string, locks: string[]) => locks.some(lock => path === lock || path.startsWith(`${lock}.`) || path.startsWith(`${lock}[`));
