# Google Drive intake scope — Maintained Client Knowledge Base

Review date: **19 October 2026 (IST)**. Required data → retrieval/access → live evidence → frontend mapping → unresolved checks. Related: [Gmail](gmail_scope.md), [ClickUp](clickup_scope.md), [Fathom](fathom_scope.md).

## 1. Feasibility verdict

**Read-only Drive, Google Docs and Google Sheets access works for `hello@weddingindustryads.com`. Real client questionnaires and a meeting summary support the frontend's client-background and preparation features. Both previously discovered attendance spreadsheets are readable, including dated attendance rows.**

The review made **20 successful Drive/Docs/Sheets GET requests**. It retained 86 unique file-metadata examples, read four Google Docs, verified one plain-text export, and read two attendance workbooks. This does not establish complete archive coverage, the current validity/approval of every document, or correct attendance calculations for every member.

**POST change notifications remain an implementation/test step.** No notification channel, file, permission or spreadsheet value was created or changed. The Knowledge Base frontend remains a fictional preview.

## 2. Authorisation and scope

User OAuth grants `drive.readonly` plus Gmail read-only access. `about.get` identifies Whitney Hodges / `hello@weddingindustryads.com`. API-only content reads through Docs and Sheets succeeded with the same Drive read-only grant; no document/spreadsheet write permission was needed.

Token exchange and offline refresh are shared with the [Gmail review](gmail_scope.md). A refresh operation was verified separately. Credentials/tokens stay in local ignored storage; source reports contain limited real file/cell/document excerpts and are internal verification artifacts.

The granted scope is broader than the intended ingestion boundary. Production intake must use reviewed client folders/files and programme sheets; readable internal hiring, marketing or unrelated files are not automatically KB inputs.

## 3. Live tests and coverage limits

Initial Drive run: **18:41:25–18:41:37 IST**, 15 GETs. Shared follow-up: **18:43:46–18:43:54 IST**, including five additional Drive/Docs/Sheets reads. All 20 returned HTTP 200.

| Check | GETs | Result |
| --- | ---: | --- |
| Drive user identity | 1 | Intended authorised account verified. |
| Two bounded file-name/folder-name searches | 2 | Known-client names and WIA folder candidates returned. Both searches have more pages; discovery is incomplete. |
| Children of Dogwood and Funktastic client folders | 2 | 14 and 15 direct children respectively; those two direct-child queries have no more pages. Descendants were not recursively exhausted. |
| Drive metadata for known attendance sheets | 2 | Both ClickUp-linked file IDs accessible. |
| Spreadsheet metadata | 2 | Both titles, America/Chicago timezone and Members/July/August/September/October tabs readable. |
| Members-tab sample cells | 2 | `Members!A1:L12` read from each workbook. |
| Google Docs content | 4 | Creative review document, Dogwood positioning questionnaire, Funktastic onboarding questionnaire, Ridgefield meeting summary. |
| Google Doc plain-text export | 1 | Export returned text; Docs structured extraction and export can have different formatting/text lengths. |
| Current Drive changes cursor/list | 2 | Start cursor obtained; current changes list empty with a new cursor. Actual change/POST notification not tested. |
| October session rows | 2 | `October!A1:L20` read from each workbook. |
| **Total** | **20** | **All HTTP 200.** |

The **86 metadata records** comprise 42 folders, 14 native Docs, 13 PDFs, six spreadsheets, four MP4s, four shortcuts and three SVGs. Those are unique returned examples, not all client documents or all relevant KB sources. Files discovered through several paths are deduplicated by file ID.

Queries used `trashed=false`, known-client/WIA name terms, 30-row result caps, explicit metadata fields and shared-drive-compatible options. `incompleteSearch=false` does **not** mean pagination was exhausted: both name searches returned a next-page token. No archive completeness claim is made.

## 4. Required data, retrieval and use cases

