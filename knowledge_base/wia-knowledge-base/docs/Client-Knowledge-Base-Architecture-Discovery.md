# Client Knowledge Base — architecture discovery and decision register

**Date:** 20 October 2026 · **Status:** Q1–Q23 recorded; first full Solution Architecture draft available

This record supports the user's request to build the Client Knowledge Base Solution Architecture through reasoning and clarification. It is not the final architecture, an implementation plan or a claim that proposed infrastructure exists.

## 1. Basis and product understanding

The KB's [Feasibility Study](Client-Knowledge-Base-Feasibility-Study.md), [agreed decisions through KB-CH-69](../../../knowledgebase_changes.md), [chatbot scope](../../../chatbot_KB.md) and [FastAPI SOP](../../../backend_build.md) establish this product's requirements.

**Agenda:** maintain an owned, evidence-backed understanding of each active WIA business and its service engagements, together with accountable follow-through on explicit commitments. WIA should be able to understand an account, trace a statement, distinguish what is known from what is inferred and find what each side owes. Contextual chat is an interface to that record, with source freshness and specialist routing still subject to testing.

The target is an internal WIA team system serving approximately 15–20 active clients, growing towards 30–40, with about ten team users who may all use it simultaneously. Counts can change; these are planning inputs, not measured capacity or a confirmed roster/corpus size. Architecture Q1–Q23 establish the foundations below, including admin-configurable retention, full testing access, evaluated/version-controlled AI changes and last-known data with sync date/time during outages. Provisioning implementation, actual role/default grants, retention durations and measured capacity/recovery remain open. The support-access question is closed at the user's direction, not a prerequisite to revisit. No external client portal or additional source is introduced here.

The mechanism needs explicit layers:

1. **Authorised intake and evidence:** obtain the approved scope, retain required provenance/coverage and recover missed work.
2. **Identity and reconciliation:** map businesses, engagements, people and source accounts; preserve shared evidence without merging business identities.
3. **Maintained records and workflow:** apply field authority, distinguish source observations from current KB state, preserve review decisions and expose unknowns.
4. **Interpretation and specialist execution:** test hybrid and Viktor-led routes against common output/evidence contracts; models cannot establish otherwise missing source access.
5. **Permissioned delivery:** Portfolio, Action Items, later enabled views and chatbot use the same authorised record/query services.
6. **Recovery and efficiency:** durable work/checkpoints, tested freshness, cost controls and dependency-aware reuse support the above without weakening QA.

## 2. Settled requirements carried forward

