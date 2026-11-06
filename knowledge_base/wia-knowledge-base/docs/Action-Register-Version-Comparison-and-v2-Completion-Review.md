# Action Register: version comparison and v2 completion review

Review date: 29 October 2026.

Basis: the current source code, the Action Register tab scope, functional requirements FR-ACT-01–18, the content agenda, recorded KB decisions and the 22 September scoping call. This is a code and requirements review, not a live production acceptance test. No application behaviour has been changed.

## Recommendation

Proceed with **v2 · Teams** as the final interface. Retain its board/list views, responsibility buckets, account-team scope and deadline approval flow. Restore the operational visibility that v1 offered, and complete the shared workflows underneath it.

Revised and v2 are substantially the same workflow. V2's principal functional addition is account-team visibility. It does not add a new acknowledgement, verification, evidence or notification engine.

The required outcome is an accountable record of **what needs doing, who is responsible, when it is due, whether they accepted it, what is blocking it, and whether completion was checked where necessary**. The original business problem also includes unanswered Slack requests, old-task noise and continuity when people leave.

## Which version is which

| User-facing version | Route | Implementation |
|---|---|---|
| v1 / original | `#actions` | `frontend/src/views/Actions.tsx` |
| Revised | `#actions-v2` | `frontend/src/views/ActionsRevised.tsx` |
| v2 · Teams | `#actions-v3` | `frontend/src/views/ActionsTeams.tsx` |

The route names are easy to misread: the user-facing v2 is `actions-v3`. All three receive the same main action array from `App.tsx` and reuse the action drawer, Add action, Done and Verify dialogs. Review queues, resolved logs and programme-task changes are separate component-local state, so those parts are not fully shared or durable.

## Exact functional comparison

| Capability | v1 | Revised | v2 · Teams |
|---|---|---|---|
| Main organisation | Grouped list: Team, Client or Due date. Team grouping is offered to ops/admin viewers. | Four buckets: My pending, Team pending, Client pending, Completed. Board/list toggle. | Same buckets and board/list toggle. |
| Default scope | Managers start on their own actions; ops/admins start on all. An All clients option is available in the implementation. | Starts with all buckets across all clients. | Starts with all buckets within the viewer's permitted preview scope, rather than automatically selecting My pending. |
| Meaning of team | WIA work grouped by named owner. No account-team membership check. | Outstanding WIA actions not owned by the viewer, across the dataset. Unassigned work also lands here. | Same bucket classification, after restricting the dataset to account-team clients plus individually assigned actions. |
| Client visibility | My actions is an owner filter; Client grouping derives the viewer's clients from actions they own. All clients is unrestricted in this preview. | No account-team restriction. | Admins see every client. Other viewers see actions for their account-team clients plus actions assigned directly to them elsewhere. Client dropdown is restricted to account-team clients. |
| Programme visibility | Separate Programme ops tab; not mixed into the register's client-action tiles. | Programme tasks appear in My/Team pending or Completed and contribute to these global bucket counts. | Same integrated list, but programme tasks are limited to admins, the task owner or members of the sample programme team. |
| Main summary | Six clickable tiles: Overdue, Due this week, Awaiting acknowledgement, Waiting on client, Needs review, Awaiting verification. | Four bucket totals. Needs review is a separate admin-only pill. | Same as Revised, with scoped totals. |
| Filters actually present | Scope, grouping, open/snoozed/completed/all, text search, owner including Unassigned when All clients is selected. | Bucket, due today/tomorrow/next seven days/all time, text search, client. | Same as Revised; restricted client dropdown. |
| Overdue visibility | Dedicated tile and due-date group; dated rows show overdue state. | Individual late dates remain visible; no dedicated overdue view/filter. | Same as Revised. Selecting This week excludes already-overdue and undated items. |
| Row/card information | Actual progress status, origin/evidence shortcut, acknowledgement age, client waiting age, verification-needed and before-call flags, deadline conflict warning. | Priority, due/late date, owner/client and pending-date-request flag. Actual status/evidence details remain in the drawer. | Same as Revised. The list's Status column describes the responsibility bucket rather than Open/In progress/Blocked. |
| Acknowledgement | Owner-only Acknowledge control in drawer; unacknowledged work is prominent in rows and summary. | Drawer control retained; no main-list acknowledgement flag or queue. | Same as Revised. |
| Completion and verification | Shared Done/Verify dialogs and drawer controls, plus Awaiting verification tile and row-level Verify action. | Same dialogs and drawer controls. Done items needing verification already enter Completed; board card says Awaiting check, list says Completed. | Same as Revised. No reviewer assignment or dedicated reviewer work queue. |
| Deadline management | Drawer allows direct deadline changes/clearing; separate snooze control hides work temporarily. | Non-admins request a new date with a reason; admins approve/decline or directly edit. Snooze UI removed. | Same as Revised. |
| Review access | Needs review is visible to all preview users. Six sample review reasons and individual outcomes. | Admin-only Needs review combines the same triage cards with deadline requests. | Same as Revised. |
| Slack notification workflow | Preview composer from toolbar, group or action; client channels, WIA owner DMs and admin summary. It does not actually send. | No notification entry points wired. | No notification entry points wired, including the shared drawer. |
| Priority | Shared Add action dialog currently captures High/Medium/Low, but original rows do not display it. | Displays priority on open cards and in list. | Same as Revised. No dedicated priority edit/filter/sort. |
| Reopen | Checkbox and drawer support it in the current code. | Checkbox and drawer support it. | Same as Revised. It is not exclusive to the newer versions. |
| Sync presentation | Static per-source last-synced line. | Failure/success pill with source details and Sync all now. Retry is simulated. | Same user-facing behaviour. Retry is simulated. |
| Evidence, notes and history | Shared drawer. | Same shared drawer. | Same shared drawer. |

