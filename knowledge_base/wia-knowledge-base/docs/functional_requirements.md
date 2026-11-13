# Client Knowledge Base — Functional Requirements

**Prepared for:** Wedding Industry Ads  
**Prepared by:** E2M Solutions  
**Date:** 21 October 2026  
**Status:** Functional-requirements baseline; unresolved definitions, configuration and source dependencies are explicitly retained.

## 1. Purpose and basis

This document records the functional requirements identified for every business view, client-record section and supporting workflow in the Maintained Client Knowledge Base. Each requirement describes observable system behaviour. Requirement IDs are stable references for development tasks, API contracts and acceptance cases.

Basis: the [Solution Architecture](Client-Knowledge-Base-Solution-Architecture.md), [decisions through KB-CH-69](../../../knowledgebase_changes.md), [chatbot scope](../../../chatbot_KB.md), [Feasibility Study](Client-Knowledge-Base-Feasibility-Study.md), existing frontend and the requirement catalogue discussed with the user. This document records intended functionality; it does not establish completed implementation or successful source/runtime acceptance.

Requirements with unresolved definitions or unavailable evidence remain conditional. They must not be fulfilled by fictional sample values, guessed business rules or unsupported claims. Section 18 records those dependencies. Existing agreed policies take precedence over illustrative mock controls.

## 2. Activation and scope

| Stage | Views |
|---|---|
| **1** | **Action Register + Client Portfolio** |
| **2** | **Call Preparation** |
| **3** | **Health & Sentiment + Invoices & Contracts + Overview** |
| **Unsequenced** | Chatbot and other unlisted capabilities |

Underlying data intake and historical processing continue independently of UI activation. All obtainable approved-source history for active clients must be processed before first launch, including data for later-stage features. Supported available Portfolio information remains in scope; full later modules and unsequenced capability depth remain subject to their gates. Coming soon labels require no timelines. This sequence assigns no new dates.

The current frontend contains six primary tabs and the supporting Source Library/Connections screens. The Chatbot is planned and has no implemented frontend route or screen. Review and administration requirements describe needed operating workflows, some of which are not fully present in the mock.

## 3. Actors and shared rules

In this catalogue, **user** means a signed-in WIA team member with permission for the relevant client, section and operation. Reviewers, action owners and administrators receive only their configured rights; their title alone does not grant authority. Background ingestion performs automated source processing. External client statements may establish acceptance or facts through supported evidence without implying an external client portal.

| Actor | Responsibility / boundary |
|---|---|
| WIA team user | Browse and use permitted records, evidence and enabled features |
| Action owner | Accept responsibility through supported identified-owner evidence or an authorised KB action |
| Authorised editor | Submit permitted corrections and perform configured action operations |
| Authorised resolver/reviewer | Apply or reject corrections, resolve business ambiguity and record permitted follow-up checks |
| KB administrator | Manage membership, grants and configured business settings; no default private-chat content inspection |
| WIA operations reviewer/account owner | Coordinate review and resolve client-specific matters within actual configured rights |
| Technical operator/E2M | Diagnose technical intake/processing issues within applicable access; testing access does not change production private-chat boundaries |
| Background system | Receive, process, reconcile and publish approved-source evidence and maintained state |

| ID | Use case | Functional requirement |
|---|---|---|
| FR-COM-01 | Enter the application | Authenticate through the agreed central login system and require active KB membership. |
| FR-COM-02 | Access permitted information | Restrict clients, modules, operations, search, citations, chat and exports according to current effective permissions. |
| FR-COM-03 | Understand missing information | Distinguish unknown, unavailable, not applicable, partially covered and not-yet-delivered functionality. Do not substitute fictional values or unsupported zeros. |
| FR-COM-04 | Judge freshness | Show applicable source-as-of and last successful sync information. Failed attempts, page refreshes and cache hits must not make evidence appear newer. |
| FR-COM-05 | Inspect factual support | Attach traceable evidence or an audited human decision to maintained facts and substantive generated claims. |
| FR-COM-06 | Understand interpretation | Distinguish direct statements, maintained facts, calculations, interpretations and proposals. |
| FR-COM-07 | Navigate consistently | Open the same canonical client, action, meeting or evidence record from any view. |
| FR-COM-08 | Receive consistent results | Apply the same business definitions across cards, lists, counts, briefs and chatbot answers; identify older artifact versions. |
| FR-COM-09 | See feature availability | Gate unreleased features with Coming soon behaviour without implying their source data is absent. |
| FR-COM-10 | Continue after source failure | Preserve supported last-known information with explicit limitations; do not represent a failed source read as an empty dataset. |

