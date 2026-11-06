# Content Atelier — Project Agenda

**Project:** Content Atelier for Wedding Industry Ads (WIA)  
**Document updated:** 14 October 2026  
**Purpose:** A single starting point for understanding why the project exists, what it should achieve, how it works, who uses it, and what remains to be delivered.

Content Atelier is WIA's internal editorial intelligence and content development workspace. It turns the useful thinking already present in client conversations, team discussions, and business knowledge into distinct content opportunities, researched production briefs, and eventually approved content packs.

Its central editorial question is:

> What does this conversation reveal that would help a relevant wedding business owner understand WIA's perspective, value its expertise, or see how its work could help them?

The project combines AI assistance, retrievable source evidence, content memory, and human editorial decisions. Its intended outcome is a repeatable weekly process in which Whitney can make clear creative decisions and Giselle can produce content from an approved direction with substantially less preparation and rewriting.

**The full product vision extends beyond the current implementation.** The backend has implemented weekly angle processing, historical comparison, researched brief generation, and approval controls through Gate 2. Recorded live brief pilots have produced drafts with unresolved validation and editorial blockers. The Weekly Studio demonstrates the broader journey using saved content and browser-local state. Production pack generation and external publishing are separate delivery stages. See [Current implementation](#11-current-implementation-and-its-limits).

## Contents

1. [Why the project exists](#1-why-the-project-exists)
2. [Target outcomes and measures of success](#2-target-outcomes-and-measures-of-success)
3. [People, responsibilities, and audience](#3-people-responsibilities-and-audience)
4. [The editorial agenda](#4-the-editorial-agenda)
5. [Inputs and the knowledge foundation](#5-inputs-and-the-knowledge-foundation)
6. [Core concepts](#6-core-concepts)
7. [The complete operating process](#7-the-complete-operating-process)
8. [Human approval and decision ownership](#8-human-approval-and-decision-ownership)
9. [The application experience](#9-the-application-experience)
10. [Architecture, memory, and reliability](#10-architecture-memory-and-reliability)
11. [Current implementation and its limits](#11-current-implementation-and-its-limits)
12. [Delivery agenda and completion criteria](#12-delivery-agenda-and-completion-criteria)
13. [Decisions still needed](#13-decisions-still-needed)
14. [Repository guide and further reading](#14-repository-guide-and-further-reading)

## 1. Why the project exists

WIA's everyday work contains valuable material: a team member explaining a campaign decision, a client describing what couples misunderstand, a landing-page discussion that reveals positioning, or a question that exposes a recurring objection. Much of that knowledge stays inside recordings, transcripts, and individual team members' memories.

Turning those conversations into useful marketing requires several different kinds of work. Someone must find the relevant exchange, understand the surrounding context, identify the larger point, decide who would care, check the evidence, compare it with previous content, choose a direction, and develop it into usable material. Repeating that work manually makes content creation dependent on attention, availability, and recall.

The difficulty also extends beyond finding a quotable sentence. An accurate transcript summary can still produce a weak angle. A narrow technical tip can overlook a more valuable story about WIA's judgment or collaboration. A polished hook can conceal a generic idea. A recent client example can repeat an argument the audience has already heard.

The project therefore has four connected jobs:

- **Discover:** Find worthwhile opportunities in the work WIA is already doing, including expertise, process, offer value, audience insight, and supported proof.
- **Select:** Explain why an opportunity deserves attention, how it serves WIA's strategy, and what makes it different from nearby alternatives.
- **Develop:** Carry the selected idea into a researched brief and useful content formats while preserving its evidence, purpose, and voice.
- **Remember:** Retain sources, decisions, feedback, and actual content use so each week builds on the previous work.

## 2. Target outcomes and measures of success

### 2.1 Business outcome

Content should help suitable wedding business owners discover WIA, trust its thinking, and understand the value and fit of its services. Over time, that should support qualified demand for ELEVATE, the Ads Accelerators, and LeadLock. The project does not assume that every individual piece should sell an offer or produce an immediately attributable booking.

### 2.2 Editorial outcome

Whitney should receive a set of worthwhile directions that already contain the missing strategic thinking: the central point, intended audience, reason to care, source demonstration, and development direction. She should be able to choose and steer ideas without having to discover their real significance herself.

The strongest indicator is approval with little strategic rewriting. Valid JSON, a high model score, or a polished title cannot establish that result.

### 2.3 Operational outcome

The intended weekly output is:

| Output | What it enables |
| --- | --- |
| An auditable source batch | The team can see what was included, missing, duplicated, or only partially processed. |
| A ledger of useful moments | Important exchanges and their surrounding context remain retrievable. |
| Distinct candidate angles | Whitney can compare supported opportunities and understand the selection reasons. |
| Explicit holds and internal insights | Promising but incomplete ideas and useful non-public learning are retained. |
| Approved, researched production briefs | Giselle has a clear message, evidence, boundaries, CTA direction, and format guidance. |
| An agreed content pack | Approved briefs can become email, carousel, reel scripts, and supporting captions. |
| An updated content and feedback history | Later runs can recognize repetition and apply relevant editorial corrections. |

Earlier product documents proposed roughly five to ten minutes of weekly founder review across three gates. Treat this as a design aspiration to measure in practice. It is not an achieved service level, and weeks with difficult evidence or substantial revisions will need more attention.

### 2.4 How success should be evaluated

Measure founder review and editing time, acceptance without major reframing, useful opportunities missed, unsupported claims, attribution mistakes, repeated central points, and the quality of holds and internal insights. Also track production readiness, turnaround time, failed or incomplete runs, and provider cost with cache reuse shown separately.

Establish numerical acceptance targets after a real review baseline. Engagement and commercial performance can inform later decisions, but they must be tied to actual published content and measured outcomes.

## 3. People, responsibilities, and audience

### 3.1 Project users

| Person or role | Responsibility |
| --- | --- |
| **Whitney — founder and editorial decision owner** | Determines worthwhile directions, supplies strategic corrections, steers CTAs, and approves content within the agreed workflow. Her latest explicit editorial instructions take precedence over conflicting historical examples. |
| **Giselle — content production** | Develops approved material into designed, edited, and prepared assets; identifies production gaps; and handles downstream work within explicitly delegated authority. |
| **WIA practitioners and client-facing team** | Supply the conversations, recommendations, questions, and practical expertise that make the content credible. Their contributions must retain accurate attribution. |
| **Engineering and operations** | Maintain intake, storage, prompts, jobs, access controls, evaluation, and recovery. Technical administration does not confer editorial approval authority. |
| **AI services** | Assist with discovery, synthesis, research planning, and drafting. Their assessments remain proposals subject to source validation and human review. |

Production approval may be delegated when WIA explicitly agrees who can make it. A team login alone should not imply permission to approve every gate.

### 3.2 Intended content audience

WIA speaks to venue owners, photographers, planners, videographers, and other wedding professionals who may benefit from its advertising expertise and supporting systems. Many are experienced business owners who already understand marketing and have invested in growth. Content should respect that experience.

The person speaking in a recording is the source participant. The intended audience is the prospective WIA client who would find the point useful. Those audiences can differ: a photographer's messaging discussion may reveal a process relevant to several wedding professions, while a particular venue campaign decision may need to remain venue-specific.

Choose the broadest audience that preserves the insight and its factual support.

## 4. The editorial agenda

### 4.1 Make WIA's thinking visible

Content should reveal what WIA notices, the questions its team asks, how it works with clients, and why a recommendation makes sense. Client collaboration, positioning work, campaign reasoning, and thoughtful implementation can all be valuable material without a dramatic result story.

For example, an imagery discussion might support an angle about helping a business choose visuals for the couples it wants to attract. That direction can show WIA's process and judgment. It does not establish that a new page was launched or that bookings increased.

### 4.2 Follow the established content strategy

Savannah's strategy supplies the purpose and packaging framework. Whitney's founder guidance supplies the expression and reasoning style.

| Primary pillar | Intended audience effect | Typical content directions |
| --- | --- | --- |
| **ATTRACT** | Reach relevant new people and create interest. | Supported opinions, founder perspectives, campaign breakdowns, and relevant trends. |
| **WARM** | Build trust and deepen understanding of WIA's judgment. | Thought shifts, positioning, processes, behind-the-scenes work, education, and founder stories. |
| **CONVERT** | Make an offer's value and suitability tangible. | Solution selling and properly supported social proof. |

Choose a primary pillar according to the piece's intended effect. The weekly mix should follow the current content plan and available evidence. There is no established requirement for equal pillar percentages or three differently labelled versions of each conversation.

### 4.3 Connect offers when the idea supports the connection

ELEVATE is the ongoing advertising partnership; the Ads Accelerators are guided implementation paths; LeadLock supports inquiry management and follow-up. These provide meaningful commercial context, but individual features, delivery scope, prices, and availability need current verified records.

A service step, platform capability, client configuration, and measured result are separate claims. Content must not turn a proposed workflow into an existing service promise or extend WIA's work into unsupported branding, sales-management, or booking guarantees.

An offer connection or immediate CTA is optional during opportunity discovery. Where a draft needs a CTA, its destination and promise should follow the approved direction and current campaign objective.

### 4.4 Preserve the founder's voice

The desired voice is calm, confident, warm, curious, and specific. Explain the reasoning behind a useful point in familiar language. Avoid talking down to owners, forcing controversy, using generic growth promises, or treating every piece as a sales pitch.

Use first person for Whitney's actual experience or perspective, and “we” for WIA's work. Team expertise can become company content without assigning the experience to Whitney. Captions should add useful context or another implication while staying aligned with the main piece.

For finished material, use the established sequence where appropriate: **Hook → Problems, Desires, or Symptoms → Main Point → Transformation → CTA.** Transformation can be a change in understanding when no implemented outcome has been established.

## 5. Inputs and the knowledge foundation

| Input | Purpose | Current boundary |
| --- | --- | --- |
| Historical Zoom transcripts and supplied metadata | Establish the initial evidence archive and exercise the workflow chronologically. The broader backfill intention is roughly three months. | Current SQL admission uses supplied local transcript files. Folder or batch labels do not prove an individual recording date. |
| New Fathom transcripts and metadata | Supply ongoing client and team conversations. | Supplied exports support editorial examples; an operational continuous connector remains separate work. Summaries cannot replace the transcript evidence contract. |
| Relevant Slack discussions and wins | Surface questions, objections, client experiences, and useful delivery context. | Part of the broader intake agenda; not an established live connector in the current SQL workflow. |
| Founder notes, voice notes, and additional documents | Capture intentional perspectives and context that may not appear in meetings. | Additional source types need deliberate intake and evidence handling. |
| Brand, voice, strategy, and offer records | Define selection standards, expression, positioning, scope, and current commercial facts. | Use curated, dated references and an explicitly reviewed brand bundle for live briefing. |
| Past angles, briefs, content, and decisions | Supply repetition checks, previous-use context, and relevant editorial feedback. | Only the history actually present can be assessed. Generated, approved, and published records have different meanings. |
| Optional external research | Add public framing, audience questions, or relevant market context. | A production web adapter is not configured. External material cannot prove an internal client outcome. |

Every run needs purpose-built context: relevant source material, current knowledge, applicable feedback, and useful history. Accumulating an entire conversation history is not a substitute for maintaining those references.

Knowledge changes should retain their date, source, scope, and status. Separate permanent preferences, temporary campaign instructions, offer facts, and case-specific restrictions. The handbook's precedence is latest explicit Whitney instruction, current verified strategy and offer records, established guidance, historical approved examples, then model suggestions. Transcript evidence remains authoritative about what was said in its own exchange.

## 6. Core concepts

| Concept | Meaning |
| --- | --- |
| **Source / transcript** | The preserved underlying conversation or document, with the identifiers and metadata actually available. |
| **Chunk / passage** | A retrievable part of a source linked back to its original text. It is a search unit, not automatically an editorial idea. |
| **Moment** | A useful exchange with enough surrounding context to understand what was discussed, who contributed, and what remains uncertain. |
| **Angle / content opportunity** | One defensible central point for a particular audience, with a strategic purpose and a reason to develop it. A topic or a different hook alone is insufficient. |
| **Research dossier** | The frozen supporting evidence, prior-content context, gaps, and research decisions gathered for an approved angle. |
| **Production brief** | The reviewed development plan: message, narrative, supported claims, voice, CTA, format direction, questions, and sources. It can contain detailed script or copy direction without establishing final asset approval. |
| **Content pack** | The agreed set of production assets developed from approved brief revisions. Several approved ideas may contribute to a weekly pack. |
| **Approval gate** | A recorded human decision on a specific version that authorizes the next stage. |
| **Content memory** | The history of ideas, evidence, decisions, revisions, and actual use that supports freshness and better future selection. |

## 7. The complete operating process

The intended journey is:

```text
Sources and current knowledge
  → verified weekly evidence
  → useful moments
  → distinct content opportunities and explicit holds
  → Gate 1: choose the direction
  → research dossier and production brief
  → Gate 2: approve the brief
  → agreed pack plan and content drafts
  → Gate 3: approve the production handoff
  → human production and confirmed use
  → content memory and editorial feedback
```

### Step 1 — Establish the week's sources and coverage

Admit the chosen source files, preserve their originals, and record what belongs to the batch. Identify repeated captures so one conversation does not become multiple independent examples of recurrence. Keep missing metadata explicit and distinguish the source window from the processing date.

The current transcript workflow prepares a lossless whole-week extraction input. It must not silently summarize, omit dialogue, or split a week to fit a request. If the selected request cannot be processed completely, report that limitation and choose a deliberate next action. Continuous source intake and scheduled processing are part of the wider operating model, not a verified installed schedule.

### Step 2 — Discover useful moments in context

The first main language-model stage examines the conversations for expertise, process and collaboration, service value, audience insight, broader principles, and supported transformation. Preserve the setup, questions, rationale, client contribution, and any result or unresolved issue needed to interpret a selected exchange.

Validate quotations and source references before accepting a moment. A proposal remains a proposal, and an unverified speaker label remains unverified. If only part of an extraction passes validation, retain the failed records and label any accepted partial pool accurately.

### Step 3 — Develop content opportunities

The second main language-model stage asks what each useful exchange could mean for WIA's audience. It may combine evidence or discover several substantive directions from one conversation.

A reviewable opportunity should explain:

- Its working title and central point.
- Who should care and what they should understand, believe, or do afterward.
- Its strategic purpose and primary pillar.
- What the source actually demonstrates, including WIA's contribution where supported.
- Why this direction deserves development and how it differs from alternatives.
- Its claim boundaries, missing context, and useful development direction.

Do not force a conflict, immediate reader action, format, or offer into every candidate. A process story can be valuable without a measured result or a dramatic tension.

### Step 4 — Give each finding an explicit disposition

The latest handbook defines the following editorial dispositions. They describe the intended review behavior; they are not a claim that every label is already implemented as a backend state.

| Disposition | Meaning |
| --- | --- |
| **SELECT** | A worthwhile and sufficiently supported direction is ready for editorial development. |
| **REFRAME** | The evidence is useful, but the proposed direction needs a better central point, breadth, or purpose. |
| **HOLD** | A promising direction needs an exact missing segment, verification, or material detail. |
| **INTERNAL** | The finding belongs in audience research, sales, delivery, or product learning. |
| **SKIP** | The material does not support a strong, distinct, relevant public opportunity. |

Preserve useful objections and negative feedback. An affordability concern may be internal intelligence, while an incomplete product demonstration from the same call may remain on hold.

### Step 5 — Compare with history and select distinct opportunities

Check eligible candidates against earlier angles and each other. Compare the central point, intended audience shift, process shown, and meaningful supporting evidence. A changed title, client name, or pillar does not establish a new angle.

The implemented comparison workflow uses stored embeddings, exact numerical comparisons, recorded historical context, and freshness calculations. It evaluates provisional cutoff scenarios and can make one targeted refinement pass. Refinement is an attempt to recover a materially different supported direction, not a separate model verdict that similarity is factually settled.

Keep provisional scores and thresholds distinguishable from founder-calibrated editorial judgment. The global authoritative comparison cutoff remains an open configuration decision; an individual pilot's selection does not set it permanently.

Present all qualifying, distinct candidates without padding to a quota or arbitrarily hiding strong ideas. Production capacity is decided later. An empty or small qualified set is a valid result when its limits are clear.

### Step 6 — Gate 1: choose the direction

Whitney or an explicitly authorized approver reviews the central point, selection reason, audience, evidence, and similarity context. She can approve, steer, reject, or defer it, and establish CTA direction when required for development.

Approval must refer to the exact reviewed version. For the enabled briefing workflow, the approval and initial brief intent are recorded together. Missing configuration, incomplete evidence, or unresolved comparison policy should remain visible blockers.

### Step 7 — Research the approved angle

Carry the original supporting passages into a frozen dossier, then search permitted transcript history for useful additional evidence. The current brief implementation combines semantic and full-text retrieval, expands results back to original passages, and records selection decisions and research gaps.

Inspect prior arguments and actual brief or publication use separately. This helps distinguish a new point from a refresh, consolidation, or substantially repeated treatment. Missing history must remain an acknowledged limitation.

Optional public research can add context when a configured provider is available. It must remain distinguishable from internal evidence, and its absence should be labelled rather than replaced with invented trends or statistics.

### Step 8 — Develop and validate the production brief

Build a coherent plan from the approved direction and dossier. It should give production enough substance: reader promise, central insight, message spine, narrative, supported claims, differentiation, voice, CTA, format treatments, creative direction, unresolved questions, and source references.

The current implementation includes deterministic source, quotation, claim-status, and number checks, plus a scoped support and differentiation review. It permits at most one automatic brief repair. A remaining defect becomes review work or a blocked state rather than an indefinite rewriting loop.

### Step 9 — Gate 2: approve the brief

The approver checks the message, evidence, voice, CTA, permissions, and open questions. She can edit, answer steering questions, request revision, reject, or approve the specific brief revision.

Substantive edits require the applicable checks to remain current. A human answer can supply direction but does not become proof that a client outcome occurred. Brief approval does not itself authorize publication or establish that a production pack exists.

### Step 10 — Agree the pack plan and create drafts

Translate approved briefs into an agreed weekly production plan. The frontend product specification proposes one email, one carousel of seven to ten slides, one to three reel scripts, and long and short captions for the carousel and reels. Current demonstrations often show the full five-piece selection of email, carousel, and three reels.

These are planning defaults. Confirm the actual quantities and assignments against WIA's production capacity. An unlimited number of qualified angles does not require a complete pack for every angle.

Give each format a distinct job while retaining the same governing message and evidence. Every asset should reference its approved brief revision. Automated pack generation in the real SQL workflow remains future work.

### Step 11 — Gate 3, production handoff, and actual use

Review the resulting drafts for message alignment, claims, voice, CTA, and production readiness. Record the final authorized handoff. Giselle can then create designs, edit video, and prepare email or social assets in the team's chosen tools, including Canva and Descript where appropriate.

The existing scheduling interface simulates planning and scheduling. It does not publish to external channels. Any later publishing integration needs an explicit delivery scope and must record actual provider confirmation before treating an item as published.

### Step 12 — Capture feedback and improve the next cycle

Record the original direction, evidence, decision, exact feedback where available, revision, and category of correction. Distinguish approved direction from approved wording and actual publication.

Apply reusable corrections at the right scope. One rejection of a technical angle does not prohibit all technical education. Improvements should be tested on unseen recordings so the system learns the selection principle rather than copying preferred sample titles.

## 8. Human approval and decision ownership

| Gate | Decision | What should be available | What it authorizes |
| --- | --- | --- | --- |
| **Gate 1 — Angle** | Is this the direction worth developing? | Central point, audience, purpose, selection reason, source context, differences from history, and any needed CTA steer. | Research and brief development for the approved version, when configured. |
| **Gate 2 — Brief** | Is the message and development plan ready for production? | Dossier, source boundaries, message spine, narrative, voice, CTA, questions, checks, and current revision. | Downstream pack development under the agreed plan. The present backend stops this scope without automatically creating a pack. |
| **Gate 3 — Pack** | Are these drafts ready for the authorized production handoff? | Format drafts, governing brief, production notes, final checks, and resolved permissions. | The agreed handoff and subsequent human production process. |

Approvals are durable decisions on specific versions. Waiting for review is a normal state. The application should let someone leave, return, inspect the same evidence, and understand what changed before approving.

## 9. The application experience

The product should make the opportunity understandable before asking the user to inspect detailed evidence. Show the central point, reason for selection, audience, purpose, disposition, and next action first; allow source passages, boundaries, alternative directions, and operational detail to expand underneath.

| Area | Agenda | Present interpretation |
| --- | --- | --- |
| **Home** | Show the week's work, pending decisions, and content planning context. | Available in the studio; planning and calendar behavior includes mock/local state. |
| **Weekly Studio** | Demonstrate the journey from angles through briefs, packs, and scheduling review. | Saved editorial proposals and browser-local progression; the current default frontend mode. |
| **Weekly Angle Review** | Inspect SQL-derived candidates, evidence, comparisons, processing status, and Gate 1 decisions. | Backend-connected surface available in live data mode. |
| **Content Brief Review** | Inspect real brief versions, source evidence, questions, checks, revisions, exports, and Gate 2 decisions. | Backend-connected surface available in live data mode. |
| **Previous Concepts / content history** | Retain earlier directions and make prior work inspectable. | A studio library exists; broader publication-aware memory still needs operational completion. |
| **Content Packs** | Inspect format treatments and prepare the production handoff. | Current saved/mock pack experience; real pack workflow remains downstream work. |
| **Moments, research, approvals, and brand references** | Provide the supporting evidence, decision queue, and editable knowledge context. | Existing components and specifications cover these concepts; their complete integration into a shared live workflow is not established. |

The application has separate mock and live data modes. Selecting live mode exposes the SQL review surfaces; it does not convert every studio screen into a shared backend workflow.

## 10. Architecture, memory, and reliability

### 10.1 Major components

The frontend is a React/TypeScript application built with Vite and served by its Node server. Command Center supplies the existing account and sign-in integration. Content Atelier owns its editorial workspace and backend workflow.

The current Python backend contains the FastAPI storage API, validation contracts, model-provider integration, retrieval, comparison, approvals, and job processing. Run backend commands from the `backend/` directory.

PostgreSQL is the authority for admitted content and execution state in the SQL workflow. The approved baseline has thirteen tables covering weeks, runs, transcripts, chunks, moments, angles, angle-to-moment links, briefs, packs, assets, calendar entries, jobs, and events. Downstream tables existing in the schema does not mean their workflows are implemented.

### 10.2 Two different kinds of memory

**Evidence memory** preserves original transcripts and searchable chunks so a claim can be traced to what was actually said. **Angle memory** preserves generated ideas and their meaning so repetition and previous treatments can be compared.

The schema has two persistent vector columns: one for transcript chunks and one for angles. Retrieval and similarity calculations serve different jobs. A similar historical angle can inform freshness, but it cannot establish a new factual claim about a current source.

Exact requests, raw responses, reusable cache, costs, dossiers, and source-byte archives remain file artifacts linked to the SQL workflow. The separate file-backed calibration runner retains experimental data in `testing/.data/`; it should not independently write the same SQL business records.

### 10.3 Durable processing and cost visibility

The current SQL worker uses persisted jobs, locks, leases, heartbeats, events, and explicit retries. Older architecture proposals mentioning Redis/RQ do not describe the executor used by this SQL path.

Preserve source revisions and request identity so compatible saved results can be reused. A cache replay is reuse of an earlier generation event. It is not a new batch of ideas or a new provider charge. Record missing cost data as unknown, and keep failed responses and partial runs visible.

Model and provider choices are configurable implementation settings. The agenda should survive a model change; actual runtime prompts, schemas, configuration, and readiness records determine a particular run's contract.

### 10.4 Evidence integrity and access

Every selected claim needs retrievable support at the stated scope. Preserve attribution, units, timeframe, approximate language, and uncertainty. Distinguish speech, recommendations, implementation, reported results, and interpretation. Inquiries, consultations, bookings, revenue, and ad-attributed revenue are different measurements.

Internal processing permission, editorial approval, and public naming or quotation permission are separate decisions. Do not infer public clearance from a transcript's availability or an angle's approval. Verify material speaker or transcription ambiguity against an appropriate original record.

The browser uses the frontend server's protected proxy for backend requests. Provider credentials, database access, and the service secret remain server-side. Real operations should respect the configured actor capabilities and execution switches; deploying a screen does not authorize unattended model calls.

## 11. Current implementation and its limits

This is a documentation and code-based summary as of 14 October 2026. It draws on the latest local status records and inspected frontend code; creating this agenda did not rerun the pipeline, query the live database, deploy services, or perform new provider calls. Older numerical inventories in the repository describe their original checkpoints.

| Workstream | Current evidence and remaining limit |
| --- | --- |
| **Source admission and evidence storage** | Local Zoom admission, immutable source preservation, mapped passages, chunk storage, and SQL state are implemented. Continuous Fathom and Slack intake are not established. |
| **Weekly discovery and angle generation** | The two main model stages, validation, artifacts, and SQL processing are implemented. Live diagnostics include partial and failed extractions; they do not establish reliable whole-week discovery. |
| **Embeddings and historical comparison** | Recorded real Week 1/2 operations encoded angles and transcript chunks and exercised comparison. Threshold scenarios remain experimental; broader editorial and freshness calibration is incomplete. |
| **Strategic discovery revision** | The 13 October strategic v1 revision is implemented with purpose, audience, WIA contribution, research states, and internal insights. Its offline contract checks do not prove live editorial quality. |
| **Latest handbook profile** | The fuller handbook has a separate versioned prompt profile and diagnostic review. It has not replaced production defaults. A separately prepared full-handbook angle request is recorded as not dispatched; preparation is not execution. |
| **Briefing and Gate 2** | Hybrid retrieval, frozen dossiers, writing, bounded repair, versioned review, exports, and approval controls are implemented. Two recorded authorized pilots produced SQL drafts; both remain blocked at Gate 2 by contract, evidence/permission, overlap, or human-review issues. |
| **Studio and authentication** | The frontend contains sign-in integration and a broader saved-content demonstration. Mock mode is the current default; its approvals and schedules use browser-local state. |
| **Packs, production, and publishing** | Saved pack material and scheduling simulation exist. Automated SQL-backed pack production, external delivery, and confirmed publishing are not completed capabilities. |
| **Production operation** | The frontend has deployment instructions. Current backend deployment, scheduled execution, recovery, and operational readiness require verification against the actual package rather than older deployment prose. |

The latest handbook is important editorial guidance, but its proposed fields, dispositions, and scoring rules must not be presented as a fully migrated and calibrated implementation. Likewise, a successful mechanics test does not establish source comprehension, founder voice, or approval readiness.

## 12. Delivery agenda and completion criteria

The following sequence organizes the remaining work by dependency. It is a completion framework, not a promised calendar or a new authorization for live execution.

| Stage | Delivery agenda | Evidence needed to move forward |
| --- | --- | --- |
| **1. Establish dependable editorial judgment** | Reconcile the active discovery contract with the latest handbook; improve breadth, strategic usefulness, attribution, and handling of incomplete inputs. | Whitney can review central points on both calibration cases and unseen recordings; misses and major reframing are measured. |
| **2. Complete the live angle review cycle** | Resolve comparison policy, current-batch overlaps, partial-week behavior, and operational Gate 1 configuration. | Reproducible candidates and evidence, honest coverage states, explainable history comparisons, and a recorded authorized approval. |
| **3. Reach an accepted production brief** | Resolve pilot validator defects and contract issues, permissions, overlap decisions, and remaining editorial questions. | A real dossier and current brief pass the applicable checks and receive explicit Gate 2 approval. |
| **4. Build the production pack workflow** | Agree pack quantities and assignments; generate format drafts from approved brief revisions; add checks and the final handoff decision. | Traceable, distinct assets that Giselle can use with limited rewriting and an explicit Gate 3 decision. |
| **5. Connect recurring intake and operations** | Complete source connectors, confirmed weekly windows, late-arrival handling, deployment, recovery, monitoring, and operating cost controls. | A real recurring cycle runs with truthful status, recoverable failures, appropriate access, and measured review effort. |
| **6. Close the memory and feedback loop** | Record actual content use and scoped editorial corrections; evaluate freshness and learning across later weeks. | The system distinguishes generated from published work and improves on unseen sources without repeating recent central points. |

The project is complete at the agreed production scope when WIA can repeat the source-to-approved-handoff cycle with retrievable evidence, acceptable editorial quality, clear ownership, durable decisions, and measured operating effort. A populated demo, a successful model response, or passing unit tests alone cannot meet that definition.

## 13. Decisions still needed

Some items have partial or pilot-specific answers. Before treating them as settled operating policy, record the current decision and its authority:

- **Weekly cadence:** WIA's business timezone, source window, processing start, late-arrival policy, and review day. Earlier Saturday timing proposals are not proof of a confirmed installed schedule.
- **Source coverage:** Which accounts, meeting types, Slack channels, and supplementary documents belong in ongoing intake, and how revised or duplicate captures are handled.
- **Editorial acceptance:** What level of strategic rewriting is acceptable, how missed opportunities are measured, and which handbook refinements should become runtime defaults.
- **Similarity and freshness:** The authoritative comparison cutoff, close-pair policy, treatment of partial history, and meaningful reasons to revisit an older point.
- **Clearance and current facts:** Source-use rules, client naming, public quotations, result claims, retention requirements, and ownership of verified offer records.
- **Production scope:** Weekly pack size, asset-to-brief allocation, delegation at each gate, export needs, and any later scheduling or publishing integration.
- **Operating policy:** Approved provider routes, spending and retry limits, service ownership, deployment verification, and recovery expectations.

Keep engineering calibration separate from client decisions. WIA should judge whether two ideas feel repetitive and whether a direction is useful; engineering should translate those judgments into tested settings.

## 14. Repository guide and further reading

Read this agenda first for orientation, then follow the document appropriate to the work. These links are relative to the Content Atelier project root so the guide remains usable in another checkout.

| Location | Use it for |
| --- | --- |
| [README.md](README.md) | Existing project entry points and notices about separate prompt experiments. Some older implementation statements need the newer status records below. |
| [frontend/README.md](frontend/README.md) | Frontend development, authentication, verification commands, and mock/live data-mode behavior. |
| [frontend/src/](frontend/src/) | Current application screens, typed data, saved editorial examples, and studio behavior. |
| [backend/STORAGE.md](backend/STORAGE.md) | SQL setup, admission, workers, matching, recovery, API, and approval/brief operation. Read its checkpoint dates alongside later pilot updates. |
| [backend/backend_pipeline/](backend/backend_pipeline/) | Current backend implementation and validation contracts. |
| [Runtime prompt templates](backend/backend_pipeline/prompt_templates/) | The actual prompt inputs, editorial policy, strategic reference, and isolated handbook profile. |
| [Brief implementation status](implementation-status-content-briefs.md) | Implemented briefing behavior, verification limits, and the two live pilot outcomes and blockers. |
| [Strategic discovery revision](backend/docs/2026-10-13-Strategic-Discovery-Revision.md) | The implemented 13 October strategic v1 change and its practical limits. |
| [Content-only WIA handbook](backend/backend_pipeline/prompt_templates/handbook_v2/wia_content_system_handbook.md) | The fuller editorial specification: audience, pillars, offers, selection, evidence, feedback, and evaluation. Its profile remains separate from production defaults. |
| [Handbook understanding ledger](research/2026-10-13-wia-handbook-understanding-ledger.md) | Detailed source-linked reasoning, calibration cases, proposed contracts, and unresolved dependencies. |
| [Frontend product specification](frontend/Frontend-contentatelier.md) | The broader product behavior, human gates, pack plan, and target experience. Treat proposed features as requirements rather than proof of implementation. |
| [Approved schema contract](database-schema-compact.md) and [data/storage map](data-storage-schema.md) | Domain relationships, approval bindings, and separation of SQL records from artifacts. |
| [Historical comparison plan](implementation-plan-historical-comparison.md) and [brief implementation plan](implementation-plan-content-briefs.md) | The reasoning and intended contracts behind those implementations. |
| [Documentation/implementation review](backend/docs/Content-Atelier-Documentation-Implementation-Review-2026-10-12.md) | Conflicts and superseded assumptions in older architecture and audit material, with dated follow-up progress. |
| [DEPLOYMENT.md](DEPLOYMENT.md) | Frontend deployment and demonstration behavior. Its optional backend instructions require checking against the current backend package. |
| [BUILD_HANDOFF.md](BUILD_HANDOFF.md) | Historical continuation and transfer context from 9 October; later status records supersede its delivery boundary. |

For implementation status, prefer current code plus the newest relevant verification or pilot record over an older architecture proposal. For editorial intent, use the latest explicit founder direction and verified strategy. Preserve the original evidence and the history of decisions whenever either changes.
