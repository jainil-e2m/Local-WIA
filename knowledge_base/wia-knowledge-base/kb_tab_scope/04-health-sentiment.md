# Tab 4 — Health & Sentiment

**Status:** Draft · H2–H5 decided 22 Oct 2026 · v2 mockup layout added (under review) · Stage 3
**Labels:** **[Agreed]** = already decided (KB-CH-35, KB-CH-42, FR-HEA). **[Proposed]** = new in this draft. **[Finding]** = from sources.

---

## 1. What this tab is for

**One question:** *Which clients need care right now, and why?*

It turns scattered signals (what clients say, whether WIA keeps its promises, support problems, lead results, programme participation) into an **explainable** picture per client. Every flag shows its reasons and the evidence behind them. Agreed boundaries [KB-CH-42]:
- **Two separate views:** *Engagement* (how the relationship is going) and *Outcomes* (LeadLock lead results). A client can be happy while conversion needs work, or have great results while WIA's promises slip.
- **No combined numeric score**, weighting or percentage.
- **Commercial context is not a health signal** (and finance is admins-only, F2).
- **Missing data is "Unassessed", never "healthy".**

---

## 2. How WIA tracks client health today [Finding]

| Signal | How it arrives today | Source |
|---|---|---|
| Client says they're happy / unhappy | Email or a call, mostly to Whitney ("pretty much everything does go through me") | Sep 22, 36:44–38:04 |
| Feedback surveys at different stages | Exist; where they're stored is unknown (GHL survey reads scope-denied) | Sep 22, 36:44; KB-V-01 |
| Lead volume, cost per lead, ad leads turning into **booked clients in LeadLock** | Whitney looks when she can | Sep 22, 36:44 |
| Ad problems ("zero leads in 3 days, here's why") | **Viktor**, proactively. "WIA's only behind-the-scenes client-health signal today" | viktor_at_wia.md 3.2 |
| **Monday green / yellow / red snapshot** of every client (last 30 vs prior 30 days, ad performance) | Viktor, before the Monday Google and Meta meetings. Carmen and Jacqueline take their week's priorities from it | viktor_at_wia.md 3.3 |
| Support problems | LeadLock support form → Danielle (support@leadlockpro.com); a GHL pipeline nobody actively watches | Sep 22, 38:04–39:25 |

Whitney's summary: **"I wouldn't say that there's really a way that we're keeping track of that at this point."** Concerns are handled case by case as they reach her.

**Implication:** the tab shouldn't rebuild Viktor's ad snapshot (paid media is deferred scope). It should add what nobody tracks today: the **relationship and follow-through** side, plus LeadLock outcomes, and sit beside Viktor's ad view in the Monday meetings.

---

## 3. Who uses it

| Person | When | What they need |
|---|---|---|
| **Whitney** | Weekly; before her calls | Which relationships are cooling, why, and what to do. Early warning before a client complains |
| **Carmen, Jacqueline** (Monday ad meetings) | Monday | Relationship context next to Viktor's ad RAG: "account is red on ads, but the client is also waiting 6 days on a page" |
| **Account owner** | Before a call | This client's drivers and the latest client words |
| **Danielle (LeadLock)** | Weekly | LeadLock clients with stalled or uncontacted inquiries |

---

## 4. The dimensions [Agreed list, Proposed definitions]

Each dimension gets its own state and reasons. Proposed states and triggers (WIA to confirm thresholds → **H1**):

| Dimension | What it looks at | States (proposed) | Example drivers | Never infer |
|---|---|---|---|---|
| **Client voice** | Direct client words in email, Slack, calls; survey answers once found | Positive · Mixed · Concern raised · No recent signal | "Sarah asked about inquiry quality (Oct 8)"; "Dana: 'This sounds much more like us now'" | Silence ≠ unhappy. A Viktor post ≠ client words |
| **Follow-through** | WIA's commitments to this client: overdue, unacknowledged, missed rhythm, **client messages waiting on a WIA reply** | On track · Slipping · Broken promise | "Landing page promised Oct 8, not sent"; "Client email unanswered 3 business days" | Unknown deadline ≠ overdue |
| **Support** | Open issues, age, repeats, resolution | None open · Open · Repeat / ageing issue · Coverage unknown | "Tour link timezone bug, 2nd time in 30 days" | No tickets seen ≠ no problems |
| **Onboarding** (onboarding clients only) | Phase, blocked milestones, client inputs outstanding | On schedule · Waiting on client · Stalled | "CRM confirmation outstanding 9 days" | Slow client ≠ unhappy client |
| **Programme** (accelerators only) | Sheet-reported attendance, missed sessions, asks for help | Engaged · Drifting · Unknown | "Missed 2 of last 3 sessions; asked for direction" | Missing transcript ≠ absence |
| **Lead outcomes** (LeadLock clients) | Inquiries, tours/consults booked, bookings, conversion by period | Improving · Steady · Declining · Unavailable | "Inquiries 42 → 31 (last 30 vs prior 30)" | Contacts ≠ leads. Current stage ≠ history |
| **Lead handling** (LeadLock clients) | First-response time, uncontacted inquiries, stalled opportunities | Good · Gaps · Unavailable | "6 inquiries with no contact after 48 h" | `updatedAt` ≠ a contact |

