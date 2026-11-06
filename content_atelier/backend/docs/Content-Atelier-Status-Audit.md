# Content Atelier: Project Status and Architecture Conformance Audit

<!-- governing-plan-note -->
> **Historical (marked 18 October 2026, plan item S.B9).** This document is kept for traceability. The one governing plan is [the implementation plan](Content-Atelier-Implementation-Plan-Brief-Generation.md) (revision 6.1 or later); where they differ, the plan wins. Do not plan from this document.

**Audit date:** 10 October 2026 · **Audited against:** `Content-Atelier-Solution-Architecture.md` (rev. 2, 4 October 2026) and `Content-Atelier-Feasibility-Study.md` (29 September 2026)

**Material reviewed:** `WIA-Content-Atelier-main/` (backend + Atelier frontend), `WIA-Command-Center-main/` (launcher, SSO, proxy, Ops Hub screen, corpus tooling), and the docs in this folder.

---

## 0. Verdict

**The project is not on track against the solution architecture, and it is deviating from it in several structural ways.** What has been built is a narrow, carefully engineered slice of the pipeline. Most of the v1 scope has not been started, and the slice that exists was built on a different data model and processing model from the one the architecture specifies.

The five things to know:

1. **Scope completed.** Of the 13 capabilities the architecture lists as essential for v1 (§13.1), **none is complete, 5 are partially built and 8 are not started.** In build-plan terms, the work sits partway through M2/M3 (extraction, angles, Gate 1), with M1 (connectors, normalisation, search) largely skipped and M4–M6 untouched.
2. **Nothing has run end to end on real data.** The only real model runs are on Week 1. The extraction failed validation (2 of 9 moments rejected), 7 moments were accepted as a "partial baseline", and 6 angle candidates were produced. No embeddings have ever been generated, so similarity matching, final selection and Gate 1 have only been exercised with synthetic data. Nobody at WIA has reviewed a real system-generated angle.
3. **The processing model differs from the architecture.** The architecture ingests continuously and extracts moments per document into a ledger. The build processes one whole week of transcripts in a single LLM request, with all-or-nothing validation and transcripts bound to a week. This is the most consequential deviation and is the direct cause of the failed real runs.
4. **Three specifications are in circulation and they contradict each other.** The solution architecture, `Content_Atelier.md` in the Command Center repo, and the implementation plan in the Atelier repo describe different workflows, gates, cadences and data models. The build follows the third, not the first.
5. **The two repos no longer fit together.** Command Center's Atelier proxy targets an API that has been deleted from the Atelier backend. The only working integration between the repos is the SSO launch link.

What is good: the built slice is high quality where it matters for trust. Evidence is traceable to exact source text, every model call is reproducible, approvals are bound to content hashes, and the core "not now" list (no vector DB, no workflow engine, no agents, no auto-publish) has been respected in the backend.

---

## 1. Audit scope, method and limits

**What I did**

- Read both architecture documents in full, plus the Atelier repo's handoff, implementation plan, READMEs and deployment guide, and the Command Center's `Content_Atelier.md` and `wia_resource_mapping.md`.
- Read the backend source (schema, repository, SQL worker, matching, Gate 1, API, providers, prompts, tests), the Atelier frontend entry points and server, and the Command Center's Atelier-related server and UI code.
- Ran the backend offline test suite.

**Verification performed**

| Check | Result |
|---|---|
| Backend offline tests (`pytest`, excluding the PostgreSQL suite) | **112 passed** |
| Backend PostgreSQL integration tests (`test_sql_storage.py`, 11 tests) | **Not run.** `pgvector` Python package is not installed on this machine and no test database is available. The handoff also makes no fresh pass claim for these. |
| Frontend tests, lint and build (31 test files) | Not run |
| Live deployments, Railway configuration, OpenRouter account settings | Not inspected (no access from this folder) |

**Limits you should weigh**

- These are downloaded snapshots with no git history, so I cannot see what changed when or what is on other branches.
- Private material is deliberately excluded from the repo and is not in this download: the transcripts (`backend/zoom_backfill_meetings/`), the JSON datastore (`testing/.data/`), the local database, and `corpus/` data. Statements about real-run results come from the repo's own documents, not from artifacts I inspected.
- Several documents the READMEs point to are missing from the download: `backend/STORAGE.md`, `content-atelier-compact.dbml`, `database-schema-compact.md`, `data-storage-schema.md`, and everything under `research/`. The "approved 13-table DBML" that the schema is generated from is therefore not available to audit.
- Completion judgements are mine, made from reading the code. I have used Done / Partial / Not started rather than percentages to avoid false precision.

---

## 2. What exists today

### 2.1 Content Atelier repo: backend (`WIA-Content-Atelier-main/backend/`)

A Python 3.12 package, `backend_pipeline`, containing two parallel runners:

