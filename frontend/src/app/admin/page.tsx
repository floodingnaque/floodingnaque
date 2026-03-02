/**
 * Admin Page
 *
 * Admin dashboard with real-time system health monitoring and
 * dashboard statistics. Restricted to users with admin role.
 */

import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Shield,
  Server,
  Activity,
  AlertTriangle,
  CheckCircle,
  Clock,
  Database,
  Cpu,
  RefreshCw,
  Loader2,
} from 'lucide-react';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { useUser } from '@/state';
import { cn } from '@/lib/utils';
import { useSystemHealth } from '@/features/admin/hooks/useAdmin';
import { useDashboardStats } from '@/features/dashboard/hooks/useDashboard';

/**
 * Stat card component
 */
function StatCard({
  icon: Icon,
  label,
  value,
  description,
  isLoading,
}: {
  icon: React.ElementType;
  label: string;
  value: string | number;
  description?: string;
  isLoading?: boolean;
}) {
  return (
    <Card>
      <CardContent className="pt-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-primary/10">
              <Icon className="h-5 w-5 text-primary" />
            </div>
            <div>
              <p className="text-sm text-muted-foreground">{label}</p>
              {isLoading ? (
                <Skeleton className="h-8 w-16 mt-1" />
              ) : (
                <p className="text-2xl font-bold">{value}</p>
              )}
            </div>
          </div>
        </div>
        {description && (
          <p className="text-xs text-muted-foreground mt-2">{description}</p>
        )}
      </CardContent>
    </Card>
  );
}

/**
 * Admin Page Component
 */
