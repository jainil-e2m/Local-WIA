# Future source intake

This implementation collects new Fathom transcripts and messages from the three
configured Slack channels after explicit connector activation. It does not scan,
import, register or re-embed the existing Zoom/Slack/corpus directories. It does
not generate moments, angles or briefs.

## Local setup

From `content_atelier/backend`, copy `intake.env.example` to `.env.intake.local`
and fill in:

- `ATELIER_API_SECRET`: the backend secret used by the existing Atelier BFF.
- `ATELIER_INTAKE_ADMINS`: comma-separated verified team email addresses allowed
  to activate connections, collect, complete and retry.
- `ATELIER_FATHOM_API_KEY`: your Fathom key; backend only.
- `ATELIER_SLACK_INTAKE_TOKEN`: a separate random service credential shared only
  with your Slack bot. Do not use the backend/BFF secret for this.
- `EMBEDDING_API_KEY` and `ATELIER_ALLOW_INTAKE_ENCODING=true` to index new text.
  Intake indexing is independent of editorial generation permissions.

Start the overlay using the existing storage project:

```powershell
docker compose -f compose.storage.yml -f compose.intake.yml --env-file .env.intake.local up -d --build
```

The migration service initializes a fresh approved baseline when necessary,
applies the text-search index and the additive intake migration, then exits.
The existing `atelier_data` volume is retained. Do not run `down --volumes`.
Migration never activates a connector or registers historical content.

The API binds to `127.0.0.1:18000`. Redis stays on the Docker network. A
persistent artifacts volume holds receipts, original files and embedding caches;
a separate model volume holds local audio models. One media worker handles
CPU-intensive extraction independently of the intake worker.

Configure the existing frontend BFF with `ATELIER_BACKEND_ORIGIN` pointing to
this API and the matching `ATELIER_API_SECRET`, then rebuild/restart that frontend
using its existing authentication configuration. For a host-run BFF, use
`http://127.0.0.1:18000`. A Docker-hosted BFF can use
`http://host.docker.internal:18000` where available, or join the storage network
and use `http://intake-api:8000`. Keep the Command Center auth configuration.

Team members see **Sources**. A configured administrator can activate Fathom and
Slack there. Each activation establishes an irreversible starting checkpoint at
the current time. Repeating activation preserves that checkpoint.
Click a weekly bucket to inspect its exact member revisions, including older
completed buckets; the default source list shows the 200 most recent sources.

## Collection and weekly buckets

- Fathom discovery runs hourly with pagination and a ten-minute overlap bounded
  by activation. Recording creation time determines eligibility, not an old
  folder or an inferred week. Fathom keys can only discover recordings the key
  holder can access.
- Newly discovered recordings with unpublished transcripts remain pending.
  Read-only transient failures retry with bounded backoff; authentication failures
  require correction and administrator retry. Already discovered live recordings
  are checked periodically for transcript corrections.
- The bot can poll Slack collection requests whenever it runs. Hourly requests
  support frequent delivery; a weekly bot can deliver the most recent complete
  requested window. Complete coverage can supersede earlier partial windows.
- Saturday at 04:00 `America/Chicago`, the scheduler freezes a cutoff and opens
  the next bucket. The earlier bucket completes after collection coverage,
  required extraction and indexing succeed. Scheduling follows CDT/CST.
- **Collect through now** refreshes without closing. **Complete current bucket**
  closes at the current time and waits for completion conditions.
- Occurrence times remain separate from receipt times. Late content goes into
  the open bucket. Completed membership and original revisions remain stable.
- Outage recovery resumes post-activation work. It never crosses activation to
  import older history. PostgreSQL owns work; Redis is a replaceable dispatcher.

## Slack bot contract

The existing bot remains responsible for Slack API access, permissions,
pagination, edits/deletions, thread replies and authenticated file downloads.
This service does not call Slack or read export folders.

Send `Authorization: Bearer <ATELIER_SLACK_INTAKE_TOKEN>` directly to the local API:

| Endpoint | Contract |
|---|---|
| `GET /intake/v1/requests` | Pending windows and configured workspace/channel IDs |
| `GET /intake/v1/slack/schema` | Exact versioned JSON schema |
| `POST /intake/v1/slack/batches` | Durable receipt, HTTP 202 |
| `GET /intake/v1/batches/{batch_id}` | Receipt plus attachment upload handles |
| `PUT /intake/v1/assets/{asset_id}/content` | Immutable attachment bytes, HTTP 202 |

The configured workspace is `T03P5A3L1DK`. Channels are Meta
`C082DURRJ2U`, Google `C09LQ656BPU`, and Social Proof `C091CPQD8L9`.

Example batch (use the exact request identifiers/window returned by the API):

```json
{
  "schema_version": 1,
  "batch_id": "your_persisted_delivery_id",
  "request_id": "request_from_api",
  "workspace": "T03P5A3L1DK",
  "channel": "C082DURRJ2U",
  "window_start": "2026-10-15T12:00:00Z",
  "window_end": "2026-10-15T13:00:00Z",
  "part": 1,
  "total_parts": 1,
  "gaps": [],
  "messages": [{
    "ts": "1792066200.000001",
    "text": "The full original message text",
    "user": "U123",
    "updated_at": "2026-10-15T12:10:00.000001Z",
    "thread_ts": null,
    "deleted": false,
    "context_only": false,
    "files": [],
    "raw": {}
  }]
}
```

