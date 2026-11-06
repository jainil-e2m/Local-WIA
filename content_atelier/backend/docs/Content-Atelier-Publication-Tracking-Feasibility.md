# Publication tracking: manual marking and next-day verification

> **Research update, 5 November 2026:** The later [automatic-verification research](Content-Atelier-Automatic-Publication-Verification-Research-2026-11-05.md) contains current API findings, a read-only GHL authentication result, Instagram account-access findings, and the proposed evidence/migration plan. The manual UI has since been implemented locally; the owner removed the pack-wide progress bar. The earlier statements below describe the proposal at the time, not the latest local UI or proof that automatic verification is connected.

**Date:** 5 November 2026  
**Status:** Feasibility analysis and proposed behavior only; no implementation or configuration changes.  
**Baseline:** `52e7083`.  
**Direction:** Retire the manual whole-pack Ready to publish approval step. Replace its prominent action with a way to record actual publication, and later verify scheduled pieces through Instagram and GHL.  
**Confirmed workflow:** Instagram is published directly or through another tool, not through GHL Social Planner. Email may use both GHL campaigns and workflows; the exact split is not yet established.

## 1. Recommended product change

Replace the approval milestone with **piece-level publication tracking**. Do not merely rename the existing button: its current action approves an entire pack, whereas the desired action records a real-world event for an individual piece and destination.

The prominent action should follow the active tab: **Mark Email as sent**, **Mark Carousel as published**, or **Mark Reel 1 as published**. If a consistent label is preferred, use **Mark as published** with the active piece named in its confirmation dialog. It must never mark all five pieces implicitly. A later bulk action could open an explicit checklist, with publication details per selected piece.

Show pack progress such as **2 of 5 pieces published**, derived from the expected destinations. If a piece must go to more than one platform, show destination-specific completion and aggregate the pack only after the required placements are complete. Instagram and GHL email are normally different targets for different pieces, not two mandatory checks on every piece.

Retain content issues as informational findings and retain existing identity/access controls, version integrity and removal protections where applicable. Removing the readiness-approval ceremony does not mean erasing content history or silently claiming that all findings are resolved. Recording a fact that something went out must remain distinct from endorsing the content.

## 2. What already exists and where it falls short

- `frontend/src/components/PackPiece.tsx` already provides a per-piece **Mark published** form: date, channel, final text and optional URL.
- `packs/versions.py::published` records through `knowledge/capture.py::record_pack`. It records who marked it and the source pack version, and preserves the difference between draft and final text.
- This is a manual assertion. It does not contact Instagram or GHL to verify publication.
- The current capture key is `pack:{brief_id}:{piece}`: one final per logical piece of a brief, across pack versions. This is useful lineage, but it cannot express independent Instagram/Facebook placements, repeated publication occurrences or multiple GHL sends without extension.
- The form captures a day, rather than a precise publication timestamp and separate verification timestamp.
- Manual and provider-confirmed evidence are not represented as distinct publication-verification methods.
- Current publication capture and calendar scheduling are separate: capture does not directly transition the calendar entry to `published`. Calendar reads can instead warn that an entry's piece is already marked published. Publication tracking needs a unified projection so a confirmed placement no longer appears simply overdue.
- Capture may invoke embedding/learning work. A minimal operational published mark should not depend on that work succeeding; commit publication evidence first and handle optional learning separately.
- Editing currently makes a new pack version and resets whole-pack approval. With approval retired, editing must not erase the historical fact that an older version was published. The interface should identify the published version and whether the newer draft differs.

The existing manual path is a starting point, not a complete implementation of the proposed tracking system.

## 3. Two methods, one publication history

Use one logical publication occurrence per piece, intended platform/account and scheduled occurrence. Manual marking and automatic verification attach evidence to that same occurrence rather than creating competing duplicate records.

Keep two concepts separate:

| Publication state | Verification evidence |
| --- | --- |
| Unscheduled / scheduled / published or sent | None yet / manually reported / provider confirmed |
| Scheduled and past due | Not found yet / ambiguous candidate / check unavailable / explicit provider failure |

Suggested display examples:

- **Published · Marked by Gisselle · 10 Nov, 11:12**
- **Published · Verified on Instagram · View post**
- **Sent · Verified in GHL · View campaign**
- **Overdue · Publication not confirmed**
- **Verification unavailable · Instagram connection needs attention**

A manual mark should count as published in the operational view, with its evidence badge visible. Automatic confirmation can add provider evidence later. An unsuccessful automated check must not silently undo a person's assertion: show the discrepancy for review. Corrections or a mistaken manual mark need an audited reversal, not deletion of the old history.

No match is not proof of non-publication. A token error, incomplete listing, deleted post, time-window mismatch or edited caption can all prevent detection. Keep an explicit provider-reported failure separate from an inconclusive search.