export default function AdminPage() {
  const navigate = useNavigate();
  const user = useUser();

  // Redirect non-admin users to dashboard
  useEffect(() => {
    if (user && user.role !== 'admin') {
      navigate('/dashboard', { replace: true });
    }
  }, [user, navigate]);

  // Fetch real data
  const {
    data: health,
    isLoading: healthLoading,
    refetch: refetchHealth,
    isFetching: healthFetching,
  } = useSystemHealth(!!user && user.role === 'admin');

  const {
    data: dashStats,
    isLoading: statsLoading,
  } = useDashboardStats();

  // Show nothing while checking permissions
  if (!user || user.role !== 'admin') {
    return null;
  }

  const isHealthy = health?.status === 'healthy';
  const dbConnected = health?.checks?.database?.connected ?? false;
  const dbLatency = health?.checks?.database?.latency_ms;
  const modelLoaded = health?.checks?.model_available ?? false;
  const slaResponseMs = health?.sla?.response_time_ms;
  const schedulerRunning = health?.checks?.scheduler_running ?? false;
  const redisStatus = health?.checks?.redis?.status ?? 'unknown';
  const cacheStatus = health?.checks?.cache?.status ?? 'unknown';

  return (
    <div className="container mx-auto space-y-8 py-8 px-4">
      {/* Page Header */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
              <Shield className="h-5 w-5 text-primary" />
            </div>
            <div>
              <h1 className="text-3xl font-bold tracking-tight">Admin Panel</h1>
              <p className="text-muted-foreground">
                System health monitoring and statistics
              </p>
            </div>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => refetchHealth()}
            disabled={healthFetching}
          >
            {healthFetching ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <RefreshCw className="mr-2 h-4 w-4" />
            )}
            Refresh
          </Button>
        </div>
      </div>

      {/* System Stats Grid */}
      <div>
        <h2 className="text-xl font-semibold mb-4">System Overview</h2>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <StatCard
            icon={Activity}
            label="Total Predictions"
            value={dashStats?.total_predictions?.toLocaleString() ?? '-'}
            description={`${dashStats?.predictions_today ?? 0} today`}
            isLoading={statsLoading}
          />
          <StatCard
            icon={AlertTriangle}
            label="Active Alerts"
            value={dashStats?.active_alerts ?? '-'}
            description={
              dashStats?.active_alerts === 0
                ? 'All clear'
                : 'Requires attention'
            }
            isLoading={statsLoading}
          />
          <StatCard
            icon={Server}
            label="API Response"
            value={slaResponseMs != null ? `${Math.round(slaResponseMs)}ms` : '-'}
            description={
              health?.sla?.within_sla ? 'Within SLA' : 'SLA exceeded'
            }
            isLoading={healthLoading}
          />
          <StatCard
            icon={Shield}
            label="Avg Risk Level"
            value={
              dashStats?.avg_risk_level != null
                ? `${Math.round(dashStats.avg_risk_level)}%`
                : '-'
            }
            isLoading={statsLoading}
          />
        </div>
      </div>

      {/* Infrastructure Status */}
      <div className="grid gap-4 md:grid-cols-3">
        {/* Database Status */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base flex items-center gap-2">
              <Database className="h-4 w-4" />
              Database
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {healthLoading ? (
              <div className="space-y-2">
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-3/4" />
              </div>
            ) : (
              <>
                <div className="flex justify-between items-center text-sm">
                  <span className="text-muted-foreground">Status</span>
                  <Badge
                    className={cn(
                      dbConnected
                        ? 'bg-green-100 text-green-800 hover:bg-green-100'
                        : 'bg-red-100 text-red-800 hover:bg-red-100',
                    )}
                  >
                    {dbConnected ? (
                      <CheckCircle className="h-3 w-3 mr-1" />
                    ) : (
                      <AlertTriangle className="h-3 w-3 mr-1" />
                    )}
                    {dbConnected ? 'Connected' : 'Disconnected'}
                  </Badge>
                </div>
                {dbLatency != null && (
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Latency</span>
                    <span className="font-medium">{Math.round(dbLatency)}ms</span>
                  </div>
                )}
                {health?.checks?.database_pool && (
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Pool Size</span>
                    <span className="font-medium">
                      {health.checks.database_pool.size ?? '-'}
                    </span>
                  </div>
                )}
              </>
            )}
          </CardContent>
        </Card>

        {/* Server Health */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base flex items-center gap-2">
              <Server className="h-4 w-4" />
              Server Health
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {healthLoading ? (
              <div className="space-y-2">
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-3/4" />
              </div>
            ) : (
              <>
                <div className="flex justify-between items-center text-sm">
                  <span className="text-muted-foreground">Status</span>
                  <Badge
                    className={cn(
                      isHealthy
                        ? 'bg-green-100 text-green-800 hover:bg-green-100'
                        : 'bg-amber-100 text-amber-800 hover:bg-amber-100',
                    )}
                  >
                    {isHealthy ? (
                      <CheckCircle className="h-3 w-3 mr-1" />
                    ) : (
                      <Clock className="h-3 w-3 mr-1" />
                    )}
                    {isHealthy ? 'Healthy' : 'Degraded'}
                  </Badge>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Scheduler</span>
                  <span className="font-medium">
                    {schedulerRunning ? 'Running' : 'Stopped'}
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Sentry</span>
                  <span className="font-medium">
                    {health?.checks?.sentry_enabled ? 'Enabled' : 'Disabled'}
                  </span>
                </div>
              </>
            )}
          </CardContent>
        </Card>

        {/* Services */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base flex items-center gap-2">
              <Cpu className="h-4 w-4" />
              Services
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {healthLoading ? (
              <div className="space-y-2">
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-3/4" />
              </div>
            ) : (
              <>
                <div className="flex justify-between items-center text-sm">
                  <span className="text-muted-foreground">ML Model</span>
                  <Badge
                    className={cn(
                      modelLoaded
                        ? 'bg-green-100 text-green-800 hover:bg-green-100'
                        : 'bg-red-100 text-red-800 hover:bg-red-100',
                    )}
                  >
                    {modelLoaded ? 'Loaded' : 'Not Available'}
                  </Badge>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Redis</span>
                  <span className="font-medium capitalize">{redisStatus}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Cache</span>
                  <span className="font-medium capitalize">{cacheStatus}</span>
                </div>
                {health?.model?.version && (
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Model Version</span>
                    <span className="font-medium">{health.model.version}</span>
                  </div>
                )}
              </>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Model Metrics */}
      {health?.model?.metrics && Object.keys(health.model.metrics).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5" />
              Model Performance Metrics
            </CardTitle>
            <CardDescription>
              Current ML model accuracy and performance scores
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 sm:grid-cols-2 md:grid-cols-4">
              {Object.entries(health.model.metrics).map(([key, value]) => (
                <div key={key} className="space-y-1">
                  <p className="text-sm text-muted-foreground capitalize">
                    {key.replace(/_/g, ' ')}
                  </p>
                  <p className="text-xl font-bold">
                    {typeof value === 'number'
                      ? value < 1
                        ? `${(value * 100).toFixed(1)}%`
                        : value.toFixed(2)
                      : String(value)}
                  </p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* System Info */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Server className="h-5 w-5" />
            System Information
          </CardTitle>
          <CardDescription>
            Server environment and configuration details
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 sm:grid-cols-2 md:grid-cols-3">
            <div className="space-y-1">
              <p className="text-sm text-muted-foreground">Python Version</p>
              <p className="font-medium">
                {health?.system?.python_version ?? '-'}
              </p>
            </div>
            <div className="space-y-1">
              <p className="text-sm text-muted-foreground">Model Type</p>
              <p className="font-medium">
                {health?.model?.type ?? '-'}
              </p>
            </div>
            <div className="space-y-1">
              <p className="text-sm text-muted-foreground">Feature Count</p>
              <p className="font-medium">
                {health?.model?.features_count ?? '-'}
              </p>
            </div>
            <div className="space-y-1">
              <p className="text-sm text-muted-foreground">Last Health Check</p>
              <p className="font-medium">
                {health?.timestamp
                  ? new Date(health.timestamp).toLocaleString()
                  : '-'}
              </p>
            </div>
            <div className="space-y-1">
              <p className="text-sm text-muted-foreground">SLA Threshold</p>
              <p className="font-medium">
                {health?.sla?.threshold_ms
                  ? `${health.sla.threshold_ms}ms`
                  : '-'}
              </p>
            </div>
            <div className="space-y-1">
              <p className="text-sm text-muted-foreground">Logged in as</p>
              <p className="font-medium">{user.name} ({user.email})</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
