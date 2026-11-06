# Action Register: discovery analysis

**As of:** 29 Oct 2026
**Scope:** observations from source checks and decisions that affect the Action Register (scope doc: `01-action-register.md`)
**Method:** read-only API calls only. Nothing was written to ClickUp or Slack.

Some figures come from live ClickUp and Slack reads:
- **ClickUp:** read with the E2M AI key. It can see 8 live spaces and 2 archived ones.
- **Slack:** read with the WIA AI BOT token.

Raw pulls were kept out of the repo.

---

## 1. Summary

ClickUp is used every day, but **mostly as an onboarding checklist engine, not a general to-do list**. That changes what the register should show.

- **Volume.** Most open tasks are templated onboarding checklist items. Showing every open task would flood the register.
- **Due dates.** Few tasks have them, so "overdue" will undercount.
- **Unused features.** Priority, tags, comments and the "in progress" / "on hold" statuses are almost never used.
- **Useful custom fields.** Two already exist:
    - **Role** marks client-owed tasks.
    - **Phase** gives onboarding progress.
- **People.** Identities are messy:
    - one shared admin account (WIA Support, used by Gisselle)
    - several staff on non-WIA email addresses
    - two former creators who are no longer members
- **Write-back and Slack notify.** The identity and permission work for both is settled (§5).
- **Slack is where ad-hoc work is asked for** (§4.1):
    - About 25% of client-channel messages are requests, and almost all name an owner with an @mention.
    - Fewer than 1 in 5 give a date.
    - Only about 30% show an explicit "done" in the thread; 39% get no reply.
    - Client requests usually arrive second-hand, relayed by Whitney or Gisselle.

---

## 2. How ClickUp is used

### 2.1 Volume

| Measure | Value |
|---|---|
| Tasks visible to E2M AI | 2,593 (1,240 of them subtasks) |
| Open tasks | 894 |
| Earliest task | Nov 2023 |
| Tasks updated, last 90 days | 1,854 |
| Tasks updated, last 30 days | 910, with updates on 26 of 30 days |
| Tasks updated, last 7 days | 516 |
| Median days from creation to close (closed in last 90 days) | 7 |

Tasks created per month:

| Month | Tasks created |
|---|---|
| Jan 2026 | 194 |
| Feb 2026 | 94 |
| Mar 2026 | 87 |
| Apr 2026 | 38 |
| May 2026 | 128 |
| Jun 2026 | 84 |
| Jul 2026 | 209 |
| Aug 2026 | 645 |
| Sep 2026 | 440 |
| Oct 2026 | 386 |

Usage stepped up sharply in Jul–Aug 2026 and has stayed high.

### 2.2 What the tasks are

| Space | Updated, last 90 days | Total | What it holds | Register treatment (proposed) |
|---|---|---|---|---|
| ONBOARDING CLIENTS | 1,019 | 1,087 | Per-client checklists: LeadLock Onboarding, Google + Meta Onboarding, Ads Traffic Landing Page | **Open question Q1.** Roll up into onboarding progress, or list individually |
| WIA Internal | 234 | 307 | Per-person lists (Carmen, Gisselle, Danielle) | Internal (D4); visible only to the owner and admins |
| ELEVATE Clients | 228 | 471 | Per-client "Client Management" lists: ongoing work | **Core register content** |
| Templates | 214 | 255 | Template definitions | **Exclude from ingestion** |
| Meta Ads Accelerator | 64 | 64 | Programme "Client Management" | Programme ops (D4) |
| Google Search Accelerator | 41 | 45 | Programme "Client Management" | Programme ops (D4) |
| Foolproof Follow-Up Advantage | 29 | 339 | Mostly dormant | Ingest; little current activity |
| VIP Days | 25 | 25 | VIP Day onboarding | Same as the onboarding question (Q1) |

- **Templated creation:** 56% of all tasks (1,451) were created in bursts of 5 or more within 10 seconds.
- **Who creates them:** 87% (2,244) were created by **WIA Support**.

### 2.3 Fields and statuses

The percentages are of tasks updated in the last 90 days (1,854).

| Field | Use | Implication |
|---|---|---|
| Assignee | 78% | Owner is usually known. 22% will show as "No owner" |
| Due date | 39%, but only **22% of open tasks** (200 of 894) | "Overdue" covers only a fifth of open work. 40 open tasks are overdue today |
| Priority | ~0% (2 tasks) | **D14:** ClickUp gives no priority signal. The KB would be introducing one |
| Tags | ~0% (2 tasks) | Not a usable signal |
| Description | 29% | Little context in the task itself |
| Custom fields set | 69% | See §2.4 |
| Comments | **0** in a 180-task sample: 120 recently updated tasks, plus 60 client-management and personal-list tasks | Discussion happens in Slack. ClickUp comment ingestion is low value |

**Statuses in use** (last 90 days):

| Status | Tasks |
|---|---|
| to do | 668 |
| done | 544 |
| complete | 431 |
| Closed | 108 |
| recurring | 73 |
| n/a | 21 |
| in progress | 6 |
| on hold | 2 |
| under review | 1 |

What the statuses mean for the register:
- **Workflow:** in practice the workflow is open → done. "Done", "complete" and "Closed" are all terminal.
- **KB-only states:** the KB's `in_progress` and `blocked` have almost no ClickUp equivalent. Setting them in the KB gives write-back nothing to write, unless a list has "on hold".
- **"n/a":** this maps naturally to `cancelled`.
- **"recurring":** these 73 tasks need a rule, probably excluded from overdue.

### 2.4 Custom fields worth using

**Role.** Roughly the function that does the task:

| Value | Tasks |
|---|---|
| Assistant | 528 |
| GHL Specialist | 495 |
| Ads Manager | 282 |
| LeadLock Designer | 239 |
| **Client** | **82** |
| CEO | 64 |
| Marketing Assistant | 24 |
| All Team Members | 20 |

