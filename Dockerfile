# Stage 1: Build
# Use a slim version of the official Python 3.12 image as the base
FROM python:3.12-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    cron \
    gcc \
    libc6-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy the requirements.txt file into the container
COPY requirements.txt .

# Install the Python dependencies from requirements.txt using a virtual environment
RUN python -m venv /venv \
    && /venv/bin/pip install --upgrade pip \
    && /venv/bin/pip install --no-cache-dir -r requirements.txt

# Stage 2: Runtime
FROM python:3.12-slim

# Copy virtual environment from the builder stage
COPY --from=builder /venv /venv

# Install cron without recommended packages to keep the image small
RUN apt-get update && apt-get install -y --no-install-recommends cron \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Set working directory
WORKDIR /app

# Copy the Python script and entrypoint script into the container from the builder stage
COPY UpdateAdGuardDNSRewrites.py entrypoint.sh ./

# Make sure scripts are executable
RUN chmod +x UpdateAdGuardDNSRewrites.py entrypoint.sh

# Set environment variables for your application
ENV ADGUARD_USERNAME="" \
    ADGUARD_PASSWORD="" \
    LANCACHE_SERVER="" \
    ADGUARD_API="" \
    # Either ALL_SERVICES or SERVICE_NAMES should be provided, not both.
    ALL_SERVICES="" \
    SERVICE_NAMES="" \
    CRON_SCHEDULE="0 0 * * *" \
    PATH="/venv/bin:$PATH"

# Use the entrypoint script to start cron and keep the container running
ENTRYPOINT ["./entrypoint.sh"]

