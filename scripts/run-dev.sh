#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
CERT_DIR="$ROOT_DIR/.certs"
BACKEND_PORT="${BACKEND_PORT:-8010}"
FRONTEND_PORT="${FRONTEND_PORT:-5174}"
USE_HTTPS="${HTTPS:-false}"

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
if [ "$USE_HTTPS" = "true" ]; then
  "$ROOT_DIR/scripts/create-dev-cert.sh"
  uvicorn app.main:app \
    --host 0.0.0.0 \
    --port "$BACKEND_PORT" \
    --ssl-keyfile "$CERT_DIR/localhost-key.pem" \
    --ssl-certfile "$CERT_DIR/localhost-cert.pem" &
else
  uvicorn app.main:app --host 0.0.0.0 --port "$BACKEND_PORT" &
fi
BACKEND_PID=$!

cd "$FRONTEND_DIR"
if [ "$USE_HTTPS" = "true" ]; then
  echo "Open https://localhost:$FRONTEND_PORT"
else
  echo "Open http://localhost:$FRONTEND_PORT"
fi
npm run dev -- --host 0.0.0.0 --port "$FRONTEND_PORT"
