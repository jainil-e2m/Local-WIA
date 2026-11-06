# Content Atelier

Content Atelier is Wedding Industry Ads' (WIA) content engine. It turns WIA's client, sales and team calls into a weekly set of content ideas (cards) that show what WIA knows, how it thinks and how it works. WIA chooses among them at Gate 1. Each chosen idea becomes a researched editorial brief in WIA's voice, which WIA approves at Gate 2. The approved scope ends at an approved brief; packs, scheduling and publishing are later stages behind flags.

## Start here

- **The plan of record:** [`backend/docs/Content-Atelier-Implementation-Plan-Brief-Generation.md`](backend/docs/Content-Atelier-Implementation-Plan-Brief-Generation.md). Revision 8 (22 October 2026) is the final audit after WIA's review of 20 October: "Read this first" gives the state and the milestones M0 to M6, "Where to resume" says what to do next on any machine, revision 8.1 (23 October) records the build of M1 and M2 in section 5.0a with the next step, and Appendix A says where every item ID went. Revision 7.3, with the item histories and logs before 22 October, is archived in [`backend/docs/archive/`](backend/docs/archive/).
- **Prompts for the next sessions:** [`backend/docs/Implementation-Prompts.md`](backend/docs/Implementation-Prompts.md): grounding (once per machine), implementation (per milestone or item), verification, and the filled prompt for the next step (plan section 5.0a).
- **Running and deploying it:** [`DEPLOYMENT.md`](DEPLOYMENT.md): the local stack, every variable and setting, the documents, moments and context commands, and the production services on Railway.
- **The data on the developer's machine:** [`backend/docs/Data-Handover-Runbook.md`](backend/docs/Data-Handover-Runbook.md) and [`backend/docs/Jainil-Handover-Prompt.md`](backend/docs/Jainil-Handover-Prompt.md).

## Layout

| Path | What it holds |
| --- | --- |
| `backend/backend_pipeline/` | The Python package (FastAPI, RQ on Redis, Postgres with pgvector): `llm/` (every model call, privacy routing, run plans, `llm_runs`), `jobs/` (executor and scheduler), `documents/` and `normalise/` (evidence intake), `moments/` and `search/` (the moments ledger and search), `cycle/` and `gates/` (verification, decisions, seeds), `briefs/` (research, brief v1 and v2, Gate 2), `knowledge/` (the context store, compiler, assembly service, learning loop), `prompt_templates/` (versioned prompts; never edit a released one) |
| `backend/migrations/` | Numbered SQL migrations applied by `python -m backend_pipeline.storage_cli migrate`, with one schema catalogue per version |
| `backend/knowledge_base/` | The committed, compiled knowledge base (WIA's brand kit), its manifest with pinned hashes, and archived versions |
| `backend/evaluation/` | The evaluation command (`python -m evaluation`), run only under a run plan |
| `backend/scripts/transfer/` | The data handover tools (inventory, pack and upload, fetch and verify) |
| `backend/deploy/production-settings.json` | The candidate editorial configuration for production, applied with `storage_cli settings apply` (plan E.X4, provisional) |
| `frontend/` | The Atelier app (React SPA) and its Node server (session check, allowlist, relay to the API) |
| `research/` | Evidence behind the plan: experiments, the one-time ChatGPT-export analysis and seed inputs, the live development week, the 19 October reconciliation. Client material is allowed only here and in `backend/knowledge_base/` (R48) |
| `client_documents/` | WIA's own guides and review document |

Everything else at the top level (the older plans, schemas and context snapshots) is historical and marked as such; the plan wins wherever they differ.

## Checks

CI (`.github/workflows/ci.yml`) runs, on every pull request and on `main`: backend lint (`ruff`) and offline tests; the OpenAPI drift check; both database suites against `pgvector/pgvector:0.8.2-pg17` after `storage_cli migrate`, with the schema-drift check; frontend type check, unit tests, server tests and production build, with the generated-types drift check; and both Docker images. The same commands run locally (`backend/docs/Phase-S-Stabilise-Handover.md` has the test-database container).

Never commit secrets, the raw ChatGPT export, or client material outside `research/` and `backend/knowledge_base/`. Paid model calls need an active run plan (`ATELIER_RUN_PLAN_ID` or `ATELIER_RUN_PLAN_FILE`) and are refused otherwise.
