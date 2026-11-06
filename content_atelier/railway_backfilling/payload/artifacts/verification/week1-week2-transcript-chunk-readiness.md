# Week 1 and Week 2 transcript chunk readiness

Verified UTC: 2026-10-12T11:14:30.951916+00:00

The real local PostgreSQL database was inspected in a repeatable-read, read-only transaction. All source files, archived originals, passage maps and stored chunks were checked. No database changes or external calls were made.

| Week | Range (2026) | Transcripts | Original passages | Chunks | Embedded chunks | Embedded angles |
|---|---|---:|---:|---:|---:|---:|
| 1 | 2026-06-01 to 2026-06-07 | 9 | 3238 | 136 | 0 | 6 |
| 2 | 2026-06-08 to 2026-06-14 | 11 | 5218 | 193 | 0 | 6 |

All 20 transcripts have chunks. All 8,456 parsed original passages are represented exactly once by chunk references. Original text, ranges, context headers, chunk IDs and hashes round-trip exactly. Regenerating chunks from the current deterministic chunker reproduces all 329 stored chunks. No orphan chunks or integrity errors were found.

All 329 transcript chunk vectors are null. The preparation jobs are completed with encoding marked `not_requested`. The 12 existing 1,536-dimensional vectors belong to content angles, not transcripts. Transcript chunks therefore cannot yet supply semantic retrieval for briefs.

Current chunks use consecutive whole turns, a 2,400-character body target and a split at conversational gaps over 90 seconds. Oversize individual turns remain intact. The header is the source filename; there is no overlap between consecutive chunks. This differs from the architecture proposal of roughly 200-400-token windows, one-turn overlap and richer date/client/speaker-role context. Meeting occurrence dates remain unknown for all 20 admitted sources.

The approved 13-table/two-vector schema matches its catalog. pgvector 0.8.2 is installed. Transcript chunk indexes are the primary key and unique transcript/content-hash index. No chunk full-text index or pg_trgm extension is installed. Hybrid brief retrieval and chunk encoding remain later implementation work.

No briefs, packs, assets or calendar entries exist. All persistent external-call switches remain false. This verifies source and chunk integrity, not retrieval relevance or editorial coverage.

## Transcript detail

| Week | Transcript | Passages | Chunks | Embedded |
|---|---|---:|---:|---:|
| 1 | Carmen Cruickshank's Personal Meeting Room's transcript (1).txt | 192 | 8 | 0 |
| 1 | Carmen Cruickshank's Personal Meeting Room's transcript (2).txt | 260 | 9 | 0 |
| 1 | Carmen Cruickshank's Personal Meeting Room's transcript (3).txt | 397 | 16 | 0 |
| 1 | Carmen Cruickshank's Personal Meeting Room's transcript (4).txt | 586 | 20 | 0 |
| 1 | Carmen Cruickshank's Personal Meeting Room's transcript.txt | 709 | 20 | 0 |
| 1 | Check-in with Gisselle's transcript.txt | 283 | 11 | 0 |
| 1 | LeadLock Sequence Refresh's transcript.txt | 247 | 16 | 0 |
| 1 | Messaging & Positioning _ The Penny's transcript.txt | 308 | 22 | 0 |
| 1 | Whitney Hodges's Personal Meeting Room's transcript.txt | 256 | 14 | 0 |
| 2 | Ads Strategy Call _ The Penny's transcript.txt | 611 | 26 | 0 |
| 2 | Carmen Cruickshank's Personal Meeting Room's transcript (1).txt | 652 | 27 | 0 |
| 2 | Carmen Cruickshank's Personal Meeting Room's transcript (2).txt | 252 | 12 | 0 |
| 2 | Carmen Cruickshank's Personal Meeting Room's transcript (3).txt | 559 | 13 | 0 |
| 2 | Carmen Cruickshank's Personal Meeting Room's transcript (4).txt | 20 | 1 | 0 |
| 2 | Carmen Cruickshank's Personal Meeting Room's transcript (5).txt | 462 | 14 | 0 |
| 2 | Carmen Cruickshank's Personal Meeting Room's transcript.txt | 1447 | 40 | 0 |
| 2 | Check-in with Gisselle's transcript.txt | 312 | 12 | 0 |
| 2 | GHL AI chat widget Review's transcript.txt | 301 | 12 | 0 |
| 2 | Whitney Hodges's Personal Meeting Room's transcript (1).txt | 282 | 20 | 0 |
| 2 | Whitney Hodges's Personal Meeting Room's transcript.txt | 320 | 16 | 0 |

[Full audit JSON](week1-week2-transcript-chunk-readiness.json)