| Part | What it does | State |
|---|---|---|
| **File-backed calibration runner** (`pipeline.py`, `store.py`, `calibration.py`, `prepare.py`, `token_budget.py`, `costs.py`) | Two LLM calls (moment extraction, angle generation) over a week of transcripts, with JSON artifacts, request fingerprinting, replay, cost ledger and token preflight | Working. Used for all real model tests so far. Labelled legacy in the docs but still load-bearing: the SQL worker calls its private methods. |
| **SQL workflow** (`repository.py`, `sql_pipeline.py`, `matching.py`, `gate_one.py`, `storage_api.py`, `storage_cli.py`, `database.py`) | Admits transcript files into Postgres, runs four job stages (extraction → angle generation → angle embedding → angle matching) through a lease-based job table, exposes review and Gate 1 endpoints | Implemented. Verified only with synthetic providers. |
| **Schema** (`migrations/001_approved_schema.sql`) | 13 tables: `weeks`, `pipeline_runs`, `transcripts`, `transcript_chunks`, `key_moments`, `content_angles`, `angle_moments`, `content_briefs`, `content_packs`, `content_assets`, `calendar_entries`, `pipeline_jobs`, `pipeline_events` | 9 populated by code. The 4 downstream tables are empty placeholders. |
| **Prompts** (`prompt_templates/`) | Versioned extraction and angle prompts plus a curated editorial policy | Solid, corpus-informed. Not founder-approved. |
| **Tests** | 12 test files | 112 offline tests pass. 11 database tests unverified here. |

Not present in the backend: connectors, scheduler, Slack app, classification, speaker roles, glossary, consent, topics, hybrid search, external research, briefs, packs, validators, critic, a Dockerfile, or any Railway configuration.

### 2.2 Content Atelier repo: frontend (`WIA-Content-Atelier-main/frontend/`)

A React 19 + Vite single-page app served by a small Express server.

| Part | State |
|---|---|
| **"Weekly Angle Review"** (`SQLWeeklyAngles.tsx`) | **The only screen backed by real data.** Lists weeks, job status and events, angles with evidence drill-down, similarity results, edit, re-score, approve with CTA, reject. It is the default view. |
| Home, Weekly Studio, Previous Concepts, Content Packs, Client Intelligence, Moments, Research, Inbox, Brand Kit, Flag Idea | **Mock.** Driven by hard-coded TypeScript data and browser `localStorage`. Includes four hand-prepared briefs and packs that were not produced by the pipeline. |
| Express server (`server/app.mjs`, `sso.mjs`) | Real. Session check against Command Center, PKCE sign-in handoff, CSRF checks, and a closed-allowlist proxy from `/api/atelier/*` to the backend's `/storage/*` with a server-held secret. Team role required for data routes. |

### 2.3 Command Center repo (`WIA-Command-Center-main/`)

You described this as where the frontend lives and where the Atelier is triggered from. The code shows something narrower:

| Part | State |
|---|---|
| **Launcher + SSO** (`server/atelier-sso.mjs`, the "View Here" link in `ExploreSection.tsx`) | Real and working by design. This is the actual trigger: it signs the user into the separately deployed Atelier app. |
| **Atelier API proxy** (`server/content-atelier-proxy.mjs`) | **Stale.** Allows `/calls`, `/verdicts/*`, `/moments/*/labels`, `/ideas/*/gate-1`, `/source-health`. None of these routes exist in the current backend. No frontend code in Command Center calls this proxy. |
| **Ops Hub "Content Atelier" screen** (`ContentAtelierScreen.tsx`, `src/data/contentAtelier.ts`) | Fixture-only demo of a different workflow (candidates → steer → CTA → lead asset → pack). No model or API call anywhere. Its own data file is flagged as out of date in `wia_resource_mapping.md`. |
| **Corpus tooling** (`corpus/*.mjs`) | One-off Node scripts that proved access and pulled the corpus: Slack fetcher, Zoom VTT indexer, GHL email fetcher, Fathom probe, a webhook receiver. Useful prototypes. Not part of the pipeline. |
| **`Content_Atelier.md`** | A detailed product spec (16–28 September) that predates the solution architecture and conflicts with it. See D10. |

So the Atelier's real UI lives in the Atelier repo. Command Center currently contributes sign-in, a launch link, an obsolete proxy and a second, fixture-only UI for the same product.

### 2.4 Data collected so far (per Command Center docs, not verified by me)

150 Zoom transcripts pulled by hand from the Zoom UI (78 client calls, 61 internal), 6 Slack channels (1,070 messages, 209 files), 126 GHL marketing emails, 18 Instagram carousels, 3 voice and strategy documents, 12 ChatGPT working chats. Fathom is proven on a test account only. The Zoom Server-to-Server app is blocked on WIA permissions and Fathom team keys are in progress.

This is real progress on M0 and it is not reflected in the pipeline: the backend has only been fed two hand-assembled weeks of VTT files (9 and 11 files).

---

## 3. Status against the build plan (architecture §14)

