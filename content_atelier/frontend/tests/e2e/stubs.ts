/// <reference types="node" />
/* The two services the Node server talks to, stubbed for the browser test (6.X1): Command Center's session endpoint and the
   Python backend's /storage routes. The backend answers recorded JSON in the generated API shapes (src/api/schema.d.ts, through
   the same synthetic fixtures the unit tests use) for the routes the acceptance path calls, and accepts its writes, changing
   what it answers next the way the backend would. Every text is synthetic (R52). */
import http from 'node:http';
import type { AddressInfo } from 'node:net';
import { ANGLE, ME_APPROVER, SCHEDULE, SUMMARY, WEEK } from '../../src/testing/fixtures';
import { BRIEF_V4, BRIEF_V4_APPROVED, PACK, PLAN, SUMMARY as PACK_SUMMARY } from '../../src/testing/packFixtures';

export const SESSION_COOKIE = 'wahha_session';
export const SESSION_TOKEN = 'e2e-session-token';
export const BACKEND_SECRET = 'e2e-backend-secret';
export const USER = { email: 'approver@example.invalid', name: 'Avery Approver', role: 'team' };
export const DOCX = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document';
// A Word file is a zip archive: bytes that are not valid UTF-8, so any text handling on the way would change them.
export const DOCX_BYTES = Buffer.from([0x50, 0x4b, 0x03, 0x04, 0x14, 0x00, 0xff, 0xfe, 0x80, 0xc3, 0x28, 0x0d, 0x0a, 0x1a, 0x50, 0x4b, 0x05, 0x06]);

export const WEEK_ID = 'week_2026-10-26';
const week = { ...WEEK, week_id: WEEK_ID, week_start: '2026-10-26', week_end: '2026-11-01' };
const ANGLE_ID = 'angle_1';

/** A strategist v7 card, synthetic, with nothing that holds it back from being developed. */
const card = {
  rank: 1, title: 'Why we read the reply first', pillar: 'WARM', content_type: 'behind_the_scenes', series: null,
  audience: 'Venue owners who already run ads', point: 'The first reply decides which couples book a tour.', point_is_about: 'wia_belief',
  surprise_for_experienced_advertiser: { surprising: true, reason: 'They tune the ads first.' }, reader_takeaway: 'I want a team that reads the whole path.',
  reader_fit: { buyer: 'elevate', buyer_statement: 'Owners who want leads that book.', why: 'Lead quality is their pain.' }, belief_ref: 'B3',
  why_it_matters: 'Fit beats volume.', wia_in_action: 'The strategist asks to see the first reply.', evidence_points: ['The strategist asks to see the first reply.'],
  guardrail: 'Keep the venue unnamed.', offer_fit: { offer: 'ELEVATE', cta_slot: 'soft_invitation', calendar_note: 'ELEVATE is open this window.' },
  public_stance: { takes_stance: false, stance: null }, recurrence: 'Came up on two calls.', moment_ids: [], verify_before_publishing: [], why_selected: 'Shows the WIA move.',
};

export interface Stubs {
  authOrigin: string;
  backendOrigin: string;
  /** Every session check Command Center answered, with the time it came. */
  sessionChecks: number[];
  /** The backend requests, `METHOD /storage/path?query`. */
  requests: string[];
  writes: { method: string; path: string; body: unknown }[];
  /** Requests the stub has no answer for (the test fails on any). */
  unanswered: string[];
  close: () => Promise<void>;
}

const listen = async (server: http.Server) => {
  await new Promise<void>(resolve => server.listen(0, '127.0.0.1', resolve));
  return `http://127.0.0.1:${(server.address() as AddressInfo).port}`;
};

const readBody = (req: http.IncomingMessage) => new Promise<string>(resolve => {
  let text = '';
  req.on('data', chunk => { text += chunk; });
  req.on('end', () => resolve(text));
});

