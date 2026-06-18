#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

if [ ! -x "$BACKEND_DIR/.venv/bin/python" ]; then
  echo "Backend virtualenv is missing. Run ./scripts/install.sh first." >&2
  exit 1
fi

cleanup() {
  if [ -n "${BACKEND_PID:-}" ]; then
    kill "$BACKEND_PID" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT INT TERM

cd "$BACKEND_DIR"
. .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port "${BACKEND_PORT:-8010}" &
BACKEND_PID=$!

cd "$FRONTEND_DIR"
npm run dev -- --host 0.0.0.0 --port "${FRONTEND_PORT:-5174}"
