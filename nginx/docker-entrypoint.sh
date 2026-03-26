#!/bin/sh
# Nginx entrypoint with periodic reload for certificate renewal.
# Certbot (separate container) renews certs every 12h.
# This script reloads nginx every 6h to pick up renewed certificates.

set -e

# Template canary traffic percentage (default: 5%)
export CANARY_TRAFFIC_PCT="${CANARY_TRAFFIC_PCT:-5}"

# Substitute environment variables in the config template
if [ -f /etc/nginx/conf.d/default.conf ]; then
  envsubst '${CANARY_TRAFFIC_PCT}' < /etc/nginx/conf.d/default.conf > /etc/nginx/conf.d/default.conf.tmp
  mv /etc/nginx/conf.d/default.conf.tmp /etc/nginx/conf.d/default.conf
fi

# Start the reload loop in background
(
  while true; do
    sleep 6h
    echo "$(date): Reloading nginx configuration..."
    nginx -s reload 2>/dev/null || true
  done
) &

# Start nginx in foreground (PID 1)
exec nginx -g "daemon off;"
