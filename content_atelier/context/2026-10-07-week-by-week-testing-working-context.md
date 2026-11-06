# Content Atelier — week-by-week testing and paid-output reuse checkpoint

Recorded: 7 October 2026. This preserves the current user request and available working context before any further summarization. Earlier complete context and document snapshots remain in this directory. No private internal reasoning or unavailable messages are claimed.

## Current user request

> for the current testing, we will have the pgvector running locally, we have to discuss on the embedding model that we will use to create embeddings of the generated content angles. Also each content angle will have 1 embedding vector and not multiple ones. we will proceed with the meetings (transcripts of zoom backfilled) of 1 week first to generate the content angles. and then move slowly while testing onto the next week and so on, backfilling as we test it out. I also want to store the temporary data that we use in the form of json like in mongo db, on .md / .json files as ledgers / datastores before we have the actual postgres schema determined. I want to you to thoroughly reason this as we will be using this setup to thoroughly test out the implementation as well as fine tune / refine the implementation as we proceed. we will be using week by week backfilling strategy in order to understand the kind of angles generated to refine them.
>
> NOTE: any where we use paid services i.e. embeddings / llm costing for the content angle, we will be storing the entire pipeline data in order to reuse it wherever possible, store the data in the form of an md / json in a dedicated section and thoroughly reason over this requirement / scenario.
>
> for the embeddings i am thinking of open ai text embeddings 3, suggest me the other openrouter models that i can use for the key moments identification, as well as the initial and the final content angles generation.

## Scope / previous requirements that still apply

This is reasoning and documentation, not authority to run paid calls, install PostgreSQL, launch Docker, restore the deleted backend, import private Zoom data, or deploy services.

Previously confirmed: one PostgreSQL/pgvector database with separate evidence and angle-memory logical collections; every valid generated candidate retained; show every eligible distinct angle strictly above the unrounded adjusted-score threshold; “last turn” means previous completed generation run; transcripts only; no additional LLM similarity judge; Saturday 04:00 Texas time provisional.

Still unresolved: “very close similarity then only include both relevant ones” could mean an old/new comparison pair or both retained as weekly suggestions. Do not silently resolve it.

An asynchronous clarification was asked this turn: does “final content angles generation” mean the final deterministic selected set, or an additional LLM rewrite/refinement pass? No answer has arrived yet. Preserve the two-stage baseline until clarified; model recommendations for an optional rewrite are not implementation of a third stage or permission for a similarity judge.

## Work done this turn so far

Read the OpenAI Docs skill and its model-selection reference completely. Official OpenAI embedding pages were searched/opened. OpenRouter primary model pages and structured-output, provider-routing, usage-accounting and cache documentation were searched/opened; pgvector official documentation opened. These are read-only checks; no model calls were made.

Existing user backend deletions and frontend modifications were observed and preserved. No implementation or document edits have occurred before this checkpoint.

## Findings to incorporate into the design

- Treat JSON as durable machine-readable experiment records, Markdown as derived reviews/decision ledgers, local pgvector as a rebuildable angle-vector search projection.
- User wants one vector per angle. Recommend one canonical structured argument signature and one vector-bearing active record, not separate hook/topic/quote/format vectors. Model/dimension changes require compatible-history rebuild and explicit experiment profile; no mixed spaces even at equal dimensions.
- Delay full relational production schema, not IDs, provenance, revision contracts, stage states, permissions, transactional/atomic file semantics or minimal pgvector scratch columns.
- Save request intent/input/prompt/config before paid calls, returned raw response immediately, parsed validated results separately, actual usage/cost/provider/request IDs and failures. No secrets in files. Reuse only exact compatible valid artifacts; cache hits are not fresh generation events.
- Recompute downstream deterministic ranking/selection free of model calls when only thresholds/decay change. Re-embed only changed canonical signatures, not changed ranks/titles unrelated to semantic projection.
- Week-by-week backfill must keep actual execution time separate from an explicit simulated editorial/generation clock. No future-week history leaks, and no pretending historical backfill creates actual old generation timestamps.
- Isolate A/B experiment branches with the same frozen prior history; keep all generated variants but do not let unrelated model trials contaminate one another's recency tests. Main-branch genuine regeneration retains prior completed runs and all eligible valid candidates.
- “Fine-tune/refine” here means prompts/contracts/context/rubrics/threshold tuning, not authorised model weight training.
- Week 1 may have empty history; history quality differs from empty memory. Week 2 can compare against all valid eligible Week 1 branch candidates.
- Local hosting does not make paid embedding/LLM inference local/private. Source authorisation and retention still apply.

