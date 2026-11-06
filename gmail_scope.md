# Gmail intake scope — Maintained Client Knowledge Base

Review date: **19 October 2026 (IST)**. Required data → retrieval/access → real examples → frontend mapping → unresolved checks. Related source reviews: [Slack](slack_scope.md), [ClickUp](clickup_scope.md), [Drive](google_drive_scope.md).

## 1. Feasibility verdict

**Read-only access to `hello@weddingindustryads.com` is verified. Gmail supports client correspondence, approvals, requests, candidate commitments and support context. Real Dubsado contract-signing and payment notifications confirm the user's proposed financial-event intake route.**

The review made **22 successful Gmail GET requests**, including message bodies, genuine multi-message threads and a PDF attachment byte read. Eleven unique message examples were retained across initial/follow-up samples. This is a bounded feasibility test, not a complete mailbox import or a reconstructed invoice ledger. The three fictional Gmail evidence entries in the frontend are structurally supportable; real client mapping, source interpretation and freshness still require implementation.

**Notification delivery is not tested.** The planned Gmail → Pub/Sub → HTTPS POST setup needs project/topic/receiver configuration, watch registration and a real event-delivery test. No emails, labels, drafts, read states or subscriptions were changed.

## 2. Authorisation and test boundary

- The user completed Google OAuth consent on **19 October, 18:41:15 IST**, granting `gmail.readonly` and `drive.readonly`. The authenticated Gmail profile is the intended `hello@weddingindustryads.com` mailbox.
- Application credentials come from `frontend/.env`; user access/refresh tokens are stored only beneath the Git-ignored `frontend/.data/knowledge-base-google/` directory. They are not written into source reports or browser frontend code.
- A separate token-refresh POST to Google's OAuth endpoint succeeded at **18:45:26–18:45:27 IST**, preserving the refresh token and the two granted scopes. This verifies the refresh operation, not an unlimited token lifetime or resistance to future revocation/admin policy changes.
- The user selected Internal audience. This is appropriate only for users within the Cloud project's parent Workspace organisation; the test did not inspect organisation/admin configuration.
- Mailbox profile reports **33,828 messages and 21,888 threads** at test time. Those are mailbox totals, not clients, useful KB records or a completeness denominator for client history.

OAuth support is shared with the [Drive review](google_drive_scope.md). Source reads were GET-only; OAuth authorisation/token refresh is separate from data modification.

## 3. Live verification

Initial Gmail run: **18:41:18–18:41:25 IST**, 17 GETs. Shared follow-up run: **18:43:46–18:43:54 IST**, including five additional Gmail GETs and five Drive-related reads. All 22 Gmail reads returned HTTP 200.

| Resource / check | GETs | Observed result |
| --- | ---: | --- |
| Mailbox profile and labels | 2 | Intended mailbox and label structures readable. |
| Four bounded candidate searches | 4 | Dubsado sender, Dubsado financial terms, known client names and support-address references all returned candidates. Each query had more pages. |
| Initial message bodies | 8 | Full MIME responses inspected; plain-text and HTML-only examples both readable. |
| Initial thread metadata | 2 | Two one-message Dubsado threads readable. |
| History endpoint at current cursor | 1 | Successful response with current history ID; no history entries returned. This is not a changed-message or push test. |
| Full client reply chains | 2 | Ridgefield thread has three messages; The Penny thread has two, including a draft. |
| One small-PDF search and its message | 2 | Bounded client-associated attachment example found. |
| Attachment bytes | 1 | PDF attachment returned, **213,816 decoded bytes**; hash recorded. PDF contents were not parsed or saved. |

Searches used `from:(dubsado.com)`, `dubsado {contract invoice payment signed paid}`, known-client terms and `"support@leadlockpro.com"`. Initial queries returned at most five IDs each; at most two candidates per query were selected for body reads, capped at eight. Search `resultSizeEstimate` was 201 for each initial query and is explicitly an **estimate**, not a validated total of notifications, payments, clients or support issues. [Message-list reference](https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages/list).

## 4. Required data and how to obtain it