**Attributed context, not a dimension (decided, H3):** Viktor's latest Monday ad rating for the client (green/yellow/red with a link to the post), shown as an *Ads (Viktor)* column. It never changes the KB category.

**Deferred [Agreed]:** commercial context; combined score.

---

## 5. Category (the one-word label on each client)

FR-HEA-01 asks for category filters. **Decided (H2): worst-signal rule**, always naming its cause:

| Category | Rule (proposed) |
|---|---|
| **Needs attention** | Any dimension in its worst state (Concern raised, Broken promise, Repeat issue, Stalled, Declining) |
| **Watch** | Any dimension in its middle state (Mixed, Slipping, Open, Waiting on client, Drifting, Gaps) |
| **Steady** | All assessed dimensions fine |
| **Settling in** | Client in onboarding (first ~60 days), unless something is in its worst state |
| **Unassessed** | Not enough coverage to judge (e.g. no client message or meeting in 45 days and no other signals) |

It's a **worst-signal rule, not a score**: the category always names the dimension(s) that caused it, so "why" is one click away. Lead outcomes are **not** part of the category: they're shown in their own view, because Engagement and Outcomes are agreed to be separate.

---

## 6. Tab structure

### Global tab: 5 sub-views
| # | Sub-view | Question |
|---|---|---|
| A | **Overview** (landing) | Who needs care, and what changed? |
| B | **Health grid** | All clients × all dimensions at a glance |
| C | **Engagement** | Per-client explanation with evidence |
| D | **Lead outcomes** | How are LeadLock clients' inquiries converting? |
| E | **Client voice** | Everything clients have actually said, positive and negative |

### A. Overview
| Component | Content | Status |
|---|---|---|
| **Category tiles** (filters) | Needs attention · Watch · Steady · Settling in · Unassessed | Agreed concept |
| **Changed this week** | "Bloom Manor: Steady → Needs attention: promise missed (Oct 8) + new concern (Oct 8)" | Proposed |
| **Needs attention list** | Client, category, top 2 drivers, latest client quote, suggested next step, owner, link to record | Agreed content |
| **Monday review** | One list for the Monday meetings: relationship category beside *Ads (Viktor)* rating; export/post to Slack (reuses review-before-send) | Proposed (H3, H4) |
| Freshness and coverage | "Assessed Mon 9:00 · Gmail, Slack, Fathom, ClickUp current · LeadLock unavailable" | Agreed |

