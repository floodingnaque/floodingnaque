/**
 * App Component
 *
 * Main application component with routing configuration.
 * Integrates protected routes, layout, and toast notifications.
 */

import { lazy, Suspense, useEffect } from "react";
import { Route, Routes, useLocation } from "react-router-dom";

import { CookieConsent } from "@/components/feedback/CookieConsent";
import { ErrorBoundary } from "@/components/feedback/ErrorBoundary";
import { OfflineBanner } from "@/components/feedback/OfflineBanner";
import { PageLoader } from "@/components/feedback/PageLoader";
import {
  NotFoundFallback,
  RouteErrorBoundary,
} from "@/components/feedback/RouteErrorBoundary";
import { InstallPrompt } from "@/components/pwa/InstallPrompt";
import { Toaster } from "@/components/ui/sonner";

// Layout & Auth (loaded eagerly - always needed)
import { Layout } from "@/app/layout";
import { ProtectedRoute } from "@/features/auth/components/ProtectedRoute";
import { RequireRole } from "@/features/auth/components/RequireRole";

// Lazy-loaded page components (code-split per route)
const LoginPage = lazy(() => import("@/app/login/page"));
const ForgotPasswordPage = lazy(() => import("@/app/forgot-password/page"));
const RegisterPage = lazy(() => import("@/app/register/page"));
const DashboardPage = lazy(() =>
  import("@/app/page").then((m) => ({ default: m.DashboardPage })),
);
const PredictPage = lazy(() => import("@/app/predict/page"));
const AlertsPage = lazy(() => import("@/app/alerts/page"));
const HistoryPage = lazy(() => import("@/app/history/page"));
const ReportsPage = lazy(() => import("@/app/reports/page"));
const SettingsPage = lazy(() => import("@/app/settings/page"));
const AdminPage = lazy(() => import("@/app/admin/page"));
const AdminLayout = lazy(() => import("@/app/admin/layout"));
const MapPage = lazy(() => import("@/app/map/page"));
const AnalyticsPage = lazy(() => import("@/app/analytics/page"));
const AdminUsersPage = lazy(() => import("@/app/admin/users/page"));
const AdminLogsPage = lazy(() => import("@/app/admin/logs/page"));
const AdminBarangaysPage = lazy(() => import("@/app/admin/barangays/page"));
const AdminDataPage = lazy(() => import("@/app/admin/data/page"));
const AdminModelsPage = lazy(() => import("@/app/admin/models/page"));
const AdminConfigPage = lazy(() => import("@/app/admin/config/page"));
const AdminSecurityPage = lazy(() => import("@/app/admin/security/page"));
const AdminMonitoringPage = lazy(() => import("@/app/admin/monitoring/page"));
const CompliancePage = lazy(() => import("@/app/compliance/page"));
const IncidentsPage = lazy(() => import("@/app/incidents/page"));
const AdminStoragePage = lazy(() => import("@/app/admin/storage/page"));
const AdminWorkflowPage = lazy(() => import("@/app/admin/workflow/page"));
const AdminSensorPage = lazy(() => import("@/app/admin/sensor/page"));
const AdminChatPage = lazy(() => import("@/app/admin/chat/page"));
const AdminAlertsPage = lazy(() => import("@/app/admin/alerts/page"));
const LandingPage = lazy(() => import("@/app/landing/page"));
const TermsPage = lazy(() => import("@/app/terms/page"));
const PrivacyPage = lazy(() => import("@/app/privacy/page"));
const OfflinePage = lazy(() => import("@/app/offline/page"));
const CommunityPage = lazy(() => import("@/app/community/page"));
const EvacuationPage = lazy(() => import("@/app/evacuation/page"));

// Operator Dashboard
const OperatorLayout = lazy(() => import("@/app/operator/layout"));
const OperatorOverviewPage = lazy(() => import("@/app/operator/page"));
const OperatorMapPage = lazy(() => import("@/app/operator/map/page"));
const OperatorWeatherPage = lazy(() => import("@/app/operator/weather/page"));
const OperatorTidesPage = lazy(() => import("@/app/operator/tides/page"));
const OperatorIncidentsPage = lazy(
  () => import("@/app/operator/incidents/page"),
);
const OperatorAlertsPage = lazy(() => import("@/app/operator/alerts/page"));
const OperatorBroadcastPage = lazy(
  () => import("@/app/operator/broadcast/page"),
);
const OperatorReportsPage = lazy(() => import("@/app/operator/reports/page"));
const OperatorEvacuationPage = lazy(
  () => import("@/app/operator/evacuation/page"),
);
const OperatorResidentsPage = lazy(
  () => import("@/app/operator/residents/page"),
);
const OperatorPredictPage = lazy(() => import("@/app/operator/predict/page"));
const OperatorAnalyticsPage = lazy(
  () => import("@/app/operator/analytics/page"),
);
const OperatorAARPage = lazy(() => import("@/app/operator/aar/page"));
const OperatorSettingsPage = lazy(() => import("@/app/operator/settings/page"));
const OperatorChatPage = lazy(() => import("@/app/operator/chat/page"));
const OperatorBarangaysPage = lazy(
  () => import("@/app/operator/barangays/page"),
);
const SimulationPage = lazy(() => import("@/app/operator/simulate/page"));

