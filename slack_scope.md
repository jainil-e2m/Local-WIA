# Slack intake scope — Maintained Client Knowledge Base

Review date: **19 October 2026 (IST)**.

## 1. Purpose and feasibility verdict

Verify whether actual Slack data can support the information and workflows shown in the existing Knowledge Base frontend. This review covers Slack only. The other sources will be reviewed individually using the same source → retrieval → evidence → frontend mapping approach.

**Verdict: Slack can supply the communication, handoff, request, approval, and reported-delivery evidence needed by the frontend. Current API access is verified for six channels. Complete portfolio coverage, automatic action extraction, dependable acknowledgement rules, and independently verified completion are not yet established.**

The six frontend clients and their excerpts are explicitly fictional. Feasibility means real source material supports comparable information and behavior; it does not mean finding those fictional clients or reproducing their invented dates and numbers. No frontend data was replaced, and no Knowledge Base production ingestion service was implemented in this review.

## 2. Verification performed and evidence retained

### Live read-only probe

Executed 19 October 2026, **16:19:45–16:20:19 IST**. The existing bot token authenticated to the Wedding Industry Ads workspace. The first sandboxed attempt could not resolve Slack; the subsequent network-enabled attempt succeeded. This was an environment restriction, not a rejected Slack credential.

| Check | Observed result | Limit of the finding |
| --- | --- | --- |
| `auth.test` | Passed; existing bot credential is usable. | Does not establish future availability or every workspace permission. |
| `users.conversations` | One complete membership page: seven private channels, including the test channel. | Inventory is the bot's membership, not the complete WIA channel/client roster. |
| `conversations.history` | Passed for all six real channels; 15 returned message objects per channel, 90 total. | Bounded samples, not a full current backfill. Every channel reported more history. Objects may include app/system posts. |
| `conversations.replies` | One thread tested per channel; all six passed, returning 11 replies in total. | Each sampled thread had no further page; large-thread pagination was not exercised live. |
| `chat.getPermalink` | Passed for one message in each channel. | Obtaining a URL does not guarantee a particular dashboard user can open it. |
| `users.info` | One non-bot author resolved with a readable name. | Display name does not establish staff/client role, business identity, or account ownership. |
| Reactions in history | Present in all six channel samples. | `reactions.get` was not separately called. Meaning and actor-specific acknowledgement require rules. |
| `files.info` and authenticated download | A native PNG returned successfully; 41,661 bytes matched the declared size and content type. | One small attachment only; no OCR, video processing, or external document access was tested. |

Evidence: [live_probe.json](knowledge_base/wia-knowledge-base/verification/slack/live_probe.json). It contains method outcomes, counts, identifiers, source permalinks, and observed scopes; it contains no token or new message bodies.

### Historical archive audit

Read the saved raw payloads, rather than relying only on the old index. Excluded `wia-ai-team-testing` throughout.

- **1,070 parent messages + 1,594 replies = 2,664 unique messages** across six channels.
- Saved `reply_count` totals equal the 1,594 saved replies; no repeated message timestamps were found within the audited channels.
- **209 locally downloaded file occurrences** and **63 over-cap file occurrences** appear in the saved manifests. These are occurrence counts, not a new physical-file integrity audit.
- All six channels have reactions. Five contain `edited` metadata. Native files, external references, human messages, bot messages, and some attachment-only posts are present.
- These checks establish consistency of the saved sample. They cannot establish that the original collection captured every historically existing message, deletion, revision, or channel.

Evidence: [archive_audit.json](knowledge_base/wia-knowledge-base/verification/slack/archive_audit.json), [original archive index](frontend/corpus/slack/_INDEX.md). The audit's regex-selected excerpts are **review candidates**, not validated actions or sentiment labels. The manually assessed cases in section 7 provide the semantic findings.

## 3. Which Slack channels are involved?

