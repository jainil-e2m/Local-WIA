/* What the Node server relays to the Python backend (plan 1.F5, section 0 rule 3): the routes the app calls, the query
   parameters each may carry and how each is validated, and the few routes that need more than the tight defaults.
   Anything not listed here is a 404 at the server and never reaches the backend. Every route added to the app is added
   here, with a server test (allowlist.test.mjs scans the app's source and fails when one is missing). */

const id = '[A-Za-z0-9_-]{1,140}';
// A content pack's piece keys (backend packs/contracts_v2.py).
const piece = '(?:email|carousel|reel_[1-3])';
// Version names carry dots (wia-kb-2026-10-20.c-1a2b3c4d), never a leading dot or "..".
const version = '(?!\\.)(?![A-Za-z0-9_.-]*\\.\\.)[A-Za-z0-9_.-]{1,140}';

const GET = [
  `flags|me|seeds|weeks(?:/${id})?|transcripts/${id}|runs/${id}/comparison(?:\\.csv)?`,
  // The moments ledger: the list, its facets and one moment (2.B8); the topic registry (2.B7).
  `moments(?:/${id})?|topics`,
  // A brief's production hand-off (E.B23): what production reads for a brief of any contract version.
  `briefs(?:/${id}(?:/(?:versions|published|handoff|export\\.json|export\\.md))?)?|angles/${id}/research`,
  `intake/(?:overview|sources/${id}|buckets/${id}|revisions/${id}/original|assets/${id}/content)`,
  `calendar(?:/config)?|packs(?:/${id}(?:/production)?)?`,
  // Every stored document, with its filters, and one document with its passages (1.B8, 1.F3).
  // `extraction-health` (2.B12) reads as an id; it is named here so it is not lost if the id pattern is ever tightened.
  `documents(?:/(?:extraction-health|${id}))?`,
  // Context system (Phase L): review queue, known items, published pieces and knowledge-base versions.
  `context/(?:summary|kinds|queue|items|published|versions|warnings|items/${id}/history|versions/${version}/diff)`,
  // Cycles over a date window (3.B2/3.B3): the list, the preview with its estimate (approvers only, said by the API) and one
  // cycle with what it read; this week's standing budgets (6.B3); the week's review document, as Markdown or as a Word file
  // (5.B14).
  `cycles(?:/(?:preview|${id}))?|budgets|weeks/${id}/review\\.(?:md|docx)`,
  // The week's measures with its editorial monitoring, for the cycle panel (6.B13; backend week_measures.py).
  `weeks/${id}/measures`,
  // Content packs (Phase NP): the week's proposed allocation and the week's pack document, as Markdown or as a Word file
  // (NP.B11, NP.B12).
  `weeks/${id}/(?:pack-plan|packs\\.(?:md|docx))`,
  // The active settings for the Settings screen (6.F7; backend settings_api.py: editors and approvers read).
  `settings`,
  // The weekly cycle's schedule for the sidebar's Next run and the intake's weekly completion (3.B11; backend summary.py).
  `schedule`,
  // The failure alerts and the cost summary on Sources (6.F5; backend alerts.py, llm/cost_summary.py).
  `alerts|costs`,
  // Home's cycle summary, whose counts the sidebar and the bell share (6.F2; backend summary.py).
  `summary`,
];
const POST = [
  `weeks/${id}/considered/[0-9]{1,3}/(?:revive|decision)|jobs/${id}/retry`,
  // A published final recorded against its approved brief (L.B9). Gate 1's refresh with feedback (3.B7), and context and
  // attested facts at either gate (5.B7, interface 2). An approver confirms a card's public stance before it is developed
  // (D31, E.B30).
  `angles/${id}/(?:quality|decision|brief/retry|refresh|context|stance)|briefs/${id}/(?:answers|review|clearance|decision|revise|cta|published|context)`,
  `seeds|seeds/${id}/withdraw|search`,
  // Starting a cycle over a window, as previewed (3.B2): an approver's write, checked again by the API.
  `cycles`,
  // Search over moments and chunks (2.B6); a person's topics for a moment (2.B7). Only the writes the app makes are relayed
  // (allowlist.test.mjs fails on any other): no screen offers a live encoding, a live brief start, the old transcript search,
  // the topic administrator's actions or a mining pass, so none of them is forwarded.
  `moments/${id}/topics`,
  // A person classifies a call the rules could not place (1.F6); an editor uploads a transcript file (1.F7).
  `documents/${id}/classification|documents/import`,
  `intake/(?:refresh|complete|search|connections/(?:slack|fathom)/activate|jobs/${id}/retry)`,
  // A content pack's decision (ready to publish or back to review) and an approved brief's pack, created or retried (NP.B6).
  // The pack scheduling modal saves selected assets together.
  `packs/${id}/(?:decision|schedule)|briefs/${id}/pack`,
  // Content pack v2 (NP.B6): a before-publishing note marked done or a quote cleared, a flagged sentence attested (R57),
  // Finish again, the brief's line put back, a piece marked published. NP-7: a face-to-camera Reel's recorded take (NP.B14) and
  // finishing again with a permission (NP.B15).
  `packs/${id}/(?:clearances|finish|refinish|findings/${id}/attest|pieces/${piece}/(?:published|recorded))`,
  `context/(?:batch|items|published|published/confirm|published/import|versions|items/${id}/decision|published/${id}/(?:performance|link)|versions/${version}/(?:approve|benchmark|discard))`,
  // A person acknowledges an open alert on Sources (6.F5): an editor's or approver's write, checked again by the API.
  `alerts/${id}/dismiss`,
];
// A person's edit of one pack piece by dotted path (NP.B3, NP.F2).
const PATCH = [`(?:angles|briefs)/${id}`, `packs/${id}/pieces/${piece}`];
// The settings an approver changes on the Settings screen (6.F7): the duplicate cutoff and the weekly cycle's schedule, and
// only these. The screen shows the models, prompt profiles, knowledge-base pin and budgets read-only, so no browser session
// can change them through the relay (they stay `storage_cli settings` changes). The screen's list is the same
// (src/utils/settings.ts EDITABLE_KEYS; allowlist.test.mjs fails when the two differ).
export const SETTABLE = ['matching.duplicate', 'cycle.timezone', 'cycle.weekday', 'cycle.hour'];
const PUT = [`settings/(?:${SETTABLE.map(key => key.replaceAll('.', '\\.')).join('|')})`];

