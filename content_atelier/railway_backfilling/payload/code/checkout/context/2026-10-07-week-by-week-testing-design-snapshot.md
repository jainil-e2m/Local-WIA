# Content Atelier — local, week-by-week testing and paid-output reuse

Prepared: 7 October 2026. Status: design and recommendations for review, not an implemented test harness.

This document defines the first testing environment: local PostgreSQL/pgvector, one embedding vector per generated angle, backfilled Zoom transcripts processed one week at a time, durable JSON experiment records, Markdown review ledgers, and saved paid-call artifacts that can be reused safely while the production PostgreSQL schema is still being learned.

No paid API call, transcript import, database installation, migration, backend restoration or deployment is performed by writing this design. The user is still clarifying requirements before implementation.

## 1. Confirmed requirements and what remains proposed

Confirmed by the latest request:

- Run pgvector locally for current testing.
- Begin with one week's backfilled Zoom meeting transcripts; progress to the next week gradually, refining and backfilling as testing proceeds.
- Give each content angle one embedding vector, not separate vectors for its hook, topic, proof and formats.
- Preserve intermediate pipeline data in JSON/Markdown files before settling the full production relational schema.
- Save paid embedding/LLM inputs, outputs and dependencies so compatible completed work can be reused.
- Discuss OpenAI third-generation text embeddings and OpenRouter model choices for key moments and angles.

Previously confirmed requirements still apply: transcripts only in the first slice; every eligible distinct angle above the adjusted-score threshold is visible; no four-angle quota; every valid generated candidate is retained; “last turn” means the previous completed generation run; no additional LLM similarity judge; one eventual PostgreSQL/pgvector database, not a separate vector service.

Recommendations in this document—including the embedding model/dimensions, LLM models, branch layout, virtual timeline and file contracts—are proposals, not already approved client requirements. Saturday 04:00 Texas time remains provisional; the business timezone/window/cutoff and source authority are tracked in the [next-call ledger][call-ledger].

Two unresolved points remain explicit:

1. “Very close similarity then only include both relevant ones”: comparison display or both weekly selectable angles, and does the rule also apply to two current candidates?
2. “Initial and final content angles generation”: final deterministic selection, or an additional LLM rewrite/refinement pass? An asynchronous clarification was asked. The baseline remains two logical LLM stages until answered; no third similarity judge is introduced.

## 2. The architecture for testing

Use three cooperating storage roles:

| Layer | Responsibility | Authority |
|---|---|---|
| Versioned JSON records/artifacts | Sources, revisions, moments, claims, candidates, requests/responses, vectors, manifests, matches, scores and decisions | Durable experiment source of truth during this phase |
| Markdown reports/ledgers | Inspect a week, compare runs, record human labels, explain decisions and index meetings | Human-readable views; deliberately recorded decisions reference exact JSON IDs |
| Local PostgreSQL with pgvector | Search/comparison projection of authorised, compatible, eligible angle vectors | Rebuildable index, not the sole copy of paid output |

This is document-shaped persistence, not installing MongoDB. A JSON file can carry a nested record like a MongoDB document, but it does not provide MongoDB's concurrent transactions, indexes or access model. Keep the initial harness single-writer with explicit locks/leases, IDs, validation, atomic writes and checkpoints.

We can defer the **full business schema**, not all data contracts. Stable identity, schema versions, provenance, completeness, permissions and generation lineage are required now; otherwise we would be preserving expensive output without knowing what it means or whether it is reusable.

pgvector is a PostgreSQL extension: using it locally still requires a small scratch database/table. That minimal projection does not determine the later production schema. [Official pgvector documentation][pgvector]

Local storage does not make embedding or LLM inference local. Approved source material would still leave the machine when sent to OpenAI/OpenRouter providers. Confirm processing authority and privacy/routing before any real call.

## 3. One week at a time: the execution loop

For an admitted week:

1. Freeze the Zoom transcript/source-revision manifest and the prior-history snapshot.
2. Normalise full transcripts, retaining original text, stable speaker/turn IDs, timestamps and permission/coverage states.
3. LLM Stage 1 extracts key moments and meaning-complete surrounding context across every eligible transcript interval. Reuse exact completed extraction artifacts where valid.
4. Assemble the week's admitted moment/claim pool; preserve qualifiers and any missing/excluded intervals.
5. LLM Stage 2 generates all substantive source-grounded angles, structured reader contributions and base-quality assessments. Reuse only compatible generation artifacts.
6. Persist every valid candidate, including ones later below threshold or overlap-suppressed.
7. Build one canonical angle signature and retrieve/create its one embedding vector.
8. Compare against all eligible prior branch history and the previous completed generation run, excluding self/current-run/retries. Compare current candidates separately.
9. Compute deterministic similarity/recency penalties and threshold-qualified visibility under the agreed close-pair policy.
10. Save the complete result and generate a Markdown review with source context, score breakdown, matched prior angles and coverage warnings.
11. Record human labels/corrections; adjust one identified variable; rerun only affected work.
12. Advance deliberately to the next week, extending the selected experiment branch's history.

