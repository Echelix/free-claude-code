#!/usr/bin/env bash
# run.sh - Launch Claude Code against the local proxy.
# Reads ANTHROPIC_AUTH_TOKEN and the port from the managed config (~/.fcc/.env)
# and waits for the proxy health check before starting claude.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

if [[ ! -f "$HOME/.fcc/.env" ]]; then
    echo "Error: ~/.fcc/.env not found. Run: mkdir -p ~/.fcc && cp .env.nvidia.example ~/.fcc/.env" >&2
    exit 1
fi

exec uv run claudex "$@"
