/* ─────────────────────────────────────────────────────────────────
   Pull WIA's sent marketing emails out of LeadLock into the corpus.

   RUN:  node --env-file=.env corpus/fetch-emails.mjs

   Writes, per sent campaign:
     corpus/emails/raw/{id}.html        the email exactly as it went out
     corpus/emails/{date}-{slug}.md     frontmatter + extracted plain text

   READ-ONLY against the API. Every request is a GET and nothing is
   created, scheduled or sent.

   CORRECTED 22 Sep. An earlier version of this comment claimed
   nonTrackingDownloadUrl preserves real destination hrefs. It does not —
   both rendered variants still route every link through
   link.msgsndr.com/email-tracking/..., so neither yields the offer map.

   The real destinations live in templateDataDownloadUrl, the MJML editor
   payload: what Whitney typed, before GHL rewrote it for click tracking.
   That is where `cta_urls` below comes from, and it is what closes the "no
   destination URLs" gap in prompts/marketing-email.md §6.

   nonTrackingDownloadUrl is still the better body source — it omits the
   open-tracking pixel — but that is the only difference.

   The download URLs are Firebase signed links and need no Authorization
   header; the bearer is only for the list call.
   ───────────────────────────────────────────────────────────────── */

import { mkdir, writeFile } from 'node:fs/promises';
import { join } from 'node:path';

const TOKEN = process.env.GHL_PIT;
const LOCATION = process.env.GHL_LOCATION_ID;
const HOST = 'https://services.leadconnectorhq.com';
const VERSION = '2021-07-28';
const OUT = 'corpus/emails';

if (!TOKEN || !LOCATION) {
  console.error('Set GHL_PIT and GHL_LOCATION_ID in .env, then run with --env-file=.env');
  process.exit(1);
}

const auth = { Authorization: `Bearer ${TOKEN}`, Version: VERSION, Accept: 'application/json' };

/* ── 1 · page through every schedule ─────────────────────────────── */

const all = [];
const seen = new Set();

for (let offset = 0; offset < 400; offset += 20) {
  const res = await fetch(
    `${HOST}/emails/schedule?locationId=${LOCATION}&limit=20&offset=${offset}`,
    { headers: auth },
  );
  if (!res.ok) {
    console.error(`list failed at offset ${offset}: ${res.status}`);
    break;
  }
  const page = (await res.json()).schedules ?? [];
  const fresh = page.filter((r) => !seen.has(r.id));
  fresh.forEach((r) => seen.add(r.id));
  all.push(...fresh);
  process.stdout.write(`  offset ${offset}: ${page.length} rows, ${fresh.length} new\n`);
  /* Some tenants ignore offset and keep returning page one — stop on that
     as well as on a short page. */
  if (page.length < 20 || fresh.length === 0) break;
}

const sent = all.filter(
  (r) => /complete|sent/i.test(r.status ?? '') && !r.deleted && !r.archived,
);

console.log(`\n${all.length} schedules, ${sent.length} sent\n`);

/* ── 2 · helpers ─────────────────────────────────────────────────── */

