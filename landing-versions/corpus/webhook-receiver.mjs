/* ─────────────────────────────────────────────────────────────────
   Local webhook receiver — Fathom and Zoom, one endpoint each.

   RUN:  node --env-file=.env corpus/webhook-receiver.mjs
         node --env-file=.env corpus/webhook-receiver.mjs --port 9000

   .env (all optional — an unset secret means "log, do not verify"):
     FATHOM_WEBHOOK_SECRET=whsec_...
     ZOOM_WEBHOOK_SECRET_TOKEN=...

   Writes every delivery to corpus/webhooks/ as raw JSON, untouched.

   THREE THINGS THIS DOES THAT A NAIVE RECEIVER DOES NOT

   1 · Answers before it works. Zoom stops delivering permanently after
       three failed retries (5 min, 20, 60). Any processing done before
       the 200 goes out is a chance to lose a meeting for good, so the
       response is written first and the disk write happens after.

   2 · Stores the raw body before parsing it. If the parse throws, the
       prompt changes, or the normaliser is wrong, the original is still
       on disk to re-run. This project has already lost 17 recordings to
       the assumption that a derived copy was good enough.

   3 · Never rejects silently. A signature mismatch still stores the
       payload and prints BOTH signatures, because the first real
       delivery is also how we confirm the scheme was read correctly.
       A receiver that 401s on mismatch tells you nothing about why.

   The Zoom half also answers the endpoint.url_validation challenge,
   which is what Whitney's Event Subscriptions setup needs before it
   will save. Same server, so standing this up unblocks both sources.
   ───────────────────────────────────────────────────────────────── */

import { createServer } from 'node:http';
import { createHmac, timingSafeEqual } from 'node:crypto';
import { mkdir, writeFile } from 'node:fs/promises';
import { join } from 'node:path';

const args = process.argv.slice(2);
const PORT = Number(args.includes('--port') ? args[args.indexOf('--port') + 1] : 8788);
const OUT = 'corpus/webhooks';

const FATHOM_SECRET = process.env.FATHOM_WEBHOOK_SECRET;
const ZOOM_SECRET = process.env.ZOOM_WEBHOOK_SECRET_TOKEN;

await mkdir(OUT, { recursive: true });

const now = () => new Date().toISOString().slice(11, 19);
const safe = (s) => String(s ?? 'unknown').replace(/[^\w.-]+/g, '_').slice(0, 60);

/* ── Fathom · Standard Webhooks ──────────────────────────────────────
   signed content is `${id}.${timestamp}.${rawBody}`, the secret is
   base64 AFTER its whsec_ prefix, and the header carries one or more
   space-delimited `v1,<sig>` pairs. */

const verifyFathom = (headers, raw) => {
  if (!FATHOM_SECRET) return { state: 'unchecked', why: 'FATHOM_WEBHOOK_SECRET not set' };

  const id = headers['webhook-id'];
  const ts = headers['webhook-timestamp'];
  const sent = headers['webhook-signature'];
  if (!id || !ts || !sent) return { state: 'malformed', why: 'missing webhook-* headers' };

  const drift = Math.abs(Math.floor(Date.now() / 1000) - Number(ts));
  if (drift > 300) return { state: 'stale', why: `timestamp is ${drift}s away, tolerance is 300s` };

  const key = Buffer.from(FATHOM_SECRET.replace(/^whsec_/, ''), 'base64');
  const mine = createHmac('sha256', key).update(`${id}.${ts}.${raw}`).digest('base64');

  /* Several signatures can be present during a secret rotation, so any
     match is a pass. Compared in constant time. */
  const theirs = sent.split(' ').map((p) => p.split(',')[1] ?? p);
  const hit = theirs.some((t) => {
    const a = Buffer.from(mine);
    const b = Buffer.from(t);
    return a.length === b.length && timingSafeEqual(a, b);
  });

  return hit ? { state: 'verified' } : { state: 'mismatch', mine, theirs };
};

