# Maintained Client Knowledge Base — architecture direction

## Product boundary

The maintained client knowledge base is an owned client-intelligence layer. Its primary surface is a dashboard for the WIA team. The user confirmed Action Items and Client Portfolio as the first-release priorities on 20 October; the 21 October sequence then activates Call Preparation in Stage 2, followed by Health & Sentiment, Invoices & Contracts and Overview in Stage 3. An in-platform chatbot is now scoped in [chatbot_KB.md](chatbot_KB.md), with delivery order left to implementation planning and source-freshness/provider routing subject to testing. External ChatGPT/Slack delivery remains later; the system of record stays in the owned KB.

## Confirmed feasibility-discovery decisions — 20 October 2026

- Action Items and Client Portfolio can ship together or in subsequent weeks as implementation and testing complete. Exact release content and timing remain to be defined.
- The frontend is the intended experience, subject to field-level evidence requirements, explicit unavailable states and proposed adjustments for review.
- Maintain KB records and propose actions; a WIA user reviews before ClickUp creation or an external notification. Include relevant ClickUp tasks and explicit Slack/email/meeting requests and commitments. AI improvements remain labelled proposals.
- Existing active tasks and clear current commitments enter the active register. Ambiguous, potentially stale and AI-suggested items go to Needs review; unknown owners/dates remain unknown. Done records reported completion from a mapped task or explicit delivery evidence; Verified requires a named WIA reviewer to record the follow-up check and evidence.
- A WIA operations reviewer coordinates Needs review, relevant account owners resolve client-specific items, and E2M handles technical ingestion issues. Names remain to be supplied.
- Acknowledgement combines explicit acceptance by the identified owner in a source message, the owner's KB Acknowledge action and a custom allowlist of owner reactions. The admin configures emoji/meaning pairs; reaction-based acknowledgement stays disabled until WIA configures them. No default map is approved; ambiguous cases go to review.
- Each client profile represents a business, with separate service engagements and linked contacts/accounts. Meetings can link to several businesses.
- All currently active WIA clients across services must have all obtainable history from every approved in-scope source backfilled before launch, even when its frontend feature is Coming soon. Former-client archives are a separate scope decision. WIA must sign off a source-by-source gap report; inaccessible items remain unresolved until explicitly accepted or recovered. Process readable text, native Docs/Sheets, existing transcripts and extractable PDF/DOCX text. Keep scans, images and audio/video as links, disclosing unprocessed content in the gap report; no OCR or new transcription. The actual roster, parser coverage and completion checks remain to be verified; no recent-window-first launch was approved.
- Fill available Client Portfolio information and mark later features Coming soon. The user clarified that these labels do not need phase timelines. The three-stage tab sequence is agreed in KB-CH-69; unlisted capability sequencing remains open; preserve unavailable/missing-data states separately from delivery gates.
- Fifteen-minute updates are sufficient once provider data is available, with visible last-sync times and on-demand refresh where supported. Existing webhook/push directions remain; end-to-end freshness still needs implementation and testing.
- Use a custom access model with per-user admin show/hide controls for clients and whole modules/sections in the first release; individual-field controls come later. New users receive a custom standard team access profile that admins may restrict/expand. WIA has not yet specified its client/module grants or operation permissions; configure them before user activation rather than assume either proposed profile. Enforce restrictions across backend data, evidence and generated content supplied to each user.
- WIA adds new clients manually. After their profile and source mappings are created, automate ingestion/backfill; do not automatically activate profiles from source events.
- Launch acceptance covers the suggested client matching, complete agreed backfill/gaps, citations, unknown fields, stale-action review, Done/Verified, access and fifteen-minute update checks. The user additionally requires responsive UI on phones, tablets, laptops, MacBooks and iMacs. The exact test matrix, measured thresholds, numeric business-improvement targets and WIA sign-off owner remain to be defined; source API reads alone do not establish acceptance.
- Use Railway and OpenRouter in WIA-owned accounts, keeping the existing frontend and FastAPI backend SOP as constraints. Assess KB-specific storage, queues, access and costs; validate source volumes, provider prices, service topology and model choices for the KB.
- Architecture Q1–Q4 select reuse of the existing Command Center email/password authentication system, with KB-admin API provisioning of central accounts and KB-managed access, a dedicated KB Railway project/data services, and persistent extracted facts/excerpts with authorised on-demand retrieval of full originals. The supported provisioning API must be established or built; it is not verified by current inspection. Persist provenance/version/coverage metadata; do not retain a complete source archive indirectly through search chunks or logs. Detailed reprocessing depends on original availability. These choices do not change full historical processing or select chatbot live-read mode.
- Architecture Q5/Q7 preserve reviewed KB corrections and route later conflicting source updates for review, with per-user read/unread indicators and separate conflict status. Opening details or Mark as read clears the viewed change for that user; later changes become unread again. Reading is separate from resolving a conflict or acknowledging an action.
- Architecture Q8–Q10/Q13 select custom roles plus per-user Inherit/Allow/Deny editing/review overrides and admin-configurable self-verification. User Deny wins over role grants; Allow stays within the user's permitted clients/sections. Visibility or account ownership alone does not grant editing/review rights. Owners who verify their work still need normal verification authority, self-verification permission and a named follow-up check with evidence. Actual role/default grants remain to configure.
- Architecture Q11 selects immediate KB-only revocation, leaving the central login active; central disabling is separate. A central session cannot bypass revoked KB membership. Apply current authorisation to pending results, citations, history, chat and exports.
- Architecture Q12 selects assessing one-hour maximum lost KB changes and four-hour restoration after serious database failure, subject to tested recovery and costs. Backup methods/retention, response coverage and recovery ownership remain to design; these are not current guarantees. Restore must preserve reviewed state and reconcile access restrictions before reopening.
- Architecture Q14 selects limited real-client fixtures in isolated staging with separate test credentials/configuration and no source writes. Q17 confirms full testing-data access for both E2M and WIA and closes the support-access question as unnecessary. Prepare representative fixtures and evaluation limits without an extra client-by-client access gate; production's full-backfill requirement is unchanged.
- Architecture Q15 selects private user chatbot threads and admin operational-metadata access only. Production admin inspection of conversation content is excluded for now, including through logs/traces/cache inspection; sharing/content inspection are later possibilities. Q16 selects admin-configurable category retention, with actual durations still to configure. Both teams' full testing access does not change that production UI policy.
- Architecture Q18 supplies a baseline of about ten WIA users, all potentially simultaneous, with headcount able to increase/decrease. Test UI/chat use alongside ongoing intake/backfill and measure capacity/cost; no exact future count or latency threshold is supplied.
- Architecture Q6 retains facts/excerpts after confirmed upstream deletion with a visible deleted-source warning. Keep permitted search/chat/citations warning-aware; refresh dependent cached answers rather than automatically withdrawing evidence. Distinguish retained historical support from proof of a current mutable state and confirmed deletion from temporary access loss. Exact retention periods remain open.
- Activate Stage 1 Action Register + Client Portfolio; Stage 2 Call Preparation; Stage 3 Health & Sentiment + Invoices & Contracts + Overview. Chatbot and unlisted capabilities remain unsequenced. First-release external actions are existing-task links only; ClickUp creation and external notifications are Coming soon, with WIA review still required when delivered.
- Health & Sentiment assesses engagement and LeadLock outcomes, adding client feedback, delivery follow-through, support/resolution, lead handling and relevant onboarding/programme context where supported by evidence. Show separate engagement/outcome views, evidence-based drivers and visible coverage. Commercial context and combined scoring remain deferred; source access and metric definitions are still unverified.
- Keep the eight approved source boundaries, including new first-release Viktor requests. Website research, ChatGPT imports and separate uploads remain later proposals. Existing approved Drive material is included. Existing Viktor posts can be retained as attributed analysis; fresh paid-media analysis is separately scoped.
- Retain selective hybrid and Viktor-led as the two implementation candidates. Hybrid includes specific skill-based Viktor work plus API LLM interpretation with relevant business context. Compare required output formation/completeness, evidence, access, quality, latency and cost before choosing. API-only is a research comparator. Both require the owned KB record and controls. Do not treat candidate approval or public-document research as a completed API test.
- Scope a chatbot for questions about displayed records and permitted client evidence, meetings, actions, context and assignments. Test KB-only versus controlled live-read modes before choosing. Assess exact KB queries/API synthesis with selective Viktor skills, preserving permissions and source authority. Chat routing is separate from background ingestion selection; delivery order remains open. No chatbot runtime or new paid evaluation is established by the scope.
- Conserve chatbot cost with safe cached/repeated-query reuse, FAQ/direct-answer patterns and bounded generation while meeting QA. The scope proposes dependency-aware invalidation, approved definitions and dynamic templates, conservative intent matching, code-based checks and cache-on versus bypassed-reference evaluation. No TTL/semantic threshold or measured saving is approved/proven; source freshness and permissions apply on every hit.
- Planning inputs: 15–20 active clients, growth to 30–40 total; development target 6 November 2026 and launch target 26 November 2026. Monthly cost cap is unknown; optimise while preserving required quality/performance. Volume/staffing/access analysis is still needed to validate the dates.
- The user recalls approximately $1,000/month of Viktor spend across individual team DMs, preparation and proactive analysis, and reports valuable current call preparation and ad-anomaly detection. This is reported context, not verified billing. Assess repeat-work reduction and reuse while preserving useful workflows; do not claim the first-release KB replaces deferred paid-media monitoring or assume private DMs are approved intake.
- Resolve conflicting information by field and evidence type, retaining both sources and escalating material ambiguity for review. Meeting commitments still take precedence over conflicting ClickUp due dates; conversations do not automatically change signed terms or payment state.

