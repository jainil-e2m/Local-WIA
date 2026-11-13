# Tab 5 — Call Preparation

**Status:** Draft · C1–C4 decided 22 Oct 2026 · v2 mockup layout added (under review) · Stage 2
**Labels:** **[Agreed]** = already decided (FR-CAL, KB-CH-69). **[Proposed]** = new in this draft. **[Finding]** = from sources.

---

## 1. What this tab is for

**One question:** *What do I need to know, ask and resolve on this specific call?*

For every scheduled client call, the KB prepares a **short, cited brief shaped by the type of call**, and after the call it closes the loop: what was decided, what's now owed, what to send. It is the KB's direct replacement for Viktor's daily call prep, which WIA values but finds verbose and unaware of call types.

---

## 2. What WIA does today [Finding]

| Today | Source |
|---|---|
| Viktor scans **Whitney's calendar every morning** and briefs her on each call: account status, what to focus on, "in theory" the last call and its open items. Covers client and sales calls | Sep 22, 24:11, 31:34 |
| **Complaints:** "very verbose… a lot of reading to sift through"; "he'll tell me things that I need to do that really don't need to be done at all"; doesn't know what each call type is for | Sep 22, ~31:00 |
| Call types Whitney named: **ads kickoff** (introductions, expectations, connecting ad accounts) → **messaging & positioning interview** (deep-dive questions) → **monthly strategy calls**; plus **LeadLock kickoff** (Danielle) | Sep 22, ~31:00; Sep 2 |
| Before the messaging interview, Viktor compares the **onboarding questionnaire** (and website) with Whitney's interview questions and reports what's still unanswered | viktor_at_wia.md 1.2 |
| Before LeadLock kickoffs, Whitney asks Viktor to brief Danielle on what matters from the sales and onboarding calls (e.g. current CRM), "when I remember to" | viktor_at_wia.md 1.3 |
| Accelerator **office hours** are group calls (Carmen: Google; Jacqueline: Meta) | ClickUp, Fathom |
| Open spec from M05: **short format, call-type templates, what counts as a "top" opportunity** | running_threads.md |
| Whitney: sales calls "wouldn't really fall into the client knowledge base" | Sep 22 |

**Design consequences:** briefs are **short by default**, built from **WIA-defined templates per call type**, and say only what that call needs.

---

## 3. Who uses it

| Person | Calls | What they need |
|---|---|---|
| **Whitney** | Ads kickoffs, messaging interviews, monthly strategy, creative reviews | A 30-second read before each call; the client's open asks; what not to waste time on |
| **Danielle** | LeadLock kickoffs, LeadLock check-ins | What was said in sales/onboarding that affects the build (CRM, who handles inquiries, forms, calendar) without asking Whitney |
| **Carmen, Jacqueline** | Google / Meta office hours (group) | Per attending member: last session's commitments and open asks |
| **Gisselle** | Programme check-ins | Attendance drift and asks |
| **Anyone covering a call** | Any | The same brief, so cover needs no hand-off chat |

---

## 4. Call types and templates [Proposed]

Each call type has a **template**: its purpose, the sections it shows, what to leave out, and an agenda skeleton. **Decided (C2): WIA-defined templates**, editable by admins.

| Call type | Purpose | Brief focuses on | Leave out |
|---|---|---|---|
| **Ads kickoff** | Introductions, set expectations, connect ad accounts | People and roles; what was sold (scope, not price); questionnaire status; access checklist (which accounts are connected); expectations to set | Performance, strategy opinions |
| **Messaging & positioning interview** | Deep-dive on the business | Questionnaire answers relevant to the interview, the client's open asks, voice notes so far. (The automatic *gap check* is not in the first version, C4) | Ads, actions unrelated to messaging |
| **LeadLock kickoff** | Plan the LeadLock build | Current CRM and owner, who answers inquiries, forms/calendar in use, anything said in sales/onboarding calls about follow-up; open setup issues; access | Ads strategy |
| **Monthly strategy** | Review and plan | Since last strategy call: decisions, what was delivered, open items both sides, client's unanswered asks, Health causes, LeadLock outcomes, *Ads (Viktor)* rating (attributed); one top opportunity; agenda | Onboarding detail |
| **Creative review** | Approve creative | Pending approvals, assets received, voice and words to avoid, feedback on earlier creative | Lead numbers |
| **Office hours** (group) | Programme coaching | Per expected member: last session's commitments, open asks, attendance; shared-session note (only each member's own parts) | Other clients' details beyond the group |
| **Programme check-in** (1:1) | Re-engage an accelerator member | Attendance drift, their asks, programme week, one concrete next step | — |
| **Other / unclassified** | — | Generic brief; asks someone to set the type | — |
| *Sales call* | Not a client yet | **Out of scope** [Finding: Whitney] | — |