/* ── Zoom · v0 scheme ────────────────────────────────────────────────
   message is `v0:{x-zm-request-timestamp}:{rawBody}`, hex, prefixed
   `v0=`. Different enough from Fathom's that sharing code would only
   obscure both. */

const verifyZoom = (headers, raw) => {
  if (!ZOOM_SECRET) return { state: 'unchecked', why: 'ZOOM_WEBHOOK_SECRET_TOKEN not set' };

  const ts = headers['x-zm-request-timestamp'];
  const sent = headers['x-zm-signature'];
  if (!ts || !sent) return { state: 'malformed', why: 'missing x-zm-* headers' };

  const mine = `v0=${createHmac('sha256', ZOOM_SECRET).update(`v0:${ts}:${raw}`).digest('hex')}`;
  const a = Buffer.from(mine);
  const b = Buffer.from(sent);
  const hit = a.length === b.length && timingSafeEqual(a, b);

  return hit ? { state: 'verified' } : { state: 'mismatch', mine, theirs: [sent] };
};

/* ── what came in, in one readable block ─────────────────────────── */

const describe = (source, body) => {
  const lines = [];
  const top = Object.keys(body ?? {});
  lines.push(`  top-level keys: ${top.join(', ') || '(none)'}`);

  /* Fathom nests the meeting; Zoom nests payload.object. Look in both
     rather than assuming a shape we have not seen yet. */
  const meeting = body?.meeting ?? body?.payload?.object ?? body;
  const title = meeting?.meeting_title ?? meeting?.title ?? meeting?.topic;
  if (title) lines.push(`  title: ${title}`);

  const recorder = meeting?.recorded_by?.email ?? meeting?.recorded_by?.name ?? meeting?.host_email;
  if (recorder) lines.push(`  recorded by: ${recorder}`);

  const t = body?.transcript ?? meeting?.transcript;
  if (Array.isArray(t)) {
    const words = t.map((s) => s.text ?? '').join(' ').trim().split(/\s+/).length;
    const speakers = [...new Set(t.map((s) => s.speaker?.display_name ?? s.speaker ?? null).filter(Boolean))];
    lines.push(`  transcript: ${t.length} segments, ~${words} words`);
    lines.push(
      speakers.length
        ? `  speakers: ${speakers.join(', ')}`
        : '  speakers: NONE — quotes could not be attributed',
    );
    /* Rule 3 lives or dies here: no timecode, no traceable claim. */
    const first = t[0] ?? {};
    const stamp = Object.keys(first).find((k) => /time|ts|start|offset/i.test(k));
    lines.push(stamp ? `  timecodes: yes (${stamp})` : '  timecodes: NONE — claims cannot be traced');
  } else if (typeof t === 'string') {
    lines.push(`  transcript: plain string, ${t.split(/\s+/).length} words (no speaker structure)`);
  } else {
    lines.push('  transcript: absent — check include_transcript on the webhook');
  }

  for (const k of ['default_summary', 'summary', 'action_items', 'crm_matches']) {
    if (body?.[k] ?? meeting?.[k]) lines.push(`  also present: ${k}`);
  }
  return lines.join('\n');
};

/* ── the server ──────────────────────────────────────────────────── */

