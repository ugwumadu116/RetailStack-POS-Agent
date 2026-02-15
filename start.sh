#!/bin/bash
# RetailStack POS Agent Launcher

echo "🚀 Starting RetailStack POS Agent..."

# Find Python
PYTHON_CMD=""
for cmd in python3 python3.13 python3.12 python python3.11; do
    if command -v $cmd &> /dev/null; then
        PYTHON_CMD=$cmd
        break
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    echo "❌ Python not found"
    exit 1
fi

cd "$(dirname "$0")"
$PYTHON_CMD main.py