## 4. Action Register — Stage 1

**Purpose:** maintain an accountable register of actual work, requests and commitments. User interactions require the relevant operation right; source-driven changes require accepted evidence and mapping.

| ID | Use case | Functional requirement |
|---|---|---|
| FR-ACT-01 | Capture existing work | Import relevant ClickUp tasks and retain their stable identity, client association and source links. |
| FR-ACT-02 | Capture conversational commitments | Identify explicit requests and commitments from approved communications and meetings, retaining the original wording and context. |
| FR-ACT-03 | Separate uncertain work | Route ambiguous, potentially stale or AI-suggested items to Needs review; label proposals separately from established commitments. |
| FR-ACT-04 | Avoid duplicate obligations | Reconcile repeated references to the same obligation across tasks, messages and meetings instead of creating duplicate actions. |
| FR-ACT-05 | Find relevant actions | Search and filter by client, owner, responsibility, progress, review state and applicable deadline conditions; support complete paginated results. |
| FR-ACT-06 | Understand responsibility | Show what WIA owes, what is required from the client, the identified owner and relevant dependencies. Preserve unknown ownership. |
| FR-ACT-07 | Understand deadlines | Preserve date-only, exact-time and unknown deadlines, their source context and material conflicts. Do not invent dates. |
| FR-ACT-08 | Identify overdue work | Calculate overdue status from accepted progress, a known applicable deadline and the relevant clock/timezone. Unknown deadlines are not overdue. |
| FR-ACT-09 | Explain an action | Show its origin, supporting conversation, current state, changes, conflicts and dependencies. |
| FR-ACT-10 | Add a manual action | Let an authorised user submit a client-linked action with manual provenance. Its acceptance/review behaviour must follow the configured creation policy. |
| FR-ACT-11 | Correct ownership or deadline | Apply an audited correction when the user has resolution authority; otherwise create a proposal without changing the maintained value. |
| FR-ACT-12 | Acknowledge responsibility | Record explicit acceptance by the identified owner through supported source evidence, the owner's KB action or an enabled reaction mapping. |
| FR-ACT-13 | Preserve acknowledgement meaning | Assignment, another person's acceptance or an old owner's acknowledgement must not automatically acknowledge the current owner. |
| FR-ACT-14 | Report completion | Record Done from accepted mapped-task completion or explicit delivery evidence. Preserve the completion basis. |
| FR-ACT-15 | Verify the outcome | Require a named authorised WIA follow-up check and evidence for Verified. Enforce the configured self-verification permission. |
| FR-ACT-16 | Reopen work | Accept permitted manual reopening and genuine mapped ClickUp reopening; supersede active verification while preserving its history. |
| FR-ACT-17 | Handle later completion | A task completed again after reopening may become Done; its superseded verification must not automatically reactivate. |
| FR-ACT-18 | Propagate changes | Update dependent client views, counts and cached answers; mark affected generated artifacts stale or eligible for rebuilding. |

**Still requiring definition:** manual-action acceptance, detailed stale-request recognition, cancellation/replacement rules and acknowledgement applicability after materially changed commitments.

The first release links existing ClickUp tasks. Creating ClickUp tasks and sending external notifications remain later capabilities. A task assignment is not owner acknowledgement, and Done is not Verified. Meeting commitments take precedence over conflicting ClickUp due dates while preserving the discrepancy; other fields follow their evidence/authority rules.

## 5. Client Portfolio — Stage 1

**Purpose:** provide one maintained business record with separate service engagements.

