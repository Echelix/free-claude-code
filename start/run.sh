#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$ROOT_DIR/.env"

if ! command -v uv &>/dev/null; then
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
fi

uv self update
uv python install 3.14

if [[ ! -f "$ENV_FILE" ]]; then
    echo "Error: $ENV_FILE not found. Copy .env.nvidia.example to .env first." >&2
    exit 1
fi

# Load ANTHROPIC_AUTH_TOKEN from .env (single source of truth).
# set -a exports every variable assigned while sourcing.
set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

if [[ -z "${ANTHROPIC_AUTH_TOKEN:-}" ]]; then
    echo "Error: ANTHROPIC_AUTH_TOKEN is empty in $ENV_FILE" >&2
    exit 1
fi

export ANTHROPIC_BASE_URL="http://localhost:8082"
claude
