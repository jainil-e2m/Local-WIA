# Content Atelier — Frontend Product and UI Specification

<!-- governing-plan-note -->
> **Target state, amended (18 October 2026, plan item S.B9).** Read this together with [the implementation plan](../backend/docs/Content-Atelier-Implementation-Plan-Brief-Generation.md), whose rulings (section 4.2, Appendix E) amend it. Where they differ, the plan wins.

**Document status:** Target product specification for design and frontend implementation  
**Audience:** Product designers, frontend engineers, backend engineers, QA engineers, and coding agents  
**Last updated:** 1 October 2026  
**Primary reference:** [`implementation_plan_v1.md`](implementation_plan_v1.md)  
**Current backend reference:** [`content_atelier/execution_flowchart_v2.md`](content_atelier/execution_flowchart_v2.md)  
**Pitch reference:** `Content-Atelier-Pitch.html (outside the repository)`

---

## 1. Purpose of this document

This document defines the complete intended frontend experience for the Content Atelier. It explains:

- What users see and interact with.
- What processing remains behind the scenes.
- What the UI shows while backend jobs are running.
- How the weekly content bucket progresses into ideas, research, briefs, generated assets, and final approval.
- How permissions, revisions, failures, degraded states, and concurrent edits behave.
- Which frontend routes, components, data contracts, and acceptance criteria implementation agents should follow.

This is an implementation-ready product specification, not a pixel-perfect final design. Agents may refine layout and visual details, but they must preserve the workflow, evidence rules, human approval gates, revision behavior, and frontend/backend boundaries described here.

The Content Atelier is a human-in-the-loop editorial system. It is not an autonomous publishing system.

---

## 2. Product outcome

The primary experience is a live weekly workspace in which source material accumulates throughout the week. At the weekly cutoff, the system automatically—or manually during early calibration—closes the bucket, finds the strongest key moments, and produces a small set of content angles for Whitney.

Whitney selects and edits the angles she wants. The backend researches each confirmed angle and produces a one-page brief for each. Whitney edits or approves those briefs. The backend then generates the weekly content pack. Whitney reviews, edits, acknowledges warnings, and gives final approval.

The intended rhythm is:

```text
Weekly Bucket
→ Notice / Key Moments
→ Angle Review
→ Research
→ Brief Review
→ Pack Generation
→ Pack Review and Sign-off
→ Approved-ready in-app content
```

The user should always understand:

1. What phase the current week is in.
2. What the system is doing now.
3. Whether anything needs human input.
4. What evidence supports an angle or claim.
5. What revision is being edited or approved.
6. What happens after the next action.

---

## 3. Product principles and non-negotiable rules

### 3.1 Human decisions stay visible

The frontend must make all three approval gates explicit:

- **Gate 1:** Whitney selects or passes content angles and chooses the CTA.
- **Gate 2:** Whitney approves the exact revision of each content brief.
- **Gate 3:** Whitney approves the exact revision of the completed content pack.

No gate may be approved invisibly or by a backend model.

### 3.2 Evidence is inspectable

Every important idea, brief claim, quote, and figure must retain a visible path back to its source. The UI should show understandable provenance: meeting, speaker, date, timestamp, Slack permalink, and proof status.

### 3.3 Progress is truthful

Do not show invented percentages or fabricated time estimates. Show actual completed units, named processing stages, and honest degraded states.

### 3.4 The app is resumable

Backend work continues when users leave the page. Refreshing, closing, or returning from a Slack deep link must recover the current server-confirmed state.

### 3.5 Nothing publishes automatically

Final approval produces an immutable in-app `approved_ready` pack. It does not automatically create a GHL draft, Google Drive document, Canva asset, email send, Slack handoff, or social-media post.

### 3.6 External research is context, not client proof

External search findings can inform audience language, framing, hooks, and questions. They cannot substantiate a WIA or client result.

### 3.7 Secrets and model internals never reach the browser

The browser must not receive API credentials, OAuth tokens, raw system prompts, model chain-of-thought, embedding vectors, database identifiers that have no product meaning, internal queue IDs, or provider billing details.

### 3.8 Strong work is not padded

The desired weekly experience ordinarily presents three to four content angles. The backend may validly return zero to five. The UI must never manufacture weak angles merely to fill the layout.

---

## 4. Roles and permissions

### 4.1 Whitney — sole approver

Whitney can:

- Inspect all visible workflow and source information.
- Edit angle titles and add steering direction.
- Choose the CTA at Gate 1.
- Approve, pass, save, or request another look for an angle.
- Edit and approve briefs.
- Edit generated assets.
- Acknowledge non-blocking warnings.
- Approve the final content pack.

Only Whitney can complete Gates 1, 2, and 3.

### 4.2 Team editor

An authenticated team editor can:

- Inspect weekly buckets, sources, moments, ideas, research, briefs, and packs.
- Create a digest preview during the calibration phase.
- Edit unapproved briefs and assets where product policy permits.
- Run checks.
- Prepare work for Whitney.

A team editor cannot approve any gate. Approval controls must either be hidden or visibly disabled with an explanation such as `Only Whitney can approve this step.`

### 4.3 Read-only team member

A read-only user can inspect permitted content but cannot modify, trigger expensive processing, notify Slack, edit, or approve.

### 4.4 Backend services

Backend workers may ingest, extract, cluster, research, generate, check, repair, and notify. They may not impersonate an approving user.

---

## 5. Core product entities

Frontend agents should use these terms consistently.

| Entity | Product meaning |
|---|---|
| **Weekly cycle** | One Monday-to-Friday content-production period and its workflow state. |
| **Bucket item** | A meeting, Slack signal, or manually supplied source included in the weekly cycle. |
| **Source segment** | Stable timestamped text used to verify a quote or moment. |
| **Moment** | A verified result, question, praise item, story, objection, teaching point, milestone, or soundbite. |
| **Idea / content angle** | A general principle supported by one or more moments and presented for Gate 1. |
| **Research packet** | Internal evidence plus optional external framing gathered after Gate 1. |
| **Brief** | A versioned one-page editorial plan for an approved angle. |
| **Pack plan** | The assignment of approved briefs/angles to the weekly asset slots. |
| **Content pack** | The complete set of weekly assets generated from approved brief revisions. |
| **Asset** | Email, carousel, reel script, or associated caption within a pack. |
| **Check result** | Factual, structural, voice, or overlap validation for a specific asset revision. |
| **Gate decision** | An append-only approval, pass, request-change, or acknowledgement event. |
| **Revision** | An immutable saved version of an idea, brief, asset, or pack snapshot. |

