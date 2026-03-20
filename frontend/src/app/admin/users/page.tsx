/**
 * Admin Users Page
 *
 * Full CRUD user management for system administrators.
 * Color-coded role stats, paginated table with inline actions,
 * role-change confirmation, Add User dialog, auto-refresh,
 * bulk selection, and inactive-account badging.
 */

import { PageHeader, SectionHeading } from "@/components/layout";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { GlassCard } from "@/components/ui/glass-card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  adminQueryKeys,
  useCreateUser,
  useDeleteUser,
  useResetUserPassword,
  useToggleUserStatus,
  useUpdateUserRole,
  useUsers,
} from "@/features/admin/hooks/useAdmin";
import type { AdminUser } from "@/features/admin/services/adminApi";
import { fadeUp, staggerContainer } from "@/lib/motion";
import { cn } from "@/lib/utils";
import { useUser } from "@/state";
import { useQueryClient } from "@tanstack/react-query";
import { formatDistanceToNow } from "date-fns";
import { motion, useInView } from "framer-motion";
import {
  AlertTriangle,
  ChevronLeft,
  ChevronRight,
  Clock,
  Loader2,
  MoreHorizontal,
  Plus,
  RefreshCw,
  Search,
  Shield,
  UserCheck,
  UserCog,
  Users,
  XCircle,
} from "lucide-react";
import { useCallback, useMemo, useRef, useState } from "react";
import { toast } from "sonner";

// ── Constants ──

const ROLE_STYLES: Record<string, string> = {
  admin: "bg-primary/15 text-primary border-primary/30",
  operator: "bg-risk-alert/15 text-risk-alert border-risk-alert/30",
  user: "bg-muted text-muted-foreground border-muted-foreground/20",
};

const ROLE_LABELS: Record<string, string> = {
  admin: "Admin",
  operator: "LGU Operator",
  user: "Resident",
};

type AccentLevel = "good" | "warn" | "critical" | "neutral";

function accentGradient(level: AccentLevel): string {
  switch (level) {
    case "good":
      return "from-risk-safe/60 via-risk-safe to-risk-safe/60";
    case "warn":
      return "from-risk-alert/60 via-risk-alert to-risk-alert/60";
    case "critical":
      return "from-risk-critical/60 via-risk-critical to-risk-critical/60";
    default:
      return "from-primary/40 via-primary/60 to-primary/40";
  }
}

function statTextColor(level: AccentLevel): string {
  switch (level) {
    case "good":
      return "text-risk-safe";
    case "warn":
      return "text-risk-alert";
    case "critical":
      return "text-risk-critical";
    default:
      return "";
  }
}

function iconRing(level: AccentLevel): string {
  switch (level) {
    case "good":
      return "bg-risk-safe/10 ring-risk-safe/20";
    case "warn":
      return "bg-risk-alert/10 ring-risk-alert/20";
    case "critical":
      return "bg-risk-critical/10 ring-risk-critical/20";
    default:
      return "bg-primary/10 ring-primary/20";
  }
}

const THIRTY_DAYS_MS = 30 * 24 * 60 * 60 * 1000;

function isInactive(lastLogin: string | null): boolean {
  if (!lastLogin) return true;
  return Date.now() - new Date(lastLogin).getTime() > THIRTY_DAYS_MS;
}

// ── Stat Card ──

function StatCard({
  icon: Icon,
  label,
  value,
  isLoading,
  health = "neutral",
}: {
  icon: React.ElementType;
  label: string;
  value: number;
  isLoading?: boolean;
  health?: AccentLevel;
}) {
  return (
    <GlassCard className="overflow-hidden hover:shadow-lg transition-all duration-300">
      <div
        className={cn("h-1 w-full bg-linear-to-r", accentGradient(health))}
      />
      <div className="pt-4 pb-3 px-6 flex items-center gap-3">
        <div
          className={cn(
            "flex h-10 w-10 items-center justify-center rounded-xl ring-1",
            iconRing(health),
          )}
        >
          <Icon
            className={cn(
              "h-5 w-5",
              health === "neutral" ? "text-primary" : statTextColor(health),
            )}
          />
        </div>
        <div>
          <p className="text-xs text-muted-foreground">{label}</p>
          {isLoading ? (
            <Skeleton className="h-7 w-10 mt-0.5" />
          ) : (
            <p className={cn("text-2xl font-bold", statTextColor(health))}>
              {value}
            </p>
          )}
        </div>
      </div>
    </GlassCard>
  );
}

