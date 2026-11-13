/* ============================================================================
   WIA CLIENT PORTFOLIO — PLAIN JAVASCRIPT
   No framework, package imports, network requests, or build step are needed.

   EDITING MAP
   • Colours, spacing and responsive layouts: #portfolio-styles in <head>.
   • Client copy and records: #portfolio-data near the end of this file.
   • Card structure: renderClientCard(). Tab structure: renderClientDetail().
   • Tab content: renderNow(), renderProfile(), renderHistory(), renderBrief(),
     renderCommitments(), renderMeetings(), renderInvoices(), renderAttendance().
   • Interaction wiring: handleClick(), handleInput(), handleKeydown().
   • Images, fonts and SVGs are embedded separately after the readable code.
   ============================================================================ */

'use strict';

const DATA = JSON.parse(document.getElementById('portfolio-data').textContent);
const ASSETS = JSON.parse(document.getElementById('portfolio-assets').textContent);
const ICONS = JSON.parse(document.getElementById('portfolio-icons').textContent);
const { CLIENTS, EVIDENCE, INITIAL_ACTIONS, CALLS, INVOICES, EVENTS, TEAM, DEMO_DATE } = DATA;
const STORAGE_KEY = 'wia-readable-portfolio-actions-v1';
const TAB_LABELS = {
  now: 'Now', profile: 'Client profile', history: 'Engagement history',
  brief: 'Handover brief', commitments: 'Commitments', meetings: 'Meetings',
  money: 'Invoices & terms', attendance: 'Attendance'
};

const state = {
  query: '', filter: 'all', layout: 'grid', sort: 'attention',
  historyMode: 'spine', historyLane: 'all', commitmentSide: 'all',
  collapsed: false, mobileOpen: false, actions: loadActions(),
  dialog: null, select: null, calendar: null, toastTimer: null
};

// 1. DATA, FORMATTING AND SHARED HTML PRIMITIVES

function escapeHtml(value = '') {
  return String(value).replace(/[&<>"']/g, character => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  })[character]);
}

function icon(name, size = 14, strokeWidth = 2) {
  const svg = ICONS[name] || ICONS.FileText;
  return svg.replace(/width="\d+"/, `width="${size}"`)
    .replace(/height="\d+"/, `height="${size}"`)
    .replace(/stroke-width="[^"]+"/, `stroke-width="${strokeWidth}"`);
}

function dateLabel(date, options = { month: 'short', day: 'numeric' }) {
  return new Intl.DateTimeFormat('en-IN', { ...options, timeZone: 'Asia/Kolkata' })
    .format(new Date(`${date}T12:00:00+05:30`));
}

function timeLabel(time) {
  const [hour, minute] = time.split(':').map(Number);
  return `${hour % 12 || 12}:${String(minute).padStart(2, '0')} ${hour >= 12 ? 'PM' : 'AM'}`;
}

function money(amount) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(amount);
}

function clientById(id) { return CLIENTS.find(client => client.id === id); }
function sourceById(id) { return EVIDENCE.find(source => source.id === id); }
function isOutstanding(action) { return ['Open', 'In progress'].includes(action.status); }
function isOverdue(action) { return isOutstanding(action) && action.due < DEMO_DATE; }
function clientActions(client) { return state.actions.filter(action => action.clientId === client.id); }

function loadActions() {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY));
    if (Array.isArray(saved) && saved.length && saved.every(action =>
      action && CLIENTS.some(client => client.id === action.clientId) &&
      EVIDENCE.some(source => source.id === action.sourceId) &&
      typeof action.title === 'string' && typeof action.owner === 'string' &&
      typeof action.note === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(action.due) &&
      ['Open', 'In progress', 'Done', 'Verified'].includes(action.status) &&
      ['WIA', 'Client'].includes(action.side) && typeof action.acknowledged === 'boolean'
    )) return saved;
  } catch { /* The HTML also works when file:// storage is unavailable. */ }
  return structuredClone(INITIAL_ACTIONS);
}

function badge(text, tone = 'neutral', dot = true) {
  return `<span class="badge badge-${tone}">${dot ? '<i aria-hidden="true"></i>' : ''}${escapeHtml(text)}</span>`;
}

function avatar(client, small = false) {
  return `<span class="client-avatar ${small ? 'small' : ''} avatar-${client.tone}" aria-hidden="true">${client.initials}</span>`;
}

function sourceIcon(kind, size = 14) {
  return icon(['Zoom', 'Fathom'].includes(kind) ? 'Video' : kind === 'Gmail' ? 'Mail' : kind === 'Slack' ? 'MessageSquare' : 'FileText', size, 1.7);
}

function sourceLink(id, label) {
  const source = sourceById(id);
  if (!source) return '<span class="muted small-text">Source unavailable</span>';
  return `<button class="source-link source-${source.kind.toLowerCase()}" data-action="evidence" data-id="${source.id}">
    ${sourceIcon(source.kind)}${escapeHtml(label || source.kind)}${icon('ArrowUpRight', 11)}
  </button>`;
}

function panel(title, content, eyebrow = '', action = '', className = '') {
  return `<section class="panel ${className}">
    ${title ? `<div class="panel-heading"><div>${eyebrow ? `<p class="eyebrow">${eyebrow}</p>` : ''}<h2>${title}</h2></div>${action}</div>` : ''}
    ${content}
  </section>`;
}

function empty(title = 'Nothing here yet', description = 'Try a different search or filter.') {
  return `<div class="empty-state">${icon('Search', 24)}<h3>${title}</h3><p>${description}</p></div>`;
}

function coverage(value) {
  return `<div class="coverage"><div class="coverage-track"><span style="width:${value}%"></span></div><span>${value}%</span></div>`;
}

function sparkline(client) {
  const maximum = Math.max(...client.activity, 1);
  const points = client.activity.map((value, index) => `${index * (100 / (client.activity.length - 1))},${26 - value / maximum * 21}`).join(' ');
  return `<svg class="sparkline sparkline-${client.tone}" viewBox="0 0 104 30" role="img" aria-label="Sample communication activity over the past twelve weeks">
    <polyline fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round" stroke-linecap="round" points="${points}"></polyline>
    <circle cx="100" cy="${26 - client.activity.at(-1) / maximum * 21}" r="2.5" fill="currentColor"></circle>
  </svg>`;
}

function segmented(label, action, selected, options) {
  return `<div class="segmented" role="group" aria-label="${label}">${options.map(([id, text, count]) => `
    <button class="${selected === id ? 'selected' : ''}" aria-pressed="${selected === id}" data-action="${action}" data-value="${id}">
      ${text}${count === undefined ? '' : `<span>${count}</span>`}
    </button>`).join('')}</div>`;
}

function selectControl(label, key, value, options, id = '') {
  const selected = options.find(option => option[0] === value);
  return `<button ${id ? `id="${id}"` : ''} type="button" role="combobox" class="atelier-select-trigger"
    aria-label="${label}" aria-haspopup="listbox" aria-expanded="false" data-action="select" data-select="${key}"
    data-options="${escapeHtml(JSON.stringify(options))}" data-value="${escapeHtml(value)}">
    <span>${escapeHtml(selected?.[1] || value)}</span>${icon('ChevronDown', 14)}
  </button>`;
}

function detailsList(entries) {
  return `<dl class="detail-list">${entries.map(([label, value]) => `<div><dt>${label}</dt><dd>${value}</dd></div>`).join('')}</dl>`;
}

// 2. APP SHELL, SIDEBAR AND HASH NAVIGATION

function getRoute() {
  const [view, id, requestedTab] = location.hash.slice(1).split('/');
  if (view === 'calls' && CALLS.some(call => call.id === id)) return { view: 'calls', id };
  const client = clientById(id);
  const allowed = client && (requestedTab !== 'attendance' || client.type === 'accelerator');
  return { view: 'clients', client: client || null, tab: allowed && TAB_LABELS[requestedTab] ? requestedTab : 'now' };
}

function openClient(id, tab = 'now') { navigate(`clients/${id}/${tab}`); }
function openCall(id) { navigate(`calls/${id}`); }
function navigate(hash) {
  const previous = getRoute();
  if (hash === 'clients' && (previous.client || previous.view !== 'clients')) {
    state.query = ''; state.filter = 'all'; state.layout = 'grid'; state.sort = 'attention';
  }
  closeDialog();
  closeSelect(false);
  closeCalendar(false);
  state.mobileOpen = false;
  syncSidebar();
  if (location.hash === `#${hash}`) renderPage();
  else location.hash = hash;
}