### 5.1 Required backend extension for the envisioned weekly UX

The existing v2 plan is predominantly shaped as `idea → brief → pack`. The target weekly UI allows Whitney to approve multiple angles and then generate one weekly pack across those approved briefs.

The backend therefore needs explicit weekly coordination entities, for example:

- `weekly_cycle`
- `weekly_bucket_item`
- `weekly_cycle_idea`
- `pack_plan`
- `pack_plan_assignment`

Each asset slot in the weekly pack must reference the exact approved brief revision that governs it. The frontend must not simulate this relationship only in local state.

---

## 6. Frontend information architecture

The Content Atelier should expose four persistent top-level areas.

### 6.1 Weekly Workspace

The operational home for the current cycle:

- Weekly Bucket
- Notice / Key Moments processing
- Angle Review
- Research status
- Brief Review
- Pack Generation
- Pack Review and Sign-off

### 6.2 Moments

A searchable, auditable Moments Ledger containing sources, proof, consent, attribution, labels, lifecycle, and usage history.

### 6.3 Ideas and History

Historical weekly digests, generated angles, passed/set-aside ideas, scores, reasons, approvals, and lineage into briefs and packs.

### 6.4 Library and Sources

- Brand and voice guide
- Published precedent
- CTA catalog
- Offers
- Consent register
- Source connections and coverage
- Ingestion health
- Job failures requiring operator attention

### 6.5 Suggested routes

```text
/content-atelier
/content-atelier/weeks/:weekId
/content-atelier/weeks/:weekId/angles
/content-atelier/ideas/:ideaId
/content-atelier/ideas/:ideaId/research
/content-atelier/briefs/:briefId
/content-atelier/packs/:packId
/content-atelier/assets/:assetId
/content-atelier/moments
/content-atelier/moments/:momentId
/content-atelier/ideas
/content-atelier/sources
/content-atelier/library
```

Every idea, brief, pack, asset, and moment must have a refresh-safe deep link. Slack notifications must open the correct entity and gate after authentication.

---

## 7. Global application shell

The shell should remain consistent across all phases.

### 7.1 Header

Show:

- Content Atelier name and mark
- Current weekly cycle selector
- Current workflow phase
- User identity/role
- Notification indicator
- Link to source health when degraded

### 7.2 Weekly phase tracker

Display the workflow persistently:

```text
Bucket → Notice → Angles → Research → Briefs → Generate → Review
```

Each phase has one of these states:

- `Complete`
- `Active`
- `Waiting for Whitney`
- `Waiting for team`
- `Processing`
- `Degraded`
- `Failed`
- `Not started`
- `Stale`

Color may reinforce status but must never be the only signal. Include a text label or icon with an accessible name.

### 7.3 Current action banner

When human action is required, show one concise action banner at the top of the active workspace:

```text
3 content angles are ready for your review.
[Review angles]
```

Processing should use a different pattern:

```text
Researching 2 approved angles. You can leave this page.
```

### 7.4 No duplicate sources of truth

The shell may summarize counts, but detailed status must come from the same backend state used by the workspace. Do not maintain separate fixture-derived or local-only counts.

---

## 8. Weekly lifecycle and state machine

### 8.1 Target lifecycle

```text
collecting
→ closing
→ extracting_moments
→ clustering_ideas
→ angles_ready
→ awaiting_angle_decisions
→ researching
→ briefs_ready
→ awaiting_brief_approvals
→ planning_pack
→ generating_assets
→ checking_assets
→ pack_ready
→ awaiting_final_approval
→ approved_ready
```

Exceptional states may include:

```text
degraded
failed
paused_for_spend_limit
stale
cancelled
archived
```

### 8.2 Calibration-mode difference

The target product supports an automatic weekly cutoff. The current backend plan deliberately keeps digest creation manual until ranking is trusted.

The frontend must support both modes without redesign:

- **Calibration mode:** an authorized team editor clicks `Close bucket and prepare angles`.
- **Scheduled mode:** the system closes the bucket automatically at the configured business cutoff.

The UI should clearly label which mode is active. Do not imply that a scheduler exists before it is actually enabled.

---

## 9. Phase 1 — Weekly Content Bucket

### 9.1 Purpose

Give the team a truthful, calm view of source material accumulating during the week.

### 9.2 Primary layout

The workspace contains:

1. Week title and date range.
2. Bucket state and next transition.
3. A visual bucket/fill meter.
4. Monday-to-Friday source timeline.
5. Recent source items.
6. Moment summary.
7. Source-health exceptions.

### 9.3 Bucket visualization

The bucket may be represented as a vessel, stacked material, or progressive container, but its fill must be based on actual source processing.

Recommended calculation:

```text
processed eligible bucket items / known eligible bucket items
```

If the denominator is not knowable because new meetings can still arrive, show counts and elapsed weekdays rather than a misleading completion percentage.

Good:

```text
7 meetings processed · 2 processing · Thursday of 5 workdays
```

Avoid:

```text
73% complete
```

unless the backend can prove what the total is.

### 9.4 Daily timeline

For each day, show:

- Meeting count
- Slack signals captured
- Processed count
- Current failures
- Empty-day state

Selecting a day reveals its bucket items.

### 9.5 Bucket-item card

Each item should show:

- Source icon and source name
- Meeting/message title
- Occurrence date and duration
- Participants when permitted
- Inclusion state
- Processing state
- Number of verified moments captured
- Source-detail action

User-facing states:

- `Waiting for transcript`
- `Received`
- `Classifying`
- `Reading conversation`
- `Moments captured`
- `Skipped — internal meeting`
- `Skipped — duplicate`
- `Needs attention`

### 9.6 Frontend responsibilities

- Render cycle and source-item status.
- Provide filters by day, source, and status.
- Keep server status fresh through polling or event updates.
- Link to source and moment details.
- Allow authorized users to close the bucket in calibration mode.
- Explain what will happen at cutoff.

### 9.7 Backend responsibilities

- Receive Fathom webhooks and reconciliation results.
- Import historical Zoom material only where applicable.
- Poll approved Slack channels.
- Accept permitted manual sources.
- Persist raw source bodies.
- Normalize calls and transcript segments.
- Classify internal/client/workshop/fragment material.
- Deduplicate source overlap.
- Extract and verify candidate moments.
- Promote canonical moments into the ledger.
- Associate eligible material with the weekly cycle.