- Architecture Q19 selects version-controlled AI prompt/skill/routing changes with evaluation before release; business settings remain admin-configurable.
- Architecture Q20 retains supported last-known data during source failure/lag with an explicit last-sync date/time and stale/unavailable warning. Failed attempts/cache hits do not reset successful sync time.

- Technical Q21 selects SQLAlchemy ORM with psycopg and Alembic. Q22 permits resolvers to apply audited corrections while other editors propose. Q23 automatically reopens a genuinely reopened mapped ClickUp action and supersedes prior verification without erasing history or overwriting unrelated corrected fields.

These latest user decisions supersede the earlier release sequence. See [agreed changes](knowledgebase_changes.md), KB-CH-05 through KB-CH-69. The [feasibility study](knowledge_base/wia-knowledge-base/docs/Client-Knowledge-Base-Feasibility-Study.md) records conditional feasibility and the two-candidate evaluation. This direction file is not a final architecture or an implementation claim.

## Scope clarifications — 19 October 2026

- The user confirms Fathom is used for all meetings going forward. Historical Zoom material remains relevant: the 22 September call confirms recordings/transcripts were downloaded into client Drive folders, while transcripts and summaries were retained in Zoom. Drive/local exports can support backfill; archive completeness and access still need checking.
- [fathom_scope.md](fathom_scope.md) records API feasibility. The 20 October correction found a duplicate environment key: the WIA key was overridden by the E2M key. The WIA key now retrieves known The Penny/Ridgefield calls and a Carmen-recorded office-hour transcript/summary; basic production samples and recorder-filter examples are verified. The duplicate was resolved while preserving both values. Complete client/recorder/history coverage, webhook delivery, playback and actual attendance remain unverified. Future intake uses the webhook with API backfill/reconciliation.
- [clickup_scope.md](clickup_scope.md) records successful read access to WIA's workspace and 338 task samples across five client/programme lists. Ownership, dates, state and role/phase fields support commitments and preparation, with unknown-date/owner and workflow exceptions preserved. Its linked attendance sheets were subsequently read in the Drive review; ClickUp task completion itself does not establish acknowledgement, verified delivery or attendance.
- [gmail_scope.md](gmail_scope.md) and [google_drive_scope.md](google_drive_scope.md) now verify the WIA mailbox/account, 42 successful source reads and OAuth refresh. Real Dubsado signing/payment events, client replies, questionnaires and dated sheet attendance support the planned intake. Gmail will use Pub/Sub push delivery and Drive a changes-watch HTTPS receiver; actual notification delivery, renewal/recovery and full archive/attendance semantics remain untested.
- [google_calendar_scope.md](google_calendar_scope.md) verifies Calendar access after API enablement: 13 successful GETs, nine subscribed calendars and event samples from five calendars, including real upcoming client calls. Scheduling supports the queue and next-call cards; client/host matching, copy reconciliation, complete historical coverage and change delivery remain open. Calendar RSVP does not establish attendance, and call-brief business content requires the other sources.
- [knowledgebase_changes.md](knowledgebase_changes.md) records agreed Client Profile additions: the LeadLock account link, support issues, and a lead-outcome snapshot. It also records Dubsado signing/payment event intake, including the Gmail notification route.
- [tobeverified_knowledgebase.md](tobeverified_knowledgebase.md) tracks survey location, support intake, and lead-outcome data readiness. [tobeverified.md](tobeverified.md) tracks the unresolved meaning of GHL pricing/billing information.
- [tobeclarified.md](tobeclarified.md) records Shopify's still-undefined use case and candidate data. Shopify is a proposed source, not an agreed detailed integration. The later Google Ads/Meta intake remains deferred as recorded in [Canbebuilt.md](Canbebuilt.md).

