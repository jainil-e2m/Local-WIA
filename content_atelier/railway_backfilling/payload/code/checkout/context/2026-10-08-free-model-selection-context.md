# Free-model selection — research and conversation continuity

Recorded 8 October 2026; public catalog inspected at `2026-10-08T07:11:00.1038509Z`, provider endpoints shortly afterward. This file preserves the current reasoning handoff and source evidence under the user's standing instruction to save context/summaries here. It is a recommendation, not model approval, backend migration, client permission or empirical output evaluation. No code/configuration/prompts were changed and no inference/embedding request was sent.

## Current user request

> I have identified a few free models from this page of openrouter: https://openrouter.ai/models?variant=free
>
> i. apodex/apodex-1.1-mini:free
> ii.nvidia/nemotron-3-ultra-550b-a55b:free
> iii. google/gemma-4-31b-it:free
>
> Thoroughly reason and identify the best one for the usecase and also if there is any other model that we should use that would override the results of these 3 at 0 cost

## Inherited context and non-negotiable requirements

The full prior preparation handoff is in `2026-10-08-week1-token-preparation-context.md`; earlier reasoning is in `2026-10-08-step1-transcript-compaction-reasoning.md` and the other context files. The completed Week 1 payload is in `testing/.data/preparations/week1/fbdd50910e4c2d8192a80a8c17419a17ff4b0a74c8bd0bccfcdb02dfdff5c1f5/`.

- Nine Zoom exports, 3,238 cues. Preserve all dialogue and source speaker names on every turn. One physical whole-week extraction request; no summary, truncation or automatic per-meeting splitting.
- Zoom metadata has not been supplied. Missing dates/day/timezones/names remain null. Production will use Fathom transcripts/metadata, not summaries.
- Call 1 identifies source-grounded key moments and sufficient context; Call 2 generates distinct relevant angles. No third LLM judge. No arbitrary four-angle cap. Similarity/recency/selection are deterministic. One embedding per angle.
- Interim JSON authority and Markdown/context ledgers; local pgvector is a rebuildable projection. Preserve paid/free requests/responses and compatible reuse. Existing embedding choice remains paid text-embedding-3-small; free LLM tokens do not make the entire pipeline free.
- Approved previous model is GPT-OSS 120B Free; its route was absent from the public catalog. This new request asks for recommendations, not authorization to change `.env`, send transcripts or adopt another model.
- GPT-OSS local message-text count: 105,052; schema proxy 549; input proxy 105,601. These numbers cannot be copied to different model tokenizers. Coverage-only output uses 8,729 GPT-OSS tokens; output capacity matters independently of input size.
- Legacy live code still sends flat input, applies a 120,000-character preflight, requests strict `json_schema`, requires provider parameter support and disables fallback. The new compact path is a separate local preparation profile. Model selection alone does not wire it into the live runner.
- Editorial goal: useful decision-level mechanisms for capable wedding-business owners; exact evidence, qualifications and attribution; calm specific argument rather than hype or generic tips. No importing historical corpus results as current-week facts.

## Research procedure and authority

OpenAI Docs skill and its model-selection reference were read. Official token-count guidance was searched and fetched before substantive local inspection. The user's explicit third-party comparison was researched through OpenRouter and developer model cards, not by substituting an OpenAI model. No migration resolver/API key was needed or used. Read-only public GETs sent no key or transcript. Only local policy/configuration and saved aggregate counts were read; real `.env` was not read.

The rendered models filter page did not reliably preserve its filter in fetched content. A public `/api/v1/models` GET verified 467 total models and 16 zero-input/zero-output `:free` entries. Specific endpoint GETs confirmed advertised provider capabilities. Catalog listings do not establish authenticated quotas, privacy clearance, exact schema compatibility or completed inference.

## Verified shortlist at inspection