## Verified model facts, 7 October 2026

OpenAI:
- text-embedding-3-small: default 1536 dimensions; USD0.02 per million input tokens.
- text-embedding-3-large: default 3072 dimensions; USD0.13 per million input tokens.
- Both support an explicit dimensions parameter. A proposed large/1536 profile balances the requested single-vector setup and numerical matching; validate on angle-pair labels, do not claim measured task superiority.
- pgvector ordinary vector HNSW/IVFFlat indexes support up to2000 dimensions; 3072 is not a general storage prohibition. Exact search remains the initial recommendation.

OpenRouter candidate catalogue:
- google/gemini-3.8-flash: USD0.75 input /3.75 output per million tokens, 1048576 context, schema outputs listed.
- anthropic/claude-sonnet-5.5: USD2 input /10 output per million, 1M context, schema outputs listed; thinking always on, effort is a cost/depth lever.
- qwen/qwen3.8-flash: USD0.15 input /0.47 output per million, 1M context, schema outputs listed.
- deepseek/deepseek-v4-pro-20260813: advertised USD0.2514 input /4.20 output per million, 1048576 context, schema outputs listed; provider choice changes operational suitability/prices.
All roles are recommendations to test, not evidence of Whitney-specific quality or guaranteed account availability.

Primary source URLs:
- https://developers.openai.com/api/docs/guides/embeddings
- https://developers.openai.com/api/docs/models/text-embedding-3-small
- https://developers.openai.com/api/docs/models/text-embedding-3-large
- https://github.com/pgvector/pgvector
- https://openrouter.ai/google/gemini-3.8-flash
- https://openrouter.ai/anthropic/claude-sonnet-5.5
- https://openrouter.ai/qwen/qwen3.8-flash
- https://openrouter.ai/deepseek/deepseek-v4-pro-20260813
- https://openrouter.ai/docs/guides/features/structured-outputs
- https://openrouter.ai/docs/guides/routing/provider-selection
- https://openrouter.ai/docs/cookbook/administration/usage-accounting
- https://openrouter.ai/docs/guides/features/response-caching
- https://openrouter.ai/docs/guides/best-practices/prompt-caching

Provider-side prompt caching still performs/bills fresh inference; OpenRouter response caching is separate and bounded/evictable. Neither replaces durable local stored artifacts. OpenRouter usage fields include actual costs/token counts and final streamed usage; request/provider metadata must be captured. Require actual schema-supporting endpoints and approved privacy routing, not only model marketing labels.

## Planned next actions

1. Create `content_atelier_week_by_week_testing.md` with the full local/files-first testing strategy, dedicated paid-call artifact/reuse section, tree/JSON contracts, weekly branch/time semantics, eval/test progression, embedding recommendation and sourced OpenRouter alternatives.
2. Create a documentation-only `testing/README.md` describing the dedicated future test/datastore area; no fake runs or paid artifacts.
3. Amend pipeline/storage docs and next-call ledger to link the testing design and record the new user choices; model/profile selection is recommendation, not approved.
4. Validate examples, links, JSON syntax and persistence/reuse invariants. Save new context snapshots without replacing earlier historical snapshots.
5. Final response should explain the design concisely but substantively, give verified recommended model IDs/prices with primary citations, identify final-generation ambiguity and remaining close-pair rule, and state no paid calls/implementation started.


