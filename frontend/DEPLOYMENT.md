# Deployment Information

## URLs

| Environment | URL |
|-------------|-----|
| Production  | https://floodingnaque.vercel.app |
| Staging     | https://floodingnaque-staging.vercel.app *(if created)* |
| Backend API | https://floodingnaque-api.railway.app |

## Monitoring

| Service     | URL |
|-------------|-----|
| Sentry      | https://sentry.io/organizations/YOUR_ORG/projects/floodingnaque/ |
| Vercel      | https://vercel.com/YOUR_TEAM/floodingnaque |
| UptimeRobot | https://uptimerobot.com/dashboard *(optional)* |

## Deployment

- **Auto-deploy** on push to `main` branch (via Vercel GitHub integration).
- **Preview deploys** are created automatically for every pull request.
- Build command: `npm run build`
- Output directory: `dist`
- Framework: Vite

## Environment Variables

Set in **Vercel → Project Settings → Environment Variables**:

| Variable                  | Scopes                           | Notes                            |
|---------------------------|----------------------------------|----------------------------------|
| `VITE_API_BASE_URL`       | Production, Preview, Development | Backend API root URL             |
| `VITE_SSE_URL`            | Production, Preview, Development | SSE endpoint for live alerts     |
| `VITE_SENTRY_DSN`         | Production                       | From sentry.io project settings  |
| `VITE_SENTRY_ENVIRONMENT` | Production                       | `production`                     |
| `VITE_APP_VERSION`        | Production                       | `1.0.0`                          |

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

1. Go to **Vercel Dashboard → Deployments**.
2. Find the previous working deployment.
3. Click **"…" → "Promote to Production"**.

## Custom Domain (Optional)

1. In Vercel: **Project Settings → Domains → Add**.
2. Enter your domain (e.g., `floodingnaque.com`).
3. Configure DNS records as instructed by Vercel.
4. SSL is auto-provisioned.

## Setup Steps (First Time)

### Option A — CLI

```bash
cd frontend
npm i -g vercel
vercel login
vercel --prod
```

### Option B — GitHub Integration (Recommended)

1. Go to [vercel.com/dashboard](https://vercel.com/dashboard).
2. Click **"Add New Project"**.
3. Import from GitHub: `KyaRhamil/floodingnaque`.
4. Set **Root Directory** to `frontend`.
5. Set **Framework Preset** to `Vite`.
6. Add environment variables (see table above).
7. Deploy.

### Sentry Setup

1. Create a project at [sentry.io](https://sentry.io) (React platform).
2. Copy the DSN.
3. Add it as `VITE_SENTRY_DSN` in Vercel env vars.
4. Configure alert rules for new errors.

### Uptime Monitoring (Optional)

1. Create a free account at [uptimerobot.com](https://uptimerobot.com).
2. Add an HTTP(s) monitor for `https://floodingnaque.vercel.app`.
3. Set interval to 5 minutes.
4. Add your email as alert contact.
