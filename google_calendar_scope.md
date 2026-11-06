# Google Calendar intake scope — Maintained Client Knowledge Base

Review date: **19 October 2026 (IST)**. Required data → retrieval/access → live evidence → frontend mapping → remaining verification. Related: [Gmail](gmail_scope.md), [Drive](google_drive_scope.md), [Fathom](fathom_scope.md), [ClickUp](clickup_scope.md).

## 1. Feasibility verdict

**Calendar read access now works for `hello@weddingindustryads.com`. Real historical and upcoming client calls support the frontend's call queue, next-conversation cards and schedule inputs to call preparation.** Enabling the Calendar API resolved the earlier `403 accessNotConfigured` error; this was an API-enablement issue, not a rejected OAuth key or missing Calendar consent.

The review completed **13 successful Calendar GETs**, discovered **nine subscribed calendars**, and sampled events on **five calendars**. There are **427 returned list rows**, or **425 distinct `(calendar_id, event_id)` source records** after overlapping windows are deduplicated. These are calendar copies/occurrences, including internal meetings, personal blocks and cancellations; they are not 425 unique meetings or clients.

The separate upcoming primary-calendar query exhausted pagination within its next-30-day window. The original primary-calendar historical query stopped at 200 rows and still had another page. Full historical coverage, all staff calendars, automatic client matching, actual attendance and live change delivery remain unverified. The frontend remains a fictional preview; no live integration or data replacement was implemented.

## 2. Authentication and access

Use the existing Google OAuth client, local `.env` configuration and callback `http://localhost:8765/oauth/google/callback`. No Calendar API key or separate Google account is required. The account owner granted these additional read permissions alongside existing Gmail/Drive access:

```text
https://www.googleapis.com/auth/calendar.calendarlist.readonly
https://www.googleapis.com/auth/calendar.events.readonly
```

All four requested scopes were granted and a refresh token is present. The prior Gmail/Drive refresh test remains separate evidence; Calendar source reads succeeded using the expanded grant. Credentials and tokens stay in ignored local storage. The temporary consent listener was stopped after consent; localhost is an OAuth callback, not a deployed notification receiver.

Calendar API service `calendar-json.googleapis.com` is enabled in the same project as the OAuth client. The initial disabled-service failure is preserved in `api_disabled_probe.json`; the retry report contains three further disabled-service responses before successful access. Do not count those as three ongoing permission failures.

| Discovered calendar | Reported timezone | Role | Events sampled? |
| --- | --- | --- | --- |
| `hello@weddingindustryads.com` — primary | America/Chicago | owner | Yes: historical and future windows |
| WIA - Tina Henares | America/Chicago | owner | Yes |
| WIA - Gisselle (Support) | America/Tegucigalpa | owner | Yes |
| WIA - Carmen Cruickshank | America/New_York | owner | Yes |
| WIA - Jacqueline Hood | America/Vancouver | owner | Yes |
| Whitney's Perfect Week | America/Chicago | owner | No |
| WLF Tier 1 Accelerator | America/Los_Angeles | reader | No |
| Holidays in United States | America/Chicago | reader | No |
| `hello@leadlockpro.com` | America/Chicago | freeBusyReader | No; role provides availability rather than client-call detail |