## Completed documentation outcome for this turn

Created:
- `content_atelier_week_by_week_testing.md`: approximately 6,100 words, with 17 numbered sections, detailed dedicated paid-service preservation/reuse contract, datastore tree, illustrative JSON, source/model recommendations and implementation-readiness decisions.
- `testing/README.md`: documentation-only dedicated local datastore area. No `testing/.data/` directory/data, imported Zoom transcripts, paid outputs, generated candidates or completed runs were created.

Amended:
- `transcript_to_content-angle.md`: links new testing design; confirms one active angle vector and file-backed initial authority; separates eventual infrastructure/schema from first harness; clarifies simulated clock/branch history and final-generation ambiguity.
- `content_atelier_vectordb.md`: initial local JSON/Markdown/pgvector projection mode; one active canonical angle vector; private paid artifacts distinct from general logs; wider embedding inventory not first-slice prerequisite.
- `to_be_asked_in_next_call.md`: U-07–U-11 for new user requirements, I-06–I-09 for model/profile, final-generation, timeline/branch and budgets/privacy choices; D-07/D-08 indexes added. Zoom first-week choice partly resolves I-03, exact dates/exports/coverage remain open.

Recommendation: start one chronological profile with OpenAI text-embedding-3-large, explicit1536 dimensions; Stage1 Gemini3.8Flash and Stage2 Sonnet5.5 through approved OpenRouter routes. Qwen3.8Flash and dated DeepSeekV4Pro0813 are challengers to test. These are not confirmed model selections or measured Whitney-specific performance. Verified primary-source model prices/capabilities are preserved in the design.

Important reasoning conclusions: JSON durable source of truth, Markdown reviews/decision ledgers, local pgvector rebuildable search projection; one active vector per angle with archival copies/paid-response provenance; exact profile compatibility before reuse; no paid calls for threshold/report/DB-rebuild changes; saved raw output can be locally reparsed; cache replays do not create generation events; historical simulated dates remain explicitly separate from actual timestamps; A/B variants share frozen prior history and do not contaminate one another's penalties. Full returned paid data does not include secrets or inaccessible hidden model state. Fine-tuning here is prompt/contract/threshold refinement, not model-weight training.

Verification: five current documents passed reference-definition and balanced-fence checks; the illustrative JSON parsed; 29 local file reference targets exist. Git ignore checked a representative future testing/.data paid-response path as ignored and README as trackable, without editing .gitignore. Five arithmetic/simulation checks passed for virtual seven-day age, actual same-time zero age,28dayhalf-life decay, model price ratio and example cost total. For an explicitly invented token budget, extraction .1125 + generation .14 + embedding .0039 = USD.2564; this is not WIA's actual weekly cost. All original tracked backend deletions/frontend modifications were preserved.

New full snapshots (do not overwrite earlier historical versions):
- `context/2026-10-07-week-by-week-testing-design-snapshot.md`
- `context/2026-10-07-testing-datastore-readme-snapshot.md`
- `context/2026-10-07-week-by-week-ledger-snapshot.md`
- `context/2026-10-07-transcript-to-angle-file-backed-testing-snapshot.md`
- `context/2026-10-07-vector-storage-file-backed-testing-snapshot.md`

No answer to the asynchronous final-generation question has arrived at this checkpoint. The earlier very-close keep-both meaning also remains unresolved. No additional LLM judge, paid call, actual harness, SQL migration, Docker/Postgres install, model evaluation or private source import was performed.

Final handoff should lead with the sound testing setup and new document link, explain storage/reuse and historical/A-B discipline, recommend the exact verified embedding and OpenRouter model IDs with primary citations, and distinguish deterministic final selection from optional yet-unconfirmed refinement. Ask for the first historical week/exports and paid budget when preparing implementation, without blocking documentation completion or claiming such inputs were already supplied.
