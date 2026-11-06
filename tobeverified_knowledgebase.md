# Knowledge Base — items to verify

Updated: 20 October 2026. All items below remain open.

Use this register for factual source/access checks. Product ambiguities are in [tobeclarified.md](tobeclarified.md); the specific GHL pricing/billing investigation is in [tobeverified.md](tobeverified.md).

## KB-V-01 — Survey responses and satisfaction feedback

**19 October source-test update:** Survey definitions and submissions in WIA's configured GHL location returned API scope denials. No response or satisfaction-survey purpose was inspected. This item remains open. See [LeadLock scope](leadlock_scope.md).

**Subsequent Drive/Gmail context:** Drive contains files named Market Research Survey Submissions, and the retrieved Ridgefield meeting summary describes questions for booked couples. Gmail also contains discussion of sharing market research. These do not establish the location/purpose of WIA's own client-service satisfaction surveys. Keep venue customer research separate from WIA client-health feedback. See [Drive scope](google_drive_scope.md).

**Known:** On 22 September at 36:44, Whitney described feedback surveys sent at different stages of the client process. Their existence was discussed; their storage in GHL was not established.

**Verify:**

- Which surveys are currently used, for which offers and engagement stages?
- Where do the forms and responses live: WIA's GHL account, client sub-accounts, or another service?
- Can responses be reliably associated with a WIA client and submission date?
- What is available: question wording, raw answers, scores and their scale, free-text concerns, submission timestamps, and source references?
- What read access, export/API route, historical coverage, and refresh method are available?

**Evidence needed to close:** An authorised sample response, confirmed source location and client mapping, and a demonstrated read/export route.

**Intended use if verified:** Evidence-backed satisfaction context and client-health signals. Preserve direct feedback separately from generated sentiment interpretations. No response does not imply satisfaction or dissatisfaction.

## KB-V-02 — Support intake route and coverage

**19 October source-test update:** GHL form/submission, pipeline and conversation reads were denied by the current API scope. The maintained support route and a request-to-resolution example remain unverified. This item remains open. See [LeadLock scope](leadlock_scope.md).

**Subsequent ClickUp check:** Live Ridgefield and Dogwood task lists contain GHL-settings/troubleshooting work with reported statuses. This verifies that ClickUp holds some issue-related work, but does not establish the authoritative support intake route, all requests, or independently confirmed resolution. See [ClickUp scope](clickup_scope.md).

**Subsequent Gmail check:** An incoming The Penny request is readable in `hello@weddingindustryads.com` and Cc'd to `support@leadlockpro.com`. The associated proposed WIA reply is a **DRAFT**, not evidence of sending, acknowledgement or resolution. Shared email issue visibility is now verified; complete support-inbox coverage and an independently traced request-to-resolution record remain open. See [Gmail scope](gmail_scope.md).

**Known:** On 22 September at 38:04–39:25, the team described a support form routing to Danielle at support@leadlockpro.com and a GHL pipeline that was not being actively monitored by Whitney/Gisselle.

**Verify:** The current form destination, mailbox/ticket/pipeline used in practice, access, client mapping, ownership, status tracking, resolution evidence, and historical coverage. Determine whether Slack/email and form submissions refer to the same issue before counting them separately.

**Evidence needed to close:** Trace a representative request from submission through handling and closure using the actual maintained source.

