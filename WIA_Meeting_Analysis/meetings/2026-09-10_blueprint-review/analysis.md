# Meeting 03: Blueprint review

**Date:** 2026-09-10 (Thu) · **Duration:** 45 min · **Source:** Fathom transcript → [source.md](source.md)
**WIA:** Whitney Hodges (founder), Gisselle Jimenez (EA / ops). *Daniela absent, for the third call in a row. Whitney reviews the blueprint with her on Fri Sep 11.*
**E2M:** Minu Bhatt (presented the blueprint and the prototype), Asha Kumar (commercials). Jainil not audible.

## TL;DR
E2M presented the **AI Blueprint**: **29 automations in 8 workflows across 3 phases**.
- Phase 1, "Stop the Leaks": admin efficiency
- Phase 2, "Free the Founder": reporting and content
- Phase 3, "Own the Fulfillment": knowledge base, first-draft copy, landing-page QA

Alongside it came a password-protected **Command Center prototype**, all on demo data. It had an **AI Operations Hub** walkthrough and three consoles:
- signed-and-paid onboarding
- meeting → action items → ClickUp
- office-hours roll call

**Whitney gave the strongest buying signal so far:** *"we probably will go the route of Apollo… a continued engagement beyond that… to just keep building."* But she was "still trying to take it all in", and Gisselle was "trying to keep up".

Whitney's questions have changed since M00. There she asked how much time they'd get back. Here she asked:
- **Will all of this be built in 3 months?** No. Two automations are built in parallel; quick wins take ~2 weeks, bigger ones 3–5.
- **Who owns it?** WIA. The repo and the Railway hosting are tied to `AI@`.
- **How do we maintain it without your team?** Handover docs, Looms and maintenance plans.

**The commercials were finally stated in full:** the audit cost $499 and is credited, so Apollo is $9,000 upfront, or $3,000 + $3,499 + $3,499 monthly. The ask is to **pick two automations and a plan**; Whitney will reply next week.

**Monthly reporting, the item Whitney had already shaped in M02, was called "a key one… high priority" but was not demoed.** *(Correction after M04: she then picked the content engine first, with reporting second.)*

## Decisions
- **How the pick works.** WIA picks **two automations** to start, plus a plan. E2M then:
  - runs a technical feasibility check
  - sends a detailed timeline and milestone chart
  - sends a **dedicated SOW** covering timeline, development, testing and the feedback loop, before any execution (35:06, 35:55)
- **Ownership.** It's a custom tool built only for WIA. The **code and repo are tied to `AI@weddingindustryads.com`**, it's **hosted on Railway** with the connectors set up, and it's handed over. If the relationship ends, WIA keeps it: "Yeah, absolutely" (8:44–9:28). *This replaces M00's "hosted on your AWS".*
- **ClickUp stays the system of record for roughly the first quarter.** After that, E2M will review whether to move into the custom tool (20:06–20:29). Whitney is the one who suggested retiring it.
- **Everything client-facing stays behind approval.** "Nothing stands without an approval" (~3:00–8:29 block). The roll-call reminders will get a **configurable sender** (23:55).
- **"Case study extraction" is renamed "client success stories".** The format is a story (problem → our work → result), with data as a supplement (27:24–28:15).
- **Pricing** (39:28). The audit is paid ($499) and credited.
  - **Upfront:** $9,499 − $499 = **$9,000**
  - **Monthly:** $3,499 × 3 with the credit on month 1 = $3,000 + $3,499 + $3,499 = **$9,998**
  - Paying upfront saves $998. The card is charged once WIA has picked.
- **After Apollo** (41:18–42:53), WIA can choose:
  - **full-time strategist:** two automations in parallel, two developers
  - **part-time strategist:** one major automation plus tweaks, one developer, a call every two weeks, about half the speed
  - maintenance-only hours
  - custom resourcing, e.g. "a team of three for three months" to finish "60 or 80%" of what was shown

  Minu and a core developer stay on in every option.

## Commitments
| Owner | Commitment | Due | Status |
|-------|------------|-----|--------|
| WIA (Whitney) | Review with Daniela (Fri Sep 11), then **pick two automations and a plan** | Asha: "tomorrow or Monday"; Whitney: "next week" | Open |
| E2M (Asha) | Share the blueprint link via the group | Sep 10 | Presumably done |
| E2M (Minu) | Send the Command Center credentials via LastPass | After the call | Unknown |
| E2M (Minu) | After the pick: technical feasibility check, then a detailed timeline and milestone chart | After pick | Open |
| E2M (Asha) | A **dedicated SOW** with timeline, development, testing and feedback, before execution | Before execution | Open |
| E2M (Asha) | Charge the card and line up the team once the pick is in | On pick | Open |
| E2M | At any pause or at the end: **handover docs, technical docs and Loom walkthroughs**; maintenance plans on offer | At pause / end | Open |
| E2M | Configurable sender for roll-call reminders (team member vs `hello@`) | If MP-01 is picked | Open |
| E2M | Role-based logins if needed | Build | Open |
| E2M (Asha) | Heads-up: slow replies **Fri Sep 18** (team event); working Saturday | Sep 18 | Info |

