/* ─────────────────────────────────────────────────────────────────
   Pull @weddingindustryads posts into the corpus.

   RUN:  node --env-file=.env corpus/fetch-instagram.mjs

   Writes, per post:
     corpus/instagram/{date}-{slug}.md        frontmatter + the caption
     corpus/instagram/raw/{id}.json           the untouched API payload
     corpus/instagram/slides/{id}-{n}.{ext}   carousel slides, downloaded
     corpus/instagram/FETCHED.md              the manifest

   READ-ONLY. Every request is a GET. No permission requested by
   `instagram-app-setup.md` would allow a post, comment or reply.

   WHAT THIS ACTUALLY RECOVERS, STATED ONCE. Captions come back as text and
   that is the prize. Carousel slide copy does NOT — `children` yields one
   IMAGE per slide with the words burned into it, so this fetcher saves the
   slides and records `slide_text_extracted: false` rather than pretending
   the copy is in hand. Reel scripts are spoken audio and are not on
   Instagram in any form. Both are why `canva-descript-access.md` exists.

   That distinction is the same one `src/data/contentAtelier.ts` draws with
   `holds.transcript`, and it is the component's second operating rule:
   nothing is drafted from a source we cannot read. A fetcher that wrote
   empty `carousel_text` fields would quietly break it.

   THE FOUR THINGS A NAIVE FETCHER GETS WRONG

   1 · MEDIA URLs EXPIRE. `media_url` and `thumbnail_url` are short-lived
       signed CDN links. Recording them in the manifest and downloading
       later gets you a wall of dead URLs — so every slide is downloaded
       DURING the run, and the manifest points at the local file.

   2 · PAGINATION IS NOT OPTIONAL. The default page is 25 and there is no
       total count in the response. A run that stops at the first page looks
       successful and silently holds a fifth of the corpus. This follows
       `paging.next` to exhaustion.

   3 · `children` EXISTS ONLY ON CAROUSELS. Requested unconditionally, absent
       on everything else, and its absence is normal rather than an error.

   4 · INSIGHTS ARE A SEPARATE PERMISSION AND A SEPARATE CALL. If
       `instagram_business_manage_insights` was not granted the call 400s.
       That must not take the run down — metrics are a bonus, captions are
       the job.
   ───────────────────────────────────────────────────────────────── */

import { mkdir, writeFile } from 'node:fs/promises';
import { join, extname } from 'node:path';

const TOKEN = process.env.IG_TOKEN;
const USER = process.env.IG_USER_ID;
const HOST = 'https://graph.facebook.com/v21.0';
const OUT = 'corpus/instagram';

if (!TOKEN || !USER) {
  console.error('Set IG_TOKEN and IG_USER_ID in .env, then run with --env-file=.env');
  console.error('See corpus/instagram-app-setup.md');
  process.exit(1);
}

await mkdir(join(OUT, 'raw'), { recursive: true });
await mkdir(join(OUT, 'slides'), { recursive: true });

/* IG Graph allows ~200 calls an hour per user. A back catalogue of a few
   hundred posts plus per-post insights sits close enough to that to be worth
   pacing, and the run is not time-critical. */
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const FIELDS = [
  'id',
  'caption',
  'media_type',
  'media_product_type',
  'permalink',
  'timestamp',
  'media_url',
  'thumbnail_url',
  'like_count',
  'comments_count',
  'children{id,media_type,media_url,thumbnail_url}',
].join(',');

/* ── 1 · page through every post ─────────────────────────────────── */

const posts = [];
let url = `${HOST}/${USER}/media?fields=${encodeURIComponent(FIELDS)}&limit=50&access_token=${TOKEN}`;
let page = 0;

while (url) {
  const res = await fetch(url);
  if (!res.ok) {
    const body = await res.text();
    console.error(`\nlist failed on page ${page}: ${res.status}`);
    console.error(body.slice(0, 400));
    /* Page one failing is a bad token or a Personal account. A later page
       failing means we hold a partial corpus, which is worth keeping. */
    if (page === 0) process.exit(1);
    break;
  }
  const json = await res.json();
  posts.push(...(json.data ?? []));
  process.stdout.write(`  page ${page}: ${(json.data ?? []).length} posts (${posts.length} total)\n`);
  url = json.paging?.next ?? null;
  page++;
  if (url) await sleep(400);
}

console.log(`\n${posts.length} posts\n`);

/* ── 2 · helpers ─────────────────────────────────────────────────── */

const slug = (s) =>
  (s || 'untitled')
    .toLowerCase()
    .replace(/https?:\/\/\S+/g, ' ')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '')
    .slice(0, 60)
    .replace(/-$/, '') || 'untitled';

const yaml = (s) => `"${String(s ?? '').replace(/\\/g, '\\\\').replace(/"/g, '\\"')}"`;

/* Optional. A 400 here means the insights permission was not granted, which
   is a documented choice in the setup guide, not a failure. */
const insights = async (id, isReel) => {
  const metrics = isReel
    ? 'reach,saved,shares,likes,comments'
    : 'reach,saved,shares';
  try {
    const res = await fetch(
      `${HOST}/${id}/insights?metric=${metrics}&access_token=${TOKEN}`,
    );
    if (!res.ok) return null;
    const json = await res.json();
    return Object.fromEntries(
      (json.data ?? []).map((m) => [m.name, m.values?.[0]?.value ?? 0]),
    );
  } catch {
    return null;
  }
};

/* Slides are downloaded now because the CDN URL will not resolve later.
   Content-type is checked before anything is written — the same trap the
   Slack fetcher documents, where an expired or unauthorised link returns an
   HTML error page with a 200 and a naive writer saves it as a .jpg. */