### Evidence to retain

Piece/brief lineage; referenced pack version and content hash; intended platform and account; schedule entry and revision; planned time; actual publication time; manual actor and marking time; external object ID/URL; verification source and check time; last check result and a short evidence summary. Keep account credentials outside these records. Store only the external data necessary for matching and audit.

Manual evidence should ask for platform/account and actual date/time, with a post URL or campaign reference where available. Do not require every manual mark to have a URL: email campaigns may not have a public permalink. Final published copy can remain an optional expandable detail. Do not silently treat the Atelier draft as the exact copy sent when it has not been captured from the platform or confirmed by a person.

## 4. Automatic verification feasibility

### Instagram — feasible with authenticated account access; matching is conditional

The official Instagram API supports professional accounts and retrieving account media. This establishes a supported integration route, not proof that WIA's particular account, app and permissions are ready. Meta's [official Instagram API collection](https://www.postman.com/meta/instagram/collection/6yqw8pt/instagram-api) is the primary reference used here. Direct Meta documentation fetches were rate-limited during this analysis, so the exact login route, read scopes and returned fields must be checked in the account proof of concept rather than assumed from older examples.

Use the account's authorized media listing or a known media object ID. Confirm the fields needed for matching and evidence in that proof: account identity, object ID, publication timestamp, caption, media classification and permalink, including carousel/Reel behavior. Use read access; this feature does not need permission to publish content itself.

Because publishing happens outside Atelier, Atelier does not automatically receive the external post ID. This is the central problem. The strongest path is storing a platform object ID, URL or tool-side correlation reference for the intended piece, then reading its actual publication result. When that is unavailable, search recent authorized media and produce candidate matches.

Candidate matching should combine the intended account, publication window, format and distinctive caption text. Scheduled time or generic title alone is insufficient. A Reel's internal working title or spoken script may not appear in the caption. Reused captions, changed hashtags, multiple similar posts and edited copy can make a match ambiguous.

Use exact provider identity matches for automatic confirmation. Any content-based automatic matching needs measured precision on real examples and an agreed conservative acceptance rule; initially present candidates for confirmation. Do not use an LLM's confidence as publication proof. Detecting a published object also does not prove that every frame, slide or spoken line matches the draft.

**Assessment:** API-backed detection is feasible in principle; reliable unassisted matching of externally published pieces is not yet demonstrated. Personal/unconnected accounts or unavailable permission paths can block it. Avoid relying on logged-in browser scraping as the normal checker.

### GHL email campaigns — a strong documented route, subject to access and linkage

HighLevel now documents listing campaigns and reading a campaign by ID, including subject and statuses such as sent, scheduled, processing and failed. Its statistics API separately exposes sending and delivery metrics. See [campaign detail](https://marketplace.gohighlevel.com/docs/ghl/emails/get-email-campaign/) and [campaign statistics](https://marketplace.gohighlevel.com/docs/ghl/emails/get-campaign-stats/).

Store the GHL location and campaign/source ID associated with the Atelier email. Then verify the identified campaign's provider-reported sending state and available send evidence. A draft, scheduled campaign, template or rendered email body is not proof that it was sent. Neither is an unrelated campaign with the same subject.

Define operational completion using the campaign's finished send state and intended audience/batch semantics, not a single test recipient or a positive open count. A partially processed batch should be shown as sending/partial, not silently complete. **Sent** and **delivered to every recipient** are different claims; opens/clicks are engagement measurements, not the publication criterion.

**Assessment:** document-supported and relatively straightforward with a stable campaign association. Live account permissions, actual field semantics and send timing evidence remain unverified.

### GHL workflow emails — possible, but requires a separate proof

The statistics API supports workflow sources and an optional workflow action identifier. That helps identify an email step, but lifetime workflow statistics with positive sends do not prove that the intended email went out during yesterday's scheduled occurrence.

Require a specific workflow/action association plus occurrence-level, time-bounded send evidence. The proof must establish whether authorized message records, counters captured before/after the window, or a supported event integration provide adequate evidence for WIA's actual sending method. HighLevel's [OutboundMessage event documentation](https://marketplace.gohighlevel.com/docs/webhook/OutboundMessage/) includes email events, but coverage for these particular campaign/workflow sends must be demonstrated, not inferred. A generic outbound event is also not an end-to-end delivery guarantee.

A recurring workflow is often continuous per-contact automation rather than one audience-wide publication. Before choosing a status rule, establish what the Atelier schedule means for such a workflow: activating a step, executing one batch, or confirming sends to a defined cohort. If there is no finite intended occurrence, a blanket “email published” status is misleading.

**Assessment:** conditional. Do not promise full workflow verification based on aggregate statistics alone. Start with campaigns if workflow-level evidence remains unclear.

### GHL Social Planner — not the primary route for this workflow

HighLevel documents [social posts with publishing statuses](https://marketplace.gohighlevel.com/docs/ghl/social-planner/get-post/). This would be useful if posts were published there. The owner confirmed otherwise, so GHL-only social verification is not sufficient. Even if another tool reports success, distinguish that tool's report from direct confirmation that the Instagram media object exists.

## 5. Next-day checking behavior

Interpret “next day” as a daily reconciliation of the previous calendar day's schedules in the configured publishing timezone, not a fixed 24 hours after each scheduled timestamp. A proposed starting point is 09:00 local publishing time the following day, with a later bounded recheck for delayed results. This timing is a proposal, not a configured job.

For each due occurrence:

1. Confirm the intended account, latest schedule revision and whether the occurrence was cancelled/rescheduled.
2. Query the appropriate provider, reusing account-level listing results across pieces and handling pagination and rate limits.
3. Prefer exact linked identifiers; otherwise evaluate candidates conservatively.
4. Record confirmed, ambiguous, not-found, unavailable or explicit failure evidence independently of any manual mark.
5. Update the publication/calendar projection without duplicating an already recorded manual/provider publication.
6. Surface unresolved due pieces with direct links for manual follow-up. Do not send repeated identical alerts every polling pass.

Keep the original planned time and actual published time so late publication is visible. A reschedule invalidates the old pending check; a cancelled occurrence is not treated as missed. Retry authentication/transport failures appropriately without declaring publication failure. A post later deleted does not erase the historical fact of publication; record present visibility separately if monitoring it is desired.

The current scope is email, feed carousel and Reels. If Stories are added later, next-day verification needs a separate retention/expiry analysis; do not assume the same approach applies.

## 6. Consequences for removing Ready to publish

Retiring the button affects more than its label: pack state calculation, decisions/API behavior, edit eligibility, library filters, document exports, calendar warning rules, week summaries and the proposed Slack readiness wording all currently use approval/readiness semantics.

Do not turn every historical pack into `published`, or remove approval checks by treating all packs as already approved. Preserve old readiness decisions as history. Finished content can use a neutral **Generated** or **Available** state, while publication progress is derived independently. Preserve Gate 1 and Gate 2 unless the owner separately changes those stages.

The remaining content findings can be presented for review without a final whole-pack approval action. A publication fact must not be concealed merely because a content warning is unresolved. Policy protections and publication tracking should be reviewed individually rather than indiscriminately removing all validation.

The Slack schedule announcement should become **“Content Atelier has new content pieces scheduled for publishing at the times below.”** Include linked pieces and schedules. It must no longer infer “ready” from a retired approval step, and a future next-day exception message must distinguish not-found evidence from a confirmed failure.

## 7. Recommended sequence and feasibility exit criteria

1. **Agree publication semantics:** active-piece button; manual versus provider evidence; destination-specific completion; email sent versus delivered; next-day timezone/cutoff; correction workflow.
2. **Perform an authorized read-only connector proof:** one known published carousel, one Reel, a known sent campaign and a representative workflow email, plus negative and ambiguous cases. Establish account type, Meta login/permissions, GHL location, granted read scopes and the actual external publishing tool. No API publishing or token changes are necessary for this analysis phase.
3. **Build manual tracking first, once implementation is requested:** promote the existing per-piece action, retire whole-pack readiness, add provenance/corrections, unify calendar status, preserve historical records and prevent version edits from erasing publication facts.
4. **Add exact-reference automated verification:** linked Instagram objects and GHL campaign IDs. Reuse existing background infrastructure, but keep external I/O out of UI save transactions and isolate checks from editorial jobs.
5. **Pilot unlinked candidate discovery:** measure on real known matches and deliberate near-duplicates. Enable automatic matching only where false confirmations are acceptably controlled; leave ambiguous cases for a person.

Proof-of-concept success must demonstrate correct account/object association, actual publication/send evidence with the required time window, a genuine negative case, correct handling of access failure, and idempotent manual/automatic reconciliation. It must also demonstrate that unrelated posts, repeated captions, a sent test email or old workflow send counts do not mark the wrong Atelier piece complete.

Before implementation, produce a data migration and compatibility plan, an inventory of affected readiness consumers and focused tests for publication facts across content versions and schedule changes. The existing Slack plan's delivery table and this publication model should be designed together rather than creating unrelated duplicate status stores. No final schema or automatic-match threshold is approved by this document.

## 8. Limits of this analysis

The repository paths and current manual behavior were inspected. Official Meta/HighLevel documentation supports the external API directions above. No Instagram or GHL account was connected or queried, and no permissions, credentials, webhooks, schedules or content were changed. Therefore this is a docs-backed feasibility assessment, not a claim that WIA's live-account integration already works.
