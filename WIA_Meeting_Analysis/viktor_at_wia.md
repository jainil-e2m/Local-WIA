# Viktor at WIA: what the team uses it for

The Slack "AI employee" WIA already runs, and the incumbent the knowledge base and reporting streams have to beat.
Built 2026-09-24 from the M00, M02 and M05 transcripts, WIA's ClickUp snapshot (Sep 8–9) and research on viktor.com.

> **Name.** The product is **Viktor** ([viktor.com](https://viktor.com/)). Fathom writes it as "Victor". Its old domain was getviktor.com, and the Slack listing still links there. **viktor.ai is a different company** (VIKTOR, an engineering app platform). WIA's ClickUp step "Add Viktor.ai" sits under *Create Slack Channel*, so it means this product.

## What Viktor is (researched Sep 24, 2026)
- **An AI agent that lives in Slack** (and Microsoft Teams). One shared agent for the whole workspace, not a per-seat assistant. You @-mention it in a thread or DM it; it runs code in its own cloud sandbox and calls the connected tools.
- **Maker:** ZETA AI, Inc. (US). Founders Fryderyk Wiatrowski (CEO) and Peter Albert (CTO), both ex-Meta AI.
  - Launched **Feb 2026**. Raised a **$75M Series A** led by Accel (May 2026); Slack's cofounders are angels.
  - Fortune (May 2026): 2,000+ organisations, $15M revenue run-rate. The site claims "65,000+ teams".
  - Earlier product: Jace (email agent).
- **Integrations:** "3,200+", of which 27 are native.
  - **Native:** Google Ads, Meta Ads, Google Drive, and others.
  - **Managed connectors:** Gmail, Google Calendar, ClickUp, Instagram, Slack.
  - **Not in the published catalog:** GoHighLevel and Zoom. Viktor says it builds custom integrations from API docs, or uses a browser, which is presumably how WIA's are connected.
- **Memory:** a shared memory of the workspace, built from the channels it's invited to.
  - "Tell him once… he acts on it from then on."
  - **Skills:** written procedures, which can be made from a screen recording.
  - Admins can wipe its memory.
- **Scheduled tasks and crons.** It also proposes recurring tasks itself and leaves them paused until someone approves.
- **Outputs:**
  - Slack replies
  - PDFs and documents
  - **Pages:** a document or dashboard at a link
  - **Spaces:** internal apps it builds and keeps running, with their own login
- **Approval gates:** sending email, modifying campaigns, deploying apps and charging cards all wait for a human to approve.
- **Agency positioning.** Viktor markets exactly WIA's use cases ([AI for Agencies](https://viktor.com/blog/ai-for-agencies)):
  - a weekly client report that pulls Meta, Google, GA4 and a **GoHighLevel** pipeline
  - pre-launch QA (UTMs, forms, GHL routing)
  - a 1-page **client call-prep** brief
  - a weekday 8:30 AM **anomaly check**
  - Meta Ads and Google Ads actions (pause, budgets, audiences, bids)
- **Pricing:**
  - $100 free credits
  - team plans from **$50/mo (20k credits)** up to $50k/mo; Enterprise is custom (SSO, DPA, SLA)
  - priced per workspace, not per seat
  - a quick task is 100–300 credits, a complex workflow 500–1,500
  - reviewers say spend is hard to predict
  - **WIA's plan and spend are unknown**
- **Security:**
  - SOC 2 Type 1 (Type II and ISO 27001 in progress); CASA Tier 3
  - hosted on AWS us-east-1
  - it sees only the channels it's added to, threads it's mentioned in, and its DMs
  - tokens are injected at run time and never shown to the model; no training on customer data
  - **Connections are shared with the whole workspace unless marked personal**
  - SAML SSO is Enterprise only
- **Known weaknesses (public reviews):**
  - verbose ("a five-paragraph answer when a sentence would do")
  - sometimes forgets or assumes context
  - credits burn fast

## How WIA has it set up
**Where it lives.** It's added to **every new client's Slack channel** during onboarding (see §7). Whitney, Carmen and Gisselle also use it in threads and DMs.

**Who set it up.**
- Whitney connected the accounts.
- Gisselle configured the open-loops scan and the ClickUp digest, and adds Viktor to each new client channel.

**What it's connected to** (M05, 33:43–35:08)
| Source | How |
|--------|-----|
| Slack | Every client channel it's added to, plus threads and DMs |
| LeadLock (white-label GHL) | The agency account, **plus added by hand to every client sub-account** WIA manages |
| Meta Ads | **Added by hand to each client ad account** WIA runs ads for |
| Google Ads | Once, through WIA's **manager (MCC) account**, which gives it every account |
| Email and calendar | **Whitney's only.** "We could probably… connect him with everybody else's, we just haven't" |
| ClickUp, Zoom | Connected |
| Fathom | **Not connected** |

GA4, Search Console and Shopify weren't mentioned.

**Who uses it**
- **Whitney:** call prep, Q&A, briefs for Danielle, SOPs
- **Carmen** (Google Ads manager): daily account recaps
- **Gisselle:** digests
- **Carmen and Jacqueline:** the Monday snapshot
- **Danielle:** receives Whitney's briefs, doesn't use it directly

## What WIA uses Viktor for

### 1. Call preparation
**1.1 Daily call prep from Whitney's calendar** (24:11, 31:34)
- Every morning it scans her calendar and briefs her on each call: what's going on with the account and what to focus on. "In theory" it also loops in the last call and its open items.
- It covers **client calls and sales calls**. She keeps chatting with it to dig further.
- *Whitney · scheduled, daily ("I already have him set up")*

**1.2 Gap check before the messaging & positioning interview** (25:32)
- It compares the client's filled-in onboarding questionnaire and website against Whitney's interview questions.
- It reports "what hasn't actually been answered", so the call skips questions WIA can already answer.
- *Whitney · on request*

**1.3 Briefing Danielle before LeadLock kickoffs** (25:32)
- It picks out anything from the sales and onboarding calls that matters for the client's LeadLock build, e.g. which CRM they use now.
- Only "when I remember to"; it isn't automated.
- *Whitney → Danielle · ad hoc*

### 2. Client status and history on demand
**2.1 "How are things going with this client?"** (18:42)
- It answers from live Meta Ads, Google Ads and GHL data, e.g. "how have leads been looking the past few weeks".
- *Whitney · on request*

**2.2 "Where does this stand?" / "Remind me about this situation"** (31:41, 43:54)
- The history is buried in old, long Slack threads, so she pings Viktor for the status instead of searching.
- She's been "leaning into having him… pull like knowledge and history".
- *Whitney · on request*

### 3. Performance monitoring and alerts
**3.1 Opportunities and problems nobody asked about** (18:42, 22:37)
- Examples: "leads have been down on Google the past week… here's what I would recommend", and "conversion tracking is no longer working… here's why".
- It spots things "we wouldn't necessarily have even spotted ourselves". It's "always spewing out… recommendations for every account".
- *proactive*

**3.2 Anomaly alerts** (38:04)
- Example: "this account… got zero leads over the past three days. This… might be why", plus what the team needs to fix.
- **This is WIA's only behind-the-scenes client-health signal today.**
- *proactive*

**3.3 Monday portfolio snapshot** (45:45)
- Before the Monday Google Ads meeting (Whitney + Carmen) and Meta Ads meeting (Whitney, Jacqueline, Carmen, sometimes Ivy), it snapshots **every client**.
- It compares the last 30 days with the 30 before ("I believe"), flags the accounts needing the most attention, and rates each **green / yellow / red**.
- The meetings focus on the reds, and **Carmen and Jacqueline take their week's priorities from it**.
- *weekly. Whether it's a scheduled task or requested each week isn't stated; the RAG "system" seems to be Viktor's own*

### 4. Support for the ads managers
**4.1 Account recaps for Carmen** (22:37)
- When she returns to an account, she asks for "everything… outstanding".
- It goes back through its past suggestions in the chat history and the most recent client calls, and checks the account's current state.
- *Carmen · on request, routinely*

**4.2 Checking that fixes stuck** (22:37)
- As she completes items, it re-checks the account "to make sure that it actually stuck".
- *Carmen · follow-up*

### 5. Team follow-through
**5.1 Daily "open loops"** (31:41)
- It scans Slack for three kinds of loose end:
  - asks to the team with no response
  - asks to Whitney she hasn't answered
  - things agreed that still haven't happened
- The name "open loops" is Viktor's own.
- *Gisselle set it up · scheduled, daily. Whitney finds it helpful*

**5.2 Monday ClickUp digest (effectively dropped)** (33:24–33:34)
- It DM'd Gisselle the incomplete ClickUp tasks every Monday. It was "a lot… even old ClickUp tasks", so **she uses her own ClickUp filter instead**.
- *was weekly*

### 6. Audits, SOPs and QA checks
**6.1 UTM parameters → SOP** (35:24)
- It found WIA was building Google Ads UTM parameters wrongly, explained why and how to change them, and Whitney had it write "a whole SOP… the team could follow".
- *Unconfirmed trace:* the stale v1 onboarding template hard-codes a UTM string (`utm_campaign={campaignid}`…); the live v2 task is blank.
- *one-off*

**6.2 GHL form setup → team resource** (35:54–36:00)
- Same pattern: a problem across all clients, turned into a resource for the team. It has "only happened a couple of times".
- *one-off*

**6.3 Live-page checks in client channels** (ClickUp)
- The LeadLock template's *Add noindex Tag to Funnel Header Code* SOP says to verify by viewing page source, "or post the domain in the client Slack channel and tag @Viktor to check". The fix was confirmed on Ridgefield and The Penny on 8/21/26.
- Whether Viktor wrote that SOP isn't recorded.
- *team · on request*

### 7. Client onboarding
**7.1 Viktor joins every new client's channel** (ClickUp snapshot, Sep 8)
- **"Add Viktor.ai"** is a standard subtask of *Create Slack Channel* in both live onboarding templates: *LeadLock Onboarding* and *Google + Meta Onboarding (version 2)*. It's assigned to WIA Support, role "Assistant".
- From day one it reads what the channel holds:
  - the client folder
  - the onboarding questionnaire
  - the checklists
  - the **sales-call recording and summary**
  - "things to note"
- *every onboarding*

## Not done in Viktor (easy to mix up)
- **Monthly client reports:** still manual (Tina: screenshots, written context, a video walkthrough). In M02 Whitney wanted "something like" Viktor to write an executive summary.
- **The post-interview Q&A document and first drafts** (landing-page copy, ad copy, ad strategy, nurture emails): Gisselle does these in **ChatGPT** Projects (25:32).
- **Dashboards:** she could have Viktor build them but chose not to: "ultimately I want it to be something that we own" (31:41).
- **Changes in ad accounts:** there's no sign it's allowed to make them. The team makes the change and Viktor checks it.

## What WIA says is wrong with it, and whether Viktor itself could fix it
| Complaint (M05) | Fixable inside Viktor? |
|-----------------|------------------------|
| "Very verbose", long replies to sift through | Yes, with instructions. It matches public reviews |
| Recommends needless actions; doesn't know an ads kickoff from a messaging & positioning call | Mostly. She says "I haven't fully trained him"; Viktor supports taught memory and written skills |
| Everything lives in Slack threads; she re-pings it for status | Partly. Pages/Spaces give dashboards, but she declined for ownership reasons |
| Findings aren't escalated or tracked, so fixes wait 1–1.5 weeks | Partly. It can create ClickUp tasks; WIA hasn't set that up. The rest is team capacity |
| The ClickUp digest was noise | Yes, it's configuration |

**Most of the complaints can be fixed inside Viktor.** Whitney's real reason for building with E2M is **ownership**, not capability.

## What this means for E2M
- **The bar is set by what Viktor already does, and ownership is where E2M wins.** Viktor can already do, or be configured to do, most of the knowledge base wish list and the weekly reporting. E2M's case is:
  - **ownership:** memory, data and code stay with WIA if it stops paying
  - **fit to WIA's process:** call-type templates, WIA's own playbook thresholds
  - **one system across the three streams:** e.g. knowledge base history feeding the content engine

  If the build isn't clearly better, the cheap alternative is Whitney training Viktor better ("I could have like trained him better").
- **Correct M00's framing.** On Aug 11 E2M said Viktor "works great at a personal level" but not across a team. It's built and sold as a shared team agent, and WIA uses it that way. Don't repeat that argument.
- **Viktor's outputs are the best spec available** for knowledge base Phase 1 and for reporting. Whitney: "which you might kind of see in Slack". E2M has had all client channels since Sep 21, so collect real samples:
  - call prep
  - the Monday snapshot
  - Carmen's recaps
  - alerts
  - the @Viktor checks

  The ClickUp digest went by DM, and call prep may too, so ask for those. The Blueprint's question to Gisselle ("What is the Viktor Google Ads and Meta Ads reporting like today…") is still unanswered. **Checklist of all 32 samples, with sources and status: [`viktor_samples.md`](viktor_samples.md).**
- **Two agents in the same client channels will confuse the team.** Decide whether to coexist or retire before the knowledge base goes live. Sales-call prep is a natural thing to leave with Viktor: Whitney said it "wouldn't really fall into the client knowledge base".
- **Copy its connector pattern:** the Google MCC once, then Meta and GHL per client account.

## Questions to take to WIA
1. Which Viktor plan, and roughly what monthly credit spend? This is the benchmark for E2M's running-cost estimate.
2. Can we have samples: a call-prep brief, a Monday snapshot, a Carmen recap, and the UTM and GHL-forms SOPs?
3. Is the Monday snapshot scheduled or requested each week? Who set the green/yellow/red rules?
4. Once the knowledge base is live: keep Viktor, narrow it (e.g. to sales-call prep only), or retire it?
5. Are Whitney's email and calendar connections marked personal or shared with the workspace?

## Adoption timeline
| Date | Evidence |
|------|----------|
| Aug 11 (M00) | "I keep seeing ads for this… Victor Slack plugin". Not yet using it. E2M dismissed it |
| Aug 21 → Sep 9 | The noindex SOP (fix confirmed 8/21) tells the team to tag @Viktor |
| Sep 2 (M02) | "I've been playing around with Victor and our Slack", connected to LeadLock, Google and Meta |
| by Sep 8 | "Add Viktor.ai" is a standard step in both live onboarding templates |
| Sep 22 (M05) | Embedded daily for Whitney, Carmen and Gisselle. "It really hasn't been until… we've started engaging with Victor recently" |

**In about a month it went from an ad Whitney kept seeing to a standard onboarding step.**

## Sources
- WIA: M05 transcript (`meetings/2026-09-22_knowledge-base-scoping/source.md`), M02 (33:01), M00 (41:14–42:10); `.clickup-snapshot/` (templates Sep 8, descriptions Sep 9)
- Viktor:
  - [viktor.com](https://viktor.com/), [Product](https://viktor.com/product), [Pricing](https://viktor.com/pricing), [Integrations](https://viktor.com/integrations), [Security](https://viktor.com/security)
  - [AI for Agencies](https://viktor.com/blog/ai-for-agencies), [Media buyers](https://viktor.com/media-lp), [AI Chief of Staff](https://viktor.com/ai-chief-of-staff)
  - [Slack Marketplace listing](https://slack.com/marketplace/A0A2VN5TR5K-viktor)
- Press and reviews:
  - [Fortune, May 19 2026](https://fortune.com/2026/05/19/viktor-ai-startup-raises-75-million-for-virtual-coworker-exclusive/)
  - [ZenML LLMOps entry](https://www.zenml.io/llmops-database/ai-employee-agent-operating-in-slack-with-multi-tool-integration)
  - [eesel review](https://www.eesel.ai/blog/viktor-ai-review)
  - [Lindy review](https://www.lindy.ai/blog/viktor-review) (a competitor)
