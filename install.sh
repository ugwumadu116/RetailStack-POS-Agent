#!/bin/bash
# RetailStack POS Agent - One-line installer
# Run this command:
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

# Get current directory
SCRIPT_DIR="$(pwd)"

# Download and extract project
echo "📦 Downloading RetailStack POS Agent..."
TMP_DIR="/tmp/retailstack_$$"

curl -fsSL https://github.com/ugwumadu116/RetailStack-POS-Agent/archive/refs/heads/main.zip -o /tmp/retailstack.zip
unzip -q /tmp/retailstack.zip -d /tmp/
mv /tmp/RetailStack-POS-Agent-main/* "$SCRIPT_DIR/"
rm -rf /tmp/retailstack.zip /tmp/RetailStack-POS-Agent-main

cd "$SCRIPT_DIR"

# Install dependencies
echo "📦 Installing dependencies..."
$PYTHON_CMD -m pip install --user pyserial requests python-dateutil 2>/dev/null || \
$PYTHON_CMD -m pip install --break-system-packages pyserial requests python-dateutil 2>/dev/null || \
$PYTHON_CMD -m pip install pyserial requests python-dateutil 2>/dev/null

if [ $? -ne 0 ]; then
    echo "❌ Failed to install dependencies"
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
