# Knowledge Base — requirements still ambiguous

Updated: 20 October 2026. Status: open.

This register records product questions that require a decision. Factual source/access checks are tracked in [tobeverified_knowledgebase.md](tobeverified_knowledgebase.md) and [tobeverified.md](tobeverified.md).

## KB-C-01 — Shopify purpose, metrics, and intake scope

### What is established

On 22 September at 16:48, Whitney mentioned one client with a different business model using Shopify and requested performance visibility. That statement establishes interest in the capability, but does not specify the client, desired measures, access arrangement, or delivery phase.

Source: [22 September transcript](WIA_Meeting_Analysis/meetings/2026-09-22_knowledge-base-scoping/source.md).

### Questions to resolve

1. **Which client and store?** Identify the WIA engagement and how Shopify relates to the work WIA delivers.
2. **What is success for this business?** Clarify whether the desired outcome is purchases, deposits/bookings, inquiries, subscriptions, or another business event. Do not apply an ecommerce revenue model solely because the client uses Shopify.
3. **What should the team see and act on?** Confirm the decisions this information should support in Client Profile, call preparation, account health, or a reporting view.
4. **Which measures and definitions?** Agree valid-order criteria, payment versus order dates, treatment of cancellations/refunds/discounts/tax/shipping, currency, period/timezone, and whether customer segmentation is useful.
5. **Is advertising attribution required?** If so, agree the attribution source, model, window and ad-spend inputs. Store sales alone cannot establish ad-attributed revenue or ROAS.
6. **What scope and timing?** Decide whether this belongs in the current Knowledge Base delivery or the later shared performance/reporting layer. No Shopify build commitment is established by this entry.

### Candidate intake if sales are the relevant outcome

These are proposals for discussion, not approved fields or verified API availability.

| Candidate data | Potential use |
| --- | --- |
| Order identifiers, dates, payment status and cancellation status | Count valid purchases and compare periods without duplicate orders. |
| Order values, discounts, refunds and currency | Produce a consistently defined sales measure and average order value. |
| Product/category breakdown | Explain which products/offers contribute to results where this informs WIA's strategy. |
| New versus returning customer classification, if reliably available | Distinguish acquisition from repeat purchasing without exposing unnecessary customer details. |

**Candidate output:** A concise sales-outcome snapshot with reporting period, definitions, source, refresh time, and coverage limitations. Display it only if the use case and source data support it.

### After clarification

Once the product questions are answered, verify store access, available fields/history, refund behavior, client mapping, refresh method and an example calculation. Record those checks in the verification register. Promote agreed requirements into [knowledgebase_changes.md](knowledgebase_changes.md) while preserving the decisions and evidence that resolved this ambiguity.

## KB-C-02 — API LLM, Viktor-led or hybrid responsibility split

**20 October decision:** Retain selective hybrid and Viktor-led as the two implementation candidates. The hybrid includes specific skill-based Viktor work and API LLM analysis supplied with relevant business context. Test required output formation/completeness and costs for both before selecting the suitable route. API-only remains a historical comparator. See [KB-CH-41](knowledgebase_changes.md#kb-ch-41--retain-selective-hybrid-and-viktor-led-for-comparative-testing) and the [comparison](knowledge_base_viktor_llm_comparison.md).

The final route/responsibility split remains subject to this evaluation, not an unanswered preference among three approaches. Set evaluation samples, thresholds and run budgets before execution. New first-release work stays within the eight approved sources; existing Viktor posts remain attributed analysis, and fresh paid-media work is separately scoped. The cost objective is optimisation without loss of required performance/quality. Approximately $1,000/month is a recalled baseline, not verified billing or a savings target. WIA's actual plan/usage and tested integration capabilities are factual checks in [KB-V-09](tobeverified_knowledgebase.md#kb-v-09--viktor-structured-orchestration-source-access-and-actual-cost).

## KB-C-03 — Health & Sentiment additions resolved; scoring/commercial context deferred

**Resolved, 20 October:** The user approves client feedback, delivery/follow-through, lead handling, support/resolution and relevant onboarding/programme context where supported by evidence, alongside engagement assessment and LeadLock tracking. Separate engagement/outcome views, evidence-based drivers and visible coverage are accepted. See [KB-CH-42](knowledgebase_changes.md#kb-ch-42--evidence-supported-health--sentiment-additions-approved).

Commercial context and combined scoring remain for later review. Source/metric readiness, including CRM history and attendance rules, remains verification work; approval of the dimensions does not establish available data or their release order.
