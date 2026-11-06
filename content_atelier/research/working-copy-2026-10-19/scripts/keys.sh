#!/bin/zsh
# Prints the remaining limit of both OpenRouter keys (never the keys).
B=/Users/kenilshah/Desktop/Wedding_industy_ads/WIA-Content-Atelier/backend
for name in OPENROUTER_API_KEY_INTERNAL OPENROUTER_API_KEY_CLIENT; do
  k=$(grep -E "^$name=" $B/.env | head -1 | cut -d= -f2- | tr -d '"'"'"' \r')
  printf '%s ' "${name#OPENROUTER_API_KEY_}"
  curl -s -m 20 -H "Authorization: Bearer $k" https://openrouter.ai/api/v1/key | $B/.venv/bin/python -I -c '
import json, sys
d = json.load(sys.stdin)["data"]
print("remaining=%.4f usage=%.4f reset=%s" % (d["limit_remaining"], d["usage"], d["limit_reset"]))'
done