const saveSlide = async (src, base) => {
  try {
    const res = await fetch(src);
    if (!res.ok) return null;
    const type = res.headers.get('content-type') ?? '';
    if (!/^(image|video)\//.test(type)) return null;
    const ext = extname(new URL(src).pathname) || (type.startsWith('video') ? '.mp4' : '.jpg');
    const name = `${base}${ext}`;
    await writeFile(join(OUT, 'slides', name), Buffer.from(await res.arrayBuffer()));
    return `slides/${name}`;
  } catch {
    return null;
  }
};

/* ── 3 · write one file per post ─────────────────────────────────── */

const index = [];

for (const p of posts) {
  const date = (p.timestamp ?? '').slice(0, 10);
  const caption = (p.caption ?? '').trim();
  const firstLine = caption.split('\n').find((l) => l.trim()) ?? '';
  const isCarousel = p.media_type === 'CAROUSEL_ALBUM';
  const isReel = p.media_product_type === 'REELS';
  const kind = isReel ? 'reel' : isCarousel ? 'carousel' : 'feed';
  const name = `${date}-${slug(firstLine)}.md`;

  await writeFile(join(OUT, 'raw', `${p.id}.json`), JSON.stringify(p, null, 2), 'utf8');

  const slides = [];
  if (isCarousel) {
    const kids = p.children?.data ?? [];
    for (const [i, kid] of kids.entries()) {
      const src = kid.media_url ?? kid.thumbnail_url;
      if (!src) continue;
      const saved = await saveSlide(src, `${p.id}-${String(i + 1).padStart(2, '0')}`);
      if (saved) slides.push(saved);
      await sleep(150);
    }
  }

  const stats = await insights(p.id, isReel);
  await sleep(250);

  const front = [
    '---',
    `post_id: ${yaml(p.id)}`,
    `kind: ${kind}`,
    `media_type: ${yaml(p.media_type)}`,
    `posted: ${date}`,
    `permalink: ${p.permalink ?? ''}`,
    `likes: ${p.like_count ?? ''}`,
    `comments: ${p.comments_count ?? ''}`,
    stats ? `insights:\n${Object.entries(stats).map(([k, v]) => `  ${k}: ${v}`).join('\n')}` : 'insights: null',
    `raw: ${yaml(`raw/${p.id}.json`)}`,
    isCarousel ? `slide_count: ${slides.length}` : null,
    isCarousel ? `slides:\n${slides.map((s) => `  - ${s}`).join('\n') || '  []'}` : null,
    /* The honest flags. Neither is a TODO — each names a source this fetcher
       structurally cannot reach, and points at the one that can. */
    isCarousel ? 'slide_text_extracted: false  # burned into the images — Canva holds it as text' : null,
    isReel ? 'script_held: false  # spoken audio — Descript holds the transcript' : null,
    '# Only Whitney or Giselle can fill this.',
    'source_session: ""',
    '---',
    '',
    '## Caption',
    '',
    caption || '_no caption_',
    '',
  ]
    .filter((l) => l !== null)
    .join('\n');

  await writeFile(join(OUT, name), front, 'utf8');
  index.push({ date, kind, file: name, permalink: p.permalink, slides: slides.length, caption });
  process.stdout.write(`  ${date}  ${kind.padEnd(8)} ${name}\n`);
}

/* ── 4 · the manifest ────────────────────────────────────────────── */

index.sort((a, b) => (a.date < b.date ? 1 : -1));

const counts = index.reduce((a, r) => ({ ...a, [r.kind]: (a[r.kind] ?? 0) + 1 }), {});
const words = index.reduce((a, r) => a + r.caption.split(/\s+/).filter(Boolean).length, 0);

const manifest = `# Instagram corpus — fetched

Pulled from the Instagram Graph API on ${new Date().toISOString().slice(0, 10)} by
\`corpus/fetch-instagram.mjs\`. **${index.length} posts** from
[@weddingindustryads](https://www.instagram.com/weddingindustryads).

${counts.feed ?? 0} feed · ${counts.carousel ?? 0} carousel · ${counts.reel ?? 0} reel
· ~${words.toLocaleString()} words of approved caption copy.

## What is text here, and what is not

| Asset | Held | Where the text actually is |
|---|---|---|
| **Captions** | **Yes** — all ${index.length} | Here |
| Carousel slide copy | No — ${index.filter((r) => r.kind === 'carousel').reduce((a, r) => a + r.slides, 0)} slide images saved under \`slides/\` | **Canva** — see \`../canva-descript-access.md\` |
| Reel scripts | No — spoken audio | **Descript** — same document |

Every carousel file carries \`slide_text_extracted: false\` and every reel
carries \`script_held: false\`. Those are not TODOs to clear by guessing; they
are the component's second operating rule applied to this corpus — nothing is
drafted from a source we cannot read.

\`source_session\` is blank in every file for the same reason it is blank across
\`corpus/emails/\` — only Whitney or Giselle know which call a post came from, and
that mapping is what turns a style sample into an input/output pair.

| Posted | Kind | Caption opens | File |
|---|---|---|---|
${index
  .map(
    (r) =>
      `| ${r.date} | ${r.kind} | ${(r.caption.split('\n')[0] ?? '').slice(0, 60).replace(/\|/g, '\\|')} | [${r.file}](./${r.file}) |`,
  )
  .join('\n')}
`;

await writeFile(join(OUT, 'FETCHED.md'), manifest, 'utf8');

console.log(`\n${index.length} posts written to ${OUT}/`);
console.log(`Manifest: ${OUT}/FETCHED.md`);