- **Role = Client** is a ready-made signal that the client owes the task (`responsibility = client`). It feeds the Client pending bucket and the D12 Client view.
- **The other roles** describe a function, not a person. They could support default assignment when the assignee is empty.

**Phase.** Onboarding phase per service:

| Field | Values (tasks) |
|---|---|
| Phase (LeadLock) | Project Initiation 169, Launch 160, Tech Setup 150, Design/Copy work 114, Onboarding 105, Final Implementation 65 |
| Phase (Full Service) | Project Initiation 81, Onboarding 63, Google Ads Setup 38, Meta Ads Setup 30 |
| Phase (Ads Traffic) | used on 74 tasks |
| Phase (Google Ads VIP Day) | used on 42 tasks |

This is the obvious source for **onboarding progress**: per client, per service, the percentage of tasks done in each phase. It also answers part of P6 (lifecycle and onboarding stage names) in the Client Portfolio.

---

## 3. People and identities

### 3.1 ClickUp members (12)

| Display name | Login email | Role | Note |
|---|---|---|---|
| Whitney Hodges | hello@weddingindustryads.com | owner | The same mailbox the KB's Gmail connector reads |
| Whitney Hoges | own domain (whitneyhodges.com) | guest | A second account for Whitney |
| **WIA Support** | support@weddingindustryads.com | admin | **This is Gisselle** (confirmed by Jainil, 29 Oct). She has no separate account. She created 87% of all tasks and is the top assignee in the last 90 days (448) |
| Carmen Cruickshank | carmen@weddingindustryads.com | member | 2nd assignee (355) |
| Danielle McGinnis | **support@leadlockpro.com** | member | 3rd assignee (324); LeadLock domain |
| Jacqueline Hood | jacqueline@weddingindustryads.com | member | 144 |
| Tina Henares | **personal Gmail** | member | 133 |
| Fallon Looney | fallon@weddingindustryads.com | member | |
| Ivy Ayala | **personal Gmail** | member | |
| Crystal Chantel | **own business domain** | member | |
| Daniela Justus | **own domain** | member | |
| E2M AI | ai@weddingindustryads.com | member | KB read/sync identity |

**Former creators** who are no longer members: Christina Hill (57 tasks) and Yulia Burris (2). Their historical tasks need an owner shown as "former member", not as unknown.

### 3.2 What this means for the register (keep in mind for Stage 3)

- **Map non-WIA addresses explicitly.** Danielle, Tina, Ivy, Crystal and Daniela don't use `@weddingindustryads.com`. The roster must map each person's ClickUp user, Slack user and every email address they use. Otherwise:
    - they'll be classified as external (G-01)
    - their actions will look like client actions
    - "awaiting our reply" will be wrong
- **WIA Support = Gisselle.**
    - The roster records `support@weddingindustryads.com` as Gisselle's ClickUp identity.
    - The "Gisselle" list in WIA Internal is her personal list.
    - **Write-back:** when Gisselle connects ClickUp, she'll sign in as WIA Support, so her KB edits show as "WIA Support" in ClickUp. If anyone else ever uses that login, the KB can't tell them apart.
- **Two Whitney accounts.** Both map to the same person.
- **Ownership comes from the assignee, never the creator.** The creator is almost always WIA Support, because templates are applied from that account.

---

## 4. Slack (feeds Slack notify, D8)