**How the type is set:** from the calendar event title/booking link where it's explicit (e.g. "Ads Kickoff Call | Harbor House"); otherwise the KB **proposes** a type and the host confirms. A wrong type is worse than none, so an unconfirmed guess is labelled [Agreed: classification is a labelled proposal].

---

## 5. Tab structure

| # | Sub-view | Question |
|---|---|---|
| A | **Call queue** (landing) | Which calls do I have, and is each brief ready? |
| B | **Call brief** | What do I need for this call? |
| C | **After the call** | What was decided, what's owed now, what do we send? |
| D | **Call-type templates** (admins) | What should each type of brief contain? |

### A. Call queue
| Component | Content | Status |
|---|---|---|
| **My calls · All calls** | Same pattern as the register; default *My calls* (host or attendee) | Proposed |
| Range | Today · Tomorrow · This week · custom | Agreed |
| **Call rows** | Time (viewer's timezone, client's timezone on hover), client, **call type** (confirmed or *proposed*), host, duration, **brief state**: Ready · Building · Stale · Needs type · Cancelled | Agreed states |
| Prep signals per row | "2 client asks unanswered" · "1 overdue promise" · Health category | Proposed |
| **Needs type / unmatched** | A call whose type is unclear shows **Needs type** on its row with *Set type*. A dedicated triage panel for unmatched events is **not in the first version (C4)**; unmatched events still show as a count with a link, because exposing ambiguity is agreed [FR-CAL-03] | Agreed minimum |
| Cancelled / moved | Shown struck through; brief marked not applicable [Agreed] | Agreed |
| **Morning prep digest** | 7:00 in-app summary, optionally a Slack DM to the host: today's calls, one line each | **First version (C4)** |

### B. Call brief
**Decided (C1): short by default**: *In 30 seconds* plus the sections the call type needs; *More detail* expands each. Every factual line cited; proposals labelled [Agreed].

| Section | Content | Notes |
|---|---|---|
| **Header** | Client, call type (+ confirmed/proposed), date/time/timezone, duration, host, attendees, link to last call of this type | Agreed |
| **In 30 seconds** | 3 bullets: where things stand, the one thing this call must achieve, the main risk | Proposed (answers "too verbose") |
| **Since the last call** | Decisions, deliveries, changes since the previous call (of any type), with dates | Agreed |
| **They asked, we haven't answered** | Client questions/requests still open, quoted | Agreed (client asks) |
| **What we owe / what they owe** | From the Action Register, current state [Agreed: no stale copy] | Agreed |
| **Agenda** | From the type's skeleton + this client's open items; each item says why it's there | Agreed |
| **Questions to ask** | Missing profile fields, unclear ownership, conflicts (Portfolio §9 *Open questions*) | Proposed |
| **Watch-outs** | Health causes, repeat support issues, sensitive topics; "don't promise X" | Proposed |
| **One opportunity** | At most one, labelled proposal, with the evidence and why it's "top" (criteria → **C5**) | Agreed (cited opportunity) |
| **Type-specific block** | e.g. access checklist (ads kickoff), questionnaire answers (interview), CRM/setup facts (LeadLock), member list (office hours), lead outcomes + Viktor rating (strategy) | Proposed |
| **Sources & limits** | Sources used, as-of time, what couldn't be seen (no transcript of last call, LeadLock unavailable) | Agreed |
| Actions | **Regenerate with instructions…** (see below) · Copy · Download · Print · **Prep done** tick · **Send agenda to client** (draft, a person reviews and sends; first version, C4) | Proposed / decided |

**Never in a brief:** finance for non-admins [F2]; website or other unapproved sources [Agreed]; another client's details from a shared session; Viktor's words as client words.

#### Regenerate with instructions [Requested 22 Oct]
The host (or anyone preparing the call) can ask for a new version of the brief at any time, saying **what else to look at** and **how it should read**.

| Part | Options |
|---|---|
| **What else to look at** | Free text, e.g. "focus on why Google leads dropped", "include everything Sarah said about pricing since August", "Danielle is joining, add the LeadLock setup status" |
| Quick focus chips | *Last call only* · *Since onboarding* · *Client's open asks* · *Support issues* · *Lead outcomes* · *Commitments only* |
| **Tone and length** | Chips: *Shorter* · *More detail* · *Bullets only* · *More direct* · *Softer, relationship-first* · *For a new team member*. Plus free text, e.g. "write it as talking points I can read out" |
| Sections | Turn a section on or off for this version (e.g. hide Watch-outs, add the questionnaire block) |
| Scope | *This call only* (default) · *Suggest for the call-type template* (goes to admins for approval, C2) |

