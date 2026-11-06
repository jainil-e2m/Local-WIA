# S.B8: a container from the documented variables replays a brief (20 October 2026)

`container.env` holds only variables DEPLOYMENT.md documents for the editorial API and worker (no key, no secret). The
image is the repository's `backend/Dockerfile` (`docker build -t content-atelier-backend:sb8 backend/`). The database is a
copy of the local working copy (D20); the artifact store is a host folder mounted at `/artifacts`.

## What ran

Two copies of the working database were made before anything ran (`CREATE DATABASE atelier_sb8a TEMPLATE atelier_work`,
the same for `atelier_sb8b`); in both, the 13 October v1 brief of `angle_1d20dd133d5492c950608290` and its run were removed
so a first brief on the current contract (v2, writer v3) is queued, not the old one returned.

Container A (`atelier_sb8a`; the key and the switches `ATELIER_ALLOW_GENERATION`, `ATELIER_ALLOW_BRIEF_GENERATION`,
`ATELIER_ALLOW_ENCODING` and `ATELIER_RUN_PLAN_ID` passed with `-e`):

    docker run --rm --env-file container.env -e ATELIER_DATABASE_URL=...atelier_sb8a -e OPENROUTER_API_KEY -e EMBEDDING_API_KEY \
      -e ATELIER_ALLOW_GENERATION=true -e ATELIER_ALLOW_BRIEF_GENERATION=true -e ATELIER_ALLOW_ENCODING=true \
      -e ATELIER_RUN_PLAN_ID=<plan> -v <artifacts>:/artifacts content-atelier-backend:sb8 \
      python -m backend_pipeline.storage_cli migrate | plan create ... | brief --angle-id <angle> --actor <approver> --mode live | worker --max-jobs 12

- `migrate`: 103 checks, from inside the container.
- The brief: prepare, research (two rounds: brief_plan and brief_grade on Claude Sonnet 5.5, query vectors), context:
  completed; USD 0.41 under `plan_091583525058401097c6` (cap USD 0.33: the plan refuses the call after the cap is
  passed, not the call that passes it). brief_writing was refused by the exhausted plan.
- The first attempt failed with HTTP 402: OpenRouter refuses a request whose worst case (its input plus the full output
  cap) exceeds what the key has left; `CONTENT_ATELIER_LLM_COMPLETION_TOKENS=12000` (documented) fixed it.

Container B (`atelier_sb8b`, the same image, env file and artifact folder; no key, no plan, generation switches off):

    docker run --rm --env-file container.env -e ATELIER_DATABASE_URL=...atelier_sb8b -v <artifacts>:/artifacts \
      content-atelier-backend:sb8 python -m backend_pipeline.storage_cli brief --angle-id <angle> --actor <approver> --mode replay
    ... storage_cli worker --max-jobs 12

- prepare, research and context completed with no provider call: four `llm_runs` rows `replayed` (USD 0), the query
  vectors from the store (`brief_cache_reused` 4).
- brief_writing: "No compatible brief response is cached; external brief calls are disabled", because container A never
  paid for it.

## To finish (about USD 0.1 to 0.3)

In container A: a new run plan (stages `brief_write`, `brief_repair`; model `openai/gpt-6.1-sol`), then retry the
failed brief_writing job and run the worker; it writes and validates the brief. Then reset `atelier_sb8b`'s brief run
(as above) and repeat container B's two commands: every stage must complete with only `replayed` rows.
