#!/usr/bin/env bash
# ============================================================================
# Render Web Service entrypoint — DispatchMind
#
# Build step (run by Render before this script):
#   pip install -r requirements.txt
#   cd frontend && npm install && npm run build
#
# This script starts the FastAPI backend with uvicorn.
# The frontend (built above) is served as static files by the backend.
# ============================================================================
set -e

APP_MODULE="backend.api:app"
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"
WORKERS="${WORKERS:-2}"
LOG_LEVEL="${LOG_LEVEL:-info}"

# Decompress dataset CSV if compressed archive exists and raw file is missing
CSV_FILE="jan to may police violation_anonymized791b166.csv"
CSV_GZ="${CSV_FILE}.gz"
if [ ! -f "$CSV_FILE" ] && [ -f "$CSV_GZ" ]; then
    echo "Decompressing $CSV_GZ -> $CSV_FILE ..."
    gzip -dk "$CSV_GZ"
fi

echo "Starting DispatchMind backend on $HOST:$PORT (workers=$WORKERS)"

exec uvicorn "$APP_MODULE" \
    --host "$HOST" \
    --port "$PORT" \
    --workers "$WORKERS" \
    --log-level "$LOG_LEVEL" \
    --proxy-headers \
    --forwarded-allow-ips '*'
