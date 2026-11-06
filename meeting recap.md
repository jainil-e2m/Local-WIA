# Wedding Industry Ads × E2M — Meeting Recap

**Engagement:** 3-week AI & automation assessment → blueprint
**Calls covered:** 26 August 2026 (44 min) · 2 September 2026 (48 min)
**Next:** Blueprint review — proposed Thursday 10 September, same time (Whitney had a Wednesday conflict; fallback Friday morning)
**Prepared:** 7 September 2026

**Attendees.** Client: Whitney Hodges (founder), Gisselle Jimenez (ops/EA). E2M: Minu Bhatt (AI adoption specialist), Jainil (AI engineer), Asha Kumar (account).

---

## Call 1 — 26 August

Focused discovery on two items only, both from Gisselle's task audit:

- **Roll call / office-hours attendance (row 13).** Walked through the Google Sheets tracker live. Two Thursday sessions — Google Ads (Carmen) and Meta Ads (Jacqueline). Manual row duplication per week, manual date entry, manual 2-week and 4-week miss flags. Two prior automation attempts had failed: a Zapier/Sheets reminder chain, and a ClickUp recurring-task loop that broke on "complete a task, now create the next one."
- **Gmail workflow (row 4).** Full walkthrough of the coloured-superstar taxonomy, the per-client label system, the `waiting` tag, and the Monday review. ~5–10 emails drafted daily. Reply SLA is 24–48 business hours.

**Whitney's own framing, which is the real brief:** she had already browsed E2M's AI library and come away with a list rather than a system — *"I don't even know what we should be starting with"* and *"how is it all connected?"* She also raised, unprompted, a much larger scope that appears nowhere in the audit sheet: creative briefs, first-draft ad copy, first-draft landing pages, landing-page QA, and turning client call recordings into reels, carousels, email and case studies. Her stated priority: *"we need more leads. We need more sales."*

**Constraints she set:** nothing AI-generated reaches a client unreviewed; approval must not sprawl across many tabs. She granted broad process-change latitude — *"I am not tied to the labeling system at all."*

Ran over time. Several high/medium priority rows were never reached.

---

## Call 2 — 2 September

Covered invoices, portal reminder posts, and a long walkthrough of onboarding. Also surfaced several facts that **correct assumptions carried out of call 1.**

### Material corrections

1. **Contracts are in Dubsado, not GoHighLevel.** Public proposals → client accepts → Dubsado generates the agreement and first invoice → **signed/paid alerts land in the Gmail inbox.** That Gmail alert is the real onboarding trigger. They are mid-migration off Dubsado into GHL, complete for one offer only (Foolproof Follow-Up Advantage). Build the trigger on the Gmail notification so it survives the migration.
2. **ClickUp is not where the team works.** Whitney: *"the team has never fully adopted ClickUp other than to just check off the tasks... part of that's probably on me, it's just not how my brain works."* Slack is the operational surface — she proactively offered access to Slack **and every client channel**. Any accountability/chase agent must operate in Slack, with ClickUp as the record, not the interface.
3. **Whitney does not use Fathom.** She uses Zoom's native recording and transcripts, and since an account manager left she now runs **all** client onboarding and strategy calls. Gisselle, Jacqueline, Carmen and Danielle have Fathom, but *"probably free accounts"* on individual work emails — likely no API. The highest-value transcripts are therefore in Zoom. She is open to a Fathom Team account.
4. **Monthly reporting is a major unlogged pain.** Tina spends *the first few business days of every month* on it — ad-account screenshots, best-performing-ad screenshots, hand-written "why" context, plus a recorded video walkthrough. *"Not automated in any way right now."* Whitney has already picked the solution shape: she has been trialling **"Victor" in their Slack** (connects LeadLog + Google Ads + Meta Ads) and wants a plain-language **executive summary**, not a screenshot dump — *"I think I saw that in your AI library."*

### Also new