- Activation sequence, confirmed on 21 October in KB-CH-69: Stage 1 Action Register + Client Portfolio; Stage 2 Call Preparation; Stage 3 Health & Sentiment + Invoices & Contracts + Overview. Chatbot and unlisted capabilities remain unsequenced. Earlier open-order statements are historical and superseded for these named tabs.
- Business-level clients have separate service engagements and linked contacts/accounts. A source/meeting can relate to several businesses.
- All obtainable history from every approved source for all currently active clients is processed before launch, even for later UI features. WIA signs off source-by-source gaps; no particular gap has been accepted.
- Approved sources remain Gmail, Slack, ClickUp, historical Zoom, Fathom, Drive, LeadLock and Calendar. Fresh paid-media intake and other proposed sources remain outside current new-source scope.
- Readable text, Docs/Sheets, existing transcripts and extractable PDF/DOCX text are processed. Scans/images/audio/video remain linked; no OCR/new transcription is approved.
- Existing active tasks and clear current commitments enter the active register; ambiguous/stale/proposed work goes to Needs review. Owners/dates remain unknown when not established.
- Acknowledgement follows identified-owner evidence/manual action/configured reactions. Done and named-WIA-reviewer Verified have distinct evidence. Self-verification is an admin-configurable permission; an owner needs normal verification rights plus that permission and follow-up evidence. Custom editing/review permissions use role baselines plus per-user Inherit/Allow/Deny overrides within permitted client/section scope; user Deny wins over role grants. Actual role/default grants remain configuration inputs.
- Client/module access applies across records, evidence, search, generated content, chat, caches and exports. The custom standard team profile is configurable; its actual grants are not supplied.
- Fifteen-minute updates, visible last-sync state and supported on-demand refresh remain the target. Cache freshness cannot add another lag window.
- Railway/OpenRouter accounts belong to WIA. Retain the existing React frontend and follow the FastAPI backend SOP, including its Redis/RQ pattern where asynchronous work is needed.
- Reuse the existing Command Center authentication system; KB admins also provision central login accounts through an API and configure KB access. The inspected implementation uses email/password and signed sessions with a cross-application sign-in handoff; a new Google sign-in system is not selected. The supported provisioning API must be established or built; it is not verified by current local code inspection.
- Revoke KB membership/access immediately without disabling the shared central account. Central disabling is separately authorised. Current KB membership must be enforced even when a central login/session remains valid.
- Use a dedicated KB Railway project and data services, with independent deployments, database and job/cache resources under WIA ownership. Existing shared authentication is an intentional integration, not permission to share the products' business databases.
- Assess maximum one-hour KB data loss and restoration within four hours after serious database failure, subject to tested recovery/costs. The targets do not establish deployed backup coverage, staffing or a guarantee.
- Use isolated staging with a WIA-approved limited real-client dataset and separate test credentials/configuration, without source-system writes. The actual dataset/access and paid evaluation limits are not approved by selecting this policy.
- Chatbot threads are private to their user. Admins may view operational metadata, not conversation content; admin content inspection is excluded for now. Current client/module restrictions still apply. Saved history/temporary-input retention remains to configure.
- Retention policies are admin-configurable by data category; numerical durations remain to configure before launch. Keep temporary full originals distinct from retained facts/excerpts and private chats distinct from admin metadata.
- E2M and WIA have full testing-data access. The user closes the proposed connector/support-access ownership question as unnecessary; no extra client-by-client testing approval is required. Isolated staging and production access policies remain intact.
- Plan for approximately ten WIA users, all potentially simultaneous, with membership able to increase/decrease. Test mixed UI/chat use alongside ingestion/backfill rather than claiming measured capacity from headcount.
- Persist extracted facts, supporting excerpts and necessary source/provenance/version metadata; fetch full originals when needed. Do not retain a complete replayable text archive by default. Full historical processing and the no-OCR/new-transcription policy remain unchanged.
- Preserve reviewed corrections and review conflicting later source observations. Track changes read/unread per user: opening details or Mark as read clears the viewed change for that user; later changes become unread again. Conflict status remains separate until resolved; seen status is not review approval.
- Retain facts/excerpts when their upstream original is confirmed deleted, with a visible deleted-source warning. Do not automatically withdraw them solely because of deletion; permissions, evidence age, known conflicts and current-state limitations still apply.
- Hybrid and Viktor-led remain two implementation candidates; no winner is selected. Chatbot KB-only versus controlled live reads also remains a test decision.
- Smart FAQ/direct answers and safe cached reuse must preserve correctness, citations, source coverage and access. Actual savings and cache settings remain unproven.
- ClickUp creation and external notifications are Coming soon; later external actions need WIA review.
- Development/launch targets remain 6/26 November 2026. Monthly cost cap, staffing and measured archive throughput are unknown; the dates are not a validated estimate.

## 3. Architecture document structure

Organise the architecture around the following engineering areas. Integrate chatbot, cache and access contracts into the sections that own their responsibilities.

| Architecture section | KB architecture content to develop |
|---|---|
| **0 · Short version** | Decision summary with approved, recommended, test-dependent and unresolved status; scope and conditions |
| **1 · Requirements and context** | Traceable KB requirements, actors, vocabulary, feasibility alignment and explicitly approved changes |
| **2 · Architecture at a glance** | Context/pipeline/deployment diagrams, sign-in versus connector authorisation, service boundaries and proposed stack |
| **3 · Knowledge and retrieval** | Business/engagement identity, versioned retained facts/excerpts and provenance, on-demand original retrieval, field authority, permission-aware exact/semantic retrieval and chat query tools |
| **4 · Pipeline stage by stage** | Eight-source backfill/change intake, normalisation, identity resolution, action extraction/reconciliation, outcomes and Portfolio delivery |
| **5 · External providers** | Direct/Viktor connector and skill contracts, source boundaries, permissions, central LeadLock access and provider failure behaviour |
| **6 · Human review** | Needs review, conflict resolution, acknowledgement, Done/Verified, correction authority and admin access controls |
| **7 · Memory and freshness** | Historical versions, coverage, reviewed decisions, cache admission/invalidation, time-sensitive results and source/permission changes |
| **8 · AI and model strategy** | Stage/skill contracts, bounded business context, hybrid/Viktor-led evaluation, chat routing, deterministic FAQs and model-change gates |
| **9 · Orchestration and operations** | Durable work/outbox/checkpoints, Redis/RQ queues, renewals/reconciliation, load priorities, budgets, monitoring, deployment and restore |
| **10 · Data model** | Businesses/engagements, identity links, source versions, evidence/facts, actions/lifecycle events, reviews, grants, runs, coverage and chat records |
| **11 · Quality and evaluation** | Required output contracts, labelled retrieval/action cases, source/field completeness, permission tests and cache-on/bypassed QA |
| **12 · Security and privacy** | Authentication, authorisation, connector ownership/secrets, mixed evidence, retention/deletion, provider context and conversation handling |
| **13 · Release scope** | First-release commitments, data obligations independent of UI gates, later ordering and excluded complexity |
| **14 · Build plan** | Dependency-aware implementation/testing sequence and launch conditions; dates validated against capacity/throughput |
| **15 · Costs** | KB-specific resource/token/credit workload, cache economics, historical versus ongoing cost and measurement gaps |
| **16 · Risks/open decisions** | Unresolved policies, source limitations, tests and failure conditions with accountable owners |
| **Appendix A · Engineering starting point** | SOP-compliant directory layout, interfaces, schemas/configuration examples and migration ownership |
| **Appendix B · Verification** | Current primary documentation, actual source-test evidence and explicit proposed/unverified statements |

