# Phase S stabilise: engineering items (handover)

18 October 2026. This covers plan revision 6 items S.B2 (frontend build and CI), S.B4 (brief validator), S.B5 (one
embedding contract) and S.B13 (Gate 1 approval independent of brief configuration), plus two small fixes. Everything
was done offline: no model or embedding calls. S.B1 (privacy routing) is out of scope; it waits for the account's
retention settings.

## Status

| Item | State | Where |
| --- | --- | --- |
| S.B2 frontend build | Done. A plain `npm ci` works. | `frontend/package.json`, `package-lock.json`, `.nvmrc` |
| S.B2 CI | Done. Passes actionlint. It runs for the first time on the push of this change. | `.github/workflows/ci.yml` |
| S.B5 embedding contract | Done | `backend_pipeline/config.py`, `startup.py`, env examples |
| S.B4 validator | Done. The two real briefs have not been re-validated (see "Left to do"). | `briefs/validation.py`, `briefs/contracts.py`, `prompt_templates/brief_write.v1.md` |
| S.B13 Gate 1 approval | Done, without changing `gate_one.py` | `briefs/workflow.py`, `startup.py` |
| Small fixes | Done | `backend/.env.example`, `knowledge_base.example/*.md`, `frontend/docker-compose.yml` |

## What changed

### S.B2: frontend build, Node pin and CI
- The root `esbuild` dev dependency is now `^0.28.0`. This meets Vite 8's peer range (`^0.27 || ^0.28`) and dedupes with
  tsx's `~0.28`. The lockfile was regenerated with npm 11 on Node 24.
- `frontend/.nvmrc` is `24`, the same as the Dockerfile. `engines.node` is `>=22.12.0`: Vite 8 needs 20.19+ or 22.12+,
  and `npm start` uses `--env-file-if-exists` (22.9+).
- New scripts: `npm run test:unit` and `npm run test:server`. `npm test` runs both.
- CI has four jobs:
  1. Backend lint and offline tests.
  2. Both database suites against `pgvector/pgvector:0.8.2-pg17`, the image and digest from `compose.yml`.
     They use isolated `atelier_test` and `atelier_intake_test` databases.
  3. Frontend type check, unit tests, server tests and production build.
  4. Both Docker image builds.
- Lint is `ruff check --select E9,F63,F7,F82` (syntax errors and undefined names). Ruff's default rules report about 170
  existing issues, so a full style gate would fail from the start.
- CI deselects the four tests that read untracked research and corpus files. The list is in the workflow's
  `KNOWN_UNTRACKED_INPUT_TESTS`. Remove each entry when S.B6 commits its fixture.
- `frontend/bun.lock` still pins the old esbuild. Neither the build nor CI uses it; delete it or regenerate it with Bun.

### S.B5: one embedding contract
- `config.py` defines the contract once: `EMBEDDING_ENDPOINT` (`https://openrouter.ai/api/v1`), `EMBEDDING_MODEL`
  (`openai/text-embedding-3-small`) and `EMBEDDING_DIMENSIONS` (1536), plus `embedding_contract(models)`.
- Every digest is built from that one definition: chunk encoding, signature encoding, research query vectors, the brief
  execution contract and the archive snapshot.
- The digests equal the earlier formulas, so stored provenance stays valid. `test_phase_s.py` pins this.
- `backend/.env.example`, `intake.env.example` and `storage.env.example` all carry the same three values.
- **Behaviour change.** A process with no `EMBEDDING_BASE_URL` or `OPENAI_EMBEDDING_MODEL` set used to fall back to the
  OpenAI values. It now gets OpenRouter. Check the environment of any deployed process that relied on that fallback.
- `startup.py` runs at start-up in the API (FastAPI lifespan) and in every queue worker (`python -m backend_pipeline.jobs worker`, plan 0.B5), and in `storage_cli worker`.
  - It reads the contract digests recorded by completed chunk-encoding and angle-signature jobs.
  - If digests are recorded and none matches the process's contract, the process refuses to start. The message names
    both contracts.
  - To re-encode the archive on purpose, set `ATELIER_ALLOW_EMBEDDING_CONTRACT_CHANGE=true` for that run only.
  - If the database cannot be reached at start-up, the check logs a warning and the process starts.

### S.B4: brief validator (N2)
- The number scan ignores three kinds of numbers: known identifiers (claim, evidence, question and prior-angle IDs),
  labels like `[C3]` or `[C1, Q2]`, and slide, step and week numbering ("Slide 2 of 8", "steps 2-3", "Week 2").
  Real quantities next to these, such as "40 percent [C1]", still block.
- `Claim.source_status` is the six-value `ClaimStatus` enum. `ClaimStatus` is now a named alias in `contracts.py`;
  the moment schema hash is unchanged.
- Evidence whose status is `unknown` supports only `reported`. It used to support `unknown`, which the enum no longer
  allows.
- A stored brief with a prose status, such as "reported by the venue owner", gets a blocking finding from `checks()`.
  It no longer fails to load.
