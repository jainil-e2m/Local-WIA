# Meeting 02: Ops wrap-up + onboarding walkthrough (weekly sync #2)

**Date:** 2026-09-02 · **Duration:** 48 min · **Source:** Fathom transcript → [source.md](source.md)
**WIA:** Whitney Hodges (founder), Gisselle Jimenez (EA / ops). *Daniela absent again.*
**E2M:** Asha Kumar (client account manager), Minu Bhatt (AI adoption specialist, led). Jainil is listed as attending in `meeting recap.md` but can't be heard in the transcript.

## TL;DR
This was the last discovery session before the blueprint, and **the most valuable call of the assessment**.
- **The first 18 minutes closed the admin rows:** call recordings, overdue invoices, invalid emails, portal reminder posts.
- **Access was agreed.** WIA will create an `AI@weddingindustryads.com` identity and share it via LastPass, with access to ClickUp, GHL, the members portal, Slack and every client channel.
- **Whitney then walked through the whole client lifecycle**, from signed contract to monthly maintenance. That walkthrough settled four things E2M had assumed wrongly:
  - Contracts are in **Dubsado**, not GHL. Its signed/paid alerts in Gmail are the real onboarding trigger.
  - **ClickUp is a checklist the team ticks off, not where it works.** Slack is.
  - **Whitney records calls in Zoom, not Fathom.**
  - The biggest unlogged pain is **Tina's monthly client reporting**. It takes the first few business days of every month and isn't automated at all.
- **The fulfilment AI already exists as a prototype:** a ChatGPT Project per client, which Whitney calls a "band-aid".

The blueprint review was set for next week. Whitney's homework afterwards: pick "a couple of the workflows" to execute.

## Decisions
- **Access mechanism.** WIA creates `AI@weddingindustryads.com` (0:05–1:33). Credentials go **via LastPass to Minu**, who distributes them (47:08). Access to map:
  - ClickUp
  - GHL
  - the members portal
  - **Slack and all client channels** (Whitney offered this unprompted, 42:16)
- **Fathom:** WIA will switch to a team account "if we need to… whatever we need to do to make this work efficiently" (4:00–4:08).
- **Human review before anything reaches the client** is confirmed again for the post-call recap and action-item loop: "if it's going out to the end client, we definitely want someone to review it" (7:58).
- **Collecting ad-account access stays manual.** Whitney screen-shares and takes remote control on the kickoff call. "We've tried it so many different ways over the years" (28:45–29:12).
- **Sequencing (Minu):** quick wins on operational inefficiencies first; then departmental and cross-department automations "over a couple of months"; then custom fulfilment solutions (40:36).
- **Next session = blueprint review.** WIA then picks a couple of workflows to execute (41:27–41:38).
  - Proposed for **Thu Sep 10, same time**, with Fri morning as fallback (Whitney has a Wednesday conflict).
  - Straight after it: a 15-minute Asha + Whitney sync on execution and plans (45:25).
- **The blueprint is not final.** Asha said it gets upgraded quarterly as other team members are interviewed (45:00).

## Commitments
| Owner | Commitment | Due | Status |
|-------|------------|-----|--------|
| WIA | Create `AI@weddingindustryads.com` and share credentials via LastPass to Minu | Before blueprint | Done by Sep 3. E2M changed the password at first sign-in and shared it back to Whitney and Gisselle |
| WIA | Grant access: ClickUp, GHL (both accounts), members portal, Slack + all client channels | Before blueprint | **Invites sent Sep 4**, plus the Shared Drive. GHL level and client channels TBD (`access_wia.md`) |
| WIA (Gisselle) | Send 1–2 office-hours transcripts (Fathom) (5:24–6:16) | Before blueprint | Done Sep 4: **two Fathom share links** (not exports) |
| WIA (Whitney) | Confirm the blueprint slot (Thu Sep 10 or Fri morning) | Sep 3 | Open |
| E2M (Asha) | Recap email + **list of items needed for technical feasibility** (41:51, 47:08) | Sep 3 | **Done Sep 3.** Jainil sent the feasibility request in Slack (see `access_wia.md`, requests log) |
| E2M (Minu) | Once access lands, go through the ClickUp onboarding checklist for quick wins (40:36) | Before blueprint | Open |
| E2M (Minu) | Once added to the portal, check the built-in scheduling/posting features. "We don't need to over-engineer it" (18:27–18:42) | Before blueprint | Open. This gates the portal-post automation |
| E2M | Blueprint review: every identified workflow, pickable (41:27) | Sep 10 | Open |
| E2M (Asha) | 15-minute sync with Whitney after the blueprint: execution + plans (45:25) | Sep 10 | Open |

