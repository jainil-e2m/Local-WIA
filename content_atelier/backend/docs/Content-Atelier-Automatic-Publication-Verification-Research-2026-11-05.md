# Automatic publication verification alongside manual marking

**Research date:** 5 November 2026, Asia/Calcutta.  
**Scope:** Instagram carousels/Reels and GHL marketing emails, including campaign and workflow sending. Research and proposed implementation only. No application code, account settings, credentials, subscriptions, workflows, or deployed data were changed during this research.

## Decision

Proceed with a hybrid publication tracker: a person can record publication immediately; a background checker independently gathers platform evidence against the same scheduled occurrence. Automatic checks must also run for manually marked pieces that have not yet received platform evidence.

The practical assessment is:

| Capability | Feasibility | Condition |
| --- | --- | --- |
| Manual mark followed by platform confirmation | Strong architectural fit | Separate the operational publication record from its evidence and learning capture |
| Instagram: verify an explicitly linked published object | Supported in principle | Authorized professional-account access and a verified association to the intended piece |
| Instagram: discover the right external post without a link | Conditional | Actual caption/format availability, distinctive content, account and time-window checks, conservative matching |
| GHL: verify the identified marketing campaign is sent | Strong documented route | Valid sub-account read token, correct campaign/source association, provider status |
| GHL: prove that campaign was sent in the intended schedule window | Conditional | Timestamped send evidence or an observed status transition; campaign update time is insufficient |
| GHL: detect sends from a specific workflow email action | Conditional but plausible | Workflow/action association and time-bounded messages/events or pre/post counters |
| GHL: infer complete workflow distribution from lifetime counts | Insufficient | Requires an explicit cohort/batch completion rule and supporting evidence |
| Guarantee a fully automatic decision for every externally published item | Not established | Ambiguous, changed, missing, or inaccessible records must remain reviewable |

The largest challenge is associating external publications with the correct Atelier piece and occurrence. A daily timer alone does not solve that problem.

## What was actually checked

### WIA's Instagram profile