**Related agreed change:** [KB-CH-02 — Support issues in Client Profile](knowledgebase_changes.md#kb-ch-02--support-requests-and-unresolved-issues-in-client-profile). The display requirement is agreed; a GHL ticket connector is not yet established.

## KB-V-03 — Lead-outcome data and account access

**20 October recheck:** Both existing PITs still authenticate their tested location metadata, while pipelines/opportunities remain scope-denied. Dogwood contacts/calendars fail similarly with the agency PIT. Current-v3 opportunity requests also return 401, so an old endpoint version does not explain the failure. Keep this check open pending appropriate location-feature scopes and authorisation. The preferred central approach is a private OAuth app with authorised location access, not manually creating a PIT per client. See [fresh evidence](knowledge_base/wia-knowledge-base/verification/leadlock/access_recheck_2026-10-20.json), [v3 evidence](knowledge_base/wia-knowledge-base/verification/leadlock/v3_access_recheck_2026-10-20.json) and [test plan](knowledge_base/wia-knowledge-base/verification/leadlock/access_test_plan.md).

**19 October source-test update:** WIA location/contact reads succeeded, but agency location discovery and two other Slack-referenced location reads returned 403. Pipeline/opportunity/calendar reads in WIA's account were scope-denied. Known-account contact searches returned candidates, not verified client-location mappings or outcome data. This item remains open. See [LeadLock scope](leadlock_scope.md) and [follow-up evidence](knowledge_base/wia-knowledge-base/verification/leadlock/followup_probe.json).

**Subsequent agency-token update:** The newly supplied `GHL_AGENCY_PIT` successfully reads the LeadLock agency, discovers **59 sub-accounts**, reads Dogwood's account identity/timezone, and searches agency/location users. Earlier discovery failures apply to the original WIA token. Direct Dogwood contacts, pipeline/opportunity/calendar and other feature reads with the agency token remain scope-denied; no lead-outcome snapshot is yet validated. Demo/internal accounts in the inventory must be excluded through a reviewed engagement roster. Evidence: [agency verification](knowledge_base/wia-knowledge-base/verification/leadlock/agency_probe.json), [user-search verification](knowledge_base/wia-knowledge-base/verification/leadlock/agency_users_probe.json).

**Known:** The user requested a lead-outcome snapshot in Client Profile. The 22 September call establishes the purpose: understand inquiries progressing to booked clients.

**Verify:**

- Which clients use LeadLock, the correct sub-account/location mapping, and read access for each account. Access to WIA's own account does not establish access to client sub-accounts.
- Whether inquiry, appointment, pipeline-stage and booking records are maintained consistently, including dates, duplicates, cancellations, and missing updates.
- Availability of stage history and follow-up activity needed to calculate conversions and detect stalled inquiries. A current stage alone cannot reconstruct every historical transition.
- With each account owner, confirm stage meanings, booking criteria, period/timezone, cohort versus period calculations, and inactivity rules.
- Whether reliable acquisition-source evidence exists before describing outcomes as ad-generated.

**Evidence needed to close:** A mapped sample account, demonstrated reads, and a reconciled snapshot using agreed definitions. Record any account-specific limitations.

**Related agreed change:** [KB-CH-03 — Lead-outcome snapshot](knowledgebase_changes.md#kb-ch-03--lead-outcome-snapshot-in-client-profile).

## KB-V-04 — Fathom production meeting coverage, attendance and webhook delivery

**20 October correction — production samples verified:** Two distinct `FATHOM_API_KEY` entries existed in `frontend/.env`; the last one selected the E2M account, explaining the earlier four-recording result. The first, WIA-authorised key lists 20 bounded meeting examples recorded by hello/Carmen and retrieves the user-identified **The Penny + WIA** and **Ridgefield x WIA** monthly strategy calls. Their transcripts contain **245 / 251 segments**, summaries are present, and they expose **seven / four candidate actions** with no structured due field. Carmen's **Google Ads Office Hours - 10.15.2026** has a **700-segment transcript** and summary. Sample hello/Carmen recorder queries each returned ten matching rows with more pages. Thirteen new GETs succeeded including the E2M control. See [diagnosis](knowledge_base/wia-knowledge-base/verification/fathom/access_recheck_2026-10-20.json) and [active-key confirmation](knowledge_base/wia-knowledge-base/verification/fathom/active_key_confirmation_2026-10-20.json).

The local configuration now retains WIA under `FATHOM_API_KEY` and preserves the other value as `FATHOM_E2M_API_KEY`. No key value was changed, and no webhook/provider permission was altered. Basic production sample access is no longer open. Full expected-recorder/client/history coverage, contact/segment mapping, attendance, playback, semantic action reconciliation and genuine webhook processing remain open; pagination was not exhausted for the WIA sample.

**19 October source-test update:** The supplied API key succeeded on **12 GET requests**. Four recordings have transcripts, three summaries and five action items; all returned recorders are `jainil.trivedi@e2m.solutions`. The set includes one WIA–E2M sync, two impromptu recordings and a demo, with no verified WIA-to-client/office-hour example. Teams and team members returned empty lists. Known WIA recorder filters returned the same nonmatching records, so their semantics remain unresolved. This is a coverage/filtering check, not an invalid-key finding. See [Fathom scope](fathom_scope.md) for results and field-level frontend mapping.

**Still verify after the correction:** Full WIA recorder/account-sharing scope, client/contact and group-segment mapping, complete filter/pagination behaviour across intended owners, citation playback and archive completeness. Establish participant/session/roster evidence before marking attendance or absence. Confirm explicit action deadlines and downstream acknowledgement/completion evidence; generated Fathom actions are not automatically agreed or verified tasks.

**Webhook deferred to implementation:** Review the existing destination, triggers, selected payload and signing secret; prove genuine event reception, signature verification, durable processing and retry deduplication. The API test did not create, alter or validate a webhook.

**Subsequent attendance-source discovery:** ClickUp's Google and Meta accelerator lists contain 14 Complete attendance tasks linking to two distinct Google Sheets. Their contents were not fetched; review them during the Google Drive source test as candidate attendance sources. Task completion is not individual attendance evidence. References are preserved in the [ClickUp audit](knowledge_base/wia-knowledge-base/verification/clickup/local_audit.json).

**Drive verification now completed on samples:** Both Roll Call sheets are readable through the same WIA account, including Members and October ranges. Twelve Google and four Meta dated attendance rows were retrieved. This establishes a source for sheet-reported attendance, while notes/counters disagree in one case and start/hold/rescheduled-session rules require review. It does not establish platform-verified joining or complete attendance history. Complete Fathom recorder coverage and webhook delivery remain open after the successful production samples above. See [Drive scope](google_drive_scope.md).

**Evidence needed to close:** Reconciled production sample coverage plus reviewed client/segment mappings; a traceable attendance example from the appropriate source; and a successfully verified and deduplicated live webhook delivery. Detailed checks F-V-01 through F-V-08 remain in [fathom_scope.md](fathom_scope.md).

## KB-V-05 — ClickUp action semantics, client mapping and refresh

**19 October source-test update:** The existing `CLICKUP_TOKEN` in `frontend/.env.local` succeeds on **50 GET requests** against WIA's workspace. Five list queries returned **338 unique tasks**, including Ridgefield management, Google/Meta accelerator operations and two Dogwood onboarding lists. Status, assignees, dates, descriptions, nested work, checklists and role/phase fields are verified. There are 151 undated tasks and 76 unassigned tasks; all nine Role=Client examples lack a named assignee and due date. Eight comment reads returned empty arrays. See [ClickUp scope](clickup_scope.md).

**Verify:** The complete engagement/list registry, shared-programme client mapping, recurrence and not-applicable status rules, known populated comments/threads, a real meeting/task deadline conflict, explicit acknowledgement and independent delivery verification, linked document/attendance data, and the incremental/move/deletion/access-loss strategy. Four terminal tasks have unresolved checklist items; provider completion and KB Verified must remain separate. Two September Ridgefield onboarding list IDs were not rediscovered in the active hierarchy; their lifecycle remains unknown.

**Evidence needed to close:** A reviewed scope/mapping registry and reconciled real action/acknowledgement/deadline/verification examples, plus a demonstrated refresh/reconciliation path. Detailed C-V-01 through C-V-08 are in [clickup_scope.md](clickup_scope.md). No ClickUp writeback was tested or built.

**Attendance dependency update:** The linked sheets have now been read in the Drive review. Their session rows can support reported attendance after programme/client mapping, but note-versus-counter conflicts and tracking-window rules remain unresolved; the attendance calculation is not yet ready for blanket automation.

## KB-V-06 — Google source coverage, interpretation and notification delivery

**19 October live-source update:** Google user consent and offline token refresh succeeded for `hello@weddingindustryads.com`. **42 source GETs succeeded**: 22 Gmail reads and 20 Drive/Docs/Sheets reads. Dubsado signing/payment notifications, client approval/support threads, a bounded attachment byte read, client questionnaires, a meeting summary and programme attendance samples are verified. This closes basic API-access uncertainty for those examples, not full history, linked agreement/invoice state or deployed notifications.

**Verify:** Complete reviewed mailbox/client/folder scope; relevant historical pages and descendants; robust MIME/quote/draft/link handling; full financial-record reconciliation; actual source citation access; document versions/aliases/shortcuts and binary parsing; complete programme attendance rules/history; and actual Gmail Pub/Sub / Drive changes-watch POST delivery to the backend domain, with renewal, deduplication and recovery.

**Evidence needed to close:** Reconciled source coverage and client/field mappings plus genuine incoming change notifications processed through the backend. Neither the local OAuth callback nor empty current-history/change responses demonstrate webhook delivery. See [Gmail scope](gmail_scope.md), [Drive scope](google_drive_scope.md), [Google refresh evidence](knowledge_base/wia-knowledge-base/verification/google/refresh_probe.json) and the per-source audits.

## KB-V-07 — Calendar mapping, lifecycle and notification delivery

**19 October live-source update:** Both Calendar read scopes are granted for the existing WIA Google OAuth client. Enabling the Calendar API resolved the earlier `accessNotConfigured` failure. Thirteen successful Calendar GETs discovered nine subscribed calendars and sampled five calendars' events: 427 list rows / 425 distinct calendar-event source records, including cancellations and copies. The separate future primary-calendar query exhausted pagination and includes real upcoming client calls; the initial historical primary query remains truncated at 200 rows. See [Calendar scope](google_calendar_scope.md).

**Verify:** Reviewed calendar/client/engagement scope, staff-host assignment, multi-client and programme-session mapping, cross-calendar/recurrence deduplication, reschedule/private/all-day/DST handling, actual source access and source-cited preparation. Calendar invitees and RSVP are not programme attendance; the sampled Carmen office hours list Carmen alone. The LeadLock mailbox calendar has free/busy-only access. No Calendar watch, incremental sync, renewal or recovery was tested.

**Evidence needed to close:** Reviewed real-client mappings and reconciled queue/brief examples, agreed attendance evidence and a genuine change notification processed with deduplication, renewal and recovery. Detailed GC-V-01 through GC-V-06 and bounded-coverage evidence are in [google_calendar_scope.md](google_calendar_scope.md).

## KB-V-08 — Complete available historical backfill before launch

**20 October product decision:** The user requires historical client records to be backfilled entirely with all available data before launch. This replaces the proposed progressive/recent-history-first launch approach. See [KB-CH-09](knowledgebase_changes.md#kb-ch-09--complete-available-historical-backfill-before-launch).

**Verify:** The agreed client/business/engagement roster and source/file boundaries; complete authorised inventory and pagination; historical folder descendants, meetings, messages/threads and relevant task records; content extraction, duplicate reconciliation and correct client mapping; and the oldest/latest coverage and missing/inaccessible items for each source. Existing bounded API tests do not demonstrate a completed backfill.

**Subsequent 20 October decisions:** The launch scope is all currently active WIA clients across services; former-client archives will be scoped separately. Process all obtainable in-scope history and require WIA sign-off on a source-by-source gap report before launch. Inaccessible items remain unresolved until explicitly accepted or recovered. No particular gap has been accepted. See [KB-CH-15](knowledgebase_changes.md#kb-ch-15--all-active-wia-clients-across-services-are-the-launch-scope) and [KB-CH-16](knowledgebase_changes.md#kb-ch-16--wia-sign-off-on-historical-source-gaps-before-launch).

**Further 20 October clarification:** All obtainable history from every approved in-scope source must be gathered before launch even if its related frontend feature is Coming soon. No phase timeline is needed on Coming soon labels. See [KB-CH-22](knowledgebase_changes.md#kb-ch-22--backfill-all-approved-in-scope-sources-regardless-of-ui-delivery).

**Content-processing decision, clarified:** Process readable text, native Docs/Sheets, existing transcripts and extractable PDF/DOCX text. Keep scans, images and audio/video as links, disclosing unprocessed content in the WIA gap report. No OCR or new transcription. A linked recording/file is not processed content. See [KB-CH-26](knowledgebase_changes.md#kb-ch-26--historical-content-processing-and-linked-unprocessed-files) and [KB-CH-32](knowledgebase_changes.md#kb-ch-32--pdfdocx-text-extraction-included-no-ocr-or-new-transcription).

**Decisions/checks still pending:** The actual active-client roster, approved source/file boundaries and verified PDF/DOCX parser coverage; the named WIA sign-off owner, exact acceptance cases/thresholds and detailed completion checks. The user has confirmed the suggested acceptance areas and added responsive UI coverage. Source coverage, approved-scope processing and source-gap acceptance remain verification work even though the product policy is agreed.

**Evidence needed to close:** Reconciled per-client/per-source inventory and ingestion/processing results for all available in-scope history, documented gaps and the agreed launch-acceptance evidence. Historical requests without closure evidence also need current-state reconciliation before being treated as active work.

## KB-V-09 — Viktor structured orchestration, source access and actual cost

**20 October comparison request:** The user wants API LLM, Viktor-led and hybrid approaches compared, including directional skills, structured data, integration/tool usage and repeated-retrieval cost. The [comparison](knowledge_base_viktor_llm_comparison.md) is public-document/offline research, not a WIA API test or a selected production architecture.

**Subsequent candidate decision:** Retain selective hybrid, including active skill-based Viktor work and context-supplied API LLM analysis, and Viktor-led as the two implementation candidates. Test the completeness of the required skill-directed output and costs for both before selecting. API-only is a historical comparator. Candidate approval does not close any access, factual-quality, schema or cost check. See [KB-CH-41](knowledgebase_changes.md#kb-ch-41--retain-selective-hybrid-and-viktor-led-for-comparative-testing).

**Documentation findings:** Paid Viktor APIs document structured results and integration/script execution. Scheduled script tasks are documented as zero-credit; exact WIA tool availability and API-triggered script billing remain to be tested. Existing local Slack archives contain nine text-bearing Viktor messages, six Dogwood and three Funktastic/DJ Hybrid; that establishes examples, not complete coverage or truth of their source claims.

**Verify:** Actual paid-plan/API access and scope; read-only tools/identity and private-connection reach; known client/source matching; underlying record IDs, historical pagination and source citations; structured output on representative WIA cases; changed-data handling, latency and error/retry behaviour; incremental credits/tokens and existing scheduled-work overlap. Provider output must respect KB per-user client/module visibility. Do not count a report as original client communication or an independently verified outcome.

**Latest user context:** The user recalls approximately $1,000/month across team DMs and other Viktor work, reports excellent current call preparation and useful Google/Meta anomaly detection, and wants efficient usage/cost reduction without losing value. The invoice, actual plan/allowance, task-level usage and top-ups remain unverified. Do not infer a credit allowance or savings forecast from the recalled spend. Billing-metadata review does not authorise ingestion of private DMs.

**Scope decision:** New first-release work, including new Viktor requests, stays within the eight approved sources. Existing Viktor posts may be retained as attributed analysis; fresh paid-media analysis is separately scoped. A useful existing ad-related report does not establish a live paid-media connector in this KB.

**Evidence needed to close:** A bounded, explicitly authorised account-specific evaluation with recorded expected outcomes, schemas, source coverage, privacy/permission results and measured script/agent/API costs, plus reconciled invoices/usage and incremental KB expenses. Measure both useful retained workflows and candidate duplicate work before changing a plan or claiming savings.

## Evidence references

- [22 September discovery transcript](WIA_Meeting_Analysis/meetings/2026-09-22_knowledge-base-scoping/source.md), 36:44–39:25.
- [Historical access ledger](WIA_Meeting_Analysis/access_wia.md), GHL account versus location-specific token coverage. This is historical evidence, not a current access test.