| Required input | Retrieval / fields | KB use and limits |
| --- | --- | --- |
| Stable file/folder identity and path context | Drive `files.list/get`: IDs, parents, names, MIME types, drive IDs | Registry of client folders/files and source identity. Names are neither unique nor immutable; moved files and multiple discovery paths must not create duplicates. |
| Source freshness and date context | Created/modified times; content/revision identity where available | Versioned facts and freshness. `modifiedTime` is not a meeting date, contract-signing date, client start date or proof of approval. |
| Document content | Docs `documents.get(includeTabsContent=true)`; Drive export when applicable | Onboarding answers, positioning, audience, voice, goals, meeting recaps and source-backed preparation. Preserve section/range/version citations, not only flattened text. |
| Spreadsheet content | Sheets metadata and values/ranges | Attendance/member/session facts, and other reviewed structured sources. A tab's grid row count is not a member count or a populated-record count. |
| File references and original URLs | `webViewLink`, file IDs, parent registry; links within content | Open source evidence and follow referenced material through authorised retrieval. URL presence does not establish that every KB user can open it. |
| Shortcuts | `shortcutDetails` → target ID/type/resource key | Resolve the target under its own permissions, preserve shortcut/target provenance and prevent duplicate intake. Target access was not followed in this test. |
| PDFs and recordings | MIME/size and content-download routes when needed | Questionnaire/contract/report parsing or recording/transcript backfill. Drive binary content download/parsing and playback were not tested here; metadata is not document/video content. |
| Change feed | `changes.getStartPageToken`, `changes.list`; later `changes.watch` | Incremental refresh, removals and moves. Persist feed scope/cursor; notification delivery is separate from reading the change endpoint. |

