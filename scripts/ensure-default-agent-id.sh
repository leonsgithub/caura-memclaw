#!/usr/bin/env bash
# Ensure a stable default agent identity is seeded into .env.
#
# Format: memclaw-<repo-folder>-<6-hex of host IP>-<3-digit random>
#   e.g. memclaw-caura-memclaw-c8624d-417
#
# Only the random suffix is non-deterministic, so it is generated ONCE and
# written to .env; every later load reads the same name from .env. No-op if
# MEMCLAW_DEFAULT_AGENT_ID is already set — so re-running is safe and the
# identity never drifts (agent_id is the memory-ownership key).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="${1:-$REPO_ROOT/.env}"
KEY=MEMCLAW_DEFAULT_AGENT_ID

if [ -f "$ENV_FILE" ] && grep -q "^${KEY}=" "$ENV_FILE"; then
  echo "$KEY already set: $(grep "^${KEY}=" "$ENV_FILE")"
  exit 0
fi

folder="$(basename "$REPO_ROOT")"
ip="$(hostname -I | awk '{print $1}')"
hash6="$(printf '%s' "$ip" | sha256sum | cut -c1-6)"
rand3="$(printf '%03d' $(( RANDOM % 1000 )))"
aid="memclaw-${folder}-${hash6}-${rand3}"

printf '\n# Stable default agent identity (auto-seeded once by ensure-default-agent-id.sh).\n%s=%s\n' \
  "$KEY" "$aid" >> "$ENV_FILE"
echo "generated $KEY=$aid"
