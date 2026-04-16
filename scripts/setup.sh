#!/usr/bin/env bash
# Crypto AI Agent — PDF report setup
# Run once: bash scripts/setup.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FONTS_DIR="$SCRIPT_DIR/fonts"

echo ">>> Installing Python dependencies..."
pip3 install -r "$SCRIPT_DIR/requirements.txt"

echo ">>> Downloading Vazirmatn font..."
mkdir -p "$FONTS_DIR"

curl -fsSL \
  "https://github.com/rastikerdar/vazirmatn/raw/v33.003/fonts/ttf/Vazirmatn-Regular.ttf" \
  -o "$FONTS_DIR/Vazirmatn-Regular.ttf"

curl -fsSL \
  "https://github.com/rastikerdar/vazirmatn/raw/v33.003/fonts/ttf/Vazirmatn-Bold.ttf" \
  -o "$FONTS_DIR/Vazirmatn-Bold.ttf"

echo ">>> Done. Font files:"
ls -lh "$FONTS_DIR"
echo ""
echo "Setup complete. You can now run /persianfeed."