### 9.8 Processing experience

The bucket remains usable while ingestion runs. Individual cards update independently. Do not block the full workspace because one call is waiting for a transcript.

If a source is degraded, show a scoped banner:

```text
Fathom reconciliation is delayed. 8 meetings are current; up to 2 may still arrive.
[View source health]
```

### 9.9 Empty and low-volume states

If no eligible material exists:

```text
No eligible client material has arrived this week yet.
Fathom is connected and checked 12 minutes ago.
```

If sources are disconnected, do not use the same empty state. Show the connection failure and recovery action.

---

## 10. Phase 2 — Notice / Key Moments

### 10.1 Purpose

Transform the closed weekly source snapshot into a small number of strong, evidence-backed content angles.

`Notice` is both a visible transition state and the name of the backend editorial-selection phase. It is not a human approval gate.

### 10.2 What the user sees while processing

Show a structured stage list using actual job completion:

```text
Preparing this week’s content angles

✓ Weekly bucket locked: 10 meetings and 14 Slack signals
✓ Eligible source material classified
✓ 31 verified moments found
● Grouping related moments
○ Checking recent published content
○ Evaluating evidence and fit
○ Preparing the strongest angles

You can leave this page. We will notify you when review is ready.
```

Also show:

- Bucket snapshot timestamp
- Included source count
- Excluded/skipped count
- Verified moment count
- Degraded integrations
- Safe cancellation behavior, if supported

### 10.3 Optional progressive evidence display

Verified moments may appear as read-only cards while angle generation continues. Clearly label them as `Candidate moment`, not as approved content angles.

Each card may show:

- Moment type
- Exact source excerpt
- Speaker and attribution quality
- Meeting and timestamp
- Proof status

Do not display incomplete model-generated angle text before it is persisted and eligible for review.

### 10.4 Backend responsibilities

- Snapshot new and unresolved eligible moments.
- Generate or retrieve embeddings.
- Build provisional clusters.
- Split/merge clusters into coherent ideas.
- Preserve strong singleton ideas.
- Apply eligibility rules.
- Evaluate proof, figure scope, consent, positioning, capability, ICP, novelty, and format sufficiency.
- Score eligible ideas.
- Select zero to five without padding.
- Persist reasons, warnings, evidence membership, prompt/configuration versions, and digest snapshot.

### 10.5 Completion transition

When ready:

- Set cycle state to `angles_ready`.
- Show an in-app notification.
- Optionally post one safe Slack notification with short titles and a deep link.
- Move the primary CTA to `Review content angles`.

---

## 11. Phase 3 — Content Angle Review / Gate 1

### 11.1 Purpose

Let Whitney inspect, edit, select, pass, defer, or request more evidence for the strongest angles.

### 11.2 Angle-list layout

Use a list or board of zero to five angle cards. The ordinary target is three to four.

Each card includes:

- Editable title
- One-sentence principle/thesis
- Why this matters to the audience
- Primary evidence
- Supporting evidence count
- Evidence-strength explanation
- Recurrence or novelty explanation
- Relevant offer suggestion
- Warnings
- Proposed role in the weekly pack
- Current decision state

### 11.3 Evidence display

Primary evidence should be visible without opening a separate page. Additional evidence may open in a side panel or expanded section.

Evidence items include:

- Exact quote or scoped figure
- Moment type
- Speaker
- Attribution quality
- Source title
- Date and timestamp
- Source link
- Consent/anonymization state

### 11.4 Scores

If scores are shown, display the dimensions and concise reasons:

- Audience pain
- Recurrence
- Novelty
- Offer fit

Do not display unexplained bars or confidence percentages. The total rank is supporting information, not the approval decision.

### 11.5 Whitney actions

For each angle:

- `Select for this week`
- `Edit title`
- Add or edit steering direction
- Choose an existing CTA or enter a custom CTA label and destination
- `Request another look`
- `Save for later`
- `Pass`

Pass requires one reason:

- Off brand
- Done before
- Weak proof
- Wrong audience
- Not now
- Consent concern
- Other

An optional detail field follows the reason.

### 11.6 CTA rule

The system may suggest an offer but must not preselect a CTA. Whitney explicitly chooses the CTA before approval.

### 11.7 Multi-angle selection

Whitney may select multiple angles. Each selected angle becomes a research and brief workstream.

Before confirming Gate 1, show the proposed weekly asset allocation:

```text
Angle A → Email + Carousel
Angle B → Reel 1 + Reel 2
Angle C → Reel 3
```

Whitney can adjust this allocation later in the Pack Plan, but the UI must prevent accidental generation of a complete five-asset pack for every selected angle unless that is an explicit future feature.

### 11.8 Approval behavior

Gate 1 approval:

- Requires Whitney.
- Requires CTA selection.
- Requires the current `expected_revision`.
- Uses an idempotency key.
- Freezes the approved angle revision, evidence, warnings, steering direction, offer, and CTA.
- Enqueues research.

Do not optimistically show an approval as complete before the server confirms it.

### 11.9 Backend responsibilities

- Save editable angle revisions.
- Validate evidence and permissions.
- Persist pass/defer/research-again decisions.
- Enforce Whitney-only approval.
- Detect revision conflicts.
- Freeze the approved snapshot.
- Enqueue one research workflow per approved angle.

---

## 12. Phase 4 — Research Processing

### 12.1 Purpose

Gather enough internal evidence and external framing to build a reliable brief for every approved angle.

### 12.2 Research overview

Show one row/card per approved angle. Each workstream progresses independently.

Recommended visible stages:

```text
✓ Gathering related client results
✓ Finding audience questions and objections
● Reviewing Whitney’s prior explanations
○ Checking previous content coverage
○ Gathering external audience language
○ Synthesizing the research packet
○ Building the brief
```

### 12.3 Research detail panel

As verified findings become available, display:

- Corroborating client results
- Recurring questions and objections
- Whitney’s explanations
- Relevant Slack proof
- Prior coverage
- Consent/attribution warnings
- External framing findings
- Contradictions
- Unanswered questions

Label every finding as one of:

- `Verified internal proof`
- `Internal context`
- `External framing`
- `Inference`
- `Contradiction`
- `Question`

### 12.4 What remains hidden

Do not expose:

- Raw search provider responses
- Provider API keys
- Search billing details
- Embedding vectors
- Full prompts
- Hidden model reasoning
- Internal retrieval ranks without a user-facing explanation

### 12.5 Degraded external research

