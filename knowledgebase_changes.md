# Maintained Client Knowledge Base — agreed changes

Updated: 20 October 2026.

These are product changes requested by the user during scope review. They are documented requirements, not implemented features or proof of live source access. The existing Knowledge Base remains a frontend preview with fictional data.

## KB-CH-01 — LeadLock account reference in Client Profile

**Decision:** Add a link to the client's LeadLock/GHL sub-account in the **Client Profile** tab.

- Store the client-to-sub-account association, including a stable account/location identifier where available, and the account URL.
- Display the account name and an “Open LeadLock account” link so the team can reach the correct account from the client record.
- Use the association to match future source records to the correct client. Confirm ambiguous mappings before importing records.
- A stored link establishes a reference; it does not establish authenticated API access, data coverage, or synchronization.
- For a client who does not use LeadLock, show that it is not applicable. For an unknown account link, show that it needs confirmation.

**Review check:** The Client Profile opens the correct client's account; missing or unresolved mappings are visible rather than guessed.

## KB-CH-02 — Support requests and unresolved issues in Client Profile

**Decision:** Add visibility of client support requests and unresolved issues alongside the account reference in the **Client Profile** tab.

The intended record should include the issue summary, source link, raised date, latest update, owner where known, current status, and next action. Distinguish a reported resolution from a verified resolution where supporting evidence exists.

