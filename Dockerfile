# TD Lead Engine - Production Dockerfile
# Multi-stage build for smaller image size

# Stage 1: Build stage
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY pyproject.toml .
COPY src/ src/

# Install the package
RUN pip install --no-cache-dir -e . && \
    pip install --no-cache-dir gunicorn

# Stage 2: Production stage
FROM python:3.11-slim as production

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash appuser

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=appuser:appuser . .

# Create data directories
RUN mkdir -p /app/data /app/logs /home/appuser/.td-lead-engine && \
    chown -R appuser:appuser /app /home/appuser/.td-lead-engine

# Switch to non-root user
USER appuser

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TD_ENGINE_ENV=production \
    TD_ENGINE_DATA_DIR=/app/data \
    TD_ENGINE_LOG_DIR=/app/logs

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/api/health || exit 1

# Expose port
EXPOSE 5000

# Default command - run the dashboard API
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--threads", "4", "apps.dashboard.server:app"]