| Item | State on 29 Oct |
|---|---|
| App | **WIA AI BOT** (the renamed Content Atelier app); the bot user handle is `content_atelier`; display name WIA AI BOT |
| Scopes | `channels:history`, `channels:read`, `groups:history`, `groups:read`, `files:read`, `reactions:read`, `users:read`, `users:read.email`, `chat:write`, `im:write`, `im:read` (`im:read` isn't needed) |
| Messages tab | On; users cannot message the bot |
| Client channels the bot is in | 4: `c_dogwoodreserve`, `c_dospalomasranch`, `c_funktasticproductions_djhybrid`, `cfpfu_luxurytravelboutique`. **Stays at 4** until testing and performance are proven (decided 29 Oct) |
| Other channels | `googlesearchaccelerator`, `metaadsaccelerator`, `social-proof-and-results`, `wia-ai-team-testing` |
| Dev app | **None** (decided). Testing goes through the outbound guard (§5.3) |
| Shared token | The same token is used by the Content Atelier code, which now also holds write scopes |

What this means for the register:
- **Notify scope.** Slack notify can only post to client channels the bot is in. In Stage 1 that's the 4 above.
- **Internal-only, confirmed for these 4.** None of the 4 is shared with an outside workspace (`is_ext_shared` false), and none has guest members. Members are WIA staff only (10–11 per channel). D9 holds for these channels; re-check each new channel before inviting the bot.

### 4.1 How asks happen in the client channels

**Data:** full history of the 4 channels, read-only on 29 Oct.
- 1,731 messages: 752 top-level and 1,044 thread replies.
- Date range: May 2025 – Oct 2026.

**"Ask"** means a message that:
- is not from a bot
- names a person with an @mention
- uses request wording ("can you", "please", "need to", "let me know", "follow up", "by Friday"…)

This is a keyword heuristic. Treat the numbers as indicative.

**Volume and activity**

| Channel | Messages | Last 30 days | Last 90 days | Active since | Note |
|---|---|---|---|---|---|
| c_funktasticproductions_djhybrid | 641 | 21 | 96 | May 2025 | |
| cfpfu_luxurytravelboutique | 438 | 0 | 2 | May 2025 | **Silent since 4 Sep 2026.** Is LTB still active? (G-04) |
| c_dogwoodreserve | 379 | 65 | 323 | May 2026 | Busiest recently |
| c_dospalomasranch | 273 | 58 | 110 | Mar 2026 | |

Monthly message volume across the 4 channels:

| Month (2026) | Messages |
|---|---|
| Mar | 112 |
| Apr | 109 |
| May | 44 |
| Jun | 123 |
| Jul | 120 |
| Aug | 147 |
| Sep | 234 |
| Oct | 130 |

**Who talks**

| Author | Messages |
|---|---|
| Whitney | 387 |
| Carmen | 320 |
| Gisselle | 262 |
| Danielle | 227 |
| Ivy | 137 |
| Viktor (bot) | 108 |
| Tina | 84 |
| Christina Hill | 78 |
| Jacqueline | 51 |

- **Former members** still appear in the history: Christina Hill, Yulia Burris, Megan Jivraj, Nicole Bautista and Jenna Tria.
- **Gisselle's Slack identity.** She has a normal Slack account, "Gisselle Jiménez". In ClickUp she is WIA Support. The roster must link the two.

**What asks look like**

- **Share of messages.** About 25% of human messages read like requests (437 of 1,731).
- **The owner is explicit.** 92% of request-style messages @mention a person, so Slack usually names the owner directly. A Slack user ID resolves to a person through `users:read.email` and the S3 roster.
- **Deadlines are rare.** Only about 18% mention a day or date, so most Slack asks have no deadline. They will show as "no due date", not as overdue.
- **Who asks and who is asked.**
    - Whitney asks most (162 request-style messages), then Gisselle (83).
    - The most-asked people are Whitney (74), Carmen (65), Tina (31), Danielle (24) and Christina Hill (23, a former member).
- **Four common shapes** (paraphrased):
    1. **Internal delegation:** "Can you draft a follow-up / check the report / launch the ads?"
    2. **Relayed client requests:** "The client let me know they want …". About 91 top-level messages relay something a client said or emailed. **Client obligations usually reach Slack second-hand, through Whitney or Gisselle.**
    3. **Call recaps:** a recap of a strategy call with a Fathom link (17). These overlap with Fathom extraction, so de-duplication is needed.
    4. **Viktor flags turned into asks:** for example, a broken promise from an earlier recap that was never done.

**How asks are closed** (205 top-level asks with an @mention)

| Outcome | Asks | Share |
|---|---|---|
| No thread reply at all | 80 | 39% |
| The mentioned person replied in the thread | 119 | 58% |
| A thread reply says it's done ("done", "sent", "launched", "live", "updated"…) | 62 | 30% |
| Closed only by a ✅ reaction | 9 | 4% |

- **Response time.** The median time to the mentioned person's first reply is 1.7 hours. The 75th percentile is 18 hours.
- **Reactions are mostly acknowledgements, not completions:**
    - 🙌 188
    - ✅ 96
    - ❤️ 84
    - 👀 57 (means "seen")
    - 👍 about 120 across skin tones

**Links to ClickUp**
- Only 20 messages mention or link ClickUp.
- **Slack asks and ClickUp tasks are mostly separate streams.** A Slack ask rarely points at its ClickUp task, so the reducer can't rely on links to merge them. It needs fuzzy matching, and probable matches go to review.

**Is "in progress" ever posted?** I checked the threads of the 205 @asks for phrases like "working on it", "on it", "will do", "I'll check", "started" and "looking into".

| Thread pattern | Asks | Share |
|---|---|---|
| No replies | 80 | 39% |
| Replies, but neither progress nor done | 48 | 23% |
| Done, with no progress note before it | 42 | 20% |
| Progress note, then done | 20 | 9% |
| Progress note, never marked done | 15 | 7% |
| A blocker or wait stated ("waiting on", "need access", "haven't heard") | 4 | 2% |

- **Progress notes are mostly acknowledgements, not status.** Across all messages there are 109 progress-style phrases. The most common are "working on" 20, "started" 19, "working on it" 12, "on it" 7 and "will do" 6. They're typically a promise to do it ("will do!", "I'll check it out"), said once when the ask arrives.
- **Asks almost never move through stages.** The pattern is ask → done, or ask → silence. Blockers are almost never stated in Slack.
- **ClickUp shows the same thing:** "in progress" on 6 tasks and "on hold" on 2 in the last 90 days.
- **For the register:**
    - Read "will do / on it / I'll check" from the person asked as **acknowledged** (D13), not as `in_progress`.
    - `in_progress` and `blocked` will rarely have evidence in the sources. If WIA wants them, people must set them in the KB. See `tobeaskedinnextcall.md` §3 and Q5.

### 4.2 Where relayed requests originate

There were 256 human messages in relay form ("let me know", "told me", "wants us to", "is asking"…):
- **Who posts them:** Gisselle 62, Whitney 54, Carmen 40, Danielle 35.
- **Mixed in:** the pattern also catches internal hand-offs, so treat the counts as shape only.

The wording often names where the request came from (one message can name more than one):

| Origin named in the message | Messages | Can the KB see the original? |
|---|---|---|
| Email | 94 | **Yes, if it reached `hello@`.** Email to a staff member's own mailbox is the accepted `hello@`-only gap |
| Call or meeting (recap, Fathom, strategy call) | 63 | **Yes, through Fathom**, if the call was recorded |
| GHL / LeadLock (sub-account, conversations, leads) | 46 | **No.** GHL reads are scope-denied today |
| Ads data or a report | 35 | Partly (Viktor posts, reports in Drive) |
| Dubsado or a form | 29 | Yes, through `hello@` notifications |
| Text or phone | 14 | **No.** Only the Slack relay exists |
| Social DM (Instagram, Messenger) | 8 | **No** |
| ClickUp | 7 | Yes |
| No origin named | 95 | Unknown |

What this means:
- **Email and calls are the main channels** for client requests. Both are mostly ingestible (`hello@`, Fathom), so the KB can often cite the client's own words, not just the relay.
- **About a quarter of named origins are invisible to the KB:** GHL/LeadLock, text/phone and social DMs. For those, the Slack relay is the only evidence.
- **Confirm with WIA:** where clients actually send requests, and which inboxes they use. See `tobeaskedinnextcall.md`.

### 4.3 What this means for the register

1. **Slack is where ad-hoc work is asked for.** ClickUp is where templated work is tracked. The register needs both, and Slack asks will mostly have an owner but no date.
2. **Extraction must read threads.** Most completions and progress updates arrive as thread replies, so a Slack action's status comes from its thread, not the parent message.
3. **Completion can't be confirmed for most asks.**
    - About a third show an explicit "done" in the thread. 39% get no thread reply at all; the work may have happened elsewhere (ClickUp, email) or not at all.
    - The thread count undercounts completions. An earlier check of the archive (23 Oct) found completion is often posted as a **new top-level message** ("Conversion ads are live!") rather than a reply. Extraction must link those posts back to the original ask, matching on subject, person and time window, and send unsure links to review.
    - Otherwise, the 30-day stale rule (D2) will move many asks to stale rather than done.
4. **Acknowledgement maps to reactions.** A 👀 or 👍 from the mentioned person is a natural "acknowledged" signal. ✅ is rarely used to mean done.
5. **Relayed client requests become client obligations,** owed by WIA to the client. Their evidence is the relay message, not the client's own words. The original email or call should be linked when it's found.
6. **Overlap with Fathom and Viktor.** Call recaps and Viktor flags repeat items that also exist in Fathom or in Viktor's posts. De-duplication and the "sources disagree" flag will fire here.
7. **Former members are frequently asked.** Christina Hill alone was asked 23 times. Their open asks need the former-member treatment (Q9).
8. **Gisselle's Slack and ClickUp identities differ.** Both must map to one person, or "My actions" will split her work in two.

---

## 5. Decisions made (29 Oct)

### 5.1 ClickUp identity
- **Read and sync:** E2M AI (`ai@weddingindustryads.com`, member).
- **Write-back:** each KB user connects their **own ClickUp account** once through the KB's ClickUp OAuth app. The edit appears in ClickUp under their name.
- **No fallback:** until a person connects, the KB blocks their edits to ClickUp-linked fields and shows "Connect ClickUp". A revoked or expired token blocks edits the same way. E2M AI never writes on anyone's behalf.
- **Echo suppression:** when the KB's own edits come back on the next sync, they carry the person's name. So the KB matches them against its outbound log, not by author.
- **Pilot impact:** every account owner must connect ClickUp before they can change an owner, due date or status.

### 5.2 Google
- `hello@weddingindustryads.com` only, for Gmail and Calendar.
- **Accepted gap:** client email to staff mailboxes, and meetings that are only on staff calendars and weren't recorded by Fathom, are not ingested. Actions raised only there won't appear.

### 5.3 Safe testing without a dev app
- **One switch:** `OUTBOUND_MODE` = `off` (the default everywhere), `sandbox` or `live`. `live` is set only on production, by hand.
- **Sandbox targets:**
    - Slack may post only to `#wia-ai-team-testing` and DM only Jainil.
    - ClickUp may write only to tasks in one sandbox list. This is checked by reading the task's list before writing.
    - Anything else is refused before the API call.
- **ClickUp write limits:** only assignees, due date and status. The prior values are stored before the write, and the task is re-read afterwards to confirm.
- **Human send only:** in Stage 1 nothing is sent automatically. A person presses Send.
- **Test isolation:** tests use fake clients, and CI holds no real tokens.
- **Kill switch:** a global kill switch stops all outbound.

### 5.4 Other
- The Fathom API key belongs to a WIA admin (confirmed).

---

## 6. Open questions raised by this discovery

To be worked through with WIA. Each links to an existing decision ID where one exists.

| # | Question | Why it matters | Related |
|---|---|---|---|
| Q1 | Do onboarding checklist tasks appear as individual actions, or roll up into an onboarding-progress view per client and service? Only Role = Client tasks and ELEVATE "Client Management" tasks would then be individual actions | Most of the 894 open tasks are checklist items; listing them all floods the register | D5, P6 |
| Q2 | Is **Role = Client** the rule for "client owes this"? Do other signals count too? | Drives the Client pending bucket and the D12 Client view | D4, D12 |
| Q3 | With 22% of open tasks dated, what should overdue mean? Should undated tasks have a default expectation, such as phase target dates? | Otherwise KPIs undercount | D10, D15 |
| Q4 | Priority (D14): drop it, derive it (from phase, client-owed, age), or let WIA set it in the KB only? | ClickUp has no priority data | D14 |
| Q5 | KB `in_progress` and `blocked`: KB-only states, or map `blocked` to "on hold" where a list has it? | Write-back has nothing to write for these | D15, write-back fields |
| Q6 | Do "recurring" tasks (73) count toward overdue and the open counts? | They never close | D15 |
| Q7 | Templates space: exclude entirely? | It holds definitions, not work | S2 scope approval |
| Q8 | WIA Internal personal lists: in the register (internal, owner-only), or out? | 234 recently updated tasks, personal to-dos | D4, D12 |
| Q9 | Former members' open tasks (Christina Hill, Yulia Burris): reassign, archive, or show as "former member"? | Unowned history | D11, S3 |
| Q10 | Is support@ (WIA Support) used **only** by Gisselle? | Write-back attribution and owner views assume one person | S3 |
| Q11 | Confirm client Slack channels have no external (client) members before the first live notify. **Confirmed for the 4 channels the bot is in.** Re-check each newly invited channel | Internal wording must never reach a client | D9 |
| Q12 | ~~Slack asks without a due date: show them as "no due date", or apply a default expectation (for example, 3 business days)?~~ **Decided 29 Oct:** no default date is invented. An undated action shows a visible **"No due date"** warning (the date field in red) and can raise a notice to its owner asking for a date | About 82% of Slack asks have no date | D10, D15 |
| Q13 | ~~Which reactions count as acknowledged (👀 👍) or done (✅)? Or ignore reactions and use only thread replies?~~ **Decided 29 Oct:** **configurable in KB Settings** (admin). Admins map Slack reactions to "acknowledged" or "done" (or nothing), and the reducer reads that mapping | Drives ack and completion signals | D13 |
| Q14 | ~~Is every relayed client request ("the client asked…") an action, or only when someone is @mentioned?~~ **Decided 29 Oct:** with an @mention, the mentioned person becomes the owner. Without one, the request becomes an unowned candidate in **Needs review**, and an admin approves or dismisses it. **Proposed next (for the next call):** a **pick-up** option, so that an approved unowned action is visible to the client's affiliated team and anyone can take it | Relays are frequent; the volume of Needs review depends on this | D4, D16, D12 |
| Q15 | Is LTB still an active client? Its channel has been silent since 4 Sep 2026. **Decided 29 Oct:** admins set each client active or inactive in the KB (an admin control on the client record and in client admin). Inactive clients drop out of default views and stale checks but keep their history. LTB's own status is set by an admin through this control | Client list and history floor | G-04, P6 |

---

## 7. Limits of this analysis

- **Last update only.** ClickUp's API exposes when a task was last updated, not every edit, so the counts are tasks touched, not changes made.
- **Visibility.** Only what E2M AI can see is counted. Archived lists and lists it isn't shared on are excluded.
- **Comments.** The comment finding is a 180-task sample. Rare comments may exist.
- **Slack heuristic.** The Slack "ask" and "done" counts come from keyword matching, not extraction. They show the shape, not exact counts. The S7 evaluation set will give real precision.
- **Slack coverage.** Only the 4 client channels the bot is in were read. Other client channels may behave differently.
- **Snapshot.** The figures describe 29 Oct 2026 and will drift as onboarding volume changes.

## 8. WIA's answers (30 Oct) checked against the data

Gisselle answered the action-item questions on 30 Oct. This section records her answers and how they compare with the Slack (4 client channels, full history) and ClickUp (all non-archived tasks) pulls of 29 Oct. Matching uses keyword overlap, so treat the percentages as approximate.

### 8.1 What WIA said

| Topic | Answer |
|---|---|
| Where requests come from | Mostly `hello@` (synced both ways with LeadLock) and client calls (onboarding and monthly strategy). A smaller share goes to Danielle (`support@` / `hello@leadlockpro.com`) and to Carmen's inbox for a few long-running accounts. New clients write only to Whitney. Slack is internal only |
| How something becomes an action | "Every action item is posted in Slack and added to ClickUp", always tagged or assigned by role. Ads: Carmen alone on some accounts; Carmen (Google) plus Jacqueline (Meta) on others. LeadLock copy, sequences and pages: Tina. Technical LeadLock: Danielle. Creatives: Ivy. Whitney sends final client communication and reviews |
| Other trackers | Only Slack and ClickUp. Emails waiting on a team member get a forward-icon tag in the inbox |
| What makes it done | ClickUp complete, almost always with a Slack update. Gisselle reviews overdue tasks weekly with a ClickUp filter, and also learns status in the Monday meeting. She marks tasks complete herself, or asks the owner |
| Due dates | Onboarding tasks have checklist deadlines plus a project-deadline recap. Targets: landing-page feedback about 3 business days; accelerator ad launch about 3; creative edits about 2; client replies 1–2; client emails within 24 hours; new copy about a week; technical fixes longer. These are not always met and are still to be confirmed with Whitney |
| Fathom | The key is a Team plan key, shared across the team (confirmed 30 Oct) |

### 8.2 Is everything in both Slack and ClickUp?

**Not yet.** Both directions are partial.

Slack @asks with a ClickUp task for the same client, created from 14 days before to 7 days after the ask:

| Period | Asks | Matched automatically |
|---|---|---|
| Last 30 days | 15 | 2 (13%) |
| 31–60 days | 17 | 7 (41%) |
| 61–90 days | 18 | 4 (22%) |
| 91–180 days | 34 | 15 (44%) |
| Older | 125 | 16 (12%) |

The automatic match under-counts. A manual check of 13 unmatched recent asks found 6 in ClickUp under different wording, such as a pixel fix in GTM or an investment guide. That puts real Slack → ClickUp coverage at **roughly half to two-thirds** in the last 90 days.

**What stays only in Slack** is mostly quick, reactive work:
- "please respond to the client's email today"
- "remove the lodging mention from the ad ASAP"
- "draft a follow-up"
- "a call recap needs to go out"
- "check ads data against actuals"
- a newsletter request
- spam calls

**ClickUp tasks seen in Slack:** about 33–50% of tasks created in the last 90 days have a related Slack message. Templated onboarding subtasks are rarely discussed in Slack.

**Implication:** ClickUp is the main action list, but not a complete one. The register should:
- use ClickUp tasks as actions;
- attach Slack, email and meeting evidence to them;
- **propose** an action for a Slack or meeting ask that has no matching ClickUp task, as a Needs review item with a "Create in ClickUp" option.

That last check is the gap Gisselle can't easily see today.

### 8.3 Is it getting better? (trend)

| Created / posted | ClickUp tasks with no assignee | Open, no assignee | Slack @asks with no thread reply |
|---|---|---|---|
| Last 30 days | 27% (101 of 372) | 67 | 26% (4 of 15) |
| 31–60 days | 15% | 24 | 23% |
| 61–90 days | 25% | 32 | 27% |
| 91–180 days | 20% | 20 | 44% |
| Older than 180 days | 51% | 81 | 39% |

- **Slack replies improved clearly.** Asks with no reply fell from about 40% in older history to about 25% in the last 90 days.
- **ClickUp assignment improved from the older 51%, but isn't fixed.** It's 15–27% in recent months, and 67 tasks created in the last 30 days are open with no assignee. Most are checklist subtasks created from templates.
- The earlier "22% unassigned" and "39% no reply" figures were all-time numbers. The older history makes them look worse than the current state.

### 8.4 How repetitive are tasks? (for suggested deadlines)

A ClickUp task counts as repetitive when its name, with client names removed, matches a template task or is used for 3 or more clients.

| Space | Repetitive |
|---|---|
| Onboarding Clients | 90% |
| Foolproof Follow-Up Advantage | 92% |
| VIP Days | 88% |
| Elevate Clients (ongoing work) | 34% |
| Accelerators, WIA Internal | Recurring patterns per member (e.g. "Launch Client Attraction Campaign for &lt;member&gt;"). The method under-counts these |

All spaces together: about 67–75% of tasks created in the last 90 days are repetitive.

**Slack @asks by type** (first match; keyword rules):

| Type | Share |
|---|---|
| Ads launch or changes | 35% |
| Copy, email or sequences | 22% |
| Landing pages | 11% |
| Creatives | 9% |
| LeadLock/GHL technical | 7% |
| Client communication | 3% |
| Reports | 3% |
| Other / one-off | 10% (3 of 50 in the last 90 days) |

**Conclusion:**
- **About 90% repetitive holds for onboarding-type work, but not for ongoing Elevate work.** Those tasks are specific, e.g. "investigate sales drop" or "test retargeting on the updated page".
- **About 90% of asks do fall into a handful of recurring task types.** So suggested deadlines should be set **by task type**, not by matching individual tasks:
  - checklist tasks keep their template or checklist dates;
  - other tasks get a type-based "suggested by" date from the turnaround targets;
  - one-offs show "No due date".

### 8.5 The three "finished" statuses

Statuses are set per space, and a list can override them. Lists built from the onboarding template carry the onboarding statuses wherever they live.

| Space | Statuses defined on the space | Finished statuses actually used (all tasks) |
|---|---|---|
| Onboarding Clients | to do, in progress, on hold, **done** (done), **n/a** (done), **Closed** (closed) | done 544, Closed 93, complete 14 |
| Elevate Clients | to do, **complete** (closed) | complete 301, done 102, Closed 1 (onboarding-template lists) |
| Foolproof Follow-Up Advantage | to do, in progress, complete | done 221, Closed 21 (onboarding-template lists) |
| Accelerators, WIA Internal | to do, in progress, complete | complete |
| VIP Days | to do, in progress, complete | Closed 12, done 6 |

- In ClickUp, **"done" is the Done type and "Closed"/"complete" are the Closed type**. Both mean finished. The difference is only that the Closed type hides tasks from default views.
- **For the KB:** all three map to Done. "n/a" maps to Cancelled.
- **Still to confirm with WIA:** whether moving a task from "done" to "Closed" means something to them, such as "reviewed by Whitney".
- **What the timestamps show** (ClickUp sets `date_done` for any finished status and `date_closed` only for the Closed type; there is no status history in this pull):
  - **done (874):** always stays at done; none was later closed.
  - **Closed (127):** only 17 were "done" first (median 1.4 h earlier). The rest went straight to Closed. 70 were closed in same-minute batches of 5 or more.
    - Carmen (36) and Tina (33) mostly close; WIA Support (220) and Danielle (115) mostly use done.
    - This looks like a personal habit: ticking the checkbox versus picking "done" from the dropdown.
  - **complete (658):** the only finished status in Elevate, the accelerators and WIA Internal. 157 were "done" first, a median of about 75 days earlier, and 252 were changed in batches. This possibly happens when a client's lists move from Onboarding to Elevate.
  - **n/a (39):** checklist steps that don't apply, e.g. "Send referral fee (if applicable)", "Send reminder", "Create Slack channel". Mostly set by WIA Support.
- **Where to see this:** in ClickUp, open the space's **⋯ → Space settings → Task statuses**. For a single list, open the list's **⋯ → List settings → Task statuses**; a list with custom statuses overrides its space.

### 8.6 Features decided (30 Oct, Jainil)

- **Suggested deadlines:**
  - The KB shows a "suggested by" date from WIA's turnaround target for the task's type, labelled as a target and separate from the real due date.
  - It ships only after sufficient testing, and WIA must confirm the targets first.
- **Reconciliation suggestions:**
  - When Slack (or a meeting) shows a task is done but ClickUp is still open, the KB raises a suggestion to mark it complete.
  - Who receives it (Gisselle or the owner) is a setting.
  - Marking complete goes through the normal ClickUp write-back, under the person's own name.


## 9. Daily volumes: email, calls and ClickUp (30 Oct)

Read-only pulls of `hello@` Gmail headers (all 4,997 messages in the last 90 days), the `hello@` Calendar, Fathom (Team key) and the 29 Oct ClickUp export. "Per day" means per business day (Mon–Fri). Senders are classified by rules, so treat the numbers as approximate.

### 9.1 Email at hello@

| Type | 90 days | Share | Per business day: mean / median / p90 |
|---|---|---|---|
| Automated: platforms, notifications, newsletters | 3,557 | 71% | 49 / 40 / 78 |
| **Client threads** (a client address is a participant) | **820** | **16%** | **12.5 / 12 / 21** |
| Other people: leads, prospects, accelerator members, past clients, vendors | 367 | 7% | 5.4 / 4 / 11 |
| Internal (team only) | 180 | 3% | 2.4 / 2 / 6 |
| LeadLock system | 39 | 1% | 0.6 |
| Partners (Celebrate Creative, Tirzah, the web vendor) | 34 | 1% | 0.5 |
| **All** | 4,997 | | **70 / 63 / 92** |

- **Client email splits evenly:** 437 received and 383 sent. About **7–8 client threads are active on a typical business day** (p90 12–13). The last 30 days look the same.
- **Most client email comes from onboarding clients.** Pecan Springs (77 received), Ridgefield (45), The Elia (36), Press Record (29) and Funktastic (18) lead; many clients send fewer than 10 in 90 days.
- **Only about 1 in 6 emails is client communication.** Filtering automated mail first removes about 70% of the volume before any extraction runs.

### 9.2 Calls

| Source (90 days) | Client calls | Sales / prospect | Programme group calls | Internal | Other |
|---|---|---|---|---|---|
| hello@ Calendar (2+ attendees) | **44** (~3.4/week; 17 in the last 30 days) | 10 | 6 | 62 | 34 (co-working blocks, misc.) |
| Fathom recordings | **22** | 3 | 4 | 17 | 13 |

- **About 0.7 client calls per business day:** median 0, up to 4 on busy days, mostly onboarding calls and monthly strategy calls.
- **Fathom recorded about half as many client calls as the calendar shows** (22 vs 44). Recordings come from Whitney (38) and Carmen (21). Either some client calls aren't recorded, or Fathom labels them differently. **Check this with WIA**, since calls are the second main source of requests.

### 9.3 ClickUp tasks

Bulk = 5 or more tasks created in the same list in the same minute, i.e. a template applied.

| Created (last 30 / 90 days) | Total | Per business day: mean / median / p90 / max |
|---|---|---|
| Manual, top-level | 87 / 307 | **4.0 / 2.5 / 10 / 22** (90 days: 4.8 / 3.5 / 11) |
| Manual subtasks | 53 / 127 | 2.4 / 1 / 5 (90 days: 2.0) |
| Template-applied, top-level | 70 / 338 | Bursty: median 0, max 40–78 on the day a client starts |
| Template-applied subtasks | 157 / 598 | Bursty: median 0, max 87–135 |
| Completed (last 30 days) | | 14.6 / 13 / max 37 |

- **Hand-made tasks average about 4–7 a business day,** counting top-level tasks and subtasks. **WIA Support (Gisselle) creates about 80% of them** (342 of 434 in 90 days).
- **Template tasks come in bursts** when a new client starts onboarding: 50–200 at once, then none for days.
- Nothing is created at weekends.

### 9.4 What this means for the Action Register

| Source | Realistic new actions per business day |
|---|---|
| ClickUp, hand-made | ~3–7 (p90 about 15) |
| ClickUp, template | 0 most days; 50–200 on a client's start day. Show them as an onboarding checklist, not as individual new actions |
| Email to propose (client threads with no ClickUp task) | Unknown until extraction is tested: 7–8 client threads a day carry the requests, approvals and replies |
| Calls | ~0.7 client calls a day, each with a few follow-ups |
| Slack asks (4 connected channels only) | ~0.8 a day |

- **Review load:**
  - With email and calls proposing only actions that aren't already in ClickUp, Needs review should see **a handful of items a day, not dozens**.
  - The main cost is the 63–70 emails a day that have to be filtered first. Filtering automated mail by rules removes about 70% of them before any LLM call.

## 10. Platform alerts: can subjects alone catch them? (30 Oct)

**Data:** 90 days of `hello@` email, read-only. 3,597 automated emails; 898 of them from ad, web and CRM platforms (Google, Meta, LeadLock/HighLevel, Squarespace, TikTok, Microsoft and others). The subject filter used keywords such as payment, failed, verification, disapproved, policy, expired, balance and action required. Every match was then opened and read.

### 10.1 What the subject filter caught (66 emails)

| Group | Emails | Client-related, needs action? |
|---|---|---|
| LeadLock "Facebook connection has expired" | 6 | **Yes**: The Penny ×3, Sunlover ×3 |
| LeadLock "Sub-account wallet balance negative" | 2 | **Yes**: Dogwood, Ridgefield |
| Google Ads "Policy issues" / "Asset groups disapproved" | 2 | **Yes**: The Elia |
| Google Ads "Your ads are reaching a limited audience" | 1 | Yes, a recommendation (only a Customer ID) |
| Meta "Avoid a payment issue on your next charge" | 1 | Yes (account unclear) |
| Google Ads "You've completed advertiser verification" | 3 | It resolves an earlier action (only a Customer ID) |
| Meta "You no longer have access to page/ad account …" | 4 | Mostly past clients and non-clients (offboarding) |
| Search Console "pages not indexed" | 2 | One past client, one WIA's own site |
| Google Ads "[Action required] Review security request" | 9 | WIA's own manager account. Internal admin, not a client |
| Google account security alerts, verification codes | 9 | WIA's own accounts. Internal |
| Squarespace subscription and renewal notices | 7 | WIA's own billing |
| Marketing ("limited spots", webinars, policy-update news), Google reps' sales pitches, TikTok, others | ~20 | No |

- **Client alerts that need action: about 15 in 90 days, roughly 1–2 a week.** That's about 23% of what the subject filter caught; another ~14% are internal admin tasks.
- **Subject alone rarely names the client:** only 2 of 66.
  - The **body** names it for LeadLock alerts, every time (the sub-account name), and for some Google Ads emails (the account name, e.g. "FS - The Elia").
  - The rest carry only a **Google Ads Customer ID**, which needs an ID → client map.
- **Most client-account alerts never reach hello@.** Meta and Google email the account's own admins, often the client. For example, the Dogwood Meta payment alert reached WIA only because the client forwarded it. hello@ sees LeadLock alerts (WIA's own platform) and Google Ads alerts for accounts under WIA's manager account.