| Model ID | Provider | Context tokens | Advertised provider completion cap | JSON contract |
|---|---|---:|---:|---|
| `apodex/apodex-1.1-mini:free` | Novita | 262,144 | 235,929 | `response_format` and `structured_outputs` advertised |
| `nvidia/nemotron-3-ultra-550b-a55b:free` | Nvidia | 1,000,000 | 65,536 | Neither response-format nor schema enforcement advertised |
| `google/gemma-4-31b-it:free` | Google AI Studio | 262,144 | 32,768 | JSON response format; model FAQ explicitly says no schema enforcement |
| `dots-studio/dots-3-note-preview:free` | AtlasCloud | 512,000 | 460,800 | response format and structured outputs advertised |
| `thinkingmachines/inkling:free` | Thinking Machines | 1,048,576 | 262,144 | No response format; agentic-harness-only free terms |
| `nvidia/nemotron-3-super-120b-a12b:free` | Nvidia | 262,144 | 235,929 | response format and structured outputs advertised |

All six inspected endpoints advertised prompt/completion price zero. Caps are metadata, not guaranteed usable response lengths in addition to a full input. Actual input + reasoning + output + formatting must fit each model/route. Native support is not proof the exact nested Pydantic schema will work; backend validation remains necessary.

Other current free entries: Ling 3.0 Flash Sante, Liquid LFM2.5-2.6B, Nemotron 3.5 Lightning, Inkling Small, Laguna S/XS 2.1, Cohere North Mini Code, Nemotron 3.5 Content Safety, Nemotron Nano Omni, Gemma 4 26B A4B. Several are coding/health/guardrail/perception-specialized or lack the schema contract; none was established as a universally better editorial extraction model.

## Important constraints discovered

1. Apodex's own homepage advertises free access through October 15. As of October 8 it is a useful short-term test candidate, not a durable zero-cost foundation. Its model card describes agent-team/harness evaluations; those scores must not be treated as performance of our one plain extraction call.
2. Nemotron Ultra's free model page explicitly asks users not to upload confidential or personal data and describes logging/product-improvement use. Real source names and private client meetings are not an appropriate default upload. Removing names alone does not remove commercial confidentiality. Its lack of native response format also conflicts with the current adapter. Its million-token window is a real capacity advantage, not proof of better Whitney-style output. Endpoint health was volatile during inspection; no universal availability conclusion is made.
3. Gemma's card documents system-role support and a 256K model context. The free OpenRouter endpoint provides JSON mode without schema enforcement, so it is a reasonable challenger only after an explicit JSON-mode adapter decision, preserving backend validation. Google unpaid-service terms have sensitive/confidential/personal-data restrictions and improvement/human-review provisions; the exact OpenRouter provider billing/terms must be verified rather than assuming every zero-priced downstream route uses unpaid Google terms.
4. Dots3-Note is a particularly useful additional candidate because of 512K context and the current schema interface. Its free preview is marked going away December 31, 2026. Atlas policy distinguishes ordinary services (possible brief content retention) from enterprise ZDR; it does not justify automatically claiming this free endpoint has ZDR. Exact route privacy/retention must be checked.
5. Inkling's free endpoint is harness-only, prohibits confidential/personal uploads and lacks response format. Nemotron Super improves schema compatibility over Ultra but retains the NVIDIA free data restriction. These are not recommended shortcuts for raw weekly client transcripts.
6. OpenRouter's structured-output guidance confirms endpoint-specific support and provider-specific strictness. Privacy filters (`data_collection: deny`, and ZDR if required) can legitimately leave no eligible free route; do not relax them or silently choose paid service.
7. Free requests remain subject to account/provider quotas and availability. The fetched rate-limit page omitted numeric constants in its rendered table, so no unverified numeric quota is asserted. No authenticated key/quota inspection was performed.

## Recommendation and confidence

Among the user's three, Apodex is the strongest *practical first-test fit for the existing schema contract*, conditional on provider/privacy clearance and exact token/schema preflight. This is not an empirical claim of highest extraction quality. Use a common baseline for the two stages initially to avoid confusing prompt changes with model changes, then compare stages independently.

Dots3-Note is the strongest additional operational challenger identified: more whole-week/output headroom with advertised schema support. Prefer an Apodex-versus-Dots experiment over claiming either has already beaten the other. Apodex's imminent promotion expiry makes Dots worth prioritizing for a testing period extending beyond October 15, but Dots also is a time-limited preview.

