# MVP vs React frontend, and where every card's data will come from

Written 4 Nov 2026. It compares the deployed MVP page (`mvp/real_index.html`) with the React source (`frontend/src`), and maps each card and field of the **Action Hub** (finalised) and the **Client Portfolio** (provisional) to its data source today and in production. It feeds the S7–S9 table design (see `backend/docs/production-readiness.md` §4).

> Repo file: no client names or personal data. The real-data build and its overlays stay in `backend/.local/raw_pull/`.

---

## 1. How the pieces relate

```
frontend/src (React)  --npm run export-->  frontend/exports/client-portfolio.html
                                                     | copied 2 Nov
                                                     v
                                   mvp/index.html  <-- hand-edited for the MVP reviews (readme_changes.md)
                                                     | build_real_index.py
   base.json (export_frontend_snapshot.py, from the KB DB) + overlay/<client>.json (hand-written, cited)
                                                     v
                                   mvp/real_index.html  (deployed)
```

**Key finding: the MVP changes exist only in `mvp/index.html`, not in the React source** (stated in `mvp/readme_changes.md`). The React app is **behind** the MVP. Before wiring the frontend to the API, either:
- (a) port the MVP changes back into `frontend/src` and treat React as the source again (recommended: the API work happens in React), or
- (b) treat the hand-edited HTML as the product. That isn't sustainable: every re-export loses the edits.

---

## 2. What the MVP changed compared with the React source

From `mvp/readme_changes.md` (v1, 2–4 Nov). Each of these must be ported to React (option a).

**Action Hub**
- Renamed Action Register → **Action Hub**. The v1 page (`#actions`) and the "Revised" page (`#actions-v2`) were **removed**; v2 · Teams (`#actions-v3`) is the only Action Hub, and old links redirect to it.
- **KPI cards:** Pending (you) / Pending (team) / Pending (client) / Completed. They act as filters, have ⓘ tooltips, and the selected one blinks. The filter bar keeps only **Needs review**.
- **Board:** client initials as the avatar; plain date (red when late); priority bottom-right; done check top-right; a hover tooltip with timing ("N days late", "Due today", "No due date"…). A filtered single column spreads into a grid.
- **Drag and drop:** between the four columns, or onto a KPI card, to change stage. Dropping on Completed opens "What shows it's done?".
- **Pending (team) always asks "Who should own it?"** The list shows the client's account team first (from ClickUp), then other members, never yourself. The new owner must acknowledge.
- **Action window:**
  - Source and ClickUp links removed; "Sources disagree" kept.
  - "Mark blocked" replaced by a **Change status** menu.
  - Comment box starts collapsed.
  - **Internal tasks** (accelerator upkeep) open the full window and show their recurrence.
- **Ping on Slack:**
  - on Pending (team/client) actions; posts to the client's channel, or the accelerator channel for Internal tasks;
  - a history line, a "Sent N mins ago" timer, a 2-minute cooldown, and a Slack mark on the board card;
  - **preview only today**.
- **Add action:** the Type field is removed (saved as Admin); Priority is on its own.
- **List view:** one line per row (title, client, person, date).
- **"Programme ops" renamed "Internal" everywhere.** The account-scope explanation line is removed (visibility rules unchanged).
- **Header:** title and sync chip on one line; workspace search (⌘K) removed; fit-to-screen toggle for 1280–1919px laptops.

**Client Portfolio and the client record**
- **Card menu:** Open client record · **Pin to top** · **Mark as archived / Restore**. Adds an **Archived** tab. Pins and archive are **saved in the browser only** (localStorage).
- **List view:** one line per row.
- **Record:**
  - Tabs reordered: Now · Profile · Commitments · Meetings · History · Handover brief · Health (Soon) · Support · Invoices & terms (Soon) · Accounts & sources.
  - Compact header.
  - The **Now** tab is a 2×2 grid (Next meeting, Last meeting, Action items, Client sentiment) plus Communication this week.
- **Sidebar:** Overview, Call preparation, Health & sentiment, Client 360 and Invoices & contracts moved to **Coming soon**, with a route guard that blocks them. **Client portfolio is the landing page.**

---

## 3. Action Hub (finalised): element → data → source

Legend for "Today": **Snap** = generated from the KB DB by `export_frontend_snapshot.py`; **Hand** = hand-written overlay; **UI** = browser only (lost on reload or shared nowhere).

