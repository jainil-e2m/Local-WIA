/* ─────────────────────────────────────────────────────────────────
   Pull Slack channel history into the corpus.

   RUN:  node --env-file=.env corpus/fetch-slack.mjs        (every channel
                                                             the bot is in)
         node --env-file=.env corpus/fetch-slack.mjs wia-ai-team-testing

   Writes:
     corpus/slack/{channel}.md        chronological, with permalinks
     corpus/slack/raw/{channel}.json  the untouched API payloads
     corpus/slack/files/{id}-{name}   attachments under the size cap
     corpus/slack/_INDEX.md           what was pulled, and what was skipped

   READ-ONLY against Slack. Every call is a read method.

   THE TARGET LIST IS DERIVED, NOT HARDCODED

   With no arguments this pulls every channel the bot is a member of, minus
   the test channel. Naming the six by hand would go stale the first time
   Gisselle adds the bot to a new client channel — and it would go stale
   SILENTLY, producing a clean run that quietly skipped a channel. Asking
   Slack what the bot can see cannot drift from what the bot can see.

   THE FOUR THINGS THIS DOES THAT A NAIVE READER DOES NOT

   1 · Walks threads. conversations.history returns parent messages only, so
       a client quote relayed as a reply is invisible to it — and it fails as
       absence, not as an error. Every message with reply_count > 0 gets a
       conversations.replies call. Same scopes, second endpoint.

   2 · Checks what it downloaded. A file's url_private_download returns a
       LOGIN PAGE with a 200 when the Authorization header is missing or
       wrong, so a naive fetcher writes HTML into a .webp and never notices.
       Content-type is verified before anything is written.

   3 · Builds permalinks without asking. chat.getPermalink would be one call
       per message; the URL is deterministic from the workspace domain, the
       channel id and the ts, so provenance links cost nothing. Operating
       rule #3 — every claim traces to its source — applies to Slack the
       same way timecodes apply to transcripts.

   4 · Caps what it downloads, and says so in the output. Office-hours
       recordings in these channels run 140–200 MB each; pulling every one
       would move gigabytes of video into a directory git ignores anyway,
       to no benefit — the transcript is the part the Atelier reads, and it
       already has 150 of those from Zoom. Skipped files are NOT dropped:
       name, size and URL go into the channel markdown, so a recording that
       turns out to matter can be fetched deliberately later. A silent skip
       would be the same failure mode as a missed channel.
   ───────────────────────────────────────────────────────────────── */

import { readdirSync, readFileSync } from 'node:fs';
import { mkdir, writeFile } from 'node:fs/promises';
import { join } from 'node:path';

const TOKEN = process.env.SLACK_BOT_TOKEN;
const OUT = 'corpus/slack';

if (!TOKEN) {
  console.error('Set SLACK_BOT_TOKEN in .env, then run with --env-file=.env');
  process.exit(1);
}

const args = process.argv.slice(2);

/* Explicit arguments, or SLACK_CHANNELS, or — the normal case — everything
   the bot can reach. An empty WANTED means "ask Slack", resolved below
   against users.conversations rather than guessed at here. */
const WANTED = (args.length ? args : (process.env.SLACK_CHANNELS ?? '').split(','))
  .map((s) => s.trim().replace(/-/g, ' ').toLowerCase())
  .filter(Boolean);

/* Our own sandbox. It holds our test messages, not WIA's, so it is noise in
   a corpus meant to be read for client signal. Name it to include it. */
const EXCLUDE = /^wia[- ]ai[- ]team[- ]testing$/i;

/* Office-hours recordings run 140–200 MB. 25 MB keeps every screenshot,
   PDF, CSV and deck — the things that actually carry campaign detail —
   and leaves the video behind with a pointer to it. */
const MAX_FILE_MB = Number(process.env.SLACK_MAX_FILE_MB ?? 25);
const MAX_FILE_BYTES = MAX_FILE_MB * 1024 * 1024;

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

