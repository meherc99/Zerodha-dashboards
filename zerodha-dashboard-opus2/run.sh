#!/bin/bash
# ============================================
#  Zerodha Portfolio Dashboard — Setup & Run
# ============================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Zerodha Portfolio Dashboard"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check Python
if ! command -v python3 &>/dev/null; then
    echo "❌ Python 3 not found. Please install Python 3.9+."
    exit 1
fi

PYTHON=$(command -v python3)
echo "✓ Python: $($PYTHON --version)"

# Create virtual environment if needed
if [ ! -d "venv" ]; then
    echo "→ Creating virtual environment..."
    $PYTHON -m venv venv
fi

# Activate
source venv/bin/activate
echo "✓ Virtual environment activated"

# Install dependencies
echo "→ Installing dependencies..."
pip install -q -r requirements.txt

# Create data directory
mkdir -p data

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Configuration"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "To use with your Zerodha account, set these"
echo "environment variables before running:"
echo ""
echo "  export KITE_API_KEY='your_api_key'"
echo "  export KITE_API_SECRET='your_api_secret'"
echo "  export KITE_ACCESS_TOKEN='your_access_token'"
echo ""
echo "Or edit config.py directly."
echo ""
echo "Without credentials, demo data will be shown."
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Starting Dashboard..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🌐 Open http://localhost:5050 in your browser"
echo ""

python app.py
