/**
 * Admin Cybersecurity & Audit Page
 *
 * Industrial-grade security dashboard with posture scoring, threat
 * monitoring, audit trail, RBAC audit, session management, and
 * security-event analytics. Admin-only access.
 */

import { PageHeader, SectionHeading } from "@/components/layout";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { GlassCard } from "@/components/ui/glass-card";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  useAuditLogs,
  useAuditStats,
  useSecurityPosture,
} from "@/features/admin/hooks/useAdmin";
import type {
  AuditLogEntry,
  AuditLogListParams,
  SecurityCheck,
} from "@/features/admin/services/adminApi";
import { fadeUp, staggerContainer } from "@/lib/motion";
import { cn } from "@/lib/utils";
import { motion, useInView } from "framer-motion";
import {
  AlertTriangle,
  CheckCircle,
  ChevronLeft,
  ChevronRight,
  Copy,
  Download,
  Eye,
  Filter,
  Lock,
  Radio,
  RefreshCw,
  Search,
  Shield,
  ShieldAlert,
  ShieldCheck,
  ShieldX,
  Users,
  XCircle,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";

// ── Constants ──────────────────────────────────────────────────────

const SEVERITY_OPTIONS = [
  { value: "_all", label: "All Severities" },
  { value: "info", label: "Info" },
  { value: "warning", label: "Warning" },
  { value: "critical", label: "Critical" },
];

const CATEGORY_OPTIONS = [
  { value: "_all", label: "All Categories" },
  { value: "authentication", label: "Authentication" },
  { value: "authorization", label: "Authorization" },
  { value: "user_management", label: "User Management" },
  { value: "data_access", label: "Data Access" },
  { value: "config_change", label: "System Config" },
  { value: "model_operation", label: "Model Operations" },
  { value: "security_event", label: "Security Events" },
];

const DATE_PRESETS = [
  { value: "_all", label: "All Time" },
  { value: "today", label: "Today" },
  { value: "7d", label: "Last 7 Days" },
  { value: "30d", label: "Last 30 Days" },
];

const PER_PAGE_OPTIONS = [15, 25, 50, 100];
const LIVE_POLL_MS = 5_000;

const CHECK_CATEGORIES: Record<string, { label: string; color: string }> = {
  authentication: {
    label: "Authentication",
    color: "text-blue-600 dark:text-blue-400",
  },
  authorization: {
    label: "Authorization",
    color: "text-purple-600 dark:text-purple-400",
  },
  network: {
    label: "Network",
    color: "text-emerald-600 dark:text-emerald-400",
  },
  data: {
    label: "Data Protection",
    color: "text-amber-600 dark:text-amber-400",
  },
  monitoring: { label: "Monitoring", color: "text-primary" },
};

// ── Helpers ────────────────────────────────────────────────────────

function threatColor(n: number): string {
  if (n === 0) return "text-risk-safe";
  if (n <= 5) return "text-risk-alert";
  if (n <= 10) return "text-amber-500";
  return "text-risk-critical";
}

function threatBg(n: number): string {
  if (n === 0) return "bg-risk-safe/10 ring-risk-safe/20";
  if (n <= 5) return "bg-risk-alert/10 ring-risk-alert/20";
  if (n <= 10) return "bg-amber-500/10 ring-amber-500/20";
  return "bg-risk-critical/10 ring-risk-critical/20";
}

function threatBarColor(n: number): string {
  if (n === 0) return "from-risk-safe/60 via-risk-safe to-risk-safe/60";
  if (n <= 5) return "from-risk-alert/60 via-risk-alert to-risk-alert/60";
  if (n <= 10) return "from-amber-500/60 via-amber-500 to-amber-500/60";
  return "from-risk-critical/60 via-risk-critical to-risk-critical/60";
}

function scoreColor(s: number): string {
  if (s >= 91) return "text-risk-safe";
  if (s >= 71) return "text-blue-600 dark:text-blue-400";
  if (s >= 41) return "text-risk-alert";
  return "text-risk-critical";
}

function scoreStroke(s: number): string {
  if (s >= 91) return "stroke-risk-safe";
  if (s >= 71) return "stroke-blue-500";
  if (s >= 41) return "stroke-risk-alert";
  return "stroke-risk-critical";
}

function scoreLabel(s: number): string {
  if (s >= 91) return "Excellent";
  if (s >= 71) return "Good";
  if (s >= 41) return "Moderate Risk";
  return "Critical Risk";
}

function severityBadgeCls(sev: string): string {
  switch (sev) {
    case "critical":
      return "bg-risk-critical/15 text-risk-critical border-risk-critical/30";
    case "warning":
      return "bg-risk-alert/15 text-risk-alert border-risk-alert/30";
    default:
      return "bg-blue-500/15 text-blue-600 dark:text-blue-400 border-blue-500/30";
  }
}

function checkStatusColor(status: string): string {
  switch (status) {
    case "pass":
      return "text-risk-safe";
    case "fail":
      return "text-risk-critical";
    default:
      return "text-risk-alert";
  }
}

function datePresetRange(preset: string): { from: string; to: string } | null {
  if (preset === "_all") return null;
  const now = new Date();
  const to = now.toISOString().slice(0, 10);
  if (preset === "today") return { from: to, to };
  if (preset === "7d") {
    const d = new Date(now);
    d.setDate(d.getDate() - 7);
    return { from: d.toISOString().slice(0, 10), to };
  }
  if (preset === "30d") {
    const d = new Date(now);
    d.setDate(d.getDate() - 30);
    return { from: d.toISOString().slice(0, 10), to };
  }
  return null;
}

// ── Main Component ─────────────────────────────────────────────────

export default function AdminSecurityPage() {
  // ── posture / stats queries ──

  const {
    data: postureRes,
    isLoading: postureLoading,
    refetch: refetchPosture,
    isFetching: postureFetching,
    dataUpdatedAt: postureUpdatedAt,
  } = useSecurityPosture();

  const { data: statsRes, isLoading: statsLoading } = useAuditStats();

  const postureData = postureRes?.data;
  const stats = statsRes?.data;

  // ── audit log state ──

  const [searchInput, setSearchInput] = useState("");
  const [appliedSearch, setAppliedSearch] = useState("");
  const [severityFilter, setSeverityFilter] = useState("_all");
  const [categoryFilter, setCategoryFilter] = useState("_all");
  const [datePreset, setDatePreset] = useState("_all");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(25);
  const [pageJump, setPageJump] = useState("");
  const [expandedAudit, setExpandedAudit] = useState<number | null>(null);
  const [liveMode, setLiveMode] = useState(false);
  const [activeTab, setActiveTab] = useState("posture");

  // Build audit query params
  const auditParams = useMemo<AuditLogListParams>(() => {
    const p: AuditLogListParams = { page, per_page: perPage };
    if (appliedSearch) p.search = appliedSearch;
    if (severityFilter !== "_all") p.severity = severityFilter;
    if (categoryFilter !== "_all") p.action = categoryFilter;
    if (startDate) p.date_from = startDate;
    if (endDate) p.date_to = endDate;
    return p;
  }, [
    page,
    perPage,
    appliedSearch,
    severityFilter,
    categoryFilter,
    startDate,
    endDate,
  ]);

  const {
    data: auditRes,
    isLoading: auditLoading,
    refetch: refetchAudit,
    isFetching: auditFetching,
  } = useAuditLogs(auditParams);

  const rawAuditLogs = auditRes?.data?.logs;
  const auditLogs = useMemo(() => rawAuditLogs ?? [], [rawAuditLogs]);
  const auditTotal = auditRes?.data?.total ?? 0;
  const auditPages = auditRes?.data?.total_pages ?? 1;
  const auditPage = auditRes?.data?.page ?? 1;

  // ── live-mode polling ──

  useEffect(() => {
    if (!liveMode) return;
    const id = setInterval(() => {
      void refetchPosture();
      void refetchAudit();
    }, LIVE_POLL_MS);
    return () => clearInterval(id);
  }, [liveMode, refetchPosture, refetchAudit]);

  // ── handlers ──

  const applySearch = useCallback(() => {
    setAppliedSearch(searchInput);
    setPage(1);
  }, [searchInput]);

  const handleDatePreset = useCallback((preset: string) => {
    setDatePreset(preset);
    const range = datePresetRange(preset);
    if (range) {
      setStartDate(range.from);
      setEndDate(range.to);
    } else {
      setStartDate("");
      setEndDate("");
    }
    setPage(1);
  }, []);

  const resetFilters = useCallback(() => {
    setSearchInput("");
    setAppliedSearch("");
    setSeverityFilter("_all");
    setCategoryFilter("_all");
    setDatePreset("_all");
    setStartDate("");
    setEndDate("");
    setPage(1);
  }, []);

  const hasFilters =
    appliedSearch ||
    severityFilter !== "_all" ||
    categoryFilter !== "_all" ||
    startDate ||
    endDate;

  const jumpToPage = useCallback(() => {
    const n = Number(pageJump);
    if (n >= 1 && n <= auditPages) {
      setPage(n);
      setPageJump("");
    }
  }, [pageJump, auditPages]);

  /** Pre-filter audit trail from stat card click */
  const filterByAction = useCallback((action: string) => {
    setActiveTab("audit");
    if (action === "login_failed") {
      setAppliedSearch("login_failed");
      setSearchInput("login_failed");
    } else if (action === "access_denied") {
      setAppliedSearch("access_denied");
      setSearchInput("access_denied");
    } else if (action === "critical") {
      setSeverityFilter("critical");
    }
    setPage(1);
  }, []);

  const refreshAll = useCallback(() => {
    void refetchPosture();
    void refetchAudit();
  }, [refetchPosture, refetchAudit]);

  const copyAuditRow = useCallback((entry: AuditLogEntry) => {
    const lines = [
      `Action: ${entry.action}`,
      `Severity: ${entry.severity}`,
      `User: ${entry.user_email ?? "System"}`,
      `IP: ${entry.ip_address ?? "N/A"}`,
      `Time: ${new Date(entry.created_at).toLocaleString("en-PH")}`,
      entry.details ? `Details: ${JSON.stringify(entry.details)}` : "",
    ]
      .filter(Boolean)
      .join("\n");
    navigator.clipboard
      .writeText(lines)
      .then(() => toast.success("Audit entry copied"));
  }, []);

  const exportAuditCsv = useCallback(() => {
    if (auditLogs.length === 0) {
      toast.error("No audit entries to export");
      return;
    }
    const hdr = [
      "ID",
      "Action",
      "Severity",
      "User",
      "IP",
      "Details",
      "Timestamp",
    ];
    const rows = auditLogs.map((l) => [
      l.id,
      l.action,
      l.severity,
      l.user_email ?? "System",
      l.ip_address ?? "",
      (l.details ? JSON.stringify(l.details) : "").replace(/"/g, '""'),
      l.created_at,
    ]);
    const csv = [
      hdr.join(","),
      ...rows.map((r) => r.map((v) => `"${v}"`).join(",")),
    ].join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `audit-trail-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success(`Exported ${auditLogs.length} audit entries`);
  }, [auditLogs]);

  // ── derived data ──

  const lastUpdated = postureUpdatedAt
    ? new Date(postureUpdatedAt).toLocaleTimeString("en-PH")
    : null;

  const showFrom = auditTotal === 0 ? 0 : (auditPage - 1) * perPage + 1;
  const showTo = Math.min(auditPage * perPage, auditTotal);

  // Group security checks by category
  const checkGroups = useMemo(() => {
    const groups: Record<string, SecurityCheck[]> = {};
    for (const c of postureData?.checks ?? []) {
      const cat = c.category || "other";
      if (!groups[cat]) groups[cat] = [];
      groups[cat].push(c);
    }
    return groups;
  }, [postureData]);

  // Brute-force alert banner
  const bruteForceAlert = (stats?.failed_logins_24h ?? 0) >= 10;

  // ── animation refs ──

  const postureRef = useRef<HTMLDivElement>(null);
  const postureInView = useInView(postureRef, { once: true, amount: 0.1 });
  const auditRef = useRef<HTMLDivElement>(null);
  const auditInView = useInView(auditRef, { once: true, amount: 0.05 });

  // ────────────────────────────────────────────────────────────────
  // RENDER
  // ────────────────────────────────────────────────────────────────

  return (
    <div className="min-h-screen bg-background">
      {/* ── Header ─────────────────────────────────────────────── */}
      <div className="w-full px-6 pt-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <PageHeader
            icon={Shield}
            title="Cybersecurity & Audit"
            subtitle="Security posture assessment, audit trail, and threat monitoring"
          />
          <div className="flex items-center gap-2">
            {lastUpdated && (
              <span className="text-xs text-muted-foreground mr-2">
                Updated {lastUpdated}
              </span>
            )}
            <div className="flex items-center gap-2 rounded-md border px-3 py-1.5">
              <Radio
                className={cn(
                  "h-3.5 w-3.5",
                  liveMode
                    ? "text-risk-safe animate-pulse"
                    : "text-muted-foreground",
                )}
              />
              <span className="text-xs font-medium">Live</span>
              <Switch
                checked={liveMode}
                onCheckedChange={setLiveMode}
                className="scale-75"
              />
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={refreshAll}
              disabled={postureFetching || auditFetching}
            >
              <RefreshCw
                className={cn(
                  "h-4 w-4 mr-1.5",
                  (postureFetching || auditFetching) && "animate-spin",
                )}
              />
              Refresh
            </Button>
          </div>
        </div>
      </div>

      {/* ── Brute-force Alert Banner ───────────────────────────── */}
      {bruteForceAlert && (
        <div className="w-full px-6 pt-4">
          <div className="flex items-center gap-3 rounded-lg border border-risk-critical/30 bg-risk-critical/10 px-4 py-3">
            <ShieldX className="h-5 w-5 text-risk-critical shrink-0" />
            <div className="flex-1">
              <p className="text-sm font-medium text-risk-critical">
                Potential Brute Force Attack Detected
              </p>
              <p className="text-xs text-risk-critical/80">
                {stats?.failed_logins_24h} failed login attempts in the last 24
                hours. Review the audit trail for suspicious IP addresses.
              </p>
            </div>
            <Button
              variant="outline"
              size="sm"
              className="border-risk-critical/30 text-risk-critical hover:bg-risk-critical/10"
              onClick={() => filterByAction("login_failed")}
            >
              Investigate
            </Button>
          </div>
        </div>
      )}

      {/* ── Tab Navigation ─────────────────────────────────────── */}
      <div className="w-full px-6 pt-6">
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="grid w-full max-w-lg grid-cols-3">
            <TabsTrigger value="posture">Security Posture</TabsTrigger>
            <TabsTrigger value="audit">Audit Trail</TabsTrigger>
            <TabsTrigger value="rbac">RBAC & Sessions</TabsTrigger>
          </TabsList>

          {/* ═══════════════════════════════════════════════════════
              TAB 1: SECURITY POSTURE
              ═══════════════════════════════════════════════════════ */}
          <TabsContent value="posture" className="mt-0">
            {/* ── Stat Cards ── */}
            <section className="py-6 bg-muted/30">
              <div className="w-full px-6" ref={postureRef}>
                <motion.div
                  variants={staggerContainer}
                  initial="hidden"
                  animate={postureInView ? "show" : undefined}
                  className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4"
                >
                  <SecurityStatCard
                    label="Active Users"
                    value={postureData?.user_stats?.active ?? 0}
                    desc={`${postureData?.user_stats?.admins ?? 0} admin(s)`}
                    icon={Users}
                    loading={postureLoading}
                    color="primary"
                    onClick={() => setActiveTab("rbac")}
                  />
                  <SecurityStatCard
                    label="Failed Logins (24h)"
                    value={
                      stats?.failed_logins_24h ??
                      postureData?.threat_indicators?.failed_logins_24h ??
                      0
                    }
                    desc="Authentication failures"
                    icon={ShieldAlert}
                    loading={statsLoading || postureLoading}
                    color="threat"
                    threatCount={
                      stats?.failed_logins_24h ??
                      postureData?.threat_indicators?.failed_logins_24h ??
                      0
                    }
                    onClick={() => filterByAction("login_failed")}
                  />
                  <SecurityStatCard
                    label="Access Denied (24h)"
                    value={stats?.access_denied_24h ?? 0}
                    desc="RBAC violations"
                    icon={XCircle}
                    loading={statsLoading}
                    color="threat"
                    threatCount={stats?.access_denied_24h ?? 0}
                    onClick={() => filterByAction("access_denied")}
                  />
                  <SecurityStatCard
                    label="Critical Events (24h)"
                    value={
                      stats?.critical_events_24h ??
                      postureData?.threat_indicators?.critical_events_24h ??
                      0
                    }
                    desc="Requires attention"
                    icon={AlertTriangle}
                    loading={statsLoading || postureLoading}
                    color="threat"
                    threatCount={
                      stats?.critical_events_24h ??
                      postureData?.threat_indicators?.critical_events_24h ??
                      0
                    }
                    onClick={() => filterByAction("critical")}
                  />
                </motion.div>
              </div>
            </section>

            {/* ── Score + Security Checks ── */}
            <section className="py-6 bg-background">
              <div className="w-full px-6">
                <SectionHeading
                  label="Assessment"
                  title="Security Posture Score"
                  subtitle="Automated evaluation of system security controls"
                />

                <div className="grid gap-6 lg:grid-cols-3 mt-4">
                  {/* Score Ring Card */}
                  <motion.div variants={fadeUp} initial="hidden" animate="show">
                    <GlassCard className="h-full overflow-hidden">
                      <div className="h-1 w-full bg-linear-to-r from-primary/60 via-primary to-primary/60" />
                      <CardContent className="flex flex-col items-center justify-center pt-8 pb-6 gap-4">
                        <ScoreRing
                          score={postureData?.score ?? 0}
                          isLoading={postureLoading}
                        />
                        {postureLoading ? (
                          <Skeleton className="h-7 w-32" />
                        ) : (
                          <ThreatBadge
                            level={postureData?.threat_level ?? "low"}
                          />
                        )}
                        <p className="text-sm text-muted-foreground text-center">
                          {postureData?.passed ?? 0} of{" "}
                          {postureData?.total ?? 0} checks passed
                        </p>
                      </CardContent>
                    </GlassCard>
                  </motion.div>

                  {/* Security Checks (grouped by category) */}
                  <motion.div
                    variants={fadeUp}
                    initial="hidden"
                    animate="show"
                    className="lg:col-span-2"
                  >
                    <GlassCard className="h-full overflow-hidden">
                      <div className="h-1 w-full bg-linear-to-r from-primary/60 via-primary to-primary/60" />
                      <CardHeader className="pb-2">
                        <CardTitle className="flex items-center gap-2 text-base">
                          <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-primary/10 ring-1 ring-primary/20">
                            <Lock className="h-4 w-4 text-primary" />
                          </div>
                          Security Checks
                          {!postureLoading && (
                            <Badge
                              variant="outline"
                              className="ml-auto text-xs"
                            >
                              {postureData?.passed ?? 0}/
                              {postureData?.total ?? 0} passed
                            </Badge>
                          )}
                        </CardTitle>
                        <CardDescription>
                          Automated security configuration assessment with
                          remediation guidance
                        </CardDescription>
                      </CardHeader>
                      <CardContent>
                        {postureLoading ? (
                          <div className="space-y-2">
                            {Array.from({ length: 8 }).map((_, i) => (
                              <Skeleton
                                key={`chk-skel-${i}`}
                                className="h-10 w-full"
                              />
                            ))}
                          </div>
                        ) : (
                          <div className="space-y-4">
                            {Object.entries(checkGroups).map(
                              ([cat, checks]) => {
                                const catInfo = CHECK_CATEGORIES[cat] ?? {
                                  label: cat,
                                  color: "text-muted-foreground",
                                };
                                return (
                                  <div key={cat}>
                                    <p
                                      className={cn(
                                        "text-xs font-semibold uppercase tracking-wider mb-1.5",
                                        catInfo.color,
                                      )}
                                    >
                                      {catInfo.label}
                                    </p>
                                    <div className="space-y-1">
                                      {checks.map((check) => (
                                        <SecurityCheckRow
                                          key={check.name}
                                          check={check}
                                        />
                                      ))}
                                    </div>
                                  </div>
                                );
                              },
                            )}
                          </div>
                        )}
                      </CardContent>
                    </GlassCard>
                  </motion.div>
                </div>
              </div>
            </section>

            {/* ── Threat Detection Summary ── */}
            <section className="py-6 bg-muted/30">
              <div className="w-full px-6">
                <SectionHeading
                  label="Threats"
                  title="Threat Detection"
                  subtitle="Real-time monitoring of security threats and anomalies"
                />

                <GlassCard className="overflow-hidden mt-4">
                  <div className="h-1 w-full bg-linear-to-r from-risk-critical/60 via-risk-critical to-risk-critical/60" />
                  <CardHeader className="pb-2">
                    <CardTitle className="flex items-center gap-2 text-base">
                      <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-risk-critical/10 ring-1 ring-risk-critical/20">
                        <ShieldAlert className="h-4 w-4 text-risk-critical" />
                      </div>
                      Threat Indicators
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    {postureLoading || statsLoading ? (
                      <div className="space-y-2">
                        {Array.from({ length: 5 }).map((_, i) => (
                          <Skeleton
                            key={`thr-skel-${i}`}
                            className="h-8 w-full"
                          />
                        ))}
                      </div>
                    ) : (
                      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                        {[
                          {
                            label: "Brute Force Attempts",
                            desc: "5+ failed logins from same IP within 10 min",
                            count: stats?.failed_logins_24h ?? 0,
                            severity:
                              (stats?.failed_logins_24h ?? 0) >= 10
                                ? "high"
                                : (stats?.failed_logins_24h ?? 0) >= 5
                                  ? "moderate"
                                  : "low",
                          },
                          {
                            label: "Unauthorized API Access",
                            desc: "Repeated 401/403 responses",
                            count: stats?.access_denied_24h ?? 0,
                            severity:
                              (stats?.access_denied_24h ?? 0) >= 10
                                ? "high"
                                : (stats?.access_denied_24h ?? 0) >= 5
                                  ? "moderate"
                                  : "low",
                          },
                          {
                            label: "Critical Security Events",
                            desc: "High-severity events requiring attention",
                            count: stats?.critical_events_24h ?? 0,
                            severity:
                              (stats?.critical_events_24h ?? 0) >= 5
                                ? "high"
                                : (stats?.critical_events_24h ?? 0) >= 1
                                  ? "moderate"
                                  : "low",
                          },
                          {
                            label: "Locked Accounts",
                            desc: "Accounts locked due to failed attempts",
                            count:
                              postureData?.threat_indicators?.locked_accounts ??
                              0,
                            severity:
                              (postureData?.threat_indicators
                                ?.locked_accounts ?? 0) >= 3
                                ? "moderate"
                                : "low",
                          },
                          {
                            label: "Rate Limit Violations",
                            desc: "Requests exceeding defined thresholds",
                            count: stats?.top_actions?.rate_limit_exceeded ?? 0,
                            severity:
                              (stats?.top_actions?.rate_limit_exceeded ?? 0) >=
                              10
                                ? "high"
                                : "low",
                          },
                          {
                            label: "Total Audit Events (24h)",
                            desc: "All security-relevant events",
                            count: stats?.total_events_24h ?? 0,
                            severity: "info",
                          },
                        ].map((t) => (
                          <div
                            key={t.label}
                            className={cn(
                              "rounded-lg border p-3 transition-colors",
                              t.severity === "high" &&
                                "border-risk-critical/20 bg-risk-critical/5",
                              t.severity === "moderate" &&
                                "border-risk-alert/20 bg-risk-alert/5",
                              t.severity === "low" &&
                                "border-border bg-muted/30",
                              t.severity === "info" &&
                                "border-border bg-muted/30",
                            )}
                          >
                            <div className="flex items-center justify-between mb-1">
                              <p className="text-xs font-medium">{t.label}</p>
                              <span
                                className={cn(
                                  "text-lg font-bold tabular-nums",
                                  t.severity === "high" && "text-risk-critical",
                                  t.severity === "moderate" &&
                                    "text-risk-alert",
                                  t.severity === "low" && "text-risk-safe",
                                  t.severity === "info" && "text-primary",
                                )}
                              >
                                {t.count}
                              </span>
                            </div>
                            <p className="text-[10px] text-muted-foreground">
                              {t.desc}
                            </p>
                          </div>
                        ))}
                      </div>
                    )}
                  </CardContent>
                </GlassCard>
              </div>
            </section>
          </TabsContent>

          {/* ═══════════════════════════════════════════════════════
              TAB 2: AUDIT TRAIL
              ═══════════════════════════════════════════════════════ */}
          <TabsContent value="audit" className="mt-0">
            {/* ── Filters ── */}
            <section className="py-4 bg-muted/30 border-b">
              <div className="w-full px-6">
                <div className="flex items-center gap-2 mb-3">
                  <Filter className="h-4 w-4 text-muted-foreground" />
                  <span className="text-sm font-medium">Audit Filters</span>
                  {hasFilters && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={resetFilters}
                      className="text-xs h-7"
                    >
                      Clear All
                    </Button>
                  )}
                  <div className="ml-auto">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={exportAuditCsv}
                    >
                      <Download className="h-4 w-4 mr-1.5" />
                      Export CSV
                    </Button>
                  </div>
                </div>

                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-6">
                  {/* Search */}
                  <div className="relative xl:col-span-2">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                    <Input
                      placeholder="Search action, email, IP, details\u2026"
                      value={searchInput}
                      onChange={(e) => setSearchInput(e.target.value)}
                      onKeyDown={(e) => e.key === "Enter" && applySearch()}
                      className="pl-9"
                    />
                  </div>
                  {/* Severity */}
                  <Select
                    value={severityFilter}
                    onValueChange={(v) => {
                      setSeverityFilter(v);
                      setPage(1);
                    }}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="All Severities" />
                    </SelectTrigger>
                    <SelectContent>
                      {SEVERITY_OPTIONS.map((o) => (
                        <SelectItem key={o.value} value={o.value}>
                          {o.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  {/* Category */}
                  <Select
                    value={categoryFilter}
                    onValueChange={(v) => {
                      setCategoryFilter(v);
                      setPage(1);
                    }}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="All Categories" />
                    </SelectTrigger>
                    <SelectContent>
                      {CATEGORY_OPTIONS.map((o) => (
                        <SelectItem key={o.value} value={o.value}>
                          {o.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  {/* Date preset */}
                  <Select value={datePreset} onValueChange={handleDatePreset}>
                    <SelectTrigger>
                      <SelectValue placeholder="All Time" />
                    </SelectTrigger>
                    <SelectContent>
                      {DATE_PRESETS.map((d) => (
                        <SelectItem key={d.value} value={d.value}>
                          {d.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {/* Custom date range */}
                <div className="flex items-center gap-3 mt-3">
                  <div className="flex items-center gap-2">
                    <label
                      htmlFor="security-start-date"
                      className="text-xs text-muted-foreground whitespace-nowrap"
                    >
                      From
                    </label>
                    <Input
                      id="security-start-date"
                      type="date"
                      value={startDate}
                      onChange={(e) => {
                        setStartDate(e.target.value);
                        setDatePreset("_all");
                        setPage(1);
                      }}
                      className="w-40 h-9 text-xs"
                    />
                  </div>
                  <div className="flex items-center gap-2">
                    <label
                      htmlFor="security-end-date"
                      className="text-xs text-muted-foreground whitespace-nowrap"
                    >
                      To
                    </label>
                    <Input
                      id="security-end-date"
                      type="date"
                      value={endDate}
                      onChange={(e) => {
                        setEndDate(e.target.value);
                        setDatePreset("_all");
                        setPage(1);
                      }}
                      className="w-40 h-9 text-xs"
                      min={startDate || undefined}
                    />
                  </div>
                </div>
              </div>
            </section>

            {/* ── Audit Table ── */}
            <section className="py-6 bg-background" ref={auditRef}>
              <div className="w-full px-6">
                <SectionHeading
                  label="Audit"
                  title="Audit Trail"
                  subtitle={
                    auditTotal > 0
                      ? `Showing ${showFrom}\u2013${showTo} of ${auditTotal.toLocaleString()} events`
                      : "No audit events found"
                  }
                />

                <motion.div
                  variants={fadeUp}
                  initial="hidden"
                  animate={auditInView ? "show" : undefined}
                >
                  <GlassCard className="overflow-hidden mt-4">
                    <div className="h-1 w-full bg-linear-to-r from-primary/60 via-primary to-primary/60" />

                    {auditLoading ? (
                      <CardContent className="pt-6 space-y-3">
                        {Array.from({ length: 8 }).map((_, i) => (
                          <div
                            key={`audit-skel-${i}`}
                            className="flex items-center gap-4"
                          >
                            <Skeleton className="h-4 w-32" />
                            <Skeleton className="h-4 w-20" />
                            <Skeleton className="h-4 w-16" />
                            <Skeleton className="h-4 w-24 flex-1" />
                            <Skeleton className="h-4 w-24" />
                          </div>
                        ))}
                      </CardContent>
                    ) : auditLogs.length === 0 ? (
                      <CardContent className="py-16 text-center">
                        <Eye className="h-10 w-10 mx-auto text-muted-foreground/40 mb-3" />
                        <p className="text-sm text-muted-foreground">
                          {hasFilters
                            ? "No audit events match the current filters"
                            : "No audit events found"}
                        </p>
                        {hasFilters && (
                          <Button
                            variant="link"
                            size="sm"
                            className="mt-2"
                            onClick={resetFilters}
                          >
                            Clear filters
                          </Button>
                        )}
                      </CardContent>
                    ) : (
                      <div className="overflow-x-auto">
                        <Table>
                          <TableHeader>
                            <TableRow>
                              <TableHead className="w-40">Timestamp</TableHead>
                              <TableHead>Action</TableHead>
                              <TableHead className="w-20">Severity</TableHead>
                              <TableHead className="w-32">User</TableHead>
                              <TableHead className="w-28">IP Address</TableHead>
                              <TableHead className="w-10" />
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            {auditLogs.map((entry) => (
                              <AuditTableRow
                                key={entry.id}
                                entry={entry}
                                expanded={expandedAudit === entry.id}
                                onToggle={() =>
                                  setExpandedAudit(
                                    expandedAudit === entry.id
                                      ? null
                                      : entry.id,
                                  )
                                }
                                onCopy={() => copyAuditRow(entry)}
                              />
                            ))}
                          </TableBody>
                        </Table>
                      </div>
                    )}

                    {/* ── Pagination ── */}
                    {auditTotal > 0 && (
                      <>
                        <Separator />
                        <div className="flex flex-col gap-3 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
                          <div className="flex items-center gap-3 text-xs text-muted-foreground">
                            <span>
                              Showing {showFrom}\u2013{showTo} of{" "}
                              {auditTotal.toLocaleString()} events
                            </span>
                            <Select
                              value={String(perPage)}
                              onValueChange={(v) => {
                                setPerPage(Number(v));
                                setPage(1);
                              }}
                            >
                              <SelectTrigger className="w-22 h-8 text-xs">
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                {PER_PAGE_OPTIONS.map((n) => (
                                  <SelectItem key={n} value={String(n)}>
                                    {n} / page
                                  </SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                          </div>

                          <div className="flex items-center gap-2">
                            <Button
                              variant="outline"
                              size="sm"
                              disabled={auditPage <= 1}
                              onClick={() => setPage((p) => Math.max(1, p - 1))}
                              className="h-8"
                            >
                              <ChevronLeft className="h-4 w-4" />
                            </Button>
                            <span className="text-xs text-muted-foreground px-1">
                              Page {auditPage} of {auditPages}
                            </span>
                            <Button
                              variant="outline"
                              size="sm"
                              disabled={auditPage >= auditPages}
                              onClick={() =>
                                setPage((p) => Math.min(auditPages, p + 1))
                              }
                              className="h-8"
                            >
                              <ChevronRight className="h-4 w-4" />
                            </Button>

                            <div className="flex items-center gap-1 ml-2">
                              <Input
                                type="number"
                                min={1}
                                max={auditPages}
                                value={pageJump}
                                onChange={(e) => setPageJump(e.target.value)}
                                onKeyDown={(e) =>
                                  e.key === "Enter" && jumpToPage()
                                }
                                placeholder="Go to"
                                className="w-16 h-8 text-xs"
                              />
                              <Button
                                variant="outline"
                                size="sm"
                                className="h-8 text-xs"
                                onClick={jumpToPage}
                              >
                                Go
                              </Button>
                            </div>
                          </div>
                        </div>
                      </>
                    )}
                  </GlassCard>
                </motion.div>
              </div>
            </section>

            {/* ── Audit Integrity & Retention ── */}
            <section className="py-6 bg-muted/30">
              <div className="w-full px-6">
                <GlassCard className="overflow-hidden">
                  <div className="h-1 w-full bg-linear-to-r from-primary/60 via-primary to-primary/60" />
                  <CardContent className="py-4">
                    <div className="flex items-center justify-between flex-wrap gap-4">
                      <div className="flex items-center gap-3">
                        <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-primary/10 ring-1 ring-primary/20">
                          <Shield className="h-4 w-4 text-primary" />
                        </div>
                        <div>
                          <p className="text-sm font-medium">
                            Audit Log Integrity
                          </p>
                          <p className="text-xs text-muted-foreground">
                            {auditTotal.toLocaleString()} total events &middot;
                            Immutable audit trail &middot; Write-only storage
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-4 text-xs text-muted-foreground">
                        <span>Retention: 1 year minimum</span>
                        <Separator orientation="vertical" className="h-4" />
                        <span>Tamper-protected &middot; Append-only</span>
                      </div>
                    </div>
                  </CardContent>
                </GlassCard>
              </div>
            </section>
          </TabsContent>

          {/* ═══════════════════════════════════════════════════════
              TAB 3: RBAC & SESSIONS
              ═══════════════════════════════════════════════════════ */}
          <TabsContent value="rbac" className="mt-0">
            {/* ── RBAC Audit ── */}
            <section className="py-6 bg-muted/30">
              <div className="w-full px-6">
                <SectionHeading
                  label="Access Control"
                  title="RBAC Enforcement Audit"
                  subtitle="Role-based access control configuration review"
                />

                <div className="grid gap-6 lg:grid-cols-2 mt-4">
                  {/* Roles & Permissions */}
                  <GlassCard className="overflow-hidden">
                    <div className="h-1 w-full bg-linear-to-r from-primary/60 via-primary to-primary/60" />
                    <CardHeader className="pb-2">
                      <CardTitle className="flex items-center gap-2 text-base">
                        <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-primary/10 ring-1 ring-primary/20">
                          <Lock className="h-4 w-4 text-primary" />
                        </div>
                        Roles & Permissions
                      </CardTitle>
                      <CardDescription>
                        Permission matrix for all defined roles
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      <div className="overflow-x-auto">
                        <Table>
                          <TableHeader>
                            <TableRow>
                              <TableHead>Permission</TableHead>
                              <TableHead className="text-center w-20">
                                Admin
                              </TableHead>
                              <TableHead className="text-center w-20">
                                User
                              </TableHead>
                              <TableHead className="text-center w-20">
                                Viewer
                              </TableHead>
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            {[
                              {
                                perm: "View Dashboard",
                                admin: true,
                                user: true,
                                viewer: true,
                              },
                              {
                                perm: "Make Predictions",
                                admin: true,
                                user: true,
                                viewer: false,
                              },
                              {
                                perm: "View Reports",
                                admin: true,
                                user: true,
                                viewer: true,
                              },
                              {
                                perm: "Export Data",
                                admin: true,
                                user: true,
                                viewer: false,
                              },
                              {
                                perm: "Manage Users",
                                admin: true,
                                user: false,
                                viewer: false,
                              },
                              {
                                perm: "Admin Panel",
                                admin: true,
                                user: false,
                                viewer: false,
                              },
                              {
                                perm: "System Config",
                                admin: true,
                                user: false,
                                viewer: false,
                              },
                              {
                                perm: "Security Audit",
                                admin: true,
                                user: false,
                                viewer: false,
                              },
                              {
                                perm: "Model Operations",
                                admin: true,
                                user: false,
                                viewer: false,
                              },
                              {
                                perm: "Storage Mgmt",
                                admin: true,
                                user: false,
                                viewer: false,
                              },
                            ].map((r) => (
                              <TableRow key={r.perm}>
                                <TableCell className="text-xs font-medium">
                                  {r.perm}
                                </TableCell>
                                <TableCell className="text-center">
                                  {r.admin ? (
                                    <CheckCircle className="h-4 w-4 text-risk-safe mx-auto" />
                                  ) : (
                                    <XCircle className="h-4 w-4 text-muted-foreground/30 mx-auto" />
                                  )}
                                </TableCell>
                                <TableCell className="text-center">
                                  {r.user ? (
                                    <CheckCircle className="h-4 w-4 text-risk-safe mx-auto" />
                                  ) : (
                                    <XCircle className="h-4 w-4 text-muted-foreground/30 mx-auto" />
                                  )}
                                </TableCell>
                                <TableCell className="text-center">
                                  {r.viewer ? (
                                    <CheckCircle className="h-4 w-4 text-risk-safe mx-auto" />
                                  ) : (
                                    <XCircle className="h-4 w-4 text-muted-foreground/30 mx-auto" />
                                  )}
                                </TableCell>
                              </TableRow>
                            ))}
                          </TableBody>
                        </Table>
                      </div>
                    </CardContent>
                  </GlassCard>

                  {/* User Stats & Admin accounts */}
                  <GlassCard className="overflow-hidden">
                    <div className="h-1 w-full bg-linear-to-r from-primary/60 via-primary to-primary/60" />
                    <CardHeader className="pb-2">
                      <CardTitle className="flex items-center gap-2 text-base">
                        <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-primary/10 ring-1 ring-primary/20">
                          <Users className="h-4 w-4 text-primary" />
                        </div>
                        User & Session Overview
                      </CardTitle>
                      <CardDescription>
                        Elevated privilege accounts and session status
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      {postureLoading ? (
                        <div className="space-y-2">
                          {Array.from({ length: 4 }).map((_, i) => (
                            <Skeleton
                              key={`user-skel-${i}`}
                              className="h-10 w-full"
                            />
                          ))}
                        </div>
                      ) : (
                        <>
                          <div className="grid grid-cols-2 gap-3">
                            {[
                              {
                                label: "Total Users",
                                value: postureData?.user_stats?.total ?? 0,
                              },
                              {
                                label: "Active Users",
                                value: postureData?.user_stats?.active ?? 0,
                              },
                              {
                                label: "Admin Accounts",
                                value: postureData?.user_stats?.admins ?? 0,
                              },
                              {
                                label: "Locked Accounts",
                                value: postureData?.user_stats?.locked ?? 0,
                              },
                            ].map((s) => (
                              <div
                                key={s.label}
                                className="rounded-lg border p-3 text-center"
                              >
                                <p className="text-2xl font-bold tabular-nums">
                                  {s.value}
                                </p>
                                <p className="text-[10px] text-muted-foreground">
                                  {s.label}
                                </p>
                              </div>
                            ))}
                          </div>

                          {(postureData?.user_stats?.locked ?? 0) > 0 && (
                            <div className="rounded-lg border border-risk-alert/20 bg-risk-alert/5 p-3 flex items-center gap-2">
                              <AlertTriangle className="h-4 w-4 text-risk-alert shrink-0" />
                              <p className="text-xs text-risk-alert">
                                {postureData?.user_stats?.locked} account(s)
                                currently locked. Review in User Management.
                              </p>
                            </div>
                          )}

                          <Separator />

                          <div>
                            <p className="text-xs font-medium mb-2">
                              RBAC Review Status
                            </p>
                            <div className="flex items-center gap-2">
                              <ShieldCheck className="h-4 w-4 text-risk-safe" />
                              <span className="text-xs text-muted-foreground">
                                3-tier role system enforced (Admin / User /
                                Viewer)
                              </span>
                            </div>
                            <p className="text-[10px] text-muted-foreground mt-1">
                              All admin routes protected by{" "}
                              <code className="text-[10px]">
                                @require_admin
                              </code>{" "}
                              decorator. Periodic review recommended every 90
                              days.
                            </p>
                          </div>
                        </>
                      )}
                    </CardContent>
                  </GlassCard>
                </div>
              </div>
            </section>

            {/* ── Session Info ── */}
            <section className="py-6 bg-background">
              <div className="w-full px-6">
                <SectionHeading
                  label="Sessions"
                  title="Session Management"
                  subtitle="Active session monitoring and security controls"
                />

                <GlassCard className="overflow-hidden mt-4">
                  <div className="h-1 w-full bg-linear-to-r from-primary/60 via-primary to-primary/60" />
                  <CardHeader className="pb-2">
                    <CardTitle className="flex items-center gap-2 text-base">
                      <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-primary/10 ring-1 ring-primary/20">
                        <Shield className="h-4 w-4 text-primary" />
                      </div>
                      Session Security Controls
                    </CardTitle>
                    <CardDescription>
                      JWT-based sessions with configurable expiry and security
                      policies
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                      {[
                        {
                          label: "Session Type",
                          value: "JWT (stateless)",
                          status: "pass" as const,
                        },
                        {
                          label: "Token Expiry",
                          value: "Access: 15 min / Refresh: 7 days",
                          status: "pass" as const,
                        },
                        {
                          label: "Cookie Security",
                          value: "HttpOnly, SameSite=Lax, Secure",
                          status: "pass" as const,
                        },
                        {
                          label: "Idle Timeout",
                          value: "Configurable via SESSION_LIFETIME",
                          status: (postureData?.checks?.find(
                            (c) => c.name === "Session Timeout",
                          )?.status ?? "warn") as "pass" | "fail" | "warn",
                        },
                        {
                          label: "Token Refresh",
                          value: "Automatic with concurrent retry queue",
                          status: "pass" as const,
                        },
                        {
                          label: "Token Storage",
                          value: "Redis (prod) / Filesystem (dev)",
                          status: "pass" as const,
                        },
                      ].map((item) => {
                        const StatusIcon =
                          CHECK_STATUS_ICONS[item.status] ?? AlertTriangle;
                        return (
                          <div
                            key={item.label}
                            className="rounded-lg border p-3 flex items-start gap-3"
                          >
                            <StatusIcon
                              className={cn(
                                "h-4 w-4 mt-0.5 shrink-0",
                                checkStatusColor(item.status),
                              )}
                            />
                            <div>
                              <p className="text-xs font-medium">
                                {item.label}
                              </p>
                              <p className="text-[10px] text-muted-foreground">
                                {item.value}
                              </p>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </CardContent>
                </GlassCard>
              </div>
            </section>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}

// ── Score Ring Component ────────────────────────────────────────────

function ScoreRing({
  score,
  size = 140,
  isLoading,
}: {
  score: number;
  size?: number;
  isLoading?: boolean;
}) {
  const radius = (size - 14) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;

  if (isLoading) {
    return (
      <Skeleton
        className="rounded-full"
        style={{ width: size, height: size }}
      />
    );
  }

  return (
    <div
      className="relative flex items-center justify-center"
      style={{ width: size, height: size }}
    >
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          strokeWidth={12}
          fill="none"
          className="stroke-muted"
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          strokeWidth={12}
          fill="none"
          className={cn("transition-all duration-1000", scoreStroke(score))}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
        />
      </svg>
      <div className="absolute flex flex-col items-center">
        <span className={cn("text-3xl font-bold", scoreColor(score))}>
          {score}
        </span>
        <span className="text-[10px] text-muted-foreground">/ 100</span>
        <span
          className={cn("text-[10px] font-medium mt-0.5", scoreColor(score))}
        >
          {scoreLabel(score)}
        </span>
      </div>
    </div>
  );
}

// ── Threat Badge ───────────────────────────────────────────────────

function ThreatBadge({ level }: { level: string }) {
  const styles: Record<string, string> = {
    low: "bg-risk-safe/15 text-risk-safe border-risk-safe/30",
    moderate: "bg-risk-alert/15 text-risk-alert border-risk-alert/30",
    high: "bg-risk-critical/15 text-risk-critical border-risk-critical/30",
  };
  const icons: Record<string, React.ElementType> = {
    low: ShieldCheck,
    moderate: ShieldAlert,
    high: ShieldX,
  };
  const Icon = icons[level] ?? Shield;

  return (
    <Badge
      variant="outline"
      className={cn("gap-1 text-sm font-semibold", styles[level])}
    >
      <Icon className="h-3.5 w-3.5" />
      {level.charAt(0).toUpperCase() + level.slice(1)} Threat
    </Badge>
  );
}

// ── Security Stat Card ─────────────────────────────────────────────

function SecurityStatCard({
  label,
  value,
  desc,
  icon: Icon,
  loading,
  color,
  threatCount,
  onClick,
}: {
  label: string;
  value: number;
  desc: string;
  icon: React.ElementType;
  loading: boolean;
  color: "primary" | "threat";
  threatCount?: number;
  onClick?: () => void;
}) {
  const isThreat = color === "threat";
  const n = threatCount ?? 0;

  return (
    <motion.div variants={fadeUp}>
      <GlassCard
        className="overflow-hidden cursor-pointer transition-all duration-300 hover:shadow-lg hover:scale-[1.02]"
        onClick={onClick}
      >
        <div
          className={cn(
            "h-1 w-full bg-linear-to-r",
            isThreat
              ? threatBarColor(n)
              : "from-primary/60 via-primary to-primary/60",
          )}
        />
        <CardContent className="pt-4 pb-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs text-muted-foreground mb-1">{label}</p>
              {loading ? (
                <Skeleton className="h-7 w-16" />
              ) : (
                <p
                  className={cn(
                    "text-2xl font-bold tabular-nums",
                    isThreat && threatColor(n),
                  )}
                >
                  {value.toLocaleString()}
                </p>
              )}
              <p className="text-[10px] text-muted-foreground mt-0.5">{desc}</p>
            </div>
            <div
              className={cn(
                "flex h-10 w-10 items-center justify-center rounded-xl ring-1",
                isThreat ? threatBg(n) : "bg-primary/10 ring-primary/20",
              )}
            >
              <Icon
                className={cn(
                  "h-5 w-5",
                  isThreat ? threatColor(n) : "text-primary",
                )}
              />
            </div>
          </div>
        </CardContent>
      </GlassCard>
    </motion.div>
  );
}

// ── Security Check Row ─────────────────────────────────────────────

const CHECK_STATUS_ICONS: Record<string, React.ElementType> = {
  pass: CheckCircle,
  fail: XCircle,
  warn: AlertTriangle,
};

function SecurityCheckRow({ check }: { check: SecurityCheck }) {
  const [showRemedy, setShowRemedy] = useState(false);
  const StatusIcon = CHECK_STATUS_ICONS[check.status] ?? AlertTriangle;

  return (
    <div>
      <button
        type="button"
        className={cn(
          "flex w-full items-center gap-3 rounded-lg px-3 py-2 transition-colors cursor-pointer text-left",
          check.status === "fail" &&
            "bg-risk-critical/3 hover:bg-risk-critical/6",
          check.status === "warn" && "bg-risk-alert/3 hover:bg-risk-alert/6",
          check.status === "pass" && "hover:bg-muted/50",
        )}
        onClick={() => setShowRemedy(!showRemedy)}
      >
        <StatusIcon
          className={cn("h-4 w-4 shrink-0", checkStatusColor(check.status))}
        />
        <span className="font-medium text-sm flex-1">{check.name}</span>
        <span className="text-xs text-muted-foreground max-w-xs truncate">
          {check.detail}
        </span>
        <Badge
          variant="outline"
          className={cn(
            "text-[10px] ml-2",
            check.status === "pass" &&
              "bg-risk-safe/15 text-risk-safe border-risk-safe/30",
            check.status === "fail" &&
              "bg-risk-critical/15 text-risk-critical border-risk-critical/30",
            check.status === "warn" &&
              "bg-risk-alert/15 text-risk-alert border-risk-alert/30",
          )}
        >
          {check.status === "pass"
            ? "Pass"
            : check.status === "fail"
              ? "Fail"
              : "Warn"}
        </Badge>
      </button>
      {showRemedy && check.status !== "pass" && (
        <div className="ml-10 px-3 py-2 text-xs text-muted-foreground bg-muted/30 rounded-b-lg -mt-0.5 mb-1">
          <span className="font-medium text-foreground">Remediation: </span>
          {check.remediation}
        </div>
      )}
    </div>
  );
}

// ── Audit Table Row ────────────────────────────────────────────────

function AuditTableRow({
  entry,
  expanded,
  onToggle,
  onCopy,
}: {
  entry: AuditLogEntry;
  expanded: boolean;
  onToggle: () => void;
  onCopy: () => void;
}) {
  const isCritical = entry.severity === "critical";
  const isWarning = entry.severity === "warning";

  return (
    <>
      <TableRow
        className={cn(
          "cursor-pointer transition-colors",
          isCritical && "bg-risk-critical/3 hover:bg-risk-critical/6",
          isWarning && "bg-risk-alert/2 hover:bg-risk-alert/4",
          !isCritical && !isWarning && "hover:bg-muted/50",
        )}
        onClick={onToggle}
      >
        <TableCell className="text-xs whitespace-nowrap text-muted-foreground">
          {new Date(entry.created_at).toLocaleString("en-PH", {
            month: "short",
            day: "numeric",
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit",
          })}
        </TableCell>
        <TableCell>
          <Badge variant="outline" className="font-mono text-[10px]">
            {entry.action}
          </Badge>
        </TableCell>
        <TableCell>
          <Badge
            variant="outline"
            className={cn("text-[10px]", severityBadgeCls(entry.severity))}
          >
            {entry.severity}
          </Badge>
        </TableCell>
        <TableCell className="text-xs">
          {entry.user_email ?? (
            <span className="text-muted-foreground italic">System</span>
          )}
        </TableCell>
        <TableCell className="text-xs font-mono text-muted-foreground">
          {entry.ip_address ?? "\u2014"}
        </TableCell>
        <TableCell>
          <Button
            variant="ghost"
            size="sm"
            className="h-7 w-7 p-0"
            onClick={(e) => {
              e.stopPropagation();
              onCopy();
            }}
          >
            <Copy className="h-3.5 w-3.5" />
          </Button>
        </TableCell>
      </TableRow>

      {/* Expanded detail */}
      {expanded && (
        <TableRow className="bg-muted/30">
          <TableCell colSpan={6} className="p-4">
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 text-xs">
              <div>
                <p className="text-muted-foreground mb-0.5">Request ID</p>
                <p className="font-mono">{entry.request_id ?? "\u2014"}</p>
              </div>
              <div>
                <p className="text-muted-foreground mb-0.5">User ID</p>
                <p className="font-mono">{entry.user_id ?? "N/A"}</p>
              </div>
              <div>
                <p className="text-muted-foreground mb-0.5">Target User ID</p>
                <p className="font-mono">{entry.target_user_id ?? "N/A"}</p>
              </div>
              <div>
                <p className="text-muted-foreground mb-0.5">IP Address</p>
                <p className="font-mono">{entry.ip_address ?? "N/A"}</p>
              </div>
              {entry.details && (
                <div className="sm:col-span-2 lg:col-span-4">
                  <p className="text-muted-foreground mb-0.5">Event Details</p>
                  <pre className="bg-muted rounded p-2 whitespace-pre-wrap break-all font-mono text-[11px] max-h-40 overflow-auto">
                    {JSON.stringify(entry.details, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          </TableCell>
        </TableRow>
      )}
    </>
  );
}