function renderShell() {
  const navigation = [
    ['Overview', 'House'], ['Client portfolio', 'FolderOpen'], ['Call preparation', 'CalendarDays'],
    ['Action register', 'ListChecks'], ['Health & sentiment', 'HeartHandshake'], ['Invoices & contracts', 'ReceiptText']
  ];
  document.getElementById('app').innerHTML = `
    <div class="app-shell">
      <a class="skip-link" href="#main-content" data-action="skip">Skip to content</a>
      <div class="ambient" aria-hidden="true"></div>
      <aside class="sidebar">
        <div class="sidebar-floral" aria-hidden="true"><img src="${ASSETS.flower}" alt=""></div>
        <div class="sidebar-orbit" aria-hidden="true"><canvas></canvas></div>
        <div class="sidebar-brand">
          <img src="${ASSETS.logo}" alt="Wedding Industry Ads">
          <div><span>Client Knowledge</span><small>A little more understood.</small></div>
          <button class="icon-button mobile-close" aria-label="Close navigation" data-action="close-navigation">${icon('X', 18)}</button>
        </div>
        <nav aria-label="Main navigation">
          <p class="nav-label">THE CLIENT DESK</p>
          ${navigation.map(([label, symbol]) => `<button class="nav-item ${label === 'Client portfolio' ? 'active' : ''}"
            ${label === 'Client portfolio' ? 'data-action="portfolio" aria-current="page"' : 'disabled aria-disabled="true"'}
            title="${label}" ${label === 'Action register' ? 'data-outstanding-count' : ''}>
            ${icon(symbol, 19, 1.65)}<span>${label}</span>${label === 'Action register' ? `<b>${state.actions.filter(isOutstanding).length}</b>` : ''}
          </button>`).join('')}
          <div class="nav-divider"></div><p class="nav-label">THE FOUNDATION</p>
          <button class="nav-item" title="Source library" data-action="sources">${icon('BookOpen', 19, 1.65)}<span>Source library</span></button>
          <button class="nav-item" title="Connections" disabled aria-disabled="true">${icon('Plug', 19, 1.65)}<span>Connections</span></button>
        </nav>
        <div class="sidebar-bottom">
          <div class="sidebar-person"><div class="person-avatar">WH</div>
            <div><strong>Whitney Hodges</strong><small>Founder · Wedding Industry Ads</small></div>
            <button class="icon-button collapse-button" aria-label="Collapse sidebar" data-action="collapse">${icon('PanelLeftClose', 17)}</button>
          </div>
          <span class="sidebar-footnote">${icon('ArrowLeftToLine', 11)} A shared memory for your team</span>
        </div>
      </aside>
      <div class="workspace">
        <header class="utility-header"><div class="header-leading">
          <button class="icon-button mobile-menu" aria-label="Open navigation" aria-expanded="false" data-action="open-navigation">${icon('Menu', 20)}</button>
          <div id="header-title"></div>
        </div><div class="header-tools">
          <button class="header-search" aria-label="Search the workspace" data-action="search">${icon('Search', 16)}<span>Search</span><kbd>⌘ K</kbd></button>
          <button class="icon-button notification-button" aria-label="Open attention items" data-action="alerts">${icon('Bell', 18)}<i></i></button>
          <button class="header-user" aria-label="About the Whitney preview account" data-action="about">WH</button>
        </div></header>
        <main id="main-content" tabindex="-1"></main>
        <footer class="workspace-footer"><span>Wedding Industry Ads <i>✧</i> Client Knowledge Base</span><span>Frontend preview · October 9, 2026</span></footer>
      </div>
    </div>
    <div id="dialog-host"></div><div id="toast-host" aria-live="polite"></div>`;
  startSidebarOrbit();
}

function syncSidebar() {
  document.querySelector('.app-shell').classList.toggle('sidebar-is-collapsed', state.collapsed);
  const sidebar = document.querySelector('.sidebar');
  sidebar.classList.toggle('collapsed', state.collapsed);
  sidebar.classList.toggle('mobile-open', state.mobileOpen);
  const collapse = document.querySelector('[data-action="collapse"]');
  collapse.setAttribute('aria-label', state.collapsed ? 'Expand sidebar' : 'Collapse sidebar');
  collapse.innerHTML = icon(state.collapsed ? 'Menu' : 'PanelLeftClose', 17);
  document.querySelector('[data-action="open-navigation"]').setAttribute('aria-expanded', state.mobileOpen);
  document.querySelector('.mobile-scrim')?.remove();
  if (state.mobileOpen) {
    const scrim = document.createElement('button');
    scrim.className = 'mobile-scrim';
    scrim.dataset.action = 'close-navigation';
    scrim.setAttribute('aria-label', 'Close navigation');
    sidebar.before(scrim);
  }
}

function renderHeader(route) {
  document.title = `${route.client?.name || (route.view === 'calls' ? 'Call preparation' : 'Client portfolio')} · WIA Client Knowledge`;
  document.getElementById('header-title').innerHTML = route.client ? `
    <nav class="header-breadcrumbs" aria-label="Breadcrumb">
      <a href="#clients">Client portfolio</a>${icon('ChevronRight', 13)}
      <a class="header-client" href="#clients/${route.client.id}/now" ${route.tab === 'now' ? 'aria-current="page"' : ''}>${escapeHtml(route.client.name)}</a>
    </nav>` : route.view === 'calls' ? '<nav class="header-breadcrumbs" aria-label="Breadcrumb"><span>Call preparation</span></nav>' : `
    <div class="workspace-title"><h1>Client Portfolio</h1><span class="workspace-title-help">
      <button class="icon-button" aria-label="About Client Portfolio" aria-describedby="portfolio-tooltip">${icon('Info', 18)}</button>
      <span id="portfolio-tooltip" class="workspace-title-tooltip" role="tooltip">See each client's engagement, progress, and open priorities in one place, with a direct path to their full record.</span>
    </span></div>`;
}

function renderPage() {
  const route = getRoute();
  renderHeader(route);
  document.getElementById('main-content').innerHTML = route.view === 'calls'
    ? renderCallBrief(CALLS.find(call => call.id === route.id))
    : route.client ? renderClientDetail(route.client, route.tab) : renderPortfolio();
  if (!route.client && route.view === 'clients') updatePortfolioCards();
  const count = document.querySelector('[data-outstanding-count] b');
  count.textContent = state.actions.filter(isOutstanding).length;
  document.querySelector('.notification-button i').hidden = !state.actions.some(isOverdue);
}

// 3. PORTFOLIO FILTERS, CARD VIEW AND LIST VIEW

function renderPortfolio() {
  return `<div class="view" data-view="portfolio">
    <div class="toolbar">
      ${segmented('Filter client portfolio', 'portfolio-filter', state.filter, [
        ['all', 'All clients', 6], ['watch', 'Needs attention', 2], ['retainer', 'Retainers', 4], ['accelerator', 'Accelerators', 2]
      ])}
      <div class="toolbar-right">
        <label class="search-field">${icon('Search', 16)}
          <input aria-label="Search clients" placeholder="Find a client…" value="${escapeHtml(state.query)}" data-input="portfolio-search">
          <button class="icon-button" aria-label="Clear search clients" data-action="clear-search" ${state.query ? '' : 'hidden'}>${icon('X', 14)}</button>
        </label>
        <label class="sr-only" for="client-sort">Sort clients</label>
        ${selectControl('Sort clients', 'sort', state.sort, [['attention', 'Attention first'], ['name', 'A to Z']], 'client-sort')}
        <div class="layout-toggle" role="group" aria-label="Portfolio layout">
          <button class="${state.layout === 'grid' ? 'selected' : ''}" aria-label="Card view" aria-pressed="${state.layout === 'grid'}" data-action="layout" data-value="grid">${icon('LayoutGrid', 16)}</button>
          <button class="${state.layout === 'list' ? 'selected' : ''}" aria-label="List view" aria-pressed="${state.layout === 'list'}" data-action="layout" data-value="list">${icon('List', 17)}</button>
        </div>
      </div>
    </div>
    <div id="portfolio-results"></div>
    <div class="quiet-footer">${icon('Users', 14)}Each client has one maintained record. All views read from that same history.</div>
  </div>`;
}

function updatePortfolioCards() {
  const query = state.query.toLowerCase();
  const clients = CLIENTS.filter(client =>
    `${client.name} ${client.contact} ${client.service} ${client.location}`.toLowerCase().includes(query) &&
    (state.filter === 'all' || (state.filter === 'watch' && client.health === 'Needs attention') || state.filter === client.type)
  ).sort((a, b) => state.sort === 'name' ? a.name.localeCompare(b.name)
    : Number(b.health === 'Needs attention') - Number(a.health === 'Needs attention'));
  const results = document.getElementById('portfolio-results');
  if (!results) return;
  results.innerHTML = clients.length ? `<div class="client-grid ${state.layout === 'list' ? 'client-list' : ''}">${clients.map(renderClientCard).join('')}</div>` : empty('No clients match your search');
  document.querySelector('[data-action="clear-search"]').hidden = !state.query;
}

