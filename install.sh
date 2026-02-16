#!/bin/bash
# Quick installation script for hit (mo-git)

set -e

echo "Installing hit (mo-git) in development mode..."
echo ""

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed"
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "Found Python $PYTHON_VERSION"

# Install in editable mode
echo "Running: pip install -e ."
pip3 install -e .

echo ""
echo "✓ Installation complete!"
echo ""
echo "The 'hit' command is now available."
echo "Try: hit --help"

