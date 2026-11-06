# Content Atelier: findings and system improvements from rebuilding the Week 2 packs

**Internal. For the E2M development team, not for the client.**
**Date:** 21 October 2026
**Written by:** Claude, in an unattended run on the owner's machine
**Companion deliverable:** `WIA-Content-Packs-Week-of-8-14-June-2026.md`, the client-ready packs
**Revised:** 20 October 2026, after an independent reassessment of these packs. Section 0A says what changed. Amendments to the original text are marked **[Revised 20 Oct]**, and the new findings and recommendations are in section 14. The original text is kept so the reasoning trail stays visible.

---

## 0A. Revision note: what the reassessment changed (read this first)

The owner judged the packs this document accompanies as repeating the mistakes WIA had already rejected. An independent reassessment followed on the same day:
- It used the same week and the same evidence.
- It reread the client's feedback, every client and prospect call, and Whitney's own content-development threads in the ChatGPT export.
- It rebuilt the packs (`deliverables_2026-10-21/v2_reassessment/`).

It agreed with the owner, and it changes this document's headline in six ways.

1. **The gap is in judgment about the point of an idea, not only in what the system reads.** This run had complete inputs:
   - all 11 recordings;
   - the knowledge base;
   - the export;
   - strategist v6's "zoom out / WIA is the subject" framing.

   It still chose "Meta takes your instructions literally" (a platform lesson) and an office-hours troubleshooting walkthrough. So recommendations 1 to 7 are still necessary, but they are not sufficient.
2. **What's missing is a test on the point.** The rules (plan section 2.2, strategist v6) test whether WIA is the *subject* of an idea. Pack 1 passes that test ("we build Meta campaigns…"), but its *point* is how Meta's objectives work.

   Section 14 adds five tests:
   - is the point WIA's, not just the subject;
   - would it surprise an experienced advertiser;
   - what does the reader take away;
   - is it written for the right reader;
   - does it fit the offer calendar.
3. **Ranking by amount of evidence picks the wrong ideas.** G1's "count independent support" favours campaign mechanics, which are the most-discussed topic in account calls. Each of the six reference pieces Whitney published rests on one moment.
4. **The best material is in the human layer of a call.** It's a handful of sentences per call: a feeling, a self-description, a counter-expected decision. Topic-based extraction and summarising drown them.
5. **A critic that can't see Whitney's work can't see the problem.** A blind reviewer given her verbatim finals rated two ideas from this run "reject the idea":
   - Pack 1, "Meta takes your instructions literally";
   - Pack 2, office hours.

   It rated Pack 3 "publish after light edits".

6. **Tone, titles and format are part of the standard, and most of the rules were already written down.** After the owner's review of v2, a second pass (section 14.8) compared every format with Whitney's own finished pieces. It found five problems:
   - hook-style angle titles where her model uses plain ones;
   - a missing brief;
   - captions that skipped Savannah's problems, desires and symptoms;
   - a casual register applied beyond scripts;
   - carousels built on operational steps.

   Knowledge base 09 already held several of the rules. They need enforcing as checks at writing time (recommendations 28 to 33). Section 14.9 consolidates everything into a house style specification by format.

**Items amended inline, marked "[Revised 20 Oct]":**
- the summary's headline;
- G1;
- section 8;
- recommendations 1, 3, 5, 6 (its ID), 10 and 12;
- section 12.

**New findings and recommendations:** section 14.

**Detailed companions:**
- `v2_reassessment/Diagnosis-Why-The-WIA-Packs-Keep-Missing.md`, with the evidence and side-by-side comparisons;
- `v2_reassessment/Reproducibility-and-System-Findings.md`, with the system mapping.

---

## 0. Summary

**What was done.** The three content packs WIA rejected on 13 October were rebuilt from the same source week. The packs were built mostly by hand, using the project's knowledge base, database, rule patterns and research artifacts. Two read-only research agents helped: one on the internal calls, one on the ChatGPT export. Every claim in the copy was checked against the transcripts, and the copy passed the project's own rejection-rule lint with zero hits. Two critic passes, one before and one after revision, cost USD 0.73 of the client key in total, including failed attempts.

**The headline finding.** Most of the gap between what WIA wants and what the system produces is not in the writer. It sits upstream, in what the system reads and how it chooses. For this week:

- **The input was five hand-picked excerpts.** The strategist benchmark for Week 2 sees five pre-selected excerpts, 99 turns in all, one per meeting. The week is really eleven recordings. One whole prospect call (Ivor) and half of the office hours were never in the input. So were The Penny's Meta audit and budget reset, and every internal call. The "selection" WIA asked about was made before the strategist ran.
- **There is no strategy brief, cross-call synthesis or account memory.** Without them, the system cannot:
  - notice that four separate calls share one idea;
  - see that an angle would repeat a point published two weeks earlier;
  - see that an angle would undercut a live offer;
  - know that the June recommendations were built by September.
- **One client story gets split into tactics.** Strategist v6 turns the Diamond A Ranch review into two or three narrow cards ("A later tour date deserves its own follow-up"). WIA's own model is one story told as "this is how we worked through it, and this is the standard you should expect."

**Where manual judgment was needed:**
- connecting moments across calls;
- writing a weekly strategy brief;
- checking freshness against what the giveaway actually said;
- resolving identities and privacy (Erin is the banned-name case-study client, Noam is a woman, Fallon has left, Ali spells her name "Ali");
- following accounts forward in time;
- writing scripts in Whitney's spoken register.

Each of these is a buildable stage. None needs a new model.

**[Revised 20 Oct]** These input problems are real, but this run had complete inputs and still chose platform education ("Meta takes your instructions literally") and an office-hours troubleshooting walkthrough. Fixing inputs is necessary, not sufficient. The missing piece is a test on the point of each idea (section 0A; section 14, V1 to V6).

**The top recommendations,** in priority order. Section 9 has detail and effort for each.
1. Run the strategist on the full week's scenes, not excerpts.
2. Admit internal calls as a "team practice" evidence class.
3. Add a weekly strategy brief stage before angles.
4. Fix the published register so each campaign has its real central points, and make recency a ranking input.
5. Add a cross-call synthesis pass and a "story card" type.
6. Add account memory (a per-client timeline) with identity resolution.
7. Decide on a minimal pack stage. Ruling R31 parks packs, but the client judges the system on packs.

---

## 1. Method, and what was manual