| UI element | Data it needs | Today | Production source | Stage / table |
|---|---|---|---|---|
| KPI counts and board columns | Each action's stage (you / team / client / completed), from owner, side, status and the viewer | Snap (ClickUp tasks) | Derived per viewer | S8 `actions` + S9 read model + S10 viewer |
| Card: client initials, title, place | Client, title, client or Internal (programme) | Snap | Client registry + action | S2, S8 |
| Card: date, "N days late" | Due date (typed: none / date) | Snap (ClickUp due) | ClickUp due date; extracted deadlines with evidence; "No due date" when unknown | S8 (`due`, never invented) |
| Card: priority | High / Medium / Low | Sample default (Medium) | **No source:** ClickUp priority is used on about 0% of tasks. A KB-only field, or dropped (D14) | Decision |
| Card: done check / "What shows it's done?" | Completion basis and evidence | Hand (`actions_patch`, 2 clients) | Command plus evidence: a ClickUp status change, a Slack "done", a meeting quote | S8 commands + S7 evidence |
| Owner, Assigned / Acknowledged chip | Owner (person), assigned date, acknowledgement method | Snap (ClickUp assignee); ack is a sample | ClickUp assignee → person (S3). Ack from a Slack reply ("will do", 👀 per Settings, Q13) or the KB button | S3 people + S7 Slack signals + S8 |
| **Pending (team) "Who should own it?"** | Account team per client, with roles | Sample ClickUp-assignee roles | `account_team_members` (built in S3, waiting for WIA confirmation) | S3 ✅ table, S11 endpoint |
| Change status / drag moves | Commands: assign, move side, reopen, complete | UI only | Commands with `expected_revision`, written to history; ClickUp write-back through the outbound guard | S8 + S12 |
| History and comments | Event log, notes | Snap history (sample) | `action_events`, `action_notes` | S8 |
| "Sources disagree" | Conflicting dates or values across sources | Sample | Reducer flags a conflict, then a proposed correction | S8 reducer |
| **Needs review** (admins) | Review items with a reason (stale, owner unclear, client unclear, duplicate, AI proposal, checklist incomplete) | Sample | `review_items` from extraction and the reducer, plus "create in ClickUp?" for Slack-only asks | S7 + S8 |
| **Ping on Slack** | Target channel, message, sent time, cooldown | UI only (preview) | Outbound request → **approval** → send (guard built 2 Nov). The send log gives "Sent N mins ago" | S12 ✅ guard/log; **decision** below |
| Add action | Manual action (title, client, owner, due, priority) | UI only | Create command; optional "create in ClickUp" | S8 (+ S12) |
| Internal tasks (accelerators) | Programme, owner, due, recurrence | Sample | ClickUp accelerator spaces (programme lists; "recurring" status) | S2 scopes (G-07), S8 |
| Sync chip ("1 source failed to sync") | Per-source last success and failures | Snap (a staged failure is blanked in the build) | `sync_streams` / `sync_runs` freshness | S6 + S9 |
| Notifications drawer (deadline-change requests) | Deadline requests and approvals | Sample | Correction / deadline-request command (D13) | S8 |
| List search ("Search action items…") | Text search | UI (client-side) | Trigram search endpoint | S11 |
| Viewer (who "you" is) and visibility | Session, role, account-team visibility, finance access | Viewer switcher (sample) | KB login + `clients_for_person` | S10 |

**Data-quality rule learned from the learning run:** the snapshot holds 648 actions for 4 clients, many of them **template tasks from archived onboarding lists**. Open actions must exclude archived-list tasks (O-8) and show onboarding checklists as progress, not as dozens of open actions.

---

## 4. Client Portfolio (provisional): element → data → source