- **Fulfilment AI already exists in prototype.** Gisselle creates a **ChatGPT Project per client** (a Project, not a custom GPT). Knowledge base = onboarding questionnaire + messaging-and-positioning interview transcript. Already drafting Meta ad strategy, Google ad strategy, landing page copy. Runs on the shared `hello@` login, **not** a team/org account. Whitney: *"a band-aid solution"*, *"not a long-term solution."* Minu named the failure mode — the knowledge base goes stale a couple of months in. Reframes the fulfilment workstream as **productionising an existing prototype**, not greenfield build.
- **Team roster, one owner per function** (so ClickUp auto-assignment is a deterministic lookup): Carmen = Google Ads; Jacqueline = Meta Ads; Ivy = ads creative design; Tina = LeadLog/GHL design + monthly reports; Danielle = LeadLog/GHL implementation (kickoff calls, workflows, DNS, A2P); Whitney = all client calls; Gisselle = all admin. Whitney: *"it is just one person with set responsibilities."*
- **Onboarding runs as two parallel tracks** — Ads (Whitney → Carmen → Jacqueline) and LeadLog (Danielle → Tina) — with a **cross-track sync dependency at the end**: LeadLog goes live → someone must tell Carmen and Jacqueline → switch campaign URLs to the new approved landing page. That handoff is exactly the kind that silently drops, and it is why onboarding *"never feels like it's actually going smoothly."* Many client-side review/approve/launch loops along the way, each able to stall.
- **Do not automate ad-account access collection.** It happens by Whitney screen-sharing and taking remote control on the kickoff call. They have tried every other way; clients are too tech-challenged.
- **GHL plan confirmed:** Agency SaaS, ~$500/mo, top tier — API access expected.
- **Invoice loop detail.** GHL's automated dues land in spam/promotions, so the effective step is a **personal email from `hello@` with the invoice link pasted in** — *"usually that's the push people need."* Link is grabbable via "copy link" in GHL. So the automation should draft that nudge, not merely flag.
- **Change appetite reconfirmed:** *"it's not going to hurt my feelings if you say that we need to [change]... everything with this business has just been us figuring it out as we go."* Human-in-the-loop remains absolute: *"if it's going out to the end client, we definitely want someone to review it."*

### Access mechanism agreed

Client creates `AI@weddingindustryads.com`, credentials shared via **LastPass to Minu**, who distributes. Accesses to map: **ClickUp, GHL, Members Portal, Slack + all client channels.**

---

## Audit row 12 — "Uploading sessions to our member's portal and creating a recap post"

> Gisselle · Operations/Admin/Internal · ~0.5 hr × 12/mo · Manual · HighLevel + Canva · Priority: Med
> *"Download recording from team members + recap summaries. Create canva banner with the session's date. Upload to member's portal. Create post with recap recording and summary in member's portal."*

### What was actually discussed: almost nothing

- **Call 1: zero coverage.** The row never came up. The portal itself got a tour — Whitney: *"it's basically built inside our high level, which is LeadLog... if you go to communities, you can open it up there"* — and Minu said at 23:23 he wanted to *"touch upon a couple of other high to medium priority tasks,"* then went to email and ran out of time.
- **Call 2: raised and dropped mid-sentence.** At 17:02 Minu said: *"And it's like one hour before every event. And then there's just like the recap posts, which I'm not sure if I..."* — the next turn pivoted to whether GHL can schedule posts in advance, and the thread never returned.

**So this ~6 hr/month item is heading into the blueprint on one aborted sentence of discovery.**

### What the calls did give us

- **Portal = GHL Communities**, inside the LeadLog white-label. Separate channels per accelerator, plus an Announcements channel.
- **Event roster:** Google Ads OH Thursday 11am CST → Google Search Accelerator channel; Meta Ads OH Thursday PM → Meta Ads Accelerator channel; **Q&A and Workshop every other week → Announcements.** ~12–13 sessions/month, matching the sheet's 12.
- **Scheduling evidence.** Gisselle: *"Actually, we can... I was able to schedule it and publish it"* — once, in April, via Social Planner. Caveats: *"there were some limitations, like tagging people or tagging the event"* and *"I'm not sure now... I haven't tried it."*
- **Minu's approach:** get `AI@weddingindustryads.com` added to the portal, *"check if there's any inbuilt features we can leverage. We don't need to over-engineer it."*
- **Free upstream input, from call 1:** *"after the meeting is hold, then our team members send like a recap in Slack. With a report and a summary."* For Carmen's and Jacqueline's office hours a human-written recap **already exists in Slack** — a better input than a raw transcript for that subset.

### Reframe: the recording is an input, the content is the deliverable

The recording already exists (Zoom/Fathom). The work is generating the recap content *from the session* and publishing it alongside the recording. Two things go beyond "just content", both visible in the live portal posts:

**1. It is a dual publish, not one post.** Every post closes with *"This recording has also been added to the Audit & Adapt lessons here in The VAULT."* That VAULT lesson needs its own deliverables:

- A rewritten "ABOUT THIS LESSON" description — same substance as the post, different register
- **Taxonomy placement** — e.g. Audit & Adapt → *Five Foundations for Success with Ads* → lesson 5 of 8
- **Extracted structured data** — one lesson lists "Landing Pages Featured:" with 7 named client pages and links (Dos Palomas Ranch, Ridgefield Weddings & Events, Davis & Grey Farms, Diamond A Ranch, Funktastic Productions, DJ Hybrid Chicago, Sandy River Getaway)
- A custom title card image

**The VAULT step is not in the sheet description at all** — row 12 only says "upload to member's portal, create post." The logged 0.5 hr is therefore probably light.

