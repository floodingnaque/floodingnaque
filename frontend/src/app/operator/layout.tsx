/**
 * Operator / LGU Dashboard Layout
 *
 * Command-center grade layout for MDRRMO staff and barangay-level officers.
 * Dense information layout with real-time connection status, SLA timer,
 * and quick-action nav bar. Responsive for tablets in the field.
 */

import {
  AlertTriangle,
  BarChart3,
  Bell,
  ChevronLeft,
  ChevronRight,
  ClipboardList,
  Cloud,
  FileText,
  Home,
  LifeBuoy,
  LogOut,
  Map,
  Menu,
  Moon,
  Radio,
  Send,
  Settings,
  Sun,
  Users,
  Waves,
  Zap,
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

// ─── Navigation Section Types ────────────────────────────────────────────────

interface NavItem {
  to: string;
  icon: React.ElementType;
  label: string;
  badge?: number;
}

interface NavSection {
  title: string;
  items: NavItem[];
}

// ─── Navigation Configuration ────────────────────────────────────────────────

const NAV_SECTIONS: NavSection[] = [
  {
    title: "Situational Awareness",
    items: [
      { to: "/operator", icon: Home, label: "Overview" },
      { to: "/operator/map", icon: Map, label: "Live Map" },
      { to: "/operator/weather", icon: Cloud, label: "Weather Monitor" },
      { to: "/operator/tides", icon: Waves, label: "Tidal & River Levels" },
    ],
  },
  {
    title: "Incident Operations",
    items: [
      {
        to: "/operator/incidents",
        icon: ClipboardList,
        label: "Active Incidents",
      },
      { to: "/operator/alerts", icon: Bell, label: "Alert Management" },
      { to: "/operator/broadcast", icon: Send, label: "Broadcast Center" },
    ],
  },
  {
    title: "Community",
    items: [
      { to: "/operator/reports", icon: FileText, label: "Community Reports" },
      {
        to: "/operator/evacuation",
        icon: LifeBuoy,
        label: "Evacuation Centers",
      },
      { to: "/operator/residents", icon: Users, label: "Resident Registry" },
    ],
  },
  {
    title: "Tools & Reports",
    items: [
      { to: "/operator/predict", icon: Zap, label: "Flood Prediction" },
      {
        to: "/operator/analytics",
        icon: BarChart3,
        label: "Analytics & Trends",
      },
      { to: "/operator/aar", icon: Radio, label: "After-Action Reports" },
    ],
  },
  {
    title: "Account",
    items: [{ to: "/operator/settings", icon: Settings, label: "Settings" }],
  },
];

// ─── Helpers ────────────────────────────────────────────────────────────────

function getInitials(name?: string | null): string {
  if (!name?.trim()) return "?";
  return name
    .trim()
    .split(" ")
    .filter(Boolean)
    .map((p) => p[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);
}

const PAGE_TITLES: Record<string, string> = {
  "/operator": "Operations Overview",
  "/operator/map": "Live Flood Map",
  "/operator/weather": "Weather Monitor",
  "/operator/tides": "Tidal & River Levels",
  "/operator/incidents": "Active Incidents",
  "/operator/alerts": "Alert Management",
  "/operator/broadcast": "Broadcast Center",
  "/operator/reports": "Community Reports",
  "/operator/evacuation": "Evacuation Centers",
  "/operator/residents": "Resident Registry",
  "/operator/predict": "Flood Prediction Tool",
  "/operator/analytics": "Analytics & Trends",
  "/operator/aar": "After-Action Reports",
  "/operator/settings": "Settings",
};

// ─── Sidebar Navigation ─────────────────────────────────────────────────────

function OperatorSidebarNav({
  collapsed,
  onNavClick,
}: {
  collapsed: boolean;
  onNavClick?: () => void;
}) {
  const user = useUser();
  const unreadCount = useUnreadCount();
  const clearAuth = useAuthStore((s) => s.clearAuth);
  const navigate = useNavigate();
  const [showLogout, setShowLogout] = useState(false);

  const confirmLogout = useCallback(() => {
    authApi.logout().catch(() => {});
    clearAuth();
    setShowLogout(false);
    navigate("/login");
  }, [clearAuth, navigate]);

  return (
    <nav className="flex flex-col h-full" aria-label="Operator navigation">
      <div className="flex-1 py-3 overflow-y-auto">
        {NAV_SECTIONS.map((section) => (
          <div key={section.title} className="mb-1">
            {!collapsed && (
              <div className="px-4 py-2">
                <span className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground/60">
                  {section.title}
                </span>
              </div>
            )}
            {collapsed && (
              <div className="mx-2 my-1 border-t border-border/20" />
            )}
            <div className="space-y-0.5">
              {section.items.map((item) => {
                const Icon = item.icon;
                const badgeCount =
                  item.to === "/operator/alerts" ? unreadCount : item.badge;

                return (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    end={item.to === "/operator"}
                    onClick={onNavClick}
                    className={({ isActive }) =>
                      cn(
                        "group relative flex items-center gap-3 px-3 py-2 mx-2 rounded-lg text-sm font-medium transition-all duration-200",
                        "hover:bg-accent hover:text-accent-foreground",
                        isActive
                          ? "bg-primary/10 text-primary font-semibold shadow-sm border border-primary/15"
                          : "text-muted-foreground",
                        collapsed && "justify-center px-2",
                      )
                    }
                  >
                    <Icon className="h-4.5 w-4.5 shrink-0" />
                    {!collapsed && (
                      <>
                        <span className="flex-1 truncate">{item.label}</span>
                        {badgeCount != null && badgeCount > 0 && (
                          <Badge
                            variant="destructive"
                            className="ml-auto h-5 min-w-5 flex items-center justify-center px-1.5 text-xs"
                          >
                            {badgeCount > 99 ? "99+" : badgeCount}
                          </Badge>
                        )}
                      </>
                    )}
                    {collapsed && badgeCount != null && badgeCount > 0 && (
                      <span className="absolute -top-1 -right-1 h-4 w-4 rounded-full bg-destructive text-[10px] text-destructive-foreground flex items-center justify-center">
                        {badgeCount > 9 ? "9+" : badgeCount}
                      </span>
                    )}
                  </NavLink>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      {/* User Section */}
      <div className="mt-auto border-t border-border/30 pt-3 pb-3">
        {user && (
          <div className={cn("px-3", collapsed && "px-2")}>
            {!collapsed ? (
              <div className="flex items-center gap-3 mb-3 p-2 rounded-xl bg-muted/30">
                <Avatar className="h-8 w-8 ring-2 ring-orange-500/20">
                  {user.avatarUrl && (
                    <AvatarImage src={user.avatarUrl} alt={user.name} />
                  )}
                  <AvatarFallback className="text-xs">
                    {getInitials(user.name)}
                  </AvatarFallback>
                </Avatar>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{user.name}</p>
                  <p className="text-[11px] text-muted-foreground">Operator</p>
                </div>
              </div>
            ) : (
              <div className="flex justify-center mb-3">
                <Avatar className="h-8 w-8">
                  <AvatarFallback className="text-xs">
                    {getInitials(user.name)}
                  </AvatarFallback>
                </Avatar>
              </div>
            )}
            <Button
              variant="outline"
              size={collapsed ? "icon" : "sm"}
              className={cn(
                "w-full border-border/40 hover:bg-destructive/10 hover:text-destructive hover:border-destructive/30 transition-all",
                collapsed && "w-8 h-8",
              )}
              onClick={() => setShowLogout(true)}
            >
              <LogOut className="h-4 w-4" />
              {!collapsed && <span className="ml-2">Logout</span>}
            </Button>
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

// ─── Main Layout ────────────────────────────────────────────────────────────

export function OperatorLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const user = useUser();
  const theme = useTheme();
  const sidebarCollapsed = useSidebarCollapsed();
  const sidebarOpen = useSidebarOpen();
  const { toggleTheme, collapseSidebar, setSidebarOpen } = useUIActions();
  const clearAuth = useAuthStore((s) => s.clearAuth);
  const [showLogoutDialog, setShowLogoutDialog] = useState(false);
  const unreadCount = useUnreadCount();

  const { isConnected, reconnect } = useAlertStream({
    enabled: import.meta.env.VITE_ENABLE_SSE === "true",
  });

  const confirmLogout = useCallback(() => {
    authApi.logout().catch(() => {});
    clearAuth();
    setShowLogoutDialog(false);
    navigate("/login");
  }, [clearAuth, navigate]);

  useEffect(() => {
    setSidebarOpen(false);
  }, [location.pathname, setSidebarOpen]);

  useEffect(() => {
    document.getElementById("main-content")?.focus({ preventScroll: true });
  }, [location.pathname]);

  const pageTitle = PAGE_TITLES[location.pathname] || "Operator Dashboard";

  useEffect(() => {
    document.title = `${pageTitle} | Floodingnaque Ops`;
  }, [pageTitle]);

  return (
    <div className="min-h-screen bg-background">
      <RouteProgress />

      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:z-100 focus:top-2 focus:left-2 focus:px-4 focus:py-2 focus:bg-primary focus:text-primary-foreground focus:rounded-md focus:shadow-lg"
      >
        Skip to main content
      </a>

      <LiveAlertsBanner
        onViewAll={() => navigate("/operator/alerts")}
        className="z-50"
      />

      <div className="flex h-screen">
        {/* Desktop Sidebar */}
        <aside
          className={cn(
            "hidden md:flex flex-col border-r border-border/50 bg-card transition-all duration-300",
            sidebarCollapsed ? "w-16" : "w-64",
          )}
        >
          {/* Orange accent for operator tier */}
          <div className="h-1 w-full bg-linear-to-r from-orange-500/60 via-orange-500 to-orange-500/60" />

          {/* Logo */}
          <div
            className={cn(
              "flex items-center h-14 px-4 border-b border-border/30",
              sidebarCollapsed && "justify-center px-2",
            )}
          >
            <div className="flex items-center gap-2">
              <div className="p-1.5 rounded-lg bg-orange-500/10 ring-1 ring-orange-500/20">
                <FloodIcon className="h-5 w-5 text-orange-500" />
              </div>
              {!sidebarCollapsed && (
                <div className="flex flex-col">
                  <span className="font-bold text-sm tracking-tight text-orange-600 dark:text-orange-400">
                    Floodingnaque
                  </span>
                  <span className="text-[10px] text-muted-foreground uppercase tracking-wider">
                    Operations
                  </span>
                </div>
              )}
            </div>
          </div>

          <OperatorSidebarNav collapsed={sidebarCollapsed} />

          {/* Collapse Toggle */}
          <div className="border-t border-border/30 p-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={collapseSidebar}
              className={cn("w-full", sidebarCollapsed && "justify-center")}
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
          {/* Top Header */}
          <header className="h-14 border-b border-border/50 bg-card flex items-center justify-between px-4 sm:px-6">
            <div className="flex items-center gap-3">
              {/* Mobile Menu */}
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
                  <div className="h-1 w-full bg-linear-to-r from-orange-500/60 via-orange-500 to-orange-500/60" />
                  <SheetHeader className="h-14 px-4 border-b border-border/30 flex flex-row items-center">
                    <div className="flex items-center gap-2">
                      <div className="p-1.5 rounded-lg bg-orange-500/10 ring-1 ring-orange-500/20">
                        <FloodIcon className="h-5 w-5 text-orange-500" />
                      </div>
                      <SheetTitle className="font-bold text-sm text-orange-600 dark:text-orange-400">
                        Floodingnaque Ops
                      </SheetTitle>
                    </div>
                  </SheetHeader>
                  <OperatorSidebarNav
                    collapsed={false}
                    onNavClick={() => setSidebarOpen(false)}
                  />
                </SheetContent>
              </Sheet>

              <h1 className="text-base font-semibold tracking-tight text-foreground">
                {pageTitle}
              </h1>
            </div>

            {/* Right side actions */}
            <div className="flex items-center gap-2">
              <ConnectionStatus
                isConnected={isConnected}
                onReconnect={reconnect}
                showReconnectButton={false}
                className="hidden sm:flex"
              />

              {/* Quick Action: Raise Incident */}
              <Button
                size="sm"
                variant="destructive"
                className="hidden sm:inline-flex h-8 text-xs gap-1"
                onClick={() => navigate("/operator/incidents")}
              >
                <AlertTriangle className="h-3.5 w-3.5" />
                Raise Incident
              </Button>

              {/* Notification Bell */}
              <Button
                variant="ghost"
                size="icon"
                className="relative"
                onClick={() => navigate("/operator/alerts")}
                aria-label="Alerts"
              >
                <Bell className="h-5 w-5" />
                {unreadCount > 0 && (
                  <span className="absolute -top-0.5 -right-0.5 h-4 min-w-4 rounded-full bg-destructive text-[10px] text-destructive-foreground flex items-center justify-center px-1">
                    {unreadCount > 99 ? "99+" : unreadCount}
                  </span>
                )}
              </Button>

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

              {user && (
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="rounded-full"
                      aria-label="User menu"
                    >
                      <Avatar className="h-8 w-8 ring-2 ring-orange-500/20">
                        {user.avatarUrl && (
                          <AvatarImage src={user.avatarUrl} alt={user.name} />
                        )}
                        <AvatarFallback className="text-xs bg-orange-500/10">
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
                    <DropdownMenuItem
                      onClick={() => navigate("/operator/settings")}
                    >
                      <Settings className="h-4 w-4 mr-2" />
                      Settings
                    </DropdownMenuItem>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem
                      onClick={() => setShowLogoutDialog(true)}
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

          {/* Content */}
          <main
            id="main-content"
            className="flex-1 overflow-auto bg-background"
            tabIndex={-1}
          >
            <Outlet />
          </main>
        </div>
      </div>

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

export default OperatorLayout;
