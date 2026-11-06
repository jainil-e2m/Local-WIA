# ClickUp intake scope — Maintained Client Knowledge Base

Review date: **19 October 2026 (IST)**. This continues [Slack](slack_scope.md), [LeadLock](leadlock_scope.md) and [Fathom](fathom_scope.md): required data → retrieval/access → live records → frontend support → remaining checks.

## 1. Feasibility verdict

**The existing ClickUp key works and reaches the Wedding Industry Ads workspace. Task identity, hierarchy, statuses, assignees, due dates, descriptions, subtasks, role/phase fields and checklists are verified on live client/programme examples. These support task evidence, commitments, onboarding/work history and call preparation.**

The test made **50 GET requests, all HTTP 200**, sampling **338 unique tasks across five lists**. This is not a full workspace backfill or a count of active clients. Ownership/date completeness varies, shared programme lists require task-level client matching, and ClickUp completion cannot establish independent verification or client acknowledgement. Eight comment reads succeeded but returned no comments; comment content and threaded replies are not yet verified.

No task, comment, date, assignee, status, custom field, webhook or setting was created or changed. No frontend mock was replaced and no writeback integration was built.

**Subsequent Drive review:** Both attendance-sheet candidates below are now readable, including sampled Members and dated October rows. This closes uncertainty about sample sheet access, while tracking rules and notes/counter exceptions remain open. The ClickUp source-only results below describe what was observed during that earlier test. See [Google Drive scope](google_drive_scope.md).

## 2. Existing credential and live access

- `CLICKUP_TOKEN` and `CLICKUP_TEAM_ID` are present in `frontend/.env.local`. The test used that file, not a pasted key or a browser-exposed `VITE_` variable.
- Authentication is an `Authorization` header against `https://api.clickup.com/api/v2`. The script hardcodes GET requests. Successful reads do not mean the credential itself is restricted to read-only access.
- `GET /user` confirms the authenticated account is **E2M AI**, ID `87472224`.
- `GET /team` confirms authorised workspace **Wedding Industry Ads**, ID `9011165651`, with 12 returned member records. Member count is not a client count or a verified current WIA staff roster.
- `GET /team/{id}/space?archived=false` returns **10 spaces**. The hierarchy walk reads active folders and folderless lists for each, returning **75 folders and nine folderless lists**. These counts include template/internal/archive containers and are not engagement counts.

The spaces are Templates, ELEVATE Clients, Foolproof Follow-Up Advantage, Google Search Accelerator, ARCHIVES - Full Service, COMPLETED - VIP Days, Meta Ads Accelerator, VIP Days, WIA Internal and ONBOARDING CLIENTS. Containers labelled “ARCHIVES” can themselves be returned under `archived=false`; a name-based lifecycle review is still needed.

ClickUp documents personal tokens for testing and access according to the authenticating user's permissions. Production credential ownership and connection lifecycle remain implementation decisions. [Official authentication guidance](https://developer.clickup.com/docs/authentication).

## 3. What was actually tested

Initial run: **17:32:01–17:32:44 IST**, 37 successful GET requests. Dogwood/programme follow-up: **17:33:34–17:33:49 IST**, 13 successful GET requests.

| Resource / operation | Requests | Observation |
| --- | ---: | --- |
| User, authorised workspaces, workspace spaces | 3 | Identity and configured WIA workspace verified. |
| Active folders and folderless lists for 10 spaces | 20 | Current metadata and folder-to-list references obtained. |
| Custom-field definitions for five selected lists | 5 | Three management lists have no returned definitions; Dogwood onboarding lists expose Role, phase and Notes fields. |
| Task pages for five lists | 6 | Closed tasks, subtasks and tasks in multiple lists explicitly included. Dogwood Google + Meta required a second page. All five sampled list queries reached their page end. |
| Individual task details | 8 | Source URLs, statuses, assignees, dates and description structures confirmed. No attachments returned in these eight detail samples. |
| Task comments | 8 | HTTP 200 with empty comment arrays on all eight tasks. No reply request made because no parent comment was found. |
| **Total** | **50** | **50 HTTP 200; no scope/access denial or rate-limit response observed.** |