| Milestone | "Done when" | Status | Evidence |
|---|---|---|---|
| **M0. Access and data audit** | 5 sample calls and a month of Slack in a scratch database; coverage report | **Partial** | Corpus collected to disk by Command Center scripts. Not in a database. Zoom API app blocked; Fathom keys pending; consent rule, approvers and WIA timezone not recorded anywhere. |
| **M1. Foundations** | Full backfill ingested and de-duplicated; search finds the "10 weeks" moment by keyword and paraphrase | **Mostly not started** | Schema and local Postgres exist. No connectors, no normalisation, no chunk embeddings, no full-text index, no search, no Sources page, no Railway environment for the backend. Only 20 of 150 transcripts admitted. |
| **M2. Moments and topics** | Almost all quotes verify; role errors reviewed; Whitney's calibration labels done | **Partial** | Extraction with exact-quote verification exists. No topics, no roles, no consent, no calibration labels. The one real extraction failed validation. |
| **M3. Weekly cycle and Gate 1** | Two dry-run cycles on backfilled weeks; golden moment in top 3; ranking agrees with Whitney | **Partial** | Angle generation, similarity scoring and a Gate 1 screen exist. No candidate themes, no external research, no selection, no Slack digest, no scheduler. Zero complete dry runs on real data. |
| **M4. Research, briefs, Gate 2** | Briefs cite several sources; retrieval recall target met | **Not started** | `content_briefs` table is empty. Gate 1 approval explicitly starts nothing. |
| **M5. Packs and final review** | Whitney rates the golden pack close to what shipped | **Not started** | Mock UI only. |
| **M6. Hardening and launch** | First live cycle runs unattended and lands in Slack | **Not started** | |

The team took a vertical-slice route (extraction → angles → Gate 1 on hand-fed files) instead of the plan's order (foundations first). That is a legitimate way to de-risk the hardest judgement step early. The cost is that the slice sits on a schema and a processing model that omit the foundations M1 and M2 were supposed to provide, so some of it will need rework rather than extension.

---

## 4. Status against the 13 v1 essentials (architecture §13.1)

| # | Capability | Status | What exists | What is missing |
|---|---|---|---|---|
| 1 | Railway setup (web, worker, scheduler, Redis, Postgres, bucket; staging + production) | **Not started** (backend) | Frontend Dockerfile and deploy guide; local Docker Compose for Postgres | Backend Dockerfile, worker and scheduler services, Redis, bucket, environments |
| 2 | Connectors: Zoom, Fathom, Slack with screenshots | **Not started** | One-off Node scripts in Command Center | Any connector in the pipeline; cursors; polling; `connections` table |
| 3 | Normalisation: classification, de-dup, roles, glossary, segmentation, embeddings, full-text | **Partial (small)** | Turn-aware chunking with exact source offsets | Everything else. Chunks are never embedded and have no text index. |
| 4 | Moment extraction with quote verification, role checks, consent | **Partial** | Extraction, exact-quote check, claim status, sensitivity label | Per-document extraction, role checks, number checks, consent status, per-moment failure handling |
| 5 | Topic registry | **Not started** | | Everything |
| 6 | Weekly cycle with web research and DataForSEO flag | **Partial (small)** | Angle generation from moments | Candidate themes, pre-score, external enrichment, rubric scoring, selection, scheduling |
| 7 | Gate 1 in dashboard and Slack, plus manual ideas | **Partial** | Dashboard approve-with-CTA, reject, edit, re-score | Slack, pass reasons, snooze, steer, expiry, manual ideas |
| 8 | Research dossier, brief, Gate 2 | **Not started** | Empty table | Everything |
| 9 | Format specs, pack generation, validators, critic, final review | **Not started** | Empty tables | Everything |
| 10 | Content memory: similarity, freshness policy, past-content import | **Partial** | Angle-to-angle cosine similarity with recency decay | Topic level, published-content level, status-based cooldowns, new-evidence rule, import |
| 11 | Dashboard screens marked v1 (7 screens) | **Partial (small)** | 1 real screen (This Week, partial) | Briefs, Packs, Moments/archive, Topics/memory, Sources, Settings |
| 12 | `llm_runs`, `job_runs`, sweep, cost caps, alerts, coverage report, backups | **Partial (small)** | Job and event tables; per-call cost files | Sweep, caps, alerts, coverage report, backups, restore drill |
| 13 | Evaluation: golden call, calibration labels, retrieval set | **Not started** | 14 synthetic diagnostic cases | All three |

---

## 5. Conformance with the 14 key decisions (architecture §0)