External research is optional and non-blocking. If unavailable:

```text
External audience research is unavailable. The brief will use verified internal evidence only.
```

The UI must not make the whole workflow look failed.

### 12.6 Background behavior

- Research continues after navigation or refresh.
- The user can inspect completed findings while later steps continue.
- The app notifies Whitney when a brief is ready or needs an answer.
- Failed work can be retried safely without duplicating research records or charges.

### 12.7 Backend responsibilities

- Run permission-filtered internal retrieval.
- Separate client evidence from external context.
- Run bounded external searches after Gate 1 only.
- Store queries, sources, timestamps, summaries, and proof eligibility.
- Identify contradictions and open questions.
- Generate a versioned brief.

---

## 13. Phase 5 — Brief Review / Gate 2

### 13.1 Purpose

Let Whitney review and freeze the editorial plan before any asset drafting occurs.

### 13.2 Brief navigation

When multiple angles are selected, show one brief tab or list item per angle:

- Brief title
- Angle title
- Status
- Unanswered required-question count
- Revision number
- Last editor and timestamp

### 13.3 Brief fields

Each one-page brief contains:

- Core principle and insight
- Audience and pain
- Primary proof
- Corroborating proof
- Three-to-four-line message spine
- CTA label and destination inherited from Gate 1
- Voice and point-of-view instruction
- Unique role for each assigned asset
- Proposed reel count
- Internal research summary
- External framing summary
- Claims requiring permission or recording verification
- Warnings and handling instructions
- Required open questions
- Optional open questions

### 13.4 Editing behavior

- Fields are directly editable according to role.
- Autosave may update draft fields, but show `Saving`, `Saved`, or `Save failed` honestly.
- Preserve server revisions.
- Never overwrite a newer revision silently.
- Show field-level validation.
- Keep evidence links attached to relevant proof fields.

### 13.5 Required questions

Gate 2 is disabled while a required question is unanswered. The disabled state must explain exactly what remains:

```text
Approval is unavailable until 2 required questions are answered.
```

### 13.6 Whitney actions

- Edit the brief
- Answer questions
- Request changes with instructions
- Return to the angle
- Approve this brief
- Approve all eligible briefs

### 13.7 Approval behavior

Gate 2 approval:

- Requires Whitney.
- Freezes the exact brief revision.
- Validates that the Gate 1 angle/CTA revision is still current.
- Enqueues generation only for assigned weekly pack assets.
- Uses `expected_revision` and idempotency.

### 13.8 Revision invalidation

- Editing an approved Gate 1 angle, steering direction, or CTA makes its research, brief, and dependent pack work stale.
- Editing an approved brief makes dependent asset generations stale and requires Gate 2 approval again.
- The UI must clearly explain downstream impact before saving such a change.

### 13.9 Backend responsibilities

- Store immutable brief revisions.
- Validate required fields and questions.
- Enforce CTA identity.
- Enforce current upstream revisions.
- Freeze the approved brief snapshot.
- Create/update the weekly pack plan.
- Enqueue independent asset-generation jobs.

---

## 14. Pack Plan

### 14.1 Purpose

Coordinate multiple approved briefs into one weekly pack without losing source lineage.

### 14.2 Default pack contract

The first production weekly pack contains:

- One email
- One carousel with 7–10 slides
- One to three reel scripts
- Long and short captions for the carousel and each reel

Stories, case studies, reel-cover titles, hashtags, and alt text are outside the first release.

### 14.3 Assignment UI

Show a simple asset-to-brief assignment table:

| Asset slot | Approved angle/brief | Status |
|---|---|---|
| Email | Select approved brief | Required |
| Carousel | Select approved brief | Required |
| Reel 1 | Select approved brief | Required |
| Reel 2 | Select approved brief | Optional |
| Reel 3 | Select approved brief | Optional |

The system may propose assignments, but a human can review them before generation.

### 14.4 Validation

- Every required slot has one approved brief revision.
- Assigned briefs are current.
- CTA and offer conflicts are resolved.
- Reel count matches the approved plan.
- Each asset records its governing brief revision.

---

## 15. Phase 6 — Pack Generation and Automated Checks

### 15.1 Purpose

Generate every asset independently from its approved brief and then validate the output.

### 15.2 Asset matrix

Show each asset independently:

| Asset | Angle | Generation | Checks | Review readiness |
|---|---|---|---|---|
| Email | Angle A | Complete | Running | Waiting |
| Carousel | Angle A | Drafting | Not started | Waiting |
| Reel 1 | Angle B | Complete | Passed | Ready |
| Reel 2 | Angle B | Queued | Not started | Waiting |
| Reel 3 | Angle C | Complete | Warning | Ready with warning |

### 15.3 User-facing generation states

- `Queued`
- `Drafting`
- `Saving draft`
- `Checking evidence`
- `Checking structure`
- `Checking voice`
- `Checking overlap`
- `Repairing a failed check`
- `Ready for review`
- `Ready with warnings`
- `Blocked by failed check`
- `Failed`

### 15.4 Progressive availability

Completed assets should become readable before the entire pack is finished. Clearly label them as provisional until checks for the current revision complete.

### 15.5 Backend responsibilities

- Generate each asset in a separate job.
- Use only the governing approved brief and permitted evidence.
- Prevent generated sibling assets from becoming context for one another.
- Store asset revisions.
- Run factual checks.
- Run structural checks.
- Run voice checks.
- Run overlap checks.
- Attempt no more than two targeted automated repairs for eligible failures.
- Persist checker version, evidence, severity, and evaluated asset revision.

### 15.6 Check display

Checks should be grouped by type:

#### Factual — blocking

- Quote or figure maps to approved evidence.
- Figure scope is preserved.
- Client naming is permitted.
- External research is not presented as client/WIA proof.

#### Structural — blocking

- Required fields exist.
- Carousel has 7–10 slides.
- Reel count and distinctness match the plan.
- CTA exactly matches Gate 1.
- POV and captions are present.

#### Voice — blocking or warning

- Banned terms or constructions
- Founder-guide mismatch
- Unresolved subjective issue after bounded repair

#### Overlap — blocking or warning

- Exact paragraph reuse is blocking.
- High semantic similarity is a warning requiring acknowledgement.

### 15.7 Spend-limit state

If processing pauses at a spend ceiling:

```text
Generation is paused by the configured processing limit.
3 of 5 assets are complete. An operator must resume the remaining jobs.
```

