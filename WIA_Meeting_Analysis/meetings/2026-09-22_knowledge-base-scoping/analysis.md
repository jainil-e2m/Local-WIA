# Meeting 05: Knowledge base scoping (weekly sync, now on Tuesdays)

**Date:** 2026-09-22 (Tue) · **Duration:** 53 min · **Source:** Fathom transcript → [source.md](source.md)
**WIA:** Whitney Hodges (founder), Gisselle Jimenez (EA / ops, joined ~1 min in). *Daniela absent (fifth call in a row).*
**E2M:** Asha Kumar (opened), Minu Bhatt (led), **Nandini Vithlani** (lead AI executor, new), Jainil (associate AI executor, introduced)

## TL;DR
E2M introduced the delivery team (Nandini as lead, Jainil as associate) and walked through the week-by-week timeline.
- **Content engine work started Sep 21.**
- The **knowledge base is "queued for November"**, but its backend starts early. The reason given: **a Q1 2027 scale-up that Minu says Whitney mentioned.** Whitney has never said it on any recorded call; she didn't object here either.

Two access facts came first:
- **Zoom.** Gisselle showed that **only recordings are deleted from Zoom** after filing to Drive. **Transcripts and summaries stay in Zoom**, now visible through a role she created for the AI account. That contradicts the "client calls are video-only, speech-to-text blocker" finding, which is still written into `frontend/Content_Atelier.md` as of Sep 23.
- **`hello@`.** To reach Whitney's calendar and ChatGPT, **E2M asked for the `hello@` password and had an E2M (+91) phone added as a second 2FA method on the company's main Google account.** It was done live on the call.

The rest was **knowledge base discovery**, the best discovery session so far. Whitney wants the knowledge base to:
- know every conversation (sales → onboarding → strategy) plus each client's live **Google, Meta, GHL (and one client's Shopify)** data and sentiment
- above all, **prep her for every call**
- give the team a **dashboard** of open action items, weekly focus, call agendas and account health

**Viktor is already doing a lot of this in Slack:**
- daily call prep from her calendar
- per-account Q&A
- flagging opportunities
- "open loops"
- a Monday 30-vs-30-day green/amber/red snapshot

But it's verbose, doesn't understand call types, is buried in threads, and its fixes lag 1–1.5 weeks. Her verdict on Viktor: **"a band-aid solution for now… ultimately I want it to be something that we own."**

## Decisions
- **Delivery team:** Nandini Vithlani (lead AI executor) and Jainil (associate AI executor). They'll contact the client directly on Slack (1:37–1:51).
- **Timeline.** The content engine has been in execution since Sep 21. The knowledge base is queued for November, with its **backend starting early**. The progress link is the central status reference (1:51 block).
- **Access (done live, 9:41–14:22).** Gisselle shares the `hello@` password via LastPass. An **E2M +91 number is added as a secondary 2FA method** on `hello@`. E2M tests it the next day. "Once that is ready, you can then reset your password."
- **Fathom team account:** deferred until E2M has reviewed the Zoom settings. Minu: a team account "makes everything easier" for API connections (15:10–15:16).
- **Knowledge base source-of-truth rule** (49:00–49:46). **What's said in a meeting beats a ClickUp due date**, and answers **cite where the information came from**. This settles part of FF-01's gating decision. *Still open: an approved document vs a later call.*
- **The knowledge base is built in phases, in parallel with the other streams.** **Phase 1 = client call prep plus the most important opportunities.** Then sentiment, account health and to-do lists (49:46 block).
- **Users:** Whitney **and the team**. No client is excluded (22:37, 45:11).
- **Find calls through the calendar:** scan Whitney's calendar to find the day's calls, then fetch their source material. It was Whitney's idea; Minu: "exactly what we were thinking" (9:20–9:41).
- **Not decided: which stream comes after the content engine.** Asha opened with "the client knowledge base or the paid media… reporting, which automation to pick up next". The call only scoped the knowledge base. Whitney called reporting "the third phase of this project" (45:45). The timeline app still shows reporting *before* the knowledge base.

## Access & security
**What happened.** `hello@weddingindustryads.com` is the company inbox that carries all client communication (M01, M02), the Google account behind the calendar and Drive, and the shared ChatGPT login (M02, M04). E2M now holds its password, and an E2M-controlled phone can pass its 2-step verification.

**Why it matters:**
- It **reverses the M02 access design**. `AI@` was created so E2M's access would be *scoped and revocable* without touching the main account.
- **"Reset your password" doesn't undo it.** The added phone stays on 2-step verification until someone removes it, and existing sessions and grants survive a password change. *Correction after reviewing the requirements doc:* the written request (~Sep 15–17) did ask for `hello@` **ChatGPT** access, "to review existing chat history", via LastPass. **This call widened it**: the calendar was added verbally, and the 2FA phone gives the whole Google account. Nobody set an end date.

