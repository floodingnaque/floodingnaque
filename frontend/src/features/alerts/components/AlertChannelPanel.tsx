/**
 * AlertChannelPanel
 *
 * Three-tab panel: Channels overview, SMS delivery log, templates preview.
 * Wired to useAlertHistory() for SMS log and useSimulateSms() for test send.
 */

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  useAlertHistory,
  useSimulateSms,
} from "@/features/alerts/hooks/useAlerts";
import type {
  AlertChannel,
  SmsLogEntry,
  SmsTemplate,
} from "@/features/dashboard/types";
import { cn } from "@/lib/utils";
import {
  Bell,
  Megaphone,
  MessageSquare,
  Radio,
  Send,
  Smartphone,
  Wifi,
} from "lucide-react";
import { memo, useCallback, useMemo, useState } from "react";

// ---------------------------------------------------------------------------
// Static data  — alert channels & templates
// ---------------------------------------------------------------------------

const CHANNELS: AlertChannel[] = [
  {
    name: "SMS Gateway",
    icon: "📱",
    status: "Primary",
    coverage: "—",
    cost: "—",
    latency: "—",
  },
  {
    name: "Push Notification",
    icon: "🔔",
    status: "Active",
    coverage: "—",
    cost: "Free",
    latency: "—",
  },
  {
    name: "Radio Broadcast",
    icon: "📻",
    status: "Fallback",
    coverage: "—",
    cost: "—",
    latency: "—",
  },
  {
    name: "Social Media",
    icon: "📲",
    status: "Active",
    coverage: "—",
    cost: "Free",
    latency: "—",
  },
  {
    name: "Sirens / PA",
    icon: "🔊",
    status: "Fallback",
    coverage: "—",
    cost: "—",
    latency: "—",
  },
  {
    name: "Mesh Radio",
    icon: "📡",
    status: "Planned",
    coverage: "TBD",
    cost: "TBD",
    latency: "TBD",
  },
];

const TEMPLATES: SmsTemplate[] = [
  {
    level: "Critical",
    title: "CRITICAL FLOOD ALERT",
    color: "text-risk-critical border-risk-critical/40 bg-risk-critical/10",
    msg: "[PARANAQUE DRRMO] CRITICAL: Severe flooding in {barangay}. Water level RISING. Evacuate to nearest center immediately. Monitor local radio for updates.",
  },
  {
    level: "Alert",
    title: "FLOOD WARNING",
    color: "text-risk-alert border-risk-alert/40 bg-risk-alert/10",
    msg: "[PARANAQUE DRRMO] WARNING: Flood risk ELEVATED in {barangay}. Prepare go-bags. Avoid low-lying areas. Stay tuned for further advisories.",
  },
  {
    level: "Safe",
    title: "ALL CLEAR",
    color: "text-risk-safe border-risk-safe/40 bg-risk-safe/10",
    msg: "[PARANAQUE DRRMO] UPDATE: Water levels receding in {barangay}. Roads reopening. Exercise caution. Report damage to 8888.",
  },
];

// ---------------------------------------------------------------------------
// Tab type
// ---------------------------------------------------------------------------

type Tab = "channels" | "sms" | "templates";

const TABS: { key: Tab; label: string; icon: typeof Bell }[] = [
  { key: "channels", label: "Channels", icon: Radio },
  { key: "sms", label: "SMS Log", icon: Smartphone },
  { key: "templates", label: "Templates", icon: MessageSquare },
];

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function ChannelRow({ ch }: { ch: AlertChannel }) {
  const statusColor =
    ch.status === "Primary"
      ? "text-risk-safe border-risk-safe/40 bg-risk-safe/10"
      : ch.status === "Active"
        ? "text-blue-400 border-blue-400/40 bg-blue-400/10"
        : ch.status === "Fallback"
          ? "text-risk-alert border-risk-alert/40 bg-risk-alert/10"
          : "text-muted-foreground border-border bg-muted";

  return (
    <div className="flex items-center justify-between py-2 border-b border-border last:border-b-0">
      <div className="flex items-center gap-2 min-w-0">
        <span className="text-base">{ch.icon}</span>
        <div className="min-w-0">
          <div className="text-[11px] font-mono font-medium truncate text-foreground">
            {ch.name}
          </div>
          <div className="text-[9px] font-mono text-muted-foreground">
            {ch.coverage} coverage · {ch.latency}
          </div>
        </div>
      </div>
      <div className="flex items-center gap-2 shrink-0">
        <span className="text-[9px] font-mono text-muted-foreground">
          {ch.cost}
        </span>
        <Badge
          variant="outline"
          className={cn("text-[9px] px-1.5 py-0", statusColor)}
        >
          {ch.status}
        </Badge>
      </div>
    </div>
  );
}

function SmsRow({ entry }: { entry: SmsLogEntry }) {
  const typeColor =
    entry.type === "Critical"
      ? "text-risk-critical border-risk-critical/40 bg-risk-critical/10"
      : entry.type === "Alert"
        ? "text-risk-alert border-risk-alert/40 bg-risk-alert/10"
        : "text-blue-400 border-blue-400/40 bg-blue-400/10";

  return (
    <div className="flex items-center justify-between py-2 border-b border-border last:border-b-0">
      <div className="min-w-0">
        <div className="flex items-center gap-1.5">
          <Badge
            variant="outline"
            className={cn("text-[9px] px-1.5 py-0", typeColor)}
          >
            {entry.type}
          </Badge>
          <span className="text-[10px] text-muted-foreground font-mono">
            {entry.time}
          </span>
        </div>
        <div className="text-[9px] font-mono text-muted-foreground mt-0.5">
          {entry.barangays.join(", ")}
        </div>
      </div>
      <div className="text-right shrink-0">
        <div className="text-[11px] font-mono font-bold text-foreground">
          {entry.recipients.toLocaleString()}
        </div>
        <div className="text-[9px] font-mono text-muted-foreground">
          {entry.rate}% delivered
        </div>
      </div>
    </div>
  );
}

