/**
 * Resident Dashboard Layout
 *
 * Citizen-friendly layout with bottom tab navigation on mobile
 * and a left sidebar on desktop. Clean, spacious, high contrast.
 * Designed for smartphone-first access during flood emergencies.
 */

import {
  AlertTriangle,
  Bell,
  BookOpen,
  ChevronLeft,
  ChevronRight,
  ClipboardList,
  FileText,
  Heart,
  Home,
  LifeBuoy,
  LogOut,
  Map,
  Menu,
  MessageSquare,
  Moon,
  Phone,
  Route,
  Settings,
  ShieldCheck,
  Sun,
  User,
  Users,
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

// ─── Navigation Types ────────────────────────────────────────────────────────

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

// ─── Bottom Tab Items (Mobile) ───────────────────────────────────────────────

const BOTTOM_TABS: NavItem[] = [
  { to: "/resident", icon: Home, label: "Home" },
  { to: "/resident/map", icon: Map, label: "Map" },
  { to: "/resident/alerts", icon: Bell, label: "Alerts" },
  { to: "/resident/report", icon: ClipboardList, label: "Reports" },
  { to: "/resident/settings", icon: User, label: "Profile" },
];

// ─── Sidebar Sections (Desktop/Tablet) ──────────────────────────────────────

const NAV_SECTIONS: NavSection[] = [
  {
    title: "My Safety",
    items: [
      { to: "/resident", icon: Home, label: "Overview" },
      { to: "/resident/risk", icon: ShieldCheck, label: "My Flood Risk" },
      { to: "/resident/map", icon: Map, label: "Live Map" },
    ],
  },
  {
    title: "Alerts & Emergency",
    items: [
      { to: "/resident/alerts", icon: Bell, label: "Active Alerts" },
      { to: "/resident/emergency", icon: Phone, label: "Emergency Contacts" },
      {
        to: "/resident/evacuation",
        icon: LifeBuoy,
        label: "Evacuation Centers",
      },
    ],
  },
  {
    title: "Community",
    items: [
      { to: "/resident/report", icon: AlertTriangle, label: "Report Flood" },
      { to: "/resident/community", icon: Users, label: "Community Reports" },
      { to: "/resident/my-reports", icon: FileText, label: "My Reports" },
      { to: "/resident/chat", icon: MessageSquare, label: "Barangay Chat" },
    ],
  },
  {
    title: "Resources",
    items: [
      { to: "/resident/guide", icon: BookOpen, label: "Flood Safety Guide" },
      { to: "/resident/plan", icon: Route, label: "Evacuation Plan" },
      { to: "/resident/profile/household", icon: Heart, label: "My Household" },
    ],
  },
  {
    title: "Account",
    items: [{ to: "/resident/settings", icon: Settings, label: "Settings" }],
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
  "/resident": "Home",
  "/resident/risk": "My Flood Risk",
  "/resident/map": "Live Map",
  "/resident/alerts": "Active Alerts",
  "/resident/emergency": "Emergency Contacts",
  "/resident/evacuation": "Evacuation Centers",
  "/resident/report": "Report Flood",
  "/resident/community": "Community Reports",
  "/resident/my-reports": "My Reports",
  "/resident/guide": "Flood Safety Guide",
  "/resident/plan": "My Evacuation Plan",
  "/resident/profile/household": "My Household Profile",
  "/resident/chat": "Barangay Chat",
  "/resident/settings": "Settings",
};

// ─── Desktop Sidebar Navigation ─────────────────────────────────────────────

function ResidentSidebarNav({
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
    <nav className="flex flex-col h-full" aria-label="Resident navigation">
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
                  item.to === "/resident/alerts" ? unreadCount : item.badge;

                return (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    end={item.to === "/resident"}
                    onClick={onNavClick}
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
                    <Icon className="h-5 w-5 shrink-0" />
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
                <Avatar className="h-9 w-9 ring-2 ring-primary/20">
                  {user.avatarUrl && (
                    <AvatarImage src={user.avatarUrl} alt={user.name} />
                  )}
                  <AvatarFallback className="text-xs">
                    {getInitials(user.name)}
                  </AvatarFallback>
                </Avatar>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{user.name}</p>
                  <p className="text-[11px] text-muted-foreground">Resident</p>
                </div>
              </div>
            ) : (
              <div className="flex justify-center mb-3">
                <Avatar className="h-9 w-9">
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
                "w-full border-border/40 hover:bg-destructive/10 hover:text-destructive transition-all",
                collapsed && "w-9 h-9",
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

// ─── Bottom Tab Bar (Mobile) ────────────────────────────────────────────────

function BottomTabBar() {
  const unreadCount = useUnreadCount();

  return (
    <nav
      className="md:hidden fixed bottom-0 inset-x-0 z-40 bg-card border-t border-border/50 safe-area-bottom"
      aria-label="Mobile navigation"
    >
      <div className="flex items-center justify-around h-16 px-1">
        {BOTTOM_TABS.map((tab) => {
          const Icon = tab.icon;
          const badgeCount =
            tab.to === "/resident/alerts" ? unreadCount : undefined;

          return (
            <NavLink
              key={tab.to}
              to={tab.to}
              end={tab.to === "/resident"}
              className={({ isActive }) =>
                cn(
                  "flex flex-col items-center justify-center gap-0.5 min-w-14 py-1 px-2 rounded-lg transition-colors",
                  isActive
                    ? "text-primary"
                    : "text-muted-foreground hover:text-foreground",
                )
              }
            >
              <div className="relative">
                <Icon className="h-5 w-5" />
                {badgeCount != null && badgeCount > 0 && (
                  <span className="absolute -top-1.5 -right-2 h-4 min-w-4 rounded-full bg-destructive text-[10px] text-destructive-foreground flex items-center justify-center px-0.5">
                    {badgeCount > 9 ? "9+" : badgeCount}
                  </span>
                )}
              </div>
              <span className="text-[10px] font-medium leading-tight">
                {tab.label}
              </span>
            </NavLink>
          );
        })}
      </div>
    </nav>
  );
}

// ─── Main Layout ────────────────────────────────────────────────────────────

export function ResidentLayout() {
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
    enabled: import.meta.env.VITE_ENABLE_SSE !== "false",
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

  const pageTitle = PAGE_TITLES[location.pathname] || "Resident Dashboard";

  useEffect(() => {
    document.title =
      pageTitle === "Home"
        ? "Floodingnaque — My Safety Dashboard"
        : `${pageTitle} | Floodingnaque`;
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

      <div className="flex h-screen">
        {/* Desktop Sidebar */}
        <aside
          className={cn(
            "hidden md:flex flex-col border-r border-border/50 bg-card transition-all duration-300",
            sidebarCollapsed ? "w-16" : "w-64",
          )}
        >
          {/* Green accent for resident tier */}
          <div className="h-1 w-full bg-linear-to-r from-emerald-500/60 via-emerald-500 to-emerald-500/60" />

          {/* Logo */}
          <div
            className={cn(
              "flex items-center h-14 px-4 border-b border-border/30",
              sidebarCollapsed && "justify-center px-2",
            )}
          >
            <NavLink to="/resident" className="flex items-center gap-2">
              <div className="p-1.5 rounded-lg bg-emerald-500/10 ring-1 ring-emerald-500/20">
                <FloodIcon className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
              </div>
              {!sidebarCollapsed && (
                <div className="flex flex-col">
                  <span className="font-bold text-sm tracking-tight text-emerald-600 dark:text-emerald-400">
                    Floodingnaque
                  </span>
                  <span className="text-[10px] text-muted-foreground uppercase tracking-wider">
                    My Safety
                  </span>
                </div>
              )}
            </NavLink>
          </div>

          <ResidentSidebarNav collapsed={sidebarCollapsed} />

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

        {/* Main Content */}
        <div className="relative flex-1 flex flex-col overflow-hidden">
          {/* Top Header */}
          <header className="h-14 border-b border-border/50 bg-card flex items-center justify-between px-4 sm:px-6">
            <div className="flex items-center gap-3">
              {/* Mobile Menu (hamburger for full sidebar access) */}
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
                  <div className="h-1 w-full bg-linear-to-r from-emerald-500/60 via-emerald-500 to-emerald-500/60" />
                  <SheetHeader className="h-14 px-4 border-b border-border/30 flex flex-row items-center">
                    <div className="flex items-center gap-2">
                      <div className="p-1.5 rounded-lg bg-emerald-500/10 ring-1 ring-emerald-500/20">
                        <FloodIcon className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
                      </div>
                      <SheetTitle className="font-bold text-sm text-emerald-600 dark:text-emerald-400">
                        Floodingnaque
                      </SheetTitle>
                    </div>
                  </SheetHeader>
                  <ResidentSidebarNav
                    collapsed={false}
                    onNavClick={() => setSidebarOpen(false)}
                  />
                </SheetContent>
              </Sheet>

              <h1 className="text-base font-semibold tracking-tight text-foreground">
                {pageTitle}
              </h1>
            </div>

            {/* Right side */}
            <div className="flex items-center gap-2">
              <ConnectionStatus
                isConnected={isConnected}
                onReconnect={reconnect}
                showReconnectButton={false}
                className="hidden sm:flex"
              />

              {/* Notification Bell */}
              <Button
                variant="ghost"
                size="icon"
                className="relative"
                onClick={() => navigate("/resident/alerts")}
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
                      <Avatar className="h-8 w-8 ring-2 ring-emerald-500/20">
                        {user.avatarUrl && (
                          <AvatarImage src={user.avatarUrl} alt={user.name} />
                        )}
                        <AvatarFallback className="text-xs bg-emerald-500/10">
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
                      onClick={() => navigate("/resident/settings")}
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

          {/* Content (with bottom padding for mobile tab bar) */}
          <main
            id="main-content"
            className="flex-1 overflow-auto bg-background pb-20 md:pb-0"
            tabIndex={-1}
          >
            <Outlet />
          </main>
        </div>
      </div>

      {/* Mobile Bottom Tab Bar */}
      <BottomTabBar />

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

export default ResidentLayout;