| # | Decision | Verdict | Note |
|---|---|---|---|
| 1 | One Postgres with pgvector; Redis for queue only; bucket for raw files | **Partly conforms** | Postgres + pgvector, yes. No Redis in use. Raw files on local disk, no bucket. |
| 2 | Three knowledge tiers (brand kit, evidence store, content memory) | **Deviates** | No brand-kit tier (a prompt file stands in). Evidence store is week-scoped. Content memory is angle vectors only. |
| 3 | Verified moments linked to a topic registry | **Partly conforms** | Moments yes. No topics. |
| 4 | Bounded research loop producing a cited dossier | **Not built** | |
| 5 | Gates as DB states; RQ on Redis; RQ cron; reconciliation sweep | **Deviates** | Gates as DB states, yes. Queue is a Postgres lease table with a polling worker. No scheduler. No sweep. See D1. |
| 6 | Idempotent scheduled polling of Zoom, Fathom, Slack | **Not built** | Manual file admission only. |
| 7 | Angle funnel: evidence → shortlist → enrichment → angles → memory filter → arithmetic ranking → pick 3–5 | **Deviates** | One prompt generates all angles with no cap. Arithmetic scoring exists but on different criteria. No shortlist, enrichment or selection. See D5. |
| 8 | Two pluggable external providers, cached, budgeted, non-blocking | **Not built** | |
| 9 | MCP not on the critical path | **Conforms** | |
| 10 | Dashboard is the system of record; Slack carries digests and one-tap actions | **Partly conforms** | Dashboard yes. No Slack. |
| 11 | Format specs and pack templates are data | **Not built** | Schema comment hard-codes "email, carousel or reel". |
| 12 | Freshness at topic, angle and asset level with status-based cooldowns | **Deviates** | Angle level only, time-decay only. See D4. |
| 13 | OpenRouter only, model per stage, structured outputs, ZDR, prompt caching, evaluation before any switch | **Deviates** | Details in D7. |
| 14 | Python monorepo: FastAPI web app and RQ workers sharing Pydantic models | **Partly conforms** | Python, FastAPI, Pydantic yes. UI is a separate React + Node service. No SQLAlchemy/Alembic. |

**Tally:** 1 conforms, 4 partly conform, 5 deviate, 4 not built.

---

## 6. Deviation register

"Deviation" means built differently from the architecture. Gaps that are simply not built yet are in §4 and §9.

### High severity

**D1. Whole-week batch extraction instead of per-document extraction**
- *Architecture:* each call is read once, on its own, as it arrives (§4.3: "Each call fits in one prompt"). Moments accumulate in a ledger. The weekly cycle only reads the ledger.
- *Built:* all transcripts for a week go into one LLM request (Week 1 was 116,370 input tokens for 9 calls). The backend README records an explicit rule that batching and per-meeting calls are not permitted. Validation is all-or-nothing: one bad quote fails the whole week.
- *Consequence:* this caused both failed paid extractions (one bad enum; two quote mismatches out of nine). Week 2's packet is 44% larger and may not fit the model at all. It cannot scale to 5–20 calls a week, cannot ingest incrementally, cannot re-process one document, and makes a quiet week and a busy week behave differently.
- *Status:* a deliberate decision recorded in the repo, never reconciled with the architecture.

**D2. Week-centric data model**
- *Architecture:* a `source_documents` table independent of any cycle, with `cycles` referencing moments by date window.
- *Built:* every transcript belongs to a `week_id`, and moments and angles hang off weeks and runs. The schema checker refuses any database that differs from the baseline, and there is no migration tool (the earlier Alembic setup was deleted).
- *Consequence:* the "whole archive" retrieval the architecture depends on (R5, Decision 3) has no natural home. Slack has no place at all: `source_type` allows only `fathom`, `zoom` or `manual`. Changing this later means a schema rewrite with no migration path.

**D3. Schema covers roughly half the architecture's data model, and was "approved" without the missing half**
- Missing tables: `clients`, `people`, `slack_channels`, `connections`, `attachments`, `topics`, `moment_topics`, `candidates`, `research_dossiers`, `brief_versions`, `asset_versions`, `published_content`, `decisions`, `brand_kit_docs`, `glossary_terms`, `format_specs`, `pack_templates`, `settings`, `llm_runs`, `external_calls`, `users`, `audit_log`.
- Moments are stored as a JSON blob with no embedding, no text index, no client, no speaker, no consent status. They cannot be searched or filtered as the architecture requires.
- A `use_restrictions` column exists on transcripts but no code reads or writes it.
- `calendar_entries` (with `external_schedule_id`) is present although the architecture puts the calendar in "later" and publishing out of scope.

**D4. Consent, speaker roles and call classification are absent, and internal calls are deliberately included**
- *Architecture:* consent is "a gate, not a note" (§12); internal and vendor calls are excluded before extraction (§4.2); testimonials must come from a client (§4.3).
- *Built:* no clients table, no roles, no classification. The extraction prompt instructs the model: "do not exclude all team meetings by category". Speaker labels are passed through as "unverified".
- *Consequence:* the feasibility study's named risks ("internal calls mined for content", "wrong speaker on a quote") are currently unmitigated. 61 of the 150 collected transcripts are internal.

