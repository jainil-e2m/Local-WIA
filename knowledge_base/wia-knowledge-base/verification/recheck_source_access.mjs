/** Bounded GET-only access checks. No callbacks, permission changes, or remote writes.
 * Test each distinct configured Fathom key instead of silently accepting duplicate precedence.
 * Preserve historical reports; save metadata/counts only, never keys or transcript bodies.
 * Run with --fathom or --leadlock from the workspace root.
 */
import { readFile, writeFile } from 'node:fs/promises';
import { parseEnv } from 'node:util';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const out = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(out, '../../..');
const raw = await readFile(path.join(root, 'frontend/.env'), 'utf8');
const env = parseEnv(raw);
const mode = process.argv.includes('--fathom') ? 'fathom' : process.argv.includes('--leadlock') ? 'leadlock' : null;
if (!mode) throw new Error('Specify --fathom or --leadlock.');
const date = '2026-10-20';
const secrets = Object.entries(env).filter(([k]) => /PIT|TOKEN|SECRET|API_KEY/i.test(k)).map(([,v]) => v).filter(Boolean);
const keyEntries = [];
raw.split(/\r?\n/).forEach((line, i) => {
  if (!/^\s*(?:export\s+)?FATHOM_API_KEY\s*=/.test(line)) return;
  const value = parseEnv(line).FATHOM_API_KEY?.trim();
  if (!value) return;
  secrets.push(value);
  const same = keyEntries.find(x => x.value === value);
  if (same) same.lines.push(i+1);
  else keyEntries.push({ value, lines: [i+1] });
});
const report = { review_date: date, started_at_utc: new Date().toISOString(),
  mode: 'GET_only_metadata_and_content_counts_no_callbacks_no_webhooks',
  credential_source: 'frontend/.env', remote_writes: 0, calls: [] };