function renderClientCard(client) {
  const call = CALLS.find(item => item.clientId === client.id);
  const count = clientActions(client).filter(isOutstanding).length;
  return `<article class="client-card" data-client-id="${client.id}">
    <div class="client-card-top">${avatar(client)}${badge(client.health, client.health === 'On track' ? 'green' : client.tone)}</div>
    <button class="client-name-link" data-action="client" data-id="${client.id}"><h2>${escapeHtml(client.name)}</h2>${icon('ArrowUpRight', 16)}</button>
    <p class="client-card-meta">${escapeHtml(client.category)} · ${escapeHtml(client.location)}</p>
    <span class="service-label">${escapeHtml(client.service)}</span>
    <p class="client-card-focus">${escapeHtml(client.focus)}</p>
    <div class="client-card-stats">
      <div><span class="small-label">OPEN ACTIONS</span><strong>${String(count).padStart(2, '0')}</strong></div>
      <div><span class="small-label">12-WEEK ACTIVITY</span>${sparkline(client)}</div>
    </div>
    <div class="client-card-coverage"><span>Source coverage</span>${coverage(client.coverage)}</div>
    <div class="client-card-footer"><span>${icon('CalendarDays', 13)}${call ? `${dateLabel(call.date)} · ${timeLabel(call.time)}` : 'No upcoming call'}</span>
      <button class="text-button" data-action="client" data-id="${client.id}">Open record${icon('ArrowRight', 14)}</button>
    </div>
  </article>`;
}

// 4. CLIENT RECORD: SHARED HEADING AND ALL EIGHT TAB RENDERERS

function renderClientDetail(client, tab) {
  const call = CALLS.find(item => item.clientId === client.id);
  const open = clientActions(client).filter(isOutstanding);
  const tabs = Object.entries(TAB_LABELS).filter(([id]) => id !== 'attendance' || client.type === 'accelerator');
  const renderers = {
    now: renderNow, profile: renderProfile, history: renderHistory, brief: renderBrief,
    commitments: renderCommitments, meetings: renderMeetings, money: renderInvoices, attendance: renderAttendance
  };
  return `<div class="view client-detail">
    <button class="back-link" data-action="portfolio">${icon('ArrowLeft', 14)}Back to client portfolio</button>
    <div class="client-detail-heading">${avatar(client)}<div>
      <p class="eyebrow">THE MAINTAINED CLIENT RECORD</p><h1>${escapeHtml(client.name)}</h1>
      <p>${escapeHtml(client.service)} <span>·</span> ${escapeHtml(client.location)} <span>·</span> With WIA since ${dateLabel(client.since, { month: 'long', year: 'numeric' })}</p>
    </div><div class="client-detail-actions">
      ${badge(client.health, client.health === 'On track' ? 'green' : client.tone)}
      ${call ? `<button class="button button-gold" data-action="call" data-id="${call.id}">${icon('CalendarDays', 15)}Prepare for the call</button>` : ''}
    </div></div>
    <div class="client-tabs" role="group" aria-label="Client record sections">${tabs.map(([id, label]) => `
      <button class="${tab === id ? 'active' : ''}" aria-pressed="${tab === id}" data-action="tab" data-id="${client.id}" data-tab="${id}">
        ${label}${id === 'commitments' ? `<span>${open.length}</span>` : ''}
      </button>`).join('')}</div>
    ${renderers[tab](client)}
  </div>`;
}

function renderNow(client) {
  const rows = clientActions(client), open = rows.filter(isOutstanding);
  const call = CALLS.find(item => item.clientId === client.id);
  const source = EVIDENCE.find(item => item.clientId === client.id && item.tag !== 'Background');
  return `<div class="client-now-intro"><div><p class="eyebrow">THE CURRENT PICTURE</p><h2>What matters this week.</h2><p>${escapeHtml(client.summary)}</p></div>
    <div class="now-counts">${[[open.length, 'open actions'], [rows.filter(isOverdue).length, 'overdue'], [open.filter(action => action.side === 'Client').length, 'waiting on client']].map(([count, label]) => `<div><strong>${count}</strong><span>${label}</span></div>`).join('')}</div>
  </div>
  <div class="detail-grid">
    ${panel('The weekly focus', `<div class="focus-icon">${icon('Target', 22)}</div><h3 class="focus-title">${escapeHtml(client.focus)}</h3>${sourceLink(source?.id || client.profileSource, 'See the context')}`, 'ONE CLEAR PRIORITY')}
    ${call ? panel('The next conversation', `<div class="next-call-type">${icon('CalendarDays', 23)}<div><h3>${call.type}</h3><p>${dateLabel(call.date)} · ${timeLabel(call.time)} IST · ${call.host}</p></div></div><p class="body-copy">${escapeHtml(call.objective)}</p><button class="text-button" data-action="call" data-id="${call.id}">Open the call brief${icon('ArrowRight', 14)}</button>`, 'ON THE CALENDAR') : ''}
  </div>
  ${panel('The commitments to keep', renderActionRows(open), '', `<button class="text-button" data-action="tab" data-id="${client.id}" data-tab="commitments">View all${icon('ArrowRight', 13)}</button>`)}
  <div class="detail-grid">
    ${panel('The relationship signal', `${badge(client.sentiment, client.tone)}<p class="body-copy">${escapeHtml(client.summary)}</p><span class="muted small-text">A sample interpretation of client communication.</span>`)}
    ${panel('What the record can tell us', `<div class="coverage-label"><span>Source coverage</span>${coverage(client.coverage)}</div><p class="body-copy">History begins ${dateLabel(client.since)}. ${client.type === 'accelerator' ? 'Some office-hour sessions have attendance records without transcripts.' : 'Background, client conversations, and recent team updates are available.'}</p><button class="text-button" data-action="sources" data-id="${client.id}">Explore the sources${icon('ArrowRight', 14)}</button>`)}
  </div>`;
}

function renderProfile(client) {
  const facts = [['Their audience', client.audience], ['What sets them apart', client.differentiator], ['Their voice', client.voice], ['The goal of this engagement', client.goal]];
  return `<div class="profile-grid">
    ${panel('A business worth understanding', `<p class="profile-story">${escapeHtml(client.story)}</p><div class="profile-facts">${facts.map(([label, value]) => `<div><h3>${label}</h3><p>${escapeHtml(value)}</p>${sourceLink(client.profileSource)}</div>`).join('')}</div>`, 'CLIENT BACKGROUND')}
    <div>${panel('The people & the agreement', detailsList([
      ['Primary contact', escapeHtml(client.contact)], ['Email', escapeHtml(client.email)], ['Location', escapeHtml(client.location)],
      ['Service', escapeHtml(client.service)], ['Engagement began', dateLabel(client.since)]
    ]))}<div class="note-box">${icon('FileText', 17)}<p>Client facts and voice belong to this account. Their source stays attached as the record evolves.</p></div></div>
  </div>`;
}

function renderHistory(client) {
  const lanes = ['Onboarding', 'Communication', 'Meetings', 'Commitments', 'Work delivered'];
  const events = EVENTS.filter(event => event.clientId === client.id && (state.historyLane === 'all' || event.lane === state.historyLane));
  const start = new Date(`${client.since}T12:00:00`).getTime();
  const duration = Math.max(new Date(`${DEMO_DATE}T12:00:00`).getTime() - start, 1);
  const spine = `<div class="spine-scroll"><div class="spine"><div class="spine-dates"><span>${dateLabel(client.since)}</span><span>Record through Oct 9</span></div>
    ${lanes.filter(lane => state.historyLane === 'all' || state.historyLane === lane).map((lane, index) => `<div class="spine-lane"><span class="spine-label">${lane}</span><div class="spine-track lane-${index}">
      ${events.filter(event => event.lane === lane).map(event => `<button aria-label="${escapeHtml(event.title)}, ${dateLabel(event.date)}" title="${dateLabel(event.date)} · ${escapeHtml(event.title)}" style="left:${Math.max(1, Math.min(97, (new Date(`${event.date}T12:00:00`).getTime() - start) / duration * 100))}%" data-action="evidence" data-id="${event.sourceId}"></button>`).join('')}
    </div></div>`).join('')}</div></div>
    <div class="spine-legend"><span><i class="legend-dot"></i>An event with source context</span><span>Empty periods mean no entries in this preview.</span></div>`;
  const feed = `<div class="history-feed">${[...events].reverse().map(event => `<div class="history-event">
    <div class="history-date">${dateLabel(event.date)}<small>${event.lane}</small></div><div class="history-node"><span></span></div>
    <div class="history-copy"><h3>${escapeHtml(event.title)}</h3><p>${escapeHtml(event.detail)}</p></div>${sourceLink(event.sourceId)}
  </div>`).join('')}${!events.length ? empty('No events in this category') : ''}</div>`;
  return `<div class="toolbar">
    ${segmented('History display', 'history-mode', state.historyMode, [['spine', 'Engagement spine'], ['feed', 'Activity feed']])}
    <label class="sr-only" for="history-lane">History category</label>
    ${selectControl('History category', 'historyLane', state.historyLane, [['all', 'All categories'], ...lanes.map(lane => [lane, lane])], 'history-lane')}
  </div>
  ${state.historyMode === 'spine' ? panel('The shape of the engagement', spine, 'ONE HISTORY, SEVERAL THREADS') : ''}
  ${panel(state.historyMode === 'spine' ? 'Moments that shaped the account' : 'The account, in order', feed, 'THE EVIDENCE TRAIL')}
  <div class="note-box">${icon('History', 17)}<p>This record begins ${dateLabel(client.since)}. Earlier history is not included; a missing entry is not proof that nothing happened.</p></div>`;
}

