# Stage 1: Build
# Use an Alpine version of the official Python 3.12 image as the base
FROM python:3.12-alpine3.20 as builder

# Install build dependencies temporarily and remove them after use
RUN mkdir /app \
    && pip install --upgrade pip \
    && python -m venv /venv \
    && /venv/bin/pip install --upgrade pip

WORKDIR /app
COPY requirements.txt .
RUN /venv/bin/pip install --no-cache-dir -r requirements.txt

# Stage 2: Runtime
FROM python:3.12-alpine3.20

# Install runtime dependencies (tzdata for timezone support, busybox-openrc for cron)
RUN apk add --no-cache \
        tzdata \
        busybox-openrc \
    && rm -rf /var/cache/apk/* \
    && mkdir -p /var/log /var/cache

# Set working directory
WORKDIR /app

# Copy virtual environment from the builder stage
COPY --from=builder /venv /venv

# Copy application files
COPY UpdateAdGuardDNSRewrites.py entrypoint.sh ./

# Make scripts executable
RUN chmod +x UpdateAdGuardDNSRewrites.py entrypoint.sh

# Add venv to PATH so cron can use python directly
ENV PATH="/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Required environment variables
ENV ADGUARD_USERNAME="" \
    ADGUARD_PASSWORD="" \
    LANCACHE_SERVER="" \
    ADGUARD_API="" \
    CRON_SCHEDULE="0 0 * * *"

# Optional environment variables
ENV ALL_SERVICES="false" \
    SERVICE_NAMES="" \
    LOG_LEVEL="INFO" \
    MAX_WORKERS="3" \
    BATCH_SIZE="100" \
    CACHE_FILE=""

# Health check - verify script runs without errors
HEALTHCHECK --interval=6h --timeout=30s --start-period=30s --retries=2 \
    CMD python /app/UpdateAdGuardDNSRewrites.py || exit 1

# Use the entrypoint script to start cron and keep the container running
ENTRYPOINT ["./entrypoint.sh"]