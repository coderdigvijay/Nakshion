#!/usr/bin/env bash
# Render start command: migrate, then serve. Run from the backend/ directory.
#
#   alembic upgrade head   uses MIGRATION_DATABASE_URL (Neon DIRECT endpoint) under an advisory lock
#                          (alembic/env.py), so overlapping deploy starts cannot race. A failed
#                          migration aborts boot: the previous instance keeps serving (fail-safe).
#   --no-proxy-headers     the client IP comes from app/core/clientip.py (TRUSTED_PROXY_HOPS=1);
#                          uvicorn's own proxy handling trusts a forgeable X-Forwarded-For (BUG-007).
set -euo pipefail
alembic upgrade head
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-10000}" --workers 1 --no-proxy-headers --no-server-header