| Required input | API fields / retrieval | Use and limits |
| --- | --- | --- |
| Mailbox identity | `users.getProfile` | Validate which mailbox is connected; one account does not establish access to another support inbox. |
| Message/thread identity | Message `id`, `threadId`, RFC Message-ID, In-Reply-To/References where available | Stable source citation, reply ordering, deduplication and cross-source references. A thread can contain several decisions and states. |
| Sender, recipients and source time | From, To, Cc/Bcc, Date, internalDate; full/metadata message reads | Client/staff/third-party identity and direction. Preserve received/internal time separately from sender date and a reported business-event time. |
| Message content | `users.messages.get(format=full)`; traverse MIME alternatives/parts, base64url decode | Requests, concerns, approvals, commitments and notification bodies. HTML entities, signatures, forwarded/quoted text and embedded assets need robust normalization. |
| Thread context | `users.threads.get(format=full)` | Distinguish original request, actual reply, later corrections and current authorship instead of treating every quoted copy as a new statement. |
| Message state | Labels such as DRAFT, SENT, INBOX and custom labels | Exclude drafts from sent communication, distinguish system notifications from client replies, and retain routing context. A sent record is not proof of delivery, reading or agreement. |
| Financial notification evidence | Trusted notification source plus subject/body, contract/invoice URLs/identifiers, available amount/currency | Reported signing/payment events, reminders and references. Sender display name or a matching keyword alone does not establish a financial event or active-client association. |
| Attachments and links | MIME attachment manifest, `users.messages.attachments.get`; parsed message URLs | Evidence pointers and document retrieval. File parsing is separate; distinguish invoice/contract links from logos, settings links, social links and tracking redirects. |
| Change cursor | Profile/history IDs; `users.history.list` | Incremental reconciliation after notification. IDs are cursors, not sequential event counts or timestamps. |

