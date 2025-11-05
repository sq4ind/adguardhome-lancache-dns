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

# Run initial healthcheck/validation
echo "Running initial configuration validation..."
/app/healthcheck.sh
if [ $? -eq 0 ]; then
    echo "✓ Configuration validation passed"
else
    echo "✗ Configuration validation failed"
    exit 1
fi

# Setup cron job with health check - append healthcheck to cron job
echo "$CRON_SCHEDULE /app/healthcheck.sh && /venv/bin/python /app/UpdateAdGuardDNSRewrites.py >> /var/log/cron.log 2>&1" | crontab -

# Display startup information
echo ""
echo "================================================"
echo "AdGuardHome LanCache DNS Synchronizer"
echo "================================================"
echo "Cron schedule: $CRON_SCHEDULE"
echo "Services: $([ "$ALL_SERVICES" = 'true' ] && echo 'ALL' || echo "$SERVICE_NAMES")"
echo "Log file: /var/log/cron.log"
echo "Configuration validation: PASSED"
echo "================================================"
echo ""
echo "Tailing cron logs (press Ctrl+C to stop):"
echo ""

# Keep container running and tail logs
tail -f /var/log/cron.log