KB requirements define eight-source intake with push/change reconciliation, all obtainable in-scope history, the existing React frontend, retained facts/excerpts, on-demand originals and human review. OCR, new media transcription, live website research and content-generation workflows are outside the approved intake scope. Embedding dimensions, model settings and recovery guarantees require their own validation.

## 4. Proposed common core, not yet a selected topology

The engineering starting recommendation is a modular FastAPI codebase serving the existing frontend's API, with separate asynchronous worker execution and a relational source of truth. Exact/full-text/optional semantic search operates on the retained facts/excerpts and metadata; it must not imply that every original word is locally indexed. Q21 selects PostgreSQL with SQLAlchemy ORM, psycopg and Alembic; Redis/RQ is the SOP-aligned work/cache direction. Dedicated KB infrastructure is selected, while database access style, final providers/extensions, service sizing and transient artifact handling need explicit design/review. A permanent raw-transcript/document bucket is not selected by the new evidence-retention answer.

Both AI candidates should share the domain contracts and acceptance rules. The choice of who obtains/interprets source material must not remove the owned evidence record, deterministic validation, current-state logic, permission enforcement or WIA review. A provider adapter must expose what source/field coverage it actually obtained, not only a successful report.

Similarly, chatbot freshness mode is an execution policy to test. Its implementation should use the same permitted query/evidence layer as the frontend. FAQs and cache hits still validate identity, scope, evidence/collection revisions and the relevant clock; new source state cannot remain hidden behind an old answer.

The recommendations are developed in the Solution Architecture draft below. User decisions, recommended implementation choices and test-dependent selections remain distinguished; documentation work does not establish a deployed system.

## 5. Architecture decision register

| ID | Question | User decision / current position | Status / impact |
|---|---|---|---|
| **ARCH-Q01** | How do users sign into the application? | Reuse the Command Center auth system, described by the user as application email/password accounts, with admin addition of users | Direction agreed; provisioning/identity-to-KB contract is ARCH-Q04. New Google sign-in recommendation not selected |
| **ARCH-Q02** | Dedicated KB Railway project/data services or selected shared infrastructure? | Dedicated KB project and data services | Agreed; physical sizing and environment/recovery design still to specify |
| **ARCH-Q03** | What source material should persist after full historical processing? | Retain extracted facts/excerpts and fetch full originals when needed | Agreed; replayable full-text snapshots were not selected. Original availability/version dependence must be explicit |
| **ARCH-Q04** | Does KB Add user grant local membership to a central account, provision a central login through an API, or create separate KB credentials? | KB admin also provisions central login accounts through an API | Agreed; establish/build the supported central contract, retaining KB-local grants and explicit provisioning states |
| **ARCH-Q05** | How do reviewed WIA corrections interact with later source updates? | Preserve reviewed correction, review later conflicts and give changes distinct read/unread-style highlighting | Agreed; exact indicator semantics are ARCH-Q07; existing field-authority rules remain fixed |
| **ARCH-Q06** | What happens to retained facts/excerpts when their upstream original is confirmed deleted? | Retain facts/excerpts with a deleted-source warning | Agreed; automatic withdrawal/quarantine recommendation not selected; temporary access failure remains distinct |
| **ARCH-Q07** | Whose read state is tracked and what clears a change indicator? | Per-user read state plus separate conflict status; opening details or Mark as read clears that user's viewed revision and later changes become unread | Agreed; reading does not resolve conflicts or acknowledge an action |
| **ARCH-Q08** | Who can correct facts/action fields and resolve business conflicts? | Define a custom set of editing/review permissions | Custom direction agreed; the recommended fixed role grant set was not selected. Mechanism is ARCH-Q10; exact grants remain configuration |
| **ARCH-Q09** | May an owner perform the follow-up check that marks their own work Verified? | Self-verification is an admin-configurable permission | Agreed; requires verification authority, allowed self-verification and named WIA actor/follow-up evidence |
| **ARCH-Q10** | How should admins configure custom operation permissions? | Custom roles plus per-user overrides | Agreed; override precedence is ARCH-Q13; role/default grants remain configuration within permitted client/section scope |
| **ARCH-Q11** | Does removal of KB access also disable the central account? | KB-only revocation; central disabling remains separate | Agreed; central login success cannot re-enable revoked KB membership |
| **ARCH-Q12** | What data-loss/restoration targets should recovery design assess? | Assess one-hour maximum KB data loss and four-hour restoration | Agreed assessment targets; test/cost validation required, no current guarantee or backup topology selected |
| **ARCH-Q13** | How do role grants and individual overrides combine? | Role baseline with per-user Inherit/Allow/Deny; user Deny wins over role grants, Allow remains within permitted scope | Agreed; revoked membership cannot be overridden; actual role grants remain configuration |
| **ARCH-Q14** | What client data may staging/comparative evaluation use? | Approved limited real-client dataset in isolated staging, with separate test configuration/credentials and no source writes | Agreed policy; Q17 confirms both teams' full testing access. Configure representative fixtures and evaluation limits |
| **ARCH-Q15** | Who may see saved chatbot conversations? | Private user threads; admin operational metadata only, with admin content inspection excluded for now | Agreed; sharing/content inspection are later proposals and current client/module restrictions still apply |
| **ARCH-Q16** | How should retention periods be managed across data categories? | Admin-configurable category policies | Agreed; actual durations remain configuration inputs before launch |
| **ARCH-Q17** | Who manages source connections and what support access does E2M receive? | User considers the question unnecessary and confirms both E2M and WIA have full data access for testing | Closed; no extra testing-access gate or inferred production ownership split |
| **ARCH-Q18** | How many initial/future users and simultaneous users/chat questions should the system serve? | Around ten WIA team members, all potentially simultaneous; number can increase/decrease | Planning baseline agreed; exact future count/rates/latency thresholds are not supplied or measured |
| **ARCH-Q19** | Can admins directly change/activate prompts, Viktor skills and query routing? | Version-controlled AI behaviour with evaluation before release | Agreed; business settings remain admin-configurable; provider/mode selection still needs testing |
| **ARCH-Q20** | What should UI/chat show during temporary source failure or freshness lag? | Show supported last-known data with an explicit Last synced at time/date message | Agreed; disclose stale/unavailable status and avoid current verification claims without fresh evidence |

