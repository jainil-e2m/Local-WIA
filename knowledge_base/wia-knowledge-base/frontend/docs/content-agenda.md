# Client Knowledge Base: content agenda

Reviewed 21 October 2026; preview notes updated 26 October 2026. This is a working map for content/UI refinement, not a change to the agreed requirements or a claim that the backend exists.

## Product purpose

Give the WIA team a maintained, evidence-backed understanding of each client business: who they are, what WIA is delivering, what changed, what each side owes, what needs attention and how to prepare for the next conversation. Reduce repeated reconstruction of context across source tools and preserve continuity during handovers.

One client represents a business, with separate service engagements and linked people/accounts. The intended users are WIA team members with configured access. This is not an external client portal.

The current application is a frontend preview with six fictional businesses, dated 9 October 2026. Actions persist locally. It does not implement live ingestion, authentication, AI, permissions, production review/verification or financial reconciliation.

## Agreed activation sequence

1. Action Register and Client Portfolio.
2. Call Preparation.
3. Health & Sentiment, Invoices & Contracts and Overview.

Chatbot and unlisted capabilities have no selected delivery position. When the chatbot (Client 360) ships, it is a single sidebar view with no per-page entry points (06-chatbot.md, N2 revised 22 Oct). All obtainable approved-source history for active clients still needs processing before first launch, including evidence for later views. Feature availability and evidence availability are different states.

## Main workspace sections

| Section | Question it should answer | Content and refinement boundary |
| --- | --- | --- |
| Action Register | What needs doing, by whom, by when, and on what basis? | Actual ClickUp tasks and explicit current requests/commitments; WIA versus client responsibility; owner, deadline, acknowledgement, progress, evidence and review. Keep ambiguous/stale items and AI proposals in Needs review. Done records supported completion; Verified requires a named authorised follow-up check with evidence. |
| Client Portfolio | Which businesses are in our care, and where should I look next? | Business identity, contacts, service engagements, supported current context, shared action counts, next interaction and coverage. Search/filter/card/list views must describe the same records. WIA creates clients manually before mapped ingestion. |
| Call Preparation | What do we need to know and resolve in this scheduled conversation? | Correct calendar occurrence, client, purpose, host/timezone, current position, relevant previous discussion, suggested agenda, established client asks, current commitments, supported opportunities and citations. Show readiness, age and missing context; suggestions are not commitments. |
| Health & Sentiment | How is engagement going, and what explains that assessment? | Client feedback, delivery follow-through, support resolution and relevant programme context. Show separate supported lead-handling/outcome information, drivers, periods and coverage. No agreed combined numerical health score; paid-media monitoring is deferred. |
| Invoices & Contracts | What commercial terms and payment events can the evidence establish? | Signing, terms, invoices, payments and actual sent reminders linked to the right engagement. Dubsado notifications enter through Gmail. Use events-only presentation if ledger/balance reconciliation is insufficient. Conversations do not establish payment or amend signed terms. |
| Overview | What should I pay attention to today? | Shared portfolio/action indicators, today's matched calls, next brief and its actual readiness, explainable client-attention flags and an attributed client quotation where supported. Derived content must agree with its underlying modules. |
| Source Library / evidence drawer | What exactly supports this claim? | Retained excerpt, author/speaker, source date/version, locator, linked client/record and coverage/deletion/access limitations; authorised original reference where available. Excerpt count is not historical completeness. |
| Connections | What is connected, how current is it, and what is missing? | Registered account/capabilities, last successful sync, lag, processing/backfill status and distinct blocked/partial/unsupported states. Connection health is separate from client relationship health. |

## Sections within a client record

| Section | Content responsibility |
| --- | --- |
| Now | The supported current picture, immediate priority, shared open/overdue/client-dependent actions, next call and record limitations. Summary/focus publication rules still need definition. |
| Client profile | Business background, audience, differentiator, voice, goals, contacts and separate engagements; reviewed LeadLock account link, supported support issues and period-based lead outcomes. Use field-specific evidence. |
| Engagement history | Dated onboarding, communication, meeting, commitment and delivery events in spine/feed views. Distinguish engagement start, earliest evidence and processed-through date. Empty periods do not prove inactivity. |
| Handover brief | Supported business background, current position, outstanding obligations and gaps, with snapshot/evidence and permitted copy/export. Reuse maintained records. |
| Commitments | The same canonical actions as the global register, scoped to the business/engagement, with WIA obligations and client dependencies. |
| Meetings | Relevant past discussions, decisions and resulting actions; reconcile Calendar/Fathom/historical Zoom representations. Preserve known meetings with unavailable transcripts. Shared meetings can concern several businesses. |
| Invoices & terms | The client/engagement subset of the shared commercial records, with the same authority, evidence and permission boundaries. |
| Attendance | Applicable programme sessions, supported attendance, holds/reschedules and missing/conflicting records. An invitation or absent transcript is not attendance evidence. |