/** The writes the relay forwards, entry by entry, for the role matrix (roles.test.mjs, 6.X2) to prove each one covered. */
export const WRITE_ROUTES = { POST, PATCH, PUT };

const compile = parts => new RegExp(`^/(?:${parts.join('|')})$`);
const ROUTES = { GET: compile(GET), POST: compile(POST), PATCH: compile(PATCH), PUT: compile(PUT) };

export const METHODS = Object.keys(ROUTES);

/** Whether the app may call this method on this path (path as the relay sees it, without /api/atelier or a query). */
export const routeAllowed = (method, path) => !!ROUTES[method]?.test(path);

// ---- query parameters

const oneOf = values => value => values.includes(value);
const integer = (min, max) => value => /^\d+$/.test(value) && +value >= min && +value <= max;
const identifier = value => new RegExp(`^${id}$`).test(value);
const calendarDay = value => /^\d{4}-\d{2}-\d{2}$/.test(value) && Number.isFinite(Date.parse(`${value}T00:00:00Z`)) && new Date(`${value}T00:00:00Z`).toISOString().slice(0, 10) === value;
const datetime = value => value.length <= 50 && /(Z|[+-]\d{2}:\d{2})$/.test(value) && Number.isFinite(Date.parse(value));
// Free text: bounded, and no control characters.
const text = max => value => value.length > 0 && value.length <= max && !/[\u0000-\u001f\u007f]/.test(value);