| Channel | Current history/thread access | Archived parents / replies | Archived coverage, UTC dates | Role in the Knowledge Base |
| --- | --- | --- | --- | --- |
| `c_dogwoodreserve` | Passed / passed | 103 / 208 | 7 May–24 Sep 2026 | Client setup, requirements, handoffs, asset references, reported delivery and issues. |
| `c_funktasticproductions_djhybrid` | Passed / passed | 248 / 371 | 5 May 2025–24 Sep 2026 | Multi-brand account context, onboarding, draft reviews, decisions and commitments. |
| `cfpfu_luxurytravelboutique` | Passed / passed | 188 / 245 | 14 May 2025–4 Sep 2026 | Client communication, delivery and follow-up context. |
| `googlesearchaccelerator` | Passed / passed | 152 / 221 | 24 Oct 2025–24 Sep 2026 | Internal programme work, team discussions, posted meeting context, references to multiple clients. |
| `metaadsaccelerator` | Passed / passed | 347 / 514 | 22 Nov 2024–24 Sep 2026 | Internal programme/campaign work and team updates across accounts. |
| `social-proof-and-results` | Passed / passed | 32 / 35 | 11 Jun 2025–14 Aug 2026 | Relayed feedback, screenshots and results, subject to account mapping and attribution checks. |
| `wia-ai-team-testing` | Membership only; content excluded | Excluded | Not evidence | Synthetic testing material; never use for client facts, health or results. |

The dated archive is not current state: live samples include newer messages in several channels. Newer than the archived latest date does not necessarily mean the channel has content through today.

Only **three dedicated account channels** are presently included. The two Accelerator channels are not verified client discussion communities: archived author names include WIA staff and programme-building discussions. Do not assume a message there is written by a programme participant or belongs to every participant. Other team/client channels and DMs are outside this verified intake coverage.

## 4. Data required from Slack and how to obtain it

| Required data | Retrieval / representation | Intended use and important qualification |
| --- | --- | --- |
| Workspace and channel identity | `auth.test`, paginated `users.conversations`, stable workspace/channel IDs; channel name/private/archive metadata. | Bind evidence to its workspace and channel. Names can change; membership is not the canonical client roster. |
| Parent message content | Paginated `conversations.history`: `ts`, `text`, `blocks`, `subtype`, `user`, `bot_id`, available metadata. | Requests, updates, proposed decisions, links and statements. Preserve raw wording before generating a summary. |
| Full thread context | Paginated `conversations.replies` for every relevant root, including open-action threads. | Acceptance, clarification, corrections and later status. Include each reply's own author and timestamp. |
| Author and mentions | `users.info`, cached by ID; preserve `<@USER_ID>` mentions. | Propose an owner and identify a speaker. A mention may notify multiple people; it does not prove assignment or acceptance. Staff/client roles require a reviewed roster. |
| Reactions and known actors | History/reply metadata; `reactions.get` when needed for a specific decision. | Potential acknowledgement under an agreed rule. Preserve emoji, count and available user IDs; count alone cannot identify the responsible person. |
| Attachments | Message `files`; `files.info` and authenticated native-file download where allowed. | Inspect briefs, screenshots and delivery evidence. Record skipped/unavailable files and content type; images may need OCR and human review. |
| External source URLs | Parse message text, blocks, attachments and file metadata. | References to Drive, ClickUp, Fathom, Zoom, LeadLock, Dubsado, websites and deliverables. A Slack link does not grant access to the target. |
| Message provenance | Stable message IDs/timestamps, `chat.getPermalink`, root/reply association, retrieval time. | Source library, evidence drawer, chronology and claim-level citations. Preserve exact timestamp strings; avoid floating-point IDs. |
| Corrections, edits and removals | Preserve observed `edited` metadata; revisit active threads and relevant history. Consider message edit/delete events for reliable ongoing reconciliation. | Supersede outdated claims and flag evidence no longer available. New-message-only polling cannot guarantee discovery of all old edits or deletions. |

**Not direct Slack fields:** client health, sentiment, weekly priority, action title/status/owner/due date, acceptance, and verified resolution. These are derived interpretations or human decisions, supported by source messages and other systems where necessary.

### Currently observed permissions

The token reported `channels:history`, `channels:read`, `groups:history`, `groups:read`, `files:read`, `reactions:read`, and `users:read`. The six verified source channels are private, so the relevant private-channel access and membership matter. The existing token succeeded for channel threads; a different token/install must be tested rather than assumed equivalent.