/* conversations.* is Tier 3 — about 50 requests a minute. users.info is
   Tier 4 and far more forgiving. Pacing them the same either crawls through
   the cheap calls or trips the expensive ones; the retry below is the
   safety net, not the plan. This is somebody else's production workspace. */
const TIER3 = /^conversations\./;
const paceFor = (method) => (TIER3.test(method) ? 1200 : 300);

const call = async (method, params = {}) => {
  const qs = new URLSearchParams(params).toString();
  const res = await fetch(`https://slack.com/api/${method}${qs ? '?' + qs : ''}`, {
    headers: { Authorization: `Bearer ${TOKEN}` },
  });
  const json = await res.json();
  if (!json.ok && json.error === 'ratelimited') {
    const wait = Number(res.headers.get('retry-after') ?? 5) * 1000;
    console.log(`    rate limited, waiting ${wait / 1000}s`);
    await sleep(wait);
    return call(method, params);
  }
  await sleep(paceFor(method));
  return json;
};

/* ── who we are, and the workspace domain for permalinks ─────────── */

const me = await call('auth.test');
if (!me.ok) {
  console.error(`auth.test failed: ${me.error}`);
  process.exit(1);
}
const domain = (me.url ?? '').replace(/\/$/, '');
console.log(`${me.team} · bot ${me.user}\n`);

const permalink = (channelId, ts) => `${domain}/archives/${channelId}/p${ts.replace('.', '')}`;

/* ── user names, resolved once each ──────────────────────────────── */

const userCache = new Map();
const userName = async (id) => {
  if (!id) return 'unknown';
  if (userCache.has(id)) return userCache.get(id);
  const r = await call('users.info', { user: id });
  const name = r.ok ? r.user.profile?.real_name || r.user.name : id;
  userCache.set(id, name);
  return name;
};

/* An app posts with a bot_id, and users.info cannot resolve one — it fails,
   and the raw "B09ANRU4AUW" lands in the markdown as the author. Slack
   already puts the readable name on the message as `username`, so no extra
   call and no extra scope is needed to do better.

   Worth the few lines: the bot in these channels is the one announcing new
   signups ("X has joined on for the Google Search Accelerator"), which is a
   client-acquisition timeline. Attributed to an opaque id, it reads as
   machine noise and gets skipped. */
const authorOf = async (m) =>
  m.user ? userName(m.user) : (m.username ?? m.bot_profile?.name ?? m.bot_id ?? 'unknown');

/* ── which channels the bot can actually reach ───────────────────── */

const mine = await call('users.conversations', {
  types: 'public_channel,private_channel',
  limit: '200',
  exclude_archived: 'true',
});
if (!mine.ok) {
  console.error(`users.conversations failed: ${mine.error}`);
  process.exit(1);
}

const reachable = mine.channels ?? [];

const targets = WANTED.length
  ? WANTED.map((want) => ({
      want,
      hit: reachable.find((c) => c.name.replace(/-/g, ' ').toLowerCase().includes(want)),
    })).filter((t) => {
      if (!t.hit) console.log(`✗ "${t.want}" — not found, or the bot was never invited`);
      return t.hit;
    })
  : reachable.filter((c) => !EXCLUDE.test(c.name)).map((hit) => ({ want: hit.name, hit }));

if (!targets.length) {
  console.error('\nNo target channels reachable. Invite the bot, then re-run.');
  process.exit(1);
}

/* Say what is about to happen before it happens. A run that silently pulls
   five channels when the bot is in six is the failure this guards against,
   and it is only visible if the skipped one is named. */
const skipped = reachable.filter((c) => !targets.some((t) => t.hit.id === c.id));
console.log(`Pulling ${targets.length} of ${reachable.length} reachable channel(s):`);
for (const { hit } of targets) console.log(`  ${hit.is_private ? '🔒' : '# '} ${hit.name}`);
if (skipped.length) {
  console.log(`Not pulled: ${skipped.map((c) => '#' + c.name).join(', ')}`);
}
console.log(`Files over ${MAX_FILE_MB} MB are recorded but not downloaded.\n`);

