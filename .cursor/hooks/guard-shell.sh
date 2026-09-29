#!/usr/bin/env bash
# Author: John Developer <john@kubozoa.com>
# Guardrail hook: deny destructive/unsafe git and shell patterns for agents.
set -euo pipefail

payload="$(cat)"
command="$(printf '%s' "$payload" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("command",""))' 2>/dev/null || true)"

deny_message=""

if printf '%s' "$command" | grep -Eiq '(^|[;&|[:space:]])(git[[:space:]]+push[[:space:]]+.*--force|--force-with-lease)'; then
  if printf '%s' "$command" | grep -Eiq '[[:space:]](main|master|develop)([[:space:]]|$)'; then
    deny_message="Force-push to main/master/develop is blocked by project hooks."
  fi
fi

if printf '%s' "$command" | grep -Eiq 'git[[:space:]]+commit.*--no-verify|git[[:space:]]+push.*--no-verify'; then
  deny_message="Skipping git hooks (--no-verify) is blocked by project hooks."
fi

if printf '%s' "$command" | grep -Eiq 'rm[[:space:]]+-rf[[:space:]]+[\"'\'']?/([[:space:]]|$)|rm[[:space:]]+-rf[[:space:]]+[\"'\'']?\*'; then
  deny_message="Destructive recursive rm is blocked by project hooks."
fi

if [[ -n "$deny_message" ]]; then
  printf '{"permission":"deny","userMessage":"%s","agentMessage":"%s"}\n' "$deny_message" "$deny_message"
  exit 0
fi

printf '{"permission":"allow"}\n'