## First-release direction — scope refinement pending

1. Action Items: relevant tasks and explicit current requests/commitments, proposals visibly separate, WIA-coordinated Needs review, unknown owners/dates preserved, hybrid owner acknowledgement and Done/Verified evidence as agreed. Existing-task links ship first; ClickUp creation and external notifications are Coming soon.
2. Client Portfolio: business-level records and linked service engagements, populated with available evidenced information. Later features are marked Coming soon without phase timelines on the labels.
3. Complete obtainable historical backfill across every approved in-scope source for all active clients before launch, including data for later UI features, with WIA sign-off on the source-by-source gap report. Process readable content/existing transcripts and extractable PDF/DOCX text; scans, images and audio/video remain linked with unprocessed content disclosed. Former-client archive scope is separate.
4. Evidence and explicit unknown/unavailable states throughout. Human review precedes external task creation or notification. Use client/module/section visibility controls, the configured standard team profile and visible sync freshness; target fifteen-minute updates and supported on-demand refresh.

Call preparation remains an overall requirement: calendar-linked calls, call-type-specific context, client asks, suggested agenda and cited opportunities. Call Preparation activates in Stage 2; Health & Sentiment, Invoices & Contracts and Overview activate in Stage 3. Chatbot and unlisted capabilities remain unsequenced. Portfolio information is populated where available and supported; health, attendance, finance and lead-outcome feature delivery can be gated as Coming soon without displaying timelines. Health assessment includes the evidence-supported additions confirmed in KB-CH-42. Gather obtainable historical data before launch where the source is already approved and in scope.