Preserve `ts` and `thread_ts` as strings. Use the original event timestamp as
`updated_at` for new messages, and edit/deletion event time for changes. Windows
are half-open `[window_start, window_end)`. Include the complete current message
and file manifest for an edit. A deletion is a new tombstone revision. The bot
must retain event/delta information if Slack history alone cannot reconstruct it.

An older parent can accompany a new reply with `context_only=true`. It must be
the reply's parent and cannot carry files or a deletion. It is saved as context
with the reply's original, without importing the historical thread.

Send a batch for every selected channel, including `messages: []` for an empty
channel. Number parts from 1 with a stable `total_parts`; all parts must be
present and gap-free for coverage to complete. Report missing pages or collection
failures in `gaps`. Repair a gapped window by collecting a later requested window
that fully covers it. An accepted part's bytes and batch identifier are immutable.

Persist exact batch bytes in the bot's outbox before sending. Retry the same
bytes and identifier on an ambiguous delivery timeout. Identical retries return
the original receipt; different bytes under that identifier return HTTP 409.
The batch limit is 4 MiB and 1,000 messages. Split before assigning part counts.

`backend_pipeline.intake.slack_client.SlackDeliveryClient` supplies request,
deterministic preparation, delivery, receipt and upload methods for integration
into the existing Python bot. It never collects Slack itself.

For each file, supply `file_id`, `filename`, `mime_type`, `size_bytes`, optional
`sha256`, and `permalink`. After the receipt becomes `processed`, obtain asset
IDs from its `assets` list and upload the corresponding original bytes. Upload
only assets marked `awaiting_upload`; video and oversized files are metadata-only.
Do not send Slack credentials to this API or substitute an arbitrary download URL.

## Evidence and operations

Raw receipts/files are stored before their acceptance transaction commits. Sources
have stable provider identities; content changes create immutable revisions.
Text normalization retains exact character ranges and speaker/time, page,
paragraph or OCR-region locators. Source identifiers and revisions are independent
of weekly editorial records.

Supported extraction: UTF-8 text/JSON, PDF text and scanned pages, DOCX, images
through local Tesseract, and audio through local CPU/int8 Faster Whisper.
The first audio task downloads its configured model into the persistent model
cache. Models are not bundled into Git or the image. OCR and ASR are explicitly
marked machine-derived. Audio is limited to two hours, PDFs to 300 pages,
and uploads to 25 MiB. Video is linked; unsupported/oversized assets retain
their status and metadata. Empty or failed extraction stays visible for review.

Indexing reuses the existing exact-chunk embedding contract, cached responses,
vector validation and SQL provenance. A lost embedding response is never
automatically rebilled. Inspect artifacts, correct configuration and explicitly
retry a failed embedding job. Newly received/unindexed revisions do not disable
ready archive research. Sources search uses local full-text retrieval without
incurring a query embedding call; the existing semantic research API remains.

Browser routes are under `/api/atelier/intake/...`, authenticated through the
existing BFF. Only verified team sessions can read sources. Mutations additionally
require the configured administrator email. The bot credential cannot access
browser/admin routes. Provider and service credentials stay outside frontend code.

Inspect failures in Sources or Docker logs:

```powershell
docker compose -f compose.storage.yml -f compose.intake.yml --env-file .env.intake.local logs --tail 100 intake-scheduler intake-worker intake-media
```

The scheduler reconciles durable SQL work with Redis every 30 seconds and resumes
eligible missing deliveries after restarts. Existing editorial jobs remain owned
by the PostgreSQL worker; intake jobs use RQ and never replace a week's active run.

## Verification

`backend_pipeline/tests/test_future_intake.py` covers provider contracts, real
PostgreSQL behavior, activation boundaries, idempotency, coverage, revisions,
attachments, indexing, queue reconciliation, permissions and weekly scheduling.
Use a dedicated `atelier_intake_test` database through
`INTAKE_TEST_DATABASE_URL`; the fixture refuses all other databases. Existing
editorial regression tests use a separate disposable `atelier_test` database.
The test suite blocks external provider HTTP.

To initialize the disposable intake database for these tests, create an empty
database named `atelier_intake_test`, set `INTAKE_TEST_DATABASE_URL` to it, and run
`python scripts/generate_intake_catalog.py` from the backend directory with
`PYTHONPATH=.`. That utility explicitly rebuilds **only** `atelier_intake_test`;
never point integration fixtures at the application database. Install the test
extras from `pyproject.toml` (`pytest` and `fakeredis`) as well as backend dependencies.

Before live acceptance: configure credentials/admin identity, connect the bot to
the delivery contract, activate each connector, and verify a newly created Fathom
recording plus a new message in each selected channel through searchable text and
weekly membership. Historical folders are not used for this verification.
