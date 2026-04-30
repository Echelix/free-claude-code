#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

if ! command -v uv &>/dev/null; then
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
fi

# Remove any pyenv .python-version pin that would override uv's managed Python
rm -f .python-version

uv self update
uv python install 3.14
uv sync

source .venv/bin/activate
uvicorn server:app --host 0.0.0.0 --port 8082
