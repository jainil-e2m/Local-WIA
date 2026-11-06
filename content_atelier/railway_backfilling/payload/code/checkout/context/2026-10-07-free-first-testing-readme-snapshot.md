# Content Atelier testing datastore

Status: documentation only, created 7 October 2026. No pipeline has run; no paid output, private Zoom transcript, generated candidate or database table is created here by this task.

This is the dedicated area for the planned local, week-by-week experiment setup. See the [full design][design], especially §8 for paid-output preservation/reuse and §§4–5 for historical clocks and experiment branches.

Latest input/model review: the user will supply roughly three months of numbered weekly meeting folders beginning June 2026. Proposed private input root: `content_atelier/transcripts/week1/`, `week2/`, etc.; exact boundaries require manifests. The current first-model recommendation is Small/1,536 embeddings and GPT-OSS 120B free for the two LLM stages, subject to approval and a suitable data route. See the [focused comparison][models]. No source files have been imported.

An existing user backfill root was subsequently observed at `backend/zoom_backfill_meetings/`, with week1/week2 folders. Prefer using it through a configurable source root; the transcripts path is only an alternative, not a relocation instruction. Contents/dates have not been validated. The existing root appears as untracked Git content; protect raw sources before committing. No files were moved or ignore rules changed.

## Storage roles

- JSON: authoritative versioned experiment records/artifacts during the schema-discovery phase.
- Markdown: generated weekly reviews, document/experiment indexes and deliberately recorded human decisions.
- Local pgvector: rebuildable search projection of one canonical vector per generated angle; not the only copy of the vector or a substitute for source provenance.

Runtime private records should live beneath `testing/.data/`. Git's ignore check confirmed a representative future paid-response path is excluded by the existing `.data/` rule, while this README remains trackable. No private artifact exists yet. Ignore rules are not encryption or permission controls.

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

Apply the same preservation contract to free calls: their quota, route availability, outputs and provenance must also be reproducible. Record service tier and actual route; prevent silent paid fallback. The common area is `service_calls/`, with `ledgers/service-attempts.jsonl`; these are proposals, not migrated runtime directories.

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

Embedding profile and LLM stages are recommendations pending selection/testing. “Final generation” may mean a new refinement pass or just the deterministic selected set. Very-close keep-both selection remains an earlier open clarification. No additional LLM similarity judge is allowed.

Privacy gate: inspected NVIDIA free endpoints prohibit confidential/personal uploads. Do not send raw client transcripts there; synthetic or verified non-confidential fixtures only. GPT-OSS/Qwen also need actual provider-policy verification. Free plan routing/quotas must meet requirements; otherwise stop. Local pgvector does not make remote inference private/local. Source-backed details are in the [comparison][models].

The central [next-call ledger][ledger] tracks client authority, remaining internal questions and future dated meeting records.

[design]: <C:/Users/Jainil Trivedi/Desktop/Wedding_Industry_Ads/content_atelier/content_atelier_week_by_week_testing.md>
[ledger]: <C:/Users/Jainil Trivedi/Desktop/Wedding_Industry_Ads/content_atelier/to_be_asked_in_next_call.md>
[models]: <C:/Users/Jainil Trivedi/Desktop/Wedding_Industry_Ads/content_atelier/content_atelier_embedding_and_free_model_comparison.md>
