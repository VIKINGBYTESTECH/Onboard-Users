#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [ ! -f "$ROOT_DIR/backend/.env" ]; then
  cp "$ROOT_DIR/backend/.env.example" "$ROOT_DIR/backend/.env"
  echo "Created backend/.env"
else
  echo "backend/.env already exists"
fi

if [ ! -f "$ROOT_DIR/frontend/.env.local" ]; then
  cp "$ROOT_DIR/frontend/.env.example" "$ROOT_DIR/frontend/.env.local"
  echo "Created frontend/.env.local"
else
  echo "frontend/.env.local already exists"
fi

if [ ! -f "$ROOT_DIR/backend/app/data/options.json" ]; then
  cp "$ROOT_DIR/backend/app/data/options.example.json" "$ROOT_DIR/backend/app/data/options.json"
  echo "Created backend/app/data/options.json"
else
  echo "backend/app/data/options.json already exists"
fi

echo
echo "Next:"
echo "1. Edit backend/.env with Entra tenant/client values."
echo "2. Run backend and frontend as described in README.md."