**Rules**
- Instructions can **narrow or re-focus**, never widen beyond approved sources or the user's permissions. "Check their website" or "add the invoice status" for a non-admin is refused with the reason [Agreed source scope, F2].
- Facts stay cited whatever the tone; a tone change never removes citations or turns a proposal into a fact.
- Each regeneration is a **new version** (v1 auto, v2 "focus on pricing, bullets only" by Whitney, 10:12). Previous versions stay viewable; the one marked *current* is what Copy/Download/Send agenda use.
- **Automatic rebuilds keep the instructions.** If the brief goes stale after a custom version (new client email, action changed), the rebuild reuses the last instructions and says so: "Rebuilt with Whitney's instructions after Sarah's 11:05 email." It never silently reverts to the default.
- The instructions are shown at the top of that version, so anyone reading it knows why it looks different.
- Each regeneration counts toward model cost; repeated identical requests reuse the existing version [Agreed cost rules, KB-CH-44].

### C. After the call [Decided, C3: recap + proposed actions + follow-up email draft]
Triggered when the Fathom transcript arrives (webhook) or the host marks the call done.

| Component | Content |
|---|---|
| **Recap** | Decisions, client asks, commitments made (who, what, by when), each linked to the transcript timestamp |
| **Brief vs reality** | Which agenda items were covered; which open asks were answered; what was left |
| **Proposed actions** | New commitments → Action Register (explicit ones as live actions, unclear ones to Needs review) [Agreed rules] |
| **Closes old items** | Asks answered on the call marked answered (with evidence) |
| **Follow-up email draft** | Recap + next steps to the client, in WIA's voice; a person reviews and sends [Agreed: review before external send] |
| **Team note** | Optional Slack recap to the client channel/owner (review-before-send) |
| **No transcript?** | "Call happened but no transcript found" → host can add notes by hand; never treated as "nothing was agreed" |

### D. Call-type templates (admins) [Decided, C2]
Per type: name, how it's detected (calendar title/booking link patterns), purpose, sections on/off, agenda skeleton, interview question list (for the gap check), things to leave out, brief length. Versioned, tested before release [Agreed Q19].

### Client record
The client's **Meetings** sub-tab already lists upcoming calls → links to their briefs; past calls show their recap.

---

## 6. When briefs are built [Agreed mechanism, Proposed timing]

| Trigger | Action |
|---|---|
| Call matched to a client and type | Build the brief (evening before, or immediately if the call is < 24 h away) |
| 2 hours before the call | Refresh if anything changed |
| New client message, action change, correction, meeting moved | Mark **Stale**, rebuild; the stale version stays visible, labelled |
| Call cancelled | Brief marked not applicable; nothing deleted |
| **User clicks Regenerate with instructions** | New version built immediately with those instructions; later automatic rebuilds keep them (see §5B) |
| Transcript arrives | Build the After-the-call recap |

A future invite is never evidence a call happened [Agreed].

---

## 7. Possible additions

| Addition | Value | Dependency | Suggest |
|---|---|---|---|
| **Messaging-interview gap check** | Saves Whitney asking what the questionnaire already answered | Interview question list from Whitney; questionnaire in Drive | High value, **not in first version (C4)** |
| **After-the-call loop** | Turns calls into tracked actions; replaces manual recaps | Fathom webhook | **First version (C3)** |
| **Morning prep digest** | Same habit Whitney has with Viktor, shorter | Slack (D8) | **First version (C4)** |
| **Unmatched-event triage** panel | Prevents silent missing briefs | Calendar | Not in first version (C4); minimal count + link kept |
| **Send agenda to client** | Clients arrive prepared | Review-before-send; Gmail | **First version (C4)** |
| **Prep done tick** | Team sees who prepared | — | Low |
| **Co-host share** | Danielle sees Whitney's notes for a joint call | — | Low |
| **Question bank per type** | Consistent interviews | Templates | Medium |
| **Brief quality feedback** (thumbs up/down + why) | Improves templates | — | Medium |
| Website gap check (as Viktor does) | More complete interview prep | Website research is **not an approved source** [Agreed] | Out unless approved |
| Sales call prep | Whitney uses Viktor for it | Not a client yet; out of KB [Finding] | Out |

---

## 8. Current mockup vs this scope

| Mockup today | Gap |
|---|---|
| One brief layout for every call | No call-type templates |
| Long sections, no "30 seconds" summary | The verbosity Whitney complains about |
| Always "Ready to review" | No Building / Stale / Needs type / Cancelled states |
| No unmatched events, no type confirmation | Silent mismatches possible |
| Commitments show owner and due date as required | Unknown owner/date not handled |
| Nothing after the call | Loop not closed |
| Times shown in IST | WIA works in US time; show viewer's and client's timezones |