Do not present this as an unknown error or continuously retry from the browser.

---

## 16. Phase 7 — Pack Review and Gate 3

### 16.1 Purpose

Give Whitney one place to edit, validate, and approve the complete weekly pack.

### 16.2 Layout

Recommended desktop layout:

- Left: asset navigation
- Center: selected asset editor
- Right: evidence, checks, comments, and revision details
- Top: pack status and approval readiness

On smaller screens, collapse the right panel into tabs or drawers and make asset navigation a compact selector.

### 16.3 Email editor

Show editable fields for:

- Primary subject
- Subject alternatives
- Preview text
- Body
- CTA label and destination
- P.S.

### 16.4 Carousel editor

Show:

- Ordered slide list
- Per-slide copy
- Per-slide design note
- Reorder controls where allowed
- Long caption
- Short caption

### 16.5 Reel editor

Show:

- Hook
- Alternate hooks
- Timed sections
- Script body
- B-roll/on-screen guidance
- Production/handling notes
- Long caption
- Short caption

### 16.6 Editing behavior

Editing an asset:

- Creates a new asset revision.
- Marks prior checks stale.
- Re-runs affected checks.
- Invalidates an existing Gate 3 approval.
- Does not invalidate unrelated approved briefs unless the edit changes upstream brief content.

### 16.7 Warning acknowledgement

Warnings must include:

- What was detected
- Which content is affected
- Why it matters
- Evidence or comparison where appropriate
- Acknowledgement control for Whitney

Acknowledgement is append-only and tied to the exact asset revision/check result.

### 16.8 Gate 3 readiness

Enable final approval only when:

- Every required asset exists.
- All blocking checks pass for current revisions.
- All governing briefs and research are current.
- Whitney has acknowledged remaining warnings.

### 16.9 Final approval

The confirmation surface must summarize:

- Pack revision
- Included assets
- Governing brief revisions
- Outstanding acknowledged warnings
- Result of approval: `Approved-ready in Content Atelier`
- Explicit statement: `This will not publish or send content automatically.`

After server confirmation:

- Set state to `approved_ready`.
- Freeze an immutable snapshot.
- Keep content readable and copyable.
- Offer non-destructive copy/export actions only when implemented.
- Do not display a fake `Sent to Giselle` state unless an actual authorized handoff integration exists.

---

## 17. Post-approval and weekly history

### 17.1 Approved-ready view

Show:

- Approval date and actor
- Immutable pack version
- Asset list
- Copy/download actions that are actually implemented
- Source lineage
- Prior revisions
- Start-next-revision action if changes are required

### 17.2 Changes after approval

An approved pack is immutable. `Create new revision` produces a new editable revision, marks it unapproved, and requires checks and Gate 3 again.

### 17.3 Feedback

Capture:

- Pass reasons
- Edit summaries
- Revision requests
- Warning acknowledgements
- Human labels

The first release stores this feedback for analysis. It must not silently rewrite prompts, weights, or strategy rules.

---

## 18. Moments Ledger

### 18.1 List view

Provide:

- Search
- Date range
- Source filter
- Moment-type filter
- Proof-state filter
- Consent-state filter
- Lifecycle filter
- Used/unused filter

Columns or card fields:

- Moment type
- Excerpt
- Source
- Speaker
- Attribution quality
- Proof state
- Consent state
- Lifecycle
- Created date
- Usage count

### 18.2 Moment detail

Show:

- Raw quote
- Cleaned context separately
- Source title and link
- Timestamp
- Speaker and attribution
- Proof state
- Consent status
- Labels and notes
- Related moments
- Idea/brief/pack lineage
- Extraction/audit version summaries that are safe for product users

### 18.3 Visual proof

OCR or image-derived material remains `unverified_visual` until a person confirms it. The UI must distinguish confirmation from mere extraction.

---

## 19. Ideas and History

Provide searchable history for:

- Weekly digests
- Selected ideas
- Passed ideas and reasons
- Saved-for-later ideas
- Ineligible ideas and explanations
- Score snapshots
- Evidence membership
- Gate decisions
- Research/brief/pack lineage

Historical decisions are read-only. A user may reuse an idea by creating a new current-cycle revision, not by mutating history.

---

## 20. Library and Sources

### 20.1 Source health

For each source, show:

- Connection/configuration state
- Coverage description
- Last successful synchronization
- Last attempted synchronization
- Cursor/checkpoint time
- Current delay
- Last error
- Missing user/host coverage
- Retry/reconnect action when authorized

Sources:

- Fathom — live source
- Slack — approved signal channels
- Zoom — historical backfill only
- Manual source upload — podcasts, webinars, interviews, and other flagged material

Do not suggest that Zoom is a live integration.

### 20.2 Editorial library

Show manageable records for:

- Voice/brand guidance
- Published content precedent
- CTA catalog
- Offers
- Consent register
- Glossary

Changes to these records should be versioned where they affect future generation or evidence use.

### 20.3 Operational failures

Show only actionable failure summaries to product operators. Raw stack traces and secrets remain in server logs.

---

## 21. Standard processing UX

Every asynchronous area should use the same processing pattern.

### 21.1 Required elements

- Clear job/group title
- Current named stage
- Completed stages
- Actual unit counts when available
- Start/update timestamp
- `You can leave this page` message for background work
- Retry or operator action only when appropriate
- Link to affected source/entity

### 21.2 Do not use

- Endless full-page spinners
- Fake progress percentages
- Model token counters
- Raw queue messages
- Animated typing that implies a model is streaming hidden reasoning
- Auto-retry buttons that can duplicate costly work

### 21.3 Example processing component

```text
Building brief for “Ads that keep working while you step away”

✓ Internal evidence gathered — 7 findings
✓ Previous content checked — 18 pieces
✓ External framing gathered — 5 findings
● Synthesizing the message spine
○ Validating claims
○ Saving brief revision

Last updated 24 seconds ago · Safe to leave this page
```

### 21.4 Stalled work

If no progress occurs beyond a backend-defined threshold:

```text
This step is taking longer than expected. Work is still queued and no action is required.
```

If a terminal failure occurs:

```text
Brief generation stopped after retrying. Your approved angle and research are safe.
[Retry generation] [View technical reference]
```

`View technical reference` should expose a safe support ID, not internal logs.

---

## 22. Notifications

### 22.1 In-app notifications

Notify when:

- Angles are ready
- A required question blocks a brief
- A brief is ready for Gate 2
- A pack is ready for review
- A processing job fails and requires action
- A source connection becomes materially degraded

