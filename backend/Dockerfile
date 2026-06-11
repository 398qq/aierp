# AIERP backend Dockerfile (Stage 6 Day 4)
# Multi-stage: builder (deps) → runtime (minimal)
# Runtime: python:3.12-slim, no build tools, ~150MB image

# ============ Stage 1: deps builder ============
FROM python:3.12-slim AS builder

WORKDIR /app

# Install build deps (gcc for cffi, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Layer cache: only re-install when requirements change
COPY requirements.txt requirements-perf.txt ./
RUN pip wheel --no-cache-dir --wheel-dir /wheels \
    -r requirements.txt \
    -r requirements-perf.txt

# ============ Stage 2: runtime ============
FROM python:3.12-slim AS runtime

# Create non-root user
RUN groupadd -r aierp && useradd -r -g aierp aierp

WORKDIR /app

# Install runtime deps + wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir --no-index --find-links=/wheels \
    -r requirements.txt \
    -r requirements-perf.txt \
    && rm -rf /wheels

# Copy app
COPY . /app

# Permissions
RUN chown -R aierp:aierp /app
USER aierp

# Health check
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health/live')" || exit 1

EXPOSE 8080

# Production server: uvicorn with 2 workers
# Use shell form to allow env var expansion at runtime
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "2", "--proxy-headers"]
