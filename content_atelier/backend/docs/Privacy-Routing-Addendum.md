# Privacy routing addendum and client-material record (S.B1, S.B12)

**Date:** 18 October 2026 · **Plan items:** S.B1 (privacy record and enforcement), S.B12 (client-material conditions, R48), decisions C-05, C-06, D7, D10, D11 · **Routing policy in force:** `2026-10-18.deny-collection-zdr.v1` (`backend_pipeline/provider.py`)

This is the record the plan's S.B1 "done when" asks for. It covers:

- every model and embedding route that has received WIA call content or export text;
- the account settings that could be checked, and what could not;
- the routing now enforced in code;
- WIA's answers on processing and on the repository.

## 1. Routes that have received real content

| When | What was sent | Model | Route (OpenRouter provider) | Volume | Source of the record |
| --- | --- | --- | --- | --- | --- |
| 6 to 16 October (developer runs, Jainil's machine) | Week 1 to 4 call excerpts: extraction, angle generation, refinement, brief plan, write and review | `openai/gpt-6-luna`, `openai/gpt-6-luna-pro`, `openai/gpt-6.1-sol`, `anthropic/claude-sonnet-5.5` | Not recorded per call in this repository; the raw responses on the developer's machine name the provider | The developer's artifacts (`backend/.storage-artifacts/`, `service_calls/*/attempts/*/response.raw.json`); counted when S.B10 restores them | Research reviews in `research/` (`week1-*`, `week2-*`, `2026-10-16-*`) |
| 14 to 15 October (transcript backfill) | 170 transcripts as 2,657 chunks | `openai/text-embedding-3-small` | OpenRouter, provider not pinned | 2,657 chunks | `research/transcript-backfill-completed-2026-10-15.md` |
| 18 October (quality experiments) | Week 1 and 2 excerpts and the knowledge base | `openai/gpt-6.1-sol` | OpenAI | 23 calls, 265,663 prompt tokens, USD 1.372 | `research/quality-experiments-2026-10-18/ledger.jsonl` |
| 18 October (quality experiments) | As above | `anthropic/claude-sonnet-5.5` | Azure | 16 calls, 228,154 prompt tokens, USD 0.652 | Same ledger |
| 18 October (quality experiments) | As above | `anthropic/claude-sonnet-5` | Claude Platform on AWS | 2 calls, 55,088 prompt tokens, USD 0.356 | Same ledger |
| 18 October (quality experiments) | As above | `openai/gpt-6-luna` | OpenAI | 2 calls, 37,229 prompt tokens, USD 0.015 | Same ledger (6 further calls failed before any provider was chosen) |
| 18 October (ChatGPT export tests) | Whitney's marketing copy and export excerpts (no one-to-one client correspondence) | `anthropic/claude-sonnet-5.5` | Claude Platform on AWS | 212 calls, 2,869,556 prompt tokens, USD 2.041 | `research/chatgpt-export-2026-10-18/ledger.jsonl` (sent with `data_collection: "deny"`) |
| 18 October (ChatGPT export tests) | As above | `anthropic/claude-haiku-5.5` | Claude Platform on AWS | 230 calls, 2,800,772 prompt tokens, USD 0.128 | Same ledger |
| 18 October (ChatGPT export tests) | As above | `openai/gpt-6-luna` | OpenAI | 228 calls, 1,730,085 prompt tokens, USD 0.055 | Same ledger |
| 18 October (ChatGPT export tests) | As above | `openai/gpt-6.1-sol` | OpenAI | 20 calls, 234,638 prompt tokens, USD 0.234 | Same ledger |

Before this addendum, no request in the product carried a retention or data-collection preference. The export tests asked for `data_collection: "deny"` only. Requests went to whichever endpoint OpenRouter chose, including first-party OpenAI endpoints.

## 2. Account settings

- **The key** (presence checked, never printed) has a USD 5 weekly limit and is not a management key. `GET /api/v1/key` does not expose the account's privacy defaults ("Allow training", "Enable ZDR only"), so they could not be read with it.
- **Request-level enforcement makes the account default irrelevant for compliance.** Every request now names its own preferences, and OpenRouter applies the stricter of the account setting and the request.
- **Recommended, not required:** the account owner can also turn on "ZDR endpoints only" and turn off "allow providers that may train" in OpenRouter's privacy settings, as a second line of defence.
- **D10 (owner, 18 October):** the replaced key recorded in the experiment ledger is not deleted, and the current key stays in use. Its hash ID in the ledger is not a credential.

## 3. Routing enforced (`2026-10-18.deny-collection-zdr.v1`)

- **The position.** WIA's content goes only to endpoints that:
  - do not collect prompts for training (`data_collection: "deny"`); and
  - retain nothing (`zdr: true`).
- **Where it is enforced.** `llm.routing.send()` (the `llm` module; `provider.py` only re-exports it) is the only function that dispatches model or embedding requests. It adds these preferences to every request:
  - chat requests from every stage (`LiveProvider.json_call`): extraction, angles, refinement, brief and pack stages;
  - single and batch embeddings (`embed`, `embed_many`), which covers chunk encoding, angle signatures and the transcript backfill;
  - both research harness runners.

  A request that tries to set either preference the other way is refused before it leaves (`RoutingError`).
- **Fail closed.** When no endpoint qualifies, OpenRouter answers 404. `send()`'s callers save the response, then raise `RoutingError`. Nothing retries without the preferences.
- **Fingerprints.** The preferences are applied at dispatch, not when the request is built. Saved responses therefore still replay, and E.B12a's exact-fingerprint re-validation is unaffected. Each live response's metadata records `routing: {policy, preferences}`.
- **Every model in use has a compliant route.** OpenRouter's public ZDR endpoint list (`GET /api/v1/endpoints/zdr`, 18 October, 1,033 endpoints) includes:

  | Model | ZDR endpoints |
  | --- | --- |
  | `openai/gpt-6.1-sol` | Azure (global, us, eu) |
  | `openai/gpt-6-luna` | Azure (global, us, eu) |
  | `openai/gpt-6-luna-pro` | Azure (global, us, eu) |
  | `openai/text-embedding-3-small` | Azure |
  | `anthropic/claude-sonnet-5.5` | Google Vertex (global, us, europe), Amazon Bedrock |
  | `anthropic/claude-haiku-5.5` | Google Vertex (global, us, europe), Amazon Bedrock (us-east-1, eu-west-1) |

  Sol and Luna therefore move from OpenAI's own endpoints to Azure. The verifier and judge family (Anthropic) has compliant routes, as R44 requires.
- **Tests:** `backend_pipeline/tests/test_privacy_routing.py`. They check:
  - every chat stage and both embedding paths send the preferences;
  - a refusal raises without a second request;
  - both harnesses dispatch through `send()`;
  - a weakening override is refused;
  - no other module, script or harness posts to a model endpoint directly.

## 4. WIA's answers

| Question | Answer | Recorded |
| --- | --- | --- |
| C-05: may WIA's calls and documents be processed by AI models, and with what retention? | Yes. The owner relays that WIA's team has given full permission to do whatever is needed to make the system work for them. The enforced position (no collection, zero retention) is stricter than that permission requires. | Owner, 18 October 2026 |
| C-06: may WIA's documents and call excerpts be kept in the private repository and used in public content? | Yes, within the same permission. Public use stays subject to Gate 2 and to client consent per client (O3, the clearance step). | Owner, 18 October 2026 |
| D11: may Whitney's ChatGPT export be used? | Yes. Whitney gave full permission to use the export to set the system up. The analysis in `research/chatgpt-export-2026-10-18/` stays in git, so the work can continue on any machine. The raw export stays out of git (R52), and its retirement follows L.X2. | Owner, 18 October 2026 |
| D7: client material in git (R48) | Keep, under R48's conditions. With C-05 and C-06 answered, the conditions are met. | Owner, 18 October 2026 |

## 5. Repository access (S.B12)

`jainil-e2m/WIA-Content-Atelier` is private, owned by the user `jainil-e2m`. Collaborators on 18 October 2026, read with `gh api repos/jainil-e2m/WIA-Content-Atelier/collaborators`:

| Account | Role |
| --- | --- |
| `jainil-e2m` | admin (owner) |
| `kenil-e2m` | write |
| `AI-WIA` | write |

Pending invitations need admin rights to list, and were not checked.

**No further transcript text outside `research/` and `backend/knowledge_base/` (R48).** `backend_pipeline/tests/test_client_material_guard.py` fails CI if a tracked file outside those roots looks like transcript or client material: a caption file or caption-timed lines, timestamped speaker lines, JSON transcript turns, quoted passages with their time and speaker, or an office file or PDF (strengthened by the verification of 18 October; the test suite itself has no exemption). Material committed before 18 October is kept, by the owner's decision (D7, V11), and listed by name in the test: `research/root-cause-2026-10-16/`, the documents in `client_documents/` and `client_review/`, the PDFs in `testing/document_qa/`, and the frontend's old fixtures with call quotes (`frontend/src/data/fathomWeeklyAngles.ts`, `frontend/src/data/mockData.ts`, `frontend/src/components/MomentsLedgerView.tsx`, `mock-data/weekly-studio-2026-10-05.json`), which Phase 6 deletes with the mock state (6.F3).