### 22.2 Slack notifications

Slack is notification-only in the intended architecture.

Allowed content:

- Weekly/digest date
- Safe short titles
- Number of items needing review
- Secure app deep link

Do not place approval buttons, sensitive evidence, full briefs, or complete packs in Slack.

### 22.3 Notification deduplication

Retries must not create duplicate notifications. The frontend should display the server-confirmed notification state.

---

## 23. Loading, empty, error, stale, and degraded states

Every page must implement these states deliberately.

### 23.1 Initial loading

Use skeleton structure that matches the destination layout. Preserve the page title and navigation.

### 23.2 Empty

Explain whether emptiness is expected, filtered, or caused by missing sources.

### 23.3 Recoverable error

Keep previously loaded safe data visible when possible. Provide a retry action.

### 23.4 Authorization error

Explain the permission boundary without exposing protected content.

### 23.5 Revision conflict

All state-changing requests send `expected_revision`. On `409 revision_conflict`:

- Stop the mutation.
- Preserve the user’s unsaved local edits.
- Explain that a newer version exists.
- Offer `Review latest version` and a safe manual comparison/merge path.
- Never blindly resubmit against the new revision.

### 23.6 Stale downstream work

If upstream content changes, show affected descendants:

```text
Changing this CTA will make 2 briefs and the current pack stale. They will require approval and regeneration again.
```

### 23.7 Degraded integration

Display what is missing and what still works. Example:

```text
External research is unavailable. Internal research and brief generation can continue.
```

---

## 24. Frontend/backend responsibility matrix

| Stage | Frontend owns | Backend owns | UI during backend work |
|---|---|---|---|
| Weekly collection | Week view, bucket visualization, source-item states | Ingestion, normalization, filtering, extraction, persistence | Per-source status and actual counts |
| Notice | Stage display and verified-moment previews | Snapshot, embeddings, clustering, eligibility, ranking | Named stages and moment count |
| Angle review | Evidence presentation, editing, CTA selection, decisions | Revision persistence, policy validation, Gate 1, research enqueue | Server-confirmed save/approval states |
| Research | Research status and safe findings | Internal/external retrieval, provenance, synthesis | Per-angle stage list and partial verified findings |
| Brief review | Structured editor, questions, Gate 2 | Brief revisions, validation, freeze, generation enqueue | Saving state and clear blockers |
| Pack plan | Asset/brief assignment UI | Assignment validation and frozen references | Validation feedback |
| Generation | Asset matrix and progressive previews | Independent jobs and revision storage | Per-asset generation stages |
| Checks | Findings, severities, acknowledgement UI | Factual, structural, voice, overlap checks and repair | Check-by-check state |
| Final review | Asset editors and Gate 3 | Revisioning, currentness checks, immutable approval snapshot | Approval readiness and blockers |
| History | Search, inspection, lineage | Audit storage and query | Stable read-only records |
| Source/library admin | Safe configuration forms | Secrets, connections, polling, policy enforcement | Health and actionable errors only |

---

## 25. API and trust boundary

### 25.1 Browser path

The browser uses the Command Center session and same-origin BFF:

```text
Browser
→ /api/content-atelier/* BFF
→ standalone Content Atelier FastAPI service
→ PostgreSQL / workers / providers
```

The BFF injects the service credential and authenticated actor. The browser never receives the upstream bearer token and cannot choose another approving identity.

### 25.2 Existing or already planned routes

```text
GET  /source-health
GET  /moments
GET  /moments/:id
POST /moments/:id/labels
POST /moments/:id/confirm-visual-proof

POST /digests/preview
GET  /digests
GET  /digests/:id
POST /digests/:id/notify

GET  /ideas/:id
POST /ideas/:id/gate-1

GET  /ideas/:id/research
GET  /briefs/:id
PUT  /briefs/:id
POST /briefs/:id/gate-2

GET   /packs/:id
PATCH /assets/:id
POST  /packs/:id/checks
POST  /packs/:id/gate-3
```

### 25.3 Additional API required for the weekly target UX

The weekly UI likely requires:

```text
GET  /weekly-cycles
GET  /weekly-cycles/current
GET  /weekly-cycles/:id
POST /weekly-cycles/:id/close
GET  /weekly-cycles/:id/bucket-items
GET  /weekly-cycles/:id/workflow
GET  /weekly-cycles/:id/ideas
PUT  /weekly-cycles/:id/pack-plan
POST /weekly-cycles/:id/generate-pack
GET  /weekly-cycles/:id/pack
```

Exact route naming may change, but the backend—not frontend local storage—must own weekly membership, cutoff, phase, pack assignments, and current revisions.

### 25.4 Typed contracts

- Generate TypeScript types from FastAPI OpenAPI.
- Commit generated contracts.
- Fail frontend CI when API contracts drift.
- Use consistent error envelopes.
- Paginate large ledgers/history.

### 25.5 Mutation requirements

Every meaningful mutation includes:

- `expected_revision`
- Idempotency key where duplicate submission matters
- Authenticated actor from the BFF
- Clear server-confirmed response

---

## 26. Suggested frontend component structure

Component naming is illustrative.

```text
ContentAtelierApp
├── AtelierShell
│   ├── AtelierHeader
│   ├── WeekSelector
│   ├── PhaseTracker
│   ├── ActionBanner
│   └── NotificationTray
├── WeeklyWorkspace
│   ├── WeeklyBucketView
│   │   ├── BucketMeter
│   │   ├── WeekDayStrip
│   │   ├── BucketItemList
│   │   ├── BucketItemCard
│   │   └── SourceHealthBanner
│   ├── NoticeProcessingView
│   │   ├── ProcessingStageList
│   │   └── CandidateMomentPreview
│   ├── AngleReviewView
│   │   ├── AngleCard
│   │   ├── EvidenceList
│   │   ├── CtaSelector
│   │   ├── PassDialog
│   │   └── PackAllocationPreview
│   ├── ResearchView
│   │   ├── ResearchWorkstreamCard
│   │   └── ResearchFindingList
│   ├── BriefReviewView
│   │   ├── BriefTabs
│   │   ├── BriefEditor
│   │   ├── RequiredQuestions
│   │   └── GateTwoControls
│   ├── PackPlanView
│   │   └── AssetBriefAssignment
│   ├── GenerationView
│   │   ├── AssetStatusMatrix
│   │   └── CheckProgress
│   └── PackReviewView
│       ├── AssetNavigator
│       ├── EmailEditor
│       ├── CarouselEditor
│       ├── ReelEditor
│       ├── EvidencePanel
│       ├── CheckPanel
│       └── GateThreeControls
├── MomentsView
├── IdeasHistoryView
└── LibrarySourcesView
```

