/**
 * Admin Page
 *
 * Admin dashboard with user management and system statistics.
 * Restricted to users with admin role.
 */

import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Shield,
  Users,
  Server,
  Activity,
  AlertTriangle,
  CheckCircle,
  Clock,
  Database,
  TrendingUp,
  HardDrive,
} from 'lucide-react';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Button } from '@/components/ui/button';
import { useUser } from '@/state';
import { cn } from '@/lib/utils';

/**
 * Mock users data for demonstration
 */
const mockUsers = [
  {
    id: 1,
    name: 'John Doe',
    email: 'john.doe@example.com',
    role: 'admin' as const,
    status: 'active' as const,
    lastLogin: '2026-02-02T08:30:00Z',
    createdAt: '2024-01-15T10:00:00Z',
  },
  {
    id: 2,
    name: 'Jane Smith',
    email: 'jane.smith@example.com',
    role: 'user' as const,
    status: 'active' as const,
    lastLogin: '2026-02-01T14:45:00Z',
    createdAt: '2024-03-20T09:15:00Z',
  },
  {
    id: 3,
    name: 'Mike Johnson',
    email: 'mike.j@example.com',
    role: 'user' as const,
    status: 'inactive' as const,
    lastLogin: '2026-01-15T11:20:00Z',
    createdAt: '2024-06-10T16:30:00Z',
  },
  {
    id: 4,
    name: 'Sarah Williams',
    email: 'sarah.w@example.com',
    role: 'user' as const,
    status: 'active' as const,
    lastLogin: '2026-02-02T06:00:00Z',
    createdAt: '2024-08-05T08:45:00Z',
  },
  {
    id: 5,
    name: 'Robert Brown',
    email: 'robert.b@example.com',
    role: 'admin' as const,
    status: 'active' as const,
    lastLogin: '2026-02-02T09:15:00Z',
    createdAt: '2024-02-28T14:00:00Z',
  },
];

/**
 * Mock system statistics
 */
const systemStats = {
  totalUsers: 156,
  activeUsers: 142,
  totalPredictions: 12847,
  alertsTriggered: 89,
  systemUptime: 99.97,
  apiResponseTime: 145,
  databaseSize: '2.4 GB',
  storageUsed: 68, // percentage as number
  lastBackup: '2026-02-02T04:00:00Z',
  serverStatus: 'healthy' as const,
};

/**
 * Get initials from user name
 */
