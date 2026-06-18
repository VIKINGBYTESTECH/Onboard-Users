#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$ROOT_DIR/backend"
if [ ! -x ".venv/bin/python" ]; then
  echo "Backend virtualenv is missing. Run ./scripts/install.sh first." >&2
  exit 1
fi
. .venv/bin/activate
python -m compileall app

cd "$ROOT_DIR/frontend"
npm run build