Keep page-level orchestration separate from presentational/editor components. Avoid one monolithic `ContentAtelierScreen` containing every phase.

---

## 27. Data-fetching and state rules

### 27.1 Server state

Treat weekly state, jobs, revisions, approvals, research, briefs, packs, and checks as server state.

### 27.2 Local UI state

Local state may own:

- Open/closed panels
- Current tab
- Temporary filter text
- Unsubmitted editor text
- Draft comparison selection

Local state must not become the source of truth for:

- Approval status
- Current revision
- CTA choice after Gate 1
- Pack readiness
- Source-processing status
- Asset checks
- Weekly phase

### 27.3 Refresh strategy

Use polling, server-sent events, or WebSockets according to platform constraints. The contract must support:

- Fast updates while processing
- Slower refresh when idle
- Backoff on failures
- Manual refresh
- Immediate cache invalidation after successful mutations

### 27.4 Autosave

Autosave is appropriate for editable draft fields. It is not appropriate for approvals, pass decisions, notification sends, or generation triggers.

---

## 28. Visual direction

The application should evolve the pitch’s editorial, premium visual language into an operational product.

### 28.1 Reference palette

- Background: `#F6F0EB`
- Surface: `#FFFFFF`
- Primary ink: `#1E1826`
- Secondary text: `#3A3242`
- Plum: `#2A2132`
- Gold: `#8A6630`
- Bright gold: `#B98E4E`
- Pale gold: `#FFF6E9`
- Blush: `#F2E2DA`
- Structural line: `#D9CBC1`

All final colors must meet accessible contrast requirements.

### 28.2 Typography

- Display/editorial headings: Bodoni Moda or approved equivalent
- Product/body/interface text: Jost or approved equivalent
- Use system fallbacks and avoid invisible text while fonts load.

### 28.3 Visual semantics

- Circular markers: system preparation steps
- Diamond markers: human decisions/gates
- Gold: progress, attention, and selected editorial evidence
- Plum: primary action or high-contrast editorial preview
- Neutral surfaces: operational lists and editors

### 28.4 Motion

- Use restrained transition animations for phase changes and bucket additions.
- Never animate continuously merely to imply backend activity.
- Respect `prefers-reduced-motion`.
- Progress must remain understandable without motion.

### 28.5 Density

The pitch is spacious and theatrical; the working application must be more information-dense while preserving calm hierarchy. Evidence, revisions, and blockers must not be hidden to preserve aesthetics.

---

## 29. Responsive behavior

### 29.1 Desktop

- Full weekly timeline
- Multi-column angle cards where readable
- Editor with navigation and evidence/check side panel
- Persistent phase tracker

### 29.2 Tablet

- Wrap phase tracker or use horizontal scrolling with visible current phase
- Two-column cards when space permits
- Evidence/check panel becomes a drawer or tab

### 29.3 Mobile

- Single-column phase workspace
- Compact week/day selector
- Asset navigation as a select/list
- Editors remain fully functional
- Fixed bottom action area may be used only if it does not cover content or keyboard input
- No approval action should require hover

The complete gate flow must remain usable at 320 CSS pixels.

---

## 30. Accessibility requirements

- Meet WCAG 2.2 AA where practical.
- Complete every gate using keyboard only.
- Preserve visible focus.
- Use semantic headings, buttons, inputs, dialogs, tabs, tables, and status regions.
- Do not encode status through color alone.
- Give evidence links descriptive accessible names.
- Associate field errors with inputs.
- Move focus to the first error after failed validation.
- Announce background state transitions through restrained `aria-live` regions.
- Do not announce every polling refresh.
- Ensure editors support zoom and reflow.
- Provide reduced-motion behavior.
- Provide accessible labels for progress stages and warnings.
- Return focus predictably when dialogs close.

Automated accessibility tests should cover all three gates, conflict states, errors, and the asset editor.

---

## 31. Security, privacy, and evidence safety

- Browser authentication uses the existing application session.
- The BFF injects the trusted actor and service token.
- Whitney-only approval is rechecked by the Atelier service.
- Do not trust a role flag supplied only by the browser.
- Sanitize generated rich text before rendering.
- Prevent generated content from executing HTML or scripts.
- Avoid exposing sensitive source content in URLs, analytics, or Slack notices.
- Preserve raw evidence separately from cleaned/model-facing text.
- Require consent or safe anonymization for named-client content.
- Redact secrets and stack traces from user-facing errors.
- Log gate actions and revisions server-side.

---

## 32. Analytics and operational measurements

Product analytics should avoid storing sensitive source text.

Measure:

- Bucket item counts and processing latency
- Eligible moment count by week
- Number of angles returned
- Gate 1 approval/pass/defer reasons
- Time spent awaiting each gate
- Research and brief completion latency
- Brief revision count
- Asset generation/check latency
- Check failure and warning categories
- Gate 3 approval time
- Source-health outages
- Revision-conflict rate

Do not send raw transcripts, quotes, briefs, or asset copy to third-party analytics.

---

## 33. Current backend reality versus target UI

Implementation agents must distinguish schema/helper existence from an executable end-to-end workflow.

### 33.1 Currently executable or partially executable

- Fathom ingestion and recovery polling
- Zoom/manual import paths
- Slack polling and metadata capture
- Normalization and deterministic classification
- Original extraction pass
- Verbatim candidate verification
- Canonical moment promotion/deduplication
- Legacy per-call triage
- Source-health and moments APIs
- Moment labels and visual-proof confirmation
- Gate 1 persistence for an existing idea
- Durable job/model-call foundations

### 33.2 Existing foundations but incomplete orchestration

- Search and clustering helpers
- Eligibility helpers
- Ranking helpers
- Upgraded ledger/digest schema
- Research/brief/pack/check schema
- Check-policy helpers
- Notification formatting/outbox foundations
- Approval invalidation policy helpers

### 33.3 Still requiring backend implementation

- Weekly cycle and bucket ownership
- Automatic weekly cutoff/scheduler
- Complete embedding production and persisted clustering workflow
- Editorial grouping and idea generation
- End-to-end digest generation
- Research enqueue from Gate 1
- Complete internal/external research adapters
- Brief generation and Gate 2 API flow
- Multi-brief weekly pack plan
- Independent asset-generation workers
- Full check/critic/repair orchestration
- Gate 3 API and immutable snapshot orchestration
- Notification dispatcher

