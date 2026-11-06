# Meeting 01: Assessment kickoff (weekly sync #1)

**Date:** 2026-08-26 · **Duration:** 44 min (ran ~5 min over) · **Source:** Fathom transcript → [source.md](source.md)
**WIA:** Whitney Hodges (founder), Gisselle Jimenez (EA / ops, based in Honduras). *Daniela was not on the call.*
**E2M:** Asha Kumar (client account manager), Minu Bhatt (AI adoption specialist, led the call), Jainil (AI engineer, introduced, silent)

## TL;DR
This was the first working session of the 3-week assessment. Gisselle had already filled out a very detailed task-audit sheet. Minu worked through it by priority, but reached only **two rows**:
- the office-hours roll call, a manual Google Sheet with 2-week and 4-week miss flags
- the Gmail triage workflow, with its star taxonomy, labels and a "waiting" tag

In the middle of the call **Whitney widened the brief unprompted**. She described four needs:
- onboarding that "never feels like it's actually going smoothly"
- a post-call loop of recap → action items → chase → report back
- AI drafts of creative briefs, copy and landing pages
- a content engine that turns client calls into reels, carousels and emails

Her priority: *"we need more leads. We need more sales."* She also asked the question that frames the whole blueprint: *"how is it all connected?"* She gave wide latitude to change processes ("not tied to the labeling system at all") but set a firm bar: drafts in her voice, no heavy rewriting, nothing reaching a client unreviewed. Minu parked fulfilment and growth until later weeks. The blueprint (~2 weeks out) was named as the point where they decide which to focus on.

