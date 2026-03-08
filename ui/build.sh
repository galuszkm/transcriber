#!/usr/bin/env bash
# Build the Transcriber UI and output to src/transcriber/server/static
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "==> Installing dependencies…"
npm ci --prefer-offline 2>/dev/null || npm install

echo "==> Running tests…"
npm run test

echo "==> Building UI…"
npm run build

echo "==> Done. Static files written to ../src/transcriber/server/static/"