| ID | Use case | Functional requirement |
|---|---|---|
| FR-POR-01 | Browse clients | Display the permitted active-client portfolio with business identity, service engagements and supported contextual indicators. |
| FR-POR-02 | Find a client | Search relevant business/contact fields and filter/sort the authorised portfolio. |
| FR-POR-03 | Switch presentation | Provide card/list presentation over the same underlying records and filters. |
| FR-POR-04 | Represent multiple services | Associate several engagements with one business without duplicating the business itself. |
| FR-POR-05 | Add a client | Allow authorised WIA users to create a business profile and engagements manually before automatic ingestion begins. |
| FR-POR-06 | Map sources | Associate approved accounts, contacts, channels, folders, lists and meetings with the correct business/engagement; review ambiguity. |
| FR-POR-07 | Show useful card indicators | Show consistent action counts, next-call information and supported assessments/activity/coverage states. |
| FR-POR-08 | Explain record boundaries | Distinguish engagement start, earliest obtained evidence and the period through which sources were processed. |

A detected folder, contact or payment notification must not independently activate a new client. The sections below are parts of the client record; their detailed feature depth remains subject to supported data and activation gates.

### 5.1 Now

| ID | Use case | Functional requirement |
|---|---|---|
| FR-NOW-01 | Understand the current position | Present the supported current picture with its evidence, freshness and relevant conflicts. |
| FR-NOW-02 | See immediate obligations | Show open actions, known overdue work and client dependencies using the shared action register. |
| FR-NOW-03 | Prepare for the next interaction | Show the next matched scheduled call and its available brief/state. |
| FR-NOW-04 | Understand attention and coverage | Show supported relationship/context indicators and what the record can or cannot establish. |

The maintenance/publication policy for summaries and weekly focus remains intentionally deferred. A later-feature brief or assessment may be Coming soon without blocking supported Stage 1 information.

### 5.2 Client Profile

| ID | Use case | Functional requirement |
|---|---|---|
| FR-PRO-01 | Understand the business | Maintain supported business background, audience, differentiator and voice with field-specific provenance. |
| FR-PRO-02 | Understand the engagement | Maintain goals, applicable services, programme context and supported engagement dates separately for each engagement. |
| FR-PRO-03 | Identify contacts | Show reviewed contacts, roles, emails and identity relationships without treating every participant as the primary contact. |
| FR-PRO-04 | Open the LeadLock account | Display the reviewed client/location link independently of whether individual LeadLock features are authorised. |
| FR-PRO-05 | Inspect support matters | Show supported requests/issues, affected work, latest known state, responsibility and resolution evidence. Disclose incomplete support coverage. |
| FR-PRO-06 | Inspect lead outcomes | Show supported period-based outcome snapshots once feature access and metric definitions qualify. |
| FR-PRO-07 | Correct profile information | Support audited proposals/application under the agreed editing and resolution permissions; preserve source disagreement. |

Lead outcomes and support completeness remain conditional on actual accessible evidence and definitions.

### 5.3 Engagement History

| ID | Use case | Functional requirement |
|---|---|---|
| FR-HIS-01 | Reconstruct the engagement | Present dated onboarding, communication, meeting, commitment and delivery events. |
| FR-HIS-02 | Change historical presentation | Provide timeline/spine and activity-feed views over the same canonical events. |
| FR-HIS-03 | Narrow history | Filter by lane/category and period, with stable ordering and pagination. |
| FR-HIS-04 | Understand historical evidence | Open supporting sources and distinguish event/effective time from ingestion time; explain gaps rather than implying nothing happened. |

Repeated representations of one meeting or delivery must not inflate the history.

### 5.4 Handover Brief

| ID | Use case | Functional requirement |
|---|---|---|
| FR-HAN-01 | Transfer account context | Assemble supported background, current position, outstanding obligations and known gaps from maintained records. |
| FR-HAN-02 | Inspect support and age | Identify the evidence, snapshot and limitations underlying the brief. |
| FR-HAN-03 | Copy the handover | Provide a permitted copy/export with its applicable evidence and as-of information. |

Its narrative generation/publication lifecycle remains an implementation-stage decision.

### 5.5 Commitments

| ID | Use case | Functional requirement |
|---|---|---|
| FR-CCM-01 | View client-specific obligations | Present the same action records as the global register, scoped to the selected business/engagement. |
| FR-CCM-02 | Separate responsibility | Distinguish WIA obligations and client dependencies while retaining the shared lifecycle, evidence and permissions. |

There must not be a second editable action register inside the client record. Requirements FR-ACT-01 through FR-ACT-18 apply to the same underlying records and commands.