await mkdir(join(OUT, 'raw'), { recursive: true });
await mkdir(join(OUT, 'files'), { recursive: true });

/* ── per channel ─────────────────────────────────────────────────── */

const summary = [];

for (const { hit } of targets) {
  console.log(`#${hit.name}`);

  /* history, paginated */
  const messages = [];
  let cursor;
  do {
    const page = await call('conversations.history', {
      channel: hit.id,
      limit: '200',
      ...(cursor ? { cursor } : {}),
    });
    if (!page.ok) {
      console.log(`  history failed — ${page.error}`);
      break;
    }
    messages.push(
      ...(page.messages ?? []).filter((m) => {
        /* Joins and leaves are not signal. */
        if (m.subtype === 'channel_join' || m.subtype === 'channel_leave') return false;
        /* conversations.history ALSO returns thread replies at top level, so
           without this every reply is rendered twice — once threaded under
           its parent and once as a standalone message. A reply is any
           message whose thread_ts points at somebody else. */
        if (m.thread_ts && m.thread_ts !== m.ts) return false;
        return true;
      }),
    );
    cursor = page.response_metadata?.next_cursor || undefined;
  } while (cursor);

  console.log(`  ${messages.length} parent message(s)`);

  /* threads */
  let replyCount = 0;
  for (const m of messages) {
    if (!(m.reply_count > 0)) continue;
    /* Paginated. A single limit:200 call silently truncates any thread
       longer than that — no error, no flag, just a short answer that looks
       complete. Office-hours threads are the ones that would hit it first.

       Only the FIRST page repeats the parent at [0]; later pages do not, so
       the slice cannot be applied unconditionally or it eats a real reply
       off every page after the first. */
    const kids = [];
    let rc;
    let page = 0;
    do {
      const r = await call('conversations.replies', {
        channel: hit.id,
        ts: m.thread_ts ?? m.ts,
        limit: '200',
        ...(rc ? { cursor: rc } : {}),
      });
      if (!r.ok) {
        console.log(`  ✗ thread ${m.ts} — ${r.error}`);
        break;
      }
      kids.push(...(r.messages ?? []).slice(page === 0 ? 1 : 0));
      rc = r.response_metadata?.next_cursor || undefined;
      page++;
    } while (rc);

    m.__replies = kids;
    replyCount += kids.length;

    /* Slack's own count, disagreed with. Worth saying out loud: it is the
       only signal that the walk came up short. */
    if (m.reply_count && kids.length < m.reply_count) {
      console.log(`  ⚠ thread ${m.ts}: Slack says ${m.reply_count} replies, fetched ${kids.length}`);
    }
  }
  if (replyCount) console.log(`  ${replyCount} thread repl${replyCount === 1 ? 'y' : 'ies'}`);

  /* files */
  let fileCount = 0;
  let skippedBytes = 0;
  const oversize = [];
  const external = [];
  const everything = messages.flatMap((m) => [m, ...(m.__replies ?? [])]);
  for (const m of everything) {
    for (const f of m.files ?? []) {
      const url = f.url_private_download ?? f.url_private;
      if (!url) continue;

      /* A Google Doc linked into Slack is a file OBJECT here, but the bytes
         live at docs.google.com. The Slack token means nothing to Google,
         which answers with its own login page at 200 — indistinguishable
         from the auth trap below unless it is caught first. Reporting these
         as failed downloads is worse than useless: it implies something
         broke, when the truth is that they need the Drive OAuth app and
         nothing about Slack will ever reach them. */
      if (f.is_external || f.mode === 'external') {
        const host = (() => {
          try { return new URL(url).host; } catch { return 'external'; }
        })();
        f.__external = { host, url, type: f.external_type ?? f.filetype ?? 'link' };
        external.push({ name: f.name, host, url, type: f.__external.type, id: f.id });
        continue;
      }

      /* Checked against the size Slack already reported, so an oversize
         file costs no transfer at all rather than being aborted mid-stream. */
      if ((f.size ?? 0) > MAX_FILE_BYTES) {
        f.__skipped = { reason: 'over cap', mb: +(f.size / 1024 / 1024).toFixed(1), url };
        oversize.push({ name: f.name, mb: f.__skipped.mb, url, ts: m.ts });
        skippedBytes += f.size;
        continue;
      }

      const res = await fetch(url, { headers: { Authorization: `Bearer ${TOKEN}` } });
      const type = res.headers.get('content-type') ?? '';
      /* The login-page trap: 200 + text/html means the auth did not take. */
      if (!res.ok || /text\/html/i.test(type)) {
        console.log(`  ✗ ${f.name} — got ${res.status} ${type.split(';')[0]}, not the file`);
        f.__skipped = { reason: `HTTP ${res.status} ${type.split(';')[0]}`, url };
        continue;
      }
      const buf = Buffer.from(await res.arrayBuffer());
      const safe = (f.name ?? 'file').replace(/[^\w.-]+/g, '_');
      await writeFile(join(OUT, 'files', `${f.id}-${safe}`), buf);
      f.__local = `files/${f.id}-${safe}`;
      fileCount++;
    }
  }
  if (fileCount) console.log(`  ${fileCount} file(s) downloaded`);
  if (oversize.length) {
    console.log(`  ${oversize.length} file(s) over ${MAX_FILE_MB} MB left in place (${(skippedBytes / 1024 / 1024).toFixed(0)} MB), URLs recorded`);
  }
  if (external.length) {
    const distinct = new Set(external.map((e) => e.id)).size;
    console.log(`  ${distinct} externally-hosted doc(s) — need Drive access, not Slack`);
  }

  /* ── render ────────────────────────────────────────────────────── */

  messages.sort((a, b) => Number(a.ts) - Number(b.ts));

  /* The date range the channel actually covers, read off the sorted ends.
     This is what says whether the 90-day retention cliff has already bitten:
     a channel opened in 2024 whose earliest message is three months old has
     lost history, and the count alone would not show it. */
  const day = (m) => (m ? new Date(Number(m.ts) * 1000).toISOString().slice(0, 10) : null);
  const first = day(messages[0]);
  const last = day(messages.at(-1));

  /* Slack stores mentions as <@U0123>. Left raw they are unreadable, and an
     LLM asked to find who said what cannot resolve them either. */
  const resolveMentions = async (text) => {
    const ids = [...new Set([...text.matchAll(/<@([A-Z0-9]+)>/g)].map((m) => m[1]))];
    let out = text;
    for (const id of ids) out = out.replaceAll(`<@${id}>`, `@${await userName(id)}`);
    return out;
  };

  const render = async (m, depth = 0) => {
    const who = await authorOf(m);
    const when = new Date(Number(m.ts) * 1000).toISOString().slice(0, 16).replace('T', ' ');
    const pad = depth ? '> ' : '';
    const lines = [`${pad}**${who}** · ${when} · [link](${permalink(hit.id, m.ts)})`];
    if (m.text) {
      const text = await resolveMentions(m.text);
      lines.push(text.split('\n').map((l) => pad + l).join('\n'));
    }
    for (const f of m.files ?? []) {
      const where = f.__local
        ? `saved as \`${f.__local}\``
        : f.__external
          ? `**hosted on ${f.__external.host}** — not in Slack, [open](${f.__external.url})`
          : f.__skipped
            ? `**not downloaded** — ${f.__skipped.reason}${f.__skipped.mb ? ` (${f.__skipped.mb} MB)` : ''}, [fetch it](${f.__skipped.url})`
            : 'not downloaded';
      lines.push(`${pad}📎 ${f.name} (${f.filetype}, ${where})`);
    }
    for (const kid of m.__replies ?? []) lines.push(await render(kid, depth + 1));
    return lines.join('\n');
  };

  const body = [];
  for (const m of messages) body.push(await render(m));

  const md = `# #${hit.name}

${hit.is_private ? 'Private channel' : 'Public channel'} · \`${hit.id}\`
Pulled ${new Date().toISOString().slice(0, 10)} by \`corpus/fetch-slack.mjs\`.

${messages.length} parent messages · ${replyCount} thread replies · ${fileCount} files downloaded${oversize.length ? ` · ${oversize.length} left in place` : ''}.
${first && last ? `Covers ${first} → ${last}.` : ''}

Thread replies are indented with \`>\`. Every message links back to Slack, so a
candidate drawn from here carries its source the way a transcript quote carries
a timecode.
${
  oversize.length
    ? `
## Not downloaded — over the ${MAX_FILE_MB} MB cap

These stayed in Slack. The link needs the bot token in an \`Authorization\`
header; a plain browser fetch returns a login page with a 200.

| File | Size | Link |
|---|---|---|
${oversize.map((f) => `| ${f.name} | ${f.mb} MB | [download](${f.url}) |`).join('\n')}
`
    : ''
}${
  external.length
    ? `
## Linked, not attached — needs Drive access

Shared into the channel as links, so the bytes never touched Slack and no
Slack scope reaches them. These want the Google Drive OAuth app. Named here
because copy like this is Atelier source material, and a link that is only
mentioned in passing in a thread is a link nobody finds again.

| Document | Host | Type | Link |
|---|---|---|---|
${[...new Map(external.map((e) => [e.id, e])).values()]
  .map((e) => `| ${e.name} | ${e.host} | ${e.type} | [open](${e.url}) |`)
  .join('\n')}
`
    : ''
}
---