const shape = v => v && typeof v === 'object' ? Object.keys(v).sort() : [];
const redact = value => {
  let text = String(value ?? '');
  for (const secret of secrets) text = text.replaceAll(secret, '[REDACTED]');
  return text.slice(0, 300);
};
let requestCount = 0;
async function get(label, base, endpoint, credential, params = {}, version = '2021-07-28') {
  if (report.network_unavailable) return null;
  if (requestCount++) await new Promise(r => setTimeout(r, mode === 'fathom' ? 1150 : 650));
  const url = new URL(`${base}${endpoint}`);
  for (const [k,v] of Object.entries(params)) url.searchParams.set(k, String(v));
  const call = { label, method: 'GET', path: endpoint, query: params };
  if (!base.includes('fathom.ai')) call.version_header=version;
  report.calls.push(call);
  const headers = base.includes('fathom.ai') ? { 'X-Api-Key': credential } :
    { Authorization: `Bearer ${credential}`, Version: version };
  try {
    const res = await fetch(url, { headers: { ...headers, Accept: 'application/json' },
      redirect: 'error', signal: AbortSignal.timeout(18000) });
    call.http_status = res.status; call.ok = res.ok;
    const body = await res.text();
    let data;
    try { data = JSON.parse(body); } catch { data = null; }
    call.response_keys = shape(data);
    if (!res.ok) {
      call.error = redact(JSON.stringify(data?.message ?? data?.error ?? body.slice(0,200)));
      return null;
    }
    return data;
  } catch (e) {
    call.ok = false; call.error_type = e.name;
    call.cause_code = e.cause?.code ?? null;
    if (['ENOTFOUND','EAI_AGAIN','ENETUNREACH','EACCES'].includes(call.cause_code)) report.network_unavailable=true;
    return null;
  }
}
function meetingMeta(m) {
  return { recording_id: m.recording_id, title: m.title, meeting_title: m.meeting_title,
    created_at: m.created_at, recording_start_time: m.recording_start_time,
    recorder_email: m.recorded_by?.email ?? null, recorder_team: m.recorded_by?.team ?? null,
    shared_with: m.shared_with, url: m.url, share_url: m.share_url };
}
const confirmActive = mode === 'fathom' && process.argv.includes('--confirm-active');
const currentVersion = mode === 'leadlock' && process.argv.includes('--current-version');
if (confirmActive) {
  if (keyEntries.length !== 1) throw new Error('Active key remains ambiguous; resolve duplicate entries first.');
  const key=env.FATHOM_API_KEY?.trim();
  const prior=JSON.parse(await readFile(path.join(out,'fathom/access_recheck_2026-10-20.json'),'utf8'));
  report.active_variable='FATHOM_API_KEY';
  report.secondary_variable_present=Boolean(env.FATHOM_E2M_API_KEY);
  report.active_key_entries=keyEntries.length;
  report.meetings=[];
  let cursor;
  for (let page=0;page<2;page++) {
    const data=await get(`active_key_content_page_${page+1}`,'https://api.fathom.ai/external/v1',
      '/meetings',key,{include_action_items:true,...(cursor?{cursor}:{})});
    if (!data) break;
    for (const m of data.items ?? []) {
      const actions=Array.isArray(m.action_items)?m.action_items:[];
      report.meetings.push({...meetingMeta(m),action_items_count:actions.length,
        actions_with_assignee:actions.filter(a=>a.assignee?.name || a.assignee?.email).length,
        action_field_names:[...new Set(actions.flatMap(shape))].sort(),
        actions_with_due_field:actions.filter(a=>Object.keys(a).some(k=>/due|deadline/i.test(k))).length});
    }
    if (!data.next_cursor) break;
    cursor=data.next_cursor;
  }
  report.known_client_matches=report.meetings.filter(m=>/penny|ridgefield/i.test(`${m.title} ${m.meeting_title}`));
  report.filter_checks=[];
  for (const email of ['hello@weddingindustryads.com','carmen@weddingindustryads.com']) {
    const data=await get(`recorder_filter_${email}`,'https://api.fathom.ai/external/v1',
      '/meetings',key,{'recorded_by[]':email});
    const rows=Array.isArray(data?.items)?data.items:[];
    report.filter_checks.push({recorder:email,http_status:report.calls.at(-1).http_status??null,
      returned_count:rows.length,matching_recorder_count:rows.filter(m=>m.recorded_by?.email===email).length,
      pagination_exhausted:Boolean(data && !data.next_cursor)});
  }
  const office=prior.keys?.[0]?.meetings?.find(m=>/office hours/i.test(`${m.title} ${m.meeting_title}`));
  if (office) {
    report.office_hour_sample={...office};
    const t=await get('office_hours_transcript','https://api.fathom.ai/external/v1',
      `/recordings/${office.recording_id}/transcript`,key);
    const s=await get('office_hours_summary','https://api.fathom.ai/external/v1',
      `/recordings/${office.recording_id}/summary`,key);
    const segments=Array.isArray(t?.transcript)?t.transcript:[];
    const summary=s?.summary?.markdown_formatted;
    report.office_hour_sample.content_check={transcript_segments:segments.length,
      segments_with_speaker:segments.filter(x=>x.speaker?.display_name).length,
      segments_with_timestamp:segments.filter(x=>x.timestamp).length,
      summary_present:Boolean(summary),summary_characters:summary?.length??0};
  }
} else if (mode === 'fathom') {
  report.duplicate_key_entries = keyEntries.map((k,i) => ({ entry: i+1, lines: k.lines,
    is_effective_under_existing_parseEnv: k.value === env.FATHOM_API_KEY?.trim() }));
  report.targets = ['The Penny + WIA | Monthly Strategy', 'Ridgefield x WIA | Monthly Strategy'];
  report.keys = [];
  for (const [index,key] of keyEntries.entries()) {
    const entry = { entry: index+1, env_lines: key.lines, calls: [], meetings: [], matches: [],
      pagination_exhausted: false, maximum_pages: 20, stopped_after_both_known_targets: false };
    report.keys.push(entry);
    const seen = new Set();
    let cursor;
    for (let page=0; page<20; page++) {
      const data = await get(`key_${index+1}_page_${page+1}`, 'https://api.fathom.ai/external/v1',
        '/meetings', key.value, cursor ? {cursor} : {});
      if (!data) break;
      if (!Array.isArray(data.items)) { entry.shape_error = 'items_not_array'; break; }
      report.calls.at(-1).returned_rows = data.items.length;
      for (const m of data.items) {
        if (!seen.has(m.recording_id)) { seen.add(m.recording_id); entry.meetings.push(meetingMeta(m)); }
      }
      entry.matches = entry.meetings.filter(m => /penny|ridgefield/i.test(`${m.title} ${m.meeting_title}`));
      if (!data.next_cursor) { entry.pagination_exhausted=true; break; }
      const both = ['penny','ridgefield'].every(name => entry.matches.some(m =>
        `${m.title} ${m.meeting_title}`.toLowerCase().includes(name)));
      if (both) { entry.stopped_after_both_known_targets=true; break; }
      if (data.next_cursor === cursor) { entry.pagination_error='repeated_cursor'; break; }
      cursor=data.next_cursor;
    }
    entry.recorder_counts = Object.fromEntries([...Map.groupBy(entry.meetings, m => m.recorder_email ?? 'unknown')]
      .map(([email,rows]) => [email,rows.length]));
    for (const name of ['penny','ridgefield']) {
      const target=entry.matches.find(m => `${m.title} ${m.meeting_title}`.toLowerCase().includes(name));
      if (!target) continue;
      const transcript=await get(`key_${index+1}_${name}_transcript`, 'https://api.fathom.ai/external/v1',
        `/recordings/${encodeURIComponent(target.recording_id)}/transcript`, key.value);
      const summary=await get(`key_${index+1}_${name}_summary`, 'https://api.fathom.ai/external/v1',
        `/recordings/${encodeURIComponent(target.recording_id)}/summary`, key.value);
      const segments=Array.isArray(transcript?.transcript) ? transcript.transcript : [];
      const text=summary?.summary?.markdown_formatted;
      target.content_check = { transcript_segments: segments.length,
        segments_with_speaker: segments.filter(s => s.speaker?.display_name).length,
        segments_with_timestamp: segments.filter(s => s.timestamp).length,
        transcript_characters: segments.reduce((n,s) => n+(s.text?.length ?? 0),0),
        summary_present: Boolean(text), summary_characters: text?.length ?? 0 };
    }
  }
} else {
  const prior = JSON.parse(await readFile(path.join(out, 'leadlock/agency_probe.json'), 'utf8'));
  const client = prior.selected_client;
  report.selected_client = { id: client.id, name: client.name };
  report.credential_checks = [];
  const creds = [
    { name:'GHL_AGENCY_PIT', value:env.GHL_AGENCY_PIT, location:client.id },
    { name:'GHL_PIT', value:env.GHL_PIT, location:env.GHL_LOCATION_ID },
  ];
  for (const cred of creds) {
    const entry={ variable:cred.name, present:Boolean(cred.value), location_id:cred.location,
      format_hint:cred.value?.startsWith('pit-') ? 'private_integration_token' : 'other', checks:[] };
    report.credential_checks.push(entry);
    if (!cred.value || !cred.location) continue;
    const reads=currentVersion ? [
      ['opportunities','/opportunities/search',{locationId:cred.location,limit:2}],
    ] : [
      ['location',`/locations/${encodeURIComponent(cred.location)}`,{}],
      ['pipelines','/opportunities/pipelines',{locationId:cred.location}],
      ['opportunities','/opportunities/search',{location_id:cred.location,limit:2}],
    ];
    if (!currentVersion && cred.name === 'GHL_AGENCY_PIT') reads.push(
      ['contacts','/contacts/',{locationId:cred.location,limit:2}],
      ['calendars','/calendars/',{locationId:cred.location}]);
    for (const [label,endpoint,params] of reads) {
      const data=await get(`${cred.name}_${label}`,'https://services.leadconnectorhq.com',
        endpoint,cred.value,params,currentVersion?'v3':'2021-07-28');
      const result={ resource:label, http_status:report.calls.at(-1).http_status ?? null,
        error:report.calls.at(-1).error ?? null };
      if (data) {
        if (label==='location') {
          const v=data.location ?? data;
          result.identity={id:v.id ?? v._id,name:v.name};
        } else {
          const list=data[label];
          result.returned_count=Array.isArray(list) ? list.length : null;
          result.sample_field_names=shape(list?.[0]);
          if (label==='pipelines' && Array.isArray(list)) result.stage_counts=list.map(p =>
            ({ pipeline_id:p.id, stages:Array.isArray(p.stages) ? p.stages.length : null }));
          if (label==='opportunities' && Array.isArray(list)) result.sample_statuses=list.map(p => p.status ?? null);
        }
      }
      entry.checks.push(result);
    }
  }
}
report.finished_at_utc=new Date().toISOString();
const relative=`${mode}/${confirmActive?'active_key_confirmation':currentVersion?'v3_access_recheck':'access_recheck'}_${date}.json`;
await writeFile(path.join(out,relative),JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify({ mode, calls:report.calls.length,
  statuses:report.calls.reduce((a,c) => { const k=c.http_status ?? 'network_error'; a[k]=(a[k]??0)+1; return a; },{}),
  keys:report.keys?.map(k => ({ entry:k.entry, env_lines:k.env_lines, meetings:k.meetings.length,
    pagination_exhausted:k.pagination_exhausted, recorder_counts:k.recorder_counts,
    matched_calls:k.matches.length, content_samples:k.matches.filter(m => m.content_check) })),
  active_key_entries:report.active_key_entries, known_client_matches:report.known_client_matches,
  filter_checks:report.filter_checks, office_hour_sample:report.office_hour_sample,
  credential_checks:report.credential_checks, report:`knowledge_base/wia-knowledge-base/verification/${relative}` },null,2));
