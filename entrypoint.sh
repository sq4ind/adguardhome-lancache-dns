#!/bin/sh

# Create empty /var/log/cron.log
touch /var/log/cron.log

# Start the cron service
crond

# Loop through the list of environment variables and write each one to /etc/environment if it's set
for var in ADGUARD_USERNAME ADGUARD_PASSWORD LANCACHE_SERVER ADGUARD_API ALL_SERVICES SERVICE_NAMES CRON_SCHEDULE; do
    value=$(eval echo \$$var)
    if [ ! -z "$value" ]; then
        echo "$var='$value'" >> /etc/environment
    fi
done

# Update the cron job setup to source environment variables
echo "$CRON_SCHEDULE /venv/bin/python /app/UpdateAdGuardDNSRewrites.py >> /var/log/cron.log 2>&1" | crontab -

# Tail the cron log to keep the container running
tail -f /var/log/cron.log
