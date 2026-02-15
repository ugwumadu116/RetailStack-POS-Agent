#!/bin/bash
# RetailStack POS Agent - One-line installer
# Run this command on Mac/Linux:
# curl -fsSL https://raw.githubusercontent.com/ugwumadu116/RetailStack-POS-Agent/main/install.sh | bash

echo "=========================================="
echo "  RetailStack POS Agent - Quick Install"
echo "=========================================="

# Find Python
PYTHON_CMD=""
for cmd in python3 python3.13 python3.12 python3.11 python; do
    if command -v $cmd &> /dev/null; then
        PYTHON_CMD=$cmd
        break
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    echo "❌ Python not found. Install from https://python.org"
    exit 1
fi

echo "✅ Python found: $($PYTHON_CMD --version)"

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Install dependencies (--user works on externally-managed Python)
echo "📦 Installing dependencies..."
$PYTHON_CMD -m pip install --user pyserial requests python-dateutil 2>/dev/null || \
$PYTHON_CMD -m pip install --break-system-packages pyserial requests python-dateutil 2>/dev/null || \
$PYTHON_CMD -m pip install pyserial requests python-dateutil

if [ $? -ne 0 ]; then
    echo "❌ Failed to install dependencies"
    echo "Try: $PYTHON_CMD -m pip install --user pyserial requests python-dateutil"
    exit 1
fi

echo "✅ Dependencies installed"

# Create logs directory
mkdir -p logs

# Run the app
echo ""
echo "🚀 Starting RetailStack POS Agent..."
echo "   Logs: $SCRIPT_DIR/logs/retailstack.log"
echo "   Press Ctrl+C to stop"
echo "=========================================="
$PYTHON_CMD main.py