**Commitments from earlier meetings, checked against this call**
- **M00: what the audit would deliver.** **Partly met.**
  - Clickable prototype: ✔
  - Maintenance: ✔, but only once Whitney asked
  - How much of Gisselle's role can be replicated: the document estimates her workload but doesn't give a share that can be replicated. Not discussed.
  - **Output accuracy: not covered**
  - **API / running cost: not covered.** The governance section only says "cost controls", and the Railway cost wasn't stated.
- **M00: audit credit.** ✔ Confirmed ($499).
- **M01: fulfilment ideas.** ✔ Delivered at last, as Phase 3 and the content engine.
- **M02, WIA side:**
  - `AI@` created ✔ (39:28)
  - office-hours transcript sent ✔ (the roll-call demo used "a transcript sent over to us… a Google Ads one")
  - blueprint slot confirmed ✔
- **M02, E2M side:**
  - ClickUp checklist reviewed ✔. "We've replicated everything that we saw in ClickUp." The templates were pulled through the API by Sep 8 (`.clickup-snapshot/`).
  - Asha's 15-minute sync ✔, folded into this call as the pricing section
  - **GHL Communities posting check: not reported**

## New facts & corrections
**The blueprint as presented**
- **29 automations · 8 workflows · 3 phases** (15 / 11 / 3 items).
  - Each automation card shows the current process, the proposed build, what E2M needs from WIA, and the expected outcome.
  - Supporting views:
    - an **impact vs effort matrix** that marks the quick wins
    - an **automation graph** showing dependencies, e.g. workspace provisioning comes before the welcome email
    - an **impact tab** with hours
    - a human-review map
    - API access dependencies
    - guardrails (security, cost controls, role-based policies)
    - an activation pipeline
- **The 8 workflows:**
  1. Operations & Task Orchestration
  2. Member Portal & Community: roll call, reminder posts, recap post + Canva banner
  3. Meetings & Knowledge Capture
  4. Client Onboarding: signed-and-paid trigger, welcome emails, asset intake, workspace provisioning, cross-track launch gate
  5. Marketing & Content Engine: idea queue, reel scripts, multi-format repurposing, case study → success story
  6. Client Communications: drafts in Whitney's voice
  7. Paid Media Reporting: ads performance watch, monthly client report pack
  8. Fulfillment & Client Delivery: maintained knowledge base, creative brief & first-draft copy, landing-page QA & conversion check
- **Six items were late additions.** The Sep 9 v0 (`WIA-Blueprint-v0-data.json`) had 23 items, 2 phases and 7 departments. The presented version added ON-04 (workspace provisioning), ON-05 (cross-track launch gate), **PM-03 (monthly client report pack)** and **FF-01/02/03**. So **the reporting money item and the whole fulfilment phase were added in the final day.**
- **The indicative timeline for all 29 runs Oct 2026 → Jun 2027,** roughly nine months (`frontend/src/data/timeline.ts`; marked "indicative, not agreed"). It wasn't shown on the call. In that sequence PM-03 sits in Feb–Mar 2027 and FF-01 in Apr–May 2027.
- **Hours were shown but not discussed.** Minu pointed at "the average hours in each phase that we hope to recover" and moved on. v0's wording:
  - "~18 hrs/month **verified** (one role)"
  - "Phase 1 targets roughly 12 verified hours per month"
  - "estimated full load 45–70 hrs/month"

  Internal scoping (`automation_scope.md`) found only **6.0 of the 18.1 derived hours are client-attested**, so "verified" overstates it. Check the version Daniela is reading.