The review does not authorise briefs, packs or public use. The first week's output can be zero, fewer than four, or more than four angles; there is no quota.

Do not import all months and then choose a week cosmetically while future records remain eligible for matching. Later weeks may be on disk, but a manifest/query must make them inaccessible to the earlier simulated cycle's evidence/history comparison.

## 4. Three clocks: meetings, real execution and simulated editorial history

Backfilling historical meetings does not make today's model output historically generated content. Preserve:

| Clock | Example role | Must not be substituted for |
|---|---|---|
| `meeting_occurred_at` | Places a meeting in its weekly source window | Transcript download time or angle generation time |
| `executed_at_actual` / `generated_at_actual` | Records when this paid/test operation really happened | A fabricated historical generation date |
| `editorial_as_of` / `generated_at_simulated` | Explicit simulation of when that cycle's generation would have happened | Actual production generation timestamps |

### 4.1 Recommended modes

**Historical weekly simulation**, recommended for the backfill exercise: use each historical cycle's agreed/provisional cutoff as its virtual generation event and scoring clock. When testing week 2, week 1's simulated generation is approximately one local week older, not a few seconds older because both runs executed today.

**Actual-operation mode:** use real generation-event timestamps for live current operation or for intentionally testing rapid real reruns. An angle truly generated yesterday is one day old even if its source meeting was three months ago.

Name the mode in every run and ranking revision. Never blend the two clocks silently or label simulated dates as real history. Assign a generation event once per logical run; replays, re-embedding and threshold changes do not refresh either clock.

For multiple intentional same-cycle generations, preserve run sequence and an explicit simulated event policy. If they share a virtual cutoff, zero simulated age is an honest configured test; do not invent elapsed days. If an advancing virtual clock is needed for the experiment, record the chosen offsets.

### 4.2 Empty initial history

Week 1 may start with no authorised prior angle memory. Record `history_seed = empty` and limited archive coverage; a computed penalty of zero means no eligible match in that declared snapshot, not “never discussed/published before.”

Week 2 adds all eligible valid generated candidates from completed prior runs on its history branch, not only visible winners. Published archive imports are separately labelled audience-exposure history, not fake angle-generation events.

Retain the original generation-recency requirement. A simulated clock is a named test mode for evaluating it, not a replacement for production semantics.

## 5. Isolate experiments without losing generated-angle memory

There are two different questions:

- **Sequential product behaviour:** what happens as weeks and genuine regenerations accumulate on one branch?
- **Controlled A/B evaluation:** does a changed model/prompt improve output for exactly the same sources and prior history?

Use a durable `experiment_id`, `branch_id`, `run_id`, `parent_run_id`, `history_snapshot_id` and `memory_role`.

For the chronological baseline, new completed generation runs become history; intentional same-week regeneration considers the previous completed run. Retain all its valid angles and dispositions.

For a controlled comparison, fork from the **same frozen prior history before either variant is generated**. Variant B must not be penalised for being similar to Variant A solely because A was tried first. Both variants are retained, but a comparison-only run is not silently inserted into the chronological branch's memory.

Before advancing a week, explicitly choose the branch/version to continue. This does not mean deleting variants or putting only approved/visible angles in memory; all valid prior generated candidates eligible on that branch remain. Exclude unrelated experiment branches, mocks, failed incomplete generations and duplicate retries through a recorded eligibility snapshot.

Never “repair” an A/B result by manually deleting an inconvenient prior angle. Keep the artifact and change the experiment scope openly.

## 6. The file-backed datastore layout

Proposed dedicated area inside Content Atelier:

```text
testing/
  README.md                         # documentation; safe to track
  .data/                            # private runtime datastore; not committed
    catalog/
      sources/                      # source identities/revisions/permissions
      policies/                     # exact editorial-policy bundles
      profiles/                     # model, signature, embedding and score profiles
    objects/
      raw_sources/<hash>/           # original Zoom VTT/export bytes
      artifacts/<hash>.json         # validated stage outputs; content addressed
    paid_calls/
      <request_key>/
        intent.json
        attempts/
          <attempt_id>/
            request.body.json
            response.raw.json
            usage.json
            validation.json
            error.json              # only if present
            status.events.jsonl
    cycles/
      <cycle_id>/
        manifest.json
        sources.json
        coverage.json
    experiments/
      <experiment_id>/
        branches/<branch_id>.json
        runs/<run_id>/
          manifest.json
          stage-index.json
          candidates.json
          history-snapshot.json
          matches.json
          ranking.json
          selection.json
          review.md
          labels.json
    ledgers/
      paid-attempts.jsonl
      reuse-events.jsonl
      corrections.jsonl
      schema-changes.jsonl
      experiments.md
    exports/
      postgres-migration-manifest.json
```

This tree describes future runtime records. Only the explanatory README/design are created now; there are no real transcript files, paid outputs or completed runs yet.

Git's ignore check verified that a representative future `testing/.data/paid_calls/.../response.raw.json` path is excluded by the existing `.data/` rule, while `testing/README.md` remains trackable. No private artifact was created. Ignore rules are not encryption, access control or backup. Keep raw material, full prompts and paid responses private and restrict cloud sync/share according to WIA's policy.

