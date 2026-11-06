# Content Atelier

The [WIA handbook understanding ledger](research/2026-10-13-wia-handbook-understanding-ledger.md) records the fresh editorial specification from the supplied 13 October 2026 handbook, with source-linked reasoning, claim boundaries, calibration cases, and a proposed rebuild contract. Its [structured counterpart](research/2026-10-13-wia-handbook-understanding-ledger.json) is a research reference; it has not been integrated into default production prompts or treated as publication approval.

The [Week 2 handbook prompt test](research/week2-handbook-luna-pro-test-review-2026-10-13.md) executed both reviewed prompts through an isolated versioned profile on `openai/gpt-6-luna-pro`. It is a partial diagnostic, with source-binding and editorial issues documented; production defaults were not migrated.

The [content-only handbook reference](backend/backend_pipeline/prompt_templates/handbook_v2/wia_content_system_handbook.md) and latest feedback are wired into a separate, prepared angle-only request, with the related market-research email supplied for overlap review. [Setup and rollback context](context/2026-10-13-full-handbook-angle-setup.md) records the local Git checkpoint and input limits. This request has not been dispatched.

The [weekly-angle PostgreSQL/pgvector implementation plan](implementation-plan-weekly-angles-postgres.md) is implemented through the SQL angle workflow and Gate 1. The [storage runbook and verification status](backend/STORAGE.md) explains setup, commands, recovery, matching and remaining execution gates. Real generation and encoding remain disabled.

The approved storage design is documented in the [complete 13-table DBML](content-atelier-compact.dbml), [column and approval contracts](database-schema-compact.md), [schema/pipeline map](data-storage-schema.md), and [standalone HTML execution flow](data-flow.html). The [storage and retrieval explanation](content_atelier_vectordb.md) covers the two pgvector columns, angle similarity/freshness, and the later brief-retrieval design. The baseline has been applied to an isolated local database. Brief generation, research retrieval, production and calendar integrations remain future stages.

The implementation is in [backend/](backend/). Run commands from that directory. SQL owns admitted content and processing state; exact provider artifacts/cache remain files. The separate calibration runner and its `testing/.data/` artifacts remain available without writing SQL business records.

The [prompt robustness review](research/transcript-angle-prompt-robustness-review.md) explains the corpus-derived editorial policy and remaining calibration/batching limits. This local testing slice is not a verified production deployment.

The Weekly Studio UI lives in [frontend/](frontend/). Railway deployment files,
production authentication and setup instructions are in [DEPLOYMENT.md](DEPLOYMENT.md). Those earlier deployment instructions have not been validated for the new backend package.