// Resident Dashboard
const ResidentLayout = lazy(() => import("@/app/resident/layout"));
const ResidentOverviewPage = lazy(() => import("@/app/resident/page"));
const ResidentRiskPage = lazy(() => import("@/app/resident/risk/page"));
const ResidentMapPage = lazy(() => import("@/app/resident/map/page"));
const ResidentAlertsPage = lazy(() => import("@/app/resident/alerts/page"));
const ResidentEmergencyPage = lazy(
  () => import("@/app/resident/emergency/page"),
);
const ResidentEvacuationPage = lazy(
  () => import("@/app/resident/evacuation/page"),
);
const ResidentReportPage = lazy(() => import("@/app/resident/report/page"));
const ResidentCommunityPage = lazy(
  () => import("@/app/resident/community/page"),
);
const ResidentMyReportsPage = lazy(
  () => import("@/app/resident/my-reports/page"),
);
const ResidentGuidePage = lazy(() => import("@/app/resident/guide/page"));
const ResidentPlanPage = lazy(() => import("@/app/resident/plan/page"));
const ResidentHouseholdPage = lazy(
  () => import("@/app/resident/profile/household/page"),
);
const ResidentSettingsPage = lazy(() => import("@/app/resident/settings/page"));
const ResidentChatPage = lazy(() => import("@/app/resident/chat/page"));