**From M01:** Minu promised "a couple of ideas for… our fulfillment aspect". **None were presented.** The fulfilment slot became Whitney's onboarding walkthrough instead. The discovery was far more valuable, but the promise itself wasn't kept.

## New facts & corrections
**Corrections (these confirm the provisional entries in the running log)**
1. **Contracts live in Dubsado** (23:00–24:09).
   - After a sales call, Whitney sends a recap email pointing to a **public proposal** for the offer.
   - Accepting it generates the agreement and the first invoice in Dubsado.
   - **Signed/paid alerts land in the Gmail inbox. That alert is the onboarding trigger.**
   - They are migrating off Dubsado into GHL (LeadLock), which is on Gisselle's plate. It's **done for one offer only, Foolproof Follow-Up Advantage (FFA)**. The rest needs custom checkout pages, contracts and workflows in GHL.
   - So today there are **two trigger sources**: Dubsado for most offers, GHL for FFA.
   - In M01 Dubsado showed up only as a newsletter "tool" label.
2. **ClickUp is the record, not where the team works** (42:16). "The team has never, like, fully adopted ClickUp other than to just, like, check off the tasks… Part of that's probably on me, it's just like, not how my brain works." Slack is where operations happen.
3. **Recording tools** (3:07–4:08, 5:24):
   - Whitney uses **Zoom's native recording and transcripts** and hasn't used Fathom lately.
   - Gisselle, Jacqueline, Carmen and probably Danielle have Fathom, on "personal sign-ins using their work email… probably free accounts". So likely no API.
   - **Office hours are recorded by Fathom.**
   - Since the account manager left, **Whitney runs *all* onboarding and strategy calls**. So the most valuable transcripts sit in Whitney's Zoom.
4. **Fulfilment AI exists as a prototype** (29:46–32:26).
   - Gisselle creates a **ChatGPT Project per client**. Whitney first called it a "custom GPT", then corrected herself.
   - Knowledge base: the onboarding questionnaire plus the **messaging & positioning interview** transcript.
   - It drafts Meta ad strategy, Google ad strategy and landing-page copy.
   - It runs on the **shared `hello@` login**, not a team or org account.
   - Minu named how this fails: the knowledge base goes stale a couple of months in. Whitney: "that's what I see coming… a band-aid solution… not a long-term solution."
   - Its purpose today: "more of a push for them than just starting from a blank page."
5. **"Customized ad strategy… in all honesty, it's pretty similar for each client"** (33:01). This softens M00's "every touch point fully personalized". The framework and strategy are templated; the personalisation lives in the copy and messaging. So strategy drafting is highly automatable.
6. Minu assumed the office hours were **in person** (4:56). M01 had already established they're on Zoom, and Gisselle corrected it. A minor slip.

**Admin rows closed**
- **Post-call loop** (6:54). After each Whitney call, Gisselle:
  - uploads the recording to the client folder
  - pulls out action items
  - assigns them in ClickUp
  - tells the team in Slack
  - drafts a recap email to the client with the action items and the recording attached

  Team members upload their own recordings when they run a call alone. Danielle's LeadLock kickoff is the main case.
- **Overdue invoices** (8:45–12:59):
  - GHL → Payments → all invoices → filter overdue. "Not very frequent."
  - GHL's automatic reminders land in spam or promotions.
  - The fix that works is a **personal email from `hello@` with the invoice link** (GHL "copy link"): "usually that's the push people need."
- **Invalid emails** (9:30–11:28):
  - Opt-in misspellings (".con"). There's a saved "invalid emails" filter in **both** GHL accounts: the main WIA account and LeadLock Pro, which takes no payments.
  - Gisselle corrects the address and re-enrols the contact so they get the materials.
  - Rare, but time-sensitive.
  - **"I really want to check this every day… but because of other things I forget."** The value is reliability, not hours saved. The sheet's comments say the same ("Easy task but I tend to forget").