const htmlToText = (html) =>
  html
    .replace(/<!--[\s\S]*?-->/g, '')
    .replace(/<(script|style)\b[\s\S]*?<\/\1>/gi, '')
    /* Keep link destinations — this is where the CTA URLs come from. */
    .replace(/<a\b[^>]*href=["']([^"']+)["'][^>]*>([\s\S]*?)<\/a>/gi, (_, href, txt) => {
      const t = txt.replace(/<[^>]+>/g, '').replace(/\s+/g, ' ').trim();
      return t ? `${t} <${href}>` : `<${href}>`;
    })
    .replace(/<\/(p|div|tr|li|h[1-6]|table|td)>/gi, '\n')
    .replace(/<br\s*\/?>/gi, '\n')
    .replace(/<[^>]+>/g, '')
    .replace(/&nbsp;/gi, ' ')
    .replace(/&amp;/gi, '&')
    .replace(/&lt;/gi, '<')
    .replace(/&gt;/gi, '>')
    .replace(/&quot;/gi, '"')
    .replace(/&#0?39;|&apos;|&rsquo;/gi, "'")
    .replace(/&[a-z]+;/gi, ' ')
    .split('\n')
    .map((l) => l.replace(/[ \t]+/g, ' ').trim())
    .filter(Boolean)
    .join('\n')
    .replace(/\n{3,}/g, '\n\n');

/* The offer map, recovered from the editor payload. The rendered HTML only
   has link.msgsndr.com redirects; these are the hrefs as written. */
const NOISE = /fonts\.googleapis|gstatic|msgsndr|firebasestorage|filesafe\.space|storage\.googleapis|w3\.org|schemas|\.(png|jpe?g|gif|webp|svg)$/i;

const ctaUrls = async (url) => {
  if (!url) return [];
  try {
    const raw = await fetch(url).then((r) => (r.ok ? r.text() : ''));
    return [
      ...new Set(
        /* Stop at whitespace, quotes, backslash AND angle brackets. Without
           the brackets the match runs straight on into the markup that
           follows the href, producing entries like
           ".../workshop</strong></span></a><br>". */
        [...raw.matchAll(/https?:\/\/[^\s"'<>\\]{6,200}/g)]
          .map((m) => m[0].replace(/[),.;]+$/, '').replace(/&amp;/g, '&')),
      ),
    ]
      .filter((u) => !NOISE.test(u))
      .filter((u) => !/facebook\.com|instagram\.com|youtube\.com/.test(u));
  } catch {
    return [];
  }
};

/* Group by origin + path. The same page arrives with _gl, utm_source and
   affiliate params attached, and four spellings of one URL is not an offer
   map, it is four rows of noise. */
const canonical = (u) => {
  try {
    const p = new URL(u);
    return (p.origin + p.pathname).replace(/\/$/, '').toLowerCase();
  } catch {
    return u;
  }
};

const WIA = /(^|\.)weddingindustryads\.com$|(^|\.)leadlockpro\.com$/i;

/* The campaign name is the log Whitney described: subject, date, CTA. */
const parseName = (name = '') => {
  const m = name.match(/^(.*?)\s+(\d{1,2}\.\d{1,2}\.\d{2})\s*\|\s*(.+?)\s*CTA\s*$/i);
  return m ? { titled: m[1].trim(), dated: m[2], cta: m[3].trim() } : {};
};

const slug = (s) =>
  s.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 55);

const iso = (ms) => (ms ? new Date(ms).toISOString().slice(0, 10) : 'undated');
const yaml = (v) => JSON.stringify(v ?? '');

/* ── 3 · fetch each body and write it out ────────────────────────── */

await mkdir(join(OUT, 'raw'), { recursive: true });

const index = [];

for (const r of sent) {
  const url = r.nonTrackingDownloadUrl || r.downloadUrl;
  if (!url) {
    console.log(`  ✗ ${r.name} — no download URL`);
    continue;
  }

  const res = await fetch(url);
  if (!res.ok) {
    console.log(`  ✗ ${r.name} — body ${res.status}`);
    continue;
  }

  const html = await res.text();
  const text = htmlToText(html);
  const { cta } = parseName(r.name);
  const urls = await ctaUrls(r.templateDataDownloadUrl);
  const date = iso(r.dateScheduled || r.dateAdded);
  const file = `${date}-${slug(r.subject || r.name)}.md`;

  await writeFile(join(OUT, 'raw', `${r.id}.html`), html, 'utf8');

  const md = `---
campaign_name: ${yaml(r.name)}
subject: ${yaml(r.subject)}
cta_from_name: ${yaml(cta)}
sent: ${date}
recipients: ${r.totalCount ?? ''}
delivered: ${r.successCount ?? ''}
failed: ${r.failed ?? ''}
sending_domain: ${yaml(r.selectedDomain)}
last_edited_by: ${yaml(r.updatedByName)}
tracking: ${r.hasTracking ? 'on' : 'off'}
schedule_id: ${yaml(r.id)}
template_id: ${yaml(r.templateId)}
raw_html: ${yaml(`raw/${r.id}.html`)}
cta_urls:${urls.length ? '\n' + urls.map((u) => `  - ${u}`).join('\n') : ' []'}
# Only Whitney or Giselle can fill these two.
source_session: ""
instagram_sibling: ""
---

## Body

${text}
`;

  await writeFile(join(OUT, file), md, 'utf8');
  index.push({ date, subject: r.subject, cta, recipients: r.totalCount, file, urls });
  console.log(`  ✓ ${date}  ${(r.subject || '').slice(0, 44).padEnd(46)} ${text.length} chars`);
}

/* ── 4 · a manifest, sorted newest first ─────────────────────────── */

index.sort((a, b) => b.date.localeCompare(a.date));

const manifest = `# Email corpus — fetched

Pulled from LeadLock on ${new Date().toISOString().slice(0, 10)} by
\`corpus/fetch-emails.mjs\`. ${index.length} sent campaigns.

Body text is extracted from \`nonTrackingDownloadUrl\`; raw HTML is kept beside
each one under \`raw/\`. Note that the links **inside the body** are
link.msgsndr.com click-redirects — both rendered variants carry them. The real
destinations are in \`cta_urls\`, recovered separately from the editor payload.
See [OFFER-MAP.md](./OFFER-MAP.md).

\`source_session\` and \`instagram_sibling\` are blank in every file. They
cannot be derived from the API — only Whitney or Giselle know which call each
email came from, and that mapping is what turns this from a style sample into
input/output pairs.

| Sent | Subject | CTA | Recipients | File |
|---|---|---|---|---|
${index.map((r) => `| ${r.date} | ${r.subject ?? ''} | ${r.cta ?? ''} | ${r.recipients ?? ''} | [${r.file}](./${r.file}) |`).join('\n')}
`;

const stats = new Map(); /* canonical url -> {ctas, emails, sample} */
for (const row of index) {
  for (const c of new Set((row.urls ?? []).map(canonical))) {
    if (!stats.has(c)) stats.set(c, { ctas: new Set(), emails: 0, sample: c });
    const e = stats.get(c);
    e.emails++;
    if (row.cta) e.ctas.add(row.cta);
  }
}

/* A link in most emails is footer chrome, not a call to action. Attributing
   every CTA label to the homepage tells us nothing. */
const BOILERPLATE = Math.max(3, Math.floor(index.length * 0.4));
const rows = [...stats.entries()]
  .filter(([, e]) => e.emails < BOILERPLATE)
  .sort((a, b) => b[1].ctas.size - a[1].ctas.size || b[1].emails - a[1].emails);

const host = (u) => { try { return new URL(u).hostname; } catch { return ''; } };
const table = (list) =>
  list.length
    ? `| Destination | Labelled CTA | Emails |
|---|---|---|
` +
      list.map(([u, e]) => `| ${u} | ${[...e.ctas].join(' · ') || '—'} | ${e.emails} |`).join('\n')
    : '_none_';

const offerMap = `# Offer map — CTA destinations

Recovered from each campaign's \`templateDataDownloadUrl\` (the MJML editor
payload). The rendered HTML only carries link.msgsndr.com click-redirects, so
these are the hrefs as originally written.

This is the gap \`prompts/marketing-email.md\` §6 records as blocking: the
engine could name a CTA but not link it.

Grouped by origin + path, so the same page arriving with \`_gl\`, \`utm_source\`
or affiliate params is one row. Links appearing in ${BOILERPLATE}+ of the
${index.length} emails are treated as footer chrome and excluded — otherwise the
homepage collects every CTA label and means nothing.

## WIA-owned

${table(rows.filter(([u]) => WIA.test(host(u))))}

## Third party and affiliate

Partner promotions and affiliate links. Not WIA offers — listed so nobody
mistakes one for a destination the engine may use.

${table(rows.filter(([u]) => !WIA.test(host(u))))}

---

${index.filter((r) => !(r.urls ?? []).length).length} of ${index.length} emails carry no destination at all, which is consistent
with reply-bait being the most-used CTA in the 2026 set.
`;

await writeFile(join(OUT, 'OFFER-MAP.md'), offerMap, 'utf8');
await writeFile(join(OUT, 'FETCHED.md'), manifest, 'utf8');

console.log(`\n${index.length} emails written to ${OUT}/`);
console.log(`Manifest: ${OUT}/FETCHED.md`);