${body.join('\n\n')}
`;

  await writeFile(join(OUT, `${hit.name}.md`), md, 'utf8');
  await writeFile(join(OUT, 'raw', `${hit.name}.json`), JSON.stringify(messages, null, 2), 'utf8');

  summary.push({
    name: hit.name,
    id: hit.id,
    private: hit.is_private,
    messages: messages.length,
    replies: replyCount,
    files: fileCount,
    oversize: oversize.length,
    oversizeMb: +(skippedBytes / 1024 / 1024).toFixed(0),
    external: new Set(external.map((e) => e.id)).size,
    externalDocs: [...new Map(external.map((e) => [e.id, e])).values()],
    first,
    last,
  });
  console.log(`  → ${OUT}/${hit.name}.md\n`);
}

/* ── index ───────────────────────────────────────────────────────── */

/* Built from every raw/*.json on disk, NOT from this run's summary.

   Re-running one channel to fix one thing must not silently delete five
   channels from the index — which is exactly what happened the first time,
   and it looked like a successful run. The raw payloads persist each
   channel's stats (files carry __local / __skipped / __external by the time
   they are written), so the index can be rebuilt in full from whatever is
   on disk regardless of what this invocation touched. */
const onDisk = [];
for (const f of readdirSync(join(OUT, 'raw')).filter((n) => n.endsWith('.json'))) {
  const name = f.replace(/\.json$/, '');

  /* The sandbox is excluded from the INDEX as well as from fetching. Its
     messages are ones we wrote to prove the pipeline worked, and at least
     one is an invented client success story — plausible, well-formed, and
     indistinguishable from signal to anything reading for testimonials.
     Listing it as corpus is how a fabricated quote ends up in a client
     deliverable with a permalink that appears to back it up. */
  if (EXCLUDE.test(name)) continue;
  const msgs = JSON.parse(readFileSync(join(OUT, 'raw', f), 'utf8'));
  const all = msgs.flatMap((m) => [m, ...(m.__replies ?? [])]);
  const files = all.flatMap((m) => m.files ?? []);
  const day = (m) => (m ? new Date(Number(m.ts) * 1000).toISOString().slice(0, 10) : null);
  const ext = [...new Map(files.filter((x) => x.__external).map((x) => [x.id, x])).values()];

  onDisk.push({
    name,
    fresh: summary.some((s) => s.name === name),
    messages: msgs.length,
    replies: all.length - msgs.length,
    files: files.filter((x) => x.__local).length,
    oversize: files.filter((x) => x.__skipped?.reason === 'over cap').length,
    oversizeMb: +(
      files.filter((x) => x.__skipped?.reason === 'over cap').reduce((n, x) => n + (x.size ?? 0), 0) /
      1024 /
      1024
    ).toFixed(0),
    external: ext.length,
    externalDocs: ext.map((x) => ({ name: x.name, host: x.__external.host, url: x.__external.url })),
    first: day(msgs[0]),
    last: day(msgs.at(-1)),
  });
}
onDisk.sort((a, b) => b.messages - a.messages);

const total = (k) => onDisk.reduce((n, s) => n + s[k], 0);

const index = `# Slack corpus — index

