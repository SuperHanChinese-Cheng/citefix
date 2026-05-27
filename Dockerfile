# ---- Stage 1: Build frontend ----
FROM node:20-alpine AS frontend-build

WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci --ignore-scripts
COPY frontend/ ./
RUN npm run build

# ---- Stage 2: Python backend + serve frontend ----
FROM python:3.11-slim AS runtime

# Prevent Python from writing .pyc and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install system deps (none needed beyond slim defaults, but keep layer for future use)
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first (better layer caching)
COPY pyproject.toml ./
COPY src/ ./src/
RUN pip install --no-cache-dir .

# Copy built frontend assets from stage 1
COPY --from=frontend-build /app/frontend/dist /app/static

# Create non-root user
RUN groupadd --gid 1000 citefix \
    && useradd --uid 1000 --gid citefix --shell /bin/bash --create-home citefix \
    && chown -R citefix:citefix /app

USER citefix

# Railway injects PORT env var; default to 8000 for local use
ENV PORT=8000
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Use shell form so ${PORT} is expanded at runtime
CMD uvicorn citefix.api:app --host 0.0.0.0 --port ${PORT}