Use paths based on application-assigned IDs/hashes, not raw client names or source-controlled paths. Validate paths remain beneath the intended store, especially on Windows. Keep relative artifact references portable within the store; do not depend on this user's absolute desktop path for runtime identity.

JSON/JSONL usage:

- One immutable source/revision/artifact/attempt record per ID, where practical.
- Modest week/run indexes can be JSON arrays of IDs and small summaries; large payloads are referenced by path/hash.
- JSONL suits single-writer append-only events/cost/reuse ledgers; each line is an independently valid JSON event.
- Do not repeatedly rewrite one enormous `all-data.json` or duplicate full transcripts in every review.
- Human corrections are structured records plus optional explanatory Markdown, not untracked edits to cached paid results.

## 7. Minimum record contract before the full PostgreSQL schema

Every authoritative JSON document has at least `record_type`, `schema_version`, stable IDs, timestamps, dependency references/hashes, provenance, permissions/readiness, and its originating run/attempt where applicable.

### 7.1 Illustrative candidate record

The following is a schema example, not actual WIA output. No fake production vector is inserted; `embedding.status = pending` until exactly one valid vector artifact is attached.

```json
{
  "record_type": "angle_candidate",
  "schema_version": "1.0",
  "angle_id": "angle-example-001",
  "angle_revision_id": "angle-example-001-r1",
  "experiment_id": "exp-example",
  "branch_id": "baseline",
  "generation_run_id": "run-example-w01",
  "cycle_id": "cycle-example-w01",
  "generated_at_actual": null,
  "generated_at_simulated": null,
  "clock_mode": "historical_simulation",
  "argument": {
    "audience": "Wedding-business owners",
    "tension": "Illustrative tension, not sourced client evidence",
    "take": "Illustrative source-supported reader argument",
    "mechanism": "Illustrative mechanism",
    "reader_decision": "Illustrative decision"
  },
  "source_moment_ids": [],
  "claim_ids": [],
  "base_quality": null,
  "signature_version": "angle-signature-v1",
  "signature_hash": null,
  "embedding": {
    "status": "pending",
    "profile_id": null,
    "artifact_ref": null,
    "response_item_index": null
  },
  "disposition": "example_only",
  "is_real_candidate": false
}
```

A real admitted candidate cannot have these missing evidence/scoring/clock fields. Validate before processing; `example_only` records never enter history. Historical unknown generation dates remain explicitly unknown, not imported as “generated now.”

### 7.2 Other essential record families

| Record | Critical information |
|---|---|
| Source revision | Stable Zoom meeting/export identity, raw hash, occurrence/fetch times, host/purpose, speaker uncertainty, locator and permissions |
| Coverage / context | Full transcript interval manifest; exact anchor/context turn IDs; processed/excluded/missing reasons |
| Moment / claim | Source-supported proposition, quote/span, context, attribution, metric scope, qualifiers and readiness |
| Paid attempt | Exact request/config, returned data, request ID, provider, usage, cost, validation and status |
| Run manifest | Source/policy snapshots, prompts/schemas/model parameters, branch/history, clock mode, stage completion and chosen artifacts |
| Embedding attachment | One canonical signature, compatible profile/dimensions, vector reference/hash and readiness |
| Similarity/ranking | Every qualified pair, raw cosine, eligible IDs, generation age, dominant risk, base/penalty/adjusted scores and config |
| Selection / labels | Visible/suppressed/review-required reason, close-pair policy, human decision/actor/evidence and ranking revision |

Keep source records distinct from generated interpretations. A parsed angle cannot become corroborating evidence just because it exists in a JSON “collection.”

## 8. Dedicated paid-service preservation and reuse contract

This is a core design requirement, not incidental debug logging.

**Pay for a needed inference once; save the complete usable returned artifact and dependencies; replay compatible validated work locally; preserve errors and cost uncertainty honestly.** This is not a promise of exactly-once provider billing under every network/storage failure.

### 8.1 Preserve before and after every paid attempt

Before calling:

- Write durable intent, logical request ID, stage and exact input artifact references/hashes.
- Save the rendered model request body, prompts, schema, policy bundle, requested model, inference parameters and allowed provider/privacy routing.
- Record estimated token/cost budget, retry cap and why new paid work is needed.
- Claim an exclusive local request-key lease so duplicate workers do not both spend.

After response, **before** parsing/scoring/upserting vectors:

- Save the returned response body immediately, including normal API metadata; preserve a failed/malformed/truncated response as failed, not successful cache data.
- Save provider/generation/request IDs, actual returned model, actual route if available, start/end/latency, finish reason and returned usage/cost/cache metadata.
- Then validate and store a distinct parsed artifact/validation report. Link each candidate/embedding item to the response item and source inputs.
- Update the paid-attempt ledger and run checkpoint durably.
- Do not delete the raw returned response when parsing fails; it may support a local parser repair without paying again.

“Entire pipeline data” means the inputs, returned outputs, validated intermediates and decision lineage needed to inspect/replay the workflow. It does not mean API keys, bearer headers, private hidden model reasoning, inaccessible provider internals, or retaining material contrary to permissions. Capture only safe request headers/metadata; keep secrets in approved environment/secret storage.

