#!/usr/bin/env bash
# Quick sanity check for the Anthropic API key in .env.hw8
set -euo pipefail
cd "$(dirname "$0")/.."
set -a && . ./.env.hw8 && set +a

echo "Key prefix: ${ANTHROPIC_API_KEY:0:20}..."
echo
curl -sS https://api.anthropic.com/v1/messages \
  -H "x-api-key: ${ANTHROPIC_API_KEY}" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{"model":"claude-haiku-4-5","max_tokens":20,"messages":[{"role":"user","content":"say hi"}]}'
echo