## System shape

```text
Sources → ingestion + normalization → client ledger → evidence store
                                        ↓
                           insight / opportunity jobs
                                        ↓
                           briefing API + action register
                                        ↓
                         dashboard / future ChatGPT / Slack
```

### Sources to normalize

The evidence store retains facts, supporting excerpts and provenance/coverage metadata. Full originals are fetched through approved connectors when needed; the diagram does not imply a permanent full-text archive. Search and chatbot answers must disclose gaps in retained context and source availability.

- Google Calendar → event, attendees, client, call type.
- Fathom for all future meetings; historical Zoom transcripts/summaries and Drive archives → conversation, decisions, asks, sentiment, commitments.
- Drive client folders → onboarding, questionnaires, approved documents, recordings/transcripts.
- Email and Slack → client signals, open loops, decisions, acknowledgements.
- ClickUp → task state, owner, due date (a later meeting wins over a stale due date).
- Dubsado signing/payment information, including notifications to hello@weddingindustryads.com → evidenced commercial events; full terms require the underlying agreement. GHL pricing/billing meaning remains to be verified.
- Client LeadLock/GHL sub-accounts → agreed Client Profile account references and lead-outcome snapshots, subject to access and metric-definition checks. Ad spend/CPL/attribution require the appropriate additional sources.
- Google Ads and Meta → later performance/reporting integration; Shopify purpose and fields remain to be clarified.
- Surveys and LeadLock support → satisfaction and escalation signals; actual source location and intake coverage remain to be verified.

