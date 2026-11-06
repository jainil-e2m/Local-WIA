# LeadLock / HighLevel intake scope — Maintained Client Knowledge Base

Review date: **19 October 2026 (IST)**; finance-token update **26 October 2026** (§3). This source review follows the approach in [slack_scope.md](slack_scope.md): required data → retrieval/access → real evidence → frontend mapping → verified results and remaining gaps.

## 1. Feasibility verdict

**Two credentials have now been tested. The original WIA token reads WIA's location and contacts. The new agency token successfully reads LeadLock agency details, discovers all 59 returned sub-accounts, reads WIA/Dogwood location metadata, and searches users. Neither tested setup yet validates client lead outcomes, invoice records, support intake or survey feedback. Direct Dogwood data reads with the new agency token remain scope-denied.**

**Update, 26 October 2026: WIA billing records are now verified.** A third credential, `GHL_FINANCE_PIT`, created in WIA's own sub-account with read-only finance scopes, reads WIA's invoices, recurring invoice schedules, payment transactions, subscriptions and orders. Product/price reads are still denied. Client lead outcomes, support intake and surveys remain unverified; the finance token does not touch client sub-accounts. See [Finance token — verification update](#finance-token--verification-update-26-october-2026).

This is an access-limited result, not proof that those records are absent. The original token's account-discovery limit has been overcome with the agency credential; feature-level/client-data access is still unresolved. The browser automation runtime failed before a LeadLock page could be inspected; UI visibility is therefore unknown. Earlier test results below are retained as historical observations, followed by the agency-token update.

The frontend remains a fictional preview. No live records were inserted, no permissions changed, and no messages, invoices, payments, workflows, appointments or forms were created or updated. This review does not replace the user's decision to obtain signing/payment events from Dubsado, including its notifications to Gmail.

## 2. Keep these three record types separate

| Record type | What it represents | Knowledge Base use |
| --- | --- | --- |
| **WIA's own LeadLock location and contacts** | WIA's CRM: potentially prospects, subscribers, customers and other contacts. | Candidate identity matching and account metadata. A contact alone does not establish an active paid engagement. |
| **WIA billing and commercial records** | Where present, amounts the WIA client owes or pays to WIA; offer/product prices and subscriptions are separate record types. | Invoice standing and financial context, if confirmed as the relevant billing source. Dubsado signing/payment events remain the directed intake route. |
| **Each client's LeadLock sub-account** | That business's prospects, inquiries, appointments, pipeline and bookings. | The agreed Client Profile lead-outcome snapshot. These are the WIA client's business outcomes, not payments to WIA. |

Reading the first category does not establish access to either of the others. The original configured location was confirmed as **Wedding Industry Ads**, ID `Xi40zxmRvW8Pbyk5DYHp`, timezone **America/Chicago**. Agency discovery now independently confirms **Dogwood Reserve**, ID `IAfZCWz2SlgOE6081j3F`, timezone **America/New_York**. The location's timezone must be retained per account.

## 3. What was actually tested?

### Live API probe

Executed **19 October 2026, 16:40:26–16:40:42 IST**, using the existing `GHL_PIT` and `GHL_LOCATION_ID` configuration and `Version: 2021-07-28`, matching the earlier project tooling. **17 GET requests:** two HTTP 200, fourteen HTTP 401 scope denials, and one HTTP 403 forbidden response.

| Resource checked | Result | Meaning |
| --- | --- | --- |
| `GET /locations/{configuredLocationId}` | **200** | WIA location identity, field structure and timezone confirmed. |
| `GET /contacts/`, limit 3 | **200** | Three contact records inspected; response metadata reports **1,787 contacts** and additional pages. No full contact backfill performed. |
| `GET /locations/search` with the returned company ID | **403 — Forbidden resource** | Agency/sub-account discovery not available through this tested request/credential. |
| `GET /invoices/` | **401 — token not authorized for this scope** | Invoice values, status, dates, reminders and source coverage cannot yet be validated. |
| `GET /payments/transactions` | **401 — scope denied** | Actual payments and refunds not inspected. |
| `GET /payments/subscriptions` | **401 — scope denied** | Subscription amounts, billing intervals and status not inspected. |
| `GET /payments/orders` | **401 — scope denied** | Order line items and related purchase records not inspected. |
| `GET /products/` | **401 — scope denied** | Product/offer catalogue not inspected. Per-product price lookup was not attempted because no product list was available. |
| `GET /opportunities/pipelines` | **401 — scope denied** | Pipeline/stage meanings and support-pipeline presence not inspected. |
| `GET /opportunities/search` | **401 — scope denied** | Opportunity counts, statuses, dates and booking evidence not inspected. |
| `GET /calendars/` | **401 — scope denied** | Calendar purpose and appointment availability not inspected. Dependent event reads were not attempted. |
| `GET /surveys/` and `/surveys/submissions` | **401 — scope denied for both** | Survey existence/content, responses and client association not inspected. |
| `GET /forms/` and `/forms/submissions` | **401 — scope denied for both** | Support-form configuration and submissions not inspected. |
| `GET /conversations/search` | **401 — scope denied** | Conversation availability and support-message content not inspected. No per-conversation message read attempted. |
| `GET /locations/{id}/customFields` | **401 — scope denied** | Custom-field definitions, including any possible pricing field, not inspected. |

Evidence: [live_probe.json](knowledge_base/wia-knowledge-base/verification/leadlock/live_probe.json). It retains status codes, errors, field names, counts and limited non-PII observations. Contact names, email addresses, phone numbers, credentials, and full raw contact bodies are not retained in the report. Contact identity hashes and IDs are still internal identifiers.

These denials occur while location/contact reads succeed, so the token is usable but lacks access for the tested resources. The exact complete set of grants on the token was not introspected. A list of scopes offered in the settings picker is not evidence that this token holds them.

### Targeted follow-up: client matching and account boundaries

Executed **16:42:29–16:42:34 IST**, with five additional GET reads:

- Two other location IDs were taken from already collected Slack app links, rather than invented. Both `GET /locations/{id}` requests returned **403**. Their account identity and client mapping remain unverified.
- Bounded contact searches for **Funktastic**, **Dogwood**, and **Luxury Travel** returned **2, 1, and 1 candidates**, respectively. These demonstrate search feasibility, not four confirmed client engagements or access to their sub-accounts.
- The returned candidates did not have a populated matching company name; the search can match other fields. Manual/entity matching against known contacts and original records is still needed. The two Funktastic candidates must not automatically become two separate clients.

Evidence: [followup_probe.json](knowledge_base/wia-knowledge-base/verification/leadlock/followup_probe.json).

### Local evidence and attempted browser check

- The frontend has **six fictional invoices:** four Paid, one Open, one Overdue. Its evidence array has **zero `HighLevel` source rows**, despite the connector card showing six sample records. The invoice rows do not currently carry a source reference.
- The local Slack archive contains **28 app-account-link occurrences referencing three location IDs**: WIA's configured ID and the two other IDs checked above. A saved link can help build the account-reference feature but does not prove the account name, live access, or historical metric coverage.
- The 126 saved LeadLock email bodies belong to the prior marketing-email corpus. They are not an invoice/payment archive, client lead database, or support-ticket history and do not validate the Knowledge Base financial mocks.
- The older `ghl-scopes.tsv` is a picker catalogue, not current token grants. No separate populated GHL/LeadLock credential was found in the other project environment files checked during the initial inspection.
- Browser inventory failed twice, including after one reset: `failed to write kernel assets ... (os error 3)`. No LeadLock browser page, pricing field, login, or settings screen was inspected.

Evidence: [local_audit.json](knowledge_base/wia-knowledge-base/verification/leadlock/local_audit.json), [ui_check.json](knowledge_base/wia-knowledge-base/verification/leadlock/ui_check.json).

**Retry requested by the user:** Browser inventory was attempted again, followed by initialization through the alternate `node_repl` computer-use runtime. Both failed with the same missing kernel-assets path error before reaching LeadLock. The pricing field remains uninspected; this is a tool-runtime issue, separate from the API permission denials.

### New agency token — verification update

The user added `GHL_AGENCY_PIT` as a separate entry in `frontend/.env`. The original WIA token and the earlier reports were preserved. The new token was tested **19 October 2026, 17:09:47–17:10:04 IST**, followed by a two-request user-search check at **17:10:35–17:10:36 IST**.

| Check with agency token | Observed result | What this establishes |
| --- | --- | --- |
| `GET /companies/{companyId}` | **200**, agency name **LeadLock** | The new credential is valid for this agency. |
| `GET /locations/search` | **200** over four pages: 20 + 20 + 19 + 0 | **59 distinct sub-account IDs** returned; pagination reached an empty page. This is an account inventory, not 59 active WIA client engagements. Demo/template/internal accounts are present. |
| WIA and Dogwood `GET /locations/{id}` | **200** for both | Cross-account metadata reads now work; Dogwood's actual ID/name/timezone verified. |
| `GET /users/?locationId=...` for WIA/Dogwood | **401**, `Token's user type mismatch!` | This location-specific list route does not accept the supplied agency token in this test. It does not establish that user reads are unavailable. |
| `GET /users/search?companyId=...&limit=3` | **200**, 3 sample rows; response count **77** | Agency user search is available. This is a bounded sample, not a completed user roster or proof all users are WIA staff. |
| `GET /users/search` filtered by Dogwood location | **200**, 3 rows; response count **3** | User IDs/role structure and account filtering are available. Business roles and WIA/client affiliation still require mapping. |
| Dogwood contacts, pipelines, opportunities, calendars, invoices, surveys, forms and conversations | **401**, token not authorised for scope, on all eight tested reads | Metadata discovery does not grant these client-data reads. The lead-outcome/financial/support/survey checks remain open. |

The combined new-token run made **19 GET requests: 9 successful and 10 HTTP 401 responses**. Two of the 401s were the user-route token-type mismatches; eight were scope denials. These outcomes must not be collapsed into a claim that the token is invalid.

The agency inventory also resolves previously observed Slack link IDs: `OhK5iHgR19YiVHrq6rMw` is **DJ Hybrid Chicago**, and `mj0FRsBhHcNFDaJltdHZ` is **Funktastic Productions**. A channel mentioning both brands therefore needs an explicit relationship to the relevant accounts rather than one guessed location ID. This mapping establishes platform account identity, not which engagement owns every statement in the channel.

**Frontend impact:** Agency discovery can support the client/account selector, account-reference mapping, per-account timezone and connector inventory. User search can support identity resolution after role mapping. Do not automatically import every agency location as an active client, treat account creation as engagement start, or populate performance/billing values from the location list.

**Next authentication step:** The user's preferred direction is one centrally managed integration rather than manually maintained private tokens for every client. The documented OAuth agency-to-location flow is the route to investigate for client-data access: install/authorise the app for intended accounts and scopes, then manage the authorised location tokens in the backend. The present agency PIT was not exchanged for tokens, no OAuth app was installed, and no permission changes were made. Do not assume this PIT is interchangeable with the agency OAuth token used by that flow. See [HighLevel OAuth token types and location-token flow](https://marketplace.gohighlevel.com/docs/Authorization/OAuth2.0/) and [agency user search](https://marketplace.gohighlevel.com/docs/ghl/users/search-users/).

Evidence: [agency_probe.json](knowledge_base/wia-knowledge-base/verification/leadlock/agency_probe.json), [agency_users_probe.json](knowledge_base/wia-knowledge-base/verification/leadlock/agency_users_probe.json). Full contact/user PII and token values are excluded from these reports.

### Finance token — verification update (26 October 2026)

The user created a Private Integration token in the **Wedding Industry Ads** sub-account (`Xi40zxmRvW8Pbyk5DYHp`) with read-only finance scopes and added it as `GHL_FINANCE_PIT` in `frontend/.env`. `GHL_PIT` and `GHL_AGENCY_PIT` were left unchanged. Probe run **26 October 2026, 13:34:15–13:34:31 IST**: **13 GET requests, 12 HTTP 200 and 1 HTTP 401.** Full pagination was reached on every list (no truncation). Nothing was created, sent, voided or changed.

| Resource | Result | What it establishes |
| --- | --- | --- |
| `GET /locations/{id}` | **200** | Token belongs to WIA's location; timezone **America/Chicago**. |
| `GET /invoices/` (4 pages) | **200**, **347 invoices** | Live USD invoices issued **31 Jan 2023 – 23 Oct 2026** to **41 distinct contacts**. Statuses observed: **343 `paid`, 4 `sent`**. **341 of 347 were generated by recurring schedules.** Fields include `status`, `total`, `amountPaid`, `amountDue`, `issueDate`, `dueDate`, `invoiceItems`, `contactDetails`, `scheduleId`, `sentAt`, `remindersConfiguration` (with `reminderExecutionDetailsList`) and `lateFeesConfiguration`. |
| `GET /invoices/schedule` | **200**, **53 schedules** | All monthly (`rrule`: `dayOfMonth`, `interval`, `intervalType`, `startDate`, `timezone`, `daysBefore`). **14 active** (combined **$18,961/month**), 2 scheduled, 36 cancelled, 1 draft (test mode). 48 have auto-payment enabled. No stored next-execution date was found; it must be derived from the rule. |
| `GET /payments/transactions` (4 pages) | **200**, **391 transactions** | Stripe (390) plus 1 manual. **373 succeeded ($425,524), 18 failed ($21,546).** Sources: invoice 357, calendar 25, funnel 9. **21 are test-mode** (`liveMode: false`). |
| `GET /payments/subscriptions` | **200**, **5** | All test-mode, cancelled funnel subscriptions from Apr–May 2023 (WIA ADvisory, LeadLock). **Not the current billing mechanism.** |
| `GET /payments/orders` | **200**, **12** | Paid calendar bookings (audits, consultation/VIP calls) and test-mode funnel orders. Peripheral to client billing. |
| `GET /products/` | **401 — scope denied** | `products.readonly` / `products/prices.readonly` were not granted. List prices remain unread. |

**What this establishes**

- **Ongoing client billing lives in WIA's sub-account as recurring invoice schedules with Stripe auto-pay**, not as GHL subscriptions. Invoice titles and line items are WIA services: Google and/or Meta Ads management, "LeadLock, Google + Meta Ads", Google Search Accelerator access, Accelerator Bundle, an ELEVATE 2027 onboarding reservation and workflow add-ons.
- **The KB can derive overdue state:** an invoice that is not `paid`/`void`/`draft`, has an amount due and is past its due date (in WIA's timezone). At probe time **4 invoices were open ($5,991)** and **2 were overdue ($2,000 two days late; $997 forty-seven days late, a manual one-off invoice not generated by a schedule)**. GHL exposes no dedicated `overdue` status value.
- **Failed auto-payments are a direct signal.** With auto-pay on 48 of 53 schedules, a failed Stripe transaction usually precedes an overdue invoice and should be surfaced on its own.
- **Recurring plans and missing invoices are derivable.** Each schedule has an amount and a monthly rule; comparing the expected monthly occurrence with the invoices carrying that `scheduleId` supports a "missing invoice" check.
- **No Dubsado-originated invoices appear in the GHL list.** This is consistent with Dubsado covering signing and first payment only. A matched Dubsado alert ↔ GHL record example has not yet been made.
- **Data hygiene rules needed:** filter `liveMode: false`; trust `status` but flag anomalies (one Dec 2023 invoice is `paid` with no `amountPaid` and $2,000 still due, likely marked paid manually); reminder settings exist on only 26 invoices, and a configured reminder is not proof it was sent.
- **Not covered by this token:** agreement terms (invoices carry `termsNotes`, not the signed agreement); list prices (scope missing); the agency-level SaaS/rebilling revenue shown on the LeadLock Agency Dashboard (a separate stream requiring agency `saas/location.read`); and every client sub-account's own data.

Evidence: [finance_probe_2026-10-26.json](knowledge_base/wia-knowledge-base/verification/leadlock/finance_probe_2026-10-26.json), produced by [verify_leadlock_finance.mjs](knowledge_base/wia-knowledge-base/verification/leadlock/verify_leadlock_finance.mjs). The report stores aggregates and record shapes only: no token, emails or phone numbers, and contact IDs are hashed. Invoice titles are retained and a few include client names, so keep the file internal.

## 4. Required intake data and retrieval plan

**20 October recheck:** The configured agency PIT still reads Dogwood account metadata (200), but Dogwood contacts, pipelines, opportunities and calendars return **401: token not authorised for scope**. The original WIA PIT still reads WIA metadata (200) while pipeline/opportunity reads return the same denial. Two additional opportunity requests using the current documented `Version: v3` and `locationId` parameter also return 401. This is not an empty-data result or merely an old query/version issue. No permissions/tokens were changed. See [fresh checks](knowledge_base/wia-knowledge-base/verification/leadlock/access_recheck_2026-10-20.json), [v3 comparison](knowledge_base/wia-knowledge-base/verification/leadlock/v3_access_recheck_2026-10-20.json) and the [next test plan](knowledge_base/wia-knowledge-base/verification/leadlock/access_test_plan.md).

The following routes identify the documented retrieval approach. **Only location/contact reads are verified live here.** The remaining rows describe what must be checked after the appropriate read access is available; they do not promise that WIA maintains every field or record.

| Data needed | Retrieval approach | Purpose and evidence conditions |
| --- | --- | --- |
| Account identity/reference | `GET /locations/{locationId}`; authorised discovery where supported. Maintain explicit KB client → location mapping and the observed app URL. | Client Profile account link and correct tenant selection. WIA account metadata cannot stand in for client sub-account metadata. |
| Contact identity | Paginated contact listing/search and, if needed, contact detail. Retain IDs, relevant contact/business fields and verified cross-source identifiers. | Candidate mapping to known WIA clients. Contact creation date is CRM creation, not automatically engagement start; `assignedTo` is not automatically the WIA account manager. |
| Invoice ledger | `GET /invoices/` scoped by `altId` and `altType=location`, plus an individual invoice read where needed. | Invoice ID/number, payer association, issuer, currency, totals, paid/due amounts, issue/due dates, status, mode and source evidence. Exclude test/draft/voided records from payable/collected figures as appropriate. |
| Payment/refund evidence | `GET /payments/transactions`, optionally joined to orders/subscriptions and underlying invoices. | Distinguish payment from listed price, failed charge or refunded value. Verify financial relationship, mode and units before calculating balances. |
| Products and prices | `GET /products/`, then `/products/{productId}/price` for the observed product. | Resolve the user's pricing question if it refers to catalogue prices. An offer's list price is not evidence a client signed at that price or paid it. |
| Subscription context | `GET /payments/subscriptions`, relevant invoice schedules if recurring invoices are the actual mechanism. | Establish billing interval and active/cancelled state where maintained. An active subscription alone does not prove every payment is settled. |
| Client inquiries/opportunities | Pipeline definitions plus opportunity search/detail in each authorised client location. Join contact/attribution records only where necessary. | Inquiry and booking snapshots; confirm which record/date constitutes a new lead and how duplicates/imports are treated. |
| Tours/consultations | Calendar definitions, then bounded `GET /calendars/events` using an actual calendar/user/group identifier. | Relevant bookings and appointment status; distinguish sales calls, tours, reschedules, cancellations, no-shows and completed appointments. Not every appointment is a won customer. |
| Support requests | Identify the maintained form, pipeline or mailbox first. Form submissions, opportunity records, or conversation/message reads may supply the record. | Client issue, dates, owner, status and next action. A generic CRM conversation or sales pipeline is not automatically a support ticket. |
| Satisfaction surveys | Survey definitions and submission reads, with question/scale context and reliable WIA-client association. | Health evidence. Surveys may be applications/qualification forms; survey existence alone does not prove satisfaction data. |
| Custom-field definitions | `GET /locations/{locationId}/customFields` and relevant values on source records. | Interpret account-specific fields before using them for business identity, pricing, booking or support state. A field ID/value without its definition is insufficient. |
| Source snapshots/freshness | Persist location/resource/record IDs, observed time, source update date, request/window metadata and a safe source locator. | Evidence drawer, source library, history and connector health. Record visibility/access failures separately from empty data. |

Primary references: [versioned invoice API](https://marketplace.gohighlevel.com/docs/2021-07-28/ghl/invoices/list-invoices/), [transactions](https://marketplace.gohighlevel.com/docs/ghl/payments/list-transactions/), [product prices](https://marketplace.gohighlevel.com/docs/ghl/products/list-prices-for-product/), [opportunity APIs](https://marketplace.gohighlevel.com/docs/ghl/opportunities/search-opportunity/), [calendar events](https://marketplace.gohighlevel.com/docs/ghl/calendars/get-calendar-events/), [surveys](https://marketplace.gohighlevel.com/docs/ghl/surveys/get-surveys/), [survey submissions](https://marketplace.gohighlevel.com/docs/ghl/surveys/get-surveys-submissions/index.html), [form submissions](https://marketplace.gohighlevel.com/docs/ghl/forms/get-forms-submissions/). Public documentation may default to newer versions; implementation must pin a compatible version per resource and validate it against the actual account.

## 5. Read access required before deeper verification

| Feature to verify | Relevant documented read scopes | Current evidence |
| --- | --- | --- |
| Location/contact identity | `locations.readonly`, `contacts.readonly` | Reads succeeded for WIA's location; other locations and discovery were forbidden. Scope names alone do not extend tenant access. |
| Agency/company discovery and users | `companies.readonly`, `locations.readonly`, `users.readonly` | **New agency token verified:** company/location reads, all 59 returned account metadata records, and agency/filtered user search. Location-specific `/users/` returned token-type mismatch; use the verified `/users/search` route for this credential. |
| Invoices and recurring invoice schedules | `invoices.readonly`; `invoices/schedule.readonly` if schedules are needed | Invoice list denied; schedule reads not tested. |
| Transactions, subscriptions, orders | `payments/transactions.readonly`, `payments/subscriptions.readonly`, `payments/orders.readonly` | All three tested list resources denied. |
| Catalogue price meaning | `products.readonly`, `products/prices.readonly` | Product list denied; dependent prices not tested. |
| Pipeline/lead outcomes | `opportunities.readonly` and applicable contact reads in the client location | Pipeline and opportunity reads denied in WIA location. Client-location data not verified. |
| Booking outcomes | `calendars.readonly`, `calendars/events.readonly` | Calendar list denied; event access not tested. |
| Survey/form intake | `surveys.readonly`, `forms.readonly` as applicable | Definitions and submission reads denied. |
| Support messages, if that is the actual route | `conversations.readonly`, `conversations/message.readonly` | Conversation search denied; message reads not tested. |
| Interpretation of custom fields | `locations/customFields.readonly` | Definition read denied. |

Source: [HighLevel scope reference](https://marketplace.gohighlevel.com/docs/Authorization/Scopes/), checked 19 October 2026. This is a scoped access checklist, not a request to enable every capability indiscriminately. Select the actual intake requirements, then establish the authorised credential/location access for them. No permission or token changes were performed during this review. Per-location private integrations or an appropriately installed OAuth approach are implementation options; agency UI access does not itself grant a location API token cross-account access.

### Is the API key the problem?

The configured credential is a **Private Integration Token (PIT)**. It successfully authenticated account/contact requests, so these tests do not indicate an invalid or expired token. There are two distinct observed access limits:

- **Feature permissions:** The 401 responses explicitly say the token is not authorised for the scope. Select the required read scopes on the existing integration, then rerun those reads. The complete grant configuration has not been inspected, and no scopes were changed.
- **Account authorisation:** The 403 responses deny agency discovery and the two other observed account IDs. Adding billing or pipeline read scopes in WIA's location does not itself establish access to those client locations. Verify the integration's level and resource support and provide the appropriate authorised account credentials/installations.

HighLevel states that existing Private Integration scopes can be edited without generating a new token. The first fix is therefore to correct the relevant permissions/account setup, not blindly rotate the working token. See [Private Integrations: Everything you need to know](https://help.gohighlevel.com/support/solutions/articles/155000003054-private-integrations-everything-you-need-to-know), especially “Can I edit the Private Integration permissions without updating the token?” The exact configuration causing the 403 responses still requires account-level inspection.

## 6. Mapping to the current frontend and agreed additions

| Frontend area / field | What LeadLock could contribute | Result of this verification |
| --- | --- | --- |
| Client Profile: primary contact, business identity and location | Relevant contact/location metadata, subject to client matching. | **Partial live support.** Original WIA contact search works; agency token now discovers client location IDs/names/timezones. Dogwood contact reads are still denied. Neither 1,787 contacts nor 59 locations establishes the active client portfolio. |
| Client Profile: service, engagement start, audience, voice, differentiators and goals | Possibly custom fields and linked reference records. | **Unverified/supplementary.** These are not established by a CRM contact or creation timestamp. Use signed engagement documents and approved background sources. |
| Agreed LeadLock account link, KB-CH-01 | Observed app URL + stable location ID + reviewed client association. | **Account discovery now verified with the agency token.** Dogwood ID/name and prior Funktastic/DJ Hybrid link IDs resolved. Map accounts to KB engagements and validate navigable URLs/user access. The addition is documented, not yet rendered in the current Client Profile. |
| `INVOICES`: ID, amount, issued, due, status, paid | Relevant invoice/payment records for WIA billing. | **Verified live, 26 Oct (finance token).** 347 real invoices with ID/number, total, amount paid/due, issue/due dates, status, line items and contact. Overdue is derived (open + past due), not a GHL status. Frontend invoices are still fictional sample records. |
| Money and client “Invoices & terms”: agreement terms | The actual underlying agreement, or linked commercial record where appropriate. | **Not supplied by a price or invoice alone.** Dubsado/Drive/Gmail remain relevant sources; GHL does not become the contract source by default. |
| Money: reminder history | Actual reminder execution/log or corresponding communication evidence. | **Partly verified.** Invoices expose `remindersConfiguration.reminderExecutionDetailsList`; settings are present on 26 of 347. The execution-log contents are not yet inspected, and a configured reminder is still not proof of delivery. |
| Money: collected/outstanding totals | Reconciled invoices/transactions after tenant, currency, status, live/test and duplicate checks. | **Data available, rules required.** Invoices and Stripe transactions are readable; filter test-mode records (21 transactions), trust `status`, and flag anomalies before totalling. Never substitute catalogue prices, opportunity values or contact counts. |
| Money: billing plans / missing invoice | Recurring invoice schedules and the invoices they generate. | **Verified source.** 53 monthly schedules (14 active, $18,961/month); next date derived from `rrule`; missing-invoice check by matching `scheduleId`. |
| Money: failed payments | Failed transactions linked to invoices. | **Verified source, not yet in the mockup.** 18 failed Stripe transactions; with auto-pay on most schedules this is the earliest late-payment signal. |
| Agreed lead-outcome snapshot, KB-CH-03 | Client-location inquiries, bookings, won outcomes, defined transitions and exceptions. | **Not verified.** Correct client access, record definitions and maintained pipeline data are missing. The current mock has no implemented LeadLock outcome snapshot. |
| Agreed support issues, KB-CH-02 | Verified support form/pipeline/mailbox records and resolution history. | **Not verified.** Generic form/pipeline/conversation reads denied; actual intake route still unknown. |
| Health & sentiment | Attributed survey/support feedback; outcome trends as a separate performance dimension. | **Not verified.** No survey response/support content was inspected. A CRM tag, payment issue or low inquiry count alone is not a sentiment finding. |
| Call preparation and weekly focus | Evidenced current issues, lead outcomes and relevant financial context. | **Dependent on the checks above.** No live metrics or issues can currently be asserted from this probe. Calendar event access in GHL would also not replace the separately planned Google Calendar review. |
| Actions/Commitments and engagement history | Source-backed commercial/operational events; follow-up recommendations. | **Conditional.** A record may motivate a suggested action; it does not prove a person accepted it. Status changes and independently verified fixes need their own trail. |
| Sources / EvidenceDrawer | Cited, dated connector snapshots with location and record IDs. | **Shape is feasible; data is limited.** `HighLevel` is in the source-kind union, but there are no HighLevel evidence fixtures or invoice citations in the present mock. |
| Connections: HighLevel sample count/readiness | Per-resource access checks, last successful reads and gaps. | **Supported by this probe.** Show partial access, not a globally healthy connector or “6 invoices synced.” |
| Client activity/coverage indicators | Defined source activity and expected-source coverage. | **Not the CRM contact total.** No full history, lead totals or coverage percentage was established. |
| Accelerator attendance | Actual attendance evidence from the appropriate meeting source. | **Not established by GHL contact membership or an appointment booking.** |

Frontend references: [data.ts](knowledge_base/wia-knowledge-base/frontend/src/data.ts), [types.ts](knowledge_base/wia-knowledge-base/frontend/src/types.ts), [Money.tsx](knowledge_base/wia-knowledge-base/frontend/src/views/Money.tsx), [ClientDetail.tsx](knowledge_base/wia-knowledge-base/frontend/src/views/ClientDetail.tsx), [Settings.tsx](knowledge_base/wia-knowledge-base/frontend/src/views/Settings.tsx). Agreed additions: [knowledgebase_changes.md](knowledgebase_changes.md).

## 7. Pricing, Dubsado and the financial-source decision

The earlier call described Dubsado agreements/first payments and GHL overdue invoice handling. That establishes a historically mixed workflow, not the meaning of the particular pricing attribute the user saw now.

**FIN-V-01 is partially resolved (26 October).** The finance token established that WIA's ongoing client billing is maintained in its own GHL sub-account as recurring invoice schedules and invoices paid through Stripe (see §3). That settles which system holds current invoice/payment state for ongoing billing. It does **not** yet identify the specific pricing value the user originally saw: product/price reads are still denied and the screen has not been inspected. Until then the value cannot be treated as a contract amount, balance, payment or revenue.

*Original 19 October position, retained for history:* invoice, product, transaction, subscription and custom-field definition access were denied, and the pricing screen could not be inspected.

Required next evidence is still the exact screen/record/field and a representative match to the actual commercial event. Keep Dubsado signing/payment event intake as directed. A Dubsado “paid” notification is not automatically a full current receivables ledger; its actual subject/body/URLs and partial-payment semantics will be checked during the Gmail source review. Do not broaden this LeadLock pass into Gmail inspection.

## 8. Rules for client lead-outcome calculations

These are requirements for a later representative client-account test, not metrics calculated in this review:

- **New inquiries:** choose a real lead event/date and exclude inappropriate imports, duplicate contacts, existing customers and WIA's own marketing contacts. Contact creation and opportunity creation can represent different events.
- **Tours/consultations:** select the appropriate calendars and appointment types. Deduplicate reschedules, handle cancellation/no-show state, and distinguish a scheduled meeting from attendance.
- **Booked clients:** agree which stage/status or contract/deposit evidence means a genuine booked customer. Opportunity monetary value is a deal estimate, not proof of money received.
- **Conversions:** choose cohort-based or period-based denominators and obtain the history necessary for that definition. A current pipeline stage cannot reconstruct every historical transition.
- **Stalled/follow-up gaps:** agree inactivity rules and inspect real activity timestamps/messages. Lack of API access must never count as lack of follow-up.
- **Attribution:** preserve available acquisition evidence and its limitations. GHL alone does not establish ad spend, CPL or ROAS. The Google Ads/Meta integration remains deferred as documented in [Canbebuilt.md](Canbebuilt.md).
- **Reporting boundaries:** each result carries location, period, timezone, definition, last refresh and missing-data status. WIA's timezone is not automatically the client's timezone.

## 9. Implementation and frontend contract implications

Follow [backend_build.md](backend_build.md) when this connector is implemented; the verification scripts are standalone probes, not the production backend.

1. Maintain a reviewed KB client ↔ WIA contact ↔ client location mapping. Preserve multiple contacts, aliases and service relationships without creating duplicate engagements.
2. Store location/resource/record IDs and typed snapshots with observed/updated timestamps. Gate calls by known access and report unsupported/forbidden/empty/partial separately.
3. Page each resource with its documented cursor or offset mechanism; do not combine the probe's small samples into portfolio-wide totals. Capture full-backfill bounds and subsequent updates.
4. Keep billing, product pricing, pipeline estimates and client outcomes separate in storage and APIs. Pin currency/units per endpoint, live/test mode, refunds and business meaning before aggregating amounts.
5. Add source citations and actual agreement references to invoice records. Current `Invoice` has no `currency`, `sourceId`/source URL, location ID, partial-payment amounts, or comprehensive status handling. The currency formatter currently assumes USD.
6. Current “View terms” renders a commercial agreement from the invoice fixture's `terms` string; production must distinguish billing terms from a signed agreement. Preserve contract-source provenance and effective dates.
7. Add client account/support/outcome fields only after their source contracts are defined. Populate unknown or access-denied states honestly. Client-specific deal/health interpretations need confidence and cited definitions.
8. Represent connector health per location and resource. WIA contact reads succeeding while invoice reads fail is a partial connection, not a complete synchronization.
9. Use bounded reads/retries, honor rate-limit responses, keep credentials server-side, and retain only relevant contact data in evidence. No write permission is needed to perform these intake checks.

## 10. Verification cases and open items

| Case / question | Observed outcome | Status / next evidence |
| --- | --- | --- |
| LL-E01 — Is the token usable? | WIA location read succeeded, confirming account ID/name/timezone. | **Verified live for that location.** |
| LL-E02 — Can contacts be read and searched? | Three list records; searches returned 2/1/1 candidates for known account terms. | **Verified retrieval; client mapping incomplete.** Names, roles and engagement status still need reconciliation. |
| LL-E03 — Does access extend to client accounts? | Original WIA token returned 403; **new agency token discovers 59 locations and reads Dogwood metadata successfully**. | **Discovery verified; client data still denied.** Continue with authorised location-level data access. |
| LL-E04 — Can the six invoice mocks be backed by live records? | 19 Oct: invoice read returned 401. **26 Oct (finance token): 347 live invoices read** — 343 paid, 4 sent/open, 2 of them past due; 53 recurring schedules; 391 transactions including 18 failed. | **Verified (closed).** Paid, open and overdue states are backed by live records; overdue is derived from status + amount due + due date. Implementation still needs client mapping, test-mode filtering and anomaly flags. |
| LL-E05 — What does the observed GHL price mean? | 26 Oct: billing mechanism identified (recurring invoice schedules, Stripe); product/price reads still **401**; the original screen not yet identified. | **Open, narrowed (FIN-V-01).** Add `products.readonly` + `products/prices.readonly` to the finance token or identify the exact screen/field, then reconcile with a Dubsado example. |
| LL-E06 — Are there usable satisfaction surveys? | Survey list/submission reads denied. | **Open KB-V-01.** Verify the real survey purpose, response and client mapping. |
| LL-E07 — Is support managed in LeadLock? | Form/pipeline/conversation reads denied. | **Open KB-V-02.** Trace the actual request through the maintained support route. |
| LL-E08 — Can lead/booked-client outcomes populate Client Profile? | Fresh WIA/Dogwood pipeline/opportunity reads remain scope-denied; Dogwood metadata is readable. v3 opportunity reads fail likewise. | **Open KB-V-03.** Establish authorised feature access and reconcile a defined client snapshot; see the central OAuth test plan. |
| LL-E09 — Do old archives prove billing or outcomes? | Existing local bodies are marketing emails; account links are only pointers. | **No.** Keep those evidence classes distinct. |

Verification registers: [tobeverified.md](tobeverified.md), [tobeverified_knowledgebase.md](tobeverified_knowledgebase.md). Their items remain open; this review adds concrete access findings rather than claiming data absence or successful end-to-end intake.

## 11. Reproducing the review

From the workspace root:

```powershell
python knowledge_base/wia-knowledge-base/verification/leadlock/audit_local_leadlock.py
node knowledge_base/wia-knowledge-base/verification/leadlock/verify_leadlock.mjs
node knowledge_base/wia-knowledge-base/verification/leadlock/verify_leadlock.mjs --followup
node knowledge_base/wia-knowledge-base/verification/leadlock/verify_leadlock_agency.mjs
node knowledge_base/wia-knowledge-base/verification/leadlock/verify_leadlock_agency.mjs --users
node knowledge_base/wia-knowledge-base/verification/leadlock/verify_leadlock_finance.mjs
```

The finance command uses `GHL_FINANCE_PIT` + `GHL_LOCATION_ID`, pages through invoices, schedules, transactions, subscriptions and orders (up to 10 pages of 100 each), attempts products, and writes `finance_probe_<date>.json` with aggregates only.

The local audit reads existing fixtures/archives and writes `local_audit.json`. The first live command writes `live_probe.json`; `--followup` uses account IDs from the local audit and writes `followup_probe.json`. Both use the existing server-side configuration and issue GET requests only. A rerun replaces these reports; retain dated copies if needed for a longitudinal audit. The initial probe's field-presence flags establish available shapes, not that arrays contain meaningful values for every contact.

The browser failure is recorded in `ui_check.json`; it is not reproduced by the API script. The original review preceded the other source reviews; consult the current feasibility study and per-source scopes for their later findings.

The agency commands use `GHL_AGENCY_PIT`, preserve the original credential's reports, and write `agency_probe.json` / `agency_users_probe.json`. The first inventories bounded location metadata and tests one client account; `--users` performs only the two documented agency user-search reads against the saved agency context.
