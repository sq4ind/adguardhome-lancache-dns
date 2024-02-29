#!/bin/bash

# Create empty /var/log/cron.log
touch /var/log/cron.log

# Start the cron service
service cron start

# Declare which environmental variables to write in the /etc/environment
declare -a env_vars=("ADGUARD_USERNAME" "ADGUARD_PASSWORD" "LANCACHE_SERVER" "ADGUARD_API" "ALL_SERVICES" "SERVICE_NAMES" "CRON_SCHEDULE")

# Loop through the list and write each one to /etc/environment if it's set
for var in "${env_vars[@]}"; do
    if [[ -v $var ]]; then
        echo "$var='${!var}'" >> /etc/environment
    fi
done

# Update the cron job setup to source environment variables
echo "$CRON_SCHEDULE /venv/bin/python /app/UpdateAdGuardDNSRewrites.py >> /var/log/cron.log 2>&1" | crontab -

# Tail the cron log to keep the container running
tail -f /var/log/cron.log