For streaming, persist received chunks safely and capture final usage if delivered. A disconnect with no final usage is `billing_unknown`/partial output, not a free request. Recover metadata by a returned generation ID where supported; do not automatically retry a possibly billed request as if nothing happened.

### 8.2 Exact reusable-result identity

Build a versioned local fingerprint from all **output-affecting** inputs:

```text
stage type
+ exact source/moment/candidate input hashes
+ exact rendered system/developer/user prompt content
+ response schema and relevant validation contract
+ active policy bundle and context inputs
+ requested model/revision and inference parameters
+ allowed provider/privacy/routing configuration
+ signature/model/dimensions for embeddings
+ deliberate sampling identity when a fresh trial is requested
```

Canonicalise JSON objects for the application's fingerprint, but preserve text bytes/order where they affect the actual request. Do not include irrelevant UI titles or a new report creation time. Save the actual serialized request body too; our local logical fingerprint is not a claim about a gateway's internal cache-key algorithm.

Reuse requires: complete success, valid artifact, exact compatible fingerprint, intact dependencies, continuing permissions, allowed route/model lineage and no expiry/revocation under the data policy.

If parsing/validation changes, retained raw output can be revalidated locally. A changed validator does not automatically require a paid call, but it invalidates the old “passed” assertion until revalidation. If previously returned output cannot satisfy the new contract, an explicit new/repair call may be needed.

For embedding batches, retain input-to-response-index mapping and an individual signature/profile reuse key. Rebatching the same signatures need not re-embed already cached items. Never attach vector index 3 to a different angle merely because the request order changed.

### 8.3 Replay is not a new generation event

A local replay points to its original successful inference/generation event. It may create a new report or ranking revision; it must not make the old angle “recently generated” again.

Intentional regeneration/fresh sampling gets a new logical generation event and a new sampling identity, even if source text is unchanged. Record it as new paid work only when actually called; distinguish reuse from fresh outputs.

Temperature zero or a seed is not a guarantee that future requests reproduce the same text. Saved output gives exact replay; a new paid request may differ. Avoid silent moving `latest` aliases or automatic model replacement across a controlled experiment.

### 8.4 Changes and what can be reused

| Change | Reuse | New work |
|---|---|---|
| Visible threshold / half-life / penalty strength | Sources, moments, angles, signatures and vectors | Deterministic ranking/selection revision only |
| Current close-pair display policy | Prior stages and numerical pair records, if membership/profile unchanged | Selection/review revision |
| Historical memory membership or score cutoff | Extraction, generation under the post-generation baseline, unchanged vectors | Refilter/recompute historical comparisons and ranking |
| Review layout or non-semantic card title | Underlying source/angle/vector artifacts | Markdown/read-model rendering |
| Parser/validator repair | Original response and compatible upstream artifacts | Local reparse/revalidation; new call only if returned data cannot satisfy contract |
| Angle-generation prompt/model/policy inputs | Unchanged valid extraction artifacts | New angle-generation experiment; embeddings only for changed/new signatures |
| Moment-extraction prompt/model/context boundaries | Unchanged raw sources/normalisation | Affected extraction and dependent generation; reuse unaffected intervals carefully |
| A transcript revision or permission change | Unaffected source revisions and dependencies | Invalidate affected descendants; some may require rerun or be prohibited entirely |
| Embedding signature/profile/dimensions | Sources, extraction and angle text | New compatible vector projection/history rebuild; recalibrate similarity thresholds |
| Scratch DB lost / later full schema migration | Authoritative JSON and saved vectors | Rehydrate database without paid regeneration |
| Fresh variability test | Sources/context and exact experiment setup | Explicit new paid samples; do not mislabel cache replay as a new model trial |

Code changes alone are not a reason to repay every earlier stage. A prompt/profile/source/permission change is not a reason to reuse an incompatible paid result merely to save money.

### 8.5 App replay versus provider caching

Local artifact reuse can avoid making the API request entirely. Provider prompt caching typically discounts repeated input work but still performs inference. OpenRouter response caching can reuse successful identical responses, but its retention is bounded and eviction/concurrent misses remain possible. It does not replace local saved results. [OpenRouter prompt caching][prompt-cache] [OpenRouter response caching][response-cache]

Treat gateway caching as optional, privacy-compatible optimisation, not the durable testing datastore. A fresh-sampling experiment must deliberately bypass stale local/gateway result reuse. Record gateway hit/miss separately from local replay.

### 8.6 Cost ledger

Track each actual attempt, not only successful selected angles:

- Logical request key, attempt ID, run/stage and provider request ID.
- Requested/returned model and provider, service tier and relevant rate snapshot/date.
- Input/output/reasoning/cached tokens as supplied; unknown fields are null with an explanation.
- Estimated cost before call, reported charge after call, currency/unit and reconciliation state.
- Success/failure/partial/billing-unknown, retries and validation result.
- Local reuse events reference the original attempt and add zero **new inference** cost, while retaining the original paid cost.
- Human-readable summaries by week, experiment, stage and quality outcome.

