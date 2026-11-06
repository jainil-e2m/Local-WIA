# Fathom intake scope — Maintained Client Knowledge Base

Initial review: **19 October 2026 (IST)**. Corrective WIA-key verification: **20 October 2026**. Method: required data → retrieval/access → live evidence → frontend feasibility → remaining checks. This continues the reviews in [slack_scope.md](slack_scope.md) and [leadlock_scope.md](leadlock_scope.md).

## 1. Feasibility verdict

**The WIA API key works for real client calls and office hours.** The 20 October recheck retrieves the user-identified The Penny/Ridgefield strategy calls and a Carmen-recorded Google Ads Office Hours transcript/summary. This supports meeting evidence, engagement history, preparation context and candidate commitments. Full recorder/client/history coverage and webhook delivery remain unverified.

**Correction to the original finding:** `frontend/.env` contained two distinct `FATHOM_API_KEY` entries. The earlier probe's `parseEnv` used the last entry, an E2M key, so its default listing returned four Jainil-recorded examples. The WIA key was already present but overridden. The second entry has been renamed `FATHOM_E2M_API_KEY`, preserving both secret values; the single active `FATHOM_API_KEY` now selects WIA. The original four-recording results below are historical E2M-control findings, not a limitation of the WIA key. WIA–E2M vendor syncs still must not be assigned to downstream clients just because they mention client work.

### 20 October production verification

| Source example | Recording ID | Transcript | Summary | Candidate actions |
|---|---:|---:|---|---:|
| Ridgefield x WIA — Monthly Strategy Call | 192835286 | 251 speaker/timestamp segments | Present | 4, with assignee information |
| The Penny + WIA — Monthly Strategy Call | 192285654 | 245 speaker/timestamp segments | Present | 7, with assignee information |
| Google Ads Office Hours — 10.15.2026, Carmen | 193137346 | 700 speaker/timestamp segments | Present | Not assessed in this per-recording sample |

The WIA sample contains **20 meeting metadata examples**, 13 recorded by hello and seven by Carmen. This includes internal meetings as well as client/programme material; it is not 20 verified client calls. Sampling stopped after finding both named client calls, with more pages remaining. Explicit hello/Carmen recorder queries each returned ten matching records, also with more pages remaining.

**Thirteen new GET requests succeeded:** the initial seven-request duplicate-key comparison includes the E2M control; six further reads confirm the corrected active key, actual client action-item fields, recorder filters and the office-hour content. No structured due-date field is present on the eleven client-call actions. Presence/assignment does not establish acceptance, current open state or independent verification. Transcript field presence does not validate every speaker attribution or complete programme attendance.

Evidence: [key comparison](knowledge_base/wia-knowledge-base/verification/fathom/access_recheck_2026-10-20.json), [active-key confirmation](knowledge_base/wia-knowledge-base/verification/fathom/active_key_confirmation_2026-10-20.json). Reports retain metadata/counts, not new transcript/summary bodies. No remote writes, callbacks, permission changes or webhook operations occurred.

The user directs Fathom for all future meetings; its role is broader than the mock frontend's programme/office-hour label. Historical Zoom and Drive records remain separate backfill sources. **Webhook implementation and delivery testing are deferred as requested.** No webhook was created, changed, triggered or verified in this review. No frontend sample was replaced and no backend integration was deployed.

## 2. Credentials and retrieval method

- Current WIA tests read the single `FATHOM_API_KEY` from `frontend/.env`, using `X-Api-Key` with `https://api.fathom.ai/external/v1`. The preserved E2M control has a separate `FATHOM_E2M_API_KEY` name. Neither belongs in a `VITE_` variable. The original probe selected the last duplicate entry; the corrective script examined both before the configuration was fixed.
- The probe performs GET requests only. Transcript/summary requests omit `destination_url`, so they return directly and do not request a callback to any external receiver.
- The meeting-list probe follows `next_cursor`, capped at 20 pages. This run returned four records on the first page with no further cursor. This exhausts that **query**, not every private/shared meeting in the organisation.
- Content was requested inline for the returned page. Separate transcript and summary endpoints were also tested for three returned recording IDs. Reports retain metadata, counts, short transcript/summary excerpts and bounded action-item samples; they are not a full transcript archive.

Fathom documents keys as user-scoped: access depends on recordings and sharing permissions. Admin status does not open other users' private recordings. A single observed recorder and an empty team listing do **not** establish the subscription tier or prove that sharing cannot be configured. [Official key/access guidance](https://developers.fathom.ai/quickstart).

## 3. Live test results

