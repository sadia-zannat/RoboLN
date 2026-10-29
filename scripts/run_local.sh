#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../backend"
python -m pip install -r requirements.txt
alembic upgrade head
python -m pytest -q
python -m uvicorn app.api:app --host 127.0.0.1 --port 8000 &
PID=$!
trap 'kill "$PID" 2>/dev/null || true' EXIT
cd ../frontend
# Requires actual npm registry, and an npm-generated package-lock.json.
if [ ! -f package-lock.json ]; then npm install; fi
npm ci
npm run lint
npm run typecheck
npm run build
npm run dev
