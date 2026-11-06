# Prompt robustness and corpus alignment — working checkpoint

## User request, verbatim

> i want you to revisit the prompts for each of the llm calls for robustness, and matching the requirement of the content atelier i.e. according to the identified samples, past data from the corpus and the analysis derived from that. I want thorough reasoning on this and ensure that the prompts are adept.

This file preserves the task context at a possible context boundary, under the user's earlier instruction to save context in this directory. It records concrete evidence, decisions and work state, not private reasoning.

## Scope and inherited decisions

Revise and test the two existing LLM responsibilities, moments/context and grounded content angles. Approved model stays `openai/gpt-oss-120b:free`; configurable credentials/models and no silent paid fallback remain. No live inference or private transcript upload is authorised/executed by this review. No new LLM judge, briefs, packs, CTAs, publishing, service installation or unrelated frontend changes. Show all qualifying distinct angles, no four-angle cap; keep one canonical vector per angle and compatible local artifact reuse. Preserve original generation lineage during replay. Preserve the user-owned deleted legacy backend and dirty frontend.

## Research performed

- Read the OpenAI Docs skill and its model-specific prompting route; fetched official prompt engineering, GPT-OSS Harmony and structured-output documentation. No migration or model replacement. Documentation informs instruction/data separation, schema/output contracts and evaluation discipline, not Whitney's taste. No API-key helper is available; tests remain offline.
- Revisited `research/whitney-taste-and-editorial-pipeline.md`, including source authority, four case readings, format distinctions, evidence-led extraction, angle boundaries, approval and evaluation sections. Its old four-angle target is superseded by later user decisions.
- Read the primary founder voice guide and Savannah strategy; checked the knowledge-base text's reel/caption material and its explicit non-verbatim-summary caveat.
- Read all user-message blocks in the assumptions/data, September caption, UVP email and workshop-reel conversations. Checked corrections/excerpts in the attribution/case study, autopilot, ten-week posting, July clips, September workshop and mindset conversations. Long supplied drafts and some combined outputs were excerpted, not claimed as newly exhaustively read.
- Read published July attribution, August ten-week pause and September UVP emails and the contemporary ten-week carousel's slide/caption transcription. Did not newly inspect original slide images or playable reel media; no inference of visual/audio taste beyond the existing analysis.

## Findings

Initial prompts were generic evidence-editor/strategist role instructions, with minimal nested JSON schema and unanchored 0–5 scores. Call 2 saw model summaries but not actual surrounding passages. Coverage IDs were not checked; context could cross source boundaries. Free-form model signatures could drift. Historical examples must not become current facts, rejected assistant drafts must not become policy, and scoped September caption restrictions must not become universal limits on short titles/older slides.

Whitney's stronger supported requirements: respect capable owners; preserve chronology, competence, cost basis and attributable versus total results; show why a consequential decision matters; connect clarity/relief to meaningful business opportunity without guarantees; do not misrepresent current offers or task ownership; avoid generic corrective contrasts, hype and repetitive hooks; preserve exact quotes even when their wording conflicts with paraphrase style rules.

## Changes applied at this checkpoint

1. Rewrote all four prompt templates; added a shared curated `editorial_policy.md` with explicit interpretation/authority limits and corpus-derived guardrails.
2. Released prompt profile v2. Rendering substitutes template placeholders in a single pass, so placeholder-like text inside untrusted input is preserved unchanged.
3. Added `contracts.py` with complete strict Pydantic nested response contracts, typed claim/status enums, nonblank fields, bounded finite scores and required nullable inference.
4. Pipeline sends full generated schemas, validates exact unique coverage acknowledgements, unique local IDs, literal quote/source references and contiguous chronological same-source context including anchors.
5. Call 2 packet now contains source_evidence (exact context turns), source revision hashes and explicitly unverified speaker labels.
6. Angle assertions must identify their supporting current moment; upstream qualifications and handling labels are retained deterministically. Backend derives a single canonical signature from audience, tension, argument, take, mechanism and reader decision; title/hook/channel/date/scores do not decorate it. Exact duplicate canonical arguments in one response fail validation.
7. LLM validation fingerprint version raised to 3, but embedding compatibility version remains 2 so unchanged exact vector requests can still be reused. Raw old attempts remain preserved; revised prompts/schemas legitimately invalidate matching LLM requests.
8. Fake provider acknowledges all spans rather than pretending empty coverage; counting-provider fixture updated to the new assertion/signature contract. Review calls coverage `acknowledged`, not proof of semantic understanding.

## Remaining work

- Finish offline regression tests for nested schemas, unsafe/partial outputs, source-boundary/context checks, actual source context propagation, canonical signatures, qualification/handling preservation, rendering isolation and cache behavior.
- Add a small synthetic corpus-derived evaluation set and documented human scoring procedure. Do not claim tests prove GPT-OSS's semantic response quality without real outputs and founder calibration.
- Save the thorough prompt audit, evidence-to-policy mapping, release/caching implications and actual remaining limitations in a research Markdown file; update README and next-call document ledger.
- Inspect first-week input size locally without provider calls; context/output size remains a real batching limitation, not solvable by longer instructions. Existing numerical near-duplicate selection/history calibration also remains outside this prompt review.
- Report exact verification results, distinguish contract readiness from empirically validated taste, and preserve this checkpoint's final outcome.
