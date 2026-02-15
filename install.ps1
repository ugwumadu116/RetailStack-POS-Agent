# RetailStack POS Agent - Windows Quick Install
# Run this in PowerShell or CMD:
# irm https://raw.githubusercontent.com/ugwumadu116/RetailStack-POS-Agent/main/install.ps1 | iex

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  RetailStack POS Agent - Quick Install" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Check Python
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✅ Python found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Python not found. Install from https://python.org" -ForegroundColor Red
    Write-Host "   Make sure to check 'Add Python to PATH'" -ForegroundColor Yellow
    exit 1
}

# Get script directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

# Install dependencies
Write-Host ""
Write-Host "📦 Installing dependencies..." -ForegroundColor Yellow
pip install -q pyserial requests python-dateutil 2>$null

Write-Host "✅ Dependencies installed" -ForegroundColor Green

# Create logs directory
New-Item -ItemType Directory -Force -Path logs | Out-Null

# Run the app
Write-Host ""
Write-Host "🚀 Starting RetailStack POS Agent..." -ForegroundColor Green
Write-Host "   Press Ctrl+C to stop" -ForegroundColor Yellow
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

python main.py