OpenRouter documents usage costs/token/cache information in responses and generation-ID lookup for audits. Use the actual returned charge as the primary record rather than deriving the invoice solely from advertised token rates. [OpenRouter usage accounting][usage-accounting]

Do not double-add reasoning tokens if they are already included in completion totals. Do not count raw/parsed copies of a response as separate paid requests. A “cost avoided” estimate is not a refund or measured invoice saving.

Configure per-attempt/stage/week/experiment spending ceilings before execution. Stop with incomplete coverage when a ceiling is reached; do not spend silently until a desired angle count appears.

Recommend explicit run modes: `replay_only` (cache misses stop and list missing work), `plan` (show eligible reuse/new-call estimates without calling), and `paid_run` (only under the configured approved budget/route). An ordinary review or database rebuild must not fall through into paid inference because an artifact is missing.

For a purely illustrative first-pass budget calculation, Stage 1 using 100,000 input and 10,000 billed output tokens at the listed Gemini rates is USD0.1125; Stage 2 using 20,000 input and 10,000 billed output tokens at the listed Sonnet rates is USD0.14. Add 30,000 angle-signature tokens at the large embedding rate (USD0.0039) for USD0.2564. Those are invented token volumes, not a quote for WIA's week, and exclude retries, any additional billed reasoning not in the supplied output total, gateway/account charges and taxes. Actual weekly volume and returned usage/charge determine the cost ledger.

## 9. File durability, idempotency and recovery

Initially prefer one writer. Use per-request leases and write immutable payloads to temporary files on the same filesystem, flush as appropriate, then atomically replace/rename committed artifacts. Validate JSON/checksums before switching manifest pointers. A crash should leave an incomplete attempt/checkpoint, not a completed run referencing half a file.

There is no automatic multi-file transaction: commit payloads first, then update a run manifest/checkpoint that names the committed artifacts. Recovery reconciles orphaned complete payloads and unresolved attempt states before requesting new paid work. JSONL appends also need exclusive ownership; truncation is detected and repaired deliberately, not ignored as valid history.

Suggested paid-attempt states: `planned`, `in_flight`, `response_saved`, `validated`, `failed`, `billing_unknown`. A provider success whose response was lost before local persistence is a real gap; recovery may need provider lookup or a consciously authorised retry. No generic client-side cache can guarantee exactly-once billing across that gap.

If the raw response is saved but PostgreSQL fails, replay the database projection locally. If the parsed schema is wrong but raw data is recoverable, fix/revalidate locally. A missing return body is not reconstructed by inventing an angle.

Permissions override frozen snapshots/caches. Purge/redact withdrawn data through raw files, derived artifacts, reports, vectors and backups under an agreed policy; a cache is not exempt from a source withdrawal. Keep backups private and test restoration. “Temporary” does not mean disposable or indefinitely retained.

## 10. One canonical embedding vector per content angle

Interpret the requested invariant as **one active searchable vector attached to each generated angle**, built from one canonical signature. No multi-view ensemble or separate title/topic/quote/format vectors.

The same numerical vector is saved in a paid/artifact record and projected to local pgvector for recovery; these are copies of one representation, not different semantic vectors. Record one authoritative attachment/profile per angle.

Recommended signature inputs:

- Audience/state, concrete tension.
- Central take/core proposition and relevant factual scope.
- Mechanism and reader decision/new contribution.
- Concise case context only when it materially distinguishes the argument.
- Essential qualifiers that change the argument's meaning.

Exclude arbitrary UUIDs, run dates, quality scores, rank, review status, proposed format counts and full repeated transcript passages from the embedded text. Keep those as metadata. Otherwise novelty can drift with bookkeeping or a shared source quote rather than the actual reader argument.

Do not embed a catchy title alone. Canonical rendering/order, whitespace rules and signature version are pinned. A wording-only card edit that leaves the canonical signature unchanged reuses its vector; a changed argument/signature requires a new vector attachment.

On a profile or substantive revision change, replace the active projection only after the compatible artifact is valid. Retain prior paid responses for audit within permissions, but do not search old/new representations concurrently for the same angle. A meaningful new independently generated angle still gets its own identity/event; it is not a disguised destructive overwrite.

This active-record interpretation allows safe versioned refinement while honouring one vector per angle. It is not permission to create several concurrent embeddings to improve recall.

## 11. OpenAI embedding recommendation

OpenAI's third-generation family has two named options; “text embeddings 3” is not a complete model/profile ID.

| Model | Default dimensions | Standard input price / 1M tokens | Recommended use here |
|---|---:|---:|---|
| [text-embedding-3-small][embedding-small] | 1,536 | USD0.02 | Lower-cost baseline if pair-label tests show adequate discrimination |
| [text-embedding-3-large][embedding-large] | 3,072 | USD0.13 | Proposed primary candidate for nuanced angle similarity; explicitly request 1,536 dimensions |

Both support reduced output dimensions through the API's `dimensions` parameter. [Official OpenAI embedding guide][embedding-guide]

