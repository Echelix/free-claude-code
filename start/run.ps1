$ErrorActionPreference = "Stop"

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "Installing uv..."
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    $env:PATH = "$env:USERPROFILE\.local\bin;$env:USERPROFILE\.cargo\bin;$env:PATH"
}

uv self update
uv python install 3.14

$env:ANTHROPIC_AUTH_TOKEN = "2HtRqkLtaRcITqWK2FoNl+uopuS3uDbXf+jy2nqMSHU="
$env:ANTHROPIC_BASE_URL = "http://localhost:8082"
claude
