# Wedding Industry Ads — Automation Scope

**Engagement:** E2M Solutions × Wedding Industry Ads, LLC (dba LeadLock / LeadLock Pro)
**Phase:** Audit & Blueprint, week 2 of 3
**Document date:** 3 September 2026
**Author:** Jainil Trivedi, AI Engineer (E2M)
**Next milestone:** Blueprint Review — Thu 10 Sept (tentative; Whitney flagged a Wednesday conflict and offered Friday 11 Sept)

---

## How to read this document

This is the consolidated scope of every automation candidate identified across three client calls (11 Aug sales/discovery, 26 Aug Weekly Sync 1, 2 Sept Weekly Sync 2) and the client-filled *AI & Automation Opportunity Task Audit* spreadsheet.

Every coverage claim in Part 2 was verified quote-by-quote against the full transcripts. Where a claim could not be supported verbatim it is marked as such. Where E2M's own design inference has been mistaken for client-confirmed fact, that is flagged explicitly — because presenting inference as confirmation on the blueprint call is the fastest way to lose the room.

**Part 3 is the important part.** Twelve spreadsheet rows plus eight unaudited workstreams look like twenty projects. They are not. They collapse onto about six builds sharing one spine, and understanding that collapse is what makes the engagement deliverable at all.

---

## Executive summary

**The audit sheet audits one seat.** All 12 client-filled rows are assigned to Gisselle Jimenez, and all 12 sit in a single department category ("Operations / Admin / Internal") out of thirteen available. Seven people do the work at Wedding Industry Ads. The sheet covers one of them — and she is an outside-agency contractor on a ~25 hr/week cap.

**Most of what was actually discussed has no row in the sheet.** On the 2 Sept call, roughly 17 minutes covered the entire spreadsheet while roughly 21 minutes covered work with no spreadsheet row at all. Nine of the twelve unused department categories are actively evidenced in the transcripts.

**Nothing is fully scoped.** After adversarial verification of all 12 rows: 8 substantially discussed, 4 named only, 0 build-ready without follow-up questions.

**The hours case does not close.** The sheet derives to 18.1 hours/month, of which only 6.0 is client-attested. Against the $9,499 Apollo price that is $175 per recovered hour at a theoretical 100% automation with zero review time. The arguments that do survive scrutiny are onboarding throughput, turnover-proofing single points of failure, and founder capacity returned to selling.

**The largest single opportunity is invisible in the deliverable.** Tina's monthly client reporting — "the first few business days of the month", "not automated in any way right now" — derives to 18–24 hrs/month, i.e. 100–133% of everything the entire twelve-row audit quantifies. It has no row, and no quantifying follow-up was ever asked.

**The thing being bought is not time savings.** Per 11 Aug, the driver is turnover-proofing: extracting institutional knowledge out of individuals' heads into a system the company owns, so the next hire "is just a person who is kind of like running it. We have the agency brain." The trigger event was their account manager resigning, which pushed Whitney back into delivery and blocked her selling time.

---

# PART 1 — The source material

## 1.1 The audit spreadsheet, as filed

Single sheet (`Sheet2`), extracted programmatically.

| Property | Finding |
|---|---|
| Client-entered rows | **12** (rows 4–15) |
| Hidden rows | Rows 2–3 are E2M's own example rows ("Sara", "James"), tagged in M2: *"These are just an example tasks"* |
| Assignee on every row | **Gisselle** |
| Department on every row | **Operations / Admin / Internal** (1 of 13 available) |
| Template capacity | ~48 task rows (validation extends to row 51) — 12 filled |
| Column F, "Total Time spent per Month (hrs)" | Filled on **2 of 12 rows**. The sheet yields no total |
| Orphan artifact | Cell comment on **E29**, an otherwise empty row: *"Only done once every 6 months-ish"* — something was started and deleted. Worth asking Gisselle what row 29 was going to be |

**Unused department options** (each one a body of work the sheet does not see): Account Management / Client Services, Sales & Lead Generation, Content & Copywriting, SEO, Paid Media / PPC, Design, Social Media, Reporting & Analytics, Project Management, Web, SEO/GEO, Internal marketing.

## 1.2 Coverage after adversarial verification

Every cited quote was located verbatim in the transcript files. Across 182 evidence items, **zero fabrications** were found. Three classifications moved under challenge.

| Task | Sheet priority | Final coverage | Value | Effort | Derivable hrs/mo |
|---|---|---|---|---|---|
| **04** Filing emails + drafting replies | HIGH | Substantially discussed | HIGH | L | unquantified |
| **05** ClickUp overdue → Slack recap | LOW | Named only | LOW | S | 2.0 |
| **06** Team meeting recap + action items | MED | Named only | MED | M | 4.0 |
| **07** Post-client-call template emails | MED | Substantially discussed | HIGH | L | unquantified |
| **08** Onboarding ClickUp checklists | MED | Substantially discussed | HIGH | **XL** | unquantified (2.0/instance) |
| **09** Client assets → client Drive | LOW | Substantially discussed | HIGH | M | unquantified |
| **10** Chasing team on action items | HIGH | Pain articulated, process never walked | HIGH | XL | unquantified |
| **11** 1-hour reminder posts | MED | Substantially discussed | MED | M | 3.0 |
| **12** Session upload + recap post | MED | **Named only** | HIGH | L | **6.0 — largest in sheet** |
| **13** Roll call | HIGH | Substantially discussed | HIGH | M | 2.0 |
| **14** Client meetings → client folder | MED | Ownership established, mechanics never asked | HIGH | M | unquantified |
| **15** Overdue invoices + invalid emails | MED | Substantially discussed — most complete process model in the sheet | MED | S | ~1.1 |

**Verification movements:**
- **TASK-10 upgraded** from named-only. Whitney's "chasing the team" passage on 26 Aug is genuinely *about* this row, plus the 24–48 business-hour SLA, the dedicated monitor-star, and ClickUp tasks created purely to verify the 2-week DMs went out. But the completeness critic's counter stands: you cannot call a task explored while its own first unknown is *"how is it tracked today, exactly?"* **The correct statement is: the pain is fully articulated, the process was never walked.**
- **TASK-14 downgraded.** Ownership and the downstream chain were established at 6:18–7:22, but not one mechanic was ever asked — how the file leaves Zoom, folder taxonomy, naming convention, or whether it is recording-only versus recording+transcript+summary as the sheet states. Do not tell Whitney it was never discussed; she will correct you. **The correct statement is: routing established, mechanics unexplored.**
- **TASK-15 downgraded** from fully scoped. Four genuine open items survive: volume was asked at 10:42 and never answered; the saved invalid-email filter definition is unknown by the client's own admission; the re-enrolment leg is unexplored; and the notification destination was never settled. All four are small and closable. It remains the most complete process model in the sheet.

**On TASK-12, one correction to an earlier reading.** The only reference in 92 minutes of transcript is a broken-off clause at 17:02: *"And then there's just like the recap posts, which I'm not sure if I."* That is first person about her own posting activity — **it is Gisselle trailing off inside her own walkthrough, not Minu raising a new row.** The client started to raise the largest quantified item in her own sheet and the vendor did not pick it up. State it that way; it is both more honest and it lands better.

## 1.3 Team roster and single points of failure

Whitney, 2 Sept @25:50: *"it's not like there are multiple team members that do the same things, right? It is just like one person with set responsibilities."*

| Person | Owns | Audited? |
|---|---|---|
| **Whitney Hodges** | All sales calls and ALL client calls (ads kickoff, messaging & positioning, ad strategy presentation, monthly 1:1s); reviews everything before it goes out | No rows, no hours |
| **Gisselle Jimenez** | Ops/EA via outside agency ("Dot"), ~25 hrs/wk cap, ~1yr tenure; Whitney's proxy | All 12 rows |
| **Carmen** | Google Ads manager; Google Ads office hours; keyword research, campaign builds, Loom walkthroughs | No |
| **Jacqueline** | Meta Ads; Meta Ads office hours; campaign launches | No |
| **Ivy** | Ads creative design | No |
| **Tina** | LeadLock/GHL design — landing pages, email + SMS nurture copy — **and monthly client reporting** | No |
| **Danielle** | LeadLock/GHL implementation — kickoff calls, workflow build/test, DNS records, A2P/10DLC registration | No |

**Unresolved:** whether "Danielle" (implementation specialist) and co-founder "Daniela Justus" are the same person. It matters for who owns the LeadLock track.

**The exposure this creates:** the four genuine single points of institutional-knowledge failure Whitney named herself are Carmen, Jacqueline, Tina and Danielle. None has been interviewed. An engagement sold on turnover-proofing has so far audited only the seat that is an outside contractor. That is the single most damaging question available to Whitney on the blueprint call, and it should be pre-empted rather than discovered.

## 1.4 The tool stack, as established

