#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
vispect_env_args=()
if [[ -f .env ]]; then vispect_env_args=(--env-file .env); fi
uv run --project backend "${vispect_env_args[@]}" --no-sync pytest backend/tests -q
VISPECT_MANAGEMENT=1 uv run --project backend "${vispect_env_args[@]}" --no-sync python backend/manage.py makemigrations --check --dry-run
uv run --project backend "${vispect_env_args[@]}" --no-sync python backend/manage.py check
pnpm --dir frontend test --run
pnpm --dir frontend typecheck
pnpm --dir frontend build
pnpm --dir frontend exec playwright test