**D5. Angle scoring and selection do not follow the specified funnel**
- *Architecture:* rubric of proof, audience pain, timeliness, offer fit, recurrence, differentiation, search demand, with two hard gates, weights in settings, a quality floor, then a diverse pick of 3–5 with at most two per pillar.
- *Built:* the generating model scores its own angles on grounding, source relevance, audience fit, specificity and editorial usefulness. Weights are hard-coded in `models.py`. Every angle scoring above 70 is shown. The prompt says "There is no target or cap". There is no pillar, no hooks, no "why now", no differentiation, no suggested CTA and no "what is new" in the angle record.
- *Consequence:* no guard against approval fatigue (the architecture caps at 5), no calibration path to Whitney's judgement, and the score is a model grading its own work.

**D6. Three conflicting specifications (governance)**

| Topic | Solution architecture (4 Oct) | Command Center `Content_Atelier.md` (16–28 Sep) | Atelier repo plan and frontend docs |
|---|---|---|---|
| Cadence | Continuous ingest, weekly cycle | Nightly batch | Weekly, whole-week batch |
| Idea detection | Moments ledger ranked across the week | Per-call "worth it / not worth it" verdict, then a gist | Whole-week moments, then angles |
| Gates | 2 gates + light final review | Gist approval, then pack acceptance | Gate 1 only (backend); 3 gates (mock UI) |
| Pack writing | Anchor piece first, others follow | Every piece written independently from the gist | Not built |
| New-call detection | Polling only | Webhook first, poll second | Manual files |
| Learning loop | Capture now, build later | "There is no learning loop after launch" | Not addressed |
| External research | OpenRouter web search + DataForSEO | Not covered | SerpAPI (mock UI) |
| Timeline | Milestones M0–M6, no dates | MC-01 to MC-04, Phase 2, January–April 2027 | None |