- Link issues to the relevant client and preserve the source communication.
- Make unresolved issues available to call preparation and client-health assessment.
- The source may be the LeadLock support mailbox, a ticket form, a maintained GHL pipeline, or linked Slack/email communication. The ingestion route is not yet verified; see [KB-V-02](tobeverified_knowledgebase.md#kb-v-02--support-intake-route-and-coverage).
- Do not infer that no issues exist merely because the source is unavailable or has not been synchronized.

**Review check:** An issue can be traced to its original request, and the team can distinguish open, resolved, and unverified states.

## KB-CH-03 — Lead-outcome snapshot in Client Profile

**Decision:** Add a concise lead-outcome snapshot to the **Client Profile** tab for clients whose LeadLock/GHL records support it.

| Proposed display | Definition required before implementation |
| --- | --- |
| New inquiries in the reporting period | What counts as a new inquiry, date field, and duplicate treatment. |
| Tours or consultations booked | Which appointment types/stages count, including cancellation and rescheduling treatment. |
| Won/booked clients | The client's accepted business-outcome definition and the evidence that marks it achieved. |
| Conversion between pipeline stages | Mapped stages, denominator, period, and whether the measure follows a cohort or activity within a period. |
| Stalled inquiries or follow-up gaps | A client-specific inactivity/follow-up rule supported by available timestamps and activity records. |
| Period, source, and last refresh | Visible reporting boundaries and source freshness for every snapshot. |

This is a summary of the WIA client's prospect and booking outcomes. It is distinct from invoices the WIA client pays to WIA. Individual prospect records should be exposed only where needed to explain a relevant exception.

**Reason:** Whitney asked for visibility into ad-generated leads becoming booked clients on 22 September at 36:44. The snapshot supports preparation, opportunities, and account health.

**Dependencies and scope:** The addition to Client Profile is agreed. Live population still requires sub-account access, client mapping, metric definitions, and coverage checks; see [KB-V-03](tobeverified_knowledgebase.md#kb-v-03--lead-outcome-data-and-account-access). Attribution to advertising must be evidenced. LeadLock data alone does not establish ad spend, CPL, or ROAS. This decision does not activate the deferred Google Ads/Meta performance intake in [Canbebuilt.md](Canbebuilt.md).

**Review check:** Every displayed measure is reproducible from a defined source and period. Missing or incomplete data is shown as unavailable/partial rather than zero.

## KB-CH-04 — Dubsado signing and payment event intake

**Decision:** Use Dubsado information for contract-signing and payment events. One intake route is the Dubsado notification emails received at **hello@weddingindustryads.com**, using their subject, body, and URLs.

**19 October live-source verification:** OAuth access to the intended mailbox is now verified. Actual Dubsado signing and payment emails for the same project label were read, including a reported 1,400.00 USD payment and contract/invoice links. This confirms the subject/body/URL event-intake route, not full contract terms or an invoice's current settled balance. Linked Dubsado records were not opened. Sent reminders and a draft client reply also occur in the mailbox and require separate treatment. See [Gmail scope](gmail_scope.md) and [event evidence](knowledge_base/wia-knowledge-base/verification/gmail/local_audit.json). The frontend remains a mock; no financial feature was implemented.

- Extract the client association, event type, relevant event date where stated, message reference, and available contract/invoice identifiers and source URLs. Record email receipt time separately from the actual event time.
- Preserve the notification as evidence and link the event to its underlying document or invoice where available. Repeated notifications must not create duplicate events or payments.
- A signing notification establishes a reported signing event; it does not by itself supply the full contractual terms. A payment notification supports only the payment information it actually contains, including whether a payment is partial if stated.
- Do not turn a single payment notification into a claim that every invoice is settled or a contract is fully paid.
- The meaning and client coverage of the pricing/payment information seen in GHL remain open. See [FIN-V-01](tobeverified.md#fin-v-01--meaning-of-ghl-pricing-and-payment-information).

## KB-CH-05 — First-release priorities: Action Items and Client Portfolio

**Decision, 20 October:** Action Items and Client Portfolio are the first-release deliverables. They may be delivered together or across subsequent weeks, based on implementation completion and testing. No fixed delivery dates or durations were agreed.

This supersedes the earlier call-preparation-first release sequence. Call preparation remains in the overall product scope; its release position is not yet decided. The exact first-release action workflow and portfolio fields/tabs require clarification. The previously agreed KB-CH-01 through KB-CH-04 additions remain in the overall scope; this decision does not imply all of them must be live in the first release.

## KB-CH-06 — Frontend is the intended experience, with evidence requirements

**Decision, 20 October:** Use the existing frontend as the intended user experience, with field-by-field evidence requirements, explicit unavailable states and proposed adjustments for review.

Fictional records and required mock fields are not proof that equivalent real data is available. Identify changes needed for unknown owner/date/status, partial coverage, shared engagements and unavailable business measures; do not silently invent values or treat every preview element as a validated release requirement.

## KB-CH-07 — KB actions and external write authority

**Decision, 20 October:** Maintain KB records and propose actions. A WIA user reviews before any ClickUp creation or external notification.

The subsequent answers in KB-CH-11 through KB-CH-13 define action eligibility, review routing and Done/Verified evidence. KB-CH-17 through KB-CH-20 establish review ownership, hybrid acknowledgement, freshness and a custom access model. Emoji configuration, detailed visibility permissions and remaining workflow details still require clarification. This decision does not authorise automatic source-system changes or reminders to other people. No external action was performed by this scope decision.

## KB-CH-08 — Business-level client profile and service engagements

**Decision, 20 October:** A client profile represents a business, with separate service engagements and linked contacts/accounts. One meeting may be associated with multiple businesses.

Related businesses can share evidence without merging their account identities or business outcomes. KB-CH-15 confirms currently active clients across services as the launch scope, with former-client archives decided separately. The actual roster and source mappings still require confirmation.

## KB-CH-09 — Complete available historical backfill before launch

**Decision, 20 October:** Historical client records must be backfilled entirely, with all available data, before launch. The proposed recent-history-first/progressive-backfill launch option was not selected.

This is a launch requirement, not a claim that full access or ingestion is already verified. KB-CH-15 and KB-CH-16 subsequently settle the launch-client category and gap-sign-off policy. The actual roster, applicable source/file scope and completion checks still require definition. Bounded source-test samples do not satisfy this requirement. No arbitrary historical cutoff or specific missing-data exception has been approved.

## KB-CH-10 — Conflicting information: rules by field and evidence type

**Decision, 20 October:** Use authority rules by field and evidence type; preserve both sources and route material ambiguity for human review. A conversation does not automatically amend signed terms or payment state.

Retain the already agreed rule that a meeting commitment takes precedence over a conflicting ClickUp due date. The remaining field-level rules, review owner and resolution workflow need definition. A newer timestamp alone is not a universal override rule.

## KB-CH-11 — Action Items include explicit work and separately labelled proposals

**Decision, 20 October:** Include relevant ClickUp tasks and explicit requests/commitments from client-related Slack, email and meetings. Keep AI-suggested improvements separately labelled as proposals.

Preserve the evidence and origin of each item. A generated proposal must not be presented as a commitment made by a client or team member. Relevance filters, duplicate matching and the evidence required for an explicit request/commitment still need implementation and evaluation.

## KB-CH-12 — Active actions, Needs review and unknown fields

**Decision, 20 October:** Import existing active tasks and clear current commitments into the active register. Put ambiguous, potentially stale or AI-suggested items into **Needs review**. Preserve unknown owners/dates without inventing them.

Historical backfill must reconcile later evidence before treating an old request as current work. No observed closure is not proof that an old obligation remains open. Needs review is a distinct review state, not an overdue-task conclusion. KB-CH-17 and KB-CH-18 subsequently establish review ownership and hybrid acknowledgement. Detailed reviewer accept/reject/resolution behaviour remains to be defined.

## KB-CH-13 — Done and Verified require different evidence

**Decision, 20 October:** **Done** means completion is reported by a mapped task or explicit delivery evidence. **Verified** requires a named WIA reviewer to record the follow-up check and evidence.

Retain the completion source separately from the verifier, verification time and check evidence. A source completion flag, AI interpretation or unlabeled Verify button does not establish the follow-up check. Source status mappings must distinguish actual completion from cancelled/not-applicable work. Automatic independent checks may provide evidence, but the approved policy requires a named WIA reviewer for Verified.

## KB-CH-14 — Populate available Portfolio information and gate phased features

**Decision, 20 October, subsequently clarified:** Fill in everything available for Client Portfolio. Gate features according to phased delivery and mark later features **Coming soon**. The user subsequently clarified in KB-CH-21 that these labels do not need phase timelines.

This replaces the proposed fixed minimal subset of portfolio tabs. The field-by-field evidence requirement in KB-CH-06 still applies; fictional sample values must not be used to fill unavailable data. Internal feature sequencing still requires definition, but no week/date allocation is required on Coming soon labels. No delivery weeks/dates have been approved through this answer.

A not-yet-delivered feature and an implemented feature whose data is unavailable have different causes. Preserve that distinction in feasibility and UI proposals; a Coming soon label must not conceal failed access, missing source data or an unresolved interpretation. KB-CH-22 confirms that approved in-scope historical data must still be gathered before launch even when its UI feature is gated.

## KB-CH-15 — All active WIA clients across services are the launch scope

**Decision, 20 October:** Fully backfill all currently active WIA clients across services before launch. Define former-client archive scope separately.

The launch is not limited to a selected convenience sample. Obtain a WIA-confirmed active business/engagement roster and reviewed source associations; LeadLock's 59 sub-accounts include demo/internal accounts and are not the active-client roster. Historical material from earlier services remains subject to the agreed per-business backfill scope; this decision does not delete it or establish a historical cutoff.

## KB-CH-16 — WIA sign-off on historical source gaps before launch

**Decision, 20 October:** Process all obtainable in-scope history and require WIA sign-off on a source-by-source gap report before launch. Inaccessible items remain unresolved until explicitly accepted or recovered.

The gap report should identify the affected client/source/history, retrieval or processing issue and remaining impact. Its exact fields and acceptance workflow still need definition. This is not blanket permission to skip unreadable sources, treat incomplete pagination as complete, or substitute a recent-history window. No particular gap has been accepted through this answer.

## KB-CH-17 — WIA review ownership and technical escalation

**Decision, 20 October:** A designated WIA operations reviewer coordinates Needs review. The relevant account owner resolves client-specific items; E2M handles technical ingestion issues. Names can be supplied later.

This covers uncertain client matches, stale actions, conflicting facts and missing owners/dates. Review responsibility does not itself grant access to restricted information; the custom access model still applies. Specific people and delegation details remain to be supplied.

## KB-CH-18 — Hybrid action-owner acknowledgement

**Decision, 20 October:** Accept an explicit acceptance by the identified owner in a source message or the owner's Acknowledge action in the KB. Also allow specified reactions from the identified owner. Ambiguous replies/reactions go to review.

KB-CH-23 subsequently selects a custom emoji allowlist, but its entries and meanings have not been supplied. An arbitrary reaction, another person's response or an assignment alone is not owner acceptance. Preserve source/actor/context evidence. Acknowledgement remains separate from Done and Verified; reaction handling must not bypass the named-reviewer verification rule.

## KB-CH-19 — Fifteen-minute updates, freshness visibility and refresh

**Decision, 20 October:** Fifteen-minute updates are sufficient, with visible last-sync times and on-demand refresh where supported.

The question concerns updates once data is available from its provider. Provider-side recording/transcript processing must remain visible rather than be confused with KB delay. Keep the already agreed Fathom webhook, Gmail push and Drive watch direction; this answer does not replace them with polling-only intake. Validate the update target and supported refresh behaviour during implementation; no end-to-end cadence has been demonstrated by the source probes.

## KB-CH-20 — Custom access model with per-user admin visibility controls

**Decision, 20 October:** Define a custom access model, with admin controls to show/hide specific information for specific users.

The user did not select the previously proposed assigned-client/finance-role template as the complete policy. KB-CH-24 and KB-CH-25 subsequently limit first-release controls to clients and whole modules/sections and select a standard team access profile as the new-user default. Exact grants and edit/review/verification permissions still require clarification; individual-field controls are later scope. Hiding restricted information must be enforced consistently in backend responses and any evidence or generated output made available to that user, rather than only hiding a visible control.

## KB-CH-21 — Coming soon labels need no phase timeline

**Decision, 20 October:** Coming soon features do not need their phase timelines mentioned.

This clarifies and supersedes the earlier request to display phase-wise timelines alongside those features. Keep the feature gate and label; do not invent release dates, week allocations or phase labels. Internal delivery sequencing can still be defined and reviewed separately. Source unavailability remains distinct from a feature awaiting delivery.

## KB-CH-22 — Backfill all approved in-scope sources regardless of UI delivery

**Decision, 20 October:** Backfill all obtainable history from every approved in-scope source before launch, independently of when its frontend feature ships. Gather available data even if the related UI says Coming soon.

Combine this with the active-client roster and WIA source-gap sign-off requirements. A later feature phase does not permit deferring that approved source's available history. The approved client/source/file/processing boundaries must still be inventoried; this does not authorise indiscriminate ingestion of unrelated data, activate the deferred Google Ads/Meta integrations or settle Shopify's unclarified scope. KB-CH-26 subsequently defines the initial content-processing boundary and link/gap treatment for other files/media.

## KB-CH-23 — Custom acknowledgement emoji allowlist

**Decision, 20 October:** Use a custom allowlist specifying emojis and their meanings for owner-reaction acknowledgement.

No actual emoji/meaning pairs were supplied with this selection. KB-CH-29 subsequently confirms admin configuration and disabling reaction-based acknowledgement until WIA configures the mappings. Do not treat the suggested thumbs-up example or any other mapping as approved. Explicit owner-message acceptance and the owner's manual KB acknowledgement remain agreed independently of the list.

## KB-CH-24 — First-release visibility controls: clients and whole sections

**Decision, 20 October:** Admin visibility controls cover clients and whole modules/sections in the first release. Add individual-field controls later.

Retain per-user restriction/expansion within these boundaries. Do not include arbitrary per-field or per-evidence-record permission editing as a first-release requirement. Client/section restrictions still apply to backend responses, search, summaries, briefs, citations and exports; hiding a section must not expose its restricted information through another output. Exact permission grants and operation rights remain to be agreed.

## KB-CH-25 — Standard team profile is the new-user default

**Decision, 20 October:** A newly added user starts with an agreed standard team access profile. The admin can restrict or expand it.

The profile's client coverage, visible modules/sections and operation permissions have not yet been specified. KB-CH-30 confirms the choice of a custom default without choosing either suggested grant set. Neither all-client access, assigned-client-only access nor financial visibility should be inferred from this decision. This replaces the proposed deny-all-until-granted new-user default; deployment still needs an explicitly configured and reviewed standard profile.

## KB-CH-26 — Historical content processing and linked unprocessed files

**Decision, 20 October, subsequently clarified:** Process readable text, native Google Docs/Sheets, existing transcripts and extractable text from PDFs/DOCX. Retain scans, images and audio/video as links and list unprocessed content in the WIA gap report. See KB-CH-32 for the format clarification.

The automatic OCR/new-audio-or-video-transcription proposal was not selected. No new transcription or image-reading fallback is approved. Extracting an existing document text layer is in scope; OCR of scans/images or transcription of audio/video is outside this initial processing policy.

Distinguish retrieved/processed content from a discovered link or metadata reference. The full-backfill commitment is evaluated against the approved source and processing scope; linked media must not be described as searched/transcribed content. The gap report must expose unprocessed content for WIA review, and no particular gap is automatically accepted.

## KB-CH-27 — WIA manually adds new clients; intake/backfill follows mappings

**Decision, 20 October:** WIA adds clients manually. Automate ingestion/backfill after the profile and source mappings are created.

Do not activate a client profile automatically from a signing/payment email, LeadLock contact or folder. Business and separate service-engagement identity remain as agreed. Automated intake still depends on valid source authorisation and configured scope, and follows the same evidence/unknown/review rules as the initial backfill. New-client activation and admin-operation permissions need to be reflected in the access model.

## KB-CH-28 — Custom launch acceptance checklist and business outcomes

**Decision, 20 October:** Define a custom acceptance checklist and business outcomes, specifying the measures that matter most.

KB-CH-31 subsequently confirms the suggested checks as relevant and adds responsive UI acceptance. Exact business-improvement targets, measurement thresholds, test-case selection and sign-off owner have not been supplied. The previously suggested Viktor benchmark was not accepted as the complete acceptance policy. Do not claim launch readiness based on the existing source GET tests.

## KB-CH-29 — Admin-configured acknowledgement mappings before reaction enablement

**Decision, 20 October:** Make emoji-to-meaning mappings admin-configurable. Require WIA to configure them before enabling reaction-based acknowledgement. Explicit-message acceptance and manual KB acknowledgement remain available independently.

No default emoji map is approved. The configured mapping still requires the identified owner's reaction and relevant action context, and ambiguous cases go to review. Configuration must not bypass the separate named-WIA-reviewer requirement for Verified.

## KB-CH-30 — Custom standard team access profile; grants to be configured

**Decision, 20 October:** Use a custom default that specifies the client coverage and modules/sections a standard team member receives.

The user selected a custom default but did not supply the actual grant list. Do not substitute either proposed assigned-client or all-client profile. Record it as WIA-defined configuration needed before user activation; feasibility should describe the configurable mechanism without claiming a default grant matrix has already been agreed. Per-user admin restrictions/expansion and first-release client/whole-section granularity remain as agreed. Detailed operation permissions remain to be specified.

## KB-CH-31 — Acceptance checks and responsive UI coverage

**Decision, 20 October:** The suggested checks are relevant, and the UI must be responsive for current mobile-phone sizes, tablets, laptops, MacBooks and iMacs.

Acceptance coverage therefore includes:

- correct client matching and complete agreed backfill with signed-off source gaps;
- cited facts/actions, no invented owners/dates and stale requests routed to review;
- separate Done/Verified evidence, working access restrictions and fifteen-minute updates;
- responsive layouts across phone, tablet, laptop and large-desktop displays, including the named Apple device categories.

These are acceptance areas, not a claim that they already pass or a zero-error guarantee for all future inputs. Representative viewport/device/browser cases, measured thresholds, the test dataset and WIA sign-off owner remain to be defined in delivery/testing work. No additional numeric business-improvement target was supplied. Evaluate layouts by actual available viewport and interaction behaviour; do not infer one fixed screen size from a device category.

## KB-CH-32 — PDF/DOCX text extraction included; no OCR or new transcription

**Decision, 20 October:** Include extractable text from PDFs/DOCX alongside readable text, native Docs/Sheets and existing transcripts. Keep scans, images and audio/video as links, without OCR or new transcription.

Preserve source references and extraction status. A PDF's existing text can be read without treating its scanned/image-only pages as understood. Do not turn document extraction into a claim of signed/current contract validity or complete financial state. Test PDF/DOCX parsing on representative authorised samples; existing metadata and bounded byte tests do not establish parser coverage. Linked unprocessed content remains visible in the WIA gap report.

## KB-CH-33 — Railway and OpenRouter in WIA-owned accounts

**Decision, 20 October:** Use Railway and OpenRouter in WIA-owned accounts. Assess the KB's own storage, queues, access and running costs explicitly.

Keep the existing frontend and FastAPI backend SOP as starting constraints. The user has not approved an exact database setup, embedding/search design, service topology, model IDs or monthly budget through this decision. Evaluate those choices using KB-specific volumes, verified unit prices and measured costs. Production credentials/ownership and E2M's operational access must be explicitly configured.

## KB-CH-34 — Remaining feature sequence stays open

**Superseded in part on 21 October by KB-CH-69:** activation order is now set for Call Preparation, Health & Sentiment, Invoices & Contracts and Overview. Chatbot and unlisted capabilities remain unsequenced. The original decision below is retained as history.

**Decision, 20 October:** Leave the feature order after Action Items and Client Portfolio open until implementation planning.

Call Preparation was not selected as an automatically committed next phase. Coming soon labels still require no displayed dates/timelines. This does not remove the overall feature requirements or the approved-source historical-backfill obligation.

## KB-CH-35 — Health & Sentiment assesses engagement plus LeadLock tracking

**Decision, 20 October:** Present assessment of the client engagement and add LeadLock lead-tracking data. The user asked for recommendations on additional relevant information.

LeadLock access, account mappings, stage/outcome definitions and completeness remain verification dependencies. KB-CH-42 subsequently approves the additional evidence-supported dimensions and separate engagement/outcome presentation. Commercial context and combined scoring remain deferred. See the [Viktor/API comparison](knowledge_base_viktor_llm_comparison.md#9-health--sentiment-agreed-scope-and-deferred-additions).

## KB-CH-36 — Current source scope stays at the approved eight

**Decision, 20 October:** Keep intake to Gmail, Slack, ClickUp, historical Zoom, Fathom, Google Drive, LeadLock and Google Calendar. Existing material in approved Drive folders remains in scope. Live website research, ChatGPT history/project imports and a separate manual-upload mechanism are later proposals.

Do not add those mechanisms solely because the historical discovery mentioned them. The user's subsequent answer explicitly keeps new first-release work within these eight sources, including any new Viktor requests. Existing Viktor posts may be retained as attributed analysis. Fresh paid-media analysis is separately scoped; Viktor's existing integrations do not expand first-release intake automatically.

## KB-CH-37 — Evaluate API LLM, Viktor-led and hybrid approaches

**Decision, 20 October:** Compare three approaches for structured UI data and interpretation: direct API LLM work with existing Viktor posts reused, Viktor orchestration through directional skills, and a hybrid using each where suitable. Assess Viktor integration/tool credit costs and API model costs, including repeated retrieval of the same information.

This request itself did not select an approach. KB-CH-41 subsequently retains selective hybrid and Viktor-led as two implementation candidates, with testing required before choosing. The [comparison](knowledge_base_viktor_llm_comparison.md) preserves the API-only approach as a research comparator. Public documentation supports structured APIs/skills, but WIA API access, billing, source-tool coverage and comparative quality have not been live-tested. Keep existing Viktor analysis attributed and distinguish it from original human communications and independently retrieved provider records. Candidate approval is not evidence of implemented routes or successful paid tests.

## KB-CH-38 — First release links existing tasks; external actions later

**Decision, 20 October:** Ship the KB Action Items register and existing-task links first. Mark ClickUp task creation and external notifications Coming soon.

The agreed WIA-review requirement still applies whenever those later capabilities are delivered. This selection does not authorise task creation, messaging or provider changes during discovery. Evaluate Viktor-related task execution separately from a passive read of its existing Slack output.

## KB-CH-39 — Scale, development/launch targets and cost objective

**User-provided planning inputs, 20 October:** Approximately **15–20 active clients** now; target **30–40 active clients total**, described as roughly 20 additional clients. Development deadline **6 November**, launch deadline **26 November**, interpreted in this project's **2026** calendar.

Monthly running-cost cap is **unknown**. Optimise cost as much as possible without loss of required performance/quality. Do not invent a cap or substitute a cheaper model without checking output quality, completeness and latency. Source volumes, historical processing totals, staffing and measured throughput still need assessment; client count alone does not establish backfill cost or deadline feasibility. The two deadlines are targets, not a claim that the work is already estimated or guaranteed to fit.

## KB-CH-40 — Recalled Viktor spend and optimisation objective

**User-reported context, 20 October:** WIA spends approximately **$1,000/month**, as the user remembers it. Team members individually DM Viktor for recommendations, information and insights. The user reports that current per-channel call preparation works very well and that Viktor identifies valuable Google/Meta configuration/performance irregularities and suggests optimisations. Reducing cost while making effective use of these capabilities is an additional desired benefit.

This is a recalled baseline, not a verified invoice, subscription, credit allowance or measured task breakdown. Preserve the distinction between the current reported value and historical discovery feedback. Evaluate repeated lookups/overlapping analysis, reuse and bounded routing without claiming the KB replaces the complete existing workload. Retained valuable Viktor work may justify a continuing subscription. Actual cash savings depend on invoices/top-ups/plan changes and incremental KB expenses, not merely lower credit consumption.

The explicit eight-source first-release boundary in KB-CH-36 remains in force. Reusing existing ad-related posts does not authorise new paid-media intake or claim equivalent campaign monitoring. The cost audit can use aggregated billing/usage metadata; private DM contents have not become an approved intake source through this answer. No schedules, plan or task execution have been changed.

## KB-CH-41 — Retain selective hybrid and Viktor-led for comparative testing

**Decision, 20 October:** Keep **two ways of implementation**: selective hybrid and Viktor-led. Test both against specified criteria, including completeness of the required skill-directed output and cost validation, then use the suitable approach. Neither is the selected winner yet; API-only is no longer a retained delivery candidate.

The hybrid includes **active, specific skill-based Viktor work**, as well as API LLM analysis where appropriate with the relevant business context supplied. It is not limited to passive reuse of previous Viktor posts. The Viktor-led candidate uses skill-based orchestration to obtain the specified structured result, with source completeness and required output formation assessed explicitly. Both retain the owned KB's evidence records, calculations/validation, access controls, review workflow and UI responsibilities.

Compare the same authorised client/source windows and expected outcomes. The feasibility study should propose tests for source/field completeness, correct client and engagement matching, required output/schema compliance, evidence and unknown handling, action lifecycle/permissions, latency/recovery, human corrections and end-to-end credits/tokens/operating costs. Exact sample size, scoring thresholds and run budgets remain to be agreed for execution. Valid JSON alone is insufficient; missing input data must be reported rather than treated as a successful complete result. Existing source access limitations still apply to both candidates.

New first-release retrieval stays within the eight approved sources. This decision authorises documenting and preparing the comparative design; it does not establish WIA API access or a completed paid evaluation, and does not authorise external notifications, source-system writes, schedule changes or fresh paid-media analysis.

## KB-CH-42 — Evidence-supported Health & Sentiment additions approved

**Decision, 20 October:** Include client feedback, delivery follow-through, support/resolution, lead handling and relevant onboarding/programme context where supported by evidence, alongside engagement assessment and LeadLock outcomes.

Use separate engagement/outcome views, evidence-based drivers and visible coverage/freshness. Commercial context and combined scoring are left for later review. No numeric score, weighting or health threshold is approved. Each dimension needs actual client/engagement mapping and source/metric readiness: an unreadable source is not a healthy result; missing deadlines do not establish overdue work; RSVP does not establish attendance; and current CRM stage does not reconstruct historical conversions or response times. This approves overall product scope, not an automatic change to first-release sequencing.

## KB-CH-43 — Scope an in-platform KB chatbot; test routing and source freshness

**Request and follow-up decisions, 20 October:** Add a chatbot concept for WIA team questions about permitted KB data and displayed records: client context, last-call discussion, action items, their origin/context and assignments. Thoroughly scope its intended conversations and assess API LLM/Viktor query routing, alternatives and the recommended solution. See [chatbot_KB.md](chatbot_KB.md).

**Delivery:** Scope now; decide delivery order during implementation planning. This does not automatically add chatbot delivery to the Action Items/Client Portfolio first release or change the November targets.

**Source-freshness choice:** The user explicitly leaves KB-only answering versus KB-first with controlled live reads to testing. Neither mode is selected. Any new retrieval remains within the eight approved sources and the requesting user's client/module permissions. The chat-specific execution design must remain distinct from the existing hybrid-versus-Viktor-led background implementation comparison.

The scope recommends a common permission-aware KB query/evidence layer, exact structured queries where appropriate, API interpretation and selectively tested Viktor skills. This is a recommendation, not a final provider/routing selection or successful evaluation. Initial read-only interaction, conversation-history policy, exact skill eligibility, live-read triggers, budgets and pass thresholds remain proposed/configuration work. Existing action authority, review-before-external-writes, source-processing and access rules continue to apply. No chatbot UI, backend, skill or paid run was implemented by this scope.

## KB-CH-44 — Accuracy-preserving chatbot caching, direct answers and token conservation

**Request, 20 October:** Make the chatbot cost-conscious through cached responses, reuse for repeated/similar questions, FAQ-style direct answers and other token-saving mechanisms while meeting the required QA/accuracy criteria. The detailed design and proposed tests are in [chatbot_KB.md, Section 13](chatbot_KB.md#13-operational-behaviour-cost-and-performance) and its QA section.

The requested objective is agreed; exact cache technology/configuration, TTLs, semantic thresholds, savings percentages and monthly cap are not supplied or proven. The scope recommends versioned approved definitions, parameterised client-query templates, dependency-checked result/answer caches, reuse of cited artifacts and conservative paraphrase-to-intent matching before new API/Viktor work. Similar wording alone must not approve an answer-cache hit. Correctness, completeness, source freshness, citations and client/module access remain required on reused answers.

Evaluate collection/record/time/coverage/permission invalidation, concurrency and cold/warm cost against reviewed expected answers and a genuinely cache-bypassed reference path. Cache age is distinct from source freshness; do not add another cache-delay window to the fifteen-minute update target. Cost reduction must not conceal stale/incorrect or forbidden answers. No cache implementation, runtime benchmark or measured saving was produced by this documentation update. KB-only versus controlled live reads and chatbot delivery order remain as recorded in KB-CH-43.

## KB-CH-45 — Reuse existing application authentication with admin-added users

**Decision, 20 October, Architecture Q1:** Use the existing Command Center authentication system, described by the user as email/password accounts managed for the application, with an additional admin mechanism for adding users. A separate Google sign-in system was not selected. Mailbox/Drive/Calendar connector OAuth remains separate from application login.

Local code inspection shows email/password authentication, signed sessions and a cross-application sign-in handoff. It does not establish a supported admin provisioning API. Architecture Q4 subsequently selects KB-admin provisioning of central login accounts through an API; see KB-CH-48. Existing coarse team/client roles do not define KB administration or client/module permissions; authentication reuse must integrate the agreed KB access model.

## KB-CH-46 — Dedicated KB Railway project and data services

**Decision, 20 October, Architecture Q2:** Use a dedicated KB Railway project and data services under WIA ownership. Keep deployments, business data and job/cache resources isolated from other applications; shared authentication remains an explicit integration.

This selects isolation, not exact database technology, service sizing, environment layout, backup retention or recovery objectives. Assess those in the Solution Architecture with KB-specific operating costs and historical-processing requirements.

## KB-CH-47 — Retain facts/excerpts; fetch full originals when needed

**Decision, 20 October, Architecture Q3:** Retain extracted facts and supporting excerpts; fetch full originals when needed. Full replayable text snapshots were not selected. Processing all obtainable approved-source history before launch remains required, including data for Coming soon features.

Retain necessary source/account/record identifiers, citation locators, observation times, version/content markers and processing/coverage metadata. Search indexes must reflect the retained facts/excerpts rather than silently preserve every original chunk. Full bodies may be transient inputs; temporary files, logs and provider/cache handling need a bounded policy rather than becoming an undeclared permanent archive.

Detailed quotation, additional extraction and exhaustive questions about unretained content depend on authorised original retrieval and provider version availability. Distinguish the earlier observed excerpt from a current, possibly edited original. If retrieval fails, disclose the gap and use only supported retained information; do not reconstruct missing text. This decision does not select chatbot Mode A versus Mode B or exact retention periods. Architecture Q6 subsequently selects retaining facts/excerpts with a deleted-source warning; see KB-CH-50 and the [architecture discovery record](knowledge_base/wia-knowledge-base/docs/Client-Knowledge-Base-Architecture-Discovery.md).

## KB-CH-48 — KB admin provisions central login accounts through an API

**Decision, 20 October, Architecture Q4:** KB administrators also provision central login accounts through an API. Keep authentication in the existing Command Center system and KB client/module membership in the KB. Membership-only administration and separate KB credentials were not selected.

The supported central provisioning contract must be established or implemented; the inspected configuration-managed registry does not demonstrate an existing provisioning API. Design authenticated server-to-server administration, create-or-link handling for an existing identity, retry-safe provisioning, audited outcomes and explicit pending/failed states. A central-account success must not masquerade as successful KB activation if membership/grant setup fails. Do not reset an existing password or grant other applications' permissions merely because a KB admin adds a user. Exact invitation/password setup, identity lifecycle and cross-application deactivation responsibilities remain to specify. No central accounts or authentication code were changed by this decision record.

## KB-CH-49 — Preserve reviewed corrections and distinguish subsequent changes

**Decision, 20 October, Architecture Q5:** Preserve reviewed WIA corrections, review later conflicting source updates, and highlight changes separately so they are differently identifiable, similar to a read/unread feature.

Maintain the reviewed KB value separately from original and later source observations, with actor/time, relevant field, evidence and review/audit history. A conflicting refresh does not silently overwrite the correction. Preserve the agreed meeting-versus-task deadline rule and field-specific financial authority; a manual assertion is not proof of an amended contract or payment. Show the difference between an accepted correction and a new unresolved conflict. Q7 subsequently selects per-user read state and separate conflict status (KB-CH-51); Q8–Q9 select custom operation permissions and admin-configurable self-verification (KB-CH-52–53).

## KB-CH-50 — Retain facts/excerpts after source deletion with a warning

**Decision, 20 October, Architecture Q6:** When an upstream original is confirmed deleted, retain the extracted facts/excerpts with a deleted-source warning. Automatic withdrawal/quarantine/removal solely due to source deletion was not selected.

Retained material remains eligible for permitted KB views, search and chatbot answers with its provenance, observation time and deleted-source status visible. It establishes what was retained at the time; it does not establish that a current contract, assignment or other mutable state remains unchanged. Keep the surviving excerpt accessible through the KB citation while explaining that the upstream original is no longer available. Do not reconstruct unretained text or claim the source was refreshed successfully.

Update evidence/coverage revisions and refresh dependent answers/caches so the warning cannot be hidden behind a previously cached result. Preserve supported facts and distinguish confirmed deletion from access denied, a missing search result or a temporary provider failure. Exact retention periods and explicit KB deletion/access-revocation policies remain separate; this choice is not indefinite retention or permission to restore material to an unauthorised user. No original full-text archive is introduced.

## KB-CH-51 — Per-user read state with separate conflict status

**Decision, 20 October, Architecture Q7:** Use per-user new-change/read state. Opening the change details or explicitly marking the change read clears that user's indicator for the viewed change; a later change becomes unread again. An unresolved-conflict badge remains until review is completed. Reading does not resolve the conflict.

Read state belongs to the user and change revision, not one shared flag on the client record. One user's reading must not clear another's indicator; marking an earlier revision read must not clear a newer unseen change. Reading, owner acknowledgement, review resolution and action verification stay separate operations. Only permitted change details may be shown. Read markers are UI metadata, not new client evidence or a reason for another LLM analysis.

## KB-CH-52 — Custom editing and review permissions

**Decision, 20 October, Architecture Q8:** Define a custom set of editing and review permissions. The proposed fixed grant set of KB admins, WIA reviewer and account owners was not selected as the final permission matrix.

Separate client/module visibility from rights to correct facts, change action fields, resolve conflicts, verify work and administer users/connectors. Architecture Q10 subsequently selects custom roles plus per-user overrides (KB-CH-54). Actual grants and the custom standard team's defaults remain configuration inputs; account ownership, visibility or a central team/client role alone must not imply editing/review authority. Existing assigned coordination roles remain, but operational responsibility is not itself an access grant. This choice does not permit source-system writes or chatbot mutations.

## KB-CH-53 — Self-verification is an admin-configurable permission

**Decision, 20 October, Architecture Q9:** Make an action owner's ability to verify their own work admin-configurable. Neither a universal prohibition nor a universal entitlement to self-verification was selected.

Verified still requires a named, authorised WIA reviewer to record the follow-up check and evidence. Where the actor is also the action owner, check the configured self-verification permission in addition to normal verification rights and client/module access. Done remains reported completion; assignment, reading or acknowledgement does not supply verification evidence. Preserve the actor, time, follow-up evidence and whether the check was self-verification in the audit history. Exact permission granularity/default grants are part of the custom permission configuration; an unconfigured permission is not an affirmative grant.

## KB-CH-54 — Custom roles plus per-user operation overrides

**Decision, 20 October, Architecture Q10:** Configure the custom editing/review permissions through custom roles plus per-user overrides. Role-only and standalone per-user-only administration were not selected.

Retain the agreed per-user client/module access boundary. A role or operation override must not implicitly reveal a hidden client/section. Keep content correction, action editing, conflict resolution, verification/self-verification and user/connector administration as distinguishable capabilities. Actual role names/grants and the standard team's defaults remain WIA configuration inputs. Architecture Q13 subsequently selects Inherit/Allow/Deny overrides within permitted scope (KB-CH-57). Audit role/override changes and enforce effective permission changes across records, pending work, caches, evidence, chat and exports. This does not introduce first-release field-level visibility controls.

## KB-CH-55 — Revoke KB access without disabling the central account

**Decision, 20 October, Architecture Q11:** Remove KB membership/access immediately while leaving the shared central account active. Central disabling is a separate, explicitly authorised operation affecting the connected applications.

A valid central login or previously issued session must not restore revoked KB membership. Apply current KB authorisation on backend requests, history/evidence access, downloads/exports and before pending job/response delivery. Prevent revoked users from receiving later chat stream output or protected results; invalidate affected access/session decisions without altering unrelated applications. Information already downloaded cannot be recalled. Keep the revocation/audit record and separate later retention/deletion handling. Central disabling still has to prevent new KB access through its trusted authentication contract; its implementation remains to verify. No account was revoked during discovery.

## KB-CH-56 — Assess one-hour data loss and four-hour restoration

**Decision, 20 October, Architecture Q12:** Assess a recovery target of at most one hour of lost KB changes and restoration within four hours after a serious KB database failure, subject to backup/restore testing and cost validation. These are design/evaluation targets, not a demonstrated guarantee.

Protect the KB-owned state that source re-fetching cannot recreate: reviewed corrections, review/verification history, access configuration, source mappings, retained excerpts and processing checkpoints. Recovering source originals alone is insufficient, particularly where an upstream original was deleted. Queue/cache rebuild and intake reconciliation must be planned without replaying external actions or reviving revoked access from an older backup.

Assess a recoverable backup/archiving method and monitor its actual freshest restorable state. Daily-only snapshots cannot establish one-hour data-loss coverage. Validate recovery on an isolated restore, including access/revocation reconciliation, source checkpoints, review history, cache invalidation and application cutover. Exact backup topology, retention, incident clock, support coverage, named recovery owner and broader project/provider-loss coverage remain to specify. No backups or Railway services were created or changed.

## KB-CH-57 — Role baseline with per-user Inherit/Allow/Deny

**Decision, 20 October, Architecture Q13:** Use custom roles as the baseline and per-user Inherit/Allow/Deny settings for each operation within the user's permitted client/section scope. An explicit per-user Deny wins over role grants; Allow can add an operation only within that existing scope. No override restores revoked membership.

An Inherit setting follows the configured role baseline; absence of any effective grant does not confer an operation. Keep role/override configuration attributable and auditable, and show administrators the effective result and its origin. Actual role names, baseline grants and any multi-role combination rules remain configuration/design inputs. Operation overrides do not implicitly grant module/client visibility, bypass feature availability or make deferred admin chat-content inspection available.

## KB-CH-58 — Approved limited real-client data in isolated staging

**Decision, 20 October, Architecture Q14:** Use a WIA-approved, limited real-client dataset in isolated staging, with separate test credentials/configuration and no source-system writes. Production still requires full obtainable historical backfill across all approved sources for all active clients.

The policy is selected; the sample roster/windows, test identities and evaluation limits need configuration. Architecture Q17 subsequently confirms full testing-data access for both E2M and WIA without a separate per-client testing-access approval step (KB-CH-61). Isolate staging data services, credentials, caches, jobs and provider subscriptions from production. Replaying a saved event must not change production state or trigger notifications/actions. Exercise permission restrictions with test identities and record coverage so limited fixtures do not masquerade as archive completeness. Testing access and paid evaluation budgets are distinct inputs.

## KB-CH-59 — Private chatbot threads; admin metadata only

**Decision, 20 October, Architecture Q15:** Keep chatbot threads private to the user. Admins may access operational metadata such as usage, cost and errors, without conversation content. Extending authorised admins to inspect content is a possible later addition, explicitly excluded for now.

Current client/module access still limits history, answers, citations and provider context; ownership of a private thread does not preserve access to revoked client evidence. Do not expose private messages through admin dashboards, search, exports, prompt logs, traces, model error bodies or cache inspection. Operational errors must be sanitised so they do not echo prompts, answers or retrieved content. Admin user/role management is not chat-content inspection permission. Shared threads and cross-user conversation-history retrieval are outside the selected current policy.

Reusable answers/artifacts may use permitted KB facts under existing cache rules, but must not turn private conversation text or personal context into shared KB evidence or a shared FAQ. Q16 subsequently selects admin-configurable category retention policies (KB-CH-60). This is the application's production access policy, not a claim that infrastructure operators physically cannot access database storage. Q17 confirms full testing-data access for E2M and WIA (KB-CH-61); it does not select production admin conversation inspection. No conversation or logging feature was implemented by this record.

## KB-CH-60 — Admin-configurable category retention policies

**Decision, 20 October, Architecture Q16:** Use separate admin-configurable retention policies for saved chats, temporary full-original files, operational/audit records and former-client data, with WIA-approved durations configured before launch. No numerical periods have been selected.

Keep policy category, duration, effective version and change actor/time explicit. Configuration must not turn temporary original processing into an undeclared permanent full-source archive or grant chat-content inspection. Plan cleanup of affected database/search/cache/artifact references and disclosure when expired supporting content is unavailable. Exact treatment of existing records on a policy change, backup expiry and provider-side retention must be designed explicitly; app deletion is not proof that every backup/provider copy is immediately erased. Former-client retention is separate from whether former-client archive intake is in scope.

## KB-CH-61 — Full testing-data access for E2M and WIA; access question closed

**User clarification, 20 October, Architecture Q17:** The user considers the connection/support-access question unnecessary to answer and confirms that both E2M and WIA have full access to the data for testing. Close this discovery question; do not require a separate client/section testing-access approval or re-open the proposed support-ownership split as a blocking prerequisite.

This establishes testing access. Preserve isolated staging and a bounded representative fixture set for evaluation; selecting fixtures records test coverage rather than adding a new access gate. Approved intake boundaries, provider credentials/scopes and actual source availability still determine what can be retrieved. Full testing access does not establish that previously denied API endpoints now work. Production's agreed roles/client-module controls and private-thread/admin metadata-only policy remain unchanged. No production support-ownership arrangement is inferred from the answer.

## KB-CH-62 — Approximately ten team users, all potentially concurrent

**User-provided planning input, 20 October, Architecture Q18:** Around ten WIA team members may use the KB, and all of them may use it simultaneously. The number can increase or decrease; no exact next-year user count is supplied.

Use ten concurrent users as the initial capacity-test baseline, alongside the established 15–20 active clients growing towards 30–40. Include simultaneous Portfolio/action use, chat request bursts and ongoing ingestion/backfill when measuring latency, freshness and cost. User count does not itself specify model-agent parallelism, per-user query rates or acceptable response-time thresholds. Size workers/provider admission and cache coalescing from measurements; keep user/resource configuration adjustable rather than hard-limit membership to ten. No load test has yet demonstrated this capacity.

## KB-CH-63 — Version-controlled AI behaviour with evaluation before release

**Decision, 20 October, Architecture Q19:** Keep AI prompts, Viktor skills and query-routing behaviour as version-controlled engineering changes, evaluated before release. Direct admin activation/editing and an admin AI-publishing workflow were not selected.

Admin controls retain the agreed business settings, roles/overrides, mappings, acknowledgement emojis and category retention. A versioned release identifies skill/prompt/schema/context/routing versions and passes relevant output, evidence, permission, freshness and cost regression checks. Business configuration changes still need audit and dependency invalidation; they must not become an indirect mechanism to execute arbitrary prompts/tools or bypass the reviewed release. Provider selection and chatbot source-freshness mode remain test-dependent.

## KB-CH-64 — Show last-known data with explicit last-sync date/time

**Decision, 20 October, Architecture Q20:** Keep supported last-known data visible during source failure/freshness lag, with an explicit message such as “Last synced at [time and date]”. This accepts the recommended freshness-limited behaviour rather than hiding all affected data.

Show the last successful sync/publication time and stale/unavailable-source status; a failed attempt, page refresh or cache hit must not advance it. Distinguish the source event's date from the time it was successfully synchronised. Chat may use retained historical evidence with the limitation disclosed; requests requiring current verification receive a partial/unavailable answer when fresh support cannot be obtained. The fifteen-minute target remains; retained data is not presented as newly verified. Confirmed deletion still follows the separate retained-excerpt warning policy.

## KB-CH-65 — SQLAlchemy ORM, psycopg and Alembic selected

**Decision, 20 October, Technical Q21:** Use SQLAlchemy ORM with psycopg and Alembic for the KB database implementation. The raw-psycopg/versioned-SQL-runner alternative was not selected.

Use the SOP layout: database bootstrap in db.py, database mappings under models/db, and Alembic-owned migration assets under sql/migrations with one documented schema owner. Exact compatible library pins, sync/async session policy, pools and transactional implementation are engineering specifications still to supply. No database or migration was executed by this decision.

## KB-CH-66 — Resolvers apply corrections; editors propose

**Decision, 20 October, Technical Q22:** Users with correction-approval/conflict-resolution authority may apply an audited KB correction directly. Other authorised editors submit a proposed correction for review; it becomes the maintained value only when an authorised resolver applies it.

Enforce current membership, client/module scope, field authority and operation permissions. Proposal submission alone does not replace the current fact/owner/deadline. Application records the previous/current value, actor/time, reason/evidence, entity revision and dependent change/invalidation work. A browser-supplied apply flag cannot confer resolution authority. This does not require a different reviewer for every correction or authorise source-system writes.

## KB-CH-67 — Automatically reopen and supersede verification

**Decision, 20 October, Technical Q23:** When the mapped ClickUp task genuinely reopens after its KB action was Verified, automatically reopen the KB action and mark the prior verification superseded. Preserve the verification actor/time/evidence as history; do not keep the current action Verified pending review.

This is a specific source-driven lifecycle rule. It does not authorise overwriting other reviewed fields such as owner/deadline or changing contract/payment authority. Validate mapping and source ordering/current state before applying the transition; duplicate or stale task snapshots must not create another reopening. Update the action/change/collection revisions and dependent cached answers. Later task completion supports Done normally and does not reactivate superseded verification; a new follow-up check is needed for a new Verified state. Exact status mapping and transaction mechanics belong in the technical specification.

## KB-CH-68 — Hybrid chatbot cost-control methodology

**Decision, 21 October:** Add the hybrid methodology to the KB chatbot documentation, using standalone KB wording. Use deterministic definitions/parameterised queries and dependency-valid reuse first, followed where needed by guarded semantic intent matching, incremental evidence/query embedding reuse and bounded API/eligible specialist work.

Semantic matches select candidate approved intents/plans, not automatically equivalent answers. Validate entity, owner/assigner, responsibility, temporal meaning, negation, status, output requirements and current permissions; ambiguous cases use the existing bounded planner or clarification. Reuse versioned exact embedding inputs, replace changed/incompatible vectors, isolate private queries and preserve category retention. Keep semantic full-answer replay disabled initially.

This approves the methodology, not an embedding model, universal similarity cutoff, cache TTL/capacity, measured saving or production activation. Require held-out correctness/privacy/freshness and R0/R1/R2 cost evaluations before enabling semantic acceptance. Chat Mode A/B, background hybrid-versus-Viktor-led selection, source scope and delivery order remain unchanged. No implementation or paid benchmark is claimed by this decision.

## KB-CH-69 — Three-stage tab activation sequence

**Decision, 21 October:** Activate **Stage 1: Action Register + Client Portfolio**, followed by **Stage 2: Call Preparation**, followed by **Stage 3: Health & Sentiment + Invoices & Contracts + Overview**.

This supersedes the open ordering for those named tabs in KB-CH-34 and related planning text. Chatbot's delivery position and unlisted capabilities remain undecided. No new dates/week allocations are assigned, and Coming soon labels still require no timelines. Each stage must meet its evidence, permission and testing gates; underlying queries/data may be built earlier without activating the later tab.

All obtainable approved-source history for active clients must still be processed before first launch, including data for later-stage features. Supported available Portfolio information remains in scope; this sequence does not invent missing health/financial evidence or enable source writes/notifications. Existing development/launch targets are unchanged.

## Related records and evidence

- [Knowledge Base verification register](tobeverified_knowledgebase.md): surveys, support-source coverage, and lead-outcome readiness.
- [Financial-source verification](tobeverified.md): GHL pricing/billing meaning and its relationship to Dubsado.
- [Ambiguities requiring clarification](tobeclarified.md): Shopify use case and data contract.
- [2 September transcript, 8:45 and 23:38–24:09](WIA_Meeting_Analysis/meetings/2026-09-02_ops-and-onboarding/source.md): historical GHL invoice handling, Dubsado notifications, and partial migration of offers to GHL.
- [22 September transcript, 36:44–39:25](WIA_Meeting_Analysis/meetings/2026-09-22_knowledge-base-scoping/source.md): booking outcomes, surveys, and support handling.

The user's 19 October instructions establish KB-CH-01 through KB-CH-04. Answers during feasibility discovery on 20 October establish KB-CH-05 through KB-CH-42; subsequent chatbot scoping, follow-up answers and the cost/QA objective establish KB-CH-43 and KB-CH-44. Architecture Q1–Q20 establish KB-CH-45 through KB-CH-64, including closure of Q17; Technical Q21–Q23 establish KB-CH-65 through KB-CH-67. The 21 October hybrid chatbot methodology instruction establishes KB-CH-68, and the tab activation sequence establishes KB-CH-69. Reported context, agreed requirements and proposed design remain distinguished. Earlier call evidence explains their purpose but does not verify today's source configuration.