### 5.6 Meetings

| ID | Use case | Functional requirement |
|---|---|---|
| FR-MTG-01 | Browse past conversations | List known relevant meetings, dates/types, associated businesses and available recordings/transcripts. |
| FR-MTG-02 | Inspect discussion | Open permitted transcript/excerpt context, decisions and resulting commitments with locators. |
| FR-MTG-03 | Recognise missing content | Preserve a known meeting even when its transcript is unavailable. |
| FR-MTG-04 | Reconcile representations | Link Calendar, Fathom, historical Zoom and approved archive representations without duplicating the meeting. |
| FR-MTG-05 | Handle shared meetings | Associate a meeting with multiple businesses while preventing unrelated passages from reaching restricted users. |

### 5.7 Invoices & Terms

| ID | Use case | Functional requirement |
|---|---|---|
| FR-CFIN-01 | Inspect commercial context | Show the client/engagement subset of the shared commercial records, with the finance requirements in Section 8. |
| FR-CFIN-02 | Preserve financial permissions | Prevent hidden financial data from appearing through profile history, handover, chat or exports. |

### 5.8 Attendance

| ID | Use case | Functional requirement |
|---|---|---|
| FR-ATT-01 | View programme participation | Show applicable programme membership, sessions and supported reported attendance. |
| FR-ATT-02 | Handle exceptions | Preserve start dates, holds, reschedules, missing entries and notes/counter conflicts. |
| FR-ATT-03 | Inspect attendance evidence | Link reported entries to the actual sheet/range/version or other accepted attendance evidence. |
| FR-ATT-04 | Avoid unsupported absence | Do not infer absence from an invitation, silent transcript, missing recording or missing transcript. |

Streaks, percentages and escalation rules require an agreed programme definition before activation.

## 6. Call Preparation — Stage 2

**Purpose:** prepare a cited, purpose-specific brief for the actual scheduled conversation.

| ID | Use case | Functional requirement |
|---|---|---|
| FR-CAL-01 | Browse scheduled conversations | Display matched calendar occurrences with actual start/end, timezone, duration, host where established and cancellation state. |
| FR-CAL-02 | Select the relevant period | Filter scheduled calls by meaningful date ranges and client scope. |
| FR-CAL-03 | Resolve call context | Associate the occurrence with the correct business/engagement and supported call purpose/type; expose ambiguity. |
| FR-CAL-04 | Understand the current position | Assemble relevant current facts, recent developments, preceding discussion and unresolved issues. |
| FR-CAL-05 | Prepare an agenda | Suggest an agenda grounded in the call purpose, client asks and outstanding decisions; label recommendations. |
| FR-CAL-06 | Identify required client inputs | Surface established requests, approvals and dependencies separately from proposed questions. |
| FR-CAL-07 | Keep commitments visible | Include current shared action records rather than an obsolete copy of their state. |
| FR-CAL-08 | Explore an opportunity | Present supported opportunities as interpretation/proposals, without introducing unapproved research sources. |
| FR-CAL-09 | Inspect and share the brief | Provide citations, source/as-of information, readiness/limitations and permitted copy/download. |
| FR-CAL-10 | Respond to changes | Invalidate or mark the brief stale after relevant rescheduling, cancellation, new evidence, correction or action changes. |

The precise preparation schedule remains configurable. A future invitation must never be treated as a completed meeting.

## 7. Health & Sentiment — Stage 3

**Purpose:** provide an explainable assessment of engagement, alongside supported lead outcomes.

| ID | Use case | Functional requirement |
|---|---|---|
| FR-HEA-01 | Browse engagement assessments | Display permitted client assessments and category-based filters/counts with applicable periods. |
| FR-HEA-02 | Explain an assessment | Show the actual drivers, supporting evidence, coverage, uncertainty and material conflicts. |
| FR-HEA-03 | Understand client feedback | Distinguish attributed client concerns/praise from internal interpretation and existing AI analysis. |
| FR-HEA-04 | Assess follow-through | Incorporate supported commitment, completion, verification and unresolved-support information. |
| FR-HEA-05 | Include programme context | Use relevant onboarding/attendance context without equating absence or silence with dissatisfaction. |
| FR-HEA-06 | Inspect lead handling/outcomes | Present defined inquiry, consultation/tour, booked-client and conversion measures where records support them. |
| FR-HEA-07 | Suggest a response | Present a supported next-step proposal and links to existing obligations without automatically creating work or outreach. |
| FR-HEA-08 | Preserve uncertainty | Represent missing access, incomplete history and unassessed accounts explicitly; do not assign healthy/negative states from missing data. |