function renderBrief(client) {
  const open = clientActions(client).filter(isOutstanding);
  const sections = [
    ['Who they are', `<p>${escapeHtml(client.story)}</p>${sourceLink(client.profileSource)}`],
    ['Where things stand', `<p>${escapeHtml(client.summary)}</p><p><strong>Current focus:</strong> ${escapeHtml(client.focus)}</p>`],
    ['The promises still open', open.length ? open.map(action => `<p>• ${escapeHtml(action.title)} <span class="muted">— ${escapeHtml(action.owner)}, ${dateLabel(action.due)}</span></p>`).join('') : '<p>No open commitments.</p>'],
    ['What this record cannot tell you', `<p>History starts on ${dateLabel(client.since)}. Earlier conversations are not represented. ${client.type === 'accelerator' ? 'Recent office-hour sessions may have attendance records without transcripts.' : 'The record has no live ad-performance data.'} Missing evidence should be confirmed with the account owner.</p>`]
  ];
  return panel('The brief for the next person', `
    <div class="handover-intro">${icon('ShieldCheck', 27)}<p>A clear starting point for anyone taking care of ${escapeHtml(client.name)}.</p></div>
    <div class="handover-sections">${sections.map(([title, body], index) => `<section><span>${String(index + 1).padStart(2, '0')}</span><div><h3>${title}</h3>${body}</div></section>`).join('')}</div>`,
  'CONTINUITY, WITHOUT THE CATCH-UP', `<button class="button button-outline button-small" data-action="copy-brief" data-id="${client.id}">${icon('Clipboard', 14)}Copy brief</button>`);
}

function renderCommitments(client) {
  const rows = clientActions(client).filter(action => state.commitmentSide === 'all' || action.side === state.commitmentSide);
  return `<div class="toolbar">${segmented('Commitment side', 'commitment-side', state.commitmentSide, [
    ['all', 'All commitments'], ['WIA', 'What we owe them'], ['Client', 'What we need from them']
  ])}</div>${panel('', renderActionRows(rows))}`;
}

function renderActionRows(rows) {
  return `<div class="action-rows compact">${rows.map(action => {
    const client = clientById(action.clientId), outstanding = isOutstanding(action);
    return `<div class="action-row ${outstanding ? '' : 'completed'}" data-action-row="${action.id}">
      <button class="action-checkbox ${outstanding ? '' : 'checked'}" aria-label="${outstanding ? 'Mark' : 'Reopen'} ${escapeHtml(action.title)}${outstanding ? ' done' : ''}" title="${outstanding ? 'Mark done' : 'Reopen action'}" data-action="toggle-action" data-id="${action.id}">${outstanding ? '' : icon('Check', 13)}</button>
      <div class="action-main"><button class="action-title" data-action="action-details" data-id="${action.id}">${escapeHtml(action.title)}</button>
        <div class="action-subline"><button data-action="client" data-id="${client.id}">${escapeHtml(client.name)}</button><span>·</span><span>${action.side === 'Client' ? 'Waiting on client' : escapeHtml(action.owner)}</span>${!action.acknowledged && outstanding ? '<span class="text-amber">· Not acknowledged</span>' : ''}</div>
      </div>
      <div class="action-due"><span class="${isOverdue(action) ? 'text-amber' : ''}">${isOverdue(action) ? 'Overdue · ' : action.due === DEMO_DATE ? 'Today · ' : ''}${dateLabel(action.due)}</span>
        ${badge(action.status, action.status === 'Verified' ? 'green' : action.status === 'Done' ? 'blue' : action.status === 'In progress' ? 'gold' : 'neutral', false)}
      </div>${sourceLink(action.sourceId)}
      ${action.status === 'Done' ? `<button class="button button-small button-outline" data-action="verify-action" data-id="${action.id}">${icon('CheckCheck', 13)}Verify</button>` : `<button class="icon-button" aria-label="Details for ${escapeHtml(action.title)}" data-action="action-details" data-id="${action.id}">${icon('ChevronRight', 17)}</button>`}
    </div>`;
  }).join('')}${rows.length ? '' : empty('All clear in this view')}</div>`;
}

function renderMeetings(client) {
  const call = CALLS.find(item => item.clientId === client.id);
  const meetings = EVIDENCE.filter(source => source.clientId === client.id && ['Zoom', 'Fathom'].includes(source.kind));
  return panel('The conversations behind the account', meetings.map(source => `<div class="meeting-record">
    <span class="meeting-icon">${icon('MessageSquare', 22, 1.5)}</span><div><h3>${escapeHtml(source.title)}</h3><p>${dateLabel(source.date)} · ${escapeHtml(source.author)}</p><span class="muted small-text">${escapeHtml(source.locator)} · ${source.tag}</span></div>${sourceLink(source.id, 'Read transcript')}
  </div>`).join('') + (call ? `<div class="next-meeting"><p class="small-label">NEXT SCHEDULED</p><h3>${call.type} · ${dateLabel(call.date)}</h3><button class="text-button" data-action="call" data-id="${call.id}">Read the upcoming brief${icon('ArrowRight', 14)}</button></div>` : ''), 'CALLS & RECORDED DECISIONS');
}

function renderInvoices(client) {
  const rows = INVOICES.filter(invoice => invoice.clientId === client.id);
  return panel('The agreement & invoice record', `<div class="table-scroll"><table class="invoice-table">
    <thead><tr><th>Client / invoice</th><th>Amount</th><th>Due date</th><th>Standing</th><th>Terms</th></tr></thead>
    <tbody>${rows.map(invoice => `<tr><td><button class="table-client" data-action="tab" data-id="${client.id}" data-tab="money">${avatar(client, true)}<span><strong>${escapeHtml(client.name)}</strong><small>${invoice.id} · issued ${dateLabel(invoice.issued)}</small></span></button></td>
      <td><strong>${money(invoice.amount)}</strong></td><td>${dateLabel(invoice.due)}${invoice.paid ? `<small class="block muted">Paid ${dateLabel(invoice.paid)}</small>` : ''}</td>
      <td>${badge(invoice.status, invoice.status === 'Paid' ? 'green' : invoice.status === 'Overdue' ? 'amber' : 'blue')}</td>
      <td><button class="text-button" data-action="invoice" data-id="${invoice.id}">View terms${icon('ArrowUpRight', 13)}</button></td></tr>`).join('')}</tbody>
    </table>${rows.length ? '' : empty('No invoices in this view')}</div>`, 'COMMERCIAL CONTEXT');
}

function renderAttendance(client) {
  return panel('A programme with people in it', `<p class="body-copy">Recent sessions for ${escapeHtml(client.contact)}. These are sample attendance records, distinct from transcript availability.</p>
    <div class="attendance-list">${['2026-09-24', '2026-10-01', '2026-10-08'].map((date, index) => {
      const missed = client.id === 'willow' && index > 0;
      return `<div>${icon('CalendarDays', 18)}<div><strong>${client.service.includes('Meta') ? 'Meta' : 'Google'} office hours</strong><small>${dateLabel(date)}</small></div>
        ${badge(missed ? 'Missed' : 'Attended', missed ? 'amber' : 'green')}
        ${index === 0 && client.id === 'willow' ? sourceLink('willow-fathom') : '<span class="muted small-text">Transcript not in preview</span>'}</div>`;
    }).join('')}</div>`, 'OFFICE-HOUR ATTENDANCE');
}

// 5. RELATED CALL BRIEFS (REACHED FROM CLIENT RECORDS)

