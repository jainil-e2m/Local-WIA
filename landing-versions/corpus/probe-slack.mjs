/* ─────────────────────────────────────────────────────────────────
   Probe the Slack app's actual reach.

   RUN:  node --env-file=.env corpus/probe-slack.mjs

   .env needs:
     SLACK_BOT_TOKEN=xoxb-...

   READ-ONLY. Every call is a read method.

   WHAT IT ANSWERS. A bot token sees nothing in a channel the bot has not
   been invited to, and the API reports that as an empty history rather
   than an error — so "it returned no messages" is ambiguous between "the
   channel is quiet" and "we were never added". This distinguishes them,
   and checks that files and reactions actually come through, since those
   are the two things the Atelier specifically needs from Slack.
   ───────────────────────────────────────────────────────────────── */

const TOKEN = process.env.SLACK_BOT_TOKEN;
if (!TOKEN) {
  console.error('Set SLACK_BOT_TOKEN in .env, then run with --env-file=.env');
  process.exit(1);
}

/* The three named on the 16 September call. Matched loosely, because Slack
   lowercases and hyphenates and nobody wrote down the exact handles.

   Override to probe a test channel before going near the real ones:
     SLACK_CHANNELS=wia-ai-team-testing node --env-file=.env corpus/probe-slack.mjs
   or pass them as arguments:
     node --env-file=.env corpus/probe-slack.mjs wia-ai-team-testing */
const args = process.argv.slice(2);
const WANTED = (args.length ? args : (process.env.SLACK_CHANNELS ??
      'googlesearchaccelerator,metaadsaccelerator,social-proof-and-results').split(','))
  /* Hyphens flattened to spaces on BOTH sides of the comparison — the
     matcher normalises the channel name the same way, so a target of
     "wia-ai-team-testing" has to be normalised too or it never matches. */
  .map((s) => s.trim().replace(/-/g, ' ').toLowerCase())
  .filter(Boolean);

const call = async (method, params = {}) => {
  const qs = new URLSearchParams(params).toString();
  const res = await fetch(`https://slack.com/api/${method}${qs ? '?' + qs : ''}`, {
    headers: { Authorization: `Bearer ${TOKEN}` },
  });
  return res.json();
};

/* ── 1 · does the token work, and what is it ─────────────────────── */

const me = await call('auth.test');
if (!me.ok) {
  console.error(`auth.test failed: ${me.error}`);
  if (me.error === 'invalid_auth') console.error('The token is wrong or the app was uninstalled.');
  process.exit(1);
}
console.log(`✓ ${me.team}  ·  bot ${me.user} (${me.user_id})\n`);

/* ── 2 · which channels the bot is actually IN ───────────────────── */

const mine = await call('users.conversations', {
  types: 'public_channel,private_channel',
  limit: '200',
  exclude_archived: 'true',
});

if (!mine.ok) {
  console.error(`users.conversations failed: ${mine.error}`);
  if (mine.error === 'missing_scope') console.error(`  needs: ${mine.needed}`);
  process.exit(1);
}

const channels = mine.channels ?? [];
console.log(`The bot is a member of ${channels.length} channel(s):`);
for (const c of channels) {
  console.log(`  ${c.is_private ? '🔒' : '# '} ${c.name}  (${c.id})`);
}
console.log();

/* ── 3 · are the three we care about among them ──────────────────── */

const matched = WANTED.map((want) => {
  const hit = channels.find((c) => c.name.replace(/-/g, " ").toLowerCase().includes(want));
  return { want, hit };
});

console.log('Target channels:');
for (const { want, hit } of matched) {
  console.log(
    hit
      ? `  ✓ "${want}" → #${hit.name}${hit.is_private ? '  (private — needs groups:* scopes)' : ''}`
      : `  ✗ "${want}" → not found. Either the bot was never invited, or the name differs.`,
  );
}
console.log();

/* ── 4 · can we actually read messages, files and reactions ──────── */

for (const { hit } of matched.filter((m) => m.hit)) {
  const hist = await call('conversations.history', { channel: hit.id, limit: '25' });

  if (!hist.ok) {
    console.log(`#${hit.name}: history failed — ${hist.error}`);
    if (hist.error === 'missing_scope') console.log(`  needs: ${hist.needed}`);
    if (hist.error === 'not_in_channel') console.log('  the bot is not in this channel — /invite it');
    console.log();
    continue;
  }

  const msgs = hist.messages ?? [];
  const withFiles = msgs.filter((m) => m.files?.length);
  const withReactions = msgs.filter((m) => m.reactions?.length);

  console.log(`#${hit.name}  —  ${msgs.length} recent message(s)`);
  console.log(`  with files:     ${withFiles.length}${withFiles.length ? '  ✓ files:read is working' : ''}`);
  console.log(`  with reactions: ${withReactions.length}${withReactions.length ? '  ✓ reactions:read is working' : ''}`);

  const sample = msgs.find((m) => m.text && m.text.length > 40) ?? msgs[0];
  if (sample) {
    const when = new Date(Number(sample.ts) * 1000).toISOString().slice(0, 16).replace('T', ' ');
    console.log(`  latest substantive: ${when}  ${(sample.text ?? '').slice(0, 90).replace(/\s+/g, ' ')}…`);
  }

  if (withFiles.length) {
    const f = withFiles[0].files[0];
    console.log(`  sample file: ${f.name} (${f.filetype}, ${f.size} bytes)`);
    console.log('    download needs the bot token in an Authorization header —');
    console.log(`    ${f.url_private_download?.slice(0, 80)}…`);
  }
  if (withReactions.length) {
    const names = [...new Set(withReactions.flatMap((m) => m.reactions.map((r) => r.name)))];
    console.log(`  emoji in use: ${names.slice(0, 12).join(', ')}`);
    console.log('    one of these could be the content-worthy flag — open question #1');
  }

  /* THREAD REPLIES ARE NOT IN THIS PAYLOAD. conversations.history returns
     parent messages only. A relayed client quote buried in a thread is
     invisible to a naive reader, which is a silent data loss rather than an
     error — so count them and fetch one to prove the second call works. */
  const threaded = msgs.filter((m) => (m.reply_count ?? 0) > 0);
  if (threaded.length) {
    const hidden = threaded.reduce((n, m) => n + m.reply_count, 0);
    console.log(`  ⚠ ${threaded.length} thread(s) holding ${hidden} repl${hidden === 1 ? 'y' : 'ies'} NOT in this payload`);
    const rep = await call('conversations.replies', {
      channel: hit.id,
      ts: threaded[0].thread_ts ?? threaded[0].ts,
      limit: '5',
    });
    if (rep.ok) {
      const kids = (rep.messages ?? []).slice(1);
      console.log(`    conversations.replies works — fetched ${kids.length}`);
      if (kids[0]) console.log(`    e.g. "${(kids[0].text ?? '').slice(0, 70).replace(/\s+/g, ' ')}…"`);
      console.log('    the ingest must walk threads, not just history');
    } else {
      console.log(`    conversations.replies failed — ${rep.error}`);
    }
  } else {
    console.log('  no threaded messages in this sample — test one deliberately');
  }
  console.log();
}

console.log('─'.repeat(58));
console.log(`Channels reachable: ${matched.filter((m) => m.hit).length} of ${WANTED.length}`);