/** Scrolls to top on pathname change (works with BrowserRouter) */
function ScrollToTop() {
  const { pathname } = useLocation();
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [pathname]);
  return null;
}

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
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/terms" element={<TermsPage />} />
          <Route path="/privacy" element={<PrivacyPage />} />
          <Route path="/offline" element={<OfflinePage />} />

          {/* Protected Routes with Layout */}
          <Route element={<ProtectedRoute />}>
            <Route element={<Layout />}>
              {/* Dashboard */}
              <Route
                path="/dashboard"
                element={
                  <RouteErrorBoundary>
                    <DashboardPage />
                  </RouteErrorBoundary>
                }
              />

              {/* Main Application Routes */}
              <Route
                path="/predict"
                element={
                  <RouteErrorBoundary>
                    <PredictPage />
                  </RouteErrorBoundary>
                }
              />
              <Route
                path="/map"
                element={
                  <RouteErrorBoundary>
                    <MapPage />
                  </RouteErrorBoundary>
                }
              />
              <Route
                path="/alerts"
                element={
                  <RouteErrorBoundary>
                    <AlertsPage />
                  </RouteErrorBoundary>
                }
              />
              <Route
                path="/history"
                element={
                  <RouteErrorBoundary>
                    <HistoryPage />
                  </RouteErrorBoundary>
                }
              />
              <Route
                path="/reports"
                element={
                  <RouteErrorBoundary>
                    <ReportsPage />
                  </RouteErrorBoundary>
                }
              />
              <Route
                path="/analytics"
                element={
                  <RouteErrorBoundary>
                    <AnalyticsPage />
                  </RouteErrorBoundary>
                }
              />
              <Route
                path="/settings"
                element={
                  <RouteErrorBoundary>
                    <SettingsPage />
                  </RouteErrorBoundary>
                }
              />
              <Route
                path="/compliance"
                element={
                  <RouteErrorBoundary>
                    <CompliancePage />
                  </RouteErrorBoundary>
                }
              />
              <Route
                path="/incidents"
                element={
                  <RouteErrorBoundary>
                    <IncidentsPage />
                  </RouteErrorBoundary>
                }
              />
              <Route
                path="/community"
                element={
                  <RouteErrorBoundary>
                    <CommunityPage />
                  </RouteErrorBoundary>
                }
              />
              <Route
                path="/evacuation"
                element={
                  <RouteErrorBoundary>
                    <EvacuationPage />
                  </RouteErrorBoundary>
                }
              />

              {/* Admin Routes (guarded by role) */}
            </Route>
          </Route>

          {/* ── Admin Dashboard Routes ────────────────────────────── */}
          <Route element={<ProtectedRoute />}>
            <Route
              element={
                <RequireRole requiredRole="admin">
                  <AdminLayout />
                </RequireRole>
              }
            >
              <Route
                path="/admin"
                element={
                  <RouteErrorBoundary>
                    <AdminPage />
                  </RouteErrorBoundary>
                }
              />
              <Route
                path="/admin/users"
                element={
                  <RouteErrorBoundary>
                    <AdminUsersPage />
                  </RouteErrorBoundary>
                }
              />
              <Route
                path="/admin/logs"
                element={
                  <RouteErrorBoundary>
                    <AdminLogsPage />
                  </RouteErrorBoundary>
                }
              />
              <Route
                path="/admin/barangays"
                element={
                  <RouteErrorBoundary>
                    <AdminBarangaysPage />
                  </RouteErrorBoundary>
                }
              />
              <Route
                path="/admin/data"
                element={
                  <RouteErrorBoundary>
                    <AdminDataPage />
                  </RouteErrorBoundary>
                }
              />
              <Route
                path="/admin/models"
                element={
                  <RouteErrorBoundary>
                    <AdminModelsPage />
                  </RouteErrorBoundary>
                }
              />
              <Route
                path="/admin/config"
                element={
                  <RouteErrorBoundary>
                    <AdminConfigPage />
                  </RouteErrorBoundary>
                }
              />
              <Route
                path="/admin/security"
                element={
                  <RouteErrorBoundary>
                    <AdminSecurityPage />
                  </RouteErrorBoundary>
                }
              />
              <Route
                path="/admin/monitoring"
                element={
                  <RouteErrorBoundary>
                    <AdminMonitoringPage />
                  </RouteErrorBoundary>
                }
              />
              <Route
                path="/admin/storage"
                element={
                  <RouteErrorBoundary>
                    <AdminStoragePage />
                  </RouteErrorBoundary>
                }
              />
              <Route
                path="/admin/workflow"
                element={
                  <RouteErrorBoundary>
                    <AdminWorkflowPage />
                  </RouteErrorBoundary>
                }
              />
              <Route
                path="/admin/sensor"
                element={
                  <RouteErrorBoundary>
                    <AdminSensorPage />
                  </RouteErrorBoundary>
                }
              />
              <Route
                path="/admin/chat"
                element={
                  <RouteErrorBoundary>
                    <AdminChatPage />
                  </RouteErrorBoundary>
                }
              />
              <Route
                path="/admin/alerts"
                element={
                  <RouteErrorBoundary>
                    <AdminAlertsPage />
                  </RouteErrorBoundary>
                }
              />
              <Route
                path="/admin/reports"
                element={
                  <RouteErrorBoundary>
                    <OperatorReportsPage />
                  </RouteErrorBoundary>
                }
              />
            </Route>
          </Route>

          {/* ── Operator Dashboard Routes ─────────────────────────── */}
          <Route element={<ProtectedRoute />}>
            <Route
              element={
                <RequireRole requiredRole={["operator", "admin"]}>
                  <OperatorLayout />
                </RequireRole>
              }
            >
              <Route
                path="/operator"
                element={
                  <RouteErrorBoundary>
                    <OperatorOverviewPage />
                  </RouteErrorBoundary>
                }
              />
              <Route
                path="/operator/map"
                element={
                  <RouteErrorBoundary>
                    <OperatorMapPage />
                  </RouteErrorBoundary>
                }
              />
              <Route
                path="/operator/weather"
                element={
                  <RouteErrorBoundary>
                    <OperatorWeatherPage />
                  </RouteErrorBoundary>
                }
              />
              <Route
                path="/operator/tides"
                element={
                  <RouteErrorBoundary>
                    <OperatorTidesPage />
                  </RouteErrorBoundary>
                }
              />
              <Route
                path="/operator/incidents"
                element={
                  <RouteErrorBoundary>
                    <OperatorIncidentsPage />
                  </RouteErrorBoundary>
                }
              />
              <Route
                path="/operator/alerts"
                element={
                  <RouteErrorBoundary>
                    <OperatorAlertsPage />
                  </RouteErrorBoundary>
                }
              />
              <Route
                path="/operator/broadcast"
                element={
                  <RouteErrorBoundary>
                    <OperatorBroadcastPage />
                  </RouteErrorBoundary>
                }
              />
              <Route
                path="/operator/reports"
                element={
                  <RouteErrorBoundary>
                    <OperatorReportsPage />
                  </RouteErrorBoundary>
                }
              />
              <Route
                path="/operator/evacuation"
                element={
                  <RouteErrorBoundary>
                    <OperatorEvacuationPage />
                  </RouteErrorBoundary>
                }
              />
              <Route
                path="/operator/residents"
                element={
                  <RouteErrorBoundary>
                    <OperatorResidentsPage />
                  </RouteErrorBoundary>
                }
              />
              <Route
                path="/operator/predict"
                element={
                  <RouteErrorBoundary>
                    <OperatorPredictPage />
                  </RouteErrorBoundary>
                }
              />
              <Route
                path="/operator/analytics"
                element={
                  <RouteErrorBoundary>
                    <OperatorAnalyticsPage />
                  </RouteErrorBoundary>
                }
              />
              <Route
                path="/operator/aar"
                element={
                  <RouteErrorBoundary>
                    <OperatorAARPage />
                  </RouteErrorBoundary>
                }
              />
              <Route
                path="/operator/settings"
                element={
                  <RouteErrorBoundary>
                    <OperatorSettingsPage />
                  </RouteErrorBoundary>
                }
              />
              <Route
                path="/operator/chat"
                element={
                  <RouteErrorBoundary>
                    <OperatorChatPage />
                  </RouteErrorBoundary>
                }
              />
              <Route
                path="/operator/barangays"
                element={
                  <RouteErrorBoundary>
                    <OperatorBarangaysPage />
                  </RouteErrorBoundary>
                }
              />
              <Route
                path="/operator/simulate"
                element={
                  <RouteErrorBoundary>
                    <SimulationPage />
                  </RouteErrorBoundary>
                }
              />
            </Route>
          </Route>

          {/* ── Resident Dashboard Routes ─────────────────────────── */}
          <Route element={<ProtectedRoute />}>
            <Route
              element={
                <RequireRole requiredRole="user">
                  <ResidentLayout />
                </RequireRole>
              }
            >
              <Route
                path="/resident"
                element={
                  <RouteErrorBoundary>
                    <ResidentOverviewPage />
                  </RouteErrorBoundary>
                }
              />
              <Route
                path="/resident/risk"
                element={
                  <RouteErrorBoundary>
                    <ResidentRiskPage />
                  </RouteErrorBoundary>
                }
              />
              <Route
                path="/resident/map"
                element={
                  <RouteErrorBoundary>
                    <ResidentMapPage />
                  </RouteErrorBoundary>
                }
              />
              <Route
                path="/resident/alerts"
                element={
                  <RouteErrorBoundary>
                    <ResidentAlertsPage />
                  </RouteErrorBoundary>
                }
              />
              <Route
                path="/resident/emergency"
                element={
                  <RouteErrorBoundary>
                    <ResidentEmergencyPage />
                  </RouteErrorBoundary>
                }
              />
              <Route
                path="/resident/evacuation"
                element={
                  <RouteErrorBoundary>
                    <ResidentEvacuationPage />
                  </RouteErrorBoundary>
                }
              />
              <Route
                path="/resident/report"
                element={
                  <RouteErrorBoundary>
                    <ResidentReportPage />
                  </RouteErrorBoundary>
                }
              />
              <Route
                path="/resident/community"
                element={
                  <RouteErrorBoundary>
                    <ResidentCommunityPage />
                  </RouteErrorBoundary>
                }
              />
              <Route
                path="/resident/my-reports"
                element={
                  <RouteErrorBoundary>
                    <ResidentMyReportsPage />
                  </RouteErrorBoundary>
                }
              />
              <Route
                path="/resident/guide"
                element={
                  <RouteErrorBoundary>
                    <ResidentGuidePage />
                  </RouteErrorBoundary>
                }
              />
              <Route
                path="/resident/plan"
                element={
                  <RouteErrorBoundary>
                    <ResidentPlanPage />
                  </RouteErrorBoundary>
                }
              />
              <Route
                path="/resident/profile/household"
                element={
                  <RouteErrorBoundary>
                    <ResidentHouseholdPage />
                  </RouteErrorBoundary>
                }
              />
              <Route
                path="/resident/settings"
                element={
                  <RouteErrorBoundary>
                    <ResidentSettingsPage />
                  </RouteErrorBoundary>
                }
              />
              <Route
                path="/resident/chat"
                element={
                  <RouteErrorBoundary>
                    <ResidentChatPage />
                  </RouteErrorBoundary>
                }
              />
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
        visibleToasts={5}
        duration={4000}
      />

      {/* Scroll to top on route change */}
      <ScrollToTop />

      {/* Offline Indicator */}
      <OfflineBanner />

      {/* PWA Install Prompt */}
      <InstallPrompt />

      {/* Cookie Consent Banner */}
      <CookieConsent />
    </ErrorBoundary>
  );
}

export default App;
