# Phase 2: search, embeddings, topics, ledger API and extraction health

Branch `item/2-moments-ledger` (this agent's work: 2.B3, 2.B5, 2.B6, 2.B7, 2.B8, 2.B12). Written for the integrator and for whoever builds
`MomentsLedgerView` from the generated types. Extraction, checks, imports and the backfill command are the other agent's and are not described here.

## What was built

| Area | Where | Notes |
| --- | --- | --- |
| One `Citation` shape | `backend_pipeline/search/citation.py` | Settled here; Phases 3 and 4 reuse it. See "The Citation" below. |
| Filters | `search/filters.py` | One `SearchFilters` for search, the ledger and its facets. Consent default, explicit-offset dates, topic merges followed. |
| Hybrid retrieval | `search/hybrid.py`, `search/rows.py` | Exact SQL (no ANN index): cosine `<=>` plus `websearch_to_tsquery`, fused by reciprocal rank fusion. |
| Query vector | `search/query.py` | Made through the llm module only when it can be; otherwise text-only, said in the answer. |
| `POST /search` | `search/api.py` | Moments, chunks or both. |
| Moment embeddings (2.B5) | `moments/embedding.py`, `embedding_cli.py` | Planned, estimated, queued as a `bulk` run; handler dispatched from `SQLWorker.execute` through `search/jobs.py`. |
| Topic registry (2.B7) | `moments/topics.py`, `topics_cli.py` | Nearest topics by embedding, a fast model picks or proposes, admin rename/merge/block/unblock, audited. |
| Moments API (2.B8) and topic routes | `moments/api.py` | `GET /moments`, `/moments/facets`, `/moments/{id}`, topics. |
| Extraction health (2.B12) | `moments/health.py` | `GET /documents/extraction-health`: on the documents API, not the intake Sources overview (that one is about connections, buckets and revisions). Pure SQL. |
| Relay allowlist | `frontend/server/allowlist.mjs`, `moments.test.mjs` | Closed queries; a team session only. |

Registered in `storage_api.py` (the old `GET /moments/{moment_id}` handler, which returned the raw row and failed on a vector column, was replaced by the ledger's detail, which
keeps its `moment` and `passages` keys), `sql_pipeline.py` (one separate branch at the top of `execute`), `storage_cli.py` (groups `moments-embed`, `topics`, `search`),
`jobs/policy.py` (stages `moment_embedding` and `topic_assignment`: bulk queue, 3600 s timeout, never retried automatically) and `llm/providers.py`
(`topic_assignment` joins `JSON_STAGES`).

## The Citation

```json
{
  "document_id": "transcript_9f2c...", "document_title": "Acme check-in", "source_type": "fathom", "call_type": "client_1to1",
  "passage_ids": ["fathom:812:span:41"], "start": 18211, "end": 18290, "start_ms": 1260000, "end_ms": 1275000,
  "speaker_label": "Dana Lee", "speaker_id": "person_dana", "speaker_role": "client",
  "client_id": "client_acme", "client_name": "Acme Weddings", "consent_status": "cleared",
  "occurred_at": "2026-03-12T15:30:00Z", "recording_url": "https://fathom.video/share/abc",
  "quote": "We reply to every inquiry within five minutes and our bookings doubled."
}
```

Every field is always present (nullable ones are `null`). For a **moment** hit: `passage_ids` are the passages the extractor anchored the scene on; `start`/`end` bound the
verified quote inside the immutable `original_text` (`original_text[start:end] == quote`, tested); `start_ms`/`end_ms` and the speaker are the anchor passage's; consent is the
moment's stored `consent_status` (computed by the backend, only displayed by the browser). For a **chunk** hit: the chunk's passage range, `quote` is the original text of that
range, the speaker is the chunk's first non-overlap turn, and consent is document-level: `do_not_use` for a client whose consent is `no_use`, otherwise `anonymise`
(never `cleared`: a chunk has no sensitivity judgement). `recording_url` comes from what the document holds (`source_url`, the provider's `share_url`/`url`, or for a Slack
thread a link built from workspace, channel and thread) and is always `http(s)`; a Zoom or file transcript has none and gets `null`. A hit whose citation cannot be located in
the original text is withheld and counted in `hits_withheld`.

## `POST /storage/search` (any signed-in role)

```json
{ "text": "how quickly should we respond to new leads", "k": 5, "scope": "moments",
  "filters": { "client_id": "client_acme", "moment_type": ["result", "testimonial"], "consent_status": ["cleared"],
               "date_from": "2026-01-01T00:00:00-05:00", "date_to": "2026-04-01T00:00:00-05:00" } }
```

`k` 1..50 (default 10). `scope`: `moments` (default), `chunks`, `all`. Filters (all optional, combined with AND; a list is alternatives):
`date_from` (closed) and `date_to` (open), both **with an explicit offset** (422 otherwise), `client_id`, `source_type`, `call_type`, `speaker_role[]`, `moment_type[]`
(all twelve types, including the new testimonial, question, teaching, soundbite, data_point), `consent_status[]` (default `cleared`, `anonymise`, `internal_only`: `do_not_use`
only when named), `topic_id` (a merged topic is followed to its target), `document_ids[]`. `moment_type` and `topic_id` describe moments: with `scope=chunks` they are a 422; with
`scope=all` no chunk can satisfy them, so only moments come back (`filters_applied.kinds` says so).

```json
{ "hits": [ { "kind": "moment", "score": 0.0325, "matched_by": ["phrase", "semantic"],
              "moment": { "moment_id": "m_reply", "document_id": "...", "moment_type": "result", "quote": "...", "record": "...", "speaker_role": "client",
                          "consent_status": "cleared", "quote_verified": true, "topics": [{ "topic_id": "topic_...", "name": "Inquiry follow-up speed" }], "...": "..." },
              "chunk": null, "citation": { "...": "see above" } } ],
  "query_embedding_status": "used", "query_embedding_detail": null,
  "filters_applied": { "consent_status": ["cleared", "anonymise", "internal_only"], "consent_defaulted": true, "kinds": ["moment"],
                       "verified_only": true, "current_only": true, "topic_id": null, "topic_resolved_id": null, "...": "..." },
  "scope": "moments", "k": 5, "hits_withheld": 0 }
```

* Only **verified, current** moments of **included, non-duplicate** documents are ever searched. Only vectors made under the process's embedding model take part in the
  meaning list.
* `score` is the fused reciprocal-rank score, `sum(1 / (search.rrf_k + rank))` over the lists a hit is in. Ties break by kind (moments first), then id.
* `query_embedding_status: "unavailable"` (with a reason in `query_embedding_detail`) means the words alone ranked: no encoding catch, no key, no active run plan, or a provider
  failure. It is never a silent failure and never an error for the person searching.
* `POST /search/transcripts` is unchanged.

**Making query embedding work in production.** The API process needs `ATELIER_ALLOW_ENCODING=true`, an embedding key, and `ATELIER_RUN_PLAN_ID` naming an active plan that
covers the `embedding` stage and the model and was created for any input set (a query has no frozen input set):
`storage_cli plan create --purpose "search queries" --stage embedding --model openai/text-embedding-3-small --input-set-hash '*' --max-calls 5000 --max-cost-usd 5 --approver whitney@...`.
A plan that runs out makes search fall back to the words, with that said in the answer. An in-process cache (512 queries) means a repeated query is not paid for twice.

## Moment embeddings (2.B5)

What is embedded (`embedding_text`): `Quote: <verified quote>`, `Scene: <record or proposition>`, `Setup: <context summary>`, whitespace collapsed, empty parts dropped, at most
6000 characters (setup is trimmed first, then the record, never the quote). Type, speaker, client and consent are filters, not meaning. The text and the builder version
(`moment-scene-v1`) are hashed into `embedding_input_hash`; a moment with the same hash and model is never embedded again.

```
storage_cli moments-embed report                       searchable moments, embedded under the contract, stale or missing
storage_cli moments-embed queue --estimate             count, tokens, USD, requests, and the run plan to create (input_set_hash). No call, nothing queued.
storage_cli plan create --purpose "Embed moments" --stage embedding --model <embedding model> --input-set-hash <from the estimate> --max-calls <requests> --max-cost-usd <cap> --approver <email>
ATELIER_RUN_PLAN_ID=<plan> ATELIER_ALLOW_ENCODING=true storage_cli moments-embed queue --mode live    (queue, from any process with the catch)
ATELIER_RUN_PLAN_ID=<plan> ATELIER_ALLOW_ENCODING=true python -m backend_pipeline.jobs worker        (the bulk queue worker runs it; or storage_cli worker inline)
```

`--mode cached` embeds only from saved vectors (and, on a synthetic database with an injected provider, from that provider). The run is one `bulk` job: batches of
`moments.embedding.batch_size`; each response is saved before any validation or write; vectors are cached by contract and text (`moment-embedding/<hash>.json`), so a retried
job or a moment whose text appears twice is not paid for again; the write re-checks that each moment is still verified, current and unchanged. **A mismatched contract
refuses**: dimensions other than 1536, vectors that exist under another model (`ATELIER_ALLOW_EMBEDDING_CONTRACT_CHANGE=true` lifts it only while re-encoding), an earlier
completed run's contract digest, or a frozen run whose contract changed. The table itself refuses a vector on an unverified moment. Suggestion for the integrator: add
`moment_embedding` to `startup._STAGES` so a process with a different contract also refuses to *start* (kept out of this branch: `startup.py` is not Phase 2's).

## Topics (2.B7)

```
storage_cli topics assign --estimate [--price-in P --price-out P]   moments needing a topic; how many attach with no call; the calls at most; the run plan to create
storage_cli topics assign --mode live                                queue one bulk run (live needs ATELIER_ALLOW_GENERATION and ATELIER_ALLOW_ENCODING and an active plan
                                                                     covering stages topic_assignment and embedding and both models)
storage_cli topics list | show TOPIC_ID
storage_cli topics rename|merge|block|unblock TOPIC_ID --actor <approver email> [--name ... | --into ...] [--note ...]
```

The nearest `topics.candidates` (5) active topics by cosine are found; the nearest is attached with no model call when it is at least `topics.attach_similarity` (0.80) close;
otherwise the cheap classification model (`models.document_classification`, else `models.moment_extraction`) gets the scene and the candidates under a strict JSON schema, with
one repair, and picks one or two of them or proposes one new topic. A proposal naming an existing subject attaches to it; one naming a blocked subject is dropped; one naming a
merged topic follows the merge. A moment the model cannot answer for (still invalid after the repair) is left alone and counted (`model_unusable`); a refused or failed call
stops the run. Blocked topics are never offered and `link` raises for them (`TopicBlocked`); merged ones likewise (`TopicMerged`); a merge moves the links
(`assigned_by='merge'`), drops duplicates and repoints topics that were merged into the source. A rename keeps the old vector, now stale; the next assignment run embeds the new
words. Statistics per topic: mentions in the last 30/90/365 days (verified, current moments of included documents), total, distinct clients, last mention.

**Schema gap (needs a one-line migration).** `decisions.item_kind` (migrations 005 and 006) does not allow `'topic'`, and every administrator action and every person's link
or unlink must write a `decisions` row. Until the integrator adds a migration, those actions fail with a clear error (`The decisions table does not accept item_kind 'topic' yet`)
and their effect is rolled back, never applied unaudited. The tests widen the constraint for their own duration (`tests/ledger_fixtures.py`). The migration:

```sql
ALTER TABLE decisions DROP CONSTRAINT decisions_item_kind_check;
ALTER TABLE decisions ADD CONSTRAINT decisions_item_kind_check CHECK (item_kind IN ('angle', 'considered_idea', 'brief',
  'brand_kit_item', 'brand_kit_version', 'brand_kit_source', 'published_content', 'run_plan', 'seed', 'topic'));
```

## Routes (all under `/storage`)

| Method and path | Who | Notes |
| --- | --- | --- |
| `POST /search` | any signed-in role | body above |
| `GET /moments` | any signed-in role | `q`, `client_id`, `source_type`, `call_type`, `speaker_role`, `moment_type`, `consent_status` (comma-separated lists), `topic_id`, `document_id`, `from`, `to` (explicit offsets), `quote_verified` and `is_current` (`true` default, `false`, `any`), `extractor_version`, `limit` (1..200, 50), `offset`. Order: `occurred_at desc nulls last, moment_id`. Answer: `{items: MomentSummary[], total, limit, offset}` |
| `GET /moments/facets` | any signed-in role | the same filters (no paging); counts by moment type, speaker role, consent status (includes `do_not_use`), client, source type, call type; `earliest`/`latest`; each dimension is counted under the *other* filters |
| `GET /moments/{id}` | any signed-in role | `{moment, passages}` (what the card screens read) plus `summary`, `citation`, `document`, `surrounding` (4 passages either side, with offsets and `cited`/`anchor` flags), `evidence_intact`, `topics`, `checks`, `quote_repair`, `unverified_reason`, `cards` (angles citing it) |
| `POST /moments/{id}/topics` | editor | `{add: [topic_id], remove: [topic_id], note}`; a blocked or merged topic is a 409 |
| `GET /topics`, `GET /topics/{id}` | any signed-in role | `status`, `q`, `limit`, `offset`; detail adds merged-from, recent moments, the decision history |
| `POST /topics/{id}/rename`, `/merge`, `/block`, `/unblock` | approver | `{name, description?, note?}`, `{into_topic_id, note?}`, `{note?}` |
| `GET /documents/extraction-health` | any signed-in role | counts of included documents by `extraction_status`, failed documents with the job's `error_summary`, the oldest pending, zero-scene and verified-quote shares, and each per source type |

The consent default hides `do_not_use` in the ledger as in search; ask for it with `consent_status=do_not_use` (the facets show how many there are).
`MomentDetail` replaces the old `MomentEvidence` in the generated types; `frontend/src/api/evidence.ts` imports it under the old name.

## Settings added (`DEPLOYMENT.md` lists them)

| Key | Default | Meaning |
| --- | --- | --- |
| `search.rrf_k` | 60 | reciprocal rank fusion constant |
| `search.candidates` | 100 | candidates each method hands to the fusion per kind |
| `search.semantic_min_cosine` | 0.0 | meaning matches below this cosine are dropped (raise only after measuring on real moments) |
| `moments.embedding.batch_size` | 32 | moments per embedding request |
| `topics.candidates` | 5 | nearest topics offered |
| `topics.attach_similarity` | 0.80 | cosine at which the nearest topic is attached with no model call |

## What needs real data or a person

* A live embedding run over the real verified moments (after the other agent's extraction and backfill): `--estimate`, a run plan approved by a person, the run.
* `topics.attach_similarity` and `search.semantic_min_cosine` are defaults, not measurements: tune them on real moments (the first topic run should be read by a person).
* The chat model's prices for the topic estimate (`--price-in/--price-out`); the embedding price is the documented constant.
* The Phase 2 golden fixture (Funktastic chain: each hand-listed moment found by paraphrase) and the "known moment in the top five" check on the real archive.
* A standing run plan for query embedding in the API process (above).