| **ARCH-Q21** | Which database access/migration baseline should the KB use? | SQLAlchemy ORM with psycopg and Alembic | Agreed; compatible pins/session/migration mechanics now elaborated in the technical draft |
| **ARCH-Q22** | When does an editor correction become the maintained value? | Authorised resolvers apply directly; other editors submit proposals | Agreed; proposal and application are distinct audited transitions |
| **ARCH-Q23** | What happens when a mapped ClickUp task reopens after Verified? | Automatically reopen and supersede prior verification, preserving history | Agreed exception to reviewed-state preservation; duplicate/stale source data must not cause false reopening |

ARCH-Q03 does not reopen historical scope or approve a fixed retention period. It distinguishes processing all available approved material from retaining original readable evidence versus only derived facts/excerpts.

### 5.1 Existing authentication implementation inspected

The local [Command Center auth service client](../../../frontend/src/services/api/auth.ts) submits email/password to `/api/auth/login` and uses cookie-backed session/logout endpoints. [Auth primitives](../../../frontend/server/auth-core.mjs) implement a configuration-driven account registry, password verification and signed session tokens. KB integration must establish the supported cross-application code/challenge handoff and user/session contract. This is local code inspection, not a new live login test or a complete security audit.

The observed user contract carries email, name and coarse `team`/`client` roles. Those roles do not establish KB admin authority or per-client/module grants. The architecture needs a trusted identity/session integration and a KB membership/permission mapping; browser-supplied actor names alone cannot authorise data access. Do not assume cross-domain cookies can simply be read by the dedicated KB application.

The inspected account registry is configuration-managed; an admin provisioning API was not established by this inspection. ARCH-Q04 now requires KB-admin API provisioning of central login accounts. Establish or implement that contract rather than treating a UI form as proof of central account creation. Authentication reuse does not mean copying password storage or exposing all Command Center users to the KB. The shared mailbox/Drive/Calendar OAuth credentials remain separate source-connector authorisation.

**Proposed provisioning flow:** an authenticated KB admin submits Add user; the backend checks admin authority, asks the central service to create or link the identity, then persists KB membership and reviewed client/module grants. The central service remains the credential authority. Use authenticated server-to-server calls, audited request/outcome identifiers and retry-safe operations. Existing-account linkage must not reset passwords or grant access to other products. Central provisioning and KB membership are separate failure boundaries: expose pending/failed setup and allow safe repair rather than declaring the user active after a partial success. ARCH-Q11 selects KB-only revocation, with central disabling separate; Section 5.6 develops the integration boundary. Exact invitation/password establishment, identity identifiers and other application entitlement contracts still need design; API implementation is a dependency of the selected approach.