The board is an alternative display with completion controls; there is no implemented drag-and-drop workflow for moving cards between buckets.

## What v2 has retained

V2 still provides the origin quote and source/ClickUp link when present, deadline conflict text, owner changes, acknowledgement, block/unblock, Done, Verify, reopen, internal notes, history and next-call navigation. These functions should not be described as entirely removed: most are less visible because they require opening the drawer.

The deliberate changes worth keeping are account-team scope, board/list views, integrated but identifiable programme work, admin-only triage and approval-based deadline changes.

## Required product additions and corrections

### 1. Restore an attention layer

Keep the four main bucket cards and add compact filters with counts for Overdue, Not acknowledged, Blocked, Awaiting verification and Unassigned. Keep undated work discoverable. Restore small row/card indicators for actual progress, acknowledgement age, client waiting age and material deadline conflicts.

An owner filter is needed for ops to inspect one person's workload and handover items. Add progress and priority filters; source/service filters can live under More filters. Counts should use the same scope and active filters as the results, across the entire result set rather than only five preview cards or one loaded page.

The old removed No owner/no date summary tile does not need to return: visible labels and useful filters cover the need. Before-next-call flags are useful once Calendar matching is ready; full Call Preparation remains Stage 2.

### 2. Make verification a visible, assigned step

For flagged action types, distinguish **Reported done — awaiting verification** from **Verified**. An unflagged action may close at Done. Add a reviewer, a review queue and a recorded outcome with check evidence. The four-bucket design can remain if Completed is clearly split into Awaiting check and Closed, with separate counts; alternatively, keep awaiting-check work outside the final completion total.

The current board places both states in Completed. The list masks the distinction entirely. Decide who reviews, whether reviewers receive a personal work item, which types require it and what self-verification grants apply.

Implementation corrections: the Verify dialog renders an evidence-link input but never reads or saves it. `canVerify` allows any non-owner through its preview rule rather than checking a configured verification grant. Mark done does not set `completedOn`. Reopening clears the active verification object; production must preserve the complete prior verification, including its evidence, as superseded history.

### 3. Define responsibility separately from the person being waited on

The present bucket expression checks completion, then `side === 'Client'`, then owner. A WIA action marked Blocked remains My/Team pending even when the blocker is a client. A client-side action can name a WIA owner but will still enter Client pending. Unassigned WIA items enter Team pending.

Keep separate fields for WIA accountability, client contact, action side and current dependency/next move. Example: Carmen still owns delivery of a landing page while waiting on Sarah for images. Record what Sarah owes, who will chase it and how receipt returns work to Carmen. Do not lose accountability when the next move changes.

Add a deliberate resolution for unassigned work. The shared Add action owner dropdown currently offers only WIA team members, even when Client is selected; it needs an appropriate client-contact selector or an explicit unknown contact. Document how third parties are handled if that scope is retained.

### 4. Make acknowledgement useful in daily work