function renderCallBrief(call) {
  const client = clientById(call.clientId);
  return `<div class="view">
    <button class="back-link" data-action="client" data-id="${client.id}">${icon('ArrowLeft', 14)}Back to ${escapeHtml(client.name)}</button>
    <div class="page-heading"><div><p class="eyebrow">BEFORE THE CONVERSATION</p><h1>Walk in with context.</h1><p class="page-description">A concise, cited brief, shaped around the purpose of each call.</p></div>
      <div class="heading-actions"><button class="button button-outline" data-action="download-call" data-id="${call.id}">${icon('Download', 15)}Download brief</button></div>
    </div><div class="call-workspace"><aside class="call-list"><p class="small-label">ON YOUR CALENDAR</p>
      ${CALLS.map(item => { const person = clientById(item.clientId); return `<button class="call-list-item ${item.id === call.id ? 'active' : ''}" data-action="call" data-id="${item.id}">
        <div class="call-list-date"><span>${item.date === DEMO_DATE ? 'TODAY' : dateLabel(item.date).toUpperCase()}</span><strong>${timeLabel(item.time)}</strong></div>
        <div class="call-list-client">${avatar(person, true)}<div><h3>${escapeHtml(person.name)}</h3><p>${item.type}</p></div></div>
        <div class="call-list-bottom"><span>${item.host} · ${item.duration}</span>${icon('CheckCircle2', 13)}</div></button>`; }).join('')}
      <div class="calendar-note">${icon('CalendarDays', 18)}<p>Calendar events are matched to a client and call type before a brief is prepared.</p></div>
    </aside><div class="call-brief">
      <div class="call-brief-heading"><div><p class="eyebrow">YOUR CALL BRIEF</p><h2>${escapeHtml(client.name)}</h2>
        <div class="call-meta"><span>${icon('CalendarDays', 13)}${dateLabel(call.date)}</span><span>${icon('Clock3', 13)}${timeLabel(call.time)} IST</span><span>${icon('UserRound', 13)}${call.host}</span></div>
      </div><div class="call-heading-right">${badge('Ready to review', 'green')}<button class="icon-button" aria-label="Copy call brief" data-action="copy-call" data-id="${call.id}">${icon('Clipboard', 17)}</button></div></div>
      <div class="call-type-line">${badge(call.type, 'blue', false)}<span>${call.duration} · ${call.sourceIds.length} sources</span><button class="text-button" data-action="client" data-id="${client.id}">Client record${icon('ArrowRight', 13)}</button></div>
      <div class="call-objective">${icon('Target', 20)}<div><p class="small-label">THE PURPOSE OF THIS CALL</p><h3>${escapeHtml(call.objective)}</h3></div></div>
      <section class="brief-section"><h3>Where things stand</h3><p>${escapeHtml(call.context)}</p><div class="inline-sources">${call.sourceIds.slice(0, 2).map(id => sourceLink(id)).join('')}</div></section>
      <div class="brief-two-col"><section class="brief-section"><h3>A suggested agenda</h3><ol class="agenda-list">${call.agenda.map((item, index) => `<li><span>${String(index + 1).padStart(2, '0')}</span><p>${escapeHtml(item)}</p></li>`).join('')}</ol></section>
        <section class="brief-section"><h3>What we need from the client</h3><ul class="need-list">${call.needs.map(item => `<li><span></span><p>${escapeHtml(item)}</p></li>`).join('')}</ul></section></div>
      <div class="insight-box">${icon('Sparkles', 19)}<div><h4>An opportunity worth exploring</h4><p>${escapeHtml(call.opportunity)}</p><small>Suggested interpretation · confirm together on the call</small></div></div>
      ${panel('Keep these commitments in view', clientActions(client).filter(isOutstanding).map(action => `<div class="brief-action"><span class="small-circle"></span><div><strong>${escapeHtml(action.title)}</strong><small>${escapeHtml(action.owner)} · due ${dateLabel(action.due)}</small></div>${sourceLink(action.sourceId)}</div>`).join(''), '', icon('ListChecks', 17), 'brief-actions-panel')}
      <div class="call-footer">${icon('CheckCircle2', 14)}<span>Sample brief assembled from the client record.</span><button class="text-button" data-action="copy-call" data-id="${call.id}">Copy brief${icon('Clipboard', 13)}</button></div>
    </div></div>
  </div>`;
}

// 6. DRAWERS, EVIDENCE, INVOICE TERMS AND EDITABLE COMMITMENTS

function showDialog(title, content, subtitle = '', drawer = true, kind = '') {
  closeDialog();
  const previousFocus = document.activeElement;
  const host = document.getElementById('dialog-host');
  host.innerHTML = `<dialog class="${drawer ? 'drawer' : 'modal'}" aria-labelledby="dialog-title">
    <div class="dialog-heading"><div>${subtitle ? `<p class="eyebrow">${escapeHtml(subtitle)}</p>` : ''}<h2 id="dialog-title">${escapeHtml(title)}</h2></div>
      <button class="icon-button" aria-label="Close dialog" data-action="close-dialog">${icon('X', 20)}</button></div>
    <div class="dialog-body">${content}</div></dialog>`;
  const dialog = host.querySelector('dialog');
  state.dialog = { element: dialog, previousFocus, kind };
  dialog.addEventListener('cancel', event => { event.preventDefault(); closeDialog(); });
  dialog.addEventListener('click', event => {
    const rect = dialog.getBoundingClientRect();
    if (event.target === dialog && (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom)) closeDialog();
  });
  dialog.showModal();
}

function closeDialog() {
  if (!state.dialog) return;
  closeSelect(false);
  closeCalendar(false);
  const { element, previousFocus } = state.dialog;
  state.dialog = null;
  element.close();
  element.remove();
  if (previousFocus?.isConnected) previousFocus.focus();
}

function showEvidence(id) {
  const source = sourceById(id), client = clientById(source.clientId);
  showDialog('Behind the insight', `
    <div class="evidence-source"><span class="source-mark source-${source.kind.toLowerCase()}">${sourceIcon(source.kind, 22)}</span><div><h3>${escapeHtml(source.title)}</h3><p>${source.kind} · ${dateLabel(source.date)} · ${escapeHtml(client.name)}</p></div></div>
    <div class="evidence-meta">${badge(source.tag, 'blue', false)}<span>${escapeHtml(source.locator)}</span></div>
    <div class="evidence-quote">${icon('Quote', 24, 1.2)}<p>${escapeHtml(source.excerpt)}</p></div>
    ${detailsList([['Recorded by', escapeHtml(source.author)], ['Client', escapeHtml(client.name)], ['Source date', dateLabel(source.date, { day: 'numeric', month: 'long', year: 'numeric' })], ['Record type', 'Fictional preview excerpt']])}
    <div class="note-box">${icon('CheckCircle2', 16)}<p>The statement and its interpretation are shown separately. This excerpt is sample content for the frontend review.</p></div>
    <button class="button button-primary full-width" data-action="tab" data-id="${client.id}" data-tab="history">See the client’s full history${icon('ArrowRight', 15)}</button>
  `, 'SOURCE EVIDENCE');
}

function showSources(clientId) {
  const sources = EVIDENCE.filter(source => !clientId || source.clientId === clientId);
  showDialog('The sources behind the record', `<div class="export-source-list">${sources.map(source => `
    <button class="source-card" data-action="evidence" data-id="${source.id}">
      <div class="source-card-top">${sourceIcon(source.kind, 18)}${source.kind}<span>${dateLabel(source.date)}</span></div>
      <h2>${escapeHtml(source.title)}</h2><p class="source-card-client">${escapeHtml(clientById(source.clientId).name)}</p>
      <p class="source-card-excerpt">${escapeHtml(source.excerpt)}</p>
    </button>`).join('')}</div>`, 'SOURCE LIBRARY');
}

function showInvoice(id) {
  const invoice = INVOICES.find(item => item.id === id), client = clientById(invoice.clientId);
  showDialog('The commercial agreement', `
    <div class="contract-icon">${icon('FileCheck2', 27, 1.3)}</div><h3 class="drawer-action-title">${escapeHtml(client.service)}</h3>
    ${detailsList([['Terms', escapeHtml(invoice.terms)], ['Amount', money(invoice.amount)], ['Invoice', invoice.id], ['Due', dateLabel(invoice.due)], ['Standing', badge(invoice.status, invoice.status === 'Paid' ? 'green' : 'amber')]])}
    ${panel('Reminder history', invoice.reminders.length ? `<ul class="reminder-list">${invoice.reminders.map(reminder => `<li>${icon('ReceiptText', 14)}${escapeHtml(reminder)}</li>`).join('')}</ul>` : '<p class="muted body-copy">No reminders recorded.</p>')}
    <p class="muted body-copy">Sample terms and invoice history for this frontend preview. The workspace displays the record; payments are handled in the billing system.</p>
  `, client.name);
}

function actionDialogContent(action) {
  return `${badge(isOverdue(action) ? 'Overdue' : action.status, isOverdue(action) ? 'amber' : 'blue')}
    <h3 class="drawer-action-title">${escapeHtml(action.title)}</h3><p class="body-copy">${escapeHtml(action.note)}</p>
    <div class="form-stack">
      <label>Owner${selectControl('Owner', `owner:${action.id}`, action.owner, [...new Set([...TEAM, action.owner])].map(owner => [owner, owner]))}</label>
      <label>Due date<button class="atelier-date-trigger" aria-label="Due date" aria-haspopup="dialog" aria-expanded="false" data-action="calendar" data-id="${action.id}"><span>${dateLabel(action.due, { day: 'numeric', month: 'short', year: 'numeric' })}</span>${icon('CalendarDays', 16)}</button></label>
      <label>Status${selectControl('Status', `status:${action.id}`, action.status, ['Open', 'In progress', 'Done', 'Verified'].map(status => [status, status]))}</label>
    </div>
    <div class="acknowledgement">${icon('CircleCheck', 17)}<span>${action.acknowledged ? 'Acknowledged by the owner' : 'Awaiting acknowledgement'}</span><button class="text-button" data-action="acknowledge" data-id="${action.id}">${action.acknowledged ? 'Undo' : 'Acknowledge'}</button></div>
    <div class="source-section"><p class="small-label">WHERE THE COMMITMENT CAME FROM</p>${sourceLink(action.sourceId, 'Read the original context')}</div>`;
}

