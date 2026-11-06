# Context checkpoint: embedding comparison and free-model testing

This checkpoint preserves the available user instructions, decisions, source findings, and work state at the context boundary on 7 October 2026. It does not claim to reconstruct unavailable messages. Earlier complete document snapshots and context ledgers in this directory preserve the prior reasoning work.

## Latest request, verbatim

> i will be providing you the meetings of the past 3 months that we will be using for the testing as well as the backfilling purpose. i will place them accordingly in the relevant folders with the structure like /week1 , /week2 , /week3, /week4 and so on. the week 1 begins on June 2026.
>
> also compare the vector sizes and efficiency and costing of text embedding 3 large and 3 small as i am more inclined towards 3 small. also for the 2 content angle & key moments, tell me from a free model like say gpt oss or nemotron, other efficient model for this task.

## Scope and confirmed decisions carried forward

- This is a design/reasoning turn. Do not implement the backend, install services, ingest supplied/private transcripts, or make inference calls.
- The initial slice is transcripts only, ending at the visible content-angle set. Briefs, packs, and publishing are later stages.
- Use one local PostgreSQL/pgvector database with separate logical angle-memory and historical-evidence collections/tables.
- Each angle has one active canonical embedding vector, not multiple semantic views.
- Two main LLM stages: identify source-grounded key moments and surrounding context; generate grounded, distinct candidate angles. Similarity, recency penalties, and final selection are deterministic. No additional LLM similarity judge is authorized.
- Show every eligible distinct angle strictly above the unrounded adjusted-score threshold, not a fixed four-angle cap.
- Last turn means the previous completed generation run, not a physical batch or cache replay.
- Save all valid generated angles with lifecycle statuses; distinguish stored records from history eligible for a particular experiment branch.
- Historical penalty uses the maximum eligible similarity/recency risk: normalized cosine above a threshold multiplied by exponential generation-age decay. Adjust the base score using a bounded maximum penalty. Thresholds and decay require calibration.
- Use authoritative JSON experiment records, readable Markdown reviews/ledgers, and a rebuildable local pgvector projection until the production schema is settled.
- Preserve usable requests, returned responses, prompts/configuration, context/evidence, validated artifacts, costs, and lineage for paid calls. Preserve free-call artifacts too for reproducibility and quota avoidance. Never store secrets.
- Backfill week by week with frozen prior-history snapshots for fair comparisons. Actual execution timestamps and explicitly simulated editorial/generation clocks must remain separate.
- The user plans roughly three months of meeting transcripts, numbered week folders, starting in June 2026. Exact start/end dates, folder root, and number of weekly windows are not confirmed; no transcripts have been loaded in this turn.
- Saturday 04:00 Texas time is provisional. America/Chicago is only an assumption if the client means Central Texas. Exact window, late arrivals, and week1 dates remain open.
- Prompt/rubric/threshold refinement is in scope; training model weights is not authorized.
- User preference for text-embedding-3-small is not yet a final approved model profile.
- Existing ambiguity about very-close pairs and any final LLM refinement remains recorded in the clarification ledger; do not invent an answer.

## Current-turn actions already performed

- Announced source/model research and use of the OpenAI Docs skill.
- Read the skill completely and its model-selection reference.
- Checked current official OpenAI model/documentation pages, official pgvector documentation, and OpenRouter catalogues/limits through read-only browsing.
- Inspected workspace inventory and relevant existing design-document sections.
- No document edits before this checkpoint, no API inference, no service changes, no credentials read.
- Existing tracked backend deletions and unrelated frontend modifications belong to the user and must be preserved.

## Verified source findings

### Embeddings

