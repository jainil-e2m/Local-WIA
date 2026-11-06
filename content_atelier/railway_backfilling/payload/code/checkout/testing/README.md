# Content Atelier testing datastore

Latest continuation, 8 October 2026: the user authorised saved A3 moments for Call 2. Seven individually source-valid moments plus their actual surrounding dialogue produced **six Luna content-angle candidates** in a separately labelled partial diagnostic. Original extraction remains failed; two rejected records unchanged. Exactly one new angle request, cost $0.009089175, no new extraction/embeddings. Actual cache-only replay preserved all candidate IDs/timestamps with zero new requests/$0. See the [six-angle review](../research/week1-gpt6-luna-content-angle-review.md); earlier no-angle statements below describe the preceding extraction checkpoint.

Latest update, 8 October 2026: the user supplied a new key and authorised an **uncapped Luna retry**. Actual/template env now omits output-cap fields and disables local input rejection, retaining full dialogue and strict source/schema validation. A3 returned nine proposals, seven individually valid, but failed two quotation checks before Call 2. Reported extraction cost $0.016626175; angle cost $0 (not attempted); zero embeddings. See the [uncapped retry review](../research/week1-gpt6-luna-uncapped-retry-review.md). Earlier A1/A2 results below remain historical, not the latest outcome. All 112 offline tests pass.

Current scope, 8 October 2026: the user authorised a paid Week 1 `openai/gpt-6-luna` comparison and per-stage cost tracking. **No embeddings until subsequent approval.** The first request received HTTP 402; a single announced lower-output-reserve retry returned 14 proposed moments but failed strict validation. Eleven records are individually valid in offline review; two have invalid quote binding and one an invalid enum. Call 1 reported $0.017861675; Call 2 was not attempted, cost $0. Both attempts and unknown billing on the rejection remain saved. See the [Luna execution/cost review](../research/week1-gpt6-luna-test-review.md). Historical Apodex output is a separate five-candidate partial diagnostic, not Luna output or complete weekly success; its [test/quality review](../research/week1-generation-only-test-review.md) and actual zero-request replay remain preserved. Earlier no-inference statements below are historical checkpoints.

Layout update, 8 October 2026: execute the current package from `content_atelier/backend/`; the datastore remains here at `testing/.data/`. The relocated implementation passed 43 offline tests. No stored transcript, credential or existing datastore was moved as part of that restructure.

Status update, 7 October 2026: the initial file-backed backend and dependency-aware reuse are implemented. Source planning and empty synthetic runs have occurred; their ignored local artifacts can exist in `.data/`. Nonempty synthetic outputs are exercised in isolated test directories. No live inference/payment call or real pgvector table creation has occurred. The layout and contracts below describe the fuller design, not a claim that every planned feature is implemented; see [the implementation README][implementation] for current paths, replay commands, tests and limits.

This is the dedicated area for the planned local, week-by-week experiment setup. See the [full design][design], especially §8 for paid-output preservation/reuse and §§4–5 for historical clocks and experiment branches.

Current input/model decision: numbered weekly folders beginning June 2026, exact intervals still unverified; Luna supersedes Apodex as the active configured model for both LLM stages, retaining the same source and prompt templates for comparison. Small/1,536 is configured but completely dormant until approval. The [focused comparison][models] remains historical research, not evidence that embeddings ran.

The configured existing backfill root is `backend/zoom_backfill_meetings/`, with week1/week2 folders; `CONTENT_ATELIER_TRANSCRIPT_ROOT` can override it. No source files were moved. A specific Git ignore rule protects this private input root. Week 1 planning parsed nine transcript exports, but exact occurrence dates and client authority have not been validated.

## Storage roles

- JSON: authoritative versioned experiment records/artifacts during the schema-discovery phase.
- Markdown: generated weekly reviews, document/experiment indexes and deliberately recorded human decisions.
- Local pgvector: rebuildable search projection of one canonical vector per generated angle; not the only copy of the vector or a substitute for source provenance.

Runtime private records live beneath `testing/.data/` by default. The `.data/` rule excludes them while this README remains trackable. Normalised source snapshots can contain private transcript content; protect and back up the directory. Ignore rules are not encryption or permission controls.

## Proposed runtime areas

| Area beneath .data | Purpose |
|---|---|
| catalog | Source identities/revisions/permissions, policy bundles, model/profile/config snapshots |
| objects | Original source bytes and validated content-addressed artifacts |
| service_calls | Exact paid/free requests, attempts, returned responses, usage, validation and errors; supersedes the earlier proposed paid_calls label |
| cycles | Weekly source manifests, exact boundaries and interval coverage |
| experiments | Branch/run lineage, history snapshots, candidates, matches, ranking and reviews |
| ledgers | Shared service-attempt/reuse/correction/schema events, paid/free cost views and human-readable experiment index |
| exports | Mapping/manifests for later PostgreSQL import without regenerating paid outputs |

