$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Split-Path -Parent $ScriptDir
$EnvFile = Join-Path $RootDir ".env"

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "Installing uv..."
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    $env:PATH = "$env:USERPROFILE\.local\bin;$env:USERPROFILE\.cargo\bin;$env:PATH"
}

uv self update
uv python install 3.14

if (-not (Test-Path $EnvFile)) {
    Write-Error "$EnvFile not found. Copy .env.nvidia.example to .env first."
    exit 1
}

# Load ANTHROPIC_AUTH_TOKEN from .env (single source of truth).
$tokenLine = Get-Content $EnvFile | Where-Object { $_ -match '^\s*ANTHROPIC_AUTH_TOKEN\s*=' } | Select-Object -First 1
if (-not $tokenLine) {
    Write-Error "ANTHROPIC_AUTH_TOKEN not set in $EnvFile"
    exit 1
}
$token = ($tokenLine -replace '^\s*ANTHROPIC_AUTH_TOKEN\s*=\s*', '').Trim()
$token = $token -replace '^["'']', '' -replace '["'']$', ''
if ([string]::IsNullOrEmpty($token)) {
    Write-Error "ANTHROPIC_AUTH_TOKEN is empty in $EnvFile"
    exit 1
}

$env:ANTHROPIC_AUTH_TOKEN = $token
$env:ANTHROPIC_BASE_URL = "http://localhost:8082"
claude
