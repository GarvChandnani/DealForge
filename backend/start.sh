#!/usr/bin/env bash
# =============================================================================
# DealForge Backend — Production Startup Script
#
# Executed by Render as the `startCommand` for the backend web service.
#
# Steps:
#   1. Navigate to the database directory and run Alembic migrations.
#   2. Start uvicorn from the backend/ directory with production settings.
#
# Environment variables are provided by Render (from render.yaml / dashboard).
# =============================================================================

set -euo pipefail

# Repo root is the working directory (render.yaml sets rootDir: .)
REPO_ROOT="$(pwd)"
export REPO_ROOT

echo "==> [DealForge] Repo root: $REPO_ROOT"

# ── 1. Database migrations ───────────────────────────────────────────────────
echo "==> [DealForge] Running Alembic migrations..."

cd "$REPO_ROOT/database"
timeout 90 alembic upgrade head || { echo "==> [DealForge] Alembic failed or timed out"; exit 1; }
cd "$REPO_ROOT"

echo "==> [DealForge] Migrations complete."

# ── 2. Start uvicorn ─────────────────────────────────────────────────────────
echo "==> [DealForge] Launching uvicorn..."

# Render exposes PORT env var; default to 8000
PORT="${PORT:-8000}"

# Run uvicorn from backend/ so `main:app` resolves correctly.
# main.py itself adds the repo root to sys.path so shared/ imports work.
cd "$REPO_ROOT/backend"

exec uvicorn main:app \
  --host 0.0.0.0 \
  --port "$PORT" \
  --workers 2 \
  --log-level info \
  --no-access-log
