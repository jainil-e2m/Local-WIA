/* ─────────────────────────────────────────────────────────────────
   Parse corpus/zoom_transcripts/*.txt into the Atelier's transcript
   shape, classify each one, and write an index.

   RUN:  node corpus/index-zoom.mjs

   Writes:
     corpus/zoom/transcripts.json   every transcript, normalised
     corpus/zoom/index.md           the readable catalogue

   Reads only. Nothing in zoom_transcripts/ is moved or deleted.

   WHY THE FILENAMES CANNOT BE TRUSTED

   Zoom names 60+ of these "Carmen Cruickshank's Personal Meeting Room's
   transcript (n).txt". The number is a download counter, not an
   identifier — (3) and (17) are different meetings, and nothing in the
   name says whether a call was with a client or an internal check-in.
   So classification is done on the WORDS: who spoke, and whether any of
   them is from outside the team.

   THE TEAM ROSTER IS DERIVED, NOT HARDCODED

   A speaker appearing across many unrelated meetings is staff; someone
   appearing in one or two is a client. Hardcoding a roster would rot the
   first time somebody joins or leaves, and would silently misclassify
   every call involving the person who was missed.

   ATTRIBUTION IS WEAKER HERE THAN IN FATHOM

   A Zoom VTT carries a display name and nothing else. Fathom resolves
   speakers to calendar invitees by email, so it can say "this person is
   external" as fact. Here it is inference, and every record says so —
   `attribution: "name-only"` — because a pipeline that forgets the
   difference will eventually put a quote in the wrong client's mouth.
   ───────────────────────────────────────────────────────────────── */