The supplied [@weddingindustryads profile](https://www.instagram.com/weddingindustryads/) opened successfully in a clean, logged-out browser. Its title identifies Digital Advertising & Funnel Strategists. The visible profile and inspected public profile data did **not** establish whether it is Business, Creator, or Personal. A business-oriented bio is not an account-type check.

No Instagram token/user ID was found under the expected credential names in the local configurations inspected. That does not establish what may exist in Meta Business settings or deployment secrets. No authenticated Instagram account request was made.

Meta documents an authenticated `/me` request with an `account_type` field. That is a definitive check once the owner grants access. The same guide demonstrates account media retrieval and distinguishes the account's identifiers. [Meta: Get started](https://developers.facebook.com/documentation/instagram-platform/instagram-api-with-instagram-login/get-started)

### Existing GHL integration

The adjacent WIA workspace already contains a documented GHL sub-account and a configured Private Integration credential. A single authenticated **GET** to its location endpoint returned **401 Unauthorized** on 5 November 2026. The probe stopped there; campaign, workflow, and statistics requests were not made after authentication failed.

This establishes that the inspected credential was not accepted for that request. It does not establish whether it expired, was revoked, was copied incorrectly, or points to a different integration. It is not a 403 scope diagnosis. No token was displayed, rotated, replaced, or copied into this report. Sanitized results are stored locally in `.qa/publication-api-research.sanitized.json`.

### Earlier integration notes

Relevant prior work exists in `../frontend/corpus/instagram-app-setup.md`, `../frontend/corpus/ghl-scopes.md`, and `../landing-versions/corpus/`. These are useful discovery aids, not proof of a working current connection.

The old Instagram helpers hard-code `graph.facebook.com/v21.0`, while the setup notes also describe Instagram Login. Those hosts/token flows must not be mixed. Some old GHL probes use candidate paths that differ from the current published email APIs. Do not interpret an old guessed-path 404 as proof the current feature is unavailable, or execute the old fetchers unchanged.

Official Meta pages initially failed in the search fetcher but loaded in a clean browser. This report uses those official pages, current HighLevel documentation, and repository inspection. Third-party tutorials were not used as the basis for API guarantees.

## Instagram: access, evidence, and matching

### Connection choice

The [Instagram Login overview](https://developers.facebook.com/documentation/instagram-platform/instagram-api-with-instagram-login/) supports professional accounts without requiring a linked Facebook Page. The media reference lists `instagram_business_basic` for reading through that route; publishing permissions are unnecessary for this feature. The Facebook Login route uses its own host, credentials, and Page permissions. Meta also documents Unified Login; an existing compatible connection can be evaluated rather than introducing another login setup. [Meta: Media reference](https://developers.facebook.com/documentation/instagram-platform/reference/instagram-media)

For accounts the app owns/manages and adds in its dashboard, Meta documents Standard Access; serving accounts outside that relationship requires Advanced Access. Therefore App Review should not be described as either universally required or universally avoidable. Instagram Login's long-lived tokens last 60 days and can be refreshed while valid and at least 24 hours old. Persistent token maintenance is part of implementation, not a one-time `.env` entry. [Meta: Business Login](https://developers.facebook.com/documentation/instagram-platform/instagram-api-with-instagram-login/business-login)

### What can count as publication evidence

Read the authorized account's published media, retaining provider ID, account identity, permalink, timestamp, and supported format fields. The reference distinguishes media types from publishing surfaces; it marks `media_product_type` and the `caption` field description as Facebook-Login-only. Treat this as a route-specific capability constraint to test, not a universal caption-reading guarantee. A missing video download URL does not prove the post is absent. [Meta: Media reference](https://developers.facebook.com/documentation/instagram-platform/reference/instagram-media)

The Facebook Login user-media reference documents `since`/`until` time-based pagination as well as a recent-media limit, and excludes Stories from the media edge. Verify equivalent filtering on the selected login route; do not copy the older Postman collection's general pagination statements over the current endpoint reference. Follow all relevant pages before declaring no match. [Meta: User media](https://developers.facebook.com/documentation/instagram-platform/instagram-graph-api/reference/ig-user/media)

A publishing container ID is not a published media ID. In Meta's publishing example, a container being `FINISHED` means its upload is ready; publication happens separately and returns a media ID. The verifier should read the resulting publication, not treat a prepared upload as success. [Meta's official API examples](https://www.postman.com/meta/instagram/documentation/6yqw8pt/instagram-api)

### Two association paths

**Exact association:** store the publishing tool's returned media ID, or link a pasted Instagram permalink to an object returned by the authorized account. Confirm the intended account and occurrence, retain the reference, then read provider evidence. A pasted URL alone remains a manual assertion until resolved and checked. Do not assume an Instagram shortcode is the Graph media ID or that identifiers from different login setups are interchangeable.

**Discovery without a link:** collect recent candidate posts, compare supported caption fields against the piece's caption snapshot, and consider format and publication window. Compare a Reel's caption to its caption, not to its internal working title or complete spoken script. Compare a carousel's caption to its caption, not to the concatenated slide copy. Do not automatically assign the only post found yesterday to the only scheduled piece.

Initial matching policy:

1. Require the intended account/placement and a compatible occurrence window.
2. Prefer explicit provider references.
3. For an unlinked piece, use a sufficiently distinctive normalized caption only if the selected connection actually returns it.
4. Require a unique match across both candidate posts and competing scheduled pieces; one post must not silently satisfy two pieces.
5. Keep generic captions, edited captions, near-duplicates, format uncertainty, and collaboration/ownership ambiguity as candidates for a person.
6. Introduce unassisted content matching only after testing on real labeled examples. No arbitrary similarity percentage or LLM confidence score is approved by this research.

The first release can verify that an associated publication exists. It cannot assert every slide image, frame, spoken line, or editorial claim matches the Atelier draft. OCR, video transcription, and visual comparison would be separate requirements and costs.

### Polling and webhooks

Meta's webhook overview lists supported activity and explains that available fields and credentials differ by API setup. It does not establish a universal new-publication notification for every external publishing route. Use scheduled media reconciliation as the initial design; do not make this feature depend on receiving an unproven webhook. Stories, trial Reels, ads-only placements, and collaborator-owned content need separate acceptance rules if added. [Meta: Webhooks](https://developers.facebook.com/documentation/instagram-platform/webhooks)

## GHL: campaigns and workflows require different rules

### Marketing campaigns

The documented campaign detail route is:

```text
GET /emails/locations/{locationId}/campaigns/emails/{campaignId}
```

It supports `emails/campaigns.readonly` through a sub-account OAuth or Private Integration token, with `Version: v3`. Its response distinguishes the campaign `id`, `sourceId`, status, and A/B variation source IDs. Documented status includes `sent`, `processing`, `scheduled`, and failure/cancellation states. Store the corresponding identifiers rather than assuming they are identical. The published response exposes creation/update dates, not a dedicated actual-send timestamp. [HighLevel: Campaign detail](https://marketplace.gohighlevel.com/docs/ghl/emails/get-email-campaign/)

A linked campaign reported sent can support **GHL confirms this campaign was sent**. It does not alone prove it was sent at yesterday's planned time. Do not substitute `updatedAt` for actual send time. For date-specific verification, use a time-bounded observed transition or a correlated provider event. Otherwise show send time as unavailable while retaining when the system checked it.

Campaign discovery supports name search and pagination. This is useful for presenting a selection, not for treating a reused subject/name as a unique identity. [HighLevel: List campaigns](https://marketplace.gohighlevel.com/docs/ghl/emails/list-email-campaigns/index.html)

The statistics route is:

```text
GET /emails/locations/{locationId}/campaigns/stats/{source}/{sourceId}
```

It uses `emails/stats.readonly`, supports campaign/workflow/bulk sources, and exposes sent and delivery-related counters. Its documented query parameter is workflow `subSourceId`; no date-range filter is documented. The sent metric includes more than successful delivery. Counters and provider state must be interpreted separately from engagement or audience completion. [HighLevel: Statistics](https://marketplace.gohighlevel.com/docs/ghl/emails/get-campaign-stats/)

Reject test-send-only evidence, unrelated old campaigns, and mere template existence. Treat A/B variants and drip/batch processing explicitly. Display **Sending** when the campaign is processing; show failure/partial delivery details without pretending that every recipient received the message. Campaign-level completion and per-recipient delivery are different product claims.

If a run completes with no actual sends or no eligible recipients, record that outcome explicitly rather than using it as evidence that the content reached an audience. Conversely, delivery failures need their own display even when the provider confirms the campaign finished sending.

### Workflow email actions

Workflow campaign detail exposes `published`/`draft` and a `subSources` list of individual email-sending steps. Each step's ID can select its statistics. Workflow activation therefore is not email-send evidence, and a workflow ID alone is insufficient when it contains several emails. [HighLevel: Workflow campaign detail](https://marketplace.gohighlevel.com/docs/ghl/emails/get-workflow-campaign/)

Store the GHL location, campaign-wrapper ID, underlying source ID, and action/sub-source ID. Then choose a verification rule appropriate to the send:

- **A one-off planned batch:** require evidence for that specific batch/cohort and an agreed completion condition.
- **An ongoing per-contact workflow:** show verified send activity for the action and bounded period. Do not claim the entire email occurrence is complete from one recipient unless the occurrence was explicitly defined that way.

Possible evidence sources:

| Method | What it can establish | Remaining limitation |
| --- | --- | --- |
| Before/after statistics snapshots for the exact action | An observed increase between two checks | Cannot reconstruct a missing pre-window snapshot; does not prove full audience completion or exact send time |
| Read a known email message | Provider state and message identity/content metadata | Requires message discovery and association to the action/occurrence |
| Receive correlated email provider events | Timestamped send/delivery activity | Requires an event subscription or an adequately authenticated workflow bridge and proven source coverage |

The email-by-ID endpoint documents `conversations/message.readonly`, email status, source values including workflow/campaign, and `dateAdded`. This is a useful readback when an event/tool supplies the message ID; do not rename the message's creation date as an exact sent/delivered timestamp. [HighLevel: Email by ID](https://marketplace.gohighlevel.com/docs/ghl/conversations/get-email-by-id/)

### Event integration: promising, but not a free addition to a PIT

`LCEmailStats` is a documented location-level app event. It includes an event timestamp, message identifier, test flags, delivery information, tags, and a campaigns array. Its example has an empty campaigns array, so it does not guarantee workflow/action correlation in every payload. Confirm the sending provider and capture actual events before relying on it. [HighLevel: LC Email](https://marketplace.gohighlevel.com/docs/webhook/LCEmailStats/)

`OutboundMessage` includes an email example and identifiers, but its existence does not prove full marketing-campaign/workflow coverage or completed delivery. Test its coverage with WIA's actual sending paths. The generic `CampaignStatusUpdate` example is contact-oriented; its name is not evidence it represents modern marketing campaign completion. [HighLevel: OutboundMessage](https://marketplace.gohighlevel.com/docs/webhook/OutboundMessage/), [CampaignStatusUpdate](https://marketplace.gohighlevel.com/docs/webhook/CampaignStatusUpdate/index.html)

HighLevel recommends Private Integrations for internal polling and OAuth apps when webhooks are needed. Therefore a PIT-only polling release is the smaller initial setup; event subscriptions are a separate integration choice. [HighLevel: Authorization](https://marketplace.gohighlevel.com/docs/Authorization/authorization_doc/index.html)

A helper workflow forwarding genuine delivery events is another candidate, but it must expose the needed identifiers. The current trigger catalog mentions delivered events while an older detailed Email Events article omits them. Confirm the actual tenant's filters/payloads instead of promising a no-OAuth workaround. A generic webhook action placed after Send Email proves a workflow reached that action, not delivery. [HighLevel: Trigger catalog](https://help.gohighlevel.com/support/solutions/articles/155000002292-a-list-of-workflow-triggers), [Email Events detail](https://help.gohighlevel.com/support/solutions/articles/155000002678-workflow-trigger-email-events)

For an OAuth webhook receiver, validate raw-body signatures using current `X-GHL-Signature`/Ed25519 guidance, deduplicate deliveries, persist receipt before acknowledging it, and process asynchronously. Never acknowledge and discard an unpersisted event needed for verification. [HighLevel: Webhook guide](https://marketplace.gohighlevel.com/docs/webhook/WebhookIntegrationGuide/index.html)

## How automatic and manual records coexist

Use one publication occurrence with independent evidence. Manual marking and provider checking must not compete to overwrite a single boolean.

| Situation | Calendar result | Evidence/history |
| --- | --- | --- |
| User manually marks the piece | Published / Sent · Manual | Actor, marking time, reported publication date/time, optional reference |
| Provider later confirms the same occurrence | Published / Sent · Verified | Keep the manual event and append provider evidence |
| Provider confirms before a manual mark | Published / Sent · Verified | No redundant manual mark is required |
| Search finds no match after a manual mark | Published / Sent · Manual | Add an unconfirmed-check result; do not undo the person's report |
| Search finds no match without a manual mark | Publication not confirmed | Retry or request review; do not label a definite publishing failure |
| Credential/API request fails | Verification unavailable | Show a connection issue; publication state remains unchanged |
| Multiple credible matches | Needs confirmation | A person chooses the exact publication; retain that association decision |
| Explicit provider failure | Provider reported failure | Preserve any manual assertion and surface the discrepancy |
| User corrects a mistaken manual mark | Recompute from remaining evidence | Audited reversal; provider-confirmed evidence is not silently erased |

Each provider claim needs an evidence level: object exists, send activity observed, campaign finished sending, or recipient delivered. The UI must not collapse these into a stronger claim than the evidence supports. Provider timestamps, manually reported times, first-observed times, and check times are separate fields.

Keep the existing calendar/pack layout, show compact evidence badges, and put details behind the existing publication dialog. **Do not reintroduce the pack-wide publication count/progress bar the owner removed.** The manual action remains available while automatic verification is unavailable or inconclusive.

## Necessary changes to the current data path

Repository inspection found important constraints beyond adding a connector:

1. `knowledge/capture.py::record_pack` uses `pack:{brief_id}:{piece}` as its identity, rejects a different final for that key, and performs embedding work before insertion. It cannot directly represent independent destinations, repeated sends, or provider evidence appended to an existing manual mark.
2. `packs/versions.py::published` routes manual recording through that capture path. Calling the same endpoint with provider text can conflict with the human's final and does not make the actor/source distinction clear.
3. `packs/views.py::published_marks` returns day, URL, actor, and pack lineage, but has no provider-verification provenance contract.
4. `calendar/service.py::entry_view` can warn that a piece is already published rather than project the occurrence as completed. The local UI currently reads pack marks to display manual status.
5. The current manual contract stores a date, not an exact actual-publication timestamp. Migration must preserve that date's granularity rather than invent an exact time.
6. Existing periodic scheduling and RQ dispatch can be reused, but there is no working Instagram/GHL verification adapter in this backend. Adjacent corpus-fetch scripts are not deployed operational connectors.

Proposed additions, with final names/schema to be designed during implementation:

- **Publication occurrence:** logical piece lineage, intended account/destination, schedule identity/revision, immutable copy/version association, planned timestamp, actual timestamp if known, and effective operational state.
- **Append-only evidence:** manual reports, provider records, human-confirmed associations, and corrections. Keep provider object/message IDs, timestamp semantics, content/reference hashes, actor/source, and observed time.
- **Verification attempts:** outcome, coverage/window, connection health, retries, last/next check, and safe diagnostic information. A no-match attempt is not proof of non-publication.

Use uniqueness and transactional reconciliation for manual/provider races. A schedule moved before publication changes its pending verification revision; it does not erase the old revision. A repeat publication after completion is a new occurrence. Preserve publication against the version actually published when later edits create a new pack.

Commit operational facts independently of optional learning/embedding jobs. An automatic match must not copy the entire Atelier draft into a field claiming it was the exact observed published text: Instagram usually supplies metadata/caption, not a complete Reel transcript or all carousel slide text.

## Minimal configuration that is realistic

| Area | Initial requirement | Additional setup only when justified |
| --- | --- | --- |
| Instagram | Professional-account access, matching Meta app/login route, read token and account ID; secure refresh storage | App review for the relevant access relationship; Page wiring only for a route that needs it |
| GHL campaigns | Valid location-scoped token with campaign/statistics read scopes and a linked campaign | Message-read scope only if needed for occurrence-level evidence |
| GHL workflows | Workflow/action association plus a tested evidence source | OAuth event subscription or a verified workflow event bridge if polling is insufficient |
| Atelier | Verification enable flag, publishing timezone, next-day cutoff, retry horizon, account-to-piece mapping | Multi-account routing when more accounts are introduced |

A selected GHL campaign is a per-piece association, not a new global secret. Prefer a campaign picker or publisher-returned ID so a person does not have to paste an opaque ID on every verification attempt. For Instagram, accept an optional permalink and use discovery to reduce manual linking where precision is demonstrated.

Private Integration scopes can be edited without issuing a different token, but the present 401 must first be resolved. Do not rotate a shared token casually; other WIA tools may rely on it. [HighLevel: Private Integrations](https://marketplace.gohighlevel.com/docs/Authorization/PrivateIntegrationsToken/index.html)

No new automation platform, paid AI matcher, or publishing service is intrinsically required. Reuse the existing scheduler, Postgres, and background-worker infrastructure. Token refresh needs secure mutable storage; putting a long-lived token in static environment configuration alone does not make Instagram maintenance-free.

## Next-day reconciliation

Suggested behavior, not configured behavior:

1. At 09:00 in the **configured publishing timezone**, claim a reconciliation pass for prior-day and still-unresolved due occurrences. The preview's Asia/Kolkata setting is not evidence of the production timezone.
2. Include manually marked but unverified occurrences. Exclude cancelled/replaced pending revisions, not every already-published item indiscriminately.
3. Fetch account media once per required window and reuse it across that account's pieces. Follow pagination; record whether coverage is complete. Fetch GHL data against explicit linked sources.
4. Revalidate the occurrence revision before applying results. Store evidence and derive the display state transactionally.
5. Retry inconclusive/temporarily unavailable results on a bounded policy; a later pass must catch work missed during downtime. Authentication failures need a connection alert rather than repeated false publishing failures.
6. Suggested starting recheck: 15:00 local time, with an explicitly agreed later horizon. This is a proposal, not a claim that 6 or 48 hours is always sufficient for every email batch.

Store UTC instants with the relevant IANA timezone and calculate calendar-day boundaries correctly across DST. Existing `periodic.day()` is UTC-based; passing `hour=9` would not implement 09:00 in an arbitrary publishing timezone. Keep external API waits outside browser save requests and editorial-generation transactions.

Use request timeouts and provider-specific backoff. HighLevel's documented default limits are 100 requests/10 seconds and 200,000/day, with different sharing rules for PITs and OAuth apps and authoritative response headers. Actual limits may differ. Do not copy the corpus helper's historical Instagram limit as a universal quota. [HighLevel: Rate limits](https://marketplace.gohighlevel.com/docs/other/rate-limits/index.html)

## Proof and implementation sequence

### Gate A — establish access and evidence, without changing publishing behavior

Obtain a valid read-only GHL connection and an authorized Meta read connection. Definitively read Instagram account type, verify the authorized account is the supplied WIA handle, and list a known Carousel and Reel. Verify the chosen Meta route's caption/format fields and time-window/pagination behavior.

In GHL, read a known sent marketing campaign and one relevant workflow action. Distinguish provider IDs and sources, test statistics scopes, determine the sender provider, and establish whether message-level evidence is available. No campaign is sent or workflow modified for this gate.

Exit with actual response shapes and a documented supported-capabilities list. Current result: GHL authentication fails with the inspected token; Instagram access is not connected locally. The documentation-backed routes are not yet live-account validated.

### Gate B — shared publication/evidence foundation

Design migration and compatibility for legacy manual marks, schedule occurrences, pack versions, provenance, corrections, and optional learning capture. Keep the manual UI usable. Add provider/evidence fields to the generated API contract and project one truthful calendar status from them.

### Gate C — exact-reference verification first

Add read-only adapters for linked Instagram media and GHL campaigns. Keep publication time unknown where the provider does not supply it. Run in shadow mode against a labeled history before allowing automatic state changes.

### Gate D — discovery and workflow evidence

Evaluate unlinked Instagram caption candidates on actual posts with near-duplicates. Add automatic association only where false matches are controlled. Implement workflow snapshots or event ingestion only after proving action/occurrence correlation and agreeing what completion means for that workflow.

### Gate E — gradual enablement

Enable one account/source at a time with a verification feature flag. Turning the checker off must leave manual records and evidence intact. Do not silently migrate every old manual mark to provider-verified status, or manufacture historical checks for periods not observed.

Acceptance scenarios must include:

- Correct Carousel/Reel and a deliberately unrelated post with a similar caption.
- One external object competing with two scheduled pieces; multiple genuine candidates; edited captions and missing format fields.
- A manually marked piece later verified, an automatic result arriving first, and both arriving concurrently.
- Token expiry/401, scope failure/403, unsupported field, 429, partial pagination, timeout, and deletion after prior verification.
- Reschedule/cancel/new pack version while a checker is running; repeated publications and duplicate webhook/job delivery.
- Sent campaign versus scheduled/processing/failed campaign, test send, A/B variants, and unknown actual-send time.
- Workflow active with no sends, historical sends only, a new event in the correct action/window, incomplete audience, zero eligible recipients, and uncorrelated provider events.
- Publication marking still works when embedding/learning is unavailable; automated evidence never overwrites the human's captured final text.

No universal matching threshold, fixed rollout date, or unconditional workflow-completion promise is justified yet. The next concrete milestone is Gate A, followed by the data/evidence foundation—not a timer that guesses publication from a title and yesterday's date.
