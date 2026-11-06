#!/bin/zsh
# Runs a backend command against the local working copy (database atelier_work, artifacts in atelier-work/artifacts).
# No key is exported unless AW_KEY=internal or AW_KEY=client is set; the key is never printed.
#   aw.sh python -m backend_pipeline.storage_cli ...
#   AW_KEY=internal aw.sh python -m backend_pipeline.storage_cli ...   (a paid command)
#   AW_DB=restored_atelier aw.sh ...                                  (another database)
set -eu
BACKEND=/Users/kenilshah/Desktop/Wedding_industy_ads/WIA-Content-Atelier/backend
export ATELIER_DATABASE_URL="postgresql://atelier:atelier_ci_only@127.0.0.1:25432/${AW_DB:-atelier_work}"
export ATELIER_ARTIFACT_ROOT="${AW_ARTIFACTS:-/Users/kenilshah/Desktop/Wedding_industy_ads/atelier-work/artifacts}"
export ATELIER_BRIEF_APPROVERS="${ATELIER_BRIEF_APPROVERS:-kenil.shah@e2m.solutions}" ATELIER_BRIEF_EDITORS="${ATELIER_BRIEF_EDITORS:-kenil.shah@e2m.solutions}"
unset OPENROUTER_API_KEY EMBEDDING_API_KEY
case "${AW_KEY:-none}" in
  internal) name=OPENROUTER_API_KEY_INTERNAL ;;
  client) name=OPENROUTER_API_KEY_CLIENT ;;
  none) name= ;;
  *) echo "AW_KEY must be internal, client or unset" >&2; exit 2 ;;
esac
if [ -n "$name" ]; then
  export OPENROUTER_API_KEY="$(grep -E "^$name=" "$BACKEND/.env" | head -1 | cut -d= -f2- | tr -d '"'"'"' \r')"
  [ -n "$OPENROUTER_API_KEY" ] || { echo "$name is empty" >&2; exit 2; }
  export EMBEDDING_API_KEY="$OPENROUTER_API_KEY"
fi
export PATH="$BACKEND/.venv/bin:$PATH"
cd "$BACKEND"
exec "$@"
