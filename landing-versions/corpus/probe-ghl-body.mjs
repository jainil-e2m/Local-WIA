/* ─────────────────────────────────────────────────────────────────
   Second probe: can we actually get an email's BODY?

   RUN:  node --env-file=.env corpus/probe-ghl-body.mjs

   The first probe found /emails/schedule returning rows with three URL
   fields — downloadUrl, templateDataDownloadUrl, nonTrackingDownloadUrl.
   Those are the candidates for the rendered email. This dumps one whole
   record, follows each URL both unauthenticated and with the bearer, and
   reports what comes back.

   It also hunts for the statistics endpoint. `emails/stats.readonly` is a
   real scope in this tenant, so an endpoint exists; /emails/statistics and
   /emails/stats both 404, which means it is shaped differently — most
   likely per-schedule.

   READ-ONLY. Every request is a GET.
   ───────────────────────────────────────────────────────────────── */

const TOKEN = process.env.GHL_PIT;
const LOCATION = process.env.GHL_LOCATION_ID;
const HOST = 'https://services.leadconnectorhq.com';
const VERSION = '2021-07-28';

if (!TOKEN || !LOCATION) {
  console.error('Set GHL_PIT and GHL_LOCATION_ID in .env, then run with --env-file=.env');
  process.exit(1);
}

const auth = {
  Authorization: `Bearer ${TOKEN}`,
  Version: VERSION,
  Accept: 'application/json',
};

const list = await fetch(
  `${HOST}/emails/schedule?locationId=${LOCATION}&limit=5`,
  { headers: auth },
).then((r) => r.json());

const rows = list.schedules ?? [];
console.log(`${list.total ?? '?'} schedules total, showing structure of 1\n`);

if (!rows.length) {
  console.error('No schedules returned.');
  process.exit(1);
}

/* ── the sent ones are what the corpus wants ─────────────────────── */
const sent = rows.filter((r) => /sent|completed/i.test(r.status ?? r.emailStatus ?? ''));
const row = sent[0] ?? rows[0];

console.log('─── full record ───');
console.log(JSON.stringify(row, null, 2).slice(0, 4000));
console.log();

console.log('─── the fields that matter ───');
for (const k of ['id', '_id', 'name', 'subject', 'status', 'emailStatus', 'templateId', 'dateScheduled', 'dateAdded']) {
  if (row[k] !== undefined) console.log(`  ${k}: ${JSON.stringify(row[k])}`);
}
console.log();

/* ── follow every URL field ──────────────────────────────────────── */
const urlFields = Object.entries(row).filter(
  ([, v]) => typeof v === 'string' && /^https?:\/\//.test(v),
);

console.log(`─── following ${urlFields.length} URL field(s) ───`);

for (const [key, url] of urlFields) {
  console.log(`\n${key}`);
  console.log(`  ${url.slice(0, 120)}${url.length > 120 ? '…' : ''}`);

  for (const [mode, headers] of [['no auth', {}], ['bearer', auth]]) {
    try {
      const res = await fetch(url, { headers });
      const ct = res.headers.get('content-type') ?? '?';
      const body = await res.text();
      const looksHtml = /<(html|body|table|div|p)\b/i.test(body);
      console.log(
        `  ${mode.padEnd(8)} ${res.status}  ${ct.split(';')[0]}  ${body.length} chars${looksHtml ? '  ← HTML' : ''}`,
      );
      if (res.ok && body.length) {
        console.log(`    ${body.slice(0, 300).replace(/\s+/g, ' ')}`);
        break; /* first mode that works is enough */
      }
    } catch (e) {
      console.log(`  ${mode.padEnd(8)} error: ${e.message}`);
    }
  }
}

/* ── hunt for statistics ─────────────────────────────────────────── */
const id = row.id ?? row._id;
console.log(`\n─── statistics candidates for schedule ${id} ───`);

const statPaths = [
  `/emails/schedule/${id}`,
  `/emails/schedule/${id}/stats`,
  `/emails/schedule/${id}/statistics`,
  `/emails/${id}/stats`,
  `/emails/stats/${id}`,
  `/emails/statistics/${id}`,
  `/emails/schedule/stats?locationId=${LOCATION}&scheduleId=${id}`,
  `/emails/stats?locationId=${LOCATION}&emailId=${id}`,
];

for (const p of statPaths) {
  try {
    const res = await fetch(HOST + p, { headers: auth });
    const text = await res.text();
    const ok = res.ok;
    console.log(`  ${ok ? '✓' : '✗'} ${res.status}  ${p}`);
    if (ok) console.log(`      ${text.slice(0, 400).replace(/\s+/g, ' ')}`);
  } catch (e) {
    console.log(`  ✗ ${p} — ${e.message}`);
  }
}

/* ── the preview URL we already knew about ───────────────────────── */
console.log('\n─── preview URL (the one from the handover) ───');
const preview = `https://backend.leadconnectorhq.com/emails/schedule/preview/${LOCATION}/${id}`;
for (const [mode, headers] of [['no auth', {}], ['bearer', auth]]) {
  try {
    const res = await fetch(preview, { headers });
    const body = await res.text();
    console.log(`  ${mode.padEnd(8)} ${res.status}  ${body.length} chars  ${/<(html|body|table)/i.test(body) ? '← HTML' : ''}`);
    if (res.ok && body.length > 200) {
      console.log(`    ${body.slice(0, 300).replace(/\s+/g, ' ')}`);
      break;
    }
  } catch (e) {
    console.log(`  ${mode.padEnd(8)} error: ${e.message}`);
  }
}
