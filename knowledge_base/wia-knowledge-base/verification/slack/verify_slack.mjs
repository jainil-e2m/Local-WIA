/** Bounded read-only Slack feasibility probe. Never posts or changes membership.
 * Run from any directory: node knowledge_base/wia-knowledge-base/verification/slack/verify_slack.mjs
 * Uses SLACK_BOT_TOKEN from the process or frontend/.env[.local], without logging it.
 * Only the six previously collected channels are read; all others are metadata only.
 * Does not overwrite historical payloads or persist new message bodies.
 */
import { readFile, writeFile } from 'node:fs/promises';
import { parseEnv } from 'node:util';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const out = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(out, '../../../..');
let token = process.env.SLACK_BOT_TOKEN;
let credentialSource = token ? 'process environment' : null;
for (const name of ['frontend/.env', 'frontend/.env.local']) {
  if (token) break;
  try {
    token = parseEnv(await readFile(path.join(root, name), 'utf8')).SLACK_BOT_TOKEN;
    if (token) credentialSource = `${name}:SLACK_BOT_TOKEN`;
  } catch { /* Missing file is reported through credential_present below. */ }
}
const known = ['c_dogwoodreserve', 'c_funktasticproductions_djhybrid',
  'cfpfu_luxurytravelboutique', 'googlesearchaccelerator',
  'metaadsaccelerator', 'social-proof-and-results'];