Health-category rules, lead-stage/cohort definitions and publication conditions remain required inputs. A combined numerical health score is not currently agreed.

## 8. Invoices & Contracts — Stage 3

**Purpose:** provide a trustworthy commercial record at the level supported by the evidence.

| ID | Use case | Functional requirement |
|---|---|---|
| FR-FIN-01 | Record commercial notifications | Capture supported Dubsado signing, payment and reminder events from Gmail with source identity and date basis. |
| FR-FIN-02 | Associate commercial records | Resolve the correct business, engagement, project, invoice or agreement using reviewed mappings. |
| FR-FIN-03 | Prevent double counting | Reconcile repeated representations of the same payment/event across notifications, reminders and replies. |
| FR-FIN-04 | Inspect agreements | Show accessible supported terms, agreement identity/version and signing evidence; distinguish a document link from parsed terms. |
| FR-FIN-05 | Browse invoices | Display supported invoice identity, issue/due dates, amounts, balances and standing, with filters. |
| FR-FIN-06 | Understand payment state | Distinguish reported payment receipt from a reconciled fully paid invoice; support partial/unknown allocation states. |
| FR-FIN-07 | Inspect totals | Calculate collected and outstanding measures only from adequate supported records, stated periods and compatible currencies. |
| FR-FIN-08 | Inspect reminders | Show actual sent reminders linked to the correct invoice; do not treat drafts as sent or reminders as proof of current debt. |
| FR-FIN-09 | Explain limitations | Support an events-only presentation when full invoice/balance/terms evidence is unavailable. |
| FR-FIN-10 | Preserve commercial authority | Do not use conversation claims or an unexplained GHL pricing field to amend signed terms or establish payment. |

The tested notifications do not yet establish a complete reconciled ledger. Payment collection, invoice sending and financial-system writes are outside these display requirements.

## 9. Overview — Stage 3

**Purpose:** combine maintained modules into a useful current workspace.

| ID | Use case | Functional requirement |
|---|---|---|
| FR-OVR-01 | Orient the user | Show the authenticated user and actual local date/time context. |
| FR-OVR-02 | Understand the portfolio | Show permitted active-business counts and clearly defined service-engagement breakdowns. |
| FR-OVR-03 | Plan today's conversations | Show eligible calls today and the next upcoming occurrence, handling no-call and unavailable-calendar states. |
| FR-OVR-04 | See outstanding work | Show consistent open, known-overdue and follow-through indicators from the shared action register. |
| FR-OVR-05 | Identify accounts needing attention | Show supported assessment flags with actual drivers; an unassessed account is not automatically healthy. |
| FR-OVR-06 | Open the next brief | Present the matching brief's actual ready, stale, processing or unavailable state. |
| FR-OVR-07 | Inspect the portfolio preview | Show consistent client/action/assessment/activity information and navigate to the underlying records. |
| FR-OVR-08 | Listen to a client signal | Show a supported attributed quotation with context, date and evidence; omit it when no suitable evidence exists. |

The application must use an activated permitted landing view before Overview is enabled.

## 10. Chatbot — Delivery position open

**Purpose:** answer questions about permitted KB records and evidence, using the selected hybrid methodology and its evaluation gates.