**The Command Center prototype** (demo data only; password-protected; credentials via LastPass)
- **AI Operations Hub**, pitched as "a one-stop shop for your Gmail, your ClickUp, your Fathom, your HighLevel". Its sections:
  - **Overview:** today's queue, items ready for review, team pulse, sources.
  - **Inbox "lanes"** that *replicate* the star/label system (waiting on client, sales follow-up…), with drafts "in the tone" Whitney uses. Approve → it sends. (CC-01/02)
  - **Meeting → execution packs:** decisions, client commitments with their source, risks, and tasks that go to ClickUp on approval. Everything is filed to a **ledger** for later automations to use. (MK-01)
  - **Ops Watch:** things assigned in Slack with "no acknowledgement or reply" (OP-02), plus a finance tab for invoices due (OP-03).
  - **Client hub:** questions about a client's history, answered with sources ("Sep 2… four commitments were made, three are still outstanding"). Minu called it "the most flexible" (FF-01-shaped).
  - **Quick questions** and **growth signals**: FAQ-style ideal answers, "quality over quantity" positioning, teaching moments turned into content (MC-01).
  - **Content from transcripts:** reel scripts, carousels, emails, captions, success stories. Minu called this part "a tiny bit aspirational". (MC-02…04)
  - **Source coverage / capability register:** Gmail is **drafts only**; Dubsado signed/paid is detected by **email parsing as a fallback**.
  - **The hub isn't one automation.** Each section in the side menu is its own automation. "Pick two to start" and grow it from there.
- **ON-01 signed-and-paid onboarding** (18:01 block):
  - A Dubsado alert is mapped to the service bought and kicks off the next steps (welcome email, call bookings).
  - It builds the **ClickUp template tasks from a start date**, each with an owner and due date. Tasks that don't apply can be unticked, then everything is approved in one click.
  - Minu narrated it as "all these template tasks get created in ClickUp". **Per the build scope, the prototype stops at approval and writes nothing to ClickUp.**
- **MK-01 meeting → action items → ClickUp:** upload a transcript → match against the ledger → action items → ClickUp + ledger + board view. Called "a quick win".
- **MP-01 office-hours roll call:**
  - Upload a transcript → the AI works out which session it was → **"how many non-staff speakers were there, who spoke on the call, who was present or not"** (20:29 block).
  - Someone can manually add people the AI missed.
  - It tracks 2- and 4-week misses, drafts a DM or email, and sends.

**Answers to standing questions**
- **$3,499 (from M00)** is the Apollo monthly instalment. **The audit cost $499** and is credited.
- **Hosting** is Railway, with the repo and account tied to `AI@`. **The running cost was never stated.**
- **Apollo** = a full-time strategist, **two automations in parallel, two developers**.

**Other**
- Minu used the idea that WIA is "planning to scale up in… quarter one of 2027" to argue for the knowledge base (30:12). **Whitney didn't confirm it.**
- E2M is at a company event on **Fri Sep 18**. "Brent" (probably Kevin) will be in India.

## Client signals
- **She's buying.** "We probably will go the route of Apollo… continued engagement beyond that" (36:48). The M00 audit downsell has converted.
- **She's buying on vision and ownership, not on hours.** Her questions moved from M00's "how much time back?" to what gets built in 3 months (34:16), how many to pick, who owns it and what runs it (8:29), and how to maintain it. **She never asked about hours.**
- **She wants to be self-sufficient.** This is the M00 motive again: she doesn't want to swap dependence on contractors for dependence on E2M. "We don't have your team, right?… how to fix it if something breaks? How to add on to it?" (36:48). Handover and maintainability are both selling points and obligations.
- **She wants fewer tools.** "Does ClickUp just become obsolete?" (20:06). This matches M01's "one place" and M02's "never fully adopted ClickUp".
- **Her marketing is storytelling:** "the client came to us and had this problem… now here's where they are" (27:54).
- **Reporting pull is still strong.** Her end goal for the client hub is "connected to the data… inside their Google Ads accounts, their Meta Ads accounts, their GHL accounts" (28:16). That's the same direction as the Viktor trial and the executive summary in M02.
- **Signs of overwhelm:**
  - Whitney: "still kind of like trying to take it all in."
  - Gisselle: "I would just be curious, like trying to keep up, you know, with everything… we need to do" (33:35). She's the person whose work is being automated and who will be approving the drafts, so the adoption risk is visible here.
- **The decision is shared.** "I definitely want to share it with Daniela." Daniela has missed three calls in a row, so she'll read a 29-item blueprint cold.

## Scope impact
- **Minu's spoken recommendations didn't match the blueprint's written order.** On the call he pointed to:
  - **MK-01** ("a quick win") and onboarding
  - **PM-03**: "a key one… high priority… a good candidate for us to start"
  - **FF-01**: "an excellent candidate… the first precursor for any automation downstream"

  The written blueprint puts PM-03 in Phase 2 and FF-01 in Phase 3. **Daniela will only see the written order.**
