# Deployment Information

## URLs

| Environment | URL                                             |
| ----------- | ----------------------------------------------- |
| Production  | `https://YOUR_DOMAIN` (self-hosted VPS)         |
| Staging     | `https://staging.YOUR_DOMAIN` _(if configured)_ |
| Backend API | `https://api.YOUR_DOMAIN`                       |
| Frontend    | Served by Nginx from the same VPS               |

## Monitoring

| Service      | URL                                                                             |
| ------------ | ------------------------------------------------------------------------------- |
| Grafana      | `http://YOUR_VPS_IP:3000` (behind VPN / SSH tunnel)                             |
| Prometheus   | `http://YOUR_VPS_IP:9090` (internal only)                                       |
| Alertmanager | `http://YOUR_VPS_IP:9093` (internal only)                                       |
| Sentry       | `https://sentry.io/organizations/YOUR_ORG/projects/floodingnaque/` _(optional)_ |
| UptimeRobot  | `https://uptimerobot.com/dashboard` _(optional)_                                |

## Architecture

The application is deployed on a self-hosted VPS using Docker Compose:

- **Nginx** handles TLS termination (Let's Encrypt) and serves the built frontend static files
- **Backend API** runs behind Nginx on port 5000
- **PostgreSQL** via Supabase (external) or a local container
- **Redis** for caching and Celery broker
- **Prometheus + Grafana + Alertmanager** for monitoring (see `compose.observability.yaml`)

## Deployment

```powershell
# Build the frontend
cd frontend
npm run build  # produces dist/

# Deploy to VPS (scp, rsync, or CI/CD)
scp -r dist/ user@YOUR_VPS:/opt/floodingnaque/frontend/dist/

# On the VPS - start all services
cd /opt/floodingnaque
docker compose -f compose.production.yaml --profile nginx --profile monitoring up -d --build

# Optional - add observability stack
docker compose -f compose.production.yaml -f compose.observability.yaml \
  --profile nginx --profile monitoring up -d --build
```

- Build command: `npm run build`
- Output directory: `dist`
- Framework: Vite

## Environment Variables

Set in `frontend/.env.production` (build-time) or pass via CI:

| Variable                  | Notes                                                 |
| ------------------------- | ----------------------------------------------------- |
| `VITE_API_BASE_URL`       | Backend API root URL (e.g. `https://api.YOUR_DOMAIN`) |
| `VITE_SSE_URL`            | SSE endpoint for live alerts                          |
| `VITE_SENTRY_DSN`         | From sentry.io project settings _(optional)_          |
| `VITE_SENTRY_ENVIRONMENT` | `production`                                          |
| `VITE_APP_VERSION`        | `1.0.0`                                               |

> **Note:** Do not commit real values to the repository. The checked-in
> `.env.production` contains only placeholder/default values.

## Post-Deployment Verification Checklist

After each production deploy, verify:

- [ ] Home redirects to login (if not authenticated)
- [ ] Login page loads, form works
- [ ] Can login with real credentials
- [ ] Dashboard loads with real data
- [ ] Prediction form submits successfully
- [ ] Alerts page loads, SSE connects
- [ ] Weather history page loads
- [ ] Reports can be generated
- [ ] Settings page works
- [ ] Logout works
- [ ] Mobile responsive (test on phone or DevTools)
- [ ] PWA installable (check browser install prompt)

## Rollback

1. SSH into your VPS.
2. Check out the previous working commit or restore the previous Docker image tag.
3. Restart:
   ```bash
   docker compose -f compose.production.yaml --profile nginx up -d --build
   ```

## Custom Domain

1. Point your domain's A record to your VPS IP address.
2. Update `nginx/floodingnaque.conf` with the domain.
3. Obtain a TLS certificate via Certbot (see [TLS_SETUP.md](../docs/TLS_SETUP.md)).
4. SSL is provisioned by Let's Encrypt.

## Setup Steps (First Time)

### 1. Provision a VPS

- Ubuntu 22.04+ LTS recommended
- Minimum 4GB RAM, 2 vCPUs, 40GB SSD
- Open ports 80, 443, and 22 (SSH)

### 2. Install Docker

```bash
# Install Docker Engine + Compose plugin
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
```

### 3. Clone and Configure

```bash
cd /opt
git clone https://github.com/floodingnaque/floodingnaque.git
cd floodingnaque

# Copy and edit environment files
cp backend/.env.example backend/.env.production
# Edit backend/.env.production with production secrets
```

### 4. Build Frontend and Deploy

```bash
cd frontend
npm ci && npm run build
cd ..

# Start production stack
docker compose -f compose.production.yaml --profile nginx --profile monitoring up -d --build
```

### Sentry Setup (Optional)

1. Create a project at [sentry.io](https://sentry.io) (React platform).
2. Copy the DSN.
3. Add it as `VITE_SENTRY_DSN` in `frontend/.env.production`.
4. Rebuild and redeploy the frontend.

### Uptime Monitoring (Optional)

1. Create a free account at [uptimerobot.com](https://uptimerobot.com).
2. Add an HTTP(s) monitor for `https://YOUR_DOMAIN`.
3. Set interval to 5 minutes.
4. Add your email as alert contact.
