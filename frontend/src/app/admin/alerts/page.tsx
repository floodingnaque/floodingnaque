/**
 * Admin — Alert Management & Notification Center
 *
 * Full alert lifecycle management with bulk actions, SMS dispatch,
 * channel monitoring, and delivery analytics.
 */

import {
  AlertTriangle,
  Bell,
  Check,
  CheckCheck,
  Clock,
  Mail,
  MapPin,
  Megaphone,
  Search,
  Shield,
  ShieldCheck,
  Smartphone,
  Trash2,
  Wifi,
} from "lucide-react";
import { useMemo, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import {
  AlertChannelPanel,
  SmsSimulationPanel,
  useAcknowledgeAlert,
  useAcknowledgeAll,
  useAlertHistory,
  useAlerts,
  useAlertStream,
} from "@/features/alerts";
import { cn } from "@/lib/utils";
import type { Alert } from "@/types/api/alert";

/* ── Risk badge styles ─────────────────────────────────── */

const RISK_BADGE: Record<number, { label: string; cls: string }> = {
  0: { label: "Safe", cls: "bg-green-500/10 text-green-700 border-green-300" },
  1: {
    label: "Alert",
    cls: "bg-amber-500/10 text-amber-700 border-amber-300",
  },
  2: {
    label: "Critical",
    cls: "bg-red-500/10 text-red-700 border-red-300",
  },
};

/* ── Alert Row ─────────────────────────────────────────── */

function AlertRow({
  alert,
  onAck,
  isAcking,
  selected,
  onSelect,
}: {
  alert: Alert;
  onAck: (id: number) => void;
  isAcking: boolean;
  selected: boolean;
  onSelect: (id: number) => void;
}) {
  const risk = RISK_BADGE[alert.risk_level] ?? RISK_BADGE[0]!;
  return (
    <div
      className={cn(
        "flex items-start justify-between gap-4 p-4 border rounded-lg transition-colors",
        selected && "ring-2 ring-primary/50",
        alert.acknowledged
          ? "bg-muted/20 opacity-70"
          : "bg-card hover:bg-muted/30",
      )}
    >
      <div className="flex gap-3 min-w-0 flex-1">
        {/* Selection checkbox */}
        <input
          type="checkbox"
          checked={selected}
          onChange={() => onSelect(alert.id)}
          className="mt-1 h-4 w-4 rounded border-input accent-primary shrink-0"
        />

        <div
          className={cn(
            "mt-0.5 h-8 w-8 rounded-lg flex items-center justify-center shrink-0",
            alert.risk_level === 2
              ? "bg-red-500/10"
              : alert.risk_level === 1
                ? "bg-amber-500/10"
                : "bg-green-500/10",
          )}
        >
          <AlertTriangle
            className={cn(
              "h-4 w-4",
              alert.risk_level === 2
                ? "text-red-500"
                : alert.risk_level === 1
                  ? "text-amber-500"
                  : "text-green-500",
            )}
          />
        </div>
        <div className="space-y-1 min-w-0">
          <p className="text-sm font-medium leading-tight">{alert.message}</p>
          <div className="flex items-center gap-3 text-xs text-muted-foreground flex-wrap">
            <Badge
              variant="outline"
              className={cn("text-[10px] px-1.5", risk?.cls)}
            >
              {risk?.label}
            </Badge>
            {alert.location && (
              <span className="flex items-center gap-1">
                <MapPin className="h-3 w-3" />
                {alert.location}
              </span>
            )}
            <span className="flex items-center gap-1">
              <Clock className="h-3 w-3" />
              {new Date(alert.triggered_at).toLocaleString("en-PH", {
                month: "short",
                day: "numeric",
                hour: "2-digit",
                minute: "2-digit",
              })}
            </span>
            {alert.confidence_score != null && (
              <span>{Math.round(alert.confidence_score * 100)}% conf.</span>
            )}
          </div>
        </div>
      </div>
      {!alert.acknowledged ? (
        <Button
          size="sm"
          variant="outline"
          className="shrink-0 gap-1 text-xs"
          onClick={() => onAck(alert.id)}
          disabled={isAcking}
        >
          <Check className="h-3 w-3" />
          Ack
        </Button>
      ) : (
        <Badge variant="secondary" className="text-xs shrink-0 gap-1">
          <CheckCheck className="h-3 w-3" />
          Ack&apos;d
        </Badge>
      )}
    </div>
  );
}

/* ── Main Page ─────────────────────────────────────────── */

export default function AdminAlertsPage() {
  const [search, setSearch] = useState("");
  const [riskFilter, setRiskFilter] = useState<string>("all");
  const [ackFilter, setAckFilter] = useState<string>("all");
  const [selected, setSelected] = useState<Set<number>>(new Set());

  const { data: alertsData, isLoading, refetch } = useAlerts();
  const { data: history } = useAlertHistory();
  const ack = useAcknowledgeAlert({ onSuccess: () => refetch() });
  const ackAll = useAcknowledgeAll({ onSuccess: () => refetch() });
  const { connectionState } = useAlertStream();

  const alerts: Alert[] = useMemo(() => {
    if (!alertsData) return [];
    if (Array.isArray(alertsData)) return alertsData;
    if ("data" in alertsData) return alertsData.data ?? [];
    return [];
  }, [alertsData]);

  const filtered = useMemo(() => {
    let result = alerts;
    if (riskFilter !== "all")
      result = result.filter((a) => String(a.risk_level) === riskFilter);
    if (ackFilter === "pending") result = result.filter((a) => !a.acknowledged);
    else if (ackFilter === "acknowledged")
      result = result.filter((a) => a.acknowledged);
    if (search.trim()) {
      const q = search.toLowerCase();
      result = result.filter(
        (a) =>
          a.message.toLowerCase().includes(q) ||
          a.location?.toLowerCase().includes(q),
      );
    }
    return result;
  }, [alerts, riskFilter, ackFilter, search]);

  const pendingCount = alerts.filter((a) => !a.acknowledged).length;

  const toggleSelect = (id: number) =>
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });

  const selectAll = () => {
    if (selected.size === filtered.length) setSelected(new Set());
    else setSelected(new Set(filtered.map((a) => a.id)));
  };

  return (
    <div className="p-4 sm:p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="h-10 w-10 rounded-lg bg-red-500/10 flex items-center justify-center">
          <Shield className="h-5 w-5 text-red-500" />
        </div>
        <div>
          <h1 className="text-lg font-semibold">Alert & Notification Center</h1>
          <p className="text-xs text-muted-foreground">
            Manage alerts, SMS dispatch, email notifications, and channel
            monitoring
          </p>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <Card>
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground">Total Alerts</p>
            <p className="text-2xl font-bold">
              {history?.summary?.total_alerts ?? alerts.length}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground flex items-center gap-1">
              <AlertTriangle className="h-3 w-3 text-red-500" />
              Critical
            </p>
            <p className="text-2xl font-bold text-red-600">
              {history?.summary?.risk_distribution?.critical ?? 0}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground flex items-center gap-1">
              <Smartphone className="h-3 w-3" />
              SMS Delivered
            </p>
            <p className="text-2xl font-bold">
              {history?.summary?.status_distribution?.delivered ?? 0}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground flex items-center gap-1">
              <Mail className="h-3 w-3" />
              Pending
            </p>
            <p className="text-2xl font-bold text-amber-600">{pendingCount}</p>
          </CardContent>
        </Card>
      </div>

      {/* Filters & Bulk Actions */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search alerts by barangay or message..."
            className="pl-9"
          />
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <Select value={riskFilter} onValueChange={setRiskFilter}>
            <SelectTrigger className="w-32">
              <SelectValue placeholder="Risk Level" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Levels</SelectItem>
              <SelectItem value="2">Critical</SelectItem>
              <SelectItem value="1">Alert</SelectItem>
              <SelectItem value="0">Safe</SelectItem>
            </SelectContent>
          </Select>
          <Select value={ackFilter} onValueChange={setAckFilter}>
            <SelectTrigger className="w-36">
              <SelectValue placeholder="Status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Status</SelectItem>
              <SelectItem value="pending">Pending</SelectItem>
              <SelectItem value="acknowledged">Acknowledged</SelectItem>
            </SelectContent>
          </Select>
          {pendingCount > 0 && (
            <Button
              size="sm"
              variant="outline"
              className="gap-1"
              onClick={() => ackAll.mutate()}
              disabled={ackAll.isPending}
            >
              <CheckCheck className="h-3.5 w-3.5" />
              Ack All ({pendingCount})
            </Button>
          )}
          {selected.size > 0 && (
            <Button
              size="sm"
              variant="destructive"
              className="gap-1"
              onClick={() => {
                // confirm in advance
                if (
                  window.confirm(`Delete ${selected.size} selected alert(s)?`)
                ) {
                  // use the bulk delete endpoint
                  fetch("/api/v1/alerts/admin/bulk-delete", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    credentials: "include",
                    body: JSON.stringify({
                      alert_ids: Array.from(selected),
                    }),
                  }).then(() => {
                    setSelected(new Set());
                    refetch();
                  });
                }
              }}
            >
              <Trash2 className="h-3.5 w-3.5" />
              Delete ({selected.size})
            </Button>
          )}
        </div>
      </div>

      {/* Alert Feed */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-base flex items-center gap-2">
                <Bell className="h-4 w-4" />
                Alert Feed
                {pendingCount > 0 && (
                  <Badge variant="destructive" className="text-xs">
                    {pendingCount} pending
                  </Badge>
                )}
              </CardTitle>
              <CardDescription>
                <button
                  type="button"
                  onClick={selectAll}
                  className="text-xs underline hover:text-primary transition-colors"
                >
                  {selected.size === filtered.length && filtered.length > 0
                    ? "Deselect all"
                    : "Select all"}
                </button>
              </CardDescription>
            </div>
            <Badge
              variant="outline"
              className={cn(
                "text-xs gap-1",
                connectionState === "CONNECTED"
                  ? "text-green-600"
                  : connectionState === "RECONNECTING"
                    ? "text-amber-600"
                    : "text-muted-foreground",
              )}
            >
              <Wifi className="h-3 w-3" />
              {connectionState === "CONNECTED"
                ? "Live"
                : connectionState === "RECONNECTING"
                  ? "Reconnecting…"
                  : "Polling"}
            </Badge>
          </div>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-3">
              {Array.from({ length: 4 }).map((_, i) => (
                <Skeleton key={i} className="h-20 w-full rounded-lg" />
              ))}
            </div>
          ) : filtered.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
              <ShieldCheck className="h-12 w-12 mb-3 text-emerald-500/50" />
              <p className="text-base font-medium">No Active Alerts</p>
              <p className="text-sm mt-1">
                {search || riskFilter !== "all" || ackFilter !== "all"
                  ? "No alerts match your filters."
                  : "All alerts have been acknowledged and resolved."}
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              {filtered.map((alert) => (
                <AlertRow
                  key={alert.id}
                  alert={alert}
                  onAck={(id) => ack.mutate(id)}
                  isAcking={ack.isPending}
                  selected={selected.has(alert.id)}
                  onSelect={toggleSelect}
                />
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Bottom panels: Channel Panel + SMS Simulation */}
      <div className="grid md:grid-cols-2 gap-6">
        <AlertChannelPanel />
        <Card>
          <CardHeader>
            <CardTitle className="text-sm flex items-center gap-2">
              <Megaphone className="h-4 w-4" />
              SMS Sandbox
            </CardTitle>
            <CardDescription>
              Send a test SMS to verify delivery. Always runs in sandbox mode.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <SmsSimulationPanel />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