**2. The Canva banner is a real asset, not free.** The title cards carry the workshop title, the subtitle hook, "PRESENTED BY WHITNEY HODGES" and the logo. Generatable via Canva's Connect API autofill from a brand template — but it is a build step.

### The post template reverse-engineers cleanly

| Slot | Pattern |
|---|---|
| Title | `Whitney's {Cadence} Workshop Recording: {Topic}` + ` - Guest Training with {Guest}` |
| Hook | `@everyone Here's the recording from {today's} {workshop or guest training} with @{Presenter}!` |
| Body | `{Presenter} covered {thesis}` + a tricolon of specific takeaways |
| Cross-ref | "also been added to the **Audit & Adapt** lessons here in The VAULT" (± deep link) |
| Optional | `Resources from {Guest}:` — bulleted links, each with a dash-description |
| Closer | "Check it out below!" + embedded video |

The body copy is unambiguously transcript-derived — *"the three layers of research,"* *"a simple survey framework,"* *"a sneak peek of actual conversion rates for each page,"* *"how they vary between Google Ads, Meta Ads, or both."* None of it comes from a title. That is LLM-shaped work, and it is the bulk of the 30 minutes.

### Feasibility — split the row rather than scoring it once

| Component | Score | Note |
|---|---|---|
| Recap post copy + VAULT description + featured-link extraction | **9/10** | Transcript → template. Feasible regardless of any API question |
| Canva title card | **8/10** | Canva Connect API autofill from a brand template |
| Publishing into Communities | **unverified** | Not "no write API" — nobody has checked yet |

**On "Members Portal has no write API" — mark this unverified, not blocked.** Against it: Gisselle actually published a scheduled post in April, and they are on GHL's top Agency SaaS tier. For it: Social Planner may be a different surface from Communities group posts, GHL's v2 API coverage on Communities has historically been thinner than contacts/invoices, and she never retested. The resolution path is exactly Minu's plan and it has not run yet. Fallbacks if it is closed: native Social Planner scheduling, or browser automation on the `AI@` account once it is a portal member.

**The crux nobody asked about:** every post uses `@everyone`, two use `@{presenter}`, and three link to VAULT lessons — precisely the features Gisselle flagged as limited (*"tagging people or tagging the event"*). Realistic outcome is partial: plain copy plus video posts fine, mentions and internal links may need a human. Even then ~80% of the time is recovered, because pasting finished copy is ~2 minutes.

### Two things worth raising at the blueprint

- **Every one of the four sampled posts has 0 likes and 0 comments, in a 20-member group.** Same retention problem as the roll-call flags — posting faster does not fix it. A *better* recap (timestamps, the named client examples surfaced in the post rather than buried in the lesson) plausibly might. Frame this as an engagement opportunity, not only a time saving.
- **The cadence label has drifted three ways** — "Monthly Workshop" (1mo ago), "Bi-Monthly Workshop" (2mo and 3mo ago), and Gisselle described it on the call as *every other week*. Also "this week's" vs "today's", and the presenter is @mentioned in two posts but plain text in a third. A templated cadence variable cleans all of this up — cheap, and visible to members.

### Question to close

**Do the two weekly office hours get the full post + VAULT lesson treatment, or only the Q&A and Workshops?** The sampled posts are all workshops, but the sheet says *"download recording from team members"* — plural, implying Carmen's and Jacqueline's sessions too. That is the difference between ~4 and ~12 full-treatment sessions a month, and it materially changes the size of this item.

---

## Open items

**Owed by the client**
- Create `AI@weddingindustryads.com`; share credentials via LastPass to Minu
- Grant access: ClickUp, GHL, Members Portal, Slack + all client channels
- Send 2 office-hours transcripts (Minu asked, Gisselle agreed)
- Confirm the blueprint call slot (Thu 10 Sept proposed; Whitney to confirm)

**Owed by E2M**
- Asha's recap email plus the formal requirements/access list
- Blueprint review — must make Tier 1 items *pickable*, since Whitney's homework afterwards is to choose *"a couple of the workflows we should start working on"*
- Verify GHL Communities write capability once portal access lands (gates row 12 publishing, and the reminder-post automation)
- Then: Asha + Whitney 15-min private sync on execution and commercials

**Still unanswered**
- Accelerator cohort sizes / how many clients typically in onboarding at once
- Which existing Gmail automations already tag inbound mail, and their rules
- Whether email templates are authoritative in Drive or in GHL
- Whether a brand-voice/tone document exists, or voice must be inferred from sent mail and recordings

**Noted by Asha:** the assessment was deliberately scoped to *"what major tasks Gisselle was doing."* The blueprint is not final — upgraded quarterly, and expanded as other team members are interviewed. The Tina monthly-reporting find argues for making the delivery-side interviews the immediate next tranche.