Initial probe: **17:23:42–17:23:59 IST**. Recorder-filter follow-up: **17:24:51–17:24:53 IST**. **12 GET requests, all HTTP 200.** HTTP success alone does not establish nonempty content or correct filtering.

| Check | Requests | Observed result |
| --- | ---: | --- |
| `GET /meetings` | 1 | Four unique recording IDs; no next cursor. |
| `GET /teams` | 1 | Empty `items`; no next cursor. |
| `GET /team_members` | 1 | Empty `items`; no next cursor. No team roster validated. |
| `GET /meetings` with transcript, summary, action, highlight and CRM include flags | 1 | Four transcripts, three summaries, five action items, three demo highlights. CRM reports `No CRM connected` for every recording. |
| `GET /recordings/{recording_id}/transcript` | 3 | Three populated transcripts; includes 475-segment project sync, eight-segment impromptu sample and 143-segment demo. |
| `GET /recordings/{recording_id}/summary` | 3 | Two populated summaries; demo summary absent despite HTTP 200. |
| `GET /meetings?recorded_by[]=...` for known Whitney/Gisselle emails | 2 | Both returned the same four Jainil-recorded IDs. No returned row matched the requested recorder. Filter semantics are not validated. |

The last check uses the documented array-style query. It did not uncover an additional WIA recorder or establish an empty authorised result for one. Do not claim the requested people have no meetings, or use an HTTP 200 response as proof the filter worked. Apply local recorder/client checks and reconcile with Fathom UI or a known target recording before depending on filter-based ingestion. The default API query also has documented limitations on external recorder inclusion. [List-meetings reference](https://developers.fathom.ai/api-reference/meetings/list-meetings).

### Returned recordings and relevance

| Recording ID | Recording | Source date | Assessment for this KB |
| --- | --- | --- | --- |
| `192191254` | Wedding Industry Ads X E2M AI Weekly Sync Calls | 13 October 2026 | Useful structural example, including Whitney/Gisselle discussion; this is a vendor/project sync, not a verified WIA-to-client delivery call. |
| `186236649` | Impromptu Google Meet Meeting | 24 September 2026 | Short feature-development discussion; client identity not established. Keep unassigned/excluded from WIA client records. |
| `186218372` | Impromptu Google Meet Meeting | 24 September 2026 | Transcript explicitly describes a webhook test. Exclude from production client activity. Its historic discussion does not verify a working webhook today. |
| `186193499` | Fathom Demo | Demo dates inconsistent | Demonstration material; exclude from client records and historical coverage calculations. |

All four have `shared_with = no_teams`, null recorder team, and null `meeting_type`. The last record mixes a 2021 recording start with a 2026 recording end/creation date. Do not turn that into a multi-year meeting duration or a claim that client coverage starts in 2021. For the three non-demo rows, recording dates span 24 September–13 October 2026; no newer client coverage is established.

## 4. What data we need and how to get it

| Required input | API fields / method | KB use | Current verification |
| --- | --- | --- | --- |
| Stable source identity | `recording_id`; retain source account/connector ID | Deduplication, retries, citation identity, Zoom/Fathom overlap reconciliation | Four distinct IDs verified. Do not extract the recording ID from the browser URL: API IDs and URL call IDs differ in these samples. |
| Meeting title and dates | `title`, `meeting_title`, `created_at`, `scheduled_*`, `recording_*` from `/meetings` | History ordering, labels, recorded duration and freshness | Present, with demo timestamp anomaly. Keep event time separate from import/creation time. |
| Recorder and invitees | `recorded_by`, `calendar_invitees`, domains, `is_external` | Identity candidates, client/host mapping and access context | Present. Invitees are not an attendance register. Recorder is not automatically host or account manager. |
| Recording links | `url`, `share_url`; action `recording_playback_url` | Open original evidence and cited moments | URL strings returned; browser playback and recipient permissions not tested. Avoid exposing share links outside authorised KB access. |
| Transcript text and provenance | `/recordings/{id}/transcript`, or `include_transcript=true`; segment text, speaker and timestamp | Quotes, decisions, asks, objections, approvals and commitments | Four populated inline transcripts; three independently fetched. Speaker identity still requires care. |
| Summary | `/recordings/{id}/summary`, or `include_summary=true`; template and Markdown | Starting point for meeting recap, handover and preparation | Three of four inline summaries populated. Preserve as Fathom-generated content, separate from direct transcript evidence and KB-generated interpretation. |
| Candidate action items | `include_action_items=true`; description, assignee, completion, source timestamp/playback URL, `user_generated` | Seed commitment review and follow-up lists | Five across two recordings. All `user_generated=false` and `completed=false`; no structured due/deadline field observed. |
| Highlights | `include_highlights=true` | Optional navigation to important discussion spans | Only three demo highlights returned. Real client-useful highlight quality unverified. |
| CRM matches | `include_crm_matches=true` | Optional identity hints if later available | No CRM connected; no contact/company/deal matches verified. Does not verify LeadLock connectivity. |
| Sharing and team coverage | Meeting sharing fields; `/teams`, `/team_members`; known-recording reconciliation | Diagnose missing recorders and meeting coverage | Empty teams/members and one observed recorder. WIA production sharing remains open. |

Use the [transcript](https://developers.fathom.ai/api-reference/recordings/get-transcript) and [summary](https://developers.fathom.ai/api-reference/recordings/get-summary) endpoints for direct per-recording retrieval. They returned successfully in this test; schema availability must still be checked per recording.

## 5. Content quality and field-level limits

Across four inline recordings, **646 transcript segments** had speaker display names and timestamps. **611** also had a nonempty matched calendar-invitee email. The remaining 35 segments are not safely attributable to a client by email alone.

- The WIA–E2M sync has 475 segments, all with names, timestamps and matched emails. Its summary and three action items include source links, illustrating the evidence structures needed by the frontend.
- The eight-segment impromptu recording labels its speaker Krish Patel but returns no matched speaker email. Its calendar invitee list contains Jainil; this demonstrates why invitees, recorder and speaker must be separate fields. Its two assigned actions likewise lack assignee email.
- The shorter webhook-test recording contains 20 segments; 13 have matched emails. Do not infer perfect attendance or speaker identity from the metadata classification.
- The demo has a transcript but no summary. Missing summaries, transcripts, classifications or CRM matches must remain explicit coverage gaps rather than fabricated data.
- The five actions contain descriptions, names, completion flags and timestamps; none supplies a structured due date. No completed, acknowledged, in-progress or independently verified action example was observed.

Speaker matching and summaries are provider outputs. Their presence does not guarantee correct attribution, agreement or exhaustive capture. A statement such as “send a revised brief” establishes a candidate request/commitment, not that it was sent. Validate decisions and deadlines against the relevant transcript span, preserving later corrections and conditions.

## 6. Mapping to the current frontend

The frontend at `knowledge_base/wia-knowledge-base/frontend` is fictional local sample data. No client in this test was mapped to Bloom Manor, Willow & Pine or another fictional account.

| Frontend surface / fields | What Fathom can support | Additional work or evidence |
| --- | --- | --- |
| Source Library and evidence drawer: `Evidence.kind`, `title`, `date`, `author`, `excerpt`, `locator` | Fathom source kind, recording title/date, transcript speaker, quoted excerpt and timestamp | Add stable provider recording ID, original URL, segment range and access provenance to the implementation. `tag` is reviewed classification, not a supplied Fathom category. |
| Client → Meetings | Historical call list and cited conversation snippets | Confirm client mapping; do not include vendor syncs, demos or unrelated meetings. The current “Read transcript” drawer shows excerpt evidence, not an implemented full transcript reader. |
| Engagement history / Meetings lane | One meeting event with attached decisions and evidence | Deduplicate multiple excerpts into their underlying event. Preserve event versus ingestion time; reconcile overlapping Zoom/Drive copies. |
| Now, weekly focus and Handover brief | Supported client asks, blockers, decisions and conversation recaps | Generated synthesis needs client-scoped evidence, freshness and review; no deterministic weekly focus or account-health field arrives from Fathom. |
| Client profile: story, goal, audience, voice and differentiator | Explicit statements from a properly mapped client conversation can update individual facts | Retain field-level citations, effective dates and document/call conflicts. Invitees do not establish service tier, contract date or active-client status. |
| Call Prep: `context`, `needs`, `agenda`, `opportunity`, `objective`, `sourceIds` | Past decisions and open requests can inform suggested preparation | Agenda/objective/opportunity are generated recommendations. Google Calendar supplies authoritative upcoming event/date/time and event-client association. A completed recording's scheduled times do not provide a future call queue. |
| Commitments / Action register: title, owner, source, note | Candidate descriptions, assignee hints and timestamp citations | Map assignee to reviewed WIA/client identities; keep unknown owner/side when unresolved. Extract and confirm due dates from conversation or another source; support null due dates. |
| Actions: due, status, acknowledgement, verification | Source completion flag may be retained as a provider-reported state | Do not map generated assignment to acknowledgement, `completed=false` to an agreed open task, or `completed=true` to independent Verified. No completed example tested. Reconcile with Slack, ClickUp and human verification. |
| Client health, sentiment, last touch and activity | Attributed client language and a correctly mapped conversation time | Sentiment is an interpretation, not a satisfaction score. Last touch requires actual client participation; recording activity and invitees alone are insufficient. No health score or coverage percentage is supplied. |
| Accelerator Attendance: Attended/Missed | Transcript speaker presence may support that a person spoke in a specific recorded session | Cannot calculate absence from a missing recording, an invitee, silence or no transcript. Need complete session schedule, programme roster and actual participant/join records or a maintained attendance source. |
| Invoices & terms, Client Profile lead-outcome snapshot | Discussion can provide context or a reported claim | Fathom is not the authoritative invoice/payment, contract or LeadLock outcome feed. Retain the Dubsado/Gmail and LeadLock plans. |
| Settings / connector coverage | Retrieved counts, content availability and sync/access checks | Actual coverage denominator and expected recorder/client roster must be established before displaying percentages or “all meetings synced”. |

### Specific mock assumptions checked

- [`data.ts`, line 25](knowledge_base/wia-knowledge-base/frontend/src/data.ts#L25) contains exactly **one Fathom evidence object**, `willow-fathom`, with a two-person commitment excerpt and timestamp range. Timestamped, speaker-labelled quotes are structurally feasible. This key does not validate the fictional exchange, its attendance or a corresponding real WIA client session.
- The mock call `call-willow` references that evidence for programme preparation. Historical Fathom content can support that context after mapping; it cannot establish the upcoming calendar event.
- [`data.ts`, line 84](knowledge_base/wia-knowledge-base/frontend/src/data.ts#L84) labels Fathom “Office hours & programme context”, one record, limited coverage, with two missing transcripts. These are sample assertions, not measured production facts. Future implementation must broaden the description to all recorded meeting types and compute actual coverage.
- `ClientDetail.tsx` hardcodes three accelerator attendance dates and marks two Willow sessions missed. Fathom invitees or absent recordings cannot validate those badges. The attendance source remains a separate open check.
- `types.ts` requires nonempty action due/owner/side and client health/coverage fields. Real ingestion needs nullable/unknown states and provenance rather than filling those fields to match the mock.

## 7. Client and session matching rules

1. Maintain an explicit client registry and verified contact-email/domain aliases. WIA staff and E2M vendor participants are not downstream WIA client identities.
2. Combine a known calendar event, client contact identities and reviewed recording/title context. Names and titles are hints; common personal-email domains cannot identify a business.
3. Distinguish client strategy/onboarding calls, accelerator group office hours, WIA internal meetings and E2M project meetings. All four original E2M examples had null `meeting_type`; the WIA list also contains mixed meeting purposes, so rules/review remain necessary.
4. A group office-hour recording can concern several clients. Associate client-relevant speaker/segment evidence rather than copying every participant's discussion into every client profile. Preserve appropriate access boundaries.
5. Keep unassigned records in a review queue. Do not infer a paid engagement from an invitee or force a mapping to a mock account.
6. Use the provider recording ID with connector/account provenance for identity. Compare event/time/participants when reconciling the same conversation recorded by Zoom and Fathom; retain both source references without double-counting it.

## 8. Implementation direction: webhook first for future intake

**This section is a proposed implementation contract, not a tested integration.** The user's existing webhook and secret were not inspected or exercised. An API success does not validate its destination, enabled triggers, signature or coverage.

- Receive future ready-content events at a backend HTTPS endpoint. Select payload content for transcript, summary and actions; configure own/shared meeting triggers to match the verified WIA recorder and sharing arrangement. Existing webhook configuration must be reviewed before creating another one.
- Verify signatures over the raw request body using the configured secret; retain event identity and processing state. Store the received event durably and process normalization/extraction asynchronously, acknowledging accepted delivery promptly.
- Deduplicate delivery retries by event identity and upsert the underlying recording by provider ID/account. Keep receipt time, recording time and content version separate. Define replay and failure recovery handling.
- Reuse the API for authorised historical backfill, missing-content retrieval and reconciliation. Webhook-only intake does not supply the historic Zoom/Drive archive or prove every expected future recording arrived.
- Track missing transcript/summary, identity exceptions, demo exclusion, invalid dates, access failures and last successful intake independently of client relationship health. Provider action completion changes and later summary edits require a refresh/reconciliation policy; change-event delivery was not tested.

Fathom documents own/shared recording triggers and signed deliveries. Follow the provider's signing guidance and verify the actual configured receiver later. [Official webhook guidance](https://developers.fathom.ai/webhooks).

For API recovery jobs, respect rate-limit headers, cursor state and bounded retries. Fathom currently documents 60 global requests per minute and additional heavy-content limits that can tighten during elevated activity. [Official rate limits](https://developers.fathom.ai/api-overview). This short probe received no 429 response; sustained throughput and retry behaviour were not load-tested.

## 9. Open verification items and closure evidence

| ID | Current status / remaining scope | Evidence needed |
| --- | --- | --- |
| F-V-01 | Production account and known samples verified; complete recorder coverage open | WIA key retrieves The Penny, Ridgefield and Carmen office hours. Finish expected-owner/sharing inventory and full historical reconciliation; do not assume one sample covers every private/shared recording. |
| F-V-02 | WIA hello/Carmen filter samples verified; complete filter/pagination visibility open | Each tested first page contains ten matching recorders. Earlier nonmatching results used the E2M key. Complete relevant pages and external/shared-owner checks before claiming exhaustive coverage. |
| F-V-03 | Real client/office-hour content retrieved; exact engagement/contact/segment scoping open | User-identified client calls and a real office-hour transcript/summary are now available. Review contact/engagement IDs, quoted segments and group evidence access boundaries. |
| F-V-04 | Attendance | Confirm complete session schedule, roster and tracking rules. Subsequent [Drive verification](google_drive_scope.md) successfully reads both Google/Meta Roll Call sheets and sample dated rows, establishing reported attendance data beyond Fathom invitees. Notes/counters, start/hold dates and rescheduling still need reconciliation; no complete attendance calculation is verified. |
| F-V-05 | Commitments and deadlines | Reconcile a real meeting request with owner, acknowledgement, explicit deadline and downstream completion/verification evidence. |
| F-V-06 | Webhook end-to-end | Verify existing destination, triggers, selected content and signing secret; receive a genuine ready-content event, validate signature, persist/process it, and prove retry deduplication. No webhook work performed here. |
| F-V-07 | Archive and freshness | Reconcile expected historical/future WIA meeting list, dates, exclusions, missing content and Zoom/Drive overlaps. Do not count the demo's 2021 date as archive coverage. |
| F-V-08 | Citation playback | Authorised user can open a source recording and the precise timestamp; source permissions remain appropriate to the KB user. URL strings alone do not prove playback. |

**Result:** API transport, production client-call/office-hour samples and sampled recorder filters are verified after correcting the duplicate key. Full coverage, semantic action reconciliation, attendance, playback and webhook reliability remain open. Original E2M-only results must not be used as evidence that the WIA key lacks those known recordings.

## 10. Reproduce and inspect evidence

From the workspace root:

```powershell
node knowledge_base/wia-knowledge-base/verification/recheck_source_access.mjs --fathom --confirm-active
```

This checks the corrected active configuration, two bounded action-item pages, two recorder filters and a previously identified office-hour example. It writes `active_key_confirmation_2026-10-20.json`; it does not exhaust the archive. The historical duplicate-key diagnosis is preserved separately. Repeating remote reads requires provider network access.

Original 19 October commands, retained for traceability:

```powershell
node knowledge_base/wia-knowledge-base/verification/fathom/verify_fathom.mjs
node knowledge_base/wia-knowledge-base/verification/fathom/verify_fathom.mjs --wia-recorders
python knowledge_base/wia-knowledge-base/verification/fathom/audit_fathom.py
```

The original first two commands repeat remote reads using the now-corrected active key and overwrite their original reports, which contain the earlier review date. Preserve those original reports if comparing historically. The audit is offline and reads those original reports. Credential values and the webhook secret are not written to reports; retained metadata/excerpts are internal verification artifacts.

- [GET-only probe](knowledge_base/wia-knowledge-base/verification/fathom/verify_fathom.mjs)
- [Initial live report](knowledge_base/wia-knowledge-base/verification/fathom/live_probe.json)
- [Recorder-filter follow-up](knowledge_base/wia-knowledge-base/verification/fathom/wia_recorder_probe.json)
- [Offline audit](knowledge_base/wia-knowledge-base/verification/fathom/audit_fathom.py)
- [Audit results](knowledge_base/wia-knowledge-base/verification/fathom/local_audit.json)

The older `frontend/corpus/probe-fathom.mjs` was inspected but not executed. Its inference from one observed recorder to free-plan/no-team restrictions is not treated as verified, and its optional webhook-registration path was not used.
