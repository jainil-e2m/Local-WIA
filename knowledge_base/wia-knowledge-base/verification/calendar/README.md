# Google Calendar source verification

Uses the existing WIA Google OAuth client and callback; no new client/key or `.env`
values are needed. Enable Google Calendar API (`calendar-json.googleapis.com`) in
the same Cloud project and add these scopes under Google Auth Platform Data Access:

```text
https://www.googleapis.com/auth/calendar.calendarlist.readonly
https://www.googleapis.com/auth/calendar.events.readonly
```

Retain Gmail/Drive scopes. Before the Calendar test, consent only granted those
earlier scopes; the account owner must consent again to add Calendar access. Refresh alone cannot
request new permissions. The local helper requests all four read-only scopes and
keeps Calendar consent status separate from the earlier authorisation report.

```powershell
node knowledge_base/wia-knowledge-base/verification/google/authorize_google.mjs --calendar
node knowledge_base/wia-knowledge-base/verification/calendar/verify_calendar.mjs --await-consent
```

If consent succeeds but Google reports the API is disabled in the OAuth client's
project, `--await-api` retries that specific API-enablement failure every 30 seconds
for at most 15 minutes. It does not enable APIs or change project settings:

```powershell
node knowledge_base/wia-knowledge-base/verification/calendar/verify_calendar.mjs --await-api
```

The first observed disabled-API response is preserved in `api_disabled_probe.json`.

Open `http://localhost:8765/` in a regular browser after saving project changes.
Sign in as `hello@weddingindustryads.com`. The probe waits at most 30 minutes for
the two Calendar scopes, then checks the primary-calendar identity, subscribed
calendar metadata and up to three selected calendars' bounded event windows.
It reads from 45 days before execution to 30 days after it, paginating at most
two 100-event pages per calendar. Relevant WIA/programme calendars are candidates;
this does not establish access to every employee's calendar or private event.

Samples retain source IDs, times/timezones, organisers, invitees/RSVPs, descriptions,
conference metadata, cancellation and recurrence references. RSVP is not attendance;
cancelled, declined, private, all-day and recurring events require separate handling.
Three event-detail reads and one recurring master are inspected when available.

No event, RSVP, calendar, ACL, email or notification channel is created/changed.
The initial report is `live_probe.json`. Pending consent or an empty event window
is not verified client-call coverage.

## Completed verification — 19 October 2026

Consent granted all four scopes. Calendar API enablement resolved the initial
`accessNotConfigured` failure. The initial run completed nine successful GETs after
three disabled-service retries. A targeted follow-up added four successful GETs:
131 primary-calendar future rows, 44 Carmen rows and 12 Jacqueline rows. All three
follow-up queries exhausted pagination in their bounded windows. The initial
primary historical query remains incomplete at 200 rows; Tina and Support returned
15 and 25 rows respectively with complete pagination in that window.

```powershell
node knowledge_base/wia-knowledge-base/verification/calendar/verify_calendar_followup.mjs
python knowledge_base/wia-knowledge-base/verification/calendar/audit_calendar.py
```

The follow-up uses calendar IDs from the successful initial report. Its report is
`followup_probe.json`; the offline audit is `local_audit.json`. Across both runs:
13 successful Calendar GETs, nine discovered calendars, five sampled event
calendars, 427 raw list rows and 425 unique calendar-event source records. Source
copies and recurring occurrences are not unique meeting/client counts. The first
standalone disabled-service attempt remains in `api_disabled_probe.json` and is
separate from the retry report's three earlier 403s.

Read the root [Calendar scope](../../../../google_calendar_scope.md) for field mapping,
real examples, frontend limitations and unresolved lifecycle/notification checks.
No Calendar watch was registered. The OAuth consent listener was stopped after
consent; localhost is not a deployed notification receiver.

References: [Calendar scopes](https://developers.google.com/workspace/calendar/api/auth),
[calendar list](https://developers.google.com/workspace/calendar/api/v3/reference/calendarList/list),
[events](https://developers.google.com/workspace/calendar/api/v3/reference/events/list).
