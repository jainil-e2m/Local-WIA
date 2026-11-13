/** GET-only Fathom feasibility probe. No webhook registration/callbacks or remote writes.
 * Reads frontend/.env only; retains bounded metadata and short content excerpts.
 * Run from workspace root: node knowledge_base/wia-knowledge-base/verification/fathom/verify_fathom.mjs
 */
import { readFile, writeFile } from 'node:fs/promises';
import { parseEnv } from 'node:util';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const out = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(out, '../../../..');
const env = parseEnv(await readFile(path.join(root, 'frontend/.env'), 'utf8'));
const key = env.FATHOM_API_KEY?.trim();
const report = { review_date: '2026-10-19', started_at_utc: new Date().toISOString(),
  credential_present: Boolean(key), credential_source: 'frontend/.env:FATHOM_API_KEY',
  mode: 'GET_only_no_callbacks_no_webhooks', limits: { meeting_pages: 20, content_samples: 3,
    sample_excerpt_characters: 420, summary_excerpt_characters: 1600 },
  calls: [], meetings: [], samples: [], observations: {}, full_content_backfill: false };
const shape = x => x && typeof x === 'object' ? Object.keys(x).sort() : [];
const clean = x => typeof x === 'string' && key ? x.replaceAll(key, '[REDACTED]') : x;
let requests = 0;
async function get(label, endpoint, params = {}) {
  if (requests++) await new Promise(r => setTimeout(r, 1150));
  const url = new URL(`https://api.fathom.ai/external/v1${endpoint}`);
  for (const [k,v] of Object.entries(params)) url.searchParams.set(k, String(v));
  const call = { label, method: 'GET', path: endpoint, query: params };
  report.calls.push(call);
  try {
    const res = await fetch(url, { headers: { 'X-Api-Key': key, Accept: 'application/json' },
      redirect: 'error', signal: AbortSignal.timeout(22000) });
    call.http_status = res.status; call.ok = res.ok;
    const text = await res.text();
    let data; try { data = JSON.parse(text); } catch { data = null; }
    call.top_level_keys = shape(data);
    if (!res.ok) { call.error = clean(JSON.stringify(data?.message ?? data?.error ?? text.slice(0, 200))); return null; }
    return data;
  } catch (e) { call.ok = false; call.error = e.name; call.cause_code = e.cause?.code ?? null; return null; }
}
function metadata(m) {
  return Object.fromEntries(['recording_id','title','meeting_title','created_at','scheduled_start_time',
    'scheduled_end_time','recording_start_time','recording_end_time','meeting_type','shared_with',
    'transcript_language','calendar_invitees_domains_type','url','share_url','recorded_by',
    'calendar_invitees'].map(k => [k, m[k] ?? null]));
}
function content(m) {
  const t = Array.isArray(m.transcript) ? m.transcript : [];
  const a = Array.isArray(m.action_items) ? m.action_items : [];
  const summary = m.default_summary ?? m.summary;
  return { recording_id: m.recording_id, transcript_present: t.length > 0,
    transcript_segments: t.length, text_characters: t.reduce((n,s) => n + (s.text?.length ?? 0), 0),
    segments_with_speaker: t.filter(s => s.speaker?.display_name).length,
    segments_with_matched_email: t.filter(s => s.speaker?.matched_calendar_invitee_email).length,
    segments_with_timestamp: t.filter(s => s.timestamp).length,
    speaker_names: [...new Set(t.map(s => s.speaker?.display_name).filter(Boolean))],
    transcript_segment_keys: shape(t[0]), speaker_keys: shape(t[0]?.speaker),
    opening_excerpt: t.slice(0, 3).map(s => ({ speaker: s.speaker?.display_name ?? null,
      timestamp: s.timestamp ?? null, text: clean(s.text?.slice(0, 140) ?? '') })),
    summary_present: Boolean(summary?.markdown_formatted), summary_keys: shape(summary),
    summary_characters: summary?.markdown_formatted?.length ?? 0,
    summary_excerpt: clean(summary?.markdown_formatted?.slice(0, 1600) ?? ''),
    action_items_count: a.length, action_item_keys: [...new Set(a.flatMap(shape))].sort(),
    actions_with_assignee: a.filter(x => x.assignee?.email || x.assignee?.name).length,
    actions_with_due_field: a.filter(x => Object.keys(x).some(k => /due|deadline/i.test(k))).length,
    actions_with_completion_flag: a.filter(x => typeof x.completed === 'boolean').length,
    action_items_sample: a.slice(0, 6),
    highlights_count: Array.isArray(m.highlights) ? m.highlights.length : null,
    crm_keys: shape(m.crm_matches), crm_error: m.crm_matches?.error ?? null,
    crm_match_counts: Object.fromEntries(['contacts','companies','deals'].map(k => [k,
      Array.isArray(m.crm_matches?.[k]) ? m.crm_matches[k].length : null])) };
}
async function main() {
  if (!key) { report.result = 'credential_missing'; return; }
  let cursor; const seen = new Set(); let completed = false;
  for (let page = 0; page < report.limits.meeting_pages; page++) {
    const data = await get(`meeting_page_${page + 1}`, '/meetings', cursor ? {cursor} : {});
    if (!data) break;
    const items = Array.isArray(data.items) ? data.items : [];
    report.calls.at(-1).item_count = items.length;
    for (const m of items) {
      if (!seen.has(m.recording_id)) { seen.add(m.recording_id); report.meetings.push(metadata(m)); }
    }
    const next = data.next_cursor;
    if (!next) { completed = true; break; }
    if (next === cursor) { report.pagination_warning = 'repeated_cursor'; break; }
    cursor = next;
  }
  report.inventory_exhausted_cursor = completed;
  if (!report.calls[0]?.ok) { report.result = 'initial_meeting_list_failed'; return; }
  const teams = await get('teams', '/teams');
  report.observations.teams = { response_keys: shape(teams),
    items: teams?.items ?? null, next_page_present: Boolean(teams?.next_cursor) };
  const members = await get('team_members', '/team_members');
  report.observations.team_members = { response_keys: shape(members),
    returned_count: members?.items?.length ?? null, member_keys: shape(members?.items?.[0]),
    next_page_present: Boolean(members?.next_cursor) };
  const enriched = await get('inline_content_page', '/meetings', { include_transcript: true,
    include_summary: true, include_action_items: true, include_highlights: true, include_crm_matches: true });
  const enrichedItems = enriched?.items ?? [];
  report.observations.inline_content = enrichedItems.map(content);
  // Prefer two distinct externally invited meetings, then one other recorder/internal example.
  const external = report.meetings.filter(m => m.calendar_invitees_domains_type === 'one_or_more_external'
    || m.calendar_invitees?.some(i => i.is_external));
  const candidates = [...external.slice(0, 2)];
  const other = report.meetings.find(m => !candidates.some(c => c.recording_id === m.recording_id)
    && (m.recorded_by?.email !== candidates[0]?.recorded_by?.email
      || m.calendar_invitees_domains_type === 'only_internal'));
  if (other) candidates.push(other);
  for (const m of [...report.meetings]) {
    if (candidates.length >= 3) break;
    if (!candidates.some(c => c.recording_id === m.recording_id)) candidates.push(m);
  }
  for (const m of candidates) {
    const transcript = await get(`transcript_${m.recording_id}`, `/recordings/${m.recording_id}/transcript`);
    const summary = await get(`summary_${m.recording_id}`, `/recordings/${m.recording_id}/summary`);
    report.samples.push({ metadata: m, content: content({ ...m, transcript: transcript?.transcript,
      summary: summary?.summary }), inline_available: enrichedItems.some(e => e.recording_id === m.recording_id) });
  }
  const tally = (keyFn) => Object.fromEntries([...Map.groupBy(report.meetings, keyFn)].map(([k,v]) => [k,v.length]));
  report.observations.meeting_count = report.meetings.length;
  report.observations.by_recorder = tally(m => m.recorded_by?.email ?? 'unknown');
  report.observations.by_sharing = tally(m => m.shared_with ?? 'unknown');
  report.observations.by_meeting_type = tally(m => m.meeting_type ?? 'unknown');
  report.observations.by_invitee_domain_type = tally(m => m.calendar_invitees_domains_type ?? 'unknown');
  const dates = report.meetings.map(m => m.recording_start_time).filter(Boolean).sort();
  report.observations.recording_date_range = { oldest: dates[0] ?? null, newest: dates.at(-1) ?? null };
  report.result = 'probe_completed';
}
const filteredFollowup = process.argv.includes('--wia-recorders');
try {
  if (filteredFollowup) {
    if (!key) report.result = 'credential_missing';
    else {
      report.filter_checks = [];
      for (const email of ['hello@weddingindustryads.com', 'gisselle@dotandcompany.co']) {
        const data = await get(`recorder_filter_${email}`, '/meetings', { 'recorded_by[]': email });
        report.filter_checks.push({ recorded_by: email, returned_count: data?.items?.length ?? null,
          next_cursor_present: Boolean(data?.next_cursor), meetings: (data?.items ?? []).map(metadata) });
      }
      report.result = 'wia_recorder_filters_completed';
    }
  } else await main();
} catch(e) { report.result = 'probe_error'; report.error_type = e.name; }
report.finished_at_utc = new Date().toISOString();
const filename = filteredFollowup ? 'wia_recorder_probe.json' : 'live_probe.json';
await writeFile(path.join(out, filename), JSON.stringify(report, null, 2) + '\n');
console.log(JSON.stringify({ result: report.result, calls: report.calls.length,
  statuses: report.calls.reduce((x,c) => { const k = c.http_status ?? 'network_error'; x[k] = (x[k] ?? 0) + 1; return x; }, {}),
  meeting_count: report.meetings.length, inventory_exhausted_cursor: report.inventory_exhausted_cursor,
  recorders: report.observations.by_recorder,
  sample_transcripts: report.samples.map(s => ({ recording_id: s.metadata.recording_id,
    segments: s.content.transcript_segments, summary: s.content.summary_present })),
  filter_checks: report.filter_checks?.map(c => ({ recorded_by: c.recorded_by,
    returned_count: c.returned_count, next_cursor_present: c.next_cursor_present,
    matching_recorder_count: c.meetings.filter(m => m.recorded_by?.email === c.recorded_by).length })),
  report: `knowledge_base/wia-knowledge-base/verification/fathom/${filename}` }, null, 2));
