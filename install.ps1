# RetailStack POS Agent - Windows Quick Install
# Run this in PowerShell:
# irm https://raw.githubusercontent.com/ugwumadu116/RetailStack-POS-Agent/main/install.ps1 | iex

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  RetailStack POS Agent - Quick Install" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Find Python
$pythonCmd = $null
foreach ($cmd in @("python", "python3", "py")) {
    if (Get-Command $cmd -ErrorAction SilentlyContinue) {
        $pythonCmd = $cmd
        break
    }
}

if (-not $pythonCmd) {
    Write-Host "❌ Python not found. Install from https://python.org" -ForegroundColor Red
    Write-Host "   Make sure to check 'Add Python to PATH'" -ForegroundColor Yellow
    exit 1
}

$pythonVersion = & $pythonCmd --version 2>&1
Write-Host "✅ Python found: $pythonVersion" -ForegroundColor Green

# Get script directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

# Install dependencies
Write-Host ""
Write-Host "📦 Installing dependencies..." -ForegroundColor Yellow
& $pythonCmd -m pip install pyserial requests python-dateutil 2>$null

if ($LASTEXITCODE -ne 0) {
    & $pythonCmd -m pip install --user pyserial requests python-dateutil 2>$null
}

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to install dependencies" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Dependencies installed" -ForegroundColor Green

# Create logs directory
New-Item -ItemType Directory -Force -Path logs | Out-Null

# Run the app
Write-Host ""
Write-Host "🚀 Starting RetailStack POS Agent..." -ForegroundColor Green
Write-Host "   Press Ctrl+C to stop" -ForegroundColor Yellow
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

& $pythonCmd main.py