References: [file listing](https://developers.google.com/workspace/drive/api/reference/rest/v3/files/list), [Docs content](https://developers.google.com/workspace/docs/api/reference/rest/v1/documents/get), [Sheets values](https://developers.google.com/workspace/sheets/api/reference/rest/v4/spreadsheets.values/get).

## 5. Real documents and matching implications

### Client-background documents

- **Dogwood Reserve | Messaging & Positioning Questionnaire**, ID `1yvreO5aF_9GxjMaqK3lV7I7Zzn_qAE8EuDpVK_euk_Y`: structured text includes brand origin, mission, audience and practical needs. It discusses prior property/brand names Abbey Manor and Meriwether Manor before Dogwood Reserve. These are useful **alias/history candidates**, not automatic legal-entity or contract equivalence.
- **Funktastic Productions Onboarding Questionnaire**, ID `15AEPtpmLCnEKF9js_FfzDwBUESXB2n_mlIoiM9JXxcQ`: business/contact, advertising setup, services and messaging context are readable. It discusses Funktastic Productions and DJ Hybrid Chicago together. Preserve shared-engagement context while keeping the two businesses' source accounts and distinct metrics separate where appropriate.

These are the same kinds of information needed by the fictional client-profile cards. Extract relevant business/positioning sections with citations; do not indiscriminately expose login/credential prompts, tax details or other unnecessary questionnaire sections in a client brief. Full text was retrieved transiently, but only bounded excerpts were retained in test reports.

### Meeting and approval context

- **2026-09-09 - Strategy Call - Ridgefield - Summary**, ID `1Gzljjl89p9Hy5kfsO2Ll6Tc1mC3soX63L_iCW1whxR8`: recap and next-step sections describe website/LeadLock work, responsibilities, brochure changes and reporting preferences. This is **summary evidence**, not a word-for-word transcript or independent proof those tasks were completed. Its historical next-meeting statement is not the current calendar schedule.
- **Dogwood Reserve | Creative Asset Approval Form: Retargeting Ads**, ID `1mX0v3g6UD9sJJCf4l3ZjwjtJj-EQ1QY3iup0luQdv-4`: structured read and plain-text export succeed. The retained excerpt asks for review/approval. A document named Approval Form, instructional text or an editable checkbox does not by itself establish actual client approval or campaign launch.

### Archive and folder evidence

Dogwood folder `1y7kLUyf_sHBLY0YzNmeio3aSiynKGt9v` and Funktastic folder `17VGO8q-RBUpC0s-ZL2l19UX32eiP4cLV` have real questionnaires, resource/brand folders and call-recording containers. Returned metadata also includes Ridgefield/Funktastic/Dogwood recording and summary filenames and monthly-report PDFs.

This supports Drive as an archive/backfill source and verifies that recording/summary references exist. No video was played/downloaded, no recording was transcribed, and no complete transcript archive or Zoom/Fathom equivalence was established. Do not infer who recorded a video or whether its transcript exists from an MP4 filename alone.

The Dogwood folder also contains a contract filename using Meriwether Manor. The questionnaire's history makes alias review relevant; do not call it a misfiled contract or the same valid current agreement without inspecting/matching the actual agreement. Similarly, combined Funktastic/DJ Hybrid material needs reviewed business/engagement mapping.

Market Research Survey Submissions files were discovered. The Ridgefield meeting summary describes research questions for booked couples. These examples do **not** validate that WIA client-satisfaction surveys are stored here, nor that a venue's prospective-couple research is a WIA service-health survey.

## 6. Attendance: source verified, blanket automation not yet verified

The two sheet IDs found during the ClickUp review are confirmed:

| Workbook | File ID | Reads verified |
| --- | --- | --- |
| Google Ads Accelerator Roll Call | `1M6CU8SnDbz-Tw0ZDft31KHujYT_0VwaiIpAQNXAEKbU` | Metadata; Members sample; 12 dated October rows. |
| Meta Ads Accelerator Roll Call | `16XQJvz1GIgpJwjAagBaNXKAoJhtn1Bv1YoI1YjRepkE` | Metadata; Members sample; four dated October rows. |

Both use **America/Chicago**. The Members sample has Member, Email, Consecutive Misses, Last Attended, 2-week flag, 4-week flag and Notes. October rows have Date, Member, Email and Attended? with returned TRUE/FALSE values. Store booleans deliberately: the string `FALSE` must not become true through generic string truthiness.

This verifies a practical source for **sheet-reported attendance by person/programme/session**, rather than relying on Fathom invitees or a ClickUp Complete attendance task. Member emails support candidate identity matching, while programme ID is necessary because a person can occur in both workbooks with different attendance.

The sampled data exposes rules and exceptions the frontend must preserve:

- A Google Members row has an empty Last Attended and a high miss count, while its Notes report attendance on 15 October that is not yet logged pending an internal decision. The October sample lacks that attendee row. Do not let missing rows or stale aggregate cells silently override the exception, and do not silently rewrite the sheet from a note.
- Other notes distinguish an outreach email **drafted but not confirmed sent** from one explicitly reported sent, and reference a member on hold. FALSE flags are not sufficient evidence that no follow-up is due.
- Google session dates include **9 October**, with a note that the session moved from 8 October; do not assume a fixed weekly weekday. A member's tracking starts on that rescheduled session, so earlier gaps cannot be counted as missed sessions for them.
- Meta notes distinguish programme joining, a kickoff call, and the later start of miss counting. Historical rows before tracking begins cannot automatically be included in a current streak.
- The same person has different reported miss history across Google and Meta programmes. Never combine streaks merely because email matches.

No formulas, formatting/data validation, automated flag workflow, complete roster or all historical tabs were audited. The test sampled Members and October ranges only. The observed rows support **reported attendance entries**, not a finished reliable escalation calculation or a provider-verified join log. Resolve notes/holds/streak rules with the maintained programme process before auto-labelling disengagement or triggering outreach.

## 7. Frontend mapping

| Frontend area | Drive/Docs/Sheets can support | Additional requirements |
| --- | --- | --- |
| Client Profile: story, audience, differentiator, voice, goals | Readable onboarding/positioning questionnaire answers | Field-level section/version citations, approved/effective status, alias and client mapping. A document's modified date is not an engagement start date. |
| Source Library / evidence drawer | File identity, source link, title, excerpt and meaningful section | Preserve content snapshot/version and access provenance. Metadata authorship/last editor is not automatically author of every quoted answer. |
| Engagement history / Meetings | Meeting summaries, recording references and dated file-backed events | Separate recording, transcript, summary and derived decision; no recorded-video playback or full archive coverage tested. |
| Now / Handover / Call Prep | Positioning, meeting recap, open requests and known caveats | Join current meetings/tasks/email so an old summary does not become the current state. Generated agenda/opportunity/sentiment is an interpretation. |
| Commitments / Done / Verified | Explicit commitments or approval statements in a document, with provenance | A next-steps list or Approval Form title is not an acknowledged/completed/verified task. Reconcile with direct client replies and delivery evidence. |
| Accelerator Attendance | Actual readable per-session sheet entries, member emails and programme-specific context | Preserve holds, start dates, reschedules, missing rows and notes; validate streak/flag rules. No blanket attendance percentage or automatic outreach rule is yet verified. |
| Invoices & terms | Contract PDFs and document pointers where present | Drive contract file contents/signatures and financial status were not parsed. Gmail separately verifies Dubsado event notifications, not a complete balance ledger. |
| Lead outcomes / reporting | Report PDFs and research-sheet metadata can supply candidate references | Metadata is not live LeadLock results, ad spend or reproducible conversion metrics. Relevant report parsing/definitions and freshness need their own verification. |
| Health / coverage / Settings | Source availability, freshness, mapping/exception status and reported attendance context | Unknown/partial coverage must not become zero, poor health or a fabricated percentage. |

`data.ts` has **six fictional Drive evidence objects**, one profile/background source per mock client. Real questionnaires demonstrate that pattern's feasibility. It does not mean six real clients are fully mapped or that one file can supply every client fact forever. The mock Attendance tab hardcodes dates/Attended/Missed values; it needs to use reviewed sheet facts and exception states instead.

## 8. Planned notifications and change processing

The user requests changes to POST to the backend domain. Proposed standard Drive path uses **`changes.watch` → public HTTPS receiver**, with no Pub/Sub dependency for this path.

- Establish a scoped baseline/cursor and reviewed folder/file registry. Watch the appropriate user/shared-drive change feed and fetch changes after notifications; keep feed scope attached to the cursor.
- A notification is a change signal, not the document/cell payload. Validate registered channel identity/token/resource metadata, acknowledge accepted delivery and process changed files asynchronously. Persist retry/deduplication and content versions.
- Re-fetch Docs/Sheets content as appropriate and resolve relevant ancestry/shortcut membership before updating a client. A folder-resource watch is not a recursive watch of all descendant file content; use the change feed plus explicit scope filtering.
- Handle changes/removals, trash/moves, shortcuts and access loss without deleting historical evidence indiscriminately. Reconcile periodically because notifications are not an exhaustive activity audit log.
- Renew channels by replacing them before expiration, preserving overlap/deduplication. Google documents a maximum of one week for `changes` channels, one day for `files`, and a one-hour default if expiry is omitted. Use the returned expiration as authoritative.

No watch/channel or receiving endpoint was created here. The empty changes response proves API access/current cursor operation only; actual authenticated POST reception, expiry renewal and change-content reconciliation remain untested. [Official Drive push guidance](https://developers.google.com/workspace/drive/api/guides/push).

## 9. Remaining checks

- **D-V-01:** reviewed folder/file/engagement registry, historical pagination/descendants, shared-drive boundaries, alias changes and scope exclusions.
- **D-V-02:** reconcile questionnaire/background facts with current approved documents; implement field-level citations and content-version handling.
- **D-V-03:** attendance definitions, complete session/member history, notes-versus-counter conflicts, paused/start/rescheduled sessions and correct streak/flag meaning. Data access is verified; full automation semantics are not.
- **D-V-04:** relevant PDF/recording content download/parsing, source playback, shortcuts/target permissions and Zoom/Fathom/Drive duplicate reconciliation. Metadata references alone do not close this.
- **D-V-05:** source users' ability to open citations, access changes and appropriate handling of restricted/unrelated document sections.
- **D-V-06:** actual Drive notification delivery to the chosen backend domain, validation, renewal, deduplication, cursor recovery and end-to-end content update.

## 10. Evidence and reproduction

```powershell
node knowledge_base/wia-knowledge-base/verification/google/verify_google_sources.mjs --drive
node knowledge_base/wia-knowledge-base/verification/google/verify_google_followup.mjs
python knowledge_base/wia-knowledge-base/verification/google/audit_google.py
```

The shared follow-up also reads bounded Gmail samples. Node commands repeat remote reads and overwrite test reports; the audit is offline. Tests did not connect the frontend to live data.

- [Drive/Docs/Sheets initial report](knowledge_base/wia-knowledge-base/verification/drive/live_probe.json)
- [Shared documents/session/thread follow-up](knowledge_base/wia-knowledge-base/verification/google/followup_probe.json)
- [Drive audit](knowledge_base/wia-knowledge-base/verification/drive/local_audit.json)
- [Original ClickUp attendance pointers](knowledge_base/wia-knowledge-base/verification/clickup/local_audit.json)
- [OAuth refresh verification](knowledge_base/wia-knowledge-base/verification/google/refresh_probe.json) and [setup notes](knowledge_base/wia-knowledge-base/verification/google/README.md)