### 10.2 What this means

| Approach | Detects the alert | Finds the client | Verdict |
|---|---|---|---|
| AI reads subjects only | About 1 in 4 matches is a real client alert; the rest need judgement | **About 3%** | Not enough on its own |
| Fixed rules (known sender + subject template), then the body of those few emails only | Close to 100% on the known templates | LeadLock 100% from the body; Google Ads by account name, or by Customer ID with a small ID → client map | **Recommended**: no AI needed, 1–2 emails a week to fetch |

**Proposed approach:**
1. Start with about 8 alert templates: Facebook connection expired, wallet negative, policy issues, asset groups disapproved, limited audience, payment issue, advertiser verification due/completed, lost access.
2. Fetch the body only for matches, and extract the sub-account, account name or Customer ID.
3. Raise an action in the Action Register with a suggested owner: LeadLock → Danielle, ads → Carmen or Jacqueline.
4. Merge repeats. "Facebook connection expired" arrived 3 times for The Penny, so that's one open action, closed by the matching "resolved" or "verification completed" email.

Coverage stays partial, because many alerts go to clients' own inboxes. Reading the platforms directly (Google Ads manager account, Meta Business) would be the complete version, later.

## 11. WIA's answers, round 2 (Gisselle, received 30 Oct, recorded 2 Nov)

