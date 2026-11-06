/* ─────────────────────────────────────────────────────────────────
   Probe the LeadLock / GHL API v2 surface.

   RUN:  node --env-file=.env corpus/probe-ghl.mjs

   .env needs:
     GHL_PIT=pit-xxxxxxxx
     GHL_LOCATION_ID=Xi40zxmRvW8Pbyk5DYHp

   READ-ONLY. Every request below is a GET. Nothing is created, updated,
   scheduled or sent.

   WHY A PROBE AND NOT A FETCHER. The one question that decides how the
   email corpus gets built is whether any endpoint returns the BODY of a
   sent campaign or only its metadata. HighLevel's docs describe create,
   update, delete and schedule for campaigns and say nothing about
   retrieving content, and the docs portal is a JS app that cannot be read
   without a browser. So: ask the API, print what it says, then write the
   fetcher against what actually exists rather than against a guess.

   The paths are candidates, not gospel. A 404 here is information.
   ───────────────────────────────────────────────────────────────── */

const TOKEN = process.env.GHL_PIT;
const LOCATION = process.env.GHL_LOCATION_ID;
const HOST = 'https://services.leadconnectorhq.com';
const VERSION = '2021-07-28';

if (!TOKEN || !LOCATION) {
  console.error('Set GHL_PIT and GHL_LOCATION_ID in .env, then run with --env-file=.env');
  process.exit(1);
}

const CANDIDATES = [
  ['auth sanity',        `/locations/${LOCATION}`],
  ['email sends',        `/emails/schedule?locationId=${LOCATION}&limit=20`],
  ['email campaigns',    `/emails/campaigns?locationId=${LOCATION}&limit=20`],
  ['email builder',      `/emails/builder?locationId=${LOCATION}&limit=20`],
  ['email templates',    `/emails/templates?locationId=${LOCATION}&limit=20`],
  ['email stats',        `/emails/statistics?locationId=${LOCATION}`],
  ['email stats alt',    `/emails/stats?locationId=${LOCATION}`],
  ['campaigns (generic)',`/campaigns?locationId=${LOCATION}&limit=20`],
  ['contacts (count)',   `/contacts/?locationId=${LOCATION}&limit=1`],
];

/* Keys whose contents would mean we can skip the copy-paste corpus. */
const BODYISH = /html|body|content|message|text|template/i;

const get = async (path) => {
  const res = await fetch(HOST + path, {
    headers: {
      Authorization: `Bearer ${TOKEN}`,
      Version: VERSION,
      Accept: 'application/json',
    },
  });
  const text = await res.text();
  let json = null;
  try { json = JSON.parse(text); } catch { /* not json */ }
  return { status: res.status, json, text };
};

/** First array found in the payload, with the key it sat under. */
const firstArray = (obj) => {
  if (Array.isArray(obj)) return ['(root)', obj];
  if (!obj || typeof obj !== 'object') return [null, null];
  for (const [k, v] of Object.entries(obj)) {
    if (Array.isArray(v) && v.length) return [k, v];
  }
  for (const v of Object.values(obj)) {
    if (v && typeof v === 'object') {
      const [k2, a] = firstArray(v);
      if (a) return [k2, a];
    }
  }
  return [null, null];
};

const describe = (json) => {
  if (!json) return '    (no JSON body)';
  const lines = [];
  lines.push(`    top-level: ${Object.keys(json).join(', ') || '(array)'}`);

  const [key, arr] = firstArray(json);
  if (!arr) {
    lines.push('    no array in payload');
    return lines.join('\n');
  }

  lines.push(`    array "${key}" · ${arr.length} item(s)`);
  const row = arr[0];
  if (!row || typeof row !== 'object') {
    lines.push(`    first item is a ${typeof row}`);
    return lines.join('\n');
  }

  lines.push(`    item keys: ${Object.keys(row).join(', ')}`);

  /* The actual question. */
  const hits = Object.entries(row).filter(
    ([k, v]) => BODYISH.test(k) && typeof v === 'string' && v.length > 40,
  );
  if (hits.length) {
    for (const [k, v] of hits) {
      const html = /<[a-z!/]/i.test(v);
      lines.push(`    ★ ${k}: ${v.length} chars${html ? ', looks like HTML' : ''}`);
    }
  } else {
    lines.push('    ✗ no body-like field on the list row — content may need a per-id GET');
  }
  return lines.join('\n');
};

console.log(`Location ${LOCATION} · API v2 · Version ${VERSION}\n`);

const reachable = [];

for (const [label, path] of CANDIDATES) {
  let r;
  try {
    r = await get(path);
  } catch (e) {
    console.log(`✗ ${label.padEnd(20)} ${path}\n    network error: ${e.message}\n`);
    continue;
  }

  const ok = r.status >= 200 && r.status < 300;
  console.log(`${ok ? '✓' : '✗'} ${label.padEnd(20)} ${r.status}  ${path}`);

  if (ok) {
    reachable.push([label, path]);
    console.log(describe(r.json));
  } else {
    /* GHL error bodies name the missing scope or the wrong version. */
    console.log(`    ${r.text.slice(0, 260).replace(/\s+/g, ' ')}`);
  }
  console.log();
}

console.log('─'.repeat(60));
console.log(`${reachable.length} of ${CANDIDATES.length} endpoints reachable:`);
for (const [label, path] of reachable) console.log(`  ${label.padEnd(20)} ${path.split('?')[0]}`);
console.log(`
Next: if a list row carries a body field (★ above), the corpus is a sync.
If not, take the campaign ids from the reachable list endpoint and try a
per-id GET, or fall back to the preview URL:
  backend.leadconnectorhq.com/emails/schedule/preview/${LOCATION}/{id}`);