Railway/RQ capability references remain [environments](https://docs.railway.com/environments), [PostgreSQL](https://docs.railway.com/databases/postgresql) and [RQ](https://python-rq.org/docs/). No dedicated KB resources, identity changes or credentials have been provisioned by discovery.

### 5.2 Consequences of facts/excerpts storage

- Process all obtainable approved history before launch, but persist selected extracted facts, supporting excerpts, event/source identity, locators, relevant timestamps and source/content/version markers where available. Retain extraction/run/coverage metadata needed to explain what was processed and what was not retained.
- Do not recreate a complete source archive by storing every transcript/document chunk as an "excerpt", a full normalised search mirror, raw JSON body or debug log. A complete readable replay copy was explicitly not selected. Index the retained information accordingly and disclose local-search coverage limitations.
- Fetch an original through an authorised connector using a verified source/account/record identifier when needed for missing context, detailed quotations, re-extraction or source checking. "Original" means the approved source record; it does not authorise following arbitrary external URLs or adding sources.
- Full bodies/binary text extraction can be transient processing inputs. Any temporary files or full-source cache need a bounded cleanup/retention design; do not silently turn them into permanent storage. Provider context/response caches also need to respect the selected handling policy.
- Preserve the distinction between an excerpt observed earlier and an original fetched now. If the provider returns an edited/current version rather than the historic one, identify that difference; hashes/locators cannot recreate missing text.
- Complete reprocessing and exhaustive new questions about unretained text depend on provider availability and source history/version support. With an unavailable original, answer from supported retained material, disclose the limitation and record the gap; do not reconstruct missing content with an LLM.
- This storage selection does not itself choose chatbot KB-only versus controlled live reads. Mode A may answer only from retained material until the permitted ingestion/refresh path supplies additional context; Mode B can assess controlled original reads at question time. Both remain subject to the agreed testing.
- Confirmed upstream deletion retains the facts/excerpts with a warning, as selected in ARCH-Q06; Section 5.4 develops its consequences. Temporary access loss, precise retention periods, old-version handling and performance/cost of on-demand fetching remain dependencies. No specific inaccessible source has been accepted as a launch gap.

### 5.3 Reviewed values, source observations and visible changes

ARCH-Q05 requires three distinct concepts: the reviewed KB value, observations arriving from sources, and the user's awareness of a change. A reviewed deadline correction must survive a conflicting ClickUp refresh; the incoming source value remains visible as a conflict rather than silently becoming the current deadline. Existing meeting-commitment precedence and financial field authority continue to apply. Storing a human correction does not establish that signed terms or payment records changed upstream.

The proposed record design links each correction/conflict to the business/engagement, entity/field, previous and reviewed values, later source observation, actor/time, supporting retained evidence and review outcome. Capture enough field-level context to explain the difference without copying full originals. Reprocessing or repeated identical deliveries must not recreate the same unresolved conflict or discard the human decision; later materially changed evidence must still be surfaced.

**Read state versus business state:** the requested change styling distinguishes a reviewed correction from a pending conflict. Reading details, acknowledging ownership, accepting a correction, resolving a conflict and marking an action Verified are separate operations. ARCH-Q07 selects per-user, per-change read state: opening details or Mark as read clears the viewed revision for that user; later changes become unread again, while an unresolved conflict retains its own status. One user reading cannot clear another user's indicator. It does not add external notifications to the initial release.

The proposed implementation records the user/change/revision observed, rather than one global read flag or only a wall-clock last-visit time. Marking revision A read must not clear revision B that arrived while details were open. Enforce scope before returning change details, old/new values or unread counts, including shared-business evidence. Keep factual answer caches separate from the personalised read-state overlay; a read marker alone changes no source fact and needs no new LLM interpretation.

Reviewed changes and conflicts also revise affected ledger/evidence dependencies. APIs, search, chatbot context and answer caches must use the reviewed value and expose relevant conflicts, rather than serve an obsolete answer from before the correction. ARCH-Q08 selects custom editing/review permissions and ARCH-Q09 makes self-verification admin-configurable; Section 5.5 records their effect.

### 5.4 Confirmed source deletion: retain evidence with warnings

ARCH-Q06 selects retention with a deleted-source warning instead of the proposed automatic withdrawal/quarantine. Keep the surviving facts/excerpts searchable and usable in permitted Portfolio/history/chat contexts, with source identity, when the material was observed, the deletion status and its detection time. A KB citation should open the retained evidence and explain the unavailable original; an upstream link must not be presented as a freshly verified working reference.

Separate content support from source availability. Deletion does not automatically negate an earlier statement, close an action or amend a payment/contract; equally, an old excerpt cannot prove a mutable fact is still current. Answer historical questions from the retained evidence with the warning, disclose limitations for current-state questions and preserve any contrary evidence or unresolved conflict. Requests for text not retained cannot be fulfilled without an obtainable original. Derived analysis needs the changed coverage/status surfaced, rather than deletion alone inventing a new business conclusion.

Revise source/coverage and dependent answer/cache records when deletion is confirmed. A previously cached unqualified answer must be regenerated or rendered with the warning and appropriate limitations; this invalidates stale presentation, not the retained evidence itself. Apply the same policy to citations, exports and specialist context. It does not bypass current user permissions or later explicit KB deletion requirements.

A denied request, missing search result, inaccessible file or ambiguous removal event is not by itself proof of deletion. Preserve separate availability states until the connector has adequate evidence. Provider-specific confirmation tests, exact retention periods, temporary access-loss handling and client deactivation/offboarding remain to specify. Retaining excerpts does not introduce a permanent original archive or a new source.

### 5.5 Custom operation rights and configurable self-verification

ARCH-Q08 selects a custom permission set, not the proposed automatic grant to KB admins, operations reviewers and account owners. Separate responsibilities from effective permissions: a named account owner coordinates business work, but that title or client visibility alone does not authorise editing. Keep the custom standard team profile's actual grants as explicit WIA configuration. ARCH-Q10/Q13 select custom roles as a baseline and per-user Inherit/Allow/Deny operation overrides: Deny wins over role grants; Allow adds rights only within permitted scope; Inherit follows the configured baseline. No effective grant means no operation permission.

The proposed operation catalogue distinguishes profile-fact correction, action-field editing, conflict/review resolution, follow-up verification and self-verification, with user provisioning/access management and connector administration separated. Model the rights explicitly in backend policy and check the applicable client/module scope. Do not let hidden UI buttons serve as the access boundary or let a user's grant-editing capability arise from ordinary content editing. Q22 permits authorised resolvers to apply audited corrections directly; other editors create proposals without replacing the maintained value.

ARCH-Q09 permits admins to configure self-verification. At a verification attempt, check current identity, WIA reviewer eligibility, client/module access, normal verification rights and, if the reviewer is the owner, the applicable self-verification permission. If it is not granted, require another authorised WIA reviewer. Even when enabled, require the named actor's follow-up check and supporting evidence; neither a Done task nor an owner acknowledgement automatically establishes Verified. Preserve who checked, when, what evidence was used and whether the check was self-verification. The configuration must specify effective rights; an absent rule is not an affirmative permission.

Permission changes need enforcement on subsequent requests and pending work before delivery/commit. Read state, ownership and source completion must not grant extra operation rights. The first-release restriction on provider writes/notifications and the chatbot's proposed read-only boundary remain unchanged.

Roles and individual overrides need attributable, versioned configuration changes and an effective-permissions view for administrators. The proposed policy order is active central identity, active KB membership, permitted client/section scope, available feature, then effective operation rights; all must pass. Apply the selected Inherit/Allow/Deny precedence within those bounds. No role/override should independently widen client/module visibility, revive revoked membership, enable deferred admin chat-content inspection or infer user-administration rights from content editing. Role names, actual grants and any multi-role behaviour remain explicit configuration/design inputs rather than copied central team/client roles. Test role grants with user Deny, ungranted operations with user Allow, inherited baseline rights and an Allow against a hidden section or revoked member.

### 5.6 KB-only revocation and the central identity boundary

ARCH-Q11 selects immediate KB membership/access revocation while leaving the shared central login active. A Command Center session proves identity; the KB must still check active membership and current grants. Treat central account disabling as a separately authorised operation whose trusted identity/session contract must also be honoured by the KB. A KB removal must not silently disable the shared central account or change other applications' permissions.

The proposed enforcement uses durable membership/permission revisions, rechecks at backend data/mutation boundaries and before delayed result delivery, and invalidates affected session/permission decisions and user-specific caches. Stop further protected output from revoked chat streams/jobs. Citation/history loads and export/download delivery need the same boundary. A completed download cannot be recalled; revocation prevents subsequent access rather than erasing already received material. User removal does not automatically delete client facts or the actor's audit history; exact retention remains separate.

Tests must cover a centrally signed-in but KB-revoked user, role/override caches, a pending chat/verification/export and attempted access through old citation/session links. Existing coarse central roles cannot substitute for membership checks. The exact central disabled-account/session invalidation mechanism remains to establish in the shared auth integration; current code inspection is not a successful end-to-end revocation test.

### 5.7 Recovery targets and evidence that they can be met

ARCH-Q12 selects assessment of a **one-hour recovery point target** (maximum lost KB changes) and a **four-hour restoration target** after serious database failure. Measure the freshest usable restored state and elapsed incident/restore/validation/cutover stages. Clock definition, response coverage, named recovery owner and scenarios outside ordinary database failure remain to specify. Neither the target nor enabling a backup feature establishes that it is met.

Protect reviewed facts/corrections, review and verification events, retained excerpts/provenance, client/source mappings, memberships/roles/overrides, acknowledgement configuration, job/checkpoint state and any approved chat history. Original re-fetching cannot recreate human decisions or excerpts whose upstream records were deleted. Treat caches as rebuildable; retain durable work/checkpoints outside the disposable queue where needed.

**Provider capability research, 20 October:** Railway documents daily/weekly/monthly volume snapshots; daily-only recovery is too coarse for this target. Its PostgreSQL PITR uses continuous WAL archiving and restores into a new service, followed by cutover; it is a candidate to assess if PostgreSQL is selected. Archive health, initial backup readiness and restore duration still need verification. [Volume backups](https://docs.railway.com/volumes/backups), [PITR](https://docs.railway.com/volumes/point-in-time-recovery).

**Proposed validation:** restore an isolated database, verify known committed records against the target recovery point, bring up the application, reconcile checkpoints/duplicate intake and test reviewed values, verification evidence and deleted-source excerpts. Rebuild caches and reconcile current revocations/access restrictions before reopening access; an old backup must not silently reactivate a removed user. Capture restore/cutover timings, missing changes, archive lag and storage/egress/temporary-service costs. A clock-based backup schedule alone is insufficient evidence of actual recoverable freshness.

Backup retention, protected-copy location, access to recovery secrets, prevention of shared-project deletion loss and routine drill/monitoring responsibilities remain design inputs. The target does not claim automatic failover, zero downtime or recovery from total provider/account loss. A backup copy of the retained KB state is consistent with facts/excerpts retention; it is not permission to archive full source originals. No live backup, restore, service creation or paid test was performed by this research.

### 5.8 Isolated staging and bounded real-client evaluation

ARCH-Q14 selects a limited real-client dataset in isolated staging, with separate test credentials/configuration and no source-system writes. ARCH-Q17 confirms full testing-data access for E2M and WIA and closes the proposed support-ownership question as unnecessary. Select representative fixtures/windows and record their coverage without requiring another client-by-client access approval. Expected answers, test identities, model-provider contexts and evaluation budgets still need preparation. A small fixture set can test behaviour without establishing complete production source coverage.

The proposed environment separation covers database, queues/cache, source cursors/mappings, storage and provider/subscription configuration. Replay saved notifications into staging without acknowledging or advancing production cursors, sharing cache keys or triggering live task creation/messages. Do not reuse production watch/channel identities in a way that changes their delivery. Keep test users and their client/module/operation scopes explicit; include denied-access and private-chat cases. Avoid unbounded production database clones; actual dataset selection and transfer remain controlled work. Production's full available-history launch condition is unchanged.

### 5.9 Private chatbot threads and admin metadata boundary

ARCH-Q15 selects private threads and operational metadata-only admin access. Admin inspection of conversation content is expressly a later possibility, excluded now; it is not a latent permission that an ordinary override can turn on. Current thread ownership and current client/module permissions both constrain history access and model context. Do not surface another user's private questions through cross-user search, team exports, memory features or cache inspection.

The proposed metadata contract covers usage, cost, latency, status and sanitised error categories. Logs, traces and validation/provider exceptions must not echo private prompts, answers, retrieved excerpts or tool bodies into that admin surface. Keep necessary identifiers protected by their own scope; an error message is not automatically safe metadata. This is the production application policy. ARCH-Q17 separately confirms full testing-data access for E2M/WIA; a new support-ownership/access gate is not required.

Cache reuse must distinguish a reusable cited KB answer from user-specific conversation content. Do not publish private chat context as a shared FAQ, evidence fact or another user's answer context. ARCH-Q16 selects admin-configurable category retention; numerical durations remain to configure for saved chats, transient originals, operational/audit records and former-client material. Retained history must also be handled appropriately in staging and recovery copies. These choices do not select chatbot source-freshness mode or provider winner.

### 5.10 Retention configuration and ten-user capacity baseline

**Retention:** keep category-specific duration/configuration, policy version/effective date and change actor/time. Separate temporary original inputs, saved private chats, retained facts/excerpts, operational logs and audit history rather than treating one TTL as suitable for every record. Former-client retention does not itself approve former-client archive intake. Actual durations remain WIA configuration; the admin UI must not imply that chat retention management permits reading conversation content.

The proposed cleanup design previews affected categories/counts, applies audited scheduled expiry and removes/revises dependent search/cache/artifact references. Define whether a policy change affects existing records and show expired evidence as unavailable instead of leaving unsupported answers. Account for backup expiry and provider copies separately; deleting an app row does not demonstrate immediate deletion from them. Recovery must reapply relevant expiry/deletion decisions before reopening access. Do not use an unset temporary-file policy to silently retain full originals forever. These are implementation responsibilities, not selected numerical retention periods.

**Capacity:** use approximately ten concurrent users as the initial test baseline, with headcount adjustable. Include mixed Portfolio/action navigation and updates, simultaneous chat requests, cache cold/warm bursts and ongoing source intake/backfill. Measure UI/API/chat latency, queue age, provider admission, memory/CPU, fifteen-minute publication freshness and cost. Exact request rates, per-class response-time thresholds and future user totals remain measurement/configuration inputs; do not replace them with client count.

Ten active users need not mean every request starts another specialist run. Apply the scoped direct-answer/cache/coalescing design and bounded workers while keeping progress and queued work visible. Test private context isolation across simultaneous users, scope-equivalent reuse, role/revocation changes and whether backfill competes with current updates. Scale resources from observed workload; no load test or hard ten-user licence/membership limit is established by this planning input.

### 5.11 Technical depth review and Q21–Q23

The user requested more implementation-specific detail in the first KB architecture draft. The [technical gap analysis](Client-Knowledge-Base-Architecture-Technical-Gap-Analysis.md) identifies 22 specification areas. The Solution Architecture now expands runtime/session ownership, source contracts/procedures, extraction schemas, reducers, API/frontend mapping, mutation/cache/job protocols, physical schema/ORM examples, central auth requirements, QA, runbooks and proposed configuration.

Q21 selects SQLAlchemy/psycopg/Alembic. Q22 separates editor proposals from resolver application. Q23 automatically reopens a genuinely reopened mapped ClickUp action and marks its prior verification superseded; it does not wait for review or overwrite unrelated reviewed fields. Preserve historical verification evidence, deduplicate/reconcile source ordering and invalidate current-state answers. These are recorded as KB-CH-65–67. Operational numbers in the expanded architecture are engineering proposals, not approved retention periods or measured QA results.

## 6. Remaining configuration and verification

These are implementation/configuration and test inputs carried into the first full architecture draft. They do not require another preference-question round before that draft can be reviewed, and they must not be silently presented as agreed numerical defaults or completed tests.

| Area | Material ambiguity to resolve | Why architecture needs it |
|---|---|---|
| **Operation permissions** | Custom roles, scoped Inherit/Allow/Deny overrides and configurable self-verification are selected; actual role/default grants remain inputs | Separate visibility from mutation authority and record the right actor/evidence |
| **Change awareness implementation** | Per-user read state and independent conflict status are selected; revision/race/scope behaviour must be tested | Avoid conflating seen content with accepted changes or resolved conflicts |
| **Identity lifecycle** | Central API provisioning and KB-only revocation are selected; central disable remains separate. Invitation/password setup and existing-account linkage still need design | Integrate admin user management without unintended cross-product changes |
| **Source access loss and client deactivation** | Confirmed deletion retains excerpts with a warning; temporary failures, deactivation and exact retention remain open | Keep warning-aware retrieval/cache behaviour distinct from permission revocation and explicit KB deletion |
| **Recovery and availability** | One-hour data loss/four-hour restoration selected for assessment; backup topology, restore responsibility, clock/support coverage and verification remain open | Define measurable recovery design and validate it through restore tests |
| **Staging/test data and connector scope** | Isolated limited real-client fixtures remain selected; E2M/WIA full testing access is confirmed. Prepare representative records/windows and test identities | Isolate credentials/data and prevent tests from changing live subscriptions or UI records |
| **Review operations** | Queue accountability, escalation behaviour and whether internal technical alerts belong in the initial release | Do not assume business notifications and operational alerts have identical scope |
| **Evaluation/operating limits** | Around ten users, all potentially concurrent, is the baseline; acceptance owners/thresholds, exact rates and model/skill evaluation budgets remain open | Set workload/cost/freshness tests and safe resource controls |
| **Retention and chat history** | Admin-configurable category policies and private threads/admin metadata-only access are selected. Durations, existing-record expiry, backup handling and own-thread export remain to design/configure | Determine persistence, permissions, cache eligibility and provider-context lifecycle |
| **Configuration governance implementation** | Version-controlled AI behaviour with evaluation before release is selected; define release checks and version dependencies | Keep business configuration flexible while preventing untested behaviour changes |
| **Temporary source failure implementation** | Keep last-known data with explicit sync time/date and stale/unavailable warnings; validate fresh-dependent partial answers | Distinguish recoverable availability/freshness gaps from confirmed deletion and factual conflict |

Actual client roster, account IDs, emoji mappings and default team grants can remain configuration inputs; do not substitute guessed values. Existing test-dependent provider/freshness choices need evaluation contracts and results, not another forced preference question. Exact libraries, indexes, queue counts and JSON fields should be proposed by engineering with reasons once the foundation is known.

## 7. How answers will feed the architecture

For each answer, record the decision, alternatives, rationale, affected sections and remaining verification. Keep recommendations visibly provisional until accepted. Do not mark a provider capability or runtime invariant verified merely because a design is approved.

The [Solution Architecture](Client-Knowledge-Base-Solution-Architecture.md) now develops the first full draft using the KB requirements and decisions through ARCH-Q23. It distinguishes agreed requirements, recommended engineering choices, configuration inputs and test-dependent selections. This discovery record preserves the decision history; the architecture draft supplies the implementation design. Runtime tests, configuration and final acceptance remain outstanding.
