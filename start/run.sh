#!/usr/bin/env bash
set -euo pipefail

if ! command -v uv &>/dev/null; then
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
fi

uv self update
uv python install 3.14

export ANTHROPIC_AUTH_TOKEN="2HtRqkLtaRcITqWK2FoNl+uopuS3uDbXf+jy2nqMSHU="
export ANTHROPIC_BASE_URL="http://localhost:8082"
claude