function showAction(id) {
  const action = state.actions.find(item => item.id === id);
  showDialog('A commitment to keep', actionDialogContent(action), clientById(action.clientId).name, true, `action:${id}`);
}

function updateAction(id, patch) {
  state.actions = state.actions.map(action => action.id === id ? { ...action, ...patch } : action);
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(state.actions)); } catch { /* Edits remain usable in memory. */ }
  const kind = state.dialog?.kind;
  renderPage();
  if (kind === `action:${id}`) {
    state.dialog.element.querySelector('.dialog-body').innerHTML = actionDialogContent(state.actions.find(action => action.id === id));
  }
}

function showAlerts() {
  const overdue = state.actions.filter(isOverdue);
  showDialog('A few things need attention.', overdue.length ? overdue.map(action => `
    <button class="alert-item" data-action="tab" data-id="${action.clientId}" data-tab="commitments">${badge('Overdue', 'amber')}<h3>${escapeHtml(action.title)}</h3><p>${escapeHtml(clientById(action.clientId).name)} · ${escapeHtml(action.owner)}</p></button>
  `).join('') : empty('No overdue commitments'), 'THE OPEN LOOPS');
}

function showAbout() {
  showDialog('A shared memory. A clearer next step.', `<div class="about-icon">${icon('BookOpen', 31, 1.3)}</div>
    <p class="body-copy">A maintained picture of each client: their background, conversations, commitments, and the next thing that needs care.</p>
    <div class="about-facts">${['Six fictional client records make the views easy to explore.', 'Action edits stay in this browser and update the other views.', 'Call briefs, evidence, and handover context are available in one workspace.'].map(text => `<div>${icon('CheckCircle2', 16)}<p>${text}</p></div>`).join('')}</div>
    <p class="muted body-copy">No live accounts, AI generation, or client messages are connected. The Content Atelier history integration remains a separate later build.</p>
    <button class="button button-primary" data-action="close-dialog">Back to the client desk${icon('ArrowRight', 14)}</button>
  `, 'THE CLIENT KNOWLEDGE BASE', false);
}

function showSearch() {
  showDialog('Find a little context.', `<label class="global-search">${icon('Search', 19)}<input autofocus placeholder="A client, a promise, or a phrase…" aria-label="Search all clients and sources" data-input="global-search"><kbd>ESC</kbd></label><div id="global-results"></div>
    <div class="search-footer">${icon('Command', 12)} Ctrl / ⌘ K to open · Escape to close</div>`, 'SEARCH THE WORKSPACE', false, 'search');
  updateGlobalSearch('');
}

function updateGlobalSearch(query) {
  const needle = query.trim().toLowerCase();
  const clients = CLIENTS.filter(client => `${client.name} ${client.contact} ${client.service}`.toLowerCase().includes(needle));
  const sources = needle ? EVIDENCE.filter(source => `${source.title} ${source.excerpt}`.toLowerCase().includes(needle)).slice(0, 5) : [];
  const actions = needle ? state.actions.filter(action => action.title.toLowerCase().includes(needle)).slice(0, 4) : [];
  document.getElementById('global-results').innerHTML = `
    ${clients.length ? `<div class="search-group"><p class="small-label">CLIENTS</p>${clients.map(client => `<button class="search-result" data-action="client" data-id="${client.id}">${avatar(client, true)}<div><strong>${escapeHtml(client.name)}</strong><span>${escapeHtml(client.service)} · ${escapeHtml(client.contact)}</span></div>${icon('ArrowRight', 14)}</button>`).join('')}</div>` : ''}
    ${actions.length ? `<div class="search-group"><p class="small-label">COMMITMENTS</p>${actions.map(action => `<button class="search-result" data-action="tab" data-id="${action.clientId}" data-tab="commitments">${icon('Sparkles', 17)}<div><strong>${escapeHtml(action.title)}</strong><span>${escapeHtml(clientById(action.clientId).name)} · ${action.status}</span></div>${icon('ArrowRight', 14)}</button>`).join('')}</div>` : ''}
    ${sources.length ? `<div class="search-group"><p class="small-label">SOURCE CONTEXT</p>${sources.map(source => `<button class="search-result" data-action="evidence" data-id="${source.id}">${sourceIcon(source.kind, 18)}<div><strong>${escapeHtml(source.title)}</strong><span>${escapeHtml(clientById(source.clientId).name)} · ${source.kind}</span></div>${icon('ArrowRight', 14)}</button>`).join('')}</div>` : ''}
    ${!clients.length && !actions.length && !sources.length ? empty('No matching context') : ''}`;
}

// 7. ACCESSIBLE SELECT MENUS AND DATE PICKER (LOCAL DOM ONLY)

function placePopover(element, trigger, requestedWidth, estimatedHeight) {
  const rect = trigger.getBoundingClientRect();
  const width = Math.min(requestedWidth, innerWidth - 24);
  const below = innerHeight - rect.bottom - 16;
  const above = rect.top - 16;
  const flip = below < estimatedHeight && above > below;
  const height = Math.max(40, Math.min(estimatedHeight, flip ? above : below));
  Object.assign(element.style, {
    left: `${Math.max(12, Math.min(rect.left, innerWidth - width - 12))}px`,
    top: `${flip ? Math.max(12, rect.top - height - 6) : rect.bottom + 6}px`,
    width: `${width}px`, maxHeight: `${height}px`
  });
}

function openSelect(trigger) {
  if (state.select?.trigger === trigger) { closeSelect(); return; }
  closeSelect(false);
  closeCalendar(false);
  const options = JSON.parse(trigger.dataset.options);
  const menu = document.createElement('div');
  menu.id = 'select-menu';
  menu.className = 'atelier-select-menu';
  menu.setAttribute('role', 'listbox');
  menu.setAttribute('aria-label', trigger.getAttribute('aria-label'));
  menu.innerHTML = options.map(([value, label], index) => `<div id="select-option-${index}" class="atelier-select-option ${value === trigger.dataset.value ? 'is-selected' : ''}" role="option" aria-selected="${value === trigger.dataset.value}" data-action="select-option" data-value="${escapeHtml(value)}" data-index="${index}">${escapeHtml(label)}${value === trigger.dataset.value ? icon('Check', 14) : ''}</div>`).join('');
  (trigger.closest('dialog') || document.body).append(menu);
  trigger.setAttribute('aria-expanded', 'true');
  trigger.setAttribute('aria-controls', menu.id);
  state.select = { trigger, menu, options, index: Math.max(0, options.findIndex(([value]) => value === trigger.dataset.value)) };
  placePopover(menu, trigger, Math.max(trigger.getBoundingClientRect().width, 220), Math.min(options.length * 40 + 12, 240));
  highlightSelectOption();
}

function highlightSelectOption() {
  const select = state.select;
  select.menu.querySelectorAll('[role="option"]').forEach((option, index) => option.classList.toggle('is-active', index === select.index));
  const active = select.menu.children[select.index];
  select.trigger.setAttribute('aria-activedescendant', active.id);
  active.scrollIntoView({ block: 'nearest' });
}

function closeSelect(restore = true) {
  if (!state.select) return;
  const { trigger, menu } = state.select;
  state.select = null;
  menu.remove();
  trigger.setAttribute('aria-expanded', 'false');
  trigger.removeAttribute('aria-controls');
  trigger.removeAttribute('aria-activedescendant');
  if (restore && trigger.isConnected) trigger.focus();
}

function chooseSelect(value) {
  const { trigger } = state.select;
  const key = trigger.dataset.select;
  closeSelect(false);
  if (key.includes(':')) {
    const [field, id] = key.split(':');
    updateAction(id, { [field]: value });
    state.dialog.element.querySelector(`[data-select="${key}"]`)?.focus();
  } else {
    state[key] = value;
    if (key === 'sort') {
      trigger.dataset.value = value;
      trigger.querySelector('span').textContent = JSON.parse(trigger.dataset.options).find(([id]) => id === value)[1];
      updatePortfolioCards();
      trigger.focus();
    } else {
      renderPage();
      document.querySelector(`[data-select="${key}"]`)?.focus();
    }
  }
}