| ID | Use case | Functional requirement |
|---|---|---|
| FR-CHT-01 | Ask globally or contextually | Accept questions from the chatbot tab or a client/action/meeting/evidence context with explicit scope. |
| FR-CHT-02 | Resolve references | Resolve 'this client', 'my tasks', 'that call' and follow-ups to validated entities; clarify material ambiguity. |
| FR-CHT-03 | Preserve conversation scope | Keep pinned scope visible; navigation must not silently change the client discussed in an existing thread. |
| FR-CHT-04 | Read maintained facts | Answer supported owner, deadline, status, profile and definition questions using authoritative records. |
| FR-CHT-05 | List and count | Answer complete scoped lists/counts using the defined record set, not the number of retrieved passages. |
| FR-CHT-06 | Recall meetings | Identify the correct relevant completed meeting and explain its supported discussion; disclose missing latest-call content. |
| FR-CHT-07 | Explain commitments | Explain an action's origin, context, changes, dependencies and current-versus-historical state. |
| FR-CHT-08 | Explain changes | Answer period/call-boundary questions using dated events and changes, with coverage limitations. |
| FR-CHT-09 | Explain assessments and figures | Use the actual assessment/metric definition, period, drivers and supporting records. |
| FR-CHT-10 | Compare permitted clients | Compare compatible facts/measures within explicit client and period boundaries; disclose inconsistent definitions or coverage. |
| FR-CHT-11 | Provide recommendations | Produce bounded, supported recommendations labelled as proposals, without treating them as established obligations. |
| FR-CHT-12 | Provide evidence | Attach valid citations and permitted navigation links to substantive factual answers. |
| FR-CHT-13 | Handle uncertainty | Return clarification, partial, conflict, no-evidence or unavailable outcomes when appropriate; state the checked scope. |
| FR-CHT-14 | Reuse safely | Answer repeated/paraphrased questions consistently while respecting current data, permissions, time boundaries and changed meaning. |
| FR-CHT-15 | Maintain private conversations | Keep saved threads private to their owner and reapply current access to historical content and late results. |
| FR-CHT-16 | Explain changing snapshots | Distinguish displayed-page information from a newer maintained value and explain relevant changes. |
| FR-CHT-17 | Show execution state | Provide progress and a terminal outcome for longer work, with supported cancellation behaviour. |
| FR-CHT-18 | Respect the action boundary | Provide links and proposals without creating ClickUp tasks, sending notifications or executing unrestricted tools. |

KB-only versus controlled live reads remains test-dependent. Semantic similarity alone must not permit answer replay. The [chatbot scope](../../../chatbot_KB.md) specifies exact/direct paths, dependency-valid reuse, guarded semantic intent routing, versioned embedding reuse and bounded generation. Semantic full-answer replay remains disabled initially. Private threads are not a shared evidence corpus; admins have operational-metadata access only.

## 11. Source Library, evidence drawer and global search

| ID | Use case | Functional requirement |
|---|---|---|
| FR-EVI-01 | Browse evidence | List authorised retained excerpts by client, engagement, provider, date and relevant classification. |
| FR-EVI-02 | Search context | Search permitted clients, actions and evidence without leaking hidden records through suggestions or counts. |
| FR-EVI-03 | Inspect an excerpt | Show exact retained text, source/version, author/speaker, dates and an appropriate message/timestamp/page/range locator. |
| FR-EVI-04 | Understand provenance | Show which maintained fact, action or interpretation the evidence supports. |
| FR-EVI-05 | Open an original | Offer an authorised original-reference path where available; distinguish KB excerpt access from direct provider access. |
| FR-EVI-06 | Handle changed/deleted sources | Preserve the selected retained evidence with appropriate deletion/version warnings; distinguish temporary access failure. |
| FR-EVI-07 | Handle expiry | Withdraw expired content and dependent unsupported outputs according to retention policy. |

A source-excerpt count must not be presented as a count of original meetings, files or complete historical coverage. Confirmed upstream deletion retains facts/excerpts with warnings under the selected policy; category expiry is a separate lifecycle event.

## 12. Connections

| ID | Use case | Functional requirement |
|---|---|---|
| FR-CON-01 | Inspect connection identity | Show the actual registered provider account, approved scope and available capabilities without exposing secrets. |
| FR-CON-02 | Inspect synchronisation | Show last successful sync, lag and relevant processing/coverage state. |
| FR-CON-03 | Distinguish capability failures | Separate connected account discovery from authorised feature reads; show blocked, expired, failed and partial states. |
| FR-CON-04 | Request refresh | Allow a permitted supported refresh and expose its processing/result state without falsely reporting immediate publication. |
| FR-CON-05 | Repair authorisation | Support the authorised connection/re-authorisation workflow and preserve last-known records while access is unavailable. |
| FR-CON-06 | Inspect coverage gaps | Show inaccessible, unsupported, unprocessed and unresolved material separately. |

