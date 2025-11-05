#!/bin/sh

set -e

# Create log directory
mkdir -p /var/log
touch /var/log/cron.log

# Start the cron service
crond

# Export environment variables for cron
for var in \
    ADGUARD_USERNAME \
    ADGUARD_PASSWORD \
    LANCACHE_SERVER \
    ADGUARD_API \
    ALL_SERVICES \
    SERVICE_NAMES \
    CRON_SCHEDULE \
    LOG_LEVEL \
    MAX_WORKERS \
    BATCH_SIZE \
    CACHE_FILE; do
    value=$(eval echo \$$var)
    if [ -n "$value" ]; then
        echo "$var='$value'" >> /etc/environment
    fi
done

# Setup cron job with proper environment
echo "$CRON_SCHEDULE /venv/bin/python /app/UpdateAdGuardDNSRewrites.py >> /var/log/cron.log 2>&1" | crontab -

# Display initial message
echo "Cron service started with schedule: $CRON_SCHEDULE"
echo "Log file: /var/log/cron.log"
echo "Services: $([ "$ALL_SERVICES" = 'true' ] && echo 'ALL' || echo "$SERVICE_NAMES")"
echo ""
echo "Tailing cron logs (press Ctrl+C to stop):"

# Keep container running and tail logs
tail -f /var/log/cron.log