**Lighter-touch routes existed** for each stated need:
- **Calendar:** share Whitney's calendar with `AI@` ("see all event details")
- **Email:** Gmail delegation to `AI@`, if it's needed
- **ChatGPT history:** ChatGPT's own data export, run from `hello@`
- **Zoom:** already covered by Gisselle's role

**What to put in writing now:**
- scope: which services E2M signs into as `hello@`
- who holds the +91 number
- an end date
- the removal steps: remove the 2FA phone, rotate the password, sign out all sessions, review third-party access

This belongs in the SOW that still hasn't been sent. *This is a governance observation; nothing suggests misuse.*

## Commitments
| Owner | Commitment | Due | Status |
|-------|------------|-----|--------|
| WIA (Gisselle) | Share the `hello@` password via LastPass | Sep 22–23 | Open (presumed done) |
| E2M (Minu / Nandini) | Test `hello@` access once the 2FA delay clears; confirm or flag problems | Sep 23 | Open |
| E2M | Review the Zoom settings, then recommend on a Fathom team account and whether Whitney should use Fathom | After access | Open |
| E2M | "Once we have all the sources locked down, we'll come back with recommendations" on what the knowledge base can do | After sources | Open |
| E2M | Knowledge base functional requirements in phases (Phase 1: call prep + opportunities) | Before build | Open |
| WIA (Gisselle / Danielle) | LeadLock kickoff calls: widen access, or have Danielle use a team Fathom, if needed | TBD | Open |
| E2M | Progress link available centrally | — | Done (timeline app) |
| **E2M + WIA** | **Written scope, end date and revocation steps for the `hello@` access** | Now | **Not raised. Recommended** |

**Commitments from earlier meetings, checked against this call**
- **M04: "an update on the marketing and the content automation, like what we have done so far".** **Partly.** The timeline was shown and "work has started from the 21st", but no output. After a week of building, one real candidate queue would have made the point.
- **M04: the new Tue/Thu slot.** ✔ This call was on a Tuesday.
- **M04: inputs.** Minu: "We've received all of the other information and the knowledge-based documents." But the Sep 21–23 access notes still list **GHL and Instagram as missing**. Reconcile.
- **Not revisited from M04:** the card, the CTA map, the flag mechanism, where drafts live, client consent, running cost.
- **M03: the SOW.** Still not mentioned.
- **M00: "daily progress updates in your project-management tool."** Replaced in practice by the timeline progress link and Slack.

## New facts & corrections
**Correction to M04's hindsight: the transcript "blocker" may largely not exist.** Gisselle (7:07):
- She **created a Zoom role** so the AI account can see Admin → **"all the recordings and transcripts, as well as summaries"**.
- Client calls are filed to **Drive, in client folders grouped by offer** (e.g. Elevate). Each client has a **"call recordings and transcripts" folder**. The *recording* is then deleted from Zoom to save storage.
- **"You probably won't find client recordings, but I don't delete summaries or transcripts."** Transcripts should still be in Zoom.
- Zoom still holds Whitney's **calls with leads**, and **workshop transcripts** can be found by searching "workshop".