### B. Health grid [Decided, H4]
Rows = clients; columns = Client voice · Follow-through · Support · Onboarding/Programme · Lead outcomes · Lead handling · *Ads (Viktor)*. Each cell is a coloured state chip; **grey = not applicable, hatched = unavailable**. Click a cell → its drivers and evidence. Sort by category; filter by owner/engagement. Shows at a glance where problems cluster (e.g. follow-through slipping across Jacqueline's clients = workload, not clients).

### C. Engagement (per-client cards)
| Component | Content | Status |
|---|---|---|
| Category + period | "Needs attention · assessed 9 Oct · last 30 days" | Agreed |
| **Why** | AI summary in 2 sentences, each claim cited. **Auto-published, labelled "AI-written"** (H5) | Agreed content |
| **Drivers** | Per dimension: state + the facts behind it, each linked to evidence; marked *fact* (code-calculated) or *interpretation* (AI) | Agreed |
| **Client's own words** | 1–2 most recent direct quotes, speaker and date verified (not staff text) | Agreed (mock bug: strips speaker prefix) |
| **Suggested next step** | Labelled proposal, e.g. "Personal check-in before the Oct 9 call". Buttons: *Add as action* (goes to register as proposal) · *Notify owner on Slack* | Agreed: proposals never auto-create work |
| **Trend** | Category history over the last 8 weeks (small strip) | Proposed |
| Coverage | What this assessment couldn't see | Agreed |

### D. Lead outcomes (LeadLock clients only)
| Component | Content | Status |
|---|---|---|
| Per client | Inquiries · tours/consults booked · bookings · inquiry→tour and tour→booking rates; last 30 vs prior 30 days | Agreed |
| Lead handling | Median first response · uncontacted after 48 h · opportunities stalled > 14 days | Agreed |
| Definitions panel | What counts as inquiry/tour/booked for this client, period, timezone, exclusions | Agreed: required before showing numbers |
| Unavailable state | "LeadLock access pending for this location" with what's needed | Agreed |
| Not in scope | Ad attribution ("leads from ads") unless the source field is reliable [Agreed]; ad spend/CPL (paid media deferred) | — |

### E. Client voice [Decided, H4]
A feed of every direct client statement the KB has classified: **praise · concern · question · request · decision**, with speaker, date, channel and link. Filters by client, type, period. Includes survey answers once located. Use: spot a cooling tone early; and praise is visible (testimonial reuse stays out of scope).

### Client record → Health (new sub-tab) [Decided, H4]
Same as the client's Engagement card + Lead outcomes + Client voice feed for that client + category history. The record's Now tab shows only the category chip and top driver with a link. Today the mock shows a "relationship signal" panel on Now with fictional sentiment; that would be replaced.

---

## 7. How assessments are produced

| Step | Who/what | Proposed timing |
|---|---|---|
| Dimension states | **Code**, from defined rules (overdue counts, response times, issue age, attendance rows, LeadLock counts) | On every relevant change (≤15 min) |
| Client voice classification | AI, per new client message/transcript segment; each quote kept verbatim | As messages arrive |
| "Why" summary + suggested step | AI draft from the drivers only | Weekly (Monday 7:00, before the meetings) + when a category worsens |
| Publication | **Auto-published, labelled as AI-written, every claim cited (H5).** Owners can flag a wrong summary; the flag goes to review and the summary is regenerated | Immediate |
| Alert | Category worsens to *Needs attention* → owner + Whitney, in-app; Slack optional (review-before-send) | On change |

Versioned prompts and evaluated changes [Agreed, Q19]. Existing Viktor posts are attributed analysis, never client testimony [Agreed].

---

## 8. Rules that protect against false alarms [Agreed]

- Silence, missed sessions or a slow reply from the **client** are not dissatisfaction by themselves.
- Unknown deadline ≠ overdue; RSVP ≠ attendance; missing transcript ≠ absence.
- Unreadable source → **Unavailable**, and if too much is unavailable → **Unassessed**.
- Staff or Viktor statements are never shown as client quotes.
- Health never uses payment status (commercial context deferred; finance admin-only).

---

## 9. Who can see it

All team members with access to the client [Agreed: client/module permissions]. Lead outcome numbers follow the same client permissions. No finance data appears here.

---

## 10. Possible additions

| Addition | Value | Dependency | Suggest |
|---|---|---|---|
| **"Waiting on us"** signal (client messages without a WIA reply after 1 business day) | The most direct relationship risk WIA controls | Gmail/Slack reply detection | **First version (H4)**; part of Follow-through |
| **Monday review** page/Slack post | Fits the existing Monday meetings; adds relationship context to Viktor's ad RAG | H3 | **First version (H4)** |
| **Health grid** | Spots patterns across owners | Dimension states | **First version (H4)** |
| **Category change alerts** | Early warning | Slack (D8) | Medium |
| **Category history / trend** | "Is it getting better?" | Weekly snapshots stored | Medium |
| **Escalation log** | Record of serious concerns and how they were resolved | Manual entry + Support | Medium |
| **Survey results** | Direct satisfaction signal | Locate surveys; GHL survey scopes (KB-V-01) | When found |
| **Save-the-account playbook** (checklist when Needs attention) | Consistent response | WIA to define steps | Later |
| **Renewal risk** | Combines health with contract end | Commercial context deferred [Agreed] | Later, admin-only |
| Testimonial candidates from praise | Marketing reuse | Out of scope [Agreed] | Out |
| Ad performance RAG built by the KB | Replaces Viktor's | Paid media deferred | Out |

---

## 11. Current mockup vs this scope

| Mockup today | Problem |
|---|---|
| Three fictional categories (On track / Needs attention / Settling in) with no rule | No drivers; no Unassessed; category not explainable |
| "How the relationship feels" sentiment line per client | Interpretation shown as fact, no evidence per claim |
| Quote found by stripping any speaker prefix | Can show staff words as client words |
| No dimensions, no lead outcomes, no coverage | Agreed scope not represented |
| Portfolio and record show "Health · Coming soon" (P1) | Consistent until this tab is built |

---

## 12. Data readiness

| Dimension | Ready? | Note |
|---|---|---|
| Client voice | **Yes** (Gmail, Slack, Fathom samples) | Classification quality to be evaluated |
| Follow-through | **Yes** (Action Register) | Reply detection needs building |
| Support | **Partial** | Gmail/Slack only; LeadLock support inbox/pipeline unverified (KB-V-02) |
| Onboarding | **Yes** (ClickUp phases) | Phase mapping needed |
| Programme | **Partial** | Two attendance sheets read; rules undefined |
| Lead outcomes / handling | **No** | LeadLock client sub-account reads scope-denied (KB-V-03). Ask alongside the F1 GHL request |
| Surveys | **No** | Location unknown; GHL survey reads denied (KB-V-01) |
| Ads (Viktor) | **Yes** for existing posts | Attributed only; Monday RAG format to confirm |

---

## 13. Decisions

| # | Decision | Outcome |
|---|---|---|
| H1 | Dimension thresholds | Open. Proposed defaults: Slipping = WIA item overdue > 3 days or unacknowledged > 1 day; "waiting on us" > 1 business day; Unassessed = no client message or meeting in 45 days |
| H2 | How the one-word category is set | **Worst-signal rule**, always naming its cause. No score. Lead outcomes stay out of the category |
| H3 | Viktor's Monday ad RAG | **Attributed *Ads (Viktor)* column** with a link to the post. Context only, never changes the category |
| H4 | First-version components | **Health grid · Monday review · "Waiting on us" · Client voice feed · Client Health sub-tab** (all) |
| H5 | Publishing the "why" summary | **Auto-published, labelled AI-written**, every claim cited. Owners can flag a wrong summary for review |
| H6 | LeadLock client sub-account access | Open. Recommended: bundle into the F1 GHL access request |

---

## 14. Mockup coverage (26 Oct)

Mockup: `frontend/exports/client-portfolio.html#health`. Built from `src/views/Health.tsx`, `Health.css` and the sample assessments in `src/health.ts`. Categories are **computed by the worst-signal rule** from the dimension states, not typed in.

**v2 layout under review (`#health-v2`, `src/views/HealthRevised.tsx`, `src/health-v2.ts`).** One page answering *"whose move is it?"*. Two measures are kept separate and never combined (KB-CH-42): **mood**, an LLM reading of the client's own words on five steps (Frustrated … Warm), and **delivery**, facts about WIA's side (on track, slipping, broken promise). Where they meet gives the zone; last week's position gives the movement. Includes a relationship map and tabs for This week, Our side, Client voice (fixed topics so themes stay comparable), Movement, Lead results and the Monday review. Not yet a decision: choosing v1 or v2, and the mood scale itself, are open. The table below describes v1.

| In the mockup | Not in the mockup yet |
|---|---|
| **Overview:** five category tiles (Needs attention 3, Watch 1, Settling in 1, Steady 1, Unassessed 0); changed this week with reasons; waiting on us (Willow 4 business days, Bloom 1); needs attention list with cause, next step, owner; Monday review table (KB category beside *Ads (Viktor)*) with Post to Slack review screen | Real Slack posting; Unassessed sample client |
| **Health grid:** clients × 7 dimensions + Ads (Viktor); fine / slipping / worst / unavailable (hatched) / not applicable; click a cell for its drivers (fact vs interpretation, with evidence) | Filter by owner |
| **Engagement:** category filter; card per client with category + cause, AI-written "why" (labelled, Flag as wrong), dimension blocks with drivers, client quotes (verified speaker), Viktor line, suggested next step (Add as action, Notify owner), 8-week trend, coverage | Real regeneration after a flag |
| **Lead outcomes:** Rosewood numbers (as if H6 access granted): inquiries, tours, bookings, two conversion rates vs prior period, lead handling (first response, uncontacted, stalled), definitions; Harbor shows *Unavailable* | Period picker; more LeadLock clients |
| **Client voice:** feed filtered by type and client; direct statements only | Survey answers (source unknown) |
| **Client record:** new *Health* sub-tab (trend, card, lead outcomes, voice); record header and portfolio cards show the category instead of "Coming soon" | Category filter/sort on the portfolio |

**Note on P1 (Client Portfolio):** P1 said the card badge reads *Coming soon* until Stage 3. The mockup now shows the whole product including Stage 3, so the badge shows the category. In a release where Health isn't switched on yet, it would still read *Coming soon*.