${onDisk.length} channel${onDisk.length === 1 ? '' : 's'} in \`corpus/slack/\`, written by \`corpus/fetch-slack.mjs\`.
Last run touched ${summary.length}: ${summary.map((s) => '#' + s.name).join(', ')} (${new Date().toISOString().slice(0, 10)}).

**${total('messages').toLocaleString()} parent messages · ${total('replies').toLocaleString()} thread replies · ${total('files')} files downloaded.**

| Channel | Messages | Replies | Files | Covers |
|---|---|---|---|---|
${onDisk
  .map(
    (s) =>
      `| [#${s.name}](./${s.name}.md) | ${s.messages} | ${s.replies} | ${s.files}${s.oversize ? ` (+${s.oversize} skipped)` : ''} | ${s.first ?? '—'} → ${s.last ?? '—'} |`,
  )
  .join('\n')}

## What is not here

**Over the size cap.** ${total('oversize')} files, ${(total('oversizeMb') / 1024).toFixed(1)} GB, almost all office-hours
recordings. Each is listed with its download URL in its own channel file. The
Atelier reads transcripts, not video, and 150 of those already came from Zoom.

**Hosted elsewhere.** ${total('external')} document${total('external') === 1 ? '' : 's'} linked into a channel rather than uploaded, so no
Slack scope reaches ${total('external') === 1 ? 'it' : 'them'}:

${
  onDisk
    .filter((s) => s.external)
    .flatMap((s) => s.externalDocs.map((e) => `- **${e.name}** — ${e.host}, in [#${s.name}](./${s.name}.md)`))
    .join('\n') || '- none'
}

These need the Google Drive OAuth app. They are worth naming individually
because copy of this kind is exactly what the Atelier is for.

Retention is the real deadline. On the free plan Slack truncates history to
90 days, so what is in these files is the record — re-running this later
returns less, not more.

## Attribution

Slack resolves every author to a real user id, so unlike the Zoom VTTs these
quotes carry \`attribution: "resolved"\` — the name is Slack's, not an inference
from who else was in the room. Permalinks make each one checkable.
`;

await writeFile(join(OUT, '_INDEX.md'), index, 'utf8');

console.log('─'.repeat(52));
for (const s of summary) {
  console.log(`  #${s.name}: ${s.messages} messages, ${s.replies} replies, ${s.files} files${s.oversize ? `, ${s.oversize} skipped` : ''}`);
}
console.log(`\n  ${total('messages')} messages · ${total('replies')} replies · ${total('files')} files`);
console.log(`\nWritten to ${OUT}/  ·  index at ${OUT}/_INDEX.md`);
