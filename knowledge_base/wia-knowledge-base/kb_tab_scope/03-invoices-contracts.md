# Tab 3 — Invoices & Contracts

**Status:** Draft · F1–F4 decided · 22 Oct 2026 · mockup updated 26 Oct · Stage 3 (data backfilled before launch [Agreed])
**Labels:** **[Agreed]** = already decided (KB-CH-04, KB-CH-49…, FR-FIN, FR-CFIN). **[Proposed]** = new in this draft. **[Finding]** = established from sources, changes an assumption.

---

## 1. What this tab is for

**One question:** *What has each client agreed to pay, what have they paid, and is anything late?*

It is WIA's **read-only commercial record**: agreements, how each engagement is billed, invoices, payments and reminders, each traced to its source. It never takes payments, sends invoices or changes anything in Dubsado or GHL [Agreed].

Today this lives in three places: Dubsado (proposals, agreements, first invoice), WIA's GHL account (ongoing invoices and payments) and the hello@ inbox (alerts and personal chase emails). Nobody can see one client's full commercial picture in one place.

---

## 2. How money actually flows at WIA today [Finding]

From the 2 Sep ops call (Gisselle and Whitney, 8:13–13:36 and 23:29–24:09):

| Step | System | Evidence the KB can read |
|---|---|---|
| 1. Sales call → recap email → **proposal** | Dubsado | Recap email in hello@ |
| 2. Proposal accepted → **agreement + first invoice** generated | Dubsado | — |
| 3. Client **signs** and **pays first invoice** | Dubsado | Gmail alerts from `noreply@dubsado.com`: "Tony has signed your contract for GSA - The Promise of 2912"; "…paid 1,400.00 USD" (verified 19 Oct) |
| 4. Signed + paid → onboarding starts | Gmail → Command Center | Same alerts (the onboarding MVP already uses this pair) |
| 5. **Ongoing invoices and recurring payments** | **WIA's own GHL account** ("we have all the payments here in GHL") | GHL invoices/payments. **API reads are currently scope-denied** |
| 6. GHL sends **automatic reminders** when due | GHL | Not in Gmail (sent from GHL) |
| 7. Gisselle filters **overdue invoices** in GHL (aims to do it daily, sometimes forgets) → tells Whitney | GHL + conversation | — |
| 8. **Personal chase email** with the invoice link | hello@ (Gmail) | Readable in Gmail |
| Migration | One offer (Foolproof Follow-Up Advantage) already sells through GHL checkout; the rest are moving off Dubsado over time | Both systems must be handled |

**What this changes:**
- Dubsado emails alone (KB-CH-04) cover **signing and first payments only**. The ongoing ledger is in GHL. Without GHL invoice/payment access, this tab can never show "overdue".
- FIN-V-01 ("what does the GHL pricing information mean?") is largely answered: GHL holds WIA's invoices and payments. The remaining check is the exact record types and whether any client is billed in both systems.
- The LeadLock Pro account does **not** take payments; only WIA's own GHL location does.
- WIA is on GHL's top agency plan, so API access exists once the right scopes are granted.

---

## 3. Who uses it

| Person | When | What they need |
|---|---|---|
| **Gisselle (ops, admin)** | Daily (her current manual GHL check) | What's overdue, since when, whether a chase has gone out |
| **Whitney (admin)** | Weekly; before deciding on a chase | Who owes what; payment history before a sensitive conversation; renewals coming up |
| ~~Account owner~~ | — | **Not a user of this tab (F2: admins only).** Account owners see no finance data anywhere |
| **Onboarding (ops)** | When a deal closes | Signed? Paid? → onboarding can start |

---

## 4. Source authority rules [Agreed + Proposed]

| Fact | Authority | Never from |
|---|---|---|
| Agreement signed | Dubsado signing alert (or GHL contract record for migrated offers) | A call or Slack message |
| Agreement terms (fee, schedule, term, notice) | The agreement document itself, when readable | The alert email (it has no terms) [Agreed] |
| Invoice amount, due date, balance | GHL invoice record (Dubsado invoice for first invoices) | Reminder emails or chase emails |
| Payment received | GHL payment record; Dubsado payment alert | "I've paid" in an email, a reminder disappearing |
| Reminder sent | GHL reminder log (if readable); chase email in hello@ | A draft email |
| Pricing on the public offer | Not a client record | Never used as a contract value |