- **GHL plan:** **Agency SaaS, ~$500/mo, the top tier**, so API access is likely (13:01–13:36).
- **Portal reminder posts** (14:35–18:45):
  - Posts go up in GHL Communities, **one hour before each event**:
    - Google Ads office hours, Thursday **11am CST**, run by Carmen → Google Search Accelerator channel
    - Meta Ads office hours, Thursday afternoon, run by Jacqueline → Meta Ads Accelerator channel
    - **Q&A and Workshop every other week**, run by Whitney → Announcements
  - The Zoom room link is the same every time. The copy is varied by hand each week.
  - **Q&A posts are the most automatable. Workshop posts need Whitney to review the theme and title.**
  - Scheduling: Gisselle scheduled one post via **Social Planner** in April. There were limitations "tagging people or… tagging the event", and she hasn't tried since. **Whether GHL can post through its API is unverified.**
  - **Recap posts were raised and dropped mid-sentence** (17:02). No discovery happened for that row.

**Onboarding lifecycle (full service), as Whitney walked it**
1. **Trigger:** a Dubsado (or GHL, for FFA) signed + paid alert arrives in Gmail.
2. **Gisselle's admin** (21:34–22:59):
   - build the ClickUp onboarding list from **one or two templates**: FFA/LeadLock, and ads management if bought
   - **set due dates by hand**; assignees are fixed by role
   - send the template email: countersigned contract + link to book the ads kickoff + onboarding questionnaire
   - create a **Google Drive folder** and upload assets (sales call recording, contract, questionnaire)
   - create a **client Slack channel** and post a "new client" brief to the team
   - create the **LeadLock sub-account**
3. **Questionnaire** (in Dubsado):
   - yes/no questions (do they have Google Ads, Meta, GTM, GA4)
   - three free-text answers (ideal clients, differentiators)
   - downloaded to Drive and shared in Slack
4. **Ads track** (Whitney → Carmen → Jacqueline):
   - **Ads kickoff call** (Whitney): expectations, education, and **live screen-share to collect access**
   - **Messaging & positioning interview** (Whitney); the transcript goes into the ChatGPT Project
   - **Ad strategy presentation** (Whitney + Carmen): keyword plan approved on the call, location targeting
   - Carmen builds Google Search and sends a **Loom for approval**
   - Meta: client-attraction ads → review → approve → launch, then **conversion**, then **retargeting**, each with its own review loop and "lots of edits"
   - **All campaigns launched = fully onboarded**
5. **LeadLock track** (Danielle → Tina), running in parallel:
   - **LeadLock kickoff** (Danielle): scope a standard build of **inquiry, pre-tour/pre-consultation and post-tour workflows**
   - landing pages for booking; a **privacy-policy page for A2P SMS approval**
   - on the call: create the user, connect email and calendar, buy the phone number, get DNS access
   - afterwards: DNS records, **A2P registration**
   - Tina designs the landing pages, email and text nurture copy, templates and forms
   - client review and edits → internal testing → client testing → **official LeadLock launch call** → LeadLock form goes on the client's website
6. **Handoff between the two tracks** (the one most likely to drop): LeadLock goes live → someone must tell **Carmen and Jacqueline** → **switch the campaign URLs** to the approved LeadLock landing page.
7. **Monthly maintenance:**
   - a recurring 1:1 **30-minute monthly strategy call** with Whitney
   - **monthly reports**
   - strategy-call tweaks feed back into the recap and action-item loop

**Team roster: one owner per function** (25:50). "It is just like one person with set responsibilities." That makes automatic assignment a simple lookup.
| Person | Function |
|---|---|
| Whitney | All client calls: sales, onboarding, strategy |
| Gisselle | All admin |
| Carmen | Google Ads |
| Jacqueline | Meta Ads |
| Ivy | Ads creative design *(new name)* |
| Tina | LeadLock/GHL design: landing pages, email and text nurture copy and design; **monthly reports** |
| Danielle | LeadLock/GHL implementation: kickoff calls, workflows, testing, DNS, A2P *(new name; not Daniela the partner)* |

**Monthly reporting, the biggest find** (33:01 block)
- Tina "dedicat[es] the first few business days of the month to pulling these reports together… It's not automated in any way right now."
- It's built from ad-account screenshots, best-performing-ad screenshots, hand-written "why" context, and a **recorded video walkthrough**.
- **Whitney has already picked the shape of the fix:**
  - She's been trialling **Viktor in their Slack**, connected to LeadLock, Google Ads and Meta Ads, for "an overarching view of everything".
  - She wants "**an executive summary on a monthly basis. I think I saw that in your AI library, actually**… clearer for clients to understand as opposed to like so many screenshots of the metrics."
