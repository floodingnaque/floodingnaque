/**
 * App Component
 *
 * Main application component with routing configuration.
 * Integrates protected routes, layout, and toast notifications.
 */

import { lazy, Suspense } from 'react';
import { Routes, Route } from 'react-router-dom';

import { Toaster } from '@/components/ui/sonner';
import { PageLoader } from '@/components/feedback/PageLoader';
import { ErrorBoundary } from '@/components/feedback/ErrorBoundary';
import { RouteErrorBoundary, NotFoundFallback } from '@/components/feedback/RouteErrorBoundary';
import { CookieConsent } from '@/components/feedback/CookieConsent';

// Layout & Auth (loaded eagerly - always needed)
import { Layout } from '@/app/layout';
import { ProtectedRoute } from '@/features/auth/components/ProtectedRoute';
import { RequireRole } from '@/features/auth/components/RequireRole';

// Lazy-loaded page components (code-split per route)
const LoginPage    = lazy(() => import('@/app/login/page'));
const ForgotPasswordPage = lazy(() => import('@/app/forgot-password/page'));
const DashboardPage = lazy(() =>
  import('@/app/page').then((m) => ({ default: m.DashboardPage }))
);
const PredictPage  = lazy(() => import('@/app/predict/page'));
const AlertsPage   = lazy(() => import('@/app/alerts/page'));
const HistoryPage  = lazy(() => import('@/app/history/page'));
const ReportsPage  = lazy(() => import('@/app/reports/page'));
const SettingsPage = lazy(() => import('@/app/settings/page'));
const AdminPage    = lazy(() => import('@/app/admin/page'));
const MapPage      = lazy(() => import('@/app/map/page'));
const AnalyticsPage = lazy(() => import('@/app/analytics/page'));
const AdminUsersPage = lazy(() => import('@/app/admin/users/page'));
const AdminLogsPage  = lazy(() => import('@/app/admin/logs/page'));
const AdminBarangaysPage = lazy(() => import('@/app/admin/barangays/page'));
const AdminDataPage  = lazy(() => import('@/app/admin/data/page'));
const AdminModelsPage = lazy(() => import('@/app/admin/models/page'));
const AdminConfigPage = lazy(() => import('@/app/admin/config/page'));
const LandingPage  = lazy(() => import('@/app/landing/page'));
const TermsPage    = lazy(() => import('@/app/terms/page'));
const PrivacyPage  = lazy(() => import('@/app/privacy/page'));

/**
 * Main App component with route configuration
 */
function App() {
  return (
    <ErrorBoundary>
      <Suspense fallback={<PageLoader />}>
        <Routes>
          {/* Public Routes */}
          <Route path="/" element={<LandingPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/forgot-password" element={<ForgotPasswordPage />} />
          <Route path="/terms" element={<TermsPage />} />
          <Route path="/privacy" element={<PrivacyPage />} />

          {/* Protected Routes with Layout */}
          <Route element={<ProtectedRoute />}>
            <Route element={<Layout />}>
              {/* Dashboard */}
              <Route path="/dashboard" element={<RouteErrorBoundary><DashboardPage /></RouteErrorBoundary>} />

              {/* Main Application Routes */}
              <Route path="/predict" element={<RouteErrorBoundary><PredictPage /></RouteErrorBoundary>} />
              <Route path="/map" element={<RouteErrorBoundary><MapPage /></RouteErrorBoundary>} />
              <Route path="/alerts" element={<RouteErrorBoundary><AlertsPage /></RouteErrorBoundary>} />
              <Route path="/history" element={<RouteErrorBoundary><HistoryPage /></RouteErrorBoundary>} />
              <Route path="/reports" element={<RouteErrorBoundary><ReportsPage /></RouteErrorBoundary>} />
              <Route path="/analytics" element={<RouteErrorBoundary><AnalyticsPage /></RouteErrorBoundary>} />
              <Route path="/settings" element={<RouteErrorBoundary><SettingsPage /></RouteErrorBoundary>} />

              {/* Admin Routes (guarded by role) */}
              <Route path="/admin" element={
                <RequireRole role="admin">
                  <RouteErrorBoundary><AdminPage /></RouteErrorBoundary>
                </RequireRole>
              } />
              <Route path="/admin/users" element={
                <RequireRole role="admin">
                  <RouteErrorBoundary><AdminUsersPage /></RouteErrorBoundary>
                </RequireRole>
              } />
              <Route path="/admin/logs" element={
                <RequireRole role="admin">
                  <RouteErrorBoundary><AdminLogsPage /></RouteErrorBoundary>
                </RequireRole>
              } />
              <Route path="/admin/barangays" element={
                <RequireRole role="admin">
                  <RouteErrorBoundary><AdminBarangaysPage /></RouteErrorBoundary>
                </RequireRole>
              } />
              <Route path="/admin/data" element={
                <RequireRole role="admin">
                  <RouteErrorBoundary><AdminDataPage /></RouteErrorBoundary>
                </RequireRole>
              } />
              <Route path="/admin/models" element={
                <RequireRole role="admin">
                  <RouteErrorBoundary><AdminModelsPage /></RouteErrorBoundary>
                </RequireRole>
              } />
              <Route path="/admin/config" element={
                <RequireRole role="admin">
                  <RouteErrorBoundary><AdminConfigPage /></RouteErrorBoundary>
                </RequireRole>
              } />
            </Route>
          </Route>

          {/* 404 – Not Found */}
          <Route path="*" element={<NotFoundFallback />} />
        </Routes>
      </Suspense>

      {/* Toast Notifications */}
      <Toaster
        position="top-right"
        expand={false}
        richColors
        closeButton
      />

      {/* Cookie Consent Banner */}
      <CookieConsent />
    </ErrorBoundary>
  );
}

export default App;