- The writer and repair calls send `writer_schema(prior_ids)`. Its `prior_differences` has exactly the supplied
  prior-angle IDs as required keys, and no other keys are allowed.
- `finalize` drops any extra key. In `checks()`, an extra key is a warning; a missing key still blocks.
- The writer prompt (`brief_write.v1.md`) now states the status rule and the prior-key rule. Because the prompt and
  schema changed, their hashes in the brief execution contract changed too. A brief run queued before this change fails
  with "Frozen brief execution contract changed" and has to be queued again.

### S.B13: approval does not depend on brief configuration
- `gate_one.py` is unchanged. Its call to `queue_in_transaction` now queues the first brief inside a savepoint.
- If queueing fails, for example because the brand bundle is missing:
  - the savepoint rolls back;
  - a failed `brief_generation` run, `brief_run_unqueued_<uuid>`, records the reason in `error_summary`, and a
    `brief_queue_failed` event is logged;
  - the approval commits.
- The failed run's ID is not the brief's deterministic ID. Running `storage_cli brief --angle-id …` after the fix
  creates the real run.
- Explicit `queue()` calls and revisions still raise, as before.
- `gate_two.research` now returns `error_summary`. The frontend does not show it yet.
- Start-up check: with `ATELIER_BRIEFS_ENABLED=true`, the API and SQL worker refuse to start unless
  `ATELIER_BRAND_BUNDLE_PATH` names a reviewed bundle. Synthetic test databases may use the built-in fixture.

### Small fixes
- `backend/.env.example` and the five `knowledge_base.example` placeholder headers now say the knowledge base is
  committed. The `KNOWLEDGE-BASE-PLACEHOLDER` marker is kept, because the loader looks for it.
- `frontend/docker-compose.yml` passes `ATELIER_BACKEND_ORIGIN` and `ATELIER_API_SECRET`, both blank by default.
  `frontend/.env.example` documents them.

## Verification (18 October, Windows, Python 3.12, Node 24 in Docker)
- Backend offline: 329 passed, 101 skipped (PostgreSQL), and the 4 known untracked-input failures.
- Backend with both databases (pgvector 0.8.6-pg17 locally), using CI's command and deselect list: 430 passed,
  1 skipped (local paid research artifacts), 4 deselected. `test_future_intake.py` had a mocked embedding endpoint tied
  to the old OpenAI default URL; it now follows the configured endpoint.
- Frontend on Node 24.21: `npm ci`, type check, unit and server tests, and the production build all pass.
- `docker build` succeeds for both `frontend/` and `backend/`.
- `.github/workflows/ci.yml` passes actionlint 1.7.7.

## Reproduce on another machine

Backend, from `backend/`:

```bash
python -m venv .venv && . .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt "pytest>=8,<10" fakeredis==2.32.1 ruff==0.17.1
ruff check --select E9,F63,F7,F82 backend_pipeline scripts
python -m pytest -q
```

Database suites, using a throwaway pgvector container. Its name and port are its own: a machine that keeps a restored
handover in a long-lived container (the owner's, `atelier-test-pg` on 25432) must never share them, because `--rm` and a
`docker stop` would remove that data with it.

```bash
docker run -d --rm --name atelier-ci-pg -e POSTGRES_USER=atelier -e POSTGRES_PASSWORD=atelier_ci_only \
  -e POSTGRES_DB=atelier_test -p 127.0.0.1:25433:5432 pgvector/pgvector:0.8.2-pg17
docker exec atelier-ci-pg psql -U atelier -d atelier_test -c "CREATE DATABASE atelier_intake_test"
export ATELIER_TEST_DATABASE_URL=postgresql://atelier:atelier_ci_only@127.0.0.1:25433/atelier_test
export INTAKE_TEST_DATABASE_URL=postgresql://atelier:atelier_ci_only@127.0.0.1:25433/atelier_intake_test
ATELIER_DATABASE_URL=$ATELIER_TEST_DATABASE_URL python -m backend_pipeline.storage_cli migrate
ATELIER_DATABASE_URL=$INTAKE_TEST_DATABASE_URL python -m backend_pipeline.storage_cli migrate
python -m pytest -q -rs
```

Frontend, from `frontend/`, on Node 24 (`nvm use`):

```bash
npm ci && npm run lint && npm test && npm run build
```

## Left to do
- **S.B4 follow-through.** Run `checks()` on the two real briefs (`brief_f4778b6818b357fde23bb1b4` and
  `brief_2ff7b35b7ad9cc0e3493bc82`). This needs the developer's database and `.storage-artifacts`. Real blocking findings
  that remain go to S.X1.
- **Frontend.** Show the run-level `error_summary` in `SQLBriefs.tsx`, so a brief that failed to queue explains itself.
- **S.B6.** Commit fixtures for the four deselected tests, then remove the deselect list from CI.
- **Lint.** Raise the ruff gate gradually once the existing issues are cleaned up.
- **CI.** Check the first CI run on GitHub. It has not run yet, and the database job has never run in a hosted runner.
- S.B1 and the other Phase S items are not covered here.
