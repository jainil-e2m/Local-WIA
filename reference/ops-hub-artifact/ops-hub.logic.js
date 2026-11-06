
class Component extends DCLogic {
  state = {
    screen: 'home', user: 'Whitney',
    inboxQueue: 'needs_whitney', emailId: 'e1', emailState: {}, voiceOpen: false, styleCue: null,
    meetingFilter: 'needs_review', meetingId: null,
    taskSel: {}, taskState: {}, packState: {}, actionsComplete: {}, completionApproved: {},
    slackIncluded: {}, recapIncluded: {},
    clientId: null, clientTab: 'overview', askQ: null,
    opsTab: 'team', nudgeState: {}, digestState: 'ready', invoiceId: null,
    invoiceState: {}, invalidState: {}, resentState: {},
    accTab: 'engagement', matchState: {}, rememberMap: {}, memberState: {}, reminderState: {},
    sessionState: {}, msgModal: null,
    contentId: 'c1', contentTab: 'reel', voiceModal: false, direction: {}, contentStage: {},
    paletteOpen: false, paletteQ: '', drawer: null, toast: null, askAnswer: null
  };

  componentDidMount() {
    this._key = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); this.setState(s => ({ paletteOpen: !s.paletteOpen, paletteQ: '' })); }
      if (e.key === 'Escape') this.setState({ paletteOpen: false, drawer: null, msgModal: null, voiceModal: false, invoiceId: null });
    };
    window.addEventListener('keydown', this._key);
  }
  componentWillUnmount() { window.removeEventListener('keydown', this._key); }

  /* ---------- helpers ---------- */
  toast(msg) {
    this.setState({ toast: msg });
    clearTimeout(this._t);
    this._t = setTimeout(() => this.setState({ toast: null }), 3200);
  }
  go(screen, extra) { this.setState(Object.assign({ screen: screen, paletteOpen: false, drawer: null }, extra || {})); }
  pill(tone) {
    const m = {
      neutral: ['#EEF1F6', '#5A6478', 'transparent'], blue: ['#EDF1FF', '#3F55D6', 'transparent'],
      green: ['#EAF7F0', '#1F8A5B', 'transparent'], amber: ['#FDF6E7', '#A9761A', 'transparent'],
      red: ['#FDECEC', '#C63F3F', 'transparent'], navy: ['#101747', '#FFFFFF', 'transparent'],
      slate: ['#EEF1F6', '#48526A', '#DDE2EE'], outline: ['#FFFFFF', '#5A6478', '#E7EAF1'],
      violet: ['#F3EEFE', '#6D3FD6', 'transparent']
    };
    const v = m[tone] || m.neutral;
    return 'display:inline-flex;align-items:center;gap:5px;padding:3px 8px;border-radius:6px;background:' + v[0] + ';color:' + v[1] + ';border:1px solid ' + v[2] + ';font-size:10.5px;font-weight:700;letter-spacing:.03em;white-space:nowrap';
  }
  srcMeta(s) {
    const m = {
      gmail: ['Gmail', '#D94C4C'], slack: ['Slack', '#7C3AED'], clickup: ['ClickUp', '#2E9E6B'],
      zoom: ['Zoom', '#2D8CFF'], fathom: ['Fathom', '#E07A3F'], drive: ['Drive', '#1F8A5B'],
      highlevel: ['HighLevel', '#3F55D6'], aihq: ['AI HQ', '#5874F7']
    };
    return m[s] || ['Source', '#8A93A6'];
  }
  srcChip(s, label) {
    const m = this.srcMeta(s);
    return {
      label: label || m[0], key: s,
      style: 'display:inline-flex;align-items:center;gap:5px;padding:3px 8px;border-radius:6px;background:#F6F8FD;border:1px solid #E7EAF1;color:' + m[1] + ';font-size:10.5px;font-weight:700;letter-spacing:.02em;white-space:nowrap',
      dot: 'width:5px;height:5px;border-radius:50%;flex:none;background:' + m[1]
    };
  }
  /* Native platform automation vs AI HQ automation — acceptance criterion */
  autoBadge(system) {
    if (!(this.props.showAutomationBadges ?? true)) return { label: '', style: 'display:none' };
    const map = {
      ai_hq: ['AI HQ Automation', 'blue'], clickup: ['Native Automation · ClickUp', 'slate'],
      highlevel: ['Native Automation · HighLevel', 'slate'], gmail: ['Native Automation · Gmail', 'slate'],
      human: ['Human decision', 'outline'], zoom: ['Native Automation · Zoom', 'slate'],
      ai_assisted: ['AI Assisted', 'violet'], validation: ['Production Validation', 'amber'],
      gmail_filter: ['Native Gmail Filter', 'slate'],
      native_highlevel_ai: ['Native event + AI HQ', 'slate']
    };
    const v = map[system] || map.ai_hq;
    return { label: v[0], style: this.pill(v[1]) };
  }
  accent() { return this.props.accent || '#5874F7'; }

  /* ---------- data ---------- */
  team = { Whitney: 'W', Gisselle: 'G', Carmen: 'C', Jacqueline: 'J', Danielle: 'D' };

  clients = [
    { id: 'bloom', name: 'Bloom Manor', contact: 'Sarah Mitchell', service: 'Elevate', status: 'active', opStatus: 'Landing-page handoff', lastComm: 'Today · Gmail', open: 7, overdue: 1, waitingOn: 'October gallery assets', waitingDays: 5, next: 'Sep 24 · Strategy call', attention: 'attention' },
    { id: 'rosewood', name: 'Rosewood Venue', contact: 'Dana Whitfield', service: 'Amplify', status: 'active', opStatus: 'Invoice + recap follow-up', lastComm: '2d ago · Gmail', open: 4, overdue: 1, waitingOn: 'Requested gallery assets', waitingDays: 12, next: 'Sep 9 · Check-in', attention: 'attention' },
    { id: 'everly', name: 'Everly Estate', contact: 'Nina Cole', service: 'Google Accelerator', status: 'active', opStatus: 'Engagement at risk', lastComm: '9d ago · Portal', open: 2, overdue: 0, waitingOn: '', waitingDays: 0, next: 'Sep 10 · Office Hours', attention: 'attention' },
    { id: 'willow', name: 'Willow & Pine', contact: 'Maya Stone', service: 'Meta Accelerator', status: 'active', opStatus: 'Re-engagement needed', lastComm: '24d ago · Portal', open: 1, overdue: 0, waitingOn: '', waitingDays: 0, next: 'Sep 10 · Office Hours', attention: 'attention' },
    { id: 'magnolia', name: 'Magnolia House', contact: 'Tessa Ruiz', service: 'Prospect · Elevate', status: 'prospect', opStatus: 'Proposal follow-up due', lastComm: 'Yesterday · Zoom', open: 1, overdue: 0, waitingOn: '', waitingDays: 0, next: 'Sep 5 · Proposal review', attention: 'attention' },
    { id: 'harbor', name: 'Harbor House', contact: 'Elena Park', service: 'Amplify', status: 'active', opStatus: 'Invoice 8 days overdue', lastComm: '4d ago · Gmail', open: 3, overdue: 0, waitingOn: '', waitingDays: 0, next: 'Sep 11 · Monthly call', attention: 'attention' }
  ];
  clientById(id) { return this.clients.find(c => c.id === id) || this.clients[0]; }

  emails = [
    { id: 'e1', queue: 'needs_whitney', sender: 'Sarah Mitchell', email: 'sarah@bloommanor.com', clientId: 'bloom', subject: 'Any update on the landing page?', age: '2h ago', classification: 'Client reply needed', priority: 'high', owner: 'Whitney', rec: 'AI Draft Ready — confirm delivery timing promised on the Sep 2 call.', trigger: 'Incoming Gmail', kind: 'draft' },
    { id: 'e2', queue: 'needs_whitney', sender: 'Dana Whitfield', email: 'dana@rosewoodvenue.com', clientId: 'rosewood', subject: 'Can we shift next month’s budget?', age: '5h ago', classification: 'Client decision needed', priority: 'high', owner: 'Whitney', rec: 'AI Draft Ready — Whitney approval required before any budget language goes out.', trigger: 'Incoming Gmail', kind: 'draft' },
    { id: 'e3', queue: 'needs_whitney', sender: 'AI HQ', email: 'ai@weddingindustryads.com', clientId: 'bloom', subject: 'Completion update ready — Bloom Manor strategy call', age: '1h ago', classification: 'Completion update', priority: 'medium', owner: 'Whitney', rec: 'All client-facing actions from the Sep 2 call are complete. Review the update draft.', trigger: 'Meeting action completion', kind: 'draft' },
    { id: 'e4', queue: 'ready_gisselle', sender: 'Elena Park', email: 'elena@harborhouse.com', clientId: 'harbor', subject: 'Question on this month’s reporting cadence', age: '1d ago', classification: 'Client reply needed', priority: 'medium', owner: 'Gisselle', rec: 'AI Draft Ready — operational answer only, cadence confirmed in ClickUp.', trigger: 'Incoming Gmail', kind: 'draft' },
    { id: 'e5', queue: 'ready_gisselle', sender: 'Nina Cole', email: 'nina@everlyestate.com', clientId: 'everly', subject: 'Re: Office Hours replay link', age: '3h ago', classification: 'Admin reply', priority: 'low', owner: 'Gisselle', rec: 'Draft ready — replay link pulled from Drive session folder.', trigger: 'Incoming Gmail', kind: 'draft' },
    { id: 'e6', queue: 'ready_gisselle', sender: 'Jacqueline', email: 'jacqueline@weddingindustryads.com', clientId: 'bloom', subject: 'Landing page QA is done', age: '4h ago', classification: 'Internal handoff', priority: 'medium', owner: 'Gisselle', rec: 'Draft ready — hand off to client with revised link.', trigger: 'Slack + Gmail', kind: 'draft' },
    { id: 'e7', queue: 'team_reply_due', sender: 'Dana Whitfield', email: 'dana@rosewoodvenue.com', clientId: 'rosewood', subject: 'Following up on my question from Thursday', age: '29 business hrs', classification: 'Reply SLA breach', priority: 'high', owner: 'Carmen', rec: 'No reply detected after 29 business hours. Preview internal nudge.', trigger: 'Reply SLA rule', kind: 'sla' },
    { id: 'e8', queue: 'team_reply_due', sender: 'Elena Park', email: 'elena@harborhouse.com', clientId: 'harbor', subject: 'Creative swap approval?', age: '26 business hrs', classification: 'Reply SLA at risk', priority: 'medium', owner: 'Jacqueline', rec: 'Approaching the 24–48 business-hour expectation. Nudge owner.', trigger: 'Reply SLA rule', kind: 'sla' },
    { id: 'e9', queue: 'waiting_client', sender: 'Bloom Manor', email: 'sarah@bloommanor.com', clientId: 'bloom', subject: 'October gallery assets — outstanding', age: 'Waiting 5 days', classification: 'Waiting on client', priority: 'medium', owner: 'Gisselle', rec: 'Follow up this week — new creative cannot be finalized without the gallery.', trigger: 'Waiting rule', kind: 'waiting' },
    { id: 'e10', queue: 'waiting_client', sender: 'Rosewood Venue', email: 'dana@rosewoodvenue.com', clientId: 'rosewood', subject: 'Requested gallery assets — outstanding', age: 'Waiting 12 days', classification: 'Waiting on client', priority: 'high', owner: 'Gisselle', rec: 'Follow up now — recap is complete, creative work is blocked.', trigger: 'Waiting rule', kind: 'waiting' },
    { id: 'e11', queue: 'sales_followup', sender: 'Tessa Ruiz', email: 'tessa@magnoliahouse.com', clientId: 'magnolia', subject: 'Great call — send over the details?', age: 'Yesterday', classification: 'Sales follow-up', priority: 'high', owner: 'Whitney', rec: 'Call outcome: interested in Elevate. Next step = send Elevate proposal.', trigger: 'Sales call', kind: 'sales' },
    { id: 'e12', queue: 'finance_followup', sender: 'Rosewood Venue', email: 'dana@rosewoodvenue.com', clientId: 'rosewood', subject: 'INV-204 · $1,850 · 5 days overdue', age: '5d overdue', classification: 'Invoice follow-up', priority: 'high', owner: 'Gisselle', rec: 'Standard HighLevel reminder already sent. Prepare a personal Gmail follow-up.', trigger: 'Invoice rule', kind: 'finance' },
    { id: 'e13', queue: 'no_action', sender: 'Canva', email: 'news@canva.com', clientId: '', subject: 'New in Canva: Brand Kit updates', age: '6h ago', classification: 'No action required', priority: 'low', owner: '—', rec: 'Read by Whitney. No reply, task or client impact detected.', trigger: 'Incoming Gmail', kind: 'noaction', dest: 'Tools / Canva' },
    { id: 'e14', queue: 'no_action', sender: 'Bloom Manor', email: 'sarah@bloommanor.com', clientId: 'bloom', subject: 'Thanks! — no reply needed', age: '1d ago', classification: 'Ambiguous', priority: 'low', owner: '—', rec: 'Likely no action, but the thread is client-facing. Keep in Inbox if unsure.', trigger: 'Incoming Gmail', kind: 'noaction', dest: 'Client / Bloom Manor', ambiguous: true }
  ];
  queues = [
    { id: 'needs_whitney', label: 'Needs Whitney' },
    { id: 'ready_gisselle', label: 'Ready for Gisselle' },
    { id: 'team_reply_due', label: 'Team Reply Due' },
    { id: 'waiting_client', label: 'Waiting on Client' },
    { id: 'sales_followup', label: 'Sales Follow-Up' },
    { id: 'finance_followup', label: 'Finance Follow-Up' },
    { id: 'no_action', label: 'No Action / File' }
  ];
  emailById(id) { return this.emails.find(e => e.id === id) || this.emails[0]; }
  emailStatus(id) { return this.state.emailState[id] || 'open'; }
  queueOpen(q) { return this.emails.filter(e => e.queue === q && this.emailStatus(e.id) === 'open').length; }

  /* ---------- derived counts ---------- */
  packIds = ['bloom-strategy', 'monday-team', 'magnolia-sales'];
  packStatus(id) { return this.state.packState[id] || 'needs_review'; }
  packsNeedingReview() { return this.packIds.filter(id => this.packStatus(id) === 'needs_review').length; }
  workshopStatus() { return this.state.reminderState['workshop'] || 'needs_review'; }
  unmatchedCount() {
    const ids = ['m1', 'm2', 'm3'];
    return ids.filter(i => !this.state.matchState[i]).length;
  }
  disengagedCount() {
    return ['everly', 'willow'].filter(id => (this.state.memberState[id] || 'flagged') === 'flagged').length;
  }
  teamRiskCount() {
    const unack = this.state.nudgeState['ack-jacqueline'] ? 0 : 1;
    const unack2 = this.state.nudgeState['ack-carmen'] ? 0 : 1;
    return 2 + unack + unack2;
  }
  invoiceOpenCount() { return ['INV-204', 'INV-198'].filter(i => (this.state.invoiceState[i] || 'overdue') !== 'handled').length; }
  invalidOpenCount() { return ['iq1', 'iq2'].filter(i => !this.state.invalidState[i]).length; }
  counts() {
    const nw = this.queueOpen('needs_whitney');
    const ws = this.workshopStatus() === 'needs_review' ? 1 : 0;
    const fin = this.invoiceOpenCount();
    return {
      needsReview: nw + this.packsNeedingReview() + ws + fin,
      needsReviewSub: nw + ' emails • ' + this.packsNeedingReview() + ' execution packs • ' + ws + ' workshop • ' + fin + ' finance',
      clientComm: this.queueOpen('waiting_client') + this.queueOpen('team_reply_due') + fin,
      clientCommSub: this.queueOpen('team_reply_due') + ' team replies • ' + this.queueOpen('waiting_client') + ' waiting clients • ' + fin + (fin === 1 ? ' personal invoice follow-up' : ' personal invoice follow-ups'),
      teamRisk: this.teamRiskCount(),
      accAttention: this.disengagedCount() + (this.unmatchedCount() > 0 ? 1 : 0),
      inboxOpen: this.emails.filter(e => this.emailStatus(e.id) === 'open').length,
      opsOpen: this.teamRiskCount() + this.invoiceOpenCount() + this.invalidOpenCount()
    };
  }

  /* ---------- shell ---------- */
  navDef = [
    { id: 'home', label: 'Home' }, { id: 'inbox', label: 'Inbox' }, { id: 'meetings', label: 'Meetings' },
    { id: 'ops', label: 'Ops Watch' }, { id: 'accelerators', label: 'Accelerators' }, { id: 'clients', label: 'Context' }
  ];
  navCount(id, c) {
    if (id === 'inbox') return c.inboxOpen;
    if (id === 'meetings') return this.packsNeedingReview();
    if (id === 'clients') return this.clients.filter(x => x.attention === 'attention').length;
    if (id === 'accelerators') return c.accAttention;
    if (id === 'ops') return c.opsOpen;
    if (id === 'home') return c.needsReview;
    if (id === 'content') return 3;
    return '';
  }
  navItem(def, c) {
    const active = this.state.screen === def.id;
    return {
      label: def.label, count: this.navCount(def.id, c),
      go: () => this.go(def.id, def.id === 'clients' ? { clientId: null } : (def.id === 'meetings' ? { meetingId: null } : {})),
      style: 'display:flex;align-items:center;gap:10px;padding:9px 11px;border-radius:10px;cursor:pointer;font-size:13px;font-weight:' + (active ? '700' : '500') + ';color:' + (active ? '#fff' : '#B9C3E8') + ';background:' + (active ? 'rgba(88,116,247,.28)' : 'transparent') + ';transition:background 140ms ease',
      dot: 'width:5px;height:5px;border-radius:50%;flex:none;background:' + (active ? this.accent() : 'rgba(185,195,232,.45)'),
      countStyle: 'font-family:JetBrains Mono,monospace;font-size:10.5px;font-weight:700;color:' + (active ? '#fff' : '#8E9BD6') + ';background:' + (active ? 'rgba(255,255,255,.14)' : 'transparent') + ';padding:2px 6px;border-radius:5px'
    };
  }
  pageMeta() {
    const m = {
      home: ['Operations Command Center', 'Attention · context · approval across WIA'],
      inbox: ['AI Inbox', 'Context-aware triage and drafts — nothing auto-sends'],
      meetings: ['Meeting-to-Execution', 'One reviewable execution pack per meeting'],
      clients: ['Context', 'Operational context for Inbox, Meetings and Ops Watch'],
      accelerators: ['Accelerator Operations', 'Attendance · engagement · reminders · sessions'],
      ops: ['Ops Watch', 'Exceptions and recurring routines'],
      content: ['Growth Signals', 'WIA’s own marketing — P1 secondary capability'],
      settings: ['Source Coverage & Automation Access', 'Demo environment only']
    };
    return m[this.state.screen] || m.home;
  }

  shellVals() {
    const c = this.counts();
    const meta = this.pageMeta();
    const user = this.state.user;
    return {
      navMain: this.navDef.map(d => this.navItem(d, c)),
      navSecondary: [this.navItem({ id: 'content', label: 'Growth Signals' }, c)],
      navSystem: [this.navItem({ id: 'settings', label: 'Settings' }, c)],
      sourceChipsMini: ['gmail', 'slack', 'clickup', 'zoom', 'fathom', 'drive', 'highlevel'].map(s => {
        const m = this.srcMeta(s);
        return { mono: m[0], title: m[0] + ' — connected (demo)', style: 'font-size:10px;font-weight:700;letter-spacing:.02em;padding:3px 7px;border-radius:6px;background:rgba(255,255,255,.08);color:#C3CDEF' };
      }),
      showDemoBadge: this.props.showDemoBadge ?? true,
      userName: user, userRole: user === 'Whitney' ? 'Founder · approver' : 'Operations lead',
      userInitial: this.team[user] || 'W',
      toggleUser: () => this.setState(s => ({ user: s.user === 'Whitney' ? 'Gisselle' : 'Whitney' })),
      pageTitle: meta[0], pageSubtitle: meta[1],
      openAlertCount: c.opsOpen,
      openPalette: () => this.setState({ paletteOpen: true, paletteQ: '' }),
      goOps: () => this.go('ops'), goSettings: () => this.go('settings'),
      goClients: () => this.go('clients', { clientId: null }), goContent: () => this.go('content'),
      goAccelerators: () => this.go('accelerators'), goInbox: () => this.go('inbox'),
      isHome: this.state.screen === 'home', isInbox: this.state.screen === 'inbox',
      isMeetings: this.state.screen === 'meetings', isClients: this.state.screen === 'clients',
      isAccelerators: this.state.screen === 'accelerators', isOps: this.state.screen === 'ops',
      isContent: this.state.screen === 'content', isSettings: this.state.screen === 'settings'
    };
  }

  /* ---------- home ---------- */
  homeVals() {
    const c = this.counts();
    const rail = (col) => 'position:absolute;left:0;top:0;bottom:0;width:3px;background:' + col;
    const kpis = [
      { label: 'Needs Review', value: c.needsReview, sub: c.needsReviewSub, col: this.accent(), trend: 'Approval queue', tone: 'blue', go: () => this.go('inbox', { inboxQueue: 'needs_whitney' }) },
      { label: 'Communication At Risk', value: c.clientComm, sub: c.clientCommSub, col: '#E0A020', trend: 'Gmail + rules', tone: 'amber', go: () => this.go('inbox', { inboxQueue: 'waiting_client' }) },
      { label: 'Team Actions At Risk', value: c.teamRisk, sub: '2 overdue • ' + (c.teamRisk - 2) + ' unacknowledged', col: '#D94C4C', trend: 'ClickUp + Slack', tone: 'red', go: () => this.go('ops', { opsTab: 'team' }) },
      { label: 'Accelerator Attention', value: c.accAttention, sub: this.disengagedCount() + ' disengaged • ' + (this.unmatchedCount() > 0 ? 1 : 0) + ' participant match', col: '#6D3FD6', trend: 'Zoom + HighLevel', tone: 'violet', go: () => this.go('accelerators', { accTab: 'engagement' }) }
    ];
    const tl = [
      { time: '08:05', label: 'Gmail changes synced', status: 'Completed', tone: 'green', icon: '✓' },
      { time: '08:07', label: 'HighLevel invalid-email workflow checked', status: 'Native', tone: 'green', icon: '✓', go: () => this.go('ops', { opsTab: 'routines' }) },
      { time: '08:10', label: '1 invalid email needs review', status: 'Needs review', tone: 'amber', icon: '⚠', go: () => this.go('ops', { opsTab: 'data' }) },
      { time: '08:12', label: 'Rosewood invoice became overdue', status: 'Exception', tone: 'amber', icon: '⚠', go: () => this.go('ops', { opsTab: 'finance', invoiceId: 'INV-204' }) },
      { time: '08:20', label: 'Fathom coverage — 1 user source unverified', status: 'Blocked', tone: 'red', icon: '!', go: () => this.go('settings') },
      { time: '09:30', label: 'Bloom Manor call processed', status: 'Completed', tone: 'green', icon: '✓', go: () => this.go('meetings', { meetingId: 'bloom-strategy' }) },
      { time: '09:34', label: 'Execution Pack needs review', status: 'Needs review', tone: 'blue', icon: '●', go: () => this.go('meetings', { meetingId: 'bloom-strategy' }) },
      { time: '10:00', label: 'Google Office Hours', status: 'Scheduled', tone: 'neutral', icon: '○', go: () => this.go('accelerators', { accTab: 'reminders' }) },
      { time: '14:30', label: 'Meta reminder scheduled in HighLevel', status: 'Scheduled', tone: 'neutral', icon: '○', go: () => this.go('accelerators', { accTab: 'reminders' }) },
      { time: '15:30', label: 'Meta Office Hours', status: 'Scheduled', tone: 'neutral', icon: '○', go: () => this.go('accelerators', { accTab: 'sessions' }) },
      { time: '17:00', label: 'Waiting-client aging check', status: 'Scheduled', tone: 'neutral', icon: '○', go: () => this.go('ops', { opsTab: 'waiting' }) }
    ];
    const glyphCol = { green: ['#EAF7F0', '#1F8A5B'], amber: ['#FDF6E7', '#A9761A'], red: ['#FDECEC', '#C63F3F'], blue: ['#EDF1FF', '#3F55D6'], neutral: ['#F1F3F8', '#8A93A6'] };
    const reviewDefs = [];
    if (this.packStatus('bloom-strategy') === 'needs_review') reviewDefs.push({
      kind: 'Execution Pack Ready', tone: 'blue', auto: 'ai_hq', time: 'Sep 2 call', title: 'Bloom Manor strategy call',
      detail: 'Meeting intelligence, ClickUp actions, Slack dispatch, client recap and Drive filing in one pack.',
      outputs: ['3 ClickUp tasks', '1 Slack dispatch', '1 Gmail recap', '4 Drive files'],
      cta: 'Review execution pack', go: () => this.go('meetings', { meetingId: 'bloom-strategy' })
    });
    if ((this.state.invoiceState['INV-204'] || 'overdue') !== 'handled') reviewDefs.push({
      kind: '5 days overdue', tone: 'red', auto: 'ai_hq', time: 'INV-204', title: 'Rosewood invoice',
      detail: 'Standard HighLevel reminder already sent. A personal Gmail follow-up is prepared.',
      outputs: ['$1,850 outstanding', 'Personal draft'], cta: 'Review personal reminder',
      go: () => this.go('ops', { opsTab: 'finance', invoiceId: 'INV-204' })
    });
    if (this.workshopStatus() === 'needs_review') reviewDefs.push({
      kind: 'Theme supplied by Whitney', tone: 'amber', auto: 'highlevel', time: 'Every other week', title: 'Workshop reminder',
      detail: 'Turning leads into venue tours. Copy drafted from Whitney’s theme — schedule in HighLevel once approved.',
      outputs: ['Community post', 'Dynamic copy'], cta: 'Review & schedule',
      go: () => this.go('accelerators', { accTab: 'reminders' })
    });
    if (this.emailStatus('e7') === 'open') reviewDefs.push({
      kind: 'Client email waiting 29 business hours', tone: 'red', auto: 'ai_hq', time: 'Rosewood Venue', title: 'Team reply at risk',
      detail: 'Carmen owns the thread and no reply has been detected. Internal nudge ready for review.',
      outputs: ['Owner: Carmen', 'Slack nudge'], cta: 'Review owner',
      go: () => this.go('inbox', { inboxQueue: 'team_reply_due', emailId: 'e7' })
    });
    const teamRows = [
      { initial: 'J', title: 'Bloom Manor testimonial creative', who: 'Jacqueline', meta: 'No Slack acknowledgement', status: 'Overdue 1 day', tone: 'red' },
      { initial: 'C', title: 'Google keyword review', who: 'Carmen', meta: 'Due today', status: this.state.nudgeState['ack-carmen'] ? 'Acknowledged' : 'Acknowledged', tone: 'green' },
      { initial: 'G', title: 'Rosewood recap', who: 'Gisselle', meta: 'Draft ready in Gmail', status: 'Draft ready', tone: 'blue' }
    ];
    const accRows = [
      { name: 'Everly Estate', program: 'Google', meta: 'Last attended Aug 20', issue: '2 consecutive Google Office Hours misses', suggestion: 'Portal DM recommended · sent manually by WIA', cta: 'Open engagement', tone: 'amber', go: () => this.go('accelerators', { accTab: 'engagement' }) },
      { name: 'Willow & Pine', program: 'Meta', meta: 'Last attended Aug 6', issue: '4 consecutive Meta Office Hours misses', suggestion: 'Personal email recommended', cta: 'Open engagement', tone: 'red', go: () => this.go('accelerators', { accTab: 'engagement' }) },
      { name: 'Attendance matching', program: 'Zoom', meta: 'Meta Office Hours · Sep 3', issue: this.unmatchedCount() + ' Zoom attendees need identity matching', suggestion: 'Confirm identity before attendance counts', cta: 'Review unmatched', tone: 'blue', go: () => this.go('accelerators', { accTab: 'attendance' }) }
    ];
    const dotCol = { amber: '#E0A020', red: '#D94C4C', blue: this.accent() };
    const cov = [
      ['gmail', 'Gmail', 'Covered', 'green'], ['slack', 'Slack', '8 channels', 'amber'],
      ['clickup', 'ClickUp', 'Covered', 'green'], ['zoom', 'Zoom', 'Covered', 'green'],
      ['fathom', 'Fathom', 'Partial · 3 users', 'amber'], ['drive', 'Drive', 'Covered', 'green'],
      ['highlevel', 'HighLevel', 'Covered', 'green']
    ];
    return {
      greeting: 'Good morning, ' + this.state.user,
      coverageStrip: cov.map(s => ({
        name: s[1], state: s[2], pill: this.pill(s[3] === 'green' ? 'green' : 'amber'),
        dot: 'width:6px;height:6px;border-radius:50%;flex:none;background:' + this.srcMeta(s[0])[1]
      })),
      kpis: kpis.map(k => ({
        label: k.label, value: k.value, sub: k.sub, trend: k.trend, go: k.go, rail: rail(k.col),
        trendStyle: this.pill(k.tone)
      })),
      queueBadge: this.autoBadge('ai_hq').style, queueBadgeLabel: this.autoBadge('ai_hq').label,
      queueRows: tl.map(t => ({
        time: t.time, label: t.label, status: t.status, icon: t.icon,
        go: t.go || (() => { }),
        wrap: 'display:flex;align-items:center;gap:11px;padding:9px 6px;border-top:1px solid #F0F2F8;cursor:' + (t.go ? 'pointer' : 'default') + ';border-radius:8px;transition:background 140ms ease',
        glyph: 'width:20px;height:20px;border-radius:6px;flex:none;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:800;background:' + glyphCol[t.tone][0] + ';color:' + glyphCol[t.tone][1],
        pill: this.pill(t.tone === 'neutral' ? 'outline' : t.tone)
      })),
      reviewCards: reviewDefs.map(r => ({
        kind: r.kind, title: r.title, detail: r.detail, cta: r.cta, time: r.time, go: r.go,
        kindPill: this.pill(r.tone), auto: this.autoBadge(r.auto).label, autoPill: this.autoBadge(r.auto).style,
        outputs: r.outputs.map(o => ({ label: o, style: this.pill('outline') }))
      })),
      pulse: {
        overdue: 2, unack: this.teamRiskCount() - 2,
        overduePill: this.pill('red'), unackPill: this.pill('amber')
      },
      teamRows: teamRows.map(t => ({ initial: t.initial, title: t.title, who: t.who, meta: t.meta, status: t.status, statusPill: this.pill(t.tone) })),
      accPulse: accRows.map(a => ({
        name: a.name, program: a.program, meta: a.meta, issue: a.issue, suggestion: a.suggestion, cta: a.cta, go: a.go,
        wrap: 'border:1px solid #E7EAF1;border-radius:14px;padding:14px 15px;cursor:pointer;background:#fff',
        dot: 'width:8px;height:8px;border-radius:50%;flex:none;background:' + dotCol[a.tone],
        programPill: this.pill('outline')
      }))
    };
  }

  renderVals() {
    return Object.assign({}, this.shellVals(), this.homeVals(), this.moreVals());
  }
  moreVals() {
    const out = {};
    ['inboxVals', 'meetingVals', 'clientVals', 'accVals', 'opsVals', 'contentVals', 'settingsVals', 'globalVals'].forEach(k => {
      if (typeof this[k] === 'function') Object.assign(out, this[k]());
    });
    return out;
  }

  /* ---------- inbox ---------- */
  drafts = {
    e1: 'Hi Sarah,\n\nAbsolutely — the team is finishing the final QA now, and we’re expecting to have the updated page ready for you tomorrow.\n\nWe’ll send the revised link over as soon as those checks are complete.\n\nThank you!',
    e2: 'Hi Dana,\n\nHappy to look at shifting next month’s budget. Before we move anything, I want to confirm the split you have in mind so the current tests aren’t interrupted mid-flight.\n\nCan you confirm the amount you’d like moved? I’ll come back with the operational impact today.\n\nThanks!',
    e3: 'Hi Sarah,\n\nQuick update — everything we committed to on our last strategy call has now been completed.\n\n✓ Revised landing page\n✓ Keyword review\n✓ Testimonial creative update\n\nHere’s the updated page:\n[link]\n\nThanks!',
    e4: 'Hi Elena,\n\nYour reporting cadence is unchanged — the monthly summary goes out on the first business day, and we review it together on our monthly call.\n\nI’ve noted your question and nothing needs to change on your side.\n\nThank you!',
    e5: 'Hi Nina,\n\nHere’s the replay from last week’s Google Office Hours — it’s filed in your member portal as well.\n\n[Watch recording]\n\nLet me know if anything didn’t come through.',
    e6: 'Hi Sarah,\n\nGood news — final QA on the revised page is complete. Here’s the updated link for your review:\n\n[link]\n\nIf anything looks off, send it back and we’ll adjust today.\n\nThank you!',
    e9: 'Hi Sarah,\n\nOne quick follow-up — we’re still waiting on the October gallery assets. Once those land we can finalize the new creative set.\n\nCould you send them over this week?\n\nThank you!',
    e10: 'Hi Dana,\n\nFollowing up on the gallery assets we requested — the recap from our last call is complete on our side, and the creative work is waiting on those images.\n\nAny chance you can send them across today or tomorrow?\n\nThank you!',
    e11: 'Hi Tessa,\n\nGreat speaking with you — as promised, here’s the Elevate proposal covering the scope we discussed.\n\n[Elevate proposal]\n\nHappy to walk through it live if that’s easier. Just let me know a time that works.\n\nThank you!',
    e12: 'Hi Dana,\n\nJust a quick personal note — invoice INV-204 ($1,850) is showing as unpaid and is now 5 days past due.\n\nIf it’s easier, here’s the payment link:\n[Open invoice]\n\nIf it’s already scheduled, ignore me entirely — just wanted to make sure it hadn’t slipped through.\n\nThank you!'
  };
  nudges = {
    e7: 'Hey Carmen — Rosewood asked a question on Thursday and I don’t see a reply on the thread yet.\n\nIt’s at 29 business hours. Can you take it today, or should I hand it to Whitney?',
    e8: 'Hey Jacqueline — Harbor House is waiting on creative-swap approval (26 business hours).\n\nCan you confirm on the thread today?'
  };
  contextFor(e) {
    const c = e.clientId ? this.clientById(e.clientId) : null;
    if (e.id === 'e1' || e.id === 'e6') return [
      { s: 'gmail', label: 'Current client thread', excerpt: 'Sarah Mitchell · 3 messages · last reply from Whitney Sep 2', time: '2h ago' },
      { s: 'slack', label: '#client-bloom-manor', excerpt: 'Jacqueline: Final QA is done; handing off tomorrow.', time: '4h ago' },
      { s: 'clickup', label: 'Landing Page QA · In Progress', excerpt: 'Owner Jacqueline · Due tomorrow', time: 'Yesterday' },
      { s: 'zoom', label: 'Sep 2 Strategy Call · 24:18', excerpt: 'Whitney told the client the revised page would be delivered this week.', time: 'Sep 2' },
      { s: 'drive', label: 'Latest landing-page review file', excerpt: 'Clients / Bloom Manor / Meetings / 2026-09-02 Strategy', time: 'Sep 2' }
    ];
    if (e.id === 'e3') return [
      { s: 'clickup', label: '4 / 4 client-facing actions complete', excerpt: 'LP handoff · keyword review · testimonial creative · recap sent', time: 'Today' },
      { s: 'slack', label: '#client-bloom-manor', excerpt: 'Jacqueline reacted 👀 then marked complete', time: 'Today' },
      { s: 'zoom', label: 'Sep 2 Strategy Call', excerpt: 'Commitments made on the call are the source of this update.', time: 'Sep 2' },
      { s: 'gmail', label: 'Last client email', excerpt: 'Whitney · Sep 2 · recap of the strategy call', time: 'Sep 2' }
    ];
    if (e.kind === 'sla') return [
      { s: 'gmail', label: 'Client thread — no reply detected', excerpt: e.sender + ' asked a question ' + e.age + ' ago', time: e.age },
      { s: 'slack', label: 'Owner channel', excerpt: 'No acknowledgement from ' + e.owner + ' on the thread', time: 'Today' },
      { s: 'clickup', label: 'No task created for this reply', excerpt: 'Reply SLA expectation: 24–48 business hours', time: '—' }
    ];
    if (e.kind === 'waiting') return [
      { s: 'gmail', label: 'Original request', excerpt: 'Assets requested by Gisselle · no client reply since', time: e.age },
      { s: 'clickup', label: (c ? c.name : '') + ' creative build · Blocked', excerpt: 'Cannot progress without client assets', time: 'Today' },
      { s: 'slack', label: '#client-' + (c ? c.id : 'account'), excerpt: 'Team confirmed everything else on the recap is complete', time: 'Yesterday' },
      { s: 'zoom', label: 'Last call commitment', excerpt: 'Client agreed to send the gallery after the call', time: 'Sep 2' }
    ];
    if (e.kind === 'sales') return [
      { s: 'zoom', label: 'Sep 3 sales call · 34 min', excerpt: 'Prospect asked about Elevate scope and timeline', time: 'Yesterday' },
      { s: 'highlevel', label: 'Contact record', excerpt: 'Magnolia House · Tessa Ruiz · lead source: referral', time: 'Aug 24' },
      { s: 'clickup', label: 'Send Elevate proposal', excerpt: 'Owner Whitney · Due today', time: 'Today' }
    ];
    if (e.kind === 'finance') return [
      { s: 'highlevel', label: 'INV-204 · unpaid', excerpt: 'Due Aug 30 · amount due $1,850 · not void', time: '5d overdue' },
      { s: 'highlevel', label: 'Standard reminder already sent', excerpt: 'Automated invoice reminder · Sep 1', time: 'Sep 1' },
      { s: 'gmail', label: 'Last client email', excerpt: 'Dana Whitfield · Sep 1 · unrelated thread', time: 'Sep 2' }
    ];
    if (e.kind === 'noaction') return [
      { s: 'gmail', label: 'Message read, no reply detected', excerpt: e.rec, time: e.age },
      { s: 'clickup', label: 'No linked task', excerpt: 'No action item references this message', time: '—' },
      { s: 'slack', label: 'No related discussion', excerpt: 'Nothing referencing this thread in the last 7 days', time: '—' }
    ];
    return [
      { s: 'gmail', label: 'Current thread', excerpt: e.subject, time: e.age },
      { s: 'slack', label: 'Related channel context', excerpt: 'Team discussion linked to ' + (c ? c.name : 'this thread'), time: 'Today' },
      { s: 'clickup', label: 'Linked task', excerpt: (c ? c.opStatus : 'Operational task') + ' · In progress', time: 'Yesterday' },
      { s: 'drive', label: 'Latest filed asset', excerpt: 'Session and meeting files for ' + (c ? c.name : 'the account'), time: 'Sep 2' }
    ];
  }
  primaryFor(e) {
    const st = this.emailStatus(e.id);
    if (st !== 'open') {
      const done = { approved: 'Draft created in Gmail', filed: 'Archived & filed', kept: 'Kept in Inbox', nudged: 'Nudge posted to Slack', snoozed: 'Snoozed 4 hours' };
      return { label: done[st] || 'Handled', style: this.pill('green') + ';padding:10px 16px;font-size:12.5px;border-radius:10px', fn: () => { } };
    }
    const btn = 'padding:10px 16px;border-radius:10px;background:#101747;color:#fff;font-size:12.5px;font-weight:700;cursor:pointer';
    const map = {
      draft: ['Approve draft', 'approved', 'Draft created in Gmail — simulated'],
      waiting: ['Draft follow-up', 'approved', 'Follow-up draft created in Gmail — simulated'],
      sla: ['Approve internal nudge', 'nudged', 'Internal nudge posted to Slack — simulated'],
      sales: ['Approve proposal draft', 'approved', 'Elevate proposal draft created in Gmail — simulated'],
      finance: ['Create personal draft', 'approved', 'Personal invoice reminder drafted in Gmail — simulated'],
      noaction: ['Archive & file', 'filed', 'Archived and filed — simulated']
    };
    const v = map[e.kind] || map.draft;
    return {
      label: v[0], style: btn,
      fn: () => {
        const es = Object.assign({}, this.state.emailState); es[e.id] = v[1];
        const inv = Object.assign({}, this.state.invoiceState);
        if (e.kind === 'finance') inv['INV-204'] = 'draft_ready';
        this.setState({ emailState: es, invoiceState: inv });
        this.toast(v[2]);
      }
    };
  }
  inboxBadgeKey(e) {
    if (e.kind === 'noaction') return 'gmail_filter';
    if (e.kind === 'sla' || e.kind === 'waiting') return 'ai_hq';
    if (e.kind === 'finance') return 'native_highlevel_ai';
    return 'ai_assisted';
  }
  inboxVals() {
    const st = this.state;
    const rows = this.emails.filter(e => e.queue === st.inboxQueue);
    const sel = this.emailById(rows.some(r => r.id === st.emailId) ? st.emailId : (rows[0] ? rows[0].id : 'e1'));
    const selClient = sel.clientId ? this.clientById(sel.clientId) : null;
    const prim = this.primaryFor(sel);
    const statusLabels = { open: 'Open', approved: 'Draft ready in Gmail', filed: 'Filed', kept: 'Kept in Inbox', nudged: 'Nudge posted', snoozed: 'Snoozed' };
    const stt = this.emailStatus(sel.id);
    return {
      inboxQueues: this.queues.map(q => {
        const active = q.id === st.inboxQueue;
        return {
          label: q.label, count: this.emails.filter(e => e.queue === q.id).length,
          go: () => this.setState({ inboxQueue: q.id, emailId: (this.emails.find(e => e.queue === q.id) || {}).id }),
          style: 'display:flex;align-items:center;gap:8px;padding:9px 10px;border-radius:10px;cursor:pointer;font-size:12.5px;font-weight:' + (active ? '700' : '500') + ';color:' + (active ? '#101747' : '#5A6478') + ';background:' + (active ? '#EDF1FF' : 'transparent') + ';transition:background 140ms ease',
          countStyle: 'font-family:JetBrains Mono,monospace;font-size:10.5px;font-weight:700;color:' + (active ? '#3F55D6' : '#B3BAC9')
        };
      }),
      inboxQueueLabel: (this.queues.find(q => q.id === st.inboxQueue) || {}).label,
      inboxCount: rows.length,
      inboxRows: rows.map(e => {
        const active = e.id === sel.id;
        const c = e.clientId ? this.clientById(e.clientId) : null;
        return {
          sender: e.sender, client: c ? c.name : 'Internal', subject: e.subject, age: e.age,
          classification: e.classification, priority: e.priority === 'high' ? 'High' : (e.priority === 'medium' ? 'Medium' : 'Low'),
          recShort: (e.rec || '').split('—')[0].trim(), owner: e.owner, trigger: e.trigger,
          go: () => this.setState({ emailId: e.id }),
          wrap: 'border:1px solid ' + (active ? '#5874F7' : '#EDEFF6') + ';border-radius:13px;padding:13px 14px;cursor:pointer;background:' + (active ? '#F8FAFF' : '#fff') + ';box-shadow:' + (active ? '0 0 0 3px rgba(88,116,247,.1)' : 'none') + ';transition:border-color 140ms ease',
          classPill: this.pill(e.kind === 'noaction' ? 'neutral' : 'blue'),
          priorityPill: this.pill(e.priority === 'high' ? 'red' : (e.priority === 'medium' ? 'amber' : 'outline'))
        };
      }),
      selSubject: sel.subject, selSender: sel.sender, selEmail: sel.email,
      selClient: selClient ? selClient.name + ' · ' + selClient.service : 'Internal',
      selClassification: sel.classification, selPriority: sel.priority === 'high' ? 'High priority' : (sel.priority === 'medium' ? 'Medium' : 'Low'),
      selClassPill: this.pill('blue'), selPriorityPill: this.pill(sel.priority === 'high' ? 'red' : (sel.priority === 'medium' ? 'amber' : 'outline')),
      selStatus: statusLabels[stt], selStatusPill: this.pill(stt === 'open' ? 'outline' : 'green'),
      selOwner: sel.owner, selAge: sel.age, selTrigger: sel.trigger, selRec: sel.rec,
      selAutoLabel: this.autoBadge(this.inboxBadgeKey(sel)).label,
      selAutoPill: this.autoBadge(this.inboxBadgeKey(sel)).style,
      selContext: this.contextFor(sel).map(x => {
        const chip = this.srcChip(x.s);
        return {
          source: chip.label, chip: chip.style, dot: chip.dot, label: x.label, excerpt: x.excerpt, time: x.time,
          go: () => this.setState({ drawer: { title: chip.label + ' — evidence', source: x.s, label: x.label, excerpt: x.excerpt, time: x.time, client: selClient ? selClient.name : 'Internal' } })
        };
      }),
      selShowDraft: !!this.drafts[sel.id],
      selDraft: this.drafts[sel.id] || '',
      selDraftDest: sel.kind === 'sla' ? 'Slack · internal' : 'Gmail draft · never auto-sent',
      selShowWaiting: sel.kind === 'waiting', selShowSla: sel.kind === 'sla',
      selShowSales: sel.kind === 'sales', selShowFinance: sel.kind === 'finance', selShowNoAction: sel.kind === 'noaction',
      selWaitAge: sel.age, selWaitOutstanding: sel.subject.replace(' — outstanding', ''),
      selWaitImpact: sel.clientId === 'bloom' ? 'New creative cannot be finalized' : 'Client recap complete · creative work waiting',
      selWaitRec: sel.clientId === 'bloom' ? 'Follow up this week' : 'Follow up now',
      selNudgePreview: this.nudges[sel.id] || '',
      selNoActionReason: sel.rec, selNoActionDest: sel.dest || 'Tools',
      selPrimary: prim.fn, selPrimaryLabel: prim.label, selPrimaryStyle: prim.style,
      selKeep: () => { const es = Object.assign({}, this.state.emailState); es[sel.id] = 'kept'; this.setState({ emailState: es }); this.toast('Kept in Inbox — AI HQ will not archive it'); },
      selSnooze: () => { const es = Object.assign({}, this.state.emailState); es[sel.id] = 'snoozed'; this.setState({ emailState: es }); this.toast('Snoozed for 4 hours'); },
      selEdit: () => this.toast('Draft opened for editing — demo'),
      selRegen: () => this.toast('Regenerated with Whitney’s voice preferences — demo'),
      goOpsFinance: () => this.go('ops', { opsTab: 'finance', invoiceId: 'INV-204' }),
      voiceOpen: st.voiceOpen, voiceToggleLabel: st.voiceOpen ? 'Hide' : 'Show',
      toggleVoice: () => this.setState(s => ({ voiceOpen: !s.voiceOpen })),
      voiceLabelPill: this.pill('violet'), voiceConceptPill: this.pill('outline'),
      voicePrefer: [
        'warm but concise', 'answer the direct question first', 'no generic “just checking in”',
        'bullets for 3+ action items', 'sign off as Whitney'
      ].concat(st.styleCue === 'accepted' ? ['prefer “quick update” over “following up”'] : []).map(l => ({ label: l })),
      cueButtons: (st.styleCue ? [{
        label: st.styleCue === 'accepted' ? 'Cue accepted ✓' : 'Cue ignored',
        style: 'padding:9px 14px;border-radius:10px;font-size:12px;font-weight:700;background:#EAF7F0;color:#1F8A5B', go: () => { }
      }] : [
        { label: 'Accept cue', style: 'padding:9px 14px;border-radius:10px;font-size:12px;font-weight:700;cursor:pointer;background:#101747;color:#fff', go: () => { this.setState({ styleCue: 'accepted' }); this.toast('Style cue accepted — added to the active cue set'); } },
        { label: 'Ignore', style: 'padding:9px 14px;border-radius:10px;font-size:12px;font-weight:700;cursor:pointer;background:#EDEFF6;color:#5A6478', go: () => { this.setState({ styleCue: 'ignored' }); this.toast('Cue ignored — no change to the style profile'); } }
      ])
    };
  }

  /* ---------- meetings ---------- */
  meetings = [
    {
      id: 'bloom-strategy', title: 'Bloom Manor — Monthly Strategy', type: 'client', source: 'zoom', clientId: 'bloom',
      date: 'Sep 2', duration: '58 min', host: 'Whitney', channel: '#client-bloom-manor',
      decisions: ['Testimonial creative test approved', 'Revised page needs client handoff', 'Keyword exclusions to be reviewed before next flight', 'Recap to be sent same day'],
      clientCommitments: ['Send October gallery Friday'],
      wiaCommitments: ['Deliver revised page', 'Review keyword exclusions', 'Update creative', 'Send recap'],
      risks: ['Client gallery still outstanding'],
      tasks: [
        { id: 't1', title: 'Complete landing-page handoff', owner: 'Jacqueline', due: 'Tomorrow', ts: '24:18' },
        { id: 't2', title: 'Review keyword exclusions', owner: 'Carmen', due: 'Friday', ts: '31:05' },
        { id: 't3', title: 'Send client recap', owner: 'Gisselle', due: 'Today', ts: '42:18' }
      ],
      moments: [
        { ts: '24:18', tag: 'Commitment', text: '“We’ll have the revised page over to you this week.”' },
        { ts: '31:05', tag: 'Decision', text: '“Let’s pull the broad keywords before the next flight.”' },
        { ts: '31:42', tag: 'Client win', text: '“We’ve had more venue tours this month than any month this year.”' },
        { ts: '42:18', tag: 'Action', text: '“Gisselle will send the recap today.”' }
      ],
      files: [['Recording.mp4', 'recording'], ['Transcript.txt', 'transcript'], ['Summary.md', 'summary'], ['Action Items.md', 'action items']],
      fileDest: 'Drive / Clients / Bloom Manor / Meetings / 2026-09-02 Strategy'
    },
    {
      id: 'monday-team', title: 'Monday Team Meeting', type: 'internal', source: 'fathom', clientId: '',
      date: 'Aug 31', duration: '42 min', host: 'Gisselle', channel: '#team-ops',
      decisions: ['Weekly overdue review moves to Monday', 'Harbor House creative swap approved internally'],
      clientCommitments: [],
      wiaCommitments: ['Clear overdue client-facing tasks', 'Confirm Office Hours host coverage', 'Ship Rosewood recap'],
      risks: ['Three overdue tasks are client-facing'],
      tasks: [
        { id: 'i1', title: 'Clear 3 overdue Bloom Manor tasks', owner: 'Jacqueline', due: 'Wednesday', ts: '06:12' },
        { id: 'i2', title: 'Rebuild Google keyword exclusion list', owner: 'Carmen', due: 'Thursday', ts: '11:40' },
        { id: 'i3', title: 'Post Rosewood recap + invoice note', owner: 'Gisselle', due: 'Today', ts: '18:22' },
        { id: 'i4', title: 'Confirm Office Hours host coverage', owner: 'Gisselle', due: 'Tomorrow', ts: '21:05' },
        { id: 'i5', title: 'Approve Harbor House creative swap', owner: 'Whitney', due: 'Today', ts: '26:31' },
        { id: 'i6', title: 'Update Meta audience exclusions', owner: 'Carmen', due: 'Friday', ts: '29:48' },
        { id: 'i7', title: 'Refresh testimonial creative brief in ClickUp', owner: 'Jacqueline', due: 'Friday', ts: '33:02' }
      ],
      moments: [
        { ts: '06:12', tag: 'Risk', text: '“Three of the overdue ones are client-facing.”' },
        { ts: '18:22', tag: 'Action', text: '“I’ll get the Rosewood recap out today.”' },
        { ts: '26:31', tag: 'Decision', text: '“Approve the swap, but Whitney signs off.”' }
      ],
      files: [['Recording.mp4', 'recording'], ['Transcript.txt', 'transcript'], ['Summary.md', 'summary'], ['Action Items.md', 'action items']],
      fileDest: 'Drive / Internal / Team Meetings / 2026-08-31 Monday'
    },
    {
      id: 'magnolia-sales', title: 'Magnolia House — Discovery Call', type: 'sales', source: 'zoom', clientId: 'magnolia',
      date: 'Sep 3', duration: '34 min', host: 'Whitney', channel: '#sales',
      decisions: ['Strong fit for Elevate', 'Proposal to be sent before Friday'],
      clientCommitments: ['Confirm internal budget window'],
      wiaCommitments: ['Send Elevate proposal', 'Share venue-tour benchmark example'],
      risks: ['Prospect comparing two agencies'],
      tasks: [
        { id: 's1', title: 'Send Elevate proposal', owner: 'Whitney', due: 'Today', ts: '19:44' },
        { id: 's2', title: 'Log prospect in HighLevel pipeline', owner: 'Gisselle', due: 'Today', ts: '30:10' }
      ],
      moments: [
        { ts: '19:44', tag: 'Buying signal', text: '“Elevate sounds like the right level for us.”' },
        { ts: '30:10', tag: 'Next step', text: '“Send the proposal and we’ll review Thursday.”' }
      ],
      files: [['Recording.mp4', 'recording'], ['Transcript.txt', 'transcript'], ['Summary.md', 'summary']],
      fileDest: 'Drive / Sales / Magnolia House / 2026-09-03 Discovery'
    },
    {
      id: 'rosewood-checkin', title: 'Rosewood Venue — Monthly Check-in', type: 'client', source: 'fathom', clientId: 'rosewood',
      date: 'Aug 25', duration: '46 min', host: 'Gisselle', channel: '#client-rosewood',
      decisions: ['Recap sent and acknowledged', 'Gallery assets requested again'],
      clientCommitments: ['Send requested gallery assets'],
      wiaCommitments: ['Send recap', 'Hold creative until assets arrive'],
      risks: ['Assets outstanding 12 days'],
      tasks: [
        { id: 'r1', title: 'Send check-in recap', owner: 'Gisselle', due: 'Aug 25', ts: '38:02' },
        { id: 'r2', title: 'Request gallery assets again', owner: 'Gisselle', due: 'Aug 26', ts: '40:15' }
      ],
      moments: [{ ts: '38:02', tag: 'Commitment', text: '“Recap goes out right after this call.”' }],
      files: [['Recording.mp4', 'recording'], ['Transcript.txt', 'transcript'], ['Summary.md', 'summary'], ['Action Items.md', 'action items']],
      fileDest: 'Drive / Clients / Rosewood Venue / Meetings / 2026-08-25 Check-in', processed: true
    },
    {
      id: 'meta-office-hours', title: 'Meta Ads Office Hours — Sep 3', type: 'office_hours', source: 'zoom', clientId: '',
      date: 'Sep 3', duration: '61 min', host: 'Whitney', channel: '#accelerator-internal',
      decisions: ['Session recap approved for the portal'],
      clientCommitments: [],
      wiaCommitments: ['Publish community recap', 'File session assets', 'Process attendance'],
      risks: ['2 Zoom participants unmatched'],
      tasks: [
        { id: 'o1', title: 'Publish community recap post', owner: 'Gisselle', due: 'Today', ts: '58:30' },
        { id: 'o2', title: 'Match 2 unidentified participants', owner: 'Gisselle', due: 'Today', ts: '01:12' }
      ],
      moments: [
        { ts: '12:04', tag: 'Teaching', text: '“Creative fatigue shows up in frequency before cost.”' },
        { ts: '44:20', tag: 'Topic', text: '“Lead-form quality beats lead volume every time.”' }
      ],
      files: [['Recording.mp4', 'recording'], ['Summary.md', 'summary'], ['Attendance.csv', 'action items']],
      fileDest: 'Drive / Accelerators / Meta Office Hours / 2026-09-03', processed: true
    },
    {
      id: 'harbor-review', title: 'Harbor House — Creative Review', type: 'client', source: 'fathom', clientId: 'harbor',
      date: 'Sep 3', duration: '38 min', host: 'Jacqueline', channel: '#client-harbor-house',
      exceptions: true,
      decisions: ['Creative swap agreed in principle'],
      clientCommitments: [],
      wiaCommitments: ['Confirm swap once transcript is available'],
      risks: ['Transcript not returned by the recorder’s Fathom account', 'Slack channel not authorized for AI HQ'],
      tasks: [
        { id: 'h1', title: 'Confirm creative swap scope', owner: 'Jacqueline', due: 'Tomorrow', ts: '—' },
        { id: 'h2', title: 'Update creative brief in ClickUp', owner: 'Carmen', due: 'Friday', ts: '—' },
        { id: 'h3', title: 'Send client confirmation', owner: 'Danielle', due: 'Friday', ts: '—' }
      ],
      moments: [],
      files: [['Recording.mp4', 'recording'], ['Summary.md', 'summary']],
      fileDest: 'No mapped folder for Harbor House meetings'
    }
  ];
  meetingById(id) { return this.meetings.find(m => m.id === id) || this.meetings[0]; }
  meetingPackStatus(m) {
    if (m.exceptions && !(this.state.packExceptions || {}).transcript) return 'needs_source';
    if (m.processed) return 'executed';
    return this.packStatus(m.id);
  }
  signalMap = { 'bloom-strategy': 'c1', 'meta-office-hours': 'c2', 'rosewood-checkin': 'c3' };
  meetingExceptions(m) {
    const fixed = this.state.packExceptions || {};
    const btn = (bg, fg) => 'padding:9px 14px;border-radius:10px;font-size:12px;font-weight:700;cursor:pointer;background:' + bg + ';color:' + fg;
    const fix = (key, msg) => () => { const n = Object.assign({}, this.state.packExceptions); n[key] = true; this.setState({ packExceptions: n }); this.toast(msg); };
    const defs = [
      {
        key: 'transcript', system: 'fathom', code: 'SOURCE_UNAVAILABLE',
        message: 'Transcript unavailable',
        recovery: 'The recorder’s Fathom account has not shared this meeting with the team. Fathom API keys are user-scoped, so an admin key does not unlock it.',
        buttons: [['Retry demo', 'primary'], ['Upload transcript', 'ghost']]
      },
      {
        key: 'slack', system: 'slack', code: 'CHANNEL_UNAUTHORIZED',
        message: 'Private channel unavailable',
        recovery: 'AI HQ is not authorized for #client-harbor-house. Choose an authorized channel or copy the dispatch and post it manually.',
        buttons: [['Choose authorized channel', 'primary'], ['Copy message', 'ghost']]
      },
      {
        key: 'drive', system: 'drive', code: 'FOLDER_UNMAPPED',
        message: 'Client meeting folder not mapped',
        recovery: 'AI HQ files into existing mapped client folders only — it never creates onboarding folders.',
        buttons: [['Choose existing folder', 'primary'], ['Open source coverage', 'ghost']]
      },
      {
        key: 'clickup', system: 'clickup', code: 'WRITE_PARTIAL',
        message: '2 tasks created · 1 task failed',
        recovery: 'Assignee mapping missing for Danielle. Fix the mapping and retry the single failed write.',
        buttons: [['Fix mapping', 'primary'], ['Retry', 'ghost']]
      }
    ];
    return defs.map(d => {
      const done = !!fixed[d.key];
      const chip = this.srcChip(d.system);
      return {
        code: done ? 'RESOLVED' : d.code, codePill: this.pill(done ? 'green' : 'red'),
        system: chip.label, srcChip: chip.style, srcDot: chip.dot,
        message: done ? d.message + ' — resolved' : d.message,
        recovery: done ? 'Resolved in this demo session. Reset the demo to see the exception again.' : d.recovery,
        buttons: done
          ? [{ label: 'Resolved ✓', style: btn('#EAF7F0', '#1F8A5B'), go: () => { } }]
          : d.buttons.map((b, i) => ({
            label: b[0],
            style: btn(b[1] === 'primary' ? '#101747' : '#EDEFF6', b[1] === 'primary' ? '#fff' : '#5A6478'),
            go: i === 0 ? fix(d.key, d.message + ' — resolved (simulated)') : (() => this.toast(b[0] + ' — demo action, nothing is written'))
          }))
      };
    });
  }
  meetingVals() {
    const st = this.state;
    const detail = st.screen === 'meetings' && !!st.meetingId;
    const filters = [
      { id: 'needs_review', label: 'Needs Review' }, { id: 'client', label: 'Client' }, { id: 'internal', label: 'Internal' },
      { id: 'sales', label: 'Sales' }, { id: 'office_hours', label: 'Office Hours' }, { id: 'exceptions', label: 'Exceptions' }, { id: 'processed', label: 'Processed' }
    ];
    const match = (m, f) => {
      const s = this.meetingPackStatus(m);
      if (f === 'needs_review') return s === 'needs_review';
      if (f === 'exceptions') return s === 'needs_source';
      if (f === 'processed') return s === 'approved' || s === 'executed';
      return m.type === f;
    };
    const list = this.meetings.filter(m => match(m, st.meetingFilter));
    const base = {
      isMeetingList: st.screen === 'meetings' && !st.meetingId,
      isMeetingDetail: detail,
      backToMeetings: () => this.setState({ meetingId: null }),
      sourceCards: [
        { key: 'zoom', name: 'Zoom', status: 'Demo source connected', tone: 'green', detail: 'Whitney-hosted strategy, sales and Office Hours calls', note: 'Cloud transcript needs a paid plan with audio transcription; participant identity can be incomplete.' },
        { key: 'fathom', name: 'Fathom', status: 'Partial coverage', tone: 'amber', detail: '3 of 4 team recorders authorized · Whitney records in Zoom', note: 'Keys are user-scoped: a user’s key reaches their own or team-shared meetings only. Danielle’s key is not authorized, so her meetings need a source. Production validation required.' },
        { key: 'drive', name: 'Drive', status: 'Demo source connected', tone: 'green', detail: 'Meeting archive destination', note: '1 client folder mapping unresolved — files into existing folders only.' }
      ].map(s => {
        const chip = this.srcChip(s.key);
        return {
          name: s.name, status: s.status, detail: s.detail, note: s.note,
          chip: chip.style, dot: chip.dot, statusPill: this.pill(s.tone),
          wrap: 'border:1px solid #E7EAF1;border-radius:14px;padding:16px;background:#FBFCFF'
        };
      }),
      meetingFilters: filters.map(f => {
        const active = f.id === st.meetingFilter;
        return {
          label: f.label, count: this.meetings.filter(m => match(m, f.id)).length,
          go: () => this.setState({ meetingFilter: f.id }),
          style: 'display:inline-flex;align-items:center;gap:7px;padding:9px 14px;border-radius:10px;cursor:pointer;font-size:12.5px;font-weight:700;border:1px solid ' + (active ? '#5874F7' : '#E7EAF1') + ';color:' + (active ? '#fff' : '#5A6478') + ';background:' + (active ? '#101747' : '#fff'),
          countStyle: 'font-family:JetBrains Mono,monospace;font-size:10.5px;opacity:.75'
        };
      }),
      meetingCards: list.map(m => {
        const chip = this.srcChip(m.source);
        const stt = this.meetingPackStatus(m);
        const typeLabel = { client: 'Client', internal: 'Internal', sales: 'Sales', office_hours: 'Office Hours' }[m.type];
        return {
          title: m.title, date: m.date, duration: m.duration, host: 'Host ' + m.host, source: chip.label,
          chip: chip.style, dot: chip.dot, type: typeLabel, typePill: this.pill('outline'),
          status: stt === 'needs_source' ? 'Needs source' : (stt === 'needs_review' ? 'Needs review' : (stt === 'approved' ? 'Approved' : 'Processed')),
          statusPill: this.pill(stt === 'needs_source' ? 'red' : (stt === 'needs_review' ? 'amber' : 'green')),
          stats: [
            { value: m.decisions.length, label: 'decisions' },
            { value: m.tasks.length, label: 'proposed actions' },
            { value: m.type === 'client' ? 1 : 0, label: 'client recap' },
            { value: m.files.length, label: 'files ready' }
          ],
          cta: stt === 'needs_source' ? 'Review exceptions' : (stt === 'needs_review' ? 'Review execution pack' : 'Open execution pack'),
          packStatus: stt === 'needs_source' ? 'Blocked on source' : (stt === 'executed' ? 'Filed and dispatched' : (stt === 'approved' ? 'Pack approved' : 'Awaiting approval')),
          wrap: 'background:#fff;border:1px solid #E7EAF1;border-radius:18px;padding:20px;cursor:pointer;box-shadow:0 1px 2px rgba(16,23,71,.04)',
          go: () => this.setState({ meetingId: m.id })
        };
      })
    };
    if (!detail) return base;

    const m = this.meetingById(st.meetingId);
    const stt = this.meetingPackStatus(m);
    const exFixed = this.state.packExceptions || {};
    const exKeys = ['transcript', 'slack', 'drive', 'clickup'];
    const exOpen = m.exceptions ? exKeys.filter(k => !exFixed[k]).length : 0;
    const blocked = stt === 'needs_source';
    const slackBlocked = !!m.exceptions && !exFixed.slack;
    const driveBlocked = !!m.exceptions && !exFixed.drive;
    const tasksBlocked = blocked || (!!m.exceptions && !exFixed.clickup);
    const packBlocked = exOpen > 0;
    const approved = stt === 'approved' || stt === 'executed';
    const chip = this.srcChip(m.source);
    const taskState = st.taskState || {};
    const sel = st.taskSel || {};
    const selCount = m.tasks.filter(t => sel[t.id]).length;
    const marker = (col) => 'width:6px;height:6px;border-radius:50%;flex:none;margin-top:6px;background:' + col;
    const intel = [
      { label: 'Decisions', items: m.decisions, tone: 'blue', col: '#5874F7' },
      { label: 'Client commitments', items: m.clientCommitments, tone: 'amber', col: '#E0A020' },
      { label: 'WIA commitments', items: m.wiaCommitments, tone: 'green', col: '#2E9E6B' },
      { label: 'Risks', items: m.risks, tone: 'red', col: '#D94C4C' }
    ].filter(g => g.items.length);
    const slackPreviews = {
      'bloom-strategy': 'New actions from today’s strategy call:\n\nJacqueline\n• Complete landing-page handoff — tomorrow\n\nCarmen\n• Review keyword exclusions — Friday\n\nGisselle\n• Send client recap — today\n\nSource: Sep 2 Strategy Call',
      'monday-team': 'Monday meeting actions — grouped by owner:\n\nCarmen (2)\n• Rebuild Google keyword exclusion list — Thursday\n• Update Meta audience exclusions — Friday\n\nJacqueline (2)\n• Clear 3 overdue Bloom Manor tasks — Wednesday\n• Refresh testimonial creative brief — Friday\n\nGisselle (2)\n• Post Rosewood recap + invoice note — today\n• Confirm Office Hours host coverage — tomorrow\n\nWhitney (1)\n• Approve Harbor House creative swap — today\n\nSource: Aug 31 Monday Team Meeting',
      'magnolia-sales': 'Sales follow-up from the Magnolia House discovery call:\n\nWhitney\n• Send Elevate proposal — today\n\nGisselle\n• Log prospect in HighLevel pipeline — today\n\nOutcome: strong fit · interested in Elevate',
      'rosewood-checkin': 'Check-in actions posted Aug 25:\n\nGisselle\n• Send check-in recap — done\n• Request gallery assets again — done\n\nStill waiting on the client gallery (12 days).',
      'meta-office-hours': 'Meta Office Hours — Sep 3 actions:\n\nGisselle\n• Publish community recap post — today\n• Match unidentified participants — today',
      'harbor-review': 'Creative review actions — Harbor House:\n\nJacqueline\n• Confirm creative swap scope — tomorrow\n\nCarmen\n• Update creative brief in ClickUp — Friday\n\nDanielle\n• Send client confirmation — Friday\n\nReact with 👀 when you have picked up your item.'
    };
    const recaps = {
      'bloom-strategy': 'Hi Sarah,\n\nThank you for the time today — quick recap of where we landed.\n\nWhat we agreed\n• Testimonial creative test is approved\n• Revised landing page will be handed over tomorrow\n• Keyword exclusions reviewed before the next flight\n\nOn your side\n• October gallery assets by Friday\n\nRecording and summary:\n[Sep 2 Strategy Call]\n\nWe’ll follow up as each item is complete.\n\nThank you!',
      'magnolia-sales': 'Hi Tessa,\n\nGreat speaking with you today. As promised, here’s the Elevate proposal covering the scope we discussed, plus the venue-tour benchmark example.\n\n[Elevate proposal]\n\nHappy to walk through it live before Thursday if that helps.\n\nThank you!',
      'rosewood-checkin': 'Hi Dana,\n\nRecap of our check-in is below, along with the one item we’re still waiting on from your side (the gallery assets).\n\n[Aug 25 Check-in recording]\n\nThank you!',
      'monday-team': '',
      'meta-office-hours': ''
    };
    const packItems = [
      m.tasks.length + ' ClickUp task' + (m.tasks.length === 1 ? '' : 's'),
      m.exceptions ? 'Slack blocked' : '1 Slack message',
      recaps[m.id] ? '1 Gmail draft' : 'No client recap',
      m.exceptions ? m.files.length + ' Drive files · folder unmapped' : m.files.length + ' Drive files'
    ];
    const completionOn = !!st.actionsComplete[m.id];
    const completionApproved = !!st.completionApproved[m.id];
    return Object.assign(base, {
      mTitle: m.title, mDate: m.date, mDuration: m.duration, mHost: m.host, mSource: chip.label,
      mChip: chip.style, mDot: chip.dot,
      mType: { client: 'Client meeting', internal: 'Internal meeting', sales: 'Sales call', office_hours: 'Office Hours' }[m.type],
      mTypePill: this.pill('outline'),
      mPackStatus: stt === 'needs_source' ? 'Needs source' : (approved ? (stt === 'executed' ? 'Pack executed' : 'Pack approved') : 'Execution pack ready'),
      mPackPill: this.pill(stt === 'needs_source' ? 'red' : (approved ? 'green' : 'amber')),
      mPackNote: stt === 'needs_source' ? 'The meeting source did not return a transcript — see Exceptions below' : (approved ? 'Tasks created · Slack posted · draft ready · files filed' : 'Nothing has been created yet — review and approve below'),
      mHasExceptions: !!m.exceptions,
      mExceptions: m.exceptions ? this.meetingExceptions(m) : [],
      exceptionPill: this.pill('red'),
      signalPill: this.pill('violet'),
      mHasSignal: !!this.signalMap[m.id],
      mSignalTs: (this.opportunities.find(o => o.id === this.signalMap[m.id]) || {}).ts || '',
      mSignalKind: ((this.opportunities.find(o => o.id === this.signalMap[m.id]) || {}).signals || []).join(' · '),
      mSignalQuote: (this.opportunities.find(o => o.id === this.signalMap[m.id]) || {}).quote || '',
      mSignalUses: ((this.opportunities.find(o => o.id === this.signalMap[m.id]) || {}).recommended || []).map(r => ({
        label: r[0], stars: '★★★★★'.slice(0, r[1]) + '☆☆☆☆☆'.slice(0, 5 - r[1])
      })),
      mSignalButtons: [
        { label: 'Add direction', style: 'padding:9px 14px;border-radius:10px;font-size:12px;font-weight:700;cursor:pointer;background:#EDEFF6;color:#5A6478', go: () => this.setState({ voiceModal: this.signalMap[m.id] }) },
        { label: 'Build WIA content package →', style: 'padding:9px 14px;border-radius:10px;font-size:12px;font-weight:700;cursor:pointer;background:#101747;color:#fff', go: () => this.go('content', { contentId: this.signalMap[m.id] }) }
      ],
      groupBadge: 'width:20px;height:20px;border-radius:6px;background:#101747;color:#fff;display:flex;align-items:center;justify-content:center;font-size:10.5px;font-weight:800;flex:none',
      mIntel: intel.map(g => ({
        label: g.label, count: g.items.length, pill: this.pill(g.tone),
        items: g.items.map(t => ({ text: t, ts: '', marker: marker(g.col) }))
      })),
      mMoments: m.moments.map(mo => ({
        ts: mo.ts, tag: mo.tag, text: mo.text, tagPill: this.pill('outline'),
        go: () => this.setState({ drawer: { title: m.source === 'zoom' ? 'Zoom transcript — evidence' : 'Fathom transcript — evidence', source: m.source, label: m.title + ' · ' + mo.ts, excerpt: mo.text, time: m.date, client: m.clientId ? this.clientById(m.clientId).name : 'Internal' } })
      })),
      clickupBadge: this.autoBadge('clickup').style, clickupBadgeLabel: this.autoBadge('clickup').label,
      mTaskSummary: tasksBlocked ? m.tasks.length + ' proposed · ' + (blocked ? 'blocked on source' : 'assignee mapping missing') : (approved ? m.tasks.length + ' created in ClickUp' : m.tasks.length + ' proposed'),
      mTasks: m.tasks.map(t => {
        const s = tasksBlocked ? 'proposed' : (approved ? (taskState[t.id] || 'created') : (taskState[t.id] || 'proposed'));
        const on = !!sel[t.id];
        return {
          title: t.title, owner: t.owner, due: t.due, ts: t.ts,
          status: { proposed: 'Proposed', created: 'Created', acknowledged: 'Acknowledged', complete: 'Complete' }[s],
          statusPill: this.pill(s === 'proposed' ? 'outline' : (s === 'created' ? 'blue' : 'green')),
          check: on ? '✓' : '', box: 'width:18px;height:18px;border-radius:5px;border:1.5px solid ' + (on ? '#5874F7' : '#D6DBE8') + ';background:' + (on ? '#5874F7' : '#fff') + ';color:#fff;font-size:10px;font-weight:800;display:flex;align-items:center;justify-content:center;cursor:pointer',
          toggle: () => { const n = Object.assign({}, this.state.taskSel); n[t.id] = !n[t.id]; this.setState({ taskSel: n }); },
          editOwner: () => { const names = Object.keys(this.team); const i = names.indexOf(t.owner); t.owner = names[(i + 1) % names.length]; this.forceUpdate(); this.toast('Owner changed to ' + t.owner + ' — demo'); },
          editDate: () => { const ds = ['Today', 'Tomorrow', 'Wednesday', 'Thursday', 'Friday', 'Next Monday']; const i = ds.indexOf(t.due); t.due = ds[(i + 1) % ds.length]; this.forceUpdate(); this.toast('Due date changed to ' + t.due + ' — demo'); }
        };
      }),
      mSelectedCount: selCount,
      selectAllTasks: () => {
        const all = selCount === m.tasks.length; const n = {};
        m.tasks.forEach(t => { n[t.id] = !all; }); this.setState({ taskSel: n });
      },
      selectAllLabel: selCount === m.tasks.length ? 'Clear selection' : 'Select all',
      approveTasksLabel: tasksBlocked ? 'Blocked — resolve exceptions first' : (approved ? 'Tasks created in ClickUp' : 'Approve selected (' + selCount + ')'),
      approveTasksStyle: 'padding:9px 15px;border-radius:10px;font-size:12px;font-weight:700;cursor:' + (tasksBlocked ? 'not-allowed' : 'pointer') + ';background:' + (tasksBlocked ? '#FDECEC' : (approved ? '#EAF7F0' : (selCount ? '#101747' : '#EDEFF6'))) + ';color:' + (tasksBlocked ? '#C63F3F' : (approved ? '#1F8A5B' : (selCount ? '#fff' : '#A9B0C0'))),
      approveSelectedTasks: () => {
        if (tasksBlocked) { this.toast(blocked ? 'No transcript yet — resolve the source exception before creating tasks' : 'Assignee mapping missing in ClickUp — fix the mapping and retry'); return; }
        if (approved || !selCount) return;
        const n = Object.assign({}, this.state.taskState);
        m.tasks.forEach(t => { if (sel[t.id]) n[t.id] = 'created'; });
        this.setState({ taskState: n, taskSel: {} });
        this.toast(selCount + ' task' + (selCount === 1 ? '' : 's') + ' created in ClickUp — simulated');
      },
      mSlackChannel: m.channel,
      mSlackNote: slackBlocked ? 'BLOCKED — ' + m.channel + ' is a private channel AI HQ is not authorized for. Choose an authorized channel or copy the message and post it manually.' : (m.type === 'internal' ? 'Grouped by owner so the team reads one message, not seven.' : 'Posted to the client channel AI HQ is permitted to access.'),
      mSlackPreview: slackPreviews[m.id],
      mSlackStatus: slackBlocked ? 'Blocked — channel not authorized' : (approved ? 'Posted to Slack' : (st.slackIncluded[m.id] === false ? 'Excluded from pack' : 'Included in pack')),
      slackIncludeLabel: slackBlocked ? 'Choose authorized channel' : (approved ? 'Posted' : (st.slackIncluded[m.id] === false ? 'Include in pack' : 'Included in pack ✓')),
      slackIncludeStyle: 'padding:9px 15px;border-radius:10px;font-size:12px;font-weight:700;cursor:pointer;background:' + (slackBlocked ? '#FDECEC' : (approved ? '#EAF7F0' : (st.slackIncluded[m.id] === false ? '#EDEFF6' : '#EDF1FF'))) + ';color:' + (slackBlocked ? '#C63F3F' : (approved ? '#1F8A5B' : (st.slackIncluded[m.id] === false ? '#5A6478' : '#3F55D6'))),
      toggleSlackInclude: () => { if (slackBlocked) { this.toast('AI HQ is not authorized for ' + m.channel + ' — choose an authorized channel or copy the message'); return; } if (approved) return; const n = Object.assign({}, this.state.slackIncluded); n[m.id] = n[m.id] === false ? true : false; this.setState({ slackIncluded: n }); },
      editSlack: () => this.toast(slackBlocked ? 'Dispatch copied — post it manually in Slack' : 'Slack dispatch opened for editing — demo'),
      mHasRecap: !!recaps[m.id],
      mRecapTitle: m.type === 'sales' ? 'Follow-up email draft' : 'Client recap draft',
      mRecapDest: 'Gmail · ' + (m.clientId ? this.clientById(m.clientId).contact : 'client'),
      mRecapNote: 'Short recap, client action, WIA next steps and the recording link. Approval required before anything reaches Gmail.',
      mRecapDraft: recaps[m.id] || '',
      recapApproveLabel: approved ? 'Draft ready in Gmail' : 'Approve to Gmail',
      recapApproveStyle: 'padding:9px 15px;border-radius:10px;font-size:12px;font-weight:700;cursor:pointer;background:' + (approved ? '#EAF7F0' : '#101747') + ';color:' + (approved ? '#1F8A5B' : '#fff'),
      blockedPill: this.pill('red'),
      approveRecap: () => {
        if (approved) return;
        const ps = Object.assign({}, this.state.packState); ps[m.id] = this.state.packState[m.id] || 'needs_review';
        this.setState({ packState: ps }); this.toast('Recap draft created in Gmail — simulated');
      },
      recapIncludeLabel: st.recapIncluded[m.id] === false ? 'Include in pack' : 'Included in pack ✓',
      recapIncludeStyle: 'padding:9px 15px;border-radius:10px;font-size:12px;font-weight:700;cursor:pointer;background:' + (st.recapIncluded[m.id] === false ? '#EDEFF6' : '#EDF1FF') + ';color:' + (st.recapIncluded[m.id] === false ? '#5A6478' : '#3F55D6'),
      toggleRecapInclude: () => { const n = Object.assign({}, this.state.recapIncluded); n[m.id] = n[m.id] === false ? true : false; this.setState({ recapIncluded: n }); },
      editRecap: () => this.toast('Recap draft opened for editing — demo'),
      mIsSales: m.type === 'sales', mIsInternal: m.type === 'internal',
      salesPill: this.pill('violet'), internalPill: this.pill('outline'),
      mInternalHeadline: m.tasks.length + ' actions found',
      mOwnerCounts: (() => {
        const byOwner = {};
        m.tasks.forEach(t => { byOwner[t.owner] = (byOwner[t.owner] || 0) + 1; });
        const max = Math.max.apply(null, Object.values(byOwner).concat([1]));
        return Object.keys(byOwner).map(name => ({
          name: name, initial: this.team[name] || name[0], count: byOwner[name],
          bar: 'height:8px;border-radius:5px;flex:1;max-width:' + Math.round((byOwner[name] / max) * 100) + '%;background:linear-gradient(90deg,#5874F7,#8FA4FB)'
        }));
      })(),
      mFileDest: driveBlocked ? m.fileDest : (m.exceptions ? 'Drive / Clients / Harbor House / Meetings / 2026-09-03 Creative Review' : m.fileDest),
      mFilesStatus: driveBlocked ? 'Blocked — folder not mapped' : (approved ? 'Filed in Drive' : 'Ready to file'),
      mFiles: m.files.map(f => ({
        name: f[0], type: f[1].charAt(0).toUpperCase() + f[1].slice(1), ext: f[0].split('.').pop().toUpperCase(),
        status: driveBlocked ? 'Waiting on folder' : (approved ? 'Filed' : 'Ready'), statusPill: this.pill(driveBlocked ? 'amber' : (approved ? 'green' : 'outline'))
      })),
      mPackHeadline: packBlocked ? (blocked ? 'Blocked on source' : exOpen + ' exceptions open')  : (approved ? (stt === 'executed' ? 'Executed' : 'Approved · executing') : 'Ready for approval'),
      mPackItems: (m.exceptions ? [
        m.tasks.length + ' ClickUp task' + (m.tasks.length === 1 ? '' : 's') + (exFixed.clickup ? '' : ' · mapping missing'),
        exFixed.slack ? '1 Slack message' : 'Slack blocked',
        'No client recap',
        m.files.length + ' Drive files' + (exFixed.drive ? '' : ' · folder unmapped')
      ] : packItems).map(p => ({ label: p, style: this.pill('outline') })),
      approvePackLabel: packBlocked ? 'Cannot approve — ' + exOpen + ' exception' + (exOpen === 1 ? '' : 's') + ' open' : (approved ? 'Pack approved ✓' : 'Approve execution pack'),
      approvePackStyle: 'padding:11px 18px;border-radius:11px;font-size:12.5px;font-weight:700;cursor:' + (packBlocked ? 'not-allowed' : 'pointer') + ';background:' + (packBlocked ? '#FDECEC' : (approved ? '#EAF7F0' : '#101747')) + ';color:' + (packBlocked ? '#C63F3F' : (approved ? '#1F8A5B' : '#fff')),
      reviewChanges: () => this.setState({
        drawer: {
          title: 'Review changes before approval', source: 'aihq', label: m.title,
          excerpt: 'On approval AI HQ will: create ' + m.tasks.length + ' ClickUp tasks with owners and due dates; post one Slack dispatch to ' + m.channel + '; ' + (recaps[m.id] ? 'create one Gmail draft for review; ' : 'create no client email; ') + 'file ' + m.files.length + ' assets to ' + m.fileDest + '; and begin acknowledgement monitoring in Ops Watch.',
          time: m.date, client: m.clientId ? this.clientById(m.clientId).name : 'Internal'
        }
      }),
      approvePack: () => {
        if (packBlocked) { this.toast(exOpen + ' exception' + (exOpen === 1 ? '' : 's') + ' still open — resolve them before approving this pack'); return; }
        if (approved) return;
        const ps = Object.assign({}, this.state.packState); ps[m.id] = 'approved';
        const ts = Object.assign({}, this.state.taskState); m.tasks.forEach(t => { ts[t.id] = 'created'; });
        this.setState({ packState: ps, taskState: ts, taskSel: {} });
        this.toast('Execution pack approved — tasks created, Slack posted, draft ready, files filed');
      },
      mShowCompleteToggle: m.id === 'bloom-strategy' && approved && !completionOn,
      completeActions: () => {
        const ac = Object.assign({}, this.state.actionsComplete); ac[m.id] = true;
        const ts = Object.assign({}, this.state.taskState); m.tasks.forEach(t => { ts[t.id] = 'complete'; });
        this.setState({ actionsComplete: ac, taskState: ts });
        this.toast('All client-facing actions complete — completion update suggested');
      },
      mShowCompletion: m.id === 'bloom-strategy' && completionOn,
      mCompletionTitle: 'Bloom Manor strategy call',
      mCompletionSub: '4 / 4 client-facing actions completed',
      mCompletionDraft: this.drafts.e3,
      completionBtnLabel: completionApproved ? 'Completion update drafted in Gmail ✓' : 'Review completion update',
      completionBtnStyle: 'padding:10px 16px;border-radius:10px;font-size:12.5px;font-weight:700;cursor:pointer;background:' + (completionApproved ? 'rgba(63,211,160,.18)' : '#fff') + ';color:' + (completionApproved ? '#8FF0CB' : '#101747'),
      approveCompletion: () => {
        const ca = Object.assign({}, this.state.completionApproved); ca[m.id] = true;
        const es = Object.assign({}, this.state.emailState); es.e3 = 'approved';
        this.setState({ completionApproved: ca, emailState: es });
        this.toast('Completion update draft created in Gmail — simulated');
      },
      goInboxCompletion: () => this.go('inbox', { inboxQueue: 'needs_whitney', emailId: 'e3' })
    });
  }
  /* ---------- client 360 ---------- */
  clientTimelines = {
    bloom: [
      { when: 'Today', s: 'gmail', text: 'Client requested landing-page update', meta: 'Sarah Mitchell · thread open', status: 'Reply due', tone: 'amber' },
      { when: 'Today', s: 'slack', text: 'Jacqueline confirmed final QA', meta: '#client-bloom-manor', status: 'Context', tone: 'outline' },
      { when: 'Yesterday', s: 'clickup', text: 'Landing Page QA moved to In Progress', meta: 'Owner Jacqueline · due tomorrow', status: 'In progress', tone: 'blue' },
      { when: 'Sep 2', s: 'gmail', text: 'Strategy call recap sent', meta: 'Approved by Whitney before sending', status: 'Sent', tone: 'green' },
      { when: 'Sep 2', s: 'zoom', text: 'Monthly Strategy Call', meta: '58 min · 4 decisions · 3 actions', status: 'Processed', tone: 'green' },
      { when: 'Sep 2', s: 'drive', text: 'Meeting transcript filed', meta: 'Clients / Bloom Manor / Meetings / 2026-09-02', status: 'Filed', tone: 'green' },
      { when: 'Aug 26', s: 'highlevel', text: 'Invoice INV-201 paid', meta: '$2,400 · on time', status: 'Paid', tone: 'green' }
    ],
    rosewood: [
      { when: 'Today', s: 'highlevel', text: 'INV-204 flagged overdue', meta: '$1,850 · 5 days past due · standard reminder sent', status: 'Needs review', tone: 'amber' },
      { when: '2d ago', s: 'gmail', text: 'Client asked a question — no reply detected', meta: 'Owner Carmen · 29 business hours', status: 'SLA breach', tone: 'red' },
      { when: 'Aug 23', s: 'gmail', text: 'Gallery assets requested again', meta: 'Waiting 12 days', status: 'Waiting', tone: 'amber' },
      { when: 'Aug 25', s: 'fathom', text: 'Monthly Check-in', meta: '46 min · recap sent same day', status: 'Processed', tone: 'green' },
      { when: 'Aug 25', s: 'drive', text: 'Check-in recording + transcript filed', meta: 'Clients / Rosewood Venue / Meetings', status: 'Filed', tone: 'green' }
    ],
    everly: [
      { when: '2d ago', s: 'highlevel', text: 'Missed Google Office Hours (2nd consecutive)', meta: 'Attendance from Zoom participant report', status: 'At risk', tone: 'amber' },
      { when: 'Aug 20', s: 'zoom', text: 'Attended Google Office Hours', meta: 'Matched automatically', status: 'Attended', tone: 'green' },
      { when: 'Aug 19', s: 'highlevel', text: 'Community reminder delivered', meta: 'Recurring post · 1 hour before', status: 'Sent', tone: 'green' }
    ],
    willow: [
      { when: 'Today', s: 'highlevel', text: 'Missed Meta Office Hours (4th consecutive)', meta: 'Personal email recommended', status: 'Re-engage', tone: 'red' },
      { when: 'Sep 3', s: 'zoom', text: 'Participant “Maya” could not be matched automatically', meta: '91% suggested match · needs confirmation', status: 'Needs match', tone: 'amber' },
      { when: 'Aug 6', s: 'zoom', text: 'Attended Meta Office Hours', meta: 'Last confirmed attendance', status: 'Attended', tone: 'green' }
    ],
    magnolia: [
      { when: 'Yesterday', s: 'zoom', text: 'Discovery call — strong fit for Elevate', meta: '34 min · next step: send proposal', status: 'Processed', tone: 'green' },
      { when: 'Yesterday', s: 'gmail', text: 'Proposal follow-up draft prepared', meta: 'Awaiting Whitney approval', status: 'Draft ready', tone: 'blue' },
      { when: 'Aug 24', s: 'highlevel', text: 'Lead created from referral', meta: 'Contact: Tessa Ruiz', status: 'Context', tone: 'outline' }
    ],
    harbor: [
      { when: 'Today', s: 'highlevel', text: 'INV-198 overdue 8 days', meta: '$1,750 · needs review', status: 'Needs review', tone: 'amber' },
      { when: '1d ago', s: 'gmail', text: 'Reporting cadence question', meta: 'Draft prepared for Whitney', status: 'Draft ready', tone: 'blue' },
      { when: '2d ago', s: 'gmail', text: 'Creative swap approval waiting on Jacqueline', meta: '26 business hours', status: 'At risk', tone: 'amber' }
    ]
  };
  clientAsks = {
    'What did we promise them on the last call?': 'On the Sep 2 strategy call WIA committed to:\n\n1. Deliver the revised landing page (Jacqueline · tomorrow).\n2. Review keyword exclusions before the next flight (Carmen · Friday).\n3. Update the testimonial creative.\n4. Send the recap the same day (sent Aug 28).',
    'What are we waiting on?': '1. October gallery assets — requested 5 days ago.\n2. Client approval on revised CTA copy — requested yesterday.',
    'What is overdue?': '1 task is overdue: testimonial creative (Jacqueline, overdue 1 day). No client-facing email is overdue; one reply is inside the 24–48 business-hour window.',
    'Has the team acknowledged the latest actions?': '2 of 3 actions acknowledged in Slack. Jacqueline has not acknowledged the testimonial creative after 23 hours — a nudge is ready in Ops Watch.',
    'When did we last email them?': 'Sep 2 — strategy call recap, approved by Whitney before sending. The client replied today asking about the landing page.',
    'Where is the last meeting recording?': 'Drive / Clients / Bloom Manor / Meetings / 2026-09-02 Strategy — Recording.mp4, Transcript.txt, Summary.md and Action Items.md are all filed.',
    'What has changed since the last call?': 'Landing Page QA moved to In Progress (yesterday), final QA confirmed in Slack today, and the client has since asked for a delivery update. The gallery assets are still outstanding.'
  };
  askSources = {
    'What are we waiting on?': ['Gmail · Sep 3', 'ClickUp · Landing Page QA', 'Slack · #client-bloom-manor'],
    'What did we promise them on the last call?': ['Zoom · Sep 2 · 24:18', 'ClickUp · 3 actions', 'Gmail · recap Sep 2'],
    'What is overdue?': ['ClickUp · overdue view', 'Slack · #client-bloom-manor'],
    'Has the team acknowledged the latest actions?': ['Slack · reactions', 'ClickUp · status events'],
    'When did we last email them?': ['Gmail · thread history'],
    'Where is the last meeting recording?': ['Drive · meeting folder', 'Zoom · recording'],
    'What has changed since the last call?': ['ClickUp · status events', 'Slack · #client-bloom-manor', 'Gmail · today']
  };
  clientVals() {
    const st = this.state;
    const list = st.screen === 'clients' && !st.clientId;
    const base = {
      isClientList: list, isClientDetail: st.screen === 'clients' && !!st.clientId,
      backToClients: () => this.setState({ clientId: null, askAnswer: null }),
      clientRows: this.clients.map(c => ({
        name: c.name, contact: c.contact, service: c.service, opStatus: c.opStatus, lastComm: c.lastComm,
        open: c.open, waiting: c.waitingOn ? c.waitingOn + ' · ' + c.waitingDays + 'd' : '—', next: c.next,
        servicePill: this.pill(c.status === 'prospect' ? 'violet' : 'outline'),
        dot: 'width:8px;height:8px;border-radius:50%;flex:none;background:' + (c.attention === 'attention' ? '#E0A020' : '#2E9E6B'),
        go: () => this.setState({ clientId: c.id, clientTab: 'overview', askAnswer: null })
      }))
    };
    if (list || st.screen !== 'clients') return base;
    const c = this.clientById(st.clientId);
    const tabs = [['overview', 'Overview'], ['activity', 'Activity'], ['communication', 'Communication'], ['meetings', 'Meetings'], ['tasks', 'Tasks'], ['files', 'Files']];
    const tl = this.clientTimelines[c.id] || [];
    const cMeetings = this.meetings.filter(m => m.clientId === c.id);
    const askKeys = Object.keys(this.clientAsks);
    return Object.assign(base, {
      cName: c.name, cContact: c.contact + ' · primary contact', cService: c.service,
      cServicePill: this.pill('outline'),
      cStatus: c.status === 'prospect' ? 'Prospect' : 'Active',
      cStatusPill: this.pill(c.status === 'prospect' ? 'violet' : 'green'),
      clientTabs: tabs.map(t => {
        const active = st.clientTab === t[0];
        return {
          label: t[1], go: () => this.setState({ clientTab: t[0] }),
          style: 'padding:9px 15px;border-radius:10px;font-size:12.5px;font-weight:700;cursor:pointer;border:1px solid ' + (active ? '#5874F7' : '#E7EAF1') + ';background:' + (active ? '#101747' : '#fff') + ';color:' + (active ? '#fff' : '#5A6478')
        };
      }),
      cTabOverview: st.clientTab === 'overview',
      cShowTimeline: st.clientTab === 'overview' || st.clientTab === 'activity',
      cShowComms: st.clientTab === 'communication', cShowMeetings: st.clientTab === 'meetings',
      cShowTasks: st.clientTab === 'tasks', cShowFiles: st.clientTab === 'files',
      cTimelineTitle: st.clientTab === 'activity' ? 'Unified activity timeline' : 'Recent operational activity',
      cTimelineNote: tl.length + ' events across 7 sources',
      cOverview: [
        { label: 'Last client message', value: c.lastComm.split(' · ')[0], meta: c.lastComm.split(' · ')[1] || 'Gmail' },
        { label: 'Last meeting', value: cMeetings.length ? cMeetings[0].date : '—', meta: cMeetings.length ? cMeetings[0].source === 'zoom' ? 'Zoom' : 'Fathom' : 'No meetings' },
        { label: 'Open actions', value: c.open, meta: 'In ClickUp' },
        { label: 'Overdue', value: c.overdue, meta: c.overdue ? 'Needs attention' : 'Clear' },
        { label: 'Waiting on client', value: c.waitingOn ? c.waitingDays + 'd' : '—', meta: c.waitingOn || 'Nothing outstanding' },
        { label: 'Next call', value: c.next.split(' · ')[0], meta: c.next.split(' · ')[1] || '' }
      ].map(o => ({
        label: o.label, value: o.value, meta: o.meta,
        valueStyle: 'font-family:DM Serif Display,serif;font-size:22px;color:#101747;line-height:1.1;margin-top:8px'
      })),
      cPriority: c.opStatus,
      cPriorityDetail: c.id === 'bloom' ? 'Revised page must reach Sarah tomorrow; the October gallery is still outstanding on the client side.' : 'Derived from open actions, waiting items and the most recent meeting commitments.',
      cTimeline: tl.map(e => {
        const chip = this.srcChip(e.s);
        return {
          when: e.when, source: chip.label, chip: chip.style, dot: chip.dot, text: e.text, meta: e.meta,
          status: e.status, statusPill: this.pill(e.tone),
          go: () => this.setState({ drawer: { title: chip.label + ' — evidence', source: e.s, label: e.text, excerpt: e.meta, time: e.when, client: c.name } })
        };
      }),
      cAskPrompts: askKeys.map(q => ({
        label: q, go: () => this.setState({ askAnswer: q }),
        style: 'padding:10px 13px;border-radius:11px;background:' + (st.askAnswer === q ? 'rgba(255,255,255,.14)' : 'rgba(255,255,255,.06)') + ';border:1px solid rgba(255,255,255,.1);color:#DDE3FB;font-size:12px;font-weight:600;cursor:pointer;line-height:1.4'
      })),
      cHasAnswer: !!st.askAnswer,
      cAnswerQ: st.askAnswer || '',
      cAnswerBody: st.askAnswer ? (c.id === 'bloom' ? this.clientAsks[st.askAnswer] : 'Operational answer for ' + c.name + ' is generated from the same sources — this demo carries the full source-backed answer set on Bloom Manor.') : '',
      cAnswerSources: ((this.askSources[st.askAnswer] || ['Gmail', 'ClickUp', 'Slack'])).map(l => ({ label: l })),
      clickupBadge2: this.autoBadge('clickup').style, clickupBadgeLabel2: this.autoBadge('clickup').label,
      cTasks: (c.id === 'bloom' ? [
        { title: 'Complete landing-page handoff', owner: 'Jacqueline', due: 'Tomorrow', origin: 'Sep 2 strategy call', status: 'In progress', tone: 'blue' },
        { title: 'Review keyword exclusions', owner: 'Carmen', due: 'Friday', origin: 'Sep 2 strategy call', status: 'Acknowledged', tone: 'green' },
        { title: 'Update testimonial creative', owner: 'Jacqueline', due: 'Friday', origin: 'Sep 2 strategy call', status: 'Overdue 1d', tone: 'red' },
        { title: 'Send client recap', owner: 'Gisselle', due: 'Today', origin: 'Sep 2 strategy call', status: 'Complete', tone: 'green' }
      ] : [
        { title: 'Send check-in recap', owner: 'Gisselle', due: c.lastComm, origin: 'Last meeting', status: 'Complete', tone: 'green' },
        { title: 'Follow up on outstanding items', owner: 'Gisselle', due: 'This week', origin: 'Waiting rule', status: 'In progress', tone: 'blue' }
      ]).map(t => ({ title: t.title, owner: t.owner, due: t.due, origin: t.origin, status: t.status, statusPill: this.pill(t.tone), initial: this.team[t.owner] || t.owner[0] })),
      cFileRoot: 'Drive / Clients / ' + c.name + ' / Meetings',
      cFiles: (cMeetings.length ? cMeetings : [this.meetings[0]]).slice(0, 2).reduce((acc, m) => acc.concat(m.files.map(f => ({
        name: f[0], meta: m.date + ' · ' + m.title, ext: f[0].split('.').pop().toUpperCase(),
        status: 'Filed', statusPill: this.pill('green')
      }))), []),
      cMeetings: cMeetings.map(m => {
        const chip = this.srcChip(m.source);
        const stt = this.meetingPackStatus(m);
        return {
          title: m.title, date: m.date, duration: m.duration, source: chip.label, chip: chip.style, dot: chip.dot,
          status: stt === 'needs_source' ? 'Needs source' : (stt === 'needs_review' ? 'Pack needs review' : 'Processed'), statusPill: this.pill(stt === 'needs_source' ? 'red' : (stt === 'needs_review' ? 'amber' : 'green')),
          summary: m.decisions.length + ' decisions · ' + m.tasks.length + ' actions · ' + m.files.length + ' files',
          go: () => this.go('meetings', { meetingId: m.id })
        };
      }),
      cComms: [
        { s: 'gmail', title: 'Latest client thread', excerpt: c.id === 'bloom' ? 'Any update on the landing page? — Sarah Mitchell' : 'Most recent Gmail thread for this account', when: 'Today', go: () => this.go('inbox', { inboxQueue: 'needs_whitney', emailId: c.id === 'bloom' ? 'e1' : 'e2' }) },
        { s: 'slack', title: '#client-' + c.id, excerpt: 'Team context AI HQ is permitted to read — QA confirmations, handoffs and acknowledgements.', when: 'Today', go: () => this.setState({ drawer: { title: 'Slack — evidence', source: 'slack', label: '#client-' + c.id, excerpt: 'Only channels the AI HQ service identity is permitted to access are read.', time: 'Today', client: c.name } }) },
        { s: 'gmail', title: 'Last approved send', excerpt: 'Recap approved by Whitney before it left AI HQ.', when: 'Sep 2', go: () => this.setState({ drawer: { title: 'Gmail — evidence', source: 'gmail', label: 'Approved recap', excerpt: 'Draft → review → approve. Nothing auto-sends.', time: 'Sep 2', client: c.name } }) },
        { s: 'highlevel', title: 'Contact + invoice record', excerpt: 'Email validity, invoice status and Accelerator context.', when: 'Live', go: () => this.go('ops', { opsTab: 'finance' }) }
      ].map(x => {
        const chip = this.srcChip(x.s);
        return { title: x.title, excerpt: x.excerpt, when: x.when, source: chip.label, chip: chip.style, dot: chip.dot, go: x.go };
      }),
      cOpenMeeting: () => this.go('meetings', { meetingId: cMeetings.length ? cMeetings[0].id : 'bloom-strategy' }),
      cOpenInbox: () => this.go('inbox', { inboxQueue: 'needs_whitney', emailId: c.id === 'bloom' ? 'e1' : 'e2' })
    });
  }

  /* ---------- accelerators ---------- */
  participants = [
    { id: 'p1', raw: 'Nina Cole', member: 'Everly Estate', status: 'matched' },
    { id: 'p2', raw: 'Dana Whitfield', member: 'Rosewood Venue', status: 'matched' },
    { id: 'p3', raw: 'Elena Park', member: 'Harbor House', status: 'matched' },
    { id: 'm1', raw: 'Sarah’s iPad', member: 'Sarah Mitchell — Bloom Manor', confidence: 76, status: 'unmatched' },
    { id: 'm2', raw: 'Maya', member: 'Maya Stone — Willow & Pine', confidence: 91, status: 'unmatched' },
    { id: 'm3', raw: 'iPhone (4)', member: 'No suggested member', confidence: 0, status: 'unmatched' }
  ];
  accVals() {
    const st = this.state;
    const tabs = [['engagement', 'Engagement'], ['attendance', 'Attendance'], ['reminders', 'Reminders'], ['sessions', 'Sessions']];
    const tabCounts = { engagement: this.disengagedCount(), attendance: this.unmatchedCount(), reminders: this.workshopStatus() === 'needs_review' ? 1 : 0, sessions: (st.sessionState.community === 'published' ? 0 : 1) };
    const members = [
      { id: 'everly', member: 'Everly Estate', program: 'Google', last: 'Aug 20', misses: 2, rule: 'at_risk' },
      { id: 'willow', member: 'Willow & Pine', program: 'Meta', last: 'Aug 6', misses: 4, rule: 'reengage' },
      { id: 'rosewood', member: 'Rosewood Venue', program: 'Google', last: 'Sep 3', misses: 0, rule: 'active' },
      { id: 'harbor', member: 'Harbor House', program: 'Meta', last: 'Sep 3', misses: 0, rule: 'active' }
    ];
    const matched = 8 + (3 - this.unmatchedCount());
    const btn = (bg, fg) => 'padding:9px 14px;border-radius:10px;font-size:12px;font-weight:700;cursor:pointer;background:' + bg + ';color:' + fg;
    const reminders = [
      {
        id: 'google_oh', title: 'Google Ads Office Hours', auto: 'highlevel', status: 'Recurring in HighLevel', tone: 'green',
        fields: [['Event', 'Thursday · 11:00 AM CT'], ['Reminder', '1 hour before'], ['Copy', 'Approved recurring variants'], ['Destination', 'HighLevel Community']],
        note: 'No weekly approval needed once the copy set is approved — HighLevel performs the scheduling.',
        buttons: [['View copy variants', 'variants'], ['Open in HighLevel', 'open']]
      },
      {
        id: 'meta_oh', title: 'Meta Ads Office Hours', auto: 'highlevel', status: 'Recurring in HighLevel', tone: 'green',
        fields: [['Event', 'Thursday · 2:00 PM CT'], ['Reminder', '1 hour before'], ['Copy', 'Approved recurring variants'], ['Destination', 'HighLevel Community']],
        note: 'AI HQ only surfaces the exception if a scheduled post fails or the event moves.',
        buttons: [['View copy variants', 'variants'], ['Open in HighLevel', 'open']]
      },
      {
        id: 'qa', title: 'Q&A reminder', auto: 'highlevel', status: 'Recurring in HighLevel', tone: 'green',
        fields: [['Event', 'Every other week'], ['Reminder', '1 hour before'], ['Copy', 'Rotates across approved variants'], ['Destination', 'HighLevel Community']],
        note: 'Copy rotation happens inside the approved variant set — no new judgment required.',
        buttons: [['View copy variants', 'variants'], ['Open in HighLevel', 'open']]
      },
      {
        id: 'workshop', title: 'Workshop reminder', auto: 'ai_hq', status: this.workshopStatus() === 'scheduled' ? 'Scheduled in HighLevel' : 'Needs review', tone: this.workshopStatus() === 'scheduled' ? 'green' : 'amber',
        fields: [['Event', 'Every other week'], ['Theme', 'Turning leads into venue tours'], ['Whitney input', 'Received'], ['AI draft', 'Ready for review']],
        note: 'The theme changes every session, so human review stays in the loop before scheduling.',
        buttons: [['Review copy', 'review'], ['Schedule in HighLevel', 'schedule']]
      }
    ];
    const sessionStages = [
      { key: 'attendance', label: 'Attendance processed', meta: matched + ' matched · ' + this.unmatchedCount() + ' unmatched', status: this.unmatchedCount() ? 'Needs matching' : 'Complete', tone: this.unmatchedCount() ? 'amber' : 'green' },
      { key: 'recording', label: 'Recording available', meta: 'Zoom cloud recording · 61 min', status: 'Complete', tone: 'green' },
      { key: 'summary', label: 'Summary generated', meta: 'Topics and follow-ups extracted', status: 'Complete', tone: 'green' },
      { key: 'internal', label: 'Internal Slack recap', meta: '#accelerator-internal', status: st.sessionState.internal === 'posted' ? 'Posted' : 'Ready', tone: st.sessionState.internal === 'posted' ? 'green' : 'blue' },
      { key: 'banner', label: 'Dated banner', meta: 'Template-generated · Sep 3', status: 'Ready', tone: 'blue' },
      { key: 'community', label: 'Community recap draft', meta: 'Member portal post', status: st.sessionState.community === 'published' ? 'Published' : 'Needs review', tone: st.sessionState.community === 'published' ? 'green' : 'amber' },
      { key: 'files', label: 'Session assets filed', meta: 'Drive / Accelerators / Meta Office Hours / 2026-09-03', status: 'Filed', tone: 'green' }
    ];
    return {
      isAccelerators: st.screen === 'accelerators',
      accHostBadge: this.autoBadge('clickup').style, accHostBadgeLabel: this.autoBadge('clickup').label,
      accTabs: tabs.map(t => {
        const active = st.accTab === t[0];
        return {
          label: t[1], count: tabCounts[t[0]] || '', go: () => this.setState({ accTab: t[0] }),
          style: 'display:inline-flex;align-items:center;gap:7px;padding:9px 15px;border-radius:10px;font-size:12.5px;font-weight:700;cursor:pointer;border:1px solid ' + (active ? '#5874F7' : '#E7EAF1') + ';background:' + (active ? '#101747' : '#fff') + ';color:' + (active ? '#fff' : '#5A6478'),
          countStyle: 'font-family:JetBrains Mono,monospace;font-size:10.5px;opacity:.75'
        };
      }),
      accIsEngagement: st.accTab === 'engagement', accIsAttendance: st.accTab === 'attendance',
      accIsReminders: st.accTab === 'reminders', accIsSessions: st.accTab === 'sessions',
      engagementRows: members.map(m => {
        const contacted = st.memberState[m.id] === 'contacted';
        const label = m.rule === 'at_risk' ? 'At Risk' : (m.rule === 'reengage' ? 'Re-engage' : 'Active');
        return {
          member: m.member, program: m.program, last: m.last, misses: m.misses,
          status: contacted ? 'Contacted' : label,
          statusPill: this.pill(contacted ? 'green' : (m.rule === 'at_risk' ? 'amber' : (m.rule === 'reengage' ? 'red' : 'outline'))),
          action: m.rule === 'at_risk' ? 'Portal DM' : (m.rule === 'reengage' ? 'Personal Email' : '—'),
          actionStyle: m.rule === 'active' ? 'font-size:12px;color:#B3BAC9' : 'font-size:12px;font-weight:700;color:#4563EE;cursor:pointer;border-bottom:1px dashed #C9D4FA',
          go: m.rule === 'active' ? (() => { }) : (() => this.setState({
            msgModal: {
              kind: m.rule, member: m.member, id: m.id,
              title: m.rule === 'at_risk' ? 'Suggested portal DM' : 'Suggested personal email',
              body: m.rule === 'at_risk'
                ? 'Hi Nina — noticed you’ve missed the last couple of Google Office Hours. Anything you’d like us to cover next week? Happy to send the replays across in the meantime.'
                : 'Hi Maya,\n\nWe’ve missed you at the last few Meta Office Hours sessions. I wanted to check in personally — is there a time or format that would work better for you?\n\nHappy to jump on a quick call and get you caught up.',
              note: m.rule === 'at_risk' ? 'Suggested only — WIA sends this manually from the member portal.' : 'Suggested only — created as a Gmail draft, never auto-sent.'
            }
          }))
        };
      }),
      accRules: [
        {
          trigger: '2 misses', status: 'At Risk', action: 'Personal portal DM', pill: this.pill('amber'),
          note: 'Suggested only — WIA sends manually. AI HQ flags the streak and prepares copy.',
          buttons: [
            { label: 'Preview suggested message', style: btn('#101747', '#fff'), go: () => this.setState({ msgModal: { kind: 'at_risk', member: 'Everly Estate', id: 'everly', title: 'Suggested portal DM', body: 'Hi Nina — noticed you’ve missed the last couple of Google Office Hours. Anything you’d like us to cover next week? Happy to send the replays across in the meantime.', note: 'Suggested only — WIA sends this manually from the member portal.' } }) },
            { label: 'Copy', style: btn('#EDEFF6', '#5A6478'), go: () => this.toast('Copied to clipboard — demo') },
            { label: 'Mark contacted', style: btn('#EDF1FF', '#3F55D6'), go: () => { const n = Object.assign({}, this.state.memberState); n.everly = 'contacted'; this.setState({ memberState: n }); this.toast('Everly Estate marked contacted'); } }
          ]
        },
        {
          trigger: '4 misses', status: 'Re-engage', action: 'Personal email', pill: this.pill('red'),
          note: 'Gmail draft prepared for a human to send. No auto-send at any point.',
          buttons: [
            { label: 'Create Gmail draft', style: btn('#101747', '#fff'), go: () => this.toast('Personal re-engagement draft created in Gmail — simulated') },
            { label: 'Mark contacted', style: btn('#EDF1FF', '#3F55D6'), go: () => { const n = Object.assign({}, this.state.memberState); n.willow = 'contacted'; this.setState({ memberState: n }); this.toast('Willow & Pine marked contacted'); } }
          ]
        }
      ],
      zoomBadge: this.autoBadge('zoom').style, zoomBadgeLabel: this.autoBadge('zoom').label,
      attendanceStats: [
        { label: 'Zoom participants', value: 11 },
        { label: 'Matched members', value: matched },
        { label: 'Probable match', value: this.state.matchState.m2 ? 0 : 1 },
        { label: 'Unmatched', value: this.unmatchedCount() }
      ].map(s => ({ label: s.label, value: s.value, valueStyle: 'font-family:DM Serif Display,serif;font-size:30px;color:#101747;line-height:1;margin-top:9px' })),
      unmatchedBtnLabel: this.unmatchedCount() ? 'Review unmatched (' + this.unmatchedCount() + ')' : 'All participants matched ✓',
      unmatchedBtnStyle: 'margin-top:16px;display:inline-flex;padding:10px 16px;border-radius:10px;font-size:12.5px;font-weight:700;cursor:pointer;background:' + (this.unmatchedCount() ? '#101747' : '#EAF7F0') + ';color:' + (this.unmatchedCount() ? '#fff' : '#1F8A5B'),
      openUnmatched: () => { if (this.unmatchedCount()) this.setState({ drawer: { kind: 'match' } }); },
      participantRows: this.participants.map(p => {
        const confirmed = !!st.matchState[p.id];
        const isUn = p.status === 'unmatched' && !confirmed;
        return {
          raw: p.raw, initial: p.raw.replace('’', '').charAt(0).toUpperCase(),
          meta: isUn ? 'Possible: ' + p.member + ' · confidence ' + p.confidence + '%' : p.member,
          status: isUn ? 'Unmatched' : (confirmed ? 'Confirmed' : 'Matched'),
          statusPill: this.pill(isUn ? 'amber' : 'green'),
          avatar: 'width:28px;height:28px;border-radius:50%;flex:none;display:flex;align-items:center;justify-content:center;font-size:11.5px;font-weight:700;background:' + (isUn ? '#FDF6E7' : '#EDF1FF') + ';color:' + (isUn ? '#A9761A' : '#101747'),
          action: isUn ? 'Review' : '',
          actionStyle: isUn ? 'font-size:11.5px;font-weight:700;color:#4563EE;cursor:pointer' : 'display:none',
          go: () => { if (isUn) this.setState({ drawer: { kind: 'match' } }); }
        };
      }),
      reminderCards: reminders.map(r => {
        const badge = this.autoBadge(r.auto);
        return {
          title: r.title, auto: badge.label, autoPill: badge.style, status: r.status, statusPill: this.pill(r.tone),
          note: r.note,
          fields: r.fields.map(f => ({ label: f[0], value: f[1] })),
          wrap: 'background:#fff;border:1px solid ' + (r.id === 'workshop' && this.workshopStatus() === 'needs_review' ? '#F3DFAE' : '#E7EAF1') + ';border-radius:18px;padding:22px',
          buttons: r.buttons.map(b => ({
            label: b[1] === 'schedule' && this.workshopStatus() === 'scheduled' ? 'Scheduled ✓' : b[0],
            style: btn(b[1] === 'schedule' ? (this.workshopStatus() === 'scheduled' ? '#EAF7F0' : '#101747') : (b[1] === 'review' ? '#EDF1FF' : '#EDEFF6'), b[1] === 'schedule' ? (this.workshopStatus() === 'scheduled' ? '#1F8A5B' : '#fff') : (b[1] === 'review' ? '#3F55D6' : '#5A6478')),
            go: () => {
              if (b[1] === 'schedule') {
                if (this.workshopStatus() === 'scheduled') return;
                const n = Object.assign({}, this.state.reminderState); n.workshop = 'scheduled';
                this.setState({ reminderState: n }); this.toast('Workshop reminder scheduled in HighLevel — review count updated');
              } else if (b[1] === 'variants') {
                this.setState({ drawer: { title: 'Approved recurring copy variants', source: 'highlevel', label: r.title, excerpt: 'Variant A: “Office Hours starts in one hour — bring your account questions.”\nVariant B: “One hour until Office Hours — we’ll review live accounts and answer anything.”\nVariant C: “Reminder: Office Hours today. Drop your questions in the thread if you can’t make it live.”', time: 'Approved Aug 12', client: 'Community' } });
              } else if (b[1] === 'review') {
                this.setState({ drawer: { title: 'Workshop reminder copy', source: 'aihq', label: 'Turning leads into venue tours', excerpt: 'Theme supplied by Whitney. Draft: “This week’s workshop is all about turning leads into booked venue tours — the follow-up sequence, the timing, and the exact language that gets a reply. See you there.”', time: 'Draft ready', client: 'Community' } });
              } else {
                this.toast('Opening HighLevel Social Planner — demo');
              }
            }
          }))
        };
      }),
      sessionBadge: this.autoBadge('ai_hq').style, sessionBadgeLabel: this.autoBadge('ai_hq').label,
      sessionPipeline: sessionStages.map(s => ({
        label: s.label, meta: s.meta, status: s.status, statusPill: this.pill(s.tone),
        icon: s.tone === 'green' ? '✓' : (s.tone === 'amber' ? '⚠' : '○'),
        dot: 'width:22px;height:22px;border-radius:7px;flex:none;display:flex;align-items:center;justify-content:center;font-size:10.5px;font-weight:800;background:' + (s.tone === 'green' ? '#EAF7F0' : s.tone === 'amber' ? '#FDF6E7' : '#EDF1FF') + ';color:' + (s.tone === 'green' ? '#1F8A5B' : s.tone === 'amber' ? '#A9761A' : '#3F55D6')
      })),
      publishBtnLabel: st.sessionState.community === 'published' ? 'Session published ✓' : 'Review & publish session',
      publishBtnStyle: 'margin-top:14px;display:inline-flex;padding:10px 16px;border-radius:10px;font-size:12.5px;font-weight:700;cursor:pointer;background:' + (st.sessionState.community === 'published' ? '#EAF7F0' : '#101747') + ';color:' + (st.sessionState.community === 'published' ? '#1F8A5B' : '#fff'),
      publishSession: () => {
        if (st.sessionState.community === 'published') return;
        const n = Object.assign({}, this.state.sessionState); n.community = 'published'; n.internal = 'posted';
        this.setState({ sessionState: n }); this.toast('Session recap published to the member portal — simulated');
      },
      sessionSlackRecap: 'META OFFICE HOURS — SEP 3\n\nAttendance\n' + matched + ' matched\n' + (this.state.matchState.m2 ? 0 : 1) + ' probable\n' + this.unmatchedCount() + ' unmatched\n\nTopics\n• creative fatigue\n• retargeting audiences\n• lead-form quality\n\nFollow-up\n1 account needs separate review',
      internalRecapLabel: st.sessionState.internal === 'posted' ? 'Posted to Slack ✓' : 'Post internal recap',
      internalRecapStyle: btn(st.sessionState.internal === 'posted' ? '#EAF7F0' : '#101747', st.sessionState.internal === 'posted' ? '#1F8A5B' : '#fff'),
      postInternalRecap: () => {
        if (st.sessionState.internal === 'posted') return;
        const n = Object.assign({}, this.state.sessionState); n.internal = 'posted';
        this.setState({ sessionState: n }); this.toast('Internal recap posted to #accelerator-internal — simulated');
      },
      communityAutoPill: this.autoBadge('highlevel').style, communityAutoLabel: this.autoBadge('highlevel').label,
      communityRecap: 'META ADS OFFICE HOURS\nSeptember 3\n\nToday we covered:\n• creative fatigue\n• retargeting audiences\n• lead-form quality\n\nReplay:\n[Watch Recording]\n\nKey takeaways:\n• Check frequency before cost when creative slows\n• Rebuild retargeting audiences monthly\n• Tighten lead forms before increasing spend',
      communityBtnLabel: st.sessionState.community === 'published' ? 'Published to portal ✓' : 'Review & publish',
      communityBtnStyle: btn(st.sessionState.community === 'published' ? '#EAF7F0' : '#101747', st.sessionState.community === 'published' ? '#1F8A5B' : '#fff'),
      publishCommunity: () => {
        if (st.sessionState.community === 'published') return;
        const n = Object.assign({}, this.state.sessionState); n.community = 'published';
        this.setState({ sessionState: n }); this.toast('Community recap published — simulated');
      },
      editCommunity: () => this.toast('Recap opened for editing — demo'),
      bannerPill: this.pill('outline')
    };
  }
  /* ---------- ops watch ---------- */
  opsVals() {
    const st = this.state;
    const btn = (bg, fg) => 'padding:9px 14px;border-radius:10px;font-size:12px;font-weight:700;cursor:pointer;background:' + bg + ';color:' + fg;
    const tabs = [['team', 'Team'], ['waiting', 'Waiting'], ['finance', 'Finance'], ['data', 'Data Quality'], ['routines', 'Routines']];
    const tabCounts = {
      team: this.teamRiskCount(), waiting: this.queueOpen('waiting_client') + 1,
      finance: this.invoiceOpenCount(), data: this.invalidOpenCount(), routines: ''
    };
    const acks = [
      {
        id: 'ack-jacqueline', client: 'Bloom Manor', task: 'Testimonial creative', owner: 'Jacqueline', since: 'No acknowledgement after 23 hours',
        facts: [['Assigned', 'Jacqueline'], ['ClickUp task created', 'Yesterday · 10:14 AM'], ['Slack action posted', 'Yesterday · 10:16 AM'], ['Due', 'Friday']],
        nudge: 'Hey Jacqueline — quick check on the Bloom Manor testimonial creative from yesterday’s strategy call.\n\nIt’s due Friday. Can you react with 👀 once you’ve got it?'
      },
      {
        id: 'ack-carmen', client: 'Rosewood Venue', task: 'Reply to client question', owner: 'Carmen', since: 'No reply after 29 business hours',
        facts: [['Assigned', 'Carmen'], ['Client asked', 'Thursday · 09:20 AM'], ['Slack action posted', 'Thursday · 09:25 AM'], ['SLA', '24–48 business hours']],
        nudge: 'Hey Carmen — Rosewood’s question from Thursday still has no reply on the thread (29 business hours).\n\nCan you take it today, or should it move to Whitney?'
      }
    ];
    const invoices = [
      { id: 'INV-204', client: 'Rosewood Venue', amount: '$1,850', age: '5d', due: 'Aug 30', contact: 'Dana Whitfield · dana@rosewoodvenue.com' },
      { id: 'INV-198', client: 'Harbor House', amount: '$1,750', age: '8d', due: 'Aug 27', contact: 'Elena Park · elena@harborhouse.com' }
    ];
    const invState = (id) => st.invoiceState[id] || (id === 'INV-204' ? 'draft_pending' : 'needs_review');
    const invLabel = { draft_pending: 'Draft reminder', needs_review: 'Needs review', draft_ready: 'Draft ready', handled: 'Handled' };
    const invoiceDetail = invoices.find(i => i.id === st.invoiceId);
    const invalids = [
      { id: 'iq1', name: 'Jessica Morgan', role: 'New lead · requested the venue-tour guide', entered: 'jessica@gmail.con', validity: 'Undeliverable', suggestion: 'jessica@gmail.com', confidence: 'High', when: 'Flagged 08:10' },
      { id: 'iq2', name: 'Priya Raman', role: 'New lead · requested pricing sheet', entered: 'priya@rmail', validity: 'Risky · unverifiable', suggestion: 'No safe correction suggested', confidence: 'Low', when: 'Flagged 08:10', lowConfidence: true }
    ];
    const routines = [
      { title: 'Google Office Hours host checklist', system: 'clickup', cadence: 'Weekly · Thursday · owner Carmen', status: 'Recurring', checklist: ['Host Zoom session', 'Complete attendance record', 'Post internal recap'], note: 'ClickUp recurring task — no custom AI required.' },
      { title: 'Meta Office Hours host checklist', system: 'clickup', cadence: 'Weekly · Thursday · owner Carmen', status: 'Recurring', checklist: ['Host Zoom session', 'Complete attendance record', 'Post internal recap'], note: 'ClickUp recurring task — roll-call completion lives in the checklist.' },
      { title: 'Google Office Hours reminder', system: 'highlevel', cadence: 'Weekly · 1 hour before', status: 'Scheduled', checklist: [], note: 'Scheduled in HighLevel Social Planner to the Community channel.' },
      { title: 'Meta Office Hours reminder', system: 'highlevel', cadence: 'Weekly · 1 hour before', status: 'Scheduled', checklist: [], note: 'Approved recurring copy variants — no weekly approval needed.' },
      { title: 'Q&A reminder', system: 'highlevel', cadence: 'Every other week · 1 hour before', status: 'Scheduled', checklist: [], note: 'Recurring Community series behaviour needs production validation in the WIA tenant; otherwise pre-schedule each instance.' },
      { title: 'Workshop reminder', system: 'ai_assisted', cadence: 'Every other week · theme changes', status: 'Needs review', checklist: [], note: 'Theme-specific copy is drafted for review, then scheduled in HighLevel.' },
      { title: 'Monday overdue digest', system: 'ai_hq', cadence: 'Monday · 08:30 · ClickUp → Slack', status: 'Scheduled', checklist: [], note: 'Deterministic overdue query; AI only groups and shortens the digest.' },
      { title: 'Invalid-email verification', system: 'highlevel', cadence: 'On workflow entry', status: 'Active', checklist: [], note: 'Native HighLevel Email Verification branches risky/invalid contacts to human review.' },
      { title: 'Invoice exception', system: 'native_highlevel_ai', cadence: 'On invoice status change', status: 'Active', checklist: [], note: 'Native HighLevel event → AI HQ personal Gmail follow-up. Scheduled API query is the fallback.' }
    ];
    const waiting = [
      {
        kind: 'Waiting on client', name: 'Rosewood Venue', item: 'Requested gallery assets', age: '12 days', tone: 'red',
        impact: 'Client recap complete\nCreative work waiting', btnLabel: 'Draft follow-up',
        go: () => this.go('inbox', { inboxQueue: 'waiting_client', emailId: 'e10' }),
        secondaryLabel: 'Open client', secondaryGo: () => this.go('clients', { clientId: 'rosewood', clientTab: 'activity' })
      },
      {
        kind: 'Waiting on client', name: 'Bloom Manor', item: 'October gallery assets', age: '5 days', tone: 'amber',
        impact: 'New creative cannot be finalized', btnLabel: 'Draft follow-up',
        go: () => this.go('inbox', { inboxQueue: 'waiting_client', emailId: 'e9' }),
        secondaryLabel: 'Open client', secondaryGo: () => this.go('clients', { clientId: 'bloom', clientTab: 'activity' })
      },
      {
        kind: 'Waiting on internal team', name: 'Jacqueline', item: 'Bloom Manor testimonial creative', age: 'Overdue 1 day', tone: 'red',
        impact: 'Client-facing commitment from the Sep 2 call\nNo Slack acknowledgement', btnLabel: 'Preview nudge',
        go: () => this.setState({ opsTab: 'team' }),
        secondaryLabel: 'Open execution pack', secondaryGo: () => this.go('meetings', { meetingId: 'bloom-strategy' })
      },
      {
        kind: 'Waiting on internal team', name: 'Whitney', item: 'Harbor House creative swap approval', age: '26 business hrs', tone: 'amber',
        impact: 'Team is blocked until approval', btnLabel: 'Preview nudge',
        go: () => this.setState({ opsTab: 'team' }),
        secondaryLabel: 'Open thread', secondaryGo: () => this.go('inbox', { inboxQueue: 'team_reply_due', emailId: 'e8' })
      }
    ];
    return {
      isOps: st.screen === 'ops',
      opsTabs: tabs.map(t => {
        const active = st.opsTab === t[0];
        return {
          label: t[1], count: tabCounts[t[0]] || '', go: () => this.setState({ opsTab: t[0] }),
          style: 'display:inline-flex;align-items:center;gap:7px;padding:9px 15px;border-radius:10px;font-size:12.5px;font-weight:700;cursor:pointer;border:1px solid ' + (active ? '#5874F7' : '#E7EAF1') + ';background:' + (active ? '#101747' : '#fff') + ';color:' + (active ? '#fff' : '#5A6478'),
          countStyle: 'font-family:JetBrains Mono,monospace;font-size:10.5px;opacity:.75'
        };
      }),
      opsIsTeam: st.opsTab === 'team', opsIsWaiting: st.opsTab === 'waiting', opsIsFinance: st.opsTab === 'finance',
      opsIsData: st.opsTab === 'data', opsIsRoutines: st.opsTab === 'routines',
      ackCards: acks.map(a => {
        const done = st.nudgeState[a.id];
        return {
          head: done === 'acknowledged' ? 'Acknowledged' : (done === 'nudged' ? 'Nudge posted' : 'No acknowledgement'),
          headPill: this.pill(done ? 'green' : 'red'),
          auto: this.autoBadge('ai_hq').label, autoPill: this.autoBadge('ai_hq').style,
          client: a.client, task: a.task, since: done ? 'Cleared' : a.since, nudge: a.nudge,
          facts: a.facts.map(f => ({ label: f[0], value: f[1] })),
          buttons: done ? [{ label: done === 'acknowledged' ? 'Marked acknowledged ✓' : 'Nudge posted to Slack ✓', style: btn('#EAF7F0', '#1F8A5B'), go: () => { } }] : [
            { label: 'Preview & approve nudge', style: btn('#101747', '#fff'), go: () => { const n = Object.assign({}, this.state.nudgeState); n[a.id] = 'nudged'; this.setState({ nudgeState: n }); this.toast('Nudge posted to Slack — simulated'); } },
            { label: 'Simulate 👀 reaction', style: btn('#EDF1FF', '#3F55D6'), go: () => { const n = Object.assign({}, this.state.nudgeState); n[a.id] = 'acknowledged'; this.setState({ nudgeState: n }); this.toast('Acknowledgement event received from Slack — item resolved'); } },
            { label: 'Snooze', style: btn('#EDEFF6', '#5A6478'), go: () => this.toast('Snoozed until tomorrow morning') },
            { label: 'Mark acknowledged manually', style: btn('#EDF1FF', '#3F55D6'), go: () => { const n = Object.assign({}, this.state.nudgeState); n[a.id] = 'acknowledged'; this.setState({ nudgeState: n }); this.toast('Marked acknowledged — team risk count updated'); } }
          ]
        };
      }),
      digestAutoPill: this.autoBadge('clickup').style, digestAutoLabel: this.autoBadge('clickup').label,
      digestStats: [{ value: 6, label: 'overdue tasks' }, { value: 3, label: 'team members' }, { value: 4, label: 'client accounts' }],
      digestOwners: [['Carmen', 2], ['Jacqueline', 3], ['Gisselle', 1]].map(o => ({
        name: o[0], count: o[1], initial: this.team[o[0]],
        bar: 'height:8px;border-radius:5px;width:' + (o[1] / 3 * 100) + 'px;background:linear-gradient(90deg,#5874F7,#8FA4FB)'
      })),
      digestBtnLabel: st.digestState === 'posted' ? 'Digest posted to Slack ✓' : 'Review Slack digest',
      digestBtnStyle: btn(st.digestState === 'posted' ? '#EAF7F0' : '#101747', st.digestState === 'posted' ? '#1F8A5B' : '#fff'),
      reviewDigest: () => {
        if (st.digestState === 'posted') { return; }
        this.setState({
          drawer: {
            title: 'Monday overdue digest — Slack preview', source: 'slack', label: '#team-ops',
            excerpt: 'Overdue client-facing tasks — Monday review\n\nJacqueline (3)\n• Bloom Manor testimonial creative — 1d overdue\n• Harbor House creative swap — 2d overdue\n• Bloom Manor asset refresh — 4d overdue\n\nCarmen (2)\n• Google keyword exclusions — 1d overdue\n• Meta audience refresh — 3d overdue\n\nGisselle (1)\n• Rosewood recap follow-up — 1d overdue',
            time: 'Every Monday · 08:30', client: '4 client accounts', confirm: 'digest'
          }
        });
      },
      monitorRows: [
        { title: 'Complete landing-page handoff', meta: 'Jacqueline · from Sep 2 strategy call', status: (st.taskState || {}).t1 === 'complete' ? 'Complete' : ((st.packState || {})['bloom-strategy'] ? 'Created · monitoring' : 'Not yet created'), tone: (st.taskState || {}).t1 === 'complete' ? 'green' : 'blue' },
        { title: 'Review keyword exclusions', meta: 'Carmen · acknowledged in Slack', status: (st.taskState || {}).t2 === 'complete' ? 'Complete' : 'Acknowledged', tone: 'green' },
        { title: 'Update testimonial creative', meta: 'Jacqueline · no acknowledgement', status: st.nudgeState['ack-jacqueline'] ? 'Acknowledged' : 'Overdue 1 day', tone: st.nudgeState['ack-jacqueline'] ? 'green' : 'red' },
        { title: 'Send client recap', meta: 'Gisselle · draft approved', status: 'Complete', tone: 'green' }
      ].map(r => ({
        title: r.title, meta: r.meta, status: r.status, statusPill: this.pill(r.tone),
        dot: 'width:8px;height:8px;border-radius:50%;flex:none;background:' + (r.tone === 'green' ? '#2E9E6B' : r.tone === 'red' ? '#D94C4C' : '#5874F7')
      })),
      waitingCards: waiting.map(w => ({
        kind: w.kind, name: w.name, item: w.item, age: w.age, impact: w.impact,
        kindPill: this.pill(w.kind === 'Waiting on client' ? 'amber' : 'blue'),
        ageStyle: 'margin-left:auto;font-size:12px;font-weight:700;color:' + (w.tone === 'red' ? '#C63F3F' : '#A9761A'),
        btnLabel: w.btnLabel, btnStyle: btn('#101747', '#fff'), go: w.go,
        secondaryLabel: w.secondaryLabel, secondaryGo: w.secondaryGo
      })),
      financeAutoPill: this.autoBadge('native_highlevel_ai').style, financeAutoLabel: this.autoBadge('native_highlevel_ai').label,
      ackRulePill: this.pill('slate'),
      ackRules: [
        { label: 'Owner reacts with the configured acknowledgement emoji on the action message' },
        { label: 'Owner replies in the action thread' },
        { label: 'Linked ClickUp task moves out of Open' },
        { label: 'Reviewer marks it acknowledged by hand' }
      ],
      financeKpis: [
        { label: 'Overdue invoices', value: this.invoiceOpenCount(), sub: 'Deterministic HighLevel rule' },
        { label: 'Amount outstanding', value: this.invoiceOpenCount() === 2 ? '$3,600' : (this.invoiceOpenCount() === 1 ? '$1,750' : '$0'), sub: 'Across ' + this.invoiceOpenCount() + ' clients' },
        { label: 'Oldest overdue', value: '8d', sub: 'Harbor House · INV-198' },
        { label: 'Personal reminders ready', value: Object.keys(st.invoiceState).filter(k => st.invoiceState[k] === 'draft_ready').length, sub: 'Gmail drafts awaiting review' }
      ],
      invoiceRows: invoices.map(i => {
        const s = invState(i.id);
        const active = st.invoiceId === i.id;
        return {
          client: i.client, invoice: i.id, amount: i.amount, age: i.age,
          status: invLabel[s], statusPill: this.pill(s === 'handled' ? 'green' : (s === 'draft_ready' ? 'blue' : (s === 'draft_pending' ? 'amber' : 'outline'))),
          wrap: 'display:grid;grid-template-columns:1fr .8fr .7fr .5fr .9fr;gap:10px;align-items:center;padding:14px;border-top:1px solid #F0F2F8;cursor:pointer;background:' + (active ? '#F8FAFF' : 'transparent'),
          go: () => this.setState({ invoiceId: i.id })
        };
      }),
      hasInvoiceDetail: !!invoiceDetail,
      invDetail: invoiceDetail ? {
        invoice: invoiceDetail.id, client: invoiceDetail.client,
        facts: [
          { label: 'Amount', value: invoiceDetail.amount }, { label: 'Due date', value: invoiceDetail.due },
          { label: 'Status', value: 'Unpaid · not void' }, { label: 'Age', value: invoiceDetail.age + ' overdue' },
          { label: 'Last standard reminder', value: 'Sent by HighLevel' }, { label: 'Contact', value: invoiceDetail.contact },
          { label: 'Trigger', value: 'HighLevel invoice workflow event' },
          { label: 'Payment link', value: invoiceDetail.id === 'INV-198' ? 'Unavailable from source payload' : 'Available in payload' }
        ],
        draft: 'Hi ' + invoiceDetail.contact.split(' ')[0] + ',\n\nJust a quick personal note — invoice ' + invoiceDetail.id + ' (' + invoiceDetail.amount + ') is showing as unpaid and is now ' + invoiceDetail.age + ' past due.\n\nIf it’s easier, here’s the payment link:\n[Open invoice in HighLevel]\n\nIf it’s already scheduled, ignore me entirely — just wanted to make sure it hadn’t slipped through.\n\nThank you!',
        buttons: [
          {
            label: invState(invoiceDetail.id) === 'draft_ready' || invState(invoiceDetail.id) === 'handled' ? 'Personal draft ready ✓' : 'Create personal draft',
            style: btn(invState(invoiceDetail.id) === 'draft_ready' || invState(invoiceDetail.id) === 'handled' ? '#EAF7F0' : '#101747', invState(invoiceDetail.id) === 'draft_ready' || invState(invoiceDetail.id) === 'handled' ? '#1F8A5B' : '#fff'),
            go: () => {
              const n = Object.assign({}, this.state.invoiceState);
              if (n[invoiceDetail.id] === 'handled') return;
              n[invoiceDetail.id] = 'draft_ready';
              const es = Object.assign({}, this.state.emailState);
              this.setState({ invoiceState: n, emailState: es });
              this.toast('Personal reminder drafted in Gmail — Inbox finance queue updated');
            }
          },
          { label: 'Open in HighLevel', style: btn('#EDEFF6', '#5A6478'), go: () => this.toast('Opening invoice in HighLevel — demo link') },
          { label: invoiceDetail.id === 'INV-198' ? 'Paste payment link' : 'Copy payment link', style: btn('#EDEFF6', '#5A6478'), go: () => this.toast(invoiceDetail.id === 'INV-198' ? 'Payment link unavailable from the source payload — paste it manually' : 'Payment link copied from the invoice payload — demo') },
          { label: 'Mark handled', style: btn('#EDF1FF', '#3F55D6'), go: () => { const n = Object.assign({}, this.state.invoiceState); n[invoiceDetail.id] = 'handled'; this.setState({ invoiceState: n }); this.toast(invoiceDetail.id + ' marked handled'); } }
        ]
      } : { invoice: '', client: '', facts: [], draft: '', buttons: [] },
      closeInvoice: () => this.setState({ invoiceId: null }),
      invalidCards: invalids.map(i => {
        const s = st.invalidState[i.id];
        const resent = st.resentState[i.id];
        return {
          name: i.name, role: i.role, entered: i.entered, validity: i.validity, suggestion: i.suggestion,
          confidence: i.confidence, when: i.when,
          headPill: this.pill(s === 'corrected' ? 'green' : (s === 'ignored' ? 'neutral' : 'amber')),
          auto: this.autoBadge('highlevel').label, autoPill: this.autoBadge('highlevel').style,
          ai: i.lowConfidence ? 'No AI suggestion' : this.autoBadge('ai_assisted').label,
          aiPill: i.lowConfidence ? this.pill('outline') : this.autoBadge('ai_assisted').style,
          buttons: s ? [{ label: s === 'corrected' ? 'Correction confirmed ✓' : 'Ignored', style: btn('#EAF7F0', '#1F8A5B'), go: () => { } }] : (i.lowConfidence ? [
            { label: 'Open contact', style: btn('#101747', '#fff'), go: () => this.toast('Opening HighLevel contact — verify the address manually') },
            { label: 'Ignore', style: btn('#FDECEC', '#C63F3F'), go: () => { const n = Object.assign({}, this.state.invalidState); n[i.id] = 'ignored'; this.setState({ invalidState: n }); this.toast('Ignored — no change made to the contact'); } }
          ] : [
            { label: 'Use suggestion', style: btn('#101747', '#fff'), go: () => this.setState({ msgModal: { kind: 'email_fix', id: i.id, member: i.name + ' · HighLevel contact', title: 'Confirm change', body: i.entered + '\n→\n' + i.suggestion + '\n\nThis change will not be applied automatically.', note: 'AI HQ never auto-corrects an email address and never silently re-enrolls a lead in an automation.' } }) },
            { label: 'Edit manually', style: btn('#EDEFF6', '#5A6478'), go: () => this.toast('Open the contact in HighLevel to edit manually — demo') },
            { label: 'Open contact', style: btn('#EDEFF6', '#5A6478'), go: () => this.toast('Opening HighLevel contact — demo') },
            { label: 'Ignore', style: btn('#FDECEC', '#C63F3F'), go: () => { const n = Object.assign({}, this.state.invalidState); n[i.id] = 'ignored'; this.setState({ invalidState: n }); this.toast('Ignored — no change made to the contact'); } }
          ]),
          showNext: s === 'corrected',
          steps: [
            { label: 'Email corrected', done: true },
            { label: 'Re-enter lead in material-delivery workflow', done: !!resent },
            { label: 'Confirm material delivered', done: !!resent }
          ].map(x => ({
            label: x.label, icon: x.done ? '✓' : '○',
            dot: 'width:16px;height:16px;border-radius:5px;flex:none;display:flex;align-items:center;justify-content:center;font-size:9.5px;font-weight:800;background:' + (x.done ? '#EAF7F0' : '#F1F3F8') + ';color:' + (x.done ? '#1F8A5B' : '#8A93A6')
          })),
          resentLabel: resent ? 'Materials resent ✓' : 'Mark materials resent',
          resentStyle: 'margin-top:13px;display:inline-flex;' + btn(resent ? '#EAF7F0' : '#101747', resent ? '#1F8A5B' : '#fff'),
          resentGo: () => { const n = Object.assign({}, this.state.resentState); n[i.id] = true; this.setState({ resentState: n }); this.toast('Materials resent and confirmed — demo'); }
        };
      }),
      nativeLegendPill: this.autoBadge('clickup').style, nativeLegendLabel: 'Native Automation',
      aiLegendPill: this.autoBadge('ai_hq').style, aiLegendLabel: this.autoBadge('ai_hq').label,
      routineCards: routines.map(r => {
        const badge = this.autoBadge(r.system);
        return {
          title: r.title, cadence: r.cadence, note: r.note, auto: badge.label, autoPill: badge.style,
          status: r.status, statusPill: this.pill(r.status === 'Needs review' ? 'amber' : (r.status === 'Recurring' || r.status === 'Scheduled' ? 'green' : 'blue')),
          hasChecklist: r.checklist.length > 0, checklist: r.checklist.map(c => ({ label: c }))
        };
      })
    };
  }

  /* ---------- content mine ---------- */
  opportunities = [
    {
      id: 'c1', client: 'Bloom Manor', meeting: 'Strategy Call', ts: '31:42',
      quote: '“We’ve had more venue tours this month than any month this year.”',
      signals: ['Client win', 'Testimonial', 'Marketing insight'],
      recommended: [['Reel', 5], ['Email', 5], ['Carousel', 4], ['Case study', 5]]
    },
    {
      id: 'c2', client: 'Meta Office Hours', meeting: 'Sep 3 session', ts: '12:04',
      quote: '“Creative fatigue shows up in frequency before it shows up in cost.”',
      signals: ['Teaching moment', 'Marketing insight'],
      recommended: [['Reel', 5], ['Carousel', 5], ['Email', 4], ['Case study', 3]]
    },
    {
      id: 'c3', client: 'Rosewood Venue', meeting: 'Monthly Check-in', ts: '22:18',
      quote: '“The tours we’re getting now actually book — that’s the difference.”',
      signals: ['Testimonial', 'Client win'],
      recommended: [['Reel', 4], ['Email', 5], ['Carousel', 4], ['Case study', 4]]
    }
  ];
  packages = {
    reel: 'HOOK\n“More venue tours this month than any month this year.”\n\nSETUP\nThat’s a real quote from a venue owner — and it wasn’t about impressions or reach.\n\nBODY\nMost venues measure the wrong thing. Reach feels good. Tours book weddings.\n\nWhen we rebuilt this account around tour requests, three things changed:\n1. The offer stopped selling the venue and started selling the visit.\n2. The follow-up got faster.\n3. The reporting only tracked tours booked.\n\nCLOSE\nIf your ads aren’t producing tours, they aren’t producing bookings.',
    carousel: 'SLIDE 1\nVanity metrics don’t book weddings.\n\nSLIDE 2\n“More venue tours this month than any month this year.” — real client, this month.\n\nSLIDE 3\nWhat changed: the offer sold the visit, not the venue.\n\nSLIDE 4\nWhat changed: follow-up speed.\n\nSLIDE 5\nWhat changed: reporting tracked tours, not reach.\n\nSLIDE 6\nAsk your marketing one question: how many tours did we book?',
    email: 'SUBJECT\nThe metric that actually books weddings\n\nBODY\nOne of our venue clients said something on a call last week that stuck with me:\n\n“We’ve had more venue tours this month than any month this year.”\n\nNo mention of impressions. No mention of reach. Tours — the thing that turns into a booking.\n\nIf you want the three changes that got them there, they’re in this week’s reel.\n\n— Whitney',
    caption: 'Reach doesn’t book weddings. Tours do.\n\nOne venue client, one month: more tours than any month this year. Three changes got them there — the offer sold the visit, the follow-up got faster, and the reporting only tracked tours.\n\nWhat is your marketing actually measuring?',
    case_study: 'CLIENT\nBoutique wedding venue (Elevate)\n\nCHALLENGE\nStrong reach, inconsistent tour volume.\n\nWHAT WE CHANGED\n• Offer repositioned around booking the visit\n• Faster lead follow-up\n• Reporting reduced to tours booked\n\nRESULT (client-reported, Sep 2 strategy call · 31:42)\n“We’ve had more venue tours this month than any month this year.”\n\nNOTE\nQuantified claims stay linked to the source transcript moment.'
  };
  contentVals() {
    const st = this.state;
    const btn = (bg, fg) => 'padding:9px 14px;border-radius:10px;font-size:12px;font-weight:700;cursor:pointer;background:' + bg + ';color:' + fg;
    const stage = (id) => st.contentStage[id] || 'opportunity';
    const tabs = [['reel', 'Reel Script'], ['carousel', 'Carousel'], ['email', 'Email'], ['caption', 'Caption'], ['case_study', 'Case Study']];
    const stageLabels = { opportunity: 'Opportunity', approved: 'Approved', scripted: 'Scripted', recorded: 'Recorded', repurposed: 'Repurposed', scheduled: 'Scheduled' };
    const counts = { opportunity: 0, approved: 0, scripted: 0, recorded: 0, repurposed: 0, scheduled: 0 };
    this.opportunities.forEach(o => { counts[stage(o.id)] = (counts[stage(o.id)] || 0) + 1; });
    return {
      isContent: st.screen === 'content',
      contentCards: this.opportunities.map(o => {
        const s = stage(o.id);
        const dir = st.direction[o.id];
        return {
          client: o.client, meeting: o.meeting, ts: o.ts, quote: o.quote,
          stage: stageLabels[s], stagePill: this.pill(s === 'opportunity' ? 'outline' : 'green'),
          headPill: this.pill('violet'),
          wrap: 'background:#fff;border:1px solid ' + (st.contentId === o.id ? '#C9D4FA' : '#E7EAF1') + ';border-radius:18px;padding:22px',
          signals: o.signals.map(x => ({ label: x, style: this.pill('outline') })),
          recommended: o.recommended.map(r => ({ label: r[0], stars: '★★★★★'.slice(0, r[1]) + '☆☆☆☆☆'.slice(0, 5 - r[1]) })),
          hasDirection: !!dir, direction: dir || '',
          buttons: [
            { label: dir ? 'Direction added ✓' : 'Add direction', style: btn(dir ? '#EAF7F0' : '#EDEFF6', dir ? '#1F8A5B' : '#5A6478'), go: () => this.setState({ voiceModal: o.id }) },
            {
              label: s === 'opportunity' ? 'Build content package' : 'Open package',
              style: btn('#101747', '#fff'),
              go: () => {
                const n = Object.assign({}, this.state.contentStage);
                if (s === 'opportunity') n[o.id] = 'approved';
                this.setState({ contentStage: n, contentId: o.id });
                if (s === 'opportunity') this.toast('Approved — content package available');
              }
            }
          ]
        };
      }),
      sourceBackedPill: this.pill('blue'),
      packageSource: (this.opportunities.find(o => o.id === st.contentId) || this.opportunities[0]).client + ' · ' + (this.opportunities.find(o => o.id === st.contentId) || this.opportunities[0]).ts,
      contentTabs: tabs.map(t => {
        const active = st.contentTab === t[0];
        return {
          label: t[1], go: () => this.setState({ contentTab: t[0] }),
          style: 'padding:8px 13px;border-radius:9px;font-size:12px;font-weight:700;cursor:pointer;border:1px solid ' + (active ? '#5874F7' : '#E7EAF1') + ';background:' + (active ? '#101747' : '#fff') + ';color:' + (active ? '#fff' : '#5A6478')
        };
      }),
      packageBody: this.packages[st.contentTab] || this.packages.reel,
      openSourceMoment: () => {
        const o = this.opportunities.find(x => x.id === st.contentId) || this.opportunities[0];
        this.setState({ drawer: { title: 'Transcript moment — source', source: 'zoom', label: o.client + ' · ' + o.meeting + ' · ' + o.ts, excerpt: o.quote, time: 'Sep 2', client: o.client } });
      },
      contentPipeline: ['opportunity', 'approved', 'scripted', 'recorded', 'repurposed', 'scheduled'].map(k => ({
        label: stageLabels[k],
        meta: k === 'opportunity' ? 'Found in transcripts' : (k === 'approved' ? 'Whitney approved the angle' : (k === 'scripted' ? 'Reel script drafted' : (k === 'recorded' ? 'Awaiting Whitney recording' : (k === 'repurposed' ? 'Carousel + email built' : 'Queued for publishing')))),
        count: counts[k] || 0, countPill: this.pill(counts[k] ? 'blue' : 'outline'),
        icon: counts[k] ? '●' : '○',
        dot: 'width:22px;height:22px;border-radius:7px;flex:none;display:flex;align-items:center;justify-content:center;font-size:9px;font-weight:800;background:' + (counts[k] ? '#EDF1FF' : '#F1F3F8') + ';color:' + (counts[k] ? '#3F55D6' : '#B3BAC9')
      }))
    };
  }

  /* ---------- settings ---------- */
  settingsVals() {
    const sources = [
      { key: 'gmail', role: 'Primary client communication · hello@…', status: 'Covered', tone: 'green', caps: ['mailbox push notifications', 'threads', 'labels', 'create drafts', 'last event 2m ago'], note: 'Production note: Gmail mailbox watches must be renewed at least every 7 days (daily recommended) and notifications can be delayed, so a history-sync fallback is required.' },
      { key: 'slack', role: 'Primary internal communication', status: 'Partial coverage', tone: 'amber', caps: ['8 authorized channels', '2 private client channels missing', 'reaction + reply events', 'post to authorized channels'], note: 'Production note: history and events are scope- and membership-dependent. AI HQ never claims all-workspace visibility.' },
      { key: 'clickup', role: 'Task ledger · 4 client lists + Ops list', status: 'Covered', tone: 'green', caps: ['create tasks with owner + due date', 'status / assignee webhooks', 'native recurring host tasks', 'webhook health: good'], note: 'Office Hours host checklists stay native ClickUp recurring tasks — no custom recurrence is built.' },
      { key: 'zoom', role: 'Whitney-hosted meetings + Office Hours', status: 'Covered', tone: 'green', caps: ['cloud recording', 'transcript-completed event', 'past-meeting participant report', 'last event: Sep 3'], note: 'Production note: cloud transcription requires a paid plan with audio transcription enabled, the participant API requires Pro or higher, and external participant identity can be incomplete.' },
      { key: 'fathom', role: 'Team meeting source · per-user keys', status: 'Partial coverage', tone: 'amber', caps: ['Gisselle — covered', 'Jacqueline — covered', 'Carmen — covered', 'Whitney — not used (Zoom source)', 'Danielle — key not authorized'], note: 'Production note: Fathom API keys are user-level. A key reaches meetings that user recorded or that were shared to their Team; an admin key does not unlock other users’ unshared meetings.' },
      { key: 'drive', role: 'Meeting archive', status: 'Covered', tone: 'green', caps: ['file into mapped client folders', '11 client folders mapped', '1 mapping unresolved — Harbor House'], note: 'AI HQ files into existing folders only. It does not create onboarding folder structures.' },
      { key: 'highlevel', role: 'Community, invoices, contacts, Accelerator context', status: 'Covered', tone: 'green', caps: ['Community post scheduling (Social Planner)', 'invoice workflow events', 'email verification action', 'contact / member reference'], note: 'Production validation required: confirm the recurring Community series behaves as expected in the WIA tenant, and that the invoice payload exposes the client-facing payment URL.' }
    ];
    return {
      identityAccess: ['ClickUp', 'Slack', 'HighLevel', 'Drive'].map(l => ({ label: l })),
      sourceSettings: sources.map(s => {
        const chip = this.srcChip(s.key);
        return {
          name: chip.label, chip: chip.style, dot: chip.dot, role: s.role,
          status: s.status, statusPill: this.pill(s.tone),
          capabilities: s.caps.map(c => ({ label: c })),
          hasNote: !!s.note, note: s.note
        };
      }),
      scopeChips: ['No onboarding orchestration', 'No ad strategy generation', 'No creative briefs', 'No client ad copy', 'No landing-page work', 'No client performance reporting'].map(l => ({ label: l, style: this.pill('outline') })),
      resetDemo: () => {
        this.setState({
          emailState: {}, taskSel: {}, taskState: {}, packState: {}, actionsComplete: {}, completionApproved: {},
          slackIncluded: {}, recapIncluded: {}, nudgeState: {}, digestState: 'ready', invoiceState: {}, invalidState: {},
          resentState: {}, matchState: {}, rememberMap: {}, memberState: {}, reminderState: {}, sessionState: {}, contentStage: {}, styleCue: null, packExceptions: {},
          direction: {}, askAnswer: null, invoiceId: null, drawer: null, msgModal: null, voiceModal: false
        });
        this.toast('Demo state reset — every count and status is back to the starting point');
      }
    };
  }
  /* ---------- global overlays ---------- */
  paletteDefs = [
    { tag: 'Review', label: 'What needs my review today?', dest: 'Home', go: () => this.go('home') },
    { tag: 'Waiting', label: 'What are we waiting on from clients?', dest: 'Inbox', go: () => this.go('inbox', { inboxQueue: 'waiting_client' }) },
    { tag: 'Team', label: 'Which team actions have not been acknowledged?', dest: 'Ops Watch', go: () => this.go('ops', { opsTab: 'team' }) },
    { tag: 'Meetings', label: 'What did we promise Bloom Manor on the last call?', dest: 'Context', go: () => this.go('clients', { clientId: 'bloom', clientTab: 'overview', askAnswer: 'What did we promise them on the last call?' }) },
    { tag: 'Meetings', label: 'Which meetings still need an execution pack approved?', dest: 'Meetings', go: () => this.go('meetings', { meetingId: null, meetingFilter: 'needs_review' }) },
    { tag: 'Replies', label: 'Which client emails are past the reply expectation?', dest: 'Inbox', go: () => this.go('inbox', { inboxQueue: 'team_reply_due' }) },
    { tag: 'Finance', label: 'Which invoices are overdue?', dest: 'Ops Watch', go: () => this.go('ops', { opsTab: 'finance' }) },
    { tag: 'Data', label: 'Which lead emails are invalid?', dest: 'Ops Watch', go: () => this.go('ops', { opsTab: 'data' }) },
    { tag: 'Members', label: 'Which Accelerator members are disengaged?', dest: 'Accelerators', go: () => this.go('accelerators', { accTab: 'engagement' }) },
    { tag: 'Members', label: 'Which Zoom participants still need identity matching?', dest: 'Accelerators', go: () => this.go('accelerators', { accTab: 'attendance' }) },
    { tag: 'Routines', label: 'Which routines are native automations, not AI?', dest: 'Ops Watch', go: () => this.go('ops', { opsTab: 'routines' }) },
    { tag: 'Sessions', label: 'Is the last Office Hours recap published?', dest: 'Accelerators', go: () => this.go('accelerators', { accTab: 'sessions' }) },
    { tag: 'Content', label: 'Which client-call moments could become WIA content?', dest: 'Growth Signals', go: () => this.go('content') },
    { tag: 'Sources', label: 'What can AI HQ read and write?', dest: 'Settings', go: () => this.go('settings') }
  ];
  globalVals() {
    const st = this.state;
    const d = st.drawer || {};
    const btn = (bg, fg) => 'padding:9px 14px;border-radius:10px;font-size:12px;font-weight:700;cursor:pointer;background:' + bg + ';color:' + fg;
    const q = (st.paletteQ || '').toLowerCase();
    const chip = d.source ? this.srcChip(d.source) : this.srcChip('aihq');
    const mm = st.msgModal || {};
    const contacted = mm.id ? st.memberState[mm.id] === 'contacted' : false;
    return {
      paletteOpen: st.paletteOpen, paletteQ: st.paletteQ,
      stop: (e) => { if (e && e.stopPropagation) e.stopPropagation(); },
      closePalette: () => this.setState({ paletteOpen: false }),
      setPaletteQ: (e) => this.setState({ paletteQ: e.target.value }),
      paletteItems: this.paletteDefs.filter(p => !q || p.label.toLowerCase().indexOf(q) > -1 || p.tag.toLowerCase().indexOf(q) > -1).map(p => ({
        label: p.label, tag: p.tag, dest: p.dest, chip: this.pill('outline'),
        go: () => { this.setState({ paletteOpen: false }); p.go(); }
      })),
      drawerOpen: !!st.drawer,
      drawerIsMatch: d.kind === 'match', drawerIsEvidence: !!st.drawer && d.kind !== 'match',
      drawerTitle: d.kind === 'match' ? 'Unmatched Zoom participants' : (d.title || 'Evidence'),
      drawerMeta: d.kind === 'match' ? 'Meta Office Hours · Sep 3 · identity confirmation required' : (d.client || ''),
      drawerSource: chip.label, drawerChip: chip.style, drawerDot: chip.dot,
      drawerLabel: d.label || '', drawerExcerpt: d.excerpt || '', drawerTime: d.time || '',
      drawerHasConfirm: d.confirm === 'digest',
      drawerConfirmLabel: st.digestState === 'posted' ? 'Digest posted ✓' : 'Approve & post digest',
      drawerConfirm: () => { this.setState({ digestState: 'posted', drawer: null }); this.toast('Monday digest posted to #team-ops — simulated'); },
      closeDrawer: () => this.setState({ drawer: null }),
      matchRows: this.participants.filter(p => p.status === 'unmatched').map(p => {
        const confirmed = !!st.matchState[p.id];
        return {
          raw: p.raw, member: p.member, confidence: p.confidence + '%',
          initial: p.raw.replace('’', '').charAt(0).toUpperCase(),
          status: confirmed ? 'Confirmed' : 'Unmatched', statusPill: this.pill(confirmed ? 'green' : 'amber'),
          avatar: 'width:28px;height:28px;border-radius:50%;flex:none;display:flex;align-items:center;justify-content:center;font-size:11.5px;font-weight:700;background:' + (confirmed ? '#EAF7F0' : '#FDF6E7') + ';color:' + (confirmed ? '#1F8A5B' : '#A9761A'),
          bar: 'height:100%;width:' + p.confidence + '%;background:linear-gradient(90deg,#5874F7,#8FA4FB)',
          note: p.confidence >= 85 ? 'Probable match · Zoom did not return an email for this participant.' : 'Low-confidence match · display name only, no stable account identifier.',
          rememberCheck: (st.rememberMap || {})[p.id] ? '✓' : '',
          rememberBox: 'width:17px;height:17px;border-radius:5px;flex:none;display:flex;align-items:center;justify-content:center;font-size:10px;font-weight:800;color:#fff;border:1.5px solid ' + ((st.rememberMap || {})[p.id] ? '#5874F7' : '#D6DBE8') + ';background:' + ((st.rememberMap || {})[p.id] ? '#5874F7' : '#fff'),
          toggleRemember: () => { const n = Object.assign({}, this.state.rememberMap); n[p.id] = !n[p.id]; this.setState({ rememberMap: n }); },
          buttons: confirmed ? [{ label: 'Attendance counted ✓', style: btn('#EAF7F0', '#1F8A5B'), go: () => { } }] : [
            { label: 'Confirm match', style: btn('#101747', '#fff'), go: () => { const n = Object.assign({}, this.state.matchState); n[p.id] = true; this.setState({ matchState: n }); this.toast((st.rememberMap || {})[p.id] ? 'Identity confirmed and mapping remembered — attendance counted, streak reset' : 'Identity confirmed — attendance counted and engagement streak reset'); } },
            { label: 'Search members', style: btn('#EDEFF6', '#5A6478'), go: () => this.toast('Member search — demo only') },
            { label: 'Mark guest', style: btn('#EDEFF6', '#5A6478'), go: () => { const n = Object.assign({}, this.state.matchState); n[p.id] = true; this.setState({ matchState: n }); this.toast('Marked as guest — excluded from member attendance'); } }
          ]
        };
      }),
      msgModalOpen: !!st.msgModal, msgTitle: mm.title || '', msgMember: mm.member || '',
      msgBody: mm.body || '', msgNote: mm.note || '',
      closeMsgModal: () => this.setState({ msgModal: null }),
      msgButtons: mm.kind === 'email_fix' ? [
        {
          label: 'Confirm correction', style: btn('#101747', '#fff'),
          go: () => {
            const n = Object.assign({}, this.state.invalidState); n[mm.id] = 'corrected';
            this.setState({ invalidState: n, msgModal: null });
            this.toast('Correction confirmed — next step: re-enter the lead in the delivery workflow');
          }
        },
        { label: 'Cancel', style: btn('#EDEFF6', '#5A6478'), go: () => this.setState({ msgModal: null }) }
      ] : (contacted ? [{ label: 'Marked contacted ✓', style: btn('#EAF7F0', '#1F8A5B'), go: () => { } }] : [
        { label: mm.kind === 'at_risk' ? 'Copy for portal DM' : 'Create Gmail draft', style: btn('#101747', '#fff'), go: () => this.toast(mm.kind === 'at_risk' ? 'Copied — send manually from the member portal' : 'Personal email draft created in Gmail — simulated') },
        { label: 'Mark contacted', style: btn('#EDF1FF', '#3F55D6'), go: () => { const n = Object.assign({}, this.state.memberState); n[mm.id] = 'contacted'; this.setState({ memberState: n, msgModal: null }); this.toast(mm.member + ' marked contacted — Accelerator attention updated'); } },
        { label: 'Dismiss', style: btn('#EDEFF6', '#5A6478'), go: () => this.setState({ msgModal: null }) }
      ]),
      voiceModalOpen: !!st.voiceModal,
      closeVoiceModal: () => this.setState({ voiceModal: false }),
      voiceBars: Array.from({ length: 24 }).map((_, i) => ({
        style: 'flex:1;background:#8FA4FB;border-radius:2px;height:' + (30 + ((i * 37) % 60)) + '%;transform-origin:bottom;animation:wiaWave ' + (0.7 + (i % 5) * 0.12).toFixed(2) + 's ease-in-out ' + (i * 0.05).toFixed(2) + 's infinite'
      })),
      useSampleDirection: () => {
        const id = st.voiceModal;
        const n = Object.assign({}, this.state.direction);
        n[id] = 'Focus the angle on why venues should care about booked tours instead of vanity metrics. Keep it practical and conversational.';
        this.setState({ direction: n, voiceModal: false, contentId: id });
        this.toast('Voice direction attached — package rewritten to Whitney’s angle');
      },
      toastOpen: !!st.toast, toastMsg: st.toast || ''
    };
  }
  /*END*/
}