- OpenAI text-embedding-3-small: default 1,536 dimensions, standard price USD 0.02 per million input tokens.
- OpenAI text-embedding-3-large: default 3,072 dimensions, standard price USD 0.13 per million input tokens.
- Both support shortening through the dimensions parameter. Shortening does not change the model's input-token price. Equal dimensions do not mean equal embedding spaces.
- Official pgvector vector storage is 4 * dimensions + 8 bytes: 6,152 bytes at 1,536 dimensions; 12,296 bytes at 3,072 dimensions, excluding rows, indexes, metadata, and JSON artifacts.
- Small 1,536 and Large shortened to 1,536 have equal vector storage and comparison dimension. The difference is model cost and task-measured quality, not vector size.
- Large costs 6.5 times Small for the same input-token count. Exact cosine scan component work scales with corpus size times dimension; do not promise twice the wall-clock speed from halving dimensions.
- Standard vector HNSW/IVFFlat indexing supports up to 2,000 dimensions; 3,072-dimensional vectors can still be stored and exactly queried. Alternative representations/index approaches exist but are unnecessary for this initial small exact-scan test.
- Proposed first experiment should now be Small at 1,536 dimensions, superseding the earlier proposed Large-at-1,536 starting profile. This is a recommendation, not user approval.

Sources:

- https://developers.openai.com/api/docs/models/text-embedding-3-small
- https://developers.openai.com/api/docs/models/text-embedding-3-large
- https://developers.openai.com/api/docs/guides/embeddings
- https://github.com/pgvector/pgvector

### Free OpenRouter candidates (catalogue listings, not tested endpoint availability)

- openai/gpt-oss-120b:free: listed free, 131,072 context; initial candidate for both logical stages.
- openai/gpt-oss-20b:free: listed free, 131,072 context; smaller extraction challenger, not guaranteed lower hosted latency.
- nvidia/nemotron-3.5-lightning:free: listed free, approximately one-million-token context; extraction challenger.
- nvidia/nemotron-3-super-120b-a12b:free: listed free, 262,144 endpoint context; synthesis/angle challenger. Do not confuse advertised model capability with endpoint context.
- qwen/qwen3.8-27b:free: listed free, 262,144 context; another extraction/generation challenger.
- CRITICAL: both inspected NVIDIA free endpoint pages explicitly prohibit uploading confidential information or personal data and state that use is logged for security/product improvement. Do not recommend sending raw WIA/client transcripts there. Use only authorized, genuinely non-confidential/synthetic material. Removing names alone is insufficient.
- Absence of that banner for GPT-OSS/Qwen is not proof of acceptable provider privacy. Verify the actual route and client permission before sending real transcripts.
- Open weights are not synonymous with a free hosted API. Local hosting entails hardware and operational costs and is not authorized here.
- Free quota, availability, schema support, and provider routing must be verified; do not silently fall back from :free to a paid model.
- Current OpenRouter pricing search result lists 50 requests/day on Free and no data-policy-based routing on Free. Finish reading the actual current pricing/limits page before giving exact quota claims.

Sources:

- https://openrouter.ai/openai/gpt-oss-120b:free
- https://openrouter.ai/openai/gpt-oss-20b:free
- https://openrouter.ai/nvidia/nemotron-3.5-lightning:free
- https://openrouter.ai/nvidia/nemotron-3-super-120b-a12b:free
- https://openrouter.ai/qwen/qwen3.8-27b:free
- https://openrouter.ai/docs/api_reference/limits
- https://openrouter.ai/pricing/

## Remaining work in this turn

1. Finish verifying free-plan quotas/routing limitations and exact comparison arithmetic.
2. Create a focused embedding/free-model comparison document; update existing testing specification, vector/pipeline amendments, datastore README, and clarification ledger without disturbing unrelated edits.
3. Recommend transcripts/week1, transcripts/week2, etc. as an input convention; require a manifest with actual intervals rather than assuming dates from folder names. Sort numerically, not lexically. Do not fabricate source files or complete week folders.
4. Preserve full updated document snapshots and update this continuity record before final handoff.
5. Explain Small-at-1,536 recommendation, qualified free-model options/privacy restrictions, remaining week1 date question, and that implementation/inference has not begun.

## Existing artifact locations

- content_atelier/content_atelier_vectordb.md
- content_atelier/transcript_to_content-angle.md
- content_atelier/content_atelier_week_by_week_testing.md
- content_atelier/to_be_asked_in_next_call.md
- content_atelier/testing/README.md
- content_atelier/context/2026-10-07-week-by-week-testing-working-context.md
- content_atelier/context/2026-10-07-editorial-and-architecture-context.md
- Earlier whole-document snapshots in content_atelier/context preserve prior stages.