export async function startStubs(): Promise<Stubs> {
  const sessionChecks: number[] = [];
  const requests: string[] = [], unanswered: string[] = [];
  const writes: Stubs['writes'] = [];
  // What the writes change: the card is developed (its brief is then written), the brief approved (its pack then exists).
  const state = { developed: false, approved: false };

  const commandCenter = http.createServer((req, res) => {
    const signedIn = (req.headers.cookie ?? '').split(';').map(part => part.trim()).includes(`${SESSION_COOKIE}=${SESSION_TOKEN}`);
    res.setHeader('content-type', 'application/json');
    if (req.method === 'GET' && req.url === '/api/auth/session') {
      sessionChecks.push(Date.now());
      if (!signedIn) { res.statusCode = 401; res.end(JSON.stringify({ error: 'Not authenticated.' })); return; }
      res.end(JSON.stringify({ user: USER }));
      return;
    }
    if (req.method === 'POST' && req.url === '/api/auth/logout') { res.end(JSON.stringify({ ok: true })); return; }
    res.statusCode = 404;
    res.end(JSON.stringify({ error: 'Unknown authentication endpoint.' }));
  });

  const angle = () => ({
    ...ANGLE, angle_id: ANGLE_ID, run_id: 'run_week', content_hash: 'hash_card', moment_ids: [],
    content_body: { title: card.title, card }, selection_status: 'visible', matching_result: { status: 'complete', current_batch_flags: [] },
    disposition: state.developed ? { disposition: 'develop', reason_code: null, author: USER.email, hold_until: null, note: null } : null,
    approval_status: state.developed ? 'approved' : 'pending', can_approve: !state.developed, can_edit: !state.developed, hold: null, refresh: null,
    stance_confirmation: null, public_use: null, account_memory: [],
  });
  const review = () => ({ week, angles: [angle()], runs: [], jobs: [], events: [], transcripts: [], roster: [], rubric: null });
  const summary = () => ({
    ...SUMMARY,
    waiting: { ...SUMMARY.waiting,
      cards_at_gate_1: { count: state.developed ? 0 : 1, who: 'an approver', by_week: state.developed ? [] : [{ week_id: WEEK_ID, n: 1 }] },
      held_cards_due_back: { count: 0, who: 'an approver', cards: [] },
      briefs_at_gate_2: { count: state.developed && !state.approved ? 1 : 0, who: 'an approver' },
      packs_in_review: { count: state.approved ? 1 : 0, who: 'an editor or an approver' }, packs_ready: 0,
      packs_with_the_system: { finishing: 0, waiting: 0, reasons: [] } },
    latest_cycle: { ...SUMMARY.latest_cycle, week_id: WEEK_ID },
    alerts: { open: 0, errors: 0 },
  });
  const brief = () => state.approved ? BRIEF_V4_APPROVED : BRIEF_V4;
  const measures = () => ({
    week_id: WEEK_ID, week_start: week.week_start, week_end: week.week_end, rubric: {}, briefs: {}, gate_two_edits: {}, packs: {}, thresholds: [],
    wia_reviewers_configured: true, previous_week_id: null,
    cards: { slate: 1, top_five: 1, developed_or_reframed_keeping_the_point: { wia: +state.developed, delegated: 0, all: +state.developed },
      top_five_developed_or_reframed_keeping_the_point: { wia: +state.developed, delegated: 0, all: +state.developed } },
    monitoring: { accepted_share: state.developed ? 1 : 0, bar: 0.5, cards_decided: +state.developed, decided_at_least: 4, gate_1_done: false, skip_reasons: [],
      cards_with_evidence_flags: 0, cycle: { run_id: 'run_week', knowledge_base_version: 'kb-e2e', strategist_profile: 'strategist-e2e', started_from: 'schedule', cost_usd: 0.42, model_calls: 3 } },
  });

  const reads: [RegExp, () => unknown][] = [
    [/^\/flags$/, () => ({ briefs: true, packs: true, calendar: false, context: false })],
    [/^\/me$/, () => ({ ...ME_APPROVER, email: USER.email, name: USER.name })],
    [/^\/summary$/, summary],
    [/^\/schedule$/, () => SCHEDULE],
    [/^\/weeks(?:\?include_archived=true)?$/, () => [week]],
    [new RegExp(`^/weeks/${WEEK_ID}$`), review],
    [new RegExp(`^/weeks/${WEEK_ID}/measures$`), measures],
    [new RegExp(`^/weeks/${WEEK_ID}/pack-plan$`), () => ({ ...PLAN, week_id: WEEK_ID })],
    [/^\/seeds\?status=open$/, () => []],
    [/^\/cycles(?:\?limit=\d+)?$/, () => []],
    [/^\/budgets$/, () => ({ week_start: '2026-10-26', week_end: '2026-11-02', enabled: true, total_cap_usd: 5, total_spent_usd: 0.42, budgets: [] })],
    [new RegExp(`^/angles/${ANGLE_ID}/research$`), () => state.developed
      ? { status: 'completed', run_id: 'run_brief', mode: 'replay', waiting_reason: null, error_summary: null, brief_id: BRIEF_V4.brief_id, jobs: [] }
      : { status: 'not_started', run_id: null, mode: null, waiting_reason: null, error_summary: null, brief_id: null, jobs: [] }],
    [/^\/briefs\?/, () => ({ items: state.developed ? [brief()] : [], total: state.developed ? 1 : 0, limit: 20, offset: 0 })],
    [new RegExp(`^/briefs/${BRIEF_V4.brief_id}$`), brief],
    [new RegExp(`^/briefs/${BRIEF_V4.brief_id}/versions$`), () => []],
    [/^\/calendar\/config$/, () => ({ enabled: false, display_timezone: 'America/Chicago', worker_ready: false })],
    [/^\/packs\?/, () => state.approved ? { items: [PACK_SUMMARY], total: 1, limit: 100, offset: 0 } : { items: [], total: 0, limit: 100, offset: 0 }],
    [new RegExp(`^/packs/${PACK.pack_id}$`), () => PACK],
  ];
  const documents: [RegExp, string, () => Buffer][] = [
    [new RegExp(`^/weeks/${WEEK_ID}/review\\.md$`), 'text/markdown; charset=utf-8', () => Buffer.from('# Content Atelier review, week of 26 October\n\nOne card developed.\n')],
    [new RegExp(`^/weeks/${WEEK_ID}/packs\\.md$`), 'text/markdown; charset=utf-8', () => Buffer.from('# Content packs, week of 26 October\n')],
    [new RegExp(`^/weeks/${WEEK_ID}/(?:review|packs)\\.docx$`), DOCX, () => DOCX_BYTES],
  ];

  const backend = http.createServer(async (req, res) => {
    const url = req.url ?? '';
    const path = url.replace(/^\/storage/, '');
    requests.push(`${req.method} ${url}`);
    const send = (status: number, body: unknown) => { res.statusCode = status; res.setHeader('content-type', 'application/json'); res.end(JSON.stringify(body)); };
    // The Node server's own secret and the verified email: never the browser's.
    if (req.headers.authorization !== `Bearer ${BACKEND_SECRET}` || req.headers['x-atelier-email'] !== USER.email || !url.startsWith('/storage/')) {
      return send(401, { detail: 'Verified backend authorization required' });
    }
    if (req.method !== 'GET') {
      const text = await readBody(req);
      const body = text ? JSON.parse(text) : null;
      writes.push({ method: req.method ?? '', path, body });
      if (req.method === 'POST' && path === `/angles/${ANGLE_ID}/decision`) {
        state.developed = true;
        return send(200, { angle_id: ANGLE_ID, approval_status: 'approved', decision_id: 'decision_card', brief_run: { run_id: 'run_brief', status: 'queued' } });
      }
      if (req.method === 'POST' && path === `/briefs/${BRIEF_V4.brief_id}/decision`) {
        state.approved = true;
        return send(200, { brief_id: BRIEF_V4.brief_id, content_hash: BRIEF_V4.content_hash, approval_status: 'approved', decision_id: 'decision_brief',
          pack_run: { pack_id: PACK.pack_id, run_id: 'run_pack', status: 'queued', mode: 'replay', error: null }, pack_note: null });
      }
      unanswered.push(`${req.method} ${path}`);
      return send(404, { detail: 'Not found' });
    }
    const document = documents.find(([pattern]) => pattern.test(path));
    if (document) { res.setHeader('content-type', document[1]); res.end(document[2]()); return; }
    const read = reads.find(([pattern]) => pattern.test(path));
    if (read) return send(200, read[1]());
    unanswered.push(`GET ${path}`);
    return send(404, { detail: 'Not found' });
  });

  const [authOrigin, backendOrigin] = await Promise.all([listen(commandCenter), listen(backend)]);
  return {
    authOrigin, backendOrigin, sessionChecks, requests, writes, unanswered,
    close: async () => {
      for (const server of [commandCenter, backend]) { server.closeAllConnections(); await new Promise(resolve => server.close(resolve)); }
    },
  };
}
