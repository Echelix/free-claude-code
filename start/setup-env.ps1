# setup-env.ps1 - Install uv + Python 3.14, sync the project, and configure PowerShell functions
#
# Adds fcc-start / fcc-stop / fcc-status / claudex functions to $PROFILE pointing at this checkout's .venv.

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$VenvScripts = Join-Path $ProjectRoot ".venv\Scripts"

Write-Host "=== Free Claude Code (Echelix) - Environment Setup ==="
Write-Host ""

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "Installing uv..."
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    $env:PATH = "$env:USERPROFILE\.local\bin;$env:USERPROFILE\.cargo\bin;$env:PATH"
}

uv self update
uv python install 3.14
Push-Location $ProjectRoot
try { uv sync } finally { Pop-Location }

$ManagedEnv = Join-Path $env:USERPROFILE ".fcc\.env"
if (-not (Test-Path $ManagedEnv)) {
    Write-Host ""
    Write-Host "No managed config found. Create one with:"
    Write-Host "  New-Item -ItemType Directory -Force `$env:USERPROFILE\.fcc; Copy-Item $ProjectRoot\.env.nvidia.example `$env:USERPROFILE\.fcc\.env"
}

$Functions = @(
    "function fcc-start { & `"$VenvScripts\fcc-start.exe`" @args }",
    "function fcc-stop { & `"$VenvScripts\fcc-stop.exe`" @args }",
    "function fcc-status { & `"$VenvScripts\fcc-status.exe`" @args }",
    "function claudex { & `"$VenvScripts\claudex.exe`" @args }"
)

if (-not (Test-Path $PROFILE)) {
    New-Item -ItemType File -Path $PROFILE -Force | Out-Null
}
$Content = Get-Content $PROFILE -Raw -ErrorAction SilentlyContinue
if ($Content -and $Content -match "function fcc-start") {
    Write-Host "Functions already configured in $PROFILE"
} else {
    $response = Read-Host "Add fcc-start / fcc-stop / fcc-status / claudex functions to $PROFILE? (y/n)"
    if ($response -match "^[Yy]$") {
        Add-Content $PROFILE ""
        Add-Content $PROFILE "# Free Claude Code functions (added by start\setup-env.ps1 on $(Get-Date))"
        $Functions | ForEach-Object { Add-Content $PROFILE $_ }
        Write-Host "Functions added. Run '. `$PROFILE' or open a new terminal."
    } else {
        Write-Host "Skipping profile configuration."
    }
}

Write-Host ""
Write-Host "=== Setup Complete ==="
Write-Host "Next steps:"
Write-Host "  1. Edit $ManagedEnv (NVIDIA_NIM_API_KEY, ANTHROPIC_AUTH_TOKEN, MODEL_*)"
Write-Host "  2. fcc-start     # start the proxy in the background"
Write-Host "  3. claudex       # launch Claude Code"