Retain the owner's Acknowledge control and reset acknowledgement when the owner changes. Expose new/unacknowledged work on the board/list and provide the owner a simple acceptance path. Store actor, timestamp, method and supporting source evidence. Define the business-day threshold and escalation recipient.

Explicit owner replies and configured reactions need ingestion/reconciliation support. Reaction acknowledgement stays disabled until the approved emoji-to-meaning mappings are supplied. Assignment or simply reading an action must not acknowledge it.

### 5. Finish durable triage, evidence and duplicate handling

Keep stale, ambiguous and AI-proposed work separate from confirmed obligations. The tab scope selects a 30-day inactivity threshold for old conversational imports; this is a triage rule, not a cutoff on the historical data to ingest. Reconcile later delivery/closure before deciding an old ask is current.

Required additions: bulk triage for initial backfill, material date-conflict resolution, supporting evidence over time, real duplicate merging, and durable accept/dismiss/resolution history. A dismissed item must stay dismissed across navigation, refresh and re-extraction unless new material evidence warrants a new review.

Current limitations are shared by the versions: review items/resolved outcomes are component-local; revisiting the view restores the sample queue. Merge into existing records an outcome message without updating the target action's evidence. Accepted review items receive an empty source ID. Programme-task status changes are also component-local.

### 6. Complete account-team scope and operation permissions

Use WIA's approved current account assignments and stable user identities. Preview names and historically observed ClickUp assignees are insufficient as the production access model. The snapshot exporter currently derives the client team from assignees on the client's ingested ClickUp tasks, including historical tasks.

Apply effective client/module/operation permissions to lists, drawers, add/edit/verify commands, global search, notifications, evidence, client records and APIs. V2 currently filters its own list, while global search and overdue notifications inspect the full shared array and Add action offers all clients.

Also fix two scope edge cases: a directly assigned action outside an account team is visible but its client is absent from the dropdown; client/date/search filters can remain set when the preview user changes, leaving an apparently empty view. Set the intended manager/admin defaults explicitly. Configure reassignment when membership or employment changes; the previously removed bulk Reassign all panel is not required to return.

### 7. Make programme and completion counts unambiguous

Integrated programme work can remain in the same board. Offer an easy programme/client-work filter and distinguish total personal workload from client-obligation totals. Revised/v2 currently add programme tasks into the four global totals; do not label those as client-only metrics. Keep programme work out of client portfolio action totals.

For recurring work, complete a dated occurrence and schedule the next occurrence rather than permanently closing a repeating responsibility. Recurring tasks should not become misleading overdue items. For Completed, use completion/verification time for history filtering and ordering; the current implementation filters and sorts completed work by its due date.

### 8. Decide the follow-up capability and priority rules

If v2 is meant to replace Viktor's daily open-loop workflow, capture explicit unanswered requests to team members and Whitney, with request age, responsible person, source thread and reply/delivery state. An unanswered request is distinct from an unacknowledged assigned task. Silence alone should not manufacture a new commitment or deadline.

Bring the v1 Slack composer into v2 if notifications are selected for release 1. Preserve reviewed message text, intended recipients, per-client isolation, channel audience rules, send results and history. The agreed baseline still defers external notifications; the later tab scope proposes moving Slack sending into release 1 (D8). Therefore this is a scope decision, not an already approved mandatory sending capability. A usable on-screen attention queue does not require automated messages. Scheduled digests and client-chase drafts can follow later.

Define High/Medium/Low and who may change priority; add audited editing and useful filtering/sorting. Current priority is mainly a display label with a shared creation input and a Medium fallback for records without a value. Do not imply imported Medium values were chosen by WIA.

## Production completion is a separate requirement

The source-intake backend exists; these frontend workflows are not a completed multi-user action service. Main action changes persist in browser local storage. There is a local real-data snapshot path, but its action export creates ClickUp actions only; conversational action extraction is explicitly not built in that path. It also sets `verifyRequired` false for every exported task.

To launch v2 for the stated agenda, connect shared persistent actions and audited commands to the maintained data, reconcile ClickUp and explicit Slack/Gmail/meeting obligations into canonical records, and preserve reviewed corrections through source refreshes. Implement source-driven completion/reopening and dependable refresh of client counts and dependent views. Complete available approved history for launch clients, with disclosed coverage gaps, rather than treating a bounded test snapshot as full backfill.