import { createHash } from 'node:crypto';
import { mkdirSync, readdirSync, readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

const IN = 'corpus/zoom_transcripts';
const OUT = 'corpus/zoom';

/* A meeting this short never happened — the host started the recording
   and the call did not follow. Kept in the index as evidence a session
   existed, excluded from extraction. */
const FRAGMENT_WORDS = 50;

/* Titles that are internal regardless of who attended. Everything else
   is decided by the speaker roster below. */
const INTERNAL_TITLE =
  /check-?in with gisselle|leadlock|ai strategy session|ghl ai chat widget|^planning$|elevate checklist/i;
const WORKSHOP_TITLE = /workshop|monthly q&a/i;

/* ── parse ───────────────────────────────────────────────────────── */

const titleOf = (file) =>
  file
    .replace(/\.txt$/, '')
    .replace(/'s transcript(\s*\(\d+\))?$/, '')
    .replace(/\s*\(\d+\)$/, '')
    .replace(/_/g, '|')
    .trim();

const parse = (raw) => {
  const segments = [];
  let pending = null;

  for (const line of raw.split(/\r?\n/)) {
    const t = line.trim();
    if (!t || t === 'WEBVTT' || /^\d+$/.test(t)) continue;

    const cue = t.match(/^(\d{2}:\d{2}:\d{2})[.,]\d+\s*-->\s*(\d{2}:\d{2}:\d{2})/);
    if (cue) {
      pending = { start: cue[1], end: cue[2] };
      continue;
    }

    /* "Speaker Name: what they said". A colon inside the sentence is
       common, so only a short leading run counts as a name. */
    const m = t.match(/^([^:]{1,60}):\s*(.*)$/);
    segments.push({
      speaker: m ? m[1].trim() : null,
      timestamp: pending?.start ?? null,
      text: (m ? m[2] : t).replace(/\s+/g, ' ').trim(),
    });
    pending = null;
  }
  return segments.filter((s) => s.text);
};

const docs = [];
for (const file of readdirSync(IN).filter((f) => f.endsWith('.txt'))) {
  const raw = readFileSync(join(IN, file), 'utf8');
  const segments = parse(raw);
  const words = segments.reduce((n, s) => n + s.text.split(/\s+/).length, 0);
  const speakers = [...new Set(segments.map((s) => s.speaker).filter(Boolean))];

  docs.push({
    file,
    title: titleOf(file),
    source: 'zoom',
    attribution: 'name-only',
    contentHash: createHash('sha256').update(raw).digest('hex').slice(0, 16),
    duration: segments.at(-1)?.timestamp ?? '00:00:00',
    words,
    speakers,
    segments,
  });
}

/* ── who is staff ────────────────────────────────────────────────── */

/* Appearing in many otherwise-unrelated meetings is what distinguishes
   the team from a client, who shows up in their own calls only. */
const appearances = new Map();
for (const d of docs) for (const s of d.speakers) appearances.set(s, (appearances.get(s) ?? 0) + 1);

const TEAM_THRESHOLD = Math.max(5, Math.round(docs.length * 0.06));
const derived = [...appearances].filter(([, n]) => n >= TEAM_THRESHOLD).map(([s]) => s);

/* Frequency alone misses staff who rarely join calls. Danielle sits on
   the imagery side and appears in three meetings — below any threshold
   that does not also sweep in Erin Smith and Shannon Lee, who attend
   Carmen's office hours regularly and are Accelerator MEMBERS, not
   staff. Raising or lowering the cutoff trades one error for the other,
   so the known names are seeded and frequency fills in the rest. */
const SEED_TEAM = [
  /^whitney hodges$/i,
  /^gis?selle/i,
  /^carmen cruickshank$/i,
  /^danielle mcginnis$/i,
  /^jacqueline/i,
];

const team = new Set([
  ...derived,
  ...[...appearances.keys()].filter((s) => SEED_TEAM.some((re) => re.test(s))),
]);

/* ── classify ────────────────────────────────────────────────────── */

const seenHash = new Set();
for (const d of docs) {
  d.externals = d.speakers.filter((s) => !team.has(s));

  if (seenHash.has(d.contentHash)) d.duplicate = true;
  seenHash.add(d.contentHash);

  d.kind = d.words < FRAGMENT_WORDS
    ? 'fragment'
    : WORKSHOP_TITLE.test(d.title)
      ? 'workshop'
      : INTERNAL_TITLE.test(d.title)
        ? 'internal'
        : d.externals.length
          ? 'client'
          : 'internal';

  /* Only a client call with an outside voice can carry a client quote,
     which is what the qualifying signals are made of. */
  d.extractable = d.kind !== 'fragment' && !d.duplicate;
}

/* ── the chains the spec names ───────────────────────────────────── */

const CHAINS = {
  Funktastic: /funktastic/i,
  'Press Record': /press record/i,
  'Miss Lyss (Alyssa)': /alyssa|miss lyss/i,
  'Carroll Hall': /carroll hall/i,
  'Dogwood Reserve': /dogwood/i,
};

const chainHits = {};
for (const [name, re] of Object.entries(CHAINS)) {
  chainHits[name] = docs.filter((d) => re.test(d.title) || d.segments.some((s) => re.test(s.text))).length;
}

/* ── write ───────────────────────────────────────────────────────── */

mkdirSync(OUT, { recursive: true });
writeFileSync(join(OUT, 'transcripts.json'), JSON.stringify(docs, null, 2), 'utf8');

const by = (k) => docs.filter((d) => d.kind === k);
const totalWords = docs.reduce((n, d) => n + d.words, 0);

const row = (d) =>
  `| ${d.title} | ${d.kind}${d.duplicate ? ' · dup' : ''} | ${d.duration} | ${d.words.toLocaleString()} | ${d.externals.slice(0, 3).join(', ') || '—'} |`;

const md = `# Zoom transcripts — index

${docs.length} files parsed from \`corpus/zoom_transcripts/\`, **${totalWords.toLocaleString()} words**.
Generated by \`corpus/index-zoom.mjs\`. Normalised copies in \`transcripts.json\`.

| Kind | Files |
|---|---|
| Client calls | ${by('client').length} |
| Workshops & Q&A | ${by('workshop').length} |
| Internal | ${by('internal').length} |
| Fragments (under ${FRAGMENT_WORDS} words) | ${by('fragment').length} |
| Exact duplicates | ${docs.filter((d) => d.duplicate).length} |
| **Extractable** | **${docs.filter((d) => d.extractable).length}** |

## Attribution

Every record is \`attribution: "name-only"\`. A Zoom VTT gives a display name
and nothing more, so "this speaker is a client" is an **inference** from who
else they appear with — not the fact that Fathom's \`matched_calendar_invitee_email\`
provides. Anything quoting a named client from this source needs its timecode
checked before it ships.

## Team roster, derived

Speakers appearing in ${TEAM_THRESHOLD}+ meetings, treated as staff:

${[...team].map((s) => `- ${s} — ${appearances.get(s)} meetings`).join('\n')}

## Named chains

| Chain | Transcripts |
|---|---|
${Object.entries(chainHits).map(([n, c]) => `| ${n} | ${c} |`).join('\n')}

## Client calls

| Title | Kind | Length | Words | Outside voices |
|---|---|---|---|---|
${by('client').sort((a, b) => b.words - a.words).map(row).join('\n')}

## Workshops & Q&A

| Title | Kind | Length | Words | Outside voices |
|---|---|---|---|---|
${by('workshop').sort((a, b) => b.words - a.words).map(row).join('\n')}

## Internal — triaged out before extraction

| Title | Kind | Length | Words | Outside voices |
|---|---|---|---|---|
${by('internal').sort((a, b) => b.words - a.words).map(row).join('\n')}

## Fragments

Recording started, meeting did not. Kept as evidence a session existed.

${by('fragment').map((d) => `- \`${d.file}\` — ${d.words}w`).join('\n')}
`;

writeFileSync(join(OUT, 'index.md'), md, 'utf8');

console.log(`${docs.length} transcripts · ${totalWords.toLocaleString()} words`);
console.log(`  client   ${by('client').length}`);
console.log(`  workshop ${by('workshop').length}`);
console.log(`  internal ${by('internal').length}`);
console.log(`  fragment ${by('fragment').length}`);
console.log(`  duplicate ${docs.filter((d) => d.duplicate).length}`);
console.log(`\n  extractable: ${docs.filter((d) => d.extractable).length}`);
console.log(`\nteam roster (${TEAM_THRESHOLD}+ meetings): ${[...team].join(', ')}`);
console.log(`\n→ ${OUT}/index.md`);
console.log(`→ ${OUT}/transcripts.json`);