---

## 9. Data readiness

| Input | Ready? | Note |
|---|---|---|
| Google Calendar | **Yes** (samples) | Client/host matching and change notifications untested |
| Fathom transcripts | **Yes** (samples) | Webhook for after-call untested |
| Action Register, Profile, Health | Built in the mockup | — |
| Onboarding questionnaire | **Yes** (Drive Docs readable) | Needed for the gap check |
| Interview question list | **No** | Whitney's list needed |
| LeadLock kickoff calls | **Partial** | Danielle's recordings reach Drive only after upload (Sep 22) |
| Viktor prep posts | **Yes** (existing posts) | Attributed only |

---

## 10. Decisions

| # | Decision | Outcome |
|---|---|---|
| C1 | Brief length by default | **Short and expandable**: *In 30 seconds* + the type's sections; *More detail* expands |
| C2 | Call-type templates | **WIA-defined templates per type**, editable by admins. Type from calendar title, or proposed by the KB and confirmed by the host |
| C3 | After-the-call loop | **Recap + proposed actions into the register + answered asks closed + follow-up email draft** (a person reviews and sends) |
| C4 | First-version extras | **Morning prep digest · Send agenda to client.** Gap check and the unmatched-event triage panel are not in the first version (a minimal unmatched count stays) |
| C5 | What makes an opportunity "top" | Open, WIA to define |
| C6 | Timezone shown | Open. Proposed: viewer's timezone, client's on hover |
| C7 | Regenerate with instructions | **Requested 22 Oct:** what-else-to-look-at + tone/length instructions, versioned, carried into automatic rebuilds. Open: whether hosts can save instructions as their personal default for a call type, in addition to suggesting template changes |

---

## 11. Mockup coverage (26 Oct)

Mockup: `frontend/exports/client-portfolio.html#calls`. Built from `src/views/CallPrep.tsx`, `CallPrep.css` and the sample calls, templates and recaps in `src/calls.ts`.

**v2 layout under review (`#calls-v2`, `src/views/CallPrepV2.tsx`).** A meetings board or list leads to each brief. The brief's **Overview is a one-minute read**: the goal of the call, an account pulse, what to settle, what changed, the top talking points, one watch-out and what the brief couldn't see. Last call, full changes, performance, asks and owed items, all talking points and sources sit in sub-tabs. Briefs build automatically 2 hours before each call with the default skill; a call-type skill runs on demand, and a brief can be regenerated with a custom prompt. Ad-performance figures (`src/performance.ts`) are attributed to Viktor's analysis, because paid media is not an approved KB source. Not yet a decision: choosing v1 or v2 is open. The table below describes v1.

| In the mockup | Not in the mockup yet |
|---|---|
| **Calls & briefs:** signed-in person from the sidebar account menu; My calls / All calls; Today / Tomorrow / This week; rows with type (and *proposed*), host, state (Ready · Stale · Scheduled · Needs type · Cancelled), open-ask and overdue-promise signals, *prepped* flag; client's local time on hover; "2 events not matched" link (minimal, C4) | Real calendar sync |
| **Morning prep** panel (C4) with optional Slack DM toggle | Real Slack delivery |
| **Brief (C1):** *In 30 seconds*; sections from the call-type template; *More detail* per section; owed lists from the live Action Register; cited lines; one opportunity with "why it's top"; type-specific block; sources & limits; Health category chip | — |
| **States:** Stale with *Rebuild now*; Scheduled with *Build now*; Needs type with type picker and *Confirm type & build*; Cancelled as not applicable | — |
| **Regenerate with instructions (C7):** what-else-to-look-at text, quick focus, tone & length, section toggles, *this call only* / *suggest for template*; refusal of website and (for non-admins) finance requests with the reason; new version with its instructions shown; version picker; **automatic rebuild keeps the instructions** (demo button "Simulate a new client message") | Saving personal defaults (C7 open) |
| Copy / Download / Print / Mark prep done / **Send agenda to client** (C4; drafted from the agenda only, a person sends) | Gmail draft creation |
| **After the call (C3):** recent calls; decisions; commitments (in register, or *Add (proposal)* → Needs review); asks answered; brief vs reality; follow-up email draft (copy, I've sent it); team recap on Slack; no-transcript case with manual notes | Real Fathom webhook |
| **Call-type templates (C2):** 8 templates with detection rule, purpose, sections, agenda skeleton, leave-out; edit for admins; *Suggested changes* inbox fed by regenerations | Real template editing |
