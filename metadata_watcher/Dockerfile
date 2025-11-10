# Dockerfile for Metadata Watcher Service
# Multi-stage build for optimal image size

FROM python:3.11-slim as base

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    procps \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY metadata_watcher/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Production stage
FROM base as production

# Create non-root user
RUN useradd -m -u 1000 -s /bin/bash radiouser

# Copy application code
COPY metadata_watcher/ /app/metadata_watcher/
COPY track_mapper/ /app/track_mapper/
WORKDIR /app/metadata_watcher

# Create directories for logs, loops, and stream control
RUN mkdir -p /var/log/radio /srv/loops /var/run/stream \
    && chown -R radiouser:radiouser /var/log/radio /srv/loops /app /var/run/stream

# Remain root for entrypoint ownership fix, then drop to radiouser
COPY metadata_watcher/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Set working directory back to /app
WORKDIR /app

# Set Python path to include /app so track_mapper can be imported
ENV PYTHONPATH=/app:$PYTHONPATH

# Expose service port
EXPOSE 9000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:9000/health || exit 1

ENTRYPOINT ["/entrypoint.sh"]


