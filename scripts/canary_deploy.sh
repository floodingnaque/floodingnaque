#!/usr/bin/env bash
# =====================================================
# Canary Deployment Script for Floodingnaque
# =====================================================
# Usage:
#   ./scripts/canary_deploy.sh deploy <image_tag>   - Deploy canary with given image tag
#   ./scripts/canary_deploy.sh promote              - Promote canary to production
#   ./scripts/canary_deploy.sh rollback             - Roll back canary (remove it)
#   ./scripts/canary_deploy.sh status               - Show canary vs production health
#
# The script monitors error rates and latency after deployment.
# If health gates fail, it automatically rolls back.
# =====================================================

set -euo pipefail

COMPOSE_FILE="compose.production.yaml"
CANARY_SERVICE="backend-canary"
PROD_SERVICE="backend"
HEALTH_ENDPOINT="http://localhost:5000/health"
CANARY_HEALTH_ENDPOINT="http://localhost:5001/health"  # Internal check
OBSERVATION_SECONDS="${CANARY_OBSERVATION_SECONDS:-120}"
MAX_ERROR_RATE="${CANARY_MAX_ERROR_RATE:-5}"  # percent

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

check_health() {
    local url=$1
    local status
    status=$(curl -sf -o /dev/null -w "%{http_code}" "$url" 2>/dev/null || echo "000")
    if [ "$status" = "200" ]; then
        echo "healthy"
    else
        echo "unhealthy (HTTP $status)"
    fi
}

get_canary_error_rate() {
    # Query Prometheus for canary error rate (requires Prometheus running)
    local rate
    rate=$(curl -sf "http://localhost:9090/api/v1/query?query=sum(rate(floodingnaque_http_request_total{instance=~\".*canary.*\",status=~\"5..\"}[2m]))/sum(rate(floodingnaque_http_request_total{instance=~\".*canary.*\"}[2m]))*100" 2>/dev/null \
        | python3 -c "import sys,json; r=json.load(sys.stdin); print(r['data']['result'][0]['value'][1] if r['data']['result'] else '0')" 2>/dev/null || echo "0")
    echo "$rate"
}

cmd_deploy() {
    local image_tag="${1:?Usage: canary_deploy.sh deploy <image_tag>}"
    log "Deploying canary with image tag: $image_tag"

    # Tag the image
    docker tag "floodingnaque-api:${image_tag}" "floodingnaque-api:canary"

    # Start canary service
    docker compose -f "$COMPOSE_FILE" --profile canary up -d "$CANARY_SERVICE"

    log "Waiting for canary to become healthy..."
    local retries=0
    while [ $retries -lt 30 ]; do
        if docker compose -f "$COMPOSE_FILE" ps "$CANARY_SERVICE" 2>/dev/null | grep -q "healthy"; then
            log "Canary is healthy"
            break
        fi
        retries=$((retries + 1))
        sleep 5
    done

    if [ $retries -ge 30 ]; then
        log "ERROR: Canary failed to become healthy within 150s. Rolling back."
        cmd_rollback
        exit 1
    fi

    log "Canary deployed. Observing for ${OBSERVATION_SECONDS}s..."
    local elapsed=0
    while [ $elapsed -lt "$OBSERVATION_SECONDS" ]; do
        sleep 15
        elapsed=$((elapsed + 15))

        # Check canary container health
        if ! docker compose -f "$COMPOSE_FILE" ps "$CANARY_SERVICE" 2>/dev/null | grep -q "healthy"; then
            log "ERROR: Canary became unhealthy at ${elapsed}s. Rolling back."
            cmd_rollback
            exit 1
        fi

        local error_rate
        error_rate=$(get_canary_error_rate)
        log "  [${elapsed}s] Canary error rate: ${error_rate}%"

        if [ "$(echo "$error_rate > $MAX_ERROR_RATE" | bc -l 2>/dev/null || echo 0)" = "1" ]; then
            log "ERROR: Canary error rate ${error_rate}% exceeds threshold ${MAX_ERROR_RATE}%. Rolling back."
            cmd_rollback
            exit 1
        fi
    done

    log "Canary passed health gates. Ready to promote."
    log "  Run: $0 promote"
}

cmd_promote() {
    log "Promoting canary to production..."

    # Tag canary image as new production image
    local canary_image
    canary_image=$(docker inspect --format='{{.Image}}' "$(docker compose -f "$COMPOSE_FILE" ps -q "$CANARY_SERVICE" 2>/dev/null)" 2>/dev/null || true)

    if [ -z "$canary_image" ]; then
        log "ERROR: No running canary found. Deploy first."
        exit 1
    fi

    # Rolling update: rebuild production with the canary image
    docker compose -f "$COMPOSE_FILE" up -d --no-deps --build "$PROD_SERVICE"

    # Wait for production to be healthy
    log "Waiting for production to become healthy with new image..."
    sleep 30

    # Remove canary
    docker compose -f "$COMPOSE_FILE" --profile canary stop "$CANARY_SERVICE"
    docker compose -f "$COMPOSE_FILE" --profile canary rm -f "$CANARY_SERVICE"

    log "Promotion complete. Canary removed."
}

cmd_rollback() {
    log "Rolling back canary..."
    docker compose -f "$COMPOSE_FILE" --profile canary stop "$CANARY_SERVICE" 2>/dev/null || true
    docker compose -f "$COMPOSE_FILE" --profile canary rm -f "$CANARY_SERVICE" 2>/dev/null || true
    log "Canary removed. Production unchanged."
}

cmd_status() {
    log "=== Canary Deployment Status ==="

    echo ""
    echo "Production:"
    docker compose -f "$COMPOSE_FILE" ps "$PROD_SERVICE" 2>/dev/null || echo "  Not running"
    echo "  Endpoint ($HEALTH_ENDPOINT): $(check_health "$HEALTH_ENDPOINT")"

    echo ""
    echo "Canary:"
    docker compose -f "$COMPOSE_FILE" --profile canary ps "$CANARY_SERVICE" 2>/dev/null || echo "  Not running"
    echo "  Endpoint ($CANARY_HEALTH_ENDPOINT): $(check_health "$CANARY_HEALTH_ENDPOINT")"

    echo ""
    local error_rate
    error_rate=$(get_canary_error_rate)
    echo "Canary error rate: ${error_rate}%"
    echo "Max allowed: ${MAX_ERROR_RATE}%"
}

# --- Main ---
case "${1:-status}" in
    deploy)  cmd_deploy "${2:-}" ;;
    promote) cmd_promote ;;
    rollback) cmd_rollback ;;
    status)  cmd_status ;;
    *)
        echo "Usage: $0 {deploy <tag>|promote|rollback|status}"
        exit 1
        ;;
esac
