/**
 * SmsSubscriptionToggle
 *
 * Toggle switch for residents to opt in / out of SMS flood alerts.
 * Uses a TanStack Query mutation to persist the preference.
 */

import { BellRing } from "lucide-react";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import { API_ENDPOINTS } from "@/config/api.config";
import api from "@/lib/api-client";
import { cn } from "@/lib/cn";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

// ---------------------------------------------------------------------------
// API helpers
// ---------------------------------------------------------------------------

async function getSmsPreference(): Promise<boolean> {
  const res = await api.get<{
    success: boolean;
    data: { sms_enabled: boolean };
  }>(`${API_ENDPOINTS.auth.me}`);
  return res.data?.sms_enabled ?? false;
}

async function toggleSmsPreference(enabled: boolean): Promise<void> {
  await api.patch(`${API_ENDPOINTS.auth.me}`, { sms_alerts_enabled: enabled });
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export interface SmsSubscriptionToggleProps {
  className?: string;
}

export function SmsSubscriptionToggle({
  className,
}: SmsSubscriptionToggleProps) {
  const queryClient = useQueryClient();

  const { data: isEnabled, isLoading } = useQuery({
    queryKey: ["sms", "preference"],
    queryFn: getSmsPreference,
    staleTime: 60_000,
  });

  const mutation = useMutation({
    mutationFn: toggleSmsPreference,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["sms", "preference"] });
    },
  });

  if (isLoading) return <SmsSubscriptionToggleSkeleton />;

  return (
    <Card className={cn("w-full", className)}>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-base">
          <BellRing className="h-4 w-4" />
          SMS Alerts
        </CardTitle>
        <CardDescription>
          Receive flood warnings via text message
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="flex items-center justify-between">
          <Label htmlFor="sms-toggle" className="text-sm">
            {isEnabled ? "SMS alerts enabled" : "SMS alerts disabled"}
          </Label>
          <Switch
            id="sms-toggle"
            checked={isEnabled ?? false}
            onCheckedChange={(checked) => mutation.mutate(checked)}
            disabled={mutation.isPending}
          />
        </div>
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Skeleton
// ---------------------------------------------------------------------------

export function SmsSubscriptionToggleSkeleton() {
  return (
    <Card className="w-full">
      <CardHeader className="pb-3">
        <Skeleton className="h-5 w-24" />
        <Skeleton className="h-4 w-48" />
      </CardHeader>
      <CardContent>
        <div className="flex items-center justify-between">
          <Skeleton className="h-4 w-36" />
          <Skeleton className="h-5 w-10 rounded-full" />
        </div>
      </CardContent>
    </Card>
  );
}