The supplied solution architecture in Downloads is reference material; do not edit it. No transcript root exists yet. Existing .gitignore excludes transcripts/, corpus/, VTTs, .data/, credentials and logs; testing/.data remains a planned private runtime datastore.

## Completed research and documentation outcome

The earlier working-state notes above are retained chronologically. Subsequent inventory found user-owned `backend/zoom_backfill_meetings/week1/` and `week2/` containers. Only directory names were inspected; source contents, date ranges and coverage were not read or ingested. Reuse that existing root through configuration rather than moving inputs or restoring backend code. Git status reports the backfill area as untracked, so it is not fully ignored. Documentation flags protecting the source root before a commit; no .gitignore change or source move occurred. The alternative transcripts/ root is already ignored.

Current OpenRouter pricing page confirms its Free plan lists 50 requests/day, no contractual SLA and no data-policy-based routing. The current limits document exposes free_model_daily_requests used/limit/remaining via key information; some numerical policy table cells are absent in the readable rendering. The answer therefore uses the published Free-plan daily figure and recommends checking actual account counters, without guessing minute limits or promising privacy routing on Free. No account key was read and no endpoint availability/inference was tested.

The new researched document is `content_atelier_embedding_and_free_model_comparison.md`. It recommends Small/1,536 first, verifies standard prices/storage, compares Large at default and shortened dimensions, gives bounded free-model stage hypotheses, foregrounds NVIDIA free confidentiality restrictions, and records chronology/evaluation contracts. The OpenAI Docs skill influenced use of verified official model prices, dimensions and compatibility guidance rather than prior defaults.

The broader testing design, ledger, testing README, pipeline and vector-storage reference were reconciled. Their earlier proposed Large/Gemini/Sonnet starting profile is explicitly superseded, not erased from historical snapshots. Paid models remain reference alternatives, not automatic fallbacks. Proposed shared runtime paths are now testing/.data/service_calls and ledgers/service-attempts.jsonl for paid and free artifacts; no runtime store exists or was migrated. All prior selection, one-vector, no-judge and clock/branch requirements remain in force.

Model roles remain hypotheses, not a Whitney-specific benchmark or final user approval: GPT-OSS 120B free as the initial two-stage reference; GPT-OSS 20B or Qwen 27B free as controlled challengers; Nemotron Lightning/Super free only for genuinely permitted non-confidential/synthetic material. Every cloud provider route requires its own privacy/schema verification. The pipeline still pays for embeddings even with zero-price LLM endpoints.

Verified arithmetic: vector(1536) = 6,152 bytes; vector(3072) = 12,296 bytes; 10,000-vector payloads approximately 58.67 and 117.26 MiB respectively. At 1,000 signatures averaging 300 tokens, Small = USD0.006 and Large = USD0.039; cost ratio 6.5. These are calculations and invented-volume examples, not a weekly usage quote or latency/model-quality benchmark.

Document checks: six edited/new current documents have balanced fences and resolved Markdown reference IDs; the illustrative JSON block parses. Twelve unique existing local reference targets were verified. Git ignore checks passed for future transcripts/week1 manifests and testing/.data/service_calls and shared ledger examples. Unrelated tracked backend deletions, frontend modifications and user-created Zoom input directories were preserved. No inference, private import, install, migration, code restoration, deployment or schedule creation took place.

Full latest document snapshots (earlier versions remain untouched):

- 2026-10-07-small-embedding-free-model-comparison-snapshot.md
- 2026-10-07-free-first-testing-design-snapshot.md
- 2026-10-07-free-first-next-call-ledger-snapshot.md
- 2026-10-07-free-first-testing-readme-snapshot.md
- 2026-10-07-free-first-transcript-to-angle-snapshot.md
- 2026-10-07-free-first-vector-storage-snapshot.md

Remaining choices: exact week1 start/end and actual final interval, approved Small/model profiles and real-source provider permissions, scoring calibration, timeline/branch policy, and the earlier very-close pair/final-refinement ambiguities. No held client meeting or response is invented. Final handoff should lead with Small/1,536 and the qualified free-model recommendation, link the focused comparison/ledger, flag NVIDIA privacy terms, and ask for the exact week1 interval.