| Step | What I did | Could the system do it today? | What it needs |
|---|---|---|---|
| 1. Verify the source period | Mapped the review document's citations (T02, T07, T10, T11) to `week_2026-06-08`, Zoom batch "week2". Confirmed the dates from inside the recordings (the World Cup opener on 11 June 2026; a test lead dated 6/11). Queried the Fathom API (no recordings for 1 to 22 June). | Partly: the week rows exist, but their dates are "meeting_dates_unknown". | Date inference from transcript content (fixtures, explicit dates, relative references) to back up the calendar labels (1.B dates). |
| 2. Read the whole week | Read all 5 client and prospect calls in full; an agent read the 5 internal calls plus a fragment. About 105K tokens of dialogue. | No. The benchmark strategist sees 5 excerpts; internal calls are excluded at normalisation. | Recommendations 1 and 2. |
| 3. Follow accounts forward | Pulled later mentions of each Week 2 account from 29 later transcripts and the ChatGPT export (Diamond A Ranch's video, selfie and photos built by 9 September; The Penny's 0 to 105 tracked leads; Erin's identity). | No. | Recommendation 6 (account memory). |
| 4. Build the strategy layer | Wrote a one-page brief: publishing window, live offers and their timing, the content plan's mix and CTA rule, recent central points, Savannah's priority series, the objections each offer must answer. | No. The inputs exist (KB 05, 13, 14, `published-central-points.json`), but there's no stage that assembles them, and cards don't have to serve a brief. | Recommendation 3. |
| 5. Find through-lines across calls | Found five ideas that each recur across several calls (for example "the platforms do what they're told" in T01, T02, T07 and T10). | No. The strategist reads scenes; nothing clusters them by WIA belief or process or counts independent evidence. | Recommendation 5. |
| 6. Check freshness | Checked each candidate against the published register. The register's 5 October giveaway entry says only "apply for a free audit"; the export showed the giveaway's real central points ("Google's recommendations aren't always what's best", "Google Reps Aren't Your Marketing Strategist"), which killed my first ATTRACT choice. | Partly. The register and a same-point flag exist, but campaign entries lack their real points, and the flag doesn't affect ranking. | Recommendation 4. |
| 7. Choose three | One per funnel stage, one per offer, three kinds of proof, three different calls, no repeats from the past four months, no undercutting the live audit offer. | Partly. v6 enforces an ATTRACT card and a pillar mix, but not offer balance, offer timing or story-first framing. | Recommendations 3 and 5. |
| 8. Frame each angle as WIA's work | Whitney's 13 October model: the scene, how we worked through it, what we built, the standard to expect. | Partly. v6 is WIA-centred, but splits stories into tactics. | Recommendation 5 (story card) and the prompt rules in section 10. |
| 9. Write the copy | By hand, against the voice guide, editing guide, rejection rules, format guide, exemplars and Whitney's spoken feedback. Scripts were written in her spoken register, with phrases from her own calls. | Partly. Contract v3's writer produces Reel scripts, an email and captions, but it hasn't been tested against these criteria, and the pack stage is parked (R31). | Recommendations 8 and 9. |
| 10. Fact-check every line | Every factual line traced to a timestamp; the appendix of the packs lists them. | Partly. Contract v3 has a claims ledger and a verifier. | Wire the ledger to pack copy. |
| 11. Privacy and identity | Kept Erin unnamed and unlinked from her published case study; used "she" for Noam; never named Fallon as current; dropped babies, ugly-day and 2027-sales details; kept all prices out. | Partly. RR-27 and RR-28 exist; there's no alias resolution, no pronouns, no do-not-name flags per person. | Recommendation 7. |
| 12. Rule lint | Ran `rejection-rules.patterns.json` over the copy sections. Final run: 0 hits. | **Yes**, reproducible today. | Add the patterns in section 6. |
| 13. Critic pass | GPT-6.1 Sol as "Whitney's most demanding editor", given the KB documents and her feedback transcript. It found real issues (DIY drift, "booking" where the evidence is tracked leads, clicks treated as booked tours, sibling repetition, LeadLock and ELEVATE scope). It also over-flagged true quotes it couldn't verify. | Semi-automatic (a script). | Recommendation 12. |

---

## 2. Source period: verified, and the assumption corrected

**The assumption.** The brief assumed the packs came from the week of the 13 October feedback call, or the week before. **They didn't.**

**Where they came from.** The 13 October packs were built from benchmark Week 2: the Zoom batch labelled 8 to 14 June 2026, 11 recordings.

**How that was established:**
- The review document's citations (T02, T07, T10, T11) match that batch's file order exactly.
- The developer's 13 October ChatGPT simulation says so: "The week is 8 to 14 June 2026".
- Two in-transcript facts independently confirm the week:
  - Erin mentions the World Cup opening match, Mexico against South Africa, which was played on 11 June 2026.
  - Fallon reads a test lead dated "6-11".
- The Diamond A Ranch call was on 10 June: Fallon says "I meet with them on the 10th" in T06.

**Fathom can't verify June.** The API returns zero recordings for 1 to 22 June 2026, because WIA recorded on Zoom then. For 5 to 19 October, Fathom lists **33 meetings**. The local database holds only a handful of October Fathom transcripts. They include:
- Google Ads Office Hours (9 and 15 October);
- a Messaging & Positioning Call (The Brightside);
- The Penny + WIA Monthly Strategy Call (13 October);
- Press Record and Ridgefield strategy calls;
- weekly Google and Meta meetings.

October is a rich, current corpus that hasn't been ingested yet (section 9, recommendation 14).

**A point of honesty to carry into the presentation.** The 13 October packs were not generated by Content Atelier. They were generated in Whitney's ChatGPT by the developer, and their copy matches the export, conversation `6acde8a5`. The new packs aren't system output either. The client document says plainly that the new packs set the target the pipeline is being built to reach. The presentation should not describe either set as generated by the system.

---

## 3. What the client actually asked for

These requirements come from four sources:
- the 13 October feedback call;
- Whitney's alternative-angle tab, with its seven-field framework;
- her own five typed messages in the ChatGPT export (`6acd92cc`);
- her editing history, now KB 17.

| # | Requirement | Her words (source) | Met by the system today? |
|---|---|---|---|
| 1 | WIA is the subject; the call is evidence | "our content can talk about the process of our work, not just the specifics of the conversation" (export) | Mostly (strategist v5 and v6) |
| 2 | Zoom out the takeaway; keep the example specific | "if they would have zoomed way out the takeaways would have been much more impactful" (export); "I'm okay with kind of zooming out a little bit more to our broader audience" (call) | Partly: audiences are now WIA's market, but cards stay narrow |
| 3 | Not how-to or DIY; reflect on the conversation and set the standard | "this is how we talked through it… That's what your expectation should be of working with… an advertising partner" (call) | No. v6 cards are still "tactic" lessons |
| 4 | A strategy layer and a reason for the selection | "why the system selected these six ideas over everything else"; Savannah's mix | Partly: v6 has `considered_not_selected` and a pillar mix, but no strategy brief |
| 5 | Funnel balance and not every piece selling | Content plan: mostly WARM, ATTRACT for reach, about one CONVERT; one offer CTA a week | Partly: v6 forces one ATTRACT card; there's no CTA plan across a week's pieces |
| 6 | Punchy hooks; subjects about the problem | "a little bit more enticing… about… the problem than the process" (call) | Untested at pack level |
| 7 | A casual spoken register in scripts | "a little bit more casual, a little less polished… more conversational" (call) | Untested. There's no spoken-voice exemplar set |
| 8 | Slide 1 states a tension | "when you just lead with more inquiries, more tours booked, like that doesn't really sound like a problem" (call) | Untested |
| 9 | Personality in email; CTA variety | "infuse a little bit more personality"; "sometimes I'm asking for a reply. Other times… the sales page" (call) | Untested |
| 10 | Separate public content from internal intelligence | Her tab: "Distinguish public-facing content opportunities from internal audience research or objection intelligence" | Yes: v6 has `internal_insights` |
| 11 | Refine, don't replace; accuracy | KB 17 and RR-46 | Yes, at the rules level |
| 12 | Volume: three strong angles a week, a bank for light weeks, repetition fine after 1 to 2 months | "three really strong angles per week"; "keep a bank of content"; "maybe like a month, two months" (call) | Partly. The KB says 90 days, and her stated window is shorter (see section 4, F5) |

---

## 4. Findings: evidence and context

**F1. The strategist benchmark reads excerpts, not the week.**
- `research/quality-experiments-2026-10-18/sources/week2.json` holds five moments with 99 turns, one per meeting:
  - Penny buying research;
  - Diamond A tour follow-up;
  - Erin clicks without conversions;
  - the GHL chat widget;
  - Noam's audit.
- Strategist v5 and v6 and the live week (L.B6) were measured on these packets.
- Never seen: Ivor's call (T10, the strongest founder explanation of the week), Felipe's half of office hours, The Penny's Meta audit and budget reset, the internal account review (T06), and T03 and T08.
- **Consequence:** the system couldn't have found Pack 1 or most of Pack 2. The benchmark measures the strategist's writing on a human pre-selection, not its judgment over a week.
- Phase 2 already extracts scenes from full documents (2.B11: 1,605 of 1,669 scenes verified across 27 documents), so the fix is mostly to change which packet the strategist gets.

**F2. Internal calls are excluded, and they hold WIA's standards.**
- At normalisation, 5 of the 11 Week 2 recordings are excluded with "Internal call: only WIA staff speak, so it is not client evidence."
- Internal calls are where WIA's behind-the-scenes process lives, and "team strategy meetings" is on Savannah's behind-the-scenes list. This week they contained:
  - the account review that judges each account against its own normal (T06);
  - "Google ROAS over 12x, Meta more leads but none buy" (T06);
  - Whitney's "reviews are not market research" and the new LeadLock survey service (T03, T09);
  - testing the AI widget on WIA first (T09);
  - the Diamond A Ranch follow-up plan (T09);
  - the observation that ChatGPT-sourced inquiries arrive cold (T03).
- They're the wrong source for client quotes, but the right source for WIA perspective and process.

**F3. There's no account memory, so stories end where the call ends.** All three account stories have documented sequels in later transcripts and in the client email threads in the export:
- **Diamond A Ranch.** The supplemental copy was ready on 6 July. The welcome video by SMS was proposed on 17 August. Tina confirmed on 9 September that the selfie, photos and packages landing page were "all done". On 5 October Whitney noted things were "doing better… funnel-wise and responsiveness-wise".
- **The Penny.** Zero tracked leads went to 105 in a month at about $8 (15 September call summary).
- **Erin.** She is the anonymised $22K-to-$70K case-study client, published 31 July to 6 August, whose name must never be used.

Without this memory, the 13 October packs ended on "Those were ideas to discuss and test" about changes that were in fact built, and a privacy rule ("never name Erin") can't fire.

**F4. Identities aren't resolved across sources.**
- `aliepler`, "Allie", "Ali Epler" and "Diamond Day Ranch" are one person and one account.
- "iver" is Ivor.
- Noam is a woman ("I'm also a mom", "I'll talk to my husband"). The 13 October packs called her "he".
- Felipe Cortes (T07) isn't Felipe Luna (2025).
- Fallon Looney left on 14 August. The 13 October briefs said "Whitney and Fallon review the pipeline".
- 1.B12 (terms with variants) is the natural home for this; it needs people, pronouns, client identity and do-not-name flags.

**F5. The published register hides campaign content, and recency doesn't steer ranking.**
- `published-central-points.json` records the 5 October entry as "The 2026 Google Ads Audit Giveaway: apply for a free audit." The giveaway's posts actually argued "Google's recommendations aren't always what's best for your wedding business" and "Google Reps Aren't Your Marketing Strategist". My first ATTRACT angle ("Google and Meta don't share your goals") would have repeated them within two weeks; I caught it only through the export.
- "Reviews aren't market research" went out on 10 June, the same week as the calls, yet it ranks first in all three v6 Week 2 samples. The verifier's same-point check flags it, but ranking ignores the flag.
- The KB says "never repeat a central point published in the last 90 days". On the call, Whitney said "maybe like a month, two months". Reconcile these and record a ruling; I'd suggest 60 days, or 30 for a fresh angle on the same point.

**F6. Offer timing isn't modelled.**
- "You can outgrow one-off ad audits" (13 October angle A03) would have run while Carmen is delivering the giveaway audits (late October to early November).
- In July, Whitney positioned the audit as the first step toward the Google Search Accelerator ("your entire $297 will be credited").
- The strategy brief needs a calendar of live offers and what must not be undercut.

**F7. The ChatGPT export analysis missed the attachments and the authorship.**
- The developer's pasted inputs, including Content Atelier's own Week 2 output (Pasted text 8), live in `.dat` files that the 18 October analysis didn't read.
- Mapping nodes carry only `parent` links, so a parser that walks `children` silently returns nothing.
- After 08:15 on 13 October, every user turn in the two simulation branches was typed by the developer in Whitney's first person ("i want the captions the way i write").
- The voice samples he pasted were April 2024 emails with emoji subject lines, which ChatGPT copied ("👀"). Two of the three "captions the way I write" were ChatGPT drafts she had accepted without editing.
- Any learning from the export needs branch reconstruction, author attribution and sample provenance.

**F8. Fathom intake lags.** See section 2. The October weeks are the fresh corpus WIA cares about now. The weekly Google and Meta meetings and office hours are exactly the behind-the-scenes evidence F2 describes.

---

## 5. Findings: reasoning and selection

**G1. There's no cross-call synthesis.** WIA's strongest ideas are patterns:
- "The platforms do what they're told": T01, T02, T07 and T10, plus Carmen's internal remark.
- "Our work starts after the leads arrive": T02, the T01 tracking plan, the T06 revenue check, Noam's lost leads.

The voice guide names this exact skill ("Notices patterns. Connects unrelated ideas."). The strategist sees scenes one at a time, and nothing counts independent support. A synthesis pass that clusters scenes by WIA belief or process, and reports how many calls back each cluster, would surface through-lines automatically and make the selection explainable ("supported by four conversations").

**[Revised 20 Oct]** Use synthesis to surface patterns, never to rank. Counting supporting calls favours what is discussed most in account calls, which is campaign mechanics. "The platforms do what they're told" became the 20 October Pack 1, a platform lesson. Each of the six reference pieces Whitney published rests on one moment (section 14, V4).

**G2. There's no strategy brief before angles.** The client asked for this directly. Every input already exists:
- the content plan (KB 14);
- the offer sheet and live offers (KB 05);
- recent published central points (KB 13 and the register);
- Savannah's priority series (KB 01);
- objections by offer (KB 03 and 11);
- the season.

The brief should be assembled deterministically, summarised once by a model, shown to the reviewer, and each card should state which brief need it serves. That's how this week's three were chosen.

**G3. One client story becomes several tactic cards.** In s1 to s3, v6 turns Diamond A Ranch into "The weeks before a venue tour deserve their own follow-up", "A later tour date deserves its own follow-up" and "The wait before a venue tour belongs in your ad strategy", with "A virtual preview…" and "Your tour calendar…" considered.

Each card is accurate, and each one is the narrow, educational shape Whitney rejected. Her model is one story card: the scene, how we worked through it, what we built, the standard. Proposed rule: scenes from one client conversation produce at most one public card, unless the angles serve different funnel stages, in which case they're linked as a series.

**G4. Founder material isn't linked.** v6 reports "no founder seeds this cycle". Yet the week ties directly to two founder sources:
- Whitney's 12 years in venue and hotel sales, behind her Diamond A Ranch ideas;
- her Director of Catering Sales story, which matches "platforms don't share your goals" (Savannah's verbatim founder-forward idea).

The founder story and Savannah's idea bank are in the KB, but nothing maps scenes to them. A matching step (scene to belief, idea-bank entry or founder story) would supply these links.

**G5. Selection reasons should reach the client.** v6's `considered_not_selected` is good. WIA wants to see it, with freshness, timing and offer-balance reasons. The packs document's section 3 shows the format.

**G6. The system has no model of "where the account stands now".** Pack 3 is a public CONVERT story about an account that, internally:
- dipped in August;
- had a Meta pixel double-counting leads in September;
- had a strategy call cancelled in October.

As of 5 October it was "going well". Before publishing a client story, the system should show the reviewer the account's current state. That's part of recommendation 6.

**G7. A live audit, not a client, was the trigger to hold an angle.** Commercial sense, meaning don't undercut what's on sale this week, has to be an explicit check in the strategy brief, not something the model infers.

---

## 6. Findings: writing and packs

**W1. Packs are parked, but the client judges packs.** Ruling R31 says packs get "no further investment until briefs meet the editorial bar (O24)", and `can_consume` and `POST /briefs/{id}/pack` are v1-only. Contract v3 already carries Reel scripts, an email and caption bodies, so a v3 brief is most of a pack. What's missing is pack-level structure: per-asset cover, on-screen hook, caption, send metadata, a CTA plan across the week, and the sibling checks below. This needs a decision (section 12).

**W2. Scripts need Whitney's spoken register.** KB 15's exemplars are her written copy. The transcripts contain hours of her speaking ("Meta is very literal, right? It will do what you tell it to do", "it doesn't make sense to spend just to spend", "And so now's the time"). A spoken-voice exemplar set mined from her own call turns would give the writer the "casual, less polished" register she asked for. Consent isn't an issue: these are her own words.

**[Revised 20 Oct]** The casual register applies to spoken scripts only. Her sent emails and approved captions are clean and declarative, and her recorded Reels open on a crisp first line. Applying "casual" everywhere was one of the v2 tone failures (section 14.8, T5; rec 31).

**W3. Boundary text must never reach copy.** The 13 October packs printed caveats as copy ("The email engagement didn't tell us why someone booked or canceled"). The new packs keep every caveat in an angle-card boundary and a "before you publish" list. This should become a contract rule and a check: caveat language in a copy field is a flag.

**W4. Clicks are not bookings.** The critic caught three of my own lines that turned clicks into bookings or tracked leads into "booking nothing". A verifier check should compare outcome verbs in copy (booked, booking, signed, converted) against the evidence type behind them (a click, a tracked lead, a booking).

**W5. DIY drift sits in the last line.** The rejected packs, and my own first draft, drifted into how-to through the ending ("take a look at what you've been asking Meta to find", "ask yourself one question"). A cheap check: flag an imperative self-audit (check, look at, ask yourself, review your) in the final two sentences of any asset that isn't an education piece.

**W6. Sibling repetition is the most common defect.** RR-39 bans a caption repeating its Reel's hook. Whitney's wider rule is "repeat ideas, not repeat language". My first draft reused "Meta is very literal", "it doesn't make sense to spend just to spend" and "none of that replaces her" across four or five siblings. An n-gram overlap check across a pack's assets (for example, any shared span of 6 or more words outside approved signature lines) would catch it.

**W7. A weekly CTA plan.** RR-42 allows one offer CTA across a week's three Instagram pieces. The 13 October packs had 15 of 20 pieces ending in "ADS". The pack stage needs a week-level CTA plan, and each asset needs a "no offer" variant for weeks when it isn't the offer post. The new packs handle this by hand in section 4 and in the checklists.

**W8. Use the source's own words for the hook.** Whitney's own subject line from the call ("When more inquiries aren't enough") became Pack 3's subject, and her slide-1 note became Pack 3's slide 1. Feedback captured at Gate 1 or Gate 2 should become locked text for the next draft (RR-46: refine, don't replace).

**W9. Offer facts drift.** Specific drifts to guard against:
- VIP Day is now a step inside the Google Search Accelerator.
- The Accelerators' published framing is "3-Month Guided Implementation", but the bundle runs six months.
- Office-hours schedules and turnaround times are internal.
- ELEVATE access is a waitlist, then a discovery call, with no application.
- "LeadLock is just one element of ELEVATE."

The KB holds all of these. The critic flagged where my copy left a support period unbounded. The offer sheet should feed a per-offer "how to describe it" line that the writer must use.

**[Revised 20 Oct]** This is recommendation 32. Whitney names and explains offers plainly, and sells "in a very intentional, non-sleazy way" (10 Jun). The v2 draft barely named an offer (section 14.8, T6).

---

## 7. Defects in the 13 October packs (QA record)

1. **Reels swapped between packs.** In `Copy of WIA - Content Atelier Review.docx`, Angle 2's pack (the Accelerator) contains Angle 3's three Ivor and ELEVATE Reels, and Angle 3's pack contains Angle 2's Accelerator Reels. Angle 2's carousel caption ends with Angle 1's ELEVATE venue lines ("…talk about whether ELEVATE is a fit").
2. **Captions copied from scripts.** Angle 1's Reel captions repeat the scripts word for word (RR-39).
3. **Noam misgendered** as "he".
4. **Former staff named.** Fallon appears in the briefs as current ("Whitney and Fallon review…").
5. **Every piece sells.** 15 of 20 pieces end with an ADS CTA (RR-42).
6. **Caveats in copy** (W3).
7. **Emoji subject lines** copied from April 2024 samples.
8. **Stale "ideas to explore"** about changes that were built by 9 September.
9. **Slide 1 without a problem**, which was Whitney's note on the call.
10. **Felipe's story had no payoff.** The new pack's payoff is the decision made for the right reason.

---

## 8. What the system produces for this week today, compared with the new packs

| | Strategist v6 on benchmark Week 2 (KB 8, three samples) | The new packs |
|---|---|---|
| Input | 5 excerpts, 99 turns | 11 full recordings, plus later account records |
| Top idea | "Reviews aren't market research" (rank 1 in 3 of 3 samples), published 10 June | Held in the bank as already published |
| Diamond A Ranch | Two or three tactic cards | One story card with what we built |
| Ivor's call (Meta is literal; full funnel; onboarding) | Absent from the input | Pack 1 |
| Office hours | "Carmen's 100-click checkpoint", "A good click-through rate still leaves us questions" | Pack 2: what support looks like, with both members' stories and the prospect's fear |
| Founder material | "No founder seeds this cycle" | Twelve years in venue sales (Pack 3); the catering story banked for December |
| Patterns across calls | None | Five through-lines; Pack 1 rests on one |
| Offer timing | Not modelled | Audit angle held until after the giveaway audits |
| Copy | Not produced (packs parked) | Full pack: 3 emails, 9 Reels with captions, 3 carousels |

v6 is a real improvement over v1 and v4. Its titles are WIA-centred, every sample has an ATTRACT card, and it keeps a considered-but-not-selected list. The remaining gap is in the inputs and the selection logic, and it's buildable.

**[Revised 20 Oct]** The "new packs" column describes the 20 October packs. The reassessment judged two of their ideas wrong:
- **Pack 1, "Meta is literal".** It's a platform lesson, and it casts Ivor, the week's clearest ELEVATE buyer, as a beginner who boosts posts.
- **Pack 2, office hours.** It's a troubleshooting procedure led by a member's failing campaign.

**What replaced them in v2:**
- the T01 budget reset ("How we approach a new client's ad budget");
- Diamond A, reframed as what a strategy call with WIA is for;
- the AI-assistant prospect (T11), as the Accelerator CONVERT pack.

Section 14 has the evidence.

---

## 9. Recommended changes to the implementation plan

Effort: S is under a day, M is 1 to 3 days, L is a week or more. Proposed IDs follow the plan's numbering.

| # | Change | Where it lands | Effort | Done when |
|---|---|---|---|---|
| 1 | **Full-week input for the strategist.** Benchmark v2 packets are the week's verified scenes (2.B11), not the five excerpts; 3.B3 runs over the window's scenes. | E.B27 (new), 3.B3 | M | v6 on full Week 2 surfaces the T01 budget reset and Ivor's "on paper… it's all fine" scene, not just the "Meta is literal" teaching turn **[Revised 20 Oct]**. The benchmark reports scene coverage. |
| 2 | **Internal calls as "team practice" evidence.** They're admitted with a role: they can support WIA perspective and process, never as client quotes. Names and figures are blocked from copy by default. | 1.B13 selection rule, 2.B scene types, verifier | M | T06's account review and T09's survey service reach the strategist. The verifier blocks client names or figures from internal calls appearing in copy. |
| 3 | **Weekly strategy brief.** Assembled from KB 14, 05, 13, 01, 03 and 11, the published register and an offer calendar (live offers, windows, do-not-undercut). One model summary. Cards must cite the brief need they serve. | E.B28 (new); extends L.B10 and 3.B3 | M | Every cycle shows a one-page brief at Gate 1. Each card names its brief need, pillar, offer and CTA slot. **[Revised 20 Oct]** The brief lists *beliefs to prove* this window, not funnel slots, and each card cites one (rec 18). |
| 4 | **The published register at piece level, with recency in ranking.** Split campaigns into pieces with their own central points (fix the 5 October entry). Feed same-point recency into rank (as a penalty or a hold-until date). Record a ruling on the window. | E.B25 (f) follow-up, 3.B5, 3.B10 | S to M | A card repeating 10 June or 5 to 16 October content drops in rank or is held, with the reason shown. |
| 5 | **Cross-call synthesis and the story card.** A pass that clusters the week's scenes by WIA belief or process (KB 16 and 07) with counts of independent support. A strategist v7 rule: one public card per client conversation unless the funnel stages differ. A "story card" shape: scene, what we did, what we built, standard. | E.B29 (new), strategist profile v7 | M to L | **[Revised 20 Oct]** On Week 2, the slate has exactly one Diamond A Ranch story card, and its point is what a strategy call with WIA is for, not a diagnostic sequence. Synthesis surfaces patterns but doesn't rank by call count (rec 19). |
| 6 | **Account memory.** A per-client timeline built from later transcripts, client email threads and reports: what was recommended, built and measured, the current account state, and consent status. The brief writer gets "what happened next", flagged for permission. | 3.B17 (new; "3.B14" was already taken) **[Revised 20 Oct]**: raise toward P0 (rec 26); uses 1.B dates and 2.B search | L | Pack 3's "what we built" can be produced from the database, with sources, without the export. |
| 7 | **Identity resolution.** People and clients with aliases, pronouns, staff status with dates, and do-not-name or do-not-link flags (Erin to the case study). | 1.B12 extension, roster (KB 04) | S to M | "aliepler", "Allie" and "Ali" resolve to one person. Noam's pronoun is recorded. A copy reference that would link Erin to the case study is flagged. |
| 8 | **A minimal pack stage (needs a decision on R31 and O24).** A pack contract over brief v3: per-asset cover, on-screen hook, script, caption, send metadata, a week-level CTA plan, "no offer" variants, and a "before you publish" list. Uses the v3 claims ledger. | Re-scope R31 with the owner; new 5.B13 | L | A v3 brief produces a pack that passes section 6's checks and the critic with no blocking item. |
| 9 | **Spoken-voice exemplars.** A KB document built from Whitney's own call turns (her phrasing, rhythm and typical moves), used for scripts only. | KB 18 (new); E.B25 process | S | Script drafts use her spoken patterns. The critic's "sounds like Whitney" rises on scripts. |
| 10 | **New copy checks.** Caveat language in copy (W3); outcome verbs against evidence type (W4); a self-audit final line (W5); sibling n-gram overlap (W6); weekly CTA count (W7); "Here's the thing" and similar (already in RR-34). | E.B24 extension, `rejection-rules.patterns.json`, verifier | M | All six checks run on pack copy, with tests. **[Revised 20 Oct]** Add four more (rec 24): aphoristic kickers, the same line across formats, detail density, and hook fidelity checked against the ledger. |
| 11 | **The ChatGPT export, done properly.** Read the `.dat` attachments, rebuild branches from `parent`, detect authorship (Whitney, developer, team), tag sample provenance (Whitney-written, AI-approved or AI-accepted). | L.B2 seed tools, research tools | M | The export seed never treats developer-typed or AI-accepted text as Whitney's voice. |
| 12 | **An automated critic before Gate 2.** A second-family model plays "Whitney's editor" with the KB and her feedback anchors, and gets the claims ledger so it doesn't flag verified quotes. Its output is reviewer notes, never auto-edits. About USD 0.16 per pack on GPT-6.1 Sol. | E.B3 (judge) sibling; Gate 2 | S to M | Each pack shows the critic's top fixes beside the copy. **[Revised 20 Oct]** The critic must also receive Whitney's verbatim finals (knowledge base 19) and the source transcripts, and compare against them (rec 25). |
| 13 | **LLM failure mode: reasoning that eats the budget.** Through OpenRouter, Sonnet 5.5 (served by Google) made reasoning mandatory, ignored `reasoning.max_tokens` and returned `content: null` with `finish_reason: length` at 9,000 and 16,000 completion tokens. Treat null content with a length finish as a classified, retryable failure with a higher cap, or pin the provider. | `llm/request.py`, E.B1 | S | A test covers null content with a length finish. |
| 14 | **October Fathom intake.** Run the Fathom path (1.B14, 6.B live intake) for 1 October onwards. 33 meetings exist between 5 and 19 October. | 6.B, 1.B14 | S to M | The October weeks have scenes. A current-week cycle can run on them. |
| 15 | **Pack-level rubric anchors.** Add Whitney's 13 October lines as judge anchors: not DIY, zoom out the audience, a punchy hook, casual spoken scripts, a problem-led subject, a slide-1 tension, CTA variety. | E.X7 rubric v2, E.B3 | S | The judge scores packs on these, and is calibrated once Whitney reviews. |

Suggested order: 1, 3 and 4 first, since they're the cheapest and change the most. Then 5 and 2, then 7 and 10, then 8 (with the owner's decision), then 6.

---

## 10. Sketches for the new stages

**Strategy brief (recommendation 3).** Assembled deterministically, then summarised once:

```
cycle_window, publishing_window, season ("engagement season in N weeks")
content_plan: {emails_per_week, ig_pieces, mix, offer_cta_rule, default_keyword}
live_offers: [{offer, status, access_route, window, do_not_undercut: [...]}]
recent_central_points: [{date, piece, point}]   # piece-level, last 12 months, recency-weighted
priority_series: [...]                          # Savannah's list, with last-published dates
objections_by_offer: {...}                      # KB 03 and 11
needs_this_week: [{pillar, offer, need}]        # e.g. WARM, Accelerators, "show support, not describe it"
```

**Synthesis pass (recommendation 5).** The input is the week's verified scenes plus KB 16 (beliefs) and KB 07 (processes). The output is clusters of the form `{belief_or_process, scenes:[...], calls:[...], independent_support:n, founder_link?, idea_bank_link?}`. The strategist ranks clusters and story candidates together.

**Story-card rule for strategist v7:**
- Scenes from one client conversation become at most one public card. A second card is allowed only for a different funnel stage, and it's linked as a series.
- A story card names the scene, what WIA did, what WIA built later (from account memory, when available), and the standard the reader should expect.
- The reader is WIA's market, not the call participant.

**Pack contract (recommendation 8).** Per asset: `{key, format, job, cover, on_screen_hook, body, caption, cta: {type, keyword?, no_offer_variant}, send_meta?}`. Per pack: `{cta_plan_by_week, before_publishing:[...], claim_refs:[...]}`.

The checks are those in recommendation 10. Hooks must be distinct across assets. A caption can't reuse any 6-word span from its script.

**[Revised 20 Oct]** The pack contract needs four additions:
- the **angle card** in Whitney's tab format (rec 29);
- the **brief** in the 13 October structure, with Savannah's narrative outline;
- a **Reel plan**: story, stance and b-roll text (rec 33);
- the format rules in section 14.9 as validators (rec 30).

Each asset also gets a `register` field (spoken or written) and an `offer_descriptor` (rec 32) where an offer is named.

---

## 11. Budget and QA record

**Spend on the client key** (the internal key was at zero):

| Run | Model | Cost (USD) | Result |
|---|---|---|---|
| Critic on the first draft | GPT-6.1 Sol | 0.16 | Useful, adopted |
| First Sonnet 5.5 attempt | Sonnet 5.5 | about 0.20 | Returned empty content (recommendation 13) |
| Second Sonnet 5.5 attempt | Sonnet 5.5 | about 0.20 | Returned empty content (recommendation 13) |
| Third Sonnet 5.5 attempt | Sonnet 5.5 | 0 | Refused: "Reasoning is mandatory" |
| Critic on the revised draft | GPT-6.1 Sol | 0.15 | Further fixes adopted (see below) |

Total: USD 0.73 (the client key went from 3.71 to 2.98). The Fathom API check cost nothing.

**The second critic pass.** Even on the revised draft, the critic scored most assets 2 to 3 out of 5 for hook and voice. Read that number carefully. The critic was told to be harsh and not to praise, and it couldn't see the transcripts, so it flags Whitney's verbatim lines as "AI polish" and true events as unverified. Its scores aren't a quality measure. Whitney's own review is.

Its specific catches were real and are fixed in the final version:
- the Pack 1 carousel called a prospect discovery call one of "three accounts we worked on";
- Pack 2's carousel used a numbered "first question, second question" structure that read like a checklist;
- a false choice between understanding your ads and handing them off;
- stacked CTAs;
- "DM us" with a "-Whitney" sign-off;
- "lead volume tells you the ads are working";
- ELEVATE not named plainly in the CONVERT copy;
- placeholder send dates.

Its main structural objection was that "here's how we worked through it" still reads as instruction. That's a judgment call against Whitney's own words on 13 October ("This is how we talked through it. This is how we're going to work through it for her"), and the packs follow her model. It's worth asking her directly, and recording her answer as a ruling.

**Lint.** `rejection-rules.patterns.json` over all copy sections:
- First draft: 2 flags, RR-31 and RR-34 ("Here's the thing").
- After revision: 1 flag (RR-31).
- Final: 0.

**What the critic changed.**
- Reframed Pack 1 from a Meta tutorial to "what we did on three accounts". **[Revised 20 Oct]** This changed the subject, not the point. The point stayed "Meta optimises for the action you choose" (section 14, V1).
- Removed self-audit endings.
- Corrected "booking nothing" to "zero tracked leads" and "book tours" to "click through to schedule".
- Stated LeadLock's role within ELEVATE once per piece.
- Bounded the Accelerator support language.
- Removed jabs at other agencies.
- Attributed Carmen's rules of thumb to her.
- Broadened the conclusions beyond venues.
- Cut the repeated lines between siblings.

**What I rejected from the critic.** Replacing Whitney's verbatim phrases ("Meta is very literal", "it doesn't make sense to spend just to spend", "fall in love with all of the other aspects"). The critic couldn't see that they're her own words. This is why recommendation 12 gives the critic the claims ledger.

**Facts checked line by line.** All quotes, sequences and implementation claims were checked against the transcripts and the dated records cited in the packs' appendix. Two of my own errors were corrected along the way:
- Felipe's experiment was suggested by WIA, not by Google.
- Carmen had never seen the sitelink problem before, so "seen it a hundred times" was removed.

---

## 12. Decisions for the owner

1. **R31 and O24.** Do we fund a minimal pack stage now (recommendation 8)? The client evaluates packs, and contract v3 is already most of one.
2. **The repetition window.** The KB says 90 days; Whitney said one to two months. Proposed: 60 days, recorded as a ruling.
3. **Internal calls as evidence (recommendation 2).** Confirm with WIA that the team's internal meetings may inform public content as process, never as names or figures.
4. **Account memory permissions.** Using later client emails and reports for "what happened next" needs WIA's agreement on which sources count and how consent is recorded.
5. **The presentation framing.** Present both the 13 October packs and these as non-system output (section 2). The new ones set the target the pipeline is being built to reach.
6. **Permissions to request from WIA**, so the packs can carry results:
   - The Penny's 0 to 105 tracked leads;
   - Diamond A Ranch's anonymised story and a LeadLock figure;
   - Carmen's 75 to 100 click checkpoint;
   - whether the office-hours venue member can be linked to her case study.

**[Revised 20 Oct] Added by the reassessment:**

7. **Week 2 as a benchmark.** Using the reassessment's weak and strong pairs in prompts would contaminate Week 2. Recommended: keep Week 2 out of prompts, and write the contrastive pairs from Week 1, whose review document holds Whitney's own rewrites.
8. **Founder notes.** Ask Whitney for a five-minute weekly "what stood out" note (rec 22).
9. **Pack size.** Allow two Reels per idea when an idea doesn't support three, with one of them text on b-roll (rec 23).
10. **Stance confirmation.** Cards that take a public position (for example, on AI) carry a flag that needs Whitney's confirmation before development.
11. **The angle title rule.** Strategist v6 limits "How we…" titles to one per slate, but all six angles in Whitney's own tab are titled that way. Proposed: replace the rule (rec 28), and confirm with Whitney that plain descriptive titles are what she wants to see at Gate 1.

---

## 13. Files produced in this run

- **The client packs:** `deliverables_2026-10-21/WIA-Content-Packs-Week-of-8-14-June-2026.md`, with its parts in `deliverables_2026-10-21/parts/`.
- **This document:** `deliverables_2026-10-21/Content-Atelier-Findings-and-System-Improvements.md`.
- **Working notes** (scratchpad, not in the repository):
  - the transcript reading notes;
  - the internal-call extraction;
  - the ChatGPT export findings, with its evidence and pack-copy companions;
  - the critic outputs;
  - the scripts: the docx converter, VTT compactor, transcript export, Fathom check, context grep, lint and critic.

Nothing was committed, pushed or deployed, and production was not touched.

**[Revised 20 Oct] Reassessment files** (`deliverables_2026-10-21/v2_reassessment/`):
- `WIA-Content-Packs-Week-of-8-14-June-2026-v2.md`: the rebuilt client packs;
- `Diagnosis-Why-The-WIA-Packs-Keep-Missing.md`: the evidence and side-by-side comparisons;
- `Reproducibility-and-System-Findings.md`: the method and the plan mapping (summarised in section 14);
- `superseded/WIA-Content-Packs-v2-before-tone-review.md`: the v2 packs before the tone and format review, kept for comparison.


---

## 14. Findings from the v2 reassessment (20 October 2026)

**Sources:**
- all five client and prospect calls, read in full;
- an inventory of the five internal calls, with quotes and timestamps;
- both review documents, the 13 October call and Whitney's written note on the angles;
- about 30 content threads from the export, focused on Whitney's own messages and followed draft by draft to the published version;
- knowledge base documents 05, 07 and 12 to 17;
- plan sections 1.10, 2.2 and 2.3a, and strategist v6;
- this document and its packs.

### 14.1 What Whitney's own content shows

| Published piece | The one moment | What it shows about WIA | The belief it lands on |
|---|---|---|---|
| "The question we ask every new client" (email, 10 Jun) | No new client has ever said yes to "have you surveyed your clients?" | How deep onboarding goes | "Most wedding businesses are making marketing decisions based on assumptions" |
| "It feels like our sales are on autopilot" (25 to 29 Jun) | A client's sentence, plus 17 to 90 events | They committed to a full system after another agency | Her rewrite: "if ads aren't producing exceptional results, the answer is to stop advertising. Most of the time, that's not the problem… you're judging paid advertising based on an incomplete strategy" |
| The 10-week story (Aug) | "I couldn't do it all." | Ads as infrastructure | "There's a difference between wanting to do less marketing and wanting your marketing to depend less on you" |
| $22K to $70K (Jul to Aug) | "I honestly have no idea if any of this is working" | Rebuilt the foundation and tracking | "You can't optimize what you can't measure" |
| "What I taught my clients this week" (15 Sep) | A training that "had nothing to do with running ads" | Strategy before the platform | "Advertising doesn't start inside Google Ads or Meta Ads Manager" |
| Taylor Swift Reel (Jul) | A cultural moment | How she thinks | Great marketing "gives people a future they can see themselves in" |

**What all six have in common:**
- one moment, never a summary of a call;
- a human sentence or a WIA practice, never a platform mechanic;
- a business belief as the point;
- written for owners already doing the work;
- nothing telling the reader what to change in their own account.

**What her corrections are about.** They are mostly positioning and audience, not wording:
- "This shouldn't be just teaching… It's about highlighting how in depth we work with our clients and how this is a differentiator for us" (8 June, planning content in our own source week).
- "ELEVATE potential clients aren't asking should we try ads… they know in their gut there is missing potential."
- "That hook speaks to someone who's in a place of desperation. That is not our ideal client."
- "Your opening makes it sound like advertising is always frustrating."

**Where her raw input already does the selecting.** Her starting point in ChatGPT is usually her own summary of a call, and it has already picked the moment: "What stood out most to me on the call was…". Our pipeline has to do that selection itself, and it doesn't know to.

### 14.2 Findings

**V1. The rules test the subject of an idea; nothing tests its point.**
- The 20 October Pack 1's core perspective is "Meta optimises for the action you choose".
- It satisfies "WIA is the subject", "zoom out" and "established owners" literally, and still teaches a setting.
- Strategist v6, step 2 ("name the WIA move… a scene with no WIA move… is an educational takeaway") passes every technical scene, because every technical scene contains a WIA move.
- Section 11 records that the critic "reframed Pack 1 from a Meta tutorial to 'what we did on three accounts'". That changed the subject and left the point untouched.

**V2. The surprise test and the takeaway test were missing.**
- Anyone who has run Meta ads knows campaign objectives exist.
- Pack 1's takeaways were instructions to the reader: "Save this for your engagement-season planning", and "Send this to the wedding pro friend who's about to boost".
- **Pass:** the reader thinks "I want a team that thinks like this" or "I hadn't looked at it that way".
- **Fail:** the reader thinks "I should change this in my account".

**V3. The audience was inverted.** Ivor (T10) runs an elopement business doing "$500 to $700 or so a year" (weddings). He spends "$100,000 or so a year in ads", has built his own automated booking flow, and said: "on paper… it's just all fine… but I think there's massive room for improvement."

That is Whitney's ELEVATE buyer, word for word. The pack used the one turn where Whitney explains a platform and recast him as a cautionary tale for people who boost posts.

**V4. Ranking by amount of evidence selects mechanics.** "Source strength: backed by more than one moment or more than one call" and G1's through-lines favour whatever is discussed most in account calls. That is campaign structure: Meta's three phases appear in T01, T02 and T10.

The week's most Whitney-shaped moments are single ones:
- the budget reset (T01);
- "the things that are kind of beyond the ads" (T02, 42:03);
- "I don't know what I've done. I don't know what we changed." (T11)

**V5. The human lines are drowned.** T10 is 186 lines, and one of them defines Ivor. Any stage that summarises, counts or retrieves by topic similarity loses lines like that.

The scene extractor needs two scene types it doesn't have:
- a verbatim **human line**: feeling, self-description or a business confession;
- a **counter-expected WIA decision**: something that cost WIA money or a sale, or went against the industry default.

**V6. "Process content" was read as a procedure.**
- The 20 October Pack 2 (office hours) and Pack 3 (Diamond A) narrate a sequence of checks. Pack 2's list: click-through rate, a click checkpoint, visit recordings, sitelinks, a banner, a thank-you page. Pack 3's: stages, then context, then email click data, then ideas, then the build. That is the "here's how to diagnose your own problem" structure Whitney rejected on 13 October, retold in the third person.
- Whitney's process pieces show one practice, the belief behind it, and how it differs from what other agencies do.
- Detail density is a usable signal: her stories carry one or two concrete details, and the 20 October Pack 3 carried about seven.

**V7. Some offer positioning was wrong.**
- **Lead forms.** Pack 1 offered "a lead form" as WIA's method. Knowledge base document 07 records Whitney on 6 June: "We do not recommend lead form ads on Meta."
- **The office-hours hook.** Pack 2 opened an Accelerator pack with a member's "we're spending money, and we're not getting anything", which presents a WIA offer as frustrating.
- **Internal context.** The internal calls (T03) show an unhappy Accelerator client at the same time. Stories about members' campaigns not working are the wrong public story now.

**V8. Format completeness splits ideas into micro-lessons.** Three Reels, a carousel and an email per idea, all distinct, came to 16,100 words. Reels became sub-lessons: retargeting, and the rain plan.

Whitney's own campaigns tell one story through a different door per format: 1 to 2 Reels, a carousel, captions and an email. A text-on-b-roll Reel is a normal format for her.

**V9. We encoded her rules, not her moves.**
- The editing guide and the export notes turn her finals into constraints: what not to repeat, which hooks she rejected, banned phrases.
- Knowledge base document 15's exemplars are truncated snippets.
- Nothing in the system shows a raw moment becoming her published piece, and that's where her judgment is visible.

**V10. The evaluators couldn't see what mattered.**
- The GPT-6.1 Sol critic had neither the transcripts nor her finals.
- The lint passes aphoristic AI kickers that her team rejects in ChatGPT ("AI common phrase"). Examples: "Meta is great at following instructions. Somebody has to write good ones."; "None of that replaces her. It keeps her in the conversation".

**V11. Hooks can overstate what the evidence shows.** A blind review of the v2 first draft caught two of these:
- **Who decided.** "Our first recommendation was to spend less", when our team asked how she felt about her budget and she wanted it lower.
- **How much of a call something took.** "We spent most of that call talking about her Sundays", when Sundays came up as one detail.

A rule-based lint can't catch this. A hook checked against the evidence ledger can.

**V12. AI is a recurring client theme.**
- In June, a prospect (T11) used her own AI assistant to set up her Google Ads, then lost track of what changed.
- On 22 September, a client forwarded her AI agent's warning about a Google change, and Whitney's 24 September reply judged it calmly and specifically.

That makes AI both content and a strategy-brief input: "what's changing in our buyers' world".

### 14.3 The method as a buildable procedure

This is the procedure the v2 packs used. Each step maps to a stage.

1. **Purpose before proof** (E.B28, revised). List four to six beliefs WIA's market should hold this window. Each names its offer and the published pieces it must not repeat. Sources are knowledge base documents 16, 14, 01 and 05, and the register.
2. **The moment hunt** (E.B27 and E.B31). Search the full calls for four kinds of moment:
   - human lines;
   - counter-expected decisions;
   - a WIA practice in Whitney's own framing;
   - something the owner knows that a dashboard doesn't.
3. **Pair a moment with a belief** and write the point in one sentence, in Whitney's register (L.B12 exemplars).
4. **The gate** (E.B30). Apply the five tests: point not subject, surprise, takeaway, reader, fit.
5. **Compress the story.** Keep one moment and at most two concrete details. State the belief once, then end on a standard or an invitation (E.B24 detail density).
6. **Plan the pack: one idea, different doors.** No sub-lessons. Two Reels are allowed, and one may be text on b-roll (5.B13, revised).
7. **Write in her register.** Spoken scripts come from her recorded Reels (knowledge base 18). Apply the full construction bans, including kickers and the same line across formats.
8. **Verify:** quotes, later records (3.B17), identities (1.B12), hook fidelity (E.B24), and five or fewer permission items.
9. **Compare with her work** (E.X8). It's a diagnostic. WIA's ratings remain the measure.

### 14.4 New and revised recommendations

These continue section 9's numbering. "Revised" means a change to an item already proposed in revision 7.2.

| # | Change | Where it lands | P | Effort | Done when |
|---|---|---|---|---|---|
| 16 | **Point tests.** Required card fields:<br>• `point` (one sentence);<br>• `point_is_about` (enum: WIA belief / WIA standard / client experience / platform or tactic);<br>• `surprise_for_experienced_advertiser` (with a reason);<br>• `reader_takeaway` (written as the reader's thought);<br>• `belief_ref`.<br>The verifier rejects public cards whose point is "platform or tactic" or whose takeaway is an instruction. | E.B30 (new), strategist profile v7 | P0 | S to M | On Week 1 or held-out weeks, cards like "Give distinct markets distinct landing pages" are rejected or reframed automatically, with the reason shown |
| 17 | **Human-line and counter-expected scenes.** Two new scene types and a ranking boost. | E.B31 (new), scene profile v3 | P0 | M | On full Week 2: T11's "I don't know what we changed", T10's "on paper… it's all fine" and T01's budget reset are extracted as such scenes |
| 18 | **Beliefs, not slots (revised E.B28).** The weekly brief outputs beliefs to prove this window, each with its offer and its do-not-repeat list. Every card cites one. | E.B28 | P0 | S on top of E.B28 | Every card carries a `belief_ref`. The brief shows no pillar "slots" without a belief |
| 19 | **Synthesis without ranking by count (revised E.B29).** Keep the story card (one story per client conversation). Use synthesis to surface patterns ("two owners this week said their spend had crept up"), but drop "independent support count" as a ranking input. | E.B29 | P0 | S | Ranking ignores call counts. A pattern can appear as context on a card |
| 20 | **Transformation exemplars.** Six to eight worked chains from the export: her raw summary, the drafts she rejected (and why), and her published version. Start with the six pieces in 14.1. These are the few-shot examples for the strategist and the writer. | L.B12 (new), knowledge base 19 | P0 | S to M | Knowledge base 19 exists; the strategist and the writer both load it. Needs D14 for export text in prompts |
| 21 | **Blind comparison harness.** Generated pieces are mixed with Whitney's real pieces on similar themes. A judge that has read her finals first guesses authorship and applies the five tests. A diagnostic only. | E.X8 (new); sits beside E.B3 | P1 | M | A report per cycle; never used as the success measure (section 2.3) |
| 22 | **"What stood out" founder notes.** Whitney, or Gisselle for her, adds one line per notable call each week ("what stood out to me was…") through the existing founder seeds. | L.B13 (new); E.B19 (built) | P1 | S | Seeds arrive weekly. This can start now, with no build |
| 23 | **Revised pack plan (5.B13).** One idea, different doors: the formats share the point and differ in scene and hook. Two Reels are allowed, one as text on b-roll. No sub-lessons. | 5.B13 | P1 | in L | The pack plan validates that the point is shared and that the scene or hook differs per asset |
| 24 | **Four more copy checks (adds to rec 10):**<br>• aphoristic kicker endings;<br>• the same sentence or title repeated across formats;<br>• detail density (more than three operational details in one story);<br>• **hook fidelity**: the claim in a hook or subject (who decided, how much of a call, what a tool did) must match the ledger. | E.B24 extension | P1 | M | The v2 draft's two overstated hooks (V11) are flagged in a test |
| 25 | **A critic that sees her work (revised rec 12).** The critic gets Whitney's verbatim finals and the source transcripts, and compares against them, not only against the rubric. | E.B3 | P1 | S | The critic's input bundle includes knowledge base 19 and the transcript excerpts |
| 26 | **Raise account memory (3.B17) toward P0.** Week 2 has almost no outcomes. Later records are the only route to outcome stories, which are Whitney's strongest format. The same records also flagged the account caution behind Pack 1's results (28 September: "the penny we need to take a look at"). | 3.B17 | P0 | L | As in recommendation 6 |
| 27 | **AI in the brief.** A short "what's changing in our buyers' world" input to E.B28: AI agents, platform changes, the season. Sourced from client and prospect mentions in calls and emails. | E.B28 input | P2 | S | The brief lists current buyer-world shifts with their sources |

**Suggested order:**
1. 16 and 18 first: they're cheap, and they can be tested on Week 1 against Whitney's own rewrites.
2. Then 20.
3. Then 17 together with recommendation 1.
4. Then 19 and 26.
5. Then 23 (after D22).
6. Then 24 and 25, and then 21.
7. Recommendation 22 can start this week.

### 14.5 What stayed human in the v2 run

| Judgment | Can the planned system do it? |
|---|---|
| Recognising Ivor as the ELEVATE buyer, not a booster | **Yes, with work:** the full call (rec 1), plus a buyer-profile match against her stated ELEVATE and Accelerator buyer descriptions (knowledge base 11 and 16) |
| Seeing "we lowered her spend" as the surprising point | **Yes:** the surprise test (16) plus counter-expected scenes (17) |
| Linking the June AI call to the September AI-agent email | **Partly:** needs account memory and cross-source search (26). The pairing with Savannah's "thinking like a strategist is the skill" comes from the beliefs list (18) and the exemplars (20) |
| Cutting forensic detail | **Partly:** a detail-density check (24) plus exemplars. Expect editing |
| Keeping internal philosophy out of public copy | **No; it stays human.** Surface it as internal and let WIA decide (rec 2, D24) |
| Spoken register | **Mostly:** knowledge base 18. Keep a Gate 2 voice pass |
| Confirming a public stance (the AI view) | **Stays human:** a stance-confirmation flag (decision 10 below) |

### 14.6 Could the planned system produce the v2 ideas?

| v2 idea | What it needs | Why it passes, and the 20 October idea fails |
|---|---|---|
| "How we approach a new client's ad budget" (T01) | A counter-expected scene (17), paired with the belief "budget follows proof" (18) | Its point is a WIA judgment, and it surprises. "Meta takes instructions literally" fails both the point test and the surprise test |
| "What our strategy calls actually cover" (T02, plus later records) | Full-call input (1), human lines (17), account memory (26), the UVP belief | Its point is the client experience and a standard to expect. "When more inquiries aren't enough" passes only weakly (a generic service claim), and fails on detail density |
| "How we help wedding pros understand their own ad accounts" (T11, plus T07) | A human line (17), Savannah's verbatim CONVERT belief (18), the exemplars (20) | Its point is what the Accelerators build: understanding your own account. The office-hours pack fails the reader test |

**Honest assessment:**
- **Ideas: a credible path.** With 1, 16 to 20 and 26, the planned system has a credible path to proposing all three. The first two are the strongest bets.
- **Copy: still needs editing.** Expect Gate 2 edits on scripts. Don't promise WIA otherwise.

### 14.7 Blind review record

A separate agent first read five of Whitney's finals verbatim, the editing guide, her 13 October call and her rewrite tab. It then judged the 20 October packs (Set A) and the v2 first draft (Set B). It wasn't told which was newer. Scores are 1 to 5.

| Pack | Point belongs to WIA | Surprise | Audience | Strategic use | Sounds like her | Free of AI tells | Hooks | Predicted decision |
|---|---|---|---|---|---|---|---|---|
| 20 Oct Meta literal | 2 | 2 | 2 | 3 | 3 | 2 | 3 | Reject the idea |
| 20 Oct Office hours | 3 | 2 | 1 | 3 | 2 | 2 | 2 | Reject the idea |
| 20 Oct When more inquiries aren't enough | 4 | 3 | 4 | 4 | 3 | 3 | 4 | Light edits |
| v2 Spend less | 4 | 4 | 4 | 4 | 3 | 2 | 4 | Light edits |
| v2 Sundays | 5 | 3 | 4 | 4 | 4 | 3 | 4 | Light edits (fix the hook) |
| v2 AI | 3 | 3 | 3 | 4 | 3 | 2 | 3 | Rewrite the copy, keep the idea |

**The verdict:** "Set B, clearly on the ideas and moderately on the copy. Neither set is publishable without edits."

**What was fixed in v2 after the review:**
- the two overstated hooks (V11);
- Pack 3's stock "doing vs deciding" copy, rewritten around what happened and Whitney's own words;
- about ten aphoristic kickers;
- one invented platform claim;
- the same title repeated across formats.

The fixes haven't been re-reviewed. Whitney's review remains the only real test.

**Cost.** No OpenRouter spend in the reassessment. The client key is still at about USD 2.98.

### 14.8 Tone and format review (after the owner's review of v2)

The owner agreed with the v2 packs' evidence and direction, but not their tone, titles, or the format of the angles, briefs and packs. A second pass compared each format with Whitney's own finished pieces:
- the approved $22K-to-$70K and 10-week carousels;
- her 10 June email, carousel and caption;
- her approved 1 October caption;
- her recorded Reel transcripts;
- knowledge base 09.

The packs were then rewritten. The version before the review is kept in `v2_reassessment/superseded/`.

**T1. Angle titles should describe WIA's work plainly.**
- Every angle in Whitney's preferred-angles tab is a descriptive title of WIA's work: "How we help wedding venues position their value…", "What our keyword research process looks like, and why client conversations are part of it", "What goes into our wedding venue advertising strategy beyond creating attractive ads".
- Strategist v6 says the opposite: "A title names the idea or the tension in it, not the fact that WIA does something. At most one title in the slate may open with 'Why we', 'What we', 'How we' or 'We'."
- The first v2 draft followed the v6 style and used hook titles ("Her ads were working, so we talked about her Sundays"). In her model, the hook belongs in the copy, and the angle title says what WIA does.

**T2. The angle card should use her tab's fields, at her length.**
- Her fields: content pillar / type, audience, why this matters, WIA's expertise or process, evidence in the referenced call, editorial guardrail / next step.
- She uses one to three sentences per field. The v2 draft's cards were long internal evidence dumps.

**T3. The brief is part of the deliverable.**
- The client reviewed a brief structure on 13 October and criticised its content (how-to drift), not its structure.
- The first v2 draft dropped the brief altogether. The owner restated the deliverable: an angle, a brief, an email, three Reels and a carousel.

**T4. Savannah's framework has to be visible in every caption.**
- She checks it constantly: "Did you actually follow the caption structure I prescribed?" (25 Jun), "Does this follow Savannah's framework?" (15 Sep, 1 Oct), "Are you aware of the content/caption formula…" (4 Aug).
- The step most often missing is problems, desires and symptoms: the reader's own situation, in wedding-specific detail ("They're opening multiple tabs… comparing packages…"), before the story. The v2 draft captions mostly retold the story.

**T5. The register depends on the format.**
- "A little more casual, a little less polished" was her note on Reel scripts (13 October, 19:38).
- Her sent emails and approved captions are clean, confident and declarative. The v2 draft applied the casual register everywhere ("Okay, so…").
- Her recorded Reels open on a crisp first line: "70K in new wedding bookings…", "If I can't tell from looking at your website…", "What would happen to your wedding business if…".

**T6. Offers are named, explained, and sold without apology.**
- "I'm looking for conversions. I'd like to sell in the caption but in a very intentional, non-sleazy way" (10 Jun).
- She uses fixed descriptors: "ELEVATE, our full-service advertising management program"; the Accelerators "for venues and wedding professionals who want to manage their own advertising".
- She positions WIA against "most agencies" ("Most agencies jump straight into targeting… We go deeper."), but never against the reader ("I really don't want this to be about how wedding pros are getting their marketing wrong").
- The v2 draft barely named an offer.

**T7. Her carousels have a recognisable shape.**
- **Length and slide 1:** 10 to 12 slides, and slide 1 is an insight about the reader ("You don't need another reminder to 'show up consistently.'").
- **The story** takes two to four slides.
- **The reader's own situation and the reframe** take several slides ("How can I keep up…" becomes "How much of my marketing still requires me…").
- **The close:** a belief slide ("We believe every wedding business deserves that kind of clarity"), then a CTA that fits both DIY and done-for-you readers ("Whether you're looking for someone to manage your ads… or… learn how to manage them yourself… DM us 'ADS'").
- **Voice and density:** "we" and "us" throughout (4 Aug), and real text on every slide.
- The v2 draft's carousels spent most of their slides on operational steps.

**T8. Many of these rules were already written down, and still weren't applied.**
- Knowledge base 09 (the format guide) already records several:
  - email send metadata (DATE, SEND TIME, RECIPIENTS);
  - flowing email paragraphs rather than bullets;
  - "-Whitney" on first-person captions;
  - covers planned as a varied set;
  - real text on every carousel slide;
  - the caption framework.
- The v2 draft broke all of them, because the writer treated the guide as background rather than as a checklist. This is the same pattern as V9: rules that exist but aren't enforced at the moment of writing.

**Recommendations** (continuing section 14.4):

| # | Change | Where it lands | P | Effort | Done when |
|---|---|---|---|---|---|
| 28 | **Angle titles follow WIA's own model.** Replace v6's "at most one 'How we' title" rule. Angle titles are plain descriptions of WIA's work or perspective, and the hook lives in the brief and the copy. | Strategist v7 (with E.B30) | P0 | S | On Week 1, v7's titles read like the titles in her tab |
| 29 | **Angle card contract = her tab.** Her fields, with a one-to-three-sentence limit per field; the evidence detail moves to the ledger. | Card contract (`WeeklyAngleCards` v6) | P1 | S | Cards render in her tab's format at Gate 1 |
| 30 | **Enforce the format guide when writing.** Deterministic checks from knowledge base 09:<br>• email metadata present;<br>• no bullet lists in list emails;<br>• first-person captions signed;<br>• covers distinct within a pack;<br>• carousel slides at or above a minimum density;<br>• carousels in "we"/"us";<br>• a two-path CTA on carousels.<br>An LLM check that every caption contains problems, desires and symptoms before the story. | E.B24 extension; 5.B13 | P1 | M | The v2 draft's format misses (T8) are flagged in a test |
| 31 | **Register by format in the writer prompt.** Casual and spoken for scripts only. Clean and declarative for emails and captions. Scripts open on a crisp first line modelled on her recorded Reels (knowledge base 18). | Writer v3 profile; knowledge base 18 | P1 | S | Gate 2 voice edits on emails and captions drop |
| 32 | **Offer descriptors from the offer sheet.** Each offer gets one approved "how to describe it" line ("ELEVATE, our full-service advertising management program"). CONVERT pieces name the offer as the solution before the CTA, and WARM pieces may name it once. | Knowledge base 05; writer | P1 | S | Every CONVERT asset names its offer with the approved line |
| 33 | **Reel set composition.** A pack's three Reels are planned as a story Reel, a stance Reel and a b-roll text Reel, unless the idea calls for otherwise. | 5.B13 pack plan | P2 | S | The pack plan validates the mix |

**Suggested order:**
1. 28 and 29 first, with recommendation 16. They are cheap, and they change what Whitney sees at Gate 1.
2. Then 31 and 32, which are prompt and knowledge-base edits.
3. Then 30 and 33, with the pack stage.

### 14.9 House style specification by format (for the writer, the pack contract and the checks)

This consolidates sections 14.1, 14.2 and 14.8 into one specification that a writer prompt, the pack contract (5.B13) and the copy checks (E.B24) can implement directly. Each row cites its evidence. Where a rule already exists in knowledge base 09 or 17, it isn't new; the finding is that it has to be checked, not just loaded.

| Asset | Structure | Rules | Evidence |
|---|---|---|---|
| **Angle** | **Title:** a plain description of WIA's work or perspective ("How we…", "What our…", "What goes into our…").<br>**Fields:** content pillar / type, audience, why this matters, WIA's expertise or process, evidence in the referenced call, editorial guardrail / next step. | One to three sentences per field. Evidence detail lives in the ledger, not in the card. The hook belongs in the copy, not the title. | Whitney's tab in the Angle Review; her 13 Oct critique (export `6acd92cc`) |
| **Brief** | In order:<br>1. central point;<br>2. strategic purpose and desired response;<br>3. audience and reason to care;<br>4. WIA perspective;<br>5. supporting example (with timestamps);<br>6. narrative outline (hook, problems/desires/symptoms, main point, transformation, CTA);<br>7. format and creative approach (one editorial job per asset);<br>8. CTA and essential boundaries. | No caveats in the central point. Every asset's job is named before any copy is written. | The 13 Oct brief structure (reviewed; the content was criticised, not the structure); Savannah's framework (knowledge base 01) |
| **Email** | **Header lines:** DATE, SEND TIME, RECIPIENTS, SUBJECT, PREVIEW TEXT.<br>**Body, in order:** "Hi {{contact.first_name}},"; an opening scene; the argument in short, flowing paragraphs; one bold key line; the principle; the offer, named with its descriptor, as the solution; the CTA.<br>**Sign-off:** "Talk soon, Whitney". | **Subject:** a specific observation or quote, about the problem rather than the process.<br>**CTA:** a low-barrier reply ("If you're tired of guessing… simply reply…") or a sales-page link. Vary it across weeks; never "DM" in an email.<br>**Bullets:** no bullet lists.<br>**Standalone:** the email stands on its own (no Instagram references). | Knowledge base 09; the 10 Jun and 15 Sep sent emails; 13 Oct call 12:50 to 13:11 and 16:30 to 16:40 |
| **Reel script** (face to camera) | **Opening:** a crisp first line (a result, a stance, a question, or a client conversation).<br>**Body:** backstory in plain speech; what WIA did or saw; the client's own words; the principle.<br>**Close:** a soft CTA or a DM keyword. | Spoken and casual, as in her recorded Reels. About 45 to 90 seconds. No "Okay, so…" openers. | Her recorded transcripts (18 Aug, the $70K Reel, 23 Sep and 1 Oct); 13 Oct call 19:38 |
| **Reel set** | A story Reel, a stance Reel, and a b-roll text Reel. | The three Reels share the idea and differ in scene and hook. | The Sep 2026 UVP set (a training story Reel, plus "If I can't tell from looking at your website…"); the May and Jun b-roll trial Reels |
| **B-roll text Reel** | One to three screens. | A strong statement that stands on its own; the caption carries the story. | Knowledge base 09; "You can't book clients who never find you." (1 May) |
| **Cover** | A short statement. | Distinct within the pack and the week's grid. Most covers don't start with "Why". CAPS emphasis is allowed ("start BEFORE the ads"). | Knowledge base 09; 1 Oct and 29 Jul covers |
| **Caption** | Savannah's framework:<br>1. a hook that differs from the Reel's;<br>2. problems, desires and symptoms in the reader's world, with wedding-specific detail;<br>3. the main point, with the story as proof;<br>4. the transformation;<br>5. the CTA (a DM keyword, follow or save). CONVERT captions name the offer. | **Length and register:** 150 to 300 words, clean and declarative.<br>**Sign-off:** "-Whitney" on first-person captions.<br>**Constructions:** at most one "it's not X, it's Y"; no staccato chains; no aphoristic kickers. | Knowledge base 09 and 17; the 25 Jun and 1 Oct approved captions; her repeated "Does this follow Savannah's framework?" |
| **Carousel** | 9 to 12 slides, in order:<br>1. slide 1: an insight or curiosity about the reader, different from the Reel and email hooks;<br>2. the story, over two to four slides;<br>3. the reader's situation and the reframe;<br>4. a belief slide ("We believe…");<br>5. a CTA slide for both DIY and done-for-you readers. | Real text on every slide; "we" and "us" throughout; stacked short lines and bold key lines are allowed on slides. | The 4 Aug ($22K) and 13 Aug (10-week) approved carousels, and her 10 Jun draft; knowledge base 09 |
| **Across the pack** | One idea, entered through different doors. | **Repetition:** repeat ideas, not language.<br>**CTA:** one offer CTA a week on Instagram.<br>**Offers:** named with approved descriptors ("ELEVATE, our full-service advertising management program").<br>**Positioning:** against "most agencies" is allowed; against the reader, never.<br>**Ads and offers:** never presented as frustrating. | Knowledge base 14 and 17; the 10 Jun caption; 13 May ("That hook speaks to someone who's in a place of desperation") |

### 14.10 Second blind review (after the tone and format rewrite)

**Setup.** A separate agent first read eight of Whitney's finished pieces verbatim:
- her 10 June, 29 June and 15 September emails;
- her 25 June caption;
- her recorded 18 August Reel;
- her approved $22K and 10-week carousels;
- her approved 1 October caption.

It also read knowledge base 09 and 17, her 13 October call, and her rewrite tab. It then judged three unlabeled sets of packs, without being told which was newer:
- X: the post-tone-review packs;
- Y: the 20 October packs;
- Z: the v2 packs before the tone review.

**Ranking:** X first, Z close behind, Y last.

| Pack | Point | Reframe | Audience | Offers | Tone | No AI tells | Format | Hooks | Predicted decision |
|---|---|---|---|---|---|---|---|---|---|
| X1 Budget | 4 | 4 | 4 | 4 | 4 | 3 | 4 | 3 | Light edits |
| X2 Strategy calls | 5 | 4 | 5 | 4 | 4 | 3 | 4 | 2 | Light edits to the body; rewrite the hooks |
| X3 AI / Accelerators | 4 | 4 | 4 | 5 | 4 | 3 | 4 | 4 | Light edits |
| Y1 Meta literal | 3 | 2 | 3 | 2 | 3 | 2 | 3 | 3 | Rewrite (borderline reject) |
| Y2 Office hours | 4 | 3 | 2 | 4 | 3 | 2 | 3 | 2 | Reject as framed |
| Y3 When more inquiries aren't enough | 5 | 4 | 4 | 5 | 4 | 3 | 4 | 5 | Light edits (best single pack: her own subject and slide-1 wording) |
| Z1 Budget | 4 | 4 | 4 | 2 | 4 | 3 | 2 | 4 | Light edits |
| Z2 Sundays | 5 | 4 | 3 | 3 | 4 | 3 | 2 | 3 | Rewrite the hooks |
| Z3 AI / Accelerators | 4 | 4 | 4 | 4 | 4 | 4 | 2 | 4 | Light edits |

**Why X won.** On the same three stories, X follows what Whitney explicitly asked for:
- her angle-tab format and titles;
- the brief;
- email send metadata;
- offers named the way her finals name them;
- the Accelerators link CTA her 15 September email uses.

**What it still found, and what was fixed.** The review produced a 29-item list. Each item was checked against the transcripts and her pieces before it was applied.

1. **Her own wording wasn't used where she had given it.** Pack 2's subject was about the process, not the problem, and slide 1 led with good news. Both broke her 13 October notes (12:50 to 13:11, 22:00 to 23:22). The 20 October pack had got this right. → The subject is now "When more inquiries aren't enough", and slide 1 uses her words. **System lesson:** feedback captured at a gate should become locked text for every later draft (W8, RR-46). The rewrite lost it.
2. **"Follow along" CTAs** appeared about 13 times, and never appear in her finals. → Removed. ATTRACT and WARM pieces now end on the principle or with no CTA, plus a DM "ADS" variant for a CONVERT week. **System lesson:** the CTA catalogue (knowledge base 10) should hold her real closing patterns and exclude ones she never uses.
3. **Repetition across siblings:** the same hook in four formats in Pack 3, the same build list in six Pack 2 pieces, and identical caption and slide openers. → Each format now has its own hook and carries one detail. **System lesson:** the sibling-overlap check (rec 24) must also cover lists of details, not only sentences.
4. **Outcome lines the evidence doesn't support:** "couples were falling for the place", "she has a clear picture…", "he'll know where to look". → Replaced with statements of what was built or planned.
5. **Small factual drifts:**
   - "it brought her four good leads" credited her AI, when the campaign brought them;
   - "helping them launch" understated that WIA does the launch;
   - "Google can start to assume" lost Whitney's "sometimes";
   - "wasn't working at all" overstated "no tracked leads".

   → All fixed. **System lesson:** add these to the hook and claim fidelity check (rec 24), comparing verbs and hedges against the ledger.
6. **DIY drift in stance Reels:** "Before you raise your ad budget, ask…", and "questions your ads partner should be asking you… bring them to your next call". → Both were reframed as WIA's own practice ("When a new client comes to us…", "Questions we ask on our strategy calls…"). **System lesson:** the takeaway test (rec 16) applies to every asset, not only the angle.
7. **A client's weak spot was published three times** (no separate indoor ceremony space). → Reframed as couples' worry about the rain plan, and checked against her own words ("leaning into our backup plan to make people feel secured").
8. **Thin carousel captions** skipped Savannah's problems, desires and symptoms. → Expanded to 150 to 250 words, with the reader's situation first.
9. **Smaller fixes:**
   - British spellings changed to American;
   - "dabbling" changed to "tinkering";
   - a filler transition slide merged;
   - prospect details trimmed to the essentials;
   - "a test Carmen had suggested" dropped from a sales piece;
   - personal reaction lines added to the scripts, flagged for Whitney to keep or cut.

**Not adopted:**
- **"A question we ask every new client: how do you feel about what you're spending?"** It's unevidenced: our team asked this one client.
- **Invented recipient segments.** The copy keeps "confirm segment".

**What the review said still separates the packs from her finals** (true before the fixes, and only partly addressed by them):
- more mechanism and less feeling: her pieces land on how the business feels ("breathing room", "autopilot");
- fewer personal beats ("I felt that in my bones");
- a cadence too uniformly polished in the scripts.

These are the hardest things to automate. They're the main reason a Gate 2 voice pass stays human (14.5).

**The fixes haven't been re-reviewed.** Whitney's review is still the real test.

**Carried into the implementation plan.** Revision 7.3 of `backend/docs/Content-Atelier-Implementation-Plan-Brief-Generation.md` (section 1.11) combines sections 9 and 14 into one quality track. It numbers this review's system lessons as recommendations 34 to 38, and adds recommendation 39: a weekly review document in the layout WIA reviews. It also adds the pack standard (plan section 2.4b, from 14.9) and decisions D28 to D34.