## 13. Review, correction and change-awareness workflows

These are required operating functions. Their complete screens are not present in the current mock.

| ID | Use case | Functional requirement |
|---|---|---|
| FR-REV-01 | Find review work | List scoped identity ambiguities, stale actions, missing fields, proposals and conflicting observations. |
| FR-REV-02 | Understand a discrepancy | Compare the maintained value, incoming claim, supporting sources and relevant history. |
| FR-REV-03 | Submit a correction | Allow permitted editors to propose a typed change with reason/support while preserving the maintained value. |
| FR-REV-04 | Apply or reject | Let an authorised resolver apply/reject a proposal or apply a direct correction with an audit trail. |
| FR-REV-05 | Preserve decisions | Keep accepted corrections and rejected proposals effective across later re-extraction; route new material conflicts for review. |
| FR-REV-06 | Resolve mapping ambiguity | Associate evidence with the correct business/engagement/person through a reviewed mapping outcome. |
| FR-REV-07 | Track awareness | Maintain per-user read state for the exact viewed change revision; later changes remain unread. |
| FR-REV-08 | Separate awareness from resolution | Reading must not acknowledge an action, accept a correction, resolve a conflict or verify completion. |
| FR-REV-09 | Apply changes consistently | Propagate accepted decisions to maintained projections and dependent answers/artifacts. |

## 14. User and business administration

| ID | Use case | Functional requirement |
|---|---|---|
| FR-ADM-01 | Add a user | Create/link the central identity through the supported interface, then establish KB membership and configured grants. |
| FR-ADM-02 | Handle partial provisioning | Expose retryable incomplete setup without resetting an existing shared account or falsely reporting full activation. |
| FR-ADM-03 | Configure visibility | Control permitted clients and whole modules/sections; individual-field visibility remains later scope. |
| FR-ADM-04 | Configure operation rights | Manage custom roles and per-user Inherit/Allow/Deny overrides within permitted scope. |
| FR-ADM-05 | Inspect effective rights | Explain effective permissions and their origin, including explicit denial and self-verification rights. |
| FR-ADM-06 | Revoke KB access | Remove KB membership/access without automatically disabling the central account; enforce revocation on subsequent delivery. |
| FR-ADM-07 | Configure acknowledgement | Define eligible emoji/meaning mappings before reaction-based acknowledgement is enabled. |
| FR-ADM-08 | Configure retention | Manage category policies and their effects on retained records, temporary originals, conversations and derivatives. |
| FR-ADM-09 | Inspect operations | Show permitted usage, cost, run state and sanitised technical errors. Private chat-content inspection remains excluded. |
| FR-ADM-10 | Audit administration | Record who changed access, mappings and business policies, when they changed and what was affected. |

Actual role defaults, retention durations and central account-enrolment behaviour still need configuration/contracts. Explicit per-user Deny wins over role grants; Allow remains within already permitted client/module scope and cannot restore revoked membership. Normal verification authority and configured self-verification permission are separate requirements.

## 15. Automated intake and maintained-knowledge functions

These requirements operate behind every view.

| ID | Use case | Functional requirement |
|---|---|---|
| FR-INT-01 | Initialise a mapped client | Start approved-source ingestion after the business, engagements and mappings are established. |
| FR-INT-02 | Backfill history | Process all obtainable in-scope history across all eight approved sources for active clients before first launch. |
| FR-INT-03 | Receive ongoing changes | Accept supported source notifications and reconcile authoritative changed records. |
| FR-INT-04 | Map identities | Resolve business, engagement, person and source relationships; send unresolved associations for review. |
| FR-INT-05 | Process approved content | Process readable text, Docs/Sheets, extractable PDF/DOCX and existing transcripts; retain excluded media/scans as references with coverage states. |
| FR-INT-06 | Maintain provenance | Preserve source identity/version, locators, event/effective/observed times and supporting excerpts. |
| FR-INT-07 | Extract observations | Capture supported facts, requests, commitments, decisions, issues and commercial events without inventing missing fields. |
| FR-INT-08 | Apply authority rules | Resolve maintained state by field/evidence policy, preserve reviewed corrections and expose material ambiguity. |
| FR-INT-09 | Reconcile duplicates | Prevent repeated deliveries and cross-source representations from duplicating actions, meetings or financial events. |
| FR-INT-10 | Resume interrupted processing | Continue safely after failure/restart and distinguish retryable, blocked and unsupported work. |
| FR-INT-11 | Publish changes | Update accepted state and dependent views/answers consistently, preserving review and freshness information. |
| FR-INT-12 | Account for historical gaps | Produce source/client coverage reports and record WIA's acceptance or recovery of unresolved launch gaps. |