function TemplateCard({ tpl }: { tpl: SmsTemplate }) {
  return (
    <div className={cn("border rounded-lg p-3 space-y-1", tpl.color)}>
      <div className="text-[10px] font-mono font-bold uppercase tracking-wider">
        {tpl.title}
      </div>
      <div className="text-[11px] font-mono leading-relaxed opacity-90">
        {tpl.msg}
      </div>
      <div className="text-[9px] font-mono opacity-60">
        ~{tpl.msg.length} chars · {Math.ceil(tpl.msg.length / 160)} SMS
        segment(s)
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

export const AlertChannelPanel = memo(function AlertChannelPanel() {
  const [tab, setTab] = useState<Tab>("channels");
  const { data: history, isLoading } = useAlertHistory();
  const simulateMutation = useSimulateSms();

  // Build SMS log from alert history
  const smsLog: SmsLogEntry[] = useMemo(() => {
    if (!history?.alerts) return [];
    return history.alerts.slice(0, 8).map((a, i) => ({
      time: new Date(a.created_at).toLocaleTimeString("en-PH", {
        hour: "2-digit",
        minute: "2-digit",
      }),
      recipients: (((a.id ?? i + 1) * 37) % 500) + 100, // deterministic placeholder
      barangays: a.location ? [a.location] : ["System-wide"],
      status: a.acknowledged ? "Delivered" : "Pending",
      type: (a.risk_level >= 2
        ? "Critical"
        : a.risk_level === 1
          ? "Alert"
          : "Info") as SmsLogEntry["type"],
      rate: a.acknowledged ? 98 : 87,
    }));
  }, [history]);

  const handleTestSms = useCallback(() => {
    simulateMutation.mutate({ phone: "09171234567", riskLevel: 2 });
  }, [simulateMutation]);

  if (isLoading) return <AlertChannelPanelSkeleton />;

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between space-y-0 pb-3">
        <CardTitle className="flex items-center gap-2 text-sm font-bold font-mono tracking-wide">
          <Megaphone className="h-4 w-4" />
          Alert Channels & SMS
        </CardTitle>
        <Button
          variant="outline"
          size="sm"
          className="h-7 text-[10px] font-mono gap-1"
          disabled={simulateMutation.isPending}
          onClick={handleTestSms}
        >
          <Send className="h-3 w-3" />
          {simulateMutation.isPending ? "Sending…" : "Test SMS"}
        </Button>
      </CardHeader>

      <CardContent className="space-y-3">
        {/* Tabs */}
        <div className="flex gap-1 border-b border-border pb-2">
          {TABS.map((t) => {
            const Icon = t.icon;
            return (
              <button
                key={t.key}
                type="button"
                onClick={() => setTab(t.key)}
                className={cn(
                  "flex items-center gap-1.5 rounded-md px-3 py-1.5 text-[10px] font-mono transition-colors",
                  tab === t.key
                    ? "bg-primary/10 text-primary border border-primary/30"
                    : "text-muted-foreground hover:bg-accent/50",
                )}
              >
                <Icon className="h-3 w-3" />
                {t.label}
              </button>
            );
          })}
        </div>

        {/* Tab content */}
        {tab === "channels" && (
          <div>
            {/* Architecture flow */}
            <div className="flex items-center justify-center gap-2 py-3 flex-wrap">
              {[
                "Prediction",
                "Risk Engine",
                "Alert Router",
                "SMS / Push / Radio",
              ].map((step, i) => (
                <div key={step} className="flex items-center gap-2">
                  <div className="rounded-md border border-border bg-muted px-2 py-1 text-[9px] font-mono text-foreground">
                    {step}
                  </div>
                  {i < 3 && <Wifi className="h-3 w-3 text-muted-foreground" />}
                </div>
              ))}
            </div>
            {CHANNELS.map((ch) => (
              <ChannelRow key={ch.name} ch={ch} />
            ))}
          </div>
        )}

        {tab === "sms" && (
          <div>
            {smsLog.length === 0 ? (
              <div className="py-6 text-center text-xs text-muted-foreground font-mono">
                No SMS delivery records yet.
              </div>
            ) : (
              smsLog.map((entry, i) => <SmsRow key={i} entry={entry} />)
            )}
          </div>
        )}

        {tab === "templates" && (
          <div className="space-y-2">
            {TEMPLATES.map((tpl) => (
              <TemplateCard key={tpl.level} tpl={tpl} />
            ))}
          </div>
        )}

        {/* Footer summary */}
        <div className="flex items-center justify-between text-[9px] text-muted-foreground font-mono pt-1 border-t border-border">
          <span>
            {CHANNELS.filter((c) => c.status !== "Planned").length} active
            channels
          </span>
          <span>{history?.summary?.total ?? 0} alerts sent (all time)</span>
        </div>
      </CardContent>
    </Card>
  );
});

// ---------------------------------------------------------------------------
// Skeleton
// ---------------------------------------------------------------------------

export function AlertChannelPanelSkeleton() {
  return (
    <Card>
      <CardHeader>
        <Skeleton className="h-5 w-44" />
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex gap-1">
          <Skeleton className="h-7 w-20" />
          <Skeleton className="h-7 w-20" />
          <Skeleton className="h-7 w-20" />
        </div>
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-10 w-full" />
        ))}
      </CardContent>
    </Card>
  );
}
