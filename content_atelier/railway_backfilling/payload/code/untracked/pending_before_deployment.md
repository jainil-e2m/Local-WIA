# Pending before deployment

Updated: 15 October 2026.

The future source intake implementation has been built and tested. The items
below remain pending for configuration, deployment and live acceptance.
Administrator configuration is deferred at the user's request.

## Intake configuration

- [ ] Set `ATELIER_INTAKE_ADMINS` to the existing, verified team login email
  addresses allowed to activate connectors, collect manually and retry jobs.
- [ ] Create the ignored `backend/.env.intake.local` from
  [the configuration template](backend/intake.env.example).
- [ ] Configure `ATELIER_FATHOM_API_KEY` and confirm it can access the intended
  future recordings.
- [ ] Configure a dedicated `ATELIER_SLACK_INTAKE_TOKEN` and share it with the
  existing Slack bot. It must differ from `ATELIER_API_SECRET`.
- [ ] Configure the matching backend/BFF `ATELIER_API_SECRET`.
- [ ] Configure `EMBEDDING_API_KEY` and enable `ATELIER_ALLOW_INTAKE_ENCODING`
  when ready to index new live sources.

## Connect the existing Slack bot

- [ ] Connect the bot to the collection-request, batch-delivery, receipt and
  attachment-upload endpoints using the supplied `SlackDeliveryClient` adapter
  or an equivalent implementation of the versioned contract.
- [ ] Confirm workspace `T03P5A3L1DK` and the three selected channels:
  Meta `C082DURRJ2U`, Google `C09LQ656BPU`, Social Proof `C091CPQD8L9`.
- [ ] Verify complete channel coverage, empty windows, pagination, replies,
  edits/deletions, retry-safe persisted batch bytes and attachment uploads.

## Deploy and activate

- [ ] Start the local Docker intake stack and apply its additive migrations to
  the intended application database. Previous end-to-end verification used an
  isolated test database and temporary containers.
- [ ] Point the frontend BFF's `ATELIER_BACKEND_ORIGIN` to the intake API, retain
  the existing Command Center authentication settings, and rebuild/restart the
  frontend so the Sources view is available.
- [ ] Activate Fathom and Slack from Sources using an authorized team account
  after credentials and bot integration are ready. Activation establishes the
  future-only starting boundary.

## Live acceptance

- [ ] Verify a newly created Fathom recording reaches preserved original,
  normalized text, searchable indexing and weekly membership.
- [ ] Verify a new message from each selected Slack channel follows the same
  path, including a real attachment delivery.
- [ ] Verify real audio transcription with the configured local model. Audio
  decoding and the ASR adapter were tested, but actual model inference has not
  been validated with a live audio source.
- [ ] Observe a scheduled Saturday 04:00 `America/Chicago` collection and bucket
  completion, plus manual refresh and restart recovery with the connected feeds.

## Existing frontend validation issue

- [ ] Review and resolve the existing failure in
  `frontend/src/components/ScheduledContent.test.tsx`: the scheduling-popup test
  expects two controls but renders ten. The affected scheduling code was not
  changed by the intake implementation; the full frontend suite is not green.

Implementation details and startup commands:
[Future source intake setup and bot contract](backend/docs/Future-Source-Intake.md).

Historical Zoom transcripts, historical Slack messages and existing corpus
backfilling remain outside the current scope; they are not deployment tasks here.
