/**
 * App Component
 *
 * Main application component with routing configuration.
 * Integrates protected routes, layout, and toast notifications.
 */

import { Routes, Route, Navigate } from 'react-router-dom';

import { Toaster } from '@/components/ui/sonner';

// Layout
import { Layout } from '@/app/layout';

// Auth Components
import { ProtectedRoute } from '@/features/auth/components/ProtectedRoute';

// Page Components
import { LoginPage } from '@/app/login/page';
import { DashboardPage } from '@/app/page';
import PredictPage from '@/app/predict/page';
import AlertsPage from '@/app/alerts/page';
import HistoryPage from '@/app/history/page';
import ReportsPage from '@/app/reports/page';
import SettingsPage from '@/app/settings/page';
import AdminPage from '@/app/admin/page';

/**
 * Main App component with route configuration
 */
function App() {
  return (
    <>
      <Routes>
        {/* Public Routes */}
        <Route path="/login" element={<LoginPage />} />

        {/* Protected Routes with Layout */}
        <Route element={<ProtectedRoute />}>
          <Route element={<Layout />}>
            {/* Dashboard - Index Route */}
            <Route index element={<DashboardPage />} />

            {/* Main Application Routes */}
            <Route path="/predict" element={<PredictPage />} />
            <Route path="/alerts" element={<AlertsPage />} />
            <Route path="/history" element={<HistoryPage />} />
            <Route path="/reports" element={<ReportsPage />} />
            <Route path="/settings" element={<SettingsPage />} />

            {/* Admin Route (additional role check in AdminPage) */}
            <Route path="/admin" element={<AdminPage />} />
          </Route>
        </Route>

        {/* Catch-all redirect to home */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>

      {/* Toast Notifications */}
      <Toaster
        position="top-right"
        expand={false}
        richColors
        closeButton
      />
    </>
  );
}

export default App;