Official routes: [message content](https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages/get), [history synchronization](https://developers.google.com/workspace/gmail/api/guides/sync).

## 5. Real evidence and what it establishes

### Dubsado signing/payment events

Two separate emails from `noreply@dubsado.com` to the intended mailbox establish the proposed intake structure:

- **Signing notification:** message `1a141b43aee1176e`, subject “Tony has signed your contract for GSA - The Promise of 2912”, dated 15 October 2026 at 22:34:51 UTC. Its body links to a Dubsado contract-view resource.
- **Payment notification:** message `1a141b55fe585991`, subject reports Tony Khatibi paid **1,400.00 USD** for the same project label, dated 15 October at 22:36:06 UTC. Its body links to a Dubsado invoice resource.

This verifies subject/body/URL retrieval and reported event association. The available timestamps are notification timestamps, not independently proven execution/signing timestamps. The target contract/invoice pages were **not opened**, so full terms, instalments, invoice balance, refunds, allocation and whether all obligations are settled remain unverified. Client/project/offer mapping must be reviewed before joining this project label to a client ledger entry.

The sampled notifications have custom/category labels and **neither currently has INBOX**. An INBOX-only watch risks missing relevant labelled/archived mail. Confirm the actual routing and use a mailbox-wide or explicitly reviewed label policy, then filter in the intake pipeline. Do not adopt an example INBOX filter without this check.

Two other financial-keyword candidates are **sent payment reminders**, not payment receipts. One reminder is addressed to an internal support address. Their amounts and due dates are available, but these alone do not establish current debt, correct client association or offer coverage. The same invoice may appear in reminders, payment notices and later replies; do not sum them as separate payments.

The audit normalizes invoice/contract URLs from message-body excerpts. The first probe's broad raw URL samples can include a closing Markdown bracket or branding/settings links; production extraction must normalize and classify actual targets rather than take the first link.

### Approval and follow-up chain

Ridgefield thread `1a13c56ff9d27807` contains three source messages:

1. WIA requests review of three creatives and other campaign inputs on 14 October.
2. Delia replies from the client mailbox approving the ads, sharing a brochure link and offering further inputs.
3. Whitney replies on 15 October, acknowledging the approval and saying she will review the brochure early the following week.

This demonstrates real client approval, WIA/client requests and candidate commitments with source-specific authorship. Approval of ads does not prove campaign launch or performance. “Early next week” and “end of the week” need a reviewed interpretation/interval; do not invent an exact mandatory due date. Count Delia's original reply once even when quoted in Whitney's later message.

### Support context with an unsent reply

The Penny thread `1a1467eea28e65cb` contains an incoming client email describing form/mobile/style issues, **Cc'd to `support@leadlockpro.com`**. Its second message, `1a1467fd30bb3c5e`, is labelled **DRAFT** and contains a proposed WIA reply to the same participants.

The incoming request and shared support context are verified. The draft is not evidence that Whitney sent the reply, assigned the work, acknowledged receipt to the client, or that support resolved it. This mailbox sample does not establish complete coverage of the separate LeadLock support inbox, form submissions or a maintained ticket pipeline.

### System notifications and duplicate signals

A known-client search returns a ClickUp daily digest mentioning Ridgefield and other clients. It is system-generated and mixes several accounts. Use it as a discovery pointer or notification evidence; the direct ClickUp record supplies task state. Do not count the digest, quoted task title and direct task as three promises or client conversations.

## 6. Frontend support

| Frontend surface | Gmail can support | Needed safeguards/dependencies |
| --- | --- | --- |
| Source Library / evidence drawer | Subject, author, date, message/thread ID and excerpt | Add stable source IDs/URL, state, observed time and quote boundaries. No production deep-link playback was tested. |
| Now / client requests / relationship signal | Attributed current concerns, requests and replies | Sent/draft/system/incoming distinctions; client contact mapping and freshness. Sentiment is interpretation, not a source score. |
| Client Commitments / Action register | Explicit WIA/client requests, approvals, acknowledgements and conditional promises | Scope approval to the exact deliverable; assignment, due date and independent completion require their own evidence. Unknown/relative dates must remain representable. |
| Call Prep | Outstanding questions, requested inputs and unresolved support context | Combine with Calendar event data and meeting/ClickUp context. A proposed time in email is not a verified scheduled event. |
| Engagement history / handover | Reported commercial events and dated conversations | Deduplicate quoted/forwarded material and system notifications; preserve message order and source date semantics. |
| Client Profile / support issues | Incoming issue, participants, reported timing and latest known state | No complete support-source or resolution trail verified. Drafts must not advance workflow state. |
| Invoices & terms | Reported signing/payment events, reminder evidence and linked contract/invoice references | **Not a complete Paid/Open/Overdue ledger.** Full invoice IDs, payment allocations/current balances, terms and document contents must be reconciled. A reminder is not current balance proof. |
| Profile / client identity | Contact aliases and statements relevant to the client | A sender/recipient or a Dubsado name is not independently a paid active engagement. Internal and test recipients need filtering. |
| Attendance / health / coverage | A client may explicitly report absence or an outreach exchange | Sheets/session records are separate. No email or silence is not proof of absence, dissatisfaction, or a meaningful coverage percentage. |

`data.ts` has **three fictional Gmail evidence objects** (`bloom-email`, `willow-email`, `harbor-email`) and a connector preview count of three. Their requests/concern/context pattern is feasible, but this review does not validate their fictional statements or connect real clients to those mock identities. `types.ts` needs nullable/relative deadlines and provenance for real extracted actions. The six mock invoices cannot be populated reliably from a single receipt/notification pair.

## 7. Planned change-notification implementation

The user requests POST delivery to the backend domain. Proposed path:

1. Create a Pub/Sub topic in the Cloud project used for the Gmail watch. Grant publisher access on that topic to `gmail-api-push@system.gserviceaccount.com`.
2. Configure a push subscription pointing to an authenticated, public HTTPS backend endpoint; validate the push caller/token according to its configured authentication.
3. Register each authorised mailbox with `users.watch`. Persist the initial history cursor and expiration, and reconcile initial backfill with changes arriving during ingestion.
4. On each notification, use the stored cursor with `history.list`, fetch relevant message details, persist durable processing and advance the cursor safely. Notification bodies carry mailbox/history information, not complete email content. Handle duplicate/reordered delivery idempotently.
5. Renew the watch before expiry. Google requires renewal at least every seven days and recommends daily renewal. Notifications can be delayed/dropped; reconcile periodically and handle expired/invalid history cursors with resynchronization.

This is **not deployed or delivery-tested**. Required remaining inputs/configuration include the public receiving domain/path, project/topic/subscription, IAM and mailbox filtering policy. Neither this OAuth callback nor successful history reads are a webhook receiver test. [Official Gmail push guidance](https://developers.google.com/workspace/gmail/api/guides/push).

## 8. Remaining checks

- **G-V-01:** reviewed client/contact/offer registry and bounded-to-full historical coverage, including additional pages and other required mailboxes.
- **G-V-02:** reconcile the Dubsado event pair with its actual invoice/contract and current balances before supporting the full money UI. GHL pricing meaning remains open.
- **G-V-03:** trace an issue from actual intake through handling to confirmed resolution; distinguish draft, sent, acknowledged and resolved states.
- **G-V-04:** robust MIME/HTML/quoted-text/link normalization, multi-client system notifications, attachments and explicit field-level source references. One PDF's bytes are readable; its content was not parsed.
- **G-V-05:** actual authenticated Pub/Sub POST delivery, renewal, cursor recovery, retries/deduplication and no-INBOX routing coverage.

## 9. Evidence and reproduction

```powershell
node knowledge_base/wia-knowledge-base/verification/google/verify_google_sources.mjs --gmail
node knowledge_base/wia-knowledge-base/verification/google/verify_google_followup.mjs
python knowledge_base/wia-knowledge-base/verification/google/audit_google.py
```

The shared follow-up also reads bounded Drive samples. Commands repeat remote GETs and overwrite their respective reports; the audit is offline. These are source tests, not production ingestion.

- [Gmail API report](knowledge_base/wia-knowledge-base/verification/gmail/live_probe.json)
- [Shared follow-up](knowledge_base/wia-knowledge-base/verification/google/followup_probe.json)
- [Gmail audit and normalized Dubsado source links](knowledge_base/wia-knowledge-base/verification/gmail/local_audit.json)
- [OAuth status](knowledge_base/wia-knowledge-base/verification/google/authorization_status.json) and [refresh verification](knowledge_base/wia-knowledge-base/verification/google/refresh_probe.json)
- [Setup and helper documentation](knowledge_base/wia-knowledge-base/verification/google/README.md)
