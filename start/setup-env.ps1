# setup-env.ps1 - Create virtual environment and configure aliases for Windows
#
# This script:
# 1. Creates a .venv in the project root
# 2. Installs dependencies via uv
# 3. Optionally adds shell aliases (functions) to your PowerShell profile

$ErrorActionPreference = "Stop"

Write-Host "=== Free Claude Code - Environment Setup (Windows) ==="
Write-Host ""

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvDir = Join-Path $ProjectRoot ".venv"
$VenvScripts = Join-Path $VenvDir "Scripts"

# Check if uv is installed
try {
    $uv = Get-Command uv -ErrorAction Stop
} catch {
    Write-Host "uv not found. Installing..."
    try {
        winget install --id astral-sh.uv
    } catch {
        Write-Host "Please install uv first: powershell -ExecutionPolicy ByPass -c `"irm https://astral.sh/uv/install.ps1 | iex`""
        exit 1
    }
}

# Create virtual environment if it doesn't exist
if (-not (Test-Path $VenvDir)) {
    Write-Host "Creating virtual environment in $VenvDir..."
    uv venv $VenvDir
} else {
    Write-Host "Virtual environment already exists at $VenvDir"
}

# Install dependencies
Write-Host "Installing dependencies..."
if (Test-Path (Join-Path $ProjectRoot "requirements.txt")) {
    uv pip sync --python (Join-Path $VenvScripts "python.exe") (Join-Path $ProjectRoot "requirements.txt")
} else {
    uv pip install -e $ProjectRoot --python (Join-Path $VenvScripts "python.exe")
}

# PowerShell profile path
$ProfilePath = $PROFILE
if (-not (Test-Path $ProfilePath)) {
    New-Item -Path $ProfilePath -ItemType File -Force | Out-Null
}

# Function definitions to add
$FunctionDefs = @"

# Free Claude Code aliases (added by setup-env.ps1 on $(Get-Date))
function fcc-start { & $VenvScripts\fcc-start.ps1 }
function fcc-stop { & $VenvScripts\fcc-stop.ps1 }
function fcc-status { & $VenvScripts\fcc-status.ps1 }
function claudex { & $VenvScripts\claudex.ps1 }
"@

# Check if aliases already exist
$Content = Get-Content $ProfilePath -Raw -ErrorAction SilentlyContinue
$AliasesExist = $false
if ($Content -match "function fcc-start") {
    $AliasesExist = $true
}

if ($AliasesExist) {
    Write-Host "Aliases already configured in $ProfilePath"
} else {
    Write-Host ""
    Write-Host "Would you like to add the aliases to $ProfilePath? (y/n)"
    $response = Read-Host
    if ($response -match "^[Yy]$") {
        Add-Content -Path $ProfilePath -Value $FunctionDefs
        Write-Host "Aliases added to $ProfilePath"
        Write-Host "Run '. $ProfilePath' or open a new PowerShell to use them."
    } else {
        Write-Host "Skipping alias configuration."
    }
}

Write-Host ""
Write-Host "=== Setup Complete ==="
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. If you added aliases: . $ProfilePath"
Write-Host "  2. Run 'fcc-start' to start the proxy server"
Write-Host "  3. Run 'claudex' to launch Claude CLI"