- The **18–24 hrs/month** figure used in later scoping (`automation_scope.md`) is *inferred* from "a few business days" (3 days × 6–8 hrs). **It wasn't said on this call and must be confirmed.**

## Client signals
- **Whitney guards the high-touch calls and wants to shed everything around them.** "I like being on those calls… they feel really special and taken care of… It's just everything else… that falls on Gisselle" (19:59). This is the right line to automate along: the calls stay human, the admin around them goes.
- **The team is overloaded:** "we're onboarding a lot of clients… I know that the team is inundated" (32:16). Capacity, not just Gisselle's hours, is the constraint.
- **She's candid about ClickUp:** "part of that's probably on me… not how my brain works." A founder-led, Slack-first culture. Anything that needs the team to live in a new tool will fail.
- **Very open to change, again:** "It's not going to hurt my feelings if you say that we need to… everything with this business has just been us figuring it out as we go" (44:07). That's stronger than M01's latitude.
- **Viktor is a live alternative.** She's actively trialling it in Slack, and it's the benchmark for the reporting item. Khushbu's M00 dismissal ("why would you want to pay for Viktor?") didn't stick.
- **She reuses E2M's AI library as a shopping list** ("I think I saw that in your AI library"). The library is working as a demand generator. M01's worry that it gave her "a list, not a system" still applies.
- Gisselle's pain points are **forgetting, not effort**. Daily checks she can't keep up with, and posts she has to remember. Automations that remind her and draft for her fit how she works.

## Scope impact
*Corrected after M04:* WIA's chosen priorities are Content Engine → Paid Media Reporting → Knowledge Base. The table below maps this call to the items in the Sep 15 draft. Of those, **reporting and FF-01 were picked**; the OP items and onboarding were not.
| Item (Sep 15 draft) | Grounded in this call |
|---|---|
| **PM-01/02/03 Paid Media Reporting** (PM-03 = monthly client report pack, the money item) | Tina's first-days-of-month reporting; the executive-summary shape Whitney chose; Viktor as the benchmark. **This answers Daniela's M00 "client reporting" question, and it came from the client, not from E2M.** |
| **FF-01 Maintained Client Knowledge Base** | Turning the per-client ChatGPT Project into a production system. Knowledge base = questionnaire + M&P transcript. **The failure it must prevent is staleness.** |
| **OP-01 overdue digest / OP-02 action-item chase** | The post-call loop (recording → action items → ClickUp → Slack → recap email). The chase has to run **in Slack**, with ClickUp as the record. |
| **OP-03 billing / data-hygiene flags** | Overdue invoices and invalid emails. The automation should **draft the personal `hello@` nudge with the invoice link**, not just raise a flag. |
| **Client Onboarding MVP** | The lifecycle above. The trigger must handle **both Dubsado and GHL (FFA)** alerts. Assignment is a lookup; due dates are the real manual work. Access collection stays out. |

**Design implications**
- **Transcript ingestion must come from Whitney's Zoom first.** Team Fathom accounts are a secondary source, and only after a Fathom Team upgrade. This affects FF-01, OP-02 and the onboarding MVP.
- **The handoff between the LeadLock and ads tracks** (switching the campaign URLs) is a small, high-value rule to add to OP-01/OP-02.
- **Portal reminder posts** (not picked): Q&A and office-hours posts can be templated. Workshop posts need review. The API is unverified.
- Not raised on this call: the content engine (M01), which **became the first priority** (M04); whole-context inbox drafting; landing-page QA.

## Open questions
- **How long does monthly reporting really take, for how many clients, and what do clients actually use?** None of this was asked. The 18–24 hr figure is an inference.
- **What did Whitney get from the Viktor trial**, and what would the E2M reporting item do that Viktor doesn't?
- **Onboarding trigger for FFA:** does GHL's checkout send a Gmail alert like Dubsado's, and in what format? When the migration finishes, a trigger built only on Dubsado alerts will silently miss clients.
- **How are due dates set?** Fixed offsets from the kickoff? This decides whether the onboarding MVP can set them.
- How many clients are onboarding at the same time ("we're onboarding a lot of clients")? How many portal members?
- **Do the office hours get the full recap-post and VAULT treatment, or only Q&As and workshops?** The recap-post row was dropped mid-sentence.
- Can GHL Communities posts be published through the API? Unverified until the `AI@` account joins the portal.
- Carried over: which Gmail automations already auto-tag mail; whether a brand-voice document exists; the $3,499 figure and the audit credit; who owns the build infrastructure.