Tasks were requested with `subtasks=true`, `include_closed=true`, `include_timl=true` and `include_markdown_description=true`. The probe caps each list at two 100-task pages; all five fit within that cap. Workspace history, archived objects and every client list were not exhaustively fetched. [Task-list parameters](https://developer.clickup.com/reference/gettasks).

### Real list samples

Counts include parent tasks and subtasks; assignee/date columns count populated records, not unique people or obligations.

| Space / client | List ID and name | Tasks | With assignee | With due date |
| --- | --- | ---: | ---: | ---: |
| ELEVATE Clients / Ridgefield Weddings and Events | `901113863138` — Client Management | 48 | 42 | 34 |
| Google Search Accelerator / shared programme list | `901112432558` — Client Management | 42 | 41 | 41 |
| Meta Ads Accelerator / shared programme list | `901110927373` — Client Management | 59 | 34 | 24 |
| ONBOARDING CLIENTS / Dogwood Reserve | `901114402417` — Google + Meta Onboarding | 105 | 79 | 49 |
| ONBOARDING CLIENTS / Dogwood Reserve | `901113739151` — LeadLock Onboarding | 84 | 66 | 39 |
| **Sample total** | **Five lists; unique IDs deduplicated** | **338** | **262** | **187** |

Across the sample: **151 lack due dates**, **76 lack assignees**, **five have multiple assignees**, **149 are subtasks**, **122 have descriptions**, and **seven have checklists**. No populated dependency array or time estimate was observed; 120 tasks have positive tracked-time values. None of these measures establishes delivery quality or client satisfaction.

The older 8 September snapshots are historical references only. They listed nine spaces and three Ridgefield lists. Today only Ridgefield's management list was rediscovered among those three IDs; the old Google + Meta (`901113683038`) and LeadLock (`901113445424`) lists were not found in the active hierarchy. This test did not establish whether they moved, became archived/private, or were removed. Do not silently fill current gaps with the old snapshot or reuse a similarly named template instead.

Hierarchy `task_count` metadata is not equivalent to the expanded task count used here: Ridgefield reports five in hierarchy metadata but returns 48 with closed/subtasks included; Dogwood Google + Meta reports 28 but returns 105. Use explicit query/count definitions for coverage and progress calculations.

## 4. Required data, retrieval and use cases

| Input | How to get it | KB use / limitation |
| --- | --- | --- |
| Workspace/space/folder/list identity | `/team`; `/team/{id}/space`; `/space/{id}/folder`; `/space/{id}/list`; folder list references | Build an explicit engagement-source registry. Names such as “Client Management” repeat; use IDs and hierarchy, not the list name alone. |
| Stable task identity and source link | `/list/{id}/task`; `/task/{id}` → `id`, `custom_id`, `url`, location references | Evidence citation, updates, deduplication and drill-through. The eight detailed tasks have null `custom_id`; do not require a fictional `WIA-482`-style identifier. |
| Task title/description | `name`, Markdown/plain description fields | Explain work requested, blockers, deliverables and linked resources. Preserve authored instructions separately from a generated task summary. |
| Workflow state | `status.id`, `status.status`, `status.type`; date done/closed | Feed a reviewed task-state mapping. A terminal state is provider-reported completion, not client acceptance or KB Verified. |
| People and responsibility | `assignees[]`, creator, watchers; Role custom field | Named owner candidates and team/client responsibility hints. Creator and watcher are not owner; role is not a named assignee. Multiple owners need an array or an explicit accountable-owner rule. |
| Due/start/completion/update dates | Millisecond date fields, where available | Due/overdue views, chronology and freshness. Preserve raw values, date-only/time semantics and display timezone during implementation. A date's presence does not establish client agreement. |
| Subtasks / parent hierarchy | `parent`, parent lookup, optional subtask details | Carry client context into nested work without counting one obligation at every hierarchy level. Recurring work needs occurrence-specific IDs/state. |
| Role and onboarding phase | `/list/{id}/field` plus task `custom_fields` values | Client-side action candidates, onboarding phase context and responsible function. Decode values using field IDs/options; numeric zero is a valid populated dropdown value. |
| Checklists and resolved flags | Task checklist/item data | Partial delivery/progress evidence and follow-up questions. Checklist completion and parent task status can disagree. |
| Comments and replies | `/task/{id}/comment`; `/comment/{id}/reply` when a parent exists | Potential blockers, clarifications and explicit acknowledgements. Routes documented; only empty task-comment responses were observed here. |
| Attachments and linked resources | Individual task details, description links | Discover deliverable/document/recording references. Download access, actual document content and current validity must be verified through the relevant source. |
| Dependencies / task links | Task relationships in detail responses | Candidate blocked-by relationships if populated. No real dependency chain was returned in this sample. |
| Time tracked / estimates | Optional task fields | Optional operational context. Tracked minutes are not a client fee, an attendance record or proof of completion; no estimate field was populated. |

[Task details](https://developer.clickup.com/reference/gettask) and [custom-field definitions](https://developer.clickup.com/reference/getaccessiblecustomfields) are distinct reads. A missing applicable custom field must remain unknown; implementation must preserve task-type applicability where relevant rather than assume every field belongs on every task.

## 5. Important semantic findings

### Workflow status does not equal verified delivery

Observed labels are `complete` (136), `done` (156), `Closed` (13), `n/a` (12), `recurring` (8), `to do` (12) and `on hold` (1). Their workflow types also vary: notably **`n/a` is returned with type `done`**. Counting all done/closed types as delivered would misclassify the 12 not-applicable tasks.

Four tasks with terminal provider statuses still have unresolved checklist items: DNS Records (`868jhyutp`), Testing (`868jhyuj5`), Complete Client Setup (`868jhyuhf`) and Domains/URLs (`868jhyufu`). This is evidence for retaining both states and surfacing a review question, not automatic proof that current delivery is broken. Checklists may also be stale; independent verification remains necessary.

`recurring` is a custom workflow status, not a returned recurrence schedule or automatic evidence of lateness. For example, Ridgefield's Monthly Consulting Call (`868m4ycv2`) carries a 12 October date and Whitney as assignee. It is not proof that the call was missed; reconcile with the meeting/calendar sources and recurrence rules.

### Client role is useful but incomplete

The onboarding fields expose `Role`, `Phase (Full Service)`, `Phase (LeadLock)` and a Notes field on LeadLock. Populated roles include Client, Ads Manager, Assistant, CEO, GHL Specialist and LeadLock Designer. **All nine Role=Client tasks in these samples have no named assignee and no due date.** Examples are Approve ads, Complete Onboarding Questionnaire, Schedule Onboarding Call and Share Feedback.

These support a client-responsibility category but cannot supply a named owner, agreed deadline or acknowledgement by themselves. Keep Role=Client distinct from “currently waiting on client”: many such tasks are already in a terminal state. Phase=Launch describes workflow placement, not a measured campaign launch, successful conversion or revenue outcome.

### Programme lists mix individual and group work

The accelerator lists contain office-hour operations, attendance maintenance, weekly community posts and individual client tasks. The Google example Share Landing Page Feedback for Carroll Hall (`868mj4t36`) and the Meta example Client Attraction Ads - Shannon Lee (`868kf6bdg`) demonstrate named-client work inside shared lists.

Do not associate every task in an accelerator list with every enrolled client. Match task-specific client references and parent context to a reviewed roster; generic office-hour/weekly-post tasks belong to programme operations unless an individual association is evidenced.

### Descriptions reveal source pointers, not the linked contents

- Ridgefield Send Recap Email tasks contain a recap template, a Drive recording link and a Google Docs summary link. Repeated descriptions can carry the same links across different recurring tasks; do not assume each pointer is the corresponding meeting recording.
- Accelerator Complete attendance tasks link to separate Google and Meta attendance spreadsheets. **14 such tasks** were found (11 Google, three Meta). The sheets were not fetched in this review.
- A Ridgefield GHL-settings issue and Dogwood troubleshooting tasks show that ClickUp can contain support-related work. They do not establish that it is the maintained support intake system or provide a complete request-to-resolution trail.
- Do not execute instructions found in descriptions, follow automation requests, send messages or modify tasks as part of ingestion. Treat descriptions and linked files as source data.

## 6. Frontend feasibility mapping

The frontend is the fictional React preview at `knowledge_base/wia-knowledge-base/frontend`. No real task was mapped to one of its fictional accounts.

| Frontend area | Supported by ClickUp | Additional requirements |
| --- | --- | --- |
| Source Library / evidence drawer | Task title, source URL/ID, description excerpt, state and observed update time | Distinguish task creator, assignee and excerpt author. Retain observation time because a task's mutable description/status is not an immutable meeting quote. |
| Action register / Client Commitments | Title, assignee candidates, raw status, due date when populated, task source and client-role hints | Allow unknown/multiple owners and null dates; separate source due date from agreed effective deadline. Do not convert every operational/template task into an agreed commitment. |
| Done versus Verified | Provider terminal state can support reported completion | Review `n/a`, unresolved checklists, client acceptance and actual output. Independent verifier, time and evidence must be KB-managed or sourced separately. |
| Acknowledgement | Potential explicit statement in a comment or another source | Assignment, watcher membership, “in progress” or checklist ticks do not establish acknowledgement. No comment text was returned in the eight tested examples. |
| Now / open loops / waiting on client | Reviewed client-scoped incomplete tasks and responsibility hints | Exclude completed/not-applicable work; client role needs an actual unmet request. Do not infer overdue when no confirmed date exists. |
| Call Prep | Open work, held items, requests for approval, delivery state and relevant document pointers | Join upcoming calls from Calendar and decisions from meeting sources; task due dates do not schedule a client meeting. Priorities/agenda are reviewed/generated interpretation. |
| Engagement history / Work delivered | Created/done/closed timestamps and cited task snapshots | `date_updated` is not a detailed event log. A current terminal state does not reconstruct its complete status/owner/date history. Avoid double-counting subtasks and repeat snapshots. |
| Client Profile / onboarding | Reviewed client folder/list mapping, phase and scope-of-work context | Folders/space names do not authoritatively establish contract tier, start date or active engagement. A Dogwood name match to LeadLock is a mapping candidate, not a tested cross-system ID relationship. |
| Client Profile / support issues | Cited issue-related tasks and their reported state | Verify actual intake, request identity, unresolved status and resolution evidence before presenting a complete support ledger. |
| Accelerator Attendance | Candidate attendance-sheet references and attendance-maintenance tasks | Read the actual sheet, session roster/date and definitions during the Drive review. “Complete attendance” marked done does not mean a specific client attended. |
| Health, sentiment, weekly focus and coverage | Workflow delays and missing inputs can contribute evidence-backed operational signals | No satisfaction/sentiment/health score is supplied. Missing owners or stale tasks are data-quality findings before they are client-health conclusions. |
| Invoices & terms / lead outcomes | Task context only | Tracked time, task labels and LeadLock onboarding completion do not establish invoices paid, contract terms, inquiries won or ad performance. Preserve the Dubsado/Gmail and LeadLock plans. |
| Settings / connector coverage | Connection, returned hierarchy, list-page coverage and freshness | Five fully paged samples do not imply every client task was synced. Track scope, exclusions, list moves and permission changes explicitly. |

### Exact mock behaviour assessed

- [`data.ts`, line 19](knowledge_base/wia-knowledge-base/frontend/src/data.ts#L19) contains **one ClickUp evidence object**, `bloom-task`. It describes a fictional ClickUp due date of 12 October versus an explicit 8 October meeting commitment. ClickUp supplies its task date; the meeting supplies the alternate agreement. This test verifies the ClickUp half of the structure, **not a real reconciled deadline-conflict example**.
- [`data.ts`, line 82](knowledge_base/wia-knowledge-base/frontend/src/data.ts#L82) shows one record and “Review needed” for that sample conflict. These are preview assertions, not measured connector health.
- `types.ts` requires one owner, a date and WIA/Client side for every action. Real data requires unknown/multiple-owner and nullable-date states, plus raw versus resolved status/deadline fields.
- `Actions.tsx` allows owner/date/status changes, acknowledgement and Verify in browser-local state. Those controls are not ClickUp writes. API writeback is outside this review and needs an explicit later product decision.

## 7. Client mapping and source priority

1. Build reviewed ID mappings for workspace → space → folder/list → client engagement. Ridgefield folder `90117807231` and Dogwood folder `90117951715` provide concrete dedicated-client examples. Retain IDs through renames/moves and retain past relationships with dates.
2. Keep Templates, WIA Internal, archived/completed engagements and shared programme operations separate from active client obligations. Tasks copied from a template become evidence of client work only in the mapped engagement and appropriate state.
3. For shared accelerator lists, use explicit task/parent client context and a verified alias/contact registry. A person name alone may not identify a business. Keep ambiguous records unassigned for review.
4. Deduplicate by workspace/task ID, including tasks appearing in multiple lists. Preserve parent/list memberships and scope transitions rather than importing duplicates as separate promises.
5. Preserve ClickUp's raw due date and the independent agreed deadline. The user's meeting-commitment priority rule applies when evidence explicitly revises or establishes the obligation; ingestion time alone must not select a winner. Show both sources and the reason for a conflict resolution.
6. Match an extracted meeting/Slack commitment to an existing task by reviewed context before linking it. Similar titles can describe distinct recurrences or separate client requests. No real cross-source obligation matching was validated here.

## 8. Retrieval and refresh plan for implementation

This is a proposal based on verified reads, not a deployed connector.

- Bootstrap a reviewed hierarchy/engagement registry, then page tasks in included lists with explicit closed/subtask/multiple-list policies. Current samples establish one second-page example, not large-scale throughput or every permission path.
- Store source IDs, raw status/type, raw dates/time semantics, assignee IDs, role/phase values, parent/list relationships, source URL, observed time and content version/hash. Snapshot mutable facts so later displays can distinguish what was known at each time.
- Refresh changed tasks with a tested incremental strategy and overlap/deduplication. An update timestamp is not a complete audit trail; moves, deletions, lost access and changed list scope require reconciliation. No incremental-filter or deletion test was performed.
- Fetch comments when needed, following `start` and `start_id` together for older pages. Fetch replies separately while retaining the parent. Eight empty samples do not validate comment pagination or the semantics of approvals. [Comment reference](https://developer.clickup.com/reference/gettaskcomments), [threaded replies](https://developer.clickup.com/reference/getthreadedcomments).
- Fetch linked Drive/Docs/Sheets content through the authorised source connector during its own intake stage. A returned URL is a discovery pointer, not a successful content read. ClickUp notes that Docs attached to a task are not returned by the task-detail endpoint. [Task-detail limitations](https://developer.clickup.com/reference/gettask).
- Polling versus ClickUp webhooks can be selected during implementation. No ClickUp webhook was inspected or registered; do not infer a requirement from the separate Fathom webhook decision.
- Handle per-token rate-limit headers and HTTP 429 with backoff. This bounded probe had no 429s or retry exercise. [Official rate limits](https://developer.clickup.com/docs/rate-limits).

## 9. Open checks and evidence needed

| ID | Still open | Closure evidence |
| --- | --- | --- |
| C-V-01 | Full client scope and lifecycle mapping | Reviewed active-client/programme roster, source IDs, archive exclusions and treatment of the two old Ridgefield lists not rediscovered. Five samples are not the full client registry. |
| C-V-02 | Shared-list task mapping | Reconcile named accelerator tasks to actual client/contact records and keep programme-wide work separate. |
| C-V-03 | Workflow/recurrence meaning | Confirm mappings for recurring, on hold, done, complete, Closed and n/a; decide checklist conflicts and avoid counting not-applicable work as delivered. |
| C-V-04 | Acknowledgement, verification and date conflicts | A known real client task reconciled to meeting agreement, owner acknowledgement and delivery/acceptance evidence. No acknowledgement or Verified signal established by assignment alone. |
| C-V-05 | Comments and threads | A known populated task/comment/reply example, authorship and older-page read. All eight comment samples were empty; this is not a scope denial. |
| C-V-06 | Attendance sheets | Subsequent Drive reads verify both workbooks and sample dated attendance rows. Reconcile complete history, programme/identity mapping, hold/start/rescheduled dates and note-versus-counter conflicts before calculating streaks or treating every missing row as an absence. See [Drive scope](google_drive_scope.md). |
| C-V-07 | Linked documents / support route | Validate a corresponding recording/summary or actual deliverable, permissions and freshness; trace one support request to current resolution. |
| C-V-08 | Refresh and connector lifecycle | Demonstrate incremental updates, moved/deleted tasks, permission loss, deduplication and durable production credential ownership. Read-only testing does not establish writeback. |

## 10. Evidence and reproduction

```powershell
node knowledge_base/wia-knowledge-base/verification/clickup/verify_clickup.mjs
node knowledge_base/wia-knowledge-base/verification/clickup/verify_clickup.mjs --onboarding
python knowledge_base/wia-knowledge-base/verification/clickup/audit_clickup.py
```

The Node commands repeat remote reads and overwrite their respective reports; the audit is offline. Key values are not printed or written into reports. Reports contain limited real task metadata, excerpts and internal links and are internal verification artifacts.

- [GET-only probe](knowledge_base/wia-knowledge-base/verification/clickup/verify_clickup.mjs)
- [Initial live results](knowledge_base/wia-knowledge-base/verification/clickup/live_probe.json)
- [Dogwood/programme follow-up](knowledge_base/wia-knowledge-base/verification/clickup/onboarding_probe.json)
- [Offline audit](knowledge_base/wia-knowledge-base/verification/clickup/audit_clickup.py)
- [Counts, field completeness and attendance-sheet candidates](knowledge_base/wia-knowledge-base/verification/clickup/local_audit.json)
- Historical references: `.clickup-snapshot/clickup-client.json`, `clickup-templates.json` and `clickup-fields.json` are dated 8 September 2026; `clickup-descriptions.json` is dated 9 September. They were inspected locally but their older scripts were not rerun or their files overwritten.