The per-call verdict in the Command Center spec is the exact pattern the feasibility study recommended against (change #1). The architecture's §1.4 reconciles itself with the feasibility study but never mentions the Command Center spec, so those conflicts were not resolved, they were missed. The team is building from the third column.

### Medium severity

**D7. LLM usage departs from the model strategy (§8)**
- **Single model for everything.** `openai/gpt-6-luna` at low reasoning effort for both stages. No tiers, no fallback list (`allow_fallbacks: false`).
- **No schema-enforced output.** Configured as `json_object` with the schema pasted into the system prompt, not `json_schema`.
- **No repair attempt.** The architecture allows one repair attempt then a visible failure. The build's rule is "never auto-repaired". Combined with D1 this turns one small defect into a failed week.
- **Models switched without an evaluation run.** GPT-OSS, then Apodex, then Luna, within days. The architecture requires an evaluation before any switch; no evaluation set exists.
- **Embeddings default to OpenAI directly** (`https://api.openai.com/v1` in `config.py`), not OpenRouter. The `.env.example` overrides this to OpenRouter, so behaviour depends on which file is used.
- **Local input and output limits are disabled** and there are no cost caps or budgets.
- **Privacy needs confirming.** The backend README records that a complete week of real client transcripts (9 calls, 3,238 turns) was sent to `apodex/apodex-1.1-mini:free` via a third-party host, and later to Luna. Nothing in either repo shows zero-data-retention routing was enabled. Free routes commonly retain or train on prompts. I could not check the account setting, so treat this as an open question, not a confirmed breach.

**D8. Job orchestration: Postgres lease queue instead of RQ on Redis**
- *Built:* jobs live in `pipeline_jobs` and are claimed with row locks and leases by a polling worker. There is no scheduler and no reconciliation sweep. An expired lease is marked failed and waits for a human retry (a deliberate choice to avoid repeating a paid call).
- *Assessment:* technically sound, and the architecture itself calls a Postgres-backed queue "technically tidier" (§9.1). It was rejected there because the team runs RQ. This is a reasonable deviation, made deliberately in the implementation plan, that needs formal sign-off and the missing pieces (scheduler, automatic recovery). `rq`, `redis`, `sqlalchemy` and `openai` are still in `requirements.txt` but nothing imports them, and the pinned `rq==1.16.2` predates the cron scheduler the architecture relies on.

**D9. Freshness is recency-decayed similarity only**
- *Built:* `risk = overlap × 2^(−age/28 days)`, maximum 50% score penalty, compared against every previously generated angle regardless of whether it was approved, rejected or published. The 0.78 and 0.90 thresholds match the architecture.
- *Missing:* topic-level and published-content-level checks, the LLM judge for the ambiguous band, status-based cooldowns, the new-evidence rule and pillar balance.
- *Design flaw to fix:* age is measured from when the model generated the angle, not from when the content was sourced or published. In a backfill, weeks that are months apart are generated days apart, so similar angles are penalised at near-maximum. The implementation plan acknowledges this.

**D10. Cross-repo integration drift**
- Command Center's proxy allowlist targets a deleted API (§2.3).
- The Atelier `DEPLOYMENT.md` section "Optional: deploy the live Python backend" describes a backend Dockerfile, `ATELIER_API_TOKEN`, `ATELIER_WHITNEY_EMAIL`, Fathom webhook secrets and an in-process Slack scheduler. None of these exist in the current backend, which uses `ATELIER_API_SECRET` and has no Dockerfile.
- Two UIs exist for one product (Ops Hub screen and the standalone app), each with a different workflow.

**D11. The mock UI shows a product the architecture does not describe**
- Simulated scheduling and a "live publishing tracker" (publishing and scheduling are out of scope; the calendar is "later").
- A SerpAPI research screen (the architecture replaced SerpAPI with DataForSEO).
- Three gates, a hard cap of four concepts per week, a four-factor score with different weights, and LeadLock as a CTA track.
- Editorial weeks computed in `Asia/Calcutta` (the architecture requires WIA's timezone).
- Hand-prepared briefs and packs presented in the same app as real pipeline output.
- *Risk:* if this has been demonstrated to WIA, it has set expectations the backend plan does not meet.

### Low severity

**D12. UI stack and auth.** React SPA with a Node server, signed in through Command Center, instead of FastAPI + HTMX with Slack/Google sign-in. The architecture permits React in front of the API, so the stack is acceptable. What is missing is the role model: any `team` user can approve; there are no admin / approver / editor / viewer roles. Separately, the static file server admits `client`-role users to an app whose bundle contains meeting-derived material.

**D13. Moment taxonomy differs.** Built: result, objection, decision, tension, mechanism, observation, story. Specified: result, testimonial, story, question, objection, teaching, opinion, data point, trend signal, soundbite. The types that matter most to WIA's stated signals (testimonial, soundbite, question) are absent.

**D14. Segmentation differs.** Chunks are capped at 2,400 characters with a 90-second gap rule, no overlap, and a header of only `Source: <filename>`. The architecture specifies 200–400 token windows, one-turn overlap, and a header carrying date, call type, client and speakers with roles.

**D15. Maintainability.** The SQL-path modules are written in a very compressed style: 61 lines exceed the project's own 130-character lint limit (up to 250 characters, multiple statements per line). The SQL worker reaches into private methods of the legacy `Pipeline` class. `provider.py` special-cases one model ID by string. This cuts against requirement N3.

**D16. Portability and housekeeping.** `.env.example` and `export-schema.cjs` contain another developer's absolute paths. READMEs link to files that are not in the repo. `@google/genai` is an unused frontend dependency and the package is still named `react-example`.

---

## 7. Requirements coverage (architecture §1.1)

| # | Requirement | Status |
|---|---|---|
| R1 | Ingest 3 months of Zoom, ongoing Fathom, Slack with screenshots | **Not met.** Data collected to disk by scripts; 20 files admitted by hand; no Fathom or Slack in the pipeline. |
| R2 | Identify content-worthy moments, not summaries | **Partly met.** Prompts and validators do this well in design. Unproven: the one real run failed validation. |
| R3 | 3–5 angles per week grounded in internal evidence and external research, DataForSEO switchable | **Partly met.** Internal grounding only. No external research. No 3–5 selection. |
| R4 | Angles in dashboard, posted to Slack, awaiting a choice | **Partly met.** Dashboard only. |
| R5 | Researched brief drawing on the whole history | **Not met.** |
| R6 | Brief can be approved, edited, given context, rejected | **Not met.** |
| R7 | Generate assets without locking in today's formats | **Not met.** |
| R8 | Remember what was proposed and used; avoid repeats; allow returns | **Partly met.** Similarity to past angles only. |
| N1 | Run on Railway | **Not met** for the backend. |
| N2 | OpenRouter for model access | **Mostly met.** Embedding default points at OpenAI. |
| N3 | Understandable and maintainable | **At risk.** See D15 and the two parallel runners. |
| N4 | Consistent, high-quality output | **Unproven.** No evaluation set, no calibration. |
| N5 | Human approval stays | **Met** in what exists. |
| N6 | External enrichment never a fragile dependency | **Not applicable yet.** |

---

## 8. What is being done properly

These are worth protecting through any rework.

- **Evidence integrity.** Every moment resolves to exact character offsets in an immutable copy of the source, and a quote must be a literal substring of its anchor passage. This is stricter than the architecture's fuzzy match.
- **Reproducibility.** Every model call stores the full request, raw response, prompt version, model and a request fingerprint. Identical work is reused, never re-billed. Replay mode guarantees no provider call. This meets and exceeds §8.4.
- **Approval integrity.** Approvals are bound to a content hash by a database constraint, edits create a superseding version instead of overwriting, and stale edits are rejected. This is the architecture's "human edits are never silently overwritten" principle, implemented well.
- **Gates as database states.** Nothing waits in memory, as specified.
- **Deterministic scoring maths.** Similarity, recency and the adjusted score are plain arithmetic in code, with an exact vector scan over the full history.
- **Honest failure handling.** Missing vectors block matching instead of reading as "no duplication risk". Failed and partial runs stay labelled as such.
- **Security of the UI boundary.** Server-held backend secret, closed route allowlist, CSRF checks, identity headers stripped, PKCE sign-in handoff.
- **Prompt quality.** The prompts treat transcript text as untrusted data, preserve claim status and qualifications, and encode real findings from WIA's ChatGPT history (for example the "not X, it's Y" construction Whitney rejects).
- **Restraint.** No vector database, graph, workflow engine, agent framework, fine-tuning or publishing path in the backend.
- **M0 groundwork in Command Center.** The corpus pull was thorough and caught real traps (Slack retention cliff, Fathom test-event flag, transcript survival in Zoom).

One caution on balance: a large share of the engineering effort has gone into provenance, replay, cost and token-budget machinery and into model comparisons. The architecture asked for complexity to be spent on grounding, judgement, retrieval depth and memory, and for everything else to stay plain. Grounding has been served. Judgement, retrieval and memory have not.

---

## 9. What is still pending

Ordered by dependency, not by effort.

**A. Decisions and reconciliation (no code)**
1. Choose the governing specification and reconcile the three documents (D6).
2. Formally accept or reverse the deliberate deviations: whole-week extraction (D1), week-centric schema (D2), Postgres queue (D8), React + Command Center sign-in (D12).
3. Inputs still owed by WIA: Zoom Server-to-Server app, Fathom keys per host, consent rule, approvers and delegates, timezone and digest time, published-content export, DataForSEO decision.

**B. Close out the current slice on real data**
4. Generate embeddings for the six Week 1 angles and run matching once for real.
5. Resolve Week 2 (cannot proceed under D1 if the request does not fit).
6. Put real angles in front of Whitney or Giselle. Collect the 30–50 calibration labels.
7. Run the 11 PostgreSQL integration tests and record the result.

**C. Foundations (M1)**
8. Backend Dockerfile; Railway `web`, `worker`, `scheduler`, Postgres, bucket; staging and production.
9. Python connectors for Zoom, Fathom and Slack with cursors and polling, porting what the Command Center scripts learned.
10. Normalisation: call classification, cross-source de-duplication, speaker roles, glossary.
11. Reference data: clients, people, consent levels, Slack channel registry.
12. Segment embeddings, full-text index, and the single hybrid search function.
13. Sources page and coverage report.

**D. Moments and topics (M2)**
14. Per-document extraction with per-moment verification and one repair attempt.
15. Role plausibility, number-in-source and consent checks.
16. Topic registry with assignment and basic admin.
17. Moments and archive screen.

**E. Weekly cycle and Gate 1 (M3)**
18. Candidate themes, pre-scoring, shortlist.
19. Web research provider; DataForSEO adapter behind a flag; cache, budgets, sanitiser.
20. Rubric scoring per the architecture, quality floor, diverse 3–5 selection.
21. Full freshness policy and past-content import.
22. Gate 1 actions: pass with reason, snooze, steer, expiry, manual ideas, decisions log.
23. Slack app: digest, one-tap actions, notifications.
24. Scheduler and automatic recovery of lost or stalled jobs.

**F. Briefs, packs, launch (M4–M6)**
25. Research loop and dossier; structured brief; Gate 2 with versions and locked fields.
26. Brand kit tier (versioned, approved documents loaded whole).
27. Format specs and pack templates as data; anchor-first generation; validators; cross-family critic; final review; mark published.
28. Briefs, Packs, Topics/memory and Settings screens; roles.
29. `llm_runs` and `external_calls` logging, cost caps, alerts, backups, restore drill, runbook.
30. Evaluation: golden acceptance test, calibration regression set, retrieval set.

---

## 10. Recommendations

**1. Stop and reconcile before building further (this week).**
Hold a short decision session and issue rev. 3 of the architecture (or a deviations addendum) that settles the table in D6 and the four deliberate deviations. Every further week of building on the current schema raises the cost of changing it.

**2. Reverse D1: move to per-document extraction with per-moment validation.**
This is the single change that most improves the project's position. It removes the context-size ceiling, makes one bad quote cost one moment instead of one week, makes extraction incremental, and restores the moments ledger the rest of the architecture stands on. The existing validators and prompts can be reused almost as they are.

**3. Extend the data model now, with a migration tool.**
Decouple transcripts from weeks, generalise to source documents (so Slack fits), promote moments to searchable rows, and add clients, people, consent, topics, decisions and published content. Adopt Alembic or an equivalent so the schema can evolve; the current "refuse anything different" guard is right for safety but leaves no way forward.

**4. Get one real cycle in front of the client.**
Embeddings for six angles cost a fraction of a cent. Until a real angle has been matched, selected and judged by Whitney or Giselle, the project has no evidence about the thing the architecture says decides its success: judgement.

**5. Confirm the privacy position.**
Check whether zero data retention is enabled on the OpenRouter account, establish what the free route's data policy was for the Week 1 test, and pin a ZDR-compatible model before any further real transcripts are sent.

**6. Fix the repo boundary.**
Decide which UI is the product. Then either update or delete Command Center's Atelier proxy, retire the fixture screen or point it at the real app, and rewrite the backend section of `DEPLOYMENT.md`. Make the mock screens visibly demo, or hide them, until their backends exist.

**7. Then resume the build plan in order.**
M1 foundations (connectors, normalisation, search), topics, the proper weekly cycle with the 3–5 cap, Slack, and only then briefs and packs.

**8. Put dates on it.**
No dated plan exists in either repo. The only timeline reference is Command Center's "Phase 2, January–April 2027". Agree milestone dates so "on track" can be measured.

---

## 11. Decisions needed from you

| # | Decision | Why it blocks |
|---|---|---|
| 1 | Is the solution architecture the governing spec, or do the 23 September decisions in `Content_Atelier.md` (nightly, per-call gist, independent pieces, no learning loop) still stand? | Determines the processing model and the gates |
| 2 | Per-document extraction (architecture) or whole-week single request (current)? | Blocks Week 2 and all scaling |
| 3 | Keep the Postgres job queue, or move to RQ on Redis as specified? | Scheduler and recovery design |
| 4 | Which UI is the product: the standalone Atelier app, or the Command Center Ops Hub screen? | Removes duplicate work and the stale proxy |
| 5 | Is scheduling/calendar in v1 scope? The mock shows it; the architecture says later | Client expectation and schema |
| 6 | Golden acceptance test: the "10 weeks" call (architecture) or the Funktastic chain (Command Center says it is the only one with both transcript and published output)? | Evaluation design |
| 7 | Who approves at each gate, and what is the client-consent rule? | Roles and the consent gate |
| 8 | Was the mock UI shown to WIA, and what was promised from it? | Scope management |

---

## Appendix A. Evidence pointers

| Finding | Where to look |
|---|---|
| 13-table schema, week binding, source types | `WIA-Content-Atelier-main/backend/migrations/001_approved_schema.sql` |
| Job stages, lease queue, manual retry on expiry | `WIA-Content-Atelier-main/backend/backend_pipeline/repository.py` (`submit`, `claim`, `retry`) |
| Whole-week extraction and reuse of legacy runner internals | `WIA-Content-Atelier-main/backend/backend_pipeline/sql_pipeline.py` (`execute`, `adapter`) |
| "No batching" rule, removed size limits, real-run history, free-route test | `WIA-Content-Atelier-main/backend/README.md` |
| Similarity and recency formula | `WIA-Content-Atelier-main/backend/backend_pipeline/matching.py` (`risk`, `match`) |
| Self-score criteria and hard-coded weights | `WIA-Content-Atelier-main/backend/backend_pipeline/models.py` (`Quality.score`) |
| Gate 1 behaviour; "No brief job is created by this release" | `WIA-Content-Atelier-main/backend/backend_pipeline/gate_one.py` |
| Model request settings, `json_object`, no fallbacks | `WIA-Content-Atelier-main/backend/backend_pipeline/provider.py`, `backend/.env.example` |
| Embedding endpoint default | `WIA-Content-Atelier-main/backend/backend_pipeline/config.py` |
| "Do not exclude all team meetings by category"; no cap on angles | `WIA-Content-Atelier-main/backend/backend_pipeline/prompt_templates/` |
| Deliberate choice of Postgres queue; nine populated tables | `WIA-Content-Atelier-main/implementation-plan-weekly-angles-postgres.md` §3 |
| Current state and disabled paid execution | `WIA-Content-Atelier-main/BUILD_HANDOFF.md` |
| Only one real view; mock data and localStorage elsewhere | `WIA-Content-Atelier-main/frontend/src/App.tsx`, `frontend/src/components/SQLWeeklyAngles.tsx` |
| BFF allowlist, team-role check, client-role static access | `WIA-Content-Atelier-main/frontend/server/app.mjs` |
| Mock workflow: 3 gates, SerpAPI, 4-concept cap, IST weeks | `WIA-Content-Atelier-main/frontend/AGENDA_AND_VIEW_ARCHITECTURE.md`, `frontend/src/utils/editorialWeeks.ts` |
| Stale backend deployment instructions | `WIA-Content-Atelier-main/DEPLOYMENT.md` (last section) |
| Stale proxy allowlist | `WIA-Command-Center-main/server/content-atelier-proxy.mjs` |
| Fixture-only Ops Hub screen | `WIA-Command-Center-main/src/components/opshub/screens/ContentAtelierScreen.tsx` |
| Competing spec and 2027 timeline | `WIA-Command-Center-main/Content_Atelier.md` (§5, §11, §12) |
| Corpus collected and access state | `WIA-Command-Center-main/wia_resource_mapping.md` |

## Appendix B. Test run recorded for this audit

```text
Location:  WIA-Content-Atelier-main/backend
Command:   python -m pytest -q --ignore=backend_pipeline/tests/test_sql_storage.py
Result:    112 passed in 9.88s  (Python 3.12.2)
Skipped:   backend_pipeline/tests/test_sql_storage.py (11 tests)
           needs the pgvector package and an isolated atelier_test database
```

No files in either repo were modified by this audit.