## E2M performance
**What landed**
- **Minu's "can we pause here" question on the trigger (23:00)** was the best question of the assessment. It surfaced Dubsado and the two-source trigger, and a trigger built on GHL alone would have failed quietly.
- **Letting Whitney narrate the whole lifecycle without interrupting** produced the roster, the handoff between the two tracks, the ChatGPT prototype and the reporting pain. None of these were in the audit sheet.
- The access plan was settled cleanly in the first two minutes. Asking about the GHL plan tier turned "is there an API?" into a concrete answer.
- The question about the resource model led to "one person per function", which makes assignment deterministic.
- Minu's "supportive, not conflicting" stance matched a founder-led, Slack-first team. Whitney then volunteered Slack access and invited process change.
- Asha set expectations honestly: the assessment covered Gisselle's tasks and the blueprint will grow as other team members are interviewed.

**What didn't**
- **The biggest find got no follow-up.** After Whitney described Tina's reporting and the Viktor trial, E2M asked nothing: no hours, no client count, no report contents, no Viktor results. Minu moved on to "quick wins". Every later hours figure for the money item is an inference because of this.
- **The fulfilment ideas promised in M01 never appeared,** and the requirements/access list slipped from M01 to the day after this call (Jainil sent it Sep 3).
- **Still no in-call quantification.** The sheet carries hours for some rows, but none of the post-call loop, the onboarding admin or the reporting was sized.
- The **recap-post row was dropped mid-sentence** and went into the blueprint with almost no discovery.
- Minu's sequencing ("custom solutions, which work on the fulfillment side" come later) pushes the highest-value item, reporting, which *is* fulfilment, to the back. That's the same tension as M01, now with evidence against it.
- Minu's in-person mix-up on office hours suggests the M01 notes weren't re-read before the call.
- **The blueprint is built on two discovery calls.** Nobody who delivers the work (Tina, Carmen, Jacqueline, Danielle) was interviewed, and Daniela hasn't been heard since M00.

## Prep for next meeting (blueprint review, ~Sep 10)
- **Answer the three open framing questions directly:**
  - **time back** (M00): be honest that the sheet's hours are small; lead with turnover-proofing, onboarding throughput and reporting
  - **"how is it all connected"** (M01): one spine, not a catalogue
  - **what to pick first** (M02): Tier 1 items must be pickable
- **Give reporting a prominent place**, and state plainly how it compares to Viktor. *(After M04: Whitney made it her second priority, behind the content engine.)*
- Show the onboarding trigger handles **Dubsado + GHL (FFA)** and that access collection stays manual.
- Keep every client-facing output behind human review. Show where the review happens (Slack / one place, not many tabs).
- **Confirm the reporting numbers** (hours, clients) before quoting ROI. Ideally ask Tina directly.
- Invite **Daniela** to the blueprint review. She raised reporting on day one and is a co-decision-maker.
- Commercials go to Asha's 15-minute sync: the $3,499 figure, the audit credit, the plan options.

## Hindsight
*Provisional; confirm as later meetings are analysed.*
- *Corrected after M04.* WIA's three priorities are **Marketing & Content Engine → Paid Media Reporting (4 wks) → Maintained Client Knowledge Base**, from a Sep 15 kickoff (`WIA-Automation-Timeline/`). Reporting is one of them, as this call pointed to. The Sep 15 spreadsheet's "Reporting / Ops / KB" version was superseded.
- Internal scoping after this call (`automation_scope.md`) found the sheet's hours add up to only **18.1 hrs/month, of which 6.0 were client-attested**. Hence "the hours case is arithmetically dead". That's the honest answer to M00's time-back question, and why the case rests on turnover-proofing, throughput and reporting.

---
*Transcript notes: speaker labels are scrambled throughout. Most "Whitney" lines between 3:07–4:08 are Minu's questions, and "We don't need to over-engineer it" (18:42) is Minu. Mis-hearings: "lead block" / "LeapBock" / "LeapBlock" / "Leadlog" = LeadLock; "DovesAuto" / "Dipsado" = Dubsado; "full-proof follow-up advantage" = Foolproof Follow-Up Advantage; "H2P" = A2P; "Carming" = Carmen; "Med-Ads" = Meta Ads; "JHL" = GHL; "leave-up kickoff" = LeadLock kickoff; "grant" (27:17) = probably "form"; "custom GPD" = custom GPT.*
