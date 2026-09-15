#!/usr/bin/env bash
# setup-env.sh - Install uv + Python 3.14, sync the project, and configure shell aliases
#
# Adds fcc-start / fcc-stop / fcc-status / fcc-models / claudex aliases pointing at this checkout's .venv.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_BIN="$PROJECT_ROOT/.venv/bin"

echo "=== Free Claude Code (Echelix) - Environment Setup ==="
echo ""

if ! command -v uv &>/dev/null; then
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
fi

uv self update
uv python install 3.14
(cd "$PROJECT_ROOT" && uv sync)

if [[ ! -f "$HOME/.fcc/.env" ]]; then
    echo ""
    echo "No managed config found. Create one with:"
    echo "  mkdir -p ~/.fcc && cp $PROJECT_ROOT/.env.nvidia.example ~/.fcc/.env"
fi

SHELL_NAME=$(basename "${SHELL:-bash}")
case "$SHELL_NAME" in
    zsh) SHELL_RC="$HOME/.zshrc" ;;
    bash)
        if [[ -f "$HOME/.bash_profile" ]]; then SHELL_RC="$HOME/.bash_profile"
        elif [[ -f "$HOME/.bashrc" ]]; then SHELL_RC="$HOME/.bashrc"
        else SHELL_RC="$HOME/.bash_profile"; fi ;;
    *) SHELL_RC="$HOME/.profile" ;;
esac

ALIASES=(
    "alias fcc-start='$VENV_BIN/fcc-start'"
    "alias fcc-stop='$VENV_BIN/fcc-stop'"
    "alias fcc-status='$VENV_BIN/fcc-status'"
    "alias fcc-models='$VENV_BIN/fcc-models'"
    "alias claudex='$VENV_BIN/claudex'"
)

echo ""
echo "Shell config file: $SHELL_RC"
ALIASES_EXIST=true
for alias_line in "${ALIASES[@]}"; do
    grep -qF "$alias_line" "$SHELL_RC" 2>/dev/null || ALIASES_EXIST=false
done

if [[ "$ALIASES_EXIST" == true ]]; then
    echo "Aliases already configured in $SHELL_RC"
else
    echo "Add the fcc-start / fcc-stop / fcc-status / fcc-models / claudex aliases to $SHELL_RC? (y/n)"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        {
            echo ""
            echo "# Free Claude Code aliases (added by start/setup-env.sh on $(date))"
            printf '%s\n' "${ALIASES[@]}"
        } >> "$SHELL_RC"
        echo "Aliases added. Run 'source $SHELL_RC' or open a new terminal."
    else
        echo "Skipping alias configuration."
    fi
fi

echo ""
echo "=== Setup Complete ==="
echo "Next steps:"
echo "  1. Edit ~/.fcc/.env (NVIDIA_NIM_API_KEY, ANTHROPIC_AUTH_TOKEN, MODEL_*)"
echo "  2. fcc-start     # start the proxy in the background"
echo "  3. claudex       # launch Claude Code"
