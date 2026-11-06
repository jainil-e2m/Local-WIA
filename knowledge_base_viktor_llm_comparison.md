# Client Knowledge Base — API LLM, Viktor and hybrid comparison

Research date: **20 October 2026**. Updated after user review: **selective hybrid and Viktor-led retained as two implementation candidates**, with comparative testing required before selection. API-only remains a research comparator. No Viktor message, paid run, integration change, skill upload or scheduled task was executed.

## 1. User decision and the initial recommendation

**Retain selective hybrid and Viktor-led, then select based on tests.** The hybrid must include specific skill-based Viktor work and API LLM analysis where suitable, supplied with relevant business context. The Viktor-led candidate must demonstrate completeness against the specified skill-directed output formation. Validate costs for both. Neither is the selected winner; API-only is not a retained implementation candidate. See [KB-CH-41](knowledgebase_changes.md#kb-ch-41--retain-selective-hybrid-and-viktor-led-for-comparative-testing).

The initial research recommended an API-led owned record with selective Viktor reuse/work. That remains the hybrid design to assess, not the final selected route. Both candidates keep source evidence, defined calculations/validation, access enforcement and review in the owned KB. The user recalls **about $1,000/month** of Viktor spending across team DMs, preparation and proactive analysis. The invoice, plan/allowance, top-ups, task attribution, integration permissions and successful structured API outputs have not been inspected. Exact costs and comparative quality need a controlled evaluation.

The latest user report says Viktor currently prepares calls very well and catches Google/Meta configuration/performance issues missed by humans. Preserve those useful capabilities while optimising repeated low-value work. Earlier historical complaints must not be substituted for this current report of value.

The main saving is avoiding repeated work. An ordinary source API read does not require an LLM call. Likewise, extracting a title/date/status from structured source data does not need an agent. A 15-minute data refresh target does not mean asking an agent to reanalyse every client every 15 minutes.

The user provides **15–20 active clients**, growing to **30–40 active clients total**, development completion **6 November 2026**, and launch **26 November 2026**. The monthly cap is unknown; optimise expenditure while preserving required quality and performance. Those dates are targets, not a verified delivery estimate.

## 2. The three approaches

| Approach | Data intake | Interpretation and UI population | Main benefit | Main tradeoff |
| --- | --- | --- | --- | --- |
| **A. API LLM — research comparator** | Direct approved connectors; existing Viktor posts arrive through Slack as bot-authored records | Code maps direct fields/calculates measures; OpenRouter handles bounded semantic work. Display existing Viktor analysis with its author/date/citations. | Predictable control over evidence, permissions, schemas and model usage | Own connector maintenance and WIA-specific evaluation. It does not automatically inherit Viktor's integration access. |
| **B. Viktor-led — retained candidate** | Viktor tools fetch required records; preserve underlying source evidence and reusable reports | Versioned skills guide retrieval and analysis into required structured outputs; KB validates and stores accepted records | Reuses WIA's configured context and connected accounts; may reduce custom integration work | Full agent cost/latency, workspace permissions and available tools; required field and historical completeness must be demonstrated. |
| **C. Selective hybrid — retained candidate** | Direct connectors where suitable; existing reports reused; assess an integration bridge where useful | Specific skill-based Viktor jobs plus OpenRouter analysis with relevant business context; explicit division by task. Persist accepted results in the owned KB | Can combine working source paths with useful Viktor skills/context/access | Two routes need provenance and cost accounting. Avoid duplicate processing outside intentional comparison/review. |

All three still require the KB's database, source inventory, identity mapping, review queue, access enforcement, audit trail and responsive UI. Outsourcing interpretation does not supply those product responsibilities automatically.

## 3. What current documentation establishes

The product is **viktor.com**, not the unrelated engineering platform at viktor.ai.

| Capability | Documentation finding | WIA-specific status |
| --- | --- | --- |
| Programmatic orchestration | Paid public API supports asynchronous threads/runs, results and JSON Schema responses | Not tested with WIA's key or workload |
| Connected tools without an agent | Public API exposes integration/tool discovery and direct Python script execution | Required tools, authorisation, pagination and API-script billing need verification |
| Existing-SDK interface | The compatible API runs Viktor's complete agent behind familiar SDK protocols; it is not just one model invocation | Actual latency and credits unknown |
| Skills | Workspace skills use SKILL.md instructions and can carry scripts/reference files | WIA's actual skill contents and execution behaviour not audited |
| Scheduled scripts | The scheduled-task documentation explicitly describes script tasks as zero-credit; AI tasks consume credits | Verify the exact route, integration behaviour and bill. Do not assume API-triggered scripts have identical billing solely from the scheduled-task description |
| Usage measurement | Usage/balance endpoints and workspace usage views are documented | User recalls about $1,000/month; invoices, actual plan, usage breakdown and allowance unverified |

References: [Public API](https://viktor.com/docs/public-api), [compatible API](https://viktor.com/docs/chat-completions), [skills](https://viktor.com/docs/skills), [scheduled tasks](https://viktor.com/docs/scheduled-tasks).

Viktor's relevant advantage is its **configured business context, skills, tools and access**. Its agency material describes selecting among models and teaching agency processes. The reviewed material does not establish a proprietary model trained specifically for wedding-industry knowledge, or prove better results than a carefully configured API workflow. Compare outputs on WIA cases. [Agency description](https://viktor.com/for/agencies).

## 4. Existing Viktor data is immediately useful, with provenance

An offline inspection of seven preserved Slack channel JSON files found **nine text-bearing messages** from the previously identified Viktor author `U0BPF0MBD45`: six Dogwood and three Funktastic/DJ Hybrid. Openings include kickoff/pre-interview preparation, a strategy-call brief and a reported campaign check. This is evidence of real existing output, not complete portfolio coverage, live freshness or independently established correctness.

The [offline inventory](knowledge_base/wia-knowledge-base/verification/viktor/comparison_costs.json) retains archive pointers, message IDs, dates and limited excerpts. Existing source access remains as documented in [Slack scope](slack_scope.md).

Re-reading these posts through the KB's Slack connector does not start another Viktor agent run. There can still be KB processing/storage costs, and an optional model call to extract a structured interpretation. The original Viktor work already consumed whatever its actual workspace billing recorded.

Maintain distinct representations:

- **Original communication:** the actual human Slack/email message or meeting transcript, with its author, timestamp and source reference.
- **Viktor analysis:** the bot's own report or interpretation, preserving its reporting date and references.
- **Provider records returned through a bridge:** source IDs/fields/periods retrieved using authorised integration tools; reconcile their raw provenance before relying on them as primary records.

A statement in Viktor's prose that a client accepted work, a campaign changed or a payment settled must not be converted silently into a direct client statement or independent verification. Structured JSON makes a result easier to validate; it does not make its assertions true. Schema, client mapping, source citations and freshness each need checking.

Reusing a few reports does not satisfy complete historical backfill. Inventory and retrieve the obtainable records within the approved source/processing scope; document genuinely missing or unprocessed history for WIA sign-off. Do not replace that obligation with Viktor's recollection or latest recap.

## 5. Cost: account for the work, not only the vendor name

### Published price inputs

Viktor's plan documentation gives a current plan rate of **$25 per 10,000 credits**, or **$0.0025/credit**. Its public pricing advertises **$100/month for 40,000 credits**; the plan documentation also lists smaller plans and notes workspace-specific availability/legacy plans. Use WIA's actual billing rather than assume the public headline is its subscription. [Plans](https://viktor.com/docs/plans-and-credits), [pricing](https://viktor.com/pricing).

The credit guide illustrates quick tasks at **100–300 credits**, complex work at **500–1,500**, with actual work and caching affecting consumption. There is no universal per-CRM-read price established by those examples. [Credit guide](https://viktor.com/help/category/credits/how-credits-work).

For an illustrative API price range, current listed standard text rates are **$0.25 input/$1.50 output per million tokens** for Gemini 3.1 Flash Lite, and **$3/$15** for Claude Sonnet 4.6. These are cost examples, not selected production models or equal-quality benchmarks. [Fast-model example](https://openrouter.ai/google/gemini-3.1-flash-lite), [strong-model example](https://openrouter.ai/anthropic/claude-sonnet-4.6).

OpenRouter bills model inference at listed rates and charges credit-purchase fees: Standard 5.5%, Business 8%. The calculation below allocates the Standard fee proportionately; actual purchase minimums, account terms and taxes may differ. [Pricing](https://openrouter.ai/pricing).

### Controlled arithmetic illustration

Assume **one analysis per client/day over 30 days**, with **10,000 input + 1,000 output tokens per API analysis**. For Viktor use its published quick-task example of **100–300 credits/run**. These do **not** establish equal work/quality: an agent may retrieve data or take several steps while the fixed API payload is already prepared. This is a sensitivity comparison, not a monthly quote or proposed schedule.

| Clients | Monthly analyses | API fast-price example, fee allocated | API strong-price example, fee allocated | Viktor quick-task credit equivalent |
| ---: | ---: | ---: | ---: | ---: |
| 15 | 450 | $1.90 | $21.36 | $112.50–$337.50 |
| 20 | 600 | $2.53 | $28.49 | $150–$450 |
| 30 | 900 | $3.80 | $42.73 | $225–$675 |
| 40 | 1,200 | $5.06 | $56.97 | $300–$900 |

**Excluded:** hosting, provider/connector resource charges, historical backfill, embeddings, extra reasoning tokens, repairs/retries, minimum purchase fees, taxes, other Viktor workspace work and current subscriptions. Actual task complexity can fall outside the illustrative credit range. The cheap-model case is useful only if it passes the quality checks.

Credit equivalent is an allocation at the published rate, **not automatically new cash spend**. If WIA already pays for spare credits, some new work can fit its allowance; it still consumes shared capacity. If other automations use that capacity, top-ups or a plan change may be needed. Record total workspace spend and incremental KB-attributable work separately.

**The $2.53 fast-model illustration is not a replacement quote for WIA's approximate $1,000/month agent workload.** It prices 600 prepared prompts, excluding the rest of that workload. The recalled spend is a baseline to audit, not evidence of 400,000 included credits or a particular plan. Actual invoice savings may require fewer top-ups or a smaller subscription; consuming fewer included credits alone may leave the monthly bill unchanged. Plan changes can also change rate limits, so check throughput before reducing a plan. [Plan tiers](https://viktor.com/docs/plans-and-credits).

At 20 clients, an unconditional 15-minute per-client AI schedule would create **57,600 runs/month**, versus 600 in the daily illustration. This arithmetic explains why change detection, batching and reuse matter. It is not an argument to weaken the agreed refresh target: use deterministic refresh and only repeat interpretation when the task requires it.

### Formula for the real comparison

```text
API inference = (billable input tokens × input rate
               + billable output/reasoning tokens × output rate) / 1,000,000

Viktor allocation = measured incremental credits × effective account credit rate

Hybrid = inference actually performed + Viktor work actually performed
       + KB infrastructure and connector costs

Total cost of ownership also includes build/maintenance/review time.
```

Model input is billed when submitted unless actual provider caching applies. Keep reusable source facts/results in the KB, deduplicate changes, and pass sufficient relevant context rather than repeatedly submitting the entire archive. Measure actual cache hits and validation failures; do not remove required context just to reduce the token count. [Prompt caching](https://openrouter.ai/docs/guides/best-practices/prompt-caching).

### Optimising the recalled $1,000 baseline

| Existing work | Candidate treatment | What must remain intact |
| --- | --- | --- |
| Repeated DM questions about account facts, outstanding work and prior decisions | Answer from the shared, permission-aware KB once the relevant records are reliable | User-specific access and source freshness; do not assume private DM contents are an approved source |
| Repeated interpretation of unchanged material | Reuse validated prior results; send changed evidence through the chosen bounded analysis route | Relevant context, evidence and quality checks |
| Currently effective pre-call preparation | Reuse existing outputs and benchmark any replacement against WIA's current useful briefs | Call-type relevance, completeness and preparation timing |
| Google/Meta anomaly detection and optimisation | Keep existing valuable Viktor work while fresh paid-media retrieval remains outside this first release | Detecting the important issues; this KB release does not claim replacement parity |
| Integration-only reads | Compare direct APIs with a fixed authorised Viktor script/export | Historical completeness, access and source identifiers; verify actual script-route billing |
| Deeper ad-hoc recommendations | Keep the route that wins on measured usefulness/cost for those cases | Avoid forcing complex work onto an inadequate cheaper model |

Obtain admin-level aggregated usage by task/workflow before deciding what to change. Public APIs document workspace usage summaries; the usage UI provides thread/task detail. An audit of billing metadata is separate from reading team members' private conversation content, and the current Slack scope does not establish that content access.

For sensitivity only, 10%, 25% and 50% reductions of a $1,000 baseline correspond to **$100, $250 and $500/month before incremental KB expenses**. These are arithmetic examples, not savings forecasts. Net savings are the measured reduction in Viktor cash spend minus additional OpenRouter, Railway and operating costs. Retaining paid-media and complex advisory work can still leave a worthwhile residual Viktor bill.

Use the [offline calculator](knowledge_base/wia-knowledge-base/verification/viktor/comparison_costs.py) and [inputs/results](knowledge_base/wia-knowledge-base/verification/viktor/comparison_costs.json) to reproduce the table. No paid benchmark is represented by these files.

## 6. The important hybrid variant: Viktor as an integration bridge

Before paying an agent to repeatedly discover how to list records, assess whether a fixed authorised script can retrieve the required source fields and return/export them. The scheduled script route is documented as zero-credit, and the public API has a script-execution route. **The corresponding WIA capability and API-route billing must be measured, not inferred.** [Scheduled-task documentation](https://viktor.com/docs/scheduled-tasks).

This is especially relevant to LeadLock: direct agency discovery works, but our tested direct credentials cannot yet read the client outcome records. If WIA's existing Viktor connections expose those authorised records through suitable tools, a bridge may reduce new integration work. It is not proof that they do, a way around missing permissions, or a replacement for historical pagination and source reconciliation.

Compare two concrete paths on the same account/window: direct authorised LeadLock reads, versus the fixed Viktor-tool export. Check completeness, source IDs, fields, dates, latency, permissions, credits and maintenance. Use the cheaper maintainable path that satisfies the same requirements. Avoid simultaneous duplicate polling of both once a route is selected.

## 7. Selective hybrid candidate: proposed division of responsibilities

| Work | Recommended route to assess |
| --- | --- |
| IDs, account links, task status, calendar times, record pagination | Deterministic connector/code; evaluate a fixed Viktor bridge only where advantageous |
| Agreed conversions, periods, counts, ageing and duplicate rules | Code over reconciled source records |
| Extracting an explicit request or commitment from conversation | Bounded model interpretation with citations, unknowns and the agreed Needs review policy |
| Existing useful Viktor analysis | Read and retain through approved Slack intake with its original authorship, date and provenance |
| Specific skill-directed work assigned to Viktor | Versioned skill, required output fields, bounded authorised context/tools, source references and measured cost; evaluate completeness explicitly |
| KB record, evidence, history, access control, review, verification | WIA-owned backend/database; named WIA reviewers for Verified |
| UI rendering and refresh | Serve stored/validated records; do not start an agent run on each page load |

This hybrid must have a task-to-provider policy so the same extraction is not performed by two models routinely. Use a second route only for a deliberate evaluation, fallback or defined review case. Model selection should follow evidence of quality, not a low unit rate alone.

## 8. What directional skills and structured output can achieve

Versioned instructions can specify client/account IDs, allowed sources, source dates, reporting window/timezone, retrieval limits, output fields, unknown handling, citations and read-only behaviour. Viktor documents SKILL.md-based skills, and also background skill refinement; keep the approved instruction/schema versions in WIA's repository and record what a run used. Instructions are not an access-control boundary. [Skills](https://viktor.com/docs/skills).

A proposed result envelope should distinguish `client_id`, `engagement_ids`, `source_system`, `source_record_ids`, `as_of`, reporting window, retrieved facts, reported analysis, unknowns, coverage and supporting references. Reject unexpected clients, unauthorised sources and unsupported numeric assertions; do not coerce missing values to zero. Retain the raw result and run identity alongside accepted fields.

Viktor and compatible OpenRouter endpoints document schema-based output; validate again with the backend's own schemas and factual checks. Support varies by model/provider endpoint on OpenRouter. [Viktor compatible API](https://viktor.com/docs/chat-completions), [OpenRouter structured outputs](https://openrouter.ai/docs/guides/features/structured-outputs).

For first-release evaluation, keep source tools read-only and do not enable downstream task creation or notifications. Viktor's integration permissions can disable tools or require confirmation. A shared API key does not automatically inherit private user connections, and broader Viktor access does not grant KB users visibility. If a result mixes restricted client/module data, enforce the KB policy before presenting it. [Integration permissions](https://viktor.com/docs/integration-permissions).

## 9. Health & Sentiment: agreed scope and deferred additions

**Agreed scope after review:** assessment of the client engagement plus LeadLock lead-tracking data, with client feedback, delivery follow-through, support/resolution, lead handling and relevant onboarding/programme context where supported by evidence. Separate engagement/outcome views, evidence-based drivers and visible coverage are accepted. Commercial context and combined scoring remain for later review. This does not fix the feature's release position. See [KB-CH-42](knowledgebase_changes.md#kb-ch-42--evidence-supported-health--sentiment-additions-approved).

| Dimension | Useful evidence | Interpretation boundary |
| --- | --- | --- |
| Client voice and relationship | Explicit concerns, praise, changes in tone, unresolved questions; satisfaction surveys if located | Direct feedback differs from generated sentiment. Silence is not a satisfaction score. |
| Delivery and follow-through | Open commitments, agreed overdue dates, blocked work, unacknowledged asks, Done awaiting verification | Separate WIA obligations from client dependencies. Unknown deadlines are not overdue. |
| LeadLock outcomes | New inquiries, booked tours/consultations, won bookings, stage conversion, period comparisons | Agree stage/cohort/period/cancellation definitions. Contacts are not all leads or bookings. |
| Lead handling | Time to first response, uncontacted leads, stale opportunities and follow-up gaps | Requires appropriate activity timestamps/history; generic record updatedAt is not a contact timestamp. |
| Support and resolution | Issue severity, owner, ageing, repeated issues and confirmed resolution | Current support route and end-to-end resolution remain unverified. |
| Onboarding/programme context | Blocked milestones, missing inputs; agreed programme attendance where relevant | Sheet-reported attendance needs reconciled rules; calendar RSVP does not establish attendance. |
| Commercial context — deferred proposal | Evidenced signing/payment exceptions or upcoming renewal from verified terms | Not approved as a health dimension. Keep any future use separate and permission-controlled; a payment event does not prove current debt or overall satisfaction. |

Show **coverage, last refresh and unresolved source gaps alongside the assessment**, separate from client health. Use an engagement view and a lead/outcome view with explainable drivers; no combined percentage is approved. A client can be happy while conversion needs attention, or have strong outcomes while delivery promises remain open.

LeadLock outcome access is currently unresolved in the direct probes. Viktor's reports may be useful attributed analysis, but do not close that gap unless authorised underlying records can be reconciled. The user explicitly confirms that new first-release work stays within the eight approved sources: existing Viktor posts can be retained as attributed analysis, while fresh paid-media analysis is separately scoped. Do not turn existing ad-related posts into a claim of a live ad connector. See [LeadLock scope](leadlock_scope.md), [verification register](tobeverified_knowledgebase.md) and [deferred scope](Canbebuilt.md).

## 10. Delivery and cost feasibility

From the 20 October project date there are **17 calendar days to the 6 November development target**, followed by **20 calendar days to the 26 November launch target**. Staffing, source inventory, provider coverage and actual throughput are not established, so these dates cannot yet be certified as achievable.

The first release remains **Action Items and Client Portfolio with existing-task links**. ClickUp creation and external notifications are Coming soon. All approved sources' obtainable historical data still need the agreed processing and WIA gap sign-off. Later feature ordering remains open.

Keep a new untested Viktor dependency off the essential launch path until a small prototype passes. Reuse working direct connectors and existing posts first. A proven integration bridge can become the chosen route for a specific source rather than rebuilding it unnecessarily. This is a delivery-risk recommendation, not a claim that direct GHL or complete WIA Fathom coverage currently works.

Railway and the owned evidence store are needed in every route. Railway Pro currently has a $20 monthly subscription applied towards resource usage, with excess usage billed beyond the allowance. The KB's service/database/worker/storage footprint determines the bill; do not add the same base subscription twice when allocating shared account costs. [Railway pricing](https://docs.railway.com/pricing/plans).

## 11. What a controlled evaluation must establish

Compare the two retained candidates on authorised matching examples for a direct-field read, a new conversation commitment, a historical request later resolved and a client outcome snapshot. Give each path equivalent source access, reporting windows and business rules. Supply relevant business context explicitly and record its version. Compare required source/field completeness, client isolation, citations, exact output-contract compliance, handling of unknowns, end-to-end latency, human corrections and measured credits/tokens. Separately compare integration-only script routes against direct reads. The [feasibility study](knowledge_base/wia-knowledge-base/docs/Client-Knowledge-Base-Feasibility-Study.md#9-alternatives-we-considered) specifies the proposed criteria and cases; thresholds and execution budgets are not yet agreed.

No paid evaluation has been executed. Before any such run, define the exact requests, output schema, allowed read tools, run/retry limits and cost ceiling; inspect WIA's existing usage and API access. Creating a new Viktor task or posting a request is different from this public-document/offline research.

Remaining account-specific inputs: verify the recalled $1,000/month against the current plan/allowance and last-30-day invoices/usage/top-ups; identify which scheduled tasks already produce reusable outputs; verify whether API/team-key access reaches the required source connections; and measure script versus agent costs. These determine which retained candidate meets the required completeness/quality at the better end-to-end cost. No final winner is inferred from published unit prices.