**Proposed starting profile: `text-embedding-3-large`, `dimensions=1536`, one canonical angle-signature vector, cosine similarity.** Choose one profile for the first chronological test branch. This is a quality-oriented hypothesis, not measured proof that large/1536 beats small/1536 on Whitney's angles.

Why this proposal:

- Our expected angle-signature volume is small relative to transcript LLM input; the dollar difference is modest even though large is 6.5 times the per-token price.
- Similarity decisions need to distinguish substantive reader arguments from broad shared topics; a quality-oriented model is worth testing.
- 1,536 dimensions keeps ordinary `vector` storage/index options straightforward.
- One stable profile across weeks avoids mixing incompatible similarity distributions while we learn.

For illustration, 100 signatures averaging 300 tokens total 30,000 tokens: small costs USD0.0006; large costs USD0.0039 at those standard rates. This is embedding inference only, excludes LLM calls/retries/infrastructure/taxes, and is not a measurement of our real input volume.

pgvector documents a 2,000-dimension limit for ordinary `vector` HNSW/IVFFlat indexes; that is **not a prohibition on storing or exactly comparing a 3,072-dimensional vector**. Other indexing representations exist. Explicit 1,536-dimensional large embeddings avoid needing them for this test. Start with exact search rather than installing an approximate index prematurely. [pgvector index types and limits][pgvector]

A large/1536 vector and small/1536 vector are not interchangeable despite matching lengths. A new model/profile means a rebuilt compatible historical projection and new threshold calibration, not copying last model's cosine cutoff.

If the initial labelled-pair test finds no useful quality gain, small/1536 is a sensible later profile choice. Do not embed every angle with both models in the active collection; any authorised model comparison uses isolated experiment profiles and one active representation per angle.

## 12. Local pgvector scratch projection

A minimal proposed record contains:

- `angle_id` / active `angle_revision_id`.
- `experiment_id`, `branch_id`, `generation_run_id`, `cycle_id`.
- Signature hash/version and embedding-profile ID.
- One `embedding vector(1536)` column if that proposed profile is selected.
- Actual/simulated generation clocks and mode, plus eligibility/search-readiness metadata needed for filtering.
- Relative authoritative JSON artifact reference and hash.

Enforce uniqueness for the active angle identity in the scratch projection. All branch/history filtering must use the explicit frozen manifest, not “whatever rows are in the database today.” For a modest pool, exact scans/pairwise comparisons give full threshold coverage.

A scratch row is not the complete angle datastore. Large source context and all paid responses remain in the file store. Rebuild by loading validated JSON mappings/vectors, then verify counts, hashes, dimensions, finite/nonzero values, and sampled cosine agreement within an explicit floating-point tolerance.

Do not round JSON vectors to a few decimals. A later cast to pgvector's storage precision can produce tiny numeric differences; define precision and threshold-boundary tolerance rather than promising bitwise identical floating-point arithmetic.

Historical transcript chunks need not be embedded to discover this week's moments: Stage 1 covers full source text. Source-chunk embedding/search can be added when historical evidence retrieval is in scope; angle-memory vectors are the immediate requirement, not an excuse to embed every transcript before the first test.

No SQL migration is executed by this document.

## 13. OpenRouter model shortlist

Sources were checked on 7 October 2026. Rates below are advertised text input/output prices in USD per million tokens, not a guaranteed invoice quote; actual endpoint/tier/cache/reasoning usage and availability must be captured per attempt. Model roles are our hypotheses to evaluate, not task-specific benchmark results.

| OpenRouter model ID | Input / output per 1M | Suggested experiment role | What to validate |
|---|---|---|---|
| [google/gemini-3.8-flash][gemini] | 0.75 / 3.75 | Primary Stage 1 moment/context extraction candidate; balanced Stage 2 alternative | Late-transcript recall, speaker/qualifier retention, exact source IDs and substantive rather than generic angles |
| [anthropic/claude-sonnet-5.5][sonnet] | 2.00 / 10.00 | Quality-oriented Stage 2 grounded angle generation; challenger for difficult extraction | Distinct reader contributions, defensible claims, calibrated base scores and editorial editing effort |
| [qwen/qwen3.8-flash][qwen] | 0.15 / 0.47 | Low-cost challenger for extraction and initial candidate generation | Same evidence/JSON contract, omissions and unsupported extrapolation; low price is not sufficient |
| [deepseek/deepseek-v4-pro-20260813][deepseek] | From 0.2514 / 4.20 | Additional reasoning/generation challenger, if its approved provider route is suitable | Output/reasoning cost, schema fidelity, source-faithfulness and review effort |

The catalogues list approximately 1M-token context and JSON-schema output support for these models. Large context is capacity, not proof of complete attention or source accuracy. Context/output budgets and coverage remain explicit. Sonnet 5.5's listed always-on thinking means reasoning effort is a relevant cost/depth setting; do not assume it can simply be disabled. [Sonnet catalogue][sonnet]

**Proposed first profile pair: Gemini 3.8 Flash for Stage 1, Claude Sonnet 5.5 for Stage 2, OpenAI large/1536 for the one-vector embedding profile.** Compare one lower-cost challenger after obtaining a useful labelled first-week baseline. Do not run all four models on every stage/week without a measured reason and budget.

