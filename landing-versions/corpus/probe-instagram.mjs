/* ─────────────────────────────────────────────────────────────────
   Probe the Instagram Graph token's actual reach.

   RUN:  node --env-file=.env corpus/probe-instagram.mjs

   .env needs:
     IG_TOKEN=      long-lived (60 days), not the 1-hour Explorer token
     IG_USER_ID=    the Instagram Business account id, not the handle

   READ-ONLY. Every call is a GET.

   WHAT IT ANSWERS. Four things about this API fail as SILENCE rather than
   as an error, and each one produces a corpus that looks fine and is not:

     · A Personal account returns an empty or malformed media edge rather
       than "this account type is unsupported".
     · The media edge pages at 25 with no total in the payload, so a
       truncated pull and a complete one are indistinguishable by eye.
     · `children` on a carousel is silently absent if the field was not
       requested or not permitted — the post still arrives, minus every
       slide.
     · Insights 400 when the permission was not granted, which is a
       documented CHOICE in instagram-app-setup.md, not a fault. The probe
       has to tell those apart or someone will go chasing a non-problem.

   It also prints the token's expiry, because the 60-day clock is the one
   operational fact most likely to bite: an expired long-lived token cannot
   be refreshed, only regenerated from step 3 of the setup guide.
   ───────────────────────────────────────────────────────────────── */

const TOKEN = process.env.IG_TOKEN;
const USER = process.env.IG_USER_ID;
const HOST = 'https://graph.facebook.com/v21.0';

if (!TOKEN || !USER) {
  console.error('Set IG_TOKEN and IG_USER_ID in .env, then run with --env-file=.env');
  console.error('See corpus/instagram-app-setup.md');
  process.exit(1);
}

const get = async (path, params = {}) => {
  const qs = new URLSearchParams({ ...params, access_token: TOKEN }).toString();
  const res = await fetch(`${HOST}/${path}?${qs}`);
  const json = await res.json().catch(() => ({}));
  return { ok: res.ok, status: res.status, json };
};

/* ── 1 · does the token work, and which account is it ────────────── */

const me = await get(USER, { fields: 'username,name,media_count,followers_count' });

if (!me.ok) {
  const err = me.json?.error ?? {};
  console.error(`✗ account lookup failed: ${me.status} ${err.message ?? ''}`);
  if (err.code === 190) console.error('  The token is invalid or has expired. Regenerate — setup guide step 3.');
  if (err.code === 100) console.error('  IG_USER_ID is probably wrong, or the account is Personal rather than Business/Creator.');
  process.exit(1);
}

const acct = me.json;
console.log(`✓ @${acct.username}${acct.name ? `  ·  ${acct.name}` : ''}`);
console.log(`  ${acct.media_count ?? '?'} posts  ·  ${(acct.followers_count ?? 0).toLocaleString()} followers\n`);

/* media_count absent is the Personal-account tell. The call succeeds, the
   field just is not there, and every downstream read comes back thin. */
if (acct.media_count == null) {
  console.log('⚠ media_count is missing. That usually means the account is Personal,');
  console.log('  not Business or Creator — see step 0 of instagram-app-setup.md.\n');
}

/* ── 2 · how long the token has left ─────────────────────────────── */

const dbg = await get('debug_token', { input_token: TOKEN });
const data = dbg.json?.data;
if (data?.expires_at === 0) {
  console.log('Token: does not expire.\n');
} else if (data?.expires_at) {
  const when = new Date(data.expires_at * 1000);
  const days = Math.round((when - Date.now()) / 86400000);
  console.log(`Token expires ${when.toISOString().slice(0, 10)} — ${days} day(s) left.`);
  if (days < 14) console.log('  ⚠ Refresh before it lapses. An expired token cannot be refreshed, only regenerated.');
  if (days <= 1) console.log('  ⚠ This looks like the 1-hour Explorer token. Exchange it — setup guide step 3.');
  console.log(`  Scopes: ${(data.scopes ?? []).join(', ') || 'none reported'}\n`);
} else {
  console.log('Token expiry could not be read (debug_token needs the app token on some setups).\n');
}

