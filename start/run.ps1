# run.ps1 - Launch Claude Code against the local proxy.
# Reads ANTHROPIC_AUTH_TOKEN and the port from the managed config (~/.fcc/.env)
# and waits for the proxy health check before starting claude.
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location (Split-Path -Parent $ScriptDir)

$ManagedEnv = Join-Path $env:USERPROFILE ".fcc\.env"
if (-not (Test-Path $ManagedEnv)) {
    Write-Error "$ManagedEnv not found. Copy .env.nvidia.example there first."
    exit 1
}

uv run claudex @args