// ── Add User Dialog ──

function AddUserDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
}) {
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [role, setRole] = useState<"user" | "operator" | "admin">("user");
  const createUser = useCreateUser();

  const handleSubmit = () => {
    if (!email.trim()) {
      toast.error("Email is required");
      return;
    }
    createUser.mutate(
      { email: email.trim(), name: name.trim() || undefined, role },
      {
        onSuccess: (res) => {
          toast.success(
            `User created. Temporary password: ${res.temporary_password}`,
            { duration: 30_000 },
          );
          setEmail("");
          setName("");
          setRole("user");
          onOpenChange(false);
        },
        onError: () => toast.error("Failed to create user"),
      },
    );
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Add New User</DialogTitle>
          <DialogDescription>
            Create an account with a temporary password. The user must change it
            on first login.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-2">
          <div className="space-y-2">
            <Label htmlFor="add-email">Email</Label>
            <Input
              id="add-email"
              type="email"
              placeholder="user@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="add-name">Full Name</Label>
            <Input
              id="add-name"
              placeholder="Juan dela Cruz"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label>Role</Label>
            <Select
              value={role}
              onValueChange={(v) => setRole(v as "user" | "operator" | "admin")}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="user">Resident</SelectItem>
                <SelectItem value="operator">LGU Operator</SelectItem>
                <SelectItem value="admin">Admin</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={createUser.isPending}
          >
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={createUser.isPending}>
            {createUser.isPending && (
              <Loader2 className="h-4 w-4 animate-spin mr-2" />
            )}
            Create User
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ── Main Page ──

export default function AdminUsersPage() {
  // ── State ──
  const [page, setPage] = useState(1);
  const [roleFilter, setRoleFilter] = useState<string>("all");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [search, setSearch] = useState("");
  const [deleteTarget, setDeleteTarget] = useState<{
    id: string;
    name: string;
  } | null>(null);
  const [roleChangeTarget, setRoleChangeTarget] = useState<{
    id: string;
    name: string;
    newRole: string;
  } | null>(null);
  const [showAddUser, setShowAddUser] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [lastRefreshed, setLastRefreshed] = useState<Date | null>(null);

  // ── Queries & Mutations ──
  const currentUser = useUser();
  const queryClient = useQueryClient();

  const params = useMemo(
    () => ({
      page,
      per_page: 15,
      ...(roleFilter !== "all" && { role: roleFilter }),
      ...(statusFilter !== "all" && { status: statusFilter }),
      ...(search && { search }),
    }),
    [page, roleFilter, statusFilter, search],
  );

  const { data, isLoading, isError, dataUpdatedAt, refetch } = useUsers(params);
  const updateRole = useUpdateUserRole();
  const toggleStatus = useToggleUserStatus();
  const resetPassword = useResetUserPassword();
  const deleteUser = useDeleteUser();

  const users = useMemo(() => data?.data?.users ?? [], [data?.data?.users]);
  const total = data?.data?.total ?? 0;
  const totalPages = data?.data?.total_pages ?? 1;
  const perPage = data?.data?.per_page ?? 15;

  // ── Derived data ──
  const admins = users.filter((u: AdminUser) => u.role === "admin").length;
  const operators = users.filter(
    (u: AdminUser) => u.role === "operator",
  ).length;
  const residents = users.filter((u: AdminUser) => u.role === "user").length;

  const isSelf = useCallback(
    (userId: string) =>
      currentUser && String(currentUser.id) === String(userId),
    [currentUser],
  );

  const allSelected =
    users.length > 0 && users.every((u) => selectedIds.has(u.id));

  // Page-level counts
  const showStart = total === 0 ? 0 : (page - 1) * perPage + 1;
  const showEnd = Math.min(page * perPage, total);

  // ── Handlers ──
  const handleRefresh = useCallback(async () => {
    setIsRefreshing(true);
    await queryClient.invalidateQueries({
      queryKey: adminQueryKeys.users(params),
    });
    setLastRefreshed(new Date());
    setIsRefreshing(false);
  }, [queryClient, params]);

  const handleConfirmRoleChange = useCallback(() => {
    if (!roleChangeTarget) return;
    updateRole.mutate(
      { id: roleChangeTarget.id, role: roleChangeTarget.newRole },
      {
        onSuccess: () => {
          toast.success(
            `${roleChangeTarget.name} is now ${ROLE_LABELS[roleChangeTarget.newRole]}`,
          );
          setRoleChangeTarget(null);
        },
        onError: () => toast.error("Failed to update role"),
      },
    );
  }, [roleChangeTarget, updateRole]);

  const handleStatusToggle = useCallback(
    (userId: string, currentlyActive: boolean) => {
      toggleStatus.mutate(
        { id: userId, isActive: !currentlyActive },
        {
          onSuccess: () =>
            toast.success(
              currentlyActive ? "User suspended" : "User reactivated",
            ),
          onError: () => toast.error("Failed to update status"),
        },
      );
    },
    [toggleStatus],
  );

  const handleResetPassword = useCallback(
    (userId: string) => {
      resetPassword.mutate(userId, {
        onSuccess: (res) =>
          toast.success(`Temporary password: ${res.temporary_password}`, {
            duration: 30_000,
          }),
        onError: () => toast.error("Failed to reset password"),
      });
    },
    [resetPassword],
  );

  const handleDelete = useCallback(() => {
    if (!deleteTarget) return;
    deleteUser.mutate(deleteTarget.id, {
      onSuccess: () => {
        toast.success("User deleted");
        setDeleteTarget(null);
        setSelectedIds((prev) => {
          const next = new Set(prev);
          next.delete(deleteTarget.id);
          return next;
        });
      },
      onError: () => toast.error("Failed to delete user"),
    });
  }, [deleteTarget, deleteUser]);

  const handleBulkSuspend = useCallback(() => {
    const ids = [...selectedIds];
    ids.forEach((id) => {
      const user = users.find((u) => u.id === id);
      if (user && user.is_active && !isSelf(id)) {
        toggleStatus.mutate({ id, isActive: false });
      }
    });
    setSelectedIds(new Set());
    toast.success(`Suspended ${ids.length} user(s)`);
  }, [selectedIds, users, toggleStatus, isSelf]);

  const toggleSelect = (id: string) =>
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });

  const toggleSelectAll = () => {
    if (allSelected) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(users.map((u) => u.id)));
    }
  };

  const clearFilters = () => {
    setSearch("");
    setRoleFilter("all");
    setStatusFilter("all");
    setPage(1);
  };

  const hasActiveFilters =
    search !== "" || roleFilter !== "all" || statusFilter !== "all";

  // ── Refs for animations ──
  const filterRef = useRef<HTMLDivElement>(null);
  const filterInView = useInView(filterRef, { once: true, amount: 0.1 });
  const tableRef = useRef<HTMLDivElement>(null);
  const tableInView = useInView(tableRef, { once: true, amount: 0.1 });
  const statsRef = useRef<HTMLDivElement>(null);
  const statsInView = useInView(statsRef, { once: true, amount: 0.1 });

  // ── Last Updated display ──
  const displayUpdatedAt =
    lastRefreshed ?? (dataUpdatedAt ? new Date(dataUpdatedAt) : null);

  // ── Stats Config ──
  const STATS: {
    label: string;
    value: number;
    icon: React.ElementType;
    health: AccentLevel;
  }[] = [
    { label: "Total Users", value: total, icon: Users, health: "neutral" },
    { label: "Admins", value: admins, icon: Shield, health: "critical" },
    { label: "LGU Operators", value: operators, icon: UserCog, health: "warn" },
    { label: "Residents", value: residents, icon: UserCheck, health: "good" },
  ];

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <div className="w-full px-6 pt-6">
        <div className="flex items-start justify-between">
          <PageHeader
            icon={Users}
            title="User Management"
            subtitle={`${total} registered account${total !== 1 ? "s" : ""}`}
          />
          <div className="flex items-center gap-3 pt-1">
            {displayUpdatedAt && (
              <span className="text-xs text-muted-foreground flex items-center gap-1">
                <Clock className="h-3 w-3" />
                Updated{" "}
                {formatDistanceToNow(displayUpdatedAt, { addSuffix: true })}
              </span>
            )}
            <Button
              variant="outline"
              size="sm"
              onClick={handleRefresh}
              disabled={isRefreshing}
            >
              <RefreshCw
                className={cn("h-4 w-4 mr-1.5", isRefreshing && "animate-spin")}
              />
              Refresh
            </Button>
          </div>
        </div>
      </div>

      {/* Role Summary Stats */}
      <section className="py-6 bg-background">
        <div className="w-full px-6" ref={statsRef}>
          <motion.div
            variants={staggerContainer}
            initial="hidden"
            animate={statsInView ? "show" : undefined}
            className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4"
          >
            {STATS.map(({ label, value, icon, health }) => (
              <motion.div key={label} variants={fadeUp}>
                <StatCard
                  icon={icon}
                  label={label}
                  value={value}
                  isLoading={isLoading}
                  health={health}
                />
              </motion.div>
            ))}
          </motion.div>
        </div>
      </section>

      {/* Filter & Search */}
      <section className="py-10 bg-muted/30">
        <div className="w-full px-6" ref={filterRef}>
          <SectionHeading
            label="Search"
            title="Filter & Search"
            subtitle="Find users by name, email, role, or status"
          />
          <motion.div
            variants={staggerContainer}
            initial="hidden"
            animate={filterInView ? "show" : undefined}
          >
            <motion.div variants={fadeUp} className="flex flex-wrap gap-3">
              <div className="relative flex-1 min-w-50 max-w-sm">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search by name or email..."
                  value={search}
                  onChange={(e) => {
                    setSearch(e.target.value);
                    setPage(1);
                  }}
                  className="pl-9"
                />
              </div>
              <Select
                value={roleFilter}
                onValueChange={(v) => {
                  setRoleFilter(v);
                  setPage(1);
                }}
              >
                <SelectTrigger className="w-37.5">
                  <SelectValue placeholder="Role" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Roles</SelectItem>
                  <SelectItem value="admin">Admin</SelectItem>
                  <SelectItem value="operator">Operator</SelectItem>
                  <SelectItem value="user">Resident</SelectItem>
                </SelectContent>
              </Select>
              <Select
                value={statusFilter}
                onValueChange={(v) => {
                  setStatusFilter(v);
                  setPage(1);
                }}
              >
                <SelectTrigger className="w-37.5">
                  <SelectValue placeholder="Status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Status</SelectItem>
                  <SelectItem value="active">Active</SelectItem>
                  <SelectItem value="inactive">Suspended</SelectItem>
                </SelectContent>
              </Select>
              {hasActiveFilters && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={clearFilters}
                  className="text-muted-foreground"
                >
                  <XCircle className="h-4 w-4 mr-1" />
                  Clear
                </Button>
              )}
            </motion.div>
          </motion.div>
        </div>
      </section>

      {/* User Directory */}
      <section className="py-10 bg-background">
        <div className="w-full px-6" ref={tableRef}>
          <SectionHeading
            label="Directory"
            title="Registered Users"
            subtitle="Manage accounts, roles, and access control"
          />
          <motion.div
            variants={staggerContainer}
            initial="hidden"
            animate={tableInView ? "show" : undefined}
          >
            <motion.div variants={fadeUp}>
              <GlassCard className="overflow-hidden hover:shadow-lg transition-all duration-300">
                <div className="h-1 w-full bg-linear-to-r from-primary/60 via-primary to-primary/60" />
                <div className="pt-6 px-6 pb-6">
                  {/* Toolbar */}
                  <div className="flex items-center justify-between mb-4">
                    <p className="text-sm text-muted-foreground">
                      Showing {showStart}–{showEnd} of {total} user
                      {total !== 1 ? "s" : ""}
                    </p>
                    <div className="flex items-center gap-2">
                      {selectedIds.size > 0 && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={handleBulkSuspend}
                          className="text-risk-alert border-risk-alert/30"
                        >
                          Suspend {selectedIds.size} selected
                        </Button>
                      )}
                      <Button size="sm" onClick={() => setShowAddUser(true)}>
                        <Plus className="h-4 w-4 mr-1.5" />
                        Add User
                      </Button>
                    </div>
                  </div>

                  {/* Error State */}
                  {isError && !isLoading ? (
                    <div className="text-center py-16">
                      <XCircle className="h-12 w-12 mx-auto text-risk-critical/40 mb-4" />
                      <p className="text-muted-foreground mb-4">
                        Failed to load users. Please try again.
                      </p>
                      <Button variant="outline" onClick={() => refetch()}>
                        <RefreshCw className="h-4 w-4 mr-1.5" />
                        Retry
                      </Button>
                    </div>
                  ) : isLoading ? (
                    <div className="space-y-3">
                      {Array.from({ length: 5 }).map((_, i) => (
                        <Skeleton key={i} className="h-12 w-full" />
                      ))}
                    </div>
                  ) : users.length === 0 ? (
                    /* Empty State */
                    <div className="text-center py-16">
                      <Users className="h-12 w-12 mx-auto text-muted-foreground/30 mb-4" />
                      <p className="text-muted-foreground mb-1">
                        No users match the current filters
                      </p>
                      {hasActiveFilters && (
                        <Button
                          variant="link"
                          size="sm"
                          onClick={clearFilters}
                          className="text-primary"
                        >
                          Clear all filters
                        </Button>
                      )}
                    </div>
                  ) : (
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead className="w-10">
                            <Checkbox
                              checked={allSelected}
                              onCheckedChange={toggleSelectAll}
                              aria-label="Select all users"
                            />
                          </TableHead>
                          <TableHead>Name</TableHead>
                          <TableHead>Email</TableHead>
                          <TableHead>Role</TableHead>
                          <TableHead>Status</TableHead>
                          <TableHead>Last Login</TableHead>
                          <TableHead className="text-right">Actions</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {users.map((u) => {
                          const self = !!isSelf(u.id);
                          const inactive = isInactive(u.last_login_at);
                          return (
                            <TableRow
                              key={u.id}
                              className={cn(
                                selectedIds.has(u.id) && "bg-muted/40",
                              )}
                            >
                              <TableCell>
                                <Checkbox
                                  checked={selectedIds.has(u.id)}
                                  onCheckedChange={() => toggleSelect(u.id)}
                                  aria-label={`Select ${u.name}`}
                                />
                              </TableCell>
                              <TableCell className="font-medium">
                                <div className="flex items-center gap-2">
                                  {u.name || "—"}
                                  {self && (
                                    <Badge
                                      variant="outline"
                                      className="text-[10px] px-1.5 py-0 bg-primary/10 text-primary border-primary/30"
                                    >
                                      You
                                    </Badge>
                                  )}
                                </div>
                              </TableCell>
                              <TableCell className="text-muted-foreground">
                                {u.email}
                              </TableCell>
                              <TableCell>
                                <Badge
                                  variant="outline"
                                  className={cn("text-xs", ROLE_STYLES[u.role])}
                                >
                                  {ROLE_LABELS[u.role] ?? u.role}
                                </Badge>
                              </TableCell>
                              <TableCell>
                                <Badge
                                  variant="outline"
                                  className={cn(
                                    "text-xs",
                                    u.is_active
                                      ? "bg-risk-safe/10 text-risk-safe border-risk-safe/30"
                                      : "bg-risk-critical/10 text-risk-critical border-risk-critical/30",
                                  )}
                                >
                                  {u.is_active ? "Active" : "Suspended"}
                                </Badge>
                              </TableCell>
                              <TableCell className="text-sm text-muted-foreground">
                                <div className="flex items-center gap-2">
                                  {u.last_login_at ? (
                                    <span>
                                      {new Date(u.last_login_at).toLocaleString(
                                        "en-PH",
                                        {
                                          dateStyle: "medium",
                                          timeStyle: "short",
                                        },
                                      )}
                                    </span>
                                  ) : (
                                    <span className="italic text-muted-foreground/60">
                                      Never
                                    </span>
                                  )}
                                  {inactive && (
                                    <Badge
                                      variant="outline"
                                      className="text-[10px] px-1.5 py-0 bg-risk-alert/10 text-risk-alert border-risk-alert/30"
                                    >
                                      <AlertTriangle className="h-3 w-3 mr-0.5" />
                                      30d+
                                    </Badge>
                                  )}
                                </div>
                              </TableCell>
                              <TableCell className="text-right">
                                <DropdownMenu>
                                  <DropdownMenuTrigger asChild>
                                    <Button
                                      variant="ghost"
                                      size="icon"
                                      className="h-8 w-8"
                                      aria-label="User actions"
                                    >
                                      <MoreHorizontal className="h-4 w-4" />
                                    </Button>
                                  </DropdownMenuTrigger>
                                  <DropdownMenuContent align="end">
                                    {(["admin", "operator", "user"] as const)
                                      .filter((r) => r !== u.role)
                                      .map((r) => (
                                        <DropdownMenuItem
                                          key={r}
                                          disabled={self}
                                          onClick={() =>
                                            setRoleChangeTarget({
                                              id: u.id,
                                              name: u.name,
                                              newRole: r,
                                            })
                                          }
                                        >
                                          Set as {ROLE_LABELS[r]}
                                        </DropdownMenuItem>
                                      ))}
                                    <DropdownMenuSeparator />
                                    <DropdownMenuItem
                                      disabled={self}
                                      onClick={() =>
                                        handleStatusToggle(u.id, u.is_active)
                                      }
                                    >
                                      {u.is_active
                                        ? "Suspend Account"
                                        : "Reactivate Account"}
                                    </DropdownMenuItem>
                                    <DropdownMenuItem
                                      onClick={() => handleResetPassword(u.id)}
                                    >
                                      Reset Password
                                    </DropdownMenuItem>
                                    <DropdownMenuSeparator />
                                    <DropdownMenuItem
                                      disabled={self}
                                      className="text-destructive focus:text-destructive"
                                      onClick={() =>
                                        setDeleteTarget({
                                          id: u.id,
                                          name: u.name,
                                        })
                                      }
                                    >
                                      Delete User
                                    </DropdownMenuItem>
                                  </DropdownMenuContent>
                                </DropdownMenu>
                              </TableCell>
                            </TableRow>
                          );
                        })}
                      </TableBody>
                    </Table>
                  )}

                  {/* Pagination */}
                  {!isError && totalPages > 0 && (
                    <div className="flex items-center justify-between mt-4 pt-4 border-t">
                      <p className="text-sm text-muted-foreground">
                        Page {page} of {totalPages}
                      </p>
                      <div className="flex gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          disabled={page <= 1}
                          onClick={() => setPage((p) => p - 1)}
                        >
                          <ChevronLeft className="h-4 w-4 mr-1" /> Previous
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          disabled={page >= totalPages}
                          onClick={() => setPage((p) => p + 1)}
                        >
                          Next <ChevronRight className="h-4 w-4 ml-1" />
                        </Button>
                      </div>
                    </div>
                  )}
                </div>
              </GlassCard>
            </motion.div>
          </motion.div>
        </div>
      </section>

      {/* Add User Dialog */}
      <AddUserDialog open={showAddUser} onOpenChange={setShowAddUser} />

      {/* Role Change Confirmation Dialog */}
      <AlertDialog
        open={!!roleChangeTarget}
        onOpenChange={(open) => !open && setRoleChangeTarget(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Change User Role</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to change{" "}
              <span className="font-semibold">{roleChangeTarget?.name}</span> to{" "}
              <span className="font-semibold">
                {roleChangeTarget && ROLE_LABELS[roleChangeTarget.newRole]}
              </span>
              ? This will immediately affect their access permissions.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleConfirmRoleChange}
              disabled={updateRole.isPending}
            >
              {updateRole.isPending && (
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
              )}
              Confirm
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Delete Confirmation Dialog */}
      <AlertDialog
        open={!!deleteTarget}
        onOpenChange={(open) => !open && setDeleteTarget(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete User</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete{" "}
              <span className="font-semibold">{deleteTarget?.name}</span>? The
              account will be deactivated and can be restored by an
              administrator.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              disabled={deleteUser.isPending}
            >
              {deleteUser.isPending && (
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
              )}
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