function getInitials(name: string): string {
  return name
    .split(' ')
    .map((part) => part[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);
}

/**
 * Format date for display
 */
function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

/**
 * Status badge component
 */
function StatusBadge({ status }: { status: 'active' | 'inactive' }) {
  return (
    <Badge
      variant={status === 'active' ? 'default' : 'secondary'}
      className={cn(
        status === 'active'
          ? 'bg-green-100 text-green-800 hover:bg-green-100'
          : 'bg-gray-100 text-gray-600 hover:bg-gray-100'
      )}
    >
      {status === 'active' ? (
        <CheckCircle className="h-3 w-3 mr-1" />
      ) : (
        <Clock className="h-3 w-3 mr-1" />
      )}
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </Badge>
  );
}

/**
 * Role badge component
 */
function RoleBadge({ role }: { role: 'admin' | 'user' }) {
  return (
    <Badge
      variant={role === 'admin' ? 'default' : 'outline'}
      className={cn(
        role === 'admin'
          ? 'bg-primary/10 text-primary hover:bg-primary/10'
          : ''
      )}
    >
      {role === 'admin' && <Shield className="h-3 w-3 mr-1" />}
      {role.charAt(0).toUpperCase() + role.slice(1)}
    </Badge>
  );
}

/**
 * Stat card component
 */
function StatCard({
  icon: Icon,
  label,
  value,
  description,
  trend,
}: {
  icon: React.ElementType;
  label: string;
  value: string | number;
  description?: string;
  trend?: { value: number; isPositive: boolean };
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
              <p className="text-2xl font-bold">{value}</p>
            </div>
          </div>
          {trend && (
            <div
              className={cn(
                'flex items-center text-sm',
                trend.isPositive ? 'text-green-600' : 'text-red-600'
              )}
            >
              <TrendingUp
                className={cn(
                  'h-4 w-4 mr-1',
                  !trend.isPositive && 'rotate-180'
                )}
              />
              {trend.value}%
            </div>
          )}
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
      navigate('/', { replace: true });
    }
  }, [user, navigate]);

  // Show nothing while checking permissions
  if (!user || user.role !== 'admin') {
    return null;
  }

  return (
    <div className="container mx-auto space-y-8 py-8 px-4">
      {/* Page Header */}
      <div className="space-y-2">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
            <Shield className="h-5 w-5 text-primary" />
          </div>
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Admin Panel</h1>
            <p className="text-muted-foreground">
              System administration and user management
            </p>
          </div>
        </div>
      </div>

      {/* System Stats Grid */}
      <div>
        <h2 className="text-xl font-semibold mb-4">System Overview</h2>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <StatCard
            icon={Users}
            label="Total Users"
            value={systemStats.totalUsers}
            description={`${systemStats.activeUsers} active`}
            trend={{ value: 12, isPositive: true }}
          />
          <StatCard
            icon={Activity}
            label="Total Predictions"
            value={systemStats.totalPredictions.toLocaleString()}
            trend={{ value: 8, isPositive: true }}
          />
          <StatCard
            icon={AlertTriangle}
            label="Alerts Triggered"
            value={systemStats.alertsTriggered}
            description="This month"
          />
          <StatCard
            icon={Server}
            label="System Uptime"
            value={`${systemStats.systemUptime}%`}
            description="Last 30 days"
          />
        </div>
      </div>

      {/* Additional Stats */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base flex items-center gap-2">
              <Database className="h-4 w-4" />
              Database Status
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Size</span>
              <span className="font-medium">{systemStats.databaseSize}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Last Backup</span>
              <span className="font-medium">
                {formatDate(systemStats.lastBackup)}
              </span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base flex items-center gap-2">
              <Server className="h-4 w-4" />
              Server Health
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Status</span>
              <Badge className="bg-green-100 text-green-800 hover:bg-green-100">
                <CheckCircle className="h-3 w-3 mr-1" />
                Healthy
              </Badge>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">API Response</span>
              <span className="font-medium">{systemStats.apiResponseTime}ms</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base flex items-center gap-2">
              <HardDrive className="h-4 w-4" />
              Storage
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Used</span>
              <span className="font-medium">{systemStats.storageUsed}%</span>
            </div>
            {/* Progress bar */}
            <div className="w-full bg-muted rounded-full h-2 mt-2">
              <div className="bg-primary h-2 rounded-full w-2/3" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* User Management Table */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Users className="h-5 w-5" />
                User Management
              </CardTitle>
              <CardDescription>
                Manage user accounts and permissions
              </CardDescription>
            </div>
            <Button size="sm">
              Add User
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>User</TableHead>
                <TableHead>Role</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Last Login</TableHead>
                <TableHead>Created</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {mockUsers.map((mockUser) => (
                <TableRow key={mockUser.id}>
                  <TableCell>
                    <div className="flex items-center gap-3">
                      <Avatar className="h-8 w-8">
                        <AvatarImage src="" alt={mockUser.name} />
                        <AvatarFallback className="text-xs">
                          {getInitials(mockUser.name)}
                        </AvatarFallback>
                      </Avatar>
                      <div>
                        <p className="font-medium">{mockUser.name}</p>
                        <p className="text-xs text-muted-foreground">
                          {mockUser.email}
                        </p>
                      </div>
                    </div>
                  </TableCell>
                  <TableCell>
                    <RoleBadge role={mockUser.role} />
                  </TableCell>
                  <TableCell>
                    <StatusBadge status={mockUser.status} />
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {formatDate(mockUser.lastLogin)}
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {formatDate(mockUser.createdAt)}
                  </TableCell>
                  <TableCell className="text-right">
                    <Button variant="ghost" size="sm">
                      Edit
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
