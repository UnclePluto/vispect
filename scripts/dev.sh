#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 scripts/init-env.py
docker compose up -d db
uv sync --project backend --frozen
pnpm --dir frontend install --frozen-lockfile
VISPECT_MANAGEMENT=1 uv run --project backend --env-file .env --no-sync python backend/manage.py migrate --database migration --noinput
uv run --project backend --env-file .env --no-sync python backend/manage.py seed_demo
uv run --project backend --env-file .env --no-sync python backend/manage.py runserver 127.0.0.1:8000 --noreload &
vispect_backend_pid=$!
trap 'kill "$vispect_backend_pid" 2>/dev/null || true' EXIT INT TERM
pnpm --dir frontend dev
