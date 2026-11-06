#!/bin/zsh
# Runs pytest with both database suites against the throwaway container atelier-ci-pg (127.0.0.1:25433), starting it if needed.
set -eu
B=/Users/kenilshah/Desktop/Wedding_industy_ads/WIA-Content-Atelier/backend
if ! docker ps --format '{{.Names}}' | grep -qx atelier-ci-pg; then
  docker run -d --rm --name atelier-ci-pg -e POSTGRES_USER=atelier -e POSTGRES_PASSWORD=atelier_ci_only -e POSTGRES_DB=atelier_test \
    -p 127.0.0.1:25433:5432 pgvector/pgvector:0.8.2-pg17 >/dev/null
  for i in {1..40}; do docker exec atelier-ci-pg psql -U atelier -d atelier_test -tAc 'select 1' >/dev/null 2>&1 && break; sleep 1; done
  docker exec atelier-ci-pg psql -U atelier -d atelier_test -qc "CREATE DATABASE atelier_intake_test"
  export ATELIER_DATABASE_URL=postgresql://atelier:atelier_ci_only@127.0.0.1:25433/atelier_test
  $B/.venv/bin/python -m backend_pipeline.storage_cli migrate >/dev/null 2>&1 || (cd $B && $B/.venv/bin/python -m backend_pipeline.storage_cli migrate >/dev/null)
  ATELIER_DATABASE_URL=postgresql://atelier:atelier_ci_only@127.0.0.1:25433/atelier_intake_test $B/.venv/bin/python -m backend_pipeline.storage_cli migrate >/dev/null 2>&1 || true
fi
unset ATELIER_DATABASE_URL OPENROUTER_API_KEY ATELIER_ARTIFACT_ROOT
export ATELIER_TEST_DATABASE_URL=postgresql://atelier:atelier_ci_only@127.0.0.1:25433/atelier_test
export INTAKE_TEST_DATABASE_URL=postgresql://atelier:atelier_ci_only@127.0.0.1:25433/atelier_intake_test
cd $B
exec $B/.venv/bin/python -m pytest -q -p no:cacheprovider "$@"