The frontend should be built against explicit fixtures or mock contracts for unimplemented stages, with feature flags and truthful unavailable states. It must not pretend missing backend behavior is live.

---

## 34. Recommended implementation sequence

### Phase A — Shell and read-only foundations

- App shell and navigation
- Weekly phase tracker
- Source health
- Moments Ledger
- Deep-link routing
- Loading/error/empty patterns
- Generated API types

### Phase B — Weekly Bucket

- Weekly-cycle contracts
- Bucket visualization
- Source-item timeline
- Calibration-mode close action
- Processing-state components

### Phase C — Notice and Gate 1

- Notice processing view
- Angle cards and evidence
- CTA selector
- Pass/request-another-look flows
- Whitney-only approval
- Revision conflicts

### Phase D — Research and Gate 2

- Research workstreams
- Finding provenance
- Brief editor
- Required questions
- Brief revisions and Gate 2

### Phase E — Pack plan and generation

- Multi-brief asset allocation
- Asset status matrix
- Progressive asset availability
- Check displays

### Phase F — Pack editing and Gate 3

- Email/carousel/reel editors
- Warning acknowledgement
- Revision/check invalidation
- Gate 3 confirmation
- Approved-ready immutable view

### Phase G — Hardening

- Role matrix tests
- Browser E2E gate lifecycle
- Accessibility automation
- Mobile behavior
- Failure/degraded-mode tests
- Analytics and operational dashboards

---

## 35. Frontend acceptance criteria

### Weekly Bucket

- The user can distinguish source silence from normal emptiness.
- Every bucket item displays an honest server-derived state.
- The bucket never uses a fake completion percentage.
- Calibration and scheduled modes are visibly different.

### Notice

- The user sees named processing stages and actual counts.
- The user can leave and return without losing progress.
- Zero eligible angles is represented as a valid result.

### Gate 1

- Every angle has inspectable proof.
- No CTA is preselected.
- Pass requires a reason.
- Only Whitney can approve.
- Approval uses the current revision and survives refresh.
- Multiple selected angles produce separate research workstreams.

### Research and Gate 2

- Internal proof and external framing are visually distinct.
- External research failure does not block internal-only briefs.
- Required questions block approval with a clear explanation.
- Approved brief revisions are immutable snapshots.

### Pack Plan and Generation

- Every asset is assigned to an approved brief revision.
- Assets generate independently.
- Users can inspect completed assets while others process.
- Processing and checks are distinct states.

### Gate 3

- Blocking checks prevent approval.
- Warnings require explicit acknowledgement.
- Editing an asset reruns applicable checks.
- Only Whitney can approve.
- Approval clearly states that no publishing or external handoff occurs.
- Approved packs are immutable.

### Platform behavior

- Deep links survive authentication and refresh.
- Revision conflicts never silently overwrite work.
- The gate flow is keyboard accessible.
- The browser never receives service secrets.
- Frontend counts and statuses come from backend state, not fixtures.

---

## 36. End-to-end reference scenario

1. On Monday, two Fathom calls appear in the weekly bucket.
2. One call completes extraction and shows four verified moments; the other waits for a transcript.
3. Slack signals and further calls accumulate through Friday.
4. At cutoff, the bucket snapshot closes. Late material is assigned according to the configured cutoff policy rather than silently changing the snapshot.
5. The Notice screen shows actual progress through moment selection, clustering, eligibility, and ranking.
6. Four strong angles become ready.
7. Whitney opens the deep link, edits two titles, passes one as `done_before`, saves one for later, and selects two for the week.
8. She chooses the CTA and confirms Gate 1.
9. Two research workstreams begin. One has external research available; the other completes in internal-only degraded mode.
10. Two briefs appear. A required question blocks one brief until Whitney answers it.
11. Whitney edits and approves both briefs.
12. The Pack Plan assigns email and carousel to the first brief and two reels to the second brief.
13. Assets generate independently and appear as they pass checks.
14. The carousel has a blocking figure-scope failure and is repaired. One reel retains a voice-overlap warning.
15. Whitney edits the reel, waits for current checks, and acknowledges the remaining non-blocking warning.
16. Gate 3 becomes available.
17. Whitney approves the exact current pack revision.
18. The pack becomes `approved_ready`, remains readable/copyable in the app, and is not posted or sent automatically.

---

## 37. Open product decisions for later refinement

The specification is implementable without settling every item below, but these should be resolved before production launch:

1. Exact business timezone and weekly cutoff.
2. Treatment of late-arriving Friday/weekend meetings.
3. Whether a cycle can be reopened after closing.
4. Maximum number of angles Whitney may approve in one week.
5. Whether email and carousel may be governed by different briefs.
6. Whether optional reel slots are chosen at Gate 1, Gate 2, or Pack Plan.
7. Which non-Whitney roles can edit briefs and assets.
8. Whether saved-for-later ideas automatically re-enter future eligibility.
9. Which copy/export formats are included in the first release.
10. Notification preferences and escalation timing.
11. Whether research results can be manually attached or excluded.
12. Final design of manual merge behavior after a revision conflict.

Until these are decided, implementations should use explicit feature flags and conservative defaults rather than silent assumptions.

---

## 38. Final boundary summary

### The frontend is responsible for

- Showing weekly progress and source health.
- Presenting evidence and provenance clearly.
- Letting users inspect, edit, select, pass, steer, approve, and acknowledge.
- Showing truthful background-processing states.
- Preserving unsaved work and handling conflicts.
- Enforcing visible role affordances.
- Providing accessible and responsive interaction.

### The backend is responsible for

- Ingestion, credentials, polling, webhooks, and deduplication.
- Transcript normalization and classification.
- Moment extraction and verification.
- Search, embeddings, clustering, eligibility, and ranking.
- Research and brief generation.
- Revision storage and approval snapshots.
- Independent asset generation.
- Automated checks and bounded repair.
- Authorization, audit logs, idempotency, queues, retries, and spend controls.
- Notifications and durable workflow state.

### While the backend works, the UI is responsible for

- Naming the current stage.
- Showing completed stages and actual counts.
- Showing partial verified results where safe.
- Explaining whether the user may leave.
- Distinguishing normal processing, degraded processing, stalled work, and terminal failure.
- Making the next required human action unmistakable.

