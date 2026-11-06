# Wedding Industry Ads — Automation Scope & MVP Plan

**Engagement:** E2M Solutions x Wedding Industry Ads, LLC (dba LeadLock / LeadLock Pro)
**Phase:** Audit & Blueprint, final week
**Document date:** 7 September 2026
**Author:** Jainil Trivedi, AI Engineer (E2M)
**Blueprint Review:** Thu 10 Sept (or Fri 11 Sept)
**Whitney's homework out of that review:** choose a couple of workflows for execution

---

## What this document is

The complete automation scope for Wedding Industry Ads, derived from three client calls (11 Aug discovery, 26 Aug Weekly Sync 1, 2 Sept Weekly Sync 2), the client-filled *AI & Automation Opportunity Task Audit* spreadsheet, the samples Gisselle sent on 5-7 Sept, and a direct technical probe of the two Fathom share links she provided.

It supersedes the earlier `automationscope.md`. Two things changed materially since that document, and both changed the plan:

1. **Transcript intake became real.** Gisselle manually copied a full office-hours transcript out of Fathom and it works. The five MVPs no longer rest on a stand-in trigger.
2. **Roll-call attendance became partially viable** — then partially un-viable again on closer reading. See the correction in Part 1.

Every quote below is verbatim from the transcripts or the spreadsheet, with its source. Where a claim is E2M inference rather than something the client said, it is labelled as inference. That distinction matters on Thursday: presenting our own design reasoning as client-confirmed fact is the fastest way to lose the room.

---

## Executive summary

**The sheet audits one seat.** All twelve client-filled rows are Gisselle's, all in one department category out of thirteen. Seven people do the work. On 2 Sept, roughly 17 minutes covered the whole spreadsheet and roughly 21 minutes covered work with no row in it at all.

**Twenty automations collapse onto five builds on one spine.** That collapse is the document's central argument and it is what makes a five-card demo possible in four engineering days.

**The hours case is arithmetically dead and we are not leading with it.** The sheet derives to 18.1 hrs/month, only 6.0 of it client-attested. Against the $9,499 Apollo price that is $175 per recovered hour at a theoretical 100% automation. The cases that survive are onboarding throughput, turnover-proofing single points of failure, and founder capacity returned to selling.

**The largest single cost has no row in the sheet.** Tina's monthly reporting runs 18-24 hrs/month - 100-133% of everything the whole twelve-row audit quantifies, and the only duration estimate given for any non-Gisselle work anywhere in either call.

**One structured cut was made.** "Nobody starts from a blank page" - first-draft ad and landing-page copy - is out of Thursday's five. It was Whitney's own unprompted number-one nomination, so the cut is stated out loud, its input half survives inside MVP 1, and its output half is first in the restore queue with a named trigger.

---

# PART 1 - What changed, and one correction I owe

## 1.1 A correction to my earlier reading

In assessing the Feb 12 transcript I concluded that office hours is a **rolling 1:1 queue** and that this made speaker-derived attendance sound, because in a 1:1 format a silent attendee is structurally almost impossible.

**That overstated the evidence.** The client described the format herself, and it is an open drop-in:

> *"it's really like an open meeting for clients to come in, ask them questions, review their accounts... just like a one hour long meeting where they are meeting with the members that can join"* - 26 Aug @12:00

> *"They just join if they have any questions about their setup. And they can join like at any moment during that hour."* - 26 Aug @13:32

So Feb 12 is what an open drop-in looks like **when only three people show up** - not evidence of a queue by design. The correct statement is that **speaker-derived attendance is sound at current volume, not sound by format.** If a week draws six attendees, silent listeners return and the argument evaporates.

And there is a failure mode no format fixes: **the member who joins, listens and leaves without speaking is precisely the disengaged member the 2-week flag exists to catch, and is scored absent.** Jillian left at 9:19 of a 48-minute call and scores as a full attendee. Attendance therefore fails at both ends, in the direction that defeats its purpose.

This is why attendance ends up as the *third* output of MVP 2 rather than a card of its own, and never as a demo headline.

## 1.2 The material changes

### Intake is redefined from API/export ingestion to a deliberate human paste, and this is what makes MVP1's call-ends trigger real rather than mocked.

**Significance:** CRITICAL

**Evidence.** File 05 §2: `canDownload: false`, `downloadVideoUrl: null`, `activateDownloadUrl: null` on BOTH share links; `access: external_view_only`. File 05 §3: the client manually copied the full Google Ads office-hours transcript out of Fathom "and it works perfectly." The working endpoint `/copy_transcript?token=` is undocumented, unauthenticated and behind Cloudflare.

**Consequence.** MVP1's biggest honesty compromise (running on E2M's own Sept 2 recording) is retired — the pipeline now runs on a real client-system transcript arriving via a step Gisselle already performs. But every "automated ingestion" claim from file 03 must be withdrawn on stage, and the follow-up must say explicitly that Gisselle did not ignore the export instruction — export was unavailable to her. Accept all three intake forms (pasted link, pasted text, dropped .txt) into one Slack channel.

### The "one normalizer serves both source systems" claim is asserted, never observed — no Zoom .txt has been seen, and Zoom holds the highest-value corpus.

**Significance:** CRITICAL

**Evidence.** File 05 §3 states Fathom's copy output and "Whitney's Zoom `.txt` both come out as `timestamp - Speaker Name` followed by indented body text" — but §1 shows no Zoom file arrived; Gisselle asked which format we want. Sept 2 @6:54 (Whitney): "it's my Zoom, my, you know, note taker, my recordings, all of that" for every client onboarding and strategy call. Files 01/02 are in Fathom's convention (`@0:11 - Gisselle Jimenez`, `(weddingindustryads.com)` suffix), so they corroborate Fathom, not Zoom.

**Consequence.** The load-bearing economy of the intake decision is unverified against the exact corpus MVP1 and MVP5 both need. Zoom's native transcript is a different product (VTT/cue-numbered or `Speaker: text` with `HH:MM:SS`), so the normalizer may need a second parser. Reply to Gisselle today: the .txt, not the summary.

### Fathom already emits action items inline with deep-linked timestamps, free, today — so MVP1's demo can no longer lead with extraction.

**Significance:** CRITICAL

**Evidence.** File 05 §4d, verbatim in the copied text: `ACTION ITEM: DM Jillian new VIP day link - WATCH: .../calls/566502955?timestamp=534.9999`, plus two more and `SCREEN SHARING` event markers. Header reads `VIEW RECORDING - 48 mins (No highlights)` while action items exist.

**Consequence.** Re-stage the demo around the four things Fathom demonstrably does NOT do: assign an owner, set a due date, deliver anything anywhere (ClickUp task, Slack @-mention, Drive file, drafted client recap email), or remember across calls whether an item was done. Use Fathom's own three items as the on-screen control group — §4e proves Fathom missed the primary→secondary conversion changes on two accounts, four of the nine negatives (`barn`, `under 5000`, `at home`, `banana`), and both soft commitments ("I'll send you the link in DMs", "you can come back to me next time with that shorter lead form"). Adopt Fathom's `?timestamp=` format as the evidence-link convention. Cost is a framing change, not a build change — but the extractor's success bar is now Fathom's output, not zero.

### Speaker-derived attendance is sound at current VOLUME, not sound by FORMAT — file 05's rolling-1:1 conclusion overstates its own evidence.

**Significance:** HIGH

**Evidence.** File 05 §4a: Jillian alone 0:00–9:22, Carmen's handoff "Hey, Erin." at 9:22, "Michael & Diana" 35:00–46:58 — n=1 session, Feb 12, seven months stale. Against it, the client's own description of the format, Aug 26 @12:00: "it's really like an open meeting for clients to come in, ask them questions, review their accounts... just like a one hour long meeting where they are meeting with the members that can join"; @13:32: "They just join if they have any questions about their setup. And they can join like at any moment during that hour."

