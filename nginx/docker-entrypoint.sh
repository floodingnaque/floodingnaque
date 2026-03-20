#!/bin/sh
# Nginx entrypoint with periodic reload for certificate renewal.
# Certbot (separate container) renews certs every 12h.
# This script reloads nginx every 6h to pick up renewed certificates.

set -e

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
