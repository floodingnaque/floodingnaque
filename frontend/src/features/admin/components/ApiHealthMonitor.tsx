/**
 * ApiHealthMonitor
 *
 * Admin component that displays per-source API health and reliability
 * using data from the /api/v1/data/reliability endpoint.
 */

import { useQuery } from "@tanstack/react-query";
import { Activity, CheckCircle2, XCircle } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { API_ENDPOINTS } from "@/config/api.config";
import api from "@/lib/api-client";
import { cn } from "@/lib/cn";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface SourceReliability {
  source_name: string;
  ema_score: number;
  success_rate: number;
  total_calls: number;
  last_latency_ms: number;
}

interface ReliabilityResponse {
  global_reliability_score: number;
  sources_available: number;
  sources_failed: number;
  per_source: Record<
    string,
    {
      source: string;
      quality: string;
      confidence: number;
      latency_ms: number;
      is_fallback: boolean;
    }
  >;
  ema_tracking: {
    source_count: number;
    sources: Record<string, SourceReliability>;
  };
  warnings: string[];
}

// ---------------------------------------------------------------------------
// Data fetching
// ---------------------------------------------------------------------------

async function fetchReliability(): Promise<ReliabilityResponse> {
  const res = await api.get<{
    success: boolean;
    data: ReliabilityResponse;
  }>(API_ENDPOINTS.data.reliability);
  return res.data;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export interface ApiHealthMonitorProps {
  className?: string;
}

export function ApiHealthMonitor({ className }: ApiHealthMonitorProps) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["admin", "apiHealth"],
    queryFn: fetchReliability,
    refetchInterval: 30_000,
    staleTime: 15_000,
  });

  if (isLoading) return <ApiHealthMonitorSkeleton />;

  const globalScore = data?.global_reliability_score ?? 0;
  const emaSources = data?.ema_tracking?.sources ?? {};
  const perSource = data?.per_source ?? {};

  return (
    <Card className={cn("w-full", className)}>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-base">
          <Activity className="h-4 w-4" />
          API Health Monitor
        </CardTitle>
        <CardDescription>Data source reliability (EMA scores)</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Global score */}
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium">Global Reliability</span>
          <Badge
            className={cn(
              "text-xs",
              globalScore >= 0.7
                ? "bg-risk-safe/15 text-risk-safe"
                : globalScore >= 0.4
                  ? "bg-risk-alert/15 text-risk-alert"
                  : "bg-risk-critical/15 text-risk-critical",
            )}
          >
            {(globalScore * 100).toFixed(0)}%
          </Badge>
        </div>

        <div className="flex gap-2 text-xs text-muted-foreground">
          <span>Available: {data?.sources_available ?? 0}</span>
          <span>Failed: {data?.sources_failed ?? 0}</span>
        </div>

        {isError && (
          <p className="text-sm text-destructive">Failed to load health data</p>
        )}

        {/* Per-source health */}
        <div className="space-y-2">
          {Object.entries(perSource).map(([category, info]) => {
            const ema = emaSources[info.source];
            const score = ema?.ema_score ?? info.confidence;

            return (
              <div
                key={category}
                className="flex items-center justify-between text-sm"
              >
                <div className="flex items-center gap-2">
                  {score >= 0.6 ? (
                    <CheckCircle2 className="h-3.5 w-3.5 text-risk-safe" />
                  ) : (
                    <XCircle className="h-3.5 w-3.5 text-risk-critical" />
                  )}
                  <span className="capitalize">{category}</span>
                  {info.is_fallback && (
                    <Badge variant="outline" className="text-xs py-0">
                      fallback
                    </Badge>
                  )}
                </div>
                <div className="flex items-center gap-3 text-muted-foreground text-xs">
                  <span>{info.latency_ms?.toFixed(0)}ms</span>
                  <span>{(score * 100).toFixed(0)}%</span>
                </div>
              </div>
            );
          })}
        </div>

        {/* Warnings */}
        {data?.warnings && data.warnings.length > 0 && (
          <div className="mt-2 space-y-1">
            {data.warnings.map((w, i) => (
              <p key={i} className="text-xs text-risk-alert">
                {w}
              </p>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Skeleton
// ---------------------------------------------------------------------------

export function ApiHealthMonitorSkeleton() {
  return (
    <Card className="w-full">
      <CardHeader className="pb-3">
        <Skeleton className="h-5 w-40" />
        <Skeleton className="h-4 w-52" />
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex justify-between">
          <Skeleton className="h-4 w-32" />
          <Skeleton className="h-5 w-12 rounded-full" />
        </div>
        {[1, 2, 3, 4, 5].map((i) => (
          <div key={i} className="flex justify-between">
            <Skeleton className="h-4 w-24" />
            <Skeleton className="h-4 w-16" />
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