- **Notification time ≠ transaction time.** Show which one a date is [Agreed].
- **One payment, many emails:** the payment alert, receipt and reply are one payment [Agreed].
- **Conversations never change terms or payment state** [Agreed].
- **Currencies are never added together** without a conversion rule [Agreed].

---

## 5. Two levels of trust, shown per record [Agreed]

| Basis badge | Meaning | Allowed statuses |
|---|---|---|
| **Reconciled** | From the invoice/payment record itself (GHL or Dubsado) | Open · Due soon · Overdue · Partially paid · Paid · Void/refunded |
| **Reported** | From an alert email only | "Payment reported" · "Signed (reported)". **No Open/Overdue claims** |
| **Unknown** | Linked but not readable | "Status unavailable" |

**F1 (decided): GHL is the ledger.** WIA grants invoice, payment and subscription read scopes on their own GHL location; ongoing invoices become *Reconciled*. Dubsado alerts stay the source for signing and first payments (*Reported* until the linked invoice is readable). Until the scopes are granted, the overdue features have nothing to act on.

The tab works in both modes at once. Each invoice shows its basis badge, and totals only include reconciled records, with the excluded count stated ("$12,400 outstanding across 6 reconciled invoices · 2 more not yet reconciled").

---

## 6. Tab structure

### Global tab: 6 sub-views

