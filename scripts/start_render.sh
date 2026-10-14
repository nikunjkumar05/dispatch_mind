#!/usr/bin/env bash
# ============================================================================
# Render entrypoint — starts the full FastAPI app
# ============================================================================
set -e

# Decompress dataset CSV if not already present
CSV_FILE="jan to may police violation_anonymized791b166.csv"
CSV_GZ="${CSV_FILE}.gz"
if [ ! -f "$CSV_FILE" ] && [ -f "$CSV_GZ" ]; then
    echo "Decompressing $CSV_GZ -> $CSV_FILE ..."
    gzip -dk "$CSV_GZ"
fi

echo "Starting DispatchMind FastAPI server..."

PORT="${PORT:-10000}"

# Low-memory tuning for Render free tier (512 MB):
# - single worker (each worker duplicates pandas/sklearn/xgboost in RAM)
# - single BLAS/OpenMP thread per worker (numpy/sklearn default to many threads)
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export WEB_CONCURRENCY=1

exec gunicorn backend.api:app \
    --worker-class uvicorn.workers.UvicornWorker \
    --workers 1 \
    --threads 2 \
    --bind "0.0.0.0:${PORT}" \
    --timeout 120 \
    --graceful-timeout 30 \
    --max-requests 500 \
    --max-requests-jitter 50 \
    --log-level info