`frontend/Content_Atelier.md` §8 (last edited Sep 23) still says client meetings reach E2M "as video… nothing beside them" and that speech-to-text blocks the strongest material. **Check Zoom Admin → Transcripts for the last three months of client calls before provisioning speech-to-text.** Speech-to-text may only be needed for the gaps:
- office hours recorded in Fathom
- LeadLock kickoffs (Danielle's; access is limited)
- older or never-transcribed calls

**How recordings are handled (Whitney, 5:24):** after a client call, Gisselle logs into Zoom, downloads the transcript and video, and uploads both to the client's Drive folder. Those assets go into ChatGPT when content is wanted.

**Access.** `AI@` hits 2FA for ChatGPT and for Whitney's calendar. Hence the `hello@` route (see *Access & security*). Nandini: with `hello@`, "we will be able to log in to ChatGPT and all other accounts" (15:35).

**What the knowledge base should do** (Whitney, 16:48–19:39, 45:45)
- **Know everything:** onboarding materials and every conversation, from sales calls through onboarding calls to ongoing strategy calls.
- **See performance:** Google Ads, Meta Ads, GHL where the client uses it, and **Shopify** for one non-GHL client. "Lead generation, first of all."
- **Read sentiment** from what clients raise by email or on calls.
- **The top use case is prep before every call:** where things stand, what to share on performance, the opportunities, what we need from the client. After the call: the team's action items.
- **Be proactive** in the way Viktor is: "leads have been down on Google the past week… conversion tracking is no longer working… here's why."
- **Be usable by the team**, e.g. Carmen asking "recap everything outstanding on this account", and **checking afterwards that the fix actually stuck**.
- **A dashboard across all clients** ("my ideal"). On it:
  - open action items pulled from Slack, team meetings and chats, "not… going to a spot and sticking there"
  - a **weekly focus per client**
  - a **call prep / agenda**
  - **account health** from both satisfaction and performance
- **Feed the content engine:** the whole history from first sales call to now, as "a much more powerful success story… than… one call in isolation."

**Viktor, the tool already doing much of this** (18:37–35:54, 45:45). *Full categorized inventory, plus research on the product ([viktor.com](https://viktor.com/)): [`viktor_at_wia.md`](../../viktor_at_wia.md)*
- **What it's connected to:**
  - the agency's LeadLock, **added by hand to each client's LeadLock** sub-account
  - Meta, added by hand to each client's ad account
  - Google, through the **manager (MCC) account**
  - Whitney's email and calendar only
  - ClickUp and Zoom
  - *not* Fathom
- **What it does:**
  - a **daily calendar scan → call prep** for client and sales calls, with conversational follow-up
  - per-client performance Q&A
  - proactive flags ("zero leads over the past three days")
  - Carmen's per-account recaps, with a check that each fix stuck
  - **a pre-interview gap analysis** before the messaging & positioning call: the onboarding questionnaire against the client's website, "what hasn't actually been answered"
  - briefing **Danielle** for LeadLock kickoffs, but only "when I remember to"
  - **daily Slack "open loops"**: things asked of the team with no response, and asks to Whitney she hasn't answered
  - a **Monday ClickUp overdue digest** to Gisselle. That was "a lot… even old ClickUp tasks", so she uses her own ClickUp filter instead.
  - a **Monday snapshot of all clients**: last 30 days against the prior 30, **green/yellow/red**, before the Google and Meta meetings
  - **SOPs** when it finds a systemic fault (Google Ads **UTM parameters built wrong**; how **GHL forms** were set up)
- **What's wrong with it:**
  - **"very verbose"**
  - recommends unnecessary actions because it **doesn't understand the call type** (ads kickoff vs messaging & positioning vs strategy)
  - **everything lives in Slack threads**, so she re-pings it for status
  - findings aren't escalated or documented, so **fixes lag 1–1.5 weeks**
- Whitney: she could have Viktor build dashboards, but "because we're doing this with you guys and ultimately I want it to be something that we own… he's just kind of like a band-aid solution for now."

**Onboarding and fulfilment detail**
- **Order:** ads kickoff (introductions, expectations, connecting ad accounts) → **messaging & positioning interview** (after the onboarding questionnaire) (25:32).
- **After the interview:** Gisselle feeds ChatGPT the transcript, questionnaire and website/marketing to fill a **Q&A document**. That goes into the client's ChatGPT Project, which drafts landing-page copy, initial ad copy, ad strategy and **email nurture sequences**. The nurture sequences are new since M02.
- **LeadLock kickoff calls** sit with Danielle. WIA's access is "limited" until she uploads them (30:19).
- **Strain is already showing:** "missed due dates or things… getting pushed out". Two clients recently had **ads kickoffs in the same week**; normally they're spaced at least a week apart. "Things weren't… as tight as… I want them to be" (40:00 block).

**Client health**
- **Satisfaction signals:**
  - email and calls (Whitney is on every full-service call)
  - **feedback surveys at different stages**
  - performance: lead volume, cost per lead, ad leads turning into **booked clients** in LeadLock
- **Escalations have "no… way that we're keeping track"**. They're handled case by case, and everything comes through Whitney.
- **LeadLock support:** a ticket form goes to Danielle (`support@leadlockpro.com`). A GHL pipeline for it was started once but nobody watches it.

**Monday meetings:** Google Ads (Whitney + Carmen); Meta Ads (Whitney + Jacqueline + Carmen, sometimes Ivy); a general team meeting (45:45).

**"What breaks first with an influx of clients?"** (40:00)
1. **Follow-through on ongoing maintenance.** Viktor's fixes wait 1–1.5 weeks. She suggests ClickUp tasks with due dates the team is held to.
2. **Monthly reporting.** "With every new client that gets added on, that's just… more and more hours."
3. **Onboarding.** Missed deadlines; she wants more reminders.

## Client signals
- **Trust is very high.** She handed over the main account and a 2FA method in minutes, without asking what it's for. That trust is an asset and an obligation (see *Access & security*).
- **Ownership is the reason she's buying.** Both the per-client ChatGPT Projects (M02) and now Viktor are "band-aids" in her words. "Ultimately I want it to be something that we own." This matches M03 ("this is ours… we own it?").
- **She's asking E2M to lead.** "I'd also love to hear from you guys, like what is working with the other agencies… I don't know what I don't know" (19:39). The same ask as M00, **and E2M deferred it again.**
- **The recurring pain is follow-through, not information.** "Him just like bringing up areas of opportunity that… I don't have the time or the bandwidth… to make sure that it all actually gets done" (43:54). It's the same pain as M00's "domino effect", M01's "chasing the team" and M02's post-call loop. **The Ops stream was dropped, but the need behind it wasn't.**
- **The team has adopted AI.** Carmen uses Viktor daily, and Gisselle configured its digests. Compared with M00's "starting at square one", **the adoption question has moved.** It's no longer "will they use AI" but "which AI surface wins": Viktor in Slack, E2M's dashboard, or ChatGPT.
- **The bar is concise and aware of context.** Verbosity and advice that ignores the call type are the complaints. The knowledge base should be short and know which call is coming.
- **Scale worries are concrete.** Two simultaneous onboardings strained the team, and reporting grows with every client. If the Q1 2027 scale-up is real, these are exactly what breaks.
- **Gisselle is the practical operator.** She set up the Zoom role and Viktor's digests, and ignored a noisy digest in favour of her own filter. She's a good predictor of what the team will actually use.

## Scope impact
- **The knowledge base (FF-01) has grown into client intelligence.** It now covers history, performance, sentiment, call prep, opportunities, action items, weekly focus, health, team Q&A, a dashboard and a link to the content engine. That's far more than FF-01a–d, which were budgeted at 5–6 weeks. Minu's phasing (Phase 1 = call prep + top opportunities) is the right move and **needs to be written down as the Phase 1 cut.**
- **It overlaps Paid Media Reporting heavily**, on both data and features:
  - the same connectors: Google MCC, Meta ad accounts, GHL sub-accounts, and now Shopify
  - Viktor's Monday 30v30 green/amber/red snapshot *is* PM-01/02 (the weekly performance watch)

  **Build the ad-data connectors once.** If the knowledge base goes before reporting, the connectors (the Sep 15 draft had them in the reporting stream) have to move earlier.
- **The dropped Ops stream is coming back through the knowledge base:** open action items, weekly focus, missed-deadline reminders, open loops. That's OP-01/02 under another name. Viktor's "open loops" also give the practical definition of "acknowledged": **an ask in Slack that got a reply.**
- **Viktor is the incumbent to beat or absorb.** It already covers much of PM-01/02 and parts of FF-01 and OP-02. E2M's version has to be clearly better:
  - organised (a dashboard, not threads)
  - owned (WIA's data and accounts)
  - **follows through** (findings become tasks with due dates and a check that they stuck)
  - concise
  - knows each call type
  - connected to the content engine

  **Decide what happens to Viktor**: coexist (e.g. sales-call prep) or retire. Two agents in the same Slack will confuse the team.
- **The front end isn't decided.** Minu floated ChatGPT connected to the knowledge base; Whitney's ideal is a dashboard; the team works in Slack today; the Command Center from M03 exists as a prototype. Pick one primary surface.
- **Ingestion gets simpler:** calendar event → Zoom meeting → **retained Zoom transcript** → client mapping (Drive folder by offer). Speech-to-text only for the gaps.
- **Call-type templates are needed** for call prep: ads kickoff, messaging & positioning interview, ad strategy presentation, monthly strategy call, LeadLock kickoff, sales call.
- **New sources:** Shopify, feedback surveys, LeadLock support tickets.

## Open questions
- **Are client-call transcripts actually in Zoom Admin?** If yes, correct `Content_Atelier.md` §8 and cut the speech-to-text scope back to the gaps.
- **Which stream comes next: knowledge base or reporting?** And if the knowledge base backend starts early, when do the ad connectors land?
- **Is Q1 2027 scaling a real plan?** It now justifies the sequencing, but it hasn't been confirmed by Whitney or Daniela on the record.
- **Knowledge base Phase 1 spec:** the call-prep format (length limits), the call types covered, the opportunity logic, what counts as a "top" opportunity.
- **Primary surface:** dashboard, ChatGPT or Slack? And how do role-based logins work for the team?
- **Viktor:** coexist or replace? Does WIA keep paying for it?
- **`hello@` access:** scope, holder of the number, end date, revocation steps.
- **Fathom team account:** yes or no, after the Zoom review. And how do office hours and LeadLock kickoffs get in?
- Source-of-truth rule for **an approved document vs a later call** (the remaining part of FF-01's gate).
- **Carried from M04:** the flag mechanism; where drafts live; client consent; the CTA map; case studies and Stories; running cost and spend cap; the SOW; reporting discovery (Tina).

## E2M performance
**What landed**
- **Naming the delivery team** (Nandini, Jainil) and giving the client a direct Slack line to them built continuity and transparency.
- **The timeline progress link** is a lasting answer to "where are we?".
- **The knowledge base discovery was excellent.** Minu:
  - started from use ("tomorrow morning, what are the first questions you'd ask?")
  - asked who else uses it
  - mined Viktor for what works *and* what doesn't
  - asked about sources, exclusions, satisfaction and escalation signals
  - asked **"what breaks first with an influx?"**, which surfaced the onboarding strain and reporting growth
  - asked a **source-of-truth question** that settled half of FF-01's gating decision
- **Asking Whitney to show where old transcripts live** surfaced the Zoom retention fact that reframes the "blocker".
- **Phasing the knowledge base** early heads off the scope sprawl its wish list invites.

**What didn't**
- **E2M asked for the keys to the main account.** The `hello@` password and a 2FA phone, set up live, with no end date or removal plan, and well **beyond the written request, which covered ChatGPT history only**. Lighter-touch routes existed, and it reverses M02's scoped-identity design.
- **No content-engine output was shown**, even though M04 promised an update on "what we have done so far". A small real candidate queue would have counted for more than the timeline, especially next to Viktor.
- **E2M didn't answer "what's working with other agencies?"** It was deferred to "once sources are locked". That's the second time (M00, M05) Whitney has asked E2M to lead with expertise.
- **Viktor wasn't positioned.** E2M learned in detail what the incumbent does but said nothing about how the knowledge base will differ or whether Viktor stays. With Whitney calling Viktor a band-aid and asking for ownership, this was the moment to state the difference.
- **The stream order was left open.** The call opened with "which to pick up next" and never answered it.
- **The Q1 2027 premise was restated as Whitney's own** ("I remember you had mentioned") without being checked. Minu also promised "two main reasons" and gave one.
- **The M04 open items weren't revisited:** CTA map, flag mechanism, drafts location, consent, SOW, spend cap.
- **The Zoom retention question came a week late.** If it had been asked in M04 (or at the Sep 21 handover), the blocker would never have been written up the way it was.

## Prep for next meeting
- **Access:** confirm `hello@` works. Agree a **written scope, end date and revocation steps**, and move calendar access to **sharing with `AI@`**. Also consider ChatGPT's data export instead of logging in.
- **Verify Zoom transcripts** for recent client calls through the role. If they're there, **correct `Content_Atelier.md` §8** and limit speech-to-text to the gaps.
- **Show real content-engine output:** a ranked moment queue from retained transcripts, and one draft pack against the Funktastic benchmark.
- **Decide stream 2 vs 3 explicitly.** If the knowledge base backend starts early, bring the ad connectors (MCC, Meta, GHL, Shopify) forward, since both streams need them.
- **Write the knowledge base Phase 1 spec:** concise call prep per call type, top opportunities, where it appears, and who can see what.
- **State the plan for Viktor**, and lead with an E2M point of view from other agencies, since she has asked for it twice.
- **Confirm the Q1 2027 plan** with Whitney, and bring Daniela in on the next decision call.
- **Carry-overs:** CTA map, flag mechanism, drafts location, consent, SOW (with the access scope in it), spend cap, reporting discovery with Tina.

---
*Transcript notes: speaker labels are scrambled throughout. Most "Whitney" lines at 1:37, 35:08, 40:00 (the question) and 51:32 are Minu, and most "Minu" lines at 9:15, 18:37, 19:33, 31:34, 34:56, 35:54, 39:19 and 39:53 are Whitney. 33:34 ("since I already have a filter in ClickUp") is Gisselle. Mis-hearings:*
- *"Victor" = **Viktor** (viktor.com, the Slack AI agent); "Brittany" = Whitney; "GFO" = probably GA4; "WAA client" = the WIA clients folder; "elevated client" = Elevate client*
- *"lead log" / "lead block" = LeadLock; "JGP" / "GPD" = ChatGPT; "hello at the red" = hello@ ("at the rate")*
- *"a pretty link" = "a pretty lengthy"; "uploads them to the job" = probably "to the Drive"*
- *"…designed for them" (1:51) = probably "designed by them"*

*The source contains a partial E2M phone number; it isn't repeated here.*
