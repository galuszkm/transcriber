#!/usr/bin/env bash
# Build the Transcriber UI and output to src/transcriber/server/static
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "==> Installing dependencies…"
npm install

echo "==> Running tests…"
npm run test

echo "==> Building UI…"
npm run build

echo "==> Fixing trailing whitespace in built files…"
STATIC_DIR="$SCRIPT_DIR/../src/transcriber/server/static"
find "$STATIC_DIR" -type f \( -name '*.js' -o -name '*.css' -o -name '*.html' \) \
  -exec sed -i 's/[[:space:]]*$//' {} +

echo "==> Done. Static files written to ../src/transcriber/server/static/"
