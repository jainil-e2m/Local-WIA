# Transcript-only backfill completed — October 15, 2026

Verified 2026-10-15 10:57:29 IST. Source selection is the gathered October 14 corpus; Week 20 remains partial.

**170 selected transcripts (164 Zoom and six additional Fathom) have 2,657 stored chunks and 2,657 verified 1,536-dimensional embeddings.** Existing Week 1/2 vectors: 329 preserved. New chunk vectors: 2,328.

**No key moments or content angles were generated, refined, rescored or changed.** All 14 existing key moments, 13 content angles (including their vectors and approval states), two briefs and other downstream records match the protected pre-backfill checksums. Earlier source, week, pipeline-run, job and event records included in the baseline are unchanged.

## Preserved state and resumption

- Source files, the Fathom import adapter, selected-source manifest, local chunk preparation, source archives and the protected database baseline survived the session change. The source plan hash stayed `86ee6c99550f3dd7cf9081340535525ac696a30edfe49a8d78728ebaa3a9dbf7`.
- The stopped PostgreSQL container was restarted with its existing data volume. Before resuming, read-only checks confirmed 170 stored transcripts, 2,657 chunks, 329 prior vectors, no active/failed embedding jobs and unchanged protected records.
- The user explicitly authorized OpenRouter embedding requests before resumption. Only exact selected chunk text was sent to `https://openrouter.ai/api/v1/embeddings`, using `openai/text-embedding-3-small`, 1,536 dimensions.
- The remaining embedding work completed with 81 new embedding batches. No retry was needed. All 20 transcript-encoding jobs are completed and no pipeline jobs are queued or running.

## Weekly results

| Week | IST calendar range | Selected transcripts | Chunks | Verified embeddings |
|---:|---|---:|---:|---:|
| 1 | 2026-06-01–2026-06-07 | 9 | 136 | 136 |
| 2 | 2026-06-08–2026-06-14 | 11 | 193 | 193 |
| 3 | 2026-06-15–2026-06-21 | 5 | 67 | 67 |
| 4 | 2026-06-22–2026-06-28 | 6 | 97 | 97 |
| 5 | 2026-06-29–2026-07-05 | 6 | 74 | 74 |
| 6 | 2026-07-06–2026-07-12 | 6 | 80 | 80 |
| 7 | 2026-07-13–2026-07-19 | 11 | 158 | 158 |
| 8 | 2026-07-20–2026-07-26 | 10 | 210 | 210 |
| 9 | 2026-07-27–2026-08-02 | 5 | 86 | 86 |
| 10 | 2026-08-03–2026-08-09 | 6 | 86 | 86 |
| 11 | 2026-08-10–2026-08-16 | 1 | 9 | 9 |
| 12 | 2026-08-17–2026-08-23 | 8 | 132 | 132 |
| 13 | 2026-08-24–2026-08-30 | 12 | 192 | 192 |
| 14 | 2026-08-31–2026-09-06 | 13 | 288 | 288 |
| 15 | 2026-09-07–2026-09-13 | 10 | 134 | 134 |
| 16 | 2026-09-14–2026-09-20 | 14 | 220 | 220 |
| 17 | 2026-09-21–2026-09-27 | 11 | 123 | 123 |
| 18 | 2026-09-28–2026-10-04 | 8 | 91 | 91 |
| 19 | 2026-10-05–2026-10-11 | 13 | 201 | 201 |
| 20 | 2026-10-12–2026-10-18 | 5 | 80 | 80 |

## Source selection

The six repeated Zoom files in Weeks 10/11 are selected only in Week 10 under the user’s fewer-transcripts rule. Week 11 contains the additional Bri Fathom call. This is a user-directed folder assignment; unknown Zoom occurrence dates were not fabricated. Both sets of disk originals remain intact.

The thirteen downloaded Fathom captures corresponding to existing Zoom calls remain alternate source evidence and are excluded from admission. Five simultaneous alternative Fathom captures remain metadata-only. The six additional Fathom calls are admitted with native provider identity, original JSON, source speaker labels, source links, occurrence dates, original segment start timestamps and null end times where Fathom supplied none.

## Independent verification

- All 170 selected archived originals match their source-byte SHA-256 hashes; all 170 original Zoom disk files match the gathering inventory.
- Every admitted passage occurs exactly once across the deterministic chunks. Stored chunk texts, source references and hashes match reconstruction from the admitted originals.
- Every stored vector has 1,536 finite dimensions and a nonzero norm. Its float32 digest matches the exact indexed provider response for its exact request text and compatible model/profile. All 93 provider receipts were audited: 12 prior and 81 new.
- Native Fathom segment text and speaker labels round-trip against the immutable original JSON; no end timestamps were invented.
- The database schema remains the existing 13-table baseline. Persistent generation, encoding, refinement and legacy external-call switches remain disabled. Encoding was enabled only in the bounded operator process.
- Newly created job stages are only source admission (18), transcript chunk preparation (18), and transcript chunk embedding (18). No generation job was created.

Offline and isolated PostgreSQL tests passed during implementation; lint passed on resumption. The live receipt/source/protected-record audit passed. Retrieval relevance and editorial output quality are outside this transcript-storage operation.

## Provider-reported embedding usage

New requests: **81**. New prompt tokens: **1,489,486**. Provider-reported new embedding cost: **$0.02978972 USD**. This excludes historical Week 1/2 costs and any account purchase fees.

## Artifacts

- [Embedding readiness](<../backend/.storage-artifacts/verification/transcript-backfill-readiness.json>)
- [Independent verification](<../backend/.storage-artifacts/verification/transcript-backfill-independent-verification.json>)
- [Preparation report](<../backend/.storage-artifacts/verification/transcript-backfill-preparation.json>)
- [Operator documentation](<../backend/docs/transcript-backfill-2026-10-14.md>)

Implementation: `backend_pipeline/fathom_sources.py` adds native admission; `storage_sources.py` handles absent end times; admission accepts explicitly selected paths; `backfill.py` restricts execution to preparation and chunk encoding. No schema migration or continuous connector was introduced.

The gathered transcript corpus is ready for later explicitly requested retrieval or generation work. Key-moment identification and content-angle generation remain deferred.
