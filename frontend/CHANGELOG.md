# Changelog

All notable changes to the Floodingnaque frontend are documented here.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [1.0.0] - 2026-01-31

### Added

- **Authentication** - login, registration, JWT token management with silent refresh.
- **Dashboard** - stats cards, recent activity feed, recent alerts, quick actions.
- **Flood Prediction** - prediction form with weather inputs, risk display (Safe / Alert / Critical), probability visualisation.
- **Real-time Alerts** - SSE-powered live alert stream, alert list with filtering, live alerts banner with unread count, connection status indicator.
- **Weather History** - paginated weather data table, interactive charts (Recharts), date range filtering, data export.
- **Map Visualisation** - Leaflet-based flood map, risk markers, location picker.
- **Report Generation** - PDF and CSV export for weather data and predictions.
- **User Settings** - profile management, password change.
- **Admin Panel** - admin-only dashboard page.
- **Dark / Light Theme** - system-preference aware, persisted to localStorage.
- **Responsive Design** - mobile-first layout with collapsible sidebar.
- **PWA Support** - web app manifest, icon set, installable prompt.
- **Error Handling** - ErrorBoundary with recovery UI, RouteErrorBoundary per page, Sentry integration (optional).
- **Accessibility** - skip-nav link, ARIA labels, `aria-live` regions, keyboard navigation, focus management.
- **Performance** - React.lazy code-splitting for all pages, `React.memo` on dashboard components, lazy-loaded chart/table heavy components.
- **Security** - input sanitisation helpers, URL validation, CSP nonce utility.
- **Deployment** - Vercel config (`vercel.json`), environment-based configuration, production `.env`, deployment documentation.
- **Testing** - Vitest unit tests for hooks and components, MSW API mocks, Playwright e2e scaffolding, integration tests for auth and prediction flows.
