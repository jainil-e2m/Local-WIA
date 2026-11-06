> The governing plan is `Content-Atelier-Implementation-Plan-Brief-Generation.md` (Phase 2, section 10). This note says what Phase 2 left and in what order to run it on the real corpus. Detail: `Phase-2-Extraction-Notes.md` (extraction, checks, triage, import, backfill, recall) and `Phase-2-Search-Notes.md` (search, citation, embeddings, topics, API).

# Phase 2: moments ledger and retrieval, hand-over

Branch `item/2-moments-ledger`, from `main` after Phases 0 and 1. Item status is in the plan (section 10 and "Implementation status"); the log row is in Appendix G.

## What exists now

| Part | Where | What it does |
| --- | --- | --- |
| Migration 008 (plan label 007) | `migrations/008_moments_ledger.sql` | `key_moments` belongs to a document (week and run are optional) and carries speaker and role, evidence kind, client, consent, quote verification and repair, sensitivity, destination, date, extractor, checks, currency, a vector and a full-text column; `topics`, `moment_topics`; `decisions` accepts `topic`. Existing moments and E.B12a's unverified ones are promoted in the migration. |
| Vocabularies | `moments/types.py` | Twelve moment types, speaker roles, evidence kinds, consent statuses: one place. |
| Extraction | `moments/scenes.py`, `extract.py`, `jobs.py`, `queue.py`, `store.py`, prompt `scene_extraction.v2.md` | One job per included document in a `document_extraction` run; scene profile `2026-10-19.scenes.v2`; each scene validated alone. |
| Checks | `moments/checks.py`, `recheck.py` | Role plausibility, numbers in the source, consent from the client's level and the sensitivity. |
| Triage and import | `normalise/classify.py` (`triage_slack`), `moments/imports.py` | Slack threads that are not content are excluded before extraction; saved Week 1 and 2 moments are imported with provenance and no provider call. |
| Backfill tooling | `moments/cli.py`, `report.py`, `recall.py` | `moments extract|report|recheck|recall|import-saved`. |
| Embeddings | `moments/embedding.py`, `search/jobs.py` | `moments-embed queue|report`; a planned `bulk` run; the archive's contract. |
| Search | `search/*` | `POST /storage/search` and `storage_cli search query`; one `Citation`. |
| Ledger API | `moments/api.py`, `moments/health.py` | `GET /moments`, `/moments/facets`, `/moments/{id}`, `POST /moments/{id}/topics`, `GET /documents/extraction-health`. |
| Topics | `moments/topics.py` | `topics assign|list|show|rename|merge|block|unblock`; routes under `/topics`. |
| Screens | `frontend/src/components/MomentsLedger.tsx`, `MomentDetail.tsx`, `ExtractionHealth.tsx` | The ledger (Moments in the navigation), a moment at `/moments/:id`, extraction health on the Sources documents page. |

## Running it on the real corpus (after S.B10 and the production environment)

Each paid step is estimated first and runs under a run plan bound to its input set (E.B1, R39); nothing below makes a call without one.

1. Documents first (`DEPLOYMENT.md`, "Documents and evidence"): `documents import`, `normalise`, `dates --apply`, `reembed`.
2. `moments import-saved <Week 1 and 2 artifacts> --dry-run`, read what matched, then without `--dry-run`. No provider call.
3. `moments extract --pilot 10 --estimate`, create the plan the estimate names, `moments extract --pilot 10 --mode live`, then `moments report`. **A person reads the ten documents' scenes** before going on (2.B11's gate).
4. `moments extract --all-pending --estimate`, its plan, `--mode live` on the `bulk` queue. Record the verified-quote share and the role distribution from `moments report` in the plan.
5. `moments-embed queue --estimate`, its plan, `--mode live`; then `topics assign --estimate` and its run. Read the first topic run (the thresholds are defaults).
6. A person lists the golden scenes (the Funktastic chain, the benchmark weeks') in the format in `Phase-2-Extraction-Notes.md`; `moments recall --golden` compares v2 with v1. v2 becomes the weekly cycle's profile only when its recall is at least v1's.
7. A standing run plan for query embedding in the API process, so `POST /search` can use meaning as well as words (`Phase-2-Search-Notes.md`).

## What is left, and why

| Remainder | Blocked on |
| --- | --- |
| 2.B11: the pilot, the backfill, the measured verified-quote share and role distribution | S.B10 (the transcripts), the production environment (0.B7), an OpenRouter key under a run plan |
| Golden fixture (the Funktastic chain) and scene recall of v2 against v1 | A person listing the golden scenes; the real transcripts |
| Running `import-saved` on the real Week 1 and 2 artifacts | S.B10 |
| Tuning `topics.attach_similarity`, `search.semantic_min_cosine`, the estimate's output-token assumption | The pilot and the first real runs |
| The weekly paths keep unverified moments in the job record, not as rows | Phase 3 retires the per-run extraction; passing `unverified=` to `repo.save_moments` then stores them |

## Quirks worth knowing

* The baseline `atelier_test` database is migrated by CI (`storage_cli migrate`) and must equal the latest catalogue; if a migration changes while you work, recreate it (drop and create `atelier_test` and `atelier_intake_test` from `postgres`, then migrate both).
* Two agents or processes must not share one Postgres container for database suites: the suites recreate the `atelier_test_*` databases.
* `test_comparison_workflow.py::test_eight_proposals_six_targets_one_refinement_three_reports` can fail with Windows socket error 10048 when other work runs in parallel; it passes alone.
* `jobs/recover.py` settles a `document_extraction` run through `moments.queue.settle_run`; a `document_intake` (normalise) run still fails whole when one job loses its lease for good (Phase 1's behaviour, retried with `repo.retry`).
