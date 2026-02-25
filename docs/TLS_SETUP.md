# TLS/SSL Setup with Nginx Reverse Proxy

This guide covers setting up TLS/SSL termination for Floodingnaque using Nginx as a reverse proxy with Let's Encrypt certificates.

## Architecture Overview

```
                    ┌─────────────────────┐
   HTTPS (443)      │                     │
   ──────────────>  │   Nginx (TLS)       │
                    │   Reverse Proxy     │
   HTTP (80)        │                     │
   ──────────────>  │  ┌───────────────┐  │
   (redirect)       │  │ Rate Limiting │  │
                    │  │ Security Hdrs │  │
                    │  │ Compression   │  │
                    │  └───────────────┘  │
                    │         │           │
                    └─────────┼───────────┘
                              │
                              │ HTTP (5000)
                              ▼
                    ┌─────────────────────┐
                    │   Flask/Gunicorn    │
                    │   Backend API       │
                    └─────────────────────┘
```

## Option 1: Self-Hosted Nginx (Recommended for VPS)

### Prerequisites

- Domain pointing to your server (e.g., `api.floodingnaque.com`)
- Ports 80 and 443 open in firewall
- Docker and Docker Compose installed

### Step 1: Update Docker Compose

The production setup already exposes port 5000. For nginx, update `compose.production.yaml` to only bind internally:

```yaml
# Change this:
ports:
  - "5000:5000"

# To this (internal only):
expose:
  - "5000"
```

### Step 2: Create Required Directories

```bash
mkdir -p nginx certbot/conf certbot/www
```

### Step 3: Initial Certificate Setup

1. **Temporarily disable SSL in nginx config** for initial cert:

Create `nginx/floodingnaque-initial.conf`:
```nginx
server {
    listen 80;
    server_name api.floodingnaque.com;

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        return 200 'Waiting for certificate...';
        add_header Content-Type text/plain;
    }
}
```

2. **Start nginx with temporary config**:
```bash
docker run -d --name nginx-temp \
  -p 80:80 \
  -v $(pwd)/nginx/floodingnaque-initial.conf:/etc/nginx/conf.d/default.conf:ro \
  -v $(pwd)/certbot/www:/var/www/certbot:ro \
  nginx:alpine
```

3. **Get initial certificate**:
```bash
docker run -it --rm \
  -v $(pwd)/certbot/conf:/etc/letsencrypt \
  -v $(pwd)/certbot/www:/var/www/certbot \
  certbot/certbot certonly \
  --webroot -w /var/www/certbot \
  --email your-email@example.com \
  --agree-tos \
  --no-eff-email \
  -d api.floodingnaque.com
```

4. **Stop temporary nginx**:
```bash
docker stop nginx-temp && docker rm nginx-temp
```

### Step 4: Deploy with Full SSL

```bash
# Start production services with nginx
docker compose -f compose.production.yaml --profile nginx up -d
```

### Step 5: Certificate Renewal

Certbot container auto-renews. Alternatively, add cron job:

```bash
# /etc/cron.d/certbot-renew
0 0,12 * * * root docker compose -f /path/to/compose.production.yaml --profile nginx run --rm certbot renew --quiet && docker compose -f /path/to/compose.production.yaml --profile nginx exec nginx nginx -s reload
```

---

## Option 2: Traefik (Alternative)

For automatic certificate management, add to `compose.production.yaml`:

```yaml
services:
  traefik:
    image: traefik:v2.10
    command:
      - "--api.insecure=false"
      - "--providers.docker=true"
      - "--providers.docker.exposedbydefault=false"
      - "--entrypoints.web.address=:80"
      - "--entrypoints.websecure.address=:443"
      - "--certificatesresolvers.letsencrypt.acme.httpchallenge=true"
      - "--certificatesresolvers.letsencrypt.acme.httpchallenge.entrypoint=web"
      - "--certificatesresolvers.letsencrypt.acme.email=your-email@example.com"
      - "--certificatesresolvers.letsencrypt.acme.storage=/letsencrypt/acme.json"
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - ./letsencrypt:/letsencrypt

  backend:
    # ... existing config ...
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.api.rule=Host(`api.floodingnaque.com`)"
      - "traefik.http.routers.api.entrypoints=websecure"
      - "traefik.http.routers.api.tls.certresolver=letsencrypt"
      - "traefik.http.services.api.loadbalancer.server.port=5000"
```

---

## Option 3: Cloud Load Balancer

### AWS Application Load Balancer (ALB)

1. Create ACM certificate for your domain
2. Create ALB with HTTPS listener (443) using ACM cert
3. Add target group pointing to EC2 instances on port 5000
4. Configure health check: `/health`

### Google Cloud Load Balancer

1. Create managed SSL certificate
2. Create backend service with health check
3. Create URL map and target HTTPS proxy
4. Create forwarding rule

### Azure Application Gateway

1. Create Application Gateway with WAF
2. Add HTTPS listener with Azure-managed certificate
3. Configure backend pool with VMs on port 5000

---

## Verification

After setup, verify TLS configuration:

```bash
# Check certificate
echo | openssl s_client -servername api.floodingnaque.com -connect api.floodingnaque.com:443 2>/dev/null | openssl x509 -noout -dates

# Test SSL configuration (online)
# Visit: https://www.ssllabs.com/ssltest/analyze.html?d=api.floodingnaque.com

# Test API over HTTPS
curl -v https://api.floodingnaque.com/health
```

---

## Security Checklist

- [ ] TLS 1.2+ only (no TLS 1.0/1.1)
- [ ] Strong cipher suites configured
- [ ] HSTS header enabled
- [ ] HTTP redirects to HTTPS
- [ ] Certificate auto-renewal working
- [ ] Security headers present (X-Frame-Options, etc.)
- [ ] Rate limiting configured
- [ ] Sensitive paths blocked (/.env, /.git)

---

## Troubleshooting

### Certificate Issues

```bash
# Check certificate status
docker compose -f compose.production.yaml --profile nginx run --rm certbot certificates

# Force renewal
docker compose -f compose.production.yaml --profile nginx run --rm certbot renew --force-renewal

# Debug certificate issues
docker compose -f compose.production.yaml --profile nginx run --rm certbot certonly --dry-run \
  --webroot -w /var/www/certbot -d api.floodingnaque.com
```

### Nginx Issues

```bash
# Test config
docker exec floodingnaque-nginx nginx -t

# Reload config
docker exec floodingnaque-nginx nginx -s reload

# Check logs
docker logs floodingnaque-nginx
```

### Connection Issues

```bash
# Check if backend is reachable from nginx
docker exec floodingnaque-nginx curl -s http://backend:5000/health

# Check DNS
nslookup api.floodingnaque.com

# Check ports
netstat -tlnp | grep -E ':(80|443|5000)'
```
