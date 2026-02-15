#!/bin/bash
# RetailStack POS Agent - One-line installer
# Run this command on Mac/Linux:
# curl -fsSL https://raw.githubusercontent.com/ugwumadu116/RetailStack-POS-Agent/main/install.sh | bash

set -e

echo "=========================================="
echo "  RetailStack POS Agent - Quick Install"
echo "=========================================="

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python not found. Install from https://python.org"
    exit 1
fi

echo "✅ Python found: $(python3 --version)"

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Install dependencies
echo "📦 Installing dependencies..."
python3 -m pip install pyserial requests python-dateutil 2>/dev/null || python -m pip install pyserial requests python-dateutil

echo "✅ Dependencies installed"

# Create logs directory
mkdir -p logs

# Run the app
echo ""
echo "🚀 Starting RetailStack POS Agent..."
echo "   Press Ctrl+C to stop"
echo "=========================================="
python3 main.py
