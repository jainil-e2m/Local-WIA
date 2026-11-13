# Tab 2 — Client Portfolio (and the client record)

**Status:** Draft · P1–P4 decided 22 Oct, P10–P12 decided 26 Oct 2026 · mockup updated 26 Oct · Stage 1
**Labels:** **[Agreed]** = already decided (KB-CH-05…69 / functional requirements). **[Proposed]** = new in this draft. **[Stage 2/3]** = shown as *Coming soon* in release 1 (data is still backfilled before launch [Agreed]).

---

## 1. What this tab is for

**One question:** *Who are we looking after, and what do I need to know about this client right now?*

It has two levels:
1. **Portfolio** — the list of client businesses: where to look next.
2. **Client record** — one maintained page per business, in sub-tabs. This is the "agency brain" Whitney asked for: a new account manager should be able to read it and take over without a catch-up call.

The Action Register answers "what's owed". The client record answers "who is this client, what's happened, and where do things stand". Both read the same action records; the record never keeps a second copy [Agreed].

---

## 2. Who uses it, day to day

| Person / role | When | What they need |
|---|---|---|
| **Account / ads managers** | Before touching an account, after a gap | "Where does this client stand and what's outstanding?" in under a minute (Carmen's "everything… outstanding" ask to Viktor today) |
| **Whitney** | Weekly, and before her own calls | Which clients need her attention; what was agreed; the client's voice and goals |
| **Ops (Gisselle)** | Onboarding a new client, ongoing | Add the client, link their Slack/Drive/ClickUp/LeadLock, watch onboarding progress |
| **Anyone writing for the client** (ads, landing pages, emails) | When drafting | The client's audience, offer, voice and proof: the "Client Marketing Profile" WIA's playbooks expect |
| **New hire / cover** | Handover | The handover brief |

---

## 3. Core model [Agreed]

- **One client = one business.** A business can have several **engagements** (e.g. Elevate retainer + LeadLock). Engagements are not duplicate clients.
- Contacts, Slack channels, Drive folders, ClickUp lists, LeadLock locations and calendars are **linked accounts**, not the client itself.
- **Related businesses** can share a channel or a call (Funktastic Productions and DJ Hybrid share a Slack channel but have separate LeadLock locations). Evidence is linked to each business it concerns.
- **WIA adds clients manually.** A new folder, email or payment never creates a client by itself.

**WIA's engagement types** (from their public pricing): Elevate retainer (Google + Meta management), LeadLock (setup + monthly), Google Search Accelerator, Meta Ads Accelerator, Accelerator bundle. Accelerator clients also belong to a **programme**.

---

# Part A — Portfolio (list view)

### A1. Header and controls
| Component | Notes |
|---|---|
| Heading | "Client Portfolio" with a one-line description; **Add client** on the right (P11) |
| **My clients · All clients** [Decided, P4] | Same pattern as the Action Register: *My clients* by default, *All* for ops/admins. Needs an **account owner** per client (see A2) |
| Search | Business name, contact name, email, location, alias (e.g. Dogwood ↔ Meriwether Manor). In the card layout this is the header search (Ctrl/⌘ K), not a field on the page (P11) |
| Filters | Service type · lifecycle stage · account owner (All clients only) · health category |
| Sort | Most overdue first, then A–Z (fixed in the card layout, P11) |
| Card / list toggle | Same records either way [Agreed] |
| **Add client** [Agreed: manual creation] | Opens the add-client flow (A4) |

### A2. Client card / list row
| Field | Rule | Status |
|---|---|---|
| **Logo banner** | The client's logo on a light tint of its own colour. Taken from the **Drive brand folder**, else the **logo in the primary contact's email signature**; never scraped from the website (outside approved intake). If neither exists: striped banner marked *Logo pending*, initials still shown. Source file and date kept; a person can replace it | Decided (P10) |
| Initials circle and *…* menu | Initials overlap the banner. Menu: open record, open actions, prepare for the next call, copy Slack channel | Decided (P11) |
| Name, category, location | Reviewed business record | Agreed |
| **Engagement chips** | e.g. `Elevate` `LeadLock`, each with its own start date | Agreed (multiple engagements) |
| **Lifecycle stage** | Onboarding · Active · Paused · Offboarding. Onboarding shows the ClickUp phase (Full Service / LeadLock phase fields) | Decided (P4); stage names to confirm (P6) |
| **Account owner** | The WIA person responsible for the relationship | Decided (P4). Names from WIA (P5) |
| Open actions | Card shows three stats: **Engagements · Open actions · Overdue** (overdue in red). The *WIA owes · client owes* split lives in the record's Commitments. Same rules as the register. Not *Open invoices*: finance is admins-only (F2) | Agreed; card stats decided (P11) |
| **Next call** | Date, type, host. "None scheduled" vs "Calendar unavailable" are different | Agreed |
| **Last contact** | "6 days ago · Gmail". Replaces the mock's 12-week sparkline, which has no agreed definition | Proposed |
| **Health badge** | Keeps its place on the card but reads **Coming soon** until Health & Sentiment (Stage 3) defines it. No interim judgement. The mockup shows the Stage 3 state: the category with an icon and its causes on hover, **never a numeric score** (no agreed combined score) | Decided (P1) |
| **Record coverage** | "History from Mar 2026 · 7 of 8 sources linked", not a % (the mock's % has no definition). Shown in the record (Accounts & sources), not on the card (P11) | Proposed |
| Next call, last contact | On the card before 26 Oct; now in the list view (next call) and the record (P11) | Agreed |

### A3. What the list must not do
- Show a "healthy / needs attention" judgement before Health is defined (Stage 3). The badge says *Coming soon* (P1) [Agreed: no unsupported assessments].
- Show 0 when a source isn't connected. "Unknown" and "0" are different [Agreed].

### A4. Add client flow [Agreed requirement, Proposed design]
1. **Business:** name, aliases, category, location, timezone.
2. **Engagements:** type, start date, programme (accelerators), account owner.
3. **Contacts:** names, roles, emails (used to match Gmail/Calendar/Fathom).
4. **Link sources:** Slack channel(s), Drive folder, ClickUp list(s), LeadLock location, calendar matching rule. The KB **suggests** matches; a person confirms each one.
5. **Start backfill.** Progress shows on the record's *Accounts & sources* sub-tab (B9).

---

# Part B — Client record

### B0. Record header (on every sub-tab)
| Component | Notes |
|---|---|
| Name, engagement chips, lifecycle, account owner | As on the card |
| **Engagement switch** | *All engagements* (default) · Elevate · LeadLock… Filters goals, commitments, invoices and attendance to one engagement [Agreed] |
| **Three dates, not one** | *Client since* (engagement start) · *Earliest evidence* · *Processed through*. The mock uses one "since" for all three [Agreed] |
| **Quick links** [Proposed] | Open the Slack channel · Drive folder · ClickUp list · LeadLock account (opens even before LeadLock data is readable [Agreed]) |
| Prepare for the call | Opens the next call's brief (Call Prep is Stage 2 → link shows *Coming soon* until then) |
| Related businesses | e.g. Funktastic ↔ DJ Hybrid |

### Sub-tab list
| # | Sub-tab | Release 1 | Notes |
|---|---|---|---|
| B1 | **Now** | Yes | Landing sub-tab |
| B2 | **Profile** (Client Marketing Profile) | Yes | |
| B3 | **History** | Yes | |
| B4 | **Handover brief** | Yes | |
| B5 | **Commitments** | Yes | Same records as the register |
| B6 | **Meetings** | Yes | |
| B7 | **Invoices & terms** | Coming soon [Stage 3]; **admins only** (F2) | Data backfilled now. Condensed layout (P12) |
| B8 | **Attendance** | Accelerator clients only | |
| B9 | **Accounts & sources** | Yes (decided, P4) | New |
| B10 | **Support** | Yes (decided, P4) | Moved out of Profile. Coverage disclosed |
| — | Lead outcomes | Stays in Profile, shown as *Unavailable* | Blocked by LeadLock access |

---

### B1. Now — *"Where do things stand this week?"*
| Component | Content | Status |
|---|---|---|
| **Current picture** | 2–3 sentences: what's happening, what's blocked, what the client last asked for. Each sentence cites its source | Agreed content; method decided (P2), see below |
| **This week's focus** | One priority | Same method |
| **What changed since you last looked** | New messages, meetings, actions and corrections since *your* last visit; "Mark as read" | Agreed (per-user read state, KB-CH-51) |
| **Commitments snapshot** | WIA owes / client owes / overdue, top items, link to B5 | Agreed |
| **Next call** | Type, date, host, link to brief | Agreed |
| **Onboarding progress** (onboarding clients only) | Phase, steps done/left, what's waiting on the client | Proposed (from ClickUp phase fields) |
| **Latest client signal** | Most recent direct client words (email/Slack/call), quoted with date | Proposed |
| **Record limits** | "No transcripts before Jun 2026", "LeadLock data unavailable" | Agreed |

**How the narrative stays fresh (decided, P2): KB drafts, owner approves.**
- The KB drafts a new *Current picture* and *Focus* after each client call, new client message or material action change. Every sentence cites its source.
- The account owner sees **"New draft waiting"** and can approve, edit or discard it. Until then, the last approved version stays visible.
- Shown as: *Approved by Jacqueline · 8 Oct* or *Draft · not yet approved*. Once something newer arrives, the approved version is marked **Stale**.
- Edits by the owner are kept; the next draft starts from the approved text, not from scratch.
- Open point: how long a draft may wait before ops is nudged (proposed: 2 business days).

### B2. Profile — *"Who is this client?"*
Structured as WIA's own **Client Marketing Profile** (decided, P3): the per-client record all three WIA playbooks (Google, Meta, Landing Page) say every task starts from, but which nothing currently defines.

| Section | Fields | Typical source |
|---|---|---|
| **Business** | What they do, story/origin, location, service area, aliases | Onboarding / positioning questionnaire |
| **Offer** | Packages, price points, minimums, capacity (e.g. "one wedding per weekend"), availability | Questionnaire, calls |
| **Ideal client** | Who their couples are, budget, what they care about, objections | Questionnaire, calls |
| **Differentiators & proof** | What sets them apart, reviews, awards, results to cite | Questionnaire, Drive brand folder |
| **Voice** | Tone, words to use / avoid, approved examples | Questionnaire, approved copy |
| **Goals** | Per engagement: what success means (e.g. "qualified tours, not more forms") | Questionnaire, strategy calls |
| **People** | Contacts, roles, emails, who approves what; WIA team on the account | Questionnaire, Gmail, ClickUp |
| **Engagements** | Type, start, programme, current phase; signing date when evidenced | WIA registry, Dubsado emails |
| **LeadLock account** | Link to the location | Agreed addition |
| **Lead outcomes** | Inquiries, tours, bookings by period | Agreed addition; **blocked** (LeadLock reads denied) → *Unavailable* |

**The same 16 fields for every client** (decided 6 Nov), so gaps show:

| Section | Fields |
|---|---|
| Business | Who they are · Category · Location & service area |
| Offer | Packages & pricing · Capacity & availability · Minimums & policies |
| Ideal client | Who their couples are · Budget · What couples worry about |
| Differentiators & proof | What sets them apart · Proof to cite |
| Voice | Tone · Words to use · Words to avoid |
| Goals | What success means · How WIA will judge it |

- **Empty fields.** An empty field says "Not in the record yet" and can be added to the next call's questions. The header shows "N of 16 filled" and what's missing.
- **Questionnaire answers.** Until the KB's profile reading fills a field, a questionnaire answer fills the field its question asks about, word for word and flagged unreviewed. Answers that fit no field stay in the questionnaire (its source link); they are not dumped into the profile.

**Every field carries:** its source link, date, and one of WIA's five labels: *Documented client fact · Voice of customer · Strategic interpretation · Ads data · WIA benchmark* (decided, P3; labels from WIA's playbooks). Support issues have their own sub-tab (B10). Editors can propose a correction; resolvers apply it; a reviewed value survives re-extraction [Agreed]. When two sources disagree, both show and the item goes to review [Agreed].

Leave out sensitive questionnaire sections (logins, tax details) [Agreed in Drive scope].

### B3. History — *"What has happened on this account, and when?"* [Defined 6 Nov]
Three layers, from exact to judged:

| Layer | What it shows | Built by |
|---|---|---|
| **Milestones** (diamonds above the lanes) | Onboarding started, onboarding or kickoff call, onboarding complete; later campaigns live, renewal, owner change | Rule (ClickUp onboarding lists, calendar titles); KB reading for "campaigns live" and similar |
| **The shape** (six lanes of balls) | Every event, merged, on one timeline | Rule |
| **Moments that shaped the account** | The 5–15 events that explain how the account got here, each with why it mattered and its sources | KB reading (AI skill `history_moments`), weekly and after new meeting digests |
| **All activity** | Every merged event, newest first, by month | Rule |

**What a ball is, per lane.** A ball is never one raw message or file:
- **Onboarding**: a setup step done, or the onboarding checklist created (ClickUp onboarding lists, the questionnaire in Drive).
- **Communication**: one conversation on one day (an email thread or a Slack thread).
- **Meetings**: one meeting: its invite, recording and transcript together.
- **Commitments**: a commitment made (a task created or an action agreed).
- **Work delivered**: work finished that day.
- **Commercial** (admins only): an agreement signed or a payment received.

On long ranges, the track groups each lane by week (up to 2 years) or month; the All activity list keeps every event.

**How a ball is drawn:**
- Size: 1 item, 2–4, 5 or more.
- Gold: the client wrote. Blue: only WIA wrote.
- Hollow: a meeting with no transcript.
- Red ring: a date was missed.

Selecting a ball lists what it holds, with sources.

**Filters:** period, lane, since the last call. Gaps are shown honestly: no records ≠ nothing happened.

### B4. Handover brief — *"Take over this account without a catch-up call."* [Defined 6 Nov]
For the incoming owner or cover. It is one page, and every section says where it comes from:
- **From the record**: rebuilt exactly from the data.
- **KB draft**: written by the KB and approved by the account owner.
- **Record + KB reading**: record facts plus what the KB read in calls and email.

| # | Section | Content | Origin |
|---|---|---|---|
| 1 | The account in brief | Who they are, what WIA does for them, where it stands, in 2–3 sentences | KB draft |
| 2 | What we do for them | Engagements (type, since, phase); what's usually included (confirm against the signed agreement); the meeting rhythm (from calendar series); the WIA team | Record |
| 3 | Where things stand | Current focus; onboarding progress; last meeting and its summary; next meeting | Record + KB |
| 4 | What's owed | WIA owes / client owes, overdue first, top 5 each | Record |
| 5 | Agreements still in force | Decisions from meetings that still bind the work, with dates | Record + KB |
| 6 | People and how to work with them | Contacts, roles, preferences | Record + KB |
| 7 | Watch-outs | Overdue items, unanswered client messages, open support issues, deadline conflicts, sensitive topics | Record + KB |
| 8 | What this brief can't tell you | Missing sources and periods | Record |

**Side card, "Before you start":** a first-week checklist built from the record:
- the Slack channel, the Drive folder, the ClickUp list and LeadLock access;
- introduce yourself to the main contact;
- read the last meeting;
- join the next call.

**Actions:** Rebuild · Copy · Download (Markdown) · Send on Slack (review-before-send). The brief shows when it was built and how many record changes happened since.

### B5. Commitments — *"What's owed on this account?"*
The Action Register filtered to this client [Agreed: no second register]. Toggle: *All · What we owe them · What we need from them*. Same rows, drawer, Done/Verified rules, Snooze, and **Post to #client channel** from the register.

### B6. Meetings — *"What did we discuss and agree?"*
| Component | Notes | Status |
|---|---|---|
| Past meetings list | Date, **call type** (strategy, onboarding, kickoff, creative review, office hours), attendees, source (Fathom / Zoom / Drive archive) | Agreed; call type matters (Viktor's known weakness) |
| Per meeting | Summary, decisions, asks, commitments created (linked to actions), transcript excerpts with timestamps | Agreed |
| Transcript state | Available · summary only · recording link only · not found. A known meeting stays listed even without a transcript | Agreed |
| Upcoming | Next scheduled calls, link to brief (Stage 2) | Agreed |
| Filter | By call type, period | Proposed |
| Shared meetings | A programme office hour shows only this client's parts | Agreed |

### B7. Invoices & terms — *Coming soon [Stage 3]*, admins only
**Question it answers (P12):** *Is this client up to date, what's billed next, and what did they sign?*
1. **Standing line:** one headline (overdue with amount and a *Chase…* button · nothing overdue but an invoice is missing · up to date · *Can't confirm yet* when only alert emails exist · no records), then Billing, Next invoice and Paid to date (reconciled only, stating how many were left out).
2. **Invoices** (compact rows with basis badges; a missing invoice flagged at the top; five then *Show all*) **beside Agreements & terms** (one card per current agreement, billing plan and instalments folded in, *What's included* collapsed, superseded agreements behind *Show earlier*).
3. **Activity:** one timeline filtered by All · Invoices & payments · Reminders & chases · Agreements. Chase history is the Reminders & chases filter.

Before Stage 3, release 1 shows a *Coming soon* panel to admins. Signing and payment **events** (from Dubsado emails) still appear in History (Commercial lane) and the engagement's signing date in Profile [Proposed]. No balances or "overdue invoice" claims until reconciled [Agreed].

### B8. Attendance — *accelerator clients only*
| Component | Notes | Status |
|---|---|---|
| Sessions list | Programme sessions with *attended · missed · unknown · on hold* as reported in the attendance sheet | Agreed |
| Sheet notes | Notes shown next to the entry; notes-vs-counter conflicts flagged | Agreed |
| Programme context | Start date, holds, reschedules | Agreed |
| No inference | Calendar invite or missing transcript ≠ absence | Agreed |
| Streaks / % / alerts | Not until WIA defines the rule | Agreed (needs definition) |

### B9. Accounts & sources — *"What's connected for this client, and how complete is it?"* [Proposed new]
| Component | Notes |
|---|---|
| Linked accounts | Slack channel(s), Drive folder, ClickUp list(s), LeadLock location, contacts' emails, calendar rule, with **Edit mapping** |
| Per source | Last successful sync, history covered (from–to), items processed, gaps |
| Backfill progress | For new clients and launch sign-off |
| Unprocessed content | Scans, images, recordings kept as links only [Agreed] |
| Mapping suggestions | "New Drive folder 'Harbor House – Brand' looks like this client. Link it?" |

Today this lives only on the global Connections screen. Per-client, it's where ops fixes mapping and where anyone checks why something is missing.

### B10. Support — *"What's broken or being fixed for this client, and is it getting handled?"* [Defined 6 Nov]
**What a support issue is:** something WIA set up or manages that isn't working: a form or follow-up, the booking calendar, tracking, the domain, a login, a page.
- A request for new work is a commitment (B5).
- A question is an ask (Now, call prep).

| Component | Content |
|---|---|
| Coverage banner | Which sources are read ("Gmail and Slack only; LeadLock support inbox not connected"). No issues ≠ no problems |
| Summary | Open · waiting on client · fixed in the last 90 days · typical time to fix · keep coming back |
| Open issues | Area (LeadLock workflow, LeadLock calendar, LeadLock access, forms and tracking, domain/DNS, landing page, ad-account access, reporting), state, raised by / channel / date, owner, days open, repeats, latest update, what happened (timeline), the fixing action in the Action Hub |
| Resolved | Collapsed. Date fixed, days to fix, and the **evidence** the fix worked. "Resolved" without evidence is flagged |

**Source:** issues are read from client email and Slack by the KB (AI). Until then, the tab says "Not extracted yet".

---|---|---|
| Issues list | Request, date raised, who raised it, affected thing (LeadLock form, DNS, tracking…), owner, latest state, resolution evidence | Agreed content (was a Profile addition) |
| States | Open · Waiting on client · Resolved · Unknown. Resolved needs evidence | Proposed |
| Link to actions | An issue's fix is an action in the register; the two link both ways | Proposed |
| Age and repeats | Days open; "3rd time this month" for recurring issues | Proposed |
| **Coverage banner** | "Support issues from Gmail and Slack only. LeadLock support inbox not connected." No issues seen ≠ no problems | Agreed |

Source readiness: Gmail has one real support chain; the actual LeadLock support intake route is unverified (KB-V-02).

---

## 4. Possible additions

| Addition | Value | Effort / dependency | Suggest |
|---|---|---|---|
| **Account owner field + My clients** | Daily filter; handover trigger | Low | **Release 1 (decided)** |
| **Accounts & sources sub-tab** | Fix mappings, explain gaps | Low–medium | **Release 1 (decided)** |
| **What changed since you last looked** | Fast catch-up | Agreed requirement | Release 1 |
| **Quick links** to Slack/Drive/ClickUp/LeadLock | Saves hunting | Low | Release 1 |
| **Onboarding progress** on Now | Ops visibility | ClickUp phase mapping | **Release 1 (decided)** |
| **Lifecycle stage** + filter | Separates onboarding from steady-state | Low | **Release 1 (decided)** |
| **Support sub-tab** | Issues in one place, linked to fixes | Coverage unverified | **Release 1 (decided)** |
| **Send handover brief on Slack** | Handover in one step | Reuses register's Slack screen | Release 1 if D8 is approved |
| **Profile export for drafting** (copy the Client Marketing Profile into ChatGPT/briefs) | Feeds WIA's playbook workflow today | Low | Release 1 |
| **Key dates** (contract renewal, seasonal peaks, client's busy season) | Proactive planning | Needs agreement terms | Later |
| **Client-side people map** (who decides, who approves) | Fewer wrong-person asks | Part of Profile → People | Release 1 (light) |
| **Account-owner change workflow** | Turnover-proofing | Ties Reassign all + handover brief | Release 1 |
| Ad account links / performance snapshot | Context | Paid media is deferred scope | Later |
| Testimonials / case-study candidates | Marketing reuse | Explicitly out of current scope | Later |

---

## 5. What this tab does not show

- Health scores or sentiment judgements (Stage 3).
- Ad performance or anomalies (deferred; Viktor keeps doing this).
- Full invoice ledger and balances (Stage 3, needs reconciliation).
- Anything from unapproved sources (website research, ChatGPT history, uploads, Shopify) [Agreed].

---

## 6. Data readiness

| Section | Ready? | Note |
|---|---|---|
| Portfolio card | Mostly | Needs the reviewed client roster, account owners and source mappings from WIA |
| Now | Yes (facts) | Narrative method undecided (P2) |
| Profile | Yes for Business/Ideal client/Voice/Goals | Real questionnaires read (Dogwood, Funktastic). Offer/pricing coverage per client unknown |
| History | Yes | Dedup rules need building |
| Meetings | Partly | Fathom samples work; historical Zoom access untested |
| Attendance | Partly | Two sheets read; rules for streaks undefined |
| LeadLock link | Yes | Lead outcomes and support **blocked** (scope-denied 401s) |
| Invoices & terms | Events only | Dubsado emails; no reconciled ledger |

---

## 7. Decisions

| # | Decision | Outcome |
|---|---|---|
| P1 | What the portfolio card shows before Health exists | **Health badge reads *Coming soon*** until Stage 3. Once Health is on, it shows the category (worst-signal rule, see 04 §5). The mockup shows the Stage 3 state |
| P2 | How "Current picture" and "Focus" are written | **KB drafts, account owner approves.** Stale when newer evidence arrives |
| P3 | Profile structure | **WIA's Client Marketing Profile** with the five source labels |
| P4 | Release-1 additions | **All four:** account owner + My clients · Accounts & sources sub-tab · lifecycle stage + onboarding progress · Support as its own sub-tab |
| P5 | Who is each client's account owner | Open, names from WIA |
| P6 | Lifecycle stages WIA actually uses | Open, confirm Onboarding / Active / Paused / Offboarding |
| P7 | How long a narrative draft can wait before ops is nudged | Open, proposed 2 business days |
| P8 | Remaining additions in §4 (handover on Slack, profile export, owner-change workflow, people map) | Open |
| P9 | Which §9 additions to adopt, and in which release | Parked 22 Oct. To revisit |
| P10 | Where client logos come from | **Decided 26 Oct:** Drive brand folder, then the primary contact's email signature; otherwise *Logo pending*. No website scraping |
| P11 | Portfolio card content | **Decided 26 Oct:** logo banner, initials, name, location, engagement chips (+ lifecycle when not Active), owner, Engagements · Open actions · Overdue, health category, *…* menu. Next call, last contact and coverage move off the card |
| P12 | Invoices & terms layout | **Decided 26 Oct:** standing line, invoices beside agreements, one activity timeline (see B7). Alert-only records never read *Up to date* |

---

## 8. Mockup coverage (26 Oct)

Mockup: `frontend/exports/client-portfolio.html#clients`. Built from `src/views/Clients.tsx`, `ClientDetail.tsx`, `Portfolio.css` and the sample records in `src/records.ts`.

| In the mockup | Not in the mockup yet |
|---|---|
| **Portfolio:** signed-in person from the sidebar account menu; heading with Add client; My clients / All clients; service, stage, owner and health filters; logo cards (P10/P11) with *Logo pending* fallback (Harbor), source shown on hover, *…* menu, three stats, health category; list view with logo thumbnail, services, owner, stats, next call, health. Logos are fictional drawings | Real logo extraction; Paused / Offboarding sample clients |
| **Add client** wizard: business → engagements → contacts → confirm suggested source links → start backfill (preview only, nothing is added) | Saving a new client |
| **Record header:** aliases, engagement chips, lifecycle, owner, three dates, quick links, related business, engagement switch (Rosewood, Harbor) | Engagement switch filtering Commitments (actions have no engagement field yet) |
| **Now:** narrative with Approved / Draft waiting / Stale states; approve, edit, discard (owner or Whitney only); what changed since you last looked with mark as read; next call; onboarding progress (Harbor); commitments snapshot; latest client words; record limits | Nudge when a draft waits too long (P7) |
| **Profile:** Client Marketing Profile sections, five source labels with legend, propose a correction, people (client + WIA), engagements with signing dates, LeadLock link with lead outcomes *Unavailable* | Resolver queue for proposed corrections |
| **History:** timeline + feed, Commercial lane (signing and payment events), "since last call" filter, three-date note | Milestones |
| **Handover brief:** seven sections, copy, download as Markdown | Send on Slack (P8) |
| **Commitments:** shared action rows, Post to #client channel (same Slack review screen), link to the register | — |
| **Meetings:** call-type filter, upcoming, decisions, actions created, transcript state, shared-session note | Transcript excerpts beyond one source link |
| **Support** (Rosewood, Harbor): coverage banner, state, owner, age, repeats, resolution evidence | Link from an issue to its fixing action |
| **Invoices & terms** (admins): condensed layout (P12) using the finance sample, or real GHL/Dubsado data in the local-only `export:live` build | *Coming soon* state for release 1 |
| **Attendance** (Willow, Magnolia): sheet-reported states incl. Unknown, notes-vs-counter conflict flag | Real sheet ranges |
| **Accounts & sources:** coverage, backfill progress, mapping suggestion (Harbor), per-source table with state, last sync, history from, items, Edit mapping | Editing a mapping |

---

## 9. Proposed additions for end-to-end coverage (22 Oct, parked for later)

**Status:** Proposals only. Not decided and not in the mockup. To revisit (P9).

**Why:** the current design covers *who they are*, *what's happened* and *what's owed*. It's thin on **what we promised to deliver**, **whether the regular rhythm is happening**, **what's still unknown**, and **the start and end of the relationship**. These additions close those gaps across the whole client journey: signed → onboarded → running → renewing or leaving.

Where an item overlaps §4 (owner-change workflow, people map, key dates), this section is the fuller version.

### 9.1 Tier 1 — closes real gaps (recommended for release 1)

| Addition | Where | Why it matters | Data |
|---|---|---|---|
| **Scope & deliverables** | New sub-tab, or a Profile section | What the engagement includes: monthly strategy call, ads management, LeadLock workflows, reporting. Without it, nobody can tell "owed" from "extra". A new account manager needs this on day one | Signed agreement in Drive/Dubsado; WIA's service definitions |
| **Service rhythm** | Now + portfolio card | Checks whether the regular commitments happen. Example: monthly strategy call, last one 38 days ago, so it's late. The Action Register only catches one-off asks, not missed routines. This is the core of Whitney's follow-through problem | Calendar + Fathom against the cadence in Scope |
| **Decision log** | New sub-tab, or a Meetings filter | Answers "what did we agree about X?". Lists every decision with its date, who made it, and what replaced it. History shows events, but can't be searched by topic | Meetings, Slack, Gmail (already extracted) |
| **Open questions for the client** | Now + feeds Call Prep | Gathers everything the KB doesn't know yet: empty profile fields, unclear ownership, conflicts. They become things to ask on the next call. Turns "Unknown" from a dead end into a task | Needs-review items, empty profile fields, conflicts |
| **Profile completeness** | Profile header + portfolio card | "Profile 9 of 14 fields filled · offer and proof missing." Shows which clients aren't documented well enough for handover | Derived |
| **Access & setup checklist** | Accounts & sources, or Onboarding | Whether WIA has access to the client's ad accounts, pixel, domain/DNS, LeadLock, GA4 and brand assets: who granted it, and what's pending. The most common onboarding blocker. **Status only, never credentials** | ClickUp onboarding tasks, Gmail |
| **Account-owner change** (P8) | Header action | Change owner → new owner gets the handover brief → open actions move with Reassign all → old owner gets read access. The turnover-proofing goal made into one flow | Existing pieces |

**Suggested first four:** Scope & deliverables, Service rhythm, Open questions for the client, Account-owner change.

### 9.2 Tier 2 — strong value, light effort

| Addition | Why |
|---|---|
| **Portfolio summary strip** | Counts above the cards: onboarding, no contact in 14+ days, narratives waiting for approval, sources not linked, clients without an owner. Like the Action Register's tiles, but per client |
| **Saved views** | E.g. "My onboarding clients" or "Not contacted in 14 days" |
| **Follow a client** | Get "what changed" for a client you don't own, e.g. Whitney watching a sensitive account |
| **Working preferences** ("How to work with them") | Preferred channel, approval process, response times, things to avoid. Today these sit in contact notes, but people need them every time they contact the client |
| **Key dates** | Busy booking season, blackout dates, availability windows, programme end. Wedding businesses are very seasonal, and that changes what you'd recommend on calls |
| **Programme progress** (accelerators) | "Week 13 of 16", modules completed, graduation date, and the natural next offer (Accelerator → Elevate). Attendance alone doesn't show this |
| **Record change log** | Who changed which profile fact, and when. Lets a resolver review corrections |

### 9.3 Tier 3 — depends on other stages or decisions

| Addition | Depends on |
|---|---|
| **Renewal / contract end** | Invoices & Contracts (Stage 3) |
| **Pause / offboarding flow and former-client archive** | Scope decision (former clients are currently out of scope) |
| ~~"Ask about this client"~~ (chatbot scoped to one client) | **Dropped 22 Oct:** Client 360 is a single sidebar tab only, with no per-page entry points (06-chatbot N2). Pick the client in its scope bar instead |
| **What we've built for them** (live campaigns, pages, workflows) | Paid-media sources, which are deferred |
| **Ad performance snapshot** | Deferred; Viktor covers this today |
| **Testimonials / case-study candidates** | Agreed as out of scope |

### 9.4 Inputs these would need from WIA

- **Service rhythm:** the agreed cadence per engagement type (e.g. "Elevate = monthly strategy call + monthly report"). Not stated anywhere yet.
- **Scope & deliverables:** WIA's service definitions, or access to the signed agreements. Dubsado notifications alone don't contain terms.
- **Access checklist:** the list of accesses WIA needs per engagement type.
- **Programme progress:** the accelerator curriculum (weeks, modules, graduation).
