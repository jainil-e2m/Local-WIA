/* ─────────────────────────────────────────────────────────────────
   Probe a Fathom API key — what does it actually reach?

   RUN:  node --env-file=.env corpus/probe-fathom.mjs

   .env needs:
     FATHOM_API_KEY=...

   READ-ONLY by default. Registers nothing, changes nothing.
   Pass --register <https-url> to create ONE webhook. That is the
   only write this file can perform, and it is opt-in.

   WHAT IT ANSWERS. A Fathom key is scoped to one PERSON, not to an
   account:

     "API keys are created at the user level. Your key can access
      meetings recorded by you or shared to your Team."
     "Admin API keys do not grant access to other users' unshared
      meetings."

   So "does the key work" is never the interesting question. The
   interesting question is WHOSE meetings it sees. On a free plan
   there is no Team, so the expected answer is "only mine" — and
   that expectation, confirmed or refuted, is the entire paid-plan
   argument. Section 3 is the one that decides it.
   ───────────────────────────────────────────────────────────────── */

const KEY = process.env.FATHOM_API_KEY;
const BASE = 'https://api.fathom.ai/external/v1';

if (!KEY) {
  console.error('Set FATHOM_API_KEY in .env, then run with --env-file=.env');
  process.exit(1);
}

const args = process.argv.slice(2);
const registerAt = args.includes('--register') ? args[args.indexOf('--register') + 1] : null;

const call = async (path, params = {}) => {
  const qs = new URLSearchParams(params).toString();
  const res = await fetch(`${BASE}${path}${qs ? '?' + qs : ''}`, {
    headers: { 'X-Api-Key': KEY },
  });
  const text = await res.text();
  let json = null;
  try {
    json = JSON.parse(text);
  } catch {
    /* keep the raw body so the error line can show it */
  }
  return { status: res.status, ok: res.ok, json, text };
};

/* ── 1 · does the key work ───────────────────────────────────────── */

const first = await call('/meetings');

if (!first.ok) {
  console.error(`✗ ${first.status} — ${first.text.slice(0, 200)}`);
  if (first.status === 401) console.error('  The key is wrong, revoked, or pasted with whitespace.');
  if (first.status === 403) console.error('  The key is valid but this account is not permitted the API.');
  process.exit(1);
}

console.log(`✓ key accepted  (${BASE})\n`);

/* ── 2 · everything the key can see ──────────────────────────────── */

/* Paginated, and capped so a probe on a busy account stays a probe.
   The ceiling is 60 calls a minute; 20 pages is nowhere near it. */
const meetings = [];
let cursor;
let pages = 0;
do {
  const page = await call('/meetings', cursor ? { cursor } : {});
  if (!page.ok) break;
  meetings.push(...(page.json?.items ?? []));
  cursor = page.json?.next_cursor || undefined;
  pages++;
} while (cursor && pages < 20);

console.log(
  `${meetings.length} meeting(s) across ${pages} page(s)${cursor ? ' — more exist, capped at 20' : ''}\n`,
);

if (!meetings.length) {
  console.log('Nothing reachable. Either this account has recorded nothing,');
  console.log('or nothing has been shared with it.');
  process.exit(0);
}

/* ── 3 · WHOSE meetings — the question that decides the plan ─────── */

const byRecorder = new Map();
for (const m of meetings) {
  const who = m.recorded_by?.email ?? m.recorded_by?.name ?? 'unknown';
  byRecorder.set(who, (byRecorder.get(who) ?? 0) + 1);
}

console.log('Recorded by:');
for (const [who, n] of [...byRecorder].sort((a, b) => b[1] - a[1])) {
  console.log(`  ${String(n).padStart(4)}  ${who}`);
}

console.log(
  byRecorder.size === 1
    ? '\n  → ONE recorder. This key reaches nobody else, which is exactly\n' +
        '    what a free plan with no Team looks like. Everyone else who\n' +
        '    records would need their own key and their own webhook.\n'
    : `\n  → ${byRecorder.size} recorders. Team sharing IS reaching this key, so one\n` +
        '    key plus one webhook could cover all of them.\n',
);

const teams = [...new Set(meetings.flatMap((m) => m.shared_with ?? []).filter(Boolean))];
console.log(
  teams.length
    ? `Shared with: ${teams.join(', ')}\n`
    : 'Shared with: nothing — no team sharing on any meeting.\n',
);

