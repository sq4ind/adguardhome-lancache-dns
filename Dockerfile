# Use the official Python 3.12 image as the base
FROM python:3.12

# Install cron and any other dependencies you might need
RUN apt-get update && apt-get install -y cron && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy the requirements.txt file into the container
COPY requirements.txt .

# Install the Python dependencies from requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the Python script into the container
COPY UpdateAdGuardDNSRewrites.py .

# Add a script to launch the cron job and the python script with env vars
COPY entrypoint.sh .

# Make sure scripts are executable
RUN chmod +x UpdateAdGuardDNSRewrites.py entrypoint.sh

# Set environment variables for your application
ENV ADGUARD_USERNAME=""
ENV ADGUARD_PASSWORD=""
ENV LANCACHE_SERVER=""
ENV ADGUARD_API=""
# Either ALL_SERVICES or SERVICE_NAMES should be provided, not both.
ENV ALL_SERVICES=""
ENV SERVICE_NAMES=""

# Set a default cron schedule (e.g., once a day at midnight)
# This can be overridden by passing a different value at runtime
ENV CRON_SCHEDULE="0 0 * * *"

# Use the entrypoint script to start cron and keep the container running
ENTRYPOINT ["./entrypoint.sh"]