// Each item of a comma-separated list is one of the set, none empty, none repeated; bounded so a list cannot be a payload.
const csvOf = values => value => {
  const items = value.split(',');
  return value.length <= 300 && items.every(item => values.includes(item)) && new Set(items).size === items.length;
};
const SOURCE_TYPES = ['zoom', 'fathom', 'slack', 'manual', 'file', 'attachment'];
const CALL_TYPES = ['client_1to1', 'office_hours', 'workshop', 'prospect', 'internal', 'vendor', 'fragment', 'slack_thread', 'other'];
const SPEAKER_ROLES = ['staff', 'client', 'prospect', 'vendor', 'outside', 'ai_agent', 'unknown'];
const MOMENT_TYPES = ['result', 'objection', 'decision', 'tension', 'mechanism', 'observation', 'story', 'testimonial', 'question', 'teaching', 'soundbite', 'data_point'];
const CONSENT_STATUSES = ['cleared', 'anonymise', 'internal_only', 'do_not_use'];
const KINDS = ['rule', 'exemplar', 'offer', 'price', 'roster_member', 'result', 'cta', 'process_step', 'belief', 'audience_phrase', 'format_rule', 'campaign', 'content_plan_entry', 'performance_note'];
const REVIEW = ['pending', 'approved', 'rejected'];
const paging = limit => ({ limit: integer(1, limit), offset: integer(0, 1_000_000) });
const MOMENT_FILTERS = {
  q: text(200), client_id: identifier, topic_id: identifier, document_id: identifier, extractor_version: text(100),
  source_type: oneOf(SOURCE_TYPES), call_type: oneOf(CALL_TYPES),
  speaker_role: csvOf(SPEAKER_ROLES), moment_type: csvOf(MOMENT_TYPES), consent_status: csvOf(CONSENT_STATUSES),
  from: datetime, to: datetime, quote_verified: oneOf(['true', 'false', 'any']), is_current: oneOf(['true', 'false', 'any']),
};

/** Per path: the only query parameters a read may carry, how each is checked, and the ones it must carry. */
const QUERIES = [
  { match: path => path === '/calendar', keys: { from: datetime, to: datetime, status: oneOf(['active', 'published', 'all']), cursor: integer(0, 1_000_000) }, required: ['from', 'to'] },
  { match: path => path === '/briefs', keys: { week_id: identifier, status: oneOf(REVIEW), ...paging(100) } },
  // The week pickers list live weeks; a toggle asks for the archived ones too (backend week_archive.py).
  { match: path => path === '/weeks', keys: { include_archived: oneOf(['true', 'false']) } },
  // Content packs by week and state (NP.B6).
  { match: path => path === '/packs', keys: { week_id: identifier, brief_id: identifier, state: oneOf(['finishing', 'waiting', 'in_review', 'ready_to_publish', 'generated']), ...paging(100) } },
  { match: path => path === '/seeds', keys: { status: oneOf(['open', 'used', 'withdrawn']) } },
  // The alerts with those resolved in the last 14 days (6.F5).
  { match: path => path === '/alerts', keys: { resolved: oneOf(['true', 'false']) } },
  // A cycle's window: both ends explicit instants; the start is required (3.B2).
  { match: path => path === '/cycles/preview', keys: { from: datetime, to: datetime }, required: ['from'] },
  { match: path => path === '/cycles', keys: { limit: integer(1, 100) } },
  { match: path => path === '/context/queue', keys: { kind: oneOf(KINDS), status: oneOf(['candidate', 'confirmed', 'rejected', 'retired']), ...paging(200) } },
  { match: path => path === '/context/items', keys: { kind: oneOf(KINDS), on: calendarDay } },
  { match: path => path === '/context/published', keys: { status: oneOf(['unconfirmed', 'confirmed']), ...paging(500) } },
  { match: path => /^\/context\/versions\/[^/]+\/diff$/.test(path), keys: { against: value => new RegExp(`^${version}$`).test(value) } },
  {
    // The documents list (1.F3): the filters the API accepts, each from its own closed set or bounded form.
    match: path => path === '/documents',
    keys: {
      source_type: oneOf(SOURCE_TYPES),
      call_type: oneOf(CALL_TYPES),
      included: oneOf(['true', 'false']),
      extraction_status: oneOf(['pending', 'queued', 'running', 'completed', 'failed', 'not_applicable']),
      date_state: oneOf(['dated', 'undated']),
      client_id: identifier, q: text(200), from: datetime, to: datetime, needs_review: oneOf(['true', 'false']), ...paging(200),
    },
  },
  {
    // The moments ledger and its facets (2.B8): the same filters as search. A list-valued filter travels as one comma-separated
    // parameter, because each parameter may appear once; every item is checked against its closed set.
    match: path => path === '/moments',
    keys: { ...MOMENT_FILTERS, ...paging(200) },
  },
  { match: path => path === '/moments/facets', keys: MOMENT_FILTERS },
  { match: path => path === '/topics', keys: { status: oneOf(['active', 'blocked', 'merged']), q: text(100), ...paging(200) } },
];