## Decisions
- **Session order: operational efficiency (Gisselle's tasks) first, fulfilment and growth in later weeks** (Minu, 22:05–23:19; Whitney agreed). The blueprint is the "inflection point" for choosing the focus.
- **Process-change latitude granted.** "Definitely open to changes… I am not tied to the labeling system at all" (Whitney, 39:09–39:36; Fathom mislabels this as Minu).
- **Human review stays the default for anything to a client.** Only narrow exceptions exist today:
  - Whitney has already said "just send it" in Slack
  - short acknowledgements (rare)
  - confirming work a client has already approved (31:35–32:40)
- **E2M ↔ WIA day-to-day communication moves to Slack.** Asha will create a group with the stakeholders (43:00).

## Commitments
| Owner | Commitment | Due | Status |
|-------|------------|-----|--------|
| E2M (Minu) | Send a **client requirements document**: the steps and the accesses needed to start technical feasibility (40:33) | Before next call | **Done Sep 3**, a week late: Jainil's feasibility request in Slack (see `access_wia.md`, requests log) |
| E2M (Asha) | Share the recording of "the Claude session we had yesterday" (Aug 25), which Whitney asked for (42:36) | ASAP | Unknown |
| E2M (Asha) | Create a Slack group with the stakeholders (43:03) | ASAP | Unknown |
| E2M (Minu) | Next week: 20–25 min more on efficiency items, then move to **fulfilment use-case ideas** (40:51–41:03) | Sep 2 | Sep 2 covered invoices, portal posts and onboarding (per recap) |
| WIA (Whitney) | Walk E2M through the full-service **onboarding process** in ClickUp (15:50, offered) | Next call(s) | **Partly.** Narrated verbally on Sep 2, but the ClickUp template itself was never screen-shared. E2M pulled it through the API by Sep 8 (`.clickup-snapshot/`) |
| — | Mobile homepage CTA → 404 (flagged by Minu, 41:28). WIA was aware of an investment-guide link problem but *not* the website one | — | No owner committed. Check whether it was fixed |

## New facts & corrections
**Correction to M00.** Khushbu's M00 case for skipping the audit was that WIA had "step-by-step ClickUp boards" and "templates for every step". But for Gisselle's tasks, *"I don't think a lot of the stuff that I included have, like, detailed SOPs"* (0:39). The sheet gives descriptions, not procedures. The onboarding process *is* documented in ClickUp (Whitney, 15:50), but Whitney also says it never runs smoothly and the team has to be chased (16:54). That's an early sign ClickUp is the record, not the driver.

**Office-hours roll call** (the audit row's "time tracking")
- Two weekly 1-hour Zoom sessions, both on **Thursday**:
  - Google Ads office hours, run by **Carmen**, ~10 or 11am CST
  - Meta Ads office hours, run by **Jacqueline**, ~3:30pm
- Open format, no agenda. Accelerator members join whenever they like during the hour.
- An **AI notetaker is present** (12:24). After each session the host posts **a recap in Slack** with a report and summary (8:16).
- The host marks attendance in a **roll-call Google Sheet**, one for Meta and one for Google. Each Thursday Gisselle updates an attendance tab with:
  - members
  - consecutive misses
  - last attended date
  - 2-week flag and 4-week flag
- Attending resets the miss count. Rows are duplicated and dates typed **by hand every week**.
- **2-week miss** → the host sends a **DM via the members portal**. Gisselle creates a **ClickUp task to check the DM was sent**. **4-week miss** → an email.
- **Two failed automation attempts:**
  - a Zapier (transcribed "Sapir") flow from Sheets to email reminders that she worked out with ChatGPT. She got lost on rows and dates.
  - a ClickUp recurring-task loop that broke on "complete a task, now create the next one".
- Gisselle: *"right now it's manageable because we have… not a large number of members."* So the volume is low. The number of members was never asked.
- Gisselle also posts an office-hours reminder **1 hour before each session** (a separate audit row).

**Members portal**
- The portal is **GHL Communities inside LeadLock** ("LeetLog" in the transcript). Only accelerator clients get it. It includes "the vault".
- Full-service clients get full-funnel GHL builds, Google and Meta ads, and a **monthly meeting**.

**Gmail workflow** (`hello@weddingindustryads.com`, the company inbox)
- Whitney stars what matters. Gisselle's Monday routine:
  - draft replies where needed
  - star according to the system
  - file no-action emails into category folders
- **Reply SLA: 24–48 business hours.** Team members' replies sometimes get lost in their own inboxes, so WIA is usually CC'd and Gisselle monitors.
- **Star taxonomy (about 7 markers)** (27:00):
  - gold = Whitney starred
  - red = action for Gisselle (draft a reply, file a recording)
  - drafted, waiting for Whitney to review and send, or for a Whitney action such as paying an invoice
  - important, no immediate action, keep starred
  - needs a reply from a team member, monitor it
  - important information, no action
  - Whitney needs to dig into it
- **Some existing Gmail automations auto-tag mail**, but nothing auto-archives. Gisselle archives read, unstarred mail by hand.
- **`waiting` tag** = waiting on the client. Each Monday, before her meeting with Whitney, Gisselle reviews it: "this customer hasn't replied in two weeks, should we follow up?"
- **Labels:** one per client, plus newsletters, partners and tools (Canva, **Dubsado**, which appears here only as a tool; see hindsight).
- Label lifecycle:
  - Items stay starred until the conversation closes, then get unstarred, labelled and archived.
  - A **new client label is created when the client "signs up"**: proposal filled, contract signed, invoice paid. Gisselle then backfiles their lead-stage emails into it.
- Context for drafts comes from Gisselle's daily monitoring plus Slack. "Almost all communications start with an email", so the thread carries the history.
- **Volume: about 5 drafts a day, 10 at most** (36:28).
- **Gmail is the CRM in practice.** It syncs to GHL, where Whitney looks at pipeline stages. Whitney: moving lead communication into GHL "probably would actually be a best practice" for open-tracking and snippets. It hasn't happened because in LeadLock (GHL) Whitney can't see drafts Gisselle writes, and formatting changes when sent (35:43).
- **Emails that start proactively come from calls:**
  - after a **sales call**, e.g. "wants Elevate → send the Elevate proposal"
  - action items from the **Monday team meeting**
  - Whitney wants AI to read those recordings and draft these automatically.

**Whitney's unprompted scope (15:50–21:47)**
1. **Onboarding** (full service): lots of hands and dependencies; "always feels like we're chasing the team".
2. **Fulfilment drafting:** creative briefs, first-draft ad copy, first-draft landing pages, landing-page QA ("errors? will it convert?").
3. **Post-call loop, across every client type:** recap to the client → share with the team → make sure it's read → create action items → chase them → report back to the client.
4. **Inbox drafting that sees everything.** It "can't happen in isolation"; it has to read Slack and Google Drive (recordings, client files) too.
5. **Content engine.** Client strategy calls are "our best content" and the source of case studies. Today: Whitney flags a call → Gisselle pastes the transcript into ChatGPT → a reel script → Whitney refines and records → a carousel → an email. She wants to give a voice note ("reference this call, here's the direction") and get multi-format content back.
6. **"How is it all connected?"** She browsed E2M's AI library and left with a list, not a system: "is there one place that we're going, and then there are just like, different tabs?"

**Other**
- Whitney attended an **E2M Claude session on Aug 25** and asked for the recording. This is the first sign of AI-literacy work after M00's "never used Claude".
- Minu's self-introduction: a background in "sales, project management, and AI project speech and text analysis". In M00 Khushbu described the adoption specialist as having "5–6 years core AI/ML". Daniela asked about this role in M00 and wasn't on this call.

## Client signals
- **Growth is the real priority.** *"Yes, I want to keep refining our operations… But we need more leads. We need more sales."* (19:21–21:47 block). The ops work only matters to her if it frees capacity for growth. This matches M00, where she wanted to move into sales and marketing.
- **She wants a system, not a catalogue.** *"I don't even know what we should be starting with… how do all of those things work together?"* (19:21). This is the M00 "very ambiguous" worry again. E2M's AI library made it worse, not better.
- **The chasing is what hurts most in operations.** "It always feels like we're like chasing the team to get done the things that need to get done" (16:54). She raised it again in the post-call loop ("chase those action items and make sure that they actually get done").
- **Her quality bar for AI drafts** (39:36–40:03):
  - timely
  - covers "the bulk" of what she'd say
  - no double work or heavy rewriting
  - it learns from what she actually sends
  - "it sounds like it's in my voice"
- **The client and lead experience is sacrosanct.** Changes are fine as long as they're not "negatively affecting the client experience… or what the leads are experiencing" (39:09). This matches Daniela's M00 requirement.
- **Gisselle is an unusually strong informant.** She's detailed, self-aware ("probably not the most efficient way"), and has already tried to automate things herself. Minu called her sheet "one of the most detailed ones I've seen".
- Whitney took the 404 flag well ("Thank you for pointing that out"). The due-diligence move built credibility.

## Scope impact
- *Corrected after M04.* **The most-discussed items weren't the ones that got picked.** Roll call and Gmail triage took most of the call. Neither is in WIA's three chosen priorities (Content Engine → Paid Media Reporting → Knowledge Base).
- **What Whitney raised unprompted is what got picked:**
  - **The content engine** (reels, carousels and emails from client calls, 19:21–21:47) → **Marketing & Content Engine, the *first* priority** (M04). This call is where it came from.
  - Briefs, copy and landing-page drafts → the per-client context in the **FF-01 knowledge base**.
  - The post-call loop and "chasing the team" were OP-01/OP-02 in the Sep 15 draft. Ops is not a stream in the final three, but meeting action items survive as a knowledge-base sub-item.
  - Onboarding → the **Client Onboarding MVP** (`MVP 1 - onboarding.md`) was demoed in M03 but not picked.
- **Not picked:** whole-context inbox drafting; landing-page QA; roll call.
- **Design notes from this call:**
  - **The roll call probably needs no sheet at all.** Zoom's participant report can supply attendance, and the flags are just a rule. The remaining human step is the host's DM, which should stay human under the review rule.
  - **Gmail triage:** Whitney's latitude means E2M can replace the 7-marker star system with labels that are both AI-friendly and human-readable. It doesn't have to be reproduced.
  - **The onboarding trigger:** "proposal filled, contract signed, invoice paid" is the moment a client label is created. That event is what the onboarding MVP later hooks onto.
  - **Drafting quality depends on voice.** Whitney's "learning from my output" means a feedback loop from her sent mail. That makes a store of her sent mail and voice (FF-01-style) a prerequisite for any drafting agent.

## Open questions
- **How much time do the roll call and inbox triage take each week?** Not asked on the call. Gisselle's sheet has a duration column, but only 2 of 12 rows were filled in by the client (the derivable total is 18.1 hrs/mo, of which 6.0 is client-attested, per `automation_scope.md`). The call was the chance to fill that gap, and it didn't.
- How many portal members are there, and how many clients are in onboarding at once? This decides whether the roll call is worth automating.
- Which **existing Gmail automations** already auto-tag mail, and what are their rules? Mentioned (27:00), not explored.
- **Which AI notetaker** is on the office hours and client calls, whose account is it on, and where do the transcripts live? The answer decides the transcript integration.
- Can a **members-portal DM** or post be sent through GHL's API, or only by hand?
- Does a **brand voice / tone document** exist, or must voice be inferred from sent mail and recordings?
- **Daniela's M00 question on fulfilment and reporting load** is still unasked. She wasn't on this call.
- Who at WIA owns fixing the **mobile 404 CTA** and the openly shared investment-guide PDF?

## E2M performance
**What landed**
- Minu's opening ("you need not repeat everything") answered M00's worry about time on the client's side.
- **The screen-share walkthroughs of the real sheet and the real inbox were the most valuable part.** We now have ground truth, not a description.
- Praising Gisselle's sheet, and normalising her failed automation attempts ("it happens to us all the time"), built rapport with the key informant.
- **Asking outright about openness to change** got explicit latitude that will make the design much easier.
- The 404 find, from pre-call due diligence, was specific, verifiable and new to them.
- The efficiency-vs-fulfilment framing, with a named decision point, gave Whitney's flood of ideas somewhere to go.

**What didn't**
- **Only two rows covered, and the call ran over.** The high and medium priority rows were never reached.
- **Too much time on the lowest-value item.** Roughly 18 minutes went on the roll call, a low-volume task Gisselle called "manageable". Whitney's highest-energy topics (onboarding, the post-call loop, content, growth) got parked.
- **No quantification in the call.** No hours per task, frequency or member counts were asked, even though the sheet's duration column was mostly empty. The ROI question from M00 moved no closer to an answer.
- **"The primary thing we are trying to solve for is operational efficiencies" (22:38) cuts against Whitney's own stated priority** of more leads and more sales. She agreed, but the tension will come back if the blueprint reads as ops-only.
- Two leads got no follow-up: the auto-tagging automations, and where the AI-notetaker transcripts live.
- The E2M engineer was introduced but not used. There were no technical questions about APIs or accesses.

## Prep for next meeting (Sep 2)
- Open by **quantifying**: hours a week for the roll call, inbox triage and post-call follow-ups, plus member and onboarding counts.
- Get the **onboarding walkthrough** Whitney offered, and map every handoff and chase point in it.
- Ask **where call recordings and transcripts live** (notetaker, account type, API) and **where the team actually communicates** (Slack vs ClickUp).
- Bring **1–2 fulfilment or growth ideas**, as Minu promised (e.g. the content engine), so Whitney's priority is visibly on the table.
- Raise Daniela's question: what ongoing fulfilment load (reporting, etc.) sits outside Gisselle's sheet?
- Deliver the requirements/access document and the Slack group *before* the call.

## Hindsight: how this call reads against later meetings
*Provisional. Based on `meeting recap.md` (Sep 2); re-confirm when Meeting 02 is analysed here.*
- The "AI notetaker" (12:24) → **Whitney uses Zoom's native recording**. The team's Fathom accounts are individual free plans with no API.
- Onboarding "documented in ClickUp" (15:50) → **the team never really adopted ClickUp**. Slack is where they actually work, so "chasing the team" has to happen in Slack.
- Dubsado appears only as a newsletter "tool" (30:08) → **contracts and first invoices are generated in Dubsado**, and its signed/paid alerts in Gmail are the real onboarding trigger. That means the onboarding trigger currently lands under a label Gisselle calls "usually not priority", which may explain slow kickoffs.
- The Slack office-hours recaps (8:16) → confirmed as a ready-made input for the portal recap posts.

---
*Transcript notes: speaker labels are heavily scrambled. Many of Gisselle's lines are tagged Whitney or Minu (e.g. 24:00, 11:06). Whitney's "I am not tied to the labeling system" (39:36) is tagged Minu. Mis-hearings: "Chadipati" = ChatGPT; "Sapir" = Zapier; "LeetLog" / "lead log" = LeadLock (the existing `meeting recap.md` repeats this error as "LeadLog"); "Depsado" = Dubsado; "Chazal" = Gisselle; "MET ads" = Meta Ads; "cloud session" = Claude session.*