const report = { review_date: '2026-10-19', started_at_utc: new Date().toISOString(),
  mode: 'bounded_read_only_live_probe', credential_present: Boolean(token), credential_source: credentialSource,
  token_kind: token?.startsWith('xoxb-') ? 'bot' : token ? 'other' : null,
  history_limit: 15, full_history_backfill: false, channels: [], calls: [] };
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
let requestNumber = 0;
async function call(method, params = {}) {
  if (requestNumber++) await delay(1250);
  const query = new URLSearchParams(params);
  try {
    const response = await fetch(`https://slack.com/api/${method}?${query}`, {
      headers: { Authorization: `Bearer ${token}` }, signal: AbortSignal.timeout(18000),
    });
    const record = { method, http_status: response.status };
    const scopes = response.headers.get('x-oauth-scopes');
    if (scopes) report.granted_scopes = scopes.split(',').map(x => x.trim());
    if (response.status === 429) {
      record.error = 'ratelimited'; record.retry_after = response.headers.get('retry-after');
      report.calls.push(record);
      // No retry storm; leave this step explicitly unverified.
      return { ok: false, error: 'ratelimited', retry_after: record.retry_after };
    }
    const result = await response.json();
    record.ok = Boolean(result.ok); if (!result.ok) record.error = result.error;
    if (result.needed) record.needed = result.needed;
    report.calls.push(record);
    return result;
  } catch (error) {
    const record = { method, ok: false, error: 'network_or_response_error',
      error_type: error.name, cause_code: error.cause?.code ?? null };
    report.calls.push(record); return { ok: false, error: record.error };
  }
}
const stamp = ts => new Date(Number(ts) * 1000).toISOString();
async function main() {
  if (!token) { report.result = 'credential_missing'; return; }
  const auth = await call('auth.test');
  report.authentication = { ok: Boolean(auth.ok), error: auth.error ?? null,
    workspace_id: auth.team_id ?? null, workspace: auth.team ?? null };
  if (!auth.ok) { report.result = 'authentication_or_network_failed'; return; }
  const channels = [];
  let cursor;
  for (let page = 0; page < 10; page++) {
    const result = await call('users.conversations', { types: 'public_channel,private_channel',
      exclude_archived: 'false', limit: 200, ...(cursor ? { cursor } : {}) });
    if (!result.ok) { report.membership_error = result.error; break; }
    channels.push(...(result.channels ?? []));
    cursor = result.response_metadata?.next_cursor || null;
    if (!cursor) break;
  }
  report.membership_inventory_complete = !cursor && !report.membership_error;
  report.membership = channels.map(c => ({ id: c.id, name: c.name, private: c.is_private,
    archived: c.is_archived, in_prior_corpus: known.includes(c.name) }));
  let userChecked = false;
  let fileChecked = false;
  for (const name of known) {
    const channel = channels.find(c => c.name === name);
    const row = { name, reachable_in_membership: Boolean(channel) };
    report.channels.push(row);
    if (!channel) continue;
    row.id = channel.id; row.private = channel.is_private;
    const hist = await call('conversations.history', { channel: channel.id, limit: 15 });
    row.history_ok = Boolean(hist.ok);
    if (!hist.ok) { row.history_error = hist.error; continue; }
    const messages = hist.messages ?? [];
    row.sample_messages = messages.length;
    row.more_history_available = Boolean(hist.has_more || hist.response_metadata?.next_cursor);
    row.sample_first_utc = messages.length ? stamp(messages.at(-1).ts) : null;
    row.sample_last_utc = messages.length ? stamp(messages[0].ts) : null;
    row.sample_with_text = messages.filter(m => m.text).length;
    row.sample_with_files = messages.filter(m => m.files?.length).length;
    row.sample_with_reactions = messages.filter(m => m.reactions?.length).length;
    row.sample_with_threads = messages.filter(m => m.reply_count > 0).length;
    row.sample_bot_posts = messages.filter(m => m.bot_id || m.subtype === 'bot_message').length;
    const parent = messages.find(m => m.reply_count > 0 && (!m.thread_ts || m.thread_ts === m.ts));
    if (parent) {
      const replies = await call('conversations.replies', { channel: channel.id, ts: parent.ts, limit: 15 });
      row.thread_probe = { ok: Boolean(replies.ok), error: replies.error ?? null,
        parent_ts: parent.ts, declared_replies: parent.reply_count,
        returned_replies: (replies.messages ?? []).filter(m => m.ts !== parent.ts).length,
        has_more: Boolean(replies.has_more || replies.response_metadata?.next_cursor) };
    } else row.thread_probe = { status: 'no_thread_in_bounded_sample' };
    const message = messages.find(m => m.text && m.user && !m.bot_id) ?? messages[0];
    if (message) {
      const link = await call('chat.getPermalink', { channel: channel.id, message_ts: message.ts });
      row.permalink_probe = { ok: Boolean(link.ok), error: link.error ?? null,
        message_ts: message.ts, permalink: link.permalink ?? null };
      if (!userChecked && message.user) {
        const user = await call('users.info', { user: message.user });
        report.user_lookup = { ok: Boolean(user.ok), error: user.error ?? null,
          id: message.user, has_display_name: Boolean(user.user?.profile?.display_name || user.user?.real_name),
          is_bot: user.user?.is_bot ?? null };
        userChecked = true;
      }
    }
    const file = messages.flatMap(m => m.files ?? []).find(f => f.id && !f.is_external);
    if (!fileChecked && file) {
      const info = await call('files.info', { file: file.id });
      report.file_lookup = { ok: Boolean(info.ok), error: info.error ?? null, id: file.id,
        has_download_url: Boolean(info.file?.url_private_download || info.file?.url_private),
        mimetype: info.file?.mimetype ?? null, size: info.file?.size ?? null };
      // Verify a small native attachment without persisting its bytes.
      const url = info.file?.url_private_download || info.file?.url_private;
      if (info.ok && url && info.file.size > 0 && info.file.size <= 1024 * 1024 && new URL(url).hostname === 'files.slack.com') {
        try {
          const response = await fetch(url, { headers: { Authorization: `Bearer ${token}` },
            redirect: 'manual', signal: AbortSignal.timeout(18000) });
          const contentType = response.headers.get('content-type') ?? '';
          const bytes = await response.arrayBuffer();
          report.file_download = { http_status: response.status, content_type: contentType,
            bytes: bytes.byteLength, expected_bytes: info.file.size,
            ok: response.ok && !contentType.includes('text/html') && bytes.byteLength === info.file.size };
        } catch (error) { report.file_download = { ok: false, error_type: error.name }; }
      } else report.file_download = { status: 'not_tested_size_or_host_or_lookup_constraint' };
      fileChecked = true;
    }
  }
  report.result = 'bounded_probe_completed';
}
await main();
report.finished_at_utc = new Date().toISOString();
await writeFile(path.join(out, 'live_probe.json'), JSON.stringify(report, null, 2) + '\n');
console.log(JSON.stringify(report, null, 2));