/** Whether the query is acceptable for this request: a path with no listed parameters takes none, each parameter appears
    once, each value passes its check, and the required ones are present. A write takes no query at all. */
export function queryAllowed(method, path, params) {
  if (!params.size) return true;
  const rule = QUERIES.find(candidate => candidate.match(path));
  if (method !== 'GET' || !rule) return false;
  const seen = new Set();
  for (const [key, value] of params) {
    if (seen.has(key) || !Object.hasOwn(rule.keys, key) || !rule.keys[key](value)) return false;
    seen.add(key);
  }
  return (rule.required ?? []).every(key => seen.has(key));
}

// ---- the routes that need more than the defaults

/** The default body limit and relay timeout stay tight. Two kinds of route are bounded exceptions. */
export const DEFAULT_BODY_LIMIT = '64kb';
// A CSV import of at most 60,000 characters (the API's own cap), which JSON escaping and multi-byte text can grow past 64 KB.
export const IMPORT_BODY_LIMIT = '384kb';
const IMPORT = /^\/context\/published\/import$/;
// A transcript upload (1.F7): one file's text, at most 2,000,000 characters (the API's own cap), which JSON escaping and
// multi-byte text can grow to about three times that.
export const UPLOAD_BODY_LIMIT = '6mb';
const UPLOAD = /^\/documents\/import$/;
export const bodyLimitFor = (method, path) => method !== 'POST' ? DEFAULT_BODY_LIMIT
  : IMPORT.test(path) ? IMPORT_BODY_LIMIT : UPLOAD.test(path) ? UPLOAD_BODY_LIMIT : DEFAULT_BODY_LIMIT;

// Reads that are large or slow by nature: exports, comparison reports, original transcripts and attachments, a
// document with all its passages (and the extraction health, which counts every document), a moment with the passages around
// it, the moments' facets, a version's changes. They get a longer relay timeout; writes never do.
const LONG_READS = [
  new RegExp(`^/briefs/${id}/export\\.(?:json|md)$`), new RegExp(`^/runs/${id}/comparison(?:\\.csv)?$`), new RegExp(`^/transcripts/${id}$`),
  // The week's review document, as Markdown or as a Word file (5.B14), and a cycle's preview, which estimates every call it
  // would make (3.B2).
  new RegExp(`^/weeks/${id}/review\\.(?:md|docx)$`), /^\/cycles\/preview$/,
  // The week's measures read every decision, brief and pack of this week and the one before (6.B13).
  new RegExp(`^/weeks/${id}/measures$`),
  // The week's pack document renders every pack unabbreviated, as Markdown or as a Word file (NP.B12).
  new RegExp(`^/weeks/${id}/packs\\.(?:md|docx)$`),
  // A brief checks every passage it cites against the original on each read, and a list does that for every brief.
  /^\/briefs$/, new RegExp(`^/briefs/${id}$`), new RegExp(`^/angles/${id}/research$`),
  // The week's whole review (every run, job and event of the week) and the packs: a busy week passed the 10 seconds on production.
  new RegExp(`^/weeks/${id}$`), /^\/packs$/, new RegExp(`^/packs/${id}$`), /^\/summary$/,
  new RegExp(`^/documents/${id}$`), new RegExp(`^/moments/${id}$`), new RegExp(`^/intake/(?:revisions/${id}/original|assets/${id}/content)$`), /^\/context\/versions\/[^/]+\/diff$/,
];
export const isLongRead = (method, path) => method === 'GET' && LONG_READS.some(pattern => pattern.test(path));
