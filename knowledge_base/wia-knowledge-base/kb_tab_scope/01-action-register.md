# Tab 1 — Action Register

**Status:** Draft · D1–D4 and D10–D13 decided, D8 proposed · mockup updated 26 Oct 2026 (`frontend/exports/client-portfolio.html#actions`, revised layouts at `#actions-v2` and `#actions-v3`) · Stage 1
**Labels:** **[Agreed]** = already decided in KB-CH-05…69 / functional requirements. **[Proposed]** = new in this draft, needs a yes/no.

---

## 1. What this tab is for

**One question:** *What needs doing, by whom, by when, and is it actually happening?*

It is WIA's single list of real obligations, both ways: what WIA owes clients, and what clients owe WIA. Every item traces back to where it was agreed. It replaces three things the team uses today:

| Today | Problem | What the register does instead |
|---|---|---|
| Gisselle's own ClickUp filter | ClickUp only. Asks made in Slack, email and calls are invisible | Pulls ClickUp **plus** explicit asks/commitments from Slack, Gmail and Fathom |
| Viktor's daily "open loops" | Lives in Slack threads, verbose, not owned | Same three loop types, as a structured, filterable list WIA owns |
| Viktor's Monday ClickUp digest | Dropped because it was "a lot… even old ClickUp tasks" | **Stale handling is the core design problem.** Old or unclear items go to Needs review, not the live list |

The last row is the main lesson. If the register shows everything ever mentioned, nobody will use it.

---

## 2. Who uses it, day to day

| Person / role | When | What they need from this tab |
|---|---|---|
| **Ops coordinator** (Gisselle today) | Every morning | Triage Needs review. Chase anything overdue, unowned or unacknowledged |
| **Account / ads managers** (e.g. Carmen) | Start of day, and after each call | "My actions" across all clients. Acknowledge new ones, mark done |
| **Whitney** | Daily scan, weekly review | What's slipping, what's waiting on *her*, what's waiting on clients. Verify key deliverables |
| **Anyone, before a client call** | Before the call | That client's open items, both directions (also feeds Call Prep in Stage 2) |
| **Whitney / ops, when someone leaves** | At handover | Everything a person owns, reassigned in one go. This is the turnover-proofing goal |

---

## 3. What counts as an action

### 3.1 In [Agreed]
| Source | What becomes an action |
|---|---|
| ClickUp | Relevant tasks in mapped client lists, with their real owner, date and status |
| Slack / Gmail | **Explicit** requests ("can you send the logo files?") and commitments ("I'll have the draft by Friday") |
| Fathom / historical Zoom | Commitments and asks made on calls, including Fathom's own action items |
| Manual | Added in the KB by an authorised user |
| AI suggestions | Shown only as **proposals** in Needs review, never as live obligations |

### 3.2 Out, or a separate bucket [Proposed]
- **Programme operations** in the accelerator lists (office hours, weekly community posts, attendance upkeep). These aren't client obligations. **Decided (D4):** they go to a separate **Programme ops** view and are left out of client action counts.
- ClickUp template or internal tasks with no client mapping.
- Status `n/a`. `recurring` tasks are not shown as overdue (ClickUp scope finding).
- Viktor's own prose ("client approved X"). That's analysis, not evidence of the ask [Agreed].

### 3.3 The live-list test [Proposed]
An item goes **straight to the live register** only if all of these hold:
1. It's matched to one client, or explicitly to WIA internal work.
2. It's an existing open ClickUp task, **or** an explicit ask/commitment with activity in the last **30 days** (decided, D2).
3. It isn't a likely duplicate of an existing action.

Anything else goes to **Needs review**, with the reason attached.

---

## 4. Components

