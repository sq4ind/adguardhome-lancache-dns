#!/bin/sh

# Healthcheck script for AdGuardHome LanCache DNS Synchronizer
# Validates configuration and verifies script can run

set -e

# Ensure venv is in PATH
export PATH="/venv/bin:$PATH"

# Source environment if available
if [ -f /etc/environment ]; then
    set -a
    . /etc/environment
    set +a
fi

# Validate required environment variables
if [ -z "$ADGUARD_USERNAME" ]; then
    echo "ERROR: ADGUARD_USERNAME not set" >&2
    exit 1
fi

if [ -z "$ADGUARD_PASSWORD" ]; then
    echo "ERROR: ADGUARD_PASSWORD not set" >&2
    exit 1
fi

if [ -z "$LANCACHE_SERVER" ]; then
    echo "ERROR: LANCACHE_SERVER not set" >&2
    exit 1
fi

if [ -z "$ADGUARD_API" ]; then
    echo "ERROR: ADGUARD_API not set" >&2
    exit 1
fi

if [ -z "$ALL_SERVICES" ] && [ -z "$SERVICE_NAMES" ]; then
    echo "ERROR: Either ALL_SERVICES=true or SERVICE_NAMES must be specified" >&2
    exit 1
fi

# Verify Python and venv
if ! command -v python >/dev/null 2>&1; then
    echo "ERROR: python not found in PATH" >&2
    exit 1
fi

# Verify script exists
if [ ! -f /app/UpdateAdGuardDNSRewrites.py ]; then
    echo "ERROR: UpdateAdGuardDNSRewrites.py not found" >&2
    exit 1
fi

# Try to import Python modules with full path
if ! /venv/bin/python -c "import requests; import urllib3" 2>/dev/null; then
    echo "ERROR: Required Python modules not installed (requests or urllib3)" >&2
    exit 1
fi

# Verify connectivity to AdGuard API (basic check)
RESPONSE=$(/venv/bin/python -c "
import requests
from requests.auth import HTTPBasicAuth
try:
    session = requests.Session()
    session.auth = HTTPBasicAuth('$ADGUARD_USERNAME', '$ADGUARD_PASSWORD')
    resp = session.get('$ADGUARD_API/control/status', timeout=5)
    print(resp.status_code)
except Exception as e:
    print('ERROR')
" 2>/dev/null || echo "ERROR")

if [ "$RESPONSE" = "ERROR" ]; then
    echo "WARNING: Cannot verify AdGuard API connectivity (may be temporary)" >&2
    # Don't fail on connectivity issues - network might be transitioning
    exit 0
fi

if [ "$RESPONSE" != "200" ]; then
    echo "ERROR: AdGuard API returned status $RESPONSE (expected 200)" >&2
    exit 1
fi

# All checks passed
echo "OK: Configuration validation successful"
exit 0