/* ── 3 · the media edge, and whether it paginates ────────────────── */

const FIELDS = 'id,caption,media_type,media_product_type,permalink,timestamp,children{id,media_type}';
const first = await get(`${USER}/media`, { fields: FIELDS, limit: '25' });

if (!first.ok) {
  console.error(`✗ media edge failed: ${first.status} ${first.json?.error?.message ?? ''}`);
  process.exit(1);
}

const page = first.json.data ?? [];
const hasNext = Boolean(first.json.paging?.next);

console.log(`Media edge: ${page.length} post(s) on page one.`);
console.log(
  hasNext
    ? '  ✓ paging.next present — there is more. The fetcher walks it; a curl test would not.'
    : '  page one is the whole corpus.',
);
if (acct.media_count && acct.media_count > page.length && !hasNext) {
  console.log(`  ⚠ the account reports ${acct.media_count} posts but no next page was offered.`);
}
console.log();

/* ── 4 · what the corpus will actually contain ───────────────────── */

const kind = (p) =>
  p.media_product_type === 'REELS' ? 'reel' : p.media_type === 'CAROUSEL_ALBUM' ? 'carousel' : 'feed';

const mix = page.reduce((a, p) => ({ ...a, [kind(p)]: (a[kind(p)] ?? 0) + 1 }), {});
const withCaption = page.filter((p) => (p.caption ?? '').trim()).length;

console.log('On this sample:');
console.log(`  feed ${mix.feed ?? 0}  ·  carousel ${mix.carousel ?? 0}  ·  reel ${mix.reel ?? 0}`);
console.log(`  ${withCaption}/${page.length} carry a caption  ${withCaption === page.length ? '✓' : ''}`);

const carousels = page.filter((p) => p.media_type === 'CAROUSEL_ALBUM');
if (carousels.length) {
  const withKids = carousels.filter((p) => (p.children?.data ?? []).length);
  const slides = withKids.reduce((n, p) => n + p.children.data.length, 0);
  console.log(`  ✓ children resolving on ${withKids.length}/${carousels.length} carousel(s) — ${slides} slides`);
  if (withKids.length < carousels.length) {
    console.log('    ⚠ a carousel with no children means the slides are invisible to the fetcher.');
  }
} else {
  console.log('  no carousel in this sample — re-run with a larger limit to confirm children resolve.');
}
console.log();

/* ── 5 · insights, which are optional by design ──────────────────── */

const sample = page[0];
if (sample) {
  const ins = await get(`${sample.id}/insights`, { metric: 'reach,saved,shares' });
  if (ins.ok) {
    const vals = (ins.json.data ?? []).map((m) => `${m.name}=${m.values?.[0]?.value ?? 0}`);
    console.log(`Insights: ✓ granted — ${vals.join('  ') || 'no values on this post'}`);
  } else {
    const msg = ins.json?.error?.message ?? '';
    console.log('Insights: not available.');
    console.log(`  ${msg.slice(0, 120)}`);
    console.log('  This is fine — instagram_business_manage_insights is optional and the');
    console.log('  fetcher records insights: null rather than failing.');
  }
}
console.log();

/* ── 6 · the honest summary ──────────────────────────────────────── */

console.log('─'.repeat(58));
console.log('What this token reaches, for the Content Atelier:');
console.log('  captions          ✓ text — the prize');
console.log('  carousel slides   images only. Copy is burned in — Canva holds it as text');
console.log('  reel scripts      ✗ spoken audio. Descript holds the transcript');
console.log('  stories           ✗ 24-hour window. Historic stories are unrecoverable');
console.log('\nSee corpus/canva-descript-access.md for the other two.');
