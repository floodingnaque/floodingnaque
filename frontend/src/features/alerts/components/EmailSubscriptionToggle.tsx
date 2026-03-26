/**
 * EmailSubscriptionToggle
 *
 * Toggle switch for residents to opt in / out of email flood alerts.
 * Uses a TanStack Query mutation to persist the preference.
 */

import { Mail } from "lucide-react";

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

async function getEmailPreference(): Promise<boolean> {
  const res = await api.get<{
    success: boolean;
    user: { email_alerts_enabled: boolean };
  }>(`${API_ENDPOINTS.auth.me}`);
  return res.user?.email_alerts_enabled ?? false;
}

async function toggleEmailPreference(enabled: boolean): Promise<void> {
  await api.patch(`${API_ENDPOINTS.auth.me}`, {
    email_alerts_enabled: enabled,
  });
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export interface EmailSubscriptionToggleProps {
  className?: string;
}

export function EmailSubscriptionToggle({
  className,
}: EmailSubscriptionToggleProps) {
  const queryClient = useQueryClient();

  const { data: isEnabled, isLoading } = useQuery({
    queryKey: ["email", "preference"],
    queryFn: getEmailPreference,
    staleTime: 60_000,
  });

  const mutation = useMutation({
    mutationFn: toggleEmailPreference,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["email", "preference"] });
    },
  });

  if (isLoading) return <EmailSubscriptionToggleSkeleton />;

  return (
    <Card className={cn("w-full", className)}>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-base">
          <Mail className="h-4 w-4" />
          Email Alerts
        </CardTitle>
        <CardDescription>Receive flood warnings via email</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="flex items-center justify-between">
          <Label htmlFor="email-toggle" className="text-sm">
            {isEnabled ? "Email alerts enabled" : "Email alerts disabled"}
          </Label>
          <Switch
            id="email-toggle"
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

export function EmailSubscriptionToggleSkeleton() {
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
