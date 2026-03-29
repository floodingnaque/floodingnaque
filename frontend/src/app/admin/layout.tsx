/**
 * Admin / System Control Layout
 *
 * Dedicated layout for system administrators with distinct violet branding.
 * Full sidebar navigation with categorized sections for system management,
 * user administration, ML model control, and monitoring.
 */

import {
  Activity,
  Bell,
  ChevronLeft,
  ChevronRight,
  Cloud,
  Cpu,
  Database,
  FileText,
  HardDrive,
  Home,
  LogOut,
  Map,
  Menu,
  MessageSquare,
  Moon,
  ScrollText,
  Settings,
  Shield,
  Sun,
  Users,
  Workflow,
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
import { authApi } from "@/features/auth/services/authApi";
import { useNotificationAutoPrompt } from "@/hooks/useNotificationAutoPrompt";
import {
  useClearAuth,
  useSidebarCollapsed,
  useSidebarOpen,
  useTheme,
  useUIActions,
  useUser,
} from "@/state";

// ─── Navigation Types ────────────────────────────────────────────────────────

interface NavItem {
  to: string;
  icon: React.ElementType;
  label: string;
}

interface NavSection {
  title: string;
  items: NavItem[];
}

// ─── Navigation Configuration ────────────────────────────────────────────────

const NAV_SECTIONS: NavSection[] = [
  {
    title: "Dashboard",
    items: [
      { to: "/admin", icon: Home, label: "System Overview" },
      { to: "/admin/monitoring", icon: Activity, label: "Monitoring" },
    ],
  },
  {
    title: "User Management",
    items: [
      { to: "/admin/users", icon: Users, label: "Users & Roles" },
      { to: "/admin/workflow", icon: Workflow, label: "LGU Workflows" },
      { to: "/admin/security", icon: Shield, label: "Security" },
    ],
  },
  {
    title: "Data & AI Model",
    items: [
      { to: "/admin/models", icon: Cpu, label: "AI Model Control" },
      { to: "/admin/data", icon: Database, label: "Datasets" },
      { to: "/admin/barangays", icon: Map, label: "Barangays" },
      { to: "/admin/sensor", icon: Cloud, label: "Sensor Data" },
    ],
  },
  {
    title: "Communications",
    items: [
      { to: "/admin/reports", icon: FileText, label: "Community Reports" },
      { to: "/admin/alerts", icon: Bell, label: "Alert Management" },
      { to: "/admin/chat", icon: MessageSquare, label: "Barangay Chat" },
    ],
  },
  {
    title: "System",
    items: [
      { to: "/admin/config", icon: Settings, label: "Configuration" },
      { to: "/admin/storage", icon: HardDrive, label: "Storage" },
      { to: "/admin/logs", icon: ScrollText, label: "System Logs" },
    ],
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
  "/admin": "System Overview",
  "/admin/monitoring": "System Monitoring",
  "/admin/users": "Users & Roles",
  "/admin/workflow": "LGU Workflows",
  "/admin/security": "Security",
  "/admin/models": "AI Model Control",
  "/admin/data": "Datasets",
  "/admin/barangays": "Barangay Management",
  "/admin/sensor": "Sensor Data",
  "/admin/alerts": "Alert Management",
  "/admin/reports": "Community Reports",
  "/admin/chat": "Barangay Chat",
  "/admin/config": "System Configuration",
  "/admin/storage": "Storage Management",
  "/admin/logs": "System Logs",
};

// ─── Sidebar Navigation ─────────────────────────────────────────────────────

function AdminSidebarNav({
  collapsed,
  onNavClick,
}: {
  collapsed: boolean;
  onNavClick?: () => void;
}) {
  const user = useUser();
  const clearAuth = useClearAuth();
  const navigate = useNavigate();
  const [showLogout, setShowLogout] = useState(false);

  const confirmLogout = useCallback(() => {
    authApi.logout().catch(() => {});
    clearAuth();
    setShowLogout(false);
    navigate("/login");
  }, [clearAuth, navigate]);

  return (
    <nav className="flex flex-col h-full" aria-label="Admin navigation">
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
                return (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    end={item.to === "/admin"}
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
                      <span className="flex-1 truncate">{item.label}</span>
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
                <Avatar className="h-8 w-8 ring-2 ring-violet-500/20">
                  {user.avatarUrl && (
                    <AvatarImage src={user.avatarUrl} alt={user.name} />
                  )}
                  <AvatarFallback className="text-xs">
                    {getInitials(user.name)}
                  </AvatarFallback>
                </Avatar>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{user.name}</p>
                  <p className="text-[11px] text-muted-foreground">
                    Administrator
                  </p>
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

export function AdminLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const user = useUser();
  const theme = useTheme();
  const sidebarCollapsed = useSidebarCollapsed();
  const sidebarOpen = useSidebarOpen();
  const { toggleTheme, collapseSidebar, setSidebarOpen } = useUIActions();
  const clearAuth = useClearAuth();
  const [showLogoutDialog, setShowLogoutDialog] = useState(false);

  // Auto-prompt push notification permission once per session
  useNotificationAutoPrompt();

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

  const pageTitle = PAGE_TITLES[location.pathname] || "Admin Dashboard";

  useEffect(() => {
    document.title = `${pageTitle} | Floodingnaque Admin`;
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
          {/* Violet accent for admin tier */}
          <div className="h-1 w-full bg-linear-to-r from-violet-500/60 via-violet-500 to-violet-500/60" />

          {/* Logo */}
          <div
            className={cn(
              "flex items-center h-14 px-4 border-b border-border/30",
              sidebarCollapsed && "justify-center px-2",
            )}
          >
            <div className="flex items-center gap-2">
              <div className="p-1.5 rounded-lg bg-violet-500/10 ring-1 ring-violet-500/20">
                <FloodIcon className="h-5 w-5 text-violet-500" />
              </div>
              {!sidebarCollapsed && (
                <div className="flex flex-col">
                  <span className="font-bold text-sm tracking-tight text-violet-600 dark:text-violet-400">
                    Floodingnaque
                  </span>
                  <span className="text-[10px] text-muted-foreground uppercase tracking-wider">
                    System Control
                  </span>
                </div>
              )}
            </div>
          </div>

          <AdminSidebarNav collapsed={sidebarCollapsed} />

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
                  <div className="h-1 w-full bg-linear-to-r from-violet-500/60 via-violet-500 to-violet-500/60" />
                  <SheetHeader className="h-14 px-4 border-b border-border/30 flex flex-row items-center">
                    <div className="flex items-center gap-2">
                      <div className="p-1.5 rounded-lg bg-violet-500/10 ring-1 ring-violet-500/20">
                        <FloodIcon className="h-5 w-5 text-violet-500" />
                      </div>
                      <SheetTitle className="font-bold text-sm text-violet-600 dark:text-violet-400">
                        System Control
                      </SheetTitle>
                    </div>
                  </SheetHeader>
                  <AdminSidebarNav
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
              <Badge
                variant="outline"
                className="hidden sm:flex gap-1 text-xs border-violet-500/30 text-violet-600 dark:text-violet-400"
              >
                <Shield className="h-3 w-3" />
                Admin
              </Badge>

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
                      <Avatar className="h-8 w-8 ring-2 ring-violet-500/20">
                        {user.avatarUrl && (
                          <AvatarImage src={user.avatarUrl} alt={user.name} />
                        )}
                        <AvatarFallback className="text-xs bg-violet-500/10">
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
                    <DropdownMenuItem onClick={() => navigate("/admin/config")}>
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

export default AdminLayout;
