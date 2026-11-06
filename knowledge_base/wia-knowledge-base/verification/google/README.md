# Gmail and Google Drive verification setup

The user configured a Google Cloud OAuth client in `frontend/.env`. Required variables:
`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, and
`GOOGLE_REDIRECT_URI=http://localhost:8765/oauth/google/callback`.

Only these data-access scopes are requested:

```text
https://www.googleapis.com/auth/gmail.readonly
https://www.googleapis.com/auth/drive.readonly
```

The user chose Internal audience for WIA-only authorisation. This requires the Cloud project's parent organisation to match the authorising WIA accounts. Client configuration presence is not proof of a valid client or a user grant. Google account sign-in and consent must be completed interactively by the account owner.

## Local consent helper

```powershell
node knowledge_base/wia-knowledge-base/verification/google/authorize_google.mjs
```

Open `http://localhost:8765/` in a regular browser. The listener binds only to
`127.0.0.1:8765`, validates OAuth state, and uses PKCE and offline access. It never
prints an authorisation code, client secret or token. The process stops after one
hour unless stopped earlier. Each initiated consent session expires after ten minutes.

The callback saves tokens beneath `frontend/.data/knowledge-base-google/`, already
excluded by `frontend/.gitignore`. Tokens are not saved in verification reports or
frontend browser code. `authorization_status.json` contains only connection status,
scope names and credential-presence metadata. Do not commit local token files.

The callback is an OAuth return URL, not a Gmail or Drive webhook endpoint.

## Read-only probes after consent

```powershell
node knowledge_base/wia-knowledge-base/verification/google/verify_google_sources.mjs --gmail
node knowledge_base/wia-knowledge-base/verification/google/verify_google_sources.mjs --drive
```

To queue both probes while the account owner completes consent:

```powershell
node knowledge_base/wia-knowledge-base/verification/google/verify_google_sources.mjs --await-consent
```

This waits for the matching client grant for at most 30 minutes, then runs the
source reads without another confirmation. `source_test_status.json` records
waiting/running/report-written status without token values. A report-written state
is not a claim that every endpoint succeeded; inspect the individual reports.

Gmail checks the authenticated profile first. The expected mailbox is
`hello@weddingindustryads.com`, based on the agreed Dubsado notification route.
If a different mailbox is authorised, its identity is recorded but message bodies
are not read. Reconcile the intended mailbox before continuing that source.

For the expected mailbox, bounded queries inspect Dubsado-related candidates,
known-client and support-route references, at most eight messages, two thread
metadata examples, at most one small attachment, and a current history cursor.
Message reads do not mark messages read. Notification watches are not registered.

Drive checks user identity, bounded WIA/client-name and folder queries, two known
attendance spreadsheet references from the ClickUp audit, sample sheet metadata
and `A1:L12` from the first tab, at most one Google Doc plus plain-text export,
and the current changes cursor. A failed read remains recorded; no new file,
sharing permission or watch is created. Named-folder search is not full-text or
complete archive discovery. First-tab cells do not establish attendance definitions
or complete historical coverage.

Source reports are saved separately to `../gmail/live_probe.json` and
`../drive/live_probe.json`. Reports contain limited real source metadata/excerpts;
they are internal verification material, not production ingestion or a full backfill.
Token exchange/refresh POSTs only to Google's OAuth token endpoint; all source
requests use GET. No email is sent, file edited or notification subscription created.

## Completed verification on 19 October 2026

Consent succeeded for the intended WIA account. The initial probes plus
`verify_google_followup.mjs` performed 42 successful source GETs: 22 Gmail and
20 Drive/Docs/Sheets. `verify_refresh.mjs` separately verified an OAuth token-refresh
POST. `audit_google.py` produces offline per-source audits without token values.
Interpret results and outstanding checks in the root `gmail_scope.md` and
`google_drive_scope.md`; a successful HTTP response alone does not establish a
complete financial ledger, archive, attendance calculation or notification delivery.

## Notification implementation still pending

Calendar was subsequently authorised using the same client with two additional
read-only scopes; Gmail/Drive grants were retained. API enablement resolved its
initial disabled-service failure. See `../calendar/README.md` and the root
`google_calendar_scope.md` for 13 successful Calendar GETs and bounded scheduling
evidence. Calendar consent is recorded separately in
`calendar_authorization_status.json`. No Calendar notification watch was created.

Gmail will use a mailbox watch, a Pub/Sub topic and push subscription. Drive will
use a changes watch and an HTTPS receiver. Public receiving URLs, project/topic
configuration, expiry renewal, authentication, retry deduplication and actual
delivery remain separate implementation/test steps. An API token or successful
source GET alone does not validate webhook delivery.

References: [Google server-side OAuth](https://developers.google.com/identity/protocols/oauth2/web-server),
[Gmail push](https://developers.google.com/workspace/gmail/api/guides/push),
[Drive push](https://developers.google.com/workspace/drive/api/guides/push).