**Consequence.** Feb 12 is what an open drop-in looks like WHEN THREE PEOPLE SHOW UP — not evidence of a queue by design. If a week draws six attendees, silent listeners return and the soundness argument evaporates. Also unfixable by format: the member who joins, listens and leaves silently is precisely the disengaged member the 2-week flag exists to catch, and is systematically scored absent. State the claim as volume-contingent; keep the abstain lane and the human gate (TASK-13's own text: "Just needs to flag, we will manually follow up"), never an auto-DM. Note the unaccounted 33:00–35:00 gap — the segmentation is inferred, not given.

### The completed onboarding questionnaire never arrived, and it is the payload of three separate signature-branch outputs — but Ridgefield's folder probably contains it.

**Significance:** HIGH

**Evidence.** File 05 §"Not received". Sept 2 @22:00 (Whitney), the Slack announcement content: "Here are, like, key things that you need to look at for them, like their onboarding questionnaire and, you know, sales call recordings." Sept 2 @29:46: "we will download it from Dipsado and Gisselle will save it in the client's Google Drive folder. She'll also share it in the Slack channel for the team to be able to review it."

**Consequence.** MVP1's welcome-email attachment leg, its Slack team-announcement payload, and the client_brief.md seed all run on fabricated content today. But Gisselle's own described mechanism puts the questionnaire in the Drive folder we were just given. This is the single highest-priority Drive lookup, and it simultaneously unblocks MVP3's brief seed.

### MVP3's exemplar layer is permanently unobtainable, not merely delayed — the block is correct platform behaviour, not a sharing mistake.

**Significance:** HIGH

**Evidence.** File 05 §1: "It's not letting me share the chatgpt project. It says it will remove all files from the project" — correct, because per Sept 2 @31:16 (Whitney): "We're not at this point, actually, no. We just have an account for the hello at weddingindustryads.com. The team members have the login information." No Team/org account, so Project sharing strips files.

**Consequence.** We lose both the custom instructions (their implicit house brief format) and the prior chats (what the team currently accepts as a usable draft, and the tweaks they made). MVP3's "matches how your team already prompts" claim must be dropped. Recalibrate against SHIPPED artifacts in Ridgefield instead — a better reference than ChatGPT drafts anyway, since Whitney called the Project "a band-aid" and "we don't see it as a long-term solution." The bar MVP3 must clear is not the Project; it is her own words, Sept 2 @32:26: "more of a push for them than just starting from a blank page."

### The two-tier folder structure adds a non-optional leak-risk requirement to MVP1's filing leg.

**Significance:** HIGH

**Evidence.** File 05 §1: "Shared Ridgefield's client folder (The wia+ridgefield sub-folder is the one shared with the client)." So an internal client folder contains a client-visible subfolder.

**Consequence.** Every Drive write now needs an explicit internal-vs-client-facing tier flag, and the client-facing tier must sit behind the same Slack review card as outbound email. Writing to the wrong tier leaks internal material to a client, which breaks the hardest constraint in the engagement. Small cost (a path-tier field plus one extra gate), but non-negotiable — and it must be visible on the demo card, because it is a correctness feature the client will immediately recognise as necessary.

### MVP5's single blocking artifact was explicitly offered by the client — but a generic ask will yield an unusable call.

**Significance:** HIGH

**Evidence.** File 05 §1: "Client meetings are held in Whitney's zoom so it's just the txt file downloaded from zoom. Would that or a summary work best?" Against Aug 26 @19:21 (Whitney), the content requirement: "I had this strategy call with a client, they said all these amazing things about our work or the growth of the business or how things are feeling, I want to take that and then turn it into content."

**Consequence.** Cheapest status change in the portfolio — one reply. But MVP5 needs a call containing client praise of results; a routine monthly 1:1 about raising a retargeting budget produces a flat reel script, and this is the ONE item Whitney tied to revenue ("we need more leads. We need more sales... if we're not marketing actively, that's not going to happen"). Ask specifically for the .txt — not the summary, which strips the verbatim quotes the three timestamped reel scripts are built on — from a call where the client said something good about results.

### Roll-call's flag VOLUME may invalidate its spec before a line is written.

**Significance:** HIGH

**Evidence.** File 05 §4c: three members across a 48-minute Google session, ONE across the 49-minute Meta session. Aug 26 @5:25 (Gisselle): "right now it's manageable because we have, like, not, like, a large number of members."

**Consequence.** If most portal members are non-attenders in any given week, the 2- and 4-week flags fire on nearly everyone continuously — a DM treadmill, which reproduces exactly the failure it was built to fix ("It's in my task list to automate this somehow but it's complex"; "I tend to forget"). Ask before building: at steady state, how many members are currently past the 4-week flag? If the answer is "most of them," the correct product is ranking who to re-engage, or firing once on threshold-crossing with a cooldown — a different spec. Be honest that its value was never hours: 2.0 hrs/month on three-row data.

### An entirely undiscussed workstream surfaced — the ad-account change log — and it feeds the largest hours item in the whole engagement while being the only artifact on-thesis for what they are actually buying.

**Significance:** HIGH

**Evidence.** File 05 §4e: Carmen switched outbound-click conversions primary→secondary on two separate client accounts, added nine negatives, committed to a 50/50 A/B for Erin, promised Jillian a VIP-day link — "None of this lands in ClickUp, Slack, or any client record." Against Sept 2 @33:01 (Whitney) on Tina's reporting: "It's not automated in any way right now... We're adding in additional context about like the why behind it all" — the 18–24 hrs/month item, the only non-Gisselle duration estimate anywhere in either call. And Aug 11's stated driver: turnover-proofing, "We have the agency brain."

**Consequence.** A sourced change log replaces a remembered "why," directly supplying MVP4's narrative layer, and is the only candidate that extracts institutional knowledge out of a specialist's head. It also puts Carmen and Jacqueline on screen — two of the four single points of failure the audit sheet never touched, which is file 04's named conversion risk. Honest caveat: zero client validation. Nobody mentioned it in either transcript.

### The office-hours engine is a new ROUTE on the existing spine, not a new card — and presenting it as a route is strictly better.

**Significance:** MED

**Evidence.** The shared spine already specifies "a strict JSON tool-schema extractor... with call_type routing." The genuine increments are three output schemas, a GHL Communities roster join (MVP1 never joins against external state), and cross-run commitment lifecycle state (MVP1 has no cross-call memory). Everything else — normalizer, abstain lane, Slack poll gate, connectors, run ledger — is reused wholesale.

**Consequence.** Fold it into MVP1 as a second call_type and present "The Handoff — any call in, the right handoff out" across three demonstrated call types (client call, internal Monday meeting, office hours), at roughly 0.5–0.75d incremental instead of a full card. This fits the 4.0-day budget without a third cut, and it answers Whitney's literal question better than five cards ever could — Aug 26 @19:21: "the biggest thing that I'm looking for at this point... is like, how is it all connected? How does it all kind of work together sort of thing?"

### Identity resolution — not attendance capture — is roll-call's real blocker, and it sits on an unverified API behind an unaccepted invite.

**Significance:** MED

**Evidence.** File 05 §4b: speaker labels are `Carmen Cruickshank (weddingindustryads.com)`, `Jillian` (no surname), `Erin Smith`, `Michael & Diana` (one label, two humans) — 2 of 3 member rows ambiguous in the only sample we have. File 03: GHL "API availability was only ever 'most likely' on-call — VERIFY EARLY." File 05 §1: invites SENT, permission levels "NOT confirmed by her."

**Consequence.** Fuzzy-match to the GHL member roster plus a mandatory abstain/confirm step, keyed per member ACCOUNT rather than per person so "Michael & Diana" resolves. Verify the Communities/membership roster endpoint within the hour the invite is accepted; if it is absent, roll-call must degrade to raw label capture into the existing sheet, not to nothing.

### Every connector leg in the portfolio is still mock until invites are accepted and permission levels verified — with three days left.

**Significance:** MED

**Evidence.** File 05 §1: "I have sent invites for clickup, highlevel, the members portal and slack (will add you to channels once invite is accepted)" and "Seat level (Member vs Guest) and GHL permission level (Agency Admin) NOT confirmed by her — must verify on acceptance."

**Consequence.** ClickUp write, GHL read, Slack post and Members Portal are all portfolio-wide live risks, not settled facts. Accept every invite today and verify three specifics: ClickUp is Member not Guest (file 03: "Guests cannot open templates" — which kills MVP1's offer-dependent template selection), GHL is Agency Admin, and the Slack grant carries channel-create scope for the signature branch's per-client channel.

### Jacqueline sits outside the company Fathom workspace, so the Meta half of any office-hours ingestion depends on a contractor changing her own tooling — and the internal/external domain heuristic fails on her.

**Significance:** MED

**Evidence.** File 05 §2: Google call `host carmen@weddingindustryads.com`, `is_multi_user: true`; Meta call `host jacqueline@jacquelinehood.com`, title never set ("Impromptu Zoom Meeting"), her label renders `Jacqueline Hood (Jacqueline Hood)` and "classifies as external under a domain heuristic."

**Consequence.** Whitney pre-consented in principle (Sept 2 @4:08: "if we need to switch to a team account or anything like that, I mean, we, we totally can") but she does not control Jacqueline's account. Do not rely on the `(weddingindustryads.com)` suffix as the internal/external test — it silently misclassifies a core team member. The Meta sample is also useless as an attendance sample: two speakers, one of them staff.

### The monthly report arrived as a Canva /edit link and the walkthrough video did not arrive at all, leaving MVP4's script leg uncalibrated and creating a write-risk on a live client asset.

**Significance:** MED

**Evidence.** File 05 §1: "Client report example: [Canva /edit link]" plus a template link; §"Not received": "The report walkthrough video — requested, not sent. MVP4 generates the script for it, so register and length are uncalibrated."

**Consequence.** The 90-second script remains a guess on register and length — the one leg of MVP4 with no design target, against a deliverable spec that file 03 called "the design target for report generation." Ask for the PDF as sent to the client (the /edit view shows template scaffolding, not the delivered artifact) plus the video. Separately, treat the /edit link as read-only by policy: it is a write-capable link into a live client report and ai@ must not modify it.

### MVP2 gained real client targets and a pre-confirmed real finding, making it a stronger insurance policy than at selection.

**Significance:** LOW

**Evidence.** File 05 §5: the Ridgefield folder "may yield real client landing-page URLs." Aug 26 @41:28 (Minu): "on the mobile section, there is a CTA which points to a 404" — Whitney confirmed it live: "Yeah, we actually caught that a couple of days ago", plus a second broken link in the investment guide.

**Consequence.** The mobile-first crawler can re-discover, live and with zero credentials, a defect the client has already independently confirmed is real — the most credible demo beat available anywhere in the portfolio. It also becomes load-bearing if MVP3 is cut, since MVP2 covers only the last clause of Whitney's own unprompted #1 nomination (Aug 26 @16:54: creative briefs, first drafts of copy, first drafts of landing pages, "and then checking the landing pages and seeing, are there errors? Is it going to convert sort of thing?").

## 1.3 Per-card status change

| Card | Direction | Reasoning |
|---|---|---|
| MVP1 · The Handoff | **STRONGER** | The call-ends trigger is genuinely real now, not mocked: a real client-system transcript arrived in the confirmed copied format, and the paste is a step Gisselle already performs (file 05 §3). Three further legs also became real rather than stubbed — the Shared Drive confirmation green-lights ai@ actually writing files, the ClickUp Member invite makes the real onboarding templates readable for the first time, and the "Full service email templates" Drive folder grounds the drafting voice in a real corpus instead of an invented one. The SIGNATURE trigger, however, is only partially de-risked. Exactly what is still missing for it: (1) a RAW, non-forwarded Dubsado alert — the samples arrived forwarded, so the envelope headers belong to the forwarder and the production signal is a Gmail filter on hello@, which file 03 lists under NOT REQUESTED and which blocks TASK-04 entirely; (2) confirmation the forwarded set contains BOTH alert types, because Whitney's gate is a conjunction — Sept 2 @24:09: "the trigger is that, like, we see in the inbox that they have signed the contract and paid the invoice"; (3) the completed onboarding questionnaire, which is the payload of the welcome email AND the Slack announcement AND the client_brief seed; (4) the offer name on the alert, since template selection is offer-dependent — Sept 2 @21:22: "if they're just doing the foolproof follow-up advantage... that's its own thing, versus if they're signing on for ads management as well, then it's like, we're going off both of those onboarding templates"; (5) Slack channel-create scope. Two new burdens land on this card: the internal-vs-client-facing filing tier (a leak risk, not a nicety), and a re-staged demo, because Fathom hands the client action items with deep links for free today. |
| MVP2 · Page Check | **STRONGER** | Still zero credentials, zero dependencies, and now with better targets. The Ridgefield folder plausibly yields live client landing-page URLs, so the crawl covers real client work rather than only WIA's own funnel. More importantly it can re-discover, on stage, a defect the client already confirmed independently — the mobile CTA pointing to a 404 that Minu surfaced Aug 26 @41:28 and Whitney immediately validated: "Yeah, we actually caught that a couple of days ago." That is the single most credible thing in the portfolio: a finding the client has already agreed is true, reproduced live with no access to anything. Its strategic weight also rose, because if MVP3 is cut it becomes the only coverage of Whitney's own unprompted #1 nominated opportunity, and it covers just the final clause of it. |
| MVP3 · Nobody starts from a blank page | **WEAKER** | Its exemplar layer is now permanently gone, not delayed: the ChatGPT Project block is correct platform behaviour on a shared hello@ login with no Team/org account (Sept 2 @31:16), so the custom instructions and prior chats are unobtainable without Gisselle manually downloading files, copying instructions and screen-recording. That removes both the house brief format and the only reference for what the team currently accepts as a usable draft. The onboarding questionnaire also never arrived and there is no messaging-and-positioning transcript. So the card's entire status rests on a Drive inventory nobody has run yet — making it the highest-variance item in the portfolio, and the natural first cut against 4.0 real days versus a 4.75-day plan. Two things cut the other way and should be weighed honestly: the Ridgefield folder is a plausibly BETTER substitute than the Project for the input corpus, because Gisselle described the exact filing mechanism herself (Sept 2 @29:46 questionnaire to the client Drive folder; TASK-14 recordings, transcripts and summaries to the client folder, and the messaging-and-positioning interview IS a client meeting); and the bar to clear is low by the client's own account, since Whitney called the Project "a band-aid", said "we don't see it as a long-term solution", and set the standard at Sept 2 @32:26 — "more of a push for them than just starting from a blank page." |
| MVP4 · An executive summary instead of a wall of screenshots | **WEAKER** | The Canva report arrived, so the one-page summary has a real design target — but as an /edit link, which shows template scaffolding rather than the artifact as delivered, and which is write-capable into a live client asset. The walkthrough video did not arrive at all, so the 90-second script leg has no calibration for register or length; that leg is now the least-grounded piece of any selected card. Live ad metrics remain mock, unchanged, since the Google Ads and Meta APIs were never requested. The offsetting gain is real but conditional: the ad-account change log from file 05 §4e would supply exactly the "why behind it all" that Whitney says Tina currently adds from memory (Sept 2 @33:01), replacing a remembered narrative with a sourced one — but only if the office-hours route is actually built, so it cannot be credited as an unconditional improvement. |
| MVP5 · One voice note, a month of marketing | **NOW_VIABLE** | Still blocked on the identical single artifact, but the block changed character decisively: the client explicitly OFFERED it and asked only which format we want — "Client meetings are held in Whitney's zoom so it's just the txt file downloaded from zoom. Would that or a summary work best?" Acquisition is genuinely one reply away, the cheapest status change in the portfolio. It is not, however, one ask away from being GOOD, for two reasons. First, not any client call works: the card needs a call containing client praise of results — Aug 26 @19:21, "they said all these amazing things about our work or the growth of the business" — and Whitney is the human filter who selects those by memory. A generic ask risks a routine budget-tweak call, which yields a flat demo on the one item she tied to revenue. Second, the voice note leg is still mocked: no voice note exists, and none was ever requested in file 03. There is also a small honesty regression that is the mirror image of MVP1's gain — Fathom-sourced content carries clickable `?timestamp=` deep links, whereas a Zoom .txt has no shareable player URL, so "timestamped quotes" degrade to bare @MM:SS citations for exactly the calls this card runs on. |
| Roll call (previously REJECTED) | **NOW_VIABLE** | The rejection ground — unknown attendee capture — is genuinely gone, but not for the reason file 05 gives. Arguing for: in a rolling 1:1 a silent attendee has no function, and the Feb 12 flow bears that out (Jillian 0:00–9:22, the explicit handoff "Hey, Erin." at 9:22, Michael & Diana 35:00–46:58 — every named member spoke at length while screen-sharing their own account). The stronger argument, underweighted in the original rejection, is that TASK-13 only ever asked for a flag: "Just needs to flag, we will manually follow up." A human catches a false-absent before any client contact, so the constraint that client relationship touch stays human is never at risk. Arguing against, and these are real: the rolling-1:1 finding is n=1 and seven months stale, and the client's OWN description contradicts it as a design — Aug 26 @12:00 "it's really like an open meeting for clients to come in", @13:32 "they can join like at any moment during that hour." Feb 12 is what an open drop-in looks like when three people show up, so the correct claim is that speakers approximate attendees at current VOLUME, not by format; grow the roster and silent listeners return. The Meta sample argues against generalising rather than for it (two speakers, one of them staff, on a call whose title was never set). Lurkers are still invisible and are precisely the disengaged population the flag exists to catch. Early departure is invisible too — Jillian left at 9:19 of 48 minutes and scores as a full attendee. Identity resolution is a blocker, not a caveat: 2 of 3 member rows in the only sample are ambiguous. And the volume question in §4c is a product-definition problem, not a caveat — if most members are non-attenders, the flags fire on nearly everyone forever. Conclusion: viable as an engine capability, not as a standalone card. Its value was never hours (2.0/month on three-row data); it is that she stops forgetting and that she tried and failed to automate it twice herself — which makes it a credibility asset and, notably, the cleanest miniature of the turnover-proofing thesis they are actually buying, since the knowledge of who is disengaging currently lives in a sheet hand-duplicated by a 25-hr/week outside contractor. |
| Office-hours engine (never considered) | **NOW_VIABLE** | Honest answer to whether it is a new card: mechanically it is largely MVP1 pointed at a different input, and it should be presented that way. The spine already carries call_type routing, and the normalizer, abstain lane, Slack poll gate, connectors and run ledger are reused wholesale. But three things make it more than a re-point. Its outputs are different KINDS of output, not reformatted ones: attendance requires a join against an external member roster, which MVP1 never does; the change log is a different extraction problem (past-tense configuration deltas attributed across two named client accounts, not future action items); and the commitment tracker needs cross-call did-it-happen state, which MVP1 has none of. Second, it is the only candidate that puts Carmen and Jacqueline on screen — two of the four single points of failure Whitney named herself (Sept 2 @25:50: "it's not like there are multiple team members that do the same things") and the exact gap file 04 identifies as the engagement's biggest conversion risk. The change log is literally institutional knowledge moved out of a specialist's head into a company-owned record, which is the Aug 11 thesis: "We have the agency brain." Third, it compounds: the change log supplies MVP4's "why behind it all", the leg Tina currently writes from memory in the 18–24 hr/month process. Weaknesses stated honestly: only 1 of 3 outputs is client-attested — roll-call was discussed, TASK-10's pain was articulated but its process never walked, and the change log was mentioned by nobody in either transcript, so we would be showing a client with low AI literacy an engine she did not ask for. And the extractor would be validated on n=1, since the Meta transcript is a two-person troubleshooting session rather than a second change-log sample, and Feb 12 is seven months old. |

## 1.4 Where the demo got more honest

- MVP1's call-ends trigger runs on a real client-system transcript in the confirmed copied format, arriving via a step Gisselle already performs — no longer standing in E2M's own Sept 2 recording, which was the portfolio's single biggest compromise
- MVP1's Drive filing leg writes for real: client folders are confirmed to live in a Shared Drive, so ai@ can actually create and upload rather than emitting a proposed-path stub
- MVP1's signature branch parses genuine Dubsado alert text rather than a synthesized payload (with the caveat that the copies are forwarded, so the envelope is not)
- MVP1's ClickUp leg can be built against the real onboarding templates for the first time, so template selection and due-date logic stop being guesses
- Drafting voice across MVP1 and MVP4 is grounded in the client's real 'Full service email templates' corpus rather than an invented tone profile
- MVP4's one-page summary has a real design target in the received Canva report
- MVP2 can re-discover live a defect the client independently confirmed on Aug 26 — a demo beat that is real end to end with zero credentials
- Roll-call and the office-hours outputs run on a real client-side transcript with real member names, real account changes and real unlogged commitments — nothing about the input is invented
- Evidence links can use Fathom's own `?timestamp=` deep-link format, so every extracted fact is clickably verifiable in a convention the team already uses

## 1.5 Where it must now be more mocked than planned

- Any claim of automated transcript ingestion must be withdrawn: intake is now an explicitly human paste, and the follow-up must state that export was unavailable to Gisselle rather than ignored by her
- MVP3 loses its 'matches how your team already prompts' claim entirely — the custom instructions and prior chats are unobtainable, so output quality has no client-side reference standard unless Ridgefield yields shipped artifacts
- MVP1's welcome-email attachment leg and Slack team-announcement payload run on a fabricated onboarding questionnaire, and must be labelled as such unless the real one turns up in Ridgefield's folder
- MVP1's signature trigger stays a manual file-drop: no raw Dubsado alert and no Gmail scope on hello@, so the production Gmail-filter signal cannot be shown at all
- 'One normalizer serves both source systems' must be presented as a design intention, not a verified fact, until a Zoom .txt has actually been parsed
- MVP4's 90-second walkthrough script is uncalibrated on register and length with no video to design against — the least-grounded leg of any selected card
- MVP5's voice note is a stand-in recording: none exists and none was ever requested
- MVP5's timestamped quotes degrade from clickable deep links to bare @MM:SS citations whenever the source is Zoom, which is every client call
- Roll-call's soundness must be stated as volume-contingent, not format-guaranteed, and cannot claim to distinguish 'did not attend' from 'attended silently and got nothing'
- Live ad metrics remain mock fixtures and the Canva banner stays descoped — both unchanged, both must stay labelled
- Every connector leg (ClickUp write, GHL read, Slack post, Members Portal) is still mock until invites are accepted and Member/Agency-Admin levels are verified, with three days remaining
- The internal/external domain heuristic must be presented as unreliable: it silently misclassifies Jacqueline, who hosts on her own domain outside the company Fathom workspace
- The office-hours engine's change-log extractor would be validated on a single seven-month-old session, and two of its three outputs have zero client validation

---

# PART 2 - The complete automation inventory

Twenty automations. Twelve from the audit sheet (A-series), eight discussed across the calls but never audited (B-series). Coverage status was verified quote-by-quote against the transcripts; across 182 evidence items, zero fabrications were found and three classifications moved under adversarial challenge.

## 2.1 A-series - from the audit sheet

| # | Row | Automation | Sheet priority | Coverage after verification | Hrs/mo | In the five? |
|---|---|---|---|---|---|---|
| A1 | 4 | Filing emails + drafting replies | HIGH | Substantially discussed - deepest segment in either call (26 Aug @23:45-@40:19, live inbox screen-share) | unquantified | **Partial** - drafting half only, in MVP 1. Triage half blocked on Gmail scope |
| A2 | 5 | ClickUp overdue sweep to Slack | LOW | Named only - one beat in a row-order sheet read, spent entirely on the access question | 2.0 | No - reuses MVP 2's commitment primitive in Apollo week 1 |
| A3 | 6 | Team meeting recap + action items | MED | Named only - E2M wrongly asserted it was covered; only Fathom seats were asked about | 4.0 | Yes - MVP 1, internal call type |
| A4 | 7 | Post-client-call recap emails from templates | MED | Substantially discussed - Whitney narrated the whole chain unprompted | unquantified | Yes - MVP 1 anchor |
| A5 | 8 | Onboarding ClickUp checklists, due dates, assignees | MED | Substantially discussed - but the row is Gisselle's 2hr setup slice while the call described a multi-week lifecycle | unquantified (2.0/instance) | Yes - MVP 1 signature trigger |
| A6 | 9 | Client assets to client Drive | LOW | Substantially discussed - really three separate builds | unquantified | Yes - MVP 1, incl. the ChatGPT-Project leg via the auto-assembled brief |
| A7 | 10 | Chasing team members on action items | HIGH | Pain fully articulated, **process never walked** | unquantified | Yes - MVP 2 commitment tracker |
| A8 | 11 | 1-hour event reminder posts | MED | Substantially discussed with screen-share | 3.0 | No - Apollo week 1, single-system GHL job |
| A9 | 12 | Session upload + portal recap post | MED | **Named only** - one broken-off clause in 92 minutes | **6.0 - largest row** | Partial - the recap-summary content leg in MVP 2 |
| A10 | 13 | Roll call, consecutive misses, 2/4-week flags | HIGH | Substantially discussed with screen-share | 2.0 | Yes - MVP 2, third output |
| A11 | 14 | Client meetings to client folder | MED | Routing established, **mechanics never asked** | unquantified | Yes - MVP 1, with the tier split added |
| A12 | 15 | Overdue invoices + invalid emails | MED | Substantially discussed - most complete process model in the sheet | ~1.1 | No - Apollo week 1 |

**Derivable total: 18.1 hrs/month**, of which only 6.0 is client-attested (column F was filled on 2 of 12 rows). Six rows cannot be quantified at all, including two of the three HIGH-priority items.

Three rows carry Gisselle's own confessions in the Comments column, and all three are memory failures rather than effort problems: *"it has happen that I forget to post on time"* (row 11), *"It's in my task list to automate this somehow but it's complex"* (row 13), *"Easy task but I tend to forget"* (row 15).

## 2.2 B-series - discussed at length, no row in the sheet

| # | Automation | Owner | Evidence | In the five? |
|---|---|---|---|---|
| B1 | Monthly client reporting to executive summary | Tina | *"dedicating the first few business days of the month... It's not automated in any way right now"*. 18-24 hrs/mo derived | Yes - MVP 4 |
| B2 | Content + marketing repurposing | Whitney | The only item she tied to revenue: *"we need more leads. We need more sales"* | Yes - MVP 5 |
| B3 | Creative briefs and first-draft copy | Ivy, Carmen, Jacqueline, Tina | Her own unprompted #1: *"getting creative briefs done... first drafts of copy, first drafts of landing pages"* | **CUT** - input half in MVP 1, output half first in restore queue |
| B4 | Landing-page and funnel QA | nobody | Same sentence, last clause: *"are there errors? Is it going to convert sort of thing?"* | Yes - MVP 3 |
| B5 | Onboarding orchestration across the delivery team | Carmen, Jacqueline, Ivy, Tina, Danielle | ~8 sequential client-approval gates, two parallel tracks, DNS + A2P | Partial - MVP 1 scaffold; full orchestration is Apollo |
| B6 | Sales call to Dubsado proposal | Whitney | *"they should know by the end of the call, okay, this person wants to move forward with Elevate"* | No - no sales-call transcript was ever requested |
| B7 | Client knowledge layer / the agency brain | Gisselle builds by hand | Per-client ChatGPT Projects. Whitney: *"a band-aid"*, *"we don't see it as a long-term solution"* | Yes - the spine, under all five |
| B8 | Whitney's own workload | Whitney | Runs every sales call and every client call. Zero rows, zero hours captured anywhere | Indirect - MVP 1 and MVP 5 return her time |

## 2.3 The exposure this creates

Whitney named her own single points of failure: *"it's not like there are multiple team members that do the same things, right? It is just like one person with set responsibilities"* (2 Sept @25:50).

Carmen (Google Ads), Jacqueline (Meta Ads), Tina (LeadLock design + all monthly reporting) and Danielle (LeadLock implementation, DNS, A2P) are each a single point of institutional-knowledge failure. **None has ever been interviewed.** An engagement sold on turnover-proofing has so far audited only the seat that is an outside contractor. That is the most damaging question available to Whitney on Thursday, and the portfolio is built to pre-empt it rather than discover it.

---

# PART 3 - The interconnection map

Twenty automations, five builds. This is the part that matters.

## 3.1 The shape

```
                    ONE INTAKE - a paste into one Slack channel
              (a link, pasted transcript text, or a dropped .txt)
                                    |
                          [ NORMALIZER + EXTRACTOR ]
                        call_type routing, timestamps on
                          every extracted fact, abstain lane
                                    |
        +---------------+-----------+-----------+---------------+
        |               |                       |               |
    MVP 1           MVP 2                   MVP 4           MVP 5
  THE HANDOFF   WHAT WE CHANGED          EXECUTIVE        ONE VOICE
                                          SUMMARY            NOTE
   client call   office-hours call         reads the       reads the
   signature     -> change log             record          record
   internal mtg  -> commitments
   messaging     -> attendance
        |               |                       |               |
        +------> client_brief.md + updates/ <---+---------------+
                   (one file per client,
                    read AND written by all)
                                    |
                      [ SLACK REVIEW GATE - approve / edit ]
                     every client-bound output stops here

    MVP 3  PAGE CHECK - needs no intake, no record, no credential.
           Runs standalone. The insurance policy.
```

## 3.2 Two cards fill the record, two cards read it, one needs nothing

That sentence is the architecture, and it is the answer to the question Whitney has asked across three calls and never had answered:

> *"the biggest thing that I'm looking for at this point, I feel like, is like, how is it all connected? How does it all kind of work together sort of thing... is there one place that we're going, and then there are just like, different tabs?"* - 26 Aug @19:21

- **MVP 1 and MVP 2 write** to the per-client record - decisions, action items, commitments, filed artifacts, account changes, attendance.
- **MVP 4 and MVP 5 read** it - the monthly summary's cause sentence traces to a real change with a real timestamp; the reel scripts draw on quotes already captured.
- **MVP 3 needs neither**, which is exactly why it exists: it is the card that works when nothing else has arrived.

Four cards in a chain and one insurance policy is a system with a shape. Five independent tiles is the catalogue that already paralysed her once.

## 3.3 Shared-trigger clusters

**"A meeting ended."** A3, A4, A11, plus the extraction half of A7, plus the harvest input for B1 and B2. These are not separate automations - Whitney described A4 + A11 + A3's client half in a single sentence:

> *"Gisselle is then uploading the recordings to the client folder, checking the meetings for action items, four action items, then assigning them to team members in ClickUp, letting them know in Slack, drafting a recap email for the client, and including action items there, and attaching the recording."* - 2 Sept @6:54

One trigger, five outputs. Three cards would let her pick a third of a system.

**"A client signed."** A5, A6 legs 1 and 3, B5, B6. One trigger - the Dubsado alert landing in Gmail - fans out to a ClickUp list, a Drive folder, a Slack channel, a team announcement, a welcome-email draft, a LeadLock sub-account and the initial client brief.

**"A clock ticked."** A12 daily, A10 weekly, A2 and A7 Monday, A8 on the event calendar, B1 at month close. Same skeleton, different queries.

**"Content exists."** B3, B2, A9 - all renderers over the same brief plus a transcript.

**"A page changed."** B4 standalone, gating B5 through the A2P readiness chain.

## 3.4 The Monday collision

A2, A3, A7 and A1's Monday inbox sweep all fire on the same morning at the same five people. Built as four independent automations, that is four bots messaging an already-inundated team every Monday. **It is one Monday product with one review pass and one outbound digest**, or it gets turned off in week two.

## 3.5 Shared primitives

**The did-the-human-do-it primitive.** A10 already contains A7 - Gisselle creates ClickUp tasks to verify Carmen and Jacqueline actually sent the 2-week DMs (26 Aug @14:47). One piece of code. MVP 2 owns it; A2 and A10 reuse it.

**The Gmail-alert trigger.** Dubsado is being decommissioned offer by offer into GHL. Build the onboarding trigger on the **Gmail alert signal, not on Dubsado** - the alert survives the migration, a Dubsado integration has a shelf life of months. One decision protects A5, A6 and B5 at once.

**Call-type routing.** A3, A4, A11, B1, B2 and B6 each need to know which kind of call this was: ads kickoff, messaging and positioning, ad strategy presentation, monthly 1:1, LeadLock kickoff, internal Monday, sales call, office hours. Classify once, route eight ways.

**The offer maps.** A5 needs offer to ClickUp template (both-services clients need two merged). B6 needs offer to public proposal URL - *"we've created public proposals for offers"*, so the artifact is a URL and no Dubsado API is needed anywhere. Same map, two consumers, five-minute client ask, never asked.

**Identity resolution.** A1 (sender to GHL contact), A10 (speaker to member roster), A12 (invalid contact), A5 (signature to client), B1 (metrics to client). Every one answers "which client is this?" Build one resolver.

**The GHL Communities question.** A8 and A9 are gated on one identical unknown - can a post be created programmatically into a Communities channel? GHL API v2 documents no such endpoint. One 15-minute test answers both rows, and the answer may be that the capability does not exist.

## 3.6 The dependency chain nobody drew

The most consequential cross-track dependency in the business, narrated by Whitney and captured nowhere:

```
Tina builds the privacy-policy landing page
        v
Danielle submits A2P / 10DLC registration     <- gated by MVP 3's reachability check
        v
A2P approved -> SMS enabled
        v
LeadLock workflows tested (internal, then client)
        v
Official LeadLock onboarding call
        v
LeadLock form goes live on the client's website
        v
Carmen + Jacqueline swap the campaign URLs
        v
Client considered fully onboarded -> monthly maintenance
```

Every arrow is a handoff between two people with no shared view of state. **That chain is what "we're always chasing the team" actually is** - and it is why the fix is a status surface plus nudges, in Slack, not a model.

---

# PART 4 - The shared spine

Standalone, the five cards cost far more than the week allows. On this spine they fit. The spine is not scaffolding - it is the product, and it is the compounding-capability argument that justifies a platform engagement over point automations.

| Component | Effort | Used by |
|---|---|---|
| Transcript normalizer + JSON tool-schema extractor with `call_type` routing; every fact carries its source timestamp | ~0.4d | MVP 1, 2, 4, 5 |
| **The confidence / abstain lane** - low-confidence or ambiguous-owner items route to a "needs a human" queue with both candidates and the quote, never a guess | ~0.05d | all |
| **The Slack review gate**, poll-based via reactions and threaded replies - no public webhook, no 3-second ACK, no tunnel to fail on stage | ~0.25d | all client-bound output |
| Connector layer - ClickUp v2, Drive v3 (`supportsAllDrives`), Gmail `drafts.create` on `ai@`, Slack, GHL v2 Private Integration Tokens | ~0.35d | all |
| `client_brief.md` + the `updates/` append log - one human-readable, Gisselle-editable file per client, **read AND written** | ~0.2d | all |
| Staleness confirm-or-correct job | small | the durability answer |
| `agency_playbook.md` - composed from the transcripts already on disk | small | the agency-level layer |
| Run ledger + 30-day backtest | small | the Aug 11 question |

**Why `client_brief.md` is a Markdown file and not a vector store:** twelve clients at a few KB each makes RAG engineering theatre. A human-readable, diffable file that Gisselle can open and fix is the correct engineering *and* the correct adoption strategy. Critically it is **written**, not just read - every run appends what it learned, so the file gets truer the more the system runs. A read-only version is just a template.

**Why the abstain lane matters more than its size suggests:** Whitney abandoned her own custom GPTs when they drifted. She needs to see the guardrail fire once, on purpose, rather than watch twenty-five minutes of clean runs.

**Why Slack and not a dashboard:** 100% team adoption, she volunteered access to the workspace and all client channels, ClickUp was never adopted (*"the team has never, like, fully adopted ClickUp other than to just, like, check off the tasks"*), and the word "dashboard" appears zero times across both transcripts despite being in the Aug 11 sold scope.

---

# PART 5 - The five MVPs


**Total: 4 engineering days, spine included.**

| # | Card | Days | Sheet rows | Dependency |
|---|---|---|---|---|
| 1 | **The Handoff — any call in, the right handoff out** | 2.3 | TASK-07, TASK-14, TASK-06, TASK-08, TASK-09, TASK-04 | 7 open items |
| 2 | **What we changed, what we promised, who showed up** | 0.7 | TASK-13, TASK-10, TASK-12, TASK-05 | 6 open items |
| 3 | **Page Check — are there errors? Is it going to convert?** | 0.5 | none (deliberate) | 3 open items |
| 4 | **An executive summary instead of a wall of screenshots** | 0.25 | none (deliberate) | 4 open items |
| 5 | **One voice note, a month of marketing** | 0.25 | none (deliberate) | 4 open items |

## The story these five tell

One sentence, and it is the answer she has been waiting three calls for: every call your business already runs contains the work, and there is one place per client where all of it lands. That is the whole architecture. One intake — a paste into a single Slack channel, in whatever form is convenient that day: a link, pasted text, a dropped .txt. One engine that reads what kind of call it was and produces the right handoff. One record per client that every card writes to and every card reads from. Five things come out of that, and they are not five machines: THE HANDOFF is the trunk — a client call, a signature, the Monday internal meeting, a messaging-and-positioning call, each producing the recap, the owners, the tasks, the filing and the announcement that Gisselle assembles by hand today. WHAT WE CHANGED, WHAT WE PROMISED, WHO SHOWED UP is that same trunk pointed at the people your audit never covered — Carmen's and Jacqueline's office hours become a company-owned account record instead of something that lives in one specialist's memory. Those two cards fill the record. The next two read it: the EXECUTIVE SUMMARY takes the record plus the metrics and produces the monthly client page, with its cause sentence tracing back to a real change and a real timestamp rather than to what somebody remembered; ONE VOICE NOTE takes the client calls already in the record and turns them into a month of your own marketing. And PAGE CHECK is the one that needs nothing at all — no call, no login, no waiting on anyone — because before anything reaches a client, something should have checked whether the page works on a phone. Show the picture once, run the five, and 'how is it all connected' is not answered with a diagram. It is answered by watching Ridgefield's client record fill up as each card runs, and by clicking a sentence in the monthly report and landing on Carmen saying the thing that caused it. The commercial line under it: nothing in here saves you a heroic number of hours, and we will not pretend otherwise. What it does is make the record exist. When the next account manager starts, the agency brain is a file they can read, not five people they have to interview.

---

## MVP 1 - The Handoff — any call in, the right handoff out

**Paste a call transcript into one Slack channel and the right handoff comes back out: a drafted recap in your own template voice, action items with owners and due dates, ClickUp tasks, the files in the right Drive tier, and the team told in Slack — all behind one approve/edit card.**

*Effort: 2.3 days. Status vs previous plan: Materially STRONGER, plus two new burdens and one absorption. (1) The trigger stopped being mocked: the client copied a full transcript out of Fathom by hand and it worked perfectly, so intake is now a deliberate human paste — a step Gisselle already performs — instead of E2M's own Sept 2 recording standing in. (2) Drive filing writes for real: client folders are confirmed to be in a Shared Drive. (3) Drafting voice is grounded in the real 'Full service email templates' folder instead of an invented tone profile. (4) NEW NON-NEGOTIABLE: every Drive write now carries an internal-vs-client-facin*

### The problem today

Every client interaction at Wedding Industry Ads produces the same six artifacts, and one contractor assembles all six of them by hand, one call at a time.

Whitney described the entire chain in a single unbroken sentence on Sept 2 @6:54, without being prompted for a process walkthrough: "Since our last account, like, our most recent account manager that left, we've We've shifted things, right, to where, like, I'm pretty much doing all of the client onboarding calls now. I'm doing all of the client strategy calls now. So it's like, it's my Zoom, my, you know, note taker, my recordings, all of that. And so then after those calls, Gisselle is then uploading the recordings to the client folder, checking the meetings for action items, four action items, then assigning them to team members in ClickUp, letting them know in Slack, drafting a recap email for the client, and including action items there, and attaching the recording." ("four action items" is a transcription artifact for "for action items.")

That is seven steps off one trigger, and the audit sheet confirms them independently from Gisselle's own seat. TASK-07 (MED): "Depending on the call (general strategy call or onboarding meeting) use the appropriate email template to send a recap to the client) Also need to download assets like recording, transcript and summary from Zoom to Google Drive (client's folder)" — time per task "Depending on the email", frequency "Depending on # of calls", monthly hours blank. TASK-14 (MED): "Downloading and uploading client assets like recording, transcript and summary to client's drive" — 15 min, frequency "varies". TASK-06 (MED): "Create a bullet list of action items per team member that came up during the meeting. Create tasks in ClickUp with description for these tasks and assign to team members with due dates. (Gisselle to review first)" — 1 hr x 4 Mondays, "4 (max)" hrs/month, the only row in this cluster with a number in it at all.

The signature branch of the same engine is TASK-08 (MED): "When a client signs up, drafting welcome email, duplicating a checklist for them and assigning due dates once their kickoff call and messaging and positioning calls are scheduled" — "2 hours, depending", frequency "Depending on clients onboarding". Whitney walked the same sequence on Sept 2 @21:34: "creating, like, emailing the client with a copy of their kind of signed contract. And their link to book their ads kickoff call, creating a folder for the client in our Google Drive and uploading all of the necessary assets there... then she's creating a Slack channel, particularly for that client's account. You know, she's sending a message to the team in Slack, letting them know, hey, this new client has signed on. Here are, like, key things that you need to look at for them, like their onboarding questionnaire and, you know, sales call recordings."

The cost is not primarily hours — it is that the record only exists if one person remembers to make it. Whitney named the consequence herself on Aug 26 @16:54: "we have a lot of meetings with our clients over zoom and still after those meetings take place, even though there's an AI. It's still all on us to write a recap to the client, to then disperse that information to the team, make sure that it's consumed, create action items based on that, and then chase those action items and make sure that they actually get done, and then get back to the client on saying, hey, this is done sort of thing." Four of the six artifacts in that sentence have no monthly-hours figure anywhere in the sheet. The sheet quantifies 18.1 hrs/month in total across twelve rows; five of the six rows this card covers are among the unquantified ones.

Two structural facts make it worse than a throughput problem. First, the assembler is an outside contractor capped at ~25 hrs/week. Second, the record she assembles is the only durable trace of what was agreed — which is exactly the thing the Aug 11 driver was about ("We have the agency brain"). Today, if she stops, the trace stops.

### Evidence

- **Call Sept 2, 2026 @6:54 (labelled Whitney Hodges; content confirms Whitney — she is describing her own Zoom and her own calls)** - "Gisselle is then uploading the recordings to the client folder, checking the meetings for action items, four action items, then assigning them to team members in ClickUp, letting them know in Slack, drafting a recap email for the client, and including action items there, and attaching the recording."
  - *Establishes:* The whole card in the client's own words, in one breath. This is why TASK-07, TASK-14 and the client half of TASK-06 are one build and not three cards: one trigger, seven outputs. Presenting them separately lets Whitney pick a third of a system that delivers nothing alone.
- **Call Sept 2, 2026 @8:01 (Whitney Hodges), answering Minu's human-in-the-loop question** - "Yeah, we'll review any drafts before they go out."
  - *Establishes:* The terminating condition of every leg. Nothing sends. The engine's last step is always a Slack review card, never a send call. Standing constraint since the Aug 11 discovery call.
- **Call Sept 2, 2026 @24:09 (Whitney Hodges)** - "at this point, like, the trigger is that, like, we see in the inbox that they have signed the contract and paid the invoice"
  - *Establishes:* The signature trigger is a conjunction — contract signed AND invoice paid — not either alone. Two Dubsado alerts must be correlated to the same client before the onboarding branch fires. A parser that fires on the first alert it sees is wrong.
- **Call Sept 2, 2026 @23:38 (Whitney Hodges)** - "we get alerts in the Gmail inbox when they have signed the contract and have paid the invoice"
  - *Establishes:* The production signal is a Gmail filter on hello@weddingindustryads.com, not a Dubsado API call. File 03 lists Gmail scope on hello@ under NOT REQUESTED, and Dubsado API under unavailable — so the correct long-term design is available but the credential for it is not. Named as an ask, not silently dropped.
- **Call Sept 2, 2026 @19:59 (Whitney Hodges)** - "if they're just doing the foolproof follow-up advantage, which is our, like, lead lock GHL offer, then that's its own thing, versus if they're signing on for ads management as well, then it's like, we're going off both of those onboarding templates, if that makes sense."
  - *Establishes:* ClickUp template selection is offer-dependent and can select TWO templates at once. Requires the offer name off the alert, and a ClickUp Member seat — file 03: 'a Member seat, not Guest (Guests cannot open templates)'. A Guest seat kills this leg outright.
- **Call Sept 2, 2026 @27:38 (Whitney Hodges)** - "we have a template email that we use that attaches their countersign contract for their records, includes a link for them to be able to book their ads kickoff call with me, and it includes an onboarding questionnaire"
  - *Establishes:* The welcome email has three payloads, one of which (the questionnaire) we do not have. Two of the three are obtainable; the third is the single highest-priority Drive lookup.
- **Call Sept 2, 2026 @29:46 (Whitney Hodges)** - "we will download it from Dipsado and Gisselle will save it in the client's Google Drive folder"
  - *Establishes:* The client described the filing mechanism that means the missing questionnaire is probably already in the Ridgefield folder we were just granted. Look before re-asking.
- **Gisselle Jimenez, client reply, Sept 5-7 2026 (file 05 §1), verbatim** - "Shared Ridgefield's client folder (The wia+ridgefield sub-folder is the one shared with the client). I have invited you to our shared drive where we keep all of our files."
  - *Establishes:* Two facts. (1) Client folders are in a Shared Drive, so ai@ can genuinely create and upload — the filing leg is a real write, not a proposed-path stub. (2) An internal client folder CONTAINS a client-visible subfolder, so every Drive write needs an explicit tier flag. Writing to the wrong tier leaks internal material to a client.
- **Technical probe finding, file 05 §2 — bootstrap JSON from both Fathom share pages (call_id 566502955 and 801737343)** - "canDownload: false · downloadVideoUrl: null · activateDownloadUrl: null · access: external_view_only"
  - *Establishes:* Export was UNAVAILABLE to Gisselle. She did not ignore the 'use export not copy-paste' instruction in the Sept 3 access email. This must be said out loud on stage and in the follow-up; it converts an unmet request into a vendor-side finding.
- **Technical probe finding, file 05 §2 finding 3** - "https://fathom.video/calls/{id}/copy_transcript?token={share_token} returns HTTP 200 unauthenticated, JSON with html and plain_text fields"
  - *Establishes:* The transcript IS retrievable — but via an undocumented, unauthenticated endpoint behind Cloudflare that could be tightened at any time. Hence the intake design: a deliberate human paste is the primary path, and this endpoint is a best-effort convenience, never a dependency.
- **Technical probe finding, file 05 §4d — verbatim from the transcript the client copied out of Fathom, one of three such lines** - "ACTION ITEM: DM Jillian new VIP day link - WATCH: .../calls/566502955?timestamp=534.9999"
  - *Establishes:* Fathom already hands them action items with clickable deep links, free, today. So extraction cannot be the payoff of the demo — it is the setup. The payoff is the four things Fathom demonstrably does not do: assign an owner, set a due date, deliver anything anywhere, or remember across calls whether it happened. Also fixes our evidence-link convention: adopt Fathom's own ?timestamp= format.
- **Call Sept 2, 2026 @25:50 (Whitney Hodges)** - "it's not like there are multiple team members that do the same things, right? It is just like one person with set responsibilities."
  - *Establishes:* Owner assignment is a lookup, not a judgement call. Google Ads to Carmen, Meta to Jacqueline, creative to Ivy, landing pages and nurture copy to Tina, LeadLock workflows/DNS/A2P to Danielle. The model picks from a closed enum in agency_playbook.md or abstains — it never invents an owner.
- **Call Sept 2, 2026 @42:16 (Whitney Hodges), in the same breath as "so much of our operations are in Slack right now, and that's the way that we're communicating"** - "the team has never, like, fully adopted ClickUp other than to just, like, check off the tasks sort of thing"
  - *Establishes:* We write tasks into ClickUp because the record belongs there, but we never ask anyone to review, discuss or approve anything there. The review surface is Slack. The word 'dashboard' appears zero times in either transcript.
- **Call Aug 26, 2026 @39:36 — transcript labels this Minu Bhatt; content is unambiguously Whitney (first person about her own edits and her own voice; continues @39:55 "it's not things where I'm, like, doing double work" and @40:03 "it sounds like it's in my voice"). Attribution corrected per the file's own warning.** - "For me, the biggest thing is that in a timely fashion, emails are proactively drafted and they cover the bulk of, like, what I want them to say."
  - *Establishes:* The acceptance bar for the drafting leg, stated by the person who will judge it: cover the bulk, don't create double work, sound like her. That is a retrieval-over-real-templates problem, not a voice-model-training problem — which is why the 'Full service email templates' Drive folder is the single most valuable artifact in Gisselle's reply.
- **Call Sept 2, 2026 @32:26 (Whitney Hodges), about the per-client ChatGPT Project Gisselle hand-builds** - "that's more of a push for them than just starting from a blank page at this point. So we don't see it as a long-term solution."
  - *Establishes:* The bar for the absorbed messaging-and-positioning call type. She has already called the Project a band-aid; we replace its INPUT half (the auto-assembled client brief) and do not attempt to rebuild its per-client GPT skills.
- **Call Sept 2, 2026 @31:28 (Whitney Hodges)** - "We just have an account for the hello at weddingindustryads.com. The team members have the login information."
  - *Establishes:* Why the ChatGPT Project cannot be shared: no Team/org account, so Project sharing strips files. Gisselle's error message ("It's not letting me share the chatgpt project. It says it will remove all files from the project") is correct platform behaviour, not a mistake. That loss is permanent, and it is what MVP3's exemplar layer depended on.
- **Call Aug 26, 2026 @19:21 (Whitney Hodges)** - "the biggest thing that I'm looking for at this point, I feel like, is like, how is it all connected? How does it all kind of work together sort of thing?"
  - *Establishes:* The question this card is the answer to. One intake, one engine, one record per client. Four call types demonstrated through the same pipe answers it better than four separate cards ever could.

### What we build

One engine, one intake, one review surface, four demonstrated call types.

INTAKE. A single Slack channel — proposed `#ai-handoff`. Gisselle pastes a transcript into it in whatever form is convenient that day: pasted text, a dropped `.txt`, or a pasted Fathom/Zoom link. Nothing else changes about her day. This is deliberately a human step, and it is a step she already performs — she already opens the call and already copies material out of it. The pipeline is everything downstream of the paste.

ROUTING. The engine reads what kind of call it was and produces the matching handoff. Four call types are demonstrated:

1. `client_call` — Whitney's strategy calls, monthly 1:1s, ads kickoff. Produces the recap email drafted against their own templates, action items with owners and due dates, ClickUp tasks, the recording/transcript/summary filed into the correct Drive tier, the team told in Slack. This is TASK-07 + TASK-14 + TASK-09 in one run.
2. `internal_team_meeting` — the Monday team call. Same engine, no client-facing output at all. TASK-06. This is the safe pilot: if the owner assignment is wrong on a Monday recap, a teammate notices; no client sees anything.
3. `signature_event` — a Dubsado "contract signed" plus "invoice paid" pair for the same client. Produces the welcome email draft with the countersigned contract and the kickoff-call booking link, the offer-appropriate ClickUp onboarding list instantiated with assignees and due dates, the client Drive folder created with the two-tier structure, the per-client Slack channel, and the team announcement. TASK-08 + the filing half of TASK-09.
4. `messaging_positioning` — absorbed from the cut MVP3. Produces the seeded `client_brief.md`: ideal client, differentiators, offer, owners, live URLs. This is the input half of the ChatGPT Project Gisselle hand-builds per client, assembled automatically instead.

WHAT MAKES IT MORE THAN EXTRACTION. Fathom already gives them action items with clickable deep links, free. This engine adds the four things Fathom does not do:
- An OWNER, chosen from a closed roster enum, never invented.
- A DUE DATE, with its basis stated on the card (explicit in the call, or a playbook default).
- DELIVERY — the item actually lands in ClickUp, the file actually lands in Drive, the team actually gets told in Slack, the client recap actually exists as a Gmail draft.
- The TIER GUARD — every Drive write is flagged internal or client-facing, and the client-facing tier sits behind the same approval as outbound email.

ONE REVIEW CARD. Every run terminates in a single Slack card: each output leg with a one-line summary and a link to inspect it, every action item rendered as `owner · due date (basis) · "quote" · [WATCH]`, tier badges on every filing row, and a NEEDS A HUMAN block listing anything the extractor refused to guess. Approve with a reaction, correct with a threaded reply. Nothing leaves until it is approved, and the client recap is a Gmail draft in `ai@` even after approval — it is structurally incapable of sending.

ONE RECORD. Every run appends to `clients/<slug>/client_brief.md` and `clients/<slug>/updates/`. That file is what the rest of the portfolio reads.

### Scope boundary - what is deliberately out

IN SCOPE
- Three intake forms into one Slack channel: pasted text, dropped `.txt`, pasted link. Fathom-copy parser validated against a real client transcript; Zoom parsers written but unexercised (see data position).
- Four call types with distinct output schemas: `client_call`, `internal_team_meeting`, `signature_event`, `messaging_positioning`.
- Recap and welcome email drafted into `ai@` Gmail drafts, grounded in the real "Full service email templates" Drive corpus.
- Action items with owners drawn from a closed roster enum, due dates with a stated basis, and an evidence quote plus timestamp on every one.
- ClickUp task creation and offer-dependent onboarding-template instantiation (contingent on a Member seat).
- Drive filing with a mandatory internal/client-facing tier flag; client-tier writes staged and only moved after approval.
- Slack team announcement and per-client channel creation (contingent on `channels:manage`).
- `client_brief.md` seeding and appending, plus the `updates/` log.
- One Slack review card per run with a needs-a-human lane and a run ledger entry.

DELIBERATELY OUT OF SCOPE, AND WHY
1. Sending anything. No `drafts.send`, no client email, no client DM, no portal post. Whitney, Sept 2 @8:01: "we'll review any drafts before they go out." Standing since Aug 11. This is the hardest constraint in the engagement and we do not want a code path that could violate it.
2. TASK-04's triage half — filing read mail into folders, the nine-symbol starring system, the `waiting` tag, and the follow-up cadence on waiting emails. Reason: no Gmail delegation or API scope on `hello@weddingindustryads.com`; file 03 lists it under NOT REQUESTED, and `ai@` is a different mailbox containing none of the history. Secondary reason worth saying out loud: Gisselle's starring taxonomy was narrated over a screen-share on Aug 26 @27:00 and is already partly automated by filters she half-remembers ("I think I have some automations where they they are tagged automatically"). Rebuilding it from a narration is its own discovery, not a leg of a 2.3-day card. We cover the DRAFTING half of the sheet's #1 HIGH row and we name the rest as an ask.
3. A live Dubsado-to-Gmail trigger. The sample alerts arrived forwarded, so their envelope headers belong to the forwarder, and there is no filter or scope on `hello@`. Signature intake is a paste or file-drop in the demo. There is also no Dubsado API (file 03) — which is fine, because Dubsado is mid-migration to GHL and the Gmail alert signal survives that migration. This is the right long-term design, blocked on one credential.
4. Programmatic questionnaire retrieval from Dubsado. No API. We parse whatever document is filed in Drive.
5. Zoom API access, recording download, or any automatic asset pull. Whitney's personal Zoom, never requested. The recording is referenced by link; the transcript arrives by paste.
6. Chasing humans. This card creates the commitment record; it does not nudge anyone. TASK-10's chase loop is MVP2's commitment tracker, and TASK-13's own sheet text sets the rule: "(Just needs to flag, we will manually follow up)".
7. A dashboard or any new UI. Zero occurrences of "dashboard" in either transcript despite being in the Aug 11 sold scope. Slack is the surface.
8. ClickUp as a conversation or approval surface. Sept 2 @42:16: "the team has never, like, fully adopted ClickUp other than to just, like, check off the tasks sort of thing." We write tasks there because the record belongs there. We ask nobody to live there.
9. Voice-model training or learning from sent mail. Whitney's bar is "it sounds like it's in my voice" — we meet it with retrieval over their real template corpus in the cached prompt prefix. Learning from her actual sent mail requires `hello@`, which we do not have.
10. Rebuilding the per-client ChatGPT Project. We build its input half (the assembled brief). We do not rebuild the per-client GPT skills. Whitney has already called the Project a band-aid she does not intend to keep.
11. Batch or concurrent runs. One transcript, one run, one card. Multi-client concurrency is an Apollo week-1 concern, not a blueprint-demo concern.
12. Portal posts and Canva banners (TASK-11/TASK-12) — MVP2 partial and descoped respectively; no Canva Connect API.
13. Any unapproved write into the `wia+ridgefield`-pattern client-shared subfolder. Non-negotiable, enforced in code, and visible on the demo card.

### Architecture

TRIGGER
A Slack app in Socket Mode (no public webhook — the spine constraint) subscribed to `message.channels` and `file_shared` on one channel, `#ai-handoff`. Three intake branches, dispatched by sniffing the event:
- Message text over ~400 chars containing 3+ lines matching the timestamp-speaker pattern → treat the body as a transcript.
- `file_shared` with a `.txt` / `.vtt` → `files.info`, then GET `url_private_download` with `Authorization: Bearer xoxb-…`.
- A bare `fathom.video/share/{token}` URL → best-effort GET `https://fathom.video/calls/{id}/copy_transcript?token={token}` (probe-verified HTTP 200 unauthenticated, JSON `{html, plain_text}`). On any non-200 the bot replies in-thread asking for a paste. A `zoom.us` URL gets an immediate reply asking for the `.txt` — we have no Zoom scope and will not pretend otherwise.
An optional threaded reply `type: client_call | internal | signature | messaging` overrides the classifier.

STAGE 1 — NORMALIZE
`normalize(raw) -> {utterances[], events[], source_system, parser_id, coverage}`. `Utterance = {t_seconds, speaker_raw, text, deep_link|null}`.
- Parser P1 (Fathom copy, VALIDATED against the real Feb 12 transcript): header regex `^\s*@?(\d{1,2}:\d{2}(:\d{2})?)\s*-\s*(.+?)(?:\s*\((.+)\))?\s*$`, body = following indented lines until the next header. `ACTION ITEM:` and `SCREEN SHARING:` lines are pulled into `events[]` with their `?timestamp=` float, and are NOT fed to the extractor as utterances — they are the control group we display beside our output, not an input we launder.
- Parser P2 (Zoom, WRITTEN, UNEXERCISED): two sub-parsers — WEBVTT (cue number, `HH:MM:SS.mmm --> HH:MM:SS.mmm`, then `Speaker: text`) and flat `HH:MM:SS Speaker Name: text`.
- Selection by sniffing the first 40 lines. If no parser achieves >=80% line coverage, the run ABORTS into the needs-a-human queue and Slack shows the first ten unparsed lines. It does not half-parse and proceed.
- Speaker identity: match `speaker_raw` against `team_roster.yml` (seven named people plus aliases). We do NOT use the `(weddingindustryads.com)` suffix as the internal/external test — the probe shows Jacqueline hosts on `jacquelinehood.com` and renders `Jacqueline Hood (Jacqueline Hood)`, so the domain heuristic silently misclassifies a core team member.

STAGE 2 — CLASSIFY, then EXTRACT (two calls, Anthropic Messages API)
`POST https://api.anthropic.com/v1/messages`, `anthropic-version: 2023-06-01`, model `claude-opus-5` for both, `thinking: {type: "adaptive"}`.
- Classify: `output_config: {effort: "low"}`, `max_tokens: 512`, forced single tool `classify_call` with `strict: true` returning `{call_type, subtype, client_guess, confidence, evidence: {quote, t_seconds}}`.
- Extract: `output_config: {effort: "high"}`, streamed, `tool_choice: {type: "tool", name: "<call_type>_handoff"}`, `strict: true`, `additionalProperties: false`, every field `required`.
- Prompt layout for cache economy: `tools` (the schemas) → `system` (agency_playbook.md: the roster enum, the due-date rules, the two-tier filing rules, the template index) → cached template corpus excerpt → `cache_control: {type: "ephemeral"}` breakpoint → the transcript last. The prefix is byte-stable across runs, so repeat runs read cache. Verify with `usage.cache_read_input_tokens`; if it is zero on the second run, something volatile leaked into the prefix.
- `client_call_handoff` schema: `client{name, drive_folder_id|null, slack_channel|null, confidence}`, `recap_email{template_id, subject, body_md, attachments[]}`, `action_items[]{text, owner_slug (ENUM: whitney|gisselle|carmen|jacqueline|ivy|tina|danielle|client|null), owner_confidence, due_date, due_basis (explicit|playbook_default), client_facing, evidence{quote, t_seconds, deep_link|null}}`, `filing[]{artifact_type, tier (internal|client_facing), target_path, source}`, `slack_announcement{channel, text}`, `brief_updates[]{section, value, evidence}`, `abstentions[]{field, reason, candidates[]}`.
- `owner_slug` is a closed enum built from Sept 2 @25:50. The model either picks from it or emits `null` plus a reason, which routes to the abstain lane. It cannot write a name that is not on the roster.
- Due dates come from `agency_playbook.md`: an explicit date in the quote wins; otherwise a client-facing commitment defaults to +3 business days and an internal build task to +5. `due_basis` records which, and the Slack card shows it, so a wrong default is visibly a default.
- Abstain thresholds: `owner_confidence < 0.75`, or a client match below 0.8, or two roster candidates within 0.1 → the item goes to NEEDS A HUMAN with its candidates listed. It is never guessed.

STAGE 3 — STAGE THE OUTPUTS (pre-approval, reversible only)
- Gmail draft on `ai@`: `POST /gmail/v1/users/me/drafts`, base64url RFC-2822 MIME. Never `drafts.send`. Scope `gmail.compose` only — there is deliberately no send scope on the token.
- Drive v3, OAuth on `ai@`, `supportsAllDrives=true`, explicit `driveId`. Every `files.create` carries a required `path_tier`. The tier resolver walks the parent chain and REFUSES the write if `tier=client_facing` resolves outside a `wia+<client>` shared subfolder, or if `tier=internal` resolves inside one. Client-tier artifacts are created in an internal `_staging` folder and only relocated post-approval via `files.update` with `addParents`/`removeParents` — so a mis-tiered file is never even briefly visible to a client.
- ClickUp v2, personal token on `ai@` (`Authorization: pk_…`): `GET /api/v2/team/{team_id}/taskTemplate?page=0` to read the real onboarding templates (Member seat required), `POST /api/v2/list/{list_id}/taskTemplate/{template_id}` to instantiate, `POST /api/v2/list/{list_id}/task` with `assignees[]` and `due_date` in ms epoch. Staged as a preview payload, not created, until approval.
- GHL v2, Private Integration Token (`Authorization: Bearer pit-…`, `Version: 2021-07-28`): read-only contact/opportunity lookup to resolve a client name to a record.

STAGE 4 — THE REVIEW GATE (the only surface)
One `chat.postMessage` Block Kit card per run:
`Handoff · client_call · Ridgefield · 34 min · run 0142`
- `EMAIL DRAFT · recap · template: post-strategy-call · [open draft]`
- `ACTION ITEMS (5)` — each row: `Tina · due Sep 11 (playbook +3d) · "…verbatim quote…" · [WATCH 8:54]`
- `FILING (3)` — each row with a badge: `INTERNAL transcript → /Clients/Ridgefield/Calls/` and `CLIENT-FACING summary → /Clients/Ridgefield/wia+ridgefield/` (the client-facing rows are collapsed under the same approve button as the email)
- `CLICKUP (5 tasks, list: Ads Onboarding – Ridgefield) · [preview]`
- `SLACK · #client-ridgefield · [preview text]`
- `NEEDS A HUMAN (1)` — `owner unresolved: "prep the shorter lead form" · candidates: Tina, Danielle`
Gate mechanics are poll-based, per the spine: `:white_check_mark:` approves, `:pencil2:` opens correction mode, `:x:` discards; threaded `edit: owner[3] = tina` / `edit: due[2] = 2026-09-15` replies are parsed by the app. No interactive-endpoint URL, no public webhook. On approve, the delivery worker executes ClickUp creates, the Slack announcement, channel creation, and the client-tier file relocation — each idempotent on `run_id + item_hash`.

STATE AND LEDGER
`clients/<slug>/client_brief.md` (YAML front matter plus sections: offer, ideal client, differentiators, owners per workstream, live URLs, filed-artifact index with tiers, open commitments) and `clients/<slug>/updates/<ISO8601>-<run_id>.md`. Every card in the portfolio reads the brief; every card appends. A staleness job posts a confirm-or-correct card for any brief field older than 30 days. `runs.sqlite` records run_id, source_system, parser_id, coverage, call_type, model, cache-read tokens, latency, items extracted, items abstained, human edits per field, approved_at — which is what makes the 30-day backtest and the accuracy numbers in success criteria measurable rather than asserted.

### Data position

REAL, IN HAND, AND USED IN THE DEMO
- The Feb 12 Google Ads office-hours transcript, copied out of Fathom by the client, in full. Probe-verified provenance: `call_id` 566502955, title "Google Ads Office Hours - 2.12.26", host `carmen@weddingindustryads.com`, `is_multi_user: true`, `started_at` 2026-02-12T17:00:06Z, 2881s, `state` finalized. Format `timestamp - Speaker Name` plus indented body, with three inline `ACTION ITEM:` lines and `?timestamp=` deep links. This is a real client-system transcript containing real client names, real account changes and real spoken commitments.
- Both E2M weekly-sync transcripts, in the same Fathom convention, as the `internal_team_meeting` sample.
- The Ridgefield client folder plus the entire company Shared Drive, including the confirmed two-tier internal/client-facing structure.
- The "Full service email templates" Drive folder — a real voice corpus for the recap and welcome drafting, replacing what would otherwise have been an invented tone profile.
- Forwarded Dubsado "contract signed" / "invoice paid" notification text.
- The Canva monthly report (an /edit link — treated as READ-ONLY by policy; it is a write-capable link into a live client asset and `ai@` must not modify it).

MOCK OR STAND-IN, AND HOW IT IS DISCLOSED
The rule we are holding ourselves to: every mock is labelled on the artifact itself, not only in Jainil's narration, so a screenshot taken out of the room stays honest.
1. INTAKE AUTOMATION — there is none, and this is the headline disclosure. Said in these words: "Intake is a deliberate human paste, not automated ingestion. And Gisselle did not ignore our export instruction — export was unavailable to her: `canDownload: false` on both share links, `downloadVideoUrl: null`, `access: external_view_only`. We asked for the wrong thing." That is a credibility gain, not a deflation: the paste is a step she already performs, and it collapses her six-step chain to one.
2. SIGNATURE TRIGGER — a manual paste/file-drop, not a live Gmail filter. The card header reads `TRIGGER: manual (Gmail scope on hello@ not granted)`. We never asked for it; that is our gap, not theirs.
3. THE ONBOARDING QUESTIONNAIRE — the payload of the welcome-email attachment, the Slack team announcement, and the `client_brief.md` seed. Not received. Gisselle's own described mechanism (Sept 2 @29:46) puts it in the Ridgefield Drive folder we now have, so the first action of the day is a Drive inventory, not a re-ask. If it is not there by Tuesday, we run on a stand-in document rendered with a visible `STAND-IN — real questionnaire not yet located` band on the Slack card and in the drafted email body.
4. THE ZOOM PARSER — written, unexercised. File 05 asserts Fathom's copy output and Whitney's Zoom `.txt` share the same shape, but no Zoom `.txt` has ever been observed and Zoom's native transcript is a different product (VTT/cue-numbered, or `Speaker: text` with `HH:MM:SS`). So "one normalizer serves both source systems" is presented as a DESIGN INTENTION, not a verified fact — stated in exactly those terms. This matters more than it sounds: Whitney runs every client call on her own Zoom (Sept 2 @6:54, "it's my Zoom, my, you know, note taker, my recordings, all of that"), so Zoom is the highest-value corpus and the one we have not parsed.
5. THE CLIENT-CALL LEG'S INPUT — pending the Zoom `.txt` Gisselle offered. Fallback if it does not arrive: run the `client_call` route on Erin Smith's segment of the Feb 12 transcript (roughly 9:22 to 33:00), which is a genuine 1:1 client working session with a real named client and real commitments made out loud, labelled on the card as `source: office-hours 1:1 segment, not a strategy call`. Honest caveat inside the caveat: that segmentation is inferred from the flow and there is an unaccounted 33:00-35:00 gap, so the boundary is our reading, not Fathom's metadata.
6. TIMESTAMP DEEP LINKS — clickable `?timestamp=` links exist only for Fathom-sourced material. A Zoom `.txt` has no shareable player URL, so citations degrade to bare `@MM:SS`. The renderer emits a link when one exists and a bare timestamp when it does not, and the card says which.
7. EVERY CONNECTOR LEG — ClickUp write, GHL read, Slack post, Members Portal — is mock until invites are accepted and permission levels verified. Invites are sent; acceptance and levels are not confirmed.

STILL NEEDED, AND FROM WHOM
- Gisselle, today, one reply: the Zoom `.txt` — not the summary, because a summary strips the verbatim quotes and speaker turns the extractor needs and MVP5's reel scripts are built on — from a real client strategy or onboarding call.
- Gisselle, same reply: confirmation that the forwarded set contains BOTH alert types. Whitney's gate is a conjunction (Sept 2 @24:09), so one alert type is not enough to build the trigger.
- Gisselle, same reply: the offer name exactly as it appears on the Dubsado alert, since template selection is offer-dependent and can select two templates (Sept 2 @19:59).
- E2M, first action of the day: the Ridgefield Drive inventory — the questionnaire, live landing-page URLs (which also feed MVP3/Page Check), and the internal-versus-client-facing boundary.
- E2M, within the hour each invite is accepted: verify ClickUp seat is Member not Guest (Guests cannot open templates, which kills the offer-dependent leg outright), GHL is Agency Admin, and the Slack grant carries `channels:manage` for the per-client channel.
- Named as an ask, not silently dropped: Gmail delegation or API scope on `hello@weddingindustryads.com`. Without it, the sheet's #1 HIGH row stays half-covered and the production signature trigger cannot be shown at all.

### How it connects to the rest

This card is the trunk, and the central argument of the whole document rests on it: twelve audit rows plus the workstreams the audit never touched collapse onto about six builds sitting on one spine, and this card pays for the spine.

WHAT IT PAYS FOR (~1.25 of its 2.3 days), which the other four then use for free: the strict JSON tool-schema extractor with `call_type` routing and a source timestamp on every fact; the transcript normalizer; the confidence/abstain lane that routes low-confidence or ambiguous-owner items to a needs-a-human queue instead of guessing; the poll-based Slack review gate; the connector layer (ClickUp v2, Drive v3, Gmail drafts on `ai@`, Slack, GHL Private Integration Tokens); `client_brief.md` plus the `updates/` append log; the staleness confirm-or-correct job; `agency_playbook.md`; and the run ledger with its 30-day backtest.

HOW THE SIBLINGS ATTACH
- MVP2 ("What we changed, what we promised, who showed up") is this exact engine with `call_type: office_hours`. Its genuine increments are three output schemas, a GHL Communities roster join (this card never joins against external state), and cross-run commitment lifecycle state (this card has no cross-call memory). Everything else is reused wholesale, which is why it costs 0.7d and not 2.0d.
- MVP4 (executive summary) reads `client_brief.md` and `updates/` for its cause layer. This is the sharpest interconnection in the portfolio: Whitney said of Tina's monthly reporting on Sept 2 @33:01, "We're adding in additional context about like the why behind it all" — written from memory today. MVP2's change log, filed into the record this card creates, is what turns that sentence from remembered into sourced. Clicking a cause sentence in the monthly report lands on Carmen saying the thing that caused it.
- MVP5 (one voice note) consumes client-call transcripts this card has already normalized, stored and tagged, so its input is a by-product rather than a new intake.
- MVP3 (Page Check) deliberately shares nothing but the Slack review surface and the run ledger. That is the point: one card ships even if every connector stays mock. It also consumes the live landing-page URLs this card writes into the brief.

WHAT IT WRITES BACK TO `client_brief.md`
Offer and the ClickUp template path selected; owner per workstream; the filed-artifact index with its tier flag; open commitments with owners and due dates (which MVP2's tracker then ages); live URLs (which MVP3 crawls); and client-praise candidates flagged with their timestamps (which MVP5 mines).

WHAT IT RETIRES
The hand-built per-client ChatGPT Project's input half. Gisselle assembles that today from the questionnaire plus the messaging-and-positioning transcript (Sept 2 @29:46). The absorbed `messaging_positioning` call type assembles it automatically for ~0.15d, recovering the most defensible half of the cut MVP3.

AND THE ANSWER TO HER STANDING QUESTION
Aug 26 @19:21: "how is it all connected? How does it all kind of work together sort of thing?" We do not answer that with an architecture diagram — her AI literacy is low and a working thing she can see beats a diagram. We answer it by running four different call types through one pipe into one channel, and letting her watch Ridgefield's client record fill up as each one lands.

### Effort

2.3 engineer-days of the 4.0 real days available before the Sept 10/11 blueprint review, split as ~1.25d shared spine plus ~1.05d card-specific.

SPINE (~1.25d, amortized across all five cards, paid here)
- 0.30d — Slack Socket Mode app, three intake branches, `#ai-handoff` wiring, file fetch.
- 0.25d — normalizer P1 (validated) + P2 (Zoom, unexercised) + coverage-abort path + roster matching.
- 0.30d — extractor harness: tool schemas with `strict: true`, forced `tool_choice`, cache-prefix layout, abstain thresholds, evidence-link renderer.
- 0.20d — Slack review card, reaction gate, threaded-edit parser, needs-a-human block.
- 0.20d — connector layer with idempotency keys, `client_brief.md` + `updates/` store, `runs.sqlite`, `agency_playbook.md`.

CARD-SPECIFIC (~1.05d)
- 0.25d — four call-type schemas, classifier, due-date rules.
- 0.20d — template-corpus retrieval and recap/welcome drafting.
- 0.20d — ClickUp template instantiation, assignee and due-date logic.
- 0.20d — Drive two-tier resolver, `_staging` + move-on-approval, refusal path.
- 0.05d — Slack announcement and per-client channel create.
- 0.15d — `messaging_positioning` brief seeding (the absorbed MVP3 input half).

BUDGET HONESTY. 2.3 + 0.7 + 0.5 + 0.25 + 0.25 = exactly 4.0 days. There is zero slack in the portfolio, and half a day is already reserved for rehearsal and pre-generating artifacts. If a connector permission comes back wrong, the first thing that gives is this card's ClickUp leg (degrading to a preview payload only), then the Slack channel-create leg. Both degradations are visible on the card and cost nothing else. The two legs we will not degrade are the review gate and the tier guard.

TIME TO VALUE IF APOLLO PROCEEDS. The internal-meeting call type is production-safe on day 1 of week 1 — no client exposure, so a wrong owner is caught by a teammate. The client-facing legs go live once Gmail scope on `hello@` and verified connector permissions are in place.

### Demo beats

1. OPEN, 15 seconds, before anything runs. "Two corrections before I show you anything. First: we asked Gisselle for Fathom exports. That was our mistake — export is switched off on those share links, canDownload is false, there was nothing for her to export. She copied the transcript out by hand instead and it works perfectly, so we redesigned around the copy. Second: because of that, the intake here is a human paste. It is not automated ingestion, and I am not going to pretend it is."
2. BEAT 1 — the paste. Jainil switches to Slack, opens #ai-handoff, and pastes the Feb 12 Google Ads office-hours transcript into the message box. Enter. "That is the whole human step. It is a step Gisselle already does — she already opens the call and already copies things out of it. Everything after this is the pipeline."
3. BEAT 2 — the control group, on screen, before our output. Jainil scrolls the pasted text to Fathom's own three lines: ACTION ITEM: DM Jillian new VIP day link. "Fathom already gives you this, free, today, with clickable timestamps. So extraction is not the demo. Watch what these three lines do not have."
4. BEAT 3 — the card returns. "They have no owner. No due date. They are not in ClickUp, not in Slack, not in a client folder, not in an email to the client, and next Thursday nothing remembers whether any of them happened." He points at the card: Carmen, due Sep 11, basis playbook +3 days, with the verbatim quote and a WATCH link. He clicks the WATCH link and lands on Carmen saying it. "Every fact on this card is one click from the moment someone said it."
5. BEAT 4 — the tier guard, and this is the beat that reads as a correctness feature rather than a feature. He points at two filing rows with different badges: INTERNAL transcript, and CLIENT-FACING summary staged for /Clients/Ridgefield/wia+ridgefield/. "Gisselle told us the wia+ridgefield sub-folder is the one shared with the client. So the client-facing file is not written yet — it is staged internally and sits behind the same approve button as the email. If we get the tier wrong, we leak your internal notes to your client. The code refuses the write rather than guess."
6. BEAT 5 — the abstain lane. He points at NEEDS A HUMAN (1): owner unresolved — "prep the shorter lead form" — candidates Tina, Danielle. "It could have guessed. It did not. One row, in a queue, with the two candidates and the quote. That is the design: a wrong owner costs you a chased task, and we would rather hand you one blank than five confident wrong answers."
7. BEAT 6 — approve, and the delivery happens. He adds the white_check_mark reaction. The ClickUp tasks appear with assignees and due dates, the client-tier file moves out of staging into the shared subfolder, the Slack announcement posts, and the recap sits in ai@ as a Gmail draft. "Note what did not happen. Nothing sent. That draft is in a mailbox with compose scope and no send scope — it cannot send, structurally, not just by policy."
8. BEAT 7 — the second paste, same channel, different call. He pastes the E2M weekly-sync transcript. "Same channel. Same engine. It read that this is an internal meeting, so there is no client email, no client folder, no client-facing tier — just the owners and the ClickUp tasks. That is your Monday recap, TASK-06. And it is the safe place to start, because if it gets an owner wrong on a Monday, a teammate notices and no client ever sees it."
9. BEAT 8 — the landing moment. He pastes a messaging-and-positioning transcript and opens Ridgefield's client_brief.md, which fills in: ideal client, differentiators, owners, open commitments, the artifact index with tiers. "Whitney, on the twenty-sixth you asked how it is all connected. This is the answer. One channel to paste into. One engine that reads what kind of call it was. One file per client that everything writes to and everything reads from. What you just watched build itself is the ChatGPT Project Gisselle hand-assembles for every new client — the thing you called a band-aid you do not want long-term. When your next account manager starts, that file is what they read instead of interviewing five people."
10. CLOSE, said plainly, not buried. "Three things on this card are not real yet and you should hear them from me. The signature trigger is a paste, because we never asked for Gmail access on hello@ — that is our gap and it is in the follow-up. The questionnaire in that welcome email is a stand-in, and it says so on the card, until we find the real one in Ridgefield's folder. And the Zoom parser is written but untested, because no Zoom .txt has reached us yet — and Zoom is where every one of your client calls actually lives. That is one reply from Gisselle away."

### Risks

- ClickUp seat comes back as Guest, not Member. Guests cannot open templates, which kills offer-dependent template selection outright — the single most differentiated part of the signature branch. Mitigation: verify within the hour the invite is accepted; degrade to creating individual tasks from a locally transcribed template list, labelled on the card as "template not readable — task list transcribed by hand". Do not silently substitute and let it look like the real thing.
- No Zoom .txt arrives before the review. The client-call leg then demonstrates on Erin Smith's office-hours 1:1 segment, which is a real client with real commitments but is not a strategy call — and the "one normalizer serves Fathom and Zoom" claim stays unverified against the corpus that holds every single client call Whitney runs. This is the largest single unknown on the card and it is resolvable by one reply today. Mitigation: reply to Gisselle this morning naming the .txt, not the summary, and naming the kind of call.
- The tier guard is the highest-consequence code path on the card and it is being built in 0.2 days against a folder structure we have seen for exactly one client. A parent-chain heuristic tuned on Ridgefield may not generalise to a client folder named differently. Mitigation: the resolver fails CLOSED — an unrecognised path shape refuses the write and files a needs-a-human row rather than picking a tier. Inventory at least two more client folders before Apollo week 1.
- Owner accuracy is unmeasured. We have no hand-labelled ground truth for owner assignment on any transcript yet, so the run ledger's precision column will be empty on demo day unless we label the three transcripts we hold. Mitigation: hand-label the Feb 12 transcript and both syncs during the rehearsal half-day; report the number, whatever it is. A card that claims accuracy without a denominator is the thing Whitney will most reasonably distrust.
- The demo's strongest input is seven months old. The Feb 12 transcript is the only real client-system transcript we have, and Carmen's format, roster and workflow may have moved since. Mitigation: ask for one recent office-hours transcript via the same paste route, both as a generalisation check and so the demo is not entirely retrospective.
- Zero slack in the portfolio. 2.3 + 0.7 + 0.5 + 0.25 + 0.25 is exactly 4.0 days. Any connector surprise consumes capacity that does not exist. Mitigation: pre-committed degradation order is ClickUp create → Slack channel create → Drive client-tier move, in that order, each degrading to a labelled preview. The review gate and the tier guard never degrade.
- Adoption risk exceeds build risk, and this card asks for a genuinely new habit: paste into a channel that did not exist before. Gisselle's own pattern is instructive — she wrote "It's in my task list to automate this somehow but it's complex" and "I tend to forget" on two separate sheet rows. A paste channel she forgets is a pipeline that never runs. Mitigation: the channel is the ONLY new surface, it accepts three sloppy input forms, and the bot always replies — even on failure — so the habit gets feedback every time.
- The extractor may produce plausible action items that were never commitments. Office-hours transcripts are full of hypotheticals and teaching. A card of five confident non-commitments is worse than three real ones. Mitigation: every item requires a verbatim quote and a timestamp, so a fabricated item has to fabricate its own evidence and is visible on inspection; and the demo deliberately shows the abstain row rather than hiding it.
- Whitney has twice said an unranked catalogue paralyses her. A card with eight legs is itself a catalogue if presented as eight features. Mitigation: it is presented as one thing — paste in, handoff out — and legs are shown as consequences of one approval, not as a feature list.
- We are showing a client with low AI literacy a re-scoped design that contradicts the access email we sent on Sept 3. Handled badly, that reads as vendor drift. Handled correctly — leading with "we asked for the wrong thing, here is the probe finding, here is the better design" — it reads as diligence. This is a delivery risk, not a technical one, and it is entirely within our control.

### Production path

WEEK 1 (production-safe immediately, no new credentials)
Ship the `internal_team_meeting` route into the live Monday call. No client-facing output, so the failure mode is a teammate correcting an owner in a Slack thread. This is TASK-06, the only row in this cluster with a monthly number attached ("4 (max)" hrs), and it is where the team's trust in the owner enum and the due-date defaults gets earned before anything touches a client. Instrument every human correction into the run ledger — those corrections are the training signal for the playbook, not for a model.

WEEK 1-2 (unblocked by the two asks already in flight)
Turn on the `client_call` route with the Zoom parser exercised against real `.txt` files. Turn on Drive filing for real, both tiers, with the tier resolver validated against at least three client folder shapes rather than one. Seed `client_brief.md` for every active client by replaying whatever transcripts exist — the brief is worth more when it has history in it, and the replay is nearly free once the pipe exists.

WEEK 2-3 (needs one credential we do not have)
Gmail delegation or API scope on `hello@weddingindustryads.com` converts the signature trigger from a paste into the real thing: a filter on the Dubsado alerts, correlating "contract signed" with "invoice paid" for the same client before firing. Whitney's conjunction gate (Sept 2 @24:09) is then enforced in code rather than assumed. The same credential is what unlocks the rest of TASK-04 — the filing, starring and waiting-tag triage that this card explicitly leaves out — and that is a separate scoped build, not a leg of this one. Note the durability argument in its favour: Dubsado is mid-migration to GHL, and a Gmail-alert signal survives that migration where a Dubsado API integration would not.

WEEK 3-4
Cross-call memory: did the action item from last month's 1:1 actually happen? That primitive is owned by MVP2's commitment tracker and this card consumes it rather than duplicating it — which is the point of the spine. Whitney's Aug 26 @16:54 sentence ends with "get back to the client on saying, hey, this is done sort of thing", and that last clause is the only part of her sentence neither card covers on day one.

BEYOND
Two things stay out of the automation boundary permanently, by design and by the client's own constraint. Sending is human. Client relationship contact is human. Everything this engine does is assemble the record and stage the artifact; a person always presses the button. If the Apollo engagement ever proposes moving that boundary, it should be a deliberate, separately-agreed decision — not a quiet consequence of the pipeline getting good.

### Success criteria

- DEMO DAY, INTAKE: three intake forms — pasted text, dropped .txt, pasted Fathom link — all produce a normalized transcript with >=95% line coverage, or abort visibly with the unparsed lines shown. No silent half-parse.
- DEMO DAY, THE BEAT-THE-BASELINE TEST: on the Feb 12 transcript, the engine returns at least the three items Fathom found, each with an owner from the roster enum and a due date with a stated basis, PLUS at least two items Fathom missed. File 05 §4e names the misses: the primary-to-secondary conversion changes on two accounts, four of the nine negative keywords, and both soft commitments ("I'll send you the link in DMs", "you can come back to me next time with that shorter lead form"). If we cannot beat Fathom's free output, the card does not ship.
- DEMO DAY, EVIDENCE: 100% of action items carry a verbatim quote and a source timestamp. Fathom-sourced items render a clickable ?timestamp= deep link; Zoom-sourced items render a bare @MM:SS and the card says why. Zero items with no evidence.
- DEMO DAY, THE ABSTAIN LANE FIRES AT LEAST ONCE, ON PURPOSE. At least one genuinely ambiguous item appears in NEEDS A HUMAN with its candidate list, rather than being guessed. A demo where the abstain lane never appears has not demonstrated the abstain lane.
- DEMO DAY, TIER SAFETY: zero client-facing Drive writes before approval. Every client-tier artifact is created in _staging and relocated only post-approval. The refusal path is demonstrated live by attempting a deliberately mis-tiered write and showing the code refuse it.
- DEMO DAY, SEND SAFETY: zero send calls of any kind exist in the codebase. The Gmail token carries compose scope and no send scope — verifiable, not just asserted.
- DEMO DAY, CONNECTEDNESS: four call types run through one channel, and Ridgefield's client_brief.md visibly changes after each run. This is the measurable version of "how is it all connected" (Aug 26 @19:21).
- MEASURED, NOT ASSERTED: owner-assignment precision and abstain rate reported as numbers against hand-labelled ground truth on the three transcripts we hold. Target: >=90% precision on non-abstained owners, with the abstain rate reported alongside it rather than hidden. A high precision achieved by abstaining on everything is not a pass.
- WEEK 1 ADOPTION (the real test, and the one the sheet's own comments predict): the Monday internal route runs on four consecutive Mondays without Gisselle being reminded to paste. Her own sheet says "I tend to forget" and "it has happen that I forget to post on time" — a pipeline that depends on a habit she does not form has failed regardless of its extraction accuracy.
- WEEK 4 CORRECTION RATE: fewer than one human edit per approved run, averaged over the month, read straight off the run ledger. This is the operational form of Whitney's own bar (Aug 26 @39:36): "emails are proactively drafted and they cover the bulk of, like, what I want them to say" — and @39:55, no "doing double work".
- THE TURNOVER-PROOFING TEST, which is what they are actually buying: pick any active client and ask whether a new hire could read client_brief.md plus updates/ and know what was agreed, by whom, when, and whether it happened — without interviewing anyone. That is the Aug 11 driver stated as a pass/fail, and it is the only success criterion on this card that is not about hours.

---

## MVP 2 - What we changed, what we promised, who showed up

**The same engine pointed at your specialists' calls: one office-hours transcript in, and out comes a per-client-account record of what was changed and why, every promise made out loud with an owner and a due date, and who actually showed up — written to the client record and to Gisselle's existing sheet, never to a client.**

*Effort: 0.7 days. Status vs previous plan: NEW — never considered before the new evidence. It exists because the Feb 12 transcript exposed a workstream nobody discussed in 92 minutes of discovery. Two deliberate reframings from the challenge that proposed it: it is named for the client account, not for a person ('Nothing lives in Carmen's head' is rejected — on a team with one person per function, a card named after a contractor's head reads as monitoring to the person whose cooperation it needs, and losing Carmen is the exact catastrophe the engagement exists to prevent), and the claim is narrowed — Google Ads ships a free native chan*

### The problem today

Twice every Thursday your specialists run a live session with your accelerator members. Gisselle, Aug 26 @8:16: "So Google Ads office hours are every, both of them are every Thursday. Google Ads are around, I think it's like 11am or 10am CST. And then Meta Ads office hours, it's later in the afternoon, like around 3.30." A Fathom notetaker is in the room — Gisselle, Sept 2 @5:24: "They use Fathom. They use a Fathom note taker." Afterwards, per Gisselle, Aug 26 @8:16: "So after the meeting is hold, then our team members send like a recap in Slack. With a report and a summary."

Three separate manual jobs then run off that one hour.

FIRST, attendance. Gisselle rebuilds the roll-call sheet by hand. Aug 26 @10:36: "we have all the Members here, their consecutive misses, the... Last time they attended, and then I just kind of like check the two-week flag, the four-week flag." On screen-share at @11:06 (the transcript mislabels this line "Whitney Hodges"; she is the one sharing the sheet): "Like manually, I go in and like I have to like copy and paste and then update the date." She has tried twice to automate it and stopped — Aug 26 @6:03: "wasn't able to figure out how we could best, um, automate this" — and wrote the same thing into her own audit sheet, TASK-13 column I: "It's in my task list to automate this somehow but it's complex." TASK-13 is one of only three HIGH-priority rows in the entire sheet.

SECOND, chasing. When a flag fires, she does not just tell the specialist — she builds a second layer of tracking to make sure the specialist actually acted. Aug 26 @14:47: "I also create, like, click-up tasks for them to just, you know, for us to follow up and monitor that they actually send the DM." That is TASK-10, the second HIGH row, in miniature: "Keep track of team members communications in slack and email and follow up if no acknowledgement so things don't slip through." Whitney's own summary of the pattern, Aug 26 @16:54: "It always feels like we're like chasing the team to get done the things that need to get done."

THIRD — and this is the part nobody has ever discussed in 92 minutes of discovery — the work itself evaporates. We read the actual Feb 12 Google Ads transcript. Inside that one 48-minute session Carmen switched outbound-click conversions from primary to secondary on two separate client accounts, added nine negative keywords across them (barn, cheapest, CVS, Opalescence Go, baking soda, homemade, under 5000, at home, banana), committed to setting up a 50/50 A/B experiment for Erin, told Jillian "I'll send you the link in DMs" about a VIP-day rebooking link, and told Erin "you can come back to me next time with that shorter lead form." Our own probe note on that finding is blunt: "None of this lands in ClickUp, Slack, or any client record." It exists in Carmen's head and in a transcript nobody reads again.

The cost of that lands one month later, on a different person. Whitney, Sept 2 @33:01, on the monthly report: "She's like pulling in screenshots from the different ad accounts, pulling in screenshots of best performing ads. We're adding in additional context about like the why behind it all." On the same breath, the process is "not... Automated in any way right now." That is Tina, the first few business days of every month, reconstructing from memory a "why" that was said out loud on a recorded call — 18–24 hrs/month by our derivation, the only duration estimate given for any non-Gisselle work anywhere in either call, and a workstream with no row in the audit sheet at all.

And the structural reason this matters more than the hours: Whitney, Sept 2 @25:50: "it's not like there are multiple team members that do the same things, right? It is just like one person with set responsibilities." One Google person. One Meta person. The knowledge of what was changed on your clients' accounts, and why, currently has exactly one copy each.

### Evidence

- **Aug 26 call @10:36 — Gisselle Jimenez, live screen-share of the roll-call sheet** - "we have all the Members here, their consecutive misses, the... Last time they attended, and then I just kind of like check the two-week flag, the four-week flag."
  - *Establishes:* The exact output shape this card must write into: member, consecutive misses, last attended, 2-week flag, 4-week flag. We are not designing a new artifact; we are filling in one she already maintains.
- **Aug 26 call @11:06 — attributed to "Whitney Hodges" in the transcript, but this is Gisselle, who is the one screen-sharing the sheet at this point** - "Like manually, I go in and like I have to like copy and paste and then update the date."
  - *Establishes:* The task is literal manual row duplication. This is the specific motion the attendance leg removes.
- **Audit sheet TASK-13, column I (client-entered comment), priority HIGH, tools Highlevel + Google Sheets** - "It's in my task list to automate this somehow but it's complex"
  - *Establishes:* She has already nominated this for automation in writing and already judged it too hard. Shipping it is a credibility event, not a time saving — the derivable value is only 2.0 hrs/month.
- **Audit sheet TASK-13, column K (client-entered AI/automation description)** - "Keep track of attendees in our office hours and flag if they haven't attended in 2 weeks so we can DM them or 4 weeks so we can email them. (Just needs to flag, we will manually follow up)"
  - *Establishes:* The client's own spec caps the scope at flagging. The parenthetical is why this card never sends a DM or an email — that boundary is theirs, not ours, and it is what makes a false-absent safe.
- **Aug 26 call @14:47 — Gisselle Jimenez** - "I also create, like, click-up tasks for them to just, you know, for us to follow up and monitor that they actually send the DM."
  - *Establishes:* TASK-13 already contains TASK-10. A fired flag generates a second, hand-built tracking task to verify a human acted. That is the 'did-the-human-do-it' primitive, and this card owns it.
- **Audit sheet TASK-10, column K — priority HIGH, frequency "Every day", total hours BLANK** - "Keep track of team members communications in slack and email and follow up if no acknowledgement so things don't slip through"
  - *Establishes:* The second HIGH row in the sheet, and one of the two HIGH rows whose monthly hours the client could not quantify. The commitment tracker is the buildable core of it.
- **Technical probe finding, file 05 §4d — verbatim from the copied Feb 12 transcript text; two further ACTION ITEM lines and SCREEN SHARING event markers present alongside it** - "ACTION ITEM: DM Jillian new VIP day link - WATCH: .../calls/566502955?timestamp=534.9999"
  - *Establishes:* Fathom already emits action items with clickable deep links, free, today. This is the baseline the extractor must beat, and it is also the citation format we adopt rather than inventing one. Note honestly: this line means Fathom DID catch the VIP-link promise — see scope_boundary for the corrected tally.
- **Technical probe finding, file 05 §4e — our own assessment after reading the full copied Feb 12 transcript** - "None of this lands in ClickUp, Slack, or any client record."
  - *Establishes:* The gap this card closes. Two conversion-setting changes on named client accounts, nine negative keywords and three spoken commitments, all real, all in a recorded call, none of them recorded anywhere a second person could find them.
- **Technical probe finding, file 05 §2 — present on BOTH Fathom share links, alongside downloadVideoUrl: null and activateDownloadUrl: null, access external_view_only** - "canDownload: false"
  - *Establishes:* Export was unavailable TO Gisselle; she did not ignore the instruction. The intake is a human paste by design, and any claim of automated ingestion is withdrawn.
- **Technical probe finding, file 05 §2 — on both share links; the call object exposes 14 fields, and the full payload greps clean for attendee/participant/invitee/guest/roster/member** - "byline "Unknown""
  - *Establishes:* There is no structured attendee data anywhere in Fathom. Attendance can only ever be derived from speaker labels, which is why it ships as a volume-contingent proxy with an abstain lane, not as a fact.
- **Sept 2 call @33:01 — Whitney Hodges, describing Tina's monthly reporting** - "We're adding in additional context about like the why behind it all."
  - *Establishes:* The 'why' is currently a remembered narrative, added by hand, monthly, by the one person who is simultaneously your sole landing-page builder. The change log replaces memory with a sourced record — and it is why this card feeds card 4.
- **Sept 2 call @25:50 — Whitney Hodges** - "it's not like there are multiple team members that do the same things, right? It is just like one person with set responsibilities."
  - *Establishes:* One person per function, no redundancy. Carmen and Jacqueline are two of the four single points of institutional-knowledge failure Whitney named herself, and the audit sheet — twelve rows, all one outside contractor — never touched either of them.
- **Aug 26 call @16:54 — Whitney Hodges** - "It always feels like we're like chasing the team to get done the things that need to get done."
  - *Establishes:* The founder-level framing of TASK-10. The commitment tracker is the narrowest honest answer to it: it records every promise made out loud, with an owner and a due date, and remembers across sessions whether it closed.
- **Aug 26 call @12:00 — WIA side answering Minu's agenda question (the transcript's speaker labels are scrambled across @11:57–@12:08; the answer is Gisselle's)** - "it's really like an open meeting for clients to come in, ask them questions, review their accounts"
  - *Establishes:* The client describes office hours as an open drop-in, NOT a queue. This is the evidence against our own rolling-1:1 reading of Feb 12, and it is why attendance is stated as sound at current volume rather than guaranteed by format.
- **Aug 26 call @13:32 — mislabelled "Minu Bhatt"; the content is the WIA side answering, i.e. Gisselle** - "They just join if they have any questions about their setup. And they can join like at any moment during that hour."
  - *Establishes:* Mid-hour arrivals and departures are normal and expected. Jillian left at 9:19 of a 48-minute call and would score as a full attendee. We say this on screen rather than letting it be discovered.
- **Sept 2 call @13:36 — Minu Bhatt, on the GHL Agency SaaS tier** - "Then most likely we would have an API where we can grab the information directly."
  - *Establishes:* "Most likely" is the strongest statement anyone has made about GHL API availability, and the invite is sent but not accepted. The roster join is the one genuinely unverified dependency in this card, which is why the fallback roster is Gisselle's own sheet.
- **Aug 26 call @19:21 — Whitney Hodges** - "the biggest thing that I'm looking for at this point, I feel like, is like, how is it all connected? How does it all kind of work together sort of thing?"
  - *Establishes:* The standing question three calls old. This card is the half of the answer that fills the client record; cards 4 and 5 are the half that read it. The final demo beat is built specifically to answer this sentence.

### What we build

One more route on the same engine, and one more card in the same Slack channel.

Gisselle pastes an office-hours transcript into the intake channel — pasted text, a dropped .txt, or a share link, whichever is convenient that day. The engine reads that it was an office-hours call rather than a client call, and returns one review card with three blocks.

CHANGED — a per-client-account record of every configuration change stated on the call: what object, what it moved from and to, the verbatim reason as spoken, whether it was done live on the call or merely intended, and a clickable evidence link to the exact second. On Feb 12 that is: outbound-click conversions moved primary → secondary on two named accounts, and nine negatives added, attributed to the account each one belongs to. Note the claim precisely: Google Ads ships a free native change history and Meta logs account activity, so we are not claiming to capture the change. We are claiming the reason, its attachment to a client record, and its arrival in next month's report — none of which any platform log contains.

PROMISED — every commitment made out loud, with an owner, a direction (staff-to-member or member-to-staff), a firmness class, a due date where one was stated, and an evidence link. On Feb 12 that is Carmen's DM'd VIP-day link for Jillian, the 50/50 A/B for Erin, and the standing offer to Erin — "you can come back to me next time with that shorter lead form" — which is a soft offer, recorded but never chased. Each open commitment carries state that survives to the next session: when next Thursday's transcript arrives, an open line either closes itself against what was said, or it is still sitting there.

SHOWED UP — an attendance row per speaker label, fuzzy-matched against the member roster, written into the same five columns Gisselle keeps by hand: member, consecutive misses, last attended, 2-week flag, 4-week flag. Flags fire once on threshold crossing with a cooldown, ranked by consecutive misses, so they surface who to re-engage rather than re-firing on everyone every week. Any label that cannot be resolved with confidence — "Jillian", with no surname, in the only sample we have — goes to a needs-a-human queue with its evidence link and the candidate we were unsure about. It flags. It never DMs. It never emails.

All three blocks sit behind one approve / edit / discard / needs-a-human gate on one Slack message, and nothing writes anywhere until a human reacts. On approval the card writes to three places: the internal client_brief.md for each account touched (an append-only `## Account changes` section and an `## Open commitments` table), Gisselle's existing roll-call sheet, and a ClickUp follow-up task when a flag fires — exactly the task she builds by hand today.

The card is named for the client account, not for a person. There is no per-specialist view, no attendance-of-staff metric, and no performance surface anywhere in it. On a team with one person per function, a tool named after a contractor's head reads as monitoring to the person whose cooperation it needs — and losing Carmen is the exact catastrophe this engagement exists to prevent.

### Scope boundary - what is deliberately out

IN SCOPE
- One office-hours transcript per run, Google or Meta, arriving as pasted text, a dropped .txt, or a pasted share link into the single intake channel.
- Per-client-account change extraction: object, before/after, verbatim stated reason, tense (done on call / done before call / intended), source second, evidence URL, confidence.
- Commitment extraction: text, owner, direction, firmness (explicit / soft offer / conditional), due date where stated, plus cross-run open→closed lifecycle state.
- Attendance capture: speaker labels, first/last second, turn and word counts, fuzzy roster match with score, verdict or abstain; threshold-crossing flags with a cooldown, ranked by consecutive misses.
- Writes, internal tier only: client_brief.md `## Account changes` and `## Open commitments`; Gisselle's roll-call sheet; one ClickUp task per fired flag.
- One poll-gated Slack review card with a visible what's-real / what's-a-fixture strip printed in the card itself.

DELIBERATELY OUT, and why
- ANY message to a member — DM, email, portal post. TASK-13's own text caps it: "(Just needs to flag, we will manually follow up)". This is also the hardest constraint in the engagement: the human touch on client relationships stays human. It is what makes a false-absent harmless.
- ANY client-facing output at all. No recap email, no portal post, no write into a wia+<client> subfolder. Since the reply established that "The wia+ridgefield sub-folder is the one shared with the client", a wrong write leaks internal material to a client. In this card the client-facing tier is not reachable: the tier flag is hard-coded internal and a unit test asserts it. Card 1 owns the gated client tier; this card owns none of it.
- Writing to any ad platform. Read-and-record only. The Google Ads API and Meta Marketing API were never requested (file 03), and a system that can change an account is a different risk class than one that records what a human changed.
- Reconciling the spoken change against the platform's own change history. This is the right eventual product — a discrepancy flag between "said" and "logged" — but it needs ad-API access we do not have and Carmen's buy-in we have not asked for. Named as an Apollo item, not smuggled in.
- Distinguishing "did not attend" from "attended silently and got nothing". Explicitly excluded because it is not derivable from a transcript. The silent listener is precisely the disengaged member the flag exists to catch, and they will score absent. We state that on screen rather than claim a capability we do not have.
- Early-departure weighting. Jillian left at 9:19 of a 48-minute call and scores as a full attendee. Out of scope; disclosed.
- TASK-12's Canva banner and portal upload. The Canva Connect API is unavailable (file 03) and TASK-12 got one broken-off clause of coverage in 92 minutes of discovery, so nothing about its process is client-confirmed. Only the recap-summary CONTENT leg is in scope; the 6.0 hrs/month figure is therefore explicitly NOT claimed as recovered.
- TASK-05 (ClickUp overdue → Slack recap). LOW priority, and it is a configuration of this card's commitment primitive rather than a build. Deferred on purpose so it costs a config change in Apollo week 1 instead of a second build.
- Any per-person or per-specialist performance reporting. Not built, not derivable from these outputs, and named out loud in the card so it survives contact with Carmen and Jacqueline.
- Automated Fathom or Zoom ingestion of any kind. Withdrawn on evidence: canDownload: false on both share links, and the only working transcript endpoint is undocumented, unauthenticated and behind Cloudflare. The paste stays the design, not a stopgap.
- Speaker diarization correction or re-transcription. We consume the source system's labels as given, including "Michael & Diana" as one label for two humans.

### Architecture

TRIGGER — one Slack channel, polled, no public webhook.
A single intake channel shared with card 1. A worker polls `conversations.history` (Slack Web API, bot token, scopes `channels:history channels:read groups:history chat:write files:read reactions:read reactions:write users:read`) with a persisted `oldest` cursor every 30s. Three intake forms are accepted and normalized:
(a) pasted transcript text — taken from `message.text`;
(b) a dropped .txt — `files.info` then GET `url_private_download` with `Authorization: Bearer <bot token>`;
(c) a pasted Fathom share link — best-effort GET `https://fathom.video/calls/{call_id}/copy_transcript?token={share_token}`, which our probe confirmed returns HTTP 200 unauthenticated with JSON `{html, plain_text}`; we use `plain_text`. This path is opportunistic only and is never on the demo's critical path, because the endpoint is undocumented and Cloudflare-fronted. On any non-200 the card replies in-thread asking for a paste.

STAGE 1 — normalizer (spine, reused).
The Fathom copy format is verified from the client's own copied output: a `VIEW RECORDING - 48 mins (No highlights)` header, then `MM:SS - Speaker Name` lines with indented body text, with `ACTION ITEM: … - WATCH: https://fathom.video/calls/{id}?timestamp={float}` and `SCREEN SHARING: {name} started screen sharing - WATCH: …` lines interleaved. Output is a turn list: `{start_seconds, speaker_label, text}`, plus a sidecar list of the source system's own action items and event markers (kept, never merged into our extraction — they are the control group). A Zoom `.txt` parser and a WebVTT parser exist in the same module for cards 1 and 5; this card's input format is the one that has actually been observed, so no unverified parsing sits on this card's path.

STAGE 2 — segmentation (new in this card).
Changes must be attributed to the right client account, so the transcript is cut into per-member segments using three signals in priority order: (1) `SCREEN SHARING` event markers as boundary candidates; (2) change-points in the non-staff speaker label; (3) vocative and farewell cues — Carmen's "Hey, Erin." at 9:22 is an explicit handoff, and a goodbye at 9:19 closes the prior segment. The model call confirms or adjusts the boundaries and returns a confidence per segment. Spans that no signal claims — the observed 33:00–35:00 gap on Feb 12 — are emitted as `unattributed`, never silently absorbed into a neighbour, because our own segmentation of that session is inferred rather than given.

STAGE 3 — extraction, three forced tool schemas.
Anthropic Messages API, `POST /v1/messages`, header `anthropic-version: 2023-06-01`, with `tool_choice: {type: "tool", name: …}` so the model cannot answer in prose. Model pinned in config (an Opus-class model for extraction, a cheaper Sonnet-class for abstain triage). One call per output, each receiving: the normalized turn list for the relevant segment(s), the segment boundaries, the staff list, and — for commitments — the currently open commitments for that account, so it can mark any it hears resolved. Every schema requires a `source: {start_seconds, speaker_label, evidence_url|null}` on every emitted fact; `evidence_url` is rendered in Fathom's own `?timestamp=` convention when the source was a share link, and degrades to a bare `@MM:SS` citation when it was a paste with no player URL. That degradation is printed on the card.
- `emit_account_changes(changes[])` — `{client_account:{label, resolved_id|null, confidence}, platform, change_type ∈ {conversion_action_primary_to_secondary, negative_keyword_added, budget, campaign_status, bid_strategy, audience, creative, other}, object, before|null, after|null, stated_reason|null, reason_quote|null, tense ∈ {done_on_call, done_before_call, intended}, source, confidence}`. Hard rule: a change with `stated_reason: null` is still written, but labelled "reason not stated on call" — that absence is itself the signal Tina needs.
- `emit_commitments(commitments[])` — `{text, owner_label, owner_class ∈ {staff, member, unresolved}, beneficiary_account, direction, firmness ∈ {explicit, soft_offer, conditional}, due:{kind ∈ {date, relative, next_session, none}, value}, source, confidence}`. The `soft_offer` class exists specifically because "you can come back to me next time with that shorter lead form" is an offer, not a task; soft offers are recorded and never chased.
- `emit_attendance(session, observed[], unattributed_spans[])` — `observed` rows carry `{speaker_label, first_seconds, last_seconds, turn_count, word_count, is_staff, roster_match:{member_account_id|null, matched_name, score, method}, verdict ∈ {attended, abstain}}`. A label counts as attended at `turn_count ≥ 2 AND word_count ≥ 40`, thresholds calibrated on Feb 12 and stored in config. Staff detection is an explicit allowlist keyed to GHL users, NOT the `(weddingindustryads.com)` domain suffix — the suffix silently misclassifies Jacqueline, whose Fathom host address is `jacqueline@jacquelinehood.com`.

STAGE 4 — roster join and identity resolution (new in this card; the one real unknown).
Primary: GoHighLevel v2 via a Private Integration Token, `Authorization: Bearer <PIT>`, `Version: 2021-07-28`, base `https://services.leadconnectorhq.com`. Probe order within the hour the invite is accepted: (1) confirm the token and location; (2) locate a Communities/memberships roster endpoint; (3) if absent, fall back to `GET /contacts/` against the saved member filter. Fallback of last resort, and it is a good one: the roster is read from Gisselle's own roll-call sheet via Sheets API v4 `spreadsheets.values.get` — she already maintains every member row there by hand, and the sheet is also our write target, so the join and the output share one source of truth.
Matching: lowercase, strip parentheticals and domain suffixes, then (a) exact full name; (b) surname token match; (c) given-name-only, allowed ONLY when unique across the roster; (d) compound labels split on `&`/`and`/`+` and matched to a single member ACCOUNT when both tokens appear on that account's contacts, so "Michael & Diana" resolves as one account rather than failing as two people. Score ≥ 0.90 auto-resolves; 0.70–0.90 abstains WITH a proposed candidate; < 0.70 abstains with none. In the only sample we hold, 2 of 3 member labels land in the abstain band. That is the honest result and it is the designed behaviour, not a failure.

STAGE 5 — cross-run commitment lifecycle (new in this card).
`commitments.jsonl` plus an index, keyed `commitment_id = sha256(normalized_text + owner + beneficiary_account)[:12]` so re-ingesting the same transcript never duplicates a row. States `open → confirmed_done | superseded | expired | dropped`, with three transition sources: a later transcript in which the extractor hears it resolved; a human's `✅` reaction on the Slack line; or age-out. This is the "did-the-human-do-it" primitive file 04 said whichever card ships first should own. Card 1 and TASK-05 both read it rather than reimplementing it.

STAGE 6 — the Slack review card.
One `chat.postMessage` with Block Kit:
  `Google Ads Office Hours · Thu 12 Feb · 48 min · 3 members seen · 1 needs a human`
  CHANGED · Ridgefield — outbound-click conversions primary → secondary · reason: "<verbatim clause>" · [40:29]
  CHANGED · Ridgefield — 4 negatives added: barn, under 5000, at home, banana · [40:29]
  PROMISED · Carmen → Jillian — DM the VIP-day rebooking link · due Fri 13 Feb · [8:55] · ✅ done / ⏳ open
  PROMISED · Carmen → Erin — soft offer, not chased: "come back to me next time with that shorter lead form" · [20:43]
  SHOWED UP · Erin Smith → attended, 9:22–33:00 · Michael & Diana → attended, 35:00–46:58 · Jillian → NEEDS A HUMAN: no surname, one candidate at 0.78
  UNATTRIBUTED · 33:00–35:00 — 2 minutes no segment claims
  REAL / FIXTURE · transcript, changes, commitments, action-item baseline = real · member roster = fixture pending the GHL invite
Decision is polled, not pushed: `reactions.get` on the message ts every 20s. `✅` executes the writes; `✏️` reads `conversations.replies` and re-runs with the human's thread text appended as a correction block; `🚫` logs and stops; `🙋` moves the whole card to the needs-a-human channel. Nothing writes before a reaction.

WRITES on approval.
- Drive API v3, OAuth on `ai@weddingindustryads.com`, scope `drive`: locate the internal client folder with `files.list?q=…&supportsAllDrives=true&includeItemsFromAllDrives=true&corpora=drive&driveId=<id>`, then `files.create?uploadType=multipart&supportsAllDrives=true`. Every write carries `tier: internal`, hard-coded; the `wia+<client>` path is unreachable from this code path.
- Sheets API v4 `values.append` / `batchUpdate` into the roll-call sheet's exact five columns. In the demo this targets an `ai-shadow` tab, so a rehearsal can never touch her live sheet.
- ClickUp v2 `POST /api/v2/list/{list_id}/task` for the flag follow-up, with assignee and due date. Needs the Member seat to be confirmed; this card does not read ClickUp templates, so a Guest seat degrades it only to a logged payload rather than killing it.
- Run ledger `runs/<run_id>.json`: input hash, model and prompt version, raw tool outputs, human decision, every write with the ID the API returned, wall-clock and token cost.

### Data position

REAL, in hand, nothing invented:
- The full Feb 12 Google Ads office-hours transcript — the client's own system, copied out by the client herself, in a format we have parsed. Real member names, two named client accounts, two conversion-setting changes, nine specific negative keywords, three spoken commitments.
- Fathom's three inline `ACTION ITEM:` lines with their `?timestamp=` deep links, and the `SCREEN SHARING` event markers used for segmentation. Real, and used on screen as the control group.
- The Aug 27 Meta session via the same route: two speakers, `host jacqueline@jacquelinehood.com`, title never set ("Impromptu Zoom Meeting"). Real, but a 1:1 support call — a format sample, not an attendance or change-log sample.
- Both share-link bootstrap payloads, including `canDownload: false` and `byline "Unknown"`.
- Gisselle's roll-call sheet column structure, observed on screen-share Aug 26 @10:36–@11:36.
- TASK-13 and TASK-10 as the client wrote them.

MOCK OR STUBBED at demo time, and exactly how each is disclosed:
- THE MEMBER ROSTER. Mocked as a twelve-row fixture in the shape of Gisselle's sheet, because the GHL invite is sent and not accepted, and API availability was only ever "most likely" (Sept 2 @13:36). Disclosed as a line printed in the card itself: "member roster = fixture pending the GHL invite". If the invite lands before Thursday this becomes real; if the Communities endpoint is absent, the roster reads from her sheet and stays real either way.
- THE CLICKUP WRITE. Real if the Member seat is confirmed on acceptance; otherwise the payload is logged and shown, labelled as a stub.
- CROSS-CALL COMMITMENT CLOSURE. There is no second Google office-hours session, so closure is demonstrated by re-ingesting Feb 12 with two synthetic follow-up lines appended — and that appended text is shown on screen and named as synthetic before it is used. This is the one fabricated input anywhere in the card, and it is fabricated for a mechanism test, not for a result.
- GENERALISATION OF THE CHANGE-LOG EXTRACTOR. Not demonstrated positively at all, because the only second sample is a two-person troubleshooting call. What we run instead is the negative test: on the Aug 27 Meta transcript the extractor must return an EMPTY change array with a stated reason, rather than inventing changes to justify itself. We show that result. It is less impressive and more informative.

STATED PLAINLY TO THE CLIENT, before the demo runs:
- Two of these three outputs were never mentioned by anyone in either call. The change log and the commitment tracker are our proposal, not your process reflected back. Roll call is yours, in writing, at HIGH priority.
- Carmen and Jacqueline have never been interviewed. Neither is in this room and neither has seen this.
- The change-log extractor is validated on a single session that is seven months old — recorded before your account manager resigned and before "we're onboarding a lot of clients" (Sept 2 @32:26).
- Google Ads and Meta both log the raw change for free. Our claim is the reason, the attachment to a client record, and the spoken promises. Nothing more.
- Attendance is a proxy that holds at your current volume, not a guarantee from the format. Your own description of office hours is an open drop-in — "they can join like at any moment during that hour" (Aug 26 @13:32) — so a member who joins, listens and leaves silently scores absent, and Jillian, who left at 9:19 of 48 minutes, scores as a full attendee. That is why it flags, a human confirms, and it never contacts anyone.
- Roll call saves roughly 2.0 hrs/month on data with three rows per session. Its value is not hours. It is that it stops being forgotten, and that Gisselle tried twice to build it and could not.

STILL NEEDED, and from whom:
- From Gisselle, today: one RECENT Google office-hours transcript and one recent Meta one, copied the same way she copied Feb 12. This lifts the change-log validation off n=1 and off a seven-month-old sample. Cheap — she has already proved the route works.
- From Gisselle, before flag logic is written: at steady state, how many members are currently past the 4-week flag? This is a spec question, not a caveat. If the answer is "most of them", the correct product is a ranked re-engagement list, not a flag, and we will build that instead. Her own line suggests the volume is low — "right now it's manageable because we have, like, not, like, a large number of members" (Aug 26 @6:03) — but low volume is exactly the condition under which flags fire on everyone.
- From Gisselle: does Carmen or Jacqueline already keep a change note anywhere? If either does, this card integrates with it rather than replacing it.
- From Whitney: fifteen minutes with Carmen and fifteen with Jacqueline. These would be the first fulfilment-side interviews this engagement has conducted, and file 04 names their absence as the engagement's biggest conversion risk.
- From Whitney: a decision on Fathom team-account consolidation. She pre-consented in principle — "if we need to switch to a team account or anything like that, I mean, we, we totally can" (Sept 2 @4:08) — but Jacqueline hosts on her own domain and Whitney does not control that account.

### How it connects to the rest

This card is the clearest proof of the document's central argument: it is a second call_type on the same engine, not a second engine.

REUSED WHOLESALE FROM THE SHARED SPINE (~1.25d, amortised across all five cards): the intake channel and the transcript normalizer; the strict JSON tool-schema extractor over the Messages API with call_type routing; source timestamps on every emitted fact; the confidence/abstain lane and the needs-a-human queue; the poll-based Slack review gate; the connector layer (GHL PITs, Drive v3, Sheets v4, ClickUp v2, Slack); client_brief.md plus the updates/ append log; the staleness confirm-or-correct job; and the run ledger. Card 1 and this card share ONE intake channel and ONE paste. Whether a paste becomes a client recap or an office-hours record is a routing decision the engine makes, not a decision Gisselle makes.

WHAT IS GENUINELY INCREMENTAL, and it is only three things: three output schemas; a join against an external member roster, which nothing else in the portfolio does; and cross-run commitment lifecycle state, which nothing else in the portfolio has. Everything else is already paid for.

TWO PRIMITIVES THIS CARD OWNS FOR THE REST OF THE PORTFOLIO:
1. The commitment lifecycle store. File 04 established that TASK-13 already contains TASK-10 and that whichever card ships first should own the "did-the-human-do-it" primitive. This one ships it. Card 1's client-call recaps read the same store to say whether last month's action items actually closed, and TASK-05 (ClickUp overdue → Slack) becomes a configuration of it in Apollo week 1 rather than a fourteenth automation.
2. The roster join. This is the first place anything in the portfolio matches a transcript label to a row in a system of record, and the fuzzy-match-plus-abstain module it produces is what card 1 will need the moment it has to resolve an action-item owner from a partial name.

WHAT IT WRITES BACK TO client_brief.md: an append-only `## Account changes` section, per platform, each line carrying the stated reason, the tense, and an evidence URL; and an `## Open commitments` table with owner, beneficiary account, firmness, due date and state. Both internal tier, always.

WHO READS WHAT IT WROTE: card 4 — the executive summary — takes the `## Account changes` section as its cause layer, which is the exact leg Whitney says Tina currently writes from memory: "We're adding in additional context about like the why behind it all" (Sept 2 @33:01). That is the compounding claim, and it is the one that turns "how is it all connected?" from a diagram into a click. Cards 1 and 2 fill the record; cards 4 and 5 read it; card 3 seeds from it; card 2 in the portfolio ordering — Page Check — deliberately depends on nothing at all, which is why it is the insurance.

WHY IT IS A NAMED CARD AND NOT A HIDDEN ROUTE: mechanically it could be presented as a sub-feature of card 1, and that would be cheaper to explain. But Whitney's homework is explicit — "your task after next week's call will be to make a decision on which are a couple of the workflows we should start working on in terms of execution" (Sept 2 @41:38). An unnamed sub-feature cannot be picked, cannot be funded, and does not survive its host card's rejection. It also carries the only two remaining HIGH-priority sheet rows, and it is the only card that puts Carmen and Jacqueline on screen at all.

### Effort

0.7 engineer-days (~5.6 hours) incremental, on top of the ~1.25d shared spine that all five cards fund jointly. Breakdown: three tool schemas plus the extraction prompt with prior-open-commitments context, 0.20d; segmentation heuristic with unattributed-span emission, 0.10d; roster join, fuzzy matcher and abstain bands, 0.15d; cross-run commitment state store and reaction-driven transitions, 0.15d; Sheets, ClickUp and client_brief writes with the hard-coded tier guard, 0.10d. Everything else — intake, normalizer, extractor harness, abstain lane, Slack gate, connectors, run ledger — is spine already being built for card 1.

Against the real capacity picture: roughly 4.0 build days remain after reserving half a day for rehearsal and pre-generating artifacts. Spine 1.25 + card 1 at 2.3 + this card at 0.7 + Page Check at 0.5 + card 4 at 0.25 + card 5 at 0.25 does not fit; the portfolio absorbs that with cards 4 and 5 built as thin readers of the record this card fills, which is why their numbers are 0.25 each. This card is the cheapest thing in the portfolio per sheet row landed: two HIGH rows and one partial MED row for 0.7 days.

Two effort risks worth naming. First, the roster join is the only line item whose cost is unknown until the GHL invite is accepted — if the Communities endpoint is absent, the sheet-as-roster fallback is actually CHEAPER (about 0.05d), so the risk is to fidelity, not to schedule. Second, the volume answer could fork the flag spec from "fire on threshold" to "rank re-engagement priority". That fork is roughly cost-neutral but must be settled before the 0.10d write leg starts, not during it.

### Demo beats

1. "This is Carmen's Google Ads office hours from the twelfth of February. It is your file, out of your Fathom, and it reached us because Gisselle copied it out — which is a thing she already does. Nothing here is a recording of ours." Paste into the same Slack channel card 1 used. Same channel, same paste, different kind of call.
2. "Before I show you anything of ours, here is what Fathom already gives you free, today." Put the three ACTION ITEM lines on screen with their clickable timestamps. "Three items. Three deep links. That is the baseline. If all we did was that, we would be charging you for something you already have."
3. The card comes back. Read the CHANGED block: "On this one call Carmen moved outbound-click conversions from primary to secondary on two of your client accounts, and added nine negatives. Fathom caught five of the nine and neither conversion change. And I want to be precise about the claim — Google Ads logs the change itself, for free. What it does not log is this." Click the reason quote. Land on Carmen, at the second she said it, in her own voice.
4. PROMISED block: "Three promises made out loud. Fathom caught two of them as text — it did catch the VIP-day link, I am not going to pretend otherwise. What none of the three has is an owner, a due date, a client account, or anywhere to go. Here they are with all four. And this one" — point at the Erin line — "is marked a soft offer. It gets recorded and it never gets chased, because 'come back to me next time' is not a task."
5. Click the ✅ on the VIP-day link. "That state now survives. When next Thursday's transcript lands in the same channel, this line either closes itself against what was said, or it is still sitting here waiting. That is the thing Gisselle builds a ClickUp task by hand to do today."
6. SHOWED UP block: "Three members seen. Two written straight into the five columns of the sheet you keep — member, consecutive misses, last attended, two-week flag, four-week flag. The third is 'Jillian', no surname. It had one candidate at 0.78 and it refused to guess." Click through to the needs-a-human queue. "Your own sheet says: just needs to flag, we will manually follow up. It flags. It never DMs anybody. And two minutes of this call are marked unattributed, because nothing in the transcript told us whose they were."
7. "One thing I want to say before the last beat. Two of these three outputs were never mentioned by anyone in ninety-two minutes of discovery. Carmen and Jacqueline have never been interviewed, and neither of them has seen this. Attendance holds at your current volume, not because of the format — a member who joins and listens quietly scores absent, and Jillian left at nine minutes into a forty-eight minute call and scores as fully present. So it flags, and a person confirms."
8. The landing beat. Switch to card 4 — Ridgefield's monthly page. Click the cause sentence in the middle of it. It jumps back to Carmen, on the twelfth of February, saying the thing that caused it. "That sentence in your client's monthly report is not something anybody remembered. It is Carmen, on a Thursday in February, in her own words, and it got there because a transcript was pasted into a Slack channel. That is what 'how is it all connected' looks like. Not a diagram — a click."

### Risks

- THE ROSTER ENDPOINT MAY NOT EXIST. The GHL invite is sent, not accepted; permission level (Agency Admin) is unconfirmed by the client; and the strongest thing anyone has said about API availability is Minu's "most likely" on Sept 2 @13:36. Mitigation: probe within the hour of acceptance, and fall back to reading the roster from Gisselle's own roll-call sheet — which she maintains by hand and which is our write target anyway. Fidelity risk, not schedule risk.
- THE VOLUME QUESTION IS UNANSWERED AND IT IS A SPEC QUESTION. Feb 12 had three members across 48 minutes; the Meta session had one. If most portal members are non-attenders in a given week, 2- and 4-week flags fire on nearly everyone continuously — reproducing exactly the failure they exist to fix. Mitigation: fire once on threshold crossing, cooldown, rank by consecutive misses; and get the answer before the flag logic is written. If the answer is "most of them", we build a ranked re-engagement list instead and say so.
- THE CHANGE-LOG EXTRACTOR IS VALIDATED ON n=1, SEVEN MONTHS STALE. Feb 12 is the only change-log sample in existence, and it predates the account manager's resignation and "we're onboarding a lot of clients". The only second sample is a two-person troubleshooting call, so generalisation is demonstrated only as a negative test. No accuracy figure can honestly be quoted. Mitigation: two recent transcripts via the same paste route, requested today.
- TWO OF THREE OUTPUTS HAVE ZERO CLIENT VALIDATION. Nobody mentioned an ad-account change log in either call, and TASK-10's pain was articulated but its process was never walked. Presenting an unrequested engine to a buyer with low AI literacy risks confusion rather than conviction. Mitigation: lead with roll call, which she nominated in writing at HIGH priority, and frame the change log as the answer to Tina's 18–24 hrs/month "why behind it all" rather than as a new idea.
- CARMEN AND JACQUELINE HAVE NEVER BEEN INTERVIEWED AND ARE NOT IN THE ROOM. This card depends on their continued recording and their tolerance of a system that reads their calls. Mitigation already in the design: the card is named for the client account, there is no per-person view, and the outputs go to the client record and Gisselle's sheet — never to a performance surface. But the adoption risk is real and it is not solvable from the demo.
- THE META HALF DEPENDS ON A CONTRACTOR'S OWN TOOLING. Jacqueline hosts on jacqueline@jacquelinehood.com, outside the company Fathom workspace, and her Aug 27 session's title was never set. Whitney pre-consented in principle to consolidation (Sept 2 @4:08) but does not control that account. Related trap already handled: the internal/external domain heuristic silently misclassifies her, so staff detection uses an explicit allowlist, never the (weddingindustryads.com) suffix.
- ATTENDANCE IS A VOLUME-CONTINGENT PROXY AND THE CLIENT'S OWN DESCRIPTION ARGUES AGAINST THE FORMAT ASSUMPTION. Our rolling-1:1 reading of Feb 12 is n=1; Gisselle described an open drop-in where "they can join like at any moment during that hour" (Aug 26 @13:32). Grow the roster and silent listeners return — and the silent listener is precisely the disengaged member the flag exists to catch. Also unfixable: Jillian left at 9:19 of 48 minutes and scores as a full attendee. Mitigation: state it out loud, keep the abstain lane, never auto-contact.
- IDENTITY RESOLUTION IS THE REAL BLOCKER, AND THE SAMPLE IS BAD. Speaker labels are Carmen Cruickshank (weddingindustryads.com), Jillian, Erin Smith, Michael & Diana — 2 of 3 member labels ambiguous in the only sample we hold. Mitigation: match per member ACCOUNT rather than per person so "Michael & Diana" resolves; abstain bands at 0.70/0.90; given-name-only matches allowed only when unique.
- A HALLUCINATED CHANGE WRITTEN INTO A CLIENT RECORD IS A TRUST INCIDENT, NOT A BUG. Precision matters more than recall here. Mitigation: a verbatim reason quote and a source second are required on every change; the human gate sits in front of every write; and the tier guard makes the client-visible folder unreachable from this code path. The bar we hold ourselves to is zero fabricated changes, not high recall.
- THE SHARE-LINK FETCH COULD DISAPPEAR AT ANY TIME. copy_transcript is undocumented, unauthenticated and behind Cloudflare, and canDownload: false suggests the surface is being tightened. Mitigation: the paste is the design and the fetch is a convenience; the fetch is never on the demo's critical path.
- TASK-12's 6.0 hrs/month IS THE LARGEST QUANTIFIABLE ROW IN THE SHEET AND WE ARE ONLY LANDING PART OF IT. The Canva banner needs an API we do not have and the portal upload path is unverified. Mitigation: claim the recap-summary content leg only, and do not put 6.0 hours in any total.

### Production path

APOLLO WEEK 1 — close the two open questions rather than write code. Get the volume answer and, if it forks the spec, ship the ranked re-engagement list instead of flags. Accept the GHL invite, verify Agency Admin, and settle whether the Communities/membership roster is reachable; if it is not, promote Gisselle's sheet to the roster of record permanently and stop pretending otherwise. Reuse this card's commitment primitive to close TASK-05 as a configuration change — no new build.

WEEK 1–2 — interview Carmen and Jacqueline. Fifteen minutes each. These would be the first fulfilment-side interviews the engagement has conducted, and file 04 names their absence as its biggest conversion risk. The questions are narrow: do you already keep a change note anywhere, what do you want the record to look like, and what would make you stop recording. Then collect four to six recent office-hours transcripts through the same paste route and re-tune the extractor off n=1.

WEEK 2–3 — wire the change log into the monthly report as card 4's cause layer, so Tina stops writing the "why" from memory. This is where the card stops being a record and starts being a saving: the leg Whitney described as "not... Automated in any way right now" gains a sourced input.

WEEK 3–4 — the discrepancy flag, which is the real product hiding inside this one. With Google Ads change-history and Meta account-activity read access, reconcile what was said on the call against what was actually logged in the account. A change promised on a call and never made, or a change made and never explained, becomes a flag. That converts this card from a record into a control, and it is the first thing in the portfolio that could catch a fulfilment error before a client does. It needs ad-API access that was never requested and Carmen's buy-in that was never sought, in that order.

WEEK 4+ — decide honestly whether to automate the intake at all. Fathom team-account consolidation is pre-consented (Sept 2 @4:08) but requires Jacqueline to change her own tooling. The paste costs Gisselle about ten seconds and it is a step she already performs, so automating it should be judged on whether it removes real friction, not on whether it sounds more automated. Our recommendation today is to leave it.

WHAT MUST NOT DRIFT INTO PRODUCTION: the flag never becomes a DM, the attendance number never becomes a staff metric, and the client-facing Drive tier never becomes reachable from this card. Those three are the reason it is safe to run against real client accounts on day one.

### Success criteria

- CHANGE-LOG RECALL, ON THE ONE SAMPLE WE HAVE, STATED WITH ITS LIMITATION: on Feb 12 the extractor captures both primary→secondary conversion changes, all nine negative keywords, and all three commitments, each attributed to the correct client account. Because Feb 12 is also the only tuning sample, this is a fit measure, not a generalisation measure, and we will say so on the call rather than quote it as accuracy.
- PRECISION IS 1.0 OR THE CARD DOES NOT SHIP. Zero fabricated changes, zero fabricated commitments, zero attendance rows for labels that never appear in the transcript. A hallucinated account change written into a client record is worse than no card at all.
- IT BEATS THE FREE BASELINE ON SCREEN, MEASURED AND NOT ASSERTED. Against Fathom's own three ACTION ITEM lines: the two conversion changes and four of the nine negatives (barn, under 5000, at home, banana) are captured that Fathom's lines do not contain; the third commitment to Erin is captured as a soft offer; and every captured item carries what none of Fathom's three carries — an owner, a due date, a client account, and a destination.
- EVERY EMITTED FACT IS SOURCED AND CLICKABLE WHERE IT CAN BE. 100% of facts carry start_seconds plus a speaker label; a ?timestamp= deep link is rendered when the source was a share link, and a bare @MM:SS citation with an on-screen note when it was a paste with no player URL.
- ATTENDANCE ABSTAINS RATHER THAN GUESSES. All three Feb 12 member labels are detected; at least one abstains to the needs-a-human queue with its evidence link and its candidate; the 33:00–35:00 span is emitted as unattributed rather than absorbed into a neighbour; and the write lands in Gisselle's exact five columns.
- COMMITMENT STATE SURVIVES A SECOND RUN. Re-ingesting Feb 12 produces the same commitment_ids and zero duplicate rows, and a ✅ reaction transitions one line to confirmed_done and keeps it there across a restart.
- THE NEGATIVE TEST PASSES AND IS SHOWN. On the Aug 27 Meta transcript — a two-person troubleshooting call — the change-log extractor returns an empty array with a stated reason rather than inventing changes. This is the criterion we care about most and the one we will demonstrate even though it is the least impressive.
- NOTHING CLIENT-FACING EXISTS ANYWHERE IN THE RUN. Zero client-bound artifacts produced; zero writes to any wia+<client> path; a unit test asserts the tier guard; and no message is generated to any member under any condition.
- THE HUMAN GATE IS PROVABLY IN FRONT OF EVERY WRITE. The run ledger shows no API write with a timestamp earlier than the reaction that approved it, for every run in the demo and the backtest.
- WHITNEY CAN NAME WHAT IT DOES WITHOUT PROMPTING. The adoption test, and the one that actually decides the engagement: after the demo she can say, unaided, that one paste produces a record of what was changed and why, a list of what was promised, and who showed up — and that the report sentence she clicked came from Carmen's own voice on a Thursday in February.

---

## MVP 3 - Page Check — are there errors? Is it going to convert?

**A mobile-first crawl of your own funnel and your clients' landing pages that returns blockers, warnings, a conversion-readiness verdict and a LeadLock go-live/A2P readiness check — with no credentials, no access and no waiting on anyone.**

*Effort: 0.5 days. Status vs previous plan: STRONGER and slightly narrowed. Stronger because the Ridgefield folder plausibly yields live client landing-page URLs and the LeadLock pages Tina built, so the crawl covers real client work rather than only WIA's own site. Its strategic weight also rose: with MVP3 cut, this is now the only remaining coverage of Whitney's own #1 nomination, which is exactly why the cost of that cut is stated out loud rather than buried. Narrowed by deferring the run-to-run diff to Apollo week 1; the LeadLock go-live/A2P readiness block is deliberately KEPT, against the advice of one challenge, because it is the*

### The problem today

There is no process to describe, and that absence is the finding.

Nobody checks a landing page before it reaches a client or a lead. The QA layer that does exist is the client: describing the LeadLock build on Sept 2 @33:01, Whitney says "Once edits are done, then there's like an internal, you know, testing kind of troubleshooting process. We ask the clients to test as well."

The Aug 26 call contains a complete, unflattering demonstration of what that costs. At @41:28 Minu reports that E2M's routine pre-call due diligence found a defect on Wedding Industry Ads' own funnel: "And we noticed that on the mobile section, there is a CTA which points to a 404." Whitney's first reaction is confirmation — "Yeah, we actually caught that a couple of days ago." Her second, @41:50, is "Did I email you or did I slack you about that, Gisselle, already?" The answer on the call is "I don't remember." Her third, @41:55, narrows the confirmation: "I think we talked about a link in the investment guide. But not on the website."

Read in order, those four lines are the process. A defect exists on the property that receives their paid traffic. Someone may have seen it. Nobody can say whether it was reported, to whom, or through which channel. What was actually confirmed independently was a second, different broken link — inside the investment guide, a gated asset. And the only durable record of any of it is a half-remembered Slack message. Fifteen days later, at the blueprint review, nobody in the company can tell you the status of either one without going to look.

The structural cause is the one Whitney named herself. Sept 2 @25:50: "So it's not like there are multiple team members that do the same things, right? It is just like one person with set responsibilities." There is no second pair of eyes by construction. Worse, the single person who builds every landing page is the same person who owns monthly reporting — Sept 2 @33:01: "we have Tina on the team, basically, like, dedicating the first few business days of the month to pulling these reports together for clients." Pages ship while she is buried in reports, and the clients signing in the first week of a month wait on both.

This work has no row in the audit sheet and could not have had one. All twelve client-entered rows are assigned to Gisselle and all twelve sit in the department "Operations / Admin / Internal"; the dropdown offered "Web", "Design" and "Paid Media / PPC" and the client used none of them. The sheet covers one outside contractor's operational seat, and page QA is fulfilment work.

Yet it is the client's own number-one nomination. Unprompted, Aug 26 @16:54, Whitney listed her biggest area of opportunity as "getting creative briefs done, you know, getting first drafts of copy, first drafts of landing pages or after landing pages are done, and then checking the landing pages and seeing, are there errors? Is it, is it good? Is it going to convert sort of thing?" The last clause is the name of this card. It was never revisited on Sept 2 and appears nowhere in the sheet.

The acceptance bar is also hers, Aug 26 @39:09: "My biggest thing is just making sure that, like, the end output is good, right? And it's not, like, negatively affecting the client experience in any way or what the leads are experiencing."

### Evidence

- **Call 2026-08-26 @16:54 (Whitney by content; the transcript's speaker labels are unreliable in this stretch, timestamps are not)** - "getting first drafts of copy, first drafts of landing pages or after landing pages are done, and then checking the landing pages and seeing, are there errors? Is it, is it good? Is it going to convert sort of thing?"
  - *Establishes:* The card's name is a direct quotation of the client's own unprompted #1 nominated opportunity. This is not E2M proposing a capability; it is the last clause of her own list, returned to her built.
- **Call 2026-08-26 @41:28 (Minu Bhatt)** - "And we noticed that on the mobile section, there is a CTA which points to a 404."
  - *Establishes:* A real, mobile-specific, zero-credential-detectable defect exists on WIA's own public funnel and was raised on the record. It is why the crawl is mobile-first rather than desktop-first.
- **Call 2026-08-26 @41:28, tail of the block the transcript labels Minu Bhatt (content is Whitney answering)** - "Yeah, we actually caught that a couple of days ago."
  - *Establishes:* Whitney's first response was agreement, not dispute — so the finding was never contested. But see the next two rows before claiming she confirmed this specific defect.
- **Call 2026-08-26 @41:55 (Whitney Hodges)** - "I think we talked about a link in the investment guide. But not on the website."
  - *Establishes:* CORRECTION TO THE EARLIER PORTFOLIO NOTE: what Whitney independently confirmed was a broken link in the investment guide, not the website's mobile CTA. There are two candidate defects — one she named herself, one E2M raised and she did not dispute. The demo script must say it in that order. Claiming 'you already confirmed this 404' would be wrong and she would catch it live.
- **Call 2026-08-26 @41:50 (Whitney Hodges); answered @41:55 with "I don't remember."** - "Did I email you or did I slack you about that, Gisselle, already?"
  - *Establishes:* The strongest single piece of evidence in this card, and it was not used in the earlier reassessment. A known defect on their own funnel has no record of ever having been reported. This is the turnover-proofing thesis in miniature: the knowledge exists only in two people's recollection, and both recollections failed on a live call.
- **Call 2026-09-02 @33:01 (Whitney Hodges)** - "Once edits are done, then there's like an internal, you know, testing kind of troubleshooting process. We ask the clients to test as well."
  - *Establishes:* The client is currently part of the QA layer for the pages WIA builds for them. That is the process being replaced — not a slow process, an outsourced-to-the-customer one.
- **Call 2026-09-02 @33:01 (Whitney Hodges; "H2P" is the transcript's rendering of A2P)** - "You know, we're having to create landing pages typically for, like, their privacy policy so that we can get them approved for the H2P, you know, SMS text messaging."
  - *Establishes:* The A2P readiness block is grounded in a compliance gate Whitney described herself, and every element of it (privacy-policy page reachable, consent language, opt-in control) is page-side and therefore checkable with no credentials. It is also the only place Danielle appears anywhere in the five-card portfolio.
- **Call 2026-09-02 @33:01 (Whitney Hodges)** - "and saying, hey, LeadLock is live now, this page is approved, we need to switch the URL for the campaigns to now go"
  - *Establishes:* The natural production trigger. Go-live is a cross-track handoff from Danielle and Tina to Carmen and Jacqueline, and it is exactly the moment a page-readiness verdict is worth having. Whitney described the dependency at length without being asked about it.
- **Call 2026-09-02 @33:01 (Whitney Hodges)** - "we have Tina on the team, basically, like, dedicating the first few business days of the month to pulling these reports together for clients"
  - *Establishes:* The sole landing-page builder is also the monthly-reporting owner, so nobody with time owns page QA. This is the documented bottleneck the card relieves, and it is the same 18-24 hrs/month workstream that MVP4 addresses from the other end.
- **Call 2026-09-02 @25:50 (Whitney Hodges)** - "So it's not like there are multiple team members that do the same things, right? It is just like one person with set responsibilities."
  - *Establishes:* No redundancy exists, so no second reviewer exists. A tool that reads is the only available second pair of eyes — and it also means a false positive lands on a single irreplaceable person, which is why blockers are deterministic code rather than model output.
- **Call 2026-08-26 @39:09 (Whitney Hodges)** - "My biggest thing is just making sure that, like, the end output is good, right? And it's not, like, negatively affecting the client experience in any way or what the leads are experiencing."
  - *Establishes:* The stated acceptance bar for anything E2M builds, in her words. This card is the only one of the five that acts directly on that sentence rather than on an hours figure.
- **Call 2026-09-02 @27:38 (Whitney Hodges, listing the onboarding questionnaire's contents)** - "If they have a Google Ads account, Meta Ads account, GTM, GA4, like all of those different things."
  - *Establishes:* Tracking-tag presence is already something they interrogate at onboarding. Verifying that GTM, GA4, the Meta pixel and the Google Ads conversion tag actually fire on the live page is on-thesis for a paid-media agency and needs no account access at all — it is observable in the page's own network traffic.
- **Technical probe finding, file 05 §4d — verbatim in the transcript text the client copied out of the Feb 12 2026 Google Ads office hours (Fathom call_id 566502955), deep-linked at ?timestamp=1242.9999** - "ACTION ITEM: Build short-form LP (name/email/phone/date); swap treehouse hero; prep for 50/50 A/B w/ Carmen"
  - *Establishes:* WIA's own conversion levers are form length, field set and hero relevance. The readiness heuristics can therefore be theirs, drawn from what Carmen actually tells clients, rather than generic CRO advice. This is what makes the verdict defensible in the room.
- **Technical probe finding, file 05 §4e — Carmen to a member, Feb 12 2026 Google Ads office hours transcript** - "you can come back to me next time with that shorter lead form"
  - *Establishes:* Shorter forms are a named, spoken agency rule. The form-field check is enforcing a policy the company already has and has never written down.
- **Call 2026-09-02 @8:45 (Gisselle Jimenez)** - "And then the invalid emails is just that we have a lot of, like, opt-in forms, so people are opting in, and sometimes they misspell their email address."
  - *Establishes:* A daily manual chore (TASK-15, ~1.1 hrs/month) is generated downstream by forms that accept typo'd addresses. Checking email-field validation and confirmation on the form is the only place in the portfolio where a fulfilment-side check reduces an operations-side task, and it is traceable to her own words.
- **Call 2026-09-02 @33:01 (Whitney Hodges, on what she wants monthly reporting to become)** - "be something clearer for clients to understand as opposed to like so many screenshots of the metrics"
  - *Establishes:* The output-format constraint. No Lighthouse score dump, no screenshot wall, no numeric grade — a short ranked list of things to fix with the evidence attached. Her stated preference for reports governs this card's report too.
- **Call 2026-09-02 @42:16 (Whitney Hodges)** - "Because I just feel like so much of our operations are in Slack right now, and that's the way that we're communicating."
  - *Establishes:* Slack is the output and review surface. The word "dashboard" appears zero times across both transcripts, and ClickUp was "never, like, fully adopted... other than to just, like, check off the tasks" (same block).
- **Gisselle's reply, Sept 5-7 2026, quoted verbatim in file 05 §1** - "Shared Ridgefield's client folder (The wia+ridgefield sub-folder is the one shared with the client). I have invited you to our shared drive where we keep all of our files."
  - *Establishes:* Two things: the target inventory for real client pages exists and is granted, and the folder structure has a client-visible tier nested inside an internal one. This card resolves the leak risk the cheapest way available — it has no client-facing write path at all.

### What we build

One command in Slack returns one card: a mobile-first read of WIA's own funnel and their clients' landing pages, with blockers, warnings, a labelled conversion-readiness judgement, a LeadLock go-live / A2P readiness block, and an explicit list of what it could not check.

Someone types `check weddingindustryads.com + ridgefield` into the shared intake channel. Roughly forty seconds later a card comes back in an internal channel with five blocks:

1. BLOCKERS — deterministic, narrow, and entirely code: the page itself non-200; a primary-CTA or navigation link resolving to 4xx/5xx; a form whose action 404s; a missing or zoom-locked viewport meta; no primary CTA inside the first mobile viewport; a LeadLock page with no reachable privacy-policy URL. Each line carries the resolved URL, the literal status code and the CSS selector it came from.
2. WARNINGS — tap targets under 44px, body text under 16px, console errors, failed subresources, mixed content, missing title or H1, page weight and first-contentful-paint outliers, form-field count and composition, an email field with no validation or confirmation step, a consent checkbox pre-checked or absent, and tracking-tag presence: whether GTM, GA4, the Meta pixel and the Google Ads conversion tag actually fire in the page's own network traffic.
3. CONVERSION READINESS — one verdict per page (`ship` / `ship_with_fixes` / `do_not_ship`), one sentence, and up to five ranked fixes. Printed under the word `judgement`. There is no score and no number, because a number would imply a precision this does not have. Every ranked fix cites a finding id from block 1 or 2; a fix that cites nothing is dropped before the card is posted, and the drop count prints on the card.
4. LEADLOCK GO-LIVE / A2P READINESS — privacy-policy URL reachable from the page, SMS/consent language present on the form, opt-in control present and unchecked by default, terms link present, and the page's own canonical final URL captured so it can be handed to Carmen and Jacqueline for the campaign swap. Carries a visible caveat: the checklist is E2M's, and Danielle has not reviewed it yet.
5. DISCLOSURE FOOTER, on every run including the demo — `Facts: N deterministic · Judgements: M (labelled) · Not checked: K · Model claims dropped: D`.

Screenshots land in the thread. Review happens by reaction, matching the spine: white-check-mark accepted, no-entry false positive (which permanently suppresses that rule on that URL pattern), eyes needs a human. Nothing is sent to a client, ever, by this card.

One precision on the "zero credentials" claim, because the loose version is an overclaim that will be caught: what this card needs no credentials for is **the target systems**. No client site login, no CMS, no GHL, no Google Ads, no Meta, no staging auth. Two of E2M's own already-granted read paths are used — Slack (bot token, for intake and output) and Google Drive read on `ai@weddingindustryads.com` (only to discover which URLs to check). Strip both away and the card still runs as `python -m pagecheck --targets targets.txt` against a text file. That is the honest formulation and it is still the strongest dependency profile in the portfolio.

### Scope boundary - what is deliberately out

IN SCOPE, and frozen on Sept 8 — the rule list does not grow after that date:
- Three target sources: URLs pasted into the Slack message, a checked-in `targets/<client>.yml`, and URLs harvested read-only from the Ridgefield folder and the company Shared Drive, including links extracted from PDF text and PDF link annotations (the investment guide is a gated asset, so a site-only crawler would never reach the defect Whitney herself named).
- Two viewports per page: iPhone-14-Pro-class mobile (393x852, DPR 3, touch, mobile UA) as the primary pass; 1440x900 desktop as a single secondary pass.
- The deterministic rule pack and the LeadLock/A2P block exactly as enumerated in `what_we_build`.
- One model call per page for the ranked, labelled judgement and the human-readable sentences.
- One internal Slack card plus thread, one internal-tier append to the client record, one line in the run ledger.
- A suppression file fed by the no-entry reaction, so a false positive cannot fire twice.

OUT OF SCOPE, each with the reason it is excluded:

1. No writes to anything. Not to a page, a CMS, GHL, ClickUp or Canva. Tina and Danielle own these assets and a tool that edits a live client landing page mid-demo is unbounded risk. This also settles the Canva `/edit` link received Sept 5: read-only by policy, because it is write-capable into a live client report.
2. No client-facing output of any kind. This card cannot address a client. Every client-bound artifact goes through MVP1's review card carrying the internal-vs-client-facing tier flag, because "The wia+ridgefield sub-folder is the one shared with the client" (file 05 §1) means a mis-tiered write leaks internal material to a client — the hardest constraint in the engagement. The cheapest possible mitigation is what we chose: this card has no client-facing write path to get wrong.
3. No authenticated or logged-in pages. No GHL login, no member-portal pages, no client CMS admin, no basic-auth staging. This is precisely what makes the card dependency-free, and the cost is stated: member-portal surfaces (TASK-11 and TASK-12) are not covered by it.
4. No campaign-side verification. We cannot confirm that Carmen's and Jacqueline's campaign final URLs point at the approved page, because the Google Ads API and the Meta Marketing API were never requested (file 03, NOT REQUESTED). The card checks the page and captures its canonical URL; matching that against live campaigns is named on stage as the next ask, not implied by silence.
5. No run-to-run diff, no scheduled monitoring, no alerting in the 0.5 day. Runs are persisted from day one because the spine's ledger already does that, so the diff is a rendering job rather than a rebuild — but the diff view and the change alerts are Apollo week 1. One exception, purely for the demo: a baseline run is stored the evening of Sept 9 so the same check can be shown twice.
6. No accessibility (WCAG) audit and no SEO audit. WCAG would roughly double the rule pack and generate findings nobody at WIA owns. SEO is not a service they sell: the audit sheet's department dropdown offered both "SEO" and "SEO/GEO" and the client selected neither. Both are excluded to keep the report short enough that Whitney actually reads it.
7. No Lighthouse score, no performance-metric dump, no wall of screenshots. Her own words about what a report should be, Sept 2 @33:01: "clearer for clients to understand as opposed to like so many screenshots of the metrics."
8. No visual-regression or pixel diffing, no A/B test setup, no copy rewriting. Copy drafting was MVP3, which is cut; the 50/50 A/B is Carmen's own work (file 05 §4d). Page Check reports; it does not author and it does not experiment.
9. No automatic owner assignment and no ticket creation. An owner is suggested only where the page maps unambiguously to a track (a LeadLock subdomain to Danielle and Tina) and otherwise abstains — the same abstain discipline that ambiguous speaker labels forced on roll-call. ClickUp task creation belongs to MVP1 and is gated on a Member seat still unverified as of Sept 7.
10. No site-wide spidering. An explicit URL list, 25 pages maximum per run, one request per second per host, 20-second page budget, robots.txt respected during discovery. A page disallowed by robots or blocked by bot protection is reported under "Not checked", never as a blocker. This bounds runtime inside the 90-second demo window and stops an agency tool from hammering a client's site.
11. Not a monitor and not an SLA. It runs when a human asks. Nobody is accountable for a page it was never pointed at, and the card says so rather than implying coverage it does not have.

WHAT IS DELIBERATELY KEPT DESPITE ADVICE TO CUT IT: the LeadLock go-live / A2P block. It is the only place Danielle appears anywhere in the portfolio, and Whitney described the cross-track dependency at length and unprompted (Sept 2 @33:01) — the privacy-policy page gating A2P approval, then the URL swap for Carmen and Jacqueline. Cutting it would leave the engagement with zero coverage of one of the four single points of failure she named herself.

THE COVERAGE GAP, SAID OUT LOUD RATHER THAN BURIED: with MVP3 cut, this card is the only remaining coverage of Whitney's four-part #1 nomination, and it covers the fourth part. Creative briefs, first-draft copy and first-draft landing pages are not in this portfolio. That sentence belongs in the review, in those words.

### Architecture

TRIGGER. A message in the portfolio's single Slack intake channel beginning `check`, followed by URLs, a client name, or nothing (which falls back to the WIA funnel target set). Same channel, same paste-anything-convenient philosophy as the transcript intake. A CLI path — `python -m pagecheck --targets targets.txt --out runs/` — exists as the no-Slack fallback and is what gets used if the spine's poller is not up yet.

SLACK TRANSPORT (shared spine; no public webhook by design). Bot token `xoxb-`, scopes `channels:history`, `channels:read`, `chat:write`, `files:write`, `reactions:read`, `reactions:write`. A 60-second poll of `conversations.history` against a stored `oldest` cursor; the run ledger dedupes on message `ts`, so a restart cannot double-run a request. No Events API and no Block Kit buttons — both require a publicly reachable request URL, which the spine excludes on purpose. Review is therefore reactions plus threaded replies.

STAGE 1 — TARGET RESOLUTION. Priority order: URLs in the message, then `targets/<client>.yml`, then Drive discovery. Drive discovery uses the Google Drive API v3 on `ai@weddingindustryads.com` via an OAuth 2.0 installed-app flow with scope `drive.readonly` (refresh token on disk): `files.list?corpora=drive&driveId=<sharedDriveId>&includeItemsFromAllDrives=true&supportsAllDrives=true`, then `files.export?mimeType=text/plain` for Docs and `files.get?alt=media` for PDFs, with URL extraction from both PDF text and `/Annots` link objects via pypdf. Output is a deduped list of `{url, client, tier_hint, source}`. Drive is the only credentialed hop in the whole card and it is read-only; its job is to find URLs, not to check them.

STAGE 2 — FETCH. Playwright with headless Chromium. Static fetching is not viable: LeadLock/GHL funnel pages and the WIA site render client-side, so a `requests.get` sees an empty shell — this is a correctness requirement, not a preference. Two browser contexts per page (mobile primary, desktop secondary). Per page we capture: final URL after redirects, HTTP status, the full redirect chain, a HAR, all console messages, all failed requests, a full-page and an above-fold mobile PNG, and a single `page.evaluate` DOM extraction returning every anchor and button with a resolved absolute href, every form with per-field `{name, type, required, autocomplete, label}`, the computed box and font metrics of the primary CTA, the `<meta name=viewport>` content, and the set of request hosts matched against tag signatures (`googletagmanager.com/gtm.js?id=GTM-`, `/g/collect?...tid=G-`, `connect.facebook.net/*/fbevents.js` plus `facebook.com/tr?id=`, `googleads.g.doubleclick.net/pagead/viewthroughconversion/`). Link checking: HEAD per unique resolved href, falling back to GET on 405, redirects followed, 10-second timeout, one retry; `mailto:` and `tel:` validated by syntax only. Concurrency 4 pages and 8 link checks, throttled to 1 request/second per host. A Cloudflare or bot-challenge response is detected by status plus body signature and classified `not_checked`, never as a blocker — a false 403 in front of the client is worse than an admitted blind spot.

STAGE 3 — DETERMINISTIC RULE PACK. Pure Python over the captured JSON. No model. Every finding gets `finding_id` (`<page_hash>-<rule_id>-<n>`), `severity` (`blocker` | `warning` | `info`), `rule_id`, and `evidence` — the literal observation: status code, resolved URL, CSS selector, computed value, tag id, or screenshot crop path. Blocker rules are deliberately few and mechanical (enumerated in `what_we_build`); everything else is a warning. This is where the demo's credibility actually sits, so it is code that either matches reality or does not, with no generative surface at all.

STAGE 4 — JUDGEMENT, ONE MODEL CALL PER PAGE. Anthropic Messages API, `claude-opus-5`, `thinking: {type: "adaptive"}`, `output_config: {effort: "medium"}`, `max_tokens: 8000`. The system block is byte-stable across pages and carries `cache_control: {type: "ephemeral"}`: it holds the conversion rules from `agency_playbook.md` — WIA's own levers, seeded from the Feb 12 office-hours transcript (short lead form with name/email/phone/date; hero relevance; one primary CTA; consent copy) rather than generic CRO advice — plus the abstain instruction and the internal-only output rule. The user turn carries three things: the deterministic findings JSON for that one page, the above-fold text and form inventory, and the above-fold mobile PNG as a base64 `image` block alongside the text. Output is forced through a single tool, `emit_page_verdict`, declared with `strict: true`, `additionalProperties: false` and full `required`, invoked with `tool_choice: {type: "tool", name: "emit_page_verdict"}`. Schema: `{verdict: enum[ship, ship_with_fixes, do_not_ship], one_line: string, ranked_fixes: [{finding_id, why_it_matters, owner_hint: enum[Tina, Danielle, Carmen, Jacqueline, unassigned]}], abstained: [{question, why}]}`. A post-validator then drops any `ranked_fixes` entry whose `finding_id` is absent from the deterministic set and increments a counter printed on the card. The model ranks, explains and judges; it never originates a fact. That is the spine's confidence/abstain lane applied to a crawler instead of a transcript.

STAGE 5 — OUTPUT AND REVIEW GATE. One `chat.postMessage` to an internal channel (never a client channel): header `N blockers · M warnings · K not checked`, then blockers with URL, one-line reason and the evidence value, then the verdict under the label `judgement`, then the LeadLock/A2P block with its "not yet reviewed by Danielle" caveat, then the four-counter disclosure footer. Screenshots via `files.upload` into the thread. Gate: white-check-mark = accepted; no-entry = false positive, which appends `{rule_id, url_pattern, reason}` to `page_check_suppressions.json` so it cannot fire again; eyes = needs a human. Threaded replies are appended verbatim to the run record as reviewer feedback and are the raw material for tightening the rule pack.

STAGE 6 — RECORD WRITE. `runs/<run_id>/{findings.json, report.json, pages/<hash>/{mobile.png, desktop.png, har.json}}`; one JSONL line to `run_ledger.jsonl`; and for any page resolved to a client, an append to `updates/<client>/page-check-YYYY-MM-DD.md` plus maintenance of a `## Live URLs` table in that client's `client_brief.md` (url, tier, last checked, last verdict). Every write from this card is stamped `tier: internal`, unconditionally and in code.

Formats end to end: YAML target lists, JSON findings, JSONL ledger, PNG, HAR, Markdown record writes. No database, no queue, no dashboard.

### Data position

REAL, ALL OF IT. Every page is fetched live during the demo. Every status code, redirect chain, DOM value, form field, tag id and screenshot on screen is read from the client's actual property at the moment it is shown. WIA's public funnel and the investment guide need nothing from anyone. The Ridgefield client folder and the whole company Shared Drive were granted on Sept 5-7 (file 05 §1). Both candidate defects are on WIA's own property and both were raised on the Aug 26 call.

MOCKED: nothing. Zero fixtures, zero synthesized payloads, zero stand-ins. This is the only card of the five with nothing to disclose in that column, and it is the reason it opens the review.

NOT MOCK, BUT NOT FACT EITHER — three things, each labelled on the card itself:

(a) The conversion-readiness verdict is a judgement. It prints under the word `judgement`, with the finding ids it rests on, and it deliberately has no score and no number. A "conversion score of 72" would imply a precision that does not exist and would invite an argument we would deserve to lose. It is a prioritised opinion with the evidence attached.

(b) The A2P/10DLC checklist is E2M-supplied domain knowledge, not client-confirmed. Whitney named the dependency verbatim — landing pages "for, like, their privacy policy so that we can get them approved for the H2P, you know, SMS text messaging" (Sept 2 @33:01) — but the item list is ours, and Danielle, who actually runs A2P registration, has never seen it. So that block carries the line "checklist not yet reviewed by Danielle" until she ratifies it. Ten minutes of her time removes the caveat.

(c) Client-page targets are unconfirmed until the Drive inventory runs. If the Ridgefield folder yields no live landing-page URLs, the card prints "0 client pages found in Drive" and the client-pages section is empty. It will not be filled with plausible-looking URLs.

STILL NEEDED, AND FROM WHOM. The Drive inventory (1-2 hours, E2M-side, no client action required) is the only prerequisite, and it should be the very next action taken because MVP1 and MVP4 need it too. From Whitney, if she wants campaign-side URL verification: the Google Ads API and the Meta Marketing API, neither of which was ever requested. From Danielle: ten minutes on the A2P checklist. From Whitney, before this card is ever pointed at a client site WIA does not host: an explicit yes.

HOW THE DISCLOSURE WORKS WITHOUT DEFLATING THE DEMO. The disclosure is a feature of the card, not an apology bolted onto it. Four counters print on every run, including the live one: facts, judgements, not-checked, and model claims dropped. Because this card has nothing to hide, it is used deliberately as the calibration instrument for the entire review. The first thing Whitney sees is a card that states exactly what it knows, exactly what it decided, and exactly what it could not reach — so when MVP4's metric fixtures and MVP5's stand-in voice note are labelled twenty minutes later, the labelling reads as the house standard rather than as an excuse being made. The line to say once, at the footer: "every card today prints what it made up. This one's number is zero."

### How it connects to the rest

This is the card that proves the spine is real, and it does so by using half of it and none of the connectors.

USES FROM THE SHARED SPINE (~1.25d, charged once to the portfolio, not to this card): the Slack poll intake and the reaction/threaded-reply review gate; the forced-tool-schema model wrapper with its confidence/abstain lane and post-validator; the run ledger; `agency_playbook.md`; `client_brief.md` plus the `updates/` append log; and the internal-vs-client-facing tier field.

DOES NOT USE: the transcript normalizer, `call_type` routing, or any connector — no ClickUp, no GHL, no Gmail. That absence is the argument. As of Sept 7 every connector leg in the portfolio is still mock: invites are sent but unaccepted, and ClickUp Member-vs-Guest and GHL Agency Admin are unverified (file 05 §1). This is the one card that runs at full strength while all of that is still in flight — which is exactly how you demonstrate that the spine is working hardware rather than a diagram. If the spine were vapour, this card could not exist.

SHARES INPUTS. It reads landing-page URLs written into `client_brief.md` by MVP1's filing leg (TASK-09, TASK-14) and by the Drive inventory that MVP1, MVP4 and the cut MVP3 all require anyway. One inventory, four consumers.

SHARES OUTPUTS. The internal-tier `updates/<client>/page-check-*.md` it writes is read by MVP4's executive summary as part of its cause layer. "Leads were flat in the second half of the month; the LeadLock page's mobile CTA was returning 404 from the 12th" is a sentence MVP4 can only write if this card has been running. That is the same causal-provenance mechanic the rank-2 card supplies from Carmen's change log, arriving from a second and completely independent source — one from what a specialist said, one from what the page actually did. Two sources agreeing is what makes the monthly report's "why" defensible instead of remembered, which is the thing Tina currently supplies from memory (Sept 2 @33:01: "We're adding in additional context about like the why behind it all").

FEEDS AND IS FED BY RANK 2. The conversion rules in `agency_playbook.md` are mined out of the office-hours change log — form length, hero relevance, negative keywords, primary-versus-secondary conversions. So the office-hours engine literally teaches Page Check what "going to convert" means at this specific agency, and Page Check is where that captured knowledge gets applied to real pages. Carmen's spoken rule of thumb becomes a check that runs on every page forever. That is the compounding claim in the portfolio story, demonstrated rather than asserted, and it is the clearest example anywhere in the five of institutional knowledge moving out of a person's head and into something the company owns.

WRITES BACK TO THE CLIENT RECORD. Two things, both internal tier, both stamped in code: a dated page-check entry in `updates/<client>/`, and a maintained `## Live URLs` table in `client_brief.md` carrying url, tier, last-checked date and last verdict. That table does not exist anywhere today. A per-client register of every live page and its last known state is small, cheap, and precisely the artifact the Aug 26 exchange proves they lack — "Did I email you or did I slack you about that, Gisselle, already?" / "I don't remember."

ITS PRODUCTION TRIGGER IS A MOMENT SHE ALREADY DESCRIBED. Sept 2 @33:01: "hey, LeadLock is live now, this page is approved, we need to switch the URL for the campaigns to now go." A Page Check pass becomes the precondition for that handoff. This connects the card to the onboarding orchestration Whitney walked through at length, and it is the only appearance of Danielle in the entire portfolio.

ITS ROLE IN THE REVIEW. It goes first, before a single line of generated prose, precisely because it only reads. It establishes that the system perceives their reality accurately, which is what she has to believe before she will consider a card that writes on her behalf. And it puts the first row into the client record that the other four cards then fill and read — which is the literal answer to the question she has asked twice, Aug 26 @19:21: "the biggest thing that I'm looking for at this point, I feel like, is like, how is it all connected? How does it all kind of work together sort of thing?"

### Effort

0.5 day (4 hours) of net-new work, on top of the shared spine which is counted once for the portfolio and not against this card.

Breakdown: Playwright capture harness and link checker, 1.25h. Deterministic rule pack, 1.0h. LeadLock go-live / A2P block, 0.5h. Model verdict plus the finding-id validator, 0.5h. Slack card, screenshot upload and suppression file, 0.5h. Record write and ledger line, 0.25h.

Explicitly charged elsewhere: the 1-2 hour Drive inventory (portfolio-shared across MVP1, MVP3 and MVP4, and it should be the next action taken regardless of this card), and pre-generation plus rehearsal, which come out of the half day already reserved for that.

BUILD ORDER: first, and finished first. It is the only card whose demo cannot be blocked by a pending invite, an unverified seat level or a missing sample — and insurance that arrives on Wednesday is not insurance. Against a real 4.0-day budget it is also the cheapest card in the portfolio at full strength, which is why it survived the narrowing while MVP3 did not.

ESTIMATE RISK, honestly: the 0.5d assumes the spine's Slack poller and run ledger exist when this is built. If the spine slips, the surface degrades to CLI output pasted into Slack by hand. That is a demo-quality regression, not a functional one, and it is worth zero additional hours to accept rather than to hedge against.

### Demo beats

1. 0:00 — Nothing on screen but a Slack channel. Jainil: "Before I show you anything that writes, I want to show you the one that only reads. This one needs nothing from you — no login, nothing you sent us, nothing pre-baked." Types into the intake channel: `check weddingindustryads.com + ridgefield`. Enter.
2. 0:10 — While it runs, one sentence and then silence: "It's opening your pages at iPhone size, following every link, and reading every form. About twenty-five pages, roughly forty seconds." Phone-shaped screenshots begin landing in the thread as each page finishes. Visible progress, nothing to narrate.
3. 0:45 — The card returns. He reads only the header line: "Two blockers, six warnings, one not checked." No scrolling yet.
4. 0:55 — Clicks blocker 1, the mobile CTA, and tells it in the order it actually happened: "On the 26th Minu mentioned a CTA on the mobile section pointing at a 404. You said you'd caught something like it — and then you said the one you'd caught was the link in the investment guide, not the site." Then whichever is true. Still broken: "Fifteen days on, here it is, with the status code and the URL. Nobody had to remember to look." Already fixed: clicks the stored Sept 9 baseline line in the ledger — "It was there last night and it's gone this morning. Same check, run twice. That's the version of this that runs every week."
5. 1:15 — Clicks blocker 2, the investment-guide link. "This one is yours — it's the one you named. And it was inside the PDF, so anything that only crawls the website would never have found it."
6. 1:30 — Scrolls to the tag block and reads whatever is actually there: "Your Meta pixel fires on this page and not on that one" — or the honest opposite. Then the form block: "Seven fields on mobile on this one. Back in February Carmen told a client she'd take a shorter lead form off her hands. That's the same judgement, applied to every page, in under a minute — and it's your rule, not a generic best practice. It came out of Carmen's own office hours."
7. 1:50 — Scrolls to the LeadLock block. "This is Danielle's and Tina's half of the business. Privacy policy reachable, consent line present, opt-in box unchecked by default — or exactly which one is missing. You described this yourself: the privacy-policy page is what gets them approved for A2P. And it captures the page's final URL, which is the thing that has to reach Carmen and Jacqueline on go-live day." One caveat out loud: "Danielle hasn't seen this checklist yet. It's ours, not hers. Until she signs off, that block says so on its face."
8. 2:10 — Points at the footer. "Facts: forty-one. Judgements: three, and they're labelled. Not checked: one, because that host blocked us and I'd rather say so than guess. Model claims dropped: zero. Every card you see today prints those four numbers. This one's made-up number is zero."
9. 2:25 — THE BEAT THAT LANDS. Turns the keyboard around. "Give me a URL. Any page — a client's, a prospect's, one of your own. I don't need a login and I haven't seen it." Types whatever she says. Runs it live. Forty seconds later it returns whatever it returns.
10. 2:55 — Closing line, with her page still on screen: "This is the only one of the five where there's nothing to take on faith. Every finding on this card, you can reproduce yourself the minute we hang up."

### Risks

- The Aug 26 defect may already be fixed by Sept 10, which kills the "still broken" beat. Mitigation: baseline runs stored the evening of Sept 9 and again the morning of the review; if it is fixed the beat inverts into the diff story, which is arguably better. Either way the demo does not depend on a client's page staying broken.
- OVERCLAIMING HER CONFIRMATION IS THE BIGGEST RISK IN THIS CARD. She said "Yeah, we actually caught that a couple of days ago" and then narrowed it to "a link in the investment guide. But not on the website." Saying "you already confirmed this 404" would be inaccurate, she would catch it in real time, and it would cost more credibility than the beat is worth. The script tells it in the order it happened and lets the two defects be two defects.
- A live audience-chosen URL can hit Cloudflare or a bot wall and return a challenge page. The tool must classify that as "not checked", never as a 403 blocker — false confidence on an unfamiliar page in front of the client is the worst available outcome. Pre-flight against six representative stacks the night before (GHL/LeadLock, Squarespace, Showit, WordPress, Wix, and a Drive-hosted PDF). E2M inference on which stacks matter: we have no inventory of client site platforms and nobody mentioned one on either call.
- False positives land on a single irreplaceable person. Tina is the sole landing-page builder and a named single point of failure (Sept 2 @25:50), so one confidently wrong claim about her work damages the exact relationship this card is meant to serve. Mitigations, all structural: blockers are deterministic code rather than model output; the verdict is labelled a judgement; the report is internal-only and cannot reach a client; the no-entry reaction permanently suppresses a false positive.
- Ridgefield may contain no live client URLs. Then this is WIA's own funnel only, and the strategic claim that it covers real client work and Tina's and Danielle's deliverables shrinks to a promise. Mitigation: run the 1-2 hour inventory before any build time is spent, and if it comes back thin, say on stage that the client-pages section is empty and why.
- The coverage gap must be named or it becomes the conversion risk. With MVP3 cut, this card covers only the fourth clause of Whitney's four-part #1 nomination (Aug 26 @16:54). Creative briefs, first-draft copy and first-draft landing pages are absent from the portfolio. Not saying that out loud is the fastest route to the predicted failure — "this is helpful, let me think about which ones", then drift.
- There is no hours story here and there must not be a fabricated one. No audit-sheet row, no duration estimate anywhere in either call, no baseline. Its case is defect escape and coverage of fulfilment work, not recovered time. Attempting an hours ROI on this card would collide with the engagement-wide arithmetic ($175 per recovered hour at a 100%-automation ceiling) and would undermine every honest number in the document.
- Campaign-side blindness. We can say the page is ready; we cannot say the campaign points at it, because the Google Ads and Meta APIs were never requested. That is a genuine hole in the go-live check and it goes on the ask list rather than being left to silence.
- Scope creep. This is the easiest card in the portfolio to keep adding checks to, and every added check lengthens a report she has to read — which is the failure mode of the thing she rejected ("so many screenshots of the metrics"). The rule list is frozen Sept 8; anything new goes to the Apollo backlog.
- Third-party crawling on non-owned domains. Checking a client's own site as their agency is unremarkable. A prospect's site named live on stage is a third party: the run is a single page, read-only, no form submitted, no login attempted, one request per second — functionally indistinguishable from a person opening it on a phone. Stated as a limit rather than assumed.
- Dependency on the spine's Slack poller for the demo surface. If the poller is not up, the card still runs and still finds everything, but the intake and output degrade to a terminal. Accepted rather than hedged.

### Production path

Seven steps, in order, from a 0.5-day demo to something the team actually relies on.

1. Freeze the rule pack and let the suppression file work for two weeks. The no-entry reactions are the training signal. After roughly twenty real runs the false-positive rate is a number instead of a worry, and the ranked-fix language has been edited by the people who use it.

2. Turn on the run-to-run diff and "new since last check" alerting — Apollo week 1. The ledger already persists every run from day one, so this is rendering work, not a rebuild. This is where the card stops being a spot check and starts being a memory.

3. Put it on the two triggers Whitney already described, not on a cron. First, the LeadLock go-live handoff (Sept 2 @33:01: "hey, LeadLock is live now, this page is approved, we need to switch the URL for the campaigns to now go"). Second, the moment Tina hands a page over for client review — which is the step that currently ends with "We ask the clients to test as well." Removing the client from the QA layer is the actual outcome, and it is reached by trigger placement, not by more checks.

4. Wire the verdict into the ClickUp onboarding checklist as a gate on the "landing pages approved" step. This needs the ClickUp seat confirmed as Member rather than Guest, which is still unverified as of Sept 7, and it needs MVP1's ClickUp leg to be live. Sequenced after both.

5. Request the Google Ads and Meta Marketing APIs to close the campaign-side URL check — confirming that the campaigns actually point at the approved page. It is the one thing this card cannot do from outside, and it is a one-line ask.

6. Promote the settled rules. Rules that survive the suppression file, plus the conversion levers mined out of Carmen's and Jacqueline's office-hours change log, get written into `agency_playbook.md`. At that point the agency's conversion heuristics are a company-owned file rather than one specialist's habit — which is the Aug 11 driver as recorded in the engagement background: the next account-manager hire "is just a person who is kind of like running it. We have the agency brain." (Aug 11 discovery call, per project background notes, not from either provided transcript.) That promotion is the only reason a page crawler belongs in a turnover-proofing engagement at all, and it should be stated in exactly those terms.

7. Only after all of the above, and only behind MVP1's review card with the internal-versus-client-facing tier flag, consider a client-facing version — a short "your page is live and here is what we checked" note. Not phase one, and not without an explicit yes.

The honest ceiling on this card: it will never produce a large hours number, because there is no measured baseline for work nobody currently does. What it produces is a record where none exists and a check that runs whether or not anyone remembered to ask for it.

### Success criteria

- Runs end to end from a Slack message typed live on the call, across at least 15 real URLs, returning in under 90 seconds, unattended, with no operator intervention between Enter and the card.
- Returns at least one of the two defects raised on Aug 26 — or, if both are now fixed, shows the stored Sept 9 baseline proving the same check found it before and does not now. Both outcomes count as a pass; only a silent miss is a fail.
- Zero fabricated findings. Every blocker and warning line on screen traces to a status code, a resolved URL, a CSS selector or a tag id present in `findings.json`. The validator's dropped-claim counter reads 0 on the card, and the mechanism that produces the 0 is shown rather than asserted.
- Survives an audience-chosen URL: returns a result, or an explicit "not checked — blocked by bot protection", within 60 seconds. Does not crash, does not hang, and does not report a challenge page as a 403 blocker.
- Produces a populated LeadLock go-live / A2P block on at least one real LeadLock or GHL-hosted page, with the "checklist not yet reviewed by Danielle" caveat visible on the card.
- Writes one internal-tier entry to a client record that MVP4's executive summary demonstrably reads later in the same demo — so the interconnection is watched, not described. This is the criterion that tests the spine rather than the card.
- Every finding is independently reproducible by the client with no access to anything E2M holds. She can open the same URL on her own phone and see the same thing.
- THE ADOPTION CRITERION, AND THE ONE THAT ACTUALLY DECIDES THE ENGAGEMENT: Whitney names, unprompted, whose work this covers (Tina's, Danielle's), or asks to run it on a specific named client. Given low AI literacy and a review whose stated purpose is a decision on "a couple of the workflows" (Sept 2 @41:38), an unprompted "can you run it on X" is the strongest signal obtainable in the room — stronger than approval of the output itself.
- Stated deliberately as a NON-criterion: no hours-saved figure. There is no baseline for work nobody performs today, and inventing one would contradict the engagement's own arithmetic and every other honest number in this document.

---

## MVP 4 - An executive summary instead of a wall of screenshots

**Metrics plus the account record in, one client-ready page out: the trend, the cause traced to a real change with a timestamp, and a recommendation — instead of a deck of screenshots assembled from memory.**

*Effort: 0.25 days. Status vs previous plan: NARROWED, and materially improved on one leg. It gained a real design target — the Canva client report arrived — but as an /edit link, which shows template scaffolding rather than the artifact as delivered, and which is write-capable into a live client asset; it is treated as read-only by policy and ai@ must never touch it. The 90-second walkthrough-script leg is CUT: the video was requested and never sent, so register and length were pure guesses, and it was the least-grounded leg of any selected card. In exchange the card gains something better than it lost: the cause layer, which Whitney sa*

### The problem today

Once a client's campaigns are all launched, Whitney moves them into "monthly maintenance," and the first artifact of that phase is a monthly report built by hand. On Sept 2 @33:01 she described it unprompted and in one breath: "we have Tina on the team, basically, like, dedicating the first few business days of the month to pulling these reports together for clients," and she called it "a very, like, painstaking process, honestly." The mechanics she gave: "She's like pulling in screenshots from the different ad accounts, pulling in screenshots of best performing ads. We're adding in additional context about like the why behind it all. And then also like recording a video walkthrough to kind of like explain it to the client." Three of those four legs are assembly; the third one — the "why behind it all" — is the only one that carries judgment, and it is written from memory, because nothing in their stack records what was changed on an ad account or why. E2M's Feb 12 probe proves the memory gap is real: in a single 48-minute Google Ads office-hours session Carmen moved outbound-click conversions from primary to secondary on two separate client accounts and added nine negative keywords, and (file 05 §4e) "None of this lands in ClickUp, Slack, or any client record." Four weeks later, whoever writes the report's cause sentence is reconstructing that from recall.

Two things make this the highest-cost workstream in the engagement rather than just an annoying one. First, it has no row in the audit sheet at all: all twelve client-filled rows (rows 4–15) are assigned to Gisselle in one department, "Operations / Admin / Internal," and the department dropdown's unused options include "Reporting & Analytics." The sheet quantifies ~18.1 hrs/month in total; E2M's derivation from "the first few business days of the month" puts this single workstream at 18–24 hrs/month — roughly equal to or greater than everything the whole sheet measures. That derivation is ours, not the client's; no one asked her for a number, and no one should present 18–24 as her figure. Second, the owner is doubly loaded. Sept 2 @25:50: "Tina is our lead block designer, GHL designer. So abstract like landing pages, email nurture sequences, and text sequences that need to be written in design, that's always getting assigned to her," under the structural fact she stated in the same breath — "it's not like there are multiple team members that do the same things." So the first few business days of every month, the only person who can build a new client's landing pages and write their nurture copy is building last month's reports instead. Every client who signs in that window waits. That is revenue timing, not admin cost, and it is the honest way to price this card.

She has also already named the fix, in her own words, before E2M proposed anything: "I would love something like that that can create more of just like an executive summary on a monthly basis. I think I saw that in your AI library, actually," and the acceptance test in the same sentence — "something clearer for clients to understand as opposed to like so many screenshots of the metrics."

### Evidence

- **Sept 2, 2026 call @33:01 (label reads Whitney Hodges; content confirms Whitney — she is describing her own team)** - "we have Tina on the team, basically, like, dedicating the first few business days of the month to pulling these reports together for clients"
  - *Establishes:* The workstream exists, its owner is Tina, and its cadence is the opening days of each month. This single line is the sole basis for the 18-24 hrs/month figure, which is an E2M derivation, not a client estimate.
- **Sept 2, 2026 call @33:01** - "That, in and of itself right now, is a very, like, painstaking process, honestly"
  - *Establishes:* Client-side pain is articulated, not inferred. This is the only non-Gisselle workstream in either call to which the client attached a duration and a complaint.
- **Sept 2, 2026 call @33:01** - "She's like pulling in screenshots from the different ad accounts, pulling in screenshots of best performing ads. We're adding in additional context about like the why behind it all. And then also like recording a video walkthrough to kind of like explain it to the client."
  - *Establishes:* The four legs of the current process. Legs 1-2 (screenshots) are what this card replaces; leg 3 (the why) is what card 2 sources; leg 4 (the video) is the leg we are cutting because the artifact never arrived.
- **Sept 2, 2026 call @33:01** - "I would love something like that that can create more of just like an executive summary on a monthly basis. I think I saw that in your AI library, actually."
  - *Establishes:* The client named this exact solution herself, unprompted, and pre-sold herself on it. This card is not an E2M idea being pitched back to her.
- **Sept 2, 2026 call @33:01** - "something clearer for clients to understand as opposed to like so many screenshots of the metrics"
  - *Establishes:* The acceptance spec is clarity and compression, NOT fidelity to the existing deck. It is the sentence that authorises us to refuse deck replication.
- **Sept 2, 2026 call @33:01** - "I've been playing around with Victor and our Slack, right? And it's been really cool to see how he can connect to lead block accounts, Google ads accounts, meta ads accounts, and just have an overarching like view of everything."
  - *Establishes:* Her mental model of this product is a live-connected agent across all three platforms. That is exactly the expectation the mock-metric disclosure has to reset in the first thirty seconds, before she discovers it herself and discounts everything else on the page.
- **Sept 2, 2026 call @25:50** - "Tina is our lead block designer, GHL designer. So abstract like landing pages, email nurture sequences, and text sequences that need to be written in design, that's always getting assigned to her."
  - *Establishes:* The report owner is also the sole landing-page and nurture-copy builder — the collision that turns report hours into onboarding delay.
- **Sept 2, 2026 call @25:50** - "it's not like there are multiple team members that do the same things"
  - *Establishes:* No redundancy behind Tina, and the turnover-proofing thesis from Aug 11: a report whose reasoning lives in one contractor's memory is institutional knowledge with no backup.
- **Sept 2, 2026 call @8:01** - "we'll review any drafts before they go out"
  - *Establishes:* The Slack review gate is a standing client instruction, not an E2M safety flourish. This card terminates in a review card and contains no send path.
- **Aug 26, 2026 call @19:21** - "the biggest thing that I'm looking for at this point, I feel like, is like, how is it all connected? How does it all kind of work together sort of thing?"
  - *Establishes:* The standing question of the whole engagement. This card is the only one that cannot function without another card's output, so it is the proof of connectedness rather than an assertion of it.
- **Aug 26, 2026 call @39:55 (attribution unreliable; content is Whitney's own quality bar, stated about drafted output generally)** - "it's not things where I'm, like, doing double work and then, like, going in and having to, like... Heavily edit or like completely rewrite stuff"
  - *Establishes:* The pass/fail test for the generated page on Thursday: does the reviewer edit it, or rewrite it. We can only measure this by asking her live.
- **Technical probe finding, file 05 §4d — verbatim from the Feb 12 Google Ads office-hours transcript the client copied out of Fathom** - "ACTION ITEM: Review search terms; add negatives (CVS, Opalescence Go, baking soda, homemade, cheapest); keep Core Whitening; remove if wasteful - WATCH: .../calls/566502955?timestamp=2428.9999"
  - *Establishes:* The change-log source material is real client-system data, already carries deep-linked evidence timestamps in a format the team recognises, and — per file 05 §4e — Fathom's own extraction missed four of the nine negatives and both of Carmen's spoken commitments. The cause layer has real input and a real quality bar to beat.
- **Technical probe finding, file 05 §2 (both Fathom share links)** - "canDownload: false · downloadVideoUrl: null · activateDownloadUrl: null"
  - *Establishes:* Why intake across the portfolio is a human paste and not an API pull — and, by the same token, why every claim of automated ingestion has to be withdrawn on stage.
- **Gisselle's reply, file 05 §1; file 05 "Not received": "The report walkthrough video - requested, not sent"** - "Client report example: [Canva /edit link] · Template: [canva.link]"
  - *Establishes:* We have a real design target (section order, metric set, length, register) but as a write-capable link into a live client asset — hence read-only by policy — and we do not have the video, which is why the 90-second script leg is cut rather than guessed at.
- **Audit sheet, rows 4-15 (programmatically verified, file 00)** - "Column F ("Total Time spent per Month (hrs)") was filled for only 2 of 12 rows, so the sheet yields no total. Every one of the 12 rows is assigned to Gisselle, and every one is in department "Operations / Admin / Internal"."
  - *Establishes:* The sheet's biggest cost has no row in it. The unused department dropdown includes "Reporting & Analytics." Naming this omission out loud is more useful than pretending the card maps to a row.

### What we build

A one-page, client-ready executive summary generated on demand from two inputs: a metric set for the reporting period, and the client's own account record. It is a single self-contained HTML page (print-to-PDF at Letter, one page) that reproduces the section order and metric vocabulary of their actual Canva report and returns four things in plain English:

1. A headline sentence — what happened this month, no jargon, no acronym that is not already in their own report.
2. A compact metric table — the same metric names their Canva report uses, each with the prior period and the delta, and each carrying a visible provenance chip (`MOCK` or `LIVE · GHL`). No screenshots.
3. A trend plus its cause, and this is the whole point of the card. The trend is read off the numbers. The cause is joined to card 2's ad-account change log and rendered as a clickable citation — "leads fell in week 3; outbound-click conversions were moved from primary to secondary on the 12th," resolving to the change-log record and then to the timestamped moment in the call where Carmen says it. If no logged change plausibly explains the movement, the cause slot renders "No logged account change explains this — needs a human" and the run is tagged into the spine's abstain queue. It will not manufacture a reason.
4. A recommendation, with a named owner and a flag for whether it needs client approval, drafted in the register of their own "Full service email templates" corpus.

Output lands as one Slack review card in the same channel the rest of the portfolio uses: the PDF, the four-line summary of what it claims, the provenance map, and Approve / Edit / Needs a human. Approve does not send anything to anyone — it stamps the artifact approved, writes it to the internal Drive tier, and appends the summary and its evidence ids to `client_brief.md` and the `updates/` log so next month's run knows what was already said.

Whitney's own framing — "something clearer for clients to understand as opposed to like so many screenshots of the metrics" (Sept 2 @33:01) — is the spec, and the compression is deliberate: N screenshots become one page with one cause sentence that has a receipt attached.

### Scope boundary - what is deliberately out

IN SCOPE
- One client, one month, run on demand from the Slack intake channel.
- One HTML page rendered to a one-page PDF, matched to the Canva report's section order and metric names.
- Mock metric fixtures for Google Ads and Meta, shaped to that report's metric set, two periods (report month + prior), every number provenance-chipped.
- The cause join against card 2's change log, with clickable evidence citations and a hard-coded abstain path when no change explains the trend.
- Register grounded in the real "Full service email templates" Drive corpus.
- One Slack review card with Approve / Edit / Needs a human, plus the write-back to `client_brief.md` and `updates/`.
- STRETCH, not promised: one live metric block — lead volume and opportunity-stage counts pulled from the client's LeadLock/GHL sub-account — and only if the GHL Agency Admin grant is already accepted and verified for card 2. If it is not verified by Wednesday, the whole metric set is mock and we say so.

DELIBERATELY OUT, and why
- The 90-second walkthrough-video script. CUT. The video was requested (file 03) and never sent (file 05 "Not received"), so register and length were pure guesses — it was the least-grounded leg of any selected card. Faking it would be the one thing on this page with no design target at all. It returns for +0.2d the day the video arrives, and it comes back as a script for a human to record: Whitney's video is client hand-holding, which hard constraint 2 puts off limits to automation permanently.
- Generating anything in Canva. The Canva Connect API was never requested (file 03), the sample arrived as a write-capable `/edit` link into a live client report, and no Canva credential enters this build. Read-only by policy. Output format is HTML/PDF, and we say on stage that we are deliberately not writing into their live asset.
- Screenshot capture, ad-creative thumbnails, and any image generation. This is the thing being replaced, per her own words. No headless browser, no ad-account screenshotting.
- Live Google Ads / Meta Marketing API metric ingestion. Never requested (file 03: "NOT REQUESTED"). Mock fixtures, labelled. The ask goes in this week's follow-up with the exact scopes named.
- Sending the report to a client. There is no send code path in this card, by design — not a disabled flag, no function. The client-facing Drive tier is card 1's gated write, and even that sits behind the same review card as outbound email (file 05 §1: the `wia+ridgefield` sub-folder is client-visible, so a mis-tiered write leaks internal material).
- Multi-client batch runs and month-start scheduling. Out for the MVP. Whitney's real need is "the first few business days of the month" across all active clients, but that is a cron entry plus a per-client loop over an already-working generator — an Apollo week-1 configuration change, not a blueprint build. Building it now buys nothing demonstrable on Thursday.
- Goals, targets and pacing ("vs target CPL"). Out. No KPI or target data exists anywhere in what we hold — not in the questionnaire we do not have, not in the Canva report, not in either transcript. Inventing a target would be the single most dangerous fabrication available on a client-facing page.
- Trend history deeper than one prior period. Out. The fixtures only support month-over-month; claiming a six-month trend line off two data points would be a lie in chart form.
- Any recommendation that executes. Recommendations are drafted text with a named owner. Nothing changes a budget, a bid, a campaign or a conversion action.
- Tina's process itself. She owns this workstream and has never been interviewed (file 04). This card is designed against her artifact, not against her process, and we say so rather than implying we modelled her work. Fifteen minutes with Tina is the first action in Apollo week 1.

### Architecture

TRIGGER
One message in the single portfolio intake Slack channel: `report ridgefield 2026-08`. Same surface as every other card — Slack is the only tool with 100% team adoption, ClickUp was never adopted ("the team has never, like, fully adopted ClickUp other than to just, like, check off the tasks", Sept 2 @42:16), and "dashboard" appears zero times in either transcript. Received via Socket Mode (`app_mentions`/`message.channels`), no public webhook.

STAGE 1 — resolve the client record (spine, reused)
Drive v3 as `ai@weddingindustryads.com` (OAuth, `drive.readonly` + `drive.file` on the folders we own). Client folders live in a Shared Drive (file 05 §1), so every call carries `supportsAllDrives=true&includeItemsFromAllDrives=true` — omitting these is the classic silent-empty-result bug. `files.list?q='<clientFolderId>' in parents and trashed=false` to locate `client_brief.md` and `updates/`; `files.get?alt=media` to read. Every path resolved through the spine's tier map, which tags each folder `internal` or `client_facing`; this card reads internal and writes internal only.

STAGE 2 — load metrics
Adapter interface `get_metrics(client_slug, period) -> MetricSet`, where every metric is `{name, value, prior_value, unit, provenance, source_label}`.
- `MockAdsSource` — reads `fixtures/metrics/<slug>/<YYYY-MM>.json`. Metric names and ordering are lifted by hand off the received Canva report so the page is field-for-field recognisable. `provenance: "mock"`.
- `GHLLeadSource` (stretch) — GHL API v2, `POST /contacts/search` and `POST /opportunities/search` with `locationId` = the client's LeadLock sub-account, headers `Authorization: Bearer <Private Integration Token>` and `Version: 2021-07-28`, filtered on `dateAdded` within the period. `provenance: "ghl_live"`. The PIT/auth client is already built for card 2's roster join, so this is one endpoint, not a new integration. Gated on the invite actually being accepted at Agency Admin — file 03 flagged GHL API availability as only ever "most likely" on-call, and file 05 §1 says permission level is "NOT confirmed by her."
- No Google Ads or Meta adapter exists in this build. Not stubbed, not commented out — absent, so it cannot be mistaken for real.

STAGE 3 — cause join (the only genuinely new logic)
Card 2 writes `clients/<slug>/updates/change-log.jsonl`, one record per extracted account change: `{id, client_account, change_type, field, before, after, changed_on, source_call_id, source_platform, source_timestamp_s, evidence_url, confidence, quote}`. This card selects records where `changed_on` falls inside the period or the 14 days before it, then ranks candidates against the moved metric using a small hand-written plausibility table — conversion-action change → conversions/CPL/lead volume; negative keywords → CTR, impressions, spend efficiency; budget change → spend, impressions; new campaign → everything — tie-broken by proximity to the inflection point. Top three candidates go to the model as *candidates*, never as a conclusion.

STAGE 4 — one model call
`POST https://api.anthropic.com/v1/messages`, headers `x-api-key` and `anthropic-version: 2023-06-01`. `model: "claude-opus-5"`, `output_config: {effort: "high"}`, adaptive thinking (default on this model — do not pass `budget_tokens`, it is rejected). Output is forced through a single strict tool: `tools: [{name: "emit_executive_summary", strict: true, input_schema: {...additionalProperties: false, required: [...]}}]` with `tool_choice: {"type": "tool", "name": "emit_executive_summary"}`, so the response is schema-valid JSON or an error — no prose parsing.
Schema fields: `headline`; `period`; `metric_table[]` (name, value, prior, delta_pct, provenance); `trend` (metric, direction, magnitude_pct, window); `cause` (`status: "sourced" | "no_logged_change" | "low_confidence"`, `sentence`, `evidence[]` where each entry must carry a `change_log_id`); `recommendation` (sentence, owner, rationale, `requires_client_approval`); `what_we_did_this_month[]`; `avoided_jargon[]`.
Request assembly is cache-ordered — `tools` → `system` → `messages`, with `cache_control: {"type": "ephemeral"}` on the tools block and on the stable system block (the report layout spec lifted from Canva, the register exemplars from the "Full service email templates" corpus, and `agency_playbook.md`'s standing rules: no unexplained jargon, no promises, no spend commitments, always name an owner). Volatile per-run content — the metric set, the candidate change-log records, the client brief — goes last in `messages`, so the cached prefix survives across every client's run that month. Verify with `usage.cache_read_input_tokens`; if it is zero on the second run, something in the prefix is moving.

STAGE 5 — the fabrication guard, enforced in code and not in the prompt
Post-validation, before rendering: if `cause.status == "sourced"`, `cause.evidence` must be non-empty and every `change_log_id` in it must be one of the ids actually passed in. Any id that was not supplied, or an empty evidence array, downgrades the field to `no_logged_change`, replaces the sentence with "No logged account change explains this — needs a human", and pushes the run into the spine's abstain lane. A model handed metrics and no change log will always produce a plausible-sounding cause; the prompt cannot be trusted to prevent that, so the renderer does.

STAGE 6 — render
One self-contained HTML file, Canva-matched section order, print CSS for one Letter page. Mock numbers carry an inline `MOCK` chip and the footer carries one disclosure line. The cause sentence renders as a link: Fathom sources become `https://fathom.video/calls/{call_id}?timestamp={seconds}` — their own convention, per the probe finding in file 05 §4d — and Zoom sources degrade to a bare `@MM:SS` plus the transcript filename in Drive, because a Zoom `.txt` has no shareable player URL. That degradation is printed on the page, not hidden.

STAGE 7 — review gate and write-back
Drive v3 `files.create` (multipart, `supportsAllDrives=true`) into the client's INTERNAL tier. Slack `files.getUploadURLExternal` → `files.completeUploadExternal` to attach the PDF to a message in the review channel, with the provenance map and Approve / Edit / Needs a human as the spine's poll gate (reactions plus threaded replies). Approve appends the approved summary, its evidence ids and the reviewer to `client_brief.md` and `updates/<ts>-monthly-summary.md`. Edit captures the reviewer's rewrite as a diff into `agency_playbook.md` candidates — how the register actually gets learned, since we have never spoken to the person who writes these today.

RUN LEDGER
`runs/<ts>-<slug>-report.json`: input hashes, model request/response ids, token counts and cache-read counts, the full provenance map, and every abstain event. Honest caveat on the spine's 30-day backtest: for this card it is degenerate. We hold exactly one change-log source session (Feb 12) and zero real metric periods, so the backtest checks the join and the abstain guard against hand-built fixtures — three where a change explains the trend, two where none does — and nothing more. It is not a claim about accuracy on their real data.

### Data position

REAL, in hand, and load-bearing
- The client monthly report as a Canva `/edit` link plus the Canva template (file 05 §1). Gives layout, section order, metric names, length and register. Treated as read-only by policy: it is a write-capable link into a live client asset and `ai@` must never modify it. No Canva credential is in the build.
- The "Full service email templates" Drive folder (file 05 §1) — a real corpus for the drafting register, replacing what would otherwise have been an invented tone profile.
- The Shared Drive plus Ridgefield's client folder — a real filing target, and the internal-vs-client-facing tier fact that governs where this card is allowed to write.
- The cause layer's source: the Feb 12 Google Ads office-hours transcript, copied out of Fathom by the client herself. Probe findings in file 05 §4d/§4e give us real changes on two real client accounts, nine negative keywords, two unlogged spoken commitments, and Fathom's own `?timestamp=` deep links as the citation convention.

MOCK, and how it is disclosed
- All Google Ads and Meta metrics. JSON fixtures, two periods, metric names lifted off their Canva report so the page is recognisable. Every number wears an inline `MOCK` chip, and the page footer carries one line: "Metrics in this example are fixtures shaped to your own monthly report. We have not asked for Google Ads or Meta API access — that ask is in this week's email. Everything else on this page comes from your files and your calls."
- The client brief's positioning and differentiator fields, until the completed onboarding questionnaire is found. Gisselle described the exact mechanism that should put it in Ridgefield's Drive folder — Sept 2 @29:46: "we will download it from Dipsado and Gisselle will save it in the client's Google Drive folder" — so the Drive inventory may retire this mock before Thursday. Until then it is labelled.
- Why the disclosure does not deflate the demo: the numbers are not the thing being demonstrated. The sentence underneath them is, and that sentence is real end to end — a real change, made by a real person, on a real client account, on a real date, with a clickable receipt. Jainil says the mock line out loud in the first thirty seconds, before anyone can discover it and start discounting. Whitney's "Victor" comment (Sept 2 @33:01) proves she is picturing live platform connections, so leaving that expectation unaddressed for two minutes is the fastest way to lose the room.

STILL NEEDED, and from whom
- Google Ads API + Meta Marketing API access to client ad accounts — Whitney to authorise, Carmen and Jacqueline to action. Named in this week's follow-up with the specific scopes. Without it there is no path to live metrics, ever.
- The report PDF exactly as sent to a client — Gisselle or Tina. The `/edit` view shows template scaffolding, not the delivered artifact, so our layout match is currently to the wrong version of the object.
- The walkthrough video — Gisselle or Tina. The sole reason the script leg is cut rather than shipped.
- Fifteen minutes with Tina — Whitney to authorise. She owns this workstream and has never been interviewed (file 04). Everything about register and length in this card is designed against an artifact, not against the person who makes it. This is the largest un-de-risked assumption on the card and it should be said plainly.
- Confirmation of GHL Agency Admin and whether client LeadLock sub-accounts are readable under the agency token — Gisselle. Decides whether one metric family on the page is live or mock.
- One recent office-hours transcript per platform, via the same paste route — Gisselle. Card 2's change log currently rests on a single seven-month-old session, which means so does this card's cause layer.

### How it connects to the rest

This card is the clearest demonstration in the portfolio that twenty automations collapse onto about six builds on one spine, for a simple reason: it is 0.25 days of net-new work and roughly 1.0 day of functionality, and the difference is entirely borrowed.

What it consumes from the shared spine, unchanged: the Anthropic strict-tool extractor and its request/caching discipline; the confidence/abstain lane (the "needs a human" cause status is that lane, not a bespoke feature); the Slack poll review gate; the Drive v3 Shared-Drive client and the internal-vs-client-facing tier map; the `client_brief.md` + `updates/` read/write convention; `agency_playbook.md`; the GHL v2 Private-Integration-Token client built for card 2's roster join; and the run ledger. It adds one output schema, one renderer, one fixture set, one plausibility table and one guard.

What it consumes from its siblings: card 1 (The Handoff) fills `client_brief.md` from client calls, signatures and internal meetings — the positioning, the offer, the owners. Card 2 (What we changed, what we promised, who showed up) writes `change-log.jsonl`, which is this card's cause layer. The dependency is real and it runs one way: without card 2, this card's recommendation section is inferred from numbers alone, and we would say that on the day rather than let the page imply otherwise. That is the honest version of "how is it all connected" — not a diagram, a hard dependency you can watch fail.

What it writes back: the approved summary, its evidence ids, the reviewer and the reported-on period, appended to `client_brief.md` and `updates/`. The period marker matters — next month's run reads it to avoid re-narrating a cause it already reported, and the spine's staleness confirm-or-correct job uses it to ask whether last month's recommendation was ever acted on. This is where the card stops being a document generator and starts being a record.

Shared triggers and surfaces: same intake channel, same review card grammar, same evidence-link renderer (Fathom `?timestamp=` deep link where one exists, bare `@MM:SS` where the source is Zoom), same voice corpus as card 1's recap and welcome emails. Nothing here is a second system with its own login.

And it answers the question that has been open across three calls (Aug 26 @19:21: "how is it all connected? How does it all kind of work together sort of thing?") by construction rather than by assertion: click a sentence in the monthly report and land on Carmen, in a call, saying the thing that caused the number.

### Effort

0.25 day net-new (~2 hours of build), and it is only 0.25 because the spine and cards 1–2 have already paid for everything expensive.

Breakdown: output schema + prompt + playbook rules 0.05d; HTML/print renderer with provenance chips and the citation link logic 0.08d; mock fixtures hand-lifted off the Canva report 0.05d; cause join, plausibility table and the evidence-id guard 0.05d; Slack card and Drive write, reusing the spine's clients 0.02d.

Stated honestly: presented as a standalone product this card is closer to 1.0 day — the Slack gate, the Shared-Drive client, the abstain lane, the voice-corpus loader, the brief reader/writer and the run ledger would all have to be built for it alone. The 4× difference between 0.25 and 1.0 is the document's central argument, and this is the cleanest place to show it.

Portfolio position: last built, first shrunk. Against roughly 4.0 real days of capacity (2.3 + 0.7 + 0.5 + 0.25 + 0.25 = 4.0, with a half day already reserved for rehearsal and pre-generating artifacts), this card is the shock absorber. If cards 1 or 2 overrun on Wednesday, this one ships as a pre-generated artifact plus a live re-render of the cause click — which is 90% of the demo value at near-zero build risk, because pre-generation is already inside the reserve.

Conditional adds: +0.15d for the GHL live lead block, taken only if the GHL grant is verified for card 2 first and costs nothing else. +0.2d to restore the 90-second walkthrough script, the day the video arrives.

### Demo beats

1. 0:00 — Their actual Canva report is already open on the left of the screen. Jainil: "This is one month, one client, built by hand. Whitney, your words on the second: Tina spends the first few business days of the month on these, and it's 'a very, like, painstaking process.' Nobody in this engagement filled in a sheet row for it — and it's bigger than every row that is in the sheet."
2. 0:20 — In the same Slack channel the other cards used, type: `report ridgefield 2026-08`. "Same channel as the transcripts. One place things go in, one place you approve them. No new tool, no dashboard."
3. 0:35 — While it runs, name the four steps out loud so the wait is content, not silence: read the client record out of your Shared Drive, load the metric set, join the account-change log, one model call with a locked output schema.
4. 1:00 — The review card lands with a one-page PDF. Open it beside the Canva deck and hold them side by side. "Same sections. Same metric names — we lifted them off your report. One page instead of a stack of screenshots, which is what you asked for: 'something clearer for clients to understand as opposed to like so many screenshots of the metrics.'"
5. 1:20 — Point at the MOCK chips before anyone asks. "Every number on this page is a fixture. We never asked you for Google Ads or Meta API access, so we do not have your data — that ask is in this week's email, and it is the only thing standing between this page and real numbers. The shape is yours. The numbers are ours, and they say so on the page." If GHL verified: point at the one line that reads LIVE · GHL. If not: say it is not verified yet and move on.
6. 1:40 — Run the abstain case first, to earn the next beat. Open a second run where the numbers moved and nothing in the record explains it. The cause line reads: "No logged account change explains this — needs a human." "It will not invent a reason. If there is no receipt, it says there is no receipt and it goes to a person. That rule is in the code, not in the prompt."
7. 2:05 — Now the payoff. Back on the first page, click the cause sentence. It resolves to the change-log line from card 2 — outbound-click conversions moved from primary to secondary on two accounts — and then straight into fathom.video/calls/566502955?timestamp=… , Carmen, on the call, saying it. "Tina writes that sentence today from memory, four weeks after the fact. This one has a receipt, and the receipt is Carmen's own voice. That is the difference between a report that says what happened and a report that says why — and this page only works because the other card exists."

### Risks

- FABRICATED CAUSE — the top correctness risk. A model handed metrics and no change log will produce a fluent, wrong explanation, and it would go onto a client-facing page. Mitigated in code, not in the prompt: a sourced cause must carry change-log ids that were actually passed in, or it is forcibly downgraded to "needs a human." This is demoed deliberately (beat 6) because the client will recognise the risk herself and needs to see it handled.
- THE CAUSE LAYER RESTS ON ONE SEVEN-MONTH-OLD SESSION. Card 2's change log currently has exactly one source: Feb 12. If card 2 slips or is cut, this card's recommendation section degrades to inference from numbers alone — which is what Tina already does, minus her judgment. Say that on the day; do not let the page imply a sourced cause it cannot produce.
- MOCK METRICS MAY NEVER GO LIVE. Google Ads needs a developer token and OAuth on ai@ with the client accounts linked to a manager account; Meta needs an app, a System User token via Business Manager, ads_read, and App Review for advanced access. Both are measured in days-to-weeks, not hours, and both need client action. E2M inference to verify, not a fact: since WIA manages these accounts, the linkage probably already exists — but nobody has confirmed it. If the asks are not made this week, this card demos on fixtures for the whole of Apollo week 1.
- REGISTER MISS, WITH NO WAY TO PRE-TEST IT. Tina has never been interviewed, the PDF-as-sent never arrived, and the video never arrived. We are matching a /edit template view. Whitney's bar is that she is not "doing double work and then... having to heavily edit or completely rewrite stuff" (Aug 26 @39:55) and the only way to measure it before Thursday is to ask her live, which we will.
- WRITE RISK ON A LIVE CLIENT ASSET. The report sample is a write-capable Canva /edit link. An accidental write is a client-visible incident on the client's own report. Mitigated by policy and by absence: no Canva credential, no Canva client, no Canva code path in the build. Stated on stage as a deliberate choice.
- EXPECTATION GAP ON "VICTOR." She has been playing with a Slack agent that connects live to LeadLock, Google Ads and Meta (Sept 2 @33:01). If the mock disclosure comes late, everything after it gets discounted. Mitigation is sequencing: the disclosure is beat 5 of 8, before the payoff, and Jainil says it unprompted.
- CUTTING THE VIDEO SCRIPT REMOVES SOMETHING SHE VALUES. The walkthrough video is client hand-holding, which is the thing wedding-industry clients buy. Cutting the script leg is the right call on evidence grounds, but it must be framed as "we will not guess at this" and paired with the ask, not left as a silent omission.
- MIS-TIERED DRIVE WRITE. Ridgefield's folder contains a client-visible sub-folder (file 05 §1). A report written to the wrong tier is internal material delivered to a client and breaks the hardest constraint in the engagement. Mitigated by the spine's tier map plus the review gate, and the tier is printed on the review card so it is visible, not assumed.
- THE 18-24 HRS/MONTH FIGURE IS OURS, NOT HERS. It is derived from "the first few business days of the month." If it is presented as her number and she disputes it, the card's whole business case wobbles. Present it as an E2M derivation, invite her to correct it, and lead with the onboarding-delay argument instead, which does not depend on the number being right.
- SCOPE CREEP INTO A REPORTING PRODUCT. Charts, targets, multi-month trends, per-platform breakouts and batch scheduling all look like small additions and are collectively a week. The scope boundary above exists to be enforced on Wednesday, not admired on Monday.

### Production path

Apollo week 1 — close the two gaps that decide whether this is a real product or a good-looking page. (a) Fifteen minutes with Tina, then a red-team pass: she marks up three generated pages, and her edits become rules in agency_playbook.md. She is the only person who knows what this artifact is for, and nobody has asked her. (b) The report PDF as sent and the walkthrough video, which restores the 90-second script leg for +0.2d — as a script for Whitney or Tina to record, never as synthesised narration.

Week 1-2 — live metrics. Google Ads API: developer token, OAuth on ai@, client accounts confirmed under a manager account; the standard-access review is the long pole. Meta Marketing API: a Meta app, System User token via Business Manager, ads_read, App Review for advanced access, client ad accounts assigned to WIA's Business Manager. Each adapter drops in behind the existing get_metrics interface and flips the provenance chip from MOCK to LIVE per metric — the page does not change shape when the data becomes real, which is the point of building the provenance layer first.

Week 2 — batch. A cron on the first business day, one run per active client, N review cards in one Slack thread, Tina approving or editing each. This is a configuration change over a working generator, and it is what actually recovers the days at the start of the month. It is also where the second-order value lands: Tina's first few business days go back to landing pages, so a client signing on the 3rd stops waiting on the report cycle.

Week 3+ — depth, in this order. Historical baselining (6-12 months per client) so trend statements have a real baseline rather than one prior period. A goal/KPI layer: capture each client's target CPL and lead volume at onboarding as a field on the questionnaire that flows into client_brief.md, so the summary can say "against your target," which is what turns a report into a conversation. Then the LeadLock-side story — form submissions, opportunity stage movement, nurture performance — which is the half of their value proposition the current report barely covers and which is reachable through the GHL token we already hold.

Permanently out of the production path: automated delivery to the client. The summary always terminates in a human review, and the client conversation about it stays a human conversation. That is hard constraint 2, and it should be reaffirmed rather than quietly revisited when the automation starts working well.

### Success criteria

- ONE PAGE. The rendered PDF is a single Letter page, and the section order and metric names match the received Canva report when the two are held side by side. Checked by eye against the real artifact, not against a description of it.
- ZERO UNLABELLED NUMBERS. Every value on the page carries a provenance chip, and the footer disclosure line is present. A page that renders with a missing provenance field fails the build, not the review.
- ZERO UNSOURCED CAUSES ACROSS FIVE RUNS. Five fixtures: three where a logged change plausibly explains the movement (the cause must cite a real change_log_id with a working evidence link), two where nothing does (the cause must abstain to "needs a human"). Five for five, or the card does not ship.
- THE CITATION RESOLVES. Clicking the cause sentence lands on the change-log record and then on fathom.video/calls/566502955?timestamp=… at the moment Carmen makes the change. For a Zoom-sourced fact it renders a bare @MM:SS plus the transcript filename, and the page states the difference rather than hiding it.
- UNDER 90 SECONDS from the Slack command to the review card appearing, on the demo machine, twice in a row.
- NOTHING SENDS. Reviewed by code inspection: no client email address is present in the artifact or the config, and there is no send function in the code path. The run terminates at the review card; the internal-tier Drive write is the only write.
- JARGON: zero acronyms or platform terms on the page that are not already present in their own Canva report, or that are not expanded on first use. Counted manually against the report's own vocabulary.
- THE REVIEWER EDITS RATHER THAN REWRITES. Whitney's own bar from Aug 26 @39:55. Honestly stated: this is subjective and un-pre-testable because Tina has never been interviewed, so the measurement is asking Whitney live on Thursday whether she would edit this or rewrite it — and recording her answer either way.
- THE RECORD GROWS. After an Approve, client_brief.md and updates/ contain the approved summary, its evidence ids, the reviewer and the reported-on period — visible on screen. If the record does not change, the card is a document generator and has failed its actual purpose.
- COMMERCIAL CRITERION, stated without inflation: Whitney can articulate back, in her own words, why this page's cause sentence is different from the one Tina writes today. If she cannot, the demo failed regardless of what shipped.

---

## MVP 5 - One voice note, a month of marketing

**A client call plus thirty seconds of your direction in; three reel scripts with cited quotes out, then carousel copy, then the marketing email — each stage held for your approval before the next one runs.**

*Effort: 0.25 days. Status vs previous plan: CONDITIONALLY UNBLOCKED and trimmed. The block did not shrink, it changed character: the client offered the artifact herself ('Client meetings are held in Whitney's zoom so it's just the txt file downloaded from zoom. Would that or a summary work best?'). But it is not one ask away from being GOOD — the card needs a call where the client praised results, and Whitney is the human filter who remembers which ones those are, so the ask must be qualified or we get a flat reel script off a routine budget-tweak call. Trimmed from 0.5d by routing the voice note through the same Slack paste channel as *

### The problem today

Today this workstream runs entirely on Whitney's memory and a five-hop human chain, and it starts with her recalling that a particular call went well. Her own description, Aug 26 @19:21: "I had this strategy call with a client, they said all these amazing things about our work or the growth of the business or how things are feeling, I want to take that and then turn it into content, right? So I'm, like, flagging it to Gisselle and saying, hey, take the transcript from this call, put it into ChatGPT, see if it can come up with, like, a script for a reel that I can record, right? And then it's like, I'm going through, I'm refining that, the reel is recorded, and then I'm like, okay, well, now we need to turn it in. Into a carousel. Now we need to turn it into a piece of, like, email marketing."

Unpacked, that is: (1) Whitney remembers which call contained praise — she is the only index; (2) she Slack-messages Gisselle; (3) Gisselle downloads the .txt from Whitney's Zoom (Sept 2 @6:54, Whitney: "it's my Zoom, my, you know, note taker, my recordings, all of that") and pastes it into the shared ChatGPT login — the company has no Team or org account, Sept 2 @31:28, Whitney: "We just have an account for the hello at weddingindustryads.com. The team members have the login information"; (4) Whitney refines the script and records the reel; (5) the carousel and the marketing email are each a fresh manual re-ask, days later, against a script that has since changed. She called the whole thing "a very heavy lift" in the same breath (Aug 26 @19:21).

Two structural facts about the problem matter more than the hops. First, it is the only item in the entire engagement anybody connected to money. Aug 26 @19:21, Whitney: "But we need more leads. We need more sales. We need to be bringing more clients in. And if we're not marketing actively, that's not going to happen." Second, it is invisible in the document that was supposed to surface her automation opportunities. The client-filled audit sheet contains twelve rows (4–15), every one assigned to Gisselle, every one in the department "Operations / Admin / Internal"; the words reel, carousel, content and marketing appear in none of them. The sheet was scoped to one outside contractor's operational seat, so the revenue-side workstream Whitney raised herself, unprompted, has no row and no hours.

It also has had no discovery follow-up. On Aug 26 @22:15 Minu deferred it explicitly — "For today, I want to focus on the efficiencies and just make sure we understand Gisselle's process. And the following weeks, we will take up the fulfillment aspect of it" (transcript labels this line Whitney; the content is Minu setting the agenda) — and Sept 2 opened by promising to return to it, then spent its forty-eight minutes on invoices, portal posts and onboarding and never came back. So everything below is built on a single unrevisited stretch of Aug 26. That is stated here rather than smoothed over, because it is the honest reason this card is ranked fifth rather than first.

### Evidence

- **Aug 26 call @19:21 (Whitney)** - "But we need more leads. We need more sales. We need to be bringing more clients in. And if we're not marketing actively, that's not going to happen."
  - *Establishes:* The only place in either transcript where any workstream is tied to revenue. Everything else discussed across 92 minutes was cost or admin. This is why a 0.25-day card earns a place in a four-day budget.
- **Aug 26 call @19:21 (Whitney)** - "I had this strategy call with a client, they said all these amazing things about our work or the growth of the business or how things are feeling, I want to take that and then turn it into content, right?"
  - *Establishes:* The extraction target, verbatim and in her own categories: praise of the work, growth of the business, and how things feel. These become the quote_type enum in the extractor's tool schema — not E2M's invention.
- **Aug 26 call @19:21 (Whitney)** - "I'm, like, flagging it to Gisselle and saying, hey, take the transcript from this call, put it into ChatGPT, see if it can come up with, like, a script for a reel that I can record, right?"
  - *Establishes:* The current process is a five-hop human chain, and Whitney personally is the index of which calls are usable. Thursday's build compresses hops 2 through 5; it deliberately does not replace hop 1.
- **Aug 26 call @19:21 (Whitney)** - "And then it's like, I'm going through, I'm refining that, the reel is recorded, and then I'm like, okay, well, now we need to turn it in. Into a carousel. Now we need to turn it into a piece of, like, email marketing."
  - *Establishes:* The sequence is strictly staged around a human recording step. This is the architectural justification for gating: the carousel and the email must derive from the APPROVED, post-refinement script, never from the draft. Generating all three up front would discard her edits.
- **Aug 26 call @19:21 (Whitney)** - "even if I'm just, like, giving it a voice note of, like, hey, I want to reference this call. Here's more context. Here's more history. This is the direction that I want to take it."
  - *Establishes:* The voice note is her own idea and her own phrasing, not a demo flourish we invented. The card's name is a quotation.
- **Aug 26 call @39:55 (Whitney — the transcript mislabels adjacent lines in this block as Minu; the content is Whitney answering about her own inbox)** - "it's not things where I'm, like, doing double work and then, like, going in and having to, like... Heavily edit or like completely rewrite stuff, right?"
  - *Establishes:* Her stated adoption bar, and the second justification for the staged gate: an edit must propagate downstream, never be re-applied by hand at each stage.
- **Aug 26 call @40:03 (Whitney — line labelled Minu; content is Whitney continuing her own answer)** - "there's some sort of process in place where it's learning from my output of what I'm sending out, right? Like it sounds like it's in my voice."
  - *Establishes:* Voice fidelity is her acceptance test. We hold no corpus of her published reels or captions — nothing social was requested in the Sept 3 access email — so this is a named, unclosed calibration gap, the exact mirror of MVP4's uncalibrated walkthrough script.
- **Aug 26 call @39:09 (Whitney)** - "My biggest thing is just making sure that, like, the end output is good, right? And it's not, like, negatively affecting the client experience in any way or what the leads are experiencing."
  - *Establishes:* Why client names are off by default and why any number not traceable to a verified quote is flagged rather than asserted. A wrong public claim about a client's results is the highest-blast-radius output in the whole portfolio.
- **Sept 2 call @8:01 (Whitney)** - "we'll review any drafts before they go out"
  - *Establishes:* The hard constraint that governs every stage. Nothing in this card posts, publishes or sends; the marketing email terminates as a draft.
- **Sept 2 call @6:54 (Whitney)** - "it's my Zoom, my, you know, note taker, my recordings, all of that"
  - *Establishes:* The corpus this card runs on is Whitney's native Zoom, not Fathom — which is precisely why its citations degrade from clickable deep links to bare timestamps. The honesty regression is a direct consequence of this sentence.
- **Gisselle's reply, Sept 5–7 2026 (file 05 §1, verbatim)** - "Client meetings are held in Whitney's zoom so it's just the txt file downloaded from zoom. Would that or a summary work best?"
  - *Establishes:* The single blocking artifact was offered by the client, who asked only which format we want. Acquisition is one reply — the cheapest status change on the board. It also means the reply must be qualified, or we get a routine call and a flat demo.
- **Aug 26 call @22:38 (Minu)** - "Maybe you have an agent who looks at all your transcripts automatically and pushes ideas for your reels, and has those scripts ready, and once those are ready, how do you feed, how does the feedback loop work in terms of when using that content, like you mentioned, for carousels, et cetera."
  - *Establishes:* E2M already described a staged feedback loop on-call, and also promised something this MVP deliberately does NOT deliver on Thursday: looking at all transcripts automatically. Intake is a human paste. That gap must be named on stage, not glossed.
- **Technical probe finding, file 05 §2** - "canDownload: false · downloadVideoUrl: null · activateDownloadUrl: null on BOTH share links; the only working transcript route is https://fathom.video/calls/{id}/copy_transcript?token={share_token} — HTTP 200, unauthenticated, behind Cloudflare"
  - *Establishes:* No export exists on either sample, so we cannot manufacture a Fathom export to compare against a Zoom .txt. 'One normalizer serves both source systems' is therefore a design intention, not a verified fact, and the normalizer ships with three parsers behind a format sniffer rather than one.
- **Technical probe finding, file 05 §4d — present verbatim in the client-copied transcript text** - "ACTION ITEM: DM Jillian new VIP day link - WATCH: .../calls/566502955?timestamp=534.9999"
  - *Establishes:* The citation format adopted wholesale, in a convention the team already recognises. It also establishes that clickable evidence exists ONLY for Fathom-sourced quotes, which this card's real corpus is not.
- **Technical probe finding, file 05 §2** - "Meta Ads Office Hours: call_id 801737343, title "Impromptu Zoom Meeting" (never set), host jacqueline@jacquelinehood.com, 2964s, only TWO speakers — Jacqueline Hood and Shannon Lee, screen-sharing a Meta Ads Manager error"
  - *Establishes:* Neither transcript in hand contains a client praising results — both are account troubleshooting. The positive lane of the praise classifier has zero real test data today. This is the weakest point of the card, and the Meta transcript becomes the deliberate negative control in the demo.
- **Audit sheet extraction, file 00 (verified programmatically)** - "12 client-entered rows (4–15), every row assigned to Gisselle, every row in department "Operations / Admin / Internal"; column F filled on 2 of 12 rows"
  - *Establishes:* Zero sheet coverage for this workstream. No hours figure exists for it and none is claimed. The sheet quantifies ~18.1 hrs/month in total across twelve rows of one contractor's operational work; this card is not measured on that axis and must not be defended on it.
- **Aug 26 call @19:21 (Whitney)** - "that's where I get our best content for our own marketing and for our case studies, for example"
  - *Establishes:* The accumulated, permission-tagged quote bank — not the reel scripts — is the durable asset. Case studies were her second named use of the same source material, and the bank is what makes them possible later.

### What we build

A staged content pass that runs on the same intake and the same review surface as everything else in the portfolio.

Whitney (or Gisselle) drops one client-call transcript into the single Slack intake channel — a pasted link, pasted text, or a dropped `.txt`, whichever is convenient that day — and replies in the thread with thirty seconds of direction as a Slack audio clip, or types it if the workspace does not hand us a transcript for the clip.

Stage 1 mines the transcript for usable quotes in her own three categories — praise of the work, growth of the business, how things feel — and verifies every single one character-for-character against a line in the source before it is allowed onto the card. A quote the verifier cannot locate is dropped and logged, never printed. If the call contains no result-praise at all, the card says so and stops, instead of inventing three scripts.

Stage 2 produces three reel scripts, each with a hook, three to five beats, a CTA, on-screen text, an estimated runtime, and its citations rendered honestly: a clickable `?timestamp=` deep link where the source has a player URL, a plain `@MM:SS` where it does not, with the difference visible on the card. Each script also carries two safety fields on screen — `claims_needing_proof`, listing any number or result the script asserts that did not come from a verified quote, and `client_named: false`, because scripts are drafted anonymised ("a Texas wedding venue") and naming the client is a deliberate toggle that simultaneously drafts the permission ask.

Then it waits. On her approval of one script, Stage 3 produces the carousel copy slide by slide, derived from the approved and edited text rather than the original draft. On her approval of that, Stage 4 drafts the marketing email into the `ai@weddingindustryads.com` mailbox as a Gmail draft. Nothing posts. Nothing sends.

Her edit path is a reaction plus a thread reply: the reply is appended to the direction and Stage 2 re-runs against the same verified quote set. That is the demo beat and it is also the daily mechanism — the thing she asked for on Aug 26 was a voice note that redirects the output, not a text box.

Every validated quote is written back to that client's record as a permission-tagged entry, which is what makes this card compound rather than terminate: the record is where MVP4's monthly summary gets the client's own words about how things feel, and where next quarter's case studies come from.

### Scope boundary - what is deliberately out

IN SCOPE for Thursday:
1. One Slack intake channel, shared with the rest of the portfolio, accepting three transcript forms (pasted link, pasted text, dropped `.txt`).
2. Direction as a Slack audio clip where the workspace supplies a transcript for it, and typed thread text otherwise.
3. Quote mining with hard verbatim verification and a working abstain path.
4. Three reel scripts with citations, `claims_needing_proof`, and anonymisation on by default.
5. Sequential gating: carousel copy only after script approval; marketing email only after carousel approval.
6. One marketing email drafted into `ai@`.
7. The permission-tagged quote bank written to the client record, plus a run-ledger entry.

DELIBERATELY OUT, and why each:
- No transcription service. If Slack's own audio-clip transcript is unavailable in this workspace, direction is typed in the thread. Building or hosting speech-to-text for a 0.25-day card buys no demo credibility and adds an unrehearsed dependency to the single highest-drama beat.
- No posting, publishing or scheduling to any social platform, ever, not even behind a delay. Sept 2 @8:01, Whitney: "we'll review any drafts before they go out." A public brand post is the largest blast radius in the portfolio and the review gate is the product, not an obstacle to it.
- No graphic or video production: no Canva render, no caption burn-in, no thumbnail, no voice cloning, no AI-generated likeness of Whitney. She records the reel; that is what a script is for. Canva was never requested (file 03, NOT REQUESTED) and the Canva banner is already descoped from TASK-12.
- Carousel COPY only, not carousel DESIGN. Ivy is the creative designer (Sept 2 @25:50: "Ivy is our like ads creative designer"), design is her lane, and we have no Canva access to build into.
- No client name and no client-identifying detail in any draft unless Whitney explicitly toggles it, which also generates the permission-ask draft. Grounded in Aug 26 @39:09: "it's not, like, negatively affecting the client experience in any way."
- No unverified numbers. If a script wants to say "tripled her bookings" and no verified quote said it, the phrase lands in `claims_needing_proof` for her to confirm rather than in the hook.
- No email SEND, and no send or draft from `hello@weddingindustryads.com`. Gmail API scope on `hello@` was never requested (file 03, NOT REQUESTED) and it is the company's entire client-comms hub. The draft lands in `ai@`; moving it to `hello@` is a named ask, not a silent omission.
- No automatic mining of every client call for Thursday. Whitney remains the selector. Auto-pushing three scripts per client call to an already inundated founder recreates exactly the notification-treadmill failure identified for roll-call at low attendance volume (file 05 §4c). Auto-flagging is a one-field configuration change in Apollo week 1, described under production path — not a Thursday claim.
- No ad copy, no Meta angles, no RSA headlines. That is MVP3's lane; this card is Whitney's own marketing, not client fulfilment.
- No LinkedIn, blog, long-form, newsletter series, or content calendar. She said "multi-purpose that into a lot of content", and the three outputs she named were reel, carousel, email marketing. We build those three.
- No content performance analytics. No Instagram or Meta insights integration was requested and none is implied by anything she said.
- No sales-call-to-proposal path. Different trigger, different card, explicitly not this one.
- No claim of automated transcript ingestion. Aug 26 @22:38 Minu described "an agent who looks at all your transcripts automatically". Thursday's intake is a deliberate human paste and Jainil says that sentence out loud.

### Architecture

TRIGGER — Slack, via the spine's Socket Mode connection (no public webhook, per the spine's constraint). Bot subscribes to `message.channels` and `file_shared` on the single intake channel. Scopes: `channels:history`, `files:read`, `chat:write`, `reactions:read`, `reactions:write`, `users:read`. A dropped `.txt` is retrieved by `files.info` → `url_private_download` with `Authorization: Bearer xoxb-…`. A pasted Fathom link is resolved via the probe-confirmed route `GET https://fathom.video/calls/{call_id}/copy_transcript?token={share_token}`, which returned HTTP 200 unauthenticated with `html` and `plain_text` fields (file 05 §2 finding 3) — used opportunistically, never depended on, because it is undocumented and sits behind Cloudflare. Pasted text is taken as-is.

DIRECTION INPUT — the thread reply. If the reply is a Slack audio clip, `files.info` is polled for `file.transcription.status == "complete"` and `file.transcription.preview.content` is read. If the status is anything else, or the field is absent, the pipeline posts one line — "no transcript came back for that clip; type your direction here instead" — and accepts the next text reply. This is a capability gate, not a build: workspace plan and audio-transcription availability are unverified because the Slack invite has not been accepted (file 05 §1: invites sent, seat levels "NOT confirmed by her").

NORMALIZER (shared spine component; this card adds one parser). Format sniffing, then one of three parsers, all emitting the same record `{t_seconds:int, speaker_raw:str, speaker_side:enum, text:str, source_system:enum, source_call_id:str|null, source_token:str|null}`:
- Parser A, Fathom copy output: `^(?<ts>\d{1,2}:\d{2}(:\d{2})?)\s+-\s+(?<speaker>.+)$` followed by indented body lines until the next header. Also strips Fathom's inline `ACTION ITEM:` and `SCREEN SHARING:` event lines into a separate events array — they are metadata, not speech, and must not be mined as quotes.
- Parser B, Zoom VTT: `WEBVTT` sniff, cue index, `HH:MM:SS.mmm --> HH:MM:SS.mmm`, then `Speaker Name: text`.
- Parser C, Zoom plain caption `.txt`: `^(?<ts>\d{2}:\d{2}:\d{2})\s+(?<speaker>[^:]+):\s*(?<text>.*)$`.
Fallback mode: if no parser yields at least two distinct speakers and five turns, the run does not fail — it degrades to ordered raw lines with `t_seconds: null`, and the card states that timestamps were unavailable. Parsers B and C exist on spec, not on a tested sample: no Zoom `.txt` has been observed, and `canDownload: false` on both Fathom links means we cannot even produce a comparison export (file 05 §2).

SPEAKER SIDE — resolved by matching `speaker_raw` against the WIA roster in `agency_playbook.md` (Whitney, Gisselle, Carmen, Jacqueline, Ivy, Tina, Danielle), NOT by email-domain suffix. The domain heuristic is explicitly rejected: file 05 §2 finding 4 shows Jacqueline hosts on `jacquelinehood.com` and her label renders `Jacqueline Hood (Jacqueline Hood)`, so a core team member classifies as external. Anyone not on the roster is `client`. An unmatched name that speaks more than 10% of turns routes to the abstain lane for a one-click confirm.

STAGE 1 — quote mining. One call to `POST /v1/messages` with `tool_choice: {"type":"tool","name":"emit_quotes"}`, temperature 0, model id pinned at build time from the current Anthropic model list rather than hard-coded here. Input: the normalized transcript rendered as `[t_seconds] speaker_side/speaker_raw: text` lines, plus the client's `client_brief.md` for context on who they are, plus the playbook's forbidden-claims list. Tool schema: `{quotes:[{quote_verbatim, speaker_raw, speaker_side, t_seconds, quote_type: result_praise|outcome_metric|emotional_relief|before_after|objection_overcome|not_usable, claim_supported, is_verifiable_number:bool, confidence:0..1}], no_usable_praise:bool, reason_if_none}`.

VERBATIM VERIFIER — deterministic code, not a model instruction, and the single most important component in this card. Each `quote_verbatim` must be found by exact substring match (whitespace-normalized only) within a single transcript line, and the reported `t_seconds` must equal that line's offset. Failures are dropped, counted, and written to the run ledger as `hallucinated_citation`. The card prints the counts — "4 usable / 11 candidates · 4 verified verbatim · 0 dropped" — so the guard is visible rather than asserted. A fabricated client testimonial is categorically worse than a bad recap email; this is why the guard is a hard gate.

ABSTAIN — `no_usable_praise: true`, or zero quotes surviving verification, routes to the spine's needs-a-human lane. The card posts what it did find, says the call contains no result-praise, and asks for a different call. It does not generate scripts.

STAGE 2 — scripts. Second `/v1/messages` call, forced tool `emit_reel_scripts`, input = verified quotes + direction text + `agency_playbook.md` voice block + `client_brief.md`. Schema per script: `{angle, hook (≤12 words), body_beats[3-5], cta, on_screen_text[], est_runtime_seconds (25-45), citations:[{quote_verbatim, t_seconds, evidence_url|null, speaker_raw}], client_named:false, claims_needing_proof[]}`. Citations may only reference quotes present in the verified set — enforced in code after the call, same as Stage 1.

CITATION RENDERER — if `source_system == fathom` and a call id and token exist: `https://fathom.video/calls/{call_id}?timestamp={t_seconds}.9999`, exactly the format observed verbatim in the copied text (file 05 §4d), rendered as "WATCH 8:55". If `source_system == zoom`: `@8:55 · no shareable link (Zoom .txt)` in muted text, with a one-line footnote on the card explaining why. No link is ever synthesized.

SLACK CARD — one bot message in the intake thread. Header: `Marketing pass · {client} · {call_type} {date} · source: {Zoom .txt | Fathom copy | STAND-IN}`. Then the verification counts, then three script blocks each with its citations, then `claims_needing_proof` in a warning block if non-empty, then `client_named: false — anonymised as "{descriptor}"`. Controls are reactions on the spine's poll-based gate: `✅` approve this script, `✏️` edit (reply in thread; direction is appended and Stage 2 re-runs), `⛔` discard, `🔁` wrong call, `🏷️` name the client (which also drafts the permission ask).

STAGE 3 / STAGE 4 — Stage 3 fires only on `✅` of a script, taking the approved-and-edited text as input, and posts carousel copy slide by slide into the same thread. Stage 4 fires only on `✅` of the carousel and calls `POST https://gmail.googleapis.com/gmail/v1/users/me/drafts` on the `ai@weddingindustryads.com` OAuth credential with scope `gmail.compose`. Draft only. No `messages.send` code path exists in this card.

WRITE-BACK — every verified quote appends to `client_brief.md` under `marketing.quote_bank[]` as `{quote_verbatim, t_seconds, source_system, evidence_url|null, quote_type, permission_state: "not_asked"}`, plus one `updates/` log entry per run recording inputs, model calls, verification counts and approvals. `permission_state` is what makes the bank safe to reuse: MVP4 may quote a client back to that client freely — they said it to us — but only a `granted` quote may ever appear in public marketing. This card writes nothing to Google Drive and touches no client-facing folder tier, so the two-tier leak risk surfaced in file 05 §1 does not apply to it.

### Data position

REAL, today, in hand:
- The full mechanism: Slack intake, three-parser normalizer, forced-tool extraction, the verbatim verifier, the staged reaction gate, the `ai@` Gmail draft. None of this is stubbed.
- Two genuine client-side transcripts to build and test against, in the confirmed copied format: the Feb 12 Google Ads office hours (`call_id` 566502955, 2881s, host carmen@weddingindustryads.com) and the Aug 27 Meta session (`call_id` 801737343, 2964s). Real speakers, real timestamps, real content.
- The Fathom `?timestamp=` deep-link convention, observed verbatim in the client-copied text (file 05 §4d), so the citation renderer's happy path is testable today against live URLs.

MOCK, MISSING, OR UNVERIFIED — stated plainly:
1. No client-praise sample exists in any artifact we hold. Both office-hours transcripts are account troubleshooting; the Meta one is two speakers over 49 minutes, one of them staff, working through a Meta Ads Manager error (file 05 §2). Neither E2M sync call contains a client praising WIA's results. So the positive lane of the praise classifier is, as of today, tested only against a hand-labelled negative set (where correct behaviour is `no_usable_praise: true`) and a synthetic positive set written by E2M. This is the weakest point of this card and it is stated in exactly those words on stage.
2. The Zoom `.txt` is offered, not sent. Gisselle, Sept 5–7: "Client meetings are held in Whitney's zoom so it's just the txt file downloaded from zoom. Would that or a summary work best?" One qualified reply closes it.
3. Zoom's actual `.txt` shape is unverified. `canDownload: false` on both Fathom links (file 05 §2) means we cannot even manufacture a comparison export. Parsers B and C are written to spec, with the raw-lines fallback as the safety net.
4. No voice note exists and none was ever requested in the Sept 3 access email.
5. Slack audio-clip transcription availability is unknown until the invite is accepted; the workspace plan is unconfirmed (file 05 §1).
6. No corpus of Whitney's own published reels or captions. The only voice corpus we hold is the "Full service email templates" Drive folder — client-facing ops register, not founder social register. The reel voice is therefore uncalibrated in exactly the way MVP4's 90-second walkthrough script is, and for the same reason: the calibrating artifact was never asked for.

HOW THE MOCK IS DISCLOSED WITHOUT DEFLATING THE DEMO — the disclosure is printed by the pipeline, not spoken over a slide. The card's own header carries a `source:` field: `source: Zoom .txt · Ridgefield · 2026-09-04` when it is real, or `source: STAND-IN (E2M sync recording 2026-09-02) — mechanism real, the praise is not your client's` when it is not. Next to it sits the machine-generated verification line, `4 usable / 11 candidates · 4 verified verbatim · 0 dropped`, which proves the guard executed on whatever input it was given. The sentence Jainil says is one line long: "the mechanism is real, the praise is not theirs." That costs nothing, because the beat that lands is not whose quote it is — it is Whitney recording thirty seconds of her own direction and watching three hooks change. That input is unambiguously hers, live, in the room, and the mock never touches it.

### How it connects to the rest

This card is the clearest proof of the document's central argument, because it is the cheapest one on the board and it is cheap for exactly one reason: almost none of it is its own.

Spine components reused wholesale, at zero incremental cost: the single Slack intake channel and all three intake forms; the transcript normalizer; the forced JSON tool-schema extractor over `/v1/messages` with source timestamps on every fact; the confidence/abstain lane; the poll-based Slack review gate on reactions and threaded replies; the `ai@` Gmail draft connector; `client_brief.md` and the `updates/` append log; `agency_playbook.md`; and the run ledger. This card adds exactly four things of its own — one transcript parser, two tool schemas, the verbatim verifier, and the citation renderer. That is why it is 0.25 day rather than the 0.5 it was scoped at before the intake decision collapsed its separate voice-note pathway into the shared channel.

Its connector surface is the smallest in the portfolio: no ClickUp, no Drive write, no GHL, no Members Portal. Every one of those is still mock until invites are accepted and seat levels verified (file 05 §1), with three days left. This card depends on Slack and `ai@` only, which makes it the second-least access-exposed item after Page Check.

What it shares with siblings. It shares MVP1's trigger and normalizer verbatim — a client call ending is the same event, and once MVP1 files a client-call transcript into the record, this card no longer needs its own paste at all; it reads from `updates/`. It shares nothing with Page Check, by design, since that card deliberately needs nothing.

What it writes back. Every verified quote lands in `client_brief.md` under `marketing.quote_bank[]` with its timestamp, its source system, its evidence URL if one exists, and a `permission_state`. That bank is the card's durable output — more durable than the scripts. MVP4's executive summary reads it to put the client's own words about how things feel underneath the metrics, so the monthly page carries a human sentence that is sourced rather than remembered, alongside the change-log cause sentence from card 2. The `permission_state` field is what makes the sharing safe in both directions: MVP4 may quote a client back to that same client, because they said it to us; only a `granted` quote may ever reach public marketing.

And it closes the loop Whitney asked about three times. Aug 26 @19:21: "the biggest thing that I'm looking for at this point, I feel like, is like, how is it all connected?" The demonstrable answer here is that the same paste that produced her recap email in card 1 also produced her reel scripts in card 5, from the same normalized transcript, on the same review surface, writing into the same client record — and that the quotes now sitting in Ridgefield's record are the same quotes card 4 will cite next month.

### Effort

0.25 day — roughly two hours incremental on the shared spine, and the smallest build in the portfolio.

Breakdown: the two tool schemas and their prompts, ~45 min against the spine's existing extractor harness; the verbatim verifier and the citation renderer with its two-mode degradation, ~30 min; staged gate wiring plus the `drafts.create` call, ~25 min, reusing the spine's reaction-poll gate; Stage 3 and Stage 4 prompts, ~20 min. Everything else — intake, normalizer, abstain lane, review gate, record read/write, run ledger — is already paid for by the spine's ~1.25 days.

Rehearsal and pre-generation come out of the reserved half day, not out of this 0.25. Both direction paths must be rehearsed, because the live beat is the only unrehearsed dependency in the whole review and it is also the one that matters most.

This card is the reason the portfolio fits four days rather than the previous plan's 4.75 with two pre-committed cuts. If something has to give, note honestly that this is not the item to cut for budget reasons — it costs almost nothing. The reason it might not run well is data, not time.

### Demo beats

1. 0:00 — No slide. "This is the one thing you tied to revenue. August 26, your words: 'we need more leads, we need more sales... if we're not marketing actively, that's not going to happen.' It has no row in the audit sheet, and we never got back to it on the second call. So this is the shortest thing we built and the one I most want your reaction to."
2. 0:15 — Drag the `.txt` into the same Slack channel used for every card so far. "Fifth thing out of one door. Same channel, same engine, no new tool. And to be straight with you: this is a paste, not automated ingestion. Fathom's export is switched off on your share links — Gisselle didn't skip that step, it wasn't available to her."
3. 0:35 — The card posts. Point at the header `source:` line and read it aloud, including the STAND-IN label if that is what it says. Then point one line lower: "4 usable / 11 candidates · 4 verified verbatim · 0 dropped. Every quote on this card was checked character-for-character against a line in your transcript. Anything the checker couldn't find got thrown away instead of printed. That matters more here than anywhere else, because a made-up client testimonial is not a typo."
4. 0:55 — Read script two's hook out loud, then click its citation. If Fathom-sourced, the browser jumps to the moment. If Zoom-sourced, point at `@8:55 · no shareable link (Zoom .txt)`: "Your client calls are on your Zoom, so there's no player URL to link into. You get the timestamp, not a link. We'd rather show you that than fake it."
5. 1:20 — Point at `claims_needing_proof` and at `client_named: false — anonymised as 'a Texas wedding venue'`. "Nothing leaves here with a client's name or a number you haven't confirmed. Naming them is one click, and that click also drafts the permission email to them."
6. 1:40 — Deliberate negative control. Drop in the Meta office-hours transcript. The card comes back: no result-praise found, here is what I did find, send me a different call. "It doesn't invent three scripts to look busy. On the wrong call it tells you it's the wrong call."
7. 2:00 — THE BEAT. Slide the laptop over. "Record thirty seconds in this thread. Tell it what you'd actually want — something like 'lead with her booking growth, not the ad spend, and make the hook about her being fully booked for 2027.'" She records. React ✏️.
8. 2:25 — Re-run in front of her. Three new hooks, same four verified quotes, her angle. Say nothing for a second, then: "That's the voice note you described on August 26. Same call, your direction, ten seconds."
9. 2:40 — React ✅ on the script she likes. Carousel copy appears in the thread, built from the edited script, not the original draft. React ✅ again. The marketing email appears as a draft in ai@. "Three stages, three approvals. Nothing posted, nothing sent, and the email is sitting in a draft in the AI mailbox — not in hello@, because we never asked you for that access."
10. 2:55 — Land it on the connection. Open Ridgefield's client record. "Those four quotes are now in here, tagged with who said them and whether you have permission to use them publicly. When Tina builds next month's report, that's where the client's own words come from — and when you want a case study in six months, this file is already written."

### Risks

- No client-praise sample exists in anything we hold, so the classifier's positive lane is untested on real data — both office-hours transcripts are account troubleshooting (file 05 §2) and neither E2M sync call contains a client praising results. Mitigation: send the qualified ask today; ship the hand-labelled negative set so the abstain path is demonstrably real; if nothing arrives by Tuesday, run the stand-in and say the sentence out loud.
- A generic ask produces the wrong call. Gisselle offered "the txt file downloaded from zoom" but a routine monthly 1:1 about raising a retargeting budget yields three flat reel scripts on the one item Whitney tied to revenue. Mitigation: the reply names both the format and the content — the .txt, not the summary, from a call where the client said something good about their results — and offers the fallback "send two and we'll pick." Whitney is the only person who remembers which calls those are; do not ask Gisselle to guess.
- The Zoom .txt format is unverified and cannot be verified in advance, because canDownload: false on both Fathom links means we cannot manufacture a comparison export (file 05 §2). "One normalizer serves both" is a design intention presented as such. Mitigation: three parsers behind a format sniffer, plus a raw-lines fallback that preserves speaker order and drops timestamps rather than failing the run, plus the abstain lane catching any parse that yields fewer than two speakers.
- The reel register is uncalibrated. The only voice corpus we hold is the client-facing email-template folder, which teaches an ops recap register, not a founder's Instagram register — the exact mirror of MVP4's missing walkthrough video, and for the same reason: nobody asked. Whitney's own bar, Aug 26 @40:03: "it sounds like it's in my voice." Mitigation: ask for three reels or captions she considers on-brand; until then the three scripts are deliberately written in three different registers (founder-POV, client-quote-led, teaching) so the gap becomes a choice she makes rather than a miss she notices.
- Slack audio-clip transcription may not be available in this workspace — the invite has not been accepted and the plan is unconfirmed (file 05 §1) — which would break the single highest-drama beat live, in the room. Mitigation: rehearse both paths; typed direction in the thread costs nothing on stage and produces the identical re-run; pre-generate the entire pass so the live re-run is the only live dependency in the demo.
- Hallucinated quotes are the specific reputational risk of this card. A fabricated testimonial that reaches public marketing is materially worse than a bad internal recap. Mitigation: exact-substring verification is a hard gate in code, not an instruction to the model; failures are dropped and logged as hallucinated_citation in the run ledger; Stage 2 citations may only reference the surviving set; the counts are printed on the card.
- Adoption risk on her own stated terms. Aug 26 @39:55: "it's not things where I'm, like, doing double work and then, like, going in and having to, like... Heavily edit or like completely rewrite stuff." If draft one is far off and her edit does not propagate, she abandons the tool after one try. Mitigation: the staged gate means the carousel and email derive from the approved, edited script; the ✏️ path re-runs the model rather than asking her to rewrite prose.
- Client-permission exposure if the naming toggle is used casually. Whitney's constraint, Aug 26 @39:09, is that nothing negatively affects the client experience. Mitigation: client_named defaults to false, the descriptor is anonymised, the toggle drafts the permission ask in the same action, and permission_state travels with every quote in the bank so a later card cannot publish an ungranted quote.
- Zero audit-sheet coverage means there is no hours number for this card and none will be manufactured. The sheet quantifies ~18.1 hrs/month across twelve rows of one contractor's operational work and this workstream has no row at all. Mitigation: say it first, before she can ask — the sheet was scoped to Gisselle's seat, this is the revenue side she raised herself, and naming the gap is part of the point. Do not let this card be defended on time saved.
- E2M has already promised more than this delivers. Aug 26 @22:38, Minu: "an agent who looks at all your transcripts automatically and pushes ideas for your reels." Thursday's intake is a human paste. Mitigation: withdraw the automation claim explicitly on stage and place the auto-flagging in the production path where it belongs — it is a one-field configuration change once MVP1 is filing calls, not a Thursday capability.

### Production path

Apollo week 1, configuration rather than build: Stage 1 already runs on every client call MVP1 files, and it already emits `no_usable_praise`. Persist the inverse as `has_client_praise` on the record, and the weekly digest can surface "three calls this week contained client praise" with the quotes attached. Whitney stops being the human index of which calls are usable — which is hop one of the five-hop chain and the only hop Thursday deliberately leaves alone. Cost: one field and one line in the existing digest.

Apollo week 1–2, closing the calibration gap: collect three to five reels or captions Whitney considers on-brand and add a `voice_profile` block to `agency_playbook.md`. Nothing is trained; the prompt is grounded. This is the same fix as MVP4's walkthrough-script problem and both should be asked for in the same email.

Apollo week 2–4, the quote bank as an asset: once the bank holds thirty or forty permission-tagged quotes across clients, a monthly "case-study candidates" digest becomes a read over existing data rather than a new build — grouped by claim, with the verified quote, the timestamp, the evidence link where one exists, and the permission state. That is Whitney's own second use of this material, Aug 26 @19:21: "that's where I get our best content for our own marketing and for our case studies, for example."

When Gmail scope on `hello@weddingindustryads.com` is granted — currently unrequested and named as an ask — the marketing email moves from a draft in `ai@` to a draft in the mailbox she actually works from, which also unblocks the larger TASK-04 drafting work. Until then, `ai@` only.

Format hardening: the first real Zoom `.txt` retires Parser B or C, whichever is wrong, and turns "one normalizer serves both" from a design intention into a verified fact. If Whitney acts on her own pre-consent — Sept 2 @4:08, "if we need to switch to a team account or anything like that, I mean, we, we totally can" — Fathom-sourced calls gain clickable citations and the degradation footnote disappears for those sources. Note the friction honestly: Jacqueline hosts on her own domain outside the company workspace (file 05 §2 finding 4), so consolidation is not entirely Whitney's to grant.

Explicitly not on the path unless she asks for it: scheduling, publishing, graphic generation, or performance analytics. If she asks, publishing goes behind the same review gate as everything else, and no code path exists to bypass it.

### Success criteria

- Whitney records thirty seconds of direction live in the Slack thread, and the re-run returns three hooks she recognises as her own angle, with nobody editing text by hand in between. This is the single criterion that matters most, because it is the thing she described on Aug 26 and the thing a founder who has never used Claude can evaluate without any explanation.
- Zero unverified quotes reach the card. Every printed quote passes exact-substring verification against the source transcript, and the run ledger's dropped count is visible on screen. If the count is non-zero, the guard worked; if a quote appears that is not in the transcript, the card failed regardless of how good the scripts read.
- The abstain path is demonstrated deliberately, not discovered accidentally: the Meta office-hours transcript is fed in on stage and the card reports no result-praise found and stops, rather than producing three scripts.
- Carousel copy does not exist until the reel script is approved, and the marketing email does not exist until the carousel is approved — and Whitney's edit to the script is visibly carried into both. Verified by editing a hook and watching the change appear in the carousel copy.
- Nothing posts and nothing sends. At the end of the run the marketing email is a draft in ai@weddingindustryads.com and no social platform has been touched. Whitney should be able to confirm this herself by looking at the card, without taking our word for it.
- The quote bank appears in Ridgefield's client record with timestamps, source system, evidence links where they exist, and permission_state, and is shown being read by MVP4's card in the same session. This is the interconnection claim being demonstrated rather than diagrammed.
- Behavioural signal, and the truest one: Whitney names a specific call she wants to send us for next time, unprompted, before the review ends. That is the difference between a demo she enjoyed and a tool she intends to use.

---

# PART 6 - What changed from the previous plan, and what is not in the five


## 6.1 Changes from the previous portfolio

- MVP3 'Nobody starts from a blank page' is CUT as a standalone card — the single hardest call in this decision. Its differentiating claim died permanently, not temporarily: the ChatGPT Project cannot be shared because they are on one shared hello@ login with no Team account, so Project sharing strips files. That removes both the house brief format and the only reference for what the team currently accepts as a usable draft. Its input corpus is the only one in the portfolio that does not exist yet. It was also the third demonstration of a capability already shown twice.
- MVP3's INPUT half is preserved inside card 1 at ~0.15d, not discarded: the messaging-and-positioning call becomes a demonstrated call type, and the per-client brief that Gisselle hand-assembles into a ChatGPT Project today builds itself — which retires the band-aid Whitney said she does not see as a long-term solution, and covers TASK-09's third leg.
- MVP3's OUTPUT half (Ivy's creative brief, Tina's landing-page copy block) is the named restore-first item with a named trigger, not a silent descope: restored at 0.3d by dropping card 1's fourth call type if the Ridgefield inventory returns shipped artifacts. The fifteen RSA headlines leg is cut outright — Carmen already does keyword research well and 'comes to the call already prepared with keyword research'.
- NEW CARD at rank 2: 'What we changed, what we promised, who showed up' — the office-hours engine, as a named, priced, pickable card rather than a hidden route. It lands both remaining HIGH-priority sheet rows, is the only card whose input is already fully in hand, and is the only artifact anywhere in the portfolio that answers the turnover-proofing thesis the engagement was actually sold on.
- Roll call re-enters the portfolio — but as one of three outputs of card 2, not as its own card and not as the demo's headline. TASK-13 gets answered; its name-level failure surface never gets the dramatic beat.
- Every 'automated ingestion' claim from the access request is WITHDRAWN on stage. Intake is a deliberate human paste, and the follow-up says explicitly that export was unavailable to Gisselle (canDownload: false on both share links) rather than leaving an unmet request hanging over her.
- Card 1's demo is re-staged around what Fathom demonstrably cannot do. Fathom already emits action items with clickable deep links, free, today, so extraction is the setup and owner assignment, due dates, four-system delivery, the drafted recap in their own voice and cross-call did-it-happen memory are the payoff — with Fathom's own three items on screen as the control group.
- A non-optional internal-vs-client-facing Drive tier flag is added to card 1, with the client tier behind the same review card as outbound email. This is a leak-risk requirement, not a nicety, and it goes on the visible demo card because it is a correctness feature Whitney will recognise instantly.
- Fathom's ?timestamp= deep-link format is adopted as the portfolio-wide evidence-citation convention, with an honest degradation to bare @MM:SS for Zoom-sourced quotes.
- MVP4's 90-second walkthrough-script leg is CUT (the video never arrived, so register and length were guesses) and the Canva /edit link is treated as read-only by policy, since it is a write-capable link into a live client asset.
- MVP2's run-to-run diff is deferred to Apollo week 1; its LeadLock go-live/A2P readiness block is deliberately kept, because it is the only place Danielle appears in the portfolio.
- MVP5's ask becomes qualified rather than generic — the .txt not the summary, from a call where the client praised results — and its voice note routes through the same paste channel instead of a separate intake.
- The domain heuristic is demoted from a signal to an unreliable one: `(weddingindustryads.com)` silently misclassifies Jacqueline, who hosts on her own domain outside the company Fathom workspace.

## 6.2 How the competing arguments were resolved

Three positions were argued independently before the decision: that roll-call must now be one of the five, that the office-hours engine should be a card, and that the existing five should be left alone. Each was resolved explicitly rather than split.


**Position 1: roll-call belongs in the final five as a 0.5d stateful card, displacing MVP3, because it is the only non-generative, client-verifiable capability and the only thing she tried and failed to automate herself, twice.**

*Verdict: REJECTED as a card. ACCEPTED as an output of card 2, and demoted from the demo's headline.*

The premises are the strongest in the packet and I am acting on them: TASK-13 is a HIGH row, it is the loop E2M opened as the first substantive question of the whole engagement, and Gisselle's two failed attempts plus her own comment 'It's in my task list to automate this somehow but it's complex' make leaving it unaddressed a visible omission. So it is in the portfolio. But three of Position 1's own concessions are fatal to card status. First, the metric fails at both ends in the direction that destroys its purpose: the member who joins, listens and leaves silently is precisely the disengaged member TASK-13 exists to catch, and is scored absent; Jillian left at 9:19 of a 48-minute call and scores as a full attendee. No abstain lane fixes a silent joiner, because there is no signal to abstain on. Second, the evidence is n=1 and seven months old, and the founder's own description of her own product contradicts the rolling-1:1 inference twice ('it's really like an open meeting for clients to come in'; 'they can join like at any moment during that hour'). Third, Position 1's honest degradation path — raw labels written into her existing sheet — is a transcription macro, and presenting a transcription macro as one of five flagship workflows to a buyer weighing $9,499 is a downgrade in perceived capability at the worst possible moment. Its correct home is inside card 2, where the roster join and abstain lane are amortised across three outputs, where a thin match degrades to a 'needs a human' row rather than a wrong client name on screen in front of the founder, and where TASK-13 and TASK-10 are covered by one line item, exactly as file 04 said they should be.

**Position 1: the flag-volume problem is a one-parameter spec choice, not two products — fire once on threshold crossing with a cooldown and rank by consecutive misses, correct at both volume regimes.**

*Verdict: ACCEPTED as the build spec. REJECTED as a reason to promote roll-call to card status.*

The spec is right, it costs nothing extra, and it is adopted verbatim: fire once on crossing, cooldown, rank by consecutive misses descending, key per member account. At low volume it reproduces her sheet; at high non-attendance it becomes a ranked re-engagement list. But Position 3's counter lands: a ladder that is arithmetically perfect and fires on ten of twelve members is operationally useless, and it fails in week one of real use in front of her, which is worse than failing privately. So the volume question goes in today's email — one line, zero marginal cost, in an email we are already sending — and attendance ships as capture plus threshold flags with the contingency stated out loud, never as a flag lifecycle and never as an auto-DM. Position 1's reframe that 'if most members are past the flag, that is an unquantified silent-engagement problem in a recurring-revenue program' is correct and worth saying, but it is a sentence at the review, not a justification for a demo slot.

**Position 1: key attendance per member ACCOUNT rather than per person, fuzzy-match to the GHL roster with a mandatory abstain step, and verify the Communities roster endpoint the hour the invite is accepted.**

*Verdict: ACCEPTED unconditionally.*

This is the actual engineering risk and this is the actual fix. Per-account keying resolves 'Michael & Diana' structurally and matches the row shape of Gisselle's own sheet, so there is nothing to reconcile later. 'Jillian' with no surname goes to abstain-and-confirm rather than a guess — 2 of 3 rows ambiguous in the only sample we hold is not a caveat, it is the design constraint. The roster endpoint is verified within the hour of invite acceptance because file 03 flagged GHL API availability as only ever 'most likely', and if it is absent the output degrades to raw label capture into the sheet she already keeps rather than to nothing.

**Positions 1 and 2 both cut MVP3 'Nobody starts from a blank page' to fund their addition. Position 3 defends it as Whitney's own unprompted #1 nomination.**

*Verdict: ACCEPTED that MVP3 is the cut — but its input half is preserved inside card 1 and its output half gets a named restore trigger. Position 3's objection to cutting it is upheld as a cost to be paid out loud, not a reason to keep it.*

MVP3 is the only card in the five whose input corpus does not exist: every other input is in hand or one reply away, and MVP3's rests entirely on a Drive inventory nobody has run, three days out. Its differentiator is permanently gone for a correct platform reason, not a fixable one. And with 'matches how your team already prompts' withdrawn, what remains competes against an incumbent the client already runs, on a bar the incumbent already clears — Whitney's own words for what the ChatGPT Project does for her today are 'more of a push for them than just starting from a blank page'. Roll-call and the change log, by contrast, compete against nothing. But Position 3 is right that cutting it silently would leave three of the four clauses of Whitney's own unprompted #1 nomination uncovered and remove the only card serving Ivy, which would also be a net loss on the very turnover axis the addition is meant to serve. So the cut is structured, not clean: the input layer — the per-client brief Gisselle hand-assembles into a ChatGPT Project — is absorbed into card 1 as a demonstrated call type for ~0.15d, which is a better artifact than the lost exemplars anyway; the output layer is the first thing restored, at 0.3d, on the named trigger of a rich Ridgefield inventory; and the review says explicitly that first-draft copy is sequenced next, so the omission reads as a choice rather than a gap.

**Position 2: build the office-hours workstream as a CARD, not as a route inside MVP1, because a route has no name, no owner, no line item and no price, so it cannot be picked, cannot be funded, and dies if its host card is not chosen.**

*Verdict: ACCEPTED. This is the decisive argument in the packet.*

Position 2 concedes the engineering objection honestly — mechanically it is largely the same extractor pointed at a different input — and then wins anyway on the ground that actually decides Thursday: the blueprint is a decision instrument, not an architecture document. Whitney's stated homework is to 'make a decision on which are a couple of the workflows we should start working on in terms of execution'. An unnamed sub-feature of another card is unpickable. And coupling the only turnover-proofing artifact in the portfolio to the survival of a different card is a bad bet on the one thesis they actually bought. The shared engine is an argument that it is CHEAP, not that it should be INVISIBLE — which is why 0.7d buys a card here and why the spine gets shown once, as a picture, with the same extractor visibly serving both cards. Position 3's warning that a sharp client will notice card 2 shares most of its code with card 1 is handled by saying so first: the reuse is the reason it costs 0.7d instead of 2.0d, and it is the answer to 'how is it all connected', not something to hide.

**Position 2: name it 'Nothing lives in Carmen's head'.**

*Verdict: REJECTED on the name and the framing. The capability is kept.*

Position 2 identifies the surveillance risk itself and then under-weights its own finding. On a team Whitney describes as one person per function with no redundancy, the card that converts a specialist's unlogged decisions into a company-owned record is the card most likely to read to that specialist as monitoring — and the binding constraint on this engagement is that adoption risk exceeds build risk. Losing Carmen is the exact catastrophe the engagement exists to prevent; building the thing that might cause it, having never spoken to her, is reckless. So: the record is keyed to the CLIENT ACCOUNT, not the person; the card is named for what it produces in plain language ('What we changed, what we promised, who showed up'); it is framed as what a client's account record should contain when the next account manager inherits it; Whitney decides who sees it; and today's follow-up asks for twenty minutes each with Carmen and Tina before any of it ships.

**Position 2's own concession: Google Ads ships a free native change history recording every change with user, timestamp and before/after values — so 'it exists only in Carmen's head' is overclaimed, and a client who checks will find out.**

*Verdict: ACCEPTED, and the claim is narrowed on stage before she can find it herself.*

This is the most important self-correction in the packet and it must survive into the room. What is genuinely missing is not the change — it is three things no platform log contains: the reason for the change as stated on the call, the attachment of that reason to a client record and to the monthly report narrative Tina currently writes from memory, and the promises made out loud ('I'll send you the link in DMs', 'you can come back to me next time with that shorter lead form'). That is a thinner claim than 'Carmen's head is the only copy' and it is still the right claim, because it is precisely the layer that the 18-24 hr/month reporting process reconstructs by recollection. Saying it ourselves, unprompted, buys more credibility than the sentence we give up.

**Position 3: keep the five exactly as selected — four improved, only one weakened with a 90-minute remedy — and spend the contested 0.5-0.75d on the four connector verifications, the re-staged demo, the tier gate and rehearsal instead of re-litigating a settled selection.**

*Verdict: REJECTED on the portfolio. ACCEPTED, in full, on the capacity discipline and the verification sequencing.*

The operational half of this position is simply correct and is adopted without modification: every connector leg in every card is mock until four things are verified (ClickUp Member not Guest, GHL Agency Admin, Slack channel-create scope, the Communities roster endpoint), the Ridgefield inventory decides a card and takes 1-2 hours, deliberation time is build time with one engineer and three days, and the half-day rehearsal reserve is untouchable. All of that happens before a line of build code, in the first two hours of today. But the portfolio half fails the requirement Position 3 names as its own strongest counterargument: five cards that all live inside Gisselle's seat, Whitney's inbox or WIA's own funnel argue the turnover-proofing thesis instead of showing it, leave both remaining HIGH-priority sheet rows uncovered, and reproduce the exact shape file 04 predicted would fail — twelve rows from one outside contractor's seat, restated as five prettier cards. Its procedural argument, that a four-lens panel and three judges already decided, is sunk-cost reasoning applied to a decision whose inputs materially changed; re-deciding on new evidence is what careful process is for. And the capacity argument cuts against it on inspection, because the card it protects with that capacity is the one that just lost its differentiator permanently and whose inputs are unknown.

**Position 3: the entire evidence base for anything office-hours is n=1 and seven months stale, with an unaccounted 33:00-35:00 gap so even the segmentation is inferred, and the Meta 'sample' is a two-person support call whose title was never set — you cannot verify an extractor against a corpus of one.**

*Verdict: ACCEPTED as a hard constraint on what we CLAIM. REJECTED as a reason not to build.*

This is decisive against attendance as a headline and it is why attendance is the third output of card 2 rather than a card, why the seven-month staleness is stated out loud, and why today's email asks for a recent office-hours transcript through the same paste route. But the change-log extraction does not depend on the session being representative of anything. The transcript contains real, specific, currently-unlogged decisions and promises — two conversion changes across two named accounts, nine named negatives, three commitments — and the output is checkable line by line against the transcript on screen in front of her. A seven-month-old session is a bad attendance sample and a perfectly good extraction sample, and the distinction is worth making explicitly rather than letting the staleness contaminate both.

**Position 3: adding a card, or growing one card a second head, reproduces the exact catalogue paralysis the client has twice told us stops her — and the honest description of any fold-in is a forced third cut of Whitney's own unprompted #1 nomination.**

*Verdict: PARTIALLY ACCEPTED. The count objection stands and is answered by structure, not by omission. The third cut is real and is named rather than hidden.*

The paralysis risk is the reason there are five cards and not six, the reason two of the five are explicitly framed as downstream consumers of the other two, and the reason the review opens with one picture rather than five: one intake, one record per client, everything writes to it and reads from it. Card 4's cause sentences come from card 2; card 5's raw material comes from card 1; card 3 needs neither and needs nothing from anyone. That is four cards in a chain and one insurance policy, which is a system with a shape, not a catalogue with five entries. Position 3 is right that MVP3 is what the addition costs, and I am not softening it: cutting the opportunity the founder named first, unprompted, to fund one she has never mentioned is the classic vendor-led substitution, and the only defence against it is to say so in the room, preserve the half of it we can afford, and put its restoration first in line with a named trigger.

**Positions 1 and 2 both claim their addition puts Carmen and Jacqueline on screen and therefore answers the turnover-proofing exposure — but neither has ever been interviewed, and two of card 2's three outputs have zero client validation.**

*Verdict: ACCEPTED as the honest limit of what card 2 can claim, and it changes how the card is presented rather than whether it is built.*

Only one of card 2's three outputs is client-attested. TASK-10's pain was articulated at length but its process was never walked, and the change log was raised by nobody in 92 minutes of discovery. So card 2 is presented as a proposal grounded in a real artifact, not as a reflection of something she told us — and the difference is stated in the first sentence of the card, because a client with low AI literacy being shown an engine she did not ask for is a trust risk unless we name it first. The mitigation is concrete rather than rhetorical: twenty minutes each with Carmen and Tina in today's follow-up, before Apollo week 1 spends any real money on either, and Whitney holding the decision on who sees the record.

---

# PART 7 - Capacity, build order and the cut line


BUDGET. Real build capacity is ~4.0 days after the half-day rehearsal-and-pre-generation reserve, which is untouchable — a pre-generated artifact set is the only defence against a live failure on stage. The five cards sum to exactly 4.00 days WITH the ~1.25d shared spine carried inside card 1 (card 1 = 1.25 spine + 1.05 card). Arithmetic: 2.30 + 0.70 + 0.50 + 0.25 + 0.25 = 4.00. The previous plan was 4.75 with two pre-committed cuts; this one fits with one structured cut (MVP3) and four trims, and carries no undeclared overhang.

NOTE ON THE BRIEF'S ARITHMETIC. The instruction reads '~4.0 real build days on top of the ~1.25-day shared spine', which would be 5.25 total, but stated capacity is 4.0 real days. I have planned to the tighter number — 4.00 all-in, spine included — because that is the one that cannot fail. If 5.25 is what is actually available, the restore line below spends the extra 1.25 in priority order.

BUILD ORDER (Mon Sept 7 → Wed Sept 9; review Thu Sept 10).
Hours 0-2, before any build code: accept all four invites and verify the four things every card depends on — ClickUp seat is Member not Guest (Guests cannot open templates, which alone kills offer-dependent template selection), GHL is Agency Admin, the Slack grant carries channel-create scope, and the GHL Communities roster endpoint actually exists. Send the follow-up email. Run the Ridgefield inventory (1-2 hrs), which decides the restore line.
Then: Page Check first (0.5d) — deliberately out of rank order, because it needs no spine and no client, so a working live demo is banked by the end of day one no matter what happens afterwards. Then the spine (1.25d). Then card 1 (1.05d). Then card 2 (0.70d). Then cards 4 and 5 (0.25d each). Then the 0.5d rehearsal.

CUT LINE, in the order things go if a day evaporates:
1. Card 5's carousel and marketing-email legs — keep the three reel scripts (-0.10).
2. Card 4's sourced-cause tracing — the one-page summary survives on metrics alone, and we say the cause layer is sequenced (-0.10).
3. Card 2's attendance output — the change log and commitment tracker survive; TASK-13 degrades to raw label capture into Gisselle's existing sheet (-0.15).
4. Card 1's fourth call type, the internal Monday meeting — the safest one to lose because it has no client-facing output (-0.15).
5. Card 5 in full, and it is said out loud that the revenue-linked item slipped and why (-0.25).
BELOW THE CUT LINE, never: the spine, Page Check, and the internal-vs-client-facing Drive tier gate. The tier gate is a leak risk, not a feature — writing internal material into the wia+ridgefield client-visible subfolder breaks the hardest constraint in the engagement.

RESTORE LINE, if the 5.25-day reading is the real one, in order: (1) MVP3's Ivy creative brief and Tina landing-page copy block, 0.30 — triggered by a rich Ridgefield inventory, and the first thing back regardless; (2) card 1's offer-dependent template branching, 0.20 — triggered by ClickUp landing as Member; (3) MVP4's 90-second walkthrough script, 0.20 — triggered only by the video arriving, never guessed; (4) MVP2's run-to-run diff, 0.25; (5) a second, recent office-hours transcript run to prove the change-log extractor generalises past n=1, 0.15. Total 1.10, leaving 0.15 of genuine slack.

WHAT IS EXPLICITLY NOT IN THE FIVE, and why, so the client sees the whole sheet: TASK-11 (1-hour reminder posts, 3.0 hrs/mo) and TASK-15 (overdue invoices and invalid emails, ~1.1 hrs/mo) are both single-system GHL jobs behind a token we have not verified yet. They are the cheapest real wins in the sheet and they are Apollo week-one work, not stage work — showing a GHL filter query does not help her decide anything. TASK-04's triage half (the sheet's #1 HIGH row) is blocked on Gmail scope on hello@, which was never requested; it is the single largest unlock available and it is the first item in today's email, named as a gap rather than quietly absent.

---

# PART 8 - Demo running order


1) PAGE CHECK, as a 90-second cold open before we ask her to trust one word of generated text. It runs live, with no login, against her own site, and returns the mobile CTA-to-404 she independently confirmed two weeks ago plus the investment-guide link. Nothing to take on faith, and the credibility it buys is spent on everything after it. 2) THE HANDOFF, the trunk: paste the real transcript with Fathom's own three deep-linked action items on screen beside it as the free control group, and beat it on owner, due date, delivery into four systems, the recap in their own template voice, and one item honestly abstaining to 'needs a human'. Then the second paste — the messaging-and-positioning call — and Ridgefield's client brief writes itself, retiring the ChatGPT-Project band-aid. 3) WHAT WE CHANGED, WHAT WE PROMISED, WHO SHOWED UP, the thesis: the same channel, Carmen's office hours in, and out comes the account record — the conversion change with its timestamp, the promise to DM Jillian the VIP-day link with a state that survives to next Thursday, the attendance line into her existing sheet with one row abstaining. Then the six things Fathom missed. 4) THE EXECUTIVE SUMMARY, which is where the portfolio stops being a list: click the cause sentence in the monthly page and land on Carmen saying the thing that caused it. That is the payoff for 'how is it all connected', shown rather than asserted. 5) ONE VOICE NOTE, the live closer on the only revenue-linked item: hand her three reel scripts from her own client's words, then ask her to record thirty seconds of direction on the spot and re-run it in front of her. CLOSE on one picture — one intake, one record per client, everything writes to it and reads from it — and then the three-line honesty slide: what is real today, what is mock and labelled, and the four things we need from her by Friday. Rehearsal rule: everything is pre-generated and on disk before the call. The only thing that runs live is Page Check, which cannot fail, and the voice-note re-run, which is worth the risk.

---

# PART 9 - Follow-up asks


- THE ZOOM .txt, qualified — not the summary, which strips the verbatim quotes the reel scripts are built on. Two of them if possible: one client strategy call where the client said something good about their results (Whitney is the only person who remembers which those are, so she has to pick it), and one recent onboarding or messaging-and-positioning call. Lead the email by saying plainly that we now know export was unavailable to her — canDownload was false on both share links — that her copy-paste worked perfectly, and that the paste is now the design rather than a workaround.
- THE COMPLETED ONBOARDING QUESTIONNAIRE — but we look in Ridgefield's Drive folder first, because Gisselle described the filing mechanism herself: downloaded from Dubsado, saved to the client's Google Drive folder, shared in the Slack channel. Only ask if it is not there. It is the payload of three separate outputs and the highest-priority Drive lookup of the day.
- BOTH DUBSADO ALERT TYPES confirmed present in the forwarded set — contract signed AND invoice paid, because Whitney's trigger is a conjunction — plus one raw, non-forwarded alert so the parser sees real envelope headers rather than the forwarder's.
- THE REPORT PDF EXACTLY AS SENT TO A CLIENT, plus the walkthrough video. Both exist, neither was sent. The /edit link shows template scaffolding rather than the delivered artifact, and we are treating it as read-only because it is a write-capable link into a live client asset. If the video arrives before Thursday the 90-second script leg comes back for free.
- THE VOLUME QUESTION, one line: at steady state, how many members are currently past the four-week flag, and how many members are in each accelerator? It configures the build rather than gating it — but if the answer is 'most of them', the right product is ranking who to re-engage rather than flagging everyone, and that is a different spec.
- ONE RECENT OFFICE-HOURS TRANSCRIPT via the same paste route — this month's, either slot. The only Google sample we hold is from Feb 12, seven months and one resignation ago, and it is the sole validation corpus for the change-log extractor.
- INVITE ACCEPTANCE AND PERMISSION CONFIRMATION, today: ClickUp as Member not Guest (Guests cannot open templates, which would kill offer-dependent onboarding selection outright), GHL as Agency Admin, the Slack channel grant including channel-create scope, and the three Members Portal channels. Every connector leg in every card is mock until these four are verified.
- GMAIL DELEGATION OR API SCOPE ON hello@weddingindustryads.com — never requested, and it is the single biggest unlock left. It blocks TASK-04's filing, starring, waiting-tag and triage legs, which is the highest-priority row on her own sheet and the company's entire client-comms hub. Named as a gap in the blueprint rather than quietly missing.
- TWENTY MINUTES EACH WITH CARMEN AND TINA before execution starts. Card 2 proposes work on Carmen's calls and card 4 replaces the narrative layer of Tina's report, and neither has ever been interviewed. Framed as a design conversation about what the client account record should contain, not a review of their work — and the point of asking now is that adoption risk on this team exceeds build risk.
- GOOGLE ADS AND META MARKETING API ACCESS to two client ad accounts, read-only. Never requested, so the executive summary's metrics stay mock. This is the difference between a labelled template and a running report.
- A THIRTY-SECOND VOICE NOTE of marketing direction, or — better — nothing at all, and she records it live at the review. The live version is worth more than the prepared one.

---

# PART 10 - Honest risks


- The portfolio is one structured cut away from being the catalogue file 04 predicted would fail, and the cut is the founder's own unprompted #1 nomination. MVP3's first-draft copy legs are gone from Thursday. The defence is that its input half survives inside card 1, its output half is first in the restore queue with a named trigger, and we say all of that out loud — but if she asks why the thing she named first is not on the page, the answer is that its input corpus does not exist yet, and that is a real answer with a real cost.
- Two of card 2's three outputs have zero client validation. The change log was raised by nobody across 92 minutes of discovery, and TASK-10's process was never walked. We are showing a founder with low AI literacy an engine she did not ask for, on a workstream we invented from a transcript. That is presented as a proposal in the card's first sentence, not smuggled in as a reflection of her own words.
- Google Ads and Meta both already log the raw account change for free. Our claim narrows to the reason, the client-record attachment and the spoken promises — which is genuinely missing and genuinely feeds the 18-24 hr/month report — but it is a thinner claim than 'it lives only in Carmen's head', and if we do not narrow it ourselves before she checks, the whole card's credibility goes with it.
- Card 2 is the surveillance risk in the portfolio. On a team with one person per function, a record of a specialist's unlogged decisions can read to that specialist as monitoring, and losing Carmen is the exact catastrophe the engagement exists to prevent. Client-account framing, Whitney holding the visibility decision, and twenty minutes with Carmen before anything ships are mitigations, not guarantees.
- The change-log extractor would be validated on a single seven-month-old session, and the Meta 'sample' is a two-person troubleshooting call whose title was never set. One recent transcript through the paste route fixes it; without one, n=1 is what we are standing on and we say so.
- Attendance cannot do the one thing TASK-13 asks for. A member who joins, listens and leaves silently is precisely the disengaged member the flag exists to catch, and is scored absent; Jillian left at 9:19 of a 48-minute call and scores as a full attendee. The soundness of speaker-derived attendance is contingent on current volume, not guaranteed by the format — the founder's own description of her session ('an open meeting for clients to come in'; 'they can join like at any moment') contradicts the rolling-1:1 inference, which rests on one Thursday when three people showed up.
- Every connector leg in every card is mock until four permissions are verified, with three days left. ClickUp landing as Guest rather than Member kills offer-dependent template selection outright. A missing Slack channel-create scope kills the signature branch's per-client channel. A missing GHL Communities roster endpoint degrades attendance to raw label capture. None of these is knowable until invites are accepted.
- 'One normalizer serves Fathom and Zoom' is a design intention, not an observed fact. No Zoom .txt has ever been seen, and Zoom holds the corpus Whitney generates for every single client call. Zoom's native transcript may need a second parser, and we would find that out on Tuesday at best.
- The signature trigger stays a manual file-drop. The Dubsado samples arrived forwarded, so the envelope belongs to the forwarder, and Gmail scope on hello@ was never requested — so the production signal cannot be demonstrated at all, only described.
- The executive summary's metrics are mock fixtures with no path to being real before Thursday, and its 90-second walkthrough script is absent rather than approximated because the video never arrived. Two of the card's three legs are therefore either labelled or missing.
- MVP5 may still be running on a stand-in call on Thursday. It is one reply from unblocked and it is the only item Whitney tied to revenue, but the reply has to come back with the right kind of call — a routine budget-tweak transcript yields a flat reel script on the highest-stakes card.
- Citations degrade honestly but visibly: clickable ?timestamp= deep links for Fathom-sourced facts, bare @MM:SS for Zoom-sourced ones, which is every client call. It is the right engineering and it looks like a downgrade on screen unless we explain it first.
- Ivy is the one named single point of failure the portfolio still does not touch anywhere, because her creative brief was MVP3's leg. Four of five specialists appear — Carmen and Jacqueline in card 2, Tina in cards 3 and 4, Danielle in card 3's LeadLock go-live and A2P readiness block — and Ivy does not. That is stated rather than papered over.
- The hours case remains arithmetically dead at $175 per recovered hour and we are not leading with it. If Whitney asks the Aug 11 question that has never been answered — how much time back in three months, what percentage can actually be automated — the honest answer is a range built on a sheet where six of twelve rows have no numbers, including two of the three HIGH rows. Going in without a prepared, honest answer to that question is the largest un-mitigated risk on the list.

---

# Appendix A - Data position summary

## In hand as of 7 September

| Artifact | Source | Notes |
|---|---|---|
| Full Google Ads office-hours transcript, 12 Feb 2026 | Gisselle, manual copy from Fathom | Real member names, two named client accounts, nine negative keywords, two conversion changes, three spoken commitments, inline `ACTION ITEM` lines with `?timestamp=` deep links |
| Meta office-hours transcript, 27 Aug 2026 | Same route | Titled "Impromptu Zoom Meeting"; two speakers only. Format sample, not an attendance sample |
| Both E2M weekly-sync transcripts | E2M's own recordings | The internal-meeting call type sample |
| Forwarded Dubsado alerts | Gisselle | Forwarded, so envelope headers belong to the forwarder |
| Ridgefield client folder + the whole company Shared Drive | Gisselle | **Shared Drive confirmed** - `ai@` can write. Two-tier structure: `wia+ridgefield` is the client-visible subfolder |
| "Full service email templates" Drive folder | Gisselle | The real voice corpus for recap and welcome drafting |
| Monthly client report | Canva `/edit` link + template link | Layout, metric set, section order, length. Treated as read-only by policy - it is write-capable into a live client asset |
| ClickUp / GHL / Members Portal / Slack | Invites sent | **Seat and permission levels unconfirmed.** Every connector leg is mock until verified |

## Requested and not received

| Missing | Blocks | Note |
|---|---|---|
| A client-meeting Zoom `.txt` | MVP 1's client-call trigger on real data, MVP 5 entirely | Offered by Gisselle, awaiting our reply. **The `.txt`, not the summary** |
| The completed onboarding questionnaire | MVP 1's welcome-email attachment, the Slack announcement payload, the client-brief seed | Probably in Ridgefield's Drive folder - Gisselle described that exact filing mechanism herself |
| The report walkthrough video | MVP 4's 90-second script leg (now cut rather than guessed) | Requested, never sent |
| The ChatGPT Project | MVP 3's differentiator - **permanently** | Correct platform behaviour: shared `hello@` login, no Team account, so Project sharing strips files |
| The report PDF as actually sent | MVP 4's design fidelity | The `/edit` view is scaffolding, not the delivered artifact |

## Never requested - and each one blocks something named

| Missing | Blocks | Ask precisely |
|---|---|---|
| Gmail API scope on `hello@` | A1's triage half - the sheet's #1 HIGH row and the company's entire comms hub | **Delegation does not grant API access.** Either `hello@` completes an OAuth consent, or a superadmin creates a service account with domain-wide delegation |
| Existing Gmail filters export | A1's filing leg | Settings > Filters > Export to XML. Building blind will fight the existing layer |
| Attributed sent-mail corpus | Voice fidelity on every draft | Templates give register, not Whitney's actual voice under pressure |
| Zoom on Whitney's account | MVP 1's production trigger, MVP 5, B1, B2 | She runs every client and sales call there |
| Google Ads developer token + MCC | MVP 4's live metrics | Approval takes days to weeks - **start now** |
| Meta System User token, `ads_read` | MVP 4's live metrics | Per client ad account via Business Manager |
| Slack workspace-admin app install | Five outputs and the review surface | A Member seat does not imply install rights. Highest fan-out unknown in the plan |
| Google Workspace OAuth allowlist for `ai@` | Drive, Gmail draft and Sheets legs simultaneously | Many Workspaces block unconfigured apps by default. **Test in hour one** |
| Danielle: 30 minutes + her LeadLock kickoff transcript | B5, the A2P readiness block | Least-documented knowledge in the company |
| Carmen and Tina: 20 minutes each | MVP 2 and MVP 4 land on their work | Neither has ever been interviewed |

---

# Appendix B - Fathom probe findings

Both share links return HTTP 200; bootstrap JSON extracted from the SPA shell.

| Property | Google Ads OH | Meta Ads OH |
|---|---|---|
| `call_id` | 566502955 | 801737343 |
| Title | "Google Ads Office Hours - 2.12.26" | **"Impromptu Zoom Meeting"** (never set) |
| Host | `carmen@weddingindustryads.com` | **`jacqueline@jacquelinehood.com`** |
| Company domain | `weddingindustryads.com`, `is_multi_user: true` | outside the company workspace |
| Started | 2026-02-12T17:00:06Z (Thu, 11:00 CST) | 2026-08-27T20:30:11Z (Thu, 15:30 CST) |
| Duration | 2881s / 48 min | 2964s / 49 min |
| `byline` | **"Unknown"** | **"Unknown"** |
| `access` | `external_view_only` | `external_view_only` |
| `canDownload` | **false** | **false** |
| Speakers | Carmen, Jillian, Erin Smith, "Michael & Diana" | Jacqueline Hood, Shannon Lee |

**Findings.**

1. **No structured attendee data anywhere.** The `call` object exposes 14 fields and none concerns who was present. The full payload was grepped for attendee / participant / invitee / guest / roster / member: zero hits.
2. **`canDownload: false` on both.** Gisselle did not ignore the export instruction - **export was unavailable to her.** Say so explicitly.
3. **The transcript is retrievable** at `/calls/{id}/copy_transcript?token={share_token}`, HTTP 200 unauthenticated, JSON with `html` and `plain_text`. Undocumented, behind Cloudflare - which is why manual paste is the better intake.
4. **Jacqueline is outside the company Fathom workspace.** Her label renders `Jacqueline Hood (Jacqueline Hood)` and classifies as *external* under a domain heuristic, so **the `(weddingindustryads.com)` suffix is an unreliable internal/external signal.** Any team-account consolidation needs her to change domains or join as a guest.
5. **Fathom's action items are embedded inline** with `?timestamp=` deep links, despite the header reading "No highlights". They are a free baseline any extractor must beat - and in the Feb 12 call Fathom missed both conversion-setting changes, four of the nine negative keywords, and both soft commitments.

---

# Appendix C - Team and timeline

| Person | Owns | Interviewed? |
|---|---|---|
| Whitney Hodges | All sales calls and all client calls; reviews everything | Yes |
| Gisselle Jimenez | Ops/EA via outside agency, ~25 hrs/wk; the only seat the sheet audits | Yes |
| Carmen Cruickshank | Google Ads; Google office hours; keyword research, builds, Looms | **No** |
| Jacqueline Hood | Meta Ads; Meta office hours; campaign launches | **No** |
| Ivy | Ads creative design | **No** |
| Tina | LeadLock/GHL design + **all monthly reporting** | **No** |
| Danielle | LeadLock implementation, workflows, DNS, A2P/10DLC | **No** |

*Unresolved: whether "Danielle" (implementation) and co-founder "Daniela Justus" are the same person.*

| Date | Event |
|---|---|
| 11 Aug 2026 | Discovery. Apollo $9,499 quoted; the cheaper Audit & Blueprint closed instead, creditable on upgrade |
| 26 Aug 2026 | Weekly Sync 1. Roll call and the Gmail workflow mapped; Whitney redirects to fulfilment at 16:43 |
| 2 Sept 2026 | Weekly Sync 2. Sheet closed in ~17 min; the fulfilment lifecycle narrated in ~21 min. ClickUp non-adoption disclosed |
| 3 Sept 2026 | Access request sent |
| 5-7 Sept 2026 | Samples received; Fathom links probed; intake decision taken |
| **10-11 Sept 2026** | **Blueprint Review.** Whitney picks a couple of workflows. Asha's private execution sync immediately after |
