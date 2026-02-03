# =====================================================
# FLOODINGNAQUE - PgBouncer Connection Pooler
# =====================================================
# Lightweight connection pooler for PostgreSQL
# Optimized for production deployments
# =====================================================

FROM alpine:3.19

# Labels for container metadata
LABEL maintainer="Floodingnaque Team" \
      description="PgBouncer connection pooler for Floodingnaque" \
      version="1.21.0"

# Install PgBouncer and dependencies in a single layer
RUN apk add --no-cache \
        ca-certificates \
        gettext \
        pgbouncer \
        postgresql-client

# Create directories and non-root user
RUN mkdir -p /etc/pgbouncer /var/log/pgbouncer /var/run/pgbouncer && \
    addgroup -S pgbouncer && \
    adduser -S pgbouncer -G pgbouncer && \
    chown -R pgbouncer:pgbouncer /etc/pgbouncer /var/log/pgbouncer /var/run/pgbouncer

# Copy configuration files
COPY --chown=pgbouncer:pgbouncer pgbouncer.ini /etc/pgbouncer/pgbouncer.ini.template
COPY --chmod=755 entrypoint.sh /entrypoint.sh

# Switch to non-root user
USER pgbouncer

# Expose PgBouncer port
EXPOSE 6432

# Health check using pg_isready
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD pg_isready -h localhost -p 6432 || exit 1

# Run PgBouncer
ENTRYPOINT ["/entrypoint.sh"]
CMD ["pgbouncer", "/etc/pgbouncer/pgbouncer.ini"]