/* ── 4 · the window, and whether it covers what we need ──────────── */

const stamps = meetings.map((m) => m.created_at).filter(Boolean).sort();
if (stamps.length) {
  console.log(`Oldest: ${stamps[0].slice(0, 10)}`);
  console.log(`Newest: ${stamps[stamps.length - 1].slice(0, 10)}\n`);
}

const types = [...new Set(meetings.map((m) => m.meeting_type).filter(Boolean))];
if (types.length) console.log(`Meeting types: ${types.join(', ')}\n`);

/* ── 5 · does a transcript actually come back ────────────────────── */

/* The whole point of the integration. include_transcript is documented
   as unavailable to OAuth apps, so this proves the key-based path
   specifically — the one we intend to use. */
const withText = await call('/meetings', { include_transcript: 'true' });
const sample = (withText.json?.items ?? []).find((m) => m.transcript);

if (!sample) {
  console.log('✗ No transcript on any meeting in the first page.');
  console.log('  Either they are still processing, or this account is not');
  console.log('  permitted transcripts over the API.');
} else {
  const t = sample.transcript;
  const words = Array.isArray(t) ? t.map((seg) => seg.text ?? '').join(' ') : String(t);
  console.log(`✓ transcript available — "${sample.meeting_title ?? sample.title}"`);
  console.log(
    `  ${Array.isArray(t) ? `${t.length} segments, ` : ''}${words.trim().split(/\s+/).length} words`,
  );
  console.log(`  opens: "${words.slice(0, 120).replace(/\s+/g, ' ')}…"`);
  if (Array.isArray(t) && t[0]) {
    /* Without speaker labels a client quote cannot be attributed, and
       operating rule 3 — every claim traces to its source — fails. */
    console.log(`  speaker labels: ${t[0].speaker ? 'yes' : 'NO — attribution would be lost'}`);
  }
}
console.log();

/* ── 6 · the webhook, only if asked ──────────────────────────────── */

if (!registerAt) {
  console.log('─'.repeat(58));
  console.log('To register a webhook, point it somewhere public and re-run:');
  console.log('  node --env-file=.env corpus/probe-fathom.mjs --register https://webhook.site/<id>');
  console.log('\nNothing was created or changed by this run.');
  process.exit(0);
}

if (!/^https:\/\//.test(registerAt)) {
  console.error(`✗ ${registerAt} is not an https URL. Fathom requires HTTPS.`);
  process.exit(1);
}

/* triggered_for decides the blast radius. my_recordings alone is the
   honest test on a single account — the team variants cannot fire if
   there is no team, and asking for them would hide that fact rather
   than surface it. */
const body = {
  destination_url: registerAt,
  triggered_for: ['my_recordings'],
  include_transcript: true,
  include_summary: true,
  include_action_items: true,
};

const res = await fetch(`${BASE}/webhooks`, {
  method: 'POST',
  headers: { 'X-Api-Key': KEY, 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
});
const out = await res.json().catch(() => null);

if (!res.ok) {
  console.error(`✗ ${res.status} — ${JSON.stringify(out)?.slice(0, 300)}`);
  process.exit(1);
}

console.log('✓ webhook registered');
console.log(`  id:        ${out.id}`);
console.log(`  url:       ${out.url ?? registerAt}`);
console.log(`  fires for: ${(out.triggered_for ?? []).join(', ')}`);
console.log(
  `  payload:   transcript${out.include_summary ? ' + summary' : ''}${out.include_action_items ? ' + action items' : ''}`,
);
/* Masked on purpose. Fathom issues the signing secret alongside the API
   key, not per webhook, so it is already in .env — printing it in full
   would only copy a live credential into a terminal log or a chat
   transcript for no gain. The tail is enough to confirm it is the same
   one FATHOM_WEBHOOK_SECRET holds. */
if (out.secret) {
  const tail = String(out.secret).slice(-4);
  const same = process.env.FATHOM_WEBHOOK_SECRET === out.secret;
  console.log(`\n  signing secret: whsec_…${tail}`);
  console.log(
    same
      ? '  matches FATHOM_WEBHOOK_SECRET in .env — signatures will verify'
      : '  DOES NOT match FATHOM_WEBHOOK_SECRET in .env — update it or every\n  delivery will read as a mismatch',
  );
}
console.log('\nRecord a short meeting. The POST lands once processing finishes,');
console.log('not when the call ends. Remove it in Settings → API Access when done.');