These model recommendations use fetched provider/router documentation, not older bundled defaults; the OpenAI Docs skill guided verification of the exact embedding family and its documented price/dimensions.

### 13.1 Structured output and routing

Require the actual endpoint to support the chosen schema/parameters; a catalogue label is insufficient. OpenRouter documents `response_format` JSON-schema support and `require_parameters: true` to restrict routing accordingly. [Structured outputs][structured]

For controlled comparisons, pin an approved provider/endpoint where practical and disable unrecorded fallback. Otherwise actual provider changes become a confound. Always record requested versus returned model/route and distinguish a model alias from a dated immutable version when the provider exposes one. Never guess a snapshot ID that is not listed.

Privacy preferences may include approved-provider allowlists, data-collection restrictions or ZDR routing where required/available; these are route constraints, not a substitute for WIA's consent or proof every selected endpoint supports the task. No web-search/tool plugins are needed to extract grounded angles from supplied transcripts. [Provider routing][routing]

### 13.2 What “final angle generation” would mean

Baseline today:

- Stage 1: key moments/context.
- Stage 2: source-grounded candidate angles and base quality.
- Final set: numerical history/current-pair comparison, recency scoring and deterministic selection/review under the agreed policy.

The final set is not generated by another LLM. If the user wants an additional refinement pass, Sonnet is a candidate to test, but that is a new explicit workflow responsibility/cost/cache dependency to agree first—not a similarity judge.

A refinement that changes the argument must be revalidated, re-embedded and re-compared/re-scored before final visibility. A wording-only refinement preserving the canonical signature need not re-embed. Do not pick winners, rewrite their meaning, and keep an old vector/rank as if nothing changed.

## 14. Evaluation and refinement week by week

For the first week, manually inspect a manageable but representative set of full transcripts, including low-signal calls and passages late in long calls. Label meaningful anchors, context completeness and useful potential reader contributions. Do not evaluate only the model's chosen moments; that hides missed evidence.

For angles, label:

- Grounded / unsupported central proposition.
- Directly connected / vague association.
- Useful specific reader decision / generic advice.
- Same argument / overlapping but useful / related topic / unrelated, for human calibration pairs.
- Accept / edit / reject with concise reason and responsible reviewer.
- Permissions/attribution/claim limitations needing resolution.

Use model-independent labels and original sources. Do not treat the model's own quality score or generated “new contribution” explanation as the evaluation truth.

Keep a weekly review table:

| Metric | Why |
|---|---|
| Transcript/interval coverage and pending exclusions | Know what actually entered generation |
| Human-labelled meaningful-moment recall | Detect missed useful evidence |
| Context/quote/speaker/claim-faithfulness errors | Avoid unsupported content |
| Valid source-linked candidate ratio | Measure relevance before novelty |
| Current-set redundancy and historical false-match/missed-match examples | Tune signatures and numerical thresholds |
| Human accept/edit/reject and editing effort | Measure editorial usefulness |
| New paid cost, cumulative cost and local artifact reuse | Make iteration economically visible |
| Pipeline failures/recovery and unresolved close pairs | Test trustworthiness, not only happy-path prose |

Change one hypothesis at a time: extraction prompt/context grouping, then generation schema/prompt, then signature/thresholds/decay, then model choice where needed. Independent stable test cases may be recomputed without importing unrelated future history.

When prompts/models are refined on early weeks, those weeks become development data. Reserve later unseen weeks/pairs for validation before tuning on them, or use explicit rolling-origin comparisons. Later human preferences/policy changes must be versioned; retrospective improvements using later knowledge are not historically unbiased evaluations.

“Fine tune/refine” here means improving prompts, context contracts, candidate schema, policies, scoring and retrieval. No model-weight fine-tuning or automated learning is authorised. If actual fine-tuning is considered later, dataset rights, evaluation and separate spend approval are new decisions.

## 15. Acceptance and failure tests for this setup

Before a paid weekly harness is considered dependable:

1. Every admitted interval is processed, cached-valid, excluded with reason or visibly incomplete.
2. Stage 1 quotes/context/attribution resolve to exact original spans; source text cannot rewrite pipeline instructions.
3. All valid angles survive filtering; each searchable angle has exactly one active compatible vector.
4. Replaying a completed week triggers no new paid calls and no refreshed generation timestamps.
5. Changing only threshold/decay recomputes ranking locally; changing the generation prompt reuses compatible extraction.
6. Changing an embedding profile rejects mixed spaces and rebuilds history from saved angle signatures.
7. Resetting the scratch projection restores it from files with matching IDs/vector counts and tolerance-checked comparisons.
8. Week 1 cannot retrieve week 2's evidence/angles; week 2 sees all eligible valid week 1 branch candidates.
9. Simulated clocks yield the expected weekly-age decay; actual clocks remain truthful.
10. A/B variants use identical prior-history snapshots and cannot penalise each other accidentally.
11. Intentional main-branch regeneration includes the previous completed run; ordinary retry/cache replay does not.
12. A crash after saved response but before parsing/DB write reuses the response; an unknown billed attempt is not blindly retried.
13. Missing final streamed usage produces uncertainty, not a zero cost claim.
14. Invalid source references, secrets in artifact payloads, revoked permissions and corrupt JSON/checksums are detected.
15. Close-pair selection follows an explicit approved rule; its current ambiguity is not silently implemented.
16. Week/report/page size never imposes a hidden four-angle quota.