function openCalendar(trigger) {
  closeSelect(false);
  closeCalendar(false);
  const action = state.actions.find(item => item.id === trigger.dataset.id);
  const date = new Date(`${action.due}T12:00:00Z`);
  const element = document.createElement('div');
  element.className = 'atelier-calendar';
  element.setAttribute('role', 'dialog');
  element.setAttribute('aria-label', 'Choose due date');
  (trigger.closest('dialog') || document.body).append(element);
  trigger.setAttribute('aria-expanded', 'true');
  state.calendar = { trigger, element, actionId: action.id, month: date.getUTCMonth(), year: date.getUTCFullYear() };
  renderCalendar();
}

function renderCalendar() {
  const calendar = state.calendar;
  const { month, year, element, trigger } = calendar;
  const action = state.actions.find(item => item.id === calendar.actionId);
  const today = new Date().toLocaleDateString('en-CA', { timeZone: 'Asia/Kolkata' });
  const count = new Date(Date.UTC(year, month + 1, 0)).getUTCDate();
  const leading = (new Date(Date.UTC(year, month, 1)).getUTCDay() + 6) % 7;
  const monthLabel = new Intl.DateTimeFormat('en-IN', { timeZone: 'UTC', month: 'long', year: 'numeric' }).format(new Date(Date.UTC(year, month, 1)));
  element.innerHTML = `<div class="atelier-calendar-title"><span>Due date</span><button class="icon-button" aria-label="Close calendar" data-action="close-calendar">${icon('X', 16)}</button></div>
    <div class="atelier-calendar-month"><button class="icon-button" aria-label="Previous month" data-action="calendar-month" data-value="-1">${icon('ChevronLeft', 16)}</button><strong aria-live="polite">${monthLabel}</strong><button class="icon-button" aria-label="Next month" data-action="calendar-month" data-value="1">${icon('ChevronRight', 16)}</button></div>
    <div class="atelier-calendar-grid">${['M', 'T', 'W', 'T', 'F', 'S', 'S'].map(day => `<span class="atelier-weekday">${day}</span>`).join('')}${'<span></span>'.repeat(leading)}
      ${Array.from({ length: count }, (_, index) => { const next = new Date(Date.UTC(year, month, index + 1, 12)).toISOString().slice(0, 10); return `<button data-day="${index + 1}" aria-label="${dateLabel(next, { day: 'numeric', month: 'short', year: 'numeric' })}" aria-pressed="${action.due === next}" class="${action.due === next ? 'selected' : next === today ? 'today' : ''}" data-action="calendar-day" data-value="${next}">${index + 1}</button>`; }).join('')}
    </div><div class="atelier-calendar-footer"><span>${dateLabel(action.due, { day: 'numeric', month: 'short', year: 'numeric' })}</span><button class="text-button" data-action="calendar-day" data-value="${today}">Today</button></div>`;
  placePopover(element, trigger, 320, element.getBoundingClientRect().height);
  (element.querySelector('[aria-pressed="true"]') || element.querySelector('[data-day]')).focus();
}

function closeCalendar(restore = true) {
  if (!state.calendar) return;
  const { trigger, element } = state.calendar;
  state.calendar = null;
  element.remove();
  trigger.setAttribute('aria-expanded', 'false');
  if (restore && trigger.isConnected) trigger.focus();
}

// 8. COPY / DOWNLOAD AND LOCAL NOTIFICATIONS

function clientBriefText(client) {
  return `# ${client.name} — Handover brief\n\nSample frontend record · ${DEMO_DATE}\n\n${client.story}\n\nCurrent focus: ${client.focus}\n\nOpen commitments:\n${clientActions(client).filter(isOutstanding).map(action => `- ${action.title} — ${action.owner}, due ${dateLabel(action.due)}`).join('\n')}\n\nRecord coverage: ${client.coverage}% (sample indicator). History starts ${client.since}.\n`;
}

function callBriefText(call) {
  const client = clientById(call.clientId);
  const evidence = call.sourceIds.map(id => { const source = sourceById(id); return `- ${source.kind}: ${source.title} — ${dateLabel(source.date)}, ${source.locator}\n  ${source.excerpt.replace(/\n/g, '\n  ')}`; }).join('\n\n');
  return `# ${client.name} — ${call.type}\n\nFrontend preview · fictional sample record\n${dateLabel(call.date)} · ${timeLabel(call.time)} IST · ${call.host}\n\n## Objective\n${call.objective}\n\n## Current position\n${call.context}\n\n## Suggested agenda\n${call.agenda.map((item, index) => `${index + 1}. ${item}`).join('\n')}\n\n## What we need from the client\n${call.needs.map(item => `- ${item}`).join('\n')}\n\n## Outstanding commitments\n${clientActions(client).filter(isOutstanding).map(action => `- ${action.title} — ${action.owner}, due ${dateLabel(action.due)} (${action.status})`).join('\n') || 'None'}\n\n## Evidence\n${evidence}\n`;
}

async function copyText(text, successMessage) {
  try {
    if (navigator.clipboard?.writeText) await navigator.clipboard.writeText(text);
    else {
      const field = document.createElement('textarea');
      field.value = text;
      field.style.cssText = 'position:fixed;left:-9999px;top:0';
      (state.dialog?.element || document.body).append(field);
      field.select();
      const copied = document.execCommand('copy');
      field.remove();
      if (!copied) throw new Error('Clipboard unavailable');
    }
    notify(successMessage);
  } catch {
    showDialog('Copy this brief', `<textarea class="export-copy-text" readonly aria-label="Brief text">${escapeHtml(text)}</textarea>`, 'HANDOVER & CONTINUITY', false);
    state.dialog.element.querySelector('textarea').select();
  }
}

function downloadText(text, name) {
  const url = URL.createObjectURL(new Blob([text], { type: 'text/markdown;charset=utf-8' }));
  const link = document.createElement('a');
  link.href = url;
  link.download = name;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
  notify('Sample call brief downloaded.');
}

function notify(message) {
  clearTimeout(state.toastTimer);
  document.getElementById('toast-host').innerHTML = `<div class="toast" role="status">${icon('CheckCircle2', 17)}<span>${escapeHtml(message)}</span><button class="icon-button" aria-label="Dismiss notification" data-action="dismiss-toast">${icon('X', 14)}</button></div>`;
  state.toastTimer = setTimeout(() => document.getElementById('toast-host').replaceChildren(), 4000);
}

// 9. EVENT DELEGATION — NO INLINE JAVASCRIPT ATTRIBUTES

function handleClick(event) {
  const button = event.target.closest('[data-action]');
  if (!button || button.disabled) return;
  const { action, id, value, tab } = button.dataset;
  if (action === 'skip') { event.preventDefault(); document.getElementById('main-content').focus(); return; }
  switch (action) {
    case 'portfolio': navigate('clients'); break;
    case 'client': openClient(id); break;
    case 'tab': {
      const previous = getRoute();
      if (previous.tab !== tab || previous.client?.id !== id) {
        state.historyMode = 'spine'; state.historyLane = 'all'; state.commitmentSide = 'all';
      }
      openClient(id, tab); break;
    }
    case 'call': openCall(id); break;
    case 'collapse': state.collapsed = !state.collapsed; syncSidebar(); break;
    case 'open-navigation': state.mobileOpen = true; syncSidebar(); document.querySelector('.mobile-close').focus(); break;
    case 'close-navigation': state.mobileOpen = false; syncSidebar(); document.querySelector('.mobile-menu').focus(); break;
    case 'portfolio-filter': state.filter = value; renderPage(); document.querySelector(`[data-action="portfolio-filter"][data-value="${value}"]`).focus(); break;
    case 'layout': state.layout = value; renderPage(); document.querySelector(`[data-action="layout"][data-value="${value}"]`).focus(); break;
    case 'clear-search': state.query = ''; document.querySelector('[data-input="portfolio-search"]').value = ''; updatePortfolioCards(); document.querySelector('[data-input="portfolio-search"]').focus(); break;
    case 'history-mode': state.historyMode = value; renderPage(); document.querySelector(`[data-action="history-mode"][data-value="${value}"]`).focus(); break;
    case 'commitment-side': state.commitmentSide = value; renderPage(); document.querySelector(`[data-action="commitment-side"][data-value="${value}"]`).focus(); break;
    case 'evidence': showEvidence(id); break;
    case 'sources': showSources(id); break;
    case 'invoice': showInvoice(id); break;
    case 'action-details': showAction(id); break;
    case 'toggle-action': { const item = state.actions.find(item => item.id === id); updateAction(id, { status: isOutstanding(item) ? 'Done' : 'Open' }); break; }
    case 'verify-action': updateAction(id, { status: 'Verified' }); notify('Verification recorded in the preview.'); break;
    case 'acknowledge': updateAction(id, { acknowledged: !state.actions.find(item => item.id === id).acknowledged }); break;
    case 'select': openSelect(button); break;
    case 'select-option': chooseSelect(value); break;
    case 'calendar': openCalendar(button); break;
    case 'close-calendar': closeCalendar(); break;
    case 'calendar-month': {
      const next = new Date(Date.UTC(state.calendar.year, state.calendar.month + Number(value), 1));
      state.calendar.year = next.getUTCFullYear(); state.calendar.month = next.getUTCMonth(); renderCalendar(); break;
    }
    case 'calendar-day': {
      const actionId = state.calendar.actionId;
      closeCalendar(false); updateAction(actionId, { due: value });
      state.dialog.element.querySelector('[data-action="calendar"]')?.focus(); break;
    }
    case 'close-dialog': closeDialog(); break;
    case 'alerts': showAlerts(); break;
    case 'about': showAbout(); break;
    case 'search': showSearch(); break;
    case 'copy-brief': copyText(clientBriefText(clientById(id)), 'Handover brief copied.'); break;
    case 'copy-call': copyText(callBriefText(CALLS.find(call => call.id === id)), 'Call brief copied to your clipboard.'); break;
    case 'download-call': { const call = CALLS.find(item => item.id === id); downloadText(callBriefText(call), `${call.clientId}-${call.date}-call-brief.md`); break; }
    case 'dismiss-toast': document.getElementById('toast-host').replaceChildren(); break;
  }
}