const handle = async (req, res) => {
  if (req.method === 'GET') {
    res.writeHead(200, { 'content-type': 'text/plain' });
    res.end('webhook receiver up\n  POST /webhooks/fathom\n  POST /webhooks/zoom\n');
    return;
  }

  const chunks = [];
  for await (const c of req) chunks.push(c);
  const raw = Buffer.concat(chunks).toString('utf8');

  const url = (req.url ?? '').split('?')[0];
  const source = url.includes('zoom') ? 'zoom' : url.includes('fathom') ? 'fathom' : 'unknown';

  let body = null;
  try {
    body = JSON.parse(raw);
  } catch {
    /* Kept as null. The raw string is still written below. */
  }

  /* Zoom's handshake must be answered inline — it is the response body
     that validates the endpoint, so this one cannot be deferred. */
  if (body?.event === 'endpoint.url_validation') {
    const plainToken = body.payload?.plainToken ?? '';
    const encryptedToken = ZOOM_SECRET
      ? createHmac('sha256', ZOOM_SECRET).update(plainToken).digest('hex')
      : '';
    res.writeHead(200, { 'content-type': 'application/json' });
    res.end(JSON.stringify({ plainToken, encryptedToken }));
    console.log(
      `\n[${now()}] zoom · endpoint.url_validation` +
        (ZOOM_SECRET ? '  ✓ answered' : '  ✗ ZOOM_WEBHOOK_SECRET_TOKEN not set, sent empty — Zoom will refuse'),
    );
    return;
  }

  /* ANSWER FIRST. Everything below this line is after the fact. */
  res.writeHead(200, { 'content-type': 'application/json' });
  res.end('{"ok":true}');

  const check = source === 'zoom' ? verifyZoom(req.headers, raw) : verifyFathom(req.headers, raw);

  const mark = { verified: '✓', unchecked: '·', mismatch: '✗', stale: '✗', malformed: '✗' }[check.state];
  const event = body?.event ?? body?.event_type ?? 'new-meeting-content-ready';

  /* Assembled, then printed once. Deliveries that arrive together would
     otherwise interleave their lines — the disk write is awaited, so a
     second request logs in the gap and the "→ file" line ends up under
     somebody else's header. Misleading in exactly the moment you are
     leaning on this output to debug something. */
  /* Fathom marks a test delivery with is_test_event: true and OMITS the
     field entirely on real ones — it is never false. So the obvious
     filter (`=== false`) matches nothing and drops every genuine event,
     and since the test arrives FIRST for a newly registered webhook,
     deduping on recording_id keeping the earliest keeps the test and
     throws away the real delivery. Both mistakes fail silently, which
     is why this is surfaced in the log rather than left in the JSON. */
  const isTest = body?.is_test_event === true;

  const log = [`\n[${now()}] ${source} · ${event}  ${mark} ${check.state}${isTest ? '  ⚠ TEST EVENT' : ''}`];
  if (isTest) log.push('  is_test_event: true — drop this before deduping on recording_id');
  if (check.why) log.push(`  ${check.why}`);
  if (check.state === 'mismatch') {
    /* Printed so a wrong assumption about the scheme is diagnosable on
       the first delivery rather than after an afternoon of guessing. */
    log.push(`  computed: ${check.mine}`);
    log.push(`  received: ${check.theirs.join(' | ')}`);
  }
  if (body) log.push(describe(source, body));

  const id =
    body?.meeting?.recording_id ??
    body?.recording_id ??
    body?.payload?.object?.uuid ??
    req.headers['webhook-id'] ??
    Date.now();
  const file = join(OUT, `${new Date().toISOString().replace(/[:.]/g, '-')}-${source}-${safe(id)}.json`);

  await writeFile(
    file,
    JSON.stringify({ receivedAt: new Date().toISOString(), source, verification: check.state, headers: req.headers, body: body ?? raw }, null, 2),
    'utf8',
  );
  log.push(`  → ${file}`);
  console.log(log.join('\n'));
};

createServer((req, res) => {
  handle(req, res).catch((err) => {
    console.error(`  handler threw: ${err.message}`);
    if (!res.headersSent) {
      res.writeHead(200);
      res.end('{"ok":true}');
    }
  });
}).listen(PORT, () => {
  console.log(`listening on http://localhost:${PORT}`);
  console.log(`  POST /webhooks/fathom   ${FATHOM_SECRET ? 'signature checked' : 'NO SECRET — logging only'}`);
  console.log(`  POST /webhooks/zoom     ${ZOOM_SECRET ? 'signature checked' : 'no secret yet — validation will fail'}`);
  console.log(`\nDeliveries land in ${OUT}/. Expose this with a tunnel — Fathom and`);
  console.log('Zoom both require a public HTTPS URL and neither can reach localhost.');
});
