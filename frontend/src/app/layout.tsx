/**
 * App Layout Component
 *
 * Main application shell with collapsible sidebar navigation,
 * responsive header, and content area. Integrates SSE alerts.
 */

import { useState, useEffect, useCallback } from 'react';
import { Outlet, NavLink, useNavigate, useLocation } from 'react-router-dom';
import {
  Home,
  Activity,
  Bell,
  Cloud,
  FileText,
  Settings,
  Shield,
  LogOut,
  ChevronLeft,
  ChevronRight,
  Menu,
  Moon,
  Sun,
  Droplets,
  User,
} from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from '@/components/ui/sheet';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { cn } from '@/lib/utils';

import { useSidebarCollapsed, useSidebarOpen, useTheme, useUIActions } from '@/state';
import { useAuthStore, useUser } from '@/state';
import { useAlertStream } from '@/features/alerts/hooks/useAlertStream';
import { ConnectionStatus } from '@/features/alerts/components/ConnectionStatus';
import { LiveAlertsBanner } from '@/features/alerts/components/LiveAlertsBanner';
import { ConfirmDialog } from '@/components/feedback/ConfirmDialog';
import { useUnreadCount } from '@/state/stores/alertStore';

/**
 * Navigation item interface
 */
interface NavItem {
  to: string;
  icon: React.ElementType;
  label: string;
  badge?: number;
  adminOnly?: boolean;
}

/**
 * Navigation items configuration
 */
const navItems: NavItem[] = [
  { to: '/', icon: Home, label: 'Dashboard' },
  { to: '/predict', icon: Activity, label: 'Prediction' },
  { to: '/alerts', icon: Bell, label: 'Alerts' },
  { to: '/history', icon: Cloud, label: 'Weather History' },
  { to: '/reports', icon: FileText, label: 'Reports' },
  { to: '/settings', icon: Settings, label: 'Settings' },
  { to: '/admin', icon: Shield, label: 'Admin', adminOnly: true },
];

/**
 * Get initials from user name.
 * Safely handles missing or empty names.
 */
function getInitials(name?: string | null): string {
  if (!name || typeof name !== 'string') {
    return '?';
  }

  const parts = name
    .trim()
    .split(' ')
    .filter((part) => part.length > 0);

  if (parts.length === 0) {
    return '?';
  }

  return parts
    .map((part) => part[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);
}

/**
 * Page title mapping based on route
 */
const pageTitles: Record<string, string> = {
  '/': 'Dashboard',
  '/predict': 'Flood Risk Prediction',
  '/alerts': 'Alerts',
  '/history': 'Weather History',
  '/reports': 'Reports & Export',
  '/settings': 'Settings',
  '/admin': 'Admin Panel',
};

/**
 * Sidebar Navigation Component
 */
function SidebarNav({
  collapsed,
  onNavClick,
}: {
  collapsed: boolean;
  onNavClick?: () => void;
}) {
  const user = useUser();
  const unreadCount = useUnreadCount();
  const clearAuth = useAuthStore((state) => state.clearAuth);
  const navigate = useNavigate();
  const [showLogout, setShowLogout] = useState(false);

  const handleLogout = useCallback(() => {
    setShowLogout(true);
  }, []);

  const confirmLogout = useCallback(() => {
    clearAuth();
    setShowLogout(false);
    navigate('/login');
  }, [clearAuth, navigate]);

  return (
    <nav className="flex flex-col h-full" aria-label="Main navigation">
      {/* Navigation Links */}
      <div className="flex-1 py-4 space-y-1 overflow-y-auto">
        {navItems.map((item) => {
          // Skip admin-only items if user is not admin
          if (item.adminOnly && user?.role !== 'admin') {
            return null;
          }

          const Icon = item.icon;
          const badgeCount = item.to === '/alerts' ? unreadCount : item.badge;

          return (
            <NavLink
              key={item.to}
              to={item.to}
              onClick={onNavClick}
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-3 px-3 py-2.5 mx-2 rounded-lg text-sm font-medium transition-colors',
                  'hover:bg-accent hover:text-accent-foreground',
                  isActive
                    ? 'bg-primary/10 text-primary'
                    : 'text-muted-foreground',
                  collapsed && 'justify-center px-2'
                )
              }
            >
              <Icon className={cn('h-5 w-5 flex-shrink-0', collapsed && 'h-5 w-5')} />
              {!collapsed && (
                <>
                  <span className="flex-1">{item.label}</span>
                  {badgeCount && badgeCount > 0 && (
                    <Badge
                      variant="destructive"
                      className="ml-auto h-5 min-w-5 flex items-center justify-center px-1.5 text-xs"
                    >
                      {badgeCount > 99 ? '99+' : badgeCount}
                    </Badge>
                  )}
                </>
              )}
              {collapsed && badgeCount && badgeCount > 0 && (
                <span className="absolute -top-1 -right-1 h-4 w-4 rounded-full bg-destructive text-[10px] text-destructive-foreground flex items-center justify-center">
                  {badgeCount > 9 ? '9+' : badgeCount}
                </span>
              )}
            </NavLink>
          );
        })}
      </div>

      {/* User Section */}
      <div className="mt-auto border-t pt-4 pb-4">
        {user && (
          <div className={cn('px-3', collapsed && 'px-2')}>
            {!collapsed ? (
              <div className="flex items-center gap-3 mb-3">
                <Avatar className="h-9 w-9">
                  <AvatarImage src="" alt={user.name} />
                  <AvatarFallback>{getInitials(user.name)}</AvatarFallback>
                </Avatar>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{user.name}</p>
                  <p className="text-xs text-muted-foreground truncate">
                    {user.email}
                  </p>
                </div>
              </div>
            ) : (
              <div className="flex justify-center mb-3">
                <Avatar className="h-9 w-9">
                  <AvatarImage src="" alt={user.name} />
                  <AvatarFallback>{getInitials(user.name)}</AvatarFallback>
                </Avatar>
              </div>
            )}
            <Button
              variant="outline"
              size={collapsed ? 'icon' : 'sm'}
              className={cn('w-full', collapsed && 'w-9 h-9')}
              onClick={handleLogout}
            >
              <LogOut className="h-4 w-4" aria-hidden="true" />
              {!collapsed && <span className="ml-2">Logout</span>}
            </Button>

            {/* Logout Confirmation Dialog */}
            <ConfirmDialog
              open={showLogout}
              onOpenChange={setShowLogout}
              title="Logout"
              description="Are you sure you want to logout?"
              confirmLabel="Logout"
              variant="destructive"
              onConfirm={confirmLogout}
            />
          </div>
        )}
      </div>
    </nav>
  );
}

