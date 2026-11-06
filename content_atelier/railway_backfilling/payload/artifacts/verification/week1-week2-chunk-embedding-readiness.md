# Week 1 and Week 2 chunk embeddings

All 329 existing transcript chunks were embedded through OpenRouter using `openai/text-embedding-3-small` and stored as `vector(1536)` in PostgreSQL.

| Week | Chunks | Stored compatible vectors |
|---|---:|---:|
| June 1-7, 2026 | 136 | 136 |
| June 8-14, 2026 | 193 | 193 |

The operation used 12 requests. Provider-reported usage: 208,733 input tokens; provider-reported cost: $0.00417466.

Independent read-only verification matched every stored float32 vector to its exact indexed provider response, request text, source transcript and immutable chunk hash. All vectors have 1,536 finite dimensions and a nonzero norm. Two sample exact cosine searches returned the original chunk with cosine approximately 1. This checks storage/search mechanics, not retrieval relevance.

Both encoding jobs completed. The existing 13-table schema, 12 angle vectors, original transcripts, chunk text/ranges, moments, approval state, weekly review state and earlier execution records were preserved. New execution/provenance records use the existing runs/jobs/events tables. No brief, pack, asset or calendar item was generated.

Existing whole-turn boundaries and filename headers were preserved. Every input was at most 2,543 UTF-8 bytes; no text was truncated. Cached responses/vectors make retries resumable without repeating successful paid work. All persistent external switches remain false; permission was local to this approved operation.

Verification: 62 offline contract, chunk recovery, SQL and comparison tests passed with external HTTP guarded. Hybrid full-text retrieval, contextual relevance evaluation, briefing and Gate 2 remain later work.

[Encoding report](week1-week2-chunk-embedding-readiness.json) | [Independent verification](week1-week2-chunk-embedding-verification.json)
