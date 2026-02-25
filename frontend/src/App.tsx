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

// Layout & Auth (loaded eagerly — always needed)
import { Layout } from '@/app/layout';
import { ProtectedRoute } from '@/features/auth/components/ProtectedRoute';

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

/**
 * Main App component with route configuration
 */
function App() {
  return (
    <ErrorBoundary>
      <Suspense fallback={<PageLoader />}>
        <Routes>
          {/* Public Routes */}
          <Route path="/login" element={<LoginPage />} />
          <Route path="/forgot-password" element={<ForgotPasswordPage />} />

          {/* Protected Routes with Layout */}
          <Route element={<ProtectedRoute />}>
            <Route element={<Layout />}>
              {/* Dashboard - Index Route */}
              <Route index element={<RouteErrorBoundary><DashboardPage /></RouteErrorBoundary>} />

              {/* Main Application Routes */}
              <Route path="/predict" element={<RouteErrorBoundary><PredictPage /></RouteErrorBoundary>} />
              <Route path="/alerts" element={<RouteErrorBoundary><AlertsPage /></RouteErrorBoundary>} />
              <Route path="/history" element={<RouteErrorBoundary><HistoryPage /></RouteErrorBoundary>} />
              <Route path="/reports" element={<RouteErrorBoundary><ReportsPage /></RouteErrorBoundary>} />
              <Route path="/settings" element={<RouteErrorBoundary><SettingsPage /></RouteErrorBoundary>} />

              {/* Admin Route (additional role check in AdminPage) */}
              <Route path="/admin" element={<RouteErrorBoundary><AdminPage /></RouteErrorBoundary>} />
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
    </ErrorBoundary>
  );
}

export default App;