Replace the simulated sync retry with actual job/results status and last-successful timestamps. Keep last-known actions visible with a source limitation on failure. Support agreed date-only, exact-time and unknown deadlines with WIA's operating timezone; the current action type and preview helper use a date string and a snapshot reference day.

Route the bell's deadline requests to the final v2 review panel. It currently opens Revised (`actions-v2/review`); Open the action register in Notifications opens v1. Retire the duplicate sidebar entries when the final view ships. Reuse the same action commands in Client Portfolio commitments: the shared row component currently has direct Done/Verified fallbacks when no dialog callbacks are supplied, which must not bypass completion/evidence/permission rules.

## Decisions to settle without reopening the layout choice

The user's preferred layout is v2 · Teams. Remaining definitions are:

1. Approved account-team roster and the exact individually-assigned-outside-team access exception.
2. Separate accountable owner, waiting-on contact and next-move rules; handling of unassigned/client-delivered items.
3. Reviewer assignment, flagged types, self-verification permissions and whether awaiting-check items count as completed.
4. Acknowledgement business-day grace, escalation recipient and optional reaction mapping.
5. Priority definitions and editing rights.
6. Manual-action acceptance, cancellation/replacement, exact-time deadlines and material-change acknowledgement rules.
7. Whether Slack sending is in release 1 or remains deferred; programme/client channel audiences and routing.

These are contracts for the chosen v2, not reasons to restart the interface design.

## Acceptance examples for a final v2

1. One obligation mentioned in a call, Slack and ClickUp appears once with all supporting evidence and the accepted deadline; conflicting dates remain explainable.
2. An old ask with no recent activity goes to review; later delivery is reconciled. Dismissal and duplicate merges survive reload and the next extraction.
3. A new owner must acknowledge; the prior owner's acknowledgement never carries over. Unowned and undated items remain discoverable.
4. A flagged task marked Done reaches its assigned reviewer and remains visibly unverified. Verification stores check evidence and checks effective permission.
5. A genuinely reopened ClickUp task becomes open and supersedes its previous verification; later Done does not restore that verification.
6. A WIA task waiting on client input retains its WIA owner; receipt of the input is recorded and returns the next step to WIA.
7. A pending deadline-change request leaves the current deadline and overdue calculation intact until approved; the outcome is auditable and visible to the requester.
8. Account-team scope and configured operation rights hold through search, notifications, direct links, evidence and client records, including an explicit test of the direct-assignment exception.
9. No-date work is never overdue; date-only and exact-time deadlines use their appropriate clocks. Today/This week do not become the only way to discover older overdue work.
10. Programme work is identifiable and does not inflate a client's obligation count; recurring occurrences and completion histories remain meaningful.
11. A failed source does not erase actions or advance its success timestamp. Real last-successful status replaces the mock sync timer.
12. The register, client commitments and notifications open the same v2 records and enforce the same lifecycle. Changes made by one authorised user persist for another.

## Evidence map

- `kb_tab_scope/01-action-register.md`: purpose, user jobs, inclusion rules, D1–D17, proposed Slack scope and mock coverage.
- `docs/functional_requirements.md`: FR-COM-01–10, FR-ACT-01–18, canonical client commitments and review/admin requirements.
- `frontend/docs/content-agenda.md`: business agenda, source/evidence rules and scope boundaries.
- `frontend/src/views/Actions.tsx`: v1 screen and shared drawer/dialog/review/Slack implementations.
- `frontend/src/views/ActionsRevised.tsx`: Revised screen and filtering/bucket rules.
- `frontend/src/views/ActionsTeams.tsx`: v2 account-team and programme visibility additions.
- `frontend/src/teams.ts` and `frontend/src/records.ts`: sample team membership.
- `frontend/src/App.tsx`: shared action storage, global search and notification navigation.
- `frontend/src/data.ts` and `frontend/src/types.ts`: status, date helpers and available action fields.
- `backend/README.md`: existing source-intake slice.
- `backend/scripts/export_frontend_snapshot.py`: ClickUp-only action export, verification default and observed-assignee team derivation.
- `../../../knowledgebase_changes.md`: KB-CH-11–13, 18, 29, 38, 52–54, 65, 67 and 69.
- `../../../WIA_Meeting_Analysis/meetings/2026-09-22_knowledge-base-scoping/source.md`: open-loop scanning and noisy old-task digest problem at 31:41–33:34.