## Supporting workflows that are broader than the preview

- Review: identity/mapping ambiguity, stale work, missing fields, proposals and material conflicts. Editors propose; authorised resolvers apply audited corrections. Source refresh must preserve reviewed decisions.
- Change awareness: per-user read/unread for the viewed change revision, separate from action acknowledgement, verification and conflict resolution.
- Administration: central-login-linked KB membership, client/module visibility, roles and operation overrides, acknowledgement mappings, retention and audited changes. Revoking KB membership leaves the central account separate.
- Planned chatbot: private, permission-aware questions across records and evidence; exact queries and safe dependency-valid reuse before bounded generation. Evidence, unknowns and current access apply to every answer. KB-only versus controlled live reads remains test-dependent; semantic full-answer replay is initially disabled.

## Content rules across every surface

- Distinguish direct statements, maintained facts, calculations, interpretations and proposals.
- Preserve unknown owners/dates and missing, partial, unavailable or not-applicable evidence. Do not fill them with invented values or unsupported zeros.
- Show last successful sync/as-of information. A refresh, cache hit or failed read must not make data appear newer.
- Keep existing tasks and clear commitments separate from review candidates; assignment is not acknowledgement and Done is not Verified.
- Prefer a meeting commitment over a conflicting ClickUp deadline while retaining the discrepancy. Other fields follow their evidence/authority rules.
- Keep client/module permissions effective across evidence, history, search, generated content and exports.
- Link existing ClickUp tasks first. External task creation and notifications remain Coming soon.
- Approved intake: Gmail, Slack, ClickUp, historical Zoom, Fathom, Drive, LeadLock and Calendar. Existing Viktor posts are attributed analysis. Website research, separate uploads, ChatGPT imports, Shopify and new paid-media analysis are outside current intake.
- Process obtainable readable history and existing transcripts; no OCR or new transcription. Retain facts/excerpts/provenance rather than silently building a permanent full-source archive.

## Important differences to address during refinement

The mock still exposes every section and starts at Overview; that is not the agreed production activation sequence. Its wording and illustrative controls are not the final business contract.

Several sections now have a second layout under review beside the original (badged in the sidebar): Action Register (Revised board/list, and v2 · Teams with per-client visibility), Call Preparation v2, Health & Sentiment v2, and a condensed Invoices & Contracts that has replaced the original. The variants share one dataset. A layout is not a decision until the matching tab scope doc records it.

Changes already reflected in the mock (26 Oct):
- **Preview accounts:** chosen from the sidebar account menu, opening as Whitney; pages follow that person's role defaults.
- **Client 360:** sidebar view only; the header button, shortcut, side panel and *Ask about this* links are removed.
- **Action Register:** "Team" grouping for admins only; Client grouping shows only what clients owe; the workload panel and bulk *Reassign all* are removed (owner changes happen per action). The revised layout adds priority, reopen and deadline-change requests that admins approve instead of snoozing.
- **Client Portfolio:** logo cards. Logos are meant to come from the Drive brand folder or the contact's email signature, never the website; the preview's logos are fictional.
- **Invoices & terms (client record):** condensed to a standing line, invoices beside agreements, and one activity timeline. Alert-only records show *Can't confirm yet* rather than *Up to date*.

Still open from the original review: the profile has one contact shape and a shared background citation. Actions allow simple acknowledgement and verification toggles without production authority or evidence. Health v1 uses fictional qualitative badges; v2 keeps mood and delivery separate with no combined score. Finance uses a fictional ledger unless built with `export:live`. Attendance is generated from sample dates. Connections and preferences are demonstrations. Review, admin and permission screens are not fully implemented.

Business definitions still needed include activity and coverage measures, lead stages and cohorts, health rules, attendance calculations, stale-action and manual-entry policies, narrative publication, financial completeness, **priority (High / Medium / Low has no agreed meaning yet)**, account-team membership for per-client visibility, and who reviews completed work.

## Requirement references

Authoritative records in the surrounding workspace:

- [Functional requirements](../../docs/functional_requirements.md): observable behaviour for every section and supporting workflow.
- [Solution architecture](../../docs/Client-Knowledge-Base-Solution-Architecture.md): records, source mappings, permissions, evidence and proposed backend mechanics.
- [Agreed changes through KB-CH-69](../../../../knowledgebase_changes.md): decisions and activation sequence.
- [Architecture direction](../../../../MAINTAINED_CLIENT_KNOWLEDGE_BASE_ARCHITECTURE.md): product boundaries and source scope.
- [Chatbot scope](../../../../chatbot_KB.md): contextual answers, evidence, private threads and cost/QA methodology.

The frontend implementation is in `src/views/`, with shared actions/navigation in `src/App.tsx`, sample records in `src/data.ts` and contracts in `src/types.ts`.