The eight approved sources remain Gmail, Slack, ClickUp, historical Zoom, Fathom, Drive, LeadLock and Calendar. Dubsado notifications enter through Gmail. Existing Viktor posts are retained as attributed analysis within those boundaries. No fresh paid-media, Shopify, website-research, ChatGPT-history or separate-upload intake is introduced here.

Full historical processing does not require permanent retention of full originals. Persist the selected facts/excerpts and provenance; fetch authorised originals on demand under the selected policy and applicable chat mode. No OCR or new media transcription is included.

## 16. Operational functions

| ID | Use case | Functional requirement |
|---|---|---|
| FR-OPS-01 | Monitor processing | Expose relevant connector, queue, run and coverage failures to permitted operators. |
| FR-OPS-02 | Recover failed work | Support bounded retry/reconciliation without duplicating accepted business effects. |
| FR-OPS-03 | Reprocess changed contracts | Track processing versions and support controlled reprocessing while preserving human decisions and source limitations. |
| FR-OPS-04 | Enforce retention | Apply expiry/cleanup and revise affected search, evidence, artifact and cache state. |
| FR-OPS-05 | Recover service | Restore maintained data and validate permissions, decisions, verification history and checkpoints before reopening access. |
| FR-OPS-06 | Account for usage | Record applicable processing/model/specialist usage and costs without exposing private conversation content through operational metadata. |

## 17. Traceability and verification

Use each requirement ID in the implementation task and its acceptance case. The implementation should identify the actor/authority, trigger/input, affected canonical records, expected visible outcome, evidence/coverage conditions, permitted exceptions and applicable activation gate. Shared use cases reuse domain records and commands rather than create divergent rules per screen.

The [Solution Architecture](Client-Knowledge-Base-Solution-Architecture.md) supplies source-to-component mappings, proposed APIs/data contracts, state transitions, RAG/caching mechanisms and meaningful acceptance examples. The [chatbot scope](../../../chatbot_KB.md) supplies semantic/direct-answer/cache evaluation cases. Source feasibility remains recorded in the [verification register](../../../tobeverified_knowledgebase.md), [financial-source checks](../../../tobeverified.md) and [clarification register](../../../tobeclarified.md).

Mark a requirement implemented/verified only against its stated behaviour and evidence conditions. A successful provider request, JSON-schema validation or fictional preview interaction does not alone establish end-to-end acceptance. Missing source support must result in the specified unavailable/partial/review state rather than an invented value.

## 18. Definitions and dependencies still requiring closure

The catalogue covers the identified views and supporting use cases. The following items remain explicit prerequisites for the affected behaviour:

| Area | Remaining decision or evidence |
|---|---|
| Action recognition | Clear-current versus stale criteria, manual-entry acceptance and cancellation/replacement handling |
| Narrative fields | Summary, focus and handover maintenance/publication lifecycle; intentionally deferred to implementation |
| Measures | Activity, coverage, lead cohorts/stages, attendance and health-category definitions |
| Finance | Accessible terms and sufficient invoice/payment reconciliation |
| Source readiness | LeadLock feature access, historical Zoom coverage and complete ongoing-delivery qualification |
| Administration | Actual grants, retention periods, identity provisioning and enrolment contracts |
| Client lifecycle | Behaviour when a client/engagement becomes inactive, including future ingestion and retained history |
| Chatbot | Source-freshness mode, eligible specialists and delivery position |

Performance, responsiveness, recovery-time targets, security mechanisms and running-cost targets accompany this catalogue as non-functional requirements and technical constraints. Their functional effects, including access denial, progress, freshness warnings and recovery behaviour, are included above. This document does not select new thresholds, business definitions, delivery dates or extra sources.
