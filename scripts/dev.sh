#!/usr/bin/env bash
# One-command local dev bring-up: Postgres (Docker) + backend (uvicorn --reload) + frontend
# (next dev), all three log-tailed in one terminal, Ctrl+C stops backend/frontend cleanly (db
# is left running -- it's the one piece worth keeping up between sessions, same as the README's
# manual "Local setup" steps already treat it).
#
# This is exactly the three manual steps in the root README's "Local setup" section, run
# together -- nothing here does anything those steps don't already say to do by hand.
#
# Usage: ./scripts/dev.sh
# Requires: backend/.venv already created (`cd backend && python3.12 -m venv .venv && .venv/bin/pip
# install -e ".[dev]"`) and frontend/node_modules already installed (`cd frontend && npm install`)
# -- this script starts things, it doesn't set up the environment from scratch.

set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
ROOT_DIR="$PWD"

if [ ! -x "$ROOT_DIR/backend/.venv/bin/uvicorn" ]; then
  echo "backend/.venv not found -- run: cd backend && python3.12 -m venv .venv && .venv/bin/pip install -e \".[dev]\"" >&2
  exit 1
fi
if [ ! -d "$ROOT_DIR/frontend/node_modules" ]; then
  echo "frontend/node_modules not found -- run: cd frontend && npm install" >&2
  exit 1
fi

echo "==> Starting Postgres (docker compose up -d db)"
docker compose up -d db

BACKEND_PID=""
FRONTEND_PID=""
cleanup() {
  echo ""
  echo "==> Stopping backend/frontend (db left running -- 'docker compose down' to stop it too)"
  [ -n "$BACKEND_PID" ] && kill "$BACKEND_PID" 2>/dev/null || true
  [ -n "$FRONTEND_PID" ] && kill "$FRONTEND_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "==> Starting backend (http://localhost:8000, /docs for the API browser)"
(cd "$ROOT_DIR/backend" && exec .venv/bin/uvicorn app.main:app --reload --port 8000) &
BACKEND_PID=$!

echo "==> Starting frontend (http://localhost:3000)"
(cd "$ROOT_DIR/frontend" && exec npm run dev) &
FRONTEND_PID=$!

echo ""
echo "Both running -- Ctrl+C to stop."
wait "$BACKEND_PID" "$FRONTEND_PID"