function handleInput(event) {
  if (event.target.dataset.input === 'portfolio-search') {
    state.query = event.target.value;
    updatePortfolioCards();
  }
  if (event.target.dataset.input === 'global-search') updateGlobalSearch(event.target.value);
}

function handleKeydown(event) {
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
    event.preventDefault(); state.dialog?.kind === 'search' ? closeDialog() : showSearch(); return;
  }
  if (state.select) {
    if (event.key === 'Escape') { event.preventDefault(); event.stopPropagation(); closeSelect(); return; }
    if (event.key === 'Tab') { closeSelect(false); return; }
    if (['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(event.key)) {
      event.preventDefault();
      const select = state.select;
      select.index = event.key === 'Home' ? 0 : event.key === 'End' ? select.options.length - 1 : (select.index + (event.key === 'ArrowDown' ? 1 : -1) + select.options.length) % select.options.length;
      highlightSelectOption(); return;
    }
    if (['Enter', ' '].includes(event.key)) { event.preventDefault(); chooseSelect(state.select.options[state.select.index][0]); return; }
    if (event.key.length === 1) {
      const index = state.select.options.findIndex(([, label]) => label.toLowerCase().startsWith(event.key.toLowerCase()));
      if (index >= 0) { state.select.index = index; highlightSelectOption(); } return;
    }
  } else if (event.target.matches('[role="combobox"]') && ['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(event.key)) {
    event.preventDefault(); openSelect(event.target); return;
  }
  if (state.calendar && state.calendar.element.contains(event.target)) {
    if (event.key === 'Escape') { event.preventDefault(); event.stopPropagation(); closeCalendar(); return; }
    const movement = { ArrowLeft: -1, ArrowRight: 1, ArrowUp: -7, ArrowDown: 7 }[event.key];
    if (movement !== undefined && event.target.dataset.day) {
      event.preventDefault(); state.calendar.element.querySelector(`[data-day="${Number(event.target.dataset.day) + movement}"]`)?.focus(); return;
    }
    if (event.key === 'Tab') trapFocus(event, state.calendar.element);
  }
  if (state.mobileOpen && matchMedia('(max-width: 700px)').matches) {
    if (event.key === 'Escape') { state.mobileOpen = false; syncSidebar(); document.querySelector('.mobile-menu').focus(); }
    if (event.key === 'Tab') trapFocus(event, document.querySelector('.sidebar'));
  }
}

function trapFocus(event, element) {
  const controls = [...element.querySelectorAll('button:not(:disabled), input, a[href], textarea')].filter(control => control.getClientRects().length);
  if (event.shiftKey && document.activeElement === controls[0]) { event.preventDefault(); controls.at(-1)?.focus(); }
  if (!event.shiftKey && document.activeElement === controls.at(-1)) { event.preventDefault(); controls[0]?.focus(); }
}

// 10. BLUE PERIMETER LIGHT — SAME SCALE, COLOURS AND 16 SECOND PERIOD

function startSidebarOrbit() {
  const element = document.querySelector('.sidebar-orbit');
  const canvas = element.querySelector('canvas');
  const context = canvas.getContext('2d');
  if (!context) return;
  const padding = 16, sampleCount = 1024;
  const motion = matchMedia('(prefers-reduced-motion: reduce)');
  let points = [], perimeter = 1, frame = 0, startedAt = null, width = 0, height = 0;
  function resize() {
    const rect = element.getBoundingClientRect(), ratio = Math.min(devicePixelRatio || 1, 2);
    width = rect.width + padding * 2; height = rect.height + padding * 2;
    canvas.width = Math.round(width * ratio); canvas.height = Math.round(height * ratio);
    context.setTransform(ratio, 0, 0, ratio, padding * ratio, padding * ratio);
    const corners = getComputedStyle(element.parentElement);
    const left = parseFloat(corners.borderTopLeftRadius) || 0, right = parseFloat(corners.borderTopRightRadius) || 0;
    const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    path.setAttribute('d', `M${left} 0 H${rect.width - right} Q${rect.width} 0 ${rect.width} ${right} V${rect.height - right} Q${rect.width} ${rect.height} ${rect.width - right} ${rect.height} H${left} Q0 ${rect.height} 0 ${rect.height - left} V${left} Q0 0 ${left} 0 Z`);
    perimeter = Math.max(path.getTotalLength(), 1);
    points = Array.from({ length: sampleCount }, (_, index) => { const point = path.getPointAtLength(index / sampleCount * perimeter); return { x: point.x, y: point.y }; });
  }
  function pointAt(distance) {
    const position = ((distance % perimeter + perimeter) % perimeter) / perimeter * sampleCount;
    const index = Math.floor(position), fraction = position - index;
    const first = points[index], second = points[(index + 1) % sampleCount];
    return { x: first.x + (second.x - first.x) * fraction, y: first.y + (second.y - first.y) * fraction };
  }
  function draw(timestamp) {
    context.clearRect(-padding, -padding, width, height);
    if (points.length && (!matchMedia('(max-width: 700px)').matches || state.mobileOpen)) {
      startedAt ??= timestamp;
      const distance = ((timestamp - startedAt) % 16000) / 16000 * perimeter;
      const head = pointAt(distance), tailLength = Math.min(135, perimeter * .07), tail = pointAt(distance - tailLength);
      const gradient = context.createLinearGradient(tail.x, tail.y, head.x, head.y);
      gradient.addColorStop(0, 'rgba(76,145,239,0)'); gradient.addColorStop(.45, 'rgba(76,145,239,.35)'); gradient.addColorStop(1, '#579aef');
      context.beginPath();
      for (let index = 0; index <= 48; index++) { const point = pointAt(distance - tailLength + index / 48 * tailLength); index ? context.lineTo(point.x, point.y) : context.moveTo(point.x, point.y); }
      context.strokeStyle = gradient; context.lineWidth = 2; context.lineCap = 'round'; context.stroke();
      context.shadowColor = '#4c91ef'; context.shadowBlur = 10; context.beginPath(); context.arc(head.x, head.y, 3.5, 0, Math.PI * 2);
      context.fillStyle = '#e4f3ff'; context.fill(); context.shadowBlur = 0; context.strokeStyle = '#579aef'; context.lineWidth = 1; context.stroke();
    }
    frame = requestAnimationFrame(draw);
  }
  function syncMotion() {
    cancelAnimationFrame(frame); context.clearRect(-padding, -padding, width, height);
    if (!motion.matches) frame = requestAnimationFrame(draw);
  }
  resize(); new ResizeObserver(resize).observe(element); motion.addEventListener('change', syncMotion); syncMotion();
}

// 11. INITIALISATION — THIS FILE ALSO OPENS DIRECTLY THROUGH file://

document.documentElement.dataset.variant = new URLSearchParams(location.search).get('variant') === 'gold' ? 'gold' : 'blue';
document.addEventListener('click', handleClick);
document.addEventListener('input', handleInput);
document.addEventListener('keydown', handleKeydown, true);
document.addEventListener('pointerdown', event => {
  if (state.select && !state.select.menu.contains(event.target) && !state.select.trigger.contains(event.target)) closeSelect(false);
  if (state.calendar && !state.calendar.element.contains(event.target) && !state.calendar.trigger.contains(event.target)) closeCalendar(false);
});
window.addEventListener('scroll', event => {
  if (state.select && !state.select.menu.contains(event.target)) closeSelect(false);
  if (state.calendar && !state.calendar.element.contains(event.target)) closeCalendar(false);
}, true);
window.addEventListener('resize', () => { closeSelect(false); closeCalendar(false); });
window.addEventListener('hashchange', () => {
  closeDialog(); closeSelect(false); closeCalendar(false); renderPage(); window.scrollTo({ top: 0, behavior: 'instant' });
});
renderShell();
if (!location.hash) location.hash = 'clients';
renderPage();