These are proposed tests. No actual pipeline, provider, database or paid-call test has been run in this documentation task.

## 16. When to migrate to the full PostgreSQL schema

Do not wait until every content format is implemented. Migrate when the evidence/angle contracts stabilise enough across representative weeks and concurrency/query/recovery needs justify relational persistence.

Import existing stable source/angle/event IDs and versions; map JSON documents to typed relational records; retain raw objects/paid artifacts as private referenced files or object storage. Postgres can become the authoritative operational store while preserving those immutable paid artifacts.

Migration must preserve:

- Every valid generated candidate, status, provenance and original generation clocks.
- Exact moment/source/claim dependencies and permission state.
- One active vector/profile per angle plus rebuild mappings.
- Run/branch/history/config/prompt/model lineage.
- Base/penalty/adjusted scores and ranking/selection revisions.
- Human labels/decisions and cost/reuse records.

Verify counts, hashes, dependency integrity, compatible profile, sampled searches/rankings and replay. A new schema is not a reason to regenerate transcripts, moments, angles or vectors with paid services. Schema-version adapters may reparse/map existing artifacts locally.

Keep the scratch projection explicitly temporary so its convenient columns do not accidentally become the production domain model.

## 17. Decisions needed before implementation

| Decision | Current position |
|---|---|
| Local pgvector / file-backed staged testing | User confirmed |
| One angle vector | User confirmed; one active canonical representation, not multi-view embeddings |
| First inputs | One historical week of Zoom meeting transcripts; exact dates/exports/host coverage still needed |
| Embedding model/profile | Proposed OpenAI large/1536; awaiting selection/evaluation |
| Stage 1/2 models | Proposed Gemini 3.8 Flash / Sonnet 5.5; not yet selected or tested |
| Paid preservation/reuse | User required; implementation must enforce compatibility, permissions and cost logging |
| Historical simulation/branch policy | Recommended and documented; confirm before interpreting recency results |
| Final-generation meaning | Open clarification: deterministic selected set versus additional LLM refinement |
| Very-close pair behaviour | Earlier I-01 still open |
| Cost limits / provider privacy routes | Need explicit settings before first paid test |
| Weekly timezone/window | Provisional; client ledger C-01–C-03 |
| Live source permissions | Must be verified; possession of an export is not assumed blanket processing/public-use permission |

Ready next step: settle these internal choices, select one authorised first-week dataset, then request implementation of the local/file-backed harness. Start with a replayable small end-to-end fixture and intentionally exercise failures; advance weeks after reviewing quality rather than expanding input volume blindly.

## Sources and related documents

- [Transcript-to-angle specification][angle-spec]: baseline source, score and visibility contracts.
- [Vector storage design][vector-spec]: broader policy/evidence/memory architecture.
- [Next-call and meeting ledger][call-ledger]: authority and client/internal open questions.
- [Testing datastore README][testing-readme]: dedicated local artifact area.
- Official model/platform/router sources linked above were checked on 7 October 2026; pricing/capabilities must be rechecked before actual calls.

[angle-spec]: <C:/Users/Jainil Trivedi/Desktop/Wedding_Industry_Ads/content_atelier/transcript_to_content-angle.md>
[vector-spec]: <C:/Users/Jainil Trivedi/Desktop/Wedding_Industry_Ads/content_atelier/content_atelier_vectordb.md>
[call-ledger]: <C:/Users/Jainil Trivedi/Desktop/Wedding_Industry_Ads/content_atelier/to_be_asked_in_next_call.md>
[testing-readme]: <C:/Users/Jainil Trivedi/Desktop/Wedding_Industry_Ads/content_atelier/testing/README.md>
[embedding-small]: https://developers.openai.com/api/docs/models/text-embedding-3-small
[embedding-large]: https://developers.openai.com/api/docs/models/text-embedding-3-large
[embedding-guide]: https://developers.openai.com/api/docs/guides/embeddings
[pgvector]: https://github.com/pgvector/pgvector
[gemini]: https://openrouter.ai/google/gemini-3.8-flash
[sonnet]: https://openrouter.ai/anthropic/claude-sonnet-5.5
[qwen]: https://openrouter.ai/qwen/qwen3.8-flash
[deepseek]: https://openrouter.ai/deepseek/deepseek-v4-pro-20260813
[structured]: https://openrouter.ai/docs/guides/features/structured-outputs
[routing]: https://openrouter.ai/docs/guides/routing/provider-selection
[usage-accounting]: https://openrouter.ai/docs/cookbook/administration/usage-accounting
[prompt-cache]: https://openrouter.ai/docs/guides/best-practices/prompt-caching
[response-cache]: https://openrouter.ai/docs/guides/features/response-caching
