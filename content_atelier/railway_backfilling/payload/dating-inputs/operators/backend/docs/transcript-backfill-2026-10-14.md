# Transcript-only backfill

This operator admits selected original transcripts, builds deterministic passage-linked chunks and encodes only those chunk texts. It never submits a weekly generation run. Key moments, angles, angle vectors, approval states, briefs and downstream records are protected by database checksums before and after execution. Earlier source, week and execution rows are also protected.

The October 14 selection contains 164 distinct Zoom originals and six additional Fathom recordings, across Weeks 1–20 beginning June 1, 2026. The six duplicate Zoom files in Weeks 10/11 are assigned to Week 10 under the user's fewer-transcripts rule; Week 11 has the additional Bri recording. Both sets of disk originals remain intact. Thirteen overlapping Fathom captures and five metadata-only paired alternatives are excluded from admission.

Native Fathom raw JSON is archived byte-for-byte. SQL stores a reversible passage view containing every segment's original text and full supplied speaker label, start timestamp, source segment index and matched email where supplied. Missing segment end times stay null. `source_type`, recording identity, source link, occurrence timestamp and provider metadata are retained. No synthetic VTT timings are generated. Normalized view hashes are separate from original-byte hashes.

Whole-turn chunking retains Zoom's existing 2,400-character body target and 90-second conversational-gap rule. Fathom uses supplied start times where end times are unknown. Preflight verifies exact once-only passage coverage and the existing conservative embedding input bound. The observed maximum input is 2,557 UTF-8 bytes. This is a source-integrity check, not a retrieval-quality evaluation.

From the backend directory:

```powershell
python -m backend_pipeline.backfill --duplicate-week 10 --local-preflight
python -m backend_pipeline.backfill --duplicate-week 10
python -m backend_pipeline.backfill --duplicate-week 10 --prepare-only
python -m backend_pipeline.backfill --duplicate-week 10 --execute
```

`--local-preflight` performs no database or external service work. The default checks the local database read-only. `--prepare-only` admits originals and stores chunks with encoding disabled; its transport guard forbids every HTTP request. `--execute` enables encoding only within this process and permits only POST requests to `https://openrouter.ai/api/v1/embeddings`, with exact frozen chunk text, the approved `openai/text-embedding-3-small` model and 1,536 dimensions. Persistent configuration files remain unchanged.

Week 1/2's existing 329 vectors are verified without re-admission or replacement. New encoding jobs use `transcript_encoding` scope and are processed by their own run ID, never by a generic worker drain. Cached vectors and valid saved provider responses are reused. A failed job requires inspection and an explicit `--retry-failed` invocation; the operator never automatically retries a dispatched request. An HTTP timeout can still represent an unknown provider outcome.

Immutable source selection, protected baseline and attempt dispatch records are retained at `.storage-artifacts/verification/transcript-backfill/<plan-hash>/`. Local preparation writes `prepared.json`; completed embedding writes `completed.json`. The latest reports are `verification/transcript-backfill-preparation.json` and `verification/transcript-backfill-readiness.json`. These reports distinguish prior compatible cache responses from dispatches in the current attempt.

Do not run overlapping writers. An active pipeline job or changed protected baseline causes preflight to stop. The selection is fixed to the reconciled October 14 corpus; Week 20 is partial. Later deliveries require a new source-selection audit.

Verification covers native segment round trips, absent end times, stable recording identity, invalid timestamps/hash/selection rejection, duplicate source selection, wrong-IST-week rejection, native SQL admission, vector storage and zero-request identical replay. Integration tests run only in `atelier_test`, and the verification fixture rejects external HTTP.
