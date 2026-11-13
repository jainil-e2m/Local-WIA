/** Builds the LOCAL-ONLY Dubsado event dataset for the Invoices & Contracts v2 mockup.
 * Read-only Gmail search of hello@ (stored gmail.readonly OAuth token) for mail from dubsado.com.
 * Reads Subject/From/Date headers only: no bodies, no recipient addresses. Classifies contract signings
 * and payments, extracts signer/payer, amount and project label, and matches them to GHL clients by name.
 * Output: knowledge_base/wia-knowledge-base/frontend/src/dubsado-live.local.json (gitignored; never ship it).
 * Run after build_finance_live.mjs: node knowledge_base/wia-knowledge-base/verification/google/build_dubsado_live.mjs
 */
import { readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { accessToken, directory } from './oauth_store.mjs';

const src = path.resolve(directory, '../../frontend/src');
const target = path.join(src, 'dubsado-live.local.json');
const token = await accessToken();
const API = 'https://gmail.googleapis.com/gmail/v1/users/me/messages';
let requests = 0;
// Gmail answers bursts with 403/429 (per-user rate limit), so back off and retry a few times.
async function get(url, attempt = 0) {
  requests++;
  const res = await fetch(url, { headers: { Authorization: `Bearer ${token}` }, signal: AbortSignal.timeout(20000), redirect: 'error' });
  if ((res.status === 403 || res.status === 429) && attempt < 7) { await new Promise(r => setTimeout(r, 2000 * 2 ** attempt)); return get(url, attempt + 1); }
  if (!res.ok) throw new Error(`Gmail HTTP ${res.status}`);
  return res.json();
}

// 1. Every message from dubsado.com (bounded at 10 pages of 100).
const ids = []; let pageToken = '';
for (let page = 0; page < 10; page++) {
  const d = await get(`${API}?maxResults=100&q=${encodeURIComponent('from:dubsado.com')}${pageToken ? `&pageToken=${pageToken}` : ''}`);
  ids.push(...(d.messages ?? []).map(m => m.id));
  if (!d.nextPageToken) break;
  pageToken = d.nextPageToken;
}

// 2. Headers only, in small parallel batches.
const headers = [];
for (let i = 0; i < ids.length; i += 3) {
  const batch = await Promise.all(ids.slice(i, i + 3).map(id => get(`${API}/${id}?format=metadata&metadataHeaders=Subject&metadataHeaders=From&metadataHeaders=Date`)));
  for (const m of batch) { const h = Object.fromEntries((m.payload?.headers ?? []).map(x => [x.name, x.value])); headers.push({ id: m.id, threadId: m.threadId, date: new Date(Number(m.internalDate)).toISOString().slice(0, 10), from: (h.From ?? '').replace(/.*<|>.*/g, ''), subject: h.Subject ?? '' }); }
}

// 3. Classify and parse.
const OFFERS = [[/^GSA\b/i, 'Google Search Accelerator'], [/^MAIE\b/i, 'Meta Ads Accelerator'], [/^Accelerators?\b/i, 'Accelerator Bundle'], [/LeadLock/i, 'LeadLock'], [/ELEVATE/i, 'Elevate']];
function project(label) {
  const offer = OFFERS.find(([re]) => re.test(label))?.[1] ?? null;
  const business = label.replace(/^(GSA|MAIE|Accelerators?)\s*-\s*/i, '').replace(/^LeadLock\s*\|\s*/i, '').replace(/\s*\|\s*ELEVATE\s*$/i, '').trim();
  return { label: label.trim(), offer, business };
}
const events = headers.map(h => {
  let m;
  if ((m = h.subject.match(/^(.+?) (?:has )?signed your contract for (.+)$/i))) return { ...h, type: 'signed', person: m[1].trim(), ...project(m[2]) };
  if ((m = h.subject.match(/^(.+?) (?:has )?paid ([\d,]+\.\d{2}) ([A-Z]{3}) - (.+)$/i))) return { ...h, type: 'paid', person: m[1].trim(), amount: Number(m[2].replace(/,/g, '')), currency: m[3], ...project(m[4]) };
  if (/completed your questionnaire|submitted a draft of your questionnaire/i.test(h.subject)) return { ...h, type: 'questionnaire' };
  if (/^New Lead:/i.test(h.subject)) return { ...h, type: 'lead' };
  if (/Workflow Error/i.test(h.subject)) return { ...h, type: 'workflow_error' };
  return { ...h, type: 'other' };
});

// 3b. For signings and payments only, read the body just to keep the Dubsado contract/invoice link (nothing else is saved).
const LINK = /https?:\/\/[\w.-]*dubsado\.com\/public\/(?:contract|invoices?|form)\/[^\s"'<>\])]+/i;
const finance0 = events.filter(e => e.type === 'signed' || e.type === 'paid');
for (let i = 0; i < finance0.length; i += 3) {
  await Promise.all(finance0.slice(i, i + 3).map(async e => {
    const m = await get(`${API}/${e.id}?format=full`);
    let text = ''; const walk = p => { if (!p) return; if (p.body?.data) text += Buffer.from(p.body.data, 'base64url').toString('utf8'); (p.parts ?? []).forEach(walk); }; walk(m.payload);
    const body = text.replace(/&amp;/g, '&');
    // Older alerts wrap the link in Dubsado's click tracking (url902.dubsado.com/ls/click…). Keep that link as-is:
    // it redirects to the same contract/invoice page. It is not resolved here, which would register a click.
    const button = [...body.matchAll(/<a\b[^>]*href=["']?([^"' >]+)[^>]*>([\s\S]*?)<\/a>/gi)]
      .find(([, href, label]) => /dubsado\.com/i.test(href) && /contract|invoice|view|pay/i.test(label.replace(/<[^>]+>/g, '')));
    e.link = body.match(LINK)?.[0] ?? button?.[1] ?? null;
    e.linkTracked = !body.match(LINK) && !!button;
  }));
}

// 4. Match to GHL clients (from the finance live file) by person name, then business name.
let ghl = [];
try { ghl = JSON.parse(await readFile(path.join(src, 'finance-live.local.json'), 'utf8')).clients ?? []; } catch { /* Finance file optional. */ }
const norm = t => String(t ?? '').toLowerCase().replace(/&/g, 'and').replace(/\b(llc|inc|co|the)\b/g, '').replace(/[^a-z0-9]+/g, ' ').trim();
const byName = new Map(ghl.filter(c => c.name).map(c => [norm(c.name), c.id]));
for (const e of events) {
  if (e.type !== 'signed' && e.type !== 'paid') continue;
  e.clientId = byName.get(norm(e.person)) ?? byName.get(norm(e.business)) ?? ghl.find(c => norm(e.business) && norm(c.name).includes(norm(e.business)))?.id ?? null;
  e.match = e.clientId ? (byName.get(norm(e.person)) ? 'person name' : 'business name') : 'none';
}

const finance = events.filter(e => e.type === 'signed' || e.type === 'paid').map(({ subject, from, ...rest }) => ({ ...rest, from }));
const out = { generated_at: new Date().toISOString(), note: 'Local-only real Dubsado notification data from hello@. Do not share, publish or commit.',
  counts: Object.fromEntries(Object.entries(events.reduce((a, e) => { a[e.type] = (a[e.type] || 0) + 1; return a; }, {}))),
  // Unclassified subjects as masked patterns (no names or amounts), to spot finance types not yet parsed.
  other_patterns: Object.fromEntries(Object.entries(events.filter(e => e.type === 'other').reduce((a, e) => {
    const k = `${e.from} | ${e.subject.replace(/[\d,]+(\.\d{2})?/g, '#').replace(/^\S+(\s\S+)?\s(?=(has|have|is|was|viewed|accepted|declined|sent|requested|scheduled|booked|opened|updated|cancel))/i, 'NAME ').replace(/\s(for|-|:)\s.*$/, ' $1 …')}`;
    a[k] = (a[k] || 0) + 1; return a; }, {})).sort((x, y) => y[1] - x[1]).slice(0, 40)),
  events: finance };
await writeFile(target, JSON.stringify(out, null, 2));
const signed = finance.filter(e => e.type === 'signed'), paid = finance.filter(e => e.type === 'paid');
console.log(JSON.stringify({ saved: path.relative(path.resolve(directory, '../../../..'), target), requests, messages: ids.length, counts: out.counts,
  signed: signed.length, paid: paid.length, paid_total: paid.reduce((s, e) => s + e.amount, 0), matched: finance.filter(e => e.clientId).length,
  match_by: finance.reduce((a, e) => { a[e.match] = (a[e.match] || 0) + 1; return a; }, {}), date_range: [finance.map(e => e.date).sort()[0], finance.map(e => e.date).sort().pop()],
  offers: finance.reduce((a, e) => { const k = e.offer ?? '(none in label)'; a[k] = (a[k] || 0) + 1; return a; }, {}),
  links: { contract: signed.filter(e => e.link).length + ' of ' + signed.length, invoice: paid.filter(e => e.link).length + ' of ' + paid.length } }, null, 1));