No posting, reaction-writing, membership changes, new app installation, or DM-reading capability is required for this read-only feasibility scope. Additional source channels would need their intended scope and access established. See the official [history](https://docs.slack.dev/reference/methods/conversations.history/), [thread replies](https://docs.slack.dev/reference/methods/conversations.replies/), [reactions](https://docs.slack.dev/reference/methods/reactions.get/), [files](https://docs.slack.dev/reference/methods/files.info/), and [permalink](https://docs.slack.dev/reference/methods/chat.getPermalink/) references.

## 5. Retrieval and maintenance approach

1. **Inventory and mapping:** compare the bot's reachable channels with the real WIA client roster and intended internal channels. Maintain explicit client/channel/brand aliases and staff/client identity mappings. Discovery must not silently opt every reachable channel into ingestion.
2. **Historical bootstrap:** import the preserved archive without overwriting it, then backfill the currently accessible history and relevant threads. Deduplicate by `(workspace_id, channel_id, message_ts)`; keep parent/reply associations. Preserve gaps and archive provenance.
3. **Ongoing reads:** poll the agreed channels with cursors and a stored checkpoint, an overlap window for reconciliation, and explicit collection status. Advance a completed-window checkpoint only after its required pages/threads succeed. Do not classify an API failure as an empty channel.
4. **Old active threads:** re-read roots attached to unresolved actions even if their parent predates the new-message window. A reply to an old request can resolve it; a new-root-only scan can miss it. A broader reconciliation schedule or event intake is needed for other historical changes.
5. **Files and links:** retain manifests and source references, retrieve relevant native attachments with bounded sizes, validate bytes/content type, and route external documents to their own connector. Do not bulk-download meeting videos merely because Slack references them.
6. **Extraction and review:** resolve entities, distinguish drafts from sent content, and propose decisions/actions/signals with per-field citations and confidence. Read corrections across the whole thread; route ambiguous client, owner or date to review.
7. **Derived record update:** recompute affected summaries and actions when evidence changes; retain prior values and the reason for supersession. Keep backend-generated recommendations distinct from explicit client requests.
8. **Freshness and gaps:** persist last attempt/success, bounds covered, page completion, thread completeness, missing files, unresolved mappings and source errors. Display these separately from relationship health.

Polling is a proposed starting approach, not a service implemented by this review. Existing scripts establish API feasibility, not a production job schedule. The current probe deliberately uses 15-message samples and bounded calls. Production must honor cursor pagination, HTTP 429 and `Retry-After`; rate limits depend on app distribution category. Slack documents different treatment for internal customer-built versus commercially distributed non-Marketplace apps. See [current history limits](https://docs.slack.dev/reference/methods/conversations.history/) and [Slack's clarification](https://docs.slack.dev/changelog/2025/06/03/rate-limits-clarity/).

### History retention

Older project notes anticipated a free-plan retention cutoff. **This review did not verify the current workspace plan or retention configuration.** The live probe returned some message dates older than 90 days; do not repeat an assumption that current access is universally limited to 90 days. Slack's published free-plan policy limits visible history to 90 days and describes deletion beyond one year, subject to actual workspace settings. Retain the already exported evidence and verify current coverage before promising history from onboarding. [Official plan limitations](https://slack.com/help/articles/27204752526611-Feature-limitations-on-the-free-version-of-Slack)

## 6. Mapping to the existing frontend

Frontend source: [data.ts](knowledge_base/wia-knowledge-base/frontend/src/data.ts), [types.ts](knowledge_base/wia-knowledge-base/frontend/src/types.ts). All sample rows remain fictional.

| Frontend data / screen | What Slack supports | Feasibility and remaining condition |
| --- | --- | --- |
| `EVIDENCE`: `rosewood-slack`, a follow-up handoff and test-inquiry report | Delivery updates and later follow-up in account threads. | **Supported evidence pattern.** Real request/correction/completion exchanges exist; the specific Rosewood narrative is fictional. |
| `EVIDENCE`: `magnolia-slack`, a client posting a page revision with a specialist reply | Page/copy reviews, updates, links and responses. | **Partially supported.** Team-side review patterns exist; the sample's direct client authorship in an Accelerator channel is not established. Preserve actual speaker/relayed attribution. |
| Actions `a4`, `a5`, `a10` and client Commitments | Proposed action, actor, request, response, reported status and next step. | **Conditional.** Due date/owner must be explicit or reviewed. A promise does not establish “In progress”; “created” can support reported “Done,” not independent verification. |
| Action register: acknowledgement, overdue, waiting on client | Explicit acceptance by the mapped owner, agreed dates and unresolved requests. | **Conditional.** Unread/seen state is not available through this scope. Reaction meanings and staff/client roles must be defined. Overdue requires an actual agreed deadline. |
| Client engagement-history lanes | Dated communications, commitments, approvals and reported delivery with source links. | **Supported.** A message about completion is a report of delivery; a Slack notification about a meeting is not the authoritative meeting record. |
| Client “Now,” `summary`, `focus`; dashboard open loops | Current context synthesised from mapped messages and actions. | **Conditional derivation.** Reconcile other sources and label suggested priorities. Silence in a partial source window does not establish an unanswered request. |
| Call prep `call-rosewood`, `call-magnolia`: context, needs, agenda, opportunity, evidence | Recent account context and outstanding work; inputs to a suggested agenda. | **Partial contribution.** Calendar supplies schedule/host/type; meetings/documents provide additional facts. Slack alone does not generate a reliable calendar. |
| Client handover brief | Communication history, unresolved promises and links to background/deliverables. | **Partial contribution.** Full business background and approved positioning still need other sources. |
| Health & sentiment: `health`, `sentiment`, supporting quote | Explicit client words where present; staff reports and support concerns as separately attributed signals. | **Conditional interpretation.** Staff gratitude or an AI summary must not be displayed as the client's feelings. No Slack activity is not evidence of dissatisfaction. |
| Client Profile: audience, differentiator, voice, goals, contact, engagement start | References and occasional explicit corrections/background. | **Supplementary only.** Slack user profiles do not establish the complete business profile or contract start date. Approved documents/client master records remain necessary. |
| `lastTouch`, `activity[]`, activity sparklines | Timestamps and counts of included messages under defined bins. | **Conditional.** Define team update versus direct client contact; exclude system noise. Label Slack communication activity, not lead performance or satisfaction. |
| `coverage` percentages | Actual per-source time/channel/file coverage and missing-input records. | **Not established as a percentage.** Mock 78–96% indicators have no agreed denominator. Do not infer completeness from message volume. |
| Source library and EvidenceDrawer | Original wording, author, date, channel, thread and permalink. | **Supported; contract/UI additions needed.** Preserve per-message attribution when showing a combined thread. |
| Connections: sample Slack `records: 2`, preview status | Actual connector read health, source/evidence counts and last successful collection. | **Supported metadata pattern.** The two sample excerpts are not a real channel/message count. Define the counting unit before replacing them. |
| Invoices & terms, attendance, live lead/booked-client metrics | Slack can relay notifications, references or assertions. | **Not authoritative from Slack alone.** Verify through Dubsado/Gmail, meeting attendance sources, and LeadLock/reporting respectively. |

### Frontend/backend contract implications

These are implementation requirements identified by the review, not changes made to the UI:

- **Evidence:** add stable workspace/channel/message/thread IDs, `sourceUrl`, observed/edited timestamps, source availability, and speaker role. The current `locator` is only a string; the evidence drawer has no original-Slack-link action. A generated title and `tag` are interpretations, not Slack fields.
- **Multiple citations:** an action may depend on the request, a corrected reply, and later acceptance/completion. Current `Action.sourceId` cannot represent that full trail; `Call.sourceIds` is broader but still needs claim-level provenance for generated statements.
- **Unknown values:** `Action.owner` and `due` are required strings and `acknowledged` is a boolean. Real messages frequently lack a confirmed owner/date; represent unknown/review-required separately from false. Do not substitute the message date or current date as the deadline.
- **Time handling:** keep UTC source timestamps and original timezone context; localise display. “Today,” “tomorrow,” and “end of day” require the author's/business timezone. Existing demo call times in IST do not establish WIA's timezone for a Slack commitment.
- **Approval, delivery and verification:** preserve separate states and evidence. A manually recorded verification also needs verifier/time/check evidence; the preview's Verify button alone is not proof a fix worked.
- **Health quotes:** the current Health view falls back to the first non-background evidence and strips a text speaker prefix. Production must use explicit attribution and distinguish direct client words from internal/relayed reports.
- **Live counts and dates:** replace hardcoded demo counts, health totals, sample readiness and `DEMO_DATE` only when actual source/assessment data exists. Missing data must remain visible.

## 7. Real evidence cases assessed against mock behavior

These are manually reviewed examples from the preserved raw archive. Permalinks provide a Slack reference; availability of these particular historical links to each user was not separately checked today.

| Case | Actual evidence and provenance | What it establishes / what it does not |
| --- | --- | --- |
| SL-E01 — Account setup request | Dogwood, 27 May 2026: a message asks the mentioned teammate to create the missing LeadLock sub-account “ASAP.” [Message](https://weddingindustryads.slack.com/archives/C0B245ATY03/p1779898361901749) | Supports request/possible owner/urgency. “ASAP” is not a dated deadline, and a request does not prove acceptance or account creation. |
| SL-E02 — Corrected requirement and reported delivery | Dogwood, 4 Aug 2026: request for three email templates; the reply corrects “events sequence” to “wedding inquiry sequence” and says templates 8–10 were created. The requester then responds positively. [Request](https://weddingindustryads.slack.com/archives/C0B245ATY03/p1785845700358089), [correction/delivery reply](https://weddingindustryads.slack.com/archives/C0B245ATY03/p1785858560688069) | Supports a corrected requirement and reported template completion, analogous to handoff/commitment samples. Does not prove the workflows were updated or tested. Relative deadline needs timezone resolution. |
| SL-E03 — Approved draft | Funktastic/DJ Hybrid: a multi-reply thread corrects draft wording and ends with Whitney's “approved” on 6 May 2025. [Thread](https://weddingindustryads.slack.com/archives/C08QND0MU5T/p1746466377786289), [approval](https://weddingindustryads.slack.com/archives/C08QND0MU5T/p1746537602316669) | Proves approval of that draft/version in context. Does not prove the email was sent or received. Embedded draft text is not an actual message from the client. |
| SL-E04 — Alias and changing requirements | Dogwood kickoff notes, 27 May 2026, say the venue may change from Meriwether Manor to Dogwood Reserve and list requested workflows/assets. Later replies clarify asset availability. [Thread](https://weddingindustryads.slack.com/archives/C0B245ATY03/p1779907677684179) | Demonstrates why names/brands and later corrections need reviewed mapping. The original “likely changing” statement alone does not prove the rename was final. |
| SL-E05 — Reported technical milestone | Dogwood, 1 Jul 2026: a team member reports A2P approval, with celebratory reactions. [Message](https://weddingindustryads.slack.com/archives/C0B245ATY03/p1782932423290329) | Supports a reported milestone/history entry. Reactions do not independently verify platform status or prove every setup task is complete. |
| SL-E06 — Shared programme thread | Google Search Accelerator archive includes a programme launch action list and staff requests/replies. [Example](https://weddingindustryads.slack.com/archives/C09LQ656BPU/p1761272651170699) | Supports internal work tracking. The channel label does not make the content a client-authored update or assign it to every Accelerator client. |
| SL-E07 — Image-only feedback | Social-proof archive includes posts with no message text and attached images, e.g. timestamp `1755634522.859249`. [Message](https://weddingindustryads.slack.com/archives/C091CPQD8L9/p1755634522859249) | A text-only collector loses potentially useful evidence. Download feasibility is verified, but the image's meaning and quoted speaker still require inspection/OCR; no sentiment finding is established by this case alone. |

Case sources: [Dogwood raw archive](frontend/corpus/slack/raw/c_dogwoodreserve.json), [Funktastic raw archive](frontend/corpus/slack/raw/c_funktasticproductions_djhybrid.json), [Google Search archive](frontend/corpus/slack/raw/googlesearchaccelerator.json), [social-proof archive](frontend/corpus/slack/raw/social-proof-and-results.json). Archive author names are also readable in the corresponding [Dogwood](frontend/corpus/slack/c_dogwoodreserve.md), [Funktastic](frontend/corpus/slack/c_funktasticproductions_djhybrid.md), and [Google Search](frontend/corpus/slack/googlesearchaccelerator.md) Markdown exports.

## 8. Existing implementation: what can be reused?

- [probe-slack.mjs](frontend/corpus/probe-slack.mjs): an earlier read probe. It is evidence of prior work, but its comments and some sampling assumptions should not become the Knowledge Base's production contract.
- [fetch-slack.mjs](frontend/corpus/fetch-slack.mjs): history/reply pagination, author lookup, file handling and archive output. Reuse concepts, not the script unchanged: it enumerates all reachable channels by default, uses loose name matching for explicit targets, does not paginate the membership inventory, and has no durable incremental ledger/checkpoints. Never run it unreviewed over the preserved archive: it writes the original archive paths.
A delivery adapter is not a Slack collector. The KB collector must retain relevant structured bot notifications and attachment-only references, preserve provenance and distinguish bot-generated claims from authoritative events; an unconditional text-only or bot-exclusion filter would lose useful records.

Knowledge Base production implementation should follow [backend_build.md](backend_build.md): thin `routes/`, Slack feature logic under `services/`, source/transport records under `models/`, configuration in `config.py`, durable DB bootstrap in `db.py`, migrations under `sql/migrations/`, and Redis/RQ workers when ingestion jobs require them. These are placements for future code, not a scaffold delivered by this review.

## 9. Verification status and decisions remaining

| Item | Status after this review | Next requirement |
| --- | --- | --- |
| Token, membership, six-channel history and thread reads | **Verified live** | Recheck when token/scopes/membership change. |
| Source permalinks, author lookup, small native attachment | **Verified live on bounded samples** | Generalise with error handling and per-resource availability. |
| Saved archive message/reply consistency | **Verified locally** | Import idempotently without erasing originals. |
| Real requests, corrections, approval and reported-delivery patterns | **Verified by manual source review** | Evaluate extraction against cases SL-E01–SL-E07; automatic accuracy is not yet measured. |
| Whole client portfolio/channel coverage | **Partial** | Obtain real roster and intended channel mapping; only three dedicated account channels are verified. |
| Staff/client/brand identity and shared-channel mapping | **Incomplete** | Establish reviewed aliases and roles; resolve mixed-client summaries at message/segment level. |
| Owner acknowledgement and reaction policy | **Not agreed** | Define acceptance rule. Generic emoji, view counts or another person's reply must not set acceptance. Reaction user lists may be incomplete; absence from a partial list is not proof of no acknowledgement. |
| Due-date and timezone rules | **Not agreed** | Confirm business/author timezone, handling of relative dates and missing dates. |
| Reliable current completion and verified resolution | **Partial evidence only** | Link later task/platform checks or an explicit human verification to the action. |
| Current plan, retention, full backfill and freshness | **Not verified end to end** | Establish accessible bounds and ongoing reconciliation behavior. |
| OCR and externally linked document contents | **Not tested** | Review representative images; defer document bytes/access checks to their actual source. |
| Role-based evidence access in the dashboard | **Not implemented** | Decide who may view each source. Bot access must not automatically grant every dashboard user visibility. |

This scope is sufficient to proceed with Slack connector design and a controlled source-grounded prototype. It is not a declaration that every mock field can be populated automatically for every client today. Agreed additional Client Profile features remain documented in [knowledgebase_changes.md](knowledgebase_changes.md); Slack can contribute links/issues but does not replace their authoritative-source checks.

## 10. Reproducing this source review

From the repository workspace:

```powershell
python knowledge_base/wia-knowledge-base/verification/slack/audit_slack_archive.py
node knowledge_base/wia-knowledge-base/verification/slack/verify_slack.mjs
```

The first command reads the old archive and writes aggregate counts/candidate excerpts into `archive_audit.json`. The second uses the existing token from the process or `frontend/.env` / `.env.local`, reads only the six previously collected channels, and writes `live_probe.json`. Network access is required for the second command. Neither modifies Slack, downloads meeting videos, sends messages, or changes the frontend. A rerun replaces these review reports; retain dated copies if a longitudinal audit is needed.

For each following source, record the same five things: required source fields, actual retrieval/access, inspected evidence and coverage, frontend mapping, and verified versus unresolved conclusions. The other seven source integrations have not been tested as part of this Slack review.