- **The two-at-a-time model caps what three months can deliver.** With two builds in parallel and each taking 2–5 weeks, 3 months realistically fits **about 4–8 automations**. The prototype showed three consoles plus a hub that is itself about 8 automations. Whitney's 34:16 question shows she took the demo as the 3-month deliverable.
- **Design risks surfaced in the demo:**
  1. **Roll call reads attendance from who *spoke*.** A member who attends and just listens gets marked absent and then nudged, which is the client-experience harm WIA has ruled out. The Sep 3 build pack said the capture was untested and that the fallback is **Zoom participant reports**. Nobody said that on the call.
  2. **Roll-call reminder channel.** The prototype emails from `hello@`. M01's actual process is a **portal DM from the session host** at 2 weeks and an email at 4. GHL Communities posting and DMs through the API are still unverified.
  3. **Onboarding:**
     - It dates everything from **a single kickoff anchor**. A client who buys both offers gets one track mis-dated. Ridgefield's LeadLock and ads kickoffs were 34 days apart.
     - It watches **Dubsado alerts only**, but FFA already runs on GHL (M02).
     - It **doesn't write to ClickUp** yet.
  4. **The inbox lanes copy the 7-marker star system** even though Whitney twice invited a redesign (M01, M02).
  5. **Ops Watch needs a definition of "acknowledged"**: an emoji, a reply, or a ClickUp status? OP-02 can't be built without it.
  6. **The client hub / knowledge base needs a rule for conflicts:** which wins when a call contradicts an approved document. This is an internal gate for FF-01.

## Planned vs presented
The Sep 3 plan (`SEPT10-MVP-BUILD-PACK.md`) scripted a different review:
- five MVPs on a shared spine: handoff, live page check, first-draft copy, **executive summary instead of screenshots**, voice note → content
- a close on the "brain" file and "receipts" (a run ledger plus a 30-day backtest), billed as "the first real answer to the question asked on Aug 11"
- three recommended **process deletions**: seven stars → three, merge the two roll-call sheets, stop hand-building ChatGPT Projects
- an on-the-record **"what we did not build, and why"**, including "roll call: the capture needs one twenty-minute test we could not run… the answer is Zoom participant reports… we refused to fake it"

What was presented instead: the blueprint, the ops hub, and three consoles (ON-01, MP-01, MK-01). **Not on the call:**
- the reporting demo
- the content demo
- an answer to the Aug 11 time-back question
- the process deletions
- the "what we didn't build" disclosures

Plans change for good reasons. But **the two disclosures that were dropped are the ones that manage expectations**, and those gaps now show up in the design risks above.

## Open questions
- **Which two automations, and which plan? What does Daniela think?**
- **What exactly is WIA buying for 3 months?** The SOW has to list which of the 29 are in and which are out.
- **Running cost** (Railway + model/API spend): how much, and who pays? M00 promised "$20–30" for hosting.
- **Output accuracy targets and review gates per automation.** Promised in M00, never presented.
- **Reporting:** Tina's actual hours, the number of clients, what's in the reports, and how it compares to Viktor. All still unasked, and PM-03 wasn't demoed.
- **What counts as "acknowledged"** for Ops Watch / OP-02?
- **Roll call:** attendance from participants or from speakers? Which sender and channel for reminders (portal DM or email)?
- **Role-based access:** who logs in, and what does each person see? How much review load lands on Gisselle?
- **Price in the SOW:** Asha quoted "$3,166 per month" for the upfront option. That's $9,499 ÷ 3 *before* the credit. With the credit it's **$3,000/month ($9,000)**.
- **Template residue:** v0's governance section says "Collect **Explore Media** feedback after two to four weeks", another client's name. Check the version Whitney and Daniela have.
- Is WIA actually planning to scale in Q1 2027, as Minu assumed?

## E2M performance
**What landed**
- **M00's promise of a clickable prototype was kept.** It was built in WIA's own language: their star lanes, the Dubsado trigger, 2- and 4-week flags, the Monday team meeting, a real Google Ads office-hours transcript, "Sep 2… three outstanding". It showed E2M had listened.
- **The automation graph and the one-hub framing answer M01's "how is it all connected?"** The impact/effort matrix answers "what do we start with?".
- The **ownership answer was clean and specific**: the repo, Railway and `AI@` are WIA's, and they keep them if the relationship ends. Maintenance and handover were answered concretely when she asked.
- **The expectation reset was honest.** When Whitney asked whether everything would be built in 3 months, Asha said the prototypes are "skeletons" and the build goes two at a time.
- **Pricing was transparent**, including the audit credit and flexible resourcing options.
- Minu's spoken steer towards PM-03 and FF-01 went with what the client had said she wanted, even though the written blueprint sequences them late.
- Renaming "case study" to "success story" showed E2M had reviewed a real recording.

