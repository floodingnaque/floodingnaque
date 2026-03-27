/**
 * App Layout Component
 *
 * Main application shell with collapsible sidebar navigation,
 * responsive header, and content area. Integrates SSE alerts.
 */

import { useQueryClient } from "@tanstack/react-query";
import {
  Activity,
  BarChart3,
  Bell,
  Brain,
  ChevronLeft,
  ChevronRight,
  ClipboardList,
  Cloud,
  Database,
  FileText,
  GitBranch,
  HardDrive,
  HeartPulse,
  Home,
  LifeBuoy,
  LogOut,
  Map,
  MapPin,
  Menu,
  MessageSquare,
  Moon,
  Scale,
  ScrollText,
  Settings,
  Shield,
  ShieldCheck,
  SlidersHorizontal,
  Sun,
  User,
  Users,
  Users2,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { cn } from "@/lib/utils";

import { RainEffect } from "@/components/effects/RainEffect";
import { ConfirmDialog } from "@/components/feedback/ConfirmDialog";
import { RouteProgress } from "@/components/feedback/RouteProgress";
import { FloodIcon } from "@/components/icons/FloodIcon";
import { ConnectionStatus } from "@/features/alerts/components/ConnectionStatus";
import { LiveAlertsBanner } from "@/features/alerts/components/LiveAlertsBanner";
import { useAlertStream } from "@/features/alerts/hooks/useAlertStream";
import { authApi } from "@/features/auth/services/authApi";
import {
  useAuthStore,
  useSidebarCollapsed,
  useSidebarOpen,
  useTheme,
  useUIActions,
  useUser,
} from "@/state";
import { useUnreadCount } from "@/state/stores/alertStore";

import type { UserRole } from "@/types";

/**
 * Navigation item interface
 */
interface NavItem {
  to: string;
  icon: React.ElementType;
  label: string;
  badge?: number;
  /** Roles that can see this item. If omitted, visible to all roles. */
  roles?: UserRole[];
}

interface NavSection {
  title: string;
  roles?: UserRole[];
  items: NavItem[];
}

/**
 * Navigation sections configuration
 *
 * Role visibility follows the 3-tier architecture:
 *   user     → Resident  (Dashboard, Map, Prediction, Alerts)
 *   operator → LGU/MDRRMO (+ Analytics, Reports, Alert Management)
 *   admin    → Admin     (+ Model Mgmt, User Mgmt, System Settings, Logs)
 */
const navSections: NavSection[] = [
  {
    title: "Situational Awareness",
    items: [
      { to: "/dashboard", icon: Home, label: "Dashboard" },
      { to: "/map", icon: Map, label: "Flood Map" },
      { to: "/predict", icon: Activity, label: "Prediction" },
      { to: "/alerts", icon: Bell, label: "Alerts" },
    ],
  },
  {
    title: "Community",
    items: [
      { to: "/community", icon: Users2, label: "Community" },
      { to: "/evacuation", icon: LifeBuoy, label: "Evacuation" },
      { to: "/admin/chat", icon: MessageSquare, label: "Barangay Chat" },
    ],
  },
  {
    title: "Operations",
    roles: ["operator", "admin"],
    items: [
      {
        to: "/incidents",
        icon: ClipboardList,
        label: "Incidents",
        roles: ["operator", "admin"],
      },
      {
        to: "/history",
        icon: Cloud,
        label: "Weather History",
        roles: ["operator", "admin"],
      },
      {
        to: "/analytics",
        icon: BarChart3,
        label: "Analytics",
        roles: ["operator", "admin"],
      },
      {
        to: "/reports",
        icon: FileText,
        label: "Reports",
        roles: ["operator", "admin"],
      },
      {
        to: "/compliance",
        icon: Scale,
        label: "Compliance",
        roles: ["operator", "admin"],
      },
    ],
  },
  {
    title: "Administration",
    roles: ["admin"],
    items: [
      { to: "/admin", icon: Shield, label: "Admin Panel", roles: ["admin"] },
      {
        to: "/admin/users",
        icon: Users,
        label: "User Management",
        roles: ["admin"],
      },
      {
        to: "/admin/barangays",
        icon: MapPin,
        label: "Barangays",
        roles: ["admin"],
      },
      {
        to: "/admin/data",
        icon: Database,
        label: "Datasets",
        roles: ["admin"],
      },
      {
        to: "/admin/storage",
        icon: HardDrive,
        label: "Storage",
        roles: ["admin"],
      },
      {
        to: "/admin/models",
        icon: Brain,
        label: "AI Models",
        roles: ["admin"],
      },
    ],
  },
  {
    title: "System",
    roles: ["admin"],
    items: [
      {
        to: "/admin/config",
        icon: SlidersHorizontal,
        label: "Configuration",
        roles: ["admin"],
      },
      {
        to: "/admin/logs",
        icon: ScrollText,
        label: "System Logs",
        roles: ["admin"],
      },
      {
        to: "/admin/security",
        icon: ShieldCheck,
        label: "Security",
        roles: ["admin"],
      },
      {
        to: "/admin/monitoring",
        icon: HeartPulse,
        label: "Monitoring",
        roles: ["admin"],
      },
      {
        to: "/admin/workflow",
        icon: GitBranch,
        label: "LGU Workflow",
        roles: ["admin"],
      },
    ],
  },
  {
    title: "Account",
    items: [{ to: "/settings", icon: Settings, label: "Settings" }],
  },
];

/**
 * Get initials from user name.
 * Safely handles missing or empty names.
 */
function getInitials(name?: string | null): string {
  if (!name || typeof name !== "string") {
    return "?";
  }

  const parts = name
    .trim()
    .split(" ")
    .filter((part) => part.length > 0);

  if (parts.length === 0) {
    return "?";
  }

  return parts
    .map((part) => part[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);
}

/**
 * Page title mapping based on route
 */
const pageTitles: Record<string, string> = {
  "/dashboard": "Dashboard",
  "/map": "Flood Map",
  "/predict": "Flood Risk Prediction",
  "/alerts": "Alerts",
  "/community": "Community Reports",
  "/evacuation": "Evacuation Centers",
  "/history": "Weather History",
  "/analytics": "Analytics & Charts",
  "/reports": "Reports & Export",
  "/settings": "Settings",
  "/admin": "Admin Panel",
  "/admin/users": "User Management",
  "/admin/logs": "System Logs",
  "/admin/barangays": "Barangay Management",
  "/admin/data": "Dataset Management",
  "/admin/storage": "Storage Management",
  "/admin/models": "AI Model Control",
  "/admin/config": "System Configuration",
  "/compliance": "National Framework Compliance",
  "/incidents": "Incident Management",
  "/admin/workflow": "LGU Workflow Management",
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
  const queryClient = useQueryClient();
  const [showLogout, setShowLogout] = useState(false);

  // Prefetch primary query for a route on hover/focus
  const prefetchRoute = useCallback(
    (to: string) => {
      const keyMap: Record<string, readonly unknown[]> = {
        "/dashboard": ["admin", "health"],
        "/alerts": ["admin", "health"],
        "/predict": ["admin", "health"],
      };
      const key = keyMap[to];
      if (key) {
        queryClient.prefetchQuery({
          queryKey: key,
          staleTime: 30_000,
        });
      }
    },
    [queryClient],
  );

  const handleLogout = useCallback(() => {
    setShowLogout(true);
  }, []);

  const confirmLogout = useCallback(() => {
    authApi.logout().catch(() => {
      /* server-side invalidation is best-effort */
    });
    clearAuth();
    setShowLogout(false);
    navigate("/login");
  }, [clearAuth, navigate]);

  return (
    <nav className="flex flex-col h-full" aria-label="Main navigation">
      {/* Navigation Links - organized by section */}
      <div className="flex-1 py-4 space-y-1 overflow-y-auto">
        {navSections.map((section) => {
          // Section-level role filter
          if (
            section.roles &&
            (!user?.role || !section.roles.includes(user.role))
          ) {
            return null;
          }

          const visibleItems = section.items.filter(
            (item) =>
              !item.roles || (user?.role && item.roles.includes(user.role)),
          );
          if (visibleItems.length === 0) return null;

          return (
            <div key={section.title} className="mb-2">
              {!collapsed && (
                <p className="px-4 pt-3 pb-1 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/60">
                  {section.title}
                </p>
              )}
              {collapsed && (
                <div className="mx-3 my-1 border-t border-border/20" />
              )}
              {visibleItems.map((item) => {
                // Resolve chat route per role so each role reaches their own chat layout
                const to =
                  item.to === "/admin/chat" && user?.role !== "admin"
                    ? user?.role === "operator"
                      ? "/operator/chat"
                      : "/resident/chat"
                    : item.to;

                const Icon = item.icon;
                const badgeCount = to === "/alerts" ? unreadCount : item.badge;

                return (
                  <NavLink
                    key={to}
                    to={to}
                    onClick={onNavClick}
                    onMouseEnter={() => prefetchRoute(to)}
                    onFocus={() => prefetchRoute(to)}
                    className={({ isActive }) =>
                      cn(
                        "group relative flex items-center gap-3 px-3 py-2.5 mx-2 rounded-lg text-sm font-medium transition-all duration-200",
                        "hover:bg-accent hover:text-accent-foreground",
                        isActive
                          ? "bg-primary/10 text-primary font-semibold shadow-sm border border-primary/15"
                          : "text-muted-foreground",
                        collapsed && "justify-center px-2",
                      )
                    }
                  >
                    {/* Active indicator bar */}
                    {!collapsed && (
                      <span className="absolute left-0 top-1/2 -translate-y-1/2 h-6 w-1 rounded-r-full bg-primary opacity-0 group-[.active]:opacity-100 transition-opacity" />
                    )}
                    <Icon
                      className={cn(
                        "h-5 w-5 shrink-0 transition-colors",
                        collapsed && "h-5 w-5",
                      )}
                    />
                    {!collapsed && (
                      <>
                        <span className="flex-1">{item.label}</span>
                        {badgeCount && badgeCount > 0 && (
                          <Badge
                            variant="destructive"
                            className="ml-auto h-5 min-w-5 flex items-center justify-center px-1.5 text-xs"
                          >
                            {badgeCount > 99 ? "99+" : badgeCount}
                          </Badge>
                        )}
                      </>
                    )}
                    {collapsed && badgeCount && badgeCount > 0 && (
                      <span className="absolute -top-1 -right-1 h-4 w-4 rounded-full bg-destructive text-[10px] text-destructive-foreground flex items-center justify-center">
                        {badgeCount > 9 ? "9+" : badgeCount}
                      </span>
                    )}
                  </NavLink>
                );
              })}
            </div>
          );
        })}
      </div>

      {/* User Section */}
      <div className="mt-auto border-t border-border/30 pt-4 pb-4">
        {user && (
          <div className={cn("px-3", collapsed && "px-2")}>
            {!collapsed ? (
              <div className="flex items-center gap-3 mb-3 p-2 rounded-xl bg-muted/30">
                <Avatar className="h-9 w-9 ring-2 ring-risk-safe/20">
                  {user.avatarUrl ? (
                    <AvatarImage src={user.avatarUrl} alt={user.name} />
                  ) : null}
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
                  {user.avatarUrl ? (
                    <AvatarImage src={user.avatarUrl} alt={user.name} />
                  ) : null}
                  <AvatarFallback>{getInitials(user.name)}</AvatarFallback>
                </Avatar>
              </div>
            )}
            <Button
              variant="outline"
              size={collapsed ? "icon" : "sm"}
              className={cn(
                "w-full border-border/40 hover:bg-destructive/10 hover:text-destructive hover:border-destructive/30 transition-all duration-200",
                collapsed && "w-9 h-9",
              )}
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
  // Controlled via VITE_ENABLE_SSE env var (defaults to true).
  const { isConnected, reconnect, lastHeartbeat } = useAlertStream({
    enabled: import.meta.env.VITE_ENABLE_SSE !== "false",
  });

  // Handle logout
  const handleLogout = useCallback(() => {
    setShowLogoutDialog(true);
  }, []);

  const confirmLogout = useCallback(() => {
    authApi.logout().catch(() => {
      /* server-side invalidation is best-effort */
    });
    clearAuth();
    setShowLogoutDialog(false);
    navigate("/login");
  }, [clearAuth, navigate]);

  // Navigate to alerts page from banner
  const handleViewAlerts = useCallback(() => {
    navigate("/alerts");
  }, [navigate]);

  // Close mobile sidebar on route change
  useEffect(() => {
    setSidebarOpen(false);
  }, [location.pathname, setSidebarOpen]);

  // Focus management: move focus to main content on route change
  // so screen-reader users don't get stuck in the sidebar.
  useEffect(() => {
    const main = document.getElementById("main-content");
    main?.focus({ preventScroll: true });
  }, [location.pathname]);

  // Get page title from current route
  const pageTitle = pageTitles[location.pathname] || "Floodingnaque";

  // Keep document.title in sync with the current route
  useEffect(() => {
    document.title =
      pageTitle === "Floodingnaque"
        ? "Floodingnaque"
        : `${pageTitle} | Floodingnaque`;
  }, [pageTitle]);

  return (
    <div className="min-h-screen bg-background">
      {/* Route transition progress bar */}
      <RouteProgress />

      {/* Skip Navigation Link */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:z-100 focus:top-2 focus:left-2 focus:px-4 focus:py-2 focus:bg-primary focus:text-primary-foreground focus:rounded-md focus:shadow-lg"
      >
        Skip to main content
      </a>

      {/* Live Alerts Banner */}
      <LiveAlertsBanner onViewAll={handleViewAlerts} className="z-50" />

      <div className="flex h-screen">
        {/* Desktop Sidebar */}
        <aside
          className={cn(
            "hidden md:flex flex-col border-r border-border/50 bg-card transition-all duration-300",
            sidebarCollapsed ? "w-16" : "w-64",
          )}
        >
          {/* Subtle rain accent on sidebar */}
          <RainEffect density={12} opacity={0.04} />

          {/* Gradient accent bar at top */}
          <div className="h-1 w-full bg-linear-to-r from-primary/60 via-primary to-primary/60" />

          {/* Logo/Brand */}
          <div
            className={cn(
              "flex items-center h-16 px-4 border-b border-border/30",
              sidebarCollapsed && "justify-center px-2",
            )}
          >
            <div className="flex items-center gap-2">
              <div className="p-1.5 rounded-lg bg-primary/10 ring-1 ring-primary/20">
                <FloodIcon className="h-6 w-6 text-primary" />
              </div>
              {!sidebarCollapsed && (
                <span className="font-bold text-lg tracking-tight text-primary">
                  Floodingnaque
                </span>
              )}
            </div>
          </div>

          {/* Navigation */}
          <SidebarNav collapsed={sidebarCollapsed} />

          {/* Collapse Toggle */}
          <div className="border-t border-border/30 p-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={collapseSidebar}
              className={cn(
                "w-full",
                sidebarCollapsed && "w-full justify-center",
              )}
              aria-label={
                sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"
              }
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
        <div className="relative flex-1 flex flex-col overflow-hidden">
          {/* Subtle rain accent across all authenticated pages */}
          <RainEffect density={15} opacity={0.03} />
          {/* Top Header Bar */}
          <header className="h-16 border-b border-border/50 bg-card flex items-center justify-between px-4 sm:px-6">
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
                <SheetContent
                  side="left"
                  className="w-72 p-0 bg-card border-border/50"
                >
                  <div className="h-1 w-full bg-linear-to-r from-primary/60 via-primary to-primary/60" />
                  <SheetHeader className="h-16 px-4 border-b border-border/30 flex flex-row items-center">
                    <div className="flex items-center gap-2">
                      <div className="p-1.5 rounded-lg bg-primary/10 ring-1 ring-primary/20">
                        <FloodIcon className="h-6 w-6 text-primary" />
                      </div>
                      <SheetTitle className="font-bold text-lg text-primary">
                        Floodingnaque
                      </SheetTitle>
                    </div>
                  </SheetHeader>
                  <SidebarNav
                    collapsed={false}
                    onNavClick={() => setSidebarOpen(false)}
                  />
                </SheetContent>
              </Sheet>

              {/* Page Title */}
              <h1 className="text-lg font-semibold tracking-tight text-foreground">
                {pageTitle}
              </h1>
            </div>

            {/* Right: Connection Status, Theme Toggle, User Dropdown */}
            <div className="flex items-center gap-2">
              {/* Connection Status */}
              <ConnectionStatus
                isConnected={isConnected}
                onReconnect={reconnect}
                showReconnectButton={false}
                lastHeartbeat={lastHeartbeat}
                className="hidden sm:flex"
              />

              {/* Theme Toggle */}
              <Button
                variant="ghost"
                size="icon"
                onClick={toggleTheme}
                aria-label="Toggle theme"
              >
                {theme === "dark" ? (
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
                      <Avatar className="h-8 w-8 ring-2 ring-primary/20 transition-all hover:ring-primary/40">
                        {user.avatarUrl && (
                          <AvatarImage src={user.avatarUrl} alt={user.name} />
                        )}
                        <AvatarFallback className="text-xs bg-primary/10">
                          {getInitials(user.name)}
                        </AvatarFallback>
                      </Avatar>
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent
                    align="end"
                    className="w-56 bg-card border-border/50"
                  >
                    <DropdownMenuLabel>
                      <div className="flex flex-col">
                        <span className="font-medium">{user.name}</span>
                        <span className="text-xs text-muted-foreground">
                          {user.email}
                        </span>
                      </div>
                    </DropdownMenuLabel>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem onClick={() => navigate("/settings")}>
                      <User className="h-4 w-4 mr-2" />
                      Profile
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => navigate("/settings")}>
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
          <main
            id="main-content"
            className="flex-1 overflow-auto bg-background"
            tabIndex={-1}
          >
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
