# =============================================================================
# DispatchMind v2.0 — Production Dockerfile
# Multi-stage: Build React frontend → Serve via FastAPI backend directly
# =============================================================================

# ---- Stage 1: Python Backend Base (used by docker-compose for dev) ----
FROM python:3.12-slim AS backend
WORKDIR /app

# Install gzip to decompress the dataset during build
RUN apt-get update && apt-get install -y --no-install-recommends \
    gzip \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ backend/
COPY src/ src/
COPY config/ config/
COPY scripts/ scripts/
COPY phantom_risk.py preprocess.py tipping_points.py ./
COPY ["jan to may police violation_anonymized791b166.csv.gz", "./"]
RUN gzip -d "jan to may police violation_anonymized791b166.csv.gz"
COPY data/external/ data/external/
COPY data/processed/ data/processed/

EXPOSE 8000
ENV PORT=8000
ENV PYTHONPATH=/app
ENV WORKERS=4

CMD ["sh", "-c", "gunicorn backend.api:app -k uvicorn.workers.UvicornWorker -w ${WORKERS} --bind 0.0.0.0:${PORT} --graceful-timeout 30 --timeout 120 --keep-alive 5"]


# ---- Stage 2: Build React Frontend ----
FROM node:20-slim AS frontend-builder
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ .
RUN npx vite build


# ---- Stage 3: Production runtime (Backend + Frontend Static Assets) ----
FROM backend AS production

# Copy built frontend static assets into the directory FastAPI expects
COPY --from=frontend-builder /app/dist /app/frontend/dist