**What didn't**
- **Too much, too fast.** 29 automations, 8 workflows, a hub with about 8 sections and three consoles, all in ~33 minutes. "I know I'm going a little fast." The client came away "still trying to take it all in" and "trying to keep up". For a founder who is new to AI, the graph helps, but the volume works against it.
- **A high-priority item was deferred.** Monthly reporting was "hoping to review once we got into the conversation about reporting". It's the item she had already shaped (an executive summary), the one competing with Viktor, and the one tied to the largest known cost. Viktor wasn't mentioned at all.
- **The M00 promises went unspoken.** The time-back answer, accuracy and running cost weren't covered. The hours sat in a tab. Daniela, the skeptic, will read them cold, with "verified" wording that overstates what was attested.
- **The roll-call demo implied it works when the capture is untested.** The silent-attendee flaw means the prototype would nudge clients who attended.
- **The onboarding demo was narrated past what it does.** "Tasks get created in ClickUp" when the prototype stops at approval. And it dates both tracks from a single anchor.
- **The inbox copies the star system** instead of taking the simplification she invited twice.
- **A price slip:** $3,166/month for the upfront option should be $3,000.
- **Daniela wasn't brought in.** She's missed three calls in a row, and E2M didn't offer her a walkthrough.
- **Mixed signals in the written document:** it sequences reporting and the knowledge base late while Minu pitched them as the place to start.

## Prep for next meeting (decision / kickoff)
- **Confirm the pick with both founders.** Offer **Daniela a 20-minute walkthrough**; she hasn't been on a call since Aug 11.
- **Put in writing (the SOW):**
  - which of the 29 are in the 3 months and which aren't
  - running costs and who pays them
  - accuracy targets and review gates
  - the handover package
  - the correct price: **$9,000 upfront or $9,998 monthly**
- **Settle the gating facts for each pick before building:**
  - **PM:** Tina's hours, client count, report contents, Viktor trial results
  - **OP-02:** what counts as "acknowledged"
  - **FF-01:** the conflict rule
  - **MP-01:** the attendance test
  - **ON-01/02:** the FFA/GHL trigger, and separate anchors for the two kickoffs
- Decide whether the inbox should **copy or simplify** the star system.
- **Scrub the shared blueprint** for template residue.
- Tell the client plainly what the prototype does *not* do yet (no ClickUp write, untested attendance capture) before it's quoted back to E2M.

## Hindsight
*Corrected after M04. The earlier version of this section came from project memory and the Sep 15 spreadsheet, both of which were out of date.*
- WIA picked **three priorities, not two**: **Marketing & Content Engine (first) → Paid Media Reporting → Maintained Client Knowledge Base** (M04 call; `WIA-Automation-Timeline/`, kickoff Sep 15).
- All three were **Phase 2–3 items in the written blueprint**: MC-01…04 and PM-03 in Phase 2, FF-01 in Phase 3. So the pick **reversed the blueprint's efficiency-first order**.
- **None of the three consoles demoed (ON-01, MP-01, MK-01) was picked.** Operations & Task Orchestration isn't a stream; parts of it were folded into knowledge-base sub-items.
- Everything picked traces to something the founders raised themselves:
  - content: Whitney in M01, "we need more leads, we need more sales"
  - reporting: Daniela in M00, Whitney in M02
  - the "agency brain": M00

---
*Transcript notes: speaker labels are scrambled again. Most "Whitney" lines at 2:02, 11:20, 14:43, 15:16, 16:21, 17:55, 29:36, 30:12 and 31:19–32:16 are Minu, and 33:05/33:44 mix up Whitney and Gisselle. Mis-hearings:*
- *"your Fallon" (~7:30) = Fathom, not the departed account manager*
- *"Antacid intake" = asset intake; "current coding" = client onboarding; "check test assignment" = checklist assignment*
- *"EOCs" / "MPP" = POCs / MVP; "Dubsar" = Dubsado; "co-high-level specialist" = GoHighLevel specialist; "kick-up" = ClickUp*
- *"Office As role call" = office-hours roll call; "custom booth" = custom tool; "opposite" = obsolete; "rule-by policies" = role-based policies*
- *"20 but nine" = 29; "re-scripts" = reel scripts; "next page Q&A" = landing-page QA; "Copolo" = Apollo*
- *"Brent and Khushma" = probably Kevin and Khushbu (M00); "Rizal" = Gisselle*