> **Mockup v2 (26 Oct, layout under review, not yet a decision):** the global tab is condensed to **three** sub-views, one concern each: **Today** (overdue chases, missing invoices, new deals, renewals, unmatched alerts: A + the Coming up list), **Invoices** (the ledger with trust badges plus the timeline of the same events: B + E) and **Clients & contracts** (what each client signed and how they're billed: C + D). The question each sub-view answers below is unchanged.

| # | Sub-view | Question it answers |
|---|---|---|
| A | **Overview** (landing) | What needs attention today? |
| B | **Invoices** | Every invoice, its status and history |
| C | **Agreements** | Who has signed what, on which terms |
| D | **Billing plans** | How each engagement is billed and what's next |
| E | **Activity** | Every commercial event in order |
| F | ~~Needs reconciliation~~ (not a separate view in the first version, F4) | Unmatched items show as an admin-only *Unmatched* tile and list on the Overview instead (see §6F) |

### A. Overview
| Component | Content | Status |
|---|---|---|
| **Summary tiles** (clickable filters) | Overdue (count, amount, oldest days) · Due in next 7 days · Payments received this month · Signed this month · Chases sent this month · Needs reconciliation | Proposed |
| **Overdue list** | Client, invoice, amount, days overdue, last reminder (auto/personal), chase status, **Chase…** button (§7.2) | Proposed. Replaces Gisselle's manual daily GHL filter |
| **New this week** | Signed agreements and first payments, with "Onboarding started?" link to the onboarding flow | Proposed |
| **Coming up** | Invoices due soon; agreements ending or renewing in 60 days | Proposed (renewals need readable terms) |
| Freshness | "GHL synced 9:42 · Gmail 9:38" | Agreed |

### B. Invoices
| Field | Notes |
|---|---|
| Invoice ID + link | Opens in GHL/Dubsado |
| Client · engagement | Reviewed mapping [Agreed]. "Tony / The Promise of 2912" must be matched to a client, not guessed |
| Source system | GHL · Dubsado |
| Issued · due | Dates with their basis |
| Amount · paid · balance | Currency shown |
| Status + **basis badge** | §5 |
| Instalment | "2 of 3" when part of a plan |
| Reminders | Auto reminders (GHL) and personal chases (hello@), counts and last date |

Filters: status, client, engagement type, source system, basis, date range. **Invoice drawer:** line items, payment history, reminder and chase history, linked agreement, source evidence. A reminder never proves the debt is current [Agreed]; a draft email is never "sent" [Agreed].

### C. Agreements
| Field | Notes |
|---|---|
| Agreement / project name | e.g. "GSA - The Promise of 2912" |
| Client · engagement(s) | One client can have several agreements and versions [Agreed: count agreements, not clients] |
| Proposal sent · signed · signer | From alerts and the recap email |
| **Key terms** (when the document is readable) | Fee, billing interval, instalments, start, minimum term, end / renewal, notice period, what's included, ad spend paid separately |
| Status | Sent · Signed · Active · Ended · Superseded · **Terms unavailable** |
| Document link | Opens in Dubsado / Drive copy |

Without a readable document, the row shows *signed on X* and **"Terms not yet read"**, never invented terms [Agreed]. Key terms feed Client Portfolio → Scope & deliverables (§9 proposal there).

### D. Billing plans [Proposed]
How each engagement is billed, so "what should have been invoiced" is visible:

| Engagement | Typical plan (WIA public pricing; confirm per client) |
|---|---|
| Elevate | Monthly retainer, recurring in GHL |
| LeadLock | Setup fee ($1,697+) + $147/month |
| Google / Meta Accelerator | One-off ($1,997 / $1,697) or instalments |
| Accelerator bundle | $3,197, possibly instalments |

Per client: plan, amount, interval, next invoice date, instalments paid "2 of 3", and a **"Missing invoice"** flag when a recurring invoice expected this month doesn't exist. Plans come from agreements or GHL recurring invoices; public prices are only a hint and never a contract value.

### E. Activity
One timeline of commercial events: proposal sent, signed, invoice issued, auto reminder, personal chase, payment, refund, plan change. Each event has its source and is de-duplicated. Filter by client and type. The same events appear in the client's History → Commercial lane.

### F. Needs reconciliation [Agreed requirement; separate screen deferred by F4]

In the first version these items appear as an **Unmatched** tile and short list on the Overview (admins only), with the same resolutions. They must **not** go to the shared Action Register review queue, because non-admins can see that (F2). A full screen can follow if volume needs it.
| Reason | Resolution |
|---|---|
| Payment or signing alert can't be matched to a client (project label/name only) | Pick client and engagement |
| Same payment in Dubsado and GHL | Merge |
| Alert sent to an internal or test address | Mark as not a client event |
| Payment amount ≠ invoice amount | Mark as partial / confirm |
| Invoice with no agreement | Link agreement or confirm none |
| Expected recurring invoice missing | Confirm or explain |

Visible to finance users only. Every resolution is recorded [Agreed].

### Client record → Invoices & terms (sub-tab)
Same records, filtered to the client [Agreed]. **Condensed 26 Oct (02-client-portfolio P12)** to three areas that answer *"Is this client up to date, what's billed next, and what did they sign?"*:
1. **Standing line:** one headline (X overdue with amount, days late, chase state and a **Chase…** button · nothing overdue but an invoice is missing · up to date · **Can't confirm yet** when every invoice is Reported/Unknown · no records), then **Billing**, **Next invoice** and **Paid to date** (reconciled only, stating how many records were left out, per §5).
2. **Invoices** beside **Agreements & terms.** Invoices: compact rows with basis badges, missing invoice flagged first. Agreements: one card per current agreement with key terms; the **billing plan** and instalment progress fold into the card (no separate Billing plan table); superseded agreements collapsed.
3. **Activity:** one timeline with filters (All · Invoices & payments · Reminders & chases · Agreements). **Chase history** is the Reminders & chases filter. Also feeds History → Commercial lane.

---

## 7. Daily workflows

### 7.1 Overdue check (replaces Gisselle's manual GHL filter)
1. GHL sync marks invoices overdue the day after the due date (WIA timezone).
2. The Overview shows them with days overdue and the last automatic reminder.
3. Optionally: an in-app/Slack nudge to ops each morning when anything is newly overdue (reuses the Slack review screen; internal only).

### 7.2 Chase [Proposed]
Today: Gisselle tells Whitney → Whitney agrees → personal email from hello@ with the invoice link.
1. **Chase…** on an overdue invoice opens a **drafted personal email** (client contact, invoice link, amount, due date) in WIA's tone.
2. Optional internal Slack note to Whitney: "Bloom Manor invoice 9 days overdue. Chase draft ready."
3. **A person reviews and sends.** In release 1 the KB only drafts: copy to Gmail, or create a Gmail draft (needs Gmail compose permission). It never sends to a client automatically [Agreed: human review before external notification].
4. The sent chase is picked up from hello@ and logged on the invoice.

### 7.3 New client closed
Signed + paid alerts → shown under *New this week* → link to the onboarding flow (Command Center onboarding MVP). The KB still never creates a client automatically [Agreed].

---

## 8. Who can see it [Agreed: finance is a permissioned section]

**Decided (F2): admins only.** Whitney and Gisselle (the proposed admins) see this tab and the client's *Invoices & terms* sub-tab. For everyone else:
- the tab and the client sub-tab are **hidden**, not shown as "Coming soon";
- the **Commercial lane** in History, signing dates in Profile → Engagements, commercial lines in the Handover brief, and any chat answers about money are hidden too [Agreed, FR-CFIN-02];
- no neutral "check before discussing renewal" flag either.

Consequence for the Client Portfolio mockup: the Commercial lane and signing dates currently show to everyone. They need to be restricted to admins.

---

## 9. Possible additions

| Addition | Value | Dependency | Suggest |
|---|---|---|---|
| **Overdue nudge to ops** (daily) | Removes the "I sometimes forget" gap | GHL access (F1); Slack (D8). Goes to admins only | **First version (F4)** |
| **Chase drafts** | Saves writing the same email | Gmail draft permission for create; else copy | **First version (F3)** |
| **Missing recurring invoice flag** | Catches billing that never went out | Billing plans + GHL (F1) | First version, with Billing plans (F4) |
| **Renewal / end-date alerts** | Retention and upsell timing | Readable agreement terms | When terms are readable |
| **Accelerator → Elevate moment** | Programme ending + paid up = natural next offer | Programme end dates | Later (with Portfolio programme progress) |
| **Payment behaviour** ("usually pays 3 days late") | Context for chases and Health | 6+ months of reconciled history | Later; feeds Health (Stage 3) |
| **Monthly recurring revenue by engagement type** | Business view for Whitney | Reconciled recurring invoices | Later; check it's wanted (bookkeeping is Daniela's phase-2 area) |
| **Commercial flag in Call Prep** | Don't pitch an upsell to a client 30 days overdue | F2 makes finance admin-only, so only admin-hosted calls could see it | Admin-hosted calls only, later |
| **Proposal pipeline** (sent, not signed) | Sales follow-up | Proposal emails; sales is phase 2 | Not this tab |
| Ad spend tracking | — | Clients pay ad platforms directly; deferred paid media | Out |
| Accounting export / bookkeeping | — | Daniela's phase-2 bookkeeping scope | Out |

---

## 10. What this tab does not do

- Take payments, send or edit invoices, change Dubsado or GHL [Agreed].
- Auto-send chase emails to clients.
- Use public offer prices, LeadLock client sub-account data, or conversation claims as financial facts [Agreed].
- Show the money of clients' own customers (LeadLock sub-accounts are client businesses, not WIA billing).

---

## 11. Current mockup vs this scope

| Mockup today | Problem |
|---|---|
| "Collected" sums invoice face values | Cash ≠ invoice totals; needs payment records [Agreed rule] |
| Every invoice has a firm Paid/Open/Overdue | No basis shown; alert-only records can't be Open/Overdue |
| One agreement per client, terms as a single line | Clients can have several agreements; terms need the document |
| Connector named "HighLevel · Invoice standing" | Right system, but access is scope-denied today |
| No overdue workflow, chases, billing plans, reconciliation or new-client view | The daily job (overdue check) isn't supported |

---

## 12. Data readiness

| Source | Ready? | Note |
|---|---|---|
| Dubsado alerts in Gmail | **Yes** (signing + payment, verified 19 Oct) | Linked contract/invoice pages not opened yet |
| Personal chase emails (hello@) | **Yes** | Need classification |
| GHL invoices / payments / recurring | **No** | `invoices`, `payments/transactions`, subscription reads return scope-denied. Needs scopes on WIA's own location |
| Agreement documents | **Unknown** | Dubsado pages behind login; signed copies may be in Drive (Gisselle sends the countersigned contract to the client) |
| GHL contracts for migrated offers | **Unknown** | Check whether FFA contracts live in GHL documents |

---

## 13. Decisions

| # | Decision | Outcome |
|---|---|---|
| F1 | Where the invoice ledger comes from | **Request GHL invoice, payment and subscription read scopes on WIA's own location** (decided 22 Oct, corrected from "decide later"). GHL is the ledger for ongoing invoices; Dubsado alerts still cover signing and first payments. Ask WIA now so the scopes are in place before Stage 3 |
| F2 | Who can see finance | **Admins only** (Whitney, Gisselle). Hidden everywhere else, including History, Profile, Handover and chat |
| F3 | Chasing overdue invoices | **KB drafts the personal email, a person reviews and sends** from hello@. Optional Slack note to Whitney. Sent chase logged on the invoice |
| F4 | First-version sub-views and additions | **Billing plans · Agreements with key terms · Daily overdue nudge.** Needs reconciliation stays a small Overview list, not its own screen |
| F5 | Is anyone billed in both Dubsado and GHL? | Open, WIA to confirm per offer |
| F6 | Where signed agreement copies live | Open, Dubsado only or Drive copies per client |
| F7 | Gmail permission for chase drafts | Open. Create a Gmail draft (needs compose scope) or copy-to-clipboard only |

---

## 14. Mockup coverage (26 Oct)

Mockup: `frontend/exports/client-portfolio.html#money`. The global tab is now built from `src/views/MoneyRevised.tsx` (three sub-views, see §6); the client sub-tab from `ClientFinance` in `src/views/Money.tsx`. Sample finance records are in `src/finance.ts` (Dubsado for agreements and first invoices, GHL for ongoing invoices, as if F1 scopes were granted). `npm run export:live` builds a **local-only** copy (`exports/client-portfolio.local.html`) with real GHL and Dubsado data via `src/financeLive.ts`; it must never be shared.

| In the mockup | Not in the mockup yet |
|---|---|
| **Admin-only (F2):** tab hidden from the sidebar for non-admins; "no access" panel if opened by URL (switch to an admin from the sidebar account menu for the demo); client *Invoices & terms* sub-tab hidden; History Commercial lane and Profile signing dates hidden for non-admins | Hiding finance from chat answers (no chatbot yet) |
| **Overview:** six tiles (overdue, due in 7 days, paid this month, signed this month, chases this month, unmatched); overdue list with Chase…; daily overdue nudge preview with on/off; new this week (incl. an unmatched new signing with "Start onboarding"); coming up (due soon, agreement ending, missing invoice); unmatched list with Match / Not a client event | Real Slack delivery of the nudge |
| **Invoices:** status, client and source filters; basis badges (Reconciled / Reported / Unknown) with legend; reconciled-only total; drawer with line items, payments, reminders and chases, agreement, source | Partially paid and void samples |
| **Chase (F3):** drafted personal email (editable, no em dashes), optional Slack note to Whitney, Copy email, Gmail draft button disabled pending F7, "I've sent it" logs the chase on the invoice, overdue row and activity | Detecting the sent email from hello@ automatically |
| **Agreements (F4):** cards with key terms; "Terms not yet read" state (Willow); renewal signed (Everly) and superseded original; GHL-sold migrated offer (Harbor LeadLock); ending-soon flag | Agreement version comparison |
| **Billing plans (F4):** per engagement, next invoice, instalment progress, missing invoice flag (Harbor October retainer) | — |
| **Activity:** one de-duplicated timeline with type filter | — |
| **Client sub-tab (condensed):** standing line with Chase, *Can't confirm yet* for alert-only records, invoices beside agreements (plan folded in), one filterable activity timeline | — |
| The rows above describe the original six sub-views; in the v2 global tab they are regrouped into Today, Invoices, and Clients & contracts | Choosing v1 or v2 for the global tab |