| UI element | Data | Today | Production source | Stage |
|---|---|---|---|---|
| Card: logo | Client logo | Hand (overlay `logo`) / extracted | Logo asset per client (upload, or extracted from Drive or website once) | S2 + admin upload |
| Card: name, service, engagements, lifecycle | Registry + engagements + lifecycle stage | Snap + Hand (`record.engagements`, `lifecycle`) | `businesses`, `service_engagements`, lifecycle (P6 names from WIA) | S2 |
| Card: owner / account team | Owner + team | Hand (`record.owner`, `team`) | `account_team_members` | S3 ✅ (WIA to confirm) |
| Card: open / overdue counts, next call | Counts, next meeting | Snap | Read model | S9 |
| Card: health | — | Coming soon | Stage 3 (health) | later |
| **Card menu: Pin to top** | Per-person pin | **UI only (localStorage)** | Per-user pin table | new small table (S9/S10) |
| **Card menu: Mark as archived** | Archived state | **UI only (localStorage), hides from the portfolio only** | **Mismatch:** in the backend, archive = `businesses.status=inactive` and **pauses sync** (decided 29 Oct), for everyone | **Decision** below |
| Record strip: client since, earliest evidence, processed through, sources | Coverage | Snap | `coverage_windows`, `sync_streams` | S5/S6 + S9 |
| Now: Next meeting | Calendar | Snap | Calendar events matched to the client | S4 ✅ + S9 |
| Now: Last meeting summary and decisions | Fathom summary + decisions | **Hand** (`meetings`, 3–6 per client) | Fathom summary units (cited) + extracted decisions | S7 |
| Now: Action items | The client's open actions | Snap | S8/S9 | S8 |
| Now: Client sentiment | Sentiment | Hand / sample | No source yet: Coming soon (Stage 3), or extracted with evidence | later |
| Now: Communication this week | Emails and Slack per day, awaiting our reply | **Gap:** COMMS isn't covered by the live data; the build swaps a literal | Gmail and Slack metadata (pointer storage) + read model | S4 (pointer) + S9 |
| Profile: summary, focus, story, audience, differentiator, voice, goal | Client marketing profile facts | **Hand** (12 fields per client) | Fact extraction from questionnaires, calls and Drive, with evidence; "Unreviewed questionnaire answer" fallback | S7 (`profile_facts`) |
| Profile: standard facts block | ~6 facts | **Hand** (`profile_prepend`) | Same | S7 |
| Profile: contacts, related people, links | Contacts, partners, links (ClickUp, Drive, LeadLock, Slack) | Hand (`record.contacts`, `related`, `links`) | Approved contacts + roster + partner links + approved scopes | S2 ✅ / S3 ✅ |
| Onboarding phase and steps | Phase and checklist progress | **Hand** (`record.onboarding`) | Derived from the ClickUp onboarding lists (statuses, the n/a rule, Phase custom field) | S9 (derivable today) |
| Commitments tab | Commitments said in calls, Slack and email | **Hand** (`actions_add`, 2–3 per client) | Action extraction with evidence | S7 → S8 |
| Meetings tab | Calls + recordings + summaries | Snap + Hand (`calls_patch`, `callMeta_patch`) | Calendar + Fathom, linked | S4 + S7 |
| History tab (milestones) | 14–18 curated moments per client; bursts counted, not typed | **Hand** (`moments`) | Milestone extraction (one moment per burst of work), citing sources; the build's burst counter becomes a job | S7 + S9 |
| Evidence tags (Decision / Client signal / Commitment / Delivery) | Tag per cited item | **Hand** (`evidence_tags`, ~31 per client) | Extraction classifies evidence | S7 |
| Handover brief | Narrative draft and approval | Hand (`record.narrative`) | Owner-written in Stage 1 (P2 is Stage 2); assembled sections are deterministic | S9 |
| Support tab | LeadLock support items | Hand / sample | **No source** until the LeadLock mailboxes are connected (O-11) | blocked |
| Accounts & sources | Approved scopes, mapping suggestions, coverage | Snap | S2 mapping + coverage | S2 ✅ + S9 |
| Timezone | Client timezone | Hand | Client registry field | S2 (add a field) |

---

## 5. What the overlays tell us: the extraction backlog (S7)

Everything marked **Hand** above was written by a person from the learning-run data. That's precisely what S7 must produce automatically, with citations:

| Output | Per pilot client (hand-written) | S7 contract |
|---|---|---|
| Profile facts (12 narrative fields + ~6 standard facts) | 12 + 6 | `profile_fact` |
| Meeting summaries and decisions | 3–6 | `meeting_summary` (Fathom summary first, extracted decisions) |
| Commitments from calls, Slack and email | 2–3 | `action_candidate` |
| Proof that a ClickUp task is done | ~5 (2 clients) | `completion_signal` → reducer |
| History milestones | 14–18 | `milestone` (bursts grouped, counts computed) |
| Evidence tags | ~31 | `evidence_classification` |

The **50-thread accuracy test** (deferred to prompt drafting) should use these hand-written outputs as the gold set: they're cited and reviewed.

---

## 6. Mismatches and risks to resolve

1. **The MVP edits aren't in React** (§1). Decide (a) port them back, or (b) keep editing HTML.
2. **Archive means two different things:** a per-browser hide in the MVP, versus a global "pause sync" in the backend. Options:
   - **Admin-only archive** (global, pauses sync) plus a **per-person "hide from my portfolio"**; or
   - a single archive for admins only.
3. **"Ping on Slack" vs the approval rule:** in the MVP a ping is one click. In the backend every Slack send is a request that a listed approver must approve (2 Nov). Options:
   - pings become approval requests (slower; the cooldown logic still applies); or
   - give team members a per-user "send pings" permission with a narrow template, while keeping the guard and kill switch.

   **Needs Jainil's decision.**
4. **Priority has no source** (ClickUp ~0%). Keep it as a KB-only field (not written back), or drop it.
5. **The deployed MVP page is public with no login and holds real data for the 4 pilot clients** (stated in `mvp/README.md`). Until S10, consider a login in front of it (for example Railway private networking or basic auth in the Caddyfile), or stub data.
6. **Open action counts include archived template tasks:** the read model must exclude them (O-8).
7. **The COMMS card has no live source:** it needs Gmail and Slack metadata in the read model, which comes after the email pointer change (BF-2).

---

## 7. Next steps

1. Decide on §6 items 1–5.
2. If (a): port the MVP changes into `frontend/src` (the Action Hub first, since it's final).
3. Design the S7 contracts from §5 and the S8/S9 tables from §3–§4, using the learning-run data as fixtures.
4. Build the read-model API (S11) for the Action Hub cards first, then the Portfolio as its design settles.