/**
 * App Layout Component
 */
export function Layout() {
  const navigate = useNavigate();
  const location = useLocation();
  const user = useUser();
  const theme = useTheme();
  const sidebarCollapsed = useSidebarCollapsed();
  const sidebarOpen = useSidebarOpen();
  const { toggleTheme, collapseSidebar, setSidebarOpen } = useUIActions();
  const clearAuth = useAuthStore((state) => state.clearAuth);
  const [showLogoutDialog, setShowLogoutDialog] = useState(false);

  // Start SSE connection for real-time alerts.
  // Disabled in local development to avoid noisy 404s when the
  // backend SSE endpoint is not configured.
  const { isConnected, reconnect } = useAlertStream({
    enabled: false,
  });

  // Handle logout
  const handleLogout = useCallback(() => {
    setShowLogoutDialog(true);
  }, []);

  const confirmLogout = useCallback(() => {
    clearAuth();
    setShowLogoutDialog(false);
    navigate('/login');
  }, [clearAuth, navigate]);

  // Navigate to alerts page from banner
  const handleViewAlerts = useCallback(() => {
    navigate('/alerts');
  }, [navigate]);

  // Close mobile sidebar on route change
  useEffect(() => {
    setSidebarOpen(false);
  }, [location.pathname, setSidebarOpen]);

  // Get page title from current route
  const pageTitle = pageTitles[location.pathname] || 'Floodingnaque';

  return (
    <div className="min-h-screen bg-background">
      {/* Skip Navigation Link */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:z-[100] focus:top-2 focus:left-2 focus:px-4 focus:py-2 focus:bg-primary focus:text-primary-foreground focus:rounded-md focus:shadow-lg"
      >
        Skip to main content
      </a>

      {/* Live Alerts Banner */}
      <LiveAlertsBanner onViewAll={handleViewAlerts} className="z-50" />

      <div className="flex h-screen">
        {/* Desktop Sidebar */}
        <aside
          className={cn(
            'hidden md:flex flex-col border-r bg-card/50 transition-all duration-300',
            sidebarCollapsed ? 'w-16' : 'w-64'
          )}
        >
          {/* Logo/Brand */}
          <div
            className={cn(
              'flex items-center h-16 px-4 border-b',
              sidebarCollapsed && 'justify-center px-2'
            )}
          >
            <div className="flex items-center gap-2">
              <div className="p-1.5 rounded-lg bg-primary/10">
                <Droplets className="h-6 w-6 text-primary" />
              </div>
              {!sidebarCollapsed && (
                <span className="font-bold text-lg tracking-tight">
                  Floodingnaque
                </span>
              )}
            </div>
          </div>

          {/* Navigation */}
          <SidebarNav collapsed={sidebarCollapsed} />

          {/* Collapse Toggle */}
          <div className="border-t p-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={collapseSidebar}
              className={cn('w-full', sidebarCollapsed && 'w-full justify-center')}
              aria-label={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            >
              {sidebarCollapsed ? (
                <ChevronRight className="h-4 w-4" />
              ) : (
                <>
                  <ChevronLeft className="h-4 w-4 mr-2" />
                  <span>Collapse</span>
                </>
              )}
            </Button>
          </div>
        </aside>

        {/* Main Content Area */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Top Header Bar */}
          <header className="h-16 border-b bg-card/50 flex items-center justify-between px-4">
            {/* Left: Mobile Menu + Page Title */}
            <div className="flex items-center gap-3">
              {/* Mobile Menu Toggle */}
              <Sheet open={sidebarOpen} onOpenChange={setSidebarOpen}>
                <SheetTrigger asChild>
                  <Button variant="ghost" size="icon" className="md:hidden">
                    <Menu className="h-5 w-5" />
                    <span className="sr-only">Open menu</span>
                  </Button>
                </SheetTrigger>
                <SheetContent side="left" className="w-72 p-0">
                  <SheetHeader className="h-16 px-4 border-b flex flex-row items-center">
                    <div className="flex items-center gap-2">
                      <div className="p-1.5 rounded-lg bg-primary/10">
                        <Droplets className="h-6 w-6 text-primary" />
                      </div>
                      <SheetTitle className="font-bold text-lg">
                        Floodingnaque
                      </SheetTitle>
                    </div>
                  </SheetHeader>
                  <SidebarNav collapsed={false} onNavClick={() => setSidebarOpen(false)} />
                </SheetContent>
              </Sheet>

              {/* Page Title */}
              <h1 className="text-lg font-semibold tracking-tight">{pageTitle}</h1>
            </div>

            {/* Right: Connection Status, Theme Toggle, User Dropdown */}
            <div className="flex items-center gap-2">
              {/* Connection Status */}
              <ConnectionStatus
                isConnected={isConnected}
                onReconnect={reconnect}
                showReconnectButton={false}
                className="hidden sm:flex"
              />

              {/* Theme Toggle */}
              <Button
                variant="ghost"
                size="icon"
                onClick={toggleTheme}
                aria-label="Toggle theme"
              >
                {theme === 'dark' ? (
                  <Sun className="h-5 w-5" />
                ) : (
                  <Moon className="h-5 w-5" />
                )}
              </Button>

              {/* User Avatar Dropdown */}
              {user && (
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="rounded-full"
                      aria-label="User menu"
                    >
                      <Avatar className="h-8 w-8">
                        <AvatarImage src="" alt={user.name} />
                        <AvatarFallback className="text-xs">
                          {getInitials(user.name)}
                        </AvatarFallback>
                      </Avatar>
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" className="w-56">
                    <DropdownMenuLabel>
                      <div className="flex flex-col">
                        <span className="font-medium">{user.name}</span>
                        <span className="text-xs text-muted-foreground">
                          {user.email}
                        </span>
                      </div>
                    </DropdownMenuLabel>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem onClick={() => navigate('/settings')}>
                      <User className="h-4 w-4 mr-2" />
                      Profile
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => navigate('/settings')}>
                      <Settings className="h-4 w-4 mr-2" />
                      Settings
                    </DropdownMenuItem>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem
                      onClick={handleLogout}
                      className="text-destructive"
                    >
                      <LogOut className="h-4 w-4 mr-2" />
                      Logout
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              )}
            </div>
          </header>

          {/* Main Content */}
          <main id="main-content" className="flex-1 overflow-auto" tabIndex={-1}>
            <Outlet />
          </main>
        </div>
      </div>

      {/* Logout Confirmation Dialog */}
      <ConfirmDialog
        open={showLogoutDialog}
        onOpenChange={setShowLogoutDialog}
        title="Logout"
        description="Are you sure you want to logout?"
        confirmLabel="Logout"
        variant="destructive"
        onConfirm={confirmLogout}
      />
    </div>
  );
}

export default Layout;
