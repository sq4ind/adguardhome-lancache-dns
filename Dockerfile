# Stage 1: Build
# Use an Alpine version of the official Python 3.12 image as the base
FROM python:3.12-alpine as builder

# Install build dependencies temporarily and remove them after use
RUN mkdir /app \
    && pip install --upgrade pip \
    # Using --no-cache-dir and a virtual environment for minimal size
    && python -m venv /venv \
    # Ensure pip is upgraded in the virtual environment
    && /venv/bin/pip install --upgrade pip

WORKDIR /app
COPY requirements.txt .
RUN /venv/bin/pip install --no-cache-dir -r requirements.txt

# Stage 2: Runtime
FROM python:3.12-alpine

# Install runtime dependencies if needed, then remove cache to keep image small
RUN apk add --no-cache \
        tzdata busybox-openrc \
    && rm -rf /var/cache/apk/*

# Set working directory
WORKDIR /app

# Copy virtual environment from the builder stage
COPY --from=builder /venv /venv
COPY UpdateAdGuardDNSRewrites.py entrypoint.sh ./

# Make sure scripts are executable
RUN chmod +x UpdateAdGuardDNSRewrites.py entrypoint.sh

# Set environment variables for your application
ENV ADGUARD_USERNAME="" \
    ADGUARD_PASSWORD="" \
    LANCACHE_SERVER="" \
    ADGUARD_API="" \
    ALL_SERVICES="" \
    SERVICE_NAMES="" \
    CRON_SCHEDULE="0 0 * * *" \
    PATH="/venv/bin:$PATH"

# Use the entrypoint script to start cron and keep the container running
ENTRYPOINT ["./entrypoint.sh"]