The calendar list is the authorised user's subscribed list, not an organisation-wide inventory. Calendar-list metadata is not proof of readable event content on each calendar. Shared-calendar permissions constrain the OAuth scope. Review the programme calendar's business relevance before intake. [Calendar list reference](https://developers.google.com/workspace/calendar/api/v3/reference/calendarList/list), [scope reference](https://developers.google.com/workspace/calendar/api/auth).

## 3. What was tested

| Read | Successful GETs | Observed result / limit |
| --- | ---: | --- |
| Calendar list | 1 | Nine calendars; list pagination exhausted. Primary matches the intended WIA mailbox. |
| Initial event windows | 4 | Primary: 200 rows over two pages, **more pages remain**. Tina: 15 rows, complete. Support: 25 rows, complete. |
| Individual event reads | 3 | Dogwood strategy call, a recurring Block occurrence and a separate timed event. |
| Recurring master read | 1 | Block master contains a weekly-Friday recurrence rule. This validates series metadata retrieval, not client participation. |
| Targeted future/team follow-up | 4 | Primary: 131 rows over two pages; Carmen: 44; Jacqueline: 12. Pagination exhausted for these exact queries/windows. |
| **Total** | **13** | All reads after API activation returned HTTP 200. |

Initial window: **4 September 13:34 UTC to 18 November 13:34 UTC**. Follow-up primary window: execution time on 19 October through 30 days later; Carmen/Jacqueline include 14 preceding days and 30 following days. Exact timestamps and query bounds are retained in the reports. End-overlapping events can be returned even if they started before the lower bound, so distinguish ongoing from future calls.

Queries use `singleEvents=true`, `showDeleted=true`, `orderBy=startTime`, 100 rows per page and at most two pages per calendar/query. They are bounded feasibility reads, not a production synchronisation cursor or full backfill. The future follow-up prevents the truncated historical result from being mistaken for an empty upcoming schedule.

Offline audit of the **425 unique source rows** finds **360 confirmed, 65 cancelled, 361 recurring occurrences and four all-day rows**. There are 596 accepted, 276 needsAction and 43 declined attendee-response entries across these copies. Those are invitation responses, not attendance totals. Fourteen iCalUIDs occur on multiple sampled calendars, demonstrating the need to reconcile copies and recurring occurrences before counting meetings.

No event, RSVP, invitation, ACL or calendar was changed. No notification channel was registered. Conference, cancellation/reschedule and source URLs were not followed or operated.

## 4. Required inputs, retrieval and use

| Required input | Retrieval / fields | KB use and interpretation |
| --- | --- | --- |
| Calendar identity, access and timezone | `calendarList.list`: ID, summary, primary, role, timezone | Reviewed ingestion boundary, source account identity and permission/freshness reporting. |
| Event identity and provenance | `events.list/get`: event ID, calendar ID, iCalUID, htmlLink, created/updated | Stable evidence record, source link, update tracking and copy reconciliation. Retain source copies. |
| Scheduled time and length | start/end dateTime or date; offsets and timeZone | Upcoming/today queue, next scheduled call and **scheduled** duration. All-day events require a separate date representation. |
| Participants and invitation state | organiser, creator, attendees, self/organiser flags, responseStatus, attendeesOmitted | Client/host candidates, RSVP context and completeness. A shared mailbox organiser is not automatically the human host. |
| Subject and available description | summary, description, eventType | Call-type and client candidates; any explicitly supplied agenda. Empty description remains unknown, rather than an invented agenda. |
| Meeting location/reference | location, hangoutLink, conferenceData, URLs in description | Join/reference affordance when available. A Zoom link is not a recording or transcript. Missing structured conference data does not establish that no join link exists elsewhere. |
| Cancellation and recurrence | status, recurringEventId, originalStartTime; master's recurrence rule | Remove cancelled queue entries; distinguish series from occurrences and handle exceptions. |
| Visibility and busy behaviour | visibility, transparency, access role | Avoid treating opaque availability blocks or private events as known client conversations. Private-detail behaviour was not exercised in this sample. |

API mechanics and parameter restrictions: [events.list](https://developers.google.com/workspace/calendar/api/v3/reference/events/list). Preserve exact source times and IDs before transformation. Do not infer a reschedule from similar titles alone or assume a list response supplies a complete edit history.

## 5. Real examples and what they establish

| Example | Observed schedule | Feasibility implication |
| --- | --- | --- |
| Dogwood Reserve — Ads Strategy Call | 9 September, 09:15–10:00 America/Chicago | Historical client title, external invitees, WIA participants and conference metadata are readable. Several invitees are still needsAction; the record does not prove they attended. |
| Ridgefield — Monthly Strategy Call | 9 September historical entry; next sampled instance 11 November, 10:00–10:30 America/Chicago | Real next-call metadata can be matched against reviewed Ridgefield email aliases and existing Drive/Gmail context. The November entry includes both info@ and hello@ Ridgefield addresses. |
| Funktastic/DJ Hybrid Monthly Meeting | 21 October, 12:00–12:30 America/Chicago | Upcoming call combines two businesses. Use a shared engagement/multiple-client association rather than force it into one account. Description is empty; structured conference data is absent in the sampled copies. |
| The Brightside — Ads Strategy Call | 23 October, 10:00–11:00 America/Chicago | Title, external client email, Carmen/WIA participants and conference metadata support a real preparation candidate. Human hosting still needs an agreed mapping. |
| The Penny — Monthly Strategy Call | 10 November, 12:00–12:30 America/Chicago | `events@thepennyslo.com` is a useful cross-source candidate alongside the Gmail support-thread evidence. This is a proposed identity match, not an implemented client registry. |
| Google Ads Weekly Office Hours on Carmen's calendar | Repeated Thursday occurrences, including 22 October | The sampled occurrences list Carmen alone. A programme session exists, but its attendees do not enumerate programme members. |
| LeadLock office-hours invitations | Historical entries with WIA mailbox marked declined | These are not evidence of WIA attendance, client absence or a missed-session health signal. |

The same 21 October Funktastic event appears as **12:00 −05:00 on the primary calendar** and **13:00 −04:00 on Carmen's calendar**: both represent 17:00 UTC. Preserve recurrence timezone and calendar display timezone separately; compare instants, not displayed clock strings. November samples cross a daylight-saving change. The frontend's hardcoded IST labels must become explicit viewer-timezone rendering of the actual instant.

The September Dogwood event's organiser is the shared mailbox while Carmen is an attendee. The human `host` field requires a reviewed WIA staff/role mapping; organiser, creator and participant are distinct concepts.

## 6. Mapping to the current frontend

Reviewed files: `knowledge_base/wia-knowledge-base/frontend/src/types.ts`, `src/data.ts`, `src/views/CallPrep.tsx`, `src/views/ClientDetail.tsx` and the dashboard's scheduled-call use of `CALLS`.

| Frontend surface / field | Calendar support | Other dependency or required change |
| --- | --- | --- |
| Dashboard and Call Preparation queue: date/time/duration | **Directly supported** by real event times and scheduled lengths | Exclude cancelled and irrelevant events; distinguish ongoing, upcoming and all-day; use live dates and viewer timezone instead of the demo date and fixed IST. |
| `Call.id`, source reference | **Supported** by source keys and event URLs | Store calendar ID + event ID; reconcile cross-calendar copies and recurrence. Current call sourceIds should include Calendar evidence as well as supporting business context. |
| `Call.clientId` | **Conditionally supported** by titles and invitee emails | Reviewed client/alias/engagement registry, confidence and unresolved-match workflow. Support shared calls and programme sessions; no forced single-client match. |
| `Call.type` and `host` | **Partial** | Title-based type is a classification; human host needs staff/role rules and may be unknown or multiple people. |
| `objective`, `context`, `needs`, `agenda`, `opportunity` | **Calendar alone is insufficient** | Use explicitly supplied descriptions where present, plus cited Gmail/Slack/ClickUp/Drive/Fathom context. Upcoming client examples often have empty descriptions. Generated suggestions must be identified as suggestions. |
| Client Now / Meetings: next conversation | **Supported after matching** | Select the next relevant active occurrence, not the first unsorted mock call. A scheduled meeting should not appear as a recorded transcript. |
| Client history and evidence | **Supports schedule/invitation evidence** | Label scheduled/cancelled/RSVP separately from meeting-held, decisions, recording and delivery. An invitation timestamp is not client last-contact proof. |
| Attendance tab: attended/missed | **Insufficient** | RSVP is not join/attendance data. Use reconciled programme sheets and/or appropriate meeting-platform attendance. Carmen-only office hours cannot identify absent members. |
| Source connector count / all calls matched | **Requires implementation and reconciliation** | Current preview says six calls and all six matched. Those fictional numbers are not validated by real Calendar samples. Report actual scope, successful refresh, match quality and incomplete coverage. |
| Client health, sentiment, actions, invoices, ad results | **No direct determination** | Calendar can schedule a review; communication, task, finance and performance sources supply the business facts. |

The six frontend clients/calls are fictional fixtures. This test verifies that the **shape of scheduling data** is feasible; it does not find or validate those six fictional records in WIA's calendar. Do not replace mock values with unreviewed automatically matched events.

## 7. Proposed production retrieval and change handling

1. Keep a reviewed calendar registry with account, role, purpose and allowed client/programme scope. Exclude personal blocks, holidays, internal meetings and unrelated webinars from client-call preparation. Preserve unmatched candidates for review.
2. Read all pages required for the agreed window; retain source records and project relevant scheduled occurrences into the queue. Match known client/engagement email aliases with title context. Keep ambiguous and multi-client meetings explicit.
3. Normalize instants, all-day dates, recurrence/exception identity, cancellation and invitation state. Use `(calendar_id, event_id)` for source upserts and a separate reconciled meeting identity. iCalUID alone identifies a series across its occurrences, so it cannot deduplicate every occurrence into one meeting.
4. Assemble the brief from current, cited client evidence. An event change should invalidate or refresh time-sensitive preparation. Preserve unknown host, missing description and unavailable join-link states.

For POST-style delivery, Calendar supports HTTPS push watches. Watch each selected calendar's events separately; watch the user's calendar list if needed. Notifications carry headers rather than the changed event body, so retrieve changes after validating the channel. Persist channel/resource IDs and expiry, renew channels, deduplicate deliveries and reconcile periodically because notifications can be missed. **This is a proposed implementation, not a tested subscription.** [Google Calendar push guide](https://developers.google.com/workspace/calendar/api/guides/push).

Persist a compatible collection sync cursor only after pagination completes. Incremental requests must obey syncToken parameter restrictions; do not attach a cursor blindly to this probe's `orderBy`/moving-window query. Handle deletions and HTTP 410 by rebuilding the affected provider cache within the agreed scope. Keep historical KB evidence and audit history separate from that cache. Advancing the queue's time horizon also requires retrieving newly relevant future occurrences. **Incremental sync/recovery was not exercised.** [Sync guide](https://developers.google.com/workspace/calendar/api/guides/sync), [list restrictions](https://developers.google.com/workspace/calendar/api/v3/reference/events/list).

## 8. Open verification checks

| ID | Remaining check | Evidence needed |
| --- | --- | --- |
| GC-V-01 | Full calendar/client scope and coverage | Reviewed calendar registry, intended history window and exhausted relevant pages; access to additional calendars where required. Decide whether free/busy-only LeadLock access matters. |
| GC-V-02 | Client, programme and human-host mapping | Reviewed examples for single-client, shared Funktastic/DJ Hybrid, generic contact-name booking, unmatched prospect and staff-only programme session. |
| GC-V-03 | Lifecycle and scheduling correctness | Trace an actual reschedule/exception, cancellation and recovery; verify cross-calendar deduplication, DST, all-day and queue boundary handling. Existing cancelled/recurring records are observed, but no lifecycle mutation was tested. |
| GC-V-04 | Brief and source access | End-to-end source-cited brief for a real future client call, including missing context/host handling and citation/join-link access for intended WIA users. |
| GC-V-05 | Attendance semantics | Reconcile an actual programme participant/session against sheet/platform evidence; no inference from RSVP or omission. |
| GC-V-06 | Change delivery and recovery | Genuine HTTPS notification, validated/deduplicated processing, update/deletion retrieval, channel renewal, access loss and invalid-cursor recovery. |

## 9. Reproducible evidence

- [Initial disabled-API evidence](knowledge_base/wia-knowledge-base/verification/calendar/api_disabled_probe.json)
- [Calendar consent status](knowledge_base/wia-knowledge-base/verification/google/calendar_authorization_status.json)
- [Initial live probe](knowledge_base/wia-knowledge-base/verification/calendar/live_probe.json)
- [Upcoming/team follow-up](knowledge_base/wia-knowledge-base/verification/calendar/followup_probe.json)
- [Offline count audit](knowledge_base/wia-knowledge-base/verification/calendar/local_audit.json)
- [Initial probe script](knowledge_base/wia-knowledge-base/verification/calendar/verify_calendar.mjs), [follow-up script](knowledge_base/wia-knowledge-base/verification/calendar/verify_calendar_followup.mjs), [audit script](knowledge_base/wia-knowledge-base/verification/calendar/audit_calendar.py), [run instructions](knowledge_base/wia-knowledge-base/verification/calendar/README.md)

Reports retain real internal calendar metadata and limited event descriptions. Treat them as internal verification evidence; source access and safe display remain part of implementation. API/OAuth secrets are not included. No meeting was joined, no booking link was operated and no Google source data was modified.