Gemma is a useful Call 2 challenger for the smaller evidence packet after explicit JSON-mode/validator/route handling. Do not assume stylistic superiority from its brand or size. Nemotron Ultra is a capacity-oriented candidate for synthetic or genuinely non-confidential evaluation, not the recommendation for this unchanged real-data payload.

No free model has been verified to override all three in actual Content Atelier quality. Compare supported use, fidelity and editorial utility, not parameter count or unrelated coding/math scores. A rigorous zero-token-price workflow may still have no acceptable hosted free route if the data terms cannot be satisfied; local open-weight inference needs suitable hardware and is not automatically zero total cost.

## Safe evaluation and later implementation gates

- First use a synthetic/public non-confidential contract packet to verify the exact schema, finish reason, quote/reference checks and source-instruction resistance. This is proposed work, not a call already made.
- Once actual source processing is authorized and route terms permit it, each Call 1 trial must deliver the complete same week in one request. Compare against human-labelled substantive passages across all meetings, including late corrections and qualifications. ID acknowledgement alone is not recall proof.
- Hold a validated Call 1 evidence packet constant while comparing Call 2. Human-review grounded argument, audience fit, mechanism, distinctness, tone and commercial boundaries. Do not add a third LLM judge or weaken grounding to improve fluency.
- Count locally with each model's actual tokenizer/chat template; the existing preparation counter is GPT-OSS-specific. Propose a measured combined completion budget rather than automatically setting huge catalog maxima. Output coverage cost should be remeasured and any contract change separately approved.
- Review the current 180-second non-streaming timeout against large responses. Do not blindly apply vendor-reported aggregate throughput to this 100K-scale prompt.
- Preserve full prompts, input, actual model/provider/settings/schema, raw response including failures/usage, validated outputs and human labels in isolated trial artifacts. Compatible stage reuse can avoid redoing Call 1 while testing Call 2. Keep trial angle histories separate; do not automatically pay to embed every text-only comparison.
- Exact `:free` IDs; zero-price endpoints; no paid model fallback, external research plugins or unrelated model router. Paid embeddings remain separate.
- No configuration/model/prompt migration, source upload, new tokens, embeddings or additional implementation was authorized by this comparison request.

## Primary references

- Token accounting: https://developers.openai.com/api/docs/guides/token-counting
- OpenRouter free discovery: https://openrouter.ai/models?variant=free ; public catalog: https://openrouter.ai/api/v1/models
- Apodex free model and provider: https://openrouter.ai/apodex/apodex-1.1-mini:free ; https://openrouter.ai/api/v1/models/apodex/apodex-1.1-mini:free/endpoints
- Apodex promotion and model card: https://www.apodex.com/ ; https://huggingface.co/apodex/Apodex-1.1-mini-NVFP4
- Nemotron Ultra model, provider, card: https://openrouter.ai/nvidia/nemotron-3-ultra-550b-a55b:free ; https://openrouter.ai/api/v1/models/nvidia/nemotron-3-ultra-550b-a55b:free/endpoints ; https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Ultra-550B-A55B-BF16
- Gemma model, provider, card: https://openrouter.ai/google/gemma-4-31b-it:free ; https://openrouter.ai/api/v1/models/google/gemma-4-31b-it:free/endpoints ; https://huggingface.co/google/gemma-4-31B-it
- Dots model and provider: https://openrouter.ai/dots-studio/dots-3-note-preview:free ; https://openrouter.ai/api/v1/models/dots-studio/dots-3-note-preview:free/endpoints
- Inkling / Super: https://openrouter.ai/thinkingmachines/inkling:free ; https://openrouter.ai/nvidia/nemotron-3-super-120b-a12b:free
- Schema and free limits: https://openrouter.ai/docs/guides/features/structured-outputs ; https://openrouter.ai/docs/api_reference/limits
- Provider policies: https://novita.ai/legal/privacy-policy ; https://www.atlascloud.ai/data-retention ; https://ai.google.dev/gemini-api/terms

Final answer should lead with conditional Apodex first-test recommendation among the three and Dots as the additional challenger, clearly distinguish model capability from free endpoint compatibility/privacy, flag both free-access expiry dates, explain stage-specific tests and tokenizer/output-budget caveats, and state that no model was changed or response evaluated.