### Core entities

`Client` (business), `ServiceEngagement`, linked contacts/accounts, `SourceDocument`, `Conversation`, `CallEvent`, `MetricSnapshot`, `Insight`, `Opportunity`, `ActionItem`, `EvidenceCitation`, `User`, and `ConnectorAccount`. Shared evidence can link to multiple businesses/engagements.

All derived objects retain `sourceIds`, `observedAt`, `confidence`, and `status`. A meeting commitment takes precedence over a conflicting ClickUp due date. Other conflicts use rules by field and evidence type, retain both sources and route material ambiguity for human review; a conversation does not automatically amend signed terms or payment state. Detailed field rules remain to be defined.

## Frontend information architecture

- **Home / Client Intelligence:** portfolio health, today's call queue, open loops, weekly focus.
- **Call brief:** call-type-specific briefing with performance, sentiment, opportunities, asks, agenda, and evidence.
- **Client record:** longitudinal timeline from sales → onboarding → strategy, connector snapshots, and open actions.
- **Action register:** owner, due date, acknowledgement, verification, and escalation.
- **Source explorer:** searchable, permission-aware source material with citations.
- **In-platform chatbot:** contextual questions about permitted client/action/meeting data, citations and follow-up conversation; scope in [chatbot_KB.md](chatbot_KB.md), delivery and tested execution choices pending.
- **Admin / connectors:** ingestion freshness, mapping exceptions, access health, and audit log.

## Delivery phases

- **First-release priorities:** Action Items and Client Portfolio, together or in subsequent weeks according to implementation and testing. Full obtainable in-scope historical backfill for all active clients and WIA gap-report sign-off are required before launch. Populate available portfolio information; explicitly label later-phase features Coming soon.
- **Subsequent tab activation:** Stage 2 Call Preparation; Stage 3 Health & Sentiment + Invoices & Contracts + Overview. Chatbot, opportunities and other unlisted feature depth remain open. No new dates are assigned, and all obtainable in-scope history is still required before first launch.
- **Chatbot sequencing:** scope now, with delivery order decided during implementation planning. KB-only versus controlled live reads and specialist routing remain evaluation choices; this does not change first-release commitments.
- **Existing deferred scope:** connector-backed paid-media reporting and proactive performance anomaly detection; conversational access through ChatGPT/Slack. No new dates or sequence have been agreed for these capabilities.

## Later content integrations

Using client transformation history for future success-story or case-study integrations is outside the current KB delivery scope.

## Decisions still needed

Architecture discovery is now tracked in [Client-Knowledge-Base-Architecture-Discovery.md](knowledge_base/wia-knowledge-base/docs/Client-Knowledge-Base-Architecture-Discovery.md). It records KB-specific mechanisms and clarification history; it is not a selected final topology.

WIA-configured acknowledgement mappings and remaining action workflow details; active-client roster, parser coverage and backfill completion checks; test matrix and sign-off owner; implementation-stage feature sequencing; call-brief presentation; tested freshness behaviour; health metric definitions and deferred commercial/scoring decisions; configured standard team-profile grants and operation permissions; hybrid versus Viktor-led evaluation/selection and measured billing/quality; detailed field-authority/review rules; source permissions; KB-specific infrastructure/model/cost evaluation and deadline feasibility; and the access/revocation plan for shared accounts.

## Full architecture draft

The [Client Knowledge Base Solution Architecture](knowledge_base/wia-knowledge-base/docs/Client-Knowledge-Base-Solution-Architecture.md) develops the first full engineering draft using KB requirements and decisions through Architecture Q23. Recommended topology, test-dependent provider/chat choices and required configuration remain explicitly identified.

The [technical-depth audit](knowledge_base/wia-knowledge-base/docs/Client-Knowledge-Base-Architecture-Technical-Gap-Analysis.md) records the first draft's 22 detail gaps and the expanded revision's coverage. New algorithms/schemas/configuration are engineering specifications/proposals, not implemented QA results.