Do not create fictional completed records to populate this layout. Date/window examples in the design are contracts, not evidence that a week was imported.

## Paid-output requirements

Apply the same preservation contract to free calls: their quota, route availability, outputs and provenance must also be reproducible. Record service tier and actual route; prevent silent paid fallback. `service_calls/` and validated cache pointers are now implemented. Shared `ledgers/service-attempts.jsonl`, request leases and budget enforcement remain design requirements, not completed features.

Per-attempt `cost.json`, run `costs/<artifact-id>.json` and `cost_summary.json`/`.md` are implemented for both LLM stages. Actual returned billing is retained even on content rejection; missing billing is unknown and replay adds zero new cost. A run with unknown billed attempts has an unknown total and an explicit known subtotal. Raw failures remain reviewable but are not automatically accepted/replayed into the validated pipeline. Luna's native usage is returned by the provider; its local preflight is a conservative byte allowance, not a claimed native tokenizer count.

1. Persist the logical request intent, exact input dependencies, rendered prompts/schema/model parameters and approved route before a call.
2. Claim a request-key lease; enforce configured budgets before spending.
3. Save returned raw output and safe provider/request/usage metadata immediately, before parsing or database projection.
4. Store validated stage outputs separately with IDs/hashes linking back to the raw attempt and exact source context.
5. Cache/replay only complete, compatible, permitted artifacts. A changed policy/input/model/signature may invalidate descendants.
6. A cache hit creates no new generation event or paid charge; keep the original generation and cost references.
7. Record failed, partial and billing-unknown attempts; never assume a disconnected request was free.
8. Do not persist API keys, bearer headers, fabricated source quotes or inaccessible internal reasoning.
9. Rebuild local pgvector from saved vectors; schema migration alone must not require new paid inference.
10. Preserve source withdrawal/retention requirements across files, Markdown, vectors and backups.

Threshold/decay changes should need no new LLM or embedding call. A generation-prompt change should reuse compatible extraction. A signature/profile change requires a new compatible active vector, not a mixed-space comparison.

## Weekly experiment discipline

Begin with one authorised week of Zoom transcripts, inspect moments/angles and record model-independent human labels, then deliberately advance the chronology.

Verify actual weekly intervals from meeting occurrence metadata rather than deriving dates from folder labels; sort numeric week indices, not lexical names. Distinguish missing data from a genuine empty week. Future folders on disk stay excluded from earlier source/history snapshots.

Record real execution timestamps separately from named simulated generation/scoring timestamps. Cache replay must not refresh angle recency. All valid generated candidates remain saved; only eligible branch history enters a given comparison.

Controlled A/B trials fork the same prior-history snapshot so one variant does not become another's accidental freshness penalty. The chosen chronological branch advances week by week; later weeks stay excluded from earlier snapshots.

## Write/recovery contract

Single-writer initially; schema validation; immutable payloads; temporary-file then atomic commit on the same filesystem; commit payloads before changing manifests; checksum/reference reconciliation on recovery. This is a file store, not an assertion of multi-document database transactions or exactly-once provider billing.

## Outstanding choices

The LLM model is approved and embedding/LLM profiles are configurable. Luna extraction capacity and returned billing were tested, but successful whole-week acceptance and its angle-stage quality remain untested after rejection. Further paid runs need a deliberate decision and agreed limits. “Final generation” currently means deterministic selection, not a third LLM pass. Very-close keep-both selection remains an earlier open clarification. No additional LLM similarity judge is allowed.

Privacy gate: inspected NVIDIA free endpoints prohibit confidential/personal uploads. Do not send raw client transcripts there; synthetic or verified non-confidential fixtures only. GPT-OSS/Qwen also need actual provider-policy verification. Free plan routing/quotas must meet requirements; otherwise stop. Local pgvector does not make remote inference private/local. Source-backed details are in the [comparison][models].

The central [next-call ledger][ledger] tracks client authority, remaining internal questions and future dated meeting records.

[design]: <C:/Users/Jainil Trivedi/Desktop/Wedding_Industry_Ads/content_atelier/content_atelier_week_by_week_testing.md>
[ledger]: <C:/Users/Jainil Trivedi/Desktop/Wedding_Industry_Ads/content_atelier/to_be_asked_in_next_call.md>
[models]: <C:/Users/Jainil Trivedi/Desktop/Wedding_Industry_Ads/content_atelier/content_atelier_embedding_and_free_model_comparison.md>
[implementation]: <C:/Users/Jainil Trivedi/Desktop/Wedding_Industry_Ads/content_atelier/backend/README.md>
