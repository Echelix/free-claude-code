#!/bin/bash
# setup-env.sh - Create virtual environment and configure aliases
#
# This script:
# 1. Creates a .venv in the project root
# 2. Installs dependencies via uv
# 3. Optionally adds shell aliases to your shell config

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"
VENV_DIR="$PROJECT_ROOT/.venv"
VENV_BIN="$VENV_DIR/bin"

echo "=== Free Claude Code - Environment Setup ==="
echo ""

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "Installing uv..."
    if command -v brew &> /dev/null; then
        brew install uv
    else
        echo "Please install uv first: curl -LsSf https://astral.sh/uv/install.sh | sh"
        exit 1
    fi
fi

# Create virtual environment if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment in $VENV_DIR..."
    uv venv "$VENV_DIR"
else
    echo "Virtual environment already exists at $VENV_DIR"
fi

# Install dependencies
echo "Installing dependencies..."
uv pip sync --python "$VENV_DIR/bin/python" requirements.txt 2>/dev/null || \
uv pip install -e "$PROJECT_ROOT" --python "$VENV_DIR/bin/python"

# Get the shell config file
SHELL_NAME=$(basename "${SHELL:-bash}")
case "$SHELL_NAME" in
    zsh)
        SHELL_RC="$HOME/.zshrc"
        ;;
    bash)
        if [ -f "$HOME/.bash_profile" ]; then
            SHELL_RC="$HOME/.bash_profile"
        elif [ -f "$HOME/.bashrc" ]; then
            SHELL_RC="$HOME/.bashrc"
        else
            SHELL_RC="$HOME/.bash_profile"
        fi
        ;;
    *)
        SHELL_RC="$HOME/.profile"
        ;;
esac

echo ""
echo "Shell config file: $SHELL_RC"
echo ""

# Define the aliases
ALIAS_FCC_START="alias fcc-start='$VENV_BIN/fcc-start'"
ALIAS_FCC_STOP="alias fcc-stop='$VENV_BIN/fcc-stop'"
ALIAS_FCC_STATUS="alias fcc-status='$VENV_BIN/fcc-status'"
ALIAS_CLAUDEX="alias claudex='$VENV_BIN/claudex'"

# Check if aliases already exist
ALIASES_EXIST=true
for alias_line in "$ALIAS_FCC_START" "$ALIAS_FCC_STOP" "$ALIAS_FCC_STATUS" "$ALIAS_CLAUDEX"; do
    if ! grep -qF "$alias_line" "$SHELL_RC" 2>/dev/null; then
        ALIASES_EXIST=false
        break
    fi
done

if [ "$ALIASES_EXIST" = true ]; then
    echo "Aliases already configured in $SHELL_RC"
else
    echo ""
    echo "Would you like to add the aliases to $SHELL_RC? (y/n)"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        echo "" >> "$SHELL_RC"
        echo "# Free Claude Code aliases (added by setup-env.sh on $(date))" >> "$SHELL_RC"
        echo "$ALIAS_FCC_START" >> "$SHELL_RC"
        echo "$ALIAS_FCC_STOP" >> "$SHELL_RC"
        echo "$ALIAS_FCC_STATUS" >> "$SHELL_RC"
        echo "$ALIAS_CLAUDEX" >> "$SHELL_RC"
        echo ""
        echo "Aliases added to $SHELL_RC"
        echo "Run 'source $SHELL_RC' or open a new terminal to use them."
    else
        echo "Skipping alias configuration."
    fi
fi

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo "  1. If you added aliases: source $SHELL_RC"
echo "  2. Run 'fcc-start' to start the proxy server"
echo "  3. Run 'claudex' to launch Claude CLI"