| Topic | Answer | What it means for the KB |
|---|---|---|
| LeadLock replies | Replies go by email. With the LeadLock two-way sync they appear in both LeadLock and hello@. Texts: not confirmed ("I believe…") | Email replies are already covered by hello@. **LeadLock texts are still unconfirmed** and may never reach Gmail. Treat them as a known gap until checked |
| support@leadlockpro.com | Danielle's own inbox for LeadLock clients. Not forwarded; she **copies hello@leadlockpro.com most of the time** | Most LeadLock-client mail reaches **hello@leadlockpro.com**. Connecting that one mailbox would cover most of it. support@ itself stays a gap unless connected too |
| hello@leadlockpro.com | Used to talk to clients mainly when onboarding a **LeadLock-only** client | Likely the main channel for the FFA/LeadLock-only clients, which explains why Evergreen, SK Designs and the other FFA clients have little or no mail in hello@weddingindustryads.com |
| Monday team meeting | "All Monday meetings are recorded with Fathom" | A source for "done"/progress updates across clients (one meeting, many clients: associate per segment, not per meeting). **Check needed:** the Fathom Team key shows only 4 "WIA Weekly Meeting" recordings since 1 Aug (about 13 Mondays). The rest may be recorded under another title or by someone whose recordings aren't shared with the team |
| Project-deadline recap | Lives in ClickUp, and Gisselle posts a summary in Slack | Due dates come from ClickUp. Gisselle's Slack summary is a second source: the bot must be in that channel |
| Finished statuses | **done** = onboarding (keeps a visible list of completed tasks); **complete** = client management (archives the task); **Closed** = used by mistake in onboarding (Gisselle switches it to done or uses "show all completed") | All three mean Done. Batch "Closed" tasks are corrections, so their close date is less reliable. **Write-back rule:** set "done" in onboarding lists, "complete" in client-management lists, never "Closed" |
| n/a | The step doesn't apply to the client | Show as "not needed" and leave it out of onboarding progress |
| Slack channels | Gisselle can't see Whitney and Daniela's private channels; "as long as it's a client-related channel" | The bot joins only client-related channels. Get Whitney's list of channels to stay out of |
| ClickUp OAuth app | **Option A approved:** set it up using the hello@ login | Unblocks Stage 1 write-back (see the stages doc) |