### 4.1 Header and scope switch [Proposed]
- **Three sections:** Register · Needs review · Programme ops, each with a count.
- **My actions · My team · All clients.** **Decided (D1):** the default is *My actions* for most users and *All* for admins/ops. *My team* is previewed in the v2 · Teams layout (`#actions-v3`) from sample account teams; WIA's real groupings are still needed.
- **Group by (D12):** **Team** (WIA's own actions by team member; admins/ops only, their default) · **Client** (only what clients owe WIA, grouped by client; under *My actions*, the clients you work with) · **Due date** (everything; the default for managers).
- Search, status filter (Open · Snoozed · Completed · All), owner filter (incl. Unassigned) and **Notify on Slack** (§5a).
- "Last synced: ClickUp 9:42, Slack 9:40…" freshness line [Agreed].
- ~~*All clients* adds a workload-by-owner panel with Reassign all~~. **Removed (D11):** owners are changed per action in the drawer.

### 4.2 Summary strip. Each tile is a clickable filter.
| Tile | Rule | Status |
|---|---|---|
| **Overdue** | Known deadline passed, not Done. Unknown deadlines are never overdue | Agreed |
| **Due this week** | Known deadline within 7 days | Proposed |
| ~~Due before next call~~ | Removed as a tile (D10). Rows still show a *Before [date] call* flag | Removed |
| **Awaiting acknowledgement** | Has an owner, no acknowledgement after 1 business day | Proposed threshold |
| **Waiting on client** | Client-side item still open, with "waiting N days" | Agreed concept, aging proposed |
| ~~No owner / no date~~ | Removed as a tile (D10). Rows still show *Unassigned* and *No date*, never filled in [Agreed] | Removed |
| **Needs review** | Triage queue count | Agreed |
| **Awaiting verification** | Done, not yet Verified. Only counts flagged types (D3) | Agreed |

### 4.3 Action list (row)
| Field | Notes |
|---|---|
| Title | Short current wording. The original statement is in the drawer |
| Client · service | e.g. "Dogwood · Google + Meta" |
| Owner | Named person, **"Unassigned"**, or several people |
| Side | WIA · Client · Third party |
| Deadline | Date / date+time / **"No date"**, with a ⚠ icon if sources disagree |
| Status | Open · In progress · Blocked · Done · Verified · Cancelled |
| Acknowledged | ✓ / pending (with age) |
| Origin icon | ClickUp / Slack / Gmail / Meeting / Manual |
| Age | Days since created / last activity |
| ClickUp link | Opens the real task when mapped [Agreed] |

### 4.4 Action detail drawer
- **Where it came from:** the original quote, who said it, when, and a link to the exact message/timestamp [Agreed].
- **Supporting evidence:** every later mention (follow-ups, the meeting where the date moved).
- **Conflicts:** e.g. *"ClickUp due 20 Oct · Meeting 14 Oct said 24 Oct → using 24 Oct"*. Meeting beats ClickUp; both are shown [Agreed].
- **History:** owner/date/status changes, and who changed what.
- **Acknowledgement record:** who, how (reply / KB button / emoji), when [Agreed].
- **Completion basis:** ClickUp closed, or the delivery message [Agreed].
- **Verification record:** reviewer, what was checked, evidence [Agreed].
- **Related:** linked meeting, next scheduled call, merged duplicates.
- **Internal notes** [Proposed]: short team comments on the action.
- **Progress controls:** Mark blocked / Unblock, Mark done…, Verify… (for flagged types).
- **Owner and deadline edits:** "Unassigned" is a valid owner; "Clear date" sets *no agreed deadline*. Changing the owner resets acknowledgement.
- **Snooze** [Proposed]: 3 / 7 / 14 days with a reason. Snoozed items drop out of counts until then. **In the revised layout this is replaced by a deadline-change request (D13).**
- **Reopen** (D13): a completed action can be reopened from the drawer or its ticked checkbox; earlier verification is superseded and history kept.
- **Request a new deadline** (D13, revised layout): non-admins can't edit the deadline; they pick a date and a reason and send it for approval. Admins (Whitney, Gisselle) see it in Notifications and Needs review, and approve or decline; both are logged.
- **Notify on Slack…** [Proposed]: client channel, or DM the owner personally (§5a).

### 4.5 Needs review queue (sub-tab)
Each card shows the item, **why it's here**, and the evidence. One-click outcomes:

| Reason | Typical resolution |
|---|---|
| Possibly stale (old, no closure seen) | Still open → accept · Already done · Dismiss |
| Owner unclear | Assign owner → accept |
| Client match unclear | Pick client |
| Possible duplicate | Merge into existing · Keep separate |
| Date conflict worth a look | Pick a date (reason recorded) |
| AI proposal | Accept as action · Dismiss |
| Done in ClickUp but checklist incomplete | Confirm done · Reopen |

Every dismissal records a reason, and a dismissed item is **not recreated** by the next sync [Agreed].

### 4.6 Dialogs
- **Add action:** title, client, who owes it (WIA / client), owner (optional), deadline (optional), **type** (sets whether it needs verification), where it was agreed.
- **Mark done:** completion basis (link or note). Says whether the type will wait for verification or close.
- **Verify:** what was checked, plus an evidence link. Verifier is the logged-in user, subject to self-verification permission [Agreed].
- ~~Reassign all~~: **removed (D11).** Changing the owner on an action already resets acknowledgement.
- **Notify on Slack** [Proposed]: one compose screen for every entry point (§5a).

### 4.7 Filters
Client · service · owner · side · origin source · status · deadline range · review reason · text search. Counts always reflect the full filtered set, not just the loaded page [Agreed].

---

## 5. Daily business logic

| Rule | Proposed default |
|---|---|
| **Status mapping from ClickUp** | Map each WIA ClickUp status to Open / In progress / Blocked / Done / Cancelled once, during setup. `recurring` and `n/a` handled separately |
| **Overdue clock** | Date-only deadline is overdue from the *next day* in **WIA's operating timezone** (configurable) |
| **Acknowledgement** | Counts if the owner replies accepting, clicks Acknowledge, or uses a configured emoji. Assignment alone never counts [Agreed]. Reaction ack stays off until WIA picks emojis [Agreed] |
| **Owner changes** | New owner starts unacknowledged. The old owner's ack doesn't carry over [Agreed] |
| **Done vs Verified** | Done = reported complete. Verified = a named person checked it actually stuck (Carmen's "make sure it actually stuck") [Agreed]. **Decided (D3):** only *flagged types* need Verified, all others close at Done. Proposed flagged types (as in the mockup): **landing page, LeadLock/GHL setup, tracking/UTM fix, ad/campaign change, client approval**. Set per action, defaulting from the type. WIA confirms the list (D7) |
| **Reopen** | ClickUp reopening a task reopens the action and supersedes verification; history kept [Agreed] |
| **Stale import** | During the historical backfill, open-looking asks with no activity in **30 days** and no closure go to Needs review in bulk, not to the live list (decided, D2). Expect a large first-day triage queue. Plan a bulk-dismiss / bulk-mark-done pass |
| **Self-verification** | Owners can't verify their own work unless an admin grants it [Agreed: admin-configurable]. In the mockup only Gisselle and Whitney can |
| **Escalation** [Proposed] | Overdue more than 3 business days → shows on Whitney's / ops view with a flag |
| **Write-back** | No ClickUp task creation in release 1 [Agreed]. **Slack notifications now proposed for release 1** (see §5a), always reviewed by a person before sending |

### 5a. Slack notifications [Proposed, 22 Oct]

Replaces the CSV export. One compose screen, three entry points. **Nothing is sent until a person reviews the messages and presses Send**, which keeps the agreed "human review before external notification" rule.

| Entry point | Who it reaches by default | Options |
|---|---|---|
| **Toolbar "Notify on Slack"** (current filtered view) | Each client's channel (that client's items only) + admin summary | DM each owner their own items |
| **By person → "Notify [name] on Slack"** | DM to that person + admin summary | Post to the client channels too |
| **By person → Unassigned → "Notify admins"** | Admin summary listing items with no owner | — |
| **By client / client contact → "Post to #channel"** | That client's channel | DM owners, admin summary |
| **Action drawer → "Notify on Slack…"** (single task) | Client channel for client-related tasks | **DM the owner personally** |

**Routing rules**
- Client-related task → that client's Slack channel. Each channel only ever gets its own client's items.
- Personal DMs only go to WIA team members. Client contacts are reached through their channel.
- Admins (proposed: Whitney, Gisselle) get one summary: counts, overdue, needs an owner, not acknowledged.
- Accelerator clients share a programme channel (#meta-accelerator, #google-accelerator). Posting there is **off by default with a warning**, and the owner's DM is ticked instead.
- Snoozed and completed items are left out.
- Every message is editable and can be unticked. Each send is logged on the action's history ("Slack: notified #client-bloom-manor (sent by Gisselle)").
- Messages invite a ✅ reply, which feeds acknowledgement once WIA configures the emoji map.

**Needs confirming before build**
- **Are client channels internal, or shared with the client (Slack Connect)?** If the client can see the channel, internal wording like "overdue" or "not acknowledged" would reach them. The channel message template would need a client-safe version, or channel posts limited to internal channels.
- Who counts as an admin for the summary.
- Slack app scopes: `chat:write`, `im:write`, plus channel membership for the KB app. This is a new write permission beyond the current read-only Slack access.

---

## 6. Possible additions

| Addition | Value | Effort / dependency | Suggest |
|---|---|---|---|
| **"Due before next call"** badge/tile | Highest daily value; nothing gets forgotten on a call | Needs Calendar matching (already in Stage 2 scope) | Release 1 if Calendar mapping is ready, else Stage 2 |
| ~~Workload by owner panel~~ | See who's overloaded | — | **Dropped (D11)** |
| ~~Reassign all on departure~~ | Turnover-proofing | — | **Dropped (D11):** per-action owner change covers it |
| **Unanswered asks** (asks to the team / to Whitney with no reply) | Viktor open-loops parity | Medium; needs "reply" detection in Slack | Release 1 or fast follow |
| **Snooze / defer with reason** | Keeps the list honest without dismissing | Low | Release 1 |
| **Internal notes** | Context without leaving the KB | Low | Release 1 |
| **Daily digest** | Replaces Viktor's open loops | The person-level Slack DM + admin summary (§5a) covers this on demand; scheduling it is a small step | Manual now, schedule later |
| **Chase draft for client-side items** | Saves writing follow-ups | Partly covered: client-channel posts list what the client owes (§5a). A client-facing wording depends on D9 | After D9 |
| **Create ClickUp task from an accepted Slack/meeting ask** | Closes the loop | Write-back is Coming soon [Agreed] | Later |
| ~~CSV export~~ | Replaced by **Notify on Slack** (22 Oct) | — | Dropped |
| **Priority** | Ranking | No agreed definition yet | Shown in the revised layout as sample High / Medium / Low with a Priority field on Add action. **WIA must define what each level means (D14)** |

---

## 7. What it does not show

- Ad performance or anomalies (Viktor keeps doing this; it's deferred scope).
- Client health judgements (Stage 3 Health tab).
- Invoices/payment chasing (Stage 3 Invoices tab).
- Programme attendance (client record → Attendance).

---

## 8. Data readiness

| Source | Ready? | Note |
|---|---|---|
| ClickUp | **Yes** for tasks, owners, dates, status | Comments not yet verified (8 reads, all empty). Status mapping needed |
| Slack | **Yes** for reading messages/threads | Reaction semantics need WIA's emoji map. DMs are not an approved *source*. **Sending** (§5a) needs new `chat:write` / `im:write` scopes, not yet requested |
| Gmail | **Yes** for samples | Push delivery untested |
| Fathom | **Yes** for samples (incl. action items) | Full coverage and webhook untested |
| Calendar | **Yes** for samples | Needed only for "due before next call" |

Nothing on this tab is blocked by LeadLock.

---

## 9. Decisions

| # | Decision | Outcome |
|---|---|---|
| D1 | Default landing grouping | **By person.** *My actions* by default, *All* for ops/admins. By-client and by-date one click away |
| D2 | Stale cutoff for imported history | **30 days** without activity → Needs review |
| D3 | Which actions need Verified | **Only flagged types.** WIA confirms the type list (see §5) |
| D4 | Programme-ops tasks | **Separate "Programme ops" bucket**, excluded from client counts |
| D5 | Which additions from §6 go into release 1 | Open |
| D6 | Who is the ops reviewer, and who can verify | Open, names from WIA |
| D7 | Confirm the flagged-for-verification type list | Open, WIA |
| D8 | Replace CSV with Slack notifications (channel / personal DM / admin summary) | **Proposed 22 Oct**, shown in the mockup. Pulls external notifications into release 1, changing KB-CH-38 |
| D9 | Are client Slack channels internal or shared with clients? | Open. Decides the channel message wording. Finding (Oct): channels are internal-only with the whole team in each, so they can't drive per-client visibility |
| D10 | Summary tiles | **Decided 22 Oct:** drop *Due before next call* and *No owner / no date*. Six tiles remain, in one row |
| D11 | Workload panel and Reassign all | **Decided 22 Oct: removed.** Owner changes happen per action |
| D12 | Grouping | **Decided 22 Oct:** *Person* renamed **Team** (WIA's actions only, admins/ops only); **Client** shows only client-owed items |
| D13 | Revised layout behaviours | **Decided 23 Oct:** Needs review visible to admins only; programme ops shown in the same list with their own hue (still excluded from client counts, D4); due-date range filter (today / tomorrow / this week / all time); snooze replaced by a deadline-change request that an admin approves; reopen; a last-sync pill that turns red when a source fails, with *Sync all now* |
| D14 | What High / Medium / Low priority means | Open. WIA |
| D15 | Bucket edge cases (revised layout) | Open: should unassigned items sit in Team pending; does "team" mean all of WIA or the person's account team; does a WIA task *blocked on the client* move to Client pending; who moves a client item back once the client delivers |
| D16 | Review stages after completion | Open: is "review" the same as Verified; who reviews (always an admin, chosen per action, or by type); do items awaiting review count as completed or appear on the reviewer's own list; review only for flagged types (D3) or on request |
| D17 | Which layout ships | Open: original (`#actions`), Revised board/list (`#actions-v2`) or v2 · Teams (`#actions-v3`) |

---

## 10. Mockup coverage (26 Oct)

Three layouts share one dataset; edits in one show in the others. The signed-in person is chosen from the sidebar account menu (Carmen, Jacqueline, Gisselle, Whitney); in the real app the view follows the signed-in user.

**Original (`#actions`)**

| In the mockup | Not in the mockup yet |
|---|---|
| Six tiles in one row (D10); Register / Needs review / Programme ops; My actions / All clients by role; Team (admins) · Client (client-owed) · Due date grouping (D12) | *My team* scope |
| Rows with Unassigned / No date, origin, ack age, waiting age, needs-verification and before-call flags, ⚠ deadline conflicts | Cancelled status, Third-party side, multiple owners |
| Drawer: origin quote, conflict, owner/date edits, acknowledgement (owner-only), block, done, verify, **reopen**, snooze, Slack, notes, history | Supporting-evidence list beyond the origin; merged-duplicate links |
| Needs review: 6 sample cards, one per reason, with working outcomes and a resolved log | "Date conflict worth a look" card; bulk triage |
| Add action with type, Mark done / Verify dialogs, self-verification rule; Slack toolbar, per-group and per-action notify | Escalation flag; Unanswered asks; scheduled digest |

**Revised (`#actions-v2`)** and **v2 · Teams (`#actions-v3`)**

| In the mockup | Not in the mockup yet |
|---|---|
| Heading with last-sync pill (green, or red with the failed source and *Sync all now*); four KPI cards: Pending (yours / team / client), Completed | Real sync |
| Filter pills with counts, due-date range, search, client filter, **Board / List** toggle, Add action (with Priority) | Slack notify (not wired in these layouts) |
| Board: four columns, five cards then *View more*; List: action, client, assignee, due, status, priority | Overdue / not-acknowledged / awaiting-verification views; row flags beyond priority and *Deadline change pending* |
| Programme ops in the same list (teal, *Programme ops* pill) | — |
| Reopen from the checkbox or drawer; deadline-change request and admin approval (Notifications → Needs review) | Review stages and reviewer assignment (D16) |
| Needs review (admins only): deadline-change requests plus the triage queue | — |
| v2 · Teams only: per-client visibility from sample account teams (`src/teams.ts`) | WIA's real account teams |