| System | Role | API status |
|---|---|---|
| **GoHighLevel** (Agency SaaS, ~$500/mo) | Everything client-facing: member portal (Communities), invoices, contacts, pipelines, LeadLock sub-accounts. Both WIA and LeadLock Pro | Agency Admin granted. **"Most likely we would have an API" (2 Sept @13:21) — never verified.** Private Integration Tokens, `services.leadconnectorhq.com`, `Version: 2021-07-28` |
| **Gmail** (`hello@weddingindustryads.com`) | The entire client-comms hub. 8-symbol star taxonomy, per-client labels, "waiting" tag | **Not requested.** Delegation ≠ API access |
| **Dubsado** | Proposals, contracts, invoices, onboarding questionnaire. Mid-migration to GHL (done for one offer) | Sample alert emails only. No API needed — see 3.4 |
| **Slack** | Where operations actually happen. 100% team adoption | Workspace + client channels granted |
| **ClickUp** | Task record only. *"the team has never, like, fully adopted ClickUp other than to just, like, check off the tasks"* | Member seat granted (not Guest — Guests can't open templates) |
| **Zoom** | Whitney's recordings and transcripts. She runs every client call | **Not requested.** Highest-value corpus in the company |
| **Fathom** | Four **individual free accounts** (Gisselle, Jacqueline, Carmen, Danielle). Whitney does not use it | Sample exports only |
| **Google Drive** | Client folders, call recordings, email templates | One client folder requested. Personal-Drive vs Shared-Drive unresolved |
| **ChatGPT** | Per-client Projects, **shared `hello@` login, no Team/org account** | Project export requested — likely not technically shareable, see 7.3 |
| **Canva** | Session recap banners | Not requested |

---

# PART 2 — The complete automation inventory

Twenty automations. Twelve from the sheet (A-series), eight discussed but unaudited (B-series).

## A-SERIES — From the audit sheet

### A1 · Email filing and reply drafting — TASK-04

**Sheet:** HIGH priority, "Everyday", time "depending on the day. Mondays takes longer because of emails that come through in the weekends". Tools: Gmail. Hours: unquantified.
**Coverage:** Substantially discussed — the deepest segment in either call. 26 Aug @23:45–@40:19, ~16.5 continuous minutes with a live inbox screen-share and genuine follow-up probes.

**Current process.** Whitney stars incoming mail; the star is an instruction to Gisselle, not metadata. Roughly seven or eight distinct states: gold = Whitney flagged it; red = action item for Gisselle (draft, or file an incoming recording); a third symbol = Gisselle has drafted, Whitney to review and send; a fourth = Whitney must act personally (e.g. pay an invoice); a fifth = important, no action, keep starred; a sixth = a team member owes the client a reply, monitor it; a seventh = something Whitney needs to dig into. Plus per-client labels created at contract signature and applied retroactively to that contact's lead-stage mail, a tools/newsletters/partners label tree, an existing Gmail filter layer Gisselle only half-remembers (*"I have some automations where they are tagged automatically"*), and archive-only-after-Whitney-has-read logic. A "waiting" tag holds threads pending a client reply, swept manually every Monday before the Whitney 1:1.

**Volume:** ~5 drafted daily ("5 regularly", 5–10 max). SLA 24–48 business hours, protected only by `hello@` being CC'd and Gisselle watching.

**Real scope — this is three products, not one.**
1. **Classify-and-file.** Deterministic-ish, mechanical, zero client exposure. Gmail `users.watch` + Pub/Sub → `messages.get` → resolve sender to a GHL contact for client-vs-lead and pipeline stage → LLM classifier over a closed intent set → `messages.modify` applies the mapped star and label. Archive only where intent is newsletter/FYI **and** already read, mirroring today's rule. Ship behind a 2-week shadow mode: write proposed labels to a Sheet log, Gisselle scores daily, promote to live writes at agreed precision. Mis-filing is recoverable and never touches a client — the only component that could eventually run unattended.
2. **Context-and-draft.** The flagship, and Whitney explicitly ruled out scoping it to Gmail: *"whatever is scanning the inbox needs to also be seeing what's happening in Slack... where the call recordings and all the client things are living, inside of our Google Drive."* Her highest-value cases are not replies at all but proactive drafts — after a sales call the agent should already know *"this person wants Elevate, we need to send them the Elevate proposal"* and have it queued.
3. **The waiting/SLA tracker.** Two clocks nobody measures: a client-side clock (the waiting tag) and an internal clock (team member owes a reply against the 24–48hr SLA). Neither exists as data anywhere — it lives in Gisselle's Monday eyeballs.

**What the calls REMOVED from scope:** no migration to GHL. Whitney named two hard blockers — she cannot see drafts made from her account, and formatting breaks between compose and send — and settled on Gmail as the working surface. Build against the Gmail API; let GHL stay the pipeline record.

**The knowledge-extraction core.** Gisselle: *"every time an email comes in, if it's a client, I'm aware of everything that's happening with that client, even with like in the slack communications."* That head-knowledge is the entire 11 Aug thesis. She is an outside contractor at 25 hrs/week whose process is documented nowhere but the sheet she wrote.

**Process-change licence, on the record.** Whitney: *"I am not tied to the labeling system at all, honestly. For me, the biggest thing is that in a timely fashion, emails are proactively drafted and they cover the bulk of, like, what I want them to say."* And her acceptance bar: *"it's not things where I'm doing double work and then having to heavily edit or completely rewrite stuff... Or if I am, that there's some sort of process in place where it's learning from my output of what I'm sending out."*

**Blockers:** Gmail API scope on `hello@` was never requested. `ai@` is a different mailbox with none of the history. Also unrequested and each blocking a leg: an export of the existing Gmail filters (Settings → Filters → Export to XML), and an attributed sent-mail corpus for the voice profile.
**Value / Effort:** HIGH / L. **Status: BLOCKED on access.**

---

### A2 · ClickUp overdue sweep → Slack recap — TASK-05

**Sheet:** LOW priority. 0.5 hrs × 4 Mondays = **2.0 hrs/mo**. Tools: ClickUp + Slack. *"Could send to Gisselle for review first"*.
**Coverage:** Named only. It is one beat in a sequential row-order read of the sheet at 2 Sept @1:58, and that beat is spent entirely on the white-label email access question. Not one question was asked about the review itself: no overdue definition, no filter, no tagging convention, no review gate. Rows 6, 7, 8 and 13 each got a screen-share or a Q&A round; row 5 got neither.

**Design:** ClickUp v2 `GET /list/{id}/task?subtasks=true&due_date_lt={now}&include_closed=false` → group by assignee → one Slack message per owner or one digest with @-mentions → optional Gisselle pre-review gate.

**The confession that reshapes this row.** 2 Sept @42:16: *"the team has never, like, fully adopted ClickUp other than to just, like, check off the tasks."* An overdue-task digest is close to meaningless if nobody works in ClickUp — the real overdue list is almost certainly full of stale, never-updated tasks, and the first genuine digest would surface dozens of items nobody intends to do. That is an adoption problem wearing an automation costume.

**Value / Effort:** LOW / S. **Status: DEFERRED — needs a data-quality assessment first, not a build.**

---

### A3 · Team meeting recap and action items — TASK-06

**Sheet:** MED priority. 1 hr × 4 Mondays = **4.0 hrs/mo (max)**. Tools: Fathom + ClickUp + Slack. Column J carries the client's own gate: *"Y (Gisselle to review before sending to Slack)"*.
**Coverage:** Named only — and E2M asserted otherwise on the call. 2 Sept @3:00: *"For team meeting, recap, and action items also we've spoken about now."* That is false; 26 Aug covered the roll-call sheet and the Gmail system and never touched the Monday meeting. The single follow-up (@3:07) was an access question about Fathom seats.

**Never asked across 92 minutes:** who attends, whether it is recorded at all, whose notetaker captures it, whether there is a standing agenda, how long it runs, or what one of Gisselle's real action-item lists looks like.

**Two unresolved identity problems.**
1. The sheet names Fathom as this task's tool, but **Whitney does not use Fathom** — so it was never established that an ingestible transcript of the Monday meeting exists at all.
2. 26 Aug @27:00 reveals a separate weekly Whitney–Gisselle Monday sync. Nobody established whether TASK-06's "team meeting" is that or a different all-hands.

**Design:** transcript → extractor → action items with owners (assignment is a deterministic lookup given one-person-per-function) → ClickUp task creation with due dates → Slack digest → Gisselle review gate. **No client-facing output**, which makes this the safe place to pilot the whole engine.

**Correction to flag:** the inference that "action-item owner assignment can be a lookup table" derives from 2 Sept @25:50, which describes who gets assigned **onboarding** work by function — not who gets assigned meeting action items. The call does not test it.

**Value / Effort:** MED / M. **Status: NEEDS DISCOVERY. Present as "input layer discussed, extraction process not yet walked through" — and do not repeat the claim that it was already covered.**

---

### A4 · Post-client-call recap emails from templates — TASK-07

**Sheet:** MED priority. Time "depending on the email", frequency "depending on # of calls". Tools: Drive templates + Gmail + Zoom. Client gate: *"Y (Gisselle/Whitney to review before sending)"*.
**Coverage:** Substantially discussed. Whitney narrated the whole chain unprompted, 2 Sept @6:54, and Minu confirmed the guardrail.

**The defining quote — one sentence, five outputs:**
> *"And so then after those calls, Gisselle is then uploading the recordings to the client folder, checking the meetings for action items, four action items, then assigning them to team members in ClickUp, letting them know in Slack, drafting a recap email for the client, and including action items there, and attaching the recording. So all, a lot of things that I'm sure could be more automated with AI that she's spending a lot of time manually doing at this point."*

And the constraint, restated on the spot: *"we'll review any drafts before they go out."*

**Template selection is call-type-dependent** — the sheet says *"depending on the call (general strategy call or onboarding meeting) use the appropriate email template"*. Known call types: ads kickoff, messaging & positioning interview, ad strategy presentation, monthly 1:1, LeadLock kickoff, sales call.

**Still open:** the Drive templates have never been seen. Volume was never quantified.
**Value / Effort:** HIGH / L standalone — but see Part 3; it is not standalone.
**Status: CORE BUILD. Highest consensus of anything in the engagement.**

---

### A5 · Onboarding ClickUp checklist creation — TASK-08

**Sheet:** MED priority, "2 hours, depending", frequency "depending on clients onboarding". Tools: ClickUp.
**Coverage:** Substantially discussed — 2 Sept @19:10–@40:36 is the longest continuous passage in either call.

**Critical scope finding: the sheet row and the discussed reality are two different things.** The row describes Gisselle's ~2-hour ClickUp setup slice. The call described a multi-week, multi-owner lifecycle. If the blueprint prices the row and delivers the lifecycle, or vice versa, that is the misunderstanding that kills the project mid-build.

**The lifecycle as narrated:**

*Trigger.* Dubsado public proposal accepted → generates agreement to sign + first invoice → signed and paid → **alert emails land in the Gmail inbox**. Whitney: *"at this point, like, the trigger is that, like, we see in the inbox that they have signed the contract and paid the invoice."*

*Gisselle's manual block.* Create the ClickUp onboarding list — template varies by offer, and both-services clients need two overlapping templates merged; set every due date by hand; assign; email the client with countersigned contract + kickoff booking link + onboarding questionnaire; create the Google Drive client folder and upload sales-call recording, contract, questionnaire; create a client-specific Slack channel; post a team announcement in Slack with key links; create the LeadLock sub-account.

*Whitney's three calls.* (1) Ads kickoff — expectations, education, and **live screen-share where she takes remote control to get ad-account access**, because *"overwhelmingly so many of our clients are tech challenged that it's really hard to give them instructions and have them do it on their own."* They have tried other ways for years; this is settled. (2) Messaging & positioning interview → transcript into the client's ChatGPT Project. (3) Ad strategy presentation — *"we say customized, but in all honesty, it's pretty similar for each client"* — Carmen attends with keyword research and gets the plan approved live.

*Two parallel execution tracks.* **Ads:** Carmen builds Google Search + records a Loom → emailed for approval. Jacqueline: client-attraction ads → review → approve → launch; then conversion campaigns; then retargeting — each its own gate, with *"lots of edits back and forth, potentially, depending upon how particular the client is."* **LeadLock (Danielle):** kickoff call scoping automations (standardised — inquiry, tour/pre-consultation, post-tour/post-consultation) → create client as user, connect email + calendar, purchase phone number, obtain DNS access → DNS records created → A2P registration on their behalf. Meanwhile **Tina** builds and designs landing pages including the privacy-policy page A2P requires, writes email and SMS nurture copy, designs templates and forms → emailed for review → edits → internal testing → client testing → official LeadLock onboarding call → form goes live on their site → **then** the LeadLock landing page feeds back into the ad strategy, and Carmen and Jacqueline swap the campaign URLs.

*Definition of done.* All campaigns launched → shift to monthly maintenance. **This is the best KPI available in the whole engagement: time-to-fully-onboarded has a defined start, a defined end, and is measurable before and after.**

**Why "we're always chasing the team" is now explained:** dependencies are cross-track (LeadLock live before ads URLs change), there are roughly eight client-approval gates, and nobody can see the whole board because ClickUp isn't adopted.

**Two admissions that make templating viable:** the ad strategy is *"pretty similar for each client"*, and the LeadLock automations are *"pretty consistent, client to client."*

**One founder-hearsay caution.** 2 Sept @21:34: *"I don't know if you're manually going in and assigning things every time, but she's definitely manually going in and having to set due dates."* That is Whitney inferring about Gisselle's process, not Gisselle confirming it. Likely right, uncontradicted, but verify against the ClickUp instance before building on it.

**Missing multiplier:** Whitney volunteered *"we're onboarding a lot of clients"* and nobody asked the number. One question converts this row from 0 hrs to a real figure at 2.0 hrs each — **and it simultaneously supplies the missing frequencies for A4 and A11.** Three of the six unquantifiable rows share this one multiplier.

**Value / Effort:** HIGH / XL. **Status: PARTIALLY IN SCOPE — the trigger-to-scaffold slice ships; full orchestration is named and costed for execution.**

---

### A6 · Client assets → client Drive folder — TASK-09

**Sheet:** LOW priority, "varies". Tools: Gmail + Drive. Description: *"Upload forms filled out by the customer and upload them to client's drive (questionnaires, surveys, etc)"*.
**Coverage:** Substantially discussed, inside the onboarding walkthrough at 2 Sept @29:46.

**This row is three separate builds with different triggers and radically different viability.**
1. **The Dubsado questionnaire leg.** *"we will download it from Dipsado and Gisselle will save it in the client's Google Drive folder. She'll also share it in the Slack channel for the team to be able to review it."*
2. **The Drive filing leg.** Mechanical; overlaps A11 entirely.
3. **The ChatGPT Project leg.** *"a new part of the onboarding process that we've added on that I'm not even sure if is documented here is that Gisselle is starting to create a custom GPT for each client"* — corrected moments later to a Project, not a custom GPT, with per-client knowledge bases seeded with the questionnaire and the messaging-and-positioning transcript. **Whitney has already disowned this leg:** *"almost like a band-aid solution for right now"*, *"we don't see it as a long-term solution."*

Bundling means the row inherits the viability of its weakest and most probably-doomed leg.
**Value / Effort:** HIGH / M. **Status: SPLIT. Legs 1 and 2 fold into the pipeline; leg 3 becomes the client-brief substrate (see 4.5).**

---

### A7 · Chasing team members on action items — TASK-10

**Sheet:** HIGH priority, "every day", "varies". Tools: **Slack** (the only tool listed). Description: *"Keep track of team members communications in slack and email and follow up if no acknowledgement so things don't slip through"*.
**Coverage:** Pain fully articulated; process never walked. This is the largest gap between stated priority and discussion depth in the sheet.

**The founder's own articulation, 26 Aug @16:54:**
> *"It always feels like we're like chasing the team to get done the things that need to get done... create action items based on that, and then chase those action items and make sure that they actually get done, and then get back to the client on saying, hey, this is done sort of thing."*

That last clause is a **fifth step the sheet omits** — closing the loop back to the client.

And the architectural requirement, which contradicts the sheet's own tool field: *"whatever is scanning the inbox needs to also be seeing what's happening in Slack in terms of where the team is communicating."*

**Two live tracking artefacts exist today.** The dedicated Gmail star meaning *"this needs a reply from a team member and we're just gonna like monitor"*, and ClickUp tasks created purely *"for us to follow up and monitor that they actually send the DM"* (26 Aug @14:47).

**Never established:** how acknowledgement is tracked today, what counts as "no acknowledgement", escalation rules, channel list, or volumes. The Slack half — the sheet's only listed tool — was never explored at all. The one head-on approach, 2 Sept @19:10, is abandoned inside a single sentence and never returns.

**Value / Effort:** HIGH / XL. **Status: BIGGEST OPEN QUESTION IN THE SHEET. Present it as such, not as understood — presenting it as understood invites Gisselle to correct it live.**

---

### A8 · Member-portal event reminder posts — TASK-11

**Sheet:** MED priority. "15 min total" × 12/mo = **3.0 hrs/mo**. Tools: Highlevel. Client comment: *"Small task but it has happen that I forget to post on time"*.
**Coverage:** Substantially discussed with a screen-share, 2 Sept @14:02–@18:27.

**Four recurring events, not two.** Google Ads office hours (Thu 11am CST, Carmen) → posted in the Google Search Accelerator channel. Meta Ads office hours (Thu afternoon, Jacqueline) → Meta Ads Accelerator channel. **Q&A, every other week** → Announcements. **Workshop, every other week** → Announcements. Zoom links are static per event; Gisselle rewrites the copy weekly for variety.

**Her own triage is the right one:** office hours and Q&A are formulaic — *"I feel like this one is the one that can be mostly automated"* — while the **workshop needs review** because Whitney sets a theme and title each time.

**The native-feature fork, unresolved.** She scheduled one successfully via GHL's social planner in April: *"I was able to schedule it and publish it"*, then hedged: *"I don't remember... I know that JHL, like, usually keeps updating these things. I haven't tried it. This was, like, in April. Like, we technically can schedule them. I just remember there were some limitations, like, tagging people or, like, tagging the event."*

Minu's instinct here was correct and should be preserved: *"We don't need to over-engineer it."* Test native scheduling in the portal before proposing to build anything. **Do not present this as either "just configuration" or "needs a build" — both can be falsified in fifteen minutes once portal access lands.**

**Value / Effort:** MED / M. **Status: 15-MINUTE SPIKE, with a stated fork.**

---

### A9 · Session upload and recap post — TASK-12

**Sheet:** MED priority. ~0.5 hrs × 12/mo = **6.0 hrs/mo — the largest quantifiable item in the entire sheet.** Tools: Highlevel + **Canva**. Description: *"Download recording from team members + recap summaries. Create canva banner with the session's date. Upload to member's portal. Create post with recap recording and summary in member's portal."*
**Coverage:** **Named only.** Total coverage across 92 minutes: one broken-off clause at 17:02.

Both transcripts were grepped for recap / upload / Canva / banner / portal / vault / session and every hit read. Not one of the four sheet steps is ever touched: no recording acquisition, no banner, no portal upload mechanics, no post format, no review gate, no volume or timing.

**The conflation trap, correctly avoided.** The strongest false positive is 2 Sept @6:18–@7:58, where Whitney describes *"uploading the recordings to the client folder... drafting a recap email for the client."* Superficially that is "uploading" plus "recap" — but the destination is the Drive client folder and the artifact is an email to one client. Different destination, different artifact, different audience from a member-facing post in the GHL community. That is A4/A11, not this row.

**Caution for the blueprint.** Any design detail for this row — Canva Connect API, Brand Template requirements, a paid Canva plan, Zoom Cloud Recording as the source, GHL media-library video limits — is E2M inference with **zero support in either call**. Since this row has no discovery at all, presenting any of it as client-confirmed will read as scoping that never happened.

**Value / Effort:** HIGH (by hours) / L. **Status: NEEDS DISCOVERY. Cannot go on an execution shortlist. Say so plainly, and say the client raised it herself.**

---

### A10 · Roll-call attendance tracking — TASK-13

**Sheet:** HIGH priority. "10 min total" × 12/mo = **2.0 hrs/mo**. Tools: Highlevel + Google Sheets. Client comment: *"It's in my task list to automate this somehow but it's complex"*. Description ends with the crucial constraint: *"(Just needs to flag, we will manually follow up)"*.
**Coverage:** Substantially discussed — 26 Aug in depth with a screen-share, plus 2 Sept follow-ups.

**Current process.** Carmen and Jacqueline hand-mark attendance in a Google Sheet (two separate sheets, Google and Meta). Gisselle then duplicates the week's column, retypes the date, tracks consecutive misses, flags at 2 weeks (portal DM by the owning team member) and 4 weeks (email), and creates ClickUp tasks to verify the DM went out.

**Her prior automation attempt failed twice** — a Zapier/Sheets email-reminder approach (*"it got very, very complicated... I think I got confused on how to do, like, the rows"*) and a ClickUp recurring-task approach (*"when we completed a task, then it needed to create a new one"*). This is the one task the client personally tried and failed to automate, which makes it high-credibility if solved and high-embarrassment if faked.

**Correct fix: delete the human data-entry step, don't automate around it.** Attendance already exists — the meetings are Zoom with a Fathom notetaker present (2 Sept @5:24: *"They use Fathom. They use a Fathom note taker."*). Pipeline: attendee list → identity-match against the GHL membership roster → compute consecutive misses → write the flag → create the ClickUp task / queue the draft email.

**The load-bearing unknown, and it is binary.** Do Fathom exports carry **structured attendee names**, or only prose? This single question decides whether the row is buildable, and it is precisely why the two office-hours transcripts were requested. If the answer is no, the fallback is **Zoom participant reports**, not transcripts — and that requires access nobody has asked for.

**Other real risks:** identity matching (Zoom join-name vs GHL contact email will not line up cleanly), and drop-in semantics — members *"can join like at any moment during that hour"*, so partial attendance needs a threshold rule that was never defined.

**Value / Effort:** HIGH / M. **Status: READY PENDING ONE BINARY TEST. Do not fake the capture leg.**

---

### A11 · Client meeting recordings → client folder — TASK-14

**Sheet:** MED priority, "15 min", frequency "varies". Tools: Zoom. Description: *"Downloading and uploading client assets like recording, transcript and summary to client's drive"*.
**Coverage:** Routing established, mechanics unexplored.

**What was established (2 Sept @6:18–@6:54).** Mostly Gisselle. Danielle uploads the LeadLock kickoff call *"because she's there alone"* — *"and I think that's really the only meeting that she's alone."* Critically: *"Since our last account manager that left, we've shifted things... I'm pretty much doing all of the client onboarding calls now. I'm doing all of the client strategy calls now. So it's like, it's my Zoom, my note taker, my recordings, all of that."*

**One over-read to correct.** *"that's really the only meeting that she's alone"* refers to Danielle only. It cannot support a claim that Whitney's Zoom is the sole source — Carmen and Jacqueline each run a weekly client-attended Zoom solo and capture it on their own Fathom notetakers. Any percentage attached to "Whitney's share of call volume" is invented; volume was never quantified.

**Never asked:** how the file leaves Zoom (cloud vs local, manual download vs API), where inside the client folder it lands, naming convention, whether it is recording-only or recording+transcript+summary as the sheet says, or how many per week. Nobody has seen the Drive.

**Value / Effort:** HIGH / M. **Status: FOLDS INTO THE PIPELINE. Needs a Drive walkthrough before anyone specs the filing taxonomy.**

---

### A12 · Overdue invoices and invalid emails — TASK-15

**Sheet:** MED priority. "3 min", "every day" ≈ **1.1 hrs/mo** at 22 working days. Tools: Highlevel. Client comment: *"Easy task but I tend to forget"*. Description: *"Just flag to Gisselle/Whitney"*.
**Coverage:** Substantially discussed with a live screen-share, 2 Sept @8:13–@13:56. The most complete process model in the sheet.

**Two daily checks, both failing on memory rather than effort.**
*Overdue invoices.* GHL → Invoices → filter overdue. GHL's automated dunning exists but *"sometimes that'll end up in people's, like, spam folders or promotions. So if and when we see it's overdue, then we're sending a personal email to them from my email that includes the link to the invoice"* — from `hello@`, not automated — *"and usually that's the push that people need to actually get it paid."* The invoice link was demonstrated on screen: *"So just here, copy link."* **Asymmetry:** invoices in the WIA account only; LeadLock Pro takes no payments (*"we don't take payments here"*), so querying invoices there would be visibly wrong.
*Invalid emails.* A pre-existing saved GHL contacts filter catching typo'd opt-in addresses. *"sometimes it's, like, common misspellings, like, oh, they wrote, like, .com instead of .com, so I'm able to just notice that, put a valid email, and then resend them the materials."* Checked in **both** accounts.

Gisselle pre-specified the deliverable herself: *"this quick notification would be, would be really helpful."* And twice admitted the failure mode: *"I really want to check this every day, and sometimes it's just very simple, but because of other things I forget."*

**Four genuine open items.** (1) Volume was asked at @10:42 and never answered — the reply was a process re-description, and the only quantification anyone got was *"it's not happening usually."* (2) The filter definition is unknown by the client's own admission (*"I already have a filter for it, so I think it's just, like, contacts, and then invalid emails"*) — what GHL counts as invalid (hard bounce vs syntax vs DNS) was never established. (3) The remediation's second half is unexplored: *"putting them in the workflow again, so they get our emails"* — which workflow, how triggered, does it double-send, and what happens when the intended address cannot be inferred. (4) The notification destination was never settled — Slack vs email vs in-GHL.

**One correction on feasibility.** @13:01–@13:21 does **not** establish API availability. Minu said *"I'm just wondering if we have the API available. Would you know that? Or we can research that"* and concluded *"most likely we would have an API."* Only the plan tier was confirmed. That single unverified word carries this whole row.

**Do not defend this row on hours** — she signalled twice that she does not actually complete it daily, so the true baseline may be nearer 0.4 hrs. Defend it on **reliability**: an unpaid invoice is revenue, and a lead who never received the opt-in material they asked for is revenue.

**Value / Effort:** MED / S. **Status: MOST BUILD-READY ROW, but double-gated on credentials landing and on the GHL API assumption holding.**

---

## B-SERIES — Discussed at length, no row in the sheet

### B1 · Monthly client reporting → executive summary

**Owner:** Tina. **Never in the sheet.**

> *"we have Tina on the team, basically, like, dedicating the first few business days of the month to pulling these reports together for clients. It's not automated in any way right now. She's like pulling in screenshots from the different ad accounts, pulling in screenshots of best performing ads. We're adding in additional context about like the why behind it all. And then also like recording a video walkthrough to kind of like explain it to the client."*

**Derived at 18–24 hrs/month** (3 days × 6–8 productive hrs). That is **100–133% of everything the entire twelve-row audit quantifies.** It is the only duration estimate given for any non-Gisselle work anywhere in either call, it was volunteered unprompted, and **not one quantifying follow-up was asked.** The 18–24 range is inference from "a few business days" and must be confirmed, not asserted.

**Whitney has already specified the solution and named her reference implementation.** *"I've been playing around with Victor and our Slack... it's been really cool to see how he can connect to lead block accounts, Google ads accounts, meta ads accounts, and just have an overarching like view of everything. So I would love something like that that can create more of just like an executive summary on a monthly basis. I think I saw that in your AI library, actually... something clearer for clients to understand as opposed to like so many screenshots of the metrics."*

**The framing that prices better than hours.** Tina is **simultaneously** the sole LeadLock/GHL designer building every landing page and writing every email and SMS nurture sequence for every in-flight onboarding. The reporting block consumes the first business days of every month, and there is no redundancy. So **every client who signs in the first week of a month waits on their build behind a screenshot deck.** That is revenue timing on new business, not admin cost.

**Scope discipline: do not replicate the deck.** Designing their layout blind against a sample nobody has seen means Tina spots the mismatch in ten seconds. The deliverable Whitney asked for is the thing she wants *instead* of the deck, and that half has a verbal spec already in hand. **The human touch stays surgically intact: automate the PREP, keep Tina on camera.**

**Access needed for production:** Google Ads developer token + MCC linkage per client; Meta System User token with `ads_read` per ad account via Business Manager; GHL for LeadLock metrics. Lead time on the Google token is days-to-weeks — **start the application now.**

---

### B2 · Content and marketing repurposing

**Owner:** Whitney. **Never in the sheet. The only item she tied to revenue.**

> *"we need more leads. We need more sales. We need to be bringing more clients in. And if we're not marketing actively, that's not going to happen."*

**Current chain — five manual hops with a founder decision at every one.** She recalls a strong client moment from a strategy call → flags it to Gisselle → Gisselle puts the transcript into ChatGPT → *"see if it can come up with, like, a script for a reel that I can record"* → Whitney refines → records → then commissions the carousel separately → then the email marketing separately. Every hop stalls whenever she is on a client call, which since the account manager resigned is all day.

**The mechanism she asked for, in her words:** *"even if I'm just, like, giving it a voice note of, like, hey, I want to reference this call. Here's more context. Here's more history. This is the direction that I want to take it. And then be able to, like, multi-purpose that into a lot of content."*

**It is also the harvest step on an asset they generate and discard.** Every strategy call where a client says something good is a case study that currently evaporates. Their public proof is thin — one spoken ~13× ROAS anecdote, no named case study with attributed metrics — which is a direct constraint on close rate when selling to tech-challenged small businesses who need reassurance.

**Two things to ask rather than assume:** whether she will publish marketing built from a client's words without telling that client (adjacent to the human-touch constraint — a fabricated-sounding testimonial in the wedding industry is a real problem, not a cosmetic one), and whether reels are her format of record or a leftover.

**Technical note:** the Anthropic API does not accept audio, so the voice-note leg needs Whisper or Google STT.

---

### B3 · Creative briefs and first-draft copy

**Owners:** Ivy (creative), Carmen (Google), Jacqueline (Meta), Tina (landing pages). **Never in the sheet. Whitney's own unprompted #1 nominated opportunity, 26 Aug @16:54:**

> *"I see the area of opportunity for utilizing AI in a strategic way to help them with getting creative briefs done, you know, getting first drafts of copy, first drafts of landing pages or after landing pages are done, and then checking the landing pages and seeing, are there errors? Is it good? Is it going to convert sort of thing?"*

Said in the same breath as the pain it solves — *"it always feels like we're like chasing the team"* — and **never revisited on 2 Sept.**

**She has already validated the mechanism and explained why it works:** *"if they're prompted and say, here's the meta ad strategy that ChatGPT came up with, like that, that's more of a push for them than just starting from a blank page."*

**Why it matters structurally:** onboarding runs through ~8 sequential client-approval gates across Carmen, Jacqueline, Ivy, Tina and Danielle, with one person per function and no redundancy. Every gate that starts from a blank page adds a day of latency to a client who is already paying. Time-to-first-lead is what retention turns on.

**This is also the durable, company-owned replacement for the per-client ChatGPT Projects** — the band-aid Whitney has already disowned.

**Honest risk: adoption, not build.** It lands on four people nobody has interviewed, and a generated brief can read as a mandate rather than a gift.

---

### B4 · Landing-page and funnel QA

**Owner:** nobody. **Never in the sheet.** The last clause of B3, and the only automation candidate in the entire set with **zero credential dependency**.

**Evidence this is recurring, not hypothetical.** On 26 Aug @41:28, E2M's manual due diligence found a mobile-only CTA resolving to a 404. Whitney's response: *"we actually caught that a couple of days ago"* — then immediately *"Did I email you or did I slack you about that, Gisselle, already? I don't remember."* Sixty seconds later a second broken link surfaced, in the investment guide. **Two defects in one glance at one company's own funnel, both found by humans by accident, one of them then lost in the handoff.**

Their one documented live defect is **mobile-only**, so a desktop-only crawl reports all clear on their actual bug. Mobile rendering at 375px must be a first-class pass.

**It is also the only candidate that puts Danielle on screen** — the privacy-policy page reachability check is the hard gate on her A2P/10DLC registration, which in turn gates LeadLock going live, which in turn gates the campaign URL swap back to Carmen and Jacqueline.

**Scope discipline:** pages WIA built and hosts in GHL, on a client-confirmed URL list. Crawling a client's live production property uninvited is a third-party action.

---

### B5 · Onboarding orchestration across the delivery team

**Owners:** Carmen, Jacqueline, Ivy, Tina, Danielle. **The sheet has only Gisselle's setup slice (A5).**

The ~8 sequential client-approval gates, the two parallel tracks, Danielle's DNS and A2P work, and the cross-track dependency where LeadLock going live forces the ads URL swap. Full narrative in A5.

**Diagnosis: this is primarily a state-visibility and accountability problem with generative work embedded in it.** "Chasing" means nobody can see state. That is fixed by a status surface plus nudges, not by a model. Do not sell an agent where a dashboard is the answer — and note that the dashboard must be **Slack-native**, because ClickUp has no adoption and the word "dashboard" appears zero times across both transcripts despite being in the 11 Aug sold scope.

---

### B6 · Sales call → proposal

**Owner:** Whitney. **Never in the sheet — the sheet's coverage begins only after the contract is signed.**

> *"it's usually after a sales call happens, which again, that is recorded too, right? So it's like if there was a, something scanning that or aware of that, like they should know by the end of the call, okay, this person wants to move forward with Elevate, we need to send them the Elevate proposal, or this person wants this accelerator, we need to send them that, right? And then like proactively have an email drafted for that."*

**Artifacts are URLs, not documents:** *"we've created public proposals for offers"* — so no Dubsado API is needed anywhere, just an offer→URL map.

**Blocker:** no sales-call transcript was ever requested, and detecting "this person wants Elevate" is the entire skill.

---

### B7 · The client knowledge layer — the "agency brain"

**Owner:** Gisselle builds it by hand today. **Never in the sheet** (Whitney: *"a new part of the onboarding process that we've added on that I'm not even sure if is documented here"*).

Per-client ChatGPT **Projects** on a shared `hello@` login with no Team or org account. Knowledge base seeded with the onboarding questionnaire and the messaging-and-positioning interview transcript. Used to draft Meta strategy, Google strategy, landing-page copy. The team reviews and tweaks.

**They have independently invented the concept, proven internal appetite, and identified its failure mode before E2M did.** Minu warned that knowledge bases are easy to create and rot within a couple of months. Whitney: *"Yeah, no, I mean, that's what I see coming, right?"* And: *"we don't see it as a long-term solution."*

**This is the 11 Aug thesis made concrete**, and it is what justifies a platform engagement over point automations.

**Also a security and continuity issue worth raising gently:** a shared password with no audit trail means offboarding anyone requires a rotation — awkward for a client explicitly buying turnover-proofing.

---

### B8 · Whitney's own workload

**Zero rows, zero hours captured anywhere across three calls.**

Since the account manager resigned she runs every sales call and every client call — ads kickoff, messaging & positioning, ad strategy presentation, monthly 1:1s — and reviews everything before it goes out. Her inbox is the company's communication hub.

**Founder hours are the only hours in this business with a credible revenue opportunity cost, and revenue is the axis she named herself.** A blueprint that quantifies a contractor's 18 hours and says nothing about the founder's blocked selling time is measuring the cheap resource and ignoring the expensive one.

---

# PART 3 — THE INTERCONNECTION MAP

Twenty automations, about six builds. This section is the argument.

## 3.1 The collapse, at a glance

```
                        ┌─────────────────────────────────────────┐
                        │   client_brief.md  +  updates/ log      │
                        │   (one file per client, human-editable) │
                        │   ← B7, A6-leg3                         │
                        └────────▲───────────────────▲────────────┘
                                 │ read              │ append
        ┌────────────────────────┼───────────────────┼──────────────────────┐
        │                        │                   │                      │
   ┌────┴─────┐         ┌────────┴────────┐   ┌──────┴──────┐      ┌────────┴───────┐
   │ EXTRACTOR│         │  RENDERERS      │   │  SWEEPERS   │      │   CRAWLER      │
   │  + NORM  │         │                 │   │             │      │                │
   └────┬─────┘         └────────┬────────┘   └──────┬──────┘      └────────┬───────┘
        │                        │                   │                      │
  triggers:                 outputs:            triggers:              triggers:
  · call ends (A4,A11,A3)   · recap email       · daily (A12)          · page live (B4)
  · client signs (A5,A6)    · action items      · weekly (A10)         · scheduled
  · voice note (B2)         · ClickUp tasks     · Monday (A2,A7)
  · month closes (B1)       · Slack digest
  · brief exists (B3)       · Drive filing
  · sales call (B6)         · ad/LP copy
                            · exec summary
                            · reel/carousel/email
        └────────────────────────┴───────────────────┴──────────────────────┘
                                 │
                        ┌────────▼─────────────────────┐
                        │  SLACK REVIEW GATE           │
                        │  approve / edit / abstain    │
                        │  — every client-bound output │
                        └──────────────────────────────┘
```

## 3.2 Shared-trigger clusters

**Cluster 1 — "A meeting ended."** A3 (team meeting), A4 (post-call recap email), A11 (recording → Drive), plus the extraction half of A7 (action items to chase) and the harvest input for B2 (content) and B1 (monthly narrative).

These are **not separate automations.** Whitney described A4 + A11 + the client-call half of A3 in a single sentence at 2 Sept @6:54. One trigger, five outputs. Presenting them as three cards on a blueprint lets her pick one and receive a third of a system that delivers nothing on its own — which is exactly the catalogue shape she has twice said paralyses her.

**A3 is the same engine on a different trigger.** Client call → recap email + Drive file + ClickUp tasks. Internal Monday meeting → ClickUp tasks + Slack digest, **no client-facing output.** Which makes the internal variant the risk-free place to pilot the whole thing.

**Cluster 2 — "A client signed."** A5 (ClickUp onboarding lists), A6 leg 1 (questionnaire → Drive + Slack), A6 leg 3 (seed the client brief), B5 (the downstream orchestration), B3 (first drafts feeding the gates), B6 (upstream, the proposal that produced the signature).

One trigger — the Dubsado alert email landing in Gmail — fans out to a ClickUp list, a Drive folder, a Slack channel, a team announcement, a welcome email draft, a LeadLock sub-account, and the initial client brief.

**Cluster 3 — "A clock ticked."** A12 (daily GHL sweep), A10 (weekly roll-call sweep), A2 + A7 (Monday accountability), A8 (event calendar reminders), B1 (month close).

All five are scheduled sweeps that read a system, compute a delta against a rule, and post a digest. Same skeleton, different queries.

**Cluster 4 — "Content exists."** B3 (first drafts), B2 (content repurposing), A9 (portal recap posts).

All three are renderers over the same client brief plus a transcript. B2 and B3 draw on the *same* client-brief file, which is why editing one line of the brief changes both the ad copy and the reel script — the most legible possible demonstration of "how is it all connected."

**Cluster 5 — "A page changed."** B4 (funnel QA) standing alone, but gating B5 (A2P → LeadLock live → URL swap).

## 3.3 The Monday collision

**A2, A3, A7 and the Monday half of A1 all fire on the same morning and all nudge the same five people.**

- A1: Gisselle sweeps the "waiting" tag before her Whitney 1:1
- A2: ClickUp overdue → tag the team in Slack
- A3: Monday team meeting → action items → ClickUp → Slack
- A7: chase yesterday's unacknowledged items

Building these as four independent automations means four bots messaging an already-inundated team every Monday morning. **This is one Monday accountability product with one review pass and one outbound digest.** Ship it as such or it will be turned off in week two.

## 3.4 Shared primitives

**The "did-the-human-actually-do-it" primitive.** A10 already contains A7. Gisselle creates ClickUp tasks to verify Carmen and Jacqueline actually sent the 2-week DMs (26 Aug @14:47). That flag-then-verify-the-human loop is one piece of code. Whichever of A7/A10 gets built first should own it and the other should reuse it. It is also the only mechanism in the whole inventory that addresses Whitney's most-repeated operational complaint.

**The Gmail-alert trigger, and why it is the right architectural bet.** Dubsado is being decommissioned offer by offer into GHL — done for one offer (Foolproof Follow-Up Advantage), the rest pending custom checkout pages and workflow migration. **So build the onboarding trigger on the Gmail alert signal, not on Dubsado.** The alert email survives the migration; a Dubsado integration has a shelf life measured in months. This one decision protects A5, A6 and B5 simultaneously.

**Call-type routing.** A3, A4, A11, B1, B2 and B6 all need to know *which kind of call* this was to pick the right renderer: ads kickoff, messaging & positioning, ad strategy presentation, monthly 1:1, LeadLock kickoff, internal Monday, sales call. Classify once, route six ways.

**The offer→template map.** A5 needs offer→ClickUp template (and both-services clients need two merged). B6 needs offer→public proposal URL. Same map, two consumers. Five-minute client ask; nobody has asked.

**The GHL Communities question.** A8 and A9 are gated on one identical unknown: can a post be created programmatically into a GHL Communities channel? GHL API v2 has no documented endpoint for this. One 15-minute test once portal access lands answers both rows — and the answer may be that the capability does not exist, in which case the honest answer is native scheduling plus a reminder, not a build.

**The identity-resolution layer.** A1 (sender → GHL contact), A10 (Zoom/Fathom attendee → membership roster), A12 (invalid contact → correction), A5 (signature → which client), B1 (metrics → which client). Every one of them needs to answer "which client is this?" against GHL. Build one resolver.

## 3.5 What must never be split, and what must never be bundled

**Never split:**
- A4 + A11 + A3's client-call half — one pipeline, described in one breath
- A5's scaffold outputs — a ClickUp list with no Drive folder and no Slack channel is not half a win, it is a broken onboarding
- A8 + A9 — same portal, same channels, same event calendar, same posting identity, same blocking question

**Never bundle:**
- **A1 into one item.** Four products stapled together: filing (mechanical, days), starring (gated on taxonomy + existing filters), drafting (highest value, highest voice risk, needs a sent-mail corpus), and waiting-tag cadence (a scheduling product). As one HIGH/L row with ~15 unknowns, the top-priority item on the sheet becomes the least pickable thing on the blueprint. Split it, and the filing leg becomes the fastest visible win in the engagement.
- **A6 into one row.** Three legs, three triggers, three viabilities — and leg 3's target is a band-aid Whitney intends to discard. Bundling makes the row inherit its weakest leg.
- **A2 with A7.** A2 reads ClickUp, which has no adoption. A7 reads Slack, which has total adoption. Same intent, opposite data quality.

## 3.6 The dependency chain nobody drew

The single most consequential cross-track dependency in the business, narrated by Whitney and never captured anywhere:

```
Tina builds privacy-policy landing page
        ↓
Danielle submits A2P/10DLC registration        ← gated by B4's reachability check
        ↓
A2P approved → SMS enabled
        ↓
LeadLock workflows tested (internal, then client)
        ↓
Official LeadLock onboarding call
        ↓
LeadLock form goes live on client's website
        ↓
LeadLock landing page approved
        ↓
Carmen + Jacqueline swap campaign URLs         ← "we need to switch the URL for the campaigns"
        ↓
Client considered fully onboarded → monthly maintenance begins
```

Every arrow is a handoff between two people with no shared view of state. This is what "we're always chasing the team" actually is.

---

# PART 4 — Shared infrastructure (the spine)

Standalone, the five selected MVPs cost ~8.25 engineering days. On this spine they cost ~3.5. **The spine is not scaffolding — it is the product, and it is the compounding-capability argument that justifies a platform engagement over point automations.**

## 4.1 Extractor + transcript normalizer — ~0.4 day, used by 4 of 5 cards

A strict JSON tool-schema extractor over the Anthropic Messages API with `call_type` routing. Output schema:

```
{ client, call_type, decisions[], 
  action_items[{owner, task, due_hint, evidence_timestamp, confidence}],
  client_recap_email{subject, body}, filing_path, open_questions[] }
```

Normalizer handles three input shapes: Fathom export (.txt/.md/.docx), Zoom (.vtt/.txt), and raw meeting transcripts. **Every extracted fact carries its source timestamp** — non-negotiable, because it is what makes output auditable rather than trusted.

**Robustness requirement discovered in the source material:** speaker attribution in these transcripts is frequently wrong (lines labelled "Whitney" are often Minu, and vice versa). The extractor must infer the speaker from content and never trust the label. This is also a demo asset — "the labels are wrong all the way through and the owners are still right."

## 4.2 The confidence / abstain lane — near-free, and the most important piece

Any extraction below threshold, or any ambiguous action-item owner, routes to a **"needs a human"** lane with both candidate owners and the supporting quote, rather than guessing.

It costs almost nothing because it is the same code path. Its value is demonstrative: **a founder who abandoned her own custom GPTs when they drifted needs to see the guardrail fire once**, not watch twenty-five minutes of clean runs.

## 4.3 The Slack review gate — ~0.25 day

Slack is the designated review surface. Justification is adoption evidence, not preference: 100% team adoption, Whitney volunteered access to the workspace and all client channels, ClickUp was never adopted, and "dashboard" appears zero times in either transcript.

**Deliberate engineering choice: poll-based approval.** Read approvals back via `reactions.get` / `conversations.replies` on a polling worker rather than an interactive Request URL. No public endpoint, no 3-second ACK requirement, no tunnel to die mid-demo.

**Every client-bound output in the entire inventory terminates here.** The gate is the product, not the plumbing — it is the mechanical form of the standing constraint from 11 Aug.

## 4.4 The connector layer — ~0.35 day

One authenticated, retrying client each:
- **ClickUp v2** — tasks, lists, templates, custom fields, assignees, due dates
- **Google Drive v3** — `supportsAllDrives`, folder creation, file upload
- **Gmail** — `drafts.create` on `ai@` with RFC822 MIME
- **Slack** — `chat.postMessage`, Block Kit, `channels.manage` for channel creation
- **GHL v2** — Private Integration Tokens, location-scoped: `/invoices/?altId={locationId}&altType=location`, `POST /contacts/search`, Communities, memberships

Each with a sandbox fallback stood up **before** anyone's permission matters. Written once, reused by every current and future card — this is why a second sprint's cards cost half of what a first sprint's did.

## 4.5 `client_brief.md` + the `updates/` append log — ~0.2 day

One human-readable, diffable, **Gisselle-editable** Markdown file per client. Deliberately **not** a vector store — twelve clients at a few KB each makes RAG engineering theatre.

**Critically it is read AND written.** Every pipeline run appends what it learned: the handoff engine appends decisions and action items, the report run appends the month's numbers and narrative, the page check appends its result. **The file gets truer the more the system runs.** A read-only version of this is just a template.

This is the durable replacement for the hand-built per-client ChatGPT Projects (B7) and the concrete form of the "agency brain."

## 4.6 The staleness / confirm-or-correct job — ~0.15 day

Reads `client_brief.md`, diffs against the last 30 days of appended updates, calls and metrics, and posts to Slack: *"these four facts are older than sixty days — confirm or correct."*

Minu warned that knowledge bases rot; Whitney said *"that's what I see coming."* Answering that objection with a file format alone is not enough. **This answers it with a mechanism.**

## 4.7 `agency_playbook.md` — ~0.15 day, zero credentials

The agency-level layer above the per-client layer, composable entirely from the two existing transcripts: the eight sequential onboarding gates with owners, the offer→template and offer→proposal-URL maps, the 2-week-DM / 4-week-email escalation ladder, the star taxonomy, the call-type→template map.

**Why this matters:** the 11 Aug quote is about a person who can run the **agency**, not one who knows one client. A client folder does not answer *"is there one place that we're going?"* — this does.

## 4.8 The run ledger and 30-day backtest — ~0.15 day

Every pipeline logs its runs. A backtest harness replays the engine over the last 30 days of available calls and sweeps.

**This is what finally answers the question asked on 11 Aug and unanswered for four weeks** — not with another re-frame but with counts Whitney watched accumulate, plus a defensible range with its assumptions shown and one honest statement of the single missing input (onboarding volume).

---

# PART 5 — The Sept 10 MVP portfolio

Five cards, ~4.75 build days on the spine. Ranked. **The running order is itself the argument**, because an unranked catalogue is the documented failure mode with this buyer.

| # | Card | Days | Input | Role in the story |
|---|---|---|---|---|
| 1 | **The Handoff** — after every call, and after every signature | 1.25 | E2M's own 2 Sept recording | The engine. Two triggers, one machine |
| 2 | **"Are there errors? Is it going to convert?"** | 0.75 | Their own live funnel | Opens the demo. Zero credentials — the insurance |
| 3 | **Nobody starts from a blank page** | 0.5 | `client_brief.md` | Moves the story off Gisselle's seat |
| 4 | **An executive summary instead of a wall of screenshots** | 0.5 | Mock metrics, real narrative | The biggest number in the engagement |
| 5 | **One voice note, a month of marketing** | 0.5 | Client transcript + voice note | The only revenue-tied item |

## 5.1 Card 1 — The Handoff (A4 + A11 + A3 + A5-slice)

One engine, two triggers. A client call ends **or** a client signs, and the recap email, the action items with owners, the ClickUp tasks, the Drive filing and the team announcement are all drafted and sitting behind one Slack approval.

**Why it runs on E2M's own 2 Sept recording:** Whitney personally sat through that call, so she audits the extraction against her own memory rather than trusting an accuracy claim. For a founder who had never used Claude, that is worth more than any percentage. It is also the only card whose input needs **zero client homework.**

**Demo beats:** drop the recording → action items with owners and clickable evidence timestamps → the robustness line about wrong speaker labels → **the guardrail firing on purpose**, one ambiguous item refusing to guess an owner → Gisselle presses Approve → ClickUp tasks, Gmail draft in `ai@`, Drive filing. Nothing sent. Then switch triggers without touching the engine: signed + paid → onboarding list from the right template, Drive folder, client channel, announcement. Then the internal-Monday variant with no client-facing output: *"same machine, and that is the risk-free place to start."*

## 5.2 Card 2 — Page Check (B4 + A2P readiness)

Scheduled crawl of their own funnel and client landing pages, **rendered at 375px mobile viewport as a first-class pass**, returning blockers, warnings, a conversion-readiness checklist, a LeadLock go-live / A2P readiness block, and a run-to-run diff.

**Three jobs at once, which is why it survives every lens.** It is the fulfilment work Whitney was promised twice and never got. It is the insurance — the only candidate with zero credential and zero sample dependency, so a complete demo exists no matter what arrives. And it is the only card that puts **Danielle** on screen.

**Cleanest production path in the set, and the one commitment that outlives the meeting:** a scheduled job emailing an HTML diff, left running from 11 Sept with a named owner, at effectively zero marginal cost. Every other card is a script on one laptop that stops existing when that engineer moves accounts — which is precisely the failure this engagement was sold to fix.

## 5.3 Card 3 — Nobody starts from a blank page (B3)

One client brief in; out comes Ivy's creative brief with angles and required assets, three Meta angle sets, fifteen character-validated Google RSA headlines, and Tina's landing-page copy block — every quoted differentiator carrying the timestamp it came from.

**The demo moment that answers the three-call-old question:** edit ONE line of the brief live — change the differentiator — re-run, and the ad copy **and** the reel script from Card 5 both change with it. *"That is what 'how is it all connected' looks like. It's one file, and a human can fix it."*

## 5.4 Card 4 — Executive summary (B1, narrative half only)

Metrics in; out comes a one-page client-ready executive summary that names a trend, explains what moved it, and recommends the change — plus the 90-second script for Tina's walkthrough video. **The screenshot deck is deliberately not replicated.**

**Mock metrics are the correct choice here, not a concession** — the product is the narrative, the judgement and the length. Two consecutive months of fixtures so month-over-month narrative has something to say, **with one bad trend injected on purpose** (Meta CPL up 22%, which campaign, what we are changing next) so it demonstrates judgement rather than cheerful restatement.

*"The assembling is gone. The explaining is still Tina."*

## 5.5 Card 5 — One voice note, a month of marketing (B2)

A client call plus a voice note of direction in; three reel scripts out, each quote stamped with the transcript timestamp it came from; then on approval the carousel copy, then the marketing email — the same staged sequence she walked through doing by hand, with a gate at every step.

**Kept standalone, not merged into Card 3.** Merging cuts the voice note and grounds the reel in an internal E2M ops call about ClickUp overdue tasks — a demo of the wrong thing wearing the right label. The genre problem is fixed by a 30-second forward from Whitney of one real client strategy call, not by changing the subject.

*"Nothing here is invented. Every quote has a source you can play."*

## 5.6 The close

Scroll one plain Markdown file. Edit a wrong line live to prove a human owns it. Show the `updates/` log and what wrote itself during the preceding twenty-five minutes. Show the staleness card. Show `agency_playbook.md`. Then the receipts: the run ledger and the 30-day backtest.

Then **one page, face up on the table**: five workflows ranked, cost to production, what each needs from a named person by a named date, **three recommended deletions before any automation** (collapse seven star meanings to three; merge the two roll-call sheets into one; stop hand-building per-client ChatGPT Projects — she invited process change twice), and two tick boxes.

*"The page check is already running, so it isn't a decision. Pick one from delivery and one from the top of the funnel, and we start Monday."*

---

# PART 6 — Not built, and why

Stated on the record rather than discovered later. Each is named, costed, and blocked on one identifiable thing.

| Candidate | Verdict | Reasoning |
|---|---|---|
| **A12** Daily GHL ops digest | **Rejected — keep the 10-minute verification** | Worst risk-to-impact ratio in the set and **double-gated**: credentials may not be actioned until 8 Sept, AND it rests on one unverified sentence (*"most likely we would have an API"*). The kill test cannot run until the credentials land, which is also when the build would need finishing |
| **A10** Roll call | **Rejected from the build; named as the flex swap-in** | Genuinely tempting — HIGH priority, deterministic arithmetic, the one task the client tried and failed to automate herself. But the capture leg turns on one binary unknown we cannot test until the Fathom exports arrive. **We refused to fake it.** If the exports come back structured, this swaps in at 0.5 days |
| **A5** Full onboarding orchestration | **Rejected as a card; partially shipped inside Card 1** | Carries the best surviving ROI argument and it is the pain Whitney spent seven minutes walking through and volunteered to show us. But three days does not fit, and the trigger leg is hard-gated on the Dubsado alerts arriving |
| **B7** Client knowledge layer | **Rejected as a pickable tile; built as the substrate under all five** | A five-day MVP cannot demonstrate durability, and durability is the entire value proposition. Built first, shown last, never as a sixth tile |
| **A8 + A9** Portal operations | **Rejected** | The sheet's largest derivable bundle (9.0 hrs/mo including its single biggest row) — and promoting it would mean selecting on the one axis the client demonstrably did not buy on. Worse, the capability may not exist: GHL API v2 has no documented Communities post-creation endpoint |
| **A1** Email triage and filing | **Blocked — and the most dangerous thing to sell** | The sheet's #1 HIGH row and the company's entire client-comms hub, structurally unavailable: Gmail API scope on `hello@` was never requested, `ai@` contains none of the history, and **delegation does not grant API access** |
| **A2 + A7** Monday accountability | **Rejected as standalone** | Easiest build in the set, which is the trap. Lands squarely on the one tool the team openly never adopted, so the real overdue list is probably full of stale tasks and the first genuine digest would surface dozens of items nobody intends to do |
| **B6** Proposal drafter | **Rejected from the build; offered as a live drop-in** | Strategically the most interesting rejection — top of the revenue funnel, a Whitney-workload item with zero rows anywhere. But no sales-call transcript was ever requested |
| **Danielle's LeadLock build-spec generator** | **Not built; named at 0.5 days; partially honoured inside Card 2** | She is one of four named single points of failure, holding the least-documented knowledge in the company. Needs 30 minutes of her time |
| **Card 5's audio leg** | **Descoped, not rejected** | The Anthropic API does not accept audio; needs Whisper or Google STT (~0.25 days). First cut if the week slips, replaced by a typed direction box |

---

# PART 7 — Access matrix

## 7.1 Granted or in flight (requested 3 Sept)

`ai@weddingindustryads.com` created; password rotated by E2M and returned via LastPass. Grants requested on that account: ClickUp **Member** seat (not Guest — Guests cannot open templates); GoHighLevel **Agency Admin** (stated to cover LeadLock Pro in one grant); Members Portal — Google Search Accelerator, Meta Ads Accelerator and Announcements channels; Slack workspace and client channels.

Samples requested: two Dubsado notification emails as attachments (contract signed, invoice paid) plus one completed onboarding questionnaire; Fathom **exports** of two office-hours transcripts plus one client meeting; one fully-onboarded client's Drive folder plus confirmation of personal-Drive vs Shared-Drive; one complete monthly report plus its walkthrough video; the post-call recap / onboarding welcome / overdue-invoice nudge / campaign-review email templates; one client's whole ChatGPT Project.

## 7.2 Not requested — each blocking something named

| Missing | Blocks | Ask precisely |
|---|---|---|
| **Gmail API scope on `hello@`** | A1 entirely | **Delegation does not grant API access.** Either `hello@` completes an OAuth consent for the E2M app, or a Workspace superadmin creates a service account with domain-wide delegation |
| **Existing Gmail filters export** | A1's filing leg | Settings → Filters and Blocked Addresses → Export to XML. 30-second client action. Building on top blind will double-label and fight the existing layer |
| **Attributed sent-mail corpus** | A1's voice profile | Without it, a generic agency voice reads as generic to exactly the person who can tell |
| **Zoom on Whitney's account** | Card 1's production trigger, B2, B1 | Highest-value transcript corpus in the company. Cloud recordings + transcripts access |
| **Google Ads developer token + MCC linkage** | B1 production | Approval measured in days to weeks. **Start today** — the lead time is the constraint |
| **Meta System User token, `ads_read` per ad account** | B1 production | Via Business Manager, per client |
| **Fathom API or team account** | A3, A10, Card 1 automation | Whitney pre-consented: *"if we need to switch to a team account, I mean, we totally can"* |
| **Slack workspace-admin app install** | Five outputs + the review surface | **Highest fan-out unknown in the plan.** A Member seat does not imply install rights. Scopes: `chat:write`, `chat:write.public`, `reactions:read`, `channels:history`, plus `channels:manage` for channel creation |
| **Google Workspace OAuth allowlist for `ai@`** | Drive, Gmail draft and Sheets legs — all at once | Many Workspaces block unconfigured third-party apps by default. **Test in hour one, not day four.** An E2M-owned Cloud project is external to their Workspace, so sensitive scopes show an "unverified app" screen and cap at 100 test users — anticipate and script it so it does not happen live |
| **Danielle: 30 minutes + her LeadLock kickoff transcript** | B5, the A2P readiness block | Least-documented knowledge in the company |
| **Client landing-page URL list** | Card 2's live-crawl moment | Confirm in Slack; never infer from ad copy. A client's live property is third-party |

## 7.3 One request that will probably bounce

The ChatGPT **Project** share. Confirmed 2 Sept @31:16–@31:28: they are on a shared `hello@weddingindustryads.com` login, explicitly **not** a Team or org account. Project sharing across accounts is not generally available outside Team/Enterprise. **Pre-empt it:** ask Gisselle instead to export the Project's uploaded files plus a copy-paste of the custom instructions, or to screen-record a walkthrough. Otherwise two days go to a round trip.

## 7.4 Cheap client asks nobody has made

- **The onboarding volume number** — clients onboarded per month, last three months. One Slack message. It is the single missing multiplier that prices A5, A4 and A11 simultaneously
- **The offer→ClickUp template map** — five minutes; both-services clients need two templates merged
- **The offer→public proposal URL map** — five minutes; *"we've created public proposals for offers"*, so the artifact is a URL and no Dubsado API is needed anywhere
- **Portal member count by track** — sizes A10
- **Whether Tina's walkthrough video is scripted or improvised** — if improvised, a script reads as a constraint rather than a gift
- **Confirm the review date** — Whitney flagged a Wednesday conflict and volunteered Friday morning; Asha never closed it. A Friday buys a full working day
- **What row 29 of the audit sheet was going to be** — orphan comment, *"Only done once every 6 months-ish"*
- **Check what is already shared first** — Gisselle *"did share a few documents"* on 2 Sept @1:05, so the roll-call sheets may already be in hand. Do not ask twice

---

# PART 8 — Quantification and ROI

## 8.1 The derivable table

| Task | Time × frequency | Hrs/month |
|---|---|---|
| A2 · TASK-05 | 0.5 × 4 | 2.0 |
| A3 · TASK-06 | 1.0 × 4 | 4.0 ("max") |
| A8 · TASK-11 | 0.25 × 12 | 3.0 |
| A9 · TASK-12 | 0.5 × 12 | **6.0** |
| A10 · TASK-13 | 0.167 × 12 | 2.0 |
| A12 · TASK-15 | 0.05 × ~22 | ~1.1 |
| **Total quantifiable** | | **~18.1** |

Only 6.0 of that is client-attested (column F). Against Gisselle's ~100–108 hr contracted month that is **~17% of one seat.**

**Six tasks contribute zero** because they cannot be quantified at all: A1, A4, A5, A6, A7, A11 — including **two of the three HIGH-priority items.**

## 8.2 The arithmetic that must not be the headline

Ceiling test at 100% automation with zero review time: 18.1 × 3 months = **54.3 hours.** Against the $9,499 Apollo price = **$175 per recovered hour.** Break-even at a generous $30/hr contractor cost requires 105.6 hrs/month — Gisselle's entire contracted capacity. Apply a realistic 60% net reduction and it falls to ~10.9 hrs/mo, ~32.6 hours over the term.

The 100% premise is already excluded by the client's own human-review constraint.

**Any buyer who does this division kills the deal, and Whitney is capable of doing it.** The honest and stronger move is to say it first: *"time savings on Gisselle's audited tasks alone will not pay for this — here is the case that does."*

## 8.3 The cases that survive scrutiny

1. **Onboarding throughput.** ~8 sequential approval gates, one person per function, no redundancy. Every gate starting from a blank page adds a day of latency to a client who is already paying. Time-to-first-lead is what retention turns on.
2. **Tina's double-booking.** She owns monthly reporting *and* every landing page and nurture sequence for every in-flight onboarding. Every client signing in the first week of a month waits behind a screenshot deck. **Revenue timing, not admin cost.**
3. **Turnover-proofing the four single points of failure** Whitney named herself — the actual thing she said she was buying in August.
4. **Founder capacity returned to selling.** The only hours in the business with a credible revenue opportunity cost, on the axis she named herself, and entirely unmeasured.

## 8.4 The measurement gap, and how to frame it

No hours baseline was captured on either weekly call. Zero instances of "how long", "how much time", "hours per", "measure", "ROI", "percent" or "3 months" across both transcripts. The one occurrence of "time tracking" is Minu mischaracterising the roll-call task, which Gisselle immediately corrected.

**Three quantification openings were opened and abandoned:** email volume (anchored by the interviewer with "5 to 10", answered by echoing the anchor, minutes-per-email never asked); lead/contact volume (2 Sept @10:42, answered with a process re-description); onboarding volume (volunteered as *"a lot of clients"*, number never requested).

**Frame it carefully.** *"We never asked"* and *"the client left it blank"* are different admissions. Column F was filled on 2 of 12 rows by the client, and six rows carry the client's own non-numeric answers. **Present it as a shared measurement gap with a named fix**, and never present 18.1 hrs/month as anything other than an explicitly labelled floor.

**The named fix:** a five-business-day time log from Gisselle starting Mon 7 Sept, two columns — task, minutes. It deliberately captures the Monday peak she flagged in her own TASK-04 cell. Lands 11 Sept: in hand if the review moves to Friday, and either way it converts Asha's private sync from *"we don't know"* to *"data lands tomorrow."*

---

# PART 9 — Standing constraints, risks and open questions

## 9.1 Non-negotiable constraints

1. **Nothing client-facing sends without human review.** Whitney, 2 Sept @8:01: *"we'll review any drafts before they go out."* Every automation producing client-bound output terminates in a review queue, never a send.
2. **The human touch on client relationships stays human.** Wedding-industry clients buy hand-holding. Do not propose automating relationship contact.
3. **The review surface is Slack.** Adoption evidence, not preference.
4. **Roll-call and similar flags only flag.** *"Just needs to flag, we will manually follow up."*
5. **Whitney's acceptance bar for drafts:** her voice, no double work, and a mechanism that learns from her sent edits.

## 9.2 Live risks

- **Slack app install is the highest fan-out unknown.** Five outputs and the review surface depend on it. Mitigated by the poll-based gate (no webhook, no tunnel) and an E2M sandbox workspace standing before anyone's permission matters.
- **Their Workspace may block the OAuth app for `ai@`**, killing Drive filing, the Gmail draft and any Sheets leg simultaneously. Test hour one. Degraded state: a proposed filing path plus a rendered draft preview, stated as degraded.
- **The Dubsado alerts probably will not arrive in time.** 5 Sept is a Saturday, 7 Sept is US Labor Day for a Texas client, and the person gathering six artifacts is the same overloaded contractor who is also the audit's subject. Realistic arrival: Fri 4 or Tue 8 Sept. Build the parser schema-first and format-agnostic.
- **No real client corpus makes two cards thinner than they look.** A brief composed from WIA's own positioning proves a renderer, not an agency brain holding a client's knowledge — and Whitney will feel the difference.
- **Voice fidelity is the weakest spot and it is gated on a sample.** Without the template pack, present the recap email as structure-only.
- **The mock sentence can cost more than the card returns if it is mumbled.** Said once, early, with the structural reason attached, it pre-empts the objection and buys trust. Said defensively it becomes the one dishonest moment in the review. Same discipline for the other two honest sentences: the roll-call capture we refused to fake, and the GHL Communities question.
- **The opener's bug may be fixed.** Two-minute recheck at 375px the morning of the review decides the opening line; the diff view converts a clean result into proof of monitoring.
- **Nothing survives 11 Sept unless someone owns it.** Every card is otherwise a script on one laptop — the exact failure this engagement was sold to fix. Commitment: Card 2 runs as a scheduled job from 11 Sept with a named owner.
- **Gisselle is in the room and she is the subject of the audit.** She filled out the most detailed sheet Minu says she has seen, and this portfolio funds only part of it. She is also the person who would operate every one of these workflows. **She is scripted as the approver in the demo** — if she leaves feeling audited and discarded, nothing gets adopted no matter which two Whitney picks.
- **Adoption risk exceeds build risk, and two cards land on people nobody interviewed.** Ivy, Carmen, Jacqueline and Tina may use a generated brief or resent it, and there is no evidence either way. Put it to Whitney as a question, and propose four 30-minute discovery conversations as scoped Apollo work — which turns the risk into a lever.
- **The predicted failure is not a "no."** It is *"this is helpful, let me think about which ones"*, then drift. Which is why the close is a physical one-page ranked sheet with costs, named owners, named dates and two tick boxes — plus six days of real run receipts.

## 9.3 Open questions, by owner

**Whitney:** onboarding volume, last three months · hours/week on the recap-disperse-chase loop and on client calls · will she publish marketing built from a client's words without telling that client · are reels the format of record · confirm the review date · confirm the client landing-page URL list · is Daniela Justus the same person as Danielle

**Gisselle:** five-day time log · the invalid-email filter definition · which GHL workflow handles re-enrolment and does it double-send · Drive folder taxonomy and naming convention · how team-member acknowledgement is tracked today and what counts as "no acknowledgement" · what row 29 was going to be · the existing Gmail filter export

**Tina:** real hours for the monthly report cycle, per client and total · is the walkthrough video scripted or improvised

**Danielle:** 30 minutes on DNS, A2P/10DLC and the workflow patterns · her LeadLock kickoff transcript

**Carmen and Jacqueline:** would they stop hand-marking attendance · how do they feel about AI in their workflow

**Technical, testable by E2M:** does the GHL Agency SaaS API expose invoices and saved contact filters · can a post be created programmatically into a GHL Communities channel · do Fathom exports carry structured attendee names · is the client Drive folder in a Shared Drive · do the Dubsado alerts carry parseable client identity and offer type

---

## Appendix — engagement timeline

| Date | Event |
|---|---|
| 11 Aug 2026 | Sales/discovery call (Kevin Svec + Khushbu Doshi × Whitney + Daniela). Standard audit skipped. Apollo $9,499 quoted; the cheaper **Audit & Blueprint** closed instead, creditable against Apollo on upgrade |
| 26 Aug 2026 | Weekly Sync 1. Team introduced (Asha, Minu, Jainil). Roll call and the Gmail workflow mapped in depth. Whitney redirects to fulfilment at 16:43 |
| 2 Sept 2026 | Weekly Sync 2. Sheet closed out in ~17 min; the full fulfilment lifecycle narrated in ~21 min. Access model agreed (`ai@` + LastPass). ClickUp non-adoption disclosed |
| **3 Sept 2026** | Access request sent. **This document.** Asha's recap and requirements list due |
| 10 Sept 2026 (or 11th) | **Blueprint Review.** Whitney's homework: pick a couple of workflows for execution. Asha's private 15-minute execution sync immediately after |
| Quarterly thereafter | Asha, 2 Sept @45:00: *"don't consider the blueprint as a final one. We always upgraded, you know, every quarterly, like when we start discussing with other team members as well"* |