Still unanswered: whether done → complete about 75 days later is the Onboarding → Elevate move (§8.5); whether LeadLock texts reach hello@.

## 12. Is "in progress" used in ClickUp? (checked 2 Nov)

**Method:** ClickUp keeps a status history only when the "Time in Status" ClickApp is on, and it's **off** in WIA's workspace (the API returns empty histories). Instead, two full snapshots (29 Oct and 2 Nov, all non-archived tasks, templates excluded) were compared, plus each space's status set.

| Finding | Detail |
|---|---|
| Elevate Clients can't use it | That space's statuses are only "to do" and "complete". Onboarding offers "in progress" and "on hold"; the other spaces offer "in progress" |
| Open tasks today | to do **518**, recurring 86 (a status for repeating tasks, not progress), **in progress 13**, on hold 4 |
| Who uses "in progress" | Recently, only **Danielle**: 4 onboarding (LeadLock) tasks touched on 30 Oct. The other 9 are **stale**: last touched June–August 2026, 3 from 2025, several unassigned |
| What actually happened 29 Oct → 2 Nov | **31 tasks finished, all straight from "to do"** (20 → done, 6 → Closed, 3 → complete, 1 → n/a) or from recurring. **None went through "in progress"** |

**Conclusion:** the team works **to do → done/complete**. "In progress" is used by one person (Danielle, LeadLock onboarding), and is otherwise left behind on old tasks. This matches Gisselle's answer and §4.1 (Slack rarely shows progress either).

**For the KB:**
- Use **Open → Done**, plus Acknowledged from Slack replies like "will do".
- Show ClickUp's "in progress" / "on hold" **only where a task really has it**. Don't infer it.
- **Flag stale ones:** "in progress" with no update for 30+ days goes into a cleanup list for Gisselle.
- Optional: if WIA turns on the "Time in Status" ClickApp, the KB gets real status history (when work started, how long it